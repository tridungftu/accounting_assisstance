# M4-01C — Cổng hồ sơ và giao diện gói 1

**Handoff triển khai CODE_ONLY — 20/10/2026.** Root đã review đầy đủ C04 và khép các bộ kiểm backend hữu hạn; chưa có code/GUI C được nghiệm thu. Giữ nguyên các bản private làm lịch sử.
Claude tiếp tục cùng session hiện hành, đúng 11 tệp ở mục6. Root quản lý lượt ghi owned1800s và kiểm sau khi coder dừng; không tự mở task, schema hoặc phạm vi khác.

## 1. Căn cứ hiện hành và điều kiện giao

| Căn cứ | Pin / giới hạn |
|---|---|
| [Kế hoạch M4 đã chốt](M4-KE-HOACH-DA-CHOT-20261020.md) | `679e8453ee5922c7cc356129c9abf9d24b4cd5f9c5d4c0176c3dcadb05e2d312` |
| [Handoff M4-01](GIAO-CODE-M4-01-CONG-HO-SO-VA-TAI-SU-DUNG.md) | `524f9e2d3d64ae5ce4bb61e9fee19db0df6ee4c450a31d88bb9b73a842b93c39` |
| [B hiện hành](GIAO-CODE-M4-01B-SUA-GATE-VA-BO-SUNG-KIEM.md) / [B2](GIAO-CODE-M4-01B2-KHEP-SUA-VA-KIEM.md) / [B3](GIAO-CODE-M4-01B3-SUA-BO-KIEM-PG.md) | `c9744c547f5f927c5319ff1381d3f463619755a3d70f87b76b28eae7f98519a7` / `9cc77a4e8f7b30d703a4af38054a8a8da84be3b04222ce2e2182f332d97e7407` / `fc54781bd6b211730630674e1e3215b61ebaacb6d235e494da3a79b6060e67b5` |
| [Actual B6 source347](../var/codex-dieu-phoi/m4b6-runtime-frozen-bff15e917043/source-manifest.json) | `72b6e08b25da8ab93b1072a4211a3b11d1c9e39d0c2cf1b854774e1538de3a7c`; actual frozen input; native10/10 đã PASS, chưa C/GUI acceptance |
| [Actual B6 terminal/freeze413](../var/codex-dieu-phoi/m4b6-runtime-frozen-bff15e917043/root-terminal-freeze.json) / manifest | receipt `f38050984157fa8282326d34ba9ccbe3d6de97745b258fba87063ca56e4d9e77`; runtime manifest `3c46b5b6ec1831f36b736da3e5567fab7cde3a1728082e422668dbae0f380c2c` =347source+65reference+reference manifest |
| [Vendor56 stage receipt](../var/codex-dieu-phoi/m4b3-vendor-stage-d6209c416326/receipt.json) / [reference65](M4-REVIEW-REFERENCE-20261020/manifest.json) | `86f51b1b39cf04a49579b190c77d1e1bd10731d30c493d4bf93a3625640aaaae` / `c212166ba6f69d137f4c24958f877a86cb4f2ac9f5a4c19e6e2bc582669549cb`; tool missing-check1/copy0/complete-check0 là stage byteexact, không product-test |

B6 actual73103/69f046 exit0; chỉ PG helper/report đổi, product/pure/API giữ nguyên. Root/peer đã review và kiểm thực tế: pure50/50 (0 skip) + independent4 PASS; independentPG8 actual25631/4a9ebf PASS; nativePG10/10 (0 skip) actual45412/8977eb PASS, gồm replay và đồng thời. Bằng chứng pure/independent được kế thừa bằng đối chiếu411/413 tệp không đổi, hai tệp còn lại chỉ helperPG/report. Root đã xác nhận child dừng và live/frozen posthash. Đây là closure hữu hạn để triển khai C, không phải C/GUI/fullM4 acceptance. Self-test lượt Claude vẫn NOT_RUN; C phải được Root kiểm HTTP/GUI/18 ca sau khi bàn giao.
Claude là coder duy nhất, cùng UUID `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`, CODE_ONLY/file tools theo Root; không tự chạy tool/vendor/AI/Office/SQL/GUI. Mọi lượt writer trước phải terminal; Root chạy kiểm sau freeze, original no-delete guard giữ nguyên.

