"use strict";
// M4-02C UI_FIX01 — hồi quy bất đồng bộ trên MÃ THẬT (app.js + m4/giao_dien/m4.js + m4/giao_dien/m4_duyet_pdf.js) cho ba lỗi nhân quả:
//  (1) đổi phiên bản mới nhất do máy chủ trả (V1→V2 và V1→V2→V1) = đổi view: ACK/lỗi/blob giữ của V1 về muộn → 0 GET/POST/tải/toast/trạng thái,
//      không thay ô nhập hiện hành, không nhả trạng thái bận; dương: ACK hiện hành toast + đọc lại, PDF đúng độ dài tải 1, sai độ dài 0.
//  (2) Gửi lại y nguyên của lệnh CHƯA RÕ cần quyền tường minh HIỆN HÀNH của đúng loại lệnh (duyet / ket_luan / tai_pdf): mất quyền → nút tắt + gọi
//      thẳng handler → 0 POST, bản ghi giữ nguyên; quyền trở lại (kể cả máy chủ đã ghi lần trước) → gửi lại đúng body chuỗi/khóa/File gốc.
//  (3) tải lười /m4/m4_duyet_pdf.js: sẵn sàng/lỗi về sau khi rời #m4 → 0 mount/GET/đổi trạng thái; quay lại #m4 mở bình thường; dương một lần tải.
// Khung DOM/fetch/DTO literal sao từ tests/m4_02c_async.cjs (tệp đó KHÔNG sửa). Mỗi ca chạy trong môi trường mới (khởi động shell thật riêng) nên mọi
// ca đều được thử, ca hỏng không kéo ca sau. Chờ = số vòng 0 ms cố định; timer dài của mã thật được unref. Không process.exit, không ghi tệp, không mạng.
// CODE_ONLY: WRITTEN_NOT_RUN — coder viết, CHƯA CHẠY. Root chạy: `node tests/m4_02c_fix01_async.cjs` (Node ≥ 18). process.exitCode = 0 khi mọi ca đạt,
// 1 khi có ca hỏng / setup_errors (mã SETUP_*: khung không tới được route/DOM — tách khỏi hỏng ngữ nghĩa) / unhandledRejection.
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

// ------------------------------------------------------------------ DOM giả có kết nối thật (sao nguyên khung m4_02c_async.cjs)
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
const nutTheoChu = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));
const theoNhan = (root, s) => tim(root, e => e.attrs && e.attrs["aria-label"] === s);

// ------------------------------------------------------------------ dữ liệu tổng hợp literal (UUID giả; không dữ liệu/credential thật)
const A1 = "MO_PHONG_DU_AN_A1", B1 = "MO_PHONG_DU_AN_B1";
const PN = "88888888-8888-4888-8888-888888888888";
// hai phiên bản có 12 ký tự đầu KHÁC nhau để tiêu đề phân biệt được V1/V2
const V1 = "1a1a1a1a-1a1a-4a1a-8a1a-1a1a1a1a1a1a", V2 = "2b2b2b2b-2b2b-4b2b-8b2b-2b2b2b2b2b2b";
const KL1 = "22222222-2222-4222-8222-222222222222", QD1 = "33333333-3333-4333-8333-333333333333";
const PDF1 = "44444444-4444-4444-8444-444444444444";
const RUN1 = "99999999-9999-4999-8999-999999999999";
let soRc = 0;
const RC = () => "77777777-7777-4777-8777-" + String(++soRc).padStart(12, "0");
const BASIS = rev => "c".repeat(63) + String(rev % 10);
const SCHEMA = "M4_DUYET_PDF_V1";

const DEMO = [{dang_nhap: A1, vai_tro: "DU_AN"}, {dang_nhap: B1, vai_tro: "DU_AN"}];
const TONG = login => ({cau_hinh: true, nguoi: {dang_nhap: login, vai_tro: "DU_AN"}, ghi_nguon: {san_sang: true, ly_do: null},
  pham_vi: [{du_an_id: "da1", vai: "PHU_TRACH", du_an: "Dự án A1", du_an_ma: "DA_XD_A1", phap_nhan: "PN_DEMO_A", soan: true, xem: true}],
  hop_dong: [{id: "hd-" + login, ten: "Gói " + login, so_hop_dong: "SO-" + login, du_an_id: "da1", du_an: "Dự án A1", phap_nhan: "PN_DEMO_A", revision: 3,
    trang_thai_pl: "CHUA_KHAI", co_tep: true, soan: true, so_dot: 2}],
  dot: [], danh_muc_ho_so: [], nhanh_sau: [], tai_len_toi_da_byte: 52428800, danh_tinh_demo: DEMO});
const TEP = (id, vai, ten) => ({id, vai_tro_tai_lieu: vai, ten_goc: ten, media_type: "x", byte_length: 10, raw_sha256: "a".repeat(64), tao_boi: "X", tao_luc: "2026-01-01T00:00:00Z"});
const CHI_TIET = login => ({ho_so: {hop_dong_id: "hd-" + login, du_an_id: "da1", phap_nhan_id: PN, ten: "Gói " + login, so_hop_dong: "SO-" + login, du_an: "Dự án A1",
  phap_nhan: "PN_DEMO_A", revision: 3, rev_tham_so: 2, tep_hop_dong_id: "tep-1", trang_thai_pl: "CHUA_KHAI", soan: true},
  tep: [TEP("tep-1", "HOP_DONG", "hd.docx")], trich_xuat: [], tham_so: [], xac_nhan: null, phu_luc: [], boq: [], boq_goc_dong: [],
  dot: [{id: "dot-1", so_dot: 1, ngay_nghiem_thu: "2026-03-01", trang_thai: "NHAP", revision: 2, nop_luc: null, revision_ho_so: 3, can_cu_doi_sau_nop: false},
    {id: "dot-2", so_dot: 2, ngay_nghiem_thu: "2026-04-01", trang_thai: "NHAP", revision: 1, nop_luc: null, revision_ho_so: 3, can_cu_doi_sau_nop: false}],
  danh_muc_sha256: "b".repeat(64), nhanh_sau: []});
