"use strict";
// M4-02C — kiểm bất đồng bộ trên MÃ THẬT: app.js (cổng kttChung + barrier đổi vai thật) + m4/giao_dien/m4.js (cầu nối tab "Duyệt & PDF", tải lười
// /m4/m4_duyet_pdf.js, teardown) + m4/giao_dien/m4_duyet_pdf.js (module mới). Không tái hiện máy trạng thái: mọi hành vi đi qua DOM giả + fetch giả
// do ca điều khiển (pending, đảo thứ tự, lỗi, JSON đứt, blob giữ lại) với DTO tổng hợp literal (UUID giả, không dữ liệu thật).
// CODE_ONLY: WRITTEN_NOT_RUN — coder viết, CHƯA CHẠY. Root chạy: `node tests/m4_02c_async.cjs` (Node ≥ 18). process.exitCode = 0 khi mọi ca đạt,
// 1 khi có ca hỏng / setup_errors / unhandledRejection. Không process.exit, không ghi/xóa tệp, không mạng, không tiến trình con.
// Timer dài của mã thật (toast 4.5–9 s, revoke object URL 60 s) được unref để tiến trình kết thúc tự nhiên; mọi chờ trong ca là số vòng 0 ms cố định.
// setup_errors (mã riêng SETUP_*) = khung không tới được route/DOM của shell (khác với ca hỏng do hành vi). Ca hỏng đầu tiên dừng chuỗi; ca sau ghi
// CHUA_CHAY (không xóa ca, không nới khẳng định). Ca:
//  D0  tài sản /m4/m4_duyet_pdf.js lỗi tải → "Chưa nối backend duyệt/PDF", 0 GET; nạp module → GET đúng dot_id.
//  D1  GET 404 / 2xx không schema → "Chưa nối backend", không lệnh; POST ket-luan 404 → chỉ lệnh đó tắt, nháp giữ, không Gửi lại, không toast thành công.
//  D2  REVIEW-only (ket_luan, không duyet) không có nút Duyệt; quyền thiếu/không boolean → sai hợp đồng; DUYET riêng có nút Duyệt; DUYET không ket_luan → Lưu tắt.
//  D3  lưu kết luận đúng body (chỉ trường hợp đồng; trống = null ≠ "0"; NT ≠ TT; số sai định dạng 0 POST) → duyệt không PDF → CHO_PDF hai nhánh chờ →
//      PDF bytes gốc + X-M4-Info đúng → seal/KT Chờ xác nhận/Request chỉ readiness, từ DTO máy chủ; không nút AP/Request; DTO KT không seal → sai hợp đồng.
//  D4  2xx sai khóa / JSON đứt / sai context / thiếu receipt / mất kết nối / 503 → CHƯA RÕ: không toast thành công, 0 GET, Lưu 0 POST; Gửi lại = cùng chuỗi body/khóa.
//  D5  X đang bay + sửa form Y → 0 POST; X chưa rõ → Gửi lại body X; ACK giữ nháp Y; Y gửi khóa mới. File X đang bay + chọn File Y cùng metadata → 0 POST;
//      Gửi lại = đúng đối tượng File X + header gốc; sau đó Y gửi khóa mới; 400 xác định không thành CHƯA RÕ.
//  D6  cùng actor A(đợt 1)→B(đợt 2)→A: B không thấy ý định A; A mới chặn lệnh mới khi X còn bay; ACK cũ không toast/GET/không đè nháp; LỖI 403 cũ không gỡ A mới.
//  D7  GET đảo thứ tự; GET về khi đang gõ không đè nháp; GET về sau khi rời tab không vẽ, mở lại GET mới.
//  D8  409/403 hiện hành vs cũ: 409 hiện hành đọc lại, giữ nháp, lần sau revision mới; 409 cũ 0 GET; 403 hiện hành gỡ bằng chứng/lệnh/tải.
//  D9  đổi vai (barrier thật) khi POST + GET đang bay → module gỡ đồng bộ, phản hồi cũ không toast/GET; về vai cũ không đợt → không GET.
//  D10 tải PDF: dương click đúng 1; độ dài khác → 0 click; header về rồi blob giữ + hashchange rời #m4 → 0 click, 0 GET.
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

// ------------------------------------------------------------------ DOM giả có kết nối thật (khung m4_01c_async.cjs / m4_02b_async.cjs)
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

const JSON_DUT = Symbol("json-dut");
function phanHoi(status, data, blobSize) {
  return {ok: status >= 200 && status < 300, status, headers: {get: () => "application/json"},
    json: async () => { if (data === JSON_DUT) throw new SyntaxError("Unexpected end of JSON input"); return data; },
    blob: async () => (BLOB_GOC ? new BLOB_GOC([new Uint8Array(blobSize ?? 0)], {type: "application/octet-stream"}) : {size: blobSize ?? 0, type: "application/octet-stream"})};
}
const taoBlob = n => (BLOB_GOC ? new BLOB_GOC([new Uint8Array(n)], {type: "application/pdf"}) : {size: n, type: "application/pdf"});
const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 10) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (!root) return null; if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
function timHet(root, pred, out = []) { if (!root) return out; if (pred(root)) out.push(root); for (const c of root.children || []) timHet(c, pred, out); return out; }
const nutTheoChu = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));
const theoNhan = (root, s) => tim(root, e => e.attrs && e.attrs["aria-label"] === s);

// ------------------------------------------------------------------ dữ liệu tổng hợp literal (UUID giả; không dữ liệu/credential thật)
const A1 = "MO_PHONG_DU_AN_A1", B1 = "MO_PHONG_DU_AN_B1";
const PN = "88888888-8888-4888-8888-888888888888";
const V1 = "11111111-1111-4111-8111-111111111111", V2 = "11111111-1111-4111-8111-222222222222";
const KL1 = "22222222-2222-4222-8222-222222222222", QD1 = "33333333-3333-4333-8333-333333333333";
const PDF1 = "44444444-4444-4444-8444-444444444444", SEAL1 = "55555555-5555-4555-8555-555555555555", KTP1 = "66666666-6666-4666-8666-666666666666";
const RUN1 = "99999999-9999-4999-8999-999999999999";
let soRc = 0;
const RC = () => "77777777-7777-4777-8777-" + String(++soRc).padStart(12, "0");
const BASIS = rev => "c".repeat(63) + String(rev % 10);
const SCHEMA = "M4_DUYET_PDF_V1";
const TRUONG_KET_LUAN = ["dot_id", "version_id", "revision", "expected_basis", "gia_tri_nt", "so_xin_thanh_toan", "tam_ung", "thu_hoi", "giu_lai", "tien_te",
  "dong_nt", "xu_ly_phat_hien", "ly_do", "khoa"].sort();
