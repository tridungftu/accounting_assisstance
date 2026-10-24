"""Nạp lõi Review hồ sơ xây dựng vào package M4 (Root chạy sau terminal; Claude KHÔNG chạy).

Sao chép BYTE-FOR-BYTE các tệp kỹ thuật từ reference đã lọc `docs/M4-REVIEW-REFERENCE-20261020/` (manifest SHA-256) vào
`src/kho_tri_thuc/m4/review_goc/`, giữ nguyên đường dẫn tương đối. Bỏ qua tests/, *.md và hardcode_audit.py (không phải mã chạy).

An toàn (M4-01B, B4): chỉ TẠO tệp mới (CreateNew — mở chế độ 'xb'); tệp đích đã có cùng bytes → bỏ qua; đã có khác bytes/symlink/không phải tệp
→ dừng, KHÔNG ghi đè/xóa/đổi tên. Mọi tệp nguồn phải khớp manifest (SHA + độ dài) VÀ khớp PIN trong kho_tri_thuc/m4/nguon_review.py.
`--kiem` chỉ kiểm, không ghi: còn BẤT KỲ tệp nào chưa nạp → mã thoát 1 (liệt kê từng tệp), không báo "xong".
Không đọc app nguồn ngoài workspace, không mạng, không cấu hình/khóa.

Mã thoát: 0 đủ/đã nạp đúng; 1 (--kiem) còn tệp chưa nạp; 2 manifest/PIN/reference sai; 3 đích khác bytes; 4 ghi xong hash khác.

Dùng:  python tools/nap_nguon_review_m4.py            (sao chép + kiểm)
       python tools/nap_nguon_review_m4.py --kiem     (chỉ kiểm, không ghi)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NGUON = ROOT / "docs" / "M4-REVIEW-REFERENCE-20261020"
DICH = ROOT / "src" / "kho_tri_thuc" / "m4" / "review_goc"
BO_QUA_THU_MUC = ("tests/",)
BO_QUA_TEP = ("hardcode_audit.py",)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _pin() -> dict:
    """PIN của adapter (chỉ hằng số; nguon_review KHÔNG nạp lõi nguồn khi import)."""
    sys.path.insert(0, str(ROOT / "src"))
    from kho_tri_thuc.m4.nguon_review import FONT_PIN, PIN
    return {**PIN, **{f"giao_dien/fonts/{k}": v for k, v in FONT_PIN.items()}}


def chon(manifest: list[dict]) -> list[dict]:
    return [e for e in manifest if not e["path"].startswith(BO_QUA_THU_MUC) and not e["path"].endswith(".md") and e["path"] not in BO_QUA_TEP]


def chay(chi_kiem: bool, *, nguon: Path = NGUON, dich: Path = DICH, pin: dict | None = None, in_ra=print) -> int:
    nguon, dich = Path(nguon), Path(dich)
    manifest = json.loads((nguon / "manifest.json").read_text("utf-8"))
    pin = _pin() if pin is None else dict(pin)
    cac = chon(manifest)
    co_trong_manifest = {e["path"] for e in cac}
    thieu_pin = sorted(set(pin) - co_trong_manifest)
    if thieu_pin:
        in_ra("PIN có tệp không thuộc manifest đã chọn:", thieu_pin)
        return 2
    tao = giu = 0
    chua_nap = []
    for e in cac:
        rel = e["path"]
        if "\\" in rel or rel.startswith("/") or ".." in rel.split("/") or ":" in rel:
            in_ra("Đường dẫn manifest không an toàn:", rel)
            return 2
        raw = (nguon / rel).read_bytes()
        if (_sha(raw), len(raw)) != (e["sha256"], e["bytes"]):
            in_ra("Tệp reference khác manifest:", rel)
            return 2
        if rel in pin and pin[rel] != e["sha256"]:
            in_ra("Manifest khác PIN của adapter:", rel)
            return 2
        dich_tep = dich / rel
        if dich_tep.exists() or dich_tep.is_symlink():
            if dich_tep.is_symlink() or not dich_tep.is_file() or dich_tep.read_bytes() != raw:
                in_ra("Tệp đích đã có nhưng khác bytes — dừng, không ghi đè:", rel)
                return 3
            giu += 1
            continue
        if chi_kiem:
            chua_nap.append(rel)
            in_ra("Chưa nạp:", rel)
            continue
        dich_tep.parent.mkdir(parents=True, exist_ok=True)
        with open(dich_tep, "xb") as f:  # CreateNew: đã có (đua) → FileExistsError, không ghi đè
            f.write(raw)
        if _sha(dich_tep.read_bytes()) != e["sha256"]:
            in_ra("Ghi xong nhưng hash khác:", rel)
            return 4
        tao += 1
    if chua_nap:
        in_ra(f"CHƯA ĐỦ: còn {len(chua_nap)}/{len(cac)} tệp chưa nạp tại {dich} — chạy lại không có --kiem.")
        return 1
    in_ra(f"Xong: tạo {tao}, đã có đúng {giu}, tổng {len(cac)} tệp tại {dich}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kiem", action="store_true", help="chỉ kiểm, không ghi")
    raise SystemExit(chay(ap.parse_args().kiem))
