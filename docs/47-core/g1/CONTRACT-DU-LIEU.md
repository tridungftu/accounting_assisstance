# CONTRACT-DU-LIEU.md

**Trạng thái:** Nháp G1c-2 để duyệt; chỉ tài liệu, chưa triển khai.  
**Phạm vi:** Bảy contract dữ liệu, hai contract API, hai schema manifest chính thức (§15), ví dụ DEMO và bộ kiểm tuân thủ; JSON Schema draft 2020-12. Đây là thiết kế đích, không khẳng định đã triển khai.

**CD-031 — JSON hai lớp:** dữ liệu trao đổi là **JSON**; JSON Schema là bản mô tả gói JSON phải có những thông tin gì để Core kiểm tự động. **Lớp kỹ thuật** do Core định nghĩa, gồm các contract hiện có tại §4–12: tệp, văn bản tài liệu, bảng, tham số, nội dung đã che, trả lời AI, hóa đơn đọc từ XML, lỗi và việc. **Lớp nghiệp vụ** do module sở hữu dữ liệu định nghĩa, Anh duyệt trước kích hoạt; danh mục, nguồn trường và ví dụ đầy đủ tại `docs/47-core/g1/CONTRACT-NGHIEP-VU.md` (**đang soạn**). Hai lớp cùng trao đổi JSON và được kiểm bằng JSON Schema; bộ contract kỹ thuật không thay thế mô tả đầy đủ nghiệp vụ.

## 1. Căn cứ và nguyên tắc

Danh sách bảy contract theo `../55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:33`. Yêu cầu JSON Schema thực, nguồn tạo kết quả, phiên bản và trạng thái duyệt theo `../54-ke-hoach-core-database-api-v1.md:140`.

Tên trường mới dùng tiếng Việt không dấu. Giữ các định danh kỹ thuật đã thống nhất như `$id`, `$schema`, `contract`, `revision`, `request_id`; căn cứ quy ước tên tại `../54-ke-hoach-core-database-api-v1.md:392` và nháp API tại `docs/47-core/g1/DAC-TA-API.md:28`.

Đây là **contract trao đổi qua Core**, không thay thế DTO nội bộ đang chạy:

- Giữ kiểm kiểu, tính bất biến đầu vào và bằng chứng của `Engine.chay`; adapter bổ sung kiểm JSON Schema tại biên trao đổi. Căn cứ: `src/kho_tri_thuc/ha_tang/engine.py:165`.
- Giữ tra cứu đúng mã và phiên bản, không tự chọn bản mới nhất. Căn cứ: `src/kho_tri_thuc/ha_tang/danh_ba_engine.py:16`, `src/kho_tri_thuc/ha_tang/danh_ba_engine.py:33`.
- Giữ một cổng AI/OCR được tiêm; không tạo cổng hoặc bộ che khác. Căn cứ: `src/kho_tri_thuc/ha_tang/engine_cong.py:1`, `src/kho_tri_thuc/ha_tang/engine_cong.py:154`.
- Engine không có login CSDL; module gọi chức năng chung qua hàm/API Core. Cơ chế login, mã phiên bí mật và quyền thực hiện **theo phiếu CSDL/API**; yêu cầu rà soát tại `docs/47-core/g1/RV-G1A-OPUS.md:41`.

Các JSON Schema dưới đây là nội dung đề xuất để lead lưu thành tài nguyên schema sau duyệt; lát này không tạo tệp.

## 2. Cách đăng ký và kiểm schema

Mỗi `$id` là một URN ổn định. Bộ kiểm đăng ký toàn bộ schema vào registry cục bộ, giải quyết `$ref` bằng registry; không tải schema qua mạng.

| Contract | `$id` | Phiên bản cấu trúc |
|---|---|---|
| Dùng chung | `urn:ktt:contract:chung.v1` | `1.0.0` |
| `tham_chieu_tep.v1` | `urn:ktt:contract:tham_chieu_tep.v1` | `1.0.0` |
| `van_ban_tai_lieu.v1` | `urn:ktt:contract:van_ban_tai_lieu.v1` | `1.0.0` |
| `du_lieu_bang.v1` | `urn:ktt:contract:du_lieu_bang.v1` | `1.0.0` |
| `tham_so.v1` | `urn:ktt:contract:tham_so.v1` | `1.0.0` |
| `noi_dung_da_che.v1` | `urn:ktt:contract:noi_dung_da_che.v1` | `1.0.0` |
| `tra_loi_ai.v1` | `urn:ktt:contract:tra_loi_ai.v1` | `1.0.0` |
| `hoa_don.v1` | `urn:ktt:contract:hoa_don.v1` | `1.0.0` |
| `loi_chuan.v1` | `urn:ktt:contract:loi_chuan.v1` | `1.0.0` |
| `viec.v1` | `urn:ktt:contract:viec.v1` | `1.0.0` |

Quy tắc bắt buộc:

1. Kiểm schema bằng meta-schema draft 2020-12 trước khi đăng ký.
2. Bật kiểm `format` cho `uuid`, `date`, `date-time`; không chỉ coi `format` là annotation.
3. Từ chối trường ngoài khai báo, sai kiểu, giá trị không hữu hạn và khóa JSON trùng nhau. Khóa trùng phải bị chặn ở bước đọc JSON.
4. Kiểm đầu vào trước tác động; kiểm đầu ra trước lưu hoặc trả người gọi.
5. Ghim chính xác `$id` + phiên bản contract, engine và adapter theo lần chạy/manifest. Mỗi contract tự đặt hằng `phien_ban`; phần vỏ chung chỉ kiểm kiểu. **Mọi thay đổi schema đã phát hành, kể cả thêm trường tùy chọn, tạo `$id` mới** và hằng phiên bản mới tại contract đó; không thay schema dưới cùng `$id`. Quy ước tài nguyên mới: `urn:ktt:contract:<ten>.v<major>:<semver>` (ví dụ `urn:ktt:contract:tra_loi_ai.v1:1.1.0`); giữ các ID 1.0.0 trong bảng cho lần phát hành đầu. Bên phát trả đúng bản bên nhận đã ghim, chuyển đổi có kiểm nếu hỗ trợ; không có bản khớp thì từ chối đăng ký/kích hoạt, không gửi ngầm bản mới. `unevaluatedProperties:false` vẫn áp dụng; nâng một contract không sửa vỏ chung hoặc các contract khác. Vòng 2 chưa phát hành nên hiệu chỉnh tại các ID nháp hiện tại. **Bổ sung lead sau Opus vòng 2:** mã contract ghi không kèm `:<semver>` chỉ bản 1.0.0 phát hành đầu, không hiểu là bản mới nhất; từ bản thứ hai, manifest và lần chạy phải ghi đủ `<ten>.v<major>:<semver>`.
6. Schema hợp lệ không chứng minh quyền truy cập, dẫn chứng đúng hay kết quả đã được duyệt. Các kiểm này thuộc lớp ngữ nghĩa và quyền của Core.

### 2.1. Metadata kết quả do Core quản lý

Sáu contract nội dung kế thừa phần vỏ gồm `contract`, `phien_ban`, `revision`, `nguon_tep_ids`. Metadata kết quả đầy đủ — pháp nhân, module/engine/function tạo kết quả, phiên bản, việc/bước/lần thử, biến thể, trạng thái duyệt và retention — được lưu hoặc tham chiếu ở Core, **theo phiếu CSDL/API**.

Cách này phù hợp API vòng 2 trả metadata kết quả, nội dung tải qua tệp: `docs/47-core/g1/DAC-TA-API.md:144`, `docs/47-core/g1/DAC-TA-API.md:1832`.

Core phải đối chiếu metadata với nội dung:

- `contract`, `revision`, `nguon_tep_ids` phải khớp.
- Mọi ID nguồn phải thuộc phạm vi được phép.
- Engine không được tự cấp pháp nhân hoặc trạng thái `da_duyet`.
- Core tự gắn module/engine/function/version, việc/bước/lần thử từ instance và lease đã xác minh; không nhận provenance tự khai của module làm bằng chứng OCR. `nguon_tep_ids`/dẫn chứng chỉ là tham chiếu phải kiểm quyền/hash/revision, không tạo quyền hoặc danh tính nguồn (SDK §3 `ket_qua`).
- Tệp phản hồi nguồn, tệp gốc và tệp nội dung chuẩn có ID riêng; không đồng nhất các mã băm của chúng.
- Tham chiếu tệp có thể trỏ tới vùng tạm có hạn dùng. Không mặc định lưu bền dữ liệu RAM-only.

### 2.2. Tiền, ngày và dữ liệu chưa xác định

- Tiền chuẩn có `gia_tri` là chuỗi decimal và `don_vi_tien`; không dùng JSON number.
- Miền tiền khớp API: tối đa 18 chữ số phần nguyên, 6 chữ số thập phân. Scale và quy tắc làm tròn theo nghiệp vụ/phiếu CSDL. Căn cứ: `docs/47-core/g1/DAC-TA-API.md:1666`.
- Giá trị decimal nguồn của XML được giữ riêng, không ép vào miền tiền chuẩn và không tự làm tròn.
- Ngày nghiệp vụ là `YYYY-MM-DD`; thời điểm response là RFC 3339 UTC, kết thúc bằng `Z`.
- `null`, chưa đọc được, thiếu, chuỗi rỗng và số `0` mang nghĩa khác nhau.
- Không suy đơn vị tiền tệ, thuế suất, tỷ giá hoặc đơn vị đo từ giao diện.

## 3. Schema dùng chung

Tài nguyên `chung.v1` cung cấp kiểu dữ liệu và phần vỏ; không phải contract nghiệp vụ thứ tám.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:chung.v1",
  "title": "chung.v1",
  "$comment": "Phien ban 1.0.0",
  "$defs": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "chuoi": {
      "type": "string",
      "minLength": 1
    },
    "ma": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]{0,31}$"
    },
    "sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "ngay": {
      "type": "string",
      "format": "date",
      "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    },
    "thoi_diem": {
      "type": "string",
      "format": "date-time",
      "pattern": "Z$"
    },
    "thap_phan": {
      "type": "string",
      "pattern": "^-?(0|[1-9][0-9]*)(\\.[0-9]+)?$"
    },
    "tien": {
      "type": "object",
      "additionalProperties": false,
      "required": ["gia_tri", "don_vi_tien"],
      "properties": {
        "gia_tri": {
          "type": "string",
          "pattern": "^-?(0|[1-9][0-9]{0,17})(\\.[0-9]{1,6})?$"
        },
        "don_vi_tien": {
          "type": "string",
          "pattern": "^[A-Z]{3}$"
        }
      }
    },
    "vo_noi_dung": {
      "type": "object",
      "required": ["contract", "phien_ban", "revision", "nguon_tep_ids"],
      "properties": {
        "contract": {"type": "string"},
        "phien_ban": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
        "revision": {"type": "integer", "minimum": 1},
        "nguon_tep_ids": {
          "type": "array",
          "minItems": 1,
          "uniqueItems": true,
          "items": {"$ref": "#/$defs/id"}
        }
      }
    },
    "vi_tri": {
      "type": "object",
      "additionalProperties": false,
      "required": ["tep_id", "dinh_vi"],
      "properties": {
        "tep_id": {"$ref": "#/$defs/id"},
        "dinh_vi": {"$ref": "#/$defs/chuoi"},
        "trang": {"type": "integer", "minimum": 1},
        "bbox": {
          "type": "array",
          "minItems": 4,
          "maxItems": 4,
          "items": {"type": "number", "minimum": 0}
        },
        "khung_toa_do": {
          "type": "object",
          "additionalProperties": false,
          "required": ["don_vi", "rong", "cao"],
          "properties": {
            "don_vi": {"enum": ["pdf_point", "pixel"]},
            "rong": {"type": "number", "exclusiveMinimum": 0},
            "cao": {"type": "number", "exclusiveMinimum": 0}
          }
        }
      },
      "dependentRequired": {
        "bbox": ["khung_toa_do"]
      }
    },
    "dan_chung": {
      "type": "object",
      "additionalProperties": false,
      "required": ["vi_tri", "trich_dan"],
      "properties": {
        "vi_tri": {"$ref": "#/$defs/vi_tri"},
        "trich_dan": {"$ref": "#/$defs/chuoi"}
      }
    },
    "gia_tri": {
      "oneOf": [
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["kieu", "gia_tri"],
          "properties": {
            "kieu": {"const": "van_ban"},
            "gia_tri": {"type": "string"}
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["kieu", "gia_tri", "don_vi"],
          "properties": {
            "kieu": {"const": "so"},
            "gia_tri": {"$ref": "#/$defs/thap_phan"},
            "don_vi": {"type": ["string", "null"], "minLength": 1}
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["kieu", "gia_tri", "don_vi_tien"],
          "properties": {
            "kieu": {"const": "tien"},
            "gia_tri": {
              "$ref": "#/$defs/tien/properties/gia_tri"
            },
            "don_vi_tien": {
              "$ref": "#/$defs/tien/properties/don_vi_tien"
            }
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["kieu", "gia_tri"],
          "properties": {
            "kieu": {"const": "ngay"},
            "gia_tri": {"$ref": "#/$defs/ngay"}
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["kieu", "gia_tri"],
          "properties": {
            "kieu": {"const": "logic"},
            "gia_tri": {"type": "boolean"}
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["kieu", "ly_do"],
          "properties": {
            "kieu": {"const": "chua_ro"},
            "ly_do": {"$ref": "#/$defs/chuoi"}
          }
        }
      ]
    }
  }
}
```

`bbox` dùng thứ tự `[x0, y0, x1, y1]`. Bộ kiểm ngữ nghĩa phải kiểm `x0 ≤ x1`, `y0 ≤ y1`, tọa độ nằm trong khung và cùng hệ tọa độ nguồn. Khi chưa xác định được hệ tọa độ, chỉ cung cấp `dinh_vi`; giữ tọa độ nguồn trong phản hồi nguồn được bảo vệ, không gắn nhãn đơn vị tùy ý.

## 4. `tham_chieu_tep.v1`

Tham chiếu không chứa đường dẫn vật lý, URL engine hoặc thông tin xác thực. Có ID không đồng nghĩa được quyền tải.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:tham_chieu_tep.v1",
  "title": "tham_chieu_tep.v1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "contract", "phien_ban", "tep_id", "ten_tep",
    "mime", "kich_thuoc", "sha256", "het_han_luc"
  ],
  "properties": {
    "contract": {"const": "tham_chieu_tep.v1"},
    "phien_ban": {"const": "1.0.0"},
    "tep_id": {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
    "ten_tep": {"type": "string", "minLength": 1, "maxLength": 255},
    "mime": {
      "type": "string",
      "pattern": "^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+$"
    },
    "kich_thuoc": {
      "type": "integer",
      "minimum": 0,
      "maximum": 9007199254740991
    },
    "sha256": {"$ref": "urn:ktt:contract:chung.v1#/$defs/sha256"},
    "het_han_luc": {
      "oneOf": [
        {"$ref": "urn:ktt:contract:chung.v1#/$defs/thoi_diem"},
        {"type": "null"}
      ]
    }
  }
}
```

Ví dụ hợp lệ về cấu trúc; checksum minh họa, không phải bằng chứng của tệp thực:

```json
{
  "contract": "tham_chieu_tep.v1",
  "phien_ban": "1.0.0",
  "tep_id": "10000000-0000-4000-8000-000000000001",
  "ten_tep": "DEMO.txt",
  "mime": "text/plain",
  "kich_thuoc": 4,
  "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "het_han_luc": "2026-10-30T05:00:00Z"
}
```

Core kiểm MIME thực, kích thước, mã băm và tên tải an toàn. `het_han_luc: null` nghĩa không có mốc hết hạn trên tham chiếu này theo chính sách được duyệt; không mặc nhiên cho phép giữ vĩnh viễn.

## 5. `van_ban_tai_lieu.v1`

Đây là nội dung văn bản cùng vị trí nguồn. Trạng thái soát OCR độc lập với duyệt nghiệp vụ ở metadata Core.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:van_ban_tai_lieu.v1",
  "title": "van_ban_tai_lieu.v1",
  "allOf": [
    {"$ref": "urn:ktt:contract:chung.v1#/$defs/vo_noi_dung"}
  ],
  "type": "object",
  "unevaluatedProperties": false,
  "required": [
    "van_ban", "trang", "canh_bao", "soat_ocr",
    "da_doi_chieu", "phan_hoi_nguon_tep_id"
  ],
  "properties": {
    "contract": {"const": "van_ban_tai_lieu.v1"},
    "phien_ban": {"const": "1.0.0"},
    "van_ban": {"type": "string"},
    "trang": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["so_trang", "van_ban", "khoi"],
        "properties": {
          "so_trang": {"type": "integer", "minimum": 1},
          "van_ban": {"type": "string"},
          "khoi": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": ["ma_nguon", "van_ban", "vi_tri"],
              "properties": {
                "ma_nguon": {"type": "string", "minLength": 1},
                "van_ban": {"type": "string"},
                "vi_tri": {
                  "$ref": "urn:ktt:contract:chung.v1#/$defs/vi_tri"
                }
              }
            }
          }
        }
      }
    },
    "canh_bao": {
      "type": "array",
      "items": {"type": "string", "minLength": 1}
    },
    "soat_ocr": {
      "enum": ["can_soat", "da_soat", "khong_ap_dung"]
    },
    "da_doi_chieu": {"type": "boolean"},
    "phan_hoi_nguon_tep_id": {
      "oneOf": [
        {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
        {"type": "null"}
      ]
    }
  }
}
```

Ví dụ:

```json
{
  "contract": "van_ban_tai_lieu.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "van_ban": "DEMO hop dong",
  "trang": [
    {
      "so_trang": 1,
      "van_ban": "DEMO hop dong",
      "khoi": [
        {
          "ma_nguon": "p1-u1",
          "van_ban": "DEMO hop dong",
          "vi_tri": {
            "tep_id": "10000000-0000-4000-8000-000000000001",
            "dinh_vi": "p1-u1",
            "trang": 1
          }
        }
      ]
    }
  ],
  "canh_bao": ["DEMO: can nguoi soat"],
  "soat_ocr": "can_soat",
  "da_doi_chieu": true,
  "phan_hoi_nguon_tep_id": "10000000-0000-4000-8000-000000000002"
}
```

Số trang không trùng; mã khối duy nhất trong phạm vi tài liệu/revision. Nếu nguồn DOCX không có phân trang xác định, cho phép `trang: []`; không dựng số trang giả.

## 6. `du_lieu_bang.v1`

Bảng dùng danh sách cột, số hàng và các ô có chỉ số bắt đầu từ `0`; cách này giữ được ô gộp của OCR.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:du_lieu_bang.v1",
  "title": "du_lieu_bang.v1",
  "allOf": [
    {"$ref": "urn:ktt:contract:chung.v1#/$defs/vo_noi_dung"}
  ],
  "type": "object",
  "unevaluatedProperties": false,
  "required": ["bang", "phan_hoi_nguon_tep_id"],
  "properties": {
    "contract": {"const": "du_lieu_bang.v1"},
    "phien_ban": {"const": "1.0.0"},
    "phan_hoi_nguon_tep_id": {
      "oneOf": [
        {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
        {"type": "null"}
      ]
    },
    "bang": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "ma", "cot", "so_dong", "o", "vi_tri",
          "can_soat", "canh_bao"
        ],
        "properties": {
          "ma": {"type": "string", "minLength": 1},
          "cot": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": ["ma", "ten", "kieu", "don_vi"],
              "properties": {
                "ma": {"$ref": "urn:ktt:contract:chung.v1#/$defs/ma"},
                "ten": {"type": "string", "minLength": 1},
                "kieu": {
                  "enum": ["van_ban", "so", "tien", "ngay", "logic", "chua_ro"]
                },
                "don_vi": {"type": ["string", "null"], "minLength": 1}
              }
            }
          },
          "so_dong": {"type": "integer", "minimum": 0},
          "o": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "dong", "cot", "gop_dong", "gop_cot",
                "gia_tri", "vi_tri", "ma_vung_nguon"
              ],
              "properties": {
                "dong": {"type": "integer", "minimum": 0},
                "cot": {"type": "integer", "minimum": 0},
                "gop_dong": {"type": "integer", "minimum": 1},
                "gop_cot": {"type": "integer", "minimum": 1},
                "gia_tri": {
                  "$ref": "urn:ktt:contract:chung.v1#/$defs/gia_tri"
                },
                "vi_tri": {
                  "$ref": "urn:ktt:contract:chung.v1#/$defs/vi_tri"
                },
                "ma_vung_nguon": {
                  "type": "array",
                  "uniqueItems": true,
                  "items": {"type": "string", "minLength": 1}
                }
              }
            }
          },
          "vi_tri": {"$ref": "urn:ktt:contract:chung.v1#/$defs/vi_tri"},
          "can_soat": {"type": "boolean"},
          "canh_bao": {
            "type": "array",
            "items": {"type": "string", "minLength": 1}
          }
        }
      }
    }
  }
}
```

