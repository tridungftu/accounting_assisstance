# M4-01B5 — Kết quả kiểm độc lập trên Windows, 20/10/2026

Phần đọc nguồn và các nhóm PostgreSQL độc lập dưới đây đã đạt trên bản code B5. **Chưa nghiệm thu toàn M4; chưa có Cổng hồ sơ GUI mới để Anh xem.** Native PostgreSQL còn hai ca vướng helper test, đã giao Claude sửa ở B6.

## Bản code và cách kiểm

Claude B5 đã kết thúc thực tế: handle14083, terminal `cc8384`, exit0, xác nhận đã dừng và đúng phạm vi. Root và peer kiểm đầy đủ ba diff: thêm matching UNIQUE trước FK M17, fixture UTF-8/LF, báo cáo. Không đổi product khác, prefix1–16 hoặc M9.

- Source347: `fce56247ec5b8fc106207864d6b37a7c597ce2e25d38c60cb5f3759097827c14`.
- Runtime413: `f93aa47e74caae6a3d5c7426295180c8f4fb2861d6d612b91a175ffd8c9ac577`.
- Frozen inputs: [m4b5-runtime-frozen-c9028465588b](../var/codex-dieu-phoi/m4b5-runtime-frozen-c9028465588b/).

Root chạy trên host Windows, original no-delete guard giữ nguyên. Chỉ dùng tệp và database DEMO mới, giữ mọi tệp/staging/DB/role/attempt. Sau mỗi child đều xác nhận dừng và kiểm lại hash. Không chuyển kho thật, gửi Request thật, ghi công nợ thật hoặc bật cloud AI.

## Bằng chứng hiện tại

| Phần | Kết quả thực tế | Phạm vi chứng minh |
|---|---|---|
| Pure native | 50 PASS, 0 fail/error/skip | Bộ kiểm `test_m4_01b_tinh.py` trên host; không thay bằng AST/source grep. |
| Bốn nhóm độc lập | 4/4 đạt | Giữ bytes và staging khi thành công/retry/conflict; loader/cache thật; hai entrypoint DOCX chống TrackChanges; XLSX thật phân biệt số lỗi, finding số học, trống và số0. |
| PostgreSQL native | 8 PASS / 10 đã chạy, 2 TypeError, 0 skip | M17 dựng được; hai ca T04/T05 dừng vì helper `ten` trùng business keyword `ten`, trước khi gọi service. Chưa tính hai ca đó đạt. |
| PostgreSQL độc lập | 8/8 nhóm đạt | Nâng16→17/seed; nguồn thật; sáu nhóm biên nhận; chặn giả mạo; BOQ vật lý; Nộp/helper; replay sau đổi căn cứ; thu hồi quyền dự án. |
| HTTP/GUI, AI/OCR và nhánh sau | Chưa kiểm/chưa hoàn tất | Không suy rộng các lát backend thành toàn M4 đã xong. |

Tám nhóm PostgreSQL độc lập ghi nhận đúng: 6 fresh, 6 immediate replay, 6 later replay, 6 changed-body denial, 6 forged-fact denial, 11 scope denial và 1 lần Nộp thật trong DEMO. Negative cases đối chiếu cả trạng thái DB/catalog/sequence/tệp, không chỉ so số dòng.

Bằng chứng:

- [50 ca native](../var/codex-dieu-phoi/m4b3-pure-runtime-prep-c35a2e407b/actual-cfc336d25fd3/pure50-summary.json).
- [Bằng chứng ghép 50 + 4](../var/codex-dieu-phoi/m4b3-pure-runtime-prep-c35a2e407b/actual-probe04-3aa99767669b/parent-summary.json): actual95538 / `eb64a9`; cùng frozen context, không chạy lại 50 ca khi chỉ sửa verifier.
- [Native PostgreSQL 8/10](../var/codex-dieu-phoi/m4b5-pg-runtime-prep-20261020-l11-02/actual-ae3d05eb85da/native/receipt.json): actual97340 / `fcb78b`.
- [PostgreSQL độc lập 8/8](../var/codex-dieu-phoi/m4b5-pg-runtime-prep-20261020-l11-02/actual-independent03-58300cc355bd/parent-summary.json): actual25631 / `4a9ebf`; child/parent posthash và stop đều được xác nhận.

## Sửa bộ kiểm và giới hạn

Mọi kết quả thất bại cũ được giữ. Root/peer đã sửa riêng verifier, không đổi product hoặc tệp nguồn để làm test xanh:

1. Giá trị typed `999.0` và raw `999` được kiểm bằng Decimal hữu hạn bằng đúng literal999, cùng raw/type/ô G2 chính xác; không tolerance hoặc tính lại thành200.
2. Đáp án PG trước đó gắn nhầm dòng. XML của BOQ DEMO nguyên gốc xác định HM_A=`2/100/999` ở E/F/G2, HM_B=`3.5/20/70` ở E/F/G3. Verifier03 dùng đúng hai dòng đó, giữ raw cells và mọi kiểm khác.

Các nhóm trên không chứng minh độ chính xác Local AI/OCR, công thức Excel/cached values đầy đủ, mọi checklist thiếu độc lập hoặc mọi tổ hợp quyền/phiên giao diện. Native T05 concurrency vẫn chờ helper B6 được sửa và chạy thật.

Self-test của lượt Claude CODE_ONLY vẫn NOT_RUN; bảng trên là kiểm độc lập của Root. Thiết kế, code, kiểm độc lập và nghiệm thu người dùng là các mốc riêng.

## Việc tiếp tục

1. B6 sửa helper native PG và báo cáo, giữ 10 methods/assertions, Barrier và connection thật; product/pure giữ nguyên. Root kiểm diff rồi chạy native PG.
2. Giao Cổng hồ sơ GUI theo C03/18 ca: upload/dùng lại nguồn, trích/soát/xác nhận, phụ lục, BOQ, đợt/checklist, Nộp và reviewer đọc/tải; nối shared session và giữ giao diện nguồn.
3. Tiếp tục đủ Review L1–L3, ghép/chạy lại/OCR/báo cáo, duyệt/PDF, nghiệm thu–công nợ chung M2–M4, nháp Request và kiểm xuyên suốt. CAD để sau theo quyết định Anh.
4. CRM41–42 tiếp tục các gói đã chốt trên baseline dùng chung ổn định; các nhánh còn quyết định riêng giữ đúng trạng thái chờ, không chặn toàn bộ CRM.
