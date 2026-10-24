# Báo cáo M5 — reader thuần nguồn kho #10, sửa 03 (dấu cộng đầu)

**19/10/2026 · tự báo cáo của coder, CHỜ ROOT freeze/review/chạy lại độc lập.** Báo cáo này không phải nghiệm thu; toàn bộ M5/L11/core/UI vẫn PENDING.

Căn cứ: `docs/GIAO-SUA-M5-READER-03.md` (SHA `7722c76d…62eaa9c`). Phạm vi: đúng một lỗi P2 về grammar.

## 1. Thay đổi tối thiểu

`src/kho_tri_thuc/nguon/kho_10.py`, sửa đúng một dòng:

```diff
-_FINITE_DEC = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
+_FINITE_DEC = re.compile(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
```

`_DEC` (regex chuẩn hóa exact-text `-?(\d+)(?:\.(\d+))?`), profile và eligibility đều giữ nguyên. Không bỏ dấu, không trim, không parse sang Number, không làm tròn.

`tests/test_kho_10.py`: thêm đúng một test `D_Repair02.test_r2b_plus_sign_text`, 48 test cũ giữ nguyên.

- **Positive `"+8"`** (sửa trong bộ nhớ từ K01): kind STRING, text và native giữ đúng `"+8"`, raw SHA bằng SHA của bytes thực, không có graph issue. Semantic và request đều có digest, và semantic khác K01. Test cũng kiểm normalized khác `"8"`, nghĩa là không bỏ dấu. Thực tế normalized là NULL, kèm `KHO_MEASUREMENT_NOT_EXACT`/HOLD, vì `_DEC` không nhận `+`. Baseline K01 vẫn đúng golden.
- **Negative `"++8"`, `"+"`, `" +8"`:** kind STRING, text giữ nguyên, có `KHO_FIELD_TYPE`, semantic và request NULL, normalized NULL.

`docs/BAO-CAO-M5-READER-03.md`: file mới.

Không sửa báo cáo 01/02, 43 fixture, DTO03, contract hay các file tái dùng. Không xóa hay di chuyển file nào. Không chạy git.

## 2. Kết quả lệnh

Lệnh: `python -X utf8 -m unittest discover -s tests -p test_kho_10.py`. Đây là lệnh duy nhất đã chạy, và chỉ chạy một lần.

```
Ran 49 tests in 0.074s
OK
```

| PASS | FAIL | ERROR | SKIP | UNRUN |
|---:|---:|---:|---:|---:|
| 49 | 0 | 0 | 0 | 0 |

49 = 48 test cũ + 1 test mới. Bước kiểm hash cuối vẫn cho thấy 43 fixture khớp manifest, trước và sau khi chạy.

Không chạy PG/SQL/Store/K2/M9/API/UI/network/Google/cloud/git. Không đọc `var`, `.env`, source app hay secret.

## 3. Giới hạn

- `"+8"` hiện qua được graph và hash, nhưng không được chuẩn hóa exact-text. Đây là chủ ý theo GIAO-SUA-03: không mở rộng `_DEC`. Nếu sau này muốn `+8` đủ điều kiện chuẩn hóa thì root cần chốt profile riêng.
- Tôi không có input của pluscounter, helper03 hay probe04 vì chúng nằm trong `var`. Test `"+8"` được dựng lại từ mô tả trong file giao, nên root cần chạy lại bộ kiểm độc lập.

Dừng tại đây để root freeze/review. Không mở việc khác.
