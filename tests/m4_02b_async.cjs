"use strict";
// M4-02B FIX01 — kiểm bất đồng bộ trên MÃ THẬT app.js (cổng kttChung thật) + m4/giao_dien/chung_tu.js (màn Chứng từ L3), cùng khung harness của
// tests/m4_01c_async.cjs: DOM giả tối thiểu có quan hệ cha–con/kết nối thật, fetch trả Promise do ca điều khiển (pending, đảo thứ tự, lỗi, JSON đứt).
// CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY). Root chạy: `node tests/m4_02b_async.cjs` (Node ≥ 18). Mã thoát 0 = mọi ca đạt; khác 0 = lỗi.
// Không ghi/xóa tệp, không mạng, không tiến trình con. unhandledRejection được ghi lại và làm FAIL ở cuối. Màn được mount như shell m4.js làm
// (window.kttM4ChungTu.ve(vùng ĐÃ gắn vào document, ngữ cảnh {hdId, dots, dotId, nguoi, duAnId, phapNhan})); đổi vai/HĐ = shell gọi lại ve với ngữ cảnh
// mới (xem m4.js veChungTu). Kiểm hành vi qua DOM + payload POST thật, không regex mã nguồn. Ca:
//  U1  sửa từng trường (số/ngày/loại) → nút Lưu bật NGAY, không vẽ lại form (ô đang gõ vẫn là cùng phần tử, còn gắn); trả về giá trị cũ → nút tắt;
//      payload đúng run/revision/basis/lý do/tai_lieu theo trường.
//  U2  sửa thêm khi lệnh sửa đang bay → giữ nháp mới; bấm Lưu lần nữa khi đang bay → 0 POST; ACK chỉ dọn đúng giá trị đã gửi; làm mới căn cứ →
//      lần Lưu kế tiếp dùng revision/basis MỚI (refresh revision metadata).
//  U3  chưa rõ (mất kết nối, rồi 200 + JSON đứt) → Gửi lại y nguyên ĐÚNG body + khóa; trong lúc chưa rõ, Lưu không phát lệnh mới; ACK của lần gửi
//      lại dọn đúng phần đã gửi, giữ sửa mới.
//  U4  đổi vai khi POST đang bay → ACK muộn không toast/không làm mới/không dọn nháp của ngữ cảnh mới; lỗi GET chi tiết/danh sách về muộn sau khi
//      người dùng đã sửa → không vẽ lại/không đổi trạng thái; 403 chi tiết (thu hồi) → xử lý có chủ ý (gỡ chi tiết).
//  U5  run/chi tiết/artifact gắn đúng run: mở run B gỡ ngay nút tải của run A; phản hồi A về muộn bị bỏ; tải gắn đúng run B; đổi run khi blob chưa
//      về → không click; dương: tải run hiện hành → click đúng một lần.
//  U6  ma trận theo so sánh typed: KL NULL / khác ĐVT → “chưa so được” (không ✓); 0 tường minh hiển thị 0; so được → ✓.
//  U7  409 REVISION_CU → làm mới danh sách, nháp giữ, nút Lưu vẫn bật; ghép tay dòng → payload đúng đích BOQ hiệu lực; ACK dọn đúng nháp ghép.
// FIX02A (CODE_ONLY, NOT_RUN_CODE_ONLY — chưa chạy; không kế thừa kết quả U1–U7 của FIX01):
//  U8  (U-A) continuation chạy sau ACK: giữ GET làm mới, rồi đổi đợt / đổi PN cùng vai / tab away–back (huy + ve thật của shell) → nhả GET cũ:
//      0 GET chi tiết của run mới, không hiện run dưới ngữ cảnh mới.
//  U9  (R5) sửa UNKNOWN khóa1 → Gửi lại đang bay → sang đợt B (B không thấy, B chạy được) → về A: không có nút Gửi lại thứ hai, bodyY bị chặn
//      (0 POST); Gửi lại về CHƯA RÕ muộn → bản ghi gốc còn, Gửi lại = body/khóa1; ACK rõ chỉ gỡ ý định đó, giữ nháp bodyY; sau đó bodyY = khóa mới.
//  U10 (R6) POST1 đang bay → vai B (cùng body → khóa KHÁC, không bị khóa của A) → về A (ABA đủ ngữ cảnh): cùng body và bodyR2 bị chặn (0 POST2);
//      ghép (đích khác) không bị chặn; POST1 CHƯA RÕ muộn → Gửi lại đúng khóa1; hai ý định chưa rõ khác đích giữ riêng, ACK ghép không gỡ sửa;
//      mọi POST của đích sửa A chỉ một khóa; sau rõ → bodyR2 khóa mới. Thứ tự ngược: UNKNOWN về khi đang ở đợt B → B không thấy; về A còn Gửi lại.
//  U11 (U-D) dấu ✓/✗ theo dung sai nguồn max(1e-3, |đối chiếu|·1e-6) hai phía ngưỡng tuyệt đối/tương đối cho NT/KL kỳ này và GN/KL lũy kế, toán
//      hạng lấy từ so sánh typed; NULL / khác ĐVT / KHONG_AP_DUNG không có dấu; 0 tường minh hiển thị 0 và ✓; nt NULL với KL > 0 → ✗.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");
const APP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/app.js"), "utf8");
const CT = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/chung_tu.js"), "utf8");
const ID_TINH = new Set([...fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/index.html"), "utf8").matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const BLOB_GOC = globalThis.Blob || (() => { try { return require("buffer").Blob; } catch (_) { return null; } })();
const loiNgoai = [];
process.on("unhandledRejection", e => { loiNgoai.push(e); });

// ------------------------------------------------------------------ DOM giả có kết nối thật (khung m4_01c_async.cjs + querySelector theo class)
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
    get textContent() { return this._text + this.children.map(c => c.textContent).join(""); }
    set textContent(v) { for (const c of this.children) c.parent = null; this._text = String(v ?? ""); this.children = []; }
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
    querySelector(s) {  // chỉ ".lớp" (đủ cho mã thật dùng) — tìm hậu duệ theo thứ tự DFS
      const lop = s.startsWith(".") ? s.slice(1) : null;
      const tim = e => { for (const c of e.children) { if (lop && c._cls && c._cls.has(lop)) return c; const r = tim(c); if (r) return r; } return null; };
      return lop ? tim(this) : null;
    }
    focus() {} showModal() {} close() {}
  }
  const body = new El("body");
  const document = {
    body, title: "", head: new El("head"),
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
    URL: {createObjectURL: () => "blob:x", revokeObjectURL() {}}, fetch, navigator: {}, Intl,
  };
  ctx.window = ctx;
  ctx.addEventListener = () => {};
  vm.createContext(ctx);
  return {ctx, document, calls, body};
}

const JSON_DUT = Symbol("json-dut");
function phanHoi(status, data, blobSize) {
  return {ok: status >= 200 && status < 300, status, headers: {get: () => "application/json"},
    json: async () => { if (data === JSON_DUT) throw new SyntaxError("Unexpected end of JSON input"); return data; },
    blob: async () => (BLOB_GOC ? new BLOB_GOC([new Uint8Array(blobSize ?? 0)], {type: "application/octet-stream"}) : {size: blobSize ?? 0, type: "application/octet-stream"})};
}
const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 10) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
const nutTheoChu = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));
const theoNhan = (root, s) => tim(root, e => e.attrs && e.attrs["aria-label"] === s);

