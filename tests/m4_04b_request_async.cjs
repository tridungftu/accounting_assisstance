"use strict";
// M4-04B — widget Request nháp THẬT (m4/giao_dien/m4_request_nhap.js) qua cầu nối THẬT của tab Duyệt & PDF (app.js + m4.js + m4_duyet_pdf.js).
// DTO duyệt + context HTTP + DTO intent/kết quả đọc từ fixture do tests/test_m4_04b_request_wiring_http.py sinh bằng nhà sản xuất THẬT
// (DuyetDot.xem / m4_request.ngu_canh / RequestNhap._dto/_ket_qua / m4_request._hold — chỉ giả tầng dữ liệu). Ca âm = ĐỘT BIẾN có chủ đích của chính dữ liệu đó.
//  W01 hiện hành dương: số xin thanh toán nguyên văn theo seal, body đúng {dot_id, version_id, khoa}, bấm đúp = 1 POST, ACK có kiểu → đọc lại; tóm tắt căn cứ
//      d.request "Đủ căn cứ duyệt + PDF" giữ nguyên trước/sau lệnh (không đồng bộ trạng thái từ widget); widget không gọi /api/m4/ke-toan (KT độc lập).
//  W02 seal thiếu số tiền → "(thiếu)", Tạo tắt.     W03 không mount khi CHUA_NOP / CHO_PDF / bản nháp kế tiếp (không script, không GET).
//  W04 lịch sử V1 chọn tường minh: Tạo tắt; Đối soát → HOLD có kiểu LICH_SU_CAN_TAO.   W05 context/ACK giả mạo (login/PN/seal/hiện hành/khóa lạ) → từ chối.
//  W06 UNKNOWN (mất mạng / 503 không kiểu) → Gửi lại y nguyên cùng body/khóa.   W07 ACK về muộn sau huy → 0 toast/GET.   W08 phiên bản A→B→A.
//  W09 huy khi GET đang bay.   W10 403/404 thu hồi.   W11 RUNNING.   W12 CHUA_CAU_HINH.   W14 2xx sai hợp đồng.   W15 tải script lỗi.
// Khung DOM/fetch sao từ tests/m4_02c_dto_ui_async.cjs (tệp đó KHÔNG sửa). Mỗi ca một môi trường mới. Không process.exit, không ghi tệp, không mạng.
// CODE_ONLY: WRITTEN_NOT_RUN. Chạy qua test Python (`node tests/m4_04b_request_async.cjs <fixture.json>`, Node ≥ 18).
// Dòng cuối: `KET_QUA_JSON {"dat":[...],"hong":[...],"setup_errors":[...]}`. process.exitCode = 0 khi mọi ca đạt; 1 khi có hỏng/setup_errors/unhandledRejection.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");
const APP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/app.js"), "utf8");
const M4 = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/m4.js"), "utf8");
const DP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/m4_duyet_pdf.js"), "utf8");
const RQ = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/m4_request_nhap.js"), "utf8");
const ID_TINH = new Set([...fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/index.html"), "utf8").matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const BLOB_GOC = globalThis.Blob || (() => { try { return require("buffer").Blob; } catch (_) { return null; } })();
const FILE_GOC = globalThis.File || (() => { try { return require("buffer").File; } catch (_) { return null; } })();
const loiNgoai = [];
process.on("unhandledRejection", e => { loiNgoai.push(e); });

// ------------------------------------------------------------------ fixture do backend thật sinh
let FX = null, loiFx = null;
try {
  FX = JSON.parse(fs.readFileSync(process.argv[2] || "", "utf8"));
  if (!FX || FX.schema !== "M4_04B_REQUEST_UI_FIXTURE_V1" || !FX.dto || !FX.ids || !FX.ctx || !FX.y || !FX.kq) throw new Error("schema fixture lạ");
} catch (e) { loiFx = e; FX = null; }
const sao = o => JSON.parse(JSON.stringify(o));
const lay_ = (nhom, ten) => { const d = FX[nhom][ten]; if (d === undefined) throw new SetupError("SETUP_FIXTURE_THIEU " + nhom + "." + ten); return sao(d); };
const DTO = ten => lay_("dto", ten);
const CTX = ten => lay_("ctx", ten);
const YD = ten => lay_("y", ten);
const KQ_ = (ten, ctx) => ({...lay_("kq", ten), context: sao(ctx)});
function rqXem(ys, ctx, {cau_hinh = {trang_thai: "SAN_SANG", thieu: []}, quyen = {tao: true, tai_pdf: true, anh_xa: true}} = {}) {
  return {schema: FX.rq_schema, quyen: sao(quyen), cau_hinh: cau_hinh === null ? null : sao(cau_hinh), y_dinh: ys.map(sao), context: sao(ctx)};
}

// ------------------------------------------------------------------ DOM giả có kết nối thật (sao nguyên khung m4_02c_dto_ui_async.cjs)
let soClickTai = 0;
function moiTruong() {
  const reg = new Map(), dongId = new Set();
  let taoTinh = false;
  class El {
    constructor(tag) {
      this.tagName = String(tag).toUpperCase(); this.children = []; this.parent = null; this._text = ""; this._id = "";
      this.listeners = {}; this.attrs = {}; this.dataset = {}; this.style = {}; this._cls = new Set(); this.files = []; this.disabled = false;
      this.checked = false; this.selected = false; this._value = ""; this._valueSet = false; this.type = ""; this.title = ""; this.open = false;
    }
    get id() { return this._id; }
    set id(v) { this._id = v; if (!reg.has(v)) reg.set(v, []); reg.get(v).push(this); if (!taoTinh) dongId.add(v); }
    get isConnected() { let e = this; while (e) { if (e === body) return true; e = e.parent; } return false; }
    get className() { return [...this._cls].join(" "); }
    set className(v) { this._cls = new Set(String(v || "").split(/\s+/).filter(Boolean)); }
    get classList() { const s = this; return {add: (...c) => c.forEach(x => s._cls.add(x)), remove: (...c) => c.forEach(x => s._cls.delete(x)),
      toggle: (c, on) => { const v = on === undefined ? !s._cls.has(c) : on; if (v) s._cls.add(c); else s._cls.delete(c); return v; }, contains: c => s._cls.has(c)}; }
    get value() {
      if (this.tagName === "SELECT" && !this._valueSet) { const ops = this.children.filter(c => c.tagName === "OPTION"); const s = ops.find(o => o.selected || "selected" in o.attrs) || ops[0]; return s ? s.value : ""; }
      return this._value;
    }
    set value(v) { this._value = String(v ?? ""); this._valueSet = true; }
    get selectedIndex() { return this.children.filter(c => c.tagName === "OPTION").findIndex(o => o.value === this.value); }
    get textContent() { return this._text + this.children.map(c => c.textContent).join(""); }
    set textContent(v) { for (const c of this.children) c.parent = null; this._text = String(v ?? ""); this.children = []; }
    get firstChild() { return this.children[0] || null; }
    get lastChild() { return this.children[this.children.length - 1] || null; }
    _con(n) { const c = typeof n === "string" ? Object.assign(new El("#text"), {_text: n}) : n; if (c.parent) c.parent.children = c.parent.children.filter(x => x !== c); c.parent = this; return c; }
    append(...n) { for (const x of n) this.children.push(this._con(x)); }
    prepend(...n) { this.children.unshift(...n.map(x => this._con(x))); }
    replaceChildren(...n) { for (const c of this.children) c.parent = null; this._text = ""; this.children = []; this.append(...n); }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(x => x !== this); this.parent = null; }
    addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
    dispatch(t, ev = {}) { return (this.listeners[t] || []).map(fn => fn({preventDefault() {}, target: this, key: "", ...ev})); }
    click() { if (this.tagName === "A") soClickTai += 1; if (this.disabled) return []; return this.dispatch("click"); }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    removeAttribute(k) { delete this.attrs[k]; }
    getAttribute(k) { return this.attrs[k] ?? null; }
    querySelector(s) {  // chỉ ".lớp" — tìm hậu duệ theo thứ tự DFS
      const lop = s.startsWith(".") ? s.slice(1) : null;
      const tim = e => { for (const c of e.children) { if (lop && c._cls && c._cls.has(lop)) return c; const r = tim(c); if (r) return r; } return null; };
      return lop ? tim(this) : null;
    }
    focus() {} showModal() {} close() {}
  }
  const body = new El("body");
  const head = new El("head");
  const document = {
    body, head, title: "",
    getElementById: id => {
      const ds = (reg.get(id) || []).filter(e => e.isConnected);
      if (ds.length) return ds[ds.length - 1];
      if (dongId.has(id) || !ID_TINH.has(id)) return null;
      taoTinh = true; const e = new El("div"); e.id = id; taoTinh = false; body.append(e); return e;
    },
    createElement: t => new El(t),
    createTextNode: t => Object.assign(new El("#text"), {_text: String(t)}),
    querySelector: s => (s.includes("ktt-token") ? {content: "TOKEN-THU"} : null),
    querySelectorAll: () => [],
  };
  const calls = [];
  const fetch = (url, opts = {}) => new Promise((resolve, reject) => calls.push({url, opts, resolve, reject, method: (opts && opts.method) || "GET"}));
  let soFile = 0;
  class FileThay { constructor(parts, name, o = {}) { this.name = name; this.type = o.type || ""; this.size = parts.reduce((n, p) => n + (p.size ?? p.byteLength ?? 0), 0);
    this.lastModified = o.lastModified ?? (Date.now() + (++soFile)); } }
  const File = FILE_GOC || FileThay;
  let soUuid = 0;
  const henGio = (fn, ms, ...a) => { const t = setTimeout(fn, ms, ...a); if (ms > 0 && t && typeof t.unref === "function") t.unref(); return t; };
  const ctx = {
    document, Node: El, console, setTimeout: henGio, clearTimeout, Promise, Map, Set, JSON, Math, Date, Number, String, Object, Array, Error, TypeError, SyntaxError,
    encodeURIComponent, decodeURIComponent, URLSearchParams, location: {hash: "#m4"}, crypto: {randomUUID: () => "uuid-" + (++soUuid)},
    URL: {createObjectURL: () => "blob:x", revokeObjectURL() {}}, fetch, File, navigator: {}, Intl,
  };
  ctx.window = ctx;
  const wl = {};
  ctx.addEventListener = (t, fn) => { (wl[t] = wl[t] || []).push(fn); };
  vm.createContext(ctx);
  return {ctx, document, calls, wl, body};
}

function phanHoi(status, data, blobSize) {
  return {ok: status >= 200 && status < 300, status, headers: {get: () => "application/json"},
    json: async () => data,
    blob: async () => (BLOB_GOC ? new BLOB_GOC([new Uint8Array(blobSize ?? 0)], {type: "application/octet-stream"}) : {size: blobSize ?? 0, type: "application/octet-stream"})};
}
const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 10) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (!root) return null; if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
function timHet(root, pred, out = []) { if (!root) return out; if (pred(root)) out.push(root); for (const c of root.children || []) timHet(c, pred, out); return out; }
const nutTheoChu = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));
const theoNhan = (root, s) => tim(root, e => e.attrs && e.attrs["aria-label"] === s);
function bangCo(root, th) { return tim(root, e => e.tagName === "TABLE" && !!tim(e, x => x.tagName === "TH" && x.textContent === th)); }
function cot(bang, ten) {
  assert.ok(bang, "không có bảng chứa cột " + ten);
  const ths = timHet(bang, x => x.tagName === "TH").map(x => x.textContent), i = ths.indexOf(ten);
  assert.ok(i >= 0, "bảng không có cột " + ten + " (có: " + ths.join(" | ") + ")");
  const tbody = bang.children.find(c => c.tagName === "TBODY");
  return (tbody ? tbody.children : []).filter(r => r.tagName === "TR").map(r => (r.children[i] || {textContent: undefined}).textContent);
}

