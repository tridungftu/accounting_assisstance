**BIÊN BẢN REVIEW CHÉO HD-3a — Kết luận: Cần sửa**

Nhánh `lat/g3-hd-3a`, HEAD `6f2a2d5`, commit triển khai `dde876a`; đối chiếu với `hop-nhat-20261023`.

**Các điểm trọng tâm**

- **Node thuộc Job: Đạt.** Launcher không dùng breakaway; test kiểm bằng đúng handle Job của Core và kiểm kết thúc engine/Node: `tests/test_g3_hd_3a.py:306`, `:349`, `:360`.
- **Cổng bị chiếm không dò: Đạt.** Node chỉ bind cổng được cấp, trả `CONG_BI_CHIEM`; có test cho cả cổng adapter và Node: `chay.py:49`, `tests/test_g3_hd_3a.py:428`, `:443`.
- **Manifest: Đạt.** Chỉ khai `hoa_don.doc_xml@1`, không quảng bá tải thật: `engine.json:11`.
- **Giữ kết quả/Node đến ACK: Cần sửa** trường hợp chờ vượt hạn lease, như phát hiện dưới đây.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Không duy trì heartbeat khi đang giữ việc/chờ ACK.** Vòng retry chỉ gọi `ghi_ket_qua` rồi ngủ; không có đường gia hạn lease. Tình huống: lease còn 120 giây, bàn giao liên tục lỗi nhưng heartbeat vẫn có thể hoạt động; sau 120 giây, SDK chặn cục bộ bằng `VIEC_MAT_LEASE`. Kể cả Core phục hồi, retry không tới Core nữa, kết quả không được ACK và drain mắc vô hạn. Vi phạm chuẩn SDK §3.6.4 bước 2 và đặc tả SDK §4.3. Test hiện chỉ kiểm lease đã hết trước xử lý và retry ngắn, chưa phủ trường hợp này. Cần duy trì heartbeat và bổ sung ca kiểm bằng đồng hồ giả trong whitelist hiện có. | **Chặn** | [`src/kho_tri_thuc/engines/e_hoa_don/chay.py:152`](</D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-g3-hd-3a/src/kho_tri_thuc/engines/e_hoa_don/chay.py:152>); `tests/test_g3_hd_3a.py:135`, `:169` |

**Đối chiếu năm nhóm kiểm**

1. **Phạm vi:** Đạt; diff chỉ thêm đúng ba tệp whitelist.
2. **Chuẩn/đặc tả:** Có điểm Chặn trên. Không thêm SQL, role, RLS, DEFINER, `search_path` hoặc quyền CSDL; tên nghiệp vụ mới dùng tiếng Việt không dấu.
3. **An toàn:** Không thấy DROP/xóa tệp, đọc kho thật, gọi dịch vụ ngoài hoặc ghi bí mật/DSN vào log/audit. Test dùng DEMO; không có truy cập PostgreSQL nên kiểm login owner không áp dụng. Tài khoản Windows riêng/ACL thuộc HD-3b.
4. **Dùng lại mã:** Đạt; dùng Bootstrap, SDKEngine, `doc_xml` HD-1, `env_con` và `_doc_dong`; không viết lại parser/tải.
5. **Test:** Các assertion kiểm đúng Job, cổng, readiness và ACK ngắn hạn; thiếu ca gia hạn trong thời gian giữ kết quả.

**Xác minh:** Tôi chỉ đọc, không chạy test hoặc sửa tệp; `git diff --check` đạt. **18/18** là kết quả lead cung cấp; chưa có bằng chứng regression so nền trong lượt review này.

**Hỏi Claude:** Tại `chay.py:152`, có cơ chế heartbeat bên ngoài cập nhật chính `SDKEngine` này không? Diff và SDK hiện có không thể hiện cơ chế đó. Lead cần xử lý điểm Chặn trước khi gộp.