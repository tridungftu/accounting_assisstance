"""V9b F1--F2 replay for August 2026, with aggregate-only output.

The replay builds two independent local stores underneath ``--output``. The
first gets a Junsky ledger cut at 31 July and is used for proposals; the
second gets the full ledger and is used only as the post-period comparison
and S7 duplicate check. It never writes a supplied workbook/XML and it does
not emit transaction-level values, text, identifiers, or source paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook, load_workbook

from kho_tri_thuc.giao_dien.operations import Operations
from kho_tri_thuc.giao_dien.v9b import journal_bank_leg, match_bank_to_journal
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.primitives import canonical_json, now_utc
from kho_tri_thuc.ha_tang.runtime import document
from kho_tri_thuc.ha_tang.store import Store
from kho_tri_thuc.nguon.that import SourceMetadata, ThatAdapter
from kho_tri_thuc.tri_thuc.human_workbook import HumanKnowledgeWorkbook


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(r"D:\Claude\Phan mem ho tro ke toan\Mang ngan hang")
INVOICE_ROOT = Path(r"D:\Claude\Phan mem download hoa don\Download hoa don\PLHN\2026-08")
CUTOFF = date(2026, 7, 31)
LEVELS = ("Xanh", "Vàng", "Đỏ")
FIELDS = ("debit_account", "credit_account", "counterparty", "project", "expense")


def _date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value[:10]).date()
        except ValueError:
            return None
    return None


def _source_files() -> tuple[Path, ...]:
    return (
        SOURCE_ROOT / "DANH MỤC",
        SOURCE_ROOT / "dgbList.xlsx",
        SOURCE_ROOT / "Ngân Hàng" / "Sổ NKC có đối ưng.xlsx",
        SOURCE_ROOT / "Ngân Hàng" / "Sao kê NH T08.xlsx",
        INVOICE_ROOT,
    )


def _require_sources() -> None:
    missing = [path for path in _source_files() if not path.exists()]
    if missing:
        # Do not print real paths: the report must remain aggregate-only.
        raise RuntimeError(f"Thiếu {len(missing)} nguồn đầu vào cho F.")


def _fingerprint(paths: Iterable[Path]) -> str:
    """Return a private before/after fingerprint without publishing source names."""
    digest = hashlib.sha256()
    for root in paths:
        items = (root,) if root.is_file() else sorted(path for path in root.rglob("*") if path.is_file())
        for item in items:
            digest.update(str(item.relative_to(root.parent)).encode("utf-8", "surrogatepass"))
            digest.update(hashlib.sha256(item.read_bytes()).digest())
    return digest.hexdigest()


def _copy_cut_ledger(source: Path, target: Path) -> None:
    """Copy headers and entries through 31/07 into the isolated replay input."""
    book = load_workbook(source, read_only=True, data_only=True, keep_links=False)
    out = Workbook()
    out.remove(out.active)
    try:
        for sheet in book.worksheets:
            target_sheet = out.create_sheet(sheet.title)
            for row_number, values in enumerate(sheet.iter_rows(values_only=True), 1):
                # Current Junsky readers find headers in the first two rows.
                if row_number <= 2:
                    target_sheet.append(list(values))
                    continue
                row_date = _date(values[3] if len(values) > 3 else None)
                if row_date is not None and row_date <= CUTOFF:
                    target_sheet.append(list(values))
    finally:
        book.close()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        out.save(target)
    finally:
        out.close()


def _prepare_cut_source(output: Path) -> tuple[Path, tuple[Path, Path]]:
    """Make a complete Junsky input whose journals end at the replay cutoff."""
    base = output / "junsky-cut"
    if base.exists():
        shutil.rmtree(base)
    shutil.copytree(SOURCE_ROOT / "DANH MỤC", base / "DANH MỤC")
    cut_dgb = base / "dgbList.xlsx"
    cut_ledger = base / "Sổ NKC có đối ưng.xlsx"
    _copy_cut_ledger(SOURCE_ROOT / "dgbList.xlsx", cut_dgb)
    _copy_cut_ledger(SOURCE_ROOT / "Ngân Hàng" / "Sổ NKC có đối ưng.xlsx", cut_ledger)
    return base / "DANH MỤC", (cut_dgb, cut_ledger)


def _metadata(scope: str) -> SourceMetadata:
    instant = now_utc()
    today = instant[:10]
    return SourceMetadata(
        today,
        instant,
        "V9b F hồi cứu — kho sao chép",
        "1900-01-01",
        (date.fromisoformat(today) + timedelta(days=1)).isoformat(),
        instant,
        "V9B_F_" + scope,
        "PLHN_JUNSKY",
        "V9B_F_" + scope,
        True,
        True,
        "1900-01-01",
    )


def _seed(operations: Operations, catalog: Path, journal_paths: tuple[Path, Path], scope: str) -> dict:
    """Seed source catalogues, journals and pending human knowledge in a copy store."""
    with Store(operations.config) as store:
        report = store.ingest(catalog, ThatAdapter("junsky", catalog, _metadata(scope), journal_paths=journal_paths))
        if report["state"] == "COMMITTED":
            operations._adopt_catalog(store, now_utc())
    workbook_root = SOURCE_ROOT / "bo_quy_tac" / "ket_qua"
    workbooks = [
        workbook_root / name
        for name in ("TU-DIEN-NHOM-NGHIEP-VU.xlsx", "BO-QUY-TAC.xlsx", "HOA-DON-CAY-PHAN-NHANH.xlsx")
    ]
    partner = PROJECT_ROOT / "DANH MUC DOI TAC PLHN - BO SUNG STK VA DICH VU (nhap 24-09-2026).xlsx"
    with Store(operations.config) as store:
        if partner.is_file():
            operations._import_partner_directory(store, partner, now_utc())
        imported = HumanKnowledgeWorkbook(store).import_sources(
            [path for path in workbooks if path.is_file()], "HE_THONG_JUNSKY", now_utc(), "1900-01-01"
        )
    return {
        "state": report.get("state"),
        "input_records": report.get("input_records", 0),
        "inserted_documents": report.get("inserted_documents", 0),
        "knowledge_pending": imported.get("pending", 0),
    }


def _write_invoice_zip(output: Path) -> int:
    """Copy XML input to a local batch archive with non-identifying member names."""
    files = sorted(path for path in INVOICE_ROOT.rglob("*.xml") if path.is_file())
    if not files:
        raise RuntimeError("Nguồn hóa đơn tháng 8 không có XML.")
    archive_path = output / "hoa-don-2026-08.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for index, path in enumerate(files, 1):
            # Names do not carry invoice or counterparty detail. The payload
            # is immediately copied to the isolated Store by quick_upload.
            archive.write(path, arcname=f"invoice-{index:04d}.xml")
    return len(files)


def _load_journals(config: Config) -> tuple[list[dict], dict[str, dict]]:
    with Store(config) as store:
        journals = [
            document(store, row[0], now_utc())
            for row in store.conn.execute("SELECT id FROM documents WHERE kind='JOURNAL'")
        ]
    return journals, {journal["id"]: journal for journal in journals}


def _journal_coverage(config: Config) -> dict:
    """Publish only period coverage/count, never a journal row or identifier."""
    with Store(config) as store:
        row = store.conn.execute(
            "SELECT COUNT(*) AS count,MIN(business_date) AS from_day,MAX(business_date) AS until_day "
            "FROM documents WHERE kind='JOURNAL'"
        ).fetchone()
    return {"count": int(row["count"]), "from_day": row["from_day"], "until_day": row["until_day"]}


def _payloads(config: Config) -> dict[str, dict]:
    with Store(config) as store:
        return {row["id"]: json.loads(row["proposal_json"]) for row in store.conn.execute("SELECT id,proposal_json FROM quick_items")}


def _records(config: Config, rows: Iterable[dict]) -> dict[str, dict]:
    ids = [row["document_id"] for row in rows]
    if not ids:
        return {}
    with Store(config) as store:
        return {identifier: document(store, identifier, now_utc()) for identifier in ids}


def _empty_correctness() -> dict:
    return {level: {field: {"matched": 0, "correct": 0} for field in FIELDS} for level in LEVELS}


def _empty_totals() -> dict:
    return {level: {"count": 0, "amount_minor": 0} for level in LEVELS}


def _rate(correct: int, matched: int) -> float | None:
    return round(100 * correct / matched, 3) if matched else None


def _quality(correctness: dict) -> dict:
    result = {}
    for level, fields in correctness.items():
        account_correct = fields["debit_account"]["correct"] + fields["credit_account"]["correct"]
        account_matched = fields["debit_account"]["matched"] + fields["credit_account"]["matched"]
        party = fields["counterparty"]
        result[level] = {
            "account_correct_percent": _rate(account_correct, account_matched),
            "counterparty_correct_percent": _rate(party["correct"], party["matched"]),
        }
    return result


def _add_correctness(target: dict, level: str, observed: dict, expected: dict[str, set[str]]) -> None:
    for field in FIELDS:
        options = expected.get(field, set())
        if not options:
            continue
        target[level][field]["matched"] += 1
        target[level][field]["correct"] += int(str(observed.get(field) or "") in options)


def _bank_expected(bank: dict, journal: dict) -> dict[str, set[str]]:
    direction = "IN" if int(bank.get("amount_minor", 0) or 0) > 0 else "OUT"
    leg = journal_bank_leg(journal, direction, int(bank.get("amount_minor", 0) or 0))
    if not leg:
        return {}
    expected: dict[str, set[str]] = defaultdict(set)
    if direction == "IN":
        expected["debit_account"].add(str(leg["account"]))
        for line in journal.get("lines", []):
            value = int(line.get("credit_minor", 0) or 0)
            account = str(line.get("account") or "")
            if value and not account.startswith("112"):
                expected["credit_account"].add(account)
    else:
        expected["credit_account"].add(str(leg["account"]))
        for line in journal.get("lines", []):
            value = int(line.get("debit_minor", 0) or 0)
            account = str(line.get("account") or "")
            if value and not account.startswith("112"):
                expected["debit_account"].add(account)
    for field, core_key in (("counterparty", "counterparty"), ("project", "project"), ("expense", "expense")):
        if journal.get(core_key):
            expected[field].add(str(journal[core_key]))
    return dict(expected)


def _invoice_expected(invoice: dict, journal: dict, direction: str) -> dict[str, set[str]]:
    del invoice  # kept explicit so the scorer documents its pairwise contract
    expected: dict[str, set[str]] = defaultdict(set)
    for line in journal.get("lines", []):
        account = str(line.get("account") or "")
        debit, credit = int(line.get("debit_minor", 0) or 0), int(line.get("credit_minor", 0) or 0)
        if direction == "MUA_VAO":
            if debit and not account.startswith("1331"):
                expected["debit_account"].add(account)
            if credit:
                expected["credit_account"].add(account)
        else:
            if debit:
                expected["debit_account"].add(account)
            if credit and not account.startswith("33311"):
                expected["credit_account"].add(account)
    for field, core_key in (("counterparty", "counterparty"), ("project", "project"), ("expense", "expense")):
        if journal.get(core_key):
            expected[field].add(str(journal[core_key]))
    return dict(expected)


def _red_reasons(rows: Iterable[dict], payloads: dict[str, dict]) -> dict:
    reasons: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "amount_minor": 0})
    for row in rows:
        if row["level"] != "Đỏ":
            continue
        payload = payloads[row["id"]]
        causes = payload.get("missing") or payload.get("constraints") or ["THIEU_CAN_CU"]
        for cause in sorted(set(str(item) for item in causes)):
            reasons[cause]["count"] += 1
            reasons[cause]["amount_minor"] += abs(int(row["amount_minor"]))
    return dict(sorted(reasons.items()))


def _score_bank(rows: list[dict], cut_config: Config, full_journals: list[dict], journal_by_id: dict[str, dict]) -> dict:
    totals = _empty_totals()
    directions = {name: _empty_totals() for name in ("THU", "CHI")}
    correctness = _empty_correctness()
    payloads, records = _payloads(cut_config), _records(cut_config, rows)
    matching = Counter()
    for row in rows:
        level, amount = row["level"], abs(int(row["amount_minor"]))
        direction = "THU" if row["amount_minor"] > 0 else "CHI"
        totals[level]["count"] += 1
        totals[level]["amount_minor"] += amount
        directions[direction][level]["count"] += 1
        directions[direction][level]["amount_minor"] += amount
        bank = records[row["document_id"]]
        match = match_bank_to_journal(bank, full_journals)
        matching[match["status"]] += 1
        if match["status"] == "UNIQUE":
            _add_correctness(correctness, level, row["fields"], _bank_expected(bank, journal_by_id[match["journal_id"]]))
    return {
        "by_level": totals,
        "by_direction_level": directions,
        "correctness": correctness,
        "quality_by_level": _quality(correctness),
        "ledger_match": {"unique": matching["UNIQUE"], "ambiguous": matching["AMBIGUOUS"], "unmatched": matching["UNMATCHED"]},
        "red_reasons": _red_reasons(rows, payloads),
    }


def _invoice_index(journals: Iterable[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = defaultdict(list)
    for journal in journals:
        number = str(journal.get("invoice_reference") or "")
        if number:
            result[number].append(journal)
    return result


def _score_invoices(rows: list[dict], cut_config: Config, full_journals: list[dict]) -> dict:
    """Score purchase/sales proposals against a unique full-ledger invoice reference."""
    payloads = _payloads(cut_config)
    records = _records(cut_config, rows)
    journal_index = _invoice_index(full_journals)
    report = {}
    for direction in ("MUA_VAO", "BAN_RA"):
        selected = [row for row in rows if payloads[row["id"]].get("direction") == direction]
        totals, correctness, matched = _empty_totals(), _empty_correctness(), Counter()
        balanced = {"count": 0, "balanced": 0}
        for row in selected:
            level, amount = row["level"], abs(int(row["amount_minor"]))
            totals[level]["count"] += 1
            totals[level]["amount_minor"] += amount
            payload = payloads[row["id"]]
            lines = payload.get("lines", [])
            if lines:
                balanced["count"] += 1
                balanced["balanced"] += int(sum(int(line.get("debit_minor", 0) or 0) for line in lines) == sum(int(line.get("credit_minor", 0) or 0) for line in lines))
            invoice = records[row["document_id"]]
            candidates = journal_index.get(str(invoice.get("number") or ""), [])
            status = "UNIQUE" if len(candidates) == 1 else "AMBIGUOUS" if candidates else "UNMATCHED"
            matched[status] += 1
            if status == "UNIQUE":
                _add_correctness(correctness, level, row["fields"], _invoice_expected(invoice, candidates[0], direction))
        report["purchase" if direction == "MUA_VAO" else "sales"] = {
            "by_level": totals,
            "correctness": correctness,
            "quality_by_level": _quality(correctness),
            "ledger_match": {"unique": matched["UNIQUE"], "ambiguous": matched["AMBIGUOUS"], "unmatched": matched["UNMATCHED"]},
            "multiline_balance": balanced,
            "red_reasons": _red_reasons(selected, payloads),
        }
    return report


def _score_config(config_text: str, entity_id: str, data_dir: str) -> str:
    def replace(name: str, value: str, text: str) -> str:
        changed, count = re.subn(rf'(?m)^{name}\s*=\s*"[^"]*"\s*$', f'{name} = "{value}"', text, count=1)
        if count != 1:
            raise RuntimeError(f"Không tạo được cấu hình F cho {name}.")
        return changed
    return replace("data_dir", data_dir, replace("entity_id", entity_id, config_text))


def _clean_output(output: Path) -> None:
    allowed = (PROJECT_ROOT / "var" / "vong-2" / "V9-giao-viec").resolve()
    if not output.is_relative_to(allowed):
        raise RuntimeError("Thư mục F phải nằm dưới var/vong-2/V9-giao-viec.")
    for name in ("cut-store", "full-store", "cut-web", "full-web", "junsky-cut", "hoa-don-2026-08.zip"):
        target = output / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def _aggregate_result(result: dict) -> dict:
    """Keep stdout useful but bounded to public aggregate figures only."""
    bank = result["bank"]
    invoice = result["invoice"]
    return {
        "status": "OK",
        "bank_proposed": result["bank_proposed_count"],
        "bank_by_level": {level: bank["by_level"][level]["count"] for level in LEVELS},
        "bank_ledger_match": bank["ledger_match"],
        "bank_full_duplicate": result["bank_full_ledger_duplicate_count"],
        "full_ledger_until": result["journal_coverage"]["full"]["until_day"],
        "bank_non_red_percent": result["acceptance"]["bank_non_red_percent"],
        "green_quality_status": result["acceptance"]["green_quality_status"],
        "invoice_xml_input": result["invoice_xml_input"],
        "invoice_purchase_by_level": {level: invoice["purchase"]["by_level"][level]["count"] for level in LEVELS},
        "invoice_sales_by_level": {level: invoice["sales"]["by_level"][level]["count"] for level in LEVELS},
        "source_files_unchanged": result["source_files_unchanged"],
        "elapsed_seconds": result["elapsed_seconds"],
    }


def _acceptance(bank: dict, proposed_count: int) -> dict:
    """State the F targets without turning an absent Green sample into 100%."""
    non_red = bank["by_level"]["Xanh"]["count"] + bank["by_level"]["Vàng"]["count"]
    non_red_percent = _rate(non_red, proposed_count) or 0.0
    green = bank["quality_by_level"]["Xanh"]
    account, party = green["account_correct_percent"], green["counterparty_correct_percent"]
    if account is None or party is None:
        quality_status = "NOT_EVALUABLE_NO_GREEN_MATCHED_SAMPLE"
        quality_target_met = False
    else:
        quality_target_met = account >= 98 and party >= 98
        quality_status = "MET" if quality_target_met else "NOT_MET"
    return {
        "bank_non_red_percent": non_red_percent,
        "bank_non_red_target_percent": 23,
        "bank_non_red_target_met": non_red_percent >= 23,
        "green_account_correct_percent": account,
        "green_counterparty_correct_percent": party,
        "green_quality_target_percent": 98,
        "green_quality_status": quality_status,
        "green_quality_target_met": quality_target_met,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    _require_sources()
    fingerprint_before = _fingerprint(_source_files())
    _clean_output(output)

    cut_catalog, cut_journals = _prepare_cut_source(output)
    config_text = args.config.read_text(encoding="utf-8")
    cut_config_path, full_config_path = output / "score-cut.toml", output / "score-full.toml"
    cut_config_path.write_text(_score_config(config_text, "PLHN_SCORE_CUT", "cut-store"), encoding="utf-8")
    full_config_path.write_text(_score_config(config_text, "PLHN_SCORE_FULL", "full-store"), encoding="utf-8")
    cut_config, full_config = Config.load(cut_config_path), Config.load(full_config_path)
    cut_ops, full_ops = Operations(cut_config_path, output / "cut-web"), Operations(full_config_path, output / "full-web")

    seed_cut = _seed(cut_ops, cut_catalog, cut_journals, "CUT")
    full_journal_paths = (SOURCE_ROOT / "dgbList.xlsx", SOURCE_ROOT / "Ngân Hàng" / "Sổ NKC có đối ưng.xlsx")
    seed_full = _seed(full_ops, SOURCE_ROOT / "DANH MỤC", full_journal_paths, "FULL")

    bank_path = SOURCE_ROOT / "Ngân Hàng" / "Sao kê NH T08.xlsx"
    cut_bank = cut_ops.quick_upload(bank_path.read_bytes(), bank_path.name)
    full_bank = full_ops.quick_upload(bank_path.read_bytes(), bank_path.name)
    if cut_bank.get("state") != "READY" or full_bank.get("state") != "READY":
        raise RuntimeError("Không nạp được sao kê vào kho chấm F.")

    invoice_xml_input = _write_invoice_zip(output)
    invoice_archive = output / "hoa-don-2026-08.zip"
    invoices = cut_ops.quick_upload(invoice_archive.read_bytes(), invoice_archive.name)
    if invoices.get("state") != "READY":
        raise RuntimeError("Không nạp được hóa đơn tháng 8 vào kho chấm F.")

    cut_rows = list(cut_bank.get("rows", []))
    full_rows = list(full_bank.get("rows", []))
    invoice_rows = list(invoices.get("rows", []))
    full_journals, journal_by_id = _load_journals(full_config)
    bank_score = _score_bank(cut_rows, cut_config, full_journals, journal_by_id)
    result = {
        "period": "2026-08",
        "mode": "offline-copy-only",
        "bank": bank_score,
        "bank_proposed_count": len(cut_rows),
        "bank_full_ledger_duplicate_count": sum(bool(row.get("potential_existing")) for row in full_rows),
        "invoice_xml_input": invoice_xml_input,
        "invoice_proposed_count": len(invoice_rows),
        "invoice": _score_invoices(invoice_rows, cut_config, full_journals),
        "cut_seed": seed_cut,
        "full_seed": seed_full,
        "journal_coverage": {"cut": _journal_coverage(cut_config), "full": _journal_coverage(full_config)},
        "replay_cutoff": CUTOFF.isoformat(),
        "matching_rule": "S7: ngày + số tiền TK 112 + độ giống diễn giải; chỉ nhận khớp duy nhất.",
        "green_target": {
            "account_and_counterparty_correct_percent": 98,
            "bank_non_red_minimum_percent": 23,
            "threshold_used": 0.8,
        },
        "acceptance": _acceptance(bank_score, len(cut_rows)),
        "source_files_unchanged": fingerprint_before == _fingerprint(_source_files()),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    (output / "KET-QUA-F2.json").write_text(canonical_json(result), encoding="utf-8")
    print(canonical_json(_aggregate_result(result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
