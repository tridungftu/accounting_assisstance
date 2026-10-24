"use strict";
// CRM-41-04A — kiểm bất đồng bộ G4 ký lần đầu trên MÃ THẬT app.js + crm_g.js (khối #crm-gk), không phải trình duyệt: DOM giả tối thiểu (cùng mẫu
// tests/crm_giao_ket_async.cjs), fetch trả Promise do ca điều khiển (treo, đảo thứ tự, mất kết nối, blob trễ). File là đối tượng giả {name,size,lastModified}.
// CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN). Root chạy: `node tests/crm_ky_ket_async.cjs` (Node ≥ 18). Mã thoát 0 = mọi ca đạt.
// Không ghi/xóa tệp, không mạng, không tiến trình con. Đây là MOCK trình duyệt — không chứng minh GUI thật.
// Ca (handoff §7.9):
//  K0  dương: mở bản soạn CHO_KY → GET điều kiện ký → nút "Ký kết…" bật → dialog hiện căn cứ (bản xuất/hash/tóm tắt).
//  K1  thiếu tệp / thiếu Có-Không / Có thiếu mô tả → 0 POST.
//  K2  bấm lặp khi POST còn chờ → đúng 1 POST; header chỉ trường cho phép (co_sua boolean, không actor/trạng thái/hash).
//  K3  mất kết nối → giữ ý định; ý định MỚI bị chặn; "Gửi lại bản ký y nguyên" gửi ĐÚNG File + header + khóa.
//  K4  đổi vai khi POST gửi lại còn chờ → ACK muộn im lặng (không toast/làm mới); vai khác không thấy nút gửi lại.
//  K5  chưa rõ → đổi vai đi rồi về → nút gửi lại vẫn còn cho đúng vai/bản soạn; 409 CRM_KY_XUAT_CU → đóng dialog + tải lại căn cứ, nhả ý định.
//  K6  thành công → "Đã ký — chờ kế toán kiểm" (không "Đã chuyển"), G5 trung thực; làm mới.
//  K7  DA_KY: không Lưu/Xuất/đổi mẫu, ô nhập vô hiệu, khối bản ký; tải PDF bản ký: dương click 1 lần; blob về sau khi đổi vai → không click.
//  K8  GET điều kiện ký cũ về trễ không lùi trạng thái; quyen.ky=false → nút vô hiệu + lý do phạm vi.
//  FIX04 (CODE_ONLY, NOT_RUN — mock DOM, không phải trình duyệt; mock ACK KHÔNG phải actual G3/PG positive):
//  K9  ACK 2xx hỏng/lệch ({} / null / JSON hỏng / sai bản soạn-HĐ-trạng thái-revision-bản xuất-ngày-co_sua-độ dài-hash G3-G5/thiếu ky_id) → CHƯA RÕ:
//      không nhãn Đã ký, không đóng dialog/xóa nháp, không GET; gửi lại ĐÚNG File + header + khóa; chỉ ACK typed đúng định danh mới FINAL.
//  K10 POST gốc + gửi lại đang bay qua vai A→B→A (B không bị khóa), G3→G2→G3, nhập form mới → lỗi/ACK cũ im lặng, nhả đúng bản ghi, giữ CHƯA RÕ
//      của A; GET làm mới dùng guard chụp lúc gửi (form đổi sau ACK → không GET chi tiết).
//  K11 tải PDF bản ký: headers đã về, blob() là Promise điều khiển; rời #hopdong rồi về (và chỉ rời) → không click; đối chứng dương sau khi về.
//  K12 U2 File-only (CODE_ONLY, NOT_RUN): (a) POST gốc còn bay, (b) gửi lại y nguyên của ý định CHƯA RÕ còn bay — CHỈ đổi File (ngày/người/Có-Không
//      giữ nguyên) → ACK HỢP LỆ cũ im lặng (không toast/trạng thái/đóng dialog/xóa File-nháp/GET); File/form mới còn; ý định File mới gửi khóa mới.
// Harness: setTimeout tiêm vào vm CHỈ unref timer dọn URL 60000ms (revokeObjectURL) để không giữ event loop Node ~60s; callback/độ trễ/thứ tự
// giữ nguyên, mọi timer khác (0ms chờ, 800ms thử lại phiên, toast) không đổi. Listener hashchange chỉ thu của crm_g.js để mô phỏng điều hướng.
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
  // chỉ timer dọn URL 60000ms (crm_g.js taiGoc/taiTep/taiBanKy; app.js tải) được unref — vẫn chạy nếu tiến trình còn sống, không giữ event loop
  const henGio = (fn, ms, ...a) => { const t = setTimeout(fn, ms, ...a); if (ms === 60000 && t && typeof t.unref === "function") t.unref(); return t; };
  const ctx = {document, Node: El, console, setTimeout: henGio, clearTimeout, Promise, Map, Set, JSON, Math, Date, Number, String, Object, Array, Error, TypeError, SyntaxError,
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
async function chay(n = 12) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
const nut = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));

const BH = "MO_PHONG_CRM_G_BH_A", KT = "MO_PHONG_CRM_G_KT_A";
const DEMO = [{dang_nhap: BH, vai_tro: "BAN_HANG"}, {dang_nhap: KT, vai_tro: "KE_TOAN"}];
const NGUOI = l => ({dang_nhap: l, vai_tro: l.includes("BH") ? "BAN_HANG" : "KE_TOAN", phap_nhan: ["PN_DEMO_A"], hanh_dong: [], xem_tien: false, duoc: {}});
const CRM = l => ({cau_hinh: true, danh_tinh_demo: DEMO, nguoi: NGUOI(l), ngay_nghiep_vu: "2026-10-21", mau: [], m1_cau_hinh: false, tien_mau: [],
  ho_so: [], hop_dong: [], tien: [], file_soat: [], danh_muc: {doi_tac: [], du_an: []}});
const DS = (l, tt = "CHO_KY") => ({nguoi: {dang_nhap: l, vai_tro: l.includes("BH") ? "BAN_HANG" : "KE_TOAN"}, ghi_nguon: {san_sang: true},
  loai_hinh: [{id: "lh-1", ma: "DT-KCN", phien_ban: 2, phap_nhan: "PN_DEMO_A"}], du_an: [{id: "da-1", ma_junsky: "DA_KCN_DEMO", phap_nhan: "PN_DEMO_A"}], khach: [],
  bao_gia: [], soan: [{id: "so-1", trang_thai: tt, revision_hien_hanh: 2, ma_noi_bo: "HD-NB-1", so_bao_gia: "BG-2026-00001"}]});
