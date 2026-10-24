# Giao code reader nguồn kho #10 → M5 — gói đầu độc lập

**19/10/2026 · PREPARE_ONLY · chưa giao coder/chưa thực thi/chưa nghiệm thu.** Anh xác nhận phần mềm #10 quản lý kho đã có code; phải dùng lại producer đó. Gói này bổ sung reader thuần trong repo kế toán, không xây lại kho. M9 vẫn dừng tuyệt đối; không sửa/vận hành M9 hoặc dùng việc sửa common M9 làm điều kiện khởi đầu.

Căn cứ: TL35§8.6; `BINDING-M5-CORE-SAU-CRM03.md` SHA256 `7de60be44fe301d043a70aa2b582572f5d96d40f9444238f10a2a50acd4bcc5c`; `TAI-SU-DUNG-PHAN-MEM-KHO-10.md` SHA256 `92dfe44947baad6cc2d0f34bb27c2a8d5f21949cf33ffc9bd91a8dbe9c1621c4`. Đây là phần triển khai đầu của toàn M5, không thu hẹp đích cuối về parser.

## 1. Hiện trạng thực tế để tái sử dụng

| File/function hiện có trong repo | Reuse cụ thể / giới hạn |
|---|---|
| `nguon/review_xay_dung.py:38 doc_json_chinh_xac`, `:48 chuan_hoa_so` | Đọc JSON UTF-8/BOM, khóa lặp/NaN bị chặn, Decimal không qua binary float; serialize exact representation cho audit. Parse exact JSON không phục hồi precision đã mất ở Number nguồn |
| `ha_tang/primitives.py:17 DataError`, `:24 canonical_json`, `:28 sha256`, `:41 text_id`, `:55 date_iso`, `:112 natural_key` | Lỗi/locator, canonical digest, namespace/native key và kiểm ngày. Không dùng `money_minor` cho quantity; không dùng thời điểm nhận thay ngày nghiệp vụ |
| `nguon/fixture.py:26 Issue`, `:34 Record`, `:46 Batch`, `:61 Adapter` | Reuse Issue/kiểu lỗi. Record hiện buộc business_date; không ép candidate thiếu ngày vào Record bằng ngày giả hoặc chọn ngày từ SoPhieu |
| `nguon/trich_hop_dong_6.py:52 envelope`, `:70 TrichHopDong6Adapter` | Tham khảo cách tách raw bytes khỏi context/provenance và reader khỏi repository; không sửa #6, không copy nguyên business logic/manifest ngày của #6 cho kho |
| `giao_dien/intake.py:40 Intake.receive`, `server.py:633 POST /api/upload`, `:557 GET /api/files/{id}/download` | Đã có raw receipt/download, nhưng SOURCES chưa có kho, bắt entity/kỳ, chưa có source-history/M5 scope; chưa nối gói này vào các endpoint đó |
| `ha_tang/store.py:111 Store.ingest`, `:190 _promote_record` | Có raw staging/hash/evidence; V12 khóa một PN, changed line set/core là conflict, `document_lines.amount_minor` bắt buộc. Không tạo amount0/đổi kind để nhét quantity/history vào Store |
| `ha_tang/pg_migrations.py:207 kho.chung_tu`, `:238 kho.chung_tu_dong`, `:550 kho.lien_ket_chung_tu` | Đã có kind PHIEU_KHO, field so_luong numeric, loai HD_PHIEU_KHO; chưa có native/logical/PB-line/observation/proof/dual-budget graph theo M5. Enum có sẵn không đồng nghĩa module đã triển khai |

Tìm tĩnh `src/`+`tests/` chưa thấy `nguon/kho_10.py`, `KhoSoLuongK2`, `/api/m5`, `hoa_don_dong_danh_tinh/hoa_don_dong_phien_ban`, `dich_so_luong/ma_hoa_luong_nguon` hoặc quantity child chung. Common core hiện có thay đổi M9 chưa nghiệm thu; gói thuần không import/chạy `k2`, Store, server hoặc migrations.

Hash pin tối thiểu khi giao coder: primitives `c7e74dc76ca331f9212a5d6e7bfb4a2d202bfaab821efee0f9bf3495c7056975`; R_REV `a2c0577609e6b73f06931f20a9873c9212b9b96c1f545cee990d0dd7813debe4`; fixture DTO `5c3250978026e706ffcd86f9c2f9d47075f968654b532dc59aa55f0f8294d463`. Root đọc/rebase hash thực trước giao; không sửa các file reuse để phục vụ gói này.

