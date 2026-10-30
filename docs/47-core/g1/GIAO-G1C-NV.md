# G1c-NV · Contract nghiệp vụ theo module (CD-031, CD-032) — Codex soạn nháp, chỉ tài liệu

## Phần chung

- Bạn là worker Codex, sandbox **chỉ đọc**. **Làm ngay.**
- Câu trả lời cuối = **toàn văn phần contract của lát**; lead ghép vào `docs\47-core\g1\CONTRACT-NGHIEP-VU.md`.
- **DỪNG LẬP TRÌNH**: chỉ tài liệu.
- Không đọc kho thật, tệp bí mật, `*.local.json`, `var\`. Ví dụ JSON chỉ dùng **dữ liệu giả có chữ DEMO**: không tên đối tác thật, không số tài khoản thật.

**Căn cứ bắt buộc:**
- `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` **CD-031, CD-032** (JSON hai lớp; lớp nghiệp vụ do module sở hữu định nghĩa, Anh duyệt; `contract/` trong gói; sổ contract);
- `docs\47-core\g1\CONTRACT-DU-LIEU.md`: lớp kỹ thuật. **Dùng lại** kiểu chung `chung.v1` (tiền, ngày, mã), tham chiếu tệp, lỗi; không định nghĩa lại;
- `docs\47-core\g1\DAC-TA-CSDL.md`: khối dữ liệu, `cong_bo_*`, `danh_muc` dùng chung;
- `docs\47-core\g1\DAC-TA-SDK.md` §6: `module.json`, khai báo công bố/sự kiện.

**Mỗi contract trình bày đúng mẫu:**
1. **Mã** (tiếng Việt không dấu, snake_case, `.v1`) · **mục đích** (1–2 câu nghiệp vụ) · **module sở hữu** · **module được đọc** · **loại** (dữ liệu công bố / sự kiện / đầu vào nguồn).
2. **Bảng trường**, mỗi trường gồm:
   - tên;
   - nghĩa nghiệp vụ;
   - kiểu;
   - bắt buộc / tùy chọn;
   - đơn vị (VND/USD, %, ngày);
   - **nguồn** (tài liệu thiết kế § hoặc `tệp:dòng` mã/bảng hiện có).
3. **Một ví dụ JSON DEMO đầy đủ** (hợp lệ JSON).
4. **Trạng thái/phiên bản:** `nhap`; ghi rõ trường nào còn chờ Anh chốt.

Lấy trường từ thiết kế **đã chốt**. Không bịa nghiệp vụ; chỗ thiết kế chưa chốt ghi "chờ Anh". Dùng lại contract chung (`doi_tuong`, `du_an` ở lát Chung) thay vì nhúng lại toàn bộ.

Tối đa khoảng 6 trang mỗi lát. Đầu câu trả lời có bảng tóm tắt các contract của lát: mã · mục đích · sở hữu · được đọc.

## Lát NV-CRM · CRM · Hợp đồng bán hàng

Contract:
- `hop_dong_ban`: phiên bản, tham số, **lịch thanh toán** (% · giá trị gồm VAT · trong đó VAT, VAT cọc dồn đợt kế), mốc dự kiến/thực tế;
- `bao_gia`;
- `du_an_dang_ban`: thông tin chung, giá & thuế, phí, mốc, tiến độ % + mốc, lô/căn.

**Căn cứ:**
- `D:\Claude\Phan mem ho tro ke toan\42-man-hinh-crm-ke-toan-va-giao-ket.md`, `45-review-man-bao-gia-sau-lap-trinh.md` (§8–§9), `49-trang-chu-luoi-icon.md`;
- `THIET-KE-MODULE-DE-CHOT-2026-10-20\CRM-CHUC-NANG-VA-THIET-KE.md`;
- CD-006/007 (mốc dự án), CD-022/023/024 (Dự án đang bán, Báo giá, VAT cọc);
- `docs\46-chuyen-doi-dieu-phoi\KK-UI-DA-BG.md`;
- tài liệu "50" nếu tìm thấy (tìm trong `D:\Claude\Phan mem ho tro ke toan\`);
- mã: `src\kho_tri_thuc\k2\crm*.py`, `sql_crm_*.py`.

## Lát NV-M4 · M4 · Nghiệm thu & chi phí dự án

Contract: `hop_dong_thau`, `phu_luc`, `boq`, `dot_thanh_toan`, `ket_qua_kiem_dot` (kết quả kiểm K/B/C/P), `nghiem_thu`.

**Căn cứ:**
- `THIET-KE-MODULE-DE-CHOT-2026-10-20\M4-XAY-DUNG-VA-NGHIEM-THU.md`;
- CD-011 (8 màn Review);
- QD-20261026-09 (phụ lục = THEM/THAY/BO dòng; BOQ/đợt là dòng);
- mã `src\kho_tri_thuc\m4\` (schema `m4.*`).

## Lát NV-M2 · M2 · Hóa đơn mua vào

Contract:
- `hoa_don_mua_vao`: đã nhận, đích hạch toán, trạng thái. **Dùng lại** `hoa_don.v1` kỹ thuật cho phần đọc XML, chỉ thêm phần nghiệp vụ;
- `cong_no_phai_tra`.

**Căn cứ:**
- `D:\Claude\Phan mem ho tro ke toan\43-M2-00-nhan-nguon-tu-cong-thue.md`;
- `THIET-KE-MODULE-DE-CHOT-2026-10-20\M2-00-NHAN-NGUON-TU-CONG-THUE.md`, `M2-MUA-HANG-VA-CONG-NO.md`. Bản 20/10 **chưa được Anh chốt** (TL 55 §9): trường nào chỉ có ở bản này ghi "chờ Anh";
- contract công bố hóa đơn M0064 (`k2\sql_cong_bo_hoa_don.py`).

## Lát NV-CHUNG · Contract chung + sự kiện

- **Contract chung:**
  - `doi_tuong` (mã Junsky);
  - `du_an`;
  - `but_toan_de_xuat`: dòng Nợ/Có, TK chi tiết, mã đối tượng, số tiền; quy tắc "thà bỏ sót còn hơn nhập sai";
  - `tep_nhap_junsky`: hai sheet `CB_tmpEntry1/2`, Mức 2 còn khóa.
- **Sự kiện:** `tien_da_noi_dot`, `ban_giao_da_duyet`, `moc_da_xay_ra`, `hop_dong_hieu_luc`, `hoa_don_da_nhan`. Mỗi sự kiện ghi: module phát, module nhận, khi nào phát, khóa chống trùng.
- **Căn cứ:**
  - `D:\Claude\Phan mem ho tro ke toan\CLAUDE.md`;
  - `docs\HUONG-DAN-DINH-KHOAN.md`;
  - tài liệu 08 file nhập Junsky (tìm trong `D:\Claude\Phan mem ho tro ke toan\`);
  - mã `src\kho_tri_thuc\` phần xuất Junsky;
  - bus `ha_tang\bus_su_kien.py`;
  - `THIET-KE-MODULE-DE-CHOT-2026-10-20\M0-NEN-TANG-DUNG-CHUNG.md`.
- **Cuối lát thêm mục "Quy tắc chung lớp nghiệp vụ"** (CD-032, ≤ 1 trang):
  - khi nào dùng lại / mở rộng / tạo mới;
  - đặt tên;
  - phiên bản;
  - ai duyệt;
  - trùng nghĩa → đỏ.
