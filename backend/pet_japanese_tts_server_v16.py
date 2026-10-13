"""Loopback Japanese TTS: warm model, native CUDA Graph, bounded RAM cache."""
from pathlib import Path
import sys,os,json,time,io,threading,base64
import numpy as np
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from synthesize_pet_voices import JapaneseTTS,TTS_Config,MODEL,WEIGHTS,GPT,REPO
import soundfile as sf
import torch

READY=False;TTS_ENGINE=None;LOCK=threading.Lock();FAILURE='';ACCEL_FALLBACK=''
CACHE=OrderedDict();REF=MODEL/'参考音频/平和/要は最初のきっかけ作りだと思うのですよ.wav'
def render(text,accelerated=False):
    global ACCEL_FALLBACK
    inputs=dict(text=text,text_lang='all_ja',ref_audio_path=str(REF),prompt_text=REF.stem,prompt_lang='all_ja',
        text_split_method='cut5',batch_size=1,seed=817,top_k=12,top_p=.8,temperature=.75,
        parallel_infer=True,use_cuda_graph=accelerated and not ACCEL_FALLBACK,
        use_flash_attention=accelerated and not ACCEL_FALLBACK,fragment_interval=.18)
    try:result=list(TTS_ENGINE.run(inputs))
    except Exception as exc:
        if not accelerated:raise
        ACCEL_FALLBACK=type(exc).__name__
        if TTS_ENGINE.t2s_accel is not None:
            TTS_ENGINE.t2s_accel.close();TTS_ENGINE.t2s_accel=None
        if torch.cuda.is_available():torch.cuda.empty_cache()
        inputs.update(use_cuda_graph=False,use_flash_attention=False);result=list(TTS_ENGINE.run(inputs))
    sr,audio=result[-1];wav=io.BytesIO();sf.write(wav,audio,sr,format='WAV',subtype='PCM_16');return wav.getvalue()

def render_chunks(text):
    inputs=dict(text=text,text_lang='all_ja',ref_audio_path=str(REF),prompt_text=REF.stem,prompt_lang='all_ja',
        text_split_method='cut5',batch_size=1,seed=817,top_k=12,top_p=.8,temperature=.75,
        parallel_infer=False,streaming_mode=True,split_bucket=False,
        min_chunk_length=16,overlap_length=2,fixed_length_chunk=False,fragment_interval=.05)
    for sr,audio in TTS_ENGINE.run(inputs):
        wav=io.BytesIO();sf.write(wav,audio,sr,format='WAV',subtype='PCM_16');yield wav.getvalue()

def join_waves(chunks):
    import wave
    combined=io.BytesIO();frames=[];params=None
    for chunk in chunks:
        with wave.open(io.BytesIO(chunk),'rb') as w:
            if params is None:params=w.getparams()
            if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(params.nchannels,params.sampwidth,params.framerate):raise ValueError('PCM format changed')
            frames.append(w.readframes(w.getnframes()))
    with wave.open(combined,'wb') as w:w.setparams(params);w.writeframes(b''.join(frames))
    return combined.getvalue()

def acceleration_info():
    a=getattr(TTS_ENGINE,'t2s_accel',None)
    return dict(backend=getattr(a,'backend',None),cuda_graph=bool(getattr(a,'graph_enabled',False)),fallback=ACCEL_FALLBACK)

def initialize():
    global READY,TTS_ENGINE,FAILURE
    try:
        cfg=TTS_Config({'custom':dict(version='v2ProPlus',device='cuda' if torch.cuda.is_available() else 'cpu',is_half=torch.cuda.is_available(),t2s_weights_path=str(GPT),vits_weights_path=str(WEIGHTS),
            bert_base_path=str(REPO/'GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large'),cnhuhbert_base_path=str(REPO/'GPT_SoVITS/pretrained_models/chinese-hubert-base'))})
        cfg.configs_path=str(ROOT/'pet-live-tts-config-v16.yaml');TTS_ENGINE=JapaneseTTS(cfg)
        with LOCK:
            CACHE['こんにちは。']=render('こんにちは。',False)
        READY=True;print('JAPANESE_TTS_V15_READY '+json.dumps(acceleration_info()),flush=True)
    except Exception as exc:FAILURE=type(exc).__name__;print('JAPANESE_TTS_INIT_FAILED '+FAILURE,flush=True)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply_json(self,status,obj):
        raw=json.dumps(obj).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path!='/health':self.reply_json(404,{'error':'not_found'});return
        self.reply_json(200,dict(ready=READY,language='ja',engine='user-trained-v2ProPlus',revision=16,quality_profile='natural_full_reply',streaming_default=False,failure=FAILURE,acceleration=acceleration_info()))
    def do_POST(self):
        if self.path not in ('/tts','/tts-stream'):self.reply_json(404,{'error':'not_found'});return
        if not READY:self.reply_json(503,{'error':'model_loading'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=4096:raise ValueError()
            obj=json.loads(self.rfile.read(size));text=obj.get('text','')
            if not isinstance(text,str) or not 1<=len(text)<=240 or not any('\u3040'<=c<='\u30ff' or '\u3400'<=c<='\u9fff' or '\uff66'<=c<='\uff9f' or c.isdigit() for c in text):raise ValueError()
        except Exception:self.reply_json(400,{'error':'Japanese_text_required'});return
        if not LOCK.acquire(blocking=False):self.reply_json(429,{'error':'busy'});return
        try:
            started=time.monotonic();hit=text in CACHE and not obj.get('bypass_cache',False)
            if self.path=='/tts-stream':
                self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.send_header('X-Cache','hit' if hit else 'miss');self.end_headers()
                chunks=[]
                stream=[CACHE[text]] if hit else render_chunks(text)
                for chunk in stream:
                    chunks.append(chunk);self.wfile.write((json.dumps(dict(wav=base64.b64encode(chunk).decode()))+'\n').encode());self.wfile.flush()
                if not hit:
                    CACHE[text]=join_waves(chunks)
                    while len(CACHE)>32 or sum(map(len,CACHE.values()))>12*1024*1024:CACHE.popitem(last=False)
                self.wfile.write(b'{"done":true}\n');self.wfile.flush();return
            if hit:CACHE.move_to_end(text);raw=CACHE[text]
            else:
                raw=render(text,obj.get('accelerated',False));CACHE[text]=raw
                while len(CACHE)>32 or sum(map(len,CACHE.values()))>12*1024*1024:CACHE.popitem(last=False)
            self.send_response(200);self.send_header('Content-Type','audio/wav');self.send_header('Content-Length',str(len(raw)))
            self.send_header('X-Synthesis-Seconds',str(round(time.monotonic()-started,3)));self.send_header('X-Cache','hit' if hit else 'miss');self.end_headers();self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
        except Exception:
            if self.path=='/tts-stream':
                try:self.wfile.write(b'{"error":"stream_synthesis_failed"}\n');self.wfile.flush()
                except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
            else:self.reply_json(500,{'error':'synthesis_failed'})
        finally:LOCK.release()

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',18893),Handler);server.daemon_threads=True
    threading.Thread(target=initialize,name='PrewarmMeguminV15',daemon=True).start();server.serve_forever()
