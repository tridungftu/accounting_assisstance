# -*- coding: utf-8 -*-
"""
may_ai.py - Cấu hình và dò tìm máy Local AI (Ollama) trong mạng LAN. Chỉ dùng thư viện chuẩn Python.

Dùng cho trang Cài đặt (kiểm tra kết nối, tự tìm máy AI). Cấu hình lưu ở cau_hinh.py (cau_hinh_may_ai.json).
"""
import concurrent.futures
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.request

CONG_MAC_DINH = 11434


def chuan_host(ip, cong=CONG_MAC_DINH):
    """'192.168.5.67' -> 'http://192.168.5.67:11434'."""
    ip = str(ip).strip().replace("http://", "").replace("https://", "").rstrip("/")
    if ":" in ip:
        ip, cong = ip.rsplit(":", 1)
    return f"http://{ip}:{int(cong)}"


def tach_host(url):
    """'http://192.168.5.67:11434' -> ('192.168.5.67', 11434)."""
    m = re.match(r"^(?:https?://)?([^:/]+)(?::(\d+))?", str(url).strip())
    return (m.group(1), int(m.group(2) or CONG_MAC_DINH)) if m else ("", CONG_MAC_DINH)


def ip_hop_le(ip):
    try:
        ipaddress.IPv4Address(str(ip).strip())
        return True
    except ValueError:
        return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", str(ip).strip()))


# ------------------------------------------------------------------ mạng
def ip_may_nay():
    """Các IPv4 trong mạng LAN của máy này (bỏ 127.x, 169.254.x)."""
    ds = []
    try:  # cách này không gửi gói tin nào, chỉ hỏi hệ điều hành đi ra mạng bằng card nào
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ds.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        ds += socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        pass
    out = []
    for ip in ds:
        if ip not in out and not ip.startswith(("127.", "169.254.")):
            out.append(ip)
    return out


def danh_sach_model(host, timeout=4):
    """Trả về list tên model trên máy AI; lỗi kết nối thì raise."""
    with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=timeout) as r:
        return [m.get("name") for m in json.loads(r.read()).get("models", [])]


def thu_tra_loi(host, model, timeout=180):
    """Hỏi thử model một câu ngắn. Trả về số giây. Model không hỗ trợ 'think' thì hỏi lại không có 'think'."""
    body = {"model": model, "stream": False, "think": False, "options": {"temperature": 0, "num_predict": 10},
            "messages": [{"role": "user", "content": "Trả lời đúng một từ: OK"}]}
    t0 = time.time()
    for lan in range(2):
        req = urllib.request.Request(host.rstrip("/") + "/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                json.loads(r.read())
            return round(time.time() - t0, 1)
        except urllib.error.HTTPError as e:
            if lan == 0 and e.code in (400, 500):
                body.pop("think", None)
                continue
            raise
    return round(time.time() - t0, 1)


def kiem_tra(host, model=None, thu_model=True):
    """Kiểm tra một máy AI. Trả về dict: ok, models, co_model, giay, loi."""
    kq = dict(ok=False, models=[], co_model=False, giay=None, loi="")
    try:
        kq["models"] = danh_sach_model(host)
    except Exception as e:
        kq["loi"] = f"Không kết nối được {host} ({e.__class__.__name__})"
        return kq
    if model:
        kq["co_model"] = model in kq["models"] or f"{model}:latest" in kq["models"]
        if not kq["co_model"]:
            kq["loi"] = f"Máy AI chưa có model '{model}'"
            return kq
        if thu_model:
            try:
                kq["giay"] = thu_tra_loi(host, model)
            except Exception as e:
                kq["loi"] = f"Model không trả lời được ({e})"
                return kq
    kq["ok"] = True
    return kq


def _mo_cong(ip, cong, timeout):
    try:
        with socket.create_connection((ip, cong), timeout=timeout):
            return True
    except OSError:
        return False


def tim_may_ai(cong=CONG_MAC_DINH, timeout=0.4, tien_do=None):
    """Dò các máy trong cùng mạng /24 với máy này đang mở cổng Ollama.
    Trả về list (ip, [model...]). tien_do(da_xong, tong) để báo tiến độ (tuỳ chọn)."""
    ung_vien = []
    for ip in ip_may_nay():
        net = ipaddress.IPv4Network(ip + "/24", strict=False)
        ung_vien += [str(h) for h in net.hosts()]
    ung_vien = list(dict.fromkeys(ung_vien))
    mo = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=96) as ex:
        fut = {ex.submit(_mo_cong, ip, cong, timeout): ip for ip in ung_vien}
        for i, f in enumerate(concurrent.futures.as_completed(fut), 1):
            if f.result():
                mo.append(fut[f])
            if tien_do and (i % 16 == 0 or i == len(ung_vien)):
                tien_do(i, len(ung_vien))
    out = []
    for ip in sorted(mo, key=lambda x: tuple(int(p) for p in x.split("."))):
        try:
            out.append((ip, danh_sach_model(f"http://{ip}:{cong}", timeout=3)))
        except Exception:
            pass  # cổng mở nhưng không phải Ollama
    return out
