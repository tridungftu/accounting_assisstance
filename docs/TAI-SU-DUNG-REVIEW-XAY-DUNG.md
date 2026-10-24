# Tái sử dụng phần mềm Review hồ sơ thanh toán xây dựng cho M4

Ngày kiểm: 18/10/2026. Yêu cầu: tận dụng tối đa phần mềm đã có; không hỏi, thiết kế hoặc lập trình lại nghiệp vụ review xây dựng.

Nguồn đã đọc tĩnh: `D:\Claude\Ho tro review ho so xay dung\review_xaydung` — README, API, quy trình và source Python định nghĩa schema/result/export/routes. Không khởi chạy/import ứng dụng, không chạy test, không gọi network; không đọc `.env`, cấu hình máy/key, `co_so_du_lieu`, `ket_qua_AI`, hợp đồng, đầu vào/đầu ra hay chứng từ thật. Không sửa source dự án nguồn. Đây là audit code/tài liệu, chưa chứng minh trạng thái vận hành của dữ liệu thật.

## 1. Kết luận dùng ngay

**#5 đã có output có cấu trúc, CSDL hợp đồng/đợt, API JSON và Excel export.** Câu hỏi cũ “review xuất kết quả dạng gì?” trong TL30/TL31 đã có thể trả lời bằng source; không hỏi Anh lại. M4 chỉ cần bridge nhận kết quả và tạo **đề xuất kế toán có provenance**, bổ sung mapping pháp nhân/Junsky và xác nhận trường còn thiếu.

**Không đồng nhất `da_nap` với duyệt hạch toán. Không lấy `de_nghi - anh_huong` làm giá trị chấp nhận.** Nguồn hiện chưa có một trường độc lập mang nghĩa “giá trị được duyệt để hạch toán”; bridge không tự chọn số tiền, chính sách 241/154, VAT hay đối tượng kế toán.

TL31/TL32 đã chốt M4 nhận kết quả #5, không review BOQ lần nữa. TL40 đã chốt giữ chỗ chạy của #5, nối bằng vai trò riêng qua `giao_tiep`; không thay bằng một ứng dụng review mới hoặc yêu cầu phòng dự án nhập lại hợp đồng.

## 2. Những gì thực sự đã có — file và dòng

Các liên kết dưới đây trỏ thẳng source nội bộ; số dòng theo lần audit này.

| Fact đã kiểm | Bằng chứng |
|---|---|
| SQLite là nguồn của nghiệp vụ review; Excel là phiếu nhập/bản xuất. Gốc bất biến; phụ lục có hiệu lực theo ngày nghiệm thu; sửa sai có lý do và nhật ký. | [csdl_hop_dong.py:5](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:5>), [trigger:175](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:175>) |
| Hợp đồng, tham số, phụ lục, thay đổi tham số, BOQ, đợt, KL đợt, ghép hạng mục và nhật ký đã có schema. | [csdl_hop_dong.py:76](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:76>) |
| Khóa nội bộ HĐ `ma_hd`; số văn bản `so_hd` là UNIQUE. `ma_hd_moi` sinh dạng HD + số thứ tự trong CSDL nguồn. | [schema:81](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:81>), [ma_hd_moi:325](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:325>) |
| Đợt có PK `(ma_hd, dot)`, ngày nghiệm thu/nhận hồ sơ, giá trị kỳ/lũy kế, giữ lại, thu hồi tạm ứng, giá trị thanh toán kỳ, nguồn và ngày nạp. | [csdl_hop_dong.py:133](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:133>) |
| Kết quả kiểm đợt lưu JSON; có hàm đọc lại và liệt kê. | [may_chu/nghiep_vu.py:809](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/may_chu/nghiep_vu.py:809>) |
| JSON kiểm đợt đã chứa mã kết quả, HĐ, đợt, ngày, tham số hiệu lực, phụ lục áp dụng, số đề nghị, tổng hợp, findings, bằng chứng, bảng kiểm/đối chiếu hạng mục và link báo cáo. | [may_chu/nghiep_vu.py:863](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/may_chu/nghiep_vu.py:863>), [payload:898](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/may_chu/nghiep_vu.py:898>) |
| Nạp đợt là hành động riêng; chống nạp trùng, thay đợt phải có lý do; cập nhật `da_nap` trong JSON sau khi ghi nguồn. | [may_chu/nghiep_vu.py:920](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/may_chu/nghiep_vu.py:920>), [csdl_hop_dong.py:1258](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:1258>) |
| API HĐ chi tiết trả `tham_so[]` gồm giá trị hiệu lực, nguồn/phụ lục và provenance; trả cả `dot[]`, `canh_bao[]`, dự án và bên B. | [may_chu/dich_vu.py:699](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/may_chu/dich_vu.py:699>) |
| Export CSDL đã có HOP_DONG, PHU_LUC, BOQ_HIEU_LUC, BOQ_DONG, DOT_THANH_TOAN, KL_THANH_TOAN, CANH_BAO, NHAT_KY. | [csdl_hop_dong.py:1686](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:1686>) |
| Trích hợp đồng và màn sửa/xác nhận đã có; provenance lưu AI gốc/giá trị nạp, trích dẫn, nguồn, người/lúc xác nhận, lịch sử và SHA-1 file nguồn. | [csdl_hop_dong.py:158](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:158>), [may_chu/dich_vu.py:576](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/may_chu/dich_vu.py:576>) |

