"use strict";
// CRM-41-06A — kiểm bất đồng bộ G6A (kế toán kiểm hợp đồng đã ký → hiệu lực) trên MÃ THẬT app.js + crm_g.js (khối #crm-kiem dựng sau #crm-gk), không
// phải trình duyệt: DOM giả tối thiểu (cùng mẫu tests/crm_ky_ket_async.cjs, thêm Element.after), fetch trả Promise do ca điều khiển.
// CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN). Root chạy: `node tests/crm_kiem_hd_async.cjs` (Node ≥ 18). Mã thoát 0 = mọi ca đạt (lỗi → exitCode 1).
// Không ghi/xóa tệp, không mạng, không tiến trình con. Đây là MOCK trình duyệt — không chứng minh GUI thật. Mọi ACK/GET là dữ liệu GIẢ của mock:
// ACK kích hoạt HIỆU LỰC ở H7 là MOCK giao diện — qua HTTP vận hành, G5 luôn HOLD (UNREGISTERED_G5_PROOF) nên kích hoạt thật KHÔNG đạt được tới khi
// có bằng chứng G5 đăng ký; ca này KHÔNG phải nghiệm thu/không phải bằng chứng F6/F7 (xem tests/test_crm_kiem_hd.py, nhãn SYNTHETIC).
// Ca:
//  H0  dương: danh sách → mở bản ký → hash bản ký/G3, G5 HOLD trung thực (UNREGISTERED_G5_PROOF, khởi tạo G4 không phải bằng chứng), kích hoạt vô hiệu.
//  H1  ngày hiệu lực thiếu căn cứ/trích dẫn → 0 POST.
//  H2  Lưu kiểm: bấm lặp → 1 POST; thân chỉ trường cho phép (không actor/PN/chế độ G5/kết quả); đối tác lấy từ mã Junsky CÓ SẴN; ACK typed → làm mới.
//  H3  Chạy check: mất kết nối → giữ ý định; lệnh khác bị chặn; gửi lại ĐÚNG body + khóa; ACK lệch (g5_che_do SYNTHETIC) → vẫn CHƯA RÕ; ACK đúng → FINAL.
//  H4  vai A→B→A khi POST còn bay: ACK hợp lệ cũ và lỗi 409 cũ im lặng (không toast/GET/vẽ); ý định mới khóa mới.
//  H5  GET chi tiết cũ về sau GET mới → không ghi đè.
//  H6  tải PDF: blob về sau khi rời #hopdong rồi quay lại → không click; đối chứng dương click 1 lần.
//  H7  kích hoạt: bấm lặp → 1 POST đúng check_id + sha256 đồ thị đã xem; ACK lệch hợp đồng → CHƯA RÕ; gửi lại y nguyên → ACK đúng → HIỆU LỰC.
//  H8  trả lại: ACK g4_trang_thai ≠ DA_KY (giả "về nháp") → CHƯA RÕ; ACK đúng → "chờ quy trình ký lại", KHÔNG về nháp; sau đó không còn form/kích hoạt.
//  H9  quyen.kiem=false (cùng người ghi bản ký) → không form/lệnh, hiện lý do tách nhiệm.
//  H10 P1-B khách dự thảo (NULL/NULL): từ khóa < 3 → 0 POST; thân tra cứu đúng {ky_id, tu_khoa}; phản hồi cũ sau A→B→A / lệch bản ký bị bỏ; 409
//      CRM_KIEM_KHACH_DA_DINH → thông báo + đọc lại; chọn ứng viên tra cứu → Lưu mang đúng cặp doi_tac_id/ma_junsky_id; làm mới giữ mã đã lưu.
//  HZ  mọi POST G6A: chỉ 7 route (6 lệnh + tim-junsky), thân ⊆ trường cho phép, không trường thẩm quyền máy chủ; không Promise bị từ chối không xử lý.
// Harness: setTimeout tiêm vào vm CHỈ unref timer dọn URL 60000ms; mọi timer khác không đổi. Listener hashchange chỉ thu của crm_g.js.
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
    after(...n) { const p = this.parent; if (!p) return; const cs = n.map(x => p._con(x)); p.children.splice(p.children.indexOf(this) + 1, 0, ...cs); }
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
function timTatCa(root, pred, out = []) { if (pred(root)) out.push(root); for (const c of root.children || []) timTatCa(c, pred, out); return out; }
const nut = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));
function blobTreo() {
  let ra;
  const p = new Promise(r => { ra = r; });
  return {res: {ok: true, status: 200, headers: {get: () => "application/pdf"}, json: async () => ({}), blob: () => p}, ra: n => ra(new BLOB_GOC([new Uint8Array(n)]))};
}

const BH = "MO_PHONG_CRM_G_BH_A", KT = "MO_PHONG_CRM_G_KT_A";
const DEMO = [{dang_nhap: BH, vai_tro: "BAN_HANG"}, {dang_nhap: KT, vai_tro: "KE_TOAN"}];
const NGUOI = l => ({dang_nhap: l, vai_tro: l.includes("BH") ? "BAN_HANG" : "KE_TOAN", phap_nhan: ["PN_DEMO_A"], hanh_dong: [], xem_tien: false, duoc: {}});
const CRM = l => ({cau_hinh: true, danh_tinh_demo: DEMO, nguoi: NGUOI(l), ngay_nghiep_vu: "2026-10-22", mau: [], m1_cau_hinh: false, tien_mau: [],
  ho_so: [], hop_dong: [], tien: [], file_soat: [], danh_muc: {doi_tac: [], du_an: []}});

