"""Non-blocking Qt chat UI with bounded daemon HTTP workers."""
import threading,time
from PySide6.QtCore import Qt,Signal,QObject,QTimer
from PySide6.QtGui import QFont,QTextCursor
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QPlainTextEdit,QLineEdit,QComboBox,QFormLayout,QMessageBox,QCheckBox,QProgressBar)
from assistant_core import (ConfigStore,DEFAULT_CONFIG,PROVIDERS,local_reply,
    normalize_config,identity,stream_answer,check_connection,safe_error,Cancelled,compact_history)

STYLE='''QDialog{background:#201c2b;color:#f7e8db;} QLabel{color:#e5cbbd;}
QPlainTextEdit,QLineEdit,QComboBox{background:#302737;color:#fff1df;border:1px solid #6c4f5e;border-radius:7px;padding:8px;selection-background-color:#a14d42;}
QPushButton{background:#8e3e42;color:#fff0d8;border:1px solid #b8795b;border-radius:7px;padding:8px 12px;}
QPushButton:disabled{background:#46343c;color:#96878b;} QComboBox QAbstractItemView{background:#302737;color:#fff1df;}
QCheckBox{color:#f5dfca;spacing:7px;padding:3px;} QProgressBar{border:0;background:#453646;} QProgressBar::chunk{background:#ffbf78;}
'''

class Bridge(QObject):
    delta=Signal(int,str);done=Signal(int,str);failed=Signal(int,str)

class AsyncJob:
    def __init__(self,owner):
        self.bridge=Bridge(owner);self.serial=0;self.cancel_event=None
        self.running=0;self.lock=threading.Lock()
    def start(self,fn):
        with self.lock:
            if self.running>=2:raise ValueError('前一个网络请求正在关闭，请稍后再试。')
            self.running+=1
        self.serial+=1;serial=self.serial;cancel=threading.Event();self.cancel_event=cancel
        def run():
            try:
                result=fn(cancel,lambda value:self.bridge.delta.emit(serial,value))
                if not cancel.is_set():self.bridge.done.emit(serial,result)
            except Cancelled:pass
            except Exception as exc:
                if not cancel.is_set():
                    try:self.bridge.failed.emit(serial,safe_error(exc))
                    except RuntimeError:pass
            finally:
                with self.lock:self.running-=1
        threading.Thread(target=run,name='MeguminAI',daemon=True).start();return serial
    def cancel(self):
        if self.cancel_event:self.cancel_event.set()
        self.serial+=1

class Composer(QPlainTextEdit):
    submitted=Signal()
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and not event.modifiers()&Qt.KeyboardModifier.ShiftModifier:
            self.submitted.emit();event.accept()
        else:super().keyPressEvent(event)

