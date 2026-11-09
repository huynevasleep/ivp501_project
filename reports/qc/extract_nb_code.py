"""In toàn bộ code cell (bỏ output) của các notebook .ipynb được truyền làm tham số.

Chạy:  /usr/bin/python3 -I reports/qc/extract_nb_code.py colab_tham_khao/goc_2/*.ipynb
"""
import json
import sys

for path in sys.argv[1:]:
    nb = json.load(open(path, encoding='utf-8'))
    print(f'\n{"="*70}\n# {path}\n{"="*70}')
    for i, cell in enumerate(nb.get('cells', [])):
        src = ''.join(cell.get('source', []))
        if not src.strip():
            continue
        tag = 'MD' if cell.get('cell_type') == 'markdown' else 'CODE'
        print(f'\n--- cell {i} [{tag}] ---')
        print(src)
