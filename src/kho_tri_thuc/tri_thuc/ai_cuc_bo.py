"""AI cục bộ (tầng 4, tùy chọn) — chỉ gợi ý, không gọi dịch vụ ngoài.

Phần mềm không cần AI để nhận diện tên: mô-đun ``ten_doi_tuong`` giải quyết
bằng chuẩn hóa và so khớp. AI cục bộ chỉ được hỏi khi so khớp cho ra NHIỀU
ứng viên, để xếp hạng lại; câu trả lời luôn ở mức yếu (Vàng), người duyệt
quyết.

Kết nối OpenAI-compatible (LM Studio, llama.cpp; với Ollama dùng endpoint
``/v1/chat/completions`` tương thích OpenAI, không dùng client riêng).
Chỉ IP loopback, RFC1918 hoặc Tailscale; link-local bị tắt. Không DNS, HTTPS,
proxy hay chuyển hướng. Tắt mặc định; bật trong ``source-settings.json`` →
``settings.local_ai``. URL phải gồm cổng và đường dẫn /v1/chat/completions.
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

DEFAULTS = {"enabled": False, "url": "http://127.0.0.1:1234/v1/chat/completions", "model": "", "timeout_seconds": 8}
_CONNECTION_FAILURES: dict[str, float] = {}  # Chỉ URL và mốc lỗi, không lưu nội dung AI.
_CONNECTION_RETRY_SECONDS = 15
_TAILSCALE = tuple(ipaddress.ip_network(n) for n in ("100.64.0.0/10", "fd7a:115c:a1e0::/48"))
_ALLOWED_NETWORKS = tuple(ipaddress.ip_network(n) for n in (
    "127.0.0.0/8", "::1/128", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
)) + _TAILSCALE


def _parse_url(url: str):
    shape = "Địa chỉ Local AI phải là http://<IP>:<cổng>/v1/chat/completions; không dùng HTTPS hoặc proxy."
    try:
        if any(c.isspace() or ord(c) < 32 for c in url):
            raise ValueError(shape)
        parsed = urlparse(url)
        if (parsed.scheme != "http" or not parsed.port or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment or parsed.params
                or parsed.path != "/v1/chat/completions" or "%" in (parsed.hostname or "")):
            raise ValueError(shape)
    except ValueError:
        raise ValueError(shape) from None
    if parsed.hostname == "localhost":
        parsed = parsed._replace(netloc=f"127.0.0.1:{parsed.port}")
    try:
        address = ipaddress.ip_address(parsed.hostname or "")
    except ValueError:
        raise ValueError("Hãy dùng IP của máy AI hoặc localhost, không dùng tên miền; Local AI không tra DNS.") from None
    if not any(address in network for network in _ALLOWED_NETWORKS):
        raise ValueError("Hãy dùng IP máy này, mạng nội bộ RFC1918 hoặc Tailscale (100.64.0.0/10); "
                         "không dùng IP công cộng hoặc link-local.")
    return parsed


def _is_tailscale(host: str) -> bool:
    return any(ipaddress.ip_address(host) in network for network in _TAILSCALE)


def source_address(host: str, port: int) -> str:
    """Hỏi đường đi của hệ điều hành; UDP connect tới IP không gửi gói tin."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_DGRAM) as probe:
        probe.connect((host, port))
        return probe.getsockname()[0]


def _route_source(host: str, port: int) -> str | None:
    if not _is_tailscale(host):
        return None
    try:
        source = source_address(host, port)
        if _is_tailscale(source):
            return source
    except (OSError, ValueError):
        pass
    raise ValueError("Hãy bật Tailscale trên máy này và kết nối lại máy AI; đích Tailscale phải đi từ IP Tailscale.")


def _model_problem(entry: dict) -> str:
    if (entry.get("remote_host") or entry.get("remote_model")
            or any("cloud" in str(entry.get(key) or "").casefold() for key in ("id", "name", "model"))):
        return "Model chạy trên cloud hoặc có remote_host/remote_model; hãy chọn model chạy trên máy AI."
    return ""


def local_ai_settings(settings: dict | None) -> dict:
    value = dict(DEFAULTS)
    raw = (settings or {}).get("local_ai")
    if isinstance(raw, dict):
        for key in DEFAULTS:
            if key in raw and raw[key] is not None:
                value[key] = raw[key]
    value["error"] = ""
    try:
        value["url"] = _parse_url(str(value["url"])).geturl()
        problem = _model_problem(raw if isinstance(raw, dict) else value)
        if problem:
            raise ValueError(problem)
    except ValueError as exc:
        value["error"] = str(exc)
    value["enabled"] = bool(value["enabled"]) and not value["error"]
    try:
        value["timeout_seconds"] = max(1, min(30, int(value["timeout_seconds"])))
    except (TypeError, ValueError):
        value["timeout_seconds"] = DEFAULTS["timeout_seconds"]
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


class _IPConnection(http.client.HTTPConnection):
    """Kết nối socket thẳng tới IP đã kiểm tra, không gọi getaddrinfo/DNS."""

    def __init__(self, host, *, source=None, **kwargs):
        super().__init__(host, **kwargs)
        self._source = source

    def connect(self):
        family = socket.AF_INET6 if ":" in self.host else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            if self._source:
                sock.bind((self._source, 0))  # Giữ nguồn Tailscale kể cả khi bảng định tuyến đổi.
            sock.connect((self.host, self.port))
        except Exception:
            sock.close()
            raise
        self.sock = sock


