# KS-C · Khảo sát route/API hiện có

**Kết luận:** có thể tận dụng routing, kiểm quyền backend và cơ chế chống lặp của các module K2; **chưa thể coi API hiện tại là API Core đa người dùng**. Ba khoảng trống đáng chú ý là: nhóm `/api/that/...` chưa ràng buộc người thao tác vào phiên xác thực; một số download chỉ kiểm đường dẫn; cơ chế tác vụ dài phân tán giữa xử lý đồng bộ, hàng đợi RAM và hàng đợi PostgreSQL. Căn cứ: `giao_dien/server.py:918`, `giao_dien/server.py:1170`, `giao_dien/operations.py:771`, `giao_dien/operations.py:873`, `k2/crm_doi_chieu.py:371`.

Khảo sát tĩnh trên nhánh `hop-nhat-20261023`, commit `6feb66d`, ngày 30/10/2026. Không sửa tệp, không chạy ứng dụng/test, không gọi dịch vụ hoặc đọc dữ liệu thật. Đã đọc TL 54, TL 55 và CD-026…CD-030; áp dụng TL 54 §14 và quyết định bổ sung CD-028.

## 1. Phạm vi và cách đọc bảng

Các đường dẫn tệp dưới đây tính từ `src/kho_tri_thuc/`. Trong bảng, tên tệp thuộc `giao_dien/` được viết gọn, ví dụ `server.py:980` là **`src/kho_tri_thuc/giao_dien/server.py:980`**. Tệp Review cũ được ghi riêng để tránh nhầm.

Ký hiệu `{a,b}` mở rộng thành từng route; `{id}` là thành phần động. Đây là cách gộp danh mục, không hàm ý backend chấp nhận mọi giá trị.

| Cổng | Danh tính, quyền và pháp nhân được kiểm ở đâu |
|---|---|
| **H** | `Handler.authorize`: Host local, Origin, `Sec-Fetch-Site`; chưa phải xác thực người dùng (`server.py:918`). |
| **A** | H + `X-KTT-Token` chung của ứng dụng; áp cho mọi POST và `/api/*` trừ health (`server.py:928`, `server.py:980`). |
| **K** | A + cookie `ktt_crm` → danh tính phiên RAM (`server.py:193`, `server.py:196`, `server.py:955`); quyền/module/pháp nhân tại K2 (`k2/quyen.py:88`, `k2/quyen.py:116`). |
| **G** | K + dịch vụ CRM G: đặt ngữ cảnh transaction, kiểm MTQ/quyền hồ sơ (`k2/crm_mau.py:136`, `k2/crm_mau.py:166`). |
| **X** | K + M4: danh tính, transaction và quyền dự án/hồ sơ (`k2/xay_dung.py:119`, `k2/xay_dung.py:123`, `k2/xay_dung.py:177`). |
| **T** | K + quyền nguồn, mapping pháp nhân, quyền M2; kiểm lại phiên/quyền quanh IO (`m2/tai_hoa_don/dieu_phoi.py:141`, `m2/tai_hoa_don/dieu_phoi.py:169`, `m2/tai_hoa_don/dieu_phoi.py:337`). |
| **Q** | K + service MTQ/Admin hoặc hàm CSDL công tắc; pháp nhân quản trị vẫn phải kiểm tại backend (`ma_tran_tham_quyen.py:42`, `module_cong_tac.py:73`). |

**Ghi/chạy:** `0` = đọc nghiệp vụ; `1` = ghi CSDL/tệp; `P` = thay phiên RAM, tiến trình hoặc thao tác hệ điều hành; `ĐB` = đồng bộ HTTP; `L` = có thể lâu nhưng vẫn đồng bộ; `N` = chạy nền. Đọc có thể phát sinh audit; factory CRM G còn có thể đánh thức worker G5 (`crm_g.py:287`).

## 2. Danh mục route nối vào shell hiện tại

### 2.1. Shell, tiếp nhận, vận hành và bridge cũ

Các nhánh dưới đây nằm trong `Handler.handle_route` (`server.py:976`).

| Method và đường dẫn | Hàm xử lý, căn cứ | Module/cổng | Ghi/chạy |
|---|---|---|---|
| GET `/api/health` | `handle_route`, `server.py:1003` | Shell/H | 0/ĐB |
| GET `/`, `/index.html`; `/{app.js,style.css,that.css,mark.svg,crm_g.js,m2_tai_hoa_don.js,ma_tran_tham_quyen.js}` | `handle_route`, `server.py:1007`, `server.py:1010` | Shell/H | 0/ĐB |
| GET `/api/state`, `/api/sample`, `/api/files/{id}/download` | `state`, `demo_sample`, `Intake.download`; `server.py:1014`, `server.py:1019` | Tiếp nhận/A | 0/ĐB |
| POST `/api/upload` | `Intake.receive`, `server.py:1143` | Tiếp nhận/A | 1/ĐB |
| GET `/api/that/{job,knowledge,catalog,source-settings,overview,runs,history,cfo-rules,invoice-months,knowledge-cards,report,proposals,quick}` | Các hàm `Operations` tương ứng; `server.py:1023`, `server.py:1055` | Vận hành/A | 0/ĐB |
| GET `/api/that/quick/{run}/download`, `/api/that/outside-catalog/download`, `/api/that/shadow/{id}/{direction}/download` | `quick_file`, `outside_catalog`, `shadow_file`; `server.py:1048`, `server.py:1057`, `server.py:1138` | Vận hành/A | 0/ĐB |
| POST `/api/that/source`, `/api/that/knowledge/import` | `receive_source`, `knowledge_upload`; `server.py:1150`, `server.py:1204` | Vận hành/A | 1/ĐB |
| POST `/api/that/quick/{upload,invoice-month,repropose}` | `Operations.start` + callback tương ứng; `server.py:1156`, `server.py:1162`, `server.py:1166` | Vận hành/A | 1/N, RAM |
| POST `/api/that/{reload,ingest,session/run,shadow/export}` | `reload_sources`/`start`; `server.py:1185`, `server.py:1208`, `server.py:1214`, `server.py:1220` | Vận hành/A | 1/N, RAM |
| POST `/api/that/quick/{decide,ai-note,ai-context,score,export}` | `quick_*`; `server.py:1170` | Vận hành/A | 1/ĐB; có thể L |
| POST `/api/that/{learning-settings,cfo-rules/toggle,cash-mapping,source-settings,knowledge/decide,proposals/decide}` | Các hàm lưu/duyệt tương ứng; `server.py:1188`, `server.py:1201`, `server.py:1211`, `server.py:1217` | Vận hành/A | 1/ĐB |
| POST `/api/that/open` | `open_ai_folder` hoặc `open_export`, `server.py:1196` | Vận hành/A | P/ĐB |
| GET `/api/nghiem-thu` | `nt_list` gọi `dong_bo`; `server.py:1128`, `server.py:137` | Bridge nghiệm thu/A; actor cố định | **1/ĐB** |
| GET `/api/nghiem-thu/sample`, `/api/nghiem-thu/file-soat/{id}` | `nt_sample`, `nt_file`; `server.py:1131`, `server.py:1134` | Bridge/A | 0/ĐB |
| POST `/api/nghiem-thu/{nhan,mau,xac-nhan,quyet-dinh,xuat}` | `nt_receive/seed/confirm/decide/export`; `server.py:1262`, `server.py:1267`; khóa actor tại `server.py:129` | Bridge/A | 1/ĐB |
| POST `/api/demo/{validate,ingest}` | `demo_import`, `server.py:1277` | DEMO/A | validate: 0; ingest: 1/ĐB |
| GET `/api/demo/vai` | `demo_vai`, `server.py:1065` | DEMO/K, có cấp cookie | P/ĐB |
| POST `/api/shutdown` | `handle_route`, `server.py:1282` | Shell/A | P/N |
| OPTIONS mọi đường dẫn | `do_OPTIONS`, `server.py:973` | Shell | Từ chối 403 |

