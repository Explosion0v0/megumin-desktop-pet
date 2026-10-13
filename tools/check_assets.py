"""Check user-supplied runtime assets; never download restricted resources."""
from pathlib import Path
import argparse,json,sys
p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,default=Path(__file__).resolve().parent.parent/'assets');a=p.parse_args()
required=['icon.ico','chomusuke-official-profile.png','models/megumin/Character.model3.json','models/megumin-eyepatch/Character.model3.json','voices/manifest.json','choreography/DeskPet_Explosion.motion3.json']
missing=[name for name in required if not (a.assets/name).is_file()]
for folder in ('megumin','megumin-eyepatch'):
 f=a.assets/'models'/folder/'Character.model3.json'
 if f.is_file():
  refs=json.loads(f.read_text(encoding='utf-8'))['FileReferences'];names=[refs[k] for k in ('Moc','Physics','Pose','DisplayInfo') if refs.get(k)]+refs.get('Textures',[])
  names += [m['File'] for group in refs.get('Motions',{}).values() for m in group if m.get('File')]
  names += [m['File'] for m in refs.get('Expressions',[]) if m.get('File')]
  missing += ['models/'+folder+'/'+name for name in names if not (f.parent/name).is_file()]
print(json.dumps({'assets_ready':not missing,'missing':missing,'hint':'See docs/ASSETS.md; supply assets you have rights to use.'},ensure_ascii=False))
sys.exit(2 if missing else 0)
