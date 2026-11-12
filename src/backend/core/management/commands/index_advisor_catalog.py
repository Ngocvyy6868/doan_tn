from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.advisor.catalog import adapt, fingerprint, search_text
from core.advisor.retrieval import embed
from core.models import Product

BATCH = 16


class Command(BaseCommand):
    help = 'Embed changed catalog descriptions locally with BGE-M3 (theo lô, chỉ sản phẩm đã đổi nội dung).'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Nhúng lại toàn bộ, kể cả sản phẩm không đổi.')

    def handle(self, *args, **options):
        pending = []
        for product in Product.objects.select_related('category').defer('embedding').iterator():
            data = adapt(product)
            digest = fingerprint(data, settings.ADVISOR_EMBEDDING_MODEL)
            if options['force'] or product.embedding_hash != digest:
                pending.append((product, data, digest))
        count = 0
        for start in range(0, len(pending), BATCH):
            batch = pending[start:start + BATCH]
            try:
                vectors = embed([search_text(data) for _, data, _ in batch])
            except Exception as exc:
                raise CommandError('Không nạp/nhúng được model embedding cục bộ.') from exc
            for (product, _, digest), vector in zip(batch, vectors):
                # Do not attach old vectors if an admin edits the product during embedding.
                count += Product.objects.filter(pk=product.pk, updated_at=product.updated_at).update(
                    embedding=vector, embedding_hash=digest)
            self.stdout.write(f'  {min(start + BATCH, len(pending))}/{len(pending)}')
        self.stdout.write(self.style.SUCCESS(f'Indexed {count} products.'))