### 2.2. CRM, khung, MTQ và công tắc

Tiền tố trong bảng: **c = `/api/crm`**. Route CRM G được chọn trước handler CRM cũ (`server.py:996`).

| Method và đường dẫn | Hàm xử lý, căn cứ | Cổng | Ghi/chạy |
|---|---|---|---|
| GET `c`; `c/file-soat/{id}` | `crm_state`, `crm_file`; `server.py:1060`, `server.py:1074` | K | Đọc; root có cấp phiên |
| POST `c/{danh-tinh,mau,bo-sung,trich-lai/doi-chieu,trich-lai/xu-ly,xac-nhan-tham-so,kiem,duyet,duyet-v4,tu-choi,mapping,m1-sao-ke,lien-ket,go-lien-ket,file-soat}` | `_crm_action`, `server.py:336` | K | ĐB; `danh-tinh`: P; `trich-lai/doi-chieu`: đọc; còn lại có ghi |
| POST `c/nhan`; `c/trich6` | `crm_receive`, `crm_trich`; `server.py:1232`, `server.py:1223`, `server.py:494`, `server.py:514` | K | 1; trich6: **L**, trả 200 |
| GET `c/hop-dong` | `dieu_huong` → `CrmDanhSachK2.danh_sach`, `crm_g.py:480` | G | 0/ĐB |
| GET `c/mau`, `c/mau/{id}`, `c/mau/so-sanh`, `c/mau/tep/{id}`, `c/bo-chuan` | `dieu_huong`, `crm_g.py:493`, `crm_g.py:500`, `crm_g.py:505`, `crm_g.py:512`, `crm_g.py:600` | G | 0/ĐB |
| POST `c/mau/tai`; `c/mau/{anh-xa,gui-kiem,kiem,tra-lai,duyet,tu-choi,xem-thu}`; `c/bo-chuan/{lap,gui-duyet,duyet}` | `dieu_huong` → `_lenh`; `crm_g.py:608`, `crm_g.py:444`; allowlist `crm_g.py:60` | G | `xem-thu`: đọc; còn lại 1/ĐB |
| GET `c/bao-gia`, `c/bao-gia/{id}`, `c/bao-gia/{mac-dinh,moc-chuan,ty-gia-mac-dinh}`, `c/soan/{id}` | `dieu_huong`, `crm_g.py:518`, `crm_g.py:536`, `crm_g.py:546` | G | 0/ĐB |
| POST `c/bao-gia/{luu,huy,chuyen,xem-truoc,ty-gia-mac-dinh,in}`, `c/soan/{luu,xuat}` | `_lenh_gk`, `_dai_gk`; `crm_g.py:388`, `crm_g.py:406`; allowlist `crm_g.py:74` | G | `xem-truoc`: 0; còn lại 1; `in/xuat`: **L** |
| GET `c/giao-ket/tep/{id}/{docx,pdf}`, `c/giao-ket/ky/{id}`, `c/giao-ket/ban-ky/{id}/tep` | `dieu_huong`, `crm_g.py:551`, `crm_g.py:559`, `crm_g.py:565` | G | Đọc + audit/ĐB |
| POST `c/giao-ket/ky-ket` | `_ky_ket`, `crm_g.py:346`, `crm_g.py:631` | G | 1/L; đánh thức G5 |
| GET `c/giao-ket/kiem`, `c/giao-ket/kiem/{id}`, `c/giao-ket/kiem/{id}/tep/{ban-ky,g3}` | `dieu_huong`, `crm_g.py:574`, `crm_g.py:579`, `crm_g.py:585` | G | Đọc + audit/ĐB |
| POST `c/giao-ket/kiem/{luu,check,xu-ly-lech,bo-sung,hieu-luc,tra-lai,tim-junsky}` | `_lenh_kiem`, `crm_g.py:317`, `crm_g.py:659`; allowlist `crm_g.py:103` | G | 1/ĐB; `tim-junsky` chỉ tra cứu + audit |
| GET `c/giao-ket/doi-chieu/{id}`; POST `c/giao-ket/doi-chieu/{chay,doi-soat,xac-nhan-tay}` | `dieu_huong`, `_lenh_dc`; `crm_g.py:594`, `crm_g.py:308`, `crm_g.py:636`, `crm_g.py:646` | G | GET đọc; POST ghi; `chay/doi-soat`: **N bền**, ACK 200 |
| GET `c/du-an-ban`, `c/du-an-ban/anh-chup`, `c/du-an-ban/{id}`, `c/du-an-ban/{id}/lich-su`, `c/du-an-ban/moc`, `c/du-an-ban/moc/{id}/lich-su` | `_dieu_huong_da`, `crm_g.py:786` | G | 0/ĐB |
| POST `c/du-an-ban/{bat-ban,cap-nhat,phi,lo,moc,ngung-ban,mo-ban-lai,tien-do}` | `_lenh_da`, `crm_g.py:757`; allowlist `crm_g.py:706` | G | 1/ĐB |
| GET `/api/khung/module/crm`; `c/{bao-gia,mau}?trang_thai=...` | `khung_khai_bao.dieu_huong`, `khung_khai_bao.py:170` | G; kiểm SQL tại `khung_khai_bao.py:103` | 0/ĐB |
| GET `/api/tham-quyen/{ma-tran,cua-toi,nhat-ky}`; POST `/api/tham-quyen/{luu-nhap,cong-bo,kich-hoat,phong,gan-vai,pham-vi,admin}` | `dieu_huong`, `ma_tran_tham_quyen.py:42`; danh mục `ma_tran_tham_quyen.py:16` | Q | GET đọc; POST 1/ĐB |
| GET `/api/cong-tac-module/{trang-thai,nguoi-thu}`; POST `/api/cong-tac-module/{che-do,nguoi-thu/cap,nguoi-thu/thu-hoi}` | `dieu_huong`, `module_cong_tac.py:73`; danh mục `module_cong_tac.py:12` | Q | GET đọc; POST 1/ĐB |

