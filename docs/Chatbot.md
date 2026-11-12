# Chạy chatbot Qwen3-4B theo đề cương ver2

Pipeline thực hiện trích nhu cầu → hỏi bổ sung → phân bổ ngân sách → HyDE + truy xuất lai → chọn linh kiện bằng luật → diễn đạt kết quả. Xem [kiến trúc](architecture.md) và [ERD](database-erd.md).

## Ghi chú yêu cầu hội thoại tư vấn PC

**Mô tả do HyDE tạo chỉ dùng để tìm kiếm; giá, tồn kho và thông số phải lấy từ dữ liệu sản phẩm thực tế.** Không dùng nội dung giả định của HyDE làm dữ liệu sản phẩm hoặc bằng chứng xác nhận cấu hình.

Khi khách muốn mua máy tính hoặc nhờ tư vấn cấu hình PC, phải xác định đủ hai nhu cầu bắt buộc trước khi tìm kiếm sản phẩm:

1. **Ngân sách dự kiến.**
2. **Mục đích sử dụng chính:** học tập, văn phòng, chơi game, đồ họa hoặc nhu cầu cụ thể khác.

Nếu còn thiếu một trong hai thông tin, chỉ hỏi bổ sung phần còn thiếu; **chưa chạy HyDE, chưa truy xuất sản phẩm và chưa đề xuất cấu hình**. Không tự mặc định ngân sách hoặc mục đích sử dụng. Nếu khách đã cung cấp thông tin trong hội thoại hiện tại thì sử dụng lại, không hỏi lặp.

Mẫu trả lời khi khách chỉ nói “Tôi cần mua máy tính”:

> Dạ em chào anh/chị! Em có thể giúp anh/chị chọn cấu hình PC phù hợp.
> Anh/chị dự định đầu tư khoảng bao nhiêu cho bộ máy ạ?
> Anh/chị dùng máy chủ yếu để làm gì ạ?

Câu hỏi bổ sung là câu mẫu cố định (`advisor/requirements.py`). Mỗi câu kèm nút chọn nhanh (`quick_replies` trong phản hồi API), ví dụ "Khoảng 25 triệu", "Chơi game", "Chưa gồm màn hình, phím chuột", "Không cần Windows bản quyền"; bấm nút sẽ gửi đúng câu đó như tin nhắn của khách. Nút chỉ hiện ở tin nhắn cuối.

Backend chặn cả HyDE và truy xuất (kể cả nhánh tra cứu sản phẩm) khi thiếu ngân sách hoặc mục đích sử dụng. Chỉ hỏi phần còn thiếu trước khi hỏi thêm về ngoại vi và bản quyền.

## Chuẩn bị

Docker Desktop chạy Linux containers, GPU NVIDIA và driver/WSL2 hỗ trợ GPU. Compose yêu cầu GPU cho Ollama; embedding/reranker chạy CPU. Muốn chạy CPU toàn bộ thì bỏ `gpus: all`, nhưng cần đo lại độ trễ.

Sao chép `.env.example` thành `.env`, điền `DJANGO_SECRET_KEY` và `POSTGRES_PASSWORD` bằng giá trị ngẫu nhiên dài. Không ghi đè file .env đang chứa cấu hình cần giữ. Build cần mạng để tải image/thư viện; bước tải trọng số chỉ thực hiện một lần. Runtime mặc định tắt truy cập Hugging Face và không dùng Ollama Cloud.

```bash
docker compose -f docker-compose.advisor.yml up -d --build   # ollama-init tự pull + create model lần đầu
docker compose -f docker-compose.advisor.yml exec -e HF_HUB_OFFLINE=0 backend python manage.py download_advisor_models
docker compose -f docker-compose.advisor.yml exec backend python manage.py createsuperuser
```

Service `ollama-init` chạy một lần: nếu chưa có `techzone-qwen3-4b` thì tải `qwen3:4b-q8_0` (~4,4GB, cần mạng) và tạo model từ `docker/advisor/Modelfile`; đã có thì thoát ngay, nên các lần khởi động sau chạy offline. Backend chỉ khởi động sau khi bước này thành công. Sau khi sửa Modelfile, chạy lại `docker compose -f docker-compose.advisor.yml exec ollama ollama create techzone-qwen3-4b -f /models/Modelfile`. Image Ollama được ghim `0.40.13` để thực nghiệm tái lập được; nâng cấp có chủ đích và chạy lại đánh giá.

