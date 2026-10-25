"use strict";
// CRM-41-02 — S6 trong shell CRM hiện có (#page-hopdong → #crm-g): G1 mẫu DOCX (tải lên → phát hiện ô → ánh xạ/phiên bản → xem thử dữ liệu giả →
// KT kiểm/Trả lại → CFO duyệt/Từ chối → so sánh → tải tệp gốc) và G7 bộ chuẩn dự án 4 cột (đọc bản cũ; sửa áp dụng ngay trong Dự án đang bán).
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
  async function napLai() { if (tab === "du-an-ban") return duAnBan.nap(); await napDs(); if (pbChon) await napCt(); if (tab === "chuan") await napBc(); }

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
  function doiTab(t) { if (tab === t) return; duAnBan.roi(); tab = t; genForm += 1; genDoc += 1; doiFormTai(); trangThai(""); ve(); if (t === "chuan") napBc(); if (t === "du-an-ban") duAnBan.nap(); }

  // ------------------------------------------------------------------ DA-2a/DA-2b1/DA-2b2 · thông tin, phí, lô/căn và tiến độ dự án đang bán
  // Dùng chung node/bang/nut/goi và epoch đổi vai của G1/G7. Mỗi GET có thế hệ riêng;
  // rời tab/đổi dự án/phiên bản/vai vô hiệu phản hồi cũ trước mọi ghi DOM/cache/lỗi.
  const duAnBan = (() => {
    let danhSach = null, chiTiet = null, lichSu = null, id = null, pb = "", chiDangBan = false, xemLichSu = false;
    let genDs = 0, genCt = 0, genLs = 0, loiDs = "", loiCt = "", loiLs = "";
    let mocChuan = null;
    let form = null, genLenh = 0;
    // Cùng quy tắc chuỗi của docSo/hienSo BG-1b (helper nằm trong closure riêng của Báo giá).
    const docSo = t => { const s = String(t ?? "").trim(); return /^(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)(?:,[0-9]{1,12})?$/.test(s) ? s.replace(/\./g, "").replace(",", ".") : null; };
    const hienSo = dec => {
      const m = /^(\d+)(?:\.(\d+))?$/.exec(String(dec ?? ""));
      if (!m) return String(dec ?? "");
      const le = (m[2] || "").replace(/0+$/, ""), ng = m[1].replace(/^0+(?=\d)/, "");
      return ng.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + (le ? "," + le : "");
    };
    const themDuoc = () => danhSach && danhSach.duoc_sua !== false && (danhSach.du_an_chua_ban || []).length > 0;
    const hienHanh = () => chiTiet && chiTiet.anh_chup?.phien_ban?.so === (chiTiet.phien_ban_ds || []).find(v => !v.hieu_luc_den)?.phien_ban;
    function boForm() { form = null; genLenh += 1; }
    async function moForm(hanh) {
      if (form?.ban) return;
      if (hanh === "bat-ban" ? !themDuoc() : !chiTiet?.duoc_sua) return;
      const g = genLenh, e = ep, da = id;
      const dung = () => g === genLenh && e === ep && da === id && tab === "du-an-ban";
      // GET lọc chỉ đang bán không kèm loại hình: nạp lại danh sách đầy đủ trước khi mở editor.
      if (chiDangBan || (hanh !== "bat-ban" && !hienHanh())) {
        chiDangBan = false; pb = "";
        if (!await napDs() || !dung()) return;
        if (id) await napCt();
        if (!dung()) return;
        if (hanh === "bat-ban" ? !themDuoc() : !chiTiet?.duoc_sua) return;
      }
      const s = chiTiet?.anh_chup || {}, tt = s.thong_tin || {}, moi = hanh === "bat-ban";
      form = {hanh, da: moi ? null : id, expected: moi ? null : s.phien_ban?.so, ban: false, loi: {}, msg: "", cu: false,
        v: {du_an_id: "", vi_tri: moi ? "" : tt.vi_tri || "", mo_ta: moi ? "" : tt.mo_ta || "",
          don_gia_niem_yet: moi ? "" : hienSo(s.don_gia), tien_te: moi ? "VND" : s.tien_te,
          loai_hinh_id: moi ? "" : s.loai_hinh?.id || "", thue_suat: moi ? "10" : s.thue?.thue_suat || "10",
          gia_dat_tru: moi ? "0" : hienSo(s.gia_dat_tru ?? "0"), giai_doan_g7: moi ? "" : s.giai_doan_g7 || "", ly_do: ""}};
      if (hanh === "phi") form.rows = (s.phi || []).map(r => ({ten: r.ten, loai: r.loai, muc: hienSo(r.muc), don_vi_tinh: r.don_vi_tinh, tien_te: r.tien_te, co_so_tinh: r.co_so_tinh || ""}));
      if (hanh === "lo") form.rows = (s.lo || []).map(r => ({ma: r.ma, dien_tich: hienSo(r.dien_tich), trang_thai: r.trang_thai, ghi_chu: r.ghi_chu || "", expected_lan: r.lan}));
      if (hanh === "tien-do") {
        form.duAn = chiTiet.du_an_id;
        form.expected = s.bo_chuan?.trang_thai === "HIEU_LUC" ? s.bo_chuan.version.phien_ban : 0;
        form.giaiDoan = s.bo_chuan?.giai_doan || s.giai_doan_g7 || null;
        form.rows = (s.bo_chuan?.rows || []).map(r => ({lan: r.lan, gl: r.gia_tri_loai || "", tp: hienSo(r.gia_tri_thap_phan ?? ""),
          st: r.so_tien_minor == null ? "" : hienSo(r.tien_te === "USD" ? String(r.so_tien_minor).padStart(3, "0").replace(/(..)$/, ".$1") : r.so_tien_minor),
          tt: r.tien_te || s.tien_te || "VND", ml: r.moc_loai || "", mn: r.moc_ngay || "", ms: r.moc_su_kien || "", gc: r.ghi_chu || ""}));
        if (!form.rows.length) form.rows.push(dongMoi(form));
      }
      genLenh += 1; ve();
    }
    function dongMoi(f) {
      if (f.hanh === "phi") return {ten: "", loai: "BAO_TRI", muc: "", don_vi_tinh: "M2_THANG", tien_te: chiTiet?.anh_chup?.tien_te || "VND", co_so_tinh: ""};
      if (f.hanh === "lo") return {ma: "", dien_tich: "", trang_thai: "CON_TRONG", ghi_chu: ""};
      let lan = 1;
      while (f.rows.some(r => r.lan === String(lan))) lan += 1;
      return {lan: String(lan), gl: "PERCENT", tp: "", st: "", tt: chiTiet?.anh_chup?.tien_te || "VND", ml: "SU_KIEN", mn: "", ms: "", gc: ""};
    }
    async function taiBanMoi(f) {
      const g = genLenh, e = ep;
      pb = "";
      if (!await napDs() || e !== ep || g !== genLenh || form !== f) return;
      if (id) await napCt();
      if (e !== ep || g !== genLenh || form !== f) return;
      // Nháp và expected cũ được giữ: người dùng phải xem bản mới rồi mở lại form để sửa.
      f.msg = "Đã tải bản mới. Nội dung đang gõ được giữ; xem bản mới rồi Hủy và mở lại màn sửa để tiếp tục."; ve();
    }
    async function guiForm(bodyDaGui) {
      const f = form;
      if (!f || f.ban || (f.cu && !bodyDaGui) || K.vaiDangChan("crm_g")) return;
      let body = bodyDaGui;
      if (!body) {
        f.loi = {}; f.msg = "";
        const canLyDo = !["lo", "tien-do"].includes(f.hanh);
        if (canLyDo && !f.v.ly_do.trim()) f.loi.ly_do = "Cần nhập lý do.";
        body = canLyDo ? {ly_do: f.v.ly_do.trim()} : {};
        if (f.hanh === "bat-ban") { body.du_an_id = f.v.du_an_id; body.phi = []; if (!body.du_an_id) f.loi.du_an_id = "Cần chọn dự án."; }
        else if (f.hanh !== "tien-do") { body.da_ban_id = f.da; if (f.hanh !== "lo") body.expected_phien_ban = f.expected; }
        if (["bat-ban", "cap-nhat"].includes(f.hanh)) {
          const tt = {}; for (const k of ["vi_tri", "mo_ta", "tien_te", "loai_hinh_id", "thue_suat", "giai_doan_g7"]) tt[k] = f.v[k].trim();
          for (const k of ["don_gia_niem_yet", "gia_dat_tru"]) {
            tt[k] = docSo(f.v[k]);
            if (tt[k] === null && (k === "gia_dat_tru" || f.v[k].trim())) f.loi[k] = "Nhập số kiểu Việt, ví dụ 1.234,5.";
          }
          if (!tt.loai_hinh_id) f.loi.loai_hinh_id = "Cần chọn loại hình.";
          body.thong_tin = tt;
        }
        const soNhap = (v, k) => { const s = docSo(v); if (s === null) f.loi[k] = "Nhập số kiểu Việt, ví dụ 1.234,5."; return s; };
        if (f.hanh === "phi") body.phi = f.rows.map((r, i) => ({...r, ten: r.ten.trim(), co_so_tinh: r.co_so_tinh.trim(), muc: soNhap(r.muc, `phi.${i}.muc`)}));
        if (f.hanh === "lo") {
          if (!f.rows.length) f.loi.lo = "Cần ít nhất một lô/căn.";
          body.lo = f.rows.map((r, i) => ({...r, ma: r.ma.trim(), dien_tich: soNhap(r.dien_tich, `lo.${i}.dien_tich`), ghi_chu: r.ghi_chu.trim()}));
        }
        if (f.hanh === "tien-do") {
          body = {du_an_id: f.duAn, giai_doan: f.giaiDoan, expected_version: f.expected, dong: f.rows.map((r, i) => {
            let minor = null;
            if (r.gl === "AMOUNT") {
              const s = soNhap(r.st, `dong.${i}.st`), scale = r.tt === "USD" ? 2 : 0;
              if (s !== null) {
                const [ng, le = ""] = s.split(".");
                if (le.length > scale && /[1-9]/.test(le.slice(scale))) f.loi[`dong.${i}.st`] = "Số tiền có phần lẻ nhỏ hơn đơn vị tiền tệ; không tự làm tròn.";
                else minor = (ng + le.slice(0, scale).padEnd(scale, "0")).replace(/^0+(?=\d)/, "");
              }
            }
            return {lan: r.lan.trim(), gia_tri_loai: r.gl, gia_tri_thap_phan: r.gl === "PERCENT" ? soNhap(r.tp, `dong.${i}.tp`) : null,
              so_tien_minor: minor, tien_te: r.gl === "AMOUNT" ? r.tt : null, moc_loai: r.ml || null,
              moc_ngay: r.ml === "NGAY" ? r.mn || null : null, moc_su_kien: r.ml === "SU_KIEN" ? r.ms || null : null, ghi_chu: r.gc.trim() || null};
          })};
        }
        if (Object.keys(f.loi).length) { ve(); return; }
      }
      const path = "du-an-ban/" + f.hanh, k = JSON.stringify([path, body]), so = nhanBanGhi(k);
      if (!so) return;
      const {rec, ve: chu} = so, g = genLenh, e = ep, a = actor();
      const dung = () => e === ep && a === actor() && g === genLenh && form === f && tab === "du-an-ban";
      let xong = false;
      f.ban = true; f.lai = null; f.msg = "Đang lưu…"; ve();
      try {
        // goi() chung bỏ locator; đọc riêng lỗi DA để giữ `truong`, dùng cùng token/phiên/khóa chung.
        const res = await fetch("/api/crm/" + path, {method: "POST", headers: {"X-KTT-Token": TOKEN, "Content-Type": "application/json"},
          credentials: "same-origin", cache: "no-store", body: JSON.stringify({...body, khoa: rec.khoa})});
        const r = await docJson(res);
        if (!res.ok) { const err = new LoiG(res.status, r.error, r.message || "Không lưu được dự án."); err.truong = r.truong; throw err; }
        xong = true;
        if (!dung()) return;
        id = r.da_ban_id || f.da; pb = "";
        // Sau ngừng bán vẫn cần thấy chi tiết phiên bản mới, kể cả trước đó có bật lọc.
        chiDangBan = false; boForm(); trangThai("Đã lưu dự án."); await nap();
      } catch (err) {
        xong = !!err.status && !chuaRo(err);
        if (!dung()) return;
        if (loiAnNinh(err)) { loiDs = loiDoc(err); ve(); return; }
        f.ban = false;
        if (err.status === 400 && err.truong) f.loi[err.truong.replace(/^thong_tin\./, "")] = err.message;
        if (err.status === 409 && ["CRM_DA_PHIEN_BAN_CU", "CRM_DA_LO_LAN_CU"].includes(err.code)) {
          f.cu = true;
          f.msg = f.hanh === "lo" ? "Lô/căn vừa được người khác đổi. " + err.message : f.hanh === "tien-do" ? "Tiến độ tiêu chuẩn vừa được người khác sửa — tải lại để xem bản mới" : "Dự án vừa được người khác sửa — tải lại để xem bản mới";
        } else if (!xong) { f.lai = body; f.msg = "Chưa rõ kết quả lưu. Gửi lại y nguyên để kiểm tra bằng cùng khóa."; }
        else f.msg = err.message || "Không lưu được dự án.";
        ve();
      } finally { traBanGhi(k, rec, chu, xong); }
    }
    function veForm() {
      const f = form, chung = ["bat-ban", "cap-nhat"].includes(f.hanh), bangSua = ["phi", "lo", "tien-do"].includes(f.hanh), modal = !chung && !bangSua;
      const box = node(modal ? "dialog" : "section", undefined, "da-form" + (modal ? " da-form-modal" : "")); box.id = "crmg-da-form";
      const ten = {"bat-ban": "Thêm dự án đang bán", "cap-nhat": "Sửa thông tin", "ngung-ban": "Ngừng bán", "mo-ban-lai": "Mở bán lại", phi: "Sửa phí", lo: "Sửa lô/căn", "tien-do": "Sửa tiến độ tiêu chuẩn"}[f.hanh];
      box.append(node("h3", ten));
      if (modal) {
        box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true"); box.setAttribute("aria-label", ten);
        box.append(node("p", `Xác nhận ${ten.toLowerCase()} dự án này? Thao tác tạo phiên bản mới và ghi nhận lý do.`));
        box.addEventListener("cancel", ev => { ev.preventDefault(); if (!f.ban && !f.lai && form === f) { boForm(); ve(); } });
        // ve() gắn DOM sau khi tạo các khối; chỉ mở modal còn thuộc form hiện hành.
        Promise.resolve().then(() => { if (box.isConnected && form === f && !box.open) box.showModal(); });
      }
      const luoi = node("div", undefined, "da-form-luoi");
      const field = (k, label, options, nhieuDong = false, vao = luoi, nguon = f.v, cot = k) => {
        const wrap = node("div", undefined, "da-form-o"), el = node(options ? "select" : nhieuDong ? "textarea" : "input");
        el.id = "crmg-da-f-" + k;
        if (options) for (const [v, t] of options) { const op = node("option", t); op.value = v; el.append(op); }
        else if (!nhieuDong) { el.type = "text"; if (["gia_dat_tru", "don_gia_niem_yet"].includes(k)) el.inputMode = "decimal"; }
        el.value = nguon[cot] ?? ""; el.disabled = f.ban || !!f.lai;
        if (["muc", "dien_tich"].includes(cot)) el.inputMode = "decimal";
        if (f.hanh === "lo" && cot === "ma" && nguon.expected_lan !== undefined) el.readOnly = true;
        if (k === "ly_do") el.required = true;
        const loi = node("small", f.loi[k] || "", "da-form-loi"); loi.id = el.id + "-loi"; loi.setAttribute("role", "alert");
        el.setAttribute("aria-describedby", loi.id); el.setAttribute("aria-invalid", String(!!f.loi[k]));
        const doi = () => { if (form === f && el.isConnected && !el.disabled && !el.readOnly) { nguon[cot] = el.value; delete f.loi[k]; loi.textContent = ""; el.setAttribute("aria-invalid", "false"); } };
        el.addEventListener("input", doi); el.addEventListener("change", doi);
        wrap.append(...truong(label, el), loi); if (vao) vao.append(wrap); return wrap;
      };
      const dm = danhSach?.danh_muc || chiTiet?.danh_muc || {};
      if (f.hanh === "bat-ban") field("du_an_id", "Dự án", [["", "Chọn dự án"], ...(danhSach.du_an_chua_ban || []).map(v => [v.du_an_id, v.du_an_ten || "Dự án chưa có tên"])]);
      if (chung) {
        field("vi_tri", "Vị trí"); field("mo_ta", "Mô tả", null, true);
        field("don_gia_niem_yet", "Đơn giá niêm yết /m² (chưa gồm VAT)");
        field("tien_te", "Tiền tệ", (dm.tien_te || []).map(v => [v.ma, v.nhan]));
        field("loai_hinh_id", "Loại hình", [["", "Chọn loại hình"], ...(danhSach?.loai_hinh || []).map(v => [v.id, v.ten])]);
        field("thue_suat", "Thuế suất", (dm.thue_suat || []).map(v => [v.ma, v.nhan]));
        field("gia_dat_tru", "Giá đất được trừ /m²"); field("giai_doan_g7", "Giai đoạn tiến độ mặc định");
      }
      if (bangSua) {
        const options = nhom => (dm[nhom] || []).map(v => [v.ma, v.nhan]);
        const cell = (i, c, label, opts) => field(`${f.hanh === "tien-do" ? "dong" : f.hanh}.${i}.${c}`, label, opts, false, null, f.rows[i], c);
        const bo = i => nut("Bỏ dòng", () => { f.rows.splice(i, 1); f.loi = {}; ve(); }, "link-button", f.ban || !!f.lai || (f.hanh === "tien-do" && f.rows.length <= 1));
        if (f.hanh === "phi") {
          box.append(node("p", "Mức chưa gồm VAT"), bang(["Tên phí", "Loại phí", "Mức", "Đơn vị tính", "Tiền tệ", "Cơ sở tính", ""], f.rows.map((r, i) => [
            cell(i, "ten", "Tên phí"), cell(i, "loai", "Loại phí", options("loai_phi")), cell(i, "muc", "Mức chưa gồm VAT"), cell(i, "don_vi_tinh", "Đơn vị tính", options("don_vi_tinh")), cell(i, "tien_te", "Tiền tệ", options("tien_te")), cell(i, "co_so_tinh", "Cơ sở tính"), bo(i)])));
        } else if (f.hanh === "lo") {
          box.append(bang(["Mã lô/căn", "Diện tích (m²)", "Trạng thái", "Ghi chú", ""], f.rows.map((r, i) => [cell(i, "ma", "Mã lô/căn"), cell(i, "dien_tich", "Diện tích (m²)"), cell(i, "trang_thai", "Trạng thái", options("trang_thai_lo")), cell(i, "ghi_chu", "Ghi chú"), r.expected_lan === undefined ? bo(i) : ""])));
        } else {
          box.append(node("p", "Áp dụng ngay — QD-20261025-07"), bangNhapChuan(f.rows.length, (i, c, label, opts) => {
            const r = f.rows[i];
            if (c === "tt") opts = options("tien_te");
            if (c === "ms") {
              opts = [["", "Chọn mốc"], ...(mocChuan?.moc || []).map(m => [m.ma, m.nhan])];
              if (r.ms && !opts.some(x => x[0] === r.ms)) opts.push([r.ms, mocDong({moc_loai: "SU_KIEN", moc_su_kien: r.ms})]);
            }
            const wrap = cell(i, c, label, opts), el = wrap.children[1];
            if (c === "mn") el.type = "date";
            if (["tp", "st"].includes(c)) el.inputMode = "decimal";
            return wrap;
          }, bo));
        }
        box.append(nut(f.hanh === "phi" ? "Thêm dòng phí" : f.hanh === "lo" ? "Thêm lô/căn" : "Thêm đợt", () => { f.rows.push(dongMoi(f)); ve(); }, "button secondary", f.ban || !!f.lai));
        if (f.loi[f.hanh]) box.append(node("p", f.loi[f.hanh], "da-form-loi"));
      }
      if (!["lo", "tien-do"].includes(f.hanh)) field("ly_do", "Lý do (bắt buộc)", null, true); box.append(luoi);
      if (f.msg) { const msg = node("p", f.msg, "da-form-loi"); msg.setAttribute("role", "alert"); box.append(msg); }
      const thanh = node("div", undefined, "da-thanh");
      thanh.append(nut(chung ? "Lưu thông tin" : bangSua ? {phi: "Lưu phí", lo: "Lưu lô/căn", "tien-do": "Áp dụng tiến độ"}[f.hanh] : "Xác nhận " + ten.toLowerCase(), () => guiForm(), "button primary", f.ban || f.cu || !!f.lai));
      if (f.cu) thanh.append(nut("Tải lại bản mới", () => taiBanMoi(f), "button secondary", f.ban));
      if (f.lai) thanh.append(nut("Gửi lại y nguyên (cùng khóa)", () => guiForm(f.lai), "button primary", f.ban));
      thanh.append(nut("Hủy", () => { boForm(); ve(); }, "button secondary", f.ban || !!f.lai)); box.append(thanh); return box;
    }
    const dinhNgay = new Intl.DateTimeFormat("vi-VN", {timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric"});
    const nhan = (nhom, ma) => ((chiTiet && chiTiet.danh_muc || danhSach && danhSach.danh_muc || {})[nhom] || []).find(x => x.ma === ma)?.nhan || "Chưa có thông tin";
    const ngay = (hienThi, goc) => hienThi || (goc && !isNaN(new Date(goc).getTime()) ? dinhNgay.format(new Date(goc)) : "—");
    const khoang = r => `${ngay(r.hieu_luc_tu_hien_thi, r.hieu_luc_tu || r.valid_from)} → ${r.hieu_luc_den || r.valid_to ? "trước " + ngay(r.hieu_luc_den_hien_thi, r.hieu_luc_den || r.valid_to) : "hiện hành"}`;
    const nguoi = v => !v ? "—" : /^MO_PHONG_|^DEMO_/.test(v) ? "Người dùng mô phỏng" : /^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(v) || /^\d+$/.test(v) ? "Người dùng" : v;
    function mocDong(r) {
      if (r.moc_loai === "NGAY") return ngay(null, r.moc_ngay);
      if (r.moc_loai !== "SU_KIEN") return "—";
      const m = (mocChuan?.moc || []).find(x => x.ma === r.moc_su_kien);
      if (m) return m.nhan;
      for (const p of mocChuan?.moc_tham_so || []) {
        const parts = p.mau_ma.split("<n>"), s = String(r.moc_su_kien || "");
        if (parts.length !== 2 || !s.startsWith(parts[0]) || !s.endsWith(parts[1])) continue;
        const n = s.slice(parts[0].length, parts[1] ? -parts[1].length : undefined);
        if (/^\d+$/.test(n)) return p.nhan.replace(/\bn\b/, n);
      }
      return "Sự kiện khác (chưa có nhãn)";
    }
    function roi() { genDs += 1; genCt += 1; genLs += 1; boForm(); }
    function xoa() { roi(); danhSach = chiTiet = lichSu = null; id = null; pb = ""; xemLichSu = false; loiDs = loiCt = loiLs = ""; }
    function loiDoc(e) {
      if (loiAnNinh(e)) { xoa(); return loiDs = "Phiên hoặc quyền truy cập đã thay đổi. Bấm Làm mới để tải lại."; }
      else if (e.status === 404) return "Không thấy dự án trong phạm vi hiện hành.";
      else if (e.status === 0) return "Mất kết nối khi tải dữ liệu. Bấm Làm mới để thử lại.";
      else return "Không tải được dữ liệu dự án. Bấm Làm mới để thử lại.";
    }
    async function napDs() {
      if (K.vaiDangChan("crm_g")) return;
      const g = ++genDs, e = ep, chi = chiDangBan, dung = () => e === ep && g === genDs && tab === "du-an-ban";
      danhSach = null; chiTiet = lichSu = null; genCt += 1; genLs += 1; loiDs = ""; ve();
      try {
        const r = await docJson(await goi("/api/crm/du-an-ban" + (chi ? "?dang_ban=1" : "")));
        if (!dung()) return false;
        danhSach = r;
        if (!(r.du_an_ban || []).some(x => x.da_ban_id === id)) { id = null; pb = ""; xemLichSu = false; }
        ve(); return true;
      } catch (err) { if (dung()) { loiDs = loiDoc(err); ve(); } return false; }
    }
    async function napCt() {
      if (!id || K.vaiDangChan("crm_g")) return;
      const g = ++genCt, e = ep, da = id, phien = pb, dung = () => e === ep && g === genCt && tab === "du-an-ban" && da === id && phien === pb;
      chiTiet = null; loiCt = ""; ve();
      try {
        const r = await docJson(await goi("/api/crm/du-an-ban/" + encodeURIComponent(da) + (phien ? "?phien_ban=" + encodeURIComponent(phien) : "")));
        if (!dung()) return;
        chiTiet = r; ve();
        // Danh mục mốc nghiệp vụ có sẵn của Báo giá; GET chỉ đọc, không đụng editor Báo giá.
        if (!mocChuan) {
          const m = await docJson(await goi("/api/crm/bao-gia/moc-chuan"));
          if (dung()) { mocChuan = m; ve(); }
        }
      } catch (err) {
        if (!dung()) return;
        // Nhãn mốc chưa tải được vẫn giữ ảnh chụp đã đọc; lỗi phiên/quyền luôn xóa dữ liệu.
        if (!chiTiet || loiAnNinh(err)) { loiCt = loiDoc(err); ve(); }
      }
    }
    async function napLs() {
      if (!id || K.vaiDangChan("crm_g")) return;
      const g = ++genLs, e = ep, da = id, dung = () => e === ep && g === genLs && da === id && tab === "du-an-ban" && xemLichSu;
      lichSu = null; loiLs = ""; ve();
      try { const r = await docJson(await goi("/api/crm/du-an-ban/" + encodeURIComponent(da) + "/lich-su")); if (dung()) { lichSu = r; ve(); } }
      catch (err) { if (dung()) { loiLs = loiDoc(err); ve(); } }
    }
    async function nap() { if (await napDs()) { if (id) { napCt(); if (xemLichSu) napLs(); } } }
    function mo(da) { boForm(); id = da; pb = ""; chiTiet = lichSu = null; xemLichSu = false; genLs += 1; loiLs = ""; napCt(); }
    function bangRong(cot, rows, thongBao) { return rows.length ? bang(cot, rows) : node("p", thongBao, "da-trong"); }
    function veCt() {
      const box = node("section", undefined, "da-chi-tiet"); box.id = "crmg-da-chi-tiet";
      const da = (danhSach?.du_an_ban || []).find(x => x.da_ban_id === id);
      box.append(node("h3", "Chi tiết · " + (da?.du_an_ten || "Dự án")));
      if (loiCt) box.append(node("p", loiCt, "da-loi"));
      if (!chiTiet) { if (!loiCt) box.append(node("p", "Đang tải chi tiết…")); return box; }
      const s = chiTiet.anh_chup || {}, h = chiTiet.hien_thi || {}, tt = s.thong_tin || {};
      const thanh = node("div", undefined, "da-thanh"), sel = node("select"); sel.id = "crmg-da-phien-ban";
      for (const v of chiTiet.phien_ban_ds || []) { const op = node("option", `Phiên bản ${v.phien_ban} · ${khoang(v)}`); op.value = String(v.phien_ban); sel.append(op); }
      sel.value = pb || String(s.phien_ban?.so || "");
      sel.addEventListener("change", () => { if (!sel.isConnected) return; boForm(); pb = sel.value; napCt(); });
      thanh.append(...truong("Phiên bản đang xem", sel), nut(xemLichSu ? "Ẩn lịch sử" : "Lịch sử", () => { xemLichSu = !xemLichSu; genLs += 1; ve(); if (xemLichSu) napLs(); }));
      if (chiTiet.duoc_sua && !form) {
        thanh.append(nut("Sửa thông tin", () => moForm("cap-nhat")));
        for (const [ten, hanh] of [["Sửa phí", "phi"], ["Sửa lô/căn", "lo"], ["Sửa tiến độ tiêu chuẩn", "tien-do"]]) thanh.append(nut(ten, () => moForm(hanh)));
        if (hienHanh()) thanh.append(nut(s.trang_thai === "DANG_BAN" ? "Ngừng bán" : "Mở bán lại", () => moForm(s.trang_thai === "DANG_BAN" ? "ngung-ban" : "mo-ban-lai")));
      }
      const chung = node("dl", undefined, "da-thong-tin");
      for (const [ten, v] of [["Vị trí", tt.vi_tri], ["Mô tả", tt.mo_ta], ["Đơn giá niêm yết", h.don_gia], ["Tiền tệ", nhan("tien_te", s.tien_te)],
        ["Loại hình", h.loai_hinh], ["Thuế suất", nhan("thue_suat", s.thue?.thue_suat)], ["Giá đất được trừ", h.gia_dat_tru], ["Trạng thái", h.trang_thai], ["Hiệu lực phiên bản", h.phien_ban]]) chung.append(node("dt", ten), node("dd", v || "Chưa có thông tin"));
      box.append(thanh, node("h4", "Thông tin chung"), chung, node("p", "Giá chưa gồm VAT"), node("h4", "Phí tiêu chuẩn"),
        bangRong(["Tên phí", "Loại phí", "Mức", "Đơn vị tính", "Tiền tệ", "Cơ sở tính"], (s.phi || []).map((f, i) => [f.ten, h.phi?.[i]?.loai || nhan("loai_phi", f.loai), h.phi?.[i]?.muc || "Chưa có thông tin", nhan("don_vi_tinh", f.don_vi_tinh), nhan("tien_te", f.tien_te), f.co_so_tinh || "—"]), "Chưa có phí tiêu chuẩn."),
        node("h4", "Lô/căn"), bangRong(["Mã lô/căn", "Diện tích (m²)", "Trạng thái"], (s.lo || []).map((l, i) => [l.ma, h.lo?.[i]?.dien_tich || "Chưa có thông tin", h.lo?.[i]?.trang_thai || nhan("trang_thai_lo", l.trang_thai)]), "Chưa có lô/căn."),
        node("h4", "Tiến độ thanh toán tiêu chuẩn"));
      const bc = s.bo_chuan;
      box.append(node("p", !bc || bc.trang_thai !== "HIEU_LUC" ? "Chưa có tiến độ tiêu chuẩn hiệu lực." : `Phiên bản ${bc.version?.phien_ban || ""} · ${khoang(bc.version || {})} · ${bc.nguon === "AP_DUNG_NGAY" ? "Bán hàng áp dụng ngay" : bc.nguon === "CFO_DUYET" ? "CFO đã duyệt" : "Chưa có thông tin nguồn"}`));
      if (bc?.trang_thai === "HIEU_LUC") box.append(bangRong(["Đợt", "Giá trị (%) / số tiền", "Mốc", "Ghi chú"], (bc.rows || []).map((r, i) => [r.lan, h.bo_chuan_dong?.[i]?.gia_tri_hien_thi || "Chưa có giá trị hiển thị", mocDong(r), r.ghi_chu || ""]), "Chưa có đợt thanh toán."));
      return box;
    }
    function veLs() {
      const box = node("section", undefined, "da-lich-su"); box.id = "crmg-da-lich-su"; box.append(node("h3", "Lịch sử dự án"));
      if (!lichSu) { box.append(node("p", loiLs || "Đang tải lịch sử…", loiLs ? "da-loi" : "")); return box; }
      const rows = [...(lichSu.phien_ban || [])].sort((a, b) => a.phien_ban - b.phien_ban);
      const truong = {vi_tri: "Vị trí", mo_ta: "Mô tả", don_gia_niem_yet: "Đơn giá niêm yết", tien_te: "Tiền tệ", loai_hinh_id: "Loại hình", thue_suat: "Thuế suất", gia_dat_tru: "Giá đất được trừ", giai_doan_g7: "Tiến độ tiêu chuẩn"};
      box.append(node("h4", "Các phiên bản"), bangRong(["Phiên bản", "Hiệu lực từ → đến", "Người lập", "Lý do", "Trường đã đổi"], rows.map((v, i) => {
        let doi = "Khởi tạo";
        if (i) {
          const a = rows[i - 1].noi_dung, b = v.noi_dung;
          if (!a || !b) doi = "Chưa có nội dung để đối chiếu";
          else {
            const dsDoi = Object.entries(truong).filter(([k]) => JSON.stringify(a.thong_tin?.[k] ?? null) !== JSON.stringify(b.thong_tin?.[k] ?? null)).map(([, ten]) => ten);
            if (a.dang_ban !== b.dang_ban) dsDoi.push("Trạng thái bán");
            if (JSON.stringify(a.phi) !== JSON.stringify(b.phi)) dsDoi.push("Phí tiêu chuẩn");
            doi = dsDoi.join(", ") || "Không đổi thông tin bán hàng";
          }
        }
        return ["Phiên bản " + v.phien_ban, khoang(v), nguoi(v.lap_boi_ten || v.lap_boi), v.ly_do || "—", doi];
      }), "Chưa có phiên bản."));
      box.append(node("h4", "Sự kiện bán hàng và áp dụng tiến độ"), bangRong(["Ngày", "Thao tác", "Người thực hiện", "Lý do"], (lichSu.su_kien || []).filter(x => ["CRM_DA_BAT_BAN", "CRM_DA_NGUNG_BAN", "CRM_DA_MO_BAN_LAI", "CRM_CHUAN_AP_DUNG"].includes(x.hanh_dong)).map(x => [ngay(null, x.luc), x.hanh_dong_hien_thi || ({CRM_DA_BAT_BAN: "Bật bán", CRM_DA_NGUNG_BAN: "Ngừng bán", CRM_DA_MO_BAN_LAI: "Mở bán lại", CRM_CHUAN_AP_DUNG: "Áp dụng tiến độ thanh toán tiêu chuẩn"})[x.hanh_dong], nguoi(x.nguoi_ten || x.nguoi), x.ly_do || "—"]), "Chưa có sự kiện bán hàng hoặc áp dụng tiến độ."));
      box.append(node("h4", "Tiến độ tiêu chuẩn đã áp dụng"), bangRong(["Giai đoạn", "Phiên bản", "Hiệu lực từ", "Người áp dụng", "Căn cứ"], (lichSu.tien_do || []).filter(v => v.trang_thai === "HIEU_LUC" && !v.khoang_rong).map(v => [v.giai_doan_hien_thi || v.giai_doan || "Toàn dự án", v.phien_ban, ngay(v.valid_from_hien_thi, v.valid_from), nguoi(v.ap_dung_boi_ten || v.ap_dung_boi || v.duyet_boi_ten || v.duyet_boi), v.nguon === "AP_DUNG_NGAY" ? "Bán hàng áp dụng ngay — " + (v.can_cu || "Chưa có căn cứ") : v.nguon === "CFO_DUYET" ? "CFO duyệt (bản cũ)" : "Chưa có thông tin"]), "Chưa có tiến độ tiêu chuẩn đã áp dụng."));
      box.append(node("h4", "Lịch sử lô/căn"), bangRong(["Mã lô/căn", "Lần", "Hiệu lực từ → đến", "Diện tích (m²)", "Trạng thái", "Người lập", "Ghi chú"], (lichSu.lo || []).flatMap(l => (l.lich_su || []).map(v => [l.ma, v.lan, khoang(v), v.dien_tich_hien_thi || "Chưa có thông tin", v.trang_thai_hien_thi || nhan("trang_thai_lo", v.trang_thai), nguoi(v.tao_boi_ten || v.tao_boi), v.ghi_chu || "—"])), "Chưa có lịch sử lô/căn."));
      return box;
    }
    function veDa() {
      const box = node("div", undefined, "da-xem"); box.id = "crmg-da";
      const loc = node("input"); loc.type = "checkbox"; loc.id = "crmg-da-chi-dang-ban"; loc.checked = chiDangBan;
      loc.addEventListener("change", () => { if (!loc.isConnected) return; boForm(); chiDangBan = loc.checked; id = null; pb = ""; xemLichSu = false; napDs(); });
      const label = node("label", undefined, "da-loc"); label.append(loc, node("span", "Chỉ dự án đang bán")); box.append(label);
      if (!danhSach) { box.append(node("p", loiDs || "Đang tải danh sách dự án…", loiDs ? "da-loi" : "")); return [box]; }
      if (themDuoc() && !form) box.append(nut("Thêm dự án đang bán", () => moForm("bat-ban"), "button primary"));
      if (form) box.append(veForm());
      const rows = danhSach.du_an_ban || [];
      const tb = bangRong(["Dự án", "Đơn giá niêm yết", "Số loại phí", "Số lô/căn", "Trạng thái", "Phiên bản"], rows.map(v => [v.du_an_ten || "Dự án chưa có tên", v.don_gia_hien_thi || "Chưa có thông tin", v.so_phi, v.so_lo, v.trang_thai_hien_thi || (v.dang_ban ? "Đang bán" : "Ngừng bán"), v.phien_ban]), "Không có dự án trong danh sách này.");
      if (rows.length) Array.from(tb.children[0].children[1].children).forEach((tr, i) => {
        tr.className = "da-dong"; tr.tabIndex = 0; tr.setAttribute("aria-label", "Xem dự án " + (rows[i].du_an_ten || "chưa có tên")); tr.setAttribute("aria-selected", String(id === rows[i].da_ban_id));
        const chonDa = () => { if (tr.isConnected) mo(rows[i].da_ban_id); };
        tr.addEventListener("click", chonDa); tr.addEventListener("keydown", e => { if (["Enter", " "].includes(e.key)) { e.preventDefault(); chonDa(); } });
      });
      box.append(tb); if (id) box.append(veCt()); if (id && xemLichSu) box.append(veLs()); return [box];
    }
    return {ve: veDa, nap, roi, xoa};
  })();

  // ------------------------------------------------------------------ đổi vai (người tham gia seam chung)
  function xoa() {  // đồng bộ, trước await đầu tiên của lần đổi vai ở BẤT KỲ selector nào
    ep += 1; duAnBan.xoa(); ds = null; bc = null; bcDoc = null; soDong = 1; taiTep = null; boChon(); doiFormTai(); khoaMap.clear(); nhapGt.clear(); genDoc += 1;
    chuNutTep = null;  // đổi vai: mọi ý định/nút gửi lại cũ đã bị huyYDinhTai vô hiệu; gỡ DOM dưới đây
    if (oGuiLai) { oGuiLai.replaceChildren(); delete oGuiLai.dataset.tep; }
    ve(); trangThai("");
    Promise.resolve().then(() => napTong());  // trong barrier: chỉ ghi "cần nạp" — nạp lại khi ý định đổi vai mới nhất giải quyết
  }
  function napTong() { napDs(); if (tab === "chuan") napBc(); if (tab === "du-an-ban") duAnBan.nap(); }
  K.dangKyVai("crm_g", xoa, () => { napTong(); if (tab === "mau" && pbChon) napCt(); });

  // ------------------------------------------------------------------ vẽ
  function ve() {
    if (!oNoiDung) dungKhung();
    $("crmg-vai").textContent = tab === "du-an-ban" ? "Dữ liệu theo phạm vi quyền CRM hiện hành." : ds ? `Vai hiện hành: ${ds.nguoi.dang_nhap} (${ds.nguoi.vai_tro}) · đổi vai ở mục Vai mô phỏng phía trên.` : "Đang tải…";
    $("crmg-tab-mau").setAttribute("aria-pressed", String(tab === "mau"));
    $("crmg-tab-chuan").setAttribute("aria-pressed", String(tab === "chuan"));
    $("crmg-tab-da").setAttribute("aria-pressed", String(tab === "du-an-ban"));
    oNoiDung.replaceChildren(...(tab === "mau" ? veMau() : tab === "chuan" ? veChuan() : duAnBan.ve()));
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
    const t3 = nut("Dự án đang bán", () => doiTab("du-an-ban"), "button secondary"); t3.id = "crmg-tab-da";
    tabs.append(t1, t2, t3);
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
    const chuThich = node("p", "Tiến độ tiêu chuẩn sửa trong Dự án đang bán, áp dụng ngay");
    if (!bc) return [chuThich, K.empty("Chưa tải bộ chuẩn", "Bấm ↻ Làm mới.")];
    const out = [chuThich], duAn = bc.du_an || [];
    if (!duAn.length) return [chuThich, K.empty("Không có dự án trong phạm vi CRM của vai này", "")];
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
        const a = duAn.find(x => x.id === v.du_an_id), box = node("div", undefined, "card");
        box.append(node("h4", `${a ? a.ma_junsky : v.du_an_id} · ${v.giai_doan} · v${v.phien_ban} · ${TT_CHUAN[v.trang_thai] || v.trang_thai}`
          + (v.valid_from ? ` · hiệu lực ${v.valid_from} → ${v.valid_to || "…"}` : "")), node("p", `Lập bởi ${v.lap_boi}${v.gui_boi ? " · gửi bởi " + v.gui_boi : ""}${v.duyet_boi ? " · duyệt bởi " + v.duyet_boi : ""}`),
          bangChuan(bc.cot, v.dong));
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
  // Bảng nhập G7 dùng chung với Dự án đang bán; Báo giá có closure/DTO riêng.
  function bangNhapChuan(n, field, bo, cot = ["Đợt", "Giá trị (%) / số tiền", "Mốc", "Ghi chú"]) {
    return bang([...cot, ""], Array.from({length: n}, (_, i) => {
      const f = (c, label, opts) => field(i, c, label, opts);
      const g = node("div", undefined, "da-chuan-nhom"), m = node("div", undefined, "da-chuan-nhom");
      g.append(f("gl", "Loại giá trị", [["PERCENT", "Tỷ lệ %"], ["AMOUNT", "Số tiền"]]), f("tp", "Tỷ lệ (%)"), f("st", "Số tiền"), f("tt", "Tiền tệ"));
      m.append(f("ml", "Loại mốc", [["NGAY", "Ngày"], ["SU_KIEN", "Sự kiện"]]), f("mn", "Ngày"), f("ms", "Sự kiện"));
      return [f("lan", "Đợt"), g, m, f("gc", "Ghi chú"), bo(i)];
    }));
  }
  function veLap(duAn) {
    const f = node("div", undefined, "demo-actions");
    const sd = chon("lap-du-an", duAn.map(a => [a.id, `${a.phap_nhan} · ${a.ma_junsky}`]), duAn[0].id), gd = nhap("lap-giai-doan", "DEMO_G7_STAGE_1");
    if (!duAn.some(a => a.id === sd.value)) { sd.value = duAn[0].id; nhapGt.set(sd.id, sd.value); }
    f.append(...truong("Dự án", sd), ...truong("Giai đoạn", gd));
    const tb = bangNhapChuan(soDong, (i, c, label, opts) => {
      const el = opts ? chon(`l-${c}-${i}`, opts, "", "— chưa có —") : nhap(`l-${c}-${i}`, c === "lan" ? String(i + 1) : c === "tt" ? "VND" : "", c === "mn" ? "date" : "text");
      el.setAttribute("aria-label", `Dòng ${i + 1} · ${label}`);
      if (c === "tp") el.placeholder = "vd 40";
      if (c === "st") el.placeholder = "số nguyên đơn vị nhỏ nhất";
      if (c === "ms") el.placeholder = "MÃ_SỰ_KIỆN";
      return el;
    }, i => nut("Bỏ", () => { const ds2 = docDong(); ds2.splice(i, 1); ghiDong(ds2); genForm += 1; ve(); }, "link-button", soDong <= 1), bc.cot);
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
  window.addEventListener("hashchange", () => { if (location.hash === "#hopdong") { napTong(); if (tab === "mau" && pbChon) napCt(); } });
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
  const VAI_VN = {KE_TOAN: "Kế toán", KE_TOAN_TRUONG: "Kế toán trưởng", CFO: "CFO", NHAP_JUNSKY: "Nhập Junsky", XEM: "Chỉ xem", BAN_HANG: "Bán hàng", DU_AN: "Dự án"};
  const TT_SO = {SOAN_THAO: "Đang soạn", CHO_KY: "Chờ ký (đã xuất DOCX+PDF)", DA_KY: "Đã ký — chờ kế toán kiểm"};
  const TT_XUAT = {PDF_DAT: "DOCX + PDF đạt", PDF_CHUA_SAN_SANG: "DOCX đã giữ · PDF chưa sẵn sàng", PDF_LOI: "DOCX đã giữ · PDF lỗi", DA_CU: "Bản cũ (revision đã đổi)"};

  let ep = 0, genForm = 0, genDs = 0, genBg = 0, genSo = 0, cheDo = "bao_gia";
  let ds = null, bgChon = null, bgCt = null, soChon = null, soCt = null, soDongBg = 1, soDongSo = 0;
  // FIX01 #3: số lần sửa NỘI DUNG form (bg-/so-) và mốc đồng bộ với revision máy chủ — In/Chuyển/Xuất chỉ khi không còn thay đổi chưa lưu
  // FIX03 R1: `nhapMoi` = ĐỊNH DANH của một lần bắt đầu nháp MỚI ({so, tao}) — "+ Báo giá mới" luôn tạo định danh mới (MOI → MOI là nháp KHÁC);
  // gõ tiếp cùng nháp giữ định danh. ACK tạo mới chỉ ghi vào đúng định danh của ý định đó (`tao` = {id, revision} của báo giá đã tạo).
  let soSua = 0, dongBo = 0, nhapMoi = null, soNhapMoi = 0;
  // BG-1b (BG-03): kết quả tính TỰ ĐỘNG của máy chủ cho form báo giá (xem-truoc). `tinhBg` = {khoa, tinh, nhan,…} của lần trả về mới nhất khớp form;
  // `tinhCho` = đang chờ (ngừng gõ 400 ms hoặc yêu cầu đang bay) → ô mờ hiện "…"; `tinhSeq` loại phản hồi cũ; lỗi mạng giữ `tinhBg` cũ + `tinhLoi`.
  let tinhBg = null, tinhCho = false, tinhLoi = "", tinhSeq = 0, tinhGen = 0, tinhHen = null, tinhBay = null, tinhLai = 0, tinhLaiHen = null, tinhDungLuu = true;
  let mocChuan = null, mocChuanCho = false, bangMocDem = null;  // danh mục mốc chuẩn từ máy chủ (GET /api/crm/bao-gia/moc-chuan)
  let dsMoBg = [], dsLoiMocBg = [], dsNutBg = [], oTongBg = null, oGoiYTong = null, oLuuYTong = null, oKiemBg = null, oTinhLoi = null, oNguCanh = null, oTongNhap = null;
  // BG-1d: editor 2 bước. `buoc2Mo` = null (tự: mở khi đã có khách/phí) | true | false (người dùng gấp/mở); `oFx*` = ô tỷ giá + nhãn nguồn + lỗi theo trường;
  // `oTongLon` = khối Tổng giá trị cỡ lớn (chỉ hiển thị kết quả của máy chủ).
  let buoc2Mo = null, oFx = null, oFxNguon = null, oFxLoi = null, oTongLon = null;
  // BG-1d vòng 2: tỷ giá USD/VND MẶC ĐỊNH chung (GET /api/crm/bao-gia/ty-gia-mac-dinh). `fxMd` = bản đọc mới nhất (null = chưa có/lỗi); `fxMdSua` = trạng thái
  // ô Sửa (kế toán; giữ ngoài ô nhập ghi xuyên để gõ không làm đổi thế hệ form báo giá); `tinhChoFxMd` = phép tính đang chờ tỷ giá mặc định;
  // `loiTai` = thông báo lỗi TẢI gần nhất đang hiện ở dòng trạng thái (xóa khi tải thành công — không xóa thông báo của lệnh).
  let fxMd = null, fxMdCho = false, fxMdLoi = "", fxMdGen = 0, oFxMd = null, tinhChoFxMd = false, loiTai = null, fxMdLai = 0, fxMdLaiHen = null;
  const fxMdSua = {mo: false, ty: "", ly: "", loi: "", dang: false};
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
  // Tiền tệ CỦA LỊCH thanh toán báo giá = tiền chính VND (máy chủ `TIEN_CHINH`): lưu từ màn này luôn là dữ liệu v2, mọi số trong lịch hiểu bằng VND, kể cả khi đơn giá USD.
  const TIEN_LICH = "VND";
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
  // Lỗi TẢI (danh sách/chi tiết) hiện ở dòng trạng thái và tự hết khi lần tải sau thành công (vd "Phiên CRM chưa có…" sau khi bấm ↻ Làm mới đã được).
  function baoLoiTai(msg) { loiTai = msg || ""; trangThai(msg, true); }
  function xoaLoiTai() { if (loiTai === null) return; if (oTrangThai && oTrangThai.textContent === loiTai) trangThai(""); loiTai = null; }
  const gt = (id, md = "") => nhapGt.has("gk-" + id) ? nhapGt.get("gk-" + id) : md;
  // BG-03: ô nội dung BÁO GIÁ (trừ ghi chú/liên hệ/mô tả không ảnh hưởng số tính) → đánh dấu "đang chờ" và hẹn máy chủ tính: ngừng gõ 400 ms hoặc rời ô
  // (change) = tính ngay. `dinhDang` (nếu có) chỉ đổi dạng chữ khi rời ô (dấu chấm hàng nghìn, dd/mm/yyyy), không đổi giá trị.
  const KHONG_TINH = /^gk-bg-(gc|l-gc-\d+|lo-mt|khach-lh)$/;
  function o(id, el, md = "", khiDoi, dinhDang) {
    el.id = "gk-" + id;
    if (!nhapGt.has(el.id)) nhapGt.set(el.id, md);
    el.value = nhapGt.get(el.id);
    const tinhTuDong = /^gk-bg-/.test(el.id) && NOI_DUNG.test(el.id) && !KHONG_TINH.test(el.id);
    const doi = roi => {
      if (roi && dinhDang) { const v = dinhDang(el.value); if (v !== el.value) el.value = v; }
      nhapGt.set(el.id, el.value); genForm += 1; if (NOI_DUNG.test(el.id)) { soSua += 1; khoaChuaLuu(); }
      if (tinhTuDong) { datCho(); henTinh(roi ? 0 : 400); }
      if (khiDoi) khiDoi(el);
    };
    el.addEventListener("input", () => doi(false)); el.addEventListener("change", () => doi(true));
    el.addEventListener("blur", () => { if (tinhHen) henTinh(0); });
    return el;
  }
  function nhap(id, md, type = "text", khiDoi, dinhDang) { const i = node("input"); i.type = type; i.autocomplete = "off"; return o(id, i, md ?? "", khiDoi, dinhDang); }
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
  // không tính ở trình duyệt, không POST mỗi phím). Chỉ còn dùng cho lịch của Soạn; lịch BÁO GIÁ tính tự động theo máy chủ (BG-03, `tinhNgay`).
  const TU_TINH_CU = "— đã sửa: Lưu để máy chủ tính lại";
  function khoaChuaLuu() {
    if (!chuaLuu()) return;
    dsCanLuu.forEach(b => { if (b.dataset.canLuu) { b.disabled = true; b.title = LY_CHUA_LUU; } });
    capNhatNutBg();
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

  // ------------------------------------------------------------------ BG-1b · ô nhập kiểu Việt (CHỈ đổi dạng chuỗi người gõ; không tính tiền ở trình duyệt)
  // Số: `15.000`, `1.500.000,50` (dấu chấm = hàng nghìn, dấu phẩy = thập phân) → chuỗi thập phân chuẩn cho các trường typed; Ngày: dd/mm/yyyy ↔ ISO.
  const RE_SO_VN = /^(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)(?:,[0-9]{1,12})?$/;
  const nhomNghin = s => s.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  function hienSo(dec) {  // chuỗi thập phân chuẩn ("1500000.5") → kiểu Việt ("1.500.000,5"); không phải số → trả nguyên
    const m = /^(\d+)(?:\.(\d+))?$/.exec(String(dec ?? ""));
    if (!m) return dec === null || dec === undefined ? "" : String(dec);
    const le = (m[2] || "").replace(/0+$/, ""), ng = m[1].replace(/^0+(?=\d)/, "");
    return nhomNghin(ng) + (le ? "," + le : "");
  }
  const docSo = t => { const s = String(t ?? "").trim(); return RE_SO_VN.test(s) ? s.replace(/\./g, "").replace(",", ".") : null; };
  const chuanSo = t => { const d = docSo(t); return d === null ? String(t ?? "") : hienSo(d); };
  function chuanGt(t) {  // ô Giá trị thông minh: `30 %` → `30%`, `450000` → `450.000`; sai dạng → giữ nguyên để máy chủ báo
    const s = String(t ?? "").trim(); if (!s) return "";
    const pc = s.endsWith("%"), d = docSo(pc ? s.slice(0, -1) : s);
    return d === null ? s : hienSo(d) + (pc ? "%" : "");
  }
  // Thời điểm ghi (ISO/UTC) → "dd/mm/yyyy hh:mm" giờ Việt Nam (UTC+7, không có giờ mùa hè); không đọc được → giữ nguyên chuỗi
  const ngayGio = v => {
    const t = new Date(v); if (v === null || v === undefined || v === "" || isNaN(t.getTime())) return String(v ?? "");
    const d = new Date(t.getTime() + 7 * 3600000), p2 = n => String(n).padStart(2, "0");
    return `${p2(d.getUTCDate())}/${p2(d.getUTCMonth() + 1)}/${String(d.getUTCFullYear()).padStart(4, "0")} ${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}`;
  };
  // Lý do của lần in/xuất do máy chủ ghi là MÃ kỹ thuật in hoa (vd COM_MO:com_error) → câu tiếng Việt; mã lạ giữ trong ngoặc để tra cứu
  const lyDoXuat = ly => {
    const t = String(ly ?? ""); if (!t || !/^[A-Z][A-Z0-9_]*(:|$)/.test(t)) return t;
    if (/^WORD_DANG_BAN/.test(t)) return "Word đang bận — in lại sau; DOCX đã giữ.";
    if (/^(COM_|WORD_|GUARD_|KHONG_SO_HUU)/.test(t)) return "Máy này chưa dùng được Word để tạo PDF — DOCX đã giữ, PDF xuất tay.";
    return `Không tạo được PDF — DOCX đã giữ (mã: ${t}).`;
  };
  const tenNguoi = (ten, dangNhap) => s0(ten) || dangNhap;  // máy chủ có trả tên hiển thị thì dùng, chưa có thì giữ tên đăng nhập
  const hienNgay = iso => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso ?? "")); return m ? `${m[3]}/${m[2]}/${m[1]}` : ""; };
  function docNgay(t) {  // dd/mm/yyyy (hoặc yyyy-mm-dd) → ISO; ngày không tồn tại → null
    const s = String(t ?? "").trim(); let m, y, mo, d;
    if ((m = /^(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{4})$/.exec(s))) { d = +m[1]; mo = +m[2]; y = +m[3]; }
    else if ((m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s))) { y = +m[1]; mo = +m[2]; d = +m[3]; }
    else return null;
    const dt = new Date(Date.UTC(y, mo - 1, d));
    if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) return null;
    return `${String(y).padStart(4, "0")}-${String(mo).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  }
  const chuanNgay = t => { const d = docNgay(t); return d === null ? String(t ?? "") : hienNgay(d); };
  const chuanTim = s => String(s ?? "").replace(/[đĐ]/g, "d").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/\+/g, " ").replace(/\s+/g, " ").trim();
  const thoatRe = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Mốc thời gian một ô: chọn sự kiện của danh mục máy chủ (Ký · Bàn giao · Sổ · Xây xong tầng n · Sau ký + n ngày) hoặc gõ ngày dd/mm/yyyy.
  function bangMoc() {
    if (bangMocDem) return bangMocDem;
    const m = mocChuan || {moc: [], moc_tham_so: []};
    bangMocDem = {co: m.moc.map(x => ({ma: x.ma, nhan: x.nhan, k: chuanTim(x.nhan)})),
      mau: (m.moc_tham_so || []).map(p => ({nhan: p.nhan, mau_ma: p.mau_ma, min: p.toi_thieu ?? 0,
        re: new RegExp("^" + thoatRe(chuanTim(p.nhan)).replace(/(^|\s)n(?=\s|$)/, "$1(\\d{1,4})") + "$"),
        reMa: new RegExp("^" + thoatRe(p.mau_ma).replace("<n>", "(\\d+)") + "$")}))};
    return bangMocDem;
  }
  function nhanMoc(ma) {
    if (!ma) return "";
    const b = bangMoc(), c = b.co.find(x => x.ma === ma);
    if (c) return c.nhan;
    for (const p of b.mau) { const m = p.reMa.exec(ma); if (m) return p.nhan.replace(/(^|\s)n(?=\s|$)/, "$1" + String(+m[1])); }
    return "Sự kiện khác (chưa có nhãn)";
  }
  const textMoc = g => g.ml === "NGAY" ? hienNgay(g.mn) : g.ml === "SU_KIEN" ? nhanMoc(g.ms) : "";
  function docMoc(text) {  // → {moc_loai, moc_ngay, moc_su_kien}; không hiểu → null
    const t = String(text ?? "").trim();
    if (!t) return {moc_loai: null, moc_ngay: null, moc_su_kien: null};
    const ng = docNgay(t);
    if (ng) return {moc_loai: "NGAY", moc_ngay: ng, moc_su_kien: null};
    const k = chuanTim(t), b = bangMoc(), c = b.co.find(x => x.k === k);
    if (c) return {moc_loai: "SU_KIEN", moc_ngay: null, moc_su_kien: c.ma};
    for (const p of b.mau) { const m = p.re.exec(k); if (m && +m[1] >= p.min) return {moc_loai: "SU_KIEN", moc_ngay: null, moc_su_kien: p.mau_ma.replace("<n>", String(+m[1]))}; }
    return null;
  }
  const gocMoc = i => ({ml: s0(gt(`bg-l-ml-${i}`)), mn: s0(gt(`bg-l-mn-${i}`)), ms: s0(gt(`bg-l-ms-${i}`))});
  // Dòng mốc chưa sửa so với dữ liệu máy chủ → gửi lại NGUYÊN (kể cả mã sự kiện chưa có nhãn); đã sửa → đọc từ chữ người gõ.
  function mocCuaDong(i) {
    const text = (gt(`bg-l-mo-${i}`) || "").trim(), g = gocMoc(i);
    if (text && chuanTim(text) === chuanTim(textMoc(g))) return {moc: {moc_loai: g.ml, moc_ngay: g.mn, moc_su_kien: g.ms}, loi: null};
    const m = docMoc(text);
    return m ? {moc: m, loi: null} : {moc: {moc_loai: null, moc_ngay: null, moc_su_kien: null},
      loi: `Dòng ${i + 1}: chưa hiểu mốc "${text}" — chọn trong danh sách (thay n bằng số) hoặc gõ ngày dd/mm/yyyy.`};
  }
  // Lịch thanh toán báo giá: 4 cột (Lần tự đánh số · Giá trị một ô · Mốc một ô · Ghi chú). Khóa nhập theo dòng: id (mã dòng giữ qua revision), gt (chuỗi giá trị
  // người gõ), mo (chữ mốc đang hiện), ml/mn/ms (mốc gốc của máy chủ để gửi lại nguyên khi chưa sửa), gc (ghi chú).
  const COT_B = ["id", "gt", "mo", "ml", "mn", "ms", "gc"];
  function ghiLichBg(rows, tt) {  // dòng dạng máy chủ → ô nhập; trả danh sách cảnh báo nạp (không nạp giá trị mơ hồ)
    xoaNhap("bg-l-"); const canh = [];
    rows.forEach((r, i) => {
      let g = "";
      if (r.gia_tri_nhap != null) g = chuanGt(r.gia_tri_nhap);
      else if (r.loai === "PERCENT" && r.ty_le != null) g = hienSo(r.ty_le) + "%";
      else if (r.loai === "AMOUNT" && r.so_tien != null) {
        if (r.tien_te && tt && r.tien_te !== tt) canh.push(`Dòng ${i + 1}: số tiền ghi bằng ${r.tien_te} còn báo giá tính bằng ${tt} — nhập lại giá trị.`);
        else g = hienSo(r.so_tien);
      }
      const v = {id: r.dong_id || "", gt: g, ml: r.moc_loai || "", mn: r.moc_ngay || "", ms: r.moc_su_kien || "", gc: r.ghi_chu || ""};
      COT_B.forEach(c => { if (c !== "mo") nhapGt.set(`gk-bg-l-${c}-${i}`, v[c]); });
    });
    return canh;
  }
  const docLichRaw = n => Array.from({length: n}, (_, i) => { const o_ = {}; COT_B.forEach(c => { o_[c] = gt(`bg-l-${c}-${i}`); }); return o_; });
  function ghiLichRaw(rows) { xoaNhap("bg-l-"); rows.forEach((r, i) => COT_B.forEach(c => nhapGt.set(`gk-bg-l-${c}-${i}`, r[c] ?? ""))); }
  function docLichBg(n, loi) {  // dòng gửi máy chủ: chỉ chuỗi người gõ (`gia_tri_nhap`) + mốc; loại/tỷ lệ/tiền do MÁY CHỦ suy ra
    return Array.from({length: n}, (_, i) => {
      const g = c => gt(`bg-l-${c}-${i}`), mc = mocCuaDong(i);
      if (mc.loi) loi.push(mc.loi);
      return {dong_id: s0(g("id")), lan: String(i + 1), gia_tri_nhap: String(g("gt") ?? "").trim(), ...mc.moc, ghi_chu: s0(g("gc"))};
    });
  }

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
    napTyGiaMd();  // song song: dòng "Tỷ giá USD mặc định" + giá trị tường minh khi xóa trống tỷ giá đã nhập tay (cùng thế hệ vai)
    try {
      const s = await (await goi("/api/crm/bao-gia")).json();
      if (!dung()) return false;
      if (actor() !== null && s.nguoi && s.nguoi.dang_nhap !== actor()) { ep += 1; boChon(); khoaMap.clear(); nhapGt.clear(); }
      ds = s;
      xoaLoiTai();
      if (!fs()) return false;
      ve();
      return true;
    } catch (err) {
      if (!dung() || !fs()) return false;
      if (loiAnNinh(err)) { ds = null; boChon(); ve(); }
      baoLoiTai(err.message);
      return false;
    }
  }
  function nap(kind, id, gen, gan, fs0) {  // GET chi tiết theo thế hệ + lựa chọn + fence của ý định gốc; người dùng đã nhập → không đè nháp
    if (K.vaiDangChan("crm_gk")) return Promise.resolve();
    const e = ep, fs = fs0 || formCon();
    return goi(`/api/crm/${kind}/${encodeURIComponent(id)}`).then(r => r.json()).then(d => {
      if (!(e === ep && gen())) return;
      if (!fs()) return;
      gan(d); xoaLoiTai(); ve();
    }).catch(err => { if (e === ep && gen() && fs()) { if (err.status === 404 || loiAnNinh(err)) { boChon(); ve(); } baoLoiTai(err.message); } });
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
  function boChon() { bgChon = null; bgCt = null; soChon = null; soCt = null; genForm += 1; genBg += 1; genSo += 1; dongBo = soSua; resetTinh(); nhapMoi = null; buoc2Mo = null;
    kyCt = null; kyMo = null; kyTep = null; genKy += 1; }  // G4: điều kiện/dialog/tệp của HĐ cũ hết hiệu lực (ý định chưa rõ vẫn giữ trong kyYD)
  function xoa() { ep += 1; ds = null; boChon(); khoaMap.clear(); nhapGt.clear(); revDaLuu.clear(); soDongBg = 1; soDongSo = 0; if (oGuiLai) oGuiLai.replaceChildren(); ve(); trangThai(""); loiTai = null;
    fxMd = null; fxMdLoi = ""; fxMdCho = false; fxMdGen += 1; tinhChoFxMd = false; fxMdLai = 0; clearTimeout(fxMdLaiHen); fxMdLaiHen = null; Object.assign(fxMdSua, {mo: false, ty: "", ly: "", loi: "", dang: false});
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
    // BG-05: số hiện kiểu Việt (dấu chấm hàng nghìn), ngày dd/mm/yyyy; BG-04: ô Tổng giá trị = số ghi đè (hoặc tổng khai kiểu cũ), trống = máy tự tính
    set("tt", q.gia.tien_te); set("dg", hienSo(q.gia.don_gia)); set("dt", hienSo(q.gia.dien_tich));
    set("tong", q.tong_gia_tri_ghi_de != null ? chuanSo(q.tong_gia_tri_ghi_de) : hienSo(q.gia.tong));  // ghi đè lưu NGUYÊN chuỗi người gõ (kiểu Việt); tổng khai kiểu cũ là thập phân chuẩn
    set("thue", q.gia.co_so_thue); set("vat", hienSo(q.gia.vat_phan_tram));
    const fxMd = !!(q.fx && q.fx.nguon === "MAC_DINH");  // BG-1d: tỷ giá mặc định đã lưu → ô trống (nhãn "mặc định"); số đã nhập tay → hiện số
    set("fx", fxMd ? "" : hienSo(q.fx && q.fx.ty_gia)); set("fx-ngay", fxMd ? "" : hienNgay(q.fx && q.fx.ngay)); set("pbt", hienSo(q.phi_bao_tri && q.phi_bao_tri.gia_tri));
    set("pbt-tt", q.phi_bao_tri && q.phi_bao_tri.tien_te); set("pbt-cs", q.phi_bao_tri && q.phi_bao_tri.co_so); set("het", hienNgay(q.het_han)); set("gc", q.ghi_chu);
    const canh = ghiLichBg(q.lich, TIEN_LICH); soDongBg = Math.max(1, q.lich.length);
    dongBo = soSua; resetTinh(); revDaLuu.delete(d.bao_gia.id);  // form = đúng revision máy chủ
    if (canh.length) trangThai(canh.join(" "), true);
  }
  // Dữ liệu gửi máy chủ + danh sách lỗi dạng nhập phát hiện ở trình duyệt (số/ngày sai dạng: trường đó bỏ khỏi yêu cầu, Lưu bị chặn kèm câu rõ).
  // Giá trị lịch gửi NGUYÊN chuỗi người gõ (`gia_tri_nhap`); tổng ghi đè gửi nguyên chuỗi người gõ; các số còn lại đổi sang chuỗi thập phân chuẩn.
  // Ô tỷ giá TRỐNG của báo giá USD (VND không gửi tỷ giá). Máy chủ: Lưu không gửi tỷ giá ⇒ báo giá ĐÃ CÓ tỷ giá giữ tỷ giá đã lưu (kể cả nhập tay), báo giá chưa có
  // nhận mặc định chung; xem-truoc không biết tỷ giá đã lưu ⇒ luôn lấy mặc định chung. Hai đường chỉ khớp nhau khi gửi TƯỜNG MINH ở chỗ chúng khác nhau:
  //  · đã lưu là MẶC ĐỊNH, ô trống như bản đã lưu: xem trước gửi đúng tỷ giá đã lưu; Lưu gửi null (máy chủ giữ nhãn "mặc định");
  //  · đã lưu là NHẬP TAY (vd 25.500) và người dùng xóa trống = muốn dùng mặc định hiện hành: xem trước VÀ Lưu cùng gửi tỷ giá mặc định hiện hành
  //    (nguồn: GET ty-gia-mac-dinh) ⇒ Tổng hiện khi xem trước = Tổng được lưu; chưa có tỷ giá mặc định ⇒ không tính, không Lưu (báo rõ);
  //  · báo giá mới/chưa có tỷ giá: gửi null ở cả hai (cùng đọc mặc định chung trong máy chủ).
  function fxDaLuu() {  // tỷ giá của revision USD đang mở (đúng báo giá đang chọn)
    const q = bgCt && bgChon && bgChon !== "MOI" && bgCt.bao_gia && bgCt.bao_gia.id === bgChon ? bgCt.du_lieu : null;
    return q && q.gia && q.gia.tien_te === "USD" && q.fx && q.fx.ty_gia ? q.fx : null;
  }
  function docBaoGiaKem(choTinh) {
    const loi = [], g = k => s0(gt("bg-" + k)), dt = g("khach-dt");
    const so = (k, ten) => { const v = g(k); if (v === null) return null; const d = docSo(v); if (d === null) loi.push(`${ten}: nhập số kiểu 15.000 hoặc 1.500,50.`); return d; };
    const ngay = (k, ten) => { const v = g(k); if (v === null) return null; const d = docNgay(v); if (d === null) loi.push(`${ten}: nhập ngày dạng dd/mm/yyyy.`); return d; };
    const tongV = g("tong");  // máy chủ đọc kiểu Việt và báo lỗi theo trường (chan_in.truong = tong_gia_tri_ghi_de)
    const usd = g("tt") === "USD";  // VND: tỷ giá cố định 1 (ô khóa) → không gửi tỷ giá
    const fxv = usd ? so("fx", "Tỷ giá") : null, fxn = usd ? ngay("fx-ngay", "Ngày tỷ giá") : null, pbv = so("pbt", "Phí bảo trì"), het = ngay("het", "Hết hạn");
    const du = {loai_hinh_id: g("loai"), du_an_id: g("du-an"), giai_doan_g7: g("g7"), nguon_lich: g("nguon") || "KHACH",
      don_vi: {ma: g("lo"), mo_ta: g("lo-mt")}, khach: {doi_tac_id: g("khach"), du_thao: dt ? {ten: dt, lien_he: g("khach-lh")} : null},
      gia: {tien_te: g("tt"), don_gia: so("dg", "Đơn giá"), dien_tich: so("dt", "Diện tích"), tong: null, co_so_thue: g("thue"), vat_phan_tram: so("vat", "VAT")},
      fx: fxv !== null ? {cap: "USD/VND", ty_gia: fxv, ngay: fxn} : null,
      phi_bao_tri: pbv !== null ? {gia_tri: pbv, tien_te: g("pbt-tt"), co_so: g("pbt-cs")} : null,
      lich: docLichBg(soDongBg, loi), het_han: het, ghi_chu: g("gc")};
    if (tongV !== null) du.tong_gia_tri_ghi_de = tongV;
    let chuaCoFxMd = false;
    if (usd && !du.fx && fxv === null && g("fx") === null) {
      const lu = fxDaLuu();
      if (lu && lu.nguon === "MAC_DINH") { if (choTinh) du.fx = {cap: "USD/VND", ty_gia: lu.ty_gia, ngay: lu.ngay || null}; }
      else if (lu) {  // đã lưu tay, nay xóa trống → mặc định hiện hành, tường minh ở cả xem trước lẫn Lưu
        if (fxMd && fxMd.ty_gia) du.fx = {cap: "USD/VND", ty_gia: String(fxMd.ty_gia), ngay: fxMd.ap_dung_tu || null};
        else { chuaCoFxMd = true; loi.push("Tỷ giá: chưa lấy được tỷ giá mặc định hiện hành (máy đang thử lại) — thử Lưu sau ít giây, hoặc nhập tỷ giá."); }
      }
    }
    return {du, loi, chuaCoFxMd};
  }

  // ------------------------------------------------------------------ BG-03 · tính TỰ ĐỘNG theo máy chủ (không nút "Tính thử"; trình duyệt không tự tính)
  // Kết quả máy chủ đang hiện: lần trả về gần nhất của form này; chưa có thì dùng revision đã lưu (hiện mờ "…" khi đã sửa) — trừ khi vừa đổi cấu trúc
  // lịch (thêm/bớt/đổi chỗ dòng, nạp bộ chuẩn: dòng cũ không còn khớp) thì để trống tới khi máy chủ trả.
  function tinhHienTai() {
    if (tinhBg) return tinhBg.tinh;
    return tinhDungLuu && bgCt && bgChon && bgChon !== "MOI" ? bgCt.tinh : null;
  }
  function resetTinh(doiCauTruc) {
    clearTimeout(tinhHen); clearTimeout(tinhLaiHen); tinhHen = tinhLaiHen = null; tinhSeq += 1; tinhBg = null; tinhCho = false; tinhLoi = ""; tinhBay = null; tinhLai = 0;
    tinhDungLuu = !doiCauTruc;
  }
  function datCho() { tinhCho = true; tinhGen += 1; apDungTinh(); }  // tinhGen: mỗi lần người dùng sửa ô ảnh hưởng số tính; phản hồi của thế hệ cũ bị bỏ
  function henTinh(ms) {
    clearTimeout(tinhHen); tinhHen = null;
    const chay = () => { tinhHen = null; chayTinh().catch(e => { tinhCho = false; tinhLoi = (e && e.message) || "Không tính được."; apDungTinh(); }); };
    if (!ms) chay(); else tinhHen = setTimeout(chay, ms);
  }
  const DU_TRUONG_MOI = t => !!t && "ly_do_chan_in" in t && (t.dong || []).every(x => "hien_thi_mo" in x);
  async function chayTinh() {
    if (cheDo !== "bao_gia" || !bgChon || K.vaiDangChan("crm_gk")) { tinhCho = false; return; }
    if (bgChon !== "MOI" && !(bgCt && bgCt.bao_gia.id === bgChon && bgCt.bao_gia.trang_thai === "NHAP")) { tinhCho = false; apDungTinh(); return; }
    const kem = docBaoGiaKem(true), du = kem.du, khoa = JSON.stringify(du);
    if (kem.chuaCoFxMd) {  // cần tỷ giá mặc định hiện hành để xem trước KHỚP bản sẽ lưu — chưa có thì không tính (không đoán), lấy rồi tính lại
      tinhCho = false; tinhChoFxMd = true;
      if (!fxMdCho && !fxMdLaiHen) napTyGiaMd();  // đang có hẹn thử lại thì chờ hẹn (xem napTyGiaMd), không gọi lặp theo từng lần gõ
      tinhLoi = fxMdCho ? "Đang lấy tỷ giá mặc định…" : LOI_CHUA_CO_FX_MD; apDungTinh();
      return;
    }
    tinhChoFxMd = false;
    if (tinhBg && tinhBg.khoa === khoa) { tinhCho = false; tinhLoi = ""; apDungTinh(); return; }  // form đúng như lần máy chủ đã trả
    if (tinhBay && tinhBay.khoa === khoa && tinhBay.gen === tinhGen) return;  // đã có yêu cầu y hệt (cùng thế hệ sửa) đang bay
    const seq = ++tinhSeq, gen = tinhGen, id = bgChon, nm = nhapMoi, f = fence(() => bgChon === id && cheDo === "bao_gia" && (id !== "MOI" || nhapMoi === nm));
    tinhBay = {seq, khoa, gen}; tinhCho = true; apDungTinh();
    try {
      const r = await docJson(await goi("/api/crm/bao-gia/xem-truoc", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({du_lieu: du})}));
      if (seq !== tinhSeq || gen !== tinhGen || !f()) return;  // phản hồi của form đã đổi (người dùng gõ tiếp)/báo giá khác: bỏ
      tinhBg = {khoa, tinh: r.tinh, nhan: r.nhan || null, fx_ngay_hien_thi: r.fx_ngay_hien_thi || null}; tinhBay = null; tinhCho = false; tinhLoi = ""; tinhLai = 0;
      apDungTinh();
    } catch (e) {
      if (seq !== tinhSeq || gen !== tinhGen || !f()) return;
      tinhBay = null; tinhCho = false;
      const mang = !e || e.status === 0 || e.status >= 500;
      tinhLoi = mang ? "Chưa cập nhật được số tính (mất kết nối) — đang hiện kết quả lần trước, máy sẽ tự thử lại." : ((e && e.message) || "Không tính được.");
      apDungTinh();
      if (mang && tinhLai < 3) { tinhLai += 1; clearTimeout(tinhLaiHen); tinhLaiHen = setTimeout(() => { tinhLaiHen = null; henTinh(0); }, 5000); }
    }
  }
  // Lý do chặn In/Chuyển. Nút CHỈ mở khi máy chủ đã trả danh sách lý do (rỗng) cho ĐÚNG bản đang mở: form = revision đã lưu ⇒ lấy kết quả máy chủ ĐÃ LƯU của revision đó
  // (không dùng bản xem trước của form — báo giá lưu theo quy ước cũ được xem trước theo quy ước mới); thiếu trường lý do (revision cũ/chưa tính lại) = CHƯA KIỂM ⇒ mờ.
  // Còn thay đổi chưa lưu ⇒ nút mờ sẵn; lý do hiện kèm là bản xem trước của form (chỉ để thông tin).
  const CHUA_KIEM = {in: "Chưa kiểm điều kiện in", chuyen: "Chưa kiểm điều kiện chuyển"};
  function lyChanBg(loai) {
    const khoa = loai === "in" ? "ly_do_chan_in" : "ly_do_chan_chuyen";
    const luu = bgCt && bgChon && bgChon !== "MOI" && bgCt.bao_gia && bgCt.bao_gia.id === bgChon ? bgCt : null;
    const t = luu && !chuaLuu() ? luu.tinh : tinhHienTai();
    if (!t || t[khoa] === undefined || t[khoa] === null) {
      if (!luu) return "";  // báo giá mới: nút đã mờ với lý do "Lưu nháp trước"
      return CHUA_KIEM[loai] + (luu.bao_gia.trang_thai === "NHAP" ? " — bấm Lưu nháp để máy kiểm lại." : " — bản này không còn sửa/lưu lại được.");
    }
    return String(t[khoa]);
  }
  function capNhatNutBg() {  // In/Chuyển: mờ khi còn thay đổi chưa lưu HOẶC máy chủ báo chặn; lý do HIỆN cạnh nút (BG-1d) và khi rê chuột
    for (const b of dsNutBg) {
      const chua = chuaLuu(), ly = lyChanBg(b.dataset.chanBg);
      const khac = b.dataset.lyKhac || "";  // lý do riêng của nút (vd chưa có mẫu hợp đồng hiệu lực, chưa lưu nháp mới) — luôn mờ
      b.disabled = chua || !!ly || !!khac; b.title = [chua ? LY_CHUA_LUU : "", ly, khac].filter(Boolean).join("\n"); b.dataset.lyChan = ly;
      if (b._lyNut) b._lyNut.textContent = [ly.split("\n").join(" · "), khac].filter(Boolean).join(" · ");
    }
  }
  function nutLuuTruocBg(loai, text, fn, cls, lyKhac) {  // trả khối (nút + dòng lý do hiện sẵn)
    const b = nut(text, async bt => {
      if (chuaLuu()) { trangThai(LY_CHUA_LUU, true); return; }
      const ly = lyChanBg(loai); if (ly) { trangThai(ly.split("\n").join(" · "), true); return; }
      await fn(bt);
    }, cls);
    b.dataset.chanBg = loai; if (lyKhac) b.dataset.lyKhac = lyKhac;
    b._lyNut = node("span", "", "gk-ly-nut"); b._lyNut.setAttribute("role", "note");
    dsNutBg.push(b); capNhatNutBg();
    const w = node("span", undefined, "gk-nut-ly"); w.append(b, b._lyNut); return w;
  }
  function trieuVn(dec) {  // dự phòng khi máy chủ chưa trả chuỗi VND của tổng: dời dấu thập phân 6 chữ số trên CHUỖI (không float), chỉ để hiện
    const m = /^(\d+)(?:\.(\d+))?$/.exec(String(dec ?? "")); if (!m) return "";
    const a = m[1].padStart(7, "0"), le = (a.slice(-6) + (m[2] || "")).replace(/0+$/, "");
    return "≈ " + hienSo(a.slice(0, -6) + (le ? "." + le : "")) + " tr VND";
  }
  function apDungTinh() {  // cập nhật TẠI CHỖ (không vẽ lại form, không mất caret) mọi chỗ hiện kết quả của máy chủ
    const t = tinhHienTai(), cho = tinhCho;
    dsMoBg.forEach((s, i) => {
      const tx = String(gt(`bg-l-gt-${i}`) || "").trim(), x = t && t.dong && t.dong[i];
      let text = "", loiDong = false;
      if (tx && x) { const l = (x.loi_chi_tiet || [])[0]; if (l) { text = String(l.thong_bao || "").replace(/^Dòng \d+:\s*/, ""); loiDong = true; } else text = x.hien_thi_mo || ""; }
      s.textContent = cho && tx ? (text ? text + " …" : "…") : text;
      s.className = "gk-mo" + (loiDong ? " gk-loi" : "") + (cho ? " gk-cho" : "");
    });
    dsLoiMocBg.forEach(({el, i}) => { const mc = mocCuaDong(i); el.textContent = mc.loi ? mc.loi.replace(/^Dòng \d+: /, "") : ""; });
    if (oTongBg) {
      const kids = [];
      if (!t) kids.push(node("span", cho ? "Σ …" : "Σ —", "gk-tong-o"));
      else {
        const ok = !!t.tong_ty_le_khop, okT = !!t.tong_tien_khop;
        const pc = node("span", "Σ " + (t.tong_ty_le_hien_thi || "—") + (ok ? " ✓" : ""), "gk-tong-o " + (ok ? "gk-ok" : "gk-sai")); pc.dataset.tongTyLe = ok ? "khop" : "lech";
        const tien = node("span", "Σ tiền " + (t.tong_dong_hien_thi || "—") + (okT ? " = Tổng giá trị ✓" : t.tong_hien_thi ? " ≠ Tổng giá trị " + t.tong_hien_thi : " · chưa có tổng giá trị"),
          "gk-tong-o " + (okT ? "gk-ok" : "gk-sai")); tien.dataset.tongTien = okT ? "khop" : "lech";
        kids.push(pc, tien);
        const vnd = t.vnd_tong_hien_thi || (t.vnd_tham_chieu && (t.vnd_tham_chieu.tong_hien_thi || trieuVn(t.vnd_tham_chieu.tong)));
        if (vnd) kids.push(node("span", vnd, "gk-tong-o"));
        const fx = String(gt("bg-fx") || "").trim();
        if (t.tien_te === "USD" && fx) kids.push(node("span", "Tỷ giá " + fx + (tinhBg && tinhBg.fx_ngay_hien_thi ? " · " + tinhBg.fx_ngay_hien_thi : ""), "gk-tong-o"));
        if (t.ly_do_chan_in) kids.push(node("div", t.ly_do_chan_in.split("\n").join(" · "), "gk-tong-ly"));
      }
      if (cho && t) kids.push(node("span", "…", "gk-tong-o"));
      oTongBg.replaceChildren(...kids); oTongBg.className = "gk-tong-dong" + (cho ? " gk-cho" : "");
    }
    const ghiDe = String(gt("bg-tong") || "").trim();
    if (oGoiYTong) {
      const lech = t && (t.canh_bao || []).find(c => c.ma === "TONG_LECH_DON_GIA_X_DIEN_TICH");
      const sai = t && (t.chan_in || []).find(c => c.truong === "tong_gia_tri_ghi_de" && c.thong_bao);
      let text, cls = "gk-goi-y";
      if (sai) { text = sai.thong_bao; cls += " gk-loi"; }
      else if (lech) { text = lech.thong_bao; cls += " gk-canh"; }
      else text = "";  // BG-1d: tổng tự tính hiện ở khối Tổng giá trị lớn; ở đây chỉ còn cảnh báo/lỗi của ô ghi đè
      oGoiYTong.textContent = cho && text ? text + " …" : text; oGoiYTong.className = cls + (cho ? " gk-cho" : "");
    }
    if (oLuuYTong) oLuuYTong.textContent = ghiDe && t && t.tong_tinh_minor != null ? "Tổng ghi đè sẽ được kiểm lại khi ký hợp đồng" : "";
    if (oTongLon) {  // BG-1d: Tổng giá trị (tiền chính) cỡ lớn + phép tính + bằng chữ + USD tham chiếu — toàn bộ do MÁY CHỦ trả, trình duyệt chỉ hiện
      const tc = (t && t.tien_te) || "VND", kids = [node("div", `Tổng giá trị (${tc})`, "gk-tong-nhan")];
      if (t && t.tong_hien_thi) {
        kids.push(node("div", t.tong_hien_thi, "gk-tong-so"));
        if (t.phep_tinh) kids.push(node("p", t.phep_tinh, "gk-phep-tinh"));
        if (t.tong_bang_chu) kids.push(node("p", "Bằng chữ: " + t.tong_bang_chu, "gk-bang-chu"));
        if (t.usd_tham_chieu && t.usd_tham_chieu.tong_hien_thi) kids.push(node("p", "Tham chiếu: " + t.usd_tham_chieu.tong_hien_thi, "gk-tham-chieu"));
      } else kids.push(node("div", cho ? "…" : "—", "gk-tong-so gk-trong"), node("p", "Nhập đơn giá và diện tích (kèm tỷ giá nếu báo giá USD); máy tự tính Tổng giá trị.", "gk-phep-tinh"));
      oTongLon.replaceChildren(...kids); oTongLon.className = "gk-tong-lon" + (cho ? " gk-cho" : "");
    }
    if (oFx) {  // tỷ giá: VND = "1" khóa; USD = số đã sửa, hoặc tỷ giá mặc định của máy chủ (hiện sẵn, trống trong dữ liệu gửi đi)
      const tt = s0(gt("bg-tt")), daNhap = s0(gt("bg-fx")) !== null;
      let ty = t && t.ty_gia && !t.ty_gia.khoa ? t.ty_gia : null;
      if (ty && tt === "USD" && !daNhap) {  // vừa xóa trống tỷ giá đã lưu TAY: không hiện số cũ cho tới khi máy chủ tính xong theo tỷ giá mặc định cho đúng form này
        const lu = fxDaLuu();
        if (lu && lu.nguon !== "MAC_DINH" && !(tinhBg && tinhBg.khoa === JSON.stringify(docBaoGiaKem(true).du))) ty = null;
      }
      let hien;
      if (tt === "VND") { hien = "1"; oFx.disabled = true; oFx.title = "Báo giá VND: tỷ giá cố định bằng 1."; }
      else { hien = daNhap ? gt("bg-fx") : (ty ? ty.hien_thi : ""); oFx.disabled = false; oFx.title = ""; }
      if (oFx.value !== hien && !(document.activeElement === oFx && tt !== "VND")) oFx.value = hien;
      oFx.placeholder = tt === "USD" && !daNhap && !ty ? "đang lấy tỷ giá mặc định…" : "";
      if (oFxNguon) {
        oFxNguon.textContent = tt === "VND" ? "cố định = 1" : tt === "USD" ? (daNhap ? "đã sửa" : "mặc định" + (ty && ty.ngay_hien_thi ? " · " + ty.ngay_hien_thi : "")) : "";
        oFxNguon.dataset.nguon = tt === "VND" ? "co_dinh" : daNhap ? "da_sua" : "mac_dinh";
      }
      if (oFxLoi) { const e = t && (t.chan_in || []).find(x => x.truong === "fx.ty_gia" && x.thong_bao); oFxLoi.textContent = e ? e.thong_bao : ""; }
    }
    if (oKiemBg) { oKiemBg.replaceChildren(); doKiem(oKiemBg, t, null, true); }
    if (oTinhLoi) oTinhLoi.textContent = tinhLoi;
    if (oNguCanh) { const n = tinhBg && tinhBg.nhan; oNguCanh.textContent = n ? [n.phap_nhan && n.phap_nhan.ten, n.loai_hinh && n.loai_hinh.ten, n.du_an && n.du_an.ten].filter(Boolean).join(" · ") : ""; }
    capNhatNutBg();
  }
  async function napMocChuan() {
    if (mocChuan || mocChuanCho) return;
    mocChuanCho = true;
    try {
      const d = await (await goi("/api/crm/bao-gia/moc-chuan")).json();
      mocChuan = {moc: Array.isArray(d.moc) ? d.moc : [], moc_tham_so: Array.isArray(d.moc_tham_so) ? d.moc_tham_so : []};
    } catch (err) {
      mocChuanCho = false;
      if (loiAnNinh(err)) return;  // chưa có phiên: lần mở form sau sẽ thử lại
      mocChuan = {moc: [], moc_tham_so: [], loi: true};  // vẫn lập được báo giá: chỉ thiếu danh sách chọn sự kiện (gõ ngày dd/mm/yyyy được)
    }
    mocChuanCho = false; bangMocDem = null;
    if (cheDo === "bao_gia" && bgChon) ve();
  }
  // ------------------------------------------------------------------ BG-1d vòng 2 · tỷ giá USD/VND mặc định chung (QD-20261025-04)
  // Một dòng nhỏ cho MỌI vai ("Tỷ giá USD mặc định: 26.000 · cập nhật dd/mm/yyyy"); vai kế toán/kế toán trưởng có module CRM (máy chủ trả `duoc_sua`) thấy nút Sửa → tỷ giá mới +
  // LÝ DO bắt buộc → POST ty-gia-mac-dinh. Báo giá đã lưu không đổi tỷ giá (máy chủ giữ tỷ giá đã lưu). Lỗi máy chủ (vd không có quyền) hiện nguyên câu tiếng Việt.
  const LOI_CHUA_CO_FX_MD = "Chưa lấy được tỷ giá mặc định hiện hành — máy đang thử lại; có thể nhập tỷ giá thay.";
  function lamMoiTinhKhiMdDoi() {  // mặc định đổi: kết quả xem trước dựa trên mặc định cũ không còn đúng → ép máy chủ tính lại (khi đang mở báo giá sửa được)
    if (cheDo !== "bao_gia" || !bgChon) return;
    if (tinhBg) tinhBg.khoa = null;
    henTinh(0);
  }
  async function napTyGiaMd() {
    if (K.vaiDangChan("crm_gk")) return;
    const e = ep, g = ++fxMdGen; fxMdCho = true; fxMdLoi = "";
    veFxMd();
    try {
      const d = await docJson(await goi("/api/crm/bao-gia/ty-gia-mac-dinh"));
      if (e !== ep || g !== fxMdGen) return;
      const doi = !!fxMd && (String(fxMd.ty_gia) !== String(d.ty_gia) || (fxMd.ap_dung_tu || null) !== (d.ap_dung_tu || null));
      fxMd = d; fxMdCho = false; fxMdLoi = ""; fxMdLai = 0; clearTimeout(fxMdLaiHen); fxMdLaiHen = null;
      veFxMd();
      if (tinhChoFxMd) { tinhChoFxMd = false; tinhLoi = ""; henTinh(0); }
      else if (doi) lamMoiTinhKhiMdDoi();
    } catch (err) {
      if (e !== ep || g !== fxMdGen) return;
      fxMdCho = false; fxMdLoi = (err && err.message) || "không đọc được";
      if (loiAnNinh(err)) fxMd = null;  // mất quyền/phiên: không giữ giá trị cũ
      veFxMd();
      if (tinhChoFxMd) {  // phép tính đang chờ tỷ giá mặc định: thử lại tối đa 3 lần, cách 5 giây
        tinhCho = false; tinhLoi = LOI_CHUA_CO_FX_MD; apDungTinh();
        if (fxMdLai < 3) { fxMdLai += 1; clearTimeout(fxMdLaiHen); fxMdLaiHen = setTimeout(() => { fxMdLaiHen = null; if (tinhChoFxMd && !fxMdCho) napTyGiaMd(); }, 5000); }
      }
    }
  }
  function veFxMd() {
    if (!oFxMd) return;
    const kids = [];
    if (fxMd) {
      const ngay = fxMd.ap_dung_tu_hien_thi ? ` · cập nhật ${fxMd.ap_dung_tu_hien_thi}` : " · giá trị có sẵn của phần mềm, chưa ai cập nhật";
      kids.push(node("span", `Tỷ giá USD mặc định: ${fxMd.hien_thi || hienSo(fxMd.ty_gia)}${ngay}`, "gk-fxmd-chu"));
      if (fxMd.duoc_sua && !fxMdSua.mo) {
        const b = nut("Sửa", () => { Object.assign(fxMdSua, {mo: true, ty: hienSo(fxMd.ty_gia), ly: "", loi: ""}); veFxMd(); }, "link-button"); b.id = "gk-fxmd-sua"; kids.push(b);
      }
    } else {
      const sp = node("span", fxMdCho ? "Tỷ giá USD mặc định: đang tải…" : "Tỷ giá USD mặc định: chưa lấy được — bấm ↻ Làm mới.", "gk-fxmd-chu");
      if (fxMdLoi) sp.title = fxMdLoi;
      kids.push(sp);
    }
    if (fxMd && fxMd.duoc_sua && fxMdSua.mo) {
      const oN = (id, nhan, md, goiY, fn) => {
        const el = node("input"); el.type = "text"; el.autocomplete = "off"; el.id = id; el.value = md; el.placeholder = goiY; el.disabled = fxMdSua.dang;
        el.addEventListener("input", () => fn(el.value));
        const w = node("div", undefined, "gk-oc"), l = node("label", nhan); l.htmlFor = id; w.append(l, el); return w;
      };
      const loi = node("small", fxMdSua.loi, "gk-loi"); loi.setAttribute("role", "alert"); loi.id = "gk-fxmd-loi";
      const hanh = node("div", undefined, "demo-actions");
      hanh.append(nut(fxMdSua.dang ? "Đang lưu…" : "Lưu tỷ giá", luuFxMd, "button primary", fxMdSua.dang),
        nut("Bỏ qua", () => { Object.assign(fxMdSua, {mo: false, loi: ""}); veFxMd(); }, "link-button", fxMdSua.dang));
      const hop = node("div", undefined, "gk-fxmd-form");
      hop.append(oN("gk-fxmd-ty", "Tỷ giá mới (VND cho 1 USD)", fxMdSua.ty, "vd 26.000", v => { fxMdSua.ty = v; }),
        oN("gk-fxmd-ly", "Lý do đổi (bắt buộc)", fxMdSua.ly, "vd theo tỷ giá ngân hàng ngày…", v => { fxMdSua.ly = v; }), loi, hanh,
        node("small", "Chỉ áp dụng cho báo giá USD lập sau; báo giá đã lưu không đổi tỷ giá. Thay đổi được ghi nhật ký kèm lý do.", "gk-ghi-chu"));
      kids.push(hop);
    }
    oFxMd.replaceChildren(...kids);
  }
  async function luuFxMd() {
    if (fxMdSua.dang) return;
    const ty = s0(fxMdSua.ty), ly = s0(fxMdSua.ly), d = ty === null ? null : docSo(ty);
    const loi = ty === null ? "Nhập tỷ giá mới (vd 26.000 hoặc 25.950,5)." : d === null || !/[1-9]/.test(d) ? "Tỷ giá: nhập số dương kiểu 26.000 hoặc 25.950,5." : ly === null ? "Cần ghi lý do đổi tỷ giá mặc định." : "";
    if (loi) { fxMdSua.loi = loi; veFxMd(); return; }
    const e = ep; fxMdSua.dang = true; fxMdSua.loi = ""; veFxMd();
    try {
      const r = await docJson(await goi("/api/crm/bao-gia/ty-gia-mac-dinh", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ty_gia: hienSo(d), ly_do: ly})}));
      if (e !== ep) return;
      fxMdGen += 1; fxMd = r; fxMdCho = false; fxMdLoi = "";
      Object.assign(fxMdSua, {mo: false, dang: false, ty: "", ly: "", loi: ""});
      veFxMd();
      K.toast(r.da_doi === false ? "Tỷ giá mặc định không đổi (cùng giá trị đang dùng)." : "Đã cập nhật tỷ giá mặc định — báo giá đã lưu không đổi tỷ giá.");
      lamMoiTinhKhiMdDoi();
    } catch (err) {
      if (e !== ep) return;
      fxMdSua.dang = false;
      fxMdSua.loi = err && err.status === 0 ? "Mất kết nối — chưa rõ tỷ giá đã đổi hay chưa. Bấm Lưu tỷ giá lần nữa (cùng giá trị thì không ghi trùng)." : ((err && err.message) || "Không lưu được tỷ giá mặc định.");
      veFxMd();
    }
  }
  // Soạn (G3) vẫn dùng lịch cũ: phía tự tính CHỈ ĐỌC lấy từ revision đã lưu khi không có thay đổi chưa lưu.
  function tinhChoForm() {
    return !chuaLuu() && soCt ? soCt.tinh : null;
  }
  function tuTinh(t, i, loai) {
    if (!t || !t.dong || !t.dong[i]) return "— chưa có số tính (Lưu để máy chủ tính)";
    const x = t.dong[i], tt = t.tien_te, out = [];
    if (loai === "PERCENT") out.push(x.so_tien_minor != null ? `= ${minorSangChinh(x.so_tien_minor, tt)} ${tt}` : "số tiền: chưa tính được");
    if (loai === "AMOUNT") out.push(x.ty_le != null ? `= ${x.ty_le}%` : "tỷ lệ: chưa tính được/không hữu hạn");
    if (t.vnd_tham_chieu && t.vnd_tham_chieu.dong[i] != null) out.push(`VND tham chiếu ${t.vnd_tham_chieu.dong[i]}`);
    if (x.loi && x.loi.length) out.push("lỗi: " + x.loi.join(", "));
    return out.join(" · ");
  }
  // BG-01: lịch 4 cột — Lần (tự đánh số) · Giá trị (MỘT ô thông minh + phần mờ do máy chủ trả) · Mốc thời gian (MỘT ô) · Ghi chú. Mỗi dòng 3 ô nhập.
  function thayLichBg(fn) {  // đổi cấu trúc lịch (thêm/bớt/đổi chỗ dòng): dựng lại; kết quả tính cũ không còn khớp dòng → hỏi máy chủ lại
    const r = docLichRaw(soDongBg); fn(r); ghiLichRaw(r); soDongBg = Math.max(1, r.length); genForm += 1; soSua += 1; resetTinh(true); ve();
  }
  function veLichBg(n) {
    const dl = node("datalist"); dl.id = "gk-bg-moc-ds";
    const m = mocChuan || {moc: [], moc_tham_so: []};
    [...m.moc.map(x => x.nhan), ...m.moc_tham_so.map(x => x.nhan)].forEach(v => { const op = node("option"); op.value = v; dl.append(op); });
    const dinhDangMoc = i => v => {
      const t = String(v ?? "").trim(); if (!t) return "";
      const g = gocMoc(i); if (chuanTim(t) === chuanTim(textMoc(g))) return textMoc(g);
      const mc = docMoc(t); return mc ? textMoc({ml: mc.moc_loai, mn: mc.moc_ngay, ms: mc.moc_su_kien}) : t;
    };
    const rows = Array.from({length: n}, (_, i) => {
      const lan = node("span", String(i + 1), "gk-lan");
      const gtI = nhap(`bg-l-gt-${i}`, "", "text", null, chuanGt), mo = node("span", "", "gk-mo"); dsMoBg.push(mo);
      gtI.placeholder = "30% hoặc 450.000"; gtI.setAttribute("aria-label", `Dòng ${i + 1}: giá trị`);
      const cG = node("div", undefined, "gk-gt"); cG.append(gtI, mo);
      const mcI = nhap(`bg-l-mo-${i}`, textMoc(gocMoc(i)), "text", null, dinhDangMoc(i)), lm = node("small", "", "gk-loi"); dsLoiMocBg.push({el: lm, i});
      mcI.setAttribute("list", "gk-bg-moc-ds"); mcI.placeholder = "Ký, Bàn giao… hoặc dd/mm/yyyy"; mcI.setAttribute("aria-label", `Dòng ${i + 1}: mốc thời gian`);
      const cM = node("div"); cM.append(mcI, lm);
      const gcI = nhap(`bg-l-gc-${i}`, ""); gcI.setAttribute("aria-label", `Dòng ${i + 1}: ghi chú`);
      const hanh = node("div", undefined, "gk-hanh");
      const len = nut("↑", () => thayLichBg(r => { [r[i - 1], r[i]] = [r[i], r[i - 1]]; }), "link-button", i === 0), xuong = nut("↓", () => thayLichBg(r => { [r[i + 1], r[i]] = [r[i], r[i + 1]]; }), "link-button", i === n - 1);
      len.title = "Đưa lên"; xuong.title = "Đưa xuống";
      hanh.append(len, xuong, nut("Bỏ", () => thayLichBg(r => { r.splice(i, 1); }), "link-button", n <= 1));
      return [lan, cG, cM, gcI, hanh];
    });
    const tb = bang(["Lần", "Giá trị", "Mốc thời gian", "Ghi chú", ""], rows); tb.className += " gk-lich";
    return [dl, tb, nut("+ Dòng", () => thayLichBg(r => { r.push({}); }), "link-button")];
  }
  function veLich(p, n, setN) {
    if (p === "bg-") return veLichBg(n);
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
  // `song` = báo giá (BG-03): cập nhật tại chỗ theo kết quả tự động của máy chủ, không nhãn "revision đã lưu"; Soạn dùng revision đã lưu như cũ.
  const NHAN_MA = {THIEU_TIEN_TE: "Chưa chọn tiền tệ báo giá.", THIEU_TONG_GIA_TRI: "Chưa có tổng giá trị báo giá.", THIEU_KHACH: "Chưa nhập khách hàng.",
    THIEU_LICH: "Chưa nhập lịch thanh toán.", THIEU_CO_SO_THUE: "Chưa chọn cơ sở thuế.", THIEU_LO_CAN: "Chưa nhập lô/căn."};
  const BUOC2_MA = new Set(["THIEU_KHACH", "KHACH_CHUA_MA", "THIEU_PHI_QUAN_LY_BAO_TRI"]);  // mã thuộc bước 2 (khách, phí quản lý/bảo trì)
  function doKiem(w, t, them, song) {
    if (!t) { w.append(node("p", song ? "Chưa có kết quả kiểm." : "Chưa có kết quả kiểm — lưu nháp để máy chủ tính.")); return; }
    const muc = (tieuDe, arr, cls) => { if (!arr || !arr.length) return; w.append(node("h4", tieuDe)); const ul = node("ul", undefined, cls);
      arr.forEach(x => { const li = node("li", x.thong_bao || NHAN_MA[x.ma] || "Còn thiếu thông tin cần nhập."); if (them && x.truong) li.append(" ", nut("→", () => them(x.truong), "link-button")); ul.append(li); }); w.append(ul); };
    if (!song) {
      const tong = node("p", (chuaLuu() ? "[Revision đã lưu — form có thay đổi chưa lưu] " : "")
        + `Tổng giá trị: ${t.tong_hien_thi || (t.tong_minor !== null && t.tong_minor !== undefined ? t.tong_minor + " " + (t.tien_te || "") + " (đơn vị nhỏ nhất)" : "chưa tính được")} · tổng tỷ lệ: ${t.tong_ty_le_hien_thi || ((t.tong_ty_le ?? "—") + "%")}`
        + (t.vnd_tham_chieu ? ` · VND tham chiếu: ${t.vnd_tham_chieu.tong ?? "—"}` : ""));
      tong.dataset.kiemTong = "1"; dsKiemTong.push(tong); w.append(tong);
    }
    // BG-1d: bước 1 (báo giá sơ bộ) KHÔNG nhắc khách/phí — việc của bước 2, hiện bên nút "Chuyển sang soạn hợp đồng"
    const loc = arr => song ? (arr || []).filter(x => !BUOC2_MA.has(x.ma)) : arr;
    muc(song ? "Cần xử lý trước khi in sơ bộ" : "Chặn In/Xuất", loc(t.chan_in || t.chan_xuat), "gk-chan"); muc("Thiếu (vẫn lưu được)", loc(t.thieu), ""); muc("Cảnh báo", loc(t.canh_bao), "gk-canh-bao");
  }
  function veKiem(t, them) {  // danh sách thiếu/cảnh báo/chặn do MÁY CHỦ tính trên revision đã lưu
    const w = node("div", undefined, "gk-kiem"); doKiem(w, t, them, false); return w;
  }

  // ------------------------------------------------------------------ vẽ
  function ve() {
    if (!oNoiDung) dungKhung();
    dsCanLuu = []; dsLyDo = []; dsTuTinh = []; dsKiemTong = [];
    dsMoBg = []; dsLoiMocBg = []; dsNutBg = []; oTongBg = oGoiYTong = oLuuYTong = oKiemBg = oTinhLoi = oNguCanh = oTongNhap = oFx = oFxNguon = oFxLoi = oTongLon = oFxMd = null;
    $("gk-vai").textContent = ds ? `Vai hiện hành: ${tenNguoi(ds.nguoi.ten_hien_thi, ds.nguoi.dang_nhap)} (${VAI_VN[ds.nguoi.vai_tro] || ds.nguoi.vai_tro})` : "Đang tải…";
    oNoiDung.replaceChildren(...(cheDo === "bao_gia" ? veBg() : veSo()));
  }
  function dungKhung() {
    const head = node("div", undefined, "section-heading"), td = node("div"), h2 = node("h2", "6 · Báo giá → Soạn hợp đồng từ mẫu"); h2.id = "crm-gk-title";
    const vai = node("p", "Đang tải…"); vai.id = "gk-vai";
    td.append(h2, node("p", "Lập báo giá (số tính tự động, in cho khách) rồi chuyển sang soạn hợp đồng từ mẫu đã duyệt. Không sinh nghĩa vụ/công nợ."), vai);
    head.append(td, nut("↻ Làm mới", () => napLai(), "button secondary"));
    const tabs = node("div", undefined, "demo-actions");
    tabs.append(nut("Báo giá", () => { cheDo = "bao_gia"; genForm += 1; ve(); }, "button secondary"), nut("Soạn hợp đồng", () => { cheDo = "soan"; genForm += 1; ve(); }, "button secondary"));
    oTrangThai = node("p", "", "upload-status"); oTrangThai.setAttribute("role", "status"); oTrangThai.setAttribute("aria-live", "polite");
    oGuiLai = node("div", undefined, "demo-actions"); oNoiDung = node("div");
    goc.replaceChildren(head, tabs, oTrangThai, oGuiLai, oNoiDung);
  }
  function veBg() {
    if (!ds) return [K.empty("Chưa tải báo giá", "Bấm ↻ Làm mới; cần kho DEMO PostgreSQL đã chuẩn bị.")];
    const out = [];
    if (!ds.ghi_nguon.san_sang) out.push(node("p", "Chưa cấu hình kết nối máy chủ (chủ CSDL) — lưu/in/chuyển sẽ báo chưa sẵn sàng.", "upload-status error"));
    oFxMd = node("div", undefined, "gk-fxmd"); out.push(oFxMd); veFxMd();  // tỷ giá USD mặc định (mọi vai; Sửa chỉ khi máy chủ cho phép)
    out.push(node("h3", "Danh sách báo giá"), ds.bao_gia.length ? bang(["Số", "Ngày", "Khách", "Lô/căn", "Giá trị", "Trạng thái", "Người lập", ""], ds.bao_gia.map(b => [
      b.so_bao_gia, b.ngay_hien_thi || hienNgay(b.ngay) || b.ngay, b.khach || "—", b.lo_can || "—", b.tong_hien_thi || "chưa tính được", TT_BG[b.trang_thai] || b.trang_thai, tenNguoi(b.tao_boi_ten, b.tao_boi),
      nut(bgChon === b.id ? "Đang mở" : "Mở", () => { boChon(); bgChon = b.id; ve(); napBgCt(); }, "link-button", bgChon === b.id)])) : K.empty("Chưa có báo giá trong phạm vi vai này", ""));
    out.push(nut("+ Báo giá mới", () => { boChon(); xoaNhap("bg-"); soDongBg = 1; bgChon = "MOI"; nhapMoi = {so: ++soNhapMoi, tao: null}; dongBo = soSua; resetTinh(); ve(); },
      "button primary"));
    if (bgChon) out.push(...veBgEditor());
    return out;
  }
  // BG-1d (QD-20261025-01…04, nhận xét cổng A): editor báo giá 2 BƯỚC.
  //  Bước 1 "Giá và lịch thanh toán" (khối to, đặt đầu, mở sẵn): pháp nhân/dự án/lô, tiền tệ, đơn giá, diện tích, tỷ giá (USD: mặc định của máy chủ + nguồn; VND: 1 khóa),
  //    Tổng giá trị VND cỡ lớn + phép tính + bằng chữ + USD tham chiếu, lịch thanh toán (VND). Nút "In báo giá sơ bộ" chỉ chịu `ly_do_chan_in` (không đòi khách/phí).
  //  Bước 2 "Sau khi khách đồng ý" (gấp/mở, đặt sau): khách hàng, liên hệ, phí quản lý/bảo trì, hạn, ghi chú. Nút "Chuyển sang soạn hợp đồng" chịu `ly_do_chan_chuyen`.
  // Trình duyệt KHÔNG tính tiền: mọi số/chữ ở khối Tổng giá trị là kết quả của máy chủ (xem-truoc); chỉ đổi chỗ hiển thị.
  function veBgEditor() {
    if (!mocChuan) { napMocChuan(); return [node("p", "Đang tải…")]; }
    if (bgChon !== "MOI" && (!bgCt || bgCt.bao_gia.id !== bgChon)) return [node("p", "Đang tải báo giá…")];
    const b = bgCt && bgChon !== "MOI" ? bgCt.bao_gia : null, sua = !b || b.trang_thai === "NHAP";
    const nm0 = b ? null : nhapMoi;  // FIX03 R1: nháp mới nào đang vẽ (MOI → MOI sau "+ Báo giá mới" là nháp KHÁC → fence cũ sai)
    const f = fence(() => bgChon === (b ? b.id : "MOI") && cheDo === "bao_gia" && (!!b || nhapMoi === nm0));
    // BG-05: pháp nhân/loại hình/dự án/khách hiện TÊN (không mã kỹ thuật); số kiểu Việt (dấu chấm hàng nghìn); ngày dd/mm/yyyy
    const loai = ds.loai_hinh.map(l => [l.id, `${l.phap_nhan_ten || l.phap_nhan} · ${l.ten || l.ma}`]);
    // ô có nhãn trên đầu (lưới gọn); `forId` = ô thật mà nhãn trỏ tới khi `el` là khối bọc
    const oc = (label, el, bat, forId) => { const w = node("div", undefined, "gk-oc"), l = node("label", label + (bat ? " *" : "")); l.htmlFor = forId || el.id; w.append(l, el); return w; };
    const ngayIn = (id, md) => { const e = nhap(id, md, "text", null, chuanNgay); e.placeholder = "dd/mm/yyyy"; return e; };
    oNguCanh = node("p", "", "gk-ngu-canh");
    oTongNhap = nhap("bg-tong", "", "text", null, chuanSo); oTongNhap.placeholder = "Để trống: máy tự tính";
    oGoiYTong = node("small", "", "gk-goi-y"); oLuuYTong = node("small", "", "gk-luu-y");
    const cTong = node("div", undefined, "gk-tong-khoi"); cTong.append(oTongNhap, oGoiYTong, oLuuYTong);
    // tỷ giá: USD = ô sửa được (trống = dùng tỷ giá mặc định của máy chủ, hiện sẵn + nguồn); VND = "1" khóa. Người sửa → state mới; ngày tỷ giá cũ bỏ (máy chủ ghi ngày nhập).
    oFx = nhap("bg-fx", "", "text", () => nhapGt.set("gk-bg-fx-ngay", ""), chuanSo);
    oFxNguon = node("small", "", "gk-fx-nguon"); oFxLoi = node("small", "", "gk-loi");
    const cFx = node("div", undefined, "gk-fx-hop"); cFx.append(oFx, oFxNguon, oFxLoi);
    oTongLon = node("div", undefined, "gk-tong-lon"); oTongLon.setAttribute("aria-live", "polite");
    oTongBg = node("div", undefined, "gk-tong-dong"); oTinhLoi = node("p", "", "gk-tinh-loi"); oTinhLoi.setAttribute("aria-live", "polite"); oKiemBg = node("div", undefined, "gk-kiem");
    const cu = bgCt && bgChon !== "MOI" && bgCt.quy_uoc && bgCt.quy_uoc.ma !== "VND_CHINH" ? bgCt : null;  // báo giá lưu theo quy ước cũ (tiền chính = tiền tệ báo giá)
    const g7Duan = s0(gt("bg-nguon")) === "DU_AN";

    // ---- lệnh Lưu (dùng chung ở hai bước)
    const luuNhap = async () => {
      // BG-05: số/ngày sai dạng phát hiện ở trình duyệt → không gửi, nói rõ ô nào (máy không tự sửa hộ)
      const kem = docBaoGiaKem();
      if (kem.loi.length) { trangThai(kem.loi[0] + (kem.loi.length > 1 ? ` (và ${kem.loi.length - 1} chỗ khác)` : ""), true); return; }
      // FIX02 #2 + FIX03 R1: báo giá MỚI do một lần lưu trước của CHÍNH nháp này tạo (người dùng gõ tiếp trong lúc chờ) → lần lưu sau là revision của
      // đúng báo giá đó. Định danh lấy từ `nm` của nháp đang vẽ — nháp mới khác (sau "+ Báo giá mới") không bao giờ nhận ID/revision này.
      const nm = nm0;
      if (nm && !nm.tao && nm.choTao && nm.choTao.lai && khoaMap.has(nm.choTao.lai.k)) {  // lần TẠO trước của nháp này chưa rõ → không tạo bản thứ hai
        trangThai("Lần tạo báo giá trước của nháp này chưa rõ kết quả — bấm Gửi lại/Đối soát y nguyên lần đó trước (không tạo báo giá thứ hai).", true);
        veGuiLai(nm.choTao.lai);
        return;
      }
      const id = b ? b.id : (nm && nm.tao ? nm.tao.id : null);
      const body = {bao_gia_id: id, expected_revision: id ? (revDaLuu.get(id) ?? (b ? b.revision_hien_hanh : nm.tao.revision)) : null, du_lieu: kem.du};
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
    };
    const nutLuu = () => nut("Lưu nháp", luuNhap, "button primary");
    const LY_LUU_TRUOC = "Lưu nháp trước — In và Chuyển dùng bản đã lưu.";

    // ---- BƯỚC 1 · Giá và lịch thanh toán
    const b1 = node("section", undefined, "gk-buoc gk-buoc1"), dau = node("div", undefined, "gk-buoc-dau");
    dau.append(node("h4", "Bước 1 · Giá và lịch thanh toán"), node("span", b ? `${b.so_bao_gia} · bản ${b.revision_hien_hanh} · ${TT_BG[b.trang_thai]}` : "Báo giá mới", "gk-buoc-so"));
    b1.append(dau, oNguCanh);
    if (cu) b1.append(node("p", cu.quy_uoc.ghi_chu, "gk-quy-uoc"));
    const l1 = node("div", undefined, "gk-luoi"), l2 = node("div", undefined, "gk-luoi gk-luoi-gia"), l3 = node("div", undefined, "gk-luoi");
    l1.append(oc("Pháp nhân · loại hình", chon("bg-loai", loai, loai.length ? loai[0][0] : "", undefined), true),
      oc("Dự án", chon("bg-du-an", ds.du_an.map(a => [a.id, a.ten || a.ma_junsky]), "", "— chưa chọn —")), oc("Lô/căn", nhap("bg-lo", ""), true));
    l2.append(oc("Tiền tệ", chon("bg-tt", [["VND", "VND"], ["USD", "USD"]], "VND"), true), oc("Đơn giá (/m²)", nhap("bg-dg", "", "text", null, chuanSo)),
      oc("Diện tích (m²)", nhap("bg-dt", "", "text", null, chuanSo)), oc("Tỷ giá USD → VND", cFx, false, oFx.id));
    l3.append(oc("Cơ sở thuế", chon("bg-thue", [["NET", "Chưa gồm VAT"], ["GROSS", "Đã gồm VAT"]], "", "— chưa chọn —"), true), oc("VAT %", nhap("bg-vat", "", "text", null, chuanSo)),
      oc("Ghi đè Tổng giá trị (VND, không bắt buộc)", cTong, false, oTongNhap.id));
    b1.append(l1, l2, oTongLon, l3);
    const lichDau = node("div", undefined, "gk-lich-dau");
    lichDau.append(node("h4", `Lịch thanh toán (${cu ? (cu.du_lieu.gia.tien_te || "tiền tệ báo giá") : "VND"})`), oc("Nguồn lịch", chon("bg-nguon", [["KHACH", "Theo khách (nhập tay)"], ["DU_AN", "Theo bộ chuẩn của dự án"]], "KHACH", undefined, () => ve())));  // hiện/ẩn nút nạp bộ chuẩn
    if (g7Duan) lichDau.append(oc("Giai đoạn bộ chuẩn", nhap("bg-g7", "")), nut("Nạp bộ chuẩn dự án vào lịch", () => napG7(f), "button secondary"));
    b1.append(lichDau, ...veLich("bg-", soDongBg), oTongBg, oTinhLoi, oKiemBg);
    const hd1 = node("div", undefined, "demo-actions gk-hanh-dong");
    if (sua) hd1.append(nutLuu());
    // FIX01 #3 + BG-02: In/Chuyển dùng REVISION ĐÃ LƯU — mờ khi còn thay đổi chưa lưu HOẶC máy chủ báo chặn; lý do HIỆN cạnh nút (và khi rê chuột)
    if (b && b.trang_thai !== "HUY") hd1.append(oLyDo(chuaLuu() ? LY_CHUA_LUU : ""));
    if (!b || b.trang_thai !== "HUY") hd1.append(nutLuuTruocBg("in", "In báo giá sơ bộ (PDF)", async () => {
      await gui("bao-gia/in", {bao_gia_id: b.id, expected_revision: b.revision_hien_hanh}, "", f, async (r, fv) => {
        if (!fv()) return;
        trangThai(`In: ${TT_XUAT[r.trang_thai] || r.trang_thai}${r.lap_lai ? " (biên nhận cũ)" : ""}`, r.trang_thai !== "PDF_DAT");
        await napBgCt(fv);
      });
    }, "button secondary", b ? "" : LY_LUU_TRUOC));
    b1.append(hd1);

    // ---- BƯỚC 2 · Sau khi khách đồng ý
    const b2 = node("details", undefined, "gk-buoc gk-buoc2");
    const coDuLieuB2 = !!(s0(gt("bg-khach")) || s0(gt("bg-khach-dt")) || s0(gt("bg-pbt")));
    b2.open = buoc2Mo === null ? coDuLieuB2 : buoc2Mo;
    b2.addEventListener("toggle", () => { buoc2Mo = !!b2.open; });
    b2.append(node("summary", "Bước 2 · Sau khi khách đồng ý — khách hàng, phí quản lý/bảo trì, chuyển sang soạn hợp đồng"),
      node("p", "Điền sau khi khách đồng ý giá. In báo giá sơ bộ (bước 1) không cần các thông tin này; Chuyển sang soạn hợp đồng cần.", "gk-ghi-chu"));
    const l4 = node("div", undefined, "gk-luoi");
    l4.append(oc("Khách hàng (đã có mã)", chon("bg-khach", ds.khach.map(k => [k.id, k.ten]), "", "— khách dự thảo —")), oc("Tên khách dự thảo (chưa mã)", nhap("bg-khach-dt", "")),
      oc("Liên hệ", nhap("bg-khach-lh", "")), oc("Phí quản lý/bảo trì", nhap("bg-pbt", "", "text", null, chuanSo)),
      oc("Tiền tệ phí", chon("bg-pbt-tt", [["VND", "VND"], ["USD", "USD"]], "", "—")), oc("Cơ sở phí", nhap("bg-pbt-cs", "")),
      oc("Hết hạn (nếu khai)", ngayIn("bg-het", "")), oc("Mô tả lô/căn", nhap("bg-lo-mt", "")), oc("Ghi chú", nhap("bg-gc", "")));
    b2.append(l4);
    const hd2 = node("div", undefined, "demo-actions gk-hanh-dong");
    if (sua) hd2.append(nutLuu());
    if (!b || b.trang_thai === "NHAP") {
      const mau = b ? (bgCt.mau_hieu_luc || []).map(m => [m.mau_phien_ban_id, `${m.ma_mau} v${m.phien_ban} (hiệu lực ${hienNgay(m.valid_from) || m.valid_from})`]) : [];
      const chuyenFn = async () => {
        await gui("bao-gia/chuyen", {bao_gia_id: b.id, expected_revision: b.revision_hien_hanh, mau_phien_ban_id: gt(`bg-mau-${b.id}`, mau[0][0])}, "Đã chuyển sang Soạn", f,
          async (r, fv) => {
            // FIX02 #2: người dùng đã gõ trên cùng báo giá trong lúc Chuyển còn chờ → KHÔNG đổi chế độ/lựa chọn, không GET đè nháp, không thông báo cũ
            if (!fv()) return;
            cheDo = "soan"; boChon(); soChon = r.soan_id;
            const f2 = fenceForm(fence(() => soChon === r.soan_id && cheDo === "soan"));  // chụp NGAY sau chuyển trạng thái do chính lệnh này
            if (await napDs(f2) && f2()) await napSoCt(f2);
          });
      };
      if (b && mau.length) hd2.append(oc("Mẫu hợp đồng hiệu lực", chon(`bg-mau-${b.id}`, mau, mau[0][0])), nutLuuTruocBg("chuyen", "Chuyển sang soạn hợp đồng", chuyenFn, "button primary"));
      else  // vẫn hiện nút (mờ kèm lý do) để người dùng thấy bước tiếp theo và vì sao chưa làm được
        hd2.append(nutLuuTruocBg("chuyen", "Chuyển sang soạn hợp đồng", async () => {}, "button primary",
          b ? "Chưa có mẫu hợp đồng hiệu lực cho loại hình này — chưa chuyển được." : LY_LUU_TRUOC));
    }
    if (b && b.trang_thai === "NHAP") hd2.append(oc("Lý do hủy", nhap(`bg-huy-${b.id}`, "")), nut("Hủy nháp", async () => {
      const ly = s0(gt(`bg-huy-${b.id}`)); if (!ly) { trangThai("Hủy cần lý do.", true); return; }
      await gui("bao-gia/huy", {bao_gia_id: b.id, expected_revision: b.revision_hien_hanh, ly_do: ly}, "Đã hủy nháp (lịch sử giữ)", f,
        async (r, fv) => { if (fv()) await napLai(fv); });
    }, "button secondary"));
    if (b && b.trang_thai === "DA_CHUYEN" && bgCt.soan_id) hd2.append(nut("Mở bản soạn", () => { cheDo = "soan"; const s = bgCt.soan_id; boChon(); soChon = s; ve(); napSoCt(); }, "button secondary"));
    b2.append(hd2);

    const out = [b1, b2];
    if (bgCt && bgChon !== "MOI" && bgCt.xuat.length) out.push(node("h4", "Lần in"), bang(["Bản", "Trạng thái", "Lý do", "Lúc", "", ""], bgCt.xuat.map(x => [x.revision,
      TT_XUAT[x.trang_thai] || x.trang_thai, lyDoXuat(x.ly_do), ngayGio(x.tao_luc), nut("DOCX ↓", () => taiTep(x.id, "docx"), "link-button"),
      x.trang_thai === "PDF_DAT" ? nut("PDF ↓", () => taiTep(x.id, "pdf"), "link-button") : ""])));
    apDungTinh();
    // Form chưa có kết quả máy chủ khớp (vừa dựng lại sau thêm/bớt dòng, hoặc revision cũ thiếu trường hiển thị) → hỏi máy chủ, không cần nút
    if (sua && !tinhBg && !tinhBay && !tinhHen && (b ? (!DU_TRUONG_MOI(bgCt.tinh) || chuaLuu()) : chuaLuu())) Promise.resolve().then(() => henTinh(0));
    return out;
  }
  async function napG7(f) {  // bộ chuẩn THẬT đọc qua route G7 hiện có; máy chủ chụp lại khi lưu để so lệch
    const q = {du_an_id: s0(gt("bg-du-an")), giai_doan: s0(gt("bg-g7"))}, gf = genForm;
    if (!q.du_an_id || !q.giai_doan) { trangThai("Chọn dự án và nhập giai đoạn bộ chuẩn.", true); return; }
    try {
      const d = await (await goi("/api/crm/bo-chuan?" + new URLSearchParams(q).toString())).json();
      if (!f() || gf !== genForm) return;  // FIX02 #2: kết quả/lỗi của lần nạp cũ không áp lên form đã đổi
      if (d.trang_thai !== "HIEU_LUC") { trangThai("Chưa có bộ chuẩn hiệu lực — không giả khớp; nhập lịch theo khách.", true); return; }
      // FIX01 #2 + BG-01 + BG-1d vòng 2: giữ thứ tự/mốc/ghi chú; tiền đổi từ số nguyên nhỏ nhất sang chữ chính xác. Lịch không còn ô tiền tệ từng dòng và máy chủ hiểu mọi số
      // trong lịch bằng TIỀN CỦA LỊCH (VND — tiền chính, kể cả khi đơn giá USD) ⇒ đợt TIỀN của bộ chuẩn phải bằng VND; khác tiền tệ/dữ liệu hỏng → KHÔNG nạp và lịch giữ nguyên
      // (không bao giờ bỏ đơn vị rồi gửi số trần: 100 USD thành 100 VND). Đợt theo % nạp bình thường.
      const rows = [];
      for (const r of d.rows) {
        if (r.gia_tri_loai === "AMOUNT") {
          if (r.tien_te !== TIEN_LICH) { trangThai(`Đợt ${r.lan}: bộ chuẩn tính bằng ${r.tien_te || "tiền tệ chưa rõ"} còn lịch thanh toán tính bằng ${TIEN_LICH} — không nạp (máy không tự đổi tiền); nhập lịch theo khách hoặc nhờ kế toán lập lại bộ chuẩn bằng ${TIEN_LICH}; lịch giữ nguyên.`, true); return; }
          const st = minorSangChinh(r.so_tien_minor, TIEN_LICH);
          if (st === null) { trangThai(`Đợt ${r.lan}: số tiền bộ chuẩn không đọc được chính xác — không nạp, lịch giữ nguyên.`, true); return; }
          rows.push({lan: r.lan, loai: "AMOUNT", ty_le: null, so_tien: st, tien_te: TIEN_LICH, moc_loai: r.moc_loai, moc_ngay: r.moc_ngay, moc_su_kien: r.moc_su_kien, ghi_chu: r.ghi_chu});
        } else rows.push({lan: r.lan, loai: r.gia_tri_loai, ty_le: r.gia_tri_thap_phan, so_tien: null, tien_te: null, moc_loai: r.moc_loai, moc_ngay: r.moc_ngay,
          moc_su_kien: r.moc_su_kien, ghi_chu: r.ghi_chu});
      }
      ghiLichBg(rows, TIEN_LICH);
      soDongBg = Math.max(1, rows.length); genForm += 1; soSua += 1; resetTinh(true); ve(); trangThai(`Đã nạp bộ chuẩn v${d.version.phien_ban} — có thể sửa (sẽ so lệch khi lưu).`);
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
        lyDoXuat(x.ly_do), ngayGio(x.tao_luc), nut("DOCX ↓", () => taiTep(x.id, "docx"), "link-button"), x.trang_thai === "PDF_DAT" ? nut("PDF ↓", () => taiTep(x.id, "pdf"), "link-button") : ""])));
      if (soCt.revisions.length) out.push(node("h4", "Lịch sử revision"), bang(["Rev", "Mẫu", "Lý do", "Bởi", "Lúc"], soCt.revisions.map(r => [r.revision, r.mau_phien_ban_id === soCt.mau.mau_phien_ban_id ? "mẫu hiện ghim" : "mẫu khác", r.ly_do || "", r.tao_boi, ngayGio(r.tao_luc)])));
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
      lyDoXuat(x.ly_do), ngayGio(x.tao_luc), nut("DOCX ↓", () => taiTep(x.id, "docx"), "link-button"), x.trang_thai === "PDF_DAT" ? nut("PDF ↓", () => taiTep(x.id, "pdf"), "link-button") : ""])));
    if (soCt.revisions.length) out.push(node("h4", "Lịch sử revision"), bang(["Rev", "Mẫu", "Lý do", "Bởi", "Lúc"], soCt.revisions.map(r => [r.revision, r.mau_phien_ban_id === soCt.mau.mau_phien_ban_id ? "mẫu hiện ghim" : "mẫu khác", r.ly_do || "", r.tao_boi, ngayGio(r.tao_luc)])));
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