Ví dụ:

```json
{
  "contract": "du_lieu_bang.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "phan_hoi_nguon_tep_id": null,
  "bang": [
    {
      "ma": "DEMO_bang_1",
      "cot": [
        {"ma": "noi_dung", "ten": "DEMO noi dung", "kieu": "van_ban", "don_vi": null}
      ],
      "so_dong": 1,
      "o": [
        {
          "dong": 0,
          "cot": 0,
          "gop_dong": 1,
          "gop_cot": 1,
          "gia_tri": {"kieu": "van_ban", "gia_tri": "DEMO"},
          "vi_tri": {
            "tep_id": "10000000-0000-4000-8000-000000000001",
            "dinh_vi": "bang_1/o_0_0"
          },
          "ma_vung_nguon": []
        }
      ],
      "vi_tri": {
        "tep_id": "10000000-0000-4000-8000-000000000001",
        "dinh_vi": "bang_1"
      },
      "can_soat": false,
      "canh_bao": []
    }
  ]
}
```

Kiểm ngữ nghĩa: mã cột duy nhất; ô không vượt kích thước bảng, không chồng ô gộp; vùng chưa đọc phải có ô `chua_ro`, không tự biến thành ô rỗng. Kiểu và đơn vị của ô phải phù hợp cột khi cột đã xác định.

## 7. `tham_so.v1`

Một tham số có giá trị đã định kiểu hoặc lý do chưa xác định. Không tự chuyển mọi chuỗi nguồn thành tiền/ngày.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:tham_so.v1",
  "title": "tham_so.v1",
  "allOf": [
    {"$ref": "urn:ktt:contract:chung.v1#/$defs/vo_noi_dung"}
  ],
  "type": "object",
  "unevaluatedProperties": false,
  "required": [
    "loai_hop_dong", "danh_muc_id", "danh_muc_sha256",
    "tham_so", "phan_hoi_nguon_tep_id"
  ],
  "properties": {
    "contract": {"const": "tham_so.v1"},
    "phien_ban": {"const": "1.0.0"},
    "loai_hop_dong": {"type": "string", "minLength": 1},
    "danh_muc_id": {"type": "string", "minLength": 1},
    "danh_muc_sha256": {
      "$ref": "urn:ktt:contract:chung.v1#/$defs/sha256"
    },
    "phan_hoi_nguon_tep_id": {
      "$ref": "urn:ktt:contract:chung.v1#/$defs/id"
    },
    "tham_so": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "ma", "ten", "gia_tri", "nguyen_van",
          "dan_chung", "can_soat", "canh_bao"
        ],
        "properties": {
          "ma": {"type": "string", "minLength": 1},
          "ten": {"type": "string", "minLength": 1},
          "gia_tri": {"$ref": "urn:ktt:contract:chung.v1#/$defs/gia_tri"},
          "nguyen_van": {"type": ["string", "null"]},
          "dan_chung": {
            "type": "array",
            "items": {"$ref": "urn:ktt:contract:chung.v1#/$defs/dan_chung"}
          },
          "can_soat": {"type": "boolean"},
          "canh_bao": {
            "type": "array",
            "items": {"type": "string", "minLength": 1}
          }
        }
      }
    }
  }
}
```

Ví dụ:

```json
{
  "contract": "tham_so.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "loai_hop_dong": "XD",
  "danh_muc_id": "DEMO_XD",
  "danh_muc_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "phan_hoi_nguon_tep_id": "10000000-0000-4000-8000-000000000002",
  "tham_so": [
    {
      "ma": "GIA_TRI",
      "ten": "DEMO gia tri hop dong",
      "gia_tri": {
        "kieu": "tien",
        "gia_tri": "1000000.00",
        "don_vi_tien": "VND"
      },
      "nguyen_van": "DEMO gia tri 1000000.00 VND",
      "dan_chung": [
        {
          "vi_tri": {
            "tep_id": "10000000-0000-4000-8000-000000000001",
            "dinh_vi": "dieu_3/doan_1"
          },
          "trich_dan": "DEMO gia tri 1000000.00 VND"
        }
      ],
      "can_soat": true,
      "canh_bao": []
    }
  ]
}
```

Mã tham số phải thuộc catalog đã ghim và không trùng. Giá trị xác định phải có dẫn chứng kiểm được. Với bảng tham số E5, adapter tạo `du_lieu_bang.v1` riêng và liên kết qua metadata Core; không ép bảng thành chuỗi hay âm thầm mở rộng union v1.

## 8. `noi_dung_da_che.v1`

Contract này áp dụng cho **văn bản đã che**. Chưa công bố khả năng che tệp độc lập chỉ từ việc có schema này.

`luot_che_id` là ID Core dùng để tra lượt nội bộ; không phải `ma_luot` của Mask, không phải credential và không tự cấp quyền mở che.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:noi_dung_da_che.v1",
  "title": "noi_dung_da_che.v1",
  "allOf": [
    {"$ref": "urn:ktt:contract:chung.v1#/$defs/vo_noi_dung"}
  ],
  "type": "object",
  "unevaluatedProperties": false,
  "required": [
    "van_ban_da_che", "luot_che_id", "het_han_mo_che_luc",
    "quy_tac", "kiem_tra"
  ],
  "properties": {
    "contract": {"const": "noi_dung_da_che.v1"},
    "phien_ban": {"const": "1.0.0"},
    "van_ban_da_che": {"type": "string", "minLength": 1},
    "luot_che_id": {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
    "het_han_mo_che_luc": {
      "$ref": "urn:ktt:contract:chung.v1#/$defs/thoi_diem"
    },
    "quy_tac": {
      "oneOf": [
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["trang_thai", "ma", "revision"],
          "properties": {
            "trang_thai": {"const": "da_cong_bo"},
            "ma": {"type": "string", "minLength": 1},
            "revision": {"type": "string", "minLength": 1}
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["trang_thai", "ma", "revision"],
          "properties": {
            "trang_thai": {"const": "chua_cong_bo"},
            "ma": {"const": null},
            "revision": {"const": null}
          }
        }
      ]
    },
    "kiem_tra": {
      "type": "object",
      "additionalProperties": false,
      "required": ["danh_muc", "gui_duoc", "so_con_sot", "giu_nguyen_tien_ngay"],
      "properties": {
        "danh_muc": {"enum": ["da_mo", "da_khoa", "chua_co"]},
        "gui_duoc": {"type": "boolean"},
        "giu_nguyen_tien_ngay": {"const": true},
        "so_con_sot": {"type": "integer", "minimum": 0}
      },
      "allOf": [
        {
          "if": {
            "properties": {"gui_duoc": {"const": true}},
            "required": ["gui_duoc"]
          },
          "then": {
            "properties": {
              "danh_muc": {"const": "da_mo"},
              "so_con_sot": {"const": 0}
            }
          }
        }
      ]
    }
  }
}
```

Ví dụ:

```json
{
  "contract": "noi_dung_da_che.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "van_ban_da_che": "DEMO [CONG_TY_1] thanh toan 1000000 VND ngay 2026-10-30",
  "luot_che_id": "10000000-0000-4000-8000-000000000003",
  "het_han_mo_che_luc": "2026-10-30T04:30:00Z",
  "quy_tac": {
    "trang_thai": "chua_cong_bo",
    "ma": null,
    "revision": null
  },
  "kiem_tra": {
    "danh_muc": "da_mo",
    "gui_duoc": true,
    "giu_nguyen_tien_ngay": true,
    "so_con_sot": 0
  }
}
```

Điều kiện vận hành:

- Cổng AI kiểm lại điều kiện gửi tại thời điểm gọi; không tin cờ do module/frontend tự gửi.
- **Không che tiền/ngày:** số tiền, đơn vị tiền và ngày nghiệp vụ giữ nguyên ý nghĩa/giá trị từ nguồn đã xác minh. `kiem_tra.giu_nguyen_tien_ngay: true` bắt buộc trong schema, do cổng Core đối chiếu nguồn trước khi gắn; schema không chứng minh nội dung cờ. Mất/đổi/che các giá trị đó thì chặn Cloud, không tự đặt cờ. Ca DEMO có tiền/ngày, kể cả sát định danh cần che, tại bộ kiểm §5 (TL 48 và review Opus G1c §4).
- Không đưa bảng ánh xạ, định danh gốc hoặc `ma_luot` vào contract công khai, log hay request Cloud.
- Hết hạn hoặc mất instance Mask thì lượt không còn dùng được, dù JSON vẫn hợp lệ.
- Revision quy tắc chưa được nguồn công bố phải ghi `chua_cong_bo`; không lấy phiên bản adapter thay revision quy tắc. Kết quả đó không được quảng bá là có thể tái lập đầy đủ.
- Chỉ gửi phần nội dung đã che cần thiết qua cổng AI; không gửi nguyên envelope chứa ID nội bộ ra Cloud.
- Retention và quyền tra/mở lượt **theo phiếu CSDL/API**.

Client hiện kiểm danh mục mở, `gui_duoc`, `con_sot`, rồi nhận `ma_luot` và `van_ban_da_che`; DTO client chưa mang revision quy tắc: `src/kho_tri_thuc/tri_thuc/cong_ai.py:663`.

## 9. `tra_loi_ai.v1`

Giữ được kết quả theo từng trường của `KetQuaAI`. Không tự tổng hợp một đoạn trả lời tự do khi nguồn chỉ trả các trường.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:tra_loi_ai.v1",
  "title": "tra_loi_ai.v1",
  "allOf": [
    {"$ref": "urn:ktt:contract:chung.v1#/$defs/vo_noi_dung"},
    {
      "if": {
        "anyOf": [
          {"properties": {"duong": {"enum": ["CLOUD", "LOCAL+CLOUD"]}}, "required": ["duong"]},
          {"properties": {"truong": {"contains": {"properties": {"nguon": {"const": "CLOUD"}}, "required": ["nguon"]}}}, "required": ["truong"]},
          {"properties": {"mo_hinh": {"contains": {"properties": {"duong": {"const": "CLOUD"}}, "required": ["duong"]}}}, "required": ["mo_hinh"]}
        ]
      },
      "then": {
        "required": ["luot_che_id"],
        "properties": {
          "duong": {"enum": ["CLOUD", "LOCAL+CLOUD"]},
          "kiem_tra": {"properties": {"mo_che": {"enum": ["dat", "khong_dat"]}}}
        }
      }
    }
  ],
  "type": "object",
  "unevaluatedProperties": false,
  "required": [
    "cau_tra_loi", "truong", "duong", "mo_hinh",
    "muc", "thong_bao", "ly_do", "truong_bi_loai",
    "ma_yeu_cau_nguon", "kiem_tra"
  ],
  "properties": {
    "contract": {"const": "tra_loi_ai.v1"},
    "phien_ban": {"const": "1.0.0"},
    "luot_che_id": {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
    "cau_tra_loi": {"type": ["string", "null"]},
    "duong": {"enum": ["LOCAL", "CLOUD", "LOCAL+CLOUD", "KHONG"]},
    "muc": {"enum": ["VANG", "DO"]},
    "thong_bao": {"type": "string"},
    "ly_do": {"type": "array", "items": {"type": "string"}},
    "truong_bi_loai": {"type": "array", "items": {"type": "string"}},
    "ma_yeu_cau_nguon": {"type": "string"},
    "truong": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["ten", "gia_tri", "nguon", "gia_tri_local", "dan_chung"],
        "properties": {
          "ten": {"type": "string", "minLength": 1},
          "gia_tri": {"$ref": "urn:ktt:contract:chung.v1#/$defs/gia_tri"},
          "nguon": {"enum": ["LOCAL", "CLOUD"]},
          "gia_tri_local": {"oneOf": [
            {"$ref": "urn:ktt:contract:chung.v1#/$defs/gia_tri"},
            {"type": "null"}
          ]},
          "dan_chung": {
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "urn:ktt:contract:chung.v1#/$defs/dan_chung"}
          }
        }
      }
    },
    "mo_hinh": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["duong", "ten", "phien_ban", "can_cu"],
        "properties": {
          "duong": {"enum": ["LOCAL", "CLOUD"]},
          "ten": {"type": ["string", "null"], "minLength": 1},
          "phien_ban": {"type": ["string", "null"], "minLength": 1},
          "can_cu": {"enum": ["thuc_te", "cau_hinh", "chua_co"]}
        }
      }
    },
    "kiem_tra": {
      "type": "object",
      "additionalProperties": false,
      "required": ["trich_dan", "mo_che"],
      "properties": {
        "trich_dan": {"enum": ["dat", "khong_dat", "chua_kiem"]},
        "mo_che": {"enum": ["dat", "khong_dat", "chua_kiem", "khong_ap_dung"]}
      }
    }
  }
}
```

Ví dụ:

```json
{
  "contract": "tra_loi_ai.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "cau_tra_loi": null,
  "truong": [
    {
      "ten": "ten_hop_dong",
      "gia_tri": {"kieu": "van_ban", "gia_tri": "DEMO hop dong"},
      "nguon": "LOCAL",
      "gia_tri_local": null,
      "dan_chung": [
        {
          "vi_tri": {
            "tep_id": "10000000-0000-4000-8000-000000000001",
            "dinh_vi": "doan_1"
          },
          "trich_dan": "DEMO hop dong"
        }
      ]
    }
  ],
  "duong": "LOCAL",
  "mo_hinh": [
    {
      "duong": "LOCAL",
      "ten": "DEMO_MODEL",
      "phien_ban": null,
      "can_cu": "cau_hinh"
    }
  ],
  "muc": "VANG",
  "thong_bao": "Kết quả DEMO cần người duyệt.",
  "ly_do": [],
  "truong_bi_loai": [],
  "ma_yeu_cau_nguon": "DEMO_AI_1",
  "kiem_tra": {
    "trich_dan": "dat",
    "mo_che": "khong_ap_dung"
  }
}
```

Tên trường không trùng. Dẫn chứng phải đối chiếu đúng biến thể/revision nguồn. `can_cu: thuc_te` đòi hỏi có tên model và bằng chứng từ lượt gọi; cấu hình model không tự chứng minh model thực tế đã xử lý. Cloud mở che thất bại không được công bố thành câu trả lời đã mở che.

Có CLOUD ở đường xử lý, nguồn trường hoặc model thì bắt buộc `luot_che_id` và `kiem_tra.mo_che` ∈ `{dat, khong_dat}`; giả nhãn `LOCAL` không tránh được điều kiện schema. Core đối chiếu lượt đúng việc/pháp nhân, còn hiệu lực lúc gọi và thực sự qua Mask v2; có ID không tự cấp quyền. `khong_dat` chỉ giữ kết quả lỗi được bảo vệ để xử lý, không công bố như đã mở che. Giá trị dùng kiểu phân biệt `chung.v1#/$defs/gia_tri`, gồm tiền có đơn vị/ngày ISO/số decimal; không nhận `"1.000.000"` làm tiền hoặc đoán kiểu từ chuỗi. Adapter chuyển theo catalog trường đã ghim, không rõ kiểu thì `chua_ro`, không mất bản Local.

