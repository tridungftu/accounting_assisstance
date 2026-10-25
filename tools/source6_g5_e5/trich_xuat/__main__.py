"""Lệnh quản lý danh mục tại bản vá engine #6 (offline)."""
import argparse
import sys

from .danh_muc import HEADER, KHOA, danh_muc_theo_loai, read_catalog, sua_danh_muc


class BoDocLenh(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, f"Lỗi cú pháp lệnh: {message}\n")


def main(argv=None):
    parser = BoDocLenh(description="Xem và sửa danh mục tham số theo loại hợp đồng")
    commands = parser.add_subparsers(dest="lenh", required=True)
    catalog = commands.add_parser("danh-muc", help="Quản lý danh mục tham số")
    actions = catalog.add_subparsers(dest="thao_tac", required=True)
    view = actions.add_parser("xem", help="Xem bảng tham số")
    view.add_argument("loai")
    edit = actions.add_parser("sua", help="Sửa một trường và ghi nhật ký")
    edit.add_argument("loai")
    edit.add_argument("ma_tham_so")
    for flag in ("truong", "gia-tri", "nguoi", "ly-do"):
        edit.add_argument("--" + flag, required=True)
    args = parser.parse_args(argv)
    try:
        if args.thao_tac == "xem":
            path = danh_muc_theo_loai(args.loai)
            print(f"Danh mục tham số loại {args.loai}")
            print(" | ".join(HEADER))
            for row in read_catalog(path):
                print(" | ".join(("Có" if row[k] else "Không") if isinstance(row[k], bool)
                                 else str(row[k]).replace("\n", " ") for k in KHOA))
        else:
            version = sua_danh_muc(args.loai, args.ma_tham_so, args.truong,
                                   args.gia_tri, args.nguoi, args.ly_do)
            print(f"Đã lưu danh mục loại {args.loai}; phiên bản: {version}")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Lỗi danh mục: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
