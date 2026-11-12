"""Budget allocation and greedy assembly; the LLM never chooses a product."""
import re

from .catalog import available, fold, number
from .rules import blocked, check_build

# Card đồ họa chuyên dụng (workstation) đắt nhưng không tối ưu cho chơi game.
WORKSTATION_GPU = re.compile(r'\b(rtx\s*a\d{3,4}|rtx\s*pro|quadro|arc\s*pro|nvidia\s*t\d{3,4})\b')
# Nhóm được nâng cấp bằng tiền còn dư sau khi đã đủ cấu hình: chỉ VGA (quyết định hiệu năng game/đồ họa);
# nhóm khác giữ sản phẩm do truy xuất chọn theo nhu cầu.
UPGRADE_ORDER = {'gaming': ('gpu',), 'creative': ('gpu',), 'office': ()}


# Card dưới mức này chỉ để xuất hình (GT 710/730/1030...), không đủ chơi game.
MIN_GAMING_GPU_W = 50


def suits_group(p, group):
    if p['cat'] != 'gpu' or group != 'gaming':
        return True
    watt = number(p.get('specs', {}).get('tdp_w'))
    return not WORKSTATION_GPU.search(fold(p.get('name', ''))) and (watt is None or watt >= MIN_GAMING_GPU_W)


def _sort_key(p, retrieved):
    # Nguồn: chọn công suất vừa đủ (luật R8 đã loại nguồn thiếu), không chọn nguồn đắt nhất.
    if p['cat'] == 'psu':
        return (number(p['specs'].get('watt')) or 10**6, -p['price'], p['id'])
    # Đề cương 3.3.3: ưu tiên sản phẩm có trong top-K truy xuất, sau đó giá cao nhất trong hạn mức.
    return (p['id'] not in retrieved, -p['price'], p['id'])


# Hạ cấp khi vượt ngân sách: nhóm ít ảnh hưởng tương thích trước; CPU/mainboard giữ nguyên để không đổi socket.
DOWNGRADE_ORDER = ('gpu', 'cooler', 'case', 'psu', 'ssd', 'ram')


# Nhìn trước một bước: CPU phải có mainboard lắp được, mainboard phải có RAM lắp được (đang còn hàng).
LOOKAHEAD = {'cpu': 'mainboard', 'mainboard': 'ram'}


def has_partner(chosen, product, usable):
    partner = LOOKAHEAD.get(product['cat'])
    if partner is None or any(p['cat'] == partner for p in chosen):
        return True
    return any(not blocked(check_build(chosen + [product, p], final=False)) for p in usable if p['cat'] == partner)


def cpu_allowed(p, group, brand):
    return (brand == 'tuy_shop' or fold(p.get('brand', '')) == brand) and (
        group != 'office' or p['specs'].get('has_igpu') is True)


def complete(chosen, usable, group, required_cats, component_budget, pinned_ids, brand='tuy_shop'):
    """Hạn mức theo tỷ lệ có thể để trống một nhóm (VD: RAM rẻ nhất vẫn đắt hơn hạn mức) dù tổng còn dư.
    Bổ sung nhóm thiếu bằng sản phẩm rẻ nhất lắp được, rồi hạ cấp nhóm khác cho vừa ngân sách.
    Không vừa được ngân sách thì giữ nguyên bộ cũ để báo phương án thay thế và số tiền còn thiếu."""
    original, chosen = chosen, list(chosen)
    for cat in ORDER:
        if cat not in required_cats or any(p['cat'] == cat for p in chosen):
            continue
        pool = sorted((p for p in usable if p['cat'] == cat and suits_group(p, group)
                       and (cat != 'cpu' or cpu_allowed(p, group, brand))), key=lambda p: (p['price'], p['id']))
        pick = next((p for p in pool if not blocked(check_build(chosen + [p], final=False))
                     and has_partner(chosen, p, usable)), None)
        if pick is not None:
            chosen.append(pick)
    over = sum(p['price'] for p in chosen) - component_budget
    for cat in DOWNGRADE_ORDER:
        current = next((p for p in chosen if p['cat'] == cat), None)
        if over <= 0:
            break
        if current is None or current['id'] in pinned_ids:
            continue
        if cat == 'cooler':  # tản rời là tùy chọn (R14 chỉ cảnh báo): bỏ trước khi phải hạ cấp phần khác
            chosen.remove(current)
            over -= current['price']
            continue
        others = [p for p in chosen if p is not current]
        cheaper = [p for p in usable if p['cat'] == cat and p['price'] < current['price'] and suits_group(p, group)
                   and not blocked(check_build(others + [p], final=False))]
        if not cheaper:
            continue
        fit = [p for p in cheaper if p['price'] <= current['price'] - over]
        new = max(fit, key=lambda p: (p['price'], p['id'])) if fit else min(cheaper, key=lambda p: (p['price'], p['id']))
        chosen[chosen.index(current)] = new
        over -= current['price'] - new['price']
    return chosen if over <= 0 else original


