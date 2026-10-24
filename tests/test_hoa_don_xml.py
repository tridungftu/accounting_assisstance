"""M2 XML/ZIP pure reader — `kho_tri_thuc.nguon.hoa_don_xml` (gói M2-XML-PURE-01, CODE_ONLY; coder KHÔNG chạy).

Chỉ đọc fixture đã root stage `tests/fixtures/m2_invoice_xml/` (manifest pin SHA trước mọi assertion; thiếu/sai → FAIL, không skip/count0).
Oracle/golden/overlay là kỳ vọng độc lập (không lấy output parser làm expected). Counterexamples tự dựng chỉ DEMO, dựng từ bytes fixture.
Không DB/HTTP/process/network; không ghi file.
"""

from __future__ import annotations

import dataclasses
import io
import json
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json, sha256
from kho_tri_thuc.nguon import hoa_don_xml as m
from kho_tri_thuc.nguon.hoa_don_xml import (CompanyFact, InvoiceMeasurementFacts, InvoiceReadContext, LineCrosswalkFact, XmlRawRef,
                                            doc_goi_hoa_don_zip, doc_hoa_don_xml, ra_json)

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "m2_invoice_xml"
MANIFEST_SHA = "43ad28257ca646b9d43f45ed34a8c441131328cca1b576cf247b378224e2b177"
THAT_SHA = "f7330761f1ef8dbbcdc49429a09919f6135001dd0a50d804e6212af3de0ff1fc"


def _json(rel):
    return json.loads((FIX / rel).read_text("utf-8"))


def _raw(rel) -> bytes:
    return (FIX / rel).read_bytes()


ORACLE = _json("oracle.json")
OVERLAY_CTX = _json("overlay/trusted-contexts.json")
IDC = _json("overlay/identity-content-expected.json")
CROSSWALK = _json("overlay/line-crosswalk.json")
GROUP = {g["case"]: g["expected"] for g in ORACLE["groups"]}
IDENTITY = {i["ref"]: tuple(i["tuple"]) for i in IDC["identities"]}
CONTENT = {c["ref"]: c for c in IDC["contents"]}
OBS = {o["ref"]: o for o in IDC["observations"]}
CTX = {c["observation_ref"]: c for c in OVERLAY_CTX["contexts"]}


def facts() -> InvoiceMeasurementFacts:
    t = ORACLE["trusted_demo_facts"]
    q, u = t["quantity_encoding"], t["unit_fact"]
    return InvoiceMeasurementFacts(encoding_ref=q["ref"], unit_definition_ref=u["ref"], profile_document_sha256=ORACLE["profile_sha256"],
                                   raw_unit=u["raw_unit"], canonical_unit=u["canonical_unit"], numerator_text=u["conversion_numerator"],
                                   denominator_text=u["conversion_denominator"], max_lexical_digits=q["max_lexical_digits"],
                                   max_scale=q["max_scale"])


def company(key) -> CompanyFact:
    c = next(x for x in OVERLAY_CTX["companies"] if x["key"] == key)
    return CompanyFact(c["key"], c["pn"], c["mapping_ref"], c["revision"], c["scope_ref"])


def crosswalk_for(obs_ref) -> tuple:
    """Alias I_*/C_*/O_* chỉ là oracle test: resolve sang tuple định danh literal của file expected đã duyệt (reader chỉ SO với tuple tự dẫn xuất)."""
    return tuple(LineCrosswalkFact(r["mapping_ref"], CROSSWALK["revision"], IDENTITY[r["invoice_identity_ref"]], r["content_artifact_sha256"],
                                   r["source_locator"], r["source_ordinal"], r["logical_line_ref"], r["continuity_ref"])
                 for r in CROSSWALK["rows"] if r["observation"] == obs_ref)


def ctx_obs(obs_ref, *, with_crosswalk=True, with_facts=True, **sua) -> InvoiceReadContext:
    c = CTX[obs_ref]
    co = company(c["source_company_key"])
    assert (co.pn_alias, co.mapping_ref, co.mapping_revision, co.scope_ref) == (c["pn_alias"], c["company_mapping_ref"],
                                                                                c["company_mapping_revision"], c["scope_ref"])
    tham = dict(source_instance=c["source_instance"], source_profile_ref=c["source_profile_ref"],
                profile_document_sha256=c["source_profile_document_sha256"], profile_payload_sha256=c["source_profile_sha256"],
                profile_payload_binding=c["source_profile_payload_binding"], company=co, identity_profile_ref=c["identity_profile_ref"],
                expected_raw_ref=XmlRawRef.tu_dict(c["raw_ref"]), line_crosswalk=crosswalk_for(obs_ref) if with_crosswalk else (),
                resolved_invoice_measurement_facts=facts() if with_facts else None)
    tham.update(sua)
    return InvoiceReadContext(**tham)


def ctx_facts(company_key="DEMO_M2_COMPANY_A", **sua) -> InvoiceReadContext:
    """Context tin cậy không bind raw ref/crosswalk (dùng cho nhóm không có observation overlay)."""
    tham = dict(source_instance=OVERLAY_CTX["source"]["instance"], source_profile_ref=m.PROFILE_REF,
                profile_document_sha256=ORACLE["profile_sha256"], company=company(company_key), identity_profile_ref=m.IDENTITY_PROFILE_REF,
                resolved_invoice_measurement_facts=facts())
    tham.update(sua)
    return InvoiceReadContext(**tham)


