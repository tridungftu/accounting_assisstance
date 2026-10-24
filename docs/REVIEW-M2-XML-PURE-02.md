# M2 XML PURE02 — closure static R1/R2

19/10/2026. **STATIC_R1_R2_CLOSED / RUNTIME02_CHƯA_ĐƯỢC_REVIEW_Ở_ĐÂY.** Root cung cấp actual27069 terminal0 `62738b`. Đọc frozen `var/codex-dieu-phoi/m2-xml-pure02-handoff-20261019-195359-021-edec5397/frozen/`; manifest240 `c4cfcb6bab62c0a6ed89523584e19ec3bb43d4d26e22cd0f1285cf2a4914094e`. So manifest01 `59d2456e12cca6d64e583855091a06982e8949f060f3d2d54432529924422c8c`: cùng240paths, chỉ reader/test đổi,238entry còn lại giữ hash. Report01 SHA `6527d70e6c55c40d24abcea52394c2c68586953e255da35201826665567856a7` giữ nguyên.

Đã đọc **toàn diff reader và tests01→02**, các block mới cùng context gọi tiếp, full report02 và repair handoff `7e010c10ebbf2a8faba4f95c21c38c35ace7eaf15376de7823be8cf7ef1eadf3`. Full reader/tests01 đã review tại `REVIEW-M2-XML-PURE-01.md` SHA `67f7137a0c37baa6e9d56566ed12d1184c07da7fbd0d5a4b868324e13550a513`; bản đó không bị sửa. Không dùng interim hoặc PASS01 thay kết quả02.

| Frozen02 artifact | SHA256 |
|---|---|
| Reader | `fcccdd39f0b2f3f4cb050da0a13ecf8f7f4b2aa19393bd6a43980c937f138bc2` |
| Tests | `2ee3bea9100aff38f11642e11f137a90754ff7ee189e8c2d08784945e298becc` |
| Report02 | `90eede1186f53464fdc0ba90469d5ffe528401feb56ca6961725ded8bee6dc39` |

## R1 — CLOSED static

Reader `49–51/353–357` pin `SUPPORTED_UNIT="CAI"`; `ho_tro` đòi **raw_unit và canonical_unit đều đúng CAI**, đồng thời giữ ratio1/1, encoding/domain/profile checks cũ. MatchingTHUNG1/1 không còn được nhận làm fact hỗ trợ. Dòng normalization phía sau không đổi: fact bị loại thì unit-definition/normalizedNULL, raw field/Decimal vẫn giữ; không mở conversion hoặc business matching.

New tests `466–492` có validCAI positive; THUNG native+factTHUNG với **rawref tính lại đúng bytes** để không fail do lỗi binding khác; nativeTHUNG+factCAI và factCAI→THUNG. Assert unsupported/unproven, normalized/unitNULL, source quantity EXACT10/Decimal10/native unit nguyên. Native unit đổi vẫn có identity và content khác đúng nguồn; chỉ proof khác không làm đổi golden content.

## R2 — CLOSED static

Reader `690–694` loại facts **trước dựng dòng** khi có một trong bốn contradiction đã chốt: `RAW_REF_MISMATCH`, `PROFILE_REF_MISMATCH`, `PROFILE_DOCUMENT_MISMATCH`, `PROFILE_PAYLOAD_CONFUSED`. Có candidate reason tường minh; không sửa native, không sửa identity/content policy. Đây là condition riêng, **không** dùng blanket `ctx_ok`/identity gate. `expected_raw_ref=None` vẫn NOT_BOUND; thiếu crosswalk/payload không bị coi là mâu thuẫn.

New tests `494–517` kiểm cả bốn negative, raw/rawref và exact Decimal/lexeme giữ nguyên, normalized/unitNULL; positive NOT_BOUND+no-crosswalk/payload và đúng ZIPbinding còn normalized10 + identity/golden digest. Existing missing-measurement-proof test vẫn giữ semantic và normalizedNULL. Không có profile/fixture/oracle/DTO change để hợp thức hóa counterexample.

Diff test chỉ thêm5methods với shared assertion helper, giữ27methods cũ; không thêm Store/config/DB/I/O ghi/temp cleanup hoặc test skip. Diff reader chỉ constant/ho_tro, fact-suppression và chú thích; strict paths/occurrences/mixed-content guards, identity/content/crosswalk/ZIP/immutability và API signatures không đổi. `that.py`/28fixtures và core thuộc238entry không đổi; không gọi legacy PASS01 là đã chạy lại02.

Không thấy blocker static còn lại trong phạm vi sửa02. **Cần root actual unit + cùng independent/supplemental controls sau terminal** trước nhãn pure verified; review này không khẳng định đã chạy hoặc đạt chúng. Parser pure vẫn không DB/API/UI/ROUTE/L11/financial/production-source acceptance, không quantity pool hoặc engine mới. M9 method-only/no calls/resume, noDelete tuyệt đối. Reviewer chỉ tạo tài liệu mới, không product edits/import/compile/test/SQL/HTTP/process.
