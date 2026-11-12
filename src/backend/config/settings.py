import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'unsafe-development-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'corsheaders', 'core',
]
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', 'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True,
              'OPTIONS': {'context_processors': ['django.template.context_processors.request',
              'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql',
    'NAME': os.getenv('POSTGRES_DB', 'techzone'), 'USER': os.getenv('POSTGRES_USER', 'techzone'),
    'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'techzone'), 'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
    'PORT': os.getenv('POSTGRES_PORT', '5432')}}
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173').split(',')
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3:4b')


# Shared cache and advisory state in production; local cache is for standalone development.
REDIS_URL = os.getenv('REDIS_URL', '')
if REDIS_URL:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                         'LOCATION': REDIS_URL}}
ADVISOR_EMBEDDING_MODEL = os.getenv('ADVISOR_EMBEDDING_MODEL', 'BAAI/bge-m3')
ADVISOR_RERANKER_MODEL = os.getenv('ADVISOR_RERANKER_MODEL', 'BAAI/bge-reranker-v2-m3')
ADVISOR_MODELS_OFFLINE = os.getenv('ADVISOR_MODELS_OFFLINE', 'true').lower() == 'true'
ADVISOR_HYDE = os.getenv('ADVISOR_HYDE', 'true').lower() == 'true'
ADVISOR_RERANK = os.getenv('ADVISOR_RERANK', 'true').lower() == 'true'
ADVISOR_RETRIEVAL = os.getenv('ADVISOR_RETRIEVAL', 'hybrid')
# 'pgvector' (production, 1024-dim HNSW) or 'memory' (exact search, any dimension; TN3 baselines).
ADVISOR_VECTOR_STORE = os.getenv('ADVISOR_VECTOR_STORE', 'pgvector')
# 'combined' = average of question and HyDE vectors (đề cương 3.1); 'only' = HyDE vector alone (TN2).
ADVISOR_HYDE_MODE = os.getenv('ADVISOR_HYDE_MODE', 'combined')
# Số sản phẩm đầu kết quả truy xuất mỗi nhóm được ưu tiên trước khi xét giá cao nhất (đề cương 3.3.3).
ADVISOR_ASSEMBLY_TOP_K = int(os.getenv('ADVISOR_ASSEMBLY_TOP_K', '5'))
# Nạp sẵn embedding/reranker khi gunicorn khởi động (bật trong docker-compose.advisor.yml).
ADVISOR_WARMUP = os.getenv('ADVISOR_WARMUP', 'false').lower() == 'true'
ADVISOR_LLM_TIMEOUT =int(os.getenv('ADVISOR_LLM_TIMEOUT', '30'))

STATIC_ROOT = BASE_DIR / 'staticfiles'
