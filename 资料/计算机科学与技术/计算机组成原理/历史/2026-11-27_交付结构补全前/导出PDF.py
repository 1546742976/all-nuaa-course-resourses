"""从唯一权威源稿讲义.md导出PDF；需要Python markdown-it-py及XeLaTeX。"""
from pathlib import Path
import re,sys,subprocess,shutil,json,os
from urllib.parse import unquote
from markdown_it import MarkdownIt
ROOT=Path(__file__).resolve().parents[1]
book = len(sys.argv)>1 and sys.argv[1]=='--题册'
name = '题目与解答' if book else '讲义'
WORK = ROOT/'附件'/'题册构建临时' if book else (Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'附件'/'构建临时')
WORK.mkdir(parents=True,exist_ok=True)
source=(ROOT/(name+'.md')).read_text(encoding='utf8')
raw={};math={}
def protect_raw(m):
 key=f'CIRRAW{len(raw):05d}';raw[key]=m[1];return '\n\n'+key+'\n\n'
source=re.sub(r'```(?:\{=latex\}|latex|tex)\s*\n(.*?)\n```',protect_raw,source,flags=re.S)
def protect_math(m):
 key=f'CIRMATH{len(math):05d}';math[key]=m[0];return key
source=re.sub(r'\$\$.*?\$\$|(?<!\\)\$[^$\n]+?(?<!\\)\$|\\\[.*?\\\]|\\\(.*?\\\)',protect_math,source,flags=re.S)
def esc(s):
 if '√' in s:raise ValueError('请将根号及其被开方量写为 LaTeX 数学公式')
 s=s.replace('Ⅰ','I')
 s=''.join({'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}.get(c,c) for c in s)
 s=s.replace('≤',r'$\le$').replace('≥',r'$\ge$').replace('→',r'$\to$').replace('π',r'$\pi$').replace('λ',r'$\lambda$').replace('θ',r'$\theta$')
 s=s.replace('μ',r'$\mu$').replace('△',r'$\triangle$').replace('∶',':').replace('′',r'${}^{\prime}$')
 symbols={'γ':r'$\gamma$','−':r'$-$','≈':r'$\approx$','×':r'$\times$','ρ':r'$\rho$','η':r'$\eta$','β':r'$\beta$','α':r'$\alpha$','ω':r'$\omega$','ε':r'$\varepsilon$','σ':r'$\sigma$','φ':r'$\varphi$','χ':r'$\chi$','τ':r'$\tau$','∠':r'$\angle$','δ':r'$\delta$','ψ':r'$\psi$','₀':r'$_{0}$','₁':r'$_{1}$','₂':r'$_{2}$','₃':r'$_{3}$','₄':r'$_{4}$','₅':r'$_{5}$','₆':r'$_{6}$','₇':r'$_{7}$','₈':r'$_{8}$','₉':r'$_{9}$','ₕ':r'$_{h}$','ₐ':r'$_{a}$','ₜ':r'$_{t}$','ᵣ':r'$_{r}$','ₙ':r'$_{n}$','ₛ':r'$_{s}$','ₖ':r'$_{k}$','ₘ':r'$_{m}$','ₚ':r'$_{p}$','ᵢ':r'$_{i}$','ᵋ':r'$^{\epsilon}$','ₑ':r'$_{e}$','ᵥ':r'$_{v}$','ᵦ':r'$_{b}$','ᶠ':r'$^{f}$','ᴴ':r'$^{H}$','²':r'$^{2}$','³':r'$^{3}$','⁶':r'$^{6}$','⁰':r'$^{0}$','⁴':r'$^{4}$','⁵':r'$^{5}$','⁷':r'$^{7}$','⁸':r'$^{8}$','⁹':r'$^{9}$','⁻':r'$^{-}$','¹':r'$^{1}$'}
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
 s=re.sub(r'\b([CKP]-\d+)\b',r'\\mbox{\1}',s)
 return s
md=MarkdownIt('commonmark',{'html':True}).enable('table')
pending=[];out=[];hlevel=0;skip_heading=False;table_cols=0;active_box=None
def inline(tokens):
 r=[]; links=[]
 for pos,t in enumerate(tokens or []):
  if t.type=='text':r.append(esc(t.content))
  elif t.type in ('softbreak','hardbreak'):r.append('\n')
  elif t.type=='code_inline':r.append(r'\texttt{'+esc(t.content)+'}')
  elif t.type=='strong_open':
   solution=book and pos+1<len(tokens) and tokens[pos+1].content in ('【解】','【证明】','【参考答案】')
   r.append(r'\textbf{\color{tealaccent}' if solution else r'\textbf{')
  elif t.type=='em_open':r.append(r'\emph{')
  elif t.type in ('strong_close','em_close'):r.append('}')
  elif t.type=='link_open':
   href=t.attrGet('href') or ''
   valid=re.fullmatch(r'#[ckp]-\d+',href,re.I)
   links.append(bool(valid))
   if valid:r.append(r'\hyperref['+href[1:]+']{')
  elif t.type=='link_close':
   if links.pop():r.append('}')
  elif t.type=='image':
   name=Path(unquote(t.attrGet('src') or '')).name
   if not name.endswith('.svg'):
    raise ValueError('Unexpected image '+name)
   import pymupdf
   source_image=ROOT/'附件'/'图示'/name
   if not source_image.is_file():raise FileNotFoundError(source_image)
   target='figure-'+str(len(list(WORK.glob('figure-*.pdf')))+1).zfill(3)+'.pdf'
   with pymupdf.open(str(source_image)) as image_doc:
    rect=image_doc[0].rect
    required=min(8.0,16.704*rect.height/rect.width)+1.4
    (WORK/target).write_bytes(image_doc.convert_to_pdf())
   name=target
   r.append(r'\Needspace{'+f'{required:.2f}'+r'cm}\begin{center}\includegraphics[width=.96\linewidth,height=8cm,keepaspectratio]{'+name+r'}\end{center}')
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
  heading_text=tokens[i+1].content if i+1<len(tokens) and tokens[i+1].type=='inline' else ''
  reserve=25 if heading_text=='学习地图与课程要求' else 32 if heading_text=='范围与核对手记' else 14 if heading_text.startswith('本章来源对照') else 12 if book and hlevel==2 else 6
  if not skip_heading:out.append('\n\\Needspace{'+str(reserve)+'\\baselineskip}\n\\'+{2:'section',3:'subsection',4:'subsubsection'}.get(hlevel,'paragraph')+'{')
 elif typ=='heading_close':
  if not skip_heading:
   out.append('}\n')
   for aid in pending:out.append(r'\hypertarget{'+aid+r'}{}\label{'+aid+'}\n')
   pending.clear()
  skip_heading=False
 elif typ=='inline':
  if not skip_heading:out.append(inline(t.children))
 elif typ=='paragraph_open':
  current=tokens[i+1].content if i+1<len(tokens) and tokens[i+1].type=='inline' else ''
  core_labels=('**定义。**','**握手定理。**','**最优性原理。**')
  method_labels=('**步骤。**','**具体做法。**','**一笔画。**')
  active_box='formulabox' if not book and current.startswith(core_labels) else ('typebox' if not book and current.startswith(method_labels) else None)
  if active_box:out.append('\\begin{'+active_box+'}\n')
  if i+4<len(tokens) and tokens[i+1].type=='inline' and tokens[i+1].content.startswith('【') and tokens[i+3].type=='paragraph_open' and tokens[i+4].type=='inline' and any(c.type=='image' for c in (tokens[i+4].children or [])):
   out.append('\n\\Needspace{9cm}\n')
  out.append('\n')
 elif typ=='paragraph_close':
  out.append('\n\n')
  if active_box:out.append('\\end{'+active_box+'}\n');active_box=None
 elif typ in ('bullet_list_open','ordered_list_open'):
  out.append('\n\\begin{'+('itemize' if typ=='bullet_list_open' else 'enumerate')+'}\n')
  if typ=='ordered_list_open' and t.attrGet('start'):out.append(r'\setcounter{enumi}{'+str(int(t.attrGet('start'))-1)+'}\n')
 elif typ in ('bullet_list_close','ordered_list_close'):out.append('\n\\end{'+('itemize' if typ=='bullet_list_close' else 'enumerate')+'}\n')
 elif typ=='list_item_open':out.append('\\item ')
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
  head=' '.join(x.content for x in tokens[i:j] if x.type=='inline')
  if table_cols==9 and '结点' in head and 'D₂' not in head:out.append('\n\\Needspace{13\\baselineskip}\n')
  widths=([2.1,2.2,2.0,4.9,1.8] if table_cols==5 and '检验数' in head else [1.3,3.5,1.5,5.9,1.8] if table_cols==5 and '残量路径' in head else [2.3]+[1.2]*8 if table_cols==9 and '结点' in head else [3.3,7.2,3.0] if table_cols==3 and '计算可用调整量' in head else [3.2,2.5,8.8] if table_cols==3 and '基变量顺序' in head and '检验数' in head else [round((15.9-table_cols*.44)/table_cols,2)]*table_cols)
  out.append('\n\\begin{longtable}{'+''.join('p{'+str(w)+'cm}' for w in widths)+'}\n\\toprule\n')
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
\usepackage[most]{tcolorbox}
\usepackage{hyperref}
\definecolor{navy}{HTML}{1B365D}
\definecolor{tealaccent}{HTML}{006D77}
\definecolor{warnred}{HTML}{9E2A2B}
\definecolor{softbg}{HTML}{F4F7FA}
\definecolor{warnbg}{HTML}{FDF3F2}
\definecolor{tipbg}{HTML}{F0F7F7}
\definecolor{bordergray}{HTML}{CBD5E1}
\hypersetup{unicode=true,colorlinks=true,linkcolor=navy,urlcolor=tealaccent,bookmarksdepth=3,pdftitle={计算机组成原理课程讲义}}
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
\setcounter{tocdepth}{1}
\setcounter{secnumdepth}{0}
\ctexset{section={format=\Large\bfseries\color{navy}},subsection={format=\large\bfseries\color{tealaccent}},subsubsection={format=\normalsize\bfseries}}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\small\color{gray}计算机组成原理课程讲义}
\fancyhead[R]{\small\color{gray}资料整理版 0.1}
\fancyfoot[C]{\thepage}
\emergencystretch=2em
\allowdisplaybreaks
\title{\textbf{计算机组成原理课程讲义}\\[.4em]\large 系统 · 运算 · 指令 · 处理器}
\author{课程资料整理版}
\date{2026年11月27日}
\begin{document}
\maketitle
\tableofcontents
\clearpage
'''
preamble=preamble.replace(r'\tableofcontents',r'{\small\tableofcontents}')
if book:
 preamble=preamble.replace('计算机组成原理课程讲义','计算机组成原理题目与解答').replace('系统 · 运算 · 指令 · 处理器','课程例题与解答')
 preamble=preamble.replace(r'subsection={format=\large\bfseries\color{tealaccent}}',r'subsection={format=\large\bfseries\color{navy}}')
(WORK/'lecture.tex').write_text(preamble+body+'\n\\end{document}\n',encoding='utf8')
for i in range(3):
 p=subprocess.run(['xelatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','lecture.tex'],cwd=WORK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (WORK/f'xelatex-pass{i+1}.txt').write_bytes(p.stdout)
 if p.returncode:print(p.stdout[-5000:].decode('utf8',errors='replace'));raise SystemExit(p.returncode)
destination=WORK/(name+'-审校预览.pdf') if os.environ.get('OPERATIONS_PDF_PREVIEW')=='1' else ROOT/(name+'.pdf')
shutil.copy2(WORK/'lecture.pdf',destination)
aux=(WORK/'lecture.aux').read_text(encoding='utf8')
mapping={m[1]:int(m[2]) for m in re.finditer(r'\\newlabel\{([ckp]-\d+)\}\{\{[^}]*\}\{(\d+)\}',aux)}
(WORK/'pdf_page_map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf8')
print('PDF exported; mapped IDs:',len(mapping))
