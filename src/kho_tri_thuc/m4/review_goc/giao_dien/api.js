// api.js — gọi API máy chủ cục bộ (xem API.md) và các hàm định dạng dùng chung.
export async function api(method, url, body, file) {
  const o = { method, headers: { "X-HD": "1" } };
  if (file) o.body = file;
  else if (body !== undefined) {
    o.body = JSON.stringify(body);
    o.headers["Content-Type"] = "application/json";
  }
  let r;
  try {
    r = await fetch(url, o);
  } catch (e) {
    throw new LoiApi("Không kết nối được phần mềm trên máy — cửa sổ đen CHAY_PHAN_MEM còn mở không?", 0);
  }
  let d = {};
  try {
    d = await r.json();
  } catch (e) {
    d = {};
  }
  if (!r.ok) throw new LoiApi(d.loi || `Lỗi ${r.status}`, r.status, d.chi_tiet);
  return d;
}
export class LoiApi extends Error {
  constructor(msg, status, chiTiet) {
    super(msg);
    this.status = status;
    this.chiTiet = chiTiet;
  }
}
export const get = (u) => api("GET", u);
export const post = (u, b) => api("POST", u, b === undefined ? {} : b);
export const upload = (u, file) => api("POST", u, undefined, file);

// chờ một việc nền (toàn vẹn, kiểm tra đợt, tìm máy AI) xong
export async function choViec(id, onTick, ms = 1200) {
  for (;;) {
    const v = await get(`/api/viec/${encodeURIComponent(id)}`);
    onTick?.(v);
    if (!["cho", "dang_chay"].includes(v.tt)) return v;
    await new Promise((r) => setTimeout(r, ms));
  }
}

const nf0 = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });
const nf3 = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 3 });
export const money = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? "—" : nf0.format(Math.round(Number(v))));
export const num = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? "—" : nf3.format(Number(v)));
export const pct = (v) => (v === null || v === undefined || isNaN(Number(v)) ? "—" : nf3.format(Number(v) * 100) + "%");
export const fmtDate = (iso) => {
  if (!iso) return "—";
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : String(iso);
};
export const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export const clock = (sec) => {
  sec = Math.max(0, Math.round(sec || 0));
  return `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;
};
export const duration = (sec) => {
  sec = Math.max(0, Math.round(sec || 0));
  const m = Math.floor(sec / 60);
  return m ? `${m} phút ${sec % 60} giây` : `${sec} giây`;
};
export const timeOf = (epoch) => {
  if (!epoch) return ["—", ""];
  const d = new Date(epoch * 1000);
  const t = d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", hour12: false });
  const isToday = d.toDateString() === new Date().toDateString();
  return [t, isToday ? "Hôm nay" : d.toLocaleDateString("vi-VN")];
};
export const size = (b) => (b > 1048576 ? `${(b / 1048576).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);
export const isOk = (kt) => String(kt || "").startsWith("OK");
