"use strict";
// DA-2a/DA-2b1/DA-2b2: chạy app.js + crm_g.js thật với DOM/fetch giả, không mạng/server/CSDL.
// node tests/crm_du_an_ban_async.cjs
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const ROOT = path.resolve(__dirname, ".."), ASSETS = path.join(ROOT, "src/kho_tri_thuc/giao_dien/assets");
const APP = fs.readFileSync(path.join(ASSETS, "app.js"), "utf8"), CRMG = fs.readFileSync(path.join(ASSETS, "crm_g.js"), "utf8");
const IDS = new Set([...fs.readFileSync(path.join(ASSETS, "index.html"), "utf8").matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const loiNgoai = []; process.on("unhandledRejection", e => loiNgoai.push(e));
function moiTruong() {
  const reg = new Map(), dongId = new Set(); let taoTinh = false;
  class El {
    constructor(tag) { this.tagName = String(tag).toUpperCase(); this.children = []; this.parent = null; this._text = ""; this._id = ""; this.listeners = {}; this.attrs = {}; this.dataset = {}; this.style = {}; this._cls = new Set(); this.files = []; this.disabled = false; this.checked = false; this.selected = false; this._value = ""; this._valueSet = false; }
    get id() { return this._id; } set id(v) { this._id = v; if (!reg.has(v)) reg.set(v, []); reg.get(v).push(this); if (!taoTinh) dongId.add(v); }
    get isConnected() { for (let e = this; e; e = e.parent) if (e === body) return true; return false; }
    get className() { return [...this._cls].join(" "); } set className(v) { this._cls = new Set(String(v || "").split(/\s+/).filter(Boolean)); }
    get classList() { return {add: (...c) => c.forEach(x => this._cls.add(x)), remove: (...c) => c.forEach(x => this._cls.delete(x)), contains: c => this._cls.has(c), toggle: (c, on) => { const v = on === undefined ? !this._cls.has(c) : on; if (v) this._cls.add(c); else this._cls.delete(c); return v; }}; }
    get value() { if (this.tagName === "SELECT" && !this._valueSet) return (this.children.find(x => x.selected) || this.children[0])?.value || ""; return this._value; } set value(v) { this._value = String(v ?? ""); this._valueSet = true; }
    get textContent() { return this._text + this.children.map(c => c.textContent).join(""); } set textContent(v) { for (const c of this.children) c.parent = null; this.children = []; this._text = String(v ?? ""); }
    set innerHTML(_) { throw Error("Không được chèn HTML thô"); } set outerHTML(_) { throw Error("Không được chèn HTML thô"); } insertAdjacentHTML() { throw Error("Không được chèn HTML thô"); }
    _con(n) { const c = typeof n === "string" ? Object.assign(new El("#text"), {_text: n}) : n; if (c.parent) c.remove(); c.parent = this; return c; }
    append(...n) { n.forEach(x => this.children.push(this._con(x))); } prepend(...n) { this.children.unshift(...n.map(x => this._con(x))); }
    replaceChildren(...n) { this.textContent = ""; this.append(...n); } remove() { if (this.parent) this.parent.children = this.parent.children.filter(x => x !== this); this.parent = null; }
    addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); } dispatch(t, ev = {}) { return (this.listeners[t] || []).map(fn => fn({preventDefault() {}, target: this, key: "", ...ev})); } click() { return this.dispatch("click"); }
    setAttribute(k, v) { this.attrs[k] = String(v); } getAttribute(k) { return this.attrs[k] ?? null; } removeAttribute(k) { delete this.attrs[k]; } focus() {} showModal() { assert.ok(this.isConnected); this.open = true; } close() { this.open = false; }
  }
  const body = new El("body"), document = {body, title: "", createElement: t => new El(t), createTextNode: t => Object.assign(new El("#text"), {_text: String(t)}), querySelector: s => s.includes("ktt-token") ? {content: "TOKEN-DA-THU"} : null, querySelectorAll: () => [],
    getElementById: id => { const ds = (reg.get(id) || []).filter(e => e.isConnected); if (ds.length) return ds.at(-1); if (dongId.has(id) || !IDS.has(id)) return null; taoTinh = true; const e = new El("div"); e.id = id; taoTinh = false; body.append(e); return e; }};
  const calls = [], ctx = {document, Node: El, console, URLSearchParams, Date, Intl, Promise, Map, Set, JSON, Math, Number, String, Object, Array, Error, TypeError, SyntaxError, encodeURIComponent, decodeURIComponent, isNaN,
    location: {hash: "#hopdong"}, setTimeout: () => 1, clearTimeout() {}, navigator: {}, crypto: {randomUUID: () => "uuid-thu"}, URL: {createObjectURL: () => "blob:thu", revokeObjectURL() {}},
    fetch: (url, opts = {}) => new Promise((resolve, reject) => calls.push({url, opts, resolve, reject, method: opts.method || "GET"}))};
  ctx.window = ctx; ctx.addEventListener = () => {}; vm.createContext(ctx);
  vm.runInContext(APP, ctx, {filename: "app.js"}); vm.runInContext(CRMG, ctx, {filename: "crm_g.js"});
  return {ctx, calls, $: id => document.getElementById(id)};
}
const ALL = (r, p) => [r, ...(r?.children || []).flatMap(c => ALL(c, p))].filter(e => e && p(e));
const nut = (r, s) => ALL(r, e => e.tagName === "BUTTON" && e.textContent === s)[0];
const phanHoi = (data, status = 200) => ({ok: status >= 200 && status < 300, status, json: async () => data});
const chay = async () => { for (let i = 0; i < 14; i++) await Promise.resolve(); };
const A = "11111111-1111-4111-8111-111111111111", B = "22222222-2222-4222-8222-222222222222", LH = "33333333-3333-4333-8333-333333333333";
const URL_DA = "/api/crm/du-an-ban", TITLE = "<b>Dự án A</b>";
const DM = {thue_suat: [{ma: "10", nhan: "Thuế suất 10%"}, {ma: "KCT", nhan: "Không chịu thuế"}], tien_te: [{ma: "USD", nhan: "USD"}, {ma: "VND", nhan: "VND (đ)"}], loai_phi: [{ma: "BAO_TRI", nhan: "Phí bảo trì"}, {ma: "SU_DUNG", nhan: "Phí sử dụng"}, {ma: "KHAC", nhan: "Phí khác"}], don_vi_tinh: [{ma: "M2_NAM", nhan: "m²/năm"}, {ma: "M2_THANG", nhan: "m²/tháng"}, {ma: "LAN", nhan: "lần"}], trang_thai_lo: [{ma: "CON_TRONG", nhan: "Còn trống"}, {ma: "GIU_CHO", nhan: "Đang giữ chỗ"}, {ma: "DA_BAN", nhan: "Đã bán/cho thuê"}, {ma: "KHONG_BAN", nhan: "Tạm không bán"}]};
const ds = (chi = false) => ({duoc_sua: false, danh_muc: DM, du_an_ban: [{da_ban_id: A, du_an_id: "da-id-ky-thuat", du_an_ma: "MA_DU_AN_KY_THUAT", du_an_ten: TITLE, phien_ban: 2, dang_ban: true, don_gia_niem_yet: "999", don_gia_hien_thi: "120 USD/m²", so_phi: 2, so_lo: 4, duoc_sua: false}, ...(!chi ? [{da_ban_id: B, du_an_ten: "Dự án B", phien_ban: 1, dang_ban: false, don_gia_hien_thi: "35.000.000 đ/m²", so_phi: 0, so_lo: 0, duoc_sua: true}] : [])], du_an_chua_ban: [{du_an_id: "khong-hien", du_an_ten: "Dự án chưa bật bán không hiện"}], loai_hinh: []});
const pbs = [{id: "pb-id-1", phien_ban: 1, hieu_luc_tu: "2026-09-01", hieu_luc_den: "2026-10-25", hieu_luc_tu_hien_thi: "01/09/2026", hieu_luc_den_hien_thi: "25/10/2026", lap_boi: "DEMO_BH", ly_do: "Lập mới"}, {id: "pb-id-2", phien_ban: 2, hieu_luc_tu: "2026-10-25", hieu_luc_den: null, hieu_luc_tu_hien_thi: "25/10/2026", lap_boi: "Chị Lan", ly_do: "Sửa phí <b>giữ nguyên</b>"}];
const phi = [{ten: "Phí <b>bảo trì</b>", loai: "BAO_TRI", muc: "0.5", don_vi_tinh: "M2_NAM", tien_te: "USD", co_so_tinh: "Diện tích thuê"}, {ten: "Phí sử dụng", loai: "SU_DUNG", muc: "15000", don_vi_tinh: "M2_THANG", tien_te: "VND", co_so_tinh: "Diện tích thông thủy"}];
const ct = (n = 2, da = A) => ({da_ban_id: da, du_an_id: "da-id-ky-thuat", danh_muc: DM, phien_ban_ds: pbs, duoc_sua: false,
  anh_chup: {du_an: {ma: "MA_DU_AN_KY_THUAT", ten: TITLE}, phien_ban: {id: "pb-id-" + n, so: n}, trang_thai: "DANG_BAN", thong_tin: {vi_tri: n === 1 ? "Vị trí cũ" : "Khu A <b>vị trí</b>", mo_ta: "Mô tả <b>nguyên văn</b>"}, don_gia: "999", tien_te: "USD", loai_hinh: {id: LH, ma: "MA_LOAI_HINH_KY_THUAT"}, thue: {thue_suat: n === 1 ? "KCT" : "10", gia_chua_gom_vat: true}, gia_dat_tru: "999", phi: phi.map((r, i) => ({...r, thu_tu: i + 1, co_so_tinh: i ? null : r.co_so_tinh})),
    lo: DM.trang_thai_lo.map((v, i) => ({id: "lo-id-" + i, ma: "A-0" + i, dien_tich: "1234.5", trang_thai: v.ma, lan: i + 1})),
    bo_chuan: {trang_thai: "HIEU_LUC", nguon: "AP_DUNG_NGAY", giai_doan: "GD_MA_KY_THUAT", giai_doan_hien_thi: "Thanh toán khi bàn giao", version: {id: "g7-id", phien_ban: n, valid_from: n === 1 ? "2026-09-01" : "2026-10-25", valid_to: n === 1 ? "2026-10-25" : null},
      rows: [{lan: "1", gia_tri_loai: "PERCENT", gia_tri_thap_phan: "30", moc_loai: "NGAY", moc_ngay: "2026-11-05", ghi_chu: "Đợt <b>một</b>"}, {lan: "2", gia_tri_loai: "PERCENT", gia_tri_thap_phan: "70", moc_loai: "SU_KIEN", moc_su_kien: "SAU_KY_90"}, {lan: "3", gia_tri_loai: "AMOUNT", so_tien_minor: "5", tien_te: "USD", moc_loai: "SU_KIEN", moc_su_kien: "BAN_GIAO"}, {lan: "4", gia_tri_loai: "AMOUNT", so_tien_minor: "123456789012345678901234", tien_te: "VND", moc_loai: "SU_KIEN", moc_su_kien: "SU_KIEN_CHUA_CO_NHAN"}, {lan: "5", gia_tri_loai: "AMOUNT", so_tien_minor: "1500000000", tien_te: "VND"}]}} ,
  hien_thi: {trang_thai: "Đang bán", don_gia: n === 1 ? "100 USD/m²" : "120 USD/m²", thue: "Giá chưa gồm VAT · Thuế suất 10%", gia_dat_tru: "24 USD/m²", bo_chuan_dong: ["30%", "70%", "0,05 USD", "123.456.789.012.345.678.901.234 đ", "1.500.000.000 đ"].map(gia_tri_hien_thi => ({gia_tri_hien_thi})), loai_hinh: "Cho thuê đất", phien_ban: `Phiên bản ${n} — hiệu lực từ ${n === 1 ? "01/09/2026" : "25/10/2026"}`, phi: [{loai: "Phí bảo trì", muc: "0,5 USD/m²/năm"}, {loai: "Phí sử dụng", muc: "15.000 đ/m²/tháng"}], lo: DM.trang_thai_lo.map((v, i) => ({ma: "A-0" + i, dien_tich: "1.234,5 m²", trang_thai: v.nhan}))}});
