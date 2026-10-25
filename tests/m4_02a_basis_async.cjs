"use strict";
// M4-02A — "Căn cứ lần chạy" (Xem BOQ căn cứ / Xem phụ lục căn cứ) trên MÃ THẬT app.js (cổng kttChung thật) + m4/giao_dien/review.js (tab Review),
// cùng khung harness của tests/m4_02b_async.cjs: DOM giả có quan hệ cha–con/kết nối thật, fetch/luồng bytes/crypto.subtle do ca điều khiển (chờ, đảo thứ
// tự, lỗi). Màn được mount như shell m4.js (window.kttM4Review.ve(vùng đã gắn, ngữ cảnh {hdId, soHd, dots, dotId, nguoi})); vào tính năng bằng đúng
// đường người dùng: Mở lần chạy ở "Kết quả đã lưu" → bấm vị trí phát hiện Lớp 2 → nút "Xem BOQ căn cứ"/"Xem phụ lục căn cứ".
// CODE_ONLY: WRITTEN_NOT_RUN — coder viết, CHƯA CHẠY. Root chạy: `node tests/m4_02a_basis_async.cjs` (Node ≥ 18). Không ghi/xóa tệp, không mạng, không
// tiến trình con, không hẹn giờ dài (setTimeout ≥ 1 s của mã thật chỉ được ghi lại, không chạy). Mỗi ca dựng MÔI TRƯỜNG MỚI (app.js + review.js nạp lại).
// Báo cáo tách: setup_errors (harness không tới được route/lối vào thật — KHÔNG phải đạt) và semantic_violations (vi phạm hành vi). Mã thoát qua
// process.exitCode: 0 chỉ khi đủ mọi ca, 0 setup_error, 0 vi phạm, 0 unhandledRejection. BASIS là chuỗi JSON tổng hợp viết tay trong tệp này; giá trị
// kỳ vọng viết tay độc lập; SHA-256 kỳ vọng tính bằng node:crypto trên chính bytes literal (không dùng mã sản phẩm).
// Ca:
//  C01 hợp lệ · BOQ: đúng MỘT GET /api/m4/review/{run}/tep/{BASIS} (token/no-store/same-origin, không body), không API HĐ/PL hiện hành, không POST;
//      panel "Căn cứ lần chạy" có run/SHA/HĐ lưu/revision/ngày NT LƯU (khác ngày đợt hiện tại)/sheet/dòng vật lý; "0" ≠ NULL; số giữ nguyên chuỗi lưu;
//      chuỗi HTML độc hại chỉ là chữ; không nhãn hiện hành/BOQ hiệu lực; tải ⭳ Căn cứ JSON vẫn hoạt động.
//  C02 PL: đổi góc xem không GET lại; trạng thái/ngày PL đúng chuỗi lưu; danh sách áp dụng lấy từ kết quả đã lưu.
//  C03–C07 đăng ký sai (không BASIS / 2 BASIS / SHA đăng ký ≠ basis của run / mã không UUID / quá giới hạn) → chưa hiển thị, 0 GET tệp.
//  C08–C10 headers/độ dài: Content-Type sai, Content-Length sai (0 lần đọc bytes), bytes ngắn hơn / dài hơn (hủy luồng).
//  C11–C16 checksum sai, JSON hỏng, phiên bản lạ, lệch danh tính (tệp / HĐ của đợt), sai kiểu, JSON chung (không phải căn cứ).
//  C17 không có crypto.subtle → chưa hiển thị, nút tải vẫn còn.
//  C18 căn cứ cũ thiếu mục (BOQ/PL/lịch sử) → CHƯA ĐỦ, không thành 0; C18b bảng thiếu dòng vs 0 dòng; 0 phụ lục tường minh.
//  C19/C20 403/401 HIỆN HÀNH → gỡ kết quả/bằng chứng/căn cứ; C21 403 cũ sau đổi phát hiện → không gỡ.
//  C22 headers chậm + đóng/mở lại CÙNG phát hiện (A→B→A): 403 cũ không chạm lần đọc mới; lần mới công bố.
//  C23 bytes chậm + đổi lần chạy → hủy luồng, không công bố; lần chạy B đọc đúng artifact của B.
//  C24 crypto chậm + đổi vai qua shell; C25 crypto chậm + đổi lớp; C26 rời tab (tat) rồi quay lại; C27 bytes chậm + đổi HĐ;
//  C28 crypto chậm + barrier đổi vai thật kttChung.doiVaiTuanTu; C29 lần chạy A→B→A khi headers chậm; C30 mất kết nối → bấm lại → đạt.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const nodeCrypto = require("crypto");

const ROOT = path.resolve(__dirname, "..");
const setupErrors = [], violations = [], ketQua = [], loiNgoai = [];
let APP = null, RV = null, ID_TINH = new Set();
try {
  APP = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/app.js"), "utf8");
  RV = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/m4/giao_dien/review.js"), "utf8");
  ID_TINH = new Set([...fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/index.html"), "utf8").matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
} catch (e) { setupErrors.push("đọc mã nguồn: " + e.message); }
process.on("unhandledRejection", e => { loiNgoai.push(e); });

class LoiSetup extends Error {}
const setup = (dk, msg) => { if (!dk) throw new LoiSetup(msg); };
let viPhamCa = [];
const kiem = (dk, msg) => { if (!dk) viPhamCa.push(msg); };

// ------------------------------------------------------------------ DOM giả có kết nối thật (khung m4_02b_async.cjs)
function moiTruong() {
  const reg = new Map(), dongId = new Set();
  let taoTinh = false, soClick = 0;
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
    click() { if (this.tagName === "A") soClick += 1; if (this.disabled) return []; return this.dispatch("click"); }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    removeAttribute(k) { delete this.attrs[k]; }
    getAttribute(k) { return this.attrs[k] ?? null; }
    querySelector(s) {
      const lop = s.startsWith(".") ? s.slice(1) : null;
      const tim_ = e => { for (const c of e.children) { if (lop && c._cls && c._cls.has(lop)) return c; const r = tim_(c); if (r) return r; } return null; };
      return lop ? tim_(this) : null;
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
  const fetch = (url, opts) => new Promise((resolve, reject) => calls.push({url: String(url), opts: opts || {}, resolve, reject, method: (opts && opts.method) || "GET", xong: false}));
  const bam = {cham: false, cho: [], soGoi: 0};
  const digest = (alg, data) => {  // SHA-256 thật của node:crypto trên ĐÚNG bytes mã thật đưa vào; có thể giữ chờ
    bam.soGoi += 1;
    if (alg !== "SHA-256") return Promise.reject(new Error("thuật toán lạ: " + alg));
    const h = nodeCrypto.createHash("sha256").update(Buffer.from(data.buffer, data.byteOffset, data.byteLength)).digest();
    const ab = h.buffer.slice(h.byteOffset, h.byteOffset + h.byteLength);
    if (!bam.cham) return Promise.resolve(ab);
    return new Promise(r => bam.cho.push(() => r(ab)));
  };
  let soUuid = 0;
  const hen = [];
  const ctx = {
    document, Node: El, console, clearTimeout, Promise, Map, Set, JSON, Math, Date, Number, String, Object, Array, Error, TypeError, SyntaxError,
    setTimeout: (fn, ms, ...a) => ((ms || 0) >= 1000 ? (hen.push(fn), 0) : setTimeout(fn, ms, ...a)),
    encodeURIComponent, decodeURIComponent, URLSearchParams, location: {hash: "#m4"}, TextDecoder,
    crypto: {randomUUID: () => "uuid-" + (++soUuid), subtle: {digest}},
    URL: {createObjectURL: () => "blob:x", revokeObjectURL() {}}, fetch, navigator: {}, Intl,
  };
  ctx.window = ctx;
  ctx.addEventListener = () => {};
  vm.createContext(ctx);
  return {ctx, document, calls, body, bam, soClick: () => soClick};
}

const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 12) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (!root) return null; if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
function timHet(root, pred, out = []) { if (!root) return out; if (pred(root)) out.push(root); for (const c of root.children || []) timHet(c, pred, out); return out; }
const nutTheoChu = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));
const theoNhan = (root, s) => tim(root, e => e.attrs && e.attrs["aria-label"] === s);

