"""R1–R14. Unknown specifications are explicit and never treated as a pass.

Luật lõi (socket, chuẩn RAM, số khe, công suất nguồn, kích thước case) thiếu thông số thì chặn như lỗi.
Luật phụ về giới hạn vật lý hầu như luôn thỏa (RAM tối đa, khe M.2, chiều dài VGA) thiếu thông số thì chỉ
cảnh báo "chưa xác minh"; vi phạm thật (fail) vẫn là lỗi.
"""
import math
import re

from .catalog import fold, number

AIR = ('air', 'khi')
LIQUID = ('liquid', 'aio', 'nuoc')


def values(value):
    if isinstance(value, list):
        return {fold(x) for x in value}
    return {fold(x) for x in re.split('[,;/]', str(value or '')) if str(x).strip()}


def check_build(products, final=True):
    by_cat = {p['cat']: p for p in products}
    checks = []

    def add(code, cats, label, fn, keys=(), severity='error', unknown_severity=None):
        if not all(cat in by_cat for cat in cats):
            return
        specs = [by_cat[cat].get('specs', {}) for cat in cats]
        missing = any(s.get(key) is None or s.get(key) == '' for s, key in
                      ((specs[i], key) for i, key in keys))
        try:
            ok = None if missing else fn(*specs)
        except (TypeError, ValueError, KeyError):
            ok = None
        checks.append({'code': code, 'rule': label,
                       'severity': (unknown_severity or severity) if ok is None else severity,
                       'pair': ' / '.join(by_cat[c].get('name', c) for c in cats),
                       'status': 'unknown' if ok is None else 'pass' if ok else 'fail',
                       'message': ('Chưa xác minh được do thiếu thông số.' if unknown_severity == 'warning'
                                   else 'Thiếu thông số để kiểm tra.') if ok is None else
                                  'Đạt điều kiện.' if ok else 'Không đạt điều kiện.'})

    def ge(a, b):
        a, b = number(a), number(b)
        return None if a is None or b is None else a >= b

    add('R1', ['cpu', 'mainboard'], 'Socket CPU – mainboard',
        lambda c, m: fold(c['socket']) == fold(m['socket']), [(0, 'socket'), (1, 'socket')])
    add('R2', ['ram', 'mainboard'], 'Chuẩn RAM',
        lambda r, m: bool(values(r['ram_type']) & values(m['ram_type'])),
        [(0, 'ram_type'), (1, 'ram_type')])
    add('R3', ['ram', 'mainboard'], 'Số thanh RAM / số khe',
        lambda r, m: ge(m['ram_slots'], r['modules']), [(0, 'modules'), (1, 'ram_slots')])
    add('R4', ['ram', 'mainboard'], 'Dung lượng RAM tối đa',
        lambda r, m: ge(m['max_ram_gb'], r['capacity_gb']), [(0, 'capacity_gb'), (1, 'max_ram_gb')],
        unknown_severity='warning')
    add('R5', ['ssd', 'mainboard'], 'Khe M.2 cho SSD NVMe',
        lambda s, m: True if fold(s['interface']) == 'sata' else
        ge(m.get('m2_slots'), 1) if fold(s['interface']) == 'nvme' else None,
        [(0, 'interface')], unknown_severity='warning')
    add('R6', ['cooler', 'cpu'], 'Socket tản nhiệt',
        lambda t, c: fold(c['socket']) in values(t['sockets']), [(0, 'sockets'), (1, 'socket')])
    add('R7', ['cooler', 'cpu'], 'TDP tản nhiệt',
        lambda t, c: ge(t['tdp_w'], c['tdp_w']), [(0, 'tdp_w'), (1, 'tdp_w')], 'warning')
    if 'psu' in by_cat and 'cpu' in by_cat and ('gpu' in by_cat or final):
        gpu = by_cat.get('gpu', {}).get('specs', {})
        add('R8', ['psu', 'cpu'], 'Công suất nguồn (CPU + GPU + 75W) × 1,3',
            lambda p, c: None if number(c.get('tdp_w')) is None or
                ('gpu' in by_cat and number(gpu.get('tdp_w')) is None) else
                ge(p.get('watt'), math.ceil((number(c['tdp_w']) +
                   (number(gpu['tdp_w']) if 'gpu' in by_cat else 0) + 75) * 1.3)),
            [(0, 'watt'), (1, 'tdp_w')])
    add('R9', ['case', 'mainboard'], 'Kích thước mainboard / case',
        lambda k, m: fold(m['form_factor']) in values(k['supported_mb']),
        [(0, 'supported_mb'), (1, 'form_factor')])
    add('R10', ['case', 'gpu'], 'Chiều dài GPU',
        lambda k, g: ge(k['max_gpu_length_mm'], g['length_mm']),
        [(0, 'max_gpu_length_mm'), (1, 'length_mm')], unknown_severity='warning')
    # R11 applies to air coolers. An AIO has no tower height; its radiator mount is not modelled,
    # so it is a non-blocking warning instead of an unknown error.
    cooler_type = fold(by_cat.get('cooler', {}).get('specs', {}).get('cooler_type') or '')
    if cooler_type in LIQUID and 'case' in by_cat:
        checks.append({'code': 'R11', 'rule': 'Chiều cao tản nhiệt', 'severity': 'warning',
                       'pair': by_cat['case'].get('name', 'case') + ' / ' + by_cat['cooler'].get('name', 'cooler'),
                       'status': 'unknown',
                       'message': 'Tản nước không áp dụng chiều cao tản khí; cần kiểm tra vị trí lắp radiator trên case.'})
    else:
        add('R11', ['case', 'cooler'], 'Chiều cao tản nhiệt',
            lambda k, t: None if fold(t.get('cooler_type', '')) not in AIR else
            ge(k['max_cooler_height_mm'], t['height_mm']),
            [(0, 'max_cooler_height_mm'), (1, 'height_mm'), (1, 'cooler_type')])
    if final:
        add('R12', ['cpu'], 'CPU cần GPU rời khi không có iGPU',
            # Đã có VGA rời thì không cần biết CPU có iGPU hay không.
            lambda c: True if 'gpu' in by_cat else None if type(c.get('has_igpu')) is not bool else c['has_igpu'])
        missing = [c for c in ('cpu', 'mainboard', 'ram', 'ssd', 'psu', 'case') if c not in by_cat]
        checks.append({'code': 'R13', 'rule': 'Đủ linh kiện bắt buộc', 'severity': 'error',
                       'pair': 'Cấu hình', 'status': 'fail' if missing else 'pass',
                       'message': 'Thiếu: ' + ', '.join(missing) if missing else 'Đủ sáu nhóm bắt buộc.'})
        add('R14', ['cpu'], 'Tản nhiệt CPU',
            lambda c: None if type(c['stock_cooler']) is not bool else
                c['stock_cooler'] or 'cooler' in by_cat,
            [(0, 'stock_cooler')], 'warning')
    return checks


def blocked(checks):
    return any(c['severity'] == 'error' and c['status'] != 'pass' for c in checks)
