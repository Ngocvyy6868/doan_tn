# Kiến trúc phát triển

- Frontend: ReactJS, Vite và Ant Design (`src/`).
- Backend: Django REST-ready API (`src/backend/`). Endpoint kiểm tra: `/api/health/`.
- Database: PostgreSQL 17.

## Chạy môi trường phát triển

```bash
docker compose -f docker-compose.dev.yml up --build
```

Sau khi các container sẵn sàng:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000/api/health/
- Django Admin: http://localhost:8000/admin/

Tạo hoặc cập nhật các bảng Django:

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
```
