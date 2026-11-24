"""尝试将权威 Markdown 排成审校预览；结果需人工检查，非正式交付。"""
from pathlib import Path
from datetime import datetime
import json
import re
import hashlib
from urllib.parse import unquote
import pymupdf as pdf
from fontTools.ttLib import TTFont
from markdown_it import MarkdownIt

root = Path(__file__).resolve().parents[1]
outdir = root / '附件' / '构建临时' / 'MuPDF审校预览'
outdir.mkdir(parents=True, exist_ok=True)
archive = pdf.Archive(r'C:\Windows\Fonts')
archive.add(str(outdir))
archive.add(str(root))
song_path = outdir / 'simsun-preview.ttf'
song = TTFont(r'C:\Windows\Fonts\simsun.ttc', fontNumber=0)
song_chars = set(song.getBestCmap())
if not song_path.exists():
    song.save(song_path)
song.close()
# Story uses a raster placeholder to reserve each image's layout. After page
# layout, replace each placeholder with the corresponding vector SVG as PDF.
overview_svg = root / '附件' / '图示' / '离散数学总览.svg'
overview_raster = outdir / '离散数学总览_高分辨率.png'
with pdf.open(str(overview_svg)) as overview_doc:
    overview_doc[0].get_pixmap(matrix=pdf.Matrix(2.5, 2.5), alpha=False).save(str(overview_raster))
set_map_svg = root / '附件' / '图示' / '集合知识地图.svg'
set_map_raster = outdir / '集合知识地图_高分辨率.png'
with pdf.open(str(set_map_svg)) as set_map_doc:
    set_map_doc[0].get_pixmap(matrix=pdf.Matrix(2.5, 2.5), alpha=False).save(str(set_map_raster))
for map_name in ('关系', '函数', '图论', '数理逻辑', '代数系统'):
    with pdf.open(str(root / '附件' / '图示' / f'{map_name}知识地图.svg')) as map_doc:
        map_doc[0].get_pixmap(matrix=pdf.Matrix(2.5, 2.5), alpha=False).save(str(outdir / f'{map_name}知识地图_高分辨率.png'))
