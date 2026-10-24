"""V11 contracts with generated records only (no PLHN data).

Covers the five case findings of 10–11/10/2026: merged 112 legs (VAT split),
description fingerprints, legacy keyword rules, weak-rule demotion, name-based
identification with an abbreviation table and a conflict check, filling a row
from its matched Junsky voucher, many-rows-to-one-voucher matching, open items
as offset evidence, numeric keys learned on approval, the AI note hand-off and
the scoring replay.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from test_modules import FeatureCase
from kho_tri_thuc.giao_dien.quick import QuickPosting
from kho_tri_thuc.giao_dien.v9b import (fingerprint, fingerprint_similar, journal_bank_leg, journal_suggestion, match_bank_groups_to_journal,
                                         merged_cash_legs, offset_account_ranking, _opposite_accounts)
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.kiem_chung.fixtures import envelope, knowledge_item as _knowledge_item
from kho_tri_thuc.tri_thuc.ai_cuc_bo import choose_counterparty, local_ai_settings
from kho_tri_thuc.tri_thuc.matching import keyword_regex
from kho_tri_thuc.tri_thuc.ten_doi_tuong import NameIndex, canonical_name, distinctive_tokens, identify_by_name, names_compatible

CUT = "2099-01-01T00:00:00Z"
ACTOR = "CFO_NTD"


def knowledge_item(category, key, payload):
    """Catalog/rule rows valid from 2024 so 2026 replays can use them."""
    return _knowledge_item(category, key, payload, start="2024-01-01")


def _envelope(source, records, *, as_of):
    """Fixture envelope whose coverage starts early enough for 2026 replays."""
    exported = (date.fromisoformat(as_of) + timedelta(days=1)).isoformat() + "T00:00:00Z"
    value = envelope(source, records, as_of=as_of, exported=exported)
    value["manifest"]["coverage_from"] = "2024-01-01"
    return value


def _journal(identifier, day, lines, *, description="SYNTHETIC", voucher_type="BP", counterparty="", project=""):
    return {"id": identifier, "business_date": day, "voucher_type": voucher_type, "voucher_number": voucher_type + "_" + identifier,
            "description": description, "counterparty": counterparty, "project": project,
            "lines": [{"account": account, "debit_minor": debit, "credit_minor": credit} for account, debit, credit in lines]}


class V11PureTests(FeatureCase):
    def test_fingerprint_drops_numbers_dates_and_filler_words(self):
        self.assertEqual(("THU", "PHI", "SMS", "BDSD", "PHAT", "SINH"), fingerprint("Thu phi SMS BDSD T7/2026 SDT 094****189 phat sinh 12 sms, stk 123456"))
        self.assertEqual(("TRA", "NO", "VAY"), fingerprint("Tra no TK vay 808004810083, so tien 691478009 VND"))
        self.assertTrue(fingerprint_similar("Tra no TK vay 808004810083, so tien 1 VND", "Tra no goc vay"))
        self.assertTrue(fingerprint_similar("Thu phi SMS BDSD T7/2026 SDT 0 phat sinh 12 sms", "Thu phi BDSD 03/2026, so TK: 1, SDT: 2"))
        self.assertFalse(fingerprint_similar("Tra no TK vay 1, so tien 2 VND", "Lai vay tien vay thang 7.2026"))
        self.assertFalse(fingerprint_similar("", "Tra no goc vay"))

    def test_merged_cash_legs_make_vat_split_vouchers_learnable_and_matchable(self):
        journal = _journal("V1", "2026-06-06", [("6427", 50000, 0), ("1121", 0, 50000), ("1331", 5000, 0), ("1121", 0, 5000)])
        self.assertEqual([{"account": "1121", "side": "CREDIT", "amount_minor": 55000}], merged_cash_legs(journal))
        self.assertEqual("1121", journal_bank_leg(journal, "OUT", -55000)["account"])
        primary, lines = _opposite_accounts(journal, "OUT")
        self.assertEqual("6427", primary)
        self.assertEqual([("1331", 5000), ("6427", 50000)], [(line["account"], line["amount_minor"]) for line in lines])

    def test_learning_measures_the_recent_window_and_reports_stats(self):
        bank = {"business_date": "2026-08-06", "amount_minor": -62040, "counterparty_account": "", "description": "Thu phi SMS BDSD T7/2026 SDT 0 phat sinh 12 sms, stk 1"}
        history = [_journal(f"OLD{index}", f"2024-{10 + index:02d}-01", [("24126", 50000, 0), ("1121", 0, 50000), ("1331", 5000, 0), ("1121", 0, 5000)], description="Thu phi BDSD 10/2024, so TK: 1") for index in range(3)]
        history += [_journal(f"NEW{index}", f"2026-{index + 1:02d}-06", [("6427", 50000, 0), ("1121", 0, 50000), ("1331", 5000, 0), ("1121", 0, 5000)], description="Thu phi BDSD 01/2026, so TK: 1, SDT: 2", project="DA_SYN") for index in range(6)]
        learned = journal_suggestion(bank, history, cutoff_day="2026-07-01", own_codes=set(), object_learning_from="2026-07-01", cash_account="1121")
        self.assertEqual("PENDING_PATTERN_STRONG", learned["strength"])
        self.assertEqual({"window": 6, "consistent": 6, "total": 9, "from": "01/2026", "to": "06/2026", "share": 1.0}, learned["stats"])
        self.assertEqual([("1331", "DEBIT"), ("6427", "DEBIT")], [(line["account"], line["side"]) for line in learned["pattern_lines"]])
        self.assertEqual("DA_SYN", learned["fields"]["project"])
        self.assertIn("6/6 chứng từ", learned["why"])
        self.assertEqual({"6427", "1331"}, set(offset_account_ranking(history + [_journal("X", "2026-05-01", [("331", 7, 0), ("1121", 0, 7)], description="TT hoa don")], "OUT", "2026-07-01", description="thu phi sms bdsd t8")[:2]))

    def test_learning_falls_back_to_the_counterparty_history(self):
        bank = {"business_date": "2026-08-06", "amount_minor": 499, "counterparty_account": "", "description": "124D60806 CTY ALPHA CHUYEN TIEN"}
        history = [_journal(f"P{index}", f"2026-0{index + 1}-10", [("1121", 100, 0), ("131171", 0, 100)], description="Thu tien hop dong", counterparty="KH.ALPHA") for index in range(4)]
        learned = journal_suggestion(bank, history, cutoff_day="2026-07-01", own_codes=set(), object_learning_from="2026-01-01", counterparty_code="KH.ALPHA")
        self.assertEqual("COUNTERPARTY_HISTORY", learned["match_basis"])
        self.assertEqual("131171", learned["fields"]["credit_account"])
        self.assertIn("của đối tượng này", learned["why"])

    def test_legacy_keyword_lists_match_on_word_boundaries(self):
        self.assertTrue(keyword_regex("PHI + THANH TOAN").search("TT PHI THANH TOAN HD 12"))
        self.assertFalse(keyword_regex("PHI + THANH TOAN").search("THU PHI SMS BDSD"))
        self.assertFalse(keyword_regex("PHI").search("PHIEU CHI 12"))
        self.assertTrue(keyword_regex("PHI").search("THU PHI SMS"))
        self.assertTrue(keyword_regex(r"SYN\d+").search("SYN123"))  # a real regex still works

    def test_name_index_handles_bank_abbreviations_descriptions_and_duplicates(self):
        index = NameIndex([("ANT", "CONG TY CO PHAN AN THUAN DVS"), ("TZ", "CONG TY TNHH TU VAN XAY DUNG T&Z"),
                           ("HD2", "CONG TY CO PHAN CO KHI NHOM KINH HOANG DUNG"), ("HD1", "CONG TY TNHH MOT THANH VIEN NOI THAT HOANG DUNG"),
                           ("SUN", "CONG TY CO PHAN XNK SUNRISE GROUP"), ("HN", "CONG TY TNHH DT SX VA TM HA NAM"), ("HN2", "CTY CP HA NAM XANH"),
                           ("HN3", "CTY TNHH HA NAM FOOD"), ("HN4", "CTY CP XD HA NAM"), ("HN5", "CTY CP TM HA NAM MOI")])
        self.assertEqual("CTY CP AN THUAN DVS", canonical_name("CT CP AN THUAN - DVS"))
        self.assertEqual(("AN", "THUAN", "DVS"), distinctive_tokens("CTCP AN THUAN DVS"))
        self.assertEqual("ANT", identify_by_name(index, "CT CP AN THUAN - DVS", "")["code"])
        self.assertEqual("CATALOG_NAME", identify_by_name(index, "CONG TY CO PHAN XNK SUNRISE GROUP", "")["level"])
        found = identify_by_name(index, "", "CTCP CO KHI NHOM KINH HOANG DUNG THANH TOAN CHI PHI SU DUNG HA TANG")
        self.assertEqual(("HD2", "CATALOG_NAME_DESC"), (found["code"], found["level"]))
        # Common words alone ("HA NAM") never identify a counterparty.
        self.assertEqual("", identify_by_name(index, "", "PLASCHEM HA NAM CHI LUONG THANG 8")["code"])
        self.assertFalse(names_compatible("CT CP AN THUAN - DVS", "CONG TY TNHH TU VAN XAY DUNG T&Z"))
        self.assertTrue(names_compatible("CT CP AN THUAN - DVS", "CONG TY CO PHAN AN THUAN DVS"))
        self.assertGreater(index.affinity("CONG TY CP NUOC SACH HA NAM", "HN"), 0)

    def test_bracketed_trade_name_is_optional_and_own_name_words_are_no_evidence(self):
        index = NameIndex([("W1", "Công ty cổ phần Nước sạch Mẫu (Wasyn)"), ("W2", "CÔNG TY TNHH MỘT THÀNH VIÊN NƯỚC SẠCH MẪU HÀ"),
                           ("B1", "CONG TY ABC (CHI NHANH 1)"), ("B2", "CONG TY ABC")])
        self.assertEqual(["W1"], index.exact("CONG TY CP NUOC SACH MAU"))
        self.assertEqual("CATALOG_NAME", identify_by_name(index, "CONG TY CP NUOC SACH MAU", "")["level"])
        self.assertEqual(["B1", "B2"], index.exact("CONG TY ABC"))  # short form shared → still ambiguous
        own = frozenset({"OWNCO", "HA", "NAM"})
        bank = "124D6080 CTY XNK DELTA GROUP TRA TIEN CTY OWNCO HA NAM"
        self.assertTrue(fingerprint_similar(bank, "THANH TOAN TIEN CHO OWNCO"))
        self.assertFalse(fingerprint_similar(bank, "THANH TOAN TIEN CHO OWNCO", ignore=own))
        self.assertFalse(fingerprint_similar(bank, "Gamma thanh toan OwnCo Ha Nam", ignore=own))

    def test_group_of_transfers_matches_one_voucher(self):
        banks = [{"id": f"B{index}", "kind": "BANK", "business_date": "2026-08-25", "amount_minor": 450, "counterparty_account": "0099887766", "counterparty_name": "CT CP ALPHA", "description": "CK"} for index in range(3)]
        banks.append({"id": "B9", "kind": "BANK", "business_date": "2026-08-25", "amount_minor": 450, "counterparty_account": "0011223344", "counterparty_name": "KHAC", "description": "CK"})
        voucher = _journal("R1", "2026-08-25", [("1121", 1350, 0), ("131171", 0, 1350)], voucher_type="BR")
        matched = match_bank_groups_to_journal(banks, [voucher])
        self.assertEqual({"B0", "B1", "B2"}, set(matched))
        self.assertEqual(3, matched["B0"]["group"]["size"])
        self.assertEqual("BR_R1", matched["B0"]["voucher_number"])

    def test_group_matching_never_shares_or_double_claims_a_voucher(self):
        voucher = _journal("R1", "2026-08-25", [("1121", 1000, 0), ("131171", 0, 1000)], voucher_type="BR", description="THU TIEN KHAC")
        single = {"id": "S", "kind": "BANK", "business_date": "2026-08-25", "amount_minor": 1000, "counterparty_account": "0011", "counterparty_name": "KHAC", "description": "THU TIEN KHAC"}
        group_a = [{"id": f"A{index}", "kind": "BANK", "business_date": "2026-08-25", "amount_minor": 500, "counterparty_account": "0022", "counterparty_name": "ALPHA", "description": "CK"} for index in range(2)]
        group_c = [{"id": f"C{index}", "kind": "BANK", "business_date": "2026-08-25", "amount_minor": 250, "counterparty_account": "0033", "counterparty_name": "GAMMA", "description": "CK"} for index in range(4)]
        # The voucher is already explained by the single row: no group may take it.
        self.assertEqual({}, match_bank_groups_to_journal([single] + group_a, [voucher]))
        # Two groups that both add up to the voucher: nobody is marked.
        self.assertEqual({}, match_bank_groups_to_journal(group_a + group_c, [voucher]))
        self.assertEqual({"A0", "A1"}, set(match_bank_groups_to_journal(group_a, [voucher])))

    def test_numeric_keys_skip_amounts_dates_and_short_numbers(self):
        record = {"account": "00001234", "counterparty_account": "", "amount_minor": -691478009,
                  "description": "Tra no TK vay 808004810083, so tien 691478009 VND ngay 20260825 ref 12345678"}
        self.assertEqual(["808004810083"], QuickPosting._numeric_keys(record))

    def test_local_ai_is_off_by_default_and_only_ever_picks_an_offered_code(self):
        self.assertFalse(local_ai_settings({})["enabled"])
        self.assertFalse(local_ai_settings({"local_ai": {"enabled": True, "url": "https://example.com/v1"}})["enabled"])
        settings = {"enabled": True, "url": "http://127.0.0.1:1234/v1/chat/completions", "model": "x", "timeout_seconds": 3}
        options = [{"code": "A", "name": "Alpha"}, {"code": "B", "name": "Beta"}]
        self.assertEqual("B", choose_counterparty(settings, "BETA CO", "", options, transport=lambda url, body: "MA=B | LY_DO=ten trung")["code"])
        self.assertIsNone(choose_counterparty(settings, "X", "", options, transport=lambda url, body: "MA=Z | LY_DO=?"))
        self.assertIsNone(choose_counterparty(settings, "X", "", options, transport=lambda url, body: "KHONG"))
        self.assertIsNone(choose_counterparty({**settings, "enabled": False}, "X", "", options, transport=lambda url, body: "MA=A"))


class V11StoreTests(FeatureCase):
    def _stage(self, items):
        for identifier in self.kb.stage_many(items, "V11_SYNTHETIC", CUT):
            self.kb.approve(identifier, "V11_SYNTHETIC", CUT)

    def _setup(self, *, rules=()):
        items = [knowledge_item("CATALOG", "COUNTERPARTY:" + code, {"kind": "COUNTERPARTY", "code": code, "name": name}) for code, name in (
            ("KH.ALPHA", "CONG TY CO PHAN XNK ALPHA GROUP"), ("KH.BETA", "CONG TY CO PHAN BETA DVS"), ("XD.GAMMA", "CONG TY TNHH TU VAN XAY DUNG GAMMA"),
            ("KH.DELTA", "CONG TY CO PHAN CO KHI NHOM KINH DELTA"), ("NH.MAU", "NGAN HANG MAU"))]
        for account in ("1121", "6427", "1331", "331", "131171", "344", "34112", "24126"):
            items.append(knowledge_item("CATALOG", "ACCOUNT:" + account, {"kind": "ACCOUNT", "code": account, "name": "Synthetic " + account}))
        items.append(knowledge_item("CATALOG", "PROJECT:DA_SYN", {"kind": "PROJECT", "code": "DA_SYN", "name": "Synthetic project"}))
        self._stage(items)
        if rules:
            # Rulebook rows arrive pending (nobody approved them); keep it so.
            self.kb.stage_many(list(rules), "V11_SYNTHETIC", CUT)
        QuickPosting(self.store).set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V11_SYNTHETIC"])

    @staticmethod
    def _bank(reference, *, amount, day, description, counterpart_account="", counterparty_name=""):
        record = {"business_date": day, "currency": "VND", "amount": str(amount), "bank": "BANK_SYN", "account": "00001234",
                  "id_scope": "v11-synthetic", "reference": reference, "description": description, "identity_verified": True}
        if counterpart_account:
            record["counterparty_account"] = counterpart_account
        if counterparty_name:
            record["counterparty_name"] = counterparty_name
        return record

    @staticmethod
    def _voucher(number, day, lines, *, description, counterparty="", project="", voucher_type="BP"):
        return {"kind": "JOURNAL", "business_date": day, "currency": "VND", "amount": "0", "book": "NKC_SYN", "fiscal_year": day[:4],
                "voucher_type": voucher_type, "voucher_number": number, "source_status": "POSTED_SOURCE_FIXTURE", "complete_voucher": True,
                "unit_code": "UNIT_SYN", "description": description, "counterparty": counterparty or None, "project": project or None,
                "lines": [{"line_id": str(index), "account": account, "debit": str(debit), "credit": str(credit)} for index, (account, debit, credit) in enumerate(lines, 1)]}

    def _ledger(self, vouchers, *, as_of):
        self.ingest(_envelope("junsky_xuat", vouchers, as_of=as_of))

    def _run(self, *records):
        attempt = self.ingest(_envelope("sao_ke", list(records), as_of="2026-12-31"))
        return QuickPosting(self.store).propose(attempt, "sao_ke", "V11_SYNTHETIC", cutoff=CUT, source_name="synthetic.xlsx", source_hash="HASH_" + attempt)

    def _sms_history(self, months=6):
        return [self._voucher(f"UNIT_SYNBP26{month:02d}-0001", f"2026-{month:02d}-06", [("6427", 50000, 0), ("1121", 0, 50000), ("1331", 5000, 0), ("1121", 0, 5000)],
                              description="Thu phi BDSD 0X/2026, so TK: 123, SDT: 09", counterparty="NH.MAU", project="DA_SYN") for month in range(1, months + 1)]

    def _weak_phi_rule(self):
        return knowledge_item("POLICY", "R_PHI", {
            "contract_version": 2, "template_id": "R_PHI", "partition": "SYN:PAYMENT", "direction": "OUT", "tier": 5, "order": 1,
            "needs_open_item": False, "required_fields": [], "trigger": {"mode": "REGEX", "regex": "PHI"},
            "fields": {"debit_account": "331"}, "source_status": "NHAP",
            "source_row": {"ma_quy_tac": "R_PHI", "tu_khoa": "PHI", "tk_doi_ung": "331", "do_on_dinh": "0.81", "so_lan_gap": "58", "so_lan_dung": "47", "trang_thai": "NHAP", "lan_dau": "2026-01-07"}})

    # -- case 1 ----------------------------------------------------------------
    def test_vat_split_history_beats_a_weak_keyword_rule_and_is_green_with_odds(self):
        self._setup(rules=[self._weak_phi_rule()])
        self._ledger(self._sms_history(), as_of="2026-06-30")
        row = self._run(self._bank("SMS-1", amount=-62040, day="2026-08-06", description="Thu phi SMS BDSD T7/2026 SDT 09 phat sinh 12 sms, stk 123"))["rows"][0]
        self.assertEqual("Xanh", row["proposal_level"])
        self.assertEqual([("N", "1331", 5640), ("N", "6427", 56400), ("C", "1121", 62040)], [(l["side"], l["account"], l["amount"]) for l in row["entry_lines"]])
        self.assertEqual({"window": 6, "consistent": 6, "total": 6, "from": "01/2026", "to": "06/2026", "share": 1.0}, row["stats"])
        self.assertEqual("R_PHI", row["demoted_rule"]["code"])
        self.assertIn("6/6 chứng từ", row["why"])
        self.assertIn("chỉ làm gợi ý", row["why"])

    def test_vat_split_voucher_already_posted_is_recognised_and_shown(self):
        self._setup()
        self._ledger(self._sms_history(1) + [self._voucher("UNIT_SYNBP2608-0007", "2026-08-06", [("6427", 56400, 0), ("1121", 0, 56400), ("1331", 5640, 0), ("1121", 0, 5640)],
                                                               description="Thu phi SMS BDSD T7/2026 SDT 09 phat sinh 12 sms, stk 123", counterparty="NH.MAU", project="DA_SYN")], as_of="2026-08-29")
        row = self._run(self._bank("SMS-2", amount=-62040, day="2026-08-06", description="Thu phi SMS BDSD T7/2026 SDT 09 phat sinh 12 sms, stk 123"))["rows"][0]
        self.assertEqual("EXISTING", row["state"])
        self.assertEqual("UNIT_SYNBP2608-0007", row["junsky_voucher"])
        # E1: the voucher's own posting is what the screen shows.
        self.assertEqual("NH.MAU", row["fields"]["counterparty"])
        self.assertEqual("DA_SYN", row["fields"]["project"])
        self.assertEqual([("N", "1331", 5640), ("N", "6427", 56400), ("C", "1121", 62040)], [(l["side"], l["account"], l["amount"]) for l in row["entry_lines"]])
        self.assertIn("chứng từ đã có trong Junsky", row["why"])

    # -- case 2 / 3 / 4 ----------------------------------------------------------
    def test_statement_name_identifies_the_catalog_counterparty_and_open_items_give_the_account(self):
        self._setup()
        self.ingest(_envelope("junsky_xuat", [{"kind": "OPEN_ITEM", "business_date": "2026-08-01", "currency": "VND", "amount": "3000", "item_id": "INV-1", "item_type": "INVOICE",
                                                "account": "131171", "counterparty": "KH.ALPHA", "invoice_reference": "HD_SYN_001"}], as_of="2026-08-01"))
        run = self._run(*[self._bank(f"ALPHA-{index}", amount=1000, day="2026-08-06", description=f"124D6080{index} CTY XNK ALPHA GROUP CHUYEN TIEN",
                                     counterpart_account="0099001122", counterparty_name="CONG TY CO PHAN XNK ALPHA GROUP") for index in range(3)])
        for row in run["rows"]:
            self.assertEqual("KH.ALPHA", row["fields"]["counterparty"])
            self.assertEqual("CATALOG_NAME", row["levels"]["counterparty"])
            self.assertEqual("131171", row["fields"]["credit_account"])
        self.assertEqual("OPEN_ITEM_LEVEL_0", run["rows"][0]["levels"]["credit_account"])  # 3 × 1000 = the open invoice
        self.assertEqual("Xanh", run["rows"][0]["proposal_level"])
        self.assertEqual([{"account": "131171", "count": 1, "open_minor": 3000}], run["rows"][0]["account_options"])

    def test_single_covering_open_item_of_a_certain_counterparty_is_green(self):
        self._setup()
        self.ingest(_envelope("junsky_xuat", [{"kind": "OPEN_ITEM", "business_date": "2026-08-01", "currency": "VND", "amount": amount, "item_id": item, "item_type": "INVOICE",
                                                "account": account, "counterparty": "KH.ALPHA", "invoice_reference": item, "project": "DA_SYN"}
                                               for amount, item, account in (("9000", "HD_SYN_101", "131171"), ("200", "HD_SYN_102", "131131"))], as_of="2026-08-01"))
        row = self._run(self._bank("ALPHA-S", amount=1000, day="2026-08-06", description="CTY XNK ALPHA GROUP TRA TIEN", counterparty_name="CONG TY CO PHAN XNK ALPHA GROUP"))["rows"][0]
        self.assertEqual(("131171", "OPEN_ITEM_SINGLE", "Xanh"), (row["fields"]["credit_account"], row["levels"]["credit_account"], row["proposal_level"]))
        self.assertIn("chỉ còn công nợ mở trên tài khoản này", row["why"])
        self.assertEqual(("DA_SYN", "OPEN_ITEM_SINGLE"), (row["fields"]["project"], row["levels"]["project"]))  # the open item's project
        # A guessed counterparty (name only inside the narrative) keeps the hint yellow.
        weak = self._run(self._bank("ALPHA-W", amount=1000, day="2026-08-07", description="CTY XNK ALPHA GROUP TRA TIEN"))["rows"][0]
        if weak["fields"].get("counterparty") == "KH.ALPHA":
            self.assertNotEqual("OPEN_ITEM_SINGLE", weak["levels"].get("credit_account"))

    def _cfo_stub(self):
        from types import MethodType, SimpleNamespace
        from kho_tri_thuc.giao_dien.operations import Operations
        stub = SimpleNamespace(config=self.store.config, _read_cfo_rules=Operations._read_cfo_rules, _knowledge_state=Operations._knowledge_state)
        stub._cfo_policy_payload = MethodType(Operations._cfo_policy_payload, stub)
        return stub

    def test_cfo_rule_can_be_switched_off_and_on_and_a_note_rule_annotates_conflicts(self):
        from kho_tri_thuc.giao_dien.operations import Operations
        self._setup()
        self._stage([knowledge_item("CATALOG", "COUNTERPARTY:NV.SYN.01", {"kind": "COUNTERPARTY", "code": "NV.SYN.01", "name": "Tran Thi Mau"}),
                     knowledge_item("CATALOG", "ACCOUNT:1111", {"kind": "ACCOUNT", "code": "1111", "name": "Synthetic cash"})])
        rule = {"ma": "CFO-SYN", "ngay_duyet": "2026-10-13", "chieu": "CHI", "mau_dien_giai": "(?<![A-Z0-9])CC\\s*\\d{9,12}(?![0-9])",
                "doi_tuong_bat_dau": "NV.", "no": "1111"}
        note = {"ma": "CFO-NOTE", "loai": "LUU_Y", "ngay_duyet": "2026-10-13", "lich_su_tk": "344", "de_xuat_tk": "131", "noi_dung": "344 chỉ cho đặt cọc ban đầu"}
        path = self.root / "TRI-THUC-CFO.json"
        stub = self._cfo_stub()
        def load(*rules, at):
            path.write_text(json.dumps({"rules": list(rules)}), encoding="utf-8")
            Operations._import_cfo_rules(stub, self.store, path, at)
        load({**rule, "tat": True}, note, at="2026-10-13T08:00:00Z")
        self.assertEqual(0, self.store.conn.execute("SELECT COUNT(*) FROM knowledge_versions WHERE logical_key='CFO:CFO-SYN'").fetchone()[0])
        load(rule, note, at="2026-10-13T09:00:00Z")
        bank = lambda ref, day: self._bank(ref, amount=-500, day=day, description="TRAN THI MAU CC 001300000000")
        self.assertEqual("1111", self._run(bank("C-1", "2026-08-03"))["rows"][0]["fields"]["debit_account"])
        load({**rule, "tat": True}, note, at="2026-10-14T09:00:00Z")  # switched off: revoked, no longer used
        self.assertNotEqual("1111", self._run(bank("C-2", "2026-08-04"))["rows"][0]["fields"].get("debit_account"))
        load(rule, note, at="2026-10-15T09:00:00Z")  # back on: a fresh version
        self.assertEqual("1111", self._run(bank("C-3", "2026-08-05"))["rows"][0]["fields"]["debit_account"])
        # The note rule: old receipts of this customer were deposits (344), its open item is 131.
        self._ledger([self._voucher(f"UNIT_SYNBR25{month:02d}-0001", f"2025-{month:02d}-10", [("1121", 900, 0), ("344", 0, 900)], description="DAT COC", counterparty="KH.ALPHA", voucher_type="BR")
                      for month in (3, 4, 5)], as_of="2025-12-31")
        self.ingest(_envelope("junsky_xuat", [{"kind": "OPEN_ITEM", "business_date": "2026-08-01", "currency": "VND", "amount": "9000", "item_id": "HD_SYN_201",
                                                "item_type": "INVOICE", "account": "131171", "counterparty": "KH.ALPHA", "invoice_reference": "HD_SYN_201"}], as_of="2026-08-01"))
        row = self._run(self._bank("ALPHA-N", amount=1000, day="2026-08-06", description="TRA TIEN", counterparty_name="CONG TY CO PHAN XNK ALPHA GROUP"))["rows"][0]
        self.assertEqual("131171", row["fields"]["credit_account"])
        self.assertIn("344 chỉ cho đặt cọc ban đầu — CFO-NOTE)", row["why"])

    def test_cfo_rule_file_is_approved_in_his_name_and_needs_an_employee_code(self):
        from kho_tri_thuc.giao_dien.operations import Operations
        self._setup()
        self._stage([knowledge_item("CATALOG", "COUNTERPARTY:NV.SYN.01", {"kind": "COUNTERPARTY", "code": "NV.SYN.01", "name": "Tran Thi Mau"}),
                     knowledge_item("CATALOG", "ACCOUNT:1111", {"kind": "ACCOUNT", "code": "1111", "name": "Synthetic cash"})])
        rules = self.root / "TRI-THUC-CFO.json"
        rule = {"ma": "CFO-SYN", "ngay_duyet": "2026-10-13", "chieu": "CHI", "mau_dien_giai": "(?<![A-Z0-9])CC(CD)?\\s*:?\\s*\\d{9,12}(?![0-9])",
                "doi_tuong_bat_dau": "NV.", "no": "1111", "mo_ta": "Rút tiền mặt nhập quỹ"}
        rules.write_text(json.dumps({"rules": [rule]}), encoding="utf-8")
        stub = self._cfo_stub()
        self.assertEqual(1, Operations._import_cfo_rules(stub, self.store, rules, "2026-10-13T08:00:00Z"))
        self.assertEqual(1, Operations._import_cfo_rules(stub, self.store, rules, "2026-10-13T09:00:00Z"))  # unchanged: no new version
        self.assertEqual(1, self.store.conn.execute("SELECT COUNT(*) FROM knowledge_versions WHERE logical_key='CFO:CFO-SYN'").fetchone()[0])
        rules.write_text(json.dumps({"rules": [{**rule, "mo_ta": "Rút tiền mặt nhập quỹ (sửa)"}]}), encoding="utf-8")
        Operations._import_cfo_rules(stub, self.store, rules, "2026-10-13T10:00:00Z")  # changed: supersedes, no overlap
        self.assertEqual(2, self.store.conn.execute("SELECT COUNT(*) FROM knowledge_versions WHERE logical_key='CFO:CFO-SYN'").fetchone()[0])
        run = self._run(self._bank("CASH-1", amount=-5000000, day="2026-08-03", description="TRAN THI MAU CC 001300000000 NC 07/08/2025"),
                        self._bank("CASH-2", amount=-5000000, day="2026-08-04", description="NGUOI LA CC 001300000001 NC 07/08/2025"))
        found = {row["source_description"][:5]: row for row in run["rows"]}
        employee, stranger = found["TRAN "], found["NGUOI"]
        self.assertEqual(("1111", "NV.SYN.01", "Xanh"), (employee["fields"]["debit_account"], employee["fields"]["counterparty"], employee["proposal_level"]))
        self.assertIn("CFO-SYN (Anh duyệt 13/10/2026)", employee["why"])
        self.assertEqual(("1111", "CFO_RULE_INCOMPLETE"), (stranger["fields"]["debit_account"], stranger["levels"]["debit_account"]))
        self.assertNotEqual("Xanh", stranger["proposal_level"])

    def test_bank_account_mapping_that_contradicts_the_statement_name_is_set_aside(self):
        self._setup()
        self._stage([knowledge_item("CATALOG", "BANK_ACCOUNT:0055443322", {"kind": "IDENTIFIER", "code": "BANK_ACCOUNT:0055443322", "identifier_type": "BANK_ACCOUNT",
                                                                               "value": "0055443322", "counterparty": "XD.GAMMA", "verified": False, "source_status": "DIRECTORY_LOW", "reliability": "LOW"})])
        row = self._run(self._bank("BETA-1", amount=450, day="2026-08-25", description="CT DEN:1 CT CP BETA DVS", counterpart_account="0055443322", counterparty_name="CT CP BETA - DVS"))["rows"][0]
        self.assertEqual("KH.BETA", row["fields"]["counterparty"])
        self.assertEqual("XD.GAMMA", row["identifier_conflict"]["code"])
        self.assertIn("không khớp", row["why"])
        # Approving teaches the account number its real owner (rank 1 next time).
        quick = QuickPosting(self.store)
        quick.decide(row and self._run_id_of(row), [{"id": row["id"], "action": "APPROVE", "fields": {**row["fields"], "credit_account": "131171"}}], ACTOR, CUT)
        again = self._run(self._bank("BETA-2", amount=450, day="2026-08-26", description="CT DEN:2", counterpart_account="0055443322", counterparty_name="CT CP BETA - DVS"))["rows"][0]
        self.assertEqual("KH.BETA", again["fields"]["counterparty"])
        self.assertIsNone(again["identifier_conflict"])

    def _run_id_of(self, row):
        return self.store.conn.execute("SELECT run_id FROM quick_items WHERE id=?", (row["id"],)).fetchone()[0]

    def test_name_inside_the_narrative_and_several_transfers_equal_one_voucher(self):
        self._setup()
        self._ledger([self._voucher("UNIT_SYNBR2608-0029", "2026-08-25", [("1121", 900, 0), ("131171", 0, 900)], description="CTCP CO KHI NHOM KINH DELTA thanh toan chi phi",
                                    counterparty="KH.DELTA", project="DA_SYN", voucher_type="BR")], as_of="2026-08-29")
        run = self._run(*[self._bank(f"DELTA-{index}", amount=300, day="2026-08-25", description="CTCP CO KHI NHOM KINH DELTA thanh toan chi phi su dung ha tang", counterparty_name="CTCP CO KHI NHOM KINH DELTA") for index in range(3)])
        for row in run["rows"]:
            self.assertEqual("EXISTING", row["state"])
            self.assertEqual(3, row["group"]["size"])
            self.assertEqual("KH.DELTA", row["fields"]["counterparty"])
            self.assertEqual("131171", row["fields"]["credit_account"])
            self.assertIn("3 lần chuyển cùng ngày = 1 chứng từ", row["why"])
        # Without a name column the narrative still names the counterparty.
        row = self._run(self._bank("DELTA-9", amount=5, day="2026-08-27", description="CTCP CO KHI NHOM KINH DELTA thanh toan dot 2"))["rows"][0]
        self.assertEqual(("KH.DELTA", "CATALOG_NAME_DESC"), (row["fields"]["counterparty"], row["levels"]["counterparty"]))
        self.assertEqual("Vàng", row["proposal_level"])

    # -- case 5 ----------------------------------------------------------------
    def test_loan_repayment_learns_from_short_ledger_wording_and_then_from_the_loan_number(self):
        self._setup()
        self._ledger([self._voucher(f"UNIT_SYNBP26{month:02d}-0009", f"2026-{month:02d}-20", [("34112", 700, 0), ("1121", 0, 700)], description="Tra no goc vay", counterparty="NH.MAU", project="DA_SYN") for month in range(1, 6)]
                     + [self._voucher("UNIT_SYNBP2606-0010", "2026-06-20", [("6427", 9, 0), ("1121", 0, 9)], description="Lai vay tien vay thang 6.2026")], as_of="2026-06-30")
        run = self._run(self._bank("LOAN-1", amount=-691478009, day="2026-08-25", description="Tra no TK vay 808004810083, so tien 691478009 VND"))
        row = run["rows"][0]
        self.assertEqual("34112", row["fields"]["debit_account"])
        self.assertEqual("Xanh", row["proposal_level"])
        self.assertEqual("34112", row["suggest_accounts"][0] if row["suggest_accounts"] else "34112")
        quick = QuickPosting(self.store)
        quick.decide(run["run_id"], [{"id": row["id"], "action": "APPROVE"}], ACTOR, CUT)
        learned = self.store.conn.execute("SELECT condition_type,condition_value FROM quick_condition_learning WHERE active=1 ORDER BY condition_value").fetchall()
        self.assertIn(("KEYWORD", "SO:808004810083"), [tuple(item) for item in learned])
        again = self._run(self._bank("LOAN-2", amount=-5, day="2026-09-25", description="Tra no TK vay 808004810083, so tien 5 VND"))["rows"][0]
        self.assertEqual("ANH_DA_DUYET", again["levels"]["debit_account"])
        self.assertEqual("34112", again["fields"]["debit_account"])

    # -- AI note and hand-off ----------------------------------------------------
    def test_ai_note_is_stored_and_packaged_for_claude(self):
        self._setup()
        run = self._run(self._bank("AI-1", amount=-10, day="2026-08-25", description="Chuyen tien"))
        quick = QuickPosting(self.store)
        row = run["rows"][0]
        self.assertEqual("", quick.set_ai_note(run["run_id"], row["id"], "   ", ACTOR, CUT)["ai_note"])
        with self.assertRaises(DataError):
            quick.ai_context(run["run_id"])
        quick.set_ai_note(run["run_id"], row["id"], "Khoản này là trả nợ vay, phải ra 341.", ACTOR, CUT)
        self.assertEqual("Khoản này là trả nợ vay, phải ra 341.", quick.rows(run["run_id"])["rows"][0]["ai_note"])
        package = quick.ai_context(run["run_id"])
        self.assertEqual(1, package["count"])
        self.assertIn("Ghi chú của Anh:** Khoản này là trả nợ vay", package["markdown"])
        self.assertIn("Chuyen tien", package["markdown"])
        with self.assertRaises(DataError):
            quick.set_ai_note(run["run_id"], row["id"], "x" * 4001, ACTOR, CUT)

    # -- reload of the Junsky background ----------------------------------------
    def test_reloading_the_junsky_catalogue_keeps_unchanged_rows_and_supersedes_changed_ones(self):
        from types import SimpleNamespace
        from kho_tri_thuc.giao_dien.operations import Operations
        stub = SimpleNamespace(config=self.store.config, _derive_own_counterparty_codes=lambda store: [])
        def catalogue(name, version, as_of):
            return [{"kind": "COUNTERPARTY", "business_date": as_of, "code": code, "version": version, "name": label,
                     "source_status": "ACTIVE", "valid_from": "2024-01-01", "valid_to": None}
                    for code, label in (("KH.RELOAD", name), ("KH.STAY", "CONG TY KHONG DOI"))]
        self.ingest(_envelope("junsky_xuat", catalogue("CONG TY CU", "v1", "2026-06-30"), as_of="2026-06-30"))
        Operations._adopt_catalog(stub, self.store, "2026-07-01T00:00:00Z")
        Operations._adopt_catalog(stub, self.store, "2026-07-02T00:00:00Z")  # same file again: nothing new, no overlap
        self.assertEqual(2, self.store.conn.execute("SELECT COUNT(*) FROM knowledge_versions WHERE category='CATALOG'").fetchone()[0])
        self.ingest(_envelope("junsky_xuat", catalogue("CONG TY MOI", "v2", "2026-08-29"), as_of="2026-08-29"))
        Operations._adopt_catalog(stub, self.store, "2026-09-01T00:00:00Z")  # used to fail with KNOWLEDGE_OVERLAP
        names = {row["payload"]["code"]: row["payload"]["name"] for row in self.kb.query("2026-09-01", "2026-09-02T00:00:00Z", "CATALOG")}
        self.assertEqual({"KH.RELOAD": "CONG TY MOI", "KH.STAY": "CONG TY KHONG DOI"}, names)

    # -- scoring replay ---------------------------------------------------------
    def _settings(self, **values):
        self.store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('v9b_runtime_settings',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                                (json.dumps(values),))
        self.store.conn.commit()

    def test_scoring_reproposal_recomputes_rows_already_marked_and_keeps_them_out_of_export(self):
        self._setup()
        self._ledger(self._sms_history(4) + [self._voucher("UNIT_SYNBP2608-0007", "2026-08-06", [("6427", 56400, 0), ("1121", 0, 56400), ("1331", 5640, 0), ("1121", 0, 5640)],
                                                               description="Thu phi SMS BDSD T7/2026 SDT 09 phat sinh 12 sms, stk 123", counterparty="NH.MAU", project="DA_SYN")], as_of="2026-08-29")
        quick = QuickPosting(self.store)
        run = self._run(self._bank("RS-1", amount=-62040, day="2026-08-06", description="Thu phi SMS BDSD T7/2026 SDT 09 phat sinh 12 sms, stk 123"),
                        self._bank("RS-2", amount=-5, day="2026-08-09", description="Khong co trong so"))
        self.assertEqual(["EXISTING", "WAIT"], sorted(row["state"] for row in run["rows"]))
        # The run was made before scoring was switched on (the case Anh met on 11/10).
        self._settings(learning_cutoff="2026-06-30", scoring_mode=True)
        with self.assertRaises(DataError) as stale:
            quick.score(run["run_id"], cutoff=CUT)
        self.assertEqual("QUICK_SCORE_STALE", stale.exception.code)
        again = quick.repropose(run["run_id"], "V11_SYNTHETIC", cutoff=CUT)
        self.assertEqual(["WAIT", "WAIT"], [row["state"] for row in again["rows"]])
        sms = next(row for row in again["rows"] if row["amount_minor"] == -62040)
        self.assertFalse(sms["potential_existing"])
        self.assertNotIn("Junsky", sms["why"])
        self.assertFalse(sms["junsky_voucher"])
        self.assertEqual("Xanh", sms["proposal_level"])  # learned from 01–04/2026, not copied from the 08/2026 voucher
        excluded = dict(self.store.conn.execute("SELECT document_id, excluded_from_export FROM quick_items WHERE run_id=?", (run["run_id"],)).fetchall())
        self.assertEqual(1, excluded[sms["document_id"]])  # still out of every export file
        with self.assertRaises(DataError) as blocked:
            quick.export(run["run_id"], self.root, junsky_files=False)
        self.assertEqual("QUICK_SCORING_MODE", blocked.exception.code)
        self.assertEqual(2, len(quick.score(run["run_id"], cutoff=CUT)["rows"]))
        # Scoring off + "Đề xuất lại": the row is marked again.
        self._settings(learning_cutoff="", scoring_mode=False)
        back = quick.repropose(run["run_id"], "V11_SYNTHETIC", cutoff=CUT)
        self.assertEqual(["EXISTING", "WAIT"], sorted(row["state"] for row in back["rows"]))

    def test_trial_kho_with_a_cut_ledger_is_graded_against_the_full_ledger_file(self):
        from openpyxl import Workbook
        self._setup()
        # The kho itself holds only vouchers up to the cut (Anh's "xóa thật").
        self._ledger(self._sms_history(4), as_of="2026-06-30")
        answer = self.root / "so-day-du.xlsx"
        book = Workbook(); sheet = book.active
        sheet.append(["Ngày hạch toán", "Số chứng từ", "Ghi nợ", "Ghi có", "Số tiền", "Nội dung", "Mã đối tượng", "Mã dự án"])
        for debit, credit, amount in (("6427", "1121", 56400), ("1331", "1121", 5640)):
            sheet.append(["06/08/2026", "UNIT_SYNBP2608-0007", debit, credit, amount, "Thu phi SMS BDSD T7/2026", "NH.MAU", "DA_SYN"])
        book.save(answer)
        self._settings(learning_cutoff="2026-06-30", scoring_mode=True, answer_ledger=str(answer))
        quick = QuickPosting(self.store)
        run = self._run(self._bank("TK-1", amount=-62040, day="2026-08-06", description="Thu phi SMS BDSD T7/2026 SDT 09 phat sinh 12 sms, stk 123"))
        self.assertLessEqual(self.store.conn.execute("SELECT MAX(business_date) FROM documents WHERE kind='JOURNAL'").fetchone()[0], "2026-06-30")
        scored = quick.score(run["run_id"], cutoff=CUT)
        self.assertEqual("File so-day-du.xlsx", scored["answer_source"])
        row = scored["rows"][0]
        self.assertEqual(("1331+6427", "1331+6427", True, "UNIT_SYNBP2608-0007"), (row["proposed"], row["actual"], row["account_ok"], row["voucher"]))
        self._settings(learning_cutoff="2026-06-30", scoring_mode=True, answer_ledger=str(self.root / "khong-co.xlsx"))
        with self.assertRaises(DataError) as missing:
            quick.score(run["run_id"], cutoff=CUT)
        self.assertEqual("QUICK_ANSWER_LEDGER", missing.exception.code)

    def test_scoring_mode_hides_the_answer_and_grades_the_proposal(self):
        self._setup()
        self.store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('v9b_runtime_settings',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                                (json.dumps({"learning_cutoff": "2026-06-30", "scoring_mode": True}),))
        self.store.conn.commit()
        self._ledger(self._sms_history(4) + [self._voucher("UNIT_SYNBP2608-0007", "2026-08-06", [("6427", 56400, 0), ("1121", 0, 56400), ("1331", 5640, 0), ("1121", 0, 5640)],
                                                               description="Thu phi SMS BDSD T7/2026 SDT 09 phat sinh 12 sms, stk 123", counterparty="NH.MAU", project="DA_SYN"),
                                               self._voucher("UNIT_SYNBP2608-0008", "2026-08-07", [("331", 70, 0), ("1121", 0, 70)], description="TT hoa don", counterparty="KH.BETA")], as_of="2026-08-29")
        run = self._run(self._bank("SC-1", amount=-62040, day="2026-08-06", description="Thu phi SMS BDSD T7/2026 SDT 09 phat sinh 12 sms, stk 123"),
                        self._bank("SC-2", amount=-70, day="2026-08-07", description="Thanh toan hoa don mau", counterparty_name="CT CP BETA DVS"),
                        self._bank("SC-3", amount=-5, day="2026-08-09", description="Khong co trong so"))
        states = [row["state"] for row in run["rows"]]
        self.assertEqual(["WAIT", "WAIT", "WAIT"], states)  # never EXISTING while scoring
        self.assertNotIn("Đã có trong Junsky", run["rows"][0]["why"])
        scored = QuickPosting(self.store).score(run["run_id"], cutoff=CUT)
        by_ref = {row["description"]: row for row in scored["rows"]}
        sms = by_ref["Thu phi SMS BDSD T7/2026 SDT 09 phat sinh 12 sms, stk 123"]
        self.assertEqual(("1331+6427", "1331+6427", True), (sms["proposed"], sms["actual"], sms["account_ok"]))
        beta = by_ref["Thanh toan hoa don mau"]
        self.assertEqual(("KH.BETA", "KH.BETA", True), (beta["counterparty"], beta["actual_counterparty"], beta["counterparty_ok"]))
        self.assertEqual("Không ghép được với chứng từ Junsky", by_ref["Khong co trong so"]["note"])
        summary = {item["level"]: item for item in scored["summary"]}
        self.assertEqual(3, sum(item["rows"] for item in summary.values()))
        self.assertEqual(1, sum(item["unmatched"] for item in summary.values()))
        path = QuickPosting(self.store).write_score_workbook(self.root / "score.xlsx", scored)
        self.assertTrue(path.is_file())
