"""Verify the trained-model bank, action dispatch, captions and real audio."""
from pathlib import Path
import hashlib,wave,time
import numpy as np
from voice import VoicePlayer
def check_model_voice(folder):
    from app import Engine,DEFAULTS
    v=VoicePlayer(folder);r={}
    try:
        bank=v.generated;r['trained_voice_bank_loaded']=bool(bank) and bank['model']['version']=='v2ProPlus'
        entries=[x for clips in bank['scenes'].values() for x in clips]+[x[k] for x in bank['chants'] for k in ('short','full')]
        valid=True
        for x in entries:
            p=Path(folder)/x['file']
            valid&=hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256']
            with wave.open(str(p),'rb') as w:
                data=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)
                valid&=w.getsampwidth()==2 and w.getnchannels()==1 and np.max(np.abs(data))>200
                valid&=abs(len(data)/w.getframerate()-x['duration'])<.01 and bool(x.get('zh'))
        r['generated_audio_integrity']=bool(valid)
        r['source_weights_unchanged']=all(hashlib.sha256(Path(bank['model'][key]).read_bytes()).hexdigest()==bank['model'][key+'_sha256'] for key in ('gpt','sovits'))
        played=[];play=v.play
        v.play=lambda clip,*args:played.append(clip) or True
        cfg=dict(DEFAULTS,voice_model=True)
        good=True
        for i,state in enumerate(('happy','drink','cat','sleep','tired')):
            e=Engine(now=100+i*20);e.action(state,100+i*20)
            before=len(played);v.tick(e,cfg,100+i*20);v.tick(e,cfg,100+i*20+.01)
            good&=len(played)==before+1 and played[-1]['file'] in [x['file'] for x in bank['scenes'][state]]
        r['scene_voices_dispatch_once']=good
        for scene in ('pride','shame','surprise','doubt','anger','cry','excite','appeal'):
            e=Engine(now=250);e.action('happy',250)
            v.react_native('00_'+scene.title()+'_01',e,cfg,250)
            good&=played[-1]['file'] in [x['file'] for x in bank['scenes'][scene]]
        r['native_expression_voices']=good
        before=len(played);v.tick(e,dict(cfg,voice_enabled=False),251)
        r['model_voice_respects_mute']=len(played)==before
        e=Engine(now=300);e.action('cast',300);v.tick(e,dict(cfg,voice_full=True),300)
        r['model_chant_sync']=v.pending['explosion_source']=='original' and abs(e.visual_age(300+v.pending['release'])-3.65)<.0001
        # Verify every original variant, without probabilistic sampling: force
        # each choice while keeping the production selection and scheduling.
        from unittest.mock import patch
        original_keys={x['id']:x for x in v.entries['chants']};verified=[]
        for variant,original_entry in original_keys.items():
            for model in (False,True):
                for full in (False,True):
                    v.last_variant=None
                    with patch('voice.random.choice',return_value=original_entry):
                        chosen=v.choose(full,model)
                    expected=original_entry['full' if full else 'short']
                    verified.append(chosen['file']==expected['file'] and chosen['release']==expected['release']
                        and chosen['duration']==expected['duration'] and chosen['original_variant']==variant
                        and not chosen.get('generated',False))
        r['all_ten_original_cast_voices']=len(original_keys)==10 and all(verified)
        v.last_variant=None;e=Engine(now=400);e.action('cast',400);v.tick(e,dict(cfg,voice_full=False),400)
        short=v.pending;delay=e.cast_release-short['release'];before=len(played)
        v.tick(e,cfg,400+delay-.01);before_release=len(played)
        v.tick(e,cfg,400+delay+.01)
        r['model_enabled_cast_uses_original_short']=before_release==before and len(played)==before+1 and played[-1]['explosion_source']=='original'
        original=v.choose(model=False);r['original_voice_switch']=not original.get('generated',False)
        v.play=play;clip=bank['scenes']['greeting'][0]
        r['generated_real_playback']=v.play(clip,1,time.monotonic())
        time.sleep(.15)
        r['generated_subtitle']=v.caption()==clip['zh']
        r['generated_mouth_envelope']=v.level() is not None and (v.position() or 0)>.03
        v.stop();r['model_voice_checks_passed']=all(r.values());return r
    finally:v.stop()
