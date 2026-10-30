# KK-UI-DA-BG — Kiểm kê và chia lát CD-022/023/024

Ngày 27/10/2026 · nhánh `lat/kk-ui-da-bg`, HEAD `87c963c` (dòng giao diện). **Chỉ kiểm kê, chưa triển khai; chưa sẵn sàng báo Anh thử.** Đề xuất giữ schema phiên bản/mốc hiện có, bổ sung lệnh lưu trọn lượt và mẫu do người dùng lưu; thống nhất engine tiền trước UI.

Căn cứ: nguyên văn CD-022/023/024 trong handoff (file `CHI-DAO-TU-ANH.md` ở HEAD này chưa có các CD mới); CD-006/007 trong file đó; `D:\Claude\Phan mem ho tro ke toan\45-review-man-bao-gia-sau-lap-trinh.md` §9 đã có đủ BG-25…28. CD-019 một engine và QD-09 thêm dòng được áp theo handoff; chưa có nguyên văn CD-019 trong file chỉ đạo của worktree. Dưới đây: `JS` = `src/kho_tri_thuc/giao_dien/assets/crm_g.js`; `HTTP` = `src/kho_tri_thuc/giao_dien/crm_g.py`; `DA`, `GK`, `MAU`, `SQL-DA`, `SQL-MỐC` lần lượt là `crm_du_an_ban.py`, `crm_giao_ket.py`, `crm_mau.py`, `sql_crm_du_an_ban.py`, `sql_crm_du_an_moc.py` trong `src/kho_tri_thuc/k2/`; `PG` = `src/kho_tri_thuc/ha_tang/pg_migrations.py`. Dòng dẫn theo HEAD nêu trên.

## 1. Hiện trạng và phần cần đổi

