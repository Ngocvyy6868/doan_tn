# TechZone — Website thương mại điện tử linh kiện máy tính

Frontend React/Vite trong `src/`, backend Django trong `src/backend/`. Xem [cấu trúc dự án](docs/architecture.md) và [đặc tả](docs/Website_Thuong_Mai_Dien_Tu.md).

## Chạy dự án

Yêu cầu Node.js 20 trở lên.

```bash
npm install
npm run dev
```

Tạo bản production:

```bash
npm run build
npm run preview
```

## Chatbot theo đề cương ver2

Môi trường đầy đủ dùng `docker-compose.advisor.yml`: nginx, Django, PostgreSQL 16 + pgvector, Redis và Ollama. BGE-M3/reranker chạy CPU, Qwen3-4B chạy GPU. Cần điền cấu hình bí mật, tải model và nhúng catalog trước khi tư vấn. Xem [hướng dẫn chạy](docs/Chatbot.md), [kiến trúc](docs/architecture.md) và [ERD](docs/database-erd.md).

```bash
docker compose -f docker-compose.advisor.yml up -d --build
```

Compose dùng volume riêng; dữ liệu từ container cũ cần được chuyển có kiểm soát. Dockerfile gốc dưới đây phục vụ ứng dụng một container, không kèm embedding/reranker và Redis.

## Chạy bằng Docker

Một `Dockerfile` chạy React, Django/Gunicorn, Nginx và PostgreSQL trong cùng container. Không cần Docker Compose.

```bash
docker build -t techzone .
docker run -d --name techzone --restart unless-stopped -p 8080:80 -v techzone_data:/data techzone
```

Mở `http://localhost:8080`, trang quản trị tại `http://localhost:8080/admin`. Container tự khởi tạo database, chạy migration và thu thập static files. Volume `techzone_data` giữ database và khóa phiên đăng nhập qua các lần khởi động.

Tạo tài khoản quản trị lần đầu bằng lệnh tương tác:

```bash
docker exec -it techzone python manage.py createsuperuser
```

Có thể tạo tài khoản staff khi chạy lần đầu bằng `-e ADMIN_EMAIL=... -e ADMIN_PASSWORD=...`. Tài khoản đã tồn tại sẽ không bị đổi mật khẩu hay quyền. Cấu hình chatbot bằng `--env-file .env` hoặc `-e OLLAMA_BASE_URL=http://host.docker.internal:11434` khi chạy container. File `.env` không được đưa vào image.

```bash
docker logs -f techzone
docker stop techzone
docker start techzone
docker exec techzone python manage.py test core.test_customers --settings=config.test_settings
```

Nếu truy cập qua hostname khác, truyền `-e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,ten-may` và `-e CORS_ALLOWED_ORIGINS=http://ten-may:8080` phù hợp. Để đổi image sau khi sửa code, build lại, xóa container cũ bằng `docker rm -f techzone`, rồi chạy lại với cùng volume. Dữ liệu chỉ được giữ nếu dùng lại volume; không xóa volume khi muốn giữ dữ liệu.

## Tính năng demo

- Trang chủ responsive, danh mục và sản phẩm nổi bật
- Tìm kiếm, lọc theo danh mục, yêu thích sản phẩm
- Giỏ hàng, thay đổi số lượng và tính tổng tiền
- PC Builder với kiểm tra tương thích mô phỏng
- Chatbot Qwen3-4B + Django: phiếu nhu cầu, HyDE/truy xuất lai, chọn cấu hình theo ngân sách, luật R1–R14, lịch sử và thêm cả bộ vào giỏ ([cấu hình](docs/Chatbot.md))
- Giao diện tối ưu cho desktop, tablet và điện thoại
