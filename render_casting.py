"""Export a continuous, actual-renderer casting sequence and its stage sheet."""
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter,QColor
from app import Pet,Engine,DEFAULTS
from spell_scene import CAST_DURATION

app=QApplication(sys.argv[:1]);pet=Pet(test_mode=True,settings=DEFAULTS.copy())
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
pet.engine=Engine(now=100,seed=1);e=pet.engine
frames=[];snapshots=[]
stages={8:('离桌',.4),36:('咏唱',1.8),79:('爆裂',3.95),114:('魔力耗尽',5.7),134:('回桌',6.7),145:('恢复',7.25)}
for step in range(-20,165):
    now=101+step*.05
    if step==0:e.action('cast',now)
    e.tick(now,dict(DEFAULTS,idle_enabled=False),.05)
    pet.character.last_render=now-.05
    img=QImage(960,900,QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor('#252332'))
    p=QPainter(img);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);p.scale(2,2)
    pet.render_scene(p,now);p.end()
    pil=Image.frombytes('RGBA',(960,900),img.bits().tobytes(),'raw','BGRA').convert('RGB')
    frames.append(pil.resize((480,450),Image.Resampling.LANCZOS))
    if step in stages:
        label,age=stages[step];pil.save(out/f'casting-{step:03d}.png');snapshots.append((label,age,pil))
frames[0].save(out/'爆裂动画.gif',save_all=True,append_images=frames[1:],duration=50,loop=0,optimize=True)
sheet=Image.new('RGB',(1440,1000),'#252332');draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
for i,(label,age,img) in enumerate(snapshots):
    x=(i%3)*480;y=(i//3)*500
    sheet.paste(img.resize((480,450),Image.Resampling.LANCZOS),(x,y))
    draw.text((x+160,y+456),f'{age:g}s · {label}',font=font,fill='#ffe1a0')
sheet.save(out/'爆裂流程.jpg')
print('Continuous casting preview:',out/'爆裂动画.gif')
pet.character.close()
