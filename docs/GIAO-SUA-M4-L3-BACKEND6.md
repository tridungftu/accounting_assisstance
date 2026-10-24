# M4 L3 — backend follow-up candidate (private)

**ROOT_REVIEW_REQUIRED · NOT_DISPATCHED · NOT_CODED · CODE_ONLY khi Root cấp release.** Đây là gói sửa hữu hạn trong M4 đã chốt; không đổi kiến trúc, schema, engine, master, receipt framework hoặc thứ tự hàng chờ.
Authority tĩnh: freeze `m4-02b-fix01-partial-frozen-b04b01c1faef/files` (terminal82bcfd); report service H43e0aa2462aa2dffdf8c62cfe7a2a8bfbb70f8de01834bad362d7183e8f657e8 và adapter H9c87ffc87f0d74596132f2bf16f0d9d8935c87a0ecb47feee7e4d06fe4f822bb. Đây chưa phải baseline để dispatch sau lượt UI đang chạy.

## Scope tối thiểu đề nghị: đúng 6 file hiện có, NEW0

| File | Delta hữu hạn |
|---|---|
| `src/kho_tri_thuc/k2/xay_dung.py` | S1: giữ UNKNOWN từ fallback publish; giữ current rights/basis/receipt và same-key reconcile. |
| `src/kho_tri_thuc/m4/chung_tu_adapter.py` | A1 giới hạn alias header rõ nghĩa; A2 lưu hai lớp nguồn nguyên trước alias và kết quả hiệu lực, gắn evidence. |
| `src/kho_tri_thuc/m4/nguon_review.py` | Mở rộng đúng locator L3 hiện có để giữ header/cell/column/row native; không thêm classifier/parser. |
| `tests/test_m4_02b_pure.py` | Regression A1/A2 trên bytes DEMO chụp một lần; giữ các invariant NULL/UOM/form/stale/manual-target. |
| `tests/test_m4_02b_k2.py` | S1 regression tại transaction/commit boundary thật; K2 factory tiêm client #6 thật cho mọi service/reopen/concurrency. |
| `docs/BAO-CAO-M4-02B.md` | Append kết quả/gate/thử đã viết và NOT_RUN_CODE_ONLY lên bản SAU UI, không ghi đè báo cáo của lượt UI. |

Các file khác chỉ đọc, gồm HTTP/app.js/shell, migrations/toàn SQL, worker, vendor và source app37. Không sửa M9, không bootstrap toàn kho; không tạo engine/client/model catalog song song. Không đưa DSN/token/credential/dữ liệu thật vào code/report.

## S1 — fallback commit UNKNOWN không bị che

Seam hiện có: `XayDungK2._tx_review`618–628, `_chung_tu_cong_bo`1368–1415, `_chung_tu_doi_soat`1417–1440. Fallback1401–1407 hiện bắt cả DataError rồi raise SQL error cũ; UNKNOWN1392–1394 của fallback bị mất.
- Giữ nguyên UNKNOWN (`M4_KET_QUA_CHUA_RO`) từ fallback; phân biệt đúng các lỗi rõ/quyền/phạm vi, không khẳng định FAILED khi kết quả commit chưa biết. Không phát compute/key/run mới và không mở thêm cơ chế retry.
- Regression gọi hàm publish thật, không patch toàn `_chung_tu_cong_bo` như test K08b414–425. Tiêm SQL error thường ở publish đầu rồi OperationalError/InterfaceError tại transaction/commit fallback; quan sát mã UNKNOWN thật ở ngoài.
- Có ca ACK mất trước commit và sau commit; chứng minh trạng thái DB/evidence tương ứng, cùng body/key reconcile về đúng run cũ, 0 worker chạy lại, 0 run/receipt trùng và lịch sử/artifact nguyên. Thử lại sau FINAL vẫn cùng FINAL. Mock boundary tách nhãn khỏi kiểm PostgreSQL thật.

## A1/A2 — compatibility mỏng, giữ nguyên dữ kiện nguồn