// ------------------------------------------------------------------ khung kiểm
class SetupError extends Error {}
const chuan = (dk, ma) => { if (!dk) throw new SetupError(ma); };
const KQ = {dat: [], hong: [], setup_errors: []};
async function ca(ten, fn) {  // MỌI ca đều được thử (môi trường riêng) — không dừng chuỗi, không bỏ qua
  try { await fn(); KQ.dat.push(ten); console.log("ĐẠT  " + ten); }
  catch (e) {
    if (e instanceof SetupError) { KQ.setup_errors.push({ca: ten, ma: e.message}); console.log("SETUP " + ten + ": " + e.message); }
    else { KQ.hong.push({ca: ten, loi: String((e && e.stack) || e)}); console.log("HỎNG " + ten + ": " + (e && e.message)); }
  }
}

const SRC_DP = "/m4/m4_duyet_pdf.js", SRC_RQ = "/m4/m4_request_nhap.js";
const NUT_TAO = "Tạo nháp Request", NUT_DS = "Đối soát Request", NUT_LAI = "Gửi lại y nguyên (cùng khóa)", NUT_RQ_MOI = "↻ Trạng thái Request";
const SAI_HD = "Phản hồi Request không đúng hợp đồng";
const TOM_TAT_CAN_CU = "Đủ căn cứ duyệt + PDF";  // tóm tắt căn cứ seal/PDF của d.request — không phải trạng thái Request

