from pathlib import Path
import pymupdf,re
root=Path('资料/电气工程/电路理论基础');d=pymupdf.open(root/'原始资料'/'电路理论基础习题(第六版)2022年-new.pdf')
# Coordinates measured from 610×894 source page render.
items=[
('33076',76,(275,75,595,240)),('33076',76,(455,480,600,655)),('33077',77,(175,110,440,300)),('33077',77,(180,600,435,750)),
('33106',81,(40,10,280,185)),('33107',81,(345,10,565,185)),('33108',81,(35,205,550,375)),('33109',81,(355,420,600,565)),('33110',83,(420,375,600,520)),
('33112',81,(305,685,565,865)),('33113',82,(355,5,585,195)),('33114',82,(145,205,465,330)),
('33204',84,(320,420,560,570)),('33205',84,(40,675,265,830)),('33206',84,(315,675,600,830)),('33207',85,(365,50,590,195)),
('33211',85,(40,390,265,550)),('33212',85,(355,375,570,550)),('33213',85,(25,670,275,815)),('33214',85,(315,655,600,815)),
]
text=(root/'讲义.md').read_text(encoding='utf8');counts={}
for ident,page,(x0,y0,x1,y1) in items:
 counts[ident]=counts.get(ident,0)+1;name=f'c{ident}-{counts[ident]}.png';p=d[page-1];r=p.rect
 path=root/'附件'/'试题原图'/name
 if path.exists():raise FileExistsError(path)
 p.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(x0/610*r.width,y0/894*r.height,x1/610*r.width,y1/894*r.height),alpha=False).save(path)
 m=re.search(r'^#{3,4} C-'+ident+r'[^\n]*',text,re.M)
 if not m:raise ValueError(ident)
 pos=m.end();text=text[:pos]+f'\n\n【原题图：CIR-S13 第 {page} 页】\n\n![原题图](附件/试题原图/{name})'+text[pos:]
(root/'讲义.md').write_text(text,encoding='utf8')
# Restore left-side source label in figure 8-16.
p=d[61];p.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(270,95,435,220),alpha=False).save(root/'附件'/'试题原图'/'c33062-1.png')
print('inserted',len(items))