const DOT_CT = (login, dotId) => ({dot: {id: dotId, hop_dong_id: "hd-" + login, du_an_id: "da1", so_dot: dotId === "dot-1" ? 1 : 2, ngay_nghiem_thu: "2026-03-01",
  trang_thai: "NHAP", revision: 2, revision_ho_so: 3, so_hop_dong: "SO-" + login, soan: true}, tep: [],
  checklist: [{ma: "A02", ten: "Biên bản nghiệm thu", bat_buoc_dot_dau: true, bat_buoc_dot_sau: true, ghi_chu: null, bat_buoc: true, tep: []}],
  thieu: [], du_can_cu: true, nop: null, hieu_luc: {ngay: "2026-03-01", phu_luc_ap_dung: [], so_hang_muc_hieu_luc: 0, so_hang_muc_bo: 0}, can_cu_doi_sau_nop: false, nhanh_sau: []});
const MAU = {mau: []};

const CTX = (dot, ver, rev, login = A1) => ({dot_id: dot, hop_dong_id: "hd-" + login, du_an_id: "da1", phap_nhan_id: PN, version_id: ver, revision: rev, basis_sha256: BASIS(rev)});
const KL_DA_LUU = (nt, tt, rev = 0) => ({id: KL1, revision: rev, gia_tri_nt: nt, so_xin_thanh_toan: tt, tam_ung: null, thu_hoi: null, giu_lai: "0", tien_te: "VND", ly_do: null,
  dong_nt: [{row_id: "R-01", khoi_luong_chap_nhan: "40"}, {row_id: "R-02", khoi_luong_chap_nhan: null}], xu_ly_phat_hien: [{finding_id: "F-01", ly_do: "đã giải trình"}]});
const QD = {id: QD1, actor: "MO_PHONG_DUYET", luc: "2026-10-22T09:00:00Z", ly_do: null};
const PDFX = {id: PDF1, version_id: V1, name: "ho_so_thanh_toan_dot_1.pdf", sha256: "4".repeat(64), byte_length: 9};
const PDF2X = {...PDFX, version_id: V2};
function DTO(o = {}) {
  const ver = o.ver || V1, rev = o.rev ?? 0, dot = o.dot || "dot-1";
  return {schema: SCHEMA, context: CTX(dot, ver, rev, o.login), quyen: {xem: true, ket_luan: false, duyet: false, tai_pdf: false, ...(o.quyen || {})},
    trang_thai: o.tt || "CHO_KET_LUAN",
    can_cu: [{loai: "BB_NT", ten: "bb_nghiem_thu_dot_" + dot + ".pdf", sha256: "1".repeat(64), byte_length: 120}],
    review_refs: [{cap: "L1", run_id: RUN1, trang_thai: "PARTIAL", ket_qua_sha256: "2".repeat(64), cong_bo: true}],
    coverage: {C01: {trang_thai: "INCOMPLETE", ly_do: "thiếu KL kỳ này"}},
    phat_hien: [{finding_id: "F-01", ma: "C01-01", muc: "CAO", noi_dung: "Khối lượng kỳ này thiếu", trang_thai: "MO"}],
    dong_nt: [{row_id: "R-01", ten: "Đào đất", don_vi: "m3", khoi_luong_de_nghi: "40", nguon: "BB NT dòng 2"},
      {row_id: "R-02", ten: "Bê tông móng", don_vi: "m3", khoi_luong_de_nghi: null, nguon: "BOQ dòng 3"}],
    ket_luan: o.kl || null, quyet_dinh: o.qd || null, pdf: o.pdf || null, seal: o.seal || null,
    kt: o.kt || {trang_thai: "CHUA_CHUYEN", pending_id: null}, request: o.rq || {trang_thai: "CHO_PDF"}, lich_su: o.ls || [], ...(o.them || {})};
}
function ACK(hanh, khoa, ctx, ids = {}) {
  return {schema: SCHEMA, hanh_dong: hanh, khoa, context: {...ctx}, receipt_id: RC(),
    ket_luan_id: null, quyet_dinh_id: null, pdf_id: null, seal_id: null, kt_pending_id: null, ...ids};
}

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

const NUT_LUU = "Lưu kết luận", NUT_DUYET = "Duyệt hồ sơ đợt (", NUT_TAI_LEN = "Tải PDF hồ sơ đợt lên", NUT_LAM_MOI = "↻ Làm mới", NUT_TAI = "Tải PDF ↓";
const NUT_LAI = "Gửi lại y nguyên (cùng khóa)", NUT_LAI_TEP = "Gửi lại tệp gốc y nguyên (cùng khóa)";
const NT = "Giá trị nghiệm thu chấp nhận (NT)";
const URL_TAI = ver => "/api/m4/duyet/" + ver + "/pdf/" + PDF1;
const tieuDe = ver => "Phiên bản hồ sơ đợt " + ver.slice(0, 12);
const SRC_DP = "/m4/m4_duyet_pdf.js";

