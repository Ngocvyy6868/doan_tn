# TechZone — Website thương mại điện tử linh kiện máy tính

Frontend React/Vite được xây dựng theo đặc tả `Resources/Website_Thuong_Mai_Dien_Tu.md`.

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

## Chạy bằng Docker

```bash
docker compose up --build -d
```

Mở `http://localhost:8080`. Xem log hoặc dừng dịch vụ bằng:

```bash
docker compose logs -f
docker compose down
```

## Tính năng demo

- Trang chủ responsive, danh mục và sản phẩm nổi bật
- Tìm kiếm, lọc theo danh mục, yêu thích sản phẩm
- Giỏ hàng, thay đổi số lượng và tính tổng tiền
- PC Builder với kiểm tra tương thích mô phỏng
- Chatbot AI dạng cửa sổ hội thoại
- Giao diện tối ưu cho desktop, tablet và điện thoại