const MOC = {moc: [{ma: "BAN_GIAO", nhan: "Bàn giao"}], moc_tham_so: [{mau_ma: "SAU_KY_<n>", nhan: "Sau ký + n ngày"}]};
const noiDung = (gia, dongBan = true) => ({dang_ban: dongBan, thong_tin: {vi_tri: "A", don_gia_niem_yet: gia, tien_te: "USD", loai_hinh_id: LH, thue_suat: gia === "100" ? "KCT" : "10", gia_dat_tru: gia === "100" ? "0" : "24", giai_doan_g7: "GD1"}, phi: gia === "100" ? [] : phi});
const ls = () => ({phien_ban: [{...pbs[1], noi_dung: noiDung("120", false)}, {...pbs[0], noi_dung: noiDung("100")}], su_kien: [{luc: "2026-10-25T09:00:00Z", nguoi: "Chị Lan", hanh_dong: "CRM_CHUAN_AP_DUNG", ly_do: "Áp dụng theo quyết định"}, {luc: "2026-10-24T20:00:00Z", nguoi: A, hanh_dong: "CRM_DA_NGUNG_BAN", hanh_dong_hien_thi: "Ngừng bán", ly_do: "Tạm ngừng <b>nguyên văn</b>"}, {luc: "2026-10-25T08:00:00Z", nguoi: "Chị Lan", hanh_dong: "CRM_DA_MO_BAN_LAI", ly_do: "Mở lại"}], lo: [{lo_id: "lo-id-0", ma: "A-00", lich_su: [{lan: 1, hieu_luc_tu: "2026-09-01", hieu_luc_den: "2026-10-25", dien_tich: "999", dien_tich_hien_thi: "1.234,5 m²", trang_thai: "CON_TRONG", tao_boi: "DEMO_BH", ghi_chu: "Lô <b>nguyên văn</b>"}, {lan: 2, hieu_luc_tu: "2026-10-25", dien_tich: "999", dien_tich_hien_thi: "1.234,5 m²", trang_thai: "GIU_CHO", tao_boi: "Chị Lan"}]}], tien_do: [
  {giai_doan: "GD1", phien_ban: 2, trang_thai: "HIEU_LUC", valid_from: "2026-10-25", ap_dung_boi: "Chị Lan", nguon: "AP_DUNG_NGAY", can_cu: "QD-20261025-07"},
  {giai_doan: "GD1", phien_ban: 1, trang_thai: "HIEU_LUC", valid_from: "2026-09-01", duyet_boi: "DEMO_CFO", nguon: "CFO_DUYET"},
  {giai_doan: "NHAP_KHONG_HIEN", trang_thai: "DRAFT"},
  {giai_doan: "CUNG_NGAY_KHONG_HIEN", trang_thai: "HIEU_LUC", khoang_rong: true}
]});