Lưu ý quan trọng cho người tích hợp: `mo_csdl()` tạo thư mục, executescript schema/trigger và có thể ALTER bảng ([csdl_hop_dong.py:197](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:197>)). **Không gọi nó chỉ để kiểm kê “read-only” kho thật.** Audit này chỉ đọc source text.

## 3. Output và ý nghĩa trường — không tự đổi nghĩa

### 3.1 Kết quả review JSON

`may_chu.nghiep_vu.kiem_tra_dot(...)` tạo payload tại dòng 898–914:

| Trường nguồn | Nghĩa dùng lại / giới hạn |
|---|---|
| `ma`, `loai`, `luc`, `tep` | ID lần review, loại `kiem_tra_dot`, thời điểm và tên file; dùng truy nguyên/chống nhận lại. Không phải chứng từ Junsky. |
| `hop_dong.ma_hd`, `hop_dong.so_hd`, `hop_dong.phan_loai` | Khóa nội bộ nguồn, số HĐ văn bản, phân loại. Cần namespace/instance nguồn; `HD...` tự sinh không phải khóa toàn tập đoàn. |
| `dot`, `dot_truoc`, `ngay_nghiem_thu` | Đợt hiện tại/đợt trước; ngày quyết định phụ lục hiệu lực. |
| `gt_hieu_luc`, `loai_gia`, `vat`, `phu_luc_ap_dung[]` | Snapshot căn cứ review tại ngày đợt. |
| `de_nghi`, `o_de_nghi` | Số **đề nghị** đọc từ hồ sơ, ưu tiên nhãn thanh toán kỳ này; không phải số được duyệt hạch toán. |
| `tong_hop` | Mỗi khóa có `gia_tri`, `o`, `nhan`; khóa đọc theo nhãn được định nghĩa ở `master_hd.py:790–823`: `gt_hd`, `gt_lk_kt`, `gt_kn`, `gt_lk`, `giu_lai`, `thu_hoi_tu`, `tt_ky_nay`. Không thay số không đọc được bằng 0. |
| `anh_huong`, `phat_hien[]` | Ảnh hưởng/phát hiện; có ảnh hưởng lũy kế, chưa VAT hoặc chưa định lượng. Không phải danh sách điều chỉnh số tiền kỳ được duyệt, không được cộng/trừ mù để tạo số chấp nhận. |
| `bang_k`, `cay`, `bang_lop2`, `doi_chieu_hm` | Bằng chứng, truy vết, bước đạt/lệch và ghép hạng mục. Giữ tham chiếu để người duyệt mở lại; M4 không tính/review chúng lần nữa. |
| `da_nap` | Ban đầu `False`; sau nạp là object `{luc,dot,so_hang_muc,khong_khop,ghi_chu,nap_lai}`. Chứng minh kết quả đã được nạp vào CSDL **review**; không chứng minh duyệt hạch toán. |
| `tai.lop1`, `tai.lop2` | Link báo cáo đã có; không bắt người dùng làm lại báo cáo review. |

`anh_huong` tổng ở `may_chu/nghiep_vu.py:896–897`; giải thích ảnh hưởng dòng là chênh **lũy kế, chưa VAT** tại dòng 351–363; các số tổng hợp đọc theo nhãn ở [master_hd.py:790](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/master_hd.py:790>). Vì khác cơ sở, **`de_nghi - anh_huong` không phải công thức chuyển đổi hợp lệ**.

