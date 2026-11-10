from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Customer
from .views import _serialize_order, _serialize_account


@require_GET
def customer_orders(request, customer_id):
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({'message': 'Administrator access required.'}, status=403)
    customer = Customer.objects.filter(pk=customer_id).first()
    if customer is None:
        return JsonResponse({'message': 'Customer not found.'}, status=404)
    orders = customer.orders.select_related('handler').prefetch_related('items').order_by('-created_at', '-pk')
    return JsonResponse({'results': [_serialize_order(order) for order in orders]})


@require_GET
def admin_session(request):
    user = request.user
    return JsonResponse({'user': _serialize_account(user) if user.is_authenticated and user.is_staff else None})
