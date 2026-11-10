# syntax=docker/dockerfile:1
FROM node:24-alpine AS frontend-build
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.mjs ./
COPY public ./public
COPY src ./src
ENV VITE_API_BASE_URL=/api
RUN npm run build

FROM nginx:stable-alpine AS web
COPY --from=frontend-build /build/dist /usr/share/nginx/html
COPY docker/advisor/nginx.conf /etc/nginx/conf.d/default.conf

FROM python:3.13-slim-bookworm AS backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/models/huggingface
WORKDIR /app
COPY src/backend/requirements.txt src/backend/requirements-advisor.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn
# CPU-only embedding and reranker leave GPU memory for Qwen.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements-advisor.txt
COPY src/backend ./
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 2 --timeout 150 --access-logfile -"]