### 2.3. M4

Tiền tố **x = `/api/m4`**; handler chung `m4.dieu_huong` (`m4.py:384`).

| Method và đường dẫn | Nhánh/hàm xử lý | Cổng | Ghi/chạy |
|---|---|---|---|
| GET x; `x/{hop-dong,dot,tep}/{id}`; `x/mau`, `x/mau/{ma}` | `trang_thai`, `chi_tiet`, `chi_tiet_dot`, `tai_ve`, mẫu; `m4.py:502`, `m4.py:507`, `m4.py:520` | X | Đọc; root cấp phiên |
| GET `x/{master-hop-dong,master-doi-tac}` | `master_hop_dong/master_doi_tac`, `m4.py:457` | X | 0/ĐB |
| GET `x/{review,chung-tu}`, `x/{review,chung-tu}/{id}`, `x/{review,chung-tu}/{id}/tep/{tep_id}` | `review_*`, `chung_tu_*`; `m4.py:465`, `m4.py:481` | X | 0/ĐB |
| GET `x/duyet`, `x/duyet/{id}/pdf/{pdf_id}`, `x/ke-toan`, `x/ke-toan/{id}`, `x/ke-toan/{id}/phong-bi/{id}/pdf` | `duyet_*`, `kt_*`; `m4.py:425`, `m4.py:442` | X | Đọc/ĐB |
| GET `x/doi-chieu/{dot,lich-su,con-thieu}/{id}` | `_dc_doc`/service ghi nhận, `m4.py:391` | X | 0/ĐB |
| POST `x/tep`, `x/duyet/pdf` | `tai_tep`, `duyet_pdf`; `m4.py:547`, `m4.py:564` | X | 1/ĐB; PDF có thể L |
| POST `x/danh-tinh`; `x/hop-dong/{tao,nhan-master,gan-doi-tac,gan-tep,trich}`; `x/tham-so/{sua,xac-nhan}`; `x/phu-luc/{khai,them,huy}`; `x/boq/{xem,nhap}`; `x/dot/{tao,sua,gan-tep,nop}` | `_lenh`, `m4.py:205`; đổi vai tại `m4.py:596`; allowlist `m4.py:20` | X | `danh-tinh`: P; `boq/xem`: đọc; còn lại 1; `hop-dong/trich`: **L** |
| POST `x/review/{chay,chay-lai,ghep}`; `x/chung-tu/{chay,chay-lai,sua,ghep}`; `x/duyet/{ket-luan,chap-thuan,phien-ban,phien-ban/nop}` | `_review_lenh` → `_lenh`, `m4.py:245`, `m4.py:316`, `m4.py:588` | X | 1/ĐB; xử lý dài vẫn giữ HTTP |
| POST `x/ke-toan/{luu,xac-nhan}`, `x/doi-chieu/{xem,luu,xac-nhan}` | `_rieng` + service tương ứng; `m4.py:532`, `m4.py:574` | X | `doi-chieu/xem`: đọc; còn lại 1/ĐB |
| GET `/api/m4-request`; POST `/api/m4-request/{tao,doi-soat}` | `m4_request.dieu_huong`, `m4_request.py:206` | X; kiểm lại phiên sau lệnh dài tại `m4_request.py:237` | GET đọc; POST có ghi/IO nguồn, **L** |
| GET `/m4.js`, `/m4.css`, `/m4/{review.js,chung-tu.js,m4_duyet_pdf.js,m4_ke_toan.js,m4_request_nhap.js}`, `/m4/fonts/{ten}` | Tài sản allowlist, `m4.py:403`, `m4.py:497` | H | 0/ĐB |

### 2.4. M2, M5/L11, M9

| Method và đường dẫn | Hàm xử lý, căn cứ | Cổng | Ghi/chạy |
|---|---|---|---|
| GET `/api/m2`; `/api/m2/{hoa-don,nguon}/{id}`; `/api/m2/nguon/{id}/raw/{vai_tro}` | `m2_state`, `m2_get`, `m2_raw`; `server.py:1115`, `server.py:771`, `server.py:839` | K + M2 | Đọc; root cấp phiên |
| POST `/api/m2/{danh-tinh,nhan,mapping,mapping-line,nguon/kiem-lai,route}` | `_m2_action`, `server.py:784` | K + M2 | Phiên P; còn lại 1/ĐB |
| POST `/api/m2/lien-ket/{...}` | `_m2_action` gọi `m2.lien_ket`, `server.py:835` | K | Chưa phát hành, có ánh xạ 501 tại `server.py:1292` |
| GET `/api/m5`, `/api/m5/{phieu,nguon}/{id}`, `/api/m5/{kiem-ke,ton-nguon}`, `/api/m5/nguon/{id}/raw/{vai_tro}`, `/api/m5/file-soat/{id}` | `m5_state/get/raw/file`; `server.py:1089`, `server.py:598`, `server.py:723` | K + M5 | Đọc; root cấp phiên |
| POST `/api/m5/{danh-tinh,nhan,mapping,nguon/kiem-lai,xuat-file-soat}` | `_m5_action`, `server.py:615` | K + M5 | Phiên P; còn lại 1/ĐB |
| GET `/api/m5/l11`, `/api/m5/l11/proof`; POST `/api/m5/l11/{danh-tinh,proof/nhan,proof/xac-nhan,proof/huy,ma-hoa,file-soat}` | `l11_state/proof`, `_l11_action`; `server.py:1094`, `server.py:664`, `server.py:718` | K + BOTH/phạm vi L11 | GET đọc; POST P/1, ĐB |
| POST `/api/m5/lien-ket/{preview,xac-nhan,huy}` | `m5_action` → `lien_ket`; `server.py:657`, `k2/kho_so_luong.py:906` | K + L11 | preview: 0; còn lại 1/ĐB |
| GET `/api/m9`, `/api/m9/file-soat/{id}` | `m9_state`, `m9_file`; `server.py:1079`, `server.py:486` | K + M9 | Đọc; root cấp phiên |
| POST `/api/m9/{danh-tinh,mau,anh-xa,anh-xa/anh-huong,anh-xa/dong,lap,pham-vi,kiem,duyet,duyet-v4,tu-choi,m1-sao-ke,goi-y,xem-truoc,xac-nhan,go,file-soat}` | `_m9_action`, `server.py:438` | K + M9 | `goi-y/xem-truoc/anh-xa/anh-huong`: đọc; danh tính P; còn lại có ghi/ĐB |

