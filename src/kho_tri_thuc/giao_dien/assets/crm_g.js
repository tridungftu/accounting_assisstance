"use strict";
// CRM-41-02 — S6 trong shell CRM hiện có (#page-hopdong → #crm-g): G1 mẫu DOCX (tải lên → phát hiện ô → ánh xạ/phiên bản → xem thử dữ liệu giả →
// KT kiểm/Trả lại → CFO duyệt/Từ chối → so sánh → tải tệp gốc) và G7 bộ chuẩn dự án 4 cột (KT lập/gửi → CFO duyệt → đọc theo ngày).
// Chỉ gọi route/DTO thật của giao_dien/crm_g.py + k2/crm_mau.py. Danh tính/PN/quyền/facts/hash/trạng thái do máy chủ trả; trình duyệt chỉ gửi
// ID/token/khóa/ánh xạ/lý do/ngày/bytes. Mọi chuỗi nguồn hiển thị bằng textContent.
// Đổi vai: selector CRM hiện có qua cổng chung window.kttChung (xóa đồng bộ, barrier GET, ý định mới nhất thắng).
// TIEP-01: mọi ô nhập ghi xuyên vào `nhapGt` (vẽ lại không mất nháp); ý định tải lên được GIỮ CHỖ đồng bộ trước POST đầu tiên (một File/
// header/khóa gốc), fence = epoch + actor + thế hệ form tải lên (đổi tệp/loại/mã/tab/phiên bản/vai ⇒ vô hiệu); GET bộ chuẩn theo thế hệ +
// truy vấn + tab — chỉ lựa chọn mới nhất được vẽ.
(() => {
  const K = window.kttChung;
  if (!K) return;  // shell chưa có seam
  const $ = id => document.getElementById(id);
  const node = K.node;
  const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || "";
  const goc = $("crm-g");
  if (!goc) return;

  const TT_MAU = {DRAFT: "Nháp", CHO_KIEM: "Chờ kế toán kiểm", CHO_CFO: "Chờ CFO duyệt", HIEU_LUC: "Đã duyệt (hiệu lực)", TU_CHOI: "CFO từ chối"};
  const TT_CHUAN = {DRAFT: "Nháp", CHO_CFO: "Chờ CFO duyệt", HIEU_LUC: "Đã duyệt (hiệu lực)"};
  const LOAI_PHAN = {THAN: "Thân văn bản", HEADER: "Đầu trang", FOOTER: "Chân trang"};
  const LY_DO_DOC = {TRACK_CHANGES: "Còn Track Changes", KENH_CHUA_HO_TRO: "Có hộp văn bản/trường (field) chưa hỗ trợ", NGOAC_LE: "Có dấu {{ hoặc }} lẻ",
    KENH_CHUA_QUET: "Phần chưa quét (chú thích/nhận xét…) có dấu { }", DOAN_QUA_DAI: "Đoạn văn quá dài",
    SIEU_DU_LIEU_MAU_THUAN: "Quan hệ/loại nội dung/phần tử gốc của một phần mâu thuẫn"};
  const COT_DONG = ["lan", "gl", "tp", "st", "tt", "ml", "mn", "ms", "gc"];

  // ------------------------------------------------------------------ trạng thái
  let ep = 0, genDs = 0, genCt = 0, genBc = 0, genDoc = 0, genForm = 0, genTai = 0;
  let ds = null, ct = null, pbChon = null, tab = "mau", xemThu = null, soSanh = null, bc = null, bcDoc = null, soDong = 1, taiTep = null;
  const nhapGt = new Map();       // id ô → giá trị nháp (ghi xuyên; vẽ lại đọc từ đây)
  const khoaMap = new Map();      // (route, body gốc) → {khoa, chu}: giữ khóa đến khi có kết quả thật
  const taiDang = new Map();      // ý định tải lên (giữ chỗ đồng bộ) → {File gốc, header gốc, khóa gốc, fence}
  const actor = () => (ds && ds.nguoi && ds.nguoi.dang_nhap) || null;
  const taoKhoa = () => "crmg-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));
  function fence(them) { const e = ep, a = actor(); return () => e === ep && a === actor() && (!them || them()); }
  const formCon = () => { const g = genForm; return () => g === genForm; };

  class LoiG extends Error { constructor(status, code, message) { super(message); this.status = status; this.code = code; } }
  async function goi(path, opts = {}) {
    let res;
    try { res = await fetch(path, {...opts, headers: {"X-KTT-Token": TOKEN, ...(opts.headers || {})}, cache: "no-store", credentials: "same-origin"}); }
    catch (_) { throw new LoiG(0, "MAT_KET_NOI", "Mất kết nối với ứng dụng — chưa xác định máy chủ đã ghi hay chưa. Khóa và nội dung được giữ; bấm Gửi lại y nguyên."); }
    if (!res.ok) {
      const r = await res.json().catch(() => ({}));
      throw new LoiG(res.status, r.error || "HTTP_" + res.status, r.message || `Không hoàn tất yêu cầu (${res.status}).`);
    }
    return res;
  }
  async function docJson(res) {
    try { return await res.json(); }
    catch (_) { throw new LoiG(0, "KET_QUA_CHUA_RO", "Phản hồi đọc không trọn — chưa rõ lệnh đã ghi hay chưa. Khóa được giữ; bấm Gửi lại y nguyên."); }
  }
  const postJson = async (ten, body) => docJson(await goi("/api/crm/" + ten, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)}));
  const chuaRo = e => !!e && (e.status === 0 || e.status >= 500) && e.code !== "CRM_G_CHUA_SAN_SANG";

  // ------------------------------------------------------------------ tiện ích hiển thị + ô nhập ghi xuyên
  let oTrangThai = null, oGuiLai = null, oNoiDung = null;
  function trangThai(msg, loi = false) { if (oTrangThai) { oTrangThai.textContent = msg || ""; oTrangThai.className = "upload-status" + (loi ? " error" : ""); } }
  const pill = (text, cls) => node("span", text, "pill " + (cls || "neutral"));
  const h12 = h => h ? String(h).slice(0, 12) + "…" : "—";
  function bang(headers, rows) {
    const wrap = node("div", undefined, "table-wrap"), t = node("table"), head = node("thead"), tr = node("tr"), body = node("tbody");
    headers.forEach(x => tr.append(node("th", x))); head.append(tr); t.append(head);
    for (const r of rows) {
      const row = node("tr");
      for (const c of r) { const td = node("td"); if (c instanceof Node) td.append(c); else td.textContent = c === null || c === undefined ? "" : String(c); row.append(td); }
      body.append(row);
    }
    t.append(body); wrap.append(t); return wrap;
  }
  function nut(text, fn, cls, tat) {
    const b = node("button", text, cls || "button secondary"); b.type = "button"; b.disabled = !!tat;
    b.addEventListener("click", () => { if (!b.disabled) fn(b); }); return b;
  }
  const gt = (id, macDinh = "") => nhapGt.has("crmg-" + id) ? nhapGt.get("crmg-" + id) : macDinh;
  function o(id, el, macDinh = "", khiDoi) {  // ô có nháp ghi xuyên; mọi sửa tăng thế hệ form (+ hook riêng)
    el.id = "crmg-" + id;
    if (!nhapGt.has(el.id)) nhapGt.set(el.id, macDinh);
    if (el.type !== "file") el.value = nhapGt.get(el.id);
    const doi = () => { if (el.type !== "file") nhapGt.set(el.id, el.value); genForm += 1; if (khiDoi) khiDoi(el); };
    el.addEventListener("input", doi); el.addEventListener("change", doi);
    return el;
  }
  function truong(label, el) { const l = node("label", label); l.htmlFor = el.id; return [l, el]; }
  function nhap(id, macDinh, type = "text", khiDoi) { const i = node("input"); i.type = type; i.autocomplete = "off"; return o(id, i, macDinh ?? "", khiDoi); }
  function chon(id, options, macDinh, dau, khiDoi) {
    const s = node("select");
    if (dau !== undefined) { const op = node("option", dau); op.value = ""; s.append(op); }
    for (const [v, t] of options) { const op = node("option", t); op.value = v; s.append(op); }
    return o(id, s, macDinh ?? "", khiDoi);
  }
  function xoaNhap(tienTo) { for (const k of [...nhapGt.keys()]) if (k.startsWith("crmg-" + tienTo)) nhapGt.delete(k); }
  const homNay = () => new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10);
  function giaTri(r) {
    if (r.gia_tri_loai === "PERCENT") return `${r.gia_tri_thap_phan}%`;
    if (r.gia_tri_loai === "AMOUNT") return `${r.so_tien_minor} ${r.tien_te} (đơn vị nhỏ nhất)`;
    return "— (chưa có giá trị)";
  }
  function moc(r) {
    if (r.moc_loai === "NGAY") return `Ngày ${r.moc_ngay}`;
    if (r.moc_loai === "SU_KIEN") return `Sự kiện: ${r.moc_su_kien}`;
    return "— (chưa có mốc)";
  }
  const bangChuan = (cot, rows) => bang(cot, rows.map(r => [r.lan, giaTri(r), moc(r), r.ghi_chu || ""]));

  // ------------------------------------------------------------------ lệnh JSON có khóa
  function nhanBanGhi(k) {
    let rec = khoaMap.get(k);
    if (rec && rec.chu) return null;  // lần gửi trước còn bay: bấm lặp không gửi thêm
    if (!rec) { rec = {khoa: taoKhoa(), chu: null}; khoaMap.set(k, rec); }
    const ve = {}; rec.chu = ve; return {rec, ve};
  }
  function traBanGhi(k, rec, ve, xong) {
    if (rec.chu === ve) rec.chu = null;
    if (xong && khoaMap.get(k) === rec) khoaMap.delete(k);
  }
  async function gui(path, body, ok, f, coKhoa = true) {
    if (!f()) { trangThai("Thao tác thuộc vai/lựa chọn cũ — không gửi.", true); return null; }
    const k = JSON.stringify([path, body]), so = nhanBanGhi(k);
    if (!so) return null;
    const {rec, ve} = so, full = coKhoa ? {...body, khoa: rec.khoa} : body;
    veGuiLai(null); trangThai("Đang gửi…");
    let xong = false;
    try {
      const r = await postJson(path, full);
      xong = true;
      if (!f()) return null;
      const lai = r && r.lap_lai ? " (biên nhận cũ của cùng yêu cầu — không ghi thêm)" : "";
      if (ok) { K.toast(ok + lai); trangThai(ok + lai); }
      return r;
    } catch (e) {
      if (!chuaRo(e)) xong = true;  // lỗi chắc chắn: máy chủ từ chối, khóa chưa dùng
      if (!f()) return null;
      xuLyLoi(e, {path, body, ok, f, coKhoa});
      return null;
    } finally { traBanGhi(k, rec, ve, xong); }
  }
  function xuLyLoi(e, lai) {
    const msg = (e && e.message) || String(e);
    K.toast(msg, true); trangThai(msg, true);
    if (e && e.status === 409 && e.code === "CRM_G_TOKEN_CU") { trangThai(msg + " Đã tải lại dữ liệu hiện hành — kiểm tra rồi thao tác lại (nháp được giữ).", true); napCt(); }
    if (lai && chuaRo(e)) veGuiLai(lai);
  }
  function veGuiLai(lai) {
    if (!oGuiLai) return;
    if (oGuiLai.dataset.tep) return;  // đang giữ nút gửi lại TỆP chưa rõ — không đè
    if (!lai) { oGuiLai.replaceChildren(); return; }
    oGuiLai.replaceChildren(node("span", "Chưa rõ kết quả lần gửi trước. "), nut("Gửi lại y nguyên (cùng khóa)", async () => {
      if (!lai.f()) { oGuiLai.replaceChildren(); trangThai("Lệnh chưa rõ kết quả thuộc vai/lựa chọn cũ — không gửi lại.", true); return; }
      const r = await gui(lai.path, lai.body, lai.ok, lai.f, lai.coKhoa);
      if (r && lai.f()) await napLai();
    }, "button primary"));
  }
  async function sauLenh(fc, f) {
    if (!f()) return;
    if (fc()) { await napLai(); return; }
    trangThai("Lệnh đã hoàn tất — form đã đổi trong lúc chờ nên chưa làm mới; bấm ↻ Làm mới khi xong.");
  }
  async function napLai() { await napDs(); if (pbChon) await napCt(); if (tab === "chuan") await napBc(); }

  // ------------------------------------------------------------------ tải lên mẫu (U01/U02)
  // Một ý định = context gốc (epoch + actor + thế hệ form tải lên genTai) + File GỐC + header/khóa gốc. Giữ chỗ ĐỒNG BỘ trong handler click,
  // trước await đầu tiên: bấm lặp cùng context/tệp → cùng ý định (đang gửi → 0 POST thêm). Chưa rõ kết quả → gửi lại ĐÚNG ý định đó.
  // Đổi tệp/loại/mã/tab/phiên bản/vai ⇒ genTai/ep tăng ⇒ mọi ý định cũ hết hiệu lực (không gửi lại, không toast/chọn/làm mới).
  // TIEP-03 (N06): QUYỀN SỞ HỮU theo ĐỐI TƯỢNG ý định, không theo chuỗi metadata. Mỗi ý định có `id` riêng (bộ đếm) và khóa Map gồm cả `genForm`,
  // nên hai ý định kế tiếp cùng tệp/loại/mã (A cũ, B mới sau khi sửa form) là HAI chủ khác nhau. Nút gửi lại tệp thuộc đúng MỘT chủ (`chuNutTep`,
  // so bằng tham chiếu đối tượng). Callback phản hồi/lỗi/finally của A chỉ dọn Map-entry/nút/inflight mà CHÍNH A đang sở hữu — không thể xóa,
  // vô hiệu hay thay khóa/nút gửi lại/trạng thái đang gửi của B. Vô hiệu TOÀN BỘ chỉ xảy ra ở sự kiện context chung (đổi tệp/loại/mã/tab/
  // phiên bản/vai, lỗi an ninh) qua huyYDinhTai.
  let soYDinh = 0, chuNutTep = null;
  function veNutTep(y) {  // nút gửi lại tệp thuộc ý định y (thay chủ trước nếu có — chủ trước đã không còn là ý định chưa rõ hiện hành)
    if (!oGuiLai) return;
    chuNutTep = y;
    oGuiLai.dataset.tep = String(y.id);
    oGuiLai.replaceChildren(node("span", `Chưa rõ kết quả tải ${y.file.name}. `), nut("Gửi lại tệp y nguyên (cùng khóa)", () => guiTai(y), "button primary"));
  }
  function goNutTep(y) {  // chỉ chủ hiện hành mới gỡ được nút
    if (chuNutTep !== y) return;
    chuNutTep = null;
    if (oGuiLai) { oGuiLai.replaceChildren(); delete oGuiLai.dataset.tep; }
  }
  function huyYDinhTai() {
    for (const y of taiDang.values()) y.het = true;
    taiDang.clear();
    if (chuNutTep) { chuNutTep.het = true; goNutTep(chuNutTep); }
  }
  function doiFormTai() { genTai += 1; huyYDinhTai(); }
  function boYDinh(y, msg) {
    if (taiDang.get(y.intent) === y) taiDang.delete(y.intent);  // chỉ Map-entry do chính y giữ
    y.het = true;
    goNutTep(y);  // chỉ nút do chính y sở hữu
    if (msg) trangThai(msg, true);
  }
  function giuChoYDinh() {
    const loai = gt("tai-loai"), ma = String(gt("tai-ma")).trim(), tep = taiTep;
    if (!loai || !ma || !tep) { trangThai("Chọn loại hình, nhập mã mẫu và chọn tệp .docx trước.", true); return null; }
    const intent = JSON.stringify([ep, actor(), genTai, genForm, loai, ma, tep.name, tep.size, tep.lastModified]);
    let y = taiDang.get(intent);
    if (y && !y.het && y.f()) return y;  // cùng context còn hiệu lực: đúng ý định cũ (đang gửi → 0 POST; chưa rõ → gửi lại y nguyên)
    if (y) boYDinh(y);  // context chung đã đổi (vd sửa ánh xạ/lý do/ngày trong lúc chờ): ý định cũ hết hiệu lực, không gửi lại; bấm này là ý định MỚI
    // TIEP-02 U02: context gốc gồm cả thế hệ form CHUNG (genForm) — sửa bất kỳ ô nào (ánh xạ, KT/CFO, G7…) sau khi bấm ⇒ hoàn tất/gửi lại cũ
    // không chọn phiên bản/toast/làm mới/xóa nháp. Kiểm trước request, sau mọi bước chờ, trước mọi side effect.
    const e = ep, a = actor(), g = genTai, gf = genForm, khoa = taoKhoa();
    const enc = encodeURIComponent(JSON.stringify({loai_hinh_id: loai, ma_mau: ma, ten_tep: tep.name, khoa}));
    y = {id: ++soYDinh, intent, file: tep, ma, enc, khoa, dangGui: false, het: false,
      f: () => e === ep && a === actor() && g === genTai && gf === genForm && tab === "mau"};
    taiDang.set(intent, y);  // giữ chỗ đồng bộ
    return y;
  }
  async function guiTai(y) {
    if (y.het || !y.f()) { boYDinh(y, "Ý định tải mẫu thuộc tệp/lựa chọn/vai cũ — không gửi."); return; }
    if (y.dangGui) { trangThai("Đang tải mẫu này — chờ kết quả, không gửi lần thứ hai."); return; }
    const toiDa = ds && ds.gioi_han_tep;
    if (!y.file.size) { boYDinh(y, "Tệp rỗng (0 byte) — không gửi."); return; }
    if (toiDa && y.file.size > toiDa) { boYDinh(y, `Tệp ${K.size(y.file.size)} vượt giới hạn ${K.size(toiDa)} — không gửi.`); return; }
    if (y.enc.length > 4000) { boYDinh(y, "Tên tệp/mã mẫu quá dài."); return; }
    y.dangGui = true;
    trangThai(`Đang tải lên ${y.file.name}…`);
    try {
      if (y.het || !y.f()) { boYDinh(y, "Ý định tải mẫu thuộc tệp/lựa chọn/vai cũ — không gửi."); return; }  // cổng cuối ngay trước POST
      const r = await docJson(await goi("/api/crm/mau/tai", {method: "POST", headers: {"X-CRM-G-Info": y.enc}, body: y.file}));
      const hieuLuc = !y.het && y.f();
      boYDinh(y);  // kết quả thật: nhả ý định
      if (!hieuLuc) return;  // hoàn tất của context cũ: không toast/chọn/làm mới trên form mới
      const msg = `Đã nhận mẫu ${y.ma} v${r.phien_ban} · ${r.trang_thai_doc === "DU" ? "đọc đủ" : "ĐỌC CHƯA ĐỦ — chặn kiểm/duyệt"} · SHA ${h12(r.raw_sha256)}${r.lap_lai ? " (biên nhận cũ)" : ""}`;
      K.toast(msg); trangThai(msg);
      taiTep = null; xoaNhap("tai-ma"); doiFormTai();  // form đã gửi xong: xóa tệp/mã để không vô tình tạo phiên bản trùng
      boChon(); pbChon = r.phien_ban_id;
      await napLai();
    } catch (e) {
      if (chuaRo(e) && !y.het && y.f()) {  // chưa rõ, context còn đúng: GIỮ ý định (File/header/khóa gốc) để gửi lại y nguyên
        veNutTep(y);
        xuLyLoi(e);
        return;
      }
      const hieuLuc = !y.het && y.f();
      boYDinh(y);  // lỗi chắc chắn (khóa chưa dùng) hoặc context đã đổi: bỏ ý định
      if (hieuLuc) xuLyLoi(e);
    } finally { y.dangGui = false; }
  }

  // ------------------------------------------------------------------ tải về tệp gốc (quyền kiểm ở máy chủ trước khi đọc kho)
  // TIEP-02 U02: fence = epoch + actor + phiên bản đang mở + tab G1 + thế hệ form chung, kiểm TRƯỚC request, sau MỌI await (phản hồi, blob,
  // arrayBuffer, digest) và ngay trước tạo URL/click/trạng thái. Context cũ: không tự tải, không ghi trạng thái/toast.
  async function taiGoc(v) {
    const gf = genForm, f = fence(() => pbChon === v.id && tab === "mau" && gf === genForm), sha = ct && ct.tep && ct.tep.raw_sha256;
    if (!f()) return;
    try {
      const res = await goi("/api/crm/mau/tep/" + encodeURIComponent(v.id));
      if (!f()) return;
      const blob = await res.blob();
      if (!f()) return;
      if (!blob.size) { trangThai("Tệp tải về rỗng — không lưu.", true); return; }
      let khop = "";
      if (window.crypto && crypto.subtle && sha) {
        const bytes = await blob.arrayBuffer();
        if (!f()) return;
        const buf = await crypto.subtle.digest("SHA-256", bytes);
        if (!f()) return;
        const hex = [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
        khop = hex === sha ? " · SHA-256 khớp bản đã nhận" : " · SHA-256 KHÁC bản đã nhận";
      }
      if (!f()) return;  // ngay trước side effect
      const url = URL.createObjectURL(blob), a = node("a"); a.href = url; a.download = v.ten_tep || "mau.docx"; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      trangThai(`Đã tải ${v.ten_tep} (${blob.size} byte)${khop}.`);
    } catch (e) { if (f()) xuLyLoi(e); }
  }

  // ------------------------------------------------------------------ nạp dữ liệu (barrier đổi vai + thế hệ + form)
  function baoCoMoi() { trangThai("Dữ liệu mới đã về trong lúc bạn đang nhập — chưa vẽ lại để giữ vị trí nhập; bấm ↻ Làm mới khi xong."); }
  // TIEP-02 U02: mọi GET dùng CÙNG invariant cho thành công / lỗi / hẹn giờ thử lại: chỉ GET mới nhất của đúng epoch(+tab/lựa chọn) được ghi
  // cache/DOM/trạng thái. Lỗi tạm (mạng/5xx/400) KHÔNG xóa dữ liệu/editor đang có — chỉ báo trạng thái. Lỗi an ninh (phiên/danh tính/403) xóa
  // dữ liệu thuộc quyền cũ ngay (không giữ dữ liệu vượt quyền); đổi vai vẫn đi qua seam chung (xoa + barrier).
  const loiAnNinh = err => !!err && (err.status === 401 || err.status === 403 || ["CRM_PHIEN", "DANH_TINH", "DANH_TINH_MO_PHONG"].includes(err.code));
  let thuPhien = 0;
  async function napDs() {
    if (K.vaiDangChan("crm_g")) return;
    const e = ep, g = ++genDs, fs = formCon(), dung = () => e === ep && g === genDs;
    try {
      const s = await (await goi("/api/crm/mau")).json();
      if (!dung()) return;
      thuPhien = 0;
      let doi = false;
      if (actor() !== null && s.nguoi && s.nguoi.dang_nhap !== actor()) { ep += 1; boChon(); huyYDinhTai(); khoaMap.clear(); nhapGt.clear(); taiTep = null; doi = true; }
      ds = s;
      if (pbChon && !(s.phien_ban || []).some(v => v.phien_ban_id === pbChon)) { boChon(); doi = true; }
      if (!doi && !fs()) { baoCoMoi(); return; }
      ve();
    } catch (err) {
      if (!dung()) return;
      // phiên cookie do GET /api/crm của mục CRM cấp — lần nạp đầu có thể đến trước: thử lại MỘT lần, không tự tạo phiên/danh tính;
      // hẹn giờ chỉ chạy nếu chưa có GET/epoch mới hơn
      if (err.code === "CRM_PHIEN" && ds === null && thuPhien < 1) { thuPhien += 1; setTimeout(() => { if (dung()) napDs(); }, 800); return; }
      if (loiAnNinh(err)) { ds = null; boChon(); huyYDinhTai(); ve(); trangThai(err.message, true); return; }
      if (ds === null && fs()) ve();  // lần nạp đầu lỗi tạm: vẽ trạng thái trống; đã có dữ liệu/editor → giữ nguyên
      trangThai(err.message, true);
    }
  }
  async function napCt() {
    if (!pbChon) { ct = null; ve(); return; }
    if (K.vaiDangChan("crm_g")) return;
    const e = ep, id = pbChon, g = ++genCt, fs = formCon(), dung = () => e === ep && id === pbChon && g === genCt;
    try {
      const d = await (await goi("/api/crm/mau/" + encodeURIComponent(id))).json();
      if (!dung()) return;
      ct = d;
      if (!fs()) { baoCoMoi(); return; }  // người dùng đã nhập sau lúc bắt đầu GET: giữ editor, chỉ báo
      ve();
    } catch (err) {
      if (!dung()) return;
      if (err.status === 404 || loiAnNinh(err)) { boChon(); ve(); trangThai(err.message + " — phiên bản không còn trong phạm vi của vai này.", true); }
      else trangThai(err.message, true);  // lỗi tạm: giữ chi tiết/nháp đang có
    }
  }
  async function napBc() {
    if (K.vaiDangChan("crm_g")) return;
    const e = ep, g = ++genBc, fs = formCon(), dung = () => e === ep && g === genBc && tab === "chuan";
    try {
      const d = await (await goi("/api/crm/bo-chuan")).json();
      if (!dung()) return;
      bc = d;
      if (!fs()) { baoCoMoi(); return; }
      ve();
    } catch (err) {
      if (!dung()) return;  // đã chuyển tab/GET mới hơn: lỗi cũ không ghi trạng thái/DOM
      if (loiAnNinh(err)) { bc = null; bcDoc = null; ve(); }
      else if (bc === null && fs()) ve();
      trangThai(err.message, true);
    }
  }
  const truyVanDoc = () => ({du_an_id: gt("doc-du-an"), giai_doan: String(gt("doc-giai-doan")).trim(), as_of: gt("doc-ngay")});
  async function docChuan() {  // U02: thế hệ + truy vấn + tab + vai — chỉ GET mới nhất của đúng lựa chọn hiện tại được ghi cache/DOM/trạng thái
    if (K.vaiDangChan("crm_g")) return;
    const q = truyVanDoc(), khoaQ = JSON.stringify(q), g = ++genDoc, e = ep, a = actor(), fs = formCon();
    if (!q.du_an_id || !q.giai_doan) { trangThai("Chọn dự án và nhập giai đoạn.", true); return; }
    const dung = () => e === ep && a === actor() && g === genDoc && tab === "chuan" && JSON.stringify(truyVanDoc()) === khoaQ;
    const p = new URLSearchParams({du_an_id: q.du_an_id, giai_doan: q.giai_doan}); if (q.as_of) p.set("as_of", q.as_of);
    try {
      const d = await (await goi("/api/crm/bo-chuan?" + p.toString())).json();
      if (!dung()) return;  // lựa chọn đã đổi/GET mới hơn: bỏ kết quả cũ
      bcDoc = {...d, khoaQ};
      if (!fs()) { baoCoMoi(); return; }
      ve();
    } catch (err) {
      if (!dung()) return;
      if (loiAnNinh(err)) { bcDoc = null; ve(); }
      xuLyLoi(err);
    }
  }
  function boChon() { pbChon = null; ct = null; xemThu = null; soSanh = null; genForm += 1; }
  function moPb(id) { if (pbChon !== id) { boChon(); pbChon = id; doiFormTai(); } ve(); napCt(); }
  function doiTab(t) { if (tab === t) return; tab = t; genForm += 1; genDoc += 1; doiFormTai(); ve(); if (t === "chuan") napBc(); }

  // ------------------------------------------------------------------ đổi vai (người tham gia seam chung)
  function xoa() {  // đồng bộ, trước await đầu tiên của lần đổi vai ở BẤT KỲ selector nào
    ep += 1; ds = null; bc = null; bcDoc = null; soDong = 1; taiTep = null; boChon(); doiFormTai(); khoaMap.clear(); nhapGt.clear(); genDoc += 1;
    chuNutTep = null;  // đổi vai: mọi ý định/nút gửi lại cũ đã bị huyYDinhTai vô hiệu; gỡ DOM dưới đây
    if (oGuiLai) { oGuiLai.replaceChildren(); delete oGuiLai.dataset.tep; }
    ve(); trangThai("");
    Promise.resolve().then(() => napTong());  // trong barrier: chỉ ghi "cần nạp" — nạp lại khi ý định đổi vai mới nhất giải quyết
  }
  function napTong() { napDs(); if (tab === "chuan") napBc(); }
  K.dangKyVai("crm_g", xoa, () => { napDs(); if (pbChon) napCt(); if (tab === "chuan") napBc(); });

  // ------------------------------------------------------------------ vẽ
  function ve() {
    if (!oNoiDung) dungKhung();
    $("crmg-vai").textContent = ds ? `Vai hiện hành: ${ds.nguoi.dang_nhap} (${ds.nguoi.vai_tro}) · đổi vai ở mục Vai mô phỏng phía trên.` : "Đang tải…";
    $("crmg-tab-mau").setAttribute("aria-pressed", String(tab === "mau"));
    $("crmg-tab-chuan").setAttribute("aria-pressed", String(tab === "chuan"));
    oNoiDung.replaceChildren(...(tab === "mau" ? veMau() : veChuan()));
  }
  function dungKhung() {
    const head = node("div", undefined, "section-heading"), tieuDe = node("div"), h2 = node("h2", "5 · Mẫu hợp đồng & bộ chuẩn dự án");
    h2.id = "crm-g-title";
    const vai = node("p", "Đang tải…"); vai.id = "crmg-vai";
    tieuDe.append(h2, node("p", "G1: mẫu DOCX có phiên bản, ánh xạ ô {{…}} vào danh mục trường, kế toán kiểm/trả lại, CFO (V4) duyệt hiệu lực. G7: bộ chuẩn đợt thu theo dự án/giai đoạn (4 cột) — không sinh lịch thu/công nợ/thuế."), vai);
    head.append(tieuDe, nut("↻ Làm mới", () => napLai(), "button secondary"));
    const tabs = node("div", undefined, "demo-actions");
    const t1 = nut("Mẫu hợp đồng (G1)", () => doiTab("mau"), "button secondary"); t1.id = "crmg-tab-mau";
    const t2 = nut("Bộ chuẩn dự án (G7)", () => doiTab("chuan"), "button secondary"); t2.id = "crmg-tab-chuan";
    tabs.append(t1, t2);
    oTrangThai = node("p", "", "upload-status"); oTrangThai.setAttribute("role", "status"); oTrangThai.setAttribute("aria-live", "polite");
    oGuiLai = node("div", undefined, "demo-actions");
    oNoiDung = node("div");
    goc.replaceChildren(head, tabs, oTrangThai, oGuiLai, oNoiDung);
  }

  function veMau() {
    if (!ds) return [K.empty("Chưa tải danh sách mẫu", "Bấm ↻ Làm mới; cần kho DEMO PostgreSQL đã chuẩn bị.")];
    const out = [];
    if (!ds.ghi_nguon.san_sang) out.push(node("p", "Chưa cấu hình kết nối máy chủ (chủ CSDL) cho mẫu/bộ chuẩn — tải lên/ánh xạ/kiểm/duyệt sẽ báo chưa sẵn sàng.", "upload-status error"));
    const loai = (ds.loai_hinh || []).filter(l => l.duoc_tai);
    if (loai.length) {
      const f = node("div", undefined, "demo-actions");
      const sel = chon("tai-loai", loai.map(l => [l.id, `${l.phap_nhan} · ${l.ma} v${l.phien_ban}`]), loai[0].id, undefined, () => doiFormTai());
      if (!loai.some(l => l.id === sel.value)) { sel.value = loai[0].id; nhapGt.set(sel.id, sel.value); }
      const ma = nhap("tai-ma", "", "text", () => doiFormTai());
      const tep = node("input"); tep.type = "file"; tep.accept = ".docx";
      o("tai-tep", tep, "", el => { taiTep = (el.files || [])[0] || null; doiFormTai(); });
      const daChon = node("small", taiTep ? `Tệp đã chọn: ${taiTep.name} (${K.size(taiTep.size)})` : "Chưa chọn tệp");
      f.append(...truong("Loại hình", sel), ...truong("Mã mẫu", ma), ...truong("Tệp mẫu (.docx)", tep), daChon,
        nut("Tải mẫu lên", () => { const y = giuChoYDinh(); if (y) guiTai(y); }, "button primary"));
      out.push(node("h3", "Tải mẫu mới / phiên bản mới"), f);
    }
    const rows = ds.phien_ban || [];
    out.push(node("h3", "Phiên bản mẫu"), rows.length ? bang(["Pháp nhân", "Mã mẫu", "Loại hình", "Phiên bản", "Trạng thái", "Hiệu lực", "Tệp", ""], rows.map(v => [
      v.phap_nhan, v.ma_mau, `${v.loai_hinh} v${v.loai_hinh_phien_ban}`, "v" + v.phien_ban, pill(TT_MAU[v.trang_thai] || v.trang_thai, v.trang_thai === "HIEU_LUC" ? "green" : v.trang_thai === "TU_CHOI" ? "red" : "amber"),
      v.valid_from ? `${v.valid_from} → ${v.valid_to || "…"}` : "—", v.ten_tep, nut(pbChon === v.phien_ban_id ? "Đang mở" : "Mở", () => moPb(v.phien_ban_id), "link-button", pbChon === v.phien_ban_id)]))
      : K.empty("Chưa có mẫu trong phạm vi vai này", loai.length ? "Tải mẫu .docx lên để bắt đầu." : "Vai này chỉ xem mẫu đã duyệt hiệu lực (nếu có)."));
    if (pbChon) out.push(...veCt());
    return out;
  }

  function veCt() {
    if (!ct || ct.phien_ban.id !== pbChon) return [node("p", "Đang tải phiên bản…")];
    const v = ct.phien_ban, kn = ct.kha_nang, tok = ct.token, f = () => fence(() => pbChon === v.id && tab === "mau");
    const box = node("div", undefined, "card"), out = [box];
    box.append(node("h3", `${v.ma_mau} · v${v.phien_ban} · ${TT_MAU[v.trang_thai] || v.trang_thai}`),
      node("p", `Tệp ${v.ten_tep} · ${K.size(ct.tep.byte_length)} · SHA-256 ${h12(ct.tep.raw_sha256)} · bộ đọc ${ct.tep.bo_doc} · danh mục ${v.danh_muc_ref}@${v.danh_muc_rev}`
        + (v.valid_from ? ` · hiệu lực ${v.valid_from} → ${v.valid_to || "…"}` : "") + (v.duyet_boi ? ` · quyết định bởi ${v.duyet_boi}` : "") + (v.tu_choi_ly_do ? ` · lý do từ chối: ${v.tu_choi_ly_do}` : "")));
    const top = node("div", undefined, "demo-actions");
    top.append(nut("Tải DOCX gốc ↓", () => taiGoc(v), "button secondary"));
    if (ct.quyen_doc === "DAY_DU") top.append(nut("Xem thử (dữ liệu giả)", async () => {
      const ff = f(), fc = formCon(); const r = await gui("mau/xem-thu", {version_id: v.id}, "", ff, false);
      if (r && ff()) { xemThu = r; if (fc()) ve(); else baoCoMoi(); } }, "button secondary"));
    const cung = (ds.phien_ban || []).filter(x => x.mau_id === v.mau_id && x.phien_ban_id !== v.id);
    if (cung.length) {
      const s = chon(`so-sanh-${v.id}`, cung.map(x => [x.phien_ban_id, `v${x.phien_ban} · ${TT_MAU[x.trang_thai] || x.trang_thai}`]), cung[0].phien_ban_id);
      top.append(...truong("So sánh với", s), nut("So sánh", async () => {
        if (K.vaiDangChan("crm_g")) return;
        const b = s.value, gf = genForm, ff = fence(() => pbChon === v.id && tab === "mau" && gt(`so-sanh-${v.id}`) === b && gf === genForm), q = new URLSearchParams({a: v.id, b});
        try { const r = await (await goi("/api/crm/mau/so-sanh?" + q.toString())).json(); if (ff()) { soSanh = r; ve(); } } catch (e) { if (ff()) xuLyLoi(e); } }, "button secondary"));
    }
    box.append(top);
    if (ct.tep.trang_thai_doc !== "DU") box.append(node("p", "Đọc CHƯA ĐỦ — chặn kiểm/duyệt: " + (ct.phat_hien
      ? ct.phat_hien.ly_do_chua_du.map(x => (LY_DO_DOC[x.ma] || x.ma) + (x.phan ? ` (${x.phan}${x.vi_tri ? " " + x.vi_tri : ""})` : "")).join("; ")
      : "chi tiết chỉ hiện cho người soạn/kiểm/duyệt"), "upload-status error"));
    if (ct.phat_hien) {
      const occ = ct.phat_hien.occurrences || [];
      box.append(node("h4", `Ô phát hiện (${occ.length} lần xuất hiện, ${ct.phat_hien.placeholders.length} tên)`),
        occ.length ? bang(["#", "Ô", "Phần", "Vị trí", "Khoảng ký tự", "Tách run", "Ngữ cảnh"], occ.map((x, i) => [i + 1, `{{${x.ten}}}`, `${LOAI_PHAN[x.loai_phan] || x.loai_phan} (${x.phan})`,
          x.vi_tri, `[${x.bat_dau}, ${x.ket_thuc})`, x.tach_run ? `có (run ${x.runs.join(", ")})` : "không", x.ngu_canh]))
          : K.empty("Không phát hiện ô {{…}}", "Tệp không có ô để ánh xạ."));
      box.append(...veAnhXa(v, kn, tok, f));
    }
    const hd = node("div", undefined, "demo-actions");
    if (v.trang_thai === "DRAFT" && kn.CRM_MAU_GUI_KIEM) hd.append(nut("Gửi kế toán kiểm", async () => { const ff = f(), fc = formCon();
      if (await gui("mau/gui-kiem", {version_id: v.id, expected_graph: tok}, "Đã gửi kiểm", ff)) await sauLenh(fc, ff); }, "button primary"));
    if (v.trang_thai === "CHO_KIEM" && kn.CRM_MAU_KIEM) hd.append(nut("Kế toán kiểm đạt", async () => { const ff = f(), fc = formCon();
      if (await gui("mau/kiem", {version_id: v.id, expected_graph: tok}, "Đã kiểm — chờ CFO", ff)) await sauLenh(fc, ff); }, "button primary"));
    if (v.trang_thai === "CHO_KIEM" && kn.CRM_MAU_TRA_LAI) {
      const ly = nhap(`tra-lai-${v.id}`, "");
      hd.append(...truong("Lý do trả lại", ly), nut("Trả lại", async () => { const ff = f(), lyDo = String(gt(`tra-lai-${v.id}`)).trim();
        if (!lyDo) { trangThai("Trả lại cần lý do.", true); return; }
        const fc = formCon();
        if (await gui("mau/tra-lai", {version_id: v.id, ly_do: lyDo, expected_graph: tok}, "Đã trả lại về nháp", ff)) { if (fc()) xoaNhap(`tra-lai-${v.id}`); await sauLenh(fc, ff); } }, "button secondary"));
    }
    if (v.trang_thai === "CHO_CFO" && kn.CRM_MAU_DUYET_V4) {
      const ngay = nhap(`duyet-${v.id}`, homNay(), "date");
      hd.append(...truong("Hiệu lực từ", ngay), nut("CFO duyệt (V4)", async () => { const ff = f(), fc = formCon();
        if (await gui("mau/duyet", {version_id: v.id, valid_from: gt(`duyet-${v.id}`), expected_graph: tok}, "Đã duyệt hiệu lực", ff)) await sauLenh(fc, ff); }, "button primary"));
    }
    if (v.trang_thai === "CHO_CFO" && kn.CRM_MAU_TU_CHOI) {
      const ly = nhap(`tu-choi-${v.id}`, "");
      hd.append(...truong("Lý do từ chối", ly), nut("CFO từ chối", async () => { const ff = f(), lyDo = String(gt(`tu-choi-${v.id}`)).trim();
        if (!lyDo) { trangThai("Từ chối cần lý do.", true); return; }
        const fc = formCon();
        if (await gui("mau/tu-choi", {version_id: v.id, ly_do: lyDo, expected_graph: tok}, "Đã từ chối", ff)) await sauLenh(fc, ff); }, "button secondary"));
    }
    if (hd.childNodes.length) box.append(node("h4", "Thao tác"), hd);
    if (xemThu && xemThu.phien_ban_id === v.id) {
      box.append(node("h4", "Xem thử — DỮ LIỆU GIẢ, không phải hợp đồng thật"));
      xemThu.doan.forEach(d => box.append(node("p", `[${LOAI_PHAN[d.loai_phan] || d.loai_phan} · ${d.vi_tri}] ${d.van_ban}${d.cat_bot ? " …(đoạn đã cắt bớt)" : ""}`)));
    }
    if (soSanh && soSanh.a.id === v.id) {
      box.append(node("h4", `So sánh v${soSanh.a.phien_ban} ↔ v${soSanh.b.phien_ban}${soSanh.khac_tep ? " · tệp khác nhau" : " · cùng tệp"}`),
        bang(["Ô", `Số lần v${soSanh.a.phien_ban}`, `Số lần v${soSanh.b.phien_ban}`, `Trường v${soSanh.a.phien_ban}`, `Trường v${soSanh.b.phien_ban}`, ""],
          soSanh.dong.map(d => [d.ten, d.so_lan_a ?? "—", d.so_lan_b ?? "—", d.truong_a || "—", d.truong_b || "—", d.khac ? "khác" : ""])));
    }
    const ls = ct.lich_su || {};
    if (ls.anh_xa && ls.anh_xa.length) box.append(node("h4", "Lịch sử ánh xạ"), bang(["Rev", "Chưa ánh xạ", "Sai kiểu", "Cảnh báo", "Bởi", "Lúc"],
      ls.anh_xa.map(a => [a.revision, a.so_chua_anh_xa, a.so_sai_kieu, (a.canh_bao || []).map(c => c.truong).join(", "), a.tao_boi, K.date(a.tao_luc)])));
    if (ls.kiem_tra && ls.kiem_tra.length) box.append(node("h4", "Lần kế toán kiểm"), bang(["Kết quả", "Bởi", "Lúc", "Hiện hành"],
      ls.kiem_tra.map(k => [k.ket_qua, k.kiem_boi, K.date(k.kiem_luc), (ct.anh_xa && k.anh_xa_id === ct.anh_xa.id && v.trang_thai === "CHO_CFO") ? "có" : "không"])));
    if (ls.su_kien && ls.su_kien.length) box.append(node("h4", "Nhật ký"), bang(["Lúc", "Người", "Hành động", "Lý do"], ls.su_kien.map(s => [K.date(s.luc), s.nguoi, s.hanh_dong, s.ly_do || ""])));
    return out;
  }

  function veAnhXa(v, kn, tok, f) {
    const out = [], ph = ct.phat_hien.placeholders || [], dm = ct.danh_muc || [];
    const hien = {};
    ((ct.anh_xa && ct.anh_xa.ban_do) || []).forEach(x => { if (!(x.ten in hien)) hien[x.ten] = x.truong; });
    if (ct.anh_xa) {
      const cb = (ct.anh_xa.canh_bao || []).map(c => c.truong);
      out.push(node("p", `Ánh xạ rev ${ct.anh_xa.revision}: ${ct.anh_xa.so_chua_anh_xa} lần xuất hiện chưa ánh xạ · ${ct.anh_xa.so_sai_kieu} sai kiểu`
        + (cb.length ? ` · Cảnh báo (không chặn): trường bắt buộc chưa có trong mẫu — ${cb.join(", ")}` : "")));
    }
    const sua = kn.CRM_MAU_MAP && ["DRAFT", "CHO_KIEM", "CHO_CFO"].includes(v.trang_thai);
    const opts = dm.map(t => [t.khoa, `${t.nhan} (${t.khoa} · ${t.kieu}${t.bat_buoc ? " · bắt buộc" : ""}${t.pii ? " · PII" : ""})`]);
    const rev = ct.anh_xa ? ct.anh_xa.revision : 0;  // nháp gắn revision ánh xạ của máy chủ: revision mới → nháp cũ không che giá trị mới
    out.push(node("h4", "Ánh xạ ô → trường danh mục"), bang(["Ô", "Số lần", "Trường"], ph.map(p => {
      if (!sua) return [`{{${p.ten}}}`, p.so_lan, hien[p.ten] || "— chưa ánh xạ"];
      return [`{{${p.ten}}}`, p.so_lan, chon(`map-${v.id}-${rev}-${p.ten}`, opts, hien[p.ten] || "", "— chưa ánh xạ —")];
    })));
    if (sua && ph.length) out.push(nut("Lưu ánh xạ (phiên bản ánh xạ mới)", async () => {
      const ff = f(), fc = formCon(), map = {};
      ph.forEach(p => { map[p.ten] = gt(`map-${v.id}-${rev}-${p.ten}`, hien[p.ten] || "") || null; });
      if (await gui("mau/anh-xa", {version_id: v.id, map, expected_graph: tok}, "Đã lưu ánh xạ", ff)) { if (fc()) xoaNhap(`map-${v.id}-`); await sauLenh(fc, ff); }
    }, "button primary"));
    return out;
  }

  // ------------------------------------------------------------------ G7
  function veChuan() {
    if (!bc) return [K.empty("Chưa tải bộ chuẩn", "Bấm ↻ Làm mới.")];
    const out = [], duAn = bc.du_an || [];
    if (!duAn.length) return [K.empty("Không có dự án trong phạm vi CRM của vai này", "")];
    const r = node("div", undefined, "demo-actions");
    const sd = chon("doc-du-an", duAn.map(a => [a.id, `${a.phap_nhan} · ${a.ma_junsky}`]), duAn[0].id), gd = nhap("doc-giai-doan", "DEMO_G7_STAGE_1"), ngay = nhap("doc-ngay", homNay(), "date");
    if (!duAn.some(a => a.id === sd.value)) { sd.value = duAn[0].id; nhapGt.set(sd.id, sd.value); }
    r.append(...truong("Dự án", sd), ...truong("Giai đoạn", gd), ...truong("Tại ngày", ngay), nut("Xem bộ chuẩn hiệu lực", () => docChuan(), "button secondary"));
    out.push(node("h3", "Bộ chuẩn hiệu lực"), r);
    if (bcDoc && bcDoc.khoaQ === JSON.stringify(truyVanDoc())) {  // chỉ hiện kết quả của ĐÚNG lựa chọn đang nhập
      if (bcDoc.trang_thai === "CHUA_CO") out.push(K.empty(`Chưa có bộ chuẩn hiệu lực (${bcDoc.giai_doan} tại ${bcDoc.as_of})`, "Không suy ra lệch hay lịch thu khi chưa có bộ chuẩn."));
      else { const d = node("div"); d.append(node("p", `v${bcDoc.version.phien_ban} · hiệu lực ${bcDoc.version.valid_from} → ${bcDoc.version.valid_to || "…"}`), bangChuan(bcDoc.cot, bcDoc.rows)); out.push(d); }
    }
    const lap = duAn.filter(a => a.duoc_lap);
    if (lap.length) out.push(node("h3", "Lập bộ chuẩn (nháp) — kế toán"), ...veLap(lap));
    const pb = bc.phien_ban || [];
    if (pb.length) {
      out.push(node("h3", "Phiên bản bộ chuẩn"));
      pb.forEach(v => {
        const a = duAn.find(x => x.id === v.du_an_id), box = node("div", undefined, "card"), f = fence(() => tab === "chuan");
        box.append(node("h4", `${a ? a.ma_junsky : v.du_an_id} · ${v.giai_doan} · v${v.phien_ban} · ${TT_CHUAN[v.trang_thai] || v.trang_thai}`
          + (v.valid_from ? ` · hiệu lực ${v.valid_from} → ${v.valid_to || "…"}` : "")), node("p", `Lập bởi ${v.lap_boi}${v.gui_boi ? " · gửi bởi " + v.gui_boi : ""}${v.duyet_boi ? " · duyệt bởi " + v.duyet_boi : ""}`),
          bangChuan(bc.cot, v.dong));
        const hd = node("div", undefined, "demo-actions");
        if (v.trang_thai === "DRAFT" && v.duoc_gui) hd.append(nut("Gửi CFO duyệt", async () => { const fc = formCon();
          if (await gui("bo-chuan/gui-duyet", {version_id: v.id, expected_graph: v.token}, "Đã gửi CFO duyệt", f)) await sauLenh(fc, f); }, "button primary"));
        if (v.trang_thai === "CHO_CFO" && v.duoc_duyet) {
          const nd = nhap(`chuan-ngay-${v.id}`, homNay(), "date");
          hd.append(...truong("Hiệu lực từ", nd), nut("CFO duyệt (V4)", async () => { const fc = formCon();
            if (await gui("bo-chuan/duyet", {version_id: v.id, valid_from: gt(`chuan-ngay-${v.id}`), expected_graph: v.token}, "Đã duyệt bộ chuẩn", f)) await sauLenh(fc, f); }, "button primary"));
        }
        if (hd.childNodes.length) box.append(hd);
        out.push(box);
      });
    }
    return out;
  }
  function docDong() {
    return Array.from({length: soDong}, (_, i) => Object.fromEntries(COT_DONG.map(c => [c, gt(`l-${c}-${i}`, c === "lan" ? String(i + 1) : c === "tt" ? "VND" : "")])));
  }
  function ghiDong(rows) {
    xoaNhap("l-");
    rows.forEach((d, i) => COT_DONG.forEach(c => nhapGt.set(`crmg-l-${c}-${i}`, d[c])));
    soDong = rows.length;
  }
  function veLap(duAn) {
    const f = node("div", undefined, "demo-actions");
    const sd = chon("lap-du-an", duAn.map(a => [a.id, `${a.phap_nhan} · ${a.ma_junsky}`]), duAn[0].id), gd = nhap("lap-giai-doan", "DEMO_G7_STAGE_1");
    if (!duAn.some(a => a.id === sd.value)) { sd.value = duAn[0].id; nhapGt.set(sd.id, sd.value); }
    f.append(...truong("Dự án", sd), ...truong("Giai đoạn", gd));
    const rows = Array.from({length: soDong}, (_, i) => {
      const lan = nhap(`l-lan-${i}`, String(i + 1)), gl = chon(`l-gl-${i}`, [["PERCENT", "Tỷ lệ %"], ["AMOUNT", "Số tiền"]], "", "— chưa có —");
      const tp = nhap(`l-tp-${i}`, ""), st = nhap(`l-st-${i}`, ""), tt = nhap(`l-tt-${i}`, "VND");
      const ml = chon(`l-ml-${i}`, [["NGAY", "Ngày"], ["SU_KIEN", "Sự kiện"]], "", "— chưa có —"), mn = nhap(`l-mn-${i}`, "", "date"), ms = nhap(`l-ms-${i}`, ""), gc = nhap(`l-gc-${i}`, "");
      [lan, gl, tp, st, tt, ml, mn, ms, gc].forEach(x => x.setAttribute("aria-label", `Dòng ${i + 1} · ${x.id.split("-")[2]}`));
      tp.placeholder = "vd 40"; st.placeholder = "số nguyên đơn vị nhỏ nhất"; ms.placeholder = "MÃ_SỰ_KIỆN";
      const g = node("div"); g.append(gl, tp, st, tt);
      const m = node("div"); m.append(ml, mn, ms);
      return [lan, g, m, gc, nut("Bỏ", () => { const ds2 = docDong(); ds2.splice(i, 1); ghiDong(ds2); genForm += 1; ve(); }, "link-button", soDong <= 1)];
    });
    const tb = bang([...bc.cot, ""], rows);
    const them = nut("+ Dòng", () => { const ds2 = docDong(); ds2.push(Object.fromEntries(COT_DONG.map(c => [c, c === "lan" ? String(ds2.length + 1) : c === "tt" ? "VND" : ""]))); ghiDong(ds2); genForm += 1; ve(); }, "link-button");
    const lapNut = nut("Lập bộ chuẩn (nháp)", async () => {
      const ff = fence(() => tab === "chuan"), fc = formCon(), s = x => (String(x).trim() === "" ? null : String(x).trim());
      const dong = docDong().map(d => {
        const gl = d.gl || null, ml = d.ml || null;
        return {lan: String(d.lan).trim(), gia_tri_loai: gl, gia_tri_thap_phan: gl === "PERCENT" ? s(d.tp) : null,
          so_tien_minor: gl === "AMOUNT" ? s(d.st) : null, tien_te: gl === "AMOUNT" ? s(d.tt) : null,
          moc_loai: ml, moc_ngay: ml === "NGAY" ? s(d.mn) : null, moc_su_kien: ml === "SU_KIEN" ? s(d.ms) : null, ghi_chu: s(d.gc)};
      });
      const res = await gui("bo-chuan/lap", {du_an_id: gt("lap-du-an"), giai_doan: String(gt("lap-giai-doan")).trim(), dong}, "Đã lập bộ chuẩn nháp", ff);
      if (res && ff()) { if (fc()) { xoaNhap("l-"); soDong = 1; } await sauLenh(fc, ff); }
    }, "button primary");
    return [f, tb, them, lapNut];
  }

  // ------------------------------------------------------------------ khởi động
  dungKhung(); ve();
  if (location.hash === "#hopdong") napDs();
  window.addEventListener("hashchange", () => { if (location.hash === "#hopdong") { napDs(); if (pbChon) napCt(); if (tab === "chuan") napBc(); } });
})();

