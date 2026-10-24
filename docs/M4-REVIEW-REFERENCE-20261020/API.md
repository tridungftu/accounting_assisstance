# API back-end — dùng để ghép giao diện (Claude Design) vào phần mềm

Máy chủ: `python chay.py` (hoặc `CHAY_PHAN_MEM.bat`) → `http://localhost:8600`. Chỉ nghe trên máy này.

- Trang chủ `/` trả `giao_dien/index.html`. Chưa có thì trả trang tạm `giao_dien/tam.html`.
- File tĩnh khác trong `giao_dien/` phục vụ theo đường dẫn, ví dụ `/app.js`, `/css/app.css`.
- Mọi yêu cầu **ghi** (POST/PUT/PATCH/DELETE) phải có header `X-HD: 1`. Thiếu header thì máy chủ trả 403, để chặn trang web lạ gọi vào.
- Kết quả trả về là JSON, khoá viết tiếng Việt không dấu.
- Khi lỗi, máy chủ trả mã HTTP kèm `{"loi": "thông báo tiếng Việt", "chi_tiet": …}`:
  - 400: dữ liệu sai.
  - 404: không có.
  - 409: xung đột, ví dụ còn ô vàng chưa xác nhận.
  - 500: lỗi máy.
- Tải file lên bằng cách gửi **nguyên nội dung file** trong body, tên file đặt ở `?ten=`. Không dùng multipart.
- Tải file xuống qua `GET /tai/<đường dẫn>`. Đường dẫn này luôn có sẵn trong các trường `tai` của kết quả; thêm `?xem=1` để mở xem trong trình duyệt.

```js
async function api(method, url, body, file) {
  const o = {method, headers: {"X-HD": "1"}};
  if (file) o.body = file;
  else if (body !== undefined) { o.body = JSON.stringify(body); o.headers["Content-Type"] = "application/json"; }
  const r = await fetch(url, o); const d = await r.json();
  if (!r.ok) throw new Error(d.loi); return d;
}
```

## Khung chung

| Gọi | Dùng cho |
|---|---|
| `GET /api/he_thong` | Thanh trên cùng: `phien_ban`, `ai` (xem dưới), `buoc` (tên 9 bước), `viec_dang_chay` |
| `GET /api/ai?lam_moi=1` | Trạng thái máy AI: `ip, cong, model, ket_noi, co_model, models[], loi` (lưu đệm 15 giây; `lam_moi=1` để hỏi lại ngay) |
| `GET /api/viec` | Ngăn "Việc đang chạy": `ds[]` gồm `id, loai, ten, tt, pct, thong_bao, loi, tao_luc, bat_dau, ket_thuc, dang_cho_ai` |
| `GET /api/viec/{id}` | Chi tiết một việc, thêm `ket_qua`, `nhat_ky`, `chi_tiet` |
| `POST /api/viec/{id}/dung` | Nút Dừng |
| `GET /api/tong_quan` | Màn Tổng quan: `ai, viec_dang_chay[], viec_gan_day[]{t, loai, ten, phu, ket_qua, kind, ghi_chu, route, ma}, can_xem_xet[]{loai, tieu_de, noi_dung, anh_huong, route, ma, nut}, so_o_can_xem, csdl{so_hop_dong, moi_trong_thang, so_phu_luc, phu_luc_co_do, so_dot, tham_so_chua_xac_nhan}, dot_cho_duyet[]` |

`tt` của một việc nhận một trong các giá trị: `cho` (đang chờ máy AI rảnh), `dang_chay`, `xong`, `loi`, `da_dung`. `loai` nhận: `trich_xuat`, `tim_may_ai`, `toan_ven`, `kiem_dot`.

## Trích tham số hợp đồng

Một **lượt** là một lần bấm Chạy cho nhiều hợp đồng. Mã lượt có dạng `yyyymmdd_hhmmss`.

