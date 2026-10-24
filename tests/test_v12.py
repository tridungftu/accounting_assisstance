"""V12 contracts with generated records only (no PLHN data).

Invoice proposals measured from earlier invoices: an invoice of the learning
months (up to the cut) is linked to the Junsky voucher that posted it by its
amounts; a new invoice is booked like the earlier invoices of the same party
with similar items, else like similar items of other parties, else like the
party's other invoices.  The project is the one the party's own vouchers
always carry.  Purchases that Junsky books against the employee who paid are
flagged.  Invoice runs are graded per direction.
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import load_workbook

from test_modules import FeatureCase
from test_v11 import ACTOR, CUT, _envelope, knowledge_item
from kho_tri_thuc.giao_dien.quick import QuickPosting
from kho_tri_thuc.nguon.that import invoice_month_files, invoice_months, parse_invoice_xml
from kho_tri_thuc.tri_thuc import lich_su_hoa_don as history
from kho_tri_thuc.tri_thuc.lich_su_hoa_don import JournalIndex, build_history, item_core, month_bounds, suggest


def _link(day, tax, account, partner, *, direction="MUA_VAO", core="XANG RON95", project="", party="", journal_party=""):
    return {"journal_id": "J" + day + account, "voucher": "V" + day, "voucher_type": "GJ", "journal_date": day, "journal_party": journal_party or party,
            "account": account, "partner_account": partner, "project": project, "expense": "", "cost_center": "", "description": "",
            "direction": direction, "tax_id": tax, "party_code": party, "date": day, "text": core, "core": core}


def _xml(*, seller, seller_name, buyer, buyer_name, day, number, item, net, tax):
    return (f"<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26TSY</KHHDon><SHDon>{number}</SHDon><NLap>{day}</NLap><DVTTe>VND</DVTTe></TTChung>"
            f"<NDHDon><NBan><Ten>{seller_name}</Ten><MST>{seller}</MST></NBan><NMua><Ten>{buyer_name}</Ten><MST>{buyer}</MST></NMua>"
            f"<DSHHDVu><HHDVu><STT>1</STT><THHDVu>{item}</THHDVu><ThTien>{net}</ThTien><TSuat>8%</TSuat><TThue>{tax}</TThue></HHDVu></DSHHDVu>"
            f"<TToan><TgTCThue>{net}</TgTCThue><TgTThue>{tax}</TgTThue><TgTTTBSo>{net + tax}</TgTTTBSo></TToan></NDHDon></DLHDon></HDon>")


class V12PureTests(FeatureCase):
    def test_item_core_drops_contract_references(self):
        self.assertEqual("PHI XU LY NUOC THAI THANG 7/2026", item_core("Phí xử lý nước thải tháng 7/2026 theo hợp đồng 01/HĐ-XLNT ký ngày 01/01/2026").strip())
        self.assertNotEqual(item_core("Phí quản lý năm 2026 theo hợp đồng số 1/KCN"), item_core("Phí sử dụng hạ tầng theo hợp đồng số 1/KCN"))
        self.assertEqual("2026-05-01", month_bounds("2026-06-30", 1))
        self.assertEqual("2025-07-01", month_bounds("2026-06-30", 11))

    def test_link_needs_net_and_tax_and_skips_collections(self):
        journals = [
            {"id": "SALE", "business_date": "2026-05-03", "voucher_number": "GJ1", "counterparty": "KH.SYN", "project": "DA_SYN",
             "lines": [{"account": "131171", "debit": 1080, "credit": 0}, {"account": "51132", "debit": 0, "credit": 1000}, {"account": "33311", "debit": 0, "credit": 80}]},
            {"id": "CASH", "business_date": "2026-05-02", "voucher_number": "BC1", "counterparty": "KH.SYN",
             "lines": [{"account": "1121", "debit": 1080, "credit": 0}, {"account": "711", "debit": 0, "credit": 1000}, {"account": "33311", "debit": 0, "credit": 80}]},
            {"id": "BUY", "business_date": "2026-05-20", "voucher_number": "GJ2", "counterparty": "NV.SYN",
             "lines": [{"account": "6427", "debit": 500, "credit": 0}, {"account": "1331", "debit": 40, "credit": 0}, {"account": "33111", "debit": 0, "credit": 540}]},
        ]
        index = JournalIndex(journals)
        sale = {"direction": "BAN_RA", "business_date": "2026-05-01", "net_minor": 1000, "tax_minor": 80, "total_minor": 1080}
        self.assertEqual(("SALE", "51132", "131171", "DA_SYN"), (lambda link: (link["journal_id"], link["account"], link["partner_account"], link["project"]))(index.link(sale)))
        purchase = {"direction": "MUA_VAO", "business_date": "2026-05-15", "net_minor": 500, "tax_minor": 40, "total_minor": 540}
        self.assertEqual(("BUY", "6427", "33111", "NV.SYN"), (lambda link: (link["journal_id"], link["account"], link["partner_account"], link["journal_party"]))(index.link(purchase)))
        self.assertIsNone(index.link({**purchase, "tax_minor": 45, "total_minor": 545}))  # tax differs by more than 2 VND
        self.assertIsNone(index.link({**purchase, "business_date": "2026-01-01"}))  # 75-day window

    def test_suggest_tries_party_items_then_similar_items_then_the_party(self):
        invoice = {"direction": "MUA_VAO", "business_date": "2026-08-05", "seller_tax_id": "TAX_SYN", "lines": [{"description": "Xăng RON95"}]}
        party = [_link("2026-01-0%d" % day, "TAX_SYN", "6427", "33111", core="DAU NHON 4L") for day in range(1, 10)]
        party += [_link("2026-02-01", "TAX_SYN", "6427", "33111"), _link("2026-02-02", "TAX_SYN", "24126", "33111"), _link("2026-02-03", "TAX_SYN", "6427", "33111", core="DAU NHON 4L")]
        found = suggest(invoice, party)
        # Same seller, similar item: 1/2 each way — not conclusive; the
        # seller's whole history (11/12) is.
        self.assertEqual(("6427", "WEAK", "PARTY_OTHER_ITEMS"), (found["account"], found["strength"], found["basis"]))
        self.assertEqual({"window": 12, "consistent": 11, "total": 12, "from": "01/2026", "to": "02/2026", "share": 0.917}, found["stats"])
        three = [_link("2026-0%d-01" % month, "TAX_SYN", "6427", "33111", project="DA_SYN") for month in range(1, 4)]
        strong = suggest(invoice, three)
        self.assertEqual(("STRONG", "PARTY_ITEM"), (strong["strength"], strong["basis"]))
        self.assertEqual({"value": "DA_SYN", "count": 3, "total": 3, "unanimous": True}, strong["dimensions"]["project"])
        others = [_link("2026-0%d-01" % month, "TAX_OTHER", "1547", "33111") for month in range(1, 5)]
        self.assertEqual(("1547", "STRONG", "ITEM"), (lambda s: (s["account"], s["strength"], s["basis"]))(suggest(invoice, others)))

    def test_majority_threshold_and_employee_payers(self):
        invoice = {"direction": "MUA_VAO", "business_date": "2026-08-05", "seller_tax_id": "TAX_SYN", "lines": [{"description": "Xăng RON95"}]}
        self.assertEqual(0.75, history.MAJORITY)
        three_of_four = [_link("2026-01-0%d" % day, "TAX_SYN", "6427", "33111", journal_party="NV.A") for day in range(1, 4)] + [_link("2026-01-05", "TAX_SYN", "1547", "33111", journal_party="331.SYN")]
        found = suggest(invoice, three_of_four)
        self.assertEqual(("6427", "WEAK"), (found["account"], found["strength"]))
        self.assertEqual({"count": 3, "total": 4, "codes": ["NV.A"]}, found["employee_payer"])
        two_of_three = three_of_four[1:]
        self.assertIsNone(suggest(invoice, two_of_three)["strength"])

    def test_invoice_xml_names_and_month_folders(self):
        own = self.store.config.entity_tax_id
        row, issues = parse_invoice_xml(_xml(seller="TAX_SYN", seller_name="CONG TY XANG SYN", buyer=own, buyer_name="DON VI SYN", day="2026-05-02",
                                             number="12", item="Xăng RON95", net=500, tax=40).encode(), own)
        self.assertEqual([], [issue.code for issue in issues])
        self.assertEqual(("MUA_VAO", "CONG TY XANG SYN", "500", "40"), (row["direction"], row["seller_name"], row["net_amount"], row["tax_amount"]))
        root = self.root / "hoa-don"
        for month, side in (("2026-05", "mua_vao"), ("2026-08", "ban_ra"), ("2026-08", "mua_vao")):
            folder = root / month / side; folder.mkdir(parents=True)
            (folder / "a.xml").write_text("<HDon/>", encoding="utf-8")
        (root / "khac").mkdir()
        self.assertEqual([{"month": "2026-08", "mua_vao": 1, "ban_ra": 1}, {"month": "2026-05", "mua_vao": 1, "ban_ra": 0}], invoice_months(root))
        self.assertEqual(["ban_ra", "mua_vao"], sorted(path.parent.name for path in invoice_month_files(root, "2026-08")))


class V12StoreTests(FeatureCase):
    OWN = None

    def _setup(self):
        self.OWN = self.store.config.entity_tax_id
        items = []
        for code, name in (("KH.ALPHA", "CONG TY ALPHA SYN"), ("NB.XANG", "CONG TY XANG SYN"), ("NV.LXE", "NHAN VIEN LAI XE SYN")):
            items.append(knowledge_item("CATALOG", "COUNTERPARTY:" + code, {"kind": "COUNTERPARTY", "code": code, "name": name}))
        for code, tax in (("KH.ALPHA", "TAX_ALPHA"), ("NB.XANG", "TAX_XANG")):
            items.append(knowledge_item("CATALOG", "ID:" + tax, {"kind": "IDENTIFIER", "code": "TAX_ID:" + tax, "identifier_type": "TAX_ID", "value": tax, "counterparty": code, "verified": True}))
        for account in ("131171", "51132", "33311", "6427", "1331", "33111", "1121"):
            items.append(knowledge_item("CATALOG", "ACCOUNT:" + account, {"kind": "ACCOUNT", "code": account, "name": "Synthetic " + account}))
        items.append(knowledge_item("CATALOG", "PROJECT:DA_SYN", {"kind": "PROJECT", "code": "DA_SYN", "name": "Synthetic project"}))
        for identifier in self.kb.stage_many(items, "V12_SYNTHETIC", CUT):
            self.kb.approve(identifier, "V12_SYNTHETIC", CUT)
        # Learning months: invoices (XML in the download folder) and the
        # vouchers that posted them, all before the 30/06 cut.
        root = self.root / "hoa-don"
        vouchers = []
        for month in (4, 5, 6):
            day = f"2026-{month:02d}-05"
            net, tax = 1000 + month, 80 + month
            folder = root / f"2026-{month:02d}" / "ban_ra"; folder.mkdir(parents=True)
            (folder / f"b{month}.xml").write_text(_xml(seller=self.OWN, seller_name="DON VI SYN", buyer="TAX_ALPHA", buyer_name="CONG TY ALPHA SYN", day=day, number=f"10{month}",
                                                       item=f"Phí xử lý nước thải tháng {month}/2026 theo hợp đồng 01/HĐ", net=net, tax=tax), encoding="utf-8")
            vouchers.append(self._voucher(f"GJ-B{month}", day, [("131171", net + tax, 0), ("51132", 0, net), ("33311", 0, tax)], counterparty="KH.ALPHA", project="DA_SYN"))
            net, tax = 500 + month, 40 + month
            folder = root / f"2026-{month:02d}" / "mua_vao"; folder.mkdir(parents=True)
            (folder / f"m{month}.xml").write_text(_xml(seller="TAX_XANG", seller_name="CONG TY XANG SYN", buyer=self.OWN, buyer_name="DON VI SYN", day=day, number=f"20{month}",
                                                       item="Xăng RON95", net=net, tax=tax), encoding="utf-8")
            vouchers.append(self._voucher(f"GJ-M{month}", day, [("6427", net, 0), ("1331", tax, 0), ("33111", 0, net + tax)], counterparty="NV.LXE", project="DA_SYN"))
        self.ingest(_envelope("junsky_xuat", vouchers, as_of="2026-06-30"))
        self._settings(learning_cutoff="2026-06-30", invoice_root=str(root))
        return root

    def _settings(self, **values):
        self.store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('v9b_runtime_settings',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(values),))
        self.store.conn.commit()

    @staticmethod
    def _voucher(number, day, lines, *, counterparty="", project="", voucher_type="GJ"):
        return {"kind": "JOURNAL", "business_date": day, "currency": "VND", "amount": "0", "book": "NKC_SYN", "fiscal_year": day[:4],
                "voucher_type": voucher_type, "voucher_number": number, "source_status": "POSTED_SOURCE_FIXTURE", "complete_voucher": True,
                "unit_code": "UNIT_SYN", "description": "SYNTHETIC", "counterparty": counterparty or None, "project": project or None,
                "lines": [{"line_id": str(index), "account": account, "debit": str(debit), "credit": str(credit)} for index, (account, debit, credit) in enumerate(lines, 1)]}

    def _invoice(self, number, *, direction, item, net, tax, party_tax, party_name, day="2026-08-05"):
        purchase = direction == "MUA_VAO"
        row = {"kind": "INVOICE", "business_date": day, "currency": "VND", "amount": str(net + tax), "net_amount": str(net), "tax_amount": str(tax), "total_amount": str(net + tax),
               "seller_tax_id": party_tax if purchase else self.OWN, "buyer_tax_id": self.OWN if purchase else party_tax, "direction": direction,
               "series": "C26TSY", "number": number, "invoice_type": "GTGT", "source_status": "ACTIVE",
               "lines": [{"line_id": "1", "description": item, "net_amount": str(net), "tax_amount": str(tax), "total_amount": str(net + tax), "tax_rate": "8", "line_nature": "GOODS"}]}
        row["seller_name" if purchase else "buyer_name"] = party_name
        return row

    def _run(self, *records):
        attempt = self.ingest(_envelope("hoa_don_xml", list(records), as_of="2026-12-31"))
        return QuickPosting(self.store).propose(attempt, "hoa_don", "V12_SYNTHETIC", cutoff=CUT, source_name="Hoa don 2026-08.zip", source_hash="HASH_" + attempt)

    def _rows(self, run):
        return {row["invoice_direction"]: row for row in run["rows"]}

    def test_invoice_month_is_booked_like_the_learning_months(self):
        self._setup()
        run = self._run(self._invoice("301", direction="BAN_RA", item="Phí xử lý nước thải tháng 8/2026 theo hợp đồng 01/HĐ", net=2000, tax=160, party_tax="TAX_ALPHA", party_name="CONG TY ALPHA SYN"),
                        self._invoice("401", direction="MUA_VAO", item="Xăng RON95", net=600, tax=48, party_tax="TAX_XANG", party_name="CONG TY XANG SYN"))
        rows = self._rows(run)
        sale, purchase = rows["BAN_RA"], rows["MUA_VAO"]
        self.assertEqual("Xanh", sale["proposal_level"])
        self.assertEqual([("N", "131171", 2160, ""), ("C", "51132", 2000, "DA_SYN"), ("C", "33311", 160, "")],
                         [(line["side"], line["account"], line["amount"], line["project"]) for line in sale["entry_lines"]])
        self.assertEqual({"KH.ALPHA"}, {line["counterparty"] for line in sale["entry_lines"]})
        self.assertIn("3/3 hóa đơn trước của người mua này có tên hàng tương tự (04/2026–06/2026)", sale["why"])
        self.assertIn("chứng từ của đối tác này luôn ghi dự án này", sale["why"])
        # Junsky booked this seller against the employee who paid: never green.
        self.assertEqual("Vàng", purchase["proposal_level"])
        self.assertEqual([("N", "6427", 600, "DA_SYN"), ("N", "1331", 48, ""), ("C", "33111", 648, "")],
                         [(line["side"], line["account"], line["amount"], line["project"]) for line in purchase["entry_lines"]])
        self.assertIn("nhân viên mua hộ: 3/3 hóa đơn trước", purchase["why"])
        self.assertIn("NV.LXE", purchase["why"])
        self.assertEqual("PENDING_PATTERN_WEAK", json.loads(self.store.conn.execute("SELECT proposal_json FROM quick_items WHERE id=?", (purchase["id"],)).fetchone()[0])["confidence"]["counterparty"]["level"])

    def test_learning_months_stop_at_the_cut(self):
        root = self._setup()
        # An invoice after the cut, with its voucher, must not teach anything.
        folder = root / "2026-07" / "ban_ra"; folder.mkdir(parents=True)
        (folder / "b7.xml").write_text(_xml(seller=self.OWN, seller_name="DON VI SYN", buyer="TAX_ALPHA", buyer_name="CONG TY ALPHA SYN", day="2026-07-05", number="107",
                                            item="Phí xử lý nước thải tháng 7/2026", net=1007, tax=87), encoding="utf-8")
        self.ingest(_envelope("junsky_xuat", [self._voucher("GJ-B7", "2026-07-05", [("131171", 1094, 0), ("51132", 0, 1007), ("33311", 0, 87)], counterparty="KH.ALPHA", project="DA_SYN")], as_of="2026-07-31"))
        sale = self._rows(self._run(self._invoice("302", direction="BAN_RA", item="Phí xử lý nước thải tháng 8/2026", net=2000, tax=160, party_tax="TAX_ALPHA", party_name="CONG TY ALPHA SYN")))["BAN_RA"]
        self.assertEqual({"window": 3, "consistent": 3, "total": 3, "from": "04/2026", "to": "06/2026", "share": 1.0}, sale["stats"])

    def test_invoice_approval_review_file_and_grading(self):
        self._setup()
        run = self._run(self._invoice("303", direction="BAN_RA", item="Phí xử lý nước thải tháng 8/2026 theo hợp đồng 01/HĐ", net=2000, tax=160, party_tax="TAX_ALPHA", party_name="CONG TY ALPHA SYN"),
                        self._invoice("403", direction="MUA_VAO", item="Xăng RON95", net=600, tax=48, party_tax="TAX_XANG", party_name="CONG TY XANG SYN"))
        quick = QuickPosting(self.store)
        sale = self._rows(run)["BAN_RA"]
        result = quick.decide(run["run_id"], [{"id": sale["id"], "action": "APPROVE", "remember": True, "lines": sale["entry_lines"]}], ACTOR, CUT)
        approved = {row["id"]: row for row in result["rows"]}[sale["id"]]
        self.assertEqual("APPROVE", approved["state"])
        self.assertEqual(("131171", "51132", "KH.ALPHA", "DA_SYN"), tuple(approved["fields"][name] for name in ("debit_account", "credit_account", "counterparty", "project")))
        # Invoices learn from Junsky once posted, not from this approval.
        self.assertEqual(0, self.store.conn.execute("SELECT COUNT(*) FROM quick_condition_learning").fetchone()[0])
        exported = quick.export(run["run_id"], self.root / "out", junsky_files=False, actor=ACTOR)
        sheet = load_workbook(exported["review"])["BUT TOAN"]
        self.assertEqual("Bán ra", sheet["C2"].value)
        self.assertEqual("Thu/Chi · Mua/Bán", sheet["C1"].value)
        # Junsky posts August later: the run is graded per direction.
        self.ingest(_envelope("junsky_xuat", [self._voucher("GJ-B8", "2026-08-06", [("131171", 2160, 0), ("51132", 0, 2000), ("33311", 0, 160)], counterparty="KH.ALPHA", project="DA_SYN"),
                                              self._voucher("GJ-M8", "2026-08-07", [("6427", 600, 0), ("1331", 48, 0), ("33111", 0, 648)], counterparty="NV.LXE", project="DA_SYN")], as_of="2026-08-31"))
        scored = quick.score(run["run_id"], cutoff=CUT)
        summary = {item["level"]: item for item in scored["summary"]}
        self.assertEqual("INVOICE", scored["kind"])
        self.assertEqual((1, 1, 1, 1, 1), tuple(summary["Xanh · Bán ra"][key] for key in ("matched", "account_ok", "partner_ok", "counterparty_ok", "project_ok")))
        self.assertEqual((1, 1, 0), tuple(summary["Vàng · Mua vào"][key] for key in ("account_ok", "partner_ok", "counterparty_ok")))
        path = quick.write_score_workbook(self.root / "score.xlsx", scored)
        book = load_workbook(path)
        self.assertIn("TK công nợ đúng", [cell.value for cell in book["TONG HOP"][1]])
        self.assertEqual("Mua vào/Bán ra", book["CHI TIET"]["B1"].value)


class V12OperationsTests(FeatureCase):
    def test_saving_settings_keeps_the_invoice_folder_and_months_after_the_cut_are_test_months(self):
        from kho_tri_thuc.giao_dien.operations import Operations
        config_path = self.root / "that.toml"
        config_path.write_text("""[app]\nenvironment='that'\nentity_id='PLHN_SYN'\ndata_dir='that'\n[money]\ncurrency='VND'\nscale=0\n[operation]\njunsky_export_enabled=false\njunsky_import_enabled=false\ncatalog_valid_from='1900-01-01'\nknowledge_approval_actor='CFO_NTD'\n""", encoding="utf-8")
        invoices = self.root / "hoa-don"
        for month in ("2026-06", "2026-07"):
            folder = invoices / month / "mua_vao"; folder.mkdir(parents=True)
            (folder / "a.xml").write_text("<HDon/>", encoding="utf-8")
        app = Operations(config_path, self.root / "web")
        paths = {key: str(self.root / ("khong-co-" + key)) for key in ("junsky_catalog", "junsky_dgblist", "junsky_ledger", "bank", "base")}
        paths["invoice"] = str(invoices)
        app.save_source_settings({"paths": paths, "settings": {"learning_cutoff": "2026-06-30"}})
        from kho_tri_thuc.ha_tang.store import Store
        with Store(app.config) as store:
            runtime = json.loads(store.conn.execute("SELECT value FROM workspace_meta WHERE key='v9b_runtime_settings'").fetchone()[0])
        self.assertEqual(str(invoices), runtime["invoice_root"])
        months = app.invoice_months()
        self.assertEqual([("2026-07", False), ("2026-06", True)], [(item["month"], item["learning"]) for item in months["months"]])
