"""Reproducible state, render, and real Windows hook smoke checks."""
import ctypes
import json
from pathlib import Path
import time


def run_state_tests():
    from app import Engine, DEFAULTS, WindowsInput
    cfg=DEFAULTS.copy()
    tests=[]
    def check(name, value):
        assert value, name
        tests.append(name)
    e=Engine(now=0,seed=12)
    e.key('left',1,45)
    check('key triggers left pose and counter', e.pose(1.02)=='left' and e.count==1)
    check('tap returns to neutral',e.pose(1.2)=='idle')
    e.action('sleep',2);e.key('right',3,45)
    check('input interrupts sleeping', e.state=='idle' and e.pose(3)=='right')
    e.action('drink',4);e.activity(5,45)
    check('mouse activity interrupts idle interaction',e.state=='idle')
    check('casting starts',e.action('cast',6) and e.mana==0)
    e.key('left',7,45)
    check('typing does not cancel cast',e.state=='cast')
    e.tick(6+__import__('spell_scene').CAST_RELEASE+.05,cfg)
    check('explosion speech after charging',e.bubble=='Explosion!!')
    e.tick(6+Engine.DURATIONS['cast']+.05,cfg)
    check('cast transitions to exhausted',e.state=='tired')
    e.activity(14.2,45)
    check('input can recover from exhaustion',e.state=='idle')
    check('cast cooldown works',not e.action('cast',15))
    check('cast cooldown expires',e.action('cast',16.1))
    check('Esc cancellation enters fatigue',e.cancel_cast(16.2) and e.state=='tired')
    check('cancellation preserves cooldown',not e.action('cast',17.1))
    e.activity(18,45)
    check('cancelling outside casting does nothing',not e.cancel_cast(18) and e.state=='idle')
    e=Engine(now=0,seed=12);e.tick(44.9,cfg)
    check('does not interact before idle threshold',e.state=='idle')
    e.tick(45.1,cfg)
    check('starts idle random action',e.state in e.DURATIONS)
    check('schedules varied idle intervals',63<e.next_idle<81)
    e=Engine(now=0);cfg['idle_enabled']=False;e.tick(400,cfg)
    check('idle toggle disables random actions',e.state=='idle')
    cfg['idle_enabled']=True;e=Engine(now=0);e.activity(44,45);e.tick(46,cfg)
    check('activity resets idle countdown',e.state=='idle')
    check('animation side classification',WindowsInput.side(0x41)=='left' and WindowsInput.side(0x4C)=='right')
    e.mana=99.99;e.tick(46.1,cfg,10)
    check('mana is clamped',e.mana==100)
    print(json.dumps({'passed':len(tests),'checks':tests},ensure_ascii=False,indent=2))