// ------------------------------------------------------------------ vỏ shell dựng từ ĐÚNG ID của fixture (sao m4_02c_dto_ui_async.cjs)
function vo() {
  const I = FX.ids, login = FX.login;
  const TONG = {cau_hinh: true, nguoi: {dang_nhap: login, vai_tro: "DU_AN"}, ghi_nguon: {san_sang: true, ly_do: null},
    pham_vi: [{du_an_id: I.du_an, vai: "PHU_TRACH", du_an: "Dự án tổng hợp", du_an_ma: "DA_XD_TH", phap_nhan: "PN_DEMO_A", soan: true, xem: true}],
    hop_dong: [{id: I.hd, ten: "Gói tổng hợp", so_hop_dong: I.so_hd, du_an_id: I.du_an, du_an: "Dự án tổng hợp", phap_nhan: "PN_DEMO_A", revision: 7,
      trang_thai_pl: "CHUA_KHAI", co_tep: true, soan: true, so_dot: 1}],
    dot: [], danh_muc_ho_so: [], nhanh_sau: [], tai_len_toi_da_byte: 52428800, danh_tinh_demo: [{dang_nhap: login, vai_tro: "DU_AN"}]};
  const CHI_TIET = {ho_so: {hop_dong_id: I.hd, du_an_id: I.du_an, phap_nhan_id: I.pn, ten: "Gói tổng hợp", so_hop_dong: I.so_hd, du_an: "Dự án tổng hợp",
    phap_nhan: "PN_DEMO_A", revision: 7, rev_tham_so: 2, tep_hop_dong_id: "tep-vo-1", trang_thai_pl: "CHUA_KHAI", soan: true},
    tep: [{id: "tep-vo-1", vai_tro_tai_lieu: "HOP_DONG", ten_goc: "hd.docx", media_type: "x", byte_length: 10, raw_sha256: "a".repeat(64), tao_boi: "X", tao_luc: "2026-01-01T00:00:00Z"}],
    trich_xuat: [], tham_so: [], xac_nhan: null, phu_luc: [], boq: [], boq_goc_dong: [],
    dot: [{id: I.dot, so_dot: 1, ngay_nghiem_thu: "2026-10-01", trang_thai: "NHAP", revision: 3, nop_luc: null, revision_ho_so: 7, can_cu_doi_sau_nop: false}],
    danh_muc_sha256: "b".repeat(64), nhanh_sau: []};
  const DOT_CT = {dot: {id: I.dot, hop_dong_id: I.hd, du_an_id: I.du_an, so_dot: 1, ngay_nghiem_thu: "2026-10-01", trang_thai: "NHAP", revision: 3, revision_ho_so: 7,
    so_hop_dong: I.so_hd, soan: true}, tep: [],
    checklist: [{ma: "A02", ten: "Biên bản nghiệm thu", bat_buoc_dot_dau: true, bat_buoc_dot_sau: true, ghi_chu: null, bat_buoc: true, tep: []}],
    thieu: [], du_can_cu: true, nop: null, hieu_luc: {ngay: "2026-10-01", phu_luc_ap_dung: [], so_hang_muc_hieu_luc: 0, so_hang_muc_bo: 0}, can_cu_doi_sau_nop: false, nhanh_sau: []};
  return {TONG, CHI_TIET, DOT_CT};
}