| Yêu cầu | Mã hiện có, phần dùng lại → phần đổi |
|---|---|
| CD-022: bảng % + mốc | `JS:416`, `JS:581`, `JS:1093` dùng bảng G7 có cả PERCENT/AMOUNT/tiền tệ, không phải bảng chỉ %. Giữ nháp, lỗi theo ô, CAS, chống phản hồi trễ; thay thành Lần · % · Mốc · Ghi chú, nhập nhanh %/số lần, Σ%=100, không tiền ở cấp dự án. `DA:545`, `SQL-DA:497` hiện nhận G7 tổng quát; phải kiểm PERCENT và tổng tại backend, không chỉ UI. |
| CD-022: một tiến độ chuẩn | `JS:405`–`407` chặn thiếu giai đoạn; `JS:569` hiện ô; `DA:118`, `DA:552`, `SQL-DA:508`–`521` vẫn yêu cầu/chọn giai đoạn. Bỏ ô và điều kiện này; máy giữ một mã chuẩn nội bộ cho mỗi dự án, đọc lịch cũ theo bản đã ghim. Không tự chọn ngẫu nhiên một G7 khi dữ liệu cũ có nhiều giai đoạn. |
| CD-022: mốc và tiếng Việt | `SQL-MỐC:18`–`47`, `DA:522`, `JS:631` đã tách `DAM-UUID` khỏi tên Unicode, có dự kiến/thực tế; dùng lại. `JS:585` chỉ nạp mốc cơ bản cho editor tiến độ, giữ mốc cũ nếu có; phải ghép thêm mốc riêng đang dùng của dự án. Giữ CD-007: chưa thực tế không quá hạn; quá ngày dự kiến có một việc chờ; thực tế + n ngày mới thành hạn. |
| CD-022: ghi chú khi sửa | `JS:452`, `JS:597` đang bắt Lý do cả lúc bật bán/phí, lại không có ở lô/tiến độ; `JS:630`, `JS:688` chỉ hỏi một số sửa ngày mốc. `DA:486`–`528` chuẩn hóa lý do nhưng phần lớn chưa bắt buộc; `SQL-MỐC:162` chỉ bắt khi đổi dự kiến/đổi thực tế đã ghi. Đổi thành một ô **Ghi chú thay đổi** chung khi sửa dự án đã lưu, bắt buộc cho mọi khối; khai ban đầu không hiện/không bắt. Backend phải kiểm tương ứng. |
| CD-023: một màn, một Lưu | `JS:391`, `JS:532`, `JS:631`, `JS:826` chia form thông tin/phí/lô/tiến độ/từng mốc; `HTTP:697`–`704` chia endpoint. Phí/lô đã là bảng nhiều dòng và có lỗi tại ô (`JS:546`–`559`); dùng lại. Chưa có trang sáu khối gấp/mở, Enter thêm phí, dán TSV từ Excel, giao dịch lưu một lượt/một phiên bản. Không ghép nhiều POST cũ thành nút Lưu vì lỗi giữa chừng sẽ lưu dở. |
| CD-023: sao chép, Lưu làm mẫu | Snapshot dự án có sẵn (`SQL-DA:572`, `GK:909`), nhưng chưa có API/UI sao chép hoặc thư viện mẫu dự án. Mẫu DOCX G1 là loại khác, không dùng thay mẫu dự án. Copy thông tin/giá/thuế/phí/mốc/tiến độ; bỏ lô, tên/mã nguồn, ngày thực tế; sinh lại ID mốc và remap lịch. Ghim nguồn X phiên bản n trong nhật ký; lưu mẫu có tên/loại do Anh hoặc kế toán đặt, không seed cứng ba nội dung mẫu. |
| CD-024 BG-25/26 | `JS:2095`–`2097`: nút mới thuộc đầu khối Danh sách; chuyển cạnh tiêu đề Báo giá. `JS:1753`, `GK:631`: khối lớn lấy `tong_minor`/bằng chữ theo cơ sở giá hiện có, chưa tách net/VAT/gross; đổi số lớn và bằng chữ sang gross, dưới hiện net + VAT. |
| CD-024 BG-27/28; CD-038 câu 2B | `GK:391`–`643` tính lịch theo tổng hiện có, chưa phân bổ VAT, chưa cờ cọc; số lẻ đợt bị báo sai scale (`GK:511`). `JS:1963` có hai ô %/tiền nhưng chỉ tiền có class chữ lớn (`JS:1989`), chưa cột VAT. Dùng lại nhập nhanh (`JS:1916`), debounce/fence; thêm đánh dấu cọc, VAT từng dòng và tổng, suy % từ tiền gross qua engine. **Bỏ ràng buộc “đợt cọc = dòng 1”**: cho cọc cuối/nhiều cọc; VAT dồn tới đợt không cọc gần nhất phía sau, hết phía sau thì về đợt không cọc gần nhất phía trước; toàn cọc → lỗi. |
| DA-3a, in và Soạn | `GK:909`–`926` đã trả lịch/thuế/đất trừ nhưng ghi rõ thuế **chỉ hiển thị**; tìm toàn bộ JS chưa thấy gọi `/bao-gia/mac-dinh`. `JS:2192`, `JS:2256` còn nạp G7 thủ công bằng giai đoạn. Phải nối chọn dự án → nạp mặc định thật. In hiện bốn cột (`GK:1367`, `nguon/crm_docx.py:323`); chuyển Soạn giữ báo giá nhưng trường tiền lấy tổng cũ (`GK:1175`–`1186`). Cả hai phải giữ sáu cột, cờ cọc, net/VAT/gross và đúng cơ sở trường trong mẫu. |

## 2. Toàn bộ chỗ áp quy tắc chữ/số/_ . - lên ô gõ

Đã tìm toàn bộ tệp mã `.py/.js/.sql/.html` trong `src` bằng câu lỗi và regex ASCII tương ứng. Các đường vào liên quan đầy đủ như sau; không đánh đồng mã kỹ thuật với tên hiển thị.

