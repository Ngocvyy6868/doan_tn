"""CDP: ghi sự kiện lên dòng thời gian khách hàng. Ghi lỗi không được làm hỏng nghiệp vụ chính."""
import logging

from .models import Customer, CustomerEvent

logger = logging.getLogger(__name__)
Type, Source = CustomerEvent.Type, CustomerEvent.Source


def customer_of(user):
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    return Customer.objects.filter(user=user).first()


def record(customer, type, data=None, actor=None, source=None, title=None, created_at=None):
    """Thêm một sự kiện; source mặc định: nhân viên nếu actor là staff, ngược lại là khách hàng."""
    if customer is None:
        return None
    if source is None:
        source = Source.STAFF if actor is not None and actor.is_staff and actor != customer.user else Source.CUSTOMER
    fields = dict(customer=customer, type=type, source=source, title=(title or Type(type).label)[:255],
                  data=data or {}, actor=actor if getattr(actor, 'is_authenticated', False) else None)
    if created_at is not None:
        fields['created_at'] = created_at
    try:
        return CustomerEvent.objects.create(**fields)
    except Exception:  # pragma: no cover - chỉ phòng lỗi DB bất thường
        logger.exception('Không ghi được sự kiện khách hàng %s', type)
        return None


def address_text(address):
    return ', '.join(p for p in (address.detail, address.ward_name, address.province_name) if p)
