"use strict";
// M4-03A GUI — kiểm MÃ THẬT (app.js + m4/giao_dien/m4.js + m4/giao_dien/m4_ke_toan.js; nhóm P2 chạy m4/giao_dien/m4_duyet_pdf.js) trên DOM/fetch giả có kiểm soát:
//  E   điểm vào "Kế toán nghiệm thu" cho vai CHỈ KE_TOAN (không phạm vi portal, không danh sách HĐ), tải lười tài sản, backend chưa compose → CHUA_NOI.
//  P01 kt=null → lưu nháp đầu expected_revision 0 (body đúng allowlist, đúng thứ tự); P02 null ≠ "0", không tự chép số nguồn.
//  P03 CO_CAN_CU dùng đúng id tệp thật trong nguon.tep_can_cu + trích dẫn → lưu; xác nhận body đúng 6 khóa, không tiền; sau xác nhận chỉ "chờ ghi công nợ".
//  P04 KHONG_AP_DUNG có lý do → xác nhận; thiếu lý do → tắt, 0 POST.  P05 tep_can_cu vắng → HOLD (0 POST), sai kiểu → SAI_DTO, rỗng → CO tắt có ghi chú.
//  P06 revision canonical đột biến (vắng/bool/chuỗi/0/alias kt.id/{}/vắng kt) → không lệnh, 0 POST.  P07 hai phong bì + selector lịch sử GET đúng
//  phong_bi_id của row.context, A chỉ đọc, kt của B không mượn A.  P08 nguồn mới chưa niêm phong → không hiện hành.  P09 lịch sử KT sai thứ tự → SAI_DTO.
//  P10 thu hồi (GET 403 / 200 xem=false / POST 403 / danh sách 403) gỡ bằng chứng ngay.  P11 UNKNOWN (mất kết nối / 2xx sai hợp đồng) → Gửi lại y nguyên
//  cùng body/khóa, lệnh mới bị chặn, nháp mới hơn không bị xóa.  P12 phản hồi giữ (ACK/GET/blob) về muộn sau A→B→A / rời #m4 / đổi vai → 0 hiệu ứng.
//  P13 409 giữ nháp + GET có fence.  PDF đúng/sai độ dài.  P2 kiemChuaNop (m4_duyet_pdf.js): baseline CHUA_NOP + 3 nhóm invariant (nhóm 1 hai ca con).
//  INTEGRATION (tùy chọn): `node tests/m4_03a_async.cjs <bundle.json>` với bundle M4_03A_KT_PRODUCER_BUNDLE_V1 do backend THẬT sinh sau compose (xem
//  docs/BAO-CAO-M4-03A-GUI.md); thiếu bundle → in INTEGRATION NOT_VERIFIED. Các DTO literal trong tệp này là fixture THỦ CÔNG mô phỏng hợp đồng: chỉ chứng
//  minh hành vi UI/route, KHÔNG chứng minh producer/PG/GUI tích hợp đạt.
// CODE_ONLY: WRITTEN_NOT_RUN — coder viết, CHƯA CHẠY. Root chạy: `node tests/m4_03a_async.cjs [bundle.json]` (Node ≥ 18). process.exitCode = 0 khi mọi ca đạt,
// 1 khi có ca hỏng / setup_errors / unhandledRejection / bundle sai. Không ghi tệp, không mạng, không process.exit.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");
const APP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/app.js"), "utf8");
const M4 = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/m4.js"), "utf8");
const KT = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/m4_ke_toan.js"), "utf8");
const DP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/m4_duyet_pdf.js"), "utf8");
const ID_TINH = new Set([...fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/index.html"), "utf8").matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const BLOB_GOC = globalThis.Blob || (() => { try { return require("buffer").Blob; } catch (_) { return null; } })();
const loiNgoai = [];
process.on("unhandledRejection", e => { loiNgoai.push(e); });

// ------------------------------------------------------------------ DOM giả có kết nối thật (sao khung tests/m4_02c_fix01_async.cjs — tệp đó KHÔNG sửa)
let soClickTai = 0;
function moiTruong() {
  const reg = new Map(), dongId = new Set();
  let taoTinh = false;
  class El {
    constructor(tag) {
      this.tagName = String(tag).toUpperCase(); this.children = []; this.parent = null; this._text = ""; this._id = "";
      this.listeners = {}; this.attrs = {}; this.dataset = {}; this.style = {}; this._cls = new Set(); this.files = []; this.disabled = false;
      this.checked = false; this.selected = false; this._value = ""; this._valueSet = false; this.type = ""; this.title = ""; this.open = false; this.hidden = false;
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
    querySelector(s) {
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
  let soUuid = 0;
  const henGio = (fn, ms, ...a) => { const t = setTimeout(fn, ms, ...a); if (ms > 0 && t && typeof t.unref === "function") t.unref(); return t; };
  const ctx = {
    document, Node: El, console, setTimeout: henGio, clearTimeout, Promise, Map, Set, JSON, Math, Date, Number, String, Object, Array, Error, TypeError, SyntaxError,
    encodeURIComponent, decodeURIComponent, URLSearchParams, location: {hash: "#m4"}, crypto: {randomUUID: () => "uuid-" + (++soUuid)},
    URL: {createObjectURL: () => "blob:x", revokeObjectURL() {}}, fetch, navigator: {}, Intl,
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
function timTatCa(root, pred, out = []) { if (!root) return out; if (pred(root)) out.push(root); for (const c of root.children || []) timTatCa(c, pred, out); return out; }
const nutTheoChu = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));
const nutDung = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent === s);
const theoNhan = (root, s) => tim(root, e => e.attrs && e.attrs["aria-label"] === s);
const sao = o => JSON.parse(JSON.stringify(o));

// ------------------------------------------------------------------ fixture THỦ CÔNG theo hợp đồng (UUID tổng hợp; không dữ liệu/credential thật)
const SCHEMA = "M4_03A_KT_V1";
const U = n => "0000000" + n + "-0000-4000-8000-" + String(n).padStart(12, "0");
const PN = U(1), DA = U(2), HD = U(3), DOT = U(4), PEND = U(5), PEND2 = "5a5a5a5a-0000-4000-8000-00000000005a";
const PB_A = "a1a1a1a1-0000-4000-8000-0000000000a1", PB_B = "b2b2b2b2-0000-4000-8000-0000000000b2";
const TEP1 = "7e7e7e7e-0000-4000-8000-00000000007e", TEP2 = "7f7f7f7f-0000-4000-8000-00000000007f";
const KTR = n => "c0c0c0c0-0000-4000-8000-" + String(n).padStart(12, "0");
let soRc = 0;
const RC = () => "77777777-7777-4777-8777-" + String(++soRc).padStart(12, "0");
const ENV = {
  A: {phap_nhan_id: PN, du_an_id: DA, hop_dong_id: HD, dot_id: DOT, kt_pending_id: PEND, phong_bi_id: PB_A, seal_id: U(6), version_id: U(7), ket_luan_id: U(8), pdf_id: U(9),
    phong_bi_sha256: "a".repeat(64), graph_sha256: "1".repeat(64), pdf_sha256: "4".repeat(64)},
  B: {phap_nhan_id: PN, du_an_id: DA, hop_dong_id: HD, dot_id: DOT, kt_pending_id: PEND, phong_bi_id: PB_B, seal_id: "6b6b6b6b-0000-4000-8000-00000000006b",
    version_id: "7b7b7b7b-0000-4000-8000-00000000007b", ket_luan_id: "8b8b8b8b-0000-4000-8000-00000000008b", pdf_id: "9b9b9b9b-0000-4000-8000-00000000009b",
    phong_bi_sha256: "b".repeat(64), graph_sha256: "2".repeat(64), pdf_sha256: "5".repeat(64)},
};
const AP = {trang_thai: "CHUA_TRIEN_KHAI_M4_03B", da_ghi_cong_no: false}, RQ = {trang_thai: "CHUA_NOI_M4_04"};
const TEP_VAT = [{id: TEP1, ten: "hoa_don_gtgt_dot_1.pdf", raw_sha256: "e".repeat(64), media_type: "application/pdf", byte_length: 2048},
  {id: TEP2, ten: "bang_ke_vat.xlsx", raw_sha256: "f".repeat(64), media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", byte_length: 4096}];
const NGUON = env => ({gia_tri_nt: "1000000", so_xin_thanh_toan: "900000", tam_ung: null, thu_hoi: "0", giu_lai: "50000", tien_te: "VND",
  dong: [{row_id: "R-01", ma_hm: "HM01", dvt: "m3", khoi_luong_chap_nhan: "40"}, {row_id: "R-02", ma_hm: "HM02", dvt: "m3", khoi_luong_chap_nhan: null}],
  pdf: {id: ENV[env].pdf_id, ten: "ho_so_thanh_toan_dot_1.pdf", media_type: "application/pdf", raw_sha256: ENV[env].pdf_sha256, byte_length: 9},
  tep_can_cu: sao(TEP_VAT)});
const KTO = (o = {}) => ({kt_revision_id: KTR(1), revision: 1, trang_thai: "CHO_XAC_NHAN", gia_tri_nt_xac_nhan: "1000000", tien_te: "VND", co_so_gia_tri: "TRUOC_VAT",
  tam_ung_xac_nhan: null, thu_hoi_xac_nhan: "0", giu_lai_xac_nhan: null, vat_trang_thai: "CO_CAN_CU", vat_can_cu_tep_id: TEP1, vat_trich_dan: "Trang 1, dòng tổng tiền thuế",
  ly_do: null, ...o});
const ROW_PB = (env, hien) => ({context: sao(ENV[env]), thu_tu: env === "A" ? 1 : 2, truoc_id: env === "A" ? null : PB_A, phien_ban_so: env === "A" ? 1 : 2, can_cu_hien_hanh: hien});
// o: env (A|B), coB (lịch sử có B — B hiện hành), khongHienHanh (nguồn mới chưa niêm phong: không row nào hiện hành), kt, lsKt [{env, kt}], quyen, them
function DTO(o = {}) {
  const env = o.env || "A", coB = !!o.coB || env === "B";
  const rows = [ROW_PB("A", !coB && !o.khongHienHanh)];
  if (coB) rows.push(ROW_PB("B", !o.khongHienHanh));
  const hien = rows.find(r => r.context.phong_bi_id === ENV[env].phong_bi_id).can_cu_hien_hanh;
  const kt = o.kt === undefined ? null : o.kt;
  const lsKt = o.lsKt || (kt ? [{env, kt}] : []);
  return {schema: SCHEMA, context: sao(ENV[env]), quyen: {xem: true, luu: hien, xac_nhan: hien, tai_pdf: true, ...(o.quyen || {})}, can_cu_hien_hanh: hien,
    nguon: NGUON(env), kt: kt && sao(kt), lich_su: {phong_bi: rows, kt: lsKt.map(r => ({context: sao(ENV[r.env]), kt: sao(r.kt)}))}, ap: sao(AP), request: sao(RQ),
    ...(o.them || {})};
}
const ACK = (env, kt, o = {}) => ({schema: SCHEMA, context: sao(ENV[env]), kt_revision_id: kt.kt_revision_id, revision: kt.revision, trang_thai: kt.trang_thai,
  lap_lai: false, receipt_id: RC(), ap: sao(AP), request: sao(RQ), ...o});
const DS = (items) => ({schema: SCHEMA, items: items || [{kt_pending_id: PEND, dot_id: DOT, phong_bi_id: PB_A, phong_bi_sha256: "a".repeat(64), revision: null,
  trang_thai: "CHO_XAC_NHAN", ap: sao(AP)}]});

const KT_LOGIN = "MO_PHONG_KE_TOAN_M4", KT2 = "MO_PHONG_KE_TOAN_M4_2";
const TONG_KT = login => ({cau_hinh: true, nguoi: {dang_nhap: login, vai_tro: "KE_TOAN"}, ghi_nguon: {san_sang: true, ly_do: null},
  pham_vi: [], hop_dong: [], dot: [], danh_muc_ho_so: [], nhanh_sau: [], tai_len_toi_da_byte: 52428800,
  danh_tinh_demo: [{dang_nhap: KT_LOGIN, vai_tro: "KE_TOAN"}, {dang_nhap: KT2, vai_tro: "KE_TOAN"}]});

class SetupError extends Error {}
const chuan = (dk, ma) => { if (!dk) throw new SetupError(ma); };
const KQ = {dat: [], hong: [], setup_errors: [], not_verified: []};
async function ca(ten, fn) {
  try { await fn(); KQ.dat.push(ten); console.log("ĐẠT  " + ten); }
  catch (e) {
    if (e instanceof SetupError) { KQ.setup_errors.push({ca: ten, ma: e.message}); console.log("SETUP " + ten + ": " + e.message); }
    else { KQ.hong.push({ca: ten, loi: String((e && e.stack) || e)}); console.log("HỎNG " + ten + ": " + (e && e.message)); }
  }
}

const NUT_LUU = "Lưu nháp kế toán", NUT_XN = "Xác nhận nghiệm thu", NUT_LAI = "Gửi lại y nguyên (cùng khóa)", NUT_TAI = "Tải PDF hồ sơ đợt ↓";
const NUT_XEM_PB = "Xem phong bì này", NUT_MOI_NHAT = "Về phong bì mới nhất";
const O_NT = "Giá trị NT xác nhận", O_TT = "Tiền tệ KT", O_VAT = "Trạng thái VAT", O_TEP = "Tệp căn cứ VAT", O_TRICH = "Trích dẫn căn cứ VAT", O_LY_DO = "Lý do / ghi chú KT";
const O_CO_SO = "Cơ sở giá trị";
const SRC_KT = "/m4/m4_ke_toan.js", URL_DS = "/api/m4/ke-toan", URL_LUU = "/api/m4/ke-toan/luu", URL_XN = "/api/m4/ke-toan/xac-nhan";
const URL_CT = (p, pb) => "/api/m4/ke-toan/" + p + (pb ? "?phong_bi_id=" + pb : "");
const URL_PDF = env => "/api/m4/ke-toan/" + PEND + "/phong-bi/" + ENV[env].phong_bi_id + "/pdf";
const KHOA_LUU = ["kt_pending_id", "phong_bi_id", "expected_phong_bi_sha256", "expected_revision", "gia_tri_nt_xac_nhan", "tien_te", "co_so_gia_tri", "tam_ung_xac_nhan",
  "thu_hoi_xac_nhan", "giu_lai_xac_nhan", "vat_trang_thai", "vat_can_cu_tep_id", "vat_trich_dan", "ly_do", "khoa"];
const KHOA_XN = ["kt_pending_id", "phong_bi_id", "kt_revision_id", "expected_revision", "expected_phong_bi_sha256", "khoa"];

// ------------------------------------------------------------------ một phiên shell thật: app.js + m4.js → vai CHỈ KE_TOAN (không phạm vi/HĐ) → chế độ KT
async function moPhien(opt = {}) {
  const {ctx, document, calls, wl} = moiTruong();
  const $ = id => document.getElementById(id);
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const lay = (pred, ma) => { const c = calls.find(x => !x.xong && pred(x)); chuan(c, ma); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const get = url => c => c.method === "GET" && c.url === url;
  const post = url => c => c.method === "POST" && c.url === url;
  const laGetKt = c => c.method === "GET" && c.url.startsWith("/api/m4/ke-toan");
  const laPostKt = c => c.method === "POST" && c.url.startsWith("/api/m4/ke-toan/");
  const laHd = c => c.url.startsWith("/api/m4/hop-dong") || c.url.startsWith("/api/m4/dot/");

  try { vm.runInContext(APP, ctx, {filename: "app.js"}); } catch (e) { throw new SetupError("SETUP_APP_JS: " + e.message); }
  chuan(ctx.window.kttChung, "SETUP_SEAM_KTTCHUNG");
  const soHashTruoc = (wl.hashchange || []).length;
  try { vm.runInContext(M4, ctx, {filename: "m4.js"}); } catch (e) { throw new SetupError("SETUP_M4_JS: " + e.message); }
  const ngheHashM4 = (wl.hashchange || []).slice(soHashTruoc);
  chuan(ngheHashM4.length > 0, "SETUP_HASHCHANGE_M4");
  for (const c of calls) if (c.url !== "/api/m4" && c.url !== "/api/m4/mau") { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND", message: "ngoài ca"})); }
  await chay();
  const tra = async (c, status, data, n) => { c.resolve(phanHoi(status, data, n)); await chay(); };
  async function traMau() { for (const c of calls.filter(x => !x.xong && get("/api/m4/mau")(x))) { c.xong = true; c.resolve(phanHoi(200, {mau: []})); } await chay(); }
  async function traTong(login) { lay(get("/api/m4"), "SETUP_ROUTE_GET_API_M4 " + login).resolve(phanHoi(200, TONG_KT(login))); await chay(); await traMau(); }
  const roiM4 = async () => { ctx.location.hash = "#hopdong"; for (const fn of ngheHashM4) fn({}); await chay(); };
  const scripts = () => document.head.children.filter(c => c.tagName === "SCRIPT" && c.src === SRC_KT);
  const chayKt = async () => { try { vm.runInContext(KT, ctx, {filename: "m4_ke_toan.js"}); } catch (e) { throw new SetupError("SETUP_KT_JS: " + e.message); } await chay(); };
  const vungKt = () => tim($("m4-kt"), e => !!e._cls && e._cls.has("m4-kt"));
  const chuKt = () => (vungKt() || {textContent: ""}).textContent;
  const statusKt = () => { const v = vungKt(), s = v && v.querySelector(".m4-kt-status"); return s ? s.textContent : ""; };
  const nutKt = s => nutTheoChu(vungKt(), s);
  const oKt = nhan => theoNhan(vungKt(), nhan);
  const go = (nhan, v) => { const e = oKt(nhan); chuan(e && e.isConnected, "SETUP_DOM_O " + nhan); e.value = v; e.dispatch("input"); return e; };
  const chonSel = async (nhan, v) => { const e = oKt(nhan); chuan(e && e.isConnected, "SETUP_DOM_SELECT " + nhan); e.value = v; e.dispatch("change"); await chay(); };
  const bam = async s => { const b = nutKt(s); assert.ok(b, "không có nút " + s); b.click(); await chay(); return b; };
  const bamEp = async s => { const b = nutKt(s); assert.ok(b, "không có nút " + s); b.disabled = false; b.click(); await chay(); };  // gọi thẳng handler
  const toast = () => ($("toast") || {textContent: ""}).textContent;
  const bodyCua = c => JSON.parse(c.opts.body);
  async function moHoSo(dto, moTa) {  // bấm "Mở" ở hộp chờ → GET chi tiết không query → trả dto
    const b = nutDung(vungKt(), "Mở"); chuan(b, "SETUP_DOM_NUT_MO");
    b.click(); await chay();
    await tra(lay(get(URL_CT(PEND)), "SETUP_ROUTE_GET_CT " + (moTa || "")), 200, dto);
  }
  const giuBlob = c => { let tha = null; c.resolve({ok: true, status: 200, headers: {get: () => "application/pdf"}, json: async () => ({}),
    blob: () => new Promise(r => { tha = r; })}); return () => tha; };

  await traTong(opt.login || KT_LOGIN);
  chuan($("m4-nguoi") && $("m4-nguoi").textContent.includes(opt.login || KT_LOGIN), "SETUP_DOM_M4_NGUOI");
  const cd = $("m4-cd-ke-toan");
  chuan(cd && cd.textContent === "Kế toán nghiệm thu", "SETUP_DOM_DIEM_VAO_KT");
  cd.click(); await chay();
  chuan(scripts().length === 1, "SETUP_SCRIPT_KT_KHONG_TAI");
  const P = {ctx, calls, $, cho, lay, dem, get, post, laGetKt, laPostKt, laHd, tra, traTong, roiM4, scripts, chayKt, vungKt, chuKt, statusKt, nutKt, oKt, go, chonSel,
    bam, bamEp, toast, bodyCua, moHoSo, giuBlob, ngheHashM4};
  if (opt.khongChay) return P;
  await chayKt();
  chuan(ctx.window.kttM4KeToan, "SETUP_KT_KHONG_CONG_BO");
  if (opt.khongDs) return P;
  await tra(lay(get(URL_DS), "SETUP_ROUTE_GET_DS"), 200, opt.ds || DS());
  return P;
}
function chup(P) {
  return {toast: P.toast(), status: P.statusKt(), get: P.dem(P.laGetKt), post: P.dem(P.laPostKt), fetch: P.calls.length, click: soClickTai,
    o: P.oKt(O_NT), oVal: P.oKt(O_NT) && P.oKt(O_NT).value, chu: P.chuKt()};
}
function khongDoi(P, t, ten) {
  assert.strictEqual(P.toast(), t.toast, ten + ": phản hồi cũ toast");
  assert.strictEqual(P.statusKt(), t.status, ten + ": phản hồi cũ đổi trạng thái");
  assert.strictEqual(P.dem(P.laGetKt), t.get, ten + ": phản hồi cũ kích GET");
  assert.strictEqual(P.dem(P.laPostKt), t.post, ten + ": phản hồi cũ kích POST");
  assert.strictEqual(P.calls.length, t.fetch, ten + ": phản hồi cũ kích yêu cầu mạng");
  assert.strictEqual(soClickTai, t.click, ten + ": phản hồi cũ click tải");
  assert.strictEqual(P.oKt(O_NT), t.o, ten + ": phản hồi cũ thay ô nhập (vẽ lại form)");
  assert.strictEqual(P.chuKt(), t.chu, ten + ": phản hồi cũ đổi DOM");
}
const coSaiDto = P => /không đúng hợp đồng/.test(P.chuKt());

async function main() {
  // ================================================================ E — điểm vào KT riêng, tải lười, chưa compose
  await ca("E01 vai chỉ KE_TOAN: không phạm vi/HĐ portal vẫn mở được hộp chờ; Mở → GET chi tiết không query; 0 GET HĐ/đợt", async () => {
    const P = await moPhien();
    assert.strictEqual(P.dem(P.laHd), 0, "điểm vào KT không được đọc HĐ/đợt portal");
    assert.strictEqual(P.$("m4-kt").hidden, false, "vùng KT phải hiện");
    assert.strictEqual(P.$("m4-luoi").hidden, true, "lưới HĐ phải ẩn ở chế độ KT");
    assert.ok(P.chuKt().includes("Hộp chờ kế toán nghiệm thu") && P.chuKt().includes("chưa có"), "danh sách hiện revision null là 'chưa có'");
    await P.moHoSo(DTO(), "E01");
    assert.ok(P.chuKt().includes("Số nguồn đã niêm phong"), "chi tiết phải hiện nguồn");
    assert.ok(P.chuKt().includes("Căn cứ hiện hành"));
    assert.strictEqual(P.dem(P.laHd), 0);
    assert.strictEqual(P.dem(P.laPostKt), 0, "đọc không được kích lệnh");
  });
  await ca("E02 tài sản /m4/m4_ke_toan.js lỗi tải → 'Chưa nối màn Kế toán nghiệm thu', 0 GET KT", async () => {
    const P = await moPhien({khongChay: true});
    const s = P.scripts()[0];
    s.onerror(); await chay();
    assert.ok(P.$("m4-kt").textContent.includes("Chưa nối màn Kế toán nghiệm thu"));
    assert.strictEqual(P.dem(P.laGetKt), 0);
  });
  await ca("E03 backend chưa compose: 503 M4_KT_CHUA_NOI ở danh sách và chi tiết → CHUA_NOI, không lệnh, 0 POST", async () => {
    const P = await moPhien({khongDs: true});
    await P.tra(P.cho(P.get(URL_DS), "ds"), 503, {error: "M4_KT_CHUA_NOI", message: "Chưa nối backend kế toán nghiệm thu (M4-03A)"});
    assert.ok(P.chuKt().includes("Chưa nối backend kế toán nghiệm thu"));
    assert.ok(!nutDung(P.vungKt(), "Mở") && !P.nutKt(NUT_LUU) && !P.nutKt(NUT_XN));
    const Q = await moPhien();
    nutDung(Q.vungKt(), "Mở").click(); await chay();
    await Q.tra(Q.cho(Q.get(URL_CT(PEND)), "ct"), 503, {error: "M4_KT_CHUA_NOI", message: "x"});
    assert.ok(Q.chuKt().includes("Chưa nối backend kế toán nghiệm thu") && !Q.nutKt(NUT_LUU));
    assert.strictEqual(Q.dem(Q.laPostKt), 0);
  });

  // ================================================================ P01/P02 — kt=null, lưu nháp đầu, null ≠ "0"
  await ca("P01 kt=null: không tự chép nguồn; Lưu gửi expected_revision 0 + body đúng allowlist/thứ tự; Xác nhận tắt; ACK hợp lệ → toast + GET lại", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO(), "P01");
    assert.ok(P.chuKt().includes("kt = null"));
    assert.strictEqual(P.oKt(O_NT).value, "", "không tự chép số nguồn 1000000 thành số KT");
    assert.ok(P.nutKt(NUT_XN).disabled, "không xác nhận từ kt null");
    P.go(O_NT, "1000000"); P.go(O_TT, "VND");
    await P.bam(NUT_LUU);
    const c = P.cho(P.post(URL_LUU), "luu");
    const b = P.bodyCua(c);
    assert.deepStrictEqual(Object.keys(b), KHOA_LUU, "thứ tự/allowlist body lưu");
    assert.deepStrictEqual({...b, khoa: undefined}, {kt_pending_id: PEND, phong_bi_id: PB_A, expected_phong_bi_sha256: "a".repeat(64), expected_revision: 0,
      gia_tri_nt_xac_nhan: "1000000", tien_te: "VND", co_so_gia_tri: "CHUA_RO", tam_ung_xac_nhan: null, thu_hoi_xac_nhan: null, giu_lai_xac_nhan: null,
      vat_trang_thai: "CHUA_DU", vat_can_cu_tep_id: null, vat_trich_dan: null, ly_do: null, khoa: undefined});
    assert.ok(/^m4kt-/.test(b.khoa));
    const kt1 = KTO({vat_trang_thai: "CHUA_DU", vat_can_cu_tep_id: null, vat_trich_dan: null, co_so_gia_tri: "CHUA_RO", thu_hoi_xac_nhan: null});
    await P.tra(c, 200, ACK("A", kt1));
    assert.ok(P.toast().includes("Đã lưu nháp kế toán · revision 1"));
    await P.tra(P.cho(P.get(URL_CT(PEND)), "GET sau lưu"), 200, DTO({kt: kt1}));
    assert.ok(P.chuKt().includes("Revision đã lưu 1"));
  });
  await ca("P02 null ≠ \"0\": bảng và ô nhập phân biệt (thiếu) với 0; nguồn null hiện (thiếu)", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO({kt: KTO({thu_hoi_xac_nhan: "0", tam_ung_xac_nhan: null})}), "P02");
    assert.strictEqual(P.oKt("Thu hồi xác nhận").value, "0");
    assert.strictEqual(P.oKt("Tạm ứng xác nhận").value, "");
    const tr = tim(P.vungKt(), e => e.tagName === "TR" && e.children[0] && e.children[0].textContent === "Tạm ứng xác nhận");
    assert.ok(tr && tr.children[1].textContent === "(thiếu)" && tr.children[2].textContent === "(thiếu)", "tạm ứng nguồn null + KT null");
    const tr2 = tim(P.vungKt(), e => e.tagName === "TR" && e.children[0] && e.children[0].textContent === "Thu hồi xác nhận");
    assert.ok(tr2 && tr2.children[1].textContent === "0" && tr2.children[2].textContent === "0", "0 hiện là 0");
    P.go("Tạm ứng xác nhận", ""); P.go("Thu hồi xác nhận", "0");
    await P.bam(NUT_LUU);
    const b = P.bodyCua(P.cho(P.post(URL_LUU), "luu"));
    assert.strictEqual(b.tam_ung_xac_nhan, null); assert.strictEqual(b.thu_hoi_xac_nhan, "0"); assert.strictEqual(b.expected_revision, 1);
  });
  await ca("P02b số không hợp lệ (dấu phẩy/0 thừa/âm) → 0 POST", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO(), "P02b");
    for (const v of ["1,000", "100.50", "-5", "1e6"]) { P.go(O_NT, v); await P.bam(NUT_LUU); }
    assert.strictEqual(P.dem(P.laPostKt), 0);
  });

  // ================================================================ P03/P04 — CO_CAN_CU và KHONG_AP_DUNG
  await ca("P03a CO_CAN_CU qua UI: chọn đúng id tệp thật + trích dẫn → body mang exact id; không mang hash/path", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO(), "P03a");
    P.go(O_NT, "1000000"); P.go(O_TT, "VND");
    await P.chonSel(O_CO_SO, "TRUOC_VAT");
    await P.chonSel(O_VAT, "CO_CAN_CU");
    const sel = P.oKt(O_TEP);
    assert.ok(sel, "nhánh CO phải hiện danh sách tệp thật");
    const ops = sel.children.filter(o => o.tagName === "OPTION").map(o => o.value);
    assert.deepStrictEqual(ops, ["", TEP1, TEP2], "đúng id từ nguon.tep_can_cu — không fake, không PDF hồ sơ đợt");
    await P.chonSel(O_TEP, TEP1); P.go(O_TRICH, "Trang 1, dòng tổng tiền thuế");
    await P.bam(NUT_LUU);
    const b = P.bodyCua(P.cho(P.post(URL_LUU), "luu"));
    assert.strictEqual(b.vat_trang_thai, "CO_CAN_CU"); assert.strictEqual(b.vat_can_cu_tep_id, TEP1); assert.strictEqual(b.vat_trich_dan, "Trang 1, dòng tổng tiền thuế");
    assert.ok(!("raw_sha256" in b) && !("object_key" in b));
  });
  await ca("P03b CO đã lưu → Xác nhận body đúng 6 khóa (không tiền); ACK → 'chờ ghi công nợ'; AP/Request trung thực; không nút ghi/gửi", async () => {
    const P = await moPhien();
    const kt = KTO();
    await P.moHoSo(DTO({kt}), "P03b");
    assert.ok(!P.nutKt(NUT_XN).disabled, "CO thật đủ điều kiện phải xác nhận được: " + P.statusKt());
    await P.bam(NUT_XN);
    const c = P.cho(P.post(URL_XN), "xn");
    const b = P.bodyCua(c);
    assert.deepStrictEqual(Object.keys(b), KHOA_XN);
    assert.deepStrictEqual({...b, khoa: undefined}, {kt_pending_id: PEND, phong_bi_id: PB_A, kt_revision_id: KTR(1), expected_revision: 1,
      expected_phong_bi_sha256: "a".repeat(64), khoa: undefined});
    const ktX = KTO({kt_revision_id: KTR(2), revision: 2, trang_thai: "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO"});
    await P.tra(c, 200, ACK("A", ktX));
    assert.ok(P.toast().includes("Đã xác nhận nghiệm thu — chờ ghi công nợ"));
    await P.tra(P.cho(P.get(URL_CT(PEND)), "GET sau xn"), 200, DTO({kt: ktX, lsKt: [{env: "A", kt}, {env: "A", kt: ktX}], quyen: {luu: false, xac_nhan: false}}));
    const t = P.chuKt();
    assert.ok(t.includes("Đã xác nhận nghiệm thu — chờ ghi công nợ") && t.includes("Chưa triển khai (M4-03B)") && t.includes("Chưa nối (M4-04)"));
    assert.ok(!P.nutKt(NUT_LUU) && !P.nutKt(NUT_XN));
    assert.ok(!nutTheoChu(P.vungKt(), "Ghi công nợ") && !nutTheoChu(P.vungKt(), "Request") && !/đã ghi công nợ:\s*có/i.test(t));
  });
  await ca("P04 KHONG_AP_DUNG có lý do → xác nhận gửi; thiếu lý do → nút tắt + gọi thẳng 0 POST", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO({kt: KTO({vat_trang_thai: "KHONG_AP_DUNG", vat_can_cu_tep_id: null, vat_trich_dan: null, ly_do: null})}), "P04 thiếu");
    assert.ok(P.nutKt(NUT_XN).disabled && /lý do/.test(P.nutKt(NUT_XN).title));
    await P.bamEp(NUT_XN);
    assert.strictEqual(P.dem(P.laPostKt), 0);
    const Q = await moPhien();
    await Q.moHoSo(DTO({kt: KTO({vat_trang_thai: "KHONG_AP_DUNG", vat_can_cu_tep_id: null, vat_trich_dan: null, ly_do: "Hợp đồng không chịu thuế theo điều 5"})}), "P04 có");
    await Q.bam(NUT_XN);
    assert.strictEqual(Q.bodyCua(Q.cho(Q.post(URL_XN), "xn")).kt_revision_id, KTR(1));
  });
  await ca("P04b CHUA_DU / CHUA_RO / tiền tệ khác nguồn / số khác nguồn không lý do → xác nhận tắt, 0 POST", async () => {
    for (const [ten, kt] of [["CHUA_DU", KTO({vat_trang_thai: "CHUA_DU", vat_can_cu_tep_id: null, vat_trich_dan: null})], ["CHUA_RO", KTO({co_so_gia_tri: "CHUA_RO"})],
      ["USD", KTO({tien_te: "USD"})], ["khác nguồn", KTO({gia_tri_nt_xac_nhan: "990000"})], ["tệp ngoài danh sách", KTO({vat_can_cu_tep_id: "7d7d7d7d-0000-4000-8000-00000000007d"})]]) {
      const P = await moPhien();
      await P.moHoSo(DTO({kt}), ten);
      assert.ok(P.nutKt(NUT_XN).disabled, ten + ": xác nhận phải tắt");
      await P.bamEp(NUT_XN);
      assert.strictEqual(P.dem(P.laPostKt), 0, ten);
    }
  });

  // ================================================================ P05 — metadata tệp căn cứ
  await ca("P05 tep_can_cu vắng → HOLD (chỉ đọc, 0 POST); sai kiểu (object_key) → SAI_DTO; rỗng → CO tắt + ghi chú không phải 'không VAT'", async () => {
    const d = DTO({kt: KTO()}); delete d.nguon.tep_can_cu;
    const P = await moPhien();
    await P.moHoSo(d, "vắng");
    assert.ok(P.chuKt().includes("Phụ thuộc backend") && P.chuKt().includes("Số nguồn đã niêm phong"), "HOLD hiện chỉ đọc");
    await P.bamEp(NUT_LUU); await P.bamEp(NUT_XN);
    assert.strictEqual(P.dem(P.laPostKt), 0);
    assert.strictEqual(P.oKt(O_NT).value, "1000000", "nháp giữ");
    const d2 = DTO(); d2.nguon.tep_can_cu[0].object_key = "kho/x.pdf";
    const Q = await moPhien();
    await Q.moHoSo(d2, "sai kiểu");
    assert.ok(coSaiDto(Q) && !Q.nutKt(NUT_LUU));
    const d3 = DTO(); d3.nguon.tep_can_cu = [];
    const R = await moPhien();
    await R.moHoSo(d3, "rỗng");
    const opCo = R.oKt(O_VAT).children.find(o => o.value === "CO_CAN_CU");
    assert.ok(opCo && opCo.disabled, "rỗng → không chọn được CO");
    assert.ok(R.chuKt().includes("KHÔNG có nghĩa là không áp dụng VAT"));
  });

  // ================================================================ P06 — revision canonical
  await ca("P06 đột biến kt canonical (vắng revision/bool/chuỗi/0/alias kt.id/{}/vắng kt) → không lệnh, 0 POST; baseline mở lệnh", async () => {
    const dot = [
      ["vắng revision", k => { delete k.revision; return k; }], ["revision bool", k => ({...k, revision: true})], ["revision chuỗi", k => ({...k, revision: "1"})],
      ["revision 0", k => ({...k, revision: 0})], ["alias kt.id", k => { const x = {...k, id: k.kt_revision_id}; delete x.kt_revision_id; return x; }], ["{}", () => ({})]];
    for (const [ten, f] of dot) {
      const d = DTO({kt: KTO()}); d.kt = f(sao(d.kt));
      const P = await moPhien();
      await P.moHoSo(d, ten);
      assert.ok(coSaiDto(P) && P.chuKt().includes("kt canonical"), ten + ": phải chặn");
      assert.ok(!P.nutKt(NUT_LUU) && !P.nutKt(NUT_XN), ten);
      assert.strictEqual(P.dem(P.laPostKt), 0, ten);
    }
    const d = DTO(); delete d.kt;
    const P = await moPhien();
    await P.moHoSo(d, "vắng kt");
    assert.ok(coSaiDto(P) && !P.nutKt(NUT_LUU), "vắng kt ≠ kt null");
    const Q = await moPhien();
    await Q.moHoSo(DTO({kt: KTO()}), "baseline");
    assert.ok(!Q.nutKt(NUT_LUU).disabled && !Q.nutKt(NUT_XN).disabled, "baseline typed phải mở lệnh");
  });

  // ================================================================ P07/P08/P09 — hai phong bì, lịch sử
  await ca("P07 hai phong bì: B hiện hành kt=null (không mượn KT của A); selector GET ?phong_bi_id=row.context; A chỉ đọc; Về mới nhất GET không query", async () => {
    const ktA = KTO();
    const P = await moPhien();
    await P.moHoSo(DTO({env: "B", kt: null, lsKt: [{env: "A", kt: ktA}]}), "B");
    assert.ok(P.chuKt().includes("kt = null"), "kt của B không mượn A");
    await P.bam(NUT_XEM_PB);
    const c = P.cho(P.get(URL_CT(PEND, PB_A)), "GET lịch sử A đúng phong_bi_id của row.context");
    await P.tra(c, 200, DTO({env: "A", coB: true, kt: ktA, lsKt: [{env: "A", kt: ktA}]}));
    assert.ok(P.chuKt().includes("Lịch sử — chỉ đọc"));
    assert.ok(!P.nutKt(NUT_LUU) && !P.nutKt(NUT_XN), "A lịch sử không có lệnh");
    await P.bam(NUT_MOI_NHAT);
    P.cho(P.get(URL_CT(PEND)), "về mới nhất không query");
    const d = DTO({env: "B", kt: sao(ktA), lsKt: [{env: "A", kt: ktA}]});
    const Q = await moPhien();
    await Q.moHoSo(d, "B mượn kt A");
    assert.ok(coSaiDto(Q), "top kt phải là revision của chính phong bì đang xem");
  });
  await ca("P07b phản hồi lịch sử trả phong bì khác phong_bi_id đã chọn → SAI_DTO", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO({env: "B"}), "B");
    await P.bam(NUT_XEM_PB);
    await P.tra(P.cho(P.get(URL_CT(PEND, PB_A)), "A"), 200, DTO({env: "B"}));
    assert.ok(coSaiDto(P));
  });
  await ca("P08 nguồn mới chưa niêm phong: không row hiện hành → không lệnh; quyền lệnh trên phong bì không hiện hành → SAI_DTO", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO({env: "B", khongHienHanh: true, kt: KTO(), lsKt: [{env: "B", kt: KTO()}]}), "P08");
    assert.ok(P.chuKt().includes("Không còn hiện hành") && !P.nutKt(NUT_LUU) && !P.nutKt(NUT_XN));
    const Q = await moPhien();
    await Q.moHoSo(DTO({env: "B", khongHienHanh: true, quyen: {luu: true}}), "P08 quyền sai");
    assert.ok(coSaiDto(Q));
  });
  await ca("P09 lịch sử KT append-only hiển thị đúng thứ tự; đảo thứ tự/trùng → SAI_DTO; lich_su dạng mảng → SAI_DTO", async () => {
    const k1 = KTO(), k2 = KTO({kt_revision_id: KTR(2), revision: 2, gia_tri_nt_xac_nhan: "999999", ly_do: "điều chỉnh"});
    const P = await moPhien();
    await P.moHoSo(DTO({kt: k2, lsKt: [{env: "A", kt: k1}, {env: "A", kt: k2}]}), "P09");
    assert.ok(P.chuKt().includes("Lịch sử revision kế toán") && P.chuKt().includes("999999"));
    const Q = await moPhien();
    await Q.moHoSo(DTO({kt: k2, lsKt: [{env: "A", kt: k2}, {env: "A", kt: k1}]}), "đảo");
    assert.ok(coSaiDto(Q));
    const d = DTO(); d.lich_su = [];
    const R = await moPhien();
    await R.moHoSo(d, "mảng");
    assert.ok(coSaiDto(R));
  });

  // ================================================================ P10 — thu hồi
  await ca("P10 thu hồi: GET 403 / 200 xem=false / POST 403 / danh sách 403 → gỡ bằng chứng + nháp ngay, không lệnh", async () => {
    for (const kieu of ["GET403", "XEM_FALSE", "POST403", "DS403"]) {
      const P = await moPhien();
      await P.moHoSo(DTO({kt: KTO()}), kieu);
      P.go(O_NT, "123");
      if (kieu === "GET403") { await P.bam("↻ Làm mới"); await P.tra(P.cho(P.get(URL_CT(PEND)), "lm"), 403, {error: "M4_KT_KHONG_QUYEN", message: "Không có quyền"}); }
      if (kieu === "XEM_FALSE") { await P.bam("↻ Làm mới"); await P.tra(P.cho(P.get(URL_CT(PEND)), "lm"), 200, {schema: SCHEMA, quyen: {xem: false, luu: false, xac_nhan: false, tai_pdf: false}}); }
      if (kieu === "POST403") { await P.bam(NUT_LUU); await P.tra(P.cho(P.post(URL_LUU), "luu"), 403, {error: "M4_KT_KHONG_QUYEN", message: "Không có quyền"}); }
      if (kieu === "DS403") { await P.bam("↻ Làm mới danh sách"); await P.tra(P.cho(P.get(URL_DS), "ds"), 403, {error: "M4_KT_KHONG_QUYEN", message: "Không có quyền"}); }
      const t = P.chuKt();
      assert.ok(!t.includes("Số nguồn đã niêm phong") && !t.includes("1000000"), kieu + ": còn bằng chứng");
      assert.ok(!P.oKt(O_NT) && !P.nutKt(NUT_LUU) && !P.nutKt(NUT_XN), kieu + ": còn form/lệnh");
    }
  });
  await ca("P10b blob đang giữ khi bị thu hồi (GET 403) → 0 click", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO(), "pdf");
    await P.bam(NUT_TAI);
    const tha = P.giuBlob(P.cho(P.get(URL_PDF("A")), "pdf")); await chay();
    await P.bam("↻ Làm mới"); await P.tra(P.cho(P.get(URL_CT(PEND)), "lm"), 403, {error: "M4_KT_KHONG_QUYEN", message: "x"});
    const truoc = soClickTai;
    tha()(BLOB_GOC ? new BLOB_GOC([new Uint8Array(9)]) : {size: 9}); await chay();
    assert.strictEqual(soClickTai, truoc);
  });

  // ================================================================ P11 — UNKNOWN
  await ca("P11 mất kết nối khi lưu → CHƯA RÕ; lệnh mới bị chặn; sửa nháp; Gửi lại y nguyên cùng body/khóa; ACK về → nháp mới hơn giữ", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO(), "P11");
    P.go(O_NT, "1000000"); P.go(O_TT, "VND");
    await P.bam(NUT_LUU);
    const c1 = P.cho(P.post(URL_LUU), "luu 1");
    c1.reject(new TypeError("mất mạng")); await chay();
    assert.ok(P.statusKt().includes("Chưa rõ kết quả"));
    assert.ok(P.nutKt(NUT_LUU).disabled, "lệnh mới cùng hồ sơ bị chặn");
    await P.bamEp(NUT_LUU);
    assert.strictEqual(P.dem(P.laPostKt), 1, "không gửi lệnh mới khi đang chưa rõ");
    P.go(O_NT, "1000001");  // nháp mới hơn
    await P.bam(NUT_LAI);
    const c2 = P.cho(P.post(URL_LUU), "gửi lại");
    assert.strictEqual(c2.opts.body, c1.opts.body, "Gửi lại phải y nguyên từng byte (cùng khóa, không lấy form mới)");
    const kt1 = KTO({vat_trang_thai: "CHUA_DU", vat_can_cu_tep_id: null, vat_trich_dan: null, co_so_gia_tri: "CHUA_RO", thu_hoi_xac_nhan: null});
    await P.tra(c2, 200, ACK("A", kt1, {lap_lai: true}));
    assert.ok(P.toast().includes("biên nhận cũ của cùng khóa"));
    await P.tra(P.cho(P.get(URL_CT(PEND)), "GET sau"), 200, DTO({kt: kt1}));
    assert.strictEqual(P.oKt(O_NT).value, "1000001", "ACK cũ không xóa nháp mới hơn");
  });
  await ca("P11b 2xx sai hợp đồng (revision 0 / context khác / ap sai) → CHƯA RÕ, không toast thành công, không GET", async () => {
    for (const [ten, sua] of [["revision0", a => ({...a, revision: 0})], ["context B", a => ({...a, context: sao(ENV.B)})],
      ["ap đã ghi", a => ({...a, ap: {trang_thai: "CHUA_TRIEN_KHAI_M4_03B", da_ghi_cong_no: true}})], ["xn chưa xác nhận", a => a]]) {
      const P = await moPhien();
      await P.moHoSo(DTO({kt: KTO()}), ten);
      const xn = ten === "xn chưa xác nhận";
      if (!xn) P.go(O_LY_DO, "ghi chú");
      await P.bam(xn ? NUT_XN : NUT_LUU);
      const c = P.cho(P.post(xn ? URL_XN : URL_LUU), ten);
      const g = P.dem(P.laGetKt);
      await P.tra(c, 200, sua(ACK("A", KTO({kt_revision_id: KTR(2), revision: 2}))));
      assert.ok(P.statusKt().includes("Chưa rõ kết quả") && !P.toast().includes("Đã lưu") && !P.toast().includes("Đã xác nhận"), ten);
      assert.strictEqual(P.dem(P.laGetKt), g, ten + ": không GET");
      assert.ok(P.nutKt(NUT_LAI), ten + ": phải có Gửi lại");
    }
  });
  await ca("P11c chưa rõ rồi mất quyền lưu (GET quyen.luu=false) → Gửi lại tắt + gọi thẳng 0 POST; bản ghi giữ", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO(), "P11c");
    P.go(O_NT, "5");
    await P.bam(NUT_LUU);
    P.cho(P.post(URL_LUU), "luu").resolve(phanHoi(502, {error: "M4_KET_QUA_CHUA_RO", message: "x"})); await chay();
    await P.bam("↻ Làm mới");
    await P.tra(P.cho(P.get(URL_CT(PEND)), "lm"), 200, DTO({quyen: {luu: false, xac_nhan: false}}));
    assert.ok(P.nutKt(NUT_LAI) && P.nutKt(NUT_LAI).disabled);
    await P.bamEp(NUT_LAI);
    assert.strictEqual(P.dem(P.laPostKt), 1);
  });

  // ================================================================ P12 — phản hồi giữ về muộn
  await ca("P12 ACK giữ về muộn sau A→B→A (lịch sử rồi về mới nhất) → 0 hiệu ứng", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO({coB: false}), "A");
    P.go(O_NT, "7"); P.go(O_TT, "VND");
    await P.bam(NUT_LUU);
    const giu = P.cho(P.post(URL_LUU), "luu giữ");
    await P.bam("↻ Làm mới");
    await P.tra(P.cho(P.get(URL_CT(PEND)), "B mới"), 200, DTO({env: "B"}));
    await P.bam(NUT_XEM_PB);
    await P.tra(P.cho(P.get(URL_CT(PEND, PB_A)), "A lịch sử"), 200, DTO({env: "A", coB: true}));
    await P.bam(NUT_MOI_NHAT);
    await P.tra(P.cho(P.get(URL_CT(PEND)), "về B"), 200, DTO({env: "B"}));
    P.go(O_NT, "8");
    const t = chup(P);
    await P.tra(giu, 200, ACK("A", KTO({vat_trang_thai: "CHUA_DU", vat_can_cu_tep_id: null, vat_trich_dan: null})));
    khongDoi(P, t, "ACK A về sau A→B→A");
  });
  await ca("P12b GET chi tiết giữ về sau khi rời #m4 / sau đổi vai → 0 DOM; vai mới tự đọc lại hộp chờ của chính nó", async () => {
    const P = await moPhien();
    nutDung(P.vungKt(), "Mở").click(); await chay();
    const giu = P.cho(P.get(URL_CT(PEND)), "ct giữ");
    await P.roiM4();
    const t = chup(P);
    await P.tra(giu, 200, DTO());
    khongDoi(P, t, "GET về sau rời #m4");
    const Q = await moPhien();
    await Q.moHoSo(DTO(), "Q");
    await Q.bam(NUT_LUU);
    const giuQ = Q.cho(Q.post(URL_LUU), "luu");
    Q.$("m4-lam-moi").click(); await chay();
    await Q.traTong(KT2);
    await Q.tra(Q.cho(Q.get(URL_DS), "ds vai mới"), 200, DS([]));
    assert.ok(Q.chuKt().includes("Hộp chờ trống") && !Q.chuKt().includes("Số nguồn đã niêm phong"), "vai mới không thấy bằng chứng vai cũ");
    const t2 = chup(Q);
    await Q.tra(giuQ, 200, ACK("A", KTO()));
    khongDoi(Q, t2, "ACK vai cũ về sau đổi vai");
  });
  await ca("PDF: đúng độ dài → tải 1; sai độ dài → 0; blob giữ rồi rời #m4 → 0 click", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO(), "pdf");
    let tr = soClickTai;
    await P.bam(NUT_TAI); await P.tra(P.cho(P.get(URL_PDF("A")), "pdf"), 200, {}, 9);
    assert.strictEqual(soClickTai, tr + 1);
    tr = soClickTai;
    await P.bam(NUT_TAI); await P.tra(P.cho(P.get(URL_PDF("A")), "pdf sai"), 200, {}, 8);
    assert.strictEqual(soClickTai, tr);
    await P.bam(NUT_TAI);
    const tha = P.giuBlob(P.cho(P.get(URL_PDF("A")), "pdf giữ")); await chay();
    await P.roiM4();
    tr = soClickTai;
    tha()(BLOB_GOC ? new BLOB_GOC([new Uint8Array(9)]) : {size: 9}); await chay();
    assert.strictEqual(soClickTai, tr);
  });
  await ca("P13 409 khi lưu → GET lại có fence, nháp giữ nguyên", async () => {
    const P = await moPhien();
    await P.moHoSo(DTO({kt: KTO()}), "409");
    P.go(O_NT, "1000002"); P.go(O_LY_DO, "khác nguồn");
    await P.bam(NUT_LUU);
    await P.tra(P.cho(P.post(URL_LUU), "luu"), 409, {error: "M4_KT_DA_DOI", message: "Revision đã đổi"});
    const k2 = KTO({kt_revision_id: KTR(2), revision: 2});
    await P.tra(P.cho(P.get(URL_CT(PEND)), "GET sau 409"), 200, DTO({kt: k2, lsKt: [{env: "A", kt: KTO()}, {env: "A", kt: k2}]}));
    assert.strictEqual(P.oKt(O_NT).value, "1000002");
    assert.ok(P.chuKt().includes("Revision đã lưu 2"));
  });

  // ================================================================ P2 — kiemChuaNop (m4_duyet_pdf.js thật)
  const CHUA_NOP = () => ({schema: "M4_DUYET_PDF_V1",  // MIRROR literal của duyet_dot.py:432–440 (biến thể CHUA_NOP) — không phải producer output
    quyen: {xem: true, ket_luan: false, duyet: false, tai_pdf: false, phien_ban: false}, dot: {so_dot: 1, ngay_nghiem_thu: "2026-03-01", trang_thai: "NHAP", so_hop_dong: "SO-1"},
    phien_ban: [], lich_su: [], context: {dot_id: "dot-1", hop_dong_id: "hd-1", du_an_id: "da1", phap_nhan_id: PN, version_id: null, revision: 0, basis_sha256: null},
    trang_thai: "CHUA_NOP", chua_nop: true, phien_ban_hien_hanh: false, do_thi: null, ly_do_trang_thai: "Đợt chưa nộp chính thức (M17)",
    can_cu: [], tep_can_cu: [], tep_can_cu_ly_do: "Chưa nộp", review_refs: [], coverage: {}, phat_hien: [], dong_nt: [], ket_luan: null, ket_luan_lich_su: [],
    quyet_dinh: null, pdf: null, pdf_lich_su: [], seal: null,
    kt: {trang_thai: "CHUA_CHUYEN", pending_id: null, phong_bi_id: null, phong_bi_hien_hanh: false, goc_id: null, phong_bi: [], ly_do: "Chưa nộp"},
    request: {trang_thai: "CHO_PDF", ly_do: "Chưa nộp"}});
  async function chayDp(dto) {
    const {ctx, document, calls} = moiTruong();
    try { vm.runInContext(APP, ctx, {filename: "app.js"}); vm.runInContext(DP, ctx, {filename: "m4_duyet_pdf.js"}); } catch (e) { throw new SetupError("SETUP_DP: " + e.message); }
    chuan(ctx.window.kttM4DuyetPdf, "SETUP_DP_KHONG_CONG_BO");
    for (const c of calls) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
    const vung = document.createElement("div"); vung.className = "m4-dp"; document.body.append(vung);
    ctx.window.kttM4DuyetPdf.ve(vung, {nguoi: "MO_PHONG_REVIEW_M4", phapNhanId: PN, duAnId: "da1", hdId: "hd-1", dotId: "dot-1", soHd: "SO-1", dots: []});
    await chay();
    const c = calls.find(x => !x.xong && x.method === "GET" && x.url === "/api/m4/duyet?dot_id=dot-1");
    chuan(c, "SETUP_DP_GET");
    c.xong = true; c.resolve(phanHoi(200, dto)); await chay();
    return {chu: vung.textContent, post: calls.filter(x => x.method === "POST").length, nutLuu: !!nutTheoChu(vung, "Lưu kết luận")};
  }
  await ca("P2-0 baseline CHUA_NOP (shape producer) vẫn hiện 'Chưa nộp hồ sơ đợt'", async () => {
    const r = await chayDp(CHUA_NOP());
    assert.ok(r.chu.includes("Chưa nộp hồ sơ đợt") && !r.chu.includes("không đúng hợp đồng"));
  });
  for (const [ten, sua, lyDo] of [
    ["P2-1a do_thi khác null", d => { d.do_thi = {nut: []}; }, "chưa nộp mà có đồ thị căn cứ"],
    ["P2-1b phien_ban_hien_hanh khác false", d => { d.phien_ban_hien_hanh = true; }, "chưa nộp mà cờ phiên bản hiện hành khác false"],
    ["P2-1b' phien_ban_hien_hanh vắng", d => { delete d.phien_ban_hien_hanh; }, "chưa nộp mà cờ phiên bản hiện hành khác false"],
    ["P2-2 kt.phong_bi không rỗng", d => { d.kt.phong_bi = [{id: PB_A}]; }, "chưa nộp mà có phong bì KT"],
    ["P2-2' kt.phong_bi vắng", d => { delete d.kt.phong_bi; }, "chưa nộp mà có phong bì KT"],
    ["P2-3 kt.phong_bi_hien_hanh khác false", d => { d.kt.phong_bi_hien_hanh = true; }, "chưa nộp mà cờ phong bì KT hiện hành khác false"]]) {
    await ca(ten + " → SAI_DTO, không lệnh/bằng chứng", async () => {
      const d = CHUA_NOP(); sua(d);
      const r = await chayDp(d);
      assert.ok(r.chu.includes("không đúng hợp đồng") && r.chu.includes(lyDo), ten + ": " + r.chu.slice(0, 200));
      assert.ok(!r.chu.includes("Chưa nộp hồ sơ đợt") && !r.nutLuu && r.post === 0);
    });
  }

  // ================================================================ INTEGRATION — producer thật → JS thật (chỉ khi có bundle)
  const duongBundle = process.argv[2];
  if (!duongBundle) {
    KQ.not_verified.push("INTEGRATION producer→JS: thiếu bundle M4_03A_KT_PRODUCER_BUNDLE_V1 (backend chưa compose/chưa chạy) — CO/NA/nullDraft/savedRevision/current/historical/revoked CHƯA được chứng minh");
  } else {
    let B;
    try { B = JSON.parse(fs.readFileSync(duongBundle, "utf8")); } catch (e) { B = null; KQ.setup_errors.push({ca: "INTEGRATION", ma: "SETUP_BUNDLE_DOC: " + e.message}); }
    if (B && B.schema !== "M4_03A_KT_PRODUCER_BUNDLE_V1") { KQ.setup_errors.push({ca: "INTEGRATION", ma: "SETUP_BUNDLE_SCHEMA"}); B = null; }
    if (B) await chayIntegration(B);
  }
}

