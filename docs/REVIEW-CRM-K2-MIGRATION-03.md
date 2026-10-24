# Review độc lập CRM-01 — schema và migration lần 03

19/10/2026, 07:48 +07. **73 criterion PASS, 0 FAIL, 0 SETUP_ERROR, không skip.** Mười criterion vi phạm ở review02 đã được kiểm lại đạt cùng positive controls. Đây là kết quả SQL/schema DEMO có giới hạn; không tự nghiệm thu toàn CRM, HTTP, launcher, GUI hoặc toàn cây33.

## Bản kiểm và phương pháp

Root xác nhận CLI **89659** terminal exit0/ClaudeExit0, stream `is_error=false`, rồi mới release runtime. Receipt `var/codex-dieu-phoi/kiem-chung-20261018-101441/crm03-handoff-20261019-074754-971/terminal-confirmation.json`; manifest121 file SHA256 `82e5e26806e05ef732536fcb0e474ab6ee96f646566e335e728da28921f47c3a`.

Source được bind đúng receipt; hash trước/sau probe không đổi:

| File | SHA256 |
|---|---|
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` | `31f25277b5e08a0f54843191bce2b3e54126dc6770ad02ece310c8265fcac1e5` |
| `src/kho_tri_thuc/ha_tang/postgres.py` | `ffca2c38527ade742d12c5332ff29e3c54eae77f111362c7d5f9b0453bbdf6f8` |
| `src/kho_tri_thuc/k2/crm.py` | `7ac089c5df5501cf24aadf699caa1d02121c662b3d58fee6a561d916abd39336` |

Chỉ dùng fixture DEMO độc lập đã giữ từ review02, actor `MO_PHONG_`, PG loopback. Boundary chạy bằng **LOGIN thực NOSUPERUSER/NOBYPASSRLS/NOINHERIT**, rồi `SET ROLE app_web`; kiểm `current_user`, `session_user`, `rolsuper=false`, `rolbypassrls=false`. Credential chỉ trong process. Guard không xóa và `PYTHONDONTWRITEBYTECODE=1` bật; giữ file/DB/role. Không sửa product hoặc báo cáo của coder.

| Nhóm | Criterion đạt |
|---|---:|
| Prefix migration1–11, fresh12, hai DB11 upgrade/preservation/convergence/repeat | 24 |
| ACL, quyền CREATE schema, login thường thực | 5 |
| Bốn helper: own-PN, foreign/module/context, unknown/existence, internal ACL | 36 |
| Lifecycle valid_to và KT/CFO replacement UTC | 7 |
| Hash source không đổi | 1 |
| **Tổng** | **73** |

Không lặp19ca SQL cũ đã đạt ở review02; không biến số73 thành số test chức năng toàn hệ thống.

## Mười criterion trước đây vi phạm nay đạt

**Hai ca valid_to:** BAN_HANG CRM đúng PN tự đóng bản đã duyệt hoặc mở lại bản đã đóng đều bị `P0001`; không có row thay đổi được chấp nhận. Positive control KT kiểm vân tay và CFO duyệt replacement hợp lệ đạt; CFO đóng đúng predecessor tại `2030-01-01T00:00:00+00` đạt. Ngày31/12/2029 helper trả bản cũ, tại01/01/2030 trả bản mới. CFO đặt boundary khác hoặc mở lại predecessor đều bị `P0001`. Các thao tác thử được rollback.

**Tám ca helper:** đối với mỗi aggregate, aggregate theo dòng lịch, effective version và fingerprint, actor CRM A đọc ID B hoặc actor A `module=[]` đọc A đều trả **NULL**, không số tiền/ID/fingerprint. Đây là kiểm caller scope trên bốn wrapper mới `master.crm_*`; không dùng ACL deny của hàm cũ để giả chứng minh scope của wrapper.

Positive own-PN: actor chỉ CRM, không M1 raw, vẫn đọc hai aggregate A đúng **70 VND** DEMO; effective version A đúng ID đã duyệt; fingerprint A không rỗng. Fixture B có aggregate **60 VND**, nên ca âm không dựa vào dữ liệu rỗng hoặc mặc định0.

Mỗi wrapper còn được kiểm thiếu ID, thiếu login, ID/login lệch; tất cả giữ NULL. ID foreign có thật và UUID không tồn tại đều trả cùng outcome NULL ở bốn cặp kiểm; không thấy tín hiệu existence qua outcome SQL của các ca này. Chưa đo timing side channel và không tuyên bố mọi dạng side channel đã được loại bỏ.

## ACL và SECURITY DEFINER

Metadata CSDL thực xác nhận **PUBLIC EXECUTE=false cho cả tám hàm** (bốn internal cũ và bốn wrapper mới). `app_web` không EXECUTE bốn internal; gọi trực tiếp bị `42501`. `app_web` EXECUTE đúng bốn wrapper; các control own-PN vẫn chạy được.

Search_path thực là `master,kho,pg_temp` hoặc `master,pg_temp`; pg_temp ở cuối. `app_web` không có CREATE trên master/kho. Wrapper dùng `ktt_danh_tinh()` và `ktt_duoc` theo pháp nhân của chính ID tham số; runtime context missing/mismatch đạt. Không dùng effective `current_user` bên trong SECURITY DEFINER để thay danh tính caller.

## Migration11→12 trên dữ liệu đã giữ

Đã so exact checksum joined SQL statements của **M0001–M0011** với source frozen handoff02:11/11 không đổi. M12 được thêm, không sửa lịch sử migration để làm xanh.

Đã snapshot và nâng cấp đúng hai DB đang schema11:

- `kho_test_crm_recheck02_20261019_071909_fad74d3c_v9_huy` — chứa legacy HUY thiếu provenance.
- `kho_test_crm_recheck02_20261019_071909_fad74d3c_old10` — chứa approved history, lịch và link70/60 DEMO, audit tương thích oldM10.

Cả hai lên12, operational schema (columns/constraints/policies/function bodies, loại metadata audit tương thích) khớp DB fresh12. `schema_migrations`1–11 giữ nguyên **version/checksum/applied_at**; số đếm/hash dữ liệu của mọi cột tồn tại trước upgrade không đổi; audit tương thích M10 giữ nguyên; marker HUY và NULL người/thời điểm/lý do cũ giữ nguyên. Migrate lặp giữ history/data/signature. Không DROP/recreate, không rewrite checksum, không bịa cancellation audit.

Giữ lại một freshDB và một login role mới; hai DB cũ được nâng cấp tại chỗ có snapshot trước. Đây là kiểm nâng cấp schema11 cụ thể; đường v9/oldM10 đã được kiểm ở review02 và không được chạy lại từ đầu trong lượt này.

## Evidence và phạm vi kết luận

Probe: `var/codex-dieu-phoi/crm-schema-recheck03/probe.py`.

Evidence: `var/codex-dieu-phoi/crm-schema-recheck03/run-20261019-074825-14421b5e/result.json`, SHA256 **`556bd4f4d858ac8c0d65dfb46d1bd5188bd6cafb971df51254a3c4f9534eccd9`**. Hai file `retained0-before.json`, `retained1-before.json` cạnh kết quả giữ snapshot trước upgrade.

Phần schema/helper/lifecycle sửa03 đủ bằng chứng độc lập cho10criterion đã giao. Không có finding chặn mới trong tập kiểm này. Kết quả M1/parser/launcher/HTTP/GUI thuộc review riêng; kho thật vẫn SQLite, không có quyền production, CFO_NTD hoặc Junsky mức2 được kích hoạt từ lượt kiểm này.
