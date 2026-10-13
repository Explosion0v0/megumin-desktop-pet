"""Real SSE fixtures + ordered native playback. Never reads the user's mic."""
import io,json,threading,time,wave,tempfile
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from assistant_core import ConfigStore,DEFAULT_CONFIG,PROMPT
from assistant_ui import AssistantDialog
from assistant_validation import pump_until
from japanese_reply import SegmentParser,bilingual_answer,parse_reply
from megumin_persona import program_context

class JapaneseFixture(BaseHTTPRequestHandler):
    seen=[]
    def log_message(self,*args):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));self.seen.append(body)
        parts=['{"segments":[','{"ja":"お疲れさまです。","zh":"辛苦了。"}',',','{"ja":"少し休みましょう。","zh":"稍微休息一下吧。"}',']}']
        ollama=self.path.endswith('/api/chat');responses=self.path.endswith('/responses')
        self.send_response(200);self.send_header('Content-Type','application/x-ndjson' if ollama else 'text/event-stream');self.end_headers()
        def emit(obj):
            data=json.dumps(obj,ensure_ascii=False);self.wfile.write((data+'\n' if ollama else 'data: '+data+'\n\n').encode());self.wfile.flush()
        try:
            for i,part in enumerate(parts):
                if i==3:time.sleep(.5)
                if ollama:emit(dict(message=dict(content=part),done=False))
                elif responses:emit(dict(type='response.output_text.delta',delta=part))
                else:emit(dict(choices=[dict(delta=dict(content=part),finish_reason=None)]))
            if ollama:emit(dict(message=dict(content=''),done=True))
            elif responses:emit(dict(type='response.completed'))
            else:self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass

