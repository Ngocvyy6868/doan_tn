---
type: SRS
feature: ecommerce website  and chatbot builc PC
status: draft
summary: build website thương mại điện tử có sử dụng AI để tư vấn độ tương thích các linh kiện
---
**ĐẶC TẢ YÊU CẦU PHẦN MỀM**
- Không được giả định các yêu cầu
- Mỗi tính năng mới phải hỏi tôi trước, không được giả định

| **Tầng** | **Công nghệ lựa chọn** | **Mục đích sử dụng** | |
|---|---|---|---|
| Frontend | ReactJS, AntDesign| - Xây storefront, trang quản trị, PC Builder và cửa sổ chat responsive. <br> - Màn hình admin sử dụng Antdesign |
| BE | Python, Django|  |
| Database | Posrgres| Quản lý database |
| Developer | Docker|  Chạy local|

**ĐẶC TẢ YÊU CẦU PHẦN MỀM**

**WEBSITE THƯƠNG MẠI ĐIỆN TỬ  
BÁN LINH KIỆN VÀ HỖ TRỢ BUILD PC**

Software Requirements Specification (SRS) – định hướng IEEE/ISO/IEC 29148

| **Thuộc tính**    | **Thông tin**                                                       |
|-------------------|---------------------------------------------------------------------|
| Phiên bản         | 1.0 – Baseline phục vụ thiết kế, lập trình và kiểm thử              |
| Ngày ban hành     | 08/08/2026                                                          |
| Kênh sử dụng      | Website responsive cho desktop                       |
| Quy mô thử nghiệm | Khoảng 500 sản phẩm; 10–20 người dùng; 200 câu hỏi đánh giá chatbot |
| Phạm vi AI        | RAG, RAG–HyDE và rule engine kiểm tra tương thích                   |
| Trạng thái        | Draft for Development                                               |

| **Mục đích:** Làm nguồn yêu cầu thống nhất để thiết kế giao diện, cơ sở dữ liệu, API, phân rã backlog, lập trình và xây dựng test case cho đồ án. |
|---------------------------------------------------------------------------------------------------------------------------------------------------|

# Lịch sử phiên bản và phê duyệt

| **Phiên bản** | **Ngày**   | **Người lập** | **Thay đổi**                                                                                | **Trạng thái** |
|---------------|------------|---------------|---------------------------------------------------------------------------------------------|----------------|
| 1.0           | 08/08/2026 | Nhóm đồ án    | Khởi tạo SRS từ brainstorm, đề cương, danh sách chức năng website consumer và bài báo HyDE. | Chờ duyệt      |

# Mục lục nội dung

| **Mục** | **Nội dung**                            |
|---------|-----------------------------------------|
| 1       | Giới thiệu                              |
| 2       | Tổng quan sản phẩm                      |
| 3       | Tác nhân và phân quyền                  |
| 4       | Kiến trúc logic                         |
| 5       | Yêu cầu chức năng                       |
| 6       | Luồng nghiệp vụ                         |
| 7       | Quy tắc nghiệp vụ                       |
| 8       | Yêu cầu dữ liệu                         |
| 9       | Đặc tả API                              |
| 10      | Yêu cầu phi chức năng                   |
| 11      | Đặc tả chatbot RAG–HyDE                 |
| 12      | Kiểm thử và nghiệm thu                  |
| 13      | Ma trận truy vết                        |
| 14      | Kế hoạch MVP                            |
| 15      | Giả định và câu hỏi mở                  |
| Phụ lục | Backlog, trạng thái, tài liệu tham khảo |

# 1. Giới thiệu

## 1.1 Mục đích

Tài liệu mô tả đầy đủ yêu cầu nghiệp vụ và kỹ thuật cho website bán linh kiện máy tính. Hệ thống hỗ trợ hành trình từ khám phá sản phẩm đến đặt hàng, theo dõi giao nhận và hậu mãi; đồng thời tích hợp công cụ build PC và chatbot tư vấn có kiểm chứng.

## 1.2 Phạm vi

- Đăng ký, đăng nhập, OTP, quên mật khẩu và quản lý hồ sơ/địa chỉ.

- Trang chủ, danh mục, tìm kiếm, lọc, sắp xếp, chi tiết sản phẩm, yêu thích và so sánh.

- Giỏ hàng, voucher, phí giao hàng, checkout, phương thức thanh toán, tạo và theo dõi đơn.

- Hủy đơn, yêu cầu trả hàng/hoàn tiền ở mức quy trình nghiệp vụ.

- Công cụ build PC, kiểm tra tương thích, lưu/thay/so sánh cấu hình và gửi nhân viên.

- Chatbot RAG/RAG–HyDE để hỏi đáp và tư vấn; rule engine quyết định tương thích.

- Khu vực nhân viên/admin quản lý sản phẩm, thuộc tính, tồn kho, giá, đơn hàng, người dùng, nội dung, tài liệu và luật.

## 1.3 Ngoài phạm vi MVP

- Marketplace đa nhà bán và quy trình đối soát/hoa hồng phức tạp.

- Quản lý mua hàng, nhà cung cấp, kho đa tầng hoặc ERP đầy đủ.

- Ứng dụng iOS/Android native.

- Marketing automation, CDP, loyalty nhiều hạng và livestream commerce.

- Tự động fine-tune mô hình AI; triển khai production quy mô lớn.

## 1.4 Thuật ngữ

| **Thuật ngữ** | **Định nghĩa**                                                                                                    |
|---------------|-------------------------------------------------------------------------------------------------------------------|
| SKU           | Đơn vị lưu kho của một biến thể sản phẩm.                                                                         |
| Build         | Cấu hình PC gồm các linh kiện đã chọn.                                                                            |
| RAG           | Sinh câu trả lời có tăng cường truy xuất từ dữ liệu thật.                                                         |
| HyDE          | Sinh tài liệu giả định để tạo embedding truy xuất tài liệu thật; không dùng tài liệu giả định làm nguồn kết luận. |
| Rule engine   | Bộ luật xác định tương thích từ thông số có cấu trúc.                                                             |
| COD           | Thanh toán khi nhận hàng.                                                                                         |
| RBAC          | Phân quyền dựa trên vai trò.                                                                                      |

# 2. Tổng quan sản phẩm

## 2.1 Mục tiêu

