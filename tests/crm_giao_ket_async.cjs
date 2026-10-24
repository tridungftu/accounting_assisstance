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
//  B5  sửa % → số tự tính + tổng đang hiện hết hiệu lực NGAY trên DOM (không vẽ lại/đổi tab); tính thử về muộn không khôi phục; tính thử hiện hành hiện.
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
  const ctx = {document, Node: El, console, setTimeout, clearTimeout, Promise, Map, Set, JSON, Math, Date, Number, String, Object, Array, Error, TypeError, SyntaxError,
    encodeURIComponent, decodeURIComponent, URLSearchParams, location: {hash: "#hopdong"}, crypto: {randomUUID: () => "uuid-" + (++soUuid)},
    URL: {createObjectURL: () => "blob:x", revokeObjectURL() {}}, fetch, navigator: {}};
  ctx.window = ctx;
  ctx.addEventListener = () => {};
  vm.createContext(ctx);
  return {ctx, document, calls};
}

const phanHoi = (status, data, blobSize) => ({ok: status >= 200 && status < 300, status, headers: {get: () => "application/json"},
  json: async () => data, blob: async () => new BLOB_GOC([new Uint8Array(blobSize ?? 0)])});
const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 10) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
const nut = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));

const DEMO = [{dang_nhap: "MO_PHONG_CRM_G_BH_A", vai_tro: "BAN_HANG"}, {dang_nhap: "MO_PHONG_CRM_G_KT_A", vai_tro: "KE_TOAN"}];
const NGUOI = l => ({dang_nhap: l, vai_tro: l.includes("BH") ? "BAN_HANG" : "KE_TOAN", phap_nhan: ["PN_DEMO_A"], hanh_dong: [], xem_tien: false, duoc: {}});
const CRM = l => ({cau_hinh: true, danh_tinh_demo: DEMO, nguoi: NGUOI(l), ngay_nghiep_vu: "2026-10-21", mau: [], m1_cau_hinh: false, tien_mau: [],
  ho_so: [], hop_dong: [], tien: [], file_soat: [], danh_muc: {doi_tac: [], du_an: []}});
const DS = l => ({nguoi: {dang_nhap: l, vai_tro: "BAN_HANG"}, ghi_nguon: {san_sang: true}, loai_hinh: [{id: "lh-1", ma: "DT-KCN", phien_ban: 2, phap_nhan: "PN_DEMO_A"}],
  du_an: [{id: "da-1", ma_junsky: "DA_KCN_DEMO", phap_nhan: "PN_DEMO_A"}], khach: [],
  bao_gia: [{id: "bg-1", so_bao_gia: "BG-2026-00001", ngay: "2026-10-21", khach: "KHÁCH DEMO", lo_can: "LO-1", tong_hien_thi: "1.000.000.000 VND",
    trang_thai: "NHAP", tao_boi: l}], soan: []});
const CT = (lo = "LO-1", rev = 1, xuat = []) => ({bao_gia: {id: "bg-1", so_bao_gia: "BG-2026-00001", trang_thai: "NHAP", revision_hien_hanh: rev, loai_hinh_id: "lh-1"},
  du_lieu: {loai_hinh_id: "lh-1", du_an_id: "da-1", giai_doan_g7: null, nguon_lich: "KHACH", don_vi: {ma: lo, mo_ta: null, can_cu: null},
    khach: {doi_tac_id: null, du_thao: {ten: "KHÁCH DEMO", lien_he: null}}, gia: {tien_te: "VND", don_gia: null, dien_tich: null, tong: "1000000000", co_so_thue: "NET", vat_phan_tram: null},
    fx: null, phi_bao_tri: null, lich: [{dong_id: "d-1", lan: "1", loai: "PERCENT", ty_le: "100", so_tien: null, tien_te: null, moc_loai: null, moc_ngay: null, moc_su_kien: null, ghi_chu: null}],
    het_han: null, ghi_chu: null},
  tinh: {tien_te: "VND", tong_minor: "1000000000", tong_ty_le: "100", dong: [], thieu: [], canh_bao: [], chan_in: []}, g7: null, revisions: [], xuat,
  mau_hieu_luc: [{mau_phien_ban_id: "mau-1", ma_mau: "HD", phien_ban: 1, valid_from: "2026-10-19"}], soan_id: null});

