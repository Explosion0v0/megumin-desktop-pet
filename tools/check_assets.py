"""Validate included assets without downloading, recording or making AI calls."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from costumes import COSTUMES
p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,default=Path(__file__).resolve().parent.parent/'assets');a=p.parse_args()
missing=[];models=0;audio=0
def require(path):
 if not path.is_file():missing.append(str(path.relative_to(a.assets)))
for name in ['icon.ico','chomusuke-official-profile.png','voices/manifest.json','voices/costumes/manifest.json','choreography/DeskPet_Explosion.motion3.json']:require(a.assets/name)
for costume in COSTUMES.values():
 f=a.assets/'models'/costume['folder']/'Character.model3.json';require(f)
 if not f.is_file():continue
 models+=1;refs=json.loads(f.read_text(encoding='utf-8-sig'))['FileReferences']
 names=[refs[k] for k in ('Moc','Physics','Pose','DisplayInfo') if refs.get(k)]+refs.get('Textures',[])
 names += [m['File'] for group in refs.get('Motions',{}).values() for m in group if m.get('File')]
 names += [m['File'] for m in refs.get('Expressions',[]) if m.get('File')]
 for name in names:require(f.parent/name)
def visit(value):
 global audio
 if isinstance(value,dict):
  for k,v in value.items():
   if k=='file' and isinstance(v,str) and v.endswith('.wav'):require(a.assets/'voices'/v);audio+=1
   else:visit(v)
 elif isinstance(value,list):
  for v in value:visit(v)
for name in ['manifest.json','generated/manifest.json','costumes/manifest.json']:
 f=a.assets/'voices'/name;require(f)
 if f.exists():visit(json.loads(f.read_text(encoding='utf-8-sig')))
print(json.dumps(dict(assets_ready=not missing,models=models,audio_references=audio,missing=missing),ensure_ascii=False))
sys.exit(2 if missing else 0)