def zip_members(raw_zip: bytes) -> list[tuple[int, str, bytes]]:
    """Đọc độc lập phía test (infolist + open(ZipInfo)), không qua product."""
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as z:
        out = []
        for i, info in enumerate(z.infolist(), 1):
            try:
                with z.open(info) as fh:
                    out.append((i, info.filename, fh.read()))
            except Exception:  # noqa: BLE001
                out.append((i, info.filename, None))
        return out


G01_RAW = _raw("inputs/G01-wrapped-positive.xml")


def bien_the(*cap: tuple[bytes, bytes]) -> bytes:
    raw = G01_RAW
    for a, b in cap:
        assert a in raw, a
        raw = raw.replace(a, b, 1)
    return raw


class FixturePins(unittest.TestCase):
    def test_manifest_va_file_dung_pin(self):
        raw = _raw("manifest.json")
        self.assertEqual(sha256(raw), MANIFEST_SHA, "manifest fixture khác root pin — FAIL, không skip")
        man = json.loads(raw.decode("utf-8"))
        for f in man["files"]:
            b = _raw(f["path"])
            self.assertEqual((sha256(b), len(b)), (f["sha256"], f["bytes"]), f["path"])
        self.assertEqual(len(man["files"]), man["copied_file_count"])
        self.assertEqual(sum(f["path"].endswith(".xml") for f in man["files"]), 16)
        self.assertEqual(sum(f["path"].endswith(".zip") for f in man["files"]), 2)
        self.assertEqual(sha256(_raw("profile.md")), m.PROFILE_DOCUMENT_SHA256)
        self.assertEqual(len(ORACLE["groups"]), 8)
        self.assertEqual(sum(len(g["artifacts"]) for g in ORACLE["groups"]), 18)

    def test_that_py_nguyen_va_module_khong_goi_legacy(self):
        that = ROOT / "src" / "kho_tri_thuc" / "nguon" / "that.py"
        self.assertEqual(sha256(that.read_bytes()), THAT_SHA)
        src = (ROOT / "src" / "kho_tri_thuc" / "nguon" / "hoa_don_xml.py").read_text("utf-8")
        for cam in ("from .that", "import that", "parse_invoice_xml(", "_xml_rows(", "import uuid", "now_utc(", "datetime.now", "os.environ",
                    "open(path", "Path(", "read_bytes(", "write_immutable", "float(", "money_minor(", "normalize_text(", "text_id("):
            self.assertNotIn(cam, src, cam)
        self.assertIn("from ..ha_tang.primitives import DataError, canonical_json, date_iso, sha256", src)  # reuse đúng primitives