async function kiemGhi(dat) {
  const {ctx, calls, $} = moiTruong(), da = () => $("crmg-da"), goc = () => $("crm-g");
  for (const c of calls) { c.xong = true; c.resolve(phanHoi({message: "Module khác"}, 404)); } await chay();
  const cho = (url, method = "GET") => { const c = calls.find(x => !x.xong && x.url === url && x.method === method); assert.ok(c, method + " " + url); c.xong = true; return c; };
  const tra = async (url, data, status) => { cho(url).resolve(phanHoi(data, status)); await chay(); };
  const lenh = () => calls.filter(c => c.method === "POST");
  const nhap = (k, v) => { const el = $("crmg-da-f-" + k); assert.ok(el, k); el.value = v; el.dispatch("input"); };
  const click = text => { const b = nut(da(), text); assert.ok(b, text); b.click(); };
  const ghi = async (hanh, data, status = 200) => { const c = cho(URL_DA + "/" + hanh, "POST"); c.resolve(phanHoi(data, status)); await chay(); return JSON.parse(c.opts.body); };
  const dsGhi = (n = 2, dang = true) => ({...ds(), duoc_sua: true, du_an_ban: [{...ds().du_an_ban[0], duoc_sua: true, phien_ban: n, dang_ban: dang}],
    du_an_chua_ban: [{du_an_id: "du-an-moi-id", du_an_ten: "Dự án mới <b>nguyên văn</b>"}], loai_hinh: [{id: LH, ma: "KHONG_HIEN_MA", ten: "Cho thuê đất"}]});
  const ctGhi = (n = 2, dang = true) => { const d = ct(n); return {...d, duoc_sua: true,
    phien_ban_ds: [...pbs.filter(v => v.phien_ban < n).map(v => ({...v, hieu_luc_den: "2026-10-25"})), {...pbs[1], phien_ban: n}],
    anh_chup: {...d.anh_chup, don_gia: "1234.5", gia_dat_tru: "1000.25", giai_doan_g7: "GD1", trang_thai: dang ? "DANG_BAN" : "NGUNG_BAN"}}; };
  const sauLuu = async (n, dang = true) => { await tra(URL_DA, dsGhi(n, dang)); await tra(URL_DA + "/" + A, ctGhi(n, dang)); };
  nut(goc(), "Dự án đang bán").click(); await tra(URL_DA, ds());
  assert.equal(nut(da(), "Thêm dự án đang bán"), undefined);
  ALL(da(), e => e.className === "da-dong")[0].click(); await tra(URL_DA + "/" + A, ct()); await tra("/api/crm/bao-gia/moc-chuan", MOC);
  for (const t of ["Sửa thông tin", "Sửa phí", "Sửa lô/căn", "Sửa tiến độ tiêu chuẩn", "Ngừng bán", "Mở bán lại"]) assert.equal(nut(da(), t), undefined);
  dat("Không có duoc_sua không thấy nút ghi");

  nut(goc(), "↻ Làm mới").click();
  // DTO máy chủ thực tế chưa có quyền tổng; chỉ trả các dự án chưa bán được phép ghi.
  const thucTe = dsGhi(); delete thucTe.duoc_sua; await tra(URL_DA, thucTe); await tra(URL_DA + "/" + A, ctGhi());
  click("Thêm dự án đang bán");
  const f = $("crmg-da-form");
  for (const t of ["Vị trí", "Mô tả", "/m² (chưa gồm VAT)", "Tiền tệ", "Loại hình", "Thuế suất", "Giá đất được trừ /m²", "Giai đoạn tiến độ mặc định", "Lý do (bắt buộc)"]) assert.ok(f.textContent.includes(t), t);
  assert.equal($("crmg-da-f-thue_suat").value, "10");
  assert.deepEqual(ALL($("crmg-da-f-thue_suat"), e => e.tagName === "OPTION").map(e => e.textContent), DM.thue_suat.map(v => v.nhan));
  assert.ok(f.textContent.includes("Dự án mới <b>nguyên văn</b>"));
  for (const t of ["du-an-moi-id", "KHONG_HIEN_MA", LH]) assert.ok(!f.textContent.includes(t));
  click("Lưu thông tin"); assert.equal(lenh().length, 0); assert.ok($("crmg-da-f-ly_do-loi").textContent);
  nhap("du_an_id", "du-an-moi-id"); nhap("loai_hinh_id", LH); nhap("vi_tri", "Vị trí mới"); nhap("mo_ta", "Mô tả <b>an toàn</b>");
  nhap("don_gia_niem_yet", "1.234,5"); nhap("gia_dat_tru", "1.000,25"); nhap("giai_doan_g7", "GD1"); nhap("ly_do", " Bắt đầu bán ");
  click("Lưu thông tin"); click("Lưu thông tin"); assert.equal(lenh().length, 1, "Không gửi lặp lúc đang chờ");
  const moi = await ghi("bat-ban", {da_ban_id: A, phien_ban: 3, lap_lai: false});
  assert.deepEqual(moi, {du_an_id: "du-an-moi-id", thong_tin: {vi_tri: "Vị trí mới", mo_ta: "Mô tả <b>an toàn</b>", don_gia_niem_yet: "1234.5", tien_te: "VND", loai_hinh_id: LH, thue_suat: "10", gia_dat_tru: "1000.25", giai_doan_g7: "GD1"}, phi: [], ly_do: "Bắt đầu bán", khoa: "crmg-uuid-thu"});
  await sauLuu(3); assert.equal($("crmg-da-form"), null); assert.equal($("crmg-da-phien-ban").value, "3");
  dat("Bật bán: form đúng, lý do bắt buộc, thuế mặc định 10, số Việt thành chuỗi ASCII, tải phiên bản mới");

  nut(goc(), "↻ Làm mới").click();
  const loaiMoi = dsGhi(3); loaiMoi.loai_hinh[0].id = LH + "-moi";
  await tra(URL_DA, loaiMoi); await tra(URL_DA + "/" + A, ctGhi(3));
  click("Sửa thông tin"); assert.equal($("crmg-da-f-loai_hinh_id").value, "");
  nhap("ly_do", "Chọn phiên bản loại hình mới");
  const truocLoai = lenh().length;
  for (const v of ["", LH]) {
    nhap("loai_hinh_id", v); click("Lưu thông tin"); assert.equal(lenh().length, truocLoai);
    assert.equal($("crmg-da-f-loai_hinh_id").getAttribute("aria-invalid"), "true");
    assert.equal($("crmg-da-f-loai_hinh_id-loi").textContent, "Cần chọn loại hình.");
  }
  nhap("loai_hinh_id", LH + "-moi"); click("Lưu thông tin");
  assert.equal((await ghi("cap-nhat", {error: "CRM_DA_YEU_CAU_SAI", truong: "ly_do", message: "Thử danh mục"}, 400)).thong_tin.loai_hinh_id, LH + "-moi");
  click("Hủy"); nut(goc(), "↻ Làm mới").click(); await sauLuu(3);
  dat("Loại hình cũ về rỗng, chặn cả id ngoài danh mục; chỉ gửi phiên bản mới đã chọn");

  click("Sửa thông tin");
  assert.equal($("crmg-da-f-don_gia_niem_yet").value, "1.234,5"); assert.equal($("crmg-da-f-gia_dat_tru").value, "1.000,25"); assert.equal($("crmg-da-f-giai_doan_g7").value, "GD1");
  nhap("ly_do", "Sửa thông tin"); nhap("vi_tri", "Nội dung đang gõ");
  const dem = lenh().length;
  for (const sai of ["1e6", "١٢٣", "1.23", "-1", "1,1234567890123"]) {
    nhap("don_gia_niem_yet", sai); click("Lưu thông tin"); assert.equal(lenh().length, dem); assert.equal($("crmg-da-f-don_gia_niem_yet").getAttribute("aria-invalid"), "true");
  }
  nhap("don_gia_niem_yet", "123456789012345678901234,123456789012");
  click("Lưu thông tin");
  const sua = await ghi("cap-nhat", {error: "CRM_DA_SO_SAI", truong: "thong_tin.gia_dat_tru", message: "Giá đất vượt đơn giá."}, 400);
  assert.equal(sua.expected_phien_ban, 3); assert.equal(sua.da_ban_id, A); assert.ok(!Object.hasOwn(sua, "phi"), "Không thay phí");
  assert.equal(sua.thong_tin.don_gia_niem_yet, "123456789012345678901234.123456789012", "Không qua float");
  assert.equal($("crmg-da-f-gia_dat_tru").getAttribute("aria-invalid"), "true"); assert.equal($("crmg-da-f-gia_dat_tru-loi").textContent, "Giá đất vượt đơn giá.");
  assert.equal($("crmg-da-f-vi_tri").value, "Nội dung đang gõ");
  nhap("gia_dat_tru", "0"); nhap("don_gia_niem_yet", "1.234,5"); click("Lưu thông tin");
  await ghi("cap-nhat", {error: "CRM_DA_YEU_CAU_SAI", truong: "ly_do", message: "Cần lý do cụ thể."}, 400);
  assert.equal($("crmg-da-f-ly_do-loi").textContent, "Cần lý do cụ thể.");
  dat("Sửa: nạp số/giai đoạn hiện hành, không gửi phí; lỗi số và HTTP 400 đỏ đúng ô, giữ nháp, không mất chính xác");

  nhap("ly_do", "Điều chỉnh theo quyết định"); click("Lưu thông tin");
  await ghi("cap-nhat", {error: "CRM_DA_PHIEN_BAN_CU", message: "Cũ"}, 409);
  assert.ok($("crmg-da-form").textContent.includes("Dự án vừa được người khác sửa — tải lại để xem bản mới"));
  assert.equal($("crmg-da-f-vi_tri").value, "Nội dung đang gõ"); assert.ok(nut(da(), "Lưu thông tin").disabled);
  assert.ok(!calls.some(c => !c.xong && c.url === URL_DA), "409 không tự tải mất nháp");
  click("Tải lại bản mới"); await sauLuu(4);
  assert.equal($("crmg-da-phien-ban").value, "4"); assert.equal($("crmg-da-f-vi_tri").value, "Nội dung đang gõ"); assert.ok(nut(da(), "Lưu thông tin").disabled);
  click("Hủy"); click("Sửa thông tin"); nhap("ly_do", "Đã xem bản mới"); click("Lưu thông tin");
  const suaMoi = await ghi("cap-nhat", {da_ban_id: A, phien_ban: 5, lap_lai: false}); assert.equal(suaMoi.expected_phien_ban, 4); await sauLuu(5);
  dat("409: thông báo chính xác, tải lại giữ nháp và chặn ghi đè; sửa lại dùng expected phiên bản mới");

  click("Ngừng bán"); await chay(); assert.equal($("crmg-da-form").getAttribute("role"), "dialog"); assert.equal($("crmg-da-form").tagName, "DIALOG"); assert.equal($("crmg-da-form").open, true);
  assert.ok($("crmg-da-form").textContent.includes("Xác nhận ngừng bán"));
  const truocDung = lenh().length; click("Xác nhận ngừng bán"); assert.equal(lenh().length, truocDung); click("Hủy"); assert.equal(lenh().length, truocDung);
  click("Ngừng bán"); nhap("ly_do", "Tạm dừng bán"); click("Xác nhận ngừng bán");
  assert.deepEqual(await ghi("ngung-ban", {da_ban_id: A, phien_ban: 6, lap_lai: false}), {da_ban_id: A, expected_phien_ban: 5, ly_do: "Tạm dừng bán", khoa: "crmg-uuid-thu"}); await sauLuu(6, false);
  assert.ok(nut(da(), "Mở bán lại")); assert.equal(nut(da(), "Ngừng bán"), undefined);
  click("Mở bán lại"); const truocMo = lenh().length; click("Xác nhận mở bán lại"); assert.equal(lenh().length, truocMo);
  nhap("ly_do", "Đã đủ điều kiện"); click("Xác nhận mở bán lại");
  assert.deepEqual(await ghi("mo-ban-lai", {da_ban_id: A, phien_ban: 7, lap_lai: false}), {da_ban_id: A, expected_phien_ban: 6, ly_do: "Đã đủ điều kiện", khoa: "crmg-uuid-thu"}); await sauLuu(7);
  assert.ok(nut(da(), "Ngừng bán"));
  dat("Ngừng/mở bán: xác nhận, Hủy không ghi, cả hai bắt buộc lý do, CAS và tải lại trạng thái/phiên bản");

  click("Sửa thông tin"); nhap("ly_do", "Thử mất mạng"); click("Lưu thông tin");
  const mat = cho(URL_DA + "/cap-nhat", "POST"), bodyGoc = mat.opts.body; mat.reject(new TypeError("Mất mạng")); await chay();
  assert.ok(nut(da(), "Lưu thông tin").disabled); assert.ok($("crmg-da-f-ly_do").disabled);
  click("Gửi lại y nguyên (cùng khóa)"); const lai = cho(URL_DA + "/cap-nhat", "POST"); assert.equal(lai.opts.body, bodyGoc);
  lai.resolve(phanHoi({lap_lai: true, da_ban_id: A, phien_ban: 8})); await chay(); await sauLuu(8);
  for (const c of lenh()) { assert.equal(c.opts.headers["X-KTT-Token"], "TOKEN-DA-THU"); assert.equal(c.opts.credentials, "same-origin"); assert.equal(c.opts.cache, "no-store"); }
  dat("Mất mạng: khóa idempotent và body giữ nguyên khi gửi lại; lệnh dùng token/phiên chung");

  click("Sửa phí");
  assert.ok($("crmg-da-form").textContent.includes("Mức chưa gồm VAT"));
  assert.equal($("crmg-da-f-phi.0.muc").value, "0,5");
  for (const [c, dm] of [["loai", "loai_phi"], ["don_vi_tinh", "don_vi_tinh"], ["tien_te", "tien_te"]]) {
    assert.deepEqual(ALL($("crmg-da-f-phi.0." + c), e => e.tagName === "OPTION").map(e => [e.value, e.textContent]), DM[dm].map(v => [v.ma, v.nhan]));
  }
  const truocPhi = lenh().length; click("Lưu phí"); assert.equal(lenh().length, truocPhi); assert.ok($("crmg-da-f-ly_do-loi").textContent);
  nhap("ly_do", " Điều chỉnh phí "); nhap("phi.0.muc", "1.234,5678"); click("Lưu phí"); click("Lưu phí");
  assert.equal(lenh().length, truocPhi + 1);
  const phi400 = await ghi("phi", {error: "CRM_DA_PHI_SAI", truong: "phi.0.muc", message: "Mức phí không phù hợp."}, 400);
  assert.deepEqual(phi400, {da_ban_id: A, expected_phien_ban: 8, phi: [{...phi[0], muc: "1234.5678"}, {...phi[1], co_so_tinh: ""}], ly_do: "Điều chỉnh phí", khoa: "crmg-uuid-thu"});
  assert.equal($("crmg-da-f-phi.0.muc").getAttribute("aria-invalid"), "true");
  assert.equal($("crmg-da-f-phi.0.muc-loi").textContent, "Mức phí không phù hợp.");
  assert.equal($("crmg-da-f-phi.0.muc").value, "1.234,5678");
  dat("Phí: đúng body/CAS, nhãn và đơn vị từ danh mục, lý do bắt buộc, 400 phi.0.muc đỏ đúng ô và giữ nháp");
  click("Thêm dòng phí"); nhap("phi.2.ten", "Phí khác"); nhap("phi.2.loai", "KHAC"); nhap("phi.2.muc", "50,25"); nhap("phi.2.don_vi_tinh", "LAN");
  ALL($("crmg-da-form"), e => e.tagName === "BUTTON" && e.textContent === "Bỏ dòng")[1].click();
  assert.equal($("crmg-da-f-phi.1.ten").value, "Phí khác"); assert.equal($("crmg-da-f-phi.1.don_vi_tinh").value, "LAN");
  click("Lưu phí"); const phi409 = await ghi("phi", {error: "CRM_DA_PHIEN_BAN_CU", message: "Cũ"}, 409);
  assert.equal(phi409.phi.length, 2); assert.equal(phi409.phi[1].muc, "50.25"); assert.equal(phi409.phi[1].don_vi_tinh, "LAN");
  assert.ok(nut(da(), "Lưu phí").disabled); assert.equal($("crmg-da-f-phi.1.ten").value, "Phí khác");
  click("Tải lại bản mới"); await sauLuu(8); assert.ok(nut(da(), "Lưu phí").disabled); click("Hủy");
  click("Sửa phí"); while (nut(da(), "Bỏ dòng")) click("Bỏ dòng"); nhap("ly_do", "Bỏ hết phí"); click("Lưu phí");
  assert.deepEqual((await ghi("phi", {da_ban_id: A, phien_ban: 8})).phi, []); await sauLuu(8);
  dat("Phí: thêm/bớt dòng và bỏ hết, giữ đơn vị lần; 409 giữ nháp và chặn ghi đè");

  click("Sửa lô/căn");
  assert.equal($("crmg-da-f-lo.0.ma").readOnly, true);
  assert.deepEqual(ALL($("crmg-da-f-lo.0.trang_thai"), e => e.tagName === "OPTION").map(e => e.textContent), DM.trang_thai_lo.map(v => v.nhan));
  assert.equal($("crmg-da-f-lo.0.dien_tich").value, "1.234,5");
  nhap("lo.0.trang_thai", "DA_BAN"); nhap("lo.1.trang_thai", "KHONG_BAN");
  click("Thêm lô/căn"); nhap("lo.4.ma", "A-MOI"); nhap("lo.4.dien_tich", "2.345,6789"); nhap("lo.4.ghi_chu", "Lô <b>mới</b>");
  click("Lưu lô/căn");
  const lo409 = await ghi("lo", {error: "CRM_DA_LO_LAN_CU", message: "lô/căn A-01 đã đổi (lần 3) — tải lại rồi sửa"}, 409);
  assert.deepEqual(Object.keys(lo409).sort(), ["da_ban_id", "lo", "khoa"].sort()); assert.equal(lo409.da_ban_id, A);
  assert.deepEqual(lo409.lo.slice(0, 4).map(r => r.expected_lan), [1, 2, 3, 4]);
  assert.equal(lo409.lo[0].trang_thai, "DA_BAN"); assert.equal(lo409.lo[1].trang_thai, "KHONG_BAN");
  assert.deepEqual(lo409.lo[4], {ma: "A-MOI", dien_tich: "2345.6789", trang_thai: "CON_TRONG", ghi_chu: "Lô <b>mới</b>"});
  assert.ok($("crmg-da-form").textContent.includes("A-01 đã đổi")); assert.equal($("crmg-da-f-lo.4.ma").value, "A-MOI"); assert.ok(nut(da(), "Lưu lô/căn").disabled);
  click("Tải lại bản mới"); await sauLuu(8); assert.equal($("crmg-da-f-lo.4.ma").value, "A-MOI"); click("Hủy");
  dat("Lô/căn: thêm mới, đổi trạng thái, số Việt và expected_lan từng lô; 409 chỉ rõ lô bị đổi và giữ nháp");
  click("Sửa lô/căn"); click("Thêm lô/căn"); click("Bỏ dòng"); assert.equal($("crmg-da-f-lo.4.ma"), null);
  nhap("lo.0.trang_thai", "GIU_CHO"); click("Lưu lô/căn");
  assert.equal((await ghi("lo", {da_ban_id: A})).lo[0].trang_thai, "GIU_CHO"); await sauLuu(8);
  dat("Lô/căn: bỏ dòng mới chưa lưu, lưu thành công và nạp lại chi tiết");

  click("Sửa tiến độ tiêu chuẩn");
  assert.ok($("crmg-da-form").textContent.includes("Áp dụng ngay, không cần CFO duyệt"));
  assert.ok($("crmg-da-form").textContent.includes("Giai đoạn đang sửa: Thanh toán khi bàn giao"));
  assert.ok(!$("crmg-da-form").textContent.includes("QD-") && !$("crmg-da-form").textContent.includes("GD_MA_KY_THUAT"));
  for (const [api, o] of [["lan", "lan"], ["gia_tri_loai", "gl"], ["gia_tri_thap_phan", "tp"], ["so_tien_minor", "st"], ["tien_te", "tt"], ["moc_loai", "ml"], ["moc_ngay", "mn"], ["moc_su_kien", "ms"], ["ghi_chu", "gc"]]) {
    click("Áp dụng tiến độ");
    await ghi("tien-do", {error: "CRM_G_YEU_CAU_SAI", truong: "dong.0." + api, message: "Cần kiểm tra dòng đầu."}, 400);
    assert.equal($("crmg-da-f-dong.0." + o).getAttribute("aria-invalid"), "true", api);
    assert.equal($("crmg-da-f-dong.0." + o + "-loi").textContent, "Cần kiểm tra dòng đầu.");
    assert.equal($("crmg-da-f-dong.1." + o).getAttribute("aria-invalid"), "false", "Không đỏ dòng khác");
    assert.equal($("crmg-da-f-dong.0.tp").value, "30");
  }
  dat("Tiến độ: hiện giai đoạn đang sửa, không mã quyết định; 400 dong.0.* đỏ đúng ô và giữ nháp");
  assert.equal($("crmg-da-f-dong.2.st").value, "0,05");
  assert.equal($("crmg-da-f-dong.3.st").value, "123.456.789.012.345.678.901.234");
  assert.ok($("crmg-da-f-dong.1.ms").textContent.includes("Sau ký + 90 ngày"));
  while (ALL($("crmg-da-form"), e => e.tagName === "BUTTON" && e.textContent === "Bỏ dòng").length > 2) {
    ALL($("crmg-da-form"), e => e.tagName === "BUTTON" && e.textContent === "Bỏ dòng").at(-1).click();
  }
  nhap("dong.0.tp", "30,5"); nhap("dong.0.gc", "Đợt đầu"); nhap("dong.1.gl", "AMOUNT"); nhap("dong.1.tt", "USD"); nhap("dong.1.st", "1.234,567");
  const truocTd = lenh().length; click("Áp dụng tiến độ"); assert.equal(lenh().length, truocTd); assert.ok($("crmg-da-f-dong.1.st-loi").textContent.includes("không tự làm tròn"));
  nhap("dong.1.st", "1.234,56"); click("Áp dụng tiến độ");
  const td409 = await ghi("tien-do", {error: "CRM_DA_PHIEN_BAN_CU", message: "Tiến độ đã đổi"}, 409);
  assert.deepEqual(td409, {du_an_id: "da-id-ky-thuat", giai_doan: "GD_MA_KY_THUAT", expected_version: 8, khoa: "crmg-uuid-thu", dong: [
    {lan: "1", gia_tri_loai: "PERCENT", gia_tri_thap_phan: "30.5", so_tien_minor: null, tien_te: null, moc_loai: "NGAY", moc_ngay: "2026-11-05", moc_su_kien: null, ghi_chu: "Đợt đầu"},
    {lan: "2", gia_tri_loai: "AMOUNT", gia_tri_thap_phan: null, so_tien_minor: "123456", tien_te: "USD", moc_loai: "SU_KIEN", moc_ngay: null, moc_su_kien: "SAU_KY_90", ghi_chu: null}]});
  assert.ok($("crmg-da-form").textContent.includes("Tiến độ tiêu chuẩn vừa được người khác sửa")); assert.ok(nut(da(), "Áp dụng tiến độ").disabled);
  assert.equal($("crmg-da-f-dong.0.tp").value, "30,5"); click("Tải lại bản mới"); await sauLuu(8); assert.equal($("crmg-da-f-dong.1.st").value, "1.234,56"); click("Hủy");
  dat("Tiến độ: body phần trăm/tiền/mốc và expected_version; không làm tròn, 409 giữ nháp và chặn ghi đè");
  click("Sửa tiến độ tiêu chuẩn"); click("Thêm đợt"); nhap("dong.5.tp", "10"); nhap("dong.5.ms", "BAN_GIAO"); click("Áp dụng tiến độ");
  const td = await ghi("tien-do", {du_an_id: "da-id-ky-thuat", phien_ban: 9}); assert.equal(td.dong.length, 6); assert.equal(td.dong[5].moc_su_kien, "BAN_GIAO"); await sauLuu(8);
  assert.equal($("crmg-da-form"), null);
  dat("Tiến độ: thêm đợt, chọn mốc tiếng Việt, áp dụng ngay và tải lại đúng dự án");

  nut(goc(), "↻ Làm mới").click(); await tra(URL_DA, dsGhi(8));
  const chuaCo = ctGhi(8); chuaCo.anh_chup.bo_chuan = null; await tra(URL_DA + "/" + A, chuaCo);
  click("Sửa tiến độ tiêu chuẩn"); nhap("dong.0.tp", "100"); nhap("dong.0.ms", "BAN_GIAO"); click("Áp dụng tiến độ");
  const matTd = cho(URL_DA + "/tien-do", "POST"), bodyTd = matTd.opts.body;
  assert.equal(JSON.parse(bodyTd).expected_version, 0); assert.equal(JSON.parse(bodyTd).giai_doan, "GD1");
  matTd.reject(new TypeError("Mất kết nối")); await chay(); assert.ok($("crmg-da-f-dong.0.tp").disabled);
  click("Gửi lại y nguyên (cùng khóa)"); const laiTd = cho(URL_DA + "/tien-do", "POST"); assert.equal(laiTd.opts.body, bodyTd);
  laiTd.resolve(phanHoi({du_an_id: "da-id-ky-thuat", lap_lai: true})); await chay(); await sauLuu(8);
  dat("Tiến độ chưa có: expected_version=0, giai đoạn mặc định; mất mạng gửi lại nguyên body và khóa");

  nut(goc(), "↻ Làm mới").click(); await tra(URL_DA, dsGhi(8));
  const thieuGiaiDoan = ctGhi(8); thieuGiaiDoan.anh_chup.bo_chuan = null; thieuGiaiDoan.anh_chup.giai_doan_g7 = null;
  await tra(URL_DA + "/" + A, thieuGiaiDoan);
  const truocThieu = lenh().length; click("Sửa tiến độ tiêu chuẩn");
  assert.equal($("crmg-da-form"), null); assert.equal(lenh().length, truocThieu);
  assert.ok(goc().textContent.includes("Cần đặt giai đoạn tiến độ mặc định trong Sửa thông tin"));
  nut(goc(), "↻ Làm mới").click(); await sauLuu(8);
  dat("Thiếu giai đoạn mặc định: báo trước khi mở form tiến độ, không gửi lệnh");

  for (const code of ["CRM_DA_TRANG_THAI", "CRM_DA_DA_CO", "CRM_XUNG_DOT_KHAC"]) {
    click("Sửa thông tin"); nhap("ly_do", "Nháp khi xung đột"); nhap("vi_tri", "Giữ nội dung " + code); click("Lưu thông tin");
    await ghi("cap-nhat", {error: code, message: "Dữ liệu vừa thay đổi."}, 409);
    assert.ok(nut(da(), "Tải lại bản mới")); assert.ok(nut(da(), "Lưu thông tin").disabled);
    assert.equal($("crmg-da-f-vi_tri").value, "Giữ nội dung " + code);
    assert.ok(!calls.some(c => !c.xong && c.url === URL_DA));
    click("Tải lại bản mới"); await sauLuu(8);
    assert.equal($("crmg-da-f-vi_tri").value, "Giữ nội dung " + code); assert.ok(nut(da(), "Lưu thông tin").disabled); click("Hủy");
  }
  dat("Mọi 409: trạng thái/đã có/mã khác đều giữ nháp, chặn lưu và có Tải lại bản mới");

  // Đọc phiên bản cũ rồi Sửa phải nạp lại hiện hành, không ghi từ ảnh chụp lịch sử.
  $("crmg-da-phien-ban").value = "1"; $("crmg-da-phien-ban").dispatch("change"); await tra(URL_DA + "/" + A + "?phien_ban=1", {...ct(1), duoc_sua: true});
  assert.equal(nut(da(), "Ngừng bán"), undefined); click("Sửa thông tin"); await sauLuu(8);
  assert.equal($("crmg-da-f-don_gia_niem_yet").value, "1.234,5"); click("Hủy");
  $("crmg-da-chi-dang-ban").checked = true; $("crmg-da-chi-dang-ban").dispatch("change");
  await tra(URL_DA + "?dang_ban=1", {...dsGhi(8), loai_hinh: [], du_an_chua_ban: []});
  ALL(da(), e => e.className === "da-dong")[0].click(); await tra(URL_DA + "/" + A, ctGhi(8));
  click("Sửa thông tin"); await sauLuu(8); assert.ok($("crmg-da-f-loai_hinh_id").textContent.includes("Cho thuê đất"));
  nhap("ly_do", "Gửi trước khi chuyển tab"); click("Lưu thông tin"); const cu = cho(URL_DA + "/cap-nhat", "POST");
  nut(goc(), "Mẫu hợp đồng (G1)").click(); const soGet = calls.length; cu.resolve(phanHoi({da_ban_id: B, lap_lai: false})); await chay();
  assert.equal(calls.length, soGet, "POST trễ không tải/chọn dự án ở tab khác"); assert.equal($("crmg-da-form"), null);
  nut(goc(), "Dự án đang bán").click(); await sauLuu(8); click("Sửa thông tin"); nhap("ly_do", "Thử quyền"); click("Lưu thông tin");
  await ghi("cap-nhat", {error: "CRM_G_QUYEN", message: "Mã " + A}, 403);
  assert.equal($("crmg-da-form"), null); assert.ok(!da().textContent.includes(TITLE) && !da().textContent.includes(A));
  assert.ok(da().textContent.includes("Phiên hoặc quyền truy cập đã thay đổi"));
  dat("Sửa từ bản cũ/lọc nạp danh mục hiện hành; bỏ POST trễ khi rời tab; 403 xóa nháp và dữ liệu");
}