## 2. Kết quả C và full reuse không thu hẹp

Khép luồng thật: bấm mở DEMO → #m4 → vai/dự án → HĐ/đợt nháp → tải hoặc dùng lại nguồn → trích/soát/xác nhận tham số → khai PL/BOQ → ngày/checklist → thiếu cụ thể → Nộp → reviewer đọc đợt đã nộp/tải nguồn được phép. Có API/nút hoạt động và ca kiểm; không phải menu, badge hay placeholder.
Phòng dự án xác nhận tham số M4, **không CFO/CRM approval**. C không làm Duyệt Review, PDF ký, ghi NT/AP, tạo Request, giả dữ liệu đã duyệt hoặc thay nghĩa tiền. Các nhánh ấy vẫn trong full plan, chuyển đúng gói sau.
Giữ roadmap toàn source Review: Tổng quan; trích/soát; danh mục HĐ/PL/BOQ; L1 K1–K8; L2 B1–B8; L3 C01–C09; ghép hạng mục/chạy lại; nguồn/trích dẫn/lịch sử; OCR; báo cáo/tác vụ/cài đặt. Chưa nối thì ghi rõ gói/CHUA_NOI, không gắn nút giả hoặc gọi full M4 xong. CAD và tài khoản nhà thầu ngoài tiếp tục deferred.
Dùng shell hiện có, không mở app nguồn/Streamlit/iframe, X-HD hoặc SQLite master khác. Giữ look Bàn kiểm soát, Be Vietnam Pro/OFL local byteexact, namespace `.m4`, navy `#19334d`/nền `#f4f6f9`/ink `#24364a`/border `#dfe5ec`/amber `#895a14`; bảng/căn cứ/checklist ưu tiên đọc, không style leak.

## 3. Đường gọi actual B6 — không bịa API

Đã FULL `giao_dien/m4.py:1–202` SHA `baf246d4226edc8e95567bf50af3a32e78a972c46e8cfb23498a9240e696e3c0`; `k2/xay_dung.py:1–567` SHA `047874da76bbfc26cf1a7b862fbf66ccd438b79b05f5493162c894d4242bcae2` trong source347. Đây là contract UI của C, không xác nhận runtime.