Các trường nguồn hiện có tại `src/kho_tri_thuc/tri_thuc/cong_ai.py:295`, `src/kho_tri_thuc/tri_thuc/cong_ai.py:304`. DTO này chưa chứa model thực thi; adapter lấy bằng chứng bổ sung từ cổng/hồ sơ lượt gọi hoặc ghi chưa có.

## 10. `hoa_don.v1`

Đây là **kết quả đọc hóa đơn**, chưa phải bằng chứng hợp lệ thuế, đủ điều kiện hạch toán hay đã ghi nhận nghiệp vụ.

Contract cung cấp phần chiếu chuẩn và tham chiếu bắt buộc tới chi tiết nguồn. Chi tiết nguồn giữ toàn bộ DTO reader dạng JSON qua `ra_json`; XML/ZIP bytes giữ bằng tham chiếu tệp riêng theo chính sách được duyệt. Căn cứ: `src/kho_tri_thuc/nguon/hoa_don_xml.py:618`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:hoa_don.v1",
  "title": "hoa_don.v1",
  "allOf": [
    {"$ref": "urn:ktt:contract:chung.v1#/$defs/vo_noi_dung"}
  ],
  "type": "object",
  "unevaluatedProperties": false,
  "required": [
    "tep_xml_id", "chi_tiet_nguon_tep_id", "profile_ref",
    "profile_document_sha256", "profile_payload_sha256",
    "dang_cau_truc", "dinh_danh_nguon", "ma_bam_noi_dung",
    "dau_hoa_don", "dong", "tong_tien",
    "van_de", "ly_do_ung_vien", "trang_thai_thue",
    "ghi_nhan_nghiep_vu"
  ],
  "properties": {
    "contract": {"const": "hoa_don.v1"},
    "phien_ban": {"const": "1.0.0"},
    "tep_xml_id": {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
    "chi_tiet_nguon_tep_id": {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
    "profile_ref": {"type": ["string", "null"], "minLength": 1},
    "profile_document_sha256": {
      "oneOf": [
        {"$ref": "urn:ktt:contract:chung.v1#/$defs/sha256"},
        {"type": "null"}
      ]
    },
    "profile_payload_sha256": {
      "oneOf": [
        {"$ref": "urn:ktt:contract:chung.v1#/$defs/sha256"},
        {"type": "null"}
      ]
    },
    "dang_cau_truc": {
      "enum": [
        "SUPPORTED_SUBSET", "UNSUPPORTED_INPUT", "XML_MALFORMED",
        "UNSUPPORTED_NAMESPACE", "UNSUPPORTED_PATH", "STRUCTURE_DUPLICATE"
      ]
    },
    "dinh_danh_nguon": {
      "type": ["array", "null"],
      "minItems": 1,
      "items": {"type": "string"}
    },
    "ma_bam_noi_dung": {
      "oneOf": [
        {"$ref": "urn:ktt:contract:chung.v1#/$defs/sha256"},
        {"type": "null"}
      ]
    },
    "dau_hoa_don": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "mau_so", "ky_hieu", "so_hoa_don", "ngay_lap",
        "don_vi_tien", "ma_so_thue_ban", "ma_so_thue_mua"
      ],
      "properties": {
        "mau_so": {"type": ["string", "null"]},
        "ky_hieu": {"type": ["string", "null"]},
        "so_hoa_don": {"type": ["string", "null"]},
        "ngay_lap": {
          "oneOf": [
            {"$ref": "urn:ktt:contract:chung.v1#/$defs/ngay"},
            {"type": "null"}
          ]
        },
        "don_vi_tien": {
          "type": ["string", "null"],
          "pattern": "^[A-Z]{3}$"
        },
        "ma_so_thue_ban": {"type": ["string", "null"]},
        "ma_so_thue_mua": {"type": ["string", "null"]}
      }
    },
    "dong": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "thu_tu_nguon", "dinh_vi", "tinh_chat", "don_vi",
          "so_luong", "don_gia", "thanh_tien", "tien_chuan", "thue_suat"
        ],
        "properties": {
          "thu_tu_nguon": {"type": "integer", "minimum": 1},
          "dinh_vi": {"type": "string", "minLength": 1},
          "tinh_chat": {
            "enum": [
              "GOODS", "PROMOTION", "DISCOUNT",
              "NOTE", "SPECIAL_GOODS", "UNKNOWN"
            ]
          },
          "don_vi": {"type": ["string", "null"]},
          "thue_suat": {
            "type": "object", "additionalProperties": false,
            "required": ["trang_thai", "gia_tri_nguon"],
            "properties": {
              "trang_thai": {"enum": ["TEXT", "ABSENT", "EMPTY", "KHONG_HOP_LE"]},
              "gia_tri_nguon": {"type": ["string", "null"], "minLength": 1}
            },
            "if": {"properties": {"trang_thai": {"const": "TEXT"}}, "required": ["trang_thai"]},
            "then": {"properties": {"gia_tri_nguon": {"type": "string"}}},
            "else": {"properties": {"gia_tri_nguon": {"const": null}}}
          },
          "so_luong": {"$ref": "#/$defs/thap_phan_nguon"},
          "don_gia": {"$ref": "#/$defs/thap_phan_nguon"},
          "thanh_tien": {"$ref": "#/$defs/thap_phan_nguon"},
          "tien_chuan": {
            "oneOf": [
              {"$ref": "urn:ktt:contract:chung.v1#/$defs/tien"},
              {"type": "null"}
            ]
          }
        }
      }
    },
    "tong_tien": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["ma", "dinh_vi", "gia_tri_nguon", "tien_chuan"],
        "properties": {
          "ma": {
            "enum": ["truoc_thue", "thue", "khong_chiu_thue", "thanh_toan"]
          },
          "dinh_vi": {"type": "string", "minLength": 1},
          "gia_tri_nguon": {"$ref": "#/$defs/thap_phan_nguon"},
          "tien_chuan": {
            "oneOf": [
              {"$ref": "urn:ktt:contract:chung.v1#/$defs/tien"},
              {"type": "null"}
            ]
          }
        }
      }
    },
    "van_de": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["ma", "thong_diep", "dinh_vi", "muc"],
        "properties": {
          "ma": {"type": "string", "minLength": 1},
          "thong_diep": {"type": "string", "minLength": 1},
          "dinh_vi": {"type": "string", "minLength": 1},
          "muc": {"enum": ["ERROR", "WARNING"]}
        }
      }
    },
    "ly_do_ung_vien": {
      "type": "array",
      "items": {"type": "string", "minLength": 1}
    },
    "trang_thai_thue": {"const": "UNKNOWN"},
    "ghi_nhan_nghiep_vu": {"const": "NOT_PERFORMED"}
  },
  "$defs": {
    "thap_phan_nguon": {
      "type": "object",
      "additionalProperties": false,
      "required": ["trang_thai", "gia_tri"],
      "properties": {
        "trang_thai": {
          "enum": [
            "EXACT", "PRECISION_UNDECLARED", "ABSENT",
            "EMPTY", "INVALID", "OVER_DOMAIN"
          ]
        },
        "gia_tri": {
          "oneOf": [
            {
              "type": "string",
              "pattern": "^-?[0-9]+(\\.[0-9]+)?$"
            },
            {"type": "null"}
          ]
        }
      },
      "allOf": [
        {
          "if": {
            "properties": {
              "trang_thai": {"enum": ["EXACT", "PRECISION_UNDECLARED"]}
            },
            "required": ["trang_thai"]
          },
          "then": {
            "properties": {"gia_tri": {"type": "string"}}
          },
          "else": {
            "properties": {"gia_tri": {"const": null}}
          }
        }
      ]
    }
  }
}
```

Ví dụ:

```json
{
  "contract": "hoa_don.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "tep_xml_id": "10000000-0000-4000-8000-000000000001",
  "chi_tiet_nguon_tep_id": "10000000-0000-4000-8000-000000000002",
  "profile_ref": "DEMO_M2_XML_QD1271_FIELDS_V1",
  "profile_document_sha256": null,
  "profile_payload_sha256": null,
  "dang_cau_truc": "SUPPORTED_SUBSET",
  "dinh_danh_nguon": null,
  "ma_bam_noi_dung": null,
  "dau_hoa_don": {
    "mau_so": "1",
    "ky_hieu": "DEMO",
    "so_hoa_don": "000001",
    "ngay_lap": "2026-10-30",
    "don_vi_tien": "VND",
    "ma_so_thue_ban": "0000000001",
    "ma_so_thue_mua": "0000000002"
  },
  "dong": [
    {
      "thu_tu_nguon": 1,
      "dinh_vi": "/HDon/DLHDon/NDHDon/DSHHDVu/HHDVu[1]",
      "tinh_chat": "GOODS",
      "don_vi": "CAI",
      "thue_suat": {"trang_thai": "TEXT", "gia_tri_nguon": "10%"},
      "so_luong": {"trang_thai": "EXACT", "gia_tri": "1"},
      "don_gia": {"trang_thai": "EXACT", "gia_tri": "100000"},
      "thanh_tien": {
        "trang_thai": "PRECISION_UNDECLARED",
        "gia_tri": "100000"
      },
      "tien_chuan": {"gia_tri": "100000", "don_vi_tien": "VND"}
    }
  ],
  "tong_tien": [],
  "van_de": [],
  "ly_do_ung_vien": ["DEMO_CHUA_DU_CONTEXT"],
  "trang_thai_thue": "UNKNOWN",
  "ghi_nhan_nghiep_vu": "NOT_PERFORMED"
}
```

Quy tắc chuyển đổi:

- Trường đầu hóa đơn chỉ chiếu khi có một occurrence rõ ràng; thiếu, trùng, mixed content hoặc giá trị không hợp lệ thì trả `null`, giữ nguyên chi tiết nguồn và issue.
- Không chọn occurrence đầu/cuối; không sửa lexeme nguồn. Reader đã phân biệt `ABSENT`, `EMPTY`, `TEXT`: `src/kho_tri_thuc/nguon/hoa_don_xml.py:221`, `src/kho_tri_thuc/nguon/hoa_don_xml.py:252`.
- Decimal nguồn giữ exact text theo `DecimalFact`; không chuyển qua float. Căn cứ: `src/kho_tri_thuc/nguon/hoa_don_xml.py:430`.
- `tien_chuan` chỉ được tạo khi giá trị, đơn vị và miền biểu diễn đều xác định. Vượt miền thì trả `null`, thêm issue; giữ `gia_tri_nguon`.
- `dong[].thue_suat` lấy occurrence `TSuat` rõ ràng từ `InvoiceLine.fields`, giữ lexeme, gồm cả ký hiệu không chịu thuế/không kê khai; không suy từ tổng hoặc mặc định thiếu thành 0. `TEXT/ABSENT/EMPTY` theo nguồn; nhiều occurrence/mixed content hoặc không thể chiếu thì `KHONG_HOP_LE` + issue, chi tiết nguồn giữ nguyên (`src/kho_tri_thuc/nguon/hoa_don_xml.py:45`, `:517`).
- `tong_tien[].ma=truoc_thue` ánh xạ `TgTCThue`, gồm cả phần không chịu thuế; **cấm coi là cơ sở chịu thuế** (`src/kho_tri_thuc/nguon/hoa_don_xml.py:459`). Muốn tính thuế phải dùng thành phần nguồn/profile nghiệp vụ được duyệt, không lấy tổng này nhân thuế suất.
- `dong[].tien_chuan` giữ giá trị nguồn, **không mã hóa dấu tác động nghiệp vụ**. `TChat=3` là `DISCOUNT` (`src/kho_tri_thuc/nguon/hoa_don_xml.py:48`); không cộng các dòng hoặc đổi dấu tùy ý để dựng tổng. Tổng hóa đơn chỉ lấy `tong_tien` đã chiếu từ nguồn; thiếu thì giữ thiếu, không bù bằng tổng dòng. Đối chiếu có thể báo lệch nhưng không thay số nguồn.
- Không dùng `thu_tu_nguon` hoặc `STT` làm khóa dòng nghiệp vụ.
- Quan hệ hóa đơn, các thành phần thuế, crosswalk, coverage và mọi occurrence nằm trong `chi_tiet_nguon_tep_id`; không bỏ chúng khi tạo phần chiếu.
- ZIP không được gộp mất entry lỗi hoặc entry trùng tên. Mỗi entry XML đọc được tạo một kết quả; báo cáo gói giữ ordinal, tên, hash, trạng thái và coverage theo DTO nguồn. Contract báo cáo gói riêng nằm ngoài lát này; chưa có schema được duyệt thì không công bố capability trả báo cáo gói như đã chuẩn hóa.
- Chỉ đọc profile được kiểm chứng; không tuyên bố hỗ trợ toàn bộ XML thuế. Phạm vi reader hiện tại được nêu tại `src/kho_tri_thuc/nguon/hoa_don_xml.py:1`.

## 11. `loi_chuan.v1`

Bổ sung vì API cần dạng lỗi thống nhất: bốn trường bắt buộc và `chi_tiet` tùy chọn theo API vòng 2 §2.3; phiên bản nằm ở tài nguyên schema, không thêm `contract` vào body. Mã lỗi module/HTTP phải đăng ký trong manifest/contract; Core đối chiếu registry, sai trả 502 `PHAN_HOI_SAI_CONTRACT`.

Căn cứ: `docs/47-core/g1/DAC-TA-API.md:81`, `docs/47-core/g1/DAC-TA-API.md:1680`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:loi_chuan.v1",
  "title": "loi_chuan.v1",
  "$comment": "Phien ban 1.0.0; body theo phieu CSDL/API",
  "type": "object",
  "additionalProperties": false,
  "required": ["ma", "thong_diep", "request_id", "thu_lai_duoc"],
  "properties": {
    "ma": {
      "type": "string",
      "pattern": "^[A-Z][A-Z0-9_]{0,95}$"
    },
    "thong_diep": {
      "type": "string",
      "minLength": 1,
      "maxLength": 1000
    },
    "request_id": {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
    "thu_lai_duoc": {"type": "boolean"},
    "chi_tiet": {
      "type": "array", "maxItems": 100,
      "items": {
        "type": "object", "additionalProperties": false,
        "required": ["truong", "ma"],
        "properties": {
          "truong": {"type": "string", "minLength": 1, "maxLength": 255},
          "ma": {"type": "string", "pattern": "^[A-Z][A-Z0-9_]{0,95}$"}
        }
      }
    }
  }
}
```

Ví dụ:

```json
{
  "ma": "DEMO_GHI_CHU_KHONG_HOP_LE",
  "thong_diep": "Ghi chú DEMO chưa hợp lệ. Anh kiểm tra ô được đánh dấu.",
  "request_id": "10000000-0000-4000-8000-000000000099",
  "thu_lai_duoc": false,
  "chi_tiet": [{"truong": "ghi_chu", "ma": "BAT_BUOC"}]
}
```

Không đưa SQL, DSN, khóa, cookie, header xác thực, đường dẫn vật lý hoặc nội dung tài liệu vào thông điệp. Adapter chỉ ánh xạ lỗi đã biết; lỗi lập trình không được đổi thành kết quả nghiệp vụ thành công.

`chi_tiet[].truong` chỉ là đường trường đã khai trong input schema của operation, `ma` thuộc danh mục lỗi trường đã đăng ký (ví dụ `BAT_BUOC`); không chứa giá trị, bản nháp hoặc nội dung nguồn. JS SDK dùng đường trường để gắn lỗi từng ô, không phản chiếu input.

## 12. `viec.v1`