// định danh GIẢ (dạng UUID để qua kiểm ACK typed)
const KY1 = "11111111-1111-4111-8111-111111111111", KY2 = "11111111-1111-4111-8111-222222222222";
const HD1 = "22222222-2222-4222-8222-111111111111", HD2 = "22222222-2222-4222-8222-222222222222", HD_KHAC = "22222222-2222-4222-8222-999999999999";
const HO1 = "33333333-3333-4333-8333-111111111111", HO2 = "33333333-3333-4333-8333-222222222222";
const CK1 = "44444444-4444-4444-8444-111111111111", CK2 = "44444444-4444-4444-8444-222222222222";
const PB = "55555555-5555-4555-8555-555555555555", CT = "66666666-6666-4666-8666-666666666666", VIEC = "77777777-7777-4777-8777-777777777777";
const MJ = "99999999-9999-4999-8999-999999999999", DT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const SHA_DT = "d".repeat(64);
const HIEN = {DANG_KIEM: "Đang kế toán kiểm", CHO_BO_SUNG: "Chờ bổ sung", TRA_LAI_CHO_KY_LAI: "Trả lại — chờ quy trình ký lại (chưa mở lại G4)", HIEU_LUC: "Hiệu lực",
  CHUA_KIEM: "Đã ký — chờ kế toán kiểm"};
const HD_CUA = {[KY1]: HD1, [KY2]: HD2}, HO_CUA = {[KY1]: HO1, [KY2]: HO2}, MA_CUA = {[KY1]: "HD-NB-1", [KY2]: "HD-NB-2"};
const DSK = (l, tt = {}) => ({nguoi: {dang_nhap: l}, ds: l === KT ? [KY1, KY2].map(id => ({ky_id: id, hop_dong_id: HD_CUA[id], ma_noi_bo: MA_CUA[id],
  ngay_ky: "2026-10-20", trang_thai: (tt[id] || ["CHUA_KIEM"])[0], hien_thi: HIEN[(tt[id] || ["CHUA_KIEM"])[0]], revision: (tt[id] || ["CHUA_KIEM", 0])[1] || 0})) : []});
const HO_SO = (id, tt, rev, sua = {}) => ({ho_so_id: HO_CUA[id], ky_id: id, hop_dong_id: HD_CUA[id], trang_thai: tt, hien_thi: HIEN[tt], revision: rev, viec_id: VIEC,
  hieu_luc: null, phu_thuoc: tt === "TRA_LAI_CHO_KY_LAI" ? "CRM_G6A_TRA_LAI_CHO_G4_KY_LAI" : null, ...sua});
const CL_DU = {ban_ky_dung_ban_xuat: "XAC_NHAN", ben_ky_dung: "XAC_NHAN", dieu_khoan_dung: "XAC_NHAN", gia_tri_lich_dung: "XAC_NHAN", khach_dung: "XAC_NHAN"};
const REV = (rev = 1) => ({rev_id: "88888888-8888-4888-8888-88888888888" + rev, revision: rev, checklist: CL_DU, de_xuat_doi_tac_id: DT, de_xuat_ma_junsky_id: MJ,
  ma_junsky: "****0001", ngay_hieu_luc: "2026-11-01", can_cu_ngay: "DIEU_KHOAN_HD", trich_dan_ngay: "Điều 12: hiệu lực từ 01/11/2026", ghi_chu: null, tao_boi: KT,
  tao_luc: "2026-10-22T02:00:00Z"});
const G5_HOLD = {che_do: "VAN_HANH", trang_thai: "HOLD", khoi_tao: {trang_thai: "NOT_SELECTED", ly_do: "CHUA_AP_DUNG_CHON_MAU"}, lech: [], chan: [{ma: "UNREGISTERED_G5_PROOF"}]};
const CHECK = (id, ketLuan, rev = 1) => ({check_id: id, ho_so_revision: rev, ket_luan: ketLuan, chan: ketLuan === "DU_DIEU_KIEN" ? [] : [{ma: "UNREGISTERED_G5_PROOF"}],
  canh_bao: [], do_thi_sha256: SHA_DT, g5_che_do: "VAN_HANH", tao_luc: "2026-10-22T03:00:00Z"});
const DOC = (id, sua = {}) => ({ky: {ky_id: id, hop_dong_id: HD_CUA[id], ma_noi_bo: MA_CUA[id], revision: 2, ngay_ky: "2026-10-20", nguoi_ky_khach: "****1234",
  co_sua: false, mo_ta_sua: null, ky_pdf_sha256: "c".repeat(64), ky_pdf_len: 2048, ky_so_trang: 1, g3_pdf_sha256: "a".repeat(64), g3_pdf_len: 1234, ma_mau: "HD",
  phien_ban_mau: 1, danh_muc_ref: "DM", danh_muc_rev: 1, tao_boi: BH, g5_khoi_tao: {trang_thai: "NOT_SELECTED", ly_do: "CHUA_AP_DUNG_CHON_MAU", la_bang_chung: false}},
  quyen: {kiem: true, ly_do: null}, hop_dong: {crm_giao_ket: "DA_KY", doi_tac_id: null}, khach_ban_ky: {doi_tac_id: DT, du_thao_ten: null, du_thao_lien_he: null},
  ma_junsky_ung_vien: [{id: MJ, doi_tac_id: DT, tien_to: "KH", object_id: "****0001", ten: "****DEMO"}], ho_so: null, rev: null,
  truong: [{ten: "so_hop_dong", nhan: "Số HĐ", kieu: "text", nhom: "Chung", pii: false, bat_buoc: true, gia_tri: "HĐ-1", vi_tri: null, trang_thai_can_cu: "CO_CAN_CU"}],
  lich: {tien_te: "VND", scale: 0, tong_minor: "1000000000", tong_dong_minor: "1000000000", loi: [],
    dong: [{dot: 1, lan: "1", loai: "PERCENT", ty_le: "100", so_tien_minor: "1000000000", moc: "NGAY:2026-11-01", han: "2026-11-01", loi: []}]},
  g7: {trang_thai: "KHONG_AP_DUNG", lech: []}, g5: G5_HOLD, check: null, xu_ly_lech: [], lich_su: [], tom_tat: {so_dong: 1, tong_minor: "1000000000", tien_te: "VND"},
  g5_che_do: "VAN_HANH", ...sua});
