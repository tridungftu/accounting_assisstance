"""M2-00B — cấu hình typed, bất biến cho bộ tải #7 sở hữu riêng. CHỈ máy chủ ứng dụng tin cậy dựng (wiring `[tai_hoa_don]` ở gói sau).

Không đọc credential/.env/profile, không tự dò đường dẫn, không nhận binary/host/port/thư mục/argv từ trình duyệt. Mọi đường dẫn phải tuyệt đối,
không UNC, mọi thành phần đã tồn tại không là symlink/junction (reparse), các gốc dữ liệu tách biệt nhau. Hash file chỉ kiểm HÌNH DẠNG ở đây;
`tien_trinh` băm lại bytes thật ngay trước khi spawn.
"""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path

from ...ha_tang.primitives import DataError

RE_HEX64 = re.compile(r"[0-9a-f]{64}")
RE_PHIEN_BAN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
RE_TEP_REL = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,79}(?:/[A-Za-z0-9_][A-Za-z0-9_.-]{0,79}){0,3}")
TEP_BAT_BUOC = ("src/server.js", "src/job.js", "src/manifest.js", "src/portal.js", "config.js")
_REPARSE = 0x400  # FILE_ATTRIBUTE_REPARSE_POINT


def _loi(ma: str, thong_bao: str):
    raise DataError(ma, thong_bao)


def kiem_khong_reparse(p: Path, *, la_thu_muc: bool | None = None) -> Path:
    """Tuyệt đối, không UNC, đã tồn tại; từng thành phần (kể cả gốc ổ) không phải symlink/junction; realpath trùng đường dẫn."""
    s = str(p)
    if not isinstance(p, Path) or not p.is_absolute() or s.startswith(("\\\\", "//")):
        _loi("M2_00B_DUONG_DAN", "Đường dẫn cấu hình phải tuyệt đối, cục bộ (không UNC).")
    cur = Path(p.anchor)
    for part in p.parts[1:]:
        cur = cur / part
        try:
            st = os.lstat(cur)
        except OSError:
            _loi("M2_00B_DUONG_DAN", "Đường dẫn cấu hình chưa tồn tại.")
        if stat.S_ISLNK(st.st_mode) or (getattr(st, "st_file_attributes", 0) & _REPARSE):
            _loi("M2_00B_DUONG_DAN_REPARSE", "Đường dẫn cấu hình đi qua symlink/junction.")
    if os.path.normcase(os.path.realpath(p)) != os.path.normcase(str(p)):
        _loi("M2_00B_DUONG_DAN_REPARSE", "Đường dẫn cấu hình không trùng realpath.")
    if la_thu_muc is True and not p.is_dir():
        _loi("M2_00B_DUONG_DAN", "Gốc cấu hình phải là thư mục.")
    if la_thu_muc is False and not p.is_file():
        _loi("M2_00B_DUONG_DAN", "Tệp cấu hình phải là tệp thường.")
    return p


@dataclass(frozen=True)
class GioiHan:
    """Giới hạn hữu hạn (giây/byte/số lượng). Bên Node nhận bản ánh xạ ms/byte tương ứng trong cấu hình stdin."""
    body_bytes: int = 64 * 1024
    phan_hoi_bytes: int = 4 * 1024 * 1024
    dong_sse_bytes: int = 64 * 1024
    su_kien_moi_job: int = 5000
    su_kien_payload_bytes: int = 4096
    khoi_dong_s: float = 30.0
    dung_s: float = 20.0
    cho_job_s: float = 10.0
    rpc_s: float = 15.0
    sse_doc_s: float = 30.0
    sse_nhip_s: float = 10.0
    sse_toi_da_s: float = 1800.0
    hang_doi_toi_da: int = 50
    cho_moi_job_s: float = 3 * 3600.0
    nhip_poll_s: float = 2.0

    def __post_init__(self):
        so_nguyen = {"body_bytes": (1024, 1024 * 1024), "phan_hoi_bytes": (4096, 64 * 1024 * 1024), "dong_sse_bytes": (1024, 1024 * 1024),
                     "su_kien_moi_job": (10, 20000), "su_kien_payload_bytes": (256, 64 * 1024), "hang_doi_toi_da": (1, 500)}
        for k, (lo, hi) in so_nguyen.items():
            v = getattr(self, k)
            if type(v) is not int or not lo <= v <= hi:
                _loi("M2_00B_GIOI_HAN", f"Giới hạn {k} ngoài miền cho phép.")
        so_thuc = {"khoi_dong_s": (0.1, 600), "dung_s": (0.1, 300), "cho_job_s": (0.1, 120), "rpc_s": (0.1, 120), "sse_doc_s": (0.1, 300),
                   "sse_nhip_s": (0.1, 60), "sse_toi_da_s": (1, 6 * 3600), "cho_moi_job_s": (1, 24 * 3600), "nhip_poll_s": (0.0, 60)}
        for k, (lo, hi) in so_thuc.items():
            v = getattr(self, k)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
                _loi("M2_00B_GIOI_HAN", f"Giới hạn {k} ngoài miền cho phép.")
        if self.sse_nhip_s >= self.sse_doc_s:
            _loi("M2_00B_GIOI_HAN", "Nhịp heartbeat SSE phải nhỏ hơn hạn đọc SSE.")

    def cho_node(self) -> dict:
        return {"body_bytes": self.body_bytes, "event_payload_bytes": self.su_kien_payload_bytes, "events_per_job": self.su_kien_moi_job,
                "sse_heartbeat_ms": int(self.sse_nhip_s * 1000), "sse_max_ms": int(self.sse_toi_da_s * 1000),
                "stop_grace_ms": max(100, int(self.dung_s * 1000 * 0.75)), "profiles_max": 64}


