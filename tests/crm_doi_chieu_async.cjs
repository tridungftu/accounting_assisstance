"use strict";
// CRM G5-B — kiểm bất đồng bộ khối "Bản ký & đối chiếu" (trong #crm-kiem) trên MÃ THẬT app.js + crm_g.js, không phải trình duyệt: DOM giả tối thiểu
// (cùng mẫu tests/crm_kiem_hd_async.cjs), fetch trả Promise do ca điều khiển; timer làm mới 5000ms của G5 được GIỮ LẠI để ca tự kích (tất định).
// CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN). Root chạy: `node tests/crm_doi_chieu_async.cjs` (Node ≥ 18). Mã thoát 0 = mọi ca đạt.
// Không ghi/xóa tệp, không mạng, không tiến trình con. Đây là MOCK trình duyệt — không chứng minh GUI thật. Mọi VIEW/ACK là dữ liệu GIẢ (DEMO) của mock,
// KHÔNG phải kết quả producer E5 thật, KHÔNG phải nghiệm thu.
// Ca:
//  D0  VIEW bắt buộc + chờ cấu hình: nhãn "bắt buộc · chờ cấu hình · chưa đối chiếu", lý do readiness/việc hiển thị; không suy "khớp".
//  D1  VIEW sai cấu trúc (thừa khóa / lệch bản ký / khởi tạo G4 tự nhận bằng chứng / KHOP mà có lệch / lịch sử chứa kết quả hiện hành) → không vẽ nút/kết quả.
//  D2  kết quả LECH: bảng tham số (bản sinh / bản ký / trích dẫn+locator / mức), ∅ ≠ 0, tiền tệ tường minh; lịch sử TÁCH bảng riêng; nhãn DEMO/CŨ.
//  D3  Chạy đối chiếu: bấm lặp → 1 POST; thân ĐÚNG {ky_id, expected_context_sha256, khoa}; ACK typed → đọc lại; việc CHO → làm mới định kỳ; XONG → dừng.
//  D4  mất kết nối → giữ ý định; lệnh khác bị chặn (0 POST); gửi lại ĐÚNG body + khóa; ACK lệch / 5xx → vẫn CHƯA RÕ; ACK đúng → xong.
//  D5  vai A→B→A khi POST + GET còn bay: không hai POST song song; ACK cũ im lặng (không toast/GET); GET cũ không ghi đè; ý định sau có khóa mới.
//  D6  quyền chạy/đối soát = false → nút vô hiệu + lý do; bấm → 0 POST.  D7 403 khi gửi → nhả ý định, đọc lại, không nút gửi lại.
//  DZ  mọi POST đối chiếu: chỉ 2 route, thân đúng 3 trường, không trường thẩm quyền; không Promise bị từ chối không xử lý.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");
const APP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/app.js"), "utf8");
const CRMG = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/crm_g.js"), "utf8");
const ID_TINH = new Set([...fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/index.html"), "utf8").matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const loiNgoai = [];
process.on("unhandledRejection", e => { loiNgoai.push(e); });

const henG5 = [];  // timer 5000ms (làm mới G5) giữ lại — ca tự kích
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
    after(...n) { const p = this.parent; if (!p) return; const cs = n.map(x => p._con(x)); p.children.splice(p.children.indexOf(this) + 1, 0, ...cs); }
    replaceChildren(...n) { for (const c of this.children) c.parent = null; this._text = ""; this.children = []; this.append(...n); }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(x => x !== this); this.parent = null; }
    addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
    dispatch(t, ev = {}) { return (this.listeners[t] || []).map(fn => fn({preventDefault() {}, target: this, key: "", ...ev})); }
    click() { return this.dispatch("click"); }
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
  const henGio = (fn, ms, ...a) => {
    if (ms === 5000) { const t = {fn, a, huy: false, g5: true}; henG5.push(t); return t; }
    const t = setTimeout(fn, ms, ...a); if (ms === 60000 && t && typeof t.unref === "function") t.unref(); return t;
  };
  const huyGio = t => { if (t && t.g5) t.huy = true; else clearTimeout(t); };
  const ctx = {document, Node: El, console, setTimeout: henGio, clearTimeout: huyGio, Promise, Map, Set, JSON, Math, Date, Number, String, Object, Array, Error,
    TypeError, SyntaxError, encodeURIComponent, decodeURIComponent, URLSearchParams, location: {hash: "#hopdong"}, crypto: {randomUUID: () => "uuid-" + (++soUuid)},
    URL: {createObjectURL: () => "blob:x", revokeObjectURL() {}}, fetch, navigator: {}};
  ctx.window = ctx;
  ctx.addEventListener = () => {};
  vm.createContext(ctx);
  return {ctx, document, calls};
}

