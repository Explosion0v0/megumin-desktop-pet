"""Opt-in capture test and synthetic speech tests; never save microphone audio."""
import io,json,threading,time,wave
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QAudioFormat,QMediaDevices
from PySide6.QtCore import QTimer
from assistant_core import ConfigStore,DEFAULT_CONFIG,local_reply
from assistant_ui import AssistantDialog
from assistant_validation import pump_until
from speech_conversation import RecognitionWorker,PCMConverter

def check_speech(pet,fixture=None,capture=False,preview_path=None):
    import tempfile
    from app import Engine
    r={};old_assistant=pet.assistant;old_volume=pet.settings['voice_volume'];old_enabled=pet.settings['voice_enabled'];old_engine=pet.engine;pet.engine=Engine();pet.settings['voice_enabled']=True
    with tempfile.TemporaryDirectory() as folder:
        store=ConfigStore(folder);store.save(DEFAULT_CONFIG);dialog=AssistantDialog(pet,store);dialog.show();QApplication.processEvents()
        try:
            s=dialog.speech
            r['microphone_off_by_default']=not dialog.mic.isChecked() and not s.enabled and s.source is None and s.microphone_open_count==0
            r['separate_readout_toggle']=dialog.read_answers.isChecked() and dialog.mic is not dialog.read_answers
            r['simple_japanese_greeting']=local_reply('你好').scene=='greeting' and 'こんにちは' in local_reply('你好').ja
            fmt=QAudioFormat();fmt.setSampleRate(48000);fmt.setChannelCount(2);fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
            signal=(np.sin(np.arange(4800)*np.pi*2*440/48000)*.2).astype(np.float32);stereo=np.column_stack((signal,signal)).tobytes();converter=PCMConverter(fmt)
            converted=converter.convert(stereo[:1001])+converter.convert(stereo[1001:])
            r['device_pcm_conversion']=abs(len(converted)-3200)<=4 and np.abs(np.frombuffer(converted,dtype='<i2')).max()>1000
            dialog.mic.blockSignals(True);dialog.mic.setChecked(True);dialog.mic.blockSignals(False)
            with patch.object(s.speaker,'speak',return_value=True) as speak:
                dialog.send_voice('你好');r['voice_text_to_japanese_reply']=speak.call_count==1 and speak.call_args.args[1]=='greeting' and '我是惠惠' in dialog.transcript.toPlainText()
                dialog.read_answers.setChecked(False);dialog.send_voice('谢谢');r['readout_off_still_text']=speak.call_count==1 and '不用谢' in dialog.transcript.toPlainText()
                dialog.mic.setChecked(False);before=dialog.transcript.toPlainText();dialog.send_voice('你好');r['mic_off_ignores_voice_callbacks']=before==dialog.transcript.toPlainText()
            dialog.read_answers.setChecked(True)
            if fixture:
                ready=[];heard=[];worker=RecognitionWorker(dialog,s.model_path,101)
                worker.signals.ready.connect(lambda serial:ready.append(serial));worker.signals.final.connect(lambda serial,text:heard.append(text));worker.start()
                pump_until(lambda:bool(ready),12)
                with wave.open(str(fixture),'rb') as w:pcm=w.readframes(w.getnframes())
                pcm+=bytes(64000)
                for i in range(0,len(pcm),16000):worker.feed(pcm[i:i+16000])
                pump_until(lambda:bool(heard),12);worker.stop()
                r['real_local_asr_hello']='你好' in heard
            if capture:
                devices=QMediaDevices.audioInputs();r['microphone_device_detected']=bool(devices)
                s.enable(devices[0] if devices else None)
                pump_until(lambda:s.source is not None or not s.enabled,12)
                r['actual_microphone_opened']=s.enabled and s.source is not None
                if s.source:
                    pump_until(lambda:s.raw_bytes>0,4)
                    r['actual_microphone_receives_pcm']=s.raw_bytes>0
                    s.set_paused(True);r['reply_pauses_capture']=s.paused and s.worker.paused.is_set()
                else:r['actual_microphone_receives_pcm']=r['reply_pauses_capture']=False
                s.disable();count=s.raw_bytes
                end=time.monotonic()+.2
                while time.monotonic()<end:QApplication.processEvents();time.sleep(.01)
                r['off_releases_device_and_stops_pcm']=not s.enabled and s.source is None and s.raw_bytes==count
            # Verify a memory WAV reply uses existing waveOut and mouth envelope.
            samples=(np.sin(np.arange(8000)*np.pi*2*260/16000)*.12*32767).astype('<i2');buff=io.BytesIO()
            with wave.open(buff,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(samples.tobytes())
            r['in_memory_japanese_playback']=pet.voice.play_generated(buff.getvalue(),'こんにちは。','你好。',1,time.monotonic()) and bool(pet.voice.clip['envelope']) and pet.voice.clip['ja']=='こんにちは。'
            pet.voice.stop()
            trained=pet.voice.generated['scenes']['greeting'][0]
            real_wav=(pet.voice.folder/trained['file']).read_bytes()
            with patch('japanese_reply.LocalJapaneseService.synthesize',return_value=real_wav):
                s.reply(trained['zh'],ja=trained['ja'])
                pump_until(lambda:not s.speaker.waiting,3)
                r['async_trained_japanese_reply']=bool(pet.voice.clip and pet.voice.clip['ja']==trained['ja'] and pet.voice.clip['file']=='<in-memory-reply>')
            pet.voice.stop()
            # Never feed newly heard text to cloud after the dialog is closed.
            dialog.mic.blockSignals(True);dialog.mic.setChecked(True);dialog.mic.blockSignals(False);dialog.close()
            r['closing_dialog_stops_listening']=not dialog.mic.isChecked() and not s.enabled and s.source is None
            dialog.show();dialog.reject();r['escape_stops_listening']=not s.enabled and not dialog.mic.isChecked()
            if preview_path:
                dialog.show();dialog.clear();dialog.input.setPlainText('你好');dialog.send();QApplication.processEvents();dialog.grab().save(str(preview_path))
            r={key:bool(value) for key,value in r.items()};r['speech_checks_passed']=all(r.values());return r
        finally:s.disable();pet.voice.stop();dialog.close();dialog.deleteLater();pet.assistant=old_assistant;pet.settings['voice_volume']=old_volume;pet.settings['voice_enabled']=old_enabled;pet.engine=old_engine