Bổ sung vì API cần biên nhận việc lâu và trạng thái polling. Giữ cấu trúc API vòng 2 tại `docs/47-core/g1/DAC-TA-API.md:2053`, `:2061`; không bổ sung token lease hay mã ủy nhiệm vào response.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:viec.v1",
  "title": "viec.v1",
  "$comment": "Phien ban 1.0.0; body theo phieu CSDL/API",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id", "phap_nhan_id", "ma_module", "trang_thai",
    "tien_do", "ket_qua_ids", "loi", "tao_luc", "cap_nhat_luc"
  ],
  "properties": {
    "id": {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
    "phap_nhan_id": {
      "oneOf": [
        {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
        {"type": "null"}
      ]
    },
    "ma_module": {
      "type": ["string", "null"],
      "pattern": "^[a-z][a-z0-9_]{0,31}$"
    },
    "trang_thai": {"$ref": "#/$defs/trang_thai"},
    "tien_do": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
    "ket_qua_ids": {
      "type": "array",
      "maxItems": 1000,
      "uniqueItems": true,
      "items": {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"}
    },
    "loi": {
      "oneOf": [
        {"$ref": "urn:ktt:contract:loi_chuan.v1"},
        {"type": "null"}
      ]
    },
    "tao_luc": {"$ref": "urn:ktt:contract:chung.v1#/$defs/thoi_diem"},
    "cap_nhat_luc": {"$ref": "urn:ktt:contract:chung.v1#/$defs/thoi_diem"}
  },
  "$defs": {
    "trang_thai": {
      "enum": [
        "queued", "running", "waiting_input", "cancel_requested",
        "cancelled", "succeeded", "failed", "interrupted"
      ]
    },
    "da_nhan": {
      "type": "object",
      "additionalProperties": false,
      "required": ["viec_id", "trang_thai", "request_id"],
      "properties": {
        "viec_id": {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"},
        "trang_thai": {"$ref": "#/$defs/trang_thai"},
        "request_id": {"$ref": "urn:ktt:contract:chung.v1#/$defs/id"}
      }
    }
  }
}
```

Ví dụ polling:

```json
{
  "id": "10000000-0000-4000-8000-000000000010",
  "phap_nhan_id": "10000000-0000-4000-8000-000000000020",
  "ma_module": "demo",
  "trang_thai": "running",
  "tien_do": 25,
  "ket_qua_ids": [],
  "loi": null,
  "tao_luc": "2026-10-30T04:00:00Z",
  "cap_nhat_luc": "2026-10-30T04:00:05Z"
}
```

Ví dụ biên nhận theo `urn:ktt:contract:viec.v1#/$defs/da_nhan`:

```json
{
  "viec_id": "10000000-0000-4000-8000-000000000010",
  "trang_thai": "queued",
  "request_id": "10000000-0000-4000-8000-000000000099"
}
```

Biên nhận HTTP 202 chỉ trả sau commit; header và đường dẫn theo phiếu CSDL/API. Không dùng schema polling để kiểm biên nhận.

Không ánh xạ chỉ theo tên trạng thái:

| Nguồn hiện có | Trạng thái công khai đề xuất | Điều kiện |
|---|---|---|
| Hàng việc `CHO` | `queued` | Đang chờ thực thi/thử lại |
| Hàng việc `DANG_CHAY` | `running` hoặc `cancel_requested` | Phân biệt cờ yêu cầu dừng |
| Hàng việc `XONG` | `succeeded` | Đã lưu kết quả hợp lệ |
| Hàng việc `LOI` | `failed` | Thất bại đã xác định |
| Hàng việc `DA_DUNG` | `cancelled` | Đã xác nhận dừng |
| Hàng việc `CHUA_RO` | `interrupted` | Lỗi chuẩn giải thích chưa rõ tác động; không tự thử lại |
| Engine `CHO` | Không ánh xạ cố định | Có thể cần nhập liệu, chờ readiness hoặc retry có lịch |

Hàng việc hiện có trạng thái và cách xử lý lease/tác động ngoài tại `src/kho_tri_thuc/k2/sql_hang_viec.py:35`, `src/kho_tri_thuc/k2/sql_hang_viec.py:145`. `waiting_input` và mô hình bước/lần thử là phần bổ sung, không phải trạng thái đã có sẵn của bảng hiện tại.

## 13. Đối chiếu trường với nguồn thực tế

| Contract/trường | Nguồn và phép chuyển đổi | Giới hạn phải giữ |
|---|---|---|
| `tham_chieu_tep`: ID, MIME, kích thước, hash, hết hạn | Core cấp/kiểm tại tiếp nhận. XML có `XmlRawRef` cung cấp native hash và độ dài: `src/kho_tri_thuc/nguon/hoa_don_xml.py:258`. | ID Core khác hash; không lấy tên tệp làm khóa. |
| Văn bản: `van_ban`, `trang` | OCR `text`, `pages`; model response tại `D:/GPT/OCR/mask_ocr/api.py:47`. Khảo sát: `docs/47-core/g0/KS-E.md:109`. | Phân biệt schema nguồn `1`/`2`; không giả định mọi trang đều có units. |
| Văn bản: khối, vị trí | `units.id`, `bbox`, `reference`, text đã xử lý review; nguồn tạo unit tại `D:/GPT/OCR/mask_ocr/structured.py:126`. | Không chọn tùy ý một nhánh Tesseract/VietOCR khi còn xung đột. |
| Văn bản: soát, đối chiếu | `review`, `comparison`; giữ revision nguồn trong snapshot. KS-E phân biệt `final` với duyệt nghiệp vụ: `docs/47-core/g0/KS-E.md:110`. | `final` không cấp `da_duyet`; hai engine đồng ý chưa chứng minh đúng. |
| OCR-1 → văn bản | `EngineOCR` trả DOCX bytes; Core đăng ký tệp rồi adapter đọc DOCX để tạo text/bảng khi capability hỗ trợ: `src/kho_tri_thuc/ha_tang/engine_cong.py:127`. | Không mô tả wrapper hiện tại đã trả JSON văn bản hoặc bảng. |
| Bảng: hàng/cột/ô gộp/vùng nguồn | OCR `rows`, `cols`, `cells`, `rowspan`, `colspan`, `bbox`, `unit_ids`: `D:/GPT/OCR/mask_ocr/layout.py:28`; đối chiếu `docs/47-core/g0/KS-E.md:135`. | OCR chưa chứng minh suy kiểu/đơn vị đầy đủ. Ban đầu dùng text hoặc `chua_ro`; giữ cảnh báo. |
| Mask: nội dung, lượt, điều kiện gửi | `van_ban_da_che`, `ma_luot`, `gui_duoc`, `con_sot`, `danh_muc`: `src/kho_tri_thuc/tri_thuc/cong_ai.py:663`; KS-D tại `docs/47-core/g0/KS-D.md:47`. | Core ánh xạ lượt thành ID nội bộ, giới hạn hạn dùng. Không tự tạo revision quy tắc. |
| Tham số #6: mã/tên/giá trị/đơn vị/dẫn chứng | Các khóa nguồn gồm `ma`, `nhom`, `tham_so`, `gia_tri`, `don_vi`, `dieu_khoan`, `trich_dan`, `ghi_chu`, `kiem_tra`, `vi_tri_do_duoc`: `src/kho_tri_thuc/nguon/trich_chung_6.py:49`. | Giữ phản hồi nguồn cho các trường chưa chiếu; không bỏ ghi chú hoặc kết luận kiểm. |
| Tham số #6: catalog và nguồn | Common request ghim loại/catalog/hash; client trả raw, hash và snapshot: `src/kho_tri_thuc/nguon/trich_chung_6.py:117`, `src/kho_tri_thuc/nguon/trich_chung_6.py:536`. | Chỉ chuyển đổi khi niêm phong và nguồn khớp. Không tự chạy lại ý định chưa rõ. |
| Tham số E5 | Kiểu text/số/ngày/tiền/bảng và kiểm ngày thực tại `src/kho_tri_thuc/nguon/trich_chung_6.py:151`, `src/kho_tri_thuc/nguon/trich_chung_6.py:173`. | Chuyển tên kiểu tường minh; giữ các hash theo vai trò, không băm lại rồi thay hash nguồn. |
| E1-MUA | Catalog loại mua có trong bản vá; chưa chứng minh triển khai vào nguồn: `docs/47-core/g0/KS-D.md:62`, `docs/47-core/g0/KS-D.md:63`. | Không đăng ký capability loại mua chỉ vì có schema dùng chung. |
| AI: trường, nguồn, giá trị Local, lý do | `TruongAI`, `KetQuaAI`: `src/kho_tri_thuc/tri_thuc/cong_ai.py:295`. | Model lấy từ bằng chứng lượt gọi; không suy từ DTO hoặc nhận từ frontend. |
| Hóa đơn: đầu hóa đơn | `KHMSHDon`, `KHHDon`, `SHDon`, `NLap`, `DVTTe`, MST hai bên: `src/kho_tri_thuc/nguon/hoa_don_xml.py:43`. | Giữ số hóa đơn dạng chuỗi; không mất số `0` đầu. |
| Hóa đơn: dòng/decimal | `InvoiceLine`, `DecimalFact`: `src/kho_tri_thuc/nguon/hoa_don_xml.py:497`, `src/kho_tri_thuc/nguon/hoa_don_xml.py:430`. | Không mặc định thiếu số lượng thành `0`; không suy khóa dòng từ STT. |
| Hóa đơn: tổng/thuế/quan hệ | `InvoiceMoney`, `InvoiceRelations`: `src/kho_tri_thuc/nguon/hoa_don_xml.py:456`, `src/kho_tri_thuc/nguon/hoa_don_xml.py:488`. | Giữ trong chi tiết nguồn; không nhập vào semantic digest V1 tùy ý. |
| Hóa đơn: trạng thái, hash, candidate | `InvoiceReadResult`: `src/kho_tri_thuc/nguon/hoa_don_xml.py:542`. | `UNKNOWN`, `NOT_PERFORMED` phải giữ; không tự nâng thành ghi nhận nghiệp vụ. |
| ZIP: entry/coverage | `InvoiceZipReadResult`: `src/kho_tri_thuc/nguon/hoa_don_xml.py:599`. | Coverage gói không chứng minh đủ hóa đơn của kỳ. |

### 13.1. Bảo toàn bằng chứng hiện có

`hash_du_lieu` hiện băm cây có nhãn kiểu, phân biệt bytes/chuỗi, tuple/list, Decimal và ngày giờ; đây không phải checksum trực tiếp của JSON wire. Căn cứ: `src/kho_tri_thuc/ha_tang/engine.py:91`.

Giữ riêng:

1. Hash bytes tệp nguồn.
2. Hash bằng chứng engine hiện có.
3. Hash bytes JSON contract sau serialize.
4. Hash nội dung chuyên biệt do nguồn cấp, như semantic digest hóa đơn.

Không so sánh bốn loại hash như cùng một thuật toán/ngữ nghĩa.

## 14. Điều kiện hoàn tất đặc tả

Trước khi công bố các contract:

- Chốt miền tiền, metadata, retention, mã phiên và ánh xạ trạng thái **theo phiếu CSDL/API**.
- Hai schema manifest chính thức tại §15; hai ví dụ SDK §6 và ca âm §15.3 phải được kiểm trước cài, không có schema cạnh tranh.
- Adapter phải có bảng ánh xạ source-version → contract-version và ca kiểm bảo toàn bằng chứng.
- Khả năng che tệp độc lập, báo cáo ZIP chuẩn và capability E1-MUA chỉ được công bố sau khi có schema và bằng chứng triển khai tương ứng.
- Chạy kiểm meta-schema, resolve `$ref`, toàn bộ ví dụ và ca âm trong giai đoạn được phép triển khai.

**Tình trạng vòng 2:** chỉ sửa tài liệu và kiểm JSON/schema/ví dụ offline; không chạy test ứng dụng, SQL hoặc dịch vụ. Kiểm runtime Windows/CSDL/adapter thuộc G2 sau duyệt, không suy kiểm tĩnh thành nghiệm thu.

## 15. Schema manifest chính thức — phiên bản 1.0.0

Hai tài nguyên thuộc phiếu SDK, nằm ngay trong tài liệu để không tạo tệp ngoài handoff. Registry nạp cả hai cùng các contract §2, không truy cập mạng. Ví dụ hợp lệ là hai manifest DEMO tại `DAC-TA-SDK.md` §6.1–6.2. Sau phát hành, mọi thay đổi có ID/phiên bản mới theo §2.

**CD-032 — nội dung gói bắt buộc:** mỗi module có `contract/`; `module.json.contract` liệt kê bốn nhóm `cong_bo`, `su_kien_phat`, `su_kien_nhan`, `dau_vao_nguon`. Nhóm không sử dụng là mảng rỗng; vẫn phải có thư mục và đủ bốn nhóm. Mỗi mục ghim `ma`, `phien_ban`, `module_so_huu`, đường dẫn `tep_mo_ta`, `schema` và `vi_du` trong `contract/`, có trong kiểm kê/hash gói. Thiếu thư mục, thiếu mục hoặc nội dung không hợp lệ → **không cài**.

Mỗi `tep_mo_ta` là JSON có đủ `ma`, `phien_ban`, `muc_dich`, `module_so_huu`, `module_duoc_doc` (danh sách mã module cụ thể, không wildcard), `truong`, `schema`, `vi_du`. Mỗi phần tử `truong` có `ten` tiếng Việt không dấu, `nghia`, `bat_buoc` kiểu boolean, `don_vi` (ghi rõ `khong_ap_dung` khi không có đơn vị), `nguon` (tài liệu/quyết định đã chốt hoặc trường nguồn cụ thể). Liệt kê cả trường con của cấu trúc lồng nhau. `schema` trỏ JSON Schema draft 2020-12, `vi_du` trỏ JSON DEMO đầy đủ và phải qua schema đó. Mã/phiên bản/sở hữu và đường dẫn phải khớp mục manifest; phiên bản tuân §2 và các binding sự kiện/công bố đã chốt. Module được đọc trong mô tả chỉ là đối tượng dự kiến; quyền thực tế vẫn cần Core cấp riêng.

Contract nhận hoặc đầu vào nguồn dùng lại bản chủ sở hữu đã đăng ký: mô tả, schema, ví dụ trong gói phải đối chiếu đúng bản ghim, không đổi chủ hay tạo contract mới cùng nghĩa. Schema nguồn có thể tham chiếu `$id` đã ghim trong registry offline. Sự kiện giữ payload chỉ gồm tham chiếu theo bus hiện có. M4, CRM, M2 ở G4 phải có `contract/` trước khi làm màn hình.

Khi cài/nâng cấp, Core kiểm và đăng ký vào **một bảng cố định** `loi.dang_ky_contract` (CSDL §3.1), thêm dòng theo QD-09; thêm module/contract không sửa code Core. Sổ lưu mã, phiên bản, module sở hữu, module đang dùng và trạng thái `nhap` / `anh_duyet` / `dang_dung` / `ngung`. Contract nghiệp vụ mới hoặc phiên bản mới của contract đang dùng phải được Anh duyệt trước kích hoạt. Core xuất danh mục dạng bảng để duyệt, gồm mã/phiên bản, mục đích, sở hữu, module được đọc/đang dùng, thay đổi, nguồn trường và trạng thái duyệt. Giữ bản cũ khi còn module đang dùng, cảnh báo bản sắp ngừng; không chuyển ngầm consumer sang bản mới hoặc ngừng bản còn người dùng. Màn quản trị đọc sổ: **bổ sung route quản trị sổ contract khi mở G2**; không sửa `DAC-TA-API.md` đã duyệt.

### 15.1. Module — `urn:ktt:manifest:module.v1`

V1 là `bang`/`ham` trong khối riêng Core suy ra; V2/V3/V4 tách thành ba danh sách. Mã V2 thuộc registry cửa ghi Core; không gộp lời gọi đọc SDK vào V2. Tất cả trường cấp cao bắt buộc; mảng rỗng diễn đạt không dùng tính năng đó.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:manifest:module.v1",
  "$comment": "Phien ban schema 1.0.0; manifest v1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "phien_ban_manifest",
    "loai",
    "ma",
    "ten",
    "phien_ban",
    "tuong_thich",
    "goi",
    "contract",
    "backend",
    "giao_dien",
    "thao_tac",
    "du_lieu_rieng",
    "ham_core_goi",
    "ma_loi",
    "quyen_yeu_cau",
    "engine_dung",
    "quy_trinh",
    "cong_bo",
    "su_kien",
    "tien_trinh",
    "cong_tac"
  ],
  "properties": {
    "phien_ban_manifest": {"const":1},
    "loai": {"const":"module"},
    "ma": {"$ref":"#/$defs/ma"},
    "ten": {"type":"string","minLength":1},
    "phien_ban": {"$ref":"#/$defs/semver"},
    "tuong_thich": {
      "type": "object",
      "additionalProperties": false,
      "required": ["core","api","sdk_python","sdk_js","contract"],
      "properties": {
        "core": {"type":"string","minLength":1},
        "api": {"const":"v1"},
        "sdk_python": {"type":"string","minLength":1},
        "sdk_js": {"type":"string","minLength":1},
        "contract": {"type":"array","items":{"$ref":"#/$defs/contract"},"uniqueItems":true}
      }
    },
    "goi": {
      "type": "object",
      "additionalProperties": false,
      "required": ["tep_kiem_ke","thuat_toan_ma_bam","phu_thuoc_module"],
      "properties": {
        "tep_kiem_ke": {"$ref":"#/$defs/tep"},
        "thuat_toan_ma_bam": {"const":"sha256"},
        "phu_thuoc_module": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["ma","phien_ban"],
            "properties": {"ma":{"$ref":"#/$defs/ma"},"phien_ban":{"type":"string","minLength":1}}
          },
          "uniqueItems": true
        }
      }
    },
    "contract": {
      "type": "object",
      "additionalProperties": false,
      "required": ["cong_bo","su_kien_phat","su_kien_nhan","dau_vao_nguon"],
      "properties": {
        "cong_bo": {"$ref":"#/$defs/ds_contract_goi"},
        "su_kien_phat": {"$ref":"#/$defs/ds_contract_goi"},
        "su_kien_nhan": {"$ref":"#/$defs/ds_contract_goi"},
        "dau_vao_nguon": {"$ref":"#/$defs/ds_contract_goi"}
      }
    },
    "backend": {"type":"object","additionalProperties":false,"required":["diem_vao"],"properties":{"diem_vao":{"$ref":"#/$defs/diem_vao"}}},
    "giao_dien": {
      "type": "object",
      "additionalProperties": false,
      "required": ["diem_vao","tai_nguyen","icon","nhom_mau","thu_tu","trang_dau","thao_tac_khung","phan","the"],
      "properties": {
        "diem_vao": {"$ref":"#/$defs/tep"},
        "tai_nguyen": {"type":"array","items":{"$ref":"#/$defs/tep"},"minItems":1,"uniqueItems":true},
        "icon": {"$ref":"#/$defs/ma"},
        "nhom_mau": {"$ref":"#/$defs/ma"},
        "thu_tu": {"type":"integer","minimum":0},
        "trang_dau": {"$ref":"#/$defs/route_ui"},
        "thao_tac_khung": {"$ref":"#/$defs/ma"},
        "phan": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["ma","ten","icon","thu_tu","duong_dan","quyen_xem"],
            "properties": {
              "ma": {"$ref":"#/$defs/ma"},
              "ten": {"type":"string","minLength":1},
              "icon": {"$ref":"#/$defs/ma"},
              "thu_tu": {"type":"integer","minimum":0},
              "duong_dan": {"$ref":"#/$defs/route_ui"},
              "quyen_xem": {"$ref":"#/$defs/quyen"},
              "dem": {"$ref":"#/$defs/ma"}
            }
          }
        },
        "the": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["ma","nhan","dem","loc"],
            "properties": {
              "ma": {"$ref":"#/$defs/ma"},
              "nhan": {"type":"string","minLength":1},
              "dem": {"$ref":"#/$defs/ma"},
              "loc": {
                "type": "object",
                "additionalProperties": false,
                "required": ["phan","tham_so"],
                "properties": {"phan":{"$ref":"#/$defs/ma"},"tham_so":{"type":"object"}}
              }
            }
          },
          "minItems": 2,
          "maxItems": 4
        }
      }
    },
    "thao_tac": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["ma","phuong_thuc","duong_dan","dau_vao","dau_ra","quyen","kieu","chong_trung"],
        "properties": {
          "ma": {"$ref":"#/$defs/ma"},
          "phuong_thuc": {"enum":["GET","POST","PUT","PATCH","DELETE"]},
          "duong_dan": {"type":"string","pattern":"^/[a-z0-9_/{}/-]*$"},
          "dau_vao": {"$ref":"#/$defs/schema_ref"},
          "dau_ra": {"$ref":"#/$defs/schema_ref"},
          "quyen": {"$ref":"#/$defs/quyen"},
          "kieu": {"enum":["dong_bo","viec"]},
          "chong_trung": {"type":"boolean"},
          "kiem_row_version": {"type":"boolean"},
          "quy_trinh": {"type":"string","minLength":1}
        },
        "allOf": [
          {
            "if": {"properties":{"kieu":{"const":"viec"}},"required":["kieu"]},
            "then": {
              "properties": {
                "dau_ra": {"const":"urn:ktt:contract:viec.v1#/$defs/da_nhan"},
                "chong_trung": {"const":true},
                "phuong_thuc": {"enum":["POST","PUT","PATCH","DELETE"]}
              }
            }
          },
          {
            "if": {"properties":{"phuong_thuc":{"const":"GET"}},"required":["phuong_thuc"]},
            "then": {"properties":{"kieu":{"const":"dong_bo"},"chong_trung":{"const":false}}},
            "else": {"properties":{"chong_trung":{"const":true}}}
          }
        ]
      },
      "minItems": 1
    },
    "du_lieu_rieng": {
      "type": "object",
      "additionalProperties": false,
      "required": ["bang","ham","phan_vung","goi_migration","v2_ghi_chung","v3_danh_muc","v4_cong_bo_doc","cot_nhom_a"],
      "properties": {
        "bang": {"$ref":"#/$defs/ds_ma"},
        "ham": {"$ref":"#/$defs/ds_ma"},
        "phan_vung": {"const":"phap_nhan_id"},
        "goi_migration": {
          "type": "object",
          "additionalProperties": false,
          "required": ["ma","phien_ban_du_lieu","tep_kiem_ke","thu_muc"],
          "properties": {
            "ma": {"$ref":"#/$defs/ma"},
            "phien_ban_du_lieu": {"type":"integer","minimum":1},
            "tep_kiem_ke": {"$ref":"#/$defs/tep"},
            "thu_muc": {"$ref":"#/$defs/tep"}
          }
        },
        "v2_ghi_chung": {"$ref":"#/$defs/ds_ma"},
        "v3_danh_muc": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["doi_tuong","truong"],
            "properties": {"doi_tuong":{"type":"string","pattern":"^danh_muc\\.[a-z][a-z0-9_]*$"},"truong":{"$ref":"#/$defs/ds_ma"}}
          },
          "uniqueItems": true
        },
        "v4_cong_bo_doc": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["module","ma","phien_ban","schema"],
            "properties": {
              "module": {"$ref":"#/$defs/ma"},
              "ma": {"$ref":"#/$defs/ma"},
              "phien_ban": {"type":"string","minLength":1},
              "schema": {"$ref":"#/$defs/schema_ref"}
            }
          },
          "uniqueItems": true
        },
        "cot_nhom_a": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["bang","cot","cot_ban_ma","cot_phien_ban_khoa","cot_hmac","mien_hmac","chuan_hoa","quyen_xem_du"],
            "properties": {
              "bang": {"$ref":"#/$defs/ma"},
              "cot": {"$ref":"#/$defs/ma"},
              "cot_ban_ma": {"$ref":"#/$defs/ma"},
              "cot_phien_ban_khoa": {"$ref":"#/$defs/ma"},
              "cot_hmac": {"$ref":"#/$defs/ma"},
              "mien_hmac": {"$ref":"#/$defs/quyen"},
              "chuan_hoa": {"$ref":"#/$defs/ma"},
              "quyen_xem_du": {"$ref":"#/$defs/quyen"}
            }
          }
        }
      }
    },
    "ham_core_goi": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["loai_ham","phien_ban_contract","ham","chu_ky"],
        "properties": {
          "loai_ham": {"enum":["resolver_mtq","kiem_nghia_vu"]},
          "phien_ban_contract": {"type":"string","minLength":1},
          "ham": {"$ref":"#/$defs/ma"},
          "chu_ky": {"$ref":"#/$defs/tep"}
        }
      }
    },
    "ma_loi": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["ma","http","truong"],
        "properties": {
          "ma": {"type":"string","pattern":"^[A-Z][A-Z0-9_]{0,95}$"},
          "http": {"enum":[400,401,403,404,409,410,413,415,422,429,500,502,503,504]},
          "truong": {"$ref":"#/$defs/ds_chuoi"}
        }
      }
    },
    "quyen_yeu_cau": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["tai_nguyen","hanh_dong","pham_vi"],
        "properties": {
          "tai_nguyen": {"$ref":"#/$defs/ma"},
          "hanh_dong": {"type":"array","items":{"$ref":"#/$defs/ma"},"minItems":1,"uniqueItems":true},
          "pham_vi": {"$ref":"#/$defs/ma"},
          "truong": {"$ref":"#/$defs/ds_ma"},
          "bien_the": {"$ref":"#/$defs/ds_ma"},
          "capability": {"$ref":"#/$defs/ds_chuoi"},
          "loai": {"$ref":"#/$defs/ds_chuoi"}
        }
      }
    },
    "engine_dung": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["capability","bat_buoc","dau_vao","dau_ra"],
        "properties": {
          "capability": {"type":"string","minLength":1},
          "bat_buoc": {"type":"boolean"},
          "dau_vao": {"$ref":"#/$defs/contract"},
          "dau_ra": {"$ref":"#/$defs/contract"}
        }
      }
    },
    "quy_trinh": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["ma","phien_ban","tep"],
        "properties": {"ma":{"$ref":"#/$defs/ma"},"phien_ban":{"type":"string","minLength":1},"tep":{"$ref":"#/$defs/tep"}}
      }
    },
    "cong_bo": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["ma","phien_ban","ham","schema","truong","quyen_doc"],
        "properties": {
          "ma": {"$ref":"#/$defs/ma"},
          "phien_ban": {"type":"string","minLength":1},
          "ham": {"$ref":"#/$defs/ma"},
          "schema": {"$ref":"#/$defs/schema_ref"},
          "truong": {"$ref":"#/$defs/ds_ma"},
          "quyen_doc": {"$ref":"#/$defs/quyen"}
        }
      }
    },
    "su_kien": {
      "type": "object",
      "additionalProperties": false,
      "required": ["phat","nhan"],
      "properties": {
        "phat": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["loai","phien_ban","tham_chieu"],
            "properties": {"loai":{"type":"string","minLength":1},"phien_ban":{"type":"integer","minimum":1},"tham_chieu":{"$ref":"#/$defs/ds_ma"}}
          }
        },
        "nhan": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["loai","phien_ban","xu_ly"],
            "properties": {"loai":{"type":"string","minLength":1},"phien_ban":{"type":"integer","minimum":1},"xu_ly":{"$ref":"#/$defs/ma"}}
          }
        }
      }
    },
    "tien_trinh": {
      "type": "object",
      "additionalProperties": false,
      "required": ["cong","nhan_listener","readiness","thu_hoi","bi_mat","che_do_mac_dinh","ranh_giay_de_xuat"],
      "properties": {
        "cong": {"$ref":"#/$defs/cong"},
        "nhan_listener": {"const":"socket.fromshare"},
        "readiness": {"const":"kenh_dieu_khien"},
        "thu_hoi": {"const":"drain_va_xac_nhan"},
        "bi_mat": {"const":"stdin_hoac_handle"},
        "che_do_mac_dinh": {"const":"tu_kich_hoat_tu_dong"},
        "ranh_giay_de_xuat": {"type":"integer","minimum":1}
      }
    },
    "cong_tac": {"type":"object","additionalProperties":false,"required":["mac_dinh"],"properties":{"mac_dinh":{"const":"TAT"}}}
  },
  "$defs": {
    "ma": {"type":"string","pattern":"^[a-z][a-z0-9_]{0,31}$"},
    "chuoi": {"type":"string","minLength":1},
    "semver": {"type":"string","pattern":"^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\\+[0-9A-Za-z.-]+)?$"},
    "tep": {"type":"string","pattern":"^(?!/)(?!.*(?:^|/)\\.\\.(?:/|$))[A-Za-z0-9_./-]+$"},
    "diem_vao": {"type":"string","pattern":"^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$"},
    "route_ui": {"type":"string","pattern":"^#[a-z][a-z0-9_/-]*$"},
    "quyen": {"type":"string","pattern":"^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2,}$"},
    "contract": {
      "type": "string",
      "pattern": "^(urn:ktt:contract:)?[a-z][a-z0-9_]*\\.v[1-9][0-9]*(:[0-9]+\\.[0-9]+\\.[0-9]+)?(#/\\$defs/[a-z][a-z0-9_]*)?$"
    },
    "schema_ref": {"oneOf":[{"$ref":"#/$defs/contract"},{"allOf":[{"$ref":"#/$defs/tep"},{"pattern":"^schema/.+\\.json$"}]},{"$ref":"#/$defs/tep_contract"}]},
    "tep_contract": {"allOf":[{"$ref":"#/$defs/tep"},{"pattern":"^contract/.+\\.json$"}]},
    "ds_contract_goi": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["ma","phien_ban","module_so_huu","tep_mo_ta","schema","vi_du"],
        "properties": {
          "ma": {"type":"string","minLength":1},
          "phien_ban": {"type":"string","minLength":1},
          "module_so_huu": {"$ref":"#/$defs/ma"},
          "tep_mo_ta": {"$ref":"#/$defs/tep_contract"},
          "schema": {"$ref":"#/$defs/tep_contract"},
          "vi_du": {"$ref":"#/$defs/tep_contract"}
        }
      }
    },
    "ds_ma": {"type":"array","items":{"$ref":"#/$defs/ma"},"uniqueItems":true},
    "ds_chuoi": {"type":"array","items":{"type":"string","minLength":1},"uniqueItems":true},
    "cong": {"const":{"nguon":"core_cap","pham_vi":"loopback"}}
  }
}
```

### 15.2. Engine — `urn:ktt:manifest:engine.v1`

Tham chiếu kiểu dùng chung từ schema module không cấp dịch vụ CSDL cho engine. `ket_noi_ngoai` nếu bỏ qua được Core chuẩn hóa thành `[]` trước kiểm/chạy (`default` không tự chèn dữ liệu); mặc định không kết nối ngoài.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:manifest:engine.v1",
  "$comment": "Phien ban schema 1.0.0; manifest v1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "phien_ban_manifest",
    "loai",
    "ma",
    "ten",
    "phien_ban",
    "tuong_thich",
    "adapter",
    "capability",
    "ho_so_chay_mau",
    "readiness",
    "tai_nguyen",
    "ban_giao_ket_qua",
    "thu_hoi"
  ],
  "properties": {
    "phien_ban_manifest": {"const":1},
    "loai": {"const":"engine"},
    "ma": {"$ref":"urn:ktt:manifest:module.v1#/$defs/ma"},
    "ten": {"type":"string","minLength":1},
    "phien_ban": {"$ref":"urn:ktt:manifest:module.v1#/$defs/semver"},
    "tuong_thich": {
      "type": "object",
      "additionalProperties": false,
      "required": ["core","api"],
      "properties": {"core":{"type":"string","minLength":1},"api":{"const":"v1"}}
    },
    "adapter": {
      "type": "object",
      "additionalProperties": false,
      "required": ["ma","phien_ban"],
      "properties": {"ma":{"$ref":"urn:ktt:manifest:module.v1#/$defs/ma"},"phien_ban":{"type":"string","minLength":1}}
    },
    "capability": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["ma","dau_vao","dau_ra","mime","tep_toi_da_mib","trang_toi_da","thoi_han_giay"],
        "properties": {
          "ma": {"type":"string","minLength":1},
          "dau_vao": {"$ref":"urn:ktt:manifest:module.v1#/$defs/contract"},
          "dau_ra": {"$ref":"urn:ktt:manifest:module.v1#/$defs/contract"},
          "mime": {"type":"array","items":{"type":"string","pattern":"^[a-z0-9.+-]+/[a-z0-9.+-]+$"},"minItems":1,"uniqueItems":true},
          "tep_toi_da_mib": {"type":"integer","minimum":1},
          "trang_toi_da": {"type":"integer","minimum":1},
          "thoi_han_giay": {"type":"integer","minimum":1}
        }
      },
      "minItems": 1
    },
    "ho_so_chay_mau": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "ma_moi_truong",
        "diem_vao",
        "headless",
        "cong",
        "nhan_listener",
        "tham_so_cong",
        "bi_mat",
        "login_csdl",
        "che_do_mac_dinh",
        "ranh_giay_de_xuat"
      ],
      "properties": {
        "ma_moi_truong": {"$ref":"urn:ktt:manifest:module.v1#/$defs/ma"},
        "diem_vao": {"$ref":"urn:ktt:manifest:module.v1#/$defs/diem_vao"},
        "headless": {"const":true},
        "cong": {"$ref":"urn:ktt:manifest:module.v1#/$defs/cong"},
        "nhan_listener": {"type":"array","items":{"enum":["socket.fromshare","tham_so_cong"]},"minItems":1,"uniqueItems":true},
        "tham_so_cong": {"const":"--port"},
        "bi_mat": {"const":"stdin_hoac_handle"},
        "login_csdl": {"const":false},
        "che_do_mac_dinh": {"const":"tu_kich_hoat_tu_dong"},
        "ranh_giay_de_xuat": {"type":"integer","minimum":1}
      }
    },
    "readiness": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kenh","kiem","thoi_han_giay"],
      "properties": {
        "kenh": {"const":"dieu_khien_noi_bo"},
        "kiem": {"type":"array","items":{"enum":["instance","phien_ban","capability","model_san_sang"]},"minItems":4,"uniqueItems":true},
        "thoi_han_giay": {"type":"integer","minimum":1,"maximum":120}
      }
    },
    "tai_nguyen": {
      "type": "object",
      "additionalProperties": false,
      "required": ["so_viec_dong_thoi","ram_toi_da_mib_de_xuat","cpu_phan_tram_toi_da_de_xuat"],
      "properties": {
        "so_viec_dong_thoi": {"type":"integer","minimum":1},
        "ram_toi_da_mib_de_xuat": {"type":"integer","minimum":1},
        "cpu_phan_tram_toi_da_de_xuat": {"type":"integer","minimum":1,"maximum":100}
      }
    },
    "ket_noi_ngoai": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["dich_vu","muc_dich"],
        "properties": {"dich_vu":{"$ref":"urn:ktt:manifest:module.v1#/$defs/ma"},"muc_dich":{"type":"string","minLength":1}}
      },
      "default": [],
      "uniqueItems": true
    },
    "ban_giao_ket_qua": {"const":"core_xac_nhan_truoc_giai_phong"},
    "thu_hoi": {"const":"drain_va_xac_nhan"}
  }
}
```