css = '''
@font-face { font-family: uni; src: url(ARIALUNI.ttf); }
@font-face { font-family: song; src: url(simsun-preview.ttf); }
body { font-family: song; font-size: 10.5pt; line-height: 1.45; }
span.mathfallback { font-family: uni; }
h1 { color: #1B365D; text-align: center; font-size: 20pt; }
h2 { color: #1B365D; font-size: 15pt; }
h3 { color: #006D77; font-size: 12pt; }
h2, h3 { page-break-after: avoid; }
div.corebox, div.methodbox { margin: 5pt 0; padding: 0 6pt 5pt; }
div.coretitle, div.methodtitle { color: white; font-weight: bold; padding: 4pt 6pt; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 0.6pt solid #888; padding: 3pt; }
a { color: #006D77; }
'''
md = MarkdownIt('commonmark', {'html': True}).enable('table')
page = pdf.paper_rect('a4')
body = pdf.Rect(51, 57, page.width - 51, page.height - 57)
# Two passes rebuild both cross-document page maps.
for build_pass in (1, 2):
    for name in ('讲义', '题目与解答'):
        source = (root / (name + '.md')).read_text(encoding='utf-8')
        expected = {x.upper() for x in re.findall(r'<a id="([kcp]-\d+)"></a>', source)}
        html = md.render(source)
        html = re.sub(r'(<img\s+[^>]*src=")([^"]+)', lambda m: m.group(1) + unquote(m.group(2)), html)
        html = html.replace('src="附件/图示/离散数学总览.svg"', 'src="离散数学总览_高分辨率.png"')
        html = html.replace('src="附件/图示/集合知识地图.svg"', 'src="集合知识地图_高分辨率.png"')
        for map_name in ('关系', '函数', '图论', '数理逻辑', '代数系统'):
            html = html.replace(f'src="附件/图示/{map_name}知识地图.svg"', f'src="{map_name}知识地图_高分辨率.png"')
        # These headings were visually verified to be stranded at page ends.
        forced = ('K-3548 ', 'K-3549 ', 'K-3551 ', 'K-3552 ', 'K-3522 ', 'K-3524 ', 'K-3526 ', 'K-3529 ', 'K-3530 ', 'K-3532 ', 'K-3534 ', 'K-3541 ', 'K-3542 ', 'K-3544 ', 'K-3545 ', 'K-3547 ') if name == '讲义' else ('C-34035 ', 'C-34069 ', 'C-34075 ', 'C-34079 ', 'C-34084 ')
        for item in forced:
            html = re.sub(r'<(h[23])>(' + re.escape(item) + ')', r'<\1 style="page-break-before: always">\2', html)
        if name == '讲义':
            html = html.replace('<h2>核对手记</h2>', '<h2 style="page-break-before: always">核对手记</h2>', 1)
            html = html.replace('<h2>来源与附件说明</h2>', '<h2 style="page-break-before: always">来源与附件说明</h2>', 1)
            html = html.replace('<h3>课件原件副本</h3>', '<h3 style="page-break-before: always">课件原件副本</h3>', 1)
            html = html.replace('<p><strong>方法卡｜Huffman 合并</strong>', '<p style="page-break-before: always"><strong>方法卡｜Huffman 合并</strong>', 1)
        def balance_table(match):
            table = match.group(0)
            header = table.split('</thead>', 1)[0]
            count = len(re.findall(r'<th(?:\s[^>]*)?>', header))
            if count == 7:
                table = re.sub(r'<(th|td)>', rf'<\1 style="width: {100/count:.4f}%;">', table)
            return table
        html = re.sub(r'<table>.*?</table>', balance_table, html, flags=re.S)
        if name == '讲义':
            core_labels = ('集合与元素。', '子集和幂集。', '笛卡尔积。', '二元关系。', '合成关系。', '逆关系。')
            box_counter = [0]
            def add_box(match):
                paragraph, label = match.group(0), match.group(1)
                if label in core_labels:
                    box_counter[0] += 1
                    return f'<div class="corebox" id="corebox-{box_counter[0]}"><div class="coretitle" id="coretitle-{box_counter[0]}">核心知识</div>' + paragraph + '</div>'
                if label.startswith('使用步骤'):
                    box_counter[0] += 1
                    return f'<div class="methodbox" id="methodbox-{box_counter[0]}"><div class="methodtitle" id="methodtitle-{box_counter[0]}">方法与步骤</div>' + paragraph + '</div>'
                return paragraph
            html = re.sub(r'<p><strong>(.*?)</strong>.*?</p>', add_box, html, flags=re.S)
            # Put a brief, substantive first paragraph of each section in a
            # knowledge box. Long paragraphs stay unboxed for manual review.
            def box_section(match):
                lead, paragraph = match.group(1), match.group(2)
                text_only = re.sub(r'<[^>]+>', '', paragraph)
                if len(text_only) > 240 or text_only.startswith('以下 a、b、c'):
                    return match.group(0)
                box_counter[0] += 1
                i = box_counter[0]
                return lead + f'<div class="corebox" id="corebox-{i}"><div class="coretitle" id="coretitle-{i}">核心知识</div>' + paragraph + '</div>'
            html = re.sub(r'(<h2(?:\s[^>]*)?>K-\d+[^<]*</h2>\s*<p><strong>学习目标与先修：</strong>(?:(?!</p>).)*</p>\s*)(<p>(?:(?!</p>).)*</p>)', box_section, html, flags=re.S)
        else:
            html = re.sub(r'【(原参考答案思路|原参考答案|整理补充解答|整理校正|整理补充|整理说明|解|证明)】', r'<span class="answerlabel">【\1】</span>', html)
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
        style = css + ('\nh3 { color: #1B365D; font-weight: bold; } span.answerlabel { color: #006D77; font-weight: bold; }' if name == '题目与解答' else '')
        story = pdf.Story(html=html, user_css=style, archive=archive)
        writer = pdf.DocumentWriter(str(output))
        more = True
        link_positions = []
        box_positions = []
        body_page = 0
        while more:
            body_page += 1
            device = writer.begin_page(page)
            more, _ = story.place(body)
            def capture_link(pos):
                if pos.href and pos.open_close & 1:
                    link_positions.append((body_page, pos.href, pdf.Rect(pos.rect)))
                if pos.id and re.match(r'^(core|method)(box|title)-\d+$', pos.id) and pos.open_close & 1:
                    box_positions.append((body_page, pos.id, pdf.Rect(pos.rect)))
            story.element_positions(capture_link)
            story.draw(device)
            writer.end_page()
        writer.close()
        doc = pdf.open(output)
        # Consecutive forced breaks can create truly empty pages. Remove only
        # pages with no text, drawings, images, or recorded link/box positions,
        # then translate all recorded body-page numbers before adding links.
        empty = [i + 1 for i, p in enumerate(doc) if not p.get_text().strip() and not p.get_drawings() and not p.get_images()]
        if any(n in empty for n, _, _ in link_positions + box_positions):
            raise ValueError(f'{name}: 空白页含定位信息，不能自动移除 {empty}')
        def revised_page(number):
            return number - sum(x < number for x in empty)
        link_positions = [(revised_page(n), href, rect) for n, href, rect in link_positions]
        box_positions = [(revised_page(n), ident, rect) for n, ident, rect in box_positions]
        for n in reversed(empty):
            doc.delete_page(n - 1)
        # Draw backgrounds behind the already-laid-out text. MuPDF's CSS
        # backgrounds can otherwise paint a continuation stripe over text.
        for box_page, box_id, rect in sorted(box_positions, key=lambda item: 'box-' in item[1]):
            is_core = box_id.startswith('core')
            color = (.106, .212, .365) if is_core else (0, .427, .467)
            bg = (.957, .969, .98) if is_core else (.941, .969, .969)
            if 'box-' in box_id:
                frame = pdf.Rect(rect.x0 - 5, rect.y0 - 2, rect.x1 + 5, min(rect.y1 + 4, body.y1))
                doc[box_page-1].draw_rect(frame, color=color, fill=bg, width=.6, overlay=False)
                # A box that reaches the page limit may continue in the first
                # text block on the next page; mark that fragment separately.
                if rect.y1 >= body.y1 - 15 and box_page < len(doc):
                    blocks = [b for b in doc[box_page].get_text('blocks') if b[4].strip()]
                    if blocks:
                        first = min(blocks, key=lambda b: b[1])
                        continued = pdf.Rect(frame.x0, max(body.y0, first[1]-3), frame.x1, first[3]+4)
                        doc[box_page].draw_rect(continued, color=color, fill=bg, width=.6, overlay=False)
            else:
                doc[box_page-1].draw_rect(rect, color=color, fill=color, width=0, overlay=False)
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
        for title in ('重点与易错点', '核对手记', '来源与附件说明', '当前缺口'):
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
        generated_date = datetime.now().astimezone().strftime('%Y 年 %m 月 %d 日')
        cover.insert_textbox(pdf.Rect(65, 565, page.width - 65, 620), f'来源：期末速成课讲义资料\n预览生成日期：{generated_date}', fontname='song', fontsize=11, align=1)
        contents = doc[1]
        contents.insert_font(fontname='song', fontfile=str(song_path))
        contents.insert_text((51, 86), '目录', fontname='song', fontsize=18, color=(.106,.212,.365))
        if name == '讲义':
            groups = [('集合与集合运算','K-3548'), ('关系及其性质','K-3551'), ('关系运算与闭包','K-3522'), ('等价、偏序与函数','K-3524'), ('图的基本概念','K-3529'), ('图的矩阵与路径','K-3532'), ('欧拉图和哈密顿图','K-3535'), ('树、匹配与平面图','K-3537'), ('数理逻辑','K-3541'), ('代数系统','K-3545'), ('重点与易错点','P-3504')]
            entries = [(title, mapping[item]) for title, item in groups]
            entries += [(title, sections[title]) for title in ('核对手记', '来源与附件说明', '当前缺口') if title in sections]
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
            elif path.startswith('原始资料/') and (root / path).is_file():
                target = 1
                spec = {'kind': pdf.LINK_GOTOR, 'file': '../../../' + path, 'page': 0, 'to': pdf.Point(0, 0)}
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
                p.insert_text((page.width - 132, 36), '整理预览版', fontname='simsun', fontsize=8, color=(.45, .45, .45))
                p.draw_line((51, 43), (page.width - 51, 43), color=(.75,.78,.8), width=.4)
            p.insert_text((page.width / 2 - 5, page.height - 28), str(page_no), fontsize=9)
        if toc:
            doc.set_toc(toc)
        if name == '讲义':
            for map_name in ('离散数学总览', '集合知识地图', '关系知识地图', '函数知识地图', '图论知识地图', '数理逻辑知识地图', '代数系统知识地图'):
                raster = pdf.Pixmap(str(outdir / f'{map_name}_高分辨率.png'))
                fingerprint = (raster.width, raster.height, raster.n, hashlib.sha256(raster.samples).digest())
                placements = []
                for page_no, map_page in enumerate(doc):
                    for image in map_page.get_images(full=True):
                        pix = pdf.Pixmap(doc, image[0])
                        if (pix.width, pix.height, pix.n, hashlib.sha256(pix.samples).digest()) == fingerprint:
                            placements.extend((page_no, image[0], rect) for rect in map_page.get_image_rects(image[0]))
                if len(placements) != 1:
                    raise ValueError(f'{map_name}: 预期恰有一处图像占位，实际 {len(placements)}')
                page_no, xref, rect = placements[0]
                with pdf.open(str(root / '附件' / '图示' / f'{map_name}.svg')) as svg_doc:
                    with pdf.open('pdf', svg_doc.convert_to_pdf()) as vector_doc:
                        doc[page_no].delete_image(xref)
                        doc[page_no].show_pdf_page(rect, vector_doc, 0)
        final = outdir / (name + '-带定位审校预览.pdf')
        doc.subset_fonts()
        doc.save(final, garbage=4, deflate=True)
        doc.close()
        # PDF file specifications need a UTF-16 Unicode filename for viewers that
        # do not interpret the UTF-8 bytes in a legacy /F entry correctly.
        doc = pdf.open(final)
        for p in doc:
            for link in p.get_links():
                if link['kind'] == pdf.LINK_GOTOR:
                    doc.xref_set_key(link['xref'], 'A/F/UF', pdf.get_pdf_str(unquote(link['file'])))
        doc.saveIncr()
        (outdir / (name + '-条目页码.json')).write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'{name}: {len(doc)} 页, 定位条目 {len(mapping)}/{len(expected)}, 缺失 {sorted(expected - mapping.keys())}, 正文链接 {linked}, 尚未处理 {sorted(set(unresolved))}, 提取字符 {sum(len(p.get_text()) for p in doc)}')
        doc.close()