### 3.2 Đợt đã nạp trong CSDL

`csdl_hop_dong.nap_dot` dòng 1274–1277 ánh xạ trực tiếp số **đọc từ hồ sơ**:

| Cột `dot_thanh_toan` | Khóa số tổng hợp nguồn |
|---|---|
| `gt_ky` | `gt_kn` |
| `gt_luy_ke` | `gt_lk` |
| `giu_lai` | `giu_lai` |
| `thu_hoi_tu` | `thu_hoi_tu` |
| `gt_tt_ky` | `tt_ky_nay` |

Các cột này không tự trở thành số quyết định kế toán chỉ vì tên hàm có chữ “đã duyệt”. Hàm nạp không tạo trường độc lập “giá trị chấp nhận hạch toán” hay trạng thái phê duyệt kế toán; `ghi_chu` là ghi chú tự do. Cần bảo toàn ý nghĩa trước/sau VAT, kỳ/lũy kế và đề nghị/chấp nhận khi chuẩn hóa.

### 3.3 Tham số hợp đồng, tạm ứng và bảo hành

Danh mục mã có sẵn tại [csdl_hop_dong.py:51](<D:/Claude/Ho tro review ho so xay dung/review_xaydung/csdl_hop_dong.py:51>):

- `TC-01` số HĐ; `TC-02` ngày ký; `TC-03` gói thầu; `TC-04` dự án; `TC-06/07` bên giao/nhận thầu.
- `TT-01` loại giá; `TT-02/03/04` giá trị HĐ, đã gồm VAT hay chưa, thuế suất.
- `TT-10/11/12` tỷ lệ tạm ứng, điều kiện thu hồi, bảo lãnh tạm ứng.
- `TT-20/21/22` tỷ lệ thanh toán đợt, giữ lại đợt, thời hạn thanh toán.
- `TT-30/31/32/33` tỷ lệ quyết toán, bảo hành/bảo lãnh bảo hành, thời hạn bảo hành, bảo lãnh thực hiện.

Phải dùng `tham_so_hieu_luc(con,ma_hd,ma_ts,ngay)` và phụ lục tại ngày nghiệm thu (`csdl_hop_dong.py:405`), không luôn lấy tham số gốc hoặc giá trị hôm nay. `TC-04` hiện là **giá trị tham số dạng text**, chưa có `ProjectID` Junsky. `ben_b`/`TC-07` cũng chưa phải mã đối tượng/MST được chuẩn hóa.

README nói pipeline 37 tham số; `DS_THAM_SO` trong CSDL có comment “36” và hỗ trợ thêm mã `Y-*`. Dùng catalog/rows thực và mã tham số, không hardcode số lượng 36/37 trong bridge; audit này không mở file catalog Excel.

## 4. Hàm, API và giao diện dùng lại

| Thành phần đã có | Cách tận dụng |
|---|---|
| `csdl_hop_dong.phu_luc_ap_dung`, `boq_hieu_luc`, `tham_so_hieu_luc`, `gt_hd_hieu_luc` (dòng 352/365/405/428) | Giữ engine hiệu lực/phiên bản, không viết lại trong M4. |
| `tinh_doi_chieu_dot` (1316), `kiem_dot` (1434), `_khop_hstt` (1132) | Kết quả nghiệp vụ ở #5; M4 tiếp nhận, không xây bản sao engine khớp BOQ/đợt. |
| `may_chu.nghiep_vu.kiem_tra_dot` (863), `nap_dot` (920), `doc_ket_qua_kiem_tra` (822) | Điểm hook/đọc cho adapter nhỏ: sau khi nạp thành công, tạo snapshot đề xuất kế toán có provenance; tách lỗi gửi khỏi nghiệp vụ review đã hoàn tất. |
| `may_chu.dich_vu.chi_tiet_hop_dong` (699) | Reuse cách dựng payload tham số hiệu lực + provenance + đợt; không đòi người dùng xuất danh mục mới bằng tay. |
| `trich_xuat.quy_trinh.TrichXuat(params,...)` (91), `.xu_ly` (264); `trich_xuat.kiem_tra.check` (97); `trich_xuat.logic.kiem_tra_logic` (56) | Đã có trích tham số, kiểm trích dẫn, logic. Khi mở rộng loại HĐ, dùng/thích nghi engine và cấu hình đã có; không mặc định làm một bộ trích xây dựng mới. Không sao chép cấu hình/key/cách gọi provider sang kế toán. |
| `trich_xuat.xuat.ghi_ket_qua_hd` (69), `cap_nhat_o` (128) | JSON/Excel trích HĐ, sửa/xác nhận và lịch sử đã có. `tom_tat_review` (49) chỉ đếm ô tham số, **không phải** chứng nhận nghiệm thu/duyệt tiền. |
| `may_chu.phu_luc_ai`, `may_chu.chung_tu`, `toan_ven.py` | Giữ phụ lục P01–P18, chứng từ lớp 3 C01–C09, toàn vẹn Excel K1–K8; không giao M4 làm lại. |
| UI `contracts.js`, `checks.js`, `phu_luc_ai.js`, `chung_tu.js` (README) | Giữ workflow nhập/xác nhận HĐ, phụ lục, ghép tay và nạp đợt của phòng dự án; UI kế toán bổ sung phần tài khoản/mapping/duyệt hạch toán. |

Các routes thực ở `may_chu/server.py`:

- `GET /api/hop_dong` (306), `GET /api/hop_dong/{ma_hd}?ngay=` (311), `GET /api/hop_dong/{ma_hd}/boq?ngay=` (316).
- `GET /api/kiem_tra/kiem_tra_dot` (358), `GET /api/kiem_tra/kiem_tra_dot/{ma}` (363).
- `POST /api/kiem_tra/kiem_tra_dot/{ma}/nap` (368); body `dot,ngay_nhan_hs,ghi_chu,ly_do_nap_lai` đi qua `may_chu/dich_vu.py:896`.
- `POST /api/csdl/xuat_excel` (403), body `ref,ngay`; export fallback đã có.

Đây là inventory API, **không phải yêu cầu gọi API hay mở server nguồn ra LAN**. Server hiện bind `127.0.0.1` ở `server.py:548–553`, kiểm Host/Origin và `X-HD` cho ghi tại 417–424; chưa phải API đa người dùng. Theo TL40, đường nối mới của phần mềm trong nhà là vai trò riêng và `giao_tiep`, không đổi toàn bộ server hoặc bỏ kiểm tra bảo vệ để tích hợp.

## 5. Bridge tối thiểu cần thêm — đề xuất kỹ thuật, chưa hiện thực

1. **Bộ chuẩn hóa nguồn** tại ranh giới #5: lấy payload review đã có và snapshot đợt/HĐ tại đúng ngày, không đọc lại BOQ/PDF để review. Chỉ nhận loại `kiem_tra_dot`; chế độ chỉ toàn vẹn `toan_ven` không đủ cho M4.
2. **Khóa liên kết**: định danh instance nguồn + `ma_hd` + `dot` + `ma` lần review; nối sang mã HĐ chung. `so_hd` là bằng chứng nhận diện bổ sung, không dùng tìm mơ hồ như UI. Lần chạy lại/nạp lại cần quan hệ thay thế, lý do và chống gửi trùng; không chèn thêm một công nợ mới cho cùng sự kiện.
3. **Mapping được người có quyền duyệt một lần**: instance/HĐ nguồn → pháp nhân + mã HĐ chung + `ProjectID`/giai đoạn + đối tượng nhà thầu Junsky; không suy mã Junsky từ tên bên B hoặc text dự án. Schema nguồn được kiểm không có các trường `phap_nhan_id`, `ProjectID`, `ObjectID`, mã hóa đơn/RQ chung.
4. **Bản đề xuất kế toán có provenance**: giữ ID review/đợt, ngày, căn cứ hợp đồng/phụ lục, số nguồn kèm ý nghĩa, tham chiếu báo cáo, dấu nạp/ghi chú; bổ sung riêng số tiền chấp nhận hạch toán và xác nhận có thẩm quyền. Thiếu mapping/số được xác nhận/cơ sở VAT → trạng thái chờ xác nhận, không mặc định 0, không tự gán “đã duyệt”, không tự sinh dòng đủ điều kiện xuất.
5. **Đẩy có kiểm soát** qua hợp đồng TL40 `giao_tiep.v1_ghi_ket_qua_review(jsonb) → uuid`, vai trò `app_review`; lõi nhận view/hàng đợi phiên bản `v1_nghiem_thu_da_kiem` để tạo hồ sơ M4 và liên kết M2/M1. Tên hàm/view là thiết kế TL40, **không tìm thấy trong source #5 đã audit**. Không ghi thẳng bảng `kho/master/bao_mat`.
6. **M4 tiếp tục phần kế toán riêng**: đề xuất 241/154, công nợ/tạm ứng/bảo hành/VAT theo chính sách đã duyệt; nối hóa đơn, RQ, thanh toán; dùng màn duyệt chung, nhật ký, chống trùng và kiểm tra Junsky của M0. Quyết định review xây dựng được giữ nguyên làm căn cứ, không bị M4 viết lại.

File Excel `DOT_THANH_TOAN` đã có thể làm fallback đọc có kiểm soát trong pilot, nhưng export tự nó chưa có mapping Junsky/ID review/duyệt kế toán. Không chọn CSV/Excel làm nguồn nghiệp vụ mới cạnh tranh với CSDL #5.

## 6. Nghiệp vụ nguồn đã chốt — không hỏi lại Anh

Theo `quy-trinh-review-ttkl.md:40–78`, `:142–145`, `:196–210`, `:288–308`:

- Review đi ngược từ số đề nghị về dữ liệu gốc; HĐ/BOQ/PL/đợt trước nằm trong một CSDL; không lấy hồ sơ tự đối chiếu chính nó.
- Chỉ phụ lục đã ký và hiệu lực tại **ngày nghiệm thu** được áp dụng; bản dự thảo không có hiệu lực. Dữ liệu gốc không sửa đè; sửa sai có lý do/nhật ký.
- Tham số tỷ lệ thanh toán, tạm ứng, thu hồi, giữ lại, bảo hành thuộc từng hợp đồng; không hỏi lại một tỷ lệ chung, không hardcode trong M4.
- Hợp đồng đơn giá cố định: KL thực tế của hạng mục đã có thay đổi thì không mặc định cần phụ lục; hạng mục mới/đổi đơn giá mới cần xử lý theo quy trình đã chốt.
- AI trích/đề xuất, Python kiểm tra, người review chốt; giữ trích dẫn và trạng thái xác nhận. Không thêm một vòng hỏi lại/phê duyệt lại cùng nghiệp vụ xây dựng bên kế toán.

**Giới hạn đã biết cần giữ khi tái sử dụng:** tài liệu nguồn dòng 455 ghi rõ bản engine vẫn báo B1 và tính ảnh hưởng cho KL vượt ở cả HĐ đơn giá cố định, chưa theo chính sách vừa nêu; source `csdl_hop_dong.py:1407–1421` và `may_chu/nghiep_vu.py:327–363` còn đường xử lý này. Đây là lệch code/đặc tả đã biết của nguồn, không phải quyết định nghiệp vụ cần hỏi lại Anh. Không dùng `anh_huong` tự tính số được hạch toán; nếu sửa thì sửa có kiểm chứng tại engine nguồn, không dựng engine cạnh tranh trong M4.

## 7. Phần thiếu tối thiểu, không mở lại toàn bộ thiết kế

| Thiếu | Cách hoàn thiện |
|---|---|
| Ánh xạ pháp nhân/HĐ chung/Junsky từ mã nguồn | Chuẩn bị bảng mapping dựa trên master hiện có; người có thẩm quyền xác nhận các dòng chưa rõ. Không yêu cầu nhập lại HĐ. |
| “Giá trị chấp nhận hạch toán”, cơ sở trước/sau VAT và quyết định kế toán | Bổ sung trường xác nhận riêng gắn snapshot review; giữ số nguồn. Người có thẩm quyền quyết phần nguồn chưa thể hiện; không chọn bằng phép trừ findings. |
| Phê duyệt kế toán và danh tính người duyệt | Tách khỏi `da_nap`/ghi chú review; đi qua workflow M0, không coi nút nạp #5 là nút Đồng ý kế toán. |
| Bridge/version/idempotency và retry | Thêm adapter + hợp đồng `giao_tiep` theo TL40, giữ nguyên engine/UI review hiện có; ca kiểm DEMO cho nhận lại, chạy lại, nạp thay và thiếu mapping. |
| Sai khác engine nguồn đã có tài liệu ghi nhận | Đưa vào kiểm chứng nguồn khi áp dụng; không thay bằng giả định “đã nạp nghĩa là mọi phát hiện hợp lệ”. |

Không có bằng chứng tĩnh nào trong audit này cho phép tuyên bố đã tích hợp #5 với PostgreSQL hoặc nghiệm thu end-to-end M4. Phần cần làm là **bridge và phần quyết định kế toán còn thiếu**, không làm lại phần mềm review xây dựng.
