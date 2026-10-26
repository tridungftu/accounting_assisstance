"use strict";
// MTQ-3a: chạy asset thật bằng VM + DOM/fetch giả; không mạng/server/CSDL.
// Fixture chỉ dùng trường DTO MTQ-2 / schema MTQ-1 thực sự có.
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../src/kho_tri_thuc/giao_dien/assets/ma_tran_tham_quyen.js"), "utf8");
const PN = "11111111-1111-4111-8111-111111111111", ROOM = "22222222-2222-4222-8222-222222222222", VERSION = "33333333-3333-4333-8333-333333333333";
const roles = ["THUC_HIEN_1", "THUC_HIEN_2", "TRUONG_PHONG", "CFO", "NGUOI_XEM"];
const clone = x => JSON.parse(JSON.stringify(x));
const catalog = [
  ["CRM", "G2_BAO_GIA", "XEM LAP SUA HUY"], ["M4", "02C_DUYET", "XEM LAP SUA KIEM DUYET"],
  ["M4", "PDF_DA_DUYET", "XEM"]
].flatMap(([module, man, actions]) => actions.split(" ").map(hanh_dong => ({catalog_version: 1, module, man, hanh_dong})));
function fixture() {
  return {admin: true, phong: [{id: ROOM, phap_nhan_id: PN, ma: "KHONG_HIEN_MA_PHONG", ten: "Phòng DEMO <script>alert(1)</script>", hoat_dong: true}],
    phien_ban: [{id: VERSION, phap_nhan_id: PN, so_phien_ban: 2, revision: 27, catalog_version: 1, trang_thai: "NHAP", tao_boi: "actor-demo", tao_luc: "2026-10-20T01:00:00Z"}],
    dong: roles.map((vai, i) => ({id: "dong-" + i, phien_ban_id: VERSION, phap_nhan_id: PN, phong_id: ROOM, vai,
      gioi_han_vnd: [null, "0", "500000000", "99999999999999999999", null][i], o: catalog.map(c => ({module: c.module, man: c.man, hanh_dong: c.hanh_dong, cho_phep: false}))})),
    danh_muc: clone(catalog), kich_hoat: [], gan_vai: [], pham_vi: [], chua_noi_mtq4: true};
}
const logFixture = () => ({thay_doi: [{phap_nhan_id: PN, phien_ban_id: VERSION, actor_id: "actor-demo", actor_login: "KHONG_HIEN_LOGIN",
  luc: "2026-10-26T01:05:00Z", ly_do: "Thử <script>audit()</script>", loai_su_kien: "O", doi_tuong: {},
  truoc: {cho_phep: false}, sau: {module: "CRM", man: "G2_BAO_GIA", hanh_dong: "XEM", cho_phep: true}},
  {phap_nhan_id: PN, phien_ban_id: VERSION, actor_id: "actor-demo", luc: "2026-10-26T01:00:00Z", ly_do: "Đổi hạn mức DEMO", loai_su_kien: "DONG",
    truoc: {vai: "CFO", gioi_han_vnd: 0}, sau: {vai: "CFO", gioi_han_vnd: 500000000}}], tu_choi: []});
