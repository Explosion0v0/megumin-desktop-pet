"""Local original-quality music + official NetEase links. No credentials or DRM decoding."""
from pathlib import Path
import json,math,os,time
from urllib.parse import urlsplit,parse_qs,quote
import numpy as np
from PySide6.QtCore import QObject,Signal,QUrl,QTimer,Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QListWidget,QFileDialog,QInputDialog,QSlider,QCheckBox,QMessageBox)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput,QAudioBufferOutput,QAudioFormat

FORMATS={'.wav','.mp3','.flac','.ogg','.m4a','.aac'}
OFFICIAL='https://music.163.com/'
def normalize_netease_url(value):
    u=urlsplit(value.strip())
    if u.scheme!='https' or u.hostname not in ('music.163.com','y.music.163.com','m.music.163.com') or u.username or u.password or u.port not in (None,443):
        raise ValueError('仅接受 HTTPS 网易云歌曲／歌单分享链接。')
    route=urlsplit(u.fragment) if u.fragment else u
    kind=route.path.strip('/').split('/')[-1]
    ids=parse_qs(route.query).get('id',[])
    if kind not in ('song','playlist','album') or len(ids)!=1 or not ids[0].isdigit() or not 1<=len(ids[0])<=20:
        raise ValueError('请复制带 id 的歌曲、歌单或专辑链接，不要填写账号凭据。')
    return OFFICIAL+'#/'+kind+'?id='+ids[0]

def supported_audio(path):
    p=Path(path)
    if not p.is_file():raise ValueError('音频文件不存在。')
    with p.open('rb') as f:header=f.read(8)
    if p.suffix.lower()=='.ncm' or header==b'CTENFDAM':
        raise ValueError('NCM 不能直接播放或用于演唱推理；请提供普通 WAV／MP3／FLAC 或你自己的试唱。不会解密 NCM。')
    if p.suffix.lower() not in FORMATS:raise ValueError('请选择 WAV／MP3／FLAC／OGG／M4A／AAC。')
    return p.resolve()