// ------------------------------------------------------------------ dữ liệu tổng hợp (literal, không lấy từ sản phẩm)
const HD = "11111111-1111-4111-8111-111111111111", HD2 = "11111111-1111-4111-8111-222222222222";
const DOT = "22222222-2222-4222-8222-222222222222", TEP = "33333333-3333-4333-8333-333333333333";
const DA = "44444444-4444-4444-8444-444444444444", PN = "55555555-5555-4555-8555-555555555555";
const RUN_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", RUN_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const ART = {[RUN_A]: "a0000000-0000-4000-8000-00000000000a", [RUN_B]: "b0000000-0000-4000-8000-00000000000b"};
const ART_KHAC = {[RUN_A]: ["a0000000-0000-4000-8000-0000000000a1", "a0000000-0000-4000-8000-0000000000a2"], [RUN_B]: ["b0000000-0000-4000-8000-0000000000b1", "b0000000-0000-4000-8000-0000000000b2"]};
const PL1 = "66666666-6666-4666-8666-666666666661", PL2 = "66666666-6666-4666-8666-666666666662";
const BQ1 = "77777777-7777-4777-8777-777777777771", BQ2 = "77777777-7777-4777-8777-777777777772";
const RAW = "3".repeat(64), LUC = {[RUN_A]: "2026-03-02T10:00:00", [RUN_B]: "2026-03-05T09:30:00"};
const XSS = "Đào đất <img src=x onerror=alert(1)>";
// BASIS lưu (định dạng m4.review.basis/1, khóa sắp xếp như canonical_json) — viết tay
const BASIS_HOP_LE = '{"boq":[' +
  `{"bo_doc":null,"cot":{"dvt":"D","kl":"E","ten":"C"},"dong":[` +
  `{"don_gia":"1250000.50","dong":12,"dvt":"m3","kl":"0","ma_hm":"HM-01","ma_rieng":null,"nhom":"Phần móng","stt":"1","ten":${JSON.stringify(XSS)},"thanh_tien":"0.00","thao_tac":null},` +
  `{"don_gia":"980000","dong":13,"dvt":"m3","kl":null,"ma_hm":"HM-02","ma_rieng":"BT-M","nhom":"Phần móng","stt":"2","ten":"Bê tông móng","thanh_tien":null,"thao_tac":null}],` +
  `"hang_tieu_de":9,"id":"${BQ1}","lan":1,"phu_luc_id":null,"raw_sha256":"${"7".repeat(64)}","sheet":"BOQ-HD","so_dong":2,"tep_id":null,"trang_thai":"XONG"},` +
  `{"bo_doc":null,"cot":{"kl":"F"},"dong":[` +
  `{"don_gia":"1100000","dong":7,"dvt":"m3","kl":"15.500","ma_hm":"HM-02","ma_rieng":null,"nhom":"Phần móng","stt":"2","ten":"Bê tông móng (PL01)","thanh_tien":"17050000","thao_tac":"SUA"}],` +
  `"hang_tieu_de":5,"id":"${BQ2}","lan":2,"phu_luc_id":"${PL1}","raw_sha256":"${"8".repeat(64)}","sheet":"PL01-BOQ","so_dong":1,"tep_id":null,"trang_thai":"XONG"}],` +
  `"che_do":"L1_L2",` +
  `"dot":{"du_an_id":"${DA}","hop_dong_id":"${HD}","id":"${DOT}","ngay_nghiem_thu":"2026-03-01","nop_digest":null,"nop_id":null,"nop_revision_ho_so":null,"revision":2,"so_dot":1,"trang_thai":"DA_NOP"},` +
  `"dot_hd":[{"id":"${DOT}","ngay_nghiem_thu":"2026-03-01","so_dot":1,"trang_thai":"DA_NOP"}],"dot_tep":[{"muc":"A01","tep_id":"${TEP}"}],"du_an_id":"${DA}","engine_sha256":"${"9".repeat(64)}",` +
  `"hop_dong":{"id":"${HD}","rev_tham_so":4,"revision":3,"so_hop_dong":"01/2025/HĐ-XL","ten":"Thi công bể","tep_hop_dong_id":null,"tep_hop_dong_sha256":null,"trang_thai_pl":"CO_PL"},` +
  `"manual_map":[],"o_dich":null,"phap_nhan_id":"${PN}",` +
  `"phu_luc":[{"doi_boq":true,"id":"${PL1}","ngay_hieu_luc":"2026-02-01","ngay_ky":"2026-01-20","so_pl":"PL01","tep_id":null,"trang_thai":"DA_KY"},` +
  `{"doi_boq":false,"id":"${PL2}","ngay_hieu_luc":"2026-06-01","ngay_ky":null,"so_pl":"PL02","tep_id":null,"trang_thai":"DU_THAO"}],` +
  `"phien_ban":"m4.review.basis/1","tham_so":[],` +
  `"tep":{"byte_length":100,"du_an_id":"${DA}","id":"${TEP}","media_type":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","phap_nhan_id":"${PN}","raw_sha256":"${RAW}","ten_goc":"hstt-dot1.xlsx","vai_tro_tai_lieu":"HO_SO_DOT"},` +
  `"trich_xuat":null,"truoc_da_duyet":{"ly_do":"Chưa có lịch sử đợt trước đã được reviewer duyệt","trang_thai":"CHUA_CO_NGUON"},"xac_nhan":null}`;
const B = s => Buffer.from(s, "utf8");
const sha = b => nodeCrypto.createHash("sha256").update(b).digest("hex");
const BYTES_HOP_LE = B(BASIS_HOP_LE);
const bienThe = fn => { const o = JSON.parse(BASIS_HOP_LE); fn(o); return B(JSON.stringify(o)); };

