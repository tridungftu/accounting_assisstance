"use strict";
// M4-04B — widget "Request nháp" trong tab Duyệt & PDF: đọc/điều khiển route riêng /api/m4-request (GET trạng thái, POST tao | doi-soat) của hồ sơ
// đợt ĐÃ SEAL đang xem. Cầu nối m4_duyet_pdf.js chỉ mount khi DTO canonical hợp lệ có seal thật khớp phiên bản đang xem (hiện hành hoặc lịch sử chọn
// tường minh) và gỡ ĐỒNG BỘ khi khóa (ngữ cảnh/thế hệ view/phiên bản/seal/hiện hành) đổi. Placeholder d.request của DTO duyệt KHÔNG là sự thật Request.
// Máy chủ sở hữu MỌI sự thật: danh tính, quyền, cấu hình/transport, người đứng tên, số tiền, intent, sự kiện. Trình duyệt chỉ gửi {dot_id, version_id,
// khoa}. `context` HTTP (M4_REQUEST_HTTP_CONTEXT_V1) phải khớp đúng hồ sơ cha (đợt/phiên bản/login/PN/seal/hiện hành) — lệch → không hiện, không lệnh.
// Số tiền hiển thị là chuỗi seal.so_lieu.so_xin_thanh_toan + tien_te (không Number, không gia_tri_nt); vắng → "(thiếu)". Nháp nhân viên ≠ công nợ.
// Phiên bản lịch sử: chỉ xem trạng thái/lịch sử và đối soát intent đã có (máy chủ chặn mọi POST nguồn); TẠO chỉ ở phiên bản hiện hành.
// Ý định UI: mỗi bấm = MỘT bản ghi (route, body chuỗi gốc, khóa, ngữ cảnh gốc); chỉ ACK có kiểu (schema + context khớp) mới làm rõ bản ghi; chưa rõ
// → chỉ "Gửi lại y nguyên (cùng khóa)"; đang bay → không gửi thêm. Phản hồi về muộn (đổi vai/PN/phiên bản/rời) chỉ cập nhật bản ghi của chính nó.
// Không lưu cục bộ làm authority; mọi chuỗi nguồn hiển thị bằng textContent; không hiện URL/khóa API/người đứng tên.
(() => {
  const K = window.kttChung;
  if (!K) return;  // shell chưa có seam
  const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || "";
  const SCHEMA = "m4.request.nhap/1", CTX_SCHEMA = "M4_REQUEST_HTTP_CONTEXT_V1", VAI = "m4_request_nhap", TOI_DA_Y_DINH = 16;
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;  // chữ thường — đúng dạng máy chủ chấp nhận ở query/body
  const THAP_PHAN = /^-?(0|[1-9]\d*)(\.\d+)?$/, MA = /^[A-Z][A-Z0-9_]{0,63}$/, TIEN_TE = /^[A-Z]{3}$/;
  const laUuid = v => typeof v === "string" && UUID.test(v);
  const laDoiTuong = v => !!v && typeof v === "object" && !Array.isArray(v);
  const CTX_KEYS = ["schema", "dot_id", "version_id", "dang_nhap", "phap_nhan_id", "seal_id", "hien_hanh"];
  const DTO_COT = ["id", "trang_thai", "hold_ma", "nhanh", "parent_id", "seal_id", "phien_ban_id", "so_tien", "tien_te", "nhom", "nhom_phien_ban",
    "remote_id", "remote_ma", "remote_trang_thai", "remote_tep_id", "tep_trang_thai_quet", "co_chua_ro", "so_lan_tao", "so_lan_tai",
    "lan_tao_dau", "pdf_sha256", "pdf_byte_length", "doi_soat_sha256", "revision", "tao_luc", "cap_nhat_luc"];
  // nhãn trạng thái intent (domain) — UNKNOWN/RUNNING/WAIT_SCAN/HOLD hiện rõ, không đoán là đã xong
  const TT = {MOI: ["Mới — chưa gửi", "m4-xam"], CHUA_RO_TAO: ["UNKNOWN — chưa rõ đã tạo", "m4-loi"], TU_CHOI_TAO: ["Chưa tạo (bị từ chối/chưa gửi)", "m4-thieu"],
    DA_TAO: ["Đã tạo — chờ đọc trạng thái", "m4-thieu"], DA_TAO_NHAP: ["Đã tạo nháp — chưa tải PDF", "m4-thieu"],
    CHUA_RO_TAI: ["UNKNOWN — chưa rõ đã tải PDF", "m4-loi"], CHO_QUET: ["WAIT_SCAN — chờ quét tệp", "m4-thieu"],
    DA_DOI_SOAT: ["Đã đối soát khớp", "m4-du"], HOLD: ["HOLD — tạm giữ", "m4-loi"]};
  const KQ = {CHUA_CAU_HINH: "CHUA_CAU_HINH — máy chủ chưa cấu hình Request (không gọi mạng)", CAU_HINH_LECH: "CAU_HINH_LECH — cấu hình lệch nguồn Request",
    LOI_REQUEST: "Nguồn Request báo lỗi", HOLD: "HOLD — tạm giữ"};
  const CHAN = {PHIEN_BAN_KHONG_HIEN_HANH: "phiên bản không còn hiện hành — không tạo/gửi", LICH_SU_CAN_TAO: "phiên bản lịch sử cần TẠO lại — chỉ xem, không gửi",
    LICH_SU_CAN_TAI: "phiên bản lịch sử cần TẢI PDF — chỉ xem, không gửi", LICH_SU_CHUA_CO_Y_DINH: "phiên bản lịch sử chưa có Request — không tạo mới",
    LICH_SU_CHAN_POST: "phiên bản lịch sử — máy chủ chặn mọi gửi lên nguồn, chỉ đọc/đối soát"};
  const HANH = {TAO: {path: "tao", ten: "tạo nháp Request"}, DOI_SOAT: {path: "doi-soat", ten: "đối soát Request"}};
  const MAT_KET_NOI = "Mất kết nối với ứng dụng trên máy — chưa rõ máy chủ đã xử lý hay chưa";
  const h12 = v => (typeof v === "string" && v ? v.slice(0, 12) + "…" : "—");
  const chu = v => (v === null || v === undefined ? "" : String(v));
  const thieuNeu = v => (v === null || v === undefined || v === "" ? "(thiếu)" : String(v));
  const taoKhoa = () => "m4rq-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));

  function el(tag, props, ...con) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === "class") e.className = v; else if (k === "text") e.textContent = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (k === "disabled") e.disabled = !!v; else e.setAttribute(k, v === true ? "" : String(v));
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
  let inc = null, box = null, khoa = "", g = null;  // g: ngữ cảnh gốc đã kiểm từ hồ sơ cha (null = không hợp lệ → không GET/POST)
  let genGet = 0, rs = null, tinh = "CHUA", loiGet = "", statusChu = "", statusLoi = false;  // tinh: CHUA|DANG|OK|SAI|KHONG_QUYEN|LOI
  // bản ghi ý định: id → {loai, ctxKey, version, seal, body, bodyText, khoa, inc, trang (BAY|CHUA_RO|RO), bay, soLan, ketQua}
  const yDinh = new Map();
  let soYDinh = 0;
  const song = () => !!inc && !!box && box.isConnected && !!g;
  function fence() {  // ngữ cảnh GỐC: incarnation + khóa cầu nối + vùng còn gắn
    const i = inc, k = khoa;
    return () => song() && i === inc && k === khoa;
  }
  const recMo = loai => [...yDinh.values()].find(r => r.loai === loai && g && r.ctxKey === g.ctxKey && r.trang !== "RO") || null;
  function donYDinh() { for (const [id, r] of yDinh) { if (yDinh.size <= TOI_DA_Y_DINH) break; if (r.trang === "RO") yDinh.delete(id); } }
  function trangThai(msg, loi = false) {
    statusChu = msg || ""; statusLoi = !!loi;
    const s = box && box.querySelector(".m4-rq-status");
    if (s) { s.textContent = statusChu; s.className = "m4-rq-status m4-status" + (statusLoi ? " m4-loi-chu" : ""); }
  }

  // ------------------------------------------------------------------ ngữ cảnh gốc từ hồ sơ cha (DTO duyệt đã kiểm ở m4_duyet_pdf.js)
  function nguCanh(c) {
    if (!laDoiTuong(c) || typeof c.khoa !== "string" || !c.khoa) return null;
    const d = c.dto;
    if (typeof c.nguoi !== "string" || !c.nguoi || !laDoiTuong(d) || !laDoiTuong(d.context) || !laDoiTuong(d.seal) || d.chua_nop === true) return null;
    const x = d.context, s = d.seal;
    if (!laUuid(x.dot_id) || !laUuid(x.version_id) || !laUuid(x.phap_nhan_id) || !laUuid(s.id) || s.version_id !== x.version_id) return null;
    if (c.phapNhanId !== null && c.phapNhanId !== undefined && c.phapNhanId !== x.phap_nhan_id) return null;
    const sl = laDoiTuong(s.so_lieu) ? s.so_lieu : {};
    const so = typeof sl.so_xin_thanh_toan === "string" && THAP_PHAN.test(sl.so_xin_thanh_toan) ? sl.so_xin_thanh_toan : null;  // chuỗi nguyên văn
    const tt = typeof sl.tien_te === "string" && TIEN_TE.test(sl.tien_te) ? sl.tien_te : null;
    const hien = d.phien_ban_hien_hanh === true;
    return {nguoi: c.nguoi, pn: x.phap_nhan_id, dot: x.dot_id, version: x.version_id, seal: s.id, hienHanh: hien, soTien: so, tienTe: tt,
      ctxKey: JSON.stringify([c.nguoi, x.phap_nhan_id, x.dot_id, x.version_id, s.id])};
  }

  // ------------------------------------------------------------------ kiểm DTO (không tin trường nào ngoài hợp đồng)
  function kiemContext(x) {
    if (!laDoiTuong(x)) return "thiếu context";
    const k = Object.keys(x).sort(), can = [...CTX_KEYS].sort();
    if (k.length !== can.length || k.some((v, i) => v !== can[i])) return "context sai bộ khóa";
    if (x.schema !== CTX_SCHEMA) return "context sai schema";
    if (x.dot_id !== g.dot) return "context khác đợt đang xem";
    if (x.version_id !== g.version) return "context khác phiên bản đang xem";
    if (x.dang_nhap !== g.nguoi) return "context khác người đăng nhập đang mở";
    if (x.phap_nhan_id !== g.pn) return "context khác pháp nhân";
    if (x.seal_id !== g.seal) return "context khác seal của hồ sơ đang xem";
    if (x.hien_hanh !== g.hienHanh) return "context khác trạng thái hiện hành của hồ sơ";
    return null;
  }
  function kiemYDinh(y, coSuKien) {
    if (!laDoiTuong(y)) return "intent sai kiểu";
    for (const k of DTO_COT) if (!(k in y)) return "intent thiếu " + k;
    if (!laUuid(y.id) || typeof y.trang_thai !== "string" || !(y.trang_thai in TT)) return "intent sai id/trạng thái";
    if (y.seal_id !== null && !laUuid(y.seal_id)) return "intent sai seal";
    if (y.phien_ban_id !== null && !laUuid(y.phien_ban_id)) return "intent sai phiên bản";
    if (y.so_tien !== null && !(typeof y.so_tien === "string" && THAP_PHAN.test(y.so_tien))) return "intent số tiền không phải chuỗi thập phân";
    if (typeof y.dang_xu_ly !== "boolean") return "intent thiếu dang_xu_ly";
    if (coSuKien) {
      if (!Array.isArray(y.su_kien) || y.su_kien.some(s => !laDoiTuong(s))) return "intent thiếu lịch sử sự kiện";
    } else if ("su_kien" in y) return "kết quả lệnh có su_kien";
    return null;
  }
  function kiemXem(d) {
    if (!laDoiTuong(d) || d.schema !== SCHEMA) return "schema lạ";
    const q = d.quyen;
    if (!laDoiTuong(q) || ["tao", "tai_pdf", "anh_xa"].some(k => typeof q[k] !== "boolean")) return "quyền không tường minh";
    const ch = d.cau_hinh;
    if (ch !== null && !(laDoiTuong(ch) && (ch.trang_thai === "CHUA_CAU_HINH" || ch.trang_thai === "SAN_SANG") && Array.isArray(ch.thieu)
      && ch.thieu.every(t => typeof t === "string"))) return "cấu hình sai dạng";
    if (!Array.isArray(d.y_dinh)) return "thiếu danh sách intent";
    for (const y of d.y_dinh) { const s = kiemYDinh(y, true); if (s) return s; }
    return kiemContext(d.context);
  }
  function kiemKetQua(a) {  // ACK có kiểu của lệnh: schema domain + context HTTP khớp ngữ cảnh gốc
    if (!laDoiTuong(a) || a.schema !== SCHEMA) return "schema lạ";
    if (typeof a.trang_thai !== "string" || !MA.test(a.trang_thai) || typeof a.lap_lai !== "boolean") return "trạng thái kết quả sai";
    if (a.chan !== null && a.chan !== undefined && (typeof a.chan !== "string" || !MA.test(a.chan))) return "mã chặn sai";
    if (!Array.isArray(a.buoc) || !Array.isArray(a.loi)) return "thiếu bước/lỗi";
    if (a.y_dinh !== null) { const s = kiemYDinh(a.y_dinh, false); if (s) return s; }
    if (a.y_dinh && (a.y_dinh.seal_id !== g.seal || a.y_dinh.phien_ban_id !== g.version)) return "intent khác seal/phiên bản đang xem";
    return kiemContext(a.context);
  }
  const intentCuaSeal = () => (rs ? rs.y_dinh.filter(y => y.seal_id === g.seal && y.phien_ban_id === g.version) : []);

  // ------------------------------------------------------------------ GET trạng thái (luôn gửi phiên bản đang xem)
  async function napLai() {
    if (!song()) return;
    if (K.vaiDangChan(VAI)) return;  // đổi vai đang chờ — không GET dưới vai cũ
    const f = fence(), gen = ++genGet, moiNhat = () => f() && gen === genGet;
    const q = new URLSearchParams({dot_id: g.dot, version_id: g.version});
    tinh = rs ? tinh : "DANG"; ve_();
    let res, e = {};
    try { res = await fetch("/api/m4-request?" + q.toString(), {headers: {"X-KTT-Token": TOKEN}, cache: "no-store", credentials: "same-origin"}); }
    catch (_) { if (moiNhat()) { tinh = rs ? "OK" : "LOI"; loiGet = MAT_KET_NOI; trangThai(MAT_KET_NOI + " — chưa đọc được trạng thái Request.", true); ve_(); } return; }
    if (!moiNhat()) return;
    let d = null, doc = true;
    try { d = await res.json(); } catch (_) { doc = false; }
    if (!moiNhat()) return;
    if (!res.ok) {
      e = doc && laDoiTuong(d) ? d : {};
      rs = null;
      if (res.status === 403 || res.status === 404) { tinh = "KHONG_QUYEN"; loiGet = e.message || e.error || `HTTP ${res.status}`; }
      else { tinh = "LOI"; loiGet = (e.error ? e.error + ": " : "") + (e.message || `máy chủ trả ${res.status}`); }
      ve_(); return;
    }
    const sai = doc ? kiemXem(d) : "phản hồi đọc không trọn";
    if (sai) { rs = null; tinh = "SAI"; loiGet = sai; ve_(); return; }
    rs = d; tinh = "OK"; loiGet = ""; ve_();
  }

  // ------------------------------------------------------------------ lệnh (bản ghi ý định chính xác)
  function lyDoTat(loai) {
    if (!song() || tinh !== "OK" || !rs) return "Chưa đọc được trạng thái Request hợp lệ";
    const q = rs.quyen, ds = intentCuaSeal();
    if (!q.tai_pdf) return "Vai hiện hành không được tạo/đối soát Request";
    if (loai === "TAO") {
      if (!g.hienHanh) return "Phiên bản lịch sử — chỉ xem; tạo Request chỉ ở phiên bản hiện hành";
      if (!q.tao) return "Vai hiện hành không có quyền tạo Request";
      if (!rs.cau_hinh || rs.cau_hinh.trang_thai !== "SAN_SANG") return "Máy chủ chưa cấu hình Request (CHUA_CAU_HINH)";
      if (ds.length) return "Seal này đã có intent Request — dùng Đối soát";
      if (g.soTien === null || g.tienTe === null) return "Seal thiếu số xin thanh toán/tiền tệ";
    } else if (!ds.length) return "Chưa có intent Request của seal này";
    if (ds.some(y => y.dang_xu_ly)) return "Máy chủ đang xử lý intent này (RUNNING) — chờ rồi làm mới";
    const r = recMo(loai);
    if (r) return r.bay ? "Đang gửi lệnh này — chờ kết quả" : "Lệnh trước chưa rõ kết quả — bấm Gửi lại y nguyên";
    return null;
  }
  function taoYDinh(loai) {  // ĐỒNG BỘ trong handler, trước await đầu tiên
    if (yDinh.size >= TOI_DA_Y_DINH) { donYDinh(); if (yDinh.size >= TOI_DA_Y_DINH) { trangThai("Quá nhiều lệnh chưa rõ kết quả — Gửi lại y nguyên các lệnh đó trước.", true); return null; } }
    const k = taoKhoa(), body = {dot_id: g.dot, version_id: g.version, khoa: k};
    const rec = {id: ++soYDinh, loai, ctxKey: g.ctxKey, version: g.version, seal: g.seal, g: {...g}, khoa: k, body, bodyText: JSON.stringify(body),
      inc, trang: "MOI", bay: null, soLan: 0, ketQua: null};
    yDinh.set(rec.id, rec);
    return rec;
  }
  function phanLoai(status, e, a) {
    if (a) return {loai: "OK", status, ack: a};
    if (status === 403 || status === 404) return {loai: "MAT_QUYEN", status, code: e.error || "HTTP_" + status, msg: e.message || ""};
    if (status === 409 && e.error === "M4_REQUEST_DANG_XU_LY") return {loai: "DANG_XU_LY", msg: e.message || ""};
    if (status === 409 && e.error === "M4_REQUEST_PHIEN_DOI") return {loai: "CHUA_RO", msg: "phiên đăng nhập đã đổi trong lúc xử lý"};
    if (status >= 500 || e.error === "M4_KET_QUA_CHUA_RO") return {loai: "CHUA_RO", msg: e.message || `máy chủ trả ${status} không kèm kết quả có kiểu`};
    return {loai: "LOI", status, code: e.error || "HTTP_" + status, msg: e.message || `Không hoàn tất (${status}).`};
  }
  async function phat(rec) {  // gửi (hoặc Gửi lại) ĐÚNG bản ghi: cùng route + body chuỗi + khóa
    if (rec.bay) { trangThai(`Đang ${HANH[rec.loai].ten} — chờ kết quả, không gửi thêm.`); return; }
    const tk = {}, f = fence(), ten = HANH[rec.loai].ten;
    rec.bay = tk; rec.trang = "BAY"; rec.inc = inc; rec.soLan += 1;
    trangThai(`Đang ${ten}… (có thể lâu — máy chủ gọi nguồn Request ngoài khóa chung)`); ve_();
    let kq;
    try {
      const res = await fetch("/api/m4-request/" + HANH[rec.loai].path,
        {method: "POST", headers: {"X-KTT-Token": TOKEN, "Content-Type": "application/json"}, body: rec.bodyText, cache: "no-store", credentials: "same-origin"});
      let d = null, doc = true;
      try { d = await res.json(); } catch (_) { doc = false; }
      if (!doc) kq = {loai: "CHUA_RO", msg: "phản hồi đọc không trọn"};
      else {
        const coKieu = laDoiTuong(d) && d.schema === SCHEMA;
        let sai = null;
        if (coKieu) { const g0 = g; g = rec.g; try { sai = kiemKetQua(d); } finally { g = g0; } }  // kiểm theo ngữ cảnh GỐC của bản ghi
        if (coKieu && !sai) kq = phanLoai(res.status, d, d);
        else if (res.ok || coKieu) kq = {loai: "CHUA_RO", msg: "phản hồi không đúng hợp đồng (" + (sai || "schema lạ") + ")"};
        else kq = phanLoai(res.status, laDoiTuong(d) ? d : {}, null);
      }
    } catch (_) { kq = {loai: "CHUA_RO", msg: MAT_KET_NOI}; }
    if (rec.bay !== tk) return;
    rec.bay = null;
    if (kq.loai === "OK") { rec.trang = "RO"; rec.ketQua = kq.ack; }
    else if (kq.loai === "CHUA_RO") rec.trang = "CHUA_RO";
    else rec.trang = "RO";  // lỗi chắc chắn (4xx có mã) / mất quyền / đang xử lý: không còn gì để gửi lại y nguyên
    donYDinh();
    if (!f()) {  // vai/PN/phiên bản/seal/vùng đã đổi: KHÔNG toast/trạng thái/GET; chỉ vẽ lại hàng ý định nếu đúng phạm vi gốc đang mở lại
      if (song() && g.ctxKey === rec.ctxKey && rec.inc !== inc) ve_();
      return;
    }
    if (kq.loai === "OK") {
      const a = kq.ack, lai = a.lap_lai ? " (kết quả cũ của cùng khóa — không gửi thêm)" : "";
      const nhan = KQ[a.trang_thai] || (TT[a.trang_thai] ? TT[a.trang_thai][0] : a.trang_thai);
      const msg = `Kết quả ${ten}: ${nhan}${a.chan ? " — " + (CHAN[a.chan] || a.chan) : ""}${lai}.`;
      const xau = a.trang_thai === "HOLD" || a.trang_thai === "LOI_REQUEST" || a.trang_thai === "CAU_HINH_LECH" || a.trang_thai === "CHUA_CAU_HINH" || /^CHUA_RO/.test(a.trang_thai);
      K.toast(msg, xau); trangThai(msg, xau);
      ve_();
      await napLai();
      return;
    }
    if (kq.loai === "CHUA_RO") {
      const msg = `Chưa rõ kết quả ${ten}: ${kq.msg}. Không coi là đã tạo/tải; khóa gốc được giữ — bấm Gửi lại y nguyên (cùng khóa) để máy chủ đối soát.`;
      K.toast(msg, true); trangThai(msg, true); ve_(); return;
    }
    if (kq.loai === "MAT_QUYEN") {
      rs = null; tinh = "KHONG_QUYEN"; loiGet = kq.msg || kq.code;
      trangThai((kq.msg || "Không có quyền") + " — đã gỡ trạng thái và lệnh Request khỏi màn hình (máy chủ kiểm quyền hiện hành).", true); ve_(); return;
    }
    if (kq.loai === "DANG_XU_LY") {
      trangThai("RUNNING — máy chủ đang xử lý intent này ở một lệnh khác; đã đọc lại trạng thái, không gửi thêm.", true);
      await napLai(); return;
    }
    K.toast(kq.msg, true); trangThai(`${kq.code}: ${kq.msg}`, true);
    await napLai();
  }
  function bam(loai) {
    if (K.vaiDangChan(VAI)) { trangThai("Đang đổi vai — chưa gửi lệnh.", true); return; }
    const tat = lyDoTat(loai);
    if (tat) { trangThai(tat + ".", true); return; }
    const rec = taoYDinh(loai);
    if (rec) phat(rec);
  }
  function guiLai(rec) {  // chỉ ở đúng ngữ cảnh gốc (vai/PN/đợt/phiên bản/seal), trạng thái đọc hợp lệ
    if (!song() || rec.ctxKey !== g.ctxKey || tinh !== "OK" || K.vaiDangChan(VAI)) {
      trangThai("Lệnh chưa rõ thuộc ngữ cảnh khác hoặc chưa đọc lại được trạng thái — không gửi lại.", true); return;
    }
    if (rec.trang !== "CHUA_RO") { trangThai(rec.bay ? "Đang gửi lại lệnh này — chờ kết quả." : "Lệnh này đã có kết quả.", true); return; }
    if (!rs.quyen.tai_pdf || (rec.loai === "TAO" && (!rs.quyen.tao || !g.hienHanh))) {
      trangThai("Vai/phiên bản hiện hành không còn cho lệnh này — lệnh chưa rõ được giữ nguyên (cùng khóa), chưa gửi lại.", true); return;
    }
    phat(rec);
  }

  // ------------------------------------------------------------------ vẽ
  function veIntent(y) {
    const [nhan, cls] = TT[y.trang_thai];
    const p = [pill(nhan, cls)];
    if (y.dang_xu_ly) p.push(pill("RUNNING — đang xử lý", "m4-thieu"));
    if (y.trang_thai === "HOLD" && y.hold_ma) p.push(el("span", {text: "mã giữ " + y.hold_ma}));
    const hang = el("div", {class: "m4-hang"}, ...p);
    const ct = bang(["Mục", "Giá trị (máy chủ)"], [
      ["Intent", h12(y.id)], ["Mã Request nguồn", thieuNeu(y.remote_ma)], ["Trạng thái nguồn", thieuNeu(y.remote_trang_thai)],
      ["Quét tệp", thieuNeu(y.tep_trang_thai_quet)], ["Số tiền đã gửi", y.so_tien === null ? "(thiếu)" : `${y.so_tien} ${chu(y.tien_te)}`.trim()],
      ["Số lần tạo / tải", `${chu(y.so_lan_tao)} / ${chu(y.so_lan_tai)}`], ["Cập nhật", y.cap_nhat_luc ? K.date(y.cap_nhat_luc) : "—"]]);
    const ls = y.su_kien.length ? bang(["#", "Bước", "Từ", "Đến", "Lúc"],
      y.su_kien.map(s => [chu(s.thu_tu), chu(s.buoc), chu(s.tu_trang_thai), chu(s.den_trang_thai), s.luc ? K.date(s.luc) : ""])) : nho("Chưa có sự kiện.");
    return [hang, ct, ls];
  }
  function veYDinh() {
    if (!g) return [];
    return [...yDinh.values()].filter(r => r.ctxKey === g.ctxKey && (r.trang === "BAY" || r.trang === "CHUA_RO")).map(r => {
      const ten = HANH[r.loai].ten;
      if (r.bay) return el("div", {class: "m4-hang m4-rq-ydinh"}, nho(r.inc === inc ? `Đang ${ten} — chờ kết quả, không gửi thêm.`
        : `Lệnh ${ten} của lần mở trước còn đang chờ phản hồi — chưa gửi thêm.`));
      return el("div", {class: "m4-hang m4-rq-ydinh"}, el("span", {text: `UNKNOWN — chưa rõ kết quả ${ten} (khóa ${r.khoa.slice(0, 13)}…, đã gửi ${r.soLan} lần). `}),
        nut("Gửi lại y nguyên (cùng khóa)", () => guiLai(r), "m4-chinh", tinh !== "OK"));
    });
  }
  function ve_() {
    if (!inc || !box || !box.isConnected) return;
    const out = [el("div", {class: "m4-hang"}, el("h3", {text: "Request nháp thanh toán (nhân viên)"}), g ? nut("↻ Trạng thái Request", () => napLai(), "", false) : null)];
    out.push(el("p", {class: "m4-rq-status m4-status" + (statusLoi ? " m4-loi-chu" : ""), role: "status", "aria-live": "polite", text: statusChu}));
    if (!g) {
      out.push(el("div", {class: "m4-notice m4-notice-loi", role: "alert", text: "Ngữ cảnh hồ sơ không hợp lệ cho Request nháp — không đọc/gửi gì."}));
      box.replaceChildren(el("section", {class: "m4-card m4-dp-request-the"}, ...out)); return;
    }
    out.push(el("div", {class: "m4-hang"}, el("span", {text: "Số xin thanh toán theo seal: "}),
      el("strong", {text: g.soTien === null ? "(thiếu)" : g.soTien}), el("span", {text: " " + thieuNeu(g.tienTe)}),
      pill(g.hienHanh ? "Phiên bản hiện hành" : "Phiên bản lịch sử — chỉ xem", g.hienHanh ? "m4-du" : "m4-xam")));
    out.push(nho("Request nháp của nhân viên — không phải công nợ đã ghi; kế toán xác nhận độc lập ở nhánh KT."));
    if (tinh === "KHONG_QUYEN") out.push(el("div", {class: "m4-notice m4-notice-loi", role: "alert", text: `Không có quyền xem/thao tác Request của đợt này${loiGet ? ": " + loiGet : ""}.`}));
    else if (tinh === "SAI") out.push(el("div", {class: "m4-notice m4-notice-loi", role: "alert", text: `Phản hồi Request không đúng hợp đồng (${loiGet}) — không hiển thị và không cho thao tác.`}));
    else if (tinh === "LOI" && !rs) out.push(el("div", {class: "m4-notice m4-notice-loi", text: loiGet || "Chưa đọc được trạng thái Request."}));
    else if (!rs) out.push(el("p", {class: "m4-trong", text: "Đang tải trạng thái Request…"}));
    if (rs && tinh === "OK") {
      const ch = rs.cau_hinh;
      if (ch && ch.trang_thai === "CHUA_CAU_HINH") out.push(el("div", {class: "m4-notice m4-notice-loi", text: "CHUA_CAU_HINH — máy chủ chưa cấu hình Request" +
        (ch.thieu.length ? " (thiếu: " + ch.thieu.join(", ") + ")" : "") + "; không có gọi mạng nào."}));
      const ds = intentCuaSeal();
      if (!ds.length) out.push(el("p", {class: "m4-trong", text: "Seal này chưa có Request nháp."}));
      for (const y of ds) out.push(...veIntent(y));
      const khac = rs.y_dinh.length - ds.length;
      if (khac > 0) out.push(nho(`Đợt còn ${khac} intent Request của seal/phiên bản khác — mở đúng phiên bản đó để xem.`));
      const tatT = lyDoTat("TAO"), tatD = lyDoTat("DOI_SOAT");
      out.push(el("div", {class: "m4-hang"}, nut("Tạo nháp Request", () => bam("TAO"), "m4-chinh", !!tatT, tatT),
        nut("Đối soát Request", () => bam("DOI_SOAT"), "", !!tatD, tatD)));
      if (tatT) out.push(nho("Tạo: " + tatT + "."));
      if (!g.hienHanh && ds.length) out.push(nho("Phiên bản lịch sử: đối soát chỉ đọc/tải về từ nguồn; nếu intent cần tạo/tải lại, máy chủ trả HOLD và giữ nguyên intent gốc."));
    }
    out.push(...veYDinh());
    box.replaceChildren(el("section", {class: "m4-card m4-dp-request-the"}, ...out));
  }

  // ------------------------------------------------------------------ vòng đời
  function huy() {  // ĐỒNG BỘ: GET/POST về muộn bị fence chặn; bản ghi ý định giữ theo phạm vi gốc (chỉ hiện lại ở đúng ngữ cảnh đó)
    inc = null; box = null; khoa = ""; g = null; genGet += 1;
    rs = null; tinh = "CHUA"; loiGet = ""; statusChu = ""; statusLoi = false;
  }
  K.dangKyVai(VAI, huy, () => {});  // nạp lại do cầu nối Duyệt & PDF mount lại sau đổi vai
  window.kttM4RequestNhap = Object.freeze({
    ve(vung, c) {
      const k = c && typeof c.khoa === "string" ? c.khoa : "";
      const moi = !inc || k !== khoa;
      if (moi) { huy(); inc = {}; khoa = k; g = nguCanh(c); }
      box = vung;
      ve_();
      if (moi && g) napLai();
    },
    huy,
  });
  if (typeof window.kttM4RequestNhapSanSang === "function") window.kttM4RequestNhapSanSang();
})();
