#!/usr/bin/env python3
"""L0-2i: kiểm kê code còn trong bản chụp, không thay đổi git hay nguồn.

Chạy bằng ``python -X utf8 tools/do_file_chua_vao_git.py <REPO>``.
Chỉ ghi hai báo cáo cạnh worktree chứa script; stdout là JSON kiểm kê.
``--self-test`` chạy kiểm thử trong bộ nhớ, không tạo file/cache.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import os
import posixpath
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import defaultdict


ROOTS = {"src", "tests", "tools"}
EXTENSIONS = {".py", ".js", ".css", ".html", ".sql", ".json", ".tsv", ".md"}
DOC_DIR = Path("docs/46-chuyen-doi-dieu-phoi")
INTEGRATION = "hop-nhat-20261023"
FIELDS = [
    "nhom", "duong_dan", "ban_chup_moi_nhat", "so_phien_ban", "ai_tham_chieu",
    "de_xuat_nhanh", "goi", "cac_ban_chup", "mtime_ban_chup_utc", "ai_import",
    "co_so_de_xuat", "blob_chuan_hoa", "noi_dung_co_o_duong_dan_git_khac",
]


def forbidden_name(name: str) -> bool:
    name = name.lower()
    return (name in {"var", "__pycache__", ".git", "tri-thuc-cfo.json"}
            or name.startswith(".env")
            or (name.startswith("cau_hinh") and name.endswith(".toml")))


def allowed_path(path: str) -> bool:
    p = PurePosixPath(path)
    return (len(p.parts) > 1 and p.parts[0] in ROOTS
            and not any(forbidden_name(part) for part in p.parts)
            and p.suffix.lower() in EXTENSIONS)


def blob_hash(data: bytes) -> str:
    data = data.replace(b"\r", b"")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def utc(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1_000_000_000, timezone.utc).isoformat(timespec="microseconds")


def git(repo: Path, *args: str, input_data: bytes | None = None) -> bytes:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    return subprocess.run(["git", "-C", str(repo), *args], input=input_data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True, env=env).stdout


def parse_tree(data: bytes) -> dict[str, str]:
    tree = {}
    for record in data.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        path = raw_path.decode("utf-8")
        # Không dereference symlink; gitlink/submodule không phải blob nguồn.
        if kind == b"blob" and mode in {b"100644", b"100755"} and allowed_path(path):
            tree[path] = oid.decode("ascii")
    return tree


def read_blobs(repo: Path, ids: set[str]) -> dict[str, bytes]:
    ordered = sorted(ids)
    if not ordered:
        return {}
    stream = io.BytesIO(git(repo, "cat-file", "--batch",
                            input_data=("\n".join(ordered) + "\n").encode("ascii")))
    result = {}
    for oid in ordered:
        header = stream.readline().decode("ascii").split()
        if len(header) != 3 or header[0] != oid or header[1] != "blob":
            raise ValueError("git cat-file trả header không hợp lệ")
        size = int(header[2])
        data = stream.read(size)
        if len(data) != size or stream.read(1) != b"\n":
            raise ValueError("git cat-file trả blob thiếu dữ liệu")
        result[oid] = data
    if stream.read():
        raise ValueError("git cat-file trả dữ liệu thừa")
    return result


def parse_heads(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and "-code-frozen-" in cells[1]:
            if cells[0] in result:
                raise ValueError("Gói bị lặp trong bảng Frozen head: " + cells[0])
            result[cells[0]] = cells[1]
    if not result:
        raise ValueError("Không tìm thấy cột Frozen head")
    return result


@dataclass
class Snapshot:
    name: str
    root: Path
    files: dict[str, str]
    latest_ns: int
    kind: str


def is_link(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def scan_snapshot(base: Path, source: Path, kind: str) -> Snapshot:
    latest = max(source.stat().st_mtime_ns, source.parent.stat().st_mtime_ns)
    files = {}
    for root_name in sorted(ROOTS):
        start = source / root_name
        if is_link(start) or not start.is_dir():
            continue
        # Chỉ duyệt ba cây cho phép; không scandir var hay thư mục nhạy cảm.
        for directory, dirs, names in os.walk(start, followlinks=False):
            current = Path(directory)
            dirs[:] = sorted(d for d in dirs if not forbidden_name(d) and not is_link(current / d))
            latest = max(latest, current.stat().st_mtime_ns)
            for name in sorted(names):
                p = current / name
                rel = p.relative_to(source).as_posix()
                if not allowed_path(rel) or is_link(p):
                    continue
                before = p.stat()
                content = p.read_bytes()
                after = p.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise RuntimeError("File thay đổi trong lúc quét: " + rel)
                latest = max(latest, after.st_mtime_ns)
                files[rel] = blob_hash(content)
    return Snapshot(source.relative_to(base).as_posix(), source, files, latest, kind)


def discover(base: Path) -> list[Snapshot]:
    sources = []
    for entry in sorted(base.iterdir()):
        if forbidden_name(entry.name) or is_link(entry) or not entry.is_dir():
            continue
        source = entry / "files"
        if "frozen" in entry.name.lower() and not is_link(source) and source.is_dir():
            sources.append((source, "frozen"))
        if entry.name == "isolated-head-jobs":
            for job in sorted(entry.iterdir()):
                if forbidden_name(job.name) or is_link(job) or not job.is_dir():
                    continue
                workspace = job / "workspace"
                if not is_link(workspace) and workspace.is_dir():
                    sources.append((workspace, "workspace"))
    snapshots = []
    # Các bản chụp độc lập, chỉ đọc; map giữ nguyên thứ tự kết quả để chạy lại ổn định.
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(lambda item: scan_snapshot(base, *item), sources)
        for number, snapshot in enumerate(results, 1):
            snapshots.append(snapshot)
            if number % 20 == 0:
                print(f"Đã quét {number}/{len(sources)} bản chụp", file=sys.stderr, flush=True)
    return snapshots


def latest_snapshot(candidates: list[Snapshot]) -> Snapshot:
    # Tên là tie-break ổn định; timestamp bằng nhau không chứng minh thứ tự tạo.
    return max(candidates, key=lambda s: (s.latest_ns, s.name))


def imported_modules(data: bytes, source: str = "") -> set[str]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(data.decode("utf-8-sig"))
    except (SyntaxError, UnicodeDecodeError, ValueError):
        return set()
    modules = set()
    package_parts = list(PurePosixPath(source).parent.parts)
    if package_parts[:1] == ["src"]:
        package_parts = package_parts[1:]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = node.module or ""
            if node.level:
                if not source or node.level > len(package_parts):
                    continue
                base = package_parts[:len(package_parts) - node.level + 1]
                prefix = ".".join(base + ([prefix] if prefix else []))
            if node.module:
                modules.add(prefix)
            modules.update((prefix + "." if prefix else "") + alias.name
                           for alias in node.names if alias.name != "*")
    return modules


def references(paths: set[str], integration: dict[str, str],
               blobs: dict[str, bytes]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    by_stem = defaultdict(list)
    for path in sorted(paths):
        by_stem[PurePosixPath(path).stem].append(path)
    refs, imports = defaultdict(set), defaultdict(set)
    # Tương đương grep tên module theo ranh giới từ, không in dòng nội dung.
    pattern = re.compile(r"(?<![\w])(?:" + "|".join(re.escape(s) for s in by_stem) + r")(?![\w])") if by_stem else None
    for source, oid in sorted(integration.items()):
        data = blobs[oid]
        stems = {m.group(0) for m in pattern.finditer(data.decode("utf-8-sig"))} if pattern else set()
        for stem in stems:
            for target in by_stem[stem]:
                if source != target:
                    refs[target].add(source)
        if PurePosixPath(source).suffix in {".js", ".html"}:
            # Chỉ nhận literal tương đối và phân giải đúng thư mục, không grep basename.
            js = data.decode("utf-8-sig")
            js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
            js = re.sub(r"(?m)^\s*//.*$", "", js)
            pattern_js = r"\b(?:from\s*|import\s*(?:\(\s*)?|require\s*\(\s*)['\"](\.{1,2}/[^'\"]+)['\"]"
            for module in re.findall(pattern_js, js):
                resolved = posixpath.normpath(posixpath.join(str(PurePosixPath(source).parent), module))
                for target in [resolved, resolved + ".js", resolved + ".json", resolved + "/index.js"]:
                    if target in paths and source != target:
                        imports[target].add(source)
        if PurePosixPath(source).suffix != ".py":
            continue
        for module in imported_modules(data, source):
            stem = module.rsplit(".", 1)[-1]
            for target in by_stem.get(stem, []):
                if PurePosixPath(target).suffix != ".py":
                    continue
                # Cả import test_x và from tests import test_x đều được nhận.
                canonical = str(PurePosixPath(target).with_suffix("")).replace("/", ".")
                aliases = {canonical, canonical.removeprefix("src.")}
                if PurePosixPath(source).parent == PurePosixPath(target).parent:
                    aliases.add(stem)
                if source != target and module in aliases:
                    imports[target].add(source)
    return ({p: sorted(v) for p, v in refs.items()}, {p: sorted(v) for p, v in imports.items()})


def propose(path: str, candidates: list[Snapshot], heads: dict[str, str],
            branches: list[str]) -> tuple[str, str, str]:
    """Suy luận sở hữu từ tên file + tên gói mang bản chụp, không tự khẳng định."""
    known = set(heads) | {b.removeprefix("luu/") for b in branches if b.startswith("luu/")}
    available = set()
    for snapshot in candidates:
        name = snapshot.root.parent.name
        if snapshot.kind == "workspace":
            available.add(name)
        else:
            match = re.match(r"(.+?)-(?:code-|runtime-|partial-)?frozen-", name)
            if match:
                available.add(match.group(1))
    choices = available | {k for k in known if any(k in s.name for s in candidates)}
    filename = PurePosixPath(path).stem.lower().replace("_", "-")

    def score(package: str) -> tuple[int, int, str]:
        tokens = set(re.findall(r"[a-z]+\d*|\d+[a-z]*", package))
        ftokens = set(re.findall(r"[a-z]+\d*|\d+[a-z]*", filename))
        common = tokens & ftokens - {"test", "tests", "py", "code", "01", "20261023", "20261022"}
        value = sum(len(token) for token in common)
        # Nhóm request backend sở hữu API/SQL và bộ test request nền; gói M27
        # có thể mang chúng theo trong full-copy nhưng chức năng chính là migration.
        if (filename in {"request-api", "sql-request-nhap"} or filename.startswith("test-m4-request-")):
            value += 100 if package.startswith("m4-04a-request-backend-") else 0
        if filename in {"test-m4-03a-http", "test-m4-03a-pg"}:
            value += 100 if package.startswith("m4-03a-kt-backend-") else 0
        if package in known:
            value += 2
        # Ưu tiên gói gốc thay vì bản fix khi file có tên chức năng gốc.
        value -= 2 if re.search(r"fix\d+", package) else 0
        return value, -len(package), package

    if not choices:
        return "lead cần xác định gói", "chưa xác định", "Không suy ra gói từ tên bản chụp"
    owner = max(choices, key=score)
    branch = "luu/" + owner
    if branch not in branches:
        branch += " (đề xuất mới)"
    return branch, owner, "Suy luận theo tên file/gói trong bản chụp; lead xác nhận sở hữu"


def classify(snapshots: list[Snapshot], heads: dict[str, str], trees: dict[str, dict[str, str]],
             normalized: dict[str, str], blobs: dict[str, bytes]) -> tuple[list[dict], dict]:
    existing = set().union(*(set(tree) for tree in trees.values()))
    all_git_content = set(normalized.values())
    versions, occurrences = defaultdict(set), defaultdict(list)
    for snapshot in snapshots:
        for path, digest in snapshot.files.items():
            versions[path].add(digest)
            occurrences[path].append(snapshot)
    absent = set(occurrences) - existing
    selected = {}
    for package, head in heads.items():
        matches = [s for s in snapshots if s.kind == "frozen" and s.root.parent.name == head]
        if len(matches) != 1:
            raise ValueError(f"Frozen head phải tìm thấy đúng một bản: {package}: {head} ({len(matches)})")
        selected[package] = matches[0]
    b_candidates = [(package, s, path) for package, s in selected.items()
                    for path, digest in s.files.items()
                    if path in existing and digest not in all_git_content]
    targets = absent | {p for _, _, p in b_candidates}
    refs, imports = references(targets, trees[INTEGRATION], blobs)
    rows = []

    def row(group: str, path: str, snapshot: Snapshot, package: str = "") -> dict:
        if group == "A":
            branch, package, basis = propose(path, occurrences[path], heads, list(trees))
        else:
            branch, basis = "luu/" + package, "Soát delta tại Frozen head chỉ định; không tự chép đè"
        return dict(zip(FIELDS, [
            group, path, snapshot.name, len(versions[path]), "; ".join(refs.get(path, [])),
            branch, package, "; ".join(sorted(s.name for s in occurrences[path])), utc(snapshot.latest_ns),
            "; ".join(imports.get(path, [])), basis, snapshot.files[path],
            "có" if snapshot.files[path] in all_git_content else "không",
        ]))

    for path in sorted(absent):
        rows.append(row("A", path, latest_snapshot(occurrences[path])))
    for package, snapshot, path in sorted(b_candidates, key=lambda item: (item[2], item[0])):
        rows.append(row("B", path, snapshot, package))
    # Chỉ thống kê, không đưa vào B: phiên bản khác nhưng blob đã có dưới tên khác.
    path_content = defaultdict(set)
    for tree in trees.values():
        for path, oid in tree.items():
            path_content[path].add(normalized[oid])
    moved = {(package, path) for package, snapshot in selected.items()
             for path, digest in snapshot.files.items()
             if path in existing and digest not in path_content[path] and digest in all_git_content}
    return rows, {"A": len(absent), "B": len({p for _, _, p in b_candidates}),
                  "B_file_goi": len(b_candidates), "head_da_doi_chieu": len(selected),
                  "blob_co_duoi_ten_khac": len(moved)}


def markdown(rows: list[dict], summary: dict) -> str:
    a_rows = [r for r in rows if r["nhom"] == "A"]
    imported = sorted((r for r in a_rows if r["ai_import"]),
                      key=lambda r: (-len(r["ai_import"].split("; ")), r["duong_dan"]))
    table = ["| File nhóm A đang được import | File trên hop-nhat import nó | Đề xuất nhánh (suy luận) |",
             "|---|---|---|"]
    for r in imported[:10]:
        callers = r["ai_import"].split("; ")
        display = callers[0] + (f" (+{len(callers) - 1}, xem CSV)" if len(callers) > 1 else "")
        table.append(f"| `{r['duong_dan']}` | {display} | `{r['de_xuat_nhanh']}` |")
    if not imported:
        table.append("| Không tìm thấy import tĩnh | — | — |")
    return "\n".join([
        "# L0-2i — File chưa vào git", "",
        f"Đối chiếu {summary['so_nhanh']} nhánh (`hop-nhat-20261023`, `chinh`, toàn bộ `luu/*`): "
        f"**A = {summary['A']} đường dẫn; B = {summary['B']} đường dẫn ({summary['B_file_goi']} cặp file–gói).** "
        f"Đã quét {summary['so_ban_chup']} bản chụp ({summary['frozen']} frozen + {summary['workspace']} workspace), "
        f"{summary['so_luot_file']} lượt file/{summary['so_duong_dan_ban_chup']} đường dẫn; "
        f"B chỉ xét {summary['head_da_doi_chieu']} Frozen head trong `TAN-DUNG-CODE.md`.", "",
        f"Mốc đầu nhánh git: {summary['moc_git_utc']} (UTC); đọc blob theo commit đã ghim, "
        "không chạy theo cập nhật nhánh sau mốc này.", "",
        f"Có **{len(imported)} file A có import xác định được** trên hop-nhat; bảng hiển thị tối đa 10 file, "
        "ưu tiên số file gọi. CSV lưu mọi bản chụp chứa file, số phiên bản, import/tham chiếu và đề xuất cho từng file A.", "",
        *table, "",
        "Đề xuất: lead khôi phục trước các dependency trong bảng vào nhánh gói sở hữu, "
        "rồi review các A còn lại theo CSV; B cần review delta từng gói trước khi hợp nhất. "
        "Tên nhánh suy từ tên file và gói mang bản chụp, cần lead xác nhận; bản chụp có thể chứa code kế thừa.", "",
        "Phương pháp/giới hạn: so SHA1 blob sau khi bỏ mọi byte CR ở cả git và bản chụp; "
        "A xét đường dẫn, B xét tập blob toàn bộ cây cho phép trên các nhánh, kể cả blob ở tên khác "
        f"({summary['blob_co_duoi_ten_khac']} cặp file–gói đã khớp dưới tên khác). "
        "Không xét lịch sử commit, nhánh ngoài danh sách, file ngoài allowlist, symlink/junction hoặc dữ liệu thật. "
        "Mtime mới nhất = max metadata thư mục snapshot/files (hoặc job/workspace), thư mục và file hợp lệ "
        "trong src/tests/tools; không phải thứ tự tạo/phiên bản ngữ nghĩa. "
        "Import phân giải AST Python và literal tương đối JS/HTML; tham chiếu grep tên module có thể trùng tên hoặc nằm trong comment; "
        "không bảo đảm tìm được dynamic import. Kiểm kê chi tiết mtime xuất JSON ra stdout khi chạy script.", "",
        "Chạy lại: `python -X utf8 tools/do_file_chua_vao_git.py <REPO>`; "
        "kiểm thử trong bộ nhớ: thêm `--self-test` (không cần REPO). Không chạy suite ứng dụng hay dịch vụ ngoài.", "",
        "Bàn giao: CSV có sẵn trên đĩa nhưng bị `.gitignore:13` (`*.csv`) bỏ qua; "
        "lead cần đưa đích danh CSV vào commit. Worker không add/commit.", "",
    ])


def self_test() -> None:
    import unittest

    class Checks(unittest.TestCase):
        def test_crlf_blob(self):
            self.assertEqual(blob_hash(b"a\r\nb\rc"), blob_hash(b"a\nbc"))
            self.assertEqual(blob_hash(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")

        def test_scope(self):
            for path in ["src/a.py", "tests/fixtures/a.json", "tools/a.tsv", "src/a.md"]:
                self.assertTrue(allowed_path(path), path)
            for path in ["var/a.py", "src/var/a.py", "src/.env.json", "tests/fixtures/a.xml",
                         "tools/TRI-THUC-CFO.json", "src/__pycache__/a.py", "tests/a.sqlite",
                         "src/cau_hinh.that.toml", "src/a.xlsx"]:
                self.assertFalse(allowed_path(path), path)

        def test_tree_filter(self):
            data = b"100644 blob abc\tsrc/a.py\0" + b"120000 blob def\ttests/link.py\0"
            self.assertEqual(parse_tree(data), {"src/a.py": "abc"})

        def test_heads(self):
            text = "| Gói | Frozen head |\n| x | `x-code-frozen-abc` | extra |"
            self.assertEqual(parse_heads(text), {"x": "x-code-frozen-abc"})

        def test_ast_import(self):
            modules = imported_modules(b"from tests import test_a\nimport test_b as b\nfrom tests.test_c import helper\n")
            self.assertTrue({"tests.test_a", "test_b", "tests.test_c"} <= modules)
            self.assertEqual(imported_modules(b"broken syntax!"), set())

        def test_reference_boundary(self):
            blobs = {"a": b"from tests.test_a import helper\n# test_ab\n"}
            refs, imports = references({"tests/test_a.py", "tests/test_ab.py", "tests/test_abc.py"},
                                       {"tests/caller.py": "a"}, blobs)
            self.assertEqual(imports, {"tests/test_a.py": ["tests/caller.py"]})
            self.assertNotIn("tests/test_abc.py", refs)
            self.assertIn("tests/test_ab.py", refs)

        def test_import_same_name_different_package(self):
            targets = {"tools/source6_lazy_excel/master_hd.py", "src/pkg/master_hd.py",
                       "tools/source7_m2_patch/config.js"}
            _, imports = references(targets, {"src/pkg/reader.py": "oid"},
                                    {"oid": b"from . import master_hd\nimport config\n"})
            self.assertEqual(imports, {"src/pkg/master_hd.py": ["src/pkg/reader.py"]})

        def test_js_relative_import(self):
            target = "tools/source7_m2_patch/config.js"
            source = "tools/source7_m2_patch/src/job.js"
            _, imports = references({target}, {source: "oid"},
                                    {"oid": b"const config = require('../config');\n"})
            self.assertEqual(imports, {target: [source]})

        def test_classification_and_selected_heads(self):
            old = Snapshot("x-code-frozen-old/files", Path("x-code-frozen-old/files"),
                           {"tests/a.py": blob_hash(b"old"), "tests/missing.py": blob_hash(b"new")}, 1, "frozen")
            head = Snapshot("x-code-frozen-new/files", Path("x-code-frozen-new/files"),
                            {"tests/a.py": blob_hash(b"new"), "tests/missing.py": blob_hash(b"new")}, 2, "frozen")
            workspace = Snapshot("isolated-head-jobs/x/workspace", Path("isolated-head-jobs/x/workspace"),
                                 {"tests/a.py": blob_hash(b"workspace-only")}, 3, "workspace")
            trees = {INTEGRATION: {"tests/a.py": "oid"}}
            rows, stats = classify([old, head, workspace], {"x": "x-code-frozen-new"}, trees,
                                   {"oid": blob_hash(b"old")}, {"oid": b"old"})
            self.assertEqual((stats["A"], stats["B"], stats["B_file_goi"]), (1, 1, 1))
            self.assertEqual(rows[0]["duong_dan"], "tests/missing.py")
            self.assertEqual(rows[1]["ban_chup_moi_nhat"], head.name)
            self.assertEqual(rows[1]["so_phien_ban"], 3)

        def test_content_already_saved_under_other_path(self):
            snapshot = Snapshot("x-code-frozen-new/files", Path("x-code-frozen-new/files"),
                                {"tests/a.py": blob_hash(b"new")}, 2, "frozen")
            rows, stats = classify([snapshot], {"x": "x-code-frozen-new"},
                                   {INTEGRATION: {"tests/a.py": "old", "tests/renamed.py": "new"}},
                                   {"old": blob_hash(b"old"), "new": blob_hash(b"new")},
                                   {"old": b"old", "new": b"new"})
            self.assertFalse(rows)
            self.assertEqual(stats["blob_co_duoi_ten_khac"], 1)

        def test_owner_from_snapshot(self):
            snapshot = Snapshot("m4-03a-kt-backend-20261023-01-code-frozen-abc/files",
                                Path("m4-03a-kt-backend-20261023-01-code-frozen-abc/files"), {}, 1, "frozen")
            branch, _, _ = propose("tests/test_m4_03a_pg.py", [snapshot],
                                   {"m4-03a-kt-backend-20261023-01": "unused"},
                                   ["luu/m4-03a-kt-backend-20261023-01"])
            self.assertEqual(branch, "luu/m4-03a-kt-backend-20261023-01")

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    if not result.wasSuccessful():
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path, nargs="?", help="Repo chính chứa var/codex-dieu-phoi")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.repo is None:
        parser.error("Cần đường dẫn REPO hoặc --self-test")
    repo = args.repo.resolve(strict=True)
    worktree = Path(__file__).resolve().parent.parent
    output = worktree / DOC_DIR
    heads = parse_heads((output / "TAN-DUNG-CODE.md").read_text(encoding="utf-8-sig"))
    snapshots = discover(repo / "var/codex-dieu-phoi")
    # Dùng git tại worktree đã được cấp quyền, cùng kho object với REPO.
    # Chụp ref -> commit một lần SAU quét; lead có thể tiếp tục commit khi worker chạy.
    ref_lines = git(worktree, "for-each-ref", "--format=%(refname:short)%09%(objectname)",
                    "refs/heads").decode("utf-8").splitlines()
    refs = dict(line.split("\t", 1) for line in ref_lines)
    git_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
    branches = [INTEGRATION, "chinh"] + sorted(r for r in refs if r.startswith("luu/"))
    if any(branch not in refs for branch in branches[:2]):
        raise ValueError("Thiếu nhánh hop-nhat hoặc chinh")
    commits = {b: refs[b] for b in branches}
    trees = {b: parse_tree(git(worktree, "ls-tree", "-r", "-z", commit)) for b, commit in commits.items()}
    blobs = read_blobs(worktree, {oid for tree in trees.values() for oid in tree.values()})
    normalized = {oid: blob_hash(data) for oid, data in blobs.items()}
    print(f"Đã đọc {len(branches)} nhánh/{len(blobs)} blob cho phép", file=sys.stderr, flush=True)
    rows, stats = classify(snapshots, heads, trees, normalized, blobs)
    summary = dict(stats, moc_git_utc=git_time, so_nhanh=len(branches), so_ban_chup=len(snapshots),
                   frozen=sum(s.kind == "frozen" for s in snapshots),
                   workspace=sum(s.kind == "workspace" for s in snapshots),
                   so_luot_file=sum(len(s.files) for s in snapshots),
                   so_duong_dan_ban_chup=len(set().union(*(set(s.files) for s in snapshots))))
    # Không mkdir, không log/cache riêng, không ghi .git; chỉ hai đầu ra được duyệt.
    with (output / "FILE-CHUA-VAO-GIT.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (output / "FILE-CHUA-VAO-GIT.md").write_text(markdown(rows, summary), encoding="utf-8", newline="\n")
    print(json.dumps(dict(summary=summary, branches=commits,
                          snapshots=[dict(ban_chup=s.name, loai=s.kind, mtime_utc=utc(s.latest_ns),
                                          so_file=len(s.files)) for s in snapshots]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