| **Mã** | **Mục tiêu**                      | **Chỉ số mục tiêu**                                                        |
|--------|-----------------------------------|----------------------------------------------------------------------------|
| OBJ-01 | Hoàn thành hành trình mua hàng    | Khách có thể tìm sản phẩm, thêm giỏ, checkout và tạo đơn hợp lệ.           |
| OBJ-02 | Giảm rủi ro chọn sai linh kiện    | Accuracy kiểm tra tương thích ≥ 90%; lỗi nghiêm trọng không được đặt hàng. |
| OBJ-03 | Tư vấn có căn cứ                  | Faithfulness ≥ 0,85; Answer Relevancy ≥ 0,80; câu cần dữ liệu có nguồn.    |
| OBJ-04 | Đánh giá RAG–HyDE                 | So sánh công bằng trên 200 câu; cải thiện ≥ 5% ở chỉ số truy xuất chính.   |
| OBJ-05 | Vận hành được catalog và đơn hàng | Nhân viên quản lý khoảng 500 sản phẩm, tồn kho, giá và trạng thái đơn.     |

## 2.2 Nhóm người dùng

| **Tác nhân**          | **Nhu cầu chính**                                                                        |
|-----------------------|------------------------------------------------------------------------------------------|
| Khách vãng lai        | Xem/tìm/lọc sản phẩm, xem build mẫu; đăng nhập khi lưu hoặc mua.                         |
| Khách hàng            | Quản lý tài khoản, yêu thích, build, giỏ hàng, đặt và theo dõi đơn.    |                    
| Quản trị viên        |- Tiếp nhận yêu cầu build, hỗ trợ đơn, hủy/trả hàng và phản hồi khách.  <br> - Cập nhật tồn kho, xác nhận đóng gói và bàn giao vận chuyển. <br> - Quản lý catalog, giá, tồn kho, tài khoản, quyền, nội dung, tài liệu AI và luật.                              |
| Nhóm đồ án            | Chạy đánh giá offline RAG/RAG–HyDE và xuất báo cáo.                                      |

## 2.3 Giả định vận hành

- Một doanh nghiệp bán hàng trực tiếp; mỗi SKU có một số lượng tồn khả dụng tại baseline.

- Tiền tệ VND, múi giờ Asia/Ho_Chi_Minh, giao hàng trong Việt Nam.

- MVP hỗ trợ COD và một phương thức thanh toán điện tử ở chế độ tích hợp/sandbox.

- Giá và tồn kho phải được kiểm tra lại ở bước xác nhận đơn; dữ liệu chatbot không được coi là cam kết nếu đã thay đổi.

# 3. Tác nhân và phân quyền

| **Chức năng**            | **Vãng lai** | **Khách hàng** | **Tư vấn/CSKH** | **Kho**     | **Admin** |
|--------------------------|--------------|----------------|-----------------|-------------|-----------|
| Xem/tìm sản phẩm         | Có           | Có             | Có              | Có          | Có        |
| Yêu thích/lưu build      | Không        | Có             | Có              | Không       | Có        |
| Đặt và xem đơn cá nhân   | Không        | Có             | Hỗ trợ          | Không       | Có        |
| Cập nhật trạng thái đơn  | Không        | Không          | Có giới hạn     | Có giới hạn | Có        |
| Quản lý sản phẩm/giá/tồn | Không        | Không          | Chỉ xem         | Tồn kho     | Có        |
| Quản lý voucher/nội dung | Không        | Không          | Không           | Không       | Có        |
| Quản lý tài liệu/luật AI | Không        | Không          | Không           | Không       | Có        |
| Xem audit log            | Không        | Không          | Không           | Không       | Có        |

| **Nguyên tắc phân quyền:** Mặc định từ chối; người dùng chỉ truy cập dữ liệu thuộc sở hữu của mình. Quyền nhạy cảm phải được kiểm tra tại Backend API, không chỉ ẩn nút trên giao diện. |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

# 4. Kiến trúc logic

| **Thành phần**  | **Trách nhiệm**                                                          | **Baseline đề xuất**                   |
|-----------------|--------------------------------------------------------------------------|----------------------------------------|
| Web Client      | Storefront responsive, tài khoản, checkout, build editor, chat và admin. | React/Next.js hoặc tương đương.        |
| Backend API     | Xác thực, catalog, giá, giỏ, đơn, voucher, tồn kho, RBAC.                | FastAPI hoặc framework tương đương.    |
| Operational DB  | Tài khoản, sản phẩm/SKU, đơn, tồn, build, voucher, audit.                | PostgreSQL; SQLite chỉ dùng prototype. |
| Search          | Tìm kiếm từ khóa, bộ lọc và sắp xếp catalog.                             | DB full-text hoặc search service.      |
| AI Orchestrator | Intent, RAG/HyDE, citation, rule engine, fallback.                       | Python service/module.                 |
| Vector Store    | Embedding tài liệu/chunk và metadata.                                    | ChromaDB.                              |
| Object Storage  | Ảnh sản phẩm và tài liệu.                                                | Local/S3-compatible.                   |
| Job Worker      | OTP, email, lập chỉ mục, đồng bộ tồn, tác vụ nền.                        | Queue/cron phù hợp.                    |

## 4.1 Nguyên tắc thiết kế

- Order lưu snapshot tên, SKU và giá tại thời điểm đặt; thay đổi catalog không sửa lịch sử đơn.

- Các thao tác trừ/giữ tồn và tạo đơn phải nằm trong transaction; request checkout có idempotency key.

- Rule engine là nguồn kết luận cuối về tương thích; LLM chỉ giải thích kết quả có cấu trúc.

- Mọi thay đổi giá, tồn kho, trạng thái đơn, luật và quyền phải có audit log.

- Job lập chỉ mục mới chỉ được kích hoạt sau khi hoàn tất; lỗi phải tiếp tục dùng index cũ.

# 5. Yêu cầu chức năng

| **Quy ước:** P0 = bắt buộc MVP; P1 = nên có; P2 = mở rộng. Mỗi yêu cầu phải được kiểm thử theo tiêu chí chấp nhận trong bảng. |
|-------------------------------------------------------------------------------------------------------------------------------|

