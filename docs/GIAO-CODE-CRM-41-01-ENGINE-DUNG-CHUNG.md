> **21/10/2026 · Engine chung F11 — kiểm độc lập mới nhất.** Một engine #6 thật, một client/projection cho M4 và CRM; mỗi lần trích có loại hợp đồng, danh mục/phiên bản và mã tham số riêng. Source native **24/24 PASS, 0 skip**; central client/projection/wiring **28/28 PASS, 0 skip**; kiểm literal DOCX thật đạt ALL37, hai tập con đồng thời, 7 loại từ chối/replay/conflict; shared-client API thật **1 PASS**.
>
> **Hai consumer M4/CRM đã qua 8 kiểm thực tế HTTP → PostgreSQL trên DEMO**: quyền/pháp nhân, revision, nhận kết quả và raw, replay, đổi envelope, mất phản hồi rồi đối soát. DB/catalog/sequences và file cũ giữ nguyên trong các ca replay; các file staging mới được đối soát riêng (5/0/5 trong bounds 6/1/6), không gọi toàn bộ filesystem bằng 0. Source đã áp F11 có backup; các server kiểm đã dừng sạch. Đây là bằng chứng hữu hạn, chưa phải accuracy toàn danh mục hoặc toàn module.
>
> **Đang chuẩn bị giao Claude nối nút DEMO với owned engine**, sau đó kiểm giao diện. Còn hai sửa nhỏ về retry khi thiếu URL và định dạng reservation request_id, đi cùng gói launcher. KCN/nhà ở và E3/E5 vẫn thuộc CRM; XD37 là mốc trung gian. CRM → M2-00 → E1-MUA giữ tuần tự; M9 giữ dừng, không xóa file. Các mốc cũ bên dưới là lịch sử.

> **Trạng thái hiện hành 21/10/2026:** Đã dispatch và viết code; dòng PREPARED_NOT_DISPATCHED bên dưới là trạng thái ban đầu của handoff. Root đã kiểm source API bản trước lượt sửa mới: 18 native PASS/0skip và HTTP literal 3 lượt/7 loại từ chối/replay/conflict đạt. FIX04 mới terminal, client/adapter 24 ca có 1 lỗi concurrency đường dẫn Windows; còn review/recovery repairs và chưa chạy central PG/GUI bản mới. Chưa nghiệm thu gói hay toàn M4/CRM/M2. Root điều phối source patch có backup; Claude chỉ sửa staged kỹ thuật.

# CRM-41-01 — Một engine #6 dùng chung, chuyển đường gọi M4/CRM

**21/10/2026 · PREPARED_NOT_DISPATCHED · CODE_ONLY sau Root review/release.** Kiến trúc đã được Anh chốt; tài liệu này chưa cấp quyền ghi source ngoài workspace, chưa phải code/test/GUI hoặc toàn CRM đã đạt.

## 1. Mục tiêu, quyền sở hữu và giới hạn

- Gói CRM-41-01 sở hữu common API và chuyển consumer; theo [quyết định chung](QUYET-DINH-ENGINE-TRICH-THAM-SO-DUNG-CHUNG.md) SHA `54be96e958c8fe9e00c93788c2d3becd6bf8522a832ab2415b63e17e811dfadb` và [hàng chờ CRM](HANG-CHO-CRM-41-42.md), không tạo engine M4/CRM/M2 riêng.
- Lõi duy nhất tiếp tục ở `D:\Claude\Ho tro review ho so xay dung\review_xaydung\trich_xuat`; central app gọi API, không import/copy lõi sang từng module. Giữ mọi bản tham chiếu/vendor/lịch sử hiện có.
- Kết quả hữu hạn: trích thật qua source #6 → một adapter output chung → M4/CRM nhận kết quả đúng nguồn, version và quyền; dùng được trên UI hiện có. Không dựng app, master, approval hoặc framework thứ hai.
- CRM-41-03 là Báo giá/Soạn/DOCX/PDF renderer, không phải extractor. Không đưa renderer, BOQ/Review L1–L3, full E1 bảng typed hoặc đo accuracy loại mới vào gói này.

## 2. Đường gọi đã kiểm tĩnh — phải thay đúng seam

