"""Opt-in local Mandarin ASR. Raw microphone audio stays in bounded RAM queues."""
import audioop,json,queue,re,threading,time
from pathlib import Path
import numpy as np
from PySide6.QtCore import QObject,Signal,QTimer
from PySide6.QtMultimedia import QAudioFormat,QAudioSource,QMediaDevices,QtAudio
from japanese_reply import LocalJapaneseService

def clean_text(text):
    return re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])','',str(text)).strip()[:500]

class PCMConverter:
    def __init__(self,fmt):self.fmt=fmt;self.state=None;self.remainder=b''
    def convert(self,data):
        size=self.fmt.bytesPerFrame();raw=self.remainder+data;cut=len(raw)//size*size;raw,self.remainder=raw[:cut],raw[cut:]
        if not raw:return b''
        types={QAudioFormat.SampleFormat.Float:np.float32,QAudioFormat.SampleFormat.Int32:np.int32,QAudioFormat.SampleFormat.Int16:np.int16,QAudioFormat.SampleFormat.UInt8:np.uint8}
        dtype=types.get(self.fmt.sampleFormat())
        if dtype is None:raise ValueError('麦克风格式不受支持。')
        samples=np.frombuffer(raw,dtype=dtype).astype(np.float32).reshape(-1,self.fmt.channelCount())
        if dtype==np.float32:samples*=32767
        elif dtype==np.int32:samples/=65536
        elif dtype==np.uint8:samples=(samples-128)*256
        mono=np.clip(samples.mean(axis=1),-32768,32767).astype('<i2').tobytes()
        if self.fmt.sampleRate()!=16000:mono,self.state=audioop.ratecv(mono,2,1,self.fmt.sampleRate(),16000,self.state)
        return mono

class RecognitionSignals(QObject):
    ready=Signal(int);partial=Signal(int,str);final=Signal(int,str);failed=Signal(int,str)

class RecognitionWorker:
    def __init__(self,owner,model_path,serial):
        self.signals=RecognitionSignals(owner);self.model_path=str(model_path);self.serial=serial
        self.stop_event=threading.Event();self.paused=threading.Event();self.reset=threading.Event();self.packets=queue.Queue(maxsize=16)
    def start(self):threading.Thread(target=self.run,name='MeguminLocalASR',daemon=True).start()
    def feed(self,data):
        if self.paused.is_set() or self.stop_event.is_set():return
        try:self.packets.put_nowait(data)
        except queue.Full:
            self.clear();self.reset.set()
    def clear(self):
        while True:
            try:self.packets.get_nowait()
            except queue.Empty:break
    def pause(self,value):
        if value:self.paused.set()
        else:self.paused.clear()
        self.clear();self.reset.set()
    def stop(self):self.stop_event.set();self.clear()
    def run(self):
        try:
            import vosk
            vosk.SetLogLevel(-1);model=vosk.Model(self.model_path);recognizer=vosk.KaldiRecognizer(model,16000)
            if self.stop_event.is_set():return
            self.signals.ready.emit(self.serial);elapsed=0;voiced=0;last=0;last_partial=''
            while not self.stop_event.is_set():
                if self.reset.is_set():recognizer.Reset();elapsed=voiced=0;last_partial='';self.reset.clear()
                try:data=self.packets.get(timeout=.12)
                except queue.Empty:continue
                if self.paused.is_set():continue
                duration=len(data)/32000;rms=audioop.rms(data,2)/32768
                if rms>.006:voiced+=duration
                if voiced:elapsed+=duration
                complete=recognizer.AcceptWaveform(data)
                force=elapsed>=9
                if complete or force:
                    obj=json.loads(recognizer.Result() if complete else recognizer.FinalResult());text=clean_text(obj.get('text',''))
                    recognizer.Reset();enough=voiced>=.12;elapsed=voiced=0;last_partial=''
                    if text and enough:
                        self.pause(True);self.signals.final.emit(self.serial,text)
                elif time.monotonic()-last>.25:
                    text=clean_text(json.loads(recognizer.PartialResult()).get('partial',''));last=time.monotonic()
                    if text!=last_partial:last_partial=text;self.signals.partial.emit(self.serial,text)
        except Exception:
            if not self.stop_event.is_set():
                try:self.signals.failed.emit(self.serial,'本地语音识别启动失败。检查识别模型与运行库；麦克风已关闭。')
                except RuntimeError:pass

