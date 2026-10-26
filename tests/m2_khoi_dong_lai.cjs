"use strict";
// DOM/fetch giả M2e, JS thật. Không server, mạng, bộ tải hay ghi tệp.
const fs = require("fs"), path = require("path"), vm = require("vm"), assert = require("assert");
const source = fs.readFileSync(path.join(__dirname, "m2_00e_giao_dien_async.cjs"), "utf8");
const {moiTruong, phanHoi, chay, JS, TT, MUC, API} = new Function("require", "__dirname",
  source.split("async function main()")[0] + "\nreturn {moiTruong, phanHoi, chay, JS, TT, MUC, API};")(require, __dirname);

function nut(root, text) {
  if (root.tagName === "BUTTON" && root.textContent === text) return root;
  for (const child of root.children || []) { const found = nut(child, text); if (found) return found; }
  return null;
}
const trang = (them = {}) => TT([MUC("DEMO_A", "MST_DEMO_A")], true, {duoc_khoi_dong_lai: true, ...them});

async function moi(tt) {
  const e = moiTruong(), $ = id => e.document.getElementById(id);
  e.ctx.confirm = () => { throw new Error("Khởi động lại phải xác nhận trong trang"); };
  vm.runInContext(JS, e.ctx);
  const lay = (method, suffix = "") => {
    const c = e.calls.find(c => !c.xong && c.method === method && c.url === API + suffix);
    assert.ok(c, `Thiếu ${method} ${suffix}`); c.xong = true; return c;
  };
  const nap = async state => {
    e.vai.get("m2_tai_hoa_don").nap(); await chay();
    lay("GET").resolve(phanHoi(200, state)); await chay();
  };
  await nap(tt);
  // Bộ tải chưa mở: kết thúc lần tự mở có sẵn bằng lỗi giả để thử nút phục hồi.
  const auto = e.calls.find(c => !c.xong && c.method === "POST" && c.url === API + "/khoi-dong");
  if (auto) {
    auto.xong = true; auto.resolve(phanHoi(503, {error: "M2_00B_BAT_TAY_QUA_HAN", message: "Bộ tải không khởi động được."}));
    await chay(); lay("GET").resolve(phanHoi(200, tt)); await chay();
  }
  return {...e, $, lay, nap, box: () => $("m2-tct-bo-tai"),
    restart: () => nut($("m2-tct-bo-tai"), "Khởi động lại bộ tải")};
}

async function main() {
  let so = 0;
  const loi = trang({bo_tai: {san_sang: false, trang_thai: "KHOI_DONG_LOI:BAT_TAY_QUA_HAN", loi_khoi_dong: "BAT_TAY_QUA_HAN"}});
  const treo = trang({bo_tai: {san_sang: true, trang_thai: "SAN_SANG", treo: true}});
  for (const tt of [loi, treo, {...treo, hang_doi: {dang_co_hang_doi: true, dang_chay: false, muc: []}}]) {
    const e = await moi(tt); assert.ok(e.restart()); assert.strictEqual(e.restart().disabled, false); so++;
  }
  for (const tt of [trang(), trang({bo_tai: {san_sang: false, trang_thai: "CHUA_KHOI_DONG"}}),
                    {...loi, duoc_khoi_dong_lai: false}, {...treo, duoc_khoi_dong_lai: undefined},
                    {cau_hinh: false, duoc_khoi_dong_lai: true, muc: []}]) {
    const e = await moi(tt); assert.strictEqual(e.restart(), null); so++;
  }
  {
    const e = await moi(treo);
    e.restart().click(); await chay();
    assert.ok(e.box().textContent.includes("Giữ nguyên gói và cấu hình"));
    assert.strictEqual(e.calls.filter(c => c.url.endsWith("/khoi-dong-lai")).length, 0);
    nut(e.box(), "Hủy").click();
    assert.strictEqual(nut(e.box(), "Xác nhận khởi động lại"), null);
    e.restart().click();
    const dongY = nut(e.box(), "Xác nhận khởi động lại");
    dongY.click(); dongY.click(); await chay();
    const c = e.lay("POST", "/khoi-dong-lai");
    assert.deepStrictEqual(JSON.parse(c.opts.body), {});
    assert.strictEqual(c.opts.headers["X-KTT-Token"], "TOKEN-THU");
    assert.strictEqual(c.opts.credentials, "same-origin");
    assert.strictEqual(e.calls.filter(c => c.url.endsWith("/khoi-dong-lai")).length, 1);
    assert.ok(e.box().textContent.includes("Đang khởi động lại bộ tải…"));
    assert.ok(nut(e.box(), "Đang khởi động lại bộ tải…").disabled);
    assert.ok(e.$("m2-tct-bat-dau").disabled);
    assert.ok(e.$("m2-tct-tat-ca").disabled);
    c.resolve(phanHoi(200, {message: "Đã khởi động lại bộ tải."})); await chay();
    e.lay("GET").resolve(phanHoi(200, trang())); await chay();
    assert.ok(e.$("m2-tct-status").textContent.includes("Đã khởi động lại bộ tải"));
    assert.strictEqual(e.restart(), null); so++;
  }
  for (const matMang of [false, true]) {
    const e = await moi(treo);
    e.restart().click(); nut(e.box(), "Xác nhận khởi động lại").click(); await chay();
    const c = e.lay("POST", "/khoi-dong-lai");
    if (matMang) c.reject(new Error("DEMO ngắt mạng"));
    else c.resolve(phanHoi(409, {error: "M2K_DANG_KHOI_DONG", message: "Bộ tải đang khởi động. Đợi kết quả rồi kiểm tra lại."}));
    await chay(); e.lay("GET").resolve(phanHoi(200, treo)); await chay();
    assert.ok(e.$("m2-tct-status").textContent.includes(matMang ? "chưa rõ kết quả khởi động lại" : "Đợi kết quả"));
    assert.strictEqual(e.calls.filter(c => c.url.endsWith("/khoi-dong-lai")).length, 1); so++;
  }
  {
    const e = await moi(treo);
    e.restart().click(); nut(e.box(), "Xác nhận khởi động lại").click(); await chay();
    const c = e.lay("POST", "/khoi-dong-lai");
    e.vai.get("m2_tai_hoa_don").xoa();
    c.resolve(phanHoi(200, {})); await chay();
    assert.strictEqual(e.box().textContent, "");
    assert.strictEqual(e.$("m2-tct-status").textContent, ""); so++;
  }
  {
    const e = await moi(trang({bo_tai: {san_sang: false, trang_thai: "DANG_KHOI_DONG"}}));
    assert.ok(e.restart().disabled); so++;
  }
  console.log(`M2k giao diện: ${so}/${so} ca đạt`);
}
main().catch(e => { console.error(e); process.exitCode = 1; });