## 2. Phạm vi được đề nghị cho lần code đầu

**Chỉ tạo** `src/kho_tri_thuc/nguon/kho_10.py`, `tests/test_kho_10.py`, và các JSON DEMO được root kiểm duyệt trong `tests/fixtures/kho_10/`. Các tên interface bên dưới là **đề nghị mới**, chưa tồn tại; không phải API đang chạy.

Interface thuần đề nghị: `doc_phieu_kho(content: bytes, context: KhoReadContext) -> KhoReadResult`; context do caller/server tin cậy cấp, raw chỉ là object `{phieu, lines}`. Result là candidate/read model chưa promote: source identity, raw/content hashes, header/ngày nullable, native lines/locator, master/profile refs, quantity raw/text/encoding state, scope/coverage và Issue[]. Không tạo DB/file, không tự cấp approval/PROVEN, không mutable cache/global history.

Đầu vào source đã có: header `SoPhieu,LoaiPhieu,NgayChungTu,MaKho,MaDoiTac,DienGiai,TrangThai,NguoiLap,NguoiDuyet,ThoiDiemDuyet,SoPhieu_Goc`; line `ID_Dong,SoPhieu,MaHang,SoLuong,GhiChu`; master whitelist `MaHang,DVT_Goc,DVT_QuyDoi` và kho/đối tác liên quan. Context giữ instance/scope/coverage, mapping instance+kho→PN có version, master snapshot và measurement evidence. Không thêm PN/UOM tự khai vào native line.

Nguồn actual #10 vẫn giữ CRUD/duyệt/đảo/tính tồn/kiểm kê/UI/Google storage. Không gửi original Apps Script/HTML, `.clasp.json`, Google data/token hoặc workbook thật tới Claude. Coder chỉ đọc source nội bộ đã được phép và diễn giải field/interface trong tài liệu đã lọc.

Reader phải giữ rõ bốn loại khóa: native header/line; logical source identity từ instance+native key; content digest không chứa fetch/fixture_id; observation/capture context ngoài content. Không tạo source revision từ mỗi lần fetch. Tách đủ thông tin cho repository sau này xử lý A→B→A; không reader tự thay accepted pointer hoặc tự đánh dấu hủy link.

Missing date/PN/UOM/precision giữ candidate+issue, không fake0/now/default1/đoán từ tên. Chặn duplicate JSON key/native line ID, orphan SoPhieu và invalid shape; không last-wins/sort-STT làm identity. Partial không chứng minh xóa. Status đảo/source-state ambiguity phải hiện ineligible/needs review trong read result, không sinh phiếu âm.

Quantity giữ Decimal/text và native representation; không Number/float/parseInt/abs/round. Kiểm miền/scale38,12 khi có exact-text proof; không đưa số vượt miền vào normalized output. `DVT_QuyDoi=12` không là conversion proof. `JSON Number`/fraction/boundary chưa chứng minh source precision giữ UNPROVEN kể cả Decimal parser đọc token đúng. Context DEMO exact-text dùng cho positive phải ghi explicit synthetic; không trở thành chứng minh cho current producer.

**Bắt buộc có hàm phân loại thuần riêng** `phan_loai_quan_sat(candidate, summary: KhoHistorySummary | None)` trong cùng reader file để tiêu chí extraction-classification10case có đầu vào kiểm được. Hàm chỉ trả reason/needs-review/known-or-unknown, không side effect/auto approve/reserve/free hoặc cập nhật accepted pointer. Không tạo máy trạng thái/storage riêng cạnh common core. Thiếu summary thì extraction vẫn giữ candidate, classification là `HISTORY_UNAVAILABLE`/PENDING; không đoán lịch sử từ raw status hay fixture metadata.

`KhoHistorySummary` là immutable trusted context do repository có quyền resolve (DEMO do root seed/pin), không nhận từ native JSON/browser. Contract tối thiểu: exact logical `(source_instance,SoPhieu)` và scope/profile refs; tập receipt đã thấy `(receipt_id,request_digest,content_digest)`; tập content digests đã thấy; accepted source `(content_digest,observation_ref,source_state)` nếu có; continuity/old line-unit-basis refs cùng proof ref nếu có. Summary empty phải tường minh và có đúng logical identity, khác summary missing. Identity/scope mismatch trả issue/UNKNOWN, không lấy summary của nguồn khác; giữ bất biến input summary, không đánh dấu trusted bằng boolean từ raw. Test context không cấp quyền production.

