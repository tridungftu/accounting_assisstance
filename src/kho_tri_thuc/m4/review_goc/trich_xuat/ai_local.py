# -*- coding: utf-8 -*-
"""
ai_local.py — Gọi Local AI (Ollama /api/chat) theo đúng cách đã thống nhất (v3):
  temperature 0; format = JSON schema; num_ctx 16384 (trích) / 32768 (tìm vị trí qua mục lục);
  think = false (qwen/gemma…), "low" với gpt-oss; model không nhận "think" (vd gemma3 báo lỗi 400/500) → hỏi lại không có "think";
  lỗi mạng/timeout → thử lại sau 10 s rồi 30 s; JSON hỏng → hỏi lại 1 lần kèm nhắc "chỉ trả JSON".
  Prompt dài hơn num_ctx (Ollama lặng lẽ cắt) → báo lỗi rõ ràng thay vì nhận kết quả sai.
Dừng giữa chừng: đặt Event `dung` → bỏ câu hỏi đang chờ, ném DaDung.
"""
import http.client
import json
import re
import socket
import threading
import time
import urllib.error
import urllib.request

SYSTEM = ("Bạn là chuyên viên trích xuất dữ liệu hợp đồng xây dựng. Chỉ dùng các đoạn hợp đồng được cung cấp. "
          "Không suy diễn, không bịa. Trả lời đúng định dạng JSON được yêu cầu.")
JSON_NHAC = "\n\nCHỈ TRẢ VỀ JSON hợp lệ đúng schema, không thêm chữ nào khác ngoài JSON."
RETRY_WAITS = (10, 30)
CTX_TRICH, CTX_MUC_LUC = 16384, 32768
NET_ERRORS = (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout, http.client.HTTPException)

SCHEMA_TRICH = {"type": "object", "properties": {"ket_qua": {"type": "array", "items": {
    "type": "object",
    "properties": {k: {"type": "string"} for k in ("ma", "gia_tri", "don_vi", "dieu_khoan", "trich_dan", "ghi_chu")},
    "required": ["ma", "gia_tri", "don_vi", "dieu_khoan", "trich_dan", "ghi_chu"]}}}, "required": ["ket_qua"]}


class AILoi(Exception):
    """AI không trả lời được (mạng hỏng sau khi thử lại, JSON hỏng sau khi hỏi lại, prompt bị cắt…)."""


class DaDung(Exception):
    """Người dùng bấm Dừng."""


def parse_json(txt, key):
    try:
        data = json.loads(txt)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{.*\}", txt or "", re.S)
        try:
            data = json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            data = None
    return data if isinstance(data, dict) and isinstance(data.get(key), list) else None


def _cho(giay, dung):
    """Ngủ `giay` giây, thức dậy sớm nếu bấm Dừng."""
    if dung is None:
        time.sleep(giay)
        return
    if dung.wait(giay):
        raise DaDung()


