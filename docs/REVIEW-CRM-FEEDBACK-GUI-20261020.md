# CRM DEMO có giao diện để Anh góp ý — kiểm độc lập 20/10/2026

Trạng thái: **RUNNING_FOR_HUMAN_FEEDBACK**. Bản CRM kế toán về hợp đồng/lịch thu; chưa nghiệm thu toàn CRM, M3 hoặc file33.

## Mở và sử dụng

- URL trên máy: http://127.0.0.1:64900/#hopdong — tab CRM đã mở và giữ lại trong chat.
- Nút mở lại: `D:\Claude\Phan mem ho tro ke toan\MO CRM GOP Y.lnk`.
- Shortcut gọi launcher có sẵn, đặt runtime riêng cho tiến trình cha/con; không chứa mật khẩu. Đã kiểm shortcut lưu đúng target/arguments và gọi thử; không quan sát được browser bên ngoài, chưa kiểm reboot/cold launch bằng shortcut.
- DataRoot riêng: `var/codex-dieu-phoi/crm-feedback-live-1773c885`, PostgreSQL neutral16 DEMO, login ứng dụng thường; cấu hình cục bộ giới hạn ACL.
- Hồ sơ mẫu đang có: hợp đồng KCN hiệu lực, 11 tham số có trạng thái căn cứ, 3 đợt thu; cọc đã nối khoản thu M1. Mẫu nhà ở/phụ lục còn sẵn để thử.
- Dùng vai MO_PHONG_KT_A để xem; các vai đều là mô phỏng. Server tiếp tục chạy sau khi kết thúc kiểm tra, không có TTL15phút. Dừng qua nút Dừng ứng dụng khi muốn.

## Code và kiểm độc lập

Claude cùng session sửa đúng hai hunk production: CRM đọc tổng tiền đã nối bằng SUM active links; route M1 CRM không gọi proof tiền của legacy M9. Giữ nguyên M9, migrations, M1 helper, guard và UI. Hai lần sửa test bổ sung fixture tự chứa và dùng hai đợt khác nhau cho cùng BANK; không nới guard.

- Frozen274: `var/codex-dieu-phoi/crm-feedback02-frozen-4b51725241`, manifest SHA256 `0f8d466966f720fe138e313c0253e524f1929f4179c448fcf23bd14ec3cfda92`.
- Root/peer FULL static production và test: CLOSED. Claude self-tests NOT_RUN (code-only); kết quả dưới đây do Root chạy.
- Native actual `d1cc80`: **5/5 method PASS, 0 failed/errors/skipped**, 6.079s; một DB mới được giữ lại, phương thức chạy theo thứ tự dùng chung trạng thái. Guard giữ tệp và source274 posthash đạt.
- Bằng chứng: `var/codex-dieu-phoi/crm-feedback-native02/direct-actual-58d2652e6a/child-summary.json`.
- Đã kiểm: neutral16 không object legacy; GET CRM; M1 ingest/engine/converter thật và retry; nhận/KT kiểm/CFO duyệt; nối một phần/replay/đổi body/gỡ; chặn vượt BANK/vượt nghĩa vụ/sai pháp nhân/sai quyền; SUM nhiều đợt; riêng tư theo pháp nhân.
- Snapshot ca âm chỉ gồm toàn hàng các bảng nghiệp vụ được chọn, số lượng audit, last_value sequence, path+size file. Không phải toàn byte/all audit/all sequence fields.

## GUI thực quan sát

Root bấm trực tiếp nhận kcn_goc bằng vai bán hàng, mở 11 tham số/trích dẫn/điều khoản, KT kiểm trước, CFO mô phỏng duyệt V4 và phiên bản. Lịch sinh 300m/1.2b/1.5b đúng mẫu. Vai KT nạp M1, xuất hiện một BANK/một đề xuất; nối300m vào COC-1 → DA_THU300m. Xuất file soát và bấm Tải↓. KT_B thấy rỗng hợp đồng/tiền/file của A; phục hồi KT_A và mở hồ sơ. Không chạy M9.

Native HTTP có token hợp lệ tải workbook **9159bytes**, SHA256 `5da0fb897fda95adf21041b2672a1d7b00edf05e5ed3c20281150bb928aadfdd`, bốn sheet HOP_DONG_PHIEN_BAN / LICH_NGHIA_VU / THAM_SO_CAN_CU / CANH_BAO. File tại `var/codex-dieu-phoi/crm-feedback-provision02/FILE-SOAT-CRM-HDC-KCN-DEMO-01-5da0fb89.xlsx`; receipt `file-native-review.json`. **Bytes lưu bởi browser sau nút Tải↓ chưa kiểm chứng**. Ảnh: cùng thư mục `crm-feedback-running.png`.

## Lỗi gặp và giới hạn còn lại

- Giữ cả hai lần native parent/Popen thất bại (actual-e824f4733d05, actual-6463020bee44: 1PASS/1FAIL/3ERROR). Diagnostic os.link bị từ chối trong một execution context; direct được cấp quyền thành công. Exact môi trường gây khác biệt chưa chốt; không xóa lịch sử thất bại và không gộp thành kiểm đạt.
- Lần GUI đầu DataRoot ngoài phạm vi giữ temp gây LOCAL_STORAGE_ERROR: giữ nguyên thư mục cũ, chuyển cấu hình sang DataRoot private phù hợp guard gốc; không sửa guard.
- Bộ chiếu M1 cần driver trong user runtime của tiến trình con. Đã cấu hình trong cách mở bản feedback; không tuyên bố launcher chung chạy độc lập với mọi môi trường. Ghi nhận để đóng gói bản vận hành sau.
- Một native GET thiếu token trả403; đã sửa chính checker, sau đó GET có token trả200 và workbook khớp. Không coi403 đó là lỗi sản phẩm.
- Tên shortcut tiếng Việt không lưu được qua COM; bản ASCII đã tạo, không xóa file nào.
- Giao diện còn nhãn kỹ thuật, nhiều nút mẫu và bảng cuộn ngang ở panel hẹp; đây là nội dung cần Anh góp ý trước vòng hoàn thiện tiếp theo.
- Nguồn hợp đồng thật/#6, profile nghiệp vụ bổ sung và toàn ngoại lệ còn cần đối chiếu. Không tự ghi nhận doanh thu/VAT, không nhập Junsky, không phê duyệt thật, không cloud AI. M3/full33 còn tiếp tục theo phạm vi đã chốt.
