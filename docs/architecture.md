# Kiến trúc phát triển

- Frontend: ReactJS, Vite và Ant Design (`src/`).
- Backend: Django API (`src/backend/`). Endpoint kiểm tra: `/api/health/`.
- Database: PostgreSQL 17.

## Cấu trúc thư mục

```text
src/                       # Mã nguồn frontend và backend
├── main.jsx               # Điểm khởi động, điều hướng và các trang cửa hàng
├── style.css              # Giao diện chung
├── admin/                 # Màn hình quản trị và CSS của admin
├── components/            # Chatbot, PC Builder, khuyến mãi; CSS đặt cạnh component
├── pages/                 # Trang đăng nhập, đăng ký
├── lib/                   # Hàm xử lý dùng chung, kiểm tra tương thích phía frontend
├── assets/                # Dữ liệu tĩnh như tỉnh/thành
└── backend/               # Backend Django
    ├── manage.py          # Lệnh quản lý Django
    ├── requirements.txt   # Thư viện Python
    ├── Dockerfile
    ├── config/            # Settings, URL gốc, WSGI, cấu hình test
    └── core/              # App nghiệp vụ
        ├── models.py      # Các bảng dữ liệu
        ├── urls.py        # Đường dẫn API
        ├── views.py       # API tài khoản, sản phẩm, đơn hàng
        ├── *_views.py     # API theo chức năng: chat, báo cáo, flash sale…
        ├── chat_service.py # Gọi Gemini và kiểm tra quy tắc tương thích
        ├── tests.py       # Test nghiệp vụ
        ├── test_chat.py   # Test chatbot
        └── migrations/    # Lịch sử thay đổi database

tests/                     # Test JavaScript
docs/                      # Đặc tả và hướng dẫn
public/                    # Ảnh và tài nguyên public
```

`src/backend/apps/core/` đã được rút gọn thành `src/backend/core/`. Python import dùng `core`, còn app label vẫn là `core`, nên tên bảng, quan hệ và lịch sử migration không đổi. Không cần xóa database hoặc tạo lại migrations khi chuyển cấu trúc này.

`migrations/` là lịch sử cấu trúc database của Django, cần giữ và đưa vào Git. Thư mục `__pycache__/` là cache Python tự sinh, đã được bỏ qua trong Git.

Khi sửa giao diện, làm việc trong `src/admin/`, `src/components/`, `src/pages/` và `src/main.jsx`; khi sửa API hoặc database, làm việc trong `src/backend/core/`. Cấu hình kết nối database và Gemini nằm trong `src/backend/config/settings.py`. Hướng dẫn chatbot: [Chatbot.md](Chatbot.md).

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

Nếu container đang chạy bằng cấu trúc cũ, chạy lại lệnh Compose với `--build` để cập nhật đường dẫn mount; giữ nguyên volume PostgreSQL.

## Kiểm tra sau khi sửa code

```bash
npm run build
node --test tests/compatibility.test.mjs
python -m pip install -r src/backend/requirements.txt
python src/backend/manage.py test core --settings=config.test_settings
python src/backend/manage.py makemigrations --check --dry-run --settings=config.test_settings
```

Test backend dùng SQLite tạm thời, không thay đổi PostgreSQL đang chạy.
