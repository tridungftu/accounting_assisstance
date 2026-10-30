**Biên bản review chéo G1c · SDK — 30/10/2026**  
**Kết luận: Cần sửa — 1 Chặn, 4 Cần sửa.**

Quy ước: `S` = `docs/47-core/g1/DAC-TA-SDK.md`; `D` = `docs/47-core/g1/CONTRACT-DU-LIEU.md`; `A` = `docs/47-core/g1/DAC-TA-API.md`; `H/`, `K/`, `N/`, `J/` lần lượt thuộc `src/kho_tri_thuc/{ha_tang,k2,nguon,giao_dien/assets}/`.

| Phát hiện và yêu cầu sửa | Mức | Căn cứ |
|---|---|---|
| **Chưa tiếp thu cơ chế chống trùng `/module/*` theo RV-G1B C1.** Giữ khóa ở frontend và không xóa biên nhận khi tắt module chưa đủ. Phải quy định module/SDK giữ biên nhận **vĩnh viễn, cùng transaction nghiệp vụ**; Core chỉ khóa request đang chạy; fingerprint theo operation + body chuẩn hóa, không theo đường dẫn; replay kiểm quyền hiện tại. Bổ sung ca kiểm crash sau commit trước response, restart, replay sau 24 giờ và route cũ/v1 dùng chung biên nhận. | **Chặn** | `S:118`, `S:343`; `D:1400` chỉ dẫn chung sang API, trong khi `A:101`, `A:103`, `A:108` vẫn chứa thiết kế bị bác. Yêu cầu sửa rõ tại `docs/47-core/g1/RV-G1B-OPUS.md:31`. |
| **Bộ kiểm tham chiếu schema manifest chưa được cung cấp.** SDK có hai JSON mẫu nhưng chưa có schema chính thức cho `module.json` và engine manifest. Cần bổ sung schema/version và quy tắc trường bắt buộc, enum, tham chiếu; kiểm cả hai mẫu cùng các ca âm. | Cần sửa | `S:147`, `S:280`; `D:1330` giao phiếu SDK cung cấp schema; `D:1402` lại yêu cầu kiểm theo schema đó. |
| **Operation việc lâu khai sai schema response.** `nhan_dang` khai `dau_ra: "viec.v1"` — đây là schema polling, bắt buộc `id`, pháp nhân, thời điểm… Response 202 lại cần `viec_id`, trạng thái, request ID. Đổi sang `urn:ktt:contract:viec.v1#/$defs/da_nhan` hoặc định danh tương đương được đăng ký. | Cần sửa | `S:201`; `D:1194`, `D:1237`, `D:1274`; `A:123`. |
| **Schema lỗi chưa tiếp thu chi tiết lỗi trường an toàn.** `additionalProperties: false` và bốn trường hiện tại sẽ bác `chi_tiet`; SDK bảng nhập liệu thiếu contract để gắn lỗi server vào từng ô. Đồng bộ với API: `chi_tiet` tùy chọn gồm `{truong, ma}`, không chứa giá trị; mã lỗi module phải đăng ký. | Cần sửa | `D:1151`, `S:127`; `docs/47-core/g1/RV-G1B-OPUS.md:16`. |
| **Câu chọn module đầu tiên hỏi lại điều đã chốt.** Chuyển M4 thành dòng thông báo; nếu cần chọn thì hỏi phạm vi luồng M4. Câu snapshot OCR có phương án và khuyến nghị nhưng phần retention cần gộp về phiếu CSDL, tránh hỏi hai lần. | Cần sửa | `S:349`, `S:350`; CD-027 tại `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:320`; `docs/47-core/g1/DAC-TA-CSDL.md:408`; `docs/47-core/g1/RV-G1B-OPUS.md:22`. |

**Độ đầy đủ và tính nhất quán**