class OracleTruong(unittest.TestCase):
    def kiem_header(self, res, exp):
        self.assertEqual({f.name: [o.ra_dict() for o in f.occurrences] for f in res.header_fields}, {k: [v] for k, v in exp.items()})

    def kiem_dong(self, line, exp, *, logical=None):
        self.assertEqual(line.source_ordinal, exp["ordinal"])
        self.assertEqual(line.source_locator, f"/HDon/DLHDon/NDHDon/DSHHDVu/HHDVu[{exp['ordinal']}]")
        self.assertEqual({f.name: [o.ra_dict() for o in f.occurrences] for f in line.fields}, {k: [v] for k, v in exp["fields"].items()})
        q = exp["quantity"]
        self.assertEqual((line.quantity.exact_text, line.quantity.lexical_digits, line.quantity.scale, line.normalized_quantity_text,
                          line.unit_definition_ref), (q["exact_decimal"], q["lexical_digits"], q["scale"], q["normalized_decimal"],
                                                      q["unit_fact_ref"]), exp["ordinal"])
        if q["exact_decimal"] is not None:
            self.assertEqual(line.quantity.exact_value, Decimal(q["exact_decimal"]))
            self.assertIsInstance(line.quantity.exact_value, Decimal)
        else:
            self.assertIsNone(line.quantity.exact_value)
        self.assertEqual(line.nature, exp["nature"])
        self.assertEqual([i.code for i in line.issues], exp["issues"], exp["ordinal"])
        self.assertEqual(line.logical_line_ref, logical if logical is not None else exp["logical_line_key"])
        self.assertIsNone(line.row_raw_sha256)

    def test_g01_wrapped_positive_golden(self):
        raw = _raw("inputs/G01-wrapped-positive.xml")
        res = doc_hoa_don_xml(raw, ctx_obs("O_G01"), artifact_name="G01-wrapped-positive.xml")
        e = GROUP["G01"]
        self.assertEqual(res.shape, "SUPPORTED_SUBSET")
        self.kiem_header(res, e["header"])
        self.assertEqual(len(res.lines), 1)
        self.kiem_dong(res.lines[0], e["lines"][0], logical="DEMO_LINE_G01_A")
        self.assertEqual((res.lines[0].continuity_ref, res.lines[0].crosswalk_ref), ("DEMO_CONTINUITY_G01_SAME_CONTENT", "CW_G01_R1"))
        self.assertEqual(res.canonical_identity, IDENTITY["I_G01_A"])
        self.assertEqual(res.canonical_identity[:2], (e["declared_pn"], e["direction"]))
        self.assertEqual(res.semantic_envelope.ra_dict(), CONTENT["C_G01"]["envelope"])
        self.assertEqual(res.semantic_digest, CONTENT["C_G01"]["semantic_sha256"])
        self.assertEqual(res.semantic_digest, sha256(canonical_json(CONTENT["C_G01"]["envelope"]).encode("utf-8")))
        self.assertEqual((res.issues, res.candidate_reasons), ((), ()))
        self.assertEqual((res.raw_xml, res.raw_ref), (raw, XmlRawRef(sha256(raw), len(raw))))
        self.assertEqual((res.native_fiscal_status, res.business_promotion, res.L11_eligibility, res.current_DB_basis_sha256,
                          res.profile_payload_sha256, res.profile_payload_binding), ("UNKNOWN", "NOT_PERFORMED", "NOT_EVALUATED", None, None, "NOT_BOUND"))
        self.assertNotEqual(res.semantic_digest, res.raw_ref.native_sha256)  # content hash ≠ raw hash

    def test_g02_direct_legacy_khong_strict(self):
        for ctx in (None, ctx_facts()):
            res = doc_hoa_don_xml(_raw("inputs/G02-direct-legacy.xml"), ctx)
            self.assertEqual((res.shape, res.lines, [i.code for i in res.issues]), ("UNSUPPORTED_PATH", (), GROUP["G02"]["issues"]))
            self.assertIsNone(res.semantic_digest)
            self.assertEqual(res.raw_xml, _raw("inputs/G02-direct-legacy.xml"))

    def test_g05_ambiguity_giu_raw_khong_khoa_logic(self):
        res = doc_hoa_don_xml(_raw("inputs/G05-stt-ambiguity.xml"), ctx_obs("O_G05_AMBIG"))
        exp = GROUP["G05"]["ambiguity_lines"]
        self.assertEqual(len(res.lines), len(exp))
        for line, e in zip(res.lines, exp):
            self.kiem_dong(line, e)
        self.assertEqual(res.semantic_digest, CONTENT["C_G05_AMBIG"]["semantic_sha256"])  # hash ordered raw states, không logical key
        self.assertTrue(all(l.logical_line_ref is None for l in res.lines))

    def test_g06_quantity_boundaries(self):
        res = doc_hoa_don_xml(_raw("inputs/G06-quantity-boundaries.xml"), ctx_facts())
        exp = GROUP["G06"]["lines"]
        self.assertEqual(len(res.lines), 15)
        for line, e in zip(res.lines, exp):
            self.kiem_dong(line, e)
        self.assertEqual(res.lines[3].quantity.exact_value, Decimal("9007199254740993"))  # 2^53+1, không float
        self.assertEqual(res.lines[1].quantity.exact_value, Decimal("0"))  # zero là fact, không phải thiếu
        self.assertEqual(res.lines[4].quantity.state, "OVER_DOMAIN")
        self.assertEqual(res.lines[8].quantity.state, "OVER_DOMAIN")
        self.assertEqual([res.lines[i].quantity.state for i in (5, 6, 9)], ["EMPTY", "ABSENT", "INVALID"])
        self.assertEqual(res.lines[0].source_amount.state, "ABSENT")  # tiền thiếu không điền 0

    def test_g07_missing_basis_natures_dchat(self):
        res = doc_hoa_don_xml(_raw("inputs/G07-missing-basis-and-natures.xml"), ctx_facts())
        e = GROUP["G07"]
        self.kiem_header(res, e["missing_basis"]["header"])
        header_codes = {i.code for i in res.issues if i.locator.split("#", 1)[1].startswith("/HDon/DLHDon/TTChung")}
        self.assertEqual(header_codes, set(e["missing_basis"]["issues"]))
        for line, x in zip(res.lines, e["nature_lines"]):
            self.kiem_dong(line, x)
        self.assertIn("UNSUPPORTED_ELEMENT", {i.code for i in res.issues})  # DChat giữ bằng chứng, không alias
        self.assertEqual(res.lines[6].field("TChat").occurrences[0].state, "ABSENT")
        self.assertIsNone(res.canonical_identity)  # thiếu mẫu số
        self.assertIsNone(res.semantic_digest)
        self.assertEqual(len(res.lines), 7)  # candidate giữ

    def test_g07_namespace_path_malformed_unit(self):
        e = GROUP["G07"]
        for rel, shape, key in (("inputs/G07-unsupported-namespace.xml", "UNSUPPORTED_NAMESPACE", "namespace"),
                                ("inputs/G07-wrong-path-decoy.xml", "UNSUPPORTED_PATH", "wrong_path"),
                                ("inputs/G07-malformed.xml", "XML_MALFORMED", "malformed")):
            with self.subTest(rel=rel):
                raw = _raw(rel)
                res = doc_hoa_don_xml(raw, ctx_facts())
                self.assertEqual((res.shape, res.lines, res.header_fields), (shape, (), ()))
                self.assertEqual([i.code for i in res.issues], e[key]["issues"])
                self.assertEqual(res.raw_xml, raw)
                self.assertIsNone(res.semantic_digest)
        res = doc_hoa_don_xml(_raw("inputs/G07-unit-no-fact.xml"), ctx_facts())
        for line, x in zip(res.lines, e["unproven_unit_lines"]):
            self.kiem_dong(line, x)


