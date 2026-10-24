"use strict";
// MASTER-REUSE-02 — kiểm bất đồng bộ trên MÃ THẬT app.js + m4.js (không phải trình duyệt): khung DOM giả/fetch điều khiển của tests/m4_01c_async.cjs.
// CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN). Root chạy: `node tests/m4_master_dung_chung_async.cjs` (Node ≥ 18). Mã thoát 0 = mọi ca đạt.
// Không ghi/xóa tệp, không mạng, không tiến trình con. unhandledRejection ghi lại và làm FAIL ở cuối. Ca:
//  MC1 danh sách master về trễ sau đổi chế độ / đổi dự án / đổi vai → không gắn; dương: lần tìm hiện hành vẽ (ứng viên CRM "Chọn", HĐ đã có hồ sơ "Mở hồ sơ").
//  MC2 bấm "Nhận" hai lần → 1 POST đúng body (expected_master của ứng viên đang thấy, không gửi trạng thái/PN/actor); phản hồi về sau đổi chế độ
//      → không mở hồ sơ, không làm mới.
//  MC3 409 M4_MASTER_DA_DOI → tự tìm lại danh sách, bỏ lựa chọn cũ; chọn lại (token mới) → body đổi → KHÓA MỚI; thành công → làm mới + mở đúng hồ sơ.
//  MC4 panel đối tác: nguồn CRM/master (CAN_SUA_TAI_NGUON) và đã nộp (CAN_PHIEN_BAN_DIEU_CHINH) → chỉ thông báo đúng authority, KHÔNG có nút gắn;
//      XEM → "chỉ xem"; máy chủ chưa trả master_can_cu → thông báo, không nút.
//  MC5 danh sách đối tác về trễ sau đổi HĐ → không gắn; dương: HOLD không chọn được, chọn mapping rõ → POST đúng body; 409 MAPPING_DA_DOI → bỏ lựa chọn,
//      tải lại hồ sơ, lý do đang nhập được giữ.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");
const APP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/app.js"), "utf8");
const M4 = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/m4.js"), "utf8");
const ID_TINH = new Set([...fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/index.html"), "utf8").matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const loiNgoai = [];
process.on("unhandledRejection", e => { loiNgoai.push(e); });

// ------------------------------------------------------------------ DOM giả có kết nối thật (cùng khung m4_01c_async.cjs)
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
    click() { return this.dispatch("click"); }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    removeAttribute(k) { delete this.attrs[k]; }
    getAttribute(k) { return this.attrs[k] ?? null; }
    focus() {} showModal() {} close() {}
  }
  const body = new El("body");
  const document = {
    body, title: "",
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
  const ctx = {
    document, Node: El, console, setTimeout, clearTimeout, Promise, Map, Set, JSON, Math, Date, Number, String, Object, Array, Error, TypeError, SyntaxError,
    encodeURIComponent, decodeURIComponent, URLSearchParams, location: {hash: "#m4"}, crypto: {randomUUID: () => "uuid-" + (++soUuid)},
    URL: {createObjectURL: () => "blob:x", revokeObjectURL() {}}, fetch, File: globalThis.File, navigator: {},
  };
  ctx.window = ctx;
  const wl = {};
  ctx.addEventListener = (t, fn) => { (wl[t] = wl[t] || []).push(fn); };
  vm.createContext(ctx);
  return {ctx, document, calls};
}

function phanHoi(status, data) {
  return {ok: status >= 200 && status < 300, status, headers: {get: () => "application/json"}, json: async () => data, blob: async () => ({size: 0})};
}
const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 8) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (!root) return null; if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
const nutTheoChu = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));

// ------------------------------------------------------------------ DTO giả (hình dạng đúng route máy chủ MASTER-REUSE-02)
const A1 = "MO_PHONG_DU_AN_A1", B1 = "MO_PHONG_DU_AN_B1", XEM = "MO_PHONG_XEM_M4";
const DEMO = [{dang_nhap: A1, vai_tro: "DU_AN"}, {dang_nhap: B1, vai_tro: "DU_AN"}, {dang_nhap: XEM, vai_tro: "XEM"}];
const HD_LIST = (id, duAn = "da1") => ({id, ten: "Gói " + id, so_hop_dong: "SO-" + id, du_an_id: duAn, du_an: duAn === "da1" ? "Dự án A1" : "Dự án A2",
  phap_nhan: "PN_DEMO_A", revision: 1, trang_thai_pl: "CHUA_KHAI", co_tep: false, soan: true, so_dot: 0});
