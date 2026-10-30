"""G2-04: checksum và chặn hạ phiên bản theo ha_tang/postgres.py:217–260.

Chỉ lead dùng kết nối provisioning trên Core DEMO/test; không tự kết nối,
không cấp quyền cho login cài đặt. Cửa áp gói đã kiểm thuộc G2-25.
Mỗi tệp là một phiên bản; cả chuỗi và sổ dùng chung một transaction.
Bootstrap 001…004 ghi sổ ngay sau khi 004 dựng bảng, trước khi áp 005.
Không nhập/suy diễn lịch sử 67 migration cũ hoặc sửa checksum lịch sử.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


class LoiDoiCauTruc(RuntimeError):
    """Lỗi an toàn, không giữ thông báo driver có thể chứa credential/SQL."""

    def __init__(self, ma: str):
        self.ma = ma
        super().__init__(ma)


# Đây là căn cứ thiết kế, KHÔNG phải chứng cứ migration nguồn đã áp dụng.
NGUON_CORE = {
    'loai': 'DUNG_MOI',
    'can_cu': 'docs/47-core/g1/ANH-XA-MIGRATION.md',
    'lineage_doi_chieu': ['M0013_COMMON', 'M0017_SQL_IMPORT_HIEN_HANH'],
}
THU_MUC_SQL = Path(__file__).with_name('sql')


def _doc_chuoi(cac_tep):
    duong_dan = sorted((Path(p) for p in cac_tep), key=lambda p: p.name)
    chuoi = {}
    for tep in duong_dan:
        khop = re.fullmatch(r'([0-9]{3})_[a-z0-9_]+\.sql', tep.name)
        if (not khop or int(khop[1]) <= max(chuoi, default=0)
                or (not chuoi and int(khop[1]) != 1)):
            raise LoiDoiCauTruc('MIGRATION_ORDER')
        so = int(khop[1])
        noi_dung = tep.read_bytes()
        chuoi[so] = (noi_dung.decode('utf-8'), hashlib.sha256(noi_dung).hexdigest())
    if not chuoi:
        raise LoiDoiCauTruc('SCHEMA_VERSION')
    return chuoi


def ap_doi_cau_truc(conn, cac_tep=None, *, ma_goi='core', so_phien_ban=None,
                   nguon_lich_su=None) -> int:
    """Áp lần lượt tệp 001…đích, bỏ qua bản đã ghi đúng checksum.

    ``cac_tep`` là toàn bộ chuỗi SQL được lead kiểm, mặc định SQL Core kèm mã.
    Caller có thể bọc transaction lớn hơn; hàm không commit transaction ngoài.
    Đích rỗng phải dựng ít nhất tới 004 để sổ và DDL luôn cùng commit/rollback.
    ``nguon_lich_su`` chỉ nhận metadata nguồn, không truyền bí mật/nội dung tài liệu.
    """
    if not isinstance(ma_goi, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', ma_goi):
        raise LoiDoiCauTruc('MA_GOI')
    ma_loi = None
    try:
        chuoi = _doc_chuoi(THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql')
                          if cac_tep is None else cac_tep)
        dich = max(chuoi) if so_phien_ban is None else so_phien_ban
        if type(dich) is not int or dich not in chuoi:
            raise LoiDoiCauTruc('SCHEMA_VERSION')
        nguon = NGUON_CORE if nguon_lich_su is None else nguon_lich_su
        if not isinstance(nguon, dict):
            raise LoiDoiCauTruc('NGUON_LICH_SU')
        nguon_json = json.dumps(nguon, ensure_ascii=False)
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute('SELECT current_database()')
                if not re.fullmatch(r'kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+',
                                    cur.fetchone()[0]):
                    raise LoiDoiCauTruc('DICH_KHONG_AN_TOAN')
                # Một khóa transaction chung cả bootstrap, trước khi bảng sổ tồn tại.
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('kho_core_migration', 4))")
                cur.execute("SELECT to_regclass('loi.lich_su_doi_cau_truc')")
                co_so = cur.fetchone()[0] is not None
                lich_su = {}
                if co_so:
                    cur.execute('SELECT so_phien_ban, ma_bam FROM loi.lich_su_doi_cau_truc '
                                'WHERE ma_goi=%s ORDER BY so_phien_ban', (ma_goi,))
                    lich_su = dict(cur.fetchall())
                elif ma_goi != 'core' or dich < 4:
                    raise LoiDoiCauTruc('CAN_BOOTSTRAP_004')
                ban_cu = max(lich_su, default=0)
                if ban_cu > dich:
                    raise LoiDoiCauTruc('FUTURE_SCHEMA')
                # Khoảng trống hợp lệ; không chèn bù số nhỏ hơn bản đã áp.
                if (any(so not in chuoi for so in lich_su)
                        or any(so <= ban_cu and so not in lich_su for so in chuoi)):
                    raise LoiDoiCauTruc('MIGRATION_ORDER')
                # Kiểm TẤT CẢ checksum trước bất kỳ DDL nào của gói.
                for so, bam in lich_su.items():
                    if chuoi[so][1] != bam:
                        raise LoiDoiCauTruc('MIGRATION_CHANGED')
                cho_ghi = []
                for so, (cau_sql, bam) in chuoi.items():
                    if so <= ban_cu or so > dich:
                        continue
                    cur.execute(cau_sql)
                    cho_ghi.append((ma_goi, so, bam, nguon_json))
                    if not co_so:
                        cur.execute("SELECT to_regclass('loi.lich_su_doi_cau_truc')")
                        co_so = cur.fetchone()[0] is not None
                    if co_so:
                        for dong in cho_ghi:
                            cur.execute('INSERT INTO loi.lich_su_doi_cau_truc '
                                        '(ma_goi,so_phien_ban,ma_bam,nguon_lich_su) '
                                        'VALUES (%s,%s,%s,%s::jsonb)', dong)
                        cho_ghi.clear()
                if cho_ghi:
                    raise LoiDoiCauTruc('CAN_BOOTSTRAP_004')
        return dich
    except LoiDoiCauTruc as exc:
        ma_loi = exc.ma
    except Exception:
        ma_loi = 'DOI_CAU_TRUC_THAT_BAI'
    # Ngoài except: không giữ __context__ chứa DSN/thông báo SQL của driver.
    raise LoiDoiCauTruc(ma_loi)