Chạy backend ngoài Docker: `pip install -r src/backend/requirements.txt -r src/backend/requirements-advisor.txt` (file thứ hai chứa sentence-transformers/PyTorch cho BGE-M3 và reranker; trên Linux cài `torch` bản CPU trước). Image một container ở `Dockerfile` gốc chỉ chạy cửa hàng, không có chatbot.

Mở `http://localhost:8080`. Backend tự chạy migration khi khởi động. Chỉ web mở cổng host; PostgreSQL, Redis, Ollama dùng mạng nội bộ. Context 8192 thuộc Modelfile; flash attention, KV q8_0 và hai phiên song song thuộc service Ollama. Cấu hình GPU thực tế cần kiểm tra bằng `docker compose -f docker-compose.advisor.yml exec ollama ollama ps`.

Compose tạo database mới trong volume riêng. Không tự di chuyển/xóa dữ liệu trong container `techzone` cũ. Trước khi chuyển dữ liệu production cần backup, đối chiếu phiên bản PostgreSQL và thử restore.

## Chuẩn hóa và nhúng sản phẩm

Giá/tồn hiện có nằm trong `Product.payload`; chatbot chỉ lấy sản phẩm active, stock nguyên dương và price nguyên dương. Không biết tồn kho thì loại khỏi tư vấn. Không suy ra socket/iGPU/TDP từ tên model.

Giữ các thuộc tính tiếng Việt hiện tại; ưu tiên `payload.specs` khi có. Định dạng JSON nhập là danh sách, mỗi phần tử có `id` hoặc `sku`, `name`, `brand`, `cat`, `price`, `stock`, `description`, `specs`. Giá là VND nguyên, tồn kho là số lượng nguyên. Danh mục dùng cpu/mainboard/ram/gpu/cooler/ssd/psu/case/license hoặc nhãn cửa hàng tương ứng.

| Nhóm | Khóa specs |
|---|---|
| CPU | socket, cores, threads, boost_ghz, tdp_w, has_igpu, stock_cooler |
| Mainboard | socket, chipset, form_factor, ram_type, ram_slots, max_ram_gb, m2_slots |
| RAM | ram_type, capacity_gb, modules, speed_mhz |
| GPU | chip, vram_gb, tdp_w, length_mm |
| Cooler | cooler_type, sockets, height_mm, tdp_w |
| SSD | interface, capacity_gb, pcie_gen |
| PSU | watt, efficiency, modular |
| Case | supported_mb, max_gpu_length_mm, max_cooler_height_mm |

Các số không kèm đơn vị trong giá trị; dùng W, mm, GB theo tên khóa. `has_igpu`, `stock_cooler`, `modular` là boolean thật; `sockets`, `supported_mb` là mảng chuỗi. `capacity_gb` của RAM là tổng dung lượng một kit, `modules` là số thanh trong kit. `interface` dùng nvme/sata, `cooler_type` dùng air/liquid (chấp nhận cả aio). R11 chỉ so chiều cao với tản khí; với tản nước, R11 là cảnh báo "cần kiểm tra vị trí lắp radiator" và không chặn cấu hình, nên tản nước không cần `height_mm`.

### Nhập bằng Excel (CSV)

Lệnh nhập nhận cả `.json` và `.csv`. Mở `data/import-template.csv` bằng Excel (chỉ có dòng tiêu đề), điền mỗi sản phẩm một dòng rồi lưu dạng **CSV UTF-8**. Xem `data/import-example.csv` cho mỗi nhóm linh kiện một dòng mẫu (tên có “[VÍ DỤ]”, `active=không`, số liệu chỉ để minh họa định dạng).

| Cột | Ghi chú |
|---|---|
| `id` hoặc `sku` | Bắt buộc, duy nhất, ≤ 64 ký tự. Nhập lại cùng id là cập nhật. |
| `name`, `category`, `price`, `stock` | Bắt buộc. `category`: cpu, mainboard, ram, vga/gpu, tản nhiệt/cooler, ssd, hdd, nguồn/psu, case, bản quyền/license… Giá ghi `2990000` hoặc `2.990.000`. |
| `brand`, `old`, `active`, `img`, `description` | Tùy chọn. `old` là giá gốc; `active` có/không (bỏ trống = giữ nguyên). |
| Cột thông số | Theo bảng khóa ở trên. Ô trống = chưa có dữ liệu (luật sẽ báo “chưa xác minh”, không chặn nhầm). Có/không cho has_igpu, stock_cooler, modular. Danh sách (`sockets`, `supported_mb`) ngăn bằng dấu `;`. |

