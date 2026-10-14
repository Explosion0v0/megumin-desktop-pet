"""Genuine Cubism 3 model rendering into a transparent offscreen framebuffer."""
from pathlib import Path
import json
import math
import time
import numpy as np
from types import SimpleNamespace
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import (QOffscreenSurface,QOpenGLContext,QSurfaceFormat,QImage,
                          QPixmap,QPainter,QColor,QPen,QRegion,QFont,QTransform,QPainterPath,QLinearGradient,QRadialGradient)
from PySide6.QtOpenGL import QOpenGLFramebufferObject,QOpenGLFramebufferObjectFormat
from OpenGL import GL
import live2d
from spell_scene import ease,desk_visibility,caster_visibility,CAST_RELEASE,CAST_RETURN
from rig_motion import Spring,PointSpring,CastClip,keyboard_contact,keyboard_layout
from costumes import COSTUMES


class Live2DCharacter:
    def __init__(self,assets):
        self.assets=Path(assets)
        self.table_transform=QTransform()
        if not QTransform.quadToQuad(
            [QPointF(44,315),QPointF(441,315),QPointF(441,402),QPointF(44,402)],
            [QPointF(157,292),QPointF(439,308),QPointF(397,399),QPointF(49,377)],
            self.table_transform):raise RuntimeError('桌面透视初始化失败')
        self.torso_transform=QTransform();self.torso_transform.translate(279,238)
        self.torso_transform.shear(-.09,0);self.torso_transform.scale(1.18,.8);self.torso_transform.translate(-240,-200)
        self.cat_art=QPixmap(str(self.assets/'chomusuke-official-profile.png'))
        if self.cat_art.isNull():raise RuntimeError('逗之助原画素材加载失败')
        self.pointer=QPointF(240,220)
        self.costume='schooluniform' if (self.assets/'models/megumin-schooluniform/Character.model3.json').is_file() else 'classic'
        self.loaded_costume=None;self.full_body=False;self.cast_body_bounds=None
        self.loaded_school_uniform=False
        self.eyepatch=False
        self.loaded_eyepatch=False
        self.closed=False
        self.model=None
        self.frame=QImage()
        self.last_state=None
        self.state_started=0
        self.requested_motion=None
        self.motion_history=[]
        self.last_render=time.monotonic()
        self.renderer_info={}
        self.filtered_params={};self.mouse_position=QPointF();self.desktop_scene=QImage()
        self.staff_orb=None;self.cast_frame=QImage()
        self.render_scale=2.0;self.scene_scale=2.0;self.desk_cache=QImage()
        self.mouse_spring=PointSpring();self.key_spring=PointSpring(QPointF(334,350))
        self.tap_spring=Spring();self.joint_springs={}
        self.cast_clip=CastClip(self.assets/'choreography/DeskPet_Explosion.motion3.json')
        live2d.enableLog(False);live2d.init()
        fmt=QSurfaceFormat();fmt.setVersion(3,3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        fmt.setAlphaBufferSize(8);fmt.setDepthBufferSize(24);fmt.setStencilBufferSize(8)
        self.surface=QOffscreenSurface();self.surface.setFormat(fmt);self.surface.create()
        self.context=QOpenGLContext();self.context.setFormat(fmt)
        if not self.context.create() or not self.context.makeCurrent(self.surface):
            raise RuntimeError('无法创建 Live2D 所需的 OpenGL 上下文')
        live2d.glInit()
        self.renderer_info['opengl']=GL.glGetString(GL.GL_VERSION).decode()
        f=QOpenGLFramebufferObjectFormat()
        f.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
        self.fbo=QOpenGLFramebufferObject(960,900,f)
        self.cast_fbo=QOpenGLFramebufferObject(720,675,f)
        if not self.fbo.isValid():raise RuntimeError('Live2D 透明画布初始化失败')
        self.load_model(False)
        self.context.doneCurrent()

    def configure_resolution(self,window_scale,device_ratio=1):
        # Keep source pixels slightly denser than the visible, enlarged head.
        # Logical pose coordinates stay fixed; only raster buffers change.
        units=max(6,min(18,math.ceil(window_scale*device_ratio*1.25*6-1e-8)))
        factor=units/6
        scene_factor=max(1,min(3,window_scale*device_ratio))
        if factor==self.render_scale and scene_factor==self.scene_scale:return
        self.context.makeCurrent(self.surface)
        f=QOpenGLFramebufferObjectFormat();f.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
        self.fbo=QOpenGLFramebufferObject(80*units,75*units,f)
        self.render_scale=factor;self.scene_scale=scene_factor;self.desk_cache=QImage()
        self.model.Resize(self.fbo.width(),self.fbo.height())
        self.model.SetScale(1.45);self.model.SetOffset(0,-.65)
        self.context.doneCurrent()
        self.renderer_info['desktop_raster']=[self.fbo.width(),self.fbo.height()]

    def load_model(self,eyepatch):
        if self.model:
            self.model.DestroyRenderer();self.model=None
        selected=self.costume if self.costume in COSTUMES else 'schooluniform'
        if selected=='classic' and eyepatch:selected='eyepatch'
        folder=COSTUMES[selected]['folder']
        path=self.assets/'models'/folder/'Character.model3.json'
        self.model=live2d.Model();self.model.LoadModelJson(str(path.resolve()))
        self.model.Resize(self.fbo.width(),self.fbo.height())
        self.model.SetScale(1.45);self.model.SetOffset(0,-.65)
        self.model.SetAutoBlink(True);self.model.SetAutoBreath(True)
        data=json.loads(path.read_text(encoding='utf-8'))
        self.motions={Path(x['File']).stem.replace('.motion3',''):i for i,x in enumerate(data['FileReferences']['Motions'][''])}
        self.param_ids=set(self.model.GetParamIds())
        self.loaded_costume=selected;self.full_body=COSTUMES[selected]['full_body'];self.cast_body_bounds=None
        self.loaded_eyepatch=selected=='eyepatch'
        self.loaded_school_uniform=selected=='schooluniform'
        self.last_state=None
        self.filtered_params={}
        self.joint_springs={}
        self.hand_mesh={}
        self.cast_hand_mesh=None
        self.cast_grip_weights=None
        self.part_ids=self.model.GetPartIds()
        # DrawingOrder parts are shared, non-drawing ancestors, not an R arm.
        # Keep them enabled in every isolated pass so their L-arm descendants
        # do not disappear (the kimono model uses this native hierarchy).
        self.visibility_support_parts=[x for x in self.part_ids if x.startswith('PartDrawingOrder')]
        self.part_groups=dict(torso=['PartUpperBody','PartNeck'],
            R=[x for x in self.part_ids if x.startswith(('PartArmR','PartHandR'))],
            L=[x for x in self.part_ids if x.startswith(('PartArmL','PartHandL'))])
        excluded=set(['PartCore','PartFoot']+self.visibility_support_parts+self.part_groups['torso']+self.part_groups['R']+self.part_groups['L'])
        self.part_groups['head']=[x for x in self.part_ids if x not in excluded]
        self.part_groups['front_hair']=['PartFrontHair']
        self.renderer_info.update(cubism_version=self.model.Version(),parameter_count=self.model.GetParamCount(),
                                  motion_count=self.model.GetMotionCount(''),choreography_motion_count=self.model.GetMotionCount('DeskPet'),model_file=str(path),
                                  costume=selected,full_body_cast=self.full_body)

    def param(self,name,value):
        if name in self.param_ids:
            value=max(self.model.GetParamMinById(name),min(value,self.model.GetParamMaxById(name)))
            self.model.SetParamById(name,value)

    def play(self,name):
        if name in self.motions:
            self.model.StartMotion('',self.motions[name],3)
            self.motion_history.append(name)
            if len(self.motion_history)>32:self.motion_history.pop(0)

    def draw(self,p,e,now,reduced=False,for_mask=False):
        if self.closed:return
        self.context.makeCurrent(self.surface)
        selected=self.costume if self.costume in COSTUMES else 'schooluniform'
        if selected=='classic' and self.eyepatch:selected='eyepatch'
        if selected!=self.loaded_costume:self.load_model(self.eyepatch)
        state=e.state
        age=e.visual_age(now)
        dt=max(0,min(.05,now-self.last_render));self.last_render=now
        self.mouse_position=self.mouse_spring.step(QPointF(e.mouse_x,e.mouse_y),dt,.06)
        desired_key=keyboard_contact(e.latest_vk) if now<e.tap_until+.45 else QPointF(334,350)
        self.keyboard_position=self.key_spring.step(desired_key,dt,.07)
        tap=max(0,min(1,(e.tap_until-now)/.14))
        pulse=self.tap_spring.step(math.sin(tap*math.pi),dt,.04)
        view=SimpleNamespace(**vars(e));view.mouse_x=self.mouse_position.x();view.mouse_y=self.mouse_position.y()
        if state!=self.last_state:
            if state=='cast':self.requested_motion=None
            self.model.StopAllMotions();self.model.ResetAllParameters();self.model.ResetPose()
            self.last_state=state
            self.play(dict(idle='00_Wait_01',happy='00_Happy_02',cat='00_Happy_04',
                           cast='00_Skill_02',tired='00_Sad_01',sleep='00_Wait_01',drink='00_Wait_01')[state])
        if self.requested_motion:
            self.play(self.requested_motion);self.requested_motion=None
        if state=='idle' and self.model.IsMotionFinished():self.play('00_Wait_01')
        self.model.SetAutoBlink(state not in ('sleep','tired'))
        self.model.SetAutoBreath(not reduced)
        self.model.Update(dt)
        # Persistent three-quarter pose; native expressions and joint motions
        # remain animated while gaze follows the cursor around this baseline.
        self.param('PARAM_BODY_ANGLE_X',-7)
        self.param('PARAM_ANGLE_X',-12);self.param('PARAM_ANGLE_Y',-4)
        if state not in ('cast','drink'):
            # Cubism arm R is the hand on the viewer's left.
            for hand in ('L','R'):
                self.param('PARAM_ARM_'+hand+'_ROTATE',0)
                self.param('PARAM_SHOULDER_'+hand+'_ROTATE',0)
                self.param('PARAM_ARM_'+hand+'_ORDER',1)
            # Viewer-right hand always operates the keyboard; viewer-left
            # hand stays with the mouse, independent of the typed key side.
            self.param('PARAM_ARM_L_ROTATE',3*pulse)
            self.param('PARAM_SHOULDER_L_ROTATE',max(-4,min(4,(self.keyboard_position.x()-334)*.05)))
            self.param('PARAM_HAND_L_ROTATE',-8*pulse)
            self.param('PARAM_BODY_ANGLE_Y',1.2*pulse)
            self.param('PARAM_SHOULDER_R_ROTATE',-self.mouse_position.x()*.13)
            self.param('PARAM_HAND_R_ROTATE',-6 if e.mouse_button else 0)
        if state in ('idle','happy','cat'):
            gx=max(-1,min(1,(self.pointer.x()-240)/250));gy=max(-1,min(1,(220-self.pointer.y())/250))
            self.param('PARAM_EYE_BALL_X',gx*.7);self.param('PARAM_EYE_BALL_Y',gy*.5)
            if not reduced:
                self.param('PARAM_BODY_ANGLE_X',-7+gx*.8)
                self.param('PARAM_ANGLE_X',-12+gx*5);self.param('PARAM_ANGLE_Y',-4+gy*3)
        if state=='drink':
            t=ease(age/.75)*ease((4-age)/.8)
            self.param('PARAM_SHOULDER_R_ROTATE',20*t)
            self.param('PARAM_ARM_R_ROTATE',15+25*t)
            self.param('PARAM_ARM_R_ORDER',1)
            self.param('PARAM_HAND_R_ROTATE',17*t)
            for i in range(1,14):self.param(f'PARAM_HAND_R_{i:02d}',1 if i==5 else 0)
            self.param('PARAM_MOUTH_OPEN_Y',.12*t)
        if state=='sleep':
            self.param('PARAM_EYE_R_OPEN',0);self.param('PARAM_EYE_L_OPEN',0)
            self.param('PARAM_ANGLE_Z',12);self.param('PARAM_ANGLE_Y',-10)
            self.param('PARAM_MOUTH_OPEN_Y',0);self.param('PARAM_BODY_ANGLE_Z',4)
        if state=='tired':
            self.param('PARAM_EYE_R_OPEN',.22);self.param('PARAM_EYE_L_OPEN',.22)
            self.param('PARAM_SWEAT',1);self.param('PARAM_ANGLE_Y',-12)
            self.param('PARAM_BODY_ANGLE_Z',5)
        if state=='cast':
            for name,value in self.cast_clip.sample(age).items():self.param(name,value)
            exhausted=ease((age-5.05)/.6)
            self.param('PARAM_ARM_R_ORDER',1)
            self.param('PARAM_ARM_L_ORDER',1)
            for i in range(1,14):self.param(f'PARAM_HAND_R_{i:02d}',1 if i==5 else 0)
            real_age=now-e.since
            self.param('PARAM_MOUTH_OPEN_Y',(.12+abs(math.sin(real_age*7))*.3)*(1-exhausted))
            self.param('EYE_TWINKLE_01',ease(age/2)*(1-exhausted))
            blink=1-.96*math.exp(-((real_age%4.7-4.45)/.065)**2) if age<3.3 else 1
            self.param('PARAM_EYE_R_OPEN',blink*(1-.78*exhausted));self.param('PARAM_EYE_L_OPEN',blink*(1-.78*exhausted))
            wind=math.exp(-max(0,age-CAST_RELEASE)*1.7) if age>CAST_RELEASE else .18*ease(age/1.3)
            self.param('PARAM_MANTLE_SHAKE_01',math.sin(real_age*8)*wind)
            self.param('PARAM_MANTLE_SHAKE_02',math.sin(real_age*8-1)*wind*.65)
            self.param('PARAM_HAIR_SIDE',math.sin(real_age*5)*wind*.18)
            self.param('PARAM_HAIR_BACK_01',math.sin(real_age*4.5-1)*wind*.14)
        # Retain the rendered pose across state changes, then ease toward native
        # motion/interaction targets. Eyes and mouth retain their fast response.
        if getattr(e,'singing',False) and state=='idle' and not reduced:
            self.param('PARAM_ANGLE_Z',1.7*math.sin(now*2.4))
            self.param('PARAM_BODY_ANGLE_Z',.65*math.sin(now*2.4-.25))
            self.param('PARAM_MOUTH_FORM',.35)
        if e.voice_mouth is not None:self.param('PARAM_MOUTH_OPEN_Y',e.voice_mouth)
        wanted={n:self.model.GetParamValueById(n) for n in self.param_ids}
        for name,value in wanted.items():
            previous=self.filtered_params.get(name,value)
            tau=.14 if age<.35 and state!='idle' else .055
            if 'EYE_' in name or 'MOUTH_' in name:tau=.018
            if name.startswith(('PARAM_HAND_R_0','PARAM_HAND_R_1','PARAM_HAND_L_0','PARAM_HAND_L_1')):tau=.028
            if any(k in name for k in ('ANGLE','ROTATE','FLUFFY','SHAKE','HAIR')):
                spring=self.joint_springs.setdefault(name,Spring(previous))
                current=spring.step(value,dt,.11 if age<.35 and state!='idle' else .075)
            else:current=previous+(value-previous)*(1-math.exp(-dt/tau))
            self.filtered_params[name]=current;self.param(name,current)
        if not self.hand_mesh:self.find_hand_meshes()
        desktop_alpha=desk_visibility(age) if state=='cast' else 1
        if desktop_alpha<.001:
            self.context.doneCurrent();self.draw_caster(p,e,age,reduced);return
        layers={}
        for name,visible in self.part_groups.items():
            for i,part in enumerate(self.part_ids):self.model.SetPartOpacity(i,1 if part in visible or part in self.visibility_support_parts else 0)
            self.fbo.bind();GL.glViewport(0,0,self.fbo.width(),self.fbo.height());live2d.clearBuffer()
            self.model.Draw();layers[name]=self.fbo.toImage();self.fbo.release()
        for i in range(len(self.part_ids)):self.model.SetPartOpacity(i,1)
        # Repaint only hair that is actually visible in the native head pass.
        # Its isolated pass also contains the hidden crown under the hat; using
        # that entire image would put the crown above the original brim.
        hair=layers['front_hair'];head=layers['head']
        hp=np.frombuffer(hair.bits(),np.uint8).reshape(hair.height(),hair.bytesPerLine())[:,:hair.width()*4].reshape(hair.height(),hair.width(),4)
        base=np.frombuffer(head.bits(),np.uint8).reshape(head.height(),head.bytesPerLine())[:,:head.width()*4].reshape(head.height(),head.width(),4)
        visible=hp[:,:,3]>220
        # Compare channels separately: a strided RGB max reduction allocated
        # several full-size temporary arrays and stalled every animation frame.
        for channel in range(3):
            difference=np.subtract(hp[:,:,channel],base[:,:,channel],dtype=np.int16)
            visible &= (difference>=-2)&(difference<=2)
        hp.view(np.uint32).reshape(hair.height(),hair.width())[~visible]=0;layers['front_hair']=hair
        self.visible_front_hair=hair
        self.frame=layers['head']
        mouse_wrist=self.table_transform.map(QPointF(149+view.mouse_x,362+view.mouse_y+(2 if e.mouse_button else 0)))+QPointF(0,-9)
        key_wrist=self.table_transform.map(self.keyboard_position)+QPointF(0,-9-3*pulse)
        # Map the currently deformed grip, so joint bending cannot pull a hand
        # away from its mouse or the key it is pressing.
        mouse_source=self.neutral_hands['R'] if state=='drink' else self.hand_position('R')
        key_source=self.hand_position('L')
        mouse_transform=self.arm_transform(QPointF(205,222),mouse_source,self.torso_transform.map(QPointF(205,222)),mouse_wrist,1.04)
        key_shoulder=self.torso_transform.map(QPointF(275,222))
        key_wrist=self.limit_keyboard_reach(key_shoulder,key_wrist)
        key_transform=self.arm_transform(QPointF(275,222),key_source,key_shoulder,key_wrist,1.0)
        self.hand_anchor=mouse_transform.map(self.hand_position('R'))
        self.keyboard_hand_anchor=key_transform.map(self.hand_position('L'))
        self.context.doneCurrent()
        destination=p
        scene=QImage(round(480*self.scene_scale),round(450*self.scene_scale),QImage.Format.Format_ARGB32_Premultiplied);scene.fill(Qt.GlobalColor.transparent)
        p=QPainter(scene);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);p.scale(self.scene_scale,self.scene_scale)
        # Compose original animated Cubism parts into a seated, large-head
        # desktop pose. All character artwork still comes from the real model.
        p.setPen(QPen(QColor('#b98660'),2));p.setBrush(QColor('#443349'))
        chair=QPainterPath();chair.moveTo(222,236);chair.cubicTo(223,209,342,215,348,232)
        chair.lineTo(359,322);chair.lineTo(213,309);chair.closeSubpath();p.drawPath(chair)
        depart=ease(age/.8)*(1-ease((age-CAST_RETURN)/1.1)) if state=='cast' else 0
        actor=QTransform();actor.translate(279-105*depart,238-65*depart);actor.scale(1-.376*depart,1-.376*depart);actor.translate(-279,-238)
        p.save();p.setTransform(actor,True)
        p.save();p.setClipRect(QRectF(45,58,390,263))
        p.setTransform(self.torso_transform,True)
        p.drawImage(QRectF(0,0,480,450),layers['torso'])
        p.restore()
        p.save();p.setClipRect(QRectF(40,58,400,263))
        p.translate(279,238);p.scale(1.25,1.25);p.translate(-240,-200)
        p.drawImage(QRectF(0,0,480,450),layers['head'])
        p.restore()
        p.restore()
        self.desk(p,view,now)
        p.save();p.setTransform(actor,True)
        for side,transform in [('R',mouse_transform),('L',key_transform)]:
            p.save();p.setTransform(transform,True);p.drawImage(QRectF(0,0,480,450),layers[side]);p.restore()
        # Native bangs/side locks remain in front of the lifted sleeve instead
        # of being flattened behind both desk arms.
        p.save();p.setClipRect(QRectF(40,58,400,263));p.translate(279,238);p.scale(1.25,1.25);p.translate(-240,-200)
        p.drawImage(QRectF(0,0,480,450),layers['front_hair']);p.restore()
        if state=='drink':self.cup(p,age)
        p.restore()
        self.draw_cat(p,state,age,now,reduced)
        if state=='cat':
            p.setPen(QColor('#eeb7c7'));p.setFont(QFont('Segoe UI',15));p.drawText(QPointF(372,300),'♪')
        p.end();self.desktop_scene=scene
        destination.save();destination.setOpacity(destination.opacity()*desktop_alpha);destination.drawImage(QRectF(0,0,480,450),scene);destination.restore()
        if state=='cast':self.draw_caster(destination,e,age,reduced)
        else:self.staff_orb=None

    def draw_caster(self,p,e,age,reduced):
        self.context.makeCurrent(self.surface)
        native_fbo=self.cast_fbo;render_scale=1.5
        self.model.Resize(720,675)
        # For verified full-body assets pull the native camera back, continuously,
        # rather than cropping the knees or fabricating missing anatomy.
        depart=ease(age/.8)*(1-ease((age-CAST_RETURN)/1.1))
        reveal=depart if self.full_body else 0
        camera_scale=1.45-.45*reveal
        self.model.SetScale(camera_scale);self.model.SetOffset(0,-.65*(1-reveal))
        for i in range(len(self.part_ids)):self.model.SetPartOpacity(i,1)
        native_fbo.bind();GL.glViewport(0,0,720,675);live2d.clearBuffer();self.model.Draw()
        frame=native_fbo.toImage();native_fbo.release()
        # Keep the native silhouettes of hair, head, sleeves and fingers in
        # front of the wand. A rectangle copied from the full frame also copied
        # unrelated hair/body pixels and caused the previous false overlaps.
        front_parts=set(self.part_groups['head']+self.part_groups['R']+self.part_groups['L'])
        for i,part in enumerate(self.part_ids):self.model.SetPartOpacity(i,1 if part in front_parts or part in self.visibility_support_parts else 0)
        native_fbo.bind();live2d.clearBuffer();self.model.Draw();occlusion=native_fbo.toImage();native_fbo.release()
        for i in range(len(self.part_ids)):self.model.SetPartOpacity(i,1)
        if self.cast_hand_mesh is None and self.model.GetParamValueById('PARAM_HAND_R_05')>.985:
            # Identify the fist by the pixels that disappear when its native
            # hand-form parameter is turned off, rather than selecting a cuff
            # near an invisible neutral hand mesh.
            for i,part in enumerate(self.part_ids):self.model.SetPartOpacity(i,1 if part in self.part_groups['R'] or part in self.visibility_support_parts else 0)
            native_fbo.bind();live2d.clearBuffer();self.model.Draw();on=native_fbo.toImage()
            value=self.model.GetParamValueById('PARAM_HAND_R_05');self.param('PARAM_HAND_R_05',0)
            live2d.clearBuffer();self.model.Draw();off=native_fbo.toImage()
            self.param('PARAM_HAND_R_05',value);self.model.Draw();native_fbo.release()
            for i in range(len(self.part_ids)):self.model.SetPartOpacity(i,1)
            def alpha(img):return np.frombuffer(img.bits(),np.uint8).reshape(img.height(),img.bytesPerLine())[:,:img.width()*4].reshape(img.height(),img.width(),4)[:,:,3]
            yy,xx=np.nonzero(alpha(on).astype(np.int16)-alpha(off).astype(np.int16)>100)
            baseline=QPointF(float(xx.mean())/render_scale,float(yy.mean())/render_scale) if len(xx) else self.hand_position('R')
            choices=[];ids=self.model.GetDrawableIds()
            for index,name in enumerate(ids):
                points=self.projected_vertices(index)
                if not points:continue
                center=QPointF(sum(q.x() for q in points)/len(points),sum(q.y() for q in points)/len(points))
                width=max(q.x() for q in points)-min(q.x() for q in points)
                height=max(q.y() for q in points)-min(q.y() for q in points)
                distance=(center-baseline).manhattanLength()
                if 5<width<35 and 5<height<40 and distance<35 and name in self.model.HitDrawable(center.x()*render_scale,center.y()*render_scale,False):choices.append((distance,index))
            if choices:self.cast_hand_mesh=min(choices)[1]
            if self.cast_hand_mesh is not None:
                vertices=self.projected_vertices(self.cast_hand_mesh)
                coords=np.array([[q.x(),q.y(),1] for q in vertices]).T
                self.cast_grip_weights=np.linalg.lstsq(coords,np.array([baseline.x(),baseline.y(),1]),rcond=None)[0]
            self.renderer_info['grip_probe']=dict(center=[baseline.x(),baseline.y()],mesh=self.cast_hand_mesh,changed_pixels=len(xx))
        points=self.projected_vertices(self.cast_hand_mesh) if self.cast_hand_mesh is not None else []
        if points and self.cast_grip_weights is not None:
            wrist=QPointF(float(sum(q.x()*w for q,w in zip(points,self.cast_grip_weights))),float(sum(q.y()*w for q,w in zip(points,self.cast_grip_weights))))
        else:wrist=self.hand_position('R')
        self.cast_frame=frame;self.frame=frame
        self.model.Resize(self.fbo.width(),self.fbo.height());self.model.SetScale(1.45);self.model.SetOffset(0,-.65);self.context.doneCurrent()
        # Preserve shoes/hem alpha for full-body models; retain the original
        # bottom veil only for knee-up assets. Anchor native feet to the floor.
        y=238-65*depart;scale=1.25-.47*depart
        if self.full_body:
            alpha=np.frombuffer(frame.bits(),np.uint8).reshape(frame.height(),frame.bytesPerLine())[:,:frame.width()*4].reshape(frame.height(),frame.width(),4)[:,:,3]
            ys,xs=np.nonzero(alpha>20)
            if len(ys):
                self.cast_body_bounds=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())]
                foot=ys.max()/render_scale;final_y=380-.78*(foot-200)
                y+=(final_y-173)*depart
        else:
            self.cast_body_bounds=None
            fade=QPainter(frame);fade.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            bottom=(300+150*depart)*render_scale
            ramp=QLinearGradient(0,bottom-35*render_scale,0,bottom);ramp.setColorAt(0,QColor(255,255,255,255));ramp.setColorAt(1,QColor(255,255,255,0));fade.fillRect(frame.rect(),ramp);fade.end()
        transform=QTransform();transform.translate(279-105*depart,y)
        transform.scale(scale,scale);transform.translate(-240,-200)
        p.save();p.setOpacity(p.opacity()*caster_visibility(age));p.setTransform(transform,True)
        p.drawImage(QRectF(0,0,480,450),frame)
        wand=QImage(frame.size(),QImage.Format.Format_ARGB32_Premultiplied);wand.fill(Qt.GlobalColor.transparent)
        # Outer scene scaling already affects body and prop together. Match
        # the native camera zoom too, which only the character used before.
        staff_scale=1.15*camera_scale/1.45
        wp=QPainter(wand);wp.setRenderHint(QPainter.RenderHint.Antialiasing);wp.scale(render_scale,render_scale);wp.translate(wrist);wp.scale(staff_scale,staff_scale)
        local_orb=self.staff(wp,QPointF(0,0),age,reduced);wp.end()
        mask=QPainter(wand);mask.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut);mask.drawImage(0,0,occlusion);mask.end()
        self.cast_occlusion=occlusion;self.cast_wand=wand;self.cast_wrist=wrist
        p.save();p.setOpacity(p.opacity()*(1-ease((age-CAST_RETURN)/.75)))
        p.drawImage(QRectF(0,0,480,450),wand);p.restore()
        self.staff_orb=transform.map(wrist+local_orb*staff_scale)
        p.restore()

    def staff(self,p,wrist,age,reduced):
        p.save();p.translate(wrist);angle=-34+self.model.GetParamValueById('PARAM_HAND_R_ROTATE')*.25+4*ease((age-CAST_RELEASE)/.25);p.rotate(angle)
        wood=QLinearGradient(-5,0,6,0);wood.setColorAt(0,QColor('#58392f'));wood.setColorAt(.45,QColor('#ac7959'));wood.setColorAt(1,QColor('#654333'))
        shaft=QPainterPath();shaft.moveTo(-4,113);shaft.lineTo(-5,-89);shaft.cubicTo(-28,-93,-33,-117,-20,-125);shaft.lineTo(-16,-107);shaft.cubicTo(-15,-104,-7,-105,-4,-97)
        shaft.lineTo(6,-107);shaft.lineTo(17,-101);shaft.cubicTo(32,-85,20,-69,7,-66);shaft.lineTo(6,110);shaft.closeSubpath()
        p.setPen(QPen(QColor('#362329'),1));p.setBrush(wood);p.drawPath(shaft)
        p.setPen(QPen(QColor('#d3a564'),2.2));p.drawLine(QPointF(-4,-53),QPointF(6,-49));p.drawLine(QPointF(-4,-45),QPointF(6,-41))
        p.setPen(QPen(QColor('#594137'),.7));p.drawLine(QPointF(-2,18),QPointF(-2,108))
        charge=ease((age-.3)/3.1)*(1-ease((age-4.8)/.7))
        p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(QColor(251,122,94,int(100*charge)),1.0))
        for radius in (17,21):p.drawEllipse(QPointF(0,-92),radius,radius)
        gem=QRadialGradient(QPointF(-4,-97),16);gem.setColorAt(0,QColor('#ffe5cc'));gem.setColorAt(.24,QColor('#f69c87'));gem.setColorAt(.7,QColor('#c93e51'));gem.setColorAt(1,QColor('#74253f'))
        p.setPen(QPen(QColor('#d4a76a'),1.2));p.setBrush(gem);p.drawEllipse(QPointF(0,-92),13,13)
        p.setPen(QPen(QColor('#ffe0a1'),.8));p.drawArc(QRectF(-11,-103,22,22),20*16,95*16)
        p.restore();r=math.radians(angle)
        return wrist+QPointF(math.sin(r)*92,-math.cos(r)*92)

    def draw_cat(self,p,state,age,now,reduced):
        # Use the original transparent official illustration. The source region
        # selects its character area; no eyes, wings or silhouette are redrawn.
        playing=state=='cat'
        approach=min(1,age/.8)*min(1,max(0,(4-age)/.8)) if playing else 0
        position=self.table_transform.map(QPointF(86+44*approach,320))
        height=70+8*approach
        bob=0 if reduced or state=='sleep' else math.sin(now*(7 if playing else 2))*(3 if playing else 1)
        p.save();p.translate(position.x(),position.y()+bob)
        if playing and not reduced:p.rotate(math.sin(age*5)*5)
        p.drawPixmap(QRectF(-height*.375,-height,height*.75,height),self.cat_art,QRectF(105,105,207,276))
        p.restore()

    def desk(self,p,e,now,_cache=False):
        if not _cache:
            if self.desk_cache.isNull():
                self.desk_cache=QImage(round(480*self.scene_scale),round(450*self.scene_scale),QImage.Format.Format_ARGB32_Premultiplied)
                self.desk_cache.fill(Qt.GlobalColor.transparent)
                cp=QPainter(self.desk_cache);cp.setRenderHint(QPainter.RenderHint.Antialiasing);cp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);cp.scale(self.scene_scale,self.scene_scale)
                self.desk(cp,SimpleNamespace(state='idle',latest_vk=0,tap_until=-1),0,True);cp.end()
            p.drawImage(QRectF(0,0,480,450),self.desk_cache)
            p.save();p.setTransform(self.table_transform,True)
            if e.state=='cast':self.pad_emblem(p,e,now)
            self.mouse_device(p,e,now,149+e.mouse_x,362+e.mouse_y+(2 if e.mouse_button else 0))
            vk={160:16,161:16,162:17,163:17,164:18,165:18}.get(e.latest_vk,e.latest_vk)
            self.active_key=None
            if now<e.tap_until and vk in self.key_by_vk:
                label,rect=self.key_by_vk[vk];self.active_key=label
                p.translate(329.5,365);p.rotate(180);p.translate(-329.5,-365)
                self.keycap(p,rect,label,True)
            p.restore();return
        p.save();p.setTransform(self.table_transform,True)
        p.setPen(QPen(QColor('#4c2d40'),2));p.setBrush(QColor('#453042'))
        p.drawRoundedRect(QRectF(44,322,397,87),13,13)
        p.setPen(QPen(QColor('#ce9b62'),1.6));p.setBrush(QColor('#702f43'))
        p.drawRoundedRect(QRectF(44,315,397,87),13,13)
        p.setPen(QPen(QColor('#b97559'),1));p.setBrush(QColor('#452838'))
        p.drawRoundedRect(QRectF(62,322,179,73),8,8)
        self.pad_emblem(p,e,now)
        p.setFont(QFont('Segoe UI',6,QFont.Weight.Bold));p.setPen(QColor('#e8b779'))
        p.drawText(QPointF(72,397),'EXPLOSION  /  CRIMSON DEMON')
        p.save()
        # Character faces the viewer: rotate the whole keypad, including its
        # legends, so the spacebar is on her side and the numbers face outward.
        # The whole table supplies a shared perspective for both input devices.
        p.translate(329.5,365);p.rotate(180);p.translate(-329.5,-365)
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(17,10,20,180));p.drawRoundedRect(QRectF(254,330,153,75),7,7)
        case=QLinearGradient(253,328,406,402);case.setColorAt(0,QColor('#a34a43'));case.setColorAt(.35,QColor('#5b2737'));case.setColorAt(1,QColor('#291d2d'))
        p.setPen(QPen(QColor('#d3ab66'),1.3));p.setBrush(case);p.drawRoundedRect(QRectF(253,328,153,74),7,7)
        p.setPen(QPen(QColor('#754b42'),.6));p.setBrush(QColor('#251b27'));p.drawRoundedRect(QRectF(256,331,147,67),4,4)
        p.setPen(QPen(QColor('#f2cc84'),.6));p.drawLine(QPointF(261,329.6),QPointF(398,329.6))
        for x in (256.5,402.5):
            for y in (331,399):
                p.setPen(QPen(QColor('#241922'),.7));p.setBrush(QColor('#c99859'));p.drawEllipse(QPointF(x,y),1.15,1.15)
                p.setPen(QPen(QColor('#6a4437'),.4));p.drawLine(QPointF(x-.5,y),QPointF(x+.5,y))
        p.setPen(QPen(QColor('#c99859'),.65))
        for i in range(9):
            x=270+i*13;p.drawLine(QPointF(x,399.8),QPointF(x+3,397.8));p.drawLine(QPointF(x+3,397.8),QPointF(x+6,399.8))
        rows=[[(s,1,ord(s)) for s in row] for row in ('12345','QWERT','ASDFG','ZXCVB')]
        rows.append([('Shift',1.5,16),('Space',2.5,32),('Ctrl',1,17)])
        self.drawn_keys={};self.key_by_vk={};self.active_key=None
        vk=e.latest_vk
        if vk in (160,161):vk=16
        if vk in (162,163):vk=17
        if vk in (164,165):vk=18
        for row,keys in enumerate(rows):
            unit=143/sum(k[1] for k in keys);x=258
            for label,width,key in keys:
                rect=QRectF(x,332+row*13.3,width*unit-3,10.8)
                active=now<e.tap_until and key==vk
                if active:self.active_key=label
                self.keycap(p,rect,label,active)
                self.drawn_keys[label]=rect
                self.key_by_vk[key]=(label,rect)
                x+=width*unit
        p.restore()
        p.restore()

    def pad_emblem(self,p,e,now):
        p.save();p.translate(111,358);p.scale(1,.83)
        casting=e.state=='cast'
        if casting:
            glow=QRadialGradient(QPointF(0,0),44);glow.setColorAt(0,QColor(255,131,41,80));glow.setColorAt(1,QColor(255,91,35,0))
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(glow);p.drawEllipse(QPointF(0,0),44,44)
        p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(QColor('#e4a661') if casting else QColor('#ae7956'),.8))
        for radius in (35,31,24):p.drawEllipse(QPointF(0,0),radius,radius)
        star=QPainterPath()
        for i in range(8):
            angle=((i*3)%7)*math.tau/7-.5*math.pi
            point=QPointF(math.cos(angle)*24,math.sin(angle)*24)
            if i==0:star.moveTo(point)
            else:star.lineTo(point)
        p.drawPath(star)
        for i in range(12):
            a=i*math.pi/6;x=math.cos(a)*33;y=math.sin(a)*33
            p.drawLine(QPointF(x-math.sin(a)*1.4,y+math.cos(a)*1.4),QPointF(x+math.sin(a)*1.4,y-math.cos(a)*1.4))
        p.restore()

    def mouse_device(self,p,e,now,mx,my):
        # Lacquered crimson shell, brass seams and staff-orb scroll wheel.
        cable=QPainterPath();cable.moveTo(mx,my-17);cable.cubicTo(mx,my-34,180,335,188,322)
        p.setPen(QPen(QColor('#231b25'),2.2));p.setBrush(Qt.BrushStyle.NoBrush);p.drawPath(cable)
        p.setPen(QPen(QColor('#b48453'),.55));p.drawPath(cable)
        p.save();p.translate(mx,my);p.rotate(-12)
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(17,10,18,120));p.drawRoundedRect(QRectF(-22,-14,44,34),15,15)
        shell=QLinearGradient(-21,-16,21,17);shell.setColorAt(0,QColor('#765061'));shell.setColorAt(.32,QColor('#362536'));shell.setColorAt(.7,QColor('#211b2b'));shell.setColorAt(1,QColor('#4b2738'))
        p.setBrush(shell);p.setPen(QPen(QColor('#d4a767'),1.15));p.drawRoundedRect(QRectF(-21,-17,42,34),15,15)
        p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(QColor('#6e404b'),.55));p.drawRoundedRect(QRectF(-18.5,-14.5,37,29),12,12)
        for side,x in [(1,-16),(2,3)]:
            lit=e.mouse_button==side
            button=QLinearGradient(x,-13,x+13,0);button.setColorAt(0,QColor('#ef9d5c') if lit else QColor('#a44849'));button.setColorAt(1,QColor('#d86738') if lit else QColor('#692d40'))
            p.setBrush(button);p.setPen(QPen(QColor('#e0b274'),.7));p.drawRoundedRect(QRectF(x,-13,13,13),5,5)
            p.setPen(QPen(QColor('#f0c583'),.65));p.drawLine(QPointF(x+4,-9),QPointF(x+9,-4));p.drawLine(QPointF(x+9,-9),QPointF(x+4,-4))
        p.setPen(QPen(QColor('#e0b274'),.8));p.drawLine(QPointF(0,-14),QPointF(0,-2))
        p.setPen(QPen(QColor('#191321'),1));p.setBrush(QColor('#b98652'));p.drawRoundedRect(QRectF(-3.1,-13,6.2,10),3,3)
        orb=QRadialGradient(QPointF(-.8,-9),4.3);orb.setColorAt(0,QColor('#ffe6bf'));orb.setColorAt(.3,QColor('#e78063'));orb.setColorAt(.7,QColor('#bf3649'));orb.setColorAt(1,QColor('#62263b'))
        p.setBrush(orb);p.setPen(QPen(QColor('#e3b46b'),.6));p.drawEllipse(QPointF(0,-8),2.5,3.5)
        p.setPen(QPen(QColor('#dc9960'),.7));p.drawArc(QRectF(-17,-10,34,23),200*16,135*16)
        p.setPen(QPen(QColor('#ca5254'),1.1));p.drawLine(QPointF(-3.5,8),QPointF(3.5,8));p.drawLine(QPointF(0,4.5),QPointF(0,11.5))
        for x in (-16,16):
            p.setPen(QPen(QColor('#d3a56c'),.6));p.drawLine(QPointF(x,3),QPointF(x,9))
        p.restore()

    def keycap(self,p,rect,label,active):
        accent=label in ('W','A','S','D')
        special=label in ('Shift','Ctrl','Space')
        if active:
            halo=QRadialGradient(rect.center(),rect.width()*.65);halo.setColorAt(0,QColor(255,165,67,125));halo.setColorAt(1,QColor(255,107,43,0))
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(halo);p.drawRoundedRect(rect.adjusted(-2,-2,2,3),3,3)
        p.setPen(QPen(QColor('#b58b55'),.6));p.setBrush(QColor('#1c1320'));p.drawRoundedRect(rect.translated(0,1.4),1.8,1.8)
        face=rect.translated(0,1.1 if active else 0)
        fill=QLinearGradient(face.topLeft(),face.bottomLeft())
        top,bottom=('#ffcf89','#ef9559') if active else (('#b7524c','#6f2d3d') if accent else (('#544052','#2b1f30') if special else ('#fff3d9','#d9bc99')))
        fill.setColorAt(0,QColor(top));fill.setColorAt(1,QColor(bottom));p.setBrush(fill);p.setPen(QPen(QColor('#d7a467') if accent or special or active else QColor('#a78166'),.65));p.drawRoundedRect(face,1.8,1.8)
        p.setPen(QPen(QColor(255,226,166,140),.5));p.drawLine(QPointF(face.left()+3,face.top()+1.2),QPointF(face.right()-3,face.top()+1.2))
        p.setPen(QColor('#fff0c8') if accent or special else QColor('#563140'))
        if active:p.setPen(QColor('#542638'))
        p.setFont(QFont('Consolas',7 if len(label)==1 else 6,QFont.Weight.Bold))
        p.drawText(face,Qt.AlignmentFlag.AlignCenter,'EXPLOSION' if label=='Space' else label)

    def limit_keyboard_reach(self,shoulder,target_wrist):
        # Limit only the keyboard arm, after perspective projection and spring
        # smoothing. Do not distort the mouse hand or alter key highlighting.
        rest=self.table_transform.map(QPointF(334,350))+QPointF(0,-9)
        natural=math.hypot(rest.x()-shoulder.x(),rest.y()-shoulder.y())
        self.keyboard_reach_limit=max(1.,natural*1.18)
        dx=target_wrist.x()-shoulder.x();dy=target_wrist.y()-shoulder.y()
        length=math.hypot(dx,dy)
        if not math.isfinite(length) or length<1e-6:
            return rest
        if length>self.keyboard_reach_limit:
            ratio=self.keyboard_reach_limit/length
            return shoulder+QPointF(dx*ratio,dy*ratio)
        return target_wrist

    @staticmethod
    def arm_transform(joint,neutral_wrist,shoulder,target_wrist,width):
        # Align the original articulated arm to the projected contact point.
        # Width is controlled perpendicular to the arm; shoulders stay attached
        # when the mouse moves rather than sliding the entire arm layer.
        vx=neutral_wrist.x()-joint.x();vy=neutral_wrist.y()-joint.y()
        length=math.hypot(vx,vy);ux=vx/length;uy=vy/length
        tx=target_wrist.x()-shoulder.x();ty=target_wrist.y()-shoulder.y()
        distance=math.hypot(tx,ty);px=-ty/distance*width;py=tx/distance*width
        a=tx/length*ux-px*uy;b=ty/length*ux-py*uy
        c=tx/length*uy+px*ux;d=ty/length*uy+py*ux
        return QTransform(a,b,c,d,shoulder.x()-a*joint.x()-c*joint.y(),shoulder.y()-b*joint.x()-d*joint.y())

    def cup(self,p,age):
        t=min(1,age/.65)*min(1,max(0,(4-age)/.65))
        x=self.hand_anchor.x()+8;y=self.hand_anchor.y()-12
        p.save();p.translate(x,y);p.rotate(-5*t)
        p.setPen(QPen(QColor('#885866'),1));p.setBrush(QColor('#fff0d8'))
        p.drawRoundedRect(QRectF(-12,-10,24,28),3,3)
        p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(QColor('#e3bca4'),3));p.drawEllipse(QRectF(9,-5,11,13))
        p.setPen(QPen(QColor('#a6747b'),1));p.setBrush(QColor('#b8d8e2'));p.drawEllipse(QRectF(-12,-12,24,5))
        p.setPen(QPen(QColor('#c95068'),2));p.drawLine(QPointF(-4,2),QPointF(4,2));p.drawLine(QPointF(0,-2),QPointF(0,6));p.restore()

    def projected_vertices(self,index):
        vertices=self.model.GetDrawableVertices(index);m=self.model.GetMvp()
        points=[]
        for i in range(0,len(vertices),2):
            x,y=vertices[i:i+2]
            xx=m[0]*x+m[4]*y+m[12];yy=m[1]*x+m[5]*y+m[13]
            points.append(QPointF((xx+1)*240,(1-yy)*225))
        return points

    def find_hand_meshes(self):
        # Identify hand meshes by their response to the corresponding arm joint.
        # This avoids relying on artist-specific PartHand naming or overlapping
        # hands at the neutral pose.
        snapshot={x:self.model.GetParamValueById(x) for x in self.param_ids}
        ids=self.model.GetDrawableIds()
        self.fbo.bind()
        for side in ('R','L'):
            self.param('PARAM_ARM_'+side+'_ROTATE',0)
            self.param('PARAM_SHOULDER_'+side+'_ROTATE',0)
            self.model.Draw()
            before=[self.projected_vertices(i) for i in range(len(ids))]
            self.param('PARAM_ARM_'+side+'_ROTATE',40)
            self.param('PARAM_SHOULDER_'+side+'_ROTATE',20)
            self.model.Draw()
            choices=[]
            for i,name in enumerate(ids):
                points=self.projected_vertices(i)
                if not points or not before[i]:continue
                bx=sum(x.x() for x in before[i])/len(before[i]);by=sum(x.y() for x in before[i])/len(before[i])
                x=sum(a.x() for a in points)/len(points);y=sum(a.y() for a in points)/len(points)
                w=max(a.x() for a in points)-min(a.x() for a in points)
                h=max(a.y() for a in points)-min(a.y() for a in points)
                shift=math.hypot(x-bx,y-by)
                if shift>8 and 3<w<45 and 3<h<45:
                    visible=name in self.model.HitDrawable(x*self.render_scale,y*self.render_scale,False)
                    choices.append((visible,shift,i))
            if choices:self.hand_mesh[side]=max(choices)[2]
            for name,value in snapshot.items():self.param(name,value)
        self.model.ResetAllParameters();self.param('PARAM_BODY_ANGLE_X',-7)
        self.model.Draw();self.neutral_hands={side:self.hand_position(side) for side in ('R','L')}
        for name,value in snapshot.items():self.param(name,value)
        self.model.Draw();self.fbo.release()

    def hand_position(self,side):
        index=self.hand_mesh.get(side)
        if index is None:return QPointF(222 if side=='R' else 258,242)
        points=self.projected_vertices(index)
        return QPointF(sum(p.x() for p in points)/len(points),sum(p.y() for p in points)/len(points))

    def region(self,scale,state):
        # Include motion reach rather than remasking every GPU frame.
        r=QRegion(round(40*scale),round(55*scale),round(405*scale),round(355*scale))
        return r

    def close(self):
        if self.closed:return
        self.closed=True
        self.context.makeCurrent(self.surface)
        if self.model:self.model.DestroyRenderer();self.model=None
        self.fbo=None
        self.cast_fbo=None
        live2d.glRelease();live2d.dispose();self.context.doneCurrent()
