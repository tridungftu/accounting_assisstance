# Báo cáo M2 XML/ZIP PURE02 — CODE_ONLY

**19/10/2026 — CODE_ONLY / RUNTIME_UNRUN / CHƯA NGHIỆM THU.**

- **Phiên:** cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`.
- **Căn cứ:** `docs/GIAO-SUA-M2-XML-PURE-02.md` (root pin `7e010c10…1eadf3`), cùng `GIAO-CODE-M2-XML-PURE-01.md`, `M2-XML-PURE-DTO-01.json` và `M2-PROFILE-XML-DEMO-01.md`.
- **Baseline:** frozen240 `59d2456e…22c8c`; fixture manifest `43ad2825…2b177`, chỉ đọc. Report01 giữ nguyên.

**Coder chỉ dùng Read/Glob/Grep/Edit/Write.** Không execute, import, compile hay test, không process/network/Bash. Không đọc var/.env/private logs. Không sửa `that.py`/`fixture.py`/`primitives.py`, fixture, oracle, golden, profile, DTO doc hay common code. Không đụng M9.

**Mọi kết quả là UNRUN.** Không dùng PASS của candidate01 thay cho evidence của 02.

## 1. Thay đổi (3 target)

| File | Diff |
|---|---|
| `src/kho_tri_thuc/nguon/hoa_don_xml.py` | **R1:** thêm `SUPPORTED_UNIT = "CAI"`. `InvoiceMeasurementFacts.ho_tro` nay yêu cầu `raw_unit == canonical_unit == "CAI"` (thay vì chỉ `raw_unit == canonical_unit`), cùng các điều kiện cũ: 1/1, EXACT_TEXT_DECIMAL, ≤21/6, đúng profile document. Fact THUNG hoặc đơn vị tùy ý tự khai 1/1 → `MEASUREMENT_FACTS_UNSUPPORTED`, coi như không có fact.<br>**R2:** khi context có mâu thuẫn tường minh (`RAW_REF_MISMATCH`, `PROFILE_REF_MISMATCH`, `PROFILE_DOCUMENT_MISMATCH`, `PROFILE_PAYLOAD_CONFUSED`), fact đo lường của context đó không được dùng. Candidate reason: `MEASUREMENT_FACTS_NOT_APPLIED_CONTEXT_CONTRADICTION`. Kết quả cho dòng:<br>• normalized NULL;<br>• `unit_definition_ref` NULL;<br>• issue `UNIT_UNPROVEN`;<br>• giữ nguyên raw bytes/hash, field state/lexeme và Decimal exact.<br>Ngoài ra docstring thêm một dòng. |
| `tests/test_hoa_don_xml.py` | Giữ nguyên 27 test cũ; thêm lớp `Pure02ChuanHoa` (5 test). |
| `docs/BAO-CAO-M2-XML-PURE-02.md` | Báo cáo này. |

Không đổi:
- interface hay chữ ký API;
- DTO shape;
- quy tắc identity/content;
- crosswalk;
- ZIP;
- hash raw/container/member;
- content digest golden.

## 2. Test mới (UNRUN)

1. **CAI dương:** G01 + context hợp lệ → normalized `10`, unit `DEMO_EXACT_CAI_V1`, digest golden, không issue.
2. **R1, THUNG tự khai:** native `DVTinh` = THUNG, fact THUNG 1/1, raw ref tính lại đúng bytes mới.
   - `MEASUREMENT_FACTS_UNSUPPORTED`, `UNIT_UNPROVEN`, normalized NULL.
   - Quantity giữ EXACT `10` (Decimal); lexeme THUNG giữ nguyên.
   - Identity vẫn dẫn xuất được, digest khác golden.
3. **R1, các biến thể khác:**
   - Native THUNG + fact CAI → `UNIT_UNPROVEN`, normalized NULL.
   - Fact CAI→THUNG → unsupported, normalized NULL; digest golden không đổi (proof không đổi content).
4. **R2:** bốn mâu thuẫn (raw ref, profile ref, profile document, payload trùng document).
   - Mỗi ca có issue tương ứng và candidate reason mới.
   - Normalized/unit NULL; identity/content NULL.
   - Raw và raw ref giữ nguyên.
5. **R2, không mâu thuẫn:**
   - `expected_raw_ref=None` → chỉ `RAW_REF_NOT_BOUND`, không mismatch.
   - Thiếu crosswalk hoặc thiếu payload vẫn cho normalized `10` và identity/digest golden.
   - Binding ZIP đúng (G03 entry 1) vẫn normalized `10`.

## 3. Giới hạn

- **UNRUN:** root phải chạy lại cả 27 test cũ lẫn 5 test mới, cùng verifier độc lập.
- **Legacy:** `that.py` không đổi (pin `f7330761…ff1fc`); không gọi lại test legacy cũ là đã chạy cho 02.
- **Hard-code DEMO:** `SUPPORTED_UNIT` là quy tắc DEMO của profile này. Mọi quy đổi khác, kể cả THUNG, cần proof riêng ở gói L11 sau; pure reader không suy hệ số từ nhãn.
- **Phạm vi R2:** chỉ áp cho bốn mâu thuẫn raw/profile nêu trên.
  - Identity profile không hỗ trợ, hoặc công ty thiếu/lạ, vẫn chặn identity như gói 01, nhưng không chặn normalized của fact CAI hợp lệ.
  - Lý do: đó không phải mâu thuẫn binding raw/profile.
  - Root có thể yêu cầu mở rộng nếu cần.
- **Normalized không phải quyền nghiệp vụ:** không cấp business matching, quantity pool, financial eligibility hay L11.
- **Ngoài phạm vi:** không seed/DB/API/UI/L11/R15/R16.

Kết thúc phạm vi PURE02. Root terminal → freeze → review → tests riêng.
