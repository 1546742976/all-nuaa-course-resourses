"""将检查版中的跨文档占位链接改为指向相邻 PDF 的页码。

先分别生成两份检查版，再传入两份 PDF 副本：
python 修复PDF跨文件链接.py 讲义副本.pdf 题册副本.pdf
两份副本需位于同一目录；原始检查版不受修改。
"""
from pathlib import Path
import json
import hashlib
import re
import sys
from urllib.parse import unquote
import pymupdf

root = Path(__file__).resolve().parents[1]
if len(sys.argv) != 3:
    raise SystemExit('用法：python 修复PDF跨文件链接.py 讲义副本.pdf 题册副本.pdf')
lecture, questions = (Path(x).resolve() for x in sys.argv[1:])
if lecture.parent != questions.parent or lecture == questions:
    raise SystemExit('两份不同的 PDF 副本必须位于同一目录')
targets = {'L': lecture, 'Q': questions}
build = root / '附件' / '构建临时'
maps = {
    'L': json.loads((build / '讲义' / 'pdf_page_map.json').read_text(encoding='utf8')),
    'Q': json.loads((build / '题目与解答' / 'pdf_page_map.json').read_text(encoding='utf8')),
}
for key, name in (('L', '讲义'), ('Q', '题目与解答')):
    checked = build / name / (name + '-检查版.pdf')
    if targets[key].read_bytes() != checked.read_bytes():
        raise ValueError(f'{targets[key].name} 不是当前检查版的副本，请重新生成两份检查版')
    manifest = json.loads((build / name / 'build_inputs.json').read_text(encoding='utf8'))
    for relative, expected in manifest.items():
        path = root / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'{name} 的构建输入已改变：{relative}；请重新生成检查版')
page_heights = {}
for key, path in targets.items():
    with pymupdf.open(path) as target_document:
        page_heights[key] = [page.rect.height for page in target_document]
pattern = re.compile(r'https://pdf-links\.invalid/([LQ])/([ckp]-\d+)$', re.I)

for source in (lecture, questions):
    temp = source.with_name(source.stem + '.linking.pdf')
    if temp.exists():
        raise FileExistsError(temp)
    count = 0
    try:
        with pymupdf.open(source) as document:
            for page in document:
                for link in page.get_links():
                    match = pattern.fullmatch(link.get('uri', ''))
                    if not match:
                        continue
                    kind, anchor = match.groups()
                    kind = kind.upper()
                    anchor = anchor.lower()
                    if anchor not in maps[kind]:
                        raise ValueError(f'找不到目标锚点：{kind}/{anchor}')
                    page.delete_link(link)
                    page.insert_link({
                        'kind': pymupdf.LINK_GOTOR,
                        'from': link['from'],
                        'file': targets[kind].name,
                        'page': maps[kind][anchor] - 1,
                        # GoToR 目标使用 PDF 原点在左下角的坐标；页高对应页面顶部。
                        'to': pymupdf.Point(0, page_heights[kind][maps[kind][anchor] - 1]),
                    })
                    count += 1
                # PDF 的 /UF 使用带 BOM 的 UTF-16，供支持 Unicode 文件名的阅读器使用。
                page = document.reload_page(page)
                for link in page.get_links():
                    if link['kind'] == pymupdf.LINK_GOTOR:
                        filename = unquote(link['file'])
                        encoded = 'FEFF' + filename.encode('utf-16-be').hex().upper()
                        document.xref_set_key(link['xref'], 'A/F/UF', '<' + encoded + '>')
            document.save(temp, garbage=4, deflate=True)
        temp.replace(source)
    finally:
        if temp.exists():
            temp.unlink()
    print(f'{source.name}: converted {count} links')