1. `POST /api/trich_xuat` → `{luot}`. Tạo lượt mới.
2. `POST /api/trich_xuat/{luot}/tep?ten=HD.docx` với body là nội dung file. Gọi lặp lại cho từng file `.docx`, `.doc`, `.pdf` (PDF có chữ; PDF scan báo lỗi), hoặc đáp án `DAP_AN_*.tsv`. Xoá một file: `DELETE /api/trich_xuat/{luot}/tep/{ten}`.
3. `POST /api/trich_xuat/{luot}/chay` với body:
   ```json
   {"model": "gpt-oss:20b", "ra_lai": true, "chay_lai": false,
    "cloud": {"bat": false, "nha_cung_cap": "anthropic", "ty_le": 20},
    "tham_so": ["TT-02", "..."], "them": ["Bảo hiểm | Loại bảo hiểm công trình"]}
   ```
   - Mọi khoá đều tuỳ chọn. Khoá nào bỏ trống thì lấy theo Cài đặt.
   - `tham_so`: chọn bớt tham số; bỏ trống là dùng cả 37.
   - `them`: tham số hỏi thêm cho riêng lượt này.

   Máy chủ trả `{viec, luot, so_hop_dong, so_tham_so, cloud, ra_lai, model}`.
4. `GET /api/trich_xuat/{luot}`. Gọi 2 giây một lần để cập nhật tiến độ. Kết quả gồm:
   - `tt, pct (0–1), thong_bao, bat_dau, ket_thuc` (giây epoch), `model, may_ai`.
   - `buoc_ten[9]`: Đọc file → Tách Điều/Khoản → Dò vị trí tham số → Hỏi Local AI → Tự kiểm tra trích dẫn → Rà lại ô vàng → Kiểm tra logic → Kiểm tra chéo cloud → Xuất kết quả.
   - `hd[]`, mỗi hợp đồng có:
     - `file`, `ten` (dùng ở bước 5).
     - `tt`: Chờ / Đang chạy / Xong / Xong có ô vàng / Lỗi / Bỏ qua (dùng kết quả cũ) / Đã dừng.
     - `pct`, `buoc` (0–8), `mo_ta` (bước đang làm, ví dụ "Hỏi Local AI: nhóm «Tạm ứng» (3/9)…").
     - `so_ok, so_vang, dung_dap_an, thoi_gian, loi, canh_bao[]`.
     - `tai{excel,json,cau_truc_xlsx,cau_truc_json,gui_ra_ngoai}`.
   - `log[]`: các dòng `[giờ, nội dung]`.
   - `tai{tong_hop_xlsx,tong_hop_json,nhat_ky,danh_muc_hd}`.
   - `tep_dau_vao[]`, `tuy_chon`.

   Nút Dừng gọi `POST /api/trich_xuat/{luot}/dung`. Chạy lại (lượt lỗi / đã dừng): `POST /api/trich_xuat/{luot}/chay_lai` với cùng body như bước 3 → tạo lượt mới chép đầu vào cũ.
5. `GET /api/trich_xuat/{luot}/hd/{ten}` trả bảng kết quả của một hợp đồng:
   - `bang[37]`, mỗi dòng có:
     - `ma, nhom, tham_so, mo_ta, muc (0–3)`.
     - `gia_tri, don_vi, dieu_khoan, trich_dan, ghi_chu`.
     - `kiem_tra`: chuỗi bắt đầu bằng "OK" là xanh; còn lại là vàng, kèm lý do.
     - `logic[]`: các mã L1–L5 kèm lý do.
     - `nguon`: Local / Local – cloud xác nhận / Cloud sửa (local: …).
     - `trang_thai`: Chưa xác nhận / Đã xác nhận / Đã sửa tay, chưa xác nhận / Đã sửa tay, đã xác nhận.
     - `gia_tri_ai` (giá trị máy trích ban đầu, luôn giữ), `da_xac_nhan, da_sua, ghi_chu_soat`, `kiem_tra_tu` (local/cloud).
     - `vang, can_xem, vi_tri_do_duoc, lich_su[]`, và `dap_an, so_voi_dap_an` nếu có đáp án.
   - `tom_tat{so_tham_so, so_ok, so_vang, so_can_xem, dung_dap_an, token_vao, token_ra, thoi_gian_giay, loi_ai, cloud{…}}`.
   - `phieu_kiem_tra{words, articles, warnings[]…}`, `tai{…}`.