const DOTS = [{id: DOT, so_dot: 1, ngay_nghiem_thu: "2026-04-15", trang_thai: "DA_NOP"}];  // ngày NT HIỆN TẠI của đợt đã sửa sau lần chạy
const NGU_CANH = (them = {}) => ({hdId: HD, soHd: "01/2025/HĐ-XL (hiện tại)", dots: DOTS, dotId: DOT, nguoi: "NV_A", ...them});
const RUN_HANG = id => ({id, hop_dong_id: HD, dot_id: DOT, tep_id: TEP, ten_goc: "hstt-dot1.xlsx", raw_sha256: RAW, che_do: "L1_L2", o_dich: null, trang_thai: "PARTIAL",
  basis_sha256: sha(BYTES_HOP_LE), parent_run_id: null, quyen: "SOAN", tao_boi: "NV_A", tao_luc: LUC[id], xong_luc: LUC[id], ly_do: null, cong_bo: true, coverage: {K1: {trang_thai: "CHECKED"}}});
const DS = () => ({runs: [RUN_HANG(RUN_A), RUN_HANG(RUN_B)], tep: [{tep_id: TEP, muc: "A01", ten_goc: "hstt-dot1.xlsx", raw_sha256: RAW, byte_length: 100}], manual_map: [],
  co_so: {san_sang: true, basis_sha256: "c".repeat(64), quyen: "SOAN", che_do: "L1_L2", o_dich: null, du_an_id: DA, phu_thuoc: {}, so_ghep_tay: 0, ngay_nghiem_thu: "2026-04-15", engine: "E"},
  nguong_nguon: null});
const F = () => [
  {id: "B3-1", layer: 2, level: "Cao", title: "Đơn giá lệch BOQ", item: "Bê tông móng", sheet: "BangKL", cell: "F12", amount: 120000, source: "BOQ HĐ + PL", reference: "HM-02",
    actual: "1250000", expected: "1100000", conclusion: "Xem lại đơn giá"},
  {id: "B4-1", layer: 2, level: "Trung bình", title: "KL vượt", item: "Đào đất", sheet: "BangKL", cell: "G20", amount: null, source: "BOQ", actual: "50", expected: "40", conclusion: "x"},
  {id: "K3-1", layer: 1, level: "Thấp", title: "Số gõ tay", sheet: "Tong", cell: "C5", source: "Excel", conclusion: "y"}];
const RES = () => ({trang_thai: "PARTIAL", tep: "hstt-dot1.xlsx", engine: "E", so_phat_hien: 3, dem: {Cao: 1, "Trung bình": 1, "Thấp": 1}, anh_huong_uoc_tinh: 120000,
  coverage: {K1: {trang_thai: "CHECKED", ly_do: ""}}, phat_hien: F(),
  lop1: {de_nghi: 1000, dich: "Tong!C9", nguon_dich: "TU_DONG", so_sheet: 3, bang_k: [], cay: []},
  lop2: {chay: true, bang_lop2: [], doi_chieu_hm: [], ngay_nghiem_thu: "2026-03-01", phu_luc_ap_dung: [{so_pl: "PL01", ngay_hieu_luc: "2026-02-01"}],
    phu_luc_chua_ap_dung: [{so_pl: "PL02", ngay_hieu_luc: "2026-06-01"}], loai_gia: "Đơn giá cố định", dot: 1, dot_truoc: null, gt_hieu_luc: "5000000", de_nghi: 1000, o_de_nghi: "Tong!C9"}});
const DK = (id, loai, bytes, them = {}) => ({id, loai, ten: `review-${loai.toLowerCase()}.${loai === "BASIS" ? "json" : "bin"}`, raw_sha256: sha(bytes), byte_length: bytes.length, tao_luc: "2026-03-02T10:01:00", ...them});
function CHI_TIET(id, {basis = BYTES_HOP_LE, artifact, runThem = {}} = {}) {
  const art = artifact || [DK(ART_KHAC[id][0], "REPORT_L2", B("xlsx-gia")), DK(ART[id], "BASIS", basis), DK(ART_KHAC[id][1], "LOG", B("log"))];
  return {run: {id, phap_nhan_id: PN, du_an_id: DA, hop_dong_id: HD, dot_id: DOT, tep_id: TEP, ten_goc: "hstt-dot1.xlsx", raw_sha256: RAW, che_do: "L1_L2", o_dich: null,
    basis_sha256: sha(basis), engine: "E", engine_sha256: "9".repeat(64), hanh_dong: "REVIEW_CHAY", quyen: "SOAN", trang_thai: "PARTIAL", parent_run_id: null, ly_do: null,
    tao_boi: "NV_A", tao_luc: LUC[id], xong_luc: LUC[id], ...runThem},
  ket_qua: {ket_qua: RES(), ket_qua_sha256: "d".repeat(64), coverage: {}, cong_bo: true}, artifact: art, con: [], manual_map: []};
}

function phanHoi(status, data) {
  return {ok: status >= 200 && status < 300, status, headers: {get: k => (String(k).toLowerCase() === "content-type" ? "application/json" : null)},
    json: async () => data, blob: async () => new Blob([B(JSON.stringify(data))])};
}
// phản hồi route tải tệp: headers + luồng bytes theo khúc (có thể giữ chờ từng khúc) + đếm số lần đọc/hủy
function phanHoiTep(bytes, {ct = "application/json", cl = "auto", cham = false, cat = 3} = {}) {
  const H = {"content-type": ct};
  if (cl === "auto") H["content-length"] = String(bytes.length); else if (cl !== null) H["content-length"] = String(cl);
  const n = bytes.length, buoc = Math.max(1, Math.ceil(n / cat)), khuc = [];
  for (let i = 0; i < n; i += buoc) khuc.push(new Uint8Array(bytes.subarray(i, i + buoc)));
  let i = 0, soDoc = 0, huy = false;
  const cho = [];
  const reader = {
    read() {
      soDoc += 1;
      const tra = () => (i < khuc.length ? {done: false, value: khuc[i++]} : {done: true, value: undefined});
      if (!cham) return Promise.resolve(tra());
      return new Promise(r => cho.push(() => r(tra())));
    },
    cancel() { huy = true; return Promise.resolve(); },
  };
  const res = {ok: true, status: 200, headers: {get: k => H[String(k).toLowerCase()] ?? null}, body: {getReader: () => reader},
    json: async () => { throw new SyntaxError("không dùng json() cho tệp"); }, blob: async () => new Blob([bytes])};
  return {res, nha: () => { const f = cho.shift(); if (!f) throw new Error("không có khúc bytes đang chờ"); f(); }, soDoc: () => soDoc, daHuy: () => huy, conCho: () => cho.length};
}

