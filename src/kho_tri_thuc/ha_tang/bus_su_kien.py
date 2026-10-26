"""XS-1B: cổng Python mỏng cho bus PostgreSQL M0052.

Bên gọi cung cấp kết nối đã đặt danh tính/quyền và đang trong giao dịch.
Các hàm không mở kết nối/giao dịch, không commit, rollback hay ghi log payload;
lỗi SQL được truyền nguyên để bên gọi rollback toàn giao dịch.

``phap_nhan_id`` do mã máy chủ lấy từ đối tượng đã đọc qua RLS, tuyệt đối
không lấy từ body client. ``ben_phat``/``ben_nhan`` là mã module do máy chủ
chọn; SQL M0052 kiểm quyền phiên cho pháp nhân/module, không tự cấp quyền.

Giao ít nhất một lần: sự kiện chưa ACK có thể được nhận lại. Bên nhận phải
ghi kết quả nghiệp vụ và ACK trên CHÍNH kết nối, trong CÙNG giao dịch; lỗi
giữa ghi kết quả và ACK hoặc sau ACK phải rollback cả hai. Không thực hiện
tác động ngoài PostgreSQL với giả định exactly-once. Dedupe/inbox do SQL giữ.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any
from uuid import UUID


def _gia_tri(dong, cot):
    """Đọc scalar với tuple_row hoặc dict_row của psycopg."""
    return dong[cot] if isinstance(dong, Mapping) else dong[0]


def phat(conn, loai: str, phien_ban: int, khoa_dedupe: str,
         tham_chieu: dict[str, str | list[str]], *, phap_nhan_id: UUID,
         ben_phat: str) -> UUID:
    """Phát trong giao dịch nghiệp vụ của bên gọi, trả UUID (kể cả dedupe).

    ``phap_nhan_id`` phải lấy từ đối tượng đã đọc qua RLS, không từ body
    client; ``ben_phat`` là mã module máy chủ. ``tham_chieu`` là object các
    khóa *_id (chuỗi UUID) / *_ids (mảng chuỗi UUID); M0052 kiểm hợp lệ và
    từ chối cùng khóa dedupe nhưng khác nội dung/loại/phiên bản. Không commit.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT bus.phat(%s,%s,%s,%s,%s,%s::jsonb) AS id",
            (phap_nhan_id, ben_phat, loai, phien_ban, khoa_dedupe,
             json.dumps(tham_chieu, ensure_ascii=False)),
        )
        return _gia_tri(cur.fetchone(), "id")


def nhan(conn, ben_nhan: str, loai: str | None = None, gioi_han: int = 100,
         *, phap_nhan_id: UUID) -> list[Any]:
    """Nhận các dòng bus.su_kien, giữ row_factory của kết nối; chưa ACK.

    ``phap_nhan_id`` lấy từ đối tượng đã đọc qua RLS, không từ body client.
    SQL giữ khóa inbox đến cuối giao dịch; nhận lại trước ACK vẫn trả cùng
    sự kiện, không thêm inbox. Ghi kết quả + ACK cùng kết nối/giao dịch và
    rollback cả hai khi lỗi. Không commit; loại None nghĩa là mọi loại.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM bus.nhan(%s,%s,%s,%s)",
                    (phap_nhan_id, ben_nhan, loai, gioi_han))
        return cur.fetchall()


def ack(conn, ben_nhan: str, su_kien_id: UUID, *, phap_nhan_id: UUID) -> bool:
    """ACK đầu trả True, ACK lặp trả False; SQL từ chối nếu chưa nhận.

    ``phap_nhan_id`` lấy từ đối tượng đã đọc qua RLS, không từ body client.
    Phải gọi trên chính kết nối/giao dịch ghi kết quả nghiệp vụ; bên gọi
    rollback cả kết quả và ACK khi lỗi, kể cả lỗi sau ACK. Không commit.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT bus.ack(%s,%s,%s) AS da_ack",
                    (phap_nhan_id, ben_nhan, su_kien_id))
        return _gia_tri(cur.fetchone(), "da_ack")
