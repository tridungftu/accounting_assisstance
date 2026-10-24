# CRM-01 — review parser/source độc lập lượt 02

Ngày 19/10/2026. **25 criterion: 23 đạt, 2 lỗi P1, 0 setup/inconclusive.** 18 source-format accepted được báo riêng; không tính thành workflow pass. CRM chưa nghiệm thu.

Chạy sau CLI51099 terminal exit 0 trên 117 frozen file của `crm02-handoff-20261019-071834-580`; manifest SHA256 `5d85cd7b822c3ae09e0b88d83421309904307a905d29da4f639fc5de933a44f2` khớp trước/sau. Baseline 187 file/44 vector bất biến, manifest `4aa3d06a63eb8a816bb044c0768801909b88837f511fe2f258922ab384db20a4`. Không xác nhận thủ công để làm xanh, không DB/product edit/deletion.

Evidence: `var/codex-dieu-phoi/crm-parser-recheck02/runtime-20261019T001922268457Z/result.json`, SHA256 `2f6274b6f90f9524196400916a388a7db7faaef8eaf968d31d3ef3db15832378`. Parser `crm_phan_tich.py` SHA256 `021ccc8c7cf24cb22bca29ec0a735924e4605513d7357f2d280e65df8f56a422`; adapter SHA256 `1d96e0428a4632c9f9c40a0d1b2b8088908df222c2dc5eb80aebe458239b3a66`.

## Hai lỗi chặn

| Ca | Input DEMO độc lập | Actual | Expected |
|---|---|---|---|
| P1 token số | Raw D1 = `40.000.000 VND`; câu trích đúng Điều/Khoản ghi `140.000.000 đồng`; D2=60m, tổng raw100m | D1 vẫn `CO_CAN_CU`, typed40m; sinh lịch40+60m, blocker rỗng | 40m không có căn cứ từ substring trong140m; giữ chờ, không tự dùng raw40m |
| P1 currency | Raw D1=`1.000.000 VND`; câu trích đúng Điều/Khoản ghi `1.000.000 USD`; D2=99m, tổng raw100m | D1 vẫn `CO_CAN_CU`, typed1mVND; sinh lịch1+99mVND, blocker rỗng | Citation USD không chứng minh amount VND; giữ chờ, không quy đổi/tự relabel |

Hai ca dùng structured source có đúng vị trí và không có blocker không liên quan. Các control dương ISO/VND, raw đơn vị `đồng` với alias khai báo và VND/citation `đồng` đều đạt. Control text phẳng thiếu vị trí giữ manual gate đúng. Vì vậy hai lỗi trên không thể giải thích bằng fixture thiếu vị trí hoặc alias chưa cấu hình.

## Phạm vi đạt và yêu cầu sửa

Các tiêu chí cũ về raw khác citation trực tiếp, `Suy ra`, sai Điều/Khoản, optional rỗng, thay basis/loại nghĩa vụ đã thu và phép tính tiền exact đã qua probe parser tương ứng. Không suy kết quả parser thành repository idempotency, V3/V4, RLS, bằng chứng Word thật hay UI đã đạt.

Sửa theo giá trị có kiểu và token số/currency trong đúng citation, giữ provenance và manual workflow. Không chỉ thêm regex nhận đúng hai ví dụ hoặc bật xác nhận thủ công mặc định. Giữ control amount chính xác, alias tương đương được cấu hình, NULL/0, số lớn, USD scale và locale; ca không chắc phải có lý do giữ chờ. Không thay baseline hoặc expected theo output.