async function main() {
  const {ctx, document, calls} = moiTruong();
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
  async function moBg(lo = "LO-1") { nut(gk(), "Mở").click(); await chay(); cho(get("/api/crm/bao-gia/bg-1"), "GET chi tiết").resolve(phanHoi(200, CT(lo))); await chay(); }
  const o = id => $("gk-" + id);

  // khởi động: CRM thật cho vai BH; module khác 404 có chủ đích
  for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM("MO_PHONG_CRM_G_BH_A"))); }
  await traKhac();
  await traDs("MO_PHONG_CRM_G_BH_A");
  await traKhac();

  // ---------------------------------------------------------------- P0 dương
  await moBg();
  assert.strictEqual(o("bg-lo").value, "LO-1", "P0: form không ghi dữ liệu máy chủ");
  nut(gk(), "Lưu nháp").click(); await chay();
  const p0 = cho(post("/api/crm/bao-gia/luu"), "POST lưu P0");
  const b0 = JSON.parse(p0.opts.body);
  assert.deepStrictEqual([b0.bao_gia_id, b0.expected_revision, b0.du_lieu.don_vi.ma, b0.du_lieu.gia.tong, b0.du_lieu.lich[0].dong_id], ["bg-1", 1, "LO-1", "1000000000", "d-1"]);
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
    chanIn.tinh = {...chanIn.tinh, tong_ty_le: "40", chan_in: [{ma: "TONG_TY_LE_KHAC_100", thong_bao: "Tổng tỷ lệ = 40% (phải 100%)."}]};
    cho(get("/api/crm/bao-gia/bg-1"), "A7 chi tiết").resolve(phanHoi(200, chanIn)); await chay();
    assert.strictEqual(o("bg-lo").value, "LO-A7");
    assert.ok(!inBtn().disabled, "A7: đã lưu + nạp revision mà In vẫn khóa");
    assert.ok(!nut(gk(), "Lưu nháp").disabled && !chuyen().disabled, "A7: cổng In (tổng % khác 100) khóa Lưu/Chuyển");
    console.log("A7 đạt");
  }

  // ---------------------------------------------------------------- A8 nạp G7 AMOUNT VND/USD chính xác
  {
    o("bg-nguon").value = "DU_AN"; o("bg-nguon").dispatch("change"); await chay();
    o("bg-du-an").value = "da-1"; o("bg-du-an").dispatch("change");
    o("bg-g7").value = "GD1"; o("bg-g7").dispatch("input");
    const G7 = rows => ({trang_thai: "HIEU_LUC", version: {phien_ban: 3}, rows});
    nut(gk(), "Nạp bộ chuẩn").click(); await chay();
    cho(c => c.method === "GET" && c.url === "/api/crm/bo-chuan?du_an_id=da-1&giai_doan=GD1", "GET G7").resolve(phanHoi(200, G7([
      {lan: "1", gia_tri_loai: "AMOUNT", gia_tri_thap_phan: null, so_tien_minor: "123456", tien_te: "USD", moc_loai: "NGAY", moc_ngay: "2026-12-01", moc_su_kien: null, ghi_chu: "đợt 1"},
      {lan: "2", gia_tri_loai: "AMOUNT", gia_tri_thap_phan: null, so_tien_minor: "5000000", tien_te: "VND", moc_loai: "SU_KIEN", moc_ngay: null, moc_su_kien: "BAN_GIAO", ghi_chu: null},
      {lan: "3", gia_tri_loai: "PERCENT", gia_tri_thap_phan: "10", so_tien_minor: null, tien_te: null, moc_loai: null, moc_ngay: null, moc_su_kien: null, ghi_chu: null},
      {lan: "4", gia_tri_loai: "AMOUNT", gia_tri_thap_phan: null, so_tien_minor: "5", tien_te: "USD", moc_loai: null, moc_ngay: null, moc_su_kien: null, ghi_chu: null}])));
    await chay();
    assert.deepStrictEqual([0, 1, 2, 3].map(i => [o(`bg-l-loai-${i}`).value, o(`bg-l-st-${i}`).value, o(`bg-l-tt-${i}`).value, o(`bg-l-tl-${i}`).value]),
      [["AMOUNT", "1234.56", "USD", ""], ["AMOUNT", "5000000", "VND", ""], ["PERCENT", "", "", "10"], ["AMOUNT", "0.05", "USD", ""]], "A8: AMOUNT mất/sai số tiền/tiền tệ");
    nut(gk(), "Lưu nháp").click(); await chay();
    const p = cho(post("/api/crm/bao-gia/luu"), "POST A8");
    assert.deepStrictEqual(JSON.parse(p.opts.body).du_lieu.lich.map(r => [r.lan, r.loai, r.ty_le, r.so_tien, r.tien_te, r.moc_loai, r.moc_ngay, r.moc_su_kien, r.ghi_chu]),
      [["1", "AMOUNT", null, "1234.56", "USD", "NGAY", "2026-12-01", null, "đợt 1"], ["2", "AMOUNT", null, "5000000", "VND", "SU_KIEN", null, "BAN_GIAO", null],
       ["3", "PERCENT", "10", null, null, null, null, null, null], ["4", "AMOUNT", null, "0.05", "USD", null, null, null, null]], "A8: body Lưu sai lịch G7");
    p.resolve(phanHoi(409, {error: "CRM_GK_REVISION_CU", message: "A8 không lưu"})); await chay();
    nut(gk(), "Nạp bộ chuẩn").click(); await chay();
    cho(c => c.method === "GET" && c.url.startsWith("/api/crm/bo-chuan?"), "GET G7 lạ").resolve(phanHoi(200, G7([
      {lan: "1", gia_tri_loai: "AMOUNT", so_tien_minor: "100", tien_te: "EUR", moc_loai: null, moc_ngay: null, moc_su_kien: null, ghi_chu: null}])));
    await chay();
    assert.strictEqual(o("bg-l-st-0").value, "1234.56", "A8: tiền tệ lạ vẫn nạp/đè lịch");
    assert.ok(trangThaiGk().textContent.includes("không nạp"), "A8: thiếu thông báo không nạp");
    console.log("A8 đạt");
  }

  // ---------------------------------------------------------------- A9 Tính thử (máy chủ tính) + phía tự tính chỉ đọc; kết quả cũ không áp form đã đổi
  {
    nut(gk(), "Tính thử").click(); await chay();
    const x = cho(post("/api/crm/bao-gia/xem-truoc"), "POST tính thử");
    assert.deepStrictEqual(Object.keys(JSON.parse(x.opts.body)), ["du_lieu"], "A9: tính thử gửi khóa/trường thừa");
    x.resolve(phanHoi(200, {du_lieu_sha256: "x", tinh: {tien_te: "USD", tong_minor: "1000000", dong: [
      {so_tien_minor: "123456", ty_le: "12.3456", loi: []}, {so_tien_minor: null, ty_le: null, loi: ["KHAC_TIEN_TE"]},
      {so_tien_minor: "100000", ty_le: "10", loi: []}, {so_tien_minor: "5", ty_le: "0.0005", loi: []}],
      vnd_tham_chieu: {tong: "25000000000", dong: ["30864000", null, "25000000", "1250"]}, thieu: [], canh_bao: [], chan_in: []}}));
    await chay();
    let t = tuTinh();
    assert.ok(t[0].includes("= 12.3456%") && t[0].includes("VND tham chiếu 30864000"), "A9 dòng 1: " + t[0]);
    assert.ok(t[1].includes("KHAC_TIEN_TE"), "A9 dòng 2: " + t[1]);
    assert.ok(t[2].includes("= 1000.00 USD") && t[2].includes("VND tham chiếu 25000000"), "A9 dòng 3: " + t[2]);
    assert.ok(t[3].includes("= 0.0005%") && t[3].includes("VND tham chiếu 1250"), "A9 dòng 4: " + t[3]);
    o("bg-l-gc-1").value = "đổi"; o("bg-l-gc-1").dispatch("input");
    nut(gk(), "Báo giá (G2)").click(); await chay();
    assert.ok(tuTinh()[0].includes("chưa tính"), "A9: kết quả tính thử cũ hiện cho form đã đổi");
    nut(gk(), "Tính thử").click(); await chay();
    const x2 = cho(post("/api/crm/bao-gia/xem-truoc"), "POST tính thử 2");
    o("bg-l-gc-1").value = "đổi nữa"; o("bg-l-gc-1").dispatch("input");
    x2.resolve(phanHoi(200, {du_lieu_sha256: "y", tinh: {tien_te: "USD", dong: [{so_tien_minor: "1", ty_le: "99", loi: []}], vnd_tham_chieu: null}})); await chay();
    nut(gk(), "Báo giá (G2)").click(); await chay();
    assert.ok(!tuTinh()[0].includes("99"), "A9: kết quả tính thử về muộn được áp lên form đã đổi");
    console.log("A9 đạt");
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
    nut(gk(), "Soạn hợp đồng (G3)").click(); await chay();
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
    nut(gk(), "Báo giá (G2)").click(); await chay();
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
    nut(gk(), "Báo giá (G2)").click(); await chay();
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

  // ---------------------------------------------------------------- B5 số tự tính đang hiện hết hiệu lực NGAY trên DOM khi sửa (không vẽ lại, không đổi tab)
  {
    const tinh = (minor, tl) => ({du_lieu_sha256: "h", tinh: {tien_te: "VND", tong_minor: "1000000000", tong_ty_le: tl, dong: [{so_tien_minor: minor, ty_le: tl, loi: []}],
      vnd_tham_chieu: null, thieu: [], canh_bao: [], chan_in: []}});
    nut(gk(), "Tính thử").click(); await chay();
    cho(post("/api/crm/bao-gia/xem-truoc"), "B5 tính thử").resolve(phanHoi(200, tinh("1000000000", "100"))); await chay();
    assert.ok(tuTinh()[0].includes("= 1000000000 VND"), "B5 dương: " + tuTinh()[0]);
    const el = o("bg-l-tl-0");
    el.value = "90"; el.dispatch("input");  // KHÔNG chay(), KHÔNG đổi tab
    assert.strictEqual(o("bg-l-tl-0"), el, "B5: sửa làm vẽ lại form (mất caret)");
    const tts = tatCa(gk(), e => e._cls && e._cls.has("gk-tu-tinh"));
    assert.ok(tts.length && tts.every(e => e.textContent.includes("đã sửa") && e.dataset.hetHieuLuc === "1"), "B5: số tự tính cũ vẫn hiện như hiệu lực");
    assert.ok(!tuTinh()[0].includes("1000000000"), "B5: còn số cũ");
    assert.ok(tim(gk(), e => e.dataset && e.dataset.kiemTong).textContent.startsWith("[Revision đã lưu"), "B5: tổng/VND cũ không gắn nhãn revision đã lưu");
    nut(gk(), "Tính thử").click(); await chay();
    const x1 = cho(post("/api/crm/bao-gia/xem-truoc"), "B5 tính thử 2");
    assert.strictEqual(JSON.parse(x1.opts.body).du_lieu.lich[0].ty_le, "90");
    o("bg-l-tl-0").value = "80"; o("bg-l-tl-0").dispatch("input");
    x1.resolve(phanHoi(200, tinh("900000000", "90"))); await chay();
    assert.ok(!tuTinh()[0].includes("900000000"), "B5: tính thử về muộn khôi phục số lên form đã đổi");
    nut(gk(), "Tính thử").click(); await chay();
    const x2 = cho(post("/api/crm/bao-gia/xem-truoc"), "B5 tính thử 3");
    assert.strictEqual(JSON.parse(x2.opts.body).du_lieu.lich[0].ty_le, "80");
    x2.resolve(phanHoi(200, tinh("800000000", "80"))); await chay();
    assert.ok(tuTinh()[0].includes("= 800000000 VND"), "B5: tính thử hiện hành không hiện");
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
