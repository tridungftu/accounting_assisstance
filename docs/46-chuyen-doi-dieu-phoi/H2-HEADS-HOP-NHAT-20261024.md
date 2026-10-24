# H2 — sổ head trước hợp nhất

Ngày rà: 24/10/2026. Repo: nhánh hop-nhat-20261023, nền chinh ở commit 59b7d8e.

- Có 76 thư mục code-frozen: 57 ở cấp điều phối và 19 bản lồng/lịch sử. Có 36 đầu việc/frozen head cấp điều phối; bảng chi tiết ở HEADS-HOP-NHAT-20261024.csv.
- Có 26 thư mục isolated-head-jobs; cả 26 đều có workspace. Đây là bản sao repo không có .git, không được nhập cả cây một cách mù quáng. Các workspace được đối chiếu bằng allowlist/release và frozen snapshot. crm-word5097-report chỉ là báo cáo chẩn đoán; m4-financial-basis-a chưa có frozen terminal tương ứng nên giữ nhánh lưu.
- Hầu hết receipt ghi kiểm trên successor là NOT_RUN hoặc NOT_RUN_ON_SUCCESSOR; terminal/freeze không đồng nghĩa kiểm độc lập hay nghiệm thu. Hai gói m4b2, m4b3 thiếu terminal receipt; giữ trên nhánh lưu.
- Đích Git của từng gói sẽ được ghi sau khi thử merge ba chiều trên hop-nhat. Xung đột hoặc head chưa terminal sẽ ở luu/<ten-nhanh> từ nền H1. Không sửa code để ép test qua.
- git diff --check trên nền đã phát hiện whitespace có sẵn trong HANG-DOI-YEU-CAU.md và docs/PHAM-VI-UY-QUYEN-CODEX.md; nội dung giữ nguyên trong H1 theo chỉ đạo commit nguyên trạng.
