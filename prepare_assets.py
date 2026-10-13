"""Extract atlas cells without changing the generated artwork or its alpha."""
import argparse
from pathlib import Path
from PIL import Image

NAMES=['idle','left','right','happy','drink','cat','cast','tired','sleep']
parser=argparse.ArgumentParser()
parser.add_argument('atlas');parser.add_argument('destination')
args=parser.parse_args()
source=Image.open(args.atlas).convert('RGBA')
dest=Path(args.destination);dest.mkdir(parents=True,exist_ok=True)
assert source.getchannel('A').getextrema()[0]==0, 'Atlas must have a genuine transparent background'
source.save(dest/'atlas.png')
for i,name in enumerate(NAMES):
    col,row=i%3,i//3
    box=(round(col*source.width/3),round(row*source.height/3),round((col+1)*source.width/3),round((row+1)*source.height/3))
    tile=source.crop(box)
    bounds=tile.getchannel('A').getbbox()
    assert bounds, f'Missing sprite: {name}'
    # Uniform contain-fit, centered with a common ground baseline. Alpha retained.
    sprite=tile.crop(bounds)
    sprite.thumbnail((920,920),Image.Resampling.LANCZOS)
    normalized=Image.new('RGBA',(1024,1024))
    normalized.alpha_composite(sprite,((1024-sprite.width)//2,972-sprite.height))
    normalized.save(dest/f'{name}.png')
    print(name,bounds,sprite.size)
icon=Image.open(dest/'idle.png')
icon.save(dest/'icon.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('Assets extracted:',dest.resolve())