- Source `may_chu/server.py:237–264`: tạo lượt/upload/chạy; `dich_vu.py:376–429` gọi `load_params`, lọc `tham_so`, dựng `LuotChay`. Hiện `if chon` làm `[]` thành tất cả và bỏ mã lạ; `_tuy_chon` chỉ giữ count/config, chưa là snapshot contract.
- Source `trich_xuat/lo.py:36–49,186–190` truyền params vào `TrichXuat`; `quy_trinh.py:91–103,462–482` trả/lưu `bang[]`. `chi_cau_truc` hiện chỉ fallback sau thử kết nối AI, chưa bảo đảm offline.
- Central `k2/xay_dung.py:356–374` → `m4/nguon_review.py:314–345`: gọi copied `TrichXuat.xu_ly` khi có AI hoặc copied `master_hd.trich_xuat` khi rule-only. Chuyển đường TRÍCH đang hoạt động này sang common client; không tự chuyển chức năng Review khác.
- CRM `giao_dien/server.py:433` → `k2/crm.py:112–150` hiện nhận JSON kết quả; `nguon/trich_hop_dong_6.py:30–42` bắt buộc `tham_so[]`, không chạy #6. Không coi `bang[]` nguồn đã tương thích sẵn.
- Coder phải inventory mọi callsite `TrichXuat`, `master_hd.trich_xuat`, `load_params` và `NR.trich_hop_dong`, phân loại runtime/test/reference; sau chuyển không còn đường active parameter extraction chạy copied core hoặc fallback sang nó.

## 3. Common request và snapshot nghiêm ngặt

- Mở rộng từ API nguồn thật `POST /api/trich_xuat/{luot}/chay`; tên DTO/version route cuối phải bind theo code thật trước dispatch, không coi field còn thiếu đã có.
- Request common gắn raw document hash/version, loại hợp đồng, catalog identity/version/hash và tập mã yêu cầu; máy chủ chọn catalog từ registry/config đã ghim, không nhận filesystem path hoặc rule code từ browser.
- New common contract: thiếu loại/catalog/version → lỗi rõ; thiếu tập mã và `[]` → hai lỗi rõ; chọn tất cả phải tường minh rồi snapshot thành tập mã không rỗng; mã lạ/trùng/sai kiểu → lỗi, không bỏ qua hoặc fallback XD.
- Chỉ dùng loại/catalog thực có và được bind. Loại chưa có như KCN/nhà ở khi chưa cung cấp catalog phù hợp phải báo unsupported/missing catalog, không bịa policy tài chính hoặc mượn XD âm thầm.
- Giữ legacy API/JSON tương thích qua nhánh/version cũ được phân biệt rõ; hành vi cũ chọn XD/tất cả không áp dụng cho new common caller. UI có thể preselect XD; M4 gửi XD, catalog/version và mã yêu cầu tường minh.
- Mỗi lượt chụp nội dung/thuộc tính catalog, rules, requested codes và implementation version trước compute; params không trỏ vào cấu hình mutable dùng chung. Sửa catalog hoặc chạy profile khác không đổi snapshot lượt đang chạy.
- Output/receipt giữ request/source hashes, engine implementation/version, catalog/rules hash, tập mã đã dùng và provenance. Tham số không yêu cầu khác CHUA_CO/không áp dụng/không quy định; không điền0 thay thiếu.

## 4. Một output adapter và hai consumer thật

- Chỉ một adapter `bang[] → tham_so[]` dùng chung: giữ raw nguồn nguyên bytes/hash, normalized view có adapter version và liên kết về raw; không ghi đè raw hoặc giả hash view là hash output nguồn.
- Giữ source quote/locator/field state; bảng chỉ giữ đúng dữ liệu/nguồn mà engine thật trả. Chưa có E3 row/cell DTO thì khai rõ thiếu, không mỗi module tự viết bộ trích bảng hoặc fabricated typed rows.
- M4 giữ source document/revision, catalog37 đã bind, kiểm trích dẫn, phòng dự án xác nhận và gate Nộp; nguồn/API unavailable báo chưa sẵn sàng, không tự dùng copied extraction để trả thành công.
- CRM thêm actual raw-document extraction trong đường tiếp nhận hiện có, rồi dùng chung adapter và workflow kiểm/duyệt hiện hành; vẫn đọc được legacy JSON. Không lấy `hop_dong` filename làm khóa HĐ/pháp nhân.
- Mọi start/read/result/download/retry kiểm current actor/module/PN/project và exact source revision; giữ raw/run history, original key/body và scope. Current role/tab/form đổi không được nhận kết quả muộn vào hồ sơ khác.
- Common client chỉ create/upload/run/read/stop extraction. Không gọi source `nap_csdl`, xác nhận/duyệt, settings hoặc DELETE; không đưa legacy X-HD auth/iframe/master SQLite thành authority central K2.

## 5. Rule-only DEMO và execution boundary

