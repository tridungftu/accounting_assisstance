"use strict";
// M4-03A GUI FIX02 — hộp chờ CAN_KIEM_LAI (docs/GIAO-CODE-M4-03A-GUI-FIX02.md). CODE_ONLY: WRITTEN_NOT_RUN — coder viết, CHƯA CHẠY.
// Root chạy: `node tests/m4_03a_gui_fix02_async.cjs [bundle.json]` (Node ≥ 18).
//
// Cùng pattern FIX01 (tests/m4_03a_gui_fix01_async.cjs — KHÔNG sửa): đọc tests/m4_03a_async.cjs GỐC bất biến, kiểm SHA-256
// fcf93d9f2c7c6a1552d9924d5ac950e0b3643dd1c78e4140f665c08f2f809daa (lệch → SETUP lỗi, không chạy), áp ĐÚNG 2 dòng delta title-reflection của El giả đã chốt
// ở FIX01 (inverse: bỏ hai mệnh đề `if (k === "title") …`), chèn MỘT lời gọi ca FIX02 trước khối INTEGRATION của main() gốc. 32 ca gốc chạy nguyên
// assertion/body golden; tệp gốc không bị ghi.
//
// Fixture THỦ CÔNG literal theo contract/producer (trang_thai:"CAN_KIEM_LAI" của trang_thai_dong) — bằng chứng UI/route trên fakeDOM; KHÔNG gọi
// producer/PG/browser thật; enum kỳ vọng viết literal, không đọc từ code sản phẩm.
//  F2-1 hộp chờ trộn CAN_KIEM_LAI (revision null và ≥1) + dòng thường → hiển thị đủ, không SAI_DTO, mỗi dòng có Mở.
//  F2-2 Mở dòng CAN_KIEM_LAI → GET chi tiết đúng root, KHÔNG query (không lấy phong_bi_id/revision từ dòng); chi tiết stale chỉ đọc (nguồn + lịch sử
//       + PDF tải được theo quyền đọc), không nút lưu/xác nhận/form, 0 POST.
//  F2-3 dòng thường cạnh CAN_KIEM_LAI vẫn mở + lưu hợp lệ (expected_revision 0 từ kt null của GET, không từ dòng) → không always-HOLD.
//  F2-4 CAN_KIEM_LAI ở kt đã lưu / lịch sử KT → SAI_DTO, không nút lệnh, 0 POST; ở ACK lưu/xác nhận → CHƯA RÕ, không toast thành công, Gửi lại y nguyên giữ body/khóa.
//  F2-5 trạng thái hộp chờ lạ/chữ thường/thiếu/null, revision 0/chuỗi, ap sai, khóa thừa → SAI_DTO, không dòng/không Mở (không fallback).
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");
const crypto = require("crypto");

const GOC = path.join(__dirname, "m4_03a_async.cjs");
const SHA_GOC = "fcf93d9f2c7c6a1552d9924d5ac950e0b3643dd1c78e4140f665c08f2f809daa";
const DELTA = [
  ["    setAttribute(k, v) { this.attrs[k] = String(v); }", "    setAttribute(k, v) { this.attrs[k] = String(v); if (k === \"title\") this.title = this.attrs[k]; }"],
  ["    removeAttribute(k) { delete this.attrs[k]; }", "    removeAttribute(k) { delete this.attrs[k]; if (k === \"title\") this.title = \"\"; }"],
];
const MOC = "  // ================================================================ INTEGRATION";
const CHEN = "  await __FIX02({ca, moPhien, DTO, KTO, ACK, DS, AP, chay, sao, timTatCa, coSaiDto, ENV, PEND, PEND2, KTR, URL_CT, URL_PDF, URL_LUU, URL_XN,\n" +
  "    NUT_LUU, NUT_XN, NUT_LAI, NUT_TAI, O_NT, O_TT, O_LY_DO, soClick: () => soClickTai});\n";

function demLan(s, t) { let n = 0, i = -1; while ((i = s.indexOf(t, i + 1)) !== -1) n += 1; return n; }

