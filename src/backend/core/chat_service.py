"""Ground Qwen3-4B responses in the catalog and deterministic compatibility checks."""
import math
import re

from django.conf import settings


class ChatUnavailable(Exception):
    pass


from .advisor.llm import generate


def normalize(value):
    return str(value if value is not None else '').strip().lower()


def tokens(value):
    return [normalize(v) for v in (value if isinstance(value, list) else re.split('[,;\n]', str(value or ''))) if normalize(v)]


def attribute(product, name):
    return next((a for a in product.get('attributes', []) if normalize(a.get('name')) == normalize(name)), {})


def check_compatibility(products, rules):
    checks = []
    for rule in rules:
        if not rule['active']:
            continue
        sources = [p for p in products if p['cat'] == rule['source_category']]
        targets = [p for p in products if p['cat'] == rule['target_category']]
        for source in sources:
            for target in targets:
                left, right = attribute(source, rule['source_attribute']), attribute(target, rule['target_attribute'])
                status, message = 'unknown', 'Thiếu thông số để kiểm tra.'
                if tokens(left.get('value')) and tokens(right.get('value')):
                    a, b, op = left['value'], right['value'], rule['operator']
                    valid = None
                    if op == 'equal':
                        valid = normalize(a) == normalize(b)
                    elif op == 'overlap':
                        valid = bool(set(tokens(a)) & set(tokens(b)))
                    elif op in ('gte', 'lte'):
                        try:
                            x, y = float(a), float(b)
                            if math.isfinite(x) and math.isfinite(y) and normalize(left.get('unit')) == normalize(right.get('unit')):
                                valid = x >= y if op == 'gte' else x <= y
                        except (ValueError, TypeError):
                            pass
                    status = 'unknown' if valid is None else ('pass' if valid else 'fail')
                    message = f"{rule['source_attribute']}: {a} {left.get('unit', '')} / {rule['target_attribute']}: {b} {right.get('unit', '')}"
                checks.append({'rule': rule['name'], 'pair': f"{source['name']} / {target['name']}", 'status': status, 'message': message})
    return checks



def advise(message, history, catalog, rules, selected_ids):
    from .advisor.pipeline import respond
    result, _ = respond(message, history, catalog, selected_ids, {}, generate)
    return result
