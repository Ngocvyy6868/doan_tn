"""Merge manufacturer specifications from data/pcpartpicker/specs.manual.json into products.vi.json.

Run from the repository root after scripts/prepare_pcpartpicker.py. Idempotent: prices and stock are
never changed; only spec keys listed in the manual file are filled.
"""
from pathlib import Path
import csv
import json

folder = Path.cwd() / 'data/pcpartpicker'
manual = json.loads((folder / 'specs.manual.json').read_text(encoding='utf8'))
products = json.loads((folder / 'products.vi.json').read_text(encoding='utf8'))
OLD = ' Thông số chưa xác minh được để trống.'
NEW = ' Thông số tương thích bổ sung theo trang nhà sản xuất, cần đối chiếu lại trước khi bán.'
unknown_ids = set(manual) - {'_note'} - {p['id'] for p in products}
if unknown_ids:
    raise SystemExit('Mã không có trong products.vi.json: ' + ', '.join(sorted(unknown_ids)))
for p in products:
    extra = manual.get(p['id'])
    if not extra:
        continue
    p['specs'] = {**p['specs'], **extra}
    p['attributes'] = [{'name': k, 'value': ', '.join(v) if isinstance(v, list) else str(v)}
                       for k, v in p['specs'].items() if v is not None]
    p['description'] = p['description'].replace(OLD, NEW)
    source = p['source']
    source['spec_basis'] = 'Tên sản phẩm nguồn và trang nhà sản xuất (data/pcpartpicker/specs.manual.json)'
    source['manual_spec_keys'] = sorted(extra)
    source['unknown_spec_keys'] = [k for k, v in p['specs'].items() if v is None]
(folder / 'products.vi.json').write_text(json.dumps(products, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
with (folder / 'products.vi.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Mã', 'Tên tiếng Việt', 'Danh mục', 'USD', 'VNĐ', 'Có giá', 'Ảnh', 'Thông số', 'Nguồn'])
    for p in products:
        w.writerow([p['id'], p['name'], p['cat'], p['source']['price_usd'], p['price'] if p['active'] else '',
                    p['active'], p['img'], json.dumps(p['specs'], ensure_ascii=False), p['source']['url']])
print('Đã bổ sung thông số cho', sum(p['id'] in manual for p in products), 'sản phẩm.')