**Bộ tải M2:** tiền tố **t = `/api/m2/tai-hoa-don`** (`m2_tai_hoa_don.py:46`).

| Method và đường dẫn | Hàm xử lý, căn cứ | Cổng | Ghi/chạy |
|---|---|---|---|
| GET t, `t/{trang-thai,hang-doi,su-kien,manifest,hoa-don}` | `dieu_huong`, `m2_tai_hoa_don.py:1048`; `_trang_thai`, `_su_kien`, `_manifest`, `_hoa_don_lan_tai` | T | Đọc trạng thái; có IO Node/profile; `su-kien`: SSE giữ kết nối |
| POST `t/{khoi-dong,khoi-dong-lai,bat-dau,tai-tat-ca,huy-hang-doi,nhan,doi-soat,mo-thu-muc}` | `dieu_huong`, `m2_tai_hoa_don.py:1069`; handler chi tiết `m2_tai_hoa_don.py:874` | T | P/1; `tai-tat-ca`: N RAM; `bat-dau`: khởi việc Node; `nhan/doi-soat`: ĐB có thể lâu |

Hàng đợi tải tất cả là `_hang_doi` trong RAM và daemon thread (`m2_tai_hoa_don.py:154`, `m2_tai_hoa_don.py:213`). Binding từng run có lưu tệp bất biến; không nên kết luận toàn bộ bộ tải chỉ có RAM (`m2/tai_hoa_don/dieu_phoi.py:255`).

## 3. Route nội bộ, mã Review cũ và client engine

### 3.1. Engine #6 do ứng dụng sở hữu

| Route được mở | Handler/cổng | Ghi/chạy |
|---|---|---|
| GET `/api/trich_xuat/common`, `/api/trich_xuat/{luot}`, `/tai/{rel}` | `HandlerSoHuu.do_GET`; Host/Origin + token riêng + allowlist common/seal; `nguon/trich6_host.py:431`, `nguon/trich6_host.py:498`, `nguon/trich6_host.py:529` | Đọc/ĐB |
| POST `/api/trich_xuat`, `/api/trich_xuat/{luot}/{tep,chay,dung}` | `HandlerSoHuu.do_POST`; kiểm contract/mode và lượt; `nguon/trich6_host.py:510`, `nguon/trich6_host.py:533` | Có ghi/tạo/chạy/dừng việc tại nguồn |

Đây là cổng dịch vụ, không thay quyền người dùng/pháp nhân của consumer. Hàm xử lý nghiệp vụ cuối cùng được kế thừa từ nguồn engine ngoài; **không thấy định nghĩa đầy đủ của nguồn đó trong repo khảo sát** (`nguon/trich6_host.py:410`, `nguon/trich6_host.py:530`).

### 3.2. HTTP server trong bản Review cũ

Có mã server riêng tại `m4/review_goc/may_chu/server.py`; **không nằm trong các nhánh chuyển tiếp của shell hiện tại** (`giao_dien/server.py:982`). Bảng dưới ghi đầy đủ các mẫu route của server này; dòng dẫn chứng thuộc **tệp server Review cũ**.

Các route qua `Handler._xu_ly`, ngoại trừ POST `/api/tat` được xử lý trực tiếp trong `do_POST`. Cả hai đường đều kiểm Host/Origin và yêu cầu `X-HD: 1` cho thao tác ghi; **không thấy kiểm tài khoản/quyền/pháp nhân ở HTTP dispatcher này** (`m4/review_goc/may_chu/server.py:417`, `m4/review_goc/may_chu/server.py:462`, `m4/review_goc/may_chu/server.py:489`).