// CRM-41-03 — S7 trong cùng shell CRM (#crm-gk): G2 Báo giá hai cột → G3 Soạn hợp đồng ba cột. Chỉ gọi route/DTO thật của crm_g.py +
// k2/crm_giao_ket.py; trình duyệt gửi dữ liệu nhập tay (chuỗi số chính xác), ID, revision mong đợi, khóa — KHÔNG actor/PN/trạng thái/kết quả tính.
// Mọi số tiền/tổng %/FX tham chiếu/chặn In-Xuất do MÁY CHỦ tính (số nguyên đơn vị nhỏ nhất, không làm tròn); giao diện chỉ hiển thị.
// Bất đồng bộ: dùng lại cổng đổi vai chung (window.kttChung), fence = epoch + actor + thế hệ form; khóa của một ý định (đường dẫn + body gốc) giữ
// đến khi có kết quả thật (chưa rõ → nút "Gửi lại y nguyên"); bấm lặp khi đang gửi → 0 POST; GET cũ/tải về trễ không ghi đè form/không tải nhầm.
(() => {
  const K = window.kttChung;
  if (!K) return;
  const $ = id => document.getElementById(id);
  const node = K.node;
  const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || "";
  const goc = $("crm-gk");
  if (!goc) return;
  const TT_BG = {NHAP: "Nháp", DA_CHUYEN: "Đã chuyển sang Soạn", HUY: "Đã hủy"};
  const TT_SO = {SOAN_THAO: "Đang soạn", CHO_KY: "Chờ ký (đã xuất DOCX+PDF)", DA_KY: "Đã ký — chờ kế toán kiểm"};
  const TT_XUAT = {PDF_DAT: "DOCX + PDF đạt", PDF_CHUA_SAN_SANG: "DOCX đã giữ · PDF chưa sẵn sàng", PDF_LOI: "DOCX đã giữ · PDF lỗi", DA_CU: "Bản cũ (revision đã đổi)"};

  let ep = 0, genForm = 0, genDs = 0, genBg = 0, genSo = 0, cheDo = "bao_gia";
  let ds = null, bgChon = null, bgCt = null, soChon = null, soCt = null, soDongBg = 1, soDongSo = 0;
  // FIX01 #3: số lần sửa NỘI DUNG form (bg-/so-) và mốc đồng bộ với revision máy chủ — In/Chuyển/Xuất chỉ khi không còn thay đổi chưa lưu
  // FIX03 R1: `nhapMoi` = ĐỊNH DANH của một lần bắt đầu nháp MỚI ({so, tao}) — "+ Báo giá mới" luôn tạo định danh mới (MOI → MOI là nháp KHÁC);
  // gõ tiếp cùng nháp giữ định danh. ACK tạo mới chỉ ghi vào đúng định danh của ý định đó (`tao` = {id, revision} của báo giá đã tạo).
  let soSua = 0, dongBo = 0, xemTruoc = null, nhapMoi = null, soNhapMoi = 0;
  // CRM-41-04A G4: `kyCt` = điều kiện/căn cứ/bản ký của bản soạn đang mở (GET mới nhất theo `genKy`); `kyMo` = căn cứ dialog chụp lúc mở
  // ({soan, revision, xuat_id}); `kyTep` = File đã chọn. `kyYD` = ý định ký theo (vai, bản soạn, căn cứ, File, khai báo) — giữ ĐÚNG File + header +
  // khóa tới kết quả thật; chưa rõ → nút gửi lại y nguyên trong khối G4 của ĐÚNG bản soạn (không dùng nút gửi lại chung), đổi vai/HĐ không xóa.
  // FIX04 U3: `genVao` = thế hệ hiển thị theo ĐIỀU HƯỚNG — mọi hashchange (rời #hopdong hoặc quay lại) tăng; callback G4 cũ (tải bản ký, ACK/lỗi
  // ký) chụp giá trị lúc bắt đầu nên đi-rồi-về KHÔNG hồi hiệu lực.
  let kyCt = null, genKy = 0, kyMo = null, kyTep = null, genVao = 0;
  const kyYD = new Map();
  // FIX02 #3: chọn mẫu khác/lý do đổi mẫu trong G3 (`so-doi-*`) là NỘI DUNG bản soạn → bẩn tới khi Lưu + nạp revision mới. `bg-mau-*` là tham số
  // của lệnh Chuyển, `bg-huy-*` là lý do hủy — không phải nội dung báo giá, không buộc lưu.
  const NOI_DUNG = /^gk-(bg-|so-)(?!mau-|huy-)/;
  const chuaLuu = () => soSua !== dongBo;
  const SCALE = {VND: 0, USD: 2};
  function minorSangChinh(s, tt) {  // chuỗi số nguyên đơn vị nhỏ nhất → chuỗi đơn vị chính CHÍNH XÁC (không float); tiền tệ lạ → null
    const sc = SCALE[tt]; if (sc === undefined || !/^-?\d+$/.test(String(s ?? ""))) return null;
    const am = String(s).startsWith("-"), so = String(s).replace("-", "");
    if (sc === 0) return (am ? "-" : "") + so;
    const d = so.padStart(sc + 1, "0"); return (am ? "-" : "") + d.slice(0, -sc) + "." + d.slice(-sc);
  }
  const nhapGt = new Map(), khoaMap = new Map(), revDaLuu = new Map();  // revDaLuu: revision đã lưu nhưng chưa nạp về form (đối tượng → revision)
  const actor = () => (ds && ds.nguoi && ds.nguoi.dang_nhap) || null;
  const taoKhoa = () => "crmgk-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));
  const fence = them => { const e = ep, a = actor(); return () => e === ep && a === actor() && (!them || them()); };
  const formCon = () => { const g = genForm; return () => g === genForm; };
  class LoiGK extends Error { constructor(status, code, message) { super(message); this.status = status; this.code = code; } }
  async function goi(path, opts = {}) {
    let res;
    try { res = await fetch(path, {...opts, headers: {"X-KTT-Token": TOKEN, ...(opts.headers || {})}, cache: "no-store", credentials: "same-origin"}); }
    catch (_) { throw new LoiGK(0, "MAT_KET_NOI", "Mất kết nối — chưa xác định máy chủ đã ghi hay chưa. Khóa và nội dung được giữ; bấm Gửi lại y nguyên."); }
    if (!res.ok) { const r = await res.json().catch(() => ({})); throw new LoiGK(res.status, r.error || "HTTP_" + res.status, r.message || `Không hoàn tất (${res.status}).`); }
    return res;
  }
  async function docJson(res) {
    try { return await res.json(); }
    catch (_) { throw new LoiGK(0, "KET_QUA_CHUA_RO", "Phản hồi đọc không trọn — chưa rõ lệnh đã ghi hay chưa. Khóa được giữ; bấm Gửi lại y nguyên."); }
  }
  // FIX02 #1: 409 "đang xử lý/chưa rõ" của lần in/xuất đã đặt chỗ = KẾT QUẢ CHƯA RÕ (giữ body + khóa gốc tới FINAL, chỉ đối soát y nguyên khi
  // người dùng bấm). CHỈ hai mã này; 409 xung đột body/revision/quyền/chặn là kết quả XÁC ĐỊNH → nhả khóa, không gửi lại.
  const MA_DANG_XU_LY = new Set(["CRM_GK_DANG_XU_LY", "CRM_GK_LAN_KHONG_KHOP"]);
  const dangXuLy = e => !!e && e.status === 409 && MA_DANG_XU_LY.has(e.code);
  const chuaRo = e => !!e && (((e.status === 0 || e.status >= 500) && e.code !== "CRM_G_CHUA_SAN_SANG") || dangXuLy(e));
  const loiAnNinh = e => !!e && (e.status === 401 || e.status === 403 || ["CRM_PHIEN", "DANH_TINH", "DANH_TINH_MO_PHONG"].includes(e.code));

  // ------------------------------------------------------------------ ô nhập ghi xuyên
  let oTrangThai = null, oGuiLai = null, oNoiDung = null;
  function trangThai(msg, loi = false) { if (oTrangThai) { oTrangThai.textContent = msg || ""; oTrangThai.className = "upload-status" + (loi ? " error" : ""); } }
  const gt = (id, md = "") => nhapGt.has("gk-" + id) ? nhapGt.get("gk-" + id) : md;
  function o(id, el, md = "", khiDoi) {
    el.id = "gk-" + id;
    if (!nhapGt.has(el.id)) nhapGt.set(el.id, md);
    el.value = nhapGt.get(el.id);
    const doi = () => { nhapGt.set(el.id, el.value); genForm += 1; if (NOI_DUNG.test(el.id)) { soSua += 1; khoaChuaLuu(); } if (khiDoi) khiDoi(el); };
    el.addEventListener("input", doi); el.addEventListener("change", doi);
    return el;
  }
  function nhap(id, md, type = "text", khiDoi) { const i = node("input"); i.type = type; i.autocomplete = "off"; return o(id, i, md ?? "", khiDoi); }
  function chon(id, opts, md, dau, khiDoi) {
    const s = node("select");
    if (dau !== undefined) { const op = node("option", dau); op.value = ""; s.append(op); }
    for (const [v, t] of opts) { const op = node("option", t); op.value = v; s.append(op); }
    return o(id, s, md ?? "", khiDoi);
  }
  function truong(label, el, bat) { const w = node("div", undefined, "gk-truong"), l = node("label", label + (bat ? " *" : "")); l.htmlFor = el.id; w.append(l, el); return w; }
  function nut(text, fn, cls, tat) { const b = node("button", text, cls || "button secondary"); b.type = "button"; b.disabled = !!tat; b.addEventListener("click", () => { if (!b.disabled) fn(b); }); return b; }
  // FIX01 #3: nút dùng revision đã lưu (In/Chuyển/Xuất) — vô hiệu NGAY khi gõ (không chờ vẽ lại) + lý do; kiểm lại lúc bấm
  const LY_CHUA_LUU = "Có thay đổi chưa lưu — bấm Lưu trước khi In/Chuyển/Xuất (các lệnh này dùng revision đã lưu).";
  const canLuu = fn => async bt => { if (chuaLuu()) { trangThai(LY_CHUA_LUU, true); return; } await fn(bt); };
  let dsCanLuu = [], dsLyDo = [], dsTuTinh = [], dsKiemTong = [];  // phần tử của lần vẽ hiện tại (đặt lại mỗi ve())
  function oLyDo(ly) { const s = node("span", ly, "gk-ly-do"); s.dataset.lyChuaLuu = "1"; s.setAttribute("role", "note"); dsLyDo.push(s); return s; }
  // FIX02 #4: số tự tính/VND tham chiếu đang hiện thuộc form CŨ → hết hiệu lực NGAY trên DOM khi nội dung đổi (không vẽ lại form, không mất caret,
  // không tính ở trình duyệt, không POST mỗi phím). Tính lại = Tính thử (máy chủ) hoặc Lưu.
  const TU_TINH_CU = "— đã sửa: chưa tính lại (Tính thử hoặc Lưu)";
  function khoaChuaLuu() {
    if (!chuaLuu()) return;
    xemTruoc = null;
    dsCanLuu.forEach(b => { if (b.dataset.canLuu) { b.disabled = true; b.title = LY_CHUA_LUU; } });
    dsLyDo.forEach(s => { s.textContent = LY_CHUA_LUU; });
    dsTuTinh.forEach(s => { s.textContent = TU_TINH_CU; s.dataset.hetHieuLuc = "1"; });
    dsKiemTong.forEach(s => { s.dataset.hetHieuLuc = "1"; if (!s.textContent.startsWith("[Revision đã lưu")) s.textContent = "[Revision đã lưu — form có thay đổi chưa lưu] " + s.textContent; });
  }
  function nutLuuTruoc(text, fn, cls) { const b = nut(text, canLuu(fn), cls, chuaLuu()); b.dataset.canLuu = "1"; if (chuaLuu()) b.title = LY_CHUA_LUU; dsCanLuu.push(b); return b; }
  function bang(headers, rows) {
    const wrap = node("div", undefined, "table-wrap"), t = node("table"), head = node("thead"), tr = node("tr"), body = node("tbody");
    headers.forEach(x => tr.append(node("th", x))); head.append(tr); t.append(head);
    for (const r of rows) { const row = node("tr"); for (const c of r) { const td = node("td"); if (c instanceof Node) td.append(c); else td.textContent = c ?? ""; row.append(td); } body.append(row); }
    t.append(body); wrap.append(t); return wrap;
  }
  const xoaNhap = p => { for (const k of [...nhapGt.keys()]) if (k.startsWith("gk-" + p)) nhapGt.delete(k); };
  const s0 = x => { const v = String(x ?? "").trim(); return v === "" ? null : v; };

  // ------------------------------------------------------------------ lệnh có khóa (giữ khóa đến khi có kết quả thật)
  // FIX02 #2: `f` = fence vận chuyển (epoch + actor + lựa chọn + chế độ) quyết định có gửi/ghi nhận trạng thái vận chuyển; `fv` = fence HIỂN THỊ của
  // Ý ĐỊNH GỐC (f + thế hệ form CHỤP MỘT LẦN trước lệnh) — mọi hiệu ứng nhìn thấy (toast/trạng thái/nút đối soát/làm mới/đổi chế độ) chỉ khi fv().
  // Gửi lại/đối soát dùng LẠI đúng f/fv/`sau` gốc (không chụp thế hệ mới sau await/retry). `sau(r, fv)` = phần tiếp của lệnh khi có kết quả.
  const fenceForm = f => { const g = genForm; return () => f() && g === genForm; };
  // FIX03 R2: MỌI hiệu ứng nhìn thấy (xóa/dựng nút gửi lại, trạng thái, toast, làm mới, chế độ, lựa chọn, lỗi) kiểm `fv` GỐC — TRƯỚC khi POST (kể cả
  // nhánh vận chuyển không hợp lệ) và SAU mọi await. Vận chuyển hợp lệ (cùng vai/đối tượng/ý định) vẫn đối soát bằng ĐÚNG body/khóa/phần tiếp gốc
  // dù form đã đổi — chỉ không chạm DOM của ý định hiện tại. FIX03 R1: `pham` = phạm vi khóa (định danh nháp MỚI) để hai nháp mới khác nhau có body
  // trùng không dùng chung khóa/kết quả.
  async function gui(path, body, ok, f, sau, fv0, pham = null) {
    const fv = fv0 || fenceForm(f);
    if (!f()) return null;  // vận chuyển không hợp lệ (vai/lựa chọn/nháp khác): không gửi, không hiệu ứng (fv ⊆ f)
    const k = JSON.stringify([path, body, pham]);
    let rec = khoaMap.get(k);
    if (rec && rec.chu) return null;  // lần trước còn bay: 0 POST thêm
    if (!rec) { rec = {khoa: taoKhoa(), chu: null}; khoaMap.set(k, rec); }
    const ve_ = {}; rec.chu = ve_;
    if (fv()) { veGuiLai(null); trangThai("Đang gửi…"); }
    let xong = false, r = null;
    try {
      r = await docJson(await goi("/api/crm/" + path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({...body, khoa: rec.khoa})}));
      xong = true;
    } catch (e) {
      if (!chuaRo(e)) xong = true;
      if (rec.chu === ve_) rec.chu = null;
      if (xong && khoaMap.get(k) === rec) khoaMap.delete(k);
      const lai = {path, body, ok, f, sau, fv, pham, k, cho: dangXuLy(e)};
      if (sau && chuaRo(e)) sau.lai = lai;  // giữ để đối soát đúng ý định gốc (R1: nháp mới chưa rõ không tạo bản thứ hai)
      if (!fv()) return null;  // lỗi/chưa rõ của ý định cũ: không toast/trạng thái/nút (khóa vẫn giữ nếu chưa rõ)
      const msg = dangXuLy(e) ? `${e.message || "Đang xử lý."} — kết quả chưa rõ; khóa và nội dung gốc được giữ, bấm Đối soát y nguyên (không tự gửi lại).`
        : ((e && e.message) || String(e));
      K.toast(msg, true); trangThai(msg, true);
      if (chuaRo(e)) veGuiLai(lai);
      return null;
    }
    if (rec.chu === ve_) rec.chu = null;
    if (khoaMap.get(k) === rec) khoaMap.delete(k);  // FINAL
    if (sau) sau.lai = null;
    if (!f()) return null;
    if (fv()) { const lai = r && r.lap_lai ? " (biên nhận cũ của cùng yêu cầu — không ghi thêm)" : ""; if (ok) { K.toast(ok + lai); trangThai(ok + lai); } }
    if (sau) await sau(r, fv);
    return r;
  }
  function veGuiLai(lai) {
    if (!oGuiLai) return;
    if (!lai) { oGuiLai.replaceChildren(); return; }
    oGuiLai.replaceChildren(node("span", lai.cho ? "Lệnh đang xử lý/chưa rõ kết quả. " : "Chưa rõ kết quả lần gửi trước. "),
      nut(lai.cho ? "Đối soát y nguyên (cùng khóa)" : "Gửi lại y nguyên (cùng khóa)", async () => {
        if (!lai.f() || !khoaMap.has(lai.k)) {  // vận chuyển không hợp lệ hoặc ý định đã có kết quả cuối: không POST
          if (lai.fv()) veGuiLai(null);  // chỉ dọn nút khi form vẫn là form của ý định gốc
          return;
        }
        await gui(lai.path, lai.body, lai.ok, lai.f, lai.sau, lai.fv, lai.pham);  // đúng body/khóa/fence/phần tiếp/phạm vi GỐC
      }, "button primary"));
  }
  async function taiTep(xuatId, loai) {  // fence trước request, sau mọi await, ngay trước click
    const gf = genForm, f = fence(() => gf === genForm);
    if (!f()) return;
    try {
      const res = await goi(`/api/crm/giao-ket/tep/${encodeURIComponent(xuatId)}/${loai}`);
      if (!f()) return;
      const blob = await res.blob();
      if (!f() || !blob.size) { if (f()) trangThai("Tệp tải về rỗng — không lưu.", true); return; }
      const url = URL.createObjectURL(blob), a = node("a"); a.href = url; a.download = `${xuatId}.${loai}`; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      trangThai(`Đã tải ${loai.toUpperCase()} (${blob.size} byte).`);
    } catch (e) { if (f()) { K.toast(e.message, true); trangThai(e.message, true); } }
  }

  // ------------------------------------------------------------------ nạp (chỉ GET mới nhất của đúng epoch/lựa chọn được ghi)
  // FIX02 #2: kết quả GET của ý định cũ khi người dùng đã gõ → im lặng (không thông báo cũ, không vẽ lại); bấm ↻ Làm mới để nạp.
  // FIX01 #1: fence của Ý ĐỊNH GỐC (epoch + actor + lựa chọn + thế hệ form) truyền xuyên mọi bước của chuỗi làm mới: danh sách đã thấy người dùng gõ
  // → chuỗi DỪNG (không mở GET chi tiết thế hệ mới rồi ghi đè); thành công/lỗi/toast cũ không đổi chế độ/lựa chọn/nháp.
  async function napDs(fs0) {
    if (K.vaiDangChan("crm_gk")) return false;
    const e = ep, g = ++genDs, fs = fs0 || formCon(), dung = () => e === ep && g === genDs;
    try {
      const s = await (await goi("/api/crm/bao-gia")).json();
      if (!dung()) return false;
      if (actor() !== null && s.nguoi && s.nguoi.dang_nhap !== actor()) { ep += 1; boChon(); khoaMap.clear(); nhapGt.clear(); }
      ds = s;
      if (!fs()) return false;
      ve();
      return true;
    } catch (err) {
      if (!dung() || !fs()) return false;
      if (loiAnNinh(err)) { ds = null; boChon(); ve(); }
      trangThai(err.message, true);
      return false;
    }
  }
  function nap(kind, id, gen, gan, fs0) {  // GET chi tiết theo thế hệ + lựa chọn + fence của ý định gốc; người dùng đã nhập → không đè nháp
    if (K.vaiDangChan("crm_gk")) return Promise.resolve();
    const e = ep, fs = fs0 || formCon();
    return goi(`/api/crm/${kind}/${encodeURIComponent(id)}`).then(r => r.json()).then(d => {
      if (!(e === ep && gen())) return;
      if (!fs()) return;
      gan(d); ve();
    }).catch(err => { if (e === ep && gen() && fs()) { if (err.status === 404 || loiAnNinh(err)) { boChon(); ve(); } trangThai(err.message, true); } });
  }
  function napBgCt(fs0) { if (!bgChon || bgChon === "MOI") return Promise.resolve(); const id = bgChon, g = ++genBg;
    return nap("bao-gia", id, () => g === genBg && bgChon === id, d => { bgCt = d; ghiFormBg(d); }, fs0); }
  function napSoCt(fs0) { if (!soChon) return Promise.resolve(); const id = soChon, g = ++genSo;
    return nap("soan", id, () => g === genSo && soChon === id, d => { soCt = d; ghiFormSo(d); napKySau(d); }, fs0); }
  async function napLai(fs0) {
    const fs = fs0 || formCon(), m = cheDo;
    await napDs(fs);
    if (!fs() || m !== cheDo) return;  // người dùng đã gõ/đổi chế độ trong lúc chờ: không mở thêm GET ghi đè
    if (m === "bao_gia" && bgChon) await napBgCt(fs);
    if (m === "soan" && soChon) await napSoCt(fs);
  }
  function boChon() { bgChon = null; bgCt = null; soChon = null; soCt = null; genForm += 1; genBg += 1; genSo += 1; dongBo = soSua; xemTruoc = null; nhapMoi = null;
    kyCt = null; kyMo = null; kyTep = null; genKy += 1; }  // G4: điều kiện/dialog/tệp của HĐ cũ hết hiệu lực (ý định chưa rõ vẫn giữ trong kyYD)
  function xoa() { ep += 1; ds = null; boChon(); khoaMap.clear(); nhapGt.clear(); revDaLuu.clear(); soDongBg = 1; soDongSo = 0; if (oGuiLai) oGuiLai.replaceChildren(); ve(); trangThai("");
    Promise.resolve().then(() => napDs()); }
  K.dangKyVai("crm_gk", xoa, () => { napDs(); if (bgChon) napBgCt(); if (soChon) napSoCt(); });

  // ------------------------------------------------------------------ form báo giá ↔ nháp
  const COT_L = ["id", "lan", "loai", "tl", "st", "tt", "ml", "mn", "ms", "gc"];
  function ghiLich(p, rows) { xoaNhap(p + "l-"); rows.forEach((r, i) => { const v = {id: r.dong_id || "", lan: r.lan || "", loai: r.loai || "", tl: r.ty_le || "", st: r.so_tien || "",
    tt: r.tien_te || "", ml: r.moc_loai || "", mn: r.moc_ngay || "", ms: r.moc_su_kien || "", gc: r.ghi_chu || ""}; COT_L.forEach(c => nhapGt.set(`gk-${p}l-${c}-${i}`, v[c])); }); }
  function docLich(p, n) {
    return Array.from({length: n}, (_, i) => { const g = c => s0(gt(`${p}l-${c}-${i}`)); const loai = g("loai"), ml = g("ml");
      return {dong_id: g("id"), lan: g("lan") || String(i + 1), loai, ty_le: loai === "PERCENT" ? g("tl") : null, so_tien: loai === "AMOUNT" ? g("st") : null,
        tien_te: loai === "AMOUNT" ? g("tt") : null, moc_loai: ml, moc_ngay: ml === "NGAY" ? g("mn") : null, moc_su_kien: ml === "SU_KIEN" ? g("ms") : null, ghi_chu: g("gc")}; });
  }
  function ghiFormBg(d) {
    xoaNhap("bg-");
    const q = d.du_lieu, set = (k, v) => nhapGt.set("gk-bg-" + k, v ?? "");
    set("loai", q.loai_hinh_id); set("du-an", q.du_an_id); set("g7", q.giai_doan_g7); set("nguon", q.nguon_lich); set("lo", q.don_vi.ma); set("lo-mt", q.don_vi.mo_ta);
    set("khach", q.khach.doi_tac_id); set("khach-dt", q.khach.du_thao && q.khach.du_thao.ten); set("khach-lh", q.khach.du_thao && q.khach.du_thao.lien_he);
    set("tt", q.gia.tien_te); set("dg", q.gia.don_gia); set("dt", q.gia.dien_tich); set("tong", q.gia.tong); set("thue", q.gia.co_so_thue); set("vat", q.gia.vat_phan_tram);
    set("fx", q.fx && q.fx.ty_gia); set("fx-ngay", q.fx && q.fx.ngay); set("pbt", q.phi_bao_tri && q.phi_bao_tri.gia_tri);
    set("pbt-tt", q.phi_bao_tri && q.phi_bao_tri.tien_te); set("pbt-cs", q.phi_bao_tri && q.phi_bao_tri.co_so); set("het", q.het_han); set("gc", q.ghi_chu);
    ghiLich("bg-", q.lich); soDongBg = Math.max(1, q.lich.length);
    dongBo = soSua; xemTruoc = null; revDaLuu.delete(d.bao_gia.id);  // form = đúng revision máy chủ
  }
  function docBaoGia() {
    const g = k => s0(gt("bg-" + k)), dt = g("khach-dt");
    return {loai_hinh_id: g("loai"), du_an_id: g("du-an"), giai_doan_g7: g("g7"), nguon_lich: g("nguon") || "KHACH",
      don_vi: {ma: g("lo"), mo_ta: g("lo-mt")}, khach: {doi_tac_id: g("khach"), du_thao: dt ? {ten: dt, lien_he: g("khach-lh")} : null},
      gia: {tien_te: g("tt"), don_gia: g("dg"), dien_tich: g("dt"), tong: g("tong"), co_so_thue: g("thue"), vat_phan_tram: g("vat")},
      fx: g("fx") ? {cap: "USD/VND", ty_gia: g("fx"), ngay: g("fx-ngay")} : null,
      phi_bao_tri: g("pbt") ? {gia_tri: g("pbt"), tien_te: g("pbt-tt"), co_so: g("pbt-cs")} : null,
      lich: docLich("bg-", soDongBg), het_han: g("het"), ghi_chu: g("gc")};
  }
  // FIX01 #4: phía tự tính (tỷ lệ ↔ số tiền) + VND tham chiếu TỪNG dòng, CHỈ ĐỌC, lấy từ phép tính typed của MÁY CHỦ: kết quả tính thử khớp ĐÚNG form
  // hiện tại, hoặc revision đã lưu khi không có thay đổi chưa lưu; ngoài ra hiện “chưa tính”.
  function tinhChoForm(p) {
    if (p === "bg-") { if (xemTruoc && xemTruoc.khoa === JSON.stringify(docBaoGia())) return xemTruoc.tinh; return !chuaLuu() && bgCt && bgChon !== "MOI" ? bgCt.tinh : null; }
    return !chuaLuu() && soCt ? soCt.tinh : null;
  }
  function tuTinh(t, i, loai) {
    if (!t || !t.dong || !t.dong[i]) return "— chưa tính (Lưu hoặc Tính thử)";
    const x = t.dong[i], tt = t.tien_te, out = [];
    if (loai === "PERCENT") out.push(x.so_tien_minor != null ? `= ${minorSangChinh(x.so_tien_minor, tt)} ${tt}` : "số tiền: chưa tính được");
    if (loai === "AMOUNT") out.push(x.ty_le != null ? `= ${x.ty_le}%` : "tỷ lệ: chưa tính được/không hữu hạn");
    if (t.vnd_tham_chieu && t.vnd_tham_chieu.dong[i] != null) out.push(`VND tham chiếu ${t.vnd_tham_chieu.dong[i]}`);
    if (x.loi && x.loi.length) out.push("lỗi: " + x.loi.join(", "));
    return out.join(" · ");
  }
  function veLich(p, n, setN) {
    const t = tinhChoForm(p);
    const rows = Array.from({length: n}, (_, i) => {
      const lan = nhap(`${p}l-lan-${i}`, String(i + 1)), loai = chon(`${p}l-loai-${i}`, [["PERCENT", "%"], ["AMOUNT", "Số tiền"]], "", "—");
      const tl = nhap(`${p}l-tl-${i}`, ""), st = nhap(`${p}l-st-${i}`, ""), ml = chon(`${p}l-ml-${i}`, [["NGAY", "Ngày"], ["SU_KIEN", "Sự kiện"]], "", "—");
      const mn = nhap(`${p}l-mn-${i}`, "", "date"), ms = nhap(`${p}l-ms-${i}`, ""), gc = nhap(`${p}l-gc-${i}`, "");
      tl.placeholder = "vd 30"; st.placeholder = "vd 1500000000"; ms.placeholder = "BAN_GIAO";
      [lan, loai, tl, st, ml, mn, ms, gc].forEach(x => x.setAttribute("aria-label", `Dòng ${i + 1} · ${x.id}`));
      const tt = chon(`${p}l-tt-${i}`, [["VND", "VND"], ["USD", "USD"]], "", "— tiền tệ quote —");
      const gtr = node("div"); gtr.append(loai, tl, st, tt); const mc = node("div"); mc.append(ml, mn, ms);
      const tu = node("small", tuTinh(t, i, s0(gt(`${p}l-loai-${i}`))), "gk-tu-tinh"); dsTuTinh.push(tu);
      return [lan, gtr, tu, mc, gc, nut("Bỏ", () => { const r = docLich(p, n); r.splice(i, 1); ghiLich(p, r); setN(r.length); genForm += 1; soSua += 1; ve(); }, "link-button", n <= 1)];
    });
    return [bang(["Lần", "Giá trị", "Tự tính (chỉ đọc)", "Mốc thời gian", "Ghi chú", ""], rows),
      nut("+ Dòng", () => { const r = docLich(p, n); r.push({}); ghiLich(p, r); setN(r.length); genForm += 1; soSua += 1; ve(); }, "link-button")];
  }
  function veKiem(t, them) {  // danh sách thiếu/cảnh báo/chặn do MÁY CHỦ tính trên revision đã lưu
    const w = node("div", undefined, "gk-kiem");
    if (!t) { w.append(node("p", "Chưa có kết quả kiểm — lưu nháp để máy chủ tính.")); return w; }
    const muc = (tieuDe, arr, cls) => { if (!arr || !arr.length) return; w.append(node("h4", tieuDe)); const ul = node("ul", undefined, cls);
      arr.forEach(x => { const li = node("li", x.thong_bao || x.ma + (x.truong ? ` (${x.truong})` : "")); if (them && x.truong) li.append(" ", nut("→", () => them(x.truong), "link-button")); ul.append(li); }); w.append(ul); };
    const tong = node("p", (chuaLuu() ? "[Revision đã lưu — form có thay đổi chưa lưu] " : "")
      + `Tổng giá trị: ${t.tong_minor !== null && t.tong_minor !== undefined ? t.tong_minor + " " + (t.tien_te || "") + " (đơn vị nhỏ nhất)" : "chưa tính được"} · tổng tỷ lệ: ${t.tong_ty_le ?? "—"}%`
      + (t.vnd_tham_chieu ? ` · VND tham chiếu: ${t.vnd_tham_chieu.tong ?? "—"}` : ""));
    tong.dataset.kiemTong = "1"; dsKiemTong.push(tong); w.append(tong);
    muc("Chặn In/Xuất", t.chan_in || t.chan_xuat, "gk-chan"); muc("Thiếu (vẫn lưu được)", t.thieu, ""); muc("Cảnh báo", t.canh_bao, "gk-canh-bao");
    return w;
  }

  // ------------------------------------------------------------------ vẽ
  function ve() {
    if (!oNoiDung) dungKhung();
    dsCanLuu = []; dsLyDo = []; dsTuTinh = []; dsKiemTong = [];
    $("gk-vai").textContent = ds ? `Vai hiện hành: ${ds.nguoi.dang_nhap} (${ds.nguoi.vai_tro})` : "Đang tải…";
    oNoiDung.replaceChildren(...(cheDo === "bao_gia" ? veBg() : veSo()));
  }
  function dungKhung() {
    const head = node("div", undefined, "section-heading"), td = node("div"), h2 = node("h2", "6 · Báo giá → Soạn hợp đồng từ mẫu"); h2.id = "crm-gk-title";
    const vai = node("p", "Đang tải…"); vai.id = "gk-vai";
    td.append(h2, node("p", "G2: báo giá hai cột (nhập tay, số chính xác, FX tham chiếu nhập tay) — lưu nháp/in PDF/chuyển. G3: soạn ba cột theo mẫu CFO đã duyệt đã ghim — xuất DOCX + PDF thật (Chờ ký). Không sinh nghĩa vụ/công nợ/M1."), vai);
    head.append(td, nut("↻ Làm mới", () => napLai(), "button secondary"));
    const tabs = node("div", undefined, "demo-actions");
    tabs.append(nut("Báo giá (G2)", () => { cheDo = "bao_gia"; genForm += 1; ve(); }, "button secondary"), nut("Soạn hợp đồng (G3)", () => { cheDo = "soan"; genForm += 1; ve(); }, "button secondary"));
    oTrangThai = node("p", "", "upload-status"); oTrangThai.setAttribute("role", "status"); oTrangThai.setAttribute("aria-live", "polite");
    oGuiLai = node("div", undefined, "demo-actions"); oNoiDung = node("div");
    goc.replaceChildren(head, tabs, oTrangThai, oGuiLai, oNoiDung);
  }
  function veBg() {
    if (!ds) return [K.empty("Chưa tải báo giá", "Bấm ↻ Làm mới; cần kho DEMO PostgreSQL đã chuẩn bị.")];
    const out = [];
    if (!ds.ghi_nguon.san_sang) out.push(node("p", "Chưa cấu hình kết nối máy chủ (chủ CSDL) — lưu/in/chuyển sẽ báo chưa sẵn sàng.", "upload-status error"));
    out.push(node("h3", "Danh sách báo giá"), ds.bao_gia.length ? bang(["Số", "Ngày", "Khách", "Lô/căn", "Giá trị", "Trạng thái", "Người lập", ""], ds.bao_gia.map(b => [
      b.so_bao_gia, b.ngay, b.khach || "—", b.lo_can || "—", b.tong_hien_thi || "chưa tính được", TT_BG[b.trang_thai] || b.trang_thai, b.tao_boi,
      nut(bgChon === b.id ? "Đang mở" : "Mở", () => { boChon(); bgChon = b.id; ve(); napBgCt(); }, "link-button", bgChon === b.id)])) : K.empty("Chưa có báo giá trong phạm vi vai này", ""));
    out.push(nut("+ Báo giá mới", () => { boChon(); xoaNhap("bg-"); soDongBg = 1; bgChon = "MOI"; nhapMoi = {so: ++soNhapMoi, tao: null}; dongBo = soSua; xemTruoc = null; ve(); },
      "button primary"));
    if (bgChon) out.push(...veBgEditor());
    return out;
  }
  function veBgEditor() {
    if (bgChon !== "MOI" && (!bgCt || bgCt.bao_gia.id !== bgChon)) return [node("p", "Đang tải báo giá…")];
    const b = bgCt && bgChon !== "MOI" ? bgCt.bao_gia : null, sua = !b || b.trang_thai === "NHAP";
    const nm0 = b ? null : nhapMoi;  // FIX03 R1: nháp mới nào đang vẽ (MOI → MOI sau "+ Báo giá mới" là nháp KHÁC → fence cũ sai)
    const f = fence(() => bgChon === (b ? b.id : "MOI") && cheDo === "bao_gia" && (!!b || nhapMoi === nm0));
    const trai = node("div", undefined, "gk-cot"), phai = node("div", undefined, "gk-cot");
    const loai = ds.loai_hinh.map(l => [l.id, `${l.phap_nhan} · ${l.ma} v${l.phien_ban}`]);
    trai.append(node("h4", b ? `${b.so_bao_gia} · rev ${b.revision_hien_hanh} · ${TT_BG[b.trang_thai]}` : "Báo giá mới"),
      truong("Pháp nhân · loại hình", chon("bg-loai", loai, loai.length ? loai[0][0] : "", undefined), true),
      truong("Dự án", chon("bg-du-an", ds.du_an.map(a => [a.id, `${a.phap_nhan} · ${a.ma_junsky}`]), "", "— chưa chọn —")),
      truong("Nguồn lịch", chon("bg-nguon", [["KHACH", "Theo khách (nhập tay)"], ["DU_AN", "Theo bộ chuẩn dự án (G7)"]], "KHACH", undefined, () => ve())),  // hiện/ẩn nút nạp G7
      truong("Giai đoạn bộ chuẩn", nhap("bg-g7", "")),
      truong("Khách hàng (đã có mã)", chon("bg-khach", ds.khach.map(k => [k.id, `${k.ten} (${k.ma})`]), "", "— khách dự thảo —")),
      truong("Tên khách dự thảo (chưa mã)", nhap("bg-khach-dt", "")), truong("Liên hệ", nhap("bg-khach-lh", "")),
      truong("Mã lô/căn", nhap("bg-lo", ""), true), truong("Mô tả lô/căn", nhap("bg-lo-mt", "")),
      truong("Tiền tệ", chon("bg-tt", [["VND", "VND"], ["USD", "USD"]], "VND"), true), truong("Đơn giá", nhap("bg-dg", "")), truong("Diện tích", nhap("bg-dt", "")),
      truong("Tổng giá trị (khai báo)", nhap("bg-tong", ""), true), truong("Cơ sở thuế", chon("bg-thue", [["NET", "Chưa gồm VAT"], ["GROSS", "Đã gồm VAT"]], "", "— chưa chọn —"), true),
      truong("VAT % (khai báo)", nhap("bg-vat", "")), truong("Tỷ giá USD/VND (nhập tay)", nhap("bg-fx", "")), truong("Ngày tỷ giá", nhap("bg-fx-ngay", "", "date")),
      truong("Phí bảo trì", nhap("bg-pbt", "")), truong("Tiền tệ phí bảo trì", chon("bg-pbt-tt", [["VND", "VND"], ["USD", "USD"]], "", "—")),
      truong("Cơ sở phí bảo trì", nhap("bg-pbt-cs", "")), truong("Hết hạn (nếu khai)", nhap("bg-het", "", "date")), truong("Ghi chú", nhap("bg-gc", "")));
    phai.append(node("h4", "Lịch thanh toán"), ...veLich("bg-", soDongBg, n => { soDongBg = Math.max(1, n); }));
    if (s0(gt("bg-nguon")) === "DU_AN") phai.append(nut("Nạp bộ chuẩn dự án vào lịch", () => napG7(f), "button secondary"));
    phai.append(veKiem(bgCt && bgChon !== "MOI" ? bgCt.tinh : null));
    const hd = node("div", undefined, "demo-actions");
    if (sua) hd.append(nut("Lưu nháp", async () => {
      // FIX02 #2 + FIX03 R1: báo giá MỚI do một lần lưu trước của CHÍNH nháp này tạo (người dùng gõ tiếp trong lúc chờ) → lần lưu sau là revision của
      // đúng báo giá đó. Định danh lấy từ `nm` của nháp đang vẽ — nháp mới khác (sau "+ Báo giá mới") không bao giờ nhận ID/revision này.
      const nm = nm0;
      if (nm && !nm.tao && nm.choTao && nm.choTao.lai && khoaMap.has(nm.choTao.lai.k)) {  // lần TẠO trước của nháp này chưa rõ → không tạo bản thứ hai
        trangThai("Lần tạo báo giá trước của nháp này chưa rõ kết quả — bấm Gửi lại/Đối soát y nguyên lần đó trước (không tạo báo giá thứ hai).", true);
        veGuiLai(nm.choTao.lai);
        return;
      }
      const id = b ? b.id : (nm && nm.tao ? nm.tao.id : null);
      const body = {bao_gia_id: id, expected_revision: id ? (revDaLuu.get(id) ?? (b ? b.revision_hien_hanh : nm.tao.revision)) : null, du_lieu: docBaoGia()};
      const sau = async (r, fv) => {
        if (nm) nm.tao = {id: r.bao_gia_id, revision: r.revision};  // chỉ ghi vào ĐÚNG định danh nháp của ý định này
        if (!fv()) {  // người dùng đã gõ tiếp: chỉ ghi nhận trạng thái vận chuyển (revision mới), không thông báo/làm mới/đè nháp; form vẫn "chưa lưu"
          revDaLuu.set(r.bao_gia_id, r.revision);
          return;
        }
        bgChon = r.bao_gia_id; nhapMoi = null;
        const fv2 = fenceForm(fence(() => bgChon === r.bao_gia_id && cheDo === "bao_gia"));  // chính lệnh này vừa đổi lựa chọn MOI → id
        if (await napDs(fv2) && fv2()) await napBgCt(fv2);
      };
      if (nm && !id) nm.choTao = sau;  // `sau.lai` do gui đặt khi kết quả chưa rõ
      await gui("bao-gia/luu", body, "Đã lưu nháp", f, sau, null, nm ? nm.so : null);
    }, "button primary"));
    if (sua) hd.append(nut("Tính thử (không lưu)", async () => {
      // FIX01 #4: máy chủ tính đúng phép tính typed của dịch vụ trên form hiện tại; chỉ hiển thị khi form chưa đổi sau khi gửi
      const fc = formCon(), du = docBaoGia(), khoa = JSON.stringify(du);
      if (!f()) return;
      try {
        const r = await docJson(await goi("/api/crm/bao-gia/xem-truoc", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({du_lieu: du})}));
        if (!f() || !fc()) return;
        xemTruoc = {khoa, tinh: r.tinh}; ve(); trangThai("Đã tính thử — chưa lưu; In/Chuyển vẫn dùng revision đã lưu.");
      } catch (e) { if (f() && fc()) trangThai(e.message, true); }
    }, "button secondary"));
    // FIX01 #3: In/Chuyển dùng REVISION ĐÃ LƯU — còn thay đổi chưa lưu thì vô hiệu kèm lý do (cổng In 100%/FX KHÔNG chặn Lưu/Chuyển)
    const ly = chuaLuu() ? LY_CHUA_LUU : "";
    if (b && b.trang_thai !== "HUY") hd.append(oLyDo(ly));
    if (b && b.trang_thai !== "HUY") hd.append(nutLuuTruoc("In báo giá (PDF)", async () => {
      await gui("bao-gia/in", {bao_gia_id: b.id, expected_revision: b.revision_hien_hanh}, "", f, async (r, fv) => {
        if (!fv()) return;
        trangThai(`In: ${TT_XUAT[r.trang_thai] || r.trang_thai}${r.lap_lai ? " (biên nhận cũ)" : ""}`, r.trang_thai !== "PDF_DAT");
        await napBgCt(fv);
      });
    }, "button secondary"));
    if (b && b.trang_thai === "NHAP") {
      const mau = (bgCt.mau_hieu_luc || []).map(m => [m.mau_phien_ban_id, `${m.ma_mau} v${m.phien_ban} (hiệu lực ${m.valid_from})`]);
      if (mau.length) hd.append(truong("Mẫu hợp đồng hiệu lực", chon(`bg-mau-${b.id}`, mau, mau[0][0])), nutLuuTruoc("Chuyển sang Soạn", async () => {
        await gui("bao-gia/chuyen", {bao_gia_id: b.id, expected_revision: b.revision_hien_hanh, mau_phien_ban_id: gt(`bg-mau-${b.id}`, mau[0][0])}, "Đã chuyển sang Soạn", f,
          async (r, fv) => {
            // FIX02 #2: người dùng đã gõ trên cùng báo giá trong lúc Chuyển còn chờ → KHÔNG đổi chế độ/lựa chọn, không GET đè nháp, không thông báo cũ
            if (!fv()) return;
            cheDo = "soan"; boChon(); soChon = r.soan_id;
            const f2 = fenceForm(fence(() => soChon === r.soan_id && cheDo === "soan"));  // chụp NGAY sau chuyển trạng thái do chính lệnh này
            if (await napDs(f2) && f2()) await napSoCt(f2);
          });
      }, "button primary"));
      else hd.append(node("span", "Chưa có mẫu hợp đồng hiệu lực cho loại hình này — chưa chuyển được."));
      hd.append(truong("Lý do hủy", nhap(`bg-huy-${b.id}`, "")), nut("Hủy nháp", async () => {
        const ly = s0(gt(`bg-huy-${b.id}`)); if (!ly) { trangThai("Hủy cần lý do.", true); return; }
        await gui("bao-gia/huy", {bao_gia_id: b.id, expected_revision: b.revision_hien_hanh, ly_do: ly}, "Đã hủy nháp (lịch sử giữ)", f,
          async (r, fv) => { if (fv()) await napLai(fv); });
      }, "button secondary"));
    }
    if (b && b.trang_thai === "DA_CHUYEN" && bgCt.soan_id) hd.append(nut("Mở bản soạn", () => { cheDo = "soan"; const s = bgCt.soan_id; boChon(); soChon = s; ve(); napSoCt(); }, "button secondary"));
    const khung = node("div", undefined, "gk-2cot"); khung.append(trai, phai);
    const out = [khung, hd];
    if (bgCt && bgChon !== "MOI" && bgCt.xuat.length) out.push(node("h4", "Lần in"), bang(["Rev", "Trạng thái", "Lý do", "Lúc", "", ""], bgCt.xuat.map(x => [x.revision,
      TT_XUAT[x.trang_thai] || x.trang_thai, x.ly_do || "", K.date(x.tao_luc), nut("DOCX ↓", () => taiTep(x.id, "docx"), "link-button"),
      x.trang_thai === "PDF_DAT" ? nut("PDF ↓", () => taiTep(x.id, "pdf"), "link-button") : ""])));
    return out;
  }
  async function napG7(f) {  // bộ chuẩn THẬT đọc qua route G7 hiện có; máy chủ chụp lại khi lưu để so lệch
    const q = {du_an_id: s0(gt("bg-du-an")), giai_doan: s0(gt("bg-g7"))}, gf = genForm;
    if (!q.du_an_id || !q.giai_doan) { trangThai("Chọn dự án và nhập giai đoạn bộ chuẩn.", true); return; }
    try {
      const d = await (await goi("/api/crm/bo-chuan?" + new URLSearchParams(q).toString())).json();
      if (!f() || gf !== genForm) return;  // FIX02 #2: kết quả/lỗi của lần nạp cũ không áp lên form đã đổi
      if (d.trang_thai !== "HIEU_LUC") { trangThai("Chưa có bộ chuẩn hiệu lực — không giả khớp; nhập lịch theo khách.", true); return; }
      // FIX01 #2: giữ loại/thứ tự/mốc/ghi chú; AMOUNT giữ ĐÚNG so_tien_minor + tiền tệ (VND scale 0, USD scale 2) — tiền tệ lạ/dữ liệu hỏng → KHÔNG nạp
      const rows = [];
      for (const r of d.rows) {
        if (r.gia_tri_loai === "AMOUNT") {
          const st = minorSangChinh(r.so_tien_minor, r.tien_te);
          if (st === null) { trangThai(`Đợt ${r.lan}: số tiền/tiền tệ bộ chuẩn không đọc được chính xác (${r.tien_te || "thiếu tiền tệ"}) — không nạp, lịch giữ nguyên.`, true); return; }
          rows.push({lan: r.lan, loai: "AMOUNT", ty_le: null, so_tien: st, tien_te: r.tien_te, moc_loai: r.moc_loai, moc_ngay: r.moc_ngay, moc_su_kien: r.moc_su_kien, ghi_chu: r.ghi_chu});
        } else rows.push({lan: r.lan, loai: r.gia_tri_loai, ty_le: r.gia_tri_thap_phan, so_tien: null, tien_te: null, moc_loai: r.moc_loai, moc_ngay: r.moc_ngay,
          moc_su_kien: r.moc_su_kien, ghi_chu: r.ghi_chu});
      }
      ghiLich("bg-", rows);
      soDongBg = Math.max(1, rows.length); genForm += 1; soSua += 1; ve(); trangThai(`Đã nạp bộ chuẩn v${d.version.phien_ban} — có thể sửa (sẽ so lệch khi lưu).`);
    } catch (e) { if (f() && gf === genForm) trangThai(e.message, true); }
  }

  // ------------------------------------------------------------------ G3 soạn ba cột
  function ghiFormSo(d) {
    xoaNhap("so-");
    const g = d.du_lieu.gia_tri_truong || {};
    (d.danh_muc || []).forEach(t => { const v = g[t.khoa];
      if (t.kieu === "tien") { nhapGt.set(`gk-so-f-${t.khoa}`, v ? v.so_tien : ""); nhapGt.set(`gk-so-f-${t.khoa}-tt`, v ? v.tien_te : ""); }
      else nhapGt.set(`gk-so-f-${t.khoa}`, v ?? ""); });
    ghiLich("so-", d.du_lieu.bao_gia.lich || []); soDongSo = Math.max(1, (d.du_lieu.bao_gia.lich || []).length);
    dongBo = soSua; revDaLuu.delete(d.soan.id);  // form = đúng revision máy chủ
  }
  function docTruong() {
    const out = {};
    (soCt.danh_muc || []).forEach(t => { const v = s0(gt(`so-f-${t.khoa}`));
      if (t.kieu === "tien") { if (v) out[t.khoa] = {so_tien: v, tien_te: s0(gt(`so-f-${t.khoa}-tt`)) || "VND"}; }
      else if (v !== null) out[t.khoa] = v; });
    return out;
  }
  function baoGiaSo() {  // gửi lại đúng các trường đầu vào (không gửi người nhập FX/kết quả tính do máy chủ ghi)
    const q = soCt.du_lieu.bao_gia;
    return {du_an_id: q.du_an_id, giai_doan_g7: q.giai_doan_g7, nguon_lich: q.nguon_lich, don_vi: {ma: q.don_vi.ma, mo_ta: q.don_vi.mo_ta}, khach: q.khach,
      gia: q.gia, fx: q.fx ? {cap: q.fx.cap, ty_gia: q.fx.ty_gia, ngay: q.fx.ngay} : null, phi_bao_tri: q.phi_bao_tri, lich: docLich("so-", soDongSo),
      het_han: q.het_han, ghi_chu: q.ghi_chu};
  }
  const nhayToi = khoa => { const el = $(`gk-so-f-${khoa}`); if (el && el.focus) el.focus(); trangThai(`Đến trường ${khoa}.`); };
  function veSo() {
    if (!ds) return [K.empty("Chưa tải", "Bấm ↻ Làm mới.")];
    const out = [node("h3", "Bản soạn hợp đồng"), (ds.soan || []).length ? bang(["Mã nội bộ", "Báo giá", "Trạng thái", "Rev", ""], ds.soan.map(s => [s.ma_noi_bo, s.so_bao_gia,
      TT_SO[s.trang_thai] || s.trang_thai, s.revision_hien_hanh, nut(soChon === s.id ? "Đang mở" : "Mở", () => { boChon(); soChon = s.id; ve(); napSoCt(); }, "link-button", soChon === s.id)]))
      : K.empty("Chưa có bản soạn", "Chuyển một báo giá sang Soạn ở tab Báo giá.")];
    if (soChon) out.push(...veSoEditor());
    return out;
  }
  function veSoEditor() {
    if (!soCt || soCt.soan.id !== soChon) return [node("p", "Đang tải bản soạn…")];
    const s = soCt.soan, k = soCt.kiem, f = fence(() => soChon === s.id && cheDo === "soan");
    const trai = node("div", undefined, "gk-cot"), giua = node("div", undefined, "gk-cot gk-van-ban"), phai = node("div", undefined, "gk-cot");
    trai.append(node("h4", `${s.ma_noi_bo} · rev ${s.revision_hien_hanh} · ${TT_SO[s.trang_thai] || s.trang_thai}`));
    Object.entries(k.nhom).forEach(([nhom, ds_]) => {
      trai.append(node("h5", nhom));
      ds_.forEach(t => {
        const typ = t.kieu === "ngay" ? "date" : "text", el = nhap(`so-f-${t.khoa}`, "", typ);
        const w = truong(`${t.nhan}`, el, t.bat_buoc);
        if (t.kieu === "tien") w.append(chon(`so-f-${t.khoa}-tt`, [["VND", "VND"], ["USD", "USD"]], "VND"));
        trai.append(w);
      });
    });
    trai.append(node("h5", "Lịch thanh toán (giữ mã dòng/thứ tự)"), ...veLich("so-", soDongSo, n => { soDongSo = Math.max(1, n); }));
    giua.append(node("h4", `Văn bản mẫu ${soCt.mau.ma_mau} v${soCt.mau.phien_ban} (đã ghim)`));
    k.doan.forEach(dd => { const p = node("p", undefined, "gk-doan"); p.append(node("small", `[${dd.phan} · ${dd.vi_tri}] `));
      dd.manh.forEach(m => { if (m.loai === "van_ban") p.append(m.text); else { const sp = node("span", m.text || `[[${m.ten}]]`, m.text ? "gk-o" : "gk-o gk-o-thieu");
        sp.title = m.truong ? `Trường ${m.truong}` : "Chưa ánh xạ"; sp.addEventListener("click", () => { if (m.truong) nhayToi(m.truong); }); p.append(sp); } });
      giua.append(p); });
    phai.append(veKiem({...soCt.tinh, chan_xuat: k.chan_xuat, chan_in: null, canh_bao: k.canh_bao}, nhayToi));
    // CRM-41-04A: bản soạn đã ký → tham số/lịch/mẫu CHỈ XEM (máy chủ chặn lưu/xuất/công bố hiện hành; vô hiệu nút chỉ là hiển thị)
    const daKy = s.trang_thai === "DA_KY";
    if (daKy) {
      tatNhap(trai);
      const khung = node("div", undefined, "gk-3cot"); khung.append(trai, giua, phai);
      const hd = node("div", undefined, "demo-actions");
      hd.append(node("span", "Bản soạn đã ký — tham số, lịch và mẫu chỉ xem; không lưu/xuất lại (máy chủ chặn). Sửa sau ký chờ quy trình riêng."));
      const out = [khung, hd, ...veKyChuaRo(s), ...veBanKy(s)];
      if (soCt.xuat.length) out.push(node("h4", "Lần xuất"), bang(["Rev", "Trạng thái", "Lý do", "Lúc", "", ""], soCt.xuat.map(x => [x.revision, TT_XUAT[x.trang_thai] || x.trang_thai,
        x.ly_do || "", K.date(x.tao_luc), nut("DOCX ↓", () => taiTep(x.id, "docx"), "link-button"), x.trang_thai === "PDF_DAT" ? nut("PDF ↓", () => taiTep(x.id, "pdf"), "link-button") : ""])));
      if (soCt.revisions.length) out.push(node("h4", "Lịch sử revision"), bang(["Rev", "Mẫu", "Lý do", "Bởi", "Lúc"], soCt.revisions.map(r => [r.revision, r.mau_phien_ban_id === soCt.mau.mau_phien_ban_id ? "mẫu hiện ghim" : "mẫu khác", r.ly_do || "", r.tao_boi, K.date(r.tao_luc)])));
      return out;
    }
    const mau = (soCt.mau_hieu_luc || []).filter(m => m.mau_phien_ban_id !== soCt.mau.mau_phien_ban_id).map(m => [m.mau_phien_ban_id, `${m.ma_mau} v${m.phien_ban}`]);
    if (mau.length) phai.append(truong("Đổi sang mẫu hiệu lực (tường minh)", chon(`so-doi-${s.id}`, mau, "", "— giữ mẫu đã ghim —")), truong("Lý do đổi mẫu", nhap(`so-doi-ly-${s.id}`, "")));
    const hd = node("div", undefined, "demo-actions");
    hd.append(nut("Lưu bản soạn (revision mới)", async () => {
      // FIX02 #3: body mang ĐÚNG mẫu/lý do đổi mẫu + revision mong đợi; Xuất chỉ mở lại khi revision mới đã nạp về form
      const body = {soan_id: s.id, expected_revision: revDaLuu.get(s.id) ?? s.revision_hien_hanh, gia_tri_truong: docTruong(), bao_gia: baoGiaSo(),
        doi_mau_phien_ban_id: s0(gt(`so-doi-${s.id}`)), ly_do: s0(gt(`so-doi-ly-${s.id}`))};
      await gui("soan/luu", body, "Đã lưu bản soạn", f, async (r, fv) => {
        if (!fv()) { revDaLuu.set(s.id, r.revision); return; }  // gõ tiếp trong lúc chờ: chỉ ghi nhận revision, không thông báo/làm mới/đè nháp
        if (await napDs(fv) && fv()) await napSoCt(fv);
      });
    }, "button primary"));
    // FIX01 #3: Xuất dùng revision đã lưu — chưa lưu → vô hiệu + lý do; chặn xuất do máy chủ tính (k.chan_xuat) vẫn giữ
    const xuat = nutLuuTruoc("Xuất DOCX + PDF", async () => {
      await gui("soan/xuat", {soan_id: s.id, expected_revision: s.revision_hien_hanh}, "", f, async (r, fv) => {
        if (!fv()) return;
        trangThai(`Xuất: ${TT_XUAT[r.trang_thai] || r.trang_thai}${r.lap_lai ? " (biên nhận cũ)" : ""}`, r.trang_thai !== "PDF_DAT");
        if (await napDs(fv) && fv()) await napSoCt(fv);
      });
    }, "button secondary");
    if (k.chan_xuat.length > 0) { xuat.disabled = true; delete xuat.dataset.canLuu; xuat.title = "Còn mục chặn xuất (xem cột phải)."; }
    hd.append(xuat, oLyDo(chuaLuu() ? LY_CHUA_LUU : ""));
    if (s.trang_thai === "CHO_KY") hd.append(...nutKy(s));
    const khung = node("div", undefined, "gk-3cot"); khung.append(trai, giua, phai);
    const out = [khung, hd, ...veKyChuaRo(s)];
    if (s.trang_thai === "CHO_KY" && kyMo && kyMo.soan === s.id) out.push(veKyDialog(s));
    if (soCt.xuat.length) out.push(node("h4", "Lần xuất"), bang(["Rev", "Trạng thái", "Lý do", "Lúc", "", ""], soCt.xuat.map(x => [x.revision, TT_XUAT[x.trang_thai] || x.trang_thai,
      x.ly_do || "", K.date(x.tao_luc), nut("DOCX ↓", () => taiTep(x.id, "docx"), "link-button"), x.trang_thai === "PDF_DAT" ? nut("PDF ↓", () => taiTep(x.id, "pdf"), "link-button") : ""])));
    if (soCt.revisions.length) out.push(node("h4", "Lịch sử revision"), bang(["Rev", "Mẫu", "Lý do", "Bởi", "Lúc"], soCt.revisions.map(r => [r.revision, r.mau_phien_ban_id === soCt.mau.mau_phien_ban_id ? "mẫu hiện ghim" : "mẫu khác", r.ly_do || "", r.tao_boi, K.date(r.tao_luc)])));
    return out;
  }

  // ------------------------------------------------------------------ CRM-41-04A G4 ký lần đầu
  // Chỉ gọi route thật của crm_g.py (GET ky/{soan}, POST ky-ket raw PDF + X-CRM-G-Info, GET ban-ky/{id}/tep). Trình duyệt gửi căn cứ dialog đã chụp
  // (revision + bản xuất), tên tệp, ngày ký, co_sua boolean, mô tả khi Có, người ký khách, khóa — KHÔNG actor/PN/trạng thái/hash/kết quả.
  // Quyền/phạm vi/CAS/khóa sau ký do MÁY CHỦ quyết; nút vô hiệu chỉ là hiển thị. Ngày ký KHÔNG là ngày hiệu lực; khai Có KHÔNG là đã trích/đã duyệt.
  const KY_TOI_DA = 50 * 1024 * 1024;  // cùng cap tải lên của máy chủ (intake.MAX_FILE_SIZE); máy chủ kiểm lại
  const HIEN_THI_DA_KY = "Đã ký — chờ kế toán kiểm";
  const LY_KY = {CRM_G_KHONG_CO_QUYEN: "Vai hiện hành không có quyền ký (cần vai Bán hàng + phân công ký kết hiện hành).",
    CRM_KY_CHUA_CO_PHAM_VI: "Chưa cấu hình phạm vi ký hiện hành cho hợp đồng/dự án/khách này — quản trị cấp phạm vi; không suy từ người tạo."};
  const MA_KY_CAN_CU = new Set(["CRM_KY_XUAT_CU", "CRM_GK_REVISION_CU", "CRM_KY_TRANG_THAI", "CRM_KY_XUAT_CHUA_DAT", "CRM_GK_DA_KY", "CRM_KY_DA_KY",
    "CRM_KY_G3_LECH", "CRM_GK_MAU_LECH_GHIM"]);
  const HD_KY = {CRM_KY_KET: "Ký lần đầu (ghi bản ký)", CRM_KY_TAI: "Tải PDF bản ký"};
  function g5Txt(g) {
    if (!g) return "—";
    if (g.trang_thai === "PENDING") return "PENDING — bắt buộc vì khai Có; CHƯA thực hiện (chưa đối chiếu, chưa trích, chưa duyệt)";
    if (g.trang_thai === "NOT_SELECTED") return "NOT_SELECTED — khai Không; chưa áp dụng chọn mẫu (không có nghĩa là đã đối chiếu)";
    return g.trang_thai;
  }
  function tomTatTxt(t) {
    if (!t) return "chưa tính được";
    const tong = t.tong_minor !== null && t.tong_minor !== undefined ? (minorSangChinh(t.tong_minor, t.tien_te) ?? `${t.tong_minor} (đơn vị nhỏ nhất)`) : "chưa tính được";
    return `${t.so_dong ?? "—"} dòng lịch · tổng ${tong} ${t.tien_te || ""}`.trim();
  }
  function tatNhap(el) {  // chỉ xem sau ký: vô hiệu ô nhập/nút trong cột tham số (hiển thị; backend vẫn là nơi chặn)
    if (["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(el.tagName)) { el.disabled = true; el.title = "Bản soạn đã ký — chỉ xem."; }
    for (const c of Array.from(el.children || [])) tatNhap(c);
  }
  function napKySau(d) {  // sau khi nạp bản soạn: điều kiện/bản ký chỉ cho Chờ ký/Đã ký (GET riêng, không chặn form G3)
    if (kyCt && kyCt.soan_id !== d.soan.id) kyCt = null;
    if (d.soan.trang_thai !== "CHO_KY" && d.soan.trang_thai !== "DA_KY") { kyCt = null; genKy += 1; return; }
    const id = d.soan.id;
    Promise.resolve().then(() => napKy(id));
  }
  async function napKy(id) {  // chỉ GET mới nhất của đúng vai/epoch/bản soạn được ghi; GET cũ về trễ bị bỏ (không lùi trạng thái)
    if (K.vaiDangChan("crm_gk")) return;
    const e = ep, a = actor(), g = ++genKy, gf = genForm, dung = () => e === ep && a === actor() && g === genKy && soChon === id;
    try {
      const d = await docJson(await goi(`/api/crm/giao-ket/ky/${encodeURIComponent(id)}`));
      if (!dung()) return;
      kyCt = d;
    } catch (err) {
      if (!dung()) return;
      kyCt = {soan_id: id, loi: (err && err.message) || String(err), quyen: {ky: false, doc: false}};
    }
    if (cheDo === "soan" && gf === genForm) ve();  // người dùng đang gõ: giữ dữ liệu mới, không vẽ lại (caret); lần vẽ sau hiển thị
  }
  function kyDangCho(sid) {  // ý định ký của vai hiện hành trên bản soạn này còn đang gửi/chưa rõ
    for (const y of kyYD.values()) if (!y.het && (y.dangGui || y.chuaRo) && y.actor === actor() && y.soan === sid) return y;
    return null;
  }
  function boKy(y) { y.het = true; y.chuaRo = false; if (kyYD.get(y.k) === y) kyYD.delete(y.k); }
  function nutKy(s) {
    const kc = kyCt && kyCt.soan_id === s.id ? kyCt : null, cc = kc && kc.can_cu;
    let ly = "";
    if (!kc) ly = "Đang tải điều kiện ký…";
    else if (kc.loi) ly = "Không tải được điều kiện ký: " + kc.loi;
    else if (!kc.quyen || !kc.quyen.ky) ly = LY_KY[kc.quyen && kc.quyen.ly_do] || "Vai hiện hành không ký được hợp đồng này.";
    else if (kc.trang_thai !== "CHO_KY" || kc.revision !== s.revision_hien_hanh) ly = "Trạng thái/revision trên máy chủ đã đổi — bấm ↻ Làm mới.";
    else if (!cc || cc.trang_thai !== "PDF_DAT" || cc.revision !== s.revision_hien_hanh || !cc.pdf_sha256) ly = "Bản xuất mới nhất của revision chưa có PDF đạt — chưa ký được.";
    else if (chuaLuu()) ly = LY_CHUA_LUU;
    const b = nut("Ký kết…", () => {
      if (chuaLuu()) { trangThai(LY_CHUA_LUU, true); return; }
      kyMo = {soan: s.id, revision: s.revision_hien_hanh, xuat_id: cc.xuat_id}; kyTep = null; xoaNhap("ky-"); ve();
    }, "button primary", !!ly);
    if (ly) b.title = ly; else { b.dataset.canLuu = "1"; dsCanLuu.push(b); }  // gõ G3 (chưa lưu) → vô hiệu NGAY như Xuất
    const out = [b];
    if (ly) { const sp = node("span", ly, "gk-ly-do"); sp.dataset.lyKy = "1"; out.push(sp); }
    return out;
  }
  function veKyDialog(s) {
    const kc = kyCt && kyCt.soan_id === s.id ? kyCt : null, cc = kc && kc.can_cu;
    const w = node("div", undefined, "gk-ky-dialog card");
    w.setAttribute("role", "dialog"); w.setAttribute("aria-modal", "true"); w.setAttribute("aria-labelledby", "gk-ky-tieu-de");
    Object.assign(w.style, {position: "fixed", left: "50%", top: "50%", transform: "translate(-50%, -50%)", zIndex: "50", maxWidth: "720px", width: "92vw",
      maxHeight: "90vh", overflow: "auto", background: "#fff", boxShadow: "0 10px 40px rgba(0,0,0,.35)", padding: "1rem"});
    const tieuDe = node("h4", `Ký kết ${s.ma_noi_bo} — ghi bản ký lần đầu`); tieuDe.id = "gk-ky-tieu-de";
    w.append(tieuDe);
    const lech = !cc || cc.xuat_id !== kyMo.xuat_id || cc.revision !== kyMo.revision || cc.trang_thai !== "PDF_DAT";
    if (lech) w.append(node("p", "Căn cứ trên máy chủ đã đổi từ khi mở hộp này — Đóng rồi mở lại Ký kết để kiểm căn cứ mới (không ký trên căn cứ cũ).", "upload-status error"));
    if (cc) w.append(node("h5", "Căn cứ ký (bản xuất G3 đã chụp — kiểm trước khi ký)"), bang(["Mục", "Giá trị"], [
      ["Mẫu", `${cc.ma_mau || "—"} v${cc.phien_ban_mau ?? "—"}`], ["Revision bản soạn", String(cc.revision)], ["Bản xuất", `${cc.xuat_id} · ${K.date(cc.tao_luc)} · ${TT_XUAT[cc.trang_thai] || cc.trang_thai}`],
      ["SHA-256 PDF bản xuất", `${cc.pdf_sha256} (${cc.pdf_len} byte)`], ["Bộ render", cc.engine || "—"], ["Số dòng · tổng · tiền tệ", tomTatTxt(cc.tom_tat)]]));
    const fi = node("input"); fi.type = "file"; fi.accept = "application/pdf,.pdf"; fi.id = "gk-ky-tep";
    // CRM-41-04A U2 (File-only): đổi File = ý định hiển thị MỚI → tăng genForm (cơ chế sẵn có) để ACK/lỗi cũ (ht() chụp gf0) không xóa File/đóng dialog mới
    fi.addEventListener("change", () => { kyTep = (fi.files && fi.files[0]) || null; genForm += 1; ve(); });
    w.append(truong("PDF bản đã ký (scan/ký tay đều được)", fi, true),
      node("p", kyTep ? `Đã chọn: ${kyTep.name} (${K.size ? K.size(kyTep.size) : kyTep.size + " byte"})` : "Chưa chọn tệp."),
      truong("Ngày ký", nhap("ky-ngay", "", "date"), true), truong("Người ký phía khách (tùy chọn)", nhap("ky-nguoi", "")),
      truong("Bản ký có sửa so với bản xuất?", chon("ky-co-sua", [["CO", "Có — bản ký có sửa"], ["KHONG", "Không — ký đúng bản xuất"]], "", "— chọn Có/Không —", () => ve()), true));
    if (gt("ky-co-sua") === "CO") w.append(truong("Mô tả nội dung đã sửa", o("ky-mo-ta", node("textarea"), ""), true));
    w.append(node("p", "Ngày ký không phải ngày hiệu lực; ghi bản ký không sinh nghĩa vụ/công nợ. Khai Có → đối chiếu G5 bắt buộc ở trạng thái chờ (chưa thực hiện); khai Không → chưa áp dụng chọn mẫu. Sau ký: chờ kế toán kiểm."));
    const hd = node("div", undefined, "demo-actions");
    hd.append(nut("Ký và lưu bản ký", async () => { const y = kyYDinh(s); if (y) await guiKy(y); }, "button primary", lech || !kc || !kc.quyen || !kc.quyen.ky),
      nut("Đóng", () => { kyMo = null; kyTep = null; xoaNhap("ky-"); ve(); }, "button secondary"));
    w.append(hd);
    return w;
  }
  function kyYDinh(s) {  // ý định ĐỒNG BỘ (không await): kiểm đủ → khóa/header tạo MỘT lần cho đúng (vai, bản soạn, căn cứ, File, khai báo)
    const loi = m => { trangThai(m, true); return null; };
    if (!kyMo || kyMo.soan !== s.id) return loi("Mở hộp Ký kết trước.");
    const kc = kyCt && kyCt.soan_id === s.id ? kyCt : null, cc = kc && kc.can_cu;
    if (!kc || !kc.quyen || !kc.quyen.ky) return loi("Vai hiện hành không có quyền/phạm vi ký hợp đồng này — không gửi.");
    if (!cc || cc.xuat_id !== kyMo.xuat_id || cc.revision !== kyMo.revision || cc.trang_thai !== "PDF_DAT" || !cc.pdf_sha256 || s.trang_thai !== "CHO_KY"
        || s.revision_hien_hanh !== kyMo.revision) return loi("Căn cứ đã đổi hoặc chưa có PDF đạt — Đóng, ↻ Làm mới rồi mở lại Ký kết.");
    const tep = kyTep, ngay = s0(gt("ky-ngay")), nguoi = s0(gt("ky-nguoi")), cs = gt("ky-co-sua"), mo = s0(gt("ky-mo-ta"));
    if (!tep) return loi("Chọn tệp PDF bản đã ký.");
    if (!tep.size) return loi("Tệp rỗng (0 byte) — không gửi.");
    if (tep.size > KY_TOI_DA) return loi("PDF bản ký vượt giới hạn 50 MB — không gửi.");
    if (!/\.pdf$/i.test(tep.name || "") || /[\\/:*?"<>|]/.test(tep.name)) return loi("Chỉ nhận tệp .pdf có tên thuần (không ký tự đặc biệt).");
    if (!ngay) return loi("Nhập ngày ký.");
    if (cs !== "CO" && cs !== "KHONG") return loi("Chọn Có hoặc Không: bản ký có sửa so với bản xuất?");
    const co = cs === "CO", moTa = co ? mo : null;
    if (co && !moTa) return loi("Khai Có cần mô tả nội dung đã sửa.");
    const a = actor(), k = JSON.stringify([a, s.id, kyMo.revision, kyMo.xuat_id, tep.name, tep.size, tep.lastModified, ngay, nguoi, co, moTa]);
    const cu = kyDangCho(s.id);
    if (cu && cu.k !== k) return loi(cu.dangGui ? "Bản ký đang gửi — chờ kết quả, không gửi ý định khác."
      : `Lần ký trước (tệp ${cu.file.name}) chưa rõ kết quả — bấm "Gửi lại bản ký y nguyên" để đối soát trước; không tạo ý định mới.`);
    let y = kyYD.get(k);
    if (y && !y.het) return y;  // cùng ý định: đang gửi → 0 POST; chưa rõ → gửi lại ĐÚNG File/header/khóa gốc
    const khoa = taoKhoa();
    const enc = encodeURIComponent(JSON.stringify({soan_id: s.id, expected_revision: kyMo.revision, expected_xuat_id: kyMo.xuat_id, ten_tep: tep.name,
      ngay_ky: ngay, co_sua: co, mo_ta: moTa, nguoi_ky_khach: nguoi, khoa}));
    if (enc.length > 24000) return loi("Mô tả/tên quá dài.");
    // FIX04 U1: ý định ghi kèm định danh mong đợi (HĐ, revision, bản xuất, hash PDF G3 đã chụp, ngày ký, co_sua) để kiểm ACK trước FINAL
    y = {k, actor: a, soan: s.id, hd: typeof kc.hop_dong_id === "string" ? kc.hop_dong_id : null, revision: kyMo.revision, xuat_id: kyMo.xuat_id,
      g3: cc.pdf_sha256, ngay, co, file: tep, enc, khoa, dangGui: false, chuaRo: false, het: false};
    kyYD.set(k, y);  // giữ chỗ đồng bộ trước mọi await
    return y;
  }
  // FIX04 U1: ACK 2xx chỉ là FINAL khi đúng DTO typed của crm_ky_kq (ky_id UUID, soan/HĐ/revision/bản xuất/ngày ký/co_sua của ĐÚNG ý định gốc,
  // DA_KY, độ dài PDF = File gốc, hash dạng SHA-256, hash PDF G3 = căn cứ đã chụp, lap_lai boolean, G5 khởi tạo đúng PENDING/NOT_SELECTED theo khai báo).
  // Thiếu/sai bất kỳ trường nào → null (KẾT QUẢ CHƯA RÕ): không suy thành công từ HTTP 2xx, không dùng nhãn dự phòng.
  const UUID_KY = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, SHA_KY = /^[0-9a-f]{64}$/;
  function ackKy(y, r) {
    if (!r || typeof r !== "object" || Array.isArray(r)) return null;
    const g5 = r.g5;
    const dung = typeof r.ky_id === "string" && UUID_KY.test(r.ky_id) && r.soan_id === y.soan && r.trang_thai === "DA_KY"
      && typeof y.hd === "string" && r.hop_dong_id === y.hd && r.revision === y.revision && r.xuat_id === y.xuat_id
      && r.ngay_ky === y.ngay && r.co_sua === y.co && r.ky_pdf_len === y.file.size
      && typeof r.ky_pdf_sha256 === "string" && SHA_KY.test(r.ky_pdf_sha256) && typeof y.g3 === "string" && r.g3_pdf_sha256 === y.g3
      && typeof r.lap_lai === "boolean" && !!g5 && typeof g5 === "object" && g5.trang_thai === (y.co ? "PENDING" : "NOT_SELECTED");
    return dung ? {ky_id: r.ky_id, lap_lai: r.lap_lai, g5: {trang_thai: g5.trang_thai}} : null;
  }
  async function guiKy(y) {
    if (y.het || y.actor !== actor()) return;  // ý định của vai khác: không bao giờ gửi dưới vai hiện hành
    if (y.soan !== soChon || cheDo !== "soan") return;  // gửi/gửi lại chỉ từ đúng bản soạn đang mở
    if (y.dangGui) { trangThai("Bản ký đang gửi — chờ kết quả, không gửi lần thứ hai."); return; }
    y.dangGui = true;
    // FIX04 U2: VẬN CHUYỂN (y: File/header/khóa gốc, bền tới FINAL) tách khỏi HIỂN THỊ. `ht` = guard hiển thị CHỤP MỘT LẦN lúc gửi lần này
    // (epoch + vai + bản soạn + chế độ + thế hệ form + thế hệ điều hướng) — không làm tươi sau await. Vai A→B→A, G3→G2→G3, nhập form mới, rời
    // #hopdong ⇒ ht() sai vĩnh viễn: ACK/lỗi cũ chỉ nhả/giữ đúng bản ghi y, không toast/đóng dialog/xóa tệp/nháp, không mở GET làm mới.
    // Gửi lại tường minh từ context mới chụp guard mới cho LẦN gửi lại đó (File/header/khóa vẫn gốc).
    const e0 = ep, a0 = actor(), gf0 = genForm, gv0 = genVao;
    const ht = () => e0 === ep && a0 === actor() && gf0 === genForm && gv0 === genVao && soChon === y.soan && cheDo === "soan" && location.hash === "#hopdong";
    const vf = () => !y.het && ht();
    trangThai(`Đang gửi bản ký ${y.file.name}…`);
    const chuaRoKy = msg0 => {  // KẾT QUẢ CHƯA RÕ: GIỮ File/header/khóa gốc; đường đối soát chỉ hiện trên đúng bản soạn của đúng vai
      y.chuaRo = true;
      if (vf()) { const msg = `${msg0} — bản ký chưa xác nhận; bấm Gửi lại bản ký y nguyên (cùng khóa).`; K.toast(msg, true); trangThai(msg, true); ve(); }
    };
    let r;
    try {
      r = await docJson(await goi("/api/crm/giao-ket/ky-ket", {method: "POST", headers: {"X-CRM-G-Info": y.enc, "Content-Type": "application/pdf"}, body: y.file}));
    } catch (e) {
      y.dangGui = false;
      if (chuaRo(e) && !y.het) { chuaRoKy((e && e.message) || "Chưa rõ kết quả."); return; }
      const hl = vf();
      boKy(y);  // kết quả xác định (khóa không dùng lại) — chỉ nhả ĐÚNG bản ghi y
      if (!hl) return;  // lỗi của ý định thuộc vai/HĐ/chế độ/form/điều hướng cũ: không toast/vẽ/làm mới
      const msg = (e && e.message) || String(e);
      if (MA_KY_CAN_CU.has(e && e.code) || loiAnNinh(e)) {  // căn cứ/quyền đã đổi: đóng dialog, tải lại căn cứ hiện hành; không chọn ngầm bản khác
        kyMo = null; kyTep = null; xoaNhap("ky-");
        K.toast(msg, true); trangThai(`${msg} — đã tải lại căn cứ; mở lại Ký kết để kiểm căn cứ mới.`, true);
        if (await napDs(ht) && ht()) await napSoCt(ht);  // GET làm mới theo guard CHỤP lúc gửi (không chụp mới ở completion)
        return;
      }
      K.toast(msg, true); trangThai(msg, true); ve();
      return;
    }
    y.dangGui = false;
    const ack = ackKy(y, r);
    if (!ack) {  // 2xx nhưng ACK thiếu/rỗng/null/lệch chủ thể-trạng thái-căn cứ: CHƯA RÕ, không FINAL
      if (!y.het) chuaRoKy("Phản hồi ký không đúng biên nhận mong đợi (thiếu/lệch hợp đồng, căn cứ, ngày ký, khai báo hoặc G5)");
      return;
    }
    const hl = vf();
    boKy(y);  // FINAL (ACK đã kiểm định danh)
    if (!hl) return;  // ACK muộn của context cũ: không toast/vẽ; lần mở lại đọc trạng thái máy chủ
    kyMo = null; kyTep = null; xoaNhap("ky-");
    const msg = `${HIEN_THI_DA_KY}${ack.lap_lai ? " (biên nhận cũ của cùng bản ký — không ghi thêm)" : ""} · G5: ${g5Txt(ack.g5)}`;
    K.toast(msg); trangThai(msg);
    if (await napDs(ht) && ht()) await napSoCt(ht);
  }
  function veKyChuaRo(s) {
    const y = kyDangCho(s.id);
    if (!y || !y.chuaRo || y.dangGui) return [];
    const w = node("div", undefined, "demo-actions"); w.dataset.kyChuaRo = "1";
    w.append(node("span", `Lần ký trước (tệp ${y.file.name}) chưa rõ kết quả. `), nut("Gửi lại bản ký y nguyên (cùng khóa)", () => guiKy(y), "button primary"));
    return [w];
  }
  async function taiBanKy(sid, kyId) {  // fence trước request, sau phản hồi/blob và ngay trước click
    // FIX04 U3: + thế hệ form (G3→G2→G3) + thế hệ điều hướng (rời #hopdong, kể cả đi-rồi-về) + đang ở #hopdong — shell chỉ ẩn trang, nên
    // headers/blob về sau điều hướng không được tạo URL/click.
    const e = ep, a = actor(), g = genKy, gf = genForm, gv = genVao;
    const f = () => e === ep && a === actor() && soChon === sid && cheDo === "soan" && g === genKy && gf === genForm && gv === genVao && location.hash === "#hopdong";
    if (!f()) return;
    try {
      const res = await goi(`/api/crm/giao-ket/ban-ky/${encodeURIComponent(kyId)}/tep`);
      if (!f()) return;
      const blob = await res.blob();
      if (!f()) return;
      if (!blob.size) { trangThai("Tệp tải về rỗng — không lưu.", true); return; }
      if (!f()) return;  // ngay trước tạo URL/click
      const url = URL.createObjectURL(blob), el = node("a"); el.href = url; el.download = `ban-ky-${kyId}.pdf`; document.body.append(el); el.click(); el.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      trangThai(`Đã tải PDF bản ký (${blob.size} byte).`);
    } catch (err) { if (f()) { K.toast(err.message, true); trangThai(err.message, true); } }
  }
  function veBanKy(s) {
    const kc = kyCt && kyCt.soan_id === s.id ? kyCt : null;
    if (!kc) return [node("p", "Đang tải bản ký…")];
    if (kc.loi) return [node("p", "Không tải được bản ký: " + kc.loi, "upload-status error")];
    const bk = kc.ban_ky;
    if (!bk) return [node("h4", "Bản ký & đối chiếu"), node("p", `${kc.hien_thi || HIEN_THI_DA_KY} — vai hiện hành không có quyền xem bản ký/hash.`)];
    const w = node("div", undefined, "gk-ban-ky"); w.setAttribute("aria-label", "Bản ký và đối chiếu");
    w.append(node("h4", "Bản ký & đối chiếu"),
      node("p", `${bk.hien_thi || HIEN_THI_DA_KY}. Ngày ký ${bk.ngay_ky} không phải ngày hiệu lực — hợp đồng chưa hiệu lực, chưa kế toán duyệt.`),
      bang(["Mục", "Giá trị"], [
        ["Ngày ký", bk.ngay_ky], ["Người ký phía khách", bk.nguoi_ky_khach || "—"], ["Người ghi bản ký", bk.tao_boi], ["Lúc ghi", K.date(bk.tao_luc)],
        ["Bản ký có sửa so với bản xuất?", bk.co_sua ? `Có — ${bk.mo_ta_sua || ""}` : "Không"], ["G5 đối chiếu", g5Txt(bk.g5)],
        ["Revision · bản xuất G3", `rev ${bk.revision} · ${bk.xuat_id}`],
        ["SHA-256 PDF bản ký", `${bk.ky_pdf_sha256} (${bk.ky_pdf_len} byte, ${bk.ky_so_trang} trang)`],
        ["SHA-256 PDF bản xuất G3", `${bk.g3_pdf_sha256} (${bk.g3_pdf_len} byte)`], ["Snapshot khi ký", tomTatTxt(bk.tom_tat)]]),
      nut("PDF bản ký ↓", () => taiBanKy(s.id, bk.ky_id), "link-button"));
    if (kc.lich_su && kc.lich_su.length) w.append(node("h5", "Lịch sử bản ký"), bang(["Lúc", "Người", "Hành động"], kc.lich_su.map(x => [K.date(x.luc), x.nguoi, HD_KY[x.hanh_dong] || x.hanh_dong])));
    return [w];
  }

  dungKhung(); ve();
  if (location.hash === "#hopdong") napDs();
  // FIX04 U3: mọi đổi hash (rời hoặc quay lại #hopdong) đổi thế hệ hiển thị G4 TRƯỚC khi nạp lại — callback cũ không hồi hiệu lực
  window.addEventListener("hashchange", () => { genVao += 1; if (location.hash === "#hopdong") napLai(); });
})();

// ===================================================================== CRM-41-06A G6A — kế toán kiểm hợp đồng đã ký từ mẫu + kích hoạt HIỆU LỰC
// Khối #crm-kiem dựng NGAY SAU #crm-gk (index.html không đổi; G1–G4 không đổi). Máy chủ quyết định quyền/phạm vi/đánh giá/kích hoạt; giao diện
// chỉ hiển thị và gửi đúng trường cho phép — KHÔNG gửi actor/PN/chế độ G5/kết quả check/hồ sơ pháp lý. G5 vận hành luôn HOLD (UNREGISTERED_G5_PROOF):
// hiển thị trung thực, không suy "khớp". Trả lại = chặn phụ thuộc, chờ quy trình ký lại (KHÔNG về nháp, không mở khóa bản ký/PDF G4).
// Bất đồng bộ: fence = epoch + actor + bản ký đang mở + thế hệ form + thế hệ điều hướng + đang ở #hopdong (chụp MỘT lần lúc gửi). Ý định lệnh giữ
// ĐÚNG body + khóa tới ACK typed; chưa rõ (mất kết nối/5xx/ACK lệch) → "Gửi lại y nguyên (cùng khóa)"; bấm lặp khi đang gửi → 0 POST; mỗi
// (vai, bản ký) chỉ một ý định đang gửi/chưa rõ — ý định khác không chen. Đổi vai không xóa ý định chưa rõ, nhưng không bao giờ gửi dưới vai khác.
(() => {
  const K = window.kttChung;
  if (!K) return;
  const $ = id => document.getElementById(id);
  const node = K.node;
  const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || "";
  const gk = $("crm-gk");
  if (!gk || typeof gk.after !== "function") return;
  const goc = node("article", undefined, "card");
  goc.id = "crm-kiem"; goc.setAttribute("aria-labelledby", "crm-kiem-title");
  gk.after(goc);

  const CHECKLIST = [["ban_ky_dung_ban_xuat", "Bản ký đúng bản xuất G3 (hoặc phần sửa đã khai)"], ["ben_ky_dung", "Bên ký / người đại diện đúng"],
    ["dieu_khoan_dung", "Điều khoản đúng mẫu CFO đã duyệt"], ["gia_tri_lich_dung", "Giá trị + lịch thu đúng bản ký"], ["khach_dung", "Khách đúng (mã Junsky CÓ SẴN)"]];
  const CAN_CU = [["DIEU_KHOAN_HD", "Điều khoản hiệu lực trong hợp đồng"], ["TRUONG_HOP_DONG", "Trường ngày hiệu lực của hợp đồng"]];
  const TEN = {luu: "Lưu kiểm", check: "Chạy check", "xu-ly-lech": "Xử lý lệch theo bản ký", "bo-sung": "Yêu cầu bổ sung", "tra-lai": "Trả lại (chờ ký lại)",
    "hieu-luc": "Kích hoạt hiệu lực"};
  const HD_LS = {CRM_KY_KET: "Ký lần đầu (G4)", CRM_KIEM_LUU: "Lưu kiểm", CRM_KIEM_CHECK: "Chạy check", CRM_KIEM_XU_LY_LECH: "Xử lý lệch",
    CRM_KIEM_BO_SUNG: "Yêu cầu bổ sung", CRM_KIEM_TRA_LAI: "Trả lại — chờ ký lại", CRM_KIEM_HIEU_LUC: "Kích hoạt hiệu lực", CRM_KIEM_XEM: "Xem", CRM_KIEM_TAI: "Tải tệp"};
  const LY_QUYEN = {CRM_G_CUNG_NGUOI: "Người ghi bản ký không tự kiểm (tách nhiệm) — cần kế toán khác.",
    CRM_KIEM_CHUA_CO_PHAM_VI: "Chưa cấu hình phạm vi kiểm hiện hành cho hợp đồng này — quản trị cấp phạm vi; không suy từ người tạo.",
    CRM_G_KHONG_CO_QUYEN: "Vai hiện hành không có quyền kiểm hợp đồng (cần phân công CRM_HD_KIEM hiện hành)."};
  const MA_CAN_CU = new Set(["CRM_KIEM_REVISION_CU", "CRM_KIEM_CHECK_CU", "CRM_KIEM_TRANG_THAI", "CRM_KIEM_DA_HIEU_LUC", "CRM_KIEM_DA_XU_LY",
    "CRM_KIEM_LECH_KHONG_CON", "CRM_KIEM_CHUA_DU_DIEU_KIEN"]);
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, SHA = /^[0-9a-f]{64}$/;
  const NOI_DUNG = /^kh-(cl-|junsky|ngay|can-cu|trich|ghi-chu)/;
  const LY_CHUA_LUU = "Có thay đổi chưa lưu — bấm Lưu kiểm trước (check/kích hoạt dùng revision đã lưu).";

  let ep = 0, genDs = 0, genCt = 0, genForm = 0, genVao = 0, genTim = 0, genG5 = 0;
  let ds = null, chon = null, ct = null, formCua = null, sua = false;
  let g5v = null, g5Hen = null;  // G5-B: CRM_G5_VIEW_V1 của bản ký đang mở (tách khỏi ct G6A) + hẹn làm mới khi việc đang xử lý
  const ydG5 = new Map();  // ý định lệnh đối chiếu (body + khóa gốc giữ tới ACK CRM_G5_ACK_V1)
  let timTu = "", timKq = null;  // P1-B: tra cứu mã Junsky CÓ SẴN cho khách dự thảo — không phải nội dung kiểm (không làm bẩn form)
  const nhapGt = new Map(), yd = new Map();
  let oTrangThai = null, oNoiDung = null, oVai = null, dsCanLuu = [];
  const actor = () => (ds && ds.nguoi && typeof ds.nguoi.dang_nhap === "string" && ds.nguoi.dang_nhap) || null;
  const dangHopDong = () => location.hash === "#hopdong";
  const taoKhoa = () => "crmkiem-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));
  const s0 = x => { const v = String(x ?? "").trim(); return v === "" ? null : v; };
  class LoiKiem extends Error { constructor(status, code, message) { super(message); this.status = status; this.code = code; } }
  async function goi(path, opts = {}) {
    let res;
    try { res = await fetch(path, {...opts, headers: {"X-KTT-Token": TOKEN, ...(opts.headers || {})}, cache: "no-store", credentials: "same-origin"}); }
    catch (_) { throw new LoiKiem(0, "MAT_KET_NOI", "Mất kết nối — chưa xác định máy chủ đã ghi hay chưa. Khóa và nội dung được giữ; bấm Gửi lại y nguyên."); }
    if (!res.ok) { const r = await res.json().catch(() => ({})); throw new LoiKiem(res.status, r.error || "HTTP_" + res.status, r.message || `Không hoàn tất (${res.status}).`); }
    return res;
  }
  async function docJson(res) {
    try { return await res.json(); }
    catch (_) { throw new LoiKiem(0, "KET_QUA_CHUA_RO", "Phản hồi đọc không trọn — chưa rõ lệnh đã ghi hay chưa. Khóa được giữ; bấm Gửi lại y nguyên."); }
  }
  const chuaRo = e => !!e && (e.status === 0 || e.status >= 500) && e.code !== "CRM_G_CHUA_SAN_SANG";
  const loiAnNinh = e => !!e && (e.status === 401 || e.status === 403 || ["CRM_PHIEN", "DANH_TINH", "DANH_TINH_MO_PHONG"].includes(e.code));
  function trangThai(msg, loi = false) { if (oTrangThai) { oTrangThai.textContent = msg || ""; oTrangThai.className = "upload-status" + (loi ? " error" : ""); } }

  // ------------------------------------------------------------------ ô nhập ghi xuyên (giá trị giữ qua vẽ lại; nội dung kiểm → bẩn tới khi Lưu)
  const gt = id => nhapGt.has("kh-" + id) ? nhapGt.get("kh-" + id) : "";
  const xoaNhap = () => { for (const k of [...nhapGt.keys()]) if (k.startsWith("kh-")) nhapGt.delete(k); };
  function o(id, el, khiDoi) {
    el.id = "kh-" + id;
    if (!nhapGt.has(el.id)) nhapGt.set(el.id, "");
    el.value = nhapGt.get(el.id);
    const doi = () => {
      nhapGt.set(el.id, el.value); genForm += 1;
      if (NOI_DUNG.test(el.id)) { sua = true; dsCanLuu.forEach(b => { b.disabled = true; b.title = LY_CHUA_LUU; }); }
      if (khiDoi) khiDoi(el);
    };
    el.addEventListener("input", doi); el.addEventListener("change", doi);
    return el;
  }
  function nhap(id, type = "text") { const i = node("input"); i.type = type; i.autocomplete = "off"; return o(id, i); }
  function chon_(id, opts, dau, khiDoi) {
    const s = node("select");
    if (dau !== undefined) { const op = node("option", dau); op.value = ""; s.append(op); }
    for (const [v, t] of opts) { const op = node("option", t); op.value = v; s.append(op); }
    return o(id, s, khiDoi);
  }
  function truong(label, el) { const w = node("div", undefined, "gk-truong"), l = node("label", label); l.htmlFor = el.id; w.append(l, el); return w; }
  function nut(text, fn, cls, tat) { const b = node("button", text, cls || "button secondary"); b.type = "button"; b.disabled = !!tat; b.addEventListener("click", () => { if (!b.disabled) fn(b); }); return b; }
  function nutCanLuu(text, fn, cls, ly) {  // dùng revision đã lưu: vô hiệu NGAY khi gõ nội dung kiểm (không chờ vẽ lại)
    const b = nut(text, () => { if (sua) { trangThai(LY_CHUA_LUU, true); return; } fn(); }, cls, !!ly || sua);
    if (ly) b.title = ly; else if (sua) b.title = LY_CHUA_LUU;
    dsCanLuu.push(b); return b;
  }
  function bang(headers, rows) {
    const wrap = node("div", undefined, "table-wrap"), t = node("table"), head = node("thead"), tr = node("tr"), body = node("tbody");
    headers.forEach(x => tr.append(node("th", x))); head.append(tr); t.append(head);
    for (const r of rows) { const row = node("tr"); for (const c of r) { const td = node("td"); if (c instanceof Node) td.append(c); else td.textContent = c ?? ""; row.append(td); } body.append(row); }
    t.append(body); wrap.append(t); return wrap;
  }
  function g5Txt(g) {
    if (!g) return "—";
    const ma = (Array.isArray(g.chan) ? g.chan : []).map(x => x && x.ma).filter(Boolean).join(", ");
    const nhan = g.nhan ? ` [${g.nhan}]` : "";
    if (g.trang_thai === "HOLD") return `HOLD (${ma || "chưa có bằng chứng"})${nhan} — chưa có kết quả/chính sách G5 tin cậy được đăng ký; PENDING/NOT_SELECTED lúc ký KHÔNG phải bằng chứng → chưa kích hoạt được`;
    if (g.trang_thai === "KHOP") return `KHỚP${nhan}`;
    if (g.trang_thai === "LECH") return `LỆCH${nhan} — cần quyết định xử lý theo bản ký`;
    if (g.trang_thai === "KHONG_CHON_MAU") return `Không thuộc mẫu chọn${nhan}`;
    return `${g.trang_thai || "—"}${nhan}`;
  }
  function g4G5Txt(g) {
    if (!g || !g.trang_thai) return "—";
    return `${g.trang_thai} (khởi tạo lúc ký — không phải bằng chứng đối chiếu)`;
  }
  const tienTxt = (m, tt) => m === null || m === undefined ? "chưa tính được" : `${m} ${tt || ""} (đơn vị nhỏ nhất)`.trim();
  const maTxt = arr => (Array.isArray(arr) ? arr : []).map(x => x && (x.ma + (x.muc ? ` (${x.muc})` : "") + (x.dong ? ` · dòng ${x.dong}` : ""))).filter(Boolean);

  // ------------------------------------------------------------------ nạp (chỉ GET mới nhất của đúng epoch/vai/bản ký/điều hướng được ghi)
  async function napDs() {
    if (K.vaiDangChan("crm_kiem")) return false;
    const e = ep, g = ++genDs, gv = genVao, gf = genForm, dung = () => e === ep && g === genDs && gv === genVao && dangHopDong();
    try {
      const s = await docJson(await goi("/api/crm/giao-ket/kiem"));
      if (!dung()) return false;
      if (!s || !Array.isArray(s.ds) || !s.nguoi || typeof s.nguoi.dang_nhap !== "string") throw new LoiKiem(0, "KET_QUA_CHUA_RO", "Danh sách kiểm không đúng cấu trúc.");
      if (actor() !== null && s.nguoi.dang_nhap !== actor()) { ep += 1; boChon(); nhapGt.clear(); }
      ds = s;
      if (gf !== genForm) return false;  // người dùng đang gõ: giữ danh sách mới, không vẽ lại (caret); lần vẽ sau hiển thị
      ve();
      return true;
    } catch (err) {
      if (!dung()) return false;
      if (loiAnNinh(err)) { ds = null; boChon(); ve(); }
      trangThai(err.message, true);
      return false;
    }
  }
  async function napCt(id) {
    if (K.vaiDangChan("crm_kiem")) return false;
    const e = ep, a = actor(), g = ++genCt, gv = genVao, gf = genForm;
    const dung = () => e === ep && a === actor() && g === genCt && gv === genVao && chon === id && dangHopDong();
    try {
      const d = await docJson(await goi(`/api/crm/giao-ket/kiem/${encodeURIComponent(id)}`));
      if (!dung()) return false;
      if (!d || !d.ky || d.ky.ky_id !== id) throw new LoiKiem(0, "KET_QUA_CHUA_RO", "Chi tiết không đúng bản ký đang mở.");
      ct = d;
      napG5(id);  // G5-B: trạng thái đối chiếu đọc RIÊNG (fence riêng), không chặn chi tiết G6A
      if (gf !== genForm) return false;  // đang gõ: không ghi đè form; form giữ revision cũ → máy chủ chặn CAS nếu đã cũ
      ghiForm(d); ve();
      return true;
    } catch (err) {
      if (!dung()) return false;
      ct = {loi: (err && err.message) || String(err), ky: {ky_id: id}};
      ve(); trangThai(ct.loi, true);
      return false;
    }
  }
  async function napLai() { await napDs(); if (chon) await napCt(chon); }
  function ghiForm(d) {
    xoaNhap();
    const rv = d.rev, set = (k, v) => nhapGt.set("kh-" + k, v ?? "");
    for (const [k] of CHECKLIST) set("cl-" + k, rv && rv.checklist ? rv.checklist[k] : "");
    set("junsky", rv && rv.de_xuat_ma_junsky_id); set("ngay", rv && rv.ngay_hieu_luc); set("can-cu", rv && rv.can_cu_ngay);
    set("trich", rv && rv.trich_dan_ngay); set("ghi-chu", rv && rv.ghi_chu);
    sua = false;
    formCua = {ky: d.ky.ky_id, rev: d.ho_so && Number.isInteger(d.ho_so.revision) ? d.ho_so.revision : 0};
  }
  function boChon() {
    chon = null; ct = null; formCua = null; sua = false; genCt += 1; genForm += 1; genTim += 1; timTu = ""; timKq = null; xoaNhap();
    g5v = null; genG5 += 1; if (g5Hen) { clearTimeout(g5Hen); g5Hen = null; }
  }
  function xoa() { ep += 1; ds = null; boChon(); nhapGt.clear(); ve(); trangThai(""); Promise.resolve().then(() => napDs()); }
  K.dangKyVai("crm_kiem", xoa, () => { napDs(); if (chon) napCt(chon); });

  // ------------------------------------------------------------------ ý định lệnh (body + khóa gốc giữ tới ACK typed)
  function yDang(a, ky) { for (const y of yd.values()) if (!y.het && (y.dangGui || y.chuaRo) && y.actor === a && y.ky === ky) return y; return null; }
  function boYD(y) { y.het = true; y.chuaRo = false; if (yd.get(y.k) === y) yd.delete(y.k); }
  function yDinh(hanh, body, kiem, ok) {  // ĐỒNG BỘ (không await): khóa tạo MỘT lần cho (vai, lệnh, body)
    const a = actor();
    if (!a || !ct || !ct.ky || body.ky_id !== chon || typeof ct.ky.hop_dong_id !== "string") { trangThai("Mở bản ký trước.", true); return null; }
    const k = JSON.stringify([a, hanh, body]), cu = yDang(a, body.ky_id);
    if (cu && cu.k !== k) {
      trangThai(cu.dangGui ? `Lệnh "${TEN[cu.hanh]}" đang gửi — chờ kết quả, không gửi lệnh khác.`
        : `Lệnh "${TEN[cu.hanh]}" trước chưa rõ kết quả — bấm Gửi lại y nguyên (cùng khóa) trước; không gửi lệnh khác.`, true);
      return null;
    }
    let y = yd.get(k);
    if (y && !y.het) return y;  // cùng ý định: đang gửi → 0 POST; chưa rõ → gửi lại ĐÚNG body + khóa gốc
    y = {k, hanh, actor: a, ky: body.ky_id, hd: ct.ky.hop_dong_id, body, khoa: taoKhoa(), kiem, ok, dangGui: false, chuaRo: false, het: false};
    yd.set(k, y);
    return y;
  }
  async function guiYD(y) {
    if (y.het || y.actor !== actor() || y.ky !== chon) return;  // ý định của vai/bản ký khác: không bao giờ gửi dưới ngữ cảnh hiện hành
    if (y.dangGui) { trangThai("Lệnh đang gửi — chờ kết quả, không gửi lần thứ hai."); return; }
    y.dangGui = true;
    const e0 = ep, a0 = actor(), gf0 = genForm, gv0 = genVao;
    const ht = () => e0 === ep && a0 === actor() && gf0 === genForm && gv0 === genVao && chon === y.ky && dangHopDong();
    const vf = () => !y.het && ht();
    trangThai(`Đang gửi: ${TEN[y.hanh]}…`);
    const chuaRoYD = msg0 => {
      y.chuaRo = true;
      if (vf()) { const msg = `${msg0} — kết quả "${TEN[y.hanh]}" chưa rõ; bấm Gửi lại y nguyên (cùng khóa).`; K.toast(msg, true); ve(); trangThai(msg, true); }
    };
    let r;
    try {
      r = await docJson(await goi("/api/crm/giao-ket/kiem/" + y.hanh, {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({...y.body, khoa: y.khoa})}));
    } catch (e) {
      y.dangGui = false;
      if (chuaRo(e) && !y.het) { chuaRoYD((e && e.message) || "Chưa rõ kết quả."); return; }
      const hl = vf();
      boYD(y);  // kết quả xác định — chỉ nhả ĐÚNG bản ghi y
      if (!hl) return;  // lỗi của ngữ cảnh cũ: không toast/vẽ/làm mới
      const msg = (e && e.message) || String(e);
      K.toast(msg, true); trangThai(msg, true);
      if (MA_CAN_CU.has(e && e.code) || loiAnNinh(e)) { await lamMoi(ht); if (ht()) trangThai(`${msg} — đã tải lại căn cứ hiện hành.`, true); }
      else ve();
      return;
    }
    y.dangGui = false;
    const ack = y.kiem(r, y);
    if (!ack) { if (!y.het) chuaRoYD("Phản hồi không đúng biên nhận mong đợi"); return; }  // 2xx lệch/thiếu: CHƯA RÕ, không FINAL
    const hl = vf();
    boYD(y);  // FINAL (ACK typed đã kiểm định danh)
    if (!hl) return;  // ACK muộn của ngữ cảnh cũ: im lặng; lần mở lại đọc trạng thái máy chủ
    const msg = y.ok(ack) + (ack.lap_lai ? " (biên nhận cũ của cùng yêu cầu — không ghi thêm)" : "");
    ve(); K.toast(msg); trangThai(msg);  // ý định đã FINAL: vẽ lại để gỡ nút gửi lại trước khi GET làm mới về
    await lamMoi(ht);
    if (ht()) trangThai(msg);
  }
  async function lamMoi(ht) {  // GET làm mới theo guard CHỤP lúc gửi (không chụp mới ở completion)
    if (!ht()) return;
    await napDs();
    if (ht() && chon) await napCt(chon);
  }
  // ACK typed: chỉ FINAL khi đúng DTO crm_kiem_kq của ĐÚNG bản ký/hợp đồng/revision/trạng thái mong đợi; thiếu/lệch → null (CHƯA RÕ)
  const soNguyen = v => Number.isInteger(v) && v >= 0;
  function ackGoc(r, y, tt, rev) {
    return !!r && typeof r === "object" && !Array.isArray(r) && r.ky_id === y.ky && r.hop_dong_id === y.hd && typeof r.ho_so_id === "string"
      && UUID.test(r.ho_so_id) && r.trang_thai === tt && soNguyen(r.revision) && r.revision === rev && typeof r.lap_lai === "boolean";
  }
  const ACK = {
    luu: (r, y) => ackGoc(r, y, "DANG_KIEM", y.body.expected_revision + 1) ? {lap_lai: r.lap_lai, revision: r.revision} : null,
    check: (r, y) => {
      const c = r && r.check;
      const dung = ackGoc(r, y, "DANG_KIEM", y.body.expected_revision) && !!c && typeof c === "object" && typeof c.check_id === "string" && UUID.test(c.check_id)
        && c.ho_so_revision === y.body.expected_revision && ["DU_DIEU_KIEN", "CHUA_DU_DIEU_KIEN"].includes(c.ket_luan) && typeof c.do_thi_sha256 === "string"
        && SHA.test(c.do_thi_sha256) && c.g5_che_do === "VAN_HANH" && Array.isArray(c.chan) && Array.isArray(c.canh_bao)
        && (c.ket_luan === "DU_DIEU_KIEN") === (c.chan.length === 0);
      return dung ? {lap_lai: r.lap_lai, ket_luan: c.ket_luan, so_chan: c.chan.length} : null;
    },
    "xu-ly-lech": (r, y) => ackGoc(r, y, "DANG_KIEM", y.body.expected_revision) && typeof r.xu_ly_id === "string" && UUID.test(r.xu_ly_id) ? {lap_lai: r.lap_lai} : null,
    "bo-sung": (r, y) => ackGoc(r, y, "CHO_BO_SUNG", y.body.expected_revision) ? {lap_lai: r.lap_lai} : null,
    "tra-lai": (r, y) => ackGoc(r, y, "TRA_LAI_CHO_KY_LAI", y.body.expected_revision) && r.ket_qua === "CHAN_PHU_THUOC"
      && r.phu_thuoc === "CRM_G6A_TRA_LAI_CHO_G4_KY_LAI" && r.g4_trang_thai === "DA_KY" ? {lap_lai: r.lap_lai} : null,
    "hieu-luc": (r, y) => {
      const h = r && r.hieu_luc;
      const dung = ackGoc(r, y, "HIEU_LUC", y.body.expected_revision) && !!h && typeof h === "object" && typeof h.phien_ban_id === "string" && UUID.test(h.phien_ban_id)
        && typeof h.chung_tu_id === "string" && UUID.test(h.chung_tu_id) && Number.isInteger(h.so_dong_lich) && h.so_dong_lich > 0
        && typeof h.tong_minor === "string" && /^[1-9]\d*$/.test(h.tong_minor) && typeof h.tien_te === "string" && /^[A-Z]{3}$/.test(h.tien_te)
        && h.g5_che_do === "VAN_HANH" && ["KHOP", "LECH", "KHONG_AP_DUNG"].includes(h.g7_trang_thai);
      return dung ? {lap_lai: r.lap_lai, so_dong_lich: h.so_dong_lich, tong_minor: h.tong_minor, tien_te: h.tien_te, g7: h.g7_trang_thai} : null;
    },
  };
  const OK = {
    luu: a => `Đã lưu kiểm (revision ${a.revision}).`,
    check: a => a.ket_luan === "DU_DIEU_KIEN" ? "Đã chạy check: đủ điều kiện kích hoạt." : `Đã chạy check: chưa đủ điều kiện (${a.so_chan} mục chặn).`,
    "xu-ly-lech": () => "Đã ghi quyết định xử lý lệch theo bản ký — chạy check lại.",
    "bo-sung": () => "Đã chuyển Chờ bổ sung.",
    "tra-lai": () => "Đã trả lại — chờ quy trình ký lại. Bản ký/PDF G4 giữ nguyên, KHÔNG về nháp (ký lại thuộc gói kế tiếp).",
    "hieu-luc": a => `Hợp đồng đã HIỆU LỰC — phiên bản v1 + ${a.so_dong_lich} đợt lịch thu (tổng ${tienTxt(a.tong_minor, a.tien_te)})`
      + (a.g7 === "LECH" ? " · đã tạo việc CFO xem xét lệch G7" : ""),
  };
  function lenh(hanh, body) { const y = yDinh(hanh, body, ACK[hanh], OK[hanh]); if (y) guiYD(y); }

  // ------------------------------------------------------------------ thân lệnh (chỉ trường cho phép; không actor/PN/chế độ G5/kết quả)
  function ungVien() {
    const uv = (ct && Array.isArray(ct.ma_junsky_ung_vien) ? ct.ma_junsky_ung_vien : []).filter(x => x && typeof x.id === "string");
    if (timKq && timKq.ky === chon && timKq.a === actor() && ct && ct.khach_du_thao === true)
      for (const x of timKq.ds) if (!uv.some(u => u.id === x.id)) uv.push(x);
    const rv = ct && ct.rev;
    if (rv && rv.de_xuat_ma_junsky_id && !uv.some(x => x.id === rv.de_xuat_ma_junsky_id))
      uv.push({id: rv.de_xuat_ma_junsky_id, doi_tac_id: rv.de_xuat_doi_tac_id, tien_to: "", object_id: rv.ma_junsky || "", ten: "(đã lưu — không còn trong danh sách hiện hành)"});
    return uv;
  }
  function bamLuu() {
    if (!ct || !formCua || formCua.ky !== chon) { trangThai("Mở bản ký trước.", true); return; }
    const cl = {};
    for (const [k] of CHECKLIST) { const v = gt("cl-" + k); cl[k] = v === "XAC_NHAN" || v === "CO_VAN_DE" ? v : null; }
    const mj = s0(gt("junsky")), uv = mj ? ungVien().find(x => x.id === mj) : null;
    if (mj && !uv) { trangThai("Mã Junsky đã chọn không còn trong danh sách — chọn lại.", true); return; }
    const ngay = s0(gt("ngay")), cc = s0(gt("can-cu")), td = s0(gt("trich"));
    if (new Set([ngay === null, cc === null, td === null]).size !== 1) { trangThai("Ngày hiệu lực cần đủ ngày + căn cứ + trích dẫn (hoặc để trống cả ba).", true); return; }
    lenh("luu", {ky_id: chon, expected_revision: formCua.rev, checklist: cl, doi_tac_id: uv ? uv.doi_tac_id : null, ma_junsky_id: uv ? uv.id : null,
      ngay_hieu_luc: ngay, can_cu_ngay: cc, trich_dan_ngay: td, ghi_chu: s0(gt("ghi-chu"))});
  }
  const revHt = () => (ct && ct.ho_so && Number.isInteger(ct.ho_so.revision) ? ct.ho_so.revision : null);
  function bamLyDo(hanh) {
    const ld = s0(gt("ly-do")), rev = revHt();
    if (rev === null) { trangThai("Chưa có hồ sơ kiểm — Lưu kiểm trước.", true); return; }
    if (!ld) { trangThai("Nhập lý do.", true); return; }
    lenh(hanh, {ky_id: chon, expected_revision: rev, ly_do: ld});
  }
  function bamXuLy(loai, mucTieu, ma) {
    const ld = s0(gt("ly-do")), rev = revHt();
    if (rev === null || !mucTieu) { trangThai("Chưa có hồ sơ kiểm/mục tiêu lệch.", true); return; }
    if (!ld) { trangThai("Nhập lý do xử lý lệch theo bản ký.", true); return; }
    lenh("xu-ly-lech", {ky_id: chon, expected_revision: rev, loai, muc_tieu_id: mucTieu, ma_lech: ma, ly_do: ld});
  }
  function bamCheck() { const rev = revHt(); if (rev === null) { trangThai("Chưa có hồ sơ kiểm — Lưu kiểm trước.", true); return; } lenh("check", {ky_id: chon, expected_revision: rev}); }
  function bamHieuLuc() {
    const rev = revHt(), c = ct && ct.check;
    if (rev === null || !c || c.ho_so_revision !== rev || c.ket_luan !== "DU_DIEU_KIEN") { trangThai("Cần lần check mới nhất của revision hiện hành đủ điều kiện.", true); return; }
    lenh("hieu-luc", {ky_id: chon, expected_revision: rev, check_id: c.check_id, do_thi_sha256: c.do_thi_sha256});
  }

  // ------------------------------------------------------------------ tra cứu mã Junsky có sẵn (khách dự thảo; chỉ đọc — lựa chọn lưu bằng Lưu kiểm)
  const KY_TU_DIEU_KHIEN = /[\u0000-\u001f\u007f]/;
  async function timJunsky() {
    const tu = String(timTu || "").trim(), ky = chon;
    if (!ct || !ct.ky || ct.ky.ky_id !== ky || ct.khach_du_thao !== true) { trangThai("Chỉ tra cứu cho bản ký khách dự thảo đang mở.", true); return; }
    if (tu.length < 3 || tu.length > 60 || KY_TU_DIEU_KHIEN.test(tu)) { trangThai("Nhập 3–60 ký tự (mã hoặc tên Junsky) để tra cứu.", true); return; }
    const e = ep, a = actor(), g = ++genTim, gv = genVao, gf = genForm;
    const f = () => e === ep && a === actor() && g === genTim && gv === genVao && chon === ky && dangHopDong();
    trangThai("Đang tra cứu mã Junsky…");
    try {
      const r = await docJson(await goi("/api/crm/giao-ket/kiem/tim-junsky", {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ky_id: ky, tu_khoa: tu})}));
      if (!f()) return;  // phản hồi của bản ký/vai/lần tra cứu cũ: bỏ
      if (!r || typeof r !== "object" || r.ky_id !== ky || !Array.isArray(r.ung_vien)) throw new LoiKiem(0, "KET_QUA_CHUA_RO", "Kết quả tra cứu không đúng bản ký đang mở.");
      const dsTim = r.ung_vien.filter(x => x && typeof x.id === "string" && UUID.test(x.id) && typeof x.doi_tac_id === "string" && UUID.test(x.doi_tac_id))
        .map(x => ({id: x.id, doi_tac_id: x.doi_tac_id, tien_to: String(x.tien_to || ""), object_id: String(x.object_id || ""), ten: String(x.ten || "")}));
      timKq = {ky, a, ds: dsTim};
      const msg = dsTim.length ? `Tìm thấy ${dsTim.length} mã Junsky có sẵn cùng pháp nhân — chọn trong danh sách rồi Lưu kiểm.`
        : "Không có mã Junsky hiện hành khớp trong pháp nhân này — tạo/ánh xạ ở quy trình danh mục đối tác (G6A không tạo mã).";
      if (gf === genForm) ve();  // đang gõ nội dung kiểm: giữ kết quả, không vẽ lại (caret/nháp); lần vẽ sau hiển thị
      trangThai(msg);
    } catch (err) {
      if (!f()) return;
      const msg = err && err.code === "CRM_KIEM_KHACH_DA_DINH" ? "Khách của bản ký/hợp đồng đã được định danh — không tra cứu/thay khách." : (err && err.message) || String(err);
      if (err && (err.code === "CRM_KIEM_KHACH_DA_DINH" || loiAnNinh(err))) { timKq = null; await napCt(ky); if (!f()) return; }
      trangThai(msg, true);
    }
  }

  // ------------------------------------------------------------------ G5-B: Bản ký & đối chiếu (một engine Source6 ở máy chủ; trình duyệt chỉ gửi
  // ky_id + expected_context_sha256 + khóa). VIEW/ACK kiểm ĐÚNG khóa/kiểu; lệch → CHƯA RÕ (giữ ý định), không suy "khớp". Kết quả hiện hành tách lịch sử.
  const G5_VIEW = ["kieu", "ky_id", "context_sha256", "bat_buoc", "khoi_tao", "quyen", "readiness", "current_job", "current_result", "history", "g6"];
  const G5_JOB = ["job_id", "loai", "trang_thai", "ly_do", "request_id", "the_he", "so_lan", "khoi_tao_loai", "cap_nhat_luc"];
  const G5_KQ = ["result_id", "trang_thai", "hien_hanh", "nhan_dang_ky", "tac_nhan_loai", "so_phu", "so_ma", "so_lech", "so_thieu", "tham_so", "tao_luc"];
  const G5_TS = ["ma", "crm_truong", "muc", "kieu", "gia_tri_ky_vong", "gia_tri_ban_ky", "trich_dan", "vi_tri_do_duoc", "trang_thai"];
  const G5_LS = ["result_id", "trang_thai", "tac_nhan_loai", "hien_hanh", "so_lech", "so_thieu", "tao_luc"];
  const G5_ACK = ["kieu", "ky_id", "context_sha256", "job_id", "request_id", "state", "current_result_id", "tao_moi", "replay"];
  const G5_MO = ["CHO", "DANG_CHAY", "CHUA_RO", "CHO_CAU_HINH"], G5_KQ_TT = ["KHOP", "LECH", "CHUA_DOI_CHIEU_DUOC"];
  const G5_TS_TT = ["LECH", "THIEU", "KHOP", "CHUA_PHU"], G5_TN = ["SYSTEM_JOB", "NGUOI_DUNG"];
  const RID_G5 = /^crm-g5-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-[1-9]\d*$/;
  const TEN_G5 = {chay: "Chạy đối chiếu", "doi-soat": "Đối soát"};
  const G5_NHAN = {BAT_BUOC: "bắt buộc", CHO_CAU_HINH: "chờ cấu hình", DANG_XU_LY: "đang xử lý", CHUA_RO: "chưa rõ", KHOP: "khớp", LECH: "lệch",
    CHUA_DOI_CHIEU_DUOC: "chưa đối chiếu được", CHUA: "chưa đối chiếu"};
  const G5_LY = {THIEU_DANG_KY: "Chưa có đăng ký engine/catalog cho loại hợp đồng/mẫu/danh mục của bản ký (chủ hệ thống đăng ký sau khi có bằng chứng producer).",
    DANG_KY_DEMO: "Đăng ký hiện hành là DEMO kiểm thử — kết quả không phải bằng chứng vận hành.",
    THIEU_NGUOI_CHAY: "Chưa cấu hình người chạy việc bắt buộc (phân công CRM_HD_KIEM hiện hành) — việc được giữ, chờ cấu hình.",
    E5_CHUA_GHEP: "Engine Source6 chưa có biến thể đối chiếu bản ký — việc được giữ, chờ cấu hình.", TRICH6_CHUA_SAN_SANG: "Engine Source6 chưa sẵn sàng.",
    E5_IMPLEMENTATION_KHAC: "Engine đang chạy khác implementation đã đăng ký — chưa công bố.", CRM_KIEM_CHUA_CO_PHAM_VI: "Người chạy chưa có phạm vi kiểm hiện hành.",
    CRM_G_KHONG_CO_QUYEN: "Người chạy không còn quyền kiểm hiện hành.", CRM_G_CUNG_NGUOI: "Người chạy là người ghi bản ký (tách nhiệm).",
    CRM_G5_DANG_KY_DOI: "Đăng ký engine/catalog đổi trước công bố — chạy lại theo đăng ký mới.", CRM_G5_NGUOI_CHAY_DOI: "Người chạy đổi/thu hồi trước công bố."};
  const laObj = x => !!x && typeof x === "object" && !Array.isArray(x);
  const dungKhoa = (x, ks) => laObj(x) && Object.keys(x).length === ks.length && ks.every(k => Object.prototype.hasOwnProperty.call(x, k));
  const uuidHoacNull = x => x === null || (typeof x === "string" && UUID.test(x));
  function g5Dung(v, id) {  // CRM_G5_VIEW_V1 đúng khóa/kiểu của ĐÚNG bản ký; sai → không dùng (không vẽ nút/kết quả từ dữ liệu lệch)
    if (!dungKhoa(v, G5_VIEW) || v.kieu !== "CRM_G5_VIEW_V1" || v.ky_id !== id || typeof v.context_sha256 !== "string" || !SHA.test(v.context_sha256)
      || typeof v.bat_buoc !== "boolean" || !dungKhoa(v.khoi_tao, ["trang_thai", "ly_do", "la_bang_chung"]) || v.khoi_tao.la_bang_chung !== false
      || !dungKhoa(v.quyen, ["chay", "doi_soat"]) || typeof v.quyen.chay !== "boolean" || typeof v.quyen.doi_soat !== "boolean"
      || !dungKhoa(v.readiness, ["san_sang", "ly_do"]) || typeof v.readiness.san_sang !== "boolean" || !Array.isArray(v.readiness.ly_do)
      || v.readiness.ly_do.some(x => typeof x !== "string") || v.readiness.san_sang !== (v.readiness.ly_do.length === 0) || !laObj(v.g6)
      || !Array.isArray(v.history)) return false;
    const j = v.current_job, x = v.current_result;
    if (j !== null && (!dungKhoa(j, G5_JOB) || !UUID.test(String(j.job_id)) || !["BAT_BUOC", "THU_CONG"].includes(j.loai) || !G5_MO.includes(j.trang_thai)
      || typeof j.request_id !== "string" || !RID_G5.test(j.request_id) || !j.request_id.startsWith(`crm-g5-${j.job_id}-`) || !Number.isInteger(j.so_lan))) return false;
    if (x !== null && (!dungKhoa(x, G5_KQ) || !UUID.test(String(x.result_id)) || !G5_KQ_TT.includes(x.trang_thai) || typeof x.hien_hanh !== "boolean"
      || !G5_TN.includes(x.tac_nhan_loai) || !["so_phu", "so_ma", "so_lech", "so_thieu"].every(k => Number.isInteger(x[k]) && x[k] >= 0)
      || !Array.isArray(x.tham_so) || x.tham_so.length !== x.so_ma
      || x.tham_so.some(t => !dungKhoa(t, G5_TS) || typeof t.ma !== "string" || !Number.isInteger(t.muc) || t.muc < 0 || t.muc > 3 || !G5_TS_TT.includes(t.trang_thai))
      || (x.trang_thai === "KHOP" && (x.so_lech !== 0 || x.so_thieu !== 0 || x.so_phu !== x.so_ma))
      || (x.trang_thai === "LECH" && (x.so_lech < 1 || x.so_phu !== x.so_ma)))) return false;
    return v.history.every(h => dungKhoa(h, G5_LS) && UUID.test(String(h.result_id)) && G5_KQ_TT.includes(h.trang_thai) && (x === null || h.result_id !== x.result_id));
  }
  function g5Ack(r, y) {  // CRM_G5_ACK_V1 của ĐÚNG bản ký + ngữ cảnh đã gửi; thiếu/lệch → null (CHƯA RÕ, giữ ý định)
    if (!dungKhoa(r, G5_ACK) || r.kieu !== "CRM_G5_ACK_V1" || r.ky_id !== y.ky || r.context_sha256 !== y.body.expected_context_sha256
      || typeof r.job_id !== "string" || !UUID.test(r.job_id) || typeof r.request_id !== "string" || !RID_G5.test(r.request_id)
      || !r.request_id.startsWith(`crm-g5-${r.job_id}-`) || !G5_MO.includes(r.state) || !uuidHoacNull(r.current_result_id)
      || typeof r.tao_moi !== "boolean" || typeof r.replay !== "boolean" || (y.hanh === "doi-soat" && r.tao_moi !== false)) return null;
    return {state: r.state, tao_moi: r.tao_moi, replay: r.replay};
  }
  async function napG5(id) {
    if (K.vaiDangChan("crm_kiem")) return false;
    const e = ep, a = actor(), g = ++genG5, gv = genVao, gf = genForm;
    const dung = () => e === ep && a === actor() && g === genG5 && gv === genVao && chon === id && dangHopDong();
    if (g5Hen) { clearTimeout(g5Hen); g5Hen = null; }
    try {
      const v = await docJson(await goi(`/api/crm/giao-ket/doi-chieu/${encodeURIComponent(id)}`));
      if (!dung()) return false;  // GET cũ (vai/bản ký/điều hướng/lần nạp khác): không ghi đè
      if (!g5Dung(v, id)) throw new LoiKiem(0, "KET_QUA_CHUA_RO", "Trạng thái đối chiếu không đúng cấu trúc CRM_G5_VIEW_V1 — không hiển thị kết quả.");
      g5v = v;
      if (v.current_job && (v.current_job.trang_thai === "CHO" || v.current_job.trang_thai === "DANG_CHAY"))
        g5Hen = setTimeout(() => { g5Hen = null; if (dung()) napG5(id); }, 5000);  // đang xử lý: làm mới định kỳ (trạng thái thật ở CSDL)
      if (gf === genForm) ve();
      return true;
    } catch (err) {
      if (!dung()) return false;
      g5v = {loi: (err && err.message) || String(err), ky_id: id, an_ninh: loiAnNinh(err) || (err && err.status === 404)};
      if (gf === genForm) ve();
      return false;
    }
  }
  function yDangG5(a, ky) { for (const y of ydG5.values()) if (!y.het && (y.dangGui || y.chuaRo) && y.actor === a && y.ky === ky) return y; return null; }
  function boG5(y) { y.het = true; y.chuaRo = false; if (ydG5.get(y.k) === y) ydG5.delete(y.k); }
  function lenhG5(hanh) {  // ĐỒNG BỘ: khóa tạo MỘT lần cho (vai, lệnh, bản ký, ngữ cảnh); quyền hiện hành của VIEW chặn trước POST
    const a = actor(), v = g5v;
    if (!a || !v || v.loi || v.ky_id !== chon) { trangThai("Tải trạng thái đối chiếu trước.", true); return; }
    if (!(hanh === "chay" ? v.quyen.chay : v.quyen.doi_soat)) { trangThai("Vai hiện hành không có quyền thao tác đối chiếu này.", true); return; }
    const body = {ky_id: chon, expected_context_sha256: v.context_sha256};
    const k = JSON.stringify([a, hanh, body]), cu = yDangG5(a, chon);
    if (cu && cu.k !== k) {
      trangThai(cu.dangGui ? `"${TEN_G5[cu.hanh]}" đang gửi — chờ kết quả.` : `"${TEN_G5[cu.hanh]}" trước chưa rõ kết quả — bấm Gửi lại y nguyên (cùng khóa) trước.`, true);
      return;
    }
    let y = ydG5.get(k);
    if (!y || y.het) { y = {k, hanh, actor: a, ky: chon, body, khoa: taoKhoa(), dangGui: false, chuaRo: false, het: false}; ydG5.set(k, y); }
    guiG5(y);
  }
  async function guiG5(y) {
    if (y.het || y.actor !== actor() || y.ky !== chon || K.vaiDangChan("crm_kiem")) return;  // không bao giờ gửi dưới vai/bản ký khác
    if (y.dangGui) { trangThai("Lệnh đối chiếu đang gửi — không gửi lần thứ hai."); return; }
    y.dangGui = true;
    const e0 = ep, a0 = actor(), gv0 = genVao;
    const ht = () => e0 === ep && a0 === actor() && gv0 === genVao && chon === y.ky && dangHopDong();
    const vf = () => !y.het && ht();
    const chuaRoG5 = msg0 => {
      y.chuaRo = true;
      if (vf()) { const msg = `${msg0} — "${TEN_G5[y.hanh]}" chưa rõ kết quả; bấm Gửi lại y nguyên (cùng khóa).`; K.toast(msg, true); ve(); trangThai(msg, true); }
    };
    trangThai(`Đang gửi: ${TEN_G5[y.hanh]}…`);
    let r;
    try {
      r = await docJson(await goi("/api/crm/giao-ket/doi-chieu/" + y.hanh, {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({...y.body, khoa: y.khoa})}));
    } catch (e) {
      y.dangGui = false;
      if (chuaRo(e) && !y.het) { chuaRoG5((e && e.message) || "Chưa rõ kết quả."); return; }
      const hl = vf();
      boG5(y);  // lỗi xác định (403/404/409/400/503-chưa-sẵn-sàng) — nhả ĐÚNG ý định này
      if (!hl) return;
      const msg = (e && e.message) || String(e);
      K.toast(msg, true); trangThai(msg, true);
      await napG5(y.ky);  // ngữ cảnh/quyền có thể đã đổi: đọc lại trạng thái hiện hành (fence riêng)
      return;
    }
    y.dangGui = false;
    const ack = g5Ack(r, y);
    if (!ack) { if (!y.het) chuaRoG5("Phản hồi không đúng biên nhận CRM_G5_ACK_V1"); return; }
    const hl = vf();
    boG5(y);
    if (!hl) return;  // ACK muộn của ngữ cảnh cũ: im lặng
    const msg = `${TEN_G5[y.hanh]}: đã ghi việc (${ack.state === "CHO_CAU_HINH" ? G5_NHAN.CHO_CAU_HINH : ack.state === "CHUA_RO" ? G5_NHAN.CHUA_RO : G5_NHAN.DANG_XU_LY})`
      + (ack.replay ? " (biên nhận cũ của cùng yêu cầu — không ghi thêm)" : "") + " — kết quả do máy chủ công bố sau khi engine đối chiếu xong.";
    ve(); K.toast(msg); trangThai(msg);
    await napG5(y.ky);
  }
  function g5Gt(v) {  // hiển thị giá trị typed: ∅ ≠ 0, tiền tệ tường minh, bảng giữ thứ tự dòng/ô
    if (v === null || v === undefined) return "∅ (trống)";
    if (typeof v === "string") return v;
    if (laObj(v) && Object.prototype.hasOwnProperty.call(v, "so_tien")) return `${v.so_tien ?? "∅"} ${v.tien_te ?? "(không có tiền tệ)"}`;
    if (laObj(v) && Array.isArray(v.dong)) return `bảng ${v.dong.length} dòng: ` + v.dong.map((d, i) => `#${i + 1} [${(Array.isArray(d) ? d : []).map(c => c === null ? "∅" : String(c)).join(" | ")}]`).join("; ");
    return JSON.stringify(v);
  }
  const g5ViTri = v => v === null || v === undefined ? "" : typeof v === "string" ? v : JSON.stringify(v);
  const G5_TS_NHAN = {LECH: "lệch", THIEU: "thiếu (chưa đọc được)", KHOP: "khớp", CHUA_PHU: "chưa phủ"};
  const tnTxt = t => t === "SYSTEM_JOB" ? "việc hệ thống (bắt buộc)" : "thủ công";
  function veG5() {
    const w = node("section", undefined, "gk-doi-chieu"); w.setAttribute("aria-label", "Bản ký & đối chiếu");
    w.append(node("h5", "Bản ký & đối chiếu"));
    const v = g5v;
    if (!v) { w.append(node("p", "Đang tải trạng thái đối chiếu…")); return [w]; }
    if (v.loi) { w.append(node("p", "Không tải được trạng thái đối chiếu: " + v.loi, "upload-status error")); return [w]; }
    const j = v.current_job, x = v.current_result, nhan = [];
    if (v.bat_buoc) nhan.push(G5_NHAN.BAT_BUOC);
    if (j) nhan.push(j.trang_thai === "CHO_CAU_HINH" ? G5_NHAN.CHO_CAU_HINH : j.trang_thai === "CHUA_RO" ? G5_NHAN.CHUA_RO : G5_NHAN.DANG_XU_LY);
    nhan.push(x ? G5_NHAN[x.trang_thai] : G5_NHAN.CHUA);
    const p = node("p", "Trạng thái: " + nhan.join(" · ")); p.dataset.g5Nhan = nhan.join("|"); w.append(p);
    if (v.bat_buoc) w.append(node("p", "Bản ký khai CÓ sửa so với bản xuất: đối chiếu là bắt buộc (việc hệ thống tự xếp hàng lúc ký; không duyệt/kích hoạt thay kế toán).", "gk-ly-do"));
    for (const ly of v.readiness.ly_do) w.append(node("p", G5_LY[ly] || ly, "gk-ly-do"));
    if (j && j.ly_do && (j.trang_thai === "CHO_CAU_HINH" || j.trang_thai === "CHUA_RO"))
      w.append(node("p", `Việc ${j.loai === "BAT_BUOC" ? "bắt buộc" : "thủ công"}: ${G5_LY[j.ly_do] || j.ly_do}`, "gk-ly-do"));
    if (x) {
      w.append(node("p", `Kết quả hiện hành: ${G5_NHAN[x.trang_thai]} · phủ ${x.so_phu}/${x.so_ma} mã · ${x.so_lech} lệch · ${x.so_thieu} thiếu · ${tnTxt(x.tac_nhan_loai)} · ${K.date(x.tao_luc)}`
        + (x.hien_hanh ? "" : " — CŨ: đăng ký engine/catalog đã đổi") + (x.nhan_dang_ky === "DEMO_KIEM_THU" ? " — DEMO kiểm thử, không phải bằng chứng vận hành" : "")));
      w.append(bang(["Tham số", "Bản sinh", "Bản ký", "Trích dẫn/locator", "Mức"], x.tham_so.map(t => [
        `${t.ma} (${t.crm_truong}) · ${G5_TS_NHAN[t.trang_thai]}`, g5Gt(t.gia_tri_ky_vong), t.trang_thai === "LECH" ? g5Gt(t.gia_tri_ban_ky) : "—",
        [t.trich_dan || "", g5ViTri(t.vi_tri_do_duoc)].filter(Boolean).join(" · ") || "—", String(t.muc)])));
    }
    const hd = node("div", undefined, "demo-actions");
    hd.append(nut("Chạy đối chiếu", () => lenhG5("chay"), "button secondary", !v.quyen.chay), nut("Đối soát", () => lenhG5("doi-soat"), "button secondary", !v.quyen.doi_soat));
    if (!v.quyen.chay) hd.append(node("span", "Vai hiện hành không chạy được đối chiếu cho bản ký này (cần phân công + phạm vi kiểm hiện hành; người ghi bản ký không tự kiểm).", "gk-ly-do"));
    w.append(hd);
    const y = yDangG5(actor(), chon);
    if (y && y.chuaRo && !y.dangGui) {
      const u = node("div", undefined, "demo-actions"); u.dataset.g5ChuaRo = "1";
      u.append(node("span", `"${TEN_G5[y.hanh]}" trước chưa rõ kết quả. `), nut("Gửi lại y nguyên (cùng khóa)", () => guiG5(y), "button primary"));
      w.append(u);
    }
    if (v.history.length) w.append(node("h6", "Lịch sử đối chiếu (không phải kết quả hiện hành)"), bang(["Lúc", "Kết quả", "Tác nhân", "Theo đăng ký hiện hành?", "Lệch/thiếu"],
      v.history.map(h => [K.date(h.tao_luc), G5_NHAN[h.trang_thai], tnTxt(h.tac_nhan_loai), h.hien_hanh ? "có" : "không", `${h.so_lech}/${h.so_thieu}`])));
    return [w];
  }

  // ------------------------------------------------------------------ tải tệp (fence trước request, sau headers/blob, ngay trước click)
  async function taiTep(kyId, loai) {
    const e = ep, a = actor(), g = genCt, gf = genForm, gv = genVao;
    const f = () => e === ep && a === actor() && chon === kyId && g === genCt && gf === genForm && gv === genVao && dangHopDong();
    if (!f()) return;
    try {
      const res = await goi(`/api/crm/giao-ket/kiem/${encodeURIComponent(kyId)}/tep/${loai}`);
      if (!f()) return;
      const blob = await res.blob();
      if (!f()) return;
      if (!blob.size) { trangThai("Tệp tải về rỗng — không lưu.", true); return; }
      if (!f()) return;
      const url = URL.createObjectURL(blob), el = node("a"); el.href = url; el.download = `${loai}-${kyId}.pdf`; document.body.append(el); el.click(); el.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      trangThai(`Đã tải PDF ${loai === "g3" ? "bản xuất G3" : "bản ký"} (${blob.size} byte).`);
    } catch (err) { if (f()) { K.toast(err.message, true); trangThai(err.message, true); } }
  }

  // ------------------------------------------------------------------ vẽ
  function dungKhung() {
    const head = node("div", undefined, "section-heading"), td = node("div"), h2 = node("h2", "7 · Kế toán kiểm hợp đồng đã ký → Hiệu lực"); h2.id = "crm-kiem-title";
    oVai = node("p", "Đang tải…");
    td.append(h2, node("p", "G6A: kế toán kiểm bản ký (checklist, khách theo mã Junsky có sẵn, ngày hiệu lực có căn cứ, lịch/G7/G5) rồi kích hoạt HIỆU LỰC nguyên tử theo đúng lần check đã xem. Không sửa bản ký/PDF G4; trả lại = chờ ký lại, không về nháp."), oVai);
    head.append(td, nut("↻ Làm mới", () => napLai(), "button secondary"));
    oTrangThai = node("p", "", "upload-status"); oTrangThai.setAttribute("role", "status"); oTrangThai.setAttribute("aria-live", "polite");
    oNoiDung = node("div");
    goc.replaceChildren(head, oTrangThai, oNoiDung);
  }
  function ve() {
    if (!oNoiDung) dungKhung();
    dsCanLuu = [];
    oVai.textContent = actor() ? `Vai hiện hành: ${actor()}` : "Đang tải…";
    const out = [];
    if (!ds) out.push(K.empty("Chưa tải danh sách kiểm", "Bấm ↻ Làm mới; cần vai Kế toán có phân công kiểm hợp đồng."));
    else {
      out.push(node("h3", "Hợp đồng đã ký trong phạm vi kiểm"));
      out.push(ds.ds.length ? bang(["Hợp đồng", "Ngày ký", "Trạng thái", "Revision kiểm", ""], ds.ds.map(x => [x.ma_noi_bo, x.ngay_ky, x.hien_thi || x.trang_thai,
        String(x.revision ?? 0), nut(chon === x.ky_id ? "Đang mở" : "Mở", () => { boChon(); chon = x.ky_id; ve(); napCt(x.ky_id); }, "link-button", chon === x.ky_id)]))
        : K.empty("Chưa có hợp đồng đã ký trong phạm vi vai này", ""));
      if (chon) out.push(...veCt());
    }
    oNoiDung.replaceChildren(...out);
  }
  function veChuaRo() {
    const y = yDang(actor(), chon);
    if (!y || !y.chuaRo || y.dangGui) return [];
    const w = node("div", undefined, "demo-actions"); w.dataset.kiemChuaRo = "1";
    w.append(node("span", `Lệnh "${TEN[y.hanh]}" trước chưa rõ kết quả. `), nut("Gửi lại y nguyên (cùng khóa)", () => guiYD(y), "button primary"));
    return [w];
  }
  function veCt() {
    if (!ct) return [node("p", "Đang tải bản ký…")];
    if (ct.loi) return [node("p", "Không tải được bản ký: " + ct.loi, "upload-status error")];
    const k = ct.ky, ho = ct.ho_so, tt = ho ? ho.trang_thai : "CHUA_KIEM", out = [];
    const w = node("div", undefined, "gk-kiem-hd"); w.setAttribute("aria-label", "Kế toán kiểm hợp đồng đã ký");
    w.append(node("h4", `Bản ký ${k.ma_noi_bo} · ${ho ? ho.hien_thi : "Đã ký — chờ kế toán kiểm"}`),
      bang(["Mục", "Giá trị"], [
        ["Mẫu", `${k.ma_mau || "—"} v${k.phien_ban_mau ?? "—"}`], ["Revision bản soạn đã ký", String(k.revision)],
        ["Ngày ký", `${k.ngay_ky} (không phải ngày hiệu lực)`], ["Người ký phía khách (đã che)", k.nguoi_ky_khach || "—"],
        ["Bản ký có sửa so với bản xuất?", k.co_sua ? `Có — ${k.mo_ta_sua || ""}` : "Không"],
        ["SHA-256 PDF bản ký", `${k.ky_pdf_sha256} (${k.ky_pdf_len} byte, ${k.ky_so_trang} trang)`], ["SHA-256 PDF bản xuất G3", `${k.g3_pdf_sha256} (${k.g3_pdf_len} byte)`],
        ["Tóm tắt báo giá đã ký", ct.tom_tat ? `${ct.tom_tat.so_dong} dòng · tổng ${tienTxt(ct.tom_tat.tong_minor, ct.tom_tat.tien_te)}` : "chưa tính được"],
        ["G5 khởi tạo (G4)", g4G5Txt(k.g5_khoi_tao)]]));
    const tai = node("div", undefined, "demo-actions");
    tai.append(nut("PDF bản ký ↓", () => taiTep(k.ky_id, "ban-ky"), "link-button"), nut("PDF bản xuất G3 ↓", () => taiTep(k.ky_id, "g3"), "link-button"));
    w.append(tai);
    if (tt === "HIEU_LUC" && ho.hieu_luc) {
      const h = ho.hieu_luc;
      w.append(node("p", `Đã HIỆU LỰC: phiên bản ${h.phien_ban_id} · ${h.so_dong_lich} đợt lịch thu · ${h.so_tham_so} tham số · tổng ${tienTxt(h.tong_minor, h.tien_te)} · G7 ${h.g7_trang_thai}`
        + (h.viec_cfo_id ? " · việc CFO xem xét lệch G7 đang chờ" : "")));
    }
    if (tt === "TRA_LAI_CHO_KY_LAI") w.append(node("p", "Đã trả lại — chờ quy trình ký lại (chưa mở lại G4). Bản ký/PDF G4 giữ nguyên; KHÔNG về nháp; không kích hoạt được.", "upload-status error"));
    const q = ct.quyen || {}, moForm = q.kiem === true && (tt === "CHUA_KIEM" || tt === "DANG_KIEM" || tt === "CHO_BO_SUNG");
    if (q.kiem !== true) w.append(node("p", LY_QUYEN[q.ly_do] || "Vai hiện hành không kiểm được bản ký này.", "gk-ly-do"));
    // khách + Junsky
    const kb = ct.khach_ban_ky || {};
    w.append(node("h5", "Khách"), node("p", kb.doi_tac_id ? `Khách trên bản ký: đối tác ${kb.doi_tac_id}` : `Khách dự thảo trên bản ký (đã che): ${kb.du_thao_ten || "—"} · ${kb.du_thao_lien_he || "—"}`));
    // ngày hiệu lực + checklist (form)
    if (moForm) {
      const uv = ungVien();
      w.append(truong("Mã Junsky CÓ SẴN của khách (không tạo mã ở đây)", chon_("junsky", uv.map(x => [x.id, `${x.tien_to || ""} ${x.object_id || ""} · ${x.ten || ""}`.trim()]), "— chọn mã Junsky —")));
      if (ct.khach_du_thao === true) {  // P1-B: khách dự thảo (bản ký + hợp đồng chưa có đối tác) — tra cứu mã CÓ SẴN cùng pháp nhân
        const ti = node("input"); ti.type = "search"; ti.id = "kiem-tim-junsky"; ti.autocomplete = "off"; ti.maxLength = 60; ti.value = timTu;
        ti.addEventListener("input", () => { timTu = ti.value; });  // không phải nội dung kiểm: không đổi genForm/không khóa nút
        const tw = node("div", undefined, "demo-actions"), tl = node("label", "Tra cứu mã/tên Junsky có sẵn (3–60 ký tự)"); tl.htmlFor = ti.id;
        tw.append(tl, ti, nut("Tìm mã Junsky có sẵn", () => timJunsky(), "button secondary"));
        w.append(tw, node("p", "Khách trên bản ký là dự thảo: chọn đúng mã Junsky ĐÃ CÓ của pháp nhân rồi Lưu kiểm — cặp đối tác/mã được lưu vào revision kiểm (có nhật ký); "
          + "không tạo mã, không sửa bản ký G4.", "gk-ly-do"));
      }
      if (!uv.length) w.append(node("p", ct.khach_du_thao === true ? "Chưa chọn mã — tra cứu ở trên; nếu không có mã hiện hành, tạo/ánh xạ ở quy trình danh mục đối tác."
        : "Chưa có mã Junsky hiện hành cho khách này — tạo/ánh xạ ở quy trình danh mục đối tác; G6A không tạo mã, không đổi khách đã ký.", "gk-ly-do"));
      w.append(node("h5", "Checklist kiểm (chưa chọn = chưa xác nhận, không mặc định đạt)"));
      for (const [kk, nhan] of CHECKLIST) w.append(truong(nhan, chon_("cl-" + kk, [["XAC_NHAN", "Xác nhận"], ["CO_VAN_DE", "Có vấn đề"]], "— chưa xác nhận —")));
      const trich = o("trich", node("textarea"));
      w.append(node("h5", "Ngày hiệu lực (kế toán xác định, có căn cứ)"), truong("Ngày hiệu lực", nhap("ngay", "date")),
        truong("Căn cứ", chon_("can-cu", CAN_CU, "— chọn căn cứ —")), truong("Trích dẫn căn cứ", trich), truong("Ghi chú", o("ghi-chu", node("textarea"))));
      const hd = node("div", undefined, "demo-actions");
      hd.append(nut("Lưu kiểm", () => bamLuu(), "button primary"));
      w.append(hd);
    } else if (ct.rev) {
      const rv = ct.rev;
      w.append(bang(["Kiểm đã lưu", "Giá trị"], [...CHECKLIST.map(([kk, nhan]) => [nhan, (rv.checklist && rv.checklist[kk]) || "chưa xác nhận"]),
        ["Mã Junsky (đã che)", rv.ma_junsky || "—"], ["Ngày hiệu lực", rv.ngay_hieu_luc ? `${rv.ngay_hieu_luc} · ${rv.can_cu_ngay}` : "—"]]));
    }
    // tham số, lịch, G7, G5
    const truongs = Array.isArray(ct.truong) ? ct.truong : [];
    if (truongs.length) w.append(node("h5", "Tham số từ bản ký (PII đã che)"), bang(["Trường", "Giá trị", "Căn cứ"], truongs.map(t => [t.nhan || t.ten, t.gia_tri ?? "—", t.trang_thai_can_cu])));
    const l = ct.lich || {};
    w.append(node("h5", `Lịch thu theo bản ký · tổng ${tienTxt(l.tong_minor, l.tien_te)}`),
      bang(["Đợt", "Lần", "Tỷ lệ", "Số tiền (đơn vị nhỏ nhất)", "Mốc", "Hạn"], (Array.isArray(l.dong) ? l.dong : []).map(d => [String(d.dot), d.lan, d.ty_le ?? "—",
        d.so_tien_minor ?? "chưa tính được", d.moc || "—", d.han || "—"])));
    if (maTxt(l.loi).length) w.append(node("p", "Lỗi lịch: " + maTxt(l.loi).join(", "), "upload-status error"));
    const daXl = new Set((Array.isArray(ct.xu_ly_lech) ? ct.xu_ly_lech : []).map(x => `${x.loai}|${x.muc_tieu_id}|${x.ma_lech}`));
    const veLech = (loai, mucTieu, lech) => {
      const ul = node("ul");
      for (const e of Array.isArray(lech) ? lech : []) {
        const li = node("li", `${e.ma}${e.dong ? ` · dòng ${e.dong}` : ""}`);
        if (daXl.has(`${loai}|${mucTieu}|${e.khoa}`)) li.append(" — đã xử lý theo bản ký");
        else if (moForm && tt === "DANG_KIEM") li.append(" ", nut("Xử lý theo bản ký", () => bamXuLy(loai, mucTieu, e.khoa), "link-button"));
        ul.append(li);
      }
      return ul;
    };
    const g7 = ct.g7 || {};
    w.append(node("h5", `G7 bộ chuẩn theo ngày ký: ${g7.trang_thai || "—"}${g7.bo_chuan_phien_ban ? ` (phiên bản ${g7.bo_chuan_phien_ban})` : ""}`));
    if (g7.trang_thai === "LECH") w.append(veLech("G7_LECH", g7.bo_chuan_pb_id, g7.lech));
    const g5 = ct.g5 || null, g5p = node("p", "G5 đối chiếu: " + g5Txt(g5)); g5p.dataset.g5 = g5 ? String(g5.trang_thai) : "";
    w.append(node("h5", "G5"), g5p);
    if (g5 && g5.trang_thai === "LECH") w.append(veLech("G5_LECH", g5.ket_qua_id, g5.lech));
    w.append(...veG5());
    // check mới nhất + lệnh
    const c = ct.check, rev = revHt();
    if (c) {
      const cu = c.ho_so_revision !== rev;
      w.append(node("h5", `Check mới nhất (${K.date(c.tao_luc)})${cu ? " — CŨ: revision đã đổi, chạy check lại" : ""}`),
        node("p", `${c.ket_luan === "DU_DIEU_KIEN" ? "Đủ điều kiện kích hoạt" : "Chưa đủ điều kiện"} · revision ${c.ho_so_revision} · đồ thị ${c.do_thi_sha256}`));
      if (maTxt(c.chan).length) w.append(node("p", "Chặn: " + maTxt(c.chan).join(", "), "upload-status error"));
      if (maTxt(c.canh_bao).length) w.append(node("p", "Cảnh báo: " + maTxt(c.canh_bao).join(", ")));
    }
    if (moForm) {
      const dk = tt === "DANG_KIEM";
      const lyHl = !dk ? "Chỉ kích hoạt hồ sơ đang kiểm." : !c || c.ho_so_revision !== rev ? "Chạy check trên revision hiện hành trước."
        : c.ket_luan !== "DU_DIEU_KIEN" ? "Lần check mới nhất còn mục chặn." : "";
      const hd = node("div", undefined, "demo-actions");
      hd.append(nutCanLuu("Chạy check", () => bamCheck(), "button secondary", dk ? "" : "Lưu kiểm trước (hồ sơ phải đang kiểm)."),
        nutCanLuu("Kích hoạt hiệu lực", () => bamHieuLuc(), "button primary", lyHl));
      if (lyHl) hd.append(node("span", lyHl, "gk-ly-do"));
      w.append(hd, truong("Lý do (bổ sung / trả lại / xử lý lệch)", o("ly-do", node("textarea"))));
      const hd2 = node("div", undefined, "demo-actions");
      hd2.append(nut("Yêu cầu bổ sung", () => bamLyDo("bo-sung"), "button secondary", !dk), nut("Trả lại (chờ ký lại)", () => bamLyDo("tra-lai"), "button secondary", !ho));
      w.append(hd2, node("p", "Trả lại không mở khóa/sửa bản ký G4 và không đưa hợp đồng về nháp — chỉ chặn phụ thuộc tới khi có quy trình ký lại."));
    }
    w.append(...veChuaRo());
    if (Array.isArray(ct.lich_su) && ct.lich_su.length) w.append(node("h5", "Lịch sử"), bang(["Lúc", "Người", "Hành động"], ct.lich_su.map(x => [K.date(x.luc), x.nguoi, HD_LS[x.hanh_dong] || x.hanh_dong])));
    out.push(w);
    return out;
  }

  dungKhung(); ve();
  if (dangHopDong()) napDs();
  // mọi đổi hash (rời hoặc quay lại #hopdong) đổi thế hệ hiển thị TRƯỚC khi nạp lại — callback/blob cũ không hồi hiệu lực
  window.addEventListener("hashchange", () => { genVao += 1; if (dangHopDong()) napLai(); });
})();