Lệnh nhập tự chuẩn hóa để luật so khớp được: socket bỏ khoảng trắng và viết hoa (`LGA 1700` → `LGA1700`), kích thước mainboard về ATX / Micro ATX / Mini ITX / E-ATX (nhận `mATX`, `micro-atx`, `ITX`…), chuẩn RAM về DDR3/DDR4/DDR5 (mainboard hỗ trợ hai loại ghi `DDR4/DDR5`), `interface` về nvme/sata, `cooler_type` về air/liquid (nhận `khí`, `nước`, `AIO`), số bỏ đơn vị (`360 mm` → 360, `4,4 GHz` → 4.4). Giá trị không nhận ra (ví dụ `DDR5-6000`, kích thước mainboard lạ) bị từ chối.

Lệnh kiểm tra toàn bộ file và liệt kê **tất cả** lỗi một lượt; có lỗi thì không ghi gì. Khi cập nhật sản phẩm đã có, các trường file không có (giá vốn, giá gốc, ảnh tải lên trong admin) được giữ nguyên; sản phẩm đã phân kho giữ tồn kho tính từ module Kho, không lấy số `stock` trong file. Lệnh không xóa sản phẩm; muốn ngừng bán thì nhập `active=không`.

Copy file dữ liệu vào container rồi kiểm tra, nhập và nhúng (Git Bash trên Windows cần `MSYS_NO_PATHCONV=1` để giữ đường dẫn `/tmp`):

```bash
docker compose -f docker-compose.advisor.yml cp products.json backend:/tmp/products.json
docker compose -f docker-compose.advisor.yml exec backend python manage.py import_advisor_catalog /tmp/products.json --dry-run
docker compose -f docker-compose.advisor.yml exec backend python manage.py import_advisor_catalog /tmp/products.json
docker compose -f docker-compose.advisor.yml exec backend python manage.py index_advisor_catalog
```

`index_advisor_catalog` nhúng theo lô 16 sản phẩm và chỉ nhúng sản phẩm có tên/thông số/mô tả thay đổi; `--force` để nhúng lại toàn bộ.

Lệnh nhập chỉ upsert các mã trong file, không xóa sản phẩm khác. Giá/tồn đọc trực tiếp từ DB, không nằm trong nội dung embedding. Sau khi đổi mô tả/specs/tên/hãng/danh mục, chạy lại lệnh index; vector cũ không được dùng trong truy xuất ngữ nghĩa. Không cần index lại khi chỉ đổi giá/tồn.

## Hội thoại và giỏ hàng

- Tối đa hai câu hỏi mẫu mỗi lượt. Ngân sách/mục đích không có mặc định. Hai trường ngoại vi/bản quyền mặc định false sau hai lần hỏi riêng từng trường, kèm giả định rõ ràng.
- Nhu cầu chơi game/đồ họa/video/AI phải chọn được GPU. Văn phòng/học tập/lập trình ưu tiên CPU có iGPU và không chọn GPU rời.
- Chọn linh kiện từng nhóm (đề cương 3.3.3): lấy sản phẩm còn hàng, giá trong hạn mức; ưu tiên sản phẩm nằm trong top-K kết quả truy xuất sau reranker (`ADVISOR_ASSEMBLY_TOP_K`, mặc định 5), sau đó giá cao nhất; chọn sản phẩm đầu tiên không vi phạm luật mức lỗi.
- Trừ 20% ngân sách khi gồm màn hình/phím/chuột. Khoản này là dự phòng, chưa phải sản phẩm được thêm giỏ. Bản quyền trừ giá sản phẩm license rẻ nhất còn hàng.
- Lỗi hoặc chưa xác minh ở luật error chặn xác nhận cấu hình; warning được hiển thị. Không tìm được linh kiện thì báo thiếu và đề nghị điều chỉnh, không tự tạo sản phẩm.
- Hai yêu cầu đồng thời của cùng tài khoản bị chặn. Rate limit 5 yêu cầu/phút dùng Redis. Lịch sử bền vững theo tài khoản, hội thoại mới không xóa lịch sử cũ.
- Thêm cả bộ kiểm tra lại cả giỏ hiện có bằng giá/tồn DB. Giỏ đã có linh kiện trùng nhóm có thể cần được điều chỉnh trước khi thêm. Sửa số lượng ở thanh toán sẽ chạy kiểm tra backend lại.
- Nút "Đổi" trên từng linh kiện của cấu hình đề xuất (chỉ ở tin nhắn cuối) mở danh sách sản phẩm cùng nhóm còn hàng. Chọn một sản phẩm sẽ gửi `swap: true` kèm id đó; backend ghim sản phẩm và để thuật toán luật chọn lại các nhóm còn lại, nên cấu hình mới vẫn qua R1–R14. Tiền chênh lệch được phân bổ lại cho nhóm khác.
- Đây không phải cơ chế giữ hàng; tồn kho có thể đổi sau tư vấn. Luồng tạo đơn hàng hiện tại chưa được thay bằng hệ thống giữ tồn kho giao dịch.

