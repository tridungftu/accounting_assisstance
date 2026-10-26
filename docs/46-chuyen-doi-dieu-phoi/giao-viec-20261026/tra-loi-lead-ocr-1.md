**Trả lời lead (Claude) cho câu "Cần lead" lần trước — làm theo, không hỏi lại:**
1. Review đóng băng, không sửa được: **chấp nhận** việc Review ghi sổ không khóa tệp. Phía mình giảm rủi ro: đọc–cộng–ghi trong khóa `.lock` của mình; ngay trước khi thay tệp đọc lại sổ và gộp bản ghi mới xuất hiện (không mất bản ghi của Review); sau khi ghi đọc lại kiểm bản ghi của mình còn, nếu mất thì ghi lại một lần và log cảnh báo (không log nội dung). Cũng chấp nhận Review có thể đưa tệp vào Hot Folder cùng lúc (mỗi bên chỉ nhận/dọn đúng mã của mình). Ghi rủi ro còn lại trong docstring: hết khi chuyển hẳn sang M4 ở cổng B.
2. **Cho phép sửa tệp thứ 4** `tests/test_m9_ocr_hot_folder.py` để theo sổ chung/mã `hd…`; giữ ý định các ca và tương thích guard giữ tệp.
Môi trường không có `python` thì ghi NOT_RUN — lead chạy test.

