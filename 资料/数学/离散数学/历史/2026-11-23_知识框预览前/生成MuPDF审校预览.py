"""尝试将权威 Markdown 排成审校预览；结果需人工检查，非正式交付。"""
from pathlib import Path
import json
import re
from urllib.parse import unquote
import pymupdf as pdf
from fontTools.ttLib import TTFont
from markdown_it import MarkdownIt

root = Path(__file__).resolve().parents[1]
outdir = root / '附件' / '构建临时' / 'MuPDF审校预览'
outdir.mkdir(parents=True, exist_ok=True)
archive = pdf.Archive(r'C:\Windows\Fonts')
archive.add(str(outdir))
song_path = outdir / 'simsun-preview.ttf'
song = TTFont(r'C:\Windows\Fonts\simsun.ttc', fontNumber=0)
song_chars = set(song.getBestCmap())
if not song_path.exists():
    song.save(song_path)
song.close()
css = '''
@font-face { font-family: uni; src: url(ARIALUNI.ttf); }
@font-face { font-family: song; src: url(simsun-preview.ttf); }
body { font-family: song; font-size: 10.5pt; line-height: 1.45; }
span.mathfallback { font-family: uni; }
h1 { color: #1B365D; text-align: center; font-size: 20pt; }
h2 { color: #1B365D; font-size: 15pt; }
h3 { color: #006D77; font-size: 12pt; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 0.6pt solid #888; padding: 3pt; }
th { background: #F0F7F7; }
a { color: #006D77; }
'''
md = MarkdownIt('commonmark', {'html': True}).enable('table')
page = pdf.paper_rect('a4')
body = pdf.Rect(51, 57, page.width - 51, page.height - 57)
for name in ('讲义', '题目与解答'):
    source = (root / (name + '.md')).read_text(encoding='utf-8')
    expected = {x.upper() for x in re.findall(r'<a id="([kcp]-\d+)"></a>', source)}
    html = md.render(source)
    # The record remains a Markdown file rather than a PDF destination.
    html = html.replace('<a href="%E6%95%B4%E7%90%86%E8%AE%B0%E5%BD%95.md">', '<a>')
    # Font fallback only for visible text: do not alter link targets or HTML tags.
    parts = re.split(r'(<[^>]*>)', html)
    for i in range(0, len(parts), 2):
        parts[i] = ''.join(
            f'<span class="mathfallback">{c}</span>'
            if ord(c) > 127 and ord(c) not in song_chars else c
            for c in parts[i]
        )
    html = ''.join(parts)
    output = outdir / (name + '-审校预览.pdf')
    story = pdf.Story(html=html, user_css=css, archive=archive)
    writer = pdf.DocumentWriter(str(output))
    more = True
    link_positions = []
    body_page = 0
    while more:
        body_page += 1
        device = writer.begin_page(page)
        more, _ = story.place(body)
        def capture_link(pos):
            if pos.href and pos.open_close & 1:
                link_positions.append((body_page, pos.href, pdf.Rect(pos.rect)))
        story.element_positions(capture_link)
        story.draw(device)
        writer.end_page()
    writer.close()
    doc = pdf.open(output)
    toc = []
    mapping = {}
    sections = {}
    section_names = re.findall(r'^## (.+)$', source, re.M) if name == '题目与解答' else []
    for page_no, p in enumerate(doc, 1):
        for line in p.get_text().splitlines():
            line = line.strip()
            if line in section_names and line not in sections:
                sections[line] = page_no + 2
            match = re.match(r'^([KC]-\d+)\s+\S|^(P-\d+)｜', line.strip())
            item = (match.group(1) or match.group(2)) if match else None
            if item in expected and item not in mapping:
                mapping[item] = page_no + 2
                toc.append([2, line, page_no + 2])
    if name == '题目与解答' and set(sections) != set(section_names):
        raise ValueError(f'未找到目录章节: {set(section_names) - set(sections)}')
    for title in ('重点与易错点', '当前缺口'):
        for page_no, p in enumerate(doc, 1):
            if title in p.get_text().splitlines():
                sections[title] = page_no + 2
                break
    # Cover and contents precede the source body. All printed numbers and
    # destinations refer to the final PDF page numbers, including these pages.
    doc.new_page(pno=0, width=page.width, height=page.height)
    doc.new_page(pno=0, width=page.width, height=page.height)
    cover = doc[0]
    cover.insert_font(fontname='song', fontfile=str(song_path))
    cover.insert_textbox(pdf.Rect(60, 215, page.width - 60, 280), f'离散数学{name}', fontname='song', fontsize=25, align=1, color=(.106,.212,.365))
    cover.insert_textbox(pdf.Rect(65, 300, page.width - 65, 345), '审校预览 · 非最终交付', fontname='song', fontsize=14, align=1, color=(0,.427,.467))
    cover.insert_textbox(pdf.Rect(65, 565, page.width - 65, 620), '来源：期末速成课讲义资料\n整理日期：2026 年 11 月 23 日', fontname='song', fontsize=11, align=1)
    contents = doc[1]
    contents.insert_font(fontname='song', fontfile=str(song_path))
    contents.insert_text((51, 86), '目录', fontname='song', fontsize=18, color=(.106,.212,.365))
    if name == '讲义':
        groups = [('集合与集合运算','K-3513'), ('关系及其性质','K-3516'), ('关系运算与闭包','K-3522'), ('等价、偏序与函数','K-3524'), ('图的基本概念','K-3529'), ('图的矩阵与路径','K-3532'), ('欧拉图和哈密顿图','K-3535'), ('树、匹配与平面图','K-3537'), ('数理逻辑','K-3541'), ('代数系统','K-3545'), ('重点与易错点','P-3504')]
        entries = [(title, mapping[item]) for title, item in groups]
    else:
        entries = [(title, sections[title]) for title in section_names]
    for i, (title, target) in enumerate(entries):
        y = 125 + i * 28
        contents.insert_text((64, y), title, fontname='song', fontsize=11, color=(.106,.212,.365))
        contents.insert_text((page.width - 80, y), str(target), fontsize=11)
        contents.insert_link({'kind': pdf.LINK_GOTO, 'from': pdf.Rect(60, y-14, page.width-55, y+5), 'page': target-1, 'to': pdf.Point(0,0)})
    other = '题目与解答' if name == '讲义' else '讲义'
    other_map_path = outdir / (other + '-条目页码.json')
    other_map = json.loads(other_map_path.read_text(encoding='utf-8')) if other_map_path.exists() else {}
    merged = []
    for page_no, href, rect in link_positions:
        if rect.width < .1 or rect.height < .1:
            continue
        if merged and merged[-1][0] == page_no and merged[-1][1] == href and abs(merged[-1][2].y0 - rect.y0) < .5 and 0 <= rect.x0 - merged[-1][2].x1 < 2:
            merged[-1][2].include_rect(rect)
        else:
            merged.append((page_no, href, rect))
    linked, unresolved = 0, []
    for body_no, raw_href, rect in merged:
        href = unquote(raw_href)
        path, _, fragment = href.partition('#')
        key = fragment.upper()
        target = None
        if not path:
            target = mapping.get(key) or sections.get(fragment)
            if target:
                spec = {'kind': pdf.LINK_GOTO, 'page': target-1, 'to': pdf.Point(0, 0)}
        elif path == other + '.md':
            target = other_map.get(key) if fragment else 1
            if target:
                spec = {'kind': pdf.LINK_GOTOR, 'file': other + '-带定位审校预览.pdf', 'page': target-1, 'to': pdf.Point(0, 0)}
        if target:
            doc[body_no+1].insert_link({'from': rect, **spec})
            linked += 1
        else:
            unresolved.append(href)
    toc = [[1, title, target] for title, target in entries] + toc
    toc.sort(key=lambda x: (x[2], x[0]))
    for page_no, p in enumerate(doc, 1):
        p.insert_font(fontname='simsun', fontfile=r'C:\Windows\Fonts\simsun.ttc')
        if page_no > 2:
            p.insert_text((51, 36), f'离散数学{name} · 审校预览', fontname='simsun', fontsize=8, color=(.45, .45, .45))
        p.insert_text((page.width / 2 - 5, page.height - 28), str(page_no), fontsize=9)
    if toc:
        doc.set_toc(toc)
    final = outdir / (name + '-带定位审校预览.pdf')
    doc.save(final, garbage=4, deflate=True)
    doc.close()
    # PDF file specifications need a UTF-16 Unicode filename for viewers that
    # do not interpret the UTF-8 bytes in a legacy /F entry correctly.
    doc = pdf.open(final)
    unicode_file = pdf.get_pdf_str(other + '-带定位审校预览.pdf')
    for p in doc:
        for link in p.get_links():
            if link['kind'] == pdf.LINK_GOTOR:
                doc.xref_set_key(link['xref'], 'A/F/UF', unicode_file)
    doc.saveIncr()
    (outdir / (name + '-条目页码.json')).write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{name}: {len(doc)} 页, 定位条目 {len(mapping)}/{len(expected)}, 缺失 {sorted(expected - mapping.keys())}, 正文链接 {linked}, 尚未处理 {sorted(set(unresolved))}, 提取字符 {sum(len(p.get_text()) for p in doc)}')
    doc.close()
