"""Offline PCM playback through a private Windows waveOut stream."""
import ctypes
import json
import math
from pathlib import Path
import random
import wave
import io
import numpy as np
from spell_scene import CAST_RELEASE,CAST_DURATION

class WaveFormat(ctypes.Structure):
    _pack_=2
    _fields_=[('tag',ctypes.c_ushort),('channels',ctypes.c_ushort),('rate',ctypes.c_uint32),
              ('bytes_per_second',ctypes.c_uint32),('alignment',ctypes.c_ushort),('bits',ctypes.c_ushort),('extra',ctypes.c_ushort)]

class WaveHeader(ctypes.Structure):
    _fields_=[('data',ctypes.c_void_p),('length',ctypes.c_uint32),('recorded',ctypes.c_uint32),
              ('user',ctypes.c_size_t),('flags',ctypes.c_uint32),('loops',ctypes.c_uint32),
              ('next',ctypes.c_void_p),('reserved',ctypes.c_size_t)]

class PositionValue(ctypes.Union):
    _fields_=[('samples',ctypes.c_uint32),('bytes',ctypes.c_uint32),('storage',ctypes.c_ubyte*8)]
class Position(ctypes.Structure):
    _fields_=[('type',ctypes.c_uint32),('value',PositionValue)]

class VoicePlayer:
    def __init__(self,folder):
        self.folder=Path(folder);self.entries=json.loads((self.folder/'manifest.json').read_text(encoding='utf-8'))
        generated=self.folder/'generated/manifest.json'
        self.generated=json.loads(generated.read_text(encoding='utf-8')) if generated.exists() else None
        outfits=self.folder/'costumes/manifest.json'
        self.costumes=json.loads(outfits.read_text(encoding='utf-8')) if outfits.is_file() else None
        self.source_model=bool(self.generated);self.seen_action=None;self.last_scene={}
        self.api=ctypes.WinDLL('winmm');self.handle=ctypes.c_void_p();self.buffer=None;self.header=None
        self.clip=None;self.started=0;self.error='';self.history=[];self.last_variant=None
        self.queued_headers=[];self.stream_serial=None
        self.api.waveOutOpen.argtypes=[ctypes.POINTER(ctypes.c_void_p),ctypes.c_uint32,ctypes.POINTER(WaveFormat),ctypes.c_size_t,ctypes.c_size_t,ctypes.c_uint32]
        for name in ('waveOutPrepareHeader','waveOutUnprepareHeader','waveOutWrite'):
            getattr(self.api,name).argtypes=[ctypes.c_void_p,ctypes.POINTER(WaveHeader),ctypes.c_uint32]
        self.api.waveOutGetPosition.argtypes=[ctypes.c_void_p,ctypes.POINTER(Position),ctypes.c_uint32]
        self.api.waveOutReset.argtypes=[ctypes.c_void_p];self.api.waveOutClose.argtypes=[ctypes.c_void_p]
        self.seen_cast=None;self.pending=None;self.played_cast=False;self.seen_happy=None

    def choose(self,full=False,model=None):
        # Casting always uses the ten original anime recordings. The model
        # preference controls everyday dialogue only.
        candidates=self.entries['chants']
        choices=[x for x in candidates if x['id']!=self.last_variant] or candidates
        entry=random.choice(choices);self.last_variant=entry['id']
        clip=dict(entry['full' if full else 'short'])
        clip['explosion_source']='original';clip['original_variant']=entry['id']
        if not full:clip.update(ja='エクスプロージョン！',zh='爆裂魔法！')
        return clip

    def scene_clip(self,scene):
        candidates=self.generated['scenes'].get(scene,[]) if self.generated else []
        if not candidates:return None
        choices=[x for x in candidates if x['file']!=self.last_scene.get(scene)] or candidates
        entry=random.choice(choices);self.last_scene[scene]=entry['file'];return entry

    def costume_clip(self,costume):
        candidates=self.costumes['scenes'].get(costume,[]) if self.costumes else []
        if not candidates:return None
        scene='costume:'+costume
        choices=[x for x in candidates if x['file']!=self.last_scene.get(scene)] or candidates
        entry=random.choice(choices);self.last_scene[scene]=entry['file'];return entry

    def react_native(self,motion,e,settings,now):
        self.seen_action=('happy',e.since)
        if not settings.get('voice_model',True) or not settings.get('voice_enabled',True):return
        scene=motion.split('_')[1].lower();clip=self.scene_clip(scene)
        if clip:self.play(clip,settings['voice_volume'],now)

    def caption(self):
        if not self.clip or not self.header or self.header.flags&1:return ''
        cues=self.clip.get('captions')
        if cues:
            position=self.position() or 0
            return next((x['zh'] for x in reversed(cues) if position>=x['at']),'')
        return self.clip.get('zh','')

    def stop(self):
        if self.handle.value:
            self.api.waveOutReset(self.handle)
            for header,buffer in self.queued_headers:
                self.api.waveOutUnprepareHeader(self.handle,ctypes.byref(header),ctypes.sizeof(WaveHeader))
            if self.header and not self.queued_headers:self.api.waveOutUnprepareHeader(self.handle,ctypes.byref(self.header),ctypes.sizeof(WaveHeader))
            self.api.waveOutClose(self.handle)
        self.handle=ctypes.c_void_p();self.buffer=None;self.header=None;self.clip=None;self.queued_headers=[];self.stream_serial=None

    def play(self,clip,volume,now):
        return self._play(clip,volume,now,self.folder/clip['file'])

    def play_generated(self,wav_bytes,ja,zh,volume,now):
        with wave.open(io.BytesIO(wav_bytes),'rb') as w:
            rate=w.getframerate();channels=w.getnchannels();audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32).reshape(-1,channels).mean(axis=1)/32768
        size=max(1,rate//20);envelope=[min(.85,float(np.sqrt(np.mean(audio[i:i+size]**2)))*6) for i in range(0,len(audio),size)]
        clip=dict(file='<in-memory-reply>',ja=ja,zh=zh,duration=len(audio)/rate,envelope=envelope)
        return self._play(clip,volume,now,io.BytesIO(wav_bytes))

    def append_generated(self,wav_bytes,ja,zh,volume,now,serial):
        """Queue PCM on one waveOut device instead of reopening each audio chunk."""
        if not (self.handle.value and self.clip and self.clip.get('file')=='<in-memory-reply>' and self.stream_serial==serial):
            result=self.play_generated(wav_bytes,ja,zh,volume,now)
            if result:self.stream_serial=serial;self.clip['captions']=[dict(at=0,zh=zh)];self.stream_ja=ja
            return result
        try:
            with wave.open(io.BytesIO(wav_bytes),'rb') as w:
                if w.getsampwidth()!=2 or w.getframerate()!=self.rate or w.getnchannels()*2!=self.alignment:raise ValueError('音频流 PCM 格式改变')
                rate=w.getframerate();channels=w.getnchannels();original=w.readframes(w.getnframes())
            data=(np.frombuffer(original,dtype='<i2').astype(np.float32)*max(0,min(100,volume))/100).astype('<i2').tobytes()
            buffer=ctypes.create_string_buffer(data);header=WaveHeader(ctypes.cast(buffer,ctypes.c_void_p),len(data),0,0,0,0,None,0)
            for name in ('waveOutPrepareHeader','waveOutWrite'):
                code=getattr(self.api,name)(self.handle,ctypes.byref(header),ctypes.sizeof(WaveHeader))
                if code:raise OSError(name+': '+str(code))
            self.queued_headers.append((header,buffer));self.header=header;self.buffer=buffer
            if ja!=self.stream_ja:
                self.clip['captions'].append(dict(at=self.clip['duration'],zh=zh));self.stream_ja=ja
            self.clip['ja']=ja;self.clip['zh']=zh
            samples=np.frombuffer(original,dtype='<i2').astype(np.float32).reshape(-1,channels).mean(axis=1)/32768
            size=max(1,rate//20);self.clip['envelope'].extend(min(.85,float(np.sqrt(np.mean(samples[i:i+size]**2)))*6) for i in range(0,len(samples),size))
            self.clip['duration']+=len(samples)/rate;return True
        except (ValueError,OSError,wave.Error) as exc:self.error=str(exc);self.stop();return False

    def _play(self,clip,volume,now,source):
        self.stop();self.error=''
        if volume<=0:return False
        try:
            with wave.open(str(source) if isinstance(source,Path) else source,'rb') as w:
                if w.getsampwidth()!=2 or w.getcomptype()!='NONE':raise ValueError('语音需要 PCM16 格式')
                channels=w.getnchannels();rate=w.getframerate();original=w.readframes(w.getnframes())
            # Attenuate samples rather than changing the user's system volume.
            gain=max(0,min(100,volume))/100
            data=(np.frombuffer(original,dtype='<i2').astype(np.float32)*gain).astype('<i2').tobytes()
            fmt=WaveFormat(1,channels,rate,rate*channels*2,channels*2,16,0)
            code=self.api.waveOutOpen(ctypes.byref(self.handle),0xffffffff,ctypes.byref(fmt),0,0,0)
            if code:raise OSError(f'waveOutOpen: {code}')
            self.buffer=ctypes.create_string_buffer(data);self.header=WaveHeader(ctypes.cast(self.buffer,ctypes.c_void_p),len(data),0,0,0,0,None,0)
            for name in ('waveOutPrepareHeader','waveOutWrite'):
                code=getattr(self.api,name)(self.handle,ctypes.byref(self.header),ctypes.sizeof(WaveHeader))
                if code:raise OSError(f'{name}: {code}')
            self.clip=clip;self.started=now;self.rate=rate;self.alignment=channels*2
            self.queued_headers=[(self.header,self.buffer)]
            self.history.append(clip['file']);self.history=self.history[-24:];return True
        except (OSError,ValueError,wave.Error) as exc:
            self.error=str(exc);self.stop();return False

    def position(self):
        if not self.handle.value:return None
        pos=Position();pos.type=2
        if self.api.waveOutGetPosition(self.handle,ctypes.byref(pos),ctypes.sizeof(pos)):return None
        if pos.type==2:return pos.value.samples/self.rate
        if pos.type==4:return pos.value.bytes/(self.rate*self.alignment)
        if pos.type==1:return pos.value.samples/1000
        return None

    def level(self):
        if not self.clip or not self.header:return None
        if self.header.flags&1:self.stop();return None
        position=self.position()
        if position is None:return None
        envelope=self.clip.get('envelope',[]);index=int(position*20)
        return envelope[index] if 0<=index<len(envelope) else 0

    def tick(self,e,settings,now,hidden=False):
        allowed=settings.get('voice_enabled',True) and settings.get('voice_volume',55)>0 and not hidden
        self.source_model=settings.get('voice_model',True) and bool(self.generated)
        if e.state=='cast' and self.seen_cast!=e.since:
            self.seen_cast=e.since;self.stop();self.played_cast=False
            full=settings.get('voice_full',False)
            self.pending=self.choose(full)
            if allowed and full:
                e.set_cast_timing(self.pending['release'],self.pending['duration']+.75)
            else:e.set_cast_timing(CAST_RELEASE,CAST_DURATION)
        if not allowed:
            self.stop();self.pending=None;self.played_cast=True;e.voice_mouth=None;return
        if self.source_model and e.state in self.generated['scenes'] and self.seen_action!=(e.state,e.since):
            self.seen_action=(e.state,e.since)
            clip=self.scene_clip(e.state)
            if clip and self.play(clip,settings['voice_volume'],now):e.until=max(e.until,now+clip['duration']+.25)
        elif not self.source_model and e.state=='happy' and self.seen_happy!=e.since:
            self.seen_happy=e.since
            if not self.clip:self.play(self.entries['happy'],settings['voice_volume'],now)
        if e.state=='cast' and self.pending and not self.played_cast:
            delay=max(0,e.cast_release-self.pending['release'])
            if now-e.since>=delay:
                self.played_cast=True;self.play(self.pending,settings['voice_volume'],now)
        elif e.state!='cast':self.pending=None
        e.voice_mouth=self.level()

    def preview(self,settings,now):
        return self.play(self.choose(settings.get('voice_full',False),settings.get('voice_model',True)),settings['voice_volume'],now)

    def greet(self,settings,now):
        if settings.get('voice_enabled',True) and settings.get('voice_volume',55)>0:
            clip=self.scene_clip('greeting') if settings.get('voice_model',True) and self.generated else self.entries['greeting']
            return self.play(clip,settings['voice_volume'],now)
        return False
