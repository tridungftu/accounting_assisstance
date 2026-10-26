# M4-DL1b: M4 · Nghiệm thu & chi phí dự án, bổ sung lược đồ chép Review (3 điểm "nên sửa" của review DL1 vòng 2; CD-011)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`.
- Ghi tệp UTF-8 không BOM. `pg_migrations.py` giữ LF (thuộc tính `eol=lf`); không ghi CRLF.
- Sandbox không ghi được `.git`: **không commit**.
- Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl1b`, dựng từ hợp nhất. M4-DL1 đã gộp thành **M0038** (`M0038_M4_REVIEW_CHEP`); M0039 là MTQ-1.

**Căn cứ:**
- `src/kho_tri_thuc/m4/sql_review_chep.py`: docstring có quy tắc bản hiện hành, mỗi `nguon_id` là một lần chụp.
- `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-m4-dl1-v2.md`.
- `docs\46-chuyen-doi-dieu-phoi\M4-KIEM-KE-CHEP-REVIEW.md`.

**Nguyên tắc chung:** M0038 đã phát hành, **không sửa** M0038 hay hằng `M4_REVIEW_CHEP_SQL`.
- Thêm hằng mới `M4_REVIEW_CHEP_B_SQL` trong `sql_review_chep.py`. Tệp này vẫn chỉ chứa hằng SQL, không import.
- Append migration mới vào cuối `pg_migrations.py` với tên tạm `M00xx_M4_REVIEW_CHEP_B` và dấu `# M4-DL1b — CD-011:`. Lead sẽ đánh số khi gộp.
- Test không ghim số thứ tự: định vị theo dấu như test DL1.

**Việc (M4_REVIEW_CHEP_B_SQL):**
1. UNIQUE `(nguon_id, hop_dong_id)` trên `m4.review_chep_hop_dong`, để một lần chụp không có hai `ma_hd` cùng trỏ một HĐ.
2. Cột `chup_luc timestamptz NOT NULL` **không DEFAULT** trên `m4.review_chep_nguon`. Đây là thời điểm chụp tệp nguồn, do công cụ nạp truyền vào.
   - Bảng đang có dòng thì migration phải dừng với lỗi rõ. Không tự điền, không nới `chi_ghi_them`.
   - Index `(chup_luc DESC, id DESC)`.
   - Cập nhật docstring: bản hiện hành sắp xếp theo `chup_luc`, không theo `nhap_luc`.
3. Quy tắc bản hiện hành tính HĐ đã xóa ở lần chụp sau. Hàm SQL chỉ đọc `m4.review_chep_hien_hanh(p_hop_dong_id uuid)` trả `nguon_id`:
   - Lấy lần chụp **mới nhất toàn bộ** (theo `chup_luc DESC, id DESC`). Mỗi lần chụp là bản sao đủ của cùng một CSDL Review.
   - Nếu HĐ không có trong lần chụp đó thì trả NULL, nghĩa là HĐ đã xóa ở nguồn.
   - Không lùi về lần chụp cũ hơn có HĐ đó.
   - Hàm không dùng `SECURITY DEFINER`; quyền đọc theo RLS sẵn có.
   - Nếu thấy có thể có nhiều CSDL Review nguồn (vd. mỗi pháp nhân một tệp) thì ghi "Cần Anh": khi đó cần cột phân biệt nguồn. Không tự thêm.
4. Không thêm cột hay DTO lộ `file_nguon` hoặc đường dẫn. DTO thuộc lát DL2; chỉ ghi chú cho DL2 trong docstring.

**Test:** sửa `tests/test_m4_review_chep_schema.py`.
- Phần tĩnh: hằng mới chỉ SQL; M0038 không đổi byte (so tiền tố); registry append đúng sau M0038 theo dấu.
- Phần PG (`skipUnless KHO_PG_DSN_TEST`, như tệp đang làm):
  - trùng `(nguon_id, hop_dong_id)` bị từ chối;
  - thiếu `chup_luc` bị từ chối;
  - hai lần chụp: HĐ có ở lần 1, mất ở lần 2 thì hàm trả NULL; HĐ có ở cả hai thì trả lần 2;
  - trùng `chup_luc` thì `id` phân xử;
  - app_web không có quyền ghi.
- Chạy thuần: `python -X utf8 -m unittest tests.test_m4_review_chep_schema tests.test_pg_schema`, với PYTHONPATH=`src;.;tests`.

**Tệp (≤ 3):** `m4/sql_review_chep.py`, `ha_tang/pg_migrations.py`, `tests/test_m4_review_chep_schema.py`.

**Báo cáo (≤ ¼ trang):** số test, phần "Cần Anh", thông điệp commit `[M4-DL1b] …`.
