"""Explicit-message assistant; no desktop/key logging or executable AI tools."""
from __future__ import annotations
import ast,ctypes,ipaddress,json,math,operator,os,re,socket,threading,time
from dataclasses import dataclass
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib import request,error,parse

ROOT=Path(os.environ.get('APPDATA',str(Path.home())))/'MeguminDesktopPet'
DEFAULT_CONFIG={'provider':'offline','base_url':'','model':''}
PROVIDERS={'offline':'本地小助手（无需 AI）','openai':'OpenAI Responses','compatible':'兼容 OpenAI 的 API','ollama':'Ollama 本地模型'}
from megumin_persona import PERSONA
PROMPT=PERSONA+'\n此通道使用中文回答。'

def normalize_config(cfg):
    provider=cfg.get('provider','offline')
    if provider not in PROVIDERS:raise ValueError('请选择有效的 AI 类型。')
    if provider=='offline':return DEFAULT_CONFIG.copy()
    url=str(cfg.get('base_url','')).strip().rstrip('/')
    if provider=='openai':url='https://api.openai.com/v1'
    elif provider=='ollama' and not url:url='http://127.0.0.1:11434'
    parts=parse.urlsplit(url)
    if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('接口地址必须是 http(s) URL，不得含用户名、密码、查询参数。')
    if parts.scheme=='http':
        host=parts.hostname.lower()
        try:local=ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback
        except ValueError:local=host=='localhost'
        if not local:raise ValueError('公网接口必须使用 HTTPS；HTTP 只允许本机或内网 IP。')
    if len(url)>1024:raise ValueError('接口地址过长。')
    model=str(cfg.get('model','')).strip()
    if not model or len(model)>200 or any(ord(c)<32 for c in model):raise ValueError('请填写服务实际可用的模型名称。')
    return dict(provider=provider,base_url=url,model=model)

def identity(cfg):
    return [cfg['provider'],cfg['base_url']]

def validate_key(key):
    if not isinstance(key,str) or len(key)>8192 or any(ord(c)<32 or ord(c)>126 for c in key):raise ValueError('API Key 必须是无换行的 ASCII 文本，且长度不超过 8192。')
    return key

def dpapi(data,decrypt=False):
    if os.name!='nt':raise RuntimeError('安全密钥存储需要 Windows。')
    class Blob(ctypes.Structure):
        _fields_=[('size',ctypes.c_ulong),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buf=ctypes.create_string_buffer(data);source=Blob(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte)));out=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32')
    fn=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(Blob)];fn.restype=ctypes.c_int
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(out)):raise OSError('Windows 密钥保护失败。')
    try:return ctypes.string_at(out.data,out.size)
    finally:kernel.LocalFree(out.data)

class ConfigStore:
    def __init__(self,folder=ROOT):
        self.folder=Path(folder);self.path=self.folder/'assistant.json';self.secret=self.folder/'assistant-key.bin'
    def load(self):
        try:return normalize_config(json.loads(self.path.read_text(encoding='utf-8')))
        except (OSError,ValueError,TypeError,AttributeError):return DEFAULT_CONFIG.copy()
    def key(self,cfg):
        try:
            item=json.loads(dpapi(self.secret.read_bytes(),True).decode('utf-8'))
            return item['key'] if item.get('identity')==identity(cfg) else ''
        except (OSError,ValueError,KeyError,RuntimeError):return ''
    def save(self,cfg,key=None):
        cfg=normalize_config(cfg);self.folder.mkdir(parents=True,exist_ok=True)
        if key is not None:
            validate_key(key)
            data=dpapi(json.dumps(dict(identity=identity(cfg),key=key),ensure_ascii=False).encode('utf-8'))
            temp=self.secret.with_suffix('.tmp');temp.write_bytes(data);temp.replace(self.secret)
        temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(self.path)
        return cfg
    def forget_key(self):
        self.secret.unlink(missing_ok=True)