class AISettings(QDialog):
    def __init__(self,pet,store=None):
        super().__init__(pet);self.pet=pet;self.store=store or ConfigStore();self.cfg=self.store.load()
        self.setWindowTitle('惠惠 · AI 连接设置');self.resize(550,430);self.setStyleSheet(STYLE)
        self.job=AsyncJob(self);self.job.bridge.done.connect(self.test_done);self.job.bridge.failed.connect(self.test_failed)
        layout=QVBoxLayout(self);title=QLabel('连接一个真正的 AI');title.setFont(QFont('Microsoft YaHei UI',16,QFont.Weight.Bold));layout.addWidget(title)
        form=QFormLayout();self.provider=QComboBox()
        for key,label in PROVIDERS.items():self.provider.addItem(label,key)
        self.provider.setCurrentIndex(self.provider.findData(self.cfg['provider']))
        self.url=QLineEdit(self.cfg['base_url']);self.url.setPlaceholderText('https://服务地址/v1')
        self.model=QLineEdit(self.cfg['model']);self.model.setPlaceholderText('填写账户/本地实际可用的模型 ID')
        self.key=QLineEdit();self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText('已安全保存；留空保留同一服务的密钥' if self.store.key(self.cfg) else 'API Key（只在此处填写）')
        for label,widget in [('服务类型',self.provider),('Base URL',self.url),('模型名称',self.model),('密钥',self.key)]:form.addRow(label,widget)
        layout.addLayout(form);self.hint=QLabel();self.hint.setWordWrap(True);layout.addWidget(self.hint)
        self.result=QLabel();self.result.setWordWrap(True);layout.addWidget(self.result)
        privacy=QLabel('仅发送主动提交的问题，或手动开启麦克风后转写的文字及最近对话；原始录音不上传。\n不读取屏幕、剪贴板、其他软件输入或文件。聊天只在内存；API 可能收费。')
        privacy.setWordWrap(True);privacy.setStyleSheet('color:#baa4b3;font-size:12px;');layout.addWidget(privacy)
        row=QHBoxLayout();self.test=QPushButton('检查连接');self.save_button=QPushButton('保存');forget=QPushButton('删除已保存密钥')
        self.test.clicked.connect(self.test_connection);self.save_button.clicked.connect(self.save);forget.clicked.connect(self.forget)
        for widget in (self.test,forget,self.save_button):row.addWidget(widget)
        layout.addLayout(row);self.provider.currentIndexChanged.connect(self.provider_changed);self.update_fields(False)
    def update_fields(self,reset):
        provider=self.provider.currentData();offline=provider=='offline'
        if reset:self.key.clear();self.model.clear();self.key.setPlaceholderText('新服务的 API Key')
        self.url.setEnabled(not offline);self.model.setEnabled(not offline);self.key.setEnabled(not offline and provider!='ollama')
        self.url.setReadOnly(provider=='openai')
        if provider=='openai':self.url.setText('https://api.openai.com/v1')
        elif reset:self.url.setText('http://127.0.0.1:11434' if provider=='ollama' else '')
        self.hint.setText('不调用网络：计算、时间、提醒和互动可直接使用。' if offline else
            ('请先自行启动 Ollama 并下载模型。不会自动安装大型模型，也不会占用 GPU 推理直到你发问。' if provider=='ollama' else
             '需要你自己的服务账户/API Key。填写模型 ID；兼容接口使用 Chat Completions，OpenAI 使用 Responses。'))
    def provider_changed(self):self.job.cancel();self.test.setEnabled(True);self.result.clear();self.update_fields(True)
    def values(self):
        cfg=normalize_config(dict(provider=self.provider.currentData(),base_url=self.url.text(),model=self.model.text()))
        key=self.key.text().strip() or self.store.key(cfg)
        if cfg['provider']=='openai' and not key:raise ValueError('请填写你自己的 OpenAI API Key。')
        return cfg,key
    def test_connection(self):
        try:
            cfg,key=self.values();self.job.start(lambda cancel,delta:check_connection(cfg,key));self.test.setEnabled(False);self.result.setText('检查中……（不生成回答）')
        except ValueError as exc:self.result.setText(str(exc))
    def test_done(self,serial,text):
        if serial!=self.job.serial:return
        self.test.setEnabled(True);self.result.setText(text)
    def test_failed(self,serial,text):self.test_done(serial,text)
    def save(self):
        try:
            cfg,key=self.values();self.store.save(cfg,key if self.key.text().strip() else None)
        except (OSError,ValueError,RuntimeError) as exc:self.result.setText(safe_error(exc));return
        if getattr(self.pet,'assistant',None):self.pet.assistant.configuration_changed()
        self.accept()
    def forget(self):
        self.store.forget_key();self.key.clear();self.key.setPlaceholderText('已删除密钥');self.result.setText('密钥已删除；网络问答可能需要重新填写。')
    def closeEvent(self,event):self.job.cancel();super().closeEvent(event)
    def done(self,result):self.job.cancel();super().done(result)