### 15.3. Tham chiếu, kiểm ngữ nghĩa và ca âm bắt buộc

JSON Schema kiểm hình dạng. Không dùng tính năng ngoài draft 2020-12 như `$data` để so hai trường động; Core kiểm thêm trước cài:

- `contract/` tồn tại và đủ nội dung §15. Đối chiếu từng công bố, sự kiện phát/nhận và đầu vào nguồn với đúng mục `contract`, mã/phiên bản/chủ và schema đã ghim; không có mục thiếu, thừa không có mục đích hoặc trùng mã/phiên bản trong cùng nhóm. Kiểm cấu trúc từng `tep_mo_ta`, đủ metadata/trường/nguồn/đơn vị, ví dụ JSON hợp lệ theo schema và mọi `$ref` giải được offline. Contract nguồn phải khớp bản đã đăng ký; không khai lại thành sở hữu của module nhận. Kiểm trùng nghĩa với sổ, kể cả khác mã/tên trường; chưa có kết luận đối chiếu thì chưa đủ điều kiện cài. Contract trùng nghĩa → đỏ, phải dùng lại/mở rộng contract chung và duyệt thay đổi theo CD-032.
- Ghi sổ `loi.dang_ky_contract` qua Core sau kiểm gói, đồng bộ trạng thái cài/kích hoạt; không kích hoạt contract nghiệp vụ mới hoặc bản mới của contract đang dùng khi thiếu Anh duyệt. Consumer chỉ đọc bản đã đăng ký và đã cấp quyền; giữ binding cũ cho module/việc đang dùng, cảnh báo bản sắp ngừng. Không sửa code Core theo từng contract mới.
- Mã module không trùng, độ dài tên schema/role dẫn xuất hợp PostgreSQL; `goi_migration.ma` bằng `ma`. Core suy `mod_<ma>`, `cong_bo_<ma>`, owner/runtime; không nhận trường role/schema/đối tượng công bố từ gói.
- `ham_core_goi[].ham` thuộc hàm riêng V1, chữ ký khớp schema gói; cài DEFINER đúng owner/hash/ACL/policy rồi ghi `loi.dang_ky_ham_module`. Loại + phiên bản không trùng; chỉ cổng Core nội bộ EXECUTE.
- Tiền tố quyền operation/menu/công bố/cột nhóm A bằng chính `<ma>.`; yêu cầu quyền Core được kiểm/cấp riêng. Cột nhóm A thuộc bảng V1; cột bản mã/phiên bản khóa/HMAC, miền/chuẩn hóa phải có trong migration, không lưu bản rõ/khóa.
- Mã operation, phần/thẻ, quy trình, công bố, capability và lỗi không trùng. `thao_tac_khung`, phần lọc, bộ đếm, workflow `ma@phien_ban`, schema/event/handler phải giải được từ gói/registry; sự kiện có schema gói ghim theo loại + phiên bản. `loc.tham_so` kiểm tiếp theo input schema operation, không thực thi JSON tự do.
- Mọi contract tham chiếu giải đúng `$id` đã ghim trong `tuong_thich.contract` hoặc registry gói; fragment phải tồn tại. Semver/range Core/SDK/dependency phải parse và tương thích; hình dạng chuỗi chưa đủ. Capability có version và được engine/adapter thực hỗ trợ.
- Tệp sau resolve/chuẩn hóa phải nằm trong gói, chống symlink/đường dẫn thoát/ổ đĩa/UNC; bytes/hash khớp kiểm kê. `ham` công bố là tên cục bộ dưới `cong_bo_<ma>`, không nhận schema tự do.
- Mã lỗi + HTTP/tên trường phải thuộc contract operation; danh mục mã lỗi trường (gồm `BAT_BUOC`) phải đăng ký, không chứa input. Kết nối ngoài chỉ mã dịch vụ Core đã duyệt, mặc định rỗng; không mở cổng AI riêng.