const TONG = (login, them = []) => ({cau_hinh: true, nguoi: {dang_nhap: login, vai_tro: "DU_AN"}, ghi_nguon: {san_sang: true, ly_do: null},
  pham_vi: [{du_an_id: "da1", vai: "PHU_TRACH", du_an: "Dự án A1", du_an_ma: "DA_XD_A1", phap_nhan: "PN_DEMO_A", soan: login !== XEM, xem: true},
    {du_an_id: "da2", vai: "PHU_TRACH", du_an: "Dự án A2", du_an_ma: "DA_XD_A2", phap_nhan: "PN_DEMO_A", soan: login !== XEM, xem: true}],
  hop_dong: [HD_LIST("hd-a"), HD_LIST("hd-b", "da2"), ...them.map(id => HD_LIST(id))], dot: [], danh_muc_ho_so: [], nhanh_sau: [],
  tai_len_toi_da_byte: 52428800, danh_tinh_demo: DEMO});
const MAU = {mau: []};
const MC = (gan, them = {}) => ({hop_dong_id: "x", revision: 1, expected_master: "a".repeat(64),
  master: {module_chu: "M4", trang_thai_master: "HIEU_LUC", crm_giao_ket: null, doi_tac_id: null, doi_tac_ten: null, ma_junsky: null,
    mapping_trang_thai: "KHONG_DOI_TAC", mapping_hien_hanh: null},
  can_cu: {id: "cc1", so: 1, sha256: "a".repeat(64), nguon: "TAO_HO_SO_M4", mapping_id: null, revision_ho_so: 1, ly_do: null, boi: A1, thieu_nguoi: null,
    tao_luc: "2026-10-23T00:00:00Z"},
  dong_bo: true, phien_ban_chua_chung_minh: 0, gan_doi_tac: gan, hold: ["MAPPING_KHONG_DOI_TAC"], ...them});
const CHI_TIET = (id, mc, duAn = "da1") => ({ho_so: {hop_dong_id: id, du_an_id: duAn, ten: "Gói " + id, so_hop_dong: "SO-" + id, du_an: "Dự án", phap_nhan: "PN_DEMO_A",
  revision: 1, rev_tham_so: 1, tep_hop_dong_id: null, trang_thai_pl: "CHUA_KHAI", soan: true},
  tep: [], trich_xuat: [], tham_so: [], xac_nhan: null, phu_luc: [], boq: [], boq_goc_dong: [], dot: [], danh_muc_sha256: "b".repeat(64), nhanh_sau: [],
  master_can_cu: mc});
const UV_CRM = em => ({hop_dong_id: "hd-crm", so_hop_dong: "CRM-01", ma_noi_bo: "NB-01", trang_thai_master: "DA_KY", module_chu: "CRM", doi_tac_id: "dt-x",
  doi_tac_ten: "Khách CRM", da_co_ho_so_m4: false, revision_ho_so: null, expected_master: em});
const UV_CO = {hop_dong_id: "hd-a", so_hop_dong: "SO-hd-a", ma_noi_bo: null, trang_thai_master: "HIEU_LUC", module_chu: "M4", doi_tac_id: null, doi_tac_ten: null,
  da_co_ho_so_m4: true, revision_ho_so: 1, expected_master: "c".repeat(64)};
const DT_OK = {doi_tac_id: "dt-1", ten: "Đối tác Một", ma_junsky: "KH001", mapping_id: "mp-1", expected_mapping: "d".repeat(64), ma_hold: null};
const DT_HOLD = {doi_tac_id: "dt-2", ten: "Đối tác Hai", ma_junsky: null, mapping_id: null, expected_mapping: null, ma_hold: "M4_MAPPING_MO_HO"};