const BG_DL = {loai_hinh_id: "lh-1", du_an_id: "da-1", giai_doan_g7: null, nguon_lich: "KHACH", don_vi: {ma: "LO-1", mo_ta: null, can_cu: null},
  khach: {doi_tac_id: null, du_thao: {ten: "KHÁCH DEMO", lien_he: null}}, gia: {tien_te: "VND", don_gia: null, dien_tich: null, tong: "1000000000", co_so_thue: "NET", vat_phan_tram: null},
  fx: null, phi_bao_tri: null, lich: [{dong_id: "d-1", lan: "1", loai: "PERCENT", ty_le: "100", so_tien: null, tien_te: null, moc_loai: null, moc_ngay: null, moc_su_kien: null, ghi_chu: null}],
  het_han: null, ghi_chu: null};
const SO = (tt = "CHO_KY") => ({soan: {id: "so-1", hop_dong_id: "hd-1", ma_noi_bo: "HD-NB-1", so_bao_gia: "BG-2026-00001", trang_thai: tt,
  revision_hien_hanh: 2, loai_hinh_id: "lh-1", mau_phien_ban_id: "mau-1"}, du_lieu: {gia_tri_truong: {so_hop_dong: "HĐ-1"}, bao_gia: BG_DL},
  tinh: {tien_te: "VND", tong_minor: "1000000000", tong_ty_le: "100", dong: [], thieu: [], canh_bao: [], chan_in: []},
  mau: {mau_phien_ban_id: "mau-1", ma_mau: "HD", phien_ban: 1, ten_tep: "m.docx", raw_sha256: "x"},
  danh_muc: [{khoa: "so_hop_dong", kieu: "text", nhan: "Số HĐ", nhom: "Chung", bat_buoc: true}],
  kiem: {nhom: {Chung: [{khoa: "so_hop_dong", kieu: "text", nhan: "Số HĐ", bat_buoc: true}]}, doan: [], chan_xuat: [], canh_bao: []},
  revisions: [], xuat: [{id: "x-1", revision: 2, trang_thai: "PDF_DAT", ly_do: null, tao_luc: "2026-10-21T00:00:00Z"}],
  mau_hieu_luc: [{mau_phien_ban_id: "mau-2", ma_mau: "HD", phien_ban: 2}]});
const TOM_TAT = {so_dong: 1, tong_minor: "1000000000", tien_te: "VND"};
const CAN_CU = {xuat_id: "x-1", revision: 2, trang_thai: "PDF_DAT", tao_luc: "2026-10-21T00:00:00Z", pdf_sha256: "a".repeat(64), pdf_len: 1234,
  docx_sha256: "b".repeat(64), engine: "WORD", mau_phien_ban_id: "mau-1", ma_mau: "HD", phien_ban_mau: 1, tom_tat: TOM_TAT};
const KY = (sua = {}) => ({soan_id: "so-1", hop_dong_id: "hd-1", ma_noi_bo: "HD-NB-1", trang_thai: "CHO_KY", revision: 2, hien_thi: null,
  quyen: {ky: true, doc: true, ly_do: null}, can_cu: CAN_CU, ...sua});
const BAN_KY = {ky_id: "k-1", revision: 2, xuat_id: "x-1", ngay_ky: "2026-10-20", nguoi_ky_khach: null, co_sua: false, mo_ta_sua: null,
  ky_pdf_sha256: "c".repeat(64), ky_pdf_len: 2048, ky_so_trang: 1, g3_pdf_sha256: "a".repeat(64), g3_pdf_len: 1234, tom_tat: TOM_TAT, tao_boi: BH,
  tao_luc: "2026-10-21T01:00:00Z", hien_thi: "Đã ký — chờ kế toán kiểm", g5: {trang_thai: "NOT_SELECTED", ly_do: "CHUA_AP_DUNG_CHON_MAU"}};
// ACK theo DTO master.crm_ky_kq (+ lap_lai) — dữ liệu GIẢ của mock, không phải biên nhận actual
const ACK = (sua = {}) => ({ky_id: "11111111-2222-4333-8444-555555555555", soan_id: "so-1", hop_dong_id: "hd-1", revision: 2, xuat_id: "x-1", trang_thai: "DA_KY",
  hien_thi: "Đã ký — chờ kế toán kiểm", ngay_ky: "2026-10-20", co_sua: false, ky_pdf_sha256: "c".repeat(64), ky_pdf_len: 2048, g3_pdf_sha256: "a".repeat(64),
  g5: {trang_thai: "NOT_SELECTED", ly_do: "CHUA_AP_DUNG_CHON_MAU"}, lap_lai: false, ...sua});
const phanHoiJsonHong = () => ({ok: true, status: 200, headers: {get: () => "application/json"}, json: async () => { throw new SyntaxError("Unexpected end of JSON input"); },
  blob: async () => new BLOB_GOC([])});
function blobTreo() {  // headers về ngay; blob() là Promise do ca điều khiển
  let ra;
  const p = new Promise(r => { ra = r; });
  return {res: {ok: true, status: 200, headers: {get: () => "application/pdf"}, json: async () => ({}), blob: () => p}, ra: n => ra(new BLOB_GOC([new Uint8Array(n)]))};
}
const TRUONG_KY = ["co_sua", "expected_revision", "expected_xuat_id", "khoa", "mo_ta", "ngay_ky", "nguoi_ky_khach", "soan_id", "ten_tep"];

