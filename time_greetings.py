"""Daily local greetings; only announcement dates are persisted."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
SHANGHAI=timezone(timedelta(hours=8))
SLOTS=(('morning',360,450),('breakfast',450,600),('lunch',690,810),('dinner',1050,1170),('evening',1170,1350),('bedtime',1350,1560))
def local_now():return datetime.now(SHANGHAI)
def current_slot(now):
    minute=now.hour*60+now.minute;day=now.date()
    if minute<120:return 'bedtime',(day-timedelta(days=1)).isoformat()
    for name,start,end in SLOTS:
        if start<=minute<end:return name,day.isoformat()
    return None
class TimeGreetings:
    def __init__(self,path=None):
        self.path=Path(path) if path else None;self.seen={};self.last_at=0
        if self.path:
            try:
                d=json.loads(self.path.read_text(encoding='utf-8'));self.seen=d.get('seen',{});self.last_at=float(d.get('last_at',0))
            except (OSError,ValueError,TypeError):pass
    def due(self,now):
        slot=current_slot(now)
        if not slot:return None
        name,day=slot
        if day+'|'+name in self.seen or 0<=now.timestamp()-self.last_at<1800:return None
        return name
    def record(self,now):
        slot=current_slot(now)
        if not slot:return
        name,day=slot;self.seen[day+'|'+name]=True;self.last_at=now.timestamp()
        oldest=(now.date()-timedelta(days=7)).isoformat();self.seen={k:v for k,v in self.seen.items() if k[:10]>=oldest}
        if self.path:
            try:
                self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_suffix('.tmp')
                tmp.write_text(json.dumps(dict(seen=self.seen,last_at=self.last_at)),encoding='utf-8');tmp.replace(self.path)
            except OSError:pass
