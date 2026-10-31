# G3 · AI-2 — adapter `ai.hoi@1` qua cổng AI chung, cờ chỉ Local, manifest `e_hoi_ai`

**Phần chung:** như `GIAO-G2-DOT-A.md`, mục "Phần chung", và `docs\47-core\engine\GIAO-ENGINE-1.md` (phần `e_hoi_ai`, bảng dùng lại / bọc). **Nền:** `hop-nhat-20261023`, đã có:
- AI-1a DTO;
- AI-4a khung chạy;
- AI-1b contract `hoi_ai.v1`;
- G2-20 SDK engine.

**Căn cứ chốt:** `docs\47-core\engine\QUYET-DINH-AI-1B.md` §6; chuẩn SDK v1.1 mục 1.

**Tệp:**
- `src\kho_tri_thuc\engines\e_hoi_ai\hoi.py`
- `src\kho_tri_thuc\engines\e_hoi_ai\engine.json`
- `tests\test_g3_ai_2.py`

**Việc:**
- **`hoi.py`** bọc `CongAI.goi` (`src\kho_tri_thuc\tri_thuc\cong_ai.py`) — không viết client mới:
  - nhận đầu vào `hoi_ai.v1` (kiểm schema), chuyển sang `YeuCauAI`;
  - `chi_cuc_bo=true` → instance theo request `cloud_bat=False`, không đổi instance chung;
  - trả `tra_loi_ai.v1`.
- **`engine.json`:**
  - khai capability `ai.hoi@1` với `dau_vao: hoi_ai.v1`, `dau_ra: tra_loi_ai.v1`;
  - `headless=true`; theo schema G2-17b;
  - chỉ khai năng lực đã có test trong lát này.
- **Không gọi AI / mạng thật** — provider Local giả, Cloud giả, Mask giả.

**Test:**
- `chi_cuc_bo=true` → **0 lời gọi Cloud** trong cả 3 tình huống (Local lỗi / không chắc / được chọn kiểm xác suất);
- hai request khác cờ chạy xen kẽ không ảnh hưởng nhau;
- `chi_cuc_bo=false` không tự bật Cloud khi công tắc toàn cục tắt;
- đầu vào sai schema bị từ chối;
- manifest đạt schema G2-17b;
- ca "M9 luôn gửi `chi_cuc_bo=true`": dựng hàm trợ giúp phía module M9 giả lập; ghi rõ đây là ca mẫu, cổng kiểm thật do lead grep.

Báo cáo ≤ 3 dòng.