## Độ trễ

Đo trên RTX 5060 8GB, catalog mẫu 30 sản phẩm còn bán (10/11/2026): một lượt đề xuất mất 11–14 s khi server đã chạy sẵn, trong đó ba lần gọi Qwen3 (trích nhu cầu, HyDE, viết câu trả lời) chiếm khoảng 7 s. Các biện pháp đang bật:

- `OLLAMA_KEEP_ALIVE=-1`: giữ Qwen3 thường trực trên GPU (mặc định Ollama gỡ model sau 5 phút rảnh, nạp lại mất ~9 s).
- `ADVISOR_WARMUP=true`: khi gunicorn khởi động, luồng nền nạp sẵn Qwen3, BGE-M3 và reranker, nên lượt chat đầu không phải chờ nạp model.
- Reranker bỏ qua khi chỉ có 0–1 ứng viên và giới hạn đầu vào 512 token.

Giới hạn đã biết: reranker bge-reranker-v2-m3 trên CPU 4 nhân mất ~0,3–0,45 s mỗi cặp và gọi riêng cho từng nhóm linh kiện. Với catalog thật (20–50 ứng viên mỗi nhóm), bước này sẽ vượt xa mục tiêu 10 s; cần chạy reranker trên GPU hoặc quyết định dựa trên kết quả TN2 (có/không reranker).

## API

| Endpoint | Mục đích |
|---|---|
| GET /api/chat/ | CSRF token, 12 tin gần nhất, phiếu nhu cầu |
| POST /api/chat/ | `{"message":"Build PC 25tr","product_ids":[]}` |
| POST /api/chat/ (đổi linh kiện) | `{"message":"Đổi RAM sang …","product_ids":["id-mới"],"swap":true}`: ghim đúng 1 sản phẩm, luôn lắp lại cấu hình (không đi nhánh tra cứu) |
| DELETE /api/chat/ | Đóng phiên đang dùng, bắt đầu hội thoại mới |
| GET /api/chat/sessions/ | Danh sách 50 hội thoại gần nhất của tài khoản |
| GET /api/chat/sessions/{id}/ | Đọc lịch sử của chủ sở hữu |
| POST /api/chat/sessions/{id}/ | Khôi phục hội thoại để tiếp tục |
| POST /api/advisor/validate/ | `{"items":[{"id":"sku","quantity":1}]}`; đọc lại giá/tồn và rules |

POST chat trả `answer`, `products`, `checks`, `stage` (clarification/lookup/recommendation), `requirements`, `can_add_to_cart`, `latency_ms`. Khi hỏi bổ sung có thêm `questions` và `quick_replies` (`[{"question": "...", "options": ["...", ...]}]`). Kết quả cấu hình có thêm `total`, `peripheral_reserve`, `component_budget`, `errors`. Khi thiếu nhóm linh kiện bắt buộc có thêm `alternatives` (đề cương 1.2, mục 4): `missing` là từng nhóm còn thiếu kèm sản phẩm rẻ nhất lắp được và số tiền vượt hạn mức (`over_by`), `other_brand` là CPU hãng khác trong hạn mức, `min_build_total` là giá bộ rẻ nhất lắp được từ hàng còn bán, `budget_shortfall` là số tiền ngân sách linh kiện còn thiếu. Các giá trị này do `advisor/assembly.py` tính bằng luật, LLM chỉ diễn đạt lại. Các giá trị số và checks do backend tính, không lấy từ câu trả lời của LLM.