| **ID**        | **Yêu cầu**                       | **Ưu tiên** | **Mô tả**                                                                                 | **Tiêu chí chấp nhận**                                                             |
|---------------|-----------------------------------|-------------|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| FR-AUTH-01    | Đăng ký khách hàng                | P0          | Đăng ký bằng email hoặc số điện thoại, mật khẩu và OTP; không tạo trùng định danh.        | OTP đúng/còn hạn tạo tài khoản; sai hoặc hết hạn báo rõ; mật khẩu đạt chính sách.  |
| FR-AUTH-02    | Đăng nhập/đăng xuất               | P0          | Đăng nhập bằng mật khẩu; duy trì phiên an toàn; đăng xuất hủy phiên hiện tại.             | Sai thông tin không tiết lộ tài khoản tồn tại; rate limit sau nhiều lần sai.       |
| FR-AUTH-03    | Quên/đổi mật khẩu                 | P0          | Gửi OTP/token và cho đặt mật khẩu mới.                                                    | Token một lần, có hạn; phiên cũ bị thu hồi theo cấu hình.                          |
| FR-ACC-01     | Hồ sơ và avatar                   | P1          | Xem/sửa họ tên, điện thoại, email và avatar.                                              | Dữ liệu hợp lệ được lưu; đổi định danh yêu cầu xác minh lại.                       |
| FR-ADDR-01    | Sổ địa chỉ                        | P0          | Thêm/sửa/xóa nhiều địa chỉ và đặt mặc định.                                               | Không xóa địa chỉ đang cần cho checkout; chỉ chủ tài khoản truy cập.               |
| FR-HOME-01    | Trang chủ                         | P0          | Hiển thị search, danh mục, banner, sản phẩm nổi bật/khuyến mãi và footer.                 | Nội dung không hoạt động được ẩn; liên kết đúng landing/category.                  |
| FR-CAT-01     | Danh mục sản phẩm                 | P0          | Duyệt phân cấp ngành hàng theo menu ngang/dọc.                                            | Breadcrumb và phân trang đúng; danh mục vô hiệu hóa không hiển thị.                |
| FR-SEARCH-01  | Tìm kiếm                          | P0          | Tìm theo tên, SKU, thương hiệu và từ khóa mô tả.                                          | Không có kết quả hiển thị gợi ý; truy vấn được chuẩn hóa và an toàn.               |
| FR-FILTER-01  | Lọc/sắp xếp                       | P0          | Lọc giá, thương hiệu, tình trạng, thuộc tính; sắp xếp giá, bán chạy, giảm giá, mới nhất.  | Nhiều bộ lọc kết hợp đúng; URL lưu được trạng thái lọc.                            |
| FR-PDP-01     | Chi tiết sản phẩm                 | P0          | Hiển thị ảnh, tên, giá, biến thể, tồn, mô tả, thuộc tính, chính sách, sản phẩm liên quan. | SKU/biến thể đổi đúng giá-tồn; hết hàng không cho mua.                             |
| FR-FAV-01     | Yêu thích                         | P1          | Thêm/xóa sản phẩm và xem danh sách yêu thích.                                             | Không tạo bản ghi trùng; trạng thái đồng bộ sau đăng nhập.                         |
| FR-COMPARE-01 | So sánh sản phẩm                  | P1          | So sánh tối đa 4 sản phẩm cùng/nhóm tương đương theo thuộc tính.                          | Bảng làm nổi khác biệt; xử lý thuộc tính thiếu bằng “Chưa có dữ liệu”.             |
| FR-CART-01    | Thêm giỏ/Mua ngay                 | P0          | Thêm SKU với số lượng; Mua ngay mở checkout cho SKU đã chọn.                              | Số lượng không vượt tồn/giới hạn; giỏ khách đăng nhập được lưu.                    |
| FR-CART-02    | Cập nhật giỏ                      | P0          | Đổi số lượng, xóa, chọn sản phẩm và tính tổng.                                            | Tổng cập nhật chính xác; cảnh báo giá/tồn thay đổi.                                |
| FR-VOUCHER-01 | Áp dụng voucher                   | P1          | Nhập/chọn voucher phù hợp với điều kiện đơn, khách và thời hạn.                           | Không cộng dồn trái quy tắc; lưu số tiền giảm và lý do từ chối.                    |
| FR-SHIP-01    | Phí và phương thức giao           | P0          | Tính phí theo địa chỉ, phương thức, trọng lượng/giá trị theo cấu hình.                    | Checkout hiển thị phí trước xác nhận; lỗi dịch vụ có fallback/thông báo.           |
| FR-CHK-01     | Checkout                          | P0          | Xác nhận địa chỉ, sản phẩm, số lượng, giá, giảm, phí, phương thức và tổng đơn.            | Kiểm tra lại giá/tồn/voucher; không cho xác nhận khi dữ liệu không hợp lệ.         |
| FR-PAY-01     | Thanh toán                        | P0          | Hỗ trợ COD và cổng điện tử/sandbox; tiếp nhận callback.                                   | Callback được xác thực, idempotent; trạng thái thanh toán không cập nhật lặp.      |
| FR-ORDER-01   | Tạo đơn                           | P0          | Tạo mã đơn và snapshot dòng hàng sau checkout thành công.                                 | Tạo một lần cho mỗi idempotency key; tổng tiền khớp chi tiết.                      |
| FR-ORDER-02   | Lịch sử/chi tiết đơn              | P0          | Khách xem đơn, timeline, địa chỉ, thanh toán và vận chuyển.                               | Chỉ chủ đơn hoặc nhân sự có quyền được xem.                                        |
| FR-ORDER-03   | Hủy đơn                           | P0          | Khách hủy khi trạng thái cho phép và chọn lý do.                                          | Hoàn tồn/khởi tạo hoàn tiền khi cần; ghi audit và timeline.                        |
| FR-RETURN-01  | Trả hàng/hoàn tiền                | P1          | Tạo yêu cầu theo dòng hàng, lý do, ảnh minh chứng và số lượng.                            | Trong thời hạn/chính sách; trạng thái và phản hồi được theo dõi.                   |
| FR-TRACK-01   | Theo dõi giao hàng                | P1          | Hiển thị mã vận đơn và trạng thái pickup/delivering/delivered.                            | Webhook/polling idempotent; sự kiện hiển thị theo thời gian.                       |
| FR-BUILD-01   | Công cụ build PC                  | P0          | Chọn CPU, mainboard, RAM, GPU, PSU, case, tản, storage theo slot.                         | Hiển thị giá/tổng/tồn; chỉ một SKU mỗi slot trừ nhóm cho phép nhiều.               |
| FR-BUILD-02   | Tư vấn theo nhu cầu               | P0          | Thu thập ngân sách, mục đích, game/phần mềm, hiệu năng, linh kiện có sẵn, thương hiệu.    | Thiếu ngân sách/mục đích thì hỏi thêm; trả một build chính và lựa chọn thay thế.   |
| FR-BUILD-03   | Kiểm tra tương thích              | P0          | Chạy luật sau mỗi thay đổi và trước lưu/đặt hàng.                                         | Trả PASS/WARNING/FAIL/UNKNOWN cùng bằng chứng; FAIL chặn lưu/đặt.                  |
| FR-BUILD-04   | Lưu/thay/so sánh build            | P0          | Lưu bản cấu hình, nhân bản, thay linh kiện, so sánh build.                                | Tính lại giá-tồn-tương thích; draft tự lưu tối đa 24 giờ.                          |
| FR-BUILD-05   | Đưa build vào giỏ                 | P0          | Thêm các SKU hợp lệ/còn hàng từ build vào giỏ.                                            | Liệt kê SKU không thể thêm và sản phẩm thay thế; không thêm âm thầm.               |
| FR-CHAT-01    | Chatbot đa điểm truy cập          | P0          | Nút chat nổi, trang Build PC và trang chi tiết sản phẩm; yêu cầu đăng nhập theo baseline. | Giữ ngữ cảnh phiên; lỗi 3 lần cho phép chuyển nhân viên.                           |
| FR-CHAT-02    | Trả lời có nguồn                  | P0          | Trả lời từ catalog/tài liệu thật, đính kèm citation và hành động liên quan.               | Không đủ căn cứ phải nói rõ; không bịa giá, tồn, chính sách hoặc tương thích.      |
| FR-HYDE-01    | RAG–HyDE                          | P0          | Sinh hypothetical document, embedding và truy xuất tài liệu thật; có fallback RAG thường. | Tài liệu giả định không được hiển thị như nguồn hoặc dùng làm kết luận.            |
| FR-LEAD-01    | Chuyển nhân viên tư vấn           | P1          | Gửi hội thoại/build và yêu cầu ở trạng thái Chờ tiếp nhận.                                | Nhân viên nhận, phản hồi và chuyển Đang tư vấn/Hoàn tất/Hủy.                       |
| FR-ADMIN-01   | Quản lý catalog                   | P0          | CRUD danh mục, thương hiệu, sản phẩm, SKU, ảnh, thuộc tính, giá và trạng thái.            | Kiểm tra trường bắt buộc theo nhóm; SKU duy nhất; xóa mềm khi đã phát sinh đơn.    |
| FR-ADMIN-02   | Quản lý tồn kho                   | P0          | Xem và điều chỉnh tồn với lý do; cảnh báo sắp/hết hàng.                                   | Không cho tồn khả dụng âm; mọi điều chỉnh có người/thời gian/lý do.                |
| FR-ADMIN-03   | Quản lý đơn hàng                  | P0          | Danh sách, chi tiết, lọc và cập nhật trạng thái theo quyền.                               | Chỉ cho transition hợp lệ; gửi thông báo và ghi audit.                             |
| FR-ADMIN-04   | Quản lý khách hàng/quyền          | P0          | Xem khách; tạo nhân viên, khóa/mở và cấp vai trò.                                         | Không xem mật khẩu; không tự nâng quyền trái chính sách.                           |
| FR-ADMIN-05   | Quản lý banner/voucher/chính sách | P1          | CRUD nội dung hiển thị và chương trình giảm giá.                                          | Có thời gian hiệu lực; preview/validation trước kích hoạt.                         |
| FR-ADMIN-06   | Quản lý tri thức và luật          | P0          | CRUD tài liệu, phiên bản, nguồn, luật tương thích; chạy index thủ công/hằng ngày.         | Chỉ kích hoạt index/rule version hợp lệ; rollback được bản trước.                  |
| FR-EVAL-01    | Đánh giá RAG/HyDE                 | P0          | Chạy hai phương pháp trên cùng 200 câu, corpus, chunking, embedding và top-k.             | Lưu version cấu hình; xuất metric retrieval, generation, compatibility và latency. |
| FR-AUDIT-01   | Nhật ký kiểm toán                 | P0          | Ghi thao tác nhạy cảm và trước/sau ở mức phù hợp.                                         | Log bất biến với người, thời gian, đối tượng, hành động và trace_id.               |

