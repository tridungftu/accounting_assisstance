# L11 R16 candidate02 — kiểm độc lập của root

**NOT_ACCEPTED / REPAIR03_REQUIRED.** M2 pure XML/ZIP và R15 bridge giữ trạng thái dependency DEMO đã kiểm hữu hạn. Bản L11 thứ hai có tiến triển thực tế, chưa nghiệm thu toàn L11/M2/M5/file33.

Claude kết thúc actual handle47839/chunk60f60e/exit0, session52783bcd-6e1d-46d2-9e45-3c527aa43e5b. Root freezer kết thúc chunk23b22f/exit0:273 source,8 thay đổi,259 protected không drift,20 fixture không đổi,0 ngoài phạm vi/thiếu/xóa. Manifest81abd25aad43aed3b0e991c91c080b86da354662f2a5f3721970bf1bcb750e2f; freeze receipt96f3a7497c3a3833a18a37076640599050eb697f48f53a643b2e396716f37fb9. Vị trí dưới đây thuộc frozen02. Root đọc toàn8 deltas và report02; peer review SQL/locking/service/HTTP/UI độc lập. Coder selftests đều UNRUN.

| Kiểm chạy actual của root | Kết quả | Giới hạn |
|---|---|---|
| Migration/primitive |12run/11pass/1fail/0error/0skip; terminalffbba6exit1, handle14405 | Fresh0→16 và oracle generated1–15 đạt. Upgrade test288 kỳ vọng L11_LIEN_KET_CHUNG_GIA nhưng trigger lịch sử lien_ket_kiem từ chối trước bằng LIEN_KET_KHONG_SUA. Đây là sai oracle của test; chưa chứng minh bypass endpoint. Không đổi guard để ép đúng lỗi mới. |
| Service |18run/17pass/1fail/0error/0skip; terminalfdb5abexit1, handle1692 | Ca forged parent UPDATE bị đúng P0001 L11_CHA_BAT_BIEN, helper184 chỉ cho42501 hoặc BIEN_NHAN*. Sửa expected-code theo đúng từng thao tác, không nới broad substring/ANY exception. |
| HTTP |2run/2pass/0fail/0error/0skip; terminal977c08exit0, handle52106 | Workflow thực receive→approve→encoding→preview→confirm/replay→FILE bytes→undo; proof GET/facts/privacy. Asset substring không chứng minh JavaScript async/browser. |

Mọi suite dùng PostgreSQL DEMO mới, no-delete guard gốc và watchdog180s; whole273 live/frozen pre/post và protected259 giữ nguyên. Không có dữ liệu thật hoặc credentials trong báo cáo. Counts không thay kiểm độc lập full row/hash/sequence/file delta. Migration native nhỏ chưa chứng minh nonempty15→16 trên toàn nguồn M2/M5.

Các ca service đã chạy đạt gồm hai confirmkeys4/4 một parent/hai child, THUNG→THUNG1/1 và split6+6, nonidentity THUNG→invoiceCAI12/1 với positive0.01/0.12→pool0.12/0.12 và negative0.01/1.44, hold khi đổi tuyến/thu hồi, undo held, quyền hiện hành, cross-PN preview denial và coverage HOLD. Những kết quả này là root chạy bộ test của coder, không phải nghiệm thu độc lập mọi trường hợp Q00–Q09. Token public DTO và unique proof keys đã giải quyết các lỗi setup của candidate01; giữ nguyên product guards.

## Các điểm phải sửa tiếp

1. **P1 — whole-batch identity/namespace lock chưa đủ (static).** Replacement8116–8122 chỉ precollect hóa đơn đã tồn tại. Loop lịch sử5936 và namespace HOA_DON5955→INSERT identity5956→HOA_DON_ROOT5962 vẫn theo input order. Hai batch mới [A,B]/[B,A] có thể giữ namespace A/B rồi chờ nhau. Batch mixed existing/new còn xin namespace sau root/pool đã precollect. Phải có shared pre-root identity gate/order cho toàn batch, resolve mọi identity trước canonical root/pool closure và trước business effects; không chỉ sort XML hoặc append một khóa sau pool. Literal/generated1–15 giữ nguyên; replacement chỉ trong16. Đây là chứng minh cấu trúc khóa, chưa runtime tái hiện deadlock.

   Peer lock review còn nêu protocol gap: helper6600–6604 chỉ recheck root containment, không toàn pool/child IDs; revoke7180–7191 xin pool từ query mới trước root expansion check. Cần full precollected set/recheck/restart đúng order. Chưa kết luận đây là oversubscription/deadlock runtime độc lập. Sort lock plan, giữ original observation order/history. Chi tiết và late-visible identity counterexample ở `REVIEW-L11-LOCK-02.md`.

