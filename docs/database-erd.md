# Sơ đồ cơ sở dữ liệu TechZone

Sơ đồ được cập nhật theo migration `0015_advisor_architecture` và đề cương chatbot ver2.

Sơ đồ dựa trên `src/backend/core/models.py` và cấu hình Django hiện tại, không phải kết quả kiểm tra database đang chạy. Bao gồm 14 bảng nghiệp vụ và bảng tài khoản `auth_user`. Các bảng hệ thống khác của Django (session, quyền, nhóm, migration, admin log) được lược bỏ; `auth_user` chỉ hiển thị các trường chính.

PK: khóa chính; FK: khóa ngoại; UK: duy nhất. Tất cả bảng nghiệp vụ có khóa chính `id` kiểu bigint do Django tự tạo. Kiểu dữ liệu dưới đây tương ứng PostgreSQL.

## Quan hệ có khóa ngoại

```mermaid
erDiagram
    auth_user ||..o| core_customer : "hồ sơ khách hàng"
    auth_user ||..o| core_employee : "hồ sơ nhân viên"
    auth_user |o..o{ core_order : "handler_id: xử lý đơn"
    core_customer ||..o{ core_address : "sở hữu"
    core_customer |o..o{ core_order : "đặt hàng"
    core_category |o..o{ core_product : "phân loại"
    core_order ||..o{ core_orderitem : "chi tiết đơn"
    auth_user ||..o{ core_chatsession : "hội thoại tư vấn"
    core_chatsession ||..o{ core_chatmessage : "tin nhắn và kết quả"

    core_chatsession {
        bigint id PK
        integer user_id FK
        jsonb state "phiếu nhu cầu, số lần hỏi, giả định"
        boolean active
        timestamptz created_at
        timestamptz updated_at
    }
    core_chatmessage {
        bigint id PK
        bigint session_id FK
        varchar role
        text text
        jsonb data "cấu hình, checks, trace truy xuất"
        integer latency_ms
        timestamptz created_at
    }

    auth_user {
        integer id PK
        varchar username UK
        varchar password
        varchar email
        boolean is_active
        boolean is_staff
        boolean is_superuser
    }
    core_customer {
        bigint id PK
        integer user_id FK,UK
        varchar full_name
        varchar phone UK
        varchar avatar_url
        timestamptz created_at
        timestamptz updated_at
    }
    core_employee {
        bigint id PK
        integer user_id FK,UK
        varchar role
        varchar full_name
        varchar phone UK
        boolean active
        timestamptz created_at
    }
    core_address {
        bigint id PK
        bigint customer_id FK
        varchar full_name
        varchar phone
        varchar province_code
        varchar province_name
        varchar ward_code
        varchar ward_name
        varchar detail
        boolean is_default
        timestamptz created_at
        timestamptz updated_at
    }
    core_category {
        bigint id PK
        varchar name UK
        timestamptz created_at
    }
    core_product {
        bigint id PK
        varchar external_id UK
        bigint category_id FK "nullable"
        jsonb payload "giá, tồn, specs, mô tả; nguồn dữ liệu duy nhất"
        vector embedding "1024 chiều BGE-M3, nullable"
        varchar embedding_hash "fingerprint nội dung và model"
        tsvector search_tsv "generated PostgreSQL"
        numeric advisor_price "generated từ payload.price"
        numeric advisor_stock "generated từ payload.stock"
        timestamptz created_at
        timestamptz updated_at
    }
    core_order {
        bigint id PK
        varchar code UK
        bigint customer_id FK "nullable"
        integer handler_id FK "nullable"
        varchar status
        varchar payment_status
        varchar payment_method
        varchar shipping_method
        varchar recipient_name
        varchar recipient_phone
        varchar province
        text address
        bigint subtotal
        bigint shipping_fee
        bigint grand_total
        timestamptz created_at
        timestamptz updated_at
    }
    core_orderitem {
        bigint id PK
        bigint order_id FK
        varchar product_external_id "mã chuỗi, không phải FK"
        varchar sku
        varchar name
        varchar image
        bigint unit_price
        integer quantity
        bigint total
    }
```