# 6. Luồng nghiệp vụ chính

## UC-01 – Mua hàng tiêu chuẩn

1.  Khách tìm/lọc và mở chi tiết SKU.

2.  Chọn biến thể, số lượng; thêm giỏ hoặc Mua ngay.

3.  Giỏ kiểm tra tồn và tính tạm tính.

4.  Checkout chọn địa chỉ, voucher, giao hàng và thanh toán.

5.  Backend kiểm tra lại giá, tồn, voucher trong transaction.

6.  Hệ thống tạo đơn, giữ/trừ tồn, ghi snapshot và gửi xác nhận.

## UC-02 – Build PC rồi đặt hàng

7.  Khách nhập nhu cầu hoặc chọn linh kiện theo slot.

8.  Hệ thống gợi ý, hiển thị giá/tồn và chạy rule engine.

9.  Khách thay linh kiện; hệ thống kiểm tra lại toàn bộ build.

10. FAIL bị chặn; WARNING cần xác nhận; UNKNOWN chuyển nhân viên.

11. Build hợp lệ được lưu và thêm các SKU còn hàng vào giỏ.

12. Checkout tiếp tục theo UC-01.

## UC-03 – Thanh toán điện tử

13. Backend tạo payment intent cho đúng tổng tiền.

14. Khách chuyển tới cổng thanh toán.

15. Cổng gửi callback đã ký.

16. Backend kiểm tra chữ ký, số tiền, mã giao dịch và idempotency.

17. Thành công cập nhật PAID; thất bại/timeout cho retry hoặc đổi phương thức.

## UC-04 – Hủy/trả hàng

18. Khách mở đơn và chọn hủy hoặc trả hàng.

19. Hệ thống kiểm tra trạng thái, thời hạn và chính sách.

20. Hủy hợp lệ hoàn tồn; thanh toán trước tạo yêu cầu hoàn tiền.

21. Trả hàng được CSKH duyệt/từ chối, kho tiếp nhận và cập nhật kết quả.

22. Mọi bước được ghi timeline và thông báo.

## UC-05 – Tư vấn RAG–HyDE

23. Nhận câu hỏi và phân loại ý định.

24. RAG thường embedding query; HyDE sinh tài liệu giả định rồi embedding.

25. Truy xuất top-k tài liệu thật; lọc theo metadata.

26. Nếu liên quan build, gọi rule engine trên dữ liệu cấu trúc.

27. LLM tổng hợp từ nguồn thật và kết quả luật; gắn citation/cảnh báo.

28. Thiếu căn cứ thì từ chối kết luận hoặc chuyển nhân viên.

## 6.6 Ngoại lệ bắt buộc

| **Tình huống**                | **Xử lý**                                                                       |
|-------------------------------|---------------------------------------------------------------------------------|
| Giá/tồn thay đổi khi checkout | Hiển thị chênh lệch, yêu cầu khách xác nhận lại; không tạo đơn bằng dữ liệu cũ. |
| Hai khách mua SKU cuối        | Transaction/lock ưu tiên xác nhận hợp lệ trước; người sau nhận hết hàng.        |
| Callback thanh toán lặp       | Idempotency bỏ qua cập nhật trùng nhưng lưu dấu vết.                            |
| Dịch vụ vận chuyển lỗi        | Giữ giỏ, cho thử lại hoặc dùng phí/phương thức fallback đã cấu hình.            |
| HyDE/LLM lỗi                  | Retry tối đa 3 lần, fallback RAG thường; sau đó chuyển nhân viên.               |
| Index mới lỗi                 | Không kích hoạt; tiếp tục phục vụ bằng index trước.                             |
| Thông số tương thích thiếu    | Trả UNKNOWN, không tự suy đoán; chặn đặt build hoặc yêu cầu nhân viên xác minh. |