def calculate(expression):
    expression=expression.replace('×','*').replace('÷','/').replace('^','**')
    if len(expression)>200:raise ValueError('算式太长。')
    tree=ast.parse(expression,mode='eval')
    if sum(1 for _ in ast.walk(tree))>60:raise ValueError('算式太复杂。')
    ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Mod:operator.mod,ast.FloorDiv:operator.floordiv,ast.Pow:operator.pow}
    def visit(n):
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):value=n.value
        elif isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):value=visit(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
        elif isinstance(n,ast.BinOp) and type(n.op) in ops:
            a,b=visit(n.left),visit(n.right)
            if isinstance(n.op,ast.Pow) and (abs(b)>12 or abs(a)>1e12):raise ValueError('指数计算超过范围。')
            value=ops[type(n.op)](a,b)
        else:raise ValueError('仅支持数字、括号和 + - * / % ^。')
        if not isinstance(value,(int,float)) or not math.isfinite(value) or abs(value)>1e30:raise ValueError('结果超出范围。')
        return value
    value=visit(tree.body);return f'{value:.12g}' if isinstance(value,float) else str(value)

@dataclass
class LocalReply:
    text:str
    action:str|None=None
    seconds:int=0
    reminder:str=''
    scene:str|None=None
    ja:str|None=None

def local_reply(text):
    t=text.strip();flat=re.sub(r'[\s？?！!。]','',t)
    if flat.lower() in ('你好','您好','嗨','hello','hi','惠惠你好'):
        return LocalReply('你好，我是惠惠！今天也一起加油吧。',scene='greeting',ja='こんにちは、めぐみんです！今日も一緒に頑張りましょう。')
    if flat in ('你是谁','你叫什么','你叫什么名字'):
        return LocalReply('我是惠惠，红魔族的天才大魔法师！今天的冒险，也算你一份。',ja='私はめぐみん、紅魔族の天才魔法使いです！今日の冒険も一緒ですよ。')
    if flat in ('你好吗','今天你好吗','你今天好吗'):
        return LocalReply('我很好！只要能释放爆裂魔法，就会是美好的一天。你今天过得怎么样？',ja='元気ですよ！あなたは今日、どんな一日でしたか？')
    if flat in ('谢谢','谢谢你','感谢','多谢'):
        return LocalReply('不用谢，这不是同伴该做的事吗？有问题再叫我。',ja='どういたしまして。仲間なら当然ですよ！困ったらまた呼んでくださいね。')
    if flat in ('你真厉害','惠惠真厉害','你好厉害','你很厉害'):
        return LocalReply('当然！你总算发现红魔族天才的实力了。要欣赏魔法的话，请按程序里的展示按钮。',ja='当然です！紅魔族の天才の実力、やっとわかりましたね。')
    if flat in ('我好累','我累了','好累','我很累'):
        return LocalReply('辛苦了。先把手上的事情放下，喝点水、休息五分钟吧；我会在这里陪着你。',ja='お疲れさまです。少し水を飲んで、五分休みましょう。私はここにいますよ。')
    if flat in ('我去工作了','我要工作了','我先去忙了'):
        return LocalReply('去吧，把眼前这一件事做好就行。忙完再回来，我等你。',ja='いってらっしゃい。まずは目の前の一つからですよ。終わったら戻ってきてくださいね。')
    if flat in ('再见','拜拜','晚安'):
        return LocalReply('再见！记得休息，我们下次再一起冒险。',ja='また会いましょう！ちゃんと休んでくださいね。')
    if flat in ('几点了','现在几点','现在几点钟','时间','现在时间'):
        now=datetime.now(timezone(timedelta(hours=8)));return LocalReply(f'现在是北京时间 {now:%H:%M:%S}。别忘了休息一下！',ja=f'今は北京時間で{now.hour}時{now.minute}分です。')
    if flat in ('今天几号','今天星期几','今天日期','日期','今天是几月几号'):
        now=datetime.now(timezone(timedelta(hours=8)));return LocalReply(f'今天是 {now:%Y年%m月%d日}，星期'+ '一二三四五六日'[now.weekday()]+'（北京时间）。',ja=f'今日は{now.year}年{now.month}月{now.day}日、'+'月火水木金土日'[now.weekday()]+'曜日です。')
    if flat in ('帮助','你会什么','你能做什么','使用说明'):
        return LocalReply('我能报时、查日期、计算、设置本次运行的提醒，以及控制桌宠互动。\n试试：计算 (128+64)*3；10分钟后提醒我喝水；喝口水；释放爆裂魔法。\n通用知识问答、写代码和聊天需在「AI 设置」接入 API 或 Ollama。本地规则不是大模型。',ja='時刻、計算、リマインダーなら任せてください！難しい質問にはAIの接続が必要です。')
    actions={'释放爆裂魔法':'cast','爆裂魔法':'cast','explosion':'cast','喝口水':'drink','喝水':'drink','和逗之助玩':'cat','休息一会儿':'sleep','开心一下':'happy','按当前时间问候':'greeting'}
    if flat.lower() in actions:return LocalReply('收到！点下面的确认按钮，我就开始演出。',actions[flat.lower()],ja='了解です！確認ボタンを押してくださいね。')
    reminder=re.fullmatch(r'(\d+)\s*(秒|分钟|小时)后提醒我\s*(.{1,100})',t)
    if reminder:
        n,unit,note=reminder.groups();seconds=int(n)*{'秒':1,'分钟':60,'小时':3600}[unit]
        if not 1<=seconds<=86400:return LocalReply('提醒时间需要在 1 秒到 24 小时之间。')
        return LocalReply(f'将在 {n}{unit}后提醒你：{note}\n提醒只在桌宠运行期间有效。','reminder',seconds,note,ja='リマインダーを設定するには、確認ボタンを押してください。')
    expression=t[2:].strip(' ：:') if t.startswith('计算') else t
    if t.startswith('计算') or (any(c.isdigit() for c in expression) and re.fullmatch(r'[\d\s.+*/()%×÷^\-]+',expression)):
        try:
            answer=calculate(expression);return LocalReply('答案是 '+answer+'。',ja='答えは'+answer+'です。')
        except (ValueError,SyntaxError,ZeroDivisionError,OverflowError):return LocalReply('这个算式无法计算。只支持有限范围的四则运算、括号、余数与乘方。')
    return None

class Cancelled(Exception):pass
class EmptyAIReply(ValueError):pass

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('接口重定向被阻止，请填写服务的最终 API 地址。')

def open_http(url,key='',payload=None):
    validate_key(key)
    headers={'Accept':'application/json, text/event-stream','User-Agent':'MeguminAssistant/13'}
    if key:headers['Authorization']='Bearer '+key
    data=None
    if payload is not None:headers['Content-Type']='application/json';data=json.dumps(payload,ensure_ascii=False).encode('utf-8')
    return request.build_opener(NoRedirect()).open(request.Request(url,data=data,headers=headers),timeout=30)

def safe_error(exc):
    if isinstance(exc,error.HTTPError):
        if exc.code in (401,403):return '认证失败（HTTP '+str(exc.code)+'）：检查 API Key 和权限。'
        if exc.code==429:return '服务限流或额度不足（HTTP 429），请稍后重试或检查账户。'
        return f'接口返回 HTTP {exc.code}，检查接口地址、模型名称和服务状态。'
    if isinstance(exc,(TimeoutError,socket.timeout)):return '请求超时。桌宠动画未阻塞，可重试或更换服务。'
    if isinstance(exc,error.URLError):return '无法连接 AI 服务。检查地址、网络或本地模型是否启动。'
    if isinstance(exc,ValueError):return str(exc)[:160]
    return 'AI 请求失败，请检查接口配置。'

def compact_history(history):
    result=[];count=0
    for item in reversed(history[-12:]):
        content=str(item.get('content',''))[:4000];count+=len(content)
        if count>16000:break
        if item.get('role') in ('user','assistant'):result.append(dict(role=item['role'],content=content))
    return list(reversed(result))

def stream_answer(cfg,key,history,cancel,on_delta,system_prompt=None,max_output_tokens=1800,json_mode=False,delta_interval=.05,streaming=True,_retry_empty=True):
    cfg=normalize_config(cfg);provider=cfg['provider'];messages=compact_history(history)
    system_prompt=system_prompt or PROMPT
    if provider=='offline':raise ValueError('尚未接入 AI：在 AI 设置中选择服务、模型，并填写密钥。')
    if provider=='openai' and not key:raise ValueError('尚未填写 OpenAI API Key。请在本机 AI 设置中填写。')
    base=cfg['base_url'];model=cfg['model']
    if provider=='openai':url=base+'/responses';body=dict(model=model,instructions=system_prompt,input=messages,stream=streaming,store=False,max_output_tokens=max_output_tokens)
    elif provider=='compatible':
        url=base+'/chat/completions';body=dict(model=model,messages=[dict(role='system',content=system_prompt)]+messages,stream=streaming,max_tokens=max_output_tokens)
        if json_mode:body['response_format']=dict(type='json_object')
        if parse.urlparse(base).hostname=='api.deepseek.com':body['thinking']=dict(type='disabled')
    else:url=base+'/api/chat';body=dict(model=model,messages=[dict(role='system',content=system_prompt)]+messages,stream=streaming,options=dict(num_predict=max_output_tokens))
    text='';pending='';last=time.monotonic();completed=False
    def take(chunk):
        nonlocal text,pending,last
        if isinstance(chunk,list):
            for block in chunk:
                if isinstance(block,dict) and block.get('type') in ('text','output_text'):
                    value=block.get('text','');take(value.get('value','') if isinstance(value,dict) else value)
            return
        if not isinstance(chunk,str):return
        text+=chunk;pending+=chunk
        if len(text)>20000:raise ValueError('回答超过长度上限。请缩小问题后重试。')
        if time.monotonic()-last>=delta_interval:on_delta(pending);pending='';last=time.monotonic()
    if cancel.is_set():raise Cancelled()
    with open_http(url,key,body) as response:
        if 'text/event-stream' not in response.headers.get('Content-Type','') and (provider!='ollama' or not streaming):
            raw=response.read(1048577)
            if len(raw)>1048576:raise ValueError('服务回复过大。')
            obj=json.loads(raw.decode('utf-8'))
            if obj.get('error'):raise ValueError('AI 服务返回错误，未生成回答。')
            if provider=='openai':
                for item in obj.get('output',[]):
                    for content in item.get('content',[]):
                        if content.get('type')=='output_text':take(content.get('text',''))
            elif provider=='ollama':take(obj.get('message',{}).get('content',''))
            else:take(obj.get('choices',[{}])[0].get('message',{}).get('content',''))
            completed=True
        else:
            started=time.monotonic()
            while True:
                if cancel.is_set():raise Cancelled()
                if time.monotonic()-started>120:raise ValueError('生成时间超过 120 秒，请缩短问题。')
                raw=response.readline(262145)
                if not raw:break
                if len(raw)>262144:raise ValueError('服务流数据过大。')
                line=raw.decode('utf-8').strip()
                if provider!='ollama':
                    if not line.startswith('data:'):continue
                    line=line[5:].strip()
                    if line=='[DONE]':completed=True;break
                if not line:continue
                obj=json.loads(line)
                if obj.get('error') or obj.get('type') in ('error','response.failed','response.incomplete'):
                    raise ValueError('AI 服务生成失败或返回不完整内容，请重试。')
                if provider=='openai':
                    if obj.get('type')=='response.output_text.delta':take(obj.get('delta',''))
                    if obj.get('type')=='response.refusal.delta':take(obj.get('delta',''))
                    if obj.get('type')=='response.completed':completed=True;break
                elif provider=='compatible':
                    choices=obj.get('choices',[])
                    if choices:
                        take(choices[0].get('delta',{}).get('content',''))
                        if choices[0].get('finish_reason'):completed=True
                else:
                    take(obj.get('message',{}).get('content',''))
                    if obj.get('done'):completed=True;break
    if cancel.is_set():raise Cancelled()
    if pending:on_delta(pending)
    if not completed:raise ValueError('连接提前断开，回答不完整。')
    if not text.strip():
        if _retry_empty:
            # Some JSON-mode/streaming responses end normally without content.
            # Retry exactly once without forced JSON and without streaming.
            # Never expose reasoning_content or resend auth/HTTP failures.
            return stream_answer(cfg,key,history,cancel,on_delta,system_prompt=system_prompt,max_output_tokens=max(1024,max_output_tokens),json_mode=False,delta_interval=delta_interval,streaming=False,_retry_empty=False)
        raise EmptyAIReply('AI 服务连续返回空内容，已自动重试一次。请稍后重试；不是麦克风或语音模型设置问题。')
    return text

def check_connection(cfg,key):
    cfg=normalize_config(cfg)
    if cfg['provider']=='offline':return '本地小助手就绪，无需网络或密钥。'
    if cfg['provider']=='openai' and not key:raise ValueError('请先填写 API Key。')
    path='/api/tags' if cfg['provider']=='ollama' else '/models'
    with open_http(cfg['base_url']+path,key) as response:
        raw=response.read(1048577)
        if len(raw)>1048576:raise ValueError('模型列表过大。')
        obj=json.loads(raw.decode('utf-8'))
    models=[m.get('name','') for m in obj.get('models',[])] if cfg['provider']=='ollama' else [m.get('id','') for m in obj.get('data',[])]
    if not models:raise ValueError('服务没有返回模型列表。部分兼容服务不支持连接检查，可保存后直接发消息测试。')
    return '连接成功，模型可见。' if cfg['model'] in models else '连接成功，但填写的模型未在列表中。可用模型示例：'+', '.join(models[:5])[:250]
