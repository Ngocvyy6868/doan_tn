"""CDP: dựng lại sự kiện từ dữ liệu có sẵn (đăng ký, đặt đơn, trò chuyện với trợ lý AI) cho dòng thời gian."""
from django.db import migrations


def backfill(apps, schema_editor):
    Customer = apps.get_model('core', 'Customer')
    CustomerEvent = apps.get_model('core', 'CustomerEvent')
    Order = apps.get_model('core', 'Order')
    ChatSession = apps.get_model('core', 'ChatSession')
    events = []
    for customer in Customer.objects.select_related('user'):
        if not CustomerEvent.objects.filter(customer=customer, type='REGISTERED').exists():
            events.append(CustomerEvent(customer=customer, type='REGISTERED', source='customer',
                                        title='Đăng ký tài khoản', created_at=customer.created_at,
                                        data={'email': customer.user.email, 'phone': customer.phone}))
        for session in ChatSession.objects.filter(user=customer.user).order_by('created_at'):
            first = session.messages.filter(role='user').order_by('id').first()
            events.append(CustomerEvent(customer=customer, type='CHAT_STARTED', source='customer',
                                        title='Trò chuyện với trợ lý AI', created_at=session.created_at,
                                        data={'session_id': session.pk, 'message': first.text[:300] if first else ''}))
    for order in Order.objects.filter(customer__isnull=False).prefetch_related('items'):
        events.append(CustomerEvent(
            customer_id=order.customer_id, type='ORDER_PLACED', source='customer', created_at=order.created_at,
            title=f'Đặt đơn hàng {order.code}',
            data={'order_id': order.id, 'code': order.code, 'grand_total': order.grand_total,
                  'payment_method': order.payment_method, 'status': order.status,
                  'items': [{'name': i.name, 'quantity': i.quantity} for i in order.items.all()][:20]}))
    CustomerEvent.objects.bulk_create(events)


def unbackfill(apps, schema_editor):
    apps.get_model('core', 'CustomerEvent').objects.filter(type__in=['REGISTERED', 'CHAT_STARTED', 'ORDER_PLACED']).delete()


class Migration(migrations.Migration):
    dependencies = [('core', '0020_customer_crm')]

    operations = [migrations.RunPython(backfill, unbackfill)]