6. Sửa và xác nhận:
   - Sửa một ô: `PATCH /api/trich_xuat/{luot}/hd/{ten}/o/{ma}` với `{"gia_tri": "…", "ghi_chu": "…"}` hoặc `{"xac_nhan": true|false}`. Sửa giá trị thì bỏ xác nhận; giá trị rỗng → 400. Máy chủ trả dòng đã cập nhật; Excel và JSON được ghi lại ngay.
   - Xác nhận nhiều ô một lúc: `POST /api/trich_xuat/{luot}/hd/{ten}/xac_nhan` với `{"ma": ["TT-21", …]}`.
7. Nạp vào CSDL: `POST /api/trich_xuat/{luot}/hd/{ten}/nap_csdl` với `{}` hoặc `{"van_nap": true}`.
   - Còn tham số chưa xác nhận thì trả 409, kèm `chi_tiet{chua_xac_nhan[], o_vang[]}`; giao diện hỏi lại rồi gửi `van_nap: true`. Các tham số đó vào CSDL với trạng thái "AI - CẦN XÁC NHẬN" / "AI - tự kiểm OK, chưa xác nhận".
   - Mỗi tham số ghi kèm **nguồn gốc** vào bảng `tham_so_nguon` (khoá bằng trigger): giá trị máy trích, giá trị nạp, kết quả tự kiểm, mức, nguồn local/cloud, đã sửa tay, người/lúc xác nhận, lịch sử, model, máy AI, lượt, file + SHA-1, lúc trích, lúc nạp.
   - Hợp đồng đã có trong CSDL thì không ghi đè, chỉ trả `lech[]`. Trả `{ok, ma_hd, moi, trang_thai, lech, chua_xac_nhan}`.
8. Ghi lại `DANH_MUC_HOP_DONG.xlsx` (dùng khi lần trước file đang mở trong Excel): `POST /api/trich_xuat/{luot}/danh_muc?ten=`.
9. Danh sách các lượt: `GET /api/trich_xuat` → `ds[]` gồm `luot, tt, model, pct, so_hd, so_xong, so_vang, hop_dong[]`. Xoá một lượt: `DELETE /api/trich_xuat/{luot}`.

## Danh mục tham số

- `GET /api/tham_so` → `rows[]` gồm `ma, nhom, mo_ta, tk, bk, dung, muc, bat_buoc, loai_tru`.
- `PUT /api/tham_so` với `{"rows": […]}`. Bản cũ được sao lưu trước khi ghi.

## Cơ sở dữ liệu hợp đồng

