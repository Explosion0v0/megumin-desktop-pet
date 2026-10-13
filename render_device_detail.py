"""Render the actual equipment without the character obscuring its details."""
import sys,time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import Qt
from app import Pet,DEFAULTS

app=QApplication(sys.argv[:1]);pet=Pet(test_mode=True,settings=DEFAULTS.copy());pet.timer.stop()
img=QImage(1620,540,QImage.Format.Format_ARGB32_Premultiplied);img.fill(Qt.GlobalColor.transparent)
p=QPainter(img);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
p.scale(4,4);p.translate(-38,-281);pet.character.desk(p,pet.engine,time.monotonic());p.end()
target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True);img.save(str(target))
pet.character.close();print('Rendered equipment detail:',target)