const TRUONG_CHAP_THUAN = ["dot_id", "version_id", "revision", "expected_basis", "ket_luan_id", "ly_do", "khoa"].sort();
const TRUONG_PDF = ["dot_id", "version_id", "revision", "expected_basis", "ten", "media_type", "khoa"].sort();

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
const SEALX = {id: SEAL1, version_id: V1, pdf_id: PDF1};
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
// ACK tổng hợp: echo khóa + ngữ cảnh của body đã gửi; ID tường minh UUID|null
function ACK(hanh, khoa, ctx, ids = {}) {
  return {schema: SCHEMA, hanh_dong: hanh, khoa, context: {...ctx}, receipt_id: RC(),
    ket_luan_id: null, quyet_dinh_id: null, pdf_id: null, seal_id: null, kt_pending_id: null, ...ids};
}

class SetupError extends Error {}
const chuan = (dk, ma) => { if (!dk) throw new SetupError(ma); };
const KQ = {dat: [], hong: [], setup_errors: [], chua_chay: []};
let dung = false;
async function ca(ten, fn) {
  if (dung) { KQ.chua_chay.push(ten); return; }
  try { await fn(); KQ.dat.push(ten); console.log("ĐẠT  " + ten); }
  catch (e) {
    dung = true;
    if (e instanceof SetupError) { KQ.setup_errors.push({ca: ten, ma: e.message}); console.log("SETUP " + ten + ": " + e.message); }
    else { KQ.hong.push({ca: ten, loi: String((e && e.stack) || e)}); console.log("HỎNG " + ten + ": " + (e && e.message)); }
  }
}

