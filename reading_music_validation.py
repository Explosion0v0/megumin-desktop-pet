"""Native widget/media checks with a generated tone; never capture the microphone."""
import time,tempfile,json,wave
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PySide6.QtCore import QRect,Qt,QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer
from assistant_validation import pump_until

def check_reading_music(pet,preview=None,real_song=None):
    from app import Engine
    from music_player import MusicDialog,normalize_netease_url,supported_audio
    from reading_bubble import ReadingBubble
    r={};old_engine=pet.engine;old_assistant=pet.assistant;pet.engine=Engine()
    message='最喜欢的当然是爆裂魔法的虹色光啊，像大炸开的光一样，帅到不行。其次勉强算是黑色吧。怎么，想送礼物给本大魔法师吗？\n'+('这是一个需要完整阅读的回答，可以滚动查看，不会省略开头和结尾。'*20)+'\n最后一句也完整保留。'
    b=ReadingBubble(pet);pet.show();QApplication.processEvents()
    with tempfile.TemporaryDirectory() as tmp:
        d=MusicDialog(pet,Path(tmp)/'library.json')
        try:
            screen=QRect(0,0,800,600)
            for scale in (.6,1.,1.6):
                b.present(message,QRect(-20,-30,480,450),screen,scale);QApplication.processEvents()
                r['clamped_at_scale_'+str(scale)]=screen.contains(b.geometry())
            r['full_bubble_text_preserved']=b.text.text()==message
            bar=b.scroll.verticalScrollBar();r['long_text_scrolls']=bar.maximum()>0;bar.setValue(bar.maximum());QApplication.processEvents();r['scroll_reaches_last_line']=bar.value()==bar.maximum()
            b.open_full();r['full_text_dialog']=b.detail.toPlainText()==message and b.detail_dialog.isVisible()
            b.pin.setChecked(True);b.deadline=0;b.expire();r['pinned_text_stays']=b.isVisible()
            b.dismiss();r['dismiss_works']=not b.isVisible();b.present('下一条完整回复',QRect(180,300,480,450),screen,1);r['new_message_reopens']=b.isVisible()
            r['netease_link_strips_user_metadata']=normalize_netease_url('https://y.music.163.com/m/song?id=12345&userid=888')=='https://music.163.com/#/song?id=12345'
            for i,url in enumerate(['javascript:alert(1)','https://music.163.com.evil.test/#/song?id=1','https://music.163.com/#/song?id=x','https://secret@music.163.com/#/song?id=1']):
                try:normalize_netease_url(url);r['unsafe_link_rejected_'+str(i)]=False
                except ValueError:r['unsafe_link_rejected_'+str(i)]=True
            ncm=Path(tmp)/'fake.mp3';ncm.write_bytes(b'CTENFDAM'+bytes(100))
            try:supported_audio(ncm);r['ncm_never_decoded']=False
            except ValueError:r['ncm_never_decoded']=True
            tone=Path(tmp)/'fixture.wav';sr=44100;n=np.arange(sr*4);envelope=np.where(n<sr*2,.2,.01);pcm=(np.sin(n*2*np.pi*330/sr)*envelope*32767).astype('<i2')
            with wave.open(str(tone),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm.tobytes())
            pet.music.output.setVolume(.01);pet.music.play(tone,'本地播放检查');pump_until(lambda:pet.music.active and pet.music.level>0,8)
            pet.music.tick(time.monotonic(),.1)
            r['real_decoder_audio_buffer']=pet.music.active and pet.music.level>0
            r['mouth_driven_without_mic']=bool(pet.engine.singing) and pet.engine.voice_mouth>0
            r['normal_speed_quality']=pet.music.player.playbackRate()==1.0
            r['music_suppresses_idle_voice']=not pet.conversation_settings()['voice_enabled'] and not pet.conversation_settings()['idle_enabled']
            pet.music.pause();r['pause_stops_mouth']=not pet.engine.singing and not pet.music.active
            pet.music.resume();pump_until(lambda:pet.music.active,3)
            pet.music.stop();r['stop_stops_mouth']=not pet.music.active and pet.engine.voice_mouth is None
            if real_song:
                pet.music.play(real_song);pump_until(lambda:pet.music.player.duration()>0 or bool(pet.music.error),10)
                pet.music.player.setPosition(45000);pump_until(lambda:pet.music.player.position()>45000 and pet.music.level>0,10)
                r['provided_flac_decodes']=pet.music.active and pet.music.player.duration()>280000 and pet.music.level>0
                r['provided_flac_duration_ms']=pet.music.player.duration();pet.music.pause()
            from assistant_core import ConfigStore,DEFAULT_CONFIG
            from assistant_ui import AssistantDialog
            store=ConfigStore(Path(tmp)/'ai');store.save(DEFAULT_CONFIG);a=AssistantDialog(pet,store);pet.assistant=a
            try:
                a.read_answers.setChecked(False);a.input.setPlainText('唱歌');a.send();r['chat_music_command']=pet.music_dialog is not None and pet.music_dialog.isVisible() and not a.mic.isChecked()
                a.input.setPlainText('计算 (128+64)*3');a.send();r['chat_still_works']='576' in a.transcript.toPlainText()
                r['chat_maximizes']=bool(a.windowFlags()&Qt.WindowType.WindowMaximizeButtonHint)
                # AI callback itself must retain the entire bubble, not [:88].
                a.busy=True;a.reply_bilingual=False;a.candidate=[{'role':'user','content':'长回答'}];a.answer_cursor=a.transcript.textCursor();a.on_done(a.job.serial,message)
                r['no_answer_truncation']=pet.engine.bubble==message
                r['mic_not_opened']=a.speech.microphone_open_count==0 and not a.mic.isChecked()
            finally:a.close();a.deleteLater();pet.assistant=old_assistant
            with patch('music_player.QDesktopServices.openUrl',return_value=True) as opened:
                d.open_official('https://music.163.com/');r['official_login_opens_without_credentials']=opened.call_count==1 and '登录结果' in d.status.text()
            if preview:
                b.present(message,QRect(80,350,480,450),QRect(0,0,960,900),1.2);QApplication.processEvents();b.grab().save(str(Path(preview)/'长回答气泡.png'))
                d.status.setText('歌曲面板：本地原声／已生成翻唱；网易云登录在官方网页完成。');d.show();QApplication.processEvents();d.grab().save(str(Path(preview)/'歌曲面板.png'))
            r['reading_music_checks_passed']=all(v for k,v in r.items() if k!='provided_flac_duration_ms');return r
        finally:
            pet.music.stop();pet.music.player.setSource(QUrl());pet.music.output.setVolume(.6);d.close();d.deleteLater();b.close_all();b.deleteLater()
            end=time.monotonic()+.3
            while time.monotonic()<end:QApplication.processEvents();time.sleep(.01)
            if pet.music_dialog:pet.music_dialog.close()
            pet.engine=old_engine;pet.assistant=old_assistant