def tiny_wave():
    buf=io.BytesIO();samples=(np.sin(np.arange(2400)*2*np.pi*280/16000)*3276).astype('<i2')
    with wave.open(buf,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(samples.tobytes())
    return buf.getvalue()

def check_persona(pet):
    r={};old=pet.assistant;old_engine=pet.engine;old_settings=pet.settings.copy()
    from app import Engine
    pet.engine=Engine();pet.dialogue_quiet=False;pet.settings.update(voice_enabled=True,voice_volume=1)
    server=ThreadingHTTPServer(('127.0.0.1',0),JapaneseFixture);server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
    try:
        events=[];p=SegmentParser(events.append)
        raw='{"segments":[{"ja":"私は天才ですよ。","zh":"我可是天才。"},{"ja":"少し休みましょう。","zh":"休息一下吧。"}]}'
        for char in raw:p.feed(char)
        r['incremental_json_parser']=len(events)==4 and parse_reply(raw)['ja']=='私は天才ですよ。少し休みましょう。'
        r['incremental_ja_parse_before_translation']=json.loads(events[0]).get('kind')=='ja_ready' and json.loads(events[1])['zh']=='我可是天才。'
        r['persona_complete']=all(t in PROMPT for t in ('不是笨蛋','主人','耗尽','不继承开发助手','每次一至三句','屏幕','亲密度高'))
        pet.engine.state='tired';r['exhausted_state_from_program']='"exhausted": true' in program_context(pet);pet.engine.state='idle'
        history=[dict(role='user',content='工作很累，陪我说两句话')]
        for provider in ('compatible','ollama','openai'):
            cfg=dict(provider=provider,model='fixture',base_url=url)
            emitted=[];start=time.monotonic()
            real_normalize=__import__('assistant_core').normalize_config
            with patch('assistant_core.normalize_config',side_effect=lambda c:dict(c,base_url=url)):
                answer=bilingual_answer(cfg,'LOCAL-FIXTURE-NOT-A-SECRET',history,threading.Event(),lambda s:emitted.append((time.monotonic()-start,s)),program_context(pet))
            parsed=parse_reply(answer);r[provider+'_bilingual_persona_stream']=len(emitted)==4 and parsed['zh']=='辛苦了。稍微休息一下吧。'
            r[provider+'_first_segment_before_completion']=emitted[0][0]<.4
            body=JapaneseFixture.seen[-1];system=body.get('instructions') or body['messages'][0]['content']
            r[provider+'_same_persona_and_program_state']='不是笨蛋' in system and '"state": "idle"' in system
        with tempfile.TemporaryDirectory() as folder:
            store=ConfigStore(folder);store.save(dict(provider='compatible',model='fixture',base_url=url))
            d=AssistantDialog(pet,store);pet.assistant=d;d.show();s=d.speech
            try:
                with patch.object(s.speaker,'speak',return_value=True) as speak:
                    d.input.setPlainText('你好');d.send();r['typed_greeting_japanese']=speak.call_count==1 and s.microphone_open_count==0
                    d.read_answers.setChecked(False);d.input.setPlainText('谢谢');d.send();r['typed_readout_switch']=speak.call_count==1
                d.read_answers.setChecked(True);seen=[];audio=tiny_wave();ticks=[];timer=QTimer();timer.timeout.connect(lambda:ticks.append(time.monotonic()));timer.start(20)
                real_play=pet.voice.append_generated;handles=[]
                def record_play(raw,ja,zh,volume,now,serial):
                    seen.append((ja,time.monotonic(),d.busy));result=real_play(raw,ja,zh,volume,now,serial);handles.append(pet.voice.handle.value);return result
                with patch('japanese_reply.LocalJapaneseService.synthesize',return_value=audio) as synth,patch.object(pet.voice,'append_generated',side_effect=record_play):
                    start=time.monotonic();d.input.setPlainText('工作很累，陪我说两句话');d.send()
                    pump_until(lambda:not d.busy,4);pump_until(lambda:len(seen)==1,4)
                    r['typed_ai_japanese_playback']=len(seen)==1 and s.microphone_open_count==0
                    r['quality_first_full_reply']=seen[0][2] is False and synth.call_count==1 and synth.call_args.args[0]=='お疲れさまです。少し休みましょう。' and s.speaker.quality_profile=='natural_full_reply'
                    r['no_fragmented_sentence_playback']=[x[0] for x in seen]==['お疲れさまです。少し休みましょう。']
                    # Retain the existing event-loop acceptance and record actual
                    # timing, including native render stalls, instead of hiding them.
                    elapsed=time.monotonic()-start
                    gaps=[b-a for a,b in zip([start]+ticks,ticks+[time.monotonic()])]
                    responsiveness=dict(elapsed_seconds=round(elapsed,4),timer_ticks=len(ticks),max_event_gap_seconds=round(max(gaps),4))
                    print('PERSONA_UI_TIMING '+json.dumps(responsiveness),flush=True)
                    r['no_ui_blocking']=len(ticks)>=12
                    r['chinese_subtitles']=d.history[-1]['content']=='辛苦了。稍微休息一下吧。'
                    pet.on_key('left',65);r['typing_does_not_cut_reply']=bool(pet.voice.clip and pet.voice.clip.get('file')=='<in-memory-reply>')
                    r['dialogue_defers_idle_actions']=pet.conversation_settings()['idle_enabled'] is False
                    pet.voice.stop();pet.voice.append_generated(audio,'一緒ですよ。','我陪着你。',1,time.monotonic(),808);handle=pet.voice.handle.value
                    pet.voice.append_generated(audio,'休みましょう。','休息一下吧。',1,time.monotonic(),808)
                    r['continuous_waveout_pcm_queue']=pet.voice.handle.value==handle and len(pet.voice.queued_headers)==2
                    d.input.setPlainText('测试停止');d.send();d.cancel();before=len(seen);pump_until(lambda:d.job.running==0,4)
                    r['cancel_discards_queued_audio']=len(seen)==before and not s.speaker.audio_queue and not s.speaker.pending
                timer.stop();d.input.setPlainText('安静一点');d.send()
                r['quiet_mutes_autonomous_voice']=pet.dialogue_quiet and not d.read_answers.isChecked() and not pet.conversation_settings()['voice_enabled'] and not pet.time_greeting(force=True)
                with patch.object(s.speaker,'speak',return_value=True):d.input.setPlainText('恢复语音');d.send()
                r['resume_restores_dialogue']=not pet.dialogue_quiet and d.read_answers.isChecked()
                d.close();r['close_clears_audio_queue']=not s.speaker.audio_queue and not s.speaker.pending
            finally:d.close();d.deleteLater()
        r={k:bool(v) for k,v in r.items()};r['persona_checks_passed']=all(r.values());return r
    finally:server.shutdown();server.server_close();pet.assistant=old;pet.engine=old_engine;pet.settings=old_settings;pet.dialogue_quiet=False;pet.voice.stop()
