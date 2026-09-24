# Chatbot Gemini + Django

Luồng: React → `GET /api/chat/` lấy CSRF token và lịch sử → `POST /api/chat/` → Django đọc Product và CompatibilityRule → Gemini chọn ID sản phẩm → Django xác minh ID, chạy rules → Gemini diễn giải kết quả → React hiển thị câu trả lời, sản phẩm và kết quả kiểm tra riêng.

## Chạy

1. Sao chép `.env.example` thành `.env`, điền `GEMINI_API_KEY` từ Google AI Studio. Không dùng tiền tố `VITE_` cho khóa này.
2. Có thể đổi `GEMINI_MODEL` theo model tài khoản của bạn được cấp quyền sử dụng. Free Tier phụ thuộc model và hạn mức tài khoản, không phải tùy chọn bật trong code.
3. Chạy `docker compose -f docker-compose.dev.yml up --build -d`.
4. Chạy `docker compose -f docker-compose.dev.yml exec backend python manage.py migrate`.
5. Lưu sản phẩm trong trang quản trị để có dữ liệu Product trên backend; dữ liệu mẫu/localStorage trên frontend không tự trở thành nguồn của chatbot.
6. Đăng nhập tại `http://localhost:5173`, mở **Hỏi AI** và nhập nhu cầu/ngân sách. Trên trang chi tiết, ID sản phẩm được gửi kèm để kiểm tra.

Nếu chạy Django trực tiếp, cần đặt biến môi trường GEMINI_API_KEY/GEMINI_MODEL trong shell trước `python manage.py runserver`; Django không tự đọc `.env`. Docker Compose bản thường chỉ chạy storefront; dùng bản dev ở trên để có backend và database.

## Hành vi

- Yêu cầu phiên đăng nhập và CSRF token cho POST/DELETE; lưu tối đa 12 tin nhắn gần nhất trong phiên Django.
- Chỉ dùng tối đa 500 bản ghi sản phẩm đầu tiên; bỏ sản phẩm ngừng bán/hết hàng. Không tự tạo sản phẩm từ câu trả lời AI.
- Rules hỗ trợ `equal`, `overlap`, `gte`, `lte`. Thiếu thông số/khác đơn vị là `unknown`. Không có rule áp dụng không đồng nghĩa tương thích toàn bộ. Chưa kiểm tra tổng công suất PSU trong chatbot.
- Hai lần gọi Gemini mỗi lượt: chọn sản phẩm và diễn giải kết quả. Giới hạn 5 yêu cầu/phút/tài khoản, timeout 30 giây mỗi lần gọi, không tự retry khi hết quota.
- Rate limit dùng cache mặc định trong từng process; khi chạy nhiều worker cần cấu hình cache dùng chung như Redis.
- Không gửi thông tin tài khoản cho Gemini. Câu hỏi, lịch sử gần nhất và thông số/giá sản phẩm được gửi đến API Google. Nội dung AI là tư vấn; kết quả rule và thẻ sản phẩm do backend trả riêng.
- Đây là luồng dùng catalog trực tiếp; chưa triển khai vector search, RAG–HyDE hoặc chuyển nhân viên.

API POST nhận `{"message":"Tư vấn PC 25 triệu", "product_ids":[]}` và trả `answer`, `products`, `checks`. DELETE xóa lịch sử phiên. 401: chưa đăng nhập; 400: dữ liệu sai; 403: CSRF; 429: gửi quá nhanh; 503: cấu hình/dịch vụ Gemini chưa khả dụng.

## Kiểm thử

`python src/backend/manage.py test core.test_chat --settings=config.test_settings`

Tests dùng SQLite và mock Gemini, không cần API key. Tài liệu REST Gemini: https://ai.google.dev/api/generate-content
