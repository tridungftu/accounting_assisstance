# Tổng hợp token Claude + Codex (CD-025)

Lập 27/10/2026 ~16:00. Chỉ đọc nhật ký; không có dữ liệu nghiệp vụ.

## Codex (`codex exec` do lead gọi)

Nguồn: dòng "tokens used" cuối mỗi nhật ký `codex-*.log` trong thư mục làm việc của phiên lead (381 tệp). Ngày theo thời điểm ghi tệp. Một số lượt chạy lại ghi đè cùng tên tệp, nên số lượt có thể **thấp hơn** thực tế.

| Ngày | Số lượt có số | Token |
|---|---:|---:|
| 24/10 | 16 | 1.460.372 |
| 25/10 | 91 | 8.631.494 |
| 26/10 | 254 | 21.670.400 |
| 27/10 (đến ~16:00) | 16 | 1.444.979 |
| **Cộng** | **377** | **33.207.245** |

- 4 nhật ký không có dòng token: lượt bị ngắt do máy chủ quá tải.
- `USAGE-20261025.md` ghi 25/10 đến 19:20 là 4.662.077 token / 47 lượt; số trên gồm cả phần còn lại của ngày 25.
- Chưa tách theo lát × mức suy luận. Hầu hết lượt dùng `model_reasoning_effort=high`, một số lượt sửa nhỏ dùng `medium`.

## Claude (lead + subagent)

Công cụ chỉ trả **% hạn mức**, không trả số token theo model.

| Thời điểm | 5 giờ | Tuần · mọi model | Tuần · Fable |
|---|---:|---:|---:|
| 26/10 ~14:00 (TRANG-THAI) | — | 88% | — |
| **27/10 ~16:00** | 8% | **100%** (đặt lại 29/10 ~01:00 giờ VN) | 10% |

- **Hạn mức tuần mọi model đã chạm 100%.**
- Từ 27/10 16:00, lead chỉ giữ gate máy và gộp. Review giao hết cho Codex (QD-20261026-04, CD-020 mục 5). **Tạm dừng phần Claude tự đọc khi rút thăm trúng**; ghi "bỏ qua do hạn mức" vào commit.
- Số token theo model của subagent: không có (từ 26/10 không dùng subagent review).
- Anh có thể chạy `/usage` trong terminal Claude Code rồi dán vào đây để có số chi tiết.

## Cập nhật hằng tối (CD-020 mục 5)

| Ngày | Codex token trong ngày | Claude tuần · mọi model |
|---|---:|---:|
| 27/10 (16:00) | 1.444.979 | 100% |
| 30/10 (đầu ngày 10:20) | — (28–29/10 không chạy) | 1% (khung 5 giờ 6%) |
| 30/10 (tối 20:00) | (chưa tổng hợp log Codex) | 7% (khung 5 giờ 4%) |