- **Đủ vị trí 6/6 mục G1c-1 và 2/2 mục G1c-2.** Có 11 dịch vụ Python, khung tiến trình, JS SDK, hai manifest, vòng đời gói, bảng chọn; bảy contract cộng hai contract API và bộ kiểm. Các mục manifest, câu chọn và chống trùng chưa khép như bảng trên.
- **Khớp CSDL vòng 2** về mã phiên bí mật/ủy nhiệm, engine không login CSDL, đọc qua `cong_bo_*`, migration theo gói: `S:57`, `S:93`, `S:97`, `S:335`; đối chiếu `DAC-TA-CSDL.md:135`, `:262`, `:269`, `:396`.
- **Khớp CD-028** về Core cấp cổng, chuyển giao listener, readiness, drain, mặc định tự kích hoạt/tự đóng và chỉ Admin áp dụng đề xuất: `S:75`, `S:77`, `S:79`, `S:101`, `S:105`.
- **Bộ kiểm:** KT01–KT16 đều có cách làm và mức chặn; các test dẫn kiểm mẫu tồn tại, phù hợp mục đích. Tài liệu phân biệt đúng kiểm metadata cũ với kiểm runtime bổ sung. Tuy nhiên KT05 thiếu các ca biên nhận nêu trên, KT07 phụ thuộc schema còn thiếu.

**Kiểm mẫu mã hiện có — 15/15 khẳng định đúng**

| # | Khẳng định đã đối chiếu | Tệp:dòng thực tế |
|---|---|---|
| 1 | `Engine.chay` kiểm kiểu, không cho sửa input, tạo bằng chứng | `H/engine.py:165` |
| 2 | Danh bạ tra đúng version, không fallback | `H/danh_ba_engine.py:33` |
| 3 | `EngineOCR` dùng cổng được tiêm, trả DOCX bytes | `H/engine_cong.py:127` |
| 4 | `EngineAI` dùng `CongAI` được tiêm | `H/engine_cong.py:154` |
| 5 | Tạo việc/dedupe không tự commit | `H/hang_viec.py:21` |
| 6 | Nhận tối đa một việc, giữ token lease | `H/hang_viec.py:31` |
| 7 | Bus phát trong transaction, có dedupe | `H/bus_su_kien.py:30` |
| 8 | ACK cùng transaction nghiệp vụ; ACK lặp trả `False` | `H/bus_su_kien.py:64` |
| 9 | `KhaiBaoVungDuLieu` có V1–V4 | `H/khai_bao_module.py:144` |
| 10 | Bộ kiểm vùng hiện chỉ kiểm bản khai/điểm được truyền | `H/khai_bao_module.py:225` |
| 11 | Công tắc kiểm cùng transaction, vẫn phải kiểm MTQ | `K/module.py:62` |
| 12 | Host #6 có Windows Job, bắt tay và kiểm readiness | `N/trich6_host.py:240` |
| 13 | Host #6 hiện để con bind cổng ngẫu nhiên | `N/trich6_host.py:607` |
| 14 | Migration có transaction/checksum, chặn hạ phiên bản | `H/postgres.py:217` |
| 15 | `parseMoney` xử lý chuỗi tiền nguyên; cần mở rộng decimal | `J/ma_tran_tham_quyen.js:26` |

**JSON Schema và tỉ lệ đúng**

- **22/22 khối JSON parse được** bằng `JSON.parse`: hai manifest, mười schema và mười ví dụ.
- **10/10 ví dụ khớp cấu trúc khi đối chiếu thủ công** từng trường bắt buộc, gồm trường lồng nhau và phần kế thừa; biên nhận được đối chiếu riêng với `$defs/da_nhan`.
- Mười schema khai draft **2020-12**, `$id` riêng và phiên bản; tiền chuẩn là chuỗi decimal kèm đơn vị. Không thấy trường credential, khóa hoặc mật khẩu trong contract dữ liệu. Decimal XML nguồn được tách khỏi tiền chuẩn.
- **Tỉ lệ đúng kiểm mẫu mã: 100% (15/15)**; tỷ lệ này không thay thế kết luận nghiệm thu toàn bộ đặc tả.

Chỉ đọc và kiểm tĩnh; không sửa tệp, không truy cập kho thật, tệp bí mật hoặc `*.local.json`; không chạy test/runtime hay validator meta-schema.