const phanHoi = (status, data) => ({ok: status >= 200 && status < 300, status, headers: {get: () => "application/json"}, json: async () => data});
const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 12) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
function timTatCa(root, pred, out = []) { if (pred(root)) out.push(root); for (const c of root.children || []) timTatCa(c, pred, out); return out; }
const nut = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));

const BH = "MO_PHONG_CRM_G_BH_A", KT = "MO_PHONG_CRM_G_KT_A";
const DEMO = [{dang_nhap: BH, vai_tro: "BAN_HANG"}, {dang_nhap: KT, vai_tro: "KE_TOAN"}];
const NGUOI = l => ({dang_nhap: l, vai_tro: l.includes("BH") ? "BAN_HANG" : "KE_TOAN", phap_nhan: ["PN_DEMO_A"], hanh_dong: [], xem_tien: false, duoc: {}});
const CRM = l => ({cau_hinh: true, danh_tinh_demo: DEMO, nguoi: NGUOI(l), ngay_nghiep_vu: "2026-10-23", mau: [], m1_cau_hinh: false, tien_mau: [],
  ho_so: [], hop_dong: [], tien: [], file_soat: [], danh_muc: {doi_tac: [], du_an: []}});

// định danh GIẢ (dạng UUID để qua kiểm VIEW/ACK typed)
const KY1 = "11111111-1111-4111-8111-111111111111", KY2 = "11111111-1111-4111-8111-222222222222";
const HD1 = "22222222-2222-4222-8222-111111111111", HD2 = "22222222-2222-4222-8222-222222222222";
const JOB = "77777777-7777-4777-8777-777777777777", JOB2 = "77777777-7777-4777-8777-888888888888";
const R1 = "99999999-9999-4999-8999-111111111111", R0 = "99999999-9999-4999-8999-000000000000";
const CTX1 = "e".repeat(64), CTX2 = "f".repeat(64), CTX_CU = "0".repeat(64);
const HD_CUA = {[KY1]: HD1, [KY2]: HD2}, MA_CUA = {[KY1]: "HD-NB-1", [KY2]: "HD-NB-2"};
const DSK = l => ({nguoi: {dang_nhap: l}, ds: l === KT ? [KY1, KY2].map(id => ({ky_id: id, hop_dong_id: HD_CUA[id], ma_noi_bo: MA_CUA[id], ngay_ky: "2026-10-20",
  trang_thai: "CHUA_KIEM", hien_thi: "Đã ký — chờ kế toán kiểm", revision: 0})) : []});
const G5_HOLD = {che_do: "VAN_HANH", trang_thai: "HOLD", khoi_tao: {trang_thai: "PENDING", ly_do: "BAT_BUOC_KHAI_CO", la_bang_chung: false}, lech: [],
  chan: [{ma: "UNREGISTERED_G5_PROOF"}]};
const DOC = id => ({ky: {ky_id: id, hop_dong_id: HD_CUA[id], ma_noi_bo: MA_CUA[id], revision: 2, ngay_ky: "2026-10-20", nguoi_ky_khach: "****1234",
  co_sua: true, mo_ta_sua: "DEMO: khách sửa tay điều 3", ky_pdf_sha256: "c".repeat(64), ky_pdf_len: 2048, ky_so_trang: 1, g3_pdf_sha256: "a".repeat(64), g3_pdf_len: 1234,
  ma_mau: "HD", phien_ban_mau: 1, danh_muc_ref: "DM", danh_muc_rev: 1, tao_boi: BH, g5_khoi_tao: {trang_thai: "PENDING", ly_do: "BAT_BUOC_KHAI_CO", la_bang_chung: false}},
  quyen: {kiem: true, ly_do: null}, hop_dong: {crm_giao_ket: "DA_KY", doi_tac_id: null}, khach_ban_ky: {doi_tac_id: null, du_thao_ten: "KHÁCH DỰ THẢO DEMO", du_thao_lien_he: null},
  ma_junsky_ung_vien: [], ho_so: null, rev: null,
  truong: [{ten: "so_hop_dong", nhan: "Số HĐ", kieu: "text", nhom: "Chung", pii: false, bat_buoc: true, gia_tri: "HĐ-1", vi_tri: null, trang_thai_can_cu: "CO_CAN_CU"}],
  lich: {tien_te: "VND", scale: 0, tong_minor: "1000000000", tong_dong_minor: "1000000000", loi: [],
    dong: [{dot: 1, lan: "1", loai: "PERCENT", ty_le: "100", so_tien_minor: "1000000000", moc: "NGAY:2026-11-01", han: "2026-11-01", loi: []}]},
  g7: {trang_thai: "KHONG_AP_DUNG", lech: []}, g5: G5_HOLD, check: null, xu_ly_lech: [], lich_su: [], tom_tat: {so_dong: 1, tong_minor: "1000000000", tien_te: "VND"},
  g5_che_do: "VAN_HANH"});