2. **P2 — FILE còn mất pair/form/generation fence (static).** l11Act1194 dùng mặc định conHieuLuc()=>true; FILE1341 không truyền captured l11FormEpoch. Pair/amount handlers1359/1366 chỉ tăng form epoch. conCap1340 chỉ kiểm parent còn trong list. Vì vậy đổi pair/amount trong POST→refresh hoặc lúc blob pending vẫn có thể click file cũ. Returned fence1196 cũng không giữ generation sau lần so1204: newer GET trong blob pending không hủy continuation cũ. Phải giữ immutable original actor/epoch/form/selection/generation qua actual click và kiểm sau mọi await; không rearm theo current state. Role epoch đã sửa nhưng chưa đóng toàn continuation.

3. **P2 — NATIVE_ENCODING bỏ native_byte_length (static).** Approval7090–7139 và encoding7359–7374 không đọc/check/store claim native_byte_length của proof, dù raw fixture khai480. Dedicated configured proof với length sai nhưng SHA/locator/lexeme đúng chưa bị semantic guard này chặn. Cần positive exact integer length, so actual supporting artifact/reader byte length, lưu cùng immutable proof/basis và kiểm lại khi encode. Sai length phải bị từ chối, không duyệt proof/encoding/child; raw evidence được giữ.

4. **R2 actual source support phải kiểm trước native-proof approval.** l11_ho_tro_don_vi_noi_bo6653 hiện chỉ được gọi khi encoding7342/7372/7402. Native proof có declaration/catalog nhưng chưa capture actual supporting unit/item field vẫn có thể được CFO approve trước đó. Theo handoff02, actual-support negative phải0newapprovedproof. Dùng chính COMMON capture/reader đã có; khi chưa đủ hỗ trợ giữ/deny candidate approval rõ mã. Sắp lại fixture setup để capture THUNG thật trước native proof approval. Không đòi capture trước toàn bộ5 binding của GOODS bằng một suy diễn mới; actual pair validation vẫn kiểm domain/bindings cụ thể.

5. **Hai test exact-error oracles sai.** Migration288 phải phân biệt LIEN_KET_KHONG_SUA của lịch sử với L11 guard mới; K2445 phải kỳ vọng L11_CHA_BAT_BIEN cho đúng forged-parent operation. Không đổi SQL trigger ordering/quyền để làm test xanh, không dùng generic exception/substrings.

   Rút nhận định cũ rằng legacy parent retarget đã là một bypass: native02 cho thấy guard lịch sử chặn trước guard L11. Chỉ nhận bằng chứng actual denial/row preservation; không trình bày một trigger thiếu check riêng như exploit đã tái hiện.

## Chưa kiểm chứng

Q09 causal races thực hai PG connections và cả hai winner orders; batch ZIP đa identity/order; AA/ABA; các source/support field/context/measurement/ordinal negatives đầy đủ; nonempty15→16 giữ nguồn/raw/FILE/quyền; aggregate one-RR dưới second-owner commit; async FILE actual event handlers; browser buttons và file download/cells. Duy trì các phần này là UNRUN/NOT_VERIFIED, không đồng nhất thiết kế/code/native tests với nghiệm thu.

Khóa mapping trước root trong các đường lịch sử chỉ có thể chấp nhận sau khi kiểm shared order với tất cả intake/file/confirm paths và causal evidence. Không dùng comment trong report02 làm chứng minh không deadlock. Giữ stable logical LINE pool grain, stored reservations và current-state replay; không thêm tiền/bút toán/tồn kho hoặc resume M9.