class OverlayIdentityContent(unittest.TestCase):
    def doc_obs(self, ref):
        o = OBS[ref]
        raw = _raw(o["artifact"])
        if o["artifact"].endswith(".zip"):
            z = doc_goi_hoa_don_zip(raw, (ctx_obs(ref),))
            entry = z.entries[o["entry_ordinal"] - 1]
            self.assertEqual(entry.state, "PARSED")
            return entry.result
        return doc_hoa_don_xml(raw, ctx_obs(ref))

    def test_11_observations_6_identity_8_content(self):
        ids, contents = set(), set()
        for ref, o in OBS.items():
            with self.subTest(ref=ref):
                res = self.doc_obs(ref)
                self.assertEqual(res.canonical_identity, IDENTITY[o["identity"]])
                self.assertEqual(res.semantic_digest, o["semantic_sha256"])
                self.assertEqual(res.semantic_digest, CONTENT[o["content"]]["semantic_sha256"])
                self.assertEqual(res.semantic_envelope.ra_dict(), CONTENT[o["content"]]["envelope"])
                self.assertEqual(res.header("SHDon").occurrences[0].lexeme, o["raw_number"])
                self.assertEqual(dataclasses.asdict(res.raw_ref), {**{"container_sha256": None, "entry_ordinal": None, "entry_name": None},
                                                                   **o["raw_ref"]})
                self.assertNotIn("RAW_REF_MISMATCH", {i.code for i in res.issues})
                ids.add(res.canonical_identity)
                contents.add(res.semantic_digest)
        self.assertEqual((len(OBS), len(ids), len(contents)), (11, 6, 8))

    def test_g01_g03_cung_identity_content_4_observations(self):
        res = [self.doc_obs(r) for r in ("O_G01", "O_G03_RAW", "O_G03_ZIP_1", "O_G03_ZIP_2")]
        self.assertEqual(len({r.canonical_identity for r in res}), 1)
        self.assertEqual(len({r.semantic_digest for r in res}), 1)
        self.assertEqual(len({(r.raw_ref.container_sha256, r.raw_ref.entry_ordinal) for r in res}), 3)  # raw, zip#1, zip#2 (raw và G01 cùng bytes)
        self.assertTrue(all(r.lines[0].logical_line_ref == "DEMO_LINE_G01_A" for r in res))

    def test_g04_padded_unpadded_pn_direction(self):
        a_pad, a_unpad, b_pad, sale = (self.doc_obs(r) for r in ("O_G04_A_PAD", "O_G04_A_UNPAD", "O_G04_B_PAD", "O_G04_SALE_A"))
        self.assertEqual(a_pad.canonical_identity, a_unpad.canonical_identity)  # cùng định danh (strip 0 bằng chuỗi)
        self.assertNotEqual(a_pad.semantic_digest, a_unpad.semantic_digest)  # nội dung raw khác
        self.assertNotEqual(a_pad.canonical_identity, b_pad.canonical_identity)  # PN khác
        self.assertEqual(sale.canonical_identity[1], "BAN_RA")
        self.assertEqual(len({a_pad.canonical_identity, b_pad.canonical_identity, sale.canonical_identity}), 3)

    def test_g05_reorder_2_logical_4_bridges(self):
        a, b = self.doc_obs("O_G05_A"), self.doc_obs("O_G05_B")
        self.assertEqual([l.logical_line_ref for l in a.lines], ["DEMO_LINE_G05_A", "DEMO_LINE_G05_B"])
        self.assertEqual([l.logical_line_ref for l in b.lines], ["DEMO_LINE_G05_B", "DEMO_LINE_G05_A"])
        self.assertEqual(len({l.logical_line_ref for l in a.lines + b.lines}), 2)
        self.assertEqual(sum(l.logical_line_ref is not None for l in a.lines + b.lines), 4)
        self.assertEqual(a.canonical_identity, b.canonical_identity)
        self.assertNotEqual(a.semantic_digest, b.semantic_digest)
        amb = self.doc_obs("O_G05_AMBIG")
        self.assertEqual(sum(l.logical_line_ref is not None for l in amb.lines), 0)


class ZipReader(unittest.TestCase):
    def test_g03_zip_hai_entry_khac_ordinal(self):
        raw = _raw("inputs/G03-identical-members.zip")
        z = doc_goi_hoa_don_zip(raw, (ctx_obs("O_G03_ZIP_1"), ctx_obs("O_G03_ZIP_2")), archive_name="G03.zip")
        self.assertEqual((z.container_sha256, z.byte_length, z.artifact_coverage), (sha256(raw), len(raw), "COMPLETE"))
        self.assertEqual([(e.entry_ordinal, e.entry_name, e.state) for e in z.entries], [(1, "invoice-a.xml", "PARSED"), (2, "invoice-b.xml", "PARSED")])
        self.assertEqual({e.raw_sha256 for e in z.entries}, {sha256(G01_RAW)})
        self.assertEqual((z.period_completeness, z.source_revocation), ("UNKNOWN", "NOT_INFERRED"))

    def test_g08_duplicate_name_partial(self):
        raw = _raw("inputs/G08-duplicate-name-partial.zip")
        e = GROUP["G08"]
        mem = zip_members(raw)
        ctxs = tuple(ctx_facts(expected_raw_ref=XmlRawRef(sha256(b), len(b), m.MEDIA_XML, sha256(raw), i, n)) for i, n, b in mem if b is not None)
        z = doc_goi_hoa_don_zip(raw, ctxs)
        self.assertEqual(len(z.entries), e["zip_entry_count"])
        self.assertEqual([(x.entry_ordinal, x.entry_name) for x in z.entries], [(x["ordinal"], x["name"]) for x in e["members"]])
        self.assertEqual([x.state for x in z.entries], ["PARSED", "PARSED", "CANDIDATE"])
        self.assertEqual(sum(x.state == "PARSED" for x in z.entries), e["parsed_member_count"])
        self.assertEqual([i.code for i in z.entries[2].result.issues], ["XML_MALFORMED"])
        self.assertEqual(z.artifact_coverage, e["coverage"])
        self.assertEqual(sum(i.code == "ZIP_DUPLICATE_ENTRY_NAME" for i in z.issues), e["duplicate_name_count"])
        self.assertNotEqual(z.entries[0].raw_sha256, z.entries[1].raw_sha256)  # hai same.xml là hai entry, không gộp
        for entry, exp in zip(z.entries[:2], e["members"][:2]):
            for line, x in zip(entry.result.lines, exp["lines"]):
                OracleTruong.kiem_dong(self, line, x)
        self.assertEqual(z.period_completeness, "UNKNOWN")

    def test_context_zip_phai_khop_dung_khe(self):
        raw = _raw("inputs/G03-identical-members.zip")
        dung = ctx_obs("O_G03_ZIP_1")
        r = dung.expected_raw_ref
        sai_container = dataclasses.replace(dung, expected_raw_ref=dataclasses.replace(r, container_sha256="0" * 64))
        sai_ordinal = dataclasses.replace(dung, expected_raw_ref=dataclasses.replace(r, entry_ordinal=2))  # tên invoice-a ở ordinal 2: không khớp
        z = doc_goi_hoa_don_zip(raw, (sai_container, sai_ordinal))
        self.assertEqual([i.code for i in z.issues], ["CONTEXT_UNMATCHED", "CONTEXT_UNMATCHED"])
        self.assertTrue(all(e.result.canonical_identity is None for e in z.entries))
        z2 = doc_goi_hoa_don_zip(raw, (dung, dung))
        self.assertIn("CONTEXT_AMBIGUOUS", {i.code for i in z2.issues})
        self.assertIsNone(z2.entries[0].result.canonical_identity)
        sai_sha = dataclasses.replace(dung, expected_raw_ref=dataclasses.replace(r, native_sha256="1" * 64))
        z3 = doc_goi_hoa_don_zip(raw, (sai_sha,))
        self.assertIn("RAW_REF_MISMATCH", {i.code for i in z3.entries[0].result.issues})
        self.assertIsNone(z3.entries[0].result.semantic_digest)
        self.assertEqual(z3.entries[0].result.header("SHDon").occurrences[0].lexeme, "000001")  # native giữ nguyên

    def test_zip_hong_giu_container(self):
        raw = b"PK\x03\x04 not a zip"
        z = doc_goi_hoa_don_zip(raw)
        self.assertEqual((z.entries, [i.code for i in z.issues], z.artifact_coverage, z.raw_zip), ((), ["ZIP_MALFORMED"], "PARTIAL", raw))