# 7. Quy tắc nghiệp vụ

| **Mã**        | **Quy tắc**                                                                                                                                                       |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| BR-PRICE-01   | Giá đơn là giá SKU tại thời điểm xác nhận, sau khuyến mãi hợp lệ; OrderItem lưu snapshot.                                                                         |
| BR-STOCK-01   | available = on_hand - reserved; không cho available âm.                                                                                                           |
| BR-STOCK-02   | Giữ/trừ tồn và tạo đơn là transaction; hủy hợp lệ hoàn giữ tồn.                                                                                                   |
| BR-VOUCHER-01 | Voucher kiểm tra hiệu lực, đối tượng, giá trị tối thiểu, quota, giới hạn người dùng và quy tắc cộng dồn.                                                          |
| BR-ORDER-01   | Transition: PENDING_PAYMENT → CONFIRMED → PACKING → READY_FOR_PICKUP → DELIVERING → DELIVERED; nhánh CANCELLED/RETURN_REQUESTED/RETURNED/REFUNDED theo điều kiện. |
| BR-CANCEL-01  | Khách chỉ tự hủy trước PACKING; sau đó cần CSKH xử lý.                                                                                                            |
| BR-RETURN-01  | Yêu cầu trả hàng phải nằm trong thời hạn chính sách và không vượt số lượng đã giao.                                                                               |
| BR-PAY-01     | Một giao dịch thanh toán thành công chỉ gắn một lần với một đơn; tổng và tiền tệ phải khớp.                                                                       |
| BR-BUILD-01   | Build tối đa 15 dòng linh kiện; một yêu cầu đặt hàng tối đa 10 build.                                                                                             |
| BR-COMP-01    | Kiểm tra tối thiểu CPU–mainboard, mainboard–RAM, mainboard–case, GPU–case, cooler–CPU/case, PSU–toàn build, storage–mainboard.                                    |
| BR-COMP-02    | FAIL chặn lưu chính thức/đặt hàng; WARNING cho lưu sau khi hiển thị; UNKNOWN không được kết luận tương thích.                                                     |
| BR-AI-01      | Khi RAG mâu thuẫn với luật có cấu trúc, luật quyết định kết luận; RAG chỉ giải thích bằng nguồn.                                                                  |
| BR-DRAFT-01   | Build nháp tự lưu trong 24 giờ rồi hết hạn nếu không lưu chính thức.                                                                                              |
| BR-SEC-01     | OTP/token có hạn, dùng một lần; mật khẩu không lưu dạng rõ.                                                                                                       |

## 7.1 Ma trận luật tương thích

| **Mã**        | **Quan hệ**         | **Điều kiện chính**                                              | **Mức khi sai/thiếu**      |
|---------------|---------------------|------------------------------------------------------------------|----------------------------|
| COMP-CPU-MB   | CPU ↔ Mainboard     | Socket khớp; CPU nằm trong support list; BIOS tối thiểu nếu có.  | FAIL / UNKNOWN             |
| COMP-MB-RAM   | Mainboard ↔ RAM     | DDR generation, module type, capacity/speed hỗ trợ.              | FAIL / WARNING             |
| COMP-MB-CASE  | Mainboard ↔ Case    | Form factor mainboard được case hỗ trợ.                          | FAIL                       |
| COMP-GPU-CASE | GPU ↔ Case          | Chiều dài, độ dày/slot, vị trí radiator phù hợp.                 | FAIL / UNKNOWN             |
| COMP-COOLER   | Cooler ↔ CPU/Case   | Socket hỗ trợ; chiều cao/radiator phù hợp; TDP có biên.          | FAIL / WARNING             |
| COMP-PSU      | PSU ↔ Build         | Công suất khuyến nghị + biên; đủ connector; form factor phù hợp. | FAIL / WARNING             |
| COMP-STORAGE  | Storage ↔ Mainboard | Interface, key, lane/port và số khe phù hợp.                     | FAIL / WARNING             |
| COMP-BUDGET   | Build ↔ Ngân sách   | Tổng tiền không vượt ngân sách trừ biên khách cho phép.          | WARNING/FAIL theo cấu hình |

# 8. Yêu cầu dữ liệu

| **Thực thể**             | **Trường cốt lõi**                                                          |
|--------------------------|-----------------------------------------------------------------------------|
| User                     | id, role, name, email, phone, password_hash, status, verified_at            |
| Address                  | id, user_id, receiver, phone, province, district, ward, line, is_default    |
| Category/Brand           | id, parent_id/name, slug, status                                            |
| Product                  | id, category_id, brand_id, name, slug, descriptions, policy, status         |
| SKU/Variant              | id, product_id, sku, option_values, price, compare_at_price, weight, status |
| ProductAttribute         | product/sku, attribute definition, typed value, unit, source                |
| Inventory                | sku_id, on_hand, reserved, reorder_level, version                           |
| Cart/CartItem            | user/session, sku_id, quantity, selected, timestamps                        |
| Voucher                  | code, type/value, conditions, quota, per_user_limit, valid range, status    |
| Order                    | code, user, address snapshot, totals, payment/shipping status, timestamps   |
| OrderItem                | order_id, sku_id, name/variant/price snapshots, qty, discounts, total       |
| Payment                  | order_id, provider, method, amount, status, transaction_ref, callback hash  |
| Shipment                 | order_id, carrier, tracking, fee, status, events                            |
| ReturnRequest            | order/item, qty, reason, evidence, status, resolution/refund                |
| Build/BuildItem          | owner, name, budget, purpose, status; slot, sku, qty, price snapshot        |
| CompatibilityRule/Result | versioned condition; build, rule, status, evidence, evaluated_at            |
| KnowledgeDocument/Chunk  | source, version, status; text, embedding metadata, index version            |
| Conversation/Message     | user/session, role, content, citations, retrieval trace                     |
| ConsultationRequest      | user, build/conversation, assignee, status, response                        |
| AuditLog                 | actor, action, object, before/after summary, trace, timestamp               |

## 8.1 Ràng buộc dữ liệu

- Email/phone đã chuẩn hóa là duy nhất khi được dùng làm định danh; SKU và mã đơn duy nhất.

- Tiền lưu bằng số nguyên VND hoặc decimal có precision rõ; không dùng float.

