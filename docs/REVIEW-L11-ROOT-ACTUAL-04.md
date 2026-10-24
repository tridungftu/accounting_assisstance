# Kiểm độc lập M2–L11–M5 — bản mã04, 20/10/2026

## Kết luận hiện hành

Đã kiểm độc lập các lát cắt dưới đây trên DEMO, giữ kho thật SQLite. Chưa nghiệm thu toàn L11, toàn M2/M5 hoặc toàn file33. M9 chỉ lấy dữ liệu, không sửa hoặc chạy phần mềm theo dõi vay.

Claude cùng session đã sửa đúng app.js và test_l11_k2.py; 271/273 file nguồn còn lại giữ nguyên so với bản03. Root đã đọc toàn bộ hai diff và báo cáo04; hai reviewer riêng kiểm lại trước runtime. Terminal thực96629/chunk827178 exit0. Manifest04 SHA d7a2ebb6fc1013b397271ebdeb1c49aec3f4f5c4260124c8c35baf7722217add; freeze e3cde8bf92bf06d40947ac4693d640f5d41598c39aefa8b19a8923b423c2a2c1. Đây là bằng chứng mã cố định, không tự chứng minh nghiệp vụ đạt.

## Kết quả đã chạy

| Phần | Bằng chứng thực | Phạm vi đạt |
|---|---|---|
| Native K2 L11 | handle53312/chunk7e8d8d exit0; pg-retained-20261020-045419-a72eaab4 | 23/23 PASS, 0 skip, gồm Q09 chọn đúng tuyến hiện hành |
| Native HTTP L11 | handle25482/chunk02bdb2 exit0; pg-retained-20261020-045419-6c7cfb5c | 2/2 PASS, 0 skip |
| Async handler/DOM/Blob | handle34905/chunkb9b14a exit0; l11-ui-async-frozen04/result-root-3f4cce51fd16.json | 14/14 PASS, 0 setup error; đổi vai/cặp/form, GET đảo thứ tự, lỗi muộn và tải hợp lệ |
| Causal độc lập | l11-causal6-root-aggregate04-01.json SHA9db9ca4066b14690986e8ecb062a77581941e98989d811623c71ef3a42744f72 | Sáu case hữu hạn: route↔confirm, revoke↔confirm, undo-held↔confirm, cả hai thứ tự |
| GUI thực | l11-gui-actual04-ead1f709e9e3 | Nhận GOODS/CAI raw, mở facts trước CFO xác nhận, mã hóa hóa đơn và dòng kho phù hợp, LINK preview bốn lượng8 rồi confirm |
| DB và workbook GUI độc lập | root-physical-file-observation01.json SHAa06dc38c3ac1f645e5fab17227e0d2950fe7da4792fae52ab4214d0210ea6abf; tool e2bb17 exit0 | Whole2candidate/2proof/2encoding/2pool/1parent/1child; hai dòng kho8+2 vẫn nguyên; confirmed8/held0, capacity10/8, remaining2/0 |
| File tải thực | root-browser-downloaded-bytes01.json; tool d7c039 | Đã đọc8865 bytes tải từ browser, bằng hoàn toàn file retained/registry SHA09df86c4b4ebd18e342a2da1721932e26a3f6b78aec73bc82f6e128e9ccb229e |

Workbook kiểm đủ LIEN_KET, DONG_SO_LUONG, NGAN_SACH_POOL, CANH_BAO; UUID/nội dung/timestamp đối chiếu physical rows, bốn lượng8, đơn vị native/pool, bằng chứng, tuyến KHO, trạng thái và ngân sách. Ô có dữ liệu đều text/@, không formula. Helper không gọi product workbook maker hoặc budget UDF để tạo đáp án. Whole DB rows/catalog/sequence/artifact trước–sau observer bằng nhau.

Causal dùng hai login app thường độc lập và observer thứ ba, UDF winner trả về trong giao dịch chưa commit; chụp whole winner-own DB và file trước khi follower kết nối, chứng minh đúng root advisory wait và pg_blocking_pids rồi mới commit. Mỗi case có11 oracle về toàn bộ delta, bốn lượng bất biến, full-domain SUM, held/confirmed, source basis và receipt/audit. C03 thêm fresh confirm1 sau revoke: exact RaiseException/P0001/L11_BANG_CHUNG_TY_LE_THIEU, whole factory rows/catalog/sequence/file delta0.

Các kết quả bản03 được giữ đúng phạm vi vì271 file business/source/test liên quan không đổi: migration14/14, M2 K2 18/18, M2 HTTP3/3, M5 K2 36/36; upgrade15→16 trên DB không rỗng; C1 native→own-pool không identity và C2 raw candidate/coverage. Không gọi chúng là vừa chạy lại trên04.

## Lịch sử lỗi và giới hạn

Lượt causal04 nguyên nhóm7DB hết240s, không tính PASS. Nhóm A/B runner05 exit1 do oracle sau race hiểu nhầm duoc_xac_nhan là eligibility: API giữ capability LINK=true và trả blocker riêng. C01/C02/C05/C06 đã hoàn tất đầy đủ trong A/B, whole273 posthash true; giữ nguyên trạng thái NOT_PASS toàn nhóm. Runner06 nhóm R kiểm mới C03/C04 với oracle đúng, terminal1263/chunk4cf548 exit0; Root tổng hợp đúng sáu case, không đổi lịch sử A/B thành PASS.

GUI lần1 tự dừng theo deadline trong lúc công cụ chờ tải bị trễ; giữ nguyên DB/file. Lần2 tải thực thành công và Root tạo stop.request; parent71165/chunkd8e153 exit0, child28004 STOP_REQUEST, không lỗi đóng kết nối, source/config/helper postpins giữ nguyên. Tất cả DB/role/attempt/file được giữ; không xóa file.

Sau đổi qua vai M5-only MO_PHONG_CFO_KHO_A bằng selector thật, trang L11 báo cần quyền CẢ M2 và M5, không còn liên kết hoặc nút FILE. Chưa kiểm GET của chính file dưới vai CFO này; không dùng việc ẩn nút thay bằng chứng download denial. Native HTTP có ca denial riêng. Chưa kiểm reopen sau restart; ảnh toàn trang còn biểu hiện cột hẹp/tràn ngang cần cải thiện trước bàn giao UI.

## Còn thiếu trước nghiệm thu L11

- Hai batch đồng thời, late-visible identity/cùng logical root mới, shared invoice/warehouse, cùng key qua cặp khác và closure nhiều pool.
- Q02/Q03 full-domain multipool/split và các phủ định độc lập còn lại; không suy từ một cặp8/8 hoặc C1 nhỏ.
- A→B→A có allocation sống, source/profile/map/unit/reversal/capacity transition; không tự phục hồi liên kết held.
- Login inactive/revocation, kỳ khóa/protection, direct write/cross-PN/typed graph và tương thích luồng cũ theo ma trận.
- GET cùng cross-file dưới current-rights khác, old bytes/reopen và toàn bộ GUI lifecycle còn lại.

Mọi trạng thái toàn L11/Q09/M2/M5/file33 vẫn NOT_VERIFIED cho đến khi đủ checklist. Bộ đọc XML/ZIP M2 đã có code và kiểm finite ở các mốc trước; kết quả ở đây là nối số lượng qua L11 với M5 tái dùng nguồn #10, không viết lại phần mềm nguồn.