| Ô/đường vào | Validator và ràng buộc cuối | Đề xuất |
|---|---|---|
| Giai đoạn mặc định dự án (`JS:569`), tham số tiến độ | `DA:119`–`120`, `DA:554`–`555`; `SQL-DA:110`, `SQL-DA:275`–`276`, `SQL-DA:512`–`513` | Ẩn khỏi người dùng; backend tự giữ mã chuẩn. |
| Sự kiện dòng lịch Báo giá/Soạn; Sự kiện G7 (`JS:1098`) | `GK:288`–`289`; G7 Python `MAU:384` chưa kiểm tên nhưng INSERT chịu CHECK `PG:9947` | Gõ/chọn tên tiếng Việt → resolve mốc hợp lệ → gửi mã. Mốc riêng tạo trong khối mốc dự án, máy sinh `DAM-UUID`; không biến tên tự do thành mã tùy ý hoặc nới CHECK mã. |
| Giai đoạn G7 ở Báo giá (`JS:2192`), đọc bộ chuẩn (`JS:1063`–`1065`) | `GK:347`–`348`, `MAU:427`–`428` (câu lỗi khác nhưng cùng regex); `PG:9877` | Chọn dự án là đủ, backend resolve mã; bộ chuẩn cũ vẫn xem qua tham chiếu nội bộ. |
| Giai đoạn ở hàm lập G7 cũ (`JS:1104`–`1106`) | `MAU:410`–`411`, CHECK `PG:9877` | `veLap` còn định nghĩa, không thấy nơi gọi; API cũ vẫn cần chặn đường nhập tên làm mã, không chỉ bỏ UI. |
| Mã mẫu DOCX ngoài màn Dự án (`JS:944`) | `MAU:318`–`319`, CHECK `PG:9744` | Thay ô bằng Tên mẫu Unicode + chọn mẫu có sẵn để thêm phiên bản; máy sinh mã ổn định. Schema G1 chưa có tên hiển thị riêng: cần bổ sung lưu tên, không mất khả năng chọn đúng mẫu cũ. |

Tên phí/cơ sở tính (`DA:142`), mô tả/vị trí (`DA:121`), tên/tên tắt mốc (`SQL-MỐC:35`) **đã nhận dấu và khoảng trắng**, không cần nới regex. Các regex idempotency/request ID/lease, mã tiền, placeholder `{{...}}`, cấu hình tải hóa đơn và lọc tên tệp tải xuống là mã/giao thức hoặc làm sạch tên tệp, không phải validator tên người dùng; giữ giới hạn kỹ thuật, không hiện chúng thành ô đặt tên. Không thấy chỗ khác phát câu lỗi này ngoài các đường trên.

## 3. Dữ liệu và migration đề xuất

**Đủ để tái sử dụng:** G7 `crm_bo_chuan_phien_ban`/`crm_bo_chuan_dong` lưu lần, %, mốc, ghi chú (`PG:9938`); dự án/phiên bản/phí/lịch sử lô (`SQL-DA:61`–`175`); mốc có ngày và lịch sử (`SQL-MỐC:18`); `nhat_ky.su_kien` có ai/lúc/trước/sau/lý do (`SQL-DA:378`, `SQL-MỐC:124`). Báo giá có JSON `du_lieu`, `tinh`, `g7` bất biến (`PG:10668`–`10687`), Soạn cũng lưu JSON (`PG:11079`); đủ chứa cờ cọc, phần không chịu thuế, kết quả từng đợt, engine version mà không thêm cột theo đợt.

**Thiếu:** phiên bản tổng hợp ghim đồng thời thông tin + phí + lô + mốc + G7; mẫu dự án có tên/loại/phiên bản/nội dung; nguồn copy/mẫu và mapping mốc; tên hiển thị G1. Nhật ký thông tin/phí đã cũ → mới, nhưng tiến độ hiện chỉ `sau`/ID bản trước và lý do cố định (`SQL-DA:560`–`565`), chưa đáp ứng một ghi chú chung và diff toàn lượt.

Đề xuất schema cố định: bổ sung một snapshot JSON tổng hợp vào phiên bản dự án (hoặc bản ghi liên kết phiên bản tương đương), chứa ID/lần mốc, ID/lần lô, G7 version, nguồn và nội dung chuẩn hóa. Lệnh lưu giữ khóa dự án, kiểm toàn bộ expected versions, ghi một phiên bản tổng và một sự kiện toàn lượt; các bảng con tiếp tục thêm dòng lịch sử trong cùng transaction, lỗi bất kỳ rollback hết; không đổi nội dung thì không thêm phiên bản. Mẫu có một bảng định danh và một bảng revision cố định, snapshot chỉ các khối được copy, ghim phiên bản nguồn. Tạo dự án từ mẫu không phụ thuộc việc dự án nguồn đổi về sau. Dữ liệu cũ giữ nguyên, chỉ có phiên bản tổng hợp khi phát sinh lượt mới.

Migration **chỉ append** `M00xx_*` và đăng ký registry sau khi lead cấp số, đánh dấu `# <MÃ LÁT> — …:`. Không sửa các tuple M0018/M0021/M0030/M0031/M0035 hay SQL module đang được các tuple cũ import. SQL mới đặt module riêng, mỗi đợt sau thêm constant mới, không sửa constant đã đăng ký. Theo QD-09: số lần, mốc, dòng phí/mẫu là **dòng dữ liệu**, không bảng/cột riêng theo mỗi dự án/đợt/mẫu. Giữ trigger bất biến, RLS và phạm vi pháp nhân; không tự cấp quyền đọc/copy/mẫu vượt quyền hiện tại. Kiểm `AS $$`/`$$`, UTF-8 không BOM; `PG` giữ LF; không dùng test CRLF/LF hoặc ghim migration cuối.

