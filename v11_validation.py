from pathlib import Path
from datetime import datetime,timedelta
import tempfile,time
from unittest.mock import patch
import numpy as np
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QImage,QPainter
from time_greetings import TimeGreetings,current_slot,SHANGHAI
def check_v11(pet):
    from app import Engine
    r={};day=datetime(2026,10,9,tzinfo=SHANGHAI)
    cases=[(6,30,'morning'),(8,0,'breakfast'),(12,0,'lunch'),(18,0,'dinner'),(20,0,'evening'),(23,0,'bedtime'),(1,0,'bedtime')]
    r['greeting_time_windows']=all(current_slot(day.replace(hour=h,minute=m))[0]==s for h,m,s in cases)
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'times.json';calendar=TimeGreetings(path);now=day.replace(hour=20)
        assert calendar.due(now)=='evening';calendar.record(now)
        r['greetings_persist_once_per_day']=TimeGreetings(path).due(now+timedelta(minutes=50)) is None and TimeGreetings(path).due(now+timedelta(days=1))=='evening'
        night=TimeGreetings();night.record(day.replace(hour=23));r['bedtime_midnight_no_repeat']=night.due((day+timedelta(days=1)).replace(hour=1)) is None
    bank=pet.voice.generated
    r['time_greeting_audio_assets']=all(len(bank['scenes'].get(s,[]))==2 for s in ('morning','breakfast','lunch','dinner','evening','bedtime'))
    old_e=pet.engine;old_calendar=pet.calendar;old_settings=pet.settings.copy()
    try:
        pet.engine=Engine();pet.calendar=TimeGreetings();pet.settings.update(time_greetings=True,voice_model=True,voice_enabled=True,voice_volume=1)
        with patch.object(pet.voice,'play',return_value=True) as play:
            now=day.replace(hour=12)
            first=pet.time_greeting(wall_now=now);second=pet.time_greeting(wall_now=now)
            r['time_greeting_speaks_once']=first and not second and play.call_count==1 and bool(pet.engine.bubble)
            pet.engine.action('cast',time.monotonic());r['greeting_defers_cast']=not pet.time_greeting(wall_now=now+timedelta(days=1))
            pet.engine=Engine();pet.settings['time_greetings']=False
            r['greeting_setting_disables_auto']=not pet.time_greeting(wall_now=now+timedelta(days=1))
        pet.engine=Engine(now=100);c=pet.character
        for i in range(8):
            c.last_render=99.96;desk=QImage(960,900,QImage.Format.Format_ARGB32_Premultiplied);desk.fill(Qt.GlobalColor.transparent)
            p=QPainter(desk);p.scale(2,2);c.draw(p,pet.engine,100);p.end()
        reference=QImage(960,900,QImage.Format.Format_ARGB32_Premultiplied);reference.fill(Qt.GlobalColor.transparent)
        p=QPainter(reference);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);p.scale(2,2);p.translate(279,238);p.scale(1.25,1.25);p.translate(-240,-200)
        p.drawImage(QRectF(0,0,480,450),c.frame);p.end()
        def gold_count(image):
            rgb=np.frombuffer(image.bits(),np.uint8).reshape(900,960,4)[140:420,400:800,:3].astype(float)
            b,g,red=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
            return int(np.count_nonzero((red>150)&(g>95)&(red>g*1.1)&(b<g*.9)))
        r['hat_brim_stays_in_front_of_hair']=gold_count(reference)>200 and gold_count(desk)>=gold_count(reference)*.98
        pet.engine.action('cast',100)
        overlap=[];grips=[]
        for age in (.8,1.7,3.42,3.75,5.7):
            for i in range(8):
                c.last_render=100+age-.04;img=QImage(960,900,QImage.Format.Format_ARGB32_Premultiplied);img.fill(Qt.GlobalColor.transparent)
                p=QPainter(img);p.scale(2,2);c.draw(p,pet.engine,100+age);p.end()
            def a(image):return np.frombuffer(image.bits(),np.uint8).reshape(image.height(),image.bytesPerLine())[:,:image.width()*4].reshape(image.height(),image.width(),4)[:,:,3]
            overlap.append(int(np.count_nonzero((a(c.cast_wand)>40)&(a(c.cast_occlusion)>220))))
            grips.append(c.cast_grip_weights is not None and len(c.cast_grip_weights)==len(c.projected_vertices(c.cast_hand_mesh)))
        r['wand_hair_hand_occlusion']=max(overlap)==0;r['wand_native_grip_anchor']=all(grips)
        r['v11_checks_passed']=all(r.values());return r
    finally:
        pet.voice.stop();pet.engine=old_e;pet.calendar=old_calendar;pet.settings.update(old_settings)
