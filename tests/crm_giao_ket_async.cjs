"use strict";
// CRM-41-03 — kiểm bất đồng bộ trên MÃ THẬT app.js + crm_g.js (khối #crm-gk G2/G3), không phải trình duyệt: DOM giả tối thiểu có quan hệ cha–con/kết nối
// thật, fetch trả Promise do ca điều khiển (treo, đảo thứ tự, mất kết nối, blob trễ). CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN).
// Root chạy: `node tests/crm_giao_ket_async.cjs` (Node ≥ 18). Mã thoát 0 = mọi ca đạt. Không ghi/xóa tệp, không mạng, không tiến trình con.
// Ca (dương trước âm):
//  P0  dương: nạp danh sách → Mở báo giá → form ghi đúng dữ liệu máy chủ → Lưu nháp gửi body typed + khóa → kết quả → làm mới.
//  A1  bấm lặp khi POST còn chờ → 0 POST thêm; mất kết nối → nút "Gửi lại y nguyên" gửi ĐÚNG body + khóa cũ; kết quả rõ → khóa nhả.
//  A2  POST lưu A còn chờ → mở "+ Báo giá mới" và gõ → A về trễ: không GET chi tiết A, không đè form mới.
//  A3  ↻ Làm mới (GET chi tiết treo) → người dùng gõ → GET về: không ghi đè nháp đang gõ.
//  A4  đổi vai khi POST còn chờ: barrier xóa đồng bộ; POST cũ về trễ không làm mới/không gắn vào vai mới.
//  A5  tải DOCX: blob về sau khi đổi vai → không click tải xuống.
// FIX01 (thêm, không nới A1–A5):
//  A6  POST lưu còn chờ → "+ Báo giá mới" + gõ → POST về LỖI muộn: không toast/trạng thái lỗi cũ, không nút gửi lại, form mới giữ.
//  A7  có thay đổi chưa lưu → In/Chuyển vô hiệu NGAY + lý do, 0 POST in; Lưu luôn bật; lưu + nạp revision → In bật lại; cổng In (chan_in) KHÔNG
//      khóa Lưu/Chuyển.
//  A8  nạp G7 có AMOUNT: VND scale 0 + USD scale 2 (kể cả 5 minor = 0.05) giữ đúng số tiền/tiền tệ/loại/thứ tự/mốc/ghi chú; body Lưu mang
//      đúng; tiền tệ lạ → không nạp, lịch giữ.
//  A9  Tính thử: POST xem-truoc chỉ {du_lieu} (không khóa); phía tự tính chỉ đọc theo dòng + VND tham chiếu; kết quả cũ/về muộn sau khi gõ
//      không hiển thị cho form đã đổi.
//  A10 G3: ↻ Làm mới treo → gõ trường → danh sách về: không GET chi tiết đè; Xuất vô hiệu khi chưa lưu; POST Lưu G3 mất kết nối sau khi
//      đổi tab → không nút gửi lại/thông báo cũ.
// FIX02 (connected-handler, giữ nguyên P0/A1–A10):
//  B1  mất ACK → gửi lại → 409 CRM_GK_DANG_XU_LY / CRM_GK_LAN_KHONG_KHOP: giữ ĐÚNG body + khóa gốc (kể cả bấm lại nút In) tới FINAL; không tự
//      gửi lại; 409 xác định (IDEMPOTENCY_KHAC / REVISION_CU) → nhả khóa, không nút đối soát.
//  B2  Chuyển còn chờ → gõ cùng báo giá → thành công/lỗi về muộn: không đổi chế độ/lựa chọn, không GET danh sách/bản soạn, không thông báo cũ;
//      dương (không gõ) → sang G3.
//  B4  G3 chỉ đổi mẫu → bẩn, Xuất khóa + lý do; Lưu mang mẫu/lý do/revision; Xuất chỉ mở khi revision mới đã nạp; Xuất về muộn sau khi gõ im lặng.
//  B3  Lưu mất ACK → gửi lại còn chờ → gõ tiếp → FINAL: im lặng, không làm mới; lần lưu sau dùng khóa mới + revision đã ghi nhận; G7 lỗi muộn im lặng.
//  B5  (BG-1b, thay "Tính thử") lỗi mạng giữ kết quả cũ + một dòng báo, máy tự thử lại; lỗi 4xx hiện câu lỗi; ghi chú/mô tả không gọi máy chủ.
// BG-1b (màn Báo giá gói 1: BG-01…BG-05; thay A8/A9/B5 cũ của "Tính thử"; timer GIẢ — `tien(ms)` — để kiểm "ngừng gõ 400 ms"):
//  A8  nạp G7 vào lịch MỘT ô Giá trị (`30%`, `1.234,56`) + mốc một ô; khác tiền tệ báo giá → KHÔNG nạp (không ngầm hiểu USD thành VND).
//  A9  lịch ≤ 3 ô nhập/dòng, 0 nút tính; gõ → "…" rồi sau 400 ms gọi xem-truoc; rời ô (change) → gọi ngay + đổi dạng `450000` → `450.000`; phản hồi cũ bị bỏ;
//      Σ% / Σ tiền / nút In-Chuyển mờ kèm lý do; cập nhật tại chỗ (không vẽ lại form).
//  A11 mốc một ô (Bàn giao · dd/mm/yyyy · Xây xong tầng n · Sau ký + n ngày), mã lạ gửi lại nguyên, mốc không hiểu chặn Lưu; thêm/đổi chỗ/bỏ dòng, Lần tự đánh số.
//  A12 Tổng giá trị tự tính (để trống) / ghi đè (gửi nguyên chuỗi người gõ + cảnh báo + lưu ý ký) / lỗi theo trường của máy chủ.
//  A13 BG-05: không mã kỹ thuật, ngày dd/mm/yyyy, số có dấu chấm; chuỗi % xấp xỉ của máy chủ hiện nguyên.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");
const APP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/app.js"), "utf8");
const CRMG = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/crm_g.js"), "utf8");
const ID_TINH = new Set([...fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/index.html"), "utf8").matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const BLOB_GOC = globalThis.Blob || require("buffer").Blob;
const loiNgoai = [];
process.on("unhandledRejection", e => { loiNgoai.push(e); });

let soClickTai = 0;
function moiTruong() {
  const reg = new Map(), dongId = new Set();
  let taoTinh = false;
  class El {
    constructor(tag) { this.tagName = String(tag).toUpperCase(); this.children = []; this.parent = null; this._text = ""; this._id = ""; this.listeners = {};
      this.attrs = {}; this.dataset = {}; this.style = {}; this._cls = new Set(); this.files = []; this.disabled = false; this.checked = false; this.selected = false;
      this._value = ""; this._valueSet = false; this.type = ""; this.title = ""; this.placeholder = ""; }
    get id() { return this._id; }
    set id(v) { this._id = v; if (!reg.has(v)) reg.set(v, []); reg.get(v).push(this); if (!taoTinh) dongId.add(v); }
    get isConnected() { let e = this; while (e) { if (e === body) return true; e = e.parent; } return false; }
    get className() { return [...this._cls].join(" "); }
    set className(v) { this._cls = new Set(String(v || "").split(/\s+/).filter(Boolean)); }
    get classList() { const s = this; return {add: (...c) => c.forEach(x => s._cls.add(x)), remove: (...c) => c.forEach(x => s._cls.delete(x)),
      toggle: (c, on) => { const v = on === undefined ? !s._cls.has(c) : on; if (v) s._cls.add(c); else s._cls.delete(c); return v; }, contains: c => s._cls.has(c)}; }
    get value() { if (this.tagName === "SELECT" && !this._valueSet) { const ops = this.children.filter(c => c.tagName === "OPTION"); const s = ops.find(o => o.selected) || ops[0]; return s ? s.value : ""; } return this._value; }
    set value(v) { this._value = String(v ?? ""); this._valueSet = true; }
    get textContent() { return this._text + this.children.map(c => c.textContent).join(""); }
    set textContent(v) { for (const c of this.children) c.parent = null; this._text = String(v ?? ""); this.children = []; }
    _con(n) { const c = typeof n === "string" ? Object.assign(new El("#text"), {_text: n}) : n; if (c.parent) c.parent.children = c.parent.children.filter(x => x !== c); c.parent = this; return c; }
    append(...n) { for (const x of n) this.children.push(this._con(x)); }
    prepend(...n) { this.children.unshift(...n.map(x => this._con(x))); }
    replaceChildren(...n) { for (const c of this.children) c.parent = null; this._text = ""; this.children = []; this.append(...n); }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(x => x !== this); this.parent = null; }
    addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
    dispatch(t, ev = {}) { return (this.listeners[t] || []).map(fn => fn({preventDefault() {}, target: this, key: "", ...ev})); }
    click() { if (this.tagName === "A") soClickTai += 1; return this.dispatch("click"); }
    setAttribute(k, v) { this.attrs[k] = String(v); } removeAttribute(k) { delete this.attrs[k]; } getAttribute(k) { return this.attrs[k] ?? null; }
    focus() {} showModal() {} close() {}
  }
  const body = new El("body");
  const document = {body, title: "",
    getElementById: id => { const ds = (reg.get(id) || []).filter(e => e.isConnected); if (ds.length) return ds[ds.length - 1];
      if (dongId.has(id) || !ID_TINH.has(id)) return null; taoTinh = true; const e = new El("div"); e.id = id; taoTinh = false; body.append(e); return e; },
    createElement: t => new El(t), createTextNode: t => Object.assign(new El("#text"), {_text: String(t)}),
    querySelector: s => (s.includes("ktt-token") ? {content: "TOKEN-THU"} : null), querySelectorAll: () => []};
  const calls = [];
  const fetch = (url, opts = {}) => new Promise((resolve, reject) => calls.push({url, opts, resolve, reject, method: (opts && opts.method) || "GET"}));
  let soUuid = 0;
  // Timer GIẢ (BG-1b): ca điều khiển thời gian bằng tien(ms); không có timer thật nào treo tiến trình
  const hen = []; let gio = 0, soHen = 0;
  const datHen = (fn, ms) => { const id = ++soHen; hen.push({id, den: gio + (ms || 0), fn}); return id; };
  const huyHen = id => { const i = hen.findIndex(h => h.id === id); if (i >= 0) hen.splice(i, 1); };
  const tien = ms => {
    const dich = gio + ms;
    for (;;) { const t = hen.filter(h => h.den <= dich).sort((a, b) => a.den - b.den || a.id - b.id)[0]; if (!t) break; hen.splice(hen.indexOf(t), 1); gio = Math.max(gio, t.den); t.fn(); }
    gio = dich;
  };
  const ctx = {document, Node: El, console, setTimeout: datHen, clearTimeout: huyHen, Promise, Map, Set, JSON, Math, Date, Number, String, Object, Array, Error, TypeError, SyntaxError,
    encodeURIComponent, decodeURIComponent, URLSearchParams, location: {hash: "#hopdong"}, crypto: {randomUUID: () => "uuid-" + (++soUuid)},
    URL: {createObjectURL: () => "blob:x", revokeObjectURL() {}}, fetch, navigator: {}};
  ctx.window = ctx;
  ctx.addEventListener = () => {};
  vm.createContext(ctx);
  return {ctx, document, calls, tien};
}

const phanHoi = (status, data, blobSize) => ({ok: status >= 200 && status < 300, status, headers: {get: () => "application/json"},
  json: async () => data, blob: async () => new BLOB_GOC([new Uint8Array(blobSize ?? 0)])});
const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 10) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
const nut = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));
// Kết quả mẫu của máy chủ cho xem-truoc (BG-1a): chuỗi hiển thị do MÁY CHỦ trả; trình duyệt chỉ hiện.
const TINH = (dong, extra = {}) => ({tien_te: "VND", tong_minor: "1000000000", tong_hien_thi: "1.000.000.000 VND", tong_ty_le: "100", tong_ty_le_hien_thi: "100%", tong_ty_le_khop: true,
  tong_tien_khop: true, tong_dong_hien_thi: "1.000.000.000 VND", ly_do_chan_in: "", ly_do_chan_chuyen: "", dong, thieu: [], canh_bao: [], chan_in: [], vnd_tham_chieu: null, ...extra});
const XEM = (tinh, extra = {}) => ({du_lieu_sha256: "h", tinh, nhan: {phap_nhan: {ma: "PN_DEMO_A", ten: "Công ty Demo A"}, loai_hinh: {ma: "DT-KCN", ten: "Cho thuê đất KCN"}, du_an: null},
  het_han_hien_thi: null, fx_ngay_hien_thi: null, ...extra});
