"""Small bilingual replies plus local, trained Japanese synthesis."""
import json,re,time,subprocess,os
from pathlib import Path
from urllib import request,error,parse
from assistant_core import ConfigStore,ROOT,PROMPT,compact_history,open_http,Cancelled
from megumin_persona import PERSONA
from collections import OrderedDict
import threading,base64,io,wave

JAPANESE_PROMPT=PERSONA+'''\n用户要求日语语音和中文字幕，输入文字或说话都使用相同人格。
只输出 JSON 对象 {"segments":[{"ja":"一句完整日语","zh":"对应中文"},{"ja":"第二句日语","zh":"对应中文"}]}。
自然地说一至三句，可按句子分段。不强迫用极短句，不用占位话抢先出声。整段日语最多220字符。必须用自然日语，但合法日语可只含汉字（如「焼肉！」），不必硬加假名。
中文对应翻译；动作描写只能放中文中，不合成动作说明。语音质量与自然情感优先，不能为速度破坏句子或改变含义。
实用问题先给准确有效信息；若需长代码/详解，给可用的简短要点并请用户关闭语音回复后索取完整版。
不得输出markdown、代码围栏或额外键。'''
def reply_object(raw):
    if not isinstance(raw,str) or len(raw)>12000:raise ValueError('AI 回复超过安全范围。')
    raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip())
    try:obj=json.loads(raw)
    except json.JSONDecodeError:
        # Tolerate an introductory line around one complete JSON object.
        start=raw.find('{')
        if start<0:raise ValueError('AI 未返回日语/中文对象。')
        try:obj,end=json.JSONDecoder().raw_decode(raw,start)
        except json.JSONDecodeError:raise ValueError('AI 日语/中文对象不完整。')
    if isinstance(obj,list):obj={'segments':obj}
    if not isinstance(obj,dict):raise ValueError('AI 回复不是有效对象。')
    return obj

def text_field(obj,names):
    value=next((obj[n] for n in names if n in obj),None)
    if type(value) in (int,float):value=str(value)
    return value.strip() if isinstance(value,str) else ''

def speakable_japanese(text):
    # Orthography check, NOT a language classifier. Japanese can be all Kanji,
    # half-width Katakana, or numbers. The AI is instructed to supply Japanese.
    return bool(re.search('[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f0-9]',text))

def parse_reply(raw,allow_text_only=False):
    obj=reply_object(raw)
    if allow_text_only and obj.get('speech_unavailable') is True:
        zh=text_field(obj,('zh',))
        if not zh or len(zh)>3000:raise ValueError('没有可保留的中文回答。')
        return dict(ja='',zh=zh,segments=[],speech_unavailable=True)
    segments=obj.get('segments',[obj])
    if isinstance(segments,dict):segments=[segments]
    if not isinstance(segments,list) or not 1<=len(segments)<=16:raise ValueError('日语回复结构无效。')
    normalized=[]
    for s in segments:
        if isinstance(s,dict) and not text_field(s,('ja','jp','japanese')) and not text_field(s,('zh','cn','chinese')):continue
        normalized.append(validate_segment(s))
    if not normalized:raise ValueError('AI 返回了空的日语/中文回答。')
    ja=''.join(s['ja'] for s in normalized);zh=''.join(s['zh'] for s in normalized)
    if len(ja)>240 or len(zh)>3000:raise ValueError('整段语音台词过长，需要整理。')
    return dict(ja=ja,zh=zh,segments=normalized)

def validate_segment(obj):
    if not isinstance(obj,dict):raise ValueError('日语回复格式无效。')
    ja=text_field(obj,('ja','jp','japanese'));zh=text_field(obj,('zh','cn','chinese'))
    if not ja or not zh or len(ja)>240 or len(zh)>1500 or not speakable_japanese(ja):raise ValueError('日语/中文台词缺失或超出合成范围。')
    return dict(ja=ja,zh=zh)