## Các bảng chưa có khóa ngoại

```mermaid
erDiagram
    core_flashsale {
        bigint id PK
        varchar product_external_id "mã chuỗi, không phải FK"
        integer quantity
        integer sold
        timestamptz starts_at
        timestamptz ends_at
        boolean active
    }
    core_productattribute {
        bigint id PK
        varchar name UK
        jsonb values
        timestamptz created_at
    }
    core_compatibilityrule {
        bigint id PK
        varchar name
        varchar source_category
        varchar source_attribute
        varchar target_category
        varchar target_attribute
        varchar operator
        boolean active
    }
    core_productimage {
        bigint id PK
        bytea content
        varchar content_type
        timestamptz created_at
    }
    core_knowledgedocument {
        bigint id PK
        varchar name
        bytea content
        text text
        integer size
        timestamptz created_at
    }
```

## Lưu ý khi đọc sơ đồ

- Mỗi hồ sơ khách hàng hoặc nhân viên thuộc đúng một tài khoản. Một tài khoản có thể không có hồ sơ khách hàng hoặc nhân viên.
- Một khách hàng có nhiều địa chỉ và đơn hàng. `customer_id` của đơn hàng cho phép NULL.
- Một danh mục có nhiều sản phẩm; sản phẩm có thể chưa có danh mục.
- Một đơn hàng có nhiều dòng chi tiết. Schema không ép đơn hàng phải có ít nhất một dòng.
- Người xử lý đơn (`handler_id`) tham chiếu trực tiếp `auth_user`, không tham chiếu `core_employee`.
- `product_external_id` trong chi tiết đơn và flash sale dùng để liên hệ sản phẩm theo mã, nhưng không có ràng buộc FK đến `core_product.external_id`.
- Thông tin chi tiết sản phẩm được lưu trong `payload` kiểu JSONB. `ProductAttribute`, `ProductImage` và `CompatibilityRule` chưa có FK đến sản phẩm/danh mục.
- Địa chỉ giao hàng trong đơn được lưu bằng các trường riêng; đơn không có FK đến `core_address`.
- Xóa tài khoản kéo theo xóa hồ sơ khách hàng/nhân viên; xóa khách hàng kéo theo xóa địa chỉ. Django đặt tham chiếu khách hàng/người xử lý trong đơn thành NULL khi đối tượng tương ứng bị xóa. Xóa danh mục đặt danh mục của sản phẩm thành NULL; xóa đơn kéo theo xóa chi tiết đơn. Đây là hành vi `on_delete` của Django ORM.


## Kiến trúc dữ liệu chatbot ver2

- `ChatSession.state` chứa phiếu nhu cầu, bộ đếm câu hỏi và giả định. Redis cache state theo ID phiên; PostgreSQL giữ bản bền vững.
- `ChatMessage.data` lưu kết quả backend, danh sách sản phẩm tại thời điểm tư vấn và trace; các snapshot này không thay thế giá/tồn hiện tại. Khi thêm cả bộ vào giỏ, backend đọc Product lại.
- Hội thoại mới đặt phiên cũ inactive, không xóa tin nhắn. Chỉ chủ tài khoản được đọc/khôi phục phiên. Xóa auth_user kéo theo xóa các phiên và tin nhắn.
- Vector nằm trong chính Product, không tạo bảng vector độc lập. HNSW dùng cosine; GIN cho search_tsv và payload.specs; B-tree theo category_id, advisor_stock, advisor_price.
- search_tsv/giá/tồn là cột PostgreSQL generated được quản lý bằng migration SQL. Model Django không khai báo các cột phụ này; SQLite test chỉ kiểm thử logic, không tạo chúng.
- Sản phẩm cũ giữ nguyên payload. Khóa chuẩn nằm trong payload.specs; xem bảng khóa trong [Chatbot.md](Chatbot.md). Khi cập nhật mô tả/thông số/tên/hãng/danh mục, chạy index_advisor_catalog.
- Catalog chưa chuẩn hóa has_igpu, stock_cooler, modules hoặc kích thước vật lý sẽ cho kết quả unknown. Đây không phải chứng nhận tương thích.
