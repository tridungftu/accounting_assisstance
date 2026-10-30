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
    """Chẩn đoán an toàn; không giữ driver, SQL hoặc giá trị tham số.

    Ngoài lớp SQLSTATE 42 chỉ giữ mã SQLSTATE và vị trí tệp. Context chỉ
    giữ loại frame, số dòng và thao tác; primary chỉ giữ mẫu lỗi đã biết.
    Không phản chiếu tên đối tượng hay token SQL vì chúng cũng có thể là dữ liệu.
    """

    def __init__(self, ma: str, *, so_phien_ban=None, ten_tep=None,
                 sqlstate=None, context=None, message_primary=None):
        self.ma = ma
        self.so_phien_ban = (so_phien_ban if type(so_phien_ban) is int
                             and 1 <= so_phien_ban <= 999 else None)
        self.ten_tep = (ten_tep if isinstance(ten_tep, str) and re.fullmatch(
            r'[0-9]{3}_[a-z0-9_]+\.sql', ten_tep) else None)
        self.sqlstate = (sqlstate if isinstance(sqlstate, str)
                         and re.fullmatch(r'[0-9A-Z]{5}', sqlstate) else None)
        lop_42 = self.sqlstate is not None and self.sqlstate.startswith('42')
        self.context = _loc_context(context) if lop_42 else None
        self.message_primary = _loc_primary(message_primary) if lop_42 else None
        chi_tiet = [f'{ten}={gia_tri}' for ten, gia_tri in (
            ('so_phien_ban', self.so_phien_ban), ('ten_tep', self.ten_tep),
            ('sqlstate', self.sqlstate), ('context', self.context),
            ('message_primary', self.message_primary)) if gia_tri is not None]
        super().__init__(ma + (': ' + '; '.join(chi_tiet) if chi_tiet else ''))


def _co_bi_mat(chuoi):
    return re.search(r'postgres(?:ql)?://|(?:password|host)\s*=', chuoi, re.I)


def _loc_context(context):
    """Allowlist cấu trúc frame; bỏ SQL statement, bind và mọi văn bản tự do."""
    if not isinstance(context, str) or not context:
        return None
    if _co_bi_mat(context):
        return '[DA_LOC]'
    cac_dong = []
    for dong in context.splitlines():
        khop = re.fullmatch(
            r'PL/pgSQL function .+ line ([0-9]{1,6}) at '
            r'(SQL statement|EXECUTE|RAISE|assignment|RETURN|PERFORM|IF|FOR over SELECT rows)',
            dong.strip())
        if khop:
            cac_dong.append(f'PL/pgSQL function [DA_LOC] line {khop[1]} at {khop[2]}')
        else:
            khop = re.fullmatch(r'compilation of PL/pgSQL function .+ near line ([0-9]{1,6})',
                                dong.strip())
            if khop:
                cac_dong.append(f'compilation of PL/pgSQL function [DA_LOC] near line {khop[1]}')
        if len(cac_dong) == 8:
            break
    return '\n'.join(cac_dong) if cac_dong else '[DA_LOC]'


def _loc_primary(primary):
    """Chỉ xuất các phần cố định của thông báo; không dùng str(driver)."""
    if not isinstance(primary, str) or not primary:
        return None
    if _co_bi_mat(primary):
        return '[DA_LOC]'
    if primary in ('syntax error', 'syntax error at end of input',
                   'query has no destination for result data'):
        return primary
    khop = re.fullmatch(
        r'(syntax error at or near|unterminated quoted string at or near|'
        r'unterminated dollar-quoted string at or near|'
        r'unterminated quoted identifier at or near) .+', primary, re.S)
    if khop:
        return khop[1] + ' [DA_LOC]'
    khop = re.fullmatch(
        r'(relation|column|function|type|schema|operator) .+ '
        r'(does not exist|already exists|is ambiguous)', primary, re.S)
    if khop:
        return f'{khop[1]} [DA_LOC] {khop[2]}'
    return '[DA_LOC]'


def _doc_truong(chan_doan, ten):
    # Driver không có diag/sqlstate hoặc property lỗi vẫn giữ được mã lỗi cũ.
    try:
        return getattr(chan_doan, ten, None)
    except Exception:
        return None


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
    loi = None
    tep_hien_tai = None
    try:
        cac_tep = [Path(p) for p in (THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql')
                                    if cac_tep is None else cac_tep)]
        chuoi = _doc_chuoi(cac_tep)
        ten_theo_so = {int(p.name[:3]): p.name for p in cac_tep}
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
                    tep_hien_tai = (so, ten_theo_so[so])
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
                    tep_hien_tai = None
                if cho_ghi:
                    raise LoiDoiCauTruc('CAN_BOOTSTRAP_004')
        return dich
    except LoiDoiCauTruc as exc:
        loi = LoiDoiCauTruc(exc.ma)
    except Exception as exc:
        so, ten = tep_hien_tai or (None, None)
        diag = _doc_truong(exc, 'diag') if tep_hien_tai else None
        loi = LoiDoiCauTruc(
            'DOI_CAU_TRUC_THAT_BAI', so_phien_ban=so, ten_tep=ten,
            sqlstate=_doc_truong(exc, 'sqlstate') if tep_hien_tai else None,
            context=_doc_truong(diag, 'context'),
            message_primary=_doc_truong(diag, 'message_primary'))
        diag = None  # Không giữ diag thô trong locals của traceback mới.
    # Ngoài except: không giữ __context__ chứa DSN/thông báo SQL của driver.
    raise loi
