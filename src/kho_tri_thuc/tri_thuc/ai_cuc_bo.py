"""AI cục bộ (tầng 4, tùy chọn) — chỉ gợi ý, chạy trên máy, không gọi dịch vụ ngoài.

Phần mềm không cần AI để nhận diện tên: mô-đun ``ten_doi_tuong`` giải quyết
bằng chuẩn hóa và so khớp. AI cục bộ chỉ được hỏi khi so khớp cho ra NHIỀU
ứng viên, để xếp hạng lại; câu trả lời luôn ở mức yếu (Vàng), người duyệt
quyết.

Kết nối theo chuẩn OpenAI-compatible (LM Studio, Ollama, llama.cpp đều có),
nhưng chỉ chấp nhận địa chỉ trên chính máy này (localhost / 127.0.0.1).  Tắt
mặc định; bật trong ``source-settings.json`` → ``settings.local_ai``.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

DEFAULTS = {"enabled": False, "url": "http://127.0.0.1:1234/v1/chat/completions", "model": "", "timeout_seconds": 8}
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def local_ai_settings(settings: dict | None) -> dict:
    value = dict(DEFAULTS)
    raw = (settings or {}).get("local_ai")
    if isinstance(raw, dict):
        for key in DEFAULTS:
            if key in raw and raw[key] is not None:
                value[key] = raw[key]
    value["enabled"] = bool(value["enabled"]) and _is_local(str(value["url"]))
    try:
        value["timeout_seconds"] = max(1, min(30, int(value["timeout_seconds"])))
    except (TypeError, ValueError):
        value["timeout_seconds"] = DEFAULTS["timeout_seconds"]
    return value


def _is_local(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and (parsed.hostname or "") in _LOCAL_HOSTS


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _ask(settings: dict, prompt: str, transport=None) -> str:
    """One chat completion; ``transport`` is injectable for tests."""
    body = json.dumps({"model": settings.get("model") or "local", "temperature": 0,
                       "messages": [{"role": "system", "content": "Bạn là trợ lý kế toán. Chỉ trả lời đúng định dạng được yêu cầu."},
                                    {"role": "user", "content": prompt}]}).encode("utf-8")
    if transport is not None:
        return str(transport(settings["url"], body) or "")
    request = urllib.request.Request(settings["url"], data=body, headers={"Content-Type": "application/json"}, method="POST")
    opener = urllib.request.build_opener(_NoRedirect())  # a local server must not send the request elsewhere
    with opener.open(request, timeout=settings["timeout_seconds"]) as response:  # noqa: S310 - localhost only, checked above
        payload = json.loads(response.read(2_000_000).decode("utf-8"))
    try:
        return str(payload["choices"][0]["message"]["content"] or "")
    except (KeyError, IndexError, TypeError):
        return ""


def choose_counterparty(settings: dict, statement_name: str, description: str, options: list[dict], transport=None) -> dict | None:
    """Hỏi AI cục bộ chọn một mã trong các ứng viên; None khi tắt, lỗi hoặc không chắc.

    Kết quả: ``{"code", "reason"}``.  Mã trả về bắt buộc nằm trong ``options``.
    """
    settings = local_ai_settings({"local_ai": settings} if settings and "enabled" in settings else settings)
    if not settings["enabled"] or len(options) < 2:
        return None
    codes = {str(item.get("code")): str(item.get("name") or "") for item in options if item.get("code")}
    if len(codes) < 2:
        return None
    listing = "\n".join(f"- {code}: {name}" for code, name in codes.items())
    prompt = ("Tên đối tác trên sao kê ngân hàng: \"" + (statement_name or "(không có)") + "\".\n"
              "Diễn giải giao dịch: \"" + (description or "") + "\".\n"
              "Các mã đối tượng có thể đúng (mã: tên trong danh mục):\n" + listing + "\n"
              "Chọn đúng một mã khớp với tên trên sao kê. Nếu không chắc, trả lời KHONG.\n"
              "Trả lời đúng một dòng dạng: MA=<mã> | LY_DO=<một câu ngắn>")
    try:
        answer = _ask(settings, prompt, transport)
    except Exception:  # noqa: BLE001 - a hint source must never break a proposal
        return None
    found = re.search(r"MA\s*=\s*([^|\n]+)", answer or "")
    code = found.group(1).strip() if found else ""
    if not code or code.upper() == "KHONG" or code not in codes:
        return None
    reason = re.search(r"LY_DO\s*=\s*(.+)", answer or "")
    return {"code": code, "reason": (reason.group(1).strip() if reason else "")[:200]}