| Gọi | Dùng cho |
|---|---|
| `GET /api/hop_dong` | Danh mục HĐ: `ds[]` gồm `ma_hd, so_hd, phan_loai, loai_gia, ngay_ky, gia_tri_hd, ben_b, du_an, gt_sau_vat_goc, gt_hieu_luc_hom_nay, so_phu_luc, so_dot, so_boq, so_tham_so, co_do, co_vang, chua_xac_nhan` |
| `GET /api/hop_dong/{ma_hd}?ngay=yyyy-mm-dd` | Chi tiết: `hop_dong, ngay, gt_goc, gt_hieu_luc, pl_ap_dung[], tham_so[]` (mỗi tham số có `gia_tri` gốc, `gia_tri_hieu_luc`, `nguon_hieu_luc`, `nhom`, `muc`, `lich_su[]` của phụ lục, `nguon_trich` = dòng `tham_so_nguon` hoặc null), `phu_luc[]` (kèm `co_do, co_vang`), `dot[], canh_bao[]` |
| `POST /api/hop_dong/{ma_hd}/tham_so/{ma_ts}/xac_nhan` với `{"ghi_chu"}` | Xác nhận trong CSDL một tham số nạp khi chưa xác nhận (không đổi giá trị, ghi nhật ký) |
| `GET /api/hop_dong/{ma_hd}/boq?ngay=` | BOQ hiệu lực: `dong[]` gồm `ma_hm, stt, nhom, ten, dvt, kl, don_gia, thanh_tien_ghi, vi_tri_nguon, nguon, lich_su[]`; `da_bo[]`, `tong_truoc_vat, vat, tong_sau_vat, gt_hieu_luc, khop, pl_ap_dung[]` |
| `GET /api/hop_dong/{ma_hd}/phu_luc/{so_pl}` | Chi tiết phụ lục: `phu_luc, thay_doi_tham_so[], boq[], canh_bao[], nhat_ky[], lan_truoc[]` |
| `POST /api/hop_dong/{ma_hd}/phieu_phu_luc` | Tạo phiếu phụ lục: `{so_pl, tai}` |
| `POST /api/phu_luc/kiem_tra?ten=` (body: file phiếu) | Kiểm tra P01–P18, không ghi: `phieu[]` gồm `sheet, phu_luc, ket_qua, co_chan, kiem_tra[]{ma, muc (CHẶN/ĐỎ/VÀNG/ĐẠT…), noi_dung}` |
| `POST /api/phu_luc/nap?ten=` | Như trên nhưng ghi các phụ lục (sheet) không có lỗi CHẶN; sheet có CHẶN trả `ket_qua: "KHÔNG GHI"` |
| `POST /api/hop_dong/{ma_hd}/phu_luc/{so_pl}/huy` với `{"ly_do"}` | Huỷ phụ lục |
| `POST /api/hop_dong/{ma_hd}/kiem_dot?ten=&ngay_nghiem_thu=yyyy-mm-dd&dot=3` (body: file hồ sơ) | Kiểm tra đợt **hai lớp** (Lớp 1 toàn vẹn + Lớp 2 đối chiếu HĐ/PL/BOQ), chạy thành việc nền. Kết quả xem mục "Kết quả kiểm tra" dưới |
| `POST /api/csdl/xuat_excel` với `{"ref", "ngay"}` | Xuất CSDL ra Excel: `{tai}` |
| `POST /api/csdl/sao_luu` | Sao lưu CSDL |

## Import BOQ gốc

1. `POST /api/boq/tai_len?ten=BOQ.xlsx` (body: file) → `{tep, ten, nguon, sheets[]{ten, so_dong, so_cot, an}, goi_y}`; `goi_y` = kết quả bước 2 cho sheet đoán được.
   Nhận cả `.docx` / `.pdf`: các bảng trong file (PDF scan → OCR ABBYY trên máy) được ghi ra Excel, mỗi nhóm bảng liên tiếp cùng số cột (bảng ngắt trang) là một sheet `Bảng k`, đầu sheet chép các dòng đầu văn bản (để nhận số HĐ); `nguon = {loai: pdf_ocr|docx, so_bang, trang, tu_luu_dem}` (`null` với file Excel). Số dạng chữ kiểu Việt Nam (`1.234.567`, `1.250,56`) được đọc khi import.
2. `POST /api/boq/sheet` với `{tep, sheet}` → `{sheet, dong[][] (40 dòng đầu, dạng chữ), so_cot, hang_tieu_de, cot{stt,ten,dvt,kl,don_gia,thanh_tien: "A"…}, truong[]}`.
3. `POST /api/boq/kiem_tra` với `{tep, sheet, hang_tieu_de, cot, ma_hd}` → `{ma_hd, so_hd, so_dong, xem_truoc[], loi[], tong_truoc_vat, vat, tong_sau_vat, gt_hd, lech, ket_luan (ĐẠT/LỆCH), boq_hien_co, chan[], can_ly_do}`. Dòng không có ĐVT = tiêu đề nhóm; dừng ở dòng Cộng/Tổng. `chan[]` khác rỗng thì không ghi được (không đọc được dòng nào, dòng sai kiểu, HĐ đã có phụ lục, hoặc đã có BOQ gốc + đợt thanh toán).
4. `POST /api/boq/ghi` với body bước 3 + `ly_do` (bắt buộc khi thay BOQ gốc đang có) + `chap_nhan_lech` → `{ok, ma_hd, so_dong, canh_bao, ket_luan}`; lỗi → 409.

