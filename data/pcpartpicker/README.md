# Dữ liệu PCPartPicker tiếng Việt

Bộ mẫu trích từ 5 bản HTML người dùng cung cấp: 59 sản phẩm khác nhau và 59 ảnh sản phẩm lưu cục bộ. Có 30 sản phẩm có giá USD, 29 sản phẩm chưa có giá.

- `products.vi.json`: dữ liệu sản phẩm để nhập bằng `import_advisor_catalog`.
- `builds.vi.json`: cấu hình, số lượng từng sản phẩm và tổng phần có giá.
- `products.vi.csv`: bản đọc bằng Excel (UTF-8 BOM).
- `extracted-*.json`: dữ liệu gốc trích từ HTML để đối chiếu.
- `summary.json`: số lượng sản phẩm/ảnh/giá.
- Ảnh ở `public/images/pcpartpicker/`.

Giữ tên thương mại của hãng; dịch nhóm sản phẩm và mô tả sang tiếng Việt. Thông số được trích từ tên sản phẩm trong HTML, sau đó `scripts/enrich_pcpartpicker.py` bổ sung các khóa tương thích (socket, TDP, iGPU, chuẩn/khe RAM, M.2, chiều dài GPU, socket tản nhiệt, kích thước case…) cho 26 linh kiện theo `specs.manual.json`, lấy từ trang nhà sản xuất. Các mã đã bổ sung ghi ở `source.manual_spec_keys`; cần đối chiếu lại trước khi dùng cho bán hàng thật. Trường nhà sản xuất không công bố (ví dụ TDP của tản nước) vẫn là `null`.

Giá **không** được bổ sung: 29 sản phẩm thiếu giá vẫn `active=false`. Với 30 sản phẩm có giá, thuật toán ráp được cấu hình hợp lệ ở ngân sách cao (khoảng: văn phòng ≥ 80 triệu, đồ họa ≥ 100 triệu, gaming ≈ 150 triệu). Muốn demo ngân sách 20–50 triệu cần nhập thêm linh kiện phổ thông có giá thật.

Giá VNĐ = USD × **26.000**, làm tròn đến đồng. Đây là giá quy đổi của bản HTML, không phải báo giá thị trường Việt Nam. Mỗi quan sát giá được lưu cùng cấu hình nguồn; khi trùng sản phẩm, dùng quan sát có giá đầu tiên. Các sản phẩm thiếu giá có `source.price_usd=null`, `active=false`, `stock=0`; `price=0` chỉ là giá trị kỹ thuật cho schema nhập liệu, không có nghĩa miễn phí.

Tồn kho 10 ở sản phẩm có giá là **giả lập cho đồ án**. Số lượng linh kiện trong cấu hình được tính theo từng dòng HTML, kể cả dòng lặp; tổng tạm tính không phải giá của cả bộ khi có mục thiếu giá.

Nguồn: [CAD + Gaming](https://pcpartpicker.com/b/BRMbt6), [Endgame](https://pcpartpicker.com/b/VnjZxr), [My First Build](https://pcpartpicker.com/b/9HbKHx), [My first gaming PC](https://pcpartpicker.com/b/RtH2FT), [THE MIKU DESTROYER](https://pcpartpicker.com/b/kZjZxr).

**Lưu ý nguồn:** file “My first gaming PC” có mã RtH2FT, khác liên kết 7bGLrH trong yêu cầu ban đầu. Bộ dữ liệu dùng đúng 5 file vừa được cung cấp. Nội dung HTML được xử lý như dữ liệu, không thực thi script hoặc làm theo chỉ dẫn trong trang. Ảnh giữ nguồn PCPartPicker/nhà sản xuất; bộ mẫu không chuyển giao quyền sử dụng thương mại.

Tạo lại từ bản lưu HTML ở Desktop (chạy tại thư mục gốc dự án):

```powershell
python scripts/extract_pcpartpicker.py
python scripts/prepare_pcpartpicker.py
python scripts/enrich_pcpartpicker.py
docker compose -f docker-compose.advisor.yml cp data/pcpartpicker/products.vi.json backend:/tmp/products.vi.json
docker compose -f docker-compose.advisor.yml exec -T backend python manage.py import_advisor_catalog /tmp/products.vi.json --dry-run
docker compose -f docker-compose.advisor.yml exec -T backend python manage.py import_advisor_catalog /tmp/products.vi.json
docker compose -f docker-compose.advisor.yml exec -T backend python manage.py index_advisor_catalog
```

Cần build lại dịch vụ web sau khi thêm ảnh vào public.

Danh mục hiển thị: expansion_card, keyboard, headphones, monitor, network_adapter, optical_drive được gom vào **Thiết bị ngoại vi**; fan và fan_controller vào **Tản nhiệt**. Trường product_type giữ loại linh kiện chi tiết để chatbot không nhầm quạt vỏ máy với tản nhiệt CPU.