class MusicController(QObject):
    changed=Signal()
    def __init__(self,pet):
        super().__init__(pet);self.pet=pet;self.title='';self.error='';self.level=0.;self.level_at=0.;self.smoothed=0.;self.show=False
        self.player=QMediaPlayer(self);self.output=QAudioOutput(self);self.output.setVolume(.6);self.player.setAudioOutput(self.output)
        self.buffers=QAudioBufferOutput(self);self.player.setAudioBufferOutput(self.buffers);self.buffers.audioBufferReceived.connect(self.on_buffer)
        self.player.playbackStateChanged.connect(self.state_changed);self.player.errorOccurred.connect(self.on_error)
        self.player.mediaStatusChanged.connect(self.media_changed)
        self.player.setPlaybackRate(1.0)
    @property
    def active(self):return self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState
    def on_buffer(self,buf):
        if not buf.isValid():self.level=0;return
        fmt=buf.format();types={QAudioFormat.SampleFormat.Float:np.float32,QAudioFormat.SampleFormat.Int16:np.int16,QAudioFormat.SampleFormat.Int32:np.int32,QAudioFormat.SampleFormat.UInt8:np.uint8}
        dtype=types.get(fmt.sampleFormat())
        if dtype is None:return
        values=np.frombuffer(buf.constData(),dtype=dtype,count=buf.byteCount()//np.dtype(dtype).itemsize).astype(np.float32)
        if not len(values):return
        if dtype==np.uint8:values=(values-128)/128
        elif dtype!=np.float32:values/=float(np.iinfo(dtype).max)
        # RMS of decoded music; no mic/system-loopback capture, no per-frame FFT.
        self.level=min(.95,math.sqrt(float(np.mean(values*values)))*4.5);self.level_at=time.monotonic()
    def state_changed(self,*_):
        if not self.active:self.level=0;self.pet.engine.singing=False
        self.changed.emit()
    def media_changed(self,status):
        if status==QMediaPlayer.MediaStatus.EndOfMedia:self.stop()
    def on_error(self,error,message):self.error=message;self.stop();self.changed.emit()
    def play(self,path,title=None):
        path=supported_audio(path)
        if self.pet.engine.state=='cast':raise ValueError('请先结束爆裂演出，再播放歌曲。')
        if self.pet.assistant:
            self.pet.assistant.cancel()
            self.pet.assistant.mic.setChecked(False)
        self.pet.voice.stop();self.pet.voice.pending=None
        self.pet.engine.activity(time.monotonic(),self.pet.settings['idle_seconds']);self.pet.engine.state='idle'
        self.error='';self.title=title or path.stem
        self.player.setSource(QUrl.fromLocalFile(str(path)));self.player.setPlaybackRate(1.0);self.player.play();self.changed.emit()
    def pause(self):
        if self.active:self.player.pause()
        self.level=0;self.smoothed=0;self.pet.engine.singing=False;self.pet.engine.voice_mouth=None;self.changed.emit()
    def resume(self):
        if self.pet.engine.state=='cast':return
        if self.pet.assistant:
            self.pet.assistant.cancel();self.pet.assistant.mic.setChecked(False)
        self.pet.voice.stop();self.player.play()
    def stop(self):
        self.player.stop();self.level=0;self.smoothed=0;self.pet.engine.singing=False;self.pet.engine.voice_mouth=None;self.changed.emit()
    def tick(self,now,dt):
        self.pet.engine.singing=self.active and self.show
        if not self.active:return
        target=self.level if now-self.level_at<.4 else 0
        self.smoothed+=(target-self.smoothed)*(1-math.exp(-max(0,dt)/.055))
        self.pet.engine.voice_mouth=self.smoothed if self.show else 0

class MusicDialog(QDialog):
    def __init__(self,pet,store=None):
        super().__init__(pet);self.pet=pet;self.music=pet.music
        self.store=Path(store) if store else Path(os.environ.get('APPDATA',str(Path.home())))/'MeguminDesktopPet/music-library-v18.json'
        self.entries=[];self.external_status=''
        self.setWindowTitle('惠惠 · 歌曲与演唱 v18');self.resize(650,520);self.setMinimumSize(460,380)
        self.setWindowFlags(self.windowFlags()|Qt.WindowType.WindowMaximizeButtonHint)
        from assistant_ui import STYLE
        self.setStyleSheet(STYLE+'QListWidget{background:#302737;color:#ffe3be;border:1px solid #6c4f5e;border-radius:8px;padding:5px;} QListWidget::item:selected{background:#80404b;}')
        layout=QVBoxLayout(self);head=QLabel('♪ 原声音质 · 惠惠音乐时间');head.setStyleSheet('font-size:21px;color:#ffc99f;');layout.addWidget(head)
        note=QLabel('本地原声／已生成的翻唱：保留音频采样率和原速，支持嘴型与轻柔摇摆。\n网易云：在官方网页登录和播放；本程序不保存密码、不读取账号歌单，也不假装已经合成翻唱。');note.setWordWrap(True);layout.addWidget(note)
        row=QHBoxLayout();login=QPushButton('网易云官网／登录');login.clicked.connect(lambda:self.open_official(OFFICIAL));row.addWidget(login)
        search=QPushButton('找高桥李依的歌');search.clicked.connect(lambda:self.open_official(OFFICIAL+'#/search/m/?s='+quote('高橋李依')+'&type=1'));row.addWidget(search)
        link=QPushButton('添加网易云链接');link.clicked.connect(self.add_link);row.addWidget(link);layout.addLayout(row)
        self.list=QListWidget();self.list.itemDoubleClicked.connect(lambda _:self.play_selected());layout.addWidget(self.list,1)
        row=QHBoxLayout();add=QPushButton('添加本地歌曲');add.clicked.connect(self.add_files);row.addWidget(add)
        remove=QPushButton('移出列表');remove.clicked.connect(self.remove);row.addWidget(remove)
        self.perform=QCheckBox('嘴型／摇摆');self.perform.setChecked(True);self.music.show=True;self.perform.toggled.connect(self.set_perform);row.addWidget(self.perform)
        row.addStretch();layout.addLayout(row)
        row=QHBoxLayout();play=QPushButton('播放选中／打开网页');play.clicked.connect(self.play_selected);row.addWidget(play)
        self.pause_button=QPushButton('暂停／继续');self.pause_button.clicked.connect(lambda:self.music.pause() if self.music.active else self.music.resume());row.addWidget(self.pause_button)
        stop=QPushButton('停止本地播放');stop.clicked.connect(self.music.stop);row.addWidget(stop);layout.addLayout(row)
        self.seek=QSlider(Qt.Orientation.Horizontal);self.seek.sliderReleased.connect(lambda:self.music.player.setPosition(self.seek.value()));layout.addWidget(self.seek)
        row=QHBoxLayout();row.addWidget(QLabel('音乐音量'));self.volume=QSlider(Qt.Orientation.Horizontal);self.volume.setRange(0,100);self.volume.setValue(round(self.music.output.volume()*100));self.volume.valueChanged.connect(lambda n:self.music.output.setVolume(n/100));row.addWidget(self.volume);layout.addLayout(row)
        self.status=QLabel('尚未播放；麦克风不会自动开启。');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(300);self.music.changed.connect(self.refresh)
        try:
            raw=json.loads(self.store.read_text(encoding='utf-8'))
            for e in raw[:300]:
                if e.get('kind')=='netease':e['value']=normalize_netease_url(e['value'])
                elif e.get('kind')!='local':continue
                if not isinstance(e.get('title'),str) or not isinstance(e.get('value'),str):continue
                self.entries.append(e)
        except (OSError,ValueError,TypeError,KeyError):pass
        self.redraw()
    def set_perform(self,on):self.music.show=on;self.pet.engine.singing=self.music.active and on
    def save(self):
        try:
            self.store.parent.mkdir(parents=True,exist_ok=True);tmp=self.store.with_suffix('.tmp');tmp.write_text(json.dumps(self.entries,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(self.store)
        except OSError as exc:self.status.setText('列表保存失败：'+str(exc))
    def redraw(self):
        self.list.clear()
        for e in self.entries:self.list.addItem(('本地 ♪ ' if e['kind']=='local' else '网易云 ↗ ')+e['title'])
        if self.entries:self.list.setCurrentRow(0)
    def add_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'选择普通音频（原声或已合成翻唱）',str(Path.home()/'Music'),'歌曲 (*.wav *.mp3 *.flac *.ogg *.m4a *.aac);;全部文件 (*)')
        failures=[]
        for p in paths:
            try:
                p=supported_audio(p)
                if not any(e['value']==str(p) for e in self.entries):self.entries.append(dict(kind='local',value=str(p),title=p.stem))
            except ValueError as exc:failures.append(str(exc))
        self.redraw();self.save()
        if failures:QMessageBox.information(self,'音频检查','\n'.join(dict.fromkeys(failures)))
    def add_link(self):
        value,ok=QInputDialog.getText(self,'网易云歌曲链接','粘贴歌曲／歌单／专辑分享链接（不要填密码）：')
        if not ok:return
        try:url=normalize_netease_url(value)
        except ValueError as exc:self.status.setText(str(exc));return
        title,ok=QInputDialog.getText(self,'显示名称','歌名／歌单名：')
        if not ok:return
        self.entries.append(dict(kind='netease',value=url,title=title.strip()[:150] or '网易云歌曲'));self.redraw();self.save()
    def remove(self):
        row=self.list.currentRow()
        if 0<=row<len(self.entries):self.entries.pop(row);self.redraw();self.save()
    def open_official(self,url):
        self.external_status='已请求打开官方网页；请在网页登录和播放。桌宠无法确认外部播放状态或登录结果。'
        if not QDesktopServices.openUrl(QUrl(url)):self.status.setText('无法打开默认浏览器，请手动访问 music.163.com。')
        else:self.status.setText(self.external_status)
    def play_selected(self):
        row=self.list.currentRow()
        if not 0<=row<len(self.entries):self.status.setText('先添加并选中一首歌。');return
        e=self.entries[row]
        if e['kind']=='netease':self.music.stop();self.open_official(e['value']);return
        try:self.external_status='';self.music.play(e['value'],e['title'])
        except ValueError as exc:self.status.setText(str(exc))
    def refresh(self):
        if self.external_status:self.status.setText(self.external_status);return
        player=self.music.player
        if not self.seek.isSliderDown():self.seek.setRange(0,max(0,player.duration()));self.seek.setValue(player.position())
        if self.music.error:self.status.setText('播放失败：'+self.music.error)
        elif self.music.title:
            state='播放中' if self.music.active else ('暂停' if player.playbackState()==QMediaPlayer.PlaybackState.PausedState else '已停止')
            def stamp(ms):return f'{ms//60000}:{ms//1000%60:02}'
            self.status.setText(f'{state} · {self.music.title} · {stamp(player.position())} / {stamp(player.duration())}\n本地嘴型按音量联动（非音素识别）；聊天／爆裂会暂停或停止音乐。')
    def closeEvent(self,event):
        # Explicit close stops playback; no hidden background music.
        self.music.stop();super().closeEvent(event)
