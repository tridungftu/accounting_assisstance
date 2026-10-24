"""M2-00B — client loopback RPC/SSE tới ĐÚNG tiến trình Node sở hữu (`tien_trinh.TienTrinhNode`).

Chỉ `127.0.0.1:<cổng đã bắt tay>`; capability trong header riêng (không URL/query/log/repr/exception). Mỗi request có timeout, phản hồi đọc
hữu hạn, Content-Type phải JSON, DTO kiểm hình dạng tối thiểu. SSE: dòng hữu hạn, JSON hỏng/quá lớn/seq lạ/khác job → dừng có mã; trước MỖI
chunk gọi `con_hop_le()` của coordinator (quyền hiện hành) — trả False thì đóng kết nối, không phát thêm.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import re
import socket

CAP_HEADER = "X-Source7-M2-Cap"
RE_HEX64 = re.compile(r"[0-9a-f]{64}")
RE_MA = re.compile(r"[A-Z0-9][A-Z0-9_+]{1,79}")
TRANG_THAI_START = ("STARTED", "RUNNING", "REPLAY", "UNKNOWN")
TRANG_THAI_STATUS = ("RUNNING", "REPLAY", "UNKNOWN", "NOT_FOUND")
LOAI_SU_KIEN = ("log", "phase", "month", "progress", "manifest", "error", "done")


class LoiKhach(Exception):
    """Lỗi RPC/SSE: mã ngắn + HTTP status (nếu có). Không mang capability/body thô."""

    def __init__(self, ma: str, http_status: int | None = None):
        super().__init__(ma)
        self.ma = ma
        self.http_status = http_status

    def __repr__(self):
        return f"LoiKhach({self.ma!r}, {self.http_status!r})"


def _ma_an_toan(v, mac_dinh: str) -> str:
    return v if isinstance(v, str) and RE_MA.fullmatch(v) else mac_dinh


class KhachNode:
    def __init__(self, port: int, capability: str, gioi_han, *, ket_noi=http.client.HTTPConnection):
        if type(port) is not int or not 0 < port < 65536:
            raise LoiKhach("KHACH_CONG_SAI")
        if not isinstance(capability, str) or len(capability) < 43:
            raise LoiKhach("KHACH_CAPABILITY_SAI")
        self._port, self._cap, self._gh, self._ket_noi = port, capability, gioi_han, ket_noi

    def __repr__(self):
        return f"KhachNode(port={self._port})"

    # ------------------------------------------------------------------ hạ tầng
    def _headers(self, co_body: bool, n: int = 0) -> dict:
        h = {"Host": f"127.0.0.1:{self._port}", CAP_HEADER: self._cap, "Accept": "application/json"}
        if co_body:
            h.update({"Content-Type": "application/json", "Content-Length": str(n)})
        return h

    def _mo(self, timeout: float):
        return self._ket_noi("127.0.0.1", self._port, timeout=timeout)

    def _goi(self, method: str, duong: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if data is not None and len(data) > self._gh.body_bytes:
            raise LoiKhach("KHACH_BODY_QUA_LON")
        c = self._mo(self._gh.rpc_s)
        try:
            try:
                c.request(method, duong, body=data, headers=self._headers(data is not None, len(data or b"")))
                r = c.getresponse()
                status = r.status
                ct = (r.getheader("Content-Type") or "").lower()
                raw = r.read(self._gh.phan_hoi_bytes + 1)
            except (socket.timeout, TimeoutError):
                raise LoiKhach("KHACH_QUA_HAN") from None
            except (OSError, http.client.HTTPException):
                raise LoiKhach("KHACH_KHONG_KET_NOI") from None
        finally:
            c.close()
        if len(raw) > self._gh.phan_hoi_bytes:
            raise LoiKhach("KHACH_PHAN_HOI_QUA_LON", status)
        if not ct.startswith("application/json"):
            raise LoiKhach("KHACH_CONTENT_TYPE", status)
        try:
            v = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise LoiKhach("KHACH_JSON_HONG", status) from None
        if not isinstance(v, dict) or not isinstance(v.get("ok"), bool):
            raise LoiKhach("KHACH_DTO_SAI", status)
        if status != 200 or v["ok"] is not True:
            raise LoiKhach(_ma_an_toan(v.get("code"), "KHACH_TU_CHOI"), status)
        return v

    # ------------------------------------------------------------------ RPC
    def config(self) -> dict:
        v = self._goi("GET", "/api/config")
        if not isinstance(v.get("protocol"), str) or not isinstance(v.get("version"), str) or not isinstance(v.get("running"), bool):
            raise LoiKhach("KHACH_DTO_SAI", 200)
        return {"protocol": v["protocol"], "version": v["version"], "running": v["running"]}

    def profiles(self, ds: list[dict]) -> list[dict]:
        v = self._goi("POST", "/api/profiles", {"profiles": ds})
        out = []
        for p in v.get("profiles") or []:
            if not isinstance(p, dict) or not isinstance(p.get("ref"), str) or not isinstance(p.get("san_sang"), bool):
                raise LoiKhach("KHACH_DTO_SAI", 200)
            out.append({"ref": p["ref"], "revision": p.get("revision"), "san_sang": p["san_sang"],
                        "ly_do": _ma_an_toan(p.get("ly_do"), "PROFILE_UNREADABLE") if p.get("ly_do") is not None else None})
        return out

    @staticmethod
    def _run_cua(context) -> tuple[str, str]:
        """(run_id, SHA-256 UTF-8 của CHÍNH context.run.request_key). Thiếu/sai kiểu → lỗi có mã, trước mọi IO."""
        run = context.get("run") if isinstance(context, dict) else None
        if not isinstance(run, dict) or not isinstance(run.get("run_id"), str) or not isinstance(run.get("request_key"), str) \
                or not run["request_key"]:
            raise LoiKhach("KHACH_CONTEXT_SAI")
        return run["run_id"], hashlib.sha256(run["request_key"].encode("utf-8")).hexdigest()

    def _kiem_run(self, v: dict, run: tuple, digest: str, cho_phep: tuple) -> dict:
        run_id, khoa_sha = run
        if v.get("status") not in cho_phep or v.get("run_id") != run_id or v.get("context_digest") != digest \
                or not isinstance(v.get("request_key_sha256"), str) or not RE_HEX64.fullmatch(v["request_key_sha256"]) \
                or v["request_key_sha256"] != khoa_sha:
            raise LoiKhach("KHACH_DTO_KHAC_RUN", 200)
        return v

    def start(self, context: dict, digest: str) -> dict:
        run = self._run_cua(context)
        return self._kiem_run(self._goi("POST", "/api/start", {"context": context}), run, digest, TRANG_THAI_START)

    def status(self, context: dict, digest: str) -> dict:
        run = self._run_cua(context)
        return self._kiem_run(self._goi("POST", "/api/status", {"context": context}), run, digest, TRANG_THAI_STATUS)

    def reconcile(self, context: dict, digest: str) -> dict:
        run = self._run_cua(context)
        return self._kiem_run(self._goi("POST", "/api/reconcile", {"context": context}), run, digest, TRANG_THAI_STATUS)

    def open_folder(self, context: dict, run_rel: str) -> dict:
        v = self._goi("POST", "/api/open-folder", {"context": context, "run_rel": run_rel})
        if v.get("run_rel") != run_rel:
            raise LoiKhach("KHACH_DTO_SAI", 200)
        return {"ok": True}

    # ------------------------------------------------------------------ SSE
    def events(self, context: dict, digest: str, cursor: int, *, con_hop_le):
        """Generator sự kiện của ĐÚNG run/context. Kết thúc bằng một dict {"ket_thuc": lý do}. Quyền mất → {"ket_thuc": "QUYEN_THAY_DOI"}."""
        if type(cursor) is not int or cursor < 0:
            raise LoiKhach("SSE_CURSOR_SAI")
        data = json.dumps({"context": context, "cursor": cursor}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(data) > self._gh.body_bytes:
            raise LoiKhach("KHACH_BODY_QUA_LON")
        c = self._mo(self._gh.sse_doc_s)
        try:
            try:
                c.request("POST", "/api/events", body=data, headers={**self._headers(True, len(data)), "Accept": "text/event-stream"})
                r = c.getresponse()
            except (socket.timeout, TimeoutError):
                raise LoiKhach("SSE_QUA_HAN") from None
            except (OSError, http.client.HTTPException):
                raise LoiKhach("KHACH_KHONG_KET_NOI") from None
            ct = (r.getheader("Content-Type") or "").lower()
            if r.status != 200 or not ct.startswith("text/event-stream"):
                try:
                    raw = r.read(self._gh.phan_hoi_bytes + 1)
                    v = json.loads(raw.decode("utf-8")) if len(raw) <= self._gh.phan_hoi_bytes else None
                except (OSError, http.client.HTTPException, UnicodeDecodeError, ValueError):
                    v = None
                raise LoiKhach(_ma_an_toan(v.get("code") if isinstance(v, dict) else None, "SSE_TU_CHOI"), r.status)
            truoc = cursor
            khung: list[str] = []
            su_kien_ten = None
            if not con_hop_le():
                yield {"ket_thuc": "QUYEN_THAY_DOI"}
                return
            while True:
                try:
                    dong = r.readline(self._gh.dong_sse_bytes + 1)
                except (socket.timeout, TimeoutError):
                    raise LoiKhach("SSE_QUA_HAN") from None
                except (OSError, http.client.HTTPException):
                    raise LoiKhach("SSE_DUT") from None
                if not dong:
                    yield {"ket_thuc": "EOF_KHONG_END"}
                    return
                if len(dong) > self._gh.dong_sse_bytes or not dong.endswith(b"\n"):
                    raise LoiKhach("SSE_DONG_QUA_LON" if len(dong) > self._gh.dong_sse_bytes else "SSE_CAT_CUT")
                try:
                    s = dong.decode("utf-8", errors="strict").rstrip("\r\n")
                except UnicodeDecodeError:
                    raise LoiKhach("SSE_JSON_HONG") from None
                if s.startswith(":"):  # heartbeat/comment: vẫn kiểm quyền hiện hành mỗi nhịp
                    if not con_hop_le():
                        yield {"ket_thuc": "QUYEN_THAY_DOI"}
                        return
                    continue
                if s:
                    if s.startswith("data: "):
                        khung.append(s[6:])
                    elif s.startswith("event: "):
                        su_kien_ten = s[7:]
                    elif not s.startswith("id: "):
                        raise LoiKhach("SSE_DONG_LA")
                    if sum(len(x) for x in khung) > self._gh.dong_sse_bytes:
                        raise LoiKhach("SSE_DONG_QUA_LON")
                    continue
                if not khung:
                    su_kien_ten = None
                    continue
                try:
                    v = json.loads("\n".join(khung))
                except ValueError:
                    raise LoiKhach("SSE_JSON_HONG") from None
                khung, ten, su_kien_ten = [], su_kien_ten, None
                if ten == "end":
                    ly_do = v.get("reason") if isinstance(v, dict) else None
                    yield {"ket_thuc": _ma_an_toan(ly_do, "END")}
                    return
                if ten is not None:
                    raise LoiKhach("SSE_DONG_LA")
                if not isinstance(v, dict) or type(v.get("seq")) is not int or v["seq"] <= truoc:
                    raise LoiKhach("SSE_THU_TU_SAI")
                if v.get("run_id") != context["run"]["run_id"] or v.get("context_digest") != digest:
                    raise LoiKhach("SSE_KHAC_JOB")
                if v.get("type") not in LOAI_SU_KIEN or not isinstance(v.get("payload"), dict):
                    raise LoiKhach("SSE_DTO_SAI")
                truoc = v["seq"]
                if not con_hop_le():  # kiểm NGAY TRƯỚC khi phát chunk (không dùng quyết định đã đệm)
                    yield {"ket_thuc": "QUYEN_THAY_DOI"}
                    return
                yield {"seq": v["seq"], "type": v["type"], "payload": v["payload"], "ts": v.get("ts")}
        finally:
            c.close()
