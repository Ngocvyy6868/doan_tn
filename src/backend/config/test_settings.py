"""Isolated SQLite settings for backend tests without a running PostgreSQL server."""
from .settings import *  # noqa: F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
ADVISOR_RETRIEVAL = 'lexical'
ADVISOR_HYDE = False
ADVISOR_RERANK = False