const JOBV = (tt, sua = {}) => ({job_id: JOB, loai: "THU_CONG", trang_thai: tt, ly_do: null, request_id: `crm-g5-${JOB}-1`, the_he: 1, so_lan: 0,
  khoi_tao_loai: "NGUOI_DUNG", cap_nhat_luc: "2026-10-23T01:00:00Z", ...sua});
const TS_LECH = [
  {ma: "GIA_TRI_HD", crm_truong: "gia_tri_hop_dong", muc: 3, kieu: "tien", gia_tri_ky_vong: {so_tien: "1000000000", tien_te: "VND"},
   gia_tri_ban_ky: {so_tien: "100000000", tien_te: "VND"}, trich_dan: "Điều 3 (bản ký DEMO): giá trị 100.000.000 VND", vi_tri_do_duoc: {trang: 1, doan: 3}, trang_thai: "LECH"},
  {ma: "DIEN_TICH", crm_truong: "dien_tich", muc: 0, kieu: "so", gia_tri_ky_vong: "0", gia_tri_ban_ky: null, trich_dan: null, vi_tri_do_duoc: null, trang_thai: "KHOP"},
  {ma: "LICH_TT", crm_truong: "crm.lich", muc: 2, kieu: "bang",
   gia_tri_ky_vong: {cot: ["dong_id", "lan", "loai", "ty_le", "so_tien", "tien_te", "moc_loai", "moc_ngay", "moc_su_kien", "ghi_chu"],
                     dong: [["d1", "1", "PERCENT", "40", "0", "VND", "SU_KIEN", null, "KY_HD", null]]},
   gia_tri_ban_ky: null, trich_dan: null, vi_tri_do_duoc: null, trang_thai: "KHOP"}];
const KQV = (tt, sua = {}) => ({result_id: R1, trang_thai: tt, hien_hanh: true, nhan_dang_ky: "VAN_HANH", tac_nhan_loai: "NGUOI_DUNG", so_phu: 3, so_ma: 3,
  so_lech: tt === "LECH" ? 1 : 0, so_thieu: 0, tham_so: tt === "LECH" ? TS_LECH : TS_LECH.map(t => ({...t, gia_tri_ban_ky: null, trich_dan: null, vi_tri_do_duoc: null,
  trang_thai: "KHOP"})), tao_luc: "2026-10-23T02:00:00Z", ...sua});
const LS0 = {result_id: R0, trang_thai: "KHOP", tac_nhan_loai: "SYSTEM_JOB", hien_hanh: false, so_lech: 0, so_thieu: 0, tao_luc: "2026-10-22T02:00:00Z"};
const VIEW = (id, sua = {}) => ({kieu: "CRM_G5_VIEW_V1", ky_id: id, context_sha256: CTX1, bat_buoc: false,
  khoi_tao: {trang_thai: "NOT_SELECTED", ly_do: "CHUA_AP_DUNG_CHON_MAU", la_bang_chung: false}, quyen: {chay: true, doi_soat: false},
  readiness: {san_sang: false, ly_do: ["THIEU_DANG_KY"]}, current_job: null, current_result: null, history: [], g6: G5_HOLD, ...sua});
const ACK = (sua = {}) => ({kieu: "CRM_G5_ACK_V1", ky_id: KY1, context_sha256: CTX1, job_id: JOB, request_id: `crm-g5-${JOB}-1`, state: "CHO",
  current_result_id: null, tao_moi: true, replay: false, ...sua});
const TRUONG_DC = ["expected_context_sha256", "khoa", "ky_id"];
const KHONG_NHAN = ["expected", "expected_sha256", "catalog", "catalog_id", "catalog_binding", "catalog_binding_sha256", "mapping", "dang_ky_id", "principal",
  "nguoi_chay", "tac_nhan", "request_id", "job_id", "result_id", "mode", "engine", "tham_so", "trusted", "lineage", "soan_rev_id", "g5", "g5_che_do", "che_do",
  "dang_nhap", "nguoi", "actor", "phap_nhan", "phap_nhan_id", "vai_tro", "trang_thai"];

