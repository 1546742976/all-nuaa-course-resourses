from pathlib import Path
import pymupdf
from PIL import Image,ImageDraw
root=Path('资料/电气工程/电路理论基础')
d=pymupdf.open(root/'原始资料'/'电路理论基础习题(第六版)2022年-new.pdf')
for first,last in [(46,49),(50,53),(54,58),(59,62),(63,66),(67,70),(71,75),(76,79),(81,86)]:
 out=Image.new('RGB',((last-first+1)*450,720),'white'); draw=ImageDraw.Draw(out)
 for j,n in enumerate(range(first,last+1)):
  pix=d[n-1].get_pixmap(matrix=pymupdf.Matrix(1,1),alpha=False)
  im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);im.thumbnail((440,680))
  out.paste(im,(j*450,30));draw.text((j*450,3),str(n),fill='black')
 out.save(f'C:/Users/Lenovo/AppData/Local/Temp/opencode/circuit-pages-{first}.png')
