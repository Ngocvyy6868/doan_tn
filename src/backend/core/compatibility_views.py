from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CompatibilityRule
from .views import _payload


@csrf_exempt
def compatibility_rules(request, rule_id=None):
    if request.method == 'GET' and rule_id is None:
        return JsonResponse({'results': [model_to_dict(rule) for rule in CompatibilityRule.objects.order_by('id')]})
    rule = CompatibilityRule.objects.filter(pk=rule_id).first() if rule_id else None
    if rule_id and not rule:
        return JsonResponse({'message': 'Không tìm thấy ràng buộc.'}, status=404)
    if request.method == 'DELETE' and rule:
        rule.delete()
        return JsonResponse({'ok': True})
    if request.method not in ('POST', 'PATCH') or (request.method == 'PATCH' and not rule):
        return JsonResponse({'message': 'Method not allowed.'}, status=405)
    data = _payload(request)
    if not isinstance(data, dict):
        return JsonResponse({'message': 'Dữ liệu không hợp lệ.'}, status=400)
    values = model_to_dict(rule) if rule else {}
    fields = ('name', 'source_category', 'source_attribute', 'target_category', 'target_attribute', 'operator', 'active')
    values.update({key: data[key] for key in fields if key in data})
    values.pop('id', None)
    values.setdefault('active', True)
    for key in fields[:5]:
        value = values.get(key)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > (150 if key == 'name' else 100):
            return JsonResponse({'message': 'Nhập đầy đủ tên, danh mục và thuộc tính.'}, status=400)
        values[key] = value.strip()
    if values.get('operator') not in ('equal', 'overlap', 'gte', 'lte') or not isinstance(values['active'], bool) or values['source_category'] == values['target_category']:
        return JsonResponse({'message': 'Chọn phép so sánh hợp lệ và hai danh mục khác nhau.'}, status=400)
    if rule:
        for key, value in values.items():
            setattr(rule, key, value)
        rule.save()
    else:
        rule = CompatibilityRule.objects.create(**values)
    return JsonResponse({'rule': model_to_dict(rule)}, status=200 if rule_id else 201)