| Actual HTTP | Input/response phải dùng |
|---|---|
| `GET /api/m4` | `{cau_hinh,nguoi,pham_vi,hop_dong,dot,danh_muc_ho_so,nhanh_sau,tai_len_toi_da_byte,danh_tinh_demo,ghi_nguon:{san_sang,ly_do}}`; khi chưa cấu hình có `{cau_hinh:false,ly_do}`; không tự tạo danh sách quyền. |
| `GET /api/m4/hop-dong/{uuid}` | `{ho_so,tep,trich_xuat,tham_so,xac_nhan,phu_luc,boq,boq_goc_dong,dot,danh_muc_sha256,nhanh_sau}`; `ho_so.revision/rev_tham_so/soan`, `xac_nhan.con_hieu_luc`, `dot[].can_cu_doi_sau_nop` là server facts. |
| `GET /api/m4/dot/{uuid}` | `{dot,tep,checklist,thieu,du_can_cu,nop,hieu_luc,can_cu_doi_sau_nop,nhanh_sau}`; `thieu[]` có `ma,nhom,noi_dung` và optional `muc/phu_luc_id/boq_id`; không có endpoint preflight riêng. |
| `GET /api/m4/tep/{uuid}` | Nonempty raw bytes, attachment filename; dùng same-origin token/cookie, không direct navigation thiếu token. File scope theo actual RLS, không tự owner-only. |
| `POST /api/m4/tep` | Body là bytes File, header `X-M4-Info=encodeURIComponent(JSON.stringify({du_an_id,vai_tro,ten,media_type,khoa}))`, metadata header≤4000, size từ GET. Vai tài liệu HOP_DONG/PHU_LUC/BOQ/HO_SO_DOT theo backend; response có `tep_id,sha256,byte_length,hang_moi,lap_lai`, hồ sơ đợt có thể có `goi_y_muc`. Hash response chỉ hiển thị. |
| `POST /api/m4/danh-tinh` | `{dang_nhap}` từ danh sách M4 DEMO, response `{dang_nhap}`; thay **cùng** cookie session CRM/M2/M5/L11, không actor tự nhập. |
| `POST /api/m4/hop-dong/{tao,gan-tep,trich}` | Tạo `{du_an_id,so_hop_dong,ten,khoa}`; gắn `{hop_dong_id,revision,tep_id,khoa}`; trích `{hop_dong_id,revision,khoa}`. |
| `POST /api/m4/tham-so/{sua,xac-nhan}` | Sửa `{hop_dong_id,revision,ma,trang_thai_tham_so,gia_tri?,don_vi?,dieu_khoan?,trich_dan?,ly_do?,khoa}`; xác nhận `{hop_dong_id,revision,ly_do?,khoa}`. Trạng thái sửa CO_GIA_TRI/KHONG_AP_DUNG/KHONG_QUY_DINH; UI không gửi `kiem_tra`. |
| `POST /api/m4/phu-luc/{khai,them,huy}` | Khai `{hop_dong_id,revision,khai,khoa}` với KHONG_CO/CO_CHUA_DU/CO_DU; thêm `{hop_dong_id,revision,so_pl,ngay_ky,ngay_hieu_luc,trang_thai_phu_luc,doi_boq,noi_dung?,tep_id?,khoa}`, DA_KY/DU_THAO và bool thật; hủy `{phu_luc_id,revision,ly_do,khoa}`. CHUA_KHAI là server state, không option giả KHONG_CO. |
| `POST /api/m4/boq/{xem,nhap}` | Xem `{tep_id,sheet?}`: không sheet→`{sheets:[{ten,so_dong,so_cot,an}],goi_y}`, có sheet→`{sheet,dong,so_cot,hang_tieu_de,cot,truong}`; gợi ý không tự commit. Nhập `{hop_dong_id,revision,tep_id,phu_luc_id?,sheet,hang_tieu_de,cot,khoa}`, cot map mã trường→chữ cột, header integer. FINAL fresh/replay giữ `loi_chan/phat_hien`, không tự tính lại. |
| `POST /api/m4/dot/{tao,sua,gan-tep,nop}` | Tạo `{hop_dong_id,so_dot,ngay_nghiem_thu?,khoa}`; sửa `{dot_id,revision,ngay_nghiem_thu,khoa}`; gắn `{dot_id,revision,tep_id,muc,khoa}`; Nộp `{dot_id,revision_ho_so,revision_dot,khoa}`. Lấy cả hai revision từ GET hiện hành, không gán bằng nhau. |

Mutation response của service là kết quả lệnh đã flatten +`lap_lai`, **không** mặc định `ket_qua` envelope. Sau response cập nhật qua GET có fence; giữ request gốc để retry không chạy lại parse. Bộ tham số hiển thị cột server `ma,nhom,ten,trang_thai,gia_tri,gia_tri_may,don_vi,dieu_khoan,trich_dan,kiem_tra,ly_do,vi_tri,nguon`; đủ37/TC09 theo thứ tự server, không sinh từ legacy36.
Lỗi có `{error,message}`:403 current scope/authority,404 không thấy hoặc ngoài scope,409 revision/idempotency/thiếu căn cứ,413 quá lớn,503 source pin/trusted writer/config unavailable; còn lại400 và LOCAL_STORAGE_ERROR500. Hiện message hữu ích, giữ nháp/key; không đổi key/revision tự vượt. Không nối thêm authority chỉ để biến 400 thành success.

## 4. Màn hình nghiệp vụ cần hoàn chỉnh

