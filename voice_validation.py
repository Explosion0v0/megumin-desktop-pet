"""Verify the actual audio stream plus cast scheduling and mute behaviour."""
from pathlib import Path
import time
import numpy as np
from voice import VoicePlayer
from spell_scene import CAST_RELEASE,CAST_DURATION

def check_voice(folder):
    from app import Engine,DEFAULTS
    v=VoicePlayer(folder);result={}
    try:
        clip=v.entries['chants'][0]['short']
        result['voice_assets']=len(v.entries['chants'])==10 and all((Path(folder)/x[k]['file']).is_file() for x in v.entries['chants'] for k in ('full','short'))
        result['voice_muted_at_zero']=not v.play(clip,0,time.monotonic()) and not v.handle.value
        # A near-silent real stream validates waveOut without a loud test shout.
        result['audio_device_opened']=v.play(clip,1,time.monotonic())
        if result['audio_device_opened']:
            original=__import__('wave').open(str(Path(folder)/clip['file']),'rb')
            raw=np.frombuffer(original.readframes(original.getnframes()),dtype='<i2');original.close()
            scaled=np.frombuffer(v.buffer.raw[:v.header.length],dtype='<i2')
            result['volume_attenuates_pcm']=float(np.max(np.abs(scaled.astype(float))))<=float(np.max(np.abs(raw.astype(float))))*.0101+1
            time.sleep(.20);result['audio_playback_advances']=(v.position() or 0)>.04
            result['audio_mouth_envelope']=v.level() is not None
        v.stop();result['audio_stops_cleanly']=not v.handle.value and v.buffer is None
        selected=[v.choose()['file'] for _ in range(20)]
        result['random_voice_no_immediate_repeat']=all(a!=b for a,b in zip(selected,selected[1:]))
        e=Engine(now=100);e.action('cast',100)
        cfg=dict(DEFAULTS,voice_full=False,voice_model=False)
        v.tick(e,cfg,100)
        result['short_voice_delayed_until_release']=v.pending is not None and not v.played_cast and e.cast_release==CAST_RELEASE and e.cast_duration==CAST_DURATION
        v.tick(e,dict(cfg,voice_enabled=False),101)
        result['mute_cancels_scheduled_voice']=v.pending is None and v.played_cast and not v.handle.value
        e=Engine(now=200);e.action('cast',200)
        # Use the real cue manifest with an inert play sink to verify long timing.
        real_play=v.play;v.play=lambda *args:True
        v.tick(e,dict(cfg,voice_full=True),200)
        release=e.cast_release
        e.tick(208,dict(DEFAULTS,idle_enabled=False))
        result['full_voice_extends_cast']=e.state=='cast' and e.until>208 and release>CAST_RELEASE
        result['voice_release_matches_visual_effect']=abs(e.visual_age(200+release)-CAST_RELEASE)<.0001
        e.tick(e.until+.01,dict(DEFAULTS,idle_enabled=False))
        result['full_voice_returns_to_tired']=e.state=='tired'
        v.play=real_play
        result['voice_checks_passed']=all(result.values())
        return result
    finally:v.stop()

if __name__=='__main__':
    import json
    report=check_voice(Path(__file__).parent/'assets/voices')
    print(json.dumps(report,indent=2))
    assert report['voice_checks_passed']
