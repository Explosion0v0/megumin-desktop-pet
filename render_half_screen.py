"""Actual half-screen renderer, a desktop mock background and included voice."""
from pathlib import Path
import sys,subprocess
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSizeF,QRectF,Qt
from PySide6.QtGui import QImage,QPainter,QColor,QFont
from app import Pet,Engine,DEFAULTS
from half_screen import HalfScreenStage
from spell_scene import CAST_RELEASE

app=QApplication(sys.argv[:1]);pet=Pet(test_mode=True,settings=DEFAULTS.copy());pet.timer.stop()
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
stage=HalfScreenStage();clip=dict(pet.voice.entries['chants'][9]['short'],zh='爆裂魔法！');delay=CAST_RELEASE-clip['release']
video=out/'半屏爆裂-语音预览.mp4'
cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-f','rawvideo','-pix_fmt','bgra','-s','1920x1080','-r','20','-i','pipe:0',
     '-i',str(pet.voice.folder/clip['file']),'-filter_complex',f'[1:a]adelay={round((1+delay)*1000)}:all=1,volume=0.55,apad[a]',
     '-map','0:v','-map','[a]','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-t','9.2','-movflags','+faststart',str(video)]
run=subprocess.Popen(cmd,stdin=subprocess.PIPE);e=pet.engine=Engine(now=100);frames=[];snapshots=[]
stages={28:'离桌',56:'咏唱',95:'释放十字光',105:'火光与冲击波',134:'魔力耗尽',154:'回桌'}
try:
    for step in range(184):
        now=100+step*.05
        if step==20:e.action('cast',now)
        e.tick(now,dict(DEFAULTS,idle_enabled=False),.05)
        audio_age=now-101-delay;env=clip['envelope'];index=int(audio_age*20)
        e.voice_mouth=env[index] if 0<=audio_age<clip['duration'] and index<len(env) else None
        pet.character.last_render=now-.05
        img=QImage(1920,1080,QImage.Format.Format_ARGB32_Premultiplied);img.fill(QColor('#242330'))
        p=QPainter(img);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setPen(QColor('#302d3d'))
        for x in range(0,1920,60):p.drawLine(x,0,x,1080)
        for y in range(0,1080,60):p.drawLine(0,y,1920,y)
        p.setFont(QFont('Microsoft YaHei UI',18));p.setPen(QColor('#a79bad'));p.drawText(70,90,'半屏演出预览 · 桌面背景示意')
        p.setFont(QFont('Microsoft YaHei UI',13));p.drawText(70,130,'演出窗口仅占右半屏，鼠标可穿透')
        if e.state=='cast':
            p.save();p.setClipRect(QRectF(960,0,960,1080));p.translate(960,0)
            stage.render(p,pet.character,e,now,QSizeF(960,1080),QRectF(364,516,576,540))
            if 0<=audio_age<clip['duration']:
                p.setFont(QFont('Microsoft YaHei UI',13,QFont.Weight.DemiBold));p.setPen(QColor('#ffe7c7'))
                rect=QRectF(24,988,912,66);p.fillRect(rect,QColor(35,24,38,205));p.drawText(rect,Qt.AlignmentFlag.AlignCenter,clip['zh'])
            p.restore()
        else:
            p.save();p.translate(1324,516);p.scale(1.2,1.2);pet.render_scene(p,now);p.restore()
        p.end();raw=img.bits().tobytes();run.stdin.write(raw)
        pil=Image.frombytes('RGBA',(1920,1080),raw,'raw','BGRA').convert('RGB')
        if step%2==0:frames.append(pil.resize((960,540),Image.Resampling.LANCZOS))
        if step in stages:
            pil.save(out/f'{step:03d}-半屏.png');snapshots.append((stages[step],pil))
finally:
    run.stdin.close();pet.character.close();pet.voice.stop()
assert run.wait()==0
frames[0].save(out/'半屏爆裂-动画预览.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=True)
sheet=Image.new('RGB',(1920,1190),'#242330');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
for i,(label,img) in enumerate(snapshots):
    x=(i%2)*960;y=(i//2)*397;sheet.paste(img.resize((640,360),Image.Resampling.LANCZOS),(x+150,y))
    draw.text((x+410,y+366),label,fill='#ffe0a0',font=font)
sheet.save(out/'半屏爆裂-流程.jpg')
print('Half-screen preview:',video)
