"""Local HTTP fixtures exercise real networking; no cloud credentials needed."""
import json,tempfile,threading,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from assistant_core import (ConfigStore,DEFAULT_CONFIG,local_reply,calculate,normalize_config,
    stream_answer,check_connection,Cancelled,safe_error,open_http)
from assistant_ui import AssistantDialog,AISettings

class Fixture(BaseHTTPRequestHandler):
    seen=[]
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path=='/redirect/models':
            self.send_response(302);self.send_header('Location','http://127.0.0.1:1/steal');self.end_headers();return
        payload={'models':[{'name':'test-model'}]} if self.path.endswith('/tags') else {'data':[{'id':'test-model'}]}
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(payload).encode())
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));self.seen.append((self.path,body,self.headers.get('Authorization')))
        model=body['model']
        if model=='auth-error':self.send_response(401);self.end_headers();return
        ollama=self.path.endswith('/api/chat');responses=self.path.endswith('/responses')
        self.send_response(200);self.send_header('Content-Type','application/x-ndjson' if ollama else 'text/event-stream');self.end_headers()
        def emit(obj):
            raw=json.dumps(obj,ensure_ascii=False)
            self.wfile.write(((raw+'\n') if ollama else ('data: '+raw+'\n\n')).encode());self.wfile.flush()
        try:
            for chunk in ('惠惠：','答案是 ','42。'):
                if model=='slow':time.sleep(.22)
                if ollama:emit(dict(message=dict(content=chunk),done=False))
                elif responses:emit(dict(type='response.output_text.delta',delta=chunk))
                else:emit(dict(choices=[dict(delta=dict(content=chunk),finish_reason=None)]))
            if model=='broken':return
            if ollama:emit(dict(done=True,message=dict(content='')))
            elif responses:emit(dict(type='response.completed'))
            else:self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass

def pump_until(predicate,timeout=3):
    end=time.monotonic()+timeout
    while not predicate() and time.monotonic()<end:QApplication.processEvents();time.sleep(.008)
    assert predicate(),'async UI timeout'

