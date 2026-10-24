# Kho tri thức — M1–M6, v0.3.0

## V11 (11/10/2026) — sửa cách tạo tri thức theo 5 case T8

- Vân tay diễn giải, gộp dòng 112 (chứng từ có VAT), quy tắc từ khóa ghép sống lại, quy tắc yếu không chặn tri thức sổ, nhận diện đối tượng theo tên (viết tắt CT/CTCP…), chặn ánh xạ STK sai, nhiều lần chuyển = 1 chứng từ, công nợ mở làm căn cứ TK, khóa số khế ước.
- Màn hình: "Vì sao" có số đo (n/n chứng từ), chip đối tượng/TK gợi ý, **Ghi chú cho AI → gói ngữ cảnh gửi Claude** (`var\web-that\ghi-chu-ai\MOI-NHAT.md`), **Chế độ chấm điểm** + nút **So với Junsky** (`SO-VOI-JUNSKY.xlsx`).
- Chạy lại T8 (học đến 30/06): dòng sai TK/đối tượng 44 → 10; Xanh 41 dòng, đúng 35/36 TK và 27/27 đối tượng. 240/240 test. Chi tiết: `docs/BAO-CAO-V11.md`, hướng dẫn: `docs/HUONG-DAN-DINH-KHOAN.md`.

## V10 (03/10/2026) — giao diện Định khoản bản Claude Design

- **Dùng thật**: bấm đúp **MỞ PHẦN MỀM.cmd** (cổng 8766). **Chạy thử tháng 8**, máy học đến 30/06: bấm đúp **MỞ PHẦN MỀM THỬ T8.cmd** (cổng 8767).
- Trên màn hình Định khoản: thả sao kê → duyệt từng giao dịch (Đồng ý / Sửa / Bỏ qua) → xuất **File soát (Excel)**. File nhập Junsky đang khóa.
- Tài liệu:
  - [Hướng dẫn dùng](docs/HUONG-DAN-DINH-KHOAN.md)
  - [Báo cáo V10](docs/BAO-CAO-V10.md)
  - [Bản bàn giao thiết kế](docs/thiet-ke/BAN-GIAO-dinh-khoan.md)
- Sao lưu trước khi nâng cấp: `var/sao-luu-truoc-V10-20261003/`.
- GitHub (repo riêng tư) chỉ chứa mã nguồn và tài liệu. Dữ liệu thật (`var/`, các file Excel, ảnh chụp) bị chặn bởi `.gitignore`.


**Đã có giao diện HTML vận hành cục bộ.** Nhấp đúp **MỞ PHẦN MỀM.cmd** để mở kho `that` PLHN tại `http://127.0.0.1:8766`; không cần ChatGPT, tài khoản AI hay Internet. Bản giả lập cũ ở **MỞ BẢN DEMO.cmd**.

Giao diện nhận và giữ nguyên file thật, chống trùng ở mức hồ sơ, tìm kiếm và tải lại bản gốc. Trạng thái **Đã nhận — chờ bộ đọc** chưa phải dữ liệu đã chuẩn hóa/hạch toán. Khu **Thử dữ liệu mẫu** dùng SQLite mô phỏng riêng; không tự đổi file thật thành fixture. Phạm vi này được Anh duyệt theo A09; [báo cáo kiểm thử giao diện](docs/BAO-CAO-KIEM-THU-GIAO-DIEN.md).

Một ứng dụng Python, SQLite và Excel chạy offline. Đã có luồng **nạp nguồn → tri thức có duyệt → đề xuất sao kê → duyệt Excel → xuất batch → xác minh → nhãn học → kiểm chứng** trên dữ liệu giả lập.

**Bàn giao có kho `that` để đọc nguồn và duyệt nội bộ; chưa có quyền nhập Junsky.** File shadow chỉ kiểm cấu trúc, không dùng import Junsky. Các điểm cần kế toán xác nhận còn ghi trong [QUYET-DINH.md](docs/QUYET-DINH.md).

