# -*- coding: utf-8 -*-
"""mock_cloud.py — Máy chủ GIẢ LẬP API Anthropic / OpenAI để thử bước kiểm tra chéo cloud (không gửi gì ra ngoài).
    srv, port = start(tra_loi={"TT-20": ("90", "câu trích…")})   → srv.requests: list (headers, body)"""
import json
import re
import threading
import http.server


def start(tra_loi):
    reqs = []

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            reqs.append((dict(self.headers), body))
            if self.path.endswith("/messages") and "temperature" in body:   # như model Claude mới
                b = json.dumps({"type": "error", "error": {"type": "invalid_request_error",
                                                           "message": "`temperature` is deprecated for this model."}}).encode()
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
                return
            prompt = body["messages"][-1]["content"]
            codes = re.findall(r"^- ((?:TC|TT|Y)-\d+) \|", prompt, re.M)
            out = []
            for c in codes:
                v, q = tra_loi.get(c, ("Không quy định", ""))
                out.append({"ma": c, "gia_tri": v, "don_vi": "", "dieu_khoan": "", "trich_dan": q, "ghi_chu": ""})
            txt = json.dumps({"ket_qua": out}, ensure_ascii=False)
            if self.path.endswith("/messages"):
                d = {"content": [{"type": "text", "text": txt}], "usage": {"input_tokens": 100, "output_tokens": 50}}
            else:
                d = {"choices": [{"message": {"content": txt}}], "usage": {"prompt_tokens": 100, "completion_tokens": 50}}
            b = json.dumps(d, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    srv.requests = reqs
    return srv, srv.server_address[1]