| Route | Hàm xử lý và dòng trong server Review | Ghi/chạy và căn cứ |
|---|---|---|
| GET `/api/{phien_ban,he_thong,tong_quan,ai,cai_dat,ocr/trang_thai,cai_dat/nhat_ky_gui_ngoai,tham_so}` | `_pb:53`, `_ht:58`, `_tq:63`, `_ai:68`, `_cd:74`, `_ocr_tt:109`, `_cd_nk:189`, `_ts:200` | Đọc/ĐB; các nhánh trạng thái AI/OCR gọi service ngay trong request (`m4/review_goc/may_chu/server.py:53`, `:58`, `:63`, `:68`, `:74`, `:109`, `:189`, `:200`). |
| POST `/api/cai_dat`, `/api/cai_dat/{kiem_tra_ai,thu_cloud,tim_may_ai,khoa}`; DELETE `/api/cai_dat/khoa/{anthropic,openai}`; PUT `/api/tham_so` | `_cd_luu:79`, `_cd_kt:84`, `_cd_thu_cloud:89`, `_cd_tim:94`, `_cd_khoa:99`, `_cd_xoa_khoa:104`, `_ts_luu:205` | Lưu cài đặt/khóa, xóa khóa, lưu tham số: 1/ĐB (`m4/review_goc/may_chu/dich_vu.py:193`, `:298`, `:305`, `:324`). `kiem_tra_ai`, `thu_cloud`: kiểm kết nối, không thấy ghi nghiệp vụ tại hai hàm, **L/ĐB** do chờ lời gọi dịch vụ (`m4/review_goc/may_chu/dich_vu.py:267`, `:276`). `tim_may_ai`: P/N qua QLV (`m4/review_goc/may_chu/dich_vu.py:288`). |
| POST `/api/ocr/chay_thu`, `/api/csdl/{sao_luu,xuat_excel}` | `_ocr_thu:184`, `_cd_sl:194`, `_csdl_xuat:404` | OCR thử: 1/N qua QLV; sao lưu/xuất Excel: 1/L, đồng bộ (`m4/review_goc/may_chu/dich_vu.py:179`, `:799`, `:811`). |
| GET `/api/phu_luc_ai`, `/api/phu_luc_ai/{id}`; POST `/api/phu_luc_ai/{tai_len,chay}`, `/api/phu_luc_ai/{id}/{cap_nhat,hoi_lai_ai,nap}`; DELETE `/api/phu_luc_ai/{id}` | `_plai_ds:124`, `_plai_xem:129`, `_plai_tl:114`, `_plai_chay:119`, `_plai_cn:134`, `_plai_hl:139`, `_plai_nap:144`, `_plai_xoa:149` | GET: 0/ĐB; tải lên/cập nhật/nạp/xóa: 1/ĐB; `chay`, `hoi_lai_ai`: 1/N qua QLV (`m4/review_goc/may_chu/dich_vu.py:1105`, `:1110`, `:1143`, `:1157`, `:1162`, `:1167`, `:1172`, `:1178`). |
| GET `/api/chung_tu`, `/api/chung_tu/{id}`; POST `/api/chung_tu/{tai_len,chay}`, `/api/chung_tu/{id}/cap_nhat`; DELETE `/api/chung_tu/{id}` | `_ct_ds:164`, `_ct_xem:169`, `_ct_tl:154`, `_ct_chay:159`, `_ct_cn:174`, `_ct_xoa:179` | GET: 0/ĐB; tải lên/cập nhật/xóa: 1/ĐB; `chay`: 1/N qua QLV (`m4/review_goc/may_chu/dich_vu.py:1197`, `:1203`, `:1223`, `:1228`, `:1233`, `:1238`). |
| GET `/api/viec`, `/api/viec/{id}`; POST `/api/viec/{id}/dung` | `_viec:211`, `_viec1:216`, `_viec_dung:224` | GET: đọc trạng thái/ĐB; `dung`: P/ĐB, gửi yêu cầu dừng việc (`m4/review_goc/may_chu/server.py:211`, `:216`, `:224`). |
| GET `/api/trich_xuat`, `/api/trich_xuat/{luot}`, `/api/trich_xuat/{luot}/hd/{ten}`; POST `/api/trich_xuat`, `/api/trich_xuat/{luot}/{tep,chay,chay_lai,dung,danh_muc}`; DELETE `/api/trich_xuat/{luot}`, `/api/trich_xuat/{luot}/tep/{ten}` | `_tx_ds:233`, `_tx:243`, `_tx_hd:286`, `_tx_moi:238`, `_tx_tep:253`, `_tx_chay:263`, `_tx_chay_lai:268`, `_tx_dung:273`, `_tx_dm:281`, `_tx_xoa:248`, `_tx_xoa_tep:258` | GET: 0/ĐB; tạo/tải lên/xóa/ghi danh mục: 1/ĐB; dừng: P/ĐB; `chay`, `chay_lai`: 1/N qua QLV, có chuẩn bị/chép tệp đồng bộ trước khi trả (`m4/review_goc/may_chu/server.py:248`, `:273`; `m4/review_goc/may_chu/dich_vu.py:339`, `:349`, `:359`, `:376`, `:425`, `:432`, `:459`, `:479`, `:511`, `:540`). |
| PATCH `/api/trich_xuat/{luot}/hd/{ten}/o/{ma}`; POST `/api/trich_xuat/{luot}/hd/{ten}/{xac_nhan,nap_csdl}` | `_tx_o:291`, `_tx_xn:296`, `_tx_nap:301` | 1/ĐB; `nap_csdl` có nhánh chỉ so sánh khi hợp đồng đã tồn tại (`m4/review_goc/may_chu/dich_vu.py:523`, `:534`, `:576`, `:600`). |
| GET `/api/hop_dong`, `/api/hop_dong/{ref}`, `/api/hop_dong/{ref}/boq`, `/api/hop_dong/{ref}/phu_luc/{so}`; POST `/api/hop_dong/{ref}/{phieu_phu_luc,kiem_dot}`, `/api/hop_dong/{ref}/phu_luc/{so}/huy`, `/api/hop_dong/{ref}/tham_so/{ma}/xac_nhan` | `_hd_ds:307`, `_hd:312`, `_hd_boq:317`, `_hd_pl:354`, `_hd_phieu:322`, `_hd_dot:332`, `_hd_huy:327`, `_hd_ts_xn:349` | GET: đọc/ĐB; tạo phiếu/hủy phụ lục/xác nhận tham số: 1/ĐB; `kiem_dot`: 1/N qua QLV, lưu upload trước khi xếp việc (`m4/review_goc/may_chu/dich_vu.py:635`, `:670`, `:699`, `:741`, `:762`, `:788`, `:827`, `:1000`). |
| POST `/api/phu_luc/{kiem_tra,nap}`, `/api/toan_ven`; GET `/api/kiem_tra/{kiem_tra_dot,toan_ven}` và `/{ma}`; POST `/api/kiem_tra/kiem_tra_dot/{ma}/{nap,ghep,chay_lai}` | `_pl:339`, `_tv:344`, `_kt_ds:359`, `_kt:364`, `_kt_nap:369`, `_kt_ghep:374`, `_kt_chay_lai:379` | GET: 0/ĐB. Phụ lục `kiem_tra`/`nap`: 1/ĐB do đều lưu upload, chỉ `nap` yêu cầu nạp nghiệp vụ. `nap`, `ghep` kết quả kiểm đợt: 1/ĐB; `toan_ven`, `chay_lai`: 1/N qua QLV (`m4/review_goc/may_chu/dich_vu.py:774`, `:845`, `:855`, `:868`, `:877`, `:896`). |
| POST `/api/boq/{tai_len,sheet,kiem_tra,ghi}`, `/api/tat`; GET `/tai/{rel}`, `/`, `/index.html`, tài sản tĩnh hợp lệ | `_boq_tl:384`, `_boq_sh:389`, `_boq_kt:394`, `_boq_ghi:399`, `do_POST:489`, `_tinh:512` | BOQ `tai_len`: **1/L**, lưu tệp và có thể chuyển PDF qua OCR, chuyển bảng DOCX sang Excel **đồng bộ**, không qua QLV (`m4/review_goc/may_chu/dich_vu.py:919`, `:943`). `sheet`, `kiem_tra`: 0/ĐB; `ghi`: 1/ĐB (`m4/review_goc/may_chu/dich_vu.py:964`, `:983`, `:990`). `/api/tat`: P/N, trả rồi tắt server bằng thread; GET tệp/trang: 0/ĐB (`m4/review_goc/may_chu/server.py:489`, `:512`). |