## Trích phụ lục từ file Word / PDF

PDF scan → OCR (task Hot Folder của phần mềm). Quy tắc: hợp đồng (số `NNNN/YYYY` trong văn bản / tên file), số PL, ngày ký ("Hôm nay, ngày …"), ngày hiệu lực, bảng KL / đơn giá (cũ → mới, Tổng, VAT, Tổng sau VAT), khoảng ngày áp đơn giá, phân loại THAY/THEM/BO so BOQ hiện hành (khớp tên gần đúng). Local AI: tham số bị sửa (giá trị cũ lấy từ CSDL) và thay đổi khác. Kiểm tra = P01–P18 của phiếu + P20–P26 riêng (OCR, BOQ gốc thiếu, tham số chưa xác nhận / trích dẫn không khớp, khớp tên gần đúng, đơn giá theo khoảng ngày, giá trị tự tính, thay đổi khác).

| Gọi | Kết quả |
|---|---|
| `POST /api/phu_luc_ai/tai_len?ten=PL01.docx` (body: file .docx/.doc/.pdf) | `{tep, ten}` |
| `POST /api/phu_luc_ai/chay` với `{tep: [...]}` | Việc nền `phu_luc` (hàng đợi máy AI) → `ket_qua{ds:[mã], loi:[{ten, loi}]}` |
| `GET /api/phu_luc_ai` | `{ds:[{id, ten, ma_hd, so_hd, so_pl, ngay_ky, ocr, so_tham_so, so_boq, so_khac, chan, do, vang, chua_xac_nhan, nap}], che_do_boq}` |
| `GET /api/phu_luc_ai/{id}` | Bản trích đầy đủ: `info, trich, nguon, tham_so[{ma_ts, ten, cu, moi, trich, dieu, kiem_tra_trich, trang_thai, bo}], khac[], boq{che_do: khong\|thay_doi\|toan_bo, bang, thoi_han, dong[], so_sanh[]}, kiem_tra[[mã, mức, nội dung]], info_tinh, gt_truoc_pl, nap` |
| `POST /api/phu_luc_ai/{id}/cap_nhat` | Sửa: `{ma_hd?, info?{so_pl, ngay_ky, ngay_hieu_luc, trang_thai, loai, noi_dung, can_cu, gt_sau_vat, gt_hd_sau_pl}, tham_so?[{ma_ts, moi?, trang_thai?, bo?}], them_ts?{ma_ts, moi, trich}, boq_che_do?}` → kiểm tra lại, trả bản trích |
| `POST /api/phu_luc_ai/{id}/hoi_lai_ai` | Việc nền: hỏi lại Local AI (giữ tham số đã xác nhận / sửa / thêm) |
| `POST /api/phu_luc_ai/{id}/nap` | Ghi CSDL (kiểm tra lại với CSDL hiện tại). 409 nếu còn CHẶN, tham số chưa xác nhận hoặc đã nạp |
| `DELETE /api/phu_luc_ai/{id}` | Xoá bản trích (không đụng CSDL) |

## Chứng từ của đợt (Lớp 3)

BB nghiệm thu KL đợt, BB giao nhận vật tư / thiết bị, packing list, CO, CQ, BB lắp đặt / chạy thử. PDF scan / ảnh → OCR ABBYY (như hợp đồng); Word, Excel đọc trực tiếp. Python đọc bảng dòng hàng; Local AI chỉ đọc chứng từ không có bảng (vd CO dạng form), kèm trích dẫn nguyên văn để Python tìm lại.