Ca âm KT07 phủ **cả module lẫn engine**: thiếu trường/sai version/sai enum/trường lạ; thêm mật khẩu/role migration; tự chọn schema/đối tượng công bố/số cổng; sai tiền tố quyền; đường dẫn `../`/absolute/symlink thoát; thiếu `$ref`/fragment/schema gói, trùng operation/route/capability, workflow/handler không có, version không tương thích; V2 trỏ hàm đọc, V3 trỏ bảng module, V4 ngoài contract; cột nhóm A thiếu HMAC/phiên bản khóa; hàm registry sai owner/chữ ký; việc lâu dùng schema polling; engine `login_csdl:true`, thiếu kiểm model, RAM/CPU vượt miền, dịch vụ ngoài chưa duyệt hoặc AI trực tiếp. Phân biệt lỗi schema và lỗi ngữ nghĩa; schema không tự chứng minh ACL/tiến trình.

Ca âm CD-032 thuộc KT06/KT07/KT15: thiếu `contract/`, thiếu một nhóm manifest, thiếu mục mô tả/schema/ví dụ/phiên bản/nguồn trường; ví dụ sai schema; bản nguồn khác sổ; contract mới trùng nghĩa; kích hoạt thiếu Anh duyệt; nâng cấp làm mất phiên bản cũ còn dùng. Mọi ca phải đỏ và chặn cài hoặc kích hoạt ở đúng bước tương ứng.


---

# BO-KIEM-TUAN-THU.md

**Trạng thái:** Nháp G1c-2 để duyệt; đặc tả bộ kiểm, chưa lập trình hoặc chạy kiểm.  
**Mục tiêu:** Một bộ kiểm áp dụng cho từng module/engine, dùng lại kiểm hiện có và bổ sung phần còn thiếu tại ranh giới Core.

## 1. Nguyên tắc triển khai

Bộ kiểm là một điểm vào chung, chọn kiểm theo loại gói và capability. Không viết lại logic nghiệp vụ hoặc bỏ các regression test đang có.

Nền cần dùng lại:

| Nền | Phần giữ lại | Căn cứ |
|---|---|---|
| Hợp đồng engine | Kiểu vào/ra, không sửa đầu vào, bằng chứng, `XONG/CHO/LOI` | `src/kho_tri_thuc/ha_tang/engine.py:165` |
| Danh bạ engine | Cặp mã/phiên bản, từ chối trùng, không fallback phiên bản | `src/kho_tri_thuc/ha_tang/danh_ba_engine.py:16` |
| Cổng AI/OCR | Cổng được tiêm, ánh xạ lỗi đã biết, giữ DTO | `src/kho_tri_thuc/ha_tang/engine_cong.py:127`, `src/kho_tri_thuc/ha_tang/engine_cong.py:158` |
| Hàng việc | Dedupe, lease/token, heartbeat, retry an toàn, dừng hợp tác | `src/kho_tri_thuc/ha_tang/hang_viec.py:21`, `src/kho_tri_thuc/k2/sql_hang_viec.py:145` |
| Bus | Giao ít nhất một lần, kết quả và ACK cùng transaction | `src/kho_tri_thuc/ha_tang/bus_su_kien.py:11` |
| Khai báo vùng | V1–V4, chủ theo dòng, điểm truy cập hiện có | `src/kho_tri_thuc/ha_tang/khai_bao_module.py:143` |
| Bản khai module | Chủ bảng, vùng chưa rõ và kiểm metadata | `src/kho_tri_thuc/k2/vung_du_lieu.py:153`, `src/kho_tri_thuc/k2/vung_du_lieu.py:274` |
| Công tắc module | Kiểm trong transaction; công tắc không thay MTQ | `src/kho_tri_thuc/k2/module.py:62` |

Kiểm XS-5 hiện tại chỉ kiểm metadata và các điểm truy cập được truyền vào, chưa phải trace runtime hay kiểm quyền PostgreSQL đầy đủ: `src/kho_tri_thuc/ha_tang/khai_bao_module.py:225`, `tests/test_xs5_khai_bao.py:1`.

## 2. Đầu vào và kết quả bộ kiểm

Mỗi lần kiểm nhận:

- Gói module hoặc mô tả engine, phiên bản và capability cần kiểm.
- Manifest và registry schema đã được duyệt.
- Bản đồ sở hữu dữ liệu, quyền yêu cầu và quyền được cấp thực tế.
- Danh mục route/operation và schema vào/ra.
- Bộ dữ liệu giả DEMO, gồm ca đúng, ca âm, ranh giới và đồng thời.
- Hồ sơ chạy thử không chứa dữ liệu thật; kiểm tích hợp chỉ dùng môi trường thử được chỉ định.

Tên login, schema, hàm, chính sách RLS, ngữ cảnh và route cuối cùng **theo phiếu CSDL/API**.

Kết quả mỗi kiểm gồm: mã kiểm, đối tượng/phiên bản, `DAT` / `KHONG_DAT` / `CHUA_KIEM` / `KHONG_AP_DUNG`, mức chặn, bằng chứng an toàn và nguyên nhân. Không ghi credential hoặc payload nhạy cảm vào bằng chứng.

`KHONG_AP_DUNG` chỉ hợp lệ khi phù hợp loại gói và manifest. Ví dụ engine không có CSDL không chạy kiểm DML vùng riêng, nhưng bắt buộc qua kiểm không có login CSDL.

## 3. Mức chặn phát hành

| Mức | Ý nghĩa |
|---|---|
| `C0` | Chặn cài/kích hoạt/phát hành khi có vi phạm an toàn dữ liệu, quyền, bí mật hoặc toàn vẹn. Không được dùng lỗi nền để miễn. |
| `C1` | Chặn phát hành thành phần/capability liên quan khi sai hợp đồng, giao thức hoặc vận hành bắt buộc; `CHUA_KIEM` cũng chưa đủ điều kiện phát hành. |
| `C2` | Cảnh báo có căn cứ; chỉ áp dụng cho chỉ tiêu chưa có ngưỡng nghiệm thu. Không được hạ kiểm bắt buộc xuống `C2`. |

Mức chặn gắn với từng capability. Capability chưa đạt có thể không được đăng ký; không được công bố rồi dựa vào cảnh báo để cho chạy.

## 4. Danh sách kiểm tự động bắt buộc

“Thay kiểm rời rạc” dưới đây nghĩa đưa về bộ kiểm chung và dùng lại các ca kiểm; không xóa tệp test trong lát tài liệu này.

| Mã | Kiểm và cách làm | Kiểm hiện có dùng lại/thay điểm chạy rời rạc | Mức |
|---|---|---|---|
| `KT01` | **Đúng khối dữ liệu.** Đối chiếu manifest, bản đồ chủ sở hữu và đối tượng thực trong catalog thử: bảng, sequence, view, hàm, trigger, policy, FK, owner. Chặn trùng chủ, đối tượng ngoài gói và phụ thuộc chéo chưa được duyệt. | `tests/test_xs5_khai_bao.py:38`, `tests/test_xs5_khai_bao.py:45`, `tests/test_xs5_khai_bao.py:72`; kiểm catalog đầy đủ là bổ sung. | `C0` |
| `KT02` | **Không SQL chéo trái phép.** Kiểm quyền hiệu lực trước; lập danh sách đối tượng hàm/view/trigger chạm tới, gồm SQL động. Sau đó chạy các operation DEMO và thu trace để phát hiện đường chưa khai báo. Ghi chung qua hàm/API Core; đọc công bố qua mặt truy cập được duyệt. | `tests/test_xs5_khai_bao.py:167`, `tests/test_xst1_cong_bo.py:47`, `tests/test_xst1_cong_bo.py:282`. Chưa có kiểm XS-5c runtime đầy đủ trong các tệp đã đọc. | `C0` |
| `KT03` | **Quyền thực tế so với khai báo/cấp quyền.** Tính quyền từ ACL, PUBLIC, membership, kế thừa, khả năng `SET ROLE`, quyền cột, sequence, default privileges, view và hàm DEFINER. Thử cả đường được cấp và đường bị cấm. Chặn quyền thực tế vượt quyền đã cấp; quyền đã cấp vượt yêu cầu phải bị phát hiện. | `tests/test_mtq_cong_sql.py:53`, `tests/test_mtq_cong_sql.py:88`, `tests/test_mtq_cong_sql.py:238`, `tests/test_xs2_sql.py:538`. | `C0` |
| `KT04` | **Danh tính, pháp nhân và MTQ.** Dùng hai pháp nhân, người dùng khác quyền; giả actor/header/GUC; mã phiên hết hạn, sai module, sai pháp nhân; tái sử dụng kết nối; thu hồi quyền giữa việc. Core kiểm phiên bí mật/mã ủy nhiệm, không tin UUID tự khai. | `tests/test_mtq_cong_sql.py:227`, `tests/test_mtq_cong_sql.py:321`, `tests/test_mtq_cong_sql.py:353`, `tests/test_xs2_sql.py:480`. Mã phiên bí mật là ca bổ sung. | `C0` |
| `KT05` | **Route đúng chuẩn.** So route đăng ký, OpenAPI, manifest và route thực; module dưới `/api/v1/module/{ma_module}/...`; kiểm method, operation, input/output, xác thực/CSRF, lỗi chuẩn, 202, CAS và idempotency theo phiếu CSDL/API. Thử route chưa đăng ký và giả header nội bộ. | `tests/test_mtq_http_dispatch.py:42`, `tests/test_mtq_http_dispatch.py:48`, `tests/test_xs4_http.py`; đối chiếu OpenAPI/registry là bổ sung. | `C0` cho vượt quyền/route quản trị; `C1` cho sai giao thức |
| `KT06` | **Contract hợp lệ.** Kiểm meta-schema 2020-12, `$id` duy nhất, mọi `$ref` giải được offline; bật kiểm format; kiểm ví dụ, input/output adapter và các ca âm ở §5. Không cho phản hồi sai schema được lưu/công bố. | `tests/test_xs3_engine.py:72`, `tests/test_xs3_engine.py:164`, `tests/test_xs3_engine.py:168`, `tests/test_xs3_cong.py:288`, `tests/test_xs3_hoa_don.py:78`. Kiểm JSON Schema chung là bổ sung. | `C1`; `C0` nếu làm lọt dữ liệu cấm hoặc sai tiền |
| `KT07` | **`module.json` hợp lệ.** Kiểm theo schema manifest chính thức của phiếu SDK: danh tính, tương thích, operations/schema, vùng dữ liệu, quyền, capability, workflow, tài nguyên. Kiểm tham chiếu tồn tại, không trùng, không vượt thư mục gói, không credential/URL engine/Python cố định. Không cài dependency tùy ý vào Core. | `tests/test_xs4_khai_bao.py`, `tests/test_xs5_khai_bao.py:249` cung cấp kiểm metadata/roundtrip; chưa thay được kiểm gói manifest đầy đủ. | `C1`; `C0` cho bí mật hoặc thoát phạm vi gói |
| `KT08` | **Readiness và nhận ổ nghe.** Kiểm cấp cổng cố định, giữ khi dừng, chuyển giao ổ nghe, bắt tay danh tính/instance/process/version/capability, rồi mới cho phục vụ. Thử sai danh tính, model chưa sẵn, khởi động đồng thời, crash và cổng bị chiếm. | `tests/test_trich6_host.py:330`, `tests/test_trich6_host.py:343`, `tests/test_trich6_host.py:529`, `tests/test_trich6_host.py:569`. Socket chuyển giao là bổ sung. | `C1`; `C0` nếu gọi nhầm hoặc dừng tiến trình lạ |
| `KT09` | **Không ghi khóa vào log.** Tiêm bí mật DEMO có thể nhận diện vào các kênh xác thực; gây lỗi parse, timeout, 401, lỗi SQL, exception, hủy và crash. Quét stdout/stderr, log, audit, trace, metric label, thông điệp HTTP và báo cáo kiểm; kiểm cả dạng escape/encode thông dụng. | `tests/test_xs2_worker.py:178`, `tests/test_xs2_worker.py:520`, `tests/test_xs3_cong.py:86`, `tests/test_xs3_hoa_don.py:173`, `tests/test_trich6_host.py:40`. | `C0` |
| `KT10` | **Engine không login CSDL; gọi AI đúng cổng.** Kiểm gói, hồ sơ chạy và cấu hình truyền vào không trao DSN/mật khẩu CSDL cho engine. Chặn thử mở DB trong sandbox thử. Dùng spy để chứng minh AI/OCR gọi cổng được cấp; đường Cloud chỉ sau Mask v2. | `tests/test_xs3_cong.py:256`, `tests/test_xs3_cong.py:267`, `tests/test_xs3_cong.py:302`, `tests/test_cong_ai.py`. Kiểm process/config engine là bổ sung. | `C0` |