// bundle: {schema, provenance:{source_sha, runtime_sha, ...}, danh_sach, cases:{NULL_DRAFT, SAVED, CO, NA, HISTORICAL, REVOKED}}
//  NULL_DRAFT/SAVED: {xem}; CO/NA: {xem (kt đã lưu đủ điều kiện), ack_xac_nhan, xem_sau}; HISTORICAL: {xem_moi_nhat, xem_lich_su, phong_bi_id};
//  REVOKED: {status, body} (phản hồi GET chi tiết sau thu hồi). Mọi DTO/ACK là JSON do service backend THẬT trả (không sửa tay).
async function chayIntegration(B) {
  const C = B.cases || {};
  const thieu = ["NULL_DRAFT", "SAVED", "CO", "NA", "HISTORICAL", "REVOKED"].filter(k => !C[k]);
  if (thieu.length) KQ.setup_errors.push({ca: "INTEGRATION", ma: "SETUP_BUNDLE_THIEU " + thieu.join(",")});
  const dsCua = x => ({schema: SCHEMA, items: [{kt_pending_id: x.context.kt_pending_id, dot_id: x.context.dot_id, phong_bi_id: x.context.phong_bi_id,
    phong_bi_sha256: x.context.phong_bi_sha256, revision: x.kt ? x.kt.revision : null, trang_thai: x.kt ? x.kt.trang_thai : "CHO_XAC_NHAN", ap: sao(AP)}]});
  async function mo(xem) {
    const P = await moPhien({ds: B.danh_sach || dsCua(xem)});
    const pend = xem.context.kt_pending_id;
    const b = nutDung(P.vungKt(), "Mở"); chuan(b, "SETUP_INT_NUT_MO"); b.click(); await chay();
    await P.tra(P.cho(P.get(URL_CT(pend)), "INT GET"), 200, xem);
    return P;
  }
  if (C.NULL_DRAFT) await ca("INT NULL_DRAFT producer: kt null → Lưu gửi expected_revision 0", async () => {
    assert.strictEqual(C.NULL_DRAFT.xem.kt, null, "producer phải trả kt null tường minh");
    const P = await mo(C.NULL_DRAFT.xem);
    assert.ok(!coSaiDto(P) && !/Phụ thuộc backend/.test(P.chuKt()), "DTO producer bị JS từ chối: " + P.statusKt());
    P.go(O_NT, "1"); await P.bam(NUT_LUU);
    assert.strictEqual(P.bodyCua(P.cho(P.post(URL_LUU), "luu")).expected_revision, 0);
  });
  if (C.SAVED) await ca("INT SAVED producer: kt typed → Lưu gửi expected_revision = kt.revision", async () => {
    const P = await mo(C.SAVED.xem);
    assert.ok(!coSaiDto(P) && !/Phụ thuộc backend/.test(P.chuKt()), "DTO producer bị JS từ chối: " + P.statusKt());
    await P.bamEp(NUT_LUU);
    assert.strictEqual(P.bodyCua(P.cho(P.post(URL_LUU), "luu")).expected_revision, C.SAVED.xem.kt.revision);
  });
  for (const k of ["CO", "NA"]) if (C[k]) await ca("INT " + k + " producer: xác nhận exact revision → ACK producer được JS chấp nhận → 'chờ ghi công nợ'", async () => {
    const P = await mo(C[k].xem);
    assert.ok(!P.nutKt(NUT_XN).disabled, "nhánh " + k + " producer phải xác nhận được: " + P.statusKt());
    await P.bam(NUT_XN);
    const c = P.cho(P.post(URL_XN), "xn");
    assert.strictEqual(P.bodyCua(c).kt_revision_id, C[k].xem.kt.kt_revision_id);
    await P.tra(c, 200, C[k].ack_xac_nhan);
    assert.ok(P.toast().includes("Đã xác nhận nghiệm thu — chờ ghi công nợ"), "ACK producer bị coi là chưa rõ: " + P.statusKt());
    await P.tra(P.cho(P.get(URL_CT(C[k].xem.context.kt_pending_id)), "GET sau"), 200, C[k].xem_sau);
    assert.ok(P.chuKt().includes("Chưa triển khai (M4-03B)") && P.chuKt().includes("Chưa nối (M4-04)"));
  });
  if (C.HISTORICAL) await ca("INT HISTORICAL producer: selector GET đúng phong_bi_id, chỉ đọc", async () => {
    const P = await mo(C.HISTORICAL.xem_moi_nhat);
    await P.bam(NUT_XEM_PB);
    const c = P.cho(P.get(URL_CT(C.HISTORICAL.xem_moi_nhat.context.kt_pending_id, C.HISTORICAL.phong_bi_id)), "GET lịch sử");
    await P.tra(c, 200, C.HISTORICAL.xem_lich_su);
    assert.ok(!coSaiDto(P) && !P.nutKt(NUT_LUU) && !P.nutKt(NUT_XN));
  });
  if (C.REVOKED) await ca("INT REVOKED producer: phản hồi thu hồi → gỡ bằng chứng", async () => {
    const P = await mo(C.SAVED ? C.SAVED.xem : C.NULL_DRAFT.xem);
    await P.bam("↻ Làm mới");
    await P.tra(P.cho(P.laGetKt, "lm"), C.REVOKED.status, C.REVOKED.body);
    assert.ok(!P.chuKt().includes("Số nguồn đã niêm phong") && !P.nutKt(NUT_LUU));
  });
}

main().then(() => {
  if (loiNgoai.length) KQ.hong.push({ca: "unhandledRejection", loi: loiNgoai.map(String).join(" | ")});
  console.log(JSON.stringify({dat: KQ.dat.length, hong: KQ.hong, setup_errors: KQ.setup_errors, not_verified: KQ.not_verified,
    nhan: KQ.not_verified.length ? "UI_ROUTE_EVIDENCE_ONLY — INTEGRATION NOT_VERIFIED (không tính là nghiệm thu)" : "INTEGRATION_BUNDLE_CHECKED"}, null, 1));
  for (const n of KQ.not_verified) console.log("NOT_VERIFIED " + n);
  process.exitCode = KQ.hong.length || KQ.setup_errors.length ? 1 : 0;
}, e => { console.error(e); process.exitCode = 1; });