| Gọi | Trả về |
|---|---|
| `POST /api/chung_tu/tai_len?ten=CO.pdf` (body: file .pdf/.docx/.doc/.xlsx/.xlsm/.jpg/.png/.tif) | `{tep, ten}` |
| `POST /api/chung_tu/chay` với `{tep:[...], ma_kq}` (một lần Kiểm tra đợt) · `{tep, ma_hd, ngay_nt}` (chỉ BOQ hiệu lực) · `{tep, them_vao: id}` (thêm vào bộ đã có) | Việc nền `chung_tu` (hàng đợi máy AI) → `ket_qua{id, so_tai_lieu, loi:[{ten, loi}]}`. 400 nếu chưa chọn đợt / hợp đồng |
| `GET /api/chung_tu` | `{ds:[{id, ma_hd, so_hd, dot, ngay_nt, tep_hstt, tao_luc, so_tai_lieu, dem{Cao, Trung bình, Thấp}}], loai{BB_NT, BB_GN, PL, CO, CQ, BB_LD, KHAC: tên}}` |
| `GET /api/chung_tu/{id}` | `so_hd, dot, ngay_nt, tep_hstt, hang_muc[], tai_lieu[{id, ten, loai, ly_do_loai, so, ngay, ngay_trich, hd_ref[], ocr, canh_bao[], bo, dong[{vi_tri, ten, nhom, model, quy_cach, dvt, so_luong, lo, xuat_xu, nsx, khoa, khop, nguon, trich_dan, kiem_tra}]}], ma_tran[{khoa, ma_hm, ten, dvt, kl_kn, kl_lk, nt, nt_docs[], gn, gn_docs[], co[], cq[], pl[], ld[]}], phat_hien[], dem, loi[]` |
| `POST /api/chung_tu/{id}/cap_nhat` với `{tai_lieu:[{id, loai?, so?, ngay?, bo?}]}` | Sửa loại / số / ngày, bỏ hoặc dùng lại chứng từ → đối chiếu lại, trả bộ đầy đủ |
| `DELETE /api/chung_tu/{id}` | Xoá bộ (không đụng file gốc, CSDL) |

Phát hiện (`id, code, level, title, detail, item, tai_lieu, amount` = ảnh hưởng sau VAT): C01 KL kỳ này không có / lệch BB nghiệm thu · C02 ngày BB nghiệm thu ≠ ngày nghiệm thu đợt · C03 Σ số lượng giao < KL lũy kế · C04 dòng hàng không ghép được hạng mục · C05 thiếu CO / CQ / packing list · C06 số lượng / model / số lô lệch giữa các chứng từ · C07 ngày bất hợp lý (CO/CQ sau giao, giao sau nghiệm thu, lắp đặt trước giao) · C08 chứng từ ghi số HĐ khác · C09 thiếu số / ngày, không đọc được dòng hàng.

## Kết quả kiểm tra (Kiểm tra đợt: đủ hai lớp · chỉ toàn vẹn file)

- File `.xls` (Excel 97-2003) nhận ở `kiem_dot`, `toan_ven`, `boq/tai_len`, `phu_luc/{kiem_tra|nap}`, chứng từ: máy chuyển sang `.xlsx` (Microsoft Excel → LibreOffice → `xlrd` chỉ giá trị). Kiểm tra đợt / toàn vẹn bắt buộc giữ công thức: không chuyển được thì việc nền báo `loi` kèm hướng dẫn. `boq/tai_len` trả thêm `tu_xls` (cách chuyển, `null` nếu không phải .xls).
- Toàn vẹn (chỉ Lớp 1): `POST /api/toan_ven?ten=HSTT.xlsx&o=0.Giấy ĐNTT!F16` (body: file Excel) chạy thành việc nền; `o` là ô số đề nghị để dựng cây truy vết, bỏ trống thì máy tự tìm.
- Khi việc xong, `GET /api/viec/{id}` → `ket_qua`; kết quả cũng lưu trên đĩa và đọc lại được:
  - `GET /api/kiem_tra/{kiem_tra_dot|toan_ven}` → `ds[]{ma, loai, tep, luc, hop_dong, dot, ngay_nghiem_thu, dem, de_nghi, anh_huong, da_nap, so_phat_hien}`.
  - `GET /api/kiem_tra/{kiem_tra_dot|toan_ven}/{ma}` → toàn bộ kết quả.
