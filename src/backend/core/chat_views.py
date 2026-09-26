import json

from django.core.cache import cache
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods

from .chat_service import ChatUnavailable, advise
from .models import CompatibilityRule, Product


@require_http_methods(['GET', 'POST', 'DELETE'])
def chat(request):
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Vui lòng đăng nhập để dùng chatbot.'}, status=401)
    if request.method == 'GET':
        return JsonResponse({'csrf_token': get_token(request), 'history': request.session.get('chat_history', [])})
    if request.method == 'DELETE':
        request.session.pop('chat_history', None)
        return JsonResponse({'ok': True})
    if len(request.body) > 12000:
        return JsonResponse({'message': 'Nội dung quá dài.'}, status=400)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        data = None
    if not isinstance(data, dict) or not isinstance(data.get('message'), str) or not 1 <= len(data['message'].strip()) <= 2000:
        return JsonResponse({'message': 'Câu hỏi cần từ 1 đến 2000 ký tự.'}, status=400)
    selected = data.get('product_ids', [])
    if not isinstance(selected, list) or len(selected) > 10 or any(not isinstance(i, str) or len(i) > 64 for i in selected):
        return JsonResponse({'message': 'Danh sách sản phẩm không hợp lệ.'}, status=400)
    key = f'chat-rate:{request.user.pk}'
    cache.add(key, 0, timeout=60)
    if cache.incr(key) > 5:
        return JsonResponse({'message': 'Bạn gửi quá nhanh. Vui lòng chờ một phút.'}, status=429)
    catalog = []
    for product in Product.objects.select_related('category').order_by('id')[:500]:
        p = product.payload
        if p.get('active') is False or p.get('stock') == 0:
            continue
        catalog.append({'id': product.external_id, 'name': p.get('name', ''),
                        'cat': product.category.name if product.category else p.get('cat', ''),
                        'price': p.get('price'), 'stock': p.get('stock'),
                        'attributes': p.get('attributes', [])})
    if any(i not in {p['id'] for p in catalog} for i in selected):
        return JsonResponse({'message': 'Sản phẩm đã chọn không còn khả dụng trong danh mục tư vấn.'}, status=400)
    if not catalog:
        return JsonResponse({'answer': 'Chưa có sản phẩm khả dụng trong database để tư vấn. Vui lòng liên hệ cửa hàng.', 'products': [], 'checks': []})
    history = request.session.get('chat_history', [])[-12:]
    try:
        result = advise(data['message'].strip(), history, catalog,
                        list(CompatibilityRule.objects.filter(active=True).values()), selected)
    except ChatUnavailable as exc:
        return JsonResponse({'message': str(exc)}, status=503)
    request.session['chat_history'] = (history + [
        {'role': 'user', 'text': data['message'].strip()},
        {'role': 'assistant', 'text': result['answer']}])[-12:]
    return JsonResponse(result)