async function main() {
  const {document, calls, ctx} = moiTruong();
  vm.runInContext(APP, ctx, {filename: "app.js"});
  const ngheHash = [];  // chỉ listener hashchange của crm_g.js (router app.js không mô phỏng)
  ctx.addEventListener = (t, fn) => { if (t === "hashchange") ngheHash.push(fn); };
  vm.runInContext(CRMG, ctx, {filename: "crm_g.js"});
  async function diHash(h) { ctx.location.hash = h; for (const fn of ngheHash) fn({}); await chay(); }
  const $ = id => document.getElementById(id);
  const conLai = pred => calls.filter(c => !c.xong && pred(c));
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const get = url => c => c.method === "GET" && c.url === url;
  const post = url => c => c.method === "POST" && c.url === url;
  const gk = () => $("crm-gk");
  const o = id => $("gk-" + id);
  const getDs = get("/api/crm/bao-gia"), getSo = get("/api/crm/soan/so-1"), getKy = get("/api/crm/giao-ket/ky/so-1"), postKy = post("/api/crm/giao-ket/ky-ket");
  const trangThaiGk = () => tim(gk(), e => e.attrs && e.attrs.role === "status");
  const toastTxt = () => ($("toast") || {textContent: ""}).textContent;
  const datToast = s => { if ($("toast")) $("toast").textContent = s; };
  const dialog = () => tim(gk(), e => e.attrs && e.attrs.role === "dialog");
  const nutKy = () => nut(gk(), "Ký kết…");
  const nutGui = () => nut(gk(), "Ký và lưu bản ký");
  const nutLai = () => nut(gk(), "Gửi lại bản ký y nguyên");
  async function traKhac() { for (const c of conLai(c => !/^\/api\/crm(\/bao-gia|\/soan\/|\/giao-ket\/|$)/.test(c.url) && c.url !== "/api/crm/danh-tinh")) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); } await chay(); }
  async function traDs(l, tt = "CHO_KY") { for (const c of conLai(getDs)) { c.xong = true; c.resolve(phanHoi(200, DS(l, tt))); } await chay(); }
  async function moSo(tt = "CHO_KY", ky = KY()) {  // Mở bản soạn → GET bản soạn → GET điều kiện ký (vi nhiệm sau nạp)
    nut(gk(), "Mở").click(); await chay();
    cho(getSo, "GET bản soạn").resolve(phanHoi(200, SO(tt))); await chay();
    cho(getKy, "GET điều kiện ký").resolve(phanHoi(200, ky)); await chay();
  }
  async function doiVai(l, tt = "CHO_KY") {
    $("crm-danh-tinh").value = l; $("crm-doi-vai").click(); await chay();
    for (const c of conLai(post("/api/crm/danh-tinh"))) { c.xong = true; c.resolve(phanHoi(200, {dang_nhap: l})); }
    await chay();
    for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM(l))); }
    await chay();
    await traDs(l, tt);
    await traKhac();
  }
  const F1 = {name: "ban-ky.pdf", size: 2048, lastModified: 1}, F2 = {name: "ban-ky-2.pdf", size: 4096, lastModified: 2};
  function chonTep(f) { const el = o("ky-tep"); el.files = f ? [f] : []; el.dispatch("change"); }
  function go(id, v, ev = "input") { const el = o(id); el.value = v; el.dispatch(ev); }
  async function moDialog() { nutKy().click(); await chay(); assert.ok(dialog(), "chưa mở dialog Ký kết"); }
  async function dienDu(f = F1, ngay = "2026-10-20", co = "KHONG") { chonTep(f); await chay(); go("ky-ngay", ngay); go("ky-co-sua", co, "change"); await chay(); }
  function ackTu(p, sua = {}) {  // ACK GIẢ đúng định danh của chính POST p (header + File), cho phép ghi đè để tạo ACK lệch
    const info = JSON.parse(decodeURIComponent(p.opts.headers["X-CRM-G-Info"]));
    return ACK({soan_id: info.soan_id, revision: info.expected_revision, xuat_id: info.expected_xuat_id, ngay_ky: info.ngay_ky, co_sua: info.co_sua,
      ky_pdf_len: p.opts.body.size, g5: info.co_sua ? {trang_thai: "PENDING", ly_do: "BAT_BUOC_KHAI_CO"} : {trang_thai: "NOT_SELECTED", ly_do: "CHUA_AP_DUNG_CHON_MAU"}, ...sua});
  }
  async function lamMoi(ky = KY(), tt = "CHO_KY") {  // ↻ Làm mới trên G3 đang mở so-1 → danh sách → bản soạn → điều kiện ký
    nut(gk(), "↻ Làm mới").click(); await chay();
    await traDs(BH, tt);
    for (const c of conLai(getSo)) { c.xong = true; c.resolve(phanHoi(200, SO(tt))); }
    await chay();
    cho(getKy, "GET điều kiện ký (làm mới)").resolve(phanHoi(200, ky)); await chay();
  }
  async function traNapLai(tt, ky) {  // trả chuỗi GET làm mới đang chờ (danh sách → bản soạn → điều kiện ký) nếu có
    await traDs(BH, tt); await traKhac();
    for (const c of conLai(getSo)) { c.xong = true; c.resolve(phanHoi(200, SO(tt))); }
    await chay();
    for (const c of conLai(getKy)) { c.xong = true; c.resolve(phanHoi(200, ky)); }
    await chay();
  }
  const KY_DA = () => KY({trang_thai: "DA_KY", hien_thi: "Đã ký — chờ kế toán kiểm", quyen: {ky: false, doc: true, ly_do: null},
    ban_ky: BAN_KY, lich_su: [{luc: "2026-10-21T01:00:00Z", nguoi: BH, hanh_dong: "CRM_KY_KET"}]});

  // khởi động vai BH → tab G3
  for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM(BH))); }
  await traKhac();
  await traDs(BH);
  await traKhac();
  nut(gk(), "Soạn hợp đồng (G3)").click(); await chay();
  await traDs(BH);

  // ---------------------------------------------------------------- K0 dương: điều kiện ký + dialog căn cứ
  {
    await moSo();
    assert.ok(nutKy() && !nutKy().disabled, "K0: nút Ký kết… không bật khi đủ điều kiện");
    assert.ok(!gk().textContent.includes("chưa nối"), "K0: còn nhãn G4 chưa nối");
    await moDialog();
    const t = dialog().textContent;
    assert.ok(t.includes("x-1") && t.includes("a".repeat(64)) && t.includes("1234"), "K0: dialog thiếu bản xuất/hash/độ dài căn cứ");
    assert.ok(t.includes("1 dòng lịch") && t.includes("VND"), "K0: dialog thiếu tóm tắt số dòng/tổng/tiền tệ");
    assert.ok(t.includes("không phải ngày hiệu lực"), "K0: thiếu cảnh báo ngày ký ≠ ngày hiệu lực");
    console.log("K0 đạt");
  }

  // ---------------------------------------------------------------- K1 thiếu dữ liệu → 0 POST
  {
    nutGui().click(); await chay();
    assert.strictEqual(dem(postKy), 0, "K1: gửi khi chưa chọn tệp");
    assert.ok(trangThaiGk().textContent.includes("Chọn tệp PDF"), "K1: thiếu thông báo chọn tệp");
    chonTep(F1); await chay(); go("ky-ngay", "2026-10-20");
    nutGui().click(); await chay();
    assert.strictEqual(dem(postKy), 0, "K1: gửi khi chưa chọn Có/Không");
    go("ky-co-sua", "CO", "change"); await chay();
    assert.ok(o("ky-mo-ta"), "K1: chọn Có không hiện ô mô tả");
    nutGui().click(); await chay();
    assert.strictEqual(dem(postKy), 0, "K1: khai Có thiếu mô tả vẫn gửi");
    chonTep({name: "ban-ky.docx", size: 10, lastModified: 3}); await chay(); go("ky-co-sua", "KHONG", "change"); await chay();
    nutGui().click(); await chay();
    assert.strictEqual(dem(postKy), 0, "K1: tệp không phải .pdf vẫn gửi");
    chonTep({name: "rong.pdf", size: 0, lastModified: 4}); await chay();
    nutGui().click(); await chay();
    assert.strictEqual(dem(postKy), 0, "K1: tệp rỗng vẫn gửi");
    console.log("K1 đạt");
  }

  // ---------------------------------------------------------------- K2 bấm lặp → 1 POST; header đúng hợp đồng
  let y1;
  {
    await dienDu();
    nutGui().click(); nutGui().click(); await chay();
    assert.strictEqual(conLai(postKy).length, 1, "K2: bấm lặp gửi thêm POST");
    y1 = cho(postKy, "POST ký K2");
    nutGui().click(); await chay();
    assert.strictEqual(conLai(postKy).length, 0, "K2: POST thứ hai khi lần đầu còn chờ");
    const h = y1.opts.headers, info = JSON.parse(decodeURIComponent(h["X-CRM-G-Info"]));
    assert.strictEqual(h["Content-Type"], "application/pdf");
    assert.strictEqual(y1.opts.body, F1, "K2: body không phải ĐÚNG File đã chọn");
    assert.deepStrictEqual(Object.keys(info).sort(), TRUONG_KY, "K2: header có trường ngoài hợp đồng");
    assert.deepStrictEqual([info.soan_id, info.expected_revision, info.expected_xuat_id, info.ten_tep, info.ngay_ky, info.co_sua, info.mo_ta],
      ["so-1", 2, "x-1", "ban-ky.pdf", "2026-10-20", false, null], "K2: header sai căn cứ/khai báo");
    assert.ok(typeof info.khoa === "string" && info.khoa.startsWith("crmgk-"), "K2: thiếu khóa");
    console.log("K2 đạt");
  }

  // ---------------------------------------------------------------- K3 chưa rõ → chặn ý định mới; gửi lại y nguyên
  let lai;
  {
    y1.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(nutLai(), "K3: thiếu nút gửi lại bản ký y nguyên");
    go("ky-ngay", "2026-10-19"); await chay();
    nutGui().click(); await chay();
    assert.strictEqual(dem(postKy), 1, "K3: ý định MỚI được gửi khi ý định cũ chưa rõ");
    assert.ok(trangThaiGk().textContent.includes("chưa rõ kết quả"), "K3: thiếu lý do chặn ý định mới");
    nutLai().click(); await chay();
    lai = cho(postKy, "POST gửi lại K3");
    assert.strictEqual(lai.opts.body, F1, "K3: gửi lại khác File");
    assert.strictEqual(lai.opts.headers["X-CRM-G-Info"], y1.opts.headers["X-CRM-G-Info"], "K3: gửi lại khác header/khóa");
    console.log("K3 đạt");
  }

  // ---------------------------------------------------------------- K4 đổi vai khi gửi lại còn chờ → ACK muộn im lặng; vai khác không thấy nút
  {
    const nSo = dem(getSo);
    $("crm-danh-tinh").value = KT; $("crm-doi-vai").click(); await chay();
    datToast("");
    lai.reject(new TypeError("Failed to fetch")); await chay();  // vẫn chưa rõ — ý định giữ, không hiệu ứng trên vai mới
    assert.strictEqual(toastTxt(), "", "K4: lỗi muộn của vai cũ hiện toast");
    for (const c of conLai(post("/api/crm/danh-tinh"))) { c.xong = true; c.resolve(phanHoi(200, {dang_nhap: KT})); }
    await chay();
    for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM(KT))); }
    await chay();
    await traDs(KT); await traKhac();
    assert.strictEqual(dem(getSo), nSo, "K4: lỗi muộn mở GET bản soạn dưới vai mới");
    await moSo("CHO_KY", KY({quyen: {ky: false, doc: true, ly_do: "CRM_G_KHONG_CO_QUYEN"}}));
    assert.strictEqual(nutLai(), null, "K4: vai KT thấy nút gửi lại ý định của BH");
    assert.ok(nutKy().disabled, "K4: KT không có quyền ký nhưng nút bật");
    console.log("K4 đạt");
  }

  // ---------------------------------------------------------------- K5 về lại vai BH → nút gửi lại còn; 409 căn cứ cũ → đóng + tải lại
  {
    await doiVai(BH);
    await moSo();
    assert.ok(nutLai(), "K5: ý định chưa rõ của BH mất sau khi đổi vai đi/về");
    nutLai().click(); await chay();
    const r = cho(postKy, "POST gửi lại K5");
    assert.strictEqual(r.opts.headers["X-CRM-G-Info"], y1.opts.headers["X-CRM-G-Info"], "K5: gửi lại sau đổi vai khác header/khóa");
    await moDialog();
    const nDs = dem(getDs);
    r.resolve(phanHoi(409, {error: "CRM_KY_XUAT_CU", message: "Đã có bản xuất mới hơn"})); await chay();
    assert.ok(dem(getDs) > nDs, "K5: 409 căn cứ cũ không tải lại căn cứ");
    assert.ok(trangThaiGk().textContent.includes("đã tải lại căn cứ"), "K5: thiếu thông báo tải lại căn cứ");
    await traDs(BH);  // napDs vẽ lại → dialog (kyMo đã nhả) biến mất
    assert.strictEqual(dialog(), null, "K5: 409 căn cứ cũ không đóng dialog");
    assert.strictEqual(nutLai(), null, "K5: kết quả xác định nhưng vẫn giữ nút gửi lại");
    cho(getSo, "K5 tải lại bản soạn").resolve(phanHoi(200, SO())); await chay();
    cho(getKy, "K5 tải lại điều kiện").resolve(phanHoi(200, KY())); await chay();
    console.log("K5 đạt");
  }

  // ---------------------------------------------------------------- K6 thành công → nhãn trung thực + làm mới
  {
    await moDialog();
    await dienDu(F2, "2026-10-20", "KHONG");
    nutGui().click(); await chay();
    const p = cho(postKy, "POST ký K6");
    assert.notStrictEqual(JSON.parse(decodeURIComponent(p.opts.headers["X-CRM-G-Info"])).khoa, JSON.parse(decodeURIComponent(y1.opts.headers["X-CRM-G-Info"])).khoa,
      "K6: ý định mới dùng lại khóa đã FINAL");
    datToast("");
    p.resolve(phanHoi(200, ackTu(p))); await chay();  // FIX04: ACK đủ DTO crm_ky_kq đúng định danh ý định (mock, không phải actual)
    const t = toastTxt() + " " + trangThaiGk().textContent;
    assert.ok(t.includes("Đã ký — chờ kế toán kiểm"), "K6: thiếu nhãn Đã ký — chờ kế toán kiểm");
    assert.ok(!t.includes("Đã chuyển") && !t.includes("hiệu lực"), "K6: nhãn nói đã chuyển/hiệu lực");
    assert.ok(t.includes("NOT_SELECTED") && !t.includes("PENDING"), "K6: G5 khởi tạo sai");
    await traDs(BH, "DA_KY");
    assert.strictEqual(dialog(), null, "K6: dialog chưa đóng sau khi ký");
    cho(getSo, "K6 làm mới bản soạn").resolve(phanHoi(200, SO("DA_KY"))); await chay();
    cho(getKy, "K6 làm mới bản ký").resolve(phanHoi(200, KY({trang_thai: "DA_KY", hien_thi: "Đã ký — chờ kế toán kiểm", quyen: {ky: false, doc: true, ly_do: null},
      ban_ky: BAN_KY, lich_su: [{luc: "2026-10-21T01:00:00Z", nguoi: BH, hanh_dong: "CRM_KY_KET"}]}))); await chay();
    console.log("K6 đạt");
  }

  // ---------------------------------------------------------------- K7 DA_KY chỉ xem + tải bản ký có fence
  {
    assert.strictEqual(nut(gk(), "Lưu bản soạn"), null, "K7: DA_KY còn nút Lưu");
    assert.strictEqual(nut(gk(), "Xuất DOCX"), null, "K7: DA_KY còn nút Xuất");
    assert.strictEqual(nutKy(), null, "K7: DA_KY còn nút Ký kết");
    assert.strictEqual(o("so-doi-so-1"), null, "K7: DA_KY còn chọn đổi mẫu");
    assert.ok(o("so-f-so_hop_dong").disabled, "K7: ô tham số DA_KY chưa vô hiệu");
    const t = gk().textContent;
    assert.ok(t.includes("Bản ký & đối chiếu") && t.includes("c".repeat(64)) && t.includes("không phải ngày hiệu lực"), "K7: thiếu khối bản ký");
    assert.ok(t.includes("NOT_SELECTED"), "K7: thiếu G5");
    const truoc = soClickTai;
    nut(gk(), "PDF bản ký ↓").click(); await chay();
    cho(get("/api/crm/giao-ket/ban-ky/k-1/tep"), "GET tải bản ký").resolve(phanHoi(200, {}, 2048)); await chay();
    assert.strictEqual(soClickTai, truoc + 1, "K7: tải dương không click đúng một lần");
    nut(gk(), "PDF bản ký ↓").click(); await chay();
    const t2 = cho(get("/api/crm/giao-ket/ban-ky/k-1/tep"), "GET tải bản ký (đổi vai)");
    $("crm-danh-tinh").value = KT; $("crm-doi-vai").click(); await chay();
    t2.resolve(phanHoi(200, {}, 2048)); await chay();
    assert.strictEqual(soClickTai, truoc + 1, "K7: blob của vai cũ vẫn click tải");
    for (const c of conLai(post("/api/crm/danh-tinh"))) { c.xong = true; c.resolve(phanHoi(200, {dang_nhap: KT})); }
    await chay();
    for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM(KT))); }
    await chay();
    await traDs(KT); await traKhac();
    console.log("K7 đạt");
  }

  // ---------------------------------------------------------------- K8 GET cũ về trễ không lùi; thiếu phạm vi → nút vô hiệu + lý do
  {
    await doiVai(BH);
    nut(gk(), "Mở").click(); await chay();
    cho(getSo, "K8 GET bản soạn").resolve(phanHoi(200, SO())); await chay();
    const cu = cho(getKy, "K8 GET điều kiện (cũ)");
    nut(gk(), "↻ Làm mới").click(); await chay();
    await traDs(BH);
    for (const c of conLai(getSo)) { c.xong = true; c.resolve(phanHoi(200, SO())); }
    await chay();
    cho(getKy, "K8 GET điều kiện (mới)").resolve(phanHoi(200, KY())); await chay();
    cu.resolve(phanHoi(200, KY({quyen: {ky: false, doc: false, ly_do: "CRM_KY_CHUA_CO_PHAM_VI"}}))); await chay();
    assert.ok(nutKy() && !nutKy().disabled, "K8: GET cũ về trễ làm lùi điều kiện ký");
    nut(gk(), "↻ Làm mới").click(); await chay();
    await traDs(BH);
    for (const c of conLai(getSo)) { c.xong = true; c.resolve(phanHoi(200, SO())); }
    await chay();
    cho(getKy, "K8 GET thiếu phạm vi").resolve(phanHoi(200, KY({quyen: {ky: false, doc: false, ly_do: "CRM_KY_CHUA_CO_PHAM_VI"}, can_cu: undefined}))); await chay();
    assert.ok(nutKy().disabled, "K8: thiếu phạm vi nhưng nút Ký kết bật");
    const ly = tim(gk(), e => e.dataset && e.dataset.lyKy === "1");
    assert.ok(ly && ly.textContent.includes("phạm vi ký"), "K8: thiếu lý do phạm vi");
    assert.ok(ly.textContent.includes("không suy từ người tạo"), "K8: lý do không nói rõ phạm vi do quản trị cấp");
    console.log("K8 đạt");
  }

  // ---------------------------------------------------------------- K9 ACK 2xx hỏng/lệch → CHƯA RÕ (giữ File/header/khóa), không FINAL
  {
    await lamMoi();
    assert.ok(nutKy() && !nutKy().disabled, "K9: chuẩn bị — nút Ký kết… không bật");
    await moDialog(); await dienDu(F1, "2026-10-20", "KHONG");
    nutGui().click(); await chay();
    let p = cho(postKy, "POST ký K9");
    const hGoc = p.opts.headers["X-CRM-G-Info"], p0 = p;
    const nDs = dem(getDs), nSo = dem(getSo), nKy = dem(getKy);
    const JSON_HONG = Symbol("json-hong");
    const HONG = [["{}", {}], ["null", null], ["mảng", []], ["JSON hỏng", JSON_HONG],
      ["sai bản soạn", ackTu(p0, {soan_id: "so-2"})], ["sai HĐ", ackTu(p0, {hop_dong_id: "hd-2"})], ["sai trạng thái", ackTu(p0, {trang_thai: "CHO_KY"})],
      ["thiếu ky_id", ackTu(p0, {ky_id: undefined})], ["ky_id không UUID", ackTu(p0, {ky_id: "k-1"})], ["sai revision", ackTu(p0, {revision: 1})],
      ["sai bản xuất", ackTu(p0, {xuat_id: "x-0"})], ["sai ngày ký", ackTu(p0, {ngay_ky: "2026-10-19"})], ["co_sua chuỗi", ackTu(p0, {co_sua: "false"})],
      ["sai độ dài PDF", ackTu(p0, {ky_pdf_len: 1})], ["hash ký sai dạng", ackTu(p0, {ky_pdf_sha256: "xyz"})], ["sai hash G3", ackTu(p0, {g3_pdf_sha256: "d".repeat(64)})],
      ["G5 PENDING khi khai Không", ackTu(p0, {g5: {trang_thai: "PENDING", ly_do: "BAT_BUOC_KHAI_CO"}})], ["G5 MATCH", ackTu(p0, {g5: {trang_thai: "MATCH"}})],
      ["thiếu G5", ackTu(p0, {g5: undefined})], ["lap_lai không boolean", ackTu(p0, {lap_lai: "false"})]];
    for (const [ten, ack] of HONG) {
      datToast("");
      p.resolve(ack === JSON_HONG ? phanHoiJsonHong() : phanHoi(200, ack)); await chay();
      const t = toastTxt() + " " + trangThaiGk().textContent;
      assert.ok(!t.includes("Đã ký — chờ kế toán kiểm"), `K9 ${ten}: ACK hỏng/lệch bị hiển thị là đã ký`);
      assert.ok(t.includes("chưa xác nhận"), `K9 ${ten}: thiếu thông báo chưa xác nhận`);
      assert.ok(dialog(), `K9 ${ten}: ACK hỏng/lệch đóng dialog`);
      assert.strictEqual(o("ky-ngay").value, "2026-10-20", `K9 ${ten}: ACK hỏng/lệch xóa nháp dialog`);
      assert.ok(dialog().textContent.includes(F1.name), `K9 ${ten}: ACK hỏng/lệch bỏ tệp đã chọn`);
      assert.strictEqual(dem(getDs), nDs, `K9 ${ten}: ACK hỏng/lệch mở GET danh sách`);
      assert.strictEqual(dem(getSo), nSo, `K9 ${ten}: ACK hỏng/lệch mở GET bản soạn`);
      assert.strictEqual(dem(getKy), nKy, `K9 ${ten}: ACK hỏng/lệch mở GET điều kiện ký`);
      assert.ok(nutLai(), `K9 ${ten}: mất đường đối soát (gửi lại y nguyên)`);
      go("ky-ngay", "2026-10-18"); await chay();  // ý định MỚI vẫn bị chặn khi ý định gốc chưa rõ
      nutGui().click(); await chay();
      assert.strictEqual(conLai(postKy).length, 0, `K9 ${ten}: ý định mới được gửi khi ý định gốc chưa rõ`);
      go("ky-ngay", "2026-10-20"); await chay();
      nutLai().click(); await chay();
      p = cho(postKy, `POST gửi lại sau ${ten}`);
      assert.strictEqual(p.opts.body, F1, `K9 ${ten}: gửi lại khác File`);
      assert.strictEqual(p.opts.headers["X-CRM-G-Info"], hGoc, `K9 ${ten}: gửi lại khác header/khóa`);
    }
    datToast("");
    p.resolve(phanHoi(200, ackTu(p0, {lap_lai: true}))); await chay();  // ACK typed đúng định danh → FINAL (mock)
    const t = toastTxt() + " " + trangThaiGk().textContent;
    assert.ok(t.includes("Đã ký — chờ kế toán kiểm") && t.includes("biên nhận cũ") && t.includes("NOT_SELECTED"), "K9: ACK đúng không FINAL");
    assert.ok(dem(getDs) > nDs, "K9: ACK đúng không làm mới");
    await traNapLai("DA_KY", KY_DA());
    assert.strictEqual(dialog(), null, "K9: ACK đúng không đóng dialog");
    assert.strictEqual(nutLai(), null, "K9: ACK đúng vẫn giữ nút gửi lại");
    console.log("K9 đạt");
  }

  // ---------------------------------------------------------------- K10 ABA: POST gốc + gửi lại đang bay; form mới; lỗi/ACK/GET cũ không ghi đè
  {
    await lamMoi();  // mock trả lại CHO_KY để dựng ca (không phải luồng nghiệp vụ thật)
    await moDialog(); await dienDu(F1, "2026-10-21", "KHONG");
    nutGui().click(); await chay();
    const goc = cho(postKy, "K10 POST gốc (A)");
    const hGoc = goc.opts.headers["X-CRM-G-Info"], khoaGoc = JSON.parse(decodeURIComponent(hGoc)).khoa;
    // A → B khi POST gốc còn bay; B không bị khóa bởi ý định của A
    await doiVai(KT);
    await moSo();
    assert.strictEqual(nutLai(), null, "K10: vai B thấy nút gửi lại của A");
    await moDialog(); await dienDu(F2, "2026-10-21", "KHONG");
    nutGui().click(); await chay();
    assert.strictEqual(conLai(postKy).length, 1, "K10: vai B bị khóa bởi ý định đang bay của A");
    const pB = cho(postKy, "K10 POST của B");
    assert.notStrictEqual(JSON.parse(decodeURIComponent(pB.opts.headers["X-CRM-G-Info"])).khoa, khoaGoc, "K10: B dùng khóa của A");
    pB.resolve(phanHoi(400, {error: "CRM_G_YEU_CAU_SAI", message: "Yêu cầu sai (mock)"})); await chay();
    datToast(""); const nDsB = dem(getDs);
    goc.reject(new TypeError("Failed to fetch")); await chay();  // lỗi chưa rõ của A khi đang là B: im lặng, A giữ CHƯA RÕ
    assert.strictEqual(toastTxt(), "", "K10: lỗi muộn của A hiện toast trên vai B");
    assert.strictEqual(dem(getDs), nDsB, "K10: lỗi muộn của A mở GET dưới vai B");
    assert.strictEqual(nutLai(), null, "K10: vai B thấy nút gửi lại của A");
    // B → A: đường đối soát của A còn; gửi lại đúng File/header/khóa gốc
    await doiVai(BH);
    await moSo();
    assert.ok(nutLai(), "K10: CHƯA RÕ của A mất sau A→B→A");
    nutLai().click(); await chay();
    const lai = cho(postKy, "K10 gửi lại (A)");
    assert.strictEqual(lai.opts.body, F1, "K10: gửi lại khác File gốc");
    assert.strictEqual(lai.opts.headers["X-CRM-G-Info"], hGoc, "K10: gửi lại khác header/khóa gốc");
    // gửi lại còn bay qua A→B→A; A nhập form MỚI; ý định mới bị chặn khi gửi lại còn bay
    await doiVai(KT); await doiVai(BH);
    await moSo();
    await moDialog(); await dienDu(F2, "2026-10-24", "KHONG");
    nutGui().click(); await chay();
    assert.strictEqual(conLai(postKy).length, 0, "K10: ý định mới gửi khi gửi lại của A còn bay");
    datToast(""); let nDs = dem(getDs), nSo = dem(getSo);
    lai.resolve(phanHoi(409, {error: "CRM_KY_XUAT_CU", message: "Đã có bản xuất mới hơn (mock)"})); await chay();  // lỗi cũ sau ABA
    assert.strictEqual(toastTxt(), "", "K10: lỗi cũ sau ABA hiện toast");
    assert.ok(!trangThaiGk().textContent.includes("đã tải lại căn cứ"), "K10: lỗi cũ sau ABA ghi trạng thái");
    assert.strictEqual(dem(getDs), nDs, "K10: lỗi cũ sau ABA mở GET danh sách với fence mới");
    assert.strictEqual(dem(getSo), nSo, "K10: lỗi cũ sau ABA mở GET bản soạn");
    assert.ok(dialog(), "K10: lỗi cũ sau ABA đóng dialog của form mới");
    assert.strictEqual(o("ky-ngay").value, "2026-10-24", "K10: lỗi cũ sau ABA xóa nháp form mới");
    assert.ok(dialog().textContent.includes(F2.name), "K10: lỗi cũ sau ABA bỏ tệp của form mới");
    // bản ghi gốc đã nhả (kết quả xác định) → ý định mới gửi được; G3→G2→G3 + nhập form mới trong lúc chờ → ACK cũ im lặng
    nutGui().click(); await chay();
    const p3 = cho(postKy, "K10 POST ý định mới");
    assert.notStrictEqual(JSON.parse(decodeURIComponent(p3.opts.headers["X-CRM-G-Info"])).khoa, khoaGoc, "K10: ý định mới dùng khóa gốc");
    assert.strictEqual(p3.opts.body, F2, "K10: ý định mới không phải File mới");
    nut(gk(), "Báo giá (G2)").click(); await chay();
    nut(gk(), "Soạn hợp đồng (G3)").click(); await chay();
    assert.ok(dialog(), "K10: chuẩn bị — dialog không còn sau G3→G2→G3");
    go("ky-nguoi", "Ông B"); await chay();
    datToast(""); nDs = dem(getDs); nSo = dem(getSo);
    p3.resolve(phanHoi(200, ackTu(p3))); await chay();
    assert.strictEqual(toastTxt(), "", "K10: ACK cũ sau G3→G2→G3 + form mới hiện toast");
    assert.ok(!trangThaiGk().textContent.includes("Đã ký — chờ kế toán kiểm"), "K10: ACK cũ ghi trạng thái lên form mới");
    assert.ok(dialog(), "K10: ACK cũ đóng dialog của form mới");
    assert.strictEqual(o("ky-nguoi").value, "Ông B", "K10: ACK cũ xóa nháp form mới");
    assert.strictEqual(dem(getDs), nDs, "K10: ACK cũ mở GET danh sách với fence mới");
    assert.strictEqual(dem(getSo), nSo, "K10: ACK cũ mở GET bản soạn");
    // ACK cũ đã nhả ĐÚNG bản ghi (không còn "đang gửi") → ý định hiện tại gửi được; ACK hợp lệ → làm mới theo guard lúc gửi; form đổi sau ACK → dừng chuỗi
    nutGui().click(); await chay();
    const p4 = cho(postKy, "K10 POST ý định hiện tại");
    datToast(""); nDs = dem(getDs); nSo = dem(getSo);
    p4.resolve(phanHoi(200, ackTu(p4))); await chay();
    assert.ok(toastTxt().includes("Đã ký — chờ kế toán kiểm"), "K10: ACK hợp lệ trong context hiện tại không hiển thị");
    assert.strictEqual(dem(getDs), nDs + 1, "K10: ACK hợp lệ không làm mới đúng một lần");
    go("ky-nguoi", "Bà C"); await chay();  // form đổi khi GET danh sách đang chờ
    await traDs(BH, "DA_KY");
    assert.strictEqual(dem(getSo), nSo, "K10: GET làm mới dùng fence chụp lại sau ACK (đè form mới)");
    await traNapLai("DA_KY", KY_DA());
    console.log("K10 đạt");
  }

  // ---------------------------------------------------------------- K11 tải PDF bản ký: blob Promise điều khiển + điều hướng hash
  {
    const getTai = get("/api/crm/giao-ket/ban-ky/k-1/tep");
    await lamMoi(KY_DA(), "DA_KY");
    assert.ok(nut(gk(), "PDF bản ký ↓"), "K11: chuẩn bị — thiếu nút tải bản ký");
    const truoc = soClickTai;
    // (a) headers đã về, blob còn chờ → rời #hopdong rồi quay lại → blob về: không click
    nut(gk(), "PDF bản ký ↓").click(); await chay();
    const b1 = blobTreo();
    cho(getTai, "K11 GET tải (đi-rồi-về)").resolve(b1.res); await chay();
    await diHash("#tongquan"); await diHash("#hopdong");
    b1.ra(2048); await chay();
    assert.strictEqual(soClickTai, truoc, "K11: blob sau đi-rồi-về #hopdong vẫn click tải");
    await traNapLai("DA_KY", KY_DA());
    // (b) headers đã về, blob còn chờ → rời #hopdong → blob về khi đang ở trang khác: không click
    nut(gk(), "PDF bản ký ↓").click(); await chay();
    const b2 = blobTreo();
    cho(getTai, "K11 GET tải (rời trang)").resolve(b2.res); await chay();
    await diHash("#tongquan");
    b2.ra(2048); await chay();
    assert.strictEqual(soClickTai, truoc, "K11: blob về khi đã rời #hopdong vẫn click tải");
    await diHash("#hopdong");
    await traNapLai("DA_KY", KY_DA());
    // (c) đối chứng dương sau khi về: cùng đường blob Promise điều khiển, không điều hướng → click đúng một lần
    nut(gk(), "PDF bản ký ↓").click(); await chay();
    const b3 = blobTreo();
    cho(getTai, "K11 GET tải (dương)").resolve(b3.res); await chay();
    b3.ra(2048); await chay();
    assert.strictEqual(soClickTai, truoc + 1, "K11: tải dương sau khi quay lại không click đúng một lần");
    console.log("K11 đạt");
  }

  // ---------------------------------------------------------------- K12 U2 File-only: đổi CHỈ File (ngày/người/Có-Không giữ nguyên) khi POST gốc
  // hoặc gửi lại y nguyên (CHƯA RÕ) còn bay → ACK HỢP LỆ cũ về: không toast/trạng thái/đóng dialog/xóa File-nháp/GET làm mới; File/form mới còn nguyên.
  {
    const kiemImLang = (nhan, n) => {
      assert.strictEqual(toastTxt(), "", `${nhan}: ACK cũ hiện toast sau khi đổi File`);
      assert.ok(!trangThaiGk().textContent.includes("Đã ký — chờ kế toán kiểm"), `${nhan}: ACK cũ ghi trạng thái lên form có File mới`);
      assert.ok(dialog(), `${nhan}: ACK cũ đóng dialog của File mới`);
      assert.ok(dialog().textContent.includes("Đã chọn: " + F2.name), `${nhan}: ACK cũ xóa File mới đã chọn`);
      assert.strictEqual(o("ky-ngay").value, n, `${nhan}: ACK cũ xóa ngày ký của form`);
      assert.strictEqual(o("ky-co-sua").value, "KHONG", `${nhan}: ACK cũ xóa khai báo Có/Không của form`);
      assert.ok(nutGui() && !nutGui().disabled, `${nhan}: ACK cũ vô hiệu nút gửi của form mới`);
    };
    // (a) POST gốc còn bay → chỉ đổi File → ACK hợp lệ cũ
    await lamMoi();  // mock trả lại CHO_KY để dựng ca (không phải luồng nghiệp vụ thật)
    await moDialog(); await dienDu(F1, "2026-10-22", "KHONG");
    nutGui().click(); await chay();
    const pa = cho(postKy, "K12a POST gốc");
    assert.strictEqual(pa.opts.body, F1, "K12a: chuẩn bị — POST gốc không phải F1");
    const khoaA = JSON.parse(decodeURIComponent(pa.opts.headers["X-CRM-G-Info"])).khoa;
    chonTep(F2); await chay();  // CHỈ File đổi
    datToast(""); let nDs = dem(getDs), nSo = dem(getSo), nKy = dem(getKy);
    pa.resolve(phanHoi(200, ackTu(pa))); await chay();
    kiemImLang("K12a", "2026-10-22");
    assert.deepStrictEqual([dem(getDs), dem(getSo), dem(getKy)], [nDs, nSo, nKy], "K12a: ACK cũ mở GET làm mới sau khi đổi File");
    // đối chứng: form mới (F2) gửi ý định MỚI (khóa mới, đúng File mới); ACK hợp lệ của CHÍNH nó hiển thị
    nutGui().click(); await chay();
    const pa2 = cho(postKy, "K12a POST ý định File mới");
    assert.strictEqual(pa2.opts.body, F2, "K12a: ý định mới không gửi File mới");
    assert.notStrictEqual(JSON.parse(decodeURIComponent(pa2.opts.headers["X-CRM-G-Info"])).khoa, khoaA, "K12a: ý định File mới dùng khóa gốc");
    datToast("");
    pa2.resolve(phanHoi(200, ackTu(pa2))); await chay();
    assert.ok(toastTxt().includes("Đã ký — chờ kế toán kiểm"), "K12a: ACK hợp lệ của ý định File mới không hiển thị");
    await traNapLai("DA_KY", KY_DA());
    console.log("K12a đạt");

    // (b) CHƯA RÕ → gửi lại y nguyên (ĐÚNG File/header/khóa gốc) còn bay → chỉ đổi File → ACK hợp lệ cũ
    await lamMoi();  // mock trả lại CHO_KY
    await moDialog(); await dienDu(F1, "2026-10-23", "KHONG");
    nutGui().click(); await chay();
    const goc = cho(postKy, "K12b POST gốc");
    const hGoc = goc.opts.headers["X-CRM-G-Info"], khoaB = JSON.parse(decodeURIComponent(hGoc)).khoa;
    goc.reject(new TypeError("Failed to fetch")); await chay();  // CHƯA RÕ
    assert.ok(nutLai(), "K12b: chuẩn bị — thiếu nút gửi lại y nguyên");
    nutLai().click(); await chay();
    const lai = cho(postKy, "K12b gửi lại y nguyên");
    assert.strictEqual(lai.opts.body, F1, "K12b: gửi lại khác File gốc");
    assert.strictEqual(lai.opts.headers["X-CRM-G-Info"], hGoc, "K12b: gửi lại khác header/khóa gốc");
    chonTep(F2); await chay();  // CHỈ File đổi khi gửi lại còn bay
    datToast(""); nDs = dem(getDs); nSo = dem(getSo); nKy = dem(getKy);
    lai.resolve(phanHoi(200, ackTu(lai))); await chay();
    kiemImLang("K12b", "2026-10-23");
    assert.deepStrictEqual([dem(getDs), dem(getSo), dem(getKy)], [nDs, nSo, nKy], "K12b: ACK cũ mở GET làm mới sau khi đổi File");
    assert.strictEqual(nutLai(), null, "K12b: ACK hợp lệ cũ đã FINAL nhưng vẫn giữ nút gửi lại");
    nutGui().click(); await chay();
    const pb2 = cho(postKy, "K12b POST ý định File mới");
    assert.strictEqual(pb2.opts.body, F2, "K12b: ý định mới không gửi File mới");
    assert.notStrictEqual(JSON.parse(decodeURIComponent(pb2.opts.headers["X-CRM-G-Info"])).khoa, khoaB, "K12b: ý định File mới dùng khóa gốc");
    datToast("");
    pb2.resolve(phanHoi(200, ackTu(pb2))); await chay();
    assert.ok(toastTxt().includes("Đã ký — chờ kế toán kiểm"), "K12b: ACK hợp lệ của ý định File mới không hiển thị");
    await traNapLai("DA_KY", KY_DA());
    console.log("K12b đạt");
  }

  assert.deepStrictEqual(loiNgoai, [], "có Promise bị từ chối không xử lý");
  console.log("CRM-41-04A async: mọi ca đạt (MOCK DOM — không phải trình duyệt thật)");
}

main().catch(e => { console.error(e); process.exit(1); });
