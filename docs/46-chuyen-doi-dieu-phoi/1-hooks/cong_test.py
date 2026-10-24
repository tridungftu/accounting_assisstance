"""Hook Stop của worker: không cho worker kết thúc khi test đỏ.

Exit 2 = chặn kết thúc, kết quả test in ra stderr để worker sửa tiếp.
Lệnh test đọc từ .claude/lenh-test.txt (một dòng) — lead điền sau khi kiểm trên máy Anh.
Bản nháp 23/10/2026.
"""
import pathlib
import subprocess
import sys

MAC_DINH = "powershell -NoProfile -ExecutionPolicy Bypass -File test.ps1"
GIOI_HAN_GIAY = 900  # [LEAD ĐO LẠI] thời gian chạy toàn bộ test trên máy Anh


def main() -> int:
    tep = pathlib.Path(".claude/lenh-test.txt")
    lenh = tep.read_text(encoding="utf-8").strip() if tep.exists() else MAC_DINH
    try:
        kq = subprocess.run(lenh, shell=True, capture_output=True, text=True,
                            timeout=GIOI_HAN_GIAY, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        print(f"Test vượt {GIOI_HAN_GIAY} giây — báo lead, không coi là đạt.", file=sys.stderr)
        return 2
    if kq.returncode != 0:
        duoi = (kq.stdout + kq.stderr)[-3000:]
        print("Test chưa xanh, chưa được kết thúc lát:\n" + duoi, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
