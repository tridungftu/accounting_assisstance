"""Chỉ mục từ khóa trong bộ nhớ; chỉ tìm câu gốc và nguồn trích dẫn."""

from __future__ import annotations

from collections import Counter
import math
import re
import unicodedata


KHONG_THAY = "Không thấy trong hợp đồng."
_TOKEN = re.compile(r"\d+(?:[.,/\-]\d+)+|[^\W_]+")
_K1 = 1.2
_B = 0.75
_NGUONG_DIEM = 0.1
_THUONG_CUM = 0.1
_TRONG_SO_TIEU_DE = 0.25
_NHAN_TIEU_DE = re.compile(
    r"^(?:(?:dieu|chuong)\s+)?(?:\d+|[ivxlcdm]+)(?:\s*[.:]\s*|\s+|$)"
)


def chuan_hoa(chu: str) -> list[str]:
    """Bỏ dấu và tách từ; giữ dấu phân cách bên trong số tiền/ngày/tỷ lệ."""
    chu = unicodedata.normalize("NFD", chu.casefold().replace("đ", "d"))
    chu = "".join(c for c in chu if unicodedata.category(c) != "Mn")
    return _TOKEN.findall(chu)


_HU_TU_HOI = (
    "hỏi", "cho hỏi", "là", "gì", "nào", "bao nhiêu", "bao lâu", "mấy",
    "có", "không", "được", "chưa", "vậy", "thì", "của", "theo",
    "như thế nào", "thế nào", "khi nào", "ở đâu", "ai", "tôi", "mình",
    "ạ", "nhé", "à", "hả", "phần trăm", "một lần",
)
# So cụm có dấu trước khi bỏ dấu; thêm cách gõ không dấu nhưng không coi
# "vay" là hư từ "vậy". Giữ cả cụm "bao nhiêu" để không bỏ "bảo" trong bảo đảm.
_CUM_HU_TU_HOI = sorted(
    {tuple(cum.split()) for cum in _HU_TU_HOI}
    | {tuple(chuan_hoa(cum)) for cum in _HU_TU_HOI if cum != "vậy"},
    key=lambda cum: (-len(cum), cum),
)
_CAP_TU_CAN_GIU = {
    tuple(chuan_hoa(cum)) for cum in (
        "cố định", "quá hạn", "trước hạn", "trong hạn", "thả nổi", "ân hạn",
        "lãi suất", "điều chỉnh", "bảo đảm", "tài sản", "biên độ",
    )
}


def _tu_noi_dung_hoi(cau_hoi: str) -> list[str]:
    """Chỉ lọc phía câu hỏi; 'một lần' là cụm hỏi tần suất 'bao lâu ...'."""
    tu = _TOKEN.findall(unicodedata.normalize("NFC", cau_hoi.casefold()))
    tu_khong_dau = chuan_hoa(" ".join(tu))
    # Chỉ bảo vệ cách gõ không dấu trong cặp liền kề, không giữ hư từ
    # "co" ở mọi câu hỏi hay nhầm "có định" thành "cố định".
    vi_tri_can_giu = {
        j for i in range(len(tu) - 1)
        if tuple(tu_khong_dau[i:i + 2]) in _CAP_TU_CAN_GIU
        for j in (i, i + 1) if tu[j] == tu_khong_dau[j]
    }
    noi_dung = []
    i = 0
    while i < len(tu):
        for cum in _CUM_HU_TU_HOI:
            if (tuple(tu[i:i + len(cum)]) == cum
                    and not any(j in vi_tri_can_giu for j in range(i, i + len(cum)))):
                i += len(cum)
                break
        else:
            noi_dung.append(tu[i])
            i += 1
    return chuan_hoa(" ".join(noi_dung))


def _tu_tieu_de(nhan: str | None) -> list[str]:
    """Lấy chữ sau số Điều/Chương, không đưa nhãn số vào ngữ cảnh."""
    if not nhan:
        return []
    chu = " ".join(chuan_hoa(nhan))
    khop = _NHAN_TIEU_DE.match(chu)
    return chu[khop.end():].split() if khop else []


def _la_tieu_de(cau: str, doan: dict) -> bool:
    tu = chuan_hoa(cau)
    for cap in ("dieu", "chuong"):
        nhan = doan.get(cap)
        if nhan and _tu_tieu_de(nhan) and tu in (
                _tu_tieu_de(nhan), chuan_hoa(nhan), chuan_hoa(cap + " " + nhan)):
            return True
    return False