@dataclass(frozen=True)
class TepPin:
    rel: str
    sha256: str

    def __post_init__(self):
        if not isinstance(self.rel, str) or not RE_TEP_REL.fullmatch(self.rel) or ".." in self.rel:
            _loi("M2_00B_TEP_PIN", "Tệp pin phải là đường dẫn tương đối an toàn trong gốc #7.")
        if not isinstance(self.sha256, str) or not RE_HEX64.fullmatch(self.sha256):
            _loi("M2_00B_TEP_PIN", "SHA-256 tệp pin phải là 64 ký tự hex thường.")


@dataclass(frozen=True)
class CauHinhTaiHoaDon:
    """Cấu hình duy nhất do máy chủ ứng dụng tin cậy cấp.

    node_exe/node_sha256: Node executable ghim; goc_7 + tep_pin: bộ #7 đã materialize (server/job/manifest/portal/config) với hash ghim;
    phien_ban_bo_tai: PRODUCER_VERSION kỳ vọng trong bắt tay; goc_tai/goc_trinh_duyet/goc_profile: gốc A đã duyệt; goc_dieu_phoi: nơi ghi
    binding điều phối bất biến (write_immutable); cong: 0 (OS cấp) hoặc cổng cấu hình ≥1024.
    """
    node_exe: Path
    node_sha256: str
    goc_7: Path
    tep_pin: tuple
    phien_ban_bo_tai: str
    goc_tai: Path
    goc_trinh_duyet: Path
    goc_profile: Path
    goc_dieu_phoi: Path
    cong: int = 0
    gioi_han: GioiHan = field(default_factory=GioiHan)

    def __post_init__(self):
        for k in ("node_exe", "goc_7", "goc_tai", "goc_trinh_duyet", "goc_profile", "goc_dieu_phoi"):
            if not isinstance(getattr(self, k), Path):
                _loi("M2_00B_CAU_HINH", f"{k} phải là pathlib.Path do máy chủ cấp.")
        if not isinstance(self.node_sha256, str) or not RE_HEX64.fullmatch(self.node_sha256):
            _loi("M2_00B_CAU_HINH", "node_sha256 phải là 64 ký tự hex thường.")
        if not isinstance(self.phien_ban_bo_tai, str) or not RE_PHIEN_BAN.fullmatch(self.phien_ban_bo_tai):
            _loi("M2_00B_CAU_HINH", "Phiên bản bộ tải kỳ vọng không hợp lệ.")
        if type(self.cong) is not int or not (self.cong == 0 or 1024 <= self.cong <= 65535):
            _loi("M2_00B_CAU_HINH", "Cổng phải là 0 hoặc 1024–65535.")
        if not isinstance(self.gioi_han, GioiHan):
            _loi("M2_00B_CAU_HINH", "gioi_han phải là GioiHan.")
        if not isinstance(self.tep_pin, tuple) or not all(isinstance(t, TepPin) for t in self.tep_pin):
            _loi("M2_00B_CAU_HINH", "tep_pin phải là tuple TepPin.")
        rels = [t.rel for t in self.tep_pin]
        if len(set(rels)) != len(rels) or not set(TEP_BAT_BUOC) <= set(rels):
            _loi("M2_00B_CAU_HINH", "tep_pin phải ghim đủ server/job/manifest/portal/config, không lặp.")
        kiem_khong_reparse(self.node_exe, la_thu_muc=False)
        kiem_khong_reparse(self.goc_7, la_thu_muc=True)
        for t in self.tep_pin:
            kiem_khong_reparse(self.goc_7.joinpath(*t.rel.split("/")), la_thu_muc=False)
        goc = [self.goc_tai, self.goc_trinh_duyet, self.goc_profile, self.goc_dieu_phoi]
        for g in goc:
            kiem_khong_reparse(g, la_thu_muc=True)
        chuan = [os.path.normcase(str(g)) for g in goc + [self.goc_7]]
        for i, a in enumerate(chuan):
            for j, b in enumerate(chuan):
                if i != j and (a == b or a.startswith(b.rstrip("\\/") + os.sep)):
                    _loi("M2_00B_GOC_CHONG", "Các gốc tải/trình duyệt/profile/điều phối/#7 phải tách biệt, không lồng nhau.")

    @property
    def server_js(self) -> Path:
        return self.goc_7 / "src" / "server.js"

    def roots_node(self) -> dict:
        return {"downloadRoot": str(self.goc_tai), "browserProfileRoot": str(self.goc_trinh_duyet), "profilesDir": str(self.goc_profile)}

    def __repr__(self):  # không in đường dẫn chi tiết vào log
        return f"CauHinhTaiHoaDon(phien_ban_bo_tai={self.phien_ban_bo_tai!r}, cong={self.cong})"
