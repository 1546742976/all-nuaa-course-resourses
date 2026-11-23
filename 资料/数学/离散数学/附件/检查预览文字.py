"""比较 Markdown 可见文本与审校 PDF 文本，输出差异供人工核对。"""
from pathlib import Path
from html.parser import HTMLParser
from difflib import SequenceMatcher
import re
import pymupdf
from markdown_it import MarkdownIt

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
    def handle_data(self, text):
        self.text.append(text)

root = Path(__file__).resolve().parents[1]
work = root / '附件' / '构建临时' / 'MuPDF审校预览'
md = MarkdownIt('commonmark', {'html': True}).enable('table')
for name in ('讲义', '题目与解答'):
    parser = VisibleText()
    parser.feed(md.render((root / (name + '.md')).read_text(encoding='utf-8')))
    source = re.sub(r'\s+', '', ''.join(parser.text))
    doc = pymupdf.open(work / (name + '-带定位审校预览.pdf'))
    output = re.sub(r'\s+', '', ''.join(p.get_text() for p in doc))
    matcher = SequenceMatcher(None, source, output, autojunk=False)
    differences = [(kind, source[a:b], output[c:d]) for kind,a,b,c,d in matcher.get_opcodes() if kind in ('replace', 'delete')]
    report = '\n'.join(f'{kind}\t{a!r}\t{b!r}' for kind,a,b in differences)
    (work / (name + '-文字差异.txt')).write_text(report, encoding='utf-8')
    print(f'{name}: 可见文本 {len(source)} 字符, 替换或缺失片段 {len(differences)}')
