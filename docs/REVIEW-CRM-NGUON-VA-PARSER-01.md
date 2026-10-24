# Review độc lập CRM-01 — nguồn và parser

**19/10/2026, sau Claude handle 3863 terminal exit 0. Chưa đạt để nghiệm thu CRM-01.** Đã kiểm 116 hash của handoff trước khi chạy; parser/source snapshot không đổi trong probe. Guard giữ file được bật. Không sửa sản phẩm, không chạy DB/repository/GUI, không xóa file hoặc DB.

Kết quả **20 criterion probe: 12 đạt đúng phạm vi, 6 sai, 2 capability gap**. Thêm **18 mẫu S01–S18 được source adapter nhận đúng format JSON**; đây chỉ là kiểm transport/format, **không phải 18 workflow hoặc 18 yêu cầu nghiệp vụ đạt**. Không chạy toàn corpus 44 vector qua blocker đơn vị tiền không liên quan.

## 1. Sáu lỗi runtime cần sửa

| Mức | Ca độc lập | Expected → thực tế |
|---|---|---|
| P1 | `P1-VALUE-NOT-IN-CITATION` | Quote ghi 40m, raw đợt 1 ghi 45m; đợt 2 có quote đúng 55m nên tổng raw vẫn 100m. Phải giữ chờ vì 45m không có căn cứ. **Thực tế** `CO_CAN_CU`, typed 45m, lịch 45m+55m, tổng cân, `chan=[]` |
| P1 | `P1-DERIVED-NOT-EXPLICIT-SCHEDULE` | Giá trị 40m có `ghi_chu=Suy ra`; quote chỉ nói phép suy tỷ lệ, không nêu 40m. Không được biến thành đợt tiền tường minh. **Thực tế** lịch 40m được sinh, không có blocker |
| P1 | `P1-ANNEX-PAID-BASIS-CHANGED` | Đợt đã thu đổi cơ sở trước VAT → sau VAT, giữ số tiền/currency/ngày. Cần đối chiếu khả năng so sánh và nghĩa vụ. **Thực tế** `GIU`, `chan=[]`; signature bỏ `co_so` |
| P1 | `P1-ANNEX-PAID-KIND-CHANGED` | Đợt đã thu đổi `DOT → COC`, giữ các trường signature. Cần đối chiếu phân loại nghĩa vụ. **Thực tế** `GIU`, `chan=[]`; signature bỏ `loai` |
| P2 | `P2-OPTIONAL-EMPTY-MONEY-SCHEDULE` | Hai đợt 40m+60m đủ; template đợt 3 có giá trị/citation rỗng, `kiem_tra=THIẾU giá trị`. Template optional chưa có nghĩa vụ không được chặn lịch hợp lệ. **Thực tế** `LICH_THIEU_SO_TIEN` |
| P2 | `P2-OPTIONAL-EMPTY-PERCENT-SCHEDULE` | Tương tự, hàng tỷ lệ optional rỗng chưa phải lịch %. **Thực tế** `LICH_TY_LE_THIEU_CO_SO`, chặn cả lịch hợp lệ |

Vị trí: `k2/crm_phan_tich.py` — `trang_thai_can_cu` chỉ kiểm quote containment; `tham_so_typed/tong_hop` không gắn giá trị/đơn vị/derived warning với căn cứ; `tong_hop` kích hoạt đợt chỉ vì mã có mặt trong `by_ma`; `so_sanh_phu_luc.sig` chỉ so tiền/currency/hạn/mốc.

Control dương tách biệt đã đạt: hai đợt ISO-currency tường minh 40m+60m, cùng cơ sở, không blocker; đợt đã thu giữ nguyên → `GIU`; đổi hạn đợt chưa thu → `DOI`; đổi số tiền đợt thu một phần → blocker đúng. Vì thế các lỗi trên không được kết luận chỉ từ việc helper/app chưa chạy.

## 2. Hai gap đã quan sát qua runtime

1. **Đơn vị tiền của nguồn #6:** corpus nguyên gốc dùng `don_vi=đồng`, đúng nguồn kỹ thuật đã đọc. Cả ba field tiền cần dùng của bản KCN nhận `PARSE_TIEN_TE`. Không đổi raw sang VND để làm baseline xanh. Cần hỗ trợ alias/currency có cấu hình và giữ nguyên raw/provenance; VND/USD ISO chỉ được dùng trong **control mới riêng** để cô lập những lỗi khác.
2. **Vị trí citation/proof:** đổi `dieu_khoan` thành Điều 99/Khoản 99.9 không tồn tại nhưng quote vẫn có trong text, parser vẫn `CO_CAN_CU`, không blocker. Interface hiện nhận text và hash Word do bên gọi truyền, chưa nhận/kiểm Word/manifest/địa chỉ đầy đủ. Phải tách “có quote trong text” với “đã đối chiếu đúng tài liệu/vị trí”. Chưa có DB/GUI probe để khẳng định toàn cổng đã được bảo vệ.

Profile version/hash và liên kết Word–text vẫn là gap interface đã ghi trong binding tĩnh; lượt này **chưa chạy repository để chứng minh/đánh giá** việc chọn latest hoặc pin profile. Không biến unsupported/setup thành business fail/pass.

## 3. Bằng chứng và giới hạn

- Baseline **187 file giữ nguyên**, manifest SHA256 `4aa3d06a63eb8a816bb044c0768801909b88837f511fe2f258922ab384db20a4`; không sửa ngày, profile hoặc expected của baseline theo output sản phẩm. Fixture clock 20/11/2026 chưa được bind vào đồng hồ ứng dụng/DB; không có claim về hiệu lực tương lai.
- Kết quả dùng để đếm: `var/codex-dieu-phoi/crm-independent-binding-20261019/runtime-20261018T233527840003Z/parser-review-result.json`. `isolation-control-inputs.json` cùng thư mục chứa các control DEMO mới và profile rõ ràng. Receipt riêng giữ receipt terminal gốc và bổ sung `product_snapshot` để gate execution.
- Parser SHA256: `3eff1bbdbcc788f32d6b1cfebfa9d63c7c150e2c68bbf64de000dbe5d6d5b60c`. Các hash source khác nằm trong report/receipt.
- 12 ca đạt gồm control dương, thiếu citation, chưa AI, chặn đổi đợt đã thu một phần, integer lớn giữ đúng từng chữ số, fractional VND trả lỗi scale thay vì rounding, USD locale chính xác, source retry key ổn định và mốc sự kiện giữ ngày NULL. Chúng không chứng minh repository idempotency, phân quyền đăng nhập, RLS, phụ lục có hiệu lực, link tiền hay GUI.
- Một lần chạy ban đầu dừng do binding dùng nhầm `Record.natural_key`; đã sửa riêng harness sang field thực `Record.key`. Lần dừng đó không tính là lỗi sản phẩm hoặc ca đạt. Lần kiểm cuối dùng optional giá trị/citation rỗng đúng hình thức nguồn, vẫn tái hiện cả hai lỗi optional.

Ca chia/gộp giữ đúng căn cứ: `BO+THEM` có thể hợp lệ khi phụ lục/mapping được duyệt rõ và chỉ tác động phần chưa thu. Control chia 70m→30m+40m trong corpus là **ca thiếu mapping**; chưa chạy repository hoặc positive control mapping đầy đủ trong lượt này, không kết luận mọi thay khóa là lỗi.