class CounterExamples(unittest.TestCase):
    def test_thieu_context_giu_ung_vien(self):
        res = doc_hoa_don_xml(G01_RAW)
        self.assertEqual((res.canonical_identity, res.semantic_digest), (None, None))
        self.assertIn("CONTEXT_ABSENT", res.candidate_reasons)
        self.assertEqual(res.header("SHDon").occurrences[0].lexeme, "000001")
        line = res.lines[0]
        self.assertEqual((line.quantity.exact_text, line.normalized_quantity_text, [i.code for i in line.issues]), ("10", None, ["UNIT_UNPROVEN"]))

    def test_thieu_proof_giu_identity_normalized_null(self):
        res = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", with_facts=False))
        self.assertEqual((res.canonical_identity, res.semantic_digest), (IDENTITY["I_G01_A"], CONTENT["C_G01"]["semantic_sha256"]))
        self.assertIsNone(res.lines[0].normalized_quantity_text)
        self.assertIn("UNIT_UNPROVEN", [i.code for i in res.lines[0].issues])
        f = dataclasses.replace(facts(), numerator_text="2")
        res2 = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", resolved_invoice_measurement_facts=f))
        self.assertIn("MEASUREMENT_FACTS_UNSUPPORTED", {i.code for i in res2.issues})
        self.assertIsNone(res2.lines[0].normalized_quantity_text)
        self.assertEqual(res2.semantic_digest, CONTENT["C_G01"]["semantic_sha256"])  # proof không đổi content hash

    def test_cong_ty_la_va_hai_phia(self):
        co = CompanyFact("DEMO_M2_OTHER", "PN_DEMO_X", "MAP_X", 1, "SCOPE_X")
        res = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", company=co, line_crosswalk=()))
        self.assertIn("COMPANY_UNMATCHED", res.candidate_reasons)
        self.assertIsNone(res.canonical_identity)
        hai = bien_the((b"<MST>DEMO_M2_SUPPLIER</MST>", b"<MST>DEMO_M2_COMPANY_A</MST>"))
        res2 = doc_hoa_don_xml(hai, ctx_facts())
        self.assertIn("COMPANY_BOTH_SIDES", {i.code for i in res2.issues})
        self.assertIsNone(res2.canonical_identity)

    def test_so_hoa_don_sai_va_toan_0(self):
        res = doc_hoa_don_xml(bien_the((b"<SHDon>000001</SHDon>", b"<SHDon>00A1</SHDon>")), ctx_facts())
        self.assertIn("NUMBER_INVALID", {i.code for i in res.issues})
        self.assertIsNone(res.canonical_identity)
        res0 = doc_hoa_don_xml(bien_the((b"<SHDon>000001</SHDon>", b"<SHDon>0000</SHDon>")), ctx_facts())
        self.assertEqual(res0.canonical_identity[5], "0")
        res_u = doc_hoa_don_xml(bien_the((b"<SHDon>000001</SHDon>", b"<SHDon>\xef\xbc\x91</SHDon>")), ctx_facts())  # chữ số fullwidth
        self.assertIsNone(res_u.canonical_identity)

    def test_profile_document_va_payload(self):
        res = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", profile_document_sha256="0" * 64))
        self.assertIn("PROFILE_DOCUMENT_MISMATCH", {i.code for i in res.issues})
        self.assertEqual((res.canonical_identity, res.semantic_digest), (None, None))
        res2 = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", profile_payload_sha256=ORACLE["profile_sha256"]))
        self.assertIn("PROFILE_PAYLOAD_CONFUSED", {i.code for i in res2.issues})
        self.assertIsNone(res2.semantic_digest)

    def test_raw_ref_mau_thuan_khong_ghi_de_native(self):
        res = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", expected_raw_ref=XmlRawRef.tu_dict(CTX["O_G04_A_PAD"]["raw_ref"])))
        self.assertIn("RAW_REF_MISMATCH", {i.code for i in res.issues})
        self.assertEqual((res.canonical_identity, res.semantic_digest), (None, None))
        self.assertEqual(res.header("SHDon").occurrences[0].lexeme, "000001")
        zip_ctx = ctx_obs("O_G03_ZIP_1")  # binding ZIP dùng cho XML rời → mâu thuẫn
        self.assertIn("RAW_REF_MISMATCH", {i.code for i in doc_hoa_don_xml(G01_RAW, zip_ctx).issues})

    def test_crosswalk_mismatch_khong_ap(self):
        base = crosswalk_for("O_G01")[0]
        cases = {"CROSSWALK_IDENTITY_MISMATCH": dataclasses.replace(base, invoice_identity_binding=IDENTITY["I_G04_B_7"]),
                 "CROSSWALK_LOCATOR_MISMATCH": dataclasses.replace(base, source_locator="/HDon/DLHDon/NDHDon/DSHHDVu/HHDVu[2]"),
                 "CROSSWALK_ARTIFACT_MISMATCH": dataclasses.replace(base, content_artifact_sha256="2" * 64)}
        for code, fct in cases.items():
            with self.subTest(code=code):
                res = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", line_crosswalk=(fct,)))
                self.assertIn(code, {i.code for i in res.issues})
                self.assertIsNone(res.lines[0].logical_line_ref)
                self.assertEqual(res.semantic_digest, CONTENT["C_G01"]["semantic_sha256"])
        res = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", line_crosswalk=(base, dataclasses.replace(base, logical_line_ref="KHAC"))))
        self.assertIn("CROSSWALK_DUPLICATE_LINE", {i.code for i in res.issues})
        self.assertIsNone(res.lines[0].logical_line_ref)
        # cùng artifact nhưng PN khác (intercompany): crosswalk của PN A không áp sang định danh PN B
        res_b = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", company=company("DEMO_M2_COMPANY_B")))
        self.assertIsNone(res_b.lines[0].logical_line_ref)

    def test_scalar_trung_mixed_entity_doctype(self):
        trung = bien_the((b"<SLuong>10</SLuong>", b"<SLuong>10</SLuong><SLuong>11</SLuong>"))
        res = doc_hoa_don_xml(trung, ctx_obs("O_G01", expected_raw_ref=None, line_crosswalk=()))
        f = res.lines[0].field("SLuong")
        self.assertEqual([o.lexeme for o in f.occurrences], ["10", "11"])  # giữ mọi occurrence, không chọn
        self.assertIn("QUANTITY_AMBIGUOUS", [i.code for i in res.lines[0].issues])
        self.assertEqual(res.lines[0].quantity.state, "INVALID")
        self.assertIsNotNone(res.canonical_identity)
        self.assertIsNone(res.semantic_digest)
        hd = bien_the((b"<SHDon>000001</SHDon>", b"<SHDon>000001</SHDon><SHDon>000002</SHDon>"))
        res_h = doc_hoa_don_xml(hd, ctx_facts())
        self.assertIn("FIELD_DUPLICATE", {i.code for i in res_h.issues})
        self.assertIsNone(res_h.canonical_identity)
        mixed = bien_the((b"<THHDVu>DEMO hang A</THHDVu>", b"<THHDVu>DEMO<b>x</b>hang</THHDVu>"))
        res_m = doc_hoa_don_xml(mixed, ctx_facts())
        self.assertIn("FIELD_MIXED_CONTENT", {i.code for i in res_m.issues})
        self.assertEqual(res_m.lines[0].field("THHDVu").occurrences[0].lexeme, "DEMO")  # không ghép itertext
        self.assertIsNone(res_m.semantic_digest)
        ent = bien_the((b"<THHDVu>DEMO hang A</THHDVu>", b"<THHDVu>DEMO &amp; A</THHDVu>"))
        res_e = doc_hoa_don_xml(ent, ctx_facts())
        self.assertIn("XML_LITERAL_LEXEME_NOT_PROVEN", {i.code for i in res_e.issues})
        self.assertEqual(res_e.lines[0].field("THHDVu").occurrences[0].lexeme, "DEMO & A")
        self.assertIsNone(res_e.semantic_digest)
        cdata = bien_the((b"<THHDVu>DEMO hang A</THHDVu>", b"<THHDVu><![CDATA[DEMO hang A]]></THHDVu>"))
        self.assertIsNone(doc_hoa_don_xml(cdata, ctx_facts()).semantic_digest)
        dt = b'<?xml version="1.0"?><!DOCTYPE HDon [<!ENTITY x "y">]><HDon/>'
        res_d = doc_hoa_don_xml(dt, ctx_facts())
        self.assertEqual((res_d.shape, [i.code for i in res_d.issues]), ("UNSUPPORTED_INPUT", ["XML_DOCTYPE_UNSUPPORTED"]))
        ws = bien_the((b"<KHHDon>DEMO_SERIES_A</KHHDon>", b"<KHHDon> DEMO_SERIES_A</KHHDon>"))  # không trim
        self.assertEqual(doc_hoa_don_xml(ws, ctx_facts()).header("KHHDon").occurrences[0].lexeme, " DEMO_SERIES_A")


