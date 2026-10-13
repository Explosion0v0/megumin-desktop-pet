"""Check monitor placement, real pixels, custom motion and restoration."""
import ctypes,time,math
from PySide6.QtCore import QRect,QPoint,QSizeF,QRectF,Qt
from PySide6.QtGui import QImage,QPainter
from half_screen import HalfScreenStage,half_geometry

def check_half_screen(pet):
    from app import Engine
    result={};old_engine=pet.engine;old_half=pet.settings['half_screen'];position=pet.pos()
    try:
        monitors=[QRect(0,0,1920,1040),QRect(-1920,-200,1920,1080),QRect(1920,0,1080,1880)]
        result['half_screen_monitor_layout']=all(half_geometry(r,QPoint(r.left()+r.width()//4,r.center().y())).left()==r.left()
            and half_geometry(r,QPoint(r.right()-r.width()//4,r.center().y())).right()==r.right()
            and half_geometry(r,r.center()).width()==r.width()//2 for r in monitors)
        now=time.monotonic();pet.engine=Engine(now=now);pet.settings['half_screen']=True;pet.action('cast')
        o=pet.overlay;screen=o.screen_rect;geom=o.geometry()
        result['half_screen_visible']=o.active and o.isVisible()
        result['half_screen_exact_area']=geom.width()==screen.width()//2 and geom.height()==screen.height() and screen.contains(geom)
        u=ctypes.WinDLL('user32');u.GetWindowLongPtrW.argtypes=[ctypes.c_void_p,ctypes.c_int];u.GetWindowLongPtrW.restype=ctypes.c_ssize_t
        style=u.GetWindowLongPtrW(int(o.winId()),-20)
        result['half_screen_input_passthrough']=bool(style&0x20) and bool(style&0x08000000)
        result['desk_window_masked_during_cast']=pet.mask().boundingRect().width()==1
        stage=HalfScreenStage();e=pet.engine;e.since=now-3.75
        img=QImage(1000,1100,QImage.Format.Format_ARGB32_Premultiplied);img.fill(Qt.GlobalColor.transparent)
        # Warm the renderer toward the release pose without a second visible window.
        for _ in range(8):
            pet.character.last_render=now-.05;p=QPainter(img)
            stage.render(p,pet.character,e,now,QSizeF(1000,1100),QRectF(400,550,576,540));p.end()
        result['cross_particles_rendered']=stage.metrics['cross_particles']>=30 and img.pixelColor(705,356).alpha()>50
        result['large_spell_pixel_coverage']=sum(img.pixelColor(x,y).alpha()>35 for x in range(440,960,26) for y in range(130,840,26))>160
        result['custom_cubism_motion_loaded']=pet.character.renderer_info.get('choreography_motion_count')==1
        # Native right arm must move through distinct authored casting poses.
        values=[]
        for age in (1.7,3.72,5.75):
            e.since=now-age
            for _ in range(12):
                pet.character.last_render=now-.05;p=QPainter(img)
                pet.character.draw(p,e,now);p.end()
            values.append(pet.character.model.GetParamValueById('PARAM_ARM_R_ROTATE'))
        # A smaller, deliberate elbow sweep prevents the wand crossing the face.
        result['casting_joint_choreography']=max(values)-min(values)>8
        pet.on_key('left',27)
        result['escape_returns_to_desk']=pet.engine.state=='tired' and not o.active and not o.isVisible() and pet.pos()==position
        e=pet.engine=Engine(now=now);pet.action('cast');pet.hide_pet()
        result['hiding_closes_half_screen']=not o.active and not o.isVisible()
        pet.restore();pet.cancel_cast()
        result['half_screen_checks_passed']=all(result.values());return result
    finally:
        pet.overlay.stop();pet.engine=old_engine;pet.settings['half_screen']=old_half;pet.move(position);pet.mask_signature=None