// ------------------------------------------------------------------ một phiên shell thật mới: app.js + m4.js → HĐ → đợt → tab Duyệt & PDF
async function moPhien() {
  const I = FX.ids, V = vo();
  const {ctx, document, calls} = moiTruong();
  const $ = id => document.getElementById(id);
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const lay = (pred, ma) => { const c = calls.find(x => !x.xong && pred(x)); chuan(c, ma); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const get = url => c => c.method === "GET" && c.url === url;
  const URL_DP = "/api/m4/duyet?dot_id=" + I.dot;
  const getDp = (ver = null) => get(URL_DP + (ver ? "&version_id=" + ver : ""));
  const laGetDp = c => c.method === "GET" && c.url.startsWith("/api/m4/duyet");
  const urlRq = ver => "/api/m4-request?" + new URLSearchParams({dot_id: I.dot, version_id: ver}).toString();
  const getRq = ver => get(urlRq(ver));
  const laRq = c => c.url.startsWith("/api/m4-request");
  const laGetRq = c => c.method === "GET" && laRq(c);
  const laPostRq = c => c.method === "POST" && laRq(c);
  const postRq = p => c => c.method === "POST" && c.url === "/api/m4-request/" + p;
  const laKt = c => c.url.startsWith("/api/m4/ke-toan");

  try { vm.runInContext(APP, ctx, {filename: "app.js"}); } catch (e) { throw new SetupError("SETUP_APP_JS: " + e.message); }
  chuan(ctx.window.kttChung, "SETUP_SEAM_KTTCHUNG");
  try { vm.runInContext(M4, ctx, {filename: "m4.js"}); } catch (e) { throw new SetupError("SETUP_M4_JS: " + e.message); }
  for (const c of calls) if (c.url !== "/api/m4" && c.url !== "/api/m4/mau") { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND", message: "ngoài ca"})); }
  await chay();

  const tra = async (c, status, data) => { c.resolve(phanHoi(status, data)); await chay(); };
  lay(get("/api/m4"), "SETUP_ROUTE_GET_API_M4").resolve(phanHoi(200, V.TONG)); await chay();
  for (const c of calls.filter(x => !x.xong && get("/api/m4/mau")(x))) { c.xong = true; c.resolve(phanHoi(200, {mau: []})); }
  await chay();
  chuan($("m4-nguoi") && $("m4-nguoi").textContent.includes(FX.login), "SETUP_DOM_M4_NGUOI");
  const li = tim($("m4-ds-hd"), e => e.tagName === "LI" && e.textContent.includes(I.so_hd));
  chuan(li, "SETUP_DOM_DS_HD"); li.dispatch("click"); await chay();
  const URL_HD = "/api/m4/hop-dong/" + I.hd;
  lay(get(URL_HD), "SETUP_ROUTE_GET_HD").resolve(phanHoi(200, V.CHI_TIET)); await chay();
  async function moTab(ten) { const b = nutTheoChu($("m4-chi-tiet"), ten); chuan(b, "SETUP_DOM_TAB " + ten); b.click(); await chay(); }
  await moTab("Đợt & checklist");
  const tr = tim($("m4-chi-tiet"), e => e.tagName === "TR" && !!e.children[0] && e.children[0].tagName === "TD" && e.children[0].textContent === "1");
  const bMo = tr && tim(tr, e => e.tagName === "BUTTON" && e.textContent === "Mở");
  chuan(bMo && !bMo.disabled, "SETUP_DOM_MO_DOT_1");
  bMo.click(); await chay();
  lay(get(URL_HD), "SETUP_ROUTE_GET_HD_2").resolve(phanHoi(200, V.CHI_TIET)); await chay();
  const gd = calls.find(c => !c.xong && get("/api/m4/dot/" + I.dot)(c));
  if (gd) { gd.xong = true; gd.resolve(phanHoi(200, V.DOT_CT)); await chay(); }
  chuan(nutTheoChu($("m4-chi-tiet"), "Duyệt & PDF"), "SETUP_DOM_TAB_DUYET_KHONG_CO");

  const scripts = src => document.head.children.filter(c => c.tagName === "SCRIPT" && c.src === src);
  const vungDp = () => tim($("m4-chi-tiet"), e => !!e._cls && e._cls.has("m4-dp"));
  const chuDp = () => (vungDp() || {textContent: ""}).textContent;
  const statusDp = () => { const v = vungDp(), s = v && v.querySelector(".m4-dp-status"); return s ? s.textContent : ""; };
  const oDp = nhan => theoNhan(vungDp(), nhan);
  const vungRq = () => tim(vungDp(), e => !!e._cls && e._cls.has("m4-dp-request"));
  const chuRq = () => (vungRq() || {textContent: ""}).textContent;
  const statusRq = () => { const v = vungRq(), s = v && v.querySelector(".m4-rq-status"); return s ? s.textContent : ""; };
  const nutRq = s => nutTheoChu(vungRq(), s);
  const bamRq = async s => { const b = nutRq(s); assert.ok(b, "không có nút " + s); assert.ok(!b.disabled, "nút " + s + " đang tắt: " + (b.attrs.title || "")); b.click(); await chay(); return b; };
  const toast = () => ($("toast") || {textContent: ""}).textContent;
  const tatVi = s => { const b = nutRq(s); assert.ok(b, "không có nút " + s); assert.ok(b.disabled, "nút " + s + " phải tắt"); return b.attrs.title || ""; };
  async function napThang(dto) {  // mở tab Duyệt lần đầu: tải lười tài sản DP THẬT, chạy module, trả GET đầu bằng DTO thật
    await moTab("Duyệt & PDF");
    chuan(scripts(SRC_DP).length === 1, "SETUP_SCRIPT_DP_KHONG_TAI");
    try { vm.runInContext(DP, ctx, {filename: "m4_duyet_pdf.js"}); } catch (e) { throw new SetupError("SETUP_DP_JS: " + e.message); }
    await chay();
    chuan(ctx.window.kttM4DuyetPdf, "SETUP_DP_KHONG_CONG_BO");
    await tra(lay(getDp(), "SETUP_ROUTE_GET_DUYET_DAU"), 200, dto);
    assert.ok(!chuDp().includes("không đúng hợp đồng"), "DTO duyệt thật bị UI từ chối: " + statusDp());
  }
  async function chayRq() {  // cầu nối đã chèn <script src=/m4/m4_request_nhap.js>: chạy MÃ THẬT của tài sản đó (tải lười đúng một lần)
    chuan(scripts(SRC_RQ).length === 1, "SETUP_SCRIPT_RQ_KHONG_TAI");
    try { vm.runInContext(RQ, ctx, {filename: "m4_request_nhap.js"}); } catch (e) { throw new SetupError("SETUP_RQ_JS: " + e.message); }
    await chay();
    chuan(ctx.window.kttM4RequestNhap, "SETUP_RQ_KHONG_CONG_BO");
  }
  async function moRq(ten, xem, ver = FX.ids.v1) {  // ca dương: DTO duyệt thật → widget mount → GET trạng thái Request (đúng version) → phản hồi
    await napThang(DTO(ten));
    await chayRq();
    await tra(cho(getRq(ver), "GET trạng thái Request đầu"), 200, xem);
    assert.ok(vungRq(), "không có vùng Request");
  }
  return {ctx, document, calls, $, cho, lay, dem, get, getDp, laGetDp, getRq, laRq, laGetRq, laPostRq, postRq, laKt, tra, scripts, vungDp, chuDp, oDp,
    vungRq, chuRq, statusRq, nutRq, bamRq, toast, tatVi, napThang, chayRq, moRq};
}

async function main() {
  const I = FX.ids;
  const CT = () => CTX("da_seal_tien");

  // ================================================================ W01 hiện hành dương
  await ca("W01 hiện hành: số seal nguyên văn, body đúng 3 trường, bấm đúp 1 POST, ACK có kiểu → đọc lại; placeholder giữ; 0 gọi KT", async () => {
    const P = await moPhien();
    const kt0 = P.dem(P.laKt);
    await P.moRq("da_seal_tien", rqXem([], CT()));
    const t = P.chuRq();
    assert.ok(t.includes("Số xin thanh toán theo seal: 120000000 VND"), "số xin thanh toán không nguyên văn theo seal: " + t);
    assert.ok(!t.includes("150000000"), "hiện gia_tri_nt thay số xin thanh toán");
    assert.ok(t.includes("Phiên bản hiện hành") && t.includes("không phải công nợ đã ghi"), "thiếu nhãn hiện hành/nháp ≠ công nợ");
    assert.ok(t.includes("Seal này chưa có Request nháp."), "thiếu trạng thái rỗng");
    assert.deepStrictEqual(cot(bangCo(P.vungDp(), "Trạng thái máy chủ"), "Trạng thái máy chủ"), ["Chờ xác nhận", TOM_TAT_CAN_CU], "tóm tắt căn cứ d.request bị đổi");
    const b = P.nutRq(NUT_TAO);
    assert.ok(b && !b.disabled, "Tạo phải mở: " + (b && b.attrs.title));
    assert.ok(P.nutRq(NUT_DS).disabled, "Đối soát phải tắt khi chưa có intent");
    b.click(); b.click(); await chay();  // bấm đúp cùng nút (đồng bộ) → đúng một bản ghi ý định
    assert.strictEqual(P.dem(P.laPostRq), 1, "bấm đúp gửi hơn một POST");
    assert.ok(P.nutRq(NUT_TAO).disabled, "đang bay mà Tạo còn mở");
    const p = P.cho(P.postRq("tao"), "POST tạo");
    const body = JSON.parse(p.opts.body);
    assert.deepStrictEqual(Object.keys(body).sort(), ["dot_id", "khoa", "version_id"], "body ngoài đúng 3 trường");
    assert.deepStrictEqual([body.dot_id, body.version_id], [I.dot, I.v1], "body sai đợt/phiên bản");
    assert.ok(/^m4rq-/.test(body.khoa), "khóa thao tác");
    assert.strictEqual(p.opts.headers["X-KTT-Token"], "TOKEN-THU", "thiếu token phiên");
    const g0 = P.dem(P.laGetRq);
    await P.tra(p, 200, KQ_("cho_quet", CT()));
    assert.ok(P.toast().includes("Kết quả tạo nháp Request: WAIT_SCAN — chờ quét tệp"), "ACK có kiểu không toast đúng: " + P.toast());
    assert.strictEqual(P.dem(P.laGetRq), g0 + 1, "ACK không đọc lại trạng thái đúng một lần");
    await P.tra(P.cho(P.getRq(I.v1), "GET sau ACK"), 200, rqXem([YD("cho_quet")], CT()));
    const t2 = P.chuRq();
    assert.ok(t2.includes("WAIT_SCAN — chờ quét tệp") && t2.includes("DX-0001") && t2.includes("Y_DINH"), "trạng thái/lịch sử intent không hiện");
    assert.strictEqual(P.tatVi(NUT_TAO), "Seal này đã có intent Request — dùng Đối soát", "lý do tắt Tạo");
    assert.ok(!P.nutRq(NUT_DS).disabled, "Đối soát phải mở khi có intent");
    assert.strictEqual(P.dem(P.laKt) - kt0, 0, "widget Request gọi nhánh KT");
    assert.deepStrictEqual(cot(bangCo(P.vungDp(), "Trạng thái máy chủ"), "Trạng thái máy chủ"), ["Chờ xác nhận", TOM_TAT_CAN_CU], "tóm tắt căn cứ sau lệnh bị đổi");
  });

  await ca("W02 seal thiếu số xin thanh toán → (thiếu), Tạo tắt, 0 POST", async () => {
    const P = await moPhien();
    await P.moRq("da_seal", rqXem([], CTX("da_seal")));
    assert.ok(P.chuRq().includes("Số xin thanh toán theo seal: (thiếu)"), "không hiện (thiếu)");
    assert.strictEqual(P.tatVi(NUT_TAO), "Seal thiếu số xin thanh toán/tiền tệ", "lý do tắt Tạo");
    P.nutRq(NUT_TAO).click(); await chay();
    assert.strictEqual(P.dem(P.laPostRq), 0, "nút tắt vẫn POST");
  });

  for (const [ten, dau] of [["chua_nop", "Chưa nộp hồ sơ đợt"], ["cho_pdf", "Đã duyệt — Chờ PDF hồ sơ đợt"], ["ke_tiep_nhap", "Cần kiểm lại"]]) {
    await ca("W03 không mount Request khi " + ten + " (không script, không GET/POST)", async () => {
      const P = await moPhien();
      await P.napThang(DTO(ten));
      assert.ok(P.chuDp().includes(dau), "DTO duyệt thật không hiện '" + dau + "'");
      await chay();
      assert.strictEqual(P.scripts(SRC_RQ).length, 0, "chèn script Request khi chưa seal");
      assert.ok(!P.vungRq(), "có vùng Request khi chưa seal");
      assert.strictEqual(P.dem(P.laRq), 0, "gọi /api/m4-request khi chưa seal");
    });
  }

  // ================================================================ W04 lịch sử
  await ca("W04 lịch sử V1 chọn tường minh: chỉ xem, Tạo tắt; Đối soát → HOLD có kiểu LICH_SU_CAN_TAO, đọc lại", async () => {
    const P = await moPhien();
    await P.napThang(DTO("ke_tiep_nhap"));
    assert.strictEqual(P.scripts(SRC_RQ).length, 0, "bản nháp mới nhất đã chèn script");
    const s = P.oDp("Phiên bản hồ sơ");
    chuan(s, "SETUP_DOM_CHON_PHIEN_BAN");
    s.value = I.v1; s.dispatch("change"); await chay();
    await P.tra(P.cho(P.getDp(I.v1), "GET chọn V1"), 200, DTO("chon_v1"));
    await P.chayRq();
    const c = CTX("chon_v1");
    assert.strictEqual(c.hien_hanh, false, "SETUP: context V1 phải là lịch sử");
    await P.tra(P.cho(P.getRq(I.v1), "GET Request V1"), 200, rqXem([YD("chua_ro_tao")], c));
    const t = P.chuRq();
    assert.ok(t.includes("Phiên bản lịch sử — chỉ xem") && t.includes("UNKNOWN — chưa rõ đã tạo"), "lịch sử/UNKNOWN không hiện");
    assert.strictEqual(P.tatVi(NUT_TAO), "Phiên bản lịch sử — chỉ xem; tạo Request chỉ ở phiên bản hiện hành", "lý do tắt Tạo lịch sử");
    await P.bamRq(NUT_DS);
    const p = P.cho(P.postRq("doi-soat"), "POST đối soát lịch sử");
    assert.deepStrictEqual(JSON.parse(p.opts.body).version_id, I.v1, "đối soát không gửi phiên bản đang xem");
    const g0 = P.dem(P.laGetRq);
    await P.tra(p, 409, KQ_("hold_can_tao", c));
    assert.ok(P.toast().includes("HOLD — tạm giữ — phiên bản lịch sử cần TẠO lại — chỉ xem, không gửi"), "HOLD có kiểu không hiện: " + P.toast());
    assert.strictEqual(P.dem(P.laGetRq), g0 + 1, "HOLD không đọc lại");
    assert.ok(!P.chuRq().includes(NUT_LAI), "HOLD có kiểu bị coi là chưa rõ");
    assert.strictEqual(P.dem(P.laPostRq), 1, "POST thêm");
  });

  // ================================================================ W05 giả mạo
  const GIA = [
    ["login khác", x => { x.dang_nhap = "MO_PHONG_DU_AN_B1"; }, "context khác người đăng nhập đang mở"],
    ["pháp nhân khác", x => { x.phap_nhan_id = I.v2; }, "context khác pháp nhân"],
    ["seal null", x => { x.seal_id = null; }, "context khác seal của hồ sơ đang xem"],
    ["hiện hành lệch", x => { x.hien_hanh = false; }, "context khác trạng thái hiện hành của hồ sơ"],
    ["phiên bản khác", x => { x.version_id = I.v2; }, "context khác phiên bản đang xem"],
    ["khóa lạ", x => { x.nguoi_tao = "nv"; }, "context sai bộ khóa"],
    ["schema lạ", x => { x.schema = "M4_REQUEST_HTTP_CONTEXT_V0"; }, "context sai schema"],
  ];
  for (const [ten, doi, lyDo] of GIA) {
    await ca("W05 GET context giả mạo (" + ten + ") → không hiện/không lệnh", async () => {
      const P = await moPhien(), c = CT();
      doi(c);
      await P.moRq("da_seal_tien", rqXem([YD("cho_quet")], c));
      const t = P.chuRq();
      assert.ok(t.includes(SAI_HD) && t.includes(lyDo), "không từ chối đúng lý do '" + lyDo + "': " + t);
      assert.ok(!P.nutRq(NUT_TAO) && !P.nutRq(NUT_DS) && !t.includes("DX-0001"), "context giả vẫn hiện intent/lệnh");
      assert.strictEqual(P.dem(P.laPostRq), 0, "có POST");
    });
  }
  await ca("W05b ACK có schema nhưng context seal giả → CHƯA RÕ, không đọc lại; Gửi lại cùng body", async () => {
    const P = await moPhien();
    await P.moRq("da_seal_tien", rqXem([], CT()));
    await P.bamRq(NUT_TAO);
    const p = P.cho(P.postRq("tao"), "POST");
    const c = CT(); c.seal_id = I.v2;
    const g0 = P.dem(P.laGetRq);
    await P.tra(p, 200, KQ_("cho_quet", c));
    assert.ok(P.toast().includes("Chưa rõ kết quả tạo nháp Request") && P.toast().includes("context khác seal"), "ACK giả bị chấp nhận: " + P.toast());
    assert.strictEqual(P.dem(P.laGetRq), g0, "ACK giả vẫn đọc lại");
    await P.bamRq(NUT_LAI);
    assert.strictEqual(P.cho(P.postRq("tao"), "POST gửi lại").opts.body, p.opts.body, "Gửi lại khác body/khóa");
  });

  // ================================================================ W06 UNKNOWN
  await ca("W06 mất mạng / 503 không kiểu → UNKNOWN, Tạo khóa; Gửi lại y nguyên hai lần cùng body; ACK có kiểu làm rõ", async () => {
    const P = await moPhien();
    await P.moRq("da_seal_tien", rqXem([], CT()));
    await P.bamRq(NUT_TAO);
    const p1 = P.cho(P.postRq("tao"), "POST 1");
    p1.reject(new TypeError("mất mạng")); await chay();
    assert.ok(P.toast().includes("Chưa rõ kết quả tạo nháp Request"), "mất mạng không là chưa rõ");
    assert.ok(P.chuRq().includes("UNKNOWN — chưa rõ kết quả tạo nháp Request"), "không hiện hàng UNKNOWN");
    assert.strictEqual(P.tatVi(NUT_TAO), "Lệnh trước chưa rõ kết quả — bấm Gửi lại y nguyên", "Tạo phải khóa khi có lệnh chưa rõ");
    await P.bamRq(NUT_LAI);
    const p2 = P.cho(P.postRq("tao"), "POST 2");
    assert.strictEqual(p2.opts.body, p1.opts.body, "Gửi lại 1 khác body");
    await P.tra(p2, 503, {error: "PG_KHONG_KET_NOI", message: "mất kết nối"});
    assert.ok(P.chuRq().includes("đã gửi 2 lần"), "không đếm lần gửi");
    await P.bamRq(NUT_LAI);
    const p3 = P.cho(P.postRq("tao"), "POST 3");
    assert.strictEqual(p3.opts.body, p1.opts.body, "Gửi lại 2 khác body");
    await P.tra(p3, 200, KQ_("cho_quet", CT()));
    assert.ok(P.toast().includes("Kết quả tạo nháp Request"), "ACK cuối không làm rõ");
    assert.ok(!P.chuRq().includes("UNKNOWN — chưa rõ kết quả"), "bản ghi đã rõ vẫn hiện UNKNOWN");
    assert.strictEqual(P.dem(P.laPostRq), 3, "số POST");
  });

  // ================================================================ W07 ACK muộn sau huy
  await ca("W07 POST đang bay → huy Duyệt & PDF → ACK về muộn: 0 toast, 0 GET", async () => {
    const P = await moPhien();
    await P.moRq("da_seal_tien", rqXem([], CT()));
    await P.bamRq(NUT_TAO);
    const p = P.cho(P.postRq("tao"), "POST");
    P.ctx.window.kttM4DuyetPdf.huy(); await chay();
    const t0 = P.toast(), n0 = P.calls.length;
    await P.tra(p, 200, KQ_("cho_quet", CT()));
    assert.strictEqual(P.toast(), t0, "ACK muộn vẫn toast");
    assert.strictEqual(P.calls.length, n0, "ACK muộn vẫn gọi mạng");
  });

  // ================================================================ W08 phiên bản A→B→A
  await ca("W08 V1 (lịch sử) → V2 nháp → V1: gỡ đồng bộ, GET/POST cũ về muộn 0 hiệu ứng, mount lại GET mới", async () => {
    const P = await moPhien();
    await P.napThang(DTO("ke_tiep_nhap"));
    const chon = async (ver, ten) => {
      const s = P.oDp("Phiên bản hồ sơ"); chuan(s, "SETUP_DOM_CHON_PHIEN_BAN");
      s.value = ver; s.dispatch("change"); await chay();
      await P.tra(P.cho(c => P.laGetDp(c) && c.url.includes("version_id=" + ver), "GET chọn " + ver), 200, DTO(ten));
    };
    await chon(I.v1, "chon_v1");
    await P.chayRq();
    const c = CTX("chon_v1");
    await P.tra(P.cho(P.getRq(I.v1), "GET Request V1 lần 1"), 200, rqXem([YD("cho_quet")], c));
    await P.bamRq(NUT_DS);
    const p = P.cho(P.postRq("doi-soat"), "POST đối soát V1");
    await P.bamRq(NUT_RQ_MOI);
    const gCu = P.cho(P.getRq(I.v1), "GET làm mới đang bay");
    await chon(I.v2, "ke_tiep_nhap");
    assert.ok(!P.vungRq(), "đổi sang bản nháp mà vùng Request còn");
    await chon(I.v1, "chon_v1");
    const gMoi = P.cho(P.getRq(I.v1), "GET Request V1 lần 2 (mount mới)");
    const t0 = P.toast(), n0 = P.calls.length;
    await P.tra(gCu, 200, rqXem([], c));
    await P.tra(p, 200, KQ_("cho_quet", c));
    assert.strictEqual(P.toast(), t0, "ACK của mount cũ vẫn toast");
    assert.strictEqual(P.calls.length, n0, "phản hồi cũ gây gọi mạng");
    await P.tra(gMoi, 200, rqXem([YD("cho_quet")], c));
    assert.ok(P.chuRq().includes("WAIT_SCAN — chờ quét tệp"), "GET mới không áp (bị GET cũ đè?)");
    assert.strictEqual(P.dem(P.laPostRq), 1, "POST thêm");
  });

  await ca("W09 huy widget khi GET trạng thái đang bay → phản hồi về muộn 0 hiệu ứng", async () => {
    const P = await moPhien();
    await P.napThang(DTO("da_seal_tien"));
    await P.chayRq();
    const g = P.cho(P.getRq(I.v1), "GET đầu");
    P.ctx.window.kttM4RequestNhap.huy();
    const t0 = P.chuRq(), n0 = P.calls.length;
    await P.tra(g, 200, rqXem([YD("cho_quet")], CT()));
    assert.strictEqual(P.chuRq(), t0, "GET muộn vẫn vẽ");
    assert.ok(!P.chuRq().includes("WAIT_SCAN"), "GET muộn áp dữ liệu");
    assert.strictEqual(P.calls.length, n0, "GET muộn gây gọi mạng");
  });

  // ================================================================ W10 thu hồi
  await ca("W10 GET 403 → không quyền, không lệnh; POST 404 sau khi đọc được → gỡ trạng thái", async () => {
    let P = await moPhien();
    await P.napThang(DTO("da_seal_tien"));
    await P.chayRq();
    await P.tra(P.cho(P.getRq(I.v1), "GET"), 403, {error: "M4_REQUEST_PHAM_VI", message: "Vai hiện hành không được xem"});
    assert.ok(P.chuRq().includes("Không có quyền xem/thao tác Request của đợt này: Vai hiện hành không được xem"), "403 không hiện");
    assert.ok(!P.nutRq(NUT_TAO) && !P.nutRq(NUT_DS), "403 vẫn có lệnh");
    P = await moPhien();
    await P.moRq("da_seal_tien", rqXem([], CT()));
    await P.bamRq(NUT_TAO);
    await P.tra(P.cho(P.postRq("tao"), "POST"), 404, {error: "M4_REQUEST_KHONG_THAY", message: "Không thấy đợt"});
    assert.ok(P.statusRq().includes("đã gỡ trạng thái và lệnh Request"), "404 không gỡ: " + P.statusRq());
    assert.ok(!P.nutRq(NUT_TAO) && !P.chuRq().includes(NUT_LAI), "404 vẫn có lệnh/Gửi lại");
  });

  await ca("W11 RUNNING: intent đang lease → Đối soát tắt; POST 409 DANG_XU_LY → RUNNING + đọc lại, không Gửi lại", async () => {
    let P = await moPhien();
    await P.moRq("da_seal_tien", rqXem([YD("dang_chay")], CT()));
    assert.ok(P.chuRq().includes("RUNNING — đang xử lý"), "không hiện RUNNING");
    assert.strictEqual(P.tatVi(NUT_DS), "Máy chủ đang xử lý intent này (RUNNING) — chờ rồi làm mới", "lý do tắt Đối soát");
    P = await moPhien();
    await P.moRq("da_seal_tien", rqXem([YD("chua_ro_tao")], CT()));
    await P.bamRq(NUT_DS);
    const g0 = P.dem(P.laGetRq);
    await P.tra(P.cho(P.postRq("doi-soat"), "POST"), 409, {error: "M4_REQUEST_DANG_XU_LY", message: "đang xử lý"});
    assert.ok(P.statusRq().includes("RUNNING — máy chủ đang xử lý"), "không báo RUNNING: " + P.statusRq());
    assert.strictEqual(P.dem(P.laGetRq), g0 + 1, "RUNNING không đọc lại");
    assert.ok(!P.chuRq().includes(NUT_LAI), "RUNNING bị coi là chưa rõ");
  });

  await ca("W12 CHUA_CAU_HINH: hiện thiếu cấu hình, Tạo tắt, 0 POST", async () => {
    const P = await moPhien();
    await P.moRq("da_seal_tien", rqXem([], CT(), {cau_hinh: {trang_thai: "CHUA_CAU_HINH", thieu: ["khoa_api"]}}));
    assert.ok(P.chuRq().includes("CHUA_CAU_HINH — máy chủ chưa cấu hình Request (thiếu: khoa_api); không có gọi mạng nào."), "không hiện CHUA_CAU_HINH");
    assert.strictEqual(P.tatVi(NUT_TAO), "Máy chủ chưa cấu hình Request (CHUA_CAU_HINH)", "lý do tắt Tạo");
    assert.strictEqual(P.dem(P.laPostRq), 0, "có POST");
    const k = KQ_("chua_cau_hinh", CT());  // kết quả lệnh CHUA_CAU_HINH thật (domain) phải qua được kiểm hợp đồng: y_dinh null, thieu
    assert.deepStrictEqual([k.trang_thai, k.y_dinh, k.thieu], ["CHUA_CAU_HINH", null, ["khoa_api"]], "SETUP kết quả CHUA_CAU_HINH");
  });

  await ca("W14 2xx sai hợp đồng → CHƯA RÕ, không đọc lại; Gửi lại cùng body", async () => {
    const P = await moPhien();
    await P.moRq("da_seal_tien", rqXem([], CT()));
    await P.bamRq(NUT_TAO);
    const p = P.cho(P.postRq("tao"), "POST");
    const g0 = P.dem(P.laGetRq);
    await P.tra(p, 200, {ok: true});
    assert.ok(P.toast().includes("Chưa rõ kết quả tạo nháp Request") && P.toast().includes("schema lạ"), "2xx sai hợp đồng bị coi là xong: " + P.toast());
    assert.strictEqual(P.dem(P.laGetRq), g0, "2xx sai vẫn đọc lại");
    await P.bamRq(NUT_LAI);
    assert.strictEqual(P.cho(P.postRq("tao"), "POST gửi lại").opts.body, p.opts.body, "Gửi lại khác body");
  });

  await ca("W15 tải script Request lỗi → báo trong vùng, không stub, 0 gọi Request", async () => {
    const P = await moPhien();
    await P.napThang(DTO("da_seal_tien"));
    const s = P.scripts(SRC_RQ);
    chuan(s.length === 1 && typeof s[0].onerror === "function", "SETUP_SCRIPT_RQ_ONERROR");
    s[0].onerror(); await chay();
    assert.ok(P.chuRq().includes("Chưa tải được thành phần Request nháp"), "không báo lỗi tải");
    assert.ok(!P.ctx.window.kttM4RequestNhap, "có stub widget");
    assert.strictEqual(P.dem(P.laRq), 0, "gọi Request khi không có widget");
    assert.strictEqual(P.scripts(SRC_RQ).length, 0, "script lỗi còn trong head");
  });
}

(async () => {
  if (loiFx) KQ.setup_errors.push({ca: "FIXTURE", ma: "SETUP_FIXTURE: " + (loiFx && loiFx.message)});
  else {
    try { await main(); } catch (e) { KQ.setup_errors.push({ca: "MAIN", ma: "SETUP_MAIN: " + String((e && e.stack) || e)}); }
  }
  await chay();
  if (loiNgoai.length) KQ.hong.push({ca: "unhandledRejection", loi: loiNgoai.map(e => String((e && e.stack) || e)).join("\n")});
  console.log(`\nKết quả: ${KQ.dat.length} đạt, ${KQ.hong.length} hỏng, ${KQ.setup_errors.length} setup_errors`);
  console.log("KET_QUA_JSON " + JSON.stringify(KQ));
  process.exitCode = KQ.hong.length || KQ.setup_errors.length ? 1 : 0;
})();
