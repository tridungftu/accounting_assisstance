# M2-BR0 · Kiểm kê nhận hóa đơn bán ra cho M3 (CD-013)

26/10/2026 · `lat/m2-br0@881ba6d`; đối chiếu `lat/m3-1a@59c0632` bằng `git show`. **Kết luận:** reader/bộ tải biết chiều bán; promote M2 chỉ nhận mua. Cần mở quyền, projector, khóa batch; tiền/quan hệ còn thiếu để đối chiếu M3.

**Quy ước tệp:dòng:** các đường dưới đây thuộc `src/kho_tri_thuc/`, trừ khi ghi khác: `SQL` = `ha_tang/pg_migrations.py`; `HD` = `k2/hoa_don.py`; `XML` = `nguon/hoa_don_xml.py`; `Q` = `k2/quyen.py`; `HTTP` = `giao_dien/server.py`; `TCT` = `giao_dien/m2_tai_hoa_don.py`; `DP`/`NH` = `m2/tai_hoa_don/dieu_phoi.py`/`nhan.py`; `UI` = `giao_dien/assets/`. Số dòng theo hai revision trên.

## 1. Điểm cố định mua vào và điểm thực tế đã hỗ trợ bán — trang 1/2

| Vùng | Bằng chứng và hệ quả |
|---|---|
| Chiều / CHECK | Không có enum chiều chung: Python dùng chuỗi. `HD:276–279` giữ bán là `SOURCE_CANDIDATE`; `HD:298` ghi cứng mua. `SQL:5243` CHECK duy nhất `MUA_VAO`; `SQL:5945–5959` kiểm, INSERT và tra danh tính đều cố định mua. |
| Khóa batch / core | M0016 chèn lại đường khóa batch: `SQL:8166–8180` tiếp tục lọc/INSERT/JOIN mua; ghép vào consumer tại `SQL:8209–8211`. `SQL:5971` tạo `HD_MUA`; `SQL:5141` chỉ nhận core `HD_MUA` thuộc M2. `HD_BAN` đã có trong loại core (`SQL:210`) nhưng chưa được projector M2 dùng. |
| Mapping công ty | `HD:124–142` dùng COMPANY đã duyệt, đúng profile/hiệu lực; thiếu hoặc nhiều mapping → HOLD. Mapping không cố định mua; điểm chặn là kế hoạch sau resolve (`HD:265–298`). `SQL:5064` còn buộc identity ứng viên mapping dòng là mua. |
| RLS / vai | `SQL:6460` đọc bảng hóa đơn theo pháp nhân + module **M2**, không phân biệt chiều; mapping tại `SQL:6468` cũng quy về M2. `Q:43–50` chỉ có quyền M2 chung, CFO + V4 cho map/route/review. Hàm đọc/DEFINER kiểm M2 (`SQL:5798,5810,6105,6153`). Chưa có quyền bán/doanh thu riêng. |
| Route nghiệp vụ / HTTP | `HD:35`, `SQL:5500,6297`, `UI/app.js:1250` chỉ có đích `CHI_PHI/XDCB_241/TAI_SAN/KHO`. HTTP nhận XML/ZIP chung (`HTTP:765–781`), danh sách chưa lọc chiều (`HD:505–525`, `HTTP:728`). Mở schema có thể làm bán lọt tuyến mua. L11 chặn mua tại `SQL:7565`, không nên nới để phục vụ M3. |
| Giao diện | `UI/index.html:137,176` ghi “Hóa đơn mua”, bán chỉ là ứng viên. Bộ tải lại có chọn bán/cả hai: `UI/m2_tai_hoa_don.js:18,411`. |
| Bộ tải cổng thuế | **Không chỉ hỗ trợ mua:** `TCT:59`, `DP:45` có `purchase/sold`; `TCT:953,960` tách thư mục và kiểm chiều manifest; `NH:136–144` kiểm thư mục rồi chuyển thành `MUA_VAO/BAN_RA`. `tools/source7_m2_patch/config.js:23–29`, `src/job.js:714`, `src/portal.js:302–305`, `src/manifest.js:33` (đều dưới cùng thư mục patch) đã tải theo chiều, nhóm và thư mục riêng. Chưa kiểm hoạt động cổng thực tế. |

## 2. Dùng lại được gì, giới hạn ở đâu