- Gói kiểm bằng dữ liệu tổng hợp, explicit rule-only DEMO: dùng chính `TrichXuat` nguồn với `ai=None/cloud=None`, không thăm dò AI/network provider rồi mới fallback; không kế thừa source config cloud/Claude/keys.
- Không bật cloud, OCR/Office hoặc gửi dữ liệu thật. `chua_chay_AI`, missing/unsupported không thành đã trích đúng/đã duyệt; accuracy AI và catalog mới là kiểm riêng sau này.
- Root bind owned loopback source endpoint/implementation, retained per-run storage, timeout/stop và no-delete trước runtime; không tự launch app nguồn đang vận hành, quét LAN, đọc real DB/config secrets hoặc cleanup.
- Công việc dài không giữ global mutation lock hoặc giao dịch K2; dùng seam owned compute/current-rights/source-basis recheck đã có, không dựng queue/lifecycle framework khác.

## 6. File proposal tối thiểu — Root chốt exact allowlist trước code

- Ở source #6: `may_chu/dich_vu.py`, `trich_xuat/lo.py`, `trich_xuat/quy_trinh.py`, `trich_xuat/danh_muc.py`; chỉ strict request/catalog snapshot/explicit offline/output metadata. Giữ extraction algorithms; đọc `server.py`/`cau_hinh.py`, chỉ thêm write nếu actual API binding thật cần.
- Ở central: đề xuất một file mới `src/kho_tri_thuc/nguon/trich_chung_6.py` cho client+normalization; sửa `nguon/trich_hop_dong_6.py`, `k2/xay_dung.py`, `k2/crm.py`, `giao_dien/server.py` trong cùng package để không còn consumer chạy sai core.
- UI tái dùng `giao_dien/assets/app.js` đúng vùng CRM và `m4/giao_dien/m4.js` đúng hành động Trích; không sửa M9 block, không tạo menu rỗng. Root bind thêm path/hunk thực sự cần thay vì mở wildcard UI.
- Root bind exact source/central test paths, nonempty DEMO inputs và report `docs/BAO-CAO-CRM-41-01.md`; không truyền oracle riêng cho coder, không đổi expected từ output sản phẩm.
- Source nằm ngoài writable roots của lượt hiện tại: phải bind quyền ghi/exact technical paths và baseline cả hai dự án trước actual dispatch. Handoff này không sửa source app hoặc thay settings/controller.
- Bảo toàn migrations1–20 đã sealed. Không cần schema thì không thêm migration; nếu thật sự cần K2 metadata, chỉ append21 sau Root bind actual prefix/registry, không invent DDL trong preparation hoặc rewrite migration cũ.

## 7. Kiểm độc lập và điểm kết thúc hữu hạn

1. Legacy request/JSON và XD regression giữ hành vi đã công bố; new common thiếu/[]/all/unknown/type/version sai có đúng lỗi, không compute lặng hoặc output rỗng tính PASS.
2. Hai profile/tập mã hợp lệ hiện có chạy đồng thời trên input DEMO không rỗng: mỗi lượt đúng catalog/rules/request snapshot, không lẫn params; đổi catalog sau start không đổi lượt cũ. Không cần bịa thêm loại mới để tạo positive.
3. M4 và CRM thực sự chạy cùng implementation/version ở source: kiểm actual origin/request/run/source hashes; xác nhận copied `TrichXuat.xu_ly` và `master_hd.trich_xuat` có0 lời gọi extraction qua common path. Vendor vẫn dùng được cho Review khác, không xóa file.
4. Kiểm raw/normalized mapping, quote/state/missing/version, exact retry và revision cũ; mất quyền/đổi role/context/source giữa chừng không leak hoặc publish sai hồ sơ; API/provider lỗi không gọi fallback copied core.
5. Actual UI từng consumer: upload/chọn catalog+tập mã → chạy rule-only → xem nguồn/kết quả → tiếp tục đúng bước soát của module; read/download/replay kiểm quyền. Không dùng placeholder UI hay result fixture làm positive.
6. Không merge quyền xác nhận: M4 phòng dự án xác nhận, Anh/sếp duyệt hồ sơ; CRM giữ A/B và CFO/KT theo41–42; kế toán NT/AP độc lập. Engine đạt không đồng nghĩa cả module đạt.
7. M2 hiện chưa có callsite #6 trong đường đã kiểm: không thêm noop để claim3consumer. M2-00 dùng #7 riêng; thứ tự giữ CRM → M2-00 → E1-MUA, gói sau mở catalog/rules/tables ngay trong cùng #6 và dùng client chung khi nghiệp vụ M2 thực sự được nối.

Coder chỉ viết trong allowlist đã bind, không tự import/AST/run/tests/SQL/network/browser/Office/launcher hoặc đọc secrets/realdata; giữ mọi file và lịch sử. Root review/freeze rồi mới cấp runtime từng bước; PREPARED_NOT_DISPATCHED và full CRM/M4/M2 acceptance vẫn chưa đạt.
