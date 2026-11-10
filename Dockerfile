# syntax=docker/dockerfile:1
# Build: docker build -t techzone .
# Run: docker run -d --name techzone -p 8080:80 -v techzone_data:/data techzone
#
# Image một container này chỉ chạy cửa hàng (web + API + PostgreSQL), KHÔNG có chatbot tư vấn:
# không có Ollama, Redis, BGE-M3/reranker. Gửi tin nhắn tới /api/chat/ sẽ nhận HTTP 503.
# Chạy đầy đủ chatbot: docker compose -f docker-compose.advisor.yml up -d (xem docs/Chatbot.md).
FROM node:24-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.mjs ./
COPY public ./public
COPY src ./src
ENV VITE_API_BASE_URL=/api
RUN npm run build

FROM python:3.13-slim-bookworm AS vector-build
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential postgresql-server-dev-15 \
    && git clone --depth 1 --branch v0.8.2 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector && make && make install

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.docker_settings \
    DJANGO_DEBUG=false \
    DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
    CORS_ALLOWED_ORIGINS=http://localhost:8080 \
    POSTGRES_DB=techzone \
    POSTGRES_USER=techzone \
    POSTGRES_HOST=127.0.0.1 \
    POSTGRES_PORT=5432 \
    PGDATA=/data/postgres
RUN apt-get update && apt-get install -y --no-install-recommends nginx postgresql supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/lib/postgresql/*/bin/initdb /usr/local/bin/initdb \
    && ln -s /usr/lib/postgresql/*/bin/pg_ctl /usr/local/bin/pg_ctl \
    && ln -s /usr/lib/postgresql/*/bin/postgres /usr/local/bin/postgres
COPY --from=vector-build /usr/lib/postgresql/15/lib/vector.so /usr/lib/postgresql/15/lib/vector.so
COPY --from=vector-build /usr/share/postgresql/15/extension/vector* /usr/share/postgresql/15/extension/
WORKDIR /app
COPY src/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY src/backend/config ./config
COPY src/backend/core ./core
COPY src/backend/manage.py ./
COPY --from=frontend /build/dist /usr/share/nginx/html

RUN <<'SETUP'
set -eu
cat > /app/config/docker_settings.py <<'PY'
from .settings import *
STATIC_ROOT = '/app/staticfiles'
# Also support manage.py commands invoked through docker exec.
from pathlib import Path
if not os.environ.get('DJANGO_SECRET_KEY') and Path('/data/django-secret').exists():
    SECRET_KEY = Path('/data/django-secret').read_text().strip()
if not os.environ.get('POSTGRES_PASSWORD') and Path('/data/database-password').exists():
    DATABASES['default']['PASSWORD'] = Path('/data/database-password').read_text().strip()
PY
cat > /etc/nginx/nginx.conf <<'NGINX'
user www-data;
worker_processes auto;
pid /run/nginx.pid;
error_log /dev/stderr warn;
events { worker_connections 1024; }
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    access_log /dev/stdout;
    sendfile on;
    server {
        listen 80;
        root /usr/share/nginx/html;
        index index.html;
        client_max_body_size 10m;
        location /api/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        location /static/ { alias /app/staticfiles/; }
        location / { try_files $uri $uri/ /index.html; }
        add_header X-Content-Type-Options nosniff always;
        add_header X-Frame-Options SAMEORIGIN always;
    }
}
NGINX
cat > /etc/supervisor/techzone.conf <<'SUPERVISOR'
[supervisord]
user=root
nodaemon=true
logfile=/dev/null
pidfile=/run/supervisord.pid
[program:postgres]
command=/usr/local/bin/postgres -D /data/postgres -c listen_addresses=127.0.0.1
user=postgres
autorestart=true
stopsignal=INT
stopwaitsecs=30
priority=10
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
[program:backend]
command=gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 120 --access-logfile - --error-logfile -
directory=/app
user=www-data
environment=HOME="/tmp"
autorestart=true
stopasgroup=true
killasgroup=true
priority=20
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
[program:nginx]
command=nginx -g "daemon off;"
autorestart=true
priority=30
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
SUPERVISOR
cat > /app/bootstrap.py <<'PY'
import os
import psycopg
from psycopg import sql

with psycopg.connect('dbname=postgres user=postgres host=/var/run/postgresql', autocommit=True) as connection:
    role, database = os.environ['POSTGRES_USER'], os.environ['POSTGRES_DB']
    password = os.environ['POSTGRES_PASSWORD']
    if not connection.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone():
        connection.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role), sql.Literal(password)))
    else:
        connection.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(role), sql.Literal(password)))
    if not connection.execute('SELECT 1 FROM pg_database WHERE datname=%s', (database,)).fetchone():
        connection.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(database), sql.Identifier(role)))
PY
cat > /app/entrypoint.sh <<'SH'
#!/bin/sh
set -eu
mkdir -p "$PGDATA" /run/postgresql
chown postgres:postgres "$PGDATA" /run/postgresql
chmod 700 "$PGDATA"
# Persist generated credentials with the database, without baking them into the image.
if [ ! -s /data/django-secret ]; then
    python -c 'import secrets; print(secrets.token_urlsafe(48))' > /data/django-secret
fi
if [ ! -s /data/database-password ]; then
    python -c 'import secrets; print(secrets.token_urlsafe(32))' > /data/database-password
fi
chmod 600 /data/django-secret /data/database-password
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-$(cat /data/django-secret)}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(cat /data/database-password)}"
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    runuser -u postgres -- initdb -D "$PGDATA" --auth-local=peer --auth-host=scram-sha-256
fi
runuser -u postgres -- pg_ctl -D "$PGDATA" -l /data/postgres/startup.log -o '-c listen_addresses=127.0.0.1' -w start
trap 'runuser -u postgres -- pg_ctl -D "$PGDATA" -m fast -w stop || true' EXIT
runuser -u postgres --preserve-environment -- python /app/bootstrap.py
python manage.py migrate --noinput
python manage.py collectstatic --noinput
# Optional local admin provisioning; existing accounts and passwords are preserved.
python - <<'PY'
import os
import django
django.setup()
from django.contrib.auth.models import User
email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
password = os.environ.get('ADMIN_PASSWORD', '')
if email and password:
    if not User.objects.filter(username=email).exists():
        User.objects.create_user(username=email, email=email, password=password, is_staff=True)
        print('Created local admin:', email)
    else:
        print('Admin username already exists; account unchanged.')
PY
runuser -u postgres -- pg_ctl -D "$PGDATA" -m fast -w stop
trap - EXIT
exec supervisord -c /etc/supervisor/techzone.conf
SH
chmod +x /app/entrypoint.sh
SETUP

VOLUME ["/data"]
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1/api/health/', timeout=3)" || exit 1
ENTRYPOINT ["/app/entrypoint.sh"]