**Bổ sung vòng 2 bắt buộc cho các mã trên** (đều là yêu cầu mới cần chạy sau, chưa phải test đã có):

| Mã | Ca và tiêu chí bổ sung | Mức |
|---|---|---|
| KT01/KT03 | Chạy lại mỗi lần kích hoạt và mỗi lần Core khởi động; giả GRANT tay vượt quyền, đổi owner/policy hoặc membership phải đưa module về chưa kích hoạt. Thử driver SQL trực tiếp bỏ qua SDK vẫn bị role/RLS/Core chặn; SDK không phải ranh giới an ninh. | C0 |
| KT04/KT11 | Việc nhận mã riêng theo `viec_id` + thế hệ lease trong `GiuViec`; token HTTP không dùng làm mã nền. Hết lease/restart/thu hồi quyền thì mã cũ thất bại; lease mới chỉ nhận mã mới sau kiểm quyền/đối chiếu tác động. | C0 |
| KT05 | Biên nhận module bất biến, giữ vĩnh viễn trong `loi_tai_lieu.bien_nhan_thao_tac` qua V2 cùng transaction nghiệp vụ/tạo việc, UNIQUE pháp nhân/module/operation/client_key; Core chỉ khóa request đang chạy. Thử rollback; crash sau commit trước response; Core/module restart; replay sau 24 giờ; alias cũ/v1 dùng cùng operation/body chuẩn hóa/khóa, không theo path/method. Cùng fingerprint trả cùng kết quả/việc; khác fingerprint trả 409; quyền hiện tại được kiểm trước tra/replay, không thấy kết quả trả 404 kể cả khác người tạo. Không tạo việc qua HTTP rồi ghi biên nhận riêng; không có biên nhận hoàn tất thứ hai ở Core. | C0 |
| KT05 | Gọi thẳng cổng loopback module thiếu token; sai chữ ký/instance; TTL >30 giây/hết hạn; hash method/path/body lệch; nonce lặp kể cả cạnh tranh đều 401 trước handler. Retry bằng token/nonce mới giữ khóa chống trùng cũ. | C0 |
| KT06/KT07 | Nạp offline **cả hai** schema manifest §15, kiểm meta-schema, hai mẫu SDK §6 và ca âm §15.3; mã lỗi/HTTP/trường lỗi phải đăng ký. `kieu:viec` bắt buộc `urn:ktt:contract:viec.v1#/$defs/da_nhan`, không dùng schema polling. | C1; vượt quyền/bí mật là C0 |
| KT08 | Core bind với `SO_EXCLUSIVEADDRUSE`, thử tiến trình khác dùng `SO_REUSEADDR` bind lại phải thất bại; nhánh engine cũ vẫn ghi khoảng hở. Module chỉ ready khi login/role và phiên bản dữ liệu/checksum khớp `loi.lich_su_doi_cau_truc`; lệch không phục vụ. Trạng thái đúng `stopped/starting/ready/busy/dang_dung/failed` (API §5). | C1; chiếm cổng/gọi nhầm là C0 |
| KT08/KT10 | Theo CD-033 câu 2 đã chốt A: kiểm SID/tài khoản thực, Core tài khoản riêng (ví dụ `ktt_core`), module/engine tài khoản máy hạn chế khác Core (ví dụ `ktt_module`), áp ngay khi thử trên máy Anh. Từ chính tiến trình module/engine, liệt kê/mở/đọc `D:\DU-LIEU-KE-TOAN\bi-mat\`, dùng DPAPI lấy khóa, mở/đọc/ghi nhớ Core, duplicate handle/token, sửa ACL lấy lại quyền đều phải thất bại. Chỉ kế thừa handle allowlist; engine không login DB; không đạt thì không kích hoạt (SDK §4.4). Dùng bí mật DEMO trong môi trường thử, không đọc kho thật. | C0 |
| KT09 | Quét thêm log PostgreSQL trong môi trường DEMO, xác minh `log_parameter_max_length=0` và `log_parameter_max_length_on_error=0` (`log_parameter_max_length*=0`); lỗi SQL/rollback không rò mã ủy nhiệm hoặc khóa. Mật khẩu truyền `password=` riêng, không DSN chứa bí mật; khóa mã hóa không vào SQL/GUC. | C0 |
| KT12/KT16 | Đang tự đóng có việc `queued`/sự kiện chờ thì Core đánh thức đúng một instance; `TAT` giữ hàng chờ, không tự bật. Hộp nhận chưa rỗng/lease/request/lượt Mask đang dùng thì chưa rảnh. Job `KILL_ON_JOB_CLOSE`, cây con và RAM/CPU được Core xác minh từ Job accounting, không lấy tự khai làm số đo chính. | C1; vượt quyền/mất tác động là C0 |
| KT14 | Module không giả nguồn OCR/engine/version/việc được; Core tự gắn provenance từ instance/lease và kiểm nguồn tham chiếu. | C0 |
| KT03/KT09 | Cổng `ma_hoa`: cột nhóm A đăng ký, bản mã + phiên bản khóa, HMAC miền/khóa độc lập; xem rút gọn tối đa bốn số, xem đủ cần quyền + audit. Thử sai pháp nhân/cột, đổi khóa/khôi phục và canary log; module không nhận khóa/bản rõ ngoài quyền. | C0 |

Các ca bắt buộc vòng 3 (CD-032/033):

| Mã kiểm | Điều kiện và ca âm phải đỏ | Mức chặn |
|---|---|---|
| KT06/KT07 | Contract mới trùng nghĩa contract đã có → đỏ, kể cả đổi tên/mã; đối chiếu mục đích, chủ dữ liệu, nguồn và nghĩa trường với sổ. Phải dùng lại hoặc mở rộng contract chung theo quy tắc phiên bản/duyệt, không tạo bản sao nghĩa. Chưa xác định được nghĩa thì `CHUA_KIEM`, không tự cho qua. | C1 — chặn cài |
| KT02/KT03 | Module đọc dữ liệu module khác ngoài contract đã đăng ký **và** cấp quyền → đỏ. Thử cả chưa đăng ký nhưng có GRANT, đã đăng ký nhưng chưa cấp quyền, sai bản ghim và SQL/HTTP trực tiếp bỏ qua SDK; quyền SQL thủ công không thay contract. | C0 |
| KT07/KT15 | Thiếu/không hợp lệ `contract/` → không cài. Cài/nâng cấp đăng ký thêm qua Core, không vá Core; contract nghiệp vụ mới/bản mới đang dùng thiếu Anh duyệt → không kích hoạt. Xuất danh mục dạng bảng; giữ bản cũ còn dùng, hiển thị module ghim bản sắp ngừng. | C1; mất dữ liệu/quyền là C0 |
| KT08/KT10/KT15 | Script tạo tài khoản/cấp quyền thư mục chạy lại không mở rộng quyền, tái lập được khi chuyển máy chủ; Anh chỉ đồng ý quyền quản trị. Engine cũ cần tài khoản riêng như ABBYY Hot Folder phải có ngoại lệ Anh duyệt; thiếu duyệt hoặc tự nới quyền → đỏ. | C0 |

### 4.1. Quyền và SQL chéo: thứ tự kiểm

Không kết luận an toàn chỉ vì trace DEMO chưa thấy câu SQL xấu. Thứ tự:

1. Đối chiếu quyền hiệu lực với quyền được cấp.
2. Kiểm chủ sở hữu, `SECURITY DEFINER`, `search_path`, quyền EXECUTE và các đối tượng bị truy cập gián tiếp.
3. Rà phụ thuộc SQL động, trigger và hàm lồng nhau; không coi catalog dependency là danh sách đầy đủ cho mọi SQL động.
4. Thử trực tiếp các thao tác bị cấm bằng đúng login runtime.
5. Chạy operation DEMO và so trace với khai báo.

Review yêu cầu lấy ACL thực và đối tượng mỗi hàm DEFINER chạm tới làm kiểm chính, trace hỗ trợ: `docs/47-core/g1/RV-G1A-OPUS.md:18`.

Ngoại lệ “đang tồn tại” của XS-5 là đầu vào chuyển đổi, không trở thành quyền mặc định của gói mới. Điểm chưa rõ chủ hoặc chưa có mặt công bố làm kiểm tương ứng `CHUA_KIEM`, chưa được kích hoạt.

### 4.2. Bắt tay readiness và chuyển giao ổ nghe

Ca bắt buộc cho mỗi module/engine chạy tiến trình riêng:

1. Core giữ cổng đã cấp khi tiến trình chưa chạy; một tiến trình thử khác không chiếm được.
2. Hai yêu cầu đồng thời chỉ tạo một instance.
3. Tiến trình nhận chính ổ nghe Core bàn giao; không tự chọn cổng khác.
4. TCP kết nối được nhưng sai instance/version/capability phải bị từ chối.
5. Liveness đạt nhưng model/task/catalog chưa sẵn thì readiness không đạt.
6. Request chờ chỉ được chuyển sau khi readiness đạt.
7. Dừng có kiểm soát, chờ việc/lượt đang dùng hoàn tất; Core giữ lại đúng cổng.
8. Sau crash phải xác minh process identity; không dùng PID đơn lẻ để dừng tiến trình.
9. Engine cũ không nhận socket: kiểm riêng nhánh đóng ổ nghe rồi chạy với cổng Core cấp. Xung đột phải báo lỗi, không tự đổi cổng hoặc dừng ứng dụng lạ.
10. Kết quả kiểm phải ghi rõ `chuyen_giao_o_nghe` hay `chuyen_tiep_engine_cu`; không báo nhánh chuyển tiếp là đã chứng minh không khoảng hở.

Căn cứ: `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:329`.

OCR hiện kiểm readiness chủ yếu qua tệp/dependency, chưa chứng minh inference; không dùng kết quả đó thay toàn bộ kiểm readiness: `docs/47-core/g0/KS-E.md:119`.

## 5. Ca kiểm contract theo từng loại dữ liệu

Mọi contract có ít nhất: một ví dụ đúng, thiếu trường bắt buộc, trường lạ, sai kiểu, sai phiên bản, tham chiếu không tồn tại, tham chiếu khác pháp nhân và dữ liệu vượt giới hạn.

| Contract | Ca kiểm riêng | Kiểm nguồn dùng lại | Mức |
|---|---|---|---|
| `tham_chieu_tep.v1` | Hash/kích thước/MIME không khớp; hết hạn; đổi tệp dưới cùng ID; tên chứa đường dẫn/control; tải bằng ID không có quyền. | Nền store/intake được khảo sát tại `docs/47-core/g0/KS-A.md:20`; kiểm ID/hash/quyền tập trung là bổ sung. | `C0` |
| `van_ban_tai_lieu.v1` | OCR schema 1/2; trang/khối trùng; bbox sai hệ; revision cũ; nguồn còn pending; `succeeded`/`final` không tự thành `da_duyet`; DOCX không có số trang xác định. | `tests/test_cong_ocr.py`, `tests/test_xs3_cong.py:256`; bổ sung adapter JSON của OCR đối chiếu theo `docs/47-core/g0/KS-E.md:109`. | `C1`; vượt quyền/duyệt sai là `C0` |
| `du_lieu_bang.v1` | Ô vượt bảng; ô gộp chồng; sai kiểu/đơn vị cột; không mất số `0`; vùng chưa đọc không thành rỗng; giữ `unit_ids` và cảnh báo. | `tests/test_source6_docx_tables.py`; nguồn cấu trúc OCR tại `D:/GPT/OCR/mask_ocr/layout.py:28`. | `C1`; sai tiền/đơn vị khi ghi là `C0` |
| `tham_so.v1` | Catalog/hash sai; mã lạ/trùng; ngày không tồn tại; dẫn chứng không thuộc nguồn; loại mua chưa triển khai; E5 bảng không bị đổi thành chuỗi; niêm phong sai. | `tests/test_trich_chung_6.py`, `tests/test_source6_g5_e5.py`; kiểm typed tại `src/kho_tri_thuc/nguon/trich_chung_6.py:151`. | `C1`; nhận dữ liệu sai nguồn/tiền là `C0` |
| `noi_dung_da_che.v1` | `gui_duoc` nhưng danh mục khóa/còn sót; lượt hết hạn/restart; giả ID lượt; mở che sai quyền; không lộ mapping; revision chưa công bố không bị tự điền; không dừng Mask khi lượt còn dùng. | `tests/test_cong_ai.py`, `tests/test_xs3_cong.py:103`; điều kiện hiện có tại `src/kho_tri_thuc/tri_thuc/cong_ai.py:663`. | `C0` |
| `tra_loi_ai.v1` | Giữ nguồn từng trường và giá trị Local; trích dẫn sai biến thể/revision bị loại; model cấu hình không bị ghi thành bằng chứng thực thi; mở che lỗi; có kết quả không tự thành duyệt. | `tests/test_cong_ai.py`, `tests/test_cong_ai_nhat_ky.py`, `tests/test_xs3_cong.py:117`, `tests/test_xs3_cong.py:224`. | `C1`; Cloud/lộ dữ liệu/sai quyền là `C0` |
| `hoa_don.v1` | Thiếu/rỗng/trùng field; exact decimal; tiền vượt miền; không default tiền tệ/số lượng; số hóa đơn giữ `0` đầu; namespace ngoài profile; ZIP trùng tên/CRC lỗi/partial; không suy đủ kỳ hoặc đã ghi sổ. | `tests/test_hoa_don_xml.py`, `tests/test_xs3_hoa_don.py:78`, `tests/test_xs3_hoa_don.py:121`, `tests/test_xs3_hoa_don.py:164`. | `C0` cho bảo toàn tiền/định danh/nguồn; còn lại `C1` |
| `loi_chuan.v1` | Đủ bốn trường, mã đúng; không lộ lỗi thô; `request_id` xuyên tiến trình; không bật retry cho tác động chưa rõ. | `tests/test_xs2_worker.py:178`, `tests/test_xs3_hoa_don.py:192`; kiểm wire body là bổ sung. | `C0` cho lộ bí mật/retry nguy hiểm; còn lại `C1` |
| `viec.v1` | Phân biệt 202/polling; không lộ lease/token; trạng thái không hợp lệ; hủy là đề nghị; `CHUA_RO` không tự retry; không trả kết quả khác pháp nhân. | `tests/test_xs2_sql.py:280`, `tests/test_xs2_sql.py:293`, `tests/test_xs2_sql.py:317`, `tests/test_xs2_worker.py:468`. | `C0` cho quyền/toàn vẹn; còn lại `C1` |

Ca contract bổ sung vòng 2 (thuộc cùng KT06, dùng cổng giả/DEMO, không dịch vụ ngoài):

| Contract | Ca bắt buộc và kết quả mong đợi | Mức |
|---|---|---|
| Tất cả | Sai hằng `phien_ban` riêng phải bị bác; nâng một contract tạo ID mới không đổi hằng contract khác/vỏ chung. Consumer ghim bản cũ chỉ nhận bản cũ; thêm trường dưới cùng ID phải bị kiểm phát hành bác. | C1 |
| `noi_dung_da_che.v1` | Thiếu/cờ `giu_nguyen_tien_ngay:false` bị schema bác; chuỗi nguồn DEMO có tiền, đơn vị, ngày và định danh sát nhau: sau che các định danh, tiền/ngày vẫn nguyên. Mất/đổi/che tiền/ngày dù tự khai cờ true phải bị kiểm ngữ nghĩa chặn Cloud. | C0 |
| `tra_loi_ai.v1` | CLOUD/LOCAL+CLOUD thiếu lượt, lượt null/sai UUID hoặc `mo_che:khong_ap_dung/chua_kiem` đều bị schema bác. Nhãn LOCAL nhưng trường/model CLOUD cũng không qua. ID đúng hình dạng nhưng sai việc/pháp nhân/hết hạn bị Core bác; mở che `khong_dat` không công bố như đã mở che. Tiền có dấu nhóm `1.000.000`, thiếu đơn vị hoặc chuỗi trần thay typed value bị bác; giữ typed Local và kiểm catalog. | **C0** cho Cloud không lượt/tiền/quyền |
| `hoa_don.v1` | Thiếu `thue_suat` bị schema bác; TSuat thiếu/rỗng/trùng/ký hiệu đặc biệt giữ trạng thái/lexeme/issue nguồn. Có dòng chiết khấu TChat=3 dương vẫn không cộng dòng thành tổng; `truoc_thue` chứa phần không chịu thuế không được làm cơ sở chịu thuế; thiếu tổng giữ thiếu. | C0 |
| `loi_chuan.v1` | `chi_tiet` hợp lệ gắn đúng ô; thêm `gia_tri`/giá trị input hoặc trường/mã chưa đăng ký bị bác/làm sạch thành 502, không echo input. Mã lỗi module/HTTP chưa đăng ký cũng 502. | C0 cho lộ input; còn lại C1 |

Bộ kiểm phải chạy cả hai chiều: nguồn → contract và contract → consumer. Không chỉ kiểm ví dụ thủ công mà bỏ response thực do adapter tạo.

## 6. Kiểm tích hợp dùng lại nền XS và MTQ

| Mã | Nội dung và cách kiểm | Test hiện có | Mức |
|---|---|---|---|
| `KT11` | **Hàng việc bền vững.** Hai worker nhận cùng việc; lease hết; token cũ; mất heartbeat; mất kết nối sau tác động; CAS thất bại phải rollback kết quả. Không đổi `CHUA_RO` thành an toàn để tự retry. | `tests/test_xs2_sql.py:215`, `tests/test_xs2_sql.py:237`, `tests/test_xs2_worker.py:402`, `tests/test_xs2_worker.py:425`, `tests/test_xs2_worker.py:468`. | `C0` |
| `KT12` | **Bus và transaction.** Ghi kết quả + ACK cùng transaction; rollback trước/sau ACK; giao lại không nhân đôi tác động; payload bus chỉ chứa tham chiếu được phép, không nhúng toàn văn. | `tests/test_xs1_bus.py:155`, `tests/test_xs1_bus.py:170`, `tests/test_xs1_bus.py:200`, `tests/test_xs1_sql.py`. | `C0` |
| `KT13` | **Công tắc module và quyền.** `TAT/THU/VAN_HANH`, hai pháp nhân, người thử; tắt chặn việc mới nhưng không làm mất dữ liệu cũ; THU không công bố/xuất chính thức. MTQ vẫn kiểm độc lập. | `tests/test_xs4_dich_vu.py`, `tests/test_xs4_sql.py`, `tests/test_xs2_sql.py:436`, `tests/test_xs2_worker.py:511`, `tests/test_xst1_cong_bo.py:244`. | `C0` |
| `KT14` | **Duyệt và phiên bản nguồn.** Kết quả thành công vẫn có thể cần duyệt; sửa tạo revision mới; dẫn chứng/consumer ghim đúng revision; không dùng phiên bản mới nhất ngầm. | `tests/test_xs3_engine.py:249`, `tests/test_xst1_cong_bo.py:236`; review OCR liên tiến trình là bổ sung. | `C0` |
| `KT15` | **Cài/nâng cấp/tắt gói.** Kiểm manifest và migration trước kích hoạt; thất bại không kích hoạt một phần; tắt giữ dữ liệu; không sửa contract của việc đang chạy. Migration và role theo phiếu CSDL/API. | Dùng lại công tắc và metadata; chưa có bộ kiểm Module Manager hoàn chỉnh theo khảo sát `docs/47-core/g0/KS-A.md:17`. | `C1`; sai quyền/mất dữ liệu là `C0` |
| `KT16` | **Số đo vận hành.** Kiểm có thời điểm yêu cầu, thời gian tới ready, chạy việc, rảnh trước dừng, số lần khởi động/ngày, RAM/CPU. Mặc định tự kích hoạt/tự dừng; đề xuất chế độ không tự áp dụng; chỉ Admin được áp dụng. | Bổ sung theo `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:332`; không coi host hiện tại đã có đủ. | `C1` cho thiếu số đo/quy trình bắt buộc; `C0` nếu tự đổi cấu hình hoặc vượt quyền Admin; ngưỡng hiệu năng chưa chốt là `C2` |

### 6.1. Chống giả danh và kiểm toàn vẹn tiền

Bộ kiểm mới phải bổ sung hai nhóm ca mà kiểm cũ chưa đủ chứng minh:

- Module tự đặt UUID người dùng/GUC, đổi pháp nhân hoặc dùng mã phiên của module khác phải thất bại. Việc nền dùng ủy nhiệm đúng việc, còn hạn, không trở thành quyền toàn hệ thống.
- Hai người có quyền xem khác nhau cùng tạo liên kết tiền không được làm vượt chứng từ/nghĩa vụ. Hàm kiểm toàn vẹn phải tính trên phạm vi cần thiết, không chỉ tổng các dòng người gọi nhìn thấy.

Cơ chế cụ thể **theo phiếu CSDL/API**. Đây là yêu cầu từ review về giả danh và FORCE RLS tại `docs/47-core/g1/RV-G1A-OPUS.md:31`, `docs/47-core/g1/RV-G1A-OPUS.md:41`.

## 7. Kiểm bí mật và giới hạn truy cập

Các bí mật DEMO dùng trong kiểm phải khác nhau cho: phiên người dùng, mã phiên liên tiến trình, mã ủy nhiệm việc, credential engine, credential CSDL và lượt Mask. Khi phát hiện rò rỉ, báo tên kênh và mã kiểm; không chép lại giá trị bị lộ vào báo cáo.

Phải kiểm:

- Bí mật không đi qua URL/query, argv, manifest, frontend hoặc response lỗi.
- Credential khởi động chỉ truyền theo kênh được duyệt; không suy cơ chế cũ dùng biến môi trường là cơ chế mới đã đạt.
- Log có allowlist metadata; lỗi từ thư viện và SQL phải qua lớp xử lý an toàn trước khi thành thông điệp người dùng.
- Tệp nguồn, bản OCR chưa che, mapping và phản hồi nguồn vẫn chịu quyền/retention tương ứng; không coi là log thông thường.
- Mọi lời gọi AI được kiểm bằng cổng giả hoặc transport giả; không cần gọi Cloud thật để chứng minh luồng tuân thủ.

Review yêu cầu credential ngoài thư mục phần mềm và kênh stdin/handle tại `docs/47-core/g1/RV-G1A-OPUS.md:45`. Cách triển khai cuối cùng **theo phiếu CSDL/API**.

## 8. Trình tự chạy và tiêu chí nghiệm thu

Sau khi được mở lập trình:

1. **Kiểm tĩnh:** manifest, schema, tham chiếu, route, bản đồ sở hữu, dependency và dấu hiệu bí mật.
2. **Kiểm thuần/adapter:** dữ liệu DEMO, cổng giả, source-version đã ghim, ca đúng/âm và bảo toàn bằng chứng.
3. **Kiểm PostgreSQL thử:** ACL, role, RLS, phiên bí mật, transaction, hàng việc, bus và công tắc.
4. **Kiểm tiến trình local:** socket, readiness, đồng thời, restart, dừng và engine cũ.
5. **Đối chiếu regression:** chạy các test liên quan, so mã lỗi với nền; tổng hợp theo từng module/engine/capability.

Không tạo một CSDL hoặc role theo mỗi test. Dùng môi trường thử được quản lý và dữ liệu DEMO; cách chuẩn bị/dọn tài nguyên theo phiếu CSDL. Không dùng dữ liệu thật hoặc dịch vụ ngoài.

Điều kiện đạt:

- Không còn `KHONG_DAT` hoặc `CHUA_KIEM` ở kiểm `C0`/`C1` áp dụng cho thành phần phát hành.
- Mọi capability công bố có schema, ví dụ, ca âm và bằng chứng chạy adapter.
- Quyền hiệu lực không vượt quyền được cấp; không có SQL chéo chưa được duyệt.
- Tất cả ca bảo toàn tiền, nguồn, danh tính, bí mật và chống thực hiện trùng phải đạt.
- Không thêm lỗi regression so với nền được chỉ định.

Nền hiện được tài liệu quy định là so theo mã lỗi, không yêu cầu giả định toàn repo không có lỗi sẵn: `docs/46-chuyen-doi-dieu-phoi/NEN-TEST.md:3`, `docs/46-chuyen-doi-dieu-phoi/NEN-TEST.md:7`. Test PostgreSQL hoặc kiểm mới thiếu môi trường phải ghi `CHUA_KIEM`; không tính skip thành đạt.

## 9. Mẫu báo cáo sau mỗi lần kiểm

Báo cáo không quá một trang:

- **Đối tượng:** module/engine, phiên bản, capability, phiên bản bộ kiểm và schema.
- **Đã kiểm:** số đạt/tổng áp dụng; số không đạt/chưa kiểm/không áp dụng.
- **Chặn phát hành:** mã kiểm `C0`/`C1`, nguyên nhân và bằng chứng đã loại bí mật.
- **Regression:** có/không lỗi mới so với nền; liệt kê mã lỗi mới.
- **Đã tự thử:** ca đồng thời, restart, quyền âm, tiền/đơn vị và log theo phạm vi.
- **Còn thiếu/rủi ro:** phụ thuộc chưa duyệt và capability chưa được phép công bố.

**Tình trạng vòng 2:** chỉ cập nhật `DAC-TA-SDK.md` và tài liệu này; không commit. Kiểm offline: 24/24 khối JSON parse, 12 `$id` duy nhất và mọi `$ref` giải được, 12/12 ví dụ + 52/52 ca đúng/âm đạt kiểm tĩnh các keyword đang dùng; UTF-8 không BOM và `git diff --check` đạt. Chưa chạy validator meta-schema draft 2020-12 chính thức vì môi trường thiếu thư viện; không cài dependency hoặc tạo tệp kiểm. Không chạy test ứng dụng/runtime; các KT là tiêu chí sau duyệt, chưa là bằng chứng tuân thủ thực tế; lỗi mới so với nền ứng dụng chưa đánh giá.

## Vòng 2 — đã xử lý

Mã phát hiện theo quy ước SDK §1: `O` = review Opus (Chặn1–3, CS1–CS9 theo mục Ưu tiên sửa; R1–R6 theo bảng), `C` = review Codex (C1–C5 theo thứ tự bảng).

| Mã phát hiện | Chỗ sửa |
|---|---|
| O-Chặn1; C1 | SDK §2; bộ kiểm KT05: biên nhận V2 vĩnh viễn/cùng transaction, fingerprint, quyền replay, crash/restart/>24 giờ/alias |
| O-Chặn2; O-R1a,b | SDK §2, §4.4; KT01/KT03/KT08/KT10: role/RLS/Core, token hạn chế, bí mật/bộ nhớ/ACL/DPAPI |
| O-Chặn3; O-R1c | SDK §3 dịch vụ `ma_hoa`; §15.1 cột nhóm A; KT03/KT09 cổng mã hóa/quyền/audit/khóa |
| O-CS1; O-R1d | SDK §4.2; KT05 token ký/instance/TTL/nonce/hash/cổng trực tiếp |
| O-CS2; O-R1e; O-R2i | SDK `GiuViec`/§4.3; KT04/KT11 ủy nhiệm theo lease; KT12/KT16 đánh thức/rảnh |
| O-CS3; O-R3; C2 | §15 hai schema/version, V1–V4/registry/quyền/Core tự suy, ca âm; KT06/KT07 kiểm cả hai mẫu SDK |
| O-CS4; O-R4 phiên bản | §2 quy tắc ID mới/ghim chính xác; §3 vỏ chung không const; §5–10 const riêng, bộ kiểm §5 |
| O-CS5; O-R4 AI/Mask | §8 schema giữ tiền/ngày; §9 điều kiện CLOUD/lượt che/typed value; ca âm C0 bộ kiểm §5 |
| O-CS6; O-R4 hóa đơn | §10 schema `thue_suat`, quy tắc `TgTCThue`/chiết khấu/tổng nguồn; bộ kiểm §5 |
| O-CS7; O-R2ii,iii | SDK §4.1–4.3; KT08 readiness/login/data version/exclusive bind; KT16 Job accounting |
| O-CS8; O-R1f và DSN; O-R5 | §2.1 Core gắn nguồn; KT01/KT03 kiểm lại lúc kích hoạt/Core restart; KT09 log PostgreSQL/tham số/khóa; KT14 provenance |
| O-CS9; O-R6; C5 | SDK §8 ba câu mới, M4 G4 là thông báo; không hỏi trùng retention hoặc thêm logic khoản vay |
| C3 | §12 phân biệt polling/202; §15.1 ràng buộc `dau_ra` việc lâu; KT07 |
| C4 | §11 schema/ví dụ `chi_tiet` an toàn/đăng ký lỗi; §15 `ma_loi`; bộ kiểm §5 |

## Vòng 3 — CD-031/032/033

| Việc | Chỗ sửa |
|---|---|
| CD-031: JSON hai lớp, module sở hữu và Anh duyệt nghiệp vụ | Đầu tài liệu, dẫn danh mục `CONTRACT-NGHIEP-VU.md` đang soạn |
| CD-032: bắt buộc `contract/`, mô tả trường/nguồn/schema/ví dụ | §15, §15.1 schema `module.v1` thêm bốn nhóm và đường dẫn `contract/`; §15.3 kiểm ngữ nghĩa/ca âm |
| CD-032: sổ, duyệt, giữ bản cũ và màn quản trị | §15 dẫn `loi.dang_ky_contract` tại CSDL §3.1; ghi chú route đọc khi mở G2 |
| CD-032: trùng nghĩa và đọc ngoài contract + cấp quyền → đỏ | Bộ kiểm §4: KT02/KT03, KT06/KT07, KT15; §15.3 chặn cài/kích hoạt |
| CD-033: tài khoản riêng từ thử máy Anh, script và ngoại lệ | Bộ kiểm §4: KT08/KT10/KT15, không đọc được `D:\DU-LIEU-KE-TOAN\bi-mat\`; SDK §4.4, §8 |

## Bổ sung AI-1b — `hoi_ai.v1` (31/10/2026)

Contract kỹ thuật thứ 10, do Core sở hữu, bản đầu `1.0.0`, `$id`
`urn:ktt:contract:hoi_ai.v1`; chốt tại `docs/47-core/engine/QUYET-DINH-AI-1B.md`
§6 sau review Opus Đạt, theo CD-041 mục 3 và chuẩn SDK v1.1 §1.
Mục này bổ sung sổ §2; giữ nguyên các mục trước để không đổi số dòng tham chiếu.

Payload là một yêu cầu đầu vào `ai.hoi@1` của engine `e_hoi_ai`, không có vỏ
`vo_noi_dung`; đầu ra dùng `tra_loi_ai.v1`. Năm trường nghiệp vụ chuyển 1-1 từ
`YeuCauAI`; danh tính, pháp nhân và việc do Core gắn, không nhận trong payload.

| Trường | Kiểu | Bắt buộc / mặc định | Ý nghĩa và nguồn |
|---|---|---|---|
| `loai_viec` | string không rỗng | Có | Mã trong `LOAI_VIEC`; cổng AI kiểm tiếp, không đóng enum tại schema. |
| `van_ban` | string có ký tự khác khoảng trắng | Có | Văn bản gốc để đọc và kiểm trích dẫn; cổng AI kiểm tiếp bằng `strip()`. |
| `chi_dan` | string | Có; được rỗng | Chỉ dẫn công việc; không đưa dữ liệu chứng từ vào đây. |
| `truong` | array<string không rỗng> | Không; `[]` | Tên trường cần điền; bỏ qua tương đương lấy mọi trường AI trả. |
| `dinh_danh_da_biet` | array<chuỗi / cặp / object> | Không; `[]`, không `null` | Cặp đúng hai chuỗi `[gia_tri, nhom]`; object bắt buộc cả `gia_tri`, `nhom`, không khóa lạ; nhóm được rỗng. |
| `chi_cuc_bo` | boolean | Không; `false`, không `null` | `true`: 0 lời gọi Cloud; `false` không tự bật Cloud. |

Nguồn từng trường: quyết định AI-1b §1 (`cong_ai.py`: DTO A:275–292,
kiểm đầu vào A:1241–1246, chuẩn hóa định danh A:909–940). Grain là một yêu cầu;
không thêm khóa định danh riêng. Schema chặn khóa ngoài khai báo. Không thêm
giới hạn độ dài văn bản, số trường, số định danh thô hoặc enum nhóm.
Giới hạn 500 định danh vẫn áp sau chuẩn hóa trên nhánh Cloud.

`default` chỉ là annotation, không tự điền dữ liệu. Adapter AI-2 áp mặc định và
chuyển array sang tuple; khi `chi_cuc_bo=true`, dùng instance theo request với
`cloud_bat=False`, không đổi cấu hình instance chung. M9 và `mau_demo` bắt buộc
đặt `true`, kể cả khi Local lỗi, thiếu chắc chắn hoặc được chọn kiểm xác suất.
Local luôn có đường dùng; Cloud chỉ qua Mask v2 theo các điều kiện hiện có,
không che tiền/ngày, không đổi lịch/ngưỡng kiểm. Schema không thay kiểm quyền,
ngữ cảnh hoặc xác thực mã loại việc của Core/cổng AI.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ktt:contract:hoi_ai.v1",
  "title": "hoi_ai.v1 — đầu vào ai.hoi@1",
  "$comment": "Phien ban 1.0.0; Lead chot AI-1b §6 (31/10/2026).",
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

Ví dụ DEMO (không có dữ liệu thật), đủ ba dạng định danh:

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

Kiểm offline bằng Draft 2020-12, đăng ký URN từ `ky_thuat.json`, không tải mạng.
Tám ca âm phải bị bác: `van_ban` chỉ khoảng trắng, khóa lạ, tên trường rỗng,
`chi_cuc_bo=null`, cặp định danh một phần tử, object thiếu `nhom`,
`loai_viec` rỗng, `dinh_danh_da_biet=null` (chặt hơn nguồn nhận `None`, cố ý).
Giữ quy tắc phiên bản §2: thay schema đã phát hành phải dùng `$id` mới.