## 4. VAT cọc và một engine

**BG-27 — quy tắc VAT cọc đã chốt tại CD-038 câu 2B; công thức triển khai CD-024 bên dưới không phải kết luận pháp lý:** cho phép cọc đợt cuối hoặc nhiều đợt cọc; không ràng buộc “đợt cọc = dòng 1”. VAT mỗi đợt cọc dồn vào đợt **không cọc gần nhất phía sau**; không còn đợt không cọc phía sau thì dồn ngược về đợt **không cọc gần nhất phía trước**. Lịch **toàn đợt cọc → lỗi**, gồm lịch chỉ một dòng cọc; một dòng không cọc được tính bình thường.

N là tổng giá bán trước VAT, E là phần không chịu thuế/được trừ đã có căn cứ (0≤E≤N), r là thuế suất dạng thập phân. VAT hợp đồng V = R((N−E)r), gross G=N+V; R làm tròn half-up đến đơn vị nhỏ nhất (VND: đồng). Giá đất trừ/m² phải nhân diện tích và quy đổi cùng tỷ giá tiền chính trước khi thành E; không lấy % cọc nhân cả N để tính VAT nếu có E. CD-038 câu 1A: lịch bản đầu chỉ giá bán, Σ%=100 cho giá bán; phí theo dõi riêng, thêm sau không phá phiên bản, không tự cộng phí vào N.

Với pᵢ, Σpᵢ=100: trước làm tròn bᵢ=Npᵢ/100, vᵢ=Vpᵢ/100 (phân bổ phần chịu/không chịu thuế theo cùng tỷ lệ). Các dòng trước cuối: Bᵢ=R(bᵢ), Vᵢ=R(vᵢ); dòng cuối Bₙ=N−ΣBᵢ, Vₙ=V−ΣVᵢ. Gọi d(c) là đích không cọc của c theo quy tắc sau/trước ở trên: T꜀=0 tại cọc; tại đợt không cọc j, Tⱼ=Vⱼ+ΣV꜀ với d(c)=j (cộng đủ nhiều cọc cùng đích). Tiền thu Aᵢ=Bᵢ+Tᵢ. Như vậy ΣB=N, ΣT=V, ΣA=G, Σ(A−T)=N; phân biệt VAT phân bổ với VAT thực thu. Phân bổ phần dư dòng cuối **trước** dồn VAT; nếu dòng cuối là cọc thì Vₙ cũng chuyển về đích không cọc, không để VAT thực thu ở cọc. Không sửa %/số tiền gốc người nhập để che lệch; kết quả âm/ngoài miền phải báo lỗi.

| Kiểm bằng dữ liệu giả | Cọc | Đợt kế | Đợt cuối | Tổng |
|---|---:|---:|---:|---:|
| N=1.000.000.000; E=0; r=10%; p=10/30/60% | 100.000.000 | 340.000.000 | 660.000.000 | **1.100.000.000** |
| Trong đó VAT thu | 0 | 40.000.000 | 60.000.000 | **100.000.000** |
| Cùng N, E=200.000.000; r=10% | 100.000.000 | 332.000.000 | 648.000.000 | **1.080.000.000** |
| N=101; E=0; r=10%; p=10/30/60% | 10 | 34 | 67 | **111** (B=10/30/61; T=0/4/6) |

**Ba ca kiểm bổ sung BG-27 theo CD-038** — cùng N=1.000.000.000 VND, E=0, r=10%, V=100.000.000, G=1.100.000.000; số trong bảng là triệu VND. Ví dụ JSON tương ứng tại NV-CRM §1 của `CONTRACT-NGHIEP-VU.md`.