async function main() {
  const {ctx, document, calls, wl} = moiTruong();
  const $ = id => document.getElementById(id);
  const conLai = pred => calls.filter(c => !c.xong && pred(c));
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const lay = (pred, ma) => { const c = calls.find(x => !x.xong && pred(x)); chuan(c, ma); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const get = url => c => c.method === "GET" && c.url === url;
  const post = url => c => c.method === "POST" && c.url === url;
  const URL_DP = dot => "/api/m4/duyet?dot_id=" + dot;
  const getDp = dot => get(URL_DP(dot));
  const laGetDp = c => c.method === "GET" && c.url.startsWith("/api/m4/duyet");
  const postDp = p => post("/api/m4/duyet/" + p);
  const laPostDp = c => c.method === "POST" && c.url.startsWith("/api/m4/duyet/");
  const URL_HD = login => "/api/m4/hop-dong/hd-" + login;

  try { vm.runInContext(APP, ctx, {filename: "app.js"}); } catch (e) { KQ.setup_errors.push({ca: "boot", ma: "SETUP_APP_JS: " + e.message}); return; }
  chuan(ctx.window.kttChung, "SETUP_SEAM_KTTCHUNG");
  const soHashTruoc = (wl.hashchange || []).length;
  try { vm.runInContext(M4, ctx, {filename: "m4.js"}); } catch (e) { KQ.setup_errors.push({ca: "boot", ma: "SETUP_M4_JS: " + e.message}); return; }
  const ngheHashM4 = (wl.hashchange || []).slice(soHashTruoc);  // chỉ listener hashchange do m4.js đăng ký (router app.js không mô phỏng)
  for (const c of calls) if (c.url !== "/api/m4" && c.url !== "/api/m4/mau") { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND", message: "ngoài ca"})); }
  await chay();

  async function traMau() { for (const c of conLai(get("/api/m4/mau"))) { c.xong = true; c.resolve(phanHoi(200, MAU)); } await chay(); }
  async function traTong(login) { lay(get("/api/m4"), "SETUP_ROUTE_GET_API_M4 " + login).resolve(phanHoi(200, TONG(login))); await chay(); await traMau(); }
  async function moHdList(login) {
    const li = tim($("m4-ds-hd"), e => e.tagName === "LI" && e.textContent.includes("SO-" + login));
    chuan(li, "SETUP_DOM_DS_HD " + login); li.dispatch("click"); await chay();
    lay(get(URL_HD(login)), "SETUP_ROUTE_GET_HD " + login).resolve(phanHoi(200, CHI_TIET(login))); await chay();
  }
  async function moTab(ten) { const b = nutTheoChu($("m4-chi-tiet"), ten); chuan(b, "SETUP_DOM_TAB " + ten); b.click(); await chay(); }
  async function moDotSo(so, login = A1) {
    await moTab("Đợt & checklist");
    const tr = tim($("m4-chi-tiet"), e => e.tagName === "TR" && !!e.children[0] && e.children[0].tagName === "TD" && e.children[0].textContent === String(so));
    const b = tr && tim(tr, e => e.tagName === "BUTTON" && e.textContent === "Mở");
    chuan(b && !b.disabled, "SETUP_DOM_MO_DOT_" + so);
    b.click(); await chay();
    lay(get(URL_HD(login)), "SETUP_ROUTE_GET_HD_KHI_MO_DOT_" + so).resolve(phanHoi(200, CHI_TIET(login))); await chay();
    const gd = calls.find(c => !c.xong && get("/api/m4/dot/dot-" + so)(c));
    if (gd) { gd.xong = true; gd.resolve(phanHoi(200, DOT_CT(login, "dot-" + so))); await chay(); }
  }
  async function doiVaiM4(login, {xongPost = true} = {}) {
    const s = $("m4-vai"), b = $("m4-doi-vai");
    chuan(s && b, "SETUP_DOM_DOI_VAI");
    s.value = login; b.click(); await chay();
    const p = lay(post("/api/m4/danh-tinh"), "SETUP_ROUTE_POST_DANH_TINH " + login);
    if (xongPost) { p.resolve(phanHoi(200, {dang_nhap: login})); await chay(); }
    return p;
  }

  // vùng module + tiện ích DOM
  const vungDp = () => tim($("m4-chi-tiet"), e => !!e._cls && e._cls.has("m4-dp"));
  const chuDp = () => (vungDp() || {textContent: ""}).textContent;
  const statusDp = () => { const v = vungDp(), s = v && v.querySelector(".m4-dp-status"); return s ? s.textContent : ""; };
  const nutDp = s => nutTheoChu(vungDp(), s);
  const oDp = nhan => theoNhan(vungDp(), nhan);
  const nhanDp = nhan => tim(vungDp(), e => e.tagName === "LABEL" && !!e.children[0] && e.children[0].textContent === nhan);
  const coPill = t => !!tim(vungDp(), e => e.tagName === "SPAN" && e._cls.has("m4-pill") && e.textContent === t);
  const go = (nhan, v) => { const e = oDp(nhan); chuan(e && e.isConnected, "SETUP_DOM_O " + nhan); e.value = v; e.dispatch("input"); return e; };
  const bam = async s => { const b = nutDp(s); assert.ok(b, "không có nút " + s); b.click(); await chay(); return b; };
  const bamEp = async s => { const b = nutDp(s); assert.ok(b, "không có nút " + s); b.disabled = false; b.click(); await chay(); };  // ép bật: kiểm chặn ở logic
  const toast = () => ($("toast") || {textContent: ""}).textContent;
  const chonTep = f => { const i = oDp("Tệp PDF hồ sơ đợt"); assert.ok(i, "không có ô chọn tệp PDF"); i.files = [f]; i.dispatch("change"); };
  async function lanMoi(dot) {  // rời tab rồi về: shell gọi huy() đồng bộ rồi ve() → incarnation mới + GET
    await moTab("Đợt & checklist");
    assert.strictEqual(vungDp(), null, "rời tab mà vùng Duyệt còn gắn");
    await moTab("Duyệt & PDF");
    return cho(getDp(dot), "GET duyệt sau khi mở lại tab (" + dot + ")");
  }
  const tra = async (c, status, data) => { c.resolve(phanHoi(status, data)); await chay(); };
  const NUT_LUU = "Lưu kết luận", NUT_DUYET = "Duyệt hồ sơ đợt (", NUT_TAI_LEN = "Tải PDF hồ sơ đợt lên", NUT_LAI = "Gửi lại", NUT_LAM_MOI = "↻ Làm mới";
  const NT = "Giá trị nghiệm thu chấp nhận (NT)", TT = "Số xin thanh toán kỳ này (TT)", TU = "Tạm ứng kỳ này", TH = "Thu hồi tạm ứng", GL = "Giữ lại (bảo hành/giữ lại)";
  const coNutLai = () => !!nutDp(NUT_LAI);
  const FILE = ctx.File;

  // ---------------------------------------------------------------- khởi động shell thật: vai A1 → HĐ → đợt 1
  await ca("BOOT shell M4 → HĐ A1 → đợt 1", async () => {
    await traTong(A1);
    chuan($("m4-nguoi") && $("m4-nguoi").textContent.includes(A1), "SETUP_DOM_M4_NGUOI");
    await moHdList(A1);
    await moDotSo(1);
    chuan(nutTheoChu($("m4-chi-tiet"), "Duyệt & PDF"), "SETUP_DOM_TAB_DUYET_KHONG_CO");
  });

  // ---------------------------------------------------------------- D0 tài sản module chưa phục vụ → nói thật; nạp → GET đúng đợt
  await ca("D0 tải lười /m4/m4_duyet_pdf.js: lỗi tải → chưa nối; nạp → GET dot_id", async () => {
    await moTab("Duyệt & PDF");
    const s = document.head.children.find(c => c.tagName === "SCRIPT" && c.src === "/m4/m4_duyet_pdf.js");
    assert.ok(s, "shell không tải /m4/m4_duyet_pdf.js khi mở tab Duyệt & PDF");
    assert.strictEqual(dem(laGetDp), 0, "chưa có module mà đã GET duyệt");
    s.onerror(); await chay();
    assert.ok($("m4-chi-tiet").textContent.includes("Chưa nối backend duyệt/PDF"), "lỗi tải tài sản không nói 'Chưa nối backend duyệt/PDF'");
    vm.runInContext(DP, ctx, {filename: "m4_duyet_pdf.js"}); await chay();
    assert.ok(ctx.window.kttM4DuyetPdf && typeof ctx.window.kttM4DuyetPdf.ve === "function" && typeof ctx.window.kttM4DuyetPdf.huy === "function", "module không công bố ve/huy");
    assert.ok(vungDp() && vungDp().isConnected, "module không mount vào vùng đã gắn");
    assert.strictEqual(conLai(getDp("dot-1")).length, 1, "nạp module không GET đúng /api/m4/duyet?dot_id=dot-1 một lần");
    const g = calls.find(c => !c.xong && getDp("dot-1")(c));
    assert.strictEqual(g.opts.headers["X-KTT-Token"], "TOKEN-THU"); assert.strictEqual(g.opts.cache, "no-store");
  });

  // ---------------------------------------------------------------- D1 backend chưa nối (GET + từng lệnh)
  await ca("D1 GET 404 / thiếu schema → chưa nối; POST 404 → chỉ tắt lệnh đó, nháp giữ", async () => {
    await tra(cho(getDp("dot-1"), "GET đầu"), 404, {error: "NOT_FOUND", message: "Không tìm thấy chức năng này."});
    assert.ok(chuDp().includes("Chưa nối backend duyệt/PDF"), "GET 404 không hiện 'Chưa nối backend duyệt/PDF'");
    for (const n of [NUT_LUU, NUT_DUYET, NUT_TAI_LEN]) assert.strictEqual(nutDp(n), null, "chưa nối mà vẫn có nút " + n);
    await bam(NUT_LAM_MOI);
    await tra(cho(getDp("dot-1"), "GET 2"), 200, {ok: true, ho_so: {}});
    assert.ok(chuDp().includes("Chưa nối backend duyệt/PDF"), "2xx thiếu schema không bị coi là chưa nối");
    assert.strictEqual(nutDp(NUT_LUU), null);
    await bam(NUT_LAM_MOI);
    await tra(cho(getDp("dot-1"), "GET 3"), 200, DTO({quyen: {ket_luan: true}}));
    assert.ok(chuDp().includes("Căn cứ của phiên bản"), "DTO hợp lệ không hiện hồ sơ");
    const toastTruoc = toast();
    go(NT, "5");
    await bam(NUT_LUU);
    await tra(cho(postDp("ket-luan"), "POST ket-luan"), 404, {error: "NOT_FOUND", message: "Không tìm thấy chức năng này."});
    assert.ok(statusDp().includes("Chưa nối backend duyệt/PDF cho lệnh lưu kết luận"), "POST 404 không nói chưa nối cho đúng lệnh: " + statusDp());
    assert.ok(nutDp(NUT_LUU) && nutDp(NUT_LUU).disabled, "POST 404 mà nút Lưu vẫn bật");
    assert.strictEqual(oDp(NT).value, "5", "POST 404 làm mất nháp");
    assert.strictEqual(coNutLai(), false, "chưa nối bị coi là CHƯA RÕ (có nút Gửi lại)");
    assert.ok(!toast().includes("Đã lưu") && toast() !== toastTruoc, "POST 404 phải báo lỗi, không toast thành công");
    assert.strictEqual(dem(postDp("ket-luan")), 1);
  });

  // ---------------------------------------------------------------- D2 REVIEW-only vs DUYET riêng
  await ca("D2 REVIEW-only không có nút Duyệt; quyền không tường minh → sai hợp đồng; DUYET riêng", async () => {
    await tra(await lanMoi("dot-1"), 200, DTO({tt: "CHO_DUYET", kl: KL_DA_LUU("1000", "900"), quyen: {ket_luan: true, duyet: false}}));
    assert.strictEqual(nutDp(NUT_DUYET), null, "REVIEW-only mà có nút Duyệt");
    assert.ok(chuDp().includes("không có quyền DUYỆT riêng"), "không giải thích thiếu quyền DUYỆT");
    assert.ok(coPill("DUYỆT: không"));
    assert.ok(nutDp(NUT_LUU) && !nutDp(NUT_LUU).disabled, "REVIEW được lưu kết luận mà nút tắt");
    await bam(NUT_LAM_MOI);
    const q = DTO({tt: "CHO_DUYET", kl: KL_DA_LUU("1000", "900")}); delete q.quyen.duyet;
    await tra(cho(getDp("dot-1"), "GET quyền thiếu"), 200, q);
    assert.ok(chuDp().includes("không đúng hợp đồng"), "quyền DUYỆT thiếu (không boolean) vẫn hiển thị");
    assert.strictEqual(nutDp(NUT_DUYET), null); assert.strictEqual(nutDp(NUT_LUU), null);
    await bam(NUT_LAM_MOI);
    await tra(cho(getDp("dot-1"), "GET DUYET riêng"), 200, DTO({tt: "CHO_DUYET", kl: KL_DA_LUU("1000", "900"), quyen: {ket_luan: false, duyet: true}}));
    assert.ok(nutDp(NUT_DUYET) && !nutDp(NUT_DUYET).disabled, "quyền DUYET mà không có/không bật nút Duyệt");
    assert.ok(nutDp(NUT_LUU) && nutDp(NUT_LUU).disabled, "DUYET không có ket_luan mà nút Lưu bật");
    assert.strictEqual(dem(laPostDp), 1, "D2 phát POST ngoài ý muốn");
  });

  // ---------------------------------------------------------------- D3 luồng dương: kết luận → duyệt không PDF → PDF → seal (từ máy chủ)
  await ca("D3 lưu/duyệt/không PDF/PDF + seal từ DTO; thiếu ≠ 0; NT ≠ TT", async () => {
    const Q = {ket_luan: true, duyet: true, tai_pdf: true};
    await tra(await lanMoi("dot-1"), 200, DTO({quyen: Q}));
    assert.ok(nhanDp(NT).textContent.includes("Thiếu"), "ô NT trống không hiện Thiếu");
    assert.ok(nhanDp(TT).textContent.includes("Thiếu"));
    go(NT, "1.000.000");
    const soPost = dem(laPostDp);
    await bam(NUT_LUU);
    assert.strictEqual(dem(laPostDp), soPost, "số sai định dạng vẫn POST");
    assert.ok(statusDp().includes("Số không hợp lệ"), "không báo số sai định dạng");
    go(NT, "1000000.50"); go(TT, "0"); go(TU, ""); go(TH, ""); go(GL, "0"); go("Tiền tệ", "VND");
    assert.ok(nhanDp(TT).textContent.includes("Có số"), "số 0 tường minh bị coi là Thiếu");
    assert.ok(nhanDp(TU).textContent.includes("Thiếu"), "ô trống không hiện Thiếu");
    go("KL chấp nhận R-01", "40"); go("Giải trình phát hiện F-01", "đã giải trình");
    await bam(NUT_LUU);
    const p = cho(postDp("ket-luan"), "POST lưu kết luận");
    assert.strictEqual(p.opts.headers["X-KTT-Token"], "TOKEN-THU"); assert.strictEqual(p.opts.cache, "no-store");
    const b = JSON.parse(p.opts.body);
    assert.deepStrictEqual(Object.keys(b).sort(), TRUONG_KET_LUAN, "body kết luận có trường ngoài hợp đồng / thiếu trường");
    assert.deepStrictEqual({...b, khoa: undefined}, {dot_id: "dot-1", version_id: V1, revision: 0, expected_basis: BASIS(0), gia_tri_nt: "1000000.50",
      so_xin_thanh_toan: "0", tam_ung: null, thu_hoi: null, giu_lai: "0", tien_te: "VND",
      dong_nt: [{row_id: "R-01", khoi_luong_chap_nhan: "40"}, {row_id: "R-02", khoi_luong_chap_nhan: null}],
      xu_ly_phat_hien: [{finding_id: "F-01", ly_do: "đã giải trình"}], ly_do: null, khoa: undefined}, "body kết luận sai (thiếu ≠ 0, NT ≠ TT)");
    assert.ok(typeof b.khoa === "string" && b.khoa.length > 4, "thiếu khóa thao tác");
    const soGet = dem(getDp("dot-1"));
    await tra(p, 200, ACK("KET_LUAN", b.khoa, CTX("dot-1", V1, 0), {ket_luan_id: KL1}));
    assert.ok(toast().includes("Đã lưu kết luận"), "ACK hợp lệ không toast lưu");
    assert.strictEqual(dem(getDp("dot-1")), soGet + 1, "ACK hợp lệ không đọc lại");
    await tra(cho(getDp("dot-1"), "GET sau lưu"), 200, DTO({tt: "CHO_DUYET", kl: KL_DA_LUU("1000000.50", "0"), quyen: Q}));
    assert.strictEqual(oDp(NT).value, "1000000.50"); assert.strictEqual(oDp(TT).value, "0");
    assert.ok(nhanDp(TT).textContent.includes("Có số") && nhanDp(TU).textContent.includes("Thiếu"), "kết luận máy chủ: 0 vs null hiển thị sai");
    assert.ok(chuDp().includes("Kết luận đã lưu: " + KL1.slice(0, 12)), "không hiện kết luận đã lưu từ máy chủ");
    // duyệt khi CHƯA có PDF
    assert.ok(nutDp(NUT_DUYET) && !nutDp(NUT_DUYET).disabled, "CHO_DUYET + DUYET mà nút Duyệt tắt");
    await bam(NUT_DUYET);
    const pd = cho(postDp("chap-thuan"), "POST duyệt");
    const bd = JSON.parse(pd.opts.body);
    assert.deepStrictEqual(Object.keys(bd).sort(), TRUONG_CHAP_THUAN, "body duyệt có trường ngoài hợp đồng");
    assert.deepStrictEqual({...bd, khoa: undefined}, {dot_id: "dot-1", version_id: V1, revision: 0, expected_basis: BASIS(0), ket_luan_id: KL1, ly_do: null, khoa: undefined});
    assert.notStrictEqual(bd.khoa, b.khoa, "lệnh duyệt dùng lại khóa của kết luận");
    await tra(pd, 200, ACK("CHAP_THUAN", bd.khoa, CTX("dot-1", V1, 0), {ket_luan_id: KL1, quyet_dinh_id: QD1}));
    assert.ok(toast().includes("Chờ PDF"), "duyệt không PDF không báo Chờ PDF: " + toast());
    await tra(cho(getDp("dot-1"), "GET sau duyệt"), 200, DTO({tt: "CHO_PDF", kl: KL_DA_LUU("1000000.50", "0"), qd: QD, quyen: Q}));
    assert.ok(coPill("Đã duyệt — Chờ PDF hồ sơ đợt"), "không hiện CHO_PDF");
    assert.ok(coPill("Chưa chuyển") && coPill("Chờ PDF"), "hai nhánh KT/Request không cùng chờ khi chưa có PDF");
    assert.ok(!coPill("Chờ xác nhận") && !coPill("Đủ căn cứ duyệt + PDF"), "chưa PDF mà hiện KT/Request sẵn sàng");
    assert.ok(nutDp(NUT_LUU).disabled, "đã duyệt mà còn lưu được kết luận");
    // PDF hồ sơ đợt: bytes File gốc + X-M4-Info chỉ trường hợp đồng
    const fX = new FILE([new Uint8Array([37, 80, 68, 70, 45, 49, 46, 55, 10])], "ho_so_thanh_toan_dot_1.pdf", {type: "application/pdf"});
    chonTep(fX);
    await bam(NUT_TAI_LEN);
    const pp = cho(postDp("pdf"), "POST PDF");
    assert.strictEqual(pp.opts.body, fX, "POST PDF không gửi đúng đối tượng File gốc");
    const info = JSON.parse(decodeURIComponent(pp.opts.headers["X-M4-Info"]));
    assert.deepStrictEqual(Object.keys(info).sort(), TRUONG_PDF, "X-M4-Info có trường ngoài hợp đồng");
    assert.deepStrictEqual({...info, khoa: undefined}, {dot_id: "dot-1", version_id: V1, revision: 0, expected_basis: BASIS(0), ten: "ho_so_thanh_toan_dot_1.pdf",
      media_type: "application/pdf", khoa: undefined});
    await tra(pp, 200, ACK("PDF", info.khoa, CTX("dot-1", V1, 0), {pdf_id: PDF1, seal_id: SEAL1, kt_pending_id: KTP1}));
    assert.ok(toast().includes("niêm phong"));
    await tra(cho(getDp("dot-1"), "GET sau PDF"), 200, DTO({tt: "DA_SEAL", kl: KL_DA_LUU("1000000.50", "0"), qd: QD, pdf: PDFX, seal: SEALX, quyen: Q,
      kt: {trang_thai: "CHO_XAC_NHAN", pending_id: KTP1}, rq: {trang_thai: "DU_DIEU_KIEN_CHUA_NOI"}}));
    assert.ok(coPill("Đã niêm phong") && coPill("Chờ xác nhận") && coPill("Đủ căn cứ duyệt + PDF"), "seal/KT/Request từ máy chủ không hiện đúng");
    assert.ok(chuDp().includes("chưa ghi nhận công nợ/AP"), "không nói rõ chưa ghi nhận AP");
    assert.strictEqual(nutDp(NUT_TAI_LEN), null, "đã seal mà còn cho thay PDF");
    const nutCam = timHet(vungDp(), e => e.tagName === "BUTTON").map(e => e.textContent)
      .filter(t => t.includes("Request") || t.includes("AP") || t.toLowerCase().includes("kế toán") || t.toLowerCase().includes("xác nhận"));
    assert.deepStrictEqual(nutCam, [], "có nút AP/Request/kế toán giả");
    // DTO KT Chờ xác nhận nhưng không có seal → sai hợp đồng, không hiển thị
    await bam(NUT_LAM_MOI);
    await tra(cho(getDp("dot-1"), "GET KT không seal"), 200, DTO({tt: "CHO_PDF", kl: KL_DA_LUU("1000000.50", "0"), qd: QD, quyen: Q,
      kt: {trang_thai: "CHO_XAC_NHAN", pending_id: KTP1}}));
    assert.ok(chuDp().includes("không đúng hợp đồng"), "KT Chờ xác nhận không seal vẫn được hiển thị");
    assert.ok(!coPill("Chờ xác nhận"));
  });

  // ---------------------------------------------------------------- D4 2xx sai / mất phản hồi → CHƯA RÕ, gửi lại y nguyên
  await ca("D4 2xx sai hợp đồng / JSON đứt / mất kết nối / 503 → CHƯA RÕ; Gửi lại cùng chuỗi body/khóa", async () => {
    const C0 = CTX("dot-1", V1, 0);
    await tra(await lanMoi("dot-1"), 200, DTO({quyen: {ket_luan: true}}));
    go(NT, "7"); go(TT, "6");
    await bam(NUT_LUU);
    const p1 = cho(postDp("ket-luan"), "POST gốc");
    const goc = p1.opts.body, khoa = JSON.parse(goc).khoa, soGet = dem(laGetDp);
    const ackHong = [
      ["sai khóa", ACK("KET_LUAN", khoa + "-x", C0, {ket_luan_id: KL1})],
      ["JSON đứt", JSON_DUT],
      ["sai context", ACK("KET_LUAN", khoa, {...C0, revision: 1}, {ket_luan_id: KL1})],
      ["thiếu receipt", {...ACK("KET_LUAN", khoa, C0, {ket_luan_id: KL1}), receipt_id: undefined}],
      ["sai hành động", ACK("CHAP_THUAN", khoa, C0, {ket_luan_id: KL1, quyet_dinh_id: QD1})],
      ["ID không tường minh", (() => { const a = ACK("KET_LUAN", khoa, C0, {ket_luan_id: KL1}); delete a.seal_id; return a; })()],
    ];
    let p = p1;
    for (const [ten, a] of ackHong) {
      await tra(p, 200, a);
      assert.ok(statusDp().includes("Chưa rõ kết quả"), ten + ": 2xx sai không thành CHƯA RÕ: " + statusDp());
      assert.ok(!toast().includes("Đã lưu"), ten + ": toast thành công cho 2xx sai");
      assert.strictEqual(dem(laGetDp), soGet, ten + ": 2xx sai vẫn đọc lại");
      assert.ok(nutDp("Gửi lại y nguyên (cùng khóa)"), ten + ": không có nút Gửi lại y nguyên (cùng khóa)");
      const truoc = dem(postDp("ket-luan"));
      go(NT, "8"); await bamEp(NUT_LUU);
      assert.strictEqual(dem(postDp("ket-luan")), truoc, ten + ": CHƯA RÕ mà Lưu phát lệnh mới");
      await bam("Gửi lại y nguyên (cùng khóa)");
      p = cho(postDp("ket-luan"), ten + ": POST gửi lại");
      assert.strictEqual(p.opts.body, goc, ten + ": gửi lại khác chuỗi body/khóa gốc");
    }
    p.reject(new TypeError("Failed to fetch")); await chay();  // mất phản hồi
    assert.ok(coNutLai() && statusDp().includes("Chưa rõ kết quả"), "mất kết nối không thành CHƯA RÕ");
    await bam("Gửi lại y nguyên (cùng khóa)");
    p = cho(postDp("ket-luan"), "POST gửi lại sau mất kết nối");
    assert.strictEqual(p.opts.body, goc);
    await tra(p, 503, {error: "M4_KET_QUA_CHUA_RO", message: "chưa rõ"});
    assert.ok(coNutLai(), "503 M4_KET_QUA_CHUA_RO không thành CHƯA RÕ");
    await bam("Gửi lại y nguyên (cùng khóa)");
    p = cho(postDp("ket-luan"), "POST gửi lại cuối");
    assert.strictEqual(p.opts.body, goc);
    await tra(p, 200, ACK("KET_LUAN", khoa, C0, {ket_luan_id: KL1, lap_lai: true}));
    assert.ok(toast().includes("Đã lưu kết luận"), "ACK rõ cuối không toast");
    assert.strictEqual(dem(laGetDp), soGet + 1, "ACK rõ cuối không đọc lại đúng một lần");
    assert.strictEqual(coNutLai(), false, "kết quả rõ mà còn nút Gửi lại");
    assert.ok(calls.filter(postDp("ket-luan")).slice(-9).every(c => c.opts.body === goc), "mọi lần gửi của ý định phải cùng chuỗi body");
    await tra(cho(getDp("dot-1"), "GET sau rõ"), 200, DTO({tt: "CHO_DUYET", kl: KL_DA_LUU("7", "6"), quyen: {ket_luan: true}}));
    assert.strictEqual(oDp(NT).value, "8", "nháp sửa trong lúc CHƯA RÕ bị ACK đè");
  });

  // ---------------------------------------------------------------- D5 X đang bay + form Y / File Y
  await ca("D5 X đang bay + nháp Y / File Y cùng metadata → không gửi Y thay X; Gửi lại = X", async () => {
    await tra(await lanMoi("dot-1"), 200, DTO({quyen: {ket_luan: true}}));
    go(NT, "10");
    await bam(NUT_LUU);
    const px = cho(postDp("ket-luan"), "POST X");
    const bodyX = px.opts.body;
    go(NT, "11");
    assert.ok(nutDp(NUT_LUU).disabled, "X đang bay mà nút Lưu bật");
    await bamEp(NUT_LUU);
    assert.strictEqual(conLai(postDp("ket-luan")).length, 0, "X đang bay mà nháp Y được gửi");
    px.reject(new TypeError("Failed to fetch")); await chay();
    await bam("Gửi lại y nguyên (cùng khóa)");
    const px2 = cho(postDp("ket-luan"), "POST gửi lại X");
    assert.strictEqual(px2.opts.body, bodyX, "Gửi lại lấy nháp Y thay body X");
    assert.strictEqual(JSON.parse(px2.opts.body).gia_tri_nt, "10");
    await tra(px2, 200, ACK("KET_LUAN", JSON.parse(bodyX).khoa, CTX("dot-1", V1, 0), {ket_luan_id: KL1}));
    await tra(cho(getDp("dot-1"), "GET sau X"), 200, DTO({tt: "CHO_DUYET", kl: KL_DA_LUU("10", null), quyen: {ket_luan: true}}));
    assert.strictEqual(oDp(NT).value, "11", "ACK của X đè nháp Y");
    await bam(NUT_LUU);
    const py = cho(postDp("ket-luan"), "POST Y");
    assert.strictEqual(JSON.parse(py.opts.body).gia_tri_nt, "11");
    assert.notStrictEqual(JSON.parse(py.opts.body).khoa, JSON.parse(bodyX).khoa, "Y dùng lại khóa của X");
    await tra(py, 200, ACK("KET_LUAN", JSON.parse(py.opts.body).khoa, CTX("dot-1", V1, 0), {ket_luan_id: KL1}));
    await tra(cho(getDp("dot-1"), "GET sau Y"), 200, DTO({tt: "CHO_DUYET", kl: KL_DA_LUU("11", null), quyen: {ket_luan: true, tai_pdf: true}}));
    // File X đang bay → chọn File Y cùng tên/loại/kích thước
    const fX = new FILE([new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9])], "ho_so_dot.pdf", {type: "application/pdf"});
    const fY = new FILE([new Uint8Array([9, 8, 7, 6, 5, 4, 3, 2, 1])], "ho_so_dot.pdf", {type: "application/pdf"});
    chonTep(fX);
    await bam(NUT_TAI_LEN);
    const tx = cho(postDp("pdf"), "POST File X");
    const infoX = tx.opts.headers["X-M4-Info"];
    chonTep(fY);
    await bamEp(NUT_TAI_LEN);
    assert.strictEqual(conLai(postDp("pdf")).length, 0, "File X đang bay mà File Y được gửi");
    await tra(tx, 503, {error: "M4_KET_QUA_CHUA_RO", message: "chưa rõ"});
    const nutLaiTep = nutDp("Gửi lại tệp gốc y nguyên (cùng khóa)");
    assert.ok(nutLaiTep, "PDF chưa rõ không có nút gửi lại tệp gốc");
    await bam("Gửi lại tệp gốc y nguyên (cùng khóa)");
    const tx2 = cho(postDp("pdf"), "POST gửi lại File X");
    assert.strictEqual(tx2.opts.body, fX, "Gửi lại gửi File khác (File Y cùng metadata) thay File X gốc");
    assert.notStrictEqual(tx2.opts.body, fY);
    assert.strictEqual(tx2.opts.headers["X-M4-Info"], infoX, "Gửi lại đổi X-M4-Info");
    const khoaX = JSON.parse(decodeURIComponent(infoX)).khoa;
    await tra(tx2, 200, ACK("PDF", khoaX, CTX("dot-1", V1, 0), {pdf_id: PDF1}));
    await tra(cho(getDp("dot-1"), "GET sau File X"), 200, DTO({tt: "CHO_DUYET", kl: KL_DA_LUU("11", null), pdf: PDFX, quyen: {ket_luan: true, tai_pdf: true}}));
    assert.ok(chuDp().includes("Đang chọn: ho_so_dot.pdf"), "File Y chọn sau bị bỏ khi X thành công");
    await bam(NUT_TAI_LEN);
    const ty = cho(postDp("pdf"), "POST File Y");
    assert.strictEqual(ty.opts.body, fY, "lệnh mới không gửi File Y");
    assert.notStrictEqual(JSON.parse(decodeURIComponent(ty.opts.headers["X-M4-Info"])).khoa, khoaX, "File Y dùng lại khóa X");
    await tra(ty, 422, {error: "M4_PDF_KHONG_HOP_LE", message: "Tệp không phải PDF hợp lệ."});
    assert.ok(statusDp().includes("Tệp không phải PDF hợp lệ."), "lỗi xác định không hiện thông điệp máy chủ");
    assert.strictEqual(coNutLai(), false, "lỗi xác định 422 bị coi là CHƯA RÕ");
  });

  // ---------------------------------------------------------------- D6 cùng actor A→B→A, ACK/ERROR cũ
  await ca("D6 A(đợt 1)→B(đợt 2)→A: ý định cũ không rò sang B; ACK/403 cũ không chạm A mới", async () => {
    await tra(await lanMoi("dot-1"), 200, DTO({quyen: {ket_luan: true}}));
    go(NT, "20");
    await bam(NUT_LUU);
    const px = cho(postDp("ket-luan"), "POST X ở A");
    const khoaX = JSON.parse(px.opts.body).khoa;
    await moDotSo(2);
    assert.strictEqual(vungDp(), null);
    await moTab("Duyệt & PDF");
    await tra(cho(getDp("dot-2"), "GET B"), 200, DTO({dot: "dot-2", ver: V2, quyen: {ket_luan: true}}));
    assert.ok(chuDp().includes("Căn cứ của phiên bản"), "B không hiện hồ sơ");
    assert.ok(!chuDp().includes("lần mở trước") && !coNutLai(), "ý định của A rò sang B");
    assert.ok(nutDp(NUT_LUU) && !nutDp(NUT_LUU).disabled, "ý định của A chặn lệnh của B");
    assert.strictEqual(oDp(NT).value, "", "nháp A rò sang B");
    await moDotSo(1);
    await moTab("Duyệt & PDF");
    await tra(cho(getDp("dot-1"), "GET A lại"), 200, DTO({quyen: {ket_luan: true}}));
    assert.ok(chuDp().includes("lần mở trước còn đang chờ"), "A mới không cho biết X còn đang chờ");
    assert.strictEqual(oDp(NT).value, "", "nháp incarnation cũ mang sang A mới");
    go(NT, "21");
    await bamEp(NUT_LUU);
    assert.strictEqual(conLai(postDp("ket-luan")).length, 0, "X chưa có kết quả mà A mới gửi Y (bỏ ngầm X)");
    const toastTruoc = toast(), soGet = dem(laGetDp);
    await tra(px, 200, ACK("KET_LUAN", khoaX, CTX("dot-1", V1, 0), {ket_luan_id: KL1}));
    assert.strictEqual(toast(), toastTruoc, "ACK cũ toast ở A mới");
    assert.strictEqual(dem(laGetDp), soGet, "ACK cũ kích GET ở A mới");
    assert.strictEqual(oDp(NT).value, "21", "ACK cũ đè nháp A mới");
    assert.ok(nutDp(NUT_LUU) && !nutDp(NUT_LUU).disabled, "ACK cũ rõ mà A mới vẫn bị chặn");
    await bam(NUT_LUU);
    const py = cho(postDp("ket-luan"), "POST Y ở A mới");
    assert.notStrictEqual(JSON.parse(py.opts.body).khoa, khoaX);
    assert.strictEqual(JSON.parse(py.opts.body).gia_tri_nt, "21");
    // LỖI cũ: Y đang bay → B → A → 403 của Y về
    await moDotSo(2); await moTab("Duyệt & PDF");
    await tra(cho(getDp("dot-2"), "GET B lần 2"), 200, DTO({dot: "dot-2", ver: V2, quyen: {ket_luan: true}}));
    await moDotSo(1); await moTab("Duyệt & PDF");
    await tra(cho(getDp("dot-1"), "GET A lần 3"), 200, DTO({quyen: {ket_luan: true}}));
    const t2 = toast(), g2 = dem(laGetDp);
    await tra(py, 403, {error: "M4_KHONG_QUYEN", message: "Không có quyền"});
    assert.ok(chuDp().includes("Căn cứ của phiên bản"), "403 cũ gỡ hồ sơ của A mới");
    assert.strictEqual(toast(), t2, "403 cũ toast ở A mới");
    assert.strictEqual(dem(laGetDp), g2, "403 cũ kích GET");
    assert.ok(nutDp(NUT_LUU) && !nutDp(NUT_LUU).disabled, "403 cũ (đã rõ) vẫn chặn A mới");
  });

  // ---------------------------------------------------------------- D7 GET đảo thứ tự / khi đang gõ / sau khi rời tab
  await ca("D7 GET đảo thứ tự; GET về khi đang gõ; GET về sau rời tab", async () => {
    await bam(NUT_LAM_MOI); const g1 = cho(getDp("dot-1"), "G1");
    await bam(NUT_LAM_MOI); const g2 = cho(getDp("dot-1"), "G2");
    await tra(g2, 200, DTO({rev: 2, quyen: {ket_luan: true}}));
    assert.ok(chuDp().includes("· revision 2"), "G2 không hiện");
    await tra(g1, 200, DTO({rev: 1, quyen: {ket_luan: true}}));
    assert.ok(chuDp().includes("· revision 2") && !chuDp().includes("· revision 1"), "G1 cũ về sau đè G2");
    await bam(NUT_LAM_MOI); const g3 = cho(getDp("dot-1"), "G3");
    go(NT, "99");
    await tra(g3, 200, DTO({rev: 3, quyen: {ket_luan: true}}));
    assert.ok(chuDp().includes("· revision 2"), "GET về khi đang gõ vẽ đè form");
    assert.ok(statusDp().includes("chưa áp dụng để giữ nháp"));
    assert.strictEqual(oDp(NT).value, "99");
    await bam(NUT_LAM_MOI); const g4 = cho(getDp("dot-1"), "G4");
    await moTab("Đợt & checklist");
    await tra(g4, 200, DTO({rev: 4, quyen: {ket_luan: true}}));
    assert.strictEqual(vungDp(), null, "GET về sau rời tab dựng lại vùng");
    await moTab("Duyệt & PDF");
    const g5 = cho(getDp("dot-1"), "G5 sau mở lại");
    assert.ok(chuDp().includes("Đang tải hồ sơ duyệt") && !chuDp().includes("· revision 4"), "dữ liệu GET cũ hiện ở lần mở mới");
    await tra(g5, 200, DTO({rev: 5, quyen: {ket_luan: true}}));
    assert.ok(chuDp().includes("· revision 5"));
  });

  // ---------------------------------------------------------------- D8 409/403 hiện hành vs cũ
  await ca("D8 409 hiện hành giữ nháp + revision mới; 409 cũ 0 GET; 403 hiện hành gỡ bằng chứng", async () => {
    await tra(await lanMoi("dot-1"), 200, DTO({rev: 0, quyen: {ket_luan: true}, pdf: PDFX}));
    go(NT, "30");
    await bam(NUT_LUU);
    const p = cho(postDp("ket-luan"), "POST 409");
    const g0 = dem(getDp("dot-1"));
    await tra(p, 409, {error: "M4_REVISION_CU", message: "Hồ sơ đã đổi"});
    assert.strictEqual(dem(getDp("dot-1")), g0 + 1, "409 hiện hành không đọc lại");
    assert.ok(statusDp().includes("đã đọc lại"));
    await tra(cho(getDp("dot-1"), "GET sau 409"), 200, DTO({rev: 1, quyen: {ket_luan: true}, pdf: PDFX}));
    assert.strictEqual(oDp(NT).value, "30", "409 làm mất nháp");
    assert.strictEqual(coNutLai(), false, "409 bị coi là CHƯA RÕ");
    await bam(NUT_LUU);
    const p2 = cho(postDp("ket-luan"), "POST sau 409");
    const b2 = JSON.parse(p2.opts.body);
    assert.deepStrictEqual([b2.revision, b2.expected_basis, b2.gia_tri_nt], [1, BASIS(1), "30"], "lần gửi sau 409 không dùng revision/basis mới");
    assert.notStrictEqual(b2.khoa, JSON.parse(p.opts.body).khoa);
    // 409 cũ
    await tra(await lanMoi("dot-1"), 200, DTO({rev: 1, quyen: {ket_luan: true}, pdf: PDFX}));
    const g1 = dem(laGetDp);
    await tra(p2, 409, {error: "M4_REVISION_CU", message: "Hồ sơ đã đổi"});
    assert.strictEqual(dem(laGetDp), g1, "409 cũ kích GET ở incarnation mới");
    // 403 hiện hành
    assert.ok(nutDp("Tải PDF ↓"), "setup: không có nút tải PDF");
    go(NT, "31");
    await bam(NUT_LUU);
    const p3 = cho(postDp("ket-luan"), "POST 403");
    await tra(p3, 403, {error: "M4_KHONG_QUYEN", message: "Không có quyền"});
    assert.ok(!chuDp().includes("Căn cứ của phiên bản") && !chuDp().includes(PDFX.name), "403 hiện hành không gỡ bằng chứng");
    assert.ok(chuDp().includes("Không có quyền"));
    for (const n of [NUT_LUU, NUT_LAI, "Tải PDF ↓"]) assert.strictEqual(nutDp(n), null, "403 hiện hành còn nút " + n);
    assert.strictEqual(dem(laGetDp), g1, "403 tự đọc lại");
  });

  // ---------------------------------------------------------------- D9 đổi vai khi POST + GET đang bay
  await ca("D9 đổi vai (barrier thật): module gỡ đồng bộ; phản hồi cũ không toast/GET; không đợt → không GET", async () => {
    await tra(await lanMoi("dot-1"), 200, DTO({quyen: {ket_luan: true}}));
    go(NT, "40");
    await bam(NUT_LUU);
    const p = cho(postDp("ket-luan"), "POST trước đổi vai");
    await bam(NUT_LAM_MOI);
    const g = cho(getDp("dot-1"), "GET trước đổi vai");
    const vCu = vungDp();
    const doi = doiVaiM4(B1, {xongPost: false});
    assert.ok(!vCu.isConnected, "đổi vai không gỡ vùng Duyệt đồng bộ");
    const pv = await doi;
    const t0 = toast(), soGet = dem(laGetDp);
    await tra(g, 200, DTO({rev: 7, quyen: {ket_luan: true}}));
    await tra(p, 200, ACK("KET_LUAN", JSON.parse(p.opts.body).khoa, CTX("dot-1", V1, 0), {ket_luan_id: KL1}));
    assert.ok(!toast().includes("Đã lưu") && toast() === t0, "ACK của vai cũ toast sau đổi vai");
    assert.strictEqual(dem(laGetDp), soGet, "phản hồi cũ kích GET sau đổi vai");
    pv.resolve(phanHoi(200, {dang_nhap: B1})); await chay();
    await traTong(B1);
    assert.strictEqual(vungDp(), null, "vai mới chưa chọn HĐ mà vẫn có vùng Duyệt");
    assert.strictEqual(dem(laGetDp), soGet, "vai mới tự GET duyệt");
    const pv2 = await doiVaiM4(A1); void pv2;
    await traTong(A1);
    await moHdList(A1);
    assert.ok(vungDp() && chuDp().includes("Chọn một đợt"), "tab Duyệt không đợt không nhắc chọn đợt");
    assert.strictEqual(dem(laGetDp), soGet, "không có đợt mà vẫn GET duyệt");
    await moDotSo(1);
    await moTab("Duyệt & PDF");
    await tra(cho(getDp("dot-1"), "GET sau về A1"), 200, DTO({tt: "DA_SEAL", kl: KL_DA_LUU("1", "1"), qd: QD, pdf: PDFX, seal: SEALX,
      kt: {trang_thai: "CHO_XAC_NHAN", pending_id: KTP1}, rq: {trang_thai: "DU_DIEU_KIEN_CHUA_NOI"}}));
    assert.ok(!chuDp().includes("lần mở trước"), "ý định đã rõ của vai cũ còn hiện");
  });

  // ---------------------------------------------------------------- D10 tải PDF: dương / sai độ dài / blob giữ + rời #m4
  await ca("D10 tải PDF đúng 1 click; độ dài khác 0 click; blob giữ + hashchange → 0 click", async () => {
    const URL_TAI = "/api/m4/duyet/" + V1 + "/pdf/" + PDF1;
    const c0 = soClickTai;
    await bam("Tải PDF ↓");
    await tra(cho(get(URL_TAI), "GET tải PDF"), 200, null);  // phanHoi blob mặc định 0 byte → sai độ dài
    assert.strictEqual(soClickTai, c0, "độ dài bytes khác byte_length mà vẫn click");
    assert.ok(statusDp().includes("khác độ dài"));
    await bam("Tải PDF ↓");
    cho(get(URL_TAI), "GET tải PDF 2").resolve(phanHoi(200, null, 9)); await chay();
    assert.strictEqual(soClickTai, c0 + 1, "tải đúng ngữ cảnh không click đúng một lần");
    await bam("Tải PDF ↓");
    let thaBlob = null;
    cho(get(URL_TAI), "GET tải PDF 3").resolve({ok: true, status: 200, headers: {get: () => "application/pdf"}, json: async () => ({}),
      blob: () => new Promise(r => { thaBlob = r; })});
    await chay();
    chuan(typeof thaBlob === "function", "SETUP_BLOB_GIU: module chưa đọc blob");
    chuan(ngheHashM4.length > 0, "SETUP_HASHCHANGE_M4: m4.js không đăng ký hashchange");
    const soGet = dem(laGetDp);
    ctx.location.hash = "#hopdong";
    for (const fn of ngheHashM4) fn({});
    thaBlob(taoBlob(9)); await chay();
    assert.strictEqual(soClickTai, c0 + 1, "blob về sau khi rời #m4 vẫn click");
    assert.strictEqual(dem(laGetDp), soGet, "rời #m4 kích GET duyệt");
  });
}

main().catch(e => {
  if (e instanceof SetupError) KQ.setup_errors.push({ca: "boot", ma: e.message});
  else KQ.hong.push({ca: "main", loi: String((e && e.stack) || e)});
}).finally(async () => {
  await chay(3);
  if (loiNgoai.length) KQ.hong.push({ca: "unhandledRejection", loi: loiNgoai.map(e => String((e && e.stack) || e)).join("\n")});
  console.log(JSON.stringify({ket_qua: KQ.hong.length || KQ.setup_errors.length ? "HONG" : "DAT", dat: KQ.dat.length, hong: KQ.hong, setup_errors: KQ.setup_errors,
    chua_chay: KQ.chua_chay}, null, 2));
  process.exitCode = KQ.hong.length || KQ.setup_errors.length || KQ.chua_chay.length ? 1 : 0;
});