Yêu cầu đăng nhập; POST/DELETE dùng CSRF. 400 dữ liệu sai; 401 chưa đăng nhập; 403 CSRF; 409 đang xử lý yêu cầu trước; 429 quá nhanh; 503 model/index chưa sẵn sàng.

## Đánh giá

Bộ kiểm thử nháp: `data/eval/advisor_eval.jsonl` (180 mẫu: 60 câu mơ hồ, 75 câu đủ thông tin, 45 câu tra cứu), sinh lại bằng `python scripts/build_advisor_eval.py`. Nhãn được sinh từ mẫu câu và đánh dấu `label_status: "draft"`; theo đề cương, hai thành viên phải gán/duyệt độc lập rồi thống nhất trước khi báo cáo. Mẫu nhóm `complete` chưa có `relevant_product_ids` nên Context Precision/Recall theo ID chỉ tính trên nhóm `lookup` cho tới khi nhóm gán nhãn thủ công.

Mỗi dòng: `{"id":"vague-001","group":"vague","messages":["Build PC 25tr"],"requirements":{"ngan_sach":25000000,"muc_dich":null,...},"expect_clarification":true,"relevant_product_ids":[],"reference":""}`.

```bash
D=data/eval/advisor_eval.jsonl
# TN1: Qwen3-4B và Qwen3-8B
python src/backend/manage.py evaluate_advisor $D --output results/tn1-qwen4b.jsonl
python src/backend/manage.py evaluate_advisor $D --output results/tn1-qwen8b.jsonl --model qwen3:8b
# TN2: không HyDE / chỉ HyDE / HyDE + câu gốc (mặc định); lặp lại với --no-reranker
python src/backend/manage.py evaluate_advisor $D --output results/tn2-nohyde.jsonl --no-hyde
python src/backend/manage.py evaluate_advisor $D --output results/tn2-hyde-only.jsonl --hyde-mode only
python src/backend/manage.py evaluate_advisor $D --output results/tn2-combined-norerank.jsonl --no-reranker
# TN3: MiniLM-L12-v2 và BGE-M3, cùng kho vector trong bộ nhớ (tìm chính xác, không cần index lại)
python src/backend/manage.py download_advisor_models --baseline   # tải một lần, cần mạng
python src/backend/manage.py evaluate_advisor $D --output results/tn3-minilm.jsonl --embedding-model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
python src/backend/manage.py evaluate_advisor $D --output results/tn3-bgem3.jsonl --embedding-model BAAI/bge-m3
# TN4: LLM tự chọn linh kiện từ ngữ cảnh, so với pipeline thuật toán luật (TN1-qwen4b)
python src/backend/manage.py evaluate_advisor $D --output results/tn4-llm.jsonl --selector llm
```

Chạy các lệnh trong môi trường có DB/model/index, hoặc dùng `docker compose ... exec backend`. Nạp model đối chứng trước và chạy riêng. `--limit N` để chạy thử. Runner không lưu hội thoại thử nghiệm thành lịch sử khách hàng.

Mỗi lần chạy ghi `results/*.jsonl` (từng mẫu, có `user_input`, `response`, `retrieved_contexts`, `reference` để chấm RAGAS) và `results/*.summary.json` gồm: F1 từng trường phiếu nhu cầu, tỉ lệ lỗi tương thích (chạy lại R1–R14 độc lập), tuân thủ ngân sách ±5% ngân sách khả dụng (ngân sách trừ dự phòng màn hình/phím chuột) kèm tỉ lệ không vượt ngân sách, tuân thủ tồn kho, độ chính xác hỏi bổ sung, MAP/recall theo ID và độ trễ trung bình/P95. Với `--selector llm`, sản phẩm LLM chọn vẫn được kiểm tra bằng cùng bộ luật; mã sản phẩm không có trong danh sách được ghi ở `invalid_llm_ids`.

