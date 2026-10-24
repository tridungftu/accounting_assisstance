**L0-3a — Kết quả (24/10/2026, HEAD a1da3d4)**
Đã sửa root/src trong sys.path/PYTHONPATH; thêm `--runtime` chỉ dùng `python`, `duong_dan_phu_thuoc`; giữ lọc KHO_*/PG*. `.gitattributes` ghim LF đúng nhóm fixture/file có pin byte, ZIP giữ binary.
File đổi: `tests/run_suite.py`, `tools/chay_test_theo_module.py`, `.gitattributes`, báo cáo này. Lead commit: `[L0-3a] Sửa đường dẫn test, hỗ trợ runtime và ghim LF cho file có SHA pin`.
Python Codex 3.12.14 (`python` vắng trên PATH), từng module riêng, không runtime. Ô = ok/ERROR/FAIL/skip; treo = 0.

| Module (bỏ tiền tố `test_`) | Trước | Sau |
|---|---:|---:|
| `crm_khoi_dong` | 0/1/0/0 | 0/1/0/0 |
| `crm_ky_ket` | 0/1/0/0 | 0/1/0/0 |
| `crm_phan_tich` | 20/1/0/0 | 20/1/0/0 |
| `doi_chieu_hoa_don` | 27/5/0/0 | 27/5/0/0 |
| `hoa_don_xml` | 0/1/0/0 | 0/1/0/0 |
| `kho_10` | 43/0/15/0 | 43/0/15/0 |
| `m2_00b_quyen` | 1/23/0/0 | 1/23/0/0 |
| `m2_00b_tinh` | 3/16/0/0 | 3/16/0/0 |
| `m4_01b_tinh` | 0/1/0/0 | 0/1/0/0 |
| `m4_02b_http` | 0/1/0/0 | 0/1/0/0 |
| `m4_02b_k2` | 0/1/0/0 | 0/1/0/0 |
| `m4_02b_pure` | 0/1/0/0 | 0/1/0/0 |
| `m4_03a_full_basis_pg` | 0/1/0/0 | 0/1/0/0 |
| `m4_03b_common_pg` | 0/1/0/0 | 0/1/0/0 |
| `m4_master_dung_chung_http` | 0/1/0/0 | 0/1/0/0 |
| `m4_master_dung_chung_pg` | 0/1/0/0 | 0/1/0/0 |
| `m5_k2` | 5/5/0/26 | 5/5/0/26 |
| `source6_docx_tables` | 0/1/0/0 | 0/1/0/0 |
| `source6_lazy_excel` | 0/3/0/0 | 0/3/0/0 |
| `trich6_host` | 14/3/0/3 | 14/3/0/3 |
| `v13_backup_safety` | 9/5/0/0 | 9/5/0/0 |
| **Tổng** | **122/73/15/29** | **122/73/15/29** |

Kiểm runner **6/6 đạt** (runtime UTF-8/BOM/relative/validation, Python/dependencies, môi trường, import, subprocess thật); `git diff --check` đạt. Không sửa test/sản phẩm, không cài thư viện, không add/commit.
**Bị chặn:** runtime thật PermissionError, hai M2 chưa kiểm được psycopg về 0. Checkout 97 file LF bị từ chối `index.lock`, N3 trên đĩa giữ nguyên. Kiểm bytes Git xuất: kho_10 42/42 pin khớp; XML 9/9 tracked khớp, thiếu 18 XML/ZIP; L11 còn 18 pin tracked lệch cả trên Git (ngoài CRLF). Chưa chạy test với LF.
**So nền:** sáu lỗi thiếu `tests` hết, lộ N1: 02b thiếu `sql_duyet`; 03a/03b thiếu `tests/test_m4_03a_pg.py`; master thiếu `fixtures_m4.KET_LUAN_VND`. Hai module master đổi ID sang `TIEN_TRINH_CON_CHET(ma=1) khi chay nap module`: **chưa đạt cổng ID lỗi**. Hai ERROR ngoài NEN-TEST (`M2BFix01.test_b05_fix01_profiles_mapping_thieu_hoac_mo_ho_khong_lo_company_ngoai_quyen`, `test_b06_fix01_phien_sai_hoac_het_chan_truoc_doc_binding`) có sẵn trước sửa. N4b/c giữ nguyên.

Fixture ngoài `git ls-files` repo chính: **19 GIẢ / 0 NGHI THẬT** (đã đọc XML/member ZIP, không in giá trị). `X/`=`tests/fixtures/m2_invoice_xml/inputs/`; `L/`=`tests/fixtures/l11_quantity/native/`. Tên đều không có DEMO; D=DEMO trong nội dung. MST/tên: G=GIẢ, –=vắng; hai file đối kháng không có định danh; cả 19 kết luận GIẢ.

| Đường dẫn (repo chính) | Byte | D | MST/tên |
|---|---:|:---:|:---:|
| `L/new-thung-one.xml` | 480 | có | G/– |
| `X/G01-wrapped-positive.xml` | 523 | có | G/– |
| `X/G02-direct-legacy.xml` | 506 | có | G/– |
| `X/G03-identical-members.zip` | 1272 | có | G/– |
| `X/G03-identical-raw.xml` | 523 | có | G/– |
| `X/G04-purchase-a-padded.xml` | 521 | có | G/– |
| `X/G04-purchase-a-unpadded.xml` | 518 | có | G/– |
| `X/G04-purchase-b-padded.xml` | 521 | có | G/– |
| `X/G04-sale-a.xml` | 518 | có | G/– |
| `X/G05-order-a.xml` | 726 | có | G/– |
| `X/G05-order-b.xml` | 726 | có | G/– |
| `X/G05-stt-ambiguity.xml` | 1119 | có | G/– |
| `X/G06-quantity-boundaries.xml` | 2462 | có | G/– |
| `X/G07-malformed.xml` | 14 | không | –/– |
| `X/G07-missing-basis-and-natures.xml` | 1677 | có | G/– |
| `X/G07-unit-no-fact.xml` | 720 | có | G/– |
| `X/G07-unsupported-namespace.xml` | 552 | có | G/– |
| `X/G07-wrong-path-decoy.xml` | 117 | không | –/– |
| `X/G08-duplicate-name-partial.zip` | 1361 | có | G/– |

Lead: checkout file có `eol=lf`, đo lại sau N1; chạy hai M2 với runtime thật. Chưa chép/stage fixture; `.gitignore` giữ nguyên.
