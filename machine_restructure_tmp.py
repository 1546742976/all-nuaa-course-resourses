from pathlib import Path
import re
p=Path('资料/机械工程/机械设计基础/讲义.md'); s=p.read_text(encoding='utf8')
matches=list(re.finditer(r'^<a id="([ckp]-\d+)"></a>\s*$',s,re.M))
prefix=s[:matches[0].start()]
parts={m.group(1):s[m.start():(matches[i+1].start() if i+1<len(matches) else len(s))] for i,m in enumerate(matches)}
assert len(parts)==len(matches)
prefix=prefix.replace('整理版本 0.2','整理版本 0.3')
groups=[
('阅读说明与资料边界',['c-3400','c-3407','c-3408','c-3416','c-3423','c-3435','c-3405','c-3406']),
('一、机械设计基础：构件、材料与强度',['c-3401','k-3420','k-3422']),
('二、平面机构：自由度、连杆与凸轮',['c-3402','c-3404','k-3410','k-3436','k-3418','k-3424']),
('三、机械传动：螺旋、带、齿轮与轮系',['c-3403','k-3409','k-3415','k-3426','k-3437','k-3411','k-3425','k-3440','k-3412','k-3419']),
('四、机械零部件：连接、轴承、轴与平衡',['k-3413','k-3427','k-3414','k-3428','k-3439','k-3417','k-3438','k-3421']),
('五、综合试卷及配套参考答案',['c-3429','k-3430','k-3431','k-3432','k-3433']),
('六、来源与附件',['c-3434'])]
ids=[x for _,g in groups for x in g]
assert len(ids)==len(parts) and set(ids)==set(parts),(set(parts)-set(ids),set(ids)-set(parts))
out=[prefix]
for title,ids in groups:
 out.append('## '+title+'\n\n')
 for key in ids:
  chunk=parts[key]
  chunk=re.sub(r'^## (?=[CKP]-\d+)', '### ',chunk,flags=re.M)
  if key=='c-3435': chunk=chunk.replace('本节图形为按运动关系和受力条件','标明自编的图形为按运动关系和受力条件')
  out.append(chunk)
p.write_text(''.join(out),encoding='utf8')
print('reordered',len(parts),'anchors; no omissions')
