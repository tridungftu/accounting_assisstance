"use strict";
// M4-03A — chế độ "Kế toán nghiệm thu" của Cổng hồ sơ M4: hộp chờ KT (root pending do M24 tạo khi seal duyệt + PDF), đọc phong bì nguồn đã niêm phong
// (hiện hành hoặc lịch sử), lưu nháp số liệu kế toán tách khỏi số nguồn, XÁC NHẬN riêng đúng revision đã lưu. Không ghi công nợ/AP (M4-03B), không
// tạo/gửi Request (M4-04), không tính VAT/tỷ giá/tài khoản.
// Hợp đồng: docs/M4-03A-API-CONTRACT.md + docs/M4-03A-CANONICAL-API-ADDENDUM-01.md (schema M4_03A_KT_V1): GET /api/m4/ke-toan,
// GET /api/m4/ke-toan/<kt_pending_id>[?phong_bi_id=], GET /api/m4/ke-toan/<kt_pending_id>/phong-bi/<phong_bi_id>/pdf, POST ke-toan/luu | ke-toan/xac-nhan.
// Máy chủ sở hữu MỌI sự thật: danh tính, quyền KT hiện hành, context/hash, revision, trạng thái, tệp căn cứ. Trình duyệt chỉ gửi ID/revision/hash đọc từ
// GET typed hợp lệ + chuỗi thập phân/mã/lý do + khóa. kt=null là trạng thái đầu tường minh (expected_revision 0 CHỈ cho lần lưu nháp đầu); không đọc
// alias (kt.id, revision top-level…), không suy revision 0 từ trường vắng. Danh sách hộp chờ chỉ để hiển thị/chọn — lệnh luôn lấy từ GET chi tiết.
// Backend chưa compose (503 M4_KT_CHUA_NOI / 404 route / 501) → "Chưa nối backend kế toán", không lệnh nào chạy; nguon.tep_can_cu vắng → HOLD phụ thuộc
// (chỉ đọc, giữ nháp, không POST); DTO sai kiểu → SAI_DTO (không hiển thị, không lệnh). Mọi chuỗi nguồn hiển thị bằng textContent.
// Vòng đời: shell m4.js gọi ve(vùng, {nguoi}) / huy() ĐỒNG BỘ ở đổi vai/đổi chế độ/rời #m4; người tham gia cổng đổi vai chung "m4_ke_toan".
// Fence = incarnation + khóa danh tính + thế hệ view (hồ sơ/phong bì chọn, context đầy đủ đổi kể cả A→B→A, thu hồi) + thế hệ form + vé GET — kiểm sau
// MỌI await (response/json/blob) và ngay trước DOM/toast/GET/click. Ý định: một bản ghi chính xác (route, body chuỗi, khóa, context gốc); chưa rõ kết quả
// → chỉ Gửi lại y nguyên bản ghi đó dưới quyền hiện hành; lệnh mới trên cùng hồ sơ KT bị chặn tới khi rõ. Hoàn tất cũ chỉ cập nhật bản ghi của nó.
(() => {
  const K = window.kttChung;
  if (!K) return;  // shell chưa có seam
  const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || "";
  const SCHEMA = "M4_03A_KT_V1", VAI = "m4_ke_toan", TOI_DA_Y_DINH = 32;
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, HEX64 = /^[0-9a-f]{64}$/;
  // cùng validator nguồn (m4/duyet_dot.py): tiền ≤ 2 chữ số thập phân không số 0 thừa, khối lượng ≤ 6, tiền tệ mã 3 chữ hoa — không qua Number
  const TIEN = /^(0|[1-9][0-9]{0,17})(\.[0-9]?[1-9])?$/, KL = /^(0|[1-9][0-9]{0,17})(\.[0-9]{0,5}[1-9])?$/, MA_TIEN_TE = /^[A-Z]{3}$/;
  const laUuid = v => typeof v === "string" && UUID.test(v);
  const laHex = v => typeof v === "string" && HEX64.test(v);
  const laTien = v => v === null || (typeof v === "string" && TIEN.test(v));
  const laKl = v => v === null || (typeof v === "string" && KL.test(v));
  const laTienTe = v => v === null || (typeof v === "string" && MA_TIEN_TE.test(v));
  const laChuoiHoacNull = v => v === null || typeof v === "string";
  const laNguyenDuong = v => Number.isInteger(v) && v >= 1;
  const laDoiTuong = v => !!v && typeof v === "object" && !Array.isArray(v);
  const co = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const DA_XAC_NHAN = "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO";
  const TT_KT = {CHO_XAC_NHAN: ["Chờ xác nhận", "m4-thieu"], CHO_BO_SUNG: ["Chờ bổ sung", "m4-thieu"],
    [DA_XAC_NHAN]: ["Đã xác nhận nghiệm thu — chờ ghi công nợ", "m4-du"]};
  // FIX02: trạng thái CHỈ của dòng hộp chờ (hiển thị) = 3 trạng thái KT + CAN_KIEM_LAI (phong bì mới nhất không hiện hành/toàn vẹn — producer
  // trang_thai_dong). KHÔNG dùng cho kt đã lưu/ACK (kiemKt/kiemAck giữ TT_KT); dòng không cấp context/revision/quyền — lệnh luôn từ GET chi tiết
  const TT_DS = {...TT_KT, CAN_KIEM_LAI: ["Cần kiểm lại căn cứ", "m4-loi"]};
  const CO_SO = {TRUOC_VAT: "Trước VAT", GOM_VAT: "Gồm VAT", CHUA_RO: "Chưa rõ"};
  const VAT = {CHUA_DU: "Chưa đủ căn cứ (giữ thiếu — không hiểu là không VAT)", CO_CAN_CU: "Có căn cứ VAT (tệp thật + trích dẫn)",
    KHONG_AP_DUNG: "Không áp dụng VAT (cần lý do)"};
  const CTX = ["phap_nhan_id", "du_an_id", "hop_dong_id", "dot_id", "kt_pending_id", "phong_bi_id", "seal_id", "version_id", "ket_luan_id", "pdf_id",
    "phong_bi_sha256", "graph_sha256", "pdf_sha256"];
  const CTX_HEX = new Set(["phong_bi_sha256", "graph_sha256", "pdf_sha256"]);
  const KT_KEYS = ["kt_revision_id", "revision", "trang_thai", "gia_tri_nt_xac_nhan", "tien_te", "co_so_gia_tri", "tam_ung_xac_nhan", "thu_hoi_xac_nhan",
    "giu_lai_xac_nhan", "vat_trang_thai", "vat_can_cu_tep_id", "vat_trich_dan", "ly_do"];
  const TIEN_KT = [["gia_tri_nt_xac_nhan", "Giá trị NT xác nhận", "gia_tri_nt"], ["tam_ung_xac_nhan", "Tạm ứng xác nhận", "tam_ung"],
    ["thu_hoi_xac_nhan", "Thu hồi xác nhận", "thu_hoi"], ["giu_lai_xac_nhan", "Giữ lại xác nhận", "giu_lai"]];
  const TIEN_NGUON = [["gia_tri_nt", "Giá trị nghiệm thu chấp nhận (NT)"], ["so_xin_thanh_toan", "Số xin thanh toán kỳ này (TT)"], ["tam_ung", "Tạm ứng kỳ này"],
    ["thu_hoi", "Thu hồi tạm ứng"], ["giu_lai", "Giữ lại"]];
  const NGUON_KEYS = ["gia_tri_nt", "so_xin_thanh_toan", "tam_ung", "thu_hoi", "giu_lai", "tien_te", "dong", "pdf"];  // tep_can_cu kiểm riêng (HOLD)
  const HANH = {LUU: {path: "ke-toan/luu", ten: "lưu nháp kế toán"}, XAC_NHAN: {path: "ke-toan/xac-nhan", ten: "xác nhận nghiệm thu"}};
  const MAT_KET_NOI = "Mất kết nối với ứng dụng trên máy — chưa rõ máy chủ đã ghi hay chưa";
  const h12 = v => (typeof v === "string" && v ? v.slice(0, 12) + "…" : "—");
  const chu = v => (v === null || v === undefined ? "" : String(v));
  const thieuNeu = v => (v === null || v === undefined || v === "" ? "(thiếu)" : String(v));  // null hiện "(thiếu)" — "0" vẫn là "0"

  function el(tag, props, ...con) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === "class") e.className = v; else if (k === "text") e.textContent = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (k === "value") e.value = v; else if (k === "disabled") e.disabled = !!v; else e.setAttribute(k, v === true ? "" : String(v));
    }
    for (const c of con.flat()) if (c !== null && c !== undefined && c !== false) e.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return e;
  }
  const nho = (t, cls) => el("p", {class: "m4-nho" + (cls ? " " + cls : ""), text: t});
  const pill = (t, cls) => el("span", {class: "m4-pill " + (cls || "m4-xam"), text: t});
  function nut(text, fn, cls, tat, title) {
    const b = el("button", {type: "button", class: cls || "", text, title: title || undefined});
    b.disabled = !!tat;
    b.addEventListener("click", () => { if (!b.disabled) fn(b); });
    return b;
  }
  function bang(headers, rows) {
    const t = el("table", {}, el("thead", {}, el("tr", {}, headers.map(h => el("th", {text: h})))),
      el("tbody", {}, rows.map(r => el("tr", {}, r.map(c => (c instanceof Node ? el("td", {}, c) : el("td", {text: chu(c)})))))));
    return el("div", {class: "m4-bang"}, t);
  }

  // ------------------------------------------------------------------ trạng thái
  let inc = null, hoatDong = false, box = null, khoaCtx = "";
  let genView = 0, genGet = 0, genForm = 0, genDs = 0;
  let ds = null, dsTinhTrang = "CHUA", dsLoi = "";  // dsTinhTrang: CHUA|DANG|OK|CHUA_NOI|KHONG_QUYEN|SAI_DTO|LOI
  let pendingChon = null, phongBiChon = null;      // phongBiChon null = phong bì mới nhất do máy chủ chọn; UUID = lấy từ lich_su.phong_bi[].context
  let dto = null, tinhTrang = "CHUA", loiGet = "", thuHoi = false, statusChu = "", statusLoi = false;  // tinhTrang: CHUA|DANG|OK|HOLD|CHUA_NOI|KHONG_QUYEN|SAI_DTO|LOI
  let ctxView = undefined;  // chuỗi context đầy đủ của DTO áp dụng gần nhất trong lựa chọn hiện tại — đổi = đổi view (genView, chống A→B→A)
  const nhapMap = new Map();  // nháp theo phong bì: "kt_pending_id|phong_bi_id" → chuỗi form (trống = thiếu ≠ "0")
  // bản ghi ý định chính xác: id → {loai, path, ctxKey, pending, phongBi, ctxGoc, body, bodyText, khoa, inc, trang, bay, soLan, gf, dkey, ketQua, loi}
  const yDinh = new Map();
  let soYDinh = 0;
  const taoKhoa = () => "m4kt-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));
  const vungSong = () => hoatDong && !!box && box.isConnected;
  function fenceInc() { const i = inc, k = khoaCtx; return () => vungSong() && i === inc && k === khoaCtx; }
  function fenceView() { const i = inc, k = khoaCtx, v = genView; return () => vungSong() && i === inc && k === khoaCtx && v === genView; }
  const chuoiCtx = c => JSON.stringify(CTX.map(t => c[t]));
  const khoaNhap = () => (dto ? dto.context.kt_pending_id + "|" + dto.context.phong_bi_id : null);
  const recMo = pending => [...yDinh.values()].find(r => r.ctxKey === khoaCtx && r.pending === pending && r.trang !== "RO") || null;
  function donYDinh() { for (const [id, r] of yDinh) { if (yDinh.size <= TOI_DA_Y_DINH) break; if (r.trang === "RO") yDinh.delete(id); } }
  function trangThai(msg, loi = false) {
    statusChu = msg || ""; statusLoi = !!loi;
    const s = box && box.querySelector(".m4-kt-status");
    if (s) { s.textContent = statusChu; s.className = "m4-kt-status m4-status" + (statusLoi ? " m4-loi-chu" : ""); }
  }
  function xoaNhapCua(pending) { for (const k of [...nhapMap.keys()]) if (k.startsWith(pending + "|")) nhapMap.delete(k); }
  // thu hồi (403/404 hoặc 200 xem=false): gỡ bằng chứng + vô hiệu view ĐỒNG BỘ; bản ghi ý định CHƯA RÕ giữ nguyên (không gửi, chờ quyền hiện hành)
  function thuHoiView(msg) {
    if (pendingChon) xoaNhapCua(pendingChon);
    dto = null; genView += 1; genForm += 1; thuHoi = true; tinhTrang = "KHONG_QUYEN"; ctxView = undefined; loiGet = msg || "";
    trangThai((msg || "Không có quyền") + " — đã gỡ hồ sơ kế toán khỏi màn hình (quyền KT hiện hành do máy chủ kiểm).", true);
  }

  // ------------------------------------------------------------------ kiểm DTO (không trường nào ngoài hợp đồng làm authority)
  const laChuaNoiMa = c => typeof c === "string" && /CHUA_NOI/.test(c);
  function chuaNoiLoi(status, e) { return status === 501 || (status === 404 && (!e.error || e.error === "NOT_FOUND" || e.error === "HTTP_404")) || laChuaNoiMa(e.error); }
  const apDung = a => laDoiTuong(a) && Object.keys(a).length === 2 && a.trang_thai === "CHUA_TRIEN_KHAI_M4_03B" && a.da_ghi_cong_no === false;
  const rqDung = r => laDoiTuong(r) && Object.keys(r).length === 1 && r.trang_thai === "CHUA_NOI_M4_04";
  function kiemCtx(c) {
    if (!laDoiTuong(c) || Object.keys(c).length !== CTX.length) return "context không đúng 13 trường";
    for (const t of CTX) if (!co(c, t) || !(CTX_HEX.has(t) ? laHex(c[t]) : laUuid(c[t]))) return "context." + t + " sai kiểu";
    return null;
  }
  const ctxBang = (a, b) => CTX.every(t => a[t] === b[t]);
  function kiemKt(k) {  // KT canonical: kt_revision_id UUID + revision int ≥ 1 là khóa lệnh DUY NHẤT; không alias
    if (!laDoiTuong(k) || Object.keys(k).length !== KT_KEYS.length || KT_KEYS.some(t => !co(k, t))) return "kt không đúng 13 trường canonical";
    if (!laUuid(k.kt_revision_id)) return "kt.kt_revision_id không phải UUID";
    if (!laNguyenDuong(k.revision)) return "kt.revision không phải số nguyên ≥ 1";
    if (!co(TT_KT, k.trang_thai)) return "kt.trang_thai lạ";
    if (TIEN_KT.some(([t]) => !laTien(k[t]))) return "số tiền KT không phải chuỗi thập phân/null";
    if (!laTienTe(k.tien_te)) return "kt.tien_te sai kiểu";
    if (!co(CO_SO, k.co_so_gia_tri) || !co(VAT, k.vat_trang_thai)) return "cơ sở giá trị/VAT lạ";
    if (k.vat_can_cu_tep_id !== null && !laUuid(k.vat_can_cu_tep_id)) return "kt.vat_can_cu_tep_id sai kiểu";
    if (!laChuoiHoacNull(k.vat_trich_dan) || !laChuoiHoacNull(k.ly_do)) return "trích dẫn/lý do KT sai kiểu";
    return null;
  }
  const ktBang = (a, b) => KT_KEYS.every(t => a[t] === b[t]);
  function kiemTep(ds_) {  // metadata tệp m4.tep thật trong phạm vi KT: đúng 5 trường, không object_key/URL
    if (!Array.isArray(ds_)) return "nguon.tep_can_cu không phải mảng";
    const ids = new Set();
    for (const t of ds_) {
      if (!laDoiTuong(t) || Object.keys(t).length !== 5 || !laUuid(t.id) || ids.has(t.id) || typeof t.ten !== "string" || !laHex(t.raw_sha256)
        || typeof t.media_type !== "string" || !laNguyenDuong(t.byte_length)) return "metadata tệp căn cứ sai kiểu/trùng";
      ids.add(t.id);
    }
    return null;
  }
  // trả {sai} (không hiển thị, không lệnh) hoặc {hold} (hiển thị chỉ đọc, giữ nháp, không POST) hoặc {}
  function kiemDto(d, pending, pb) {
    for (const t of ["context", "quyen", "can_cu_hien_hanh", "nguon", "kt", "lich_su", "ap", "request"]) if (!co(d, t)) return {sai: "thiếu trường " + t};
    const c = d.context, q = d.quyen, n = d.nguon, sai = kiemCtx(c);
    if (sai) return {sai};
    if (c.kt_pending_id !== pending) return {sai: "context khác hồ sơ KT đang mở"};
    if (pb && c.phong_bi_id !== pb) return {sai: "context khác phong bì đã chọn"};
    if (!laDoiTuong(q) || Object.keys(q).length !== 4 || ["xem", "luu", "xac_nhan", "tai_pdf"].some(t => typeof q[t] !== "boolean")) return {sai: "quyền không tường minh"};
    if (typeof d.can_cu_hien_hanh !== "boolean") return {sai: "can_cu_hien_hanh không phải boolean"};
    if (!d.can_cu_hien_hanh && (q.luu || q.xac_nhan)) return {sai: "phong bì không hiện hành mà có quyền lệnh"};
    if (!laDoiTuong(n) || NGUON_KEYS.some(t => !co(n, t))) return {sai: "nguồn thiếu trường"};
    if (TIEN_NGUON.some(([t]) => !laTien(n[t])) || !laTienTe(n.tien_te)) return {sai: "số/tiền tệ nguồn không phải chuỗi thập phân/mã/null"};
    if (!Array.isArray(n.dong)) return {sai: "dòng nguồn không phải mảng"};
    const rowIds = new Set();
    for (const r of n.dong) {
      if (!laDoiTuong(r) || typeof r.row_id !== "string" || !r.row_id || rowIds.has(r.row_id)) return {sai: "dòng nguồn thiếu/trùng row_id"};
      if (!co(r, "khoi_luong_chap_nhan") || !laKl(r.khoi_luong_chap_nhan)) return {sai: "khối lượng chấp nhận nguồn sai kiểu"};
      if ([r.ma_hm, r.dvt].some(v => v !== undefined && !laChuoiHoacNull(v))) return {sai: "mã hạng mục/ĐVT sai kiểu"};
      rowIds.add(r.row_id);
    }
    const p = n.pdf;
    if (!laDoiTuong(p) || Object.keys(p).length !== 5 || p.id !== c.pdf_id || p.raw_sha256 !== c.pdf_sha256 || typeof p.ten !== "string"
      || p.media_type !== "application/pdf" || !laNguyenDuong(p.byte_length)) return {sai: "PDF nguồn không khớp context/hash/độ dài"};
    // kt canonical thiếu/sai (vắng key, {}, alias kt.id, revision bool/chuỗi/0) = phụ thuộc backend: không hiển thị như hồ sơ thao tác được, không POST, giữ nháp
    if (!co(d, "kt") || (d.kt !== null && kiemKt(d.kt))) return {sai: "HOLD phụ thuộc kt canonical — " + (co(d, "kt") ? kiemKt(d.kt) : "thiếu kt")};
    // lịch sử canonical {phong_bi, kt}
    const ls = d.lich_su;
    if (!laDoiTuong(ls) || Object.keys(ls).length !== 2 || !Array.isArray(ls.phong_bi) || !Array.isArray(ls.kt)) return {sai: "lich_su không đúng {phong_bi, kt}"};
    const pbMap = new Map();
    let truocThuTu = 0, soHienHanh = 0;
    for (const r of ls.phong_bi) {
      if (!laDoiTuong(r) || Object.keys(r).length !== 5 || kiemCtx(r.context) || r.context.kt_pending_id !== pending) return {sai: "lịch sử phong bì sai kiểu/khác hồ sơ"};
      if (!laNguyenDuong(r.thu_tu) || r.thu_tu <= truocThuTu || !laNguyenDuong(r.phien_ban_so)) return {sai: "lịch sử phong bì sai thứ tự"};
      if (!(r.truoc_id === null || laUuid(r.truoc_id)) || typeof r.can_cu_hien_hanh !== "boolean") return {sai: "lịch sử phong bì sai kiểu"};
      if (pbMap.has(r.context.phong_bi_id)) return {sai: "lịch sử phong bì trùng"};
      truocThuTu = r.thu_tu; if (r.can_cu_hien_hanh) soHienHanh += 1;
      pbMap.set(r.context.phong_bi_id, r);
    }
    if (soHienHanh > 1) return {sai: "nhiều phong bì cùng hiện hành"};
    const dangXem = pbMap.get(c.phong_bi_id);
    if (!dangXem || !ctxBang(dangXem.context, c) || dangXem.can_cu_hien_hanh !== d.can_cu_hien_hanh) return {sai: "phong bì đang xem không khớp lịch sử"};
    let truocRev = 0, ktCuoi = null;
    const revIds = new Set();
    for (const r of ls.kt) {
      if (!laDoiTuong(r) || Object.keys(r).length !== 2 || kiemCtx(r.context) || kiemKt(r.kt)) return {sai: "lịch sử KT sai kiểu"};
      const g = pbMap.get(r.context.phong_bi_id);
      if (!g || !ctxBang(g.context, r.context)) return {sai: "lịch sử KT thuộc phong bì ngoài lịch sử"};
      if (r.kt.revision <= truocRev || revIds.has(r.kt.kt_revision_id)) return {sai: "lịch sử KT sai thứ tự/trùng"};
      truocRev = r.kt.revision; revIds.add(r.kt.kt_revision_id);
      if (r.context.phong_bi_id === c.phong_bi_id) ktCuoi = r.kt;
    }
    if (d.kt === null ? ktCuoi !== null : !ktCuoi || !ktBang(ktCuoi, d.kt)) return {sai: "kt không phải revision mới nhất của chính phong bì đang xem"};
    if (!apDung(d.ap) || !rqDung(d.request)) return {sai: "AP/Request không đúng trạng thái chưa triển khai/chưa nối"};
    // phụ thuộc additive: thiếu danh sách tệp căn cứ = HOLD (không phải "không có tệp"); sai kiểu = SAI_DTO
    if (!co(n, "tep_can_cu")) return {hold: "máy chủ chưa cung cấp nguon.tep_can_cu"};
    const st = kiemTep(n.tep_can_cu);
    if (st) return {sai: st};
    return {};
  }
  function kiemAck(rec, a) {  // sai bất kỳ → CHƯA RÕ (không coi là đã lưu/xác nhận)
    if (!laDoiTuong(a) || a.schema !== SCHEMA) return "schema";
    for (const t of ["context", "kt_revision_id", "revision", "trang_thai", "lap_lai", "receipt_id", "ap", "request"]) if (!co(a, t)) return "thiếu " + t;
    if (kiemCtx(a.context) || !ctxBang(a.context, rec.ctxGoc)) return "context không khớp phong bì đã gửi";
    if (!laUuid(a.kt_revision_id) || !laNguyenDuong(a.revision) || !co(TT_KT, a.trang_thai)) return "revision/trạng thái không tường minh";
    if (typeof a.lap_lai !== "boolean" || !laUuid(a.receipt_id)) return "thiếu biên nhận/cờ lặp lại";
    if (!apDung(a.ap) || !rqDung(a.request)) return "AP/Request không đúng";
    const ex = rec.body.expected_revision;
    if (rec.loai === "LUU" && (a.revision <= ex || a.trang_thai === DA_XAC_NHAN)) return "revision lưu không tăng hoặc tự xác nhận";
    if (rec.loai === "XAC_NHAN" && (a.trang_thai !== DA_XAC_NHAN || a.revision < ex || (a.revision === ex && a.kt_revision_id !== rec.body.kt_revision_id))) return "xác nhận không đúng revision";
    return null;
  }
  function kiemDs(d) {
    if (!laDoiTuong(d) || d.schema !== SCHEMA || !Array.isArray(d.items)) return "danh sách không đúng {schema, items}";
    const ids = new Set();
    for (const r of d.items) {
      if (!laDoiTuong(r) || Object.keys(r).length !== 7 || !laUuid(r.kt_pending_id) || ids.has(r.kt_pending_id) || !laUuid(r.dot_id) || !laUuid(r.phong_bi_id)
        || !laHex(r.phong_bi_sha256) || !(r.revision === null || laNguyenDuong(r.revision)) || !co(TT_DS, r.trang_thai) || !apDung(r.ap)) return "hàng hộp chờ sai kiểu/trùng";
      ids.add(r.kt_pending_id);
    }
    return null;
  }

  // ------------------------------------------------------------------ nạp hộp chờ (chỉ hiển thị/chọn)
  async function napDs() {
    if (!vungSong() || K.vaiDangChan(VAI)) return;
    const g = ++genDs, fi = fenceInc(), f = () => fi() && g === genDs;
    if (!ds) { dsTinhTrang = "DANG"; ve_(); }
    let res;
    try { res = await fetch("/api/m4/ke-toan", {headers: {"X-KTT-Token": TOKEN}, cache: "no-store", credentials: "same-origin"}); }
    catch (_) { if (!f()) return; if (!ds) dsTinhTrang = "LOI"; dsLoi = MAT_KET_NOI + "."; trangThai(dsLoi, true); ve_(); return; }
    if (!f()) return;
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      if (!f()) return;
      if (chuaNoiLoi(res.status, e)) { ds = null; dsTinhTrang = "CHUA_NOI"; dsLoi = e.message || ""; trangThai("Chưa nối backend kế toán nghiệm thu (M4-03A) — không có lệnh kế toán nào chạy.", true); ve_(); return; }
      if (res.status === 403 || res.status === 404) {
        ds = null; dsTinhTrang = "KHONG_QUYEN"; dsLoi = e.message || "";
        if (pendingChon) { thuHoiView(e.message); pendingChon = null; phongBiChon = null; } else trangThai((e.message || "Không có quyền kế toán") + ".", true);
        ve_(); return;
      }
      if (!ds) dsTinhTrang = "LOI";
      dsLoi = e.message || `Không đọc được hộp chờ kế toán (${res.status}).`; trangThai(dsLoi, true); ve_(); return;
    }
    let d;
    try { d = await res.json(); } catch (_) { d = undefined; }
    if (!f()) return;
    const sai = d === undefined ? "phản hồi đọc không trọn" : kiemDs(d);
    if (sai) { ds = null; dsTinhTrang = "SAI_DTO"; dsLoi = sai; trangThai("Hộp chờ kế toán không đúng hợp đồng (" + sai + ") — không hiển thị.", true); ve_(); return; }
    ds = d.items; dsTinhTrang = "OK"; dsLoi = "";
    if (pendingChon && !ds.some(r => r.kt_pending_id === pendingChon)) {  // hồ sơ đang mở không còn trong phạm vi KT hiện hành → gỡ ngay
      thuHoiView("Hồ sơ kế toán đang mở không còn trong hộp chờ của vai này"); pendingChon = null; phongBiChon = null;
    }
    ve_();
  }
  function chon(pending, phongBi) {  // đổi lựa chọn = đổi view: vô hiệu đồng bộ GET/ACK/blob/finally của lựa chọn cũ; nháp theo phong bì giữ trong map
    if (!vungSong() || K.vaiDangChan(VAI)) return;
    pendingChon = pending; phongBiChon = phongBi || null;
    genView += 1; genGet += 1; genForm += 1; dto = null; thuHoi = false; tinhTrang = "DANG"; loiGet = ""; ctxView = undefined;
    trangThai(""); ve_(); napLai();
  }

  // ------------------------------------------------------------------ nạp chi tiết (GET có barrier đổi vai + vé + fence)
  function doiThamQuyen(d, kq) {  // DTO mới (đã kiểm) khác DTO đang hiện về quyền / căn cứ hiện hành / context đầy đủ / revision KT / HOLD
    if (!dto || (tinhTrang !== "OK" && tinhTrang !== "HOLD")) return true;
    if (chuoiCtx(d.context) !== chuoiCtx(dto.context) || d.can_cu_hien_hanh !== dto.can_cu_hien_hanh || !!kq.hold !== (tinhTrang === "HOLD")) return true;
    if (["xem", "luu", "xac_nhan", "tai_pdf"].some(t => d.quyen[t] !== dto.quyen[t])) return true;
    return d.kt === null || dto.kt === null ? d.kt !== dto.kt : !ktBang(d.kt, dto.kt);
  }
  async function napLai(opt = {}) {
    if (!vungSong() || !pendingChon || (opt.ngoai && !opt.ngoai())) return;
    if (K.vaiDangChan(VAI)) return;
    const g = ++genGet, gf = genForm, fv = fenceView(), pending = pendingChon, pb = phongBiChon;
    const f = () => fv() && g === genGet && pending === pendingChon && pb === phongBiChon && (!opt.ngoai || opt.ngoai());
    if (!dto) { tinhTrang = "DANG"; ve_(); }
    const url = "/api/m4/ke-toan/" + encodeURIComponent(pending) + (pb ? "?" + new URLSearchParams({phong_bi_id: pb}).toString() : "");
    let res;
    try { res = await fetch(url, {headers: {"X-KTT-Token": TOKEN}, cache: "no-store", credentials: "same-origin"}); }
    catch (_) { if (!f()) return; if (!dto) tinhTrang = "LOI"; loiGet = MAT_KET_NOI + "."; trangThai(loiGet, true); ve_(); return; }
    if (!f()) return;
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      if (!f()) return;
      if (chuaNoiLoi(res.status, e)) { dto = null; tinhTrang = "CHUA_NOI"; loiGet = e.message || ""; trangThai("Chưa nối backend kế toán nghiệm thu (M4-03A) — nháp được giữ, các lệnh tạm tắt.", true); ve_(); return; }
      if (res.status === 403 || res.status === 404) { thuHoiView(e.message); ve_(); return; }
      if (!dto) tinhTrang = "LOI";
      loiGet = e.message || `Không đọc được hồ sơ kế toán (${res.status}).`; trangThai(loiGet, true); ve_(); return;
    }
    let d;
    try { d = await res.json(); } catch (_) { d = undefined; }
    if (!f()) return;
    if (d === undefined) { if (!dto) tinhTrang = "LOI"; loiGet = "Phản hồi hồ sơ kế toán đọc không trọn — chưa hiển thị."; trangThai(loiGet, true); ve_(); return; }
    // 200 xem=false = thu hồi hiện hành (kiểm trước shape đầy đủ: máy chủ không phải trả bằng chứng khi đã thu hồi)
    if (laDoiTuong(d) && d.schema === SCHEMA && laDoiTuong(d.quyen) && d.quyen.xem === false) { thuHoiView("Vai này không có quyền xem hồ sơ kế toán"); ve_(); return; }
    const kq = laDoiTuong(d) && d.schema === SCHEMA ? kiemDto(d, pending, pb) : {sai: "schema khác " + SCHEMA};
    if (kq.sai) { dto = null; tinhTrang = "SAI_DTO"; loiGet = kq.sai; trangThai("Phản hồi hồ sơ kế toán không đúng hợp đồng (" + kq.sai + ") — không hiển thị, không cho thao tác; nháp được giữ.", true); ve_(); return; }
    if (d.quyen.xem !== true) { thuHoiView("Vai này không có quyền xem hồ sơ kế toán"); ve_(); return; }
    // FIX01-B: chỉ hoãn khi KHÔNG đổi thẩm quyền/nguồn (giữ con trỏ nhập); quyền/context/revision/HOLD đổi → áp dụng NGAY (nháp nằm trong nhapMap theo
    // phong bì nên không mất, phong bì mới có nháp riêng) để handler đã vẽ trước đó kiểm theo quyền hiện hành
    if (gf !== genForm && !opt.giu && !doiThamQuyen(d, kq)) { trangThai("Dữ liệu mới đã về trong lúc bạn đang nhập — chưa áp dụng để giữ nháp; bấm ↻ Làm mới khi xong."); return; }
    const sc = chuoiCtx(d.context);
    if (ctxView !== undefined && sc !== ctxView) genView += 1;  // context đầy đủ đổi (phong bì mới, kể cả A→B→A) = view mới: continuation cũ hết hiệu lực
    ctxView = sc;
    dto = d; thuHoi = false; loiGet = kq.hold || ""; tinhTrang = kq.hold ? "HOLD" : "OK";
    if (kq.hold) trangThai("Phụ thuộc backend: " + kq.hold + " — chỉ đọc, nháp được giữ, không gửi lệnh (không coi là không có tệp VAT).", true);
    if (opt.hat && opt.hat()) nhapMap.delete(khoaNhap());
    ve_();
  }

  // ------------------------------------------------------------------ nháp form (chuỗi; trống = thiếu ≠ "0"; không tự chép số nguồn)
  function nhapTu(k) {
    const n = {co_so_gia_tri: "CHUA_RO", vat_trang_thai: "CHUA_DU", tien_te: "", vat_can_cu_tep_id: "", vat_trich_dan: "", ly_do: ""};
    for (const [t] of TIEN_KT) n[t] = "";
    if (!k) return n;
    for (const [t] of TIEN_KT) n[t] = chu(k[t]);
    n.tien_te = chu(k.tien_te); n.co_so_gia_tri = k.co_so_gia_tri; n.vat_trang_thai = k.vat_trang_thai;
    n.vat_can_cu_tep_id = chu(k.vat_can_cu_tep_id); n.vat_trich_dan = chu(k.vat_trich_dan); n.ly_do = chu(k.ly_do);
    return n;
  }
  const soHoa = v => { const t = String(v ?? "").trim(); return t === "" ? null : t; };
  function noiDung(n) {  // nội dung KT (không ngữ cảnh/khóa) — thứ tự cố định; tệp/trích dẫn chỉ đi kèm CO_CAN_CU
    const coCu = n.vat_trang_thai === "CO_CAN_CU";
    return {gia_tri_nt_xac_nhan: soHoa(n.gia_tri_nt_xac_nhan), tien_te: soHoa(n.tien_te), co_so_gia_tri: n.co_so_gia_tri,
      tam_ung_xac_nhan: soHoa(n.tam_ung_xac_nhan), thu_hoi_xac_nhan: soHoa(n.thu_hoi_xac_nhan), giu_lai_xac_nhan: soHoa(n.giu_lai_xac_nhan),
      vat_trang_thai: n.vat_trang_thai, vat_can_cu_tep_id: coCu ? soHoa(n.vat_can_cu_tep_id) : null, vat_trich_dan: coCu ? soHoa(n.vat_trich_dan) : null,
      ly_do: soHoa(n.ly_do)};
  }
  function nhapHienHanh() {
    const k = khoaNhap();
    if (!k) return null;
    if (!nhapMap.has(k)) nhapMap.set(k, nhapTu(dto.kt));
    return nhapMap.get(k);
  }
  const nhapKhacDaLuu = () => !!(dto && dto.kt) && JSON.stringify(noiDung(nhapHienHanh())) !== JSON.stringify(noiDung(nhapTu(dto.kt)));
  const tepCo = id => !!dto && Array.isArray(dto.nguon.tep_can_cu) && dto.nguon.tep_can_cu.some(t => t.id === id);

  // ------------------------------------------------------------------ lệnh (một bản ghi ý định chính xác cho mỗi thao tác gốc)
  const QUYEN_LENH = {LUU: ["luu", "Vai này không có quyền lưu số liệu kế toán"], XAC_NHAN: ["xac_nhan", "Vai này không có quyền xác nhận nghiệm thu kế toán"]};
  // cổng dùng chung cho lệnh mới VÀ Gửi lại y nguyên: DTO hiện hành hợp lệ (không HOLD), phong bì hiện hành, quyền tường minh HIỆN HÀNH đúng loại
  function lyDoTatQuyen(loai) {
    if (tinhTrang === "HOLD") return "Phụ thuộc backend (" + loiGet + ") — chỉ đọc";
    if (tinhTrang !== "OK" || !dto || thuHoi) return "Chưa có hồ sơ kế toán hợp lệ từ máy chủ";
    if (dto.can_cu_hien_hanh !== true) return "Phong bì này không phải căn cứ hiện hành (lịch sử/đã có nguồn mới) — chỉ đọc";
    const [k, ly] = QUYEN_LENH[loai];
    return dto.quyen[k] === true ? null : ly;
  }
  function lyDoTat(loai) {  // null = được gửi; chuỗi = lý do tắt (máy chủ vẫn kiểm quyền/CAS/nguồn)
    const tq = lyDoTatQuyen(loai);
    if (tq) return tq;
    const k = dto.kt, n = dto.nguon;
    if (k && k.trang_thai === DA_XAC_NHAN) return "Đã xác nhận nghiệm thu — chờ ghi công nợ (sửa sau xác nhận là điều chỉnh riêng, chưa mở ở gói này)";
    if (loai === "XAC_NHAN") {
      if (!k) return "Chưa có bản kế toán đã lưu — lưu nháp trước khi xác nhận";
      if (nhapKhacDaLuu()) return "Nháp đang khác bản đã lưu — lưu trước khi xác nhận";
      if (k.gia_tri_nt_xac_nhan === null || k.tien_te === null) return "Thiếu giá trị NT hoặc tiền tệ xác nhận";
      if (n.tien_te === null) return "Nguồn đã niêm phong thiếu tiền tệ — không xác nhận";
      if (k.tien_te !== n.tien_te) return "Tiền tệ KT khác tiền tệ nguồn (không quy đổi)";
      if (k.co_so_gia_tri === "CHUA_RO") return "Cơ sở giá trị chưa rõ (trước/gồm VAT)";
      if (k.vat_trang_thai === "CHUA_DU") return "VAT chưa đủ căn cứ — chọn Có căn cứ (tệp + trích dẫn) hoặc Không áp dụng (có lý do)";
      if (k.vat_trang_thai === "CO_CAN_CU" && (!k.vat_can_cu_tep_id || !tepCo(k.vat_can_cu_tep_id))) return "Căn cứ VAT không thuộc danh sách tệp hiện hành";
      if (k.vat_trang_thai === "CO_CAN_CU" && !soHoa(k.vat_trich_dan)) return "Thiếu trích dẫn căn cứ VAT";
      if (k.vat_trang_thai === "KHONG_AP_DUNG" && !soHoa(k.ly_do)) return "Không áp dụng VAT cần lý do";
      if (TIEN_KT.some(([t, , ng]) => k[t] !== null && k[t] !== n[ng]) && !soHoa(k.ly_do)) return "Số KT khác số nguồn mà chưa có lý do";
    }
    const r = recMo(dto.context.kt_pending_id);
    if (r) return r.bay ? "Đang gửi lệnh kế toán — chờ kết quả" : "Lệnh trước chưa rõ kết quả — bấm Gửi lại y nguyên";
    return null;
  }
  function taoYDinh(loai, body) {  // ĐỒNG BỘ trong handler, trước await đầu tiên
    if (yDinh.size >= TOI_DA_Y_DINH) { donYDinh(); if (yDinh.size >= TOI_DA_Y_DINH) { trangThai("Quá nhiều lệnh chưa rõ kết quả — Gửi lại y nguyên các lệnh đó trước.", true); return null; } }
    const c = dto.context, khoa = taoKhoa(), ctxGoc = {};
    for (const t of CTX) ctxGoc[t] = c[t];
    const rec = {id: ++soYDinh, loai, path: HANH[loai].path, ctxKey: khoaCtx, pending: c.kt_pending_id, phongBi: c.phong_bi_id, ctxGoc, khoa, inc, trang: "MOI",
      bay: null, soLan: 0, ketQua: null, loi: null, gf: genForm, dkey: khoaNhap()};
    rec.body = {...body, khoa};
    rec.bodyText = JSON.stringify(rec.body);  // body GỐC chuỗi hóa một lần — Gửi lại y nguyên từng byte
    yDinh.set(rec.id, rec);
    return rec;
  }
  function phanLoaiLoi(status, e) {
    if (chuaNoiLoi(status, e)) return {loai: "LOI", chuaNoi: true, status, msg: e.message || ""};
    if (status >= 500 || e.error === "M4_KET_QUA_CHUA_RO") return {loai: "CHUA_RO", msg: e.message || `máy chủ trả ${status}`};
    return {loai: "LOI", status, code: e.error || "HTTP_" + status, msg: e.message || `Không hoàn tất (${status}).`};
  }
  async function phat(rec) {  // gửi (hoặc Gửi lại) ĐÚNG bản ghi: cùng route, cùng body chuỗi, cùng khóa
    if (rec.bay) { trangThai(`Đang ${HANH[rec.loai].ten} — chờ kết quả, không gửi thêm.`); return; }
    const tk = {}, f = fenceView(), ten = HANH[rec.loai].ten;
    rec.bay = tk; rec.trang = "BAY"; rec.inc = inc; rec.soLan += 1;
    trangThai(`Đang ${ten}…`); ve_();
    let kq;
    try {
      const res = await fetch("/api/m4/" + rec.path, {method: "POST", headers: {"X-KTT-Token": TOKEN, "Content-Type": "application/json"}, body: rec.bodyText,
        cache: "no-store", credentials: "same-origin"});
      if (res.ok) {
        let a, doc = true;
        try { a = await res.json(); } catch (_) { doc = false; }
        const sai = doc ? kiemAck(rec, a) : "phản hồi đọc không trọn";
        kq = sai ? {loai: "CHUA_RO", msg: "phản hồi 2xx không đúng hợp đồng (" + sai + ")"} : {loai: "OK", ack: a};
      } else kq = phanLoaiLoi(res.status, await res.json().catch(() => ({})));
    } catch (_) { kq = {loai: "CHUA_RO", msg: MAT_KET_NOI}; }
    if (rec.bay !== tk) return;
    rec.bay = null;
    if (kq.loai === "OK") { const a = kq.ack; rec.trang = "RO"; rec.ketQua = {receipt_id: a.receipt_id, kt_revision_id: a.kt_revision_id, revision: a.revision}; }
    else if (kq.loai === "CHUA_RO") rec.trang = "CHUA_RO";
    else { rec.trang = "RO"; rec.loi = {status: kq.status, code: kq.code || null}; }
    donYDinh();
    if (!f()) {  // view/incarnation/vai đã đổi: KHÔNG toast/trạng thái/GET/đổi nháp; chỉ vẽ lại hàng ý định nếu đúng phạm vi gốc đang mở lại
      if (vungSong() && rec.ctxKey === khoaCtx && rec.inc !== inc && rec.pending === pendingChon) ve_();
      return;
    }
    if (kq.loai === "OK") {
      const a = kq.ack, lai = a.lap_lai === true ? " (biên nhận cũ của cùng khóa — không ghi thêm)" : "";
      const msg = rec.loai === "LUU" ? `Đã lưu nháp kế toán · revision ${a.revision} · biên nhận ${h12(a.receipt_id)} — chưa xác nhận${lai}`
        : `Đã xác nhận nghiệm thu — chờ ghi công nợ (chưa ghi công nợ/AP — M4-03B; Request chưa nối — M4-04)${lai}`;
      K.toast(msg); trangThai(msg);
      let hat = false;  // nháp đã gửi được dọn → GET đọc lại hạt lại từ revision máy chủ (nếu không gõ thêm trước khi GET về)
      if (rec.gf === genForm) { nhapMap.delete(rec.dkey); hat = true; }
      else trangThai(msg + " — form đã sửa trong lúc chờ nên nháp hiện tại được giữ.");
      ve_();
      const gHat = genForm;
      await napLai({ngoai: f, giu: true, hat: () => hat && genForm === gHat});
      return;
    }
    if (kq.loai === "CHUA_RO") {
      const msg = `Chưa rõ kết quả ${ten}: ${kq.msg}. Không coi là đã lưu/xác nhận; nháp và khóa gốc được giữ — bấm Gửi lại y nguyên (cùng khóa) để máy chủ đối soát.`;
      K.toast(msg, true); trangThai(msg, true); ve_(); return;
    }
    K.toast(kq.msg || ("Không " + ten), true);
    if (kq.chuaNoi) { dto = null; tinhTrang = "CHUA_NOI"; trangThai(`Chưa nối backend kế toán nghiệm thu cho lệnh ${ten} — nháp được giữ, các lệnh tạm tắt.`, true); ve_(); return; }
    if (kq.status === 403 || kq.status === 404) { thuHoiView(kq.msg); ve_(); return; }
    if (kq.status === 409) {
      trangThai((kq.msg || "Hồ sơ đã đổi") + " — đã đọc lại phong bì/revision hiện hành; nháp được giữ, kiểm tra rồi gửi lại.", true);
      await napLai({ngoai: f, giu: true}); return;
    }
    trangThai(kq.msg, true); ve_();
  }
  // FIX01-B: handler gắn với view lúc vẽ — nút cũ (đã giữ tham chiếu) sau khi đổi phong bì/context/vai/thu hồi không chạy lệnh trên view mới;
  // trong cùng view, luu/xacNhan vẫn kiểm lại quyền hiện hành bằng lyDoTat
  function theoView(fn) {
    const fv = fenceView();
    return () => {
      if (!fv()) { if (vungSong()) trangThai("Hồ sơ đang hiện đã đổi (phong bì/quyền/vai) — nút cũ không gửi lệnh; thao tác lại trên hồ sơ hiện hành.", true); return; }
      fn();
    };
  }
  function luu() {
    const tat = lyDoTat("LUU");
    if (tat) { trangThai(tat + ".", true); return; }
    const b = noiDung(nhapHienHanh()), sai = [];
    for (const [t, nhan] of TIEN_KT) if (!laTien(b[t])) sai.push(nhan);
    if (!laTienTe(b.tien_te)) sai.push("Tiền tệ (mã 3 chữ hoa, ví dụ VND)");
    if (!co(CO_SO, b.co_so_gia_tri) || !co(VAT, b.vat_trang_thai)) sai.push("Cơ sở giá trị/VAT");
    if (b.vat_can_cu_tep_id !== null && !tepCo(b.vat_can_cu_tep_id)) sai.push("Tệp căn cứ VAT không thuộc danh sách hiện hành");
    if (sai.length) { trangThai("Không hợp lệ: " + sai.join("; ") + " — số nhập dạng 1234567.5 (dấu chấm thập phân, không phân cách nghìn, không số 0 thừa); để trống = thiếu.", true); return; }
    const c = dto.context;
    // thứ tự khóa cố định theo allowlist; expected_revision = kt.revision, hoặc 0 CHỈ khi GET typed hiện hành trả kt === null (lưu nháp đầu)
    const rec = taoYDinh("LUU", {kt_pending_id: c.kt_pending_id, phong_bi_id: c.phong_bi_id, expected_phong_bi_sha256: c.phong_bi_sha256,
      expected_revision: dto.kt === null ? 0 : dto.kt.revision, ...b});
    if (rec) phat(rec);
  }
  function xacNhan() {
    const tat = lyDoTat("XAC_NHAN");
    if (tat) { trangThai(tat + ".", true); return; }
    const c = dto.context, k = dto.kt;  // xác nhận ĐÚNG revision đã lưu — không gửi lại số tiền
    const rec = taoYDinh("XAC_NHAN", {kt_pending_id: c.kt_pending_id, phong_bi_id: c.phong_bi_id, kt_revision_id: k.kt_revision_id, expected_revision: k.revision,
      expected_phong_bi_sha256: c.phong_bi_sha256});
    if (rec) phat(rec);
  }
  function guiLai(rec) {  // Gửi lại y nguyên: chỉ đúng vai/hồ sơ/phong bì gốc, DTO hiện hành hợp lệ, quyền hiện hành
    if (!vungSong() || rec.ctxKey !== khoaCtx || !dto || rec.pending !== dto.context.kt_pending_id || rec.phongBi !== dto.context.phong_bi_id
      || rec.ctxGoc.phong_bi_sha256 !== dto.context.phong_bi_sha256 || K.vaiDangChan(VAI)) {
      trangThai("Lệnh chưa rõ thuộc hồ sơ/phong bì khác hoặc chưa đọc lại được hồ sơ — không gửi lại.", true); return;
    }
    if (rec.trang !== "CHUA_RO") { trangThai(rec.bay ? "Đang gửi lại lệnh này — chờ kết quả." : "Lệnh này đã có kết quả.", true); return; }
    const tq = lyDoTatQuyen(rec.loai);
    if (tq) { trangThai(tq + " — lệnh chưa rõ được giữ nguyên (cùng khóa), chưa gửi lại.", true); return; }
    phat(rec);
  }

  // ------------------------------------------------------------------ tải PDF hồ sơ đợt đã niêm phong (route từ UUID context đã kiểm; fence trước click)
  async function taiPdf() {
    if (!dto || thuHoi || (tinhTrang !== "OK" && tinhTrang !== "HOLD") || dto.quyen.tai_pdf !== true) return;
    const c = dto.context, p = dto.nguon.pdf, f = fenceView(), dai = p.byte_length, ten = p.ten || "ho-so-dot.pdf", sc = chuoiCtx(c);
    // FIX01-A: quyền tải + view HIỆN HÀNH kiểm ngay trước hiệu ứng cuối — GET cùng context trả tai_pdf=false trong lúc chờ blob → không click
    const conQuyen = () => f() && !!dto && !thuHoi && (tinhTrang === "OK" || tinhTrang === "HOLD") && dto.quyen.tai_pdf === true && chuoiCtx(dto.context) === sc;
    try {
      const res = await fetch("/api/m4/ke-toan/" + encodeURIComponent(c.kt_pending_id) + "/phong-bi/" + encodeURIComponent(c.phong_bi_id) + "/pdf",
        {headers: {"X-KTT-Token": TOKEN}, cache: "no-store", credentials: "same-origin"});
      if (!f()) return;
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        if (!f()) return;
        if (!chuaNoiLoi(res.status, e) && (res.status === 403 || res.status === 404)) { thuHoiView(e.message); ve_(); return; }
        trangThai(chuaNoiLoi(res.status, e) ? "Chưa nối backend tải PDF hồ sơ đợt cho kế toán." : (e.message || `Không tải được PDF (${res.status}).`), true); return;
      }
      const blob = await res.blob();
      if (!f()) return;  // bytes về sau khi rời view/module/vai: không click
      if (blob.size !== dai) { trangThai(`Bytes tải về (${blob.size}) khác độ dài máy chủ đã niêm phong (${dai}) — không lưu tệp.`, true); return; }
      if (!conQuyen()) { if (f()) trangThai("Quyền tải PDF hồ sơ đợt đã đổi trong lúc tải (quyền hiện hành do máy chủ trả) — không lưu tệp.", true); return; }
      const url = URL.createObjectURL(blob), a = document.createElement("a");
      a.href = url; a.download = ten; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      trangThai(`Đã tải ${ten} (${blob.size} byte).`);
    } catch (_) { if (f()) trangThai(MAT_KET_NOI + " — chưa tải được PDF.", true); }
  }

  // ------------------------------------------------------------------ 03B: chỉ đối chiếu căn cứ, dùng dịch vụ chung; không suy ghép hóa đơn
  const DC_SCHEMA = "M4_03B_DOI_CHIEU_CAN_CU_V1", dcMap = new Map();
  const dcRef = c => ({kind: "NT", occurrence_id: c.kt_pending_id, source_version_id: c.phong_bi_id, part_id: null});
  const dcKey = r => JSON.stringify([r.kind, r.occurrence_id, r.part_id]);
  const dcCopy = x => JSON.parse(JSON.stringify(x));
  const dcNgay = v => typeof v === "string" && /^\d{4}-\d{2}-\d{2}/.test(v) ? v.slice(0, 10).split("-").reverse().join("/") : "Chưa có ngày";
  const dcTien = (v, tt) => {
    if (v === null || v === undefined) return "Chưa đọc được số tiền";
    const [nguyen, le] = String(v).split(".");
    return nguyen.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + (le ? "," + le : "") + " " + (tt || "chưa rõ đơn vị");
  };
  const dcChu = v => String(v || "").replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/gi, "(đối chiếu liên quan)")
    .replace(/\b[A-Z][A-Z0-9_]{3,}\b/g, "(cần kiểm tra)").replace(/\b[a-z]+(?:_[a-z0-9]+)+\b/g, "(trường dữ liệu)");
  const DC_TT = {NHAP_DOI_CHIEU: "Nháp", KT_XAC_NHAN_CAN_CU: "Đã xác nhận — đã khóa", CAN_KIEM_LAI: "Cần kiểm lại"};
  const DC_THIEU = {THIEU_NT: "Chưa gắn đợt nghiệm thu", THIEU_HOA_DON: "Đợt chưa có hóa đơn", PHAN_KHAI_THIEU: "Phần khai còn thiếu số tiền hoặc đơn vị",
    NT_KHONG_HIEN_HANH: "Căn cứ nghiệm thu đã đổi", NT_CHUA_KT_XAC_NHAN: "Đợt chưa được kế toán xác nhận", NT_KHAC_HOP_DONG: "Các đợt khác hợp đồng",
    BEN_BAN_HD_THIEU: "Hợp đồng thiếu đối tác", BEN_BAN_KHAC: "Đối tác hóa đơn khác hợp đồng", HOA_DON_CHUA_CO_PHIEN_BAN: "Hóa đơn chưa có bản hiện hành",
    CHO_MAPPING_M2: "Dòng hóa đơn chờ xác định tại màn hóa đơn"};
  function dcState() {
    const key = chuoiCtx(dto.context);
    if (!dcMap.has(key)) dcMap.set(key, {key, parts: [], tep: [], tepBoSung: [], lyDo: "", data: null, hist: null, base: null, edit: true, busy: false, error: "", pending: null, saved: null});
    return dcMap.get(key);
  }
  const dcLive = s => vungSong() && !!dto && s.key === chuoiCtx(dto.context) && !thuHoi && dto.quyen.xem === true && !K.vaiDangChan(VAI);
  const dcSua = s => dcLive(s) && tinhTrang === "OK" && dto.can_cu_hien_hanh && s.edit && !s.busy && !s.pending && s.data && s.data.can_cu.kt.duoc_ghi === true &&
    (!s.hist || s.hist.kt.duoc_ghi === true) && !s.data.goi_y.khong_quyen;
  const dcSig = s => JSON.stringify([s.parts, s.tep, s.lyDo]);
  const dcHd = (s, r) => s.data.goi_y.hoa_don.find(h => dcKey(h.nguon) === dcKey(r));
  const dcGanKhac = (s, h) => (h.da_gan_o || []).filter(x => !s.root || x.doi_chieu_id !== s.root);
  function dcLoiPhan(s) {
    if (!s.parts.some(t => t.nguon.kind === "HOA_DON")) return "Đợt chưa có hóa đơn — hãy bấm chọn hóa đơn.";
    for (const t of s.parts) {
      const h = t.nguon.kind === "HOA_DON" && dcHd(s, t.nguon);
      if (h && dcGanKhac(s, h).length) return "Hóa đơn đã gắn ở đối chiếu khác — không cho gắn trùng.";
      if (t.phan === "MOT_PHAN" && (!t.so_tien_khai || !t.tien_te)) return "Một phần bắt buộc nhập số tiền và đơn vị.";
      if (t.phan === "MOT_PHAN" && (!/^(0|[1-9][0-9]{0,17})(\.[0-9]{1,2})?$/.test(t.so_tien_khai) || !/[1-9]/.test(t.so_tien_khai) ||
          !["VND", "USD"].includes(t.tien_te) || (t.tien_te === "VND" && t.so_tien_khai.includes(".")))) return "Số tiền một phần phải dương; VND nguyên, USD tối đa hai số lẻ.";
    }
    return "";
  }
  async function dcFetch(path, body) {
    const res = await fetch("/api/m4/doi-chieu/" + path, {method: body ? "POST" : "GET", cache: "no-store", credentials: "same-origin",
      headers: {"X-KTT-Token": TOKEN, ...(body ? {"Content-Type": "application/json"} : {})}, ...(body ? {body: typeof body === "string" ? body : JSON.stringify(body)} : {})});
    let d; try { d = await res.json(); } catch (_) { throw new Error("Phản hồi không trọn; hãy tải lại căn cứ."); }
    if (!res.ok) { const e = new Error(dcChu(d.message) || "Chưa thực hiện được thao tác đối chiếu."); e.status = res.status; e.known = res.status < 500; throw e; }
    if (!d || d.schema !== DC_SCHEMA) throw new Error("Dữ liệu đối chiếu chưa hợp lệ; hãy tải lại căn cứ.");
    return d;
  }
  function dcNhan(s, r) {
    if (r.kind === "NT") return r.occurrence_id === dto.context.kt_pending_id ? "Đợt đang mở" : "Đợt đã chọn " + (s.parts.filter(t => t.nguon.kind === "NT").findIndex(t => dcKey(t.nguon) === dcKey(r)) + 1);
    const h = dcHd(s, r);
    return h ? `Hóa đơn ${h.so_chuan || "chưa có số"} · ${h.ky_hieu || "chưa có ký hiệu"} · ${dcNgay(h.ngay_lap)}` : "Hóa đơn đã lưu (cần kiểm lại danh sách hiện hành)";
  }
  async function dcNap(s) {
    if (!dcLive(s) || s.busy || s.pending) return;
    const f = fenceView(); s.busy = true; s.error = ""; ve_();
    try {
      const d = await dcFetch("dot/" + dto.context.kt_pending_id);
      if (!f() || !dcLive(s)) return;
      if (!d.can_cu || !d.can_cu.kt || !Array.isArray(d.can_cu.doi_chieu.goc_lien_quan) || !d.goi_y || !Array.isArray(d.goi_y.hoa_don) ||
          typeof d.goi_y.khong_quyen !== "boolean" || !laHex(d.can_cu.doi_chieu.graph_sha256)) throw new Error("Danh sách căn cứ chưa đầy đủ; hãy tải lại.");
      if (!d.nguon_nt || d.nguon_nt.occurrence_id !== dto.context.kt_pending_id || d.nguon_nt.source_version_id !== dto.context.phong_bi_id) {
        s.data = null; throw new Error("Cần kiểm lại — căn cứ nghiệm thu đã đổi. Làm mới hồ sơ nghiệm thu trước khi đối chiếu.");
      }
      s.data = d;
      if (!s.parts.length) s.parts = [{nguon: d.nguon_nt, phan: "TOAN_PHAN", so_tien_khai: null, tien_te: null}];
      const roots = d.can_cu.doi_chieu.goc_lien_quan;
      if (s.root || roots.length === 1) {
        const id = s.root || roots[0].doi_chieu_id;
        const h = await dcFetch("lich-su/" + id);
        if (!f() || !dcLive(s)) return;
        dcApHistory(s, h);
      }
    } catch (e) { if (f() && dcLive(s)) dcError(s, e); }
    finally { s.busy = false; if (f() && dcLive(s)) ve_(); }
  }
  function dcError(s, e) {
    s.error = e.message || "Chưa đọc được đối chiếu.";
    if (e.status === 403 || e.status === 404) { s.data = null; s.parts = []; s.hist = null; s.base = null; s.edit = false; }
  }
  function dcApHistory(s, h) {
    const pbs = h.doi_chieu && h.doi_chieu.phien_ban, p = Array.isArray(pbs) && pbs[pbs.length - 1];
    if (!p || !p.noi_dung || !Array.isArray(p.noi_dung.thanh_phan) || !Array.isArray(p.noi_dung.can_cu_tep) || !DC_TT[p.trang_thai] ||
        !laHex(h.doi_chieu.graph_sha256) || !Number.isInteger(p.revision)) throw new Error("Lịch sử đối chiếu chưa đầy đủ; hãy tải lại.");
    s.root = h.doi_chieu_id; s.hist = h; s.base = p; s.parts = dcCopy(p.noi_dung.thanh_phan);
    s.tep = p.noi_dung.can_cu_tep.map(t => t.id); s.lyDo = p.noi_dung.ly_do || "";
    s.edit = p.loai === "NHAP" && p.trang_thai === "NHAP_DOI_CHIEU"; s.saved = dcSig(s);
  }
  async function dcHistory(s, id) {
    if (!dcLive(s) || s.busy || s.pending) return;
    const f = fenceView(); s.busy = true; ve_();
    try { const h = await dcFetch("lich-su/" + id); if (f() && dcLive(s)) dcApHistory(s, h); }
    catch (e) { if (f() && dcLive(s)) dcError(s, e); }
    finally { s.busy = false; if (f() && dcLive(s)) ve_(); }
  }
  async function dcGui(s, confirm) {
    if (!dcLive(s) || s.busy || s.pending || !dcSua(s)) return;
    const reason = dcLoiPhan(s);
    if (confirm && (reason || !s.base || s.base.loai !== "NHAP" || s.base.trang_thai !== "NHAP_DOI_CHIEU" || s.saved !== dcSig(s) || (s.base.thieu || []).length)) return;
    if (!confirm && (!s.lyDo.trim() || s.parts.some(t => t.phan === "MOT_PHAN" && t.so_tien_khai && !/^(0|[1-9][0-9]{0,17})(\.[0-9]{1,2})?$/.test(t.so_tien_khai)))) return;
    const f = fenceView(); s.busy = true; s.error = ""; ve_();
    try {
      let body;
      if (confirm) body = {doi_chieu_id: s.root, phien_ban_id: s.base.phien_ban_id, expected_revision: s.base.revision, expected_graph: s.base.graph_sha256, khoa: taoKhoa()};
      else {
        const preview = await dcFetch("xem", {nguon: s.parts.map(t => t.nguon)});
        if (!f() || !dcLive(s)) return;
        if (!laHex(preview.doi_chieu.graph_sha256) || preview.kt.duoc_ghi !== true) throw new Error("Chưa có quyền lưu tập căn cứ này.");
        body = {doi_chieu_id: s.root || null, thanh_phan: dcCopy(s.parts).map(t => ({nguon: t.nguon, phan: t.phan, so_tien_khai: t.phan === "MOT_PHAN" ? t.so_tien_khai || null : null,
          tien_te: t.phan === "MOT_PHAN" ? t.tien_te || null : null})), can_cu_tep: [...s.tep], expected_graph: preview.doi_chieu.graph_sha256,
          expected_revision: s.base ? s.base.revision : 0, ly_do: s.lyDo, khoa: taoKhoa()};
      }
      s.pending = {path: confirm ? "xac-nhan" : "luu", body: JSON.stringify(body)};
    } catch (e) { if (f() && dcLive(s)) dcError(s, e); }
    finally { s.busy = false; }
    if (f() && dcLive(s)) { if (s.pending) await dcPhat(s); else ve_(); }
  }
  async function dcPhat(s) {
    if (!dcLive(s) || s.busy || !s.pending) return;
    const f = fenceView(), rec = s.pending; s.busy = true; s.error = ""; ve_();
    try {
      const ack = await dcFetch(rec.path, rec.body);
      if (!f() || !dcLive(s)) return;
      const a = ack.doi_chieu;
      if (!a || !laUuid(a.doi_chieu_id) || !laUuid(a.phien_ban_id) || !Number.isInteger(a.revision) || !DC_TT[a.trang_thai]) throw new Error("Chưa rõ kết quả đối chiếu.");
      s.root = a.doi_chieu_id; s.pending = null;
      const h = await dcFetch("lich-su/" + s.root);
      if (!f() || !dcLive(s)) return;
      dcApHistory(s, h);
    } catch (e) {
      if (f() && dcLive(s)) { if (e.known) s.pending = null; dcError(s, e); if (s.pending) s.error = "Chưa rõ kết quả. Gửi lại y nguyên để đối soát."; else s.edit = false; }
    } finally { s.busy = false; if (f() && dcLive(s)) ve_(); }
  }
  async function dcThemDot(s, id) {
    if (!id || !dcSua(s)) return;
    const f = fenceView(); s.busy = true; ve_();
    try {
      const res = await fetch("/api/m4/ke-toan/" + id, {headers: {"X-KTT-Token": TOKEN}, credentials: "same-origin", cache: "no-store"});
      const d = await res.json(); if (!f() || !dcLive(s)) return;
      if (!res.ok || !d.context || d.quyen.xem !== true || d.can_cu_hien_hanh !== true || !d.kt || d.kt.trang_thai !== DA_XAC_NHAN ||
          d.context.hop_dong_id !== dto.context.hop_dong_id) throw new Error("Chỉ chọn đợt đã xác nhận, hiện hành và cùng hợp đồng.");
      const r = dcRef(d.context); if (!s.parts.some(t => dcKey(t.nguon) === dcKey(r))) s.parts.push({nguon: r, phan: "TOAN_PHAN", so_tien_khai: null, tien_te: null});
      s.tepBoSung = s.tepBoSung.filter(t => t.pending !== id).concat((d.nguon.tep_can_cu || []).map(tep => ({pending: id, tep})));
    } catch (e) { if (f() && dcLive(s)) s.error = dcChu(e.message); }
    finally { s.busy = false; if (f() && dcLive(s)) ve_(); }
  }
  function veDoiChieu() {
    const s = dcState(), card = el("section", {class: "m4-card m4-03b"}, el("h3", {text: "Đối chiếu căn cứ với hóa đơn"}));
    const redraw = fn => () => { if (dcSua(s)) { fn(); ve_(); } };
    card.append(nho("Chọn nguồn tường minh. Hóa đơn được lọc theo pháp nhân, đối tác hợp đồng và xếp theo kỳ, số tiền đọc được; kế toán bấm chọn."));
    if (s.error) card.append(nho(dcChu(s.error), "m4-loi-chu"));
    card.append(nut(s.data ? "Tải lại căn cứ đối chiếu" : "Mở đối chiếu", () => dcNap(s), "", s.busy || !!s.pending));
    if (s.pending) card.append(nut("Gửi lại đối chiếu y nguyên", () => dcPhat(s), "", s.busy));
    if (s.busy) card.append(nho("Đang đọc hoặc lưu đối chiếu…"));
    if (!s.data) return card;
    if (s.data.goi_y.khong_quyen) { card.append(nho("Không có quyền đọc hóa đơn mua. Danh sách hóa đơn được ẩn.")); return card; }
    const roots = s.data.can_cu.doi_chieu.goc_lien_quan;
    roots.forEach((r, i) => card.append(nut("Xem đối chiếu " + (i + 1), () => dcHistory(s, r.doi_chieu_id), "", s.busy || !!s.pending)));
    if (roots.length > 1 && !s.root) { card.append(nho("Đợt thuộc nhiều đối chiếu. Chọn đối chiếu để xem và sửa đúng phiên bản.")); return card; }
    if (s.base) card.append(pill(DC_TT[s.base.trang_thai], s.base.trang_thai === "CAN_KIEM_LAI" ? "m4-loi" : "m4-du"));
    if (!s.edit) card.append(nut("Sửa bằng phiên bản mới", () => {
      if (!dcLive(s) || s.busy || s.pending || !dto.can_cu_hien_hanh) return;
      s.edit = true; s.saved = null;
      s.parts.forEach(t => {
        if (t.nguon.kind === "NT" && t.nguon.occurrence_id === dto.context.kt_pending_id) t.nguon = dcRef(dto.context);
        const h = t.nguon.kind === "HOA_DON" && dcHd(s, t.nguon); if (h) t.nguon = dcCopy(h.nguon);
        if (t.ty_le_khai !== undefined) { delete t.ty_le_khai; t.so_tien_khai = null; t.tien_te = null; }
      }); ve_();
    }, "", s.busy || !!s.pending || !dto.can_cu_hien_hanh));
    const editable = !!dcSua(s);
    card.append(el("h4", {text: "Nguồn đã chọn"}));
    s.parts.forEach((t, i) => {
      const row = el("div", {class: "m4-hang"}, el("span", {text: dcNhan(s, t.nguon)}));
      const sel = el("select", {"aria-label": "Phạm vi nguồn " + (i + 1)}, [["TOAN_PHAN", "Toàn bộ"], ["MOT_PHAN", "Một phần"]].map(([value, text]) => el("option", {value, text})));
      sel.value = t.phan; sel.disabled = !editable; sel.addEventListener("change", redraw(() => { t.phan = sel.value; t.so_tien_khai = null; t.tien_te = null; })); row.append(sel);
      if (t.phan === "MOT_PHAN") {
        const input = el("input", {"aria-label": "Số tiền một phần nguồn " + (i + 1), type: "text", inputmode: "decimal", value: t.so_tien_khai || ""}); input.disabled = !editable;
        input.addEventListener("input", () => { if (dcSua(s)) { t.so_tien_khai = input.value || null; dcNut(s, card); } });
        const unit = el("select", {"aria-label": "Đơn vị nguồn " + (i + 1)}, [["", "Chọn đơn vị"], ["VND", "VND"], ["USD", "USD"]].map(([value, text]) => el("option", {value, text})));
        unit.value = t.tien_te || ""; unit.disabled = !editable; unit.addEventListener("change", redraw(() => { t.tien_te = unit.value || null; }));
        row.append(input, unit);
      }
      if (!(t.nguon.kind === "NT" && t.nguon.occurrence_id === dto.context.kt_pending_id)) row.append(nut("Bỏ nguồn " + (i + 1), redraw(() => s.parts.splice(i, 1)), "", !editable));
      card.append(row);
    });
    const other = (ds || []).filter(r => r.trang_thai === DA_XAC_NHAN && !s.parts.some(t => t.nguon.occurrence_id === r.kt_pending_id));
    const add = el("select", {"aria-label": "Thêm đợt đã xác nhận"}, el("option", {value: "", text: "Chọn thêm đợt đã xác nhận cùng hợp đồng"}),
      other.map((r, i) => el("option", {value: r.kt_pending_id, text: "Hồ sơ đã xác nhận " + (i + 1)})));
    add.disabled = !editable; add.addEventListener("change", () => dcThemDot(s, add.value)); card.append(add);
    card.append(el("h4", {text: "Hóa đơn mua — thứ tự gợi ý"}));
    s.data.goi_y.hoa_don.forEach(h => {
      const selected = s.parts.some(t => dcKey(t.nguon) === dcKey(h.nguon)), assigned = dcGanKhac(s, h);
      const labels = assigned.map((x, i) => {
        const pos = roots.findIndex(r => r.doi_chieu_id === x.doi_chieu_id);
        return x.doi_chieu_id ? "đã gắn ở đối chiếu " + (pos >= 0 ? pos + 1 : "liên quan " + (i + 1)) : "đã gắn ở đối chiếu ngoài phạm vi";
      });
      card.append(el("div", {class: "m4-hang"}, el("span", {text: dcNhan(s, h.nguon) + " · " + dcTien(h.so_tien_doc_duoc, h.tien_te)}),
        labels.length ? nho(labels.join("; ")) : null, nut(selected ? "Đã chọn hóa đơn" : "Chọn hóa đơn " + (h.so_chuan || "chưa có số"), redraw(() => {
          if (!dcGanKhac(s, h).length && !s.parts.some(t => dcKey(t.nguon) === dcKey(h.nguon))) s.parts.push({nguon: dcCopy(h.nguon), phan: "TOAN_PHAN", so_tien_khai: null, tien_te: null});
        }), "", !editable || selected || !!assigned.length)));
    });
    card.append(el("h4", {text: "Tệp căn cứ"}));
    const tepUngVien = [...new Map([...(dto.nguon.tep_can_cu || []), ...s.tepBoSung.filter(x => s.parts.some(t => t.nguon.occurrence_id === x.pending)).map(x => x.tep)].map(t => [t.id, t])).values()];
    for (const t of tepUngVien) {
      const chk = el("input", {type: "checkbox", "aria-label": "Tệp căn cứ " + t.ten}); chk.checked = s.tep.includes(t.id); chk.disabled = !editable;
      chk.addEventListener("change", redraw(() => { s.tep = chk.checked ? [...new Set([...s.tep, t.id])] : s.tep.filter(id => id !== t.id); }));
      card.append(el("label", {}, chk, t.ten));
    }
    s.tep.filter(id => !tepUngVien.some(t => t.id === id)).forEach((id, i) => card.append(el("div", {class: "m4-hang"}, nho("Tệp căn cứ đã lưu của đợt trong nhóm " + (i + 1)),
      nut("Bỏ tệp đã lưu " + (i + 1), redraw(() => { s.tep = s.tep.filter(x => x !== id); }), "", !editable))));
    card.append(nho("Chọn tệp căn cứ đã có trong hồ sơ nghiệm thu. Tải tệp mới do phòng dự án thực hiện."));
    const reason = el("textarea", {"aria-label": "Lý do đối chiếu", value: s.lyDo}); reason.disabled = !editable;
    reason.addEventListener("input", () => { if (dcSua(s)) { s.lyDo = reason.value; dcNut(s, card); } }); card.append(el("label", {}, "Lý do đối chiếu / phiên bản mới", reason));
    card.append(nut("Lưu nháp đối chiếu", () => dcGui(s, false), "m4-chinh", !editable), nut("Xác nhận đối chiếu", () => dcGui(s, true), "m4-chinh", true), el("p", {class: "m4-03b-ly-do m4-nho"}));
    card.append(el("h4", {text: "Còn thiếu"}));
    const missing = s.base ? s.base.thieu || [] : s.data.can_cu.kt.thieu;
    missing.forEach(code => card.append(nho(DC_THIEU[code] || "Căn cứ cần kiểm tra lại")));
    if (dcLoiPhan(s)) card.append(nho(dcLoiPhan(s)));
    const unlinked = s.data.goi_y.hoa_don.filter(h => !(h.da_gan_o || []).length && !s.parts.some(t => dcKey(t.nguon) === dcKey(h.nguon)));
    unlinked.forEach(h => card.append(nho(dcNhan(s, h.nguon) + " — hóa đơn chưa gắn đợt")));
    for (const t of (s.hist && s.hist.kt.phan_khai_con_thieu) || []) card.append(nho("Phần khai còn thiếu của đợt: " + (t.ly_do ? "Cần kiểm lại phần khai" : dcTien(t.so_tien_con_thieu, t.tien_te))));
    if (s.hist) {
      card.append(el("h4", {text: "Lịch sử phiên bản đối chiếu"}));
      s.hist.doi_chieu.phien_ban.forEach(p => card.append(el("details", {}, el("summary", {text: `Phiên bản ${p.revision} · ${DC_TT[p.trang_thai]} · ${dcNgay(p.tao_luc)}`}),
        nho(dcChu(p.ly_do)), (p.noi_dung.thanh_phan || []).map(t => nho(dcNhan(s, t.nguon) + " · " + (t.phan === "TOAN_PHAN" ? "Toàn bộ" : "Một phần · " + (t.ty_le_khai ? "Cần khai lại số tiền" : dcTien(t.so_tien_khai, t.tien_te))))),
        nho("Tệp căn cứ: " + (p.noi_dung.can_cu_tep.length ? p.noi_dung.can_cu_tep.map(t => (dto.nguon.tep_can_cu.find(f => f.id === t.id) || {}).ten || "Tệp của đợt trong nhóm").join("; ") : "Chưa đính kèm")))));
    }
    dcNut(s, card); return card;
  }
  function dcNut(s, card) {
    const buttons = [...card.querySelectorAll("button")], save = buttons.find(b => b.textContent === "Lưu nháp đối chiếu"), confirm = buttons.find(b => b.textContent === "Xác nhận đối chiếu");
    const reason = !dcSua(s) ? "Đối chiếu đang khóa hoặc chưa có quyền sửa; hãy tải lại căn cứ hoặc tạo phiên bản mới." : dcLoiPhan(s) ||
      (!s.base || s.base.loai !== "NHAP" || s.base.trang_thai !== "NHAP_DOI_CHIEU" || s.saved !== dcSig(s) ? "Lưu nháp hiện tại trước khi xác nhận." : (s.base.thieu || []).length ? "Căn cứ còn thiếu; hãy bổ sung trước khi xác nhận." : "");
    if (save) save.disabled = !dcSua(s) || !s.lyDo.trim();
    if (confirm) { confirm.disabled = !!reason; confirm.title = reason; }
    const note = card.querySelector(".m4-03b-ly-do"); if (note) note.textContent = reason;
  }

  // ------------------------------------------------------------------ giao diện
  function oNhap(nhan, gia, ghi, kieu) {  // cập nhật nháp + thế hệ form; không vẽ lại khi gõ
    const i = el(kieu === "area" ? "textarea" : "input", {"aria-label": nhan, autocomplete: "off"});
    if (kieu !== "area") i.type = "text";
    i.value = gia;
    i.addEventListener("input", () => { ghi(i.value); genForm += 1; });
    return i;
  }
  function chonO(nhan, cacMuc, gia, ghi, tat, tatMuc) {  // select: đổi = cập nhật nháp + vẽ lại (hiện/ẩn nhánh VAT); nháp nằm trong map nên không mất
    const s = el("select", {"aria-label": nhan}, cacMuc.map(([v, t]) => { const o = el("option", {value: v, text: t}); if (tatMuc && tatMuc(v)) o.disabled = true; return o; }));
    s.value = gia; s.disabled = !!tat;
    s.addEventListener("change", () => { ghi(s.value); genForm += 1; ve_(); });
    return s;
  }
  function veDs() {
    const s = el("section", {class: "m4-card m4-kt-ds"}, el("div", {class: "m4-hang"}, el("h3", {text: "Hộp chờ kế toán nghiệm thu"}), nut("↻ Làm mới danh sách", () => napDs())));
    if (dsTinhTrang === "CHUA_NOI") s.append(el("div", {class: "m4-notice m4-notice-loi", role: "alert"}, el("strong", {text: "Chưa nối backend kế toán nghiệm thu (M4-03A). "}),
      `Máy chủ chưa có dịch vụ ${SCHEMA}${dsLoi ? " (" + dsLoi + ")" : ""}. Không có số liệu kế toán, xác nhận, công nợ hay Request nào được ghi.`));
    else if (dsTinhTrang === "KHONG_QUYEN") s.append(el("div", {class: "m4-notice m4-notice-loi", role: "alert", text: `Vai này không có quyền kế toán nghiệm thu${dsLoi ? ": " + dsLoi : ""}.`}));
    else if (dsTinhTrang === "SAI_DTO") s.append(el("div", {class: "m4-notice m4-notice-loi", role: "alert", text: `Hộp chờ không đúng hợp đồng ${SCHEMA} (${dsLoi}) — không hiển thị.`}));
    else if (dsTinhTrang === "LOI" && !ds) s.append(el("div", {class: "m4-notice m4-notice-loi", text: dsLoi || "Chưa đọc được hộp chờ kế toán."}));
    else if (!ds) s.append(el("p", {class: "m4-trong", text: "Đang tải hộp chờ…"}));
    else if (!ds.length) s.append(el("p", {class: "m4-trong", text: "Hộp chờ trống — chưa có hồ sơ đợt nào được duyệt + niêm phong PDF trong phạm vi kế toán của vai này."}));
    else s.append(bang(["Hồ sơ KT", "Đợt", "Phong bì mới nhất", "Revision KT", "Trạng thái", "Công nợ/AP", ""], ds.map(r => {
      const [tt, cls] = TT_DS[r.trang_thai], dang = r.kt_pending_id === pendingChon;  // FIX02: tập hộp chờ (cùng tập với kiemDs)
      return [h12(r.kt_pending_id), h12(r.dot_id), h12(r.phong_bi_id), r.revision === null ? "chưa có" : String(r.revision), pill(tt, cls),
        "Chưa triển khai (M4-03B)", nut(dang ? "Đang mở" : "Mở", () => chon(r.kt_pending_id, null), dang ? "" : "m4-chinh")];
    })), nho("Danh sách chỉ để chọn — mọi lệnh dùng context/revision của hồ sơ chi tiết đọc lại từ máy chủ."));
    return s;
  }
  function veHoSo() {
    const d = dto, c = d.context, n = d.nguon, q = d.quyen, k = d.kt, out = [], ls = d.lich_su;
    const dangPb = ls.phong_bi.find(r => r.context.phong_bi_id === c.phong_bi_id);
    const lichSu = phongBiChon !== null && !d.can_cu_hien_hanh;
    const dau = el("section", {class: "m4-card m4-kt-dau"}, el("div", {class: "m4-hang"},
      el("strong", {text: `Phong bì nguồn ${h12(c.phong_bi_id)} · thứ tự ${dangPb.thu_tu} · bản số ${dangPb.phien_ban_so}`}),
      d.can_cu_hien_hanh ? pill("Căn cứ hiện hành", "m4-du") : pill(lichSu ? "Lịch sử — chỉ đọc" : "Không còn hiện hành — chỉ đọc", "m4-loi")),
      nho(`Hồ sơ KT ${h12(c.kt_pending_id)} · đợt ${h12(c.dot_id)} · phiên bản ${h12(c.version_id)} · kết luận ${h12(c.ket_luan_id)} · seal ${h12(c.seal_id)} · H phong bì ${h12(c.phong_bi_sha256)} · SHA đồ thị ${h12(c.graph_sha256)}`));
    if (!d.can_cu_hien_hanh) dau.append(nho("Phong bì này không phải căn cứ hiện hành (đã có phong bì/phiên bản nguồn mới hoặc nguồn mới chưa niêm phong) — không lưu/xác nhận trên phong bì này.", "m4-loi-chu"));
    dau.append(el("div", {class: "m4-hang"}, ...[["Xem", q.xem], ["Lưu KT", q.luu], ["Xác nhận", q.xac_nhan], ["Tải PDF", q.tai_pdf]]
      .map(([t, v]) => pill(`${t}: ${v ? "có" : "không"}`, v ? "m4-du" : "m4-xam"))), nho("Quyền do máy chủ trả theo vai KE_TOAN hiện hành; REVIEW/DUYET/XEM không tự có quyền kế toán."));
    if (phongBiChon !== null) dau.append(el("div", {class: "m4-hang"}, nut("Về phong bì mới nhất", () => chon(c.kt_pending_id, null))));
    out.push(dau);

    const ng = el("section", {class: "m4-card m4-kt-nguon"}, el("h3", {text: "Số nguồn đã niêm phong (chỉ đọc)"}),
      nho("Số do hồ sơ đợt đã duyệt + niêm phong cung cấp; không phải số kế toán xác nhận. Số xin thanh toán không tự là số NT/AP."));
    ng.append(bang(["Khoản", "Số nguồn"], [...TIEN_NGUON.map(([t, nhan]) => [nhan, thieuNeu(n[t])]), ["Tiền tệ nguồn", thieuNeu(n.tien_te)]]));
    ng.append(el("h4", {text: "Dòng khối lượng chấp nhận (nguồn)"}));
    ng.append(n.dong.length ? bang(["Dòng", "Hạng mục", "ĐVT", "KL chấp nhận"], n.dong.map(r => [r.row_id, chu(r.ma_hm), chu(r.dvt), thieuNeu(r.khoi_luong_chap_nhan)]))
      : nho("Phong bì không có dòng khối lượng."));
    ng.append(el("div", {class: "m4-hang"}, el("span", {text: `PDF hồ sơ đợt đã duyệt: ${n.pdf.ten || "—"} · ${K.size(n.pdf.byte_length)} · H ${h12(n.pdf.raw_sha256)}`}),
      nut("Tải PDF hồ sơ đợt ↓", theoView(taiPdf), "m4-lien-ket", q.tai_pdf !== true || thuHoi, q.tai_pdf !== true ? "Vai này không có quyền tải PDF" : "")),
      nho("PDF hồ sơ đợt không phải chứng cứ VAT."));
    out.push(ng);

    const kt = el("section", {class: "m4-card m4-kt-so"}, el("h3", {text: "Số liệu kế toán nghiệm thu"}));
    if (k === null) kt.append(nho("Chưa có bản kế toán nào cho phong bì này (kt = null). Lần lưu đầu tạo revision 1 — số KT không tự chép từ số nguồn."));
    else {
      const [tt, cls] = TT_KT[k.trang_thai];
      kt.append(el("div", {class: "m4-hang"}, pill(tt, cls), el("span", {text: `Revision đã lưu ${k.revision} · ${h12(k.kt_revision_id)}`})));
      if (k.trang_thai === DA_XAC_NHAN) kt.append(el("div", {class: "m4-notice m4-kt-xac-nhan", role: "status", text: "Đã xác nhận nghiệm thu — chờ ghi công nợ. Chưa ghi công nợ/AP, chưa hạch toán; Request chưa nối."}));
      kt.append(bang(["Khoản", "Số nguồn", "Số KT đã lưu"], [...TIEN_KT.map(([t, nhan, nguon]) => [nhan, thieuNeu(n[nguon]), thieuNeu(k[t])]),
        ["Tiền tệ", thieuNeu(n.tien_te), thieuNeu(k.tien_te)], ["Cơ sở giá trị", "", CO_SO[k.co_so_gia_tri]], ["VAT", "", VAT[k.vat_trang_thai]],
        ["Tệp căn cứ VAT", "", k.vat_can_cu_tep_id ? tenTep(k.vat_can_cu_tep_id) : "—"], ["Trích dẫn VAT", "", thieuNeu(k.vat_trich_dan)], ["Lý do", "", thieuNeu(k.ly_do)]]));
    }
    if (q.luu === true && d.can_cu_hien_hanh && !(k && k.trang_thai === DA_XAC_NHAN)) kt.append(...veForm());
    else if (d.can_cu_hien_hanh && q.luu !== true) kt.append(nho("Vai này không có quyền lưu số liệu kế toán — chỉ xem.", "m4-loi-chu"));
    out.push(kt);
    if (k && k.trang_thai === DA_XAC_NHAN) out.push(veDoiChieu());

    out.push(el("section", {class: "m4-card m4-kt-nhanh"}, el("h3", {text: "Nhánh sau xác nhận"}), bang(["Nhánh", "Trạng thái máy chủ", "Ghi chú"], [
      ["Ghi công nợ/AP", pill("Chưa triển khai (M4-03B)", "m4-xam"), "Đã ghi công nợ: không. Xác nhận kế toán không đồng nghĩa ghi công nợ/hạch toán."],
      ["Request thanh toán", pill("Chưa nối (M4-04)", "m4-xam"), "Không tạo/gửi Request từ màn này."]])));

    const lsS = el("section", {class: "m4-card m4-kt-lich-su"}, el("h3", {text: "Lịch sử phong bì nguồn"}));
    lsS.append(bang(["Thứ tự", "Bản số", "Phong bì", "Phong bì trước", "Hiện hành", ""], ls.phong_bi.map(r => [String(r.thu_tu), String(r.phien_ban_so),
      h12(r.context.phong_bi_id), r.truoc_id ? h12(r.truoc_id) : "—", r.can_cu_hien_hanh ? "hiện hành" : "",
      r.context.phong_bi_id === c.phong_bi_id ? "đang xem" : nut("Xem phong bì này", () => chon(c.kt_pending_id, r.context.phong_bi_id))])));
    lsS.append(el("h4", {text: "Lịch sử revision kế toán (append-only)"}));
    lsS.append(ls.kt.length ? bang(["Revision", "Phong bì", "Trạng thái", "Giá trị NT", "Tiền tệ", "VAT"], ls.kt.map(r => [String(r.kt.revision), h12(r.context.phong_bi_id),
      TT_KT[r.kt.trang_thai][0], thieuNeu(r.kt.gia_tri_nt_xac_nhan), thieuNeu(r.kt.tien_te), VAT[r.kt.vat_trang_thai]]))
      : nho("Chưa có revision kế toán nào."));
    lsS.append(nho("Lịch sử chỉ để đọc — không dùng làm căn cứ lệnh."));
    out.push(lsS);
    return out;
  }
  function tenTep(id) {
    const t = Array.isArray(dto.nguon.tep_can_cu) ? dto.nguon.tep_can_cu.find(x => x.id === id) : null;
    return t ? `${t.ten} · ${h12(t.raw_sha256)}` : h12(id) + " (không còn trong danh sách tệp hiện hành)";
  }
  function veForm() {
    const n = nhapHienHanh(), d = dto, tep = d.nguon.tep_can_cu, out = [];
    const tatL = lyDoTat("LUU"), choSua = tinhTrang === "OK" && (!tatL || /chưa rõ|Đang gửi/.test(tatL));  // chờ/chưa rõ: vẫn sửa nháp, chỉ chặn gửi
    out.push(el("h4", {text: "Nháp kế toán"}), nho("Để trống = THIẾU (gửi null), khác số 0. Số dạng chuỗi thập phân 1234567.5 — không làm tròn, không quy đổi, không tính VAT."));
    if (d.kt && nhapKhacDaLuu()) out.push(nho("Nháp đang khác bản đã lưu.", "m4-loi-chu"));
    const form = el("div", {class: "m4-form"});
    for (const [t, nhan] of TIEN_KT) {
      const i = oNhap(nhan, n[t], v => { n[t] = v; }); i.disabled = !choSua; i.inputMode = "decimal";
      form.append(el("label", {}, el("span", {text: nhan}), i));
    }
    const tt = oNhap("Tiền tệ KT", n.tien_te, v => { n.tien_te = v; }); tt.disabled = !choSua;
    form.append(el("label", {}, el("span", {text: `Tiền tệ (nguồn: ${thieuNeu(d.nguon.tien_te)})`}), tt));
    form.append(el("label", {}, el("span", {text: "Cơ sở giá trị"}), chonO("Cơ sở giá trị", Object.entries(CO_SO), n.co_so_gia_tri, v => { n.co_so_gia_tri = v; }, !choSua)));
    const khongTep = !Array.isArray(tep) || !tep.length;
    form.append(el("label", {}, el("span", {text: "VAT"}), chonO("Trạng thái VAT", Object.entries(VAT), n.vat_trang_thai, v => { n.vat_trang_thai = v; }, !choSua,
      v => v === "CO_CAN_CU" && khongTep && n.vat_trang_thai !== "CO_CAN_CU")));
    out.push(form);
    if (!Array.isArray(tep)) out.push(nho("Máy chủ chưa cung cấp danh sách tệp căn cứ VAT (nguon.tep_can_cu) — phụ thuộc backend; nhánh Có căn cứ khóa, nháp được giữ.", "m4-loi-chu"));
    else if (!tep.length) out.push(nho("Không có tệp căn cứ VAT nào trong phạm vi kế toán — chưa chọn được Có căn cứ. Điều này KHÔNG có nghĩa là không áp dụng VAT."));
    if (n.vat_trang_thai === "CO_CAN_CU") {
      const s = chonO("Tệp căn cứ VAT", [["", "— chọn tệp căn cứ —"], ...(Array.isArray(tep) ? tep : []).map(t => [t.id, `${t.ten} · ${K.size(t.byte_length)} · H ${h12(t.raw_sha256)}`])],
        n.vat_can_cu_tep_id, v => { n.vat_can_cu_tep_id = v; }, !choSua);
      const tr = oNhap("Trích dẫn căn cứ VAT", n.vat_trich_dan, v => { n.vat_trich_dan = v; }, "area"); tr.disabled = !choSua; tr.rows = 2;
      out.push(el("div", {class: "m4-form m4-kt-vat"}, el("label", {}, el("span", {text: "Tệp căn cứ VAT (tệp thật đã lưu)"}), s),
        el("label", {}, el("span", {text: "Trích dẫn (trang/mục/dòng)"}), tr)));
      if (soHoa(n.vat_can_cu_tep_id) && !tepCo(n.vat_can_cu_tep_id)) out.push(nho("Tệp đã chọn không còn trong danh sách tệp hiện hành — chọn lại.", "m4-loi-chu"));
    }
    const ld = oNhap("Lý do / ghi chú KT", n.ly_do, v => { n.ly_do = v; }, "area"); ld.disabled = !choSua; ld.rows = 2;
    out.push(el("label", {class: "m4-kt-o"}, el("span", {text: "Lý do (bắt buộc khi Không áp dụng VAT hoặc số KT khác số nguồn)"}), ld));
    const exp = d.kt === null ? "lưu đầu" : "revision " + d.kt.revision, tatX = lyDoTat("XAC_NHAN");
    out.push(el("div", {class: "m4-hang"}, nut(`Lưu nháp kế toán (${exp})`, theoView(luu), "m4-chinh", !!tatL, tatL), tatL ? nho(tatL) : null));
    out.push(el("div", {class: "m4-hang"}, nut(d.kt ? `Xác nhận nghiệm thu (revision ${d.kt.revision})` : "Xác nhận nghiệm thu", theoView(xacNhan), "m4-chinh", !!tatX, tatX), tatX ? nho(tatX) : null),
      nho("Lưu và Xác nhận là hai lệnh riêng; xác nhận đúng revision đã lưu, không ghi công nợ."));
    return out;
  }
  function veYDinh() {  // ý định đang bay/chưa rõ của ĐÚNG vai + hồ sơ KT đang mở — phong bì khác chỉ hiện chữ
    const ds_ = [...yDinh.values()].filter(r => r.ctxKey === khoaCtx && r.pending === pendingChon && r.trang !== "RO" && r.trang !== "MOI");
    return ds_.map(r => {
      const ten = HANH[r.loai].ten, dung = !!dto && r.phongBi === dto.context.phong_bi_id && r.ctxGoc.phong_bi_sha256 === dto.context.phong_bi_sha256;
      if (r.bay) return el("div", {class: "m4-hang m4-kt-ydinh"}, nho(r.inc === inc ? `Đang ${ten} — chờ kết quả, không gửi thêm.`
        : `Lệnh ${ten} của lần mở trước còn đang chờ phản hồi — chưa gửi thêm; bấm ↻ Làm mới sau để xem kết quả.`));
      if (!dung) return el("div", {class: "m4-hang m4-kt-ydinh"}, nho(`Chưa rõ kết quả ${ten} ở phong bì ${h12(r.phongBi)} — mở lại đúng phong bì đó để gửi lại.`, "m4-loi-chu"));
      const tatLai = lyDoTatQuyen(r.loai);
      return el("div", {class: "m4-hang m4-kt-ydinh"}, el("span", {text: `Chưa rõ kết quả ${ten} (khóa ${r.khoa.slice(0, 13)}…, đã gửi ${r.soLan} lần). `}),
        nut("Gửi lại y nguyên (cùng khóa)", () => guiLai(r), "m4-chinh", !!tatLai, tatLai), tatLai ? nho(tatLai + " — lệnh chưa rõ được giữ nguyên, chưa gửi lại.") : null);
    });
  }
  function ve_() {
    if (!vungSong()) return;
    const out = [el("div", {class: "m4-hang m4-kt-tieu-de"}, el("h3", {text: "Kế toán nghiệm thu"}),
      nut("↻ Làm mới", () => napLai(), "", !pendingChon))];
    out.push(el("p", {class: "m4-kt-status m4-status" + (statusLoi ? " m4-loi-chu" : ""), role: "status", "aria-live": "polite", text: statusChu}));
    out.push(veDs());
    const ct = el("div", {class: "m4-kt-chi-tiet"});
    if (!pendingChon) ct.append(el("p", {class: "m4-trong", text: "Chọn một hồ sơ trong hộp chờ để xem nguồn và nhập số kế toán."}));
    else if (tinhTrang === "CHUA_NOI") ct.append(el("div", {class: "m4-notice m4-notice-loi", role: "alert"}, el("strong", {text: "Chưa nối backend kế toán nghiệm thu. "}),
      `Máy chủ chưa có dịch vụ ${SCHEMA}${loiGet ? " (" + loiGet + ")" : ""}. Không có số liệu kế toán/xác nhận nào được ghi; nháp được giữ, các lệnh tạm tắt.`));
    else if (tinhTrang === "KHONG_QUYEN") ct.append(el("div", {class: "m4-notice m4-notice-loi", role: "alert", text: `Không có quyền xem/thao tác hồ sơ kế toán này${loiGet ? ": " + loiGet : ""}. Bấm ↻ Làm mới để máy chủ kiểm lại quyền hiện hành.`}));
    else if (tinhTrang === "SAI_DTO") ct.append(el("div", {class: "m4-notice m4-notice-loi", role: "alert", text: `Phản hồi hồ sơ kế toán không đúng hợp đồng ${SCHEMA} (${loiGet}) — không hiển thị và không cho thao tác.`}));
    else if (tinhTrang === "LOI" && !dto) ct.append(el("div", {class: "m4-notice m4-notice-loi", text: loiGet || "Chưa đọc được hồ sơ kế toán."}));
    else if (!dto) ct.append(el("p", {class: "m4-trong", text: "Đang tải hồ sơ kế toán…"}));
    if (dto && (tinhTrang === "OK" || tinhTrang === "HOLD")) {
      if (tinhTrang === "HOLD") ct.append(el("div", {class: "m4-notice m4-notice-loi", role: "alert", text: `Phụ thuộc backend: ${loiGet}. Chỉ đọc — nháp được giữ, không gửi lưu/xác nhận.`}));
      ct.append(...veHoSo());
    } else if (dto) ct.append(nho("Dữ liệu đang hiện có thể chưa mới nhất — bấm ↻ Làm mới."));
    ct.append(...veYDinh());
    out.push(ct, nho("Gói M4-03A: chỉ xác nhận nguồn nghiệm thu cho kế toán. Chưa ghi công nợ/AP (M4-03B), chưa tạo/gửi Request (M4-04)."));
    box.replaceChildren(...out);
  }

  // ------------------------------------------------------------------ vòng đời (cổng đổi vai chung + cầu nối shell)
  function huy() {  // ĐỒNG BỘ: mọi GET/POST/blob/finally về muộn bị fence chặn; bản ghi ý định giữ theo phạm vi gốc (không gửi, không hiện ở vai khác)
    hoatDong = false; inc = null; box = null; khoaCtx = "";
    genView += 1; genGet += 1; genForm += 1; genDs += 1;
    ds = null; dsTinhTrang = "CHUA"; dsLoi = ""; pendingChon = null; phongBiChon = null;
    dto = null; tinhTrang = "CHUA"; loiGet = ""; thuHoi = false; statusChu = ""; statusLoi = false; ctxView = undefined;
    nhapMap.clear();
    dcMap.clear();
  }
  K.dangKyVai(VAI, huy, () => { if (vungSong()) napDs(); });
  window.kttM4KeToan = Object.freeze({
    ve(vung, c) {
      const k = JSON.stringify([(c && c.nguoi) || null]);
      if (!hoatDong || !inc || k !== khoaCtx) { huy(); inc = {}; khoaCtx = k; }
      box = vung; hoatDong = true;
      ve_();
      if (!ds && dsTinhTrang !== "CHUA_NOI" && dsTinhTrang !== "KHONG_QUYEN" && dsTinhTrang !== "DANG") napDs();
      if (pendingChon && !dto && tinhTrang !== "CHUA_NOI" && tinhTrang !== "KHONG_QUYEN" && tinhTrang !== "DANG") napLai();
    },
    huy,
  });
  if (typeof window.kttM4KeToanSanSang === "function") window.kttM4KeToanSanSang();
})();
