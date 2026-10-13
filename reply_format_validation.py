"""Regression fixtures for the user's food question and speech schema recovery."""
import json,threading,tempfile
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from assistant_core import ConfigStore,Cancelled
from japanese_reply import parse_reply,bilingual_answer
from assistant_ui import AssistantDialog
from assistant_validation import pump_until

class FormatFixture(BaseHTTPRequestHandler):
    calls=[]
    def log_message(self,*args):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));self.calls.append(body)
        repair=body['messages'][-1]['content']=='整理上一条回复的格式，保留自然日语和对应中文。'
        if body['model']=='kanji':obj={'segments':[{'ja':'焼肉！','zh':'烤肉！'}]}
        elif body['model']=='repair' and repair:obj={'ja':'温かいご飯が好きですよ。','zh':'我喜欢热乎乎的饭菜。'}
        elif body['model']=='repair':obj={'segments':[{'ja':'ご飯。','zh':'旧的预览'},{'ja':'oops','zh':'我喜欢热乎乎的饭菜。'}]}
        else:obj={'segments':[{'ja':'','zh':'我喜欢热乎乎的饭菜。'}]}
        raw=json.dumps(obj,ensure_ascii=False);self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
        try:
            for i in range(0,len(raw),7):
                data=json.dumps({'choices':[{'delta':{'content':raw[i:i+7]},'finish_reason':None}]},ensure_ascii=False)
                self.wfile.write(('data: '+data+'\n\n').encode());self.wfile.flush()
            self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass

def check_reply_format(pet):
    r={};cases={
        'kanji_only_japanese':{'segments':[{'ja':'焼肉！','zh':'烤肉！'}]},
        'numeric_japanese':{'ja':'42。','zh':'42。'},
        'halfwidth_katakana':{'ja':'ﾊﾟﾝ！','zh':'面包！'},
        'trailing_empty_segment':{'segments':[{'ja':'好きですよ。','zh':'我喜欢。'},{'ja':'','zh':''}]},
        'legacy_and_alias_keys':{'jp':'好きですよ。','cn':'我喜欢。'},
        'long_but_speakable_segment':{'segments':[{'ja':'好きですよ。'*22,'zh':'我喜欢。'}]},
        'more_than_three_short_segments':{'segments':[{'ja':'好き。','zh':'喜欢。'}]*4}}
    for name,obj in cases.items():r[name]=bool(parse_reply(json.dumps(obj,ensure_ascii=False))['ja'])
    r['json_fence_tolerated']=parse_reply('```json\n{"ja":"好きですよ。","zh":"我喜欢。"}\n```')['zh']=='我喜欢。'
    try:parse_reply(json.dumps({'ja':'あ'*241,'zh':'过长'}));r['tts_size_bound_preserved']=False
    except ValueError:r['tts_size_bound_preserved']=True
    server=ThreadingHTTPServer(('127.0.0.1',0),FormatFixture);server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
    cfg=lambda model:dict(provider='compatible',model=model,base_url=url)
    try:
        history=[dict(role='user',content='你喜欢吃什么')]
        start=len(FormatFixture.calls);reply=json.loads(bilingual_answer(cfg('repair'),'',history,threading.Event(),lambda t:None))
        r['one_automatic_format_repair']=len(FormatFixture.calls)-start==2 and reply.get('format_repaired') and reply['zh']=='我喜欢热乎乎的饭菜。'
        start=len(FormatFixture.calls);reply=json.loads(bilingual_answer(cfg('fallback'),'',history,threading.Event(),lambda t:None))
        r['failed_speech_keeps_chinese']=len(FormatFixture.calls)-start==2 and reply.get('speech_unavailable') and reply['zh']=='我喜欢热乎乎的饭菜。' and reply['ja']==''
        stop=threading.Event()
        def cancel_bad(*args,**kwargs):stop.set();return '{"ja":"","zh":"原回答"}'
        with patch('assistant_core.stream_answer',side_effect=cancel_bad) as mocked:
            try:bilingual_answer(cfg('repair'),'',history,stop,lambda t:None);r['cancel_prevents_repair']=False
            except Cancelled:r['cancel_prevents_repair']=mocked.call_count==1
        old=pet.assistant
        with tempfile.TemporaryDirectory() as folder:
            store=ConfigStore(folder);store.save(cfg('kanji'));d=AssistantDialog(pet,store);pet.assistant=d
            try:
                for model,label,expected,spoken in [('kanji','food_question_reply','烤肉！',True),('repair','repaired_ui_renders_canonical_reply','我喜欢热乎乎的饭菜。',True),('fallback','fallback_ui_not_blank','我喜欢热乎乎的饭菜。',False)]:
                    store.save(cfg(model));d.clear()
                    with patch.object(d.speech.speaker,'speak',return_value=True) as speak:
                        d.input.setPlainText('你喜欢吃什么');d.send();pump_until(lambda:not d.busy,4)
                        transcript=d.transcript.toPlainText();r[label]=expected in transcript and '旧的预览' not in transcript and bool(d.history) and bool(speak.call_count)==spoken
                        if not r[label]:print('FORMAT_UI_FAILURE',label,json.dumps(dict(transcript=transcript,history=d.history,speak_calls=speak.call_count),ensure_ascii=False))
                        if model=='fallback':r['no_wrong_voice_fallback']=not speak.call_count and '已保留中文回答' in d.mic_status.text()
                r['repair_keeps_microphone_off']=d.speech.microphone_open_count==0 and not d.mic.isChecked()
            finally:d.close();d.deleteLater();pet.assistant=old
        r={k:bool(v) for k,v in r.items()};r['reply_format_checks_passed']=all(r.values());return r
    finally:server.shutdown();server.server_close()
