"""
mock_ollama.py — Máy chủ GIẢ LẬP API Ollama để kiểm thử toàn luồng KHÔNG cần GPU.
- GET  /api/tags  → danh sách model
- POST /api/chat  → nếu prompt là "MỤC LỤC HỢP ĐỒNG": trả vị trí theo từ khoá đơn giản;
                     còn lại: trả giá trị lấy từ file đáp án (DAP_AN_*.tsv) cho các mã được hỏi.
Tuỳ chọn WRONG={"TT-54": "câu trích sai"} để kiểm tra bước tự kiểm tra có bắt lỗi không.
Giả lập sự cố (đặt trong srv.ctl): "loi_mang": N → N lần /api/chat kế tiếp trả HTTP 503;
                                   "json_hong": N → N lần /api/chat kế tiếp trả nội dung không phải JSON;
                                   "sai_lan_dau": {mã} → lần đầu hỏi mã đó trả trích dẫn sai.
                                   "think_500": True → yêu cầu có "think" bị HTTP 500 (như gemma3);
                                   "ctx_day": True → prompt_eval_count = num_ctx (giả lập prompt bị cắt);
                                   "cham": giây → trả lời chậm (thử nút Dừng);
                                   "phu_luc": {thay_doi, khac} → câu trả lời cho prompt trích phụ lục.
POST …/v1/messages (định dạng Anthropic) → cùng câu trả lời, gói theo kiểu Anthropic (thử nguồn AI = Claude).
Dùng:  srv, port = start(answer_tsv_paths, wrong={...});  ...;  srv.shutdown()
"""
import json, re, threading, http.server


def _load(paths):
    keys = {}
    for p in paths:
        k = {}
        with open(p, encoding="utf-8-sig") as fh:
            lines = fh.read().splitlines()
        for line in lines:
            c = line.rstrip("\r\n").split("\t")
            if len(c) >= 8 and re.match(r"^(TC|TT)-\d+$", c[0]):
                k[c[0]] = c
        keys[p] = k
    return keys


def start(answer_paths, wrong=None, model="qwen3.6:35b"):
    keys = _load(answer_paths)
    wrong = wrong or {}
    calls = {"chat": 0, "locate": 0, "http": 0}
    ctl = {"loi_mang": 0, "json_hong": 0, "sai_lan_dau": set(), "think_500": False, "ctx_day": False, "cham": 0,
           "phu_luc": {"thay_doi": [], "khac": []}}
    prompts = []
    thinks = []

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, o):
            if self.path.endswith("/v1/messages"):       # giả lập API Anthropic (nguồn AI = Claude): cùng câu trả lời
                o = {"content": [{"type": "text", "text": (o.get("message") or {}).get("content", "")}],
                     "usage": {"input_tokens": o.get("prompt_eval_count", 100), "output_tokens": o.get("eval_count", 50)}}
            b = json.dumps(o, ensure_ascii=False).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            self._send({"models": [{"name": model}]})

        def do_POST(self):
            d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            p = d["messages"][-1]["content"]
            calls["http"] += 1
            prompts.append(p)
            thinks.append(d.get("think"))
            if ctl["think_500"] and "think" in d:
                b = json.dumps({"error": f'"{model}" does not support thinking'}).encode()
                self.send_response(500); self.send_header("Content-Length", str(len(b))); self.end_headers()
                self.wfile.write(b)
                return
            if ctl["cham"]:
                import time
                time.sleep(ctl["cham"])
            if ctl["ctx_day"]:
                return self._send({"message": {"content": "{}"}, "prompt_eval_count": d["options"]["num_ctx"], "eval_count": 1})
            if ctl["loi_mang"] > 0:
                ctl["loi_mang"] -= 1
                self.send_response(503); self.send_header("Content-Length", "0"); self.end_headers()
                return
            if ctl["json_hong"] > 0:
                ctl["json_hong"] -= 1
                return self._send({"message": {"content": "Xin lỗi, tôi không chắc"}, "prompt_eval_count": 10, "eval_count": 5})
            if "CHỨNG TỪ CẦN ĐỌC" in p:                          # đọc dòng hàng chứng từ: trả câu đặt sẵn
                calls["chung_tu"] = calls.get("chung_tu", 0) + 1
                return self._send({"message": {"content": json.dumps(ctl.get("chung_tu") or {"dong": []}, ensure_ascii=False)},
                                   "prompt_eval_count": len(p) // 3, "eval_count": 100})
            if "PHỤ LỤC HỢP ĐỒNG CẦN PHÂN TÍCH" in p:           # trích phụ lục: trả câu trả lời đặt sẵn trong ctl
                calls["phu_luc"] = calls.get("phu_luc", 0) + 1
                return self._send({"message": {"content": json.dumps(ctl["phu_luc"], ensure_ascii=False)},
                                   "prompt_eval_count": len(p) // 3, "eval_count": 100})
            codes = re.findall(r"^- ((?:TC|TT|Y)-\d+) \|", p, re.M)
            if "MỤC LỤC HỢP ĐỒNG" in p:
                calls["locate"] += 1
                toc = p.split("MỤC LỤC HỢP ĐỒNG:")[1].strip().split("\n")
                out = []
                for c in codes:
                    desc = re.search(rf"^- {c} \| (.+)$", p, re.M).group(1).lower()
                    word = desc.split()[0] if desc else ""
                    out.append({"ma": c, "ids": [l.split(" | ")[0] for l in toc if word and word in l.lower()][:3]})
                return self._send({"message": {"content": json.dumps({"vi_tri": out}, ensure_ascii=False)}})
            calls["chat"] += 1
            # chọn bộ đáp án có nhiều giá trị xuất hiện trong prompt nhất
            best = max(keys.values(), key=lambda k: sum(1 for r in k.values() if r[3] and r[3] in p)) if keys else {}
            out = []
            for c in codes:
                r = best.get(c)
                if r:
                    out.append({"ma": c, "gia_tri": r[3], "don_vi": r[4], "dieu_khoan": r[5],
                                "trich_dan": wrong.get(c, r[6]), "ghi_chu": r[7]})
                    if c in ctl["sai_lan_dau"]:        # lần đầu hỏi mã này: trả trích dẫn sai (để thử lượt rà lại)
                        ctl["sai_lan_dau"].discard(c)
                        out[-1]["trich_dan"] = "Câu này không có trong hợp đồng " + c
                else:
                    out.append({"ma": c, "gia_tri": "Không quy định", "don_vi": "", "dieu_khoan": "", "trich_dan": "", "ghi_chu": ""})
            self._send({"message": {"content": json.dumps({"ket_qua": out}, ensure_ascii=False)},
                        "prompt_eval_count": len(p) // 3, "eval_count": 300})

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    srv.calls, srv.ctl, srv.prompts, srv.thinks = calls, ctl, prompts, thinks
    return srv, srv.server_address[1]
