# TAN-DUNG-CODE — mã nguồn đã có trước hợp nhất

24/10/2026 - Nền chinh tại 59b7d8e. Bảng này là kiểm kê code, không phải nghiệm thu. Các kết quả test ghi từ receipt/báo cáo riêng; phải chạy lại sau hợp nhất trước cổng B.

| Lát / chức năng | Frozen head | Tệp chính | Số tệp test | Mức đã kiểm / còn thiếu |
|---|---|---|---:|---|
| crm-g4 | crm-g4-code-frozen-e5be9c82b636 | crm_g.js, crm_g.py, pg_migrations.py +1 | 3 | Code đóng băng; kiểm lại trên head hợp nhất. |
| crm-g5-doi-chieu-20261023-01 | crm-g5-doi-chieu-20261023-01-code-frozen-3cb518064b79 | crm_g.py | 2 | Code-only freeze; review trên head hợp nhất còn pending. |
| crm-g6a-20261022-01 | crm-g6a-20261022-01-code-frozen-7c9df8b14ad4 | — | 0 | Code đóng băng; kiểm lại trên head hợp nhất. |
| crm-g6a-m25-registration-20261023-01 | crm-g6a-m25-registration-20261023-01-code-frozen-806fbb5ee451 | pg_migrations.py | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| crm-m4-three | crm-m4-three-code-frozen-2a4b1bf55d3f | crm_g.js, crm_g.py, pg_migrations.py +2 | 4 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m2-00a-source7-manifest-20261023-01 | m2-00a-source7-manifest-20261023-01-code-frozen-3a320c0ab55a | — | 1 | Có kiểm producer trước đó; cần chạy lại trên head hợp nhất. |
| m2-00b-fix01 | m2-00b-fix01-code-frozen-d269061a1c29 | dieu_phoi.py, khach.py | 2 | Python 60/60 + independent 3/3 được báo đạt; Node58 trên fixed head còn chờ. |
| m2-00b-owned-rpc-20261023-01 | m2-00b-owned-rpc-20261023-01-code-frozen-d69e5bd05516 | __init__.py, __init__.py, cau_hinh.py +3 | 4 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-02c-backend-20261022-01 | m4-02c-backend-20261022-01-code-frozen-cdb836d0e325 | m4.py, pg_migrations.py, m4_demo.py +4 | 3 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-02c-integration-repair-20261023-01 | m4-02c-integration-repair-20261023-01-code-frozen-5b20eead36ad | — | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-02c-ui-20261022-01 | m4-02c-ui-20261022-01-code-frozen-bed57155117e | m4_duyet_pdf.js, m4.css, m4.js | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-02c-ui-fix01-20261022-01 | m4-02c-ui-fix01-20261022-01-code-frozen-e9d78d5826b4 | m4_duyet_pdf.js, m4.js | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-03a-gui-20261023-01 | m4-03a-gui-20261023-01-code-frozen-ff1677c7c157 | m4_ke_toan.js | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-03a-kt-backend-20261023-01 | m4-03a-kt-backend-20261023-01-code-frozen-dccd810be387 | ke_toan_nghiem_thu.py, sql_ke_toan_nghiem_thu.py | 3 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-03b-common-identity-20261023-01 | m4-03b-common-identity-20261023-01-code-frozen-4538d9562cd5 | ghi_nhan_chung.py, sql_ghi_nhan_chung.py, ghi_nhan_nghiem_thu.py | 2 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-03b-common-identity-fix01 | m4-03b-common-identity-fix01-code-frozen-45d12f685ee6 | ghi_nhan_chung.py, sql_ghi_nhan_chung.py | 2 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-03b-common-identity-fix02 | m4-03b-common-identity-fix02-code-frozen-eefa3bb0d8e6 | sql_ghi_nhan_chung.py | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-03b-common-identity-fix03 | m4-03b-common-identity-fix03-code-frozen-549a1e912393 | sql_ghi_nhan_chung.py | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-03b-common-identity-fix04 | m4-03b-common-identity-fix04-code-frozen-5d363a87f3f3 | sql_ghi_nhan_chung.py | 1 | Chưa có runtime xác minh; kiểm pure/native còn pending. |
| m4-04a-request-backend-20261023-01 | m4-04a-request-backend-20261023-01-code-frozen-60589ad2fbd3 | request_nhap.py | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-04b-request-wiring-20261023-01 | m4-04b-request-wiring-20261023-01-code-frozen-2902e80fd63e | m4_request.py | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-04b-ui-copy-20261023-01 | m4-04b-ui-copy-20261023-01-code-frozen-c478b6382bb0 | duyet_dot.py, m4_duyet_pdf.js | 3 | Python 27 + CJS 76 được báo đạt; GUI successor chưa xác minh. |
| m4-04c-m27-oracle02 | m4-04c-m27-oracle02-code-frozen-a793805297d6 | — | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-04c-request-m27-20261023-01 | m4-04c-request-m27-20261023-01-code-frozen-9167c0cbb9ee | pg_migrations.py | 2 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-backend-crm-three | m4-backend-crm-three-code-frozen-8390cbe315e6 | crm_g.js, xay_dung.py, chung_tu_adapter.py +1 | 4 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-kt-m26-registration-20261023-01 | m4-kt-m26-registration-20261023-01-code-frozen-1afefc0aa71e | — | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-l3-boundary-test-20261022-01 | m4-l3-boundary-test-20261022-01-code-frozen-9e15dc26ff34 | — | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-master-reuse | m4-master-reuse-code-frozen-60d4019cca91 | m4.py, xay_dung.py, m4.js +1 | 4 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-review-basis-20261022-01 | m4-review-basis-20261022-01-code-frozen-ab19f1b9cd0f | review.js | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4-review-basis-c18-testfix-20261023-01 | m4-review-basis-c18-testfix-20261023-01-code-frozen-60910216c26e | — | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4b2 | m4b2-code-frozen-727f1b740fb8 | docx_an_toan.py | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| m4b3 | m4b3-code-frozen-99d7521d2aa8 | — | 0 | Code đóng băng; kiểm lại trên head hợp nhất. |
| source6-e3-docx-tables-20261023-01 | source6-e3-docx-tables-20261023-01-code-frozen-bee008a24f21 | — | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| source6-g5-e5-20261023-01 | source6-g5-e5-20261023-01-code-frozen-352344e312c3 | trich_chung_6.py, trich6_host.py | 1 | PDF DEMO 15/15 được báo đạt; Word G3 và whole-engine chưa đạt. |
| source6-g5-e5-ordered-fix01 | source6-g5-e5-ordered-fix01-code-frozen-69cbcff74e92 | — | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |
| source6-lazy-excel-20261023-01 | source6-lazy-excel-20261023-01-code-frozen-f17a38d5a9e9 | — | 1 | Code đóng băng; kiểm lại trên head hợp nhất. |

Ranh giới lưu giữ: TRI-THUC-CFO.json, cấu hình máy, bằng chứng runtime và cache sinh tự động nằm ngoài commit. Code/test/fixture được giữ nguyên; workspace full-copy không được nhập cả cây, chỉ dùng file trong allowlist hoặc snapshot hash.