class MayAI:
    def __init__(self, url, model, timeout=1800, ghi_log=None, dung=None, retry_waits=RETRY_WAITS):
        self.url = str(url).rstrip("/")
        self.model = model
        self.timeout = timeout
        self.ghi_log = ghi_log or (lambda msg: None)
        self.dung = dung
        self.retry_waits = tuple(retry_waits)
        self.khong_think = False             # model không nhận tham số "think"
        self.tok_vao = self.tok_ra = self.so_lan_goi = 0

    # ---------------------------------------------------------------- HTTP
    def _http(self, path, payload=None, timeout=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(self.url + path, data=data, headers={"Content-Type": "application/json"},
                                     method="POST" if data else "GET")
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _http_co_the_dung(self, path, payload):
        """Gọi HTTP trong luồng phụ để nút Dừng có hiệu lực ngay (câu hỏi đang chờ bị bỏ, AI tự chạy xong)."""
        if self.dung is None:
            return self._http(path, payload)
        kq = {}

        def chay():
            try:
                kq["ok"] = self._http(path, payload)
            except BaseException as e:      # noqa: BLE001 — chuyển lỗi về luồng chính
                kq["loi"] = e
        t = threading.Thread(target=chay, daemon=True)
        t.start()
        while t.is_alive():
            t.join(0.5)
            if self.dung.is_set():
                raise DaDung()
        if "loi" in kq:
            raise kq["loi"]
        return kq["ok"]

    def models(self, timeout=8):
        return [m.get("name") for m in self._http("/api/tags", timeout=timeout).get("models", [])]

    def think(self):
        if self.khong_think:
            return None
        return "low" if str(self.model).lower().startswith("gpt-oss") else False

    def _post(self, payload, what):
        last = None
        for i, wait in enumerate((0,) + self.retry_waits):
            if wait:
                self.ghi_log(f"Lỗi kết nối AI ({type(last).__name__}) — thử lại sau {wait}s")
                _cho(wait, self.dung)
            try:
                return self._http_co_the_dung("/api/chat", payload)
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", "replace")[:300]
                except Exception:  # noqa: BLE001
                    pass
                if e.code in (400, 500) and "think" in payload and not self.khong_think and \
                        (e.code == 400 or "think" in body.lower() or "thinking" in body.lower() or not body):
                    self.khong_think = True          # vd gemma3: "does not support thinking"
                    payload = {k: v for k, v in payload.items() if k != "think"}
                    self.ghi_log(f"Model {self.model} không nhận tham số think → hỏi lại không có think")
                    try:
                        return self._http_co_the_dung("/api/chat", payload)
                    except NET_ERRORS as e2:
                        last = e2
                        continue
                if e.code == 404:
                    raise AILoi(f"Máy AI chưa có model {self.model} (HTTP 404)")
                last = e
                self.ghi_log(f"LỖI máy AI lần {i + 1} ({what}): HTTP {e.code} {body[:120]}")
            except NET_ERRORS as e:
                last = e
                self.ghi_log(f"LỖI mạng lần {i + 1} ({what}): {type(e).__name__}: {str(e)[:120]}")
        raise AILoi(f"mất kết nối AI sau {len(self.retry_waits) + 1} lần thử: {type(last).__name__}: {str(last)[:150]}")

    # ---------------------------------------------------------------- hỏi JSON
    def chat_json(self, prompt, schema, key, num_ctx, what="AI"):
        """Trả (data, token_vào, token_ra). Hỏng hẳn → AILoi. Bấm Dừng → DaDung."""
        tin = tout = 0
        for attempt in range(2):
            if self.dung is not None and self.dung.is_set():
                raise DaDung()
            payload = {"model": self.model, "stream": False, "format": schema,
                       "options": {"temperature": 0, "num_ctx": num_ctx},
                       "messages": [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": prompt + (JSON_NHAC if attempt else "")}]}
            th = self.think()
            if th is not None:
                payload["think"] = th
            r = self._post(payload, what)
            self.so_lan_goi += 1
            pi, po = r.get("prompt_eval_count", 0) or 0, r.get("eval_count", 0) or 0
            tin += pi
            tout += po
            self.tok_vao += pi
            self.tok_ra += po
            if pi and pi >= num_ctx - 8:
                raise AILoi(f"Câu hỏi dài {pi:,} token ≥ giới hạn {num_ctx:,} — máy AI đã cắt bớt, kết quả không tin được")
            data = parse_json((r.get("message") or {}).get("content", ""), key)
            if data is not None:
                return data, tin, tout
            self.ghi_log(f"AI trả JSON không hợp lệ ({what})" + (" — hỏi lại, nhắc 'chỉ trả JSON'" if not attempt else ""))
        raise AILoi("AI trả JSON không hợp lệ sau 2 lần")

    def hoi_trich(self, prompt, what="AI"):
        data, tin, tout = self.chat_json(prompt, SCHEMA_TRICH, "ket_qua", CTX_TRICH, what)
        return [x for x in data["ket_qua"] if isinstance(x, dict)], tin, tout
