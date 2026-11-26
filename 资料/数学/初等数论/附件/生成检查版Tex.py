"""生成临时检查版：python 生成检查版Tex.py 讲义.md（或题目与解答.md）。"""
from pathlib import Path
from datetime import datetime
import re,sys,subprocess,shutil,json,hashlib
from urllib.parse import unquote
from markdown_it import MarkdownIt
ROOT=Path(__file__).resolve().parents[1]
if len(sys.argv)!=2 or sys.argv[1] not in ('讲义.md','题目与解答.md'):
 raise SystemExit('用法：python 生成检查版Tex.py 讲义.md（或题目与解答.md）')
WORK=ROOT/'附件'/'构建临时'/(Path(sys.argv[1]).stem)
OUTPUT=WORK/(Path(sys.argv[1]).stem+'-检查版.pdf')
WORK.mkdir(parents=True,exist_ok=True)
source=(ROOT/sys.argv[1]).read_text(encoding='utf8')
# 将连续的 Unicode 上下标作为一个整体排版；根号必须包住被开方数。
supers = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻ᵃᵇᶜᵈᵉᵏᵖᵗʰʳⁿ', '0123456789-abcde kpthrn'.replace(' ', ''))
subs = str.maketrans('₀₁₂₃₄₅₆₇₈₉ₐₑₕᵢₖₘₙₚₜᵣᵥ₌', '0123456789aehikmnptrv=')
source = re.sub(r'√([A-Za-z0-9]+)', lambda m: r'$\sqrt{' + m.group(1) + r'}$', source)
source = re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹⁻ᵃᵇᶜᵈᵉᵏᵖᵗʰʳⁿ]+', lambda m: '$^{' + m.group().translate(supers) + '}$', source)
source = re.sub(r'[₀₁₂₃₄₅₆₇₈₉ₐₑₕᵢₖₘₙₚₜᵣᵥ₌]+', lambda m: '$_{' + m.group().translate(subs) + '}$', source)
raw={};math={}
def protect_raw(m):
 key=f'CIRRAW{len(raw):05d}';raw[key]=m[1];return '\n\n'+key+'\n\n'
source=re.sub(r'```(?:\{=latex\}|latex|tex)\s*\n(.*?)\n```',protect_raw,source,flags=re.S)
def protect_math(m):
 key=f'CIRMATH{len(math):05d}';math[key]=m[0];return key
