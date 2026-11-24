"""检查预览 PDF 内含条目编号的链接及其目标页，不能代替阅读器点击。"""
from pathlib import Path
from urllib.parse import unquote
import re
import pymupdf as pdf

root = Path(__file__).resolve().parents[1]
work = root / '附件' / '构建临时' / 'MuPDF审校预览'
paths = [work / (x + '-带定位审校预览.pdf') for x in ('讲义', '题目与解答')]
docs = {p.name: pdf.open(p) for p in paths}
for name, doc in docs.items():
    checked, issues, skipped = 0, [], 0
    for number, page in enumerate(doc, 1):
        for link in page.get_links():
            text = page.get_text(clip=link['from']).strip()
            ids = re.findall(r'\b[KCP]-\d+\b', text)
            if len(ids) != 1:
                skipped += 1
                continue
            target = doc if link['kind'] == pdf.LINK_GOTO else docs.get(unquote(link.get('file', '')))
            index = link.get('page', -1)
            checked += 1
            if target is None or not 0 <= index < len(target):
                issues.append((number, text, '目标文件或页码无效'))
                continue
            # An actual entry heading starts its line with the identifier.
            lines = target[index].get_text().splitlines()
            if not any(re.match(r'^' + re.escape(ids[0]) + r'(?:\s|｜)', s.strip()) for s in lines):
                issues.append((number, text, f'目标第 {index+1} 页未找到对应条目标题'))
    print(f'{name}: 可检查编号链接 {checked}, 问题 {len(issues)}, 其他文字链接未检查 {skipped}')
    for issue in issues:
        print(' ', issue)
    if name.startswith('讲义'):
        expected = ['K-3548','K-3551','K-3522','K-3524','K-3529','K-3532','K-3535','K-3537','K-3541','K-3545','P-3504','核对手记','当前缺口']
    else:
        expected = re.findall(r'^## (.+)$', (root / '题目与解答.md').read_text(encoding='utf-8'), re.M)
    directory_links = sorted(doc[1].get_links(), key=lambda link: link['from'].y0)
    failures = []
    if len(directory_links) != len(expected):
        failures.append(f'目录链接数量 {len(directory_links)}，应为 {len(expected)}')
    for link, title in zip(directory_links, expected):
        index = link.get('page', -1)
        if not 0 <= index < len(doc) or title not in doc[index].get_text():
            failures.append(f'{title} 目标页无对应标题')
    print(f'  目录目标页核对: {len(directory_links)}/{len(expected)}, 问题 {failures}')
for doc in docs.values():
    doc.close()