def upgrade(chosen, usable, group, budget_left, pinned_ids):
    """Dùng tiền còn dư nâng cấp các nhóm quan trọng mà vẫn tương thích (thay trực tiếp, không lắp lại)."""
    for cat in UPGRADE_ORDER[group]:
        current = next((p for p in chosen if p['cat'] == cat), None)
        if current is None or current['id'] in pinned_ids or budget_left <= 0:
            continue
        others = [p for p in chosen if p is not current]
        better = sorted((p for p in usable if p['cat'] == cat and suits_group(p, group)
                         and current['price'] < p['price'] <= current['price'] + budget_left),
                        key=lambda p: (-p['price'], p['id']))
        pick = next((p for p in better if not blocked(check_build(others + [p], final=False))), None)
        if pick:
            budget_left -= pick['price'] - current['price']
            chosen[chosen.index(current)] = pick
    return chosen

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


def _brief(p):
    return {k: p.get(k) for k in ('id', 'name', 'cat', 'brand', 'price', 'img')}


def cheapest_build(usable, group, required_cats, brand='tuy_shop'):
    """Bộ hoàn chỉnh có tổng giá thấp nhất lắp được từ hàng còn bán (không vi phạm luật mức Lỗi).

    Duyệt mọi cặp CPU + mainboard tương thích (socket, chuẩn RAM quyết định các nhóm còn lại); với mỗi cặp lấy
    RAM, SSD, case rẻ nhất lắp được và cặp VGA + nguồn có tổng thấp nhất (VGA rẻ chưa chắc đi với nguồn rẻ).
    Nhánh có giá tối thiểu đã vượt bộ tốt nhất thì bỏ qua. Tản rời không bắt buộc nên không thêm."""
    def pool(cat):
        return sorted((p for p in usable if p['cat'] == cat and suits_group(p, group)
                       and (cat != 'cpu' or cpu_allowed(p, group, brand))), key=lambda p: (p['price'], p['id']))

    def cheapest(chosen, cat):
        return next((p for p in pool(cat) if not blocked(check_build(chosen + [p], final=False))), None)

    pools = {cat: pool(cat) for cat in ORDER if cat in required_cats}
    floor = {cat: items[0]['price'] if items else None for cat, items in pools.items()}
    if any(v is None for v in floor.values()):
        return None
    best = None
    for cpu in pools['cpu']:
        for board in pools['mainboard']:
            base = [cpu, board]
            # Cận dưới: CPU + mainboard + giá rẻ nhất của mỗi nhóm còn lại.
            bound = cpu['price'] + board['price'] + sum(v for c, v in floor.items() if c not in ('cpu', 'mainboard'))
            if (best is not None and bound >= best[0]) or blocked(check_build(base, final=False)):
                continue
            chosen = list(base)
            for cat in ('ram', 'ssd'):
                if cat in required_cats:
                    picked = cheapest(chosen, cat)
                    if picked is None:
                        break
                    chosen.append(picked)
            else:
                if 'gpu' in required_cats:
                    pair = None
                    for gpu in pools['gpu']:
                        if pair is not None and gpu['price'] + floor['psu'] >= pair[0]:
                            break
                        psu = cheapest(chosen + [gpu], 'psu') if not blocked(check_build(chosen + [gpu], final=False)) else None
                        if psu is not None and (pair is None or gpu['price'] + psu['price'] < pair[0]):
                            pair = (gpu['price'] + psu['price'], [gpu, psu])
                    if pair is None:
                        continue
                    chosen += pair[1]
                else:
                    psu = cheapest(chosen, 'psu')
                    if psu is None:
                        continue
                    chosen.append(psu)
                case = cheapest(chosen, 'case')
                if case is None:
                    continue
                chosen.append(case)
                total = sum(p['price'] for p in chosen)
                if best is None or total < best[0]:
                    best = (total, sorted(chosen, key=lambda p: ORDER.index(p['cat'])))
    return best[1] if best else None