async function fix02(T) {
  const {ca, moPhien, DTO, KTO, ACK, DS, AP, chay, sao, timTatCa, coSaiDto, ENV, PEND, PEND2, KTR, URL_CT, URL_PDF, URL_LUU, URL_XN,
    NUT_LUU, NUT_XN, NUT_LAI, NUT_TAI, O_NT, O_TT, O_LY_DO} = T;
  const PEND3 = "5b5b5b5b-0000-4000-8000-00000000005b", DOT2 = "4b4b4b4b-0000-4000-8000-00000000004b", DOT3 = "4c4c4c4c-0000-4000-8000-00000000004c";
  const DONG = (pending, dot, env, revision, trang_thai) => ({kt_pending_id: pending, dot_id: dot, phong_bi_id: ENV[env].phong_bi_id,
    phong_bi_sha256: ENV[env].phong_bi_sha256, revision, trang_thai, ap: sao(AP)});
  const nutMo = P => timTatCa(P.vungKt(), e => e.tagName === "BUTTON" && (e.textContent === "Mở" || e.textContent === "Đang mở"));
  const SAI_DS = "Hộp chờ không đúng hợp đồng";
  const xemDuoc = P => !P.chuKt().includes(SAI_DS);

  // ================================================================ F2-1 hiển thị
  await ca("F2-1 hộp chờ trộn: CAN_KIEM_LAI (revision 1) + CAN_KIEM_LAI (null) + CHO_XAC_NHAN → hiển thị đủ 3 dòng, không SAI_DTO", async () => {
    const P = await moPhien({ds: DS([DONG(PEND, ENV.A.dot_id, "B", 1, "CAN_KIEM_LAI"), DONG(PEND2, DOT2, "A", null, "CAN_KIEM_LAI"),
      DONG(PEND3, DOT3, "A", null, "CHO_XAC_NHAN")])});
    assert.ok(xemDuoc(P), "dòng CAN_KIEM_LAI hợp lệ không được làm cả hộp chờ thành SAI_DTO");
    assert.strictEqual(nutMo(P).length, 3, "mỗi dòng có Mở");
    const t = P.chuKt();
    assert.ok(t.includes("Cần kiểm lại căn cứ"), "nhãn hộp chờ cho CAN_KIEM_LAI");
    assert.ok(t.includes("Chờ xác nhận") && t.includes("chưa có"), "dòng thường + revision null vẫn hiển thị");
    assert.ok(t.includes("5a5a5a5a-000") && t.includes("5b5b5b5b-000"));
    assert.strictEqual(P.dem(P.laGetKt), 1, "chỉ GET danh sách; không tự GET chi tiết từ dòng");
    assert.strictEqual(P.dem(P.laPostKt), 0);
  });

  // ================================================================ F2-2 Mở dòng CAN_KIEM_LAI → chi tiết typed, stale chỉ đọc
  await ca("F2-2 Mở CAN_KIEM_LAI → GET đúng root không query; chi tiết không hiện hành: nguồn + lịch sử + PDF đọc được, không nút lệnh, 0 POST", async () => {
    const P = await moPhien({ds: DS([DONG(PEND, ENV.A.dot_id, "B", 1, "CAN_KIEM_LAI"), DONG(PEND3, DOT3, "A", null, "CHO_XAC_NHAN")])});
    nutMo(P)[0].click(); await chay();
    const c = P.cho(c_ => c_.method === "GET" && c_.url.startsWith("/api/m4/ke-toan/"), "GET chi tiết");
    assert.strictEqual(c.url, URL_CT(PEND), "GET đúng root, không phong_bi_id/revision lấy từ dòng hộp chờ");
    const kt = KTO();
    await P.tra(c, 200, DTO({khongHienHanh: true, kt, lsKt: [{env: "A", kt}]}));  // literal: successor chưa seal → không row hiện hành, luu/xac_nhan false
    const t = P.chuKt();
    assert.ok(!coSaiDto(P), "chi tiết stale đúng hợp đồng phải hiển thị: " + P.statusKt());
    assert.ok(t.includes("Không còn hiện hành") && t.includes("Số nguồn đã niêm phong") && t.includes("Lịch sử phong bì nguồn") && t.includes("Revision đã lưu 1"));
    assert.ok(!P.nutKt(NUT_LUU) && !P.nutKt(NUT_XN), "không lệnh trên phong bì không hiện hành");
    assert.ok(!P.oKt(O_NT), "không form nháp");
    const nutTai = P.nutKt(NUT_TAI);
    assert.ok(nutTai && !nutTai.disabled, "PDF vẫn tải được theo quyền đọc hiện hành (không tự cấm mọi PDF)");
    const truoc = T.soClick();
    await P.bam(NUT_TAI);
    await P.tra(P.cho(P.get(URL_PDF("A")), "pdf"), 200, {}, 9);
    assert.strictEqual(T.soClick(), truoc + 1);
    assert.strictEqual(P.dem(P.laPostKt), 0);
  });

  // ================================================================ F2-3 dòng thường vẫn thao tác được
  await ca("F2-3 dòng thường cạnh CAN_KIEM_LAI: Mở → kt null → Lưu gửi expected_revision 0 từ GET (không từ dòng)", async () => {
    const P = await moPhien({ds: DS([DONG(PEND, ENV.A.dot_id, "A", null, "CHO_XAC_NHAN"), DONG(PEND2, DOT2, "B", 3, "CAN_KIEM_LAI")])});
    assert.ok(xemDuoc(P));
    await P.moHoSo(DTO(), "F2-3");
    assert.ok(P.nutKt(NUT_LUU) && !P.nutKt(NUT_LUU).disabled, "dòng thường không bị always-HOLD");
    P.go(O_NT, "1000000"); P.go(O_TT, "VND");
    await P.bam(NUT_LUU);
    const b = P.bodyCua(P.cho(P.post(URL_LUU), "luu"));
    assert.strictEqual(b.kt_pending_id, PEND); assert.strictEqual(b.phong_bi_id, ENV.A.phong_bi_id); assert.strictEqual(b.expected_revision, 0);
  });

  // ================================================================ F2-4 CAN_KIEM_LAI KHÔNG phải trạng thái KT đã lưu / ACK
  for (const [ten, lam] of [
    ["kt đã lưu", () => { const k = KTO({trang_thai: "CAN_KIEM_LAI"}); return DTO({kt: k, lsKt: [{env: "A", kt: k}]}); }],
    ["lịch sử KT", () => { const k1 = KTO({trang_thai: "CAN_KIEM_LAI"}), k2 = KTO({kt_revision_id: KTR(2), revision: 2});
      return DTO({kt: k2, lsKt: [{env: "A", kt: k1}, {env: "A", kt: k2}]}); }]]) {
    await ca(`F2-4a CAN_KIEM_LAI ở ${ten} → SAI_DTO, không nút lệnh, 0 POST`, async () => {
      const P = await moPhien();
      await P.moHoSo(lam(), ten);
      assert.ok(coSaiDto(P), ten + ": phải SAI_DTO");
      assert.ok(!P.nutKt(NUT_LUU) && !P.nutKt(NUT_XN));
      assert.strictEqual(P.dem(P.laPostKt), 0);
    });
  }
  for (const xn of [false, true]) {
    await ca(`F2-4b ACK ${xn ? "xác nhận" : "lưu"} trang_thai CAN_KIEM_LAI → CHƯA RÕ, không toast thành công; Gửi lại y nguyên cùng body/khóa`, async () => {
      const P = await moPhien();
      await P.moHoSo(DTO({kt: KTO()}), "F2-4b");
      if (!xn) P.go(O_LY_DO, "ghi chú");
      await P.bam(xn ? NUT_XN : NUT_LUU);
      const c1 = P.cho(P.post(xn ? URL_XN : URL_LUU), "lệnh");
      const g = P.dem(P.laGetKt);
      await P.tra(c1, 200, ACK("A", KTO({kt_revision_id: KTR(2), revision: 2, trang_thai: "CAN_KIEM_LAI"})));
      assert.ok(P.statusKt().includes("Chưa rõ kết quả"), "ACK trạng thái ngoài 3 trạng thái KT không được coi là thành công");
      assert.ok(!P.toast().includes("Đã lưu") && !P.toast().includes("Đã xác nhận"));
      assert.strictEqual(P.dem(P.laGetKt), g, "không GET như thành công");
      await P.bam(NUT_LAI);
      const c2 = P.cho(P.post(xn ? URL_XN : URL_LUU), "gửi lại");
      assert.strictEqual(c2.opts.body, c1.opts.body, "ý định gốc giữ nguyên từng byte (cùng khóa)");
    });
  }

  // ================================================================ F2-5 hộp chờ sai → SAI_DTO (không fallback)
  const dongHop = () => DONG(PEND, ENV.A.dot_id, "A", null, "CAN_KIEM_LAI");
  for (const [ten, sua] of [
    ["trạng thái lạ", r => { r.trang_thai = "HOLD"; }], ["chữ thường", r => { r.trang_thai = "can_kiem_lai"; }],
    ["trạng thái null", r => { r.trang_thai = null; }], ["thiếu trạng thái", r => { delete r.trang_thai; }],
    ["revision 0", r => { r.revision = 0; }], ["revision chuỗi", r => { r.revision = "1"; }],
    ["ap đã ghi", r => { r.ap = {trang_thai: "CHUA_TRIEN_KHAI_M4_03B", da_ghi_cong_no: true}; }], ["khóa thừa", r => { r.can_cu_hien_hanh = false; }],
    ["phong_bi_sha256 sai", r => { r.phong_bi_sha256 = "B".repeat(64); }]]) {
    await ca(`F2-5 hộp chờ ${ten} (cạnh dòng hợp lệ) → SAI_DTO, không dòng/không Mở`, async () => {
      const r = dongHop(); sua(r);
      const P = await moPhien({ds: DS([DONG(PEND3, DOT3, "A", null, "CHO_XAC_NHAN"), r])});
      assert.ok(P.chuKt().includes(SAI_DS), ten + ": phải SAI_DTO");
      assert.strictEqual(nutMo(P).length, 0, ten + ": không hiển thị dòng nào");
      assert.strictEqual(P.dem(P.laPostKt), 0);
    });
  }
}