async function kiemG7(dat) {
  const {calls, $} = moiTruong(), goc = () => $("crm-g");
  for (const c of calls) { c.xong = true; c.resolve(phanHoi({message: "Module khác"}, 404)); } await chay();
  const cho = url => { const c = calls.find(c => !c.xong && c.url === url); assert.ok(c, url); c.xong = true; return c; };
  nut(goc(), "Bộ chuẩn dự án (G7)").click();
  const dong = [{lan: "1", gia_tri_loai: "PERCENT", gia_tri_thap_phan: "100", moc_loai: "SU_KIEN", moc_su_kien: "BAN_GIAO", ghi_chu: "Tiến độ CFO cũ"}];
  cho("/api/crm/bo-chuan").resolve(phanHoi({du_an: [{id: A, ma_junsky: "DEMO", phap_nhan: "DEMO", duoc_lap: true}], cot: ["Lần", "Giá trị", "Mốc", "Ghi chú"],
    phien_ban: ["DRAFT", "CHO_CFO", "HIEU_LUC"].map((tt, i) => ({id: "g7-" + i, du_an_id: A, giai_doan: "GD1", phien_ban: i + 1, trang_thai: tt, duoc_gui: true, duoc_duyet: true, lap_boi: "DEMO_KT", duyet_boi: tt === "HIEU_LUC" ? "DEMO_CFO" : null, valid_from: tt === "HIEU_LUC" ? "2026-09-01" : null, dong}))}));
  await chay();
  assert.ok(goc().textContent.includes("Dự án đang bán → Sửa tiến độ tiêu chuẩn"));
  assert.ok(!goc().textContent.includes("Lập bộ chuẩn (nháp)") && !goc().textContent.includes("QD-"));
  assert.equal(nut(goc(), "Lập bộ chuẩn (nháp)"), undefined); assert.equal($("crmg-lap-du-an"), null);
  assert.equal($("crmg-lap-giai-doan"), null); assert.equal($("crmg-l-tp-0"), null);
  assert.ok(goc().textContent.includes("Phiên bản bộ chuẩn"));
  assert.equal(nut(goc(), "Gửi CFO duyệt"), undefined); assert.equal(nut(goc(), "CFO duyệt (V4)"), undefined);
  assert.ok(goc().textContent.includes("Tiến độ CFO cũ") && goc().textContent.includes("duyệt bởi DEMO_CFO"));
  $("crmg-doc-giai-doan").value = "GD1"; $("crmg-doc-giai-doan").dispatch("input"); nut(goc(), "Xem bộ chuẩn hiệu lực").click();
  const doc = calls.find(c => !c.xong && c.url.startsWith("/api/crm/bo-chuan?")); assert.ok(doc); doc.xong = true;
  doc.resolve(phanHoi({trang_thai: "HIEU_LUC", version: {phien_ban: 3, valid_from: "2026-09-01"}, cot: ["Lần", "Giá trị", "Mốc", "Ghi chú"], rows: dong})); await chay();
  assert.ok(goc().textContent.includes("v3 · hiệu lực 2026-09-01")); assert.ok(!calls.some(c => c.method === "POST"));
  dat("G7: ẩn gửi/duyệt CFO dù máy chủ cấp quyền; có chú thích, vẫn xem danh sách và đọc bản CFO đã duyệt cũ");
}

