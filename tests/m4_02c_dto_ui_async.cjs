"use strict";
// M4-02C INTEGRATION-REPAIR — DTO THẬT của backend (DuyetDot.xem chạy trong tests/test_m4_02c_dto_ui.py, chỉ giả tầng dữ liệu) đi qua MÃ UI THẬT
// (app.js + m4/giao_dien/m4.js + m4/giao_dien/m4_duyet_pdf.js). Không literal DTO viết tay cho ca dương: mọi DTO đọc từ tệp fixture do test Python
// sinh (đường dẫn = argv[2]); ca âm là ĐỘT BIẾN có chủ đích của chính DTO thật đó.
//  P*: ánh xạ DTO→UI chuẩn (phát hiện code/level/title/detail + giải trình đã lưu; "Đề nghị nguồn" = đúng de_xuat.kl_kn, null "(thiếu)", "0" vẫn "0";
//      công bố ba trạng thái; căn cứ có kiểu tách khỏi metadata tệp từ snapshot phiên bản; lý do trạng thái; lịch sử phiên bản; chọn phiên bản tường minh;
//      biến thể CHUA_NOP gắn thẻ; DTO V1 cũ thiếu tep_can_cu/chua_nop vẫn hợp lệ).
//  N*: biến thể CHUA_NOP chặt + trường bổ sung sai kiểu → SAI_DTO, không form/lệnh/POST.
//  R*: 200 hợp lệ xem=false thu hồi view ĐỒNG BỘ — ACK/blob giữ về muộn 0 hiệu ứng; ý định CHƯA RÕ giữ nguyên và Gửi lại y nguyên khi quyền trở lại.
//  M1: 2xx sai hợp đồng → Chưa rõ kết quả, không toast thành công, Gửi lại cùng body/khóa.
// Khung DOM/fetch sao từ tests/m4_02c_fix01_async.cjs (tệp đó KHÔNG sửa). Mỗi ca một môi trường mới. Không process.exit, không ghi tệp, không mạng.
// CODE_ONLY: WRITTEN_NOT_RUN. Root chạy qua test Python (sinh fixture rồi gọi `node tests/m4_02c_dto_ui_async.cjs <fixture.json>`, Node ≥ 18).
// Dòng cuối: `KET_QUA_JSON {"dat":[...],"hong":[...],"setup_errors":[...]}`. process.exitCode = 0 khi mọi ca đạt; 1 khi có hỏng/setup_errors/unhandledRejection.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");
const APP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/app.js"), "utf8");
const M4 = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/m4.js"), "utf8");
const DP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/m4_duyet_pdf.js"), "utf8");
const ID_TINH = new Set([...fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/index.html"), "utf8").matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const BLOB_GOC = globalThis.Blob || (() => { try { return require("buffer").Blob; } catch (_) { return null; } })();
const FILE_GOC = globalThis.File || (() => { try { return require("buffer").File; } catch (_) { return null; } })();
const loiNgoai = [];
process.on("unhandledRejection", e => { loiNgoai.push(e); });

// ------------------------------------------------------------------ fixture do backend thật sinh
let FX = null, loiFx = null;
try {
  FX = JSON.parse(fs.readFileSync(process.argv[2] || "", "utf8"));
  if (!FX || FX.schema !== "M4_02C_DTO_UI_FIXTURE_V1" || !FX.dto || !FX.ids) throw new Error("schema fixture lạ");
} catch (e) { loiFx = e; FX = null; }
const sao = o => JSON.parse(JSON.stringify(o));
const DTO = ten => { const d = FX.dto[ten]; if (!d) throw new SetupError("SETUP_FIXTURE_THIEU_DTO " + ten); return sao(d); };

// ------------------------------------------------------------------ DOM giả có kết nối thật (sao nguyên khung m4_02c_fix01_async.cjs)
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
const taoBlob = n => (BLOB_GOC ? new BLOB_GOC([new Uint8Array(n)], {type: "application/pdf"}) : {size: n, type: "application/pdf"});
const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 10) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (!root) return null; if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
function timHet(root, pred, out = []) { if (!root) return out; if (pred(root)) out.push(root); for (const c of root.children || []) timHet(c, pred, out); return out; }
const nutTheoChu = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));
const theoNhan = (root, s) => tim(root, e => e.attrs && e.attrs["aria-label"] === s);
// bảng có cột tiêu đề `th` (khớp nguyên văn) → giá trị chữ của cột `cot` theo từng dòng tbody
function bangCo(root, th) { return tim(root, e => e.tagName === "TABLE" && !!tim(e, x => x.tagName === "TH" && x.textContent === th)); }
function cot(bang, ten) {
  assert.ok(bang, "không có bảng chứa cột " + ten);
  const ths = timHet(bang, x => x.tagName === "TH").map(x => x.textContent), i = ths.indexOf(ten);
  assert.ok(i >= 0, "bảng không có cột " + ten + " (có: " + ths.join(" | ") + ")");
  const tbody = bang.children.find(c => c.tagName === "TBODY");
  return (tbody ? tbody.children : []).filter(r => r.tagName === "TR").map(r => (r.children[i] || {textContent: undefined}).textContent);
}
const h12 = v => v.slice(0, 12) + "…";

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

