"""M3-1b: ba đẳng thức hóa đơn ↔ cơ sở hợp đồng, chỉ đọc.

``tinh_ba_dang_thuc`` nhận snapshot đã ghim: cơ sở dạng dòng SQL; mỗi liên
kết có ``hoa_don`` chứa id/phien_ban_id/phien_ban/chieu/currency và ba khoản
Decimal tong_thanh_toan/khong_chiu_thue/net_chiu_thue. Không nhận float,
không tính lại khoản tiền từ dòng XML, VAT hay tổng khác.
Snapshot thuần có thể dùng phien_ban_id làm bản hiện hành; adapter SQL luôn
đọc eligible_content_id (kể cả NULL), co_ban_thay_the và native_fiscal_status
từ M2. Không tự chuyển liên kết đã ghim sang nội dung mới.

Căn cứ đủ đợt và policy thuế #7 là dữ liệu xác nhận từ tầng gọi tin cậy,
không phải cờ do trình duyệt gửi. Cả hai phải có id/revision/nguon/co_so_id/
trang_thai; căn cứ đủ đợt còn ghim lien_ket_ids của tập đang đối chiếu.
Schema M3-1a chưa lưu hai căn cứ này. Policy hình thức doanh thu không phải
policy thuế. Không có căn cứ thì giữ chờ, không tự chọn policy.

``M3K2`` nhận kết nối đã thiết lập danh tính/quyền RLS bởi tầng gọi, không
mở kết nối, ghi CSDL, commit hay thay đổi phiên. Một SELECT đọc một snapshot.
M2 hiện khóa tiền ở UNPROVEN_NO_MINOR và chưa promote bán ra: adapter giữ
các khoản tiền là None, tuyệt đối không suy từ raw_components/minor.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from typing import Iterable, Mapping


NHAN = (
    "Tổng thanh toán hóa đơn tiến độ bằng tổng thanh toán hợp đồng",
    "Phần không chịu thuế trên hóa đơn bằng giá đất được trừ của hợp đồng",
    "Phần trước thuế chịu thuế trên hóa đơn bằng phần chịu thuế của hợp đồng",
)
TRANG_THAI = {"KHOP": "Khớp", "LECH": "Lệch", "PENDING": "Chờ đủ căn cứ",
              "CHUA_DU_DOT": "Chưa đủ đợt"}


@dataclass(frozen=True)
class Nguon:
    loai: str
    id: str | None
    phien_ban: str | int | None
    revision: int | None
    ten: str | None
    vi_tri: str | None = None
    duoc_tinh: bool | None = None

    def ra_man_hinh(self) -> dict:
        """Nhãn nghiệp vụ, không đưa khóa kỹ thuật lên màn hình."""
        return {"loai": self.loai, "ten": self.ten or "Chưa có nguồn xác nhận",
                "phien_ban": (f"Phiên bản {self.phien_ban}" if self.phien_ban is not None
                              else "Chưa rõ phiên bản"),
                "lan_xac_nhan": f"Lần {self.revision}" if self.revision is not None else None,
                "vi_tri": self.vi_tri,
                "su_dung": ("Đã tính" if self.duoc_tinh else "Chưa tính")
                if self.duoc_tinh is not None else None}


def _tien(v: Decimal | None, currency: str | None) -> str:
    if v is None:
        return "Chưa đủ dữ liệu"
    # format f không làm tròn theo context, khác với phép toán Decimal.
    whole, dot, fraction = format(v, "f").partition(".")
    sign = "−" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    grouped = ".".join(reversed([whole[max(0, i - 3):i] for i in range(len(whole), 0, -3)]))
    return f"{sign}{grouped}{',' + fraction if dot else ''} {currency or '(chưa rõ đơn vị tiền)'}"


@dataclass(frozen=True)
class DangThuc:
    so: int
    ve_trai: Decimal | None
    ve_phai: Decimal | None
    chenh: Decimal | None
    currency: str | None
    trang_thai: str
    ly_do: tuple[str, ...]
    nguon: tuple[Nguon, ...]

    def ra_man_hinh(self) -> dict:
        return {"noi_dung": NHAN[self.so - 1], "trang_thai": TRANG_THAI[self.trang_thai],
                "ve_trai": _tien(self.ve_trai, self.currency),
                "ve_phai": _tien(self.ve_phai, self.currency),
                "chenh": _tien(self.chenh, self.currency), "ly_do": list(self.ly_do),
                "nguon": [n.ra_man_hinh() for n in self.nguon]}


def _so(value) -> Decimal | None:
    return value if isinstance(value, Decimal) and value.is_finite() else None


def _tong_exact(values: list[Decimal]) -> Decimal:
    """Không để precision mặc định 28 làm mất chênh nhỏ khi số rất lớn."""
    low = min(v.as_tuple().exponent for v in values)
    high = max(v.adjusted() for v in values)
    with localcontext() as ctx:
        ctx.prec = max(1, high - low + len(str(len(values))) + 3)
        return sum(values, Decimal(0))


def _id(v) -> str | None:
    return str(v) if v is not None else None


def _nguon(loai, row, *, phien_ban=None, duoc_tinh=None) -> Nguon:
    return Nguon(loai, _id(row.get("id")), phien_ban, row.get("revision"),
                 row.get("nguon"), row.get("nguon_vi_tri"), duoc_tinh)


def _can_cu(row, co_so) -> bool:
    return bool(row and row.get("trang_thai") == "DA_XAC_NHAN"
                and row.get("id") and isinstance(row.get("nguon"), str) and row["nguon"].strip()
                and type(row.get("revision")) is int and row["revision"] >= 1
                and co_so.get("id") and _id(row.get("co_so_id")) == _id(co_so.get("id")))


def tinh_ba_dang_thuc(
    co_so: Mapping | None,
    lien_ket: Iterable[Mapping],
    *,
    can_cu_du_dot: Mapping | None = None,
    policy_thue: Mapping | None = None,
) -> tuple[DangThuc, ...]:
    """Chênh = trái − phải; PENDING ưu tiên khi thiếu căn cứ, không bù thiếu.

    Chỉ tổng hợp liên kết DA_XAC_NHAN, cùng cơ sở/pháp nhân và hóa đơn bán
    ghim đúng phiên bản/quan sát. Đầu vào là các revision mapping hiện hành;
    adapter SQL lọc revision trước khi lọc cơ sở (mapping có thể chuyển cơ sở).
    """
    c = co_so or {}
    links = list(lien_ket)
    reasons = []
    sources = [_nguon("Hợp đồng", c, phien_ban=c.get("hop_dong_phien_ban"))]
    if c.get("trang_thai") != "DA_XAC_NHAN" or c.get("crm_trang_thai") != "DA_DUYET":
        reasons.append("Chưa có cơ sở hợp đồng đã xác nhận và phiên bản hợp đồng đã duyệt.")
    if not all(c.get(k) for k in ("id", "revision", "phap_nhan_id", "hop_dong_id",
                                  "hop_dong_phien_ban_id", "pham_vi", "nguon")):
        reasons.append("Chưa đủ nguồn, phiên bản và phạm vi cơ sở hợp đồng để đối chiếu.")
    currency = c.get("currency")
    valid_currency = isinstance(currency, str) and len(currency) == 3 and currency.isascii() and currency.isupper() and currency.isalpha()
    if not valid_currency:
        reasons.append("Chưa xác định được đơn vị tiền của cơ sở hợp đồng.")
        currency = None
    invoices = []
    seen = set()
    mixed = False
    for link in links:
        confirmed = link.get("trang_thai") == "DA_XAC_NHAN"
        hd = link.get("hoa_don") or {}
        usable = confirmed
        if not confirmed:
            reasons.append("Liên kết hóa đơn còn là ứng viên, chưa được xác nhận để tính.")
        if (_id(link.get("co_so_id")) != _id(c.get("id"))
                or _id(link.get("phap_nhan_id")) != _id(c.get("phap_nhan_id"))):
            usable = False
            reasons.append("Liên kết chưa khớp pháp nhân hoặc cơ sở hợp đồng.")
        if confirmed and not hd:
            usable = False
            reasons.append("Không xem được hóa đơn đã liên kết để đối chiếu.")
        # M3-1c — CD-013: NULL eligible cũng không còn là bản đủ điều kiện.
        if confirmed and hd and (
                _id(hd.get("eligible_content_id", hd.get("phien_ban_id")))
                != _id(link.get("hoa_don_phien_ban_id"))
                or hd.get("co_ban_thay_the")
                or hd.get("native_fiscal_status") in ("CANCELLED", "HUY", "DA_HUY")):
            usable = False
            reasons.append("Hóa đơn đã được thay thế/điều chỉnh, cần xác nhận lại liên kết.")
        if confirmed and (not all(link.get(k) for k in ("id", "revision", "nguon", "can_cu",
                                                         "hoa_don_id", "hoa_don_phien_ban_id", "hoa_don_quan_sat_id"))
                          or hd.get("chieu") != "BAN_RA"
                          or _id(hd.get("id")) != _id(link.get("hoa_don_id"))
                          or _id(hd.get("phien_ban_id")) != _id(link.get("hoa_don_phien_ban_id"))
                          or hd.get("phien_ban") is None):
            usable = False
            reasons.append("Chưa đủ hóa đơn bán, phiên bản, quan sát và căn cứ liên kết.")
        invoice_currency = hd.get("currency")
        valid_invoice_currency = (isinstance(invoice_currency, str) and len(invoice_currency) == 3
                                  and invoice_currency.isascii() and invoice_currency.isupper()
                                  and invoice_currency.isalpha())
        if confirmed and hd and not valid_invoice_currency:
            usable = False
            reasons.append("Chưa xác định được đơn vị tiền của hóa đơn.")
        if confirmed and currency and valid_invoice_currency and invoice_currency != currency:
            mixed = True
            reasons.append("Hóa đơn và hợp đồng có đồng tiền khác nhau, chưa thể cộng để đối chiếu.")
        if usable and _id(hd.get("id")) in seen:
            usable = False
            reasons.append("Hóa đơn xuất hiện nhiều lần trong tập liên kết, chỉ được tính một lần.")
        if usable:
            seen.add(_id(hd.get("id")))
            invoices.append(hd)
        sources.append(_nguon("Liên kết hóa đơn", link, duoc_tinh=usable and not mixed))
        if hd:
            sources.append(Nguon("Hóa đơn", _id(hd.get("phien_ban_id")), hd.get("phien_ban"),
                                 None, hd.get("nguon") or link.get("nguon"),
                                 hd.get("nguon_vi_tri"), usable and not mixed))
    if not invoices:
        reasons.append("Chưa có hóa đơn đủ căn cứ với liên kết đã xác nhận để tính số lũy kế.")
    if mixed:
        sources = [replace(s, duoc_tinh=False) if s.duoc_tinh is not None else s for s in sources]
    fields = (("tong_thanh_toan", "tong_thanh_toan", "tổng thanh toán", "tổng thanh toán"),
              ("khong_chiu_thue", "tong_gia_dat_duoc_tru", "phần không chịu thuế", "giá đất được trừ"),
              ("net_chiu_thue", "phan_chiu_thue", "phần trước thuế chịu thuế", "phần chịu thuế"))
    expected_links = {_id(l.get("id")) for l in links if l.get("trang_thai") == "DA_XAC_NHAN"}
    full = (_can_cu(can_cu_du_dot, c)
            and isinstance(can_cu_du_dot.get("lien_ket_ids"), (list, tuple, set, frozenset))
            and {_id(v) for v in can_cu_du_dot["lien_ket_ids"]} == expected_links)
    results = []
    for i, (left_field, right_field, left_label, right_label) in enumerate(fields, 1):
        why = list(reasons)
        provenance = list(sources)
        amounts = [_so(h.get(left_field)) for h in invoices]
        left = _tong_exact(amounts) if amounts and None not in amounts and not mixed and currency else None
        right = _so(c.get(right_field))
        if left is None:
            why.append(f"Chưa đủ căn cứ để đối chiếu {left_label} trên hóa đơn; số thiếu không được thay bằng 0.")
            provenance = [replace(s, duoc_tinh=False) if s.duoc_tinh is not None else s for s in provenance]
        if right is None:
            why.append(f"Chưa có {right_label} của cơ sở hợp đồng để đối chiếu.")
        if i in (2, 3):
            if not _can_cu(policy_thue, c):
                why.append("Chưa có xác nhận cơ sở thuế của bộ phận thuế.")
            if policy_thue:
                provenance.append(_nguon("Căn cứ cơ sở thuế", policy_thue))
        elif can_cu_du_dot:
            provenance.append(_nguon("Căn cứ đã xuất đủ đợt", can_cu_du_dot))
        diff = _tong_exact([left, right.copy_negate()]) if left is not None and right is not None and currency else None
        status = "PENDING" if why else ("KHOP" if diff == 0 else "LECH")
        if i == 1 and not full:
            why.append("Chưa có xác nhận đã xuất đủ đợt cho cơ sở và tập hóa đơn đang đối chiếu.")
            if status != "PENDING":
                status = "CHUA_DU_DOT"
        results.append(DangThuc(i, left, right, diff, currency, status,
                               tuple(dict.fromkeys(why)), tuple(provenance)))
    return tuple(results)


class M3K2:
    """Reader trên kết nối đã được giới hạn quyền M3; không nhận actor từ UI."""

    def __init__(self, conn):
        self.conn = conn

    def ba_dang_thuc(self, phap_nhan_id, hop_dong_id, hop_dong_phien_ban_id, *,
                     pham_vi: str, revision: int | None = None,
                     can_cu_du_dot: Mapping | None = None,
                     policy_thue: Mapping | None = None) -> tuple[DangThuc, ...]:
        """Chọn revision mới nhất kể cả PENDING, hoặc ghim revision chỉ định.

        Chưa thể trả KHOP với schema M2 hiện hành: bán ra chưa promote, tiền
        chưa chứng minh. Không đọc policy hình thức doanh thu thay policy #7.
        """
        cur = self.conn.execute("""
            WITH co_so AS (
                SELECT c.*, p.phien_ban AS hop_dong_phien_ban, p.trang_thai AS crm_trang_thai
                FROM m3.hop_dong_co_so c
                JOIN master.hop_dong_phien_ban p
                  ON p.id = c.hop_dong_phien_ban_id AND p.hop_dong_id = c.hop_dong_id
                WHERE c.phap_nhan_id = %s AND c.hop_dong_id = %s
                  AND c.hop_dong_phien_ban_id = %s AND c.pham_vi = %s
                  AND (%s::integer IS NULL OR c.revision = %s::integer)
                ORDER BY c.revision DESC LIMIT 1
            )
            SELECT c.*, l.id AS lien_ket_id, l.revision AS lien_ket_revision,
                   l.trang_thai AS lien_ket_trang_thai, l.nguon AS lien_ket_nguon,
                   l.nguon_ref, l.nguon_vi_tri AS lien_ket_vi_tri, l.can_cu,
                   l.hoa_don_id, l.hoa_don_phien_ban_id, l.hoa_don_quan_sat_id,
                   d.chieu, v.phien_ban AS hoa_don_phien_ban, v.tien_te,
                   v.money_basis_state, d.eligible_content_id,
                   latest.native_fiscal_status,
                   EXISTS (
                       SELECT 1 FROM kho.hoa_don_phien_ban successor
                       WHERE successor.phap_nhan_id = c.phap_nhan_id
                         AND successor.hoa_don_id = l.hoa_don_id
                         AND successor.supersedes_id = l.hoa_don_phien_ban_id
                   ) AS co_ban_thay_the
            FROM co_so c
            LEFT JOIN m3.hoa_don_hop_dong l ON l.co_so_id = c.id
              AND l.phap_nhan_id = c.phap_nhan_id
              AND NOT EXISTS (
                SELECT 1 FROM m3.hoa_don_hop_dong newer
                WHERE newer.khoa_lien_ket = l.khoa_lien_ket
                  AND newer.phap_nhan_id = l.phap_nhan_id AND newer.revision > l.revision)
            LEFT JOIN kho.hoa_don_phien_ban v ON v.id = l.hoa_don_phien_ban_id
              AND v.hoa_don_id = l.hoa_don_id AND v.phap_nhan_id = c.phap_nhan_id
            LEFT JOIN kho.hoa_don_danh_tinh d ON d.id = v.hoa_don_id
              AND d.phap_nhan_id = c.phap_nhan_id
            LEFT JOIN kho.hoa_don_quan_sat latest ON latest.id = d.latest_observation_id
              AND latest.hoa_don_id = d.id AND latest.phap_nhan_id = c.phap_nhan_id
            ORDER BY l.id
            """, (phap_nhan_id, hop_dong_id, hop_dong_phien_ban_id, pham_vi, revision, revision))
        names = [col.name for col in cur.description]
        rows = [dict(r) if isinstance(r, Mapping) else dict(zip(names, r)) for r in cur.fetchall()]
        c = rows[0] if rows else None
        links = []
        for r in rows:
            if r["lien_ket_id"] is None:
                continue
            hd = None
            if r["hoa_don_phien_ban"] is not None and r["chieu"] is not None:
                hd = {"id": r["hoa_don_id"], "phien_ban_id": r["hoa_don_phien_ban_id"],
                      "phien_ban": r["hoa_don_phien_ban"], "chieu": r["chieu"],
                      "currency": r["tien_te"], "nguon": r["lien_ket_nguon"],
                      "eligible_content_id": r["eligible_content_id"],
                      "co_ban_thay_the": r["co_ban_thay_the"],
                      "native_fiscal_status": r["native_fiscal_status"],
                      "tong_thanh_toan": None, "khong_chiu_thue": None, "net_chiu_thue": None}
            links.append({"id": r["lien_ket_id"], "revision": r["lien_ket_revision"],
                          "co_so_id": r["id"], "phap_nhan_id": r["phap_nhan_id"],
                          "trang_thai": r["lien_ket_trang_thai"], "nguon": r["lien_ket_nguon"],
                          "nguon_vi_tri": r["lien_ket_vi_tri"], "can_cu": r["can_cu"],
                          **{k: r[k] for k in ("hoa_don_id", "hoa_don_phien_ban_id", "hoa_don_quan_sat_id")},
                          "hoa_don": hd})
        return tinh_ba_dang_thuc(c, links, can_cu_du_dot=can_cu_du_dot, policy_thue=policy_thue)