| Vùng | Thao tác thật và trạng thái |
|---|---|
| Cổng/Tổng quan | Vai/PN/dự án server cho phép; lọc HĐ/đợt, tạo nháp/mở lại/làm mới, empty/permission/unavailable; không hiện project ngoài scope. |
| Nguồn HĐ | Dùng HĐ cũ hoặc tạo identity một lần, upload/gắn nguồn, xem tên/loại/bytes/hash rút gọn/người/ngày; server detail `tep` là pool tệp dự án không tự coi đều thuộc HĐ. Chỉ gắn/ref hiện hành và lịch sử trích đúng HĐ. |
| Tham số | Chạy trích thật, so máy/thủ công/quote/locator/check, sửa có căn cứ, lọc thiếu, phòng dự án xác nhận, hiển thị hết hiệu lực theo server; không auto-confirm37. |
| PL | Chưa khai/Không có/Có chưa đủ/Có đủ; nguồn/số/ngày/trạng thái/đổi BOQ; hủy lý do; giữ mọi lịch sử, không coi PL dự thảo/tương lai là hiện hành. |
| BOQ | File→sheet/header/map7 trường→preview→nhập gốc/PL; rawcell/blank/0/missing, lỗi blocking và finding số học riêng; giữ supplied999, không tự sửa tiền. `boq_goc_dong` tối đa2000 dòng theo B, không gọi toàn workbook đã hiện đủ. |
| Đợt/checklist | Soạn ngày/bộ hồ sơ đúng mục; `goi_y_muc` chỉ gợi ý; nguồn mục còn thiếu có link tới vùng bổ sung, không chép kỳ trước hoặc auto ngày. |
| Preflight/Nộp | Render `thieu` từ GETdot, đủ điều kiện mới enable và vẫn xử lý server denial; lưu nháp luôn được; stale giữ form và yêu cầu xem lại, success chỉ từ response/GETsnapshot thật. |
| Theo dõi/reviewer | Đợt đã nộp/snapshot/refs/căn cứ đổi sau nộp; action dựa `soan`/backend, không tạo Duyệt/PDF/AP/Request khi `nhanh_sau` còn CHUA_NOI. |

## 5. Shared session, dữ liệu tin cậy và retention

Shell actual `assets/index.html:9/25/192` đã gọi /m4.js,/m4.css và có nav/section; `app.js:5/35–44` chưa có M4 trong router, m4.js chưa tồn tại. `server.py:879–881` đã dispatch /api/m4 và /m4; không cần sửa server hay dựng server mới.
`app.js:678–679/1201–1241` có shared role generation, POST serialization/pending-GET barrier M2/M5/L11. **CRM vẫn** crmAct392–396/crmLoad517–522 độc lập; M4 đổi chung session qua HTTP186–192. C phải đưa M4 **và CRM selector/load/continuations** vào một seam nhỏ có registration API, không chỉ dựng queue M4 riêng; giữ M2/M5/L11 fences và M9 code nguyên trạng.
Mọi intent đổi vai clear cache/selection/raw/quote/DOM/actions của các participant đồng bộ trước await; POST role serialize, GET không gửi khi còn pending-role, chỉ latest intent drain. Fence actor+generation+project/HĐ/đợt/form qua list/detail/preview/mutation/headers/blob/click và success/error; không revive dữ liệu cũ sau chuyển tab/role.
Tệp chỉ download khi same-origin token/cookie và fence còn đúng; late bytes không click; current quyền server vẫn kiểm trước lookup/replay. Không tuyên bố có thể thu hồi bytes đã giao hợp lệ trước đó.
HTTP allowlist actual chỉ nhận IDs/revision/key/map/text/reason/raw; không actor authority/PN/approved/check/facts/parsedrows/rawhash/path/URL/DSN/receipt. Trusted factory HTTP50–68 đã inject ordinary CRM conn + owner writer đã kiểm, `ghi_nguon.san_sang=false` phải dừng ghi và giữ nháp; không fallback SQL thường.
No-AI hiện factory để ai=None, che_do_ai=None; catalog hiện đủ không đồng nghĩa giá trị đã trích. Không bật cloud/downloadmodel/Office, fake AI chỉ kiểm plumbing khai báo; LocalAI/OCR/PDF chưa nối ghi rõ. B2 retained staging không dọn bằng UI/test/helper, retry giữ body/key; không xóa/ghi đè sources/DB/roles/attempts.

## 6. Bootstrap, package và exact target đề xuất

