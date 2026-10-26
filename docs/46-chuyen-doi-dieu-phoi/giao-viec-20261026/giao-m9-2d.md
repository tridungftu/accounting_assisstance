# M9-2d: M9 · Vốn vay & đầu tư tài chính, câu hỏi số dư/lãi suất hiện hành trả từ snapshot Sheet có mốc, không qua AI (thuần, CD-015 mục 3)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. Không commit. Không mạng, không AI thật, không thư viện ngoài. Không xóa file.
- Chỗ chưa rõ: dừng, ghi "Cần lead".
- Làm trong worktree hiện tại, nhánh `lat/m9-2d`, dựng từ hợp nhất. Đã có:
  - `m9/snapshot_sheet.py`: `lap_snapshot` → `{moc, nguon, khoan_vay[...]}`;
  - `m9/dich_vu_hoi_dap.py`: `hoi(...)` → tìm hợp đồng + `hoi_dap_vay.tra_loi`, chỉ Local.

**Căn cứ:**
- CD-015 mục 3: "số dư/lãi suất chỉ từ snapshot Sheet có mốc".
- Thiết kế M9 §1, §5.1–5.2:
  - hỏi đáp số dư luôn ghi "nguồn Sheet, mốc dd/mm/yyyy hh:mm";
  - hai nguồn lệch thì báo lệch, không tự chọn;
  - tiền luôn kèm đơn vị.

**Việc:**
1. Tệp mới `src/kho_tri_thuc/m9/so_du_snapshot.py`, hàm `tra_so_du(cau_hoi, snapshot) -> dict | None`.
   - Nhận diện câu hỏi về **dư nợ / số dư / lãi suất hiện hành / kỳ điều chỉnh / ngày đáo hạn** bằng từ khóa có dấu và không dấu.
   - Lọc theo mã khoản vay, ngân hàng hoặc pháp nhân nếu câu hỏi có nêu; so khớp đúng chuỗi trong snapshot sau chuẩn hóa, **không** khớp mờ.
   - Không phải loại câu này → trả `None`.
   - Có → `{"trang_thai": "TU_SNAPSHOT", "tra_loi": <câu tiếng Việt>, "dong": [{ma_khoan_vay, ngan_hang, phap_nhan, truong, gia_tri, don_vi}], "nguon": "Sheet", "moc": snapshot["moc"]}`.
     - Câu trả lời luôn kết thúc bằng "(nguồn Sheet, mốc dd/mm/yyyy hh:mm)".
     - Tiền có đơn vị theo `tien_te`; lãi suất có "%/năm"; ngày dd/mm/yyyy.
     - Khớp nhiều khoản → liệt kê, không cộng khác đồng tiền.
   - Không khớp khoản nào → `{"trang_thai": "KHONG_THAY_TRONG_SNAPSHOT", ...}` kèm mốc.
2. `m9/dich_vu_hoi_dap.py` thêm tham số tùy chọn `snapshot=None`.
   - Có snapshot và `tra_so_du` trả khác `None` → trả kết quả đó, **không gọi cổng AI**, vẫn ghi nhật ký (`trang_thai` tương ứng).
   - Ngược lại → luồng hợp đồng như cũ.
   - Không truyền `snapshot` → hành vi cũ giữ nguyên.
3. Không suy số dư từ hợp đồng, không tính lãi.

**Test, tệp mới `tests/test_m9_so_du_snapshot.py`** (snapshot DEMO dựng bằng `lap_snapshot` hoặc dict):
- "dư nợ khoản vay A là bao nhiêu" / "du no khoan A" → đúng số, có đơn vị, có mốc.
- "lãi suất hiện hành NH B" → %/năm + mốc.
- Mã không có → `KHONG_THAY_TRONG_SNAPSHOT`.
- Câu về điều khoản ("phí trả nợ trước hạn") → `None`, đi luồng hợp đồng.
- Qua `hoi(..., snapshot=...)`: câu số dư **không** gọi cổng AI (cổng giả đếm lần gọi = 0) và có ghi nhật ký.
- Không float.
- `tests.test_m9_dich_vu_hoi_dap` vẫn đạt.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_so_du_snapshot tests.test_m9_dich_vu_hoi_dap`, PYTHONPATH=`src;.;tests`. Không có `python` thì ghi NOT_RUN.

**Tệp (3):** `m9/so_du_snapshot.py`, `m9/dich_vu_hoi_dap.py`, `tests/test_m9_so_du_snapshot.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M9-2d] …`.