const MOC_CHUAN = {moc: [{ma: "KY_HD", nhan: "Ký"}, {ma: "BAN_GIAO", nhan: "Bàn giao"}, {ma: "SO", nhan: "Sổ"}],
  moc_tham_so: [{mau_ma: "XONG_TANG_<n>", nhan: "Xây xong tầng n", tham_so: "n", toi_thieu: 1}, {mau_ma: "SAU_KY_<n>", nhan: "Sau ký + n ngày", tham_so: "n", toi_thieu: 0}]};

const DEMO = [{dang_nhap: "MO_PHONG_CRM_G_BH_A", vai_tro: "BAN_HANG"}, {dang_nhap: "MO_PHONG_CRM_G_KT_A", vai_tro: "KE_TOAN"}];
const NGUOI = l => ({dang_nhap: l, vai_tro: l.includes("BH") ? "BAN_HANG" : "KE_TOAN", phap_nhan: ["PN_DEMO_A"], hanh_dong: [], xem_tien: false, duoc: {}});
const CRM = l => ({cau_hinh: true, danh_tinh_demo: DEMO, nguoi: NGUOI(l), ngay_nghiep_vu: "2026-10-21", mau: [], m1_cau_hinh: false, tien_mau: [],
  ho_so: [], hop_dong: [], tien: [], file_soat: [], danh_muc: {doi_tac: [], du_an: []}});
const DS = l => ({nguoi: {dang_nhap: l, vai_tro: "BAN_HANG"}, ghi_nguon: {san_sang: true},
  loai_hinh: [{id: "lh-1", ma: "DT-KCN-THUE-DAT-DEMO", ten: "Cho thuê đất KCN", phien_ban: 2, phap_nhan: "PN_DEMO_A", phap_nhan_ten: "Công ty Demo A"}],
  du_an: [{id: "da-1", ma_junsky: "DA_KCN_DEMO", ten: "KCN Demo", phap_nhan: "PN_DEMO_A", phap_nhan_ten: "Công ty Demo A"}], khach: [{id: "k-1", ten: "Khách Demo A", ma: "KH.DEMO.CHUNG_A"}],
  bao_gia: [{id: "bg-1", so_bao_gia: "BG-2026-00001", ngay: "2026-10-21", ngay_hien_thi: "21/10/2026", khach: "KHÁCH DEMO", lo_can: "LO-1", tong_hien_thi: "1.000.000.000 VND",
    trang_thai: "NHAP", tao_boi: l}], soan: []});
const CT = (lo = "LO-1", rev = 1, xuat = []) => ({bao_gia: {id: "bg-1", so_bao_gia: "BG-2026-00001", trang_thai: "NHAP", revision_hien_hanh: rev, loai_hinh_id: "lh-1"},
  du_lieu: {loai_hinh_id: "lh-1", du_an_id: "da-1", giai_doan_g7: null, nguon_lich: "KHACH", don_vi: {ma: lo, mo_ta: null, can_cu: null},
    khach: {doi_tac_id: null, du_thao: {ten: "KHÁCH DEMO", lien_he: null}}, gia: {tien_te: "VND", don_gia: null, dien_tich: null, tong: "1000000000", co_so_thue: "NET", vat_phan_tram: null},
    fx: null, phi_bao_tri: null, lich: [{dong_id: "d-1", lan: "1", loai: "PERCENT", ty_le: "100", so_tien: null, tien_te: null, moc_loai: null, moc_ngay: null, moc_su_kien: null, ghi_chu: null, gia_tri_nhap: "100%"}],
    het_han: null, ghi_chu: null},
  tinh: TINH([{hien_thi_mo: "= 1.000.000.000 VND", loi: [], loi_chi_tiet: []}]), g7: null, revisions: [], xuat,
  mau_hieu_luc: [{mau_phien_ban_id: "mau-1", ma_mau: "HD", phien_ban: 1, valid_from: "2026-10-19"}], soan_id: null});