- Trường chung: `ma, tep, luc, de_nghi, phat_hien[], bang_k[8]{code, ten, ket_qua, so, chi_tiet, finding}, cay[]{cap, ten, o, cong_thuc, gia_tri, loai, nhom, tai_lieu, ghi}, dem{Cao, Trung bình, Thấp}, so_phat_hien, tai`.
  - Mỗi phát hiện: `id, code (K1–K8 / B1 vượt BOQ, B2 đơn giá, B3 ngoài BOQ, B4 KL HĐ, B5 kỳ trước, B6 thiếu, B7 hằng số / ô tham số gõ cứng ≠ HĐ (VAT, tỷ lệ tạm ứng, thanh toán, giữ lại…), B8 khấu trừ giữ lại / thu hồi tạm ứng / thanh toán ≠ tỷ lệ HĐ, GT giá trị HĐ), layer (1|2), level, title, detail, amount (đồng, chưa VAT, null = chưa định lượng), sheet, cell, item, actual, expected, source, formula, reference, conclusion`.
- Riêng kiểm tra đợt, bảng kiểm Lớp 2 (gồm cả bước đạt): `bang_lop2[]{nhom, ten, ho_so, hd, chenh, don_vi (đồng | hạng mục | ""), ket_qua (Đạt | Lệch | Cần xem | Không áp dụng | Không có số liệu), o, ghi, finding}` theo 3 nhóm: giá trị HĐ so với giá trị thực hiện / thanh toán (GT HĐ, lũy kế ≤ GT HĐ, cộng lũy kế, lũy kế kỳ trước = đợt đã duyệt, Σ KL kỳ này × đơn giá × (1+VAT), lũy kế thanh toán ≤ GT HĐ); đơn giá và khối lượng BOQ so với hồ sơ (B1–B6, đếm hạng mục đạt / lệch); tỷ lệ thanh toán và khấu trừ so với tham số HĐ (đề nghị = TT-20 × GT kỳ này − thu hồi tạm ứng, cộng trừ trong hồ sơ, giữ lại = TT-21, thu hồi tạm ứng, hằng số). `doi_chieu_hm[]{dong, ma_hm, ten, nhom, dvt, khop (cách ghép), khoa (khoá dòng hồ sơ), ma_rieng, can_ghep, ung_vien[]{ma_hm, ten, nhom, dvt, don_gia, kl, ty_le}, ghep_tay, kl_hd_hs, kl_hd, dg_hs, dg_hd, kl_kt, kl_kt_db, kl_kn, kl_lk, nguon, anh_huong, loi[]}` — từng hạng mục, cả hạng mục đạt. Kết quả chạy trước bản 2026-10-07c không có hai trường này.
- Riêng kiểm tra đợt: `hop_dong{ma_hd, so_hd}, ben_b, dot, dot_truoc, ngay_nghiem_thu, gt_hieu_luc, loai_gia, vat, phu_luc_ap_dung[], phu_luc_chua_ap_dung[], o_de_nghi, anh_huong, tong_hop{}, dem_lop{1,2}, da_nap, tai{lop1, lop2}`.
- Ghép tay một dòng hồ sơ với Mã HM BOQ: `POST /api/kiem_tra/kiem_tra_dot/{ma}/ghep` với `{dong, ma_hm}` → `{ok, dong, ma_hm, ten_boq, so_ghep_moi}`; lưu vào `khop_hang_muc` (dùng cho lần chạy lại và các đợt sau), đổi ghép đã có → nhật ký chế độ sửa. Mã HM không có trong BOQ của HĐ → 400. Kết quả ghi thêm `ghep_moi[]` (các dòng đã ghép, chờ chạy lại).
- Chạy lại kiểm tra đợt trên đúng file đã tải lên: `POST /api/kiem_tra/kiem_tra_dot/{ma}/chay_lai` → việc nền (như `kiem_dot`), tạo kết quả mới.
- Nạp đợt đã duyệt: `POST /api/kiem_tra/kiem_tra_dot/{ma}/nap` với `{dot, ngay_nhan_hs, ghi_chu}` → `{ok, so_hang_muc, khong_khop[]}`. Đợt đã có trong CSDL → 409; muốn thay thì gửi thêm `ly_do_nap_lai` (ghi nhật ký).

