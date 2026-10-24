"""Nhận diện đối tượng theo TÊN (V11).

Danh mục đối tượng Junsky ghi tên đầy đủ ("CONG TY CO PHAN ..."), ngân hàng ghi
viết tắt ("CT CP ...", "CTCP ...") hoặc chỉ ghi tên trong diễn giải.  Mô-đun này
đưa hai phía về một cách viết, tách phần "định danh" (bỏ loại hình doanh
nghiệp) rồi so khớp theo ba mức, từ mạnh đến yếu:

1. ``exact``        – tên trùng hẳn sau chuẩn hóa và ứng với đúng một mã.
2. ``fuzzy``        – phần định danh trùng đủ nhiều (một bên chứa bên kia hoặc
                      đa số từ trùng); kết quả là danh sách để người duyệt chọn.
3. ``in_description`` – không có cột tên: tìm tên danh mục nằm trong diễn giải.

Mô-đun thuần Python, không gọi dịch vụ ngoài; AI cục bộ (nếu bật) chỉ được
hỏi khi mức 2–3 trả về nhiều ứng viên.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

from ..ha_tang.primitives import normalize_text

# Cụm dài trước, cụm ngắn sau; so sau khi đã bỏ dấu và viết hoa.
ABBREVIATIONS: tuple[tuple[str, str], ...] = (
    ("TRACH NHIEM HUU HAN MOT THANH VIEN", "TNHH MTV"),
    ("TRACH NHIEM HUU HAN", "TNHH"),
    ("MOT THANH VIEN", "MTV"),
    ("DOANH NGHIEP TU NHAN", "DNTN"),
    ("HOP TAC XA", "HTX"),
    ("CONG TY CO PHAN", "CTY CP"),
    ("CONG TY", "CTY"),
    ("CO PHAN", "CP"),
    ("XUAT NHAP KHAU", "XNK"),
    ("THUONG MAI", "TM"),
    ("DICH VU", "DV"),
    ("XAY DUNG", "XD"),
    ("SAN XUAT", "SX"),
    ("DAU TU", "DT"),
    ("PHAT TRIEN", "PT"),
    ("VIET NAM", "VN"),
    ("NGAN HANG", "NH"),
    ("CHI NHANH", "CN"),
    ("KY THUAT", "KT"),
)
# Viết tắt riêng của ngân hàng → dạng chuẩn trong danh mục.
_BANK_SHORTHAND: tuple[tuple[str, str], ...] = (
    (r"\bCTCP\b", "CTY CP"),
    (r"\bCT CP\b", "CTY CP"),
    (r"\bCT TNHH\b", "CTY TNHH"),
    (r"\bCTY TNHH 1TV\b", "CTY TNHH MTV"),
    (r"\bTNHH 1TV\b", "TNHH MTV"),
    (r"\bC TY\b", "CTY"),
    (r"\bCONGTY\b", "CTY"),
    (r"^CT\b", "CTY"),
)
# Từ chỉ loại hình/đơn vị, không dùng để phân biệt hai công ty.
LEGAL_FORM_TOKENS = frozenset({
    "CTY", "CP", "TNHH", "MTV", "DNTN", "HTX", "CN", "DV", "TM", "XD", "XNK", "SX", "VN", "DT", "PT", "KT", "NH",
    "VA", "CO", "CONG", "TY", "DN", "TNHHMTV", "GROUP", "CORP", "CORPORATION", "COMPANY", "LTD", "JSC", "CO", "INC",
})
# Từ của câu diễn giải (không phải tên riêng): không được là từ hiếm quyết định.
NARRATIVE_TOKENS = frozenset({
    "THANH", "TOAN", "TIEN", "CHUYEN", "TT", "CK", "TRA", "NOP", "THU", "CHI", "PHI", "HOAN", "TAM", "UNG", "HD", "HOA", "DON",
    "SO", "NGAY", "THANG", "LUONG", "THUONG", "MUA", "BAN", "HANG", "DICH", "VU", "DOT", "LAN", "KY", "NAM", "QUY", "NOI", "BO",
})
# Từ nối trong diễn giải ngân hàng: phần tên thường đứng trước các từ này.
DESCRIPTION_CONNECTORS = frozenset({
    "THANH", "TT", "CHUYEN", "CK", "TRA", "NOP", "THU", "CHI", "HOAN", "TAM", "GUI", "TTOAN", "UNC", "TTIEN", "THANHTOAN", "CHUYENTIEN",
})


@lru_cache(maxsize=65536)
def canonical_name(value: str) -> str:
    """Bỏ dấu, viết hoa, bỏ ký tự lạ, đưa viết tắt về một dạng."""
    text = normalize_text(str(value or ""))
    text = re.sub(r"[^A-Z0-9 ]", " ", text)
    text = " ".join(text.split())
    for pattern, replacement in _BANK_SHORTHAND:
        text = re.sub(pattern, replacement, text)
    for long, short in ABBREVIATIONS:
        text = re.sub(r"\b" + long + r"\b", short, text)
    return " ".join(text.split())


@lru_cache(maxsize=65536)
def distinctive_tokens(value: str) -> tuple:
    """Các từ phân biệt của một tên, theo thứ tự, không lặp."""
    seen, result = set(), []
    for token in canonical_name(value).split():
        if token in LEGAL_FORM_TOKENS or len(token) < 2:
            continue
        if token not in seen:
            seen.add(token); result.append(token)
    return tuple(result)


def names_compatible(left: object, right: object) -> bool:
    """Hai tên có thể cùng chỉ một đơn vị không (dùng để chặn ánh xạ STK sai)."""
    a, b = set(distinctive_tokens(str(left or ""))), set(distinctive_tokens(str(right or "")))
    if not a or not b:
        return True  # không có gì để so → không kết luận mâu thuẫn
    shared = len(a & b)
    smallest = min(len(a), len(b))
    return shared / smallest >= 0.5 or a <= b or b <= a


class NameIndex:
    """Chỉ mục tên danh mục đối tượng cho một lần đề xuất."""

    def __init__(self, entries: Iterable[tuple[str, str]]):
        self.exact_map: dict[str, set[str]] = {}
        self.tokens: dict[str, tuple] = {}
        self.names: dict[str, str] = {}
        self.by_token: dict[str, set[str]] = {}
        self.df: dict[str, int] = {}
        for code, name in entries:
            code, name = str(code or ""), str(name or "")
            if not code or not name:
                continue
            canon = canonical_name(name)
            self.exact_map.setdefault(canon, set()).add(code)
            # "Công ty cổ phần Nước sạch Hà Nam (Hanvico)": the bracketed trade
            # name is optional on a bank statement.  Two codes sharing the short
            # form stay ambiguous (exact() then lists both).
            if "(" in name:
                short = canonical_name(re.sub(r"\([^)]*\)", " ", name))
                if short and short != canon:
                    self.exact_map.setdefault(short, set()).add(code)
            tokens = distinctive_tokens(name)
            self.tokens[code] = tokens
            self.names[code] = name
            for token in tokens:
                self.by_token.setdefault(token, set()).add(code)
                self.df[token] = self.df.get(token, 0) + 1
        # A token is "rare" when few catalog names carry it; "HA", "NAM" or
        # "VIET" alone never identify anyone.
        self.rare_limit = max(3, len(self.names) // 100)

    def is_rare(self, token: str) -> bool:
        return self.df.get(token, 0) <= self.rare_limit

    def affinity(self, name: object, code: str) -> float:
        """0..1: how well a statement name fits one catalog code."""
        query, own = set(distinctive_tokens(str(name or ""))), set(self.tokens.get(code, ()))
        if not query or not own:
            return 0.0
        shared = len(query & own)
        if not shared:
            return 0.0
        score = shared / max(len(query), len(own))
        if (query <= own or own <= query) and min(len(query), len(own)) >= 2:
            score = max(score, 0.8)
        return round(score, 3)

    def exact(self, name: object) -> list[str]:
        canon = canonical_name(str(name or ""))
        return sorted(self.exact_map.get(canon, set())) if canon else []

    def fuzzy(self, name: object, limit: int = 5) -> list[dict]:
        """Ứng viên theo phần định danh; điểm = tỷ lệ từ trùng trên tên dài hơn."""
        query = set(distinctive_tokens(str(name or "")))
        if not query:
            return []
        codes: set[str] = set()
        for token in query:
            codes |= self.by_token.get(token, set())
        scored = []
        for code in codes:
            own = set(self.tokens.get(code, ()))
            if not own:
                continue
            shared = len(query & own)
            if not shared:
                continue
            score = shared / max(len(query), len(own))
            contained = (query <= own or own <= query) and min(len(query), len(own)) >= 2
            if score >= 0.6 or contained:
                scored.append({"code": code, "name": self.names[code], "score": round(max(score, 0.6 if contained else score), 3), "shared": shared})
        scored.sort(key=lambda item: (-item["score"], -item["shared"], item["code"]))
        return scored[:limit]

    def in_description(self, description: object, limit: int = 5) -> list[dict]:
        """Tìm tên danh mục nằm trong diễn giải (khi sao kê không có cột tên)."""
        words = canonical_name(str(description or "")).split()
        if not words:
            return []
        positions: dict[str, list[int]] = {}
        for index, word in enumerate(words):
            positions.setdefault(word, []).append(index)
        candidates: set[str] = set()
        for word in positions:
            candidates |= self.by_token.get(word, set())
        found = []
        for code in candidates:
            tokens = self.tokens.get(code, ())
            if not tokens or any(token not in positions for token in tokens):
                continue
            # Một từ phân biệt duy nhất chỉ đủ khi là từ dài, ít gặp; tên hai
            # từ phải có ít nhất một từ hiếm (tránh "HA NAM", "VIET NAM").
            if len(tokens) == 1 and (len(tokens[0]) < 6 or len(self.by_token.get(tokens[0], ())) > 1):
                continue
            if not any(self.is_rare(token) and token not in NARRATIVE_TOKENS for token in tokens):
                continue
            # Các từ phải xuất hiện theo đúng thứ tự, gói trong một cửa sổ ngắn
            # (chọn vị trí sớm nhất còn giữ được thứ tự, vì một từ như "DUNG"
            # có thể lặp lại ở chỗ khác trong diễn giải).
            first, previous = None, -1
            for token in tokens:
                position = next((index for index in positions[token] if index > previous), None)
                if position is None:
                    break
                if first is None:
                    first = position
                previous = position
            else:
                if previous - first <= len(tokens) + 4:
                    found.append({"code": code, "name": self.names[code], "score": 1.0, "shared": len(tokens), "start": first})
        # Tên nhiều từ hơn (cụ thể hơn) đứng trước; tên đứng đầu diễn giải trước.
        found.sort(key=lambda item: (-item["shared"], item["start"], item["code"]))
        return found[:limit]

    def description_prefix(self, description: object) -> str:
        """Đoạn đầu diễn giải trước từ nối (thanh toan / TT / chuyen …)."""
        words = canonical_name(str(description or "")).split()
        prefix = []
        for word in words:
            if word in DESCRIPTION_CONNECTORS and len(prefix) >= 2:
                break
            if word.isdigit() or sum(ch.isdigit() for ch in word) >= 3:
                if prefix:
                    break
                continue
            prefix.append(word)
            if len(prefix) >= 12:
                break
        return " ".join(prefix)


def identify_by_name(index: NameIndex, counterparty_name: object, description: object) -> dict:
    """Kết quả nhận diện theo tên cho một dòng sao kê.

    Trả về ``{"code", "level", "options", "basis"}``; ``code`` rỗng khi không
    duy nhất.  Mức: CATALOG_NAME (trùng hẳn), CATALOG_NAME_FUZZY (gần giống),
    CATALOG_NAME_DESC (tên tìm thấy trong diễn giải).
    """
    name = str(counterparty_name or "").strip()
    if name:
        exact = index.exact(name)
        if len(exact) == 1:
            return {"code": exact[0], "level": "CATALOG_NAME", "options": [{"code": exact[0], "name": index.names[exact[0]], "score": 1.0}], "basis": "NAME_EXACT"}
        if len(exact) > 1:
            return {"code": "", "level": "CATALOG_NAME_FUZZY", "options": [{"code": code, "name": index.names[code], "score": 1.0} for code in exact], "basis": "NAME_EXACT_MANY"}
        fuzzy = index.fuzzy(name)
        if fuzzy:
            top = fuzzy[0]
            unique = len(fuzzy) == 1 or top["score"] - fuzzy[1]["score"] >= 0.2
            return {"code": top["code"] if unique else "", "level": "CATALOG_NAME_FUZZY", "options": fuzzy, "basis": "NAME_FUZZY"}
        return {"code": "", "level": "UNKNOWN", "options": [], "basis": "NAME_NOT_IN_CATALOG"}
    found = index.in_description(description)
    if found:
        top = found[0]
        unique = len(found) == 1 or top["shared"] > found[1]["shared"]
        return {"code": top["code"] if unique else "", "level": "CATALOG_NAME_DESC", "options": found, "basis": "NAME_IN_DESCRIPTION"}
    prefix = index.description_prefix(description)
    if prefix:
        fuzzy = index.fuzzy(prefix)
        if fuzzy:
            top = fuzzy[0]
            unique = len(fuzzy) == 1 or top["score"] - fuzzy[1]["score"] >= 0.2
            return {"code": top["code"] if unique else "", "level": "CATALOG_NAME_DESC", "options": fuzzy, "basis": "NAME_PREFIX_FUZZY"}
    return {"code": "", "level": "UNKNOWN", "options": [], "basis": "NO_NAME"}