def render_previews(pet,directory):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage,QPainter,QColor
    from PIL import Image,ImageDraw,ImageFont
    directory.mkdir(parents=True,exist_ok=True)
    now=time.monotonic();now+=(2-now%4.7)%4.7
    scenes=[('idle',0),('left',0),('right',0),('happy',1),('drink',1.6),('cat',2),
            ('cast',2.5),('cast',4.0),('tired',1),('sleep',2)]
    paths=[]
    for i,(state,age) in enumerate(scenes):
        from app import Engine
        pet.engine=Engine(now=now-30,seed=1)
        if state not in ('idle','left','right'):
            pet.engine.action(state,now-age)
        pet.engine.since=now-age
        pet.engine.tap_until=now+.07 if state in ('left','right') else 0
        pet.engine.tap_side=state
        pet.engine.latest_vk=65 if state=='left' else (76 if state=='right' else 0)
        pet.engine.bubble_until=now+5
        if state=='cast' and age>__import__('spell_scene').CAST_RELEASE:pet.engine.bubble='Explosion!!'
        img=QImage(960,900,QImage.Format.Format_ARGB32_Premultiplied)
        if hasattr(pet.character,'model'):
            pet.character.last_state=None
            steps=max(1,round(age/.05))
            start=now-age
            pet.character.last_render=start-.05
        else:steps=1;start=now
        for step in range(steps):
            img.fill(Qt.GlobalColor.transparent)
            p=QPainter(img);p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);p.scale(2,2)
            pet.render_scene(p,start+(step+1)*(age/steps) if steps>1 else now);p.end()
        path=directory/f'{i:02d}-{state}.png';img.save(str(path));paths.append(path)
    canvas=Image.new('RGB',(1500,1050),'#252332')
    draw=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
    except OSError:font=ImageFont.load_default()
    labels=['待机','敲击 · A 键','敲击 · 任意键','开心','喝水','逗之助','爆裂 · 蓄力','爆裂 · 释放','魔力耗尽','小憩']
    for i,path in enumerate(paths):
        sprite=Image.open(path);sprite.thumbnail((300,310))
        x=(i%5)*300;y=(i//5)*480+70
        canvas.paste(sprite,(x,y),sprite)
        draw.text((x+90,y+340),labels[i],fill='#f7d5ad',font=font)
    draw.text((40,25),'MEGUMIN   /   惠惠 · 爆裂桌宠',fill='#ffe8c7',font=font)
    draw.text((40,1000),'透明桌面浮窗  ·  键盘响应  ·  空闲互动  ·  爆裂魔法',fill='#c2aeba',font=font)
    canvas.save(directory/'preview.jpg')
    print('Rendered ten states and contact sheet:',directory)


def start_live_smoke(app,pet):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QLineEdit
    from PySide6.QtGui import QImage,QPainter
    editor=QLineEdit();editor.setWindowTitle('Desktop pet input smoke test')
    editor.setText('');editor.resize(300,50);editor.show();editor.activateWindow();editor.setFocus()
    # Retain the widget through asynchronous Qt timers.
    pet.smoke_editor=editor
    pet.save_settings=lambda:None
    result={'hook_installed':bool(pet.input.hook),'keyboard_before':pet.engine.count}
    def send_keys():
        editor.activateWindow();editor.setFocus()
        u=ctypes.WinDLL('user32',use_last_error=True)
        u.GetForegroundWindow.restype=ctypes.c_void_p
        u.SetForegroundWindow.argtypes=[ctypes.c_void_p]
        hwnd=int(editor.winId())
        # Frozen GUI apps do not always inherit the launching shell's foreground
        # permission. Temporarily attach our test window's queue, then detach
        # before emitting any keys; never send into an unrelated window.
        u.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
        u.GetWindowThreadProcessId.restype=ctypes.c_ulong
        u.AttachThreadInput.argtypes=[ctypes.c_ulong,ctypes.c_ulong,ctypes.c_bool]
        u.BringWindowToTop.argtypes=[ctypes.c_void_p]
        u.SetFocus.argtypes=[ctypes.c_void_p]
        u.SetActiveWindow.argtypes=[ctypes.c_void_p]
        foreground=u.GetForegroundWindow()
        foreground_thread=u.GetWindowThreadProcessId(foreground,None)
        current_thread=ctypes.WinDLL('kernel32').GetCurrentThreadId()
        attached=False
        try:
            if foreground_thread and foreground_thread!=current_thread:
                attached=bool(u.AttachThreadInput(current_thread,foreground_thread,True))
            u.BringWindowToTop(hwnd)
            u.SetActiveWindow(hwnd)
            u.SetFocus(hwnd)
            u.SetForegroundWindow(hwnd)
        finally:
            if attached:u.AttachThreadInput(current_thread,foreground_thread,False)
        if u.GetForegroundWindow()!=hwnd:
            result['injection_skipped']='test window did not obtain focus'
            return
        u.keybd_event.argtypes=[ctypes.c_ubyte,ctypes.c_ubyte,ctypes.c_ulong,ctypes.c_size_t]
        for vk in (0x41,0x4C):
            u.keybd_event(vk,0,0,0);u.keybd_event(vk,0,2,0)
    def verify():
        result['keyboard_after']=pet.engine.count
        result['real_input_response']=pet.engine.count>=result['keyboard_before']+2
        result['tray_visible']=pet.tray.isVisible()
        result['transparent_window']=pet.testAttribute(__import__('PySide6.QtCore',fromlist=['Qt']).Qt.WidgetAttribute.WA_TranslucentBackground)
        pet.action('cat');result['cat_action']=pet.engine.state=='cat'
        pet.action('cast');result['cast_action']=pet.engine.state=='cast'
        result['window_size']=[pet.width(),pet.height()]
        u=ctypes.WinDLL('user32',use_last_error=True)
        u.GetWindowLongPtrW.argtypes=[ctypes.c_void_p,ctypes.c_int]
        u.GetWindowLongPtrW.restype=ctypes.c_ssize_t
        pet.settings['clickthrough']=True;pet.apply_settings()
        result['clickthrough_style']=bool(u.GetWindowLongPtrW(int(pet.winId()),-20)&0x20)
        pet.restore()
        result['restored_mouse_operation']=not bool(u.GetWindowLongPtrW(int(pet.winId()),-20)&0x20)
        pet.settings['scale']=120;pet.settings['opacity']=75;pet.apply_settings()
        result['scale_setting']=pet.width()==576 and pet.height()==540
        result['opacity_setting']=abs(pet.windowOpacity()-.75)<.01
        pet.settings['scale']=100;pet.settings['opacity']=100;pet.apply_settings()
        def render():
            from PySide6.QtCore import Qt
            img=QImage(480,450,QImage.Format.Format_ARGB32_Premultiplied);img.fill(Qt.GlobalColor.transparent)
            painter=QPainter(img);pet.character.draw(painter,pet.engine,time.monotonic());painter.end()
            return img
        render()
        c=pet.character
        result['renderer_info']=c.renderer_info.copy()
        result['genuine_cubism_model']=c.renderer_info['cubism_version']==3 and c.renderer_info['motion_count']==37 and c.renderer_info['parameter_count']>80
        result['transparent_model_frame']=c.frame.hasAlphaChannel() and c.frame.pixelColor(0,0).alpha()==0 and any(c.frame.pixelColor(x,y).alpha()>200 for x in range(50,c.frame.width()-50,40) for y in range(50,c.frame.height()-50,40))
        result['native_skill_motion']='00_Skill_02' in c.motion_history
        result['official_cat_art']=not c.cat_art.isNull() and c.cat_art.hasAlphaChannel()
        c.context.makeCurrent(c.surface);c.fbo.bind()
        hand=c.hand_mesh['R'];snapshot={n:c.model.GetParamValueById(n) for n in c.param_ids}
        c.param('PARAM_ARM_R_ROTATE',0);c.model.Draw();before=list(c.model.GetDrawableVertices(hand))
        c.param('PARAM_ARM_R_ROTATE',40);c.model.Draw();after=list(c.model.GetDrawableVertices(hand))
        result['real_rig_deformation']=any(abs(x-y)>.01 for x,y in zip(before,after))
        for name,value in snapshot.items():c.param(name,value)
        c.fbo.release();c.context.doneCurrent()
        pet.settings['eyepatch']=True;pet.apply_settings();render()
        result['eyepatch_model_setting']=c.loaded_eyepatch and 'megumin-eyepatch' in c.renderer_info['model_file']
        pet.settings['eyepatch']=False;pet.apply_settings();render()
        result['model_reload_back']=not c.loaded_eyepatch
        from app import Engine
        pet.engine=Engine(now=time.monotonic(),seed=1)
        def render_input():
            c.last_render=time.monotonic()-1/60
            return render()
        for _ in range(8):render_input()
        mouse_before=c.hand_anchor;key_before=c.keyboard_hand_anchor
        pet.engine.mouse_x=10;pet.engine.mouse_y=5
        for _ in range(16):render_input()
        result['mouse_hand_moves_independently']=(c.hand_anchor-mouse_before).manhattanLength()>3 and (c.keyboard_hand_anchor-key_before).manhattanLength()<1
        mouse_before=c.hand_anchor;key_before=c.keyboard_hand_anchor
        pet.engine.latest_vk=65
        for _ in range(6):
            pet.engine.tap_until=time.monotonic()+.07;render_input()
        result['key_labels_and_exact_highlight']=c.active_key=='A' and all(x in c.drawn_keys for x in ('Q','A','Z','1','Shift','Space','Ctrl'))
        result['keyboard_hand_moves_independently']=(c.keyboard_hand_anchor-key_before).manhattanLength()>1 and (c.hand_anchor-mouse_before).manhattanLength()<1
        # Verify rendered pixels, not just phase flags: the desk disappears
        # during the movie and returns before control is handed back.
        now=time.monotonic();pet.engine=Engine(now=now);render_input()
        idle=render_input()
        pet.engine.action('cast',now);pet.engine.since=now-2.3
        for _ in range(12):movie=render_input()
        result['casting_leaves_desk']=idle.pixelColor(400,385).alpha()>180 and movie.pixelColor(400,385).alpha()<10
        result['casting_live2d_visible']=any(movie.pixelColor(x,y).alpha()>180 for x in range(100,240,15) for y in range(95,300,15))
        result['staff_follows_native_hand']=c.staff_orb is not None and 0<c.staff_orb.x()<480 and -20<c.staff_orb.y()<450
        pet.engine.since=time.monotonic()-7.15
        for _ in range(8):returned=render_input()
        result['casting_returns_to_desk']=returned.pixelColor(400,385).alpha()>180
        pet.hide_pet();result['hide_works']=not pet.isVisible()
        pet.restore();result['restore_works']=pet.isVisible()
        pet.open_settings();result['settings_dialog']=pet.dialog.isVisible()
        pet.dialog.close()
        from voice_validation import check_voice
        result.update(check_voice(pet.voice.folder))
        from model_voice_validation import check_model_voice
        result.update(check_model_voice(pet.voice.folder))
        from v11_validation import check_v11
        result.update(check_v11(pet))
        pet.engine=Engine(now=time.monotonic());pet.engine.voice_mouth=0
        for _ in range(6):render_input()
        closed_mouth=c.model.GetParamValueById('PARAM_MOUTH_OPEN_Y')
        pet.engine.voice_mouth=.8
        for _ in range(6):render_input()
        result['voice_drives_native_mouth']=c.model.GetParamValueById('PARAM_MOUTH_OPEN_Y')-closed_mouth>.35
        from half_screen_validation import check_half_screen
        result.update(check_half_screen(pet))
        from assistant_validation import check_assistant
        result.update(check_assistant(pet))
        from speech_validation import check_speech
        from app import ASSETS
        result.update(check_speech(pet,ASSETS/'speech/hello-test.wav',capture=False))
        from persona_validation import check_persona
        result.update(check_persona(pet))
        from reply_format_validation import check_reply_format
        result.update(check_reply_format(pet))
        from empty_reply_validation import check_empty_reply
        result.update(check_empty_reply(pet))
        from reading_music_validation import check_reading_music
        result.update(check_reading_music(pet))
        result['passed']=all(result[k] for k in ['real_input_response','tray_visible','transparent_window','cat_action','cast_action',
            'clickthrough_style','restored_mouse_operation','scale_setting','opacity_setting','hide_works','restore_works','settings_dialog',
            'genuine_cubism_model','transparent_model_frame','native_skill_motion','official_cat_art','real_rig_deformation','eyepatch_model_setting','model_reload_back',
            'mouse_hand_moves_independently','key_labels_and_exact_highlight','keyboard_hand_moves_independently',
            'casting_leaves_desk','casting_live2d_visible','staff_follows_native_hand','casting_returns_to_desk','voice_checks_passed','voice_drives_native_mouth','half_screen_checks_passed','model_voice_checks_passed','v11_checks_passed'])
        (Path.cwd()/'smoke-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        result['passed']=result['passed'] and result['assistant_checks_passed'] and result['speech_checks_passed'] and result['persona_checks_passed'] and result['reply_format_checks_passed'] and result['empty_reply_checks_passed'] and result['reading_music_checks_passed']
        (Path.cwd()/'smoke-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        pet.test_mode=True # Smoke tests must not replace the user's saved settings.
        editor.close();pet.quit()
    QTimer.singleShot(600,send_keys)
    def safe_verify():
        try:verify()
        except Exception:
            import traceback
            (Path.cwd()/'smoke-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            pet.test_mode=True;pet.quit()
    QTimer.singleShot(1500,safe_verify)
