"""G2-33: pure preview/ACL templates; never provision accounts or write ACLs."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "tao_tai_khoan_core.ps1"
CMD = ROOT / "tools" / "CAI-TAI-KHOAN-CORE.cmd"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("pwsh")
ACCOUNTS = {"ktt_core", "ktt_module", "ktt_e_mask", "ktt_e_ai", "ktt_e_hoa_don", "ktt_e_ocr"}


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def powershell(code: str) -> subprocess.CompletedProcess:
    encoded = base64.b64encode(code.encode("utf-16-le")).decode("ascii")
    return subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )


class StaticTests(unittest.TestCase):
    def test_only_safe_source_commands(self):
        source = SCRIPT.read_text(encoding="utf-8") + CMD.read_text(encoding="utf-8")
        self.assertNotRegex(source.lower(), r"\b(remove-item|remove-localuser|clear-content|erase|rmdir|rd|del|rm)\b")
        # This fallback revision must contain no mutation path at all.
        self.assertNotRegex(source.lower(), r"\b(new-localuser|set-localuser|set-acl|icacls|new-item|out-file|set-content)\b")
        self.assertNotIn("WriteAll", source)

    def test_no_credential_output_or_insecure_protection(self):
        source = SCRIPT.read_text(encoding="utf-8") + CMD.read_text(encoding="utf-8")
        self.assertNotRegex(source, r"(?i)(write-(?:output|host|warning|error)|echo).*\$(?:password|matkhau|secret|credential)\b")
        self.assertNotRegex(source, r"(?i)ConvertFrom-SecureString|AsPlainText|NetworkCredential|LocalMachine\s*\)")
        self.assertNotRegex(source, r"(?i)-ExecutionPolicy\s+Bypass|Add-LocalGroupMember|net\s+user")

    def test_wrapper_preview_confirm_elevate_in_order(self):
        source = CMD.read_text(encoding="utf-8")
        self.assertLess(source.index('-File "%KTT_CORE_SCRIPT%"'), source.index("choice /C YN"))
        self.assertLess(source.index("choice /C YN"), source.index("-Verb RunAs"))
        self.assertIn("-WindowStyle Hidden", source)
        self.assertIn("-Wait -PassThru", source)
        self.assertIn("exit $p.ExitCode", source)
        self.assertIn("if errorlevel 2 goto Huy", source)
        self.assertIn("DisableDelayedExpansion", source)
        self.assertIn("$env:KTT_CORE_SCRIPT", source)

    def test_utf8_without_bom(self):
        for path in (SCRIPT, CMD, Path(__file__)):
            with self.subTest(path=path.name):
                data = path.read_bytes()
                self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
                data.decode("utf-8")


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "Windows PowerShell unavailable")
class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # AST execution is confined to pure preview tests. Do not alter the
        # host ExecutionPolicy; the production .cmd still uses normal -File.
        cls.functions = (
            "$tokens=$null; $errors=$null; "
            "$ast=[Management.Automation.Language.Parser]::ParseFile("
            + ps_quote(str(SCRIPT)) + ",[ref]$tokens,[ref]$errors); "
            "if($errors.Count){throw ($errors | Out-String)}; "
            "$ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},"
            "$false) | ForEach-Object { . ([scriptblock]::Create($_.Extent.Text)) }; "
        )
        cls.preview = (
            "$tokens=$null; $errors=$null; "
            "$ast=[Management.Automation.Language.Parser]::ParseFile("
            + ps_quote(str(SCRIPT)) + ",[ref]$tokens,[ref]$errors); "
            "if($errors.Count){throw ($errors | Out-String)}; $preview=$ast.GetScriptBlock(); "
        )
        result = powershell(cls.preview + "& $preview -Json")
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.plan = json.loads(result.stdout)

    def test_default_preview_is_repeatable(self):
        result = powershell(self.preview + "& $preview -Json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), self.plan)
        self.assertEqual(self.plan["TrangThai"], "CAN_LEAD")
        self.assertFalse(self.plan["SanSangApDung"])

    def test_six_distinct_local_accounts_without_admin(self):
        self.assertEqual({a["Ten"] for a in self.plan["TaiKhoan"]}, ACCOUNTS)
        self.assertEqual(len(self.plan["TaiKhoan"]), 6)
        self.assertTrue(all(a["Loai"] == "LocalUser" and not a["QuanTri"] for a in self.plan["TaiKhoan"]))

    def test_vault_and_file_store_core_only(self):
        for name in ("bi-mat", "tep"):
            acl = next(a for a in self.plan["Acl"] if Path(a["DuongDan"]).name == name)
            self.assertEqual(acl["ChuSoHuu"], "ktt_core")
            self.assertFalse(acl["KeThua"])
            self.assertTrue(acl["ThayTheDacl"])
            self.assertEqual(acl["Quyen"], [{"TaiKhoan": "ktt_core", "Quyen": "FullControl", "TruyenXuong": True}])

    def test_engine_and_module_rights_are_separate(self):
        for name, account in (("module", "ktt_module"), ("e_mask", "ktt_e_mask"),
                              ("e_ai", "ktt_e_ai"), ("e_hoa_don", "ktt_e_hoa_don"), ("e_ocr", "ktt_e_ocr")):
            for parent, right in (("chuong-trinh", "ReadAndExecute"), ("lam-viec", "Modify")):
                with self.subTest(name=name, parent=parent):
                    acl = next(a for a in self.plan["Acl"] if Path(a["DuongDan"]).parts[-2:] == (parent, name))
                    self.assertFalse(acl["KeThua"])
                    self.assertEqual({q["TaiKhoan"]: q["Quyen"] for q in acl["Quyen"]},
                                     {"ktt_core": "FullControl", account: right})

    def test_parent_traversal_does_not_inherit_or_list(self):
        acl = self.plan["Acl"][0]
        self.assertEqual({q["TaiKhoan"] for q in acl["Quyen"]}, ACCOUNTS)
        for q in acl["Quyen"]:
            if q["TaiKhoan"] != "ktt_core":
                self.assertEqual(q["Quyen"], "Traverse")
                self.assertFalse(q["TruyenXuong"])

    def test_real_and_ambiguous_targets_refused_without_io(self):
        targets = [r"D:\DU-LIEU-KE-TOAN\bi-mat", r"\\server\share", r"\\?\D:\DU-LIEU-KE-TOAN",
                   str(self.plan["GocDemo"]) + "-khac", str(self.plan["GocDemo"]) + ":ads",
                   str(self.plan["GocDemo"]) + r"\..\g2-33", r"var\core-demo\g2-33"]
        code = self.preview + "function Test-Path {throw 'IO_FORBIDDEN'}; function Get-Item {throw 'IO_FORBIDDEN'}; "
        code += "$targets=@(" + ",".join(ps_quote(t) for t in targets) + "); "
        code += "foreach($t in $targets){try{& $preview -ThuMucDemo $t; throw 'ACCEPTED'}catch{if($_.ToString() -notmatch 'TU_CHOI_DICH'){throw}}}; 'OK'"
        result = powershell(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "OK")

    def test_acl_template_protected_exact_and_repeatable(self):
        code = self.preview + "$plan=& $preview -Json | ConvertFrom-Json; " + self.functions + "$sid=@{}; $i=1000; "
        code += "foreach($t in $plan.TaiKhoan){$sid[$t.Ten]='S-1-5-21-111-222-333-'+$i; $i++}; "
        code += "$m=$plan.Acl | Where-Object { $_.DuongDan.EndsWith('\\bi-mat') }; "
        code += "$a=New-AclTrongBoNho $m $sid; $b=New-AclTrongBoNho $m $sid; "
        code += "$rules=$a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]); "
        code += "if(!$a.AreAccessRulesProtected -or $rules.Count -ne 1){throw 'ACL'}; "
        code += "if($a.Sddl -ne $b.Sddl -or $a.Sddl -notmatch 'D:P'){throw 'DACL'}; "
        code += "if($a.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $sid.ktt_core){throw 'OWNER'}; "
        code += "if($rules[0].IdentityReference.Value -ne $sid.ktt_core){throw 'SID'}; 'OK'"
        result = powershell(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "OK")

    def test_admin_and_dpapi_gates_with_mock_only(self):
        # No script -ApDung invocation, account creation or actual elevation.
        code = self.functions
        code += "function Test-QuyenQuanTri {return $false}; "
        code += "try{Assert-SanSangApDung; throw 'BYPASS'}catch{if($_.ToString() -notmatch 'CAN_QUYEN_QUAN_TRI'){throw}}; "
        code += "function Test-QuyenQuanTri {return $true}; "
        code += "try{Assert-SanSangApDung; throw 'BYPASS'}catch{if($_.ToString() -notmatch 'CAN_LEAD'){throw}}; 'OK'"
        result = powershell(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "OK")


if __name__ == "__main__":
    unittest.main()
