"use strict";
// Dùng lại DOM/fetch giả của M2e, chạy JS thật; không mạng, không ghi tệp.
const fs = require("fs"), path = require("path"), vm = require("vm"), assert = require("assert");
const source = fs.readFileSync(path.join(__dirname, "m2_00e_giao_dien_async.cjs"), "utf8");
assert.ok(source.includes("async function main()"), "Mẫu M2e đã đổi điểm vào");
const {moiTruong, phanHoi, chay, JS, TT, MUC, API} = new Function("require", "__dirname",
  source.split("async function main()")[0] + "\nreturn {moiTruong, phanHoi, chay, JS, TT, MUC, API};")(require, __dirname);

async function main() {
  // M2s-b: chạy câu dựng option thật, giữ login làm giá trị đổi vai.
  {
    const app = fs.readFileSync(path.join(__dirname, "../src/kho_tri_thuc/giao_dien/assets/app.js"), "utf8");
    const render = app.split(/\r?\n/).find(line => line.includes('$("m2-danh-tinh").replaceChildren'));
    assert.ok(render, "Không thấy câu dựng danh sách đổi vai M2");
    const login = "MO_PHONG_KT_M2_A";
    let options;
    vm.runInNewContext(render, {
      m2: {nguoi: {dang_nhap: login}, danh_tinh_demo: [{dang_nhap: login, vai_tro: "KE_TOAN"}]},
      $: id => { assert.strictEqual(id, "m2-danh-tinh"); return {replaceChildren: (...items) => { options = items; }}; },
      node: (tag, text) => ({tagName: tag, textContent: text})
    });
    assert.strictEqual(options.length, 1);
    assert.strictEqual(options[0].textContent, "Kế toán M2 (mô phỏng)");
    assert.strictEqual(options[0].value, login);
    assert.strictEqual(options[0].selected, true);
    console.log("M2s-b: nhãn tiếng Việt và giá trị đổi vai: đạt");
  }

  const {ctx, document, calls, vai} = moiTruong(), timers = [];
  const xacNhan = [];
  let dongY = false;
  ctx.confirm = msg => { xacNhan.push(msg); return dongY; };
  ctx.setTimeout = fn => { timers.push(fn); return timers.length; };
  const $ = id => document.getElementById(id);
  const lay = (method, url) => {
    const c = calls.find(c => !c.xong && c.method === method && c.url === API + url);
    assert.ok(c, `Thiếu ${method} ${url}`); c.xong = true; return c;
  };
  const q = (chay, a = "Đang tải", b = "Chờ") => ({dang_chay: chay, dang_co_hang_doi: chay, muc: [
    {phap_nhan_ten: "Công ty DEMO Ánh Dương", trang_thai: a, ly_do: null},
    {phap_nhan_ten: "Công ty DEMO Bình Minh", trang_thai: b, ly_do: b === "Lỗi" ? "Đăng nhập quá hạn" : null}]});
  const ds = [MUC("DEMO_A", "KEY_DEMO_A"), MUC("DEMO_B", "KEY_DEMO_B")];
  ctx.location.hash = "#hoadonmua";
  vm.runInContext(JS, ctx);
  $("m2-tct-dd-xml").checked = true;
  lay("GET", "").resolve(phanHoi(200, TT(ds))); await chay();
  const btn = $("m2-tct-tat-ca");
  assert.strictEqual(btn.textContent, "Tải tất cả công ty");
  $("m2-tct-thang").value = "2026-09";
  btn.click(); await chay();
  assert.strictEqual(calls.filter(c => c.method === "POST").length, 0, "Hủy xác nhận không được gửi lệnh");
  assert.strictEqual(xacNhan[0], "Tải 2 công ty · 09/2026 · Mua vào?");
  dongY = true;
  btn.click(); btn.click(); await chay();
  assert.strictEqual(xacNhan.length, 2, "Bấm đôi khi đang gửi không hỏi/lệnh thêm");
  const bd = lay("POST", "/tai-tat-ca");
  assert.deepStrictEqual(JSON.parse(bd.opts.body), {mode: "month", year: 2026, month: 9, types: ["purchase"], formats: ["xml"]});
  assert.strictEqual(calls.filter(c => c.url === API + "/tai-tat-ca").length, 1, "Bấm hai lần không gửi chồng");
  bd.resolve(phanHoi(200, q(true))); await chay();
  lay("GET", "/hang-doi").resolve(phanHoi(200, q(true))); await chay();
  assert.ok(btn.disabled && $("m2-tct-bat-dau").disabled);
  assert.strictEqual($("m2-tct-huy-hang-doi").textContent, "Hủy");
  const text = $("m2-tct-hang-doi").textContent;
  assert.ok(text.includes("Công ty DEMO Ánh Dương") && text.includes("Chờ") && text.includes("Đang tải"));
  assert.ok(!/KEY_DEMO|DEMO_A|DEMO_B/.test(text), "Bảng dùng tên pháp nhân");
  $("m2-tct-form").dispatch("submit"); await chay();
  assert.strictEqual(calls.filter(c => c.url === API + "/bat-dau").length, 0);
  timers.shift()(); await chay();
  lay("GET", "/hang-doi").resolve(phanHoi(200, q(false, "Xong", "Lỗi"))); await chay();
  assert.ok(!btn.disabled && !$("m2-tct-bat-dau").disabled);
  assert.strictEqual($("m2-tct-huy-hang-doi"), null);
  assert.ok($("m2-tct-hang-doi").textContent.includes("Đăng nhập quá hạn"));
  console.log("H1: nút, body, tiến độ theo tên, khóa tải lẻ và bấm đôi: đạt");

  // Mở lại trang: khôi phục hàng đợi phía máy chủ. Đổi vai chặn phản hồi cũ.
  $("m2-tct-lam-moi").click(); await chay();
  lay("GET", "").resolve(phanHoi(200, TT(ds, true, {hang_doi: q(true)}))); await chay();
  const muon = lay("GET", "/hang-doi");
  ctx.kttChung._chan = true;
  vai.get("m2_tai_hoa_don").xoa();
  assert.strictEqual($("m2-tct-hang-doi").textContent, "");
  muon.resolve(phanHoi(200, q(false))); await chay();
  assert.strictEqual($("m2-tct-hang-doi").textContent, "", "Phản hồi vai cũ không được vẽ lại");
  console.log("H2: phục hồi tiến độ và đổi vai: đạt");

  for (const status of [400, 403, 404, 409, 503]) {
    const env = moiTruong(), waits = [];
    env.ctx.setTimeout = fn => { waits.push(fn); return waits.length; };
    env.ctx.location.hash = "#hoadonmua";
    vm.runInContext(JS, env.ctx);
    env.calls[0].resolve(phanHoi(200, TT(ds, true, {hang_doi: q(true)}))); await chay();
    const poll = env.calls.find(c => c.url === API + "/hang-doi");
    assert.ok(poll);
    poll.resolve(phanHoi(status, {message: "DEMO: không đọc được hàng đợi"})); await chay();
    assert.strictEqual(waits.length, 0, `HTTP ${status} phải dừng poll`);
    assert.strictEqual(env.calls.filter(c => c.url === API + "/hang-doi").length, 1);
    assert.ok(env.document.getElementById("m2-tct-status").textContent.includes("DEMO:"));
  }
  console.log("H3: dừng poll ở HTTP 400/403/404/409/503: đạt");

  const env = moiTruong(), waits = [];
  env.ctx.setTimeout = fn => { waits.push(fn); return waits.length; };
  env.ctx.location.hash = "#hoadonmua";
  vm.runInContext(JS, env.ctx);
  env.calls[0].resolve(phanHoi(200, TT(ds, true, {hang_doi: q(true)}))); await chay();
  const pending = env.calls.find(c => c.url === API + "/hang-doi");
  const huy = env.document.getElementById("m2-tct-huy-hang-doi");
  huy.click(); huy.click(); await chay();
  const posts = env.calls.filter(c => c.method === "POST" && c.url === API + "/huy-hang-doi");
  assert.strictEqual(posts.length, 1, "Bấm hủy hai lần chỉ gửi một lệnh");
  assert.deepStrictEqual(JSON.parse(posts[0].opts.body), {});
  assert.ok(env.document.getElementById("m2-tct-huy-hang-doi").disabled);
  posts[0].resolve(phanHoi(200, {da_huy: true})); await chay();
  const sauHuy = env.calls.filter(c => c.url === API + "/hang-doi").at(-1);
  assert.notStrictEqual(sauHuy, pending);
  sauHuy.resolve(phanHoi(200, q(false, "Đã hủy", "Đã hủy"))); await chay();
  pending.resolve(phanHoi(200, q(true))); await chay();
  assert.strictEqual(env.document.getElementById("m2-tct-huy-hang-doi"), null);
  assert.ok(env.document.getElementById("m2-tct-hang-doi").textContent.includes("Đã hủy"));
  assert.ok(!env.document.getElementById("m2-tct-tat-ca").disabled);
  assert.strictEqual(waits.length, 0, "Phản hồi cũ không được khởi động lại poll sau hủy");
  env.document.getElementById("m2-tct-lam-moi").click(); await chay();
  env.calls.at(-1).resolve(phanHoi(200, TT(ds, true, {hang_doi: {dang_chay: false, dang_co_hang_doi: true, muc: []}}))); await chay();
  assert.strictEqual(env.document.getElementById("m2-tct-huy-hang-doi"), null, "Không hiện Hủy cho hàng đợi người khác");
  console.log("H4: hủy hàng đợi, chống bấm đôi/phản hồi cũ, ẩn Hủy của người khác: đạt");

  for (const status of [0, 400, 403, 409, 500, 502]) {
    const env = moiTruong(), waits = [];
    env.ctx.setTimeout = fn => { waits.push(fn); return waits.length; };
    env.ctx.location.hash = "#hoadonmua";
    vm.runInContext(JS, env.ctx);
    env.calls[0].resolve(phanHoi(200, TT(ds, true, {hang_doi: q(true)}))); await chay();
    const cu = env.calls.at(-1);
    env.document.getElementById("m2-tct-huy-hang-doi").click(); await chay();
    const post = env.calls.at(-1);
    if (status === 0) post.reject(new Error("DEMO: mất kết nối"));
    else post.resolve(phanHoi(status, {message: "DEMO: chưa xác nhận hủy"}));
    await chay();
    const moi = env.calls.at(-1);
    assert.strictEqual(moi.url, API + "/hang-doi", `Hủy lỗi ${status} vẫn đọc lại tiến độ`);
    assert.notStrictEqual(moi, cu);
    moi.resolve(phanHoi(200, q(true))); await chay();
    cu.resolve(phanHoi(200, q(false))); await chay();
    assert.ok(env.document.getElementById("m2-tct-huy-hang-doi"), "Phản hồi poll cũ không đổi tiến độ");
    assert.strictEqual(waits.length, 1);
    waits.shift()(); await chay();
    env.calls.at(-1).resolve(phanHoi(200, q(false))); await chay();
    assert.ok(!env.document.getElementById("m2-tct-tat-ca").disabled);
  }
  console.log("H5: hủy lỗi mạng/HTTP luôn tiếp tục poll và chống phản hồi cũ: đạt");

  for (const status of [0, 500, 502]) {
    const env = moiTruong(), waits = [];
    env.ctx.setTimeout = fn => { waits.push(fn); return waits.length; };
    env.ctx.location.hash = "#hoadonmua";
    vm.runInContext(JS, env.ctx);
    env.calls[0].resolve(phanHoi(200, TT(ds, true, {hang_doi: q(true)}))); await chay();
    const hong = async () => {
      const c = env.calls.at(-1);
      if (status === 0) c.reject(new Error("DEMO: mất kết nối"));
      else c.resolve(phanHoi(status, {message: "DEMO: lỗi tạm thời"}));
      await chay();
    };
    for (let i = 0; i < 19; i++) {
      await hong();
      assert.strictEqual(waits.length, 1);
      waits.shift()(); await chay();
    }
    // Một phản hồi tốt phải đặt lại bộ đếm lỗi liên tiếp.
    env.calls.at(-1).resolve(phanHoi(200, q(true))); await chay();
    waits.shift()(); await chay();
    for (let i = 0; i < 20; i++) {
      await hong();
      if (i < 19) { assert.strictEqual(waits.length, 1); waits.shift()(); await chay(); }
    }
    assert.strictEqual(waits.length, 0, `Lỗi ${status} dừng sau 20 lần liên tiếp`);
    assert.strictEqual(env.document.getElementById("m2-tct-status").textContent, "Mất kết nối — bấm Làm mới");
    env.document.getElementById("m2-tct-lam-moi").click(); await chay();
    env.calls.at(-1).resolve(phanHoi(200, TT(ds, true, {hang_doi: q(true)}))); await chay();
    assert.strictEqual(env.calls.at(-1).url, API + "/hang-doi", "Làm mới khởi động lại poll");
    env.calls.at(-1).resolve(phanHoi(200, q(false))); await chay();
  }
  console.log("H6: lỗi 0/500/502 dừng sau 20 lần, reset khi thành công, Làm mới phục hồi: đạt");
}
main().then(() => process.exit(0)).catch(e => { console.error(e.stack || e); process.exit(1); });
