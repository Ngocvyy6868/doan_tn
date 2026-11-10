"""Generate the draft labelled test set for evaluate_advisor (đề cương 3.3.1, 3.4).

Run from the repository root:  python scripts/build_advisor_eval.py
Output: data/eval/advisor_eval.jsonl (deterministic, seed 400).

Three groups as in the outline:
  vague   – câu mơ hồ cần hỏi lại           (expect_clarification = true)
  complete – câu/hội thoại đủ thông tin      (expect_clarification = false, stage recommendation)
  lookup  – tra cứu sản phẩm cụ thể          (expect_clarification = false, stage lookup)

Labels are generated from templates and marked label_status="draft". The outline requires two
members to label independently and resolve disagreements; review every row before reporting results.
"""
from pathlib import Path
import json
import random

rng = random.Random(400)
root = Path.cwd()
products = {p['id']: p for p in json.loads((root / 'data/pcpartpicker/products.vi.json').read_text(encoding='utf8'))}

PURPOSES = {
    'gaming': ['chơi game', 'gaming', 'chơi Valorant với LOL', 'chơi game AAA ở 2K'],
    'van_phong': ['làm văn phòng', 'làm Word Excel', 'làm kế toán văn phòng'],
    'hoc_tap': ['cho con học online', 'học tập', 'sinh viên học tập'],
    'lap_trinh': ['lập trình', 'code web và chạy Docker', 'làm dev phần mềm'],
    'do_hoa': ['làm đồ họa', 'chạy Photoshop, Illustrator', 'thiết kế 3D bằng Blender'],
    'video': ['dựng video', 'edit video bằng Premiere', 'render video 4K'],
    'ai': ['chạy AI', 'train model deep learning', 'chạy LLM local'],
}
PURPOSE_VI = {'gaming': 'chơi game', 'van_phong': 'văn phòng', 'hoc_tap': 'học tập', 'lap_trinh': 'lập trình',
              'do_hoa': 'đồ họa', 'video': 'dựng video', 'ai': 'chạy AI'}
BUDGETS = [12, 15, 18, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 100, 120, 150]
SCREEN = {True: ['đã gồm màn hình và phím chuột', 'tính luôn cả màn hình, bàn phím, chuột'],
          False: ['chưa gồm màn hình', 'màn hình phím chuột mình có rồi', 'chỉ tính thùng máy thôi']}
LICENSE = {True: ['tính luôn Windows bản quyền', 'cần Win bản quyền'],
           False: ['không cần Windows bản quyền', 'Win mình tự cài']}
BRAND = {'intel': ['thích Intel', 'ưu tiên CPU Intel'], 'amd': ['ưu tiên AMD', 'muốn dùng chip AMD'],
         'tuy_shop': ['']}


def money(m):
    return rng.choice([f'{m} triệu', f'{m}tr', f'{m} củ', f'khoảng {m} triệu', f'tầm {m}tr', f'{m}.000.000đ'])


def pick(options):
    return rng.choice(options)


def sheet(budget=None, purpose=None, screen=None, lic=None, brand='tuy_shop'):
    return {'ngan_sach': budget * 1_000_000 if budget else None, 'muc_dich': purpose,
            'gom_man_hinh_phim_chuot': screen, 'gom_ban_quyen': lic, 'hang_cpu': brand}


def reference(budget, purpose, screen, lic):
    parts = ['CPU', 'mainboard', 'RAM', 'SSD', 'nguồn', 'case']
    if purpose not in ('van_phong', 'hoc_tap', 'lap_trinh'):
        parts.insert(3, 'card đồ họa rời')
    notes = ['ngân sách ' + ('đã gồm màn hình, phím chuột (dự phòng 20%)' if screen else 'chưa gồm màn hình, phím chuột'),
             'đã tính Windows bản quyền' if lic else 'chưa gồm Windows bản quyền']
    return (f'Cấu hình {PURPOSE_VI[purpose]} với ngân sách {budget} triệu; ' + '; '.join(notes) +
            '. Gồm ' + ', '.join(parts) + '. Mọi linh kiện còn hàng, đạt kiểm tra tương thích R1–R14, '
            'tổng tiền nằm trong ±5% ngân sách khả dụng; nếu không đủ hàng thì nêu rõ và đề nghị điều chỉnh ngân sách.')


rows = []


def add(group, messages, requirements, expect, reference_text='', relevant=(), notes=''):
    rows.append({'id': f'{group}-{sum(r["group"] == group for r in rows) + 1:03d}', 'group': group,
                 'messages': messages, 'requirements': requirements, 'expect_clarification': expect,
                 'relevant_product_ids': list(relevant), 'reference': reference_text,
                 'notes': notes, 'label_status': 'draft'})


# 1. Câu mơ hồ (60): thiếu ngân sách, mục đích, hoặc chưa rõ màn hình/bản quyền.
vague_none = ['Tư vấn giúp mình một bộ PC', 'Muốn lắp máy tính', 'Shop build pc giúp em', 'Cần mua máy bàn',
              'Lắp cho tôi bộ máy', 'Có bộ nào ngon không shop']
for i in range(60):
    kind = i % 4
    budget, purpose = rng.choice(BUDGETS), rng.choice(list(PURPOSES))
    if kind == 0:
        add('vague', [pick([f'Build máy {money(budget)}', f'Có {money(budget)} muốn lắp PC',
                            f'Lắp được bộ nào với {money(budget)}?'])], sheet(budget=budget), True)
    elif kind == 1:
        add('vague', [pick([f'Tư vấn máy {pick(PURPOSES[purpose])}', f'Cần PC để {pick(PURPOSES[purpose])}',
                            f'Mình muốn build pc {pick(PURPOSES[purpose])}'])], sheet(purpose=purpose), True)
    elif kind == 2:
        add('vague', [pick(vague_none)], sheet(), True)
    else:
        add('vague', [f'Lắp cho tôi bộ máy {pick(PURPOSES[purpose])} {money(budget)}'],
            sheet(budget, purpose), True, notes='Đủ ngân sách và mục đích nhưng chưa rõ màn hình/bản quyền.')