async function main() {
  const {ctx, document, calls, tien} = moiTruong();
  vm.runInContext(APP, ctx, {filename: "app.js"});
  vm.runInContext(CRMG, ctx, {filename: "crm_g.js"});
  const $ = id => document.getElementById(id);
  const conLai = pred => calls.filter(c => !c.xong && pred(c));
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const get = url => c => c.method === "GET" && c.url === url;
  const post = url => c => c.method === "POST" && c.url === url;
  const gk = () => $("crm-gk");
  async function traKhac() { for (const c of conLai(c => !/^\/api\/crm(\/bao-gia|$)/.test(c.url) && c.url !== "/api/crm/danh-tinh")) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); } await chay(); }
  async function traDs(l) { cho(get("/api/crm/bao-gia"), "GET danh sách " + l).resolve(phanHoi(200, DS(l))); await chay(); }
  // GET danh mục mốc chuẩn chỉ phát sinh khi mở form báo giá lần đầu; trả ngay để form dựng
  async function traMoc() { for (const c of conLai(get("/api/crm/bao-gia/moc-chuan"))) { c.xong = true; c.resolve(phanHoi(200, MOC_CHUAN)); } await chay(); }
  // trả MỌI yêu cầu xem-truoc còn chờ bằng cùng một kết quả (yêu cầu cũ bị module bỏ nếu form đã đổi)
  async function traXem(tinh = TINH([{hien_thi_mo: "", loi: [], loi_chi_tiet: []}])) {
    for (const c of conLai(post("/api/crm/bao-gia/xem-truoc"))) { c.xong = true; c.resolve(phanHoi(200, XEM(tinh))); }
    await chay();
  }
  async function moBg(lo = "LO-1") {
    if (!nut(gk(), "Mở")) { nut(gk(), "+ Báo giá mới").click(); await chay(); }  // đang mở đúng báo giá đó → bỏ chọn rồi mở lại (nạp mới từ máy chủ)
    nut(gk(), "Mở").click(); await chay(); await traMoc(); cho(get("/api/crm/bao-gia/bg-1"), "GET chi tiết").resolve(phanHoi(200, CT(lo))); await chay(); }
  const o = id => $("gk-" + id);

  // khởi động: CRM thật cho vai BH; module khác 404 có chủ đích
  for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM("MO_PHONG_CRM_G_BH_A"))); }
  await traKhac();
  await traDs("MO_PHONG_CRM_G_BH_A");
  await traKhac();

  // ---------------------------------------------------------------- P0 dương
  await moBg();
  assert.strictEqual(o("bg-lo").value, "LO-1", "P0: form không ghi dữ liệu máy chủ");
  assert.strictEqual(o("bg-tong").value, "1.000.000.000", "P0: tổng không hiện dấu chấm hàng nghìn");
  nut(gk(), "Lưu nháp").click(); await chay();
  const p0 = cho(post("/api/crm/bao-gia/luu"), "POST lưu P0");
  const b0 = JSON.parse(p0.opts.body);
  assert.deepStrictEqual([b0.bao_gia_id, b0.expected_revision, b0.du_lieu.don_vi.ma, b0.du_lieu.tong_gia_tri_ghi_de, b0.du_lieu.gia.tong, b0.du_lieu.lich[0].dong_id],
    ["bg-1", 1, "LO-1", "1.000.000.000", null, "d-1"], "P0: body Lưu");
  assert.deepStrictEqual([b0.du_lieu.lich[0].gia_tri_nhap, b0.du_lieu.lich[0].lan, "loai" in b0.du_lieu.lich[0], "tien_te" in b0.du_lieu.lich[0]], ["100%", "1", false, false],
    "P0: dòng lịch gửi chuỗi người gõ, không loại/tiền tệ");
  assert.ok(!("tinh" in b0.du_lieu) && !("trang_thai" in b0) && !("nguoi" in b0), "P0: không gửi kết quả tính/actor/trạng thái");
  assert.ok(b0.khoa && b0.khoa.startsWith("crmgk-"));
  p0.resolve(phanHoi(200, {bao_gia_id: "bg-1", revision: 2, lap_lai: false})); await chay();
  await traDs("MO_PHONG_CRM_G_BH_A");
  cho(get("/api/crm/bao-gia/bg-1"), "P0: làm mới chi tiết").resolve(phanHoi(200, CT("LO-1", 2))); await chay();
  console.log("P0 đạt");

  // ---------------------------------------------------------------- A1 bấm lặp + mất kết nối → gửi lại y nguyên
  {
    o("bg-lo").value = "LO-A1"; o("bg-lo").dispatch("input");
    nut(gk(), "Lưu nháp").click(); nut(gk(), "Lưu nháp").click(); await chay();
    assert.strictEqual(conLai(post("/api/crm/bao-gia/luu")).length, 1, "A1: bấm lặp gửi thêm POST");
    const a = cho(post("/api/crm/bao-gia/luu"), "POST A1");
    const ba = JSON.parse(a.opts.body);
    nut(gk(), "Lưu nháp").click(); await chay();
    assert.strictEqual(conLai(post("/api/crm/bao-gia/luu")).length, 0, "A1: POST thứ hai khi lần đầu còn chờ");
    a.reject(new TypeError("Failed to fetch")); await chay();
    const lai = nut(gk(), "Gửi lại y nguyên");
    assert.ok(lai, "A1: thiếu nút gửi lại");
    lai.click(); await chay();
    const a2 = cho(post("/api/crm/bao-gia/luu"), "POST gửi lại A1");
    assert.deepStrictEqual(JSON.parse(a2.opts.body), ba, "A1: gửi lại khác body/khóa");
    a2.resolve(phanHoi(200, {bao_gia_id: "bg-1", revision: 3, lap_lai: true})); await chay();
    for (const c of conLai(get("/api/crm/bao-gia"))) { c.xong = true; c.resolve(phanHoi(200, DS("MO_PHONG_CRM_G_BH_A"))); }
    await chay();
    for (const c of conLai(get("/api/crm/bao-gia/bg-1"))) { c.xong = true; c.resolve(phanHoi(200, CT("LO-A1", 3))); }
    await chay();
    console.log("A1 đạt");
  }

  // ---------------------------------------------------------------- A2 POST cũ về trễ sau khi mở form mới
  {
    nut(gk(), "Lưu nháp").click(); await chay();
    const a = cho(post("/api/crm/bao-gia/luu"), "POST A2");
    nut(gk(), "+ Báo giá mới").click(); await chay();
    o("bg-lo").value = "LO-MOI"; o("bg-lo").dispatch("input");
    const truoc = dem(get("/api/crm/bao-gia/bg-1"));
    a.resolve(phanHoi(200, {bao_gia_id: "bg-1", revision: 4, lap_lai: false})); await chay();
    assert.strictEqual(dem(get("/api/crm/bao-gia/bg-1")), truoc, "A2: kết quả cũ GET chi tiết A");
    assert.strictEqual(o("bg-lo").value, "LO-MOI", "A2: form mới bị đè");
    console.log("A2 đạt");
  }

  // ---------------------------------------------------------------- A3 GET làm mới treo → gõ → GET về không đè nháp
  {
    for (const c of conLai(() => true)) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
    await moBg("LO-1");
    nut(gk(), "↻ Làm mới").click(); await chay();
    o("bg-lo").value = "LO-DANG-GO"; o("bg-lo").dispatch("input");
    for (const c of conLai(get("/api/crm/bao-gia"))) { c.xong = true; c.resolve(phanHoi(200, DS("MO_PHONG_CRM_G_BH_A"))); }
    await chay();
    for (const c of conLai(get("/api/crm/bao-gia/bg-1"))) { c.xong = true; c.resolve(phanHoi(200, CT("LO-MAY-CHU", 9))); }
    await chay();
    assert.strictEqual(o("bg-lo").value, "LO-DANG-GO", "A3: GET về đè nháp đang gõ");
    console.log("A3 đạt");
  }

  // ---------------------------------------------------------------- A4 đổi vai khi POST còn chờ
  {
    nut(gk(), "Lưu nháp").click(); await chay();
    const a = cho(post("/api/crm/bao-gia/luu"), "POST A4");
    $("crm-danh-tinh").value = "MO_PHONG_CRM_G_KT_A"; $("crm-doi-vai").click(); await chay();
    assert.strictEqual(o("bg-lo"), null, "A4: form vai cũ chưa được xóa đồng bộ");
    const truoc = dem(get("/api/crm/bao-gia/bg-1"));
    a.resolve(phanHoi(200, {bao_gia_id: "bg-1", revision: 10, lap_lai: false})); await chay();
    assert.strictEqual(dem(get("/api/crm/bao-gia/bg-1")), truoc, "A4: POST cũ làm mới chi tiết dưới vai mới");
    for (const c of conLai(post("/api/crm/danh-tinh"))) { c.xong = true; c.resolve(phanHoi(200, {dang_nhap: "MO_PHONG_CRM_G_KT_A"})); }
    await chay();
    for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM("MO_PHONG_CRM_G_KT_A"))); }
    await chay();
    for (const c of conLai(get("/api/crm/bao-gia"))) { c.xong = true; c.resolve(phanHoi(200, DS("MO_PHONG_CRM_G_KT_A"))); }
    await traKhac();
    assert.ok($("gk-vai").textContent.includes("MO_PHONG_CRM_G_KT_A"), "A4: chưa vẽ vai mới");
    console.log("A4 đạt");
  }

  // ---------------------------------------------------------------- A5 blob về sau khi đổi vai → không click tải
  {
    nut(gk(), "Mở").click(); await chay();
    cho(get("/api/crm/bao-gia/bg-1"), "GET chi tiết A5").resolve(phanHoi(200, CT("LO-1", 10, [{id: "x-1", revision: 10, trang_thai: "PDF_DAT", ly_do: null, tao_luc: "2026-10-21T00:00:00Z"}])));
    await chay();
    nut(gk(), "DOCX ↓").click(); await chay();
    const t = cho(c => c.method === "GET" && c.url === "/api/crm/giao-ket/tep/x-1/docx", "GET tệp");
    const truoc = soClickTai;
    $("crm-danh-tinh").value = "MO_PHONG_CRM_G_BH_A"; $("crm-doi-vai").click(); await chay();
    t.resolve(phanHoi(200, {}, 128)); await chay();
    assert.strictEqual(soClickTai, truoc, "A5: tải xuống của vai cũ vẫn click");
    console.log("A5 đạt");
  }

  // ---------------------------------------------------------------- FIX01: khôi phục vai BH sau A5 (danh sách có bản soạn cho A10)
  const BH = "MO_PHONG_CRM_G_BH_A";
  const DS2 = l => ({...DS(l), soan: [{id: "so-1", trang_thai: "SOAN_THAO", revision_hien_hanh: 1, ma_noi_bo: "HD-NB-1", so_bao_gia: "BG-2026-00001"}]});
  const trangThaiGk = () => tim(gk(), e => e.attrs && e.attrs.role === "status");
  const tatCa = (root, pred, out = []) => { if (pred(root)) out.push(root); for (const c of root.children || []) tatCa(c, pred, out); return out; };
  const tuTinh = () => tatCa(gk(), e => e._cls && e._cls.has("gk-tu-tinh")).map(e => e.textContent);
  for (const c of conLai(post("/api/crm/danh-tinh"))) { c.xong = true; c.resolve(phanHoi(200, {dang_nhap: BH})); }
  await chay();
  for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM(BH))); }
  await chay();
  for (const c of conLai(get("/api/crm/bao-gia"))) { c.xong = true; c.resolve(phanHoi(200, DS2(BH))); }
  await traKhac();

  // ---------------------------------------------------------------- A6 lỗi muộn của ý định cũ
  {
    await moBg("LO-1");
    nut(gk(), "Lưu nháp").click(); await chay();
    const a = cho(post("/api/crm/bao-gia/luu"), "POST A6");
    nut(gk(), "+ Báo giá mới").click(); await chay();
    o("bg-lo").value = "LO-A6"; o("bg-lo").dispatch("input");
    a.resolve(phanHoi(409, {error: "CRM_GK_REVISION_CU", message: "LOI-CU-A6"})); await chay();
    assert.ok(!trangThaiGk().textContent.includes("LOI-CU-A6"), "A6: lỗi của ý định cũ hiện trên form mới");
    assert.strictEqual(nut(gk(), "Gửi lại y nguyên"), null, "A6: nút gửi lại của ý định cũ");
    assert.strictEqual(o("bg-lo").value, "LO-A6", "A6: form mới bị đè");
    console.log("A6 đạt");
  }

  // ---------------------------------------------------------------- A7 thay đổi chưa lưu ↔ In/Chuyển (revision đã lưu); cổng In không khóa Lưu/Chuyển
  {
    await moBg("LO-1");
    const inBtn = () => nut(gk(), "In báo giá"), chuyen = () => nut(gk(), "Chuyển sang Soạn");
    assert.ok(inBtn() && !inBtn().disabled && !chuyen().disabled, "A7: In/Chuyển bị khóa khi form = revision đã lưu");
    o("bg-lo").value = "LO-A7"; o("bg-lo").dispatch("input");
    assert.ok(inBtn().disabled && chuyen().disabled, "A7: chưa khóa In/Chuyển khi có thay đổi chưa lưu");
    assert.ok(tim(gk(), e => e.dataset && e.dataset.lyChuaLuu && e.textContent.includes("chưa lưu")), "A7: thiếu lý do vô hiệu");
    inBtn().click(); chuyen().click(); await chay();
    assert.strictEqual(dem(post("/api/crm/bao-gia/in")) + dem(post("/api/crm/bao-gia/chuyen")), 0, "A7: In/Chuyển gửi khi chưa lưu");
    assert.ok(!nut(gk(), "Lưu nháp").disabled, "A7: Lưu bị khóa");
    nut(gk(), "Lưu nháp").click(); await chay();
    cho(post("/api/crm/bao-gia/luu"), "POST A7").resolve(phanHoi(200, {bao_gia_id: "bg-1", revision: 2, lap_lai: false})); await chay();
    cho(get("/api/crm/bao-gia"), "A7 danh sách").resolve(phanHoi(200, DS2(BH))); await chay();
    const chanIn = CT("LO-A7", 2);
    chanIn.tinh = {...chanIn.tinh, tong_ty_le: "40", tong_ty_le_hien_thi: "40%", tong_ty_le_khop: false, ly_do_chan_in: "Tổng % = 40, thiếu 60", ly_do_chan_chuyen: "Tổng % = 40, thiếu 60",
      chan_in: [{ma: "TONG_TY_LE_KHAC_100", thong_bao: "Tổng % = 40, thiếu 60"}]};
    cho(get("/api/crm/bao-gia/bg-1"), "A7 chi tiết").resolve(phanHoi(200, chanIn)); await chay();
    assert.strictEqual(o("bg-lo").value, "LO-A7");
    // BG-02 (lead 24/10): Σ% ≠ 100 → mờ CẢ In lẫn Chuyển kèm lý do của máy chủ; Lưu luôn bật
    assert.ok(inBtn().disabled && chuyen().disabled, "A7: Σ% ≠ 100 mà In/Chuyển không mờ");
    assert.ok(inBtn().title.includes("Tổng % = 40, thiếu 60") && chuyen().title.includes("Tổng % = 40, thiếu 60"), "A7: thiếu lý do khi rê chuột");
    assert.ok(!nut(gk(), "Lưu nháp").disabled, "A7: cổng In khóa Lưu");
    inBtn().click(); chuyen().click(); await chay();
    assert.strictEqual(dem(post("/api/crm/bao-gia/in")) + dem(post("/api/crm/bao-gia/chuyen")), 0, "A7: In/Chuyển gửi khi máy chủ báo chặn");
    console.log("A7 đạt");
  }

  // ---------------------------------------------------------------- BG-1b: trợ giúp chung cho A8…A13, B5
  const postXem = post("/api/crm/bao-gia/xem-truoc");
  const tab = ten => tim(gk(), e => e.tagName === "BUTTON" && e.textContent === ten);
  const mo = i => tatCa(gk(), e => e._cls && e._cls.has("gk-mo"))[i];
  const tongDong = () => tim(gk(), e => e._cls && e._cls.has("gk-tong-dong"));
  const ghiLoiTinh = () => tim(gk(), e => e._cls && e._cls.has("gk-tinh-loi"));
  const goiY = () => tim(gk(), e => e._cls && e._cls.has("gk-goi-y"));
  const luuY = () => tim(gk(), e => e._cls && e._cls.has("gk-luu-y"));
  const goVao = (id, v, ev = "input") => { o(id).value = v; o(id).dispatch(ev); };
  const ketQua = (hien, extra = {}) => TINH([{hien_thi_mo: hien, loi: [], loi_chi_tiet: []}], extra);

  // ---------------------------------------------------------------- A8 nạp G7 vào lịch MỘT ô Giá trị + mốc một ô; khác tiền tệ báo giá → không nạp
  {
    o("bg-nguon").value = "DU_AN"; o("bg-nguon").dispatch("change"); await chay();
    o("bg-tt").value = "USD"; o("bg-tt").dispatch("change");
    o("bg-du-an").value = "da-1"; o("bg-du-an").dispatch("change");
    o("bg-g7").value = "GD1"; o("bg-g7").dispatch("input");
    const G7 = rows => ({trang_thai: "HIEU_LUC", version: {phien_ban: 3}, rows});
    nut(gk(), "Nạp bộ chuẩn").click(); await chay();
    cho(c => c.method === "GET" && c.url === "/api/crm/bo-chuan?du_an_id=da-1&giai_doan=GD1", "GET G7").resolve(phanHoi(200, G7([
      {lan: "1", gia_tri_loai: "AMOUNT", gia_tri_thap_phan: null, so_tien_minor: "123456", tien_te: "USD", moc_loai: "NGAY", moc_ngay: "2026-12-01", moc_su_kien: null, ghi_chu: "đợt 1"},
      {lan: "2", gia_tri_loai: "AMOUNT", gia_tri_thap_phan: null, so_tien_minor: "500000", tien_te: "USD", moc_loai: "SU_KIEN", moc_ngay: null, moc_su_kien: "BAN_GIAO", ghi_chu: null},
      {lan: "3", gia_tri_loai: "PERCENT", gia_tri_thap_phan: "10", so_tien_minor: null, tien_te: null, moc_loai: null, moc_ngay: null, moc_su_kien: null, ghi_chu: null},
      {lan: "4", gia_tri_loai: "AMOUNT", gia_tri_thap_phan: null, so_tien_minor: "5", tien_te: "USD", moc_loai: null, moc_ngay: null, moc_su_kien: null, ghi_chu: null}])));
    await chay();
    assert.deepStrictEqual([0, 1, 2, 3].map(i => [o(`bg-l-gt-${i}`).value, o(`bg-l-mo-${i}`).value]),
      [["1.234,56", "01/12/2026"], ["5.000", "Bàn giao"], ["10%", ""], ["0,05", ""]], "A8: giá trị/mốc G7 nạp sai");
    nut(gk(), "Lưu nháp").click(); await chay();
    const p = cho(post("/api/crm/bao-gia/luu"), "POST A8");
    const lich8 = JSON.parse(p.opts.body).du_lieu.lich;
    assert.deepStrictEqual(lich8.map(r => [r.lan, r.gia_tri_nhap, r.moc_loai, r.moc_ngay, r.moc_su_kien, r.ghi_chu]),
      [["1", "1.234,56", "NGAY", "2026-12-01", null, "đợt 1"], ["2", "5.000", "SU_KIEN", null, "BAN_GIAO", null], ["3", "10%", null, null, null, null], ["4", "0,05", null, null, null, null]],
      "A8: body Lưu sai lịch G7");
    assert.ok(lich8.every(r => !("loai" in r) && !("ty_le" in r) && !("so_tien" in r) && !("tien_te" in r)), "A8: trình duyệt gửi loại/tỷ lệ/tiền (máy chủ phải suy ra)");
    p.resolve(phanHoi(409, {error: "CRM_GK_REVISION_CU", message: "A8 không lưu"})); await chay();
    nut(gk(), "Nạp bộ chuẩn").click(); await chay();
    cho(c => c.method === "GET" && c.url.startsWith("/api/crm/bo-chuan?"), "GET G7 khác tiền tệ").resolve(phanHoi(200, G7([
      {lan: "1", gia_tri_loai: "AMOUNT", so_tien_minor: "100", tien_te: "VND", moc_loai: null, moc_ngay: null, moc_su_kien: null, ghi_chu: null}])));
    await chay();
    assert.strictEqual(o("bg-l-gt-0").value, "1.234,56", "A8: tiền tệ khác báo giá vẫn nạp/đè lịch");
    assert.ok(trangThaiGk().textContent.includes("giữ nguyên"), "A8: thiếu thông báo không nạp");
    await traXem();
    console.log("A8 đạt");
  }

  // ---------------------------------------------------------------- A9 lịch ≤ 3 ô nhập/dòng, 0 nút tính, ô Giá trị thông minh, tính TỰ ĐỘNG (timer giả), Σ, In/Chuyển mờ
  {
    for (const c of conLai(() => true)) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
    await moBg("LO-1");
    const inBtn = () => nut(gk(), "In báo giá"), chuyen = () => nut(gk(), "Chuyển sang Soạn");
    assert.deepStrictEqual(tatCa(gk(), e => e.id && /^gk-bg-l-.*-0$/.test(e.id)).map(e => e.id).sort(), ["gk-bg-l-gc-0", "gk-bg-l-gt-0", "gk-bg-l-mo-0"], "A9: ô nhập mỗi dòng lịch (đích ≤ 4)");
    assert.strictEqual(tatCa(gk(), e => e.tagName === "BUTTON" && /Tính thử/.test(e.textContent)).length, 0, "A9: còn nút Tính thử");
    assert.ok(!/Tính thử|chưa tính lại|lưu nháp để máy chủ tính/.test(gk().textContent), "A9: còn chuỗi 'chưa tính lại'/'Tính thử'");
    assert.ok(["loai", "tl", "st", "tt", "ml", "mn", "ms", "lan"].every(c => o(`bg-l-${c}-0`) === null), "A9: còn ô cũ của lịch");
    // revision đã lưu đủ trường hiển thị → hiện ngay, KHÔNG gọi máy chủ tính
    assert.strictEqual(o("bg-l-gt-0").value, "100%");
    assert.strictEqual(mo(0).textContent, "= 1.000.000.000 VND");
    assert.ok(tongDong().textContent.includes("Σ 100%") && tongDong().children[0].dataset.tongTyLe === "khop", "A9: thiếu dòng tổng Σ");
    assert.strictEqual(conLai(postXem).length, 0, "A9: mở báo giá đã lưu vẫn gọi tính");
    // gõ → "…"; chưa tới 400 ms thì chưa gọi; sau đó đúng một lần với chuỗi người gõ
    const el = o("bg-l-gt-0");
    goVao("bg-l-gt-0", "30%");
    assert.ok(mo(0).textContent.includes("…") && mo(0).className.includes("gk-cho"), "A9: không hiện '…' khi chờ");
    tien(399); await chay();
    assert.strictEqual(conLai(postXem).length, 0, "A9: gọi trước 400 ms");
    tien(1); await chay();
    const x1 = cho(postXem, "A9 xem trước 1"), bx1 = JSON.parse(x1.opts.body);
    assert.deepStrictEqual(Object.keys(bx1), ["du_lieu"], "A9: xem trước gửi khóa/trường thừa");
    assert.strictEqual(bx1.du_lieu.lich[0].gia_tri_nhap, "30%");
    assert.ok(!("loai" in bx1.du_lieu.lich[0]) && !("tien_te" in bx1.du_lieu.lich[0]), "A9: gửi loại/tiền tệ của dòng");
    x1.resolve(phanHoi(200, XEM(ketQua("= 300.000.000 VND", {tong_ty_le_hien_thi: "30%", tong_ty_le_khop: false, tong_tien_khop: false, tong_dong_hien_thi: "300.000.000 VND",
      ly_do_chan_in: "Tổng % = 30, thiếu 70", ly_do_chan_chuyen: "Tổng % = 30, thiếu 70"})))); await chay();
    assert.strictEqual(mo(0).textContent, "= 300.000.000 VND", "A9: ô mờ không hiện kết quả của máy chủ");
    assert.ok(!mo(0).className.includes("gk-cho"));
    assert.strictEqual(o("bg-l-gt-0"), el, "A9: kết quả về làm vẽ lại form (mất caret)");
    const t1 = tongDong();
    assert.ok(t1.textContent.includes("Σ 30%") && t1.children[0].className.includes("gk-sai") && t1.children[0].dataset.tongTyLe === "lech", "A9: Σ% ≠ 100 không đỏ");
    assert.ok(t1.textContent.includes("Tổng % = 30, thiếu 70"), "A9: dòng tổng thiếu lý do");
    assert.ok(inBtn().disabled && chuyen().disabled && inBtn().title.includes("Tổng % = 30, thiếu 70") && chuyen().title.includes("Tổng % = 30, thiếu 70"), "A9: In/Chuyển không mờ kèm lý do");
    // rời ô (change): gọi NGAY + đổi dạng chữ (không đổi giá trị); không có % = số tiền
    goVao("bg-l-gt-0", "450000", "change");
    assert.strictEqual(o("bg-l-gt-0").value, "450.000", "A9: không đổi dạng khi rời ô");
    await chay();
    const x2 = cho(postXem, "A9 xem trước 2");
    assert.strictEqual(JSON.parse(x2.opts.body).du_lieu.lich[0].gia_tri_nhap, "450.000");
    // phản hồi cũ bị bỏ: gõ tiếp khi x2 còn bay
    goVao("bg-l-gt-0", "460.000");
    x2.resolve(phanHoi(200, XEM(ketQua("= 30% (CU)")))); await chay();
    assert.ok(!mo(0).textContent.includes("CU") && mo(0).textContent.includes("…"), "A9: phản hồi cũ áp lên form đã đổi");
    tien(400); await chay();
    const x3 = cho(postXem, "A9 xem trước 3");
    assert.strictEqual(JSON.parse(x3.opts.body).du_lieu.lich[0].gia_tri_nhap, "460.000");
    x3.resolve(phanHoi(200, XEM(ketQua("= 46% · ≈ 1.000 tr VND", {tong_ty_le_hien_thi: "100%", tong_ty_le_khop: true, tong_tien_khop: true})))); await chay();
    assert.strictEqual(mo(0).textContent, "= 46% · ≈ 1.000 tr VND");
    assert.ok(tongDong().children[0].dataset.tongTyLe === "khop" && tongDong().children[0].className.includes("gk-ok"), "A9: Σ = 100 không xanh");
    assert.ok(inBtn().disabled && !inBtn().title.includes("Tổng %"), "A9: còn lý do Σ khi đã khớp (nút vẫn mờ vì chưa lưu)");
    assert.ok(inBtn().title.includes("chưa lưu"), "A9: In không giải thích vì sao mờ (chưa lưu)");
    // gõ dòng có lỗi: máy chủ trả lỗi cho dòng → hiện đúng chỗ, bỏ tiền tố "Dòng n:"
    goVao("bg-l-gt-0", "1.50", "change"); await chay();
    cho(postXem, "A9 dòng lỗi").resolve(phanHoi(200, XEM(TINH([{hien_thi_mo: "", loi: ["GIA_TRI_NHAP_SAI"],
      loi_chi_tiet: [{ma: "GIA_TRI_NHAP_SAI", dong: 1, thong_bao: "Dòng 1: Giá trị phải là số không âm kiểu Việt (450.000 hoặc 1.500.000,50); thêm % khi nhập tỷ lệ."}]}])))); await chay();
    assert.ok(mo(0).textContent.startsWith("Giá trị phải là số") && mo(0).className.includes("gk-loi"), "A9: lỗi dòng hiện sai chỗ: " + mo(0).textContent);
    await traXem();
    console.log("A9 đạt");
  }

  // ---------------------------------------------------------------- A11 mốc một ô; mã lạ giữ nguyên; mốc không hiểu chặn Lưu; thêm/đổi chỗ/bỏ dòng
  {
    const xemLai = async () => {  // mỗi thay đổi → lấy body của yêu cầu mới nhất rồi trả
      await chay();
      const cs = conLai(postXem), c = cs[cs.length - 1];
      const b = JSON.parse(c.opts.body);
      for (const x of cs) { x.xong = true; x.resolve(phanHoi(200, XEM(ketQua("")))); }
      await chay(); return b.du_lieu.lich;
    };
    const moc = l => [l.moc_loai, l.moc_ngay, l.moc_su_kien];
    goVao("bg-l-mo-0", "ban giao", "change");
    assert.strictEqual(o("bg-l-mo-0").value, "Bàn giao", "A11: không chuẩn hóa mốc");
    assert.deepStrictEqual(moc((await xemLai())[0]), ["SU_KIEN", null, "BAN_GIAO"]);
    goVao("bg-l-mo-0", "5/1/2027", "change");
    assert.strictEqual(o("bg-l-mo-0").value, "05/01/2027", "A11: ngày không về dd/mm/yyyy");
    assert.deepStrictEqual(moc((await xemLai())[0]), ["NGAY", "2027-01-05", null]);
    goVao("bg-l-mo-0", "xây xong tầng 5", "change");
    assert.strictEqual(o("bg-l-mo-0").value, "Xây xong tầng 5");
    assert.deepStrictEqual(moc((await xemLai())[0]), ["SU_KIEN", null, "XONG_TANG_5"]);
    goVao("bg-l-mo-0", "sau ky + 30 ngay", "change");
    assert.strictEqual(o("bg-l-mo-0").value, "Sau ký + 30 ngày");
    assert.deepStrictEqual(moc((await xemLai())[0]), ["SU_KIEN", null, "SAU_KY_30"]);
    // mốc không hiểu / ngày không tồn tại: báo tại dòng, KHÔNG gửi mốc, Lưu bị chặn
    for (const sai of ["xây xong tầng 0", "31/02/2026", "abc"]) {
      goVao("bg-l-mo-0", "Ký", "change"); await xemLai();
      goVao("bg-l-mo-0", sai, "change");
      assert.strictEqual(o("bg-l-mo-0").value, sai, "A11: tự sửa chữ mốc không hiểu");
      assert.deepStrictEqual(moc((await xemLai())[0]), [null, null, null], "A11: gửi mốc đoán: " + sai);
      assert.ok(tatCa(gk(), e => e.tagName === "SMALL" && e._cls && e._cls.has("gk-loi")).some(e => e.textContent.includes("chưa hiểu mốc")), "A11: thiếu báo mốc không hiểu tại dòng: " + sai);
      const nL = dem(post("/api/crm/bao-gia/luu"));
      nut(gk(), "Lưu nháp").click(); await chay();
      assert.strictEqual(dem(post("/api/crm/bao-gia/luu")), nL, "A11: Lưu khi mốc không hiểu");
      assert.ok(trangThaiGk().textContent.includes("chưa hiểu mốc"));
    }
    goVao("bg-l-mo-0", "Sổ", "change");
    assert.ok(tatCa(gk(), e => e.tagName === "SMALL" && e._cls && e._cls.has("gk-loi")).every(e => e.textContent === ""), "A11: còn báo mốc không hiểu sau khi sửa");
    await xemLai();
    // thêm / đổi chỗ / bỏ dòng; Lần tự đánh số; mã dòng đi theo nội dung
    const lans = () => tatCa(gk(), e => e._cls && e._cls.has("gk-lan")).map(e => e.textContent);
    goVao("bg-l-gc-0", "g0", "change");
    nut(gk(), "+ Dòng").click(); await chay();
    assert.ok(o("bg-l-gt-1") && !o("bg-l-gt-2"), "A11: thêm dòng");
    assert.deepStrictEqual(lans(), ["1", "2"], "A11: Lần không tự đánh số");
    goVao("bg-l-gt-0", "30%", "change"); goVao("bg-l-gt-1", "70%", "change");
    await xemLai();
    const xuong = () => tatCa(gk(), e => e.tagName === "BUTTON" && e.textContent === "↓")[0];
    xuong().click(); await chay();
    assert.deepStrictEqual([o("bg-l-gt-0").value, o("bg-l-gt-1").value, o("bg-l-mo-1").value, o("bg-l-gc-1").value, o("bg-l-gc-0").value], ["70%", "30%", "Sổ", "g0", ""],
      "A11: đổi chỗ dòng không mang theo mốc/ghi chú");
    assert.deepStrictEqual(lans(), ["1", "2"]);
    nut(gk(), "Lưu nháp").click(); await chay();
    const ps = cho(post("/api/crm/bao-gia/luu"), "POST A11");
    assert.deepStrictEqual(JSON.parse(ps.opts.body).du_lieu.lich.map(r => [r.dong_id, r.lan, r.gia_tri_nhap, r.moc_su_kien]), [[null, "1", "70%", null], ["d-1", "2", "30%", "SO"]],
      "A11: mã dòng không đi theo nội dung khi đổi chỗ");
    ps.resolve(phanHoi(409, {error: "CRM_GK_REVISION_CU", message: "A11 không lưu"})); await chay();
    tatCa(gk(), e => e.tagName === "BUTTON" && e.textContent === "Bỏ")[0].click(); await chay();
    assert.ok(o("bg-l-gt-0") && !o("bg-l-gt-1"), "A11: bỏ dòng");
    assert.strictEqual(o("bg-l-gt-0").value, "30%");
    await traXem();
    // mã sự kiện chưa có nhãn: hiện nhãn trung tính, gửi lại NGUYÊN mã khi không sửa
    for (const c of conLai(() => true)) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
    nut(gk(), "+ Báo giá mới").click(); await chay();
    nut(gk(), "Mở").click(); await chay();
    const ct = CT("LO-1"); ct.du_lieu.lich[0].moc_loai = "SU_KIEN"; ct.du_lieu.lich[0].moc_su_kien = "MA_LA";
    cho(get("/api/crm/bao-gia/bg-1"), "A11 GET mã lạ").resolve(phanHoi(200, ct)); await chay();
    assert.strictEqual(o("bg-l-mo-0").value, "Sự kiện khác (chưa có nhãn)", "A11: hiện mã kỹ thuật");
    nut(gk(), "Lưu nháp").click(); await chay();
    const pl = cho(post("/api/crm/bao-gia/luu"), "POST A11 mã lạ");
    assert.deepStrictEqual(moc(JSON.parse(pl.opts.body).du_lieu.lich[0]), ["SU_KIEN", null, "MA_LA"], "A11: mã sự kiện lạ không được gửi lại nguyên");
    pl.resolve(phanHoi(409, {error: "CRM_GK_REVISION_CU", message: "A11 không lưu 2"})); await chay();
    console.log("A11 đạt");
  }

  // ---------------------------------------------------------------- A12 Tổng giá trị: tự tính / ghi đè (nguyên chuỗi người gõ) / lỗi theo trường
  {
    goVao("bg-tong", "", "change");
    goVao("bg-dg", "100", "change"); goVao("bg-dt", "15000", "change");
    assert.strictEqual(o("bg-dt").value, "15.000", "A12: diện tích không hiện dấu chấm hàng nghìn");
    await chay();
    let cs = conLai(postXem), bd = JSON.parse(cs[cs.length - 1].opts.body).du_lieu;
    assert.deepStrictEqual([bd.gia.don_gia, bd.gia.dien_tich, bd.gia.tong, "tong_gia_tri_ghi_de" in bd], ["100", "15000", null, false], "A12: đơn giá/diện tích/tổng để trống");
    const usd = (extra = {}) => ketQua("= 100% · ≈ 38.250 tr VND", {tien_te: "USD", tong_minor: "150000000", tong_tinh_minor: "150000000", tong_hien_thi: "1.500.000,00 USD",
      tong_dong_hien_thi: "1.500.000,00 USD", vnd_tham_chieu: {tong: "38250000000", dong: ["38250000000"]}, ...extra});
    for (const c of cs) { c.xong = true; c.resolve(phanHoi(200, XEM(usd(), {fx_ngay_hien_thi: "23/10/2026"}))); }
    await chay();
    assert.ok(goiY().textContent.includes("tự tính") && goiY().textContent.includes("1.500.000,00 USD"), "A12: tổng tự tính không hiện: " + goiY().textContent);
    assert.strictEqual(luuY().textContent, "", "A12: lưu ý ký khi chưa ghi đè");
    assert.ok(tongDong().textContent.includes("= Tổng giá trị") && tongDong().textContent.includes("≈ 38.250 tr VND"), "A12: dòng tổng thiếu so khớp/VND quy đổi: " + tongDong().textContent);
    // ghi đè: gửi NGUYÊN chuỗi người gõ; cảnh báo của máy chủ + lưu ý ký
    goVao("bg-tong", "1.400.000", "change"); await chay();
    cs = conLai(postXem); bd = JSON.parse(cs[cs.length - 1].opts.body).du_lieu;
    assert.deepStrictEqual([bd.tong_gia_tri_ghi_de, bd.gia.tong], ["1.400.000", null], "A12: tổng ghi đè không gửi nguyên chuỗi người gõ");
    for (const c of cs) { c.xong = true; c.resolve(phanHoi(200, XEM(usd({tong_hien_thi: "1.400.000,00 USD", canh_bao: [{ma: "TONG_LECH_DON_GIA_X_DIEN_TICH",
      thong_bao: "Khác tính toán: 1.400.000,00 USD; đơn giá × diện tích = 1.500.000,00 USD."}]})))); }
    await chay();
    assert.ok(goiY().textContent.startsWith("Khác tính toán:") && goiY().className.includes("gk-canh"), "A12: thiếu cảnh báo 'Khác tính toán': " + goiY().textContent);
    assert.strictEqual(luuY().textContent, "Tổng ghi đè sẽ được kiểm lại khi ký hợp đồng", "A12: thiếu lưu ý ký");
    // lỗi theo trường của máy chủ
    goVao("bg-tong", "abc", "change"); await chay();
    cs = conLai(postXem); assert.strictEqual(JSON.parse(cs[cs.length - 1].opts.body).du_lieu.tong_gia_tri_ghi_de, "abc", "A12: tự sửa/chặn chuỗi sai ở trình duyệt");
    for (const c of cs) { c.xong = true; c.resolve(phanHoi(200, XEM(usd({tong_minor: null, tong_hien_thi: null, chan_in: [{ma: "TONG_GIA_TRI_GHI_DE_SAI", truong: "tong_gia_tri_ghi_de",
      thong_bao: "Giá trị phải là số không âm kiểu Việt (450.000 hoặc 1.500.000,50)."}]})))); }
    await chay();
    assert.ok(goiY().textContent.startsWith("Giá trị phải là số") && goiY().className.includes("gk-loi"), "A12: lỗi theo trường không hiện cạnh ô tổng: " + goiY().textContent);
    // Lưu mang nguyên chuỗi người gõ của tổng
    goVao("bg-tong", "1.400.000", "change");
    nut(gk(), "Lưu nháp").click(); await chay();
    const pt = cho(post("/api/crm/bao-gia/luu"), "POST A12");
    const dl = JSON.parse(pt.opts.body).du_lieu;
    assert.deepStrictEqual([dl.tong_gia_tri_ghi_de, dl.gia.tong, dl.gia.don_gia, dl.gia.dien_tich], ["1.400.000", null, "100", "15000"], "A12: body Lưu");
    pt.resolve(phanHoi(409, {error: "CRM_GK_REVISION_CU", message: "A12 không lưu"})); await chay();
    // số sai dạng ở ô còn lại (đơn giá): báo rõ, không gửi, Lưu bị chặn
    goVao("bg-dg", "1.5", "change"); await chay();
    const nL = dem(post("/api/crm/bao-gia/luu"));
    nut(gk(), "Lưu nháp").click(); await chay();
    assert.strictEqual(dem(post("/api/crm/bao-gia/luu")), nL, "A12: Lưu khi đơn giá sai dạng");
    assert.ok(trangThaiGk().textContent.includes("Đơn giá"), "A12: không nói rõ ô nào sai");
    await traXem();
    console.log("A12 đạt");
  }

  // ---------------------------------------------------------------- A13 BG-05: không mã kỹ thuật, ngày dd/mm/yyyy, số có dấu chấm; chuỗi xấp xỉ hiện nguyên
  {
    for (const c of conLai(() => true)) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
    await moBg("LO-1");
    const khung = tim(gk(), e => e._cls && e._cls.has("gk-2cot"));
    assert.ok(!/[A-Z0-9]+_[A-Z0-9_]+/.test(khung.textContent), "A13: còn mã kỹ thuật trong form: " + (khung.textContent.match(/[A-Z0-9]+_[A-Z0-9_]+/) || [])[0]);
    assert.ok(khung.textContent.includes("Công ty Demo A · Cho thuê đất KCN") && khung.textContent.includes("KCN Demo") && khung.textContent.includes("Khách Demo A"), "A13: không hiện tên");
    assert.ok(!/\(G7\)|\(G2\)|\(G3\)|mm\/dd\/yyyy|DT-KCN|KH\.DEMO/.test(gk().textContent), "A13: còn mã/ghi chú kỹ thuật: " + (gk().textContent.match(/\(G\d\)|DT-KCN|KH\.DEMO/) || [])[0]);
    assert.ok(gk().textContent.includes("21/10/2026"), "A13: ngày danh sách không dd/mm/yyyy");
    assert.ok(!tatCa(gk(), e => e.tagName === "INPUT" && e.type === "date").length, "A13: còn ô ngày kiểu trình duyệt (hiện mm/dd/yyyy theo máy)");
    goVao("bg-fx", "25500", "change"); goVao("bg-fx-ngay", "3/1/2026", "change"); goVao("bg-het", "2026-12-31", "change");
    assert.deepStrictEqual([o("bg-fx").value, o("bg-fx-ngay").value, o("bg-het").value], ["25.500", "03/01/2026", "31/12/2026"], "A13: số/ngày không hiện kiểu Việt");
    await chay();
    const cs = conLai(postXem), bd = JSON.parse(cs[cs.length - 1].opts.body).du_lieu;
    assert.deepStrictEqual([bd.fx && bd.fx.ty_gia, bd.fx && bd.fx.ngay, bd.het_han], ["25500", "2026-01-03", "2026-12-31"], "A13: gửi số/ngày không về dạng chuẩn");
    // chuỗi % xấp xỉ của máy chủ hiện nguyên (cờ ty_le_xap_xi)
    for (const c of cs) { c.xong = true; c.resolve(phanHoi(200, XEM(TINH([{hien_thi_mo: "= ≈ 33,33%", ty_le_xap_xi: true, ty_le: null, loi: [], loi_chi_tiet: []}],
      {tong_ty_le_hien_thi: "≈ 100%", tong_ty_le_khop: true, tong_tien_khop: true})))); }
    await chay();
    assert.strictEqual(mo(0).textContent, "= ≈ 33,33%", "A13: chuỗi xấp xỉ bị đổi");
    assert.ok(tongDong().textContent.includes("Σ ≈ 100%"), "A13: Σ xấp xỉ bị đổi");
    // đổi tỷ giá → máy chủ tính lại, VND quy đổi cập nhật (không nút nào)
    goVao("bg-fx", "26000", "change"); await chay();
    const c2 = cho(postXem, "A13 đổi tỷ giá");
    assert.strictEqual(JSON.parse(c2.opts.body).du_lieu.fx.ty_gia, "26000");
    c2.resolve(phanHoi(200, XEM(ketQua("= 100% · ≈ 39.000 tr VND", {tien_te: "USD", vnd_tham_chieu: {tong: "39000000000", dong: ["39000000000"]}, vnd_tong_hien_thi: "≈ 39.000 tr VND"})))); await chay();
    assert.strictEqual(mo(0).textContent, "= 100% · ≈ 39.000 tr VND");
    assert.ok(tongDong().textContent.includes("≈ 39.000 tr VND"), "A13: VND quy đổi tổng không đổi theo tỷ giá");
    // chưa có mẫu hợp đồng hiệu lực: vẫn hiện nút Chuyển (mờ kèm lý do) thay vì dòng chữ rời
    for (const c of conLai(() => true)) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
    nut(gk(), "+ Báo giá mới").click(); await chay(); nut(gk(), "Mở").click(); await chay();
    const ctm = CT("LO-1"); ctm.mau_hieu_luc = [];
    cho(get("/api/crm/bao-gia/bg-1"), "A13 không mẫu").resolve(phanHoi(200, ctm)); await chay();
    const cm = nut(gk(), "Chuyển sang Soạn");
    assert.ok(cm && cm.disabled && cm.title.includes("mẫu hợp đồng hiệu lực"), "A13: thiếu mẫu mà không hiện nút Chuyển mờ kèm lý do");
    await traXem();
    console.log("A13 đạt");
  }

  // ---------------------------------------------------------------- A10 G3: GET cũ không đè, Xuất cần lưu, lỗi muộn sau đổi tab bị fence
  {
    const SO = (shd = "HĐ-1", rev = 1) => ({soan: {id: "so-1", hop_dong_id: "hd-1", ma_noi_bo: "HD-NB-1", so_bao_gia: "BG-2026-00001", trang_thai: "SOAN_THAO",
      revision_hien_hanh: rev, loai_hinh_id: "lh-1", mau_phien_ban_id: "mau-1"}, du_lieu: {gia_tri_truong: {so_hop_dong: shd}, bao_gia: CT().du_lieu}, tinh: CT().tinh,
      mau: {mau_phien_ban_id: "mau-1", ma_mau: "HD", phien_ban: 1, ten_tep: "m.docx", raw_sha256: "x"},
      danh_muc: [{khoa: "so_hop_dong", kieu: "text", nhan: "Số HĐ", nhom: "Chung", bat_buoc: true}],
      kiem: {nhom: {Chung: [{khoa: "so_hop_dong", kieu: "text", nhan: "Số HĐ", bat_buoc: true}]}, doan: [], chan_xuat: [], canh_bao: []},
      revisions: [], xuat: [], mau_hieu_luc: []});
    for (const c of conLai(() => true)) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
    tab("Soạn hợp đồng").click(); await chay();
    nut(gk(), "Mở").click(); await chay();
    cho(get("/api/crm/soan/so-1"), "GET bản soạn").resolve(phanHoi(200, SO())); await chay();
    assert.strictEqual(o("so-f-so_hop_dong").value, "HĐ-1", "A10: form G3 không ghi dữ liệu máy chủ");
    const xuat = () => nut(gk(), "Xuất DOCX");
    assert.ok(!xuat().disabled, "A10: Xuất bị khóa khi form = revision đã lưu");
    nut(gk(), "↻ Làm mới").click(); await chay();
    o("so-f-so_hop_dong").value = "HĐ-DANG-GO"; o("so-f-so_hop_dong").dispatch("input");
    assert.ok(xuat().disabled, "A10: Xuất chưa khóa khi có thay đổi chưa lưu");
    const truoc = dem(get("/api/crm/soan/so-1"));
    for (const c of conLai(get("/api/crm/bao-gia"))) { c.xong = true; c.resolve(phanHoi(200, DS2(BH))); }
    await chay();
    for (const c of conLai(get("/api/crm/soan/so-1"))) { c.xong = true; c.resolve(phanHoi(200, SO("HĐ-MAY-CHU", 9))); }
    await chay();
    assert.strictEqual(dem(get("/api/crm/soan/so-1")), truoc, "A10: chuỗi làm mới vẫn mở GET chi tiết sau khi người dùng gõ");
    assert.strictEqual(o("so-f-so_hop_dong").value, "HĐ-DANG-GO", "A10: GET về đè nháp G3 đang gõ");
    xuat().click(); await chay();
    assert.strictEqual(dem(post("/api/crm/soan/xuat")), 0, "A10: Xuất gửi khi chưa lưu");
    nut(gk(), "Lưu bản soạn").click(); await chay();
    const p = cho(post("/api/crm/soan/luu"), "POST lưu G3");
    assert.strictEqual(JSON.parse(p.opts.body).gia_tri_truong.so_hop_dong, "HĐ-DANG-GO");
    tab("Báo giá").click(); await chay();
    p.reject(new TypeError("Failed to fetch")); await chay();
    assert.strictEqual(nut(gk(), "Gửi lại y nguyên"), null, "A10: nút gửi lại của ý định G3 cũ hiện ở tab khác");
    assert.ok(!trangThaiGk().textContent.includes("Mất kết nối"), "A10: thông báo lỗi muộn của ý định cũ");
    console.log("A10 đạt");
  }

  // ================================================================ FIX02 — connected-handler (handler THẬT gắn trên DOM giả; không phải trình duyệt)
  const toastTxt = () => ($("toast") || {textContent: ""}).textContent;
  const datToast = s => { if ($("toast")) $("toast").textContent = s; };
  const SOm = (rev = 1) => ({soan: {id: "so-1", hop_dong_id: "hd-1", ma_noi_bo: "HD-NB-1", so_bao_gia: "BG-2026-00001", trang_thai: "SOAN_THAO",
    revision_hien_hanh: rev, loai_hinh_id: "lh-1", mau_phien_ban_id: "mau-1"}, du_lieu: {gia_tri_truong: {so_hop_dong: "HĐ-1"}, bao_gia: CT().du_lieu}, tinh: CT().tinh,
    mau: {mau_phien_ban_id: "mau-1", ma_mau: "HD", phien_ban: 1, ten_tep: "m.docx", raw_sha256: "x"},
    danh_muc: [{khoa: "so_hop_dong", kieu: "text", nhan: "Số HĐ", nhom: "Chung", bat_buoc: true}],
    kiem: {nhom: {Chung: [{khoa: "so_hop_dong", kieu: "text", nhan: "Số HĐ", bat_buoc: true}]}, doan: [], chan_xuat: [], canh_bao: []},
    revisions: [], xuat: [], mau_hieu_luc: [{mau_phien_ban_id: "mau-2", ma_mau: "HD", phien_ban: 2}]});
  const getDs = get("/api/crm/bao-gia"), getBg = get("/api/crm/bao-gia/bg-1"), getSo = get("/api/crm/soan/so-1");
  async function lamMoiBg(ct) {  // ↻ Làm mới khi KHÔNG gõ: danh sách rồi chi tiết → form = revision máy chủ (sạch)
    nut(gk(), "↻ Làm mới").click(); await chay();
    cho(getDs, "làm mới danh sách").resolve(phanHoi(200, DS2(BH))); await chay();
    cho(getBg, "làm mới chi tiết").resolve(phanHoi(200, ct)); await chay();
  }
  const nutLai = () => nut(gk(), "Gửi lại y nguyên") || nut(gk(), "Đối soát y nguyên");

  // ---------------------------------------------------------------- B1 409 đang xử lý/chưa rõ: giữ body + khóa gốc tới FINAL; 409 xác định → nhả khóa
  {
    for (const c of conLai(() => true)) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
    await moBg("LO-1");
    const inBtn = () => nut(gk(), "In báo giá");
    inBtn().click(); await chay();
    const i1 = cho(post("/api/crm/bao-gia/in"), "B1 In"), b1 = JSON.parse(i1.opts.body);
    i1.reject(new TypeError("Failed to fetch")); await chay();  // mất ACK
    nut(gk(), "Gửi lại y nguyên").click(); await chay();
    const i2 = cho(post("/api/crm/bao-gia/in"), "B1 gửi lại");
    assert.deepStrictEqual(JSON.parse(i2.opts.body), b1, "B1: gửi lại khác body/khóa");
    i2.resolve(phanHoi(409, {error: "CRM_GK_DANG_XU_LY", message: "Đang xử lý"})); await chay();
    assert.ok(nut(gk(), "Đối soát y nguyên"), "B1: 409 đang xử lý không giữ thao tác đối soát");
    assert.ok(trangThaiGk().textContent.includes("chưa rõ"), "B1: thiếu trạng thái chưa rõ");
    assert.strictEqual(conLai(post("/api/crm/bao-gia/in")).length, 0, "B1: tự gửi lại (vòng lặp)");
    inBtn().click(); await chay();  // bấm lại nút In gốc khi chưa có FINAL → CÙNG khóa (không phát ý định mới)
    const i3 = cho(post("/api/crm/bao-gia/in"), "B1 In lại");
    assert.deepStrictEqual(JSON.parse(i3.opts.body), b1, "B1: In lại khi đang xử lý đổi khóa");
    i3.resolve(phanHoi(409, {error: "CRM_GK_LAN_KHONG_KHOP", message: "Chưa khớp"})); await chay();
    nut(gk(), "Đối soát y nguyên").click(); await chay();
    const i4 = cho(post("/api/crm/bao-gia/in"), "B1 đối soát");
    assert.deepStrictEqual(JSON.parse(i4.opts.body), b1, "B1: đối soát khác body/khóa");
    i4.resolve(phanHoi(200, {xuat_id: "x-9", trang_thai: "PDF_DAT", lap_lai: true})); await chay();
    assert.strictEqual(nutLai(), null, "B1: còn nút gửi lại/đối soát sau FINAL");
    cho(getBg, "B1 làm mới sau FINAL").resolve(phanHoi(200, CT("LO-1", 1))); await chay();
    inBtn().click(); await chay();  // ý định MỚI sau FINAL → khóa mới
    const i5 = cho(post("/api/crm/bao-gia/in"), "B1 In mới"), k5 = JSON.parse(i5.opts.body).khoa;
    assert.notStrictEqual(k5, b1.khoa, "B1: FINAL không nhả khóa");
    i5.resolve(phanHoi(409, {error: "CRM_G_IDEMPOTENCY_KHAC", message: "Khóa đã dùng cho yêu cầu khác"})); await chay();
    assert.strictEqual(nutLai(), null, "B1: 409 xung đột body bị coi là chưa rõ");
    inBtn().click(); await chay();
    const i6 = cho(post("/api/crm/bao-gia/in"), "B1 In sau xung đột");
    assert.notStrictEqual(JSON.parse(i6.opts.body).khoa, k5, "B1: 409 xác định không nhả khóa");
    i6.resolve(phanHoi(409, {error: "CRM_GK_REVISION_CU", message: "Revision cũ"})); await chay();
    assert.strictEqual(nutLai(), null, "B1: 409 revision cũ bị coi là chưa rõ");
    console.log("B1 đạt");
  }

  // ---------------------------------------------------------------- B2 Chuyển còn chờ → gõ cùng báo giá: thành công/lỗi muộn không đổi chế độ/đè nháp
  {
    const chuyen = () => nut(gk(), "Chuyển sang Soạn");
    chuyen().click(); await chay();
    const c1 = cho(post("/api/crm/bao-gia/chuyen"), "B2 Chuyển 1");
    o("bg-lo").value = "LO-B2"; o("bg-lo").dispatch("input");
    const nDs = dem(getDs), nSo = dem(c => c.url.startsWith("/api/crm/soan/"));
    datToast("");
    c1.resolve(phanHoi(200, {soan_id: "so-1", hop_dong_id: "hd-1", lap_lai: false})); await chay();
    assert.ok(o("bg-lo") && o("bg-lo").value === "LO-B2", "B2: Chuyển về muộn đổi chế độ/đè nháp");
    assert.deepStrictEqual([dem(getDs), dem(c => c.url.startsWith("/api/crm/soan/"))], [nDs, nSo], "B2: Chuyển về muộn vẫn mở GET danh sách/bản soạn");
    assert.ok(!trangThaiGk().textContent.includes("Đã chuyển") && !toastTxt().includes("Đã chuyển"), "B2: thông báo của ý định cũ");
    await lamMoiBg(CT("LO-1", 1));
    chuyen().click(); await chay();
    const c2 = cho(post("/api/crm/bao-gia/chuyen"), "B2 Chuyển 2");
    o("bg-lo").value = "LO-B2B"; o("bg-lo").dispatch("input");
    datToast("");
    c2.resolve(phanHoi(409, {error: "CRM_GK_DA_CHUYEN", message: "LOI-B2-CU"})); await chay();
    assert.ok(!trangThaiGk().textContent.includes("LOI-B2-CU") && !toastTxt().includes("LOI-B2-CU"), "B2: lỗi của ý định cũ hiện ra");
    assert.strictEqual(o("bg-lo").value, "LO-B2B");
    await lamMoiBg(CT("LO-1", 1));
    chuyen().click(); await chay();  // dương: không gõ → sang G3, danh sách rồi bản soạn
    cho(post("/api/crm/bao-gia/chuyen"), "B2 Chuyển 3").resolve(phanHoi(200, {soan_id: "so-1", hop_dong_id: "hd-1", lap_lai: false})); await chay();
    cho(getDs, "B2 danh sách sau chuyển").resolve(phanHoi(200, DS2(BH))); await chay();
    cho(getSo, "B2 GET bản soạn").resolve(phanHoi(200, SOm())); await chay();
    assert.strictEqual(o("so-f-so_hop_dong").value, "HĐ-1", "B2: Chuyển dương không mở bản soạn");
    console.log("B2 đạt");
  }

  // ---------------------------------------------------------------- B4 G3: chỉ đổi mẫu → bẩn, khóa Xuất tới revision mới; Xuất về muộn sau khi gõ
  {
    const xuat = () => nut(gk(), "Xuất DOCX");
    assert.ok(!xuat().disabled, "B4: Xuất khóa khi form = revision đã lưu");
    o("so-doi-so-1").value = "mau-2"; o("so-doi-so-1").dispatch("change");
    assert.ok(xuat().disabled, "B4: chỉ chọn mẫu khác mà Xuất không khóa");
    assert.ok(tim(gk(), e => e.dataset && e.dataset.lyChuaLuu && e.textContent.includes("chưa lưu")), "B4: thiếu lý do");
    xuat().click(); await chay();
    assert.strictEqual(dem(post("/api/crm/soan/xuat")), 0, "B4: Xuất gửi khi đổi mẫu chưa lưu");
    o("so-doi-ly-so-1").value = "Đổi sang mẫu v2"; o("so-doi-ly-so-1").dispatch("input");
    nut(gk(), "Lưu bản soạn").click(); await chay();
    const s = cho(post("/api/crm/soan/luu"), "B4 lưu đổi mẫu"), bs = JSON.parse(s.opts.body);
    assert.deepStrictEqual([bs.doi_mau_phien_ban_id, bs.ly_do, bs.expected_revision], ["mau-2", "Đổi sang mẫu v2", 1], "B4: body Lưu sai mẫu/lý do/revision");
    s.resolve(phanHoi(200, {soan_id: "so-1", revision: 2, lap_lai: false})); await chay();
    assert.ok(xuat().disabled, "B4: Xuất mở trước khi revision mới về form");
    cho(getDs, "B4 danh sách").resolve(phanHoi(200, DS2(BH))); await chay();
    assert.ok(xuat().disabled, "B4: Xuất mở khi mới có danh sách");
    const so2 = SOm(2); so2.mau = {...so2.mau, mau_phien_ban_id: "mau-2", phien_ban: 2}; so2.mau_hieu_luc = [];
    cho(getSo, "B4 bản soạn rev 2").resolve(phanHoi(200, so2)); await chay();
    assert.ok(!xuat().disabled, "B4: Xuất vẫn khóa sau khi revision mới đã nạp");
    xuat().click(); await chay();
    const x = cho(post("/api/crm/soan/xuat"), "B4 Xuất");
    assert.strictEqual(JSON.parse(x.opts.body).expected_revision, 2);
    o("so-f-so_hop_dong").value = "HĐ-B4"; o("so-f-so_hop_dong").dispatch("input");
    const nDs = dem(getDs);
    x.resolve(phanHoi(200, {xuat_id: "x-b4", trang_thai: "PDF_DAT", lap_lai: false})); await chay();
    assert.strictEqual(dem(getDs), nDs, "B4: Xuất về muộn vẫn làm mới");
    assert.ok(!trangThaiGk().textContent.includes("Xuất:"), "B4: thông báo Xuất của ý định cũ");
    assert.strictEqual(o("so-f-so_hop_dong").value, "HĐ-B4", "B4: nháp G3 bị đè");
    console.log("B4 đạt");
  }

  // ---------------------------------------------------------------- B3 Lưu mất ACK → gửi lại còn chờ → gõ tiếp: FINAL im lặng, revision ghi nhận; G7 lỗi muộn
  {
    tab("Báo giá").click(); await chay();
    await moBg("LO-1");
    o("bg-lo").value = "LO-B3"; o("bg-lo").dispatch("input");
    nut(gk(), "Lưu nháp").click(); await chay();
    const s1 = cho(post("/api/crm/bao-gia/luu"), "B3 lưu"), b1 = JSON.parse(s1.opts.body);
    s1.reject(new TypeError("Failed to fetch")); await chay();
    nut(gk(), "Gửi lại y nguyên").click(); await chay();
    const s2 = cho(post("/api/crm/bao-gia/luu"), "B3 gửi lại");
    assert.deepStrictEqual(JSON.parse(s2.opts.body), b1, "B3: gửi lại khác body/khóa");
    o("bg-lo").value = "LO-B3-TIEP"; o("bg-lo").dispatch("input");
    const nDs = dem(getDs);
    datToast("");
    s2.resolve(phanHoi(200, {bao_gia_id: "bg-1", revision: 7, lap_lai: false})); await chay();
    assert.strictEqual(dem(getDs), nDs, "B3: gửi lại về muộn vẫn làm mới/đè nháp");
    assert.ok(!toastTxt().includes("Đã lưu") && !trangThaiGk().textContent.includes("Đã lưu"), "B3: thông báo của ý định cũ");
    assert.strictEqual(o("bg-lo").value, "LO-B3-TIEP");
    assert.ok(nut(gk(), "In báo giá").disabled, "B3: In mở khi form còn thay đổi chưa lưu");
    nut(gk(), "Lưu nháp").click(); await chay();
    const s3 = cho(post("/api/crm/bao-gia/luu"), "B3 lưu 2"), b3 = JSON.parse(s3.opts.body);
    assert.notStrictEqual(b3.khoa, b1.khoa, "B3: ý định mới dùng lại khóa cũ");
    assert.deepStrictEqual([b3.bao_gia_id, b3.expected_revision, b3.du_lieu.don_vi.ma], ["bg-1", 7, "LO-B3-TIEP"], "B3: lần lưu sau không dựa revision đã ghi nhận");
    s3.resolve(phanHoi(200, {bao_gia_id: "bg-1", revision: 8, lap_lai: false})); await chay();
    cho(getDs, "B3 danh sách").resolve(phanHoi(200, DS2(BH))); await chay();
    cho(getBg, "B3 chi tiết").resolve(phanHoi(200, CT("LO-B3-TIEP", 8))); await chay();
    assert.ok(!nut(gk(), "In báo giá").disabled, "B3: In khóa sau khi revision mới đã nạp");
    o("bg-nguon").value = "DU_AN"; o("bg-nguon").dispatch("change"); await chay();
    o("bg-du-an").value = "da-1"; o("bg-du-an").dispatch("change");
    o("bg-g7").value = "GD1"; o("bg-g7").dispatch("input");
    nut(gk(), "Nạp bộ chuẩn").click(); await chay();
    const g = cho(c => c.method === "GET" && c.url.startsWith("/api/crm/bo-chuan?"), "B3 G7");
    o("bg-l-gc-0").value = "gõ khi G7 chờ"; o("bg-l-gc-0").dispatch("input");
    g.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(!trangThaiGk().textContent.includes("Mất kết nối"), "B3: lỗi G7 của lần nạp cũ hiện ra");
    assert.strictEqual(o("bg-l-gc-0").value, "gõ khi G7 chờ");
    await lamMoiBg(CT("LO-1", 8));
    console.log("B3 đạt");
  }

  // ---------------------------------------------------------------- B5 (BG-1b) lỗi mạng giữ kết quả cũ + một dòng báo + tự thử lại; lỗi 4xx hiện câu lỗi; ghi chú không gọi máy chủ
  {
    await traXem();  // yêu cầu xem-truoc còn treo từ B3 (thế hệ cũ, module đã bỏ) — dọn để cho() không lấy nhầm
    goVao("bg-l-gt-0", "60%", "change"); await chay();
    cho(postXem, "B5 60%").resolve(phanHoi(200, XEM(ketQua("= 600.000.000 VND")))); await chay();
    assert.strictEqual(mo(0).textContent, "= 600.000.000 VND");
    const el = o("bg-l-gt-0");
    goVao("bg-l-gt-0", "65%", "change"); await chay();
    const e2 = cho(postXem, "B5 65% mất mạng");
    e2.reject(new TypeError("Failed to fetch")); await chay();
    assert.strictEqual(mo(0).textContent, "= 600.000.000 VND", "B5: lỗi mạng làm mất kết quả cũ");
    assert.ok(ghiLoiTinh().textContent.includes("mất kết nối"), "B5: thiếu dòng báo lỗi mạng");
    assert.ok(!mo(0).className.includes("gk-cho") && o("bg-l-gt-0") === el, "B5: lỗi mạng làm vẽ lại form / kẹt '…'");
    tien(4999); await chay();
    assert.strictEqual(conLai(postXem).length, 0, "B5: tự thử lại quá sớm");
    tien(1); await chay();
    const e3 = cho(postXem, "B5 tự thử lại");
    assert.strictEqual(JSON.parse(e3.opts.body).du_lieu.lich[0].gia_tri_nhap, "65%", "B5: thử lại sai nội dung");
    e3.resolve(phanHoi(200, XEM(ketQua("= 650.000.000 VND")))); await chay();
    assert.deepStrictEqual([mo(0).textContent, ghiLoiTinh().textContent], ["= 650.000.000 VND", ""], "B5: thử lại xong mà còn dòng báo lỗi");
    // lỗi 4xx của máy chủ: hiện câu lỗi, giữ kết quả cũ, không tự thử lại
    goVao("bg-l-gt-0", "66%", "change"); await chay();
    cho(postXem, "B5 lỗi 400").resolve(phanHoi(400, {error: "CRM_G_YEU_CAU_SAI", message: "Mốc ngày dòng 1 không tồn tại."})); await chay();
    assert.ok(ghiLoiTinh().textContent.includes("Mốc ngày dòng 1 không tồn tại") && mo(0).textContent === "= 650.000.000 VND", "B5: lỗi 400 không hiện/mất kết quả cũ");
    tien(60000); await chay();
    assert.strictEqual(conLai(postXem).length, 0, "B5: tự thử lại sau lỗi 400");
    // ghi chú / mô tả lô / liên hệ không ảnh hưởng số tính → không gọi máy chủ, không "…"
    const n = dem(postXem);
    goVao("bg-l-gc-0", "ghi chú"); goVao("bg-lo-mt", "mô tả"); goVao("bg-khach-lh", "liên hệ"); goVao("bg-gc", "ghi chú chung");
    tien(2000); await chay();
    assert.strictEqual(dem(postXem), n, "B5: ghi chú gọi máy chủ tính");
    assert.ok(!mo(0).textContent.includes("…"), "B5: ghi chú làm hiện '…'");
    await traXem();
    console.log("B5 đạt");
  }

  // ================================================================ FIX03 — R1 định danh nháp MỚI, R2 fence hiển thị gốc trước/sau retry POST
  const postLuu = post("/api/crm/bao-gia/luu");
  const ctId = (id, lo, rev) => { const d = CT(lo, rev); d.bao_gia = {...d.bao_gia, id, revision_hien_hanh: rev}; return d; };
  const goLo = v => { o("bg-lo").value = v; o("bg-lo").dispatch("input"); };

  // ---------------------------------------------------------------- C1 (R1) MOI → MOI: ACK của nháp A không gán ID/revision cho nháp B
  {
    for (const c of conLai(() => true)) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
    // âm: Mới A → Lưu (tạo) còn chờ → "+ Báo giá mới" B → gõ B → ACK A
    nut(gk(), "+ Báo giá mới").click(); await chay();
    goLo("LO-A-MOI");
    nut(gk(), "Lưu nháp").click(); await chay();
    const a = cho(postLuu, "C1 tạo A"), ba = JSON.parse(a.opts.body);
    assert.deepStrictEqual([ba.bao_gia_id, ba.expected_revision], [null, null]);
    nut(gk(), "+ Báo giá mới").click(); await chay();
    goLo("LO-B-MOI");
    datToast("");
    const st0 = trangThaiGk().textContent, nDs = dem(getDs);
    a.resolve(phanHoi(200, {bao_gia_id: "bg-A", revision: 1, lap_lai: false})); await chay();
    assert.strictEqual(o("bg-lo").value, "LO-B-MOI", "C1: ACK A đè nháp B");
    assert.deepStrictEqual([toastTxt(), trangThaiGk().textContent, dem(getDs), dem(get("/api/crm/bao-gia/bg-A"))], ["", st0, nDs, 0], "C1: ACK A có hiệu ứng trên nháp B");
    nut(gk(), "Lưu nháp").click(); await chay();
    const b = cho(postLuu, "C1 tạo B"), bb = JSON.parse(b.opts.body);
    assert.deepStrictEqual([bb.bao_gia_id, bb.expected_revision, bb.du_lieu.don_vi.ma], [null, null, "LO-B-MOI"], "C1: Lưu B thành cập nhật A");
    assert.notStrictEqual(bb.khoa, ba.khoa, "C1: B dùng khóa của A");
    b.resolve(phanHoi(400, {error: "CRM_GK_YEU_CAU_SAI", message: "C1 dừng B"})); await chay();
    // âm: hai nháp mới có body TRÙNG không dùng chung khóa (phạm vi khóa = định danh nháp)
    nut(gk(), "+ Báo giá mới").click(); await chay();
    goLo("LO-TRUNG");
    nut(gk(), "Lưu nháp").click(); await chay();
    const a2 = cho(postLuu, "C1 tạo A2");
    nut(gk(), "+ Báo giá mới").click(); await chay();
    goLo("LO-TRUNG");
    nut(gk(), "Lưu nháp").click(); await chay();
    const b2 = cho(postLuu, "C1 tạo B2 (body trùng A2)");
    assert.deepStrictEqual(JSON.parse(b2.opts.body).du_lieu, JSON.parse(a2.opts.body).du_lieu);
    assert.notStrictEqual(JSON.parse(b2.opts.body).khoa, JSON.parse(a2.opts.body).khoa, "C1: hai nháp mới body trùng dùng chung khóa");
    a2.resolve(phanHoi(400, {error: "CRM_GK_YEU_CAU_SAI", message: "x"})); b2.resolve(phanHoi(400, {error: "CRM_GK_YEU_CAU_SAI", message: "x"})); await chay();
    // dương: CÙNG nháp mới, Lưu còn chờ → gõ tiếp → ACK → Lưu sau cập nhật đúng báo giá đã tạo, giữ nội dung gõ tiếp, không tạo bản thứ hai
    nut(gk(), "+ Báo giá mới").click(); await chay();
    goLo("LO-C");
    nut(gk(), "Lưu nháp").click(); await chay();
    const c1 = cho(postLuu, "C1 tạo C");
    goLo("LO-C-TIEP");
    c1.resolve(phanHoi(200, {bao_gia_id: "bg-C", revision: 1, lap_lai: false})); await chay();
    assert.strictEqual(o("bg-lo").value, "LO-C-TIEP");
    nut(gk(), "Lưu nháp").click(); await chay();
    const c2 = cho(postLuu, "C1 cập nhật C"), bc2 = JSON.parse(c2.opts.body);
    assert.deepStrictEqual([bc2.bao_gia_id, bc2.expected_revision, bc2.du_lieu.don_vi.ma], ["bg-C", 1, "LO-C-TIEP"], "C1: cùng nháp không giữ ID/revision đã ACK");
    c2.resolve(phanHoi(200, {bao_gia_id: "bg-C", revision: 2, lap_lai: false})); await chay();
    cho(getDs, "C1 danh sách").resolve(phanHoi(200, DS2(BH))); await chay();
    cho(get("/api/crm/bao-gia/bg-C"), "C1 chi tiết C").resolve(phanHoi(200, ctId("bg-C", "LO-C-TIEP", 2))); await chay();
    assert.strictEqual(o("bg-lo").value, "LO-C-TIEP");
    // dương: cùng nháp mới, tạo MẤT ACK → Lưu lại bị chặn (không tạo bản 2) → gửi lại → 409 đang xử lý → đối soát → FINAL cùng body/khóa
    nut(gk(), "+ Báo giá mới").click(); await chay();
    goLo("LO-D");
    nut(gk(), "Lưu nháp").click(); await chay();
    const d1 = cho(postLuu, "C1 tạo D"), bd = JSON.parse(d1.opts.body);
    d1.reject(new TypeError("Failed to fetch")); await chay();
    nut(gk(), "Lưu nháp").click(); await chay();
    assert.strictEqual(conLai(postLuu).length, 0, "C1: lần tạo chưa rõ mà Lưu lại vẫn gửi (nguy cơ báo giá thứ hai)");
    assert.ok(trangThaiGk().textContent.includes("chưa rõ"));
    nut(gk(), "Gửi lại y nguyên").click(); await chay();
    const d2 = cho(postLuu, "C1 gửi lại D");
    assert.deepStrictEqual(JSON.parse(d2.opts.body), bd);
    d2.resolve(phanHoi(409, {error: "CRM_GK_DANG_XU_LY", message: "Đang xử lý"})); await chay();
    nut(gk(), "Đối soát y nguyên").click(); await chay();
    const d3 = cho(postLuu, "C1 đối soát D");
    assert.deepStrictEqual(JSON.parse(d3.opts.body), bd);
    d3.resolve(phanHoi(200, {bao_gia_id: "bg-D", revision: 1, lap_lai: true})); await chay();
    cho(getDs, "C1 danh sách D").resolve(phanHoi(200, DS2(BH))); await chay();
    cho(get("/api/crm/bao-gia/bg-D"), "C1 chi tiết D").resolve(phanHoi(200, ctId("bg-D", "LO-D", 1))); await chay();
    // tạo chưa rõ → gõ tiếp cùng nháp → Lưu bị chặn; đối soát lần gốc (body/khóa gốc, không hiệu ứng lên form mới) → Lưu sau = cập nhật
    nut(gk(), "+ Báo giá mới").click(); await chay();
    goLo("LO-E");
    nut(gk(), "Lưu nháp").click(); await chay();
    const e1 = cho(postLuu, "C1 tạo E"), be = JSON.parse(e1.opts.body);
    e1.reject(new TypeError("Failed to fetch")); await chay();
    goLo("LO-E-TIEP");
    nut(gk(), "Lưu nháp").click(); await chay();
    assert.strictEqual(conLai(postLuu).length, 0, "C1: tạo bản thứ hai khi lần tạo trước chưa rõ");
    const stE = trangThaiGk().textContent;
    nut(gk(), "Gửi lại y nguyên").click(); await chay();
    const e2 = cho(postLuu, "C1 đối soát E");
    assert.deepStrictEqual(JSON.parse(e2.opts.body), be, "C1: ghép body gốc với form mới");
    assert.deepStrictEqual([trangThaiGk().textContent, o("bg-lo").value], [stE, "LO-E-TIEP"]);
    e2.resolve(phanHoi(200, {bao_gia_id: "bg-E", revision: 1, lap_lai: false})); await chay();
    assert.deepStrictEqual([trangThaiGk().textContent, o("bg-lo").value, dem(get("/api/crm/bao-gia/bg-E"))], [stE, "LO-E-TIEP", 0]);
    nut(gk(), "Lưu nháp").click(); await chay();
    const e3 = cho(postLuu, "C1 cập nhật E"), be3 = JSON.parse(e3.opts.body);
    assert.deepStrictEqual([be3.bao_gia_id, be3.expected_revision, be3.du_lieu.don_vi.ma], ["bg-E", 1, "LO-E-TIEP"]);
    e3.resolve(phanHoi(400, {error: "CRM_GK_YEU_CAU_SAI", message: "dừng"})); await chay();
    console.log("C1 đạt");
  }

  // ---------------------------------------------------------------- C2 (R2) gõ B TRƯỚC khi bấm gửi lại A: không hiệu ứng cũ trước/sau POST
  {
    await moBg("LO-1");
    goLo("LO-R2-A");
    nut(gk(), "Lưu nháp").click(); await chay();
    const s1 = cho(postLuu, "C2 lưu A"), bA = JSON.parse(s1.opts.body);
    s1.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(nut(gk(), "Gửi lại y nguyên"));
    goLo("LO-R2-B");  // B trên cùng đối tượng, TRƯỚC khi bấm gửi lại A
    datToast("T-B");
    const stB = trangThaiGk().textContent;
    const truocA = dem(postLuu);
    nut(gk(), "Gửi lại y nguyên").click(); await chay();
    // ngay sau click, trước phản hồi
    assert.strictEqual(dem(postLuu) - truocA, 1, "C2: gửi lại A không gửi đúng một POST");
    const s2 = cho(postLuu, "C2 gửi lại A");
    assert.deepStrictEqual(JSON.parse(s2.opts.body), bA, "C2: gửi lại A khác body/khóa gốc");
    assert.deepStrictEqual([trangThaiGk().textContent, toastTxt(), o("bg-lo").value], [stB, "T-B", "LO-R2-B"], "C2: click gửi lại A sửa trạng thái/toast/form B");
    assert.ok(nut(gk(), "Gửi lại y nguyên"), "C2: click gửi lại A xóa trạng thái gửi lại trước khi có kết quả");
    // thành công muộn
    const nDs = dem(getDs);
    s2.resolve(phanHoi(200, {bao_gia_id: "bg-1", revision: 2, lap_lai: false})); await chay();
    assert.deepStrictEqual([trangThaiGk().textContent, toastTxt(), o("bg-lo").value, dem(getDs)], [stB, "T-B", "LO-R2-B", nDs], "C2: FINAL A có hiệu ứng trên B");
    assert.ok(nut(gk(), "In báo giá").disabled);
    nut(gk(), "Gửi lại y nguyên").click(); await chay();
    assert.strictEqual(dem(postLuu) - truocA, 1, "C2: nút cũ gửi lại ý định đã có kết quả cuối");
    // UNKNOWN: Lưu B (revision đã ghi nhận) → mất ACK → gõ C → gửi lại B
    nut(gk(), "Lưu nháp").click(); await chay();
    const t1 = cho(postLuu, "C2 lưu B"), bB = JSON.parse(t1.opts.body);
    assert.deepStrictEqual([bB.expected_revision, bB.du_lieu.don_vi.ma], [2, "LO-R2-B"]);
    t1.reject(new TypeError("Failed to fetch")); await chay();
    goLo("LO-R2-C");
    datToast("T-C");
    const stC = trangThaiGk().textContent;
    nut(gk(), "Gửi lại y nguyên").click(); await chay();
    const t2 = cho(postLuu, "C2 gửi lại B");
    assert.deepStrictEqual(JSON.parse(t2.opts.body), bB);
    assert.deepStrictEqual([trangThaiGk().textContent, toastTxt(), o("bg-lo").value], [stC, "T-C", "LO-R2-C"]);
    t2.reject(new TypeError("Failed to fetch")); await chay();
    assert.deepStrictEqual([trangThaiGk().textContent, toastTxt(), o("bg-lo").value], [stC, "T-C", "LO-R2-C"], "C2: UNKNOWN của B có hiệu ứng trên C");
    // vận chuyển cũ dưới lựa chọn khác: không gửi
    nut(gk(), "+ Báo giá mới").click(); await chay();
    const truocMoi = dem(postLuu);
    nut(gk(), "Gửi lại y nguyên").click(); await chay();
    assert.strictEqual(dem(postLuu), truocMoi, "C2: gửi lại B dưới lựa chọn khác");
    // lỗi xác định khi gửi lại (mở lại đúng đối tượng; form đã khác ý định B)
    await moBg("LO-1");
    goLo("LO-R2-D");
    datToast("T-D");
    const stD = trangThaiGk().textContent;
    nut(gk(), "Gửi lại y nguyên").click(); await chay();
    const t3 = cho(postLuu, "C2 gửi lại B lần 2");
    assert.deepStrictEqual(JSON.parse(t3.opts.body), bB);
    t3.resolve(phanHoi(409, {error: "CRM_GK_REVISION_CU", message: "LOI-B-CU"})); await chay();
    assert.deepStrictEqual([trangThaiGk().textContent, toastTxt(), o("bg-lo").value], [stD, "T-D", "LO-R2-D"], "C2: lỗi xác định của B hiện trên D");
    // dương hiện hành: không gõ sau lỗi → gửi lại hoàn tất đúng MỘT lần, làm mới đúng một lần
    await lamMoiBg(CT("LO-1", 3));
    goLo("LO-R2-E");
    nut(gk(), "Lưu nháp").click(); await chay();
    const u1 = cho(postLuu, "C2 lưu E"), bE = JSON.parse(u1.opts.body);
    u1.reject(new TypeError("Failed to fetch")); await chay();
    const truocE = dem(postLuu), dsE = dem(getDs);
    datToast("");
    nut(gk(), "Gửi lại y nguyên").click(); await chay();
    assert.strictEqual(nut(gk(), "Gửi lại y nguyên"), null, "C2 dương: nút gửi lại không được dọn khi form vẫn của ý định");
    assert.ok(trangThaiGk().textContent.includes("Đang gửi"));
    const u2 = cho(postLuu, "C2 gửi lại E");
    assert.deepStrictEqual(JSON.parse(u2.opts.body), bE);
    u2.resolve(phanHoi(200, {bao_gia_id: "bg-1", revision: 4, lap_lai: false})); await chay();
    assert.ok(toastTxt().includes("Đã lưu nháp"), "C2 dương: thiếu toast");
    assert.deepStrictEqual([dem(postLuu) - truocE, dem(getDs) - dsE], [1, 1], "C2 dương: không hoàn tất đúng một lần");
    cho(getDs, "C2 danh sách E").resolve(phanHoi(200, DS2(BH))); await chay();
    cho(getBg, "C2 chi tiết E").resolve(phanHoi(200, CT("LO-R2-E", 4))); await chay();
    assert.ok(!nut(gk(), "In báo giá").disabled);
    console.log("C2 đạt");
  }

  if (loiNgoai.length) throw loiNgoai[0];
  console.log("Tất cả ca đạt");
}
main().catch(e => { console.error(e); process.exit(1); });