`k2/crm_khoi_dong.py:178–223` đang seed CRM/M5/M2/L11, **chưa M4**. Thêm đúng `m4_demo.khoi_tao(admin)` sau CRM/migrate bằng owner bootstrap sẵn, trả `m4_seed` nguyên trạng/actor diagnostics; không biến THIEU/DA_THU_HOI thành DU. `m4_demo.py:75–119` đã có one-time/revoke-preserving seed, không sửa nó hoặc regrant actor cũ.
`MỞ BẢN DEMO.cmd` gọi start-web.ps1→tools/chuan_bi_crm_demo.py→chuan_bi; giữ launcher/Config/DataRoot/ordinary-role checks. Link/nav #m4 đã có, bấm mở shell rồi M4 là đủ, không bắt Anh chạy CLI/DSN/SQL. Không đổi launcher, schema/migration hoặc config thật để ép DEMO.
pyproject hiện chỉ include assets shell. Thêm package data đúng `kho_tri_thuc.m4` UI m4.js/css và các non-Python source bytes được NR.PIN/tai_san_font dùng: catalogue XLSX, checklist CSV, fonts CSS/12woff2/OFL dưới vendor; giữ nguồn/pins/56vendor byteexact. Chưa build wheel/smoke installed thì ghi NOT_RUN, không coi khai báo glob là packaged PASS.
Phạm vi **11 targets hữu hạn** dưới đây đã được Root kiểm và đưa vào settings; không tự nới:
- Existing6: `src/kho_tri_thuc/giao_dien/assets/app.js`, `src/kho_tri_thuc/giao_dien/assets/index.html`, `src/kho_tri_thuc/m4/giao_dien/m4.css`, `src/kho_tri_thuc/giao_dien/m4.py`, `src/kho_tri_thuc/k2/crm_khoi_dong.py`, `pyproject.toml`.
- New5: `src/kho_tri_thuc/m4/giao_dien/m4.js`, `tests/test_m4_01c.py`, `tests/test_m4_01c_http.py`, `tests/m4_01c_async.cjs`, `docs/BAO-CAO-M4-01C.md`.
Chỉ thin HTTP m4.py được thêm GET fixture whitelist DEMO tại `/api/m4/mau/{ma}` (route **đề xuất C, chưa có**): builders `fixtures_m4.py` đã có, authenticated/current M4 scope +same server session, explicit fixed names, trả source bytes để chọn/upload bình thường; không client path, không seed XONG/approved/FINAL. Không cần sửa fixtures_m4.py; test native khai source-based manual oracle riêng.
`test_m4_01c.py` kiểm assets/bootstrap/DTO/config hiện có, `test_m4_01c_http.py` fresh retained DEMO ordinary+trusted hiện hành và luồng thật; `m4_01c_async.cjs` kiểm actual JS handlers bằng controlledPromises, không gọi unit giả là browser. Không đổi B/native/CRM/M2/M5/L11 regression tests/guards hoặc expected để accommodate UI.
Protected: server.py, k2/xay_dung.py, m4_demo.py, sql_m17.py, nguon_review/nap_ghim/docx/store, migrations1–17, vendor/reference, mọi M9/business source/oldfixtures. Nếu cần thêm backend/capability thì báo exact gap, Root xử lý riêng trước code; không lách UI. Root có thể bỏ target không cần khi final allowlist, không tự nới11.

## 7. Mười tám ca kiểm GUI hữu hạn sau terminal/freeze

Claude viết định nghĩa/hướng dẫn bấm, self-test NOT_RUN. Root kiểm độc lập actualDEMO retained với final source/receipt/roles/fixture/manual source pins; không copy output làm expected, không gọi code delivery là module PASS.