| Ca | p và cọc | B=N×p/100; VAT phân bổ=V×p/100 | VAT thu T sau dồn | Tiền thu A=B+T; tổng |
|---|---|---|---|---|
| Cọc đợt cuối | 30/50/20%; dòng 3 cọc | B=300/500/200; Vᵢ=30/50/20 | 30/(50+20)/0=30/70/0; d(3)=2 | 330/570/200; ΣA=1.100, ΣT=100 |
| Hai đợt cọc liền nhau | 20/30/50%; dòng 1,2 cọc | B=200/300/500; Vᵢ=20/30/50 | 0/0/(50+20+30)=0/0/100; d(1)=d(2)=3 | 200/300/600; ΣA=1.100, ΣT=100 |
| Cọc xen giữa | 10/30/20/40%; dòng 1,3 cọc | B=100/300/200/400; Vᵢ=10/30/20/40 | 0/(30+10)/0/(40+20)=0/40/0/60; d(1)=2, d(3)=4 | 100/340/200/460; ΣA=1.100, ΣT=100 |

Ca âm bắt buộc: đánh dấu toàn bộ dòng là cọc (kể cả một dòng 100%) → lỗi tại lịch, chặn in/chuyển hiệu lực; không tự thêm đợt hoặc bỏ cờ cọc. Ba ca hợp lệ phải giữ nguyên qua xem trước/Lưu/In/chuyển Soạn/Ký bằng cùng engine.

Gõ tiền gross: đặt k=V/N (N>0); cọc B=A; đợt không cọc j nhận Dⱼ=ΣV꜀ với d(c)=j thì Bⱼ=(Aⱼ−Dⱼ)/(1+k), đợt không nhận VAT cọc có Dⱼ=0; p=100B/N. Đây là phép suy trước làm tròn; phải giải/đối soát cả lịch vì Dⱼ có thể đến từ nhiều cọc phía trước hoặc phía sau, không chỉ dòng liền trước. Engine dùng số hữu tỷ, đối soát lại A sau làm tròn và trả % xấp xỉ khi cần, giữ số gốc như cơ chế hiện tại; N=0 không được chia mà xử lý theo miền hợp lệ đã chốt. Không chia trực tiếp tiền đợt nhận VAT cọc cho N hoặc G. Thuế 0/không chịu thuế: V=0, A=B (vẫn chặn lịch toàn cọc). NET/GROSS phải được khai rõ; khi đầu vào là gross và E xác định, suy N=(G+rE)/(1+r), không cộng VAT lần nữa.

**Vị trí đề xuất:** một hàm SQL thuần `master.crm_gk_tinh_thanh_toan(jsonb)` trong module mới `k2/sql_crm_thanh_toan.py`, chuẩn hóa kết quả net/VAT/gross/%/VAT thu từng dòng. Lý do: `GK:tinh_bao_gia` tính ở Python trong khi bước Ký đã tính lại ở `k2/sql_crm_bg1c.py:22`; chỉ thêm VAT ở Python sẽ tiếp tục hai nơi tính. Phiên bản mới đi qua SQL canonical; Python giữ việc chuẩn hóa, lỗi nghiệp vụ, định dạng và điều phối, không chép công thức VAT/suy % vào JS hay renderer. Màn xem trước, Lưu, In, chuyển/đọc/sửa/xuất Soạn và kiểm Ký cùng tiêu thụ kết quả đó; append wrapper Ký gọi engine, không sửa M0030. JSON ghim engine version/quy tắc thuế để bản cũ không âm thầm đổi tiền. Test hàm SQL độc lập bằng số giả, rồi test qua service; không nhận kết quả tính do client gửi. Mẫu hợp đồng map trường net hay gross theo cơ sở đã khai, không đổi tất cả trường thành gross.

## 5. Chia lát (đề xuất tên, lead cấp handoff và số migration)

Mỗi hàng tối đa **3 tệp kể cả test**; tệp mới ghi rõ “mới”. Ký hiệu `t/` = `tests/`, `k2/` = `src/kho_tri_thuc/k2/`. Không triển khai các thay đổi này trong lát kiểm kê.

