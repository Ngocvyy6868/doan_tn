from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.advisor.catalog import adapt, fingerprint, search_text
from core.advisor.retrieval import embed
from core.models import Product


class Command(BaseCommand):
    help = 'Embed changed catalog descriptions locally with BGE-M3.'

    def handle(self, *args, **options):
        count = 0
        for product in Product.objects.select_related('category').iterator():
            data = adapt(product)
            digest = fingerprint(data, settings.ADVISOR_EMBEDDING_MODEL)
            if product.embedding_hash == digest and product.embedding is not None:
                continue
            try:
                vector = embed([search_text(data)])[0]
            except Exception as exc:
                raise CommandError('Không nạp/nhúng được model embedding cục bộ.') from exc
            # Do not attach old vectors if an admin edits the product during embedding.
            count += Product.objects.filter(pk=product.pk, updated_at=product.updated_at).update(
                embedding=vector, embedding_hash=digest)
        self.stdout.write(self.style.SUCCESS(f'Indexed {count} products.'))