- **XML/ZIP và danh tính:** giữ parser bytes, giới hạn an toàn, raw hash/locator/ordinal ZIP (`XML:59–62,955,963`). XOR từng company key đã so MST người mua/người bán (`XML:834–843`); khóa là **PN + chiều + MST bán + mẫu + ký hiệu + số chuẩn**, bỏ số 0 đầu bằng chuỗi (`XML:821–843`, `SQL:5254`). MST mua nằm trong header (`XML:777–778`), không thuộc unique identity. Không thêm MST mua vào khóa: sửa nội dung phải thành revision cùng hóa đơn.
- **Nguồn/raw/receipt:** dùng nguyên capture → stage → consumer → finalizer (`HD:394–429`), replay bất biến (`HD:446–451`), raw theo quyền nguồn (`HD:463–475`). Kho đã có version theo semantic, quan sát theo delivery, raw/container/entry và ba con trỏ latest/accepted/eligible (`SQL:5256–5335,5990–6014`). 
- **Tiền chưa dùng nguyên được:** có sẵn cột `net_minor/tax_minor/total_minor/other_minor/non_taxable_minor` nhưng CHECK buộc toàn bộ NULL, `money_basis_state=UNPROVEN_NO_MINOR` (`SQL:5271–5282`). Chỉ giữ raw dòng `DGia/ThTien/TSuat` (`HD:301–303`); `TToan` bị đánh dấu unsupported và chặn semantic (`XML:799–803,852–856`). Chưa có net chịu thuế chuẩn hóa; không coi `net_minor` là net chịu thuế hoặc suy giá đất từ tổng trừ VAT.
- **Điều chỉnh/thay thế:** dùng lại trích raw `TTHDLQuan` và locator (`NH:88–114`), nhưng `NH:33` xác nhận chưa ghi quan hệ vào K2; strict reader chưa có tag đó trong allowlist (`XML:42,69`). `supersedes_id` chỉ nối phiên bản nội dung cùng danh tính (`SQL:5292–5293`), không thay liên kết hóa đơn pháp lý khác số. Trạng thái thuế vẫn `UNKNOWN` (`SQL:5314`).

<div style="page-break-after: always;"></div>

## 3. Phần phải bổ sung — trang 2/2

1. **Chiều:** MST bán khớp COMPANY đã duyệt của PN → `BAN_RA`; hai phía/không khớp/xung đột → HOLD. Nội bộ tập đoàn: bán PN A, mua PN B là hai danh tính riêng. SQL kiểm lại chiều/header/mapping, không tin UI/thư mục.
2. **Quyền:** kế toán bán hàng/doanh thu theo PN + chiều, đồng nhất Python/RLS/DEFINER/API/raw. Không cấp toàn M2 để người xem M3 vượt RLS. Giữ quyền nguồn `INTAKE/READ_SOURCE/SOURCE_MAP` riêng; ZIP nhiều PN/chiều cần scope phù hợp.
3. **Tách luồng:** lọc chiều phía máy chủ; SQL/UI chặn bán vào tuyến mua/L11. Projector chọn `HD_MUA/HD_BAN`, owner M2, chưa hạch toán. Giữ `purchase/sold`, thư mục/manifest/receipt riêng, dùng chung parser/kho.
4. **Chống trùng:** giữ unique identity/semantic/delivery (`SQL:5254,5288–5289,5324`) và khóa M0016. Cổng/file xuất cùng hóa đơn: một identity, nhiều quan sát; khác nội dung → HOLD. Receipt ứng viên cũ bất biến, retry không tự promote (`HD:403–406,446–451`); xử lý lại cần audit/receipt mới nối raw gốc, vẫn dedup.
5. **M3:** bổ sung tiền exact/currency/precision và quan hệ có phiên bản, thiếu giữ NULL/PENDING; không tự tính thuế/doanh thu. M3-1a FK ba bảng M2 (`lat/m3-1a:src/kho_tri_thuc/k2/sql_m3.py:80–85`), kiểm bán/currency (`:105–114`); tích hợp phải kiểm thêm tiền/quan hệ/eligible trước xác nhận.

## 4. Đề xuất thứ tự lát (chưa triển khai; mỗi lát ≤ 3 tệp, gồm test)

Các test dưới đây ở `tests/`; tệp mới đánh dấu **mới, dự kiến**. Lead chốt handoff/số migration sau. Dùng migration bổ sung, không sửa lịch sử M0015/M0016 đã áp dụng.

