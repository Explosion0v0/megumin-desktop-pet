"""Generate an offline voice bank using the user's trained GPT-SoVITS model."""
from pathlib import Path
import os,sys,json,time,hashlib,argparse
ROOT=Path(__file__).resolve().parent
REPO=Path(os.environ.get('GPT_SOVITS_DIR',str(ROOT/'gpt-sovits'))).expanduser().resolve()
os.chdir(REPO);sys.path[:0]=[str(REPO),str(REPO/'GPT_SoVITS')]
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
import torch,numpy as np,soundfile as sf
import jieba,jieba.posseg
sys.modules['jieba_fast']=jieba;sys.modules['jieba_fast.posseg']=jieba.posseg
from TTS_infer_pack.TTS import TTS,TTS_Config
from TTS_infer_pack.TextPreprocessor import TextPreprocessor
from process_ckpt import get_sovits_version_from_path_fast
MODEL=Path(os.environ['MEGUMIN_VOICE_MODEL_DIR']).expanduser().resolve()
WEIGHTS=Path(os.environ.get('MEGUMIN_SOVITS_WEIGHTS',str(MODEL/'模型v2proplus/huihui-v2proplus.pth')))
GPT=Path(os.environ.get('MEGUMIN_GPT_WEIGHTS',str(MODEL/'模型v2proplus/huihui-v2proplus.ckpt')))
class JapanesePreprocessor(TextPreprocessor):
    def get_phones_and_bert(self,text,language,version,final=False):
        assert language in ('ja','all_ja'),'This voice bank is Japanese only'
        phones,word2ph,normalized=self.clean_text_inf(text,'ja',version)
        if len(phones)<6 and not final:return self.get_phones_and_bert('.'+text,language,version,True)
        return phones,self.get_bert_inf(phones,word2ph,normalized,'ja'),normalized
class JapaneseTTS(TTS):
    # Japanese uses zero BERT features in the official preprocessor. Avoid
    # loading an unrelated Chinese 651 MB encoder for an entirely Japanese bank.
    def init_bert_weights(self,base_path):self.bert_model=None;self.bert_tokenizer=None
    def __init__(self,cfg):
        super().__init__(cfg)
        self.text_preprocessor=JapanesePreprocessor(None,None,self.configs.device)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only');parser.add_argument('--force',action='store_true');args=parser.parse_args()
    version=get_sovits_version_from_path_fast(str(WEIGHTS))[1]
    print('Trained model version: '+version,flush=True)
    assert version=='v2ProPlus' and torch.cuda.is_available()
    # Check that the supplied GPT checkpoint is ordinary tensor/config data.
    ckpt=torch.load(GPT,map_location='cpu',weights_only=True);assert 'weight' in ckpt;del ckpt
    cfg=TTS_Config({'custom':dict(version=version,device='cuda',is_half=True,t2s_weights_path=str(GPT),vits_weights_path=str(WEIGHTS),
        bert_base_path=str(REPO/'GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large'),cnhuhbert_base_path=str(REPO/'GPT_SoVITS/pretrained_models/chinese-hubert-base'))})
    cfg.configs_path=str(ROOT/'pet-tts-config.yaml');tts=JapaneseTTS(cfg)
    refs={
        'calm':MODEL/'参考音频/平和/要は最初のきっかけ作りだと思うのですよ.wav',
        'happy':MODEL/'参考音频/兴奋/どうせこの後今日も勝負だって言うのでしょ楽しいゲームを思いつきましたよ.wav',
        'proud':MODEL/'惠惠/音频/愚問！この方がカッコイイからに決まっているでしょう！.wav',
        'dramatic':MODEL/'参考音频/中二/悪しき魔の者よ。我がレクイエムを聞き、常しえの眠りに沈むがいい!.wav'}
    out=ROOT/'generated-pet-voices';out.mkdir(exist_ok=True)
    lines=json.loads((ROOT/'tts_lines.json').read_text(encoding='utf-8'))
    report=json.loads((out/'generation.json').read_text(encoding='utf-8')) if (out/'generation.json').exists() else {}
    report['model']=dict(gpt=str(GPT),sovits=str(WEIGHTS),version=version,gpt_sha256=sha(GPT),sovits_sha256=sha(WEIGHTS),repository_commit=os.popen('git rev-parse HEAD').read().strip(),device=torch.cuda.get_device_name())
    report.setdefault('clips',{})
    for i,line in enumerate(lines):
        if args.only and line['id'] not in args.only.split(','):continue
        target=out/(line['id']+'.wav')
        if target.exists() and line['id'] in report['clips'] and not args.force:continue
        if target.exists() and args.force:
            archive=out/'raw-attempts';archive.mkdir(exist_ok=True)
            __import__('shutil').copy2(target,archive/(line['id']+'-'+sha(target)[:8]+'.wav'))
        ref=refs[line['tone']];prompt=ref.stem.replace('めぐみんja','')
        start=time.perf_counter()
        inputs=dict(text=line.get('tts_text',line['ja']),text_lang='all_ja',ref_audio_path=str(ref),prompt_text=prompt,prompt_lang='all_ja',
            text_split_method='cut5',batch_size=1,seed=1217+i if args.force else 817+i,top_k=12,top_p=.8,temperature=.75,
            parallel_infer=True,use_cuda_graph=False,use_flash_attention=False,fragment_interval=.18)
        results=list(tts.run(inputs));assert results
        sr,audio=results[-1];assert len(audio)>sr*.35
        sf.write(target,audio,sr,subtype='PCM_16')
        report['clips'][line['id']]=dict(**line,file=target.name,duration=round(len(audio)/sr,4),sample_rate=sr,reference=str(ref),
            synthesis_seconds=round(time.perf_counter()-start,3),sha256=sha(target))
        (out/'generation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('READY '+line['id']+' '+str(report['clips'][line['id']]['duration'])+'s',flush=True)
    print('Generated voice bank ready',flush=True)
if __name__=='__main__':main()