| Case | Thao tác và quan sát bắt buộc |
|---|---|
| C01 | Bấm mở DEMO→#m4, title/nav/assets/role/list đúng; reopen không duplicate/regrant, unavailable có hướng xử lý. |
| C02 | DU_AN A1 lưu/mở lại HĐ+đợt thiếu; `thieu` chỉ đúng căn cứ, Nộp bị chặn cả direct HTTP. |
| C03 | DOCX vật lý→upload đúng purpose→gắn→native rule-only trích; source bytes/H và catalogue37/TC09 thật, không fabricate values. |
| C04 | DU_AN sửa giá trị/quote hoặc lý do Không áp dụng rồi xác nhận; fake quote, KT/reviewer không xác nhận thay DU_AN. |
| C05 | Writer/vendor/AI/OCR/format unavailable giữ nguồn/nháp; fake plumbing khác native; TrackChanges hai entrypoint bị chặn trước Office/cleanup. |
| C06 | Chưa khai/Không có/Có chưa đủ/Có đủ PL, nguồn/BOQ thiếu chỉ đúng lỗi; future/draft không áp nhầm, hủy có lịch sử. |
| C07 | XLSX thật chọn sheet/header/map; badmap/abc chặn; finding999 không sửa và không tự chặn Nộp khi các căn cứ khác đủ; blank/0 khác. |
| C08 | Ngày/checklist/purpose đúng; zero/media/traversal bị từ chối; thiếu một mục hiện đúng mục, không van_nap/bypass. |
| C09 | Đủ căn cứ→Nộp→snapshot/revision/refs thật; reviewer đọc/tải đúng source; không approval/PDF/AP/Request giả. |
| C10 | Đợt2 reuse đúng HĐ/PL/BOQ nhưng ngày/bộ tài liệu kỳ2 phải có; không duplicate master/auto-complete kỳ2. |
| C11 | Source/tham số đổi sau load→form stale/confirmation hết hiệu lực theo server; không success cũ hoặc đè snapshot kỳ trước. |
| C12 | Doubleclick/unknown-timeout/retry giữ request/key gốc, không duplicate/reparse; changed-body cùng key bị từ chối, arrays BOQ giữ nguyên. |
| C13 | A2/B1/thiếu module/sai capability: list/detail/action/guessedID/raw đúng backend; không leak tên/quote/bytes, không tự owner-only. |
| C14 | Pending rolePOST rồi refresh/open/Nộp/FILE/đổi tiếp: freshGET0 khi barrier, late response0 và latest intent thắng, không deadlock. |
| C15 | M4↔CRM↔M2/M5/L11 đổi vai hai chiều, cả5participant clear/fence chung; M9 code unchanged, old regression giữ nguyên. |
| C16 | Root DEMO revoke→current request/replay/download chặn; UI clear, reopen không reseed; bytes đã tải hợp lệ không bị tuyên bố thu hồi. |
| C17 | Download actual raw nonempty/H/length khớp retained source; metadata/directGET thiếu token không tính tải thành công; lateBlob0click. |
| C18 | 1280/1440: list/params/rawBOQ/checklist/stale/permission đọc được, hành động không khuất, scroll bảng chủ đích và không style leak CRM. |

Root giữ screenshot/case/actor/size thật trong attempt mới: portal, params, BOQ findings, missing checklist, submitted reviewer, stale denial. Chưa có screenshot/runtime thì ghi NOT_RUN; Claude không browser/var. Report phải map HIEN_CO/NOI_C/GOI_SAU, actual routes/DTO/errors/seed/package/launcher, test definitions và giới hạn AI/format; source hoàn chỉnh không bằng nghiệm thu toàn module.

## 8. Các gói full M4 còn tiếp tục

M4-02 nối đủ Review L1–L3/ghép/chạy lại/OCR/báo cáo/tác vụ, Anh/sếp duyệt và PDF đúng revision; thiếu PDF vẫn chờ, không chuyển hai nhánh.
M4-03 nhận nghiệm thu/công nợ chung M2–M4, kế toán xác nhận số NT+taxbasis, advance/retention riêng; không đồng nhất tiền thanh toán với công nợ, không Junsky posting.
M4-04 tạo **nháp** Request thanh toán đợt dưới employee session sau PDF, existing approval riêng; durable crossref/immutable body+revision, unknown-timeout reconcile; AP pending độc lập employee Requestclick/completion. Không Request ký HĐ.
M4-05 kiểm xuyên suốt/quyền/rawfile/amount/replay/concurrency/restart và DEMO feedback. C không hủy full reuse, không thêm CAD/external-contractor scope; không dừng CRM đã được Anh giao ngoài thứ tự writer/file conflict đã chốt.