// ------------------------------------------------------------------ dữ liệu DTO tin cậy giả (hình dạng đúng service chung_tu_ds / chung_tu_chi_tiet)
const BASIS = rev => "b".repeat(63) + String(rev);
const DOTS = [{id: "dot-1", so_dot: 1, ngay_nghiem_thu: "2026-03-01", trang_thai: "DA_NOP"}, {id: "dot-2", so_dot: 2, ngay_nghiem_thu: "2026-04-01", trang_thai: "NHAP"}];
const NGU_CANH = (nguoi = "MO_PHONG_DU_AN_A1", them = {}) => ({hdId: "hd-1", soHd: "123/2025", dots: DOTS, dotId: "dot-1", nguoi, duAnId: "da1", phapNhan: "PN_DEMO_A", ...them});
const RUN = (id, luc) => ({id, revision: 0, trang_thai: "PARTIAL", basis_sha256: BASIS(0), parent_run_id: null, quyen: "SOAN", tao_boi: "MO_PHONG_DU_AN_A1",
  tao_luc: luc, xong_luc: luc, ly_do: null, cong_bo: true, coverage: {C01: {trang_thai: "INCOMPLETE"}}, dem: {}});
const DS = rev => ({dot: {id: "dot-1", so_dot: 1}, revision: rev, tai_lieu: [{tep_id: "t-nt", muc: "A01", ten_goc: "bb_nghiem_thu.docx", media_type: "x/docx", byte_length: 10,
  raw_sha256: "1".repeat(64), doc: "NATIVE"}, {tep_id: "t-gn", muc: "A02", ten_goc: "bb_giao_nhan.xlsx", media_type: "x/xlsx", byte_length: 10, raw_sha256: "2".repeat(64), doc: "NATIVE"}],
  runs: [RUN("r1", "2026-03-02T10:00:00"), RUN("r2", "2026-03-03T10:00:00")], revisions: [], manual_map: [],
  co_so: {san_sang: true, basis_sha256: BASIS(rev), quyen: "SOAN", revision: rev, phu_thuoc: {}, so_ghep_tay: 0, engine: "E"},
  loai: {BB_NT: "BB nghiệm thu", BB_GN: "BB giao nhận", CO: "CO", KHAC: "Khác"}, provider: {}});
const DS2 = rev => ({...DS(rev), dot: {id: "dot-2", so_dot: 2}, runs: []});  // đợt 2 (ngữ cảnh B): cùng hình dạng, chưa có lần chạy
const SS = (tt, ly) => ({trang_thai: tt, ly_do: ly || null});
const VT = (dong) => ({trang_thai: "CHECKED", loai: "XLSX", sheet: "GiaoNhan", dong});
const RES = () => ({trang_thai: "PARTIAL", so_hd: "123/2025", ngay_nt: "2026-03-01", engine: "E", coverage: {C01: {trang_thai: "INCOMPLETE", ly_do: "x"}},
  phat_hien: [], dem: {}, chu_thich_phat_hien: [], c06_cap: [],
  hang_muc: [{khoa: "HM-01", ma_hm: "HM-01", ten: "Đào đất", dvt: "m3", nguon_boq: [{boq_id: "bq1", dong: 2}]},
    {khoa: "HM-02", ma_hm: "HM-02", ten: "Bê tông móng", dvt: "m3", nguon_boq: [{boq_id: "bq1", dong: 3}]},
    {khoa: "HM-03", ma_hm: "HM-03", ten: "Cốt thép", dvt: "kg", nguon_boq: [{boq_id: "bq1", dong: 4}]}],
  ma_tran: [
    {khoa: "HM-01", ma_hm: "HM-01", ten: "Đào đất", dvt: "m3", kl_kn: null, kl_lk: null, nt: 40, nt_docs: ["bb_nghiem_thu.docx"], gn: 0, gn_docs: [], co: [], cq: [], pl: [], ld: [],
      so_sanh: {C01: SS("CHUA_SO_DUOC", "KL kỳ này NULL"), C03: SS("KHONG_AP_DUNG")}},
    {khoa: "HM-02", ma_hm: "HM-02", ten: "Bê tông móng", dvt: "m3", kl_kn: 0, kl_lk: 5, nt: null, nt_docs: [], gn: 5, gn_docs: ["bb_giao_nhan.xlsx"], co: [], cq: [], pl: [], ld: [],
      so_sanh: {C01: SS("SO_DUOC"), C03: SS("CHUA_SO_DUOC", "1 dòng khác ĐVT")}},
    {khoa: "HM-03", ma_hm: "HM-03", ten: "Cốt thép", dvt: "kg", kl_kn: 10, kl_lk: 10, nt: 10, nt_docs: ["bb_nghiem_thu.docx"], gn: 10, gn_docs: ["bb_giao_nhan.xlsx"], co: [], cq: [], pl: [], ld: [],
      so_sanh: {C01: SS("SO_DUOC"), C03: SS("SO_DUOC")}}],
  provenance: {nguon_hang_muc: "L2", ghep_tay: [], auto: {tai_lieu: []}},
  tai_lieu: [
    {tep_id: "t-nt", ten: "bb_nghiem_thu.docx", trang_thai_doc: "CHECKED", trang_thai_dong: "CHECKED", loai: "BB_NT", so: "01/BBNT-2026", ngay: "2026-03-01",
      trich: {loai: "BB_NT", so: "01/BBNT-2026", ngay: "2026-03-01"}, hd_ref: [["123", "2025"]], canh_bao: [], thich_nghi_cot: [], bo: false,
      dong: [{row_id: "a".repeat(64), ten: "Đào đất", dvt: "m3", so_luong: 40, khoa: "HM-01", khop: 0.95, vi_tri: "bảng 1 dòng 2", vi_tri_vat_ly: {trang_thai: "CHECKED", loai: "DOCX", bang: 1, dong: 2}}]},
    {tep_id: "t-gn", ten: "bb_giao_nhan.xlsx", trang_thai_doc: "CHECKED", trang_thai_dong: "CHECKED", loai: "BB_GN", so: "05/BBGN-2026", ngay: "2026-02-25",
      trich: {loai: "BB_GN", so: "05/BBGN-2026", ngay: "2026-02-25"}, hd_ref: [["123", "2025"]], canh_bao: [], thich_nghi_cot: [], bo: false,
      dong: [{row_id: "c".repeat(64), ten: "Xi măng PC40", dvt: "m3", so_luong: 10, khoa: null, khop: 0, vi_tri: "bảng 1 dòng 2", vi_tri_vat_ly: VT(6)}]}]});
const CHI_TIET = id => ({run: {...RUN(id, "2026-03-02T10:00:00"), id}, ket_qua: {ket_qua: RES(), ket_qua_sha256: "d".repeat(64), cong_bo: true},
  artifact: [{id: "a-" + id, loai: "REPORT_L3", ten: `bc-${id}.xlsx`, raw_sha256: "e".repeat(64), byte_length: 10}], con: [], manual_map: [], revisions: []});