- [Báo cáo kiểm thử M1–M6](docs/BAO-CAO-KIEM-THU-M1-M6.md).
- [Tiến độ đúng sáu module](docs/TIEN-DO.md).
- [Hướng dẫn chạy, duyệt Excel và phục hồi](docs/HUONG-DAN-VAN-HANH.md).
- [Hợp đồng dữ liệu](docs/HOP-DONG-DU-LIEU.md).

## Chạy trên máy hiện tại

Mở kho thật bằng nhấp đúp [MỞ PHẦN MỀM.cmd](MỞ%20PHẦN%20MỀM.cmd), hoặc bằng PowerShell:

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\start-web.ps1 -ConfigPath '.\cau_hinh.that.toml' -DataRoot '.\var\web-that'
```

Không mở trực tiếp `index.html`. Python phải chạy để lưu file. Đóng tab không dừng server; nút **Dừng ứng dụng** dừng server, giữ nguyên hồ sơ. Mở lại launcher sẽ tiếp tục dùng kho cũ. Hồ sơ thật ở `var/web/ho-so-goc`; mô phỏng giao diện ở `var/web/mo-phong`. Sao lưu hồ sơ thật theo hướng dẫn giao diện, riêng với backup SQLite bên dưới.

Cần Python 3.11+ và openpyxl 3.1.x. Máy bàn giao có Python 3.12.14 và openpyxl 3.1.5 trong runtime đóng gói; không cài thêm hoặc tải dữ liệu từ mạng. `run.ps1` tìm Python trên PATH hoặc runtime này; `-PythonExecutable` cho phép chỉ rõ đường dẫn. Khi chuyển máy cần chuẩn bị dependency offline trước; setuptools chỉ dùng nếu đóng gói.

Chạy toàn bộ kiểm thử tự động, không cần Anh thao tác Excel:

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\test.ps1
```

Kết quả chi tiết ở `var/test-results/latest.json`. Tests tạo kho tạm riêng, không sửa kho demo hay dữ liệu thực. Có bài thử kết thúc đột ngột tiến trình Python con do chính test tạo.