const KQ = (id, tt, rev, sua = {}) => ({...HO_SO(id, tt, rev), lap_lai: false, ...sua});
const TRUONG = {luu: ["can_cu_ngay", "checklist", "doi_tac_id", "expected_revision", "ghi_chu", "khoa", "ky_id", "ma_junsky_id", "ngay_hieu_luc", "trich_dan_ngay"],
  check: ["expected_revision", "khoa", "ky_id"], "xu-ly-lech": ["expected_revision", "khoa", "ky_id", "loai", "ly_do", "ma_lech", "muc_tieu_id"],
  "bo-sung": ["expected_revision", "khoa", "ky_id", "ly_do"], "tra-lai": ["expected_revision", "khoa", "ky_id", "ly_do"],
  "hieu-luc": ["check_id", "do_thi_sha256", "expected_revision", "khoa", "ky_id"], "tim-junsky": ["ky_id", "tu_khoa"]};
const KHONG_NHAN = ["g5_che_do", "che_do", "synthetic", "ket_luan", "chan", "do_thi", "hop_dong_id", "phien_ban_id", "chung_tu_id", "quyet_dinh_id", "g5", "g7",
  "dang_nhap", "nguoi", "actor", "phap_nhan", "phap_nhan_id", "trang_thai", "vai_tro"];