const SCHEMA = "M4_DUYET_PDF_V1";
const NUT_LUU = "Lưu kết luận", NUT_DUYET = "Duyệt hồ sơ đợt (", NUT_TAI_LEN = "Tải PDF hồ sơ đợt lên", NUT_LAM_MOI = "↻ Làm mới", NUT_TAI = "Tải PDF ↓";
const NUT_LAI = "Gửi lại y nguyên (cùng khóa)";
const NT = "Giá trị nghiệm thu chấp nhận (NT)";
const SAI_HD = "không đúng hợp đồng";
const tieuDe = ver => "Phiên bản hồ sơ đợt " + ver.slice(0, 12);
const SRC_DP = "/m4/m4_duyet_pdf.js";
let soRc = 0;
const RC = () => "77777777-7777-4777-8777-" + String(++soRc).padStart(12, "0");
function ACK(hanh, khoa, ctx, ids = {}) {
  return {schema: SCHEMA, hanh_dong: hanh, khoa, context: {...ctx}, receipt_id: RC(),
    ket_luan_id: null, quyet_dinh_id: null, pdf_id: null, seal_id: null, kt_pending_id: null, ...ids};
}
const KHONG_QUYEN = q => Object.fromEntries(Object.keys(q).map(k => [k, false]));  // 200 hợp lệ, mọi cờ (kể cả xem) false = thu hồi hiện hành

// ------------------------------------------------------------------ vỏ shell dựng từ ĐÚNG ID của fixture (ngữ cảnh m4.js phải trùng context DTO thật)
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

