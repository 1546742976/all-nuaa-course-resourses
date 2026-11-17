"""从唯一权威源稿讲义.md导出PDF；需要Python markdown-it-py及XeLaTeX。"""
from pathlib import Path
import re,sys,subprocess,shutil,json
from markdown_it import MarkdownIt
ROOT=Path(__file__).resolve().parents[1]
WORK=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'附件'/'构建临时'
WORK.mkdir(parents=True,exist_ok=True)
source=(ROOT/'讲义.md').read_text(encoding='utf8')
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
 s=s.replace('≤',r'$\le$').replace('≥',r'$\ge$').replace('→',r'$\to$').replace('π',r'$\pi$').replace('λ',r'$\lambda$').replace('θ',r'$\theta$')
 s=s.replace('μ',r'$\mu$').replace('△',r'$\triangle$').replace('∶',':').replace('′',r'${}^{\prime}$')
 for n,c in enumerate('①②③④⑤⑥⑦⑧⑨',1):s=s.replace(c,r'\textcircled{'+str(n)+'}')
 for key,val in math.items():
  if key in s:s=s.replace(key,val.replace('$$',r'\[' ,1).rsplit('$$',1)[0]+r'\]' if val.startswith('$$') else val)
 for key,val in raw.items():
  if key in s:
   val=val.replace(r'\textwidth',r'\linewidth')
   val=re.sub(r'\\subsection(?=[*{])',r'\\subsubsection',val)
   val=re.sub(r'\\section(?=[*{])',r'\\subsection',val)
   s=s.replace(key,val)
 return s
md=MarkdownIt('commonmark',{'html':True}).enable('table')
pending=[];out=[];hlevel=0;skip_heading=False;table_cols=0
def inline(tokens):
 r=[]
 for t in tokens or []:
  if t.type=='text':r.append(esc(t.content))
  elif t.type in ('softbreak','hardbreak'):r.append('\n')
  elif t.type=='code_inline':r.append(r'\texttt{'+esc(t.content)+'}')
  elif t.type=='strong_open':r.append(r'\textbf{')
  elif t.type=='em_open':r.append(r'\emph{')
  elif t.type in ('strong_close','em_close'):r.append('}')
  elif t.type=='link_open':r.append('')
  elif t.type=='link_close':r.append('')
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
  if not skip_heading:out.append('\n\\'+{2:'section',3:'subsection',4:'subsubsection'}.get(hlevel,'paragraph')+'{')
 elif typ=='heading_close':
  if not skip_heading:
   out.append('}\n')
   for aid in pending:out.append(r'\label{'+aid+'}\n')
   pending.clear()
  skip_heading=False
 elif typ=='inline':
  if not skip_heading:out.append(inline(t.children))
 elif typ=='paragraph_open':out.append('\n')
 elif typ=='paragraph_close':out.append('\n\n')
 elif typ in ('bullet_list_open','ordered_list_open'):out.append('\n\\begin{'+('itemize' if typ=='bullet_list_open' else 'enumerate')+'}\n')
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
  out.append('\n\\begin{longtable}{'+('p{'+str(round((15.9-table_cols*.44)/table_cols,2))+'cm}')*table_cols+'}\n\\toprule\n')
 elif typ=='table_close':out.append('\\bottomrule\n\\end{longtable}\n')
 elif typ in ('thead_open','thead_close','tbody_open','tbody_close','tr_open','th_open','td_open'):pass
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
\usepackage{amsmath,amssymb,bm,booktabs,array,tabularx,longtable,enumitem,xcolor,tikz,fancyhdr}
\usepackage[most]{tcolorbox}
\usepackage{hyperref}
\definecolor{navy}{HTML}{1B365D}
\definecolor{tealaccent}{HTML}{006D77}
\definecolor{warnred}{HTML}{9E2A2B}
\definecolor{softbg}{HTML}{F4F7FA}
\definecolor{warnbg}{HTML}{FDF3F2}
\definecolor{tipbg}{HTML}{F0F7F7}
\definecolor{bordergray}{HTML}{CBD5E1}
\hypersetup{unicode=true,colorlinks=true,linkcolor=navy,urlcolor=tealaccent,bookmarksdepth=3,pdftitle={电路理论基础课程讲义}}
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
\setcounter{secnumdepth}{1}
\ctexset{section={format=\Large\bfseries\color{navy}},subsection={format=\large\bfseries\color{tealaccent}},subsubsection={format=\normalsize\bfseries}}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\small\color{gray}电路理论基础课程讲义}
\fancyhead[R]{\small\color{gray}资料整理版 1.0}
\fancyfoot[C]{\thepage}
\emergencystretch=2em
\allowdisplaybreaks
\title{\textbf{电路理论基础课程讲义}\\[.4em]\large 核心知识 · 例题详解 · 习题与参考答案}
\author{课程资料整理版}
\date{2026年11月17日}
\begin{document}
\maketitle
\tableofcontents
\clearpage
'''
(WORK/'lecture.tex').write_text(preamble+body+'\n\\end{document}\n',encoding='utf8')
for i in range(2):
 p=subprocess.run(['xelatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','lecture.tex'],cwd=WORK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (WORK/f'xelatex-pass{i+1}.txt').write_bytes(p.stdout)
 if p.returncode:print(p.stdout[-5000:].decode('utf8',errors='replace'));raise SystemExit(p.returncode)
shutil.copy2(WORK/'lecture.pdf',ROOT/'讲义.pdf')
aux=(WORK/'lecture.aux').read_text(encoding='utf8')
mapping={m[1]:int(m[2]) for m in re.finditer(r'\\newlabel\{([ckp]-\d+)\}\{\{[^}]*\}\{(\d+)\}',aux)}
(WORK/'pdf_page_map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf8')
print('PDF exported; mapped IDs:',len(mapping))