Phân biệt: cùng receipt+request/content digest đã thấy → `REPLAY`; receipt mới cùng accepted content → fresh observation/same-content, không replay; acceptedB đảo+seenA,B rồi A xuất hiện lại → `REAPPEARANCE_HOLD`, không eligible/reopen hoặc thêm phiếu âm; current đảo → `REVERSED`; partial/continuity thiếu giữ reason riêng. Classifier không suy accepted/approved từ chỉ chuỗi `Đã duyệt`. `fixture_id`, `order`, `after_fixture` và expected/oracle không được đưa vào classifier; K01/K03/K05 có native payload/master giống nhau nên chỉ history summary hợp lệ mới phân biệt được chúng. K09 old unit/basis dùng refs explicit, không tự nhân12.

**Màn hình/schema:** không thêm màn hình, HTTP route hay migration trong gói đầu. Shell M5/POST `/api/m5/nhan`/history/mapping/preview/V2/file trong binding vẫn thuộc scope tiếp theo khi common contract được root review; upload/raw inbox đang có không được đổi tên thành M5 đã vận hành. Output reader phải đủ hiển thị các field đó sau này, không cột valuation/giá vốn/stock journals.

## 3. Corpus và điều gì kiểm được ngay

Root kiểm và sao chép corpus synthetic đã chuẩn bị từ `var/codex-dieu-phoi/m5-source-inputs-20261019` vào whitelist tests trước khi giao; không cấp coder đọc var. Manifest hiện pin `0dce3a08bedfa96b31bdc75859e03caaaec97972b29d239ad247ef5d1d73a29a`, oracle `8e260e2c2dd979c87b8f614ef084dd0e83d8c336aba5fcc4590602daff26aabb`; root phải xác minh latest manifest nếu corpus được sửa. Oracle không đưa vào parser như dữ liệu nguồn.

**Bridge corpus trước dispatch:** mười JSON hiện là outer wrapper `{fixture_id,format,fixture_context,source_detail,source_master}`, không phải native bytes nhận nguyên. Root tạo/pin riêng mười native-only fixture bytes dưới `tests/fixtures/kho_10/` từ đúng lexical JSON subtree `/source_detail` bằng lossless span extraction sau kiểm strict outer JSON (không serialize Decimal qua `chuan_hoa_so`, không đổi Number/text). Giữ wrapper/oracle gốc nguyên hash, ghi manifest riêng outer SHA→native SHA/token-kind checks/context/history-summary refs; byte capture native này là DEMO synthetic, không export thực của #10. Coder chỉ đọc fixtures đã root chuẩn bị, không tự chuẩn hóa input/expected hoặc đọc var.

`source_master` và whitelist `fixture_context` đi vào typed trusted context riêng; `fixture_id/format/order/after_fixture` chỉ dùng bên test observer, không parser/classifier. History summary được root lập độc lập theo preconditions K01/K03/K05/K09, pin exact identity/receipt/content hashes/accepted state/old basis refs trước run; không lấy output implementation làm expected. Production phải resolve từ common repository có quyền sau này, không dùng fixture receipt như bằng chứng nguồn thật.

Raw SHA trong result phải bằng SHA **chính native bytes truyền vào reader**, khác SHA outer-wrapper; semantic digest tách receipt/fetch/fixture ID. Giữ native bytes/raw SHA trước/sau; K08 vẫn NULL/int0/numeric2.5/numeric9007199254740992 với native token kinds tương ứng, không audit-tag object/string hóa Number hoặc sửa intended integer. Có controls native wrapper input bị từ chối, receipt/fixture metadata không đổi semantic digest, business/status đổi có đổi; duplicate key/NaN/BOM dùng native bytes trực tiếp, không preprocessor làm mất lỗi. Native BOM hợp lệ được đọc theo reuse parser, không coi BOM là business change.