class Pure02ChuanHoa(unittest.TestCase):
    """PURE02: R1 chỉ CAI 1/1 được chuẩn hóa (THUNG/đơn vị tùy ý fail-closed); R2 context mâu thuẫn không cấp normalized từ fact của nó."""

    def kiem_khong_chuan_hoa(self, res, unit_lexeme):
        line = res.lines[0]
        self.assertEqual((line.quantity.state, line.quantity.exact_text, line.quantity.exact_value), ("EXACT", "10", Decimal("10")))
        self.assertEqual((line.normalized_quantity_text, line.unit_definition_ref), (None, None))
        self.assertIn("UNIT_UNPROVEN", [i.code for i in line.issues])
        self.assertEqual(line.field("DVTinh").occurrences[0].lexeme, unit_lexeme)  # native đơn vị giữ nguyên
        self.assertEqual(line.field("SLuong").occurrences[0].ra_dict(), {"state": "TEXT", "lexeme": "10"})

    def test_cai_duong_van_chuan_hoa(self):
        res = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01"))
        self.assertEqual((res.lines[0].normalized_quantity_text, res.lines[0].unit_definition_ref), ("10", "DEMO_EXACT_CAI_V1"))
        self.assertEqual(res.semantic_digest, CONTENT["C_G01"]["semantic_sha256"])
        self.assertEqual(res.issues, ())

    def test_r1_thung_fact_tu_khai_1_1_bi_tu_choi(self):
        raw = bien_the((b"<DVTinh>CAI</DVTinh>", b"<DVTinh>THUNG</DVTinh>"))
        thung = dataclasses.replace(facts(), raw_unit="THUNG", canonical_unit="THUNG", unit_definition_ref="DEMO_THUNG_SELF_DECLARED")
        res = doc_hoa_don_xml(raw, ctx_obs("O_G01", expected_raw_ref=XmlRawRef(sha256(raw), len(raw)), line_crosswalk=(),
                                           resolved_invoice_measurement_facts=thung))
        self.assertNotIn("RAW_REF_MISMATCH", {i.code for i in res.issues})  # raw ref tính đúng bytes mới
        self.assertIn("MEASUREMENT_FACTS_UNSUPPORTED", {i.code for i in res.issues})
        self.kiem_khong_chuan_hoa(res, "THUNG")
        self.assertEqual(res.canonical_identity, IDENTITY["I_G01_A"])  # identity/content native vẫn đủ căn cứ
        self.assertIsNotNone(res.semantic_digest)
        self.assertNotEqual(res.semantic_digest, CONTENT["C_G01"]["semantic_sha256"])  # đơn vị native khác → content khác

    def test_r1_don_vi_native_khac_fact_cai_va_fact_cai_sang_thung(self):
        raw = bien_the((b"<DVTinh>CAI</DVTinh>", b"<DVTinh>THUNG</DVTinh>"))
        res = doc_hoa_don_xml(raw, ctx_obs("O_G01", expected_raw_ref=XmlRawRef(sha256(raw), len(raw)), line_crosswalk=()))
        self.kiem_khong_chuan_hoa(res, "THUNG")
        cai_thung = dataclasses.replace(facts(), canonical_unit="THUNG")
        res2 = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", resolved_invoice_measurement_facts=cai_thung))
        self.assertIn("MEASUREMENT_FACTS_UNSUPPORTED", {i.code for i in res2.issues})
        self.kiem_khong_chuan_hoa(res2, "CAI")
        self.assertEqual(res2.semantic_digest, CONTENT["C_G01"]["semantic_sha256"])

    def test_r2_context_mau_thuan_khong_cap_normalized(self):
        cases = {"RAW_REF_MISMATCH": dict(expected_raw_ref=XmlRawRef.tu_dict(CTX["O_G04_A_PAD"]["raw_ref"])),
                 "PROFILE_REF_MISMATCH": dict(source_profile_ref="DEMO_PROFILE_KHAC"),
                 "PROFILE_DOCUMENT_MISMATCH": dict(profile_document_sha256="0" * 64),
                 "PROFILE_PAYLOAD_CONFUSED": dict(profile_payload_sha256=ORACLE["profile_sha256"])}
        for code, sua in cases.items():
            with self.subTest(code=code):
                res = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", **sua))
                self.assertIn(code, {i.code for i in res.issues})
                self.assertIn("MEASUREMENT_FACTS_NOT_APPLIED_CONTEXT_CONTRADICTION", res.candidate_reasons)
                self.kiem_khong_chuan_hoa(res, "CAI")
                self.assertEqual((res.canonical_identity, res.semantic_digest), (None, None))
                self.assertEqual((res.raw_xml, res.raw_ref), (G01_RAW, XmlRawRef(sha256(G01_RAW), len(G01_RAW))))

    def test_r2_not_bound_va_thieu_crosswalk_payload_van_duong(self):
        res = doc_hoa_don_xml(G01_RAW, ctx_obs("O_G01", expected_raw_ref=None, line_crosswalk=(), profile_payload_sha256=None))
        self.assertIn("RAW_REF_NOT_BOUND", res.candidate_reasons)
        self.assertNotIn("RAW_REF_MISMATCH", {i.code for i in res.issues})
        self.assertNotIn("MEASUREMENT_FACTS_NOT_APPLIED_CONTEXT_CONTRADICTION", res.candidate_reasons)
        self.assertEqual((res.lines[0].normalized_quantity_text, res.lines[0].unit_definition_ref), ("10", "DEMO_EXACT_CAI_V1"))
        self.assertEqual((res.canonical_identity, res.semantic_digest), (IDENTITY["I_G01_A"], CONTENT["C_G01"]["semantic_sha256"]))
        self.assertIsNone(res.lines[0].logical_line_ref)
        z = doc_goi_hoa_don_zip(_raw("inputs/G03-identical-members.zip"), (ctx_obs("O_G03_ZIP_1"),))
        self.assertEqual(z.entries[0].result.lines[0].normalized_quantity_text, "10")  # binding ZIP đúng: dương