class SegmentParser:
    def __init__(self,emit):self.raw='';self.cursor=None;self.segments=[];self.emit=emit;self.early=set()
    def feed(self,delta):
        self.raw+=delta
        if len(self.raw)>12000:raise ValueError('日语回复超过范围。')
        if self.cursor is None:
            match=re.search(r'"segments"\s*:\s*\[',self.raw)
            if not match:return
            self.cursor=match.end()
        while True:
            pos=self.cursor
            while pos<len(self.raw) and self.raw[pos] in ' \r\n\t,':pos+=1
            if pos>=len(self.raw) or self.raw[pos]==']':return
            # Start synthesis when a complete JA string arrives, before its
            # Chinese translation finishes generating. No invented filler.
            index=len(self.segments)
            match=re.match(r'\{\s*"ja"\s*:\s*',self.raw[pos:])
            if match and index not in self.early:
                try:ja,end=json.JSONDecoder().raw_decode(self.raw,pos+match.end())
                except json.JSONDecodeError:pass
                else:
                    if isinstance(ja,str) and 1<=len(ja)<=120 and re.search('[\u3040-\u30ff]',ja):
                        self.early.add(index);self.emit(json.dumps(dict(kind='ja_ready',index=index,ja=ja),ensure_ascii=False))
            try:obj,end=json.JSONDecoder().raw_decode(self.raw,pos)
            except json.JSONDecodeError:return
            segment=validate_segment(obj)
            if len(self.segments)>=3:raise ValueError('日语回复超过三段。')
            self.cursor=end;self.segments.append(segment);self.emit(json.dumps(dict(segment,index=index),ensure_ascii=False))

def bilingual_answer(cfg,key,history,cancel,on_delta,context=''):
    from assistant_core import stream_answer
    parser=SegmentParser(on_delta)
    failed_preview=False
    def preview(delta):
        nonlocal failed_preview
        if failed_preview:return
        try:parser.feed(delta)
        except (ValueError,TypeError,KeyError):failed_preview=True
    # DeepSeek documents occasional empty content in forced JSON mode. Keep
    # the JSON instructions, but do not enable that mode for this provider.
    forced_json=parse.urlparse(cfg.get('base_url','')).hostname!='api.deepseek.com'
    raw=stream_answer(cfg,key,history,cancel,preview,system_prompt=JAPANESE_PROMPT+context,max_output_tokens=1024,json_mode=forced_json,delta_interval=0)
    try:reply=parse_reply(raw)
    except (ValueError,TypeError):
        if cancel.is_set():raise Cancelled()
        repair_prompt=JAPANESE_PROMPT+context+'\n上一条返回结构不合格。请保留回答含义，只整理成合法的日语/中文 JSON；不得将中文填进ja，不要空段，不要附加解释。'
        repair_history=compact_history(history+[dict(role='assistant',content=raw[:9000]),dict(role='user',content='整理上一条回复的格式，保留自然日语和对应中文。')])
        try:
            fixed=stream_answer(cfg,key,repair_history,cancel,lambda text:None,system_prompt=repair_prompt,max_output_tokens=1024,json_mode=forced_json,delta_interval=0)
            reply=parse_reply(fixed);reply['format_repaired']=True
        except Cancelled:raise
        except Exception:
            # A bad speech field must not erase usable written content or
            # substitute an unrelated/Chinese voice. One repair attempt only.
            zh=extract_chinese(raw)
            if not zh:raise ValueError('AI 返回格式异常，自动整理仍未得到可用回答。请重试；无需关闭语音。')
            return json.dumps(dict(ja='',zh=zh,segments=[],speech_unavailable=True),ensure_ascii=False)
    if not parser.segments:
        for segment in reply.get('segments',[dict(ja=reply['ja'],zh=reply['zh'])]):on_delta(json.dumps(segment,ensure_ascii=False))
    return json.dumps(reply,ensure_ascii=False)

def extract_chinese(raw):
    try:
        obj=reply_object(raw);items=obj.get('segments',[obj]);items=[items] if isinstance(items,dict) else items
        zh=''.join(text_field(s,('zh','cn','chinese')) for s in items if isinstance(s,dict))
        if zh:return zh[:3000]
    except (ValueError,TypeError):pass
    values=[]
    for match in re.finditer(r'"(?:zh|cn|chinese)"\s*:\s*("(?:\\.|[^"\\])*")',raw[:12000]):
        try:values.append(json.loads(match.group(1)))
        except ValueError:pass
    return ''.join(values)[:3000]