- Order/OrderItem, Payment và AuditLog không bị sửa/xóa vật lý bởi thao tác người dùng.

- Thuộc tính kỹ thuật có kiểu, đơn vị và nguồn; trường quyết định luật không được lưu chỉ trong mô tả tự do.

- Tất cả bảng chính có created_at, updated_at; bản ghi quản trị quan trọng có created_by/updated_by/version.

# 9. Đặc tả API

| **Method**            | **Endpoint**                             | **Quyền**       | **Mục đích**                    |
|-----------------------|------------------------------------------|-----------------|---------------------------------|
| POST                  | /api/v1/auth/register                    | Public          | Đăng ký và gửi OTP              |
| POST                  | /api/v1/auth/verify-otp                  | Public          | Xác minh tài khoản              |
| POST                  | /api/v1/auth/login                       | Public          | Đăng nhập                       |
| POST                  | /api/v1/auth/forgot-password             | Public          | Khởi tạo đặt lại mật khẩu       |
| GET                   | /api/v1/products                         | Public          | Tìm kiếm/lọc/sắp xếp/phân trang |
| GET                   | /api/v1/products/{slug}                  | Public          | Chi tiết sản phẩm/SKU           |
| GET/POST              | /api/v1/favorites                        | Customer        | Xem/thêm yêu thích              |
| GET/POST/PATCH/DELETE | /api/v1/cart/items                       | Customer        | Quản lý giỏ                     |
| POST                  | /api/v1/checkout/quote                   | Customer        | Tính lại giá, voucher, phí, tồn |
| POST                  | /api/v1/orders                           | Customer        | Tạo đơn idempotent              |
| GET                   | /api/v1/orders/{id}                      | Owner/Staff     | Chi tiết đơn                    |
| POST                  | /api/v1/orders/{id}/cancel               | Owner/Staff     | Hủy đơn                         |
| POST                  | /api/v1/orders/{id}/returns              | Customer        | Tạo yêu cầu trả                 |
| POST                  | /api/v1/payments/intents                 | Customer        | Tạo giao dịch                   |
| POST                  | /api/v1/payments/webhooks/{provider}     | Provider        | Nhận callback có chữ ký         |
| POST                  | /api/v1/builds/validate                  | Customer        | Kiểm tra tương thích            |
| GET/POST/PATCH        | /api/v1/builds                           | Customer        | Quản lý build                   |
| POST                  | /api/v1/builds/{id}/add-to-cart          | Customer        | Thêm build vào giỏ              |
| POST                  | /api/v1/chat/messages                    | Customer        | Chat RAG/HyDE                   |
| POST                  | /api/v1/consultations                    | Customer        | Chuyển nhân viên                |
| CRUD                  | /api/v1/admin/products\|skus\|categories | Admin           | Quản lý catalog                 |
| PATCH                 | /api/v1/admin/inventory/{skuId}          | Warehouse/Admin | Điều chỉnh tồn                  |
| GET/PATCH             | /api/v1/admin/orders                     | Staff/Admin     | Quản lý đơn                     |
| POST                  | /api/v1/admin/index-jobs                 | Admin           | Lập chỉ mục                     |
| POST                  | /api/v1/admin/evaluations                | Admin           | Chạy đánh giá                   |

## 9.1 Chuẩn API

- JSON UTF-8; version bằng /api/v1; timestamp ISO 8601 UTC, giao diện đổi sang Asia/Ho_Chi_Minh.

- Phân trang dùng page/page_size hoặc cursor nhất quán; response có data, meta và error.

- Mutation tạo đơn/thanh toán dùng Idempotency-Key; mỗi request có trace_id.

- Mã lỗi tối thiểu: VALIDATION_ERROR, UNAUTHORIZED, FORBIDDEN, NOT_FOUND, CONFLICT, OUT_OF_STOCK, PRICE_CHANGED, INVALID_VOUCHER, INCOMPATIBLE_BUILD, INSUFFICIENT_DATA, PAYMENT_FAILED, RATE_LIMITED.

- Không trả stack trace, secret, password hash hoặc thông tin người dùng khác.

## 9.2 Ví dụ request checkout

| **POST /api/v1/orders** { address_id, shipping_method, payment_method, voucher_code?, selected_cart_item_ids\[\] } + header Idempotency-Key. Response trả order_id, order_code, totals, payment_action và trạng thái. |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

# 10. Yêu cầu phi chức năng

| **ID**        | **Nhóm**     | **Yêu cầu**                                                                                                    |
|---------------|--------------|----------------------------------------------------------------------------------------------------------------|
| NFR-PERF-01   | Hiệu năng    | Trang danh sách/chi tiết P95 API ≤ 1 giây với 500 sản phẩm; tìm kiếm P95 ≤ 1,5 giây.                           |
| NFR-PERF-02   | Hiệu năng AI | Phản hồi trung bình ≤ 10 giây; time-to-first-token P95 mục tiêu ≤ 4 giây nếu streaming.                        |
| NFR-PERF-03   | Checkout     | Tính quote P95 ≤ 2 giây, không tính thời gian cổng ngoài.                                                      |
| NFR-AVAIL-01  | Sẵn sàng     | Mục tiêu MVP 99% trong khung demo; lỗi AI không làm hỏng catalog/checkout.                                     |
| NFR-CONC-01   | Đồng thời    | Tối thiểu 20 phiên hoạt động đồng thời; kiểm thử race SKU cuối.                                                |
| NFR-SEC-01    | Bảo mật      | HTTPS, password hash Argon2id/bcrypt, RBAC, CSRF theo kiến trúc, rate limit, validation, secure cookies/token. |
| NFR-SEC-02    | OWASP        | Phòng SQLi, XSS, broken access control, SSRF, upload độc hại; dependency/secrets scan.                         |
| NFR-SEC-03    | Thanh toán   | Không lưu dữ liệu thẻ; xác minh chữ ký callback và chống replay.                                               |
| NFR-PRIV-01   | Riêng tư     | Thu thập tối thiểu; ẩn dữ liệu nhạy cảm trong log; quyền xem dữ liệu theo vai trò.                             |
| NFR-REL-01    | Tin cậy      | Transaction cho order/stock/payment; retry chỉ với thao tác idempotent; backup/restore được kiểm thử.          |
| NFR-OBS-01    | Quan sát     | Structured log, trace_id, metric latency/error/payment/stock/AI fallback; cảnh báo lỗi quan trọng.             |
| NFR-USAB-01   | Dễ dùng      | Responsive từ 360 px; loading/empty/error rõ; checkout không mất dữ liệu khi lỗi có thể phục hồi.              |
| NFR-A11Y-01   | Truy cập     | Điều hướng bàn phím, label form, focus rõ, alt ảnh, tương phản phù hợp; không chỉ dùng màu báo lỗi.            |
| NFR-SEO-01    | SEO          | Slug/canonical, sitemap, metadata, structured data Product khi phù hợp; trang riêng tư không index.            |
| NFR-MAINT-01  | Bảo trì      | Tách module; cấu hình ngoài code; migration; unit/integration/E2E; version rule/index/prompt.                  |
| NFR-COMPAT-01 | Tương thích  | Hỗ trợ hai phiên bản gần nhất của Chrome, Edge, Firefox; responsive desktop/mobile.                            |
| NFR-REPRO-01  | Tái lập AI   | Lưu dataset, corpus/index, model, prompt, embedding, top-k, threshold và timestamp cho mỗi experiment.         |

