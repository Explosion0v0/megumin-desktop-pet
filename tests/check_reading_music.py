from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app import Pet,DEFAULTS
from PySide6.QtWidgets import QApplication
from reading_music_validation import check_reading_music
app=QApplication([]);pet=Pet(test_mode=True,settings=dict(DEFAULTS,voice_enabled=False))
try:
 result=check_reading_music(pet)
 print(json.dumps(result,ensure_ascii=False))
 assert result['reading_music_checks_passed']
finally: pet.quit()