async function main() {
  const {ctx, document, calls} = moiTruong();
  vm.runInContext(APP, ctx, {filename: "app.js"});
  vm.runInContext(M4, ctx, {filename: "m4.js"});
  const $ = id => document.getElementById(id);
  const conLai = pred => calls.filter(c => !c.xong && pred(c));
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const get = url => c => c.method === "GET" && c.url === url;
  const post = url => c => c.method === "POST" && c.url === url;
  const laMaster = c => c.method === "GET" && c.url.startsWith("/api/m4/master-hop-dong?");
  const laDoiTac = c => c.method === "GET" && c.url.startsWith("/api/m4/master-doi-tac?");
  async function traMau() { for (const c of conLai(get("/api/m4/mau"))) { c.xong = true; c.resolve(phanHoi(200, MAU)); } await chay(); }
  async function traTong(login, them = []) { cho(get("/api/m4"), "GET /api/m4 " + login).resolve(phanHoi(200, TONG(login, them))); await chay(); await traMau(); }
  async function doiVaiM4(login) {
    $("m4-vai").value = login; $("m4-doi-vai").click(); await chay();
    cho(post("/api/m4/danh-tinh"), "POST đổi vai " + login).resolve(phanHoi(200, {dang_nhap: login})); await chay();
  }
  async function cheDoCo() { $("m4-tao-co").click(); await chay(); assert.ok($("m4f-tao-q"), "chưa vào chế độ 'Dùng hợp đồng đã có'"); }
  async function timMaster(q) { $("m4f-tao-q").value = q; $("m4-tao-tim").click(); await chay(); return cho(laMaster, "GET master-hop-dong " + q); }
  async function moHdList(id) {
    const li = tim($("m4-ds-hd"), e => e.tagName === "LI" && e.textContent.includes("SO-" + id));
    assert.ok(li, "không thấy HĐ " + id); li.dispatch("click"); await chay();
  }

  for (const c of calls) if (c.url !== "/api/m4") { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND", message: "ngoài ca"})); }
  await traTong(A1);
  assert.ok($("m4-tao-moi") && $("m4-tao-co"), "thiếu hai nút chế độ tạo/nhận");
  assert.ok(nutTheoChu($("m4-tao"), "Tạo hồ sơ HĐ"), "chế độ mặc định phải giữ form tạo mới cũ");

  // ---------------------------------------------------------------- MC1: danh sách master về trễ
  {
    await cheDoCo();
    const g1 = await timMaster("CRM");
    assert.ok(g1.url.includes("du_an_id=da1") && g1.url.includes("q=CRM") && g1.url.includes("limit=25"), "MC1: tham số GET sai: " + g1.url);
    $("m4-tao-moi").click(); await chay();                       // đổi chế độ khi còn chờ
    g1.resolve(phanHoi(200, {du_an_id: "da1", items: [UV_CRM("e".repeat(64))], limit: 25})); await chay();
    assert.strictEqual($("m4-tao-ds-master"), null, "MC1: danh sách cũ gắn sau đổi chế độ");
    await cheDoCo();
    const g2 = await timMaster("CRM");
    $("m4f-tao-du-an").value = "da2"; $("m4f-tao-du-an").dispatch("change"); await chay();  // đổi dự án khi còn chờ
    g2.resolve(phanHoi(200, {du_an_id: "da1", items: [UV_CRM("e".repeat(64))], limit: 25})); await chay();
    assert.strictEqual($("m4-tao-ds-master"), null, "MC1: danh sách dự án cũ gắn sau đổi dự án");
    $("m4f-tao-du-an").value = "da1"; $("m4f-tao-du-an").dispatch("change"); await chay();
    const g3 = await timMaster("CRM");
    await doiVaiM4(B1);                                          // đổi vai khi còn chờ
    g3.resolve(phanHoi(200, {du_an_id: "da1", items: [UV_CRM("e".repeat(64))], limit: 25})); await chay();
    assert.strictEqual($("m4-tao-ds-master"), null, "MC1: danh sách của vai cũ gắn sau đổi vai");
    await traTong(B1);
    await doiVaiM4(A1); await traTong(A1);
    assert.ok(nutTheoChu($("m4-tao"), "Tạo hồ sơ HĐ"), "MC1: sau đổi vai phải về chế độ tạo mới");
    await cheDoCo();
    const g4 = await timMaster("SO");
    g4.resolve(phanHoi(200, {du_an_id: "da1", items: [UV_CRM("e".repeat(64)), UV_CO], limit: 25})); await chay();
    const ds = $("m4-tao-ds-master");
    assert.ok(ds && ds.isConnected, "MC1: lần tìm hiện hành không vẽ");
    const liCrm = tim(ds, e => e.tagName === "LI" && e.textContent.includes("CRM-01")), liCo = tim(ds, e => e.tagName === "LI" && e.textContent.includes("SO-hd-a"));
    assert.ok(nutTheoChu(liCrm, "Chọn") && !nutTheoChu(liCrm, "Mở hồ sơ"), "MC1: ứng viên chưa có hồ sơ phải có 'Chọn'");
    assert.ok(nutTheoChu(liCo, "Mở hồ sơ") && !nutTheoChu(liCo, "Chọn"), "MC1: HĐ đã có hồ sơ phải 'Mở hồ sơ', không nhận lại");
    assert.ok(liCrm.textContent.includes("Hồ sơ M4: chưa có") && liCrm.textContent.includes("Master:"), "MC1: trạng thái master và readiness M4 phải tách");
    console.log("MC1 đạt");
  }

  // ---------------------------------------------------------------- MC2: bấm hai lần → 1 POST; phản hồi về sau đổi chế độ không mở hồ sơ
  {
    nutTheoChu(tim($("m4-tao-ds-master"), e => e.tagName === "LI" && e.textContent.includes("CRM-01")), "Chọn").click(); await chay();
    $("m4f-tao-nhan-ten").value = "Gói CRM";
    $("m4-tao-nhan").click(); $("m4-tao-nhan").click(); await chay();
    assert.strictEqual(conLai(post("/api/m4/hop-dong/nhan-master")).length, 1, "MC2: bấm lặp gửi hơn một POST");
    const p = cho(post("/api/m4/hop-dong/nhan-master"), "POST nhận");
    const b = JSON.parse(p.opts.body);
    assert.deepStrictEqual(Object.keys(b).sort(), ["du_an_id", "expected_master", "hop_dong_id", "khoa", "ten"], "MC2: body có trường ngoài hợp đồng");
    assert.deepStrictEqual([b.du_an_id, b.hop_dong_id, b.ten, b.expected_master], ["da1", "hd-crm", "Gói CRM", "e".repeat(64)]);
    const soGet = calls.filter(c => c.method === "GET").length;
    $("m4-tao-moi").click(); await chay();
    p.resolve(phanHoi(200, {hop_dong_id: "hd-crm", revision: 1, expected_master: "e".repeat(64), da_co_san: false, lap_lai: false})); await chay();
    assert.strictEqual(calls.filter(c => c.method === "GET").length, soGet, "MC2: phản hồi cũ làm mới/mở hồ sơ sau đổi chế độ");
    console.log("MC2 đạt");
  }

  // ---------------------------------------------------------------- MC3: 409 MASTER_DA_DOI → tìm lại, chọn lại, khóa mới, thành công mở đúng hồ sơ
  {
    await cheDoCo();
    (await timMaster("CRM")).resolve(phanHoi(200, {du_an_id: "da1", items: [UV_CRM("e".repeat(64))], limit: 25})); await chay();
    nutTheoChu($("m4-tao-ds-master"), "Chọn").click(); await chay();
    $("m4f-tao-nhan-ten").value = "Gói CRM";
    $("m4-tao-nhan").click(); await chay();
    const p1 = cho(post("/api/m4/hop-dong/nhan-master"), "POST nhận (token cũ)");
    const k1 = JSON.parse(p1.opts.body).khoa;
    p1.resolve(phanHoi(409, {error: "M4_MASTER_DA_DOI", message: "Hợp đồng nguồn đã đổi"})); await chay();
    assert.ok($("m4-status").textContent.includes("đã tải lại"), "MC3: thiếu hướng dẫn tiếng Việt cho M4_MASTER_DA_DOI");
    const g = cho(laMaster, "MC3: 409 phải tự tìm lại danh sách");
    assert.ok(g.url.includes("q=CRM"), "MC3: tìm lại không giữ từ khóa");
    assert.strictEqual($("m4-tao-nhan"), null, "MC3: lựa chọn/expected_master cũ còn dùng được sau 409");
    g.resolve(phanHoi(200, {du_an_id: "da1", items: [UV_CRM("f".repeat(64))], limit: 25})); await chay();
    nutTheoChu($("m4-tao-ds-master"), "Chọn").click(); await chay();
    $("m4f-tao-nhan-ten").value = "Gói CRM";
    $("m4-tao-nhan").click(); await chay();
    const p2 = cho(post("/api/m4/hop-dong/nhan-master"), "POST nhận (token mới)");
    const b2 = JSON.parse(p2.opts.body);
    assert.strictEqual(b2.expected_master, "f".repeat(64), "MC3: gửi expected_master cũ");
    assert.notStrictEqual(b2.khoa, k1, "MC3: body đổi mà dùng lại khóa cũ");
    p2.resolve(phanHoi(200, {hop_dong_id: "hd-crm", revision: 1, expected_master: "f".repeat(64), da_co_san: false, lap_lai: false})); await chay();
    await traTong(A1, ["hd-crm"]);
    const ct = cho(get("/api/m4/hop-dong/hd-crm"), "MC3: thành công phải mở đúng hồ sơ vừa nhận");
    ct.resolve(phanHoi(200, CHI_TIET("hd-crm", MC({duoc: false, ma: "M4_MASTER_CAN_SUA_TAI_NGUON"}, {
      master: {module_chu: "CRM", trang_thai_master: "DA_KY", crm_giao_ket: "DA_KY", doi_tac_id: "dt-x", doi_tac_ten: "Khách CRM", ma_junsky: "KH9",
        mapping_trang_thai: "OK", mapping_hien_hanh: "mp-x"}, hold: []})))); await chay();
    console.log("MC3 đạt");
  }

  // ---------------------------------------------------------------- MC4: panel đối tác chỉ thông báo khi không được gắn
  {
    const dt = $("m4-doi-tac");
    assert.ok(dt && dt.isConnected, "MC4: thiếu panel đối tác trong tab Nguồn HĐ");
    assert.ok(dt.textContent.includes("CRM/master quản lý"), "MC4: thiếu hướng dẫn authority nguồn CRM/master");
    assert.strictEqual($("m4-dt-gan"), null, "MC4: HĐ nguồn CRM vẫn có nút gắn đối tác");
    assert.strictEqual(nutTheoChu($("m4-chi-tiet"), "Gắn đối tác"), null);
    await moHdList("hd-a");
    cho(get("/api/m4/hop-dong/hd-a"), "GET hd-a").resolve(phanHoi(200, CHI_TIET("hd-a", MC({duoc: false, ma: "M4_MASTER_CAN_PHIEN_BAN_DIEU_CHINH"})))); await chay();
    assert.ok($("m4-doi-tac").textContent.includes("CHƯA triển khai"), "MC4: hồ sơ đã nộp phải nói rõ điều chỉnh sau nộp chưa triển khai");
    assert.strictEqual($("m4-dt-gan"), null, "MC4: hồ sơ đã nộp vẫn có nút gắn");
    await moHdList("hd-b");
    cho(get("/api/m4/hop-dong/hd-b"), "GET hd-b").resolve(phanHoi(200, CHI_TIET("hd-b", null, "da2"))); await chay();
    assert.ok($("m4-chi-tiet").textContent.includes("chưa trả căn cứ master"), "MC4: master_can_cu null phải báo, không dựng căn cứ giả");
    assert.strictEqual($("m4-dt-gan"), null);
    await doiVaiM4(XEM); await traTong(XEM);
    await moHdList("hd-a");
    cho(get("/api/m4/hop-dong/hd-a"), "GET hd-a (XEM)").resolve(phanHoi(200, CHI_TIET("hd-a", MC({duoc: false, ma: "M4_KHONG_CO_QUYEN_DU_AN"})))); await chay();
    assert.ok($("m4-doi-tac").textContent.includes("chỉ xem"), "MC4: XEM phải thấy thông báo chỉ xem");
    assert.strictEqual($("m4-dt-gan"), null, "MC4: XEM có nút gắn");
    await doiVaiM4(A1); await traTong(A1);
    console.log("MC4 đạt");
  }

  // ---------------------------------------------------------------- MC5: danh sách đối tác về trễ; HOLD; POST đúng body; 409 MAPPING_DA_DOI giữ lý do
  {
    await moHdList("hd-a");
    cho(get("/api/m4/hop-dong/hd-a"), "GET hd-a").resolve(phanHoi(200, CHI_TIET("hd-a", MC({duoc: true, ma: null})))); await chay();
    assert.ok($("m4-dt-gan") && $("m4-dt-gan").disabled, "MC5: nút gắn phải tắt khi chưa chọn mapping");
    $("m4f-dt-q").value = "Đối tác"; $("m4-dt-tim").click(); await chay();
    const d1 = cho(laDoiTac, "GET master-doi-tac (hd-a)");
    assert.ok(d1.url.includes("du_an_id=da1") && d1.url.includes("limit=25"));
    await moHdList("hd-b");                                      // đổi HĐ khi còn chờ
    cho(get("/api/m4/hop-dong/hd-b"), "GET hd-b").resolve(phanHoi(200, CHI_TIET("hd-b", MC({duoc: true, ma: null}), "da2"))); await chay();
    d1.resolve(phanHoi(200, {du_an_id: "da1", items: [DT_OK], limit: 25})); await chay();
    assert.strictEqual(nutTheoChu($("m4-dt-ds"), "Chọn"), null, "MC5: danh sách đối tác của HĐ cũ gắn vào HĐ mới");
    await moHdList("hd-a");
    cho(get("/api/m4/hop-dong/hd-a"), "GET hd-a lại").resolve(phanHoi(200, CHI_TIET("hd-a", MC({duoc: true, ma: null})))); await chay();
    $("m4f-dt-q").value = "Đối tác"; $("m4-dt-tim").click(); await chay();
    cho(laDoiTac, "GET master-doi-tac hiện hành").resolve(phanHoi(200, {du_an_id: "da1", items: [DT_OK, DT_HOLD], limit: 25})); await chay();
    const hangHold = tim($("m4-dt-ds"), e => e.tagName === "TR" && e.textContent.includes("Đối tác Hai"));
    assert.ok(nutTheoChu(hangHold, "Chọn").disabled, "MC5: mapping HOLD chọn được");
    nutTheoChu(tim($("m4-dt-ds"), e => e.tagName === "TR" && e.textContent.includes("Đối tác Một")), "Chọn").click(); await chay();
    assert.strictEqual($("m4-dt-gan").disabled, false, "MC5: chọn mapping rõ mà nút gắn vẫn tắt");
    $("m4f-dt-ly-do").value = "Theo HĐ ký"; $("m4f-dt-ly-do").dispatch("input");
    $("m4-dt-gan").click(); $("m4-dt-gan").click(); await chay();
    assert.strictEqual(conLai(post("/api/m4/hop-dong/gan-doi-tac")).length, 1, "MC5: bấm lặp gửi hơn một POST");
    const pg = cho(post("/api/m4/hop-dong/gan-doi-tac"), "POST gắn");
    const b = JSON.parse(pg.opts.body);
    assert.deepStrictEqual(Object.keys(b).sort(), ["doi_tac_id", "expected_mapping", "expected_master", "hop_dong_id", "khoa", "ly_do", "mapping_id", "revision"]);
    assert.deepStrictEqual([b.hop_dong_id, b.doi_tac_id, b.mapping_id, b.revision, b.expected_master, b.expected_mapping, b.ly_do],
      ["hd-a", "dt-1", "mp-1", 1, "a".repeat(64), "d".repeat(64), "Theo HĐ ký"]);
    pg.resolve(phanHoi(409, {error: "M4_MAPPING_DA_DOI", message: "Mapping đã đổi"})); await chay();
    const lai = cho(get("/api/m4/hop-dong/hd-a"), "MC5: 409 MAPPING_DA_DOI phải tải lại hồ sơ");
    lai.resolve(phanHoi(200, CHI_TIET("hd-a", MC({duoc: true, ma: null}, {revision: 1})))); await chay();
    assert.ok($("m4-dt-gan").disabled, "MC5: lựa chọn mapping cũ còn sau 409");
    assert.strictEqual($("m4f-dt-ly-do").value, "Theo HĐ ký", "MC5: lý do đang nhập bị mất sau tải lại");
    assert.strictEqual(nutTheoChu($("m4-dt-ds"), "Đang chọn"), null);
    console.log("MC5 đạt");
  }
}

main().then(async () => {
  await chay();
  if (loiNgoai.length) { console.error("MASTER-REUSE-02 async LỖI: unhandledRejection ngoài ca:", loiNgoai.map(e => (e && e.stack) || String(e))); process.exit(1); }
  console.log("MASTER-REUSE-02 async: mọi ca đạt"); process.exit(0);
}).catch(e => { console.error("MASTER-REUSE-02 async LỖI:", (e && e.stack) || e); process.exit(1); });