# 11. Đặc tả chatbot RAG–HyDE

## 11.1 Nguồn tri thức

- Catalog và thuộc tính kỹ thuật có cấu trúc.

- Tài liệu chính hãng và chính sách cửa hàng có nguồn/phiên bản.

- Hướng dẫn build PC đã kiểm duyệt.

- Giá và tồn kho đọc trực tiếp từ cơ sở dữ liệu nghiệp vụ, không từ vector store.

- Luật tương thích do admin quản lý và version hóa.

## 11.2 Pipeline

| **Giai đoạn** | **RAG thường**                                            | **RAG–HyDE**                                                 |
|---------------|-----------------------------------------------------------|--------------------------------------------------------------|
| Chuẩn hóa     | Query + intent + entities.                                | Query + intent + entities.                                   |
| Cầu truy xuất | Embedding query.                                          | LLM sinh hypothetical document; embedding tài liệu giả định. |
| Truy xuất     | Top-k tài liệu thật theo vector/metadata.                 | Top-k tài liệu thật gần embedding HyDE; có thể rerank.       |
| Kiểm chứng    | Đọc catalog/giá/tồn và chạy luật khi cần.                 | Giống RAG thường.                                            |
| Sinh đáp án   | Chỉ dùng tài liệu thật + dữ liệu cấu trúc + kết quả luật. | Giống RAG thường; không trích hypothetical document.         |
| Fallback      | Thông báo thiếu nguồn/chuyển nhân viên.                   | Fallback RAG thường nếu sinh HyDE lỗi/timeout.               |

## 11.3 Đánh giá

| **Nhóm**      | **Chỉ số**                                                            | **Ngưỡng/ghi chú**                                |
|---------------|-----------------------------------------------------------------------|---------------------------------------------------|
| Retrieval     | Precision@k, Recall@k, Context Precision/Recall, MRR hoặc nDCG@10     | RAG–HyDE cải thiện ≥ 5% ở chỉ số chính đã chốt.   |
| Generation    | Faithfulness, Answer Relevancy, Answer Correctness, chấm thủ công 1–5 | Faithfulness ≥ 0,85; Relevancy ≥ 0,80.            |
| Compatibility | Accuracy, Precision, Recall, F1                                       | Accuracy ≥ 90%; báo cáo confusion matrix.         |
| Performance   | Latency trung bình/P95, timeout, fallback rate                        | Trung bình ≤ 10 giây trong môi trường nghiệm thu. |
| Composite     | 0,30 Retrieval + 0,30 Generation + 0,40 Compatibility                 | Chuẩn hóa 0–1; vẫn công bố chỉ số thành phần.     |

| **Ràng buộc chống hallucination:** HyDE tạo nội dung giả định có thể sai. Nội dung đó chỉ là cầu nối truy xuất; nguồn hiển thị cho người dùng phải là tài liệu thật. Giá, tồn và kết luận tương thích bắt buộc lấy từ dữ liệu nghiệp vụ/rule engine. |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

# 12. Kiểm thử và nghiệm thu

## 12.1 Tầng kiểm thử

- Unit test: giá/giảm/thuế-phí, voucher, transition, tồn kho, từng luật tương thích.

- Integration test: DB transaction, payment callback, shipping adapter, vector store, index job.

- API contract/security test: auth, ownership, RBAC, validation, idempotency, rate limit.

- E2E: đăng ký → tìm → giỏ → checkout → thanh toán/COD → theo dõi/hủy/trả.

- Race test: hai checkout cùng SKU cuối; callback thanh toán lặp/đảo thứ tự.

- AI evaluation: chạy cố định 200 câu trên cùng dữ liệu và cấu hình so sánh.

## 12.2 Tiêu chí nghiệm thu

| **Mã** | **Điều kiện đạt**                                                           |
|--------|-----------------------------------------------------------------------------|
| AC-01  | Đăng ký/OTP/đăng nhập/quên mật khẩu đạt test hợp lệ và lỗi.                 |
| AC-02  | Tìm/lọc/phân trang/chi tiết đúng với khoảng 500 sản phẩm.                   |
| AC-03  | Giỏ và checkout tính chính xác subtotal, discount, shipping và grand total. |
| AC-04  | Không oversell trong test đồng thời SKU cuối; order idempotent.             |
| AC-05  | COD và payment sandbox xử lý callback thành công/thất bại/lặp đúng.         |
| AC-06  | Khách chỉ xem đơn của mình; trạng thái đơn đi theo transition cho phép.     |
| AC-07  | Hủy/trả hàng cập nhật tồn, thanh toán và timeline đúng chính sách.          |
| AC-08  | 100% test luật bắt buộc đạt; FAIL/UNKNOWN không được đặt build.             |
| AC-09  | Build được lưu, thay, so sánh, gửi nhân viên và thêm vào giỏ.               |
| AC-10  | Chatbot trả nguồn thật; không dùng hypothetical document làm nguồn.         |
| AC-11  | Báo cáo RAG/RAG–HyDE tái lập được trên 200 câu.                             |
| AC-12  | RBAC, audit log và kiểm tra OWASP quan trọng đạt.                           |
| AC-13  | Responsive 360 px và desktop; không clipping/overflow ở luồng chính.        |
| AC-14  | Đạt các ngưỡng NFR trong môi trường nghiệm thu được ghi nhận.               |

# 13. Ma trận truy vết

| **Mục tiêu**          | **Yêu cầu liên quan**                                            | **Nghiệm thu**      |
|-----------------------|------------------------------------------------------------------|---------------------|
| OBJ-01 – Mua hàng     | FR-HOME/CAT/SEARCH/FILTER/PDP, FR-CART, FR-CHK, FR-PAY, FR-ORDER | AC-02..07           |
| OBJ-02 – Tương thích  | FR-BUILD-01..05, BR-COMP, COMP-\*                                | AC-08, AC-09        |
| OBJ-03 – AI có căn cứ | FR-CHAT, FR-HYDE, BR-AI                                          | AC-10               |
| OBJ-04 – So sánh HyDE | FR-EVAL, NFR-REPRO                                               | AC-11               |
| OBJ-05 – Vận hành     | FR-ADMIN-01..06, FR-AUDIT                                        | AC-04, AC-06, AC-12 |
| Bảo mật/hiệu năng     | NFR-\*                                                           | AC-12..14           |

