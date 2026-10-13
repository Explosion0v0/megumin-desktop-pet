"""Megumin desktop assistant. Keyboard events are never persisted or uploaded."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import math
import os
from pathlib import Path
import random
import sys
import time

from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, Signal, QObject
from PySide6.QtGui import (QAction, QColor, QFont, QIcon, QPainter, QPainterPath,
                           QPen, QPixmap, QRadialGradient, QCursor, QImage, QRegion)
from PySide6.QtWidgets import (QApplication, QWidget, QMenu, QSystemTrayIcon,
    QDialog, QVBoxLayout, QLabel, QFormLayout, QSpinBox, QSlider, QCheckBox,
    QPushButton, QMessageBox)
from spell_scene import ExplosionStage,CAST_DURATION,CAST_RELEASE,desk_visibility

APP_NAME = '惠惠 · Live2D 爆裂桌宠 v20'
BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
ASSETS = BASE / 'assets'
CONFIG = Path(os.environ.get('APPDATA', str(Path.home()))) / 'MeguminDesktopPet' / 'settings.json'
DEFAULTS = dict(scale=120, opacity=100, idle_seconds=45, idle_enabled=True,
                keyboard=True, topmost=True, clickthrough=False, reduced_motion=False,
                counter=True, eyepatch=False, voice_enabled=True, voice_volume=55, voice_full=True, voice_model=True, voice_caption=True, time_greetings=True, original_cast_revision=10, half_screen=True, x=None, y=None)
NAMES = ['idle', 'left', 'right', 'happy', 'drink', 'cat', 'cast', 'tired', 'sleep']


def load_config():
    result = DEFAULTS.copy()
    try:
        raw = json.loads(CONFIG.read_text(encoding='utf-8'))
        for k, default in DEFAULTS.items():
            value = raw.get(k, default)
            if k in ('x', 'y'):
                if isinstance(value, int) or value is None:
                    result[k] = value
            elif type(value) is type(default):
                result[k] = value
        result['scale'] = max(60, min(160, result['scale']))
        result['opacity'] = max(35, min(100, result['opacity']))
        result['idle_seconds'] = max(10, min(600, result['idle_seconds']))
        result['voice_volume'] = max(0,min(100,result['voice_volume']))
        # Apply the user's request for all ten original full chants once. Later
        # manual changes to the full/short setting remain persistent.
        if raw.get('original_cast_revision')!=10:
            result['voice_full']=True;result['original_cast_revision']=10
    except (OSError, ValueError, TypeError):
        pass
    return result


class Engine:
    """Pure state machine, separate from rendering and Windows input."""
    DURATIONS = dict(happy=2.6, drink=4.0, cat=4.5, cast=CAST_DURATION, tired=3.5, sleep=9.0)

    def __init__(self, now=None, seed=None):
        now = time.monotonic() if now is None else now
        self.rng = random.Random(seed)
        self.state = 'idle'
        self.since = now
        self.until = now
        self.last_input = now
        self.next_idle = now + 45
        self.last_cast = -1000
        self.tap_until = 0
        self.tap_side = 'left'
        self.count = 0
        self.mana = 100.0
        self.bubble = '我是惠惠！今天也要爆裂！'
        self.bubble_until = now + 7
        self.mouse_until = 0
        self.mouse_x=0.0;self.mouse_y=0.0;self.mouse_button=0
        self.latest_vk=0
        self.cast_release=CAST_RELEASE;self.cast_duration=CAST_DURATION;self.voice_mouth=None

    def set_cast_timing(self,release,duration):
        self.cast_release=max(.9,release)
        self.cast_duration=max(self.cast_release+3.55,duration)
        if self.state=='cast':self.until=self.since+self.cast_duration

    def visual_age(self,now):
        age=max(0,now-self.since)
        if self.state!='cast' or age<=.8:return age
        if age<self.cast_release:return .8+(age-.8)*(CAST_RELEASE-.8)/(self.cast_release-.8)
        return CAST_RELEASE+(age-self.cast_release)*(CAST_DURATION-CAST_RELEASE)/(self.cast_duration-self.cast_release)

    def say(self, message, now, seconds=3):
        self.bubble, self.bubble_until = message, now + seconds

    def activity(self, now, idle_seconds):
        self.last_input = now
        self.next_idle = now + idle_seconds
        if self.state in ('happy', 'drink', 'cat', 'sleep') or (self.state == 'tired' and now-self.since > .8):
            self.state, self.since, self.until = 'idle', now, now
            self.bubble_until = now

    def key(self, side, now, idle_seconds, vk=0):
        self.activity(now, idle_seconds)
        self.tap_side = side
        self.tap_until = now + .14
        self.latest_vk=vk
        self.count += 1
        self.mana = min(100, self.mana + .25)

    def action(self, state, now):
        if self.state == 'cast':
            return False
        if state == 'cast' and now-self.last_cast < 10:
            self.say('魔力回复中……稍等一下！', now)
            return False
        if state == 'cast':
            self.last_cast = now
            self.mana = 0
            self.cast_release=CAST_RELEASE;self.cast_duration=CAST_DURATION
        self.state, self.since = state, now
        self.until = now + self.DURATIONS[state]
        messages = dict(happy='哼哼，红魔族的天才就是我！', drink='补充水分，魔力也要休息一下。',
            cat='逗之助，不许偷吃我的点心！', cast='比黑色更黑，比黑暗更暗……',
            tired='爆裂之后……就拜托你了。', sleep='呼……明天也要 Explosion…')
        self.say(messages[state], now, self.DURATIONS[state])
        return True

    def tick(self, now, settings, dt=.016):
        self.mana = min(100, self.mana + dt*2.4)
        if self.state != 'idle' and now >= self.until:
            previous = self.state
            self.state = 'idle'
            if previous == 'cast':
                self.action('tired', now)
        if self.state == 'cast' and self.visual_age(now) > CAST_RELEASE:
            self.bubble = 'Explosion!!'
            if self.visual_age(now)>5.3:self.bubble='爆裂之后……就拜托你了。'
        if (settings['idle_enabled'] and self.state == 'idle' and
                now-self.last_input >= settings['idle_seconds'] and now >= self.next_idle):
            choices = ['drink', 'cat', 'happy', 'sleep', 'cast']
            self.action(self.rng.choice(choices), now)
            self.next_idle = now + self.rng.uniform(18, 35)

    def cancel_cast(self,now):
        if self.state!='cast':return False
        self.state='idle';self.action('tired',now);return True

    def pose(self, now):
        return self.tap_side if self.state == 'idle' and now < self.tap_until else self.state


class WindowsInput(QObject):
    pressed = Signal(str,int)

    def __init__(self):
        super().__init__()
        self.hook = None
        self.callback = None
        self.pressed_keys = set()
        self.last_fallback = {}
        self.last_input_stamp = None
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        self.user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.CallNextHookEx.restype = ctypes.c_ssize_t
        self.user32.SetWindowsHookExW.restype = wintypes.HANDLE
        self.user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel32.GetModuleHandleW.restype = wintypes.HMODULE

    @staticmethod
    def side(vk):
        # Only choose an animation side. No text reconstruction, storage, or networking.
        return 'left' if vk in {0x41,0x53,0x44,0x46,0x47,0x51,0x57,0x45,0x52,0x54,
            0x5A,0x58,0x43,0x56,0x42,0x31,0x32,0x33,0x34,0x35,0xA0,0xA2,0xA4} else 'right'

    def start(self):
        class KeyInfo(ctypes.Structure):
            _fields_ = [('vkCode',wintypes.DWORD),('scanCode',wintypes.DWORD),
                        ('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        prototype = ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM)
        def callback(code, message, data):
            if code >= 0:
                vk = ctypes.cast(data,ctypes.POINTER(KeyInfo)).contents.vkCode
                if message in (0x100,0x104):
                    self.pressed.emit(self.side(vk),vk)
                elif message in (0x101,0x105):
                    self.pressed_keys.discard(vk)
            return self.user32.CallNextHookEx(self.hook, code, message, data)
        self.callback = prototype(callback)
        self.user32.SetWindowsHookExW.argtypes = [ctypes.c_int,prototype,wintypes.HINSTANCE,wintypes.DWORD]
        self.hook = self.user32.SetWindowsHookExW(13,self.callback,self.kernel32.GetModuleHandleW(None),0)
        return bool(self.hook)

    def fallback_poll(self, now):
        if self.hook:
            return
        for vk in range(8,255):
            down = bool(self.user32.GetAsyncKeyState(vk) & 0x8000)
            if down and (vk not in self.pressed_keys or now-self.last_fallback.get(vk,0) > .09):
                self.pressed.emit(self.side(vk),vk)
                self.last_fallback[vk] = now
            if down:
                self.pressed_keys.add(vk)
            else:
                self.pressed_keys.discard(vk)

    def idle_seconds(self):
        class LastInput(ctypes.Structure):
            _fields_ = [('cbSize',wintypes.UINT),('dwTime',wintypes.DWORD)]
        info = LastInput(ctypes.sizeof(LastInput),0)
        if self.user32.GetLastInputInfo(ctypes.byref(info)):
            self.last_input_stamp = info.dwTime
            ticks = self.kernel32.GetTickCount() & 0xffffffff
            return ((ticks-info.dwTime) & 0xffffffff)/1000.0
        return None

    def close(self):
        if self.hook:
            self.user32.UnhookWindowsHookEx(self.hook)
            self.hook = None


class SettingsDialog(QDialog):
    def __init__(self, pet):
        super().__init__(pet)
        self.pet = pet
        self.setWindowTitle('惠惠的冒险设置')
        self.setMinimumWidth(370)
        self.setStyleSheet('''QDialog {background:#201c2b;color:#f5e9df;} QLabel,QCheckBox{color:#f5e9df;}
            QSpinBox{background:#332b41;color:#fff;border:1px solid #685168;border-radius:6px;padding:6px;}
            QPushButton{background:#c85b47;color:white;border:none;border-radius:8px;padding:10px;}
            QSlider::groove:horizontal{height:5px;background:#4c3a50;border-radius:2px;}
            QSlider::handle:horizontal{background:#ffc484;width:16px;margin:-6px 0;border-radius:8px;}
            QCheckBox{padding:4px;}''')
        layout = QVBoxLayout(self)
        title = QLabel('MEGUMIN  /  惠惠')
        title.setFont(QFont('Segoe UI',18,QFont.Weight.Bold))
        layout.addWidget(title)
        subtitle = QLabel('把一点爆裂魔法，放在桌面上。')
        layout.addWidget(subtitle)
        form = QFormLayout()
        self.scale = QSlider(Qt.Orientation.Horizontal)
        self.scale.setRange(60,160); self.scale.setValue(pet.settings['scale'])
        self.scale_label = QLabel(f"{self.scale.value()}%")
        self.scale.valueChanged.connect(lambda v:self.scale_label.setText(f'{v}%'))
        row = QVBoxLayout(); row.addWidget(self.scale);row.addWidget(self.scale_label)
        form.addRow('角色大小',row)
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(35,100);self.opacity.setValue(pet.settings['opacity'])
        form.addRow('透明度',self.opacity)
        self.idle = QSpinBox();self.idle.setRange(10,600)
        self.idle.setSuffix(' 秒');self.idle.setValue(pet.settings['idle_seconds'])
        form.addRow('多久无操作后互动',self.idle)
        self.volume=QSlider(Qt.Orientation.Horizontal);self.volume.setRange(0,100);self.volume.setValue(pet.settings['voice_volume'])
        self.volume_label=QLabel(f'{self.volume.value()}%')
        self.volume.valueChanged.connect(lambda v:self.volume_label.setText(f'{v}%'))
        self.volume.setToolTip('新音量用于下一次播放；可点击试听确认。')
        volume_row=QVBoxLayout();volume_row.addWidget(self.volume);volume_row.addWidget(self.volume_label)
        form.addRow('惠惠语音音量',volume_row)
        layout.addLayout(form)
        self.checks = {}
        for key,text in [('keyboard','跟随键盘与鼠标'),('idle_enabled','空闲时随机互动'),
                ('voice_enabled','播放惠惠语音'),('voice_model','日常互动使用模型生成的日语语音'),('voice_caption','语音显示中文台词'),('voice_full','完整爆裂吟唱（原声随机 10 段）'),
                ('time_greetings','早晚与饭点问候（每天各时段一次）'),
                ('half_screen','半屏爆裂演出（鼠标可穿透；Esc 收起）'),
                ('topmost','保持在最上层'),('counter','显示本次按键次数'),
                ('reduced_motion','轻柔特效（减少闪光与晃动）'),
                ('eyepatch','佩戴眼罩（另一套 Live2D 模型）'),
                ('clickthrough','鼠标穿透（用系统托盘菜单恢复）')]:
            box=QCheckBox(text);box.setChecked(pet.settings[key]);layout.addWidget(box);self.checks[key]=box
        hint=QLabel('拖动：移动位置　·　轻点：摸摸头\n双击：爆裂魔法　·　右键 / 托盘：和惠惠聊聊\n桌宠动画离线；问答仅主动发送聊天窗口内容，不保存其他软件输入。')
        hint.setWordWrap(True);hint.setStyleSheet('color:#beadb9;font-size:12px;padding:10px 0;')
        layout.addWidget(hint)
        save=QPushButton('保存，继续冒险');save.clicked.connect(self.save);layout.addWidget(save)
        preview=QPushButton('试听爆裂语音');preview.clicked.connect(lambda:pet.preview_voice(dict(pet.settings,voice_enabled=True,voice_volume=self.volume.value(),voice_full=self.checks['voice_full'].isChecked(),voice_model=self.checks['voice_model'].isChecked())));layout.addWidget(preview)
        assistant=QPushButton('和惠惠聊聊 / 桌面小助手');assistant.clicked.connect(pet.open_assistant);layout.addWidget(assistant)
        ai=QPushButton('AI 连接设置');ai.clicked.connect(pet.open_ai_settings);layout.addWidget(ai)

    def save(self):
        self.pet.settings.update(scale=self.scale.value(),opacity=self.opacity.value(),idle_seconds=self.idle.value(),voice_volume=self.volume.value())
        for k,box in self.checks.items(): self.pet.settings[k]=box.isChecked()
        self.pet.apply_settings();self.pet.save_settings();self.accept()


class Pet(QWidget):
    def __init__(self, test_mode=False, settings=None):
        super().__init__()
        self.test_mode = test_mode
        self.settings = settings or load_config()
        self.engine = Engine()
        from live_character import Live2DCharacter
        self.character=Live2DCharacter(ASSETS)
        from voice import VoicePlayer
        self.voice=VoicePlayer(ASSETS/'voices')
        self.dialogue_quiet=False
        from time_greetings import TimeGreetings
        self.calendar=TimeGreetings(None if test_mode or '--smoke-test' in sys.argv else CONFIG.parent/'time-greetings.json');self.next_time_check=0
        self.engine.next_idle=self.engine.last_input+self.settings['idle_seconds']
        self.setWindowTitle(APP_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.drag_start = None
        self.did_drag = False
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.pat)
        self.last_tick = time.monotonic()
        self.next_paint = 0
        self.next_bubble_sync = 0
        self.last_mouse = QCursor.pos()
        self.last_system_stamp = None
        self.action_grace = 0
        self.mouse_down = False
        self.hidden_by_user = False
        self.mask_signature = None
        self.dialog = None
        self.assistant = None;self.ai_dialog = None;self.assistant_hotkey=False
        from reading_bubble import ReadingBubble
        from music_player import MusicController
        self.reading_bubble=ReadingBubble(self);self.music=MusicController(self);self.music_dialog=None
        self.input = None
        self.tray = None
        from half_screen import CastingOverlay
        self.overlay=CastingOverlay(self)
        self.apply_settings(first=True)
        if not test_mode:
            self.create_tray()
            self.input = WindowsInput()
            self.input.pressed.connect(self.on_key)
            self.input.start()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)
        if not test_mode and '--smoke-test' not in sys.argv:
            u=ctypes.WinDLL('user32');u.RegisterHotKey.argtypes=[wintypes.HWND,ctypes.c_int,wintypes.UINT,wintypes.UINT]
            self.assistant_hotkey=bool(u.RegisterHotKey(int(self.winId()),0x4D47,0x4000|0x0002|0x0001,ord('M')))
        if not test_mode:QTimer.singleShot(650,self.start_greeting)

    def start_greeting(self):
        if self.dialogue_quiet or self.conversation_busy():return
        if self.hidden_by_user or self.engine.state!='idle' or self.voice.clip:return
        if not self.time_greeting():self.voice.greet(self.settings,time.monotonic())

    def time_greeting(self,force=False,wall_now=None):
        from time_greetings import local_now,current_slot
        if self.dialogue_quiet or self.conversation_busy():return False
        if self.hidden_by_user or self.engine.state!='idle' or (self.voice.clip and not force):return False
        if not force and not self.settings.get('time_greetings',True):return False
        wall_now=wall_now or local_now();slot=current_slot(wall_now)
        scene=(slot[0] if slot else 'greeting') if force else self.calendar.due(wall_now)
        if not scene:return False
        clip=self.voice.scene_clip(scene)
        if not clip:return False
        now=time.monotonic()
        if self.settings.get('voice_enabled',True) and self.settings.get('voice_model',True) and self.settings['voice_volume']>0:
            if not self.voice.play(clip,self.settings['voice_volume'],now):return False
        self.engine.say(clip['zh'],now,max(4,clip['duration']+.25));self.update()
        self.character.requested_motion='00_Appeal_01'
        if slot:self.calendar.record(wall_now)
        return True

    def save_settings(self):
        if self.test_mode:return
        self.settings.update(x=self.x(),y=self.y())
        try:
            CONFIG.parent.mkdir(parents=True,exist_ok=True)
            temp=CONFIG.with_suffix('.tmp')
            temp.write_text(json.dumps(self.settings,ensure_ascii=False,indent=2),encoding='utf-8')
            temp.replace(CONFIG)
        except OSError:pass

    def apply_settings(self, first=False):
        if hasattr(self,'voice') and (not self.settings['voice_enabled'] or not self.settings['voice_volume']):self.voice.stop()
        flags=Qt.WindowType.FramelessWindowHint|Qt.WindowType.Tool|Qt.WindowType.WindowDoesNotAcceptFocus
        if self.settings['topmost']: flags|=Qt.WindowType.WindowStaysOnTopHint
        if self.settings['clickthrough']: flags|=Qt.WindowType.WindowTransparentForInput
        old=self.pos()
        self.setWindowFlags(flags)
        self.resize(round(480*self.settings['scale']/100),round(450*self.settings['scale']/100))
        self.setWindowOpacity(self.settings['opacity']/100)
        screen=QApplication.primaryScreen().availableGeometry()
        if first:
            x,y=self.settings['x'],self.settings['y']
            self.move(x if x is not None else screen.right()-self.width()-24,
                      y if y is not None else screen.bottom()-self.height()+18)
        else:self.move(old)
        self.clamp_position()
        self.mask_signature=None
        self.character.eyepatch=self.settings['eyepatch']
        self.engine.next_idle=self.engine.last_input+self.settings['idle_seconds']
        if not self.test_mode and not self.hidden_by_user:self.show()
        if self.tray:self.tray.setContextMenu(self.make_menu())
        if hasattr(self,'overlay'):
            self.overlay.setWindowOpacity(self.windowOpacity());self.sync_overlay()

    def clamp_position(self):
        # Keep the actual character reachable even on small / rearranged monitors.
        screen=QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        r=screen.availableGeometry();s=self.settings['scale']/100
        self.move(max(r.left()-int(115*s),min(self.x(),r.right()-int(350*s))),
                  max(r.top()-int(90*s),min(self.y(),r.bottom()-int(420*s))))

    def create_tray(self):
        self.tray=QSystemTrayIcon(QIcon(str(ASSETS/'icon.ico')),self)
        self.tray.setToolTip(APP_NAME+'\n右键互动 / 设置 / 退出')
        self.tray.setContextMenu(self.make_menu())
        self.tray.activated.connect(lambda reason:self.restore() if reason==QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def make_menu(self):
        menu=QMenu(self)
        menu.setStyleSheet('QMenu{background:#241e30;color:#f5ece6;border:1px solid #6d4850;padding:7px;} QMenu::item{padding:7px 22px;border-radius:4px;} QMenu::item:selected{background:#9b453f;}')
        title=menu.addAction('惠惠 · EXPLOSION');title.setEnabled(False)
        menu.addSeparator()
        menu.addAction('和惠惠聊聊（Ctrl+Alt+M）',self.open_assistant)
        menu.addAction('语音对话（麦克风开关）',self.open_voice_conversation)
        menu.addAction('歌曲／演唱（高桥李依・本地音乐）',self.open_music)
        menu.addAction('展开当前台词',self.reading_bubble.open_full)
        menu.addAction('AI 连接设置…',self.open_ai_settings)
        menu.addSeparator()
        for text,state in [('释放爆裂魔法','cast'),('喝口水','drink'),('和逗之助玩','cat'),('开心一下','happy'),('休息一会儿','sleep')]:
            action=menu.addAction(text);action.triggered.connect(lambda checked=False,s=state:self.action(s))
        menu.addAction('收起爆裂演出（Esc）',self.cancel_cast)
        expressions=menu.addMenu('Live2D 原生表情动作')
        for text,motion in [('得意','00_Pride_01'),('害羞','00_Shame_01'),('惊讶','00_Surprise_01'),('疑惑','00_Doubt_01'),('生气','00_Anger_01'),('哭泣','00_Cry_01'),('兴奋','00_Excite_01'),('招呼','00_Appeal_01')]:
            expressions.addAction(text).triggered.connect(lambda checked=False,m=motion:self.native_motion(m))
        menu.addSeparator()
        menu.addAction('冒险设置…',self.open_settings)
        menu.addAction('试听爆裂语音',lambda:self.preview_voice())
        menu.addAction('按当前时间问候',lambda:self.time_greeting(force=True))
        sound=menu.addAction('惠惠语音');sound.setCheckable(True);sound.setChecked(self.settings['voice_enabled'])
        sound.triggered.connect(self.toggle_voice)
        menu.addAction('显示 / 恢复鼠标操作',self.restore)
        menu.addAction('暂时隐藏',self.hide_pet)
        menu.addAction('回到屏幕右下角',self.reset_position)
        menu.addSeparator()
        menu.addAction('退出桌宠',self.quit)
        return menu

    def restore(self):
        self.settings['clickthrough']=False
        self.hidden_by_user=False;self.apply_settings();self.save_settings()

    def hide_pet(self):
        self.music.stop();self.reading_bubble.hide()
        self.hidden_by_user=True;self.voice.stop();self.voice.pending=None;self.voice.played_cast=True;self.overlay.stop();self.hide()

    def reset_position(self):
        r=QApplication.primaryScreen().availableGeometry()
        self.move(r.right()-self.width()-24,r.bottom()-self.height()+18)
        self.restore()

    def open_settings(self):
        if self.dialog and self.dialog.isVisible():self.dialog.raise_();return
        self.dialog=SettingsDialog(self);self.dialog.show();self.dialog.activateWindow()

    def open_assistant(self):
        if self.assistant is None:
            from assistant_ui import AssistantDialog
            self.assistant=AssistantDialog(self)
        self.assistant.show();self.assistant.raise_();self.assistant.activateWindow();self.assistant.input.setFocus()

    def open_music(self):
        if self.music_dialog is None:
            from music_player import MusicDialog
            self.music_dialog=MusicDialog(self)
        self.music_dialog.show();self.music_dialog.raise_();self.music_dialog.activateWindow()

    def open_ai_settings(self):
        if self.ai_dialog is None:
            from assistant_ui import AISettings
            self.ai_dialog=AISettings(self)
        elif not self.ai_dialog.isVisible():
            self.ai_dialog.deleteLater()
            from assistant_ui import AISettings
            self.ai_dialog=AISettings(self)
        self.ai_dialog.show();self.ai_dialog.raise_();self.ai_dialog.activateWindow()

    def open_voice_conversation(self):
        self.open_assistant();self.assistant.mic.setFocus()

    def nativeEvent(self,eventType,message):
        msg=wintypes.MSG.from_address(int(message))
        if msg.message==0x0312 and msg.wParam==0x4D47:
            self.open_assistant();return True,0
        return super().nativeEvent(eventType,message)

    def action(self,state):
        if state=='cast':self.music.stop()
        if self.hidden_by_user:self.hidden_by_user=False;self.show()
        self.action_grace=time.monotonic()+.2
        now=time.monotonic();self.engine.action(state,now)
        self.voice.tick(self.engine,self.conversation_settings(),now);self.sync_overlay();self.update()

    def sync_overlay(self):
        if self.engine.state=='cast' and self.settings['half_screen'] and not self.hidden_by_user:
            if not self.overlay.active:self.overlay.start()
        else:self.overlay.stop()

    def cancel_cast(self):
        if self.engine.cancel_cast(time.monotonic()):
            self.voice.stop();self.voice.pending=None;self.voice.played_cast=True
            self.overlay.stop();self.engine.voice_mouth=None;self.update()

    def toggle_voice(self,enabled):
        self.settings['voice_enabled']=enabled
        if not enabled:self.voice.stop()
        self.save_settings()
        if self.tray:self.tray.setContextMenu(self.make_menu())

    def preview_voice(self,settings=None):
        cfg=settings or self.settings
        if self.engine.state=='cast':return
        if not cfg['voice_volume']:return
        if not self.voice.preview(cfg,time.monotonic()):QMessageBox.information(self,APP_NAME,'语音暂时无法播放：'+self.voice.error)

    def pat(self):self.action(random.choice(['happy','cat']))

    def native_motion(self,motion):
        if self.hidden_by_user:self.hidden_by_user=False;self.show()
        now=time.monotonic();self.action_grace=now+.2
        if self.engine.action('happy',now):
            self.voice.seen_happy=self.engine.since
            self.voice.react_native(motion,self.engine,self.conversation_settings(),now)
            self.character.requested_motion=motion;self.update()

    def on_key(self,side,vk=0):
        if vk==27 and self.engine.state=='cast':self.cancel_cast();return
        if self.settings['keyboard'] and not self.hidden_by_user:
            if self.engine.state!='cast' and not self.conversation_busy():
                self.voice.stop();self.engine.voice_mouth=None
            self.engine.key(side,time.monotonic(),self.settings['idle_seconds'],vk)

    def conversation_busy(self):
        if self.music.active:return True
        if self.assistant and (self.assistant.busy or self.assistant.speech.speaker.busy()):return True
        if self.assistant and self.voice.clip is not None and self.assistant.speech.speaker.active_clip is self.voice.clip:
            return bool(self.voice.header and not self.voice.header.flags&1)
        return bool(self.voice.clip and self.voice.clip.get('file')=='<in-memory-reply>' and self.voice.header and not self.voice.header.flags&1)

    def conversation_settings(self):
        cfg=self.settings.copy()
        if self.music.active:cfg['voice_enabled']=False
        if self.dialogue_quiet:cfg['voice_enabled']=False
        if self.dialogue_quiet or self.conversation_busy():cfg['idle_enabled']=False
        return cfg

    def tick(self):
        now=time.monotonic();dt=min(now-self.last_tick,.1);self.last_tick=now
        if self.input:
            self.input.fallback_poll(now)
            system_idle=self.input.idle_seconds()
            if (self.last_system_stamp is not None and self.input.last_input_stamp != self.last_system_stamp
                    and now > self.action_grace):
                self.engine.activity(now,self.settings['idle_seconds'])
            self.last_system_stamp=self.input.last_input_stamp
            mouse=QCursor.pos()
            s=self.settings['scale']/100
            self.character.pointer=QPointF((mouse.x()-self.x())/s,(mouse.y()-self.y())/s)
            down=bool(self.input.user32.GetAsyncKeyState(1)&0x8000 or self.input.user32.GetAsyncKeyState(2)&0x8000)
            if self.settings['keyboard']:
                delta=mouse-self.last_mouse
                self.engine.mouse_x=max(-12,min(12,self.engine.mouse_x+delta.x()*.07))
                self.engine.mouse_y=max(-7,min(7,self.engine.mouse_y+delta.y()*.07))
                self.engine.mouse_button=1 if self.input.user32.GetAsyncKeyState(1)&0x8000 else (2 if self.input.user32.GetAsyncKeyState(2)&0x8000 else 0)
            if self.settings['keyboard'] and (mouse!=self.last_mouse or (down and not self.mouse_down)):
                self.engine.mouse_until=now+.14
            self.last_mouse=mouse;self.mouse_down=down
        if self.hidden_by_user:
            self.engine.last_input=now;self.engine.next_idle=now+self.settings['idle_seconds']
            return
        cfg=self.conversation_settings()
        self.voice.tick(self.engine,cfg,now)
        self.engine.tick(now,cfg,dt)
        # Idle interactions may start a cast during Engine.tick.
        self.voice.tick(self.engine,cfg,now)
        if self.engine.state=='cast' and self.music.active:self.music.stop()
        self.music.tick(now,dt)
        self.sync_overlay()
        caption=self.voice.caption() if self.settings.get('voice_caption',True) else ''
        visible=bool(caption) or (now<self.engine.bubble_until and (self.engine.state!='cast' or self.engine.visual_age(now)<CAST_RELEASE))
        if now>=self.next_bubble_sync or self.overlay.active:
            self.next_bubble_sync=now+.1
            self.reading_bubble.sync(caption or self.engine.bubble,visible)
        if now>=self.next_time_check:
            self.next_time_check=now+15
            if now-self.engine.last_input>=4:self.time_greeting()
        # Input, audio and state still tick every 16 ms. Limit idle/large-effect
        # repaints so they leave time for Windows hook and tray events.
        if now>=self.next_paint:
            interval=1/30 if self.overlay.active or now-self.engine.last_input>2 else 1/60
            self.next_paint=now+interval
            if self.overlay.active:self.overlay.update()
            else:self.update()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self.drag_start=event.globalPosition().toPoint()-self.pos();self.did_drag=False

    def mouseMoveEvent(self,event):
        if self.drag_start is not None and event.buttons()&Qt.MouseButton.LeftButton:
            target=event.globalPosition().toPoint()-self.drag_start
            if (target-self.pos()).manhattanLength()>3 or self.did_drag:
                self.did_drag=True;self.move(target)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            if self.did_drag:self.clamp_position();self.save_settings()
            else:self.click_timer.start(QApplication.doubleClickInterval())
            self.drag_start=None

    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self.click_timer.stop();self.action('cast');self.did_drag=True

    def contextMenuEvent(self,event):self.make_menu().exec(event.globalPos())

    def paintEvent(self,event):
        painter=QPainter(self)
        if self.overlay.active:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(self.rect(),Qt.GlobalColor.transparent);painter.end();return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.character.configure_resolution(self.settings['scale']/100,self.devicePixelRatioF())
        painter.scale(self.settings['scale']/100,self.settings['scale']/100)
        self.render_scene(painter,time.monotonic())
        painter.end()

    def render_scene(self,p,now):
        e=self.engine;age=e.visual_age(now);pose=e.pose(now)
        reduced=self.settings['reduced_motion']
        if e.state=='cast':ExplosionStage().background(p,age,reduced)
        # Soft contact shadow, with continuous breathing / bongo movement.
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(38,22,37,38))
        p.drawEllipse(QRectF(140,388,200,17))
        tilt=0
        p.save()
        waiting=bool(self.assistant and self.assistant.busy and e.state=='idle' and not self.character.desktop_scene.isNull())
        if waiting:
            # Keep gentle breathing using the last full-quality composition while
            # the foreground chat waits for HTTP; avoid seven GL readbacks per frame.
            if not reduced:p.translate(0,math.sin(now*2)*.7)
            p.drawImage(QRectF(0,0,480,450),self.character.desktop_scene)
        else:self.character.draw(p,e,now,reduced)
        p.restore()
        if e.state=='cast':ExplosionStage().foreground(p,age,reduced,self.character.staff_orb)
        if e.state=='happy':self.draw_hearts(p,age)
        if e.state=='sleep':
            p.setPen(QColor('#d6c1e9'))
            for i in range(3):
                p.setFont(QFont('Segoe UI',12+i*3,QFont.Weight.Bold))
                p.drawText(QPointF(310+i*15,234-i*23-(age*7)%18),'z')
        caption=self.voice.caption() if self.settings.get('voice_caption',True) else ''
        bubble_visible=bool(caption) or (now<e.bubble_until and (e.state!='cast' or age<CAST_RELEASE))
        if bubble_visible and self.test_mode:
            msg=caption or e.bubble
            p.setFont(QFont('Microsoft YaHei UI',11,QFont.Weight.DemiBold))
            width=min(384,max(170,p.fontMetrics().horizontalAdvance(msg)+32))
            height=min(130,max(34,p.fontMetrics().boundingRect(QRectF(0,0,width-24,10000).toRect(),int(Qt.TextFlag.TextWordWrap),msg).height()+12))
            rect=QRectF(240-width/2,12,width,height)
            p.setPen(QPen(QColor('#9c5f59'),1));p.setBrush(QColor(34,26,43,238));p.drawRoundedRect(rect,14,14)
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(34,26,43,238))
            tail=QPainterPath();tail.moveTo(232,rect.bottom());tail.lineTo(240,rect.bottom()+6);tail.lineTo(248,rect.bottom());p.drawPath(tail)
            p.setPen(QColor('#ffe3be'));p.drawText(rect.adjusted(12,2,-12,-2),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,msg)
        if self.settings['counter']:
            p.save();p.setOpacity(desk_visibility(age) if e.state=='cast' else 1)
            rect=QRectF(172,411,136,22)
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(35,27,43,204));p.drawRoundedRect(rect,11,11)
            p.setBrush(QColor('#f5aa71'));p.drawEllipse(QPointF(188,422),3,3)
            p.setPen(QColor('#ead6ca'));p.setFont(QFont('Microsoft YaHei UI',8))
            p.drawText(QRectF(200,411,100,22),Qt.AlignmentFlag.AlignVCenter,f'敲击  {e.count:,}')
            p.restore()
        if e.state in ('cast','tired'):
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(35,27,43,210));p.drawRoundedRect(QRectF(164,438,152,5),2,2)
            p.setBrush(QColor('#faac70'));p.drawRoundedRect(QRectF(164,438,152*e.mana/100,5),2,2)
        if not self.test_mode:self.update_hit_mask(pose,bubble_visible,e.state=='cast',tilt)

    def update_hit_mask(self,pose,bubble,magic,tilt):
        signature=(pose,bubble,magic,self.settings['scale'],self.settings['counter'],self.settings['eyepatch'])
        if signature==self.mask_signature:return
        self.mask_signature=signature
        s=self.settings['scale']/100
        region=QRegion(self.character.region(s,pose))
        # Regions leave the surrounding desktop clickable; effects may temporarily expand it.
        # Reading bubble is independent: the pet hit mask must not clip its text.
        if self.settings['counter']:region|=QRegion(round(170*s),round(410*s),round(140*s),round(25*s))
        if magic:region|=QRegion(0,0,self.width(),self.height())
        self.setMask(region)

    def draw_hearts(self,p,age):
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(4):
            t=(age*.6+i*.23)%1;x=132+(i%2)*216;y=285-t*100
            p.setBrush(QColor(244,125,155,round(220*(1-t))))
            p.save();p.translate(x,y);p.scale(.65+t*.4,.65+t*.4)
            path=QPainterPath();path.moveTo(0,4);path.cubicTo(-18,-6,-12,-18,0,-9)
            path.cubicTo(12,-18,18,-6,0,4);p.drawPath(path);p.restore()

    def draw_magic(self,p,age,reduced):
        charge=min(1,age/2.3);burst=max(0,age-2.3)
        fade=max(0,1-burst/1.8) if burst else charge
        center=QPointF(240,282)
        p.save();p.setOpacity(fade*(.65 if reduced else 1))
        glow=QRadialGradient(center,190)
        glow.setColorAt(0,QColor(255,207,94,0 if reduced else 75))
        glow.setColorAt(.5,QColor(255,74,25,48));glow.setColorAt(1,QColor(255,40,20,0))
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(glow);p.drawEllipse(center,210,150)
        p.save();p.translate(240,382);p.scale(1,.30)
        for radius,width,color in [(148,2,'#ff6b35'),(130,1.5,'#ffc679'),(107,1.5,'#e66649')]:
            p.setPen(QPen(QColor(color),width));p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(0,0),radius*charge,radius*charge)
        p.rotate(age*34)
        for i in range(12):
            angle=i*math.pi/6
            p.drawLine(QPointF(math.cos(angle)*134*charge,math.sin(angle)*134*charge),
                       QPointF(math.cos(angle)*145*charge,math.sin(angle)*145*charge))
        path=QPainterPath()
        for i in range(7):
            angle=(i*2 % 7)*math.tau/7
            point=QPointF(math.cos(angle)*105*charge,math.sin(angle)*105*charge)
            if i==0:path.moveTo(point)
            else:path.lineTo(point)
        path.closeSubpath();p.drawPath(path);p.restore()
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(34 if not reduced else 12):
            a=i*2.39996+age*.4
            r=35+(i%7)*18
            if burst:r+=burst*(65+i%5*12)
            x=240+math.cos(a)*r;y=307+math.sin(a)*r*.72-(age*28+i*5)%85
            p.setBrush(QColor('#ffe5a3') if i%3 else QColor('#ff774a'))
            size=1.5+i%3;p.drawEllipse(QPointF(x,y),size,size)
        if burst:
            radius=20+burst*145
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor('#ffc975'),max(1,6-burst*3)))
            p.drawEllipse(center,radius,radius*.64)
            p.setPen(QPen(QColor('#ff8052'),2));p.drawEllipse(center,radius*.8,radius*.51)
            if burst<.55 and not reduced:
                p.setOpacity((1-burst/.55)*.7)
                p.setPen(Qt.PenStyle.NoPen)
                star=QPainterPath()
                for i in range(16):
                    a=i*math.pi/8;radius2=(120 if i%2==0 else 20)*(1+burst)
                    pt=QPointF(240+math.cos(a)*radius2,282+math.sin(a)*radius2)
                    if i==0:star.moveTo(pt)
                    else:star.lineTo(pt)
                star.closeSubpath();p.setBrush(QColor('#fff0c5'));p.drawPath(star)
        p.restore()

    def quit(self):
        self.music.stop()
        if self.music_dialog:self.music_dialog.close()
        self.reading_bubble.close_all()
        if self.assistant:
            self.assistant.speech.disable();self.assistant.speech.speaker.service.close();self.assistant.job.cancel();self.assistant.close()
        if self.ai_dialog:self.ai_dialog.job.cancel();self.ai_dialog.close()
        if self.assistant_hotkey:
            u=ctypes.WinDLL('user32');u.UnregisterHotKey.argtypes=[wintypes.HWND,ctypes.c_int];u.UnregisterHotKey(int(self.winId()),0x4D47)
        self.save_settings()
        self.overlay.stop()
        self.voice.stop()
        if self.input:self.input.close()
        self.character.close()
        if self.tray:self.tray.hide()
        QApplication.quit()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--preview-dir');parser.add_argument('--smoke-test',action='store_true')
    args=parser.parse_args()
    if args.smoke_test:
        # Windowed PyInstaller executables otherwise discard Qt callback
        # tracebacks, leaving a test process alive with no failure report.
        sys.stdout=open(Path.cwd()/'smoke-console.log','w',encoding='utf-8',buffering=1)
        sys.stderr=sys.stdout
    if args.self_test:
        from validation import run_state_tests
        run_state_tests();return
    app=QApplication(sys.argv[:1]);app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME);app.setWindowIcon(QIcon(str(ASSETS/'icon.ico')))
    app.setFont(QFont('Microsoft YaHei UI',9))
    test=bool(args.preview_dir)
    mutex=None
    if not test and not args.smoke_test:
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateMutexW.restype=wintypes.HANDLE
        kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
        mutex=kernel.CreateMutexW(None,False,'Local\\MeguminDesktopPet_v1')
        if ctypes.get_last_error()==183:
            QMessageBox.information(None,APP_NAME,'惠惠已经在运行啦！请在系统托盘中找到红色帽子图标。')
            return
    pet=Pet(test_mode=test,settings=dict(DEFAULTS,voice_enabled=False) if args.smoke_test else (DEFAULTS.copy() if test else None))
    app.aboutToQuit.connect(lambda:pet.input.close() if pet.input else None)
    app.aboutToQuit.connect(pet.character.close)
    app.aboutToQuit.connect(pet.voice.stop)
    app.aboutToQuit.connect(pet.overlay.stop)
    if args.preview_dir:
        from validation import render_previews
        render_previews(pet,Path(args.preview_dir));pet.character.close();return
    pet.show()
    if args.smoke_test:
        from validation import start_live_smoke
        start_live_smoke(app,pet)
    app.exec()
    if mutex:kernel.CloseHandle(mutex)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Log only exception type/message, never keyboard events or user text.
        error=Path(os.environ.get('APPDATA','.'))/'MeguminDesktopPet'/'error.txt'
        error.parent.mkdir(parents=True,exist_ok=True)
        error.write_text(f'{type(exc).__name__}: {exc}',encoding='utf-8')
        if QApplication.instance():QMessageBox.critical(None,APP_NAME,f'启动失败：{exc}')
        raise
