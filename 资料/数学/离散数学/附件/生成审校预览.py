"""由 Markdown 生成供审校的临时 PDF；预览未通过正式交付验收。"""
from pathlib import Path
import subprocess
from markdown_it import MarkdownIt

root = Path(__file__).resolve().parents[1]
work = root / '附件' / '构建临时' / 'PDF审校预览'
work.mkdir(parents=True, exist_ok=True)
edge = Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
if not edge.is_file():
    raise SystemExit('未找到 Microsoft Edge；请调整浏览器路径。')
md = MarkdownIt('commonmark', {'html': True}).enable('table')
css = '''
@page { size: A4; margin: 2cm 1.8cm; }
body { font-family: SimSun, "Cambria Math", serif; font-size: 10.5pt; line-height: 1.6; color: #111; overflow-wrap: anywhere; }
h1 { text-align: center; font-size: 20pt; color: #1B365D; }
h2 { font-size: 15pt; color: #1B365D; break-after: avoid; }
h3 { font-size: 12pt; color: #006D77; break-after: avoid; }
h4 { font-size: 11pt; break-after: avoid; }
p { margin: 0.45em 0; } li { margin: 0.2em 0; }
table { border-collapse: collapse; width: 100%; } th, td { border: .6pt solid #9aa9ae; padding: 3pt; }
th { background: #F0F7F7; } a { color: #006D77; text-decoration: none; }
'''
for name in ('讲义', '题目与解答'):
    src = root / (name + '.md')
    html = work / (name + '.html')
    pdf = work / (name + '-审校预览.pdf')
    html.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>' + css + '</style><body>' + md.render(src.read_text(encoding='utf-8')) + '</body></html>', encoding='utf-8')
    try:
        result = subprocess.run([str(edge), '--headless', '--disable-gpu', '--no-first-run', '--no-pdf-header-footer', '--user-data-dir=' + str(work / 'edge-profile'), '--print-to-pdf=' + str(pdf), html.as_uri()], capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        raise SystemExit(f'{name} 导出超时；HTML 保存在 {html}，PDF 未通过验收。')
    if result.returncode or not pdf.is_file():
        raise SystemExit(f'{name} 导出失败: {result.stderr[-2000:]}')
    print(pdf)