class ChiMucVay:
    """BM25 theo từng câu, k1=1.2, b=0.75; không sinh nội dung trả lời.

    Nhận khi điểm >= 0.1 và khớp hơn nửa số từ nội dung khác nhau của câu hỏi.
    Tiêu đề chỉ làm ngữ cảnh với trọng số 0.25 so với từ của chính câu.
    Thống kê BM25 chỉ tính trên tài liệu được lọc. Đồng điểm xếp theo ID
    tài liệu rồi thứ tự câu để kết quả ổn định sau khi nạp JSON.
    """

    def __init__(self):
        self._tai_lieu: dict[str, list[dict]] = {}
        self._tu: dict[str, list[tuple[list[str], list[str]]]] = {}

    def them(self, tai_lieu_id: str, ten_tep: str, doan_cat: list[dict]):
        """Thay chỉ mục cùng ID; mỗi phần tử doan['cau'] giữ nguyên chữ gốc."""
        cac_cau = []
        cac_tu = []
        for doan in doan_cat:
            ngu_canh = _tu_tieu_de(doan["dieu"]) + _tu_tieu_de(doan.get("chuong"))
            for cau in doan["cau"]:
                cac_cau.append({
                    "tai_lieu_id": tai_lieu_id, "ten_tep": ten_tep,
                    "trang_dau": doan["trang_dau"],
                    "trang_cuoi": doan["trang_cuoi"],
                    "dieu": doan["dieu"], "khoan": doan["khoan"],
                    "diem": doan["diem"], "ma_doan": doan["ma_doan"],
                    "cau": cau,
                    **({"chuong": doan["chuong"]} if "chuong" in doan else {}),
                })
                cac_tu.append(([], []) if _la_tieu_de(cau, doan)
                              else (chuan_hoa(cau), list(ngu_canh)))
        self._tai_lieu[tai_lieu_id] = cac_cau
        self._tu[tai_lieu_id] = cac_tu

    def xoa(self, tai_lieu_id):
        """Bỏ toàn bộ câu của ID; ID chưa tồn tại không gây lỗi."""
        self._tai_lieu.pop(tai_lieu_id, None)
        self._tu.pop(tai_lieu_id, None)

    def tim(self, cau_hoi: str, *, so_ket_qua=5,
            loc_tai_lieu: set[str] | None = None) -> list[dict]:
        """Trả câu cùng điểm và trích dẫn; trang đơn là số, khoảng là 'đầu-cuối'.

        diem ở kết quả là điểm tìm kiếm; trich_dan.diem là nhãn điểm gốc.
        Khoảng trang kế thừa cat_doan, không đoán trang riêng cho từng câu.
        """
        tu_hoi = _tu_noi_dung_hoi(cau_hoi)
        if not tu_hoi or so_ket_qua <= 0:
            return []
        cac_cau = []
        for ma in sorted(self._tai_lieu):
            if loc_tai_lieu is None or ma in loc_tai_lieu:
                cac_cau.extend((cau, tu, ngu_canh)
                               for cau, (tu, ngu_canh) in zip(self._tai_lieu[ma], self._tu[ma])
                               if tu)
        if not cac_cau:
            return []
        tan_suat = [(Counter(tu), Counter(ngu_canh)) for _, tu, ngu_canh in cac_cau]
        so_cau = len(cac_cau)
        do_dai_tb = sum(len(tu) for _, tu, _ in cac_cau) / so_cau
        if not do_dai_tb:
            return []
        tu_can = set(tu_hoi)
        df = Counter(t for dem, nen in tan_suat for t in dem.keys() | nen.keys()
                     if t in tu_can)
        idf = {t: math.log(1 + (so_cau - n + 0.5) / (n + 0.5))
               for t, n in df.items()}
        cum_hoi = set(zip(tu_hoi, tu_hoi[1:]))
        ket_qua = []
        for (cau, tu, ngu_canh), (dem, nen) in zip(cac_cau, tan_suat):
            khop = tu_can.intersection(dem.keys() | nen.keys())
            if not khop or len(khop) * 2 <= len(tu_can):
                continue
            he_so = _K1 * (1 - _B + _B * len(tu) / do_dai_tb)
            # Duyệt từ đã sắp xếp để tổng float ổn định giữa các tiến trình.
            diem = sum(
                idf[t] * (_K1 + 1) * (
                    dem[t] / (dem[t] + he_so)
                    + _TRONG_SO_TIEU_DE * nen[t] / (nen[t] + he_so))
                for t in sorted(khop))
            diem += _THUONG_CUM * len(cum_hoi.intersection(zip(tu, tu[1:])))
            diem += (_THUONG_CUM * _TRONG_SO_TIEU_DE
                     * len(cum_hoi.intersection(zip(ngu_canh, ngu_canh[1:]))))
            if diem < _NGUONG_DIEM:
                continue
            trang = cau["trang_dau"]
            if trang != cau["trang_cuoi"]:
                trang = f"{trang}-{cau['trang_cuoi']}"
            ket_qua.append({
                **cau, "diem": diem,
                "trich_dan": {
                    "ten_tep": cau["ten_tep"], "trang": trang,
                    "dieu": cau["dieu"], "khoan": cau["khoan"],
                    "diem": cau["diem"], "cau": cau["cau"],
                },
            })
        ket_qua.sort(key=lambda muc: -muc["diem"])
        return ket_qua[:so_ket_qua]

    def to_dict(self) -> dict:
        """JSON thuần, bản sao độc lập; sắp ID, giữ thứ tự câu của cat_doan."""
        return {"phien_ban": 1, "tai_lieu": [
            {"tai_lieu_id": ma, "ten_tep": self._tai_lieu[ma][0]["ten_tep"],
             "doan_cat": [
                 {"trang_dau": c["trang_dau"], "trang_cuoi": c["trang_cuoi"],
                  "dieu": c["dieu"], "khoan": c["khoan"], "diem": c["diem"],
                  **({"chuong": c["chuong"]} if "chuong" in c else {}),
                  "ma_doan": c["ma_doan"], "cau": [c["cau"]]}
                 for c in self._tai_lieu[ma]
             ]}
            for ma in sorted(self._tai_lieu) if self._tai_lieu[ma]
        ]}

    @classmethod
    def from_dict(cls, du_lieu: dict) -> ChiMucVay:
        """Nạp định dạng của to_dict, tính lại token thay vì tin cache ngoài."""
        if du_lieu.get("phien_ban") != 1:
            raise ValueError("Phiên bản chỉ mục vay không được hỗ trợ.")
        chi_muc = cls()
        for muc in du_lieu["tai_lieu"]:
            chi_muc.them(muc["tai_lieu_id"], muc["ten_tep"], muc["doan_cat"])
        return chi_muc