async function main() {
  const {document, calls, ctx} = moiTruong();
  vm.runInContext(APP, ctx, {filename: "app.js"});
  const ngheHash = [];
  ctx.addEventListener = (t, fn) => { if (t === "hashchange") ngheHash.push(fn); };
  vm.runInContext(CRMG, ctx, {filename: "crm_g.js"});
  async function diHash(h) { ctx.location.hash = h; for (const fn of ngheHash) fn({}); await chay(); }
  const $ = id => document.getElementById(id);
  const conLai = pred => calls.filter(c => !c.xong && pred(c));
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const get = url => c => c.method === "GET" && c.url === url;
  const post = url => c => c.method === "POST" && c.url === url;
  const getDsK = get("/api/crm/giao-ket/kiem"), getCt = id => get(`/api/crm/giao-ket/kiem/${id}`), postK = h => post(`/api/crm/giao-ket/kiem/${h}`);
  const sec = () => $("crm-kiem");
  const o = id => $("kh-" + id);
  const trangThaiK = () => tim(sec(), e => e.attrs && e.attrs.role === "status");
  const toastTxt = () => ($("toast") || {textContent: ""}).textContent;
  const datToast = s => { if ($("toast")) $("toast").textContent = s; };
  const nutLai = () => nut(sec(), "Gửi lại y nguyên (cùng khóa)");
  const than = c => JSON.parse(c.opts.body);
  const h4 = () => (tim(sec(), e => e.tagName === "H4") || {textContent: ""}).textContent;
  async function traKhac() {
    for (const c of conLai(c => !/^\/api\/crm(\/giao-ket\/kiem|\/danh-tinh|$)/.test(c.url))) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND"})); }
    await chay();
  }
  async function traDs(l, tt) { for (const c of conLai(getDsK)) { c.xong = true; c.resolve(phanHoi(200, DSK(l, tt))); } await chay(); }
  async function traCt(id, doc) { for (const c of conLai(getCt(id))) { c.xong = true; c.resolve(phanHoi(200, doc)); } await chay(); }
  async function traLamMoi(id, doc, tt) { await traDs(KT, tt); await traKhac(); await traCt(id, doc); }
  async function moKy(id, doc) {
    const tr = tim(sec(), e => e.tagName === "TR" && e.textContent.includes(MA_CUA[id]));
    assert.ok(tr, "không thấy dòng " + MA_CUA[id]);
    nut(tr, "Mở").click(); await chay();
    cho(getCt(id), "GET chi tiết " + id).resolve(phanHoi(200, doc)); await chay();
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
  function go(id, v, ev = "input") { const el = o(id); assert.ok(el, "không thấy ô kh-" + id); el.value = v; el.dispatch(ev); }

  // khởi động vai KT
  assert.ok(sec(), "chưa dựng khối #crm-kiem sau #crm-gk");
  for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM(KT))); }
  await traKhac();
  await traDs(KT);
  await traKhac();

  // ---------------------------------------------------------------- H0 dương: danh sách → chi tiết; G5 HOLD trung thực
  {
    assert.ok(sec().textContent.includes("HD-NB-1") && sec().textContent.includes("HD-NB-2"), "H0: danh sách thiếu hợp đồng đã ký");
    await moKy(KY1, DOC(KY1));
    const t = sec().textContent;
    assert.ok(t.includes("c".repeat(64)) && t.includes("a".repeat(64)), "H0: thiếu hash bản ký/G3");
    assert.ok(t.includes("không phải ngày hiệu lực"), "H0: thiếu nhắc ngày ký ≠ ngày hiệu lực");
    assert.ok(t.includes("HOLD") && t.includes("UNREGISTERED_G5_PROOF"), "H0: G5 không hiện HOLD/UNREGISTERED_G5_PROOF");
    assert.ok(t.includes("không phải bằng chứng"), "H0: G5 khởi tạo G4 bị trình bày như bằng chứng");
    assert.ok(!/KHỚP|MATCH/.test(t), "H0: G5 vận hành bị suy thành khớp");
    const g5p = tim(sec(), e => e.dataset && e.dataset.g5 !== undefined && e.dataset.g5 !== "");
    assert.strictEqual(g5p && g5p.dataset.g5, "HOLD", "H0: nhãn G5 dữ liệu không phải HOLD");
    assert.ok(nut(sec(), "Kích hoạt hiệu lực").disabled, "H0: kích hoạt bật khi chưa có check đủ điều kiện");
    assert.ok(nut(sec(), "Chạy check").disabled, "H0: chạy check bật khi chưa có hồ sơ kiểm");
    assert.ok(nut(sec(), "Lưu kiểm") && !nut(sec(), "Lưu kiểm").disabled, "H0: thiếu nút Lưu kiểm");
    console.log("H0 đạt");
  }

  // ---------------------------------------------------------------- H1 ngày hiệu lực thiếu căn cứ → 0 POST
  {
    go("ngay", "2026-11-01");
    nut(sec(), "Lưu kiểm").click(); await chay();
    assert.strictEqual(dem(postK("luu")), 0, "H1: gửi khi ngày hiệu lực thiếu căn cứ/trích dẫn");
    assert.ok(trangThaiK().textContent.includes("căn cứ"), "H1: thiếu thông báo căn cứ ngày hiệu lực");
    assert.ok(nut(sec(), "Chạy check").disabled, "H1: chạy check không bị vô hiệu khi có thay đổi chưa lưu");
    console.log("H1 đạt");
  }

  // ---------------------------------------------------------------- H2 Lưu kiểm: bấm lặp → 1 POST; thân đúng hợp đồng
  {
    for (const k of Object.keys(CL_DU)) go("cl-" + k, "XAC_NHAN", "change");
    go("junsky", MJ, "change"); go("can-cu", "DIEU_KHOAN_HD", "change"); go("trich", "Điều 12: hiệu lực từ 01/11/2026");
    nut(sec(), "Lưu kiểm").click(); nut(sec(), "Lưu kiểm").click(); await chay();
    assert.strictEqual(conLai(postK("luu")).length, 1, "H2: bấm lặp gửi thêm POST");
    const p = cho(postK("luu"), "POST lưu");
    nut(sec(), "Lưu kiểm").click(); await chay();
    assert.strictEqual(conLai(postK("luu")).length, 0, "H2: POST thứ hai khi lần đầu còn chờ");
    const b = than(p);
    assert.deepStrictEqual(Object.keys(b).sort(), TRUONG.luu, "H2: thân có trường ngoài hợp đồng");
    assert.deepStrictEqual([b.ky_id, b.expected_revision, b.doi_tac_id, b.ma_junsky_id, b.ngay_hieu_luc, b.can_cu_ngay], [KY1, 0, DT, MJ, "2026-11-01", "DIEU_KHOAN_HD"],
      "H2: thân sai bản ký/revision/khách/ngày");
    assert.deepStrictEqual(b.checklist, CL_DU, "H2: checklist sai");
    assert.ok(typeof b.khoa === "string" && b.khoa.startsWith("crmkiem-"), "H2: thiếu khóa");
    datToast("");
    p.resolve(phanHoi(200, KQ(KY1, "DANG_KIEM", 1))); await chay();
    assert.ok(toastTxt().includes("Đã lưu kiểm (revision 1)"), "H2: ACK đúng không hiển thị");
    await traLamMoi(KY1, DOC(KY1, {ho_so: HO_SO(KY1, "DANG_KIEM", 1), rev: REV(1)}), {[KY1]: ["DANG_KIEM", 1]});
    assert.ok(h4().includes("Đang kế toán kiểm"), "H2: không làm mới về hồ sơ đang kiểm");
    assert.ok(!nut(sec(), "Chạy check").disabled, "H2: chạy check chưa bật sau khi lưu");
    console.log("H2 đạt");
  }

  // ---------------------------------------------------------------- H3 chưa rõ → giữ ý định; ACK lệch vẫn chưa rõ; gửi lại y nguyên
  {
    nut(sec(), "Chạy check").click(); await chay();
    const p1 = cho(postK("check"), "POST check gốc");
    assert.deepStrictEqual(Object.keys(than(p1)).sort(), TRUONG.check, "H3: thân check có trường ngoài hợp đồng (chế độ G5/kết quả)");
    p1.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(nutLai(), "H3: thiếu nút gửi lại y nguyên");
    nut(sec(), "Lưu kiểm").click(); await chay();
    assert.strictEqual(dem(postK("luu")), 1, "H3: lệnh khác chen khi ý định trước chưa rõ");
    assert.ok(trangThaiK().textContent.includes("chưa rõ"), "H3: thiếu thông báo chặn ý định khác");
    nutLai().click(); await chay();
    const p2 = cho(postK("check"), "POST check gửi lại");
    assert.strictEqual(p2.opts.body, p1.opts.body, "H3: gửi lại khác body/khóa gốc");
    datToast("SENTINEL-H3");
    p2.resolve(phanHoi(200, KQ(KY1, "DANG_KIEM", 1, {check: {...CHECK(CK1, "CHUA_DU_DIEU_KIEN"), g5_che_do: "SYNTHETIC_FIXTURE"}}))); await chay();
    assert.ok(!toastTxt().includes("Đã chạy check"), "H3: ACK lệch chế độ G5 bị coi là FINAL");
    assert.ok(nutLai(), "H3: ACK lệch làm mất ý định chưa rõ");
    for (const ackSai of [null, {}, KQ(KY2, "DANG_KIEM", 1, {check: CHECK(CK1, "CHUA_DU_DIEU_KIEN")}), KQ(KY1, "DANG_KIEM", 1, {check: {...CHECK(CK1, "DU_DIEU_KIEN"), chan: [{ma: "X"}]}})]) {
      nutLai().click(); await chay();
      const px = cho(postK("check"), "POST check gửi lại (ACK sai)");
      assert.strictEqual(px.opts.body, p1.opts.body, "H3: gửi lại khác body/khóa gốc (vòng ACK sai)");
      px.resolve(phanHoi(200, ackSai)); await chay();
      assert.ok(!toastTxt().includes("Đã chạy check") && nutLai(), "H3: ACK sai " + JSON.stringify(ackSai) + " bị coi là FINAL");
    }
    nutLai().click(); await chay();
    const p3 = cho(postK("check"), "POST check gửi lại lần cuối");
    assert.strictEqual(p3.opts.body, p1.opts.body, "H3: gửi lại lần cuối khác body/khóa gốc");
    p3.resolve(phanHoi(200, KQ(KY1, "DANG_KIEM", 1, {check: CHECK(CK1, "CHUA_DU_DIEU_KIEN")}))); await chay();
    assert.ok(toastTxt().includes("Đã chạy check: chưa đủ điều kiện (1 mục chặn)"), "H3: ACK đúng không FINAL");
    assert.strictEqual(nutLai(), null, "H3: FINAL vẫn giữ nút gửi lại");
    await traLamMoi(KY1, DOC(KY1, {ho_so: HO_SO(KY1, "DANG_KIEM", 1), rev: REV(1), check: CHECK(CK1, "CHUA_DU_DIEU_KIEN")}), {[KY1]: ["DANG_KIEM", 1]});
    assert.ok(nut(sec(), "Kích hoạt hiệu lực").disabled, "H3: kích hoạt bật khi check còn chặn (G5 HOLD)");
    console.log("H3 đạt");
  }

  // ---------------------------------------------------------------- H4 vai A→B→A: ACK/lỗi cũ im lặng
  {
    nut(sec(), "Chạy check").click(); await chay();
    const p4 = cho(postK("check"), "POST check H4");
    const khoa4 = than(p4).khoa;
    await doiVai(BH);
    assert.ok(!sec().textContent.includes("HD-NB-1"), "H4: vai B thấy danh sách của vai A");
    assert.strictEqual(nutLai(), null, "H4: vai B thấy nút gửi lại của vai A");
    await doiVai(KT);
    datToast("SENTINEL-H4");
    let nDs = dem(getDsK), nCt = dem(getCt(KY1));
    p4.resolve(phanHoi(200, KQ(KY1, "DANG_KIEM", 1, {check: CHECK(CK2, "CHUA_DU_DIEU_KIEN")}))); await chay();
    assert.strictEqual(toastTxt(), "SENTINEL-H4", "H4: ACK cũ sau A→B→A vẫn toast");
    assert.deepStrictEqual([dem(getDsK), dem(getCt(KY1))], [nDs, nCt], "H4: ACK cũ mở GET làm mới");
    assert.ok(!trangThaiK().textContent.includes("Đã chạy check"), "H4: ACK cũ ghi trạng thái");
    // lỗi xác định cũ cũng im lặng
    await moKy(KY1, DOC(KY1, {ho_so: HO_SO(KY1, "DANG_KIEM", 1), rev: REV(1), check: CHECK(CK1, "CHUA_DU_DIEU_KIEN")}));
    assert.strictEqual(nutLai(), null, "H4: ý định đã FINAL (ACK hợp lệ cũ) vẫn hiện gửi lại");
    nut(sec(), "Chạy check").click(); await chay();
    const p5 = cho(postK("check"), "POST check H4 lỗi");
    assert.notStrictEqual(than(p5).khoa, khoa4, "H4: ý định mới dùng lại khóa đã FINAL");
    await doiVai(BH); await doiVai(KT);
    datToast("SENTINEL-H4B");
    nDs = dem(getDsK); nCt = dem(getCt(KY1));
    p5.resolve(phanHoi(409, {error: "CRM_KIEM_REVISION_CU", message: "hồ sơ kiểm đã có revision mới"})); await chay();
    assert.strictEqual(toastTxt(), "SENTINEL-H4B", "H4: lỗi cũ sau A→B→A vẫn toast");
    assert.deepStrictEqual([dem(getDsK), dem(getCt(KY1))], [nDs, nCt], "H4: lỗi cũ mở GET làm mới");
    console.log("H4 đạt");
  }

  // ---------------------------------------------------------------- H5 GET chi tiết cũ về sau GET mới → không ghi đè
  {
    const tr = tim(sec(), e => e.tagName === "TR" && e.textContent.includes("HD-NB-1"));
    nut(tr, "Mở").click(); await chay();
    const d1 = cho(getCt(KY1), "GET chi tiết cũ");
    nut(sec(), "↻ Làm mới").click(); await chay();
    // ↻ của khối crm-kiem (nút đầu tiên trong #crm-kiem)
    await traDs(KT, {[KY1]: ["DANG_KIEM", 1]}); await traKhac();
    const d2 = cho(getCt(KY1), "GET chi tiết mới");
    d2.resolve(phanHoi(200, DOC(KY1, {ho_so: HO_SO(KY1, "DANG_KIEM", 1), rev: REV(1), check: CHECK(CK2, "DU_DIEU_KIEN")}))); await chay();
    d1.resolve(phanHoi(200, DOC(KY1))); await chay();
    assert.ok(h4().includes("Đang kế toán kiểm"), "H5: GET cũ ghi đè trạng thái mới");
    assert.ok(!nut(sec(), "Kích hoạt hiệu lực").disabled, "H5: GET cũ lùi điều kiện kích hoạt");
    console.log("H5 đạt");
  }

  // ---------------------------------------------------------------- H6 tải PDF: blob về sau điều hướng → không click; đối chứng dương
  {
    const n0 = soClickTai;
    nut(sec(), "PDF bản ký ↓").click(); await chay();
    const t = cho(get(`/api/crm/giao-ket/kiem/${KY1}/tep/ban-ky`), "GET PDF bản ký");
    const bt = blobTreo(); t.resolve(bt.res); await chay();
    await diHash("#hoso"); await diHash("#hopdong");
    await traLamMoi(KY1, DOC(KY1, {ho_so: HO_SO(KY1, "DANG_KIEM", 1), rev: REV(1), check: CHECK(CK2, "DU_DIEU_KIEN")}), {[KY1]: ["DANG_KIEM", 1]});
    bt.ra(100); await chay();
    assert.strictEqual(soClickTai, n0, "H6: blob về sau đi-rồi-về vẫn click tải");
    nut(sec(), "PDF bản xuất G3 ↓").click(); await chay();
    cho(get(`/api/crm/giao-ket/kiem/${KY1}/tep/g3`), "GET PDF G3").resolve(phanHoi(200, {}, 10)); await chay();
    assert.strictEqual(soClickTai, n0 + 1, "H6: đối chứng dương không click đúng 1 lần");
    console.log("H6 đạt");
  }

  // ---------------------------------------------------------------- H7 kích hoạt (MOCK ACK — không phải nghiệm thu)
  {
    nut(sec(), "Kích hoạt hiệu lực").click(); nut(sec(), "Kích hoạt hiệu lực").click(); await chay();
    assert.strictEqual(conLai(postK("hieu-luc")).length, 1, "H7: bấm lặp gửi thêm POST");
    const p = cho(postK("hieu-luc"), "POST hiệu lực");
    const b = than(p);
    assert.deepStrictEqual(Object.keys(b).sort(), TRUONG["hieu-luc"], "H7: thân kích hoạt có trường ngoài hợp đồng");
    assert.deepStrictEqual([b.ky_id, b.expected_revision, b.check_id, b.do_thi_sha256], [KY1, 1, CK2, SHA_DT], "H7: kích hoạt không theo đúng check đã xem");
    const HL = {phien_ban_id: PB, chung_tu_id: CT, so_dong_lich: 1, so_tham_so: 3, tong_minor: "1000000000", tien_te: "VND", g7_trang_thai: "KHONG_AP_DUNG",
      g5_che_do: "VAN_HANH", viec_cfo_id: null};
    datToast("SENTINEL-H7");
    p.resolve(phanHoi(200, KQ(KY1, "HIEU_LUC", 1, {hop_dong_id: HD_KHAC, hieu_luc: HL}))); await chay();
    assert.ok(!toastTxt().includes("HIỆU LỰC") && nutLai(), "H7: ACK lệch hợp đồng bị coi là FINAL");
    nutLai().click(); await chay();
    const p2 = cho(postK("hieu-luc"), "POST hiệu lực gửi lại");
    assert.strictEqual(p2.opts.body, p.opts.body, "H7: gửi lại khác body/khóa gốc");
    p2.resolve(phanHoi(200, KQ(KY1, "HIEU_LUC", 1, {hieu_luc: HL}))); await chay();
    assert.ok(toastTxt().includes("HIỆU LỰC") && toastTxt().includes("1 đợt lịch thu"), "H7: ACK đúng không FINAL");
    await traLamMoi(KY1, DOC(KY1, {ho_so: HO_SO(KY1, "HIEU_LUC", 1, {hieu_luc: HL}), rev: REV(1), check: CHECK(CK2, "DU_DIEU_KIEN"),
      hop_dong: {crm_giao_ket: "HIEU_LUC", doi_tac_id: DT}}), {[KY1]: ["HIEU_LUC", 1]});
    assert.ok(sec().textContent.includes("Đã HIỆU LỰC"), "H7: không hiện trạng thái hiệu lực");
    assert.strictEqual(nut(sec(), "Lưu kiểm"), null, "H7: còn form kiểm sau hiệu lực");
    assert.strictEqual(nut(sec(), "Kích hoạt hiệu lực"), null, "H7: còn nút kích hoạt sau hiệu lực");
    console.log("H7 đạt");
  }

  // ---------------------------------------------------------------- H8 trả lại: chờ ký lại, KHÔNG về nháp
  {
    await moKy(KY2, DOC(KY2, {ho_so: HO_SO(KY2, "DANG_KIEM", 1), rev: REV(1)}));
    nut(sec(), "Trả lại (chờ ký lại)").click(); await chay();
    assert.strictEqual(dem(postK("tra-lai")), 0, "H8: gửi trả lại khi thiếu lý do");
    go("ly-do", "Người ký phía khách không đúng đại diện");
    nut(sec(), "Trả lại (chờ ký lại)").click(); await chay();
    const p = cho(postK("tra-lai"), "POST trả lại");
    assert.deepStrictEqual(Object.keys(than(p)).sort(), TRUONG["tra-lai"], "H8: thân trả lại có trường ngoài hợp đồng");
    datToast("SENTINEL-H8");
    p.resolve(phanHoi(200, KQ(KY2, "TRA_LAI_CHO_KY_LAI", 1, {ket_qua: "CHAN_PHU_THUOC", phu_thuoc: "CRM_G6A_TRA_LAI_CHO_G4_KY_LAI", g4_trang_thai: "SOAN_THAO"})));
    await chay();
    assert.ok(!toastTxt().includes("Đã trả lại") && nutLai(), "H8: ACK 'về nháp' bị coi là FINAL");
    nutLai().click(); await chay();
    const p2 = cho(postK("tra-lai"), "POST trả lại gửi lại");
    assert.strictEqual(p2.opts.body, p.opts.body, "H8: gửi lại khác body/khóa gốc");
    p2.resolve(phanHoi(200, KQ(KY2, "TRA_LAI_CHO_KY_LAI", 1, {ket_qua: "CHAN_PHU_THUOC", phu_thuoc: "CRM_G6A_TRA_LAI_CHO_G4_KY_LAI", g4_trang_thai: "DA_KY"})));
    await chay();
    assert.ok(toastTxt().includes("chờ quy trình ký lại") && toastTxt().includes("KHÔNG về nháp"), "H8: thông báo trả lại sai nghĩa");
    await traLamMoi(KY2, DOC(KY2, {ho_so: HO_SO(KY2, "TRA_LAI_CHO_KY_LAI", 1), rev: REV(1)}), {[KY1]: ["HIEU_LUC", 1], [KY2]: ["TRA_LAI_CHO_KY_LAI", 1]});
    const t = sec().textContent;
    assert.ok(t.includes("chờ quy trình ký lại (chưa mở lại G4)"), "H8: không hiện trạng thái chờ ký lại");
    assert.ok(!/Đã về nháp|Về nháp thành công|Đang soạn/.test(t), "H8: trình bày như đã về nháp");
    assert.strictEqual(nut(sec(), "Lưu kiểm"), null, "H8: còn form kiểm sau trả lại");
    assert.strictEqual(nut(sec(), "Kích hoạt hiệu lực"), null, "H8: còn nút kích hoạt sau trả lại");
    console.log("H8 đạt");
  }

  // ---------------------------------------------------------------- H9 không có quyền kiểm (tách nhiệm) → không form/lệnh
  {
    nut(sec(), "↻ Làm mới").click(); await chay();
    await traLamMoi(KY2, DOC(KY2, {quyen: {kiem: false, ly_do: "CRM_G_CUNG_NGUOI"}}), {[KY1]: ["HIEU_LUC", 1]});
    assert.ok(sec().textContent.includes("tách nhiệm"), "H9: thiếu lý do tách nhiệm");
    assert.strictEqual(nut(sec(), "Lưu kiểm"), null, "H9: hiện form kiểm khi không có quyền");
    assert.strictEqual(nut(sec(), "Chạy check"), null, "H9: hiện lệnh khi không có quyền");
    console.log("H9 đạt");
  }

  // ---------------------------------------------------------------- H10 P1-B khách dự thảo (bản ký + hợp đồng doi_tac NULL): tra cứu mã CÓ SẴN → chọn → Lưu
  {
    const MJ2 = "99999999-9999-4999-8999-000000000002", DT2 = "aaaaaaaa-aaaa-4aaa-8aaa-000000000002";
    const DOC_DT = (sua = {}) => DOC(KY2, {khach_du_thao: true, khach_ban_ky: {doi_tac_id: null, du_thao_ten: "****KHACH", du_thao_lien_he: "****99"},
      hop_dong: {crm_giao_ket: "DA_KY", doi_tac_id: null}, ma_junsky_ung_vien: [], ...sua});
    const UV2 = {id: MJ2, doi_tac_id: DT2, tien_to: "KH", object_id: "KH_DEMO.A01", khop_ma: true, ten: "****DEMO"};
    const tuKhoa = v => { const el = $("kiem-tim-junsky"); assert.ok(el, "H10: thiếu ô tra cứu mã Junsky cho khách dự thảo"); el.value = v; el.dispatch("input"); };
    const giaTriJunsky = () => (o("junsky") ? o("junsky").children.filter(c => c.tagName === "OPTION").map(c => c.value) : []);
    const postTim = postK("tim-junsky");
    nut(sec(), "↻ Làm mới").click(); await chay();
    await traLamMoi(KY2, DOC_DT(), {[KY1]: ["HIEU_LUC", 1]});
    assert.ok(nut(sec(), "Tìm mã Junsky có sẵn"), "H10: thiếu nút tra cứu mã Junsky có sẵn");
    assert.ok(sec().textContent.includes("không tạo mã"), "H10: thiếu nhắc G6A không tạo mã");
    assert.deepStrictEqual(giaTriJunsky(), [""], "H10: khách dự thảo đã có ứng viên trước khi tra cứu");
    // từ khóa ngắn → 0 POST; gõ ô tra cứu không làm bẩn form (không phải nội dung kiểm)
    tuKhoa("KH"); nut(sec(), "Tìm mã Junsky có sẵn").click(); await chay();
    assert.strictEqual(dem(postTim), 0, "H10: gửi tra cứu với từ khóa < 3 ký tự");
    assert.ok(trangThaiK().textContent.includes("3–60"), "H10: thiếu thông báo độ dài từ khóa");
    // tra cứu cũ về sau A→B→A → bỏ (không thêm ứng viên vào bản ký mở lại)
    tuKhoa("KH_DEMO"); nut(sec(), "Tìm mã Junsky có sẵn").click(); await chay();
    const pCu = cho(postTim, "POST tra cứu (sẽ cũ)");
    assert.deepStrictEqual(than(pCu), {ky_id: KY2, tu_khoa: "KH_DEMO"}, "H10: thân tra cứu khác {ky_id, tu_khoa}");
    await doiVai(BH); await doiVai(KT);
    await moKy(KY2, DOC_DT());
    datToast("SENTINEL-H10");
    pCu.resolve(phanHoi(200, {ky_id: KY2, ung_vien: [UV2], gioi_han: 10})); await chay();
    assert.ok(!giaTriJunsky().includes(MJ2), "H10: phản hồi tra cứu cũ (A→B→A) thêm ứng viên vào bản ký mở lại");
    assert.ok(!trangThaiK().textContent.includes("Tìm thấy"), "H10: phản hồi tra cứu cũ ghi trạng thái");
    // khách đã định danh (máy chủ 409) → thông báo + đọc lại chi tiết, không thêm ứng viên
    tuKhoa("KH_DEMO"); nut(sec(), "Tìm mã Junsky có sẵn").click(); await chay();
    cho(postTim, "POST tra cứu 409").resolve(phanHoi(409, {error: "CRM_KIEM_KHACH_DA_DINH", message: "khách đã định danh"})); await chay();
    await traCt(KY2, DOC_DT());
    assert.ok(trangThaiK().textContent.includes("đã được định danh"), "H10: thiếu thông báo khách đã định danh");
    // phản hồi lệch bản ký → không nhận
    tuKhoa("KH_DEMO"); nut(sec(), "Tìm mã Junsky có sẵn").click(); await chay();
    cho(postTim, "POST tra cứu lệch").resolve(phanHoi(200, {ky_id: KY1, ung_vien: [UV2]})); await chay();
    assert.ok(!giaTriJunsky().includes(MJ2), "H10: nhận kết quả tra cứu của bản ký khác");
    // tra cứu đúng → chọn → Lưu: thân mang ĐÚNG cặp đối tác/mã đã chọn
    tuKhoa("KH_DEMO"); nut(sec(), "Tìm mã Junsky có sẵn").click(); await chay();
    const pTim = cho(postTim, "POST tra cứu");
    assert.deepStrictEqual(than(pTim), {ky_id: KY2, tu_khoa: "KH_DEMO"}, "H10: thân tra cứu khác {ky_id, tu_khoa}");
    pTim.resolve(phanHoi(200, {ky_id: KY2, ung_vien: [UV2], gioi_han: 10})); await chay();
    assert.ok(giaTriJunsky().includes(MJ2), "H10: ứng viên tra cứu không vào danh sách chọn");
    for (const k of Object.keys(CL_DU)) go("cl-" + k, "XAC_NHAN", "change");
    go("junsky", MJ2, "change");
    nut(sec(), "Lưu kiểm").click(); await chay();
    const pL = cho(postK("luu"), "POST lưu khách dự thảo");
    const b = than(pL);
    assert.deepStrictEqual(Object.keys(b).sort(), TRUONG.luu, "H10: thân lưu có trường ngoài hợp đồng");
    assert.deepStrictEqual([b.ky_id, b.expected_revision, b.doi_tac_id, b.ma_junsky_id], [KY2, 0, DT2, MJ2], "H10: Lưu không mang đúng cặp đối tác/mã đã chọn");
    pL.resolve(phanHoi(200, KQ(KY2, "DANG_KIEM", 1))); await chay();
    await traLamMoi(KY2, DOC_DT({ho_so: HO_SO(KY2, "DANG_KIEM", 1), rev: {...REV(1), de_xuat_doi_tac_id: DT2, de_xuat_ma_junsky_id: MJ2, ma_junsky: "KH_DEMO.A01"},
      ma_junsky_ung_vien: [UV2]}), {[KY1]: ["HIEU_LUC", 1], [KY2]: ["DANG_KIEM", 1]});
    assert.strictEqual(o("junsky").value, MJ2, "H10: sau làm mới không giữ mã đã lưu");
    console.log("H10 đạt");
  }

  // ---------------------------------------------------------------- HZ mọi POST G6A đúng hợp đồng trường
  {
    const posts = calls.filter(c => c.method === "POST" && c.url.startsWith("/api/crm/giao-ket/kiem"));
    assert.ok(posts.length > 0, "HZ: không có POST G6A nào");
    for (const c of posts) {
      const hanh = c.url.slice("/api/crm/giao-ket/kiem/".length);
      assert.ok(Object.prototype.hasOwnProperty.call(TRUONG, hanh), "HZ: POST ngoài 7 route: " + c.url);
      const keys = Object.keys(than(c));
      assert.ok(keys.every(k => TRUONG[hanh].includes(k)), `HZ: ${hanh} có trường ngoài hợp đồng: ${keys}`);
      assert.ok(!keys.some(k => KHONG_NHAN.includes(k)), `HZ: ${hanh} gửi trường thẩm quyền máy chủ: ${keys}`);
      assert.strictEqual(c.opts.headers["X-KTT-Token"], "TOKEN-THU", "HZ: thiếu token phiên");
    }
    assert.deepStrictEqual(timTatCa(sec(), e => e.tagName === "INPUT" && e.type === "file"), [], "HZ: G6A có ô tải tệp (không được sửa/ghi bản ký)");
    console.log("HZ đạt");
  }

  assert.deepStrictEqual(loiNgoai, [], "có Promise bị từ chối không xử lý");
  console.log("CRM-41-06A async: mọi ca đạt (MOCK DOM — không phải trình duyệt thật; không phải nghiệm thu)");
}

main().catch(e => { console.error(e); process.exitCode = 1; });