// ------------------------------------------------------------------ dựng môi trường + đi đúng lối vào thật đến bằng chứng L2
async function batDau({ct = {}, baoQua = false} = {}) {
  setup(APP && RV, "không đọc được app.js/review.js");
  const env = moiTruong();
  const {ctx, calls, body, document} = env;
  try { vm.runInContext(APP, ctx, {filename: "app.js"}); } catch (e) { throw new LoiSetup("chạy app.js: " + e.message); }
  for (const c of calls) { c.xong = true; c.resolve(phanHoi(404, {error: "NOT_FOUND", message: "ngoài ca"})); }
  await chay();
  try { vm.runInContext(RV, ctx, {filename: "review.js"}); } catch (e) { throw new LoiSetup("chạy review.js: " + e.message); }
  const W = ctx.window;
  setup(W.kttM4Review && typeof W.kttM4Review.ve === "function" && W.kttChung, "review.js/app.js không công bố window.kttM4Review/kttChung");
  const box = document.createElement("div");
  body.append(box);
  const moc = calls.length;
  const conCho = pred => calls.filter(c => !c.xong && pred(c));
  const laySetup = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); setup(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const lay = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); if (!c) throw new Error("không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const laDs = c => c.method === "GET" && c.url.startsWith("/api/m4/review?");
  const laCt = id => c => c.method === "GET" && c.url === "/api/m4/review/" + id;
  const laTep = c => c.url.includes("/tep/");
  const h = {
    env, W, box, calls, moc, conCho, lay, laySetup, laDs, laCt, laTep,
    async traDs(batBuoc = true) {
      const ds = conCho(laDs);
      if (batBuoc) setup(ds.length, "không thấy GET danh sách Review");
      for (const c of ds) { c.xong = true; c.resolve(phanHoi(200, DS())); }
      await chay();
    },
    nutMo(id) { const tr = tim(box, e => e.tagName === "TR" && e.textContent.includes(LUC[id].replace("T", " ")) && !!nutTheoChu(e, "Mở")); return tr && nutTheoChu(tr, "Mở"); },
    async moRun(id, opt, {tra = true} = {}) {
      const n = h.nutMo(id);
      setup(n, "không thấy nút Mở của lần chạy " + id);
      n.click(); await chay();
      if (!tra) return null;
      laySetup(laCt(id), "GET chi tiết " + id).resolve(phanHoi(200, CHI_TIET(id, opt))); await chay();
      await h.traDs(false);
      return null;
    },
    async moBangChung(nhan) {
      const n = nutTheoChu(box, nhan);
      setup(n, "không thấy nút vị trí phát hiện " + nhan);
      n.click(); await chay();
      setup(h.bangChung(), "không mở được panel bằng chứng " + nhan);
    },
    bangChung: () => theoNhan(box, "Bằng chứng phát hiện"),
    panel: () => theoNhan(box, "Căn cứ lần chạy"),
    nutBoq: () => nutTheoChu(box, "Xem BOQ căn cứ"),
    nutPl: () => nutTheoChu(box, "Xem phụ lục căn cứ"),
    async bam(nut, moTa) { if (!nut) throw new Error("không có nút: " + moTa); nut.click(); await chay(); },
    tep: () => calls.filter(laTep),
    tatCaSau: () => calls.slice(moc),
    trangThai: () => (box.querySelector(".m4-rv-status") || {textContent: ""}).textContent,
  };
  W.kttM4Review.ve(box, NGU_CANH()); await chay();
  await h.traDs();
  await h.moRun(RUN_A, ct[RUN_A]);
  if (!baoQua) await h.moBangChung("BangKL!F12");
  return h;
}
const urlTep = id => `/api/m4/review/${id}/tep/${ART[id]}`;
// lỗi "chưa hiển thị được" phải là chữ; không có dữ liệu căn cứ được hiển thị
function kiemChuaHien(h, chu, moTa, coNutTai = true) {
  const p = h.panel();
  kiem(p, moTa + ": không có panel Căn cứ lần chạy báo trạng thái");
  const t = p ? p.textContent : "";
  kiem(t.includes("Chưa hiển thị được căn cứ lần chạy"), moTa + ": không báo chưa hiển thị được — " + t.slice(0, 200));
  if (chu) kiem(t.includes(chu), `${moTa}: thiếu lý do "${chu}" — ${t.slice(0, 300)}`);
  kiem(!t.includes("BOQ-HD") && !t.includes("01/2025/HĐ-XL") && !t.includes("HM-01"), moTa + ": hiển thị dữ liệu căn cứ dù chưa kiểm được");
  if (coNutTai) kiem(!!nutTheoChu(h.box, "⭳ Căn cứ JSON"), moTa + ": mất nút tải Căn cứ JSON");
  kiem(!!h.bangChung() && h.box.textContent.includes("Phát hiện cần xem"), moTa + ": lỗi căn cứ gỡ kết quả/bằng chứng");
}

// ------------------------------------------------------------------ các ca
const CA = [];
const ca = (ten, fn) => CA.push([ten, fn]);

ca("C01 hợp lệ · BOQ · không API hiện hành · tải gốc giữ nguyên", async () => {
  const h = await batDau();
  kiem(h.nutBoq() && h.nutPl(), "C01: bằng chứng L2 không có nút Xem BOQ căn cứ / Xem phụ lục căn cứ");
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  const t = h.lay(h.laTep, "GET tệp BASIS");
  kiem(t.url === urlTep(RUN_A), "C01: URL đọc căn cứ sai: " + t.url);
  kiem(t.method === "GET" && t.opts.body === undefined, "C01: đọc căn cứ không phải GET không body");
  kiem(t.opts.headers && t.opts.headers["X-KTT-Token"] === "TOKEN-THU" && t.opts.cache === "no-store" && t.opts.credentials === "same-origin", "C01: thiếu token/no-store/same-origin");
  kiem(h.panel() && h.panel().textContent.includes("Đang đọc"), "C01: không có trạng thái đang đọc");
  const r = phanHoiTep(BYTES_HOP_LE);
  t.resolve(r.res); await chay();
  const p = h.panel();
  kiem(p, "C01: không có panel Căn cứ lần chạy");
  if (!p) return;
  const s = p.textContent;
  for (const x of ["Căn cứ lần chạy · BOQ", RUN_A, sha(BYTES_HOP_LE), "01/2025/HĐ-XL", "revision 3", "01/03/2026", "BOQ-HD", "PL01-BOQ", "BOQ gốc HĐ", "PL PL01", String(BYTES_HOP_LE.length) + " byte"])
    kiem(s.includes(x), `C01: panel thiếu "${x}"`);
  kiem(!s.includes("15/04/2026") && !s.includes("2026-04-15"), "C01: panel dùng ngày NT hiện tại thay vì ngày lưu");
  kiem(!s.includes("(hiện tại)") && !s.includes("c".repeat(12)), "C01: panel lấy HĐ/căn cứ hiện tại");
  kiem(!/hiện hành|BOQ hiệu lực/i.test(s), "C01: panel gắn nhãn hiện hành/BOQ hiệu lực");
  const hang = (ma, ten) => tim(p, e => e.tagName === "TR" && e.children[1] && e.children[1].textContent === ma && (!ten || e.children[5].textContent === ten));
  const h1 = hang("HM-01"), h2 = hang("HM-02", "Bê tông móng"), h3 = hang("HM-02", "Bê tông móng (PL01)");
  kiem(h1 && h2 && h3, "C01: thiếu dòng BOQ");
  if (h1 && h2 && h3) {
    kiem(h1.children[0].textContent === "12" && h2.children[0].textContent === "13" && h3.children[0].textContent === "7", "C01: dòng vật lý sai");
    kiem(h1.children[7].textContent === "0", "C01: KL 0 tường minh không hiện 0");
    kiem(h2.children[7].textContent === "NULL" && h2.children[9].textContent === "NULL", "C01: KL/thành tiền NULL không hiện NULL (bị thành 0/—?)");
    kiem(h1.children[8].textContent === "1250000.50" && h3.children[7].textContent === "15.500", "C01: số không giữ nguyên chuỗi lưu (bị làm tròn/định dạng)");
    kiem(h1.children[5].textContent === XSS, "C01: tên chứa HTML không hiện nguyên chữ");
  }
  kiem(!tim(h.box, e => e.tagName === "IMG"), "C01: chuỗi HTML trong căn cứ thành phần tử");
  kiem(r.soDoc() >= 2 && h.env.bam.soGoi === 1, "C01: không đọc luồng/không băm SHA-256");
  kiem(!h.tatCaSau().some(c => c.method !== "GET"), "C01: có lệnh không phải GET");
  kiem(!h.tatCaSau().some(c => !c.url.startsWith("/api/m4/review")), "C01: gọi API ngoài Review (HĐ/PL hiện hành?): " + h.tatCaSau().map(c => c.url).join(" | "));
  kiem(h.tep().length === 1, "C01: số GET tệp sai");
  // tải gốc giữ nguyên
  const truoc = h.env.soClick();
  await h.bam(nutTheoChu(h.box, "⭳ Căn cứ JSON"), "⭳ Căn cứ JSON");
  const d = h.lay(h.laTep, "GET tải Căn cứ JSON");
  kiem(d.url === urlTep(RUN_A), "C01: nút tải gốc đổi URL");
  d.resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  kiem(h.env.soClick() === truoc + 1, "C01: tải Căn cứ JSON không click đúng một lần");
  kiem(h.panel() && h.panel().textContent.includes("BOQ-HD"), "C01: tải gốc làm mất panel");
});