Các route lưu/tải lên/sửa/nạp/xóa/xuất có ghi tệp hoặc CSDL; cấu hình/khởi dừng có thay đổi trạng thái. `sheet`, kiểm BOQ và kiểm phụ lục là nhánh kiểm/đọc nghiệp vụ, nhưng kiểm phụ lục vẫn lưu tệp upload (`m4/review_goc/may_chu/dich_vu.py:774`, `:964`, `:983`). Các tác vụ OCR thử, dò máy AI, trích xuất, phụ lục AI, chứng từ, kiểm đợt/toàn vẹn chạy qua `QLV`; còn upload/sửa/nạp/xuất được gọi đồng bộ. Căn cứ: `m4/review_goc/may_chu/dich_vu.py:179`, `:288`, `:376`, `:774`, `:827`, `:845`, `:964`, `:983`, `:1110`, `:1178`, `:1203`. Upload BOQ có thể lâu do OCR/chuyển đổi ngay trong HTTP request; `kiem_tra_ai` và `thu_cloud` cũng chờ lời gọi dịch vụ đồng bộ (`m4/review_goc/may_chu/dich_vu.py:267`, `:276`, `:919`, `:943`). QLV dùng dictionary và queue RAM (`m4/review_goc/may_chu/viec.py:79`).

### 3.3. Những endpoint chỉ thấy ở phía client

| Thành phần | Kết quả khảo sát |
|---|---|
| Mask v2 | Client gọi GET `/api/v1/trang-thai`, POST `/api/v1/che`, POST `/api/v1/mo-che`, có Bearer phía backend (`tri_thuc/cong_ai.py:635`, `:660`, `:669`, `:683`). **Không phải route do shell cung cấp**; không kết luận quyền/pháp nhân phía server Mask từ client. |
| Bộ tải hóa đơn | Client gọi GET `/api/config`; POST `/api/{profiles,start,status,reconcile,open-folder,events}` (`m2/tai_hoa_don/khach.py:95`, `:101`, `:129`, `:133`, `:137`, `:140`, `:156`). Server Node không nằm trong mã route Python khảo sát. |
| OCR-1 | API Python `CongOCR.ocr`, vận hành qua Hot Folder; không thấy HTTP dispatcher OCR-1 trong tệp này (`ha_tang/cong_ocr.py:127`, `:274`, `:339`). |
| Cổng AI | Dịch vụ Python `CongAI.goi`; không thấy nhóm HTTP `/api/ai/...` được nối vào shell hiện tại (`tri_thuc/cong_ai.py:979`, `:1236`; `giao_dien/server.py:982`). |
| M3 | Có dịch vụ `M3K2.ba_dang_thuc`, không thấy route HTTP M3 trong các dispatcher đã khảo sát (`k2/m3.py:240`, `:246`; `giao_dien/server.py:976`). |

## 4. Quy ước API hiện tại

| Nội dung | Hiện trạng có căn cứ |
|---|---|
| **Dạng lỗi** | Chủ yếu `{error,message}`; CRM thêm `truong`, đối chiếu M4 thêm `field`, bộ tải thêm `goi_y`. Review cũ dùng `{loi,chi_tiet}`. Chưa có envelope chung với `request_id` và `thu_lai_duoc` (`server.py:1288`; `crm_g.py:693`; `m4.py:616`; `m2_tai_hoa_don.py:574`; `m4/review_goc/may_chu/server.py:477`). |
| **Mã HTTP** | Shell: 400/403/413/500; M2/M5 thêm 409/501. CRM: 404/409/413/503; M4 thêm 422; bộ tải/Request có 502. Chưa thống nhất phân loại lỗi phiên: không thấy luồng 401/login tập trung (`server.py:1289`; `crm_g.py:690`; `m4.py:621`; `m2_tai_hoa_don.py:536`; `m4_request.py:141`). |
| **Tác vụ dài** | `/api/that/...` dùng 201 hoặc 202 + `job_id`; G5 ACK 200 dù chạy nền; M2 tải tất cả trả 200; CRM trích/render và nhiều lệnh M4 chờ đồng bộ (`server.py:1161`, `:1169`, `:1231`; `crm_g.py:658`, `:677`; `m4.py:592`; `m2_tai_hoa_don.py:1076`). |
| **Idempotency** | Có nhiều cách: intake băm `[entity,period,source,content_hash]`; M4 dùng `khoa` + biên nhận; CRM G dùng namespace/hash yêu cầu; liên kết chung có biên nhận bền theo PN/module/operation/client key. Không thấy một chính sách HTTP chung về header, thời hạn và phạm vi key (`giao_dien/intake.py:74`; `k2/xay_dung.py:154`; `k2/crm_mau.py:160`; `k2/lien_ket_chung.py:3`). |
| **CAS** | Nhiều biến thể: `expected_graph`, `expected_revision`, `revision`, `expected_version`, `expected_phien_ban`, `expected_basis`, `expected_context_sha256`; đã có trả 409 theo module. Không thể thay tên hàng loạt thành `row_version` mà bỏ token căn cứ nghiệp vụ (`crm_g.py:60`, `:75`, `:123`, `:706`; `m4.py:20`; `module_cong_tac.py:65`). |
| **Phân trang** | CRM S1: `trang/kich_thuoc_trang`, mặc định 25, tối đa 100; M2/M5: `trang/co`, tối đa 100; knowledge: `page/size`, mặc định 50. Một số danh sách chỉ cắt LIMIT, ví dụ báo giá 200; chưa có contract chung (`k2/crm_s1.py:52`, `:72`, `:427`; `k2/hoa_don.py:505`; `k2/kho_so_luong.py:473`; `giao_dien/operations.py:945`; `khung_khai_bao.py:116`). |
| **Upload/download** | Chủ yếu raw bytes + metadata JSON URL-encoded trong header `X-*-Info`; M2/M5 còn dùng base64 trong JSON. Body chung tối đa 50 MB, JSON mặc định 1 MiB; từng module có giới hạn riêng. Download trả bytes + `Content-Disposition`, `no-store`; kiểm quyền khác nhau theo nhóm (`server.py:931`, `:945`, `:1143`, `:1232`; `server.py:806`; `crm_g.py:608`). |
| **Phiên** | Cookie `HttpOnly; SameSite=Strict`; SID ngẫu nhiên ánh xạ vào dictionary của app. Đây là danh tính DEMO, không phải đăng nhập production; không thấy TTL, logout hoặc kho phiên dùng chung nhiều tiến trình (`server.py:193`, `:196`, `:1062`). |
| **CSRF/Origin** | Shell kiểm Host, Origin nếu có, từ chối `Sec-Fetch-Site=cross-site`; yêu cầu token cho API riêng tư; token được chèn vào HTML. Token này chung toàn app, không gắn với từng người (`server.py:918`, `:980`, `:1008`). Review cũ chỉ yêu cầu `X-HD: 1` cho ghi (`m4/review_goc/may_chu/server.py:417`). |