(function chayGoc() {
  let raw;
  try { raw = fs.readFileSync(GOC); } catch (e) { console.log("SETUP FIX02_GOC_KHONG_DOC: " + e.message); process.exitCode = 1; return; }
  const sha = crypto.createHash("sha256").update(raw).digest("hex");
  if (sha !== SHA_GOC) { console.log("SETUP FIX02_GOC_SAI_HASH: " + sha + " ≠ " + SHA_GOC + " — không chạy (bản gốc phải bất biến)"); process.exitCode = 1; return; }
  let src = raw.toString("utf8").replace(/^﻿/, "");
  for (const [cu, moi] of DELTA) {
    if (demLan(src, cu) !== 1) { console.log("SETUP FIX02_DELTA_KHONG_KHOP: " + cu.trim()); process.exitCode = 1; return; }
    src = src.replace(cu, () => moi);
  }
  if (demLan(src, MOC) !== 1) { console.log("SETUP FIX02_MOC_INTEGRATION"); process.exitCode = 1; return; }
  const i = src.indexOf(MOC);
  src = src.slice(0, i) + CHEN + src.slice(i);
  console.log("FIX02 harness: bản gốc sha256 " + sha + " + delta title-reflection (2 dòng El giả, như FIX01) + ca FIX02 chèn trước INTEGRATION");
  const fn = vm.runInThisContext("(function (require, module, exports, __filename, __dirname, __FIX02) {" + src + "\n})", {filename: GOC});
  fn(require, module, exports, GOC, path.dirname(GOC), fix02);
})();