ca("C02 phụ lục · đổi góc xem không GET lại · trạng thái lưu", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp").resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  await h.bam(h.nutPl(), "Xem phụ lục căn cứ");
  kiem(h.tep().length === 1, "C02: đổi sang phụ lục GET lại tệp");
  const p = h.panel(), s = p ? p.textContent : "";
  kiem(s.includes("Căn cứ lần chạy · Phụ lục"), "C02: tiêu đề phụ lục sai");
  for (const x of ["PL01", "PL02", "DA_KY", "DU_THAO", "2026-06-01", "2026-02-01", "2026-01-20"]) kiem(s.includes(x), `C02: thiếu "${x}"`);
  kiem(s.includes("áp dụng PL01") && s.includes("chưa áp dụng PL02"), "C02: không lấy danh sách áp dụng từ kết quả đã lưu");
  const r2 = p && tim(p, e => e.tagName === "TR" && e.children[0] && e.children[0].textContent === "PL02");
  kiem(r2 && r2.children[1].textContent === "NULL" && r2.children[4].textContent === "không", "C02: ngày ký NULL / đổi BOQ false hiển thị sai");
  kiem(!/hiện hành/i.test(s), "C02: gắn nhãn hiện hành");
  await h.bam(h.nutBoq(), "quay lại BOQ");
  kiem(h.tep().length === 1 && h.panel() && h.panel().textContent.includes("BOQ-HD"), "C02: quay lại BOQ GET lại hoặc mất dữ liệu");
});

const caDangKy = (ten, opt, chu, coNutTai = true) => ca(ten, async () => {
  const h = await batDau({ct: {[RUN_A]: opt}});
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  kiem(h.tep().length === 0, ten + ": vẫn GET tệp dù đăng ký sai");
  kiemChuaHien(h, chu, ten, coNutTai);
});
caDangKy("C03 không có BASIS", {artifact: [DK(ART_KHAC[RUN_A][0], "REPORT_L2", B("x")), DK(ART_KHAC[RUN_A][1], "RESULT", B("{}"))]}, "không có tệp căn cứ", false);
caDangKy("C04 hai BASIS", {artifact: [DK(ART[RUN_A], "BASIS", BYTES_HOP_LE), DK(ART_KHAC[RUN_A][1], "BASIS", BYTES_HOP_LE)]}, "2 tệp căn cứ");
caDangKy("C05 SHA đăng ký khác basis của lần chạy", {artifact: [DK(ART[RUN_A], "BASIS", BYTES_HOP_LE, {raw_sha256: "e".repeat(64)}), DK(ART_KHAC[RUN_A][1], "LOG", B("l"))]},
  "khác căn cứ của lần chạy");
caDangKy("C06 mã artifact không phải UUID", {artifact: [DK("../../m4/hop-dong", "BASIS", BYTES_HOP_LE)]}, "Đăng ký tệp căn cứ sai");
caDangKy("C07 vượt giới hạn hiển thị", {artifact: [DK(ART[RUN_A], "BASIS", BYTES_HOP_LE, {byte_length: 16 * 1024 * 1024 + 1})]}, "vượt giới hạn");

ca("C08 Content-Type sai → không đọc bytes", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  const r = phanHoiTep(BYTES_HOP_LE, {ct: "text/html; charset=utf-8"});
  h.lay(h.laTep, "GET tệp").resolve(r.res); await chay();
  kiemChuaHien(h, "không phải JSON căn cứ", "C08");
  kiem(r.soDoc() === 0 && h.env.bam.soGoi === 0, "C08: vẫn đọc/băm bytes");
});
ca("C09 Content-Length khác đăng ký → không đọc bytes", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  const r = phanHoiTep(BYTES_HOP_LE, {cl: BYTES_HOP_LE.length + 1});
  h.lay(h.laTep, "GET tệp").resolve(r.res); await chay();
  kiemChuaHien(h, "khác độ dài đăng ký", "C09");
  kiem(r.soDoc() === 0, "C09: vẫn đọc bytes");
});
ca("C10 bytes ngắn hơn / dài hơn đăng ký", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp").resolve(phanHoiTep(BYTES_HOP_LE.subarray(0, BYTES_HOP_LE.length - 5), {cl: null}).res); await chay();
  kiemChuaHien(h, "Độ dài thật", "C10 ngắn");
  kiem(h.env.bam.soGoi === 0, "C10: băm bytes thiếu");
  await h.bam(h.nutBoq(), "thử lại");
  const r = phanHoiTep(Buffer.concat([BYTES_HOP_LE, B("          ")]), {cl: null, cat: 2});
  h.lay(h.laTep, "GET tệp lần 2").resolve(r.res); await chay();
  kiemChuaHien(h, "dài hơn độ dài đăng ký", "C10 dài");
  kiem(r.daHuy(), "C10: không hủy luồng khi vượt độ dài đăng ký");
});
ca("C11 checksum sai (cùng độ dài)", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  const sai = Buffer.from(BYTES_HOP_LE); sai[sai.indexOf(B("BOQ-HD"))] = "X".charCodeAt(0);
  h.lay(h.laTep, "GET tệp").resolve(phanHoiTep(sai).res); await chay();
  kiemChuaHien(h, "SHA-256 thật", "C11");
  kiem(h.env.bam.soGoi === 1, "C11: không băm");
});
const caNoiDung = (ten, bytes, chu) => ca(ten, async () => {
  const h = await batDau({ct: {[RUN_A]: {basis: bytes}}});
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp").resolve(phanHoiTep(bytes).res); await chay();
  kiemChuaHien(h, chu, ten);
});
caNoiDung("C12 JSON hỏng (SHA khớp)", B('{"phien_ban":"m4.review.basis/1","tep":'), "không phải JSON hợp lệ");
caNoiDung("C13 phiên bản chưa hỗ trợ", bienThe(o => { o.phien_ban = "m4.review.basis/2"; }), "chưa hỗ trợ");
caNoiDung("C14 lệch danh tính tệp", bienThe(o => { o.tep.id = "33333333-3333-4333-8333-999999999999"; }), "không khớp lần chạy");
caNoiDung("C14b lệch HĐ của đợt", bienThe(o => { o.dot.hop_dong_id = HD2; }), "HĐ của đợt");
caNoiDung("C15 sai kiểu dòng BOQ", bienThe(o => { o.boq[0].dong[0].kl = {gia_tri: 1}; }), "sai kiểu ở boq.dong.kl");
caNoiDung("C16 JSON chung không phải căn cứ", B('{"ok":true,"data":[]}'), "chưa hỗ trợ");