| Case | Có thể kiểm ở reader thuần | Bằng chứng vẫn phải có ở gói core sau |
|---|---|---|
| K01 | Đã duyệt/date/2 native lines, quantity8CAI exact theo **proof DEMO explicit**, raw/hash/PN mapping đúng | L11 invoice10↔source8, remaining2/0, common child/receipt và0 delta invoice/claim/331/BANK; chưa gọi là PASS K01 đầy đủ |
| K02 | Cùng native keys ở instance A/B cho logical keys/PN mapping khác; context mismatch phải giữ issue | Actual API/SQL cross-PN reject cùng positive control PNB |
| K03 | Same payload/source digest/key, same receipt context nhận diện replay; fresh capture tách content | Actual receipt replay0observation/row/consumption delta, fresh fetch history |
| K04–K05 | Cùng key đảo; raw A cũ sau B được phân loại hold, không source negative document | DB acceptedB/eligibleNULL/1logical2content, old links6 held+IDs nguyên và period/action guards |
| K06–K07 | Duplicate ID conflict; partial/missing row không đánh dấu deleted/cancel | Atomic promotion/current pointers/old reservation không free ở DB |
| K08 | NULL≠0;0không positive capacity;2.5không truncate;Number boundary UNPROVEN không sửa intended integer | Source encoding proof+exact measurement/budget/capacity guards thực |
| K09–K10 | Master UOM đổi/factor12 không đủ evidence, unknown UOM không default; giữ old basis refs trong result | Old link proof/quantity/budget nguyên, no new pool/free; approved conversion/continuity workflow |

K01 L11 branch dùng8; K04/K05 là nhánh riêng với precondition link6. Không ghi test xanh bằng cách giả lập DB rồi so chính constants của implementation. Unit tests cần raw input+expected độc lập, counterexample thực (key lặp/orphan/invalid date/unknown proof), kiểm raw bất biến, quantity representation và reason codes; không yêu cầu core acceptance cho gói thuần.

## 4. Dependency còn thiếu và điều kiện bàn giao

Để hoàn tất positive/negative runtime toàn M5 vẫn cần: source instance/profile/read-only deployment xác minh; common M0 tiếp nhận trước PN + snapshot scope/observation/review/history; typed M5 header/logical-line/PB; M2 invoice identity/PB-line bridge; exact encoding/conversion proof và hai normalized cross-revision pools/child non-money; actor/PN/action/RLS/locks/common receipt/period; UI/file/restart và producer tồn/kiểm kê gaps. Không dùng generic numeric/STT hoặc JSON core để bỏ những dependency này.

Dependency đó được triển khai dưới gói common/M2/M5 được root review sau, **không yêu cầu sửa M9 đã dừng**. Reader thuần không import/chạm M9; source vay mới của Anh không là đầu vào của gói này. Chưa có cơ sở giao cả M5 CRUD/Google/K2 chỉ với hai file nhỏ.

Khi root phát lệnh riêng mới bắt đầu coder: whitelist chỉ ba vị trí tạo mới nêu trên; đọc primitives/R_REV/DTO và tài liệu, không sửa product/public ledgers/source app/M9/launchers/config/DB. Coder chạy tests riêng reader bằng system Python trong môi trường guard root cấp; không suite PostgreSQL/Store/HTTP/UI/Google. Hiện chưa có lệnh chạy nào được thực hiện cho gói này.

Bàn giao gói: diff chỉ whitelist, strict parsing/10case extraction-classification có kết quả độc lập, raw/hash/provenance giữ đúng, không import I/O path, không xóa file; root freeze/hash và review riêng trước nối ứng dụng. Thiếu root-pinned native fixtures/history summaries/bridge là dependency trước dispatch, không tự coi mười outer JSON đã sẵn sàng làm input reader. Nhãn đạt nếu đủ chỉ là **M5_READER_PURE_VERIFIED**, còn toàn module M5/L11/runtime/production **PENDING**. Tiếp tục phần core/UI/deployment đúng scope đầy đủ sau khi các hợp đồng tương ứng đủ điều kiện.

Amend technical R1/R2 theo `REVIEW-M5-READER-HANDOFF-01.md` SHA `d0c580f943f222d19aee88f74b7f6d2f3c71b5a15fb49f5a01fd37c4226a7485`; vẫn PREPARE_ONLY/NOT_DISPATCHED/NOT_RUN. Không thêm storage/engine/route/schema hoặc thay scope toàn M5; root chuẩn bị fixture bridge riêng và review pins trước lần giao sau.