class LocalJapaneseService:
    _cache=OrderedDict();_lock=threading.Lock()
    def __init__(self):self.config_path=ROOT/'speech-runtime-v16.json';self.process=None;self.start_lock=threading.Lock();self.last_metrics={}
    def health(self):
        try:
            with request.urlopen('http://127.0.0.1:18893/health',timeout=1) as r:obj=json.load(r)
            return bool(obj.get('ready')) and obj.get('engine')=='user-trained-v2ProPlus' and obj.get('revision')==16 and obj.get('quality_profile')=='natural_full_reply'
        except Exception:return False
    def ensure(self,cancel):
        if self.health():return
        try:cfg=json.loads(self.config_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):raise ValueError('未配置惠惠日语模型服务，请运行随包的语音环境配置脚本。')
        with self.start_lock:
            if self.health():return
            if self.process is None or self.process.poll() is not None:
                python=Path(cfg['python']);script=Path(cfg['script'])
                if not python.is_file() or not script.is_file():raise ValueError('日语推理环境不存在，请检查语音环境配置。')
                self.process=subprocess.Popen([str(python),str(script)],cwd=str(script.parent),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        started=time.monotonic()
        while time.monotonic()-started<120:
            if cancel.is_set():raise Cancelled()
            if self.health():return
            if self.process.poll() is not None:raise ValueError('日语模型服务启动失败，请检查本地模型和推理环境。')
            time.sleep(.3)
        raise ValueError('日语模型仍在加载，请稍后重试。')
    def synthesize(self,text,cancel):
        if cancel.is_set():raise Cancelled()
        with self._lock:
            if text in self._cache:
                self._cache.move_to_end(text);self.last_metrics={'cache':'memory','seconds':0};return self._cache[text]
        self.ensure(cancel)
        req=request.Request('http://127.0.0.1:18893/tts',data=json.dumps(dict(text=text,accelerated=False,quality_profile='natural_full_reply'),ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json'})
        started=time.monotonic()
        for attempt in range(40):
            if cancel.is_set():raise Cancelled()
            try:
                with request.urlopen(req,timeout=60) as r:
                    raw=r.read(8*1024*1024+1);self.last_metrics={'cache':r.headers.get('X-Cache','miss'),'seconds':time.monotonic()-started}
                break
            except error.HTTPError as exc:
                if exc.code!=429 or attempt==39:raise
                cancel.wait(.15)
        if cancel.is_set():raise Cancelled()
        if len(raw)>8*1024*1024 or not raw.startswith(b'RIFF'):raise ValueError('日语语音合成没有返回有效 WAV。')
        with self._lock:
            self._cache[text]=raw
            while len(self._cache)>32 or sum(map(len,self._cache.values()))>12*1024*1024:self._cache.popitem(last=False)
        return raw
    def synthesize_chunks(self,text,cancel,emit):
        if cancel.is_set():raise Cancelled()
        with self._lock:cached=self._cache.get(text)
        if cached:emit(cached);return
        self.ensure(cancel)
        req=request.Request('http://127.0.0.1:18893/tts-stream',data=json.dumps(dict(text=text),ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
        chunks=[];total=0;done=False
        for attempt in range(80):
            if cancel.is_set():raise Cancelled()
            try:response=request.urlopen(req,timeout=60);break
            except error.HTTPError as exc:
                if exc.code!=429 or attempt==79:raise
                cancel.wait(.15)
        with response:
            while True:
                if cancel.is_set():raise Cancelled()
                line=response.readline(4*1024*1024+1)
                if not line:break
                if len(line)>4*1024*1024:raise ValueError('音频块超过范围。')
                obj=json.loads(line)
                if obj.get('error'):raise ValueError('日语流式合成失败。')
                if obj.get('done'):done=True;break
                raw=base64.b64decode(obj['wav'],validate=True);total+=len(raw)
                if total>8*1024*1024 or len(chunks)>=96 or not raw.startswith(b'RIFF'):raise ValueError('音频流超过范围。')
                chunks.append(raw);emit(raw)
        if not done or not chunks:raise ValueError('日语音频流未完成。')
        buff=io.BytesIO();frames=[];params=None
        for raw in chunks:
            with wave.open(io.BytesIO(raw),'rb') as w:
                if params is None:params=w.getparams()
                if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(params.nchannels,params.sampwidth,params.framerate):raise ValueError('音频格式中途改变。')
                frames.append(w.readframes(w.getnframes()))
        with wave.open(buff,'wb') as w:w.setparams(params);w.writeframes(b''.join(frames))
        with self._lock:
            self._cache[text]=buff.getvalue()
            while len(self._cache)>32 or sum(map(len,self._cache.values()))>12*1024*1024:self._cache.popitem(last=False)
    def prewarm(self):
        def run():
            try:self.ensure(threading.Event())
            except Exception:pass
        threading.Thread(target=run,name='MeguminVoicePrewarm',daemon=True).start()
    def close(self):
        if self.process is not None and self.process.poll() is None:self.process.terminate()
