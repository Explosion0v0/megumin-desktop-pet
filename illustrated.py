"""Live 2D renderer using an unchanged official transparent illustration.

Artwork source: https://konosuba.com/bakuen/character/img/megmin-2.png
Animation transforms, expression overlays, and interaction objects are drawn
at runtime. The original PNG is retained byte-for-byte.
"""
import math
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QPixmap,QPainter,QPainterPath,QPen,QColor,QLinearGradient,QRegion,QFont,QRadialGradient


class IllustratedCharacter:
    def __init__(self,path):
        self.art=QPixmap(str(path))
        if self.art.isNull():raise RuntimeError('官方立绘素材缺失')
        self.region_cache={}
        self.full_body=False
        # The original image is 976×1378. The desktop uses a larger waist-up
        # framing; casting shows the complete illustration and staff.
        self.crop=QRectF(0,45,976,790)
        self.target=QRectF(91,130,298,790*298/976)

    def draw_image(self,p,state,now,reduced):
        full=state=='cast' or self.full_body
        source=QRectF(self.art.rect()) if full else self.crop
        target=QRectF(138,105,286*976/1378,286) if full else self.target
        # Fine image bands give the cape a very small continuous sway while
        # preserving the original texture and its alpha, without new image files.
        bands=28
        for i in range(bands):
            fraction=i/bands
            src=QRectF(source.x(),source.y()+source.height()*fraction,
                       source.width(),source.height()/bands)
            dx=0 if reduced else math.sin(now*1.7+fraction*2.6)*(.45+fraction*.65)
            dst=QRectF(target.x()+dx,target.y()+target.height()*fraction,
                      target.width(),target.height()/bands+.25)
            p.save()
            if not full and i>bands-4:p.setOpacity(p.opacity()*(bands-i-.5)/3)
            p.drawPixmap(dst,self.art,src)
            p.restore()
        return target,source

    def draw(self,p,engine,now,reduced=False,for_mask=False):
        state=engine.pose(now);age=max(0,now-engine.since)
        p.save()
        target,source=self.draw_image(p,state,now,reduced or for_mask)
        if state!='cast':
            # Image-space positions are mapped using the same crop as the art.
            sx=target.width()/source.width();sy=target.height()/source.height()
            p.save();p.translate(target.x()-source.x()*sx,target.y()-source.y()*sy);p.scale(sx,sy)
            blink=(now%4.7)>.0 and (now%4.7)<.13
            closed=state in ('sleep','tired') or (blink and state not in ('left','right'))
            if closed or state=='happy':self.draw_expression(p,state)
            if state=='happy':
                p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(240,146,148,75))
                p.drawEllipse(QPointF(439,378),19,8);p.drawEllipse(QPointF(549,394),19,8)
            p.restore()
        if not for_mask:
            if state=='drink':self.draw_cup(p,age,self.full_body)
            if state in ('cat','sleep'):
                self.draw_cat(p,315,334,1.02,state=='sleep',age)
                if state=='cat':
                    p.setPen(QColor('#f3c7c5'));p.setFont(QFont('Segoe UI',17))
                    p.drawText(QPointF(350,285-abs(math.sin(age*2))*8),'♪')
            elif state!='cast':
                self.draw_cat(p,358,354,.64,False,now)
        if not self.full_body:self.draw_keyboard(p,state,now<engine.mouse_until)
        elif state in ('left','right'):
            x=204 if state=='left' else 277
            p.setPen(QPen(QColor('#ffd291'),1.5));p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(x,390),17,5)
            for dx in (-7,0,7):p.drawLine(QPointF(x+dx,382),QPointF(x+dx*1.4,375))
        if state=='cast' and not for_mask:
            # Red/orange spell glow overlays the original blue orb during casting.
            glow=QRadialGradient(QPointF(181,173),29)
            glow.setColorAt(0,QColor(255,226,154,170))
            glow.setColorAt(.45,QColor(255,91,52,130))
            glow.setColorAt(1,QColor(255,77,34,0))
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(glow);p.drawEllipse(QPointF(181,173),29,29)
        p.restore()

    def draw_expression(self,p,state):
        # Runtime eyelid layers follow the original angled eye shapes.
        p.setPen(Qt.PenStyle.NoPen)
        skin=QLinearGradient(430,333,540,381)
        skin.setColorAt(0,QColor('#ffe1c4'));skin.setColorAt(1,QColor('#f6d3b7'))
        p.setBrush(skin)
        left=QPainterPath();left.moveTo(431,329);left.cubicTo(439,315,455,317,465,335)
        left.cubicTo(473,348,466,367,453,369);left.cubicTo(437,369,430,355,431,329)
        right=QPainterPath();right.moveTo(495,342);right.cubicTo(514,336,534,340,544,354)
        right.cubicTo(536,379,512,383,500,369);right.closeSubpath()
        p.drawPath(left);p.drawPath(right)
        p.setPen(QPen(QColor('#654039'),5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        path=QPainterPath()
        if state=='happy':
            path.moveTo(435,344);path.quadTo(448,332,464,347)
            path.moveTo(500,357);path.quadTo(520,347,537,360)
        else:
            path.moveTo(435,344);path.quadTo(446,354,463,348)
            path.moveTo(500,357);path.quadTo(518,369,537,359)
        p.drawPath(path)
        p.setPen(QPen(QColor('#533238'),3))
        p.drawLine(QPointF(436,345),QPointF(431,341))
        p.drawLine(QPointF(535,360),QPointF(540,357))

    def draw_keyboard(self,p,state,mouse):
        if state=='cast':return
        p.save()
        if state=='sleep':p.setOpacity(.68)
        p.setPen(QPen(QColor('#705565'),1.1))
        shell=QLinearGradient(0,350,0,391)
        shell.setColorAt(0,QColor('#e8c4b6'));shell.setColorAt(1,QColor('#925563'))
        p.setBrush(shell)
        body=QPainterPath();body.moveTo(153,350);body.lineTo(323,350)
        body.lineTo(345,381);body.quadTo(345,390,334,390)
        body.lineTo(143,390);body.quadTo(131,390,134,381);body.closeSubpath();p.drawPath(body)
        p.setBrush(QColor('#fff0dc'));p.setPen(QPen(QColor('#b68584'),1))
        for row in range(3):
            for col in range(11):
                x=154+col*15.1-row*4;y=355+row*8.5
                active=(state=='left' and col<5) or (state=='right' and col>=5)
                if row==2 and 3<=col<=7:continue
                p.setBrush(QColor('#ffb365') if active else QColor('#f7e6d4'))
                rect=QRectF(x,y+(.9 if active else 0),12,6)
                p.drawRoundedRect(rect,1.3,1.3)
                p.setPen(QPen(QColor('#bfa4a4'),.55));p.drawLine(QPointF(x+3,y+2),QPointF(x+6,y+2))
                p.setPen(QPen(QColor('#b68584'),1))
        p.setBrush(QColor('#ffb365') if state in ('left','right') else QColor('#f7e6d4'))
        p.drawRoundedRect(QRectF(191,372,72,6),1.5,1.5)
        p.setPen(QPen(QColor('#efccba'),1));p.drawLine(QPointF(144,383),QPointF(331,383))
        # Mouse indicator is visible on the same little keyboard.
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#ffd39b') if mouse else QColor('#ad867e'))
        p.drawEllipse(QPointF(318,379),2,2)
        if state in ('left','right'):
            x=185 if state=='left' else 287
            p.setPen(QPen(QColor('#ffca80'),1.4));p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(x,362),13,6)
            for dx in (-10,0,10):p.drawLine(QPointF(x+dx,346),QPointF(x+dx*1.25,339))
        p.restore()

    def draw_cup(self,p,age,full=False):
        # The mug rises toward the mouth, pauses, then lowers again.
        t=min(1,age/.7)*min(1,max(0,(4-age)/.7))
        x=243;y=(257-67*t) if full else (326-78*t)
        p.save();p.translate(x,y);p.rotate(-8*t)
        p.scale(.73,.73)
        p.setPen(QPen(QColor('#775c5b'),1.2))
        grad=QLinearGradient(-17,-7,17,20)
        grad.setColorAt(0,QColor('#fff4e2'));grad.setColorAt(.6,QColor('#edd3b7'));grad.setColorAt(1,QColor('#ba998c'))
        p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(QColor('#e5c6aa'),4))
        p.drawEllipse(QRectF(10,-4,15,16))
        p.setBrush(grad);p.setPen(QPen(QColor('#775c5b'),1.2))
        path=QPainterPath();path.moveTo(-16,-7);path.lineTo(16,-7);path.lineTo(13,19)
        path.quadTo(0,26,-13,19);path.closeSubpath();p.drawPath(path)
        p.setBrush(QColor('#81b8c9'));p.drawEllipse(QRectF(-16,-10,32,7))
        p.setPen(QPen(QColor('#fcf4de'),1));p.drawArc(QRectF(-15,-9,30,5),0,160*16)
        p.setPen(QPen(QColor('#c95464'),2));p.drawLine(QPointF(-4,6),QPointF(4,6));p.drawLine(QPointF(0,2),QPointF(0,10))
        p.restore()
        p.setPen(QPen(QColor(228,221,238,150),1.4))
        for i in range(2):
            path=QPainterPath();yy=y-16-(age*12+i*8)%19;xx=x-5+i*10
            path.moveTo(xx,yy);path.cubicTo(xx-4,yy-5,xx+4,yy-10,xx,yy-14);p.drawPath(path)

    def draw_cat(self,p,x,y,scale,sleep,age):
        p.save();p.translate(x,y-(0 if sleep else abs(math.sin(age*2))*3))
        p.scale(scale,scale)
        p.setPen(QPen(QColor('#272330'),1.5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QColor('#3b3444'))
        p.drawEllipse(QRectF(-20,-9,40,29))
        p.setPen(QPen(QColor('#36303d'),6));p.setBrush(Qt.BrushStyle.NoBrush)
        path=QPainterPath();path.moveTo(14,15);path.cubicTo(43,20,43,-7,31,-10);p.drawPath(path)
        p.setPen(QPen(QColor('#272330'),1.5));p.setBrush(QColor('#625064'))
        wings=QPainterPath();wings.moveTo(-13,1);wings.quadTo(-41,-20,-39,1)
        wings.lineTo(-32,-2);wings.lineTo(-27,9);wings.lineTo(-18,4)
        wings.moveTo(13,1);wings.quadTo(41,-20,39,1);wings.lineTo(32,-2);wings.lineTo(27,9);wings.lineTo(18,4);p.drawPath(wings)
        p.setPen(QPen(QColor('#897389'),.8));p.drawLine(QPointF(-32,-3),QPointF(-20,2));p.drawLine(QPointF(32,-3),QPointF(20,2))
        head=QPainterPath();head.moveTo(-23,-20);head.lineTo(-22,-43);head.lineTo(-9,-32)
        head.quadTo(0,-36,9,-32);head.lineTo(22,-43);head.lineTo(23,-20)
        head.cubicTo(28,-4,14,1,0,2);head.cubicTo(-14,1,-28,-4,-23,-20)
        fur=QLinearGradient(-20,-40,20,5);fur.setColorAt(0,QColor('#504553'));fur.setColorAt(1,QColor('#211e2a'))
        p.setBrush(fur);p.setPen(QPen(QColor('#24212c'),1.4));p.drawPath(head)
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#ae7c8c'))
        for sign in (-1,1):
            path=QPainterPath();path.moveTo(sign*19,-36);path.lineTo(sign*17,-23);path.lineTo(sign*10,-29);path.closeSubpath();p.drawPath(path)
        if sleep:
            p.setPen(QPen(QColor('#dcaf9b'),1.5));path=QPainterPath()
            path.moveTo(-15,-17);path.quadTo(-10,-12,-5,-17)
            path.moveTo(5,-17);path.quadTo(10,-12,15,-17);p.drawPath(path)
        else:
            eye=QLinearGradient(0,-22,0,-7);eye.setColorAt(0,QColor('#e98d4e'));eye.setColorAt(1,QColor('#fff0a4'))
            p.setBrush(eye);p.setPen(QPen(QColor('#14121e'),1))
            for xx in (-10,10):
                p.drawEllipse(QRectF(xx-5.5,-22,11,13));p.setBrush(QColor('#262036'))
                p.drawEllipse(QRectF(xx-1.5,-21,3,11));p.setBrush(QColor('#fff8ed'))
                p.drawEllipse(QRectF(xx-3,-21,2,3));p.setBrush(eye)
        p.setPen(QPen(QColor('#d5a0ad'),1));p.drawLine(QPointF(-2,-5),QPointF(0,-3));p.drawLine(QPointF(0,-3),QPointF(2,-5))
        p.setPen(QPen(QColor('#cd4b60'),2.8));p.drawLine(QPointF(-4,-28),QPointF(4,-28));p.drawLine(QPointF(0,-32),QPointF(0,-24))
        p.setPen(QPen(QColor('#92738a'),.8));p.drawLine(QPointF(-19,-7),QPointF(-28,-10));p.drawLine(QPointF(19,-7),QPointF(28,-10))
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#4d3e51'))
        p.drawEllipse(QRectF(-16,14,13,7));p.drawEllipse(QRectF(3,14,13,7))
        p.restore()

    def region(self,scale,state):
        # Cache alpha-derived regions per pose/size. Blinking stays inside this mask.
        key=(scale,state,self.full_body)
        if key not in self.region_cache:
            pix=QPixmap(round(480*scale),round(450*scale));pix.fill(Qt.GlobalColor.transparent)
            from app import Engine
            e=Engine(now=0);e.state=state if state not in ('left','right') else 'idle'
            e.tap_side=state;e.tap_until=10 if state in ('left','right') else 0
            p=QPainter(pix);p.scale(scale,scale);self.draw(p,e,1,True);p.end()
            base=QRegion(pix.mask());region=QRegion(base)
            for dx,dy in [(-10,0),(10,0),(0,-10),(0,10)]:region|=base.translated(round(dx*scale),round(dy*scale))
            # Ensure the mug's entire animated trajectory remains visible.
            if state=='drink':region|=QRegion(round(220*scale),round(158*scale),round(65*scale),round(190*scale))
            self.region_cache[key]=region
        return self.region_cache[key]
