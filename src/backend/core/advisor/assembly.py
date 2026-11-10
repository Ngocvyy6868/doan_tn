"""Budget allocation and greedy assembly; the LLM never chooses a product."""
from .catalog import available, fold, number
from .rules import blocked, check_build

ORDER = ('cpu', 'mainboard', 'ram', 'gpu', 'cooler', 'ssd', 'psu', 'case')
RATIOS = {
    'gaming': (20, 12, 8, 35, 4, 8, 8, 5),
    'creative': (25, 12, 12, 28, 3, 10, 7, 3),
    'office': (30, 18, 15, 0, 3, 17, 10, 7),
}


def budget_plan(sheet, usable):
    """Đề cương 3.3.3: trừ 20% nếu đã gồm màn hình/phím chuột, trừ bản quyền rẻ nhất còn hàng."""
    budget = sheet['ngan_sach']
    peripheral_reserve = budget // 5 if sheet['gom_man_hinh_phim_chuot'] else 0
    licenses = sorted((p for p in usable if p['cat'] == 'license'), key=lambda p: p['price'])
    license_product = licenses[0] if licenses and sheet['gom_ban_quyen'] else None
    license_cost = license_product['price'] if license_product else 0
    group = 'gaming' if sheet['muc_dich'] == 'gaming' else (
        'creative' if sheet['muc_dich'] in ('do_hoa', 'video', 'ai') else 'office')
    return {'budget': budget, 'peripheral_reserve': peripheral_reserve, 'license_product': license_product,
            'component_budget': max(0, budget - peripheral_reserve - license_cost), 'group': group}


def assemble(sheet, catalog, ranked_ids=(), selected_ids=(), retrieve=None, top_k=5):
    """top_k: số sản phẩm đầu kết quả truy xuất (sau reranker) được coi là "có trong kết quả truy xuất"."""
    usable = [p for p in catalog if available(p)]
    plan = budget_plan(sheet, usable)
    budget, peripheral_reserve = plan['budget'], plan['peripheral_reserve']
    license_product, component_budget, group = plan['license_product'], plan['component_budget'], plan['group']
    retrieved = set(list(ranked_ids)[:top_k])
    pinned = {p['cat']: p for p in usable if p['id'] in selected_ids}
    chosen, carry, allocations = [], 0, {}
    errors = []
    if sheet['gom_ban_quyen'] and not license_product:
        errors.append('Không có Windows bản quyền còn hàng; chưa thể xác nhận tổng ngân sách.')
    if len(pinned) != len(selected_ids):
        errors.append('Sản phẩm cố định không khả dụng hoặc có nhiều sản phẩm cùng nhóm.')
    required_cats = {'cpu', 'mainboard', 'ram', 'ssd', 'psu', 'case'} | (
        {'gpu'} if group in ('gaming', 'creative') else set())
    cases = [pinned['case']] if 'case' in pinned else [p for p in usable if p['cat'] == 'case']
    for idx, (cat, ratio) in enumerate(zip(ORDER, RATIOS[group])):
        spent = sum(p['price'] for p in chosen)
        cpu_chosen = next((p for p in chosen if p['cat'] == 'cpu'), None)
        need_cooler = cpu_chosen is not None and cpu_chosen.get('specs', {}).get('stock_cooler') is False
        reserved = 0
        for rc in ORDER[idx + 1:]:
            if rc in pinned:
                reserved += pinned[rc]['price']
            elif rc in required_cats or (rc == 'cooler' and need_cooler):
                reserved += min((p['price'] for p in usable if p['cat'] == rc), default=0)
        max_avail = max(0, component_budget - spent - reserved) if component_budget - spent >= reserved else max(0, component_budget - spent)
        base_allowance = min(max(0, component_budget - spent), component_budget * ratio // 100 + carry)
        allowance = min(base_allowance, max_avail)
        if cat in pinned and pinned[cat]['price'] <= max_avail:
            allowance = max(allowance, pinned[cat]['price'])
        allocations[cat] = allowance
        candidates = [p for p in usable if p['cat'] == cat and p['price'] <= allowance]
        if cat == 'gpu' and group == 'office' and cat not in pinned:
            candidates = []
        if cat == 'cooler' and group == 'office' and cat not in pinned and cpu_chosen and cpu_chosen.get('specs', {}).get('stock_cooler') is True and base_allowance > max_avail:
            candidates = []
        if cat == 'cpu':
            brand = sheet.get('hang_cpu', 'tuy_shop')
            candidates = [p for p in candidates if (brand == 'tuy_shop' or fold(p.get('brand', '')) == brand)
                          and (group != 'office' or p['specs'].get('has_igpu') is True)]
        if cat in pinned:
            candidates = [p for p in candidates if p['id'] == pinned[cat]['id']]
        elif cat == 'cooler' and cases:
            candidates = [p for p in candidates if any(not blocked(check_build(chosen + [p, c], final=False)) for c in cases)]
        if retrieve and candidates:
            retrieved = set(list(retrieve(candidates))[:top_k])
        # Đề cương 3.3.3: ưu tiên sản phẩm có trong top-K truy xuất, sau đó giá cao nhất trong hạn mức.
        candidates.sort(key=lambda p: (p['id'] not in retrieved, -p['price'], p['id']))
        picked = next((p for p in candidates if not blocked(check_build(chosen + [p], final=False))), None)
        if picked:
            chosen.append(picked)
        carry = max(0, base_allowance - (picked['price'] if picked else 0))
    if license_product:
        chosen.append(license_product)
    checks = check_build(chosen)
    if group in ('gaming', 'creative') and not any(p['cat'] == 'gpu' for p in chosen):
        errors.append('Chưa chọn được GPU cho nhu cầu chơi game/đồ họa/video/AI.')
    if any(p['id'] not in {x['id'] for x in chosen} for p in pinned.values()):
        errors.append('Không giữ được tất cả linh kiện đã chọn trong giới hạn ngân sách và tương thích.')
    total = sum(p['price'] for p in chosen)
    return {'products': chosen, 'checks': checks, 'total': total,
            'budget': budget, 'component_budget': component_budget,
            'peripheral_reserve': peripheral_reserve, 'allocations': allocations,
            'errors': errors, 'can_add_to_cart': not errors and not blocked(checks) and
                total + peripheral_reserve <= budget}
