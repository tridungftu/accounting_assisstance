"use strict";
// M4-01C — Cổng hồ sơ xây dựng (gói 1) trong shell hiện có: nguồn HĐ → trích/soát 37 mã → phòng dự án xác nhận → PL/BOQ → đợt/checklist → Nộp →
// reviewer đọc/tải. Chỉ gọi đúng route/DTO thật của giao_dien/m4.py + k2/xay_dung.py (B6). Danh tính, phạm vi, quyền, kết quả kiểm máy, hash,
// trạng thái căn cứ đều do máy chủ trả; trình duyệt chỉ gửi ID/revision/khóa/map/văn bản/lý do/bytes. Mọi chuỗi nguồn hiển thị bằng textContent.
// Đổi vai đi qua cổng chung của app.js (window.kttChung): xóa đồng bộ mọi module, hàng POST tuần tự, barrier GET, ý định mới nhất thắng.
// Fence = epoch vai/lựa chọn + actor + HĐ/đợt đang mở + thế hệ GET; kiểm sau MỌI await trước khi vẽ/toast/tải.
(() => {
  const K = window.kttChung;
  if (!K) return;  // shell chưa có seam (không chạy M4 rời khỏi app.js)
  const $ = id => document.getElementById(id);
  const node = K.node;
  const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || "";
  const goc = $("page-m4");
  if (!goc) return;

  const TT_THAM_SO = {CO_GIA_TRI: "Có giá trị", KHONG_AP_DUNG: "Không áp dụng", KHONG_QUY_DINH: "Không quy định", CHUA_CO: "Chưa có"};
  const TT_TRICH = {XONG: "Đã trích", KHONG_HO_TRO: "Chưa hỗ trợ", LOI: "Lỗi đọc"};
  const KHAI = {CHUA_KHAI: "Chưa khai báo", KHONG_CO: "Không có phụ lục", CO_CHUA_DU: "Có phụ lục — chưa cung cấp đủ", CO_DU: "Có phụ lục — đã cung cấp đủ"};
  const PL_TT = {DA_KY: "Đã ký", DU_THAO: "Dự thảo", DA_HUY: "Đã hủy"};
  const BOQ_TT = {DA_MAP: "Đọc/map đủ", CO_LOI: "Còn lỗi chặn"};
  const DOT_TT = {NHAP: "Nháp", DA_NOP: "Đã nộp"};
  const VAI_TL = {HOP_DONG: "Hợp đồng", PHU_LUC: "Phụ lục", BOQ: "BOQ", HO_SO_DOT: "Hồ sơ đợt"};
  const VAI_DA = {PHU_TRACH: "Phụ trách (soạn hồ sơ)", XEM: "Xem", REVIEW: "Review (chỉ đợt đã nộp)"};
  const DUOI_MEDIA = {docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", pdf: "application/pdf", png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg"};
  const TRUONG_BOQ = [["stt", "STT"], ["ma_rieng", "Mã hạng mục"], ["ten", "Tên công việc"], ["dvt", "Đơn vị tính"], ["kl", "Khối lượng"],
    ["don_gia", "Đơn giá"], ["thanh_tien", "Thành tiền"]];
  const LO_TRINH = [  // roadmap Review hồ sơ xây dựng (kế hoạch M4) — chỉ trạng thái thật, không nút
    ["Cổng hồ sơ: nguồn HĐ, trích/soát 37 mã, xác nhận phòng dự án, PL/BOQ, đợt/checklist, nộp, reviewer đọc/tải", "HIỆN CÓ", "M4-01"],
    ["Tổng quan Review, danh mục HĐ/PL/BOQ đầy đủ", "CHƯA NỐI", "M4-02"],
    ["Review L1 K1–K8 + L2 B1–B8/GT trên tệp đã tiếp nhận (tab Review) — có phạm vi kiểm từng mã", "HIỆN CÓ (hữu hạn)", "M4-02A"],
    ["Ghép tay hạng mục, chạy lại cùng tệp gốc, lịch sử lần chạy, báo cáo Excel L1/L2", "HIỆN CÓ (hữu hạn)", "M4-02A"],
    ["Review L3 C01–C09 trên chứng từ Word/Excel của đợt (tab Chứng từ L3): ma trận, phạm vi kiểm, sửa metadata/ghép tay theo revision, chạy lại, báo cáo Excel L3",
      "HIỆN CÓ (hữu hạn)", "M4-02B"],
    ["OCR / Local AI cho chứng từ PDF/ảnh; PL có kiểu GT/tham số/BO; lịch sử đợt trước đã duyệt", "CHƯA NỐI", "M4-02 (chưa có provider)"],
    ["Duyệt hồ sơ đợt (Anh/sếp) và PDF ký đúng revision", "GIAO DIỆN CÓ — BACKEND CHƯA NỐI", "M4-02C"],
    ["OCR / Local AI trích tham số", "CHƯA NỐI", "M4-02 (chưa có Local AI/OCR trong gói này)"],
    ["Báo cáo, tác vụ, cài đặt Review", "CHƯA NỐI", "M4-02"],
    ["Kế toán xác nhận nghiệm thu từ phong bì đã niêm phong (NT, cơ sở giá trị, tạm ứng/thu hồi/giữ lại, căn cứ VAT) — mục “Kế toán nghiệm thu”",
      "GIAO DIỆN CÓ — CHỜ COMPOSE BACKEND", "M4-03A"],
    ["Ghi công nợ/AP, thuế/tài khoản, chống ghi trùng", "CHƯA NỐI", "M4-03B"],
    ["Nháp Request thanh toán đợt sau PDF", "CHƯA NỐI", "M4-04"],
    ["Kiểm xuyên suốt, quyền, replay, khởi động lại", "CHƯA NỐI", "M4-05"],
    ["CAD bản vẽ, tài khoản nhà thầu ngoài", "HOÃN", "ngoài phạm vi đã chốt"]];

  // ------------------------------------------------------------------ trạng thái
  let ep = 0, genTong = 0, genHd = 0, genDot = 0;
  let m4 = null, hd = null, dot = null, hdChon = null, dotChon = null, tab = "nguon", suaMa = null, xemLoi = null;
  let boqXem = null, boqTep = "", mau = null, hoSoMoi = [], mucChon = "", chiThieu = false;
  // C2: bản ghi khóa theo (route, body gốc) = {khoa, chu}. `chu` = vé của lần gửi ĐANG bay (một incarnation). Hoàn tất/lỗi/finally của lần gửi chỉ dọn
  // đúng bản ghi + vé mình sở hữu — lần gửi cũ về trễ không xóa khóa/không nhả "đang gửi" của lần gửi mới (kể cả sau đổi vai A→B→A).
  const khoaMap = new Map(), oNhap = new Map();
  // C3 (C2UI-02): ý định tải lên CHƯA RÕ kết quả, theo ý định (tệp thật: dự án/vai/tên/kích thước/thời điểm sửa; tệp mẫu: dự án/vai/tên mẫu) →
  // {File GỐC (đúng bytes), vai, fence, form, continuation}. Gửi lại dùng ĐÚNG đối tượng này: cùng bytes/metadata/khóa, không lấy lại tệp mẫu.
  const taiChuaRo = new Map();
  const mauDang = new Map();  // C4-02: ý định tệp mẫu đang lấy/đang tải (giữ chỗ đồng bộ trước await đầu tiên)
  // C2: thế hệ form/lựa chọn — tăng khi người dùng sửa ô nhập, đổi tab, mở form tham số khác, đổi tệp/mẫu/sheet BOQ. Continuation của lệnh cũ không
  // đóng/vẽ đè form mới (lệnh đã gửi vẫn có thể commit hợp lệ ở máy chủ). genBoq: vé lựa chọn tệp/sheet BOQ — chỉ xem trước MỚI NHẤT được vẽ.
  let genForm = 0, genBoq = 0;
  // MASTER-REUSE-02: chọn master có sẵn (form Tạo) + gắn đối tác (tab Nguồn). Danh sách + expected_* chỉ thuộc vai/dự án/HĐ hiện hành; đổi dự án/
  // chế độ/vai/HĐ → hủy lựa chọn + token cũ (genMaster/genDoiTac tăng); phản hồi về trễ của thế hệ cũ không vẽ.
  let taoCheDo = "moi", taoDuAn = null, masterDs = null, masterChon = null, genMaster = 0, doiTacDs = null, doiTacChon = null, genDoiTac = 0;
  const TT_MASTER = {SOAN_THAO: "Soạn thảo", CHO_KY: "Chờ ký", DA_KY: "Đã ký", HIEU_LUC: "Hiệu lực"};
  const MAP_TT = {OK: "Mapping hiện hành rõ", KHONG_DOI_TAC: "Chưa có đối tác", MO_HO: "Nhiều mapping mở — HOLD", KHOA_DONG: "Mapping khóa/đóng — HOLD",
    THIEU: "Chưa có mapping mở cùng pháp nhân — HOLD"};
  const HOLD_MAP = {M4_MAPPING_MO_HO: "Nhiều mapping mở — chờ nguồn master làm rõ", M4_MAPPING_CHUA_HIEU_LUC: "Mapping chưa hiệu lực",
    M4_MAPPING_KHOA_DONG: "Mapping khóa/đóng"};
  const HOLD_TL = {MAPPING_KHONG_DOI_TAC: "Chưa có đối tác", MAPPING_MO_HO: "Đối tác có nhiều mapping mở — chờ nguồn master làm rõ",
    MAPPING_KHOA_DONG: "Mapping đối tác đang khóa/đóng", MAPPING_THIEU: "Đối tác chưa có mapping mở cùng pháp nhân",
    CAN_CU_CHUA_DONG_BO: "Căn cứ chưa khớp nguồn hiện hành", CAN_CU_CHUA_CO_NGUOI_XAC_NHAN: "Căn cứ ghi do nguồn đổi — chưa có người xác nhận trong phiên",
    LICH_SU_NOP_CHUA_CHUNG_MINH: "Có bản đã nộp trước khi bật căn cứ — chưa chứng minh căn cứ lúc nộp (HOLD khi dùng tài chính)"};
  const NGUON_CC = {TAO_HO_SO_M4: "Tạo hồ sơ M4", NHAN_MASTER_CO_SAN: "Nhận hợp đồng có sẵn", GAN_DOI_TAC: "Gắn đối tác", QUAN_SAT_NGUON_HOP_DONG: "Nguồn hợp đồng đổi",
    QUAN_SAT_NGUON_MAPPING: "Nguồn mapping đổi", BASELINE_BIET_TAI_NHAN: "Mốc lúc bật căn cứ", BASELINE_BIET_TAI_NOP: "Mốc lúc nộp"};
  // máy chủ chỉ trả "CSDL từ chối thao tác (mã)" → hướng dẫn bổ sung/correction theo authority thật, không hứa nút chưa có
  const HUONG_MASTER = {
    M4_MASTER_DA_DOI: "Hợp đồng nguồn/đối tác/mapping vừa đổi — đã tải lại; kiểm tra rồi chọn lại (nháp được giữ).",
    M4_MAPPING_DA_DOI: "Mapping đối tác vừa đổi ở nguồn master — đã bỏ lựa chọn cũ; tìm và chọn lại đối tác.",
    M4_MASTER_KHONG_THAY: "Không thấy hợp đồng xây dựng này trong dự án — tìm lại danh sách.",
    M4_MAPPING_KHONG_THAY: "Không thấy mapping đối tác đúng pháp nhân — tìm lại danh sách đối tác.",
    M4_MASTER_TRANG_THAI_KHONG_NHAN: "Trạng thái hợp đồng nguồn không nhận được — xử lý tại nguồn CRM/master.",
    M4_MAPPING_KHONG_HIEN_HANH: "Mapping đã đóng/khóa hoặc chưa hiệu lực — chờ nguồn master mở/hiệu lực mapping.",
    M4_MAPPING_MO_HO: "Đối tác có nhiều mapping mở cùng pháp nhân — chờ nguồn master làm rõ; M4 không tự chọn.",
    M4_DOI_TAC_KHONG_HOP_LE: "Đối tác không hoạt động hoặc khác pháp nhân — chọn đối tác khác hoặc sửa tại nguồn master.",
    M4_LY_DO_BAT_BUOC: "Nhập lý do gắn/sửa đối tác.",
    M4_MASTER_CAN_SUA_TAI_NGUON: "Hợp đồng do CRM/master quản lý hoặc đã khóa — chọn/sửa đối tác tại nguồn có quyền; M4 không sửa thay.",
    M4_MASTER_CAN_PHIEN_BAN_DIEU_CHINH: "Hồ sơ đã nộp — đổi đối tác cần căn cứ/quyết định phiên bản điều chỉnh từ nguồn có quyền. Lệnh điều chỉnh sau nộp CHƯA triển khai "
      + "trong gói này; lịch sử và master giữ nguyên.",
    M4_MASTER_CAN_CU_DOI: "Căn cứ master/đối tác đổi trong lúc nộp — đã tải lại hồ sơ; kiểm tra rồi nộp lại."};
  const actor =() => (m4 && m4.nguoi && m4.nguoi.dang_nhap) || null;
  const taoKhoa = () => "m4-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));
  function fence(them) {  // ngữ cảnh GỐC của thao tác: epoch + actor + HĐ/đợt đang mở (+ điều kiện riêng)
    const e = ep, a = actor(), h = hdChon, d = dotChon;
    return () => e === ep && a === actor() && h === hdChon && d === dotChon && (!them || them());
  }

  class LoiM4 extends Error {
    constructor(status, code, message) { super(message); this.status = status; this.code = code; }
  }
  async function goi(path, opts = {}) {
    let res;
    try { res = await fetch(path, {...opts, headers: {"X-KTT-Token": TOKEN, ...(opts.headers || {})}, cache: "no-store", credentials: "same-origin"}); }
    catch (_) { throw new LoiM4(0, "MAT_KET_NOI", "Mất kết nối với ứng dụng trên máy — chưa xác định máy chủ đã ghi hay chưa. Nháp và khóa thao tác được giữ; bấm Gửi lại y nguyên để nhận đúng kết quả cũ."); }
    if (!res.ok) {
      const r = await res.json().catch(() => ({}));
      throw new LoiM4(res.status, r.error || "HTTP_" + res.status, r.message || `Không hoàn tất yêu cầu (${res.status}).`);
    }
    return res;
  }
  const KET_QUA_CHUA_RO = "Máy chủ đã trả lời nhưng nội dung phản hồi đọc không trọn — chưa rõ lệnh đã ghi hay chưa. Nháp và khóa được giữ; bấm Gửi lại y nguyên để nhận đúng kết quả.";
  async function docJson(res) {  // C2: HTTP 2xx nhưng body/JSON đứt → kết quả CHƯA RÕ (không coi là thất bại chắc chắn, không đổi khóa)
    try { return await res.json(); } catch (_) { throw new LoiM4(0, "KET_QUA_CHUA_RO", KET_QUA_CHUA_RO); }
  }
  const postJson = async (ten, body) => docJson(await goi("/api/m4/" + ten, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)}));

  // ------------------------------------------------------------------ tiện ích hiển thị
  function trangThai(msg, loi = false) { const s = $("m4-status"); if (s) { s.textContent = msg || ""; s.className = "m4-status" + (loi ? " m4-loi-chu" : ""); } }
  const pill = (text, cls) => node("span", text, "m4-pill " + (cls || "m4-xam"));
  const h12 = h => h ? h.slice(0, 12) + "…" : "—";
  const ngay = v => v ? K.date(v) : "—";
  function bang(headers, rows, cls) {
    const wrap = node("div", undefined, "m4-bang" + (cls ? " " + cls : "")), t = node("table"), head = node("thead"), tr = node("tr"), body = node("tbody");
    headers.forEach(x => tr.append(node("th", x))); head.append(tr); t.append(head);
    for (const r of rows) {
      const row = node("tr");
      for (const c of r) { const td = node("td"); if (c instanceof Node) td.append(c); else td.textContent = c === null || c === undefined ? "" : String(c); row.append(td); }
      body.append(row);
    }
    t.append(body); wrap.append(t); return wrap;
  }
  function nut(text, fn, cls, tat) {
    const b = node("button", text, cls || ""); b.type = "button"; b.disabled = !!tat;
    b.addEventListener("click", () => { if (!b.disabled) fn(b); }); return b;
  }
  function o(id, el) {  // ô nhập có giữ nháp khi tải lại vì revision cũ; mọi sửa của người dùng tăng thế hệ form (C2)
    el.id = "m4f-" + id; oNhap.set(el.id, el);
    el.addEventListener("input", () => { genForm += 1; });
    el.addEventListener("change", () => { genForm += 1; });
    return el;
  }
  const formCon = () => { const g = genForm; return () => g === genForm; };
  // sau lệnh thành công: form vẫn là form đã gửi → làm mới bình thường; người dùng đã sửa/đổi form trong lúc chờ → KHÔNG vẽ lại (giữ nháp mới)
  async function sauLenh(fc, msg) {
    if (fc()) { await napLai(false); return true; }
    trangThai((msg || "Lệnh đã hoàn tất") + " — form đã đổi trong lúc chờ nên chưa làm mới; nháp hiện tại được giữ, bấm ↻ Làm mới khi xong.");
    return false;
  }
  function truong(label, el) { const l = node("label"); l.htmlFor = el.id; l.append(node("span", label), el); return l; }
  function nhapText(id, value, type = "text") { const i = o(id, node("input")); i.type = type; i.value = value ?? ""; i.autocomplete = "off"; return i; }
  function chon(id, options, value, dau) {
    const s = o(id, node("select"));
    if (dau !== undefined) { const op = node("option", dau); op.value = ""; s.append(op); }
    for (const [v, t] of options) { const op = node("option", t); op.value = v; op.selected = v === value; s.append(op); }
    return s;
  }
  function giuNhap() { const m = new Map(); for (const [id, el] of oNhap) m.set(id, el.type === "checkbox" ? {checked: el.checked} : {value: el.value}); return m; }
  function traNhap(m) {
    if (!m) return;
    for (const [id, v] of m) { const el = $(id); if (!el || el.type === "file") continue; if ("checked" in v) el.checked = v.checked; else el.value = v.value; }
  }
  const rong = v => { const t = typeof v === "string" ? v.trim() : v; return t === "" || t === undefined ? null : t; };
  const cotChu = i => { let s = ""; i += 1; while (i > 0) { const m = (i - 1) % 26; s = String.fromCharCode(65 + m) + s; i = Math.floor((i - 1) / 26); } return s; };
  const soan = () => !!(hd && hd.ho_so && hd.ho_so.soan);
  const ghiNguon = () => !!(m4 && m4.ghi_nguon && m4.ghi_nguon.san_sang);

  // ------------------------------------------------------------------ thao tác có khóa (giữ khóa + body gốc đến khi có kết quả thật)
  function nhanBanGhi(k) {  // bản ghi khóa hiện hành của (route, body); đang có lần gửi bay → null (bấm lặp không gửi thêm)
    let rec = khoaMap.get(k);
    if (rec && rec.chu) return null;
    if (!rec) { rec = {khoa: taoKhoa(), chu: null}; khoaMap.set(k, rec); }
    const ve = {}; rec.chu = ve;
    return {rec, ve};
  }
  function traBanGhi(k, rec, ve, xong) {  // chỉ dọn đúng bản ghi + vé của CHÍNH lần gửi này
    if (rec.chu === ve) rec.chu = null;
    if (xong && khoaMap.get(k) === rec) khoaMap.delete(k);  // có kết quả thật → bỏ khóa; lỗi/chưa rõ → giữ khóa cho gửi lại y nguyên
  }
  async function gui(path, body, ok, f, opt = {}) {
    const k = JSON.stringify([path, body]), so = nhanBanGhi(k);
    if (!so) return null;
    const {rec, ve} = so, full = {...body, khoa: rec.khoa};
    veGuiLai(null);
    trangThai("Đang gửi…");
    let xong = false;
    try {
      const r = await postJson(path, full);
      xong = true;
      if (!f()) return null;  // vai/lựa chọn đã đổi: không gắn kết quả cũ vào màn hình mới
      K.toast(ok + (r && r.lap_lai ? " (biên nhận cũ của cùng yêu cầu — không ghi thêm)" : ""));
      trangThai(ok + (r && r.lap_lai ? " — kết quả cũ của cùng khóa/yêu cầu." : ""));
      return r;
    } catch (e) {
      if (!f()) return null;
      xuLyLoi(e, {path, body, ok, f, khi409: opt.khi409});
      return null;
    } finally { traBanGhi(k, rec, ve, xong); }
  }
  function xuLyLoi(e, lai) {
    const msg = ((e && e.message) || String(e)) + (e && HUONG_MASTER[e.code] ? " " + HUONG_MASTER[e.code] : "");
    K.toast(msg, true); trangThai(msg, true);
    if (e && e.status === 409 && e.code === "M4_REVISION_CU") {
      trangThai(msg + " Đã tải lại dữ liệu hiện hành; nháp trên form được giữ — kiểm tra rồi gửi lại (revision mới).", true);
      napHd({giu: true});  // C3: nháp được chụp NGAY TRƯỚC khi vẽ lại (giá trị mới nhất), không phải lúc bắt đầu tải
    }
    if (e && e.status === 409 && e.code === "M4_MASTER_CAN_CU_DOI" && hdChon) napHd({giu: true});
    if (lai && lai.khi409 && e && e.status === 409) lai.khi409(e);  // MASTER-REUSE-02: lệnh tự bỏ token cũ + tải lại danh sách của chính nó
    if (lai && e && (e.status === 0 || e.status >= 500)) veGuiLai(lai);  // kết quả chưa rõ: gửi lại ĐÚNG body + khóa gốc
  }
  function veGuiLai(lai) {
    const box = $("m4-gui-lai"); if (!box) return;
    delete box.dataset.tep;
    if (!lai) { box.replaceChildren(); return; }
    box.replaceChildren(node("span", "Chưa rõ kết quả lần gửi trước. "), nut("Gửi lại y nguyên (cùng khóa)", async () => {
      if (!lai.f()) { veGuiLai(null); trangThai("Lệnh chưa rõ kết quả thuộc hồ sơ/đợt/vai cũ — không gửi lại.", true); return; }  // C4: cổng trước request
      const r = await gui(lai.path, lai.body, lai.ok, lai.f, lai);
      if (r && lai.f()) await napLai(false);
    }, "m4-chinh"));
  }
  async function napLai(giu) { await m4Nap(giu ? {giu: true} : {}); }

  // ------------------------------------------------------------------ tải về (bytes nguồn đã xác thực, chỉ khi fence còn đúng)
  async function taiTep(tepId, ten) {
    const f = fence();
    try {
      const blob = await (await goi("/api/m4/tep/" + encodeURIComponent(tepId))).blob();
      if (!f()) return;  // bytes về trễ của vai/lựa chọn cũ: không click
      if (!blob.size) { trangThai("Tệp tải về rỗng — không lưu.", true); return; }
      const url = URL.createObjectURL(blob), a = node("a"); a.href = url; a.download = ten || "tep"; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      trangThai(`Đã tải ${ten} (${blob.size} byte).`);
    } catch (e) { if (f()) xuLyLoi(e); }
  }

  // ------------------------------------------------------------------ tải lên (bytes File nguyên văn; hash/metadata do máy chủ tính)
  // C4 (C4-01): đích/metadata/khóa của tải lên lấy từ Ý ĐỊNH (dự án gốc chụp lúc tạo), KHÔNG dựng lại từ hồ sơ đang chọn. Kiểm ý định còn hợp lệ
  // (vai/HĐ/đợt/epoch gốc) NGAY TRƯỚC POST — không chỉ chặn hiệu ứng sau phản hồi.
  async function taiLen(y, khiChuaRo) {
    const file = y.file, vai = y.vai, f = y.f;
    if (!file) { trangThai("Chọn tệp trước.", true); return null; }
    if (!y.du_an_id || !f()) { boYDinh(y, "Ý định tải tệp thuộc hồ sơ/đợt/vai cũ — không gửi."); return null; }
    if (!file.size) { trangThai("Tệp rỗng (0 byte) — không gửi.", true); return null; }
    const toiDa = m4 && m4.tai_len_toi_da_byte;
    if (toiDa && file.size > toiDa) { trangThai(`Tệp ${K.size(file.size)} vượt giới hạn ${K.size(toiDa)} — không gửi.`, true); return null; }
    const duoi = (file.name.split(".").pop() || "").toLowerCase(), media = file.type || DUOI_MEDIA[duoi] || "";
    const k = JSON.stringify(["tep", y.du_an_id, vai, file.name, media, file.size, file.lastModified]);
    const thu = {du_an_id: y.du_an_id, vai_tro: vai, ten: file.name, media_type: media, khoa: "m4-" + "x".repeat(36)};
    if (encodeURIComponent(JSON.stringify(thu)).length > 4000) { trangThai("Tên tệp quá dài — đổi tên ngắn hơn rồi tải lại.", true); return null; }
    const so = nhanBanGhi(k);
    if (!so) return null;
    const {rec, ve} = so;
    const enc = encodeURIComponent(JSON.stringify({...thu, khoa: rec.khoa}));
    if (y.enc && y.enc !== enc) { traBanGhi(k, rec, ve, false); boYDinh(y, "Ý định tải tệp không còn khóa/metadata gốc — không gửi."); return null; }
    y.enc = enc;  // header gốc của ý định: mọi lần gửi lại phải trùng y nguyên
    trangThai(`Đang tải lên ${file.name}…`);
    let xong = false;
    try {
      if (!f()) { boYDinh(y, "Ý định tải tệp thuộc hồ sơ/đợt/vai cũ — không gửi."); return null; }  // cổng cuối, ngay trước POST
      const r = await docJson(await goi("/api/m4/tep", {method: "POST", headers: {"X-M4-Info": enc}, body: file}));
      xong = true;
      if (!f()) return null;
      const msg = `${r.hang_moi ? "Đã nhận tệp mới" : "Tệp cùng bytes đã có — dùng lại"} ${file.name} · ${K.size(r.byte_length)} · H ${h12(r.sha256)}${r.lap_lai ? " (biên nhận cũ)" : ""}`;
      K.toast(msg); trangThai(msg);
      return r;
    } catch (e) {
      if (!f()) return null;
      xuLyLoi(e);  // nháp/tệp đã chọn giữ nguyên; chọn lại cùng tệp sẽ dùng lại cùng khóa (bản ghi giữ khi chưa rõ kết quả)
      if (khiChuaRo && e && (e.status === 0 || e.status >= 500)) khiChuaRo();  // mất kết nối / 5xx / JSON đứt sau 2xx: giữ ý định để gửi lại y nguyên
      return null;
    } finally { traBanGhi(k, rec, ve, xong); }
  }
  // C3: một lần tải lên = một ý định y {intent, file, vai, f, fc, sau, nhan}. Kết quả rõ → continuation (gắn vào danh sách/làm mới) chạy ĐÚNG MỘT LẦN.
  // C4: tạo ý định tải lên ĐỒNG BỘ trong handler, chụp ngữ cảnh gốc (epoch/vai/HĐ/đợt qua fence, dự án gốc) — không đổi theo hồ sơ chọn sau này
  function taoYDinh(loai, ten, vai, file, sau, nhan) {
    if (!hd) return null;
    const du_an_id = hd.ho_so.du_an_id;
    return {intent: JSON.stringify([loai, ep, hdChon, dotChon, du_an_id, vai, ten]), file, vai, du_an_id, f: fence(), fc: formCon(), sau, nhan};
  }
  function boYDinh(y, msg) {  // ý định hết hiệu lực (đổi vai/HĐ/đợt): bỏ giữ + gỡ nút gửi lại của nó; không gửi gì
    if (taiChuaRo.get(y.intent) === y) taiChuaRo.delete(y.intent);
    y.het = true; xoaGuiLaiTep(y.intent);
    if (msg) trangThai(msg, true);
  }
  function xoaGuiLaiTep(intent) {  // gỡ nút gửi lại tệp toàn cục (của một ý định, hoặc mọi ý định khi intent không truyền)
    const box = $("m4-gui-lai"); if (!box || !box.dataset.tep) return;
    if (intent === undefined || box.dataset.tep === intent) { box.replaceChildren(); delete box.dataset.tep; }
  }
  async function guiTep(y) {
    if (y.het || !y.f()) { boYDinh(y, "Ý định tải tệp thuộc hồ sơ/đợt/vai cũ — không gửi."); return null; }  // cổng ở entrypoint
    const r = await taiLen(y, () => { if (y.f() && !y.het) { taiChuaRo.set(y.intent, y); veGuiLaiTep(y); } });
    if (!r) return null;  // bấm lặp khi còn bay (0 POST thêm), lỗi chắc chắn, chưa rõ, hoặc vai/lựa chọn đã đổi
    if (taiChuaRo.get(y.intent) === y) taiChuaRo.delete(y.intent);
    xoaGuiLaiTep(y.intent);
    if (!y.f() || y.daXong) return r;
    y.daXong = true;
    if (y.sau) y.sau(r, y.file.name);
    await sauLenh(y.fc, y.nhan || "Đã nhận tệp");
    return r;
  }
  function veGuiLaiTep(y) {
    const box = $("m4-gui-lai"); if (!box) return;
    box.dataset.tep = y.intent;
    box.replaceChildren(node("span", `Chưa rõ kết quả tải tệp ${y.file.name}. `), nut("Gửi lại tệp y nguyên (cùng khóa)", () => guiTep(y), "m4-chinh"));
  }
  async function layMau(ma) {  // bytes tệp mẫu DEMO cố định từ máy chủ → File → đi qua đúng POST /api/m4/tep như tệp thật
    const res = await goi("/api/m4/mau/" + encodeURIComponent(ma));
    const blob = await res.blob(), item = (mau || []).find(x => x.ma === ma);
    return new File([blob], ma, {type: (item && item.media_type) || blob.type || DUOI_MEDIA[ma.split(".").pop()] || ""});
  }
  async function napMau() {
    if (mau !== null || !m4 || !(m4.pham_vi || []).some(p => p.soan)) return;
    const e = ep, fs = formCon();
    try {
      const r = await (await goi("/api/m4/mau")).json();
      if (e !== ep) return;
      mau = r.mau || [];
      if (fs()) veGiu(veHd);  // C3: người dùng đã nhập sau khi GET bắt đầu → không dựng lại (danh sách mẫu hiện ở lần vẽ kế tiếp)
    } catch (_) { if (e === ep) mau = []; }
  }

  // ------------------------------------------------------------------ nạp dữ liệu (GET có barrier đổi vai + thế hệ)
  // C3 (C2UI-01): guard tới TÁC ĐỘNG DOM CUỐI. Mỗi chuỗi nạp chụp thế hệ form `fs` lúc GET đầu tiên bắt đầu và mang theo qua mọi await (tổng quan →
  // HĐ → đợt). Phản hồi về mà người dùng đã mở/nhập form sau lúc bắt đầu → KHÔNG vẽ lại (giữ nguyên DOM + nháp mới nhất), chỉ báo có dữ liệu mới.
  // `giu: true` (khôi phục sau revision cũ): vẽ lại với nháp MỚI NHẤT chụp ngay trước khi vẽ (không dùng snapshot lúc bắt đầu).
  // Hết quyền/không còn trong phạm vi (đổi vai, 403/404, HĐ biến khỏi danh sách) vẫn XÓA dữ liệu — không giữ nháp trái phạm vi.
  function veGiu(fn) { const g = giuNhap(); fn(); traNhap(g); }  // vẽ lại rồi đặt lại đúng giá trị đang có ngay trước khi vẽ
  function baoCoMoi() {
    trangThai("Dữ liệu mới đã về trong lúc bạn đang nhập — chưa vẽ lại để giữ nháp hiện tại; bấm ↻ Làm mới khi xong.");
  }
  async function m4Nap(opt = {}) {
    if (K.vaiDangChan("m4")) return;
    const e = ep, g = ++genTong, fs = opt.fs || formCon();
    try {
      const s = await (await goi("/api/m4")).json();
      if (e !== ep || g !== genTong) return;
      let xoa = false;
      if (actor() !== null && s.nguoi && s.nguoi.dang_nhap !== actor()) { ep += 1; boChon(); boMaster(); tatKeToan(); xoa = true; }  // máy chủ báo vai khác: bỏ lựa chọn cũ
      if (hdChon && !(s.hop_dong || []).some(h => h.id === hdChon)) { boChon(); xoa = true; }  // HĐ không còn trong phạm vi hiện hành
      m4 = s;
      if (!xoa && !opt.giu && !fs()) { baoCoMoi(); return; }
      if (opt.giu && !xoa) veGiu(veTong); else veTong();
      if (cheDo === "ke_toan") veKeToan();  // M4-03A: vùng KT theo vai hiện hành, không chờ HĐ
      napMau();
      if (hdChon) await napHd({...opt, fs: xoa ? formCon() : fs});
      else if (xoa) veHd();
    } catch (err) { if (e === ep && g === genTong) { trangThai(err.message, true); veKhongNap(err); } }
  }
  async function napHd(opt = {}) {
    if (!hdChon) { veHd(); return; }
    if (K.vaiDangChan("m4")) return;
    const e = ep, id = hdChon, g = ++genHd, fs = opt.fs || formCon(), conDung = () => e === ep && id === hdChon && g === genHd;
    try {
      const d = await (await goi("/api/m4/hop-dong/" + encodeURIComponent(id))).json();
      if (!conDung()) return;
      if (!opt.giu && !fs()) { baoCoMoi(); return; }  // C3: nháp mới sau lúc bắt đầu → không vẽ đè
      hd = d;
      if (opt.giu) veGiu(veHd); else veHd();
      if (dotChon) await napDot({...opt, fs});
    } catch (err) {
      if (!conDung()) return;
      if (err.status === 404 || err.status === 403) { boChon(); veTong(); veHd(); trangThai(err.message + " — hồ sơ không còn trong phạm vi hiện hành của vai này.", true); }
      else xuLyLoi(err);
    }
  }
  async function napDot(opt = {}) {
    if (!dotChon) return;
    if (K.vaiDangChan("m4")) return;
    const e = ep, id = dotChon, g = ++genDot, fs = opt.fs || formCon(), conDung = () => e === ep && id === dotChon && g === genDot;
    try {
      const d = await (await goi("/api/m4/dot/" + encodeURIComponent(id))).json();
      if (!conDung()) return;
      if (!opt.giu && !fs()) { baoCoMoi(); return; }
      dot = d;
      if (opt.giu) veGiu(veDot); else veDot();
    } catch (err) {
      if (!conDung()) return;
      if (err.status === 404 || err.status === 403) { dotChon = null; dot = null; veDot(); trangThai(err.message, true); }
      else xuLyLoi(err);
    }
  }
  // M4-02A FIX01 R7: vô hiệu vùng Review NGAY lúc ý định đổi tab/HĐ/đợt/vai (không chờ lần vẽ sau mới cập nhật ngữ cảnh)
  // M4-02B: cùng điểm tắt cho vùng Chứng từ L3 (mọi ý định đổi tab/HĐ/đợt/vai gọi tatReview) — teardown ĐỒNG BỘ trước lần vẽ sau
  function tatReview() {
    const R = window.kttM4Review; if (R && typeof R.tat === "function") R.tat();
    const C = window.kttM4ChungTu; if (C && typeof C.huy === "function") C.huy();
    tatDuyet();
  }
  // M4-02C: tab Duyệt & PDF là module riêng (m4_duyet_pdf.js); mọi điểm tắt module (tatReview) cũng tắt nó ĐỒNG BỘ, kể cả khi rời #m4
  const TAB_MODULE = new Set(["review", "chung_tu", "duyet"]);
  function tatDuyet() { const D = window.kttM4DuyetPdf; if (D && typeof D.huy === "function") D.huy(); }
  function boChon() {
    tatReview();
    hdChon = null; hd = null; dotChon = null; dot = null; boqXem = null; boqTep = ""; hoSoMoi = []; suaMa = null; xemLoi = null; oNhap.clear();
    huyYDinhTai(); genForm += 1; genBoq += 1;  // C3/C4: ý định tải lên/gửi lại gắn với HĐ/đợt cũ không mang sang lựa chọn mới
    boDoiTac();
  }
  function boMaster() { masterDs = null; masterChon = null; genMaster += 1; }  // ứng viên + expected_master thuộc dự án/chế độ/vai cũ
  function boDoiTac() { doiTacDs = null; doiTacChon = null; genDoiTac += 1; }  // đối tác + expected_mapping thuộc HĐ/revision cũ
  function huyYDinhTai() {  // C4-01: vô hiệu NGAY mọi ý định tải lên + gỡ nút gửi lại toàn cục (cả gửi lại lệnh) của ngữ cảnh cũ
    for (const y of taiChuaRo.values()) y.het = true;
    for (const y of mauDang.values()) y.het = true;
    taiChuaRo.clear(); mauDang.clear();
    veGuiLai(null);
  }
  function moHd(id, tabMoi) {
    if (hdChon !== id) { ep += 1; boChon(); hdChon = id; }  // đổi HĐ: kết quả/nháp của HĐ cũ không còn gắn vào màn hình
    if (tabMoi && TAB_MODULE.has(tab) && tabMoi !== tab) tatReview();
    if (tabMoi) tab = tabMoi;
    veTong(); veHd(); napHd();
  }
  function moDot(hdId, dotId) {
    if (hdChon !== hdId) { ep += 1; boChon(); hdChon = hdId; }
    if (dotChon !== dotId) { tatReview(); dotChon = dotId; dot = null; hoSoMoi = []; mucChon = ""; huyYDinhTai(); }
    if (TAB_MODULE.has(tab)) tatReview();
    tab = "dot"; veTong(); veHd(); napHd();
  }

  // ------------------------------------------------------------------ đổi vai (người tham gia seam chung)
  function m4Xoa() {  // đồng bộ, trước await đầu tiên của lần đổi vai (gọi từ app.js cho MỌI selector)
    ep += 1; m4 = null; mau = null; boChon(); tatKeToan(); khoaMap.clear();  // bản ghi cũ mồ côi: lần gửi cũ về trễ chỉ chạm bản ghi của nó (C2)
    boMaster(); taoDuAn = null; taoCheDo = "moi";
    genForm += 1; genBoq += 1;
    for (const id of ["m4-vai", "m4-pham-vi", "m4-ds-hd", "m4-ds-dot", "m4-tao", "m4-chi-tiet", "m4-thong-bao", "m4-gui-lai", "m4-kt"]) { const el = $(id); if (el) el.replaceChildren(); }
    const n = $("m4-nguoi"); if (n) n.textContent = "Đang tải…";
    trangThai("");
  }
  K.dangKyVai("m4", m4Xoa, () => m4Nap());

  // ------------------------------------------------------------------ khung trang
  function dungKhung() {
    const wrap = node("div", undefined, "m4-wrap"), head = node("div", undefined, "m4-head"), tieuDe = node("div");
    const h1 = node("h1", "Hồ sơ xây dựng"); h1.id = "m4-title";
    tieuDe.append(node("p", "HỒ SƠ XÂY DỰNG · CỔNG HỒ SƠ (M4-01) · DEMO", "m4-eyebrow"), h1,
      node("p", "Phòng dự án soạn hồ sơ hợp đồng và đợt thanh toán từ tệp nguồn thật; người review đọc đợt đã nộp. Chưa duyệt Review/PDF/kế toán/Request ở gói này.", "m4-sub"));
    const vai = node("div", undefined, "m4-role"), sel = node("select"), lbl = node("label", "Vai mô phỏng");
    sel.id = "m4-vai"; lbl.htmlFor = sel.id;
    const doi = nut("Dùng vai này", () => {
      const login = sel.value;  // chụp đồng bộ trước khi seam xóa
      if (!login) return;
      return K.doiVaiTuanTu(() => postJson("danh-tinh", {dang_nhap: login}), "m4-status", "m4");
    }, "m4-chinh");
    doi.id = "m4-doi-vai";
    const moi = nut("↻ Làm mới", () => m4Nap()); moi.id = "m4-lam-moi";
    vai.append(lbl, sel, doi, moi);
    head.append(tieuDe, vai);
    // M4-03A: điểm vào riêng "Kế toán nghiệm thu" — không cần chọn HĐ hay quyền portal (PHU_TRACH/XEM/REVIEW/DUYET)
    const cd = node("div", undefined, "m4-tabs m4-che-do"); cd.id = "m4-che-do"; cd.setAttribute("role", "tablist");
    const cdHs = nut("Hồ sơ hợp đồng & đợt", () => doiCheDo("ho_so")), cdKt = nut("Kế toán nghiệm thu", () => doiCheDo("ke_toan"));
    cdHs.id = "m4-cd-ho-so"; cdKt.id = "m4-cd-ke-toan";
    for (const b of [cdHs, cdKt]) b.setAttribute("role", "tab");
    cd.append(cdHs, cdKt);
    const tb = node("div"); tb.id = "m4-thong-bao";
    const st = node("p", "", "m4-status"); st.id = "m4-status"; st.setAttribute("role", "status"); st.setAttribute("aria-live", "polite");
    const gl = node("div", undefined, "m4-hang"); gl.id = "m4-gui-lai";
    const grid = node("div", undefined, "m4-grid"), trai = node("div"), phai = node("div"); grid.id = "m4-luoi";
    const c1 = node("section", undefined, "m4-card"), nguoi = node("p", "Đang tải…", "m4-nho"), pv = node("div"); nguoi.id = "m4-nguoi"; pv.id = "m4-pham-vi";
    c1.append(node("h2", "Vai & phạm vi dự án"), nguoi, pv);
    const c2 = node("section", undefined, "m4-card"), loc = node("input"), dsHd = node("ul", undefined, "m4-list"), tao = node("div");
    loc.id = "m4-loc"; loc.type = "search"; loc.placeholder = "Lọc số HĐ, tên, dự án…"; loc.setAttribute("aria-label", "Lọc hợp đồng");
    loc.addEventListener("input", () => veDsHd()); dsHd.id = "m4-ds-hd"; tao.id = "m4-tao";
    c2.append(node("h2", "Hồ sơ hợp đồng"), loc, dsHd, tao);
    const c3 = node("section", undefined, "m4-card"), dsDot = node("ul", undefined, "m4-list"); dsDot.id = "m4-ds-dot";
    c3.append(node("h2", "Đợt thanh toán"), dsDot);
    trai.append(c1, c2, c3);
    const ct = node("div"); ct.id = "m4-chi-tiet"; phai.append(ct);
    grid.append(trai, phai);
    const kt = node("div"); kt.id = "m4-kt"; kt.hidden = true;
    wrap.append(head, cd, tb, st, gl, grid, kt);
    goc.replaceChildren(wrap);
    veCheDoNut();
  }

  function veKhongNap(err) {
    const tb = $("m4-thong-bao"); if (!tb) return;
    tb.replaceChildren(node("div", `Chưa đọc được Cổng hồ sơ: ${err.message}`, "m4-notice m4-notice-loi"),
      node("p", "Mở lại bằng tệp MỞ BẢN DEMO.cmd (bước chuẩn bị tạo kho DEMO và vai M4). Nếu vẫn lỗi, giữ nguyên thư mục dữ liệu và báo lại thông báo trên.", "m4-nho"));
  }
  function veTong() {
    const tb = $("m4-thong-bao"); if (!tb) return;
    tb.replaceChildren();
    if (!m4) return;
    if (m4.cau_hinh === false) {
      tb.append(node("div", `Chưa kết nối kho DEMO PostgreSQL: ${m4.ly_do || ""}`, "m4-notice m4-notice-loi"),
        node("p", "Mở bằng tệp MỞ BẢN DEMO.cmd để chuẩn bị kho DEMO; không cần nhập DSN hay chạy SQL.", "m4-nho"));
      return;
    }
    tb.append(node("div", "Dữ liệu DEMO, danh tính mô phỏng (không phải đăng nhập thật). Trích tham số chạy theo quy tắc của lõi nguồn — chưa có Local AI/OCR; "
      + "danh mục 37 mã hiện đủ không có nghĩa giá trị đã được trích. Phòng dự án xác nhận tham số — không phải CFO/CRM duyệt.", "m4-notice"));
    if (m4.ghi_nguon && !m4.ghi_nguon.san_sang) {
      tb.append(node("div", `Đường ghi nguồn tin cậy của máy chủ chưa sẵn sàng (${m4.ghi_nguon.ly_do || "chưa cấu hình"}): tải tệp, trích, nhập BOQ và sửa tham số tạm khóa; `
        + "nháp được giữ. Mở lại bằng MỞ BẢN DEMO.cmd.", "m4-notice m4-notice-loi"));
    }
    const sel = $("m4-vai");
    sel.replaceChildren(...(m4.danh_tinh_demo || []).map(d => { const op = node("option", `${d.dang_nhap} (${d.vai_tro})`); op.value = d.dang_nhap; op.selected = !!m4.nguoi && d.dang_nhap === m4.nguoi.dang_nhap; return op; }));
    if (m4.nguoi && !(m4.danh_tinh_demo || []).some(d => d.dang_nhap === m4.nguoi.dang_nhap)) {
      const op = node("option", `${m4.nguoi.dang_nhap} (vai hiện tại — không thuộc danh sách M4)`); op.value = ""; op.selected = true; sel.prepend(op);
    }
    $("m4-nguoi").textContent = m4.nguoi ? `${m4.nguoi.dang_nhap} · ${m4.nguoi.vai_tro} · phiên của trình duyệt này` : "";
    const pv = m4.pham_vi || [];
    $("m4-pham-vi").replaceChildren(pv.length ? bang(["Pháp nhân", "Dự án", "Vai dự án", "Soạn"], pv.map(p => [p.phap_nhan, `${p.du_an_ma} · ${p.du_an}`, VAI_DA[p.vai] || p.vai,
      p.soan ? "Có" : "Không"])) : node("p", "Vai này không có phạm vi dự án M4 hiện hành (chưa được giao hoặc đã thu hồi).", "m4-trong"));
    veDsHd(); veDsDot(); veTao();
  }
  function veDsHd() {
    const ul = $("m4-ds-hd"); if (!ul || !m4 || m4.cau_hinh === false) return;
    const q = ($("m4-loc").value || "").trim().toLocaleLowerCase("vi-VN");
    const ds = (m4.hop_dong || []).filter(h => `${h.so_hop_dong} ${h.ten} ${h.du_an} ${h.phap_nhan}`.toLocaleLowerCase("vi-VN").includes(q));
    if (!ds.length) { ul.replaceChildren(node("li", (m4.hop_dong || []).length ? "Không có hồ sơ khớp bộ lọc." : "Chưa có hồ sơ hợp đồng trong phạm vi.", "m4-trong")); return; }
    ul.replaceChildren(...ds.map(h => {
      const li = node("li", undefined, h.id === hdChon ? "m4-chon" : "");
      li.append(node("strong", `${h.so_hop_dong}`), node("div", h.ten), node("small", `${h.phap_nhan} · ${h.du_an} · rev ${h.revision} · ${KHAI[h.trang_thai_pl] || h.trang_thai_pl}`
        + ` · ${h.co_tep ? "đã có tệp HĐ" : "chưa có tệp HĐ"} · ${h.so_dot} đợt${h.soan ? "" : " · chỉ xem"}`));
      li.tabIndex = 0; li.setAttribute("role", "button");
      li.addEventListener("click", () => moHd(h.id));
      li.addEventListener("keydown", ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); moHd(h.id); } });
      return li;
    }));
  }
  function veDsDot() {
    const ul = $("m4-ds-dot"); if (!ul || !m4 || m4.cau_hinh === false) return;
    const ds = m4.dot || [];
    if (!ds.length) { ul.replaceChildren(node("li", "Chưa có đợt trong phạm vi (người review chỉ thấy đợt đã nộp).", "m4-trong")); return; }
    ul.replaceChildren(...ds.map(d => {
      const li = node("li", undefined, d.id === dotChon ? "m4-chon" : "");
      li.append(node("strong", `${d.so_hop_dong} · Đợt ${d.so_dot}`), node("small", ` ${DOT_TT[d.trang_thai] || d.trang_thai} · NT ${d.ngay_nghiem_thu || "chưa có ngày"}${d.nop_luc ? " · nộp " + ngay(d.nop_luc) : ""}`));
      li.tabIndex = 0; li.setAttribute("role", "button");
      li.addEventListener("click", () => moDot(d.hop_dong_id, d.id));
      li.addEventListener("keydown", ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); moDot(d.hop_dong_id, d.id); } });
      return li;
    }));
  }
  function veTao() {
    const box = $("m4-tao"); if (!box || !m4) return;
    const duAn = [], thay = new Set();
    for (const p of m4.pham_vi || []) if (p.soan && !thay.has(p.du_an_id)) { thay.add(p.du_an_id); duAn.push([p.du_an_id, `${p.phap_nhan} · ${p.du_an_ma} · ${p.du_an}`]); }
    if (!duAn.length) { box.replaceChildren(); return; }
    if (!thay.has(taoDuAn)) { taoDuAn = duAn[0][0]; boMaster(); }  // dự án cũ không còn quyền soạn → bỏ ứng viên/token cũ
    const da = chon("tao-du-an", duAn, taoDuAn);
    da.addEventListener("change", () => { taoDuAn = da.value; boMaster(); if (taoCheDo === "co") veGiu(veTao); });  // đổi dự án: hủy ứng viên + expected_master
    const cd = node("div", undefined, "m4-tabs");
    for (const [k, t] of [["moi", "Tạo hồ sơ mới"], ["co", "Dùng hợp đồng đã có"]]) {
      const b = nut(t, () => { if (taoCheDo === k) return; genForm += 1; taoCheDo = k; boMaster(); veGiu(veTao); });
      b.id = "m4-tao-" + k; if (k === taoCheDo) b.className = "m4-chon"; b.setAttribute("aria-pressed", String(k === taoCheDo));
      cd.append(b);
    }
    if (taoCheDo === "co") { veNhanMaster(box, da, cd); return; }
    const so = nhapText("tao-so", ""), ten = nhapText("tao-ten", "");
    so.maxLength = 100; ten.maxLength = 300;
    const b = nut("Tạo hồ sơ HĐ", async () => {
      const body = {du_an_id: da.value, so_hop_dong: so.value.trim(), ten: ten.value.trim()};
      if (!body.so_hop_dong || !body.ten) { trangThai("Nhập số hợp đồng và tên gói thầu.", true); return; }
      const f = fence(), fc = formCon();
      const r = await gui("hop-dong/tao", body, "Đã tạo hồ sơ hợp đồng", f);
      if (r && f()) {
        if (!fc()) { trangThai("Đã tạo hồ sơ hợp đồng — form đã đổi trong lúc chờ nên chưa tự mở; chọn hồ sơ ở danh sách sau khi ↻ Làm mới."); return; }
        await m4Nap(); if (f() && fc()) moHd(r.hop_dong_id, "nguon");
      }
    }, "m4-chinh");
    const form = node("div", undefined, "m4-form");
    form.append(truong("Dự án", da), truong("Số hợp đồng", so), truong("Tên hợp đồng / gói thầu", ten), b);
    box.replaceChildren(node("h3", "Tạo hồ sơ HĐ mới (một lần cho mỗi hợp đồng — đợt sau dùng lại)"), cd, form);
  }
  // MASTER-REUSE-02: nhận hợp đồng xây dựng đã có (master/CRM) làm hồ sơ M4 nháp — không ghi master/CRM; trạng thái master tách khỏi readiness M4
  function veNhanMaster(box, da, cd) {
    const q = nhapText("tao-q", ""); q.maxLength = 100; q.placeholder = "Số HĐ hoặc mã nội bộ";
    const tim = nut("Tìm hợp đồng", () => taiMaster(q.value.trim()), "m4-chinh"); tim.id = "m4-tao-tim";
    const form = node("div", undefined, "m4-form"), kq = node("div"); kq.id = "m4-tao-ung-vien";
    form.append(truong("Dự án", da), truong("Tìm hợp đồng đã có", q), tim);
    box.replaceChildren(node("h3", "Dùng hợp đồng đã có (master/CRM) làm hồ sơ M4"), cd, form,
      node("p", "Chỉ hợp đồng xây dựng đúng pháp nhân/dự án, trạng thái Soạn thảo/Chờ ký/Đã ký/Hiệu lực. Nhận chỉ tạo hồ sơ M4 nháp; hợp đồng, đối tác và CRM giữ nguyên.", "m4-nho"), kq);
    veUngVien();
  }
  async function taiMaster(qv) {
    const e = ep, a = actor(), duAn = taoDuAn, g = ++genMaster;
    const con = () => e === ep && a === actor() && g === genMaster && duAn === taoDuAn && taoCheDo === "co";
    masterChon = null; masterDs = {dang: true, q: qv}; veUngVien();
    try {
      const r = await docJson(await goi(`/api/m4/master-hop-dong?du_an_id=${encodeURIComponent(duAn)}&q=${encodeURIComponent(qv)}&limit=25`));
      if (!con()) return;  // vai/dự án/chế độ/lần tìm đã đổi: không vẽ danh sách cũ
      masterDs = {q: qv, items: r.items || []}; veUngVien();
    } catch (err) {
      if (!con()) return;
      masterDs = {q: qv, loi: err.message}; veUngVien(); xuLyLoi(err);
    }
  }
  function veUngVien() {
    const kq = $("m4-tao-ung-vien"); if (!kq) return;
    kq.replaceChildren();
    if (!masterDs) return;
    if (masterDs.dang) { kq.append(node("p", "Đang tìm hợp đồng…", "m4-trong")); return; }
    if (masterDs.loi) { kq.append(node("p", "Chưa đọc được danh sách hợp đồng: " + masterDs.loi, "m4-trong m4-loi-chu")); return; }
    const ds = masterDs.items;
    if (!ds.length) { kq.append(node("p", "Không có hợp đồng xây dựng phù hợp trong dự án.", "m4-trong")); return; }
    const ul = node("ul", undefined, "m4-list"); ul.id = "m4-tao-ds-master";
    for (const it of ds) {
      const dangChon = !!masterChon && masterChon.hop_dong_id === it.hop_dong_id;
      const li = node("li", undefined, dangChon ? "m4-chon" : ""), hang = node("div", undefined, "m4-hang");
      hang.append(pill(`Master: ${TT_MASTER[it.trang_thai_master] || it.trang_thai_master} · ${it.module_chu === "M4" ? "M4 sở hữu" : "nguồn master/CRM"}`, "m4-xam"),
        it.da_co_ho_so_m4 ? pill(`Hồ sơ M4: đã có (rev ${it.revision_ho_so})`, "m4-du") : pill("Hồ sơ M4: chưa có", "m4-thieu"));
      if (it.da_co_ho_so_m4) {
        if ((m4.hop_dong || []).some(h => h.id === it.hop_dong_id)) hang.append(nut("Mở hồ sơ", () => moHd(it.hop_dong_id, "nguon"), "m4-lien-ket"));
      } else hang.append(nut(dangChon ? "Đang chọn" : "Chọn", () => { genForm += 1; masterChon = it; veUngVien(); }, "m4-lien-ket"));
      li.append(node("strong", it.so_hop_dong), node("small", ` ${it.ma_noi_bo ? it.ma_noi_bo + " · " : ""}${it.doi_tac_ten ? "Đối tác: " + it.doi_tac_ten : "Chưa có đối tác"}`), hang);
      ul.append(li);
    }
    kq.append(ul);
    if (!masterChon) return;
    const cu = $("m4f-tao-nhan-ten"), ten = nhapText("tao-nhan-ten", cu ? cu.value : ""); ten.maxLength = 300;
    const b = nut("Nhận làm hồ sơ M4", async () => {
      const it = masterChon, duAn = taoDuAn, g = genMaster;  // chụp đồng bộ: đúng ứng viên + expected_master người dùng đang thấy
      if (!it) return;
      const body = {du_an_id: duAn, hop_dong_id: it.hop_dong_id, ten: ten.value.trim(), expected_master: it.expected_master};
      if (!body.ten) { trangThai("Nhập tên hồ sơ (tên hợp đồng / gói thầu).", true); return; }
      const f = fence(() => g === genMaster && duAn === taoDuAn && taoCheDo === "co"), fc = formCon();
      const r = await gui("hop-dong/nhan-master", body, "Đã nhận hợp đồng làm hồ sơ M4", f,
        {khi409: e => { if (e.code === "M4_MASTER_DA_DOI") taiMaster(masterDs && masterDs.q || ""); }});  // token cũ: tìm lại, tên đang nhập được giữ
      if (r && f()) {
        if (!fc()) { trangThai("Đã nhận hồ sơ — form đã đổi trong lúc chờ nên chưa tự mở; chọn hồ sơ ở danh sách sau khi ↻ Làm mới."); return; }
        await m4Nap();
        if (f() && fc()) { boMaster(); moHd(r.hop_dong_id, "nguon"); }
      }
    }, "m4-chinh");
    b.id = "m4-tao-nhan";
    const form = node("div", undefined, "m4-form");
    form.append(node("p", `Đã chọn ${masterChon.so_hop_dong} — trạng thái master giữ nguyên; hồ sơ M4 bắt đầu ở nháp.`, "m4-nho"), truong("Tên hồ sơ / gói thầu", ten), b);
    kq.append(form);
  }

  // ------------------------------------------------------------------ chi tiết HĐ
  function veHd() {
    const box = $("m4-chi-tiet"); if (!box) return;
    if (cheDo !== "ho_so") return;  // M4-03A: chế độ Kế toán nghiệm thu — không mount module HĐ vào vùng ẩn (vẽ lại khi quay về)
    oNhap.clear();
    if (!m4 || m4.cau_hinh === false) { box.replaceChildren(); return; }
    if (!hdChon) { box.replaceChildren(node("section", undefined, "m4-card")); box.firstChild.append(node("p", "Chọn một hồ sơ hợp đồng bên trái, hoặc tạo hồ sơ mới.", "m4-trong")); return; }
    if (!hd) { box.replaceChildren(node("p", "Đang tải hồ sơ…", "m4-trong")); return; }
    const h = hd.ho_so, card = node("section", undefined, "m4-card");
    const facts = node("p", `${h.phap_nhan} · ${h.du_an} · revision hồ sơ ${h.revision} · revision tham số ${h.rev_tham_so} · phụ lục: ${KHAI[h.trang_thai_pl] || h.trang_thai_pl}`, "m4-nho");
    card.append(node("h2", `${h.so_hop_dong} · ${h.ten}`), facts,
      soan() ? pill("Phòng dự án phụ trách — được soạn", "m4-du") : pill("Chỉ xem (không soạn/xác nhận)", "m4-xam"));
    const tabs = node("div", undefined, "m4-tabs");
    for (const [k, t] of [["nguon", "Nguồn HĐ & trích"], ["tham_so", "Tham số (37)"], ["phu_luc", "Phụ lục"], ["boq", "BOQ"], ["dot", "Đợt & checklist"],
      ["review", "Review L1/L2"], ["chung_tu", "Chứng từ L3"], ["duyet", "Duyệt & PDF"], ["lo_trinh", "Lộ trình Review"]]) {
      const b = nut(t, () => { genForm += 1; if (TAB_MODULE.has(tab) && k !== tab) tatReview(); tab = k; veHd(); });  // đổi tab: continuation tab cũ không vẽ đè (C2, R7)
      if (k === tab) b.className = "m4-chon";
      b.setAttribute("role", "tab"); b.setAttribute("aria-selected", String(k === tab));
      tabs.append(b);
    }
    card.append(tabs);
    const noi = node("div");
    if (tab === "nguon") veNguon(noi);
    else if (tab === "tham_so") veThamSo(noi);
    else if (tab === "phu_luc") vePhuLuc(noi);
    else if (tab === "boq") veBoq(noi);
    else if (tab === "dot") veTabDot(noi);
    else if (tab === "review") { /* FIX02 F5: mount Review SAU khi vùng đã gắn vào document (fence isConnected của review.js) */ }
    else if (tab === "chung_tu") { /* M4-02B: mount Chứng từ L3 SAU khi vùng đã gắn vào document */ }
    else if (tab === "duyet") { /* M4-02C: mount Duyệt & PDF SAU khi vùng đã gắn vào document */ }
    else veLoTrinh(noi);
    card.append(noi);
    box.replaceChildren(card);
    if (tab === "dot") veDot();  // panel đợt chỉ vẽ sau khi khung đã gắn vào trang
    if (tab === "review") veReview(noi);  // vùng đã attached → R.ve có thể GET đúng ngữ cảnh hiện hành
    if (tab === "chung_tu") veChungTu(noi);
    if (tab === "duyet") veDuyet(noi);
    veDsHd(); veDsDot();
  }

  function tepTheoVai(vai) { return (hd.tep || []).filter(t => t.vai_tro_tai_lieu === vai); }
  function khoGhi(msg) { return !ghiNguon() ? node("p", `Tạm khóa: đường ghi nguồn tin cậy chưa sẵn sàng (${(m4.ghi_nguon && m4.ghi_nguon.ly_do) || "chưa cấu hình"}). ${msg || ""}`, "m4-nho m4-loi-chu") : null; }
  function oTaiLen(vaiCho, idGoc, sauKhi) {  // tải tệp thật hoặc dùng tệp mẫu DEMO cố định (đi qua đúng POST /api/m4/tep)
    const box = node("div", undefined, "m4-form");
    const vai = chon(idGoc + "-vai", vaiCho.map(v => [v, VAI_TL[v]]), vaiCho[0]);
    const tep = o(idGoc + "-file", node("input")); tep.type = "file"; tep.accept = ".docx,.xlsx,.pdf,.png,.jpg,.jpeg";
    const tat = !ghiNguon();
    const b = nut("Tải lên", async () => {
      const file = (tep.files || [])[0];  // tệp + vai chụp đồng bộ lúc bấm
      if (!file) { trangThai("Chọn tệp trước.", true); return; }
      const moi = taoYDinh("tep", JSON.stringify([file.name, file.size, file.lastModified]), vai.value, file, sauKhi, "Đã nhận tệp");
      if (!moi) return;
      // C3: còn ý định chưa rõ cho đúng tệp này TRONG CÙNG ngữ cảnh → gửi lại ĐÚNG File gốc + continuation gốc (không tạo ý định mới)
      await guiTep(taiChuaRo.get(moi.intent) || moi);
    }, "m4-chinh", tat);
    box.append(truong("Vai tài liệu", vai), truong("Tệp", tep), b);
    const mauHop = (mau || []).filter(m => vaiCho.includes(m.vai_tro));
    if (mauHop.length) {
      const m = chon(idGoc + "-mau", mauHop.map(x => [x.ma, `${x.ma} — ${x.mo_ta}`]), "", "— tệp mẫu DEMO —");
      const bm = nut("Dùng tệp mẫu", async () => {
        if (!m.value) return;
        const ma = m.value, item = mauHop.find(x => x.ma === ma);
        const y = taoYDinh("mau", ma, item.vai_tro, null, sauKhi, "Đã nhận tệp mẫu");
        if (!y) return;
        const giu = taiChuaRo.get(y.intent);
        if (giu) { await guiTep(giu); return; }  // C3: gửi lại ý định chưa rõ bằng File GỐC — KHÔNG lấy lại tệp mẫu (bytes/thời điểm có thể khác)
        // C4-02: giữ chỗ MỘT ý định logic ĐỒNG BỘ, trước await đầu tiên — bấm lặp khi đang lấy mẫu/đang tải lên không tạo lần lấy/tải thứ hai.
        // Giữ chỗ tới khi lần tải lên của ý định này kết thúc; kết quả chưa rõ thì chuyển sang taiChuaRo (gửi lại bằng File gốc).
        if (mauDang.has(y.intent)) { trangThai("Đang lấy/tải tệp mẫu này — chờ kết quả, không gửi lần thứ hai."); return; }
        mauDang.set(y.intent, y);
        try {
          const file = await layMau(ma);
          if (!y.f()) return;
          // C2: người dùng đổi mẫu/tệp/vai trong lúc tải bytes mẫu → KHÔNG gửi lựa chọn cũ
          if (!y.fc()) { trangThai("Lựa chọn tệp đã đổi trong lúc lấy tệp mẫu — không gửi tệp mẫu cũ; bấm lại theo lựa chọn hiện tại."); return; }
          y.file = file;  // File gốc của ý định (giữ qua mọi lần gửi lại)
          await guiTep(y);
        } catch (e) { if (y.f()) xuLyLoi(e); }  // lấy mẫu lỗi chắc chắn → nhả giữ chỗ; bấm lại là lần lấy hợp lệ mới
        finally { if (mauDang.get(y.intent) === y) mauDang.delete(y.intent); }
      }, "", tat);
      box.append(truong("Hoặc tệp mẫu DEMO", m), bm);
    }
    return box;
  }

  function veNguon(box) {
    const h = hd.ho_so, hien = (hd.tep || []).find(t => t.id === h.tep_hop_dong_id);
    box.append(node("h3", "Tệp hợp đồng nguồn hiện hành"));
    box.append(hien ? bang(["Tên", "Loại", "Dung lượng", "H (SHA-256)", "Người tải", "Lúc", ""], [[hien.ten_goc, hien.media_type, K.size(hien.byte_length), h12(hien.raw_sha256),
      hien.tao_boi, ngay(hien.tao_luc), nut("Tải ↓", () => taiTep(hien.id, hien.ten_goc), "m4-lien-ket")]])
      : node("p", "Chưa gắn tệp hợp đồng nguồn — tải lên rồi bấm “Gắn làm tệp HĐ”.", "m4-trong"));
    box.append(node("h3", "Tệp nguồn của dự án"), node("p", "Kho tệp của cả dự án (phụ lục/BOQ/hợp đồng) — không mặc định thuộc hồ sơ HĐ này; chỉ tệp được gắn mới là căn cứ.", "m4-nho"));
    const ds = hd.tep || [];
    box.append(ds.length ? bang(["Vai", "Tên", "Loại", "Dung lượng", "H", "Người tải", "Lúc", ""], ds.map(t => {
      const acts = node("div", undefined, "m4-hang");
      acts.append(nut("Tải ↓", () => taiTep(t.id, t.ten_goc), "m4-lien-ket"));
      if (soan() && t.vai_tro_tai_lieu === "HOP_DONG" && t.id !== h.tep_hop_dong_id) {
        acts.append(nut("Gắn làm tệp HĐ", async () => {
          const f = fence(), fc = formCon();
          const r = await gui("hop-dong/gan-tep", {hop_dong_id: h.hop_dong_id, revision: h.revision, tep_id: t.id}, "Đã gắn tệp hợp đồng nguồn", f);
          if (r && f()) await sauLenh(fc, "Đã gắn tệp hợp đồng nguồn");
        }, "m4-chinh"));
      }
      return [VAI_TL[t.vai_tro_tai_lieu] || t.vai_tro_tai_lieu, t.ten_goc, t.media_type, K.size(t.byte_length), h12(t.raw_sha256), t.tao_boi, ngay(t.tao_luc), acts];
    })) : node("p", "Chưa có tệp nguồn trong dự án.", "m4-trong"));
    if (soan()) {
      box.append(node("h3", "Tải tệp nguồn"));
      const k = khoGhi(); if (k) box.append(k);
      box.append(oTaiLen(["HOP_DONG", "PHU_LUC", "BOQ"], "nguon"));
    }
    box.append(node("h3", "Trích tham số từ tệp HĐ hiện hành"));
    if (soan()) {
      const k = khoGhi(); if (k) box.append(k);
      box.append(node("p", "Chạy engine trích DÙNG CHUNG #6 (contract common/v1, chế độ quy tắc RULE_ONLY, loại XD, danh mục 37 mã đã ghim — cùng engine với CRM) "
        + "trên đúng bytes tệp HĐ đã gắn; chưa có Local AI/OCR. Engine chưa được máy chủ cấu hình → báo chưa sẵn sàng (không dùng lõi chép). Tệp Word còn Track Changes "
        + "hoặc PDF sẽ báo chưa hỗ trợ, không đánh dấu đã trích. Mất kết nối khi đang trích: giữ nguyên lệnh, bấm gửi lại y nguyên để đối soát (không chạy lại).", "m4-nho"));
      box.append(nut(`Chạy trích (revision ${h.revision})`, async () => {
        const f = fence(), fc = formCon();
        const r = await gui("hop-dong/trich", {hop_dong_id: h.hop_dong_id, revision: h.revision}, "Đã chạy trích", f);
        if (r && f()) {
          const daVe = await sauLenh(fc, "Đã chạy trích");
          if (daVe && r.trang_thai !== "XONG") trangThai(`Lần trích: ${TT_TRICH[r.trang_thai] || r.trang_thai} — ${r.ly_do || ""}`, true);
        }
      }, "m4-chinh", !h.tep_hop_dong_id || !ghiNguon()));
    }
    const tr = hd.trich_xuat || [];
    box.append(tr.length ? bang(["Lần", "Tệp (H)", "Trạng thái", "Chế độ", "Lý do", "Bộ trích", "Người chạy", "Lúc"], tr.map(t => [t.lan, h12(t.raw_sha256),
      pill(TT_TRICH[t.trang_thai] || t.trang_thai, t.trang_thai === "XONG" ? "m4-du" : "m4-loi"), t.che_do, t.ly_do || "", t.engine, t.tao_boi, ngay(t.tao_luc)]))
      : node("p", "Chưa chạy trích.", "m4-trong"));
    veDoiTac(box);
  }

  // MASTER-REUSE-02: đối tác + căn cứ master của hồ sơ (máy chủ trả trong chi tiết HĐ). Chỉ gắn khi máy chủ báo được; còn lại nêu đúng authority, không nút giả.
  function veDoiTac(box) {
    const mc = hd.master_can_cu, h = hd.ho_so;
    box.append(node("h3", "Đối tác & căn cứ master"));
    if (!mc) { box.append(node("p", "Máy chủ chưa trả căn cứ master/đối tác cho hồ sơ này (gói dùng chung chưa bật) — hồ sơ vẫn soạn như hiện có.", "m4-trong")); return; }
    const ms = mc.master || {}, cc = mc.can_cu, gd = mc.gan_doi_tac || {}, wrap = node("div"); wrap.id = "m4-doi-tac";
    wrap.append(bang(["Nguồn hợp đồng", "Trạng thái master", "Đối tác hiện hành", "Mã Junsky", "Mapping"], [[ms.module_chu === "M4" ? "M4 sở hữu" : "Nguồn master/CRM",
      TT_MASTER[ms.trang_thai_master] || ms.trang_thai_master || "—", ms.doi_tac_ten || "Chưa có đối tác", ms.ma_junsky || "—",
      pill(MAP_TT[ms.mapping_trang_thai] || ms.mapping_trang_thai || "—", ms.mapping_trang_thai === "OK" ? "m4-du" : "m4-thieu")]]));
    wrap.append(node("p", cc ? `Căn cứ số ${cc.so} · ${NGUON_CC[cc.nguon] || cc.nguon} · ${cc.boi || "chưa có người xác nhận"} · ${ngay(cc.tao_luc)}`
      + `${cc.ly_do ? " · " + cc.ly_do : ""} · H ${h12(cc.sha256)}` : "Chưa có căn cứ master.", "m4-nho"),
      mc.dong_bo ? pill("Căn cứ khớp nguồn hiện hành", "m4-du") : pill("Căn cứ chưa khớp nguồn — ↻ Làm mới", "m4-thieu"));
    const hold = mc.hold || [];
    if (hold.length) wrap.append(node("ul", undefined, "m4-list"));
    for (const x of hold) wrap.lastChild.append(node("li", HOLD_TL[x] || x, "m4-loi-chu"));
    if (!ms.doi_tac_id) wrap.append(node("p", "Chưa có đối tác: hồ sơ vẫn là nháp, dữ liệu đã nhập được giữ; gắn đối tác trước khi nộp.", "m4-nho"));
    box.append(wrap);
    if (!gd.duoc) {
      if (gd.ma === "M4_KHONG_CO_QUYEN_DU_AN") wrap.append(node("p", "Vai này chỉ xem — không gắn/sửa đối tác.", "m4-nho"));
      else if (gd.ma) wrap.append(node("p", HUONG_MASTER[gd.ma] || gd.ma, "m4-nho m4-loi-chu"));
      return;
    }
    const q = nhapText("dt-q", ""); q.maxLength = 100; q.placeholder = "Tên đối tác hoặc mã Junsky";
    const tim = nut("Tìm đối tác", () => taiDoiTac(h.du_an_id, q.value.trim()), "m4-chinh"); tim.id = "m4-dt-tim";
    const ds = node("div"); ds.id = "m4-dt-ds";
    const lyDo = nhapText("dt-ly-do", ""); lyDo.maxLength = 1000;
    const gan = nut(`Gắn đối tác đã chọn (revision ${mc.revision})`, async () => {
      const it = doiTacChon, g = genDoiTac;  // chụp đồng bộ: đúng mapping + revision/expected_* người dùng đang thấy
      if (!it) return;
      const ly = lyDo.value.trim();
      if (!ly) { trangThai("Nhập lý do gắn/sửa đối tác (bắt buộc).", true); return; }
      const body = {hop_dong_id: h.hop_dong_id, doi_tac_id: it.doi_tac_id, mapping_id: it.mapping_id, revision: mc.revision,
        expected_master: mc.expected_master, expected_mapping: it.expected_mapping, ly_do: ly};
      const f = fence(() => g === genDoiTac), fc = formCon();
      const r = await gui("hop-dong/gan-doi-tac", body, "Đã gắn đối tác", f, {khi409: e => {
        if (e.code === "M4_MASTER_DA_DOI" || e.code === "M4_MAPPING_DA_DOI") { boDoiTac(); napHd({giu: true}); }  // token cũ: bỏ lựa chọn, giữ lý do
      }});
      if (r && f()) { boDoiTac(); await sauLenh(fc, "Đã gắn đối tác"); }
    }, "m4-chinh", !doiTacChon);
    gan.id = "m4-dt-gan";
    const form = node("div", undefined, "m4-form");
    form.append(truong("Tìm đối tác cùng pháp nhân", q), tim, ds, truong("Lý do gắn/sửa đối tác", lyDo), gan);
    box.append(node("p", "Chọn đúng một mapping hiện hành; mapping mơ hồ/khóa/chưa hiệu lực chỉ hiển thị, không chọn được. M4 không đoán theo MST/tên.", "m4-nho"), form);
    veDsDoiTac();
  }
  async function taiDoiTac(duAn, qv) {
    const g = ++genDoiTac, f = fence(() => g === genDoiTac);
    doiTacChon = null; doiTacDs = {dang: true, q: qv}; veDsDoiTac();
    try {
      const r = await docJson(await goi(`/api/m4/master-doi-tac?du_an_id=${encodeURIComponent(duAn)}&q=${encodeURIComponent(qv)}&limit=25`));
      if (!f()) return;  // vai/HĐ/lần tìm đã đổi: không vẽ danh sách cũ
      doiTacDs = {q: qv, items: r.items || []}; veDsDoiTac();
    } catch (err) {
      if (!f()) return;
      doiTacDs = {q: qv, loi: err.message}; veDsDoiTac(); xuLyLoi(err);
    }
  }
  function veDsDoiTac() {
    const box = $("m4-dt-ds"); if (!box) return;
    const gan = $("m4-dt-gan"); if (gan) gan.disabled = !doiTacChon;
    box.replaceChildren();
    if (!doiTacDs) return;
    if (doiTacDs.dang) { box.append(node("p", "Đang tìm đối tác…", "m4-trong")); return; }
    if (doiTacDs.loi) { box.append(node("p", "Chưa đọc được danh sách đối tác: " + doiTacDs.loi, "m4-trong m4-loi-chu")); return; }
    if (!doiTacDs.items.length) { box.append(node("p", "Không có đối tác hoạt động có mapping cùng pháp nhân.", "m4-trong")); return; }
    box.append(bang(["Đối tác", "Mã Junsky", "Mapping", ""], doiTacDs.items.map(it => {
      const dangChon = !!doiTacChon && doiTacChon.mapping_id === it.mapping_id && doiTacChon.doi_tac_id === it.doi_tac_id;
      return [it.ten, it.ma_junsky || "—", it.ma_hold ? pill(HOLD_MAP[it.ma_hold] || it.ma_hold, "m4-thieu") : pill("Hiện hành rõ", "m4-du"),
        nut(dangChon ? "Đang chọn" : "Chọn", () => { genForm += 1; doiTacChon = it; veDsDoiTac(); }, "m4-lien-ket", !!it.ma_hold || !it.mapping_id)];
    })));
    if (doiTacChon) box.append(node("p", `Đã chọn: ${doiTacChon.ten} · mã ${doiTacChon.ma_junsky}`, "m4-nho"));
  }

  function veThamSo(box) {
    const h = hd.ho_so, ts = hd.tham_so || [], xn = hd.xac_nhan;
    const dem = {};
    ts.forEach(t => { const k = t.trang_thai || "CHUA_TRICH"; dem[k] = (dem[k] || 0) + 1; });
    box.append(node("p", `${ts.length} mã theo danh mục máy chủ (SHA ${h12(hd.danh_muc_sha256)}): ` + Object.entries(dem).map(([k, n]) => `${TT_THAM_SO[k] || "Chưa trích"} ${n}`).join(" · "), "m4-nho"));
    const xbox = node("div", undefined, "m4-hang");
    if (xn) {
      xbox.append(node("span", `Phòng dự án đã xác nhận revision tham số ${xn.rev_tham_so} — ${xn.xac_nhan_boi}, ${ngay(xn.xac_nhan_luc)}${xn.ly_do ? " · " + xn.ly_do : ""}. `),
        xn.con_hieu_luc ? pill("Còn hiệu lực", "m4-du") : pill("Hết hiệu lực — tham số/nguồn đã đổi, cần xác nhận lại", "m4-thieu"));
    } else xbox.append(pill("Chưa xác nhận bộ tham số", "m4-thieu"));
    box.append(xbox);
    const loc = o("ts-thieu", node("input")); loc.type = "checkbox"; loc.checked = chiThieu;
    loc.addEventListener("change", () => { chiThieu = loc.checked; veHd(); });
    const ll = node("label"); ll.htmlFor = loc.id; ll.append(loc, document.createTextNode(" Chỉ mã còn thiếu (chưa trích / Chưa có)"));
    box.append(ll);
    const hien = ts.filter(t => !chiThieu || !t.trang_thai || t.trang_thai === "CHUA_CO");
    box.append(bang(["Mã", "Nhóm", "Tham số", "Trạng thái", "Giá trị", "Giá trị máy", "Đơn vị", "Điều khoản", "Trích dẫn", "Kiểm tra", "Lý do", "Vị trí", "Nguồn", ""],
      hien.map(t => [node("span", t.ma, "m4-ma"), t.nhom, t.ten, pill(t.trang_thai ? (TT_THAM_SO[t.trang_thai] || t.trang_thai) : "Chưa trích",
        t.trang_thai === "CO_GIA_TRI" ? "m4-du" : t.trang_thai && t.trang_thai !== "CHUA_CO" ? "m4-xam" : "m4-thieu"), t.gia_tri || "", t.gia_tri_may || "", t.don_vi || "",
        t.dieu_khoan || "", node("div", t.trich_dan || "", "m4-trich"), t.kiem_tra || "", t.ly_do || "", node("div", t.vi_tri || "", "m4-trich"), t.nguon || "",
        soan() && t.trang_thai ? nut("Sửa", () => { genForm += 1; suaMa = t.ma; veHd(); const el = $("m4f-sua-tt"); if (el) el.focus(); }, "m4-lien-ket") : ""]), "m4-bang-rong"));
    if (soan() && suaMa) {
      const t = ts.find(x => x.ma === suaMa);
      if (t) {
        const k = khoGhi("Sửa tham số cần máy chủ kiểm trích dẫn trên văn bản nguồn."); if (k) box.append(k);
        const tt = chon("sua-tt", [["CO_GIA_TRI", "Có giá trị"], ["KHONG_AP_DUNG", "Không áp dụng"], ["KHONG_QUY_DINH", "Không quy định"]], t.trang_thai === "CHUA_CO" ? "CO_GIA_TRI" : t.trang_thai);
        const gt = nhapText("sua-gt", t.gia_tri), dv = nhapText("sua-dv", t.don_vi), dk = nhapText("sua-dk", t.dieu_khoan);
        const td = o("sua-td", node("textarea")); td.value = t.trich_dan || ""; td.rows = 3;
        const ld = o("sua-ld", node("textarea")); ld.value = t.ly_do || ""; ld.rows = 2;
        const form = node("div", undefined, "m4-form");
        form.append(truong("Trạng thái", tt), truong("Giá trị", gt), truong("Đơn vị", dv), truong("Điều khoản", dk), truong("Trích dẫn nguyên văn từ HĐ", td), truong("Lý do", ld));
        const luu = nut(`Lưu ${t.ma} (revision ${h.revision})`, async () => {
          const body = {hop_dong_id: h.hop_dong_id, revision: h.revision, ma: t.ma, trang_thai_tham_so: tt.value, gia_tri: rong(gt.value), don_vi: rong(dv.value),
            dieu_khoan: rong(dk.value), trich_dan: rong(td.value), ly_do: rong(ld.value)};
          const f = fence(), fc = formCon();
          const r = await gui("tham-so/sua", body, `Đã lưu ${t.ma}`, f);
          if (r && f()) {
            // C2: chỉ đóng form khi form đang hiện vẫn là form đã gửi (mở Sửa mã khác/sửa ô trong lúc chờ → giữ form + nháp mới)
            if (!fc()) { trangThai(`Đã lưu ${t.ma}${r.kiem_tra ? " · máy kiểm: " + r.kiem_tra : ""} — form đang mở đã đổi nên giữ nguyên nháp; bấm ↻ Làm mới khi xong.`); return; }
            suaMa = null; await napLai(false);
            if (r.kiem_tra && f()) trangThai(`Máy kiểm trích dẫn: ${r.kiem_tra}`);
          }
        }, "m4-chinh", !ghiNguon());
        const huy = nut("Đóng", () => { genForm += 1; suaMa = null; veHd(); });
        box.append(node("h3", `Sửa ${t.ma} · ${t.ten}`), node("p", "Có giá trị phải kèm trích dẫn nguyên văn — máy chủ đối chiếu với văn bản HĐ nguồn. Không áp dụng/Không quy định cần lý do (không ghi 0).", "m4-nho"),
          form, node("div", undefined, "m4-hang"));
        box.lastChild.append(luu, huy);
      }
    }
    if (soan()) {
      const ld = o("xn-ld", node("textarea")); ld.rows = 2;
      const b = nut(`Phòng dự án xác nhận bộ tham số (revision ${h.revision})`, async () => {
        const f = fence(), fc = formCon();
        const r = await gui("tham-so/xac-nhan", {hop_dong_id: h.hop_dong_id, revision: h.revision, ly_do: rong(ld.value)}, "Đã xác nhận bộ tham số", f);
        if (r && f()) await sauLenh(fc, "Đã xác nhận bộ tham số");
      }, "m4-chinh");
      box.append(node("h3", "Xác nhận của phòng dự án"), node("p", "Chỉ xác nhận khi đã soát đủ 37 mã trên lần trích hiện hành; máy chủ chặn nếu còn mã Chưa có hoặc lần trích chưa xong/khác tệp. Không tự xác nhận.", "m4-nho"),
        truong("Ghi chú xác nhận", ld), b);
    }
  }

  function vePhuLuc(box) {
    const h = hd.ho_so, ds = hd.phu_luc || [];
    box.append(node("p", `Khai báo hiện tại: ${KHAI[h.trang_thai_pl] || h.trang_thai_pl}`, "m4-nho"));
    if (soan()) {
      const s = chon("pl-khai", [["KHONG_CO", KHAI.KHONG_CO], ["CO_CHUA_DU", KHAI.CO_CHUA_DU], ["CO_DU", KHAI.CO_DU]], h.trang_thai_pl === "CHUA_KHAI" ? "" : h.trang_thai_pl, "— chọn khai báo —");
      const b = nut(`Lưu khai báo (revision ${h.revision})`, async () => {
        if (!s.value) { trangThai("Chọn khai báo phụ lục.", true); return; }
        const f = fence(), fc = formCon();
        const r = await gui("phu-luc/khai", {hop_dong_id: h.hop_dong_id, revision: h.revision, khai: s.value}, "Đã lưu khai báo phụ lục", f);
        if (r && f()) await sauLenh(fc, "Đã lưu khai báo phụ lục");
      }, "m4-chinh");
      const hang = node("div", undefined, "m4-hang"); hang.append(truong("Tình trạng phụ lục", s), b); box.append(hang);
    }
    box.append(node("h3", "Phụ lục (giữ toàn bộ lịch sử, kể cả đã hủy)"),
      node("p", "Phụ lục dự thảo hoặc có ngày hiệu lực sau ngày nghiệm thu của đợt không được áp vào đợt đó — xem mục Hiệu lực ở tab Đợt.", "m4-nho"));
    box.append(ds.length ? bang(["Số PL", "Ngày ký", "Ngày hiệu lực", "Trạng thái", "Đổi BOQ", "Nội dung", "Tệp", "Lý do hủy", ""], ds.map(p => {
      const t = p.tep_id && (hd.tep || []).find(x => x.id === p.tep_id);
      const tep = t ? nut(t.ten_goc + " ↓", () => taiTep(t.id, t.ten_goc), "m4-lien-ket") : "—";
      let act = "";
      if (soan() && p.trang_thai !== "DA_HUY") {
        act = node("div", undefined, "m4-hang"); const ld = nhapText("pl-huy-" + p.id, "");
        act.append(truong("Lý do hủy", ld), nut("Hủy", async () => {
          if (!ld.value.trim()) { trangThai("Nhập lý do hủy phụ lục.", true); return; }
          const f = fence(), fc = formCon();
          const r = await gui("phu-luc/huy", {phu_luc_id: p.id, revision: h.revision, ly_do: ld.value.trim()}, "Đã hủy phụ lục (giữ lịch sử)", f);
          if (r && f()) await sauLenh(fc, "Đã hủy phụ lục");
        }));
      }
      return [p.so_pl, p.ngay_ky, p.ngay_hieu_luc, pill(PL_TT[p.trang_thai] || p.trang_thai, p.trang_thai === "DA_KY" ? "m4-du" : "m4-xam"), p.doi_boq ? "Có" : "Không",
        p.noi_dung || "", tep, p.huy_ly_do || "", act];
    })) : node("p", "Chưa nhập phụ lục.", "m4-trong"));
    if (soan()) {
      const so = nhapText("pl-so", ""), nk = nhapText("pl-ngay-ky", "", "date"), nh = nhapText("pl-ngay-hl", "", "date");
      const tt = chon("pl-tt", [["DA_KY", "Đã ký"], ["DU_THAO", "Dự thảo"]], "DA_KY");
      const doi = o("pl-doi-boq", node("input")); doi.type = "checkbox";
      const nd = nhapText("pl-nd", ""), tep = chon("pl-tep", tepTheoVai("PHU_LUC").map(t => [t.id, `${t.ten_goc} · H ${h12(t.raw_sha256)}`]), "", "— chưa gắn tệp —");
      const form = node("div", undefined, "m4-form");
      form.append(truong("Số phụ lục", so), truong("Ngày ký", nk), truong("Ngày hiệu lực", nh), truong("Trạng thái", tt), truong("Có đổi BOQ", doi), truong("Nội dung", nd), truong("Tệp phụ lục (đã tải ở tab Nguồn)", tep));
      const b = nut(`Thêm phụ lục (revision ${h.revision})`, async () => {
        const body = {hop_dong_id: h.hop_dong_id, revision: h.revision, so_pl: so.value.trim(), ngay_ky: nk.value, ngay_hieu_luc: nh.value, trang_thai_phu_luc: tt.value,
          doi_boq: !!doi.checked, noi_dung: rong(nd.value), tep_id: tep.value || null};
        if (!body.so_pl || !body.ngay_ky || !body.ngay_hieu_luc) { trangThai("Nhập số phụ lục, ngày ký và ngày hiệu lực.", true); return; }
        const f = fence(), fc = formCon();
        const r = await gui("phu-luc/them", body, "Đã thêm phụ lục", f);
        if (r && f()) await sauLenh(fc, "Đã thêm phụ lục");
      }, "m4-chinh");
      box.append(node("h3", "Thêm phụ lục"), form, b);
    }
  }

  function oGoc(c, typed) {  // ô gốc do máy chủ đọc lại: trống ≠ 0, chữ hiện nguyên văn, locator ở tooltip
    if (!c) return typed ?? "";
    const s = c.kieu === "TRONG" ? "(trống)" : c.kieu === "KHONG_MAP" ? "(không map)" : c.kieu === "CHU" ? `"${c.tho}" (chữ)` : String(c.tho);
    const el = node("span", s, "m4-o m4-o-" + String(c.kieu || "").toLowerCase()); if (c.o) el.title = "Ô " + c.o; return el;
  }
  function dsLoi(ds) {
    if (!ds || !ds.length) return node("p", "Không có.", "m4-nho");
    const ul = node("ul"); ds.forEach(x => ul.append(node("li", `${x.ma} · dòng ${x.dong || "—"}${x.o && x.o.length ? " · ô " + x.o.join(", ") : ""} · ${x.noi_dung}`))); return ul;
  }
  function veBoq(box) {
    const h = hd.ho_so, ds = hd.boq || [];
    box.append(node("h3", "Các lần nhập BOQ"));
    box.append(ds.length ? bang(["Lần", "Loại", "Tệp (H)", "Sheet", "Dòng tiêu đề", "Số dòng", "Trạng thái", "Lỗi chặn", "Phát hiện", ""], ds.map(b => {
      const pl = b.phu_luc_id ? (hd.phu_luc || []).find(p => p.id === b.phu_luc_id) : null;
      return [b.lan, pl ? "Phụ lục " + pl.so_pl : "BOQ gốc", h12(b.raw_sha256), b.sheet, b.hang_tieu_de, b.so_dong, pill(BOQ_TT[b.trang_thai] || b.trang_thai, b.trang_thai === "DA_MAP" ? "m4-du" : "m4-loi"),
        (b.loi_chan || []).length, (b.phat_hien || []).length, nut(xemLoi === b.id ? "Ẩn" : "Xem lỗi/phát hiện", () => { xemLoi = xemLoi === b.id ? null : b.id; veHd(); }, "m4-lien-ket")];
    })) : node("p", "Chưa nhập BOQ.", "m4-trong"));
    const xb = ds.find(b => b.id === xemLoi);
    if (xb) box.append(node("h3", `Lần ${xb.lan} — lỗi chặn (chưa đủ căn cứ)`), dsLoi(xb.loi_chan),
      node("h3", "Phát hiện nghiệp vụ (giữ để review, không chặn nộp; không tự sửa thành tiền)"), dsLoi(xb.phat_hien));
    const dong = hd.boq_goc_dong || [];
    box.append(node("h3", "BOQ gốc hiện hành"), node("p", "Tối đa 2.000 dòng của lần nhập BOQ gốc mới nhất (không phải toàn bộ workbook). Số hiển thị đúng ô gốc: trống ≠ 0; thành tiền giữ nguyên số trong tệp.", "m4-nho"));
    box.append(dong.length ? bang(["Dòng", "Mã hạng mục", "Thao tác", "STT", "Nhóm", "Tên", "ĐVT", "Khối lượng", "Đơn giá", "Thành tiền"], dong.map(r => [r.dong,
      node("span", r.ma_hm, "m4-ma"), r.thao_tac, r.stt || "", r.nhom || "", r.ten, r.dvt, oGoc(r.o_goc && r.o_goc.kl, r.kl), oGoc(r.o_goc && r.o_goc.don_gia, r.don_gia),
      oGoc(r.o_goc && r.o_goc.thanh_tien, r.thanh_tien)])) : node("p", "Chưa có BOQ gốc đọc được.", "m4-trong"));
    if (!soan()) return;
    box.append(node("h3", "Nhập BOQ: tệp → sheet → dòng tiêu đề → map 7 trường → nhập"));
    const k = khoGhi(); if (k) box.append(k);
    // C2: vé lựa chọn BOQ (genBoq) — mỗi lần đổi tệp/sheet hoặc bấm đọc/xem tăng vé; chỉ phản hồi của vé MỚI NHẤT được vẽ (A trễ không kéo về A,
    // lỗi cũ không vẽ). Đổi lựa chọn → form Nhập của lựa chọn cũ bị gỡ NGAY (vẽ lại đồng bộ); khi xem trước còn chờ thì không có nút Nhập.
    const tep = chon("boq-tep", tepTheoVai("BOQ").map(t => [t.id, `${t.ten_goc} · H ${h12(t.raw_sha256)}`]), boqTep, "— chọn tệp BOQ (tải ở tab Nguồn) —");
    // C3: phản hồi/lỗi xem trước cập nhật TRẠNG THÁI BOQ (theo vé); chỉ vẽ lại khi vẫn đang ở tab BOQ, và vẽ với nháp mới nhất (veGiu).
    // Đã chuyển tab/đang nhập form khác → không dựng lại gì; quay lại tab BOQ sẽ thấy đúng xem trước mới nhất.
    const veBoqNeuDangMo = () => { if (tab === "boq") veGiu(veHd); };
    const docSheet = async tepId => {
      const ve = ++genBoq, f = fence(() => ve === genBoq && boqTep === tepId);
      boqXem = {tep_id: tepId, sheets: null, sheet: "", xem: null, dang: true}; veHd();
      try {
        const r = await postJson("boq/xem", {tep_id: tepId});
        if (!f()) return;
        const goiY = r.goi_y || null;
        boqXem = {tep_id: tepId, sheets: r.sheets || [], sheet: goiY ? goiY.sheet : "", xem: goiY, dang: false};
        veBoqNeuDangMo();
      } catch (e) { if (f()) { boqXem = {tep_id: tepId, sheets: null, sheet: "", xem: null, dang: false}; veBoqNeuDangMo(); xuLyLoi(e); } }
    };
    const doc = nut("Đọc danh sách sheet", () => { if (!tep.value) { trangThai("Chọn tệp BOQ.", true); return; } boqTep = tep.value; docSheet(tep.value); });
    tep.addEventListener("change", () => { genBoq += 1; boqTep = tep.value; boqXem = null; veHd(); });  // đổi tệp: gỡ ngay xem trước/form Nhập của tệp cũ
    const hang1 = node("div", undefined, "m4-hang"); hang1.append(truong("Tệp BOQ", tep), doc); box.append(hang1);
    if (!boqXem || boqXem.tep_id !== boqTep) return;
    if (!boqXem.sheets) { if (boqXem.dang) box.append(node("p", "Đang đọc danh sách sheet…", "m4-nho")); return; }
    const sh = chon("boq-sheet", boqXem.sheets.map(s => [s.ten, `${s.ten} · ${s.so_dong} dòng × ${s.so_cot} cột${s.an ? " (ẩn)" : ""}`]), boqXem.sheet);
    const xemSheet = async ten => {
      const tepId = boqXem.tep_id, ve = ++genBoq, f = fence(() => ve === genBoq && boqTep === tepId && boqXem && boqXem.tep_id === tepId && boqXem.sheet === ten);
      boqXem.sheet = ten; boqXem.xem = null; boqXem.dang = true; veHd();  // gỡ form Nhập cũ ngay, trước khi chờ
      try {
        const r = await postJson("boq/xem", {tep_id: tepId, sheet: ten});
        if (!f()) return;
        boqXem.xem = r; boqXem.dang = false; veBoqNeuDangMo();
      } catch (e) { if (f()) { boqXem.dang = false; veBoqNeuDangMo(); xuLyLoi(e); } }
    };
    sh.addEventListener("change", () => xemSheet(sh.value));
    const xem = nut("Xem trước sheet", () => xemSheet(sh.value));
    const hang2 = node("div", undefined, "m4-hang"); hang2.append(truong("Sheet", sh), xem); box.append(hang2);
    const xv = boqXem.xem;
    if (boqXem.dang) { box.append(node("p", `Đang xem trước sheet ${boqXem.sheet}… (chưa nhập được cho tới khi xem trước xong)`, "m4-nho")); return; }
    if (!xv || xv.sheet !== boqXem.sheet) return;
    const veNhap = genBoq, xemNhap = boqXem;
    const soCot = Math.max(xv.so_cot || 0, ...(xv.dong || []).map(d => d.length));
    box.append(node("p", `Xem trước ${Math.min((xv.dong || []).length, 40)} dòng đầu của sheet ${xv.sheet}. Gợi ý dòng tiêu đề/cột chỉ để điền sẵn — không tự nhập.`, "m4-nho"));
    box.append(bang(["#", ...Array.from({length: soCot}, (_, i) => cotChu(i))], (xv.dong || []).slice(0, 40).map((d, i) => [i + 1, ...Array.from({length: soCot}, (_, j) => d[j] ?? "")]), "m4-bang-nho"));
    const hang = nhapText("boq-hang", xv.hang_tieu_de ?? "", "number"); hang.min = "1";
    const truongDs = (xv.truong && xv.truong.length ? xv.truong.map(t => [t.ma, t.ten]) : TRUONG_BOQ);
    const map = node("div", undefined, "m4-form"), oCot = {};
    map.append(truong("Dòng tiêu đề", hang));
    for (const [ma, ten] of truongDs) { const i = nhapText("boq-cot-" + ma, (xv.cot || {})[ma] || ""); i.maxLength = 3; i.placeholder = "A…"; oCot[ma] = i; map.append(truong(ten + " (cột)", i)); }
    const plDs = (hd.phu_luc || []).filter(p => p.doi_boq && p.trang_thai !== "DA_HUY");
    const pl = chon("boq-pl", plDs.map(p => [p.id, `Phụ lục ${p.so_pl} (${PL_TT[p.trang_thai]}, hiệu lực ${p.ngay_hieu_luc})`]), "", "BOQ gốc của HĐ");
    map.append(truong("Thuộc", pl));
    box.append(map);
    const nhap = nut(`Nhập BOQ (revision ${h.revision})`, async () => {
      // C2: chỉ nhập khi lựa chọn hiện tại vẫn đúng tệp/sheet của xem trước đang hiện; đọc header/map từ CHÍNH các ô đang hiện
      if (veNhap !== genBoq || boqXem !== xemNhap || boqXem.dang || boqXem.sheet !== xv.sheet || boqTep !== xemNhap.tep_id) {
        trangThai("Lựa chọn tệp/sheet BOQ đã đổi — xem trước lại rồi nhập.", true); return;
      }
      const n = Number(hang.value);
      if (!Number.isInteger(n) || n < 1) { trangThai("Dòng tiêu đề phải là số nguyên ≥ 1.", true); return; }
      const cot = {};
      for (const [ma, i] of Object.entries(oCot)) { const v = i.value.trim().toUpperCase(); if (v) cot[ma] = v; }
      const body = {hop_dong_id: h.hop_dong_id, revision: h.revision, tep_id: xemNhap.tep_id, phu_luc_id: pl.value || null, sheet: xv.sheet, hang_tieu_de: n, cot};
      const f = fence(), fc = formCon(), veLuc = genBoq;
      const r = await gui("boq/nhap", body, "Đã nhập BOQ", f);
      if (r && f()) {
        const tom = `BOQ lần nhập: ${BOQ_TT[r.trang_thai] || r.trang_thai} · ${r.so_dong} dòng · ${r.so_loi_chan} lỗi chặn · ${r.so_phat_hien} phát hiện`;
        if (!fc() || veLuc !== genBoq) { trangThai(tom + " — lựa chọn/form đã đổi trong lúc chờ nên giữ nguyên màn hình; bấm ↻ Làm mới khi xong.", r.trang_thai !== "DA_MAP"); return; }
        xemLoi = r.boq_id; boqXem = null; boqTep = ""; await napLai(false);
        if (f()) trangThai(tom, r.trang_thai !== "DA_MAP");
      }
    }, "m4-chinh", !ghiNguon());
    nhap.id = "m4-boq-nhap";
    box.append(nhap);
  }

  function veTabDot(box) {
    const h = hd.ho_so, ds = hd.dot || [];
    box.append(node("h3", "Các đợt của hợp đồng"));
    box.append(ds.length ? bang(["Đợt", "Ngày nghiệm thu", "Trạng thái", "Revision đợt", "Nộp lúc", "Căn cứ", ""], ds.map(d => [d.so_dot, d.ngay_nghiem_thu || "chưa có",
      pill(DOT_TT[d.trang_thai] || d.trang_thai, d.trang_thai === "DA_NOP" ? "m4-du" : "m4-xam"), d.revision, d.nop_luc ? ngay(d.nop_luc) : "",
      d.can_cu_doi_sau_nop ? pill("Căn cứ HĐ đã đổi sau khi nộp", "m4-thieu") : "", nut(d.id === dotChon ? "Đang mở" : "Mở", () => moDot(h.hop_dong_id, d.id), "m4-lien-ket", d.id === dotChon)]))
      : node("p", "Chưa có đợt.", "m4-trong"));
    if (soan()) {
      const so = nhapText("dot-so", "", "number"), ng = nhapText("dot-ngay", "", "date"); so.min = "1";
      const b = nut("Tạo đợt", async () => {
        const n = Number(so.value);
        if (!Number.isInteger(n) || n < 1) { trangThai("Nhập số đợt (số nguyên ≥ 1).", true); return; }
        const f = fence(), fc = formCon();
        const r = await gui("dot/tao", {hop_dong_id: h.hop_dong_id, so_dot: n, ngay_nghiem_thu: ng.value || null}, "Đã tạo đợt nháp", f);
        if (r && f()) {
          if (!fc()) { trangThai("Đã tạo đợt nháp — form đã đổi trong lúc chờ nên chưa tự mở; bấm ↻ Làm mới khi xong."); return; }
          await m4Nap(); if (f() && fc()) moDot(h.hop_dong_id, r.dot_id);
        }
      }, "m4-chinh");
      const form = node("div", undefined, "m4-form"); form.append(truong("Số đợt", so), truong("Ngày nghiệm thu (có thể bổ sung sau)", ng), b);
      box.append(node("h3", "Tạo đợt nháp"), node("p", "Đợt sau dùng lại hồ sơ HĐ/PL/BOQ; ngày nghiệm thu và bộ tài liệu của kỳ phải nhập riêng (không chép kỳ trước).", "m4-nho"), form);
    }
    const p = node("div"); p.id = "m4-dot-panel"; box.append(p);
  }

  function denBoSung(t) {  // từ mục còn thiếu → vùng bổ sung tương ứng
    genForm += 1;
    if (TAB_MODULE.has(tab)) tatReview();
    if (t.muc) { mucChon = t.muc; tab = "dot"; veHd(); const el = $("m4f-hs-file"); if (el) el.focus(); return; }
    if (t.ma === "DOT_CHUA_NGAY") { tab = "dot"; veHd(); const el = $("m4f-dot-sua-ngay"); if (el) el.focus(); return; }
    tab = t.nhom === "PHU_LUC" ? "phu_luc" : t.nhom === "BOQ" ? "boq" : ["HD_CHUA_CO_TEP", "HD_CHUA_TRICH", "HD_TRICH_KHAC_TEP", "HD_TRICH_CHUA_XONG"].includes(t.ma) ? "nguon" : "tham_so";
    veHd();
  }
  function veDot() {
    const box = $("m4-dot-panel"); if (!box) return;
    if (!dotChon) { box.replaceChildren(); return; }
    if (!dot) { box.replaceChildren(node("p", "Đang tải đợt…", "m4-trong")); return; }
    const d = dot.dot, laSoan = !!d.soan, card = node("div", undefined, "m4-card m4-card-dot");
    card.append(node("h3", `Đợt ${d.so_dot} · ${DOT_TT[d.trang_thai] || d.trang_thai} · revision đợt ${d.revision} · revision hồ sơ HĐ ${d.revision_ho_so}`));
    if (dot.can_cu_doi_sau_nop) card.append(node("div", "Căn cứ hồ sơ HĐ đã đổi sau khi nộp — ảnh chụp lúc nộp vẫn giữ nguyên; đợt đã nộp không tự cập nhật.", "m4-notice"));
    if (laSoan && d.trang_thai === "NHAP") {
      const ng = nhapText("dot-sua-ngay", d.ngay_nghiem_thu || "", "date");
      const b = nut(`Lưu ngày (revision đợt ${d.revision})`, async () => {
        if (!ng.value) { trangThai("Chọn ngày nghiệm thu.", true); return; }
        const f = fence(), fc = formCon();
        const r = await gui("dot/sua", {dot_id: d.id, revision: d.revision, ngay_nghiem_thu: ng.value}, "Đã lưu ngày nghiệm thu", f);
        if (r && f()) await sauLenh(fc, "Đã lưu ngày nghiệm thu");
      }, "m4-chinh");
      const hang = node("div", undefined, "m4-hang"); hang.append(truong("Ngày nghiệm thu", ng), b); card.append(hang);
    } else card.append(node("p", `Ngày nghiệm thu: ${d.ngay_nghiem_thu || "chưa có"}`, "m4-nho"));
    card.append(node("h3", "Checklist hồ sơ đợt"));
    card.append(bang(["Mã", "Tài liệu", "Bắt buộc kỳ này", "Tệp đã gắn", "Ghi chú"], (dot.checklist || []).map(c => {
      const cell = node("div");
      (c.tep || []).forEach(t => cell.append(nut(`${t.ten_goc} ↓`, () => taiTep(t.tep_id, t.ten_goc), "m4-lien-ket")));
      if (!(c.tep || []).length) cell.append(node("span", c.bat_buoc ? "Thiếu" : "—", c.bat_buoc ? "m4-loi-chu" : "m4-nho"));
      return [node("span", c.ma, "m4-ma"), c.ten, c.bat_buoc ? "Có" : "Không", cell, c.ghi_chu || ""];
    })));
    if (laSoan && d.trang_thai === "NHAP") {
      card.append(node("h3", "Bổ sung tài liệu đợt"));
      const k = khoGhi(); if (k) card.append(k);
      const tl = oTaiLen(["HO_SO_DOT"], "hs", (r, ten) => { hoSoMoi = hoSoMoi.filter(x => x.tep_id !== r.tep_id).concat([{tep_id: r.tep_id, ten, goi_y_muc: r.goi_y_muc || []}]); });
      card.append(tl);
      const tepDs = [...hoSoMoi.map(x => [x.tep_id, `${x.ten} (vừa tải trong phiên này)`]),
        ...(dot.tep || []).filter(t => !hoSoMoi.some(x => x.tep_id === t.tep_id)).map(t => [t.tep_id, `${t.ten_goc} (đã gắn mục ${t.muc})`])];
      const goiY = new Set(hoSoMoi.flatMap(x => (x.goi_y_muc || []).map(g => g.ma)));
      const tepSel = chon("hs-tep", tepDs, tepDs.length ? tepDs[0][0] : "", "— chọn tệp —");
      const mucSel = chon("hs-muc", (dot.checklist || []).map(c => [c.ma, `${c.ma} · ${c.ten}${goiY.has(c.ma) ? " (gợi ý theo tên tệp)" : ""}`]), mucChon, "— chọn mục —");
      const b = nut(`Gắn vào mục (revision đợt ${d.revision})`, async () => {
        if (!tepSel.value || !mucSel.value) { trangThai("Chọn tệp và mục hồ sơ.", true); return; }
        const f = fence(), fc = formCon();
        const r = await gui("dot/gan-tep", {dot_id: d.id, revision: d.revision, tep_id: tepSel.value, muc: mucSel.value}, "Đã gắn tài liệu vào mục", f);
        if (r && f() && fc()) mucChon = "";
        if (r && f()) await sauLenh(fc, "Đã gắn tài liệu vào mục");
      }, "m4-chinh");
      const form = node("div", undefined, "m4-form"); form.append(truong("Tệp", tepSel), truong("Mục hồ sơ", mucSel), b); card.append(form);
      card.append(node("p", "Gợi ý mục theo tên tệp chỉ để tham khảo — người soạn chọn mục.", "m4-nho"));
    }
    const hl = dot.hieu_luc || {};
    card.append(node("h3", "Hiệu lực phụ lục/BOQ tại ngày nghiệm thu"),
      node("p", hl.loi ? `Chưa tính được: ${hl.thong_bao || hl.loi}` : `Ngày ${hl.ngay || "—"} · phụ lục áp dụng: ${(hl.phu_luc_ap_dung || []).join(", ") || "không có"} · hạng mục hiệu lực ${hl.so_hang_muc_hieu_luc ?? "—"}`
        + ` · bỏ ${hl.so_hang_muc_bo ?? "—"} — chỉ hiển thị; CSDL quyết định gate nộp.`, "m4-nho"));
    if (!dot.nop) {
      card.append(node("h3", "Kiểm trước khi nộp (máy chủ)"));
      const th = dot.thieu || [];
      if (th.length) {
        const ul = node("ul", undefined, "m4-thieu-ds");
        th.forEach(t => { const li = node("li"); li.append(pill(t.nhom, "m4-thieu"), node("span", " " + t.noi_dung + " "));
          if (laSoan) li.append(nut("Bổ sung →", () => denBoSung(t), "m4-lien-ket")); ul.append(li); });
        card.append(ul);
      } else card.append(node("p", "Đủ căn cứ theo kiểm của máy chủ.", "m4-nho m4-du-chu"));
      if (laSoan && d.trang_thai === "NHAP") {
        card.append(nut(`Nộp chính thức (hồ sơ rev ${d.revision_ho_so}, đợt rev ${d.revision})`, async () => {
          const f = fence(), fc = formCon();
          const r = await gui("dot/nop", {dot_id: d.id, revision_ho_so: d.revision_ho_so, revision_dot: d.revision}, "Đã nộp hồ sơ đợt", f);
          if (r && f() && await sauLenh(fc, `Đã nộp · digest ${h12(r.digest)}`) && f()) trangThai(`Đã nộp · digest ${h12(r.digest)} · các nhánh sau chưa nối (xem bên dưới).`);
        }, "m4-chinh", !dot.du_can_cu));
        if (!dot.du_can_cu) card.append(node("p", "Nút Nộp mở khi máy chủ báo đủ căn cứ; nháp vẫn được lưu từng phần.", "m4-nho"));
      }
    } else {
      const n = dot.nop, s = n.snapshot || {};
      card.append(node("h3", "Đã nộp — ảnh chụp căn cứ"),
        node("p", `Nộp bởi ${n.nop_boi} lúc ${ngay(n.nop_luc)} · revision hồ sơ ${n.revision_ho_so} · revision đợt ${n.revision_dot} · digest ${h12(n.digest)}`, "m4-nho"));
      const tepHd = s.tep_hop_dong || {};
      card.append(bang(["Căn cứ", "Tham chiếu"], [
        ["Tệp HĐ", `${tepHd.ten || "—"} · H ${h12(tepHd.raw_sha256)}`], ["Lần trích", s.trich_xuat_id || "—"], ["Xác nhận tham số", `${s.xac_nhan_id || "—"} · digest ${h12(s.tham_so_digest)}`],
        ["Khai phụ lục", KHAI[s.khai_phu_luc] || s.khai_phu_luc || "—"], ["Phụ lục đã ký", (s.phu_luc || []).map(p => `${p.so_pl}${p.ap_dung ? " (áp dụng)" : ""}`).join(", ") || "không"],
        ["BOQ", (s.boq || []).map(b => `${b.phu_luc_id ? "PL" : "gốc"} · ${b.so_dong} dòng · ${b.so_phat_hien} phát hiện`).join("; ") || "—"],
        ["Tài liệu đợt", (s.tai_lieu || []).map(t => `${t.muc} H ${h12(t.raw_sha256)}`).join("; ") || "—"]]));
    }
    const ns = dot.nhanh_sau || [];
    if (ns.length) card.append(node("h3", "Các bước sau khi nộp"), bang(["Bước", "Trạng thái", "Gói"], ns.map(x => [x.ten, x.trang_thai === "CHUA_NOI" ? "Chưa nối" : x.trang_thai, x.goi])));
    box.replaceChildren(card);
  }

  // M4-02A: tab Review = màn checks.js nguồn đã thích nghi (/m4/review.js, tải đúng một lần qua route M4). Cầu nối chỉ truyền ngữ cảnh do máy chủ
  // trả (HĐ đang mở, các đợt trong phạm vi, vai hiện hành); review.js tự là người tham gia cổng đổi vai chung ("m4_review").
  let rvTai = false;
  function veReview(box) {  // gọi SAU khi `box` đã gắn vào document (veHd) — không mount vào cây tách rời
    const vung = node("div", undefined, "m4-rv");
    box.append(vung);
    if (!vung.isConnected) return;  // khung đã bị thay trước khi mount (đổi tab/HĐ/vai) → không mount/load ngữ cảnh cũ
    const R = window.kttM4Review;
    if (!R) {
      vung.append(node("p", "Đang tải màn Review…", "m4-trong"));
      if (!rvTai) {
        rvTai = true;
        // script nạp xong: chỉ vẽ lại theo ngữ cảnh HIỆN HÀNH (tab/HĐ/vai lúc callback), không mount ngữ cảnh lúc bắt đầu tải
        window.kttM4ReviewSanSang = () => { if (tab === "review" && hd && hdChon) veHd(); };
        const s = document.createElement("script");
        s.src = "/m4/review.js";
        s.onerror = () => { rvTai = false; trangThai("Không tải được màn Review (/m4/review.js) — mở lại bằng MỞ BẢN DEMO.cmd.", true); };
        document.head.append(s);
      }
      return;
    }
    R.ve(vung, {hdId: hdChon, soHd: hd.ho_so.so_hop_dong, dots: hd.dot || [], dotId: dotChon, nguoi: actor()});
  }

  // M4-02B: tab Chứng từ L3 = màn chung_tu.js nguồn đã thích nghi (/m4/chung-tu.js, tải đúng một lần qua route M4); cùng mẫu cầu nối với Review.
  let ctTai = false;
  function veChungTu(box) {  // gọi SAU khi `box` đã gắn vào document (veHd)
    const vung = node("div", undefined, "m4-ct");
    box.append(vung);
    if (!vung.isConnected) return;
    const C = window.kttM4ChungTu;
    if (!C) {
      vung.append(node("p", "Đang tải màn Chứng từ…", "m4-trong"));
      if (!ctTai) {
        ctTai = true;
        window.kttM4ChungTuSanSang = () => { if (tab === "chung_tu" && hd && hdChon) veHd(); };
        const s = document.createElement("script");
        s.src = "/m4/chung-tu.js";
        s.onerror = () => { ctTai = false; trangThai("Không tải được màn Chứng từ (/m4/chung-tu.js) — mở lại bằng MỞ BẢN DEMO.cmd.", true); };
        document.head.append(s);
      }
      return;
    }
    // FIX01: ngữ cảnh fence gồm actor + pháp nhân + dự án + HĐ + đợt (cùng actor đổi sang HĐ dự án/PN khác → màn L3 xóa nháp/lệnh cũ)
    C.ve(vung, {hdId: hdChon, soHd: hd.ho_so.so_hop_dong, dots: hd.dot || [], dotId: dotChon, nguoi: actor(), duAnId: hd.ho_so.du_an_id || null,
      phapNhan: hd.ho_so.phap_nhan || null});
  }

  // M4-02C: tab Duyệt & PDF = module m4_duyet_pdf.js (/m4/m4_duyet_pdf.js, tải đúng một lần qua route M4 — route asset thuộc backend, chưa có trong
  // baseline này: lỗi tải → nói thật "chưa nối"). Shell chỉ chuyển danh tính/PN/dự án/HĐ/đợt; module tự GET/POST theo hợp đồng M4-02C.
  let dpTai = false;
  // FIX01: view Duyệt hợp lệ HIỆN HÀNH = đang ở #m4 + tab Duyệt + HĐ đã nạp. Sẵn sàng/lỗi tải lười về sau khi rời #m4 không mount/GET/đổi trạng thái
  // (vùng ẩn vẫn còn gắn trong document); quay lại #m4 → m4Nap → veHd mount bình thường (module đã nạp) hoặc tải lại (lỗi trước đã nhả dpTai).
  const xemDuyet = () => location.hash === "#m4" && tab === "duyet" && !!hd && !!hdChon;
  function veDuyet(box) {  // gọi SAU khi `box` đã gắn vào document (veHd)
    const vung = node("div", undefined, "m4-dp");
    box.append(vung);
    if (!vung.isConnected || location.hash !== "#m4") return;  // FIX01: không mount module vào trang M4 đã rời (ẩn)
    const D = window.kttM4DuyetPdf;
    if (!D) {
      vung.append(node("p", "Đang tải màn Duyệt & PDF…", "m4-trong"));
      if (!dpTai) {
        dpTai = true;
        window.kttM4DuyetPdfSanSang = () => { if (xemDuyet()) veHd(); };
        const s = document.createElement("script");
        s.src = "/m4/m4_duyet_pdf.js";
        s.onerror = () => {
          dpTai = false;  // nhả để lần mở hợp lệ sau tải lại
          if (!xemDuyet()) return;
          if (vung.isConnected) vung.replaceChildren(node("p", "Chưa nối backend duyệt/PDF: máy chủ chưa phục vụ /m4/m4_duyet_pdf.js — không có lệnh duyệt/PDF nào chạy.", "m4-notice m4-notice-loi"));
          trangThai("Không tải được màn Duyệt & PDF (/m4/m4_duyet_pdf.js) — backend chưa nối.", true);
        };
        document.head.append(s);
      }
      return;
    }
    D.ve(vung, {nguoi: actor(), phapNhanId: hd.ho_so.phap_nhan_id || null, duAnId: hd.ho_so.du_an_id || null, hdId: hdChon, dotId: dotChon,
      soHd: hd.ho_so.so_hop_dong, dots: hd.dot || []});
  }

  // M4-03A: chế độ "Kế toán nghiệm thu" = module m4_ke_toan.js (/m4/m4_ke_toan.js, tải lười đúng một lần qua route M4). Vùng riêng #m4-kt, độc lập
  // HĐ/đợt đang chọn và danh sách HĐ portal: inbox/quyền KT do GET /api/m4/ke-toan của phiên hiện hành quyết định. Shell chỉ chuyển danh tính hiện hành;
  // đổi vai / đổi chế độ / rời #m4 tắt module ĐỒNG BỘ (huy) trước lần vẽ sau. Lỗi tải tài sản → nói thật "chưa nối", không lệnh nào chạy.
  let cheDo = "ho_so", ktTai = false;
  const xemKeToan = () => location.hash === "#m4" && cheDo === "ke_toan" && !!m4 && m4.cau_hinh !== false;
  function tatKeToan() { const T = window.kttM4KeToan; if (T && typeof T.huy === "function") T.huy(); }
  function veCheDoNut() {
    for (const [id, k] of [["m4-cd-ho-so", "ho_so"], ["m4-cd-ke-toan", "ke_toan"]]) {
      const b = $(id); if (!b) continue;
      b.className = k === cheDo ? "m4-chon" : ""; b.setAttribute("aria-selected", String(k === cheDo));
    }
    const luoi = $("m4-luoi"), kt = $("m4-kt");
    if (luoi) luoi.hidden = cheDo !== "ho_so";
    if (kt) kt.hidden = cheDo !== "ke_toan";
  }
  function doiCheDo(moi) {
    if (moi === cheDo) return;
    genForm += 1;
    if (moi === "ke_toan") tatReview(); else tatKeToan();  // rời chế độ nào thì tắt ĐỒNG BỘ module của chế độ đó
    cheDo = moi; veCheDoNut();
    if (cheDo === "ke_toan") veKeToan();
    else { const kt = $("m4-kt"); if (kt) kt.replaceChildren(); veHd(); if (hdChon) napHd(); }
  }
  function veKeToan() {
    const box = $("m4-kt"); if (!box || cheDo !== "ke_toan") return;
    if (!m4) { box.replaceChildren(node("p", "Đang tải…", "m4-trong")); return; }
    if (m4.cau_hinh === false) { box.replaceChildren(node("p", "Chưa kết nối kho DEMO PostgreSQL — Kế toán nghiệm thu chưa đọc được.", "m4-trong")); return; }
    let vung = box.firstChild;
    if (!vung || !vung._ktVung || !vung.isConnected) { vung = node("div", undefined, "m4-kt"); vung._ktVung = true; box.replaceChildren(vung); }
    if (!vung.isConnected || !xemKeToan()) return;
    const T = window.kttM4KeToan;
    if (!T) {
      vung.replaceChildren(node("p", "Đang tải màn Kế toán nghiệm thu…", "m4-trong"));
      if (!ktTai) {
        ktTai = true;
        window.kttM4KeToanSanSang = () => { if (xemKeToan()) veKeToan(); };  // chỉ mount theo ngữ cảnh HIỆN HÀNH lúc callback
        const s = document.createElement("script");
        s.src = "/m4/m4_ke_toan.js";
        s.onerror = () => {
          ktTai = false;  // nhả để lần mở hợp lệ sau tải lại
          if (!xemKeToan()) return;
          const v = $("m4-kt");
          if (v) v.replaceChildren(node("p", "Chưa nối màn Kế toán nghiệm thu: máy chủ chưa phục vụ /m4/m4_ke_toan.js — không có lệnh kế toán nào chạy.", "m4-notice m4-notice-loi"));
          trangThai("Không tải được màn Kế toán nghiệm thu (/m4/m4_ke_toan.js).", true);
        };
        document.head.append(s);
      }
      return;
    }
    T.ve(vung, {nguoi: actor()});
  }

  function veLoTrinh(box) {
    box.append(node("p", "Lộ trình đầy đủ của phần mềm Review hồ sơ xây dựng trong M4 — chỉ trạng thái thật; mục chưa nối không có nút.", "m4-nho"));
    box.append(bang(["Chức năng", "Trạng thái", "Gói"], LO_TRINH.map(([t, s, g]) => [t, pill(s, s === "HIỆN CÓ" ? "m4-du" : "m4-xam"), g])));
  }

  // ------------------------------------------------------------------ khởi động
  dungKhung();
  // M4-02C/M4-03A: rời #m4 → tắt Duyệt & PDF và Kế toán nghiệm thu ĐỒNG BỘ
  window.addEventListener("hashchange", () => { if (location.hash === "#m4") m4Nap(); else { tatDuyet(); tatKeToan(); } });
  if (location.hash === "#m4") m4Nap();
})();
