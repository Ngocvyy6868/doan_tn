from django.conf import settings
from django.core.management.base import BaseCommand

MINILM = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'


class Command(BaseCommand):
    help = 'One-time download of embedding/reranker weights; runtime remains offline.'

    def add_arguments(self, parser):
        parser.add_argument('--baseline', action='store_true',
                            help='Tải thêm MiniLM-L12-v2 làm mốc so sánh cho TN3.')

    def handle(self, *args, **options):
        from sentence_transformers import SentenceTransformer, CrossEncoder
        SentenceTransformer(settings.ADVISOR_EMBEDDING_MODEL, device='cpu')
        CrossEncoder(settings.ADVISOR_RERANKER_MODEL, device='cpu')
        if options['baseline']:
            SentenceTransformer(MINILM, device='cpu')
        self.stdout.write(self.style.SUCCESS('Models cached. Restart backend in offline mode.'))