source=re.sub(r'\$\$.*?\$\$|(?<!\\)\$[^$\n]+?(?<!\\)\$|\\\[.*?\\\]|\\\(.*?\\\)',protect_math,source,flags=re.S)
def esc(s):
 s=s.replace('Ⅰ','I')
 s=''.join({'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}.get(c,c) for c in s)
 s=s.replace('=',r'=\allowbreak{}').replace('+',r'+\allowbreak{}').replace('≡',r'≡\allowbreak{}')
 s=s.replace('≤',r'$\le$').replace('≥',r'$\ge$').replace('→',r'$\to$').replace('π',r'$\pi$').replace('λ',r'$\lambda$').replace('θ',r'$\theta$')
 s=s.replace('μ',r'$\mu$').replace('△',r'$\triangle$').replace('∶',':').replace('′',r'${}^{\prime}$')
 symbols={'γ':r'$\gamma$','−':r'$-$','≈':r'$\approx$','×':r'$\times$','√':r'$\sqrt{\quad}$','ρ':r'$\rho$','η':r'$\eta$','β':r'$\beta$','α':r'$\alpha$','ω':r'$\omega$','ε':r'$\varepsilon$','σ':r'$\sigma$','φ':r'$\varphi$','δ':r'$\delta$','ψ':r'$\psi$','₀':r'$_{0}$','₁':r'$_{1}$','₂':r'$_{2}$','₃':r'$_{3}$','₄':r'$_{4}$','₅':r'$_{5}$','ₕ':r'$_{h}$','ₐ':r'$_{a}$','ₜ':r'$_{t}$','ᵣ':r'$_{r}$','ₙ':r'$_{n}$','ₑ':r'$_{e}$','ᵥ':r'$_{v}$','ᵦ':r'$_{b}$','ᶠ':r'$^{f}$','ᴴ':r'$^{H}$','²':r'$^{2}$','³':r'$^{3}$','⁶':r'$^{6}$','⁻':r'$^{-}$','¹':r'$^{1}$'}
 for c,v in symbols.items():s=s.replace(c,v)
 for n,c in enumerate('①②③④⑤⑥⑦⑧⑨',1):s=s.replace(c,r'\textcircled{'+str(n)+'}')
 for key,val in math.items():
  if key in s:s=s.replace(key,val.replace('$$',r'\[' ,1).rsplit('$$',1)[0]+r'\]' if val.startswith('$$') else val)
 for key,val in raw.items():
  if key in s:
   val=val.replace(r'\textwidth',r'\linewidth')
   val=re.sub(r'\\subsection(?=[*{])',r'\\subsubsection',val)
   val=re.sub(r'\\section(?=[*{])',r'\\subsection',val)
   s=s.replace(key,val)
 for label in ('【解】','【证明】','【参考答案】','【整理说明】'):
  s=s.replace(label,r'\textcolor{tealaccent}{\textbf{'+label+'}}')
 return s
md=MarkdownIt('commonmark',{'html':True}).enable('table')
pending=[];out=[];hlevel=0;skip_heading=False;table_cols=0;current_box=None
def inline(tokens):
 r=[]; links=[]
 for t in tokens or []:
  if t.type=='text':r.append(esc(t.content))
  elif t.type in ('softbreak','hardbreak'):r.append('\n')
  elif t.type=='code_inline':r.append(r'\texttt{'+esc(t.content)+'}')
  elif t.type=='strong_open':r.append(r'\textbf{')
  elif t.type=='em_open':r.append(r'\emph{')
  elif t.type in ('strong_close','em_close'):r.append('}')
  elif t.type=='link_open':
   href=unquote(t.attrGet('href') or '')
   valid=re.fullmatch(r'#[ckp]-\d+',href,re.I)
   cross=re.fullmatch(r'(讲义|题目与解答)\.md#([ckp]-\d+)',href,re.I)
   links.append(bool(valid or cross))
   if valid:r.append(r'\hyperref['+href[1:]+']{')
   elif cross:
    target='L' if cross[1]=='讲义' else 'Q'
    r.append(r'\href{https://pdf-links.invalid/'+target+'/'+cross[2]+'}{')
  elif t.type=='link_close':
   if links.pop():r.append('}')
  elif t.type=='image':
   name=Path(unquote(t.attrGet('src') or '')).name
   if re.fullmatch(r'图(?:0-1-数论知识路线|[1-8]-1-知识地图)\.svg',name):
    import pymupdf
    svg=ROOT/'附件'/'图示'/name
    if not svg.is_file():raise ValueError('Missing diagram '+name)
    target='diagram-'+str(len(list(WORK.glob('diagram-*.pdf'))))+'.pdf'
    with pymupdf.open(svg) as diagram:
     (WORK/target).write_bytes(diagram.convert_to_pdf())
    r.append(r'\begin{center}\includegraphics[width=.98\linewidth,height=8cm,keepaspectratio]{'+target+r'}\end{center}')
   else:
    if name not in {'q28.png','a28.png','q29.png','a29.png','q30.png','a30.png','q31.png','q33.png','q34.png','a34.png'}:raise ValueError('Unexpected image '+name)
    shutil.copy2(ROOT/'附件'/'试题原图'/name,WORK/name)
    r.append(r'\begin{center}\includegraphics[width=.8\linewidth,height=8cm,keepaspectratio]{'+name+r'}\end{center}')
  elif t.type=='html_inline':pending.extend(re.findall(r'<a\s+id="([^"]+)"\s*>',t.content))
  else:raise ValueError('Unsupported inline '+t.type)
 return ''.join(r)
tokens=md.parse(source)
for i,t in enumerate(tokens):
 typ=t.type
 if typ=='html_block':
  pending+=re.findall(r'<a\s+id="([^"]+)"\s*></a>',t.content)
 elif typ=='heading_open':
  hlevel=int(t.tag[1:]);skip_heading=hlevel==1
  if not skip_heading:
   heading = tokens[i+1].content if i+1<len(tokens) and tokens[i+1].type=='inline' else ''
   lines=5 if heading in ('来源与附件说明','题意待核对') else (18 if hlevel==2 and sys.argv[1]=='题目与解答.md' else (14 if hlevel==2 else 12))
   out.append('\n\\Needspace{'+str(lines)+'\\baselineskip}\n\\'+{2:'section',3:'subsection',4:'subsubsection'}.get(hlevel,'paragraph')+'{')
 elif typ=='heading_close':
  if not skip_heading:
   out.append('}\n')
   for aid in pending:out.append(r'\label{'+aid+'}\n')
   pending.clear()
  skip_heading=False
 elif typ=='inline':
  if not skip_heading:out.append(inline(t.children))
 elif typ=='paragraph_open':
  paragraph = tokens[i+1].content if i+1<len(tokens) and tokens[i+1].type=='inline' else ''
  current_box=None
  if paragraph.startswith('**三句话带走：**'):
   out.append('\n\\Needspace{6cm}\n')
  if paragraph.startswith('**本节核对手记**'):
   out.append('\n\\Needspace{7cm}\n')
  if paragraph.startswith('**符号对照：**'):
   out.append('\n\\Needspace{5cm}\n')
  if paragraph.startswith(('**原文范围补充','**原文条件补充','**原文疑点','**整理补充：')):
   out.append('\n\\Needspace{4\\baselineskip}\n')
  if sys.argv[1]=='讲义.md':
   if paragraph.startswith(('**算术基本定理','对奇素数 p 和 p∤a','求解 ax≡b')):
    current_box='formulabox'
   elif paragraph.startswith(('**模重复平方。**','若模数 m')):
    current_box='typebox'
  if current_box:out.append('\n\\begin{'+current_box+'}\n')
  if i+4<len(tokens) and tokens[i+1].type=='inline' and tokens[i+1].content.startswith('【') and tokens[i+3].type=='paragraph_open' and tokens[i+4].type=='inline' and any(c.type=='image' for c in (tokens[i+4].children or [])):
   out.append('\n\\Needspace{9cm}\n')
  out.append('\n')
 elif typ=='paragraph_close':
  out.append('\n\n')
  if current_box:out.append('\\end{'+current_box+'}\n');current_box=None
 elif typ in ('bullet_list_open','ordered_list_open'):
  out.append('\n\\begin{'+('itemize' if typ=='bullet_list_open' else 'enumerate')+'}\n')
  if typ=='ordered_list_open' and t.attrGet('start'):out.append(r'\setcounter{enumi}{'+str(int(t.attrGet('start'))-1)+'}\n')
 elif typ in ('bullet_list_close','ordered_list_close'):out.append('\n\\end{'+('itemize' if typ=='bullet_list_close' else 'enumerate')+'}\n')
 elif typ=='list_item_open':
  out.append('\\item ')
  for aid in pending:
   if re.fullmatch(r'p-\d+',aid,re.I):
    out.append(r'\pdfbookmark[2]{'+aid.upper()+'}{bookmark-'+aid+r'}')
   out.append(r'\phantomsection\label{'+aid+'}')
  pending.clear()
 elif typ=='list_item_close':out.append('\n')
 elif typ=='blockquote_open':out.append('\n\\begin{quote}\n')
 elif typ=='blockquote_close':out.append('\n\\end{quote}\n')
 elif typ=='hr':out.append('\n\\medskip\\hrule\\medskip\n')
 elif typ=='fence':
  raise ValueError('Unexpected fenced block '+t.info)
 elif typ=='table_open':
  j=i+1;table_cols=0
  while tokens[j].type!='tr_close':
   if tokens[j].type=='th_open':table_cols+=1
   j+=1
  out.append('\n\\begin{longtable}{'+('p{'+str(round((15.9-table_cols*.44)/table_cols,2))+'cm}')*table_cols+'}\n\\toprule\n')
 elif typ=='table_close':out.append('\\bottomrule\n\\end{longtable}\n')
 elif typ=='thead_close':out.append('\n\\midrule\n\\endhead\n')
 elif typ in ('thead_open','tbody_open','tbody_close','tr_open','th_open','td_open'):pass
 elif typ in ('th_close','td_close'):
  if tokens[i+1].type!='tr_close':out.append(' & ')
 elif typ=='tr_close':out.append(' \\\\\n')
 else:raise ValueError('Unsupported token '+typ)
if pending:raise ValueError('Unbound anchors '+str(pending))
body=''.join(out)
assert not re.search(r'CIR(?:RAW|MATH)\d+',body)
# The attached source is treated as data: no file inclusion, writes or shell escape.
assert not re.search(r'\\(?:input|include|write|openout|read|catcode|csname|directlua|usepackage)\b',body)
preamble=r'''\documentclass[zihao=5,a4paper,UTF8,fontset=fandol]{ctexart}
\usepackage[top=2.0cm,bottom=2.0cm,left=1.8cm,right=1.8cm,headheight=15pt]{geometry}
\usepackage{amsmath,amssymb,bm,booktabs,array,tabularx,longtable,enumitem,xcolor,tikz,fancyhdr,needspace}
\setmainfont{Cambria}
\usepackage[most]{tcolorbox}
\usepackage{hyperref}
\definecolor{navy}{HTML}{1B365D}
\definecolor{tealaccent}{HTML}{006D77}
\definecolor{warnred}{HTML}{9E2A2B}
\definecolor{softbg}{HTML}{F4F7FA}
\definecolor{warnbg}{HTML}{FDF3F2}
\definecolor{tipbg}{HTML}{F0F7F7}
\definecolor{bordergray}{HTML}{CBD5E1}
\hypersetup{unicode=true,colorlinks=true,linkcolor=navy,urlcolor=tealaccent,bookmarksdepth=3,pdftitle={初等数论讲义（课件整理版）}}
\newtcolorbox{formulabox}[1][核心公式与基本规律]{enhanced,breakable,colback=softbg,colframe=navy,title=#1,fonttitle=\bfseries,boxrule=.6pt,arc=2pt,left=6pt,right=6pt,top=5pt,bottom=5pt}
\newtcolorbox{typebox}[1][题型分析]{enhanced,breakable,colback=tipbg,colframe=tealaccent,title=#1,fonttitle=\bfseries,boxrule=.6pt,arc=2pt,left=6pt,right=6pt,top=5pt,bottom=5pt}
\newtcolorbox{warnbox}[1][重点与易错点]{enhanced,breakable,colback=warnbg,colframe=warnred,title=#1,fonttitle=\bfseries,boxrule=.6pt,arc=2pt,left=6pt,right=6pt,top=5pt,bottom=5pt}
\newenvironment{prob}[2]{\par\vspace{6pt}\noindent\textbf{\color{navy}#1} \textbf{#2}\par\nopagebreak\vspace{2pt}}{\par\vspace{4pt}}
\newcommand{\sol}{\noindent\textbf{\color{tealaccent}【解】}\ }
\newcommand{\proofbegin}{\noindent\textbf{\color{tealaccent}【证明】}\ }
\newcommand{\dd}{\mathrm{d}}
\newcommand{\ee}{\mathrm{e}}
\newcommand{\vect}[1]{\bm{#1}}
\newcommand{\eps}{\varepsilon}
\newcommand{\blank}[1][2.5cm]{\allowbreak\underline{\hspace{#1}}\allowbreak}
\newcommand{\choicebox}{\hfill(\hspace{1.8em})}
\setlist{itemsep=2pt,parsep=0pt,topsep=3pt}
\setlist[itemize]{leftmargin=1.5em}
\setlist[enumerate]{leftmargin=2em}
\setcounter{tocdepth}{2}
\setcounter{secnumdepth}{0}
\ctexset{section={format=\Large\bfseries\color{navy}},subsection={format=\large\bfseries\color{tealaccent}},subsubsection={format=\normalsize\bfseries}}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\small\color{gray}初等数论讲义}
\fancyhead[R]{\small\color{gray}课件整理版}
\fancyfoot[C]{\thepage}
\emergencystretch=2em
\allowdisplaybreaks
\title{\textbf{初等数论讲义}\\[.4em]\large 课件整理版}
\author{课程资料整理版}
\date{生成日期：CHECK_GENERATED_DATE}
\begin{document}
\maketitle
\clearpage
\tableofcontents
\clearpage
'''
generated_at=datetime.now().astimezone()
preamble=preamble.replace('CHECK_GENERATED_DATE',generated_at.strftime('%Y年%m月%d日'))
if sys.argv[1]=='题目与解答.md':
 preamble=preamble.replace('初等数论讲义','初等数论题目与解答')
 preamble=preamble.replace('subsection={format=\\large\\bfseries\\color{tealaccent}}','subsection={format=\\large\\bfseries\\color{navy}}')
(WORK/'lecture.tex').write_text(preamble+body+'\n\\end{document}\n',encoding='utf8')
for i in range(3):
 p=subprocess.run(['xelatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','lecture.tex'],cwd=WORK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (WORK/f'xelatex-pass{i+1}.txt').write_bytes(p.stdout)
 if p.returncode:print(p.stdout[-5000:].decode('utf8',errors='replace'));raise SystemExit(p.returncode)
shutil.copy2(WORK/'lecture.pdf',OUTPUT)
aux=(WORK/'lecture.aux').read_text(encoding='utf8')
mapping={m[1]:int(m[2]) for m in re.finditer(r'\\newlabel\{([ckp]-\d+)\}\{\{[^}]*\}\{(\d+)\}',aux)}
(WORK/'pdf_page_map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf8')
inputs = [ROOT / sys.argv[1], Path(__file__).resolve()]
if sys.argv[1]=='讲义.md':
 inputs += sorted((ROOT/'附件'/'图示').glob('*.svg'))
manifest = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
(WORK/'build_inputs.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print('CHECK PDF:', OUTPUT, 'mapped IDs:', len(mapping))