// ------------------------------------------------------------------ một phiên shell thật mới: app.js + m4.js → vai A1 → HĐ → đợt 1 (chưa nạp module)
async function moPhien() {
  const {ctx, document, calls, wl} = moiTruong();
  const $ = id => document.getElementById(id);
  const conLai = pred => calls.filter(c => !c.xong && pred(c));
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const lay = (pred, ma) => { const c = calls.find(x => !x.xong && pred(x)); chuan(c, ma); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const get = url => c => c.method === "GET" && c.url === url;
  const post = url => c => c.method === "POST" && c.url === url;
  const getDp = dot => get("/api/m4/duyet?dot_id=" + dot);
  const laGetDp = c => c.method === "GET" && c.url.startsWith("/api/m4/duyet");
  const postDp = p => post("/api/m4/duyet/" + p);
  const laPostDp = c => c.method === "POST" && c.url.startsWith("/api/m4/duyet/");
  const URL_HD = login => "/api/m4/hop-dong/hd-" + login;

  try { vm.runInContext(APP, ctx, {filename: "app.js"}); } catch (e) { throw new SetupError("SETUP_APP_JS: " + e.message); }
  chuan(ctx.window.kttChung, "SETUP_SEAM_KTTCHUNG");
  const soHashTruoc = (wl.hashchange || []).length;
  try { vm.runInContext(M4, ctx, {filename: "m4.js"}); } catch (e) { throw new SetupError("SETUP_M4_JS: " + e.message); }
  const ngheHashM4 = (wl.hashchange || []).slice(soHashTruoc);  // chỉ listener hashchange do m4.js đăng ký (router app.js không mô phỏng)
  chuan(ngheHashM4.length > 0, "SETUP_HASHCHANGE_M4");
  for (const c of calls) if (c.url !== "/api/m4" && c.url !== "/api/m4/mau") { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND", message: "ngoài ca"})); }
  await chay();

  const tra = async (c, status, data, n) => { c.resolve(phanHoi(status, data, n)); await chay(); };
  async function traMau() { for (const c of conLai(get("/api/m4/mau"))) { c.xong = true; c.resolve(phanHoi(200, MAU)); } await chay(); }
  async function traTong(login) { lay(get("/api/m4"), "SETUP_ROUTE_GET_API_M4 " + login).resolve(phanHoi(200, TONG(login))); await chay(); await traMau(); }
  async function traHdDot(login) {  // GET HĐ (+ GET đợt nếu shell đọc) của lần nạp lại shell
    lay(get(URL_HD(login)), "SETUP_ROUTE_GET_HD " + login).resolve(phanHoi(200, CHI_TIET(login))); await chay();
    const gd = calls.find(c => !c.xong && get("/api/m4/dot/dot-1")(c));
    if (gd) { gd.xong = true; gd.resolve(phanHoi(200, DOT_CT(login, "dot-1"))); await chay(); }
  }
  async function moTab(ten) { const b = nutTheoChu($("m4-chi-tiet"), ten); chuan(b, "SETUP_DOM_TAB " + ten); b.click(); await chay(); }
  const roiM4 = async () => { ctx.location.hash = "#hopdong"; for (const fn of ngheHashM4) fn({}); await chay(); };
  const veM4 = async () => { ctx.location.hash = "#m4"; for (const fn of ngheHashM4) fn({}); await chay(); };
  const scripts = () => document.head.children.filter(c => c.tagName === "SCRIPT" && c.src === SRC_DP);
  const chayDp = async () => { try { vm.runInContext(DP, ctx, {filename: "m4_duyet_pdf.js"}); } catch (e) { throw new SetupError("SETUP_DP_JS: " + e.message); } await chay(); };

  const vungDp = () => tim($("m4-chi-tiet"), e => !!e._cls && e._cls.has("m4-dp"));
  const chuDp = () => (vungDp() || {textContent: ""}).textContent;
  const daMount = () => { const v = vungDp(); return !!(v && v.querySelector(".m4-dp-status")); };  // module đã vẽ vào vùng (có dòng trạng thái riêng)
  const statusDp = () => { const v = vungDp(), s = v && v.querySelector(".m4-dp-status"); return s ? s.textContent : ""; };
  const statusM4 = () => ($("m4-status") || {textContent: ""}).textContent;
  const nutDp = s => nutTheoChu(vungDp(), s);
  const oDp = nhan => theoNhan(vungDp(), nhan);
  const go = (nhan, v) => { const e = oDp(nhan); chuan(e && e.isConnected, "SETUP_DOM_O " + nhan); e.value = v; e.dispatch("input"); return e; };
  const bam = async s => { const b = nutDp(s); assert.ok(b, "không có nút " + s); b.click(); await chay(); return b; };
  const bamEp = async s => { const b = nutDp(s); assert.ok(b, "không có nút " + s); b.disabled = false; b.click(); await chay(); };  // gọi thẳng handler
  const toast = () => ($("toast") || {textContent: ""}).textContent;
  const chonTep = f => { const i = oDp("Tệp PDF hồ sơ đợt"); chuan(i, "SETUP_DOM_O_TEP_PDF"); i.files = [f]; i.dispatch("change"); };
  const giuBlob = c => { let tha = null; c.resolve({ok: true, status: 200, headers: {get: () => "application/pdf"}, json: async () => ({}),
    blob: () => new Promise(r => { tha = r; })}); return () => tha; };
  async function lamMoi(dto, moTa) { await bam(NUT_LAM_MOI); await tra(cho(getDp("dot-1"), moTa), 200, dto); }
  async function napModule(dto) {  // mở tab Duyệt lần đầu: tải lười tài sản THẬT, chạy module, GET đầu
    await moTab("Duyệt & PDF");
    chuan(scripts().length === 1, "SETUP_SCRIPT_DP_KHONG_TAI");
    await chayDp();
    chuan(ctx.window.kttM4DuyetPdf, "SETUP_DP_KHONG_CONG_BO");
    await tra(lay(getDp("dot-1"), "SETUP_ROUTE_GET_DUYET_DAU"), 200, dto);
    chuan(chuDp().includes("Căn cứ của phiên bản"), "SETUP_DTO_DAU_KHONG_HIEN");
  }

  // khởi động shell thật
  await traTong(A1);
  chuan($("m4-nguoi") && $("m4-nguoi").textContent.includes(A1), "SETUP_DOM_M4_NGUOI");
  const li = tim($("m4-ds-hd"), e => e.tagName === "LI" && e.textContent.includes("SO-" + A1));
  chuan(li, "SETUP_DOM_DS_HD"); li.dispatch("click"); await chay();
  lay(get(URL_HD(A1)), "SETUP_ROUTE_GET_HD").resolve(phanHoi(200, CHI_TIET(A1))); await chay();
  await moTab("Đợt & checklist");
  const tr = tim($("m4-chi-tiet"), e => e.tagName === "TR" && !!e.children[0] && e.children[0].tagName === "TD" && e.children[0].textContent === "1");
  const bMo = tr && tim(tr, e => e.tagName === "BUTTON" && e.textContent === "Mở");
  chuan(bMo && !bMo.disabled, "SETUP_DOM_MO_DOT_1");
  bMo.click(); await chay();
  await traHdDot(A1);
  chuan(nutTheoChu($("m4-chi-tiet"), "Duyệt & PDF"), "SETUP_DOM_TAB_DUYET_KHONG_CO");
  chuan(scripts().length === 0 && dem(laGetDp) === 0, "SETUP_DP_DA_NAP_TRUOC");

  return {ctx, calls, $, conLai, cho, lay, dem, get, getDp, laGetDp, postDp, laPostDp, tra, traTong, traHdDot, moTab, roiM4, veM4, scripts, chayDp,
    vungDp, chuDp, daMount, statusDp, statusM4, nutDp, oDp, go, bam, bamEp, toast, chonTep, giuBlob, lamMoi, napModule};
}

// ảnh chụp mọi hiệu ứng nhìn thấy/ra ngoài của view HIỆN HÀNH — so đúng bằng 0 sau khi phản hồi cũ về
function chup(P) {
  return {toast: P.toast(), status: P.statusDp(), statusM4: P.statusM4(), get: P.dem(P.laGetDp), post: P.dem(P.laPostDp), fetch: P.calls.length, click: soClickTai,
    o: P.oDp(NT), oVal: P.oDp(NT) && P.oDp(NT).value, luu: P.nutDp(NUT_LUU), luuTat: P.nutDp(NUT_LUU) && P.nutDp(NUT_LUU).disabled};
}
function khongDoi(P, t, ten) {
  assert.strictEqual(P.toast(), t.toast, ten + ": phản hồi cũ toast ở view hiện hành");
  assert.strictEqual(P.statusDp(), t.status, ten + ": phản hồi cũ đổi trạng thái module");
  assert.strictEqual(P.statusM4(), t.statusM4, ten + ": phản hồi cũ đổi trạng thái shell");
  assert.strictEqual(P.dem(P.laGetDp), t.get, ten + ": phản hồi cũ kích GET");
  assert.strictEqual(P.dem(P.laPostDp), t.post, ten + ": phản hồi cũ kích POST");
  assert.strictEqual(P.calls.length, t.fetch, ten + ": phản hồi cũ kích yêu cầu mạng");
  assert.strictEqual(soClickTai, t.click, ten + ": phản hồi cũ click tải");
  assert.strictEqual(P.oDp(NT), t.o, ten + ": phản hồi cũ thay ô nhập hiện hành (vẽ lại form)");
  assert.ok(t.o && t.o.isConnected && t.o.value === t.oVal, ten + ": nháp hiện hành bị đổi");
  assert.strictEqual(P.nutDp(NUT_LUU), t.luu, ten + ": phản hồi cũ vẽ lại nút lệnh");
  assert.strictEqual(t.luu && t.luu.disabled, t.luuTat, ten + ": phản hồi cũ đổi trạng thái bận của nút lệnh");
}

async function main() {
  const Q = {ket_luan: true};

  // ================================================================ (1) sở hữu view theo phiên bản máy chủ
  await ca("V0 dương: ACK hiện hành toast + đọc lại; PDF hiện hành đúng độ dài tải 1, sai độ dài 0", async () => {
    const P = await moPhien();
    await P.napModule(DTO({quyen: Q, pdf: PDFX}));
    P.go(NT, "5");
    await P.bam(NUT_LUU);
    const p = P.cho(P.postDp("ket-luan"), "POST hiện hành");
    const khoa = JSON.parse(p.opts.body).khoa, g0 = P.dem(P.laGetDp), t0 = P.toast();
    await P.tra(p, 200, ACK("KET_LUAN", khoa, CTX("dot-1", V1, 0), {ket_luan_id: KL1}));
    assert.ok(P.toast().includes("Đã lưu kết luận") && P.toast() !== t0, "ACK hiện hành không toast");
    assert.strictEqual(P.dem(P.laGetDp), g0 + 1, "ACK hiện hành không đọc lại đúng một lần");
    await P.tra(P.cho(P.getDp("dot-1"), "GET sau ACK"), 200, DTO({tt: "CHO_DUYET", kl: KL_DA_LUU("5", null), quyen: Q, pdf: PDFX}));
    assert.ok(P.chuDp().includes("Kết luận đã lưu: " + KL1.slice(0, 12)), "đọc lại sau ACK không hiện kết luận máy chủ");
    const c0 = soClickTai;
    await P.bam(NUT_TAI);
    await P.tra(P.cho(P.get(URL_TAI(V1)), "GET tải sai độ dài"), 200, null, 3);
    assert.strictEqual(soClickTai, c0, "sai độ dài mà vẫn click");
    assert.ok(P.statusDp().includes("khác độ dài"), "không báo sai độ dài");
    await P.bam(NUT_TAI);
    await P.tra(P.cho(P.get(URL_TAI(V1)), "GET tải đúng độ dài"), 200, null, 9);
    assert.strictEqual(soClickTai, c0 + 1, "PDF hiện hành đúng độ dài không tải đúng một lần");
  });

  await ca("V1 ACK V1 giữ → mới nhất V2 → ACK cũ về: 0 hiệu ứng; V2 vẫn lưu được", async () => {
    const P = await moPhien();
    await P.napModule(DTO({quyen: Q}));
    P.go(NT, "6");
    await P.bam(NUT_LUU);
    const p1 = P.cho(P.postDp("ket-luan"), "POST V1 giữ");
    const khoa1 = JSON.parse(p1.opts.body).khoa;
    await P.lamMoi(DTO({ver: V2, rev: 3, quyen: Q}), "GET mới nhất V2");
    assert.ok(P.chuDp().includes(tieuDe(V2)), "GET mới nhất V2 hợp lệ không hiện V2");
    P.go(NT, "77");
    const t = chup(P);
    assert.ok(t.luu && !t.luuTat, "V2: lệnh V1 đang bay chặn nhầm lệnh của V2");
    await P.tra(p1, 200, ACK("KET_LUAN", khoa1, CTX("dot-1", V1, 0), {ket_luan_id: KL1}));
    khongDoi(P, t, "ACK V1 sau V2");
    assert.ok(P.chuDp().includes(tieuDe(V2)), "ACK V1 làm mất view V2");
    // dương sau: lệnh của view hiện hành V2 vẫn đi đúng phiên bản/basis và hoàn tất bình thường
    await P.bam(NUT_LUU);
    const p2 = P.cho(P.postDp("ket-luan"), "POST V2");
    const b2 = JSON.parse(p2.opts.body);
    assert.deepStrictEqual([b2.version_id, b2.revision, b2.expected_basis, b2.gia_tri_nt], [V2, 3, BASIS(3), "77"], "lệnh V2 sai phiên bản/basis/nháp");
    assert.notStrictEqual(b2.khoa, khoa1, "lệnh V2 dùng lại khóa V1");
    const g = P.dem(P.laGetDp);
    await P.tra(p2, 200, ACK("KET_LUAN", b2.khoa, CTX("dot-1", V2, 3), {ket_luan_id: KL1}));
    assert.ok(P.toast().includes("Đã lưu kết luận"), "ACK hiện hành V2 không toast");
    assert.strictEqual(P.dem(P.laGetDp), g + 1, "ACK hiện hành V2 không đọc lại");
  });

  await ca("V2 ACK V1 giữ → V2 → V1 (ABA) → ACK cũ về: 0 hiệu ứng, không nhả bận; làm mới tường minh trở lại bình thường", async () => {
    const P = await moPhien();
    await P.napModule(DTO({quyen: Q}));
    P.go(NT, "6");
    await P.bam(NUT_LUU);
    const p1 = P.cho(P.postDp("ket-luan"), "POST V1 giữ");
    const khoa1 = JSON.parse(p1.opts.body).khoa;
    await P.lamMoi(DTO({ver: V2, rev: 3, quyen: Q}), "GET mới nhất V2");
    assert.ok(P.chuDp().includes(tieuDe(V2)), "không hiện V2");
    await P.lamMoi(DTO({quyen: Q}), "GET mới nhất trở lại V1");
    assert.ok(P.chuDp().includes(tieuDe(V1)), "không hiện V1 sau ABA");
    P.go(NT, "88");
    const t = chup(P);
    assert.ok(t.luu && t.luuTat === true, "V1 sau ABA: lệnh V1 còn bay mà Lưu không bị chặn");
    await P.tra(p1, 200, ACK("KET_LUAN", khoa1, CTX("dot-1", V1, 0), {ket_luan_id: KL1}));
    khongDoi(P, t, "ACK V1 sau V1→V2→V1");
    // dương sau: làm mới tường minh của view hiện hành → lệnh đã rõ không còn chặn, nháp giữ, lệnh mới khóa mới
    await P.lamMoi(DTO({quyen: Q}), "GET làm mới tường minh");
    assert.strictEqual(P.oDp(NT).value, "88", "làm mới làm mất nháp hiện hành");
    assert.ok(P.nutDp(NUT_LUU) && !P.nutDp(NUT_LUU).disabled, "sau làm mới Lưu vẫn bị chặn");
    await P.bam(NUT_LUU);
    const p2 = P.cho(P.postDp("ket-luan"), "POST mới sau ABA");
    const b2 = JSON.parse(p2.opts.body);
    assert.strictEqual(b2.gia_tri_nt, "88"); assert.notStrictEqual(b2.khoa, khoa1, "lệnh mới dùng lại khóa cũ");
    await P.tra(p2, 200, ACK("KET_LUAN", b2.khoa, CTX("dot-1", V1, 0), {ket_luan_id: KL1}));
    assert.ok(P.toast().includes("Đã lưu kết luận"), "ACK hiện hành sau ABA không toast");
  });

  await ca("V3 blob V1 giữ → mới nhất V2 → blob đúng độ dài về: 0 click/hiệu ứng; tải PDF của V2 vẫn được", async () => {
    const P = await moPhien();
    await P.napModule(DTO({quyen: Q, pdf: PDFX}));
    await P.bam(NUT_TAI);
    const thaBlob = P.giuBlob(P.cho(P.get(URL_TAI(V1)), "GET tải V1"));
    await chay();
    chuan(typeof thaBlob() === "function", "SETUP_BLOB_GIU");
    await P.lamMoi(DTO({ver: V2, rev: 2, quyen: Q}), "GET mới nhất V2");
    assert.ok(P.chuDp().includes(tieuDe(V2)), "không hiện V2");
    P.go(NT, "55");
    const t = chup(P);
    thaBlob()(taoBlob(9)); await chay();
    khongDoi(P, t, "blob V1 sau V2");
    await P.lamMoi(DTO({ver: V2, rev: 2, quyen: Q, pdf: PDF2X}), "GET V2 có PDF");
    const c0 = soClickTai;
    await P.bam(NUT_TAI);
    await P.tra(P.cho(P.get(URL_TAI(V2)), "GET tải V2"), 200, null, 9);
    assert.strictEqual(soClickTai, c0 + 1, "PDF của view hiện hành V2 không tải được");
  });

  await ca("V4 blob V1 giữ → V2 → V1 (ABA) → blob đúng độ dài về: 0 click/hiệu ứng; tải lại V1 hiện hành được", async () => {
    const P = await moPhien();
    await P.napModule(DTO({quyen: Q, pdf: PDFX}));
    await P.bam(NUT_TAI);
    const thaBlob = P.giuBlob(P.cho(P.get(URL_TAI(V1)), "GET tải V1"));
    await chay();
    chuan(typeof thaBlob() === "function", "SETUP_BLOB_GIU");
    await P.lamMoi(DTO({ver: V2, rev: 2, quyen: Q}), "GET mới nhất V2");
    await P.lamMoi(DTO({quyen: Q, pdf: PDFX}), "GET mới nhất trở lại V1");
    assert.ok(P.chuDp().includes(tieuDe(V1)) && P.nutDp(NUT_TAI), "không hiện V1 có PDF sau ABA");
    P.go(NT, "56");
    const t = chup(P);
    thaBlob()(taoBlob(9)); await chay();
    khongDoi(P, t, "blob V1 sau V1→V2→V1");
    await P.bam(NUT_TAI);
    await P.tra(P.cho(P.get(URL_TAI(V1)), "GET tải V1 hiện hành"), 200, null, 9);
    assert.strictEqual(soClickTai, t.click + 1, "PDF V1 của view hiện hành không tải được");
  });

  await ca("V5 lỗi 409 của V1 về sau V2: 0 GET/toast/trạng thái; 409 hiện hành V2 đọc lại một lần + giữ nháp", async () => {
    const P = await moPhien();
    await P.napModule(DTO({quyen: Q}));
    P.go(NT, "6");
    await P.bam(NUT_LUU);
    const p1 = P.cho(P.postDp("ket-luan"), "POST V1 giữ");
    await P.lamMoi(DTO({ver: V2, rev: 3, quyen: Q}), "GET mới nhất V2");
    P.go(NT, "66");
    const t = chup(P);
    await P.tra(p1, 409, {error: "M4_REVISION_CU", message: "Hồ sơ đã đổi"});
    khongDoi(P, t, "409 V1 sau V2");
    await P.bam(NUT_LUU);
    const p2 = P.cho(P.postDp("ket-luan"), "POST V2");
    const g = P.dem(P.laGetDp);
    await P.tra(p2, 409, {error: "M4_REVISION_CU", message: "Hồ sơ đã đổi"});
    assert.strictEqual(P.dem(P.laGetDp), g + 1, "409 hiện hành không đọc lại đúng một lần");
    await P.tra(P.cho(P.getDp("dot-1"), "GET sau 409 hiện hành"), 200, DTO({ver: V2, rev: 4, quyen: Q}));
    assert.strictEqual(P.oDp(NT).value, "66", "409 hiện hành làm mất nháp");
    assert.ok(P.chuDp().includes("· revision 4"), "409 hiện hành không hiện revision mới");
  });

  // ================================================================ (2) Gửi lại y nguyên cần quyền hiện hành của đúng loại lệnh
  const KL = KL_DA_LUU("1000", "900");
  await ca("R1 duyệt CHƯA RÕ → xem:true/duyet:false → Gửi lại 0 POST (nút + handler); quyền trở lại (đã ghi) → đúng body/khóa gốc", async () => {
    const P = await moPhien(), QD_ = {ket_luan: true, duyet: true, tai_pdf: true};
    await P.napModule(DTO({tt: "CHO_DUYET", kl: KL, quyen: QD_}));
    await P.bam(NUT_DUYET);
    const p = P.cho(P.postDp("chap-thuan"), "POST duyệt gốc");
    const goc = p.opts.body, khoa = JSON.parse(goc).khoa;
    p.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(P.nutDp(NUT_LAI) && !P.nutDp(NUT_LAI).disabled && P.statusDp().includes("Chưa rõ kết quả"), "mất kết nối không thành CHƯA RÕ có Gửi lại");
    const n0 = P.dem(P.postDp("chap-thuan"));
    await P.lamMoi(DTO({tt: "CHO_DUYET", kl: KL, quyen: {ket_luan: true, duyet: false, tai_pdf: true}}), "GET mất quyền duyệt");
    assert.strictEqual(P.nutDp(NUT_DUYET), null, "mất quyền duyệt mà còn nút Duyệt mới");
    const lai = P.nutDp(NUT_LAI);
    assert.ok(lai, "bản ghi CHƯA RÕ bị bỏ khi mất quyền (phải giữ)");
    assert.strictEqual(lai.disabled, true, "mất quyền duyệt mà nút Gửi lại vẫn bật");
    lai.click(); await chay();
    assert.strictEqual(P.dem(P.postDp("chap-thuan")), n0, "nút Gửi lại tắt mà vẫn POST");
    await P.bamEp(NUT_LAI);
    assert.strictEqual(P.dem(P.postDp("chap-thuan")), n0, "gọi thẳng handler Gửi lại khi mất quyền vẫn POST");
    assert.ok(P.statusDp().includes("chưa gửi lại"), "không báo lệnh chưa rõ được giữ, chưa gửi lại: " + P.statusDp());
    await P.lamMoi(DTO({tt: "CHO_PDF", kl: KL, qd: QD, quyen: QD_}), "GET quyền trở lại, máy chủ đã ghi quyết định");
    const lai2 = P.nutDp(NUT_LAI);
    assert.ok(lai2 && !lai2.disabled, "quyền trở lại mà Gửi lại vẫn tắt (tự chặn đối soát)");
    await P.bam(NUT_LAI);
    const p2 = P.cho(P.postDp("chap-thuan"), "POST Gửi lại sau khi quyền trở lại");
    assert.strictEqual(p2.opts.body, goc, "Gửi lại khác chuỗi body/khóa gốc");
    assert.strictEqual(P.dem(P.postDp("chap-thuan")), n0 + 1);
    await P.tra(p2, 200, ACK("CHAP_THUAN", khoa, CTX("dot-1", V1, 0), {ket_luan_id: KL1, quyet_dinh_id: QD1, lap_lai: true}));
    assert.ok(P.toast().includes("Chờ PDF"), "ACK đối soát không báo kết quả: " + P.toast());
    assert.strictEqual(P.nutDp(NUT_LAI), null, "đã rõ mà còn nút Gửi lại");
  });

  await ca("R2 kết luận CHƯA RÕ → ket_luan:false → 0 POST (nút + handler + lệnh mới); quyền trở lại (đã lưu) → đúng body gốc", async () => {
    const P = await moPhien();
    await P.napModule(DTO({quyen: Q}));
    P.go(NT, "12");
    await P.bam(NUT_LUU);
    const p = P.cho(P.postDp("ket-luan"), "POST kết luận gốc");
    const goc = p.opts.body, khoa = JSON.parse(goc).khoa;
    await P.tra(p, 503, {error: "M4_KET_QUA_CHUA_RO", message: "chưa rõ"});
    assert.ok(P.nutDp(NUT_LAI) && !P.nutDp(NUT_LAI).disabled, "503 chưa rõ không có Gửi lại bật");
    const n0 = P.dem(P.postDp("ket-luan"));
    await P.lamMoi(DTO({quyen: {ket_luan: false}}), "GET mất quyền kết luận");
    const lai = P.nutDp(NUT_LAI);
    assert.ok(lai && lai.disabled === true, "mất quyền kết luận mà Gửi lại vẫn bật / bản ghi bị bỏ");
    lai.click(); await chay();
    await P.bamEp(NUT_LAI);
    await P.bamEp(NUT_LUU);
    assert.strictEqual(P.dem(P.postDp("ket-luan")), n0, "mất quyền kết luận mà vẫn POST");
    await P.lamMoi(DTO({tt: "CHO_DUYET", kl: KL_DA_LUU("12", null), quyen: Q}), "GET quyền trở lại, máy chủ đã lưu");
    const lai2 = P.nutDp(NUT_LAI);
    assert.ok(lai2 && !lai2.disabled, "quyền trở lại mà Gửi lại vẫn tắt");
    await P.bam(NUT_LAI);
    const p2 = P.cho(P.postDp("ket-luan"), "POST Gửi lại kết luận");
    assert.strictEqual(p2.opts.body, goc, "Gửi lại khác chuỗi body/khóa gốc");
    await P.tra(p2, 200, ACK("KET_LUAN", khoa, CTX("dot-1", V1, 0), {ket_luan_id: KL1, lap_lai: true}));
    assert.ok(P.toast().includes("Đã lưu kết luận"), "ACK đối soát kết luận không toast");
  });

  await ca("R3 PDF CHƯA RÕ → tai_pdf:false → 0 POST (nút + handler); quyền trở lại (PDF đã lưu) → đúng File gốc + X-M4-Info", async () => {
    const P = await moPhien(), QP = {tai_pdf: true}, FILE = P.ctx.File;
    await P.napModule(DTO({quyen: QP}));
    const fX = new FILE([new Uint8Array([37, 80, 68, 70, 45, 49, 46, 55, 10])], "ho_so_thanh_toan_dot_1.pdf", {type: "application/pdf"});
    P.chonTep(fX);
    await P.bam(NUT_TAI_LEN);
    const t = P.cho(P.postDp("pdf"), "POST PDF gốc");
    const infoX = t.opts.headers["X-M4-Info"], khoa = JSON.parse(decodeURIComponent(infoX)).khoa;
    t.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(P.nutDp(NUT_LAI_TEP) && !P.nutDp(NUT_LAI_TEP).disabled, "PDF chưa rõ không có Gửi lại tệp gốc bật");
    const n0 = P.dem(P.postDp("pdf"));
    await P.lamMoi(DTO({quyen: {tai_pdf: false}}), "GET mất quyền PDF");
    assert.strictEqual(P.nutDp(NUT_TAI_LEN), null, "mất quyền PDF mà còn nút tải lên mới");
    const lai = P.nutDp(NUT_LAI_TEP);
    assert.ok(lai && lai.disabled === true, "mất quyền PDF mà Gửi lại tệp vẫn bật / bản ghi bị bỏ");
    lai.click(); await chay();
    await P.bamEp(NUT_LAI_TEP);
    assert.strictEqual(P.dem(P.postDp("pdf")), n0, "mất quyền PDF mà vẫn POST");
    await P.lamMoi(DTO({quyen: QP, pdf: PDFX}), "GET quyền trở lại, PDF đã lưu");
    const lai2 = P.nutDp(NUT_LAI_TEP);
    assert.ok(lai2 && !lai2.disabled, "quyền trở lại mà Gửi lại tệp vẫn tắt");
    await P.bam(NUT_LAI_TEP);
    const t2 = P.cho(P.postDp("pdf"), "POST Gửi lại tệp gốc");
    assert.strictEqual(t2.opts.body, fX, "Gửi lại không dùng đúng đối tượng File gốc");
    assert.strictEqual(t2.opts.headers["X-M4-Info"], infoX, "Gửi lại đổi X-M4-Info/khóa");
    await P.tra(t2, 200, ACK("PDF", khoa, CTX("dot-1", V1, 0), {pdf_id: PDF1, lap_lai: true}));
    assert.ok(P.toast().includes("Đã lưu PDF hồ sơ đợt"), "ACK đối soát PDF không toast");
  });

  // ================================================================ (3) tải lười không hồi sinh module đã rời
  await ca("L1 dương: sẵn sàng hiện hành mount + đúng 1 GET; mở lại tab GET mới, không tải tài sản lần hai", async () => {
    const P = await moPhien();
    await P.moTab("Duyệt & PDF");
    assert.strictEqual(P.scripts().length, 1, "mở tab Duyệt không tải tài sản đúng một lần");
    assert.strictEqual(P.dem(P.laGetDp), 0, "chưa có module mà đã GET");
    await P.chayDp();
    assert.ok(P.daMount(), "sẵn sàng hiện hành không mount module");
    assert.strictEqual(P.conLai(P.getDp("dot-1")).length, 1, "sẵn sàng hiện hành không GET đúng một lần");
    await P.tra(P.cho(P.getDp("dot-1"), "GET đầu"), 200, DTO({quyen: Q}));
    assert.ok(P.chuDp().includes("Căn cứ của phiên bản"));
    await P.moTab("Đợt & checklist");
    assert.strictEqual(P.vungDp(), null);
    await P.moTab("Duyệt & PDF");
    assert.strictEqual(P.conLai(P.getDp("dot-1")).length, 1, "mở lại tab không GET đúng một lần");
    assert.strictEqual(P.scripts().length, 1, "mở lại tab tải tài sản lần hai");
  });

  await ca("L2 tài sản đang tải → rời #m4 → sẵn sàng muộn: 0 mount/GET/trạng thái; quay lại #m4 mở bình thường", async () => {
    const P = await moPhien();
    await P.moTab("Duyệt & PDF");
    assert.strictEqual(P.scripts().length, 1, "không tải tài sản");
    await P.roiM4();
    const vung = P.vungDp(), s0 = P.statusM4(), f0 = P.calls.length;
    chuan(vung && vung.textContent.includes("Đang tải màn Duyệt & PDF"), "SETUP_VUNG_DANG_TAI");
    await P.chayDp();
    chuan(P.ctx.window.kttM4DuyetPdf, "SETUP_DP_KHONG_CONG_BO");
    assert.strictEqual(P.dem(P.laGetDp), 0, "sẵn sàng muộn sau khi rời #m4 vẫn GET");
    assert.strictEqual(P.calls.length, f0, "sẵn sàng muộn sau khi rời #m4 kích yêu cầu mạng");
    assert.strictEqual(P.vungDp(), vung, "sẵn sàng muộn vẽ lại khung HĐ khi đã rời #m4");
    assert.strictEqual(P.daMount(), false, "sẵn sàng muộn mount module vào trang đã rời");
    assert.strictEqual(P.statusM4(), s0, "sẵn sàng muộn đổi trạng thái shell");
    // quay lại hợp lệ
    await P.veM4();
    await P.traTong(A1);
    await P.traHdDot(A1);
    assert.ok(P.daMount(), "quay lại #m4 không mount module");
    assert.strictEqual(P.conLai(P.getDp("dot-1")).length, 1, "quay lại #m4 không GET đúng một lần");
    assert.strictEqual(P.scripts().length, 1, "quay lại #m4 tải tài sản lần hai");
    await P.tra(P.cho(P.getDp("dot-1"), "GET sau quay lại"), 200, DTO({quyen: Q}));
    assert.ok(P.chuDp().includes("Căn cứ của phiên bản"), "quay lại #m4 không hiện hồ sơ");
  });

  await ca("L3 tài sản đang tải → rời #m4 → lỗi tải muộn: 0 trạng thái/thông báo; quay lại tải lại; lỗi hiện hành báo chưa nối; mở lại tab nạp được", async () => {
    const P = await moPhien();
    await P.moTab("Duyệt & PDF");
    const s1 = P.scripts()[0];
    chuan(s1 && typeof s1.onerror === "function", "SETUP_SCRIPT_ONERROR");
    await P.roiM4();
    const vung = P.vungDp(), s0 = P.statusM4(), f0 = P.calls.length;
    s1.onerror(); await chay();
    assert.strictEqual(P.statusM4(), s0, "lỗi tải muộn sau khi rời #m4 đổi trạng thái shell");
    assert.ok(P.vungDp() === vung && !vung.textContent.includes("Chưa nối backend"), "lỗi tải muộn sau khi rời #m4 đổi vùng");
    assert.strictEqual(P.calls.length, f0, "lỗi tải muộn kích yêu cầu mạng");
    await P.veM4();
    await P.traTong(A1);
    await P.traHdDot(A1);
    assert.strictEqual(P.scripts().length, 2, "quay lại hợp lệ sau lỗi không tải lại tài sản (kẹt Đang tải)");
    assert.strictEqual(P.dem(P.laGetDp), 0);
    P.scripts()[1].onerror(); await chay();  // dương: lỗi khi đang ở đúng view → nói thật
    assert.ok(P.chuDp().includes("Chưa nối backend duyệt/PDF"), "lỗi tải hiện hành không báo chưa nối");
    assert.ok(P.statusM4().includes("Không tải được màn Duyệt & PDF"), "lỗi tải hiện hành không đặt trạng thái");
    await P.moTab("Đợt & checklist");
    await P.moTab("Duyệt & PDF");
    assert.strictEqual(P.scripts().length, 3, "mở lại tab sau lỗi không tải lại");
    await P.chayDp();
    assert.ok(P.daMount(), "sẵn sàng hiện hành sau lỗi không mount");
    assert.strictEqual(P.conLai(P.getDp("dot-1")).length, 1, "sẵn sàng hiện hành sau lỗi không GET đúng một lần");
  });
}

main().catch(e => {
  if (e instanceof SetupError) KQ.setup_errors.push({ca: "main", ma: e.message});
  else KQ.hong.push({ca: "main", loi: String((e && e.stack) || e)});
}).finally(async () => {
  await chay(3);
  if (loiNgoai.length) KQ.hong.push({ca: "unhandledRejection", loi: loiNgoai.map(e => String((e && e.stack) || e)).join("\n")});
  const SO_CA = 12;  // V0–V5, R1–R3, L1–L3
  const dat = !KQ.hong.length && !KQ.setup_errors.length && KQ.dat.length === SO_CA;
  console.log(JSON.stringify({ket_qua: dat ? "DAT" : "HONG", dat: KQ.dat.length, ca: SO_CA, hong: KQ.hong, setup_errors: KQ.setup_errors}, null, 2));
  process.exitCode = dat ? 0 : 1;
});
