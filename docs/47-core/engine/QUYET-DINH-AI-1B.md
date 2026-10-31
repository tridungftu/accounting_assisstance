# AI-1b — Đầu vào `ai.hoi@1` và cờ chỉ Local

**Ngày:** 31/10/2026. **Phạm vi:** tài liệu cho engine `e_hoi_ai`, không sửa code hay chuẩn SDK hiện hành.

**Trạng thái:** bản đề xuất để lead chốt theo CD-041 mục 3 trong giao việc của Anh; **chưa qua Opus review**. Các quy tắc đã có được giữ nguyên; các biểu diễn kỹ thuật TL 48 chưa quy định được đánh dấu **Cần lead**, không coi là quyết định đã duyệt. Sau khi lead chốt và Opus review đạt, lead ghi phần “Thay đổi” vào CHUAN-CORE-SDK v1.1.

## 1. Căn cứ và bảng trường đầu vào

Ký hiệu nguồn và số dòng tính trên các tệp đã đọc khi soạn:

- **T48:** `D:\Claude\Phan mem ho tro ke toan\48-cong-ai-local-luon-co-cloud-qua-mask-v2.md`.
- **E1:** `docs/47-core/engine/GIAO-ENGINE-1.md` trên repo hợp nhất `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức`.
- **A:** `src/kho_tri_thuc/tri_thuc/cong_ai.py` trên repo hợp nhất trên, không lấy bản worktree làm mã gốc.
- **SDK:** `docs/47-core/chuan/CHUAN-CORE-SDK-v1.0.md` trên repo hợp nhất trên, §3.9–3.10.
- **K:** `src/kho_tri_thuc/core/contract/ky_thuat.json` trong worktree hiện tại.

Một payload là một yêu cầu gửi cổng AI. Năm trường nghiệp vụ chuyển 1-1 từ `YeuCauAI`; tuple Python biểu diễn bằng array JSON. Cờ chỉ Local là điều khiển bổ sung của adapter, không phải trường đã có trong DTO gốc.

| Trường | Kiểu JSON → Python | Bắt buộc / nullable | Đơn vị, giới hạn và ý nghĩa | Nguồn dòng mã |
|---|---|---|---|---|
| `loai_viec` | `string` → `str` | Có; không `null` | Mã loại việc đã khai trong `LOAI_VIEC`; mã lạ bị từ chối. Không tự bổ sung loại việc, ngưỡng hay quyền Cloud. | A:82–101, 285, 1241 |
| `van_ban` | `string` → `str` | Có; không `null` | Văn bản gốc để đọc và kiểm trích dẫn; phải còn nội dung sau `strip()`. Không đưa XML hóa đơn thô ra Cloud. Chưa có giới hạn số ký tự đầu vào được quy định tại các dòng này. | A:278, 286, 1156–1157, 1242–1243 |
| `chi_dan` | `string` → `str` | Có; không `null`; được rỗng | Việc cần làm; không đưa dữ liệu chứng từ vào đây. Cả chỉ dẫn, tên trường và văn bản đều nằm trong nội dung đi qua Mask trước Cloud. Không có giới hạn ký tự riêng trong nguồn. | A:279, 287, 964–969, 1164, 1244–1245 |
| `truong` | `array<string>` → `tuple[str, ...]` | Không; bỏ qua tương đương `[]`; không `null` | Tên trường cần điền, mỗi tên là chuỗi không rỗng; `[]` nghĩa là nhận mọi trường AI trả. Nguồn không cấm tên trùng hoặc đặt số lượng tối đa. Đây không phải array các object `TruongAI`. | A:280, 288, 296–301, 1244–1245 |
| `dinh_danh_da_biet` | `array` → `tuple` | Không; bỏ qua tương đương `[]`; không `null` | Mỗi phần tử: chuỗi, cặp `[gia_tri, nhom]`, hoặc object `{gia_tri, nhom}`. Sau chuẩn hóa khoảng trắng, chỉ giữ giá trị dài 2–300 ký tự, bỏ trùng theo giá trị không phân biệt hoa thường + nhóm. Nhóm được trim/viết hoa; nếu có phải khớp `[A-Z][A-Z_]{1,19}` (2–20 ký tự). Giới hạn 500 mục áp **sau chuẩn hóa, trên nhánh Cloud**, không phải `maxItems` của payload. Chỉ đưa định danh; không đưa tiền/ngày vào danh sách che. | A:281–283, 289, 909–940, 1158–1160, 1246 |

