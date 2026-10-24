"use strict";
// M4-02C — tab "Duyệt & PDF" của Cổng hồ sơ M4: reviewer xem đúng phiên bản hồ sơ đợt bất biến (căn cứ/review/coverage/phát hiện), lưu kết luận NT/TT
// tách riêng, DUYỆT bằng quyền DUYET riêng, bổ sung PDF hồ sơ thanh toán đợt đã duyệt (bytes File gốc), xem trạng thái hai nhánh KT/Request.
// Hợp đồng: docs/M4-02C-UI-CONTRACT.md (GET /api/m4/duyet, POST duyet/ket-luan | duyet/chap-thuan | duyet/pdf, GET duyet/<version>/pdf/<pdf>,
// schema M4_DUYET_PDF_V1). Máy chủ sở hữu MỌI sự thật: danh tính, quyền hiện hành, ID, hash, trạng thái, seal, KT pending, Request readiness.
// Trình duyệt chỉ gửi ID/revision/basis đã đọc từ GET hợp lệ + chuỗi thập phân/lý do + khóa + bytes; không tự dựng duyệt/seal/KT/Request, không lưu
// cục bộ làm authority. Route/DTO chưa có (404/501/CHUA_NOI/schema lạ) → hiện "Chưa nối backend duyệt/PDF", tắt đúng lệnh bị ảnh hưởng, giữ nháp.
// Không tạo AP, không tạo/gửi Request ngoài, không OCR/trích PDF. Mọi chuỗi nguồn hiển thị bằng textContent.
// Vòng đời: shell m4.js gọi ve(vùng đã gắn, ngữ cảnh) / huy() ĐỒNG BỘ ở mọi lần đổi vai/PN/dự án/HĐ/đợt/tab/rời #m4; người tham gia cổng đổi vai
// chung "m4_duyet_pdf". Fence = incarnation + khóa ngữ cảnh chuỗi + thế hệ view (phiên bản/thu hồi) + thế hệ form/tệp + vé GET — kiểm sau MỌI await.
// Ý định: mỗi thao tác gốc = MỘT bản ghi chính xác (route, body chuỗi đã gửi / File gốc + X-M4-Info, khóa, ngữ cảnh gốc, incarnation); chưa rõ kết quả
// → chỉ Gửi lại y nguyên đúng bản ghi đó; lệnh mới cùng loại cùng phạm vi bị chặn tới khi bản ghi có kết quả rõ. Hoàn tất cũ chỉ cập nhật bản ghi
// của chính nó (vé từng lần gửi), không chạm form/toast/nút/GET của incarnation khác. Phân quyền/CAS/seal idempotent là trách nhiệm backend.
(() => {
  const K = window.kttChung;
  if (!K) return;  // shell chưa có seam
  const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || "";
  const SCHEMA = "M4_DUYET_PDF_V1", VAI = "m4_duyet_pdf", TOI_DA_Y_DINH = 32;
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, HEX64 = /^[0-9a-f]{64}$/i;
  const THAP_PHAN = /^-?(0|[1-9]\d*)(\.\d+)?$/;  // chuỗi thập phân chuẩn (dấu chấm, không phân cách nghìn) — không qua Number
  const laUuid = v => typeof v === "string" && UUID.test(v);
  const laChuoiSo = v => v === null || (typeof v === "string" && THAP_PHAN.test(v));
  const TT = {CHO_KET_LUAN: ["Chờ kết luận", "m4-thieu"], CHO_DUYET: ["Chờ duyệt", "m4-thieu"], CHO_PDF: ["Đã duyệt — Chờ PDF hồ sơ đợt", "m4-thieu"],
    DA_SEAL: ["Đã niêm phong với PDF hồ sơ đợt", "m4-du"], CAN_KIEM_LAI: ["Cần kiểm lại (căn cứ/phiên bản đã đổi)", "m4-loi"],
    CHUA_NOP: ["Chưa nộp hồ sơ", "m4-xam"]};  // CHUA_NOP chỉ hợp lệ ở biến thể gắn thẻ chua_nop=true (kiemChuaNop)
  const HANH = {KET_LUAN: {path: "duyet/ket-luan", ten: "lưu kết luận"}, CHAP_THUAN: {path: "duyet/chap-thuan", ten: "duyệt hồ sơ đợt"},
    PDF: {path: "duyet/pdf", ten: "tải PDF hồ sơ đợt"}};
  const CTX_TRUONG = ["dot_id", "hop_dong_id", "du_an_id", "phap_nhan_id", "version_id", "revision", "basis_sha256"];
  const ID_ACK = ["ket_luan_id", "quyet_dinh_id", "pdf_id", "seal_id", "kt_pending_id"];
  const TIEN = [["gia_tri_nt", "Giá trị nghiệm thu chấp nhận (NT)"], ["so_xin_thanh_toan", "Số xin thanh toán kỳ này (TT)"], ["tam_ung", "Tạm ứng kỳ này"],
    ["thu_hoi", "Thu hồi tạm ứng"], ["giu_lai", "Giữ lại (bảo hành/giữ lại)"]];
  const MAT_KET_NOI = "Mất kết nối với ứng dụng trên máy — chưa rõ máy chủ đã ghi hay chưa";
  const h12 = v => (typeof v === "string" && v ? v.slice(0, 12) + "…" : "—");
  const chu = v => (v === null || v === undefined ? "" : String(v));
  const thieuNeu = v => (v === null || v === undefined || v === "" ? "(thiếu)" : String(v));  // vắng/null hiện "(thiếu)" — "0" vẫn là "0"
  const chuGon = v => (v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v) : String(v));
  const NHAN_CAN_CU = {PHIEN_BAN: "Phiên bản đã nộp", VAT_LIEU: "Vật liệu hồ sơ HĐ/tham số/PL/BOQ", REVIEW_L3: "Review Chứng từ L3", REVIEW_L2: "Review L1+L2",
    TRUOC_DA_DUYET: "Lũy kế đợt trước đã duyệt", THUE: "Thuế/AP", DO_THI: "Đồ thị căn cứ"};
  function dinhDanhCanCu(x) {  // định danh theo ĐÚNG loại dữ kiện — không gọi digest/basis/H kết quả/SHA đồ thị là hash tệp gốc
    const p = [];
    if (x.loai === "PHIEN_BAN") { p.push("Bản số " + thieuNeu(x.so)); if (x.version_id) p.push("phiên bản " + h12(x.version_id)); p.push("digest phiên bản " + (x.digest ? h12(x.digest) : "(thiếu)")); }
    else if (x.loai === "VAT_LIEU") p.push("rev hồ sơ lúc nộp " + thieuNeu(x.revision_ho_so_nop), "rev hồ sơ hiện hành " + thieuNeu(x.revision_ho_so_hien_hanh));
    else if (x.loai === "REVIEW_L3" || x.loai === "REVIEW_L2") p.push("lần chạy " + (x.run_id ? h12(x.run_id) : "(chưa có)"), "basis review " + (x.basis_sha256 ? h12(x.basis_sha256) : "(chưa có)"),
      "H kết quả " + (x.ket_qua_sha256 ? h12(x.ket_qua_sha256) : "(chưa có)"));
    else if (x.loai === "TRUOC_DA_DUYET") p.push(`${Array.isArray(x.dot) ? x.dot.length : 0} đợt trước`);
    else if (x.loai === "DO_THI") p.push("SHA đồ thị " + (x.sha256 ? h12(x.sha256) : "(thiếu)"));
    else {  // loại máy chủ không gắn kiểu ở bảng này (DTO V1 cũ): hiện nguyên trường, không gán nghĩa
      if (x.ten || x.ten_goc) p.push(String(x.ten || x.ten_goc));
      if (x.sha256 || x.raw_sha256) p.push("SHA-256 (máy chủ không ghi loại) " + h12(x.sha256 || x.raw_sha256));
      if (x.byte_length !== undefined && x.byte_length !== null) p.push(x.byte_length + " byte");
    }
    return p.join(" · ") || "—";
  }

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
  let inc = null, hoatDong = false, box = null, ctx = null, khoaCtx = "";
  let genView = 0, genGet = 0, genForm = 0, genTep = 0;
  let dto = null, tinhTrang = "CHUA", loiGet = "", versionChon = null;  // tinhTrang: CHUA|DANG|OK|CHUA_NOI|KHONG_QUYEN|SAI_DTO|LOI
  let nhap = null, lyDoDuyet = "", tepChon = null, khaNang = {}, thuHoi = false, statusChu = "", statusLoi = false;
  // FIX01: phiên bản của DTO hợp lệ áp dụng gần nhất trong incarnation (không xóa khi DTO tạm null vì chưa nối/sai DTO) — đổi = đổi view (genView)
  let verView = undefined;
  // M4-04B: cầu nối widget Request nháp (m4_request_nhap.js, tải lười đúng một tệp). Vùng widget là MỘT phần tử giữ qua các lần vẽ lại cùng khóa
  // (ngữ cảnh + thế hệ view + phiên bản + seal); khóa đổi / hồ sơ không còn hợp lệ-đã seal-khớp phiên bản → gỡ widget ĐỒNG BỘ. Không đụng d.request.
  const SRC_RQ = "/m4/m4_request_nhap.js";
  let rqBox = null, rqKhoa = "", rqTai = 0;  // rqTai: 0 chưa tải | 1 đang tải | 2 đã có | -1 tải lỗi (thử lại khi khóa đổi)
  // bản ghi ý định chính xác (giới hạn): id → {loai, path, ctxKey, version, ctxGoc, body, bodyText, file, info, khoa, inc, trang, bay, soLan, ketQua, loi}
  const yDinh = new Map();
  let soYDinh = 0;
  const taoKhoa = () => "m4dp-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));
  const khoaCua = c => JSON.stringify([c.nguoi || null, c.phapNhanId || null, c.duAnId || null, c.hdId || null, c.dotId || null]);
  const vungSong = () => hoatDong && !!box && box.isConnected;
  function fenceView() {  // ngữ cảnh GỐC: incarnation + khóa ngữ cảnh + thế hệ view (phiên bản/thu hồi) + vùng còn gắn
    const i = inc, k = khoaCtx, v = genView;
    return () => vungSong() && i === inc && k === khoaCtx && v === genView;
  }
  const verHienHanh = () => (dto && dto.context ? dto.context.version_id : null);
  const recMo = loai => [...yDinh.values()].find(r => r.loai === loai && r.ctxKey === khoaCtx && r.version === verHienHanh() && r.trang !== "RO") || null;
  function donYDinh() {  // giới hạn: bỏ bản ghi ĐÃ RÕ cũ nhất; bản ghi đang bay/chưa rõ không bị bỏ ngầm
    for (const [id, r] of yDinh) { if (yDinh.size <= TOI_DA_Y_DINH) break; if (r.trang === "RO") yDinh.delete(id); }
  }
  function trangThai(msg, loi = false) {
    statusChu = msg || ""; statusLoi = !!loi;
    const s = box && box.querySelector(".m4-dp-status");
    if (s) { s.textContent = statusChu; s.className = "m4-dp-status m4-status" + (statusLoi ? " m4-loi-chu" : ""); }
  }
  function xoaBangChung() { dto = null; nhap = null; lyDoDuyet = ""; tepChon = null; genForm += 1; genTep += 1; }

  // ------------------------------------------------------------------ kiểm DTO GET (không tin trường nào ngoài hợp đồng làm authority)
  const laChuaNoiMa = c => typeof c === "string" && /CHUA_NOI/.test(c);
  function chuaNoiLoi(status, e) { return status === 501 || (status === 404 && (!e.error || e.error === "NOT_FOUND" || e.error === "HTTP_404")) || laChuaNoiMa(e.error); }
  const chuaNoiDto = d => !d || typeof d !== "object" || d.schema !== SCHEMA || d.chua_noi === true || laChuaNoiMa(d.trang_thai_backend);
  const laDoiTuong = v => !!v && typeof v === "object" && !Array.isArray(v);
  const QUYEN_4 = ["xem", "ket_luan", "duyet", "tai_pdf"];
  // biến thể CHƯA NỘP gắn thẻ chặt: chua_nop=true + CHUA_NOP, đúng ngữ cảnh đang mở, KHÔNG chọn phiên bản tường minh; không phiên bản/basis/hiệu lực,
  // mọi cờ lệnh false, mọi mảng bằng chứng rỗng. Sai bất kỳ → sai hợp đồng (không đoán, không hạ cấp thành hồ sơ có phiên bản).
  function kiemChuaNop(d, ver) {
    const c = d.context, q = d.quyen;
    if (d.chua_nop !== true || d.trang_thai !== "CHUA_NOP") return "biến thể chưa nộp thiếu thẻ chua_nop/CHUA_NOP";
    if (ver) return "chưa nộp nhưng đã chọn phiên bản tường minh";
    if (c.version_id !== null || c.basis_sha256 !== null || c.revision !== 0) return "chưa nộp mà có phiên bản/basis/revision";
    if (!q || QUYEN_4.some(k => typeof q[k] !== "boolean")) return "quyền không tường minh";
    if (q.ket_luan !== false || q.duyet !== false || q.tai_pdf !== false || q.phien_ban !== false) return "chưa nộp mà có quyền lệnh";
    if (!Array.isArray(d.phien_ban) || d.phien_ban.length) return "chưa nộp mà có phiên bản";
    if (["can_cu", "review_refs", "phat_hien", "dong_nt", "tep_can_cu"].some(k => !Array.isArray(d[k]) || d[k].length)) return "chưa nộp mà có căn cứ/review/phát hiện/dòng/tệp";
    if (["ket_luan_lich_su", "pdf_lich_su"].some(k => d[k] !== undefined && (!Array.isArray(d[k]) || d[k].length))) return "chưa nộp mà có lịch sử kết luận/PDF";
    if (!Array.isArray(d.lich_su)) return "thiếu lịch sử";
    if (!laDoiTuong(d.coverage) || Object.keys(d.coverage).length) return "chưa nộp mà có coverage";
    if (["ket_luan", "quyet_dinh", "pdf", "seal"].some(k => d[k] !== null)) return "chưa nộp mà có kết luận/quyết định/PDF/seal";
    const kt = d.kt, rq = d.request;
    if (!kt || kt.trang_thai !== "CHUA_CHUYEN" || kt.pending_id !== null || (kt.goc_id !== undefined && kt.goc_id !== null)
      || (kt.phong_bi_id !== undefined && kt.phong_bi_id !== null)) return "chưa nộp mà có KT";
    if (!rq || rq.trang_thai !== "CHO_PDF") return "chưa nộp mà Request khác Chờ PDF";
    // M4-03A P2 (§5a): đúng shape producer CHUA_NOP (duyet_dot.py) — không đồ thị, không cờ phiên bản hiện hành, KT không phong bì/không phong bì hiện hành
    if (d.do_thi !== null) return "chưa nộp mà có đồ thị căn cứ";
    if (d.phien_ban_hien_hanh !== false) return "chưa nộp mà cờ phiên bản hiện hành khác false";
    if (!Array.isArray(kt.phong_bi) || kt.phong_bi.length) return "chưa nộp mà có phong bì KT";
    if (kt.phong_bi_hien_hanh !== false) return "chưa nộp mà cờ phong bì KT hiện hành khác false";
    return null;
  }
  function kiemDto(d, dotId, ver) {
    const c = d.context, q = d.quyen;
    if (!c || typeof c !== "object") return "thiếu context";
    if (c.dot_id !== dotId || c.hop_dong_id !== ctx.hdId) return "context khác đợt/HĐ đang mở";
    if ((ctx.duAnId && c.du_an_id !== ctx.duAnId) || (ctx.phapNhanId && c.phap_nhan_id !== ctx.phapNhanId)) return "context khác dự án/pháp nhân đang mở";
    if (d.chua_nop !== undefined && typeof d.chua_nop !== "boolean") return "chua_nop không phải boolean";
    if (d.chua_nop === true || d.trang_thai === "CHUA_NOP") return kiemChuaNop(d, ver);
    // DTO có phiên bản (V1 cũ thiếu chua_nop vẫn hợp lệ): UUID/HEX/quyền/hiệu lực chặt như cũ
    if (!laUuid(c.version_id) || (ver && c.version_id !== ver)) return "phiên bản không đúng phiên bản đã chọn";
    if (!Number.isInteger(c.revision) || c.revision < 0 || typeof c.basis_sha256 !== "string" || !HEX64.test(c.basis_sha256)) return "revision/basis không hợp lệ";
    if (!q || ["xem", "ket_luan", "duyet", "tai_pdf"].some(k => typeof q[k] !== "boolean")) return "quyền không tường minh";
    if (!Object.prototype.hasOwnProperty.call(TT, d.trang_thai)) return "trạng thái lạ";
    if (["can_cu", "review_refs", "phat_hien", "dong_nt", "lich_su"].some(k => !Array.isArray(d[k]))) return "thiếu mảng căn cứ/review/phát hiện/dòng NT/lịch sử";
    if (!d.coverage || typeof d.coverage !== "object") return "thiếu coverage";
    const rowIds = new Set();
    for (const r of d.dong_nt) { if (!r || typeof r.row_id !== "string" || !r.row_id || rowIds.has(r.row_id)) return "dòng NT thiếu/trùng row_id"; rowIds.add(r.row_id); }
    for (const p of d.phat_hien) if (!p || typeof p.finding_id !== "string" || !p.finding_id) return "phát hiện thiếu finding_id";
    // trường bổ sung (vắng ở DTO V1 cũ = chưa cung cấp, KHÔNG phải rỗng/0): có thì phải đúng kiểu
    for (const r of d.dong_nt) {
      if (r.de_xuat === undefined) continue;
      if (!laDoiTuong(r.de_xuat)) return "đề xuất nguồn của dòng không phải đối tượng";
      if (["kl_kn", "kl_lk", "kl_hd", "don_gia"].some(t => r.de_xuat[t] !== undefined && !laChuoiSo(r.de_xuat[t]))) return "số đề xuất nguồn không phải chuỗi thập phân/null";
    }
    for (const p of d.phat_hien) if (p.xu_ly !== undefined && p.xu_ly !== null && (!laDoiTuong(p.xu_ly) || typeof p.xu_ly.ly_do !== "string")) return "giải trình phát hiện sai kiểu";
    for (const r of d.review_refs) if (!r || (r.cong_bo !== undefined && r.cong_bo !== null && typeof r.cong_bo !== "boolean")) return "cờ công bố review sai kiểu";
    if (d.tep_can_cu !== undefined) {
      if (!Array.isArray(d.tep_can_cu)) return "tệp căn cứ không phải mảng";
      for (const t of d.tep_can_cu) {
        if (!laDoiTuong(t)) return "tệp căn cứ sai kiểu";
        if ((t.tep_id !== null && t.tep_id !== undefined && !laUuid(t.tep_id)) || [t.raw_sha256, t.raw_sha256_da_chup].some(h => h !== null && h !== undefined && !(typeof h === "string" && HEX64.test(h)))
          || (t.byte_length !== null && t.byte_length !== undefined && (!Number.isInteger(t.byte_length) || t.byte_length < 0))) return "metadata tệp căn cứ sai kiểu";
      }
    }
    if (d.phien_ban !== undefined) {
      if (!Array.isArray(d.phien_ban) || d.phien_ban.some(v => !laDoiTuong(v) || !laUuid(v.version_id))) return "lịch sử phiên bản sai kiểu";
      if (d.phien_ban.length && !d.phien_ban.some(v => v.version_id === c.version_id)) return "lịch sử phiên bản không gồm phiên bản đang xem";
    }
    const k = d.ket_luan;
    if (k !== null) {
      if (!k || !laUuid(k.id) || !Number.isInteger(k.revision)) return "kết luận thiếu id/revision";
      if (TIEN.some(([t]) => !laChuoiSo(k[t] === undefined ? null : k[t]))) return "số tiền kết luận không phải chuỗi thập phân/null";
      if ((k.dong_nt || []).some(r => !r || !laChuoiSo(r.khoi_luong_chap_nhan === undefined ? null : r.khoi_luong_chap_nhan))) return "khối lượng chấp nhận không phải chuỗi thập phân/null";
    }
    if (d.quyet_dinh !== null && (!d.quyet_dinh || !laUuid(d.quyet_dinh.id))) return "quyết định thiếu id";
    const p = d.pdf, s = d.seal;
    if (p !== null && (!p || !laUuid(p.id) || p.version_id !== c.version_id || typeof p.sha256 !== "string" || !HEX64.test(p.sha256)
      || !Number.isInteger(p.byte_length) || p.byte_length <= 0)) return "PDF thiếu id/phiên bản/hash/độ dài";
    if (s !== null && (!s || !laUuid(s.id) || s.version_id !== c.version_id || !p || s.pdf_id !== p.id || !d.quyet_dinh)) return "seal không gắn đúng PDF/phiên bản/quyết định";
    const kt = d.kt, rq = d.request;
    if (!kt || !["CHUA_CHUYEN", "CHO_XAC_NHAN"].includes(kt.trang_thai) || (kt.pending_id !== null && !laUuid(kt.pending_id))) return "trạng thái KT lạ";
    if (kt.trang_thai === "CHO_XAC_NHAN" ? (!s || !kt.pending_id) : kt.pending_id !== null) return "KT chờ xác nhận không có seal";
    if (kt.goc_id !== undefined && kt.goc_id !== null && !laUuid(kt.goc_id)) return "gốc KT sai kiểu";
    if (!rq || !["CHO_PDF", "DU_DIEU_KIEN_CHUA_NOI"].includes(rq.trang_thai) || (rq.trang_thai === "DU_DIEU_KIEN_CHUA_NOI" && !s)) return "trạng thái Request lạ";
    if ((d.trang_thai === "DA_SEAL") !== !!s) return "trạng thái seal không nhất quán";
    if (d.trang_thai === "CHO_PDF" && !d.quyet_dinh) return "Chờ PDF không có quyết định";
    return null;
  }
  // ACK mutation: đúng schema/hành động/khóa/ngữ cảnh GỐC + receipt + ID typed. Sai bất kỳ → CHƯA RÕ (không coi là đã lưu/duyệt)
  function kiemAck(rec, a) {
    if (!a || typeof a !== "object" || a.schema !== SCHEMA) return "schema";
    if (a.hanh_dong !== rec.loai || a.khoa !== rec.khoa) return "hành động/khóa không khớp lệnh đã gửi";
    const c = a.context;
    if (!c || typeof c !== "object" || CTX_TRUONG.some(t => c[t] !== rec.ctxGoc[t])) return "ngữ cảnh không khớp hồ sơ/phiên bản/basis đã gửi";
    if (!laUuid(a.receipt_id)) return "thiếu biên nhận";
    for (const t of ID_ACK) if (!Object.prototype.hasOwnProperty.call(a, t) || (a[t] !== null && !laUuid(a[t]))) return "ID " + t + " không tường minh";
    if ((a.seal_id === null) !== (a.kt_pending_id === null) || (a.seal_id !== null && a.pdf_id === null)) return "seal/KT/PDF không nhất quán";
    if (rec.loai === "KET_LUAN" && (a.ket_luan_id === null || a.seal_id !== null)) return "thiếu ID kết luận";
    if (rec.loai === "CHAP_THUAN" && (a.quyet_dinh_id === null || a.ket_luan_id !== rec.body.ket_luan_id)) return "thiếu ID quyết định/kết luận khác";
    if (rec.loai === "PDF" && a.pdf_id === null) return "thiếu ID PDF";
    return null;
  }

  // ------------------------------------------------------------------ nạp (GET có barrier đổi vai + vé + fence)
  async function napLai(opt = {}) {
    if (!vungSong() || !ctx || !ctx.dotId || (opt.ngoai && !opt.ngoai())) return;
    if (K.vaiDangChan(VAI)) return;
    const g = ++genGet, gf = genForm, fv = fenceView(), ver = versionChon, dotId = ctx.dotId;
    const f = () => fv() && g === genGet && (!opt.ngoai || opt.ngoai());
    if (!dto) { tinhTrang = "DANG"; ve_(); }
    const q = new URLSearchParams({dot_id: dotId});
    if (ver) q.set("version_id", ver);
    let res;
    try { res = await fetch("/api/m4/duyet?" + q.toString(), {headers: {"X-KTT-Token": TOKEN}, cache: "no-store", credentials: "same-origin"}); }
    catch (_) { if (!f()) return; if (!dto) tinhTrang = "LOI"; loiGet = MAT_KET_NOI + "."; trangThai(loiGet, true); ve_(); return; }
    if (!f()) return;
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      if (!f()) return;
      if (chuaNoiLoi(res.status, e)) { dto = null; tinhTrang = "CHUA_NOI"; loiGet = e.message || ""; trangThai("Chưa nối backend duyệt/PDF — nháp được giữ, các lệnh tạm tắt.", true); ve_(); return; }
      if (res.status === 403 || res.status === 404) {  // thu hồi/ngoài phạm vi: xóa bằng chứng + lệnh của incarnation này
        xoaBangChung(); genView += 1; thuHoi = true; tinhTrang = "KHONG_QUYEN"; loiGet = e.message || "";
        trangThai((e.message || "Không có quyền") + " — đã gỡ hồ sơ duyệt khỏi màn hình (quyền hiện hành do máy chủ kiểm).", true); ve_(); return;
      }
      if (!dto) tinhTrang = "LOI";
      loiGet = e.message || `Không đọc được hồ sơ duyệt (${res.status}).`; trangThai(loiGet, true); ve_(); return;
    }
    let d;
    try { d = await res.json(); } catch (_) { d = undefined; }
    if (!f()) return;
    if (d === undefined) { if (!dto) tinhTrang = "LOI"; loiGet = "Phản hồi hồ sơ duyệt đọc không trọn — chưa hiển thị."; trangThai(loiGet, true); ve_(); return; }
    if (chuaNoiDto(d)) { dto = null; tinhTrang = "CHUA_NOI"; loiGet = ""; trangThai("Chưa nối backend duyệt/PDF (máy chủ chưa trả DTO " + SCHEMA + ") — nháp được giữ.", true); ve_(); return; }
    const sai = kiemDto(d, dotId, ver);
    if (sai) { dto = null; tinhTrang = "SAI_DTO"; loiGet = sai; trangThai("Phản hồi hồ sơ duyệt không đúng hợp đồng (" + sai + ") — không hiển thị, không cho thao tác.", true); ve_(); return; }
    // 200 hợp lệ nhưng xem=false = thu hồi hiện hành: gỡ bằng chứng VÀ thu hồi view ĐỒNG BỘ (genView) — ACK/blob/lỗi/finally đang giữ của view này không
    // còn hiệu ứng muộn (toast/GET/click). Bản ghi ý định CHƯA RÕ (body/khóa/File gốc) giữ nguyên; Gửi lại chờ máy chủ trả lại quyền hiện hành.
    if (d.quyen.xem !== true) { xoaBangChung(); genView += 1; thuHoi = true; tinhTrang = "KHONG_QUYEN"; loiGet = ""; trangThai("Vai này không có quyền xem hồ sơ duyệt của đợt.", true); ve_(); return; }
    if (gf !== genForm && !opt.giu) { trangThai("Dữ liệu mới đã về trong lúc bạn đang nhập — chưa áp dụng để giữ nháp; bấm ↻ Làm mới khi xong."); return; }
    // FIX01: máy chủ trả phiên bản KHÁC phiên bản đang hiện (mới nhất đổi, kể cả V1→V2→V1) = đổi view → thế hệ view tăng ĐƠN ĐIỆU: ACK/lỗi/finally/
    // blob của view cũ chỉ còn cập nhật bản ghi ý định của chính nó (so UUID không đủ cho ABA). Nháp/genForm không đổi (409 vẫn giữ nháp).
    // undefined = chưa có view; null = view CHƯA NỘP (khác mọi phiên bản thật)
    if (verView !== undefined && d.context.version_id !== verView) genView += 1;
    verView = d.context.version_id;
    dto = d; tinhTrang = "OK"; loiGet = ""; thuHoi = false;
    if (!nhap || (opt.hat && opt.hat())) nhap = nhapTu(d);
    ve_();
  }

  // ------------------------------------------------------------------ nháp form (chuỗi; trống = thiếu ≠ "0")
  function nhapTu(d) {
    const k = d.ket_luan || {}, dong = {}, ph = {};
    for (const r of k.dong_nt || []) if (r && typeof r.row_id === "string") dong[r.row_id] = chu(r.khoi_luong_chap_nhan);
    for (const p of k.xu_ly_phat_hien || []) if (p && typeof p.finding_id === "string") ph[p.finding_id] = chu(p.ly_do);
    const n = {tien_te: chu(k.tien_te), ly_do: chu(k.ly_do), dong, ph};
    for (const [t] of TIEN) n[t] = chu(k[t]);
    return n;
  }
  const soHoa = v => { const t = String(v ?? "").trim(); return t === "" ? null : t; };
  function noiDung(n) {  // nội dung kết luận (không có ngữ cảnh/khóa) — dùng cho body và so nháp với kết luận đã lưu
    const b = {};
    for (const [t] of TIEN) b[t] = soHoa(n[t]);
    b.tien_te = soHoa(n.tien_te);
    b.dong_nt = dto.dong_nt.map(r => ({row_id: r.row_id, khoi_luong_chap_nhan: soHoa(n.dong[r.row_id])}));
    b.xu_ly_phat_hien = dto.phat_hien.filter(p => soHoa(n.ph[p.finding_id]) !== null).map(p => ({finding_id: p.finding_id, ly_do: soHoa(n.ph[p.finding_id])}));
    b.ly_do = soHoa(n.ly_do);
    return b;
  }
  const nhapKhacDaLuu = () => !!(dto && nhap) && JSON.stringify(noiDung(nhap)) !== JSON.stringify(noiDung(nhapTu(dto)));

  // ------------------------------------------------------------------ lệnh (một bản ghi ý định chính xác cho mỗi thao tác gốc)
  const QUYEN_LENH = {KET_LUAN: ["ket_luan", "Vai này không có quyền lưu kết luận"], CHAP_THUAN: ["duyet", "Vai này không có quyền DUYỆT riêng (REVIEW/SOẠN không đủ)"],
    PDF: ["tai_pdf", "Vai này không có quyền bổ sung PDF hồ sơ đợt"]};
  // FIX01: cổng dùng chung cho lệnh mới VÀ Gửi lại y nguyên — hồ sơ hiện hành hợp lệ + khả năng backend + quyền tường minh HIỆN HÀNH của đúng loại lệnh.
  // Không gồm recMo/trạng thái sau ghi (đã duyệt/đã lưu): Gửi lại cùng khóa phải đối soát được cả khi máy chủ đã ghi lần trước.
  function lyDoTatQuyen(loai) {
    if (tinhTrang !== "OK" || !dto || thuHoi) return "Chưa có hồ sơ hợp lệ từ máy chủ";
    if (dto.chua_nop === true) return "Đợt chưa nộp — chưa có phiên bản hồ sơ để thao tác";
    if (khaNang[loai] === "CHUA_NOI" || (dto.kha_nang && laChuaNoiMa(dto.kha_nang[loai]))) return "Chưa nối backend cho lệnh này";
    const [k, ly] = QUYEN_LENH[loai];
    return dto.quyen[k] === true ? null : ly;
  }
  function lyDoTat(loai) {  // null = được gửi; chuỗi = lý do tắt (máy chủ vẫn kiểm lại quyền/CAS)
    const tq = lyDoTatQuyen(loai);
    if (tq) return tq;
    if (loai === "KET_LUAN") {
      if (dto.quyet_dinh) return "Đã duyệt — kết luận đã chốt theo quyết định";
      if (!["CHO_KET_LUAN", "CHO_DUYET"].includes(dto.trang_thai)) return "Trạng thái máy chủ không cho lưu kết luận";
    } else if (loai === "CHAP_THUAN") {
      if (dto.quyet_dinh) return "Đã có quyết định duyệt";
      if (!dto.ket_luan || dto.trang_thai !== "CHO_DUYET") return "Chưa có kết luận đã lưu ở trạng thái Chờ duyệt";
      if (nhapKhacDaLuu()) return "Nháp đang khác kết luận đã lưu — lưu kết luận trước khi duyệt";
    } else if (loai === "PDF") {
      if (dto.seal) return "Đã niêm phong — PDF của seal không thay";
      if (dto.trang_thai === "CAN_KIEM_LAI") return "Hồ sơ cần kiểm lại — không gắn PDF vào phiên bản này";
    }
    const r = recMo(loai);
    if (r) return r.bay ? "Đang gửi lệnh này — chờ kết quả" : "Lệnh trước chưa rõ kết quả — bấm Gửi lại y nguyên";
    return null;
  }
  function taoYDinh(loai, body, file) {  // ĐỒNG BỘ trong handler, trước await đầu tiên
    if (yDinh.size >= TOI_DA_Y_DINH) { donYDinh(); if (yDinh.size >= TOI_DA_Y_DINH) { trangThai("Quá nhiều lệnh chưa rõ kết quả — Gửi lại y nguyên các lệnh đó trước.", true); return null; } }
    const c = dto.context, khoa = taoKhoa(), ctxGoc = {};
    for (const t of CTX_TRUONG) ctxGoc[t] = c[t];
    const rec = {id: ++soYDinh, loai, path: HANH[loai].path, ctxKey: khoaCtx, version: c.version_id, ctxGoc, khoa, inc, trang: "MOI", bay: null, soLan: 0,
      ketQua: null, loi: null, body: null, bodyText: null, file: null, info: null, gf: genForm};  // gf: thế hệ form LÚC TẠO ý định (không phải lúc gửi lại)
    if (file) {
      const duoi = (file.name.split(".").pop() || "").toLowerCase();
      rec.file = file;  // File GỐC (đúng đối tượng/bytes) — mọi lần Gửi lại dùng lại chính nó
      rec.info = encodeURIComponent(JSON.stringify({dot_id: c.dot_id, version_id: c.version_id, revision: c.revision, expected_basis: c.basis_sha256,
        ten: file.name, media_type: file.type || (duoi === "pdf" ? "application/pdf" : ""), khoa}));
      if (rec.info.length > 4000) { trangThai("Tên tệp quá dài — đổi tên ngắn hơn rồi chọn lại.", true); return null; }
    } else {
      rec.body = {dot_id: c.dot_id, version_id: c.version_id, revision: c.revision, expected_basis: c.basis_sha256, ...body, khoa};
      rec.bodyText = JSON.stringify(rec.body);  // body GỐC chuỗi hóa một lần — Gửi lại y nguyên từng byte
    }
    yDinh.set(rec.id, rec);
    return rec;
  }
  function phanLoaiLoi(status, e) {
    if (chuaNoiLoi(status, e)) return {loai: "LOI", chuaNoi: true, status, msg: e.message || ""};
    if (status >= 500 || e.error === "M4_KET_QUA_CHUA_RO") return {loai: "CHUA_RO", msg: e.message || `máy chủ trả ${status}`};
    return {loai: "LOI", status, code: e.error || "HTTP_" + status, msg: e.message || `Không hoàn tất (${status}).`};
  }
  async function phat(rec) {  // gửi (hoặc Gửi lại) ĐÚNG bản ghi: cùng route/body chuỗi hoặc File gốc + X-M4-Info, cùng khóa
    if (rec.bay) { trangThai(`Đang ${HANH[rec.loai].ten} — chờ kết quả, không gửi thêm.`); return; }
    const tk = {}, f = fenceView(), ten = HANH[rec.loai].ten;
    rec.bay = tk; rec.trang = "BAY"; rec.inc = inc; rec.soLan += 1;
    trangThai(`Đang ${ten}…`); ve_();
    const opts = rec.file
      ? {method: "POST", headers: {"X-KTT-Token": TOKEN, "X-M4-Info": rec.info}, body: rec.file, cache: "no-store", credentials: "same-origin"}
      : {method: "POST", headers: {"X-KTT-Token": TOKEN, "Content-Type": "application/json"}, body: rec.bodyText, cache: "no-store", credentials: "same-origin"};
    let kq;
    try {
      const res = await fetch("/api/m4/" + rec.path, opts);
      if (res.ok) {
        let a, doc = true;
        try { a = await res.json(); } catch (_) { doc = false; }
        const sai = doc ? kiemAck(rec, a) : "phản hồi đọc không trọn";
        kq = sai ? {loai: "CHUA_RO", msg: "phản hồi 2xx không đúng hợp đồng (" + sai + ")"} : {loai: "OK", ack: a};
      } else kq = phanLoaiLoi(res.status, await res.json().catch(() => ({})));
    } catch (_) { kq = {loai: "CHUA_RO", msg: MAT_KET_NOI}; }
    if (rec.bay !== tk) return;  // phòng thủ: vé không còn của lần gửi này
    rec.bay = null;
    if (kq.loai === "OK") {  // ID chỉ lưu vào ĐÚNG bản ghi ý định gốc (nội bộ), không gán cho hồ sơ/ngữ cảnh khác
      const a = kq.ack; rec.trang = "RO"; rec.ketQua = {receipt_id: a.receipt_id};
      for (const t of ID_ACK) rec.ketQua[t] = a[t];
    } else if (kq.loai === "CHUA_RO") rec.trang = "CHUA_RO";
    else { rec.trang = "RO"; rec.loi = {status: kq.status, code: kq.code || null}; }
    donYDinh();
    if (!f()) {  // ngữ cảnh/incarnation/view đã đổi: KHÔNG toast/trạng thái/GET/đổi nháp; chỉ vẽ lại hàng ý định nếu đúng phạm vi gốc đang mở lại
      if (vungSong() && rec.ctxKey === khoaCtx && rec.inc !== inc) ve_();
      return;
    }
    if (kq.loai === "OK") {
      const a = kq.ack, lai = a.lap_lai === true ? " (biên nhận cũ của cùng khóa — không ghi thêm)" : "";
      let msg;
      if (rec.loai === "KET_LUAN") msg = `Đã lưu kết luận · biên nhận ${h12(a.receipt_id)}${lai}`;
      else if (rec.loai === "CHAP_THUAN") msg = a.seal_id ? `Đã duyệt và niêm phong với PDF đã lưu — hồ sơ kế toán Chờ xác nhận (chưa ghi nhận AP)${lai}`
        : `Đã duyệt — Chờ PDF hồ sơ đợt; chưa chuyển kế toán, Request chưa đủ điều kiện${lai}`;
      else msg = a.seal_id ? `Đã lưu PDF hồ sơ đợt và niêm phong — hồ sơ kế toán Chờ xác nhận (chưa ghi nhận AP)${lai}` : `Đã lưu PDF hồ sơ đợt · chưa niêm phong (chờ duyệt)${lai}`;
      K.toast(msg); trangThai(msg);
      let hat = false;  // nháp đã gửi được dọn → GET đọc lại hạt lại từ kết luận máy chủ (nếu không gõ thêm trước khi GET về)
      if (rec.gf === genForm) { if (rec.loai === "KET_LUAN") { nhap = null; hat = true; } if (rec.loai === "CHAP_THUAN") lyDoDuyet = ""; }
      else trangThai(msg + " — form đã sửa trong lúc chờ nên nháp hiện tại được giữ.");
      if (rec.loai === "PDF" && tepChon === rec.file) tepChon = null;  // chỉ bỏ chọn đúng File đã gửi; tệp Y chọn sau vẫn giữ
      ve_();  // gỡ ngay hàng ý định/nút Gửi lại đã rõ (không chờ GET)
      const gHat = genForm;
      await napLai({ngoai: f, giu: true, hat: () => hat && genForm === gHat});
      return;
    }
    if (kq.loai === "CHUA_RO") {
      const msg = `Chưa rõ kết quả ${ten}: ${kq.msg}. Không coi là đã lưu/duyệt; nháp và khóa gốc được giữ — bấm Gửi lại y nguyên (cùng khóa) để máy chủ đối soát.`;
      K.toast(msg, true); trangThai(msg, true); ve_(); return;
    }
    K.toast(kq.msg || ("Không " + ten), true);
    if (kq.chuaNoi) { khaNang[rec.loai] = "CHUA_NOI"; trangThai(`Chưa nối backend duyệt/PDF cho lệnh ${ten} — nháp được giữ, lệnh này tạm tắt.`, true); ve_(); return; }
    if (kq.status === 403 || kq.status === 404) {
      xoaBangChung(); genView += 1; thuHoi = true; tinhTrang = "KHONG_QUYEN";
      trangThai((kq.msg || "Không có quyền") + " — đã gỡ hồ sơ, lệnh và tải tệp khỏi màn hình (máy chủ kiểm quyền hiện hành).", true); ve_(); return;
    }
    if (kq.status === 409) {
      trangThai((kq.msg || "Hồ sơ đã đổi") + " — đã đọc lại phiên bản/basis hiện hành; nháp được giữ, kiểm tra rồi gửi lại.", true);
      await napLai({ngoai: f, giu: true}); return;
    }
    trangThai(kq.msg, true); ve_();
  }
  function luuKetLuan() {
    const tat = lyDoTat("KET_LUAN");
    if (tat) { trangThai(tat + ".", true); return; }
    const b = noiDung(nhap), sai = [];
    for (const [t, nhan] of TIEN) if (!laChuoiSo(b[t])) sai.push(nhan);
    for (const r of b.dong_nt) if (!laChuoiSo(r.khoi_luong_chap_nhan)) sai.push("KL chấp nhận " + r.row_id);
    if (sai.length) { trangThai("Số không hợp lệ: " + sai.join("; ") + " — nhập dạng 1234567.50 (dấu chấm thập phân, không phân cách nghìn); để trống = thiếu.", true); return; }
    const rec = taoYDinh("KET_LUAN", b);
    if (rec) phat(rec);
  }
  function duyet() {
    const tat = lyDoTat("CHAP_THUAN");
    if (tat) { trangThai(tat + ".", true); return; }
    const rec = taoYDinh("CHAP_THUAN", {ket_luan_id: dto.ket_luan.id, ly_do: soHoa(lyDoDuyet)});
    if (rec) phat(rec);
  }
  function guiPdf() {
    const tat = lyDoTat("PDF");
    if (tat) { trangThai(tat + ".", true); return; }
    const file = tepChon;  // chụp ĐỒNG BỘ lúc bấm
    if (!file) { trangThai("Chọn tệp PDF hồ sơ đợt đã duyệt trước.", true); return; }
    if (!file.size) { trangThai("Tệp rỗng (0 byte) — không gửi.", true); return; }
    const rec = taoYDinh("PDF", null, file);
    if (rec) phat(rec);
  }
  function guiLai(rec) {  // Gửi lại y nguyên: chỉ ở đúng ngữ cảnh/phiên bản gốc, hồ sơ hiện hành đọc hợp lệ, chưa bị thu hồi
    if (!vungSong() || rec.ctxKey !== khoaCtx || rec.version !== verHienHanh() || tinhTrang !== "OK" || thuHoi || K.vaiDangChan(VAI)) {
      trangThai("Lệnh chưa rõ thuộc ngữ cảnh/phiên bản khác hoặc chưa đọc lại được hồ sơ — không gửi lại.", true); return;
    }
    if (rec.trang !== "CHUA_RO") { trangThai(rec.bay ? "Đang gửi lại lệnh này — chờ kết quả." : "Lệnh này đã có kết quả.", true); return; }
    const tq = lyDoTatQuyen(rec.loai);  // FIX01: mất quyền hiện hành ≠ thất bại chắc chắn — giữ nguyên bản ghi/body/khóa/File gốc, không gửi
    if (tq) { trangThai(tq + " — lệnh chưa rõ được giữ nguyên (cùng khóa), chưa gửi lại; Gửi lại được khi máy chủ trả lại quyền hiện hành.", true); return; }
    phat(rec);
  }

  // ------------------------------------------------------------------ tải PDF đã lưu (đường dẫn dựng từ UUID đã kiểm; fence trước click)
  async function taiPdf() {
    if (!dto || !dto.pdf || thuHoi || tinhTrang !== "OK") return;
    const p = dto.pdf, f = fenceView(), dai = p.byte_length, ten = p.name || "ho-so-dot.pdf";
    if (!laUuid(p.id) || !laUuid(p.version_id) || p.version_id !== verHienHanh()) return;
    try {
      const res = await fetch("/api/m4/duyet/" + encodeURIComponent(p.version_id) + "/pdf/" + encodeURIComponent(p.id),
        {headers: {"X-KTT-Token": TOKEN}, cache: "no-store", credentials: "same-origin"});
      if (!f()) return;
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        if (!f()) return;
        if (res.status === 403) { xoaBangChung(); genView += 1; thuHoi = true; tinhTrang = "KHONG_QUYEN"; trangThai((e.message || "Không có quyền") + " — không tải.", true); ve_(); return; }
        trangThai(chuaNoiLoi(res.status, e) ? "Chưa nối backend tải PDF hồ sơ đợt." : (e.message || `Không tải được PDF (${res.status}).`), true); return;
      }
      const blob = await res.blob();
      if (!f()) return;  // bytes về sau khi rời ngữ cảnh/module: không click
      if (blob.size !== dai) { trangThai(`Bytes tải về (${blob.size}) khác độ dài máy chủ đã lưu (${dai}) — không lưu tệp.`, true); return; }
      if (!f()) return;  // ngay trước khi công bố object URL / click
      const url = URL.createObjectURL(blob), a = document.createElement("a");
      a.href = url; a.download = ten; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      trangThai(`Đã tải ${ten} (${blob.size} byte).`);
    } catch (_) { if (f()) trangThai(MAT_KET_NOI + " — chưa tải được PDF.", true); }
  }

  // ------------------------------------------------------------------ giao diện
  function oNhap(nhan, gia, ghi, kieu) {  // ô nhập: cập nhật nháp + thế hệ form; không vẽ lại khi gõ
    const i = el(kieu === "area" ? "textarea" : "input", {"aria-label": nhan, autocomplete: "off"});
    if (kieu !== "area") i.type = "text";
    i.value = gia;
    i.addEventListener("input", () => { ghi(i.value); genForm += 1; });
    return i;
  }
  function oTien(t, nhan, tat) {  // trống = THIẾU (gửi null) — khác số 0 được nhập tường minh
    const tag = pill(soHoa(nhap[t]) === null ? "Thiếu" : "Có số", soHoa(nhap[t]) === null ? "m4-thieu" : "m4-du");
    const i = oNhap(nhan, nhap[t], v => { nhap[t] = v; const co = soHoa(v) !== null; tag.textContent = co ? "Có số" : "Thiếu"; tag.className = "m4-pill " + (co ? "m4-du" : "m4-thieu"); });
    i.disabled = !!tat; i.inputMode = "decimal";
    return el("label", {}, el("span", {text: nhan}), i, tag);
  }
  function veHoSo() {
    const d = dto, c = d.context, [ttTen, ttCls] = TT[d.trang_thai], out = [];
    if (!nhap) nhap = nhapTu(d);  // nháp đã xóa sau lưu thành công nhưng GET đọc lại chưa về: hạt từ kết luận máy chủ đang hiện
    const ds = Array.isArray(d.phien_ban) ? d.phien_ban.filter(v => v && laUuid(v.version_id)) : [];
    const dau = el("section", {class: "m4-card m4-dp-ban"}, el("div", {class: "m4-hang"}, el("strong", {text: `Phiên bản hồ sơ đợt ${h12(c.version_id)} · revision ${c.revision}`}),
      pill(ttTen, ttCls)), nho(`Basis ${h12(c.basis_sha256)} · ${ctx.soHd || ""} · bản bất biến do máy chủ chọn${versionChon ? " (đã chọn tường minh)" : " (mới nhất/hiện hành)"}`));
    if (typeof d.ly_do_trang_thai === "string" && d.ly_do_trang_thai) dau.append(nho("Lý do trạng thái (máy chủ): " + d.ly_do_trang_thai));
    if (typeof d.giai_thich === "string" && d.giai_thich) dau.append(nho(d.giai_thich));
    const nhanBan = v => `Bản số ${v.so ?? "?"} · ${h12(v.version_id)} · kết luận rev ${v.ket_luan_revision ?? "—"}${v.moi_nhat === true ? " (mới nhất)" : ""}`;
    if (ds.length > 1) {
      const s = el("select", {"aria-label": "Phiên bản hồ sơ"}, ds.map(v => el("option", {value: v.version_id, text: nhanBan(v)})));
      s.value = c.version_id;
      s.addEventListener("change", () => {  // đổi phiên bản = đổi view: vô hiệu đồng bộ nháp/continuation của phiên bản cũ
        if (s.value === c.version_id) return;
        versionChon = s.value; genView += 1; genForm += 1; genTep += 1; dto = null; nhap = null; lyDoDuyet = ""; tepChon = null; khaNang = {}; tinhTrang = "DANG"; ve_(); napLai();
      });
      dau.append(el("label", {class: "m4-dp-o"}, el("span", {text: "Phiên bản hồ sơ"}), s));
    }
    if (ds.length) dau.append(el("h4", {text: "Lịch sử phiên bản hồ sơ đợt"}), bang(["Bản số", "Phiên bản", "Trạng thái", "Kết luận (rev)", "Quyết định", "Seal", "Mới nhất", "Đang xem"],
      ds.map(v => [chu(v.so), h12(v.version_id), chu(v.trang_thai), v.ket_luan_revision === null || v.ket_luan_revision === undefined ? "chưa có" : String(v.ket_luan_revision),
        v.quyet_dinh_id ? h12(v.quyet_dinh_id) : "chưa có", v.seal_id ? h12(v.seal_id) : "chưa có", v.moi_nhat === true ? "mới nhất" : "",
        v.version_id === c.version_id ? "đang xem" : ""])));
    const q = d.quyen;
    dau.append(el("div", {class: "m4-hang"}, ...[["Xem", q.xem], ["Lưu kết luận", q.ket_luan], ["DUYỆT", q.duyet], ["Bổ sung PDF", q.tai_pdf]]
      .map(([t, v]) => pill(`${t}: ${v ? "có" : "không"}`, v ? "m4-du" : "m4-xam"))), nho("Quyền do máy chủ trả theo vai hiện hành; REVIEW/SOẠN không tự có quyền DUYỆT."));
    out.push(dau);
    const cc = el("section", {class: "m4-card"}, el("h3", {text: "Căn cứ của phiên bản"}));
    // dữ kiện căn cứ CÓ KIỂU (định danh gắn nhãn đúng loại — digest phiên bản/basis review/H kết quả/SHA đồ thị, KHÔNG gọi là hash tệp gốc)
    cc.append(d.can_cu.length ? bang(["Loại căn cứ", "Trạng thái", "Định danh (có kiểu)", "Lý do (máy chủ)"], d.can_cu.map(x => [
      (NHAN_CAN_CU[x.loai] ? NHAN_CAN_CU[x.loai] + " (" + x.loai + ")" : chu(x.loai || x.vai)), chu(x.trang_thai), dinhDanhCanCu(x), chu(x.ly_do)]))
      : nho("Máy chủ không trả căn cứ nào.", "m4-loi-chu"));
    cc.append(el("h3", {text: "Tệp căn cứ đã chụp khi nộp (metadata tệp thật)"}));
    if (d.tep_can_cu === undefined) cc.append(nho("Máy chủ chưa cung cấp metadata tệp căn cứ cho phiên bản này — không suy ra là không có tệp.", "m4-loi-chu"));
    else if (!d.tep_can_cu.length) cc.append(nho("Phiên bản không có tham chiếu tệp nào" + (d.tep_can_cu_ly_do ? " — " + d.tep_can_cu_ly_do : "") + "."));
    else cc.append(bang(["Vai", "Mục", "Tên tệp", "SHA-256 tệp", "Byte", "Trạng thái", "Lý do (máy chủ)"], d.tep_can_cu.map(t => [chu(t.vai), chu(t.nhan),
      thieuNeu(t.ten), (t.raw_sha256 ? h12(t.raw_sha256) : "(thiếu)") + (t.raw_sha256_da_chup && t.raw_sha256_da_chup !== t.raw_sha256 ? " · đã chụp " + h12(t.raw_sha256_da_chup) : ""),
      thieuNeu(t.byte_length), chu(t.trang_thai), t.ly_do || (t.trang_thai === "CO" ? "" : "(máy chủ không ghi lý do)")])));
    cc.append(el("h3", {text: "Kết quả Review (L1/L2/L3) — công bố tách khỏi CO/CU"}));
    cc.append(d.review_refs.length ? bang(["Cấp", "Lần chạy", "Căn cứ (CO/CU)", "Trạng thái lần chạy", "H kết quả", "Công bố", "Lý do (máy chủ)"], d.review_refs.map(x => [
      x.cap || x.loai || "", x.run_id || x.id ? h12(x.run_id || x.id) : "(chưa có)", chu(x.trang_thai), chu(x.trang_thai_run), h12(x.ket_qua_sha256 || x.sha256),
      x.cong_bo === true ? "Đã công bố" : x.cong_bo === false ? "Chưa công bố" : "Chưa có kết quả phù hợp / chưa xác định", chu(x.ly_do)]))
      : nho("Chưa có kết quả Review gắn phiên bản này.", "m4-loi-chu"));
    cc.append(el("h3", {text: "Phạm vi kiểm (coverage)"}));
    const cv = Array.isArray(d.coverage) ? d.coverage.map(x => [x.ma || "", x.trang_thai || "", x.ly_do || ""])
      : Object.entries(d.coverage).map(([k, v]) => [k, v && typeof v === "object" ? v.trang_thai || "" : chu(v), v && typeof v === "object" ? v.ly_do || "" : ""]);
    cc.append(cv.length ? bang(["Mã", "Trạng thái kiểm", "Lý do"], cv) : nho("Coverage rỗng.", "m4-loi-chu"));
    out.push(cc);

    const tatKL = lyDoTat("KET_LUAN"), choSua = !tatKL || /chưa rõ|Đang gửi/.test(tatKL);  // đang chờ/chưa rõ: vẫn cho sửa nháp (nháp Y), chỉ chặn gửi
    const kl = el("section", {class: "m4-card m4-dp-kl"}, el("h3", {text: "Kết luận nghiệm thu & thanh toán"}),
      nho("NT (nghiệm thu chấp nhận theo khối lượng/đơn vị nguồn) và TT (số xin thanh toán) độc lập — không tự suy TT = NT. Tạm ứng/thu hồi/giữ lại nhập riêng. "
        + "Để trống = THIẾU (gửi null), khác số 0. Số nhập dạng chuỗi thập phân 1234567.50 — không làm tròn."));
    if (d.ket_luan) kl.append(nho(`Kết luận đã lưu: ${h12(d.ket_luan.id)} · revision ${d.ket_luan.revision}${nhapKhacDaLuu() ? " · nháp đang khác bản đã lưu" : ""}`));
    const form = el("div", {class: "m4-form"});
    for (const [t, nhan] of TIEN) form.append(oTien(t, nhan, !choSua));
    const tt = oNhap("Tiền tệ", nhap.tien_te, v => { nhap.tien_te = v; }); tt.disabled = !choSua;
    form.append(el("label", {}, el("span", {text: "Tiền tệ"}), tt));
    kl.append(form);
    kl.append(el("h4", {text: "Khối lượng nghiệm thu chấp nhận theo dòng (NT)"}));
    // "Đề nghị nguồn" = ĐÚNG de_xuat.kl_kn của máy chủ (null/vắng = "(thiếu)", "0" vẫn "0"); KHÔNG lấy KL hợp đồng/lũy kế/chấp nhận thay
    kl.append(d.dong_nt.length ? bang(["Dòng", "Hạng mục", "ĐVT", "Đề nghị nguồn", "KL lũy kế nguồn", "KL hợp đồng", "Nguồn", "Lũy kế đã duyệt trước", "KL chấp nhận"], d.dong_nt.map(r => {
      const i = oNhap("KL chấp nhận " + r.row_id, chu(nhap.dong[r.row_id]), v => { nhap.dong[r.row_id] = v; }); i.disabled = !choSua; i.inputMode = "decimal";
      const de = laDoiTuong(r.de_xuat) ? r.de_xuat : {}, tr = r.truoc_da_duyet;
      const truoc = laDoiTuong(tr) ? (tr.trang_thai === "CO" ? thieuNeu(tr.khoi_luong_chap_nhan) : "(chưa đủ — " + chu(tr.trang_thai) + ")") : "(chưa có nguồn)";
      return [h12(r.row_id), [r.ma_hm, r.ten].filter(Boolean).join(" · "), r.dvt || r.don_vi || "", thieuNeu(de.kl_kn), thieuNeu(de.kl_lk), thieuNeu(de.kl_hd),
        r.nguon || "", truoc, i];
    })) : nho("Máy chủ không trả dòng NT nào cho phiên bản này."));
    kl.append(el("h4", {text: "Phát hiện & giải trình của reviewer"}));
    kl.append(d.phat_hien.length ? bang(["Mã", "Mức", "Tiêu đề", "Chi tiết", "Giải trình đã lưu", "Giải trình"], d.phat_hien.map(p => {
      const i = oNhap("Giải trình phát hiện " + p.finding_id, chu(nhap.ph[p.finding_id]), v => { nhap.ph[p.finding_id] = v; }, "area"); i.disabled = !choSua; i.rows = 2;
      const ct = [chuGon(p.detail), p.item ? "Hạng mục: " + chuGon(p.item) : "", p.tai_lieu ? "Tài liệu: " + chuGon(p.tai_lieu) : "",
        p.amount !== null && p.amount !== undefined ? "Số tiền: " + chuGon(p.amount) : ""].filter(Boolean).join(" · ");
      return [(p.nguon ? p.nguon + " · " : "") + (p.code || p.ma || h12(p.finding_id)), p.level || p.muc || "(chưa rõ mức — không coi là đạt)",
        p.title || p.noi_dung || "(máy chủ không ghi tiêu đề)", ct || "—",
        laDoiTuong(p.xu_ly) ? "Đã ghi giải trình: " + p.xu_ly.ly_do : "Chưa có giải trình", i];
    })) : nho("Không có phát hiện."));
    const ld = oNhap("Lý do kết luận", nhap.ly_do, v => { nhap.ly_do = v; }, "area"); ld.disabled = !choSua; ld.rows = 2;
    kl.append(el("label", {class: "m4-dp-o"}, el("span", {text: "Lý do / ghi chú kết luận"}), ld));
    kl.append(el("div", {class: "m4-hang"}, nut(`Lưu kết luận (revision ${c.revision})`, luuKetLuan, "m4-chinh", !!tatKL, tatKL), tatKL ? nho(tatKL) : null));
    out.push(kl);

    const dy = el("section", {class: "m4-card m4-dp-duyet"}, el("h3", {text: "Duyệt hồ sơ đợt"}));
    if (d.quyet_dinh) {
      const qd = d.quyet_dinh;
      dy.append(el("div", {class: "m4-hang"}, pill("Đã duyệt", "m4-du"), el("span", {text: `Quyết định ${h12(qd.id)} · ${qd.actor || qd.nguoi || "—"} · ${qd.luc ? K.date(qd.luc) : "—"}${qd.ly_do ? " · " + qd.ly_do : ""}`})));
    }
    if (q.duyet !== true) dy.append(nho("Vai này không có quyền DUYỆT riêng — chỉ xem/kết luận; nút duyệt không hiện.", "m4-loi-chu"));
    else if (!d.quyet_dinh) {
      const tatD = lyDoTat("CHAP_THUAN"), l = oNhap("Lý do duyệt", lyDoDuyet, v => { lyDoDuyet = v; }, "area"); l.rows = 2;
      dy.append(el("label", {class: "m4-dp-o"}, el("span", {text: "Lý do duyệt"}), l),
        el("div", {class: "m4-hang"}, nut(`Duyệt hồ sơ đợt (kết luận ${d.ket_luan ? h12(d.ket_luan.id) : "—"})`, duyet, "m4-chinh", !!tatD, tatD), tatD ? nho(tatD) : null),
        nho("Duyệt được cả khi chưa có PDF: khi đó trạng thái là Chờ PDF, chưa chuyển kế toán và chưa đủ điều kiện Request."));
    }
    out.push(dy);

    const pd = el("section", {class: "m4-card m4-dp-pdf"}, el("h3", {text: "PDF hồ sơ thanh toán đợt đã duyệt"}),
      nho("Đây là PDF hồ sơ đợt — không phải PDF hợp đồng hay báo cáo Review. Máy chủ kiểm bytes thật và lưu bất biến; tên/loại tệp của trình duyệt không chứng minh PDF hợp lệ."));
    if (d.pdf) pd.append(el("div", {class: "m4-hang"}, pill(d.seal ? "Đã niêm phong" : "Đã lưu — chưa niêm phong", d.seal ? "m4-du" : "m4-thieu"),
      el("span", {text: `${d.pdf.name || "—"} · ${K.size(d.pdf.byte_length)} · H ${h12(d.pdf.sha256)}`}), nut("Tải PDF ↓", () => taiPdf(), "m4-lien-ket", thuHoi)));
    else pd.append(pill("Chưa có PDF hồ sơ đợt", "m4-thieu"));
    if (q.tai_pdf === true && !d.seal) {
      const tatP = lyDoTat("PDF"), inp = el("input", {type: "file", accept: ".pdf,application/pdf", "aria-label": "Tệp PDF hồ sơ đợt"});
      inp.addEventListener("change", () => { tepChon = (inp.files || [])[0] || null; genTep += 1; });  // tệp chọn giữ trong trạng thái (không mất khi vẽ lại)
      pd.append(el("div", {class: "m4-hang"}, inp, nut("Tải PDF hồ sơ đợt lên", guiPdf, "m4-chinh", !!tatP, tatP), tatP ? nho(tatP) : null));
      if (tepChon) pd.append(nho(`Đang chọn: ${tepChon.name} · ${K.size(tepChon.size)} (chọn lại tệp nếu muốn đổi)`));
    }
    out.push(pd);

    const ktCho = !!d.seal && d.kt.trang_thai === "CHO_XAC_NHAN", rqDu = !!d.seal && d.request.trang_thai === "DU_DIEU_KIEN_CHUA_NOI";
    // gốc KT của đợt (từ phiên bản đã seal trước) chỉ là LỊCH SỬ khi phiên bản đang xem chưa seal — không hiện như bàn giao của phiên bản này
    const gocKt = !ktCho && laUuid(d.kt.goc_id) ? ` Gốc KT của đợt ${h12(d.kt.goc_id)} là lịch sử từ phiên bản đã seal trước — không phải bàn giao của phiên bản đang xem.` : "";
    const lyKt = typeof d.kt.ly_do === "string" && d.kt.ly_do ? " Máy chủ: " + d.kt.ly_do + "." : "";
    const lyRq = typeof d.request.ly_do === "string" && d.request.ly_do ? " Máy chủ: " + d.request.ly_do + "." : "";
    const nh = el("section", {class: "m4-card m4-dp-nhanh"}, el("h3", {text: "Nhánh sau duyệt (hai nhánh tách riêng)"}));
    nh.append(bang(["Nhánh", "Trạng thái máy chủ", "Ghi chú"], [
      ["Kế toán", pill(ktCho ? "Chờ xác nhận" : "Chưa chuyển", ktCho ? "m4-du" : "m4-xam"), (ktCho ? `Hồ sơ KT ${h12(d.kt.pending_id)} — chờ kế toán xác nhận; chưa ghi nhận công nợ/AP.`
        : (d.quyet_dinh && !d.seal ? "Đã duyệt nhưng chưa có PDF hồ sơ đợt — chờ PDF." : "Chưa có seal duyệt + PDF.")) + gocKt + lyKt],
      ["Request thanh toán", pill(rqDu ? "Đủ căn cứ duyệt + PDF" : "Chờ PDF", rqDu ? "m4-thieu" : "m4-xam"), (rqDu ? "Phiên bản này có seal duyệt + PDF — chỉ là căn cứ nguồn cho Request nháp;"
        + " trạng thái, cấu hình, quyền tạo và đối soát xem tại mục Request nháp." + (d.phien_ban_hien_hanh === true ? ""
          : " Phiên bản đang xem là lịch sử — seal chỉ là căn cứ lịch sử, không mở quyền tạo Request.")
        : "Chưa đủ điều kiện (cần duyệt + PDF đã niêm phong).") + lyRq]]));
    out.push(nh);
    if (rqDuoc()) {  // M4-04B: vùng widget Request nháp (trạng thái thật do route riêng trả) — dòng d.request ở trên chỉ tóm tắt căn cứ seal/PDF, không phải trạng thái Request
      const k = rqKhoaCua();
      if (k !== rqKhoa) { rqGo(); rqKhoa = k; rqBox = el("div", {class: "m4-dp-request"}); if (rqTai === -1) rqTai = 0; }
      out.push(rqBox);
    }

    if (d.lich_su.length) out.push(el("section", {class: "m4-card"}, el("h3", {text: "Lịch sử"}), bang(["Sự kiện", "Người", "Lúc", "Ghi chú", "ID"],
      d.lich_su.map(x => [x.loai || x.hanh_dong || "", x.actor || x.nguoi || "", x.luc ? K.date(x.luc) : "", x.ly_do || x.ghi_chu || "", h12(x.id)]))));
    return out;
  }
  function veChuaNop() {  // biến thể CHƯA NỘP đã kiểm chặt: chỉ trạng thái + lý do máy chủ + lịch sử sự kiện; không form, không lệnh, không bằng chứng
    const d = dto, q = d.quyen, out = [];
    out.push(el("section", {class: "m4-card m4-dp-ban"}, el("div", {class: "m4-hang"}, el("strong", {text: "Chưa nộp hồ sơ đợt"}), pill(TT.CHUA_NOP[0], TT.CHUA_NOP[1])),
      nho(typeof d.ly_do_trang_thai === "string" && d.ly_do_trang_thai ? "Lý do trạng thái (máy chủ): " + d.ly_do_trang_thai : "Máy chủ không ghi lý do trạng thái.",
        "m4-loi-chu"),
      nho("Chưa có phiên bản hồ sơ, căn cứ, kết luận, quyết định, PDF, kế toán hay Request nào — không có lệnh nào được mở."),
      el("div", {class: "m4-hang"}, ...[["Xem", q.xem], ["Lưu kết luận", q.ket_luan], ["DUYỆT", q.duyet], ["Bổ sung PDF", q.tai_pdf]]
        .map(([t, v]) => pill(`${t}: ${v ? "có" : "không"}`, v ? "m4-du" : "m4-xam")))));
    if (d.lich_su.length) out.push(el("section", {class: "m4-card"}, el("h3", {text: "Lịch sử"}), bang(["Sự kiện", "Người", "Lúc", "Ghi chú", "ID"],
      d.lich_su.map(x => [x.loai || x.hanh_dong || "", x.actor || x.nguoi || "", x.luc ? K.date(x.luc) : "", x.ly_do || x.ghi_chu || "", h12(x.id)]))));
    return out;
  }
  function veYDinh() {  // ý định chưa rõ/đang bay của ĐÚNG ngữ cảnh đang mở (vai/PN/dự án/HĐ/đợt) — phiên bản khác chỉ hiện chữ
    const ds = [...yDinh.values()].filter(r => r.ctxKey === khoaCtx && r.trang !== "RO" && r.trang !== "MOI");
    return ds.map(r => {
      const ten = HANH[r.loai].ten, dung = r.version === verHienHanh();
      const moTa = r.file ? `${ten} (tệp gốc ${r.file.name})` : ten;
      if (r.bay) return el("div", {class: "m4-hang m4-dp-ydinh"}, nho(r.inc === inc ? `Đang ${moTa} — chờ kết quả, không gửi thêm.`
        : `Lệnh ${moTa} của lần mở trước còn đang chờ phản hồi — chưa gửi thêm; bấm ↻ Làm mới sau để xem kết quả.`));
      if (!dung) return el("div", {class: "m4-hang m4-dp-ydinh"}, nho(`Chưa rõ kết quả ${moTa} ở phiên bản ${h12(r.version)} — mở lại đúng phiên bản đó để gửi lại.`, "m4-loi-chu"));
      const tatLai = lyDoTatQuyen(r.loai);  // FIX01: cùng cổng quyền hiện hành với lệnh mới (không gồm trạng thái sau ghi)
      return el("div", {class: "m4-hang m4-dp-ydinh"}, el("span", {text: `Chưa rõ kết quả ${moTa} (khóa ${r.khoa.slice(0, 13)}…, đã gửi ${r.soLan} lần). `}),
        nut(r.file ? "Gửi lại tệp gốc y nguyên (cùng khóa)" : "Gửi lại y nguyên (cùng khóa)", () => guiLai(r), "m4-chinh", !!tatLai, tatLai),
        tatLai ? nho(tatLai + " — lệnh chưa rõ được giữ nguyên, chưa gửi lại.") : null);
    });
  }
  function ve_() {
    if (!vungSong()) return;
    const out = [el("div", {class: "m4-hang m4-dp-dau"}, el("h3", {text: "Duyệt hồ sơ đợt & PDF hồ sơ thanh toán"}),
      nut("↻ Làm mới", () => napLai(), "", !ctx || !ctx.dotId))];
    out.push(el("p", {class: "m4-dp-status m4-status" + (statusLoi ? " m4-loi-chu" : ""), role: "status", "aria-live": "polite", text: statusChu}));
    if (!ctx || !ctx.dotId) out.push(el("p", {class: "m4-trong", text: "Chọn một đợt (tab Đợt & checklist hoặc danh sách bên trái) rồi mở lại tab Duyệt & PDF."}));
    else if (tinhTrang === "CHUA_NOI") out.push(el("div", {class: "m4-notice m4-notice-loi", role: "alert"}, el("strong", {text: "Chưa nối backend duyệt/PDF. "}),
      `Máy chủ chưa có route/DTO ${SCHEMA} cho đợt này${loiGet ? " (" + loiGet + ")" : ""}. Không có duyệt, PDF, kế toán hay Request nào được ghi; nháp được giữ, các lệnh tạm tắt.`));
    else if (tinhTrang === "KHONG_QUYEN") out.push(el("div", {class: "m4-notice m4-notice-loi", role: "alert", text: `Không có quyền xem/thao tác hồ sơ duyệt của đợt này${loiGet ? ": " + loiGet : ""}. Bấm ↻ Làm mới để máy chủ kiểm lại quyền hiện hành.`}));
    else if (tinhTrang === "SAI_DTO") out.push(el("div", {class: "m4-notice m4-notice-loi", role: "alert", text: `Phản hồi hồ sơ duyệt không đúng hợp đồng ${SCHEMA} (${loiGet}) — không hiển thị và không cho thao tác.`}));
    else if (tinhTrang === "LOI" && !dto) out.push(el("div", {class: "m4-notice m4-notice-loi", text: loiGet || "Chưa đọc được hồ sơ duyệt."}));
    else if (!dto) out.push(el("p", {class: "m4-trong", text: "Đang tải hồ sơ duyệt…"}));
    if (dto && tinhTrang === "OK") out.push(...(dto.chua_nop === true ? veChuaNop() : veHoSo()));
    else if (dto && tinhTrang !== "OK") out.push(nho("Dữ liệu đang hiện có thể chưa mới nhất — bấm ↻ Làm mới."));
    out.push(...veYDinh());
    out.push(nho("Kế toán chỉ ở trạng thái Chờ xác nhận khi máy chủ đã niêm phong duyệt + PDF; bàn giao/Chờ xác nhận chưa phải đã ghi nhận công nợ/AP."
      + " Request nháp là nhánh độc lập với kế toán, xem tại mục Request nháp; tạo nháp không tự gửi duyệt."));
    box.replaceChildren(...out);
    cauRequest();
  }

  // ------------------------------------------------------------------ M4-04B cầu nối widget Request nháp
  // chỉ khi DTO canonical hợp lệ (tinhTrang OK, không thu hồi, quyền xem), đã nộp, seal thật gắn ĐÚNG phiên bản đang xem (hiện hành hoặc lịch sử chọn
  // tường minh — hiện hành chỉ là cổng TẠO do widget + máy chủ kiểm, không phải cổng đọc). CHUA_NOP/thiếu seal/seal lệch → không mount/GET/POST.
  function rqDuoc() {
    return tinhTrang === "OK" && !thuHoi && !!dto && dto.chua_nop !== true && !!dto.quyen && dto.quyen.xem === true && !!dto.seal
      && laUuid(dto.seal.id) && laUuid(dto.context.version_id) && dto.seal.version_id === dto.context.version_id && dto.trang_thai === "DA_SEAL";
  }
  const rqKhoaCua = () => JSON.stringify([khoaCtx, genView, dto.context.version_id, dto.seal.id, dto.phien_ban_hien_hanh === true]);
  function rqGo() {  // ĐỒNG BỘ: gỡ vùng + hủy widget (GET/POST đang bay của nó bị fence riêng chặn)
    rqKhoa = ""; rqBox = null;
    const R = window.kttM4RequestNhap;
    if (R && typeof R.huy === "function") R.huy();
  }
  function napRq() {  // tải lười đúng MỘT tài sản; vắng/lỗi → báo trong vùng, không stub, không thao tác Request
    if (window.kttM4RequestNhap) { rqTai = 2; return true; }
    if (rqTai !== 0) return false;
    rqTai = 1;
    window.kttM4RequestNhapSanSang = () => { rqTai = 2; if (vungSong()) cauRequest(); };
    const s = document.createElement("script");
    s.src = SRC_RQ;
    s.onerror = () => { rqTai = -1; s.remove(); if (vungSong()) cauRequest(); };
    document.head.append(s);
    return false;
  }
  function cauRequest() {
    if (!vungSong() || !rqDuoc() || !rqBox || rqKhoa !== rqKhoaCua() || !rqBox.isConnected) { if (rqBox || rqKhoa) rqGo(); return; }
    if (!napRq()) {
      if (rqTai === -1) rqBox.replaceChildren(nho("Chưa tải được thành phần Request nháp — không có thao tác Request nào; mở lại hồ sơ để thử lại.", "m4-loi-chu"));
      return;
    }
    window.kttM4RequestNhap.ve(rqBox, {khoa: rqKhoa, nguoi: ctx.nguoi || null, phapNhanId: ctx.phapNhanId || null, dto, chonTuongMinh: !!versionChon});
  }

  // ------------------------------------------------------------------ vòng đời (cổng đổi vai chung + cầu nối shell)
  function huy() {  // ĐỒNG BỘ: mọi GET/POST/blob/finally về muộn bị fence chặn; bản ghi ý định giữ theo phạm vi gốc (không gửi, không hiện ở ngữ cảnh khác)
    hoatDong = false; inc = null; box = null; ctx = null; khoaCtx = "";
    genView += 1; genGet += 1; genForm += 1; genTep += 1;
    dto = null; nhap = null; lyDoDuyet = ""; tepChon = null; khaNang = {}; thuHoi = false; tinhTrang = "CHUA"; loiGet = ""; versionChon = null; statusChu = ""; statusLoi = false;
    verView = undefined;
    rqGo();
  }
  K.dangKyVai(VAI, huy, () => { if (vungSong()) napLai(); });
  window.kttM4DuyetPdf = Object.freeze({
    ve(vung, c) {
      const k = khoaCua(c || {});
      if (!hoatDong || !inc || k !== khoaCtx) { huy(); inc = {}; khoaCtx = k; ctx = {...c}; }
      else ctx = {...ctx, ...c};
      box = vung; hoatDong = true;
      ve_();
      if (!dto && tinhTrang !== "CHUA_NOI" && tinhTrang !== "KHONG_QUYEN") napLai();
    },
    huy,
  });
  if (typeof window.kttM4DuyetPdfSanSang === "function") window.kttM4DuyetPdfSanSang();
})();