class _IPHandler(urllib.request.HTTPHandler):
    def __init__(self, source):
        super().__init__()
        self._source = source

    def http_open(self, req):
        return self.do_open(lambda host, **kw: _IPConnection(host, source=self._source, **kw), req)


class _LocalAIUnavailable(ValueError):
    """Lỗi kết nối có thể thử lại sau khoảng nghỉ ngắn."""


def _read_json(opener, url: str, timeout: int, body: bytes | None = None):
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(2_000_001)
    except urllib.error.URLError as exc:
        if isinstance(exc, urllib.error.HTTPError):
            raise
        raise _LocalAIUnavailable("Chưa kết nối được máy AI; hãy kiểm tra IP, cổng, LAN/Tailscale và bật máy AI.") from exc
    except (OSError, http.client.HTTPException) as exc:
        raise _LocalAIUnavailable("Chưa kết nối được máy AI; hãy kiểm tra IP, cổng, LAN/Tailscale và bật máy AI.") from exc
    if len(raw) > 2_000_000:
        raise ValueError("Phản hồi Local AI quá lớn; hãy kiểm tra máy AI.")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise ValueError("Máy AI trả dữ liệu không hợp lệ; hãy dùng endpoint tương thích OpenAI.") from None


def _check_model(opener, settings: dict):
    """Kiểm metadata không mang nội dung kế toán trước khi gửi prompt."""
    root = settings["url"].removesuffix("/v1/chat/completions")
    model = str(settings.get("model") or "local")
    try:
        payload = _read_json(opener, root + "/v1/models", settings["timeout_seconds"])
    except urllib.error.HTTPError as exc:
        exc.close()
        raise ValueError("Không đọc được danh sách model; hãy bật endpoint /v1/models tương thích OpenAI "
                         "trên máy AI, không chuyển hướng.") from None
    entries = payload.get("data", []) if isinstance(payload, dict) else []
    if not isinstance(entries, list):
        entries = []
    entry = next((m for m in entries if isinstance(m, dict)
                  and str(m.get("id") or "").removesuffix(":latest") == model.removesuffix(":latest")), None)
    if entry is None:
        raise ValueError("Máy AI chưa có model đã chọn; hãy tải model và đặt đúng tên trong cài đặt Local AI.")
    problem = _model_problem(entry)
    if problem:
        raise ValueError(problem)
    # Ollama có thể không công bố remote_host trong /v1/models. Dùng metadata
    # /api/tags nếu có; các máy OpenAI-compatible khác thường trả 404/405.
    try:
        tags = _read_json(opener, root + "/api/tags", settings["timeout_seconds"])
    except urllib.error.HTTPError as exc:
        exc.close()
        if exc.code in (404, 405):
            return
        raise ValueError("Không kiểm tra được model; hãy kiểm tra dịch vụ Local AI.") from None
    entries = tags.get("models") if isinstance(tags, dict) else None
    if not isinstance(entries, list):
        return  # LM Studio có thể trả 200 cho đường dẫn không phải của Ollama.
    entry = next((m for m in entries if isinstance(m, dict) and any(
        str(m.get(key) or "").removesuffix(":latest") == model.removesuffix(":latest")
        for key in ("name", "model"))), None)
    if entry is None:
        raise ValueError("Không xác minh được model trên máy AI; hãy chọn model đã cài cục bộ.")
    problem = _model_problem(entry)
    if problem:
        raise ValueError(problem)


def _ask(settings: dict, prompt: str, transport=None) -> str:
    """One chat completion; ``transport`` is injectable for tests."""
    parsed = _parse_url(str(settings["url"]))
    settings = {**settings, "url": parsed.geturl()}
    problem = _model_problem(settings)
    if problem:
        raise ValueError(problem)
    source = _route_source(parsed.hostname, parsed.port)
    body = json.dumps({"model": settings.get("model") or "local", "temperature": 0,
                       "messages": [{"role": "system", "content": "Bạn là trợ lý kế toán. Chỉ trả lời đúng định dạng được yêu cầu."},
                                    {"role": "user", "content": prompt}]}).encode("utf-8")
    if transport is not None:
        return str(transport(settings["url"], body) or "")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect(), _IPHandler(source))
    _check_model(opener, settings)
    try:
        payload = _read_json(opener, settings["url"], settings["timeout_seconds"], body)
    except urllib.error.HTTPError as exc:
        exc.close()
        raise ValueError("Máy AI từ chối trả lời; hãy kiểm tra model và endpoint /v1/chat/completions "
                         "tương thích OpenAI, không chuyển hướng.") from None
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
    now = time.monotonic()
    for url, failed_at in tuple(_CONNECTION_FAILURES.items()):
        if now - failed_at >= _CONNECTION_RETRY_SECONDS:
            _CONNECTION_FAILURES.pop(url, None)
    if settings["url"] in _CONNECTION_FAILURES:
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
    except (_LocalAIUnavailable, OSError, http.client.HTTPException):
        _CONNECTION_FAILURES[settings["url"]] = time.monotonic()
        return None
    except Exception:  # noqa: BLE001 - a hint source must never break a proposal
        return None
    _CONNECTION_FAILURES.pop(settings["url"], None)
    found = re.search(r"MA\s*=\s*([^|\n]+)", answer or "")
    code = found.group(1).strip() if found else ""
    if not code or code.upper() == "KHONG" or code not in codes:
        return None
    reason = re.search(r"LY_DO\s*=\s*(.+)", answer or "")
    return {"code": code, "reason": (reason.group(1).strip() if reason else "")[:200]}