class GeneratedReplySignals(QObject):
    ready=Signal(int,bytes,str,str);failed=Signal(int,str);complete=Signal(int)

class ReplySpeaker(QObject):
    status=Signal(str)
    quality_profile='natural_full_reply'
    def __init__(self,pet,parent):
        super().__init__(parent);self.pet=pet;self.waiting=False;self.last_spoken='';self.error='';self.serial=0;self.cancel=threading.Event()
        self.service=LocalJapaneseService();self.signals=GeneratedReplySignals(self)
        self.signals.ready.connect(self.on_ready);self.signals.failed.connect(self.on_failed)
        self.signals.complete.connect(self.on_complete)
        self.pending=0;self.audio_queue=[];self.requests=None;self.first_audio_seconds=None;self.started=0;self.active_clip=None;self.translations={}
        self.pump_timer=QTimer(self);self.pump_timer.setInterval(30);self.pump_timer.timeout.connect(self.pump)
    def busy(self):return self.waiting
    def allowed(self):
        return not getattr(self.pet,'dialogue_quiet',False) and self.pet.settings.get('voice_enabled',True) and self.pet.settings.get('voice_volume',55)>0
    def begin(self):
        self.stop();self.error='';self.started=time.monotonic();self.first_audio_seconds=None
        self.requests=queue.Queue(maxsize=4);serial=self.serial;cancel=self.cancel;requests=self.requests
        self.pump_timer.start()
        def run():
            while not cancel.is_set():
                try:item=requests.get(timeout=.15)
                except queue.Empty:continue
                if item is None:return
                ja,zh=item
                try:
                    raw=self.service.synthesize(ja,cancel)
                    if not cancel.is_set():self.signals.ready.emit(serial,raw,ja,zh)
                    if not cancel.is_set():self.signals.complete.emit(serial)
                except Exception:
                    if not cancel.is_set():
                        try:self.signals.failed.emit(serial,'惠惠日语合成失败，已保留文字；未切换为其他声音。')
                        except RuntimeError:return
        threading.Thread(target=run,name='MeguminJapaneseSentenceQueue',daemon=True).start()
    def enqueue(self,ja,zh):
        if not self.allowed() or self.pet.engine.state=='cast':return False
        if not ja:return False
        if self.requests is None:self.begin()
        try:self.requests.put_nowait((ja,zh))
        except queue.Full:self.status.emit('语音队列已满，剩余内容保留文字。');return False
        self.pending+=1;self.waiting=True;self.pump_timer.start();return True
    def finish(self):
        if self.requests:
            try:self.requests.put_nowait(None)
            except queue.Full:pass
    def speak(self,text,scene=None,ja=None):
        if self.pet.engine.state=='cast' or not self.allowed():return False
        self.stop();self.last_spoken=text
        if scene=='greeting' and self.pet.settings.get('voice_enabled',True) and self.pet.settings.get('voice_volume',55)>0:
            bank=self.pet.voice.generated
            if bank and bank['scenes'].get('greeting'):
                result=self.pet.voice.play(bank['scenes']['greeting'][0],self.pet.settings['voice_volume'],time.monotonic());self.active_clip=self.pet.voice.clip
                return result
        if not ja:self.error='这条回复没有日语内容，已保留中文字幕，不改用中文语音。';self.status.emit(self.error);return False
        self.begin();result=self.enqueue(ja,text);self.finish()
        self.status.emit('惠惠正在自然合成整段日语……音质优先，请稍等。');return result
    def on_ready(self,serial,raw,ja,zh):
        if serial!=self.serial:return
        if len(self.audio_queue)>=96 or sum(len(x[0]) for x in self.audio_queue)+len(raw)>12*1024*1024:
            self.stop();self.error='音频队列超过范围，已停止朗读。';self.status.emit(self.error);return
        self.audio_queue.append((raw,ja,self.translations.get(ja,zh)));self.pump()
    def translate(self,ja,zh):
        self.translations[ja]=zh
        self.audio_queue=[(raw,j,self.translations.get(j,z)) for raw,j,z in self.audio_queue]
        voice=self.pet.voice
        if voice.clip and voice.clip.get('file')=='<in-memory-reply>' and voice.clip.get('ja')==ja:
            voice.clip['zh']=zh
            if voice.clip.get('captions'):voice.clip['captions'][-1]['zh']=zh
    def on_complete(self,serial):
        if serial!=self.serial:return
        self.pending=max(0,self.pending-1);self.pump()
    def pump(self):
        if not self.allowed():self.stop();return
        if self.pet.engine.state=='cast':self.stop();return
        voice=self.pet.voice
        playing=bool(voice.clip and voice.header and not voice.header.flags&1)
        if self.audio_queue and (not playing or self.active_clip is voice.clip):
            raw,ja,zh=self.audio_queue.pop(0)
            if voice.append_generated(raw,ja,zh,self.pet.settings.get('voice_volume',55),time.monotonic(),self.serial):
                self.active_clip=voice.clip
                if self.first_audio_seconds is None:self.first_audio_seconds=time.monotonic()-self.started
                self.status.emit('惠惠正在回答（日语 / 中文台词）')
        self.waiting=bool(self.pending or self.audio_queue)
        if not self.waiting:self.pump_timer.stop()
    def on_failed(self,serial,text):
        if serial!=self.serial:return
        self.pending=max(0,self.pending-1);self.waiting=bool(self.pending or self.audio_queue);self.error=text;self.status.emit(text)
    def stop(self):
        self.waiting=False;self.serial+=1;self.cancel.set();self.cancel=threading.Event()
        self.pending=0;self.audio_queue=[];self.requests=None;self.active_clip=None;self.translations={}
        if hasattr(self,'pump_timer'):self.pump_timer.stop()