async function main() {
  const {ctx, document, calls, body} = moiTruong();
  vm.runInContext(APP, ctx, {filename: "app.js"});
  for (const c of calls) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND", message: "ngoài ca"})); }  // module khác của app.js: lỗi có chủ đích
  await chay();
  vm.runInContext(CT, ctx, {filename: "chung_tu.js"});
  const W = ctx.window;
  assert.ok(W.kttM4ChungTu && typeof W.kttM4ChungTu.ve === "function", "chung_tu.js không công bố window.kttM4ChungTu");
  const conLai = pred => calls.filter(c => !c.xong && pred(c));
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const dem = pred => calls.filter(pred).length;
  const URL_DS = "/api/m4/chung-tu?dot_id=dot-1";
  const getDs = c => c.method === "GET" && c.url === URL_DS;
  const getCt = id => c => c.method === "GET" && c.url === "/api/m4/chung-tu/" + id;
  const post = p => c => c.method === "POST" && c.url === "/api/m4/" + p;
  const box = document.createElement("div");
  body.append(box);
  const trangThaiChu = () => (box.querySelector("m4-ct-status") || box.querySelector(".m4-ct-status") || {textContent: ""}).textContent;
  async function traDs(rev) { cho(getDs, "GET danh sách").resolve(phanHoi(200, DS(rev))); await chay(); }
  async function moRun(id, {tra = true} = {}) {
    const tr = tim(box, e => e.tagName === "TR" && e.textContent.includes(id === "r1" ? "2026-03-02 10:00:00" : "2026-03-03 10:00:00") && !!nutTheoChu(e, "Mở"));
    assert.ok(tr, "không thấy nút Mở của " + id);
    nutTheoChu(tr, "Mở").click(); await chay();
    if (tra) { cho(getCt(id), "GET chi tiết " + id).resolve(phanHoi(200, CHI_TIET(id))); await chay(); }
  }
  const nutLuu = () => nutTheoChu(box, "Lưu sửa");
  const nhap = (nhan, v, su = "input") => { const e = theoNhan(box, nhan); assert.ok(e && e.isConnected, "không có ô " + nhan); e.value = v; e.dispatch(su); return e; };

  // mount như shell (vùng đã gắn vào document)
  W.kttM4ChungTu.ve(box, NGU_CANH()); await chay();
  await traDs(0);
  await moRun("r1");
  assert.ok(box.textContent.includes("3. Chứng từ đã đọc"), "chưa vẽ chi tiết run r1");

  // ---------------------------------------------------------------- U1 sửa từng trường → nút Lưu bật tại chỗ, payload đúng
  {
    const nut = nutLuu();
    assert.ok(nut && nut.disabled, "U1: nút Lưu phải tắt khi chưa sửa");
    const so = nhap("Số chứng từ bb_nghiem_thu.docx", "01/BBNT-2026/A");
    assert.strictEqual(nutLuu(), nut, "U1: sửa một ký tự làm vẽ lại cả form");
    assert.ok(so.isConnected, "U1: ô đang gõ bị gỡ (mất focus)");
    assert.strictEqual(nut.disabled, false, "U1: sửa số không bật nút Lưu");
    nhap("Số chứng từ bb_nghiem_thu.docx", "01/BBNT-2026");  // trả về giá trị hiệu lực → không còn sửa
    assert.strictEqual(nut.disabled, true, "U1: trả về giá trị cũ vẫn bật nút Lưu");
    nhap("Số chứng từ bb_nghiem_thu.docx", "01/BBNT-2026/A");
    nhap("Ngày chứng từ bb_nghiem_thu.docx", "2026-03-05");
    assert.strictEqual(nut.disabled, false, "U1: sửa ngày không bật nút Lưu");
    nhap("Loại chứng từ bb_giao_nhan.xlsx", "CO", "change");
    nhap("Lý do sửa metadata", "lý do 1");
    assert.strictEqual(nutLuu(), nut);
    nut.click(); await chay();
    const p = cho(post("chung-tu/sua"), "U1: POST sửa");
    const b = JSON.parse(p.opts.body);
    assert.deepStrictEqual({...b, khoa: undefined}, {run_id: "r1", revision: 0, expected_basis: BASIS(0), ly_do: "lý do 1", khoa: undefined,
      tai_lieu: [{tep_id: "t-nt", so: "01/BBNT-2026/A", ngay: "2026-03-05"}, {tep_id: "t-gn", loai: "CO"}]}, "U1: payload sửa sai");
    assert.ok(typeof b.khoa === "string" && b.khoa.length > 4, "U1: thiếu khóa thao tác");

    // ------------------------------------------------------------ U2 sửa thêm khi đang bay; bấm lặp 0 POST; ACK dọn đúng phần đã gửi; refresh revision
    nhap("Số chứng từ bb_giao_nhan.xlsx", "06/BBGN-X");
    assert.strictEqual(nutLuu().disabled, true, "U2: nút Lưu phải tắt khi lệnh sửa đang bay");
    nutLuu().disabled = false; nutLuu().click(); await chay();  // kể cả nếu nút bị bật lại, lệnh mới không được phát khi đang bay
    assert.strictEqual(conLai(post("chung-tu/sua")).length, 0, "U2: bấm Lưu khi đang bay phát POST mới");
    p.resolve(phanHoi(200, {revision_id: "rv1", revision: 1, lap_lai: false})); await chay();
    await traDs(1);
    assert.strictEqual(theoNhan(box, "Số chứng từ bb_giao_nhan.xlsx").value, "06/BBGN-X", "U2: ACK dọn mất sửa mới (gửi sau lúc POST)");
    assert.strictEqual(theoNhan(box, "Số chứng từ bb_nghiem_thu.docx").value, "01/BBNT-2026", "U2: ACK không dọn trường đã gửi");
    assert.strictEqual(theoNhan(box, "Lý do sửa metadata").value, "", "U2: lý do đã gửi không được dọn");
    assert.strictEqual(nutLuu().disabled, false, "U2: còn nháp mới mà nút Lưu tắt");
    nhap("Lý do sửa metadata", "lý do 2");
    nutLuu().click(); await chay();
    const p2 = cho(post("chung-tu/sua"), "U2: POST sửa lần 2");
    const b2 = JSON.parse(p2.opts.body);
    assert.deepStrictEqual([b2.revision, b2.expected_basis, b2.tai_lieu], [1, BASIS(1), [{tep_id: "t-gn", so: "06/BBGN-X"}]], "U2: lần Lưu sau không dùng revision/basis mới");

    // ------------------------------------------------------------ U3 chưa rõ → gửi lại y nguyên; Lưu không phát lệnh mới; ACK dọn đúng phần gửi
    p2.reject(new TypeError("Failed to fetch")); await chay();
    const lai = nutTheoChu(box, "Gửi lại y nguyên");
    assert.ok(lai, "U3: mất kết nối mà không có nút Gửi lại");
    nhap("Ngày chứng từ bb_nghiem_thu.docx", "2026-03-07");  // sửa mới trong lúc chưa rõ
    nutLuu().disabled = false; nutLuu().click(); await chay();
    assert.strictEqual(conLai(post("chung-tu/sua")).length, 0, "U3: lệnh chưa rõ mà Lưu phát lệnh mới (khóa mới)");
    assert.ok(trangThaiChu().includes("Gửi lại"), "U3: không báo phải Gửi lại trước");
    nutTheoChu(box, "Gửi lại y nguyên").click(); await chay();
    const p3 = cho(post("chung-tu/sua"), "U3: POST gửi lại 1");
    assert.deepStrictEqual(JSON.parse(p3.opts.body), b2, "U3: gửi lại khác body/khóa");
    p3.resolve(phanHoi(200, JSON_DUT)); await chay();  // HTTP 200 nhưng JSON đứt: vẫn chưa rõ
    assert.ok(nutTheoChu(box, "Gửi lại y nguyên"), "U3: JSON đứt sau 200 bị coi là xong");
    nutTheoChu(box, "Gửi lại y nguyên").click(); await chay();
    const p4 = cho(post("chung-tu/sua"), "U3: POST gửi lại 2");
    assert.deepStrictEqual(JSON.parse(p4.opts.body), b2, "U3: gửi lại lần 2 khác body/khóa");
    p4.resolve(phanHoi(200, {revision_id: "rv2", revision: 2, lap_lai: true})); await chay();
    await traDs(2);
    assert.strictEqual(theoNhan(box, "Số chứng từ bb_giao_nhan.xlsx").value, "05/BBGN-2026", "U3: ACK gửi lại không dọn phần đã gửi");
    assert.strictEqual(theoNhan(box, "Ngày chứng từ bb_nghiem_thu.docx").value, "2026-03-07", "U3: ACK gửi lại dọn mất sửa mới");
    assert.strictEqual(nutTheoChu(box, "Gửi lại y nguyên"), null, "U3: nút Gửi lại còn sau khi kết quả rõ");
    assert.strictEqual(dem(post("chung-tu/sua")), 4, "U3: số POST sửa sai (2 ý định + 2 lần gửi lại)");
    console.log("U1–U3 đạt");
  }

  // ---------------------------------------------------------------- U4 đổi vai khi POST đang bay; lỗi GET về muộn sau khi sửa; 403 thu hồi
  {
    nhap("Lý do sửa metadata", "lý do 3");
    nutLuu().click(); await chay();
    const p = cho(post("chung-tu/sua"), "U4: POST sửa trước đổi vai");
    const getTruoc = dem(c => c.method === "GET");
    W.kttM4ChungTu.ve(box, NGU_CANH("MO_PHONG_DU_AN_B1")); await chay();  // shell: vai mới
    const dsB = cho(getDs, "U4: GET danh sách vai mới");
    p.resolve(phanHoi(200, {revision_id: "rv3", revision: 3, lap_lai: false})); await chay();
    assert.strictEqual(dem(c => c.method === "GET"), getTruoc + 1, "U4: ACK của vai cũ phát GET làm mới");
    dsB.resolve(phanHoi(404, {error: "M4_CHUNG_TU_KHONG_THAY", message: "Không thấy đợt"})); await chay();
    assert.strictEqual(theoNhan(box, "Ngày chứng từ bb_nghiem_thu.docx"), null, "U4: nháp/chi tiết của vai cũ còn sau đổi vai");
    // quay lại A1 (shell đổi vai lần nữa) → nạp lại; mở r1
    W.kttM4ChungTu.ve(box, NGU_CANH()); await chay();
    await traDs(3);
    await moRun("r1");
    nutTheoChu(box, "↻").click(); await chay();  // làm mới: GET danh sách + chi tiết cùng lúc
    const gDs = cho(getDs, "U4: GET danh sách làm mới"), gCt = cho(getCt("r1"), "U4: GET chi tiết làm mới");
    const o = nhap("Số chứng từ bb_nghiem_thu.docx", "SUA-SAU-GET");  // người dùng sửa SAU lúc GET bắt đầu
    const tt = trangThaiChu();
    gCt.resolve(phanHoi(500, {error: "LOCAL_STORAGE_ERROR", message: "lỗi cũ"})); gDs.resolve(phanHoi(500, {error: "X", message: "lỗi cũ ds"})); await chay();
    assert.ok(o.isConnected, "U4: lỗi GET về muộn vẽ lại form đang sửa");
    assert.strictEqual(o.value, "SUA-SAU-GET");
    assert.strictEqual(trangThaiChu(), tt, "U4: lỗi GET về muộn đổi trạng thái/báo lỗi");
    nutTheoChu(box, "↻").click(); await chay();
    cho(getDs, "U4: GET danh sách 2").resolve(phanHoi(200, DS(3))); await chay();  // thứ tự xác định: danh sách về trước, rồi chi tiết 403
    cho(getCt("r1"), "U4: GET chi tiết 2").resolve(phanHoi(403, {error: "M4_CHUNG_TU_PHAM_VI", message: "Đã thu hồi quyền"})); await chay();
    assert.ok(!box.textContent.includes("3. Chứng từ đã đọc"), "U4: thu hồi quyền (403) bị che — chi tiết vẫn hiện");
    assert.ok(trangThaiChu().includes("thu hồi"), "U4: 403 không báo");
    console.log("U4 đạt");
  }

  // ---------------------------------------------------------------- U5 run/chi tiết/artifact gắn đúng run
  {
    await moRun("r1");
    assert.ok(nutTheoChu(box, "Báo cáo L3"), "U5: run r1 không có nút tải báo cáo");
    await moRun("r2", {tra: false});
    assert.strictEqual(nutTheoChu(box, "Báo cáo L3"), null, "U5: mở run B còn nút tải artifact của run A");
    await moRun("r1", {tra: false});
    await moRun("r2", {tra: false});
    const ct = conLai(c => c.method === "GET" && c.url.startsWith("/api/m4/chung-tu/r"));
    const c2 = ct.filter(c => c.url.endsWith("/r2")).pop(), c1 = ct.find(c => c.url.endsWith("/r1"));
    for (const c of ct) c.xong = true;
    c2.resolve(phanHoi(200, CHI_TIET("r2"))); await chay();
    c1.resolve(phanHoi(200, CHI_TIET("r1"))); await chay();  // A về muộn
    for (const c of ct) if (c !== c1 && c !== c2) c.resolve(phanHoi(200, CHI_TIET(c.url.endsWith("/r1") ? "r1" : "r2")));
    await chay();
    nutTheoChu(box, "Báo cáo L3").click(); await chay();
    const t2 = cho(c => c.method === "GET" && c.url.includes("/tep/"), "U5: GET tải");
    assert.strictEqual(t2.url, "/api/m4/chung-tu/r2/tep/a-r2", "U5: nút tải ghép run hiện hành với artifact khác run");
    const truoc = soClickTai;
    await moRun("r1");  // đổi run khi bytes chưa về
    t2.resolve(phanHoi(200, null, 10)); await chay();
    assert.strictEqual(soClickTai, truoc, "U5: bytes của run cũ được click sau khi đổi run");
    nutTheoChu(box, "Báo cáo L3").click(); await chay();
    const t1 = cho(c => c.method === "GET" && c.url.includes("/tep/"), "U5: GET tải r1");
    assert.strictEqual(t1.url, "/api/m4/chung-tu/r1/tep/a-r1");
    t1.resolve(phanHoi(200, null, 10)); await chay();
    assert.strictEqual(soClickTai, truoc + 1, "U5: tải run hiện hành không click đúng một lần");
    console.log("U5 đạt");
  }

  // ---------------------------------------------------------------- U6 ma trận theo so sánh typed
  {
    const hang = ma => tim(box, e => e.tagName === "TR" && e.textContent.startsWith(ma));
    const h1 = hang("HM-01"), h2 = hang("HM-02"), h3 = hang("HM-03");
    assert.ok(h1 && h2 && h3, "U6: thiếu dòng ma trận");
    assert.ok(h1.children[4].textContent.includes("chưa so được") && !h1.children[4].textContent.includes("✓"), "U6: KL kỳ này NULL vẫn hiện ✓");
    assert.ok(h1.children[4].textContent.includes("NULL"), "U6: thiếu lý do chưa so được");
    assert.strictEqual(h2.children[2].textContent, "0", "U6: 0 tường minh không hiển thị là 0");
    assert.ok(h2.children[5].textContent.includes("chưa so được") && !h2.children[5].textContent.includes("✓"), "U6: khác ĐVT vẫn hiện ✓ ở Đã giao");
    assert.ok(h2.children[5].textContent.includes("ĐVT"));
    assert.ok(h3.children[4].textContent.includes("✓") && h3.children[5].textContent.includes("✓"), "U6: so được mà không hiện ✓");
    console.log("U6 đạt");
  }

  // ---------------------------------------------------------------- U7 409 REVISION_CU giữ nháp; ghép tay đúng đích + ACK dọn đúng
  {
    nhap("Số chứng từ bb_giao_nhan.xlsx", "07/BBGN");
    nhap("Lý do sửa metadata", "lý do 7");
    nutLuu().click(); await chay();
    cho(post("chung-tu/sua"), "U7: POST sửa").resolve(phanHoi(409, {error: "M4_REVISION_CU", message: "revision đã đổi"})); await chay();
    await traDs(4);
    assert.strictEqual(theoNhan(box, "Số chứng từ bb_giao_nhan.xlsx").value, "07/BBGN", "U7: 409 làm mất nháp");
    assert.strictEqual(nutLuu().disabled, false, "U7: sau 409 nút Lưu tắt dù còn nháp");
    nhap("Hạng mục ghép cho Xi măng PC40", "HM-02", "change");
    nhap("Lý do ghép Xi măng PC40", "xi măng cho bê tông móng");
    nutTheoChu(box, "Ghép").click(); await chay();
    const g = cho(post("chung-tu/ghep"), "U7: POST ghép");
    const gb = JSON.parse(g.opts.body);
    assert.deepStrictEqual([gb.run_id, gb.row_id, gb.boq_id, gb.boq_dong, gb.ma_hm, gb.revision, gb.expected_basis],
      ["r1", "c".repeat(64), "bq1", 3, "HM-02", 4, BASIS(4)], "U7: payload ghép sai đích/căn cứ");
    nutTheoChu(box, "Ghép").click(); await chay();
    assert.strictEqual(conLai(post("chung-tu/ghep")).length, 0, "U7: bấm Ghép lặp khi đang bay phát POST mới");
    g.resolve(phanHoi(200, {map_id: "m1", revision: 1, ma_hm: "HM-02", lap_lai: false})); await chay();
    await traDs(4);
    assert.strictEqual(theoNhan(box, "Lý do ghép Xi măng PC40").value, "", "U7: ACK ghép không dọn nháp ghép đã gửi");
    assert.strictEqual(theoNhan(box, "Số chứng từ bb_giao_nhan.xlsx").value, "07/BBGN", "U7: ACK ghép dọn nhầm nháp sửa metadata");
    console.log("U7 đạt");
  }

  // ---------------------------------------------------------------- trợ giúp FIX02A
  const getDot = id => c => c.method === "GET" && c.url === "/api/m4/chung-tu?dot_id=" + id;
  const doiDot = async id => { nhap("Đợt thanh toán", id, "change"); await chay(); };
  // nút Gửi lại của ĐÚNG một ý định chưa rõ (dòng .m4-hang chứa mô tả đích)
  const nutGuiLai = moTa => { const d = tim(box, e => e._cls && e._cls.has("m4-hang") && e.textContent.includes(moTa)); return d ? nutTheoChu(d, "Gửi lại y nguyên") : null; };
  const nutChay = () => nutTheoChu(box, "Đọc & đối chiếu");
  const thayYDinh = () => box.textContent.includes("Chưa rõ kết quả") || box.textContent.includes("Đang gửi lại y nguyên");
  const bodyCua = c => JSON.parse(c.opts.body);

  // ---------------------------------------------------------------- U8 (U-A) continuation gốc qua mọi await: đổi đợt / đổi PN / tab away–back
  {
    // (a) ACK chạy → GET làm mới đang giữ → đổi đợt → nhả GET cũ
    nutChay().click(); await chay();
    const pc = cho(post("chung-tu/chay"), "U8: POST chạy");
    assert.deepStrictEqual({...bodyCua(pc), khoa: undefined}, {dot_id: "dot-1", revision: 4, expected_basis: BASIS(4), khoa: undefined}, "U8: payload chạy sai");
    pc.resolve(phanHoi(200, {run_id: "r3", lap_lai: false})); await chay();
    const gSau = cho(getDs, "U8: GET làm mới của continuation sau ACK chạy");
    await doiDot("dot-2");
    const g2 = cho(getDot("dot-2"), "U8: GET danh sách đợt 2");
    gSau.resolve(phanHoi(200, DS(5))); await chay();  // GET của đợt 1 về SAU khi đã sang đợt 2
    g2.resolve(phanHoi(200, DS2(0))); await chay();
    assert.strictEqual(dem(getCt("r3")), 0, "U8: continuation cũ mở run r3 (đợt 1) dưới đợt 2");
    assert.ok(!box.textContent.includes("Đang tải kết quả") && !nutTheoChu(box, "Đang xem"), "U8: đợt 2 hiện run/chi tiết của đợt 1");
    await doiDot("dot-1");
    await traDs(5);
    // (b) cùng vai, đổi pháp nhân qua shell khi GET làm mới đang giữ
    nutChay().click(); await chay();
    cho(post("chung-tu/chay"), "U8: POST chạy 2").resolve(phanHoi(200, {run_id: "r4", lap_lai: false})); await chay();
    const gSau2 = cho(getDs, "U8: GET làm mới sau ACK chạy 2");
    W.kttM4ChungTu.ve(box, NGU_CANH("MO_PHONG_DU_AN_A1", {phapNhan: "PN_DEMO_B"})); await chay();
    const gPn = cho(getDs, "U8: GET danh sách dưới pháp nhân B");
    gSau2.resolve(phanHoi(200, DS(5))); await chay();
    gPn.resolve(phanHoi(200, DS(5))); await chay();
    assert.strictEqual(dem(getCt("r4")), 0, "U8: continuation của PN A mở run dưới PN B");
    assert.ok(!box.textContent.includes("Đang tải kết quả") && !nutTheoChu(box, "Đang xem"), "U8: PN B hiện run của PN A");
    W.kttM4ChungTu.ve(box, NGU_CANH()); await chay();
    await traDs(5);
    // (c) tab away/back qua đúng huy + ve của shell khi GET làm mới đang giữ
    nutChay().click(); await chay();
    cho(post("chung-tu/chay"), "U8: POST chạy 3").resolve(phanHoi(200, {run_id: "r5", lap_lai: false})); await chay();
    const gSau3 = cho(getDs, "U8: GET làm mới sau ACK chạy 3");
    W.kttM4ChungTu.huy();
    W.kttM4ChungTu.ve(box, NGU_CANH()); await chay();
    const gLai = cho(getDs, "U8: GET khi quay lại tab");
    gSau3.resolve(phanHoi(200, DS(5))); await chay();
    gLai.resolve(phanHoi(200, DS(5))); await chay();
    assert.strictEqual(dem(getCt("r5")), 0, "U8: continuation trước khi rời tab mở run sau khi quay lại");
    assert.strictEqual(dem(post("chung-tu/chay")), 3, "U8: số POST chạy sai");
    await moRun("r1");
    console.log("U8 đạt");
  }

  // ---------------------------------------------------------------- U9 (R5) UNKNOWN → Gửi lại đang bay → B → A → bodyY
  {
    nhap("Số chứng từ bb_nghiem_thu.docx", "X-R5");
    nhap("Lý do sửa metadata", "r5 x");
    nutLuu().click(); await chay();
    const p1 = cho(post("chung-tu/sua"), "U9: POST sửa bodyX");
    const bX = bodyCua(p1);
    assert.deepStrictEqual([bX.run_id, bX.revision, bX.expected_basis, bX.ly_do, bX.tai_lieu], ["r1", 5, BASIS(5), "r5 x", [{tep_id: "t-nt", so: "X-R5"}]], "U9: payload bodyX sai");
    p1.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(nutGuiLai("sửa metadata"), "U9: UNKNOWN không có Gửi lại");
    nutGuiLai("sửa metadata").click(); await chay();
    const p2 = cho(post("chung-tu/sua"), "U9: Gửi lại 1 (đang bay)");
    assert.deepStrictEqual(bodyCua(p2), bX, "U9: Gửi lại 1 khác body/khóa1");
    const soSua = dem(post("chung-tu/sua"));
    // sang B (đợt 2) khi Gửi lại đang bay: B không thấy ý định của A, B tự chạy được
    await doiDot("dot-2");
    cho(getDot("dot-2"), "U9: GET danh sách đợt 2").resolve(phanHoi(200, DS2(0))); await chay();
    assert.ok(!thayYDinh(), "U9: đợt B hiện ý định chưa rõ của đợt A");
    nutChay().click(); await chay();
    const pb = cho(post("chung-tu/chay"), "U9: B bị khóa bởi ý định của A");
    assert.strictEqual(bodyCua(pb).dot_id, "dot-2", "U9: lệnh của B mang đợt sai");
    pb.resolve(phanHoi(422, {error: "M4_KHONG_HOP_LE", message: "B: lỗi rõ"})); await chay();
    // về A: Gửi lại vẫn đang bay → không có nút Gửi lại thứ hai, có giải thích; bodyY bị chặn
    await doiDot("dot-1");
    await traDs(5);
    await moRun("r1");
    assert.strictEqual(nutGuiLai("sửa metadata"), null, "U9: Gửi lại đang bay mà vẫn cho bấm Gửi lại lần nữa");
    assert.ok(box.textContent.includes("Đang gửi lại y nguyên lệnh chưa rõ kết quả (sửa metadata)"), "U9: về A không giải thích lệnh đang chặn");
    nhap("Số chứng từ bb_nghiem_thu.docx", "Y-R5");
    nhap("Lý do sửa metadata", "r5 y");
    assert.strictEqual(nutLuu().disabled, true, "U9: nút Lưu bật khi ý định chưa rõ đang Gửi lại");
    nutLuu().disabled = false; nutLuu().click(); await chay();
    assert.strictEqual(dem(post("chung-tu/sua")), soSua, "U9: bodyY phát khóa/body mới khi chưa rõ");
    assert.ok(trangThaiChu().includes("chờ kết quả"), "U9: chặn mà không báo");
    // Gửi lại 1 về CHƯA RÕ muộn (fence cũ): giữ NGUYÊN bản ghi gốc, hiện Gửi lại ở đúng A, giữ nháp bodyY
    p2.resolve(phanHoi(503, {error: "TAM_NGUNG", message: "máy chủ bận"})); await chay();
    assert.ok(nutGuiLai("sửa metadata"), "U9: Gửi lại về chưa rõ làm mất đường đối soát");
    assert.strictEqual(theoNhan(box, "Số chứng từ bb_nghiem_thu.docx").value, "Y-R5", "U9: vẽ lại làm mất nháp bodyY");
    nutLuu().disabled = false; nutLuu().click(); await chay();
    assert.strictEqual(dem(post("chung-tu/sua")), soSua, "U9: còn chưa rõ mà Lưu bodyY phát lệnh mới");
    assert.ok(trangThaiChu().includes("Gửi lại"), "U9: không hướng dẫn Gửi lại trước");
    const nutCu = nutGuiLai("sửa metadata");
    nutCu.click(); await chay();
    const p3 = cho(post("chung-tu/sua"), "U9: Gửi lại 2");
    assert.deepStrictEqual(bodyCua(p3), bX, "U9: Gửi lại 2 khác body/khóa1 gốc");
    nutCu.click(); await chay();  // nút cũ còn trong DOM khi Gửi lại 2 đang bay
    assert.strictEqual(dem(post("chung-tu/sua")), soSua + 1, "U9: bấm Gửi lại lặp khi đang bay phát POST thêm");
    p3.resolve(phanHoi(200, {revision_id: "rv6", revision: 6, lap_lai: true})); await chay();
    await traDs(6);
    assert.strictEqual(nutGuiLai("sửa metadata"), null, "U9: ACK rõ không gỡ ý định đã rõ");
    assert.ok(!thayYDinh(), "U9: còn dòng chưa rõ sau ACK");
    assert.strictEqual(theoNhan(box, "Số chứng từ bb_nghiem_thu.docx").value, "Y-R5", "U9: ACK của bodyX dọn mất bodyY");
    assert.strictEqual(theoNhan(box, "Lý do sửa metadata").value, "r5 y", "U9: ACK của bodyX dọn mất lý do bodyY");
    assert.strictEqual(nutLuu().disabled, false, "U9: đã rõ mà bodyY vẫn bị khóa");
    nutLuu().click(); await chay();
    const p4 = cho(post("chung-tu/sua"), "U9: bodyY sau khi rõ");
    const bY = bodyCua(p4);
    assert.deepStrictEqual([bY.run_id, bY.revision, bY.expected_basis, bY.ly_do, bY.tai_lieu], ["r1", 6, BASIS(6), "r5 y", [{tep_id: "t-nt", so: "Y-R5"}]], "U9: payload bodyY sai");
    assert.notStrictEqual(bY.khoa, bX.khoa, "U9: bodyY dùng lại khóa của bodyX");
    p4.resolve(phanHoi(200, {revision_id: "rv7", revision: 7, lap_lai: false})); await chay();
    await traDs(7);
    assert.strictEqual(dem(post("chung-tu/sua")), soSua + 2, "U9: tổng POST sửa sai");
    console.log("U9 đạt");
  }

  // ---------------------------------------------------------------- U10 (R6) A→B→A cùng đích/route/body khi POST1 đang bay
  {
    const moc = calls.length;
    nhap("Số chứng từ bb_nghiem_thu.docx", "R6-1");
    nhap("Lý do sửa metadata", "r6");
    nutLuu().click(); await chay();
    const q1 = cho(post("chung-tu/sua"), "U10: POST1 của A");
    const b1 = bodyCua(q1);
    assert.deepStrictEqual([b1.run_id, b1.revision, b1.tai_lieu], ["r1", 7, [{tep_id: "t-nt", so: "R6-1"}]], "U10: payload POST1 sai");
    const soTruoc = dem(post("chung-tu/sua"));
    // A → vai B (cùng HĐ/đợt/run): B không thấy gì của A; B gửi CÙNG body → được gửi, khóa KHÁC (không gộp khóa giữa vai)
    W.kttM4ChungTu.ve(box, NGU_CANH("MO_PHONG_DU_AN_B1")); await chay();
    cho(getDs, "U10: GET danh sách vai B").resolve(phanHoi(200, DS(7))); await chay();
    assert.ok(!thayYDinh(), "U10: vai B thấy ý định của vai A");
    await moRun("r1");
    nhap("Số chứng từ bb_nghiem_thu.docx", "R6-1");
    nhap("Lý do sửa metadata", "r6");
    assert.strictEqual(nutLuu().disabled, false, "U10: vai B bị khóa bởi lệnh đang bay của vai A");
    nutLuu().click(); await chay();
    const qb = cho(post("chung-tu/sua"), "U10: POST của vai B");
    const bb = bodyCua(qb);
    assert.deepStrictEqual({...bb, khoa: undefined}, {...b1, khoa: undefined}, "U10: body của vai B khác body đã nhập");
    assert.notStrictEqual(bb.khoa, b1.khoa, "U10: vai B tái dùng khóa của vai A vì cùng body");
    qb.resolve(phanHoi(422, {error: "M4_KHONG_HOP_LE", message: "B: lỗi rõ"})); await chay();
    // → về A (ABA đủ ngữ cảnh): cùng body và body R2 đều bị chặn khi POST1 còn bay
    W.kttM4ChungTu.ve(box, NGU_CANH()); await chay();
    await traDs(7);
    await moRun("r1");
    nhap("Số chứng từ bb_nghiem_thu.docx", "R6-1");
    nhap("Lý do sửa metadata", "r6");
    assert.strictEqual(nutLuu().disabled, true, "U10: ABA làm mất khóa đích đang bay");
    nutLuu().disabled = false; nutLuu().click(); await chay();
    assert.strictEqual(dem(post("chung-tu/sua")), soTruoc + 1, "U10: ABA phát POST2 (khóa thứ hai) cho cùng đích/body");
    assert.ok(trangThaiChu().includes("chờ kết quả"), "U10: chặn mà không báo");
    nhap("Số chứng từ bb_nghiem_thu.docx", "R6-2");
    nutLuu().disabled = false; nutLuu().click(); await chay();
    assert.strictEqual(dem(post("chung-tu/sua")), soTruoc + 1, "U10: body R2 cho cùng đích phát khi POST1 còn bay");
    // đích khác (ghép dòng) không bị khóa
    nhap("Hạng mục ghép cho Xi măng PC40", "HM-02", "change");
    nhap("Lý do ghép Xi măng PC40", "g r6");
    nutTheoChu(box, "Ghép").click(); await chay();
    const g1 = cho(post("chung-tu/ghep"), "U10: ghép bị khóa bởi lệnh sửa");
    const bg = bodyCua(g1);
    // POST1 (trước ABA) về CHƯA RÕ → bản ghi khóa1 giữ; đang ở đúng A → hiện Gửi lại; nháp R2 giữ
    q1.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(nutGuiLai("sửa metadata"), "U10: UNKNOWN của POST1 sau ABA mất đường đối soát");
    assert.strictEqual(theoNhan(box, "Số chứng từ bb_nghiem_thu.docx").value, "R6-2", "U10: vẽ lại làm mất nháp R2");
    g1.resolve(phanHoi(502, {error: "BAD_GATEWAY", message: "cổng lỗi"})); await chay();
    assert.ok(nutGuiLai("sửa metadata") && nutGuiLai("ghép Xi măng PC40"), "U10: hai ý định chưa rõ khác đích bị gộp/ghi đè");
    nutGuiLai("ghép Xi măng PC40").click(); await chay();
    const g2 = cho(post("chung-tu/ghep"), "U10: Gửi lại ghép");
    assert.deepStrictEqual(bodyCua(g2), bg, "U10: Gửi lại ghép khác body/khóa");
    nutGuiLai("sửa metadata").click(); await chay();
    const q2 = cho(post("chung-tu/sua"), "U10: Gửi lại sửa");
    assert.deepStrictEqual(bodyCua(q2), b1, "U10: Gửi lại sau ABA khác body/khóa1");
    g2.resolve(phanHoi(200, {map_id: "m6", revision: 8, ma_hm: "HM-02", lap_lai: false})); await chay();
    await traDs(8);
    assert.strictEqual(nutGuiLai("ghép Xi măng PC40"), null, "U10: ACK ghép không gỡ ý định ghép");
    assert.ok(box.textContent.includes("Đang gửi lại y nguyên lệnh chưa rõ kết quả (sửa metadata)"), "U10: ACK ghép gỡ nhầm ý định sửa đang Gửi lại");
    q2.resolve(phanHoi(200, JSON_DUT)); await chay();  // 200 nhưng JSON đứt: vẫn chưa rõ, giữ bản ghi
    assert.ok(nutGuiLai("sửa metadata"), "U10: JSON đứt sau Gửi lại làm mất bản ghi");
    nutGuiLai("sửa metadata").click(); await chay();
    const q3 = cho(post("chung-tu/sua"), "U10: Gửi lại sửa 2");
    assert.deepStrictEqual(bodyCua(q3), b1, "U10: Gửi lại 2 khác body/khóa1");
    q3.resolve(phanHoi(200, {revision_id: "rv9", revision: 9, lap_lai: true})); await chay();
    await traDs(9);
    const cuaA = calls.slice(moc).filter(c => post("chung-tu/sua")(c) && c !== qb);
    assert.deepStrictEqual(cuaA.map(bodyCua), [b1, b1, b1], "U10: đích sửa của A không chỉ một khóa/body (POST1 + 2 lần Gửi lại)");
    assert.ok(!thayYDinh(), "U10: còn dòng chưa rõ sau khi rõ");
    // đã rõ → body R2 hợp lệ không bị khóa, khóa mới
    assert.strictEqual(theoNhan(box, "Số chứng từ bb_nghiem_thu.docx").value, "R6-2", "U10: ACK body1 dọn mất nháp R2");
    nhap("Lý do sửa metadata", "r6 b");
    assert.strictEqual(nutLuu().disabled, false, "U10: R2 bị khóa sau khi POST1 đã rõ");
    nutLuu().click(); await chay();
    const q4 = cho(post("chung-tu/sua"), "U10: body R2");
    const b4 = bodyCua(q4);
    assert.deepStrictEqual([b4.revision, b4.ly_do, b4.tai_lieu], [9, "r6 b", [{tep_id: "t-nt", so: "R6-2"}]], "U10: payload R2 sai");
    assert.notStrictEqual(b4.khoa, b1.khoa, "U10: R2 dùng lại khóa1");
    q4.resolve(phanHoi(200, {revision_id: "rv10", revision: 10, lap_lai: false})); await chay();
    await traDs(10);
    // thứ tự ngược: UNKNOWN về khi đang ở đợt B → B không thấy; về A còn đúng khóa, cùng body bị chặn tới khi Gửi lại
    nhap("Số chứng từ bb_nghiem_thu.docx", "R6-3");
    nhap("Lý do sửa metadata", "r6 c");
    nutLuu().click(); await chay();
    const q5 = cho(post("chung-tu/sua"), "U10: POST5");
    const b5 = bodyCua(q5);
    await doiDot("dot-2");
    cho(getDot("dot-2"), "U10: GET đợt 2").resolve(phanHoi(200, DS2(0))); await chay();
    q5.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(!thayYDinh(), "U10: UNKNOWN của đợt A hiện dưới đợt B");
    await doiDot("dot-1");
    await traDs(10);
    await moRun("r1");
    assert.ok(nutGuiLai("sửa metadata"), "U10: UNKNOWN về khi ở B làm mất Gửi lại ở A");
    nhap("Số chứng từ bb_nghiem_thu.docx", "R6-3");
    nhap("Lý do sửa metadata", "r6 c");
    const soQ5 = dem(post("chung-tu/sua"));
    nutLuu().disabled = false; nutLuu().click(); await chay();
    assert.strictEqual(dem(post("chung-tu/sua")), soQ5, "U10: cùng body sau UNKNOWN phát khóa mới");
    assert.ok(trangThaiChu().includes("Gửi lại"), "U10: không hướng dẫn Gửi lại");
    nutGuiLai("sửa metadata").click(); await chay();
    const q6 = cho(post("chung-tu/sua"), "U10: Gửi lại POST5");
    assert.deepStrictEqual(bodyCua(q6), b5, "U10: Gửi lại POST5 khác body/khóa");
    q6.resolve(phanHoi(200, {revision_id: "rv11", revision: 11, lap_lai: true})); await chay();
    await traDs(11);
    assert.ok(!thayYDinh(), "U10: còn dòng chưa rõ sau ACK POST5");
    console.log("U10 đạt");
  }

  // ---------------------------------------------------------------- U11 (U-D) dấu lượng theo dung sai nguồn
  {
    const SO = them => ({trang_thai: "SO_DUOC", ly_do: null, ...them});
    const DONG = (ma, c1, c3, them = {}) => ({khoa: ma, ma_hm: ma, ten: "Biên " + ma, dvt: "m3", kl_kn: 1, kl_lk: 1, nt: null, nt_docs: ["bb_nghiem_thu.docx"],
      gn: null, gn_docs: ["bb_giao_nhan.xlsx"], co: [], cq: [], pl: [], ld: [], so_sanh: {C01: c1, C03: c3}, ...them});
    const ct = CHI_TIET("r2");
    ct.ket_qua.ket_qua.ma_tran = [
      DONG("TA-DUOI", SO({kl_kn: 10.0005, nt: 10}), SO({kl_lk: 10.0005, gn: 10})),          // chênh 0,0005 ≤ 0,001 (ngưỡng tuyệt đối) → ✓
      DONG("TA-TREN", SO({kl_kn: 10.002, nt: 10}), SO({kl_lk: 10.002, gn: 10})),            // chênh 0,002 > 0,001 → ✗
      DONG("TR-DUOI", SO({kl_kn: 1000000.5, nt: 1000000}), SO({kl_lk: 1000000.5, gn: 1000000})),  // ngưỡng tương đối 1 → chênh 0,5 → ✓
      DONG("TR-TREN", SO({kl_kn: 1000001.5, nt: 1000000}), SO({kl_lk: 1000001.5, gn: 1000000})),  // chênh 1,5 > 1 → ✗
      DONG("TOP", SO({kl_kn: 10.0005, nt: 10}), SO({kl_lk: 10.0005, gn: 10}), {kl_kn: 999, kl_lk: 999, nt: 1, gn: 1}),  // toán hạng typed thắng trường dòng
      DONG("TNULL", SS("CHUA_SO_DUOC", "KL kỳ này NULL"), SS("CHUA_SO_DUOC", "1 dòng khác ĐVT"), {kl_kn: null}),
      DONG("TZERO", SO({kl_kn: 0, nt: null}), SS("KHONG_AP_DUNG"), {kl_kn: 0, gn_docs: []}),
      DONG("TKN", SO({kl_kn: 5, nt: null}), SS("KHONG_AP_DUNG"), {gn_docs: []})];
    await moRun("r2", {tra: false});
    cho(getCt("r2"), "U11: GET chi tiết r2").resolve(phanHoi(200, ct)); await chay();
    const hang = ma => { const h = tim(box, e => e.tagName === "TR" && e.textContent.startsWith(ma + " ")); assert.ok(h, "U11: thiếu dòng " + ma); return h; };
    const o = (ma, i) => hang(ma).children[i].textContent;
    const dat = s => s.includes("✓") && !s.includes("✗"), thieu = s => s.includes("✗") && !s.includes("✓"), khongDau = s => !s.includes("✓") && !s.includes("✗");
    for (const [ma, nt, gn] of [["TA-DUOI", dat, dat], ["TA-TREN", thieu, thieu], ["TR-DUOI", dat, dat], ["TR-TREN", thieu, thieu], ["TOP", dat, dat]]) {
      assert.ok(nt(o(ma, 4)), `U11: ${ma} NT/KL kỳ này sai dấu theo ngưỡng nguồn: ${o(ma, 4)}`);
      assert.ok(gn(o(ma, 5)), `U11: ${ma} GN/KL lũy kế sai dấu theo ngưỡng nguồn: ${o(ma, 5)}`);
    }
    assert.ok(khongDau(o("TNULL", 4)) && o("TNULL", 4).includes("chưa so được") && o("TNULL", 4).includes("NULL"), "U11: KL NULL có dấu");
    assert.ok(khongDau(o("TNULL", 5)) && o("TNULL", 5).includes("ĐVT"), "U11: khác ĐVT có dấu");
    assert.strictEqual(o("TZERO", 2), "0", "U11: 0 tường minh không hiển thị 0");
    assert.ok(dat(o("TZERO", 4)), "U11: KL kỳ này 0 tường minh (so được) không ✓");
    assert.ok(khongDau(o("TZERO", 5)) && khongDau(o("TKN", 5)), "U11: KHONG_AP_DUNG có dấu");
    assert.ok(thieu(o("TKN", 4)), "U11: KL > 0 không có trong BB nghiệm thu không ✗");
    console.log("U11 đạt");
  }

  await chay();
  if (loiNgoai.length) throw loiNgoai[0];
  console.log("m4_02b_async: mọi ca đạt");
}

main().then(() => process.exit(0), e => { console.error(e); process.exit(1); });