async function main() {
  const {ctx, calls, $} = moiTruong(), goc = () => $("crm-g"), da = () => $("crmg-da"); let nhom = 0;
  const dat = s => { nhom++; console.log(`${nhom}. ${s}: đạt`); };
  const cho = url => { const c = calls.find(x => !x.xong && x.url === url); assert.ok(c, "Không có GET " + url); c.xong = true; return c; };
  const tra = async (url, data, status) => { cho(url).resolve(phanHoi(data, status)); await chay(); };
  const dong = name => ALL(da(), e => e.tagName === "TR" && e.className === "da-dong" && e.textContent.includes(name))[0];
  const mo = async (name = TITLE, data = ct(), daId = A) => { dong(name).click(); await tra(URL_DA + "/" + daId, data); };
  // Các module khác nhận 404 có chủ đích; không cần tạo phiên thật để kiểm cổng chỉ đọc.
  for (const c of calls) { c.xong = true; c.resolve(phanHoi({message: "Chưa nạp module khác"}, 404)); } await chay();
  assert.ok(!calls.some(c => c.url.startsWith(URL_DA)), "Không tự nạp DA trước khi mở tab");
  assert.ok(nut(goc(), "Mẫu hợp đồng (G1)") && nut(goc(), "Bộ chuẩn dự án (G7)"));
  nut(goc(), "Dự án đang bán").click(); await tra(URL_DA, ds());
  assert.equal($("crmg-tab-da").getAttribute("aria-pressed"), "true");
  assert.deepEqual(ALL(da(), e => e.tagName === "TH").map(e => e.textContent), ["Dự án", "Đơn giá niêm yết", "Số loại phí", "Số lô/căn", "Trạng thái", "Phiên bản"]);
  assert.equal(ALL(da(), e => e.className === "da-dong").length, 2); assert.ok(da().textContent.includes("120 USD/m²") && da().textContent.includes("Ngừng bán"));
  assert.ok(!da().textContent.includes("chưa bật bán không hiện"));
  assert.equal(ALL(da(), e => e.tagName === "BUTTON").length, 0, "Không có nút thêm/sửa giả"); dat("Danh sách, cột và nút chuyển mục 5");

  const loc = $("crmg-da-chi-dang-ban"); loc.checked = true; loc.dispatch("change"); await tra(URL_DA + "?dang_ban=1", ds(true));
  assert.equal($("crmg-da-chi-dang-ban").checked, true); assert.equal(ALL(da(), e => e.className === "da-dong").length, 1);
  $("crmg-da-chi-dang-ban").checked = false; $("crmg-da-chi-dang-ban").dispatch("change"); await tra(URL_DA, ds()); dat("Lọc gọi máy chủ và giữ trạng thái checkbox");

  dong(TITLE).dispatch("keydown", {key: "Enter"}); await tra(URL_DA + "/" + A, ct()); await tra("/api/crm/bao-gia/moc-chuan", MOC);
  const detail = $("crmg-da-chi-tiet").textContent;
  for (const x of ["Khu A <b>vị trí</b>", "Mô tả <b>nguyên văn</b>", "120 USD/m²", "Thuế suất", "Thuế suất 10%", "Giá chưa gồm VAT", "Giá đất được trừ", "24 USD/m²", "Cho thuê đất", "Phí <b>bảo trì</b>", "0,5 USD/m²/năm", "m²/tháng", "15.000 đ/m²/tháng", "1.234,5 m²", ...DM.trang_thai_lo.map(x => x.nhan)]) assert.ok(detail.includes(x), "Chi tiết thiếu " + x);
  assert.ok(!detail.includes("999") && !detail.includes("17%"), "Không tự tính/đổi thông tin máy chủ"); dat("Chi tiết thông tin, thuế, hai phí và bốn trạng thái lô");
  for (const x of ["30%", "70%", "05/11/2026", "Sau ký + 90 ngày", "Bàn giao", "0,05 USD", "123.456.789.012.345.678.901.234 đ", "1.500.000.000 đ", "Sự kiện khác (chưa có nhãn)", "Bán hàng áp dụng ngay"]) assert.ok(detail.includes(x), "Tiến độ thiếu " + x);
  dat("Tiến độ đọc rows thật, mốc tiếng Việt, tiền chính xác");

  $("crmg-da-phien-ban").value = "1"; $("crmg-da-phien-ban").dispatch("change");
  assert.ok(!$("crmg-da-chi-tiet").textContent.includes("120 USD/m²"), "Xóa ảnh chụp cũ khi đổi phiên bản");
  await tra(URL_DA + "/" + A + "?phien_ban=1", ct(1));
  assert.ok($("crmg-da-chi-tiet").textContent.includes("100 USD/m²") && $("crmg-da-chi-tiet").textContent.includes("Vị trí cũ"));
  assert.equal($("crmg-da-phien-ban").value, "1");
  assert.ok($("crmg-da-chi-tiet").textContent.includes("Không chịu thuế"), "Nhãn danh mục thuế phi số");
  assert.ok($("crmg-da-phien-ban").textContent.includes("01/09/2026 → trước 25/10/2026")); dat("Chọn phiên bản cũ và ngày hiệu lực dd/mm/yyyy");

  nut(da(), "Lịch sử").click(); await tra(URL_DA + "/" + A + "/lich-su", ls());
  const hist = $("crmg-da-lich-su").textContent;
  for (const x of ["Phiên bản 1", "Phiên bản 2", "Chị Lan", "Sửa phí <b>giữ nguyên</b>", "Đơn giá niêm yết", "Phí tiêu chuẩn", "Trạng thái bán", "Ngừng bán", "Mở bán lại", "01/09/2026 → trước 25/10/2026", "Người dùng mô phỏng", "Lô <b>nguyên văn</b>", "Đang giữ chỗ", "1.234,5 m²", "Thuế suất", "Giá đất được trừ", "Tiến độ tiêu chuẩn đã áp dụng", "GD1", "Bán hàng/kế toán áp dụng ngay", "CFO duyệt (bản cũ)", "Áp dụng tiến độ thanh toán tiêu chuẩn", "Áp dụng theo quyết định"]) assert.ok(hist.includes(x), "Lịch sử thiếu " + x);
  assert.ok(!hist.includes("QD-") && !hist.includes("999") && !hist.includes("NHAP_KHONG_HIEN") && !hist.includes("CUNG_NGAY_KHONG_HIEN"));
  assert.ok(hist.indexOf("Phiên bản 1") < hist.indexOf("Phiên bản 2"), "Đối chiếu theo thứ tự phiên bản");
  const eventTable = ALL($("crmg-da-lich-su"), e => e.tagName === "TABLE" && e.textContent.includes("Người thực hiện"))[0];
  assert.ok(eventTable.textContent.includes("25/10/2026"), "Ngày UTC được đổi giờ Việt Nam");
  assert.ok(!hist.includes("2026-10-") && !hist.includes("2026-09-")); dat("Lịch sử phiên bản, trường đổi, sự kiện và lô");

  assert.ok(goc().textContent.includes(TITLE)); assert.equal(ALL(goc(), e => ["B", "SCRIPT", "IMG"].includes(e.tagName)).length, 0);
  for (const x of [A, B, LH, "pb-id-", "lo-id-", "g7-id", "MA_DU_AN_KY_THUAT", "MA_LOAI_HINH_KY_THUAT", "GD_MA_KY_THUAT", "MO_PHONG_", "DEMO_BH", "BAO_TRI", "SU_DUNG", "M2_NAM", "M2_THANG", "CON_TRONG", "GIU_CHO", "DA_BAN", "KHONG_BAN", "PERCENT", "AMOUNT", "SU_KIEN", "AP_DUNG_NGAY", "CRM_DA_"]) assert.ok(!goc().textContent.includes(x), "Lộ mã kỹ thuật " + x);
  dat("Chuỗi HTML hiện nguyên văn, không lộ UUID/id/enum");

  // Hai GET phiên bản về ngược thứ tự: kết quả/ lỗi cũ không đè lựa chọn sau.
  $("crmg-da-phien-ban").value = "2"; $("crmg-da-phien-ban").dispatch("change"); const cu = cho(URL_DA + "/" + A + "?phien_ban=2");
  await mo(); cu.resolve(phanHoi(ct(1))); await chay();
  assert.ok($("crmg-da-chi-tiet").textContent.includes("120 USD/m²") && !$("crmg-da-chi-tiet").textContent.includes("Vị trí cũ"));
  dong(TITLE).click(); const cuDa = cho(URL_DA + "/" + A); await mo("Dự án B", ct(2, B), B); cuDa.reject(new Error("LOI_KY_THUAT_CU")); await chay();
  assert.ok($("crmg-da-chi-tiet").textContent.includes("Dự án B") && !goc().textContent.includes("LOI_KY_THUAT_CU")); dat("GET chi tiết/phiên bản về trễ hoặc lỗi bị bỏ");

  nut(da(), "Lịch sử").click(); const lsCu = cho(URL_DA + "/" + B + "/lich-su");
  nut(goc(), "Mẫu hợp đồng (G1)").click(); lsCu.resolve(phanHoi(ls())); await chay(); assert.equal($("crmg-da"), null);
  nut(goc(), "Dự án đang bán").click(); await tra(URL_DA, ds()); await tra(URL_DA + "/" + B, ct(2, B)); await tra(URL_DA + "/" + B + "/lich-su", ls());
  nut(da(), "Ẩn lịch sử").click(); assert.equal($("crmg-da-lich-su"), null); dat("Rời tab vô hiệu lịch sử cũ, mở lại và ẩn lịch sử");

  // Danh sách lọc cũ về sau danh sách mới; empty và lỗi đọc có thể làm mới lại.
  $("crmg-da-chi-dang-ban").checked = true; $("crmg-da-chi-dang-ban").dispatch("change"); const locCu = cho(URL_DA + "?dang_ban=1");
  $("crmg-da-chi-dang-ban").checked = false; $("crmg-da-chi-dang-ban").dispatch("change"); await tra(URL_DA, {...ds(), du_an_ban: []}); locCu.resolve(phanHoi(ds(true))); await chay();
  assert.ok(da().textContent.includes("Không có dự án")); assert.equal(ALL(da(), e => e.className === "da-dong").length, 0);
  nut(goc(), "↻ Làm mới").click(); await tra(URL_DA, {error: "CRM_LOI_MA_KY_THUAT", message: "UUID " + A}, 503);
  assert.ok(da().textContent.includes("Không tải được") && !goc().textContent.includes(A));
  nut(goc(), "↻ Làm mới").click(); await tra(URL_DA, ds()); assert.ok(dong(TITLE)); dat("GET danh sách mới nhất thắng, empty/lỗi và làm mới");

  dong(TITLE).click(); const vaiCu = cho(URL_DA + "/" + A), demTruoc = calls.filter(c => c.url.startsWith(URL_DA)).length;
  let moChan; const doiVai = ctx.kttChung.doiVaiTuanTu(() => new Promise(r => { moChan = r; }), "crmg-vai", "crm_g");
  assert.ok(!goc().textContent.includes(TITLE), "Đổi vai xóa đồng bộ dữ liệu cũ"); await chay();
  vaiCu.resolve(phanHoi(ct())); await chay(); assert.ok(!goc().textContent.includes(TITLE));
  assert.equal(calls.filter(c => c.url.startsWith(URL_DA)).length, demTruoc, "Barrier chặn GET khi đổi vai chưa xong");
  const soMau = calls.filter(c => c.url === "/api/crm/mau").length;
  moChan(); await chay();
  assert.equal(calls.filter(c => c.url === "/api/crm/mau").length, soMau + 1, "Đổi vai ở tab DA vẫn GET danh sách mẫu");
  await tra("/api/crm/mau", {nguoi: {dang_nhap: "DEMO_VAI_MOI", vai_tro: "BAN_HANG"}, ghi_nguon: {san_sang: true}, loai_hinh: [], phien_ban: []});
  await tra(URL_DA, {...ds(), du_an_ban: []}); await doiVai;
  nut(goc(), "Mẫu hợp đồng (G1)").click();
  assert.ok(goc().textContent.includes("Vai hiện hành: DEMO_VAI_MOI") && goc().textContent.includes("Chưa có mẫu trong phạm vi vai này"));
  assert.ok(!goc().textContent.includes("Đang tải…"));
  nut(goc(), "Bộ chuẩn dự án (G7)").click(); await tra("/api/crm/bo-chuan", {du_an: []});
  assert.ok(goc().textContent.includes("Vai hiện hành: DEMO_VAI_MOI") && goc().textContent.includes("Không có dự án trong phạm vi CRM của vai này"));
  nut(goc(), "Dự án đang bán").click(); await tra(URL_DA, {...ds(), du_an_ban: []});
  assert.ok(da().textContent.includes("Không có dự án")); dat("Đổi vai xóa đồng bộ, barrier và bỏ phản hồi vai cũ");

  nut(goc(), "↻ Làm mới").click(); await tra(URL_DA, ds()); await mo();
  nut(da(), "Lịch sử").click(); await tra(URL_DA + "/" + A + "/lich-su", {error: "CRM_G_QUYEN", message: "Mã " + A}, 403);
  assert.ok(!goc().textContent.includes(TITLE) && !goc().textContent.includes(A), "Lỗi quyền phải bỏ toàn bộ dữ liệu đang xem");
  assert.ok(da().textContent.includes("Phiên hoặc quyền truy cập đã thay đổi") && !da().textContent.includes("Đang tải"));
  nut(goc(), "↻ Làm mới").click(); await tra(URL_DA, {...ds(), du_an_ban: []});
  for (const status of [401, 403]) {
    nut(goc(), "↻ Làm mới").click(); await tra(URL_DA, {error: "CRM_G_QUYEN", message: "Mã " + A}, status);
    assert.ok(da().textContent.includes("Phiên hoặc quyền truy cập đã thay đổi") && !da().textContent.includes("Đang tải") && !goc().textContent.includes(A), "Lỗi danh sách " + status);
    nut(goc(), "↻ Làm mới").click(); await tra(URL_DA, ds());
    dong(TITLE).click(); await tra(URL_DA + "/" + A, {error: "CRM_G_QUYEN", message: "Mã " + A}, status);
    assert.ok(da().textContent.includes("Phiên hoặc quyền truy cập đã thay đổi") && !da().textContent.includes("Đang tải") && !goc().textContent.includes(TITLE) && !goc().textContent.includes(A), "Lỗi chi tiết " + status);
  }
  const daCalls = calls.filter(c => c.url.startsWith(URL_DA));
  assert.ok(daCalls.length > 15 && daCalls.every(c => c.method === "GET" && c.opts.headers["X-KTT-Token"] === "TOKEN-DA-THU" && c.opts.credentials === "same-origin" && c.opts.cache === "no-store"));
  assert.ok(!calls.some(c => c.method !== "GET"), "Màn chỉ xem không gửi lệnh ghi"); dat("Lỗi quyền xóa dữ liệu; API dùng token/phiên và chỉ GET");
  // Mất riêng nhãn mốc không được báo nhầm là dự án không tồn tại hoặc làm mất ảnh chụp.
  const mt2 = moiTruong();
  for (const c of mt2.calls) { c.xong = true; c.resolve(phanHoi({message: "Module khác"}, 404)); } await chay();
  const tra2 = async (url, data, status) => { const c = mt2.calls.find(x => !x.xong && x.url === url); assert.ok(c, url); c.xong = true; c.resolve(phanHoi(data, status)); await chay(); };
  nut(mt2.$("crm-g"), "Dự án đang bán").click(); await tra2(URL_DA, ds());
  ALL(mt2.$("crmg-da"), e => e.className === "da-dong")[0].click(); await tra2(URL_DA + "/" + A, ct());
  await tra2("/api/crm/bao-gia/moc-chuan", {message: "Không có nhãn"}, 404);
  assert.ok(mt2.$("crmg-da-chi-tiet").textContent.includes("120 USD/m²") && mt2.$("crmg-da-chi-tiet").textContent.includes("Sự kiện khác (chưa có nhãn)"));
  assert.ok(!mt2.$("crmg-da").textContent.includes("Không thấy dự án")); dat("Lỗi tải nhãn mốc giữ nguyên chi tiết và không lộ enum");
  await kiemGhi(dat);
  await kiemG7(dat);
  if (loiNgoai.length) throw loiNgoai[0]; console.log(`Tất cả ${nhom}/${nhom} nhóm DA-2a/DA-2b1/DA-2b2 đạt`);
}
main().catch(e => { console.error(e); process.exitCode = 1; });