def suggest_alternatives(sheet, usable, chosen, allocations, component_budget, group, required_cats):
    """Đề cương 1.2 và 4: thiếu linh kiện thì nêu phương án thay thế do backend tính, LLM không tự chọn."""
    have = {p['cat'] for p in chosen}
    missing_cats = [cat for cat in ORDER if cat in required_cats and cat not in have]
    if not missing_cats:
        return None
    brand = sheet.get('hang_cpu', 'tuy_shop')
    missing = []
    for cat in missing_cats:
        pool = [p for p in usable if p['cat'] == cat and not blocked(check_build(chosen + [p], final=False))]
        if cat == 'cpu' and group == 'office':
            pool = [p for p in pool if p['specs'].get('has_igpu') is True]
        same_brand = [p for p in pool if cat != 'cpu' or brand == 'tuy_shop' or fold(p.get('brand', '')) == brand]
        entry = {'cat': cat, 'allowance': allocations.get(cat, 0)}
        if same_brand:
            cheapest = min(same_brand, key=lambda p: (p['price'], p['id']))
            entry.update(reason='over_allowance', product=_brief(cheapest),
                         over_by=max(0, cheapest['price'] - allocations.get(cat, 0)))
        else:
            entry['reason'] = 'no_compatible_product'
        if cat == 'cpu' and brand != 'tuy_shop':
            # Không thiên vị hãng: nêu CPU hãng khác nằm trong hạn mức, nếu có.
            other = [p for p in pool if fold(p.get('brand', '')) != brand and p['price'] <= allocations.get(cat, 0)]
            if other:
                entry['other_brand'] = _brief(max(other, key=lambda p: (p['price'], p['id'])))
        missing.append(entry)
    result = {'missing': missing}
    build = cheapest_build(usable, group, required_cats, brand)
    if build is None and brand != 'tuy_shop':
        build = cheapest_build(usable, group, required_cats)
        result['brand_unavailable'] = build is not None
    if build is not None:
        total = sum(p['price'] for p in build)
        result.update(min_build_total=total, budget_shortfall=max(0, total - component_budget),
                      min_build=[_brief(p) for p in build])
    return result


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
        stock_cooler = cpu_chosen.get('specs', {}).get('stock_cooler') if cpu_chosen else None
        # Không rõ CPU có kèm tản thì máy chơi game/đồ họa vẫn dành tiền cho tản rời.
        need_cooler = cpu_chosen is not None and (stock_cooler is False or (stock_cooler is None and group != 'office'))
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
        candidates = [p for p in usable if p['cat'] == cat and p['price'] <= allowance and suits_group(p, group)]
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
        candidates.sort(key=lambda p: _sort_key(p, retrieved))
        picked = next((p for p in candidates if not blocked(check_build(chosen + [p], final=False))
                       and (cat in pinned or has_partner(chosen, p, usable))), None)
        if picked:
            chosen.append(picked)
        carry = max(0, base_allowance - (picked['price'] if picked else 0))
    pinned_ids = {p['id'] for p in pinned.values()}
    if any(not any(p['cat'] == cat for p in chosen) for cat in required_cats):
        chosen = complete(chosen, usable, group, required_cats, component_budget, pinned_ids,
                          sheet.get('hang_cpu', 'tuy_shop'))
    if all(any(p['cat'] == cat for p in chosen) for cat in required_cats):
        chosen = upgrade(chosen, usable, group, component_budget - sum(p['price'] for p in chosen), pinned_ids)
    chosen.sort(key=lambda p: ORDER.index(p['cat']))
    alternatives = suggest_alternatives(sheet, usable, chosen, allocations, component_budget, group, required_cats)
    # Ngân sách không đủ lắp bộ hoàn chỉnh: vẫn đề xuất bộ hoàn chỉnh rẻ nhất lắp được từ hàng đang có
    # (khách đã ghim linh kiện thì giữ bộ đang có để không bỏ linh kiện khách chọn).
    proposal = 'budget'
    if alternatives and alternatives.get('min_build') and not pinned:
        by_id = {p['id']: p for p in usable}
        chosen = [by_id[p['id']] for p in alternatives['min_build']]
        left = component_budget - sum(p['price'] for p in chosen)
        if left >= 0:  # lắp theo hạn mức bị hụt nhưng bộ rẻ nhất vẫn vừa: dùng phần dư nâng cấp
            chosen = upgrade(chosen, usable, group, left, pinned_ids)
            if not alternatives.get('brand_unavailable'):  # đổi hãng CPU thì giữ thông tin để báo khách
                alternatives = None
        else:  # vượt ngân sách: giữ đúng bộ có giá thấp nhất
            proposal = 'cheapest_complete'
    if license_product:
        chosen.append(license_product)
    checks = check_build(chosen)
    if group in ('gaming', 'creative') and not any(p['cat'] == 'gpu' for p in chosen):
        errors.append('Chưa chọn được GPU cho nhu cầu chơi game/đồ họa/video/AI.')
    if any(p['id'] not in {x['id'] for x in chosen} for p in pinned.values()):
        errors.append('Không giữ được tất cả linh kiện đã chọn trong giới hạn ngân sách và tương thích.')
    total = sum(p['price'] for p in chosen)
    over_budget = max(0, total + peripheral_reserve - budget)
    return {'products': chosen, 'checks': checks, 'total': total,
            'budget': budget, 'component_budget': component_budget,
            'peripheral_reserve': peripheral_reserve, 'allocations': allocations,
            'errors': errors, 'alternatives': alternatives, 'proposal': proposal, 'over_budget': over_budget,
            # Vượt ngân sách vẫn cho thêm vào giỏ khi đủ linh kiện và tương thích; over_budget báo rõ số tiền vượt.
            'can_add_to_cart': not errors and not blocked(checks)}