def check_assistant(pet,preview_path=None):
    r={};server=ThreadingHTTPServer(('127.0.0.1',0),Fixture);server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    def cfg(provider='compatible',model='test-model'):return dict(provider=provider,model=model,base_url=base+('/v1' if provider!='ollama' else ''))
    try:
        with tempfile.TemporaryDirectory() as folder:
            store=ConfigStore(folder);key='TEST-LOCAL-NOT-A-CLOUD-KEY'
            store.save(cfg(),key);r['dpapi_key_roundtrip']=store.key(store.load())==key and key.encode() not in store.secret.read_bytes() and key not in store.path.read_text()
            moved=cfg();moved['base_url']=base+'/other';r['key_bound_to_service']=store.key(moved)==''
            assert calculate('(128+64)*3')=='576';assert calculate('2^8')=='256';assert calculate('10%3')=='1'
            rejected=[]
            for expr in ('__import__("os").system("x")','9**999999','(1).__class__','10/0'):
                try:calculate(expr);rejected.append(False)
                except (ValueError,SyntaxError,ZeroDivisionError):rejected.append(True)
            r['bounded_calculator_no_eval']=all(rejected)
            r['local_clock_and_date']=('北京时间' in local_reply('现在几点').text and '星期' in local_reply('今天星期几').text)
            r['unknown_not_faked_ai']=local_reply('为什么天空是蓝色的？') is None
            bad=[]
            for url in ('http://example.com/v1','https://user:pass@example.com/v1','file:///tmp','https://example.com/v1?key=x'):
                try:normalize_config(dict(provider='compatible',model='x',base_url=url));bad.append(False)
                except ValueError:bad.append(True)
            r['endpoint_validation']=all(bad)
            chunks=[];expected='惠惠：答案是 42。';history=[dict(role='user',content='6*7是多少？')]
            for provider in ('compatible','ollama'):
                answer=stream_answer(cfg(provider),key,history,threading.Event(),chunks.append)
                r[provider+'_http_stream']=answer==expected
            # Exercise the real Responses payload/parser against a local HTTP
            # fixture while retaining the official endpoint lock in production.
            real_normalize=normalize_config
            with patch('assistant_core.normalize_config',side_effect=lambda c:dict(provider='openai',base_url=base+'/v1',model='test-model')):
                r['responses_http_stream']=stream_answer(dict(provider='openai'),key,history,threading.Event(),chunks.append)==expected
            response_body=next(body for path,body,auth in Fixture.seen if path.endswith('/responses'))
            r['responses_store_false']=response_body['store'] is False and response_body['stream'] is True and 'previous_response_id' not in response_body
            r['request_contains_only_explicit_chat']=response_body['input']==history and set(response_body)=={'model','instructions','input','stream','store','max_output_tokens'}
            r['connection_check']=all('连接成功' in check_connection(cfg(p),key) for p in ('compatible','ollama'))
            for name in ('http_auth_error_redacted','truncated_stream_detected','redirect_cannot_forward_key','cancel_before_request'):r[name]=False
            try:stream_answer(cfg(model='auth-error'),key,history,threading.Event(),lambda t:None)
            except Exception as exc:r['http_auth_error_redacted']='401' in safe_error(exc) and key not in safe_error(exc)
            try:stream_answer(cfg(model='broken'),key,history,threading.Event(),lambda t:None)
            except ValueError as exc:r['truncated_stream_detected']='不完整' in str(exc)
            try:open_http(base+'/redirect/models',key)
            except ValueError:r['redirect_cannot_forward_key']=True
            stop=threading.Event();stop.set()
            try:stream_answer(cfg(),key,history,stop,lambda t:None)
            except Cancelled:r['cancel_before_request']=True
            old_assistant=pet.assistant;pet.assistant=None
            dialog=AssistantDialog(pet,store);dialog.read_answers.setChecked(False);dialog.show()
            try:
                dialog.input.setPlainText('计算 (128+64)*3');QTest.keyClick(dialog.input,Qt.Key.Key_Return)
                r['chat_enter_calculator']='答案是 576' in dialog.transcript.toPlainText()
                dialog.input.setPlainText('释放爆裂魔法');dialog.send()
                with patch.object(pet,'action') as action:
                    r['interaction_requires_confirmation']=action.call_count==0 and not dialog.confirm.isHidden()
                    dialog.run_action();r['confirmed_interaction']=action.call_args.args==('cast',)
                dialog.input.setPlainText('1秒后提醒我测试提醒');dialog.send();dialog.run_action()
                pump_until(lambda:'提醒：测试提醒' in dialog.transcript.toPlainText(),2)
                r['timer_reminder_fires']='提醒：测试提醒' in dialog.transcript.toPlainText() and not dialog.reminders
                # A deliberately slow real HTTP stream must not block Qt's tick.
                store.save(cfg(model='slow'),key);dialog.configuration_changed();ticks=[];timer=QTimer();timer.timeout.connect(lambda:ticks.append(time.monotonic()));timer.start(20)
                dialog.input.setPlainText('测试真实后台问答');start=time.monotonic();dialog.send();send_ms=(time.monotonic()-start)*1000
                pump_until(lambda:not dialog.busy,3);timer.stop()
                r['network_runs_off_ui_thread']=send_ms<150 and len(ticks)>=8
                r['stream_rendered_and_context_saved']=expected in dialog.transcript.toPlainText() and dialog.history[-1]['content']==expected
                dialog.input.setPlainText('继续问答');dialog.send();dialog.cancel();before=dialog.transcript.toPlainText()
                pump_until(lambda:dialog.job.running==0,3)
                r['cancel_discards_stale_callbacks']=before==dialog.transcript.toPlainText() and not dialog.busy
                dialog.clear();r['clear_removes_conversation']=not dialog.history and not dialog.transcript.toPlainText()
                store.save(DEFAULT_CONFIG);dialog.configuration_changed();dialog.input.setPlainText('请解释量子力学');dialog.send()
                r['offline_mode_honest']='需要真正的 AI' in dialog.transcript.toPlainText()
                settings=AISettings(pet,store);settings.show();settings.provider.setCurrentIndex(settings.provider.findData('ollama'));settings.model.setText('test-model');settings.url.setText(base)
                settings.test_connection();pump_until(lambda:settings.test.isEnabled(),3)
                r['settings_check_connection']='连接成功' in settings.result.text();settings.save()
                r['settings_save_provider']=store.load()['provider']=='ollama'
                settings.close()
                if preview_path:
                    store.save(DEFAULT_CONFIG);dialog.clear();dialog.input.setPlainText('计算 (128+64)*3');dialog.send();dialog.input.setPlainText('通用问题请先点右上角 AI 设置');QApplication.processEvents();dialog.grab().save(str(preview_path))
            finally:dialog.close();dialog.deleteLater();pet.assistant=old_assistant
            store.forget_key();r['forget_key']=not store.secret.exists()
        r['assistant_checks_passed']=all(r.values());return r
    finally:server.shutdown();server.server_close()
