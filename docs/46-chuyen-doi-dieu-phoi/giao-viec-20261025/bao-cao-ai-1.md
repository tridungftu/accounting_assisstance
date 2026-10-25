Anh, đã hoàn thành AI-1 trong 3 tệp UTF-8, giữ API hiện có và mặc định tắt.

- Quy tắc tại [ai_cuc_bo.py:32](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-ai-1/src/kho_tri_thuc/tri_thuc/ai_cuc_bo.py:32>): chỉ HTTP tới IP loopback/RFC1918/Tailscale; chặn domain, HTTPS, IP công cộng, link-local và redirect. Tailscale kiểm tra và bind IP nguồn; chặn model cloud/remote qua metadata.
- Đã cập nhật gợi ý/lỗi trên giao diện. Test máy AI giả chứng minh không gọi `getaddrinfo`, không dùng proxy dù có `HTTP_PROXY`, và `choose_counterparty` trả kết quả đúng.
- **Test: 40/40 đạt** — 15 mới, 25 hiện có; không thêm mã lỗi so với nền v4. Chỉ kiểm tra mock/loopback, chưa thử LAN/Tailscale thật.
- Không commit theo chỉ đạo. Thông điệp đề xuất: `[AI-1] Mở Local AI qua LAN/Tailscale với kiểm tra địa chỉ và model`.