class SpeechConversation(QObject):
    status=Signal(str);partial=Signal(str);heard=Signal(str);level=Signal(int);disabled=Signal()
    def __init__(self,dialog,pet,assets):
        super().__init__(dialog);self.dialog=dialog;self.pet=pet;self.model_path=Path(assets)/'speech/vosk-model-small-cn-0.22'
        self.enabled=False;self.serial=0;self.worker=None;self.source=None;self.device=None;self.converter=None
        self.paused=True;self.responding=False;self.hold_until=0;self.raw_bytes=0;self.microphone_open_count=0
        self.speaker=ReplySpeaker(pet,self);self.watch=QTimer(self);self.watch.setInterval(80);self.watch.timeout.connect(self.guard)
        self.speaker.status.connect(self.status)
    def enable(self,device):
        self.disable();self.enabled=True;self.serial+=1;self.device=device;self.paused=True
        self.status.emit('麦克风：准备本地中文识别（尚未采集）')
        self.worker=RecognitionWorker(self,self.model_path,self.serial)
        self.worker.signals.ready.connect(self.open_microphone);self.worker.signals.partial.connect(self.on_partial);self.worker.signals.final.connect(self.on_final);self.worker.signals.failed.connect(self.on_error)
        self.worker.start();self.watch.start()
    def open_microphone(self,serial):
        if not self.enabled or serial!=self.serial:return
        device=self.device or QMediaDevices.defaultAudioInput()
        if device.isNull():self.on_error(serial,'没有可用的麦克风。请连接麦克风并检查 Windows 麦克风权限。');return
        fmt=QAudioFormat();fmt.setSampleRate(16000);fmt.setChannelCount(1);fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):fmt=device.preferredFormat()
        self.converter=PCMConverter(fmt);self.source=QAudioSource(device,fmt,self);self.source.setBufferSize(max(4096,fmt.bytesForDuration(200000)))
        # PySide 6.11 exposes this signal as the old QAudio::State enum on
        # Windows. Poll error/state in guard instead of its broken conversion.
        self.io=self.source.start();self.microphone_open_count+=1
        if not self.enabled or self.source is None:return
        if self.io is None or self.source.error()!=QtAudio.Error.NoError:
            self.on_error(serial,'麦克风无法开启。请检查 Windows 隐私设置中的麦克风权限，或改选真实麦克风。');return
        self.io.readyRead.connect(self.read_audio);self.responding=False;self.set_paused(False);self.guard()
    def audio_state(self,state):
        if self.enabled and self.source and state==QtAudio.State.StoppedState and self.source.error()!=QtAudio.Error.NoError:
            self.on_error(self.serial,'麦克风设备错误或已被移除，监听已关闭。')
    def read_audio(self):
        if not self.enabled or not self.source:return
        raw=bytes(self.io.readAll());self.raw_bytes+=len(raw)
        if self.paused:return
        try:
            pcm=self.converter.convert(raw)
            if pcm:
                self.level.emit(min(100,int(audioop.rms(pcm,2)/32768*550)));self.worker.feed(pcm)
        except ValueError:self.on_error(self.serial,'麦克风音频格式无法转换，监听已关闭。')
    def set_paused(self,value):
        if not self.enabled:return
        if value==self.paused and self.source:return
        self.paused=value
        if self.worker:self.worker.pause(value)
        if self.source:
            if value:self.source.suspend();self.level.emit(0)
            else:
                if hasattr(self,'io'):self.io.readAll()
                self.converter.state=None;self.converter.remainder=b'';self.source.resume()
    def external_voice_busy(self):
        voice=self.pet.voice
        return bool(voice.clip and voice.header and not voice.header.flags&1)
    def guard(self):
        if not self.enabled or self.source is None:return
        if self.source.error()!=QtAudio.Error.NoError:
            self.on_error(self.serial,'麦克风设备错误或已被移除，监听已关闭。');return
        busy=self.dialog.busy or self.speaker.busy() or self.external_voice_busy() or self.pet.engine.state=='cast' or time.monotonic()<self.hold_until
        self.set_paused(busy)
        if busy:self.status.emit('麦克风：暂停收音（思考 / 回复 / 演出）')
        else:self.responding=False;self.status.emit('麦克风：正在听 · 本地中文识别，说完停顿即可发送')
    def on_partial(self,serial,text):
        if self.enabled and serial==self.serial and not self.paused:self.partial.emit(text)
    def on_final(self,serial,text):
        if not self.enabled or serial!=self.serial:return
        self.set_paused(True);self.responding=True;self.hold_until=time.monotonic()+.9;self.partial.emit(text);self.heard.emit(text)
    def reply(self,text,scene=None,ja=None):
        self.hold_until=time.monotonic()+.8;self.set_paused(True)
        if not self.speaker.speak(text,scene,ja):
            if self.speaker.error:self.status.emit(self.speaker.error)
    def stop_reply(self):
        self.speaker.stop()
        if self.pet.engine.state!='cast':self.pet.voice.stop()
        self.hold_until=time.monotonic()+.5
    def on_error(self,serial,message):
        if serial!=self.serial:return
        self.disable();self.status.emit(message);self.disabled.emit()
    def disable(self,stop_reply=True):
        self.enabled=False;self.serial+=1;self.watch.stop();self.paused=True;self.responding=False
        if self.worker:self.worker.stop();self.worker=None
        if self.source:
            try:self.io.readyRead.disconnect(self.read_audio)
            except (RuntimeError,TypeError):pass
            self.source.stop();self.source.deleteLater();self.source=None
        self.converter=None
        if stop_reply:self.speaker.stop()
        self.level.emit(0);self.partial.emit('');self.status.emit('麦克风：关闭（未采集）')