function environment(options = {}) {
  class El {
    constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.listeners = {}; this.attrs = {}; this.className = ""; this._text = ""; this.value = ""; this.disabled = false; this.checked = false; this.hidden = false; this.ownerDocument = doc; }
    get textContent() { return this._text + this.children.map(c => c.textContent).join(""); }
    set textContent(v) { this.children = []; this._text = String(v); }
    set innerHTML(v) { throw Error("Cấm innerHTML: " + v); }
    set outerHTML(v) { throw Error("Cấm outerHTML: " + v); }
    insertAdjacentHTML() { throw Error("Cấm HTML thô"); }
    append(...nodes) { this.children.push(...nodes); }
    replaceChildren(...nodes) { this.children = []; this._text = ""; this.append(...nodes); }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    getAttribute(k) { return this.attrs[k]; }
    addEventListener(k, fn) { (this.listeners[k] ||= []).push(fn); }
    dispatch(k) { for (const fn of this.listeners[k] || []) fn({target: this}); }
    click() { if (!this.disabled) this.dispatch("click"); }
    showModal() { this.open = true; }
    close() { this.open = false; }
  }
  const doc = {createElement: tag => new El(tag), querySelector: () => ({content: "TOKEN-DEMO"})};
  const root = new El("main"), calls = [];
  let uuid = 0;
  const ctx = {document: doc, Intl, Date, console, crypto: {randomUUID: () => `00000000-0000-4000-8000-${String(++uuid).padStart(12, "0")}`},
    fetch: (url, opts) => new Promise((resolve, reject) => calls.push({url, opts, resolve, reject, done: false}))};
  ctx.window = ctx; vm.createContext(ctx); vm.runInContext(source, ctx);
  const app = ctx.dungMaTranThamQuyen(root, {laAdmin: true, tenPhapNhan: () => "Công ty DEMO <script>pn()</script>", tenNguoi: () => "Chị DEMO <script>ten()</script>", ...options});
  return {root, calls, app};
}
const all = (r, p) => [r, ...r.children.flatMap(c => all(c, () => true))].filter(p);
const byClass = (r, name) => all(r, e => e.className.split(" ").includes(name));
const buttons = e => all(e.root, n => n.tagName === "BUTTON");
const button = (e, text) => buttons(e).find(b => b.textContent === text);
const checks = e => all(e.root, n => n.type === "checkbox");
const inputs = e => byClass(e.root, "mtq-money");
const textArea = e => all(e.root, n => n.tagName === "TEXTAREA")[0];
const tick = (e, i = 0) => { const c = checks(e)[i]; c.checked = !c.checked; c.dispatch("change"); };
const input = (n, value) => { n.value = value; n.dispatch("input"); };
const settle = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };
async function respond(e, suffix, data, status = 200) {
  const c = e.calls.find(c => !c.done && c.url.endsWith("/" + suffix)); assert.ok(c, "Có yêu cầu " + suffix); c.done = true;
  c.resolve({ok: status < 400, status, json: async () => clone(data)}); await settle(); return c;
}
async function ready(data = fixture(), options = {}) {
  const e = environment(options); await respond(e, options.laAdmin === false ? "cua-toi" : "ma-tran", data);
  if (data.admin && options.laAdmin !== false) await respond(e, "nhat-ky", logFixture());
  await e.app.sanSang; return e;
}
let count = 0;
async function test(name, fn) { await fn(); console.log("ĐẠT " + (++count) + ": " + name); }
async function main() {
  await test("Năm dòng vai, một cột hạn mức ghim, nhóm module / màn và M9 tạm dừng", async () => {
    const e = await ready(); assert.equal(byClass(e.root, "mtq-row").length, 5);
    assert.equal(inputs(e).length, 5); assert.equal(all(e.root, n => n.tagName === "TH" && n.textContent === "Giới hạn số tiền (VND)").length, 1);
    assert.match(e.root.textContent, /Người thực hiện 1.*Người thực hiện 2.*Trưởng phòng.*CFO.*Người xem/s);
    assert.match(e.root.textContent, /M9.*Tạm dừng/s); assert.ok(!button(e, "Bật")); assert.ok(!buttons(e).some(b => /tick hết|mẫu/i.test(b.textContent)));
  });
  await test("Ô không khả dụng là —, không có checkbox", async () => {
    const e = await ready(), row = byClass(e.root, "mtq-row")[0];
    assert.equal(all(row, n => n.type === "checkbox").length, catalog.length);
    const unavailable = row.children[2 + 3]; assert.equal(unavailable.textContent, "—"); assert.equal(all(unavailable, n => n.tagName === "INPUT").length, 0);
  });
  await test("Gấp / mở module và màn giữ tick cùng lý do", async () => {
    const e = await ready(); tick(e); input(textArea(e), "Giữ nguyên lý do");
    button(e, "− CRM · Khách hàng & hợp đồng").click(); assert.equal(checks(e).length, (catalog.length - 4) * 5);
    button(e, "+ CRM · Khách hàng & hợp đồng").click(); assert.equal(checks(e)[0].checked, true);
    button(e, "− Báo giá").click(); button(e, "+ Báo giá").click(); assert.equal(checks(e)[0].checked, true); assert.equal(textArea(e).value, "Giữ nguyên lý do");
  });
  await test("Tiền trống, 0, 500.000.000 và số lớn giữ chính xác", async () => {
    const e = await ready(); assert.equal(inputs(e)[0].placeholder, "Không giới hạn");
    assert.equal(inputs(e)[0].value, ""); assert.equal(inputs(e)[1].value, "0"); assert.equal(inputs(e)[2].value, "500.000.000");
    assert.equal(inputs(e)[3].value, "99.999.999.999.999.999.999"); assert.match(e.root.textContent, /0 VND/); assert.match(e.root.textContent, /500\.000\.000 VND/);
    input(inputs(e)[0], "500000000"); inputs(e)[0].dispatch("blur"); assert.equal(inputs(e)[0].value, "500.000.000");
  });
  await test("Chặn âm, chữ, số thập phân, phân nhóm sai và quá 20 chữ số ngay trên màn", async () => {
    const e = await ready(); input(textArea(e), "Thử hạn mức"); tick(e);
    for (const v of ["-1", "abc", "1.5", "1e9", "12.34.000", "100000000000000000000"]) {
      input(inputs(e)[0], v); assert.equal(inputs(e)[0].getAttribute("aria-invalid"), "true"); assert.equal(button(e, "Lưu nháp").disabled, true);
      button(e, "Lưu nháp").click(); assert.equal(e.calls.filter(c => c.opts.method === "POST").length, 0);
    }
    input(inputs(e)[0], "0"); assert.equal(inputs(e)[0].getAttribute("aria-invalid"), "false"); assert.equal(button(e, "Lưu nháp").disabled, false);
  });
  await test("Diff ô và hạn mức cũ → mới; lý do bắt buộc", async () => {
    const e = await ready(); tick(e); input(inputs(e)[2], "600.000.000");
    const diff = byClass(e.root, "mtq-diff")[0].textContent;
    assert.match(diff, /Xem: Không → Có/); assert.match(diff, /500\.000\.000 VND → 600\.000\.000 VND/);
    assert.equal(button(e, "Lưu nháp").disabled, true); input(textArea(e), "   "); assert.equal(button(e, "Lưu nháp").disabled, true);
    input(textArea(e), "Cập nhật DEMO"); assert.equal(button(e, "Lưu nháp").disabled, false);
  });
  await test("Thân lưu nháp đúng DTO, token, revision và UUID; chống bấm đúp", async () => {
    const e = await ready(); tick(e); input(inputs(e)[1], "500.000.000"); input(textArea(e), "  Cập nhật DEMO  ");
    const b = button(e, "Lưu nháp"); b.click(); b.click(); button(e, "Lưu nháp").click();
    const calls = e.calls.filter(c => c.opts.method === "POST"); assert.equal(calls.length, 1);
    const p = JSON.parse(calls[0].opts.body);
    assert.deepEqual(Object.keys(p).sort(), ["dong", "expected_revision", "khoa", "ly_do", "phien_ban_id"].sort());
    assert.equal(p.expected_revision, 27); assert.equal(p.phien_ban_id, VERSION); assert.equal(p.ly_do, "Cập nhật DEMO");
    assert.match(p.khoa, /^[0-9a-f-]{36}$/); assert.equal(p.dong.length, 5);
    assert.deepEqual(Object.keys(p.dong[0]).sort(), ["phong_id", "vai", "gioi_han_vnd", "o"].sort());
    assert.equal(p.dong[0].phong_id, ROOM); assert.equal(p.dong[0].gioi_han_vnd, null); assert.equal(p.dong[1].gioi_han_vnd, "500000000");
    assert.equal(p.dong[0].o[0].cho_phep, true); assert.deepEqual(Object.keys(p.dong[0].o[0]).sort(), ["module", "man", "hanh_dong", "cho_phep"].sort());
    assert.equal(calls[0].opts.headers["X-KTT-Token"], "TOKEN-DEMO"); assert.equal(calls[0].opts.credentials, "same-origin");
    assert.ok(!calls[0].opts.body.includes('"actor"')); assert.ok(!calls[0].opts.body.includes('"phap_nhan_id"'));
    await respond(e, "luu-nhap", {ket_qua: {id: VERSION}, lap_lai: false});
    const updated = fixture(); updated.phien_ban[0].revision = 40; updated.dong[0].o[0].cho_phep = true; updated.dong[1].gioi_han_vnd = "500000000";
    await respond(e, "ma-tran", updated); await respond(e, "nhat-ky", logFixture());
    assert.match(e.root.textContent, /Đã lưu nháp/); assert.equal(checks(e)[0].checked, true); assert.equal(button(e, "Lưu nháp").disabled, true);
  });
  await test("Sửa bản đã công bố tạo nháp từ nguon_id, revision 0", async () => {
    const d = fixture(); d.phien_ban[0].trang_thai = "DA_CONG_BO"; const e = await ready(d);
    tick(e); input(textArea(e), "Nháp kế tiếp"); button(e, "Lưu nháp").click();
    const p = JSON.parse(e.calls.at(-1).opts.body); assert.equal(p.nguon_id, VERSION); assert.equal(p.expected_revision, 0); assert.ok(!("phien_ban_id" in p));
  });
  for (const code of ["MTQ_REVISION", "MTQ_IDEMPOTENCY_KHAC"]) await test(`409 ${code} khóa ghi, báo xung đột và không tự ghi đè`, async () => {
    const e = await ready(); tick(e); input(textArea(e), "Đổi quyền"); button(e, "Lưu nháp").click();
    await respond(e, "luu-nhap", {error: code, message: "Không hiện mã kỹ thuật"}, 409);
    assert.equal(byClass(e.root, "mtq-message")[0].textContent, "Đã có người khác sửa, tải lại"); assert.equal(button(e, "Lưu nháp").disabled, true); assert.equal(checks(e)[0].disabled, true);
    assert.equal(e.calls.filter(c => c.opts.method === "POST").length, 1); assert.ok(!e.root.textContent.includes(code));
  });
  await test("409 nghiệp vụ giữ nguyên câu máy chủ, không ghép câu xung đột", async () => {
    for (const [code, message] of [
      ["MTQ_THIEU_DONG", "Chưa đủ năm vai tại mọi phòng hoạt động."],
      ["MTQ_BAT_BIEN", "Bản đã công bố không được sửa."],
      ["CRM_G_GIAO_DICH_NGOAI", "Không thể ghi cấu hình trong giao dịch hiện hành."]
    ]) {
      const e = await ready(); tick(e); input(textArea(e), "Đổi quyền"); button(e, "Lưu nháp").click();
      await respond(e, "luu-nhap", {error: code, message}, 409);
      assert.equal(byClass(e.root, "mtq-message")[0].textContent, message);
      assert.ok(!e.root.textContent.includes("Đã có người khác sửa")); assert.equal(button(e, "Lưu nháp").disabled, true);
      assert.equal(button(e, "Tải lại").disabled, false); assert.equal(e.calls.filter(c => c.opts.method === "POST").length, 1);
    }
  });
  await test("403 khóa ghi, báo không có quyền; tải lại bị từ chối xóa dữ liệu cũ", async () => {
    const e = await ready(); tick(e); input(textArea(e), "Đổi quyền"); button(e, "Lưu nháp").click();
    await respond(e, "luu-nhap", {error: "MTQ_CHI_ADMIN", message: "<script>error()</script>"}, 403);
    assert.match(e.root.textContent, /Người dùng đang thực hành không có quyền/); assert.equal(button(e, "Lưu nháp").disabled, true);
    button(e, "Tải lại").click(); await respond(e, "ma-tran", {error: "MTQ_CHI_ADMIN"}, 403);
    assert.equal(byClass(e.root, "mtq-row").length, 0); assert.match(e.root.textContent, /Người dùng đang thực hành không có quyền/);
  });
  await test("503 lỗi nhật ký báo thao tác chưa thực hiện và cho phép thử lại", async () => {
    const e = await ready(); tick(e); input(textArea(e), "Đổi quyền"); button(e, "Lưu nháp").click();
    const body = e.calls.at(-1).opts.body;
    await respond(e, "luu-nhap", {error: "MTQ_NHAT_KY_LOI", message: "Chưa ghi được nhật ký thẩm quyền, thao tác không được thực hiện. Báo quản trị."}, 503);
    assert.equal(byClass(e.root, "mtq-message")[0].textContent, "Chưa ghi được nhật ký, thao tác chưa thực hiện. Báo quản trị.");
    assert.ok(!e.root.textContent.includes("Mất kết nối")); assert.ok(!e.root.textContent.includes("Đã lưu nháp"));
    assert.equal(button(e, "Lưu nháp").disabled, false); assert.equal(button(e, "Tải lại").disabled, false);
    assert.equal(checks(e)[0].disabled, false); assert.equal(checks(e)[0].checked, true);
    button(e, "Lưu nháp").click(); assert.equal(e.calls.at(-1).opts.body, body);
  });
  await test("Mất mạng thử lại cùng khóa yêu cầu và cùng nội dung", async () => {
    const e = await ready(); tick(e); input(textArea(e), "Thử lại"); button(e, "Lưu nháp").click();
    const first = e.calls.at(-1); first.done = true; first.reject(Error("offline")); await settle();
    assert.match(e.root.textContent, /Mất kết nối/); button(e, "Lưu nháp").click(); assert.equal(e.calls.at(-1).opts.body, first.opts.body);
  });
  await test("Công bố có xác nhận, lý do, revision và cảnh báo bản toàn tắt", async () => {
    const e = await ready(); assert.equal(button(e, "Công bố").disabled, true); input(textArea(e), "Công bố DEMO"); button(e, "Công bố").click();
    assert.equal(e.calls.filter(c => c.opts.method === "POST").length, 0); assert.match(e.root.textContent, /Toàn bộ ô quyền đang tắt/);
    const dialog = all(e.root, n => n.tagName === "DIALOG")[0]; assert.equal(dialog.open, true);
    const confirm = button(e, "Xác nhận công bố"); confirm.click(); confirm.click();
    const posts = e.calls.filter(c => c.opts.method === "POST"); assert.equal(posts.length, 1); assert.match(posts[0].url, /cong-bo$/);
    const p = JSON.parse(posts[0].opts.body); assert.deepEqual(Object.keys(p).sort(), ["expected_revision", "ly_do", "phien_ban_id", "khoa"].sort()); assert.equal(p.expected_revision, 27);
  });
  await test("Nhật ký: ngày giờ Việt Nam, tên hiển thị, lý do, đổi ô; escape script", async () => {
    const e = await ready(); button(e, "Xem nhật ký").click();
    assert.match(e.root.textContent, /26\/10\/2026 08:05/); assert.match(e.root.textContent, /Chị DEMO <script>ten\(\)<\/script>/);
    assert.match(e.root.textContent, /Thử <script>audit\(\)<\/script>/); assert.match(e.root.textContent, /Xem: Không → Có/);
    assert.match(e.root.textContent, /0 VND → 500\.000\.000 VND/);
    assert.equal(all(e.root, n => n.tagName === "SCRIPT").length, 0);
    for (const s of [PN, ROOM, VERSION, "KHONG_HIEN_LOGIN", "KHONG_HIEN_MA_PHONG", "THUC_HIEN_1", "G2_BAO_GIA"]) assert.ok(!e.root.textContent.includes(s), s);
  });
  await test("Bật chỉ hiện khi máy chủ trả sẵn sàng rõ ràng; dùng revision con trỏ", async () => {
    const d = fixture(); d.phien_ban[0].trang_thai = "DA_CONG_BO";
    for (const flag of [true, undefined]) { const no = clone(d); if (flag === undefined) delete no.chua_noi_mtq4; const e = await ready(no); assert.ok(!button(e, "Bật")); }
    d.chua_noi_mtq4 = false; d.kich_hoat = [{phap_nhan_id: PN, bat: false, revision: 8, phien_ban_id: null}];
    const e = await ready(d); assert.ok(button(e, "Bật")); assert.equal(button(e, "Bật").disabled, true);
    input(textArea(e), "Bật DEMO"); button(e, "Bật").click(); button(e, "Xác nhận bật").click();
    const p = JSON.parse(e.calls.at(-1).opts.body); assert.equal(p.expected_revision, 8); assert.equal(p.phien_ban_id, VERSION);
    assert.deepEqual(Object.keys(p).sort(), ["expected_revision", "ly_do", "phien_ban_id", "khoa"].sort());
    const message = "Không thể áp dụng cấu hình thẩm quyền; kiểm tra lại phiên bản và điều kiện thực hiện.";
    await respond(e, "kich-hoat", {error: "MTQ_CHUA_NOI_MTQ4", message}, 409);
    assert.equal(byClass(e.root, "mtq-message")[0].textContent, message); assert.ok(!e.root.textContent.includes("Đã có người khác sửa"));
    assert.ok(!e.root.textContent.includes("MTQ_CHUA_NOI_MTQ4"));
  });
  await test("Nhật ký hạn mức cũ → mới, trạng thái đang dùng", async () => {
    const d = fixture(); d.kich_hoat = [{phap_nhan_id: PN, bat: true, phien_ban_id: VERSION, revision: 3}];
    const e = environment(); await respond(e, "ma-tran", d);
    const l = logFixture(); l.thay_doi[0].sau = {vai: "CFO", gioi_han_vnd: 0}; l.thay_doi[0].truoc = {gioi_han_vnd: null};
    await respond(e, "nhat-ky", l); button(e, "Xem nhật ký").click(); assert.match(e.root.textContent, /Không giới hạn → 0 VND/); assert.match(e.root.textContent, /Đang dùng/);
  });
  for (const literal of ["99999999999999999999", "123456789012345678"]) await test(`Nhật ký số JSON ${literal}: vẽ đủ và mở lại nút sau Tải lại`, async () => {
    const e = environment(), l = logFixture(), amount = JSON.parse(literal);
    assert.equal(typeof amount, "number"); assert.equal(Number.isSafeInteger(amount), false);
    l.thay_doi[1].sau.gioi_han_vnd = amount;
    l.thay_doi.push({...clone(l.thay_doi[1]), truoc: {gioi_han_vnd: amount}, sau: {vai: "CFO", gioi_han_vnd: 500000000}});
    await respond(e, "ma-tran", fixture()); await respond(e, "nhat-ky", l); await e.app.sanSang;
    button(e, "Xem nhật ký").click();
    const checkScreen = () => {
      const log = byClass(e.root, "mtq-log")[0]; assert.ok(log);
      assert.match(log.textContent, /0 VND → Giá trị quá lớn — xem ở máy chủ/);
      assert.match(log.textContent, /Giá trị quá lớn — xem ở máy chủ → 500\.000\.000 VND/);
      assert.ok(!log.textContent.includes(String(amount))); assert.ok(!log.textContent.includes(literal));
      assert.equal(byClass(e.root, "mtq-row").length, 5); assert.equal(checks(e).length, catalog.length * 5);
      assert.ok(checks(e).every(c => !c.disabled)); assert.ok(inputs(e).every(c => !c.disabled));
      assert.equal(button(e, "Tải lại").disabled, false); assert.equal(button(e, "Ẩn nhật ký").disabled, false);
    };
    checkScreen(); button(e, "Tải lại").click();
    assert.equal(button(e, "Tải lại").disabled, true);
    await respond(e, "ma-tran", fixture()); await respond(e, "nhat-ky", l); checkScreen();
    tick(e); input(textArea(e), "Thử sau tải lại"); assert.equal(button(e, "Lưu nháp").disabled, false);
    button(e, "Lưu nháp").click(); assert.equal(e.calls.filter(c => c.opts.method === "POST").length, 1);
  });
  await test("Nhật ký nhận chuỗi tiền chính xác và dữ liệu tiền sai không làm hỏng màn", async () => {
    const e = environment(), l = logFixture();
    for (const value of ["99999999999999999999", "123456789012345678", "không hợp lệ", {sai: true}]) {
      l.thay_doi.push({...clone(l.thay_doi[1]), truoc: {gioi_han_vnd: value}, sau: {vai: "CFO", gioi_han_vnd: value}});
    }
    await respond(e, "ma-tran", fixture()); await respond(e, "nhat-ky", l); await e.app.sanSang;
    button(e, "Xem nhật ký").click();
    const text = byClass(e.root, "mtq-log")[0].textContent;
    assert.match(text, /99\.999\.999\.999\.999\.999\.999 VND/); assert.match(text, /123\.456\.789\.012\.345\.678 VND/);
    assert.match(text, /Hạn mức không hợp lệ — xem ở máy chủ/); assert.equal(button(e, "Tải lại").disabled, false);
  });
  for (const action of ["render", "load"]) await test(`Lỗi ${action} phục hồi bằng Tải lại, không để nút khóa`, async () => {
    let fail = false;
    const e = await ready(fixture(), {tenPhapNhan: () => { if (fail) throw Error("Lỗi nhãn DEMO"); return "Công ty DEMO"; }});
    fail = true;
    if (action === "render") button(e, "Xem nhật ký").click();
    else await e.app.taiLai(); // Lỗi ở lần vẽ trạng thái busy, trước khi gọi fetch.
    assert.match(e.root.textContent, /Không hiển thị được quyền/);
    assert.equal(byClass(e.root, "mtq-row").length, 0); assert.equal(button(e, "Tải lại").disabled, false);
    fail = false; button(e, "Tải lại").click(); await respond(e, "ma-tran", fixture()); await respond(e, "nhat-ky", logFixture());
    assert.equal(byClass(e.root, "mtq-row").length, 5); assert.ok(checks(e).every(c => !c.disabled));
    tick(e); input(textArea(e), "Đã phục hồi"); assert.equal(button(e, "Lưu nháp").disabled, false);
  });
  await test("Bật lần đầu gửi revision 0; thành công nạp lại và ẩn nút Bật", async () => {
    const d = fixture(); d.phien_ban[0].trang_thai = "DA_CONG_BO"; d.chua_noi_mtq4 = false;
    const e = await ready(d); input(textArea(e), "Bật lần đầu"); button(e, "Bật").click(); button(e, "Xác nhận bật").click();
    assert.equal(JSON.parse(e.calls.at(-1).opts.body).expected_revision, 0);
    await respond(e, "kich-hoat", {ket_qua: {phap_nhan_id: PN, phien_ban_id: VERSION, bat: true, revision: 1}, lap_lai: false});
    d.kich_hoat = [{phap_nhan_id: PN, phien_ban_id: VERSION, bat: true, revision: 1}];
    await respond(e, "ma-tran", d); await respond(e, "nhat-ky", logFixture());
    assert.match(e.root.textContent, /Đã bật ma trận/); assert.match(e.root.textContent, /Đang dùng/); assert.ok(!button(e, "Bật"));
  });
  await test("Người không phải Admin chỉ gọi cua-toi, chỉ hiện vai được trả, không có ô sửa", async () => {
    const d = fixture(); d.admin = false; d.phong = []; d.dong = [{...d.dong[2], ten_phong: "Phòng của tôi"}];
    d.kich_hoat = [{phap_nhan_id: PN, bat: true, phien_ban_id: VERSION, revision: 1}];
    const e = await ready(d, {laAdmin: false}); assert.deepEqual(e.calls.map(c => c.url), ["/api/tham-quyen/cua-toi"]);
    assert.equal(byClass(e.root, "mtq-row").length, 1); assert.match(e.root.textContent, /Trưởng phòng/); assert.ok(!e.root.textContent.includes("Người thực hiện 1"));
    assert.equal(checks(e).length, 0); assert.equal(inputs(e).length, 0); assert.ok(!button(e, "Lưu nháp")); assert.ok(!button(e, "Xem nhật ký"));
    button(e, "Tải lại").click(); await respond(e, "cua-toi", d); assert.ok(e.calls.every(c => c.url.endsWith("/cua-toi")));
  });
  await test("Người không phải Admin: chưa bật ma trận hiện quyền theo phân quyền đang có", async () => {
    for (const state of ["rong", "chua-bat", "khac-phap-nhan"]) {
      const d = fixture(); d.admin = false; d.phong = []; d.phien_ban = []; d.dong = [];
      if (state !== "rong") {
        d.gan_vai = [{id: "gan-demo", phap_nhan_id: PN, phong_id: ROOM, vai: "CFO"}];
        d.kich_hoat = [{phap_nhan_id: PN, bat: false, phien_ban_id: null, revision: 1}];
        if (state === "khac-phap-nhan") d.kich_hoat.push({phap_nhan_id: "pn-khac", bat: true, phien_ban_id: "ban-khac", revision: 1});
      }
      const e = await ready(d, {laAdmin: false});
      assert.match(e.root.textContent, /Pháp nhân chưa dùng ma trận thẩm quyền; quyền hiện áp dụng theo phân quyền đang có\./);
      assert.ok(!e.root.textContent.includes("Chưa có quyền đang áp dụng")); assert.ok(!button(e, "Lưu nháp"));
      assert.equal(button(e, "Tải lại").disabled, false); button(e, "Tải lại").click(); await respond(e, "cua-toi", d);
      assert.ok(e.calls.every(c => c.url.endsWith("/cua-toi")));
    }
  });
  await test("Mặc định gọi cua-toi; thiếu tên dùng nhãn rõ, không lấy login hay UUID", async () => {
    const e = environment({laAdmin: undefined, tenPhapNhan: undefined, tenNguoi: undefined}); assert.equal(e.calls[0].url, "/api/tham-quyen/cua-toi");
    const d = fixture(); d.admin = false; d.kich_hoat = [{phap_nhan_id: PN, bat: true, phien_ban_id: VERSION, revision: 1}];
    await respond(e, "cua-toi", d); assert.match(e.root.textContent, /Pháp nhân 1 \(chưa có tên\)/); assert.ok(!e.root.textContent.includes(PN));
  });
  await test("Tạo mới phòng đủ năm dòng, trường gửi đúng; chọn pháp nhân rồi phòng", async () => {
    const d = fixture(); d.phien_ban = []; d.dong = [];
    d.phong.push({id: "phong-demo-2", phap_nhan_id: "pn-demo-2", ten: "Phòng hai", hoat_dong: true});
    const e = await ready(d); const selects = all(e.root, n => n.tagName === "SELECT");
    selects[0].value = "pn-demo-2"; selects[0].dispatch("change"); assert.equal(all(e.root, n => n.tagName === "SELECT")[1].value, "phong-demo-2");
    input(textArea(e), "Khởi tạo"); button(e, "Lưu nháp").click(); const p = JSON.parse(e.calls.at(-1).opts.body);
    assert.equal(p.expected_revision, 0); assert.equal(p.dong.length, 5); assert.ok(!p.nguon_id && !p.phien_ban_id); assert.ok(p.dong.every(r => r.phong_id === "phong-demo-2"));
  });
  await test("Đổi phòng khi đang sửa bị chặn để giữ dữ liệu", async () => {
    const e = await ready(); tick(e); const sel = all(e.root, n => n.tagName === "SELECT")[1]; sel.value = "phong-khac"; sel.dispatch("change");
    assert.equal(sel.value, ROOM); assert.match(e.root.textContent, /Lưu nháp hoặc tải lại/); assert.equal(checks(e)[0].checked, true);
  });
  await test("Hủy màn chặn phản hồi muộn và xóa nội dung đồng bộ", async () => {
    const e = environment(); e.app.huy(); await respond(e, "ma-tran", fixture()); await e.app.sanSang; assert.equal(e.root.textContent, ""); assert.equal(e.calls.length, 1);
  });
  console.log(`MTQ-3a: ${count}/${count} đạt; 0 lỗi.`);
}
main().catch(e => { console.error(e); process.exitCode = 1; });