## 5. Ánh xạ route cũ → nhóm `/api/v1/`

**Đây là đề xuất phân nhóm cho G1, chưa phải contract đã duyệt.** Giữ namespace `module`, `engine` theo TL 55; tên nghiệp vụ mới dùng tiếng Việt không dấu, snake_case. Vì vậy dùng `quan_tri`, `phap_nhan`, `tai_lieu` thay các cách viết có dấu gạch nối trong bản nháp.

| Route/nhóm cũ đã kiểm kê | Nhóm đích đề xuất | Nguyên tắc chuyển |
|---|---|---|
| Cookie DEMO, `*/danh-tinh`, `/api/demo/vai` | `/api/v1/phien`, `/api/v1/toi`, `/api/v1/phap_nhan` | Tách đổi vai DEMO khỏi xác thực thật. |
| `/api/khung/module/crm`, danh mục module theo quyền | `/api/v1/module`; `/api/v1/module/crm` | Menu và khả năng truy cập lấy từ backend. |
| `/api/crm/...` | `/api/v1/module/crm/...` | Giữ nghiệp vụ và token CAS đặc thù. |
| `/api/m4/...`, `/api/m4-request/...`, bridge `/api/nghiem-thu/...` | `/api/v1/module/m4/...` | Phân biệt bridge cũ và M4 chuẩn; nghiệp vụ Request vẫn thuộc M4. |
| `/api/m2/...`, `/api/m5/...`, `/api/m9/...` | `/api/v1/module/{m2,m5,m9}/...` | Giữ quyền nguồn/pháp nhân và cơ chế BOTH của L11. |
| `/api/cong-tac-module/...` | `/api/v1/quan_tri/module/...` | Công tắc là quản trị module. |
| `/api/tham-quyen/...` | `/api/v1/quan_tri/cap_quyen/...`; quyền cá nhân tại `/api/v1/toi/...` | Giữ cổng Admin và revision hiện tại. |
| `/api/upload`, `/api/files/...`, upload/download tài liệu trong module | `/api/v1/tep`, `/api/v1/tai_lieu`, `/api/v1/ket_qua` | Core kiểm quyền; module giữ liên kết nghiệp vụ. |
| `/api/that/job`, trạng thái G5/M2, Review `/api/viec` | `/api/v1/viec/...` | Theo dõi/hủy/kết quả dùng contract chung, giữ nguồn thực thi trong adapter. |
| Khởi động bộ tải; gọi #6, OCR, Mask | `/api/v1/engine/...`; cấu hình tại `/api/v1/quan_tri/engine/...` | Người dùng gọi Core; endpoint engine nội bộ giữ sau adapter. |
| Review `/api/{phien_ban,he_thong,ai,ocr/trang_thai}`, `/api/cai_dat` và các nhánh đọc/lưu, kiểm AI/cloud, dò máy, nhật ký gửi ngoài | `/api/v1/quan_tri/engine/...` | Đề xuất gom trạng thái/cấu hình công cụ vào quản trị engine; các lệnh thử kết nối/dò máy qua adapter. Route nguồn: `m4/review_goc/may_chu/server.py:53`, `:58`, `:68`, `:74`, `:79`, `:84`, `:89`, `:94`, `:109`, `:189`. |
| Review POST `/api/cai_dat/khoa`, DELETE `/api/cai_dat/khoa/{anthropic,openai}` | Đề xuất ngừng công khai hai route cũ khi chuyển sang Core; cấu hình qua `/api/v1/quan_tri/engine/...` | Không chuyển nguyên endpoint quản lý khóa riêng của Review sang API nghiệp vụ; đây là đề xuất G1, chưa phải quyết định ngừng đã duyệt. Route nguồn: `m4/review_goc/may_chu/server.py:99`, `:104`. |
| Review `/api/tong_quan`, GET/PUT `/api/tham_so` | `/api/v1/module/m4/tong_quan`, `/api/v1/module/m4/tham_so` | Đề xuất giữ chức năng trong M4, tách danh mục tham số nghiệp vụ khỏi cấu hình engine. Route nguồn: `m4/review_goc/may_chu/server.py:63`, `:200`, `:205`. |
| Review `/api/csdl/{sao_luu,xuat_excel}` | `/api/v1/quan_tri/sao_luu/...`; `/api/v1/module/m4/xuat_du_lieu/...` | Đề xuất thay sao lưu riêng bằng cơ chế Core sau khi chốt chuyển dữ liệu; xuất Excel giữ tại M4. Hiện hai hàm tạo bản sao SQLite/tệp Excel: `m4/review_goc/may_chu/dich_vu.py:799`, `:811`. |
| Review `/api/hop_dong/...`, `/api/phu_luc/...`, `/api/boq/...`, `/api/kiem_tra/...`, `/api/toan_ven`, `/api/phu_luc_ai/...`, `/api/chung_tu/...` | `/api/v1/module/m4/{hop_dong,phu_luc,boq,kiem_tra,toan_ven,phu_luc_ai,chung_tu}/...` | Đề xuất giữ nghiệp vụ sau adapter M4; tác vụ nền trả tham chiếu `/api/v1/viec/...`, upload BOQ có OCR cần chuyển thành tác vụ dài. Route nguồn: `m4/review_goc/may_chu/server.py:114`, `:154`, `:307`, `:339`, `:344`, `:359`, `:384`; OCR đồng bộ: `m4/review_goc/may_chu/dich_vu.py:943`. |
| Review `/api/trich_xuat/...`, `/api/ocr/chay_thu`, `/tai/{rel}` | Lệnh engine tại `/api/v1/engine/...`; sửa/xác nhận/nạp kết quả tại `/api/v1/module/m4/trich_xuat/...`; tải qua `/api/v1/ket_qua/...` | Đề xuất tách chạy engine khỏi duyệt/nạp nghiệp vụ; thay đường dẫn tệp bằng kết quả được Core kiểm quyền. Route nguồn: `m4/review_goc/may_chu/server.py:184`, `:233`, `:291`, `:296`, `:301`, `:512`. |
| Review POST `/api/tat`; GET `/`, `/index.html`, tài sản tĩnh | Đề xuất ngừng công khai `/api/tat` của server Review; trang/tài sản tĩnh do shell phục vụ, không đổi thành `/api/v1/` | Vòng đời server giao cho quản trị engine; đây là đề xuất G1. Hiện `/api/tat` tắt server riêng và `_tinh` phục vụ giao diện: `m4/review_goc/may_chu/server.py:489`, `:512`. |
| `/api/that/...` còn lại | `/api/v1/module/{ma_module}/...` | **Chờ phân ranh module**; không dồn nghiệp vụ định khoản/tri thức vào Core. |
| `/api/health` | `/healthz`, `/readyz` | Tách sống/sẵn sàng; shutdown thuộc vận hành có quyền riêng. |

