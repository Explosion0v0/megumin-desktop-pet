"""A bounded, transparent anime-inspired Explosion stage, rendered in real time."""
import math
from PySide6.QtCore import QPointF,QRectF,Qt
from PySide6.QtGui import QColor,QPen,QPainterPath,QRadialGradient,QLinearGradient,QFont

CAST_DURATION=7.2
CAST_RELEASE=3.65
CAST_RETURN=6.1

def ease(value):
    t=max(0,min(1,value));return t*t*(3-2*t)

def desk_visibility(age):
    return 1-ease(age/.8) if age<.8 else ease((age-CAST_RETURN)/(CAST_DURATION-CAST_RETURN))

def caster_visibility(age):
    return ease(age/.65)*(1-ease((age-CAST_RETURN)/(CAST_DURATION-CAST_RETURN)))

class ExplosionStage:
    @staticmethod
    def phase(age):
        if age<.8:return 'depart'
        if age<CAST_RELEASE:return 'chant'
        if age<5.3:return 'release'
        if age<CAST_RETURN:return 'exhausted'
        return 'return'

    def circle(self,p,center,radius,flatten,rotation,opacity,color='#fd7158'):
        p.save();p.setOpacity(opacity);p.translate(center);p.scale(1,flatten);p.rotate(rotation)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for size,width in ((radius,1.6),(radius*.91,.7),(radius*.74,1.0)):
            p.setPen(QPen(QColor(color),width));p.drawEllipse(QPointF(0,0),size,size)
        p.setPen(QPen(QColor('#ffd8a0'),.9))
        star=QPainterPath()
        for i in range(8):
            a=((i*3)%7)*math.tau/7-.5*math.pi;pt=QPointF(math.cos(a)*radius*.73,math.sin(a)*radius*.73)
            if i==0:star.moveTo(pt)
            else:star.lineTo(pt)
        p.drawPath(star)
        for i in range(18):
            a=i*math.tau/18;x=math.cos(a)*radius*.95;y=math.sin(a)*radius*.95
            p.save();p.translate(x,y);p.rotate(i*20)
            p.drawLine(QPointF(-2,-2),QPointF(2,2));p.drawLine(QPointF(2,-2),QPointF(-2,2));p.restore()
        p.restore()

    def background(self,p,age,reduced):
        show=caster_visibility(age)
        if show<=0:return
        charge=ease((age-.65)/2.8);burst=max(0,age-CAST_RELEASE)
        fade=1-ease((age-5.0)/1.0)
        p.save();p.setOpacity(show)
        # Sparse ember trails leave the real desktop transparent around the stage.
        p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(QColor(198,55,78,65),.8))
        for i in range(5):
            trail=QPainterPath();trail.moveTo(104+i*11,353)
            trail.cubicTo(82+i*15,277,107+i*17,222,93+i*19,158)
            p.drawPath(trail)
        # Floor circle beneath the mage, with a second group over the target.
        self.circle(p,QPointF(173,374),76,.24,-age*19,show*.65)
        for i,(y,radius) in enumerate(((144,76),(179,62),(210,49))):
            growth=ease((age-.85-i*.18)/1.1)
            self.circle(p,QPointF(348,y),radius*growth,.30,age*(23 if i%2 else -19),growth*fade*.88)
        if age<CAST_RELEASE:
            glow=QRadialGradient(QPointF(348,182),88)
            glow.setColorAt(0,QColor(255,81,53,int(55*charge)));glow.setColorAt(1,QColor(255,59,34,0))
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(glow);p.drawEllipse(QPointF(348,182),88,105)
            for i in range(30 if not reduced else 12):
                a=i*2.3999+age*.45;r=25+(i%8)*9
                pt=QPointF(348+math.cos(a)*r,285-((age*40+i*13)%145))
                p.setBrush(QColor('#ffdca1') if i%3 else QColor('#ef5351'));p.drawEllipse(pt,1.2+(i%3)*.45,1.2+(i%3)*.45)
        else:self.blast(p,burst,reduced)
        p.restore()

    def blast(self,p,t,reduced):
        if t>2.0:return
        fade=1-ease((t-1.15)/.85);strike=ease(t/.17)
        # A white-hot column descends through the stacked circles.
        p.save();p.setOpacity(fade)
        for width,color in ((30,QColor(244,62,38,65)),(14,QColor(255,150,56,160)),(4,QColor('#fff2c8'))):
            p.setPen(QPen(color,width,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(348,128),QPointF(348,128+200*strike))
        radius=12+90*ease(t/.8);center=QPointF(348,322)
        fire=QRadialGradient(center,radius)
        fire.setColorAt(0,QColor('#fff8da'));fire.setColorAt(.16,QColor('#fff0ae'));fire.setColorAt(.48,QColor('#ffbc53'));fire.setColorAt(.76,QColor('#f65c2e'));fire.setColorAt(1,QColor(144,33,36,0))
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(fire);p.drawEllipse(center,radius,radius*.85)
        # Curved, expanding lobes form the rising fire cloud rather than a flat star.
        for i in range(12):
            a=i*math.tau/12;r=(23+42*ease(t/.6))*(.8+.2*math.sin(i*4.8))
            x=348+math.cos(a)*r;y=320+math.sin(a)*r*.65-18*ease(t/.7)
            size=(12+16*ease(t/.7))*(1+.18*math.cos(i*3.4))
            lobe=QRadialGradient(QPointF(x,y),size)
            lobe.setColorAt(0,QColor('#ffd78b'));lobe.setColorAt(.5,QColor(251,111,44,205));lobe.setColorAt(1,QColor(164,41,39,0))
            p.setBrush(lobe);p.drawEllipse(QPointF(x,y),size,size*.85)
        # Ground shockwaves and debris retain a clear target in the desktop canvas.
        p.setBrush(Qt.BrushStyle.NoBrush)
        for lag in (0,.12,.26):
            u=max(0,t-lag);r=10+u*157
            p.setPen(QPen(QColor(255,208,121,max(0,int(220*(1-u/1.5)))),max(.7,3-u)))
            p.drawEllipse(QPointF(348,345),r,r*.22)
        for i in range(28 if not reduced else 10):
            a=i*2.3999;r=t*(45+(i%7)*14)
            x=348+math.cos(a)*r;y=318+math.sin(a)*r*.55-22*t+35*t*t
            p.setPen(QPen(QColor('#ffd18e') if i%3 else QColor('#df7750'),1.2))
            p.drawLine(QPointF(x,y),QPointF(x-math.cos(a)*5,y-math.sin(a)*3))
        if t<.32:
            flash=(1-t/.32)*(.20 if reduced else .55)
            p.setOpacity(flash);light=QRadialGradient(center,140)
            light.setColorAt(0,QColor('#fff9de'));light.setColorAt(.4,QColor(255,225,177,190));light.setColorAt(1,QColor(255,180,118,0))
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(light);p.drawEllipse(center,140,150)
        p.restore()

    def foreground(self,p,age,reduced,orb):
        show=caster_visibility(age);charge=ease((age-.65)/2.9)
        if not show:return
        p.save();p.setOpacity(show)
        if .65<age<CAST_RELEASE+.25 and orb is not None:
            target=QPointF(348,144);strength=charge*(1-ease((age-CAST_RELEASE)/.25))
            for i in range(3):
                path=QPainterPath();path.moveTo(orb)
                dx=target.x()-orb.x();dy=target.y()-orb.y()
                for j in range(1,9):
                    u=j/8;offset=math.sin(j*4.3+age*17+i*1.9)*(4+i*2)*math.sin(u*math.pi)
                    path.lineTo(QPointF(orb.x()+dx*u,orb.y()+dy*u+offset))
                p.setPen(QPen(QColor(250,102,72,int(130*strength)),2+i*.4));p.drawPath(path)
            p.setPen(QPen(QColor(255,222,162,int(160*strength)),.8));p.drawPath(path)
        # A soft spell veil hides the game model's knee-level lower boundary.
        for i in range(7):
            x=137+i*12;y=367+math.sin(age*2+i)*5
            mist=QRadialGradient(QPointF(x,y),26)
            mist.setColorAt(0,QColor(110,38,70,100));mist.setColorAt(1,QColor(87,34,63,0))
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(mist);p.drawEllipse(QPointF(x,y),26,13)
        if CAST_RELEASE<age<5.05:
            visibility=ease((age-CAST_RELEASE)/.1)*(1-ease((age-4.65)/.4))
            p.setOpacity(visibility);font=QFont('Segoe UI',26,QFont.Weight.Black)
            text=QPainterPath();text.addText(QPointF(65,418),font,'EXPLOSION!')
            p.setPen(QPen(QColor('#3a1730'),5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin));p.setBrush(QColor('#ffe1a0'));p.drawPath(text)
        p.restore()