// ------------------------------------------------------------------ một phiên shell thật mới: app.js + m4.js → HĐ → đợt (chưa nạp module)
async function moPhien() {
  const I = FX.ids, V = vo();
  const {ctx, document, calls, wl} = moiTruong();
  const $ = id => document.getElementById(id);
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const lay = (pred, ma) => { const c = calls.find(x => !x.xong && pred(x)); chuan(c, ma); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const get = url => c => c.method === "GET" && c.url === url;
  const post = url => c => c.method === "POST" && c.url === url;
  const URL_DP = "/api/m4/duyet?dot_id=" + I.dot;
  const getDp = (ver = null) => get(URL_DP + (ver ? "&version_id=" + ver : ""));
  const laGetDp = c => c.method === "GET" && c.url.startsWith("/api/m4/duyet");
  const postDp = p => post("/api/m4/duyet/" + p);
  const laPostDp = c => c.method === "POST" && c.url.startsWith("/api/m4/duyet/");

  try { vm.runInContext(APP, ctx, {filename: "app.js"}); } catch (e) { throw new SetupError("SETUP_APP_JS: " + e.message); }
  chuan(ctx.window.kttChung, "SETUP_SEAM_KTTCHUNG");
  try { vm.runInContext(M4, ctx, {filename: "m4.js"}); } catch (e) { throw new SetupError("SETUP_M4_JS: " + e.message); }
  for (const c of calls) if (c.url !== "/api/m4" && c.url !== "/api/m4/mau") { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND", message: "ngoài ca"})); }
  await chay();

  const tra = async (c, status, data, n) => { c.resolve(phanHoi(status, data, n)); await chay(); };
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

  const scripts = () => document.head.children.filter(c => c.tagName === "SCRIPT" && c.src === SRC_DP);
  const vungDp = () => tim($("m4-chi-tiet"), e => !!e._cls && e._cls.has("m4-dp"));
  const chuDp = () => (vungDp() || {textContent: ""}).textContent;
  const statusDp = () => { const v = vungDp(), s = v && v.querySelector(".m4-dp-status"); return s ? s.textContent : ""; };
  const statusM4 = () => ($("m4-status") || {textContent: ""}).textContent;
  const nutDp = s => nutTheoChu(vungDp(), s);
  const oDp = nhan => theoNhan(vungDp(), nhan);
  const go = (nhan, v) => { const e = oDp(nhan); chuan(e && e.isConnected, "SETUP_DOM_O " + nhan); e.value = v; e.dispatch("input"); return e; };
  const bam = async s => { const b = nutDp(s); assert.ok(b, "không có nút " + s); assert.ok(!b.disabled, "nút " + s + " đang tắt: " + (b.attrs.title || b.title || "")); b.click(); await chay(); return b; };
  const toast = () => ($("toast") || {textContent: ""}).textContent;
  const giuBlob = c => { let tha = null; c.resolve({ok: true, status: 200, headers: {get: () => "application/pdf"}, json: async () => ({}),
    blob: () => new Promise(r => { tha = r; })}); return () => tha; };
  const bang = th => bangCo(vungDp(), th);
  async function napThang(dto) {  // mở tab Duyệt lần đầu: tải lười tài sản THẬT, chạy module, trả GET đầu bằng DTO cho trước
    await moTab("Duyệt & PDF");
    chuan(scripts().length === 1, "SETUP_SCRIPT_DP_KHONG_TAI");
    try { vm.runInContext(DP, ctx, {filename: "m4_duyet_pdf.js"}); } catch (e) { throw new SetupError("SETUP_DP_JS: " + e.message); }
    await chay();
    chuan(ctx.window.kttM4DuyetPdf, "SETUP_DP_KHONG_CONG_BO");
    await tra(lay(getDp(), "SETUP_ROUTE_GET_DUYET_DAU"), 200, dto);
  }
  async function napModule(dto, dau = "Căn cứ của phiên bản") {  // ca dương: DTO thật PHẢI hiện (không phải SAI_DTO/CHƯA NỐI) — sai là HỎNG ngữ nghĩa
    await napThang(dto);
    assert.ok(!chuDp().includes(SAI_HD), "DTO thật bị UI từ chối: " + statusDp());
    assert.ok(chuDp().includes(dau), "DTO thật không hiện '" + dau + "' — trạng thái: " + statusDp());
  }
  async function lamMoi(dto, moTa, ver = null) { await bam(NUT_LAM_MOI); await tra(cho(getDp(ver), moTa), 200, dto); }
  return {ctx, calls, $, cho, lay, dem, get, getDp, laGetDp, postDp, laPostDp, tra, vungDp, chuDp, statusDp, statusM4, nutDp, oDp, go, bam, toast, giuBlob,
    bang, napThang, napModule, lamMoi};
}

function chupNho(P) {
  return {toast: P.toast(), status: P.statusDp(), statusM4: P.statusM4(), get: P.dem(P.laGetDp), post: P.dem(P.laPostDp), fetch: P.calls.length, click: soClickTai,
    chu: P.chuDp()};
}
function khongDoiNho(P, t, ten) {
  const n = chupNho(P);
  for (const k of Object.keys(t)) assert.strictEqual(n[k], t[k], ten + ": phản hồi cũ đổi " + k);
}
function khongLenh(P, ten) {  // không form/lệnh nào mở và không POST
  for (const s of [NUT_LUU, NUT_DUYET, NUT_TAI_LEN, NUT_TAI]) assert.ok(!P.nutDp(s), ten + ": vẫn có nút " + s);
  assert.ok(!P.oDp(NT) && !P.oDp("Tiền tệ") && !P.oDp("Tệp PDF hồ sơ đợt"), ten + ": vẫn có ô nhập lệnh");
  assert.strictEqual(P.dem(P.laPostDp), 0, ten + ": có POST");
}

async function main() {
  const I = FX.ids;

  // ================================================================ P — ánh xạ DTO thật → UI
  await ca("P0 CHUA_NOP gắn thẻ: trạng thái + lý do máy chủ, không phiên bản/căn cứ/form/lệnh/POST", async () => {
    const P = await moPhien(), d = DTO("chua_nop");
    await P.napModule(d, "Chưa nộp hồ sơ đợt");
    const t = P.chuDp();
    assert.ok(t.includes("Lý do trạng thái (máy chủ): " + d.ly_do_trang_thai), "không hiện lý do trạng thái máy chủ");
    assert.ok(t.includes("không có lệnh nào được mở"), "không nói rõ không có lệnh");
    for (const s of ["Xem: có", "Lưu kết luận: không", "DUYỆT: không", "Bổ sung PDF: không"]) assert.ok(t.includes(s), "thiếu nhãn quyền " + s);
    for (const s of ["Căn cứ của phiên bản", "Phiên bản hồ sơ đợt ", "Chưa nối backend duyệt/PDF", "Tệp căn cứ đã chụp"]) assert.ok(!t.includes(s), "CHUA_NOP vẫn hiện " + s);
    khongLenh(P, "CHUA_NOP");
    await P.lamMoi(DTO("chua_nop"), "GET làm mới CHUA_NOP");
    assert.ok(P.chuDp().includes("Chưa nộp hồ sơ đợt") && !P.chuDp().includes(SAI_HD), "làm mới CHUA_NOP hỏng");
    khongLenh(P, "CHUA_NOP sau làm mới");
  });

  await ca("P1 đã nộp: Đề nghị nguồn = đúng de_xuat.kl_kn; phát hiện đủ cột; công bố CU vẫn Đã công bố; tệp căn cứ từ snapshot; lịch sử phiên bản", async () => {
    const P = await moPhien(), d = DTO("da_nop");
    await P.napModule(d);
    const t = P.chuDp();
    assert.ok(t.includes(tieuDe(I.v1)), "tiêu đề không theo version_id DTO");
    assert.ok(t.includes("Chờ kết luận"), "nhãn trạng thái");
    assert.ok(t.includes("Lý do trạng thái (máy chủ): " + d.ly_do_trang_thai), "thiếu lý do trạng thái máy chủ");
    // dòng NT: "Đề nghị nguồn" chỉ là kl_kn; KL hợp đồng/lũy kế ở cột riêng; null → (thiếu), "0" vẫn "0"
    const nt = P.bang("Đề nghị nguồn");
    assert.deepStrictEqual(cot(nt, "Đề nghị nguồn"), d.dong_nt.map(r => (r.de_xuat.kl_kn === null ? "(thiếu)" : r.de_xuat.kl_kn)), "Đề nghị nguồn lệch de_xuat.kl_kn");
    assert.deepStrictEqual(cot(nt, "Đề nghị nguồn"), ["(thiếu)", "0", "40.5"], "Đề nghị nguồn không đúng (thiếu)/0/40.5");
    assert.deepStrictEqual(cot(nt, "KL hợp đồng"), ["100", "50", "60"], "KL hợp đồng");
    assert.deepStrictEqual(cot(nt, "KL lũy kế nguồn"), ["10", "0", "12.25"], "KL lũy kế nguồn");
    assert.deepStrictEqual(cot(nt, "ĐVT"), ["m3", "m3", "m2"], "ĐVT do máy chủ");
    assert.deepStrictEqual(cot(nt, "Lũy kế đã duyệt trước"), ["(chưa có nguồn)", "(chưa có nguồn)", "(chưa có nguồn)"], "lũy kế trước");
    for (const r of d.dong_nt) assert.ok(P.oDp("KL chấp nhận " + r.row_id), "thiếu ô KL chấp nhận " + r.row_id);
    // phát hiện: code/level/title/detail + giải trình đã lưu
    const ph = P.bang("Giải trình đã lưu");
    assert.strictEqual(cot(ph, "Mã").length, d.phat_hien.length, "số dòng phát hiện ≠ DTO");
    assert.deepStrictEqual(cot(ph, "Mã"), ["L3 · L3_KL_VUOT", "L3 · L3_THIEU_CHU_KY", "COVERAGE · HOA_DON"], "cột Mã");
    assert.deepStrictEqual(cot(ph, "Mức"), ["ERROR", "(chưa rõ mức — không coi là đạt)", "CHUA_CHAY"], "cột Mức");
    assert.deepStrictEqual(cot(ph, "Tiêu đề"), ["Khối lượng vượt HĐ", "Thiếu chữ ký", "Kiểm HOA_DON: CHUA_CHAY"], "cột Tiêu đề");
    const ct = cot(ph, "Chi tiết");
    assert.strictEqual(ct[0], "Dòng R-03 vượt 5% · Hạng mục: R-03 · Tài liệu: BANG_KL · Số tiền: 125000.5", "chi tiết phát hiện 1");
    assert.strictEqual(ct[1], "—", "chi tiết trống phải là —");
    assert.strictEqual(ct[2], "Chưa có hóa đơn", "chi tiết coverage");
    assert.deepStrictEqual(cot(ph, "Giải trình đã lưu"), ["Chưa có giải trình", "Chưa có giải trình", "Chưa có giải trình"], "giải trình đã lưu");
    for (const p of d.phat_hien) assert.ok(P.oDp("Giải trình phát hiện " + p.finding_id), "thiếu ô giải trình " + p.finding_id);
    // review: công bố tách khỏi CO/CU
    const rv = P.bang("Công bố");
    assert.deepStrictEqual(cot(rv, "Cấp"), ["L3", "L2"], "cấp review");
    assert.deepStrictEqual(cot(rv, "Căn cứ (CO/CU)"), ["CO", "CU"], "CO/CU");
    assert.deepStrictEqual(cot(rv, "Công bố"), ["Đã công bố", "Đã công bố"], "CU vẫn là Đã công bố");
    assert.deepStrictEqual(cot(rv, "Trạng thái lần chạy"), ["SUCCEEDED", ""], "trạng thái lần chạy");
    assert.ok(cot(rv, "Lý do (máy chủ)")[1].includes("Căn cứ L2 đã đổi"), "lý do L2 CU");
    // căn cứ có kiểu ≠ metadata tệp
    const cc = P.bang("Định danh (có kiểu)");
    assert.deepStrictEqual(cot(cc, "Loại căn cứ"), ["Phiên bản đã nộp (PHIEN_BAN)", "Vật liệu hồ sơ HĐ/tham số/PL/BOQ (VAT_LIEU)", "Review Chứng từ L3 (REVIEW_L3)",
      "Review L1+L2 (REVIEW_L2)", "Lũy kế đợt trước đã duyệt (TRUOC_DA_DUYET)", "Thuế/AP (THUE)", "Đồ thị căn cứ (DO_THI)"], "loại căn cứ");
    const dd = cot(cc, "Định danh (có kiểu)");
    assert.strictEqual(dd[0], "Bản số 1 · phiên bản " + h12(I.v1) + " · digest phiên bản " + h12(d.can_cu[0].digest), "định danh phiên bản");
    assert.strictEqual(dd[1], "rev hồ sơ lúc nộp 7 · rev hồ sơ hiện hành 7", "định danh vật liệu");
    assert.strictEqual(dd[6], "SHA đồ thị " + h12(d.context.basis_sha256), "định danh đồ thị");
    assert.ok(!dd.some(x => x.includes("SHA-256 (máy chủ không ghi loại)")), "căn cứ có kiểu bị hiện như hash tệp");
    const tp = P.bang("Tên tệp");
    assert.deepStrictEqual(cot(tp, "Vai"), ["HOP_DONG", "PHU_LUC", "HO_SO_DOT", "HO_SO_DOT", "BOQ", "BOQ"], "vai tệp");
    assert.deepStrictEqual(cot(tp, "Trạng thái"), ["CO", "KHONG_GAN_TEP", "CO", "THIEU_METADATA", "CO", "THIEU_METADATA"], "trạng thái tệp");
    assert.deepStrictEqual(cot(tp, "Tên tệp"), ["HD-TH-01.pdf", "(thiếu)", "BB-NT-dot1.pdf", "(thiếu)", "BOQ-HD.xlsx", "(thiếu)"], "tên tệp");
    assert.deepStrictEqual(cot(tp, "Byte"), ["123456", "(thiếu)", "2048", "(thiếu)", "4096", "(thiếu)"], "byte tệp");
    assert.strictEqual(cot(tp, "SHA-256 tệp")[0], h12(FX.sha.hd), "SHA tệp hợp đồng");
    assert.strictEqual(cot(tp, "SHA-256 tệp")[3], "(thiếu) · đã chụp " + h12(FX.sha.dot2), "tệp thiếu metadata phải giữ hash đã chụp, không mượn");
    assert.ok(cot(tp, "Lý do (máy chủ)")[3].includes("không mượn tệp hiện hành"), "lý do THIEU_METADATA");
    // lịch sử phiên bản
    const ls = P.bang("Đang xem");
    assert.deepStrictEqual(cot(ls, "Bản số"), ["1"], "lịch sử phiên bản");
    assert.deepStrictEqual(cot(ls, "Kết luận (rev)"), ["chưa có"], "kết luận rev");
    assert.deepStrictEqual(cot(ls, "Mới nhất"), ["mới nhất"], "mới nhất");
    assert.deepStrictEqual(cot(ls, "Đang xem"), ["đang xem"], "đang xem");
    assert.ok(!t.includes("object_key"), "lộ object_key");
    assert.ok(P.nutDp(NUT_LUU) && !P.nutDp(NUT_LUU).disabled, "Lưu kết luận phải mở cho CHO_KET_LUAN có quyền");
  });

  await ca("P2 CHO_DUYET: giải trình đã lưu hiện theo phát hiện; POST kết luận dùng đúng ID/dòng/phát hiện của DTO thật", async () => {
    const P = await moPhien(), d = DTO("cho_duyet");
    await P.napModule(d);
    const t = P.chuDp();
    assert.ok(t.includes("Chờ duyệt") && t.includes("Kết luận đã lưu: " + h12(I.kl)), "kết luận đã lưu");
    assert.deepStrictEqual(cot(P.bang("Giải trình đã lưu"), "Giải trình đã lưu"), ["Đã ghi giải trình: " + FX.ly_do_f01, "Chưa có giải trình", "Chưa có giải trình"],
      "giải trình đã lưu theo phát hiện");
    assert.strictEqual(P.oDp("Giải trình phát hiện F-01").value, FX.ly_do_f01, "ô giải trình không hạt từ kết luận máy chủ");
    assert.strictEqual(P.oDp("KL chấp nhận R-01").value, "10", "ô KL chấp nhận không hạt từ kết luận máy chủ");
    assert.strictEqual(P.oDp(NT).value, "150000000", "ô NT không hạt từ kết luận máy chủ");
    assert.ok(P.nutDp(NUT_DUYET) && !P.nutDp(NUT_DUYET).disabled, "Duyệt phải mở ở CHO_DUYET có quyền DUYET");
    await P.bam(NUT_LUU);
    const p = P.cho(P.postDp("ket-luan"), "POST kết luận");
    const b = JSON.parse(p.opts.body);
    assert.deepStrictEqual([b.dot_id, b.version_id, b.revision, b.expected_basis], [I.dot, I.v1, 1, d.context.basis_sha256], "ngữ cảnh body");
    assert.deepStrictEqual(b.dong_nt.map(r => r.row_id), d.dong_nt.map(r => r.row_id), "row_id body ≠ DTO");
    assert.deepStrictEqual(b.xu_ly_phat_hien, [{finding_id: "F-01", ly_do: FX.ly_do_f01}], "xử lý phát hiện body");
    assert.deepStrictEqual([b.gia_tri_nt, b.so_xin_thanh_toan, b.tam_ung, b.thu_hoi, b.giu_lai, b.tien_te], ["150000000", "120000000", "0", null, "6000000", "VND"], "tiền body");
    const g0 = P.dem(P.laGetDp);
    await P.tra(p, 200, ACK("KET_LUAN", b.khoa, d.context, {ket_luan_id: I.kl}));
    assert.ok(P.toast().includes("Đã lưu kết luận"), "ACK hợp lệ không toast");
    assert.strictEqual(P.dem(P.laGetDp), g0 + 1, "ACK hợp lệ không đọc lại đúng một lần");
  });

  await ca("P3 L3 CU + tệp HĐ đổi hash: Cần kiểm lại với lý do L3; CU vẫn Đã công bố; KHONG_KHOP hiện cả hash đã chụp", async () => {
    const P = await moPhien(), d = DTO("l3_cu");
    await P.napModule(d);
    const t = P.chuDp();
    assert.ok(t.includes("Cần kiểm lại") && t.includes("Lý do trạng thái (máy chủ): " + d.ly_do_trang_thai) && d.ly_do_trang_thai.includes("Chạy lại L3"), "lý do CU");
    const rv = P.bang("Công bố");
    assert.deepStrictEqual(cot(rv, "Căn cứ (CO/CU)"), ["CU", "CU"], "CU");
    assert.deepStrictEqual(cot(rv, "Công bố"), ["Đã công bố", "Đã công bố"], "CU vẫn Đã công bố");
    const tp = P.bang("Tên tệp");
    assert.strictEqual(cot(tp, "Trạng thái")[0], "KHONG_KHOP", "tệp HĐ đổi hash");
    assert.strictEqual(cot(tp, "SHA-256 tệp")[0], h12(FX.sha.hd_moi) + " · đã chụp " + h12(FX.sha.hd), "SHA lưu + đã chụp");
    assert.ok(P.nutDp(NUT_LUU).disabled, "CAN_KIEM_LAI không cho lưu kết luận");
  });

  await ca("P4 vật liệu đổi sau nộp: VAT_LIEU DOI_SAU_NOP với revision lúc nộp/hiện hành", async () => {
    const P = await moPhien(), d = DTO("doi_sau_nop");
    await P.napModule(d);
    const cc = P.bang("Định danh (có kiểu)");
    assert.strictEqual(cot(cc, "Trạng thái")[1], "DOI_SAU_NOP", "trạng thái vật liệu");
    assert.strictEqual(cot(cc, "Định danh (có kiểu)")[1], "rev hồ sơ lúc nộp 7 · rev hồ sơ hiện hành 8", "định danh vật liệu");
    assert.ok(P.chuDp().includes("Lý do trạng thái (máy chủ): " + d.ly_do_trang_thai) && d.trang_thai === "CAN_KIEM_LAI", "lý do trạng thái");
  });

  await ca("P5 CHO_PDF: đã duyệt, kế toán Chưa chuyển, Request Chờ PDF kèm lý do máy chủ; còn nút tải PDF lên", async () => {
    const P = await moPhien(), d = DTO("cho_pdf");
    await P.napModule(d);
    const t = P.chuDp();
    assert.ok(t.includes("Đã duyệt — Chờ PDF hồ sơ đợt") && t.includes("Quyết định " + h12(I.qd)), "quyết định");
    const nh = P.bang("Trạng thái máy chủ");
    assert.deepStrictEqual(cot(nh, "Trạng thái máy chủ"), ["Chưa chuyển", "Chờ PDF"], "hai nhánh");
    assert.ok(cot(nh, "Ghi chú")[1].includes("Máy chủ: " + d.request.ly_do + "."), "lý do Request máy chủ");
    assert.ok(cot(nh, "Ghi chú")[0].includes("Máy chủ: " + d.kt.ly_do + "."), "lý do KT máy chủ");
    assert.ok(P.nutDp(NUT_TAI_LEN), "thiếu nút tải PDF lên");
    assert.ok(!P.nutDp(NUT_DUYET), "đã duyệt mà còn nút duyệt");
  });

  await ca("P6 DA_SEAL: niêm phong, KT Chờ xác nhận theo seal của phiên bản, Request đủ điều kiện — chưa nối; tải PDF đúng độ dài click 1", async () => {
    const P = await moPhien(), d = DTO("da_seal");
    await P.napModule(d);
    const t = P.chuDp();
    assert.ok(t.includes("Đã niêm phong với PDF hồ sơ đợt") && t.includes("Đã niêm phong"), "seal");
    const nh = P.bang("Trạng thái máy chủ");
    assert.deepStrictEqual(cot(nh, "Trạng thái máy chủ"), ["Chờ xác nhận", "Đủ căn cứ duyệt + PDF"], "hai nhánh sau seal");
    assert.ok(cot(nh, "Ghi chú")[0].includes("Hồ sơ KT " + h12(I.goc)) && !cot(nh, "Ghi chú")[0].includes("là lịch sử từ phiên bản"), "KT của chính phiên bản");
    assert.ok(!P.nutDp(NUT_TAI_LEN), "đã seal mà còn tải PDF lên");
    const c0 = soClickTai;
    await P.bam(NUT_TAI);
    await P.tra(P.cho(P.get("/api/m4/duyet/" + I.v1 + "/pdf/" + I.pdf), "GET tải PDF"), 200, null, d.pdf.byte_length);
    assert.strictEqual(soClickTai, c0 + 1, "PDF đúng độ dài không tải đúng một lần");
  });

  await ca("P7 phiên bản kế tiếp nháp: không mượn tệp/KT; lịch sử 2 bản; chọn V1 tường minh → GET version_id → DA_SEAL của V1", async () => {
    const P = await moPhien(), d = DTO("ke_tiep_nhap");
    await P.napModule(d);
    let t = P.chuDp();
    assert.ok(t.includes(tieuDe(I.v2)) && t.includes("Cần kiểm lại") && t.includes("Lý do trạng thái (máy chủ): " + d.ly_do_trang_thai), "V2 nháp");
    assert.ok(t.includes("Phiên bản không có tham chiếu tệp nào — " + d.tep_can_cu_ly_do + "."), "tệp căn cứ nháp phải rỗng kèm lý do");
    assert.ok(t.includes("Gốc KT của đợt " + h12(I.goc) + " là lịch sử từ phiên bản đã seal trước"), "gốc KT phải là lịch sử");
    assert.deepStrictEqual(cot(P.bang("Trạng thái máy chủ"), "Trạng thái máy chủ"), ["Chưa chuyển", "Chờ PDF"], "V2 chưa bàn giao KT");
    const ls = P.bang("Đang xem");
    assert.deepStrictEqual(cot(ls, "Bản số"), ["1", "2"], "lịch sử 2 bản");
    assert.deepStrictEqual(cot(ls, "Seal"), [h12(I.seal), "chưa có"], "seal theo bản");
    assert.deepStrictEqual(cot(ls, "Kết luận (rev)"), ["1", "chưa có"], "kết luận rev theo bản");
    assert.deepStrictEqual(cot(ls, "Mới nhất"), ["", "mới nhất"], "mới nhất");
    assert.deepStrictEqual(cot(ls, "Đang xem"), ["", "đang xem"], "đang xem");
    const s = P.oDp("Phiên bản hồ sơ");
    assert.ok(s && s.tagName === "SELECT", "thiếu ô chọn phiên bản");
    assert.deepStrictEqual(s.children.map(o => o.textContent), ["Bản số 1 · " + h12(I.v1) + " · kết luận rev 1", "Bản số 2 · " + h12(I.v2) + " · kết luận rev — (mới nhất)"],
      "nhãn chọn phiên bản");
    s.value = I.v1; s.dispatch("change"); await chay();
    await P.tra(P.cho(P.getDp(I.v1), "GET chọn V1 tường minh"), 200, DTO("chon_v1"));
    t = P.chuDp();
    assert.ok(!t.includes(SAI_HD), "DTO V1 chọn tường minh bị từ chối: " + P.statusDp());
    assert.ok(t.includes(tieuDe(I.v1)) && t.includes("(đã chọn tường minh)") && t.includes("Đã niêm phong với PDF hồ sơ đợt"), "V1 đã seal");
    assert.deepStrictEqual(cot(P.bang("Trạng thái máy chủ"), "Trạng thái máy chủ"), ["Chờ xác nhận", "Đủ căn cứ duyệt + PDF"], "V1 KT theo seal của V1");
    assert.ok(!t.includes("là lịch sử từ phiên bản đã seal trước"), "V1 đã seal không phải lịch sử gốc");
  });

  await ca("P8 tương thích DTO V1 cũ: thiếu tep_can_cu/chua_nop/phien_ban vẫn hợp lệ, hiện 'chưa cung cấp metadata tệp'", async () => {
    const P = await moPhien(), d = DTO("da_nop");
    for (const k of ["tep_can_cu", "tep_can_cu_ly_do", "chua_nop", "phien_ban"]) delete d[k];
    await P.napModule(d);
    assert.ok(P.chuDp().includes("Máy chủ chưa cung cấp metadata tệp căn cứ cho phiên bản này"), "không báo chưa cung cấp metadata tệp");
    assert.ok(!P.bang("Tên tệp"), "không được bịa bảng tệp");
  });

  await ca("P9 chưa có review: công bố null = 'Chưa có kết quả phù hợp / chưa xác định' (không phải Chưa công bố)", async () => {
    const P = await moPhien(), d = DTO("chua_review");
    await P.napModule(d);
    const rv = P.bang("Công bố");
    assert.deepStrictEqual(cot(rv, "Công bố"), ["Chưa có kết quả phù hợp / chưa xác định", "Chưa có kết quả phù hợp / chưa xác định"], "công bố null");
    assert.deepStrictEqual(cot(rv, "Lần chạy"), ["(chưa có)", "(chưa có)"], "lần chạy");
    const t = P.chuDp();
    assert.ok(t.includes("Máy chủ không trả dòng NT nào") && t.includes("Không có phát hiện.") && !t.includes("Chưa công bố"), "rỗng trung thực");
  });

  // ================================================================ N — đột biến DTO thật → SAI_DTO, không lệnh
  const AM = [
    ["N01 chua_nop là chuỗi", "chua_nop", d => { d.chua_nop = "true"; }, "chua_nop không phải boolean"],
    ["N02 CHUA_NOP thiếu thẻ chua_nop", "chua_nop", d => { delete d.chua_nop; }, "biến thể chưa nộp thiếu thẻ"],
    ["N03 thẻ chua_nop trên trạng thái khác", "da_nop", d => { d.chua_nop = true; }, "biến thể chưa nộp thiếu thẻ"],
    ["N04 CHUA_NOP có version_id", "chua_nop", d => { d.context.version_id = I.v1; }, "chưa nộp mà có phiên bản/basis/revision"],
    ["N05 CHUA_NOP có basis", "chua_nop", d => { d.context.basis_sha256 = "a".repeat(64); }, "chưa nộp mà có phiên bản/basis/revision"],
    ["N06 CHUA_NOP revision 1", "chua_nop", d => { d.context.revision = 1; }, "chưa nộp mà có phiên bản/basis/revision"],
    ["N07 CHUA_NOP có quyền ket_luan", "chua_nop", d => { d.quyen.ket_luan = true; }, "chưa nộp mà có quyền lệnh"],
    ["N08 CHUA_NOP thiếu cờ phien_ban", "chua_nop", d => { delete d.quyen.phien_ban; }, "chưa nộp mà có quyền lệnh"],
    ["N09 CHUA_NOP có phiên bản trong lịch sử", "chua_nop", d => { d.phien_ban = sao(FX.dto.da_nop.phien_ban); }, "chưa nộp mà có phiên bản"],
    ["N10 CHUA_NOP có căn cứ", "chua_nop", d => { d.can_cu = sao(FX.dto.da_nop.can_cu); }, "chưa nộp mà có căn cứ"],
    ["N11 CHUA_NOP thiếu tep_can_cu", "chua_nop", d => { delete d.tep_can_cu; }, "chưa nộp mà có căn cứ"],
    ["N12 CHUA_NOP có lịch sử kết luận", "chua_nop", d => { d.ket_luan_lich_su = [{id: I.kl, revision: 1}]; }, "chưa nộp mà có lịch sử kết luận/PDF"],
    ["N13 CHUA_NOP có PDF", "chua_nop", d => { d.pdf = sao(FX.dto.da_seal.pdf); }, "chưa nộp mà có kết luận/quyết định/PDF/seal"],
    ["N14 CHUA_NOP có pending KT", "chua_nop", d => { d.kt.pending_id = I.goc; }, "chưa nộp mà có KT"],
    ["N15 CHUA_NOP mượn gốc KT", "chua_nop", d => { d.kt.goc_id = I.goc; }, "chưa nộp mà có KT"],
    ["N16 CHUA_NOP Request đủ điều kiện", "chua_nop", d => { d.request.trang_thai = "DU_DIEU_KIEN_CHUA_NOI"; }, "chưa nộp mà Request khác Chờ PDF"],
    ["N17 CHUA_NOP có coverage", "chua_nop", d => { d.coverage = {HOA_DON: {trang_thai: "CHECKED"}}; }, "chưa nộp mà có coverage"],
    ["N18 CHUA_NOP khác HĐ", "chua_nop", d => { d.context.hop_dong_id = I.v2; }, "context khác đợt/HĐ đang mở"],
    ["N19 có phiên bản nhưng version_id null", "da_nop", d => { d.context.version_id = null; }, "phiên bản không đúng phiên bản đã chọn"],
    ["N20 có phiên bản nhưng basis null", "da_nop", d => { d.context.basis_sha256 = null; }, "revision/basis không hợp lệ"],
    ["N21 kl_kn là số JS", "da_nop", d => { d.dong_nt[2].de_xuat.kl_kn = 40.5; }, "số đề xuất nguồn không phải chuỗi thập phân/null"],
    ["N22 cong_bo là chuỗi", "da_nop", d => { d.review_refs[0].cong_bo = "true"; }, "cờ công bố review sai kiểu"],
    ["N23 byte_length âm", "da_nop", d => { d.tep_can_cu[0].byte_length = -1; }, "metadata tệp căn cứ sai kiểu"],
    ["N24 xu_ly sai kiểu", "da_nop", d => { d.phat_hien[0].xu_ly = "đã xử lý"; }, "giải trình phát hiện sai kiểu"],
    ["N25 lịch sử không gồm phiên bản đang xem", "da_nop", d => { d.phien_ban[0].version_id = I.v2; }, "lịch sử phiên bản không gồm phiên bản đang xem"],
    ["N26 gốc KT không phải UUID", "da_nop", d => { d.kt.goc_id = "goc-1"; }, "gốc KT sai kiểu"],
  ];
  for (const [ten, goc, doi, lyDo] of AM) {
    await ca(ten + " → SAI_DTO, không lệnh", async () => {
      const P = await moPhien(), d = DTO(goc);
      doi(d);
      await P.napThang(d);
      const t = P.chuDp();
      assert.ok(t.includes(SAI_HD) && t.includes(lyDo), "không từ chối đúng lý do '" + lyDo + "': " + P.statusDp());
      assert.ok(!t.includes("Căn cứ của phiên bản") && !t.includes("Chưa nộp hồ sơ đợt"), "DTO sai vẫn hiện hồ sơ");
      khongLenh(P, ten);
    });
  }
  await ca("N27 CHUA_NOP trả về sau khi đã chọn phiên bản tường minh → SAI_DTO", async () => {
    const P = await moPhien();
    await P.napModule(DTO("ke_tiep_nhap"));
    const s = P.oDp("Phiên bản hồ sơ");
    chuan(s, "SETUP_DOM_CHON_PHIEN_BAN");
    s.value = I.v1; s.dispatch("change"); await chay();
    await P.tra(P.cho(P.getDp(I.v1), "GET chọn V1"), 200, DTO("chua_nop"));
    assert.ok(P.chuDp().includes(SAI_HD) && P.chuDp().includes("chưa nộp nhưng đã chọn phiên bản tường minh"), "không từ chối: " + P.statusDp());
    khongLenh(P, "N27");
  });

  // ================================================================ R — 200 hợp lệ xem=false thu hồi view đồng bộ
  await ca("R1 ACK giữ → GET 200 xem=false → ACK về muộn: 0 hiệu ứng, thông báo thu hồi giữ nguyên", async () => {
    const P = await moPhien(), d = DTO("cho_duyet");
    await P.napModule(d);
    P.go(NT, "150000001");
    await P.bam(NUT_LUU);
    const p = P.cho(P.postDp("ket-luan"), "POST giữ");
    const khoa = JSON.parse(p.opts.body).khoa;
    const thu = DTO("cho_duyet"); thu.quyen = KHONG_QUYEN(thu.quyen);
    await P.lamMoi(thu, "GET xem=false");
    assert.ok(P.chuDp().includes("Không có quyền xem/thao tác hồ sơ duyệt"), "xem=false không thu hồi");
    assert.ok(!P.chuDp().includes("Căn cứ của phiên bản"), "xem=false vẫn hiện bằng chứng");
    const t = chupNho(P);
    await P.tra(p, 200, ACK("KET_LUAN", khoa, d.context, {ket_luan_id: I.kl}));
    khongDoiNho(P, t, "R1");
    assert.ok(!P.toast().includes("Đã lưu kết luận"), "ACK muộn vẫn toast");
  });

  await ca("R1b POST mất mạng sau thu hồi = CHƯA RÕ giữ nguyên; quyền trở lại → Gửi lại đúng body/khóa → ACK toast", async () => {
    const P = await moPhien(), d = DTO("cho_duyet");
    await P.napModule(d);
    P.go(NT, "150000002");
    await P.bam(NUT_LUU);
    const p1 = P.cho(P.postDp("ket-luan"), "POST 1");
    const thu = DTO("cho_duyet"); thu.quyen = KHONG_QUYEN(thu.quyen);
    await P.lamMoi(thu, "GET xem=false");
    const t = chupNho(P);
    p1.reject(new TypeError("mất mạng")); await chay();
    khongDoiNho(P, t, "R1b mất mạng muộn");
    await P.lamMoi(DTO("cho_duyet"), "GET quyền trở lại");
    assert.ok(P.chuDp().includes("Chưa rõ kết quả lưu kết luận"), "ý định CHƯA RÕ không còn");
    await P.bam(NUT_LAI);
    const p2 = P.cho(P.postDp("ket-luan"), "POST gửi lại");
    assert.strictEqual(p2.opts.body, p1.opts.body, "Gửi lại không y nguyên body/khóa");
    await P.tra(p2, 200, ACK("KET_LUAN", JSON.parse(p1.opts.body).khoa, d.context, {ket_luan_id: I.kl}));
    assert.ok(P.toast().includes("Đã lưu kết luận"), "ACK gửi lại không toast");
  });

  await ca("R2 blob PDF giữ → GET 200 xem=false → blob về: 0 click; quyền trở lại tải đúng một lần", async () => {
    const P = await moPhien(), d = DTO("da_seal");
    await P.napModule(d);
    await P.bam(NUT_TAI);
    const tha = P.giuBlob(P.cho(P.get("/api/m4/duyet/" + I.v1 + "/pdf/" + I.pdf), "GET tải giữ"));
    await chay();
    const thu = DTO("da_seal"); thu.quyen = KHONG_QUYEN(thu.quyen);
    await P.lamMoi(thu, "GET xem=false");
    const t = chupNho(P);
    chuan(tha(), "SETUP_BLOB_CHUA_DOC");
    tha()(taoBlob(d.pdf.byte_length)); await chay();
    khongDoiNho(P, t, "R2");
    await P.lamMoi(DTO("da_seal"), "GET quyền trở lại");
    const c0 = soClickTai;
    await P.bam(NUT_TAI);
    await P.tra(P.cho(P.get("/api/m4/duyet/" + I.v1 + "/pdf/" + I.pdf), "GET tải lại"), 200, null, d.pdf.byte_length);
    assert.strictEqual(soClickTai, c0 + 1, "tải dương không click đúng một lần");
  });

  // ================================================================ M — 2xx sai hợp đồng
  await ca("M1 2xx sai hợp đồng → Chưa rõ kết quả, không toast thành công, không đọc lại; Gửi lại cùng body", async () => {
    const P = await moPhien(), d = DTO("cho_duyet");
    await P.napModule(d);
    P.go(NT, "1");
    await P.bam(NUT_LUU);
    const p = P.cho(P.postDp("ket-luan"), "POST");
    const g0 = P.dem(P.laGetDp);
    await P.tra(p, 200, {ok: true});
    assert.ok(P.toast().includes("Chưa rõ kết quả lưu kết luận") && !P.toast().includes("Đã lưu kết luận"), "2xx sai hợp đồng bị coi là đã lưu");
    assert.strictEqual(P.dem(P.laGetDp), g0, "2xx sai hợp đồng vẫn đọc lại");
    await P.bam(NUT_LAI);
    assert.strictEqual(P.cho(P.postDp("ket-luan"), "POST gửi lại").opts.body, p.opts.body, "Gửi lại khác body");
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
