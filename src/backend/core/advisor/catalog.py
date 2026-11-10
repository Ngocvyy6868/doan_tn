"""Adapt the existing storefront catalog without duplicating prices or stock."""
import hashlib
import json
import math
import unicodedata


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value)).lower()
                   if unicodedata.category(c) != 'Mn').replace('đ', 'd').strip()


CATEGORIES = {
    'cpu': 'cpu', 'mainboard': 'mainboard', 'ram': 'ram', 'vga': 'gpu', 'gpu': 'gpu',
    'ssd': 'ssd', 'hdd': 'hdd', 'nguon': 'psu', 'psu': 'psu', 'case': 'case',
    'tan nhiet': 'cooler', 'cooler': 'cooler', 'ban quyen': 'license', 'license': 'license',
}
ALIASES = {
    'socket': 'socket', 'tdp': 'tdp_w', 'cong suat': 'watt',
    'the he ram': 'ram_type', 'the he ram ho tro': 'ram_type',
    'so khe ram': 'ram_slots', 'dung luong ram toi da': 'max_ram_gb',
    'dung luong': 'capacity_gb', 'so thanh ram': 'modules',
    'so khe m.2': 'm2_slots', 'kich thuoc': 'form_factor',
    'kich thuoc ho tro': 'supported_mb', 'chieu dai': 'length_mm',
    'chieu dai vga toi da': 'max_gpu_length_mm',
    'chieu cao tan nhiet toi da': 'max_cooler_height_mm',
    'chieu cao': 'height_mm', 'socket ho tro': 'sockets', 'giao tiep': 'interface',
}


def category(value):
    return CATEGORIES.get(fold(value), fold(value))


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (ValueError, TypeError):
        return None


def adapt(product):
    p = product.payload
    cat = category(p.get('product_type') or (product.category.name if product.category else p.get('cat', '')))
    specs = {}
    for attribute in p.get('attributes', []):
        key = ALIASES.get(fold(attribute.get('name', '')))
        if key:
            specs[key] = attribute.get('value')
    if cat in ('cpu', 'gpu', 'cooler') and 'watt' in specs:
        specs.setdefault('tdp_w', specs.pop('watt'))
    # Explicit canonical specs take precedence; never infer technical facts from model names.
    specs.update(p.get('specs', {}) if isinstance(p.get('specs'), dict) else {})
    price, stock = number(p.get('price')), number(p.get('stock'))
    public = {k: p[k] for k in ('name', 'brand', 'sku', 'img', 'description', 'attributes', 'active') if k in p}
    return {**public, 'id': product.external_id, 'cat': cat, 'specs': specs,
            'price': int(price) if price is not None and price.is_integer() else None,
            'stock': int(stock) if stock is not None and stock.is_integer() else None}


def available(p):
    return (p.get('active') is not False and number(p.get('stock')) is not None
            and number(p['stock']) >= 1 and number(p.get('price')) is not None
            and number(p['price']) > 0)


def search_text(p):
    return json.dumps({k: p.get(k) for k in ('name', 'brand', 'cat', 'specs', 'description')},
                      ensure_ascii=False, sort_keys=True)


def fingerprint(p, model):
    return hashlib.sha256((model + '\n' + search_text(p)).encode()).hexdigest()