| Thứ tự/lát | Tệp được đổi (đủ danh sách) | Kết quả/kiểm chính |
|---|---|---|
| 1 DA-B1 | `k2/sql_crm_du_an_mot_luot.py` (mới), `PG`, `t/test_crm_du_an_mot_luot_pg.py` (mới) | Append schema snapshot/lệnh atomic, chuẩn %/mốc/mã ẩn, ghi chú khi sửa. PG: rollback, CAS, replay, diff toàn lượt, quyền. |
| 2 DA-B2 | `DA`, `HTTP`, `t/test_crm_du_an_ban.py` | DTO/service/route một Lưu; lỗi theo ô, tạo mới không lý do, sửa bắt một ghi chú; hồi quy HTTP cũ. Sau 1. |
| 3 DA-B3 | `k2/sql_crm_du_an_mot_luot.py`, `PG`, `t/test_crm_du_an_mot_luot_pg.py` | Append constant/migration mẫu dự án, copy snapshot và nguồn/version, remap mốc, bỏ dữ liệu loại trừ. Sau 1. |
| 4 DA-B4 | `DA`, `HTTP`, `t/test_crm_du_an_ban.py` | API Lưu làm mẫu/Từ mẫu/Từ dự án khác, nguồn ngoài phạm vi bị chặn. Sau 2–3. |
| 5 TEN-B1 | `k2/sql_crm_ten_hien_thi.py` (mới), `PG`, `t/test_crm_ten_hien_thi_pg.py` (mới) | Tên G1 Unicode tách mã sinh; đọc G7 tự resolve chuẩn, giữ bản cũ. Kiểm mã ổn định/replay, không sửa SQL cũ. |
| 6 TEN-B2 | `MAU`, `HTTP`, `t/test_crm_41_02_http.py` | G1 nhận tên/chọn mẫu để thêm bản; G7 không đòi gõ giai đoạn, không phá upload/fence/biên nhận. Sau 5. |
| 7 BG-B1 | `k2/sql_crm_thanh_toan.py` (mới), `PG`, `t/test_crm_thanh_toan_pg.py` (mới) | Engine canonical + wrapper kiểm Ký mới; test ví dụ, E, gross, làm tròn, suy %, phiên bản cũ; CD-038: cọc cuối, hai cọc liền nhau, cọc xen giữa, toàn cọc → lỗi. |
| 8 BG-B2 | `GK`, `t/test_crm_giao_ket.py`, `t/test_crm_bao_gia_mac_dinh.py` | Nối engine mới, cờ cọc, snapshot thuế/đất, DA-3a và toàn bộ đường Soạn; test adapter/legacy và mapping tổng. Sau 1,7. |
| 9 DA-U1 | `JS`, `t/crm_du_an_ban_async.cjs`, `giao_dien/assets/style.css` | Trang sáu khối + Enter phí + paste lô + %/mốc, một Lưu/ghi chú chung, bỏ giai đoạn; giữ nháp/lỗi/fence. Sau 2. |
| 10 DA-U2 | `JS`, `t/crm_du_an_ban_async.cjs` | Copy/Từ mẫu/Lưu làm mẫu, kiểm các trường loại trừ và sửa tiếp trước Lưu. Sau 4,9. |
| 11 TEN-U | `JS`, `t/crm_du_an_ban_async.cjs`, `t/crm_giao_ket_async.cjs` | Tên G1, bỏ mọi ô gõ giai đoạn ở G7/Báo giá; chọn nhãn mốc có dấu gửi mã. Sau 6,9. |
| 12 BG-U | `JS`, `t/crm_giao_ket_async.cjs`, `giao_dien/assets/style.css` | BG-25…28; chọn dự án gọi DA-3a, nạp %/mốc/cọc; sáu cột cả Báo giá/Soạn. Sau 8,11. |
| 13 BG-IN | `GK`, `nguon/crm_docx.py`, `t/test_crm_giao_ket.py` | Dữ liệu in và renderer sáu cột/tổng gross/bằng chữ; DOCX test không Word COM. Sau 8. |
| 14 NGHIEM-THU | `t/test_crm_thanh_toan_pg.py`, `t/test_crm_du_an_mot_luot_pg.py`, `CHANGELOG.md` | Hồi quy liên màn bằng dữ liệu giả + kết quả đo trước/sau thực tế. Sau tất cả; lead thử DEMO/in trong phiên được phép. |

Các đường dẫn rút gọn ở lát 9/12/13 đều dưới `src/kho_tri_thuc/`. **Tệp chung cần khóa tuần tự:** `JS` (9→10→11→12), `HTTP` (2→4→6), `PG` (1→3→5→7, cấp số theo lúc gộp), `GK` (8→13), `style.css` (9→12); test chung cũng nối tiếp. `giao_dien/server.py:972` đã chuyển toàn bộ route CRM qua `HTTP`, **dùng chung nhưng dự kiến không sửa**; không tách thêm route tại server. Backend tương ứng phải qua test trước UI; chưa bật luồng mới khi engine/snapshot chưa hoàn chỉnh.