ca("C17 không có crypto.subtle", async () => {
  const h = await batDau();
  h.env.ctx.crypto.subtle = undefined;
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp").resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  kiemChuaHien(h, "crypto.subtle", "C17");
});

ca("C18 căn cứ cũ thiếu mục → CHƯA ĐỦ, không thành 0", async () => {
  const bytes = bienThe(o => { delete o.boq; delete o.phu_luc; delete o.truoc_da_duyet; });
  const h = await batDau({ct: {[RUN_A]: {basis: bytes}}});
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp").resolve(phanHoiTep(bytes).res); await chay();
  const s = h.panel() ? h.panel().textContent : "";
  kiem(s.includes("Chưa đủ căn cứ") && s.includes("không có mục BOQ"), "C18: thiếu BOQ không báo CHƯA ĐỦ");
  kiem(s.includes("BOQ") && s.includes("phụ lục") && s.includes("trạng thái lịch sử đợt trước"), "C18: không liệt kê mục thiếu");
  // Khẳng định 0 về mục thiếu: xét chữ RIÊNG của từng nút (không gộp con), tách mệnh đề theo ";"/"—"/". "; chỉ bỏ đúng cụm phủ định tường minh
  // "không coi là 0…" của mệnh đề đó — "0 bảng/dòng/phụ lục", "so_dong 0" còn lại ở bất kỳ mệnh đề nào là vi phạm; số 0 không gắn đơn vị đó không bị xét.
  // Mọi dòng bảng (TR) trong panel của mục thiếu cũng là vi phạm (dòng BOQ/PL bịa ra).
  const PHU_DINH_0 = /không coi là\s+0(?:\/[^\s;,.—]+)?(?:\s+(?:bảng|dòng|phụ lục))?/gi;
  const KHANG_DINH_0 = /(?:^|[^\d.,\/])0\s*(?:bảng|dòng|phụ lục)|so_dong\s+0(?![\d.])/i;
  const viPham0 = root => {
    const loi = [];
    for (const e of timHet(root, x => x.tagName !== "#text")) {
      if (e.tagName === "TR") loi.push("dòng bảng: " + e.textContent.slice(0, 80));
      const rieng = e._text + e.children.filter(c => c.tagName === "#text").map(c => c._text).join("");
      for (const md of rieng.split(/[;—]|\.(?=\s|$)/)) if (KHANG_DINH_0.test(md.replace(PHU_DINH_0, " "))) loi.push("khẳng định 0: " + md.trim());
    }
    return loi;
  };
  const laThieu = (p, chu) => !!(p && tim(p, e => e._cls && e._cls.has("m4-notice") && e.textContent.includes("Chưa đủ căn cứ") && e.textContent.includes(chu)));
  const p1 = h.panel(), v1 = p1 ? viPham0(p1) : ["không có panel"];
  kiem(v1.length === 0, "C18: mục thiếu bị hiển thị thành 0 — " + v1.join(" | "));
  kiem(laThieu(p1, "không có mục BOQ"), "C18: không có nút thông báo CHƯA ĐỦ riêng cho BOQ thiếu");
  kiem(!s.includes("BOQ lần") && !s.includes("so_dong"), "C18: BOQ thiếu mà vẫn hiện bảng/số dòng BOQ");
  kiem(s.includes("01/2025/HĐ-XL") && s.includes("01/03/2026"), "C18: phần có trong căn cứ không hiển thị");
  await h.bam(h.nutPl(), "Xem phụ lục căn cứ");
  const s2 = h.panel() ? h.panel().textContent : "";
  kiem(s2.includes("không có mục phụ lục") && !s2.includes("0 phụ lục"), "C18: thiếu phụ lục bị coi là 0 phụ lục");
  const p2 = h.panel(), v2 = p2 ? viPham0(p2) : ["không có panel"];
  kiem(v2.length === 0, "C18: phụ lục thiếu bị hiển thị thành 0/dòng — " + v2.join(" | "));
  kiem(laThieu(p2, "không có mục phụ lục"), "C18: không có nút thông báo CHƯA ĐỦ riêng cho phụ lục thiếu");
  kiem(s2.includes("01/2025/HĐ-XL") && s2.includes("01/03/2026"), "C18: góc phụ lục mất phần có trong căn cứ");
  kiem(h.tep().length === 1, "C18: GET lại khi đổi góc xem");
  // Đối chứng âm/dương: DOM tổng hợp RIÊNG (không gắn vào box, không đụng DOM sản phẩm) — cùng viPham0 phải bắt khẳng định 0 thật, không bắt câu phủ định/số 0 khác.
  const D = h.env.document;
  const gia = (...cau) => { const g = D.createElement("section"); for (const c of cau) { const d = D.createElement("div"); d.append(c); g.append(d); } return g; };
  const tr = D.createElement("tr"), o_ = D.createElement("td"); o_.append("HM-01"); tr.append(o_);
  const am = [
    ["0 bảng BOQ", gia("Căn cứ ghi nhận 0 bảng BOQ lúc chạy.")],
    ["0 dòng sau câu phủ định", gia("Căn cứ lần chạy này không có mục BOQ — chưa hiển thị; không coi là 0 dòng.", "BOQ lần 1 · 0 dòng lưu trong căn cứ.")],
    ["phủ định rồi khẳng định cùng nút", gia("không coi là 0 dòng; ghi nhận 0 dòng")],
    ["0 phụ lục", gia("Căn cứ ghi nhận 0 phụ lục lúc chạy.")],
    ["so_dong 0", gia("sheet BOQ-HD · so_dong 0 · trạng thái lưu XONG")],
    ["dòng bảng bịa", gia(tr)]];
  for (const [ten, g] of am) kiem(!g.isConnected && viPham0(g).length > 0, `C18 đối chứng âm "${ten}": viPham0 không bắt khẳng định 0 về mục thiếu`);
  const duong = gia("Căn cứ lần chạy này không có mục BOQ — chưa hiển thị; không coi là 0 dòng.",
    "Căn cứ lưu của lần chạy này không có mục: phụ lục, BOQ — hiển thị là chưa đủ; không coi là 0/trống, không lấy từ dữ liệu hiện tại.",
    "Đợt 0 · revision 0 · rev tham số 0 · PL01 · 100 byte");
  kiem(viPham0(duong).length === 0, "C18 đối chứng dương: viPham0 bắt nhầm câu phủ định/số 0 hợp lệ — " + viPham0(duong).join(" | "));
});
ca("C18b bảng thiếu dòng ≠ 0 dòng; 0 phụ lục tường minh", async () => {
  const bytes = bienThe(o => { delete o.boq[0].dong; o.boq[1].dong = []; o.phu_luc = []; });
  const h = await batDau({ct: {[RUN_A]: {basis: bytes}}});
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp").resolve(phanHoiTep(bytes).res); await chay();
  const s = h.panel() ? h.panel().textContent : "";
  kiem(s.includes("Bảng này không có dòng trong căn cứ đã lưu"), "C18b: bảng thiếu dòng không báo");
  kiem(s.includes("0 dòng lưu trong căn cứ"), "C18b: bảng 0 dòng tường minh không hiện 0");
  kiem(s.includes("phụ lục " + PL1), "C18b: BOQ trỏ phụ lục vắng mục không nêu rõ");
  await h.bam(h.nutPl(), "Xem phụ lục căn cứ");
  kiem(h.panel() && h.panel().textContent.includes("0 phụ lục"), "C18b: 0 phụ lục tường minh không hiện");
});

