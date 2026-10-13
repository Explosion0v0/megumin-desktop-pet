"""A compact speech balloon that grows with text and scrolls long replies."""
import time
from PySide6.QtCore import Qt,QRect,QRectF,QTimer
from PySide6.QtGui import QFont,QFontMetrics,QPainter,QPainterPath,QColor,QPen
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QScrollArea,
    QPushButton,QCheckBox,QApplication,QDialog,QPlainTextEdit,QMenu,QSizePolicy,QLayout)

class ReadingBubble(QWidget):
    def __init__(self,pet):
        super().__init__(pet,Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        self.pet=pet;self.source='';self.dismissed='';self.deadline=0;self.detail=None;self.layout_key=None
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.tail_size=9;self.tail_on_top=False;self.tail_x=85
        self.setObjectName('readingBubble')
        self.setStyleSheet('''QWidget#readingBubble{background:transparent;border:0;}
        QLabel{color:#ffe3be;background:transparent;border:0;} QScrollArea{border:0;background:transparent;}
        QScrollArea>QWidget{background:transparent;} QScrollArea>QWidget>QWidget{background:transparent;}
        QScrollBar:vertical{background:transparent;width:7px;margin:2px 0;}
        QScrollBar::handle:vertical{background:#a46e68;border-radius:3px;min-height:22px;}
        QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:transparent;}''')
        layout=QVBoxLayout(self);layout.setContentsMargins(14,10,14,10+self.tail_size);layout.setSpacing(0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text=QLabel();self.text.setWordWrap(True);self.text.setTextFormat(Qt.TextFormat.PlainText)
        self.text.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.text.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.text.setMinimumWidth(0)
        self.scroll.setWidget(self.text);layout.addWidget(self.scroll,1)
        # Keep existing pin/full API, but do not reserve a permanent toolbar.
        self.pin=QCheckBox('保留',self);self.pin.hide()
        self.full=QPushButton('全文',self);self.full.clicked.connect(self.open_full);self.full.hide()
        self.setToolTip('长回复可滚轮阅读；右键可保留、查看全文、复制或收起')
        self.text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text.customContextMenuRequested.connect(lambda pos:self.open_menu(self.text.mapToGlobal(pos)))
        self.timer=QTimer(self);self.timer.timeout.connect(self.expire);self.timer.start(250)
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(),Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        top=self.tail_size if self.tail_on_top else 0
        body=QPainterPath();body.addRoundedRect(QRectF(.7,top+.7,self.width()-1.4,self.height()-self.tail_size-1.4),14,14)
        x=max(22,min(self.width()-22,self.tail_x));tail=QPainterPath()
        if self.tail_on_top:
            tail.moveTo(x-8,self.tail_size+1);tail.lineTo(x,1);tail.lineTo(x+8,self.tail_size+1)
        else:
            y=self.height()-self.tail_size-1
            tail.moveTo(x-8,y);tail.lineTo(x,self.height()-1);tail.lineTo(x+8,y)
        tail.closeSubpath();body=body.united(tail)
        painter.setPen(QPen(QColor('#9c5f59'),1));painter.setBrush(QColor(34,26,43,238));painter.drawPath(body)
    def open_menu(self,position):
        menu=QMenu(self);keep=menu.addAction('保留气泡');keep.setCheckable(True);keep.setChecked(self.pin.isChecked())
        keep.triggered.connect(self.pin.setChecked)
        menu.addAction('查看全文',self.open_full)
        menu.addAction('复制完整台词',lambda:QApplication.clipboard().setText(self.source))
        menu.addSeparator();menu.addAction('收起气泡',self.dismiss);menu.exec(position)
    def contextMenuEvent(self,event):self.open_menu(event.globalPos())
    def wheelEvent(self,event):
        bar=self.scroll.verticalScrollBar()
        if bar.maximum()>0:
            delta=event.pixelDelta().y() or event.angleDelta().y()/120*QFontMetrics(self.text.font()).lineSpacing()*3
            bar.setValue(bar.value()-round(delta));event.accept()
        else:event.ignore()
    def dismiss(self):self.dismissed=self.source;self.hide()
    def expire(self):
        if self.isVisible() and not self.pin.isChecked() and not self.underMouse() and time.monotonic()>self.deadline:self.dismiss()
    def present(self,message,anchor,screen,scale=1.0):
        if not message:return
        changed=message!=self.source
        if changed:
            self.source=message;self.dismissed='';self.text.setText(message)
            self.deadline=time.monotonic()+max(10,min(180,len(message)/4+4))
            self.scroll.verticalScrollBar().setValue(0)
            if self.detail:self.detail.setPlainText(message)
        if self.dismissed==message:return
        self.deadline=max(self.deadline,time.monotonic()+2)
        key=(message,screen.width(),screen.height(),round(scale,2))
        if key!=self.layout_key:
            self.layout_key=key;font=QFont('Microsoft YaHei UI');font.setPixelSize(round(16*max(.85,min(1.4,scale))));font.setWeight(QFont.Weight.DemiBold)
            self.text.setFont(font);fm=QFontMetrics(font)
            limit=max(40,min(screen.width()-16,round(384*scale)))
            natural=max((fm.horizontalAdvance(line) for line in message.splitlines()),default=0)+36
            width=min(limit,max(round(170*max(.7,scale)),natural))
            text_width=max(20,width-36)
            h=fm.boundingRect(QRect(0,0,text_width,100000),int(Qt.TextFlag.TextWordWrap),message).height()+8
            short='\n' not in message and natural<=limit
            self.text.setAlignment((Qt.AlignmentFlag.AlignHCenter if short else Qt.AlignmentFlag.AlignLeft)|Qt.AlignmentFlag.AlignTop)
            # Grow naturally until the reading limit; keep every line in the scroll area.
            h=max(h,self.text.heightForWidth(text_width))
            cap=max(35,min(round(280*max(.7,scale)),screen.height()-16))
            self.text.setMinimumHeight(h);self.resize(width,min(max(54,h+20+self.tail_size),cap))
        x=anchor.center().x()-self.width()//2;y=anchor.top()-self.height()-6
        on_top=False
        if y<screen.top()+8:
            if anchor.bottom()+6+self.height()<=screen.bottom()-8:y=anchor.bottom()+6;on_top=True
            else:y=anchor.top()+max(8,round(4*scale))
        x=max(screen.left()+8,min(x,screen.right()-self.width()-7));y=max(screen.top()+8,min(y,screen.bottom()-self.height()-7))
        self.tail_on_top=on_top;self.tail_x=anchor.center().x()-x
        self.layout().setContentsMargins(14,10+(self.tail_size if on_top else 0),14,10+(0 if on_top else self.tail_size))
        self.move(x,y)
        self.update()
        if not self.isVisible():self.show()
    def sync(self,message,active=True):
        if not self.pet:return
        if self.pet.hidden_by_user or self.pet.overlay.active or not self.pet.isVisible():self.hide();return
        if active and message:
            screen=QApplication.screenAt(self.pet.geometry().center()) or QApplication.primaryScreen()
            self.present(message,self.pet.geometry(),screen.availableGeometry(),self.pet.settings['scale']/100)
        elif self.isVisible() and not self.pin.isChecked():self.expire()
    def open_full(self):
        if self.detail is None:
            dialog=QDialog(self);dialog.setWindowTitle('惠惠 · 完整台词');dialog.resize(650,420)
            dialog.setWindowFlags(dialog.windowFlags()|Qt.WindowType.WindowMaximizeButtonHint)
            layout=QVBoxLayout(dialog);self.detail=QPlainTextEdit();self.detail.setReadOnly(True);self.detail.setFont(self.text.font());layout.addWidget(self.detail)
            self.detail_dialog=dialog
        self.detail.setPlainText(self.source);self.detail_dialog.show();self.detail_dialog.raise_();self.detail_dialog.activateWindow()
    def close_all(self):
        self.timer.stop()
        if self.detail:self.detail_dialog.close()
        self.close()
