"use strict";
// M4-01C / C2 — kiểm bất đồng bộ trên MÃ THẬT app.js + m4.js (không phải trình duyệt): DOM giả tối thiểu có quan hệ cha–con/kết nối thật,
// fetch trả Promise do ca điều khiển (pending, đảo thứ tự, lỗi, body JSON đứt). CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN).
// Root chạy: `node tests/m4_01c_async.cjs` (Node ≥ 18). Mã thoát 0 = mọi ca đạt; khác 0 = có ca lỗi. Không ghi/xóa tệp, không mạng, không tiến trình con.
// getElementById chỉ trả phần tử ĐANG GẮN vào document (phần tử đã bị replaceChildren gỡ ra không được trả về). unhandledRejection được ghi lại
// và làm FAIL ở cuối (không nuốt). Ca:
//  P0  dương không rỗng: M4 + CRM + M2 + M5 + L11 cùng nạp vai thật sau đổi vai (payload có cấu hình, không dùng cau_hinh:false làm “đạt”).
//  C2-1a POST: gửi A → đổi vai A→B→A → gửi lại cùng body (khóa mới) → lần cũ về trước: không nhả “đang gửi”/khóa của lần mới; bấm lặp vẫn 0 POST;
//        mất kết nối → gửi lại đúng body+khóa; HTTP 200 nhưng JSON đứt → vẫn “chưa rõ” → gửi lại đúng body+khóa.
//  C2-1b tải lên: cùng vòng đời (vé sở hữu, khóa giữ khi JSON đứt, X-M4-Info y nguyên).
//  C2-2 BOQ: đổi tệp khi đọc sheet còn chờ, phản hồi đảo thứ tự, lỗi cũ không vẽ; đổi sheet → nút Nhập gỡ ngay; nhập dương đúng tệp/sheet/header/map đang hiện.
//  C2-3 form: lưu tham số A còn chờ → mở form B và gõ → phản hồi A không đóng/không vẽ đè B; dương: lưu B rồi làm mới. Tệp mẫu còn chờ → đổi mẫu →
//        không gửi mẫu cũ; dương: mẫu hiện tại được gửi.
//  C2-4 hàng đổi vai: POST1 xong, GET nạp lại còn treo → ý định 2 gửi POST2 ngay (không chờ GET); GET1 về trễ không vẽ; ý định từ CRM cũng vậy;
//        GET cũ của M2 bắt đầu trước đổi vai về trễ không vẽ; bytes tải về trễ không click.
//  C3-1 làm mới về trễ: POST thành công → GET HĐ (và GET đợt) còn chờ → mở/nhập form khác → GET về: form + nháp mới còn nguyên; dương: không sửa → làm mới.
//  C3-2 khôi phục sau revision cũ: GET bắt đầu → nhập thêm → GET về: vẽ revision mới với giá trị MỚI NHẤT (không snapshot lúc bắt đầu).
//  C3-3 BOQ: xem trước còn chờ → đổi tab Phụ lục và nhập → phản hồi/lỗi cũ không dựng lại/không mất nháp; quay lại BOQ → xem trước + nhập đúng.
//  C3-4 tải lên chưa rõ: mẫu (HTTP 200 JSON đứt rồi mất kết nối) và tệp thật — gửi lại dùng ĐÚNG File gốc/X-M4-Info, không lấy lại mẫu,
//        bấm lặp 1 POST, kết quả rõ → continuation (làm mới) đúng một lần.
//  C4-01a cùng actor hai dự án/HĐ (DTO tin cậy): tải ở A chưa rõ → bấm HĐ B thật → chi tiết B xong → lấy lại nút gửi lại còn nối (nếu có) → 0 POST;
//        quay lại A cũng không tự gửi.
//  C4-01b chưa rõ (5xx) ở đợt 1 → mở đợt 2 bằng nút thật → nút gửi lại không còn, 0 POST.
//  C4-02 bấm “Dùng tệp mẫu” hai lần trước khi GET mẫu settle (Blob/File gốc của Node, lastModified thay đổi) → 1 GET, 1 POST; bấm khi POST chờ → 0 thêm;
//        dương: đúng bytes/dự án/metadata → làm mới thật → hàng nguồn mới hiện đúng một lần; chưa rõ cùng ngữ cảnh → File gốc, cùng header, 0 GET mẫu.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");
const APP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/app.js"), "utf8");
const M4 = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/m4.js"), "utf8");
// id tĩnh THẬT của shell (index.html) — chỉ những id này được tạo theo nhu cầu; id khác chưa từng gắn → null như trình duyệt
const ID_TINH = new Set([...fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/index.html"), "utf8").matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));

const BLOB_GOC = globalThis.Blob || (() => { try { return require("buffer").Blob; } catch (_) { return null; } })();
const FILE_GOC = globalThis.File || (() => { try { return require("buffer").File; } catch (_) { return null; } })();
const loiNgoai = [];
process.on("unhandledRejection", e => { loiNgoai.push(e); });

// ------------------------------------------------------------------ DOM giả có kết nối thật
let soClickTai = 0;
function moiTruong() {
  const reg = new Map(), dongId = new Set();
  let taoTinh = false;
  class El {
    constructor(tag) {
      this.tagName = String(tag).toUpperCase(); this.children = []; this.parent = null; this._text = ""; this._id = "";
      this.listeners = {}; this.attrs = {}; this.dataset = {}; this.style = {}; this._cls = new Set(); this.files = []; this.disabled = false;
      this.checked = false; this.selected = false; this._value = ""; this._valueSet = false; this.type = ""; this.title = "";
    }
    get id() { return this._id; }
    set id(v) { this._id = v; if (!reg.has(v)) reg.set(v, []); reg.get(v).push(this); if (!taoTinh) dongId.add(v); }
    get isConnected() { let e = this; while (e) { if (e === body) return true; e = e.parent; } return false; }
    get className() { return [...this._cls].join(" "); }
    set className(v) { this._cls = new Set(String(v || "").split(/\s+/).filter(Boolean)); }
    get classList() { const s = this; return {add: (...c) => c.forEach(x => s._cls.add(x)), remove: (...c) => c.forEach(x => s._cls.delete(x)),
      toggle: (c, on) => { const v = on === undefined ? !s._cls.has(c) : on; if (v) s._cls.add(c); else s._cls.delete(c); return v; }, contains: c => s._cls.has(c)}; }
    get value() {
      if (this.tagName === "SELECT" && !this._valueSet) { const ops = this.children.filter(c => c.tagName === "OPTION"); const s = ops.find(o => o.selected) || ops[0]; return s ? s.value : ""; }
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
    click() { if (this.tagName === "A") soClickTai += 1; return this.dispatch("click"); }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    removeAttribute(k) { delete this.attrs[k]; }
    getAttribute(k) { return this.attrs[k] ?? null; }
    focus() {} showModal() {} close() {}
  }
  const body = new El("body");
  const document = {
    body, title: "",
    // phần tử tĩnh của index.html tạo theo nhu cầu và GẮN vào body; id do script tạo chỉ trả khi phần tử đang gắn vào trang
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
  // như trình duyệt: không khai lastModified → thời điểm tạo (mỗi lần tạo một giá trị khác) — không cố định để che lỗi khóa theo thời điểm
  // C4: ưu tiên Blob/File GỐC của Node (như trình duyệt: lastModified mặc định = thời điểm tạo); chỉ khi Node không có mới dùng lớp thay thế
  let soFile = 0;
  class FileThay { constructor(parts, name, o = {}) { this.name = name; this.type = o.type || ""; this.size = parts.reduce((n, p) => n + (p.size ?? p.byteLength ?? 0), 0);
    this.lastModified = o.lastModified ?? (Date.now() + (++soFile)); } }
  const File = FILE_GOC || FileThay;
  let soUuid = 0;
  const ctx = {
    document, Node: El, console, setTimeout, clearTimeout, Promise, Map, Set, JSON, Math, Date, Number, String, Object, Array, Error, TypeError, SyntaxError,
    encodeURIComponent, decodeURIComponent, URLSearchParams, location: {hash: "#m4"}, crypto: {randomUUID: () => "uuid-" + (++soUuid)},
    URL: {createObjectURL: () => "blob:x", revokeObjectURL() {}}, fetch, File, navigator: {},
  };
  ctx.window = ctx;
  const wl = {};
  ctx.addEventListener = (t, fn) => { (wl[t] = wl[t] || []).push(fn); };
  vm.createContext(ctx);
  return {ctx, document, calls, wl};
}

const JSON_DUT = Symbol("json-dut");
function phanHoi(status, data, blobSize) {
  return {ok: status >= 200 && status < 300, status, headers: {get: () => "application/json"},
    json: async () => { if (data === JSON_DUT) throw new SyntaxError("Unexpected end of JSON input"); return data; },
    blob: async () => (BLOB_GOC ? new BLOB_GOC([new Uint8Array(blobSize ?? 0)], {type: "application/octet-stream"}) : {size: blobSize ?? 0, type: "application/octet-stream"})};
}
const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 8) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
const nutTheoChu = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));

const DEMO = [{dang_nhap: "MO_PHONG_DU_AN_A1", vai_tro: "DU_AN"}, {dang_nhap: "MO_PHONG_DU_AN_B1", vai_tro: "DU_AN"}, {dang_nhap: "MO_PHONG_DU_AN_A2", vai_tro: "DU_AN"}];
const TONG = login => ({cau_hinh: true, nguoi: {dang_nhap: login, vai_tro: "DU_AN"}, ghi_nguon: {san_sang: true, ly_do: null},
  pham_vi: [{du_an_id: "da1", vai: "PHU_TRACH", du_an: "Dự án A1", du_an_ma: "DA_XD_A1", phap_nhan: "PN_DEMO_A", soan: true, xem: true}],
  hop_dong: [{id: "hd-" + login, ten: "Gói " + login, so_hop_dong: "SO-" + login, du_an_id: "da1", du_an: "Dự án A1", phap_nhan: "PN_DEMO_A", revision: 3,
    trang_thai_pl: "CHUA_KHAI", co_tep: true, soan: true, so_dot: 0}],
  dot: [], danh_muc_ho_so: [], nhanh_sau: [], tai_len_toi_da_byte: 52428800, danh_tinh_demo: DEMO});
const TS = (ma, ten) => ({ma, nhom: "Thông tin chung", ten, trang_thai: "CHUA_CO", gia_tri: null, don_vi: null, dieu_khoan: null, trich_dan: null, kiem_tra: null,
  ly_do: null, vi_tri: null, nguon: "CHUA_CO", gia_tri_may: null});
const TEP = (id, vai, ten) => ({id, vai_tro_tai_lieu: vai, ten_goc: ten, media_type: "x", byte_length: 10, raw_sha256: "a".repeat(64), tao_boi: "X", tao_luc: "2026-01-01T00:00:00Z"});
const CHI_TIET = (login, rev = 3, them = [], hdId = "hd-" + login, duAn = "da1") => ({ho_so: {hop_dong_id: hdId, du_an_id: duAn, ten: "Gói " + login,
  so_hop_dong: "SO-" + login, du_an: duAn === "da1" ? "Dự án A1" : "Dự án A2", phap_nhan: "PN_DEMO_A", revision: rev, rev_tham_so: 2, tep_hop_dong_id: "tep-1",
  trang_thai_pl: "CHUA_KHAI", soan: true},
  tep: [TEP("tep-1", "HOP_DONG", "hd.docx"), TEP("boq-1", "BOQ", "boq1.xlsx"), TEP("boq-2", "BOQ", "boq2.xlsx"), ...them],
  trich_xuat: [], tham_so: [TS("TC-01", "Số hợp đồng"), TS("TC-02", "Ngày ký")], xac_nhan: null, phu_luc: [], boq: [], boq_goc_dong: [],
  dot: [{id: "dot-1", so_dot: 1, ngay_nghiem_thu: "2026-03-01", trang_thai: "NHAP", revision: 2, nop_luc: null, revision_ho_so: rev, can_cu_doi_sau_nop: false},
    {id: "dot-2", so_dot: 2, ngay_nghiem_thu: "2026-04-01", trang_thai: "NHAP", revision: 1, nop_luc: null, revision_ho_so: rev, can_cu_doi_sau_nop: false}],
  danh_muc_sha256: "b".repeat(64), nhanh_sau: []});
// C4: cùng actor có HAI dự án/HĐ trong DTO tin cậy của máy chủ (A1 ở da1, "B" ở da2)
const TONG2 = login => {
  const s = TONG(login);
  s.pham_vi.push({du_an_id: "da2", vai: "PHU_TRACH", du_an: "Dự án A2", du_an_ma: "DA_XD_A2", phap_nhan: "PN_DEMO_A", soan: true, xem: true});
  s.hop_dong.push({id: "hd-B", ten: "Gói B", so_hop_dong: "SO-B", du_an_id: "da2", du_an: "Dự án A2", phap_nhan: "PN_DEMO_A", revision: 1,
    trang_thai_pl: "CHUA_KHAI", co_tep: true, soan: true, so_dot: 0});
  return s;
};
const DOT_CT = (login, rev = 2, dotId = "dot-1") => ({dot: {id: dotId, hop_dong_id: "hd-" + login, du_an_id: "da1", so_dot: dotId === "dot-1" ? 1 : 2,
  ngay_nghiem_thu: "2026-03-01", trang_thai: "NHAP",
  revision: rev, revision_ho_so: 3, so_hop_dong: "SO-" + login, soan: true}, tep: [],
  checklist: [{ma: "A02", ten: "Biên bản nghiệm thu", bat_buoc_dot_dau: true, bat_buoc_dot_sau: true, ghi_chu: null, bat_buoc: true, tep: []}],
  thieu: [{ma: "DOT_THIEU_TAI_LIEU", nhom: "DOT", muc: "A02", noi_dung: "Thiếu A02"}], du_can_cu: false, nop: null,
  hieu_luc: {ngay: "2026-03-01", phu_luc_ap_dung: [], so_hang_muc_hieu_luc: 0, so_hang_muc_bo: 0}, can_cu_doi_sau_nop: false, nhanh_sau: []});
const MAU = {mau: [{ma: "hop_dong.docx", vai_tro: "HOP_DONG", media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", mo_ta: "HĐ"},
  {ma: "boq_goc.xlsx", vai_tro: "BOQ", media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", mo_ta: "BOQ"}]};
const NGUOI = login => ({dang_nhap: login, vai_tro: "DU_AN", phap_nhan: ["PN_DEMO_A"], hanh_dong: [], xem_tien: false, duoc: {}});
const CRM = login => ({cau_hinh: true, danh_tinh_demo: DEMO, nguoi: NGUOI(login), ngay_nghiep_vu: "2026-10-20", mau: [], m1_cau_hinh: false, tien_mau: [],
  ho_so: [], hop_dong: [], tien: [], file_soat: [], danh_muc: {doi_tac: [], du_an: []}});
const M5 = login => ({cau_hinh: true, danh_tinh_demo: DEMO, nguoi: NGUOI(login), nang_luc_nguon: [], mau: [], pham_vi_nguon: [], may_chu_nhan: false,
  nguon: [], phieu: [], viec: [], file_soat: []});
const M2 = login => ({cau_hinh: true, danh_tinh_demo: DEMO, nguoi: NGUOI(login), nang_luc_nguon: [], pham_vi_nguon: [], may_chu_nhan: false, mau: [],
  nguon: [], hoa_don: []});
const L11 = login => ({cau_hinh: true, danh_tinh_demo: DEMO, nguoi: NGUOI(login), pham_vi_bang_chung: [], may_chu_nhan: false, mau_bang_chung: [],
  ung_vien: [], bang_chung: [], dong_hoa_don: [], dong_phieu: [], lien_ket: []});

async function main() {
  const {ctx, document, calls} = moiTruong();
  vm.runInContext(APP, ctx, {filename: "app.js"});
  vm.runInContext(M4, ctx, {filename: "m4.js"});
  const $ = id => document.getElementById(id);
  const conLai = pred => calls.filter(c => !c.xong && pred(c));
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const get = url => c => c.method === "GET" && c.url === url;
  const post = url => c => c.method === "POST" && c.url === url;
  const laGetM5 = c => c.method === "GET" && /^\/api\/m5(\?|$)/.test(c.url), laGetM2 = c => c.method === "GET" && /^\/api\/m2(\?|$)/.test(c.url);
  async function traMau() { for (const c of conLai(get("/api/m4/mau"))) { c.xong = true; c.resolve(phanHoi(200, MAU)); } await chay(); }
  async function doiVaiM4(login, {xongPost = true} = {}) {
    $("m4-vai").value = login; $("m4-doi-vai").click(); await chay();
    const p = cho(post("/api/m4/danh-tinh"), "POST đổi vai " + login);
    assert.deepStrictEqual(JSON.parse(p.opts.body), {dang_nhap: login});
    if (xongPost) { p.resolve(phanHoi(200, {dang_nhap: login})); await chay(); }
    return p;
  }
  async function traTong(login) { cho(get("/api/m4"), "GET /api/m4 " + login).resolve(phanHoi(200, TONG(login))); await chay(); await traMau(); }
  async function moHd(login) {
    const li = tim($("m4-ds-hd"), e => e.tagName === "LI" && e.textContent.includes("SO-" + login));
    assert.ok(li, "không thấy HĐ " + login); li.dispatch("click"); await chay();
    cho(get("/api/m4/hop-dong/hd-" + login), "GET chi tiết " + login).resolve(phanHoi(200, CHI_TIET(login))); await chay();
  }
  const moTab = async ten => { nutTheoChu($("m4-chi-tiet"), ten).click(); await chay(); };

  // khởi động: các module ngoài #m4 trả lỗi có chủ đích (chúng tự bắt lỗi), M4 nạp thật
  for (const c of calls) if (c.url !== "/api/m4") { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND", message: "ngoài ca"})); }
  await traTong("MO_PHONG_DU_AN_A1");
  assert.ok($("m4-nguoi").textContent.includes("MO_PHONG_DU_AN_A1"));

  // ---------------------------------------------------------------- P0: dương không rỗng cho cả năm người tham gia
  {
    await doiVaiM4("MO_PHONG_DU_AN_B1", {xongPost: false});
    const pending = calls.filter(c => !c.xong && c.method === "POST");
    $("crm-refresh").click(); $("m5-refresh").click(); $("m2-refresh").click(); $("l11-refresh").click(); await chay();
    assert.strictEqual(dem(c => !c.xong && c.method === "GET" && ["/api/crm", "/api/m5/l11"].includes(c.url)) + conLai(laGetM5).length + conLai(laGetM2).length, 0,
      "P0: GET gửi khi barrier đổi vai còn chờ");
    calls.filter(c => c.url === "/api/m4/danh-tinh" && c.xong && !c.daTra).forEach(c => { c.daTra = true; c.resolve(phanHoi(200, {dang_nhap: "MO_PHONG_DU_AN_B1"})); });
    void pending; await chay();
    cho(get("/api/crm"), "GET CRM").resolve(phanHoi(200, CRM("MO_PHONG_DU_AN_B1")));
    cho(laGetM5, "GET M5").resolve(phanHoi(200, M5("MO_PHONG_DU_AN_B1")));
    cho(laGetM2, "GET M2").resolve(phanHoi(200, M2("MO_PHONG_DU_AN_B1")));
    cho(get("/api/m5/l11"), "GET L11").resolve(phanHoi(200, L11("MO_PHONG_DU_AN_B1")));
    await traTong("MO_PHONG_DU_AN_B1");
    for (const id of ["crm-nguoi", "m5-nguoi", "m2-nguoi", "l11-nguoi", "m4-nguoi"]) assert.ok($(id).textContent.includes("MO_PHONG_DU_AN_B1"), "P0: " + id + " chưa vẽ vai mới: " + $(id).textContent);
    console.log("P0 đạt");
  }

  // ---------------------------------------------------------------- C2-1a: vé sở hữu POST qua A→B→A, JSON đứt
  {
    await doiVaiM4("MO_PHONG_DU_AN_A1"); await traTong("MO_PHONG_DU_AN_A1");
    const nhapTao = () => { $("m4f-tao-so").value = "HD-C2"; $("m4f-tao-ten").value = "Gói C2"; };
    nhapTao(); nutTheoChu($("m4-tao"), "Tạo hồ sơ HĐ").click(); await chay();
    const cu = cho(post("/api/m4/hop-dong/tao"), "POST tạo lần A cũ");
    const khoaCu = JSON.parse(cu.opts.body).khoa;
    await doiVaiM4("MO_PHONG_DU_AN_B1"); await traTong("MO_PHONG_DU_AN_B1");
    await doiVaiM4("MO_PHONG_DU_AN_A1"); await traTong("MO_PHONG_DU_AN_A1");
    nhapTao(); nutTheoChu($("m4-tao"), "Tạo hồ sơ HĐ").click(); await chay();
    const moi = cho(post("/api/m4/hop-dong/tao"), "POST tạo lần A mới");
    const bodyMoi = JSON.parse(moi.opts.body);
    assert.notStrictEqual(bodyMoi.khoa, khoaCu, "C2-1a: khóa của lần mới phải là bản ghi mới sau đổi vai");
    cu.resolve(phanHoi(200, {hop_dong_id: "hd-cu", lap_lai: false})); await chay();  // lần cũ về trước lần mới
    nhapTao(); nutTheoChu($("m4-tao"), "Tạo hồ sơ HĐ").click(); await chay();
    assert.strictEqual(conLai(post("/api/m4/hop-dong/tao")).length, 0, "C2-1a: lần cũ đã nhả 'đang gửi' của lần mới (bấm lặp gửi thêm POST)");
    moi.reject(new TypeError("Failed to fetch")); await chay();
    nutTheoChu($("m4-gui-lai"), "Gửi lại y nguyên").click(); await chay();
    const lai1 = cho(post("/api/m4/hop-dong/tao"), "POST gửi lại 1");
    assert.deepStrictEqual(JSON.parse(lai1.opts.body), bodyMoi, "C2-1a: gửi lại khác body/khóa");
    lai1.resolve(phanHoi(200, JSON_DUT)); await chay();  // HTTP 200 nhưng JSON đứt: chưa rõ kết quả
    const nutLai = nutTheoChu($("m4-gui-lai"), "Gửi lại y nguyên");
    assert.ok(nutLai, "C2-1a: JSON đứt sau 200 không được coi là xong/thất bại chắc chắn");
    nutLai.click(); await chay();
    const lai2 = cho(post("/api/m4/hop-dong/tao"), "POST gửi lại 2");
    assert.deepStrictEqual(JSON.parse(lai2.opts.body), bodyMoi, "C2-1a: gửi lại sau JSON đứt khác body/khóa");
    lai2.resolve(phanHoi(200, {hop_dong_id: "hd-moi", lap_lai: true})); await chay();
    await traTong("MO_PHONG_DU_AN_A1");
    for (const c of conLai(get("/api/m4/hop-dong/hd-moi"))) { c.xong = true; c.resolve(phanHoi(404, {error: "M4_KHONG_THAY_HOP_DONG", message: "ngoài ca"})); }
    await chay();
    console.log("C2-1a đạt");
  }

  // ---------------------------------------------------------------- C2-1b: vé sở hữu tải lên
  {
    await moHd("MO_PHONG_DU_AN_A1");
    const tep = {name: "hd2.docx", size: 20, type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", lastModified: 7};
    const guiTep = async () => { $("m4f-nguon-file").files = [tep]; nutTheoChu($("m4-chi-tiet"), "Tải lên").click(); await chay(); };
    await guiTep();
    const u1 = cho(post("/api/m4/tep"), "upload lần cũ");
    await doiVaiM4("MO_PHONG_DU_AN_B1"); await traTong("MO_PHONG_DU_AN_B1");
    await doiVaiM4("MO_PHONG_DU_AN_A1"); await traTong("MO_PHONG_DU_AN_A1");
    await moHd("MO_PHONG_DU_AN_A1");
    await guiTep();
    const u2 = cho(post("/api/m4/tep"), "upload lần mới");
    const info2 = u2.opts.headers["X-M4-Info"];
    assert.notStrictEqual(info2, u1.opts.headers["X-M4-Info"], "C2-1b: lần mới sau đổi vai dùng bản ghi mới");
    u1.resolve(phanHoi(200, {tep_id: "t-cu", sha256: "c".repeat(64), byte_length: 20, hang_moi: true, lap_lai: false})); await chay();
    await guiTep();
    assert.strictEqual(conLai(post("/api/m4/tep")).length, 0, "C2-1b: lần cũ nhả 'đang gửi' của lần mới");
    u2.resolve(phanHoi(200, JSON_DUT)); await chay();
    assert.ok($("m4-status").textContent.includes("chưa rõ"), "C2-1b: JSON đứt sau 200 phải báo chưa rõ kết quả");
    await guiTep();
    const u3 = cho(post("/api/m4/tep"), "upload gửi lại");
    assert.strictEqual(u3.opts.headers["X-M4-Info"], info2, "C2-1b: gửi lại tệp khác khóa/metadata");
    u3.resolve(phanHoi(200, {tep_id: "t-moi", sha256: "d".repeat(64), byte_length: 20, hang_moi: false, lap_lai: true})); await chay();
    await traTong("MO_PHONG_DU_AN_A1");
    cho(get("/api/m4/hop-dong/hd-MO_PHONG_DU_AN_A1"), "GET sau upload").resolve(phanHoi(200, CHI_TIET("MO_PHONG_DU_AN_A1"))); await chay();
    console.log("C2-1b đạt");
  }

  // ---------------------------------------------------------------- C2-2: BOQ chọn tệp/sheet, đảo thứ tự, lỗi cũ, nhập dương
  {
    await moTab("BOQ");
    const chonTep = async v => { $("m4f-boq-tep").value = v; $("m4f-boq-tep").dispatch("change"); await chay(); };
    await chonTep("boq-1");
    nutTheoChu($("m4-chi-tiet"), "Đọc danh sách sheet").click(); await chay();
    const x1 = cho(c => c.method === "POST" && c.url === "/api/m4/boq/xem" && JSON.parse(c.opts.body).tep_id === "boq-1", "xem boq-1");
    await chonTep("boq-2");
    nutTheoChu($("m4-chi-tiet"), "Đọc danh sách sheet").click(); await chay();
    const x2 = cho(c => c.method === "POST" && c.url === "/api/m4/boq/xem" && JSON.parse(c.opts.body).tep_id === "boq-2", "xem boq-2");
    x2.resolve(phanHoi(200, {sheets: [{ten: "B-S1", so_dong: 5, so_cot: 7, an: false}, {ten: "B-S2", so_dong: 5, so_cot: 7, an: false}], goi_y: null})); await chay();
    x1.resolve(phanHoi(200, {sheets: [{ten: "A-S1", so_dong: 5, so_cot: 7, an: false}], goi_y: null})); await chay();  // A về trễ
    const sel = $("m4f-boq-sheet");
    assert.ok(sel && sel.isConnected, "C2-2: chưa có ô chọn sheet của tệp hiện tại");
    assert.ok(sel.textContent.includes("B-S1") && !sel.textContent.includes("A-S1"), "C2-2: phản hồi tệp cũ kéo lựa chọn về tệp cũ");
    assert.strictEqual($("m4f-boq-tep").value, "boq-2");
    sel.value = "B-S2"; sel.dispatch("change"); await chay();
    const y1 = cho(c => c.url === "/api/m4/boq/xem" && JSON.parse(c.opts.body).sheet === "B-S2", "xem B-S2");
    assert.strictEqual($("m4-boq-nhap"), null, "C2-2: nút Nhập còn khi xem trước đang chờ");
    $("m4f-boq-sheet").value = "B-S1"; $("m4f-boq-sheet").dispatch("change"); await chay();
    const y2 = cho(c => c.url === "/api/m4/boq/xem" && JSON.parse(c.opts.body).sheet === "B-S1", "xem B-S1");
    const trangThaiTruoc = $("m4-status").textContent;
    y1.reject(new TypeError("Failed to fetch")); await chay();  // lỗi của lựa chọn cũ
    assert.strictEqual($("m4-status").textContent, trangThaiTruoc, "C2-2: lỗi của sheet cũ được vẽ");
    assert.strictEqual($("m4-boq-nhap"), null);
    y2.resolve(phanHoi(200, {sheet: "B-S1", dong: [["STT", "Mã", "Tên", "ĐVT", "KL", "ĐG", "TT"]], so_cot: 7, hang_tieu_de: 1,
      cot: {stt: "A", ma_rieng: "B", ten: "C", dvt: "D", kl: "E", don_gia: "F", thanh_tien: "G"}, truong: []})); await chay();
    const nhap = $("m4-boq-nhap");
    assert.ok(nhap && nhap.isConnected, "C2-2: xem trước hiện tại xong mà không có nút Nhập");
    $("m4f-boq-hang").value = "1"; $("m4f-boq-hang").dispatch("input");
    $("m4f-boq-cot-kl").value = "e"; $("m4f-boq-cot-kl").dispatch("input");
    nhap.click(); await chay();
    const n = cho(post("/api/m4/boq/nhap"), "POST nhập BOQ");
    const b = JSON.parse(n.opts.body);
    assert.deepStrictEqual([b.tep_id, b.sheet, b.hang_tieu_de, b.cot.kl, b.cot.ten, b.phu_luc_id], ["boq-2", "B-S1", 1, "E", "C", null], "C2-2: nhập không đúng lựa chọn đang hiện");
    n.resolve(phanHoi(200, {boq_id: "bq", so_dong: 0, trang_thai: "CO_LOI", so_loi_chan: 1, so_phat_hien: 0, loi_chan: [], phat_hien: [], revision: 4, lap_lai: false}));
    await chay();
    for (const c of conLai(get("/api/m4"))) { c.xong = true; c.resolve(phanHoi(200, TONG("MO_PHONG_DU_AN_A1"))); }
    await chay(); await traMau();
    for (const c of conLai(get("/api/m4/hop-dong/hd-MO_PHONG_DU_AN_A1"))) { c.xong = true; c.resolve(phanHoi(200, CHI_TIET("MO_PHONG_DU_AN_A1"))); }
    await chay();
    console.log("C2-2 đạt");
  }

  // ---------------------------------------------------------------- C2-3: form tham số + tệp mẫu
  {
    await moTab("Tham số");
    const sua = ma => tim($("m4-chi-tiet"), e => e.tagName === "TR" && e.textContent.includes(ma) && !!nutTheoChu(e, "Sửa"));
    nutTheoChu(sua("TC-01"), "Sửa").click(); await chay();
    $("m4f-sua-tt").value = "KHONG_QUY_DINH"; $("m4f-sua-ld").value = "Không có"; nutTheoChu($("m4-chi-tiet"), "Lưu TC-01").click(); await chay();
    const pA = cho(post("/api/m4/tham-so/sua"), "lưu TC-01");
    nutTheoChu(sua("TC-02"), "Sửa").click(); await chay();
    $("m4f-sua-gt").value = "nháp B"; $("m4f-sua-gt").dispatch("input");
    const getTruoc = dem(get("/api/m4/hop-dong/hd-MO_PHONG_DU_AN_A1"));
    pA.resolve(phanHoi(200, {revision: 4, kiem_tra: null, lap_lai: false})); await chay();
    assert.ok(nutTheoChu($("m4-chi-tiet"), "Lưu TC-02"), "C2-3: phản hồi lưu TC-01 đã đóng form TC-02");
    assert.strictEqual($("m4f-sua-gt").value, "nháp B", "C2-3: nháp TC-02 bị vẽ đè");
    assert.strictEqual(dem(get("/api/m4/hop-dong/hd-MO_PHONG_DU_AN_A1")), getTruoc, "C2-3: continuation cũ làm mới đè form mới");
    $("m4f-sua-tt").value = "CO_GIA_TRI"; $("m4f-sua-td").value = "Hôm nay, ngày 05"; nutTheoChu($("m4-chi-tiet"), "Lưu TC-02").click(); await chay();
    const pB = cho(post("/api/m4/tham-so/sua"), "lưu TC-02");
    const bB = JSON.parse(pB.opts.body);
    assert.deepStrictEqual([bB.ma, bB.gia_tri, bB.trich_dan], ["TC-02", "nháp B", "Hôm nay, ngày 05"]);
    pB.resolve(phanHoi(200, {revision: 5, kiem_tra: "OK", lap_lai: false})); await chay();
    cho(get("/api/m4"), "GET sau lưu TC-02 (dương)").resolve(phanHoi(200, TONG("MO_PHONG_DU_AN_A1"))); await chay(); await traMau();
    cho(get("/api/m4/hop-dong/hd-MO_PHONG_DU_AN_A1"), "GET chi tiết sau lưu").resolve(phanHoi(200, CHI_TIET("MO_PHONG_DU_AN_A1"))); await chay();
    // tệp mẫu
    await moTab("Nguồn HĐ");
    const chonMau = v => { $("m4f-nguon-mau").value = v; $("m4f-nguon-mau").dispatch("change"); };
    chonMau("hop_dong.docx"); nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu").click(); await chay();
    const g1 = cho(get("/api/m4/mau/hop_dong.docx"), "GET mẫu cũ");
    chonMau("boq_goc.xlsx");
    g1.resolve(phanHoi(200, null, 30)); await chay();
    assert.strictEqual(conLai(post("/api/m4/tep")).length, 0, "C2-3: gửi tệp mẫu của lựa chọn cũ");
    nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu").click(); await chay();
    cho(get("/api/m4/mau/boq_goc.xlsx"), "GET mẫu hiện tại").resolve(phanHoi(200, null, 40)); await chay();
    const up = cho(post("/api/m4/tep"), "upload mẫu hiện tại");
    const info = JSON.parse(decodeURIComponent(up.opts.headers["X-M4-Info"]));
    assert.deepStrictEqual([info.ten, info.vai_tro], ["boq_goc.xlsx", "BOQ"], "C2-3: tệp mẫu hiện tại không đúng lựa chọn");
    up.resolve(phanHoi(200, {tep_id: "t-mau", sha256: "e".repeat(64), byte_length: 40, hang_moi: true, lap_lai: false})); await chay();
    for (const c of conLai(get("/api/m4"))) { c.xong = true; c.resolve(phanHoi(200, TONG("MO_PHONG_DU_AN_A1"))); }
    await chay(); await traMau();
    for (const c of conLai(get("/api/m4/hop-dong/hd-MO_PHONG_DU_AN_A1"))) { c.xong = true; c.resolve(phanHoi(200, CHI_TIET("MO_PHONG_DU_AN_A1"))); }
    await chay();
    console.log("C2-3 đạt");
  }

  // ---------------------------------------------------------------- C2-4: hàng đổi vai không bị GET nạp lại giữ
  {
    // tải bytes trước khi đổi vai: bytes về trễ không click
    nutTheoChu($("m4-chi-tiet"), "Tải ↓").click(); await chay();
    const tai = cho(get("/api/m4/tep/tep-1"), "GET tệp");
    // GET M2 cũ bắt đầu trước đổi vai
    $("m2-refresh").click(); await chay();
    const m2Cu = cho(laGetM2, "GET M2 cũ");
    await doiVaiM4("MO_PHONG_DU_AN_B1");  // POST1 xong → nạp lại M4
    const getTreo = cho(get("/api/m4"), "GET nạp lại của ý định 1 (treo)");
    $("m4-vai").value = "MO_PHONG_DU_AN_A2"; $("m4-doi-vai").click(); await chay();
    const p2 = cho(post("/api/m4/danh-tinh"), "C2-4: POST ý định 2 phải gửi khi GET nạp lại của ý định 1 còn treo");
    assert.deepStrictEqual(JSON.parse(p2.opts.body), {dang_nhap: "MO_PHONG_DU_AN_A2"});
    const truocClick = soClickTai;
    tai.resolve(phanHoi(200, null, 10)); m2Cu.resolve(phanHoi(200, M2("MO_PHONG_DU_AN_A1")));
    getTreo.resolve(phanHoi(200, TONG("MO_PHONG_DU_AN_B1"))); await chay();
    assert.strictEqual(soClickTai, truocClick, "C2-4: bytes trễ của vai cũ được click");
    assert.strictEqual($("m4-nguoi").textContent, "Đang tải…", "C2-4: GET nạp lại của ý định cũ được vẽ");
    assert.strictEqual($("m2-nguoi").textContent, "Đang tải…", "C2-4: GET M2 cũ được vẽ sau đổi vai");
    p2.resolve(phanHoi(200, {dang_nhap: "MO_PHONG_DU_AN_A2"})); await chay();
    await traTong("MO_PHONG_DU_AN_A2");
    assert.ok($("m4-nguoi").textContent.includes("MO_PHONG_DU_AN_A2"));
    // chiều ngược: ý định từ CRM, GET CRM nạp lại treo, ý định M4 tiếp theo vẫn gửi POST ngay
    $("crm-danh-tinh").value = "MO_PHONG_DU_AN_B1"; $("crm-doi-vai").click(); await chay();
    cho(post("/api/crm/danh-tinh"), "POST đổi vai từ CRM").resolve(phanHoi(200, {dang_nhap: "MO_PHONG_DU_AN_B1"})); await chay();
    const crmTreo = cho(get("/api/crm"), "GET CRM nạp lại (treo)");
    await doiVaiM4("MO_PHONG_DU_AN_A1", {xongPost: false});  // cho() bên trong khẳng định POST đã gửi khi GET CRM còn treo
    crmTreo.resolve(phanHoi(200, CRM("MO_PHONG_DU_AN_B1"))); await chay();
    assert.strictEqual($("crm-nguoi").textContent, "Đang tải…", "C2-4: GET CRM của ý định cũ được vẽ");
    calls.filter(c => c.url === "/api/m4/danh-tinh" && c.xong && !c.daTra).forEach(c => { c.daTra = true; c.resolve(phanHoi(200, {dang_nhap: "MO_PHONG_DU_AN_A1"})); });
    await chay();
    await traTong("MO_PHONG_DU_AN_A1");
    for (const c of conLai(get("/api/crm"))) { c.xong = true; c.resolve(phanHoi(200, CRM("MO_PHONG_DU_AN_A1"))); }
    await chay();
    console.log("C2-4 đạt");
  }

  // ================================================================ C3
  const A1 = "MO_PHONG_DU_AN_A1", URL_HD = "/api/m4/hop-dong/hd-" + A1, URL_DOT = "/api/m4/dot/dot-1";
  const nhap = (id, v) => { const el = $(id); assert.ok(el && el.isConnected, "không có ô " + id); el.value = v; el.dispatch("input"); };
  const suaMa = ma => nutTheoChu(tim($("m4-chi-tiet"), e => e.tagName === "TR" && e.textContent.includes(ma) && !!nutTheoChu(e, "Sửa")), "Sửa");
  async function traHetGet(rev = 3) {  // trả các GET làm mới còn chờ theo thứ tự chuỗi tổng quan → HĐ → đợt
    for (let i = 0; i < 4; i++) {
      for (const c of conLai(get("/api/m4"))) { c.xong = true; c.resolve(phanHoi(200, TONG(A1))); }
      await chay(); await traMau();
      for (const c of conLai(get(URL_HD))) { c.xong = true; c.resolve(phanHoi(200, CHI_TIET(A1, rev))); }
      await chay();
      for (const c of conLai(get(URL_DOT))) { c.xong = true; c.resolve(phanHoi(200, DOT_CT(A1))); }
      await chay();
    }
  }

  // ---------------------------------------------------------------- C3-1: làm mới về trễ không vẽ đè form/nháp mới; dương vẫn làm mới
  {
    await moHd(A1);
    await moTab("Tham số");
    suaMa("TC-01").click(); await chay();
    $("m4f-sua-tt").value = "KHONG_QUY_DINH"; $("m4f-sua-ld").value = "Không có";
    nutTheoChu($("m4-chi-tiet"), "Lưu TC-01").click(); await chay();
    cho(post("/api/m4/tham-so/sua"), "lưu TC-01 (C3-1)").resolve(phanHoi(200, {revision: 4, kiem_tra: null, lap_lai: false})); await chay();
    await traTong(A1);                                   // GET tổng quan về khi chưa có sửa mới → bình thường
    const getHd = cho(get(URL_HD), "C3-1: GET HĐ làm mới còn chờ");
    suaMa("TC-02").click(); await chay();               // mở form khác SAU lúc GET bắt đầu
    nhap("m4f-sua-gt", "B mới");
    getHd.resolve(phanHoi(200, CHI_TIET(A1, 4))); await chay();
    assert.strictEqual($("m4f-sua-gt").value, "B mới", "C3-1: GET HĐ về trễ làm mất nháp mới");
    assert.ok(nutTheoChu($("m4-chi-tiet"), "Lưu TC-02 (revision 3)"), "C3-1: GET HĐ về trễ đóng/vẽ đè form mới");
    assert.strictEqual(conLai(get(URL_DOT)).length, 0);
    // dương: không sửa thêm → lưu B → chuỗi làm mới vẽ revision mới, form đóng
    $("m4f-sua-tt").value = "CO_GIA_TRI"; $("m4f-sua-td").value = "Hôm nay, ngày 05";
    nutTheoChu($("m4-chi-tiet"), "Lưu TC-02").click(); await chay();
    cho(post("/api/m4/tham-so/sua"), "lưu TC-02 (C3-1)").resolve(phanHoi(200, {revision: 5, kiem_tra: "OK", lap_lai: false})); await chay();
    await traHetGet(5);
    assert.strictEqual($("m4f-sua-gt"), null, "C3-1: làm mới hiện hành không đóng form đã lưu");
    assert.ok($("m4-chi-tiet").textContent.includes("revision hồ sơ 5"), "C3-1: làm mới hiện hành không vẽ revision mới");
    // GET đợt về trễ
    await moTab("Đợt");
    nutTheoChu($("m4-chi-tiet"), "Mở").click(); await chay();
    await traHetGet(5);
    assert.ok($("m4f-dot-sua-ngay") && $("m4f-dot-sua-ngay").isConnected, "C3-1: chưa mở panel đợt");
    nhap("m4f-dot-sua-ngay", "2026-03-05");
    nutTheoChu($("m4-chi-tiet"), "Lưu ngày").click(); await chay();
    cho(post("/api/m4/dot/sua"), "lưu ngày").resolve(phanHoi(200, {revision: 3, lap_lai: false})); await chay();
    await traTong(A1);
    cho(get(URL_HD), "GET HĐ sau lưu ngày").resolve(phanHoi(200, CHI_TIET(A1, 5))); await chay();
    const getDot = cho(get(URL_DOT), "C3-1: GET đợt làm mới còn chờ");
    nhap("m4f-dot-sua-ngay", "2026-03-09");             // nhập SAU lúc chuỗi làm mới bắt đầu
    getDot.resolve(phanHoi(200, DOT_CT(A1, 3))); await chay();
    assert.strictEqual($("m4f-dot-sua-ngay").value, "2026-03-09", "C3-1: GET đợt về trễ làm mất nháp ngày");
    assert.ok($("m4-chi-tiet").textContent.includes("revision đợt 2"), "C3-1: GET đợt về trễ vẽ đè panel đang nhập");
    console.log("C3-1 đạt");
  }

  // ---------------------------------------------------------------- C3-2: khôi phục sau revision cũ giữ giá trị MỚI NHẤT
  {
    await moTab("Tham số");
    suaMa("TC-01").click(); await chay();
    $("m4f-sua-tt").value = "CO_GIA_TRI"; nhap("m4f-sua-gt", "v1"); $("m4f-sua-td").value = "Số: HD";
    nutTheoChu($("m4-chi-tiet"), "Lưu TC-01").click(); await chay();
    cho(post("/api/m4/tham-so/sua"), "lưu TC-01 (C3-2)").resolve(phanHoi(409, {error: "M4_REVISION_CU", message: "Hồ sơ đã đổi"})); await chay();
    const getHd = cho(get(URL_HD), "C3-2: GET khôi phục revision");
    nhap("m4f-sua-gt", "v2");                            // nhập thêm SAU lúc GET khôi phục bắt đầu
    getHd.resolve(phanHoi(200, CHI_TIET(A1, 6))); await chay();
    assert.ok(nutTheoChu($("m4-chi-tiet"), "Lưu TC-01 (revision 6)"), "C3-2: không vẽ revision mới sau 409");
    assert.strictEqual($("m4f-sua-gt").value, "v2", "C3-2: khôi phục bằng snapshot cũ thay vì giá trị mới nhất");
    for (const c of conLai(get(URL_DOT))) { c.xong = true; c.resolve(phanHoi(200, DOT_CT(A1))); }
    await chay();
    nutTheoChu($("m4-chi-tiet"), "Đóng").click(); await chay();
    console.log("C3-2 đạt");
  }

  // ---------------------------------------------------------------- C3-3: BOQ xem trước chờ + đổi tab và nhập
  {
    await moTab("BOQ");
    $("m4f-boq-tep").value = "boq-1"; $("m4f-boq-tep").dispatch("change"); await chay();
    nutTheoChu($("m4-chi-tiet"), "Đọc danh sách sheet").click(); await chay();
    const x = cho(c => c.url === "/api/m4/boq/xem" && JSON.parse(c.opts.body).tep_id === "boq-1" && !JSON.parse(c.opts.body).sheet, "C3-3 đọc sheet");
    await moTab("Phụ lục");
    nhap("m4f-pl-so", "PL-09");
    x.resolve(phanHoi(200, {sheets: [{ten: "S1", so_dong: 3, so_cot: 7, an: false}, {ten: "S2", so_dong: 3, so_cot: 7, an: false}], goi_y: null})); await chay();
    assert.strictEqual($("m4f-pl-so").value, "PL-09", "C3-3: phản hồi đọc sheet dựng lại tab khác/mất nháp");
    assert.strictEqual($("m4f-boq-sheet"), null, "C3-3: phản hồi BOQ vẽ khi đang ở tab khác");
    await moTab("BOQ");
    assert.ok($("m4f-boq-sheet") && $("m4f-boq-sheet").textContent.includes("S2"), "C3-3: quay lại BOQ không thấy kết quả đọc sheet mới nhất");
    $("m4f-boq-sheet").value = "S2"; $("m4f-boq-sheet").dispatch("change"); await chay();
    const y = cho(c => c.url === "/api/m4/boq/xem" && JSON.parse(c.opts.body).sheet === "S2", "C3-3 xem S2");
    await moTab("Phụ lục");
    nhap("m4f-pl-so", "PL-10");
    const st = $("m4-status").textContent;
    y.resolve(phanHoi(400, {error: "M4_BOQ_MAP_SAI", message: "lỗi xem trước"})); await chay();
    assert.strictEqual($("m4f-pl-so").value, "PL-10", "C3-3: lỗi xem trước làm mất nháp tab khác");
    assert.notStrictEqual(st, null);
    await moTab("BOQ");
    nutTheoChu($("m4-chi-tiet"), "Xem trước sheet").click(); await chay();
    cho(c => c.url === "/api/m4/boq/xem" && JSON.parse(c.opts.body).sheet === "S2", "C3-3 xem lại S2").resolve(phanHoi(200, {sheet: "S2", dong: [["a"]], so_cot: 7,
      hang_tieu_de: 2, cot: {ten: "C", dvt: "D", kl: "E", don_gia: "F"}, truong: []})); await chay();
    nhap("m4f-boq-cot-thanh_tien", "g");
    $("m4-boq-nhap").click(); await chay();
    const b = JSON.parse(cho(post("/api/m4/boq/nhap"), "C3-3 nhập").opts.body);
    assert.deepStrictEqual([b.tep_id, b.sheet, b.hang_tieu_de, b.cot.thanh_tien, b.cot.kl], ["boq-1", "S2", 2, "G", "E"], "C3-3: nhập sai lựa chọn hiện tại");
    calls.filter(c => c.url === "/api/m4/boq/nhap" && c.xong && !c.daTra).forEach(c => { c.daTra = true;
      c.resolve(phanHoi(200, {boq_id: "bq2", so_dong: 1, trang_thai: "DA_MAP", so_loi_chan: 0, so_phat_hien: 0, loi_chan: [], phat_hien: [], revision: 7, lap_lai: false})); });
    await chay(); await traHetGet(7);
    console.log("C3-3 đạt");
  }

  // ---------------------------------------------------------------- C3-4: tải lên chưa rõ → gửi lại đúng ý định gốc
  {
    await moTab("Nguồn HĐ");
    $("m4f-nguon-mau").value = "hop_dong.docx"; $("m4f-nguon-mau").dispatch("change");
    nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu").click(); await chay();
    cho(get("/api/m4/mau/hop_dong.docx"), "C3-4 lấy mẫu").resolve(phanHoi(200, null, 30)); await chay();
    const u1 = cho(post("/api/m4/tep"), "C3-4 tải mẫu lần 1");
    const soLayMau = dem(c => c.url === "/api/m4/mau/hop_dong.docx");
    u1.resolve(phanHoi(200, JSON_DUT)); await chay();                     // HTTP 200, JSON đứt → chưa rõ
    assert.ok(nutTheoChu($("m4-gui-lai"), "Gửi lại tệp y nguyên"), "C3-4: JSON đứt không giữ ý định tải lên");
    nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu").click(); await chay();  // bấm lại Dùng mẫu → phải dùng ý định đang giữ
    assert.strictEqual(dem(c => c.url === "/api/m4/mau/hop_dong.docx"), soLayMau, "C3-4: lấy lại tệp mẫu khi gửi lại ý định chưa rõ");
    const u2 = cho(post("/api/m4/tep"), "C3-4 gửi lại 1");
    assert.strictEqual(u2.opts.body, u1.opts.body, "C3-4: gửi lại khác đối tượng File/bytes gốc");
    assert.strictEqual(u2.opts.headers["X-M4-Info"], u1.opts.headers["X-M4-Info"], "C3-4: gửi lại khác metadata/khóa");
    nutTheoChu($("m4-gui-lai"), "Gửi lại tệp y nguyên").click(); await chay();  // bấm lặp khi còn bay
    assert.strictEqual(conLai(post("/api/m4/tep")).length, 0, "C3-4: bấm lặp gửi thêm POST");
    u2.reject(new TypeError("Failed to fetch")); await chay();            // mất kết nối → vẫn chưa rõ
    nutTheoChu($("m4-gui-lai"), "Gửi lại tệp y nguyên").click(); await chay();
    const u3 = cho(post("/api/m4/tep"), "C3-4 gửi lại 2");
    assert.strictEqual(u3.opts.body, u1.opts.body);
    assert.strictEqual(u3.opts.headers["X-M4-Info"], u1.opts.headers["X-M4-Info"]);
    const getTruoc = dem(get("/api/m4"));
    u3.resolve(phanHoi(200, {tep_id: "t-mau-c3", sha256: "f".repeat(64), byte_length: 30, hang_moi: true, lap_lai: false})); await chay();
    assert.strictEqual(dem(get("/api/m4")) - getTruoc, 1, "C3-4: continuation sau kết quả rõ không chạy đúng một lần");
    assert.strictEqual($("m4-gui-lai").children.length, 0, "C3-4: nút gửi lại còn sau khi có kết quả");
    await traHetGet(7);
    // tệp thật: chọn lại cùng tệp (đối tượng File mới, cùng tên/kích thước/thời điểm sửa) → gửi đúng File GỐC đang giữ
    const goc = new ctx.File([new Uint8Array(12)], "that.pdf", {type: "application/pdf"});
    $("m4f-nguon-file").files = [goc];
    nutTheoChu($("m4-chi-tiet"), "Tải lên").click(); await chay();
    const t1 = cho(post("/api/m4/tep"), "tệp thật lần 1");
    t1.reject(new TypeError("Failed to fetch")); await chay();
    $("m4f-nguon-file").files = [new ctx.File([new Uint8Array(12)], "that.pdf", {type: "application/pdf", lastModified: goc.lastModified})];
    nutTheoChu($("m4-chi-tiet"), "Tải lên").click(); await chay();
    const t2 = cho(post("/api/m4/tep"), "tệp thật gửi lại");
    assert.strictEqual(t2.opts.body, goc, "C3-4: tệp thật gửi lại không phải File gốc");
    assert.strictEqual(t2.opts.headers["X-M4-Info"], t1.opts.headers["X-M4-Info"]);
    t2.resolve(phanHoi(200, {tep_id: "t-that", sha256: "1".repeat(64), byte_length: 12, hang_moi: true, lap_lai: false})); await chay();
    await traHetGet(7);
    console.log("C3-4 đạt");
  }

  // ================================================================ C4
  const URL_HD_B = "/api/m4/hop-dong/hd-B", URL_DOT2 = "/api/m4/dot/dot-2";
  const soPostTep = () => dem(post("/api/m4/tep"));
  const moLi = async soHd => {  // bấm phần tử danh sách HĐ ĐANG NỐI DOM (thao tác thật của người dùng)
    const li = tim($("m4-ds-hd"), e => e.tagName === "LI" && e.isConnected && e.textContent.includes(soHd));
    assert.ok(li, "C4: không thấy HĐ " + soHd + " trong danh sách đang hiện"); li.dispatch("click"); await chay();
  };
  // nạp tổng quan có HAI dự án/HĐ cho cùng actor
  $("m4-lam-moi").click(); await chay();
  cho(get("/api/m4"), "C4 tổng quan hai dự án").resolve(phanHoi(200, TONG2(A1))); await chay(); await traMau();
  for (const c of conLai(get(URL_HD))) { c.xong = true; c.resolve(phanHoi(200, CHI_TIET(A1, 7))); }
  await chay();
  for (const c of conLai(get(URL_DOT))) { c.xong = true; c.resolve(phanHoi(200, DOT_CT(A1))); }  // đợt 1 còn mở từ C3
  await chay();
  assert.ok(tim($("m4-ds-hd"), e => e.tagName === "LI" && e.textContent.includes("SO-B")), "C4: DTO hai dự án chưa hiện HĐ B");

  // ---------------------------------------------------------------- C4-01a: chưa rõ ở HĐ A → mở HĐ B thật → nút gửi lại không còn / 0 POST
  {
    await moTab("Nguồn HĐ");
    const fA = new ctx.File([new Uint8Array(16)], "hop_dong_A.pdf", {type: "application/pdf"});
    $("m4f-nguon-file").files = [fA];
    nutTheoChu($("m4-chi-tiet"), "Tải lên").click(); await chay();
    const a1 = cho(post("/api/m4/tep"), "C4-01a tải A");
    assert.strictEqual(JSON.parse(decodeURIComponent(a1.opts.headers["X-M4-Info"])).du_an_id, "da1");
    a1.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(nutTheoChu($("m4-gui-lai"), "Gửi lại tệp y nguyên"), "C4-01a setup: chưa có nút gửi lại cho kết quả chưa rõ");
    const truoc = soPostTep();
    await moLi("SO-B");                                                   // chuyển hồ sơ bằng control thật
    cho(get(URL_HD_B), "GET chi tiết B").resolve(phanHoi(200, CHI_TIET("B", 1, [], "hd-B", "da2"))); await chay();
    assert.ok($("m4-chi-tiet").textContent.includes("SO-B"), "C4-01a setup: detail B chưa xong");
    const lai = nutTheoChu($("m4-gui-lai"), "Gửi lại tệp");                // lấy lại control CÒN NỐI nếu có
    if (lai) { assert.ok(lai.isConnected); lai.click(); await chay(); }
    assert.strictEqual(soPostTep() - truoc, 0, "C4-01a: gửi lại tệp A dưới ngữ cảnh B");
    assert.strictEqual(lai, null, "C4-01a: nút gửi lại của HĐ A còn hiện trên HĐ B");
    // quay về A bằng control thật: ý định cũ đã bị vô hiệu, không tự gửi
    await moLi("SO-" + A1);
    cho(get(URL_HD), "GET chi tiết A lại").resolve(phanHoi(200, CHI_TIET(A1, 7))); await chay();
    assert.strictEqual(nutTheoChu($("m4-gui-lai"), "Gửi lại tệp"), null);
    assert.strictEqual(soPostTep() - truoc, 0);
    console.log("C4-01a đạt");
  }

  // ---------------------------------------------------------------- C4-01b: chưa rõ ở đợt 1 → mở đợt 2 → gửi lại cũ bị vô hiệu trước POST
  {
    await moTab("Đợt");
    nutTheoChu($("m4-chi-tiet"), "Mở").click(); await chay();            // đợt 1
    cho(get(URL_HD), "GET HĐ khi mở đợt 1").resolve(phanHoi(200, CHI_TIET(A1, 7))); await chay();
    cho(get(URL_DOT), "GET đợt 1").resolve(phanHoi(200, DOT_CT(A1))); await chay();
    const fD = new ctx.File([new Uint8Array(9)], "bien_ban.pdf", {type: "application/pdf"});
    $("m4f-hs-file").files = [fD];
    nutTheoChu($("m4-dot-panel"), "Tải lên").click(); await chay();
    cho(post("/api/m4/tep"), "C4-01b tải hồ sơ đợt 1").resolve(phanHoi(503, {error: "PG_KHONG_KET_NOI", message: "tạm lỗi"})); await chay();
    assert.ok(nutTheoChu($("m4-gui-lai"), "Gửi lại tệp y nguyên"), "C4-01b setup: 5xx không giữ ý định chưa rõ");
    const truoc = soPostTep();
    nutTheoChu($("m4-chi-tiet"), "Mở").click(); await chay();            // nút “Mở” còn lại là đợt 2 (đợt 1 hiện “Đang mở”)
    cho(get(URL_HD), "GET HĐ khi mở đợt 2").resolve(phanHoi(200, CHI_TIET(A1, 7))); await chay();
    cho(get(URL_DOT2), "GET đợt 2").resolve(phanHoi(200, DOT_CT(A1, 1, "dot-2"))); await chay();
    const lai = nutTheoChu($("m4-gui-lai"), "Gửi lại tệp");
    if (lai) { lai.click(); await chay(); }
    assert.strictEqual(lai, null, "C4-01b: nút gửi lại của đợt 1 còn trên đợt 2");
    assert.strictEqual(soPostTep() - truoc, 0, "C4-01b: gửi lại tệp đợt 1 dưới đợt 2");
    console.log("C4-01b đạt");
  }

  // ---------------------------------------------------------------- C4-02: bấm “Dùng tệp mẫu” hai lần trước GET về → một ý định, một tải lên
  {
    await moTab("Nguồn HĐ");
    $("m4f-nguon-mau").value = "hop_dong.docx"; $("m4f-nguon-mau").dispatch("change");
    const nutMau = nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu");
    assert.ok(nutMau.isConnected);
    const soGet = dem(get("/api/m4/mau/hop_dong.docx")), truoc = soPostTep();
    nutMau.click(); nutMau.click();                                       // bấm lặp trước khi GET mẫu đầu tiên settle
    await chay();
    assert.strictEqual(dem(get("/api/m4/mau/hop_dong.docx")) - soGet, 1, "C4-02: bấm lặp tạo hai lần lấy mẫu");
    cho(get("/api/m4/mau/hop_dong.docx"), "C4-02 GET mẫu").resolve(phanHoi(200, null, 30)); await chay();
    nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu").click(); await chay();  // bấm thêm khi POST còn chờ
    assert.strictEqual(soPostTep() - truoc, 1, "C4-02: hơn một tải lên cho cùng ý định mẫu");
    assert.strictEqual(dem(get("/api/m4/mau/hop_dong.docx")) - soGet, 1, "C4-02: lấy lại mẫu khi ý định còn đang tải");
    const p = cho(post("/api/m4/tep"), "C4-02 tải mẫu");
    const info = JSON.parse(decodeURIComponent(p.opts.headers["X-M4-Info"]));
    assert.deepStrictEqual([info.du_an_id, info.vai_tro, info.ten, p.opts.body.name, p.opts.body.size], ["da1", "HOP_DONG", "hop_dong.docx", "hop_dong.docx", 30],
      "C4-02: tải lên không đúng bytes/dự án/metadata gốc");
    // dương không rỗng: thành công → làm mới thật → hàng nguồn mới hiện đúng một lần
    const getTruoc = dem(get("/api/m4"));
    p.resolve(phanHoi(200, {tep_id: "t-mau-c4", sha256: "9".repeat(64), byte_length: 30, hang_moi: true, lap_lai: false})); await chay();
    assert.strictEqual(dem(get("/api/m4")) - getTruoc, 1, "C4-02: continuation sau kết quả rõ không chạy đúng một lần");
    cho(get("/api/m4"), "C4-02 làm mới").resolve(phanHoi(200, TONG2(A1))); await chay(); await traMau();
    cho(get(URL_HD), "C4-02 GET HĐ sau tải").resolve(phanHoi(200, CHI_TIET(A1, 8, [TEP("t-mau-c4", "HOP_DONG", "hop_dong.docx")]))); await chay();
    for (const c of conLai(get(URL_DOT2))) { c.xong = true; c.resolve(phanHoi(200, DOT_CT(A1, 1, "dot-2"))); }
    await chay();
    const hang = [];
    (function duyet(e) { if (e.tagName === "TR" && e.textContent.includes("hop_dong.docx")) hang.push(e); (e.children || []).forEach(duyet); })($("m4-chi-tiet"));
    assert.strictEqual(hang.length, 1, "C4-02: hàng nguồn mới không hiện đúng một lần");
    // chưa rõ cùng ngữ cảnh: lần lấy mẫu mới hợp lệ → POST JSON đứt → bấm lại: dùng File gốc, 0 GET mẫu, cùng header/khóa
    const soGet2 = dem(get("/api/m4/mau/hop_dong.docx"));
    $("m4f-nguon-mau").value = "hop_dong.docx"; $("m4f-nguon-mau").dispatch("change");
    nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu").click(); await chay();
    cho(get("/api/m4/mau/hop_dong.docx"), "C4-02 GET mẫu lần 2").resolve(phanHoi(200, null, 30)); await chay();
    const q1 = cho(post("/api/m4/tep"), "C4-02 tải lần 2");
    q1.resolve(phanHoi(200, JSON_DUT)); await chay();
    nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu").click(); await chay();
    assert.strictEqual(dem(get("/api/m4/mau/hop_dong.docx")) - soGet2, 1, "C4-02: lấy lại mẫu cho ý định chưa rõ");
    const q2 = cho(post("/api/m4/tep"), "C4-02 gửi lại");
    assert.strictEqual(q2.opts.body, q1.opts.body, "C4-02: gửi lại không phải File gốc");
    assert.strictEqual(q2.opts.headers["X-M4-Info"], q1.opts.headers["X-M4-Info"], "C4-02: gửi lại khác header/khóa");
    q2.resolve(phanHoi(200, {tep_id: "t-mau-c4", sha256: "9".repeat(64), byte_length: 30, hang_moi: false, lap_lai: true})); await chay();
    cho(get("/api/m4"), "C4-02 làm mới sau gửi lại").resolve(phanHoi(200, TONG2(A1))); await chay(); await traMau();
    cho(get(URL_HD), "C4-02 GET HĐ sau gửi lại").resolve(phanHoi(200, CHI_TIET(A1, 8, [TEP("t-mau-c4", "HOP_DONG", "hop_dong.docx")]))); await chay();
    for (const c of conLai(get(URL_DOT2))) { c.xong = true; c.resolve(phanHoi(200, DOT_CT(A1, 1, "dot-2"))); }
    await chay();
    assert.strictEqual(conLai(get("/api/m4")).length, 0, "C4-02: continuation chạy hơn một lần");
    console.log("C4-02 đạt");
  }
}

main().then(async () => {
  await chay();
  if (loiNgoai.length) { console.error("M4-01C async LỖI: unhandledRejection ngoài ca:", loiNgoai.map(e => (e && e.stack) || String(e))); process.exit(1); }
  console.log("M4-01C async: mọi ca đạt"); process.exit(0);
}).catch(e => { console.error("M4-01C async LỖI:", (e && e.stack) || e); process.exit(1); });
