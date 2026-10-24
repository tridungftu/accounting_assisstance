# BÁO CÁO L11 QUANTITY — REPAIR03 (CODE_ONLY)

- Căn cứ: `docs/GIAO-CODE-L11-QUANTITY-03.md` (pin 27af004c…6d06), kế thừa handoff01/02 + cases01; review `REVIEW-L11-ROOT-ACTUAL-02.md`, `REVIEW-L11-HTTP-UI-02.md`, `REVIEW-L11-LOCK-02.md`. Lineage 02→01→R15 giữ nguyên.
- **CODE_ONLY**: không execute/import/compile/test/SQL/PG/HTTP/JS/browser/CLI/process/network; không credentials/var/.git/sourceapps/dữ liệu thật; không delete/move/drop/reset.
- **Mọi selftest của coder: UNRUN.** Không có PASS, không có checksum M0016 mới (root đo khi freeze), không có kết luận race/UI/L11 đầy đủ/full33.

## 1. Tệp đã ghi

| Tệp | Thay đổi (line hiện hành) |
|---|---|
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` | **Chỉ 16.** `l11_khoa_dong_nguon_noi_bo` `6581` (bind pool lúc precollect, kiểm lại trùng khít ngay sau gốc, trước pool/hàng); `l11_xac_nhan_bang_chung` `6972` (nhánh NATIVE_ENCODING: độ dài + hỗ trợ nguồn thật trước INSERT, chặn `L11_HO_TRO_CHUA_CAPTURE` `7156`); `l11_huy_bang_chung` `7194` (closure bind một lần, kiểm lại sau gốc và sau hàng bằng chứng); `l11_ma_hoa` `7415` (kiểm lại độ dài bất biến); `_R1_M2_BATCH` `8154` (cổng identity toàn batch); `_L11_R1_THAY` `8185`; bảng `bang_chung_quy_doi_luong` thêm `native_byte_length` `8351` + CHECK theo kind + guard bất biến; DTO danh sách/FILE thêm độ dài |
| `src/kho_tri_thuc/giao_dien/assets/app.js` | `l11Act` `1196` (ngữ cảnh gốc + **vé** GET của chính thao tác `1206`); `l11Tai` `1214` (kiểm sau headers và sau body, ngay trước click); nút FILE `1346` (chụp form epoch + liên kết + token đồ thị, truyền predicate thật); facts hiển thị độ dài native |
| `tests/test_l11_migrations.py` | Sửa oracle D; tĩnh R1-L01/L02 + C — UNRUN |
| `tests/test_l11_k2.py` | Sửa oracle D; thứ tự capture-trước-duyệt; âm C; A,A; batch identity; Q09 route↔confirm — UNRUN |
| `tests/test_l11_http.py` | Chỉ thêm chuỗi asset (không chứng minh async) — UNRUN |
| `docs/BAO-CAO-L11-QUANTITY-03.md` | Tạo mới |

Không sửa (không cần): `lien_ket_chung.py`, `kho_so_luong.py`, `hoa_don.py`, `quyen.py`, `crm_khoi_dong.py`, `nguon_chung.py`, `server.py`, `index.html`, `l11_demo.py`. Không chạm report01/02, reviews, fixtures, seed M2/M5, M9. Literal/generated 1–15 byte-identical; không append 17.

## 2. A — giao thức khóa toàn batch

**Vấn đề kế thừa và vấn đề do 02 đưa vào (static, chưa tái hiện runtime):**

- (i) Kế thừa từ R15: vòng lặp consumer M2 xin namespace `HOA_DON|PN|identity` rồi `HOA_DON_ROOT` theo thứ tự XML/ZIP. Hai batch mới [A,B]/[B,A] có thể chờ vòng.
- (ii) Do repair02 đưa vào: precollect chỉ gồm hóa đơn đã có, nên batch trộn hoặc identity vừa xuất hiện xin namespace **sau** khi đã giữ root/pool → đảo thứ tự namespace/root.

**Sửa:** `_R1_M2_BATCH` được chèn vào `m2_tieu_thu_quan_sat` sinh trong 16, sau kiểm actor/INTAKE/stage/replay và **trước** vòng lặp lịch sử:

1. Hàng mapping công ty của batch, sorted, `FOR SHARE` (giữ thứ tự R15).
2. **Mọi** namespace `HOA_DON|PN|identity` của batch, sorted theo khóa văn bản.
3. Dưới namespace: tạo **skeleton** danh tính cho identity mới hợp lệ — chỉ hàng danh tính, cùng giá trị và điều kiện vòng lặp lịch sử sẽ chèn, không quan sát/nội dung/con trỏ/core.
4. Resolve **mọi** ID của batch.
5. `l11_khoa_dong_nguon_noi_bo`: gốc hóa đơn sorted + gốc phiếu ngang hàng → kiểm lại → pool → child.

Vòng lặp lịch sử giữ **nguyên** thứ tự delivery/occurrence (phân loại A,A / A→B→A / ZIP không đổi); mọi khóa nó xin sau đó là tái nhập. Namespace `HOA_DON|` chỉ consumer này xin (grep toàn source: một chỗ duy nhất), nên thứ tự chung là: **mapping → namespace → gốc → pool → hàng**. M5 chỉ có một phiếu mỗi lần nhận và khóa gốc theo khóa (instance, SoPhieu); không có namespace riêng.

**Kiểm lại closure (R1-L02):**

- `l11_khoa_dong_nguon_noi_bo` bind tập child/pool ở precollect → khóa gốc → đọc lại tập child **trùng khít**. Nếu khác (child mới cùng cặp nhưng LINE/pool mới, child đã HUY, gốc mới) → `L11_CLOSURE_MO_RONG`, hủy toàn thao tác **trước** khi xin pool/hàng. Sau đó mới khóa pool đã bind và hàng child.
- `l11_huy_bang_chung` theo cùng mẫu, rồi khóa hàng bằng chứng `FOR UPDATE` và đọc lại lần hai: confirm ở cặp gốc khác có thể đã commit trong lúc chờ hàng bằng chứng → khác thì hủy. Đã bỏ truy vấn pool mới sau khi chờ gốc.

**Các đường còn lại** đã kiểm theo cùng thứ tự gốc → pool → hàng: confirm, undo, encoding, FILE, 5 đường M5, M2 review/map/route/mapping công ty, trigger mapping chung. Hành vi do Python mutex không được tính là bằng chứng an toàn CSDL.

## 3. B — FILE continuation

- `l11Act` chụp epoch + vai + predicate của người gọi; sau POST kiểm lại; GET làm mới do chính thao tác mở trả **vé** thế hệ bất biến.
- Fence trả về = `ctx() && ve === l11Gen`: bất kỳ GET cạnh tranh nào mới hơn đều hủy continuation suốt đời của nó.
- Lỗi trong `catch` chỉ hiện khi ngữ cảnh còn đúng.
- Nút FILE chụp `l11FormEpoch`, id liên kết và `co_so_sha256` lúc bấm, rồi truyền làm predicate thật cho `l11Act`.
- `l11Tai` dùng **chính** fence đó, kiểm trước request, sau headers và sau Blob — ngay trước click thật. Đổi cặp/lượng/vai hoặc GET mới hơn → 0 click/toast/status cũ.
- Quyền server trước replay/download, selector 2 login, facts/proof GET/one-RR: giữ nguyên.

## 4. C — NATIVE_ENCODING: độ dài + hỗ trợ nguồn thật trước khi duyệt

Trước INSERT bằng chứng đã duyệt, nhánh NATIVE_ENCODING kiểm theo thứ tự:

1. `native_byte_length` phải là **JSON number nguyên dương** (regex `^[1-9][0-9]{0,17}$`); chuỗi/0/âm/thập phân → `L11_DO_DAI_NATIVE_SAI`.
2. Miền hóa đơn của bằng chứng hàng = ngữ cảnh hỗ trợ của định nghĩa native (instance/profile/payload SHA) → nếu không, `L11_BANG_CHUNG_MA_HOA_KHONG_KHOP`.
3. Có dòng **XML_LINE thật đã capture** qua COMMON + reader: đúng artifact SHA, đúng ngữ cảnh hỗ trợ, `source_locator + '/DVTinh'` = locator khai → nếu không, `L11_HO_TRO_CHUA_CAPTURE`.
4. Độ dài thật của dòng reader **và** catalog = claim → nếu không, `L11_DO_DAI_NATIVE_SAI`.
5. Lexeme đơn vị/số lượng, locator số lượng và mã hàng thật = claim/miền hàng → nếu không, `L11_HO_TRO_DON_VI_KHONG_KHOP`.
6. `l11_ho_tro_don_vi_noi_bo(native def, mã hàng)` — trường hỗ trợ khai báo của định nghĩa.

Tuple độ dài được lưu bất biến (`native_byte_length`): có CHECK theo kind, có trong guard ROW, DTO danh sách và snapshot FILE. Encode kiểm lại độ dài so với dòng hiện hành, cùng các kiểm ngữ cảnh/hỗ trợ đã có từ 02.

Không viết parser SQL mới; chỉ dùng dòng reader/COMMON đã capture. SAME_VERIFIED M2 với seed support NULL giữ fallback dòng thật như 02; không sửa seed/profile. Giữ phân biệt MASTER 3a8…/3c6…; đo lường hiện hành và source_ordinal giữ như 02. Bốn proof mặc định và 20 fixture không đổi.

## 5. D — hai oracle

- `test_l11_migrations.py` (UPDATE retarget): assert đúng `(P0001, LIEN_KET_KHONG_SUA)` của trigger lịch sử `lien_ket_kiem`, và hàng không đổi. Không đổi thứ tự trigger/quyền. Ca INSERT vẫn kiểm `L11_LIEN_KET_CHUNG_GIA`.
- `test_l11_k2.py` t04: app UPDATE parent tách khỏi vòng 42501 và assert đúng `L11_CHA_BAT_BIEN` cho riêng thao tác đó. Các thao tác khác giữ 42501 hoặc mã biên nhận cụ thể; không dùng chuỗi con `L11_`.

## 6. Test đã viết (tất cả UNRUN)

**Tĩnh (`test_l11_migrations.py`):**

- `test_r1_repair03_cong_identity_va_kiem_lai_trung_khit`: thứ tự mapping → namespace sorted → skeleton → closure → vòng lặp lịch sử; helper/revoke kiểm lại trước pool; không còn truy vấn pool mới sau gốc.
- `test_c_native_ma_hoa_do_dai_va_ho_tro_truoc_duyet`.
- Ca insert-only diff của 11 đường vẫn đúng (cổng là khối chèn thêm).

**PG trong `test_l11_k2.py`:**

| Ca | Nội dung |
|---|---|
| t01 | Duyệt THUNG_ENCODING trước capture → `L11_HO_TRO_CHUA_CAPTURE`, 0 bằng chứng mới; capture THUNG qua service M2 thật rồi duyệt dương; `native_byte_length = 480` |
| t03b | A,A: nhận lại G01/K01 khóa mới → SAME_CONTENT_REPEAT, child không đổi trạng thái, ngân sách giữ |
| t04 | Oracle `L11_CHA_BAT_BIEN` |
| `L11PhiDongNhatPg` | Đăng ký 5 bằng chứng tổng hợp qua đường COMMON sẵn có. Duyệt trước capture → `L11_HO_TRO_CHUA_CAPTURE`. Sau capture, các âm đúng mã với 0 bằng chứng/mã hóa/child/ứng viên mới: độ dài 479 / độ dài chuỗi `"480"` → `L11_DO_DAI_NATIVE_SAI`; lexeme số lượng sai → `L11_HO_TRO_DON_VI_KHONG_KHOP`; profile khác → `L11_BANG_CHUNG_MA_HOA_KHONG_KHOP`. Rồi dương; giữ dương 0.01/0.12 và âm 0.01/1.44 |
| `L11LoDanhTinhPg` | ZIP trong bộ nhớ [A,B] mới → [B,A] đã có → trộn đã có + mới (G04). Phân loại đúng, không danh tính thừa, không skeleton mồ côi. **Tuần tự, không phải bằng chứng đồng thời** |
| `L11Q09TuyenXacNhanPg` | Hai kết nối app thật, giao dịch mở, `pg_blocking_pids` đúng PID kẻ thắng, watchdog (lock_timeout + join timeout). (q02) route thắng → confirm nhận đúng `L11_VERSION_CHANGED`, 0 child/parent/biên nhận. (q03) confirm thắng → route nhận đúng `L11_CLOSURE_MO_RONG`, 0 tuyến mới, child còn CO_HIEU_LUC; đối chứng **tuần tự** riêng với token mới → CAN_SOAT `TUYEN_DOI_KHOI_KHO` |

## 7. Mã lỗi mới

- `L11_DO_DAI_NATIVE_SAI` (400)
- `L11_HO_TRO_CHUA_CAPTURE` (400)

Đổi ngữ nghĩa: `L11_CLOSURE_MO_RONG` nay cũng bắt tập child/pool khác (không chỉ gốc mới); dùng trong cả 11 đường nguồn và thu hồi.

## 8. Kiểm soát còn thiếu (UNRUN / chưa viết)

- **Q09 chưa viết:**
  - Revoke bằng chứng đang dùng ↔ confirm, undo held ↔ confirm mới (cả hai thứ tự).
  - Hai batch ZIP đồng thời thứ tự ngược.
  - Lịch identity vừa xuất hiện (late-visible).
  - Cùng gốc nhưng LINE mới.
  - Multipool hai thứ tự thắng.
- **Q05:** A→B→A với liên kết sống (cần biến thể nội dung của cùng hóa đơn/phiếu có child); source-only intake giữ soát nguyên tử bằng nội dung đổi/nguồn đảo.
- **Q04/Q07** như 02: sức chứa 8/4, nguồn đảo, profile/đơn vị đổi, login ngưng, kỳ khóa.
- **C:** chưa có âm cho khai locator đơn vị trỏ dòng khác và cho thiếu artifact hỗ trợ của định nghĩa (khác artifact dòng).
- **UI (B):** chưa có adapter chạy handler thật cho đổi cặp/lượng trong refresh pending và trong blob pending, hai thứ tự đổi vai, và GET mới hơn khi blob đang tải. Test chuỗi asset không đóng hành vi async.
- **Nâng cấp 15→16 có dữ liệu nguồn M2/M5 đầy đủ:** chưa.
- **Giới hạn đã biết:** skeleton danh tính được tạo dưới namespace trước khi vòng lặp chạy. Nếu một item sau đó lỗi, toàn giao dịch rollback nên không còn skeleton; test b01 có kiểm "không skeleton mồ côi" ở ca dương, nhưng chưa có ca âm.
- **Test cũ ngoài phạm vi sẽ đổi** (như 01/02): `test_m5_http.py:170–171`, `test_m2_migrations.py` (schema 15).

**Kết luận:** repair03 CODE_ONLY đã viết xong; mọi selftest UNRUN; chờ root terminal + freeze + review và release runtime riêng.