## 6. Kịch bản Anh thử trên DEMO 8798 và số đo

Chỉ chạy sau khi lead gộp/chuẩn bị DEMO; worker này không mở server/PG. Dùng dự án và báo giá **giả** để thử.

1. **CD-022:** Dự án đang bán → Thêm → khối Mốc: nhập “Cấp giấy CN Đầu tư”, tên tắt “CNĐT”, ngày dự kiến hợp lệ → Tiến độ: nhập nhanh `10%, 30%, 40%, 20%`, chọn mốc cơ bản/riêng cho bốn dòng → thấy Σ100%, không ô giai đoạn/tiền/Lý do → Lưu. Mở lại → Sửa một dòng tiến độ: hiện **một Ghi chú thay đổi**; bỏ trống bị chặn đúng ô, điền rồi Lưu → Lịch sử có ai/lúc/cũ → mới. Sửa tên phí/mốc có dấu được. Chỉnh dự kiến đã qua chưa thực tế: một việc chờ, chưa tính quá hạn; ghi thực tế thì hạn được tính theo CD-007.
2. **CD-023:** Thêm dự án KCN giả → nhập chung/giá/thuế, ba phí (Enter thêm dòng), bốn mốc và lịch bốn đợt trên cùng trang; dán ít nhất hai lô từ Excel → một Lưu, một phiên bản tổng. Sửa nhiều khối chỉ hỏi một ghi chú. Mở dự án này → **Lưu làm mẫu**, đặt tên → Thêm → **Từ mẫu**, sửa rồi Lưu. Lặp **Sao chép từ dự án khác** → chọn nguồn: đủ mọi khối được copy, không mang lô/tên/mã/ngày thực tế; lịch trỏ mốc mới đúng; nhật ký ghi nguồn X phiên bản n. Lưu thêm mẫu Nhà ở/Cho thuê do người dùng tự khai, kiểm không có nội dung ép sẵn.
3. **CD-024 + CD-038 câu 2B:** Báo giá → nút **+ Báo giá mới** cạnh tiêu đề → N=1.000.000.000 VND, VAT10%, lịch10/30/60%, dòng1 Đặt cọc → số lớn1.100.000.000; net/VAT/bằng chữ đúng; tiền100/340/660 triệu, VAT0/40/60 triệu, ba tổng khớp. Gõ340 triệu ở dòng2 vẫn suy30%. Thử đủ ba ca tại §4: cọc cuối30/50/20%, hai cọc liền20/30/50%, cọc xen10/30/20/40%; đối chiếu đúng từng dòng và tổng, thử toàn cọc phải báo lỗi. Chọn dự án đã khai: tự nạp %/mốc, quy tắc VAT như lịch tự nhập. In sơ bộ → đủ sáu cột; điền khách/phí hợp lệ → Chuyển sang Soạn → đối chiếu nguyên lịch/cọc/thuế/tổng; mở lại không đổi tiền. Thử thêm E=200 triệu và ca làm tròn ở §4.

**Đo CD-023 mục 5:** đo cùng dự án nguồn kế toán đã tồn tại, bắt đầu tại danh sách Dự án đang bán; chưa tính lô (đo paste riêng). Chỉ số chính C = số bấm nút lệnh, D = số modal/dialog thực mở; thêm F = số lượt mở form và S = số Lưu/POST. Dùng Tab/Enter để nhập/chọn dữ liệu, không tính click focus, không tính thao tác cửa sổ hệ điều hành. Ghi thêm C-toàn-bộ nếu Anh nhập bằng chuột, không trộn hai định nghĩa.

| Chỉ số | Trước: suy tĩnh từ HEAD, chưa đo DEMO | Sau: mục tiêu, chưa nghiệm thu |
|---|---|---|
| C | **20** = bật bán (mở+Lưu)2 + phí (mở+3 Thêm dòng+Lưu)5 + 4 mốc (mở+Lưu)8 + tiến độ (mở+3 Thêm đợt+Lưu)5 | **3** = Thêm + Áp dụng nhập nhanh lịch + Lưu; phí/mốc Enter, sáu khối mở sẵn lúc tạo |
| F / S | **7 / 7** = thông tin + phí + 4 mốc + tiến độ | **1 / 1** |
| D | **0**: `JS:534`, `JS:657` dùng section cho các form trên, không dialog | **0**; không tuyên bố giảm hộp thoại từ 7 xuống 0 |