`retrieved_contexts` là top-K sản phẩm mỗi nhóm (cùng `ADVISOR_ASSEMBLY_TOP_K` mà thuật toán chọn linh kiện ưu tiên), gồm tên, hãng, nhóm, giá, tồn kho, specs, mô tả.

### Chấm RAGAS bằng mô hình giám khảo

`scripts/ragas_judge.py` chấm bốn chỉ số RAGAS trên file trace, dùng môi trường Python riêng (ragas 0.2.15 chỉ chạy với langchain 0.3):

```bash
python -m venv .venv-eval
.venv-eval/Scripts/pip install -r scripts/requirements-ragas.txt     # Linux/macOS: .venv-eval/bin/pip
# Giám khảo qua endpoint tương thích OpenAI, chọn một:
#   Ollama:    ollama pull qwen3:14b                       → --base-url http://localhost:11434/v1 --model qwen3:14b
#   llama.cpp: llama-server -m Qwen3-30B-A3B-Q4_K_M.gguf -c 16384 --n-cpu-moe 48 --jinja \
#                --reasoning-format deepseek --port 8081    → --base-url http://localhost:8081/v1 --model qwen3-30b-a3b
.venv-eval/Scripts/python scripts/ragas_judge.py results/tn1-qwen4b.jsonl --dry-run   # kiểm tra dữ liệu
.venv-eval/Scripts/python scripts/ragas_judge.py results/tn1-qwen4b.jsonl --model qwen3:14b --base-url http://localhost:11434/v1
```

- Context Precision (có tham chiếu) và Context Recall dùng `retrieved_contexts` + `reference`; chỉ chấm mẫu có cả hai (nhóm câu mơ hồ dừng ở hỏi lại nên bị bỏ qua).
- Faithfulness và Answer Relevancy dùng dữ liệu mà Qwen3-4B thực sự nhận khi viết câu trả lời (sản phẩm đã chọn, tổng tiền, kết quả kiểm tra, dựng lại từ `result`), chỉ cho mẫu ở bước đề xuất/tra cứu. Answer Relevancy sinh ngược N=3 câu hỏi và dùng BGE-M3 (CPU) để tính cosine.
- Script từ chối chạy nếu mô hình giám khảo trùng mô hình được đánh giá.
- Kết quả: `*.ragas.jsonl` (điểm từng mẫu) và `*.ragas.summary.json` (trung bình từng chỉ số, theo nhóm, số mẫu chấm được, `ragas_mean` chỉ để xếp hạng nhanh). Mẫu giám khảo trả lời sai định dạng thành NaN và không tính vào trung bình; báo cáo kèm `scored_samples`.

Script đã được chạy thử với giám khảo giả lập để kiểm tra luồng dữ liệu; chưa có điểm thật. Không báo cáo điểm nghiên cứu khi chưa chạy với giám khảo thật.

## Kiểm thử và tài liệu kỹ thuật

```bash
python src/backend/manage.py test core.test_chat core.test_advisor --settings=config.test_settings
python src/backend/manage.py makemigrations --check --dry-run --settings=config.test_settings
npm run build
```

Tests logic dùng SQLite và mock model, không cần tải BGE/Qwen. Cần thêm kiểm chứng PostgreSQL/Redis/GPU khi Docker daemon sẵn sàng.

Tham khảo chính thức: [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility), [Modelfile](https://docs.ollama.com/modelfile), [pgvector](https://github.com/pgvector/pgvector), [SentenceTransformer](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html), [CrossEncoder](https://www.sbert.net/docs/package_reference/cross_encoder/model.html).

Kiểm thử tích hợp SQL sau khi Compose đã chạy (tạo database test riêng, không dùng SQLite):

```bash
docker compose -f docker-compose.advisor.yml exec backend python manage.py test core.test_advisor_postgres --settings=config.settings
```

Bốn kiểm thử này xác minh vector round-trip, toàn văn không dấu, lọc lại tồn kho ở SQL và loại vector cũ. Chúng được bỏ qua khi chạy trên SQLite.

Nếu container cũ đang dùng cổng 8080, đặt `SITE_PORT=8081` và `CORS_ALLOWED_ORIGINS=http://localhost:8081` trong `.env`, rồi chạy lại Compose. Không cần dừng container cũ.