# 2. Đủ thông tin (75): 40 câu đơn, 35 hội thoại nhiều lượt.
for i in range(75):
    budget, purpose = rng.choice(BUDGETS), rng.choice(list(PURPOSES))
    screen, lic = rng.random() < 0.3, rng.random() < 0.3
    brand = rng.choice(['tuy_shop', 'tuy_shop', 'intel', 'amd'])
    brand_text = pick(BRAND[brand])
    extra = ', ' + brand_text if brand_text else ''
    ref = reference(budget, purpose, screen, lic)
    expected = sheet(budget, purpose, screen, lic, brand)
    if i < 40:
        add('complete', [f'Build PC {pick(PURPOSES[purpose])} {money(budget)}, {pick(SCREEN[screen])}, '
                         f'{pick(LICENSE[lic])}{extra}'], expected, False, ref)
    elif i < 58:
        add('complete', [f'Mình cần máy {pick(PURPOSES[purpose])} {money(budget)}{extra}',
                         f'{pick(SCREEN[screen]).capitalize()}, {pick(LICENSE[lic])}'], expected, False, ref)
    else:
        add('complete', [pick(vague_none), f'{money(budget).capitalize()}, dùng để {pick(PURPOSES[purpose])}{extra}',
                         f'{pick(SCREEN[screen]).capitalize()}, {pick(LICENSE[lic])}'], expected, False, ref)

# 3. Tra cứu sản phẩm (45): lượt 1 nêu nhu cầu, lượt 2 hỏi sản phẩm cụ thể.
NAMED = {'pcpp-HcPgXL': 'Core i5-10600K', 'pcpp-fPyH99': 'Ryzen 7 9800X3D', 'pcpp-3hyH99': 'Ryzen 7 7800X3D',
         'pcpp-WtyV3C': 'Core i7-9700K', 'pcpp-J9PgXL': 'ROG STRIX Z490-E', 'pcpp-fDm2FT': 'ROG STRIX X870E-H',
         'pcpp-W6ndnQ': 'RAM Corsair Vengeance LPX 32GB', 'pcpp-QF9wrH': 'RAM Crucial Pro DDR5 32GB',
         'pcpp-P4FKHx': 'RAM Silicon Power 16GB', 'pcpp-hRQcCJ': 'G.Skill Trident Z5 Neo 64GB',
         'pcpp-hh4Zxr': 'SSD Crucial P310 2TB', 'pcpp-M82j4D': 'SSD Crucial P310 1TB',
         'pcpp-RKYmP6': 'Samsung 990 Pro 4TB', 'pcpp-TcG2FT': 'RX 9060 XT', 'pcpp-fKp323': 'GTX 1070',
         'pcpp-N2zp99': 'RTX 5080', 'pcpp-g8pD4D': 'tản Thermalright Frozen Warframe 360',
         'pcpp-3nTFf7': 'case Thermaltake View 270', 'pcpp-8qFbt6': 'case Fractal Pop XL Air',
         'pcpp-pQxTwP': 'case ROG Strix Helios II', 'pcpp-yWJBD3': 'nguồn be quiet! Pure Power 13 M 750W',
         'pcpp-4FH48d': 'nguồn EVGA 600 W1', 'pcpp-HxKKHx': 'Windows 11 Pro'}
SPEC_QUERIES = [('SSD NVMe 2TB', ['pcpp-hh4Zxr']), ('RAM DDR5', ['pcpp-QF9wrH', 'pcpp-hRQcCJ']),
                ('card đồ họa 16GB VRAM', ['pcpp-TcG2FT', 'pcpp-N2zp99']), ('mainboard socket AM5', ['pcpp-fDm2FT']),
                ('nguồn 750W', ['pcpp-yWJBD3']), ('CPU AMD', ['pcpp-fPyH99', 'pcpp-3hyH99']),
                ('Windows bản quyền', ['pcpp-HxKKHx']), ('tản nhiệt nước 360mm', ['pcpp-g8pD4D'])]
named = list(NAMED.items())
for i in range(45):
    budget, purpose = rng.choice(BUDGETS), rng.choice(list(PURPOSES))
    first = f'Mình đang tính build máy {pick(PURPOSES[purpose])} {money(budget)}'
    if i < 30:
        key, label = named[i % len(named)]
        p = products[key]
        question = pick([f'Giá {label} bao nhiêu?', f'{label} còn hàng không shop?', f'Cho xem thông số {label}'])
        ref = f'{p["name"]}: giá {p["price"]:,} đồng, còn {p["stock"]} sản phẩm.'.replace(',', '.')
        add('lookup', [first, question], sheet(budget, purpose), False, ref, [key])
    else:
        spec, keys = SPEC_QUERIES[i % len(SPEC_QUERIES)]
        question = pick([f'Shop có {spec} nào không?', f'Liệt kê giúp mình {spec} đang bán'])
        ref = 'Các sản phẩm phù hợp: ' + '; '.join(
            f'{products[k]["name"]} ({products[k]["price"]:,} đồng)'.replace(',', '.') for k in keys) + '.'
        add('lookup', [first, question], sheet(budget, purpose), False, ref, keys)

out = root / 'data/eval/advisor_eval.jsonl'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf8')
print({g: sum(r['group'] == g for r in rows) for g in ('vague', 'complete', 'lookup')}, '→', out)
