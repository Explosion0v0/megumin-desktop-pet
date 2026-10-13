"""Real HTTP regression: empty/whitespace/thought-only responses are not answers."""
import json,threading,tempfile
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from assistant_core import stream_answer,ConfigStore,EmptyAIReply,Cancelled,open_http
from japanese_reply import bilingual_answer
from assistant_ui import AssistantDialog
from assistant_validation import pump_until
GOOD=json.dumps({'ja':'私は十四歳ですよ。','zh':'我十四岁哦。'},ensure_ascii=False)
class EmptyFixture(BaseHTTPRequestHandler):
    seen=[]
    def log_message(self,*args):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));self.seen.append(body)
        model=body['model'];count=sum(b['model']==model for b in self.seen)
        if model=='auth':self.send_response(401);self.end_headers();return
        empty=count==1 or model=='always_empty'
        if model=='parts':empty=False
        if not body['stream']:
            raw=json.dumps({'choices':[{'message':{'content':'' if model=='always_empty' else GOOD},'finish_reason':'stop'}]},ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw);return
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
        if model=='parts':delta={'content':[{'type':'text','text':'正常回复。'}]}
        elif model=='thought':delta={'reasoning_content':'PRIVATE_THOUGHT_DO_NOT_SHOW'}
        elif model=='whitespace':delta={'content':'   \n   '}
        elif model=='broken':delta={'content':'未完成'}
        else:delta={'content':'' if empty else GOOD}
        obj={'choices':[{'delta':delta,'finish_reason':None if model=='broken' else ('length' if model=='thought' else 'stop')}]}
        self.wfile.write(('data: '+json.dumps(obj,ensure_ascii=False)+'\n\n').encode());self.wfile.flush()
        if model!='broken':self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()

def check_empty_reply(pet):
    r={};s=ThreadingHTTPServer(('127.0.0.1',0),EmptyFixture);s.daemon_threads=True
    threading.Thread(target=s.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{s.server_port}'
    cfg=lambda m:dict(provider='compatible',base_url=url,model=m)
    history=[dict(role='user',content='你几岁了')]
    count=lambda m:sum(b['model']==m for b in EmptyFixture.seen)
    try:
        for model,label in [('empty','empty_stream_recovers'),('whitespace','whitespace_response_recovers'),('thought','thought_only_response_recovers')]:
            events=[];answer=stream_answer(cfg(model),'',history,threading.Event(),events.append,json_mode=True,max_output_tokens=650)
            bodies=[b for b in EmptyFixture.seen if b['model']==model]
            r[label]=answer==GOOD and len(bodies)==2 and bodies[1]['stream'] is False and 'response_format' not in bodies[1] and bodies[1]['max_tokens']>=1024
            if model=='thought':r['private_reasoning_never_used_as_answer']='PRIVATE_THOUGHT_DO_NOT_SHOW' not in answer and all('PRIVATE_THOUGHT_DO_NOT_SHOW' not in e for e in events)
        try:stream_answer(cfg('always_empty'),'',history,threading.Event(),lambda t:None);r['retry_is_bounded']=False
        except EmptyAIReply as exc:r['retry_is_bounded']=count('always_empty')==2 and '确认模型支持' not in str(exc)
        answer=stream_answer(cfg('parts'),'',history,threading.Event(),lambda t:None);r['content_blocks_supported']=answer=='正常回复。' and count('parts')==1
        try:stream_answer(cfg('auth'),'',history,threading.Event(),lambda t:None);r['auth_failure_not_retried']=False
        except HTTPError:r['auth_failure_not_retried']=count('auth')==1
        try:stream_answer(cfg('broken'),'',history,threading.Event(),lambda t:None);r['partial_disconnect_not_replayed']=False
        except ValueError:r['partial_disconnect_not_replayed']=count('broken')==1
        stop=threading.Event();stop.set()
        try:stream_answer(cfg('cancel'),'',history,stop,lambda t:None);r['cancel_prevents_recovery']=False
        except Cancelled:r['cancel_prevents_recovery']=count('cancel')==0
        real_http=open_http
        def local_route(endpoint,key='',payload=None):return real_http(url+'/chat/completions','',payload)
        with patch('assistant_core.open_http',side_effect=local_route):
            answer=bilingual_answer(dict(provider='compatible',base_url='https://api.deepseek.com/v1',model='deepseek_fixture'),'',history,threading.Event(),lambda t:None)
        bodies=[b for b in EmptyFixture.seen if b['model']=='deepseek_fixture']
        r['deepseek_no_forced_json']=len(bodies)==2 and all('response_format' not in b for b in bodies) and all(b.get('thinking',{}).get('type')=='disabled' for b in bodies)
        r['bilingual_recovery_keeps_japanese']=json.loads(answer)['ja']=='私は十四歳ですよ。'
        old=pet.assistant
        with tempfile.TemporaryDirectory() as temp:
            store=ConfigStore(temp);store.save(cfg('ui_empty'));d=AssistantDialog(pet,store);pet.assistant=d
            try:
                with patch.object(d.speech.speaker,'speak',return_value=True) as speak:
                    d.input.setPlainText('你几岁了');d.send();pump_until(lambda:not d.busy,5)
                    r['age_question_ui_reply']=bool(d.history) and d.history[-1]['content']=='我十四岁哦。' and '我十四岁哦。' in d.transcript.toPlainText() and speak.call_count==1
                    r['recovery_keeps_mic_off']=d.speech.microphone_open_count==0 and not d.mic.isChecked()
                r['version_visible']='v20' in d.windowTitle()
            finally:d.close();d.deleteLater();pet.assistant=old
        r={k:bool(v) for k,v in r.items()};r['empty_reply_checks_passed']=all(r.values());return r
    finally:s.shutdown();s.server_close()
