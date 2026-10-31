**Biên bản review chéo AI-5a — Kết luận: Cần sửa**

Nhánh `lat/g3-ai-5a`, HEAD `cadb80c`, commit triển khai `96a4bec`; đối chiếu với `hop-nhat-20261023`.

**Các câu trọng tâm**

- **Bọc mã hiện có: Đạt.** Hiện thực giao diện `BoGhiNhatKy`, dùng lại `BoGhiBoNho.thong_ke`; không viết lại thuật toán — `nhat_ky.py:119`.
- **Metadata qua SDK Core: Đạt ở mức adapter.** Đọc qua `doc_dau_vao`/`mo_doc`, ghi qua `ghi_ket_qua`, chờ ACK — `nhat_ky.py:73,106,125`.
- **Sống qua restart: Chưa đạt đầy đủ.** Test chứng minh lịch sử **đã bàn giao** tồn tại qua tiến trình mới trên Core giả SQLite (`test_g3_ai_5a.py:204`); hai đường lỗi bên dưới vẫn làm mất bản ghi.
- **Không lộ văn bản/bí mật:** Không thấy ghi prompt, câu trả lời hoặc DSN trong diff. Test canary đường Local tại `test_g3_ai_5a.py:285` kiểm đúng nội dung này.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Lỗi đọc snapshot làm mất bản ghi nhưng vẫn báo đã bàn giao.** `ghi()` gọi `_snapshot()` trước khi gán `__cho`. Khi Core lỗi đọc hoặc trả thiếu metadata, `CongAI._ghi()` bắt lỗi rồi tiếp tục; `__cho` vẫn `None`, nên `da_ban_giao()` trả `True`, `thu_lai()` không làm gì. Engine có thể tự đóng dù metadata chưa được lưu. Vi phạm AI-5a: thống kê/kiểm xác suất không mất khi tự đóng. | **Chặn** | [nhat_ky.py:91](</D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-g3-ai-5a/src/kho_tri_thuc/engines/e_hoi_ai/nhat_ky.py:91>) |
| **Bản ghi tiếp theo bị bỏ khi bản trước đang chờ ACK.** Ví dụ lượt Local chưa ACK; `CongAI.goi()` tiếp tục sang Cloud và ghi metadata Cloud. Bộ ghi ném `NHAT_KY_CHO_ACK`; `CongAI._ghi()` nuốt lỗi, bản ghi Cloud không được giữ. Sau khi retry Local thành công, `da_ban_giao()` trả `True` dù thiếu Cloud. Vi phạm yêu cầu lưu metadata và giữ thống kê qua restart. | **Chặn** | [nhat_ky.py:89](</D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-g3-ai-5a/src/kho_tri_thuc/engines/e_hoi_ai/nhat_ky.py:89>) |
| Test retry hiện **mong đợi từ chối bản ghi thứ hai**, nhưng không kiểm việc bản ghi đó bị mất khi dùng qua `CongAI`; cũng thiếu ca lỗi snapshot lúc ghi rồi kiểm drain/restart. Cần bổ sung regression cho hai tình huống trên. | **Cần sửa** | [test_g3_ai_5a.py:235](</D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-g3-ai-5a/tests/test_g3_ai_5a.py:235>) |

**Phạm vi và an toàn:** Đúng 2/2 tệp whitelist. Không có DROP/xóa, SQL chéo module, thay ACL/RLS/DEFINER hoặc mở quyền. SQL chỉ thuộc fixture SQLite DEMO; không có test PG để xác nhận quyền bằng login thật, cũng không có thao tác đóng giả owner.

**Kiểm chứng:** Lead báo **9/9**. Tôi không chạy lại test vì bộ test tạo tệp tạm trong phiên chỉ đọc; chưa xác nhận độc lập lỗi mới so với nền. `git diff --check` đạt; không sửa tệp, không đọc kho thật/tệp bí mật.

**Hỏi Claude trước khi gộp:** Với hai điểm Chặn tại `nhat_ky.py:91` và `:89`, cơ chế nào bảo đảm giữ đủ metadata khi lỗi snapshot hoặc đang chờ ACK? Trong diff hiện tại chưa có cơ chế đó.