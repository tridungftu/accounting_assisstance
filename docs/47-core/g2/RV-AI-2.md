**Biên bản review chéo AI-2 — Kết luận: Cần sửa**

Nhánh `lat/g3-ai-2`, HEAD `d0e19d7`; đối chiếu `hop-nhat-20261023...HEAD`.

Các trọng tâm:

- **Đạt:** `chi_cuc_bo=true` đặt `cloud_bat=False` trên instance riêng; giữ nguyên instance chung. Test kiểm 0 Cloud khi Local lỗi, không chắc và kiểm xác suất: `hoi.py:84–92`; `tests/test_g3_ai_2.py:120–145`.
- **Đạt:** test hai request xen kẽ kiểm kết quả, số lời gọi Cloud và cấu hình chung; `false` không tự bật Cloud toàn cục: `tests/test_g3_ai_2.py:147–181`.
- **Đạt:** bọc `CongAI.goi`, không viết client/bộ che mới, không thêm đường gọi trực tiếp `api.anthropic/openai`: `hoi.py:92`. Test tiêm Local/Cloud/Mask giả và chặn socket: `tests/test_g3_ai_2.py:93–110`.
- **Đạt qua đối chiếu tĩnh:** manifest chỉ khai `ai.hoi@1`, đúng cặp contract, `headless=true`, phù hợp schema G2-17b: `engine.json:9–28`; test tại `tests/test_g3_ai_2.py:284`.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Adapter bác dẫn chứng hợp lệ sau chuẩn hóa.** Ví dụ `van_ban="Lãi suất DEMO\n8%/năm."`, Local trả giá trị `8%/năm` và trích dẫn cùng nội dung. `CongAI.danh_gia` gộp khoảng trắng thành `"Lãi suất DEMO 8%/năm."` và chấp nhận; adapter tìm chuỗi này trong văn bản thô rồi ném `ValueError`, khiến toàn bộ request thất bại. Vi phạm yêu cầu giữ thuật toán/đường cũ tại `GIAO-ENGINE-1.md:152` và mục B.4 của mẫu review. Cần giữ cùng quy tắc kiểm dẫn chứng của cổng gốc và bổ sung regression test qua adapter cho xuống dòng/khoảng trắng. Fixture AI-2 hiện chỉ có một dòng nên chưa bắt lỗi này. | **Chặn** | `src/kho_tri_thuc/engines/e_hoi_ai/hoi.py:100`; `tests/test_g3_ai_2.py:28` |

Đối chiếu năm nhóm kiểm:

1. **Phạm vi — Đạt:** đúng 3 tệp whitelist, đều là tệp thêm mới; không xóa tệp.
2. **Yêu cầu — Cần sửa:** cơ chế chỉ Local đạt; bước chuyển kết quả có regression nêu trên.
3. **Chuẩn/quyền — Không phát hiện vi phạm:** tên trường mới không dấu; không thêm SQL, quyền, RLS, DEFINER hay `search_path`. Ca login CSDL thật không áp dụng.
4. **An toàn/dùng lại — Đạt trong diff:** dùng cổng và DTO gốc; không đọc kho thật, tệp bí mật; không thêm log chứa khóa/DSN.
5. **Test — Cần bổ sung:** các assertion kiểm đúng cơ chế chỉ Local; ca M9 được ghi rõ là mẫu giả, không thay bằng chứng grep M9 thật.

**Kiểm chứng:** review tĩnh, không sửa tệp hoặc chạy dịch vụ. Không chạy lại test; số liệu AI-2 **15/15**, AI-1b **13/13**, AI-4a **13/13**, G2-17 **28/28** là kết quả lead cung cấp.

**Hỏi Claude:** xác nhận điểm Chặn tại `hoi.py:100` trước khi giao sửa; căn cứ bổ sung là quy tắc chuẩn hóa tại `cong_ai.py:800,871` và test gốc `tests/test_cong_ai.py:277`.