Chạy demo hai phiên vào một thư mục mới:

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
$kttDemo = Join-Path 'var' ('demo-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
.\run.ps1 demo-full $kttDemo
Get-Content -LiteralPath (Join-Path $kttDemo 'reports\SUMMARY.json') -Encoding UTF8
```

Demo tự sinh dữ liệu, duyệt và mô phỏng sổ nhập lại. Người duyệt có tên `AUTOMATED_FIXTURE_*`; đây không phải kế toán trưởng đã duyệt hoặc Junsky đã nhận file. Các mốc thời gian là giả lập, gồm cả cuối tháng tương lai.

Kết quả bàn giao: `var/full-demo-final-v2/reports/SUMMARY.json`. Hai khoản chi 100 + 100, công nợ 200 → 100 → 0, hai phiên đóng, hai nhãn sau xác minh, chốt tháng fixture và restore. Độ đúng trên hai dòng giả lập không đại diện PLHN.

## Sáu module

| Module | Chức năng |
|---|---|
| M1 — Nền tảng và dữ liệu | TOML, raw/staging/evidence, chống trùng, migration, năm nhóm nguồn JSON fixture, Base fixture, backup/restore; tiếp nhận file gốc chờ bộ đọc |
| M2 — Kho tri thức | Năm nhóm; version/hiệu lực/known_at; Excel chờ duyệt; duyệt/thu hồi; định danh; LINK_A/B/C và E2 fixture |
| M3 — Phiên và đề xuất | Một phiên hoạt động; cổng nguồn/danh mục; giữ chỗ atomic; phân bổ M:N; năm bước, đầy đủ/một phần/không |
| M4 — Duyệt và xuất | Excel duyệt từng chứng từ; sửa có lý do/revision; batch nội bộ, cân Nợ/Có, hash/manifest, crash/recovery; chặn Junsky thật |
| M5 — Đối soát và học | RECON_A/B/C/chưa rõ; chứng cứ từng trường/HĐ; kỳ vọng cộng dồn; nhãn lịch sử/vận hành, thu hồi/thay thế, thống kê lượng/tiền; đề cử |
| M6 — Kiểm chứng và vận hành | Dataset version, DEV/HOLDOUT/BLIND, A/B đúng cutoff; tác động quy tắc; mẫu mù; dựng công nợ từ neo quá khứ; chốt tháng fixture; báo cáo/demo; giao diện HTML cục bộ |

Schema SQLite v8 nâng tiếp từ v1/v2, giữ checksum migration cũ. Fixture/shadow/backtest không dùng chung kho; mọi mode hiện vẫn chỉ nhận giả lập. Có audit actor/thời điểm nhưng chưa có hệ đăng nhập/xác thực chữ ký kế toán.

## Lệnh nền tảng

Tùy chọn `--config`, `--data-dir` đặt trước tên lệnh. `COMMITTED` chỉ là nguồn đã nạp, không phải ghi sổ.

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\run.ps1 catalog
.\run.ps1 --data-dir var/thu-m1 init
.\run.ps1 --data-dir var/thu-m1 validate tests/fixtures/sao_ke.json
.\run.ps1 --data-dir var/thu-m1 ingest tests/fixtures/sao_ke.json
.\run.ps1 --data-dir var/thu-m1 ingest tests/fixtures/sao_ke.json
.\run.ps1 --data-dir var/thu-m1 status
```

Lần nạp thứ hai tạo 0 giao dịch mới. Hai giao dịch cùng ngày/tiền nhưng khác tham chiếu vẫn riêng biệt. Các lệnh `report`, `scan-base`, `check-bundle`, `backup`, `verify-backup`, `restore` tiếp tục được hỗ trợ. `status` có thêm trạng thái phiên/batch/đề xuất/nhãn/tháng.

M2–M6 dùng `workflow <action> <request.json> [--output result.json]`; request có actor, thời điểm, ID và tham số. Danh sách tham số ở [hướng dẫn vận hành](docs/HUONG-DAN-VAN-HANH.md).

## Backup/restore

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
$kttSuffix = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$kttBackup = Join-Path 'var' ('backup-' + $kttSuffix)
$kttRestored = Join-Path 'var' ('restored-' + $kttSuffix)
.\run.ps1 --data-dir var/full-demo-final-v2/data backup $kttBackup
.\run.ps1 verify-backup $kttBackup
.\run.ps1 restore $kttBackup $kttRestored
.\run.ps1 --data-dir $kttRestored status
```

Đích phải chưa tồn tại. Backup gồm DB nhất quán, config trong DB và raw được tham chiếu, kể cả workbook duyệt, file sửa, batch, manifest và dataset. Sau restore, `batch-recover` tái dựng file xuất nguyên byte/ID từ artifact, không sinh lại quyết định. Tài liệu rời và log test ngoài kho không nằm trong backup DB.

Mã thoát: 0 thực hiện lệnh thành công; 2 sai dữ liệu/thiếu điều kiện; 3 lỗi I/O/SQLite. Đối soát/đánh giá có thể trả 0 khi tạo báo cáo thành công nhưng `complete=false` hoặc `candidate_gate_passed=false`; phải đọc kết quả nghiệp vụ.

## Phần phải chờ mẫu thực

Sao kê/PDF, XML/bảng kê, Base, bộ Junsky và sổ chi tiết; Entry1/2 + EntryID/DebtID; từ điển/28 mã/10–15 mẫu sao kê; ba chỉ số từ khóa, bảy mã lý do, sáu phần báo cáo gốc; lịch sử/known_at, tập vàng độc lập, người ký và ngưỡng chất lượng. Không tự đặt mapping thật, thông số kế toán hoặc quyền vận hành từ fixture. Bốn tài liệu gốc giữ nguyên; script khảo sát bản 1.2 vẫn chưa được cung cấp.