# 14. Kế hoạch triển khai MVP

| **Sprint** | **Phạm vi**                                               | **Đầu ra**                                    |
|------------|-----------------------------------------------------------|-----------------------------------------------|
| 0          | Chốt schema, wireframe, coding standard, CI, dữ liệu mẫu. | ERD, API contract, seed catalog, test plan.   |
| 1          | Auth, RBAC, hồ sơ, địa chỉ; catalog admin.                | Đăng ký/OTP/login; CRUD category/product/SKU. |
| 2          | Storefront, search/filter, PDP, favorites/compare.        | Luồng khám phá sản phẩm responsive.           |
| 3          | Cart, voucher, shipping quote, checkout, order, stock.    | Luồng COD hoàn chỉnh và race test.            |
| 4          | Payment sandbox, tracking, cancel/return; admin order.    | Hậu mãi và webhook idempotent.                |
| 5          | Build editor, rule engine, lưu/so sánh/add-to-cart.       | Bộ test tương thích.                          |
| 6          | Chatbot RAG/HyDE, handoff, index/evaluation.              | Báo cáo 200 câu và dashboard.                 |
| 7          | Hardening, E2E, performance, security, tài liệu.          | Release candidate và biên bản nghiệm thu.     |

# 15. Giả định và câu hỏi mở

## 15.1 Giả định baseline

- MVP là mô hình một nhà bán; “Seller page” trong file tham chiếu được chuyển thành trang thương hiệu/cửa hàng, chưa có onboarding marketplace.

- COD được triển khai thật ở mức nghiệp vụ; cổng điện tử dùng sandbox nếu không có tài khoản merchant.

- Thuế đã nằm trong giá hiển thị theo baseline; nếu cần tách VAT phải chốt trước thiết kế totals.

- Tồn kho một địa điểm; mở rộng đa kho sẽ cần InventoryLocation và allocation.

- Chatbot yêu cầu khách đăng nhập theo quyết định brainstorm; catalog và build thủ công vẫn có thể xem trước khi đăng nhập.

## 15.2 Câu hỏi cần chốt trước Sprint 1

| **ID** | **Câu hỏi**                                        | **Giá trị mặc định để code**                                     |
|--------|----------------------------------------------------|------------------------------------------------------------------|
| OQ-01  | Website một nhà bán hay marketplace nhiều nhà bán? | Một nhà bán.                                                     |
| OQ-02  | Cổng thanh toán và đơn vị vận chuyển nào?          | Adapter + mock/sandbox; COD bắt buộc.                            |
| OQ-03  | Chính sách hủy/trả và thời hạn cụ thể?             | Cấu hình admin; khách tự hủy trước PACKING.                      |
| OQ-04  | Giá đã gồm VAT?                                    | Đã gồm VAT; không tách dòng thuế.                                |
| OQ-05  | Giữ tồn ở lúc tạo đơn hay khi thanh toán?          | Giữ khi xác nhận đơn; timeout đơn chưa thanh toán theo cấu hình. |
| OQ-06  | Top-k và chỉ số retrieval chính?                   | top-k=5; nDCG@10 hoặc MRR chốt trước thí nghiệm.                 |
| OQ-07  | Ai gán nhãn bộ 200 câu?                            | Nhóm đồ án, đối soát bởi người có kiến thức phần cứng.           |

# Phụ lục A – Backlog theo Epic

| **Epic**                       | **Phạm vi**                                                       |
|--------------------------------|-------------------------------------------------------------------|
| EPIC-01 Identity & Account     | FR-AUTH, FR-ACC, FR-ADDR                                          |
| EPIC-02 Catalog & Discovery    | FR-HOME, FR-CAT, FR-SEARCH, FR-FILTER, FR-PDP, FR-FAV, FR-COMPARE |
| EPIC-03 Cart & Promotion       | FR-CART, FR-VOUCHER                                               |
| EPIC-04 Checkout & Fulfillment | FR-SHIP, FR-CHK, FR-PAY, FR-ORDER, FR-TRACK                       |
| EPIC-05 After-sales            | FR-ORDER-03, FR-RETURN                                            |
| EPIC-06 PC Builder             | FR-BUILD, COMP-\*                                                 |
| EPIC-07 Conversational AI      | FR-CHAT, FR-HYDE, FR-LEAD, FR-EVAL                                |
| EPIC-08 Administration         | FR-ADMIN, FR-AUDIT                                                |
| EPIC-09 Quality                | NFR, AC, observability, security, test automation                 |

# Phụ lục B – Definition of Done

- Acceptance criteria được tự động hóa ở mức phù hợp và QA xác nhận.

- API có validation, authorization, error model và tài liệu contract.

- Migration/seed chạy được trên môi trường sạch; không có secret trong code.

- Unit/integration test đạt; không phát sinh lỗi nghiêm trọng từ security/lint scan.

- UI responsive và có trạng thái loading/empty/error; kiểm tra keyboard cơ bản.

- Mutation quan trọng có audit/log/trace; metric cần thiết đã được instrument.

- Pull request được review; tài liệu SRS/API/test case cập nhật nếu thay đổi yêu cầu.

# Phụ lục C – Tài liệu tham khảo

| **Nguồn**                                                                               | **Cách sử dụng**                                                                                                                    |
|-----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| Doan-brainstorm.md                                                                      | Phạm vi chatbot build PC, vai trò, luồng, rule, 500 sản phẩm, 200 câu hỏi và ngưỡng đánh giá.                                       |
| Website consumer.xlsx                                                                   | Danh sách chức năng storefront và phần mềm nhân viên: auth, homepage, catalog, cart, payment, account, order và product management. |
| DeCuongDATN_25410227_NguyenHuuHuy_25410341 \_NguyenThiNgocVy(3).docx                    | Bối cảnh đề cương đồ án và định hướng hệ thống.                                                                                     |
| Gao et al. (2023), Precise Zero-Shot Dense Retrieval without Relevance Labels, ACL 2023 | Cơ sở HyDE: sinh hypothetical document, embedding và truy xuất tài liệu thật; nội dung giả định có thể hallucinate.                 |
| ISO/IEC/IEEE 29148                                                                      | Tham chiếu cấu trúc và nguyên tắc đặc tả yêu cầu.                                                                                   |
