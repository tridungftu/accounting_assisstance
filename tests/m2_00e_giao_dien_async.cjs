"use strict";
// M2-00E — kiểm bất đồng bộ trên MÃ THẬT assets/m2_tai_hoa_don.js (khối #m2-tct trong Hóa đơn mua XML), không phải trình duyệt: DOM giả tối thiểu (id lấy từ index.html thật),
// fetch do ca điều khiển (treo/trả theo thứ tự), luồng SSE giả bằng getReader() có abort. Cổng chung window.kttChung là bản giả tối thiểu (đăng ký vai, node, empty).
// Chạy: `node tests/m2_00e_giao_dien_async.cjs` (Node >= 18). Mã thoát 0 = mọi ca đạt. Không ghi/xóa tệp, không mạng, không tiến trình con. Dữ liệu chỉ DEMO.
// Ca:
//  S0  chưa cấu hình: hiện "Bộ tải chưa cấu hình" + lý do bằng textContent (không dựng HTML từ máy chủ), ẩn form, 0 POST.
//  S1  đã cấu hình, bộ tải chưa mở: tự POST khởi động (TL 43 §3 bước 1); form chỉ có pháp nhân máy chủ trả; mục chưa sẵn sàng bị khóa kèm lý do.
//  S2  luồng đầy đủ (M2-00-01): body bắt đầu đúng 9 trường + khóa, không actor/pháp nhân/đường dẫn/mật khẩu; trạng thái theo sự kiện: mở cổng → chờ đăng nhập (đồng hồ 8 phút)
//      → đã đăng nhập → lấy danh sách → tải n/N → ghi manifest → biên nhận → nhận → "Đã nhận vào M2: mới a · đổi trạng thái b · không mã c · lỗi d"; mở thư mục, xem manifest,
//      xem hóa đơn của kỳ; lần tải sau dùng khóa MỚI.
//  S3  lỗi (M2-00-05): biên nhận FAILED/PARTIAL hiện mã lỗi + giai đoạn + HTTP + gợi ý, KHÔNG gọi nhận; lỗi API hiện mã + HTTP + gợi ý; ngoại lệ khi nhận hiện, không im lặng.
//  S4  mất kết nối khi bắt đầu: bấm lại gửi ĐÚNG khóa cũ (cùng một lần tải); lỗi xác định (403) → khóa mới.
//  S5  đổi vai giữa chừng: luồng bị hủy, DOM xóa đồng bộ, phản hồi về muộn không vẽ lại; nạp lại theo vai mới.
//  S6  bộ tải chết giữa chừng: lỗi hiện + nút "Kiểm tra lại" tiếp tục từ con trỏ cũ.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");
const JS = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/m2_tai_hoa_don.js"), "utf8");
const HTML = fs.readFileSync(path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets/index.html"), "utf8");
const ID_TINH = new Set([...HTML.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const loiNgoai = [];
process.on("unhandledRejection", e => { loiNgoai.push(e); });

function moiTruong() {
  const reg = new Map(), dongId = new Set();
  let taoTinh = false;
  class El {
    constructor(tag) { this.tagName = String(tag).toUpperCase(); this.children = []; this.parent = null; this._text = ""; this._id = ""; this.listeners = {};
      this.attrs = {}; this.dataset = {}; this.style = {}; this._cls = new Set(); this.disabled = false; this.checked = false; this._value = ""; this.type = ""; }
    get id() { return this._id; }
    set id(v) { this._id = v; if (!reg.has(v)) reg.set(v, []); reg.get(v).push(this); if (!taoTinh) dongId.add(v); }
    get isConnected() { let e = this; while (e) { if (e === body) return true; e = e.parent; } return false; }
    get className() { return [...this._cls].join(" "); }
    set className(v) { this._cls = new Set(String(v || "").split(/\s+/).filter(Boolean)); }
    get classList() { const s = this; return {add: (...c) => c.forEach(x => s._cls.add(x)), remove: (...c) => c.forEach(x => s._cls.delete(x)),
      toggle: (c, on) => { const v = on === undefined ? !s._cls.has(c) : on; if (v) s._cls.add(c); else s._cls.delete(c); return v; }, contains: c => s._cls.has(c)}; }
    get value() { return this._value; }
    set value(v) { this._value = String(v ?? ""); }
    get textContent() { return this._text + this.children.map(c => c.textContent).join(""); }
    set textContent(v) { for (const c of this.children) c.parent = null; this._text = String(v ?? ""); this.children = []; }
    _con(n) { const c = typeof n === "string" ? Object.assign(new El("#text"), {_text: n}) : n; if (c.parent) c.parent.children = c.parent.children.filter(x => x !== c); c.parent = this; return c; }
    append(...n) { for (const x of n) this.children.push(this._con(x)); }
    replaceChildren(...n) { for (const c of this.children) c.parent = null; this._text = ""; this.children = []; this.append(...n); }
    addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
    dispatch(t, ev = {}) { return (this.listeners[t] || []).map(fn => fn({preventDefault() {}, target: this, ...ev})); }
    click() { return this.dispatch("click"); }
    scrollIntoView() { this.scrolled = true; }
  }
  const body = new El("body");
  const document = {body,
    getElementById: id => { const ds = (reg.get(id) || []).filter(e => e.isConnected); if (ds.length) return ds[ds.length - 1];
      if (dongId.has(id) || !ID_TINH.has(id)) return null; taoTinh = true; const e = new El("div"); e.id = id; taoTinh = false; body.append(e); return e; },
    createElement: t => new El(t), querySelector: s => (s.includes("ktt-token") ? {content: "TOKEN-THU"} : null)};
  const calls = [];
  const fetch = (url, opts = {}) => new Promise((resolve, reject) => {
    const c = {url, opts, resolve, reject, method: (opts && opts.method) || "GET"};
    calls.push(c);
    if (opts && opts.signal) opts.signal.addEventListener("abort", () => { const e = new Error("aborted"); e.name = "AbortError"; reject(e); });
  });
  let soUuid = 0;
  const vai = new Map();
  const K = {node: (tag, text, cls) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (cls) el.className = cls; return el; },
    empty: (m, h) => { const b = document.createElement("div"); b.className = "empty-state"; const t = document.createElement("strong"); t.textContent = m; const p = document.createElement("p"); p.textContent = h; b.append(t, p); return b; },
    toast() {}, dangKyVai: (ten, xoa, nap) => vai.set(ten, {xoa, nap}), vaiDangChan: () => false};
  const ctx = {document, Node: El, console, setTimeout, clearTimeout, setInterval, clearInterval, Promise, Map, Set, JSON, Math, Date, Number, String, Object, Array, Error, TypeError,
    RegExp, parseInt, encodeURIComponent, decodeURIComponent, AbortController, TextDecoder, Uint8Array, location: {hash: ""}, crypto: {randomUUID: () => "00000000-0000-4000-8000-" + String(++soUuid).padStart(12, "0")}, fetch,
    navigator: {}};
  ctx.window = ctx;
  ctx.kttChung = K;
  ctx.addEventListener = () => {};
  vm.createContext(ctx);
  return {ctx, document, calls, vai};
}

const phanHoi = (status, data, body) => ({ok: status >= 200 && status < 300, status, headers: {get: () => "application/json"}, json: async () => data, body});
const nghi = () => new Promise(r => setTimeout(r, 0));
async function chay(n = 12) { for (let i = 0; i < n; i++) await nghi(); }
function tim(root, pred) { if (pred(root)) return root; for (const c of root.children || []) { const r = tim(c, pred); if (r) return r; } return null; }
function timTat(root, pred, out = []) { if (pred(root)) out.push(root); for (const c of root.children || []) timTat(c, pred, out); return out; }
const nut = (root, s) => tim(root, e => e.tagName === "BUTTON" && e.textContent.includes(s));
const enc = new TextEncoder();
function luong(signal) {
  const hang = []; let cho = null, dong = false;
  const lap = () => { if (!cho) return; if (hang.length) { const c = cho; cho = null; c.res({done: false, value: hang.shift()}); } else if (dong) { const c = cho; cho = null; c.res({done: true, value: undefined}); } };
  if (signal) signal.addEventListener("abort", () => { if (cho) { const c = cho; cho = null; const e = new Error("aborted"); e.name = "AbortError"; c.rej(e); } dong = true; });
  return {day(t) { hang.push(enc.encode(t)); lap(); }, ket() { dong = true; lap(); }, body: {getReader: () => ({read: () => new Promise((res, rej) => { cho = {res, rej}; lap(); })})}};
}
const khung = (ten, du, seq) => (seq !== undefined ? `id: ${seq}\n` : "") + `event: ${ten}\ndata: ${JSON.stringify(du)}\n\n`;
const sk = (seq, type, payload, ts) => khung("su-kien", {seq, type, payload, ts: ts ?? Date.now()}, seq);

const API = "/api/m2/tai-hoa-don";
const MUC = (ma, key, ss = true, ly = null, viet = null) => ({source_instance: "demo.hddt.m2", scope_ref: "INV_SET_DEMO", company_key: key, phap_nhan_ma: ma, san_sang: ss, ly_do: ly, ly_do_vi: viet});
const TT = (muc, san = true, them = {}) => ({phien_ban: "m2_00e.v1", cau_hinh: true, bo_tai: {san_sang: san, trang_thai: san ? "SAN_SANG" : "CHUA_KHOI_DONG"}, muc, ...them});
const HANDLE = "ab".repeat(32);
const RUN_REL = "DEMO_A/2026-09/mua_vao/20261024-093000";
const REPLAY = (trang, runs) => ({phien_ban: "m2_00b.run.v1", run_handle: HANDLE, trang_thai: "REPLAY", ket_qua: {trang_thai: trang, runs}, doi_soat: null});
const RUN_OK = {ky: "2026-09", chieu: "purchase", run_rel: RUN_REL, trang_thai: "COMPLETE", loi: []};
const NHAN_OK = {run_handle: HANDLE, trang_thai_tai: "COMPLETE", nhat_ky: "DA_GHI", tom_tat: {moi: 5, doi_trang_thai: 2, khong_ma: 1, loi: 0, khong_doi: 0, giu_cho_tien_te: 0},
  runs: [{run_rel: RUN_REL, ky: "2026-09", chieu: "purchase", nguon: "TAI_MOI", so_muc: 8, ngoai_le: []}]};

async function main() {
  const {ctx, document, calls, vai} = moiTruong();
  const $ = id => document.getElementById(id);
  const conLai = pred => calls.filter(c => !c.xong && pred(c));
  const cho = (pred, moTa) => { const c = calls.find(x => !x.xong && pred(x)); assert.ok(c, "không thấy yêu cầu: " + moTa); c.xong = true; return c; };
  const get = u => c => c.method === "GET" && c.url === u;
  const post = u => c => c.method === "POST" && c.url === u;
  const sseUrl = c => c.method === "GET" && c.url.startsWith(API + "/su-kien?");
  const tienTrinh = () => $("m2-tct-tien-trinh").textContent;
  const ketQua = () => $("m2-tct-ket-qua").textContent;
  const lamMoi = []; // đếm nút Làm mới của M2 (danh sách hóa đơn) bị bấm
  $("m2-refresh").addEventListener("click", () => lamMoi.push(1));
  const loc = []; $("m2-loc").addEventListener("click", () => loc.push(1));
  ctx.location.hash = "#hoadonmua";
  vm.runInContext(JS, ctx, {filename: "m2_tai_hoa_don.js"});
  $("m2-tct-dd-xml").checked = true;  // thuộc tính HTML `checked` mà DOM giả không đọc

  // ---------------------------------------------------------------- S0 chưa cấu hình
  await chay();
  cho(get(API), "S0 GET trạng thái").resolve(phanHoi(200, {phien_ban: "m2_00e.v1", cau_hinh: false, ma: "TAI_HOA_DON_CHUA_CAU_HINH",
    ly_do: "Bộ tải chưa cấu hình (cấu hình chưa có mục [tai_hoa_don]). <b>x</b>", goi_y: "Báo Claude đặt mục [tai_hoa_don].", bo_tai: {san_sang: false}, muc: []}));
  await chay();
  assert.ok($("m2-tct-bo-tai").textContent.includes("Bộ tải chưa cấu hình"), "S0: thiếu thông báo chưa cấu hình");
  assert.ok($("m2-tct-bo-tai").textContent.includes("<b>x</b>"), "S0: chuỗi máy chủ phải hiện nguyên văn (textContent)");
  assert.strictEqual(tim($("m2-tct-bo-tai"), e => e.tagName === "B"), null, "S0: dựng HTML từ chuỗi máy chủ");
  assert.ok($("m2-tct-form").classList.contains("hidden"), "S0: form phải ẩn khi chưa cấu hình");
  assert.strictEqual(calls.filter(c => c.method === "POST").length, 0, "S0: không được POST khi chưa cấu hình");
  console.log("S0 đạt");

  // ---------------------------------------------------------------- S1 đã cấu hình, bộ tải chưa mở → tự khởi động
  $("m2-tct-lam-moi").click(); await chay();
  cho(get(API), "S1 GET").resolve(phanHoi(200, TT([MUC("DEMO_A", "MST_0100000001", false, "NODE_CHUA_SAN_SANG", "Bộ tải chưa mở — bấm “Mở bộ tải”."),
    MUC("DEMO_B", "MST_0100000002", false, "PROFILE_NOT_FOUND", "Chưa có hồ sơ đăng nhập cổng thuế của pháp nhân này trong thư mục profiles của bộ tải.")], false)));
  await chay();
  const kd = cho(post(API + "/khoi-dong"), "S1 POST khởi động");
  assert.deepStrictEqual(JSON.parse(kd.opts.body), {}, "S1: khởi động chỉ gửi {}");
  kd.resolve(phanHoi(200, {bo_tai: {san_sang: true}})); await chay();
  cho(get(API), "S1 GET sau mở").resolve(phanHoi(200, TT([MUC("DEMO_A", "MST_0100000001"), MUC("DEMO_B", "MST_0100000002", false, "PROFILE_NOT_FOUND", "Chưa có hồ sơ đăng nhập cổng thuế của pháp nhân này.")], true)));
  await chay();
  assert.ok(!$("m2-tct-form").classList.contains("hidden"), "S1: form phải hiện");
  const ops = $("m2-tct-phap-nhan").children;
  assert.deepStrictEqual(ops.map(o => o.textContent.split(" — ")[0]), ["DEMO_A · MST_0100000001", "DEMO_B · MST_0100000002"], "S1: chỉ pháp nhân máy chủ trả");
  assert.deepStrictEqual(ops.map(o => o.disabled), [false, true], "S1: mục chưa sẵn sàng phải bị khóa");
  assert.ok(ops[1].textContent.includes("Chưa có hồ sơ đăng nhập"), "S1: thiếu lý do chưa sẵn sàng");
  assert.strictEqual($("m2-tct-phap-nhan").value, JSON.stringify(["demo.hddt.m2", "INV_SET_DEMO", "MST_0100000001"]), "S1: phải chọn sẵn pháp nhân sẵn sàng đầu tiên");
  assert.ok(/^\d{4}-\d{2}$/.test($("m2-tct-thang").value), "S1: kỳ mặc định (tháng trước)");
  assert.strictEqual(calls.filter(post(API + "/khoi-dong")).length, 1, "S1: chỉ tự khởi động một lần");
  console.log("S1 đạt");

  // ---------------------------------------------------------------- S2 luồng đầy đủ
  $("m2-tct-thang").value = "2026-09";
  $("m2-tct-form").dispatch("submit"); await chay();
  assert.ok(tienTrinh().includes("Đang gửi lệnh tải"), "S2: thiếu trạng thái gửi lệnh");
  assert.ok($("m2-tct-bat-dau").disabled, "S2: nút tải phải khóa khi đang chạy");
  const bd = cho(post(API + "/bat-dau"), "S2 POST bắt đầu");
  const b = JSON.parse(bd.opts.body);
  assert.deepStrictEqual(Object.keys(b).sort(), ["company_key", "formats", "khoa", "mode", "month", "scope_ref", "source_instance", "types", "year"], "S2: body phải đúng 9 trường");
  assert.deepStrictEqual([b.source_instance, b.scope_ref, b.company_key, b.mode, b.year, b.month, b.types, b.formats],
    ["demo.hddt.m2", "INV_SET_DEMO", "MST_0100000001", "month", 2026, 9, ["purchase"], ["xml"]]);
  assert.ok(/^m2tct-[A-Za-z0-9_-]{8,}$/.test(b.khoa), "S2: khóa thao tác sai dạng");
  assert.ok(!/actor|phap_nhan|profile|duong_dan|password|mat_khau|captcha|token|run_id|cong/i.test(bd.opts.body), "S2: body chứa trường cấm");
  const khoa1 = b.khoa;
  bd.resolve(phanHoi(200, {run_handle: HANDLE, trang_thai: "STARTED", run_id: "20261024-093000", phap_nhan_ma: "DEMO_A"})); await chay();
  assert.ok(tienTrinh().includes("Đang mở cổng thuế"), "S2: bước 1 'Đang mở cổng thuế' — thực tế: " + tienTrinh());
  const s1 = cho(sseUrl, "S2 SSE");
  assert.strictEqual(s1.url, `${API}/su-kien?run=${HANDLE}&cursor=0`);
  const L1 = luong(s1.opts.signal);
  s1.resolve(phanHoi(200, null, L1.body)); await chay();
  L1.day(sk(1, "log", {msg: "Dang mo cong thue hoadondientu.gdt.gov.vn ..."})); await chay();
  assert.ok(tienTrinh().includes("Đang mở cổng thuế"));
  L1.day(sk(2, "log", {msg: "Da dien san tai khoan. Vui long NHAP CAPTCHA va bam Dang nhap trong cua so trinh duyet."}, Date.now() - 20000)); await chay();
  assert.ok(tienTrinh().includes("Chờ đăng nhập — gõ captcha trong cửa sổ Chrome"), "S2: thiếu bước chờ captcha");
  assert.ok(/còn 07:(3[6-9]|4[0-4]) \/ hạn 8 phút/.test(tienTrinh()), "S2: đồng hồ 8 phút sai: " + tienTrinh());
  L1.day(sk(3, "log", {msg: "Da nhan dien dang nhap thanh cong!"})); await chay();
  assert.ok(tienTrinh().includes("Đã đăng nhập"), "S2: thiếu bước đã đăng nhập");
  assert.ok(!tienTrinh().includes("còn 0"), "S2: đồng hồ phải tắt sau khi đăng nhập");
  L1.day(sk(4, "phase", {type: "purchase", label: "Mua vao", monthTag: "2026-09"})); await chay();
  assert.ok(tienTrinh().includes("Đang lấy danh sách Mua vào 2026-09"), "S2: thiếu bước lấy danh sách: " + tienTrinh());
  L1.day(sk(5, "progress", {type: "purchase", monthTag: "2026-09", index: 3, total: 12})); await chay();
  assert.ok(tienTrinh().includes("Đang tải 3/12 (Mua vào 2026-09)"), "S2: thiếu bước tải n/N: " + tienTrinh());
  const pg = tim($("m2-tct-tien-trinh"), e => e.tagName === "PROGRESS");
  assert.deepStrictEqual([Number(pg.value), pg.max], [3, 12], "S2: thanh tiến độ sai");
  L1.day(sk(6, "phase", {type: "purchase", label: "Dang ghi manifest", monthTag: "2026-09"})); await chay();
  assert.ok(tienTrinh().includes("Đang ghi manifest"), "S2: thiếu bước ghi manifest");
  L1.day(sk(7, "manifest", {run_rel: RUN_REL, trang_thai: "COMPLETE"}) + sk(8, "done", {trang_thai: "COMPLETE", so_run: 1}) + khung("ket-thuc", {ly_do: "DONE"})); await chay();
  const tt1 = cho(get(`${API}/trang-thai?run=${HANDLE}`), "S2 trạng thái cuối");
  tt1.resolve(phanHoi(200, REPLAY("COMPLETE", [RUN_OK]))); await chay();
  const nh = cho(post(API + "/nhan"), "S2 POST nhận");
  assert.deepStrictEqual(JSON.parse(nh.opts.body), {run: HANDLE}, "S2: nhận chỉ gửi mã lần tải");
  assert.ok(tienTrinh().includes("Đang nhận vào M2"), "S2: thiếu bước nhận");
  assert.strictEqual(lamMoi.length, 0);
  nh.resolve(phanHoi(200, NHAN_OK)); await chay();
  assert.ok(ketQua().includes("Đã nhận vào M2: mới 5 · đổi trạng thái 2 · không mã 1 · lỗi 0"), "S2: thiếu dòng kết quả nhận: " + ketQua());
  assert.strictEqual(lamMoi.length, 1, "S2: sau khi nhận phải làm mới danh sách hóa đơn M2");
  assert.ok(!$("m2-tct-bat-dau").disabled, "S2: nút tải phải mở lại sau khi xong");
  // mở thư mục / xem manifest / xem hóa đơn
  nut($("m2-tct-ket-qua"), "Mở thư mục Mua vào 2026-09").click(); await chay();
  const mo = cho(post(API + "/mo-thu-muc"), "S2 POST mở thư mục");
  assert.deepStrictEqual(JSON.parse(mo.opts.body), {run: HANDLE, run_rel: RUN_REL});
  mo.resolve(phanHoi(200, {da_mo: true})); await chay();
  nut($("m2-tct-ket-qua"), "Xem manifest Mua vào 2026-09").click(); await chay();
  cho(get(`${API}/manifest?run=${HANDLE}&run_rel=${encodeURIComponent(RUN_REL)}`), "S2 GET manifest").resolve(phanHoi(200, {run_rel: RUN_REL, nguon: "TAI_MOI", ky: "2026-09",
    chieu: "purchase", trang_thai: "COMPLETE", tong: {tong_hd: 8, xml_ok: 7, khong_xml_goc: 1, xml_loi: 0, pdf_loi: 0, bang_ke_trang_thai: "OK"},
    dang_nhap: {captcha_da_go: {trang_thai: "UNKNOWN", gia_tri: null}, token_tai_su_dung: {trang_thai: "UNKNOWN", gia_tri: null}, thoi_gian_cho_dang_nhap_giay: {trang_thai: "UNKNOWN", gia_tri: null}},
    nhom: [], loi_chung: []})); await chay();
  assert.ok(ketQua().includes("Manifest Mua vào 2026-09 — COMPLETE (tải mới)") && ketQua().includes("chưa đo"), "S2: thiếu bảng manifest: " + ketQua());
  nut($("m2-tct-ket-qua"), "Xem hóa đơn của kỳ").click();
  assert.deepStrictEqual([$("m2-loc-pn").value, $("m2-loc-ky").value, loc.length], ["DEMO_A", "2026-09", 1], "S2: chuyển sang danh sách hóa đơn của kỳ");
  // lần tải sau: khóa MỚI
  $("m2-tct-form").dispatch("submit"); await chay();
  const bd2 = cho(post(API + "/bat-dau"), "S2 POST lần hai");
  assert.notStrictEqual(JSON.parse(bd2.opts.body).khoa, khoa1, "S2: lần tải mới phải có khóa mới");
  bd2.resolve(phanHoi(409, {error: "M2_00B_JOB_BUSY", message: "Bộ tải #7 từ chối yêu cầu.", goi_y: "Bộ tải đang chạy một lần tải khác. Đợi lần đó xong rồi tải tiếp."})); await chay();
  assert.ok(tienTrinh().includes("Bộ tải #7 từ chối yêu cầu. (mã M2_00B_JOB_BUSY, HTTP 409)") && tienTrinh().includes("Gợi ý: Bộ tải đang chạy một lần tải khác"), "S2: lỗi API phải hiện mã + HTTP + gợi ý: " + tienTrinh());
  assert.ok(!$("m2-tct-bat-dau").disabled, "S2: sau lỗi bắt đầu phải bấm lại được");
  console.log("S2 đạt");

  // ---------------------------------------------------------------- S3 lỗi cổng thuế / lỗi nhận hiện rõ
  {
    $("m2-tct-form").dispatch("submit"); await chay();
    const k409 = JSON.parse(calls.filter(post(API + "/bat-dau")).slice(-2)[0].opts.body).khoa;
    const bd = cho(post(API + "/bat-dau"), "S3 POST");
    assert.strictEqual(JSON.parse(bd.opts.body).khoa, k409, "S3: lỗi 409 giữ khóa (cùng một lần tải)");
    bd.resolve(phanHoi(200, {run_handle: HANDLE, trang_thai: "STARTED"})); await chay();
    const s = cho(sseUrl, "S3 SSE"), L = luong(s.opts.signal);
    s.resolve(phanHoi(200, null, L.body)); await chay();
    L.day(sk(1, "error", {code: "LOGIN_TIMEOUT", goi_y: "Quá hạn chờ đăng nhập (8 phút). Tải lại và gõ captcha trong cửa sổ Chrome kịp hạn."}) + sk(2, "done", {trang_thai: "FAILED", so_run: 1}) + khung("ket-thuc", {ly_do: "DONE"})); await chay();
    assert.ok(tienTrinh().includes("Mã lỗi LOGIN_TIMEOUT"), "S3: lỗi trong luồng phải hiện nguyên mã: " + tienTrinh());
    cho(get(`${API}/trang-thai?run=${HANDLE}`), "S3 trạng thái").resolve(phanHoi(200, REPLAY("FAILED", [{ky: "2026-09", chieu: "purchase", run_rel: RUN_REL, trang_thai: "FAILED", loi: [
      {code: "LIST_FAILED", stage: "LIST", http_status: 401, goi_y: "Token cổng thuế đã hết hạn. Bấm “Tải từ cổng thuế” lại."},
      {code: "LIST_FAILED", stage: "LIST", http_status: 404, goi_y: "Cổng thuế có thể đã đổi API. Dừng tải; báo Claude sửa config.js của bộ tải."}]}]))); await chay();
    const kq = ketQua();
    assert.ok(kq.includes("Lần tải không hoàn tất (FAILED)"), "S3: " + kq);
    assert.ok(kq.includes("Mua vào 2026-09: mã lỗi LIST_FAILED · giai đoạn LIST · HTTP 401") && kq.includes("Token cổng thuế đã hết hạn"), "S3: lỗi 401: " + kq);
    assert.ok(kq.includes("HTTP 404") && kq.includes("đổi API"), "S3: lỗi 404: " + kq);
    assert.strictEqual(conLai(post(API + "/nhan")).length + calls.filter(post(API + "/nhan")).length, 1, "S3: lần FAILED không được gọi nhận (chỉ có lần nhận của S2)");
    assert.ok(!$("m2-tct-bat-dau").disabled, "S3: phải tải lại được");
    // lần PARTIAL: nhận và hiện ngoại lệ
    $("m2-tct-form").dispatch("submit"); await chay();
    cho(post(API + "/bat-dau"), "S3b POST").resolve(phanHoi(200, {run_handle: HANDLE, trang_thai: "STARTED"})); await chay();
    const s2 = cho(sseUrl, "S3b SSE"), L2 = luong(s2.opts.signal);
    s2.resolve(phanHoi(200, null, L2.body)); L2.day(khung("ket-thuc", {ly_do: "DONE"})); await chay();
    cho(get(`${API}/trang-thai?run=${HANDLE}`), "S3b trạng thái").resolve(phanHoi(200, REPLAY("PARTIAL", [{...RUN_OK, trang_thai: "PARTIAL"}]))); await chay();
    const nh = cho(post(API + "/nhan"), "S3b nhận");
    nh.resolve(phanHoi(200, {...NHAN_OK, tom_tat: {moi: 0, doi_trang_thai: 0, khong_ma: 0, loi: 2, khong_doi: 0, giu_cho_tien_te: 1}, runs: [{run_rel: RUN_REL, ky: "2026-09", chieu: "purchase",
      ngoai_le: [{ma: "TAI_LOI", item_ordinal: 1, loi: {code: "EXPORT_XML_FAILED", stage: "EXPORT_XML", http_status: 429, goi_y: "Cổng thuế giới hạn tốc độ. Đợi vài phút rồi tải lại."}},
                 {ma: "RUN_PARTIAL", item_ordinal: null}]}]})); await chay();
    const k2 = ketQua();
    assert.ok(k2.includes("mới 0 · đổi trạng thái 0 · không mã 0 · lỗi 2 · giữ chờ tiền tệ 1"), "S3b: " + k2);
    assert.ok(k2.includes("TAI_LOI") && k2.includes("EXPORT_XML_FAILED · HTTP 429") && k2.includes("giới hạn tốc độ") && k2.includes("RUN_PARTIAL"), "S3b: ngoại lệ phải hiện: " + k2);
    // nhận lỗi (đang chạy / mất quyền) hiện mã + nút nhận lại
    $("m2-tct-form").dispatch("submit"); await chay();
    cho(post(API + "/bat-dau"), "S3c POST").resolve(phanHoi(200, {run_handle: HANDLE, trang_thai: "STARTED"})); await chay();
    const s3 = cho(sseUrl, "S3c SSE"), L3 = luong(s3.opts.signal);
    s3.resolve(phanHoi(200, null, L3.body)); L3.day(khung("ket-thuc", {ly_do: "DONE"})); await chay();
    cho(get(`${API}/trang-thai?run=${HANDLE}`), "S3c trạng thái").resolve(phanHoi(200, REPLAY("COMPLETE", [RUN_OK]))); await chay();
    cho(post(API + "/nhan"), "S3c nhận").resolve(phanHoi(403, {error: "KHONG_CO_QUYEN_PHAP_NHAN", message: "Vai hiện tại không có quyền với pháp nhân này.", goi_y: "Vai hiện tại không được tải hoặc xem pháp nhân này."})); await chay();
    assert.ok(ketQua().includes("Chưa nhận được kết quả vào M2") && ketQua().includes("KHONG_CO_QUYEN_PHAP_NHAN, HTTP 403"), "S3c: " + ketQua());
    assert.ok(nut($("m2-tct-ket-qua"), "Nhận lại"), "S3c: thiếu nút nhận lại");
    console.log("S3 đạt");
  }

  // ---------------------------------------------------------------- S4 mất kết nối khi bắt đầu → bấm lại cùng khóa; lỗi xác định → khóa mới
  {
    $("m2-tct-thang").value = "2026-08";
    $("m2-tct-form").dispatch("submit"); await chay();
    const a = cho(post(API + "/bat-dau"), "S4 POST 1"), ba = JSON.parse(a.opts.body);
    a.reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(tienTrinh().includes("Mất kết nối với ứng dụng trên máy") && tienTrinh().includes("MAT_KET_NOI"), "S4: " + tienTrinh());
    assert.ok(!$("m2-tct-bat-dau").disabled, "S4: phải bấm lại được");
    $("m2-tct-form").dispatch("submit"); await chay();
    const a2 = cho(post(API + "/bat-dau"), "S4 POST 2");
    assert.deepStrictEqual(JSON.parse(a2.opts.body), ba, "S4: gửi lại phải y nguyên (cùng khóa)");
    a2.resolve(phanHoi(403, {error: "M2_CLIENT_AUTHORITY", message: "Danh tính, pháp nhân do máy chủ xác định."})); await chay();
    $("m2-tct-form").dispatch("submit"); await chay();
    const a3 = cho(post(API + "/bat-dau"), "S4 POST 3");
    assert.notStrictEqual(JSON.parse(a3.opts.body).khoa, ba.khoa, "S4: sau lỗi xác định (403) phải dùng khóa mới");
    a3.resolve(phanHoi(200, {run_handle: HANDLE, trang_thai: "UNKNOWN", can_doi_soat: true, ma: "KHACH_KHONG_KET_NOI", goi_y: "Mất kết nối tới bộ tải. Bấm “Đối soát” để kiểm tra lần tải; đừng tải lại ngay."})); await chay();
    assert.ok(tienTrinh().includes("Chưa rõ bộ tải đã nhận lệnh hay chưa") && tienTrinh().includes("Bấm “Đối soát”"), "S4: " + tienTrinh());
    nut($("m2-tct-tien-trinh"), "Đối soát").click(); await chay();
    const ds = cho(post(API + "/doi-soat"), "S4 POST đối soát");
    assert.deepStrictEqual(JSON.parse(ds.opts.body), {run: HANDLE});
    ds.resolve(phanHoi(200, {run_handle: HANDLE, trang_thai: "NOT_FOUND", ket_qua: null, doi_soat: null})); await chay();
    assert.ok(ketQua().includes("chưa có lần tải này"), "S4: " + ketQua());
    console.log("S4 đạt");
  }

  // ---------------------------------------------------------------- S5 đổi vai giữa chừng
  {
    $("m2-tct-form").dispatch("submit"); await chay();
    cho(post(API + "/bat-dau"), "S5 POST").resolve(phanHoi(200, {run_handle: HANDLE, trang_thai: "STARTED"})); await chay();
    const s = cho(sseUrl, "S5 SSE"), L = luong(s.opts.signal);
    s.resolve(phanHoi(200, null, L.body)); await chay();
    L.day(sk(1, "log", {msg: "Vui long NHAP CAPTCHA"})); await chay();
    assert.ok(tienTrinh().includes("Chờ đăng nhập"));
    const m = vai.get("m2_tai_hoa_don");
    assert.ok(m, "S5: chưa đăng ký vào cổng đổi vai");
    m.xoa();  // đồng bộ, trước mọi await
    assert.ok(s.opts.signal.aborted, "S5: luồng SSE phải bị hủy");
    assert.strictEqual(tienTrinh() + ketQua() + $("m2-tct-bo-tai").textContent, "", "S5: DOM phải xóa đồng bộ");
    assert.ok($("m2-tct-form").classList.contains("hidden"));
    L.day(sk(2, "done", {trang_thai: "COMPLETE", so_run: 1})); await chay();
    assert.strictEqual(conLai(c => c.url.startsWith(`${API}/trang-thai`)).length, 0, "S5: phản hồi muộn không được kéo theo GET trạng thái");
    assert.strictEqual(tienTrinh(), "", "S5: phản hồi muộn vẽ lại");
    m.nap(); await chay();
    cho(get(API), "S5 GET sau đổi vai").resolve(phanHoi(200, TT([MUC("DEMO_A", "MST_0100000001")], true))); await chay();
    assert.strictEqual($("m2-tct-phap-nhan").children.length, 1, "S5: phải nạp lại theo vai mới (1 pháp nhân)");
    assert.ok(!$("m2-tct-form").classList.contains("hidden"));
    console.log("S5 đạt");
  }

  // ---------------------------------------------------------------- S6 bộ tải chết giữa chừng → Kiểm tra lại tiếp tục từ con trỏ cũ
  {
    $("m2-tct-form").dispatch("submit"); await chay();
    cho(post(API + "/bat-dau"), "S6 POST").resolve(phanHoi(200, {run_handle: HANDLE, trang_thai: "STARTED"})); await chay();
    const s = cho(sseUrl, "S6 SSE"), L = luong(s.opts.signal);
    s.resolve(phanHoi(200, null, L.body)); await chay();
    L.day(sk(1, "log", {msg: "x"}) + sk(2, "progress", {type: "purchase", monthTag: "2026-09", index: 1, total: 4})); await chay();
    L.ket(); await chay();
    cho(get(`${API}/trang-thai?run=${HANDLE}`), "S6 trạng thái lỗi").resolve(phanHoi(503, {error: "M2_00B_NODE_CHUA_SAN_SANG", message: "Bộ tải #7 sở hữu chưa sẵn sàng (chưa cấu hình/khởi động).", goi_y: "Bộ tải chưa mở. Bấm “Mở bộ tải” trước khi tải."})); await chay();
    assert.ok(tienTrinh().includes("M2_00B_NODE_CHUA_SAN_SANG, HTTP 503") && tienTrinh().includes("Gợi ý: Bộ tải chưa mở"), "S6: " + tienTrinh());
    nut($("m2-tct-tien-trinh"), "Kiểm tra lại").click(); await chay();
    const s2 = cho(sseUrl, "S6 SSE lại");
    assert.strictEqual(s2.url, `${API}/su-kien?run=${HANDLE}&cursor=2`, "S6: phải đọc tiếp từ con trỏ cũ");
    const L2 = luong(s2.opts.signal);
    s2.resolve(phanHoi(200, null, L2.body)); L2.day(khung("ket-thuc", {ly_do: "DONE"})); await chay();
    cho(get(`${API}/trang-thai?run=${HANDLE}`), "S6 trạng thái 2").resolve(phanHoi(200, {run_handle: HANDLE, trang_thai: "RUNNING"})); await chay();
    assert.ok(tienTrinh().includes("Đang tải 1/4"), "S6: vẫn hiện bước đang tải: " + tienTrinh());
    $("m2-tct-form").children; // không làm gì thêm
    const huy = vai.get("m2_tai_hoa_don"); huy.xoa();  // dọn: hủy vòng chờ còn treo
    console.log("S6 đạt");
  }

  await chay(4);
  assert.deepStrictEqual(loiNgoai.map(String), [], "có promise bị từ chối không xử lý");
  console.log("m2_00e_giao_dien_async: TẤT CẢ ĐẠT");
  process.exit(0);
}

main().catch(e => { console.error(e && e.stack || e); process.exit(1); });