| Thứ tự | Tệp được đụng (tối đa 3) | Kết quả / điểm kiểm tương lai |
|---|---|---|
| BR1 · Quyền | `Q`; `SQL`; `test_m2_k2.py` | Quyền bán theo PN/chiều; đọc bảng/hàm/raw không lộ mua hoặc PN khác. |
| BR2 · SQL promote | `SQL`; `test_m2_migrations.py`; `test_m2_k2.py` | Nới CHECK chiều, projector/owner `HD_BAN`, batch khóa, chặn route mua/L11; giữ dedup và bất biến. |
| BR3 · Capture bán | `HD`; `NH`; `test_m2_k2.py` | Kế hoạch bán vào consumer chung, kiểm manifest, xử lý lại nguồn cũ có audit; không tự thêm hồ sơ M3. |
| BR4 · Reader tiền/quan hệ | `XML`; `test_hoa_don_xml.py`; `fixtures/m2_ban_ra.xml` (**mới, dự kiến**) | Mở profile/envelope theo mẫu tổng/thuế/quan hệ; exact, thiếu/mơ hồ HOLD; bảo toàn contract cũ. |
| BR5 · Tiền chuẩn hóa | `HD`; `SQL`; `test_m2_k2.py` | Lưu thành phần tiền theo phiên bản và căn cứ currency/precision; không gán NULL thành 0. |
| BR6 · Quan hệ hóa đơn | `HD`; `SQL`; `test_m2_k2.py` | Ghim quan hệ khác identity và trạng thái nguồn; gốc đến sau, thay thế/điều chỉnh không nhân doanh số. |
| BR7 · Nối bộ tải | `DP`; `TCT`; `test_m2_00e_http.py` | Quyền bán + context/receipt khi tải/nhận/replay; không nhầm `purchase/sold`. |
| BR8 · API đọc | `HD`; `HTTP`; `test_m2_http.py` | Lọc chiều, trả tiền/quan hệ/lineage; M3 chỉ tham chiếu, kiểm truy cập trực tiếp bằng ID. |
| BR9 · UI | `UI/index.html`; `UI/app.js`; `m2_ban_ra_ui.cjs` (**mới, dự kiến**) | Tách danh sách/nhãn, hiện nguồn và HOLD; ẩn/chặn tuyến mua cho bán. |

**Rủi ro:** `SQL` chung BR1/2/5/6 và đăng ký migration M3-1a; `HD` chung BR3/5/6/8; `HTTP`/`UI/app.js`/`UI/index.html` chung nhiều module. Gộp tuần tự; chỉ mở khi quyền/SQL/API/UI đồng bộ. Đổi envelope cần version profile/semantic (CHECK `SQL:5261`), tránh revision giả/phá mua. Test tương lai: mua, hai PN, XML/ZIP/cross-source/replay, thu hồi quyền, tiền âm/thiếu/ngoại tệ, quan hệ gốc đến sau. **BR0 không chạy test.**

## 5. Cần Anh (ghi để lead chốt, không hỏi trong lát này)

- **Nguồn ưu tiên:** A — cổng thuế (đường tải có sẵn, cần xác minh đủ nhóm/trạng thái); B — XML/ZIP xuất từ phần mềm hóa đơn tập đoàn (cần mẫu/profile); C — cả hai (cần xác định nguồn quyết định khi lệch). Đề xuất dùng XML/ZIP của nguồn sẵn có trước; nguồn thứ hai chỉ bật sau kiểm chống trùng.
- **Người chịu trách nhiệm:** ai được nhận/xem bán theo PN, ai xác nhận nguồn/ngoại lệ; người xem M3 có được mở raw hay chỉ dữ liệu đã lọc. Không tự chuyển quyền CFO mua sang kế toán bán.
- **Mẫu/căn cứ:** bộ XML giả lập đại diện tiền chịu thuế/không chịu thuế, đất được trừ, điều chỉnh/thay thế/hủy, ngoại tệ và nguồn ưu tiên khi mâu thuẫn; kế toán thuế xác nhận cách thể hiện theo thiết kế M3 v2 §6/#7. Chưa đủ thì NULL/PENDING, chưa nghiệm thu đối chiếu.

Căn cứ: thiết kế `M3-HOA-DON-BAN-VA-DOANH-THU-v2-20261026.md` §4/§6, thư mục thiết kế cấp tập đoàn: **không tạo kho M3 song song**. BR0 chỉ đọc mã/tài liệu; không đọc `var/`/bí mật, không gọi dịch vụ/DB/server.
