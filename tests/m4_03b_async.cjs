"use strict";
// Dùng khung DOM/fetch M4 có sẵn, chỉ chạy ca 03B; fixture thủ công, không mạng/PG.
const fs = require("fs"), path = require("path"), vm = require("vm");
const source = fs.readFileSync(path.join(__dirname, "m4_03a_async.cjs"), "utf8");
let harness = source.slice(0, source.indexOf("async function main() {"));
if (!harness || !source.includes("async function main() {")) throw new Error("Thiếu khung test M4");
// Bổ sung API DOM chuẩn còn thiếu của fake DOM, không thay code sản phẩm/assertion.
harness = harness.replace("    focus() {} showModal() {} close() {}", `
    querySelectorAll(selector) {
      const result = [];
      const walk = e => { for (const c of e.children) { if (c.tagName === selector.toUpperCase()) result.push(c); walk(c); } };
      walk(this); return result;
    }
    focus() {} showModal() {} close() {}`);

async function cases(T) {
  const {assert, ca, moPhien, DTO, KTO, DS, sao, timTatCa, chay, ENV, PEND, PEND2, TEP1} = T;
  const U = n => "00000000-0000-4000-8000-" + String(n).padStart(12, "0");
  const schema = "M4_03B_DOI_CHIEU_CAN_CU_V1", root = U(80), otherRoot = U(81), sha = "b".repeat(64);
  const ref = (n, kind = "HOA_DON") => ({kind, occurrence_id: U(n), source_version_id: U(n + 100), part_id: null});
  const nt = {kind: "NT", occurrence_id: PEND, source_version_id: ENV.A.phong_bi_id, part_id: null};
  const tp = (nguon, more = {}) => ({nguon, phan: "TOAN_PHAN", so_tien_khai: null, tien_te: null, ...more});
  const invoice = (n, assigned = false) => ({nguon: ref(n), so_chuan: String(n), ky_hieu: "AA/26E", ngay_lap: "2026-10-25", tien_te: "USD",
    so_tien_doc_duoc: "1234.50", da_gan: assigned, da_gan_o: assigned ? [{doi_chieu_id: otherRoot, nhan: "đã gắn ở đối chiếu " + otherRoot}] : []});
  const data = (roots = [], noPermission = false) => ({schema, nguon_nt: nt,
    can_cu: {schema, doi_chieu: {graph_sha256: sha, goc_lien_quan: roots.map(doi_chieu_id => ({doi_chieu_id}))}, kt: {duoc_ghi: true, thieu: ["THIEU_HOA_DON"]}},
    goi_y: {khong_quyen: noPermission, hoa_don: noPermission ? [] : [invoice(21), invoice(22), invoice(23, true)]}});
  const version = (parts, rev = 1, status = "NHAP_DOI_CHIEU", extra = {}) => ({phien_ban_id: U(90 + rev), revision: rev, loai: rev % 2 ? "NHAP" : "XAC_NHAN",
    trang_thai: status, graph_sha256: sha, thieu: [], tao_luc: "2026-10-26T03:00:00Z", ly_do: "Căn cứ đã kiểm tra",
    noi_dung: {thanh_phan: parts, can_cu_tep: [{id: TEP1}], ly_do: "Căn cứ đã kiểm tra"}, ...extra});
  const history = versions => ({schema, doi_chieu_id: root, doi_chieu: {graph_sha256: sha, phien_ban: versions},
    kt: {duoc_ghi: true, phan_khai_con_thieu: [{so_tien_con_thieu: "50", tien_te: "USD", ly_do: null}]}});
  const ack = (rev, status) => ({schema, doi_chieu: {doi_chieu_id: root, phien_ban_id: U(90 + rev), revision: rev, graph_sha256: sha, trang_thai: status}});
  const card = P => P.vungKt().querySelector(".m4-03b");
  const countDc = P => P.calls.filter(c => c.method === "POST" && c.url.includes("/doi-chieu/")).length;
  const confirmed = () => DTO({kt: KTO({trang_thai: "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO"}), quyen: {luu: false, xac_nhan: false}});
  async function open(d = data(), h = null, opt = {}) {
    const P = await moPhien(opt); await P.moHoSo(confirmed());
    await P.bam("Mở đối chiếu"); await P.tra(P.cho(P.get("/api/m4/doi-chieu/dot/" + PEND), "đọc theo đợt"), 200, d);
    for (const row of (opt.ds && opt.ds.items || []).filter(r => r.trang_thai === "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO" && r.kt_pending_id !== PEND)) {
      const detail = opt.details && opt.details[row.kt_pending_id] || confirmed(); detail.context.kt_pending_id = row.kt_pending_id;
      await P.tra(P.cho(P.get("/api/m4/ke-toan/" + row.kt_pending_id), "đọc đợt ứng viên"), 200, detail);
    }
    if (h) await P.tra(P.cho(P.get("/api/m4/doi-chieu/lich-su/" + root), "lịch sử"), 200, h);
    return P;
  }
  async function save(P, parts) {
    await P.bam("Lưu nháp đối chiếu");
    const preview = P.cho(P.post("/api/m4/doi-chieu/xem"), "xem đồ thị");
    assert.deepStrictEqual(P.bodyCua(preview).nguon, parts.map(t => t.nguon));
    await P.tra(preview, 200, {schema, doi_chieu: {graph_sha256: sha}, kt: {duoc_ghi: true}});
    return P.cho(P.post("/api/m4/doi-chieu/luu"), "lưu nháp");
  }
  await ca("03B-1 chỉ hiện khối ngay dưới số kế toán của đợt đã xác nhận", async () => {
    const P = await moPhien(); await P.moHoSo(DTO()); assert.strictEqual(card(P), null);
    const Q = await moPhien(); await Q.moHoSo(confirmed());
    assert.ok(card(Q)); const parent = card(Q).parent, i = parent.children.indexOf(card(Q));
    assert.ok(parent.children[i - 1]._cls.has("m4-kt-so"));
    assert.strictEqual(countDc(Q), 0);
  });
  await ca("03B-2 danh sách theo thứ tự máy chủ, không tự chọn; tiếng Việt/ngày/đơn vị/không mã kỹ thuật", async () => {
    const P = await open(); const text = card(P).textContent;
    assert.ok(text.indexOf("Hóa đơn 21") < text.indexOf("Hóa đơn 22"));
    assert.ok(text.includes("25/10/2026") && text.includes("1.234,50 USD"));
    assert.ok(text.includes("hóa đơn chưa gắn đợt"));
    assert.ok(!P.vungKt().textContent.includes("Cần Anh"));
    assert.ok(text.includes("Chọn tệp căn cứ đã có trong hồ sơ nghiệm thu. Tải tệp mới do phòng dự án thực hiện."));
    assert.strictEqual(timTatCa(card(P), e => e.tagName === "SELECT" && (e.attrs["aria-label"] || "").startsWith("Phạm vi nguồn")).length, 1);
    assert.ok(!/công nợ|[0-9a-f]{8}-[0-9a-f-]{27,}|NHAP_DOI_CHIEU|THIEU_HOA_DON|graph_sha256|M4_03B/i.test(text));
    assert.strictEqual(countDc(P), 0);
  });
  await ca("03B-3 một phần thiếu số tiền: xác nhận mờ và có lý do, vẫn lưu nháp thiếu", async () => {
    const P = await open(); await P.bam("Chọn hóa đơn 21");
    await P.chonSel("Phạm vi nguồn 2", "MOT_PHAN"); await P.chonSel("Đơn vị nguồn 2", "USD");
    P.go("Lý do đối chiếu", "Còn chờ số tiền");
    const b = P.nutKt("Xác nhận đối chiếu"); assert.ok(b.disabled && b.title.includes("số tiền"));
    assert.ok(card(P).textContent.includes("Một phần bắt buộc nhập số tiền"));
    await P.bamEp("Xác nhận đối chiếu"); assert.strictEqual(countDc(P), 0);
    const parts = [tp(nt), tp(ref(21), {phan: "MOT_PHAN", so_tien_khai: null, tien_te: "USD"})];
    const c = await save(P, parts); assert.strictEqual(P.bodyCua(c).thanh_phan[1].so_tien_khai, null);
  });
  await ca("03B-4 hóa đơn đã gắn nơi khác bị chặn, kể cả gọi handler cưỡng bức", async () => {
    const P = await open(); const b = P.nutKt("Chọn hóa đơn 23");
    assert.ok(b.disabled && card(P).textContent.includes("đã gắn ở đối chiếu"));
    b.disabled = false; b.click(); await chay();
    assert.ok(!P.oKt("Phạm vi nguồn 2")); assert.strictEqual(countDc(P), 0);
  });
  await ca("03B-5 lưu → xác nhận đúng bản nháp → khóa → sửa cùng gốc thành phiên bản mới", async () => {
    const P = await open(); await P.bam("Chọn hóa đơn 21"); await P.bam("Chọn hóa đơn 22");
    await P.chonSel("Phạm vi nguồn 2", "MOT_PHAN"); await P.chonSel("Đơn vị nguồn 2", "USD");
    P.go("Số tiền một phần nguồn 2", "50.25"); P.go("Lý do đối chiếu", "Căn cứ đã kiểm tra");
    const chk = P.oKt("Tệp căn cứ hoa_don_gtgt_dot_1.pdf"); chk.checked = true; chk.dispatch("change"); await chay();
    const parts = [tp(nt), tp(ref(21), {phan: "MOT_PHAN", so_tien_khai: "50.25", tien_te: "USD"}), tp(ref(22))];
    const c = await save(P, parts), body = P.bodyCua(c);
    assert.strictEqual(body.expected_revision, 0); assert.strictEqual(body.doi_chieu_id, null); assert.deepStrictEqual(body.can_cu_tep, [TEP1]);
    assert.ok(!("actor" in body) && !("phap_nhan_id" in body));
    await P.tra(c, 200, ack(1, "NHAP_DOI_CHIEU"));
    const p1 = version(parts); await P.tra(P.cho(P.get("/api/m4/doi-chieu/lich-su/" + root), "bản vừa lưu"), 200, history([p1]));
    assert.ok(!P.nutKt("Xác nhận đối chiếu").disabled);
    await P.bam("Xác nhận đối chiếu"); const xn = P.cho(P.post("/api/m4/doi-chieu/xac-nhan"), "xác nhận");
    assert.deepStrictEqual(P.bodyCua(xn), {doi_chieu_id: root, phien_ban_id: p1.phien_ban_id, expected_revision: 1, expected_graph: sha, khoa: P.bodyCua(xn).khoa});
    await P.tra(xn, 200, ack(2, "KT_XAC_NHAN_CAN_CU"));
    const p2 = version(parts, 2, "KT_XAC_NHAN_CAN_CU");
    await P.tra(P.cho(P.get("/api/m4/doi-chieu/lich-su/" + root), "bản khóa"), 200, history([p1, p2]));
    assert.ok(P.nutKt("Lưu nháp đối chiếu").disabled && P.oKt("Phạm vi nguồn 2").disabled);
    assert.ok(card(P).textContent.includes("Phiên bản 1") && card(P).textContent.includes("Phiên bản 2") && card(P).textContent.includes("50 USD"));
    await P.bam("Sửa bằng phiên bản mới"); P.go("Lý do đối chiếu", "Bổ sung căn cứ");
    const c2 = await save(P, parts); assert.strictEqual(P.bodyCua(c2).doi_chieu_id, root); assert.strictEqual(P.bodyCua(c2).expected_revision, 2);
  });
  await ca("03B-6 nguồn thay đổi: Cần kiểm lại, không xác nhận bản cũ", async () => {
    const p = version([tp(nt), tp(ref(21))], 2, "CAN_KIEM_LAI");
    const P = await open(data([root]), history([p]));
    assert.ok(card(P).textContent.includes("Cần kiểm lại")); assert.ok(P.nutKt("Xác nhận đối chiếu").disabled);
    await P.bamEp("Xác nhận đối chiếu"); assert.strictEqual(countDc(P), 0);
    await P.bam("Sửa bằng phiên bản mới"); assert.ok(!P.oKt("Phạm vi nguồn 2").disabled);
  });
  await ca("03B-7 thiếu quyền M2 ẩn danh sách; thu hồi quyền gỡ căn cứ", async () => {
    const P = await open(data([], true)); assert.ok(card(P).textContent.includes("Không có quyền đọc hóa đơn"));
    assert.ok(!P.nutKt("Chọn hóa đơn 21"));
    const Q = await open(); await Q.bam("Tải lại căn cứ đối chiếu");
    const message = "Quyền đọc căn cứ đối chiếu đã bị thu hồi";
    await Q.tra(Q.cho(Q.get("/api/m4/doi-chieu/dot/" + PEND), "thu hồi"), 403, {error: "FORBIDDEN", message});
    assert.ok(card(Q).textContent.includes(message));
    assert.ok(!card(Q).textContent.includes("Không lưu được"));
    assert.ok(!card(Q).textContent.includes("Hóa đơn 21") && !Q.nutKt("Lưu nháp đối chiếu"));
  });
  await ca("03B-8 phản hồi đọc về muộn sau rời màn không vẽ lại", async () => {
    const P = await moPhien(); await P.moHoSo(confirmed()); await P.bam("Mở đối chiếu");
    const c = P.cho(P.get("/api/m4/doi-chieu/dot/" + PEND), "đọc chậm");
    await P.roiM4(); const before = P.calls.length, text = P.$("m4-kt").textContent;
    await P.tra(c, 200, data()); assert.strictEqual(P.calls.length, before); assert.strictEqual(P.$("m4-kt").textContent, text);
  });
  await ca("03B-9 kết quả chưa rõ: khóa lệnh mới, gửi lại nguyên body và khóa", async () => {
    const P = await open(); await P.bam("Chọn hóa đơn 21"); P.go("Lý do đối chiếu", "Kiểm tra");
    const c = await save(P, [tp(nt), tp(ref(21))]); c.reject(new TypeError("mất mạng")); await chay();
    assert.ok(P.nutKt("Lưu nháp đối chiếu").disabled && card(P).textContent.includes("Chưa rõ kết quả"));
    await P.bam("Gửi lại đối chiếu y nguyên"); const retry = P.cho(P.post("/api/m4/doi-chieu/luu"), "gửi lại");
    assert.strictEqual(retry.opts.body, c.opts.body);
  });
  await ca("03B-10 nhiều đợt và nhiều hóa đơn trong cùng đối chiếu", async () => {
    const d = DS(); d.items.push({...sao(d.items[0]), kt_pending_id: PEND2, trang_thai: "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO"});
    const P = await open(data(), null, {ds: d}); await P.chonSel("Thêm đợt đã xác nhận", PEND2);
    const c = P.cho(P.get("/api/m4/ke-toan/" + PEND2), "đợt bổ sung"); const ct = confirmed(); ct.context.kt_pending_id = PEND2;
    ct.nguon.tep_can_cu.push({id: U(40), ten: "Bien ban dot bo sung.pdf"});
    await P.tra(c, 200, ct); await P.bam("Chọn hóa đơn 21"); await P.bam("Chọn hóa đơn 22");
    assert.ok(P.oKt("Tệp căn cứ Bien ban dot bo sung.pdf"));
    P.go("Lý do đối chiếu", "Nhóm nhiều đợt");
    await P.bam("Lưu nháp đối chiếu");
    const preview = P.bodyCua(P.cho(P.post("/api/m4/doi-chieu/xem"), "đồ thị nhiều nguồn"));
    assert.strictEqual(preview.nguon.filter(r => r.kind === "NT").length, 2); assert.strictEqual(preview.nguon.filter(r => r.kind === "HOA_DON").length, 2);
  });
  await ca("03B-11 nguồn nghiệm thu đổi giữa hai lần đọc: chặn sửa và yêu cầu kiểm lại", async () => {
    const d = sao(data()); d.nguon_nt.source_version_id = ENV.B.phong_bi_id;
    const P = await open(d);
    assert.ok(card(P).textContent.includes("Cần kiểm lại")); assert.ok(!P.nutKt("Lưu nháp đối chiếu")); assert.strictEqual(countDc(P), 0);
  });
  await ca("03B-12 hóa đơn của chính đối chiếu đang sửa không bị chặn nhầm", async () => {
    const d = data([root]); d.goi_y.hoa_don[0].da_gan_o = [{doi_chieu_id: root}];
    const P = await open(d, history([version([tp(nt), tp(ref(21))])]));
    assert.ok(!P.nutKt("Xác nhận đối chiếu").disabled); assert.ok(!card(P).textContent.includes("Hóa đơn đã gắn ở đối chiếu khác"));
  });
  await ca("03B-13 mã DC thành hướng dẫn tiếng Việt, xung đột tải lại thật", async () => {
    const rows = [
      ["DC_REVISION_CU", "Đối chiếu đã đổi ở nơi khác — đã tải lại, kiểm rồi làm lại.", true],
      ["DC_DO_THI_DOI", "Đối chiếu đã đổi ở nơi khác — đã tải lại, kiểm rồi làm lại.", true],
      ["DC_CAN_KIEM_LAI", "Nguồn đã đổi — cần kiểm lại trước khi xác nhận."],
      ["DC_HOA_DON_DA_GAN", "Hóa đơn đã gắn ở đối chiếu khác — tải lại và chọn hóa đơn chưa gắn."],
      ["DC_MA_MOI", "Không lưu được — tải lại rồi thử lại."]
    ];
    for (const [code, message, reload] of rows) for (const field of ["error", "message"]) {
      const P = await open(); await P.bam("Chọn hóa đơn 21"); P.go("Lý do đối chiếu", "Kiểm tra");
      const c = await save(P, [tp(nt), tp(ref(21))]);
      await P.tra(c, 409, {[field]: field === "error" ? code : "CSDL từ chối thao tác (" + code + ")"});
      if (reload) await P.tra(P.cho(P.get("/api/m4/doi-chieu/dot/" + PEND), "tải lại sau xung đột"), 200, data());
      assert.ok(card(P).textContent.includes(message), code + ": " + card(P).textContent);
      assert.ok(!card(P).textContent.includes("(cần kiểm tra)") && !card(P).textContent.includes(code));
      assert.strictEqual(countDc(P), 2, "không tự gửi lại lệnh ghi");
    }
  });
  await ca("03B-14 định dạng số tiền rõ ràng, giữ nguyên nội dung người gõ", async () => {
    const P = await open(); await P.bam("Chọn hóa đơn 21");
    await P.chonSel("Phạm vi nguồn 2", "MOT_PHAN"); await P.chonSel("Đơn vị nguồn 2", "USD");
    const input = P.oKt("Số tiền một phần nguồn 2");
    assert.ok(input.getAttribute("placeholder").includes("dấu chấm thập phân: 1234.50"));
    P.go("Số tiền một phần nguồn 2", "1.234,50");
    assert.strictEqual(input.value, "1.234,50");
    assert.ok(P.nutKt("Xác nhận đối chiếu").title.includes("không dấu phân cách hàng nghìn"));
    assert.ok(card(P).textContent.includes("VND: 1234 (số nguyên)"));
    await P.chonSel("Đơn vị nguồn 2", "USD");
    assert.strictEqual(P.oKt("Số tiền một phần nguồn 2").value, "1.234,50");
  });
  await ca("03B-15 chỉ liệt kê đợt cùng hợp đồng, nhãn dùng số đợt thật/ngày/tiền", async () => {
    const d = DS(), wrong = U(201), same = U(202), stale = U(204);
    for (const id of [wrong, same, stale]) d.items.push({...sao(d.items[0]), kt_pending_id: id, trang_thai: "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO"});
    const a = confirmed(), b = confirmed(), c = confirmed(); a.context.hop_dong_id = U(203); c.can_cu_hien_hanh = false;
    a.dot = {so_dot: 3}; b.dot = {so_dot: 8, ngay_nghiem_thu: "2026-10-25"}; b.kt.gia_tri_nt_xac_nhan = "1234.50"; b.kt.tien_te = "USD";
    const P = await open(data(), null, {ds: d, details: {[wrong]: a, [same]: b, [stale]: c}});
    const options = P.oKt("Thêm đợt đã xác nhận").children;
    assert.deepStrictEqual(options.map(o => o.value), ["", same]);
    assert.strictEqual(options[1].textContent, "Đợt 8 · 25/10/2026 · 1.234,50 USD");
  });
  await ca("03B-16 lỗi mạng đọc căn cứ/lịch sử/thêm đợt dùng câu Việt", async () => {
    const viet = "Mất kết nối với ứng dụng trên máy — chưa rõ máy chủ đã ghi hay chưa";
    const P = await moPhien(); await P.moHoSo(confirmed()); await P.bam("Mở đối chiếu");
    P.cho(P.get("/api/m4/doi-chieu/dot/" + PEND), "mạng đọc").reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(card(P).textContent.includes(viet)); assert.ok(!card(P).textContent.includes("Failed to fetch"));
    const Q = await open(data([root, otherRoot])); await Q.bam("Xem đối chiếu 1");
    Q.cho(Q.get("/api/m4/doi-chieu/lich-su/" + root), "mạng lịch sử").reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(card(Q).textContent.includes(viet)); assert.ok(!card(Q).textContent.includes("Failed to fetch"));
    const d = DS(); d.items.push({...sao(d.items[0]), kt_pending_id: PEND2, trang_thai: "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO"});
    const R = await open(data(), null, {ds: d}); await R.chonSel("Thêm đợt đã xác nhận", PEND2);
    R.cho(R.get("/api/m4/ke-toan/" + PEND2), "mạng thêm đợt").reject(new TypeError("Failed to fetch")); await chay();
    assert.ok(card(R).textContent.includes(viet)); assert.ok(!card(R).textContent.includes("Failed to fetch"));
  });
  await ca("03B-17 lỗi chỉ đọc không mã DC giữ thông báo máy chủ", async () => {
    for (const route of ["dot/" + PEND, "lich-su/" + root]) for (const status of [400, 404, 500]) {
      const P = await open(data([root, otherRoot]));
      if (route.startsWith("dot/")) await P.bam("Tải lại căn cứ đối chiếu");
      else await P.bam("Xem đối chiếu 1");
      const message = "Máy chủ chưa đọc được căn cứ đối chiếu (" + status + ")";
      await P.tra(P.cho(P.get("/api/m4/doi-chieu/" + route), "lỗi chỉ đọc"), status, {error: "HTTP_" + status, message});
      assert.ok(card(P).textContent.includes(message), card(P).textContent);
      assert.ok(!card(P).textContent.includes("Không lưu được"));
      assert.strictEqual(countDc(P), 0);
    }
    const P = await open(); await P.bam("Tải lại căn cứ đối chiếu");
    await P.tra(P.cho(P.get("/api/m4/doi-chieu/dot/" + PEND), "mã DC mới khi đọc"), 400, {error: "DC_MA_MOI"});
    assert.ok(card(P).textContent.includes("Không đọc được"));
    assert.ok(!card(P).textContent.includes("Không lưu được"));
  });
  for (const failure of [400, 409, 500, "mạng", "JSON"]) await ca("03B-18 ứng viên lỗi " + failure + " không cản mở khối/lịch sử", async () => {
    const d = DS(), good = U(205);
    for (const id of [PEND2, good]) d.items.push({...sao(d.items[0]), kt_pending_id: id, trang_thai: "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO"});
    const P = await moPhien({ds: d}); await P.moHoSo(confirmed()); await P.bam("Mở đối chiếu");
    await P.tra(P.cho(P.get("/api/m4/doi-chieu/dot/" + PEND), "căn cứ"), 200, data([root]));
    const bad = P.cho(P.get("/api/m4/ke-toan/" + PEND2), "ứng viên lỗi");
    if (failure === "mạng") { bad.reject(new TypeError("Failed to fetch")); await chay(); }
    else if (failure === "JSON") { bad.resolve({ok: true, status: 200, json: async () => { throw new SyntaxError("JSON không trọn"); }}); await chay(); }
    else await P.tra(bad, failure, {message: "Không đọc được ứng viên"});
    const detail = confirmed(); detail.context.kt_pending_id = good; detail.dot = {so_dot: 9};
    await P.tra(P.cho(P.get("/api/m4/ke-toan/" + good), "ứng viên còn lại"), 200, detail);
    await P.tra(P.cho(P.get("/api/m4/doi-chieu/lich-su/" + root), "lịch sử vẫn nạp"), 200, history([version([tp(nt), tp(ref(21))])]));
    assert.deepStrictEqual(P.oKt("Thêm đợt đã xác nhận").children.map(o => o.value), ["", good]);
    assert.ok(card(P).textContent.includes("Hóa đơn 21") && card(P).textContent.includes("Phiên bản 1"));
    assert.ok(!P.nutKt("Lưu nháp đối chiếu").disabled);
    assert.ok(!card(P).textContent.includes("Chỉ chọn đợt đã xác nhận"));
    assert.ok(!card(P).textContent.includes("Failed to fetch"));
    assert.strictEqual(countDc(P), 0);
  });
}

const tail = `
__cases({assert, ca, moPhien, DTO, KTO, DS, sao, timTatCa, chay, ENV, PEND, PEND2, TEP1, U}).then(() => {
  console.log(JSON.stringify({dat: KQ.dat.length, hong: KQ.hong, setup_errors: KQ.setup_errors}));
  process.exitCode = KQ.hong.length || KQ.setup_errors.length ? 1 : 0;
}, e => { console.error(e); process.exitCode = 1; });`;
const run = vm.runInThisContext("(function(require, module, exports, __filename, __dirname, __cases) {\n" + harness + tail + "\n})");
run(require, module, exports, __filename, __dirname, cases);