## Cài đặt

| Gọi | Dùng cho |
|---|---|
| `GET /api/cai_dat` | `may_ai{ip,cong,url,model,an_danh,timeout_giay}, trich_xuat{ra_lai}, cloud{bat,nha_cung_cap,model,ty_le,khoa{anthropic,openai: {co_khoa,nguon,bon_ky_tu_cuoi}},model_mac_dinh}, du_lieu{csdl,ket_qua,danh_muc_hd,khoa_api}, ocr{che_do,thu_muc,mac_dinh,cho_toi_da,cho_nhan,che_do_ds[],mac_dinh_thu_muc,input_dir,output_dir}, ip_may_nay[]` |
| `POST /api/cai_dat` | Gửi phần cần đổi, ví dụ `{"may_ai":{"ip":"192.168.5.67","cong":11434,"model":"gpt-oss:20b"},"trich_xuat":{"ra_lai":true},"cloud":{"bat":false,"nha_cung_cap":"anthropic","model":"","ty_le":20}}` |
| `POST /api/cai_dat/kiem_tra_ai` với `{ip, cong, model, thu_model}` | Nút "Kiểm tra kết nối": `{ok, models[], co_model, giay, loi, url}` |
| `POST /api/cai_dat/tim_may_ai` | Tự tìm máy AI, chạy thành việc nền; khi xong `ket_qua.may[]` gồm `{ip, models[]}` |
| `POST /api/cai_dat/khoa` với `{nha_cung_cap, khoa}` · `DELETE /api/cai_dat/khoa/{anthropic\|openai}` | Lưu hoặc xoá API key. Máy chủ không bao giờ trả lại key, chỉ trả 4 ký tự cuối |
| `GET /api/ocr/trang_thai[?lam_moi=1]` | OCR qua task ABBYY Hot Folder riêng của phần mềm (thư mục `ocr\in` → `ocr\out` trong thư mục phần mềm, đổi được): `{che_do, thu_muc, input_dir, output_dir, task{input,output,luu[]} (đọc từ log Hot Folder trong out), usage{used_pages,limit,window_days,remaining} (trang phần mềm đã OCR 30 ngày), checks[{check,ok,detail}], ok, loi, canh_bao[]}`. Lưu qua `POST /api/cai_dat` với `{"ocr":{"che_do":"tu_dong\|luon\|tat","thu_muc":"","cho_toi_da":1800,"cho_nhan":300}}` (`thu_muc` trống = mặc định) |
| `POST /api/ocr/chay_thu` | Việc nền `ocr_thu`: đưa PDF 1 trang vào `in`, chờ DOCX ở `out` (tốn 1 trang) → `ket_qua{giay, chu}` |
| `POST /api/cai_dat` với `{"nguon_ai":"local"\|"claude"}` | Nguồn AI: máy Local AI (mặc định) hoặc Claude qua API khi máy AI không bật (dùng nhà cung cấp / model / key của mục cloud; 400 nếu chưa có key). `GET /api/cai_dat` trả `nguon_ai`; `GET /api/he_thong` → `ai{nguon:"claude", ip:"Claude", model, ket_noi}` khi đang dùng Claude. Nhật ký gửi của phụ lục / chứng từ: `ket_qua/gui_ra_ngoai/<ngày>/GUI_RA_NGOAI_*.txt` (có trong `GET /api/cai_dat/nhat_ky_gui_ngoai`) |
| `POST /api/cai_dat/thu_cloud` với `{nha_cung_cap, model?}` | Nút "Thử kết nối Claude": gửi một câu hỏi ngắn không có dữ liệu HĐ → `{ok, model, giay, tra_loi}` hoặc `{ok:false, loi}` (kèm gợi ý sửa) |
| `GET /api/cai_dat/nhat_ky_gui_ngoai` | Danh sách nhật ký `GUI_RA_NGOAI_*.txt` kèm link tải |
