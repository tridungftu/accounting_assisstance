"""Hook PreToolUse: chặn lệnh xóa và mọi thao tác vào kho thật / .env.

Exit 2 = chặn, lý do in ra stderr để Claude đọc và đổi cách làm.
Bản nháp 23/10/2026 — lead chạy thử trên máy Anh trước khi bật.
"""
import json
import re
import sys

LENH_CAM = [
    r"(^|[\s;&|])rm\s", r"(^|[\s;&|])rmdir\s", r"(^|[\s;&|])del\s",
    r"Remove-Item", r"git\s+clean", r"git\s+reset\s+--hard",
    r"git\s+push\s+.*--force", r"shutil\.rmtree", r"os\.remove", r"unlink\(",
]
DUONG_CAM = [
    r"var/plhn-that", r"var/web-that", r"cau_hinh\.that\.toml",
    r"(^|[/\s'\"])\.env(?!\.example)(\.[A-Za-z0-9_-]+)?($|[\s'\"])",
]


def main() -> int:
    # Windows mặc định cp1252: đọc/ghi UTF-8 để không lỗi phông và không bỏ sót đường dẫn có dấu.
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        du_lieu = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except Exception:
        return 0
    vao = du_lieu.get("tool_input", {}) or {}
    van_ban = " ".join(str(vao.get(k, "")) for k in ("command", "file_path", "path"))
    van_ban = van_ban.replace("\\", "/")

    for mau in LENH_CAM:
        if re.search(mau, van_ban, flags=re.IGNORECASE):
            print(f"Chặn: quy tắc không xóa file (khớp '{mau}'). "
                  "Cần bỏ file thì báo lead để chuyển vào thư mục lưu trữ.", file=sys.stderr)
            return 2
    for duong in DUONG_CAM:
        if re.search(duong, van_ban, flags=re.IGNORECASE):
            print("Chặn: đường dẫn thuộc kho thật hoặc tệp bí mật, "
                  "không được đọc/sửa qua công cụ.", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
