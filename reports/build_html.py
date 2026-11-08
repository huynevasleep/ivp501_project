"""Sinh bản HTML của mỗi báo cáo Markdown trong reports/ (cùng tên, cùng thư mục).

Dùng: pip install markdown   (chỉ cần cho script này, không phải dependency của app)
      python reports/build_html.py                 # mọi file .md trong reports/
      python reports/build_html.py reports/anhnhc/tach-pha-bong.md

Sửa file .md rồi chạy lại script; đừng sửa tay file .html. Kiểu trang ở reports/report.css.
"""
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
CSS = (ROOT/'report.css').read_text(encoding='utf-8')


def build(md_path):
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'sane_lists'], extension_configs={'toc': {'toc_depth': '2-3'}})
    body = md.convert(md_path.read_text(encoding='utf-8'))
    body = body.replace('<table>', '<div class="tbl"><table>').replace('</table>', '</table></div>')
    body = re.sub(r'<img ([^>]*?)\s*/?>', r'<img \1 loading="lazy">', body)
    title = re.search(r'<h1[^>]*>(.*?)</h1>', body)
    if '<ul>' in md.toc:                                  # mục lục sau dòng đầu tiên dưới tiêu đề
        toc = md.toc[md.toc.index('<ul>'):md.toc.rindex('</ul>')+5]
        toc = '<ol>'+toc[4:-5]+'</ol>'
        at = body.index('</p>', body.index('</h1>'))+4 if title else 0
        body = body[:at]+'\n<nav><strong>Mục lục</strong>'+toc+'</nav>\n'+body[at:]
    name = re.sub(r'<[^>]+>', '', title.group(1)) if title else md_path.stem
    html = (f'<!doctype html>\n<html lang="vi">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{name.split(":")[0].strip()}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<main>\n'
            f'<!-- Sinh từ {md_path.name} bằng reports/build_html.py; sửa file .md rồi chạy lại, đừng sửa tay file này. -->\n'
            f'{body}\n</main>\n</body>\n</html>\n')
    out = md_path.with_suffix('.html'); out.write_text(html, encoding='utf-8')
    return out


if __name__ == '__main__':
    files = [Path(a).resolve() for a in sys.argv[1:]] or sorted(ROOT.rglob('*.md'))
    for f in files:
        print(build(f).relative_to(ROOT.parent))