Không thấy route workflow dùng chung trong shell; `/api/v1/quy_trinh/...` cần đặc tả mới, không thể chỉ đổi tiền tố (`giao_dien/server.py:976`).

## 6. Chênh lệch với TL 54 §9

| Nguyên tắc | Route/vấn đề xác nhận được |
|---|---|
| **Backend quyết định quyền** | `/api/that/knowledge/decide` nhận `actor` từ body; backend chỉ so chuỗi với cấu hình, trong khi `/api/state` trả `approval_actor`. Đây chưa phải chứng minh người gọi có quyền duyệt (`server.py:1211`; `giao_dien/operations.py:972`, `:844`). |
| **Không tin danh tính frontend khai** | `/api/that/quick/decide`, `/api/that/proposals/decide` truyền actor do client cung cấp. Dịch vụ có kiểm cấu trúc/trạng thái nghiệp vụ nhưng không thấy ràng buộc actor với phiên xác thực trong đường xử lý đã đọc (`server.py:1170`, `:1217`; `giao_dien/quick.py:921`; `xuat/service.py:43`). Không kết luận mọi kiểm nghiệp vụ đều nằm ở frontend. |
| **Ngữ cảnh riêng từng người** | Token `LocalApp.token` dùng chung cho mọi API A; nhóm `/api/that/...` không lấy `crm_sid`. `Operations.state` chọn phiên nghiệp vụ OPEN mới nhất dùng chung. Đây là chênh lệch với Core đa người dùng (`server.py:63`, `:928`, `:1023`; `giao_dien/operations.py:834`). |
| **Phiên và điều phối bền** | CRM có **SID riêng từng trình duyệt**, không phải một login toàn cục; tuy nhiên kho phiên vẫn nằm trong RAM app. Job Operations và hàng đợi tải tất cả cũng ở RAM, khác hàng đợi G5 bền trong CSDL (`server.py:196`; `giao_dien/operations.py:873`; `m2_tai_hoa_don.py:213`; `k2/crm_doi_chieu.py:371`). |
| **Download kiểm quyền dữ liệu** | `/api/files/{id}/download`, `/api/that/quick/{run}/download`, `/api/that/shadow/.../download`, `/api/that/outside-catalog/download`, bridge `/api/nghiem-thu/file-soat/{id}` chỉ có cổng A và kiểm ID/đường dẫn/dữ liệu; không thấy kiểm người dùng/quyền hồ sơ/pháp nhân (`server.py:1019`, `:1048`, `:1057`, `:1134`, `:1138`; `giao_dien/operations.py:771`, `:1044`; `server.py:187`). |
| **Download Review cũ** | `/tai/{rel}` kiểm file nằm trong thư mục dữ liệu, không kiểm quyền người dùng/pháp nhân. Chỉ áp dụng nếu chạy server Review cũ; không gán kết luận này cho cổng owned #6 có token/allowlist seal (`m4/review_goc/may_chu/server.py:512`; `m4/review_goc/may_chu/dich_vu.py:58`; `nguon/trich6_host.py:484`). |

**Phần nên giữ:** download CRM/M4/M5/M9 có kiểm quyền backend, không nên đánh đồng với các download trên: `k2/crm.py:860`, `k2/xay_dung.py:309`, `k2/kho_so_luong.py:720`, `k2/vay.py:798`. Khung CRM cũng truy vấn quyền tại backend (`giao_dien/khung_khai_bao.py:103`).

## Chờ Anh

- Chốt nguồn tài khoản production, vòng đời phiên và quan hệ người dùng–pháp nhân/workspace.
- Chốt module sở hữu các nghiệp vụ `/api/that/...`, cùng quyền đọc/duyệt/xuất tương ứng.
- Chốt thời hạn duy trì route cũ, phạm vi tương thích và chính sách lưu tệp/kết quả tạm.

## Gợi ý cho đặc tả G1

1. Lập OpenAPI từ danh mục này; đánh dấu rõ API shell, adapter nội bộ và server legacy.
2. Chuẩn hóa lỗi, phân trang, trace và mã HTTP; tác vụ dài trả 202 + `viec_id`.
3. Giữ CAS nghiệp vụ; bổ sung `row_version` nơi phù hợp, không thay token căn cứ bằng một số phiên bản chung.
4. Ràng buộc actor/pháp nhân từ phiên backend cho API, job và download; loại bỏ quyền dựa trên chuỗi actor client gửi.
5. Đặc tả namespace/thời hạn/replay của idempotency và chuyển tiếp route cũ; chưa triển khai trước khi đủ các phiếu duyệt cổng C.

Vòng 2: đã sửa theo RV-C (3 mục)