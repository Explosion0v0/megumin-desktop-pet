"""Coordinated pose sampling and velocity-continuous contact motion."""
from pathlib import Path
import json,math
from PySide6.QtCore import QPointF,QRectF

class Spring:
    def __init__(self,value=0):self.value=value;self.velocity=0
    def step(self,target,dt,tau=.07):
        dt=max(0,min(.08,dt));omega=2/max(.01,tau);decay=math.exp(-omega*dt)
        delta=self.value-target;moment=(self.velocity+omega*delta)*dt
        self.value=target+(delta+moment)*decay
        self.velocity=(self.velocity-omega*moment)*decay
        return self.value

class PointSpring:
    def __init__(self,point=None):
        point=point or QPointF();self.x=Spring(point.x());self.y=Spring(point.y())
    def step(self,target,dt,tau=.07):return QPointF(self.x.step(target.x(),dt,tau),self.y.step(target.y(),dt,tau))

class CastClip:
    def __init__(self,path):
        data=json.loads(Path(path).read_text(encoding='utf-8'));self.tracks={}
        for curve in data['Curves']:
            a=curve['Segments'];keys=[(a[0],a[1])]
            for i in range(2,len(a),7):keys.append((a[i+5],a[i+6]))
            self.tracks[curve['Id']]=keys
    def sample(self,age):
        values={}
        for name,keys in self.tracks.items():
            value=keys[-1][1]
            for (a,x),(b,y) in zip(keys,keys[1:]):
                if age<=b:
                    u=max(0,min(1,(age-a)/(b-a)));value=x+(y-x)*u*u*(3-2*u);break
            values[name]=value
        return values

def keyboard_layout():
    rows=[[(s,1,ord(s)) for s in row] for row in ('12345','QWERT','ASDFG','ZXCVB')]
    rows.append([('Shift',1.5,16),('Space',2.5,32),('Ctrl',1,17)])
    result=[]
    for row,keys in enumerate(rows):
        unit=143/sum(k[1] for k in keys);x=258
        for label,width,vk in keys:
            result.append((label,vk,QRectF(x,332+row*13.3,width*unit-3,10.8)));x+=width*unit
    return result

def keyboard_contact(vk):
    if vk in (160,161):vk=16
    if vk in (162,163):vk=17
    for label,key,rect in keyboard_layout():
        if vk==key:
            c=rect.center();return QPointF(659-c.x(),730-c.y())
    return QPointF(334,350)
