"""Transparent, input-pass-through half-monitor Explosion choreography."""
import math,time
from PySide6.QtCore import Qt,QPointF,QRectF,QRect,QSizeF
from PySide6.QtGui import QImage,QPainter,QColor,QPen,QPainterPath,QRadialGradient,QFont,QTransform,QLinearGradient,QRegion
from PySide6.QtWidgets import QWidget,QApplication
from spell_scene import ExplosionStage,ease,caster_visibility,CAST_RELEASE,CAST_RETURN

def half_geometry(screen_rect,pet_center):
    width=screen_rect.width()//2
    right=pet_center.x()>=screen_rect.center().x()
    return QRect(screen_rect.right()-width+1 if right else screen_rect.left(),screen_rect.top(),width,screen_rect.height())

class HalfScreenStage(ExplosionStage):
    WIDTH=1000;HEIGHT=1100
    PALETTE=('#58eeff','#ff72d9','#ffe568','#74ff9f','#9c8dff','#b5fff1')
    def __init__(self):
        self.cross_count=0;self.metrics={};self.cross_sprites={};self.circle_sprites={}
        self.ribbon_sprites={}
        self.explosion_text=QPainterPath()
        self.explosion_text.addText(QPointF(289,978),QFont('Segoe UI',47,QFont.Weight.Black),'EXPLOSION!')
        self.aura_sprite=QImage(900,1120,QImage.Format.Format_ARGB32_Premultiplied);self.aura_sprite.fill(Qt.GlobalColor.transparent)
        aura=QRadialGradient(QPointF(450,560),450)
        aura.setColorAt(0,QColor(65,18,35,90));aura.setColorAt(.6,QColor(88,26,40,38));aura.setColorAt(1,QColor(50,16,30,0))
        painter=QPainter(self.aura_sprite);painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(aura);painter.drawEllipse(QPointF(450,560),450,560);painter.end()
        self.plasma_sprite=QImage(400,400,QImage.Format.Format_ARGB32_Premultiplied);self.plasma_sprite.fill(Qt.GlobalColor.transparent)
        lobe=QRadialGradient(QPointF(200,200),200)
        lobe.setColorAt(0,QColor(255,230,158,175));lobe.setColorAt(.35,QColor(255,180,74,165));lobe.setColorAt(.72,QColor(241,85,39,140));lobe.setColorAt(1,QColor(174,44,43,0))
        painter=QPainter(self.plasma_sprite);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(lobe);painter.drawEllipse(QPointF(200,200),200,172);painter.end()

    def circle(self,p,center,radius,flatten,rotation,opacity,color='#fd7158'):
        if radius<.1 or opacity<=0:return
        # Cache the detailed rune artwork; only its scale and rotation change.
        if color not in self.circle_sprites:
            image=QImage(1040,1040,QImage.Format.Format_ARGB32_Premultiplied);image.fill(Qt.GlobalColor.transparent)
            painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.translate(520,520);painter.scale(2,2)
            super().circle(painter,QPointF(0,0),256,1,0,1,color);painter.end();self.circle_sprites[color]=image
        p.save();p.setOpacity(p.opacity()*opacity);p.translate(center);p.scale(1,flatten);p.rotate(rotation)
        extent=radius*260/256;p.drawImage(QRectF(-extent,-extent,extent*2,extent*2),self.circle_sprites[color]);p.restore()

    def cross(self,p,point,size,alpha,rotation=0,color='#ffc789'):
        if alpha<=0:return
        self.cross_count+=1
        base=280 if size>60 else 20
        angle=0 if base==280 else round(rotation/6)*6;key=(base,color,angle)
        if key not in self.cross_sprites:
            extent=base*2+2;side=int(extent*4)
            image=QImage(side,side,QImage.Format.Format_ARGB32_Premultiplied);image.fill(Qt.GlobalColor.transparent)
            painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.translate(side/2,side/2);painter.scale(2,2)
            self.paint_cross(painter,QPointF(0,0),base,1,angle,color);painter.end();self.cross_sprites[key]=image
        extent=(base*2+2)*size/base
        p.save();p.translate(point);p.setOpacity(p.opacity()*min(1,alpha))
        p.drawImage(QRectF(-extent,-extent,extent*2,extent*2),self.cross_sprites[key]);p.restore()

    def paint_cross(self,p,point,size,alpha,rotation,color):
        p.save();p.translate(point);p.rotate(rotation)
        p.setOpacity(p.opacity()*min(1,alpha));p.setPen(Qt.PenStyle.NoPen)
        halo=QRadialGradient(QPointF(0,0),size*1.7)
        tint=QColor(color);tint.setAlpha(150);halo.setColorAt(0,tint)
        edge=QColor(color);edge.setAlpha(0);halo.setColorAt(1,edge)
        p.setBrush(halo);p.drawEllipse(QPointF(0,0),size*1.6,size*1.9)
        star=QPainterPath();star.moveTo(0,-size*1.6)
        star.quadTo(QPointF(size*.025,-size*.12),QPointF(size*.10,-size*.08));star.quadTo(QPointF(size*.22,-size*.025),QPointF(size,0))
        star.quadTo(QPointF(size*.22,size*.025),QPointF(size*.10,size*.08));star.quadTo(QPointF(size*.025,size*.12),QPointF(0,size*1.6))
        star.quadTo(QPointF(-size*.025,size*.12),QPointF(-size*.10,size*.08));star.quadTo(QPointF(-size*.22,size*.025),QPointF(-size,0))
        star.quadTo(QPointF(-size*.22,-size*.025),QPointF(-size*.10,-size*.08));star.quadTo(QPointF(-size*.025,-size*.12),QPointF(0,-size*1.6))
        star.closeSubpath()
        glint=QRadialGradient(QPointF(0,0),size*1.6)
        glint.setColorAt(0,QColor('#ffffff'));glint.setColorAt(.16,QColor('#f5ffff'));glint.setColorAt(.60,QColor(color));glint.setColorAt(1,edge)
        p.setBrush(glint);p.drawPath(star)
        p.setPen(QPen(QColor('#fffbe9'),max(.45,size*.034),Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(0,-size*.78),QPointF(0,size*.78));p.drawLine(QPointF(-size*.46,0),QPointF(size*.46,0));p.restore()

    def charge_particles(self,p,age,real_age,reduced):
        charge=ease((age-.55)/2.6)
        for i in range(22 if reduced else 72):
            life=(real_age*.36+i*.61803)%1
            angle=i*2.39996+real_age*.36
            radius=22+math.sqrt((i*.754877+real_age*.047)%1)*(150+(i%7)*15)
            point=QPointF(705+math.cos(angle)*radius,360+math.sin(angle)*radius*.85)
            size=(4+i%6*1.7)*(1+.65*charge)
            self.cross(p,point,size,math.sin(life*math.pi)*(.35+.6*charge),math.sin(real_age+i)*13,self.PALETTE[i%6])
        # A few larger cross flares hover around the mage's staff and mantle.
        for i in range(9 if reduced else 30):
            life=(real_age*.23+i*.38197)%1
            point=QPointF(70+(i*73)%450,900-life*680)
            self.cross(p,point,5+i%5*3,math.sin(life*math.pi)*.78,math.sin(i+real_age)*10,self.PALETTE[(i+2)%6])

    def ribbons(self,p,age,real_age,reduced,front=False):
        strength=ease((age-.45)/1.4)*(1-ease((age-CAST_RELEASE)/.6))*caster_visibility(age)
        if strength<.06:return
        p.save();p.setOpacity(p.opacity()*strength*(1 if front else .65))
        if front:
            area=QPainterPath();area.addRect(QRectF(0,0,1000,1100))
            face=QPainterPath();face.addEllipse(QRectF(213,280,155,135));p.setClipPath(area.subtracted(face))
        for i in range(1 if reduced else 3):
            phase=real_age*.95+i*2.1;base=480+i*75+math.sin(phase)*24
            tint='#69fff0' if i%2 else '#50deff'
            if tint not in self.ribbon_sprites:
                image=QImage(1140,960,QImage.Format.Format_ARGB32_Premultiplied);image.fill(Qt.GlobalColor.transparent)
                painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.scale(2,2);painter.translate(0,290)
                path=QPainterPath();path.moveTo(80,150);path.cubicTo(520,80,490,-110,145,-120);path.cubicTo(30,-190,210,-265,440,-225)
                for width,alpha in ((23,15),(12,30),(4.5,125),(1.1,180)):
                    color=QColor(tint);color.setAlpha(alpha);painter.setPen(QPen(color,width,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap));painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawPath(path)
                painter.end();self.ribbon_sprites[tint]=image
            p.drawImage(QRectF(0,base-290,570,480),self.ribbon_sprites[tint])
        p.restore()

    def back(self,p,age,real_age,reduced):
        opacity=caster_visibility(age)
        if opacity<=0:return
        p.save();p.setOpacity(opacity)
        charge=ease((age-.6)/2.8);fade=1-ease((age-5.15)/.8)
        p.save();p.setOpacity(p.opacity()*charge);p.drawImage(QPointF(255,-70),self.aura_sprite);p.restore()
        self.circle(p,QPointF(290,743),133,.24,-real_age*13,.68,'#5ce6dd')
        for i,(y,r) in enumerate(((190,207),(260,178),(330,148),(393,116))):
            growth=ease((age-.6-i*.18)/1.2)
            self.circle(p,QPointF(705,y),r*growth,.34,real_age*(15 if i%2 else -18),growth*fade*.85,('#59e9ff','#81ffbf','#dc91ff','#ffe681')[i])
            if growth>.2:
                self.circle(p,QPointF(705,y),r*.96*growth,.34,-real_age*8,.12*growth*fade,'#fff0c1')
        if age<CAST_RELEASE:self.charge_particles(p,age,real_age,reduced)
        else:self.big_blast(p,age-CAST_RELEASE,reduced)
        p.restore()

    def big_blast(self,p,t,reduced):
        if t>2.5:return
        alpha=1-ease((t-1.5)/1.0);impact=ease(t/.15)
        p.save();p.setOpacity(p.opacity()*alpha)
        # Light pierces four suspended circles, with a flared, white-hot core.
        for width,color in ((104,QColor(249,52,45,35)),(48,QColor(255,118,47,125)),(19,QColor('#ffd994')),(5,QColor('#fffbea'))):
            p.setPen(QPen(color,width,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(705,150),QPointF(705,150+585*impact))
        self.cross(p,QPointF(705,356),200+80*ease(t/.18),max(0,1-t/.55)*(.4 if reduced else .9))
        expansion=ease(t/.6);rise=ease(t/1.2)
        center=QPointF(705,731-rise*152);radius=28+203*expansion
        # An irregular curved corona and several layers of plasma form the cloud.
        cloud=QPainterPath();points=[]
        for i in range(36):
            a=i/36*math.tau;r=radius*(1+.06*math.sin(i*1.2+t*7))
            points.append(QPointF(center.x()+math.cos(a)*r,center.y()+math.sin(a)*r*.75))
        cloud.moveTo(points[0])
        for i in range(36):
            a=points[i];b=points[(i+1)%36]
            cloud.cubicTo(a+(b-points[(i-1)%36])/6,b-(points[(i+2)%36]-a)/6,b)
        cloud.closeSubpath()
        fire=QRadialGradient(center,radius*1.15)
        for stop,color in ((0,'#fffdf0'),(.18,'#fff0ae'),(.48,'#ffcd62'),(.74,'#f87432'),(.95,'#a93337')):fire.setColorAt(stop,QColor(color))
        fire.setColorAt(1,QColor(134,27,43,0));p.setPen(Qt.PenStyle.NoPen);p.setBrush(fire);p.drawPath(cloud)
        for i in range(12):
            a=i*2.39996;r=(36+137*expansion)*(1+.12*math.sin(i*4.4))
            pos=center+QPointF(math.cos(a)*r,math.sin(a)*r*.61-20*rise)
            size=(29+54*expansion)*(1+.16*math.cos(i*2.7))
            p.drawImage(QRectF(pos.x()-size,pos.y()-size,size*2,size*2),self.plasma_sprite)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for k in range(3):
            curl=QPainterPath()
            for j in range(35):
                u=j/34;a=k*2.09+u*5+t*.9;r=radius*(.18+.67*u)
                pt=center+QPointF(math.cos(a)*r,math.sin(a)*r*.6)
                if j==0:curl.moveTo(pt)
                else:curl.lineTo(pt)
            p.setPen(QPen(QColor(255,234,178,95),2.4,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap));p.drawPath(curl)
        # Expanding elliptical rings and a heated ground glow.
        p.setBrush(Qt.BrushStyle.NoBrush)
        for lag in (0,.11,.24,.39):
            u=max(0,t-lag);r=25+u*320
            p.setPen(QPen(QColor(255,223,159,int(235*max(0,1-u/2))),max(.7,4-u)))
            p.drawEllipse(QPointF(705,760),r,r*.24)
        # Cross-shaped fragments drift outward, then fall and fade as embers.
        for i in range(21 if reduced else 62):
            a=i*2.39996;speed=85+(i%11)*26;r=t*speed
            pos=QPointF(705+math.cos(a)*r,710+math.sin(a)*r*.65-60*t+43*t*t)
            self.cross(p,pos,4+(i%7)*2.3,max(0,1-t/2.5)*(.45+.5*(i%4)/3),math.sin(i+t)*12,self.PALETTE[i%6])
        if t<.3:
            p.setOpacity(p.opacity()*(1-t/.3)*(.12 if reduced else .38))
            flash=QRadialGradient(QPointF(705,660),470)
            flash.setColorAt(0,QColor('#fffbe5'));flash.setColorAt(.4,QColor(255,226,174,155));flash.setColorAt(1,QColor(255,181,128,0))
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(flash);p.drawEllipse(QPointF(705,660),470,520)
        p.restore()

    def front(self,p,age,real_age,reduced,orb):
        visibility=caster_visibility(age)
        if visibility<=0:return
        p.save();p.setOpacity(visibility)
        self.ribbons(p,age,real_age,reduced,True)
        if age<CAST_RELEASE:
            for i in range(7 if reduced else 22):
                life=(real_age*.29+i*.61803)%1;point=QPointF(100+(i*97)%420,870-life*590)
                if 205<point.x()<370 and 270<point.y()<425:continue
                self.cross(p,point,7+(i%5)*3,math.sin(math.pi*life)*.82,math.sin(real_age+i)*12,self.PALETTE[(i+1)%6])
        if orb is not None and age<CAST_RELEASE+.2:
            charge=ease((age-.6)/2.7)*(1-ease((age-CAST_RELEASE)/.2))
            target=QPointF(705,190)
            for strand in range(3):
                path=QPainterPath();path.moveTo(orb)
                for j in range(1,16):
                    u=j/15;pt=orb+(target-orb)*u
                    pt+=QPointF(0,math.sin(j*3.1+real_age*14+strand*2)*7*math.sin(u*math.pi));path.lineTo(pt)
                p.setPen(QPen(QColor(255,132,87,int(160*charge)),1.7+strand*.65));p.drawPath(path)
            self.cross(p,orb,14+11*charge,.85*charge)
        if CAST_RELEASE<age<5.15:
            opacity=ease((age-CAST_RELEASE)/.08)*(1-ease((age-4.85)/.30))
            p.setOpacity(visibility*opacity)
            p.setPen(QPen(QColor('#4b1d31'),6,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin));p.setBrush(QColor('#ffe5ab'));p.drawPath(self.explosion_text)
        p.restore()

    def render(self,p,character,e,now,size,source_rect,reduced=False):
        # Composite the large translucent effect once at a bounded raster size.
        # The overlay still occupies exactly half the monitor; particles, paths
        # and timing are unchanged, with one smooth final upscale.
        factor=min(1,720/max(1,size.width()),900/max(1,size.height()))
        if factor<.999:
            width=max(1,round(size.width()*factor));height=max(1,round(size.height()*factor))
            if not hasattr(self,'composite') or self.composite.width()!=width or self.composite.height()!=height:
                self.composite=QImage(width,height,QImage.Format.Format_ARGB32_Premultiplied)
            self.composite.fill(Qt.GlobalColor.transparent)
            fp=QPainter(self.composite);fp.setRenderHint(QPainter.RenderHint.Antialiasing);fp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            sr=QRectF(source_rect.x()*factor,source_rect.y()*factor,source_rect.width()*factor,source_rect.height()*factor)
            self.render_native(fp,character,e,now,QSizeF(width,height),sr,reduced);fp.end()
            p.drawImage(QRectF(0,0,size.width(),size.height()),self.composite)
            self.metrics['composite_raster']=[width,height]
        else:self.render_native(p,character,e,now,size,source_rect,reduced)
        # Public metrics always describe the window's logical coordinates.
        self.metrics['source_rect']=[source_rect.x(),source_rect.y(),source_rect.width(),source_rect.height()]

    def render_native(self,p,character,e,now,size,source_rect,reduced=False):
        age=e.visual_age(now);real_age=max(0,now-e.since);self.cross_count=0
        frame=QImage(720,675,QImage.Format.Format_ARGB32_Premultiplied);frame.fill(Qt.GlobalColor.transparent)
        avatar=QPainter(frame);avatar.setRenderHint(QPainter.RenderHint.Antialiasing);avatar.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);avatar.scale(1.5,1.5)
        character.draw(avatar,e,now,reduced);avatar.end()
        scale=min(size.width()/self.WIDTH,size.height()/self.HEIGHT)
        padx=(size.width()-self.WIDTH*scale)/2;pady=(size.height()-self.HEIGHT*scale)/2
        travel=ease(age/.8)*(1-ease((age-CAST_RETURN)/1.1))
        start_scale=source_rect.width()/480/scale
        start_x=(source_rect.x()-padx)/scale;start_y=(source_rect.y()-pady)/scale
        factor=start_scale+(1.65-start_scale)*travel
        x=start_x+((290-174*1.65)-start_x)*travel;y=start_y+((400-173*1.65)-start_y)*travel
        transform=QTransform();transform.translate(x,y);transform.scale(factor,factor)
        orb=transform.map(character.staff_orb) if character.staff_orb is not None else None
        p.save();p.translate(padx,pady);p.scale(scale,scale)
        self.back(p,age,real_age,reduced)
        p.save();p.setTransform(transform,True);p.drawImage(QRectF(0,0,480,450),frame);p.restore()
        self.front(p,age,real_age,reduced,orb);p.restore()
        self.metrics=dict(cross_particles=self.cross_count,virtual_age=age,canvas_scale=scale,
                          caster_in_view=0<290*scale+padx<size.width(),source_rect=[source_rect.x(),source_rect.y(),source_rect.width(),source_rect.height()])

class CastingOverlay(QWidget):
    def __init__(self,pet):
        super().__init__();self.pet=pet;self.stage=HalfScreenStage();self.active=False
        self.setWindowTitle('惠惠 · 半屏爆裂演出')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Tool|Qt.WindowType.WindowDoesNotAcceptFocus|Qt.WindowType.WindowTransparentForInput|Qt.WindowType.WindowStaysOnTopHint)
    def start(self):
        screen=QApplication.screenAt(self.pet.geometry().center()) or QApplication.primaryScreen()
        self.screen_rect=screen.availableGeometry();self.setGeometry(half_geometry(self.screen_rect,self.pet.geometry().center()))
        self.setWindowOpacity(self.pet.windowOpacity());self.active=True
        self.pet.setMask(QRegion(0,0,1,1));self.pet.mask_signature=None
        self.show();self.pet.update()
    def stop(self):
        if not self.active:return
        self.active=False;self.hide();self.pet.mask_signature=None;self.pet.clearMask();self.pet.update()
    def paintEvent(self,event):
        if not self.active:return
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        source=QRectF(self.pet.x()-self.x(),self.pet.y()-self.y(),self.pet.width(),self.pet.height())
        self.stage.render(p,self.pet.character,self.pet.engine,time.monotonic(),QSizeF(self.size()),source,self.pet.settings['reduced_motion'])
        caption=self.pet.voice.caption() if self.pet.settings.get('voice_caption',True) else ''
        if caption:
            p.setFont(QFont('Microsoft YaHei UI',13,QFont.Weight.DemiBold));p.setPen(QColor('#ffe7c7'))
            rect=QRectF(24,self.height()-92,self.width()-48,66)
            p.fillRect(rect,QColor(35,24,38,205));p.drawText(rect.adjusted(14,5,-14,-5),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,caption)
        p.end()