const caQuyen = (ten, status) => ca(ten, async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp").resolve(phanHoi(status, {error: "M4_REVIEW_PHAM_VI", message: "Đã thu hồi quyền đọc lần chạy"})); await chay();
  kiem(!h.panel() && !h.bangChung(), ten + ": quyền hiện hành bị từ chối mà bằng chứng/căn cứ còn hiện");
  kiem(!h.box.textContent.includes("Phát hiện cần xem"), ten + ": kết quả lần chạy còn hiện sau từ chối quyền");
  kiem(!nutTheoChu(h.box, "⭳ Căn cứ JSON"), ten + ": nút tải còn sau từ chối quyền");
  kiem(h.trangThai().includes("thu hồi"), ten + ": không báo từ chối");
});
caQuyen("C19 403 hiện hành", 403);
caQuyen("C20 401 hiện hành", 401);

ca("C21 403 cũ sau đổi phát hiện không gỡ ngữ cảnh mới", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  const t = h.lay(h.laTep, "GET tệp");
  await h.moBangChung("BangKL!G20");
  const tt = h.trangThai();
  t.resolve(phanHoi(403, {error: "M4_REVIEW_PHAM_VI", message: "Đã thu hồi quyền đọc"})); await chay();
  const bc = h.bangChung();
  kiem(bc && bc.textContent.includes("B4-1"), "C21: 403 cũ gỡ bằng chứng mới");
  kiem(h.box.textContent.includes("Phát hiện cần xem"), "C21: 403 cũ gỡ kết quả");
  kiem(!h.panel(), "C21: panel căn cứ của phát hiện cũ hiện ở phát hiện mới");
  kiem(h.trangThai() === tt, "C21: 403 cũ ghi trạng thái");
});

ca("C22 headers chậm + đóng/mở lại cùng phát hiện (A→B→A)", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ (1)");
  const t1 = h.lay(h.laTep, "GET tệp 1");
  await h.bam(nutTheoChu(h.bangChung(), "Đóng"), "Đóng");
  kiem(!h.panel(), "C22: đóng bằng chứng mà panel còn");
  await h.moBangChung("BangKL!F12");
  kiem(!h.panel(), "C22: mở lại phát hiện hiện panel của lần trước");
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ (2)");
  const t2 = h.lay(h.laTep, "GET tệp 2");
  const tt = h.trangThai();
  t1.resolve(phanHoi(403, {error: "M4_REVIEW_PHAM_VI", message: "403 cũ"})); await chay();
  kiem(h.bangChung() && h.panel() && h.panel().textContent.includes("Đang đọc"), "C22: 403 cũ xóa bằng chứng/trạng thái đang đọc của lần mới");
  kiem(h.trangThai() === tt, "C22: 403 cũ ghi trạng thái");
  t2.resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  kiem(h.panel() && h.panel().textContent.includes("BOQ-HD"), "C22: lần đọc mới không công bố");
});

ca("C23 bytes chậm + đổi lần chạy → hủy, B đọc đúng artifact của B", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  const r = phanHoiTep(BYTES_HOP_LE, {cham: true});
  h.lay(h.laTep, "GET tệp A").resolve(r.res); await chay();
  await h.moRun(RUN_B, undefined, {tra: false});
  r.nha(); await chay();
  kiem(r.daHuy(), "C23: không hủy luồng của lần chạy cũ");
  kiem(!h.panel(), "C23: căn cứ của lần chạy A hiện sau khi đổi sang B");
  kiem(h.env.bam.soGoi === 0, "C23: vẫn băm bytes của lần chạy cũ");
  h.laySetup(h.laCt(RUN_B), "GET chi tiết B").resolve(phanHoi(200, CHI_TIET(RUN_B))); await chay();
  await h.traDs(false);
  kiem(!h.panel(), "C23: panel A hiện trên kết quả B");
  await h.moBangChung("BangKL!F12");
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ B");
  const t = h.lay(h.laTep, "GET tệp B");
  kiem(t.url === urlTep(RUN_B), "C23: lần chạy B đọc artifact sai: " + t.url);
  t.resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  kiem(h.panel() && h.panel().textContent.includes(RUN_B) && !h.panel().textContent.includes(RUN_A), "C23: panel B không gắn đúng lần chạy B");
});

ca("C24 crypto chậm + đổi vai qua shell", async () => {
  const h = await batDau();
  h.env.bam.cham = true;
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp").resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  setup(h.env.bam.cho.length === 1, "C24: không tới bước băm");
  h.W.kttM4Review.ve(h.box, NGU_CANH({nguoi: "NV_B"})); await chay();
  const tt = h.trangThai(), chu = h.box.textContent;
  h.env.bam.cho.shift()(); await chay();
  kiem(!h.panel() && !h.box.textContent.includes("Chưa hiển thị được"), "C24: căn cứ/lỗi của vai cũ hiện ở vai mới");
  kiem(h.trangThai() === tt && h.box.textContent === chu, "C24: kết quả muộn của vai cũ đổi DOM vai mới");
  await h.traDs();
  kiem(!h.panel(), "C24: căn cứ vai cũ hiện sau khi nạp vai mới");
  kiem(h.tep().length === 1, "C24: GET tệp thêm");
});

