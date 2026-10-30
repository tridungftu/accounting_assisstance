# G2 · giao G2-CR2 — contract `bao_gia.v1` theo CD-038 (1A, 2B)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-cr1` (đã có contract `du_an_dang_ban.v1` và test G2-CR1 — làm theo đúng mẫu đó).

## Lát G2-CR2

**Tệp:**
- `src\kho_tri_thuc\modules\crm\contract\bao_gia.schema.json`
- `src\kho_tri_thuc\modules\crm\contract\bao_gia.demo.json`
- `tests\test_g2_cr2.py`

**Căn cứ:**
- `docs\47-core\g1\CONTRACT-NGHIEP-VU.md`:
  - §2 `bao_gia.v1` (dòng ~879);
  - "Cơ sở VAT, thang tiền và bất biến" (dòng ~526, ~706);
  - quy ước NV-CRM;
  - quy tắc `nguon_tep_ids`.
- **CD-038:**
  - **1A:** lịch chỉ gồm **giá bán chia %**, Σ% = 100; phí theo dõi riêng.
  - **2B:** cho phép cọc là đợt cuối hoặc nhiều đợt cọc. VAT của đợt cọc dồn vào đợt **không cọc** gần nhất phía sau; hết thì dồn ngược về đợt không cọc gần nhất phía trước. Toàn đợt cọc → lỗi.
- TL 45 §9 BG-27 (`D:\Claude\Phan mem ho tro ke toan\45-review-man-bao-gia-sau-lap-trinh.md`).

**Việc:**
- Schema đúng trường của đặc tả; không thêm nghiệp vụ.
- Bất biến nào JSON Schema diễn đạt được thì đưa vào schema; bất biến số học (Σ% = 100, ΣT = V, ΣA = G, T đợt cọc = 0) kiểm bằng hàm kiểm trong **test**, không đặt mã nghiệp vụ mới vào gói.
- Ví dụ DEMO có đợt cọc **cuối** và **hai đợt cọc liền nhau**.

**Test** (thuần):
- schema hợp lệ meta-schema 2020-12; ví dụ đạt schema; `$ref` phân giải offline;
- Σ% ≠ 100 → đỏ;
- ví dụ thỏa bất biến dồn VAT 2B. Kiểm thêm bằng dữ liệu tạo trong test: cọc cuối, 2 cọc liền, cọc xen giữa;
- toàn đợt cọc → đỏ;
- phí nằm ngoài lịch giá bán.
- Chỗ đặc tả ghi "chờ Anh": giữ nguyên và ghi "Cần lead".

Báo cáo ≤ 3 dòng.