Số trước giả định khai giai đoạn ASCII hợp lệ ngay lúc bật bán; nếu gõ tên có dấu như lỗi Anh gặp thì luồng bị chặn, không có số hoàn thành để so. Sau là tiêu chí thiết kế cần xác nhận bằng thao tác thật; nếu khối gấp mặc định thì cộng đúng số lần mở. Lát NGHIEM-THU ghi `CHANGELOG.md`: HEAD trước/sau, cùng fixture, C/D/F/S đo thật, chênh lệch và cách nhập; không thay số đo bằng mục tiêu.

## 7. Kiểm tra và Cần lead

Test hiện có để dùng lại: `test_crm_du_an_ban.py` (chuẩn hóa/service/HTTP/CAS), `test_crm_du_an_ban_pg.py`, `test_crm_du_an_moc*.py` (mốc/ngày/diff), `test_crm_bao_gia_mac_dinh.py`, `test_crm_moc_du_an_bao_gia.py`, `test_bg1_o_thong_minh_tinh.py`, `test_crm_giao_ket.py`/`_http.py`, hai bộ node async. **Lưu ý fixture:** `test_crm_du_an_ban_pg.py:3` đang yêu cầu DEMO có sẵn, còn `test_crm_du_an_moc_pg.py:148` dùng kết nối admin. Không dùng các cách này làm bằng chứng mới thay cho test `kho_test_*` chạy vai ứng dụng thật. Test mới tự tạo DB riêng bằng cơ chế chuẩn, chỉ dùng quyền setup cho DDL/fixture; ca nghiệp vụ qua session/quyền/cổng tin cậy đúng runtime, kiểm quyền bằng app role thật, không đóng giả bằng admin. Giữ tệp dưới guard, không cleanup xóa; dữ liệu giả đúng trigger, không mở DEMO.

Đã chạy node Dự án: **44/44 nhóm đạt**; node Báo giá/Soạn: **tất cả ca đạt, exit 0** (script không in tổng số ca). Python không có trong PATH: **NOT_RUN**; PG **NOT_RUN** (handoff cấm mở), không kết luận xanh toàn nền `NEN-TEST.md`. Không sửa mã nên chưa phát hiện lỗi mới trong hai bộ node đã chạy. Kiểm bổ sung cần có: lưu lượt lỗi ở dòng cuối rollback toàn bộ; hai người sửa CAS; replay không thêm bản; copy remap mốc và chặn nguồn ngoài phạm vi; tổng100%; cọc đổi dòng; VAT0/E/NET/GROSS/USD→VND/làm tròn/suy tiền→%; in/Soạn/Ký cùng engine và bản cũ bất biến.

**Cần lead (không bàn lại CD đã chốt):**

- Cấp số migration khi giao các lát backend; bổ sung nguyên văn CD-019 nếu có ràng buộc ngoài “một engine” trong handoff. Phương án SQL ở §4 là đề xuất kiến trúc để lead duyệt, chưa phải mã đã đổi.
- VAT cọc đã chốt CD-038 câu 2B: giao các ca ở §4, không còn chờ quyết định cọc cuối/nhiều cọc; lịch toàn cọc phải lỗi. Đồng bộ BG-27 TL45 do lead thực hiện ngoài phạm vi bốn tệp của lát tài liệu này.
- Khi nguồn dữ liệu cũ có nhiều G7 và không có `giai_doan_g7` mặc định: cần lead chỉ định quy tắc chuyển tham chiếu, không tự đoán.
- `JS:562` hiện chỉ chọn dự án kế toán đã tồn tại để bật bán; chưa có ô tạo tên/mã danh mục gốc. Kế hoạch giữ luồng này. Nếu “tạo dự án mới” trong CD-023 bao gồm tạo luôn `master.du_an` thì cần lead giao thêm luồng/quyền danh mục gốc trước coding; không tự mở rộng. Copy/mẫu cũng chỉ lấy nguồn trong phạm vi quyền hiện hành.

CD-038 (30/10): đã áp BG-27 câu 2B, bỏ ràng buộc cọc dòng 1; cập nhật dồn VAT sau/trước, bất biến/suy ngược, ba ca kiểm cọc cuối/liền nhau/xen giữa và lỗi toàn cọc; lịch giá bán 100%, phí riêng theo câu 1A.
