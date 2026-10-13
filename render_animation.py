"""Export the actual renderer as a short animated preview."""
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QPainter,QColor
from PIL import Image
from app import Pet,Engine,DEFAULTS
import sys,math

app=QApplication(sys.argv[:1]);pet=Pet(test_mode=True,settings=DEFAULTS.copy())
phases=[('idle',.8),('left',.16),('idle',.12),('right',.16),('idle',.12),
        ('left',.16),('idle',.12),('right',.16),('mouse',1.3),('click',.5),('happy',1),('drink',1.7),
        ('cat',1.4),('cast',7.2),('tired',1.3),('sleep',1.3)]
frames=[];now=100.0;count=0
for state,duration in phases:
    pet.engine=Engine(now=now-30,seed=1)
    e=pet.engine
    if state not in ('idle','left','right','mouse','click'):e.action(state,now)
    e.since=now;e.count=count
    if state in ('left','right'):e.tap_side=state;e.tap_until=now+duration;e.latest_vk=65 if state=='left' else 76;count+=1
    for i in range(max(1,round(duration*20))):
        t=now+i/20
        if state=='mouse':e.mouse_x=math.sin(i*.2)*12;e.mouse_y=math.cos(i*.2)*7;e.mouse_until=t+.14
        if state=='click':e.mouse_button=1 if i<5 else 2;e.mouse_until=t+.14
        pet.character.last_render=t-.05
        e.tick(t,dict(DEFAULTS,idle_enabled=False),.05)
        img=QImage(480,450,QImage.Format.Format_ARGB32)
        img.fill(QColor('#252332'))
        p=QPainter(img);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        pet.render_scene(p,t);p.end()
        buffer=img.bits().tobytes()
        pil=Image.frombytes('RGBA',(480,450),buffer,'raw','BGRA').convert('RGB')
        frames.append(pil)
    now+=duration
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
frames[0].save(out,save_all=True,append_images=frames[1:],duration=50,loop=0,optimize=True)
print('Animated renderer preview:',out)
pet.character.close()