class AssistantDialog(QDialog):
    def __init__(self,pet,store=None):
        super().__init__(pet);self.pet=pet;self.store=store or ConfigStore();self.history=[];self.busy=False;self.answer='';self.pending_action=None;self.reminders=[]
        self.setWindowTitle('惠惠 · 桌面小助手 v20');self.resize(700,720);self.setMinimumSize(420,420);self.setStyleSheet(STYLE)
        self.setWindowFlags(self.windowFlags()|Qt.WindowType.WindowMinimizeButtonHint|Qt.WindowType.WindowMaximizeButtonHint)
        self.last_reply_from_voice=False
        self.reply_bilingual=False;self.streamed_segments=0;self.spoken_segments=set()
        self.job=AsyncJob(self);self.job.bridge.delta.connect(self.on_delta);self.job.bridge.done.connect(self.on_done);self.job.bridge.failed.connect(self.on_failed)
        layout=QVBoxLayout(self);top=QHBoxLayout();title=QLabel('MEGUMIN  /  和惠惠聊聊');title.setFont(QFont('Microsoft YaHei UI',16,QFont.Weight.Bold))
        settings=QPushButton('AI 设置');settings.clicked.connect(self.open_settings);top.addWidget(title);top.addStretch()
        songs=QPushButton('♪ 歌曲');songs.clicked.connect(pet.open_music);top.addWidget(songs);top.addWidget(settings);layout.addLayout(top)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        from speech_conversation import SpeechConversation
        from app import ASSETS
        from PySide6.QtMultimedia import QMediaDevices
        self.speech=SpeechConversation(self,pet,ASSETS)
        controls=QHBoxLayout();self.mic=QCheckBox('开启麦克风对话');self.mic.setChecked(False)
        self.read_answers=QCheckBox('语音回复');self.read_answers.setChecked(True)
        self.read_answers.setToolTip('文字和麦克风问题都用日语回复、配中文说明；音质优先，整段自然合成，不切碎音频或加速播放。')
        self.devices=QComboBox();self.devices.addItem('系统默认麦克风',None)
        for device in QMediaDevices.audioInputs():self.devices.addItem(device.description(),device)
        stop_speech=QPushButton('停止朗读');stop_speech.clicked.connect(self.speech.stop_reply)
        controls.addWidget(self.mic);controls.addWidget(self.read_answers);controls.addWidget(self.devices,1);controls.addWidget(stop_speech);layout.addLayout(controls)
        self.mic_status=QLabel('麦克风：关闭（未采集）');self.mic_status.setWordWrap(True);layout.addWidget(self.mic_status)
        self.heard_text=QLabel();self.heard_text.setWordWrap(True);layout.addWidget(self.heard_text)
        self.meter=QProgressBar();self.meter.setRange(0,100);self.meter.setValue(0);self.meter.setTextVisible(False);self.meter.setMaximumHeight(6);layout.addWidget(self.meter)
        notice=QLabel('开启期间连续监听、自动提交转写文字；关闭即释放麦克风。语音识别在本地进行。')
        notice.setWordWrap(True);notice.setStyleSheet('color:#baa4b3;font-size:11px;');layout.addWidget(notice)
        self.mic.toggled.connect(self.toggle_microphone);self.devices.currentIndexChanged.connect(self.change_microphone)
        self.read_answers.toggled.connect(lambda enabled:None if enabled else self.speech.stop_reply())
        self.speech.status.connect(self.mic_status.setText);self.speech.level.connect(self.meter.setValue)
        self.speech.partial.connect(lambda text:self.heard_text.setText('识别：'+text if text else ''))
        self.speech.heard.connect(self.send_voice);self.speech.disabled.connect(self.disable_mic_switch)
        self.transcript=QPlainTextEdit();self.transcript.setReadOnly(True);self.transcript.document().setMaximumBlockCount(2500);self.transcript.setFont(QFont('Microsoft YaHei UI',11));layout.addWidget(self.transcript,1)
        quick=QHBoxLayout()
        for label,text in [('现在几点','现在几点'),('计算','计算 (128+64)*3'),('提醒喝水','10分钟后提醒我喝水'),('使用帮助','你能做什么')]:
            button=QPushButton(label);button.clicked.connect(lambda checked=False,t=text:self.prefill(t));quick.addWidget(button)
        layout.addLayout(quick)
        self.confirm=QPushButton('确认执行桌宠互动');self.confirm.hide();self.confirm.clicked.connect(self.run_action);layout.addWidget(self.confirm)
        self.input=Composer();self.input.setMaximumHeight(110);self.input.setPlaceholderText('输入问题，Enter 发送，Shift+Enter 换行。最多 4000 字。');self.input.submitted.connect(self.send);layout.addWidget(self.input)
        row=QHBoxLayout();clear=QPushButton('清空对话');self.send_button=QPushButton('发送');self.stop=QPushButton('停止生成');self.stop.setEnabled(False)
        clear.clicked.connect(self.clear);self.send_button.clicked.connect(self.send);self.stop.clicked.connect(self.cancel)
        row.addWidget(clear);row.addStretch();row.addWidget(self.stop);row.addWidget(self.send_button);layout.addLayout(row)
        self.append('惠惠','红魔族的天才大魔法师，惠惠！文字或麦克风都能和我聊天；勾选「语音回复」就能听到日语回答。\n现在是音质优先：自然合成整段台词，不抢先切碎声音。麦克风默认关闭，文字聊天不用开麦。\n提醒和桌宠互动需确认；关闭窗口停止监听与朗读。')
        self.configuration_changed()
        if not getattr(pet,'test_mode',True):self.speech.speaker.service.prewarm()
    def append(self,speaker,text):self.transcript.appendPlainText(f'{speaker}：\n{text}\n')
    def prefill(self,text):self.input.setPlainText(text);self.input.setFocus()
    def open_settings(self):
        dialog=AISettings(self.pet,self.store);dialog.exec();self.configuration_changed()
    def configuration_changed(self):
        self.cancel();self.speech.stop_reply();self.history=[];cfg=self.store.load();self.status.setText('当前：'+PROVIDERS[cfg['provider']]+(' / '+cfg['model'] if cfg['model'] else '')+' · 高音质日语 / 对话不落盘')
    def set_busy(self,value):
        self.busy=value;self.send_button.setEnabled(not value);self.stop.setEnabled(value)
    def toggle_microphone(self,enabled):
        if enabled:self.speech.enable(self.devices.currentData())
        else:
            if self.last_reply_from_voice and self.busy:self.cancel()
            stop_readout=self.last_reply_from_voice;self.last_reply_from_voice=False;self.speech.disable(stop_reply=stop_readout)
        self.devices.setEnabled(not enabled)
    def change_microphone(self):
        if self.mic.isChecked():self.mic.setChecked(False)
    def disable_mic_switch(self):
        self.mic.blockSignals(True);self.mic.setChecked(False);self.mic.blockSignals(False);self.devices.setEnabled(True)
    def send_voice(self,text):
        if not self.mic.isChecked():return
        if text in ('关闭麦克风','停止监听','关闭语音对话'):
            self.mic.setChecked(False);self.append('系统','已按语音指令关闭麦克风。');return
        if self.busy or self.input.toPlainText().strip():
            self.status.setText('语音已转写；当前正在回答或存在未发送草稿，未自动提交。');return
        self.pet.engine.activity(time.monotonic(),self.pet.settings['idle_seconds'])
        self.input.setPlainText(text);self.send(from_voice=True)
    def send(self,from_voice=False):
        if self.busy:return
        text=self.input.toPlainText().strip()
        if not text:return
        if len(text)>4000:self.status.setText('问题超过 4000 字，请缩短后发送。');return
        self.pet.music.pause()
        self.last_reply_from_voice=bool(from_voice)
        self.reply_bilingual=bool(from_voice or self.read_answers.isChecked());self.streamed_segments=0;self.spoken_segments=set()
        self.speech.stop_reply()
        self.pending_action=None;self.confirm.hide();self.input.clear();self.append('你',text)
        flat=text.strip(' 。！？!?')
        if flat in ('唱歌','听歌','播放音乐','打开音乐','唱嘘月','唱一首歌'):
            self.pet.open_music();self.append('系统','歌曲面板已打开：可播放普通音频并联动嘴型。模型翻唱须先完成演唱音频生成，不会把原曲标成模型演唱。');return
        if flat in ('安静','安静一点','保持安静','别说话','停止语音','恢复语音','可以说话了'):
            quiet=flat not in ('恢复语音','可以说话了');self.pet.dialogue_quiet=quiet
            self.read_answers.setChecked(not quiet)
            self.append('惠惠','好，我安静陪着你。需要我时再叫我。' if quiet else '我回来了。有什么事就说吧！')
            if not quiet:self.speech.reply('我回来了。有什么事就说吧！',ja='戻りましたよ。何かあったら呼んでくださいね。')
            return
        reply=local_reply(text)
        if reply:
            self.append('惠惠',reply.text);self.pending_action=reply
            if reply.action:
                self.confirm.setText('确认添加提醒' if reply.action=='reminder' else '确认执行桌宠互动');self.confirm.show()
            self.pet.engine.say(reply.text,time.monotonic(),max(8,len(reply.text)/4))
            if self.read_answers.isChecked():self.speech.reply(reply.text,reply.scene,reply.ja or '内容を確認してください。')
            return
        cfg=self.store.load()
        if cfg['provider']=='offline':
            reply='这个问题需要真正的 AI。打开右上角「AI 设置」，填写服务与模型，就能进行通用问答。当前仅本地规则功能可用。'
            self.append('惠惠',reply)
            if self.read_answers.isChecked():self.speech.reply(reply,ja='この質問にはAIの接続が必要です。設定を確認してください。')
            return
        key=self.store.key(cfg);candidate=compact_history(self.history+[dict(role='user',content=text)])
        self.answer='';self.append('惠惠','');self.answer_cursor=self.transcript.textCursor();self.answer_cursor.movePosition(QTextCursor.MoveOperation.End)
        self.answer_cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock)
        self.set_busy(True);self.status.setText('惠惠正在思考……动画继续运行。')
        try:
            from megumin_persona import program_context
            context=program_context(self.pet)
            if self.reply_bilingual:
                from japanese_reply import bilingual_answer
                self.job.start(lambda cancel,delta:bilingual_answer(cfg,key,candidate,cancel,delta,context))
            else:
                from assistant_core import PROMPT
                self.job.start(lambda cancel,delta:stream_answer(cfg,key,candidate,cancel,delta,system_prompt=PROMPT+context))
            self.candidate=candidate
        except ValueError as exc:self.set_busy(False);self.append('系统',str(exc))
    def on_delta(self,serial,text):
        if serial!=self.job.serial or not self.busy:return
        if self.reply_bilingual:
            import json
            from japanese_reply import validate_segment
            obj=json.loads(text);index=obj.get('index',self.streamed_segments)
            if obj.get('kind')=='ja_ready':
                return
            segment=validate_segment(obj);ja=segment['ja'];zh=segment['zh']
            self.streamed_segments+=1
            # Quality mode only displays the final validated/repaired answer.
            # Do not show an invalid prefix that may be replaced by a repair.
            self.answer+=ja+'\n中文：'+zh+'\n';return
        self.answer+=text;self.answer_cursor.insertText(text);self.transcript.ensureCursorVisible()
    def on_done(self,serial,text):
        if serial!=self.job.serial or not self.busy:return
        ja=None
        if self.reply_bilingual:
            from japanese_reply import parse_reply
            try:
                reply=parse_reply(text,allow_text_only=True);ja=reply['ja'];text=reply['zh']
                # Replace preview with the complete normalized/repaired reply.
                # This also keeps valid Chinese visible when only speech fails.
                rendered=''.join(s['ja']+'\n中文：'+s['zh']+'\n' for s in reply.get('segments',[])) if ja else text+'\n'
                self.answer_cursor.insertText(rendered)
                self.speech.speaker.finish()
            except (ValueError,TypeError):self.on_failed(serial,'AI 没有返回日语回复与中文字幕，请重试。');return
        self.history=compact_history(self.candidate+[dict(role='assistant',content=text)])
        self.set_busy(False);self.transcript.appendPlainText('');self.status.setText('回答完成。Enter 继续提问。')
        self.pet.engine.say(text,time.monotonic(),max(10,min(180,len(text)/4+4)))
        if self.reply_bilingual and self.read_answers.isChecked():
            if ja:self.speech.reply(text,ja=ja)
            else:self.mic_status.setText('AI 日语格式仍异常，已保留中文回答；本次不播放不可靠语音。')
    def on_failed(self,serial,text):
        if serial!=self.job.serial or not self.busy:return
        self.speech.stop_reply()
        self.set_busy(False);self.append('系统',text+'\n本次未完成的回答不加入后续对话。');self.status.setText('连接/生成失败，可修改配置后重试。')
    def cancel(self):
        was_busy=self.busy;self.job.cancel();self.set_busy(False);self.speech.stop_reply()
        if was_busy:self.append('系统','已停止接收；本次未完成回答不加入上下文。远端请求可能直到连接关闭才停止。')
    def clear(self):
        self.cancel();self.history=[];self.transcript.clear();self.pending_action=None;self.confirm.hide();self.configuration_changed()
    def run_action(self):
        reply=self.pending_action;self.pending_action=None;self.confirm.hide()
        if not reply or not reply.action:return
        if reply.action=='reminder':
            if len(self.reminders)>=10:self.append('系统','最多同时保留 10 个提醒。');return
            timer=QTimer(self);timer.setSingleShot(True)
            def remind():
                if timer in self.reminders:self.reminders.remove(timer)
                text='提醒：'+reply.reminder;self.append('惠惠',text);self.pet.engine.say(text,time.monotonic(),10)
                if self.pet.tray:self.pet.tray.showMessage('惠惠提醒你',reply.reminder)
                timer.deleteLater()
            timer.timeout.connect(remind);self.reminders.append(timer);timer.start(reply.seconds*1000);self.append('系统','提醒已添加；退出桌宠后不会继续计时。')
        elif reply.action=='greeting':self.pet.time_greeting(force=True)
        else:self.pet.action(reply.action)
    def closeEvent(self,event):
        self.mic.setChecked(False);self.speech.disable();self.cancel();super().closeEvent(event)
    def done(self,result):
        self.mic.setChecked(False);self.speech.disable();self.cancel();super().done(result)
