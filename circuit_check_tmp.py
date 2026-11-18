from pathlib import Path
from PIL import Image,ImageDraw
p=Path('资料/电气工程/电路理论基础/附件/试题原图')
files=sorted(p.glob('c*-*.png'))
for start in range(0,len(files),20):
 group=files[start:start+20];out=Image.new('RGB',(1600,1500),'white');dr=ImageDraw.Draw(out)
 for i,f in enumerate(group):
  im=Image.open(f).convert('RGB');im.thumbnail((390,265));x=(i%4)*400;y=(i//4)*300
  out.paste(im,(x,y+25));dr.text((x,y),f.name,fill='black')
 out.save(f'C:/Users/Lenovo/AppData/Local/Temp/opencode/cropcheck-{start}.png')