Seam adapter47,73–103,158–163,797–803; locator `NR.l3_vi_tri_xlsx`708–741 / `l3_vi_tri_docx`744–774 hiện chỉ có sheet/table và danh sách dòng vật lý, chưa có cột header.
- Alias chỉ header tên rõ nghĩa được chứng minh (ví dụ `Tên hàng`); không alias `Tên hàng / Nhà sản xuất`, `Tên hàng (Hãng sản xuất)`, Hãng/NSX hoặc header mơ hồ. Không nới regex bằng hậu tố tùy ý; giữ quyết định nguồn và ghi giới hạn khi không xác định, không bịa cột tên.
- Giữ riêng bản trích/rows nguyên nguồn trước thích nghi (tên/model/NSX/raw cells/header/quote) và bản hiệu lực sau alias; mapping manual/auto tiếp tục giữ riêng. Không lấy provenance.auto hiện chỉ row_id/khoa/khop làm bản nguồn pre-alias.
- Alias evidence gắn đúng raw hash/tep, sheet hoặc bảng, header row/cột và dòng/cell nguồn; không gộp record cùng chuỗi header ở hai vị trí khác nhau. DOCX merged/logical column khác physical cell phải ghi rõ; vị trí không xác định → NOT_AVAILABLE/LIMITED có lý do, không giả locator CHECKED.
- Dùng lại code/parser vendor trong worker-local namespace và locator có sẵn; không monkeypatch module/vendor/source app, không đổi raw bytes/row_id ổn định hay ngưỡng C01–C09. Evidence theo vùng đọc/giới hạn/finite-tree hiện hành, không nới guard để được PASS.
- Acceptance: positive header có tên/model/NSX riêng vẫn đúng; combined hoặc không dấu mơ hồ (như `Ten hang`) không bị compatibility layer tự alias sang cột tên; header/alias không dấu rõ nghĩa mà parser nguồn đã nhận (như `Ten vat tu`) vẫn giữ quyết định native; hai sheet/bảng cùng header có hai locator; blank rows/offset/merged cells đúng physical evidence. Pre-alias output còn nguyên và truy về đúng bytes đã chụp; hiệu lực mới đúng mà bản nguồn/lịch sử không bị ghi đè. Giữ NULL≠0, khác UOM chưa so được và form metadata CHECKED nhưng rows NOT_CONFIGURED theo FIX01.

## K2 fixture — dùng đúng ONE engine #6; gate actual host riêng

Factory `tests/test_m4_02b_k2.py:96–101` thiếu trich6; K01:174 đòi XONG nhưng service102–112/379–380 chủ động chặn None. Chỉ đặt URL môi trường không tiêm được client vào constructor này.
- Dùng lại `nguon/trich6_host.py:Trich6Host`199–219, `.client`396–402 và `nguon/trich_chung_6.py:Trich6Client`154–178 + catalog XD38–39/preflight `.nang_luc`241–270. Một owned host/implementation/catalog chung, client gắn scope DataRoot DEMO; không clone extractor hoặc nhét fake XONG/tham số/kết quả.
- Tạo host/đăng ký stop ngay trước start; mọi `_svc_moi`/reopen/2-kết-nối đều nhận client đúng host và scope. Dùng lại lifecycle thực trong `tests/test_trich6_host.py:525–566`; đây là mẫu seam, không phải bằng chứng test K2 đã chạy. Host/guard/endpoint chỉ loopback động, môi trường lọc, token chỉ trong bộ nhớ, nguồn37 chỉ đọc.
- GATE thực trước positive K01: source37/implementation và catalog XD khớp; host start/readiness thực; shared-client typed capability RULE_ONLY; DOCX DEMO thật qua cùng endpoint trả request/source/catalog/seal đúng. Nếu chưa có/không khớp, báo NOT_READY/NOT_VERIFIED và ngừng positive K2; không dùng legacy extractor, mock host hoặc sửa service guard để đi vòng.
- K01 chỉ XONG từ trích thật rồi tham số được phòng dự án soát/xác nhận như hiện hành; không fake trạng thái nghiệp vụ. PG dùng DB mới template0, ordinary app role và owner-connection đúng factory, chỉ CRM/M4 DEMO seed; retained outputs/DB/role, không DELETE/DROP/cleanup. Skip/NOT_RUN không tính PASS.

## Trình tự và giới hạn nghiệm thu

1. Chờ UI writer terminal + owned Job empty; Root freeze/kiểm UI rồi rebind scope6/pins/settings/prompt, đặc biệt báo cáo chung. Không dispatch hoặc sửa/hashing live source trong lúc UI còn chạy.
2. Code S1 và A1/A2 độc lập về logic; thêm test đúng từng nhánh, đọc lại thay đổi; báo NOT_RUN_CODE_ONLY. Locator phải xong trước assertion A2; không kéo thêm UI/HTTP/SQL/schema vào gói.
3. Sau Root cho runtime riêng: kiểm native A1/A2 và S1 boundary trước; bật gate #6 thật trước K01/positive PG + same-key reconcile. Không coi isolated mock là positive PG; nếu host gate chưa đủ, tách prerequisite runtime thay vì bịa kết quả.
4. HTTP/app-factory hiện có (`giao_dien/m4.py:257–261`, `server.py:39–45`) dùng client chung; HTTP/GUI xuyên suốt là gate kế tiếp, không tự mở scope sửa trong gói6file này. Host prerequisite cần đổi implementation/source37 ngoài scope → dừng nhánh đó, Root xử lý riêng; các phần native độc lập vẫn báo riêng.
5. Root kiểm độc lập từng phần và báo giới hạn. L3 analysis không phải duyệt đợt/accepted nghiệm thu/công nợ/Request; các gói M4 sau và CRM41–42 vẫn giữ nguyên phạm vi đã chốt.