`chi_dan`, `truong` và `dinh_danh_da_biet` giữ nghĩa gốc; không tự tạo prompt riêng theo module. Chuỗi định danh dạng số từ 6 chữ số, nếu thiếu nhóm hoặc nhóm `KHAC`, được chuẩn hóa thành `GIAY_TO` theo A:934–935. Danh sách nhóm ở A:282–283 là hướng dẫn nguồn, không biến thành enum đóng vì mã chỉ kiểm mẫu nhóm tại A:930–931.

**Danh tính, pháp nhân và việc không nằm trong payload.** Core gắn ngữ cảnh đã xác thực; `phap_nhan_id`, `viec_id`, `de_xuat_id` của DTO không do module tự khai ở đây (E1:144; A:290–292). Schema đóng trường ngoài theo SDK:1047; schema không thay kiểm quyền và ngữ cảnh của Core (SDK:1048–1049).

**Cần lead — biểu diễn kỹ thuật:** TL 48 không định nghĩa JSON của năm trường. Bảng trên lấy từ DTO/kiểm tra nguồn theo E1:144. Schema ở §3 là đề xuất tuần tự hóa các dạng chuỗi được mô tả trong DTO; không tuyên bố rằng mọi giá trị Python mà hàm chuẩn hóa có thể ép sang chuỗi đều là đầu vào JSON hợp lệ.

## 2. Cờ “chỉ AI nội bộ” / chỉ Local

| Thuộc tính | Nội dung |
|---|---|
| Tên đề xuất | `chi_cuc_bo` |
| Kiểu / bắt buộc | `boolean`, không `null`, tùy chọn |
| Mặc định đề xuất | `false`; bỏ trường tương đương `false` |
| `true` | Chỉ dùng đường Local; **0 lời gọi Cloud**, kể cả khi Local lỗi/không chạy, thiếu chắc chắn hoặc được chọn kiểm xác suất. Không mở nhánh provider dự phòng trên Cloud. |
| `false` | Không áp hạn chế chỉ Local của request; **không có nghĩa bật Cloud**. Vẫn chịu công tắc Cloud, bảng loại việc, ba điều kiện dùng Cloud và điều kiện Mask v2 hiện có. |
| Ánh xạ | Adapter dùng instance/cấu hình riêng cho request; `chi_cuc_bo=true` → `cloud_bat=False` trên instance đó. Không sửa DTO/lõi gốc, không tạm đổi `self.cai_dat` của instance chung rồi khôi phục. |
| Module bắt buộc | **M9 phải đặt `true` theo CD-015** (căn cứ CD-015 do giao việc của Anh cung cấp; E1:144 nhắc rõ M9, A:93 khai `HOI_DAP_VAY` không dùng Cloud). Không suy rộng thành nghĩa vụ mới cho module khác. |

Đây là cách bọc công tắc tắt Cloud đã có: E1:154 yêu cầu instance theo request; A:1033–1035 chặn chọn kiểm khi Cloud tắt, A:1149–1150 chặn trước khi đọc khóa/gọi Mask/Cloud. Hai request khác cờ không làm đổi cấu hình của nhau (E1:177–178). Cờ `false` không vượt qua `duoc_dung_cloud=False` của loại việc (A:1151–1152).

Local luôn có đường sử dụng, không đồng nghĩa model/tiến trình luôn chạy (E1:140). Nếu Local không tạo được kết quả dùng được khi chỉ Local, giữ cách trả kết quả/thiếu kết quả của nguồn; không tự đổi sang Cloud, không thêm mã lỗi hoặc chính sách retry mới (A:1261–1295).

**Cần lead — tên/default:** TL 48:19–22 quy định Local, công tắc Cloud và điều kiện Cloud, không đặt tên cờ theo request hay default của cờ này. `chi_cuc_bo=false` là đề xuất kỹ thuật theo giao việc, khác với `cloud_bat=False` mặc định của cấu hình nguồn (A:117–118); chưa coi là đã duyệt trước lead và Opus review.

## 3. JSON Schema 2020-12 và ví dụ DEMO

Schema dưới đây mô tả **payload đầu vào capability**, không phải dữ liệu công bố; không tự thêm vỏ `vo_noi_dung` dành cho dữ liệu công bố (SDK:1003–1016). Đầu ra vẫn là `tra_loi_ai.v1` theo E1:146. **Cần lead:** xác nhận mã/URN đầu vào đề xuất `hoi_ai.v1` và việc ghim trong manifest; `ai.hoi@1` là mã capability, không đồng nhất với `$id` contract. Quy ước URN bản đầu theo SDK:1051–1055; không sửa schema đã phát hành dưới cùng `$id`.

Các `$ref` dùng đúng tài nguyên `urn:ktt:contract:chung.v1` của K:2–18; đăng ký tài nguyên đó từ `ky_thuat.json` để giải **offline**, không tải mạng. Dùng `chuoi` cho mã loại việc và tên trường không rỗng; không dùng `ma` vì kiểu này chỉ nhận chữ thường trong khi mã loại việc gốc viết hoa. `chi_dan` và chuỗi định danh thô dùng `type: string` để giữ khả năng rỗng của nguồn; không ép sang `chuoi` có `minLength: 1`.

**Cần lead — chi tiết schema:** dạng object định danh đề xuất bắt buộc cả `gia_tri`, `nhom` theo mô tả DTO A:281–283 (nhóm có thể là `""`); nguồn A:923–929 thực tế còn chấp nhận thiếu khóa và ép kiểu. Chưa chốt mở rộng JSON cho các trường hợp dung nạp này. Không thêm giới hạn độ dài văn bản, số trường, số định danh thô, enum nhóm hay quy tắc loại trùng ngoài nguồn.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:hoi_ai.v1",
  "title": "hoi_ai.v1 — đầu vào ai.hoi@1 (đề xuất AI-1b)",
  "$comment": "Bản đầu 1.0.0 đề xuất; Cần lead chốt và Opus review trước đăng ký.",
  "type": "object",
  "additionalProperties": false,
  "required": ["loai_viec", "van_ban", "chi_dan"],
  "properties": {
    "loai_viec": {
      "$ref": "urn:ktt:contract:chung.v1#/$defs/chuoi",
      "description": "Kiểm tiếp mã trong LOAI_VIEC hiện có; không bổ sung bảng định tuyến."
    },
    "van_ban": {
      "$ref": "urn:ktt:contract:chung.v1#/$defs/chuoi",
      "pattern": "\\S",
      "description": "Văn bản gốc không rỗng/không chỉ khoảng trắng; kiểm tiếp theo strip() của Python."
    },
    "chi_dan": {"type": "string"},
    "truong": {
      "type": "array",
      "default": [],
      "items": {"$ref": "urn:ktt:contract:chung.v1#/$defs/chuoi"}
    },
    "dinh_danh_da_biet": {
      "type": "array",
      "default": [],
      "items": {"$ref": "#/$defs/dinh_danh"}
    },
    "chi_cuc_bo": {
      "type": "boolean",
      "default": false,
      "description": "true: 0 lời gọi Cloud cho request; false không tự bật Cloud."
    }
  },
  "$defs": {
    "dinh_danh": {
      "oneOf": [
        {"type": "string"},
        {
          "type": "array",
          "minItems": 2,
          "maxItems": 2,
          "prefixItems": [{"type": "string"}, {"type": "string"}],
          "items": false
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["gia_tri", "nhom"],
          "properties": {
            "gia_tri": {"type": "string"},
            "nhom": {"type": "string"}
          }
        }
      ]
    }
  }
}
```

`default` là annotation của JSON Schema, không tự điền dữ liệu: adapter phải áp mặc định đã được lead chốt rồi đổi array thành tuple cho DTO. Kiểm bằng `chuan_dinh_danh` vẫn chạy ngay cả khi chỉ Local (A:1246); giới hạn 500 trên nhánh Cloud giữ đúng vị trí gốc. Không chuyển ngầm thành giới hạn đầu vào chung hoặc từ chối các mục nguồn vốn bỏ qua.

Ví dụ DEMO, không chứa dữ liệu thật; M9 đặt cờ chỉ Local và không đưa tiền/ngày vào danh sách định danh:

```json
{
  "loai_viec": "HOI_DAP_VAY",
  "van_ban": "Hợp đồng DEMO-VAY-001: Công ty DEMO A vay Công ty DEMO B. Lãi suất 8%/năm. Số tiền 100000000 VND. Ngày ký 2026-10-01.",
  "chi_dan": "Trích lãi suất; mỗi trường phải có trích dẫn nguyên văn.",
  "truong": ["lai_suat"],
  "dinh_danh_da_biet": [
    "Công ty DEMO A",
    ["Công ty DEMO B", "CONG_TY"],
    {"gia_tri": "DEMO-VAY-001", "nhom": "HOP_DONG"}
  ],
  "chi_cuc_bo": true
}
```

## 4. “Thay đổi” đề xuất cho CHUAN-CORE-SDK v1.1

Đoạn 4 dòng dưới đây để lead đưa vào chuẩn **sau khi chốt các điểm Cần lead và Opus review đạt**; không ghi nhận rằng chuẩn v1.1 đã được sửa trong lát này:

- Bổ sung schema đầu vào `ai.hoi@1` từ năm trường `YeuCauAI`: `loai_viec`, `van_ban`, `chi_dan`, `truong`, `dinh_danh_da_biet`; dùng `$ref` URN kiểu chung, ngữ cảnh danh tính/pháp nhân/việc do Core gắn.
- Bổ sung cờ `chi_cuc_bo: boolean`, mặc định `false`; `true` bảo đảm 0 lời gọi Cloud cả khi Local lỗi, không chắc hoặc được chọn kiểm xác suất; `false` không tự bật Cloud.
- Ánh xạ chỉ Local sang `cloud_bat=False` bằng instance theo request, không đổi trạng thái instance chung; M9 bắt buộc đặt `true` theo CD-015.
- Giữ nguyên TL 48: Local luôn có đường sử dụng; Cloud chỉ qua Mask v2, không gửi khi còn sót định danh, giữ tiền/ngày; không đổi lịch/ngưỡng kiểm xác suất.

## 5. Bảng truy vết và điểm chưa chốt

| Quy tắc / biểu diễn | Dòng T48 | Dòng E1 | Dòng mã gốc / chuẩn | Kết luận |
|---|---|---|---|---|
| Một cổng AI; Local luôn có đường; Cloud có điều kiện qua Mask v2, còn sót thì không gửi | 18–20, 60–63 | 140, 153, 164 | A:7–16, 1149–1176 | Giữ quyết định đã có; không tạo client/bộ che mới. |
| Năm trường đầu vào và required/default của DTO | 60 nói văn bản + định danh đã biết; không định nghĩa DTO/JSON | 144, 152 | A:275–289, 1241–1246 | **Cần lead** xác nhận schema tuần tự hóa; nguồn cho từng trường tại §1. |
| Ngữ cảnh danh tính, pháp nhân, việc do Core gắn; không nhận từ payload | Không quy định cấu trúc ngữ cảnh Core | 144 | A:290–292; SDK:1048–1049 | Giữ ràng buộc E1; không suy ra quyền từ payload. |
| Tên `chi_cuc_bo`, kiểu boolean, default `false` | 20 có công tắc Cloud; không đặt cờ request/default | 144, 168 còn ghi chờ tên/schema | A:117–118 là default của **cloud_bat**, không phải default cờ request | **Cần lead** chốt tên/default đề xuất theo CD-041 mục 3 do Anh giao. |
| `true` chặn cả ba lý do gọi Cloud | 22 liệt kê ba lý do; không mô tả cờ request | 144, 177–178 | A:1033–1035, 1149–1152, 1236–1258 | Giữ yêu cầu 0 Cloud đã có ở E1, không tạo ngoại lệ mới. |
| Instance riêng theo request, `cloud_bat=False`; không đổi cấu hình chung | 20 có công tắc; không nêu cơ chế instance | 154, 178, 195 | A:988–1000, 1033–1035, 1149–1150 | Giữ cách bọc đã giao; không sửa mã gốc. |
| `false` không bật Cloud, không vượt cấm Cloud theo loại việc | 20, 22, 24 | 152, 154, 164 | A:82–101, 117–118, 1151–1155 | Giữ công tắc và định tuyến gốc. |
| M9 phải chỉ Local | Không nêu M9/CD-015 | 144 | A:93 (`HOI_DAP_VAY`, Cloud=False) | Nghĩa vụ theo CD-015 do giao việc cung cấp; không khẳng định đã đọc CD-015 độc lập, không mở rộng module bắt buộc. |
| Các dạng định danh, chuẩn hóa, 2–300 ký tự, 500 mục sau chuẩn hóa | 21, 60 nói loại dữ liệu/định danh; không chốt cấu trúc và con số | 144, 152, 164 | A:281–283, 909–940, 1158–1160 | Giữ thuật toán/giới hạn nguồn; **Cần lead** xác nhận dạng JSON chuỗi/cặp/object và việc không đưa dung nạp ép kiểu vào schema. |
| Không che tiền/ngày; chỉ dẫn, trường và văn bản qua Mask trước Cloud | 20–21, 60–63 | 164 | A:279–283, 964–969, 1164 | Giữ quy tắc đã có; không thêm bộ che hay lịch che riêng. |
| Schema 2020-12, `$ref` URN kiểu chung, khóa ngoài bị chặn | Không quy định JSON Schema/URN | 144 yêu cầu schema | SDK:883–887, 997–1003, 1044–1055; K:2–18 | Theo chuẩn đã có; **Cần lead** chốt tên/URN `hoi_ai.v1`, manifest và phạm vi payload trước đăng ký. |
| Không đặt giới hạn văn bản, enum nhóm hoặc lịch/ngưỡng kiểm mới | 23, 94 còn chờ con số lịch kiểm | 164 | A:83, 131–134, 930–940 | Không tự chốt; mọi yêu cầu thêm giới hạn/đổi lịch là **Cần lead**, ngoài quyết định lát này. |
| Opus review và ghi chuẩn SDK v1.1 | Không quy định bước SDK v1.1 | 138 yêu cầu Opus review trước lập trình | Giao việc hiện tại của Anh (CD-041 mục 3) | Chưa review; §4 chỉ là nội dung đề xuất, chưa sửa chuẩn. |

**Điều kiện bàn giao tiếp:** lead giải quyết các dòng **Cần lead**, nhận Opus review và cập nhật chuẩn v1.1. Chưa dùng bản đề xuất này để tự công bố contract đã duyệt hoặc mở lập trình AI-1b/AI-2. Ca kiểm triển khai cần giữ theo E1:177–178: 0 Cloud khi chỉ Local trong cả ba tình huống và hai request khác cờ không ảnh hưởng nhau; lát tài liệu này chưa chạy engine/dịch vụ.

## 6. Lead chốt (31/10/2026, theo CD-041 mục 3 — sau review Opus Đạt)

Review Opus: Đạt, không có điểm Chặn. Schema hợp lệ Draft 2020-12, `$ref` URN giải offline, ví dụ DEMO đạt, 8 ca âm bị bác đúng. Không có quyết định mới ngoài TL 48.

1. **Năm trường đầu vào:** chốt theo bảng §1, chuyển 1-1 từ `YeuCauAI`. Danh tính / pháp nhân / việc do Core gắn.
   - Schema bác `dinh_danh_da_biet=null`. Mã gốc nhận `None` (A:920), nên đây là chỗ schema chặt hơn nguồn — cố ý, theo hướng an toàn.
2. **Cờ:** `chi_cuc_bo: boolean`, mặc định `false`. Mặc định `true` sẽ là quy tắc mới ngoài TL 48 nên không chọn; công tắc toàn cục `cloud_bat` vẫn tắt sẵn.
   - Bắt buộc `true` với **M9** (CD-015 mục 2: không gửi Cloud, kể cả qua Mask v2) và **`mau_demo`** (GIAO-ENGINE-1 dòng 172).
   - **Cơ chế bảo đảm:** lead grep ở cổng kiểm soát mọi lời gọi `ai.hoi@1` của M9; lát AI-2 có ca test "M9 luôn gửi `chi_cuc_bo=true`".
3. **Contract:** `hoi_ai.v1` (`urn:ktt:contract:hoi_ai.v1`, bản `1.0.0`, không có vỏ `vo_noi_dung`). Đây là contract kỹ thuật thứ 10 do Core sở hữu (SDK §3.10.4), không cần Anh duyệt như contract nghiệp vụ.
   - Manifest `e_hoi_ai` khai capability `ai.hoi@1` với `dau_vao: hoi_ai.v1`, `dau_ra: tra_loi_ai.v1`.
   - Lát AI-2 đăng ký `hoi_ai.v1` vào `ky_thuat.json` và `CONTRACT-DU-LIEU.md`, sửa test đếm 9 contract.
4. **Object định danh:** bắt buộc cả `gia_tri` và `nhom` (`nhom` được rỗng); không mở thêm dạng ngầm của nguồn.
5. **Không thêm giới hạn hay lịch kiểm.** Đổi lịch / ngưỡng kiểm xác suất **phải hỏi Anh** (TL 48 §1.6 còn "CẦN ANH XÁC NHẬN").
6. **Đã biết, không đổi:** khi chỉ Local, nhật ký ghi lý do `CLOUD_TAT` giống công tắc toàn cục tắt, nên kiểm toán không phân biệt được hai lý do.

**Mở lập trình:** AI-1b (manifest + schema) và AI-2 (adapter chỉ Local) giao được theo bản chốt này.