async function main() {
  const {document, calls, ctx} = moiTruong();
  vm.runInContext(APP, ctx, {filename: "app.js"});
  const ngheHash = [];
  ctx.addEventListener = (t, fn) => { if (t === "hashchange") ngheHash.push(fn); };
  vm.runInContext(CRMG, ctx, {filename: "crm_g.js"});
  const $ = id => document.getElementById(id);
  const conLai = pred => calls.filter(c => !c.xong && pred(c));
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const get = url => c => c.method === "GET" && c.url === url;
  const post = url => c => c.method === "POST" && c.url === url;
  const getDsK = get("/api/crm/giao-ket/kiem"), getCt = id => get(`/api/crm/giao-ket/kiem/${id}`);
  const getDc = id => get(`/api/crm/giao-ket/doi-chieu/${id}`), postDc = h => post(`/api/crm/giao-ket/doi-chieu/${h}`);
  const laDc = c => c.url.startsWith("/api/crm/giao-ket/doi-chieu/");
  const sec = () => $("crm-kiem");
  const g5s = () => tim(sec(), e => e.tagName === "SECTION" && e.className.includes("gk-doi-chieu"));
  const g5Txt = () => (g5s() || {textContent: ""}).textContent;
  const nhanG5 = () => { const p = tim(g5s(), e => e.dataset && e.dataset.g5Nhan !== undefined); return p ? p.dataset.g5Nhan : null; };
  const nutLai = () => { const u = tim(g5s(), e => e.dataset && e.dataset.g5ChuaRo === "1"); return u ? nut(u, "Gửi lại y nguyên (cùng khóa)") : null; };
  const toastTxt = () => ($("toast") || {textContent: ""}).textContent;
  const datToast = s => { if ($("toast")) $("toast").textContent = s; };
  const than = c => JSON.parse(c.opts.body);
  async function traKhac() {
    for (const c of conLai(c => !/^\/api\/crm(\/giao-ket\/(kiem|doi-chieu)|\/danh-tinh|$)/.test(c.url))) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
  }
  async function traDs(l) { for (const c of conLai(getDsK)) { c.xong = true; c.resolve(phanHoi(200, DSK(l))); } await chay(); }
  async function traDc(id, v) { const cs = conLai(getDc(id)); assert.ok(cs.length, "không có GET đối chiếu " + id); for (const c of cs) { c.xong = true; c.resolve(phanHoi(200, v)); } await chay(); }
  async function moKy(id, v) {  // mở bản ký: GET chi tiết G6A → GET VIEW đối chiếu (fence riêng)
    const tr = tim(sec(), e => e.tagName === "TR" && e.textContent.includes(MA_CUA[id]));
    assert.ok(tr, "không thấy dòng " + MA_CUA[id]);
    nut(tr, "Mở").click(); await chay();
    cho(getCt(id), "GET chi tiết " + id).resolve(phanHoi(200, DOC(id))); await chay();
    if (v !== undefined) await traDc(id, v);
  }
  async function doiVai(l) {
    $("crm-danh-tinh").value = l; $("crm-doi-vai").click(); await chay();
    for (const c of conLai(post("/api/crm/danh-tinh"))) { c.xong = true; c.resolve(phanHoi(200, {dang_nhap: l})); }
    await chay();
    for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM(l))); }
    await chay();
    await traKhac();
    await traDs(l);
  }
  const henCon = () => henG5.filter(t => !t.huy && !t.chay);
  async function kichHen() { for (const t of henCon()) { t.chay = true; t.fn(...t.a); } await chay(); }

  // khởi động vai KT
  assert.ok(sec(), "chưa dựng khối #crm-kiem sau #crm-gk");
  for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM(KT))); }
  await traKhac();
  await traDs(KT);
  await traKhac();

  // ---------------------------------------------------------------- D0 bắt buộc + chờ cấu hình (không suy khớp)
  {
    await moKy(KY1, VIEW(KY1, {bat_buoc: true, khoi_tao: {trang_thai: "PENDING", ly_do: "BAT_BUOC_KHAI_CO", la_bang_chung: false},
      quyen: {chay: true, doi_soat: true}, readiness: {san_sang: false, ly_do: ["THIEU_DANG_KY", "THIEU_NGUOI_CHAY"]},
      current_job: JOBV("CHO_CAU_HINH", {loai: "BAT_BUOC", khoi_tao_loai: "HE_THONG", ly_do: "THIEU_NGUOI_CHAY"})}));
    assert.ok(g5s(), "D0: thiếu khối Bản ký & đối chiếu");
    assert.strictEqual(nhanG5(), "bắt buộc|chờ cấu hình|chưa đối chiếu", "D0: nhãn trạng thái sai");
    const t = g5Txt();
    assert.ok(t.includes("Chưa có đăng ký engine/catalog") && t.includes("Chưa cấu hình người chạy việc bắt buộc"), "D0: thiếu lý do readiness");
    assert.ok(t.includes("Việc bắt buộc:"), "D0: thiếu lý do của việc đang chờ");
    assert.ok(!/khớp|KHỚP|MATCH/.test(t), "D0: chưa có kết quả mà hiển thị khớp");
    assert.ok(!nut(g5s(), "Chạy đối chiếu").disabled && !nut(g5s(), "Đối soát").disabled, "D0: nút theo quyền máy chủ bị vô hiệu sai");
    assert.strictEqual(henCon().length, 0, "D0: việc chờ cấu hình không cần làm mới định kỳ");
    console.log("D0 đạt");
  }

  // ---------------------------------------------------------------- D1 VIEW sai cấu trúc → không vẽ nút/kết quả
  {
    const sai = [
      VIEW(KY1, {them: 1}),
      VIEW(KY2),
      VIEW(KY1, {khoi_tao: {trang_thai: "PENDING", ly_do: "BAT_BUOC_KHAI_CO", la_bang_chung: true}}),
      VIEW(KY1, {current_result: KQV("KHOP", {so_lech: 1})}),
      VIEW(KY1, {current_result: KQV("KHOP"), history: [{...LS0, result_id: R1}]}),
      VIEW(KY1, {readiness: {san_sang: true, ly_do: ["THIEU_DANG_KY"]}}),
      VIEW(KY1, {current_job: JOBV("XONG")}),
      VIEW(KY1, {current_job: JOBV("CHO", {request_id: `crm-g5-${JOB2}-1`})}),
      VIEW(KY1, {current_result: KQV("LECH", {tham_so: TS_LECH.slice(0, 2)})}),
    ];
    for (const [i, v] of sai.entries()) {
      await moKy(KY1, v);
      assert.ok(g5Txt().includes("Không tải được trạng thái đối chiếu"), `D1.${i}: VIEW sai vẫn được dùng`);
      assert.ok(!nut(g5s(), "Chạy đối chiếu"), `D1.${i}: vẽ nút từ VIEW sai`);
      assert.ok(!/khớp|KHỚP/.test(g5Txt()), `D1.${i}: suy khớp từ VIEW sai`);
    }
    console.log("D1 đạt");
  }

  // ---------------------------------------------------------------- D2 kết quả LECH: bảng tham số + lịch sử tách riêng + nhãn
  {
    await moKy(KY1, VIEW(KY1, {readiness: {san_sang: true, ly_do: []}, current_result: KQV("LECH", {hien_hanh: false, nhan_dang_ky: "DEMO_KIEM_THU"}), history: [LS0]}));
    const t = g5Txt();
    assert.ok(nhanG5().endsWith("lệch"), "D2: nhãn không phải lệch");
    assert.ok(t.includes("phủ 3/3 mã · 1 lệch · 0 thiếu"), "D2: thiếu tóm tắt phủ/lệch/thiếu");
    assert.ok(t.includes("CŨ: đăng ký engine/catalog đã đổi") && t.includes("DEMO kiểm thử, không phải bằng chứng vận hành"), "D2: thiếu nhãn CŨ/DEMO");
    const bangs = timTatCa(g5s(), e => e.tagName === "TABLE");
    assert.strictEqual(bangs.length, 2, "D2: kết quả hiện hành và lịch sử phải là HAI bảng riêng");
    const hd0 = timTatCa(bangs[0], e => e.tagName === "TH").map(e => e.textContent);
    assert.deepStrictEqual(hd0, ["Tham số", "Bản sinh", "Bản ký", "Trích dẫn/locator", "Mức"], "D2: cột bảng tham số sai");
    const dong = timTatCa(bangs[0], e => e.tagName === "TR").slice(1).map(r => timTatCa(r, e => e.tagName === "TD").map(e => e.textContent));
    assert.deepStrictEqual(dong[0], ["GIA_TRI_HD (gia_tri_hop_dong) · lệch", "1000000000 VND", "100000000 VND",
      "Điều 3 (bản ký DEMO): giá trị 100.000.000 VND · {\"trang\":1,\"doan\":3}", "3"], "D2: dòng lệch tiền sai");
    assert.deepStrictEqual(dong[1].slice(0, 3), ["DIEN_TICH (dien_tich) · khớp", "0", "—"], "D2: 0 phải hiển thị 0 (≠ ∅), bản ký khớp không lặp giá trị");
    assert.ok(dong[2][1].startsWith("bảng 1 dòng: #1 [d1 | 1 | PERCENT | 40 | 0 | VND | SU_KIEN | ∅ | KY_HD | ∅]"), "D2: bảng lịch mất thứ tự/∅");
    assert.ok(t.includes("Lịch sử đối chiếu (không phải kết quả hiện hành)"), "D2: thiếu tiêu đề lịch sử tách riêng");
    const hd1 = timTatCa(bangs[1], e => e.tagName === "TH").map(e => e.textContent);
    assert.deepStrictEqual(hd1, ["Lúc", "Kết quả", "Tác nhân", "Theo đăng ký hiện hành?", "Lệch/thiếu"], "D2: cột lịch sử sai");
    assert.ok(bangs[1].textContent.includes("việc hệ thống (bắt buộc)"), "D2: lịch sử không tách tác nhân việc hệ thống");
    console.log("D2 đạt");
  }

  // ---------------------------------------------------------------- D3 Chạy: bấm lặp → 1 POST; thân 3 trường; ACK → đọc lại; làm mới định kỳ khi CHO
  {
    await moKy(KY1, VIEW(KY1));
    nut(g5s(), "Chạy đối chiếu").click(); nut(g5s(), "Chạy đối chiếu").click(); await chay();
    assert.strictEqual(conLai(postDc("chay")).length, 1, "D3: bấm lặp gửi thêm POST");
    const p = cho(postDc("chay"), "POST chạy");
    nut(g5s(), "Chạy đối chiếu").click(); await chay();
    assert.strictEqual(conLai(postDc("chay")).length, 0, "D3: POST thứ hai khi lần đầu còn chờ");
    const b = than(p);
    assert.deepStrictEqual(Object.keys(b).sort(), TRUONG_DC, "D3: thân có trường ngoài hợp đồng");
    assert.deepStrictEqual([b.ky_id, b.expected_context_sha256], [KY1, CTX1], "D3: thân sai bản ký/ngữ cảnh");
    assert.ok(typeof b.khoa === "string" && b.khoa.startsWith("crmkiem-"), "D3: thiếu khóa");
    datToast("");
    const g0 = dem(getDc(KY1));
    p.resolve(phanHoi(200, ACK())); await chay();
    assert.ok(toastTxt().includes("Chạy đối chiếu: đã ghi việc (đang xử lý)"), "D3: ACK đúng không hiển thị");
    assert.ok(!/khớp/.test(toastTxt()), "D3: ACK (đã ghi việc) bị trình bày như kết quả");
    assert.strictEqual(dem(getDc(KY1)), g0 + 1, "D3: không đọc lại VIEW sau ACK");
    const ctxMoi = VIEW(KY1, {context_sha256: CTX2, current_job: JOBV("CHO")});
    await traDc(KY1, ctxMoi);
    assert.strictEqual(nhanG5(), "đang xử lý|chưa đối chiếu", "D3: nhãn việc đang xử lý sai");
    assert.strictEqual(henCon().length, 1, "D3: việc CHO phải hẹn làm mới định kỳ");
    await kichHen();
    await traDc(KY1, VIEW(KY1, {context_sha256: CTX2, current_job: JOBV("DANG_CHAY", {so_lan: 1})}));
    assert.strictEqual(henCon().length, 1, "D3: việc DANG_CHAY phải tiếp tục làm mới");
    await kichHen();
    await traDc(KY1, VIEW(KY1, {context_sha256: CTX2, readiness: {san_sang: true, ly_do: []}, current_result: KQV("KHOP")}));
    assert.strictEqual(henCon().length, 0, "D3: đã có kết quả mà vẫn làm mới");
    assert.strictEqual(nhanG5(), "khớp", "D3: kết quả KHOP do máy chủ công bố không hiển thị");
    console.log("D3 đạt");
  }

  // ---------------------------------------------------------------- D4 chưa rõ → giữ ý định; ACK lệch/5xx vẫn chưa rõ; gửi lại y nguyên
  {
    await moKy(KY1, VIEW(KY1, {quyen: {chay: true, doi_soat: true}, current_job: JOBV("CHUA_RO", {ly_do: "TRICH6_CHUA_RO"})}));
    assert.strictEqual(henCon().length, 0, "D4: việc CHUA_RO không tự làm mới (đối soát tường minh)");
    nut(g5s(), "Chạy đối chiếu").click(); await chay();
    const p1 = cho(postDc("chay"), "POST chạy gốc");
    const b1 = than(p1);
    p1.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(nutLai(), "D4: thiếu nút gửi lại y nguyên");
    nut(g5s(), "Đối soát").click(); await chay();
    assert.strictEqual(conLai(postDc("doi-soat")).length, 0, "D4: lệnh khác chen khi ý định trước chưa rõ");
    nutLai().click(); await chay();
    const p2 = cho(postDc("chay"), "POST gửi lại 1");
    assert.deepStrictEqual(than(p2), b1, "D4: gửi lại khác body/khóa");
    p2.resolve(phanHoi(200, ACK({state: "XONG"}))); await chay();
    assert.ok(nutLai(), "D4: ACK lệch (state ngoài hợp đồng) bị coi là xong");
    nutLai().click(); await chay();
    const p3 = cho(postDc("chay"), "POST gửi lại 2");
    assert.deepStrictEqual(than(p3), b1, "D4: gửi lại lần 2 khác body/khóa");
    p3.resolve(phanHoi(200, {...ACK(), ket_qua: "KHOP"})); await chay();
    assert.ok(nutLai(), "D4: ACK thừa khóa (kết quả tự nhận) bị coi là xong");
    nutLai().click(); await chay();
    const p4 = cho(postDc("chay"), "POST gửi lại 3");
    assert.deepStrictEqual(than(p4), b1, "D4: gửi lại lần 3 khác body/khóa");
    p4.resolve(phanHoi(502, {error: "HTTP_502"})); await chay();
    assert.ok(nutLai(), "D4: 5xx bị coi là lỗi xác định (mất ý định)");
    nutLai().click(); await chay();
    const p5 = cho(postDc("chay"), "POST gửi lại 4");
    assert.deepStrictEqual(than(p5), b1, "D4: gửi lại lần 4 khác body/khóa");
    p5.resolve(phanHoi(200, ACK({tao_moi: false, replay: true}))); await chay();
    assert.ok(!nutLai(), "D4: ACK đúng mà còn nút gửi lại");
    assert.ok(toastTxt().includes("biên nhận cũ của cùng yêu cầu"), "D4: replay không được báo");
    await traDc(KY1, VIEW(KY1));
    console.log("D4 đạt");
  }

  // ---------------------------------------------------------------- D5 vai A→B→A: không hai POST song song; ACK/GET cũ im lặng; khóa mới
  {
    nut(g5s(), "Chạy đối chiếu").click(); await chay();
    const pCu = cho(postDc("chay"), "POST trước đổi vai");
    const khoaCu = than(pCu).khoa;
    const tr = tim(sec(), e => e.tagName === "TR" && e.textContent.includes(MA_CUA[KY1]));
    nut(tr, "Mở").click(); await chay();
    cho(getCt(KY1), "GET chi tiết trước đổi vai").resolve(phanHoi(200, DOC(KY1))); await chay();
    const gCu = cho(getDc(KY1), "GET VIEW trước đổi vai");  // còn bay qua A→B→A
    await doiVai(BH);
    assert.ok(!g5s(), "D5: vai BH vẫn thấy khối đối chiếu của KT");
    await doiVai(KT);
    await moKy(KY1, VIEW(KY1, {context_sha256: CTX2}));
    nut(g5s(), "Chạy đối chiếu").click(); await chay();
    assert.strictEqual(conLai(postDc("chay")).length, 0, "D5: hai POST song song cho cùng (vai, bản ký)");
    datToast("");
    const g0 = dem(getDc(KY1));
    pCu.resolve(phanHoi(200, ACK())); await chay();
    assert.strictEqual(toastTxt(), "", "D5: ACK cũ sau A→B→A vẫn toast");
    assert.strictEqual(dem(getDc(KY1)), g0, "D5: ACK cũ kích đọc lại");
    gCu.resolve(phanHoi(200, VIEW(KY1, {current_result: KQV("KHOP"), readiness: {san_sang: true, ly_do: []}}))); await chay();
    assert.ok(!/khớp/.test(g5Txt()), "D5: GET VIEW cũ ghi đè trạng thái hiện hành");
    nut(g5s(), "Chạy đối chiếu").click(); await chay();
    const pMoi = cho(postDc("chay"), "POST sau đổi vai");
    assert.notStrictEqual(than(pMoi).khoa, khoaCu, "D5: ý định mới dùng lại khóa cũ");
    assert.strictEqual(than(pMoi).expected_context_sha256, CTX2, "D5: ý định mới không theo ngữ cảnh hiện hành");
    pMoi.resolve(phanHoi(409, {error: "CRM_G5_NGU_CANH_CU", message: "Trạng thái đối chiếu đã đổi — tải lại rồi thao tác"})); await chay();
    assert.ok(!nutLai(), "D5: lỗi xác định 409 vẫn giữ ý định");
    assert.ok(toastTxt().includes("tải lại"), "D5: 409 ngữ cảnh cũ không báo");
    await traDc(KY1, VIEW(KY1, {context_sha256: CTX2}));
    console.log("D5 đạt");
  }

  // ---------------------------------------------------------------- D6 không có quyền chạy/đối soát → 0 POST
  {
    await moKy(KY1, VIEW(KY1, {quyen: {chay: false, doi_soat: false}, current_job: JOBV("CHUA_RO")}));
    const n0 = dem(laDc.bind(null)) && dem(c => c.method === "POST" && laDc(c));
    assert.ok(nut(g5s(), "Chạy đối chiếu").disabled && nut(g5s(), "Đối soát").disabled, "D6: nút bật khi máy chủ báo không có quyền");
    assert.ok(g5Txt().includes("Vai hiện hành không chạy được đối chiếu"), "D6: thiếu lý do không có quyền");
    nut(g5s(), "Chạy đối chiếu").click(); nut(g5s(), "Đối soát").click(); await chay();
    assert.strictEqual(dem(c => c.method === "POST" && laDc(c)), n0, "D6: gửi POST khi không có quyền");
    console.log("D6 đạt");
  }

  // ---------------------------------------------------------------- D7 403 khi gửi (quyền bị thu hồi giữa đọc và bấm) → nhả ý định + đọc lại
  {
    await moKy(KY1, VIEW(KY1, {quyen: {chay: true, doi_soat: true}, current_job: JOBV("CHO_CAU_HINH", {ly_do: "E5_CHUA_GHEP"})}));
    assert.ok(g5Txt().includes("Engine Source6 chưa có biến thể đối chiếu bản ký"), "D7: lý do E5 chưa ghép không hiển thị");
    nut(g5s(), "Đối soát").click(); await chay();
    const p = cho(postDc("doi-soat"), "POST đối soát");
    assert.deepStrictEqual(Object.keys(than(p)).sort(), TRUONG_DC, "D7: thân đối soát có trường ngoài hợp đồng");
    const g0 = dem(getDc(KY1));
    p.resolve(phanHoi(403, {error: "CRM_KIEM_CHUA_CO_PHAM_VI", message: "Chưa có phạm vi kiểm hiện hành."})); await chay();
    assert.ok(!nutLai(), "D7: 403 vẫn giữ ý định gửi lại");
    assert.strictEqual(dem(getDc(KY1)), g0 + 1, "D7: không đọc lại VIEW sau 403");
    await traDc(KY1, VIEW(KY1, {quyen: {chay: false, doi_soat: false}}));
    assert.ok(nut(g5s(), "Chạy đối chiếu").disabled, "D7: sau thu hồi quyền nút vẫn bật");
    console.log("D7 đạt");
  }

  // ---------------------------------------------------------------- DZ hợp đồng mọi POST đối chiếu + không Promise từ chối không xử lý
  {
    const ps = calls.filter(c => c.method === "POST" && laDc(c));
    assert.ok(ps.length >= 8, "DZ: quá ít POST đối chiếu được đo");
    for (const c of ps) {
      assert.ok(["/api/crm/giao-ket/doi-chieu/chay", "/api/crm/giao-ket/doi-chieu/doi-soat"].includes(c.url), "DZ: route ngoài hợp đồng " + c.url);
      const b = than(c);
      assert.deepStrictEqual(Object.keys(b).sort(), TRUONG_DC, "DZ: thân ngoài 3 trường");
      for (const k of KHONG_NHAN) assert.ok(!(k in b), "DZ: gửi trường thẩm quyền " + k);
      assert.ok(SHA_OK(b.expected_context_sha256), "DZ: ngữ cảnh không phải sha256");
    }
    assert.strictEqual(dem(c => laDc(c) && c.method === "GET" && /\?/.test(c.url)), 0, "DZ: GET VIEW mang query");
    await chay(30);
    assert.deepStrictEqual(loiNgoai, [], "DZ: có Promise bị từ chối không xử lý");
    console.log("DZ đạt");
  }
  for (const t of henCon()) t.huy = true;
}
const SHA_OK = s => typeof s === "string" && /^[0-9a-f]{64}$/.test(s);

main().then(() => { console.log("crm_doi_chieu_async: mọi ca đạt (mock — không phải GUI thật)"); },
  e => { console.error(e); process.exitCode = 1; });