class Immutability(unittest.TestCase):
    def test_context_snapshot_sau_va_key_cam(self):
        d = {"source_instance": "DEMO_M2_XML_INSTANCE_A", "source_profile_ref": m.PROFILE_REF, "profile_document_sha256": ORACLE["profile_sha256"],
             "company": {"source_company_key": "DEMO_M2_COMPANY_A", "pn_alias": "PN_DEMO_A", "mapping_ref": "M", "mapping_revision": 1,
                         "scope_ref": "S"},
             "identity_profile_ref": m.IDENTITY_PROFILE_REF, "line_crosswalk": [dict(mapping_ref="CW", revision=1,
                                                                                  invoice_identity_binding=list(IDENTITY["I_G01_A"]),
                                                                                  content_artifact_sha256=sha256(G01_RAW),
                                                                                  source_locator="/HDon/DLHDon/NDHDon/DSHHDVu/HHDVu[1]",
                                                                                  source_ordinal=1, logical_line_ref="L", continuity_ref="C")]}
        ctx = InvoiceReadContext.tu_dict(d)
        d["company"]["pn_alias"] = "PN_SUA"
        d["line_crosswalk"][0]["invoice_identity_binding"][0] = "PN_SUA"
        d["line_crosswalk"].append({})
        self.assertEqual((ctx.company.pn_alias, ctx.line_crosswalk[0].invoice_identity_binding[0], len(ctx.line_crosswalk)), ("PN_DEMO_A", "PN_DEMO_A", 1))
        self.assertIsInstance(ctx.line_crosswalk, tuple)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            ctx.company = None  # type: ignore[misc]
        for cam in ("case_id", "expected_semantic_digest", "canonical_invoice_tuple", "identity_alias", "route", "actor", "observation_ref"):
            with self.subTest(cam=cam):
                with self.assertRaises(DataError) as cm:
                    InvoiceReadContext.tu_dict({cam: "x"})
                self.assertEqual(cm.exception.code, "CONTEXT_FORBIDDEN_FIELD")
        with self.assertRaises(DataError):
            XmlRawRef(sha256(b"x"), 1, m.MEDIA_XML, sha256(b"z"), True, "a.xml")  # bool không phải ordinal
        with self.assertRaises(DataError):
            XmlRawRef(sha256(b"x"), 1, m.MEDIA_XML, sha256(b"z"), 1, None)  # bộ ba ZIP thiếu

    def test_ket_qua_bat_bien_va_json_copy_moi(self):
        res = doc_hoa_don_xml(bytearray(G01_RAW), ctx_obs("O_G01"))
        self.assertIsInstance(res.raw_xml, bytes)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            res.semantic_digest = "x"  # type: ignore[misc]
        self.assertIsInstance(res.lines, tuple)
        self.assertIsInstance(res.lines[0].fields[0].occurrences, tuple)
        j = ra_json(res)
        self.assertEqual(j["lines"][0]["quantity"]["exact_value"], "10")  # Decimal → text exact
        self.assertNotIn("raw_xml", j)
        json.dumps(j, allow_nan=False)

        def khong_float(x):
            if isinstance(x, float):
                self.fail("float trong JSON copy")
            if isinstance(x, dict):
                [khong_float(v) for v in x.values()]
            if isinstance(x, list):
                [khong_float(v) for v in x]
        khong_float(j)
        j["lines"][0]["fields"][0]["occurrences"][0]["lexeme"] = "SUA"
        env = res.semantic_envelope.ra_dict()
        env["header"]["SHDon"]["lexeme"] = "SUA"
        self.assertEqual(res.semantic_envelope.ra_dict(), CONTENT["C_G01"]["envelope"])
        self.assertEqual(res.semantic_digest, CONTENT["C_G01"]["semantic_sha256"])
        a, b = res.lines[0].issues, res.issues
        self.assertEqual((a, b), ((), ()))
        iss = doc_hoa_don_xml(G01_RAW).lines[0].issues[0]
        x, y = iss.as_issue(), iss.as_issue()
        self.assertIsNot(x, y)
        x.code = "SUA"
        self.assertEqual(iss.code, "UNIT_UNPROVEN")

    def test_input_chi_bytes(self):
        for xau in (G01_RAW.decode("utf-8"), str(FIX / "inputs" / "G01-wrapped-positive.xml"), FIX / "inputs" / "G01-wrapped-positive.xml",
                    memoryview(G01_RAW), io.BytesIO(G01_RAW)):
            with self.subTest(kieu=type(xau).__name__):
                with self.assertRaises(DataError) as cm:
                    doc_hoa_don_xml(xau)  # type: ignore[arg-type]
                self.assertEqual(cm.exception.code, "INPUT_NOT_BYTES")
        with self.assertRaises(DataError):
            doc_hoa_don_xml(G01_RAW, {"source_instance": "x"})  # type: ignore[arg-type]
        with self.assertRaises(DataError):
            doc_goi_hoa_don_zip(_raw("inputs/G03-identical-members.zip"), ({},))  # type: ignore[arg-type]
        self.assertEqual(doc_hoa_don_xml(bytearray(G01_RAW)).raw_ref, doc_hoa_don_xml(G01_RAW).raw_ref)


if __name__ == "__main__":
    unittest.main()