ca("C25 crypto chậm + đổi lớp", async () => {
  const h = await batDau();
  h.env.bam.cham = true;
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp").resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  setup(h.env.bam.cho.length === 1, "C25: không tới bước băm");
  await h.bam(nutTheoChu(h.box, "Lớp 1 · Toàn vẹn file"), "tab Lớp 1");
  h.env.bam.cho.shift()(); await chay();
  kiem(!h.panel(), "C25: đổi lớp mà căn cứ cũ vẫn công bố");
});

ca("C26 rời tab (tat) rồi quay lại", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  const t = h.lay(h.laTep, "GET tệp");
  h.W.kttM4Review.tat();
  const chu = h.box.textContent;
  t.resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  kiem(h.box.textContent === chu, "C26: kết quả sau rời tab đổi DOM");
  kiem(h.env.bam.soGoi === 0, "C26: vẫn đọc/băm sau rời tab");
  h.W.kttM4Review.ve(h.box, NGU_CANH()); await chay();
  await h.traDs();
  const c = h.conCho(h.laCt(RUN_A));
  setup(c.length === 1, "C26: quay lại tab không nạp lại lần chạy");
  c[0].xong = true; c[0].resolve(phanHoi(200, CHI_TIET(RUN_A))); await chay();
  await h.traDs(false);
  kiem(!h.panel() && !h.bangChung(), "C26: quay lại tab hiện căn cứ/bằng chứng cũ");
});

ca("C27 bytes chậm + đổi HĐ", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  const r = phanHoiTep(BYTES_HOP_LE, {cham: true});
  h.lay(h.laTep, "GET tệp").resolve(r.res); await chay();
  h.W.kttM4Review.ve(h.box, NGU_CANH({hdId: HD2, soHd: "02/2025"})); await chay();
  r.nha(); await chay();
  kiem(r.daHuy() && h.env.bam.soGoi === 0, "C27: không hủy luồng của HĐ cũ");
  kiem(!h.panel() && !h.box.textContent.includes("BOQ-HD"), "C27: căn cứ HĐ cũ hiện ở HĐ mới");
  const ds = h.conCho(h.laDs);
  kiem(ds.length && ds.every(c => c.url.includes(HD2)), "C27: HĐ mới không nạp đúng HĐ");
});

ca("C28 crypto chậm + barrier đổi vai thật (kttChung.doiVaiTuanTu)", async () => {
  const h = await batDau();
  h.env.bam.cham = true;
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp").resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  setup(h.env.bam.cho.length === 1, "C28: không tới bước băm");
  let nhaGui;
  const p = h.W.kttChung.doiVaiTuanTu(() => new Promise(r => { nhaGui = r; }), "m4-vai-trang-thai", "m4_review");
  await chay();
  setup(h.box.textContent.includes("Đang tải"), "C28: barrier đổi vai không tới xoa() của review.js");
  kiem(!h.nutBoq(), "C28: nút Xem BOQ căn cứ còn trong lúc barrier đổi vai");
  h.env.bam.cho.shift()(); await chay();
  kiem(!h.panel() && h.box.textContent.includes("Đang tải"), "C28: căn cứ công bố trong lúc barrier đổi vai");
  setup(typeof nhaGui === "function", "C28: doiVaiTuanTu không gọi gui");
  nhaGui(); await chay(); await p.catch(() => {});
  await h.traDs(false);
  kiem(!h.panel(), "C28: căn cứ cũ hiện sau khi barrier mở");
  kiem(h.tep().length === 1, "C28: GET tệp thêm");
});

ca("C29 lần chạy A→B→A khi headers chậm", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ (A1)");
  const t1 = h.lay(h.laTep, "GET tệp A1");
  await h.moRun(RUN_B);
  await h.moRun(RUN_A);
  await h.moBangChung("BangKL!F12");
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ (A2)");
  const t2 = h.lay(h.laTep, "GET tệp A2");
  kiem(t2.url === urlTep(RUN_A), "C29: URL A2 sai");
  t1.resolve(phanHoiTep(bienThe(o => { o.boq[0].sheet = "CU-SHEET"; })).res); await chay();
  kiem(h.panel() && h.panel().textContent.includes("Đang đọc") && !h.box.textContent.includes("CU-SHEET"), "C29: kết quả A1 cũ công bố/xóa trạng thái của A2");
  t2.resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  kiem(h.panel() && h.panel().textContent.includes("BOQ-HD") && !h.box.textContent.includes("CU-SHEET"), "C29: A2 không công bố");
});

ca("C30 mất kết nối → bấm lại → đạt", async () => {
  const h = await batDau();
  await h.bam(h.nutBoq(), "Xem BOQ căn cứ");
  h.lay(h.laTep, "GET tệp 1").reject(new TypeError("Failed to fetch")); await chay();
  kiemChuaHien(h, "Mất kết nối", "C30");
  kiem(h.bangChung() && h.box.textContent.includes("Phát hiện cần xem"), "C30: mất kết nối gỡ kết quả/bằng chứng");
  await h.bam(h.nutBoq(), "bấm lại");
  h.lay(h.laTep, "GET tệp 2").resolve(phanHoiTep(BYTES_HOP_LE).res); await chay();
  kiem(h.panel() && h.panel().textContent.includes("BOQ-HD"), "C30: thử lại không công bố");
  kiem(!h.tatCaSau().some(c => c.method !== "GET"), "C30: có lệnh ghi");
});

// ------------------------------------------------------------------ chạy tuần tự, hữu hạn; không bỏ qua ca
async function main() {
  for (const [ten, fn] of CA) {
    viPhamCa = [];
    try { await fn(); }
    catch (e) {
      if (e instanceof LoiSetup) { setupErrors.push(`${ten}: ${e.message}`); ketQua.push([ten, "SETUP_ERROR"]); continue; }
      viPhamCa.push("ngoại lệ: " + ((e && e.stack) || e));
    }
    for (const v of viPhamCa) violations.push(`${ten}: ${v}`);
    ketQua.push([ten, viPhamCa.length ? "VI_PHAM" : "DAT"]);
  }
  await chay();
  for (const e of loiNgoai) violations.push("unhandledRejection: " + ((e && e.stack) || e));
  for (const [ten, kq] of ketQua) console.log(`${kq.padEnd(12)} ${ten}`);
  console.log(`setup_errors: ${setupErrors.length}`);
  for (const s of setupErrors) console.log("  SETUP " + s);
  console.log(`semantic_violations: ${violations.length}`);
  for (const v of violations) console.log("  VI_PHAM " + v);
  const dat = setupErrors.length === 0 && violations.length === 0 && ketQua.length === CA.length && ketQua.every(([, k]) => k === "DAT");
  console.log(dat ? `m4_02a_basis_async: ${CA.length}/${CA.length} ca đạt` : "m4_02a_basis_async: KHÔNG ĐẠT");
  process.exitCode = dat ? 0 : 1;
}
main().catch(e => { console.error("harness lỗi:", e); process.exitCode = 1; });
