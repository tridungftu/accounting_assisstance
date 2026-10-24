"use strict";
// M4-02A — màn Review L1/L2 trong tab "Review" của Cổng hồ sơ M4. Bố cục/cột/bộ lọc/ghép tay/chạy lại/lịch sử lấy từ màn Review nguồn
// `review_goc/giao_dien/checks.js` (cheDo 173, paymentForm 178, scope 194, summary 199, findingsTable 204, checksGrid 220, lop2Grid 232, hangMuc 254,
// traceTree 311, historyPanel 361, exportButtons 372, evidence 440, handleCheckAction 448) + helper `ui.js`/`api.js` (badge, money, num, fmtDate).
// Thích nghi DUY NHẤT phần nối: chuỗi HTML nguồn → dựng DOM (textContent, không innerHTML); API nguồn (/api/hop_dong, X-HD, /api/kiem_tra, việc RAM)
// → route hiện hành /api/m4/review (token X-KTT-Token + cookie phiên); HĐ/đợt/tệp lấy từ ngữ cảnh shell M4 + ID máy chủ, không tự chọn HĐ đầu danh sách;
// thêm cột "Trạng thái kiểm" (coverage companion) cạnh kết quả nguồn. KHÔNG có nút "Nạp đợt đã duyệt" của nguồn (đó là nhập/thay dữ liệu cũ, không phải
// Nộp/duyệt M4). Đổi vai qua cổng chung window.kttChung (người tham gia "m4_review"); fence epoch/vai/HĐ/đợt/tệp/lần chạy/form/thế hệ GET sau MỌI await.
// Nút nguồn "Mở BOQ hiệu lực"/"Xem phụ lục" (checks.js 444) → "Xem BOQ căn cứ"/"Xem phụ lục căn cứ": chỉ đọc artifact BASIS bất biến của lần chạy (docCanCu).
(() => {
  const K = window.kttChung;
  if (!K) return;
  const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || "";
  // ------------------------------------------------------------------ helper nguồn (ui.js / api.js) — giữ định dạng
  const nf0 = new Intl.NumberFormat("vi-VN", {maximumFractionDigits: 0}), nf3 = new Intl.NumberFormat("vi-VN", {maximumFractionDigits: 3});
  const money = v => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? "—" : nf0.format(Math.round(Number(v))));
  const num = v => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? "—" : nf3.format(Number(v)));
  const fmtDate = iso => { if (!iso) return "—"; const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? `${m[3]}/${m[2]}/${m[1]}` : String(iso); };
  function el(tag, props, ...con) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === "class") e.className = v; else if (k === "text") e.textContent = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (k === "value") e.value = v; else e.setAttribute(k, v === true ? "" : String(v));
    }
    for (const c of con.flat()) if (c !== null && c !== undefined && c !== false) e.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return e;
  }
  const KIND = {success: "m4-du", warning: "m4-thieu", danger: "m4-loi", neutral: "m4-xam", info: "m4-xam"};
  const MARK = {success: "✓", warning: "!", danger: "!", info: "•", neutral: "–"};
  const badge = (label, kind = "neutral") => el("span", {class: "m4-pill " + (KIND[kind] || "m4-xam")}, el("span", {class: "m4-rv-mark", "aria-hidden": "true", text: MARK[kind] || "–"}), " " + label);
  function pill(label) {  // checks.js pill — cùng phân loại nhãn
    const kind = ["Cao", "Lỗi", "CHẶN", "Lệch", "Lỗi kiểm tra"].includes(label) ? "danger"
      : ["Trung bình", "Cần xem", "Có cảnh báo", "Kiểm có giới hạn"].includes(label) ? "warning"
        : ["Thấp", "Không áp dụng", "Không có số liệu", "Không đủ điều kiện xét"].includes(label) || String(label).startsWith("Chưa đủ căn cứ") ? "neutral" : "success";
    return badge(label, kind);
  }
  const TT_KIEM = {CHECKED: ["Đã kiểm", "success"], NOT_ELIGIBLE: ["Không đủ điều kiện xét", "neutral"], LIMITED: ["Kiểm có giới hạn", "warning"],
    NOT_AVAILABLE: ["Không có số liệu", "neutral"], INCOMPLETE: ["Chưa đủ căn cứ", "warning"], ERROR: ["Lỗi kiểm tra", "danger"], KHONG_AP_DUNG: ["Không áp dụng (có căn cứ)", "neutral"]};
  const ttKiem = t => badge(...(TT_KIEM[t] || [t || "—", "neutral"]));
  const TT_RUN = {PENDING: ["Chờ", "neutral"], RUNNING: ["Đang chạy", "info"], SUCCEEDED: ["Xong · đủ phạm vi", "success"], PARTIAL: ["Xong · phạm vi chưa đủ", "warning"],
    FAILED: ["Lỗi — không có kết quả", "danger"], STALE: ["Căn cứ đã đổi — không hiện hành", "warning"], CANCELLED: ["Đã hủy", "neutral"]};
  const ttRun = t => badge(...(TT_RUN[t] || [t, "neutral"]));

  // ------------------------------------------------------------------ trạng thái
  let ep = 0, genDs = 0, genCt = 0, genForm = 0;
  let box = null, ctx = null, ds = null, kq = null, runChon = null, dsLoi = null;
  let hoatDong = false;  // FIX01 R7: vùng Review đang là tab hiện hành của đúng HĐ/đợt; shell tắt NGAY lúc ý định đổi tab/HĐ/đợt (tat())
  const sel = {dot: null, tep: null, che_do: "L1_L2", o_dich: ""};
  const ui = {layer: "all", severity: "all", hmLoc: null, hmMo: false, doi: {}, ghep: {}, lyDo: {}, ev: null, formMo: true, cc: null};
  // M4-02A căn cứ lần chạy: thế hệ của panel BOQ/phụ lục căn cứ — tăng ĐỒNG BỘ khi mở/đóng/đổi bằng chứng, đổi lớp, đổi lần chạy, đổi vai/HĐ, rời tab
  let genCc = 0;
  const boCc = () => { genCc += 1; ui.cc = null; };
  const moEv = r => { ui.ev = r; boCc(); ve_(); };
  const khoaMap = new Map();
  const taoKhoa = () => "m4rv-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));
  const actor = () => (ctx && ctx.nguoi) || null;  // vai hiện hành do shell M4 nhận từ máy chủ (GET /api/m4)
  const selKey = () => JSON.stringify([ctx && ctx.hdId, sel.dot, sel.tep, sel.che_do, sel.o_dich || null]);
  const vungSong = () => hoatDong && !!box && box.isConnected;
  function fence(them) {  // epoch (tat/xoa tăng) + vai + HĐ + vùng đang hoạt động + điều kiện riêng — kiểm trước request, sau headers, sau blob
    const e = ep, a = actor(), h = ctx && ctx.hdId;
    return () => e === ep && vungSong() && a === actor() && h === (ctx && ctx.hdId) && (!them || them());
  }
  const formCon = () => { const g = genForm; return () => g === genForm; };

  class LoiRv extends Error { constructor(status, code, message) { super(message); this.status = status; this.code = code; } }
  async function goi(path, opts = {}) {
    let res;
    try { res = await fetch(path, {...opts, headers: {"X-KTT-Token": TOKEN, ...(opts.headers || {})}, cache: "no-store", credentials: "same-origin"}); }
    catch (_) { throw new LoiRv(0, "MAT_KET_NOI", "Mất kết nối — chưa rõ máy chủ đã ghi hay chưa. Khóa được giữ; bấm Gửi lại y nguyên."); }
    if (!res.ok) { const r = await res.json().catch(() => ({})); throw new LoiRv(res.status, r.error || "HTTP_" + res.status, r.message || `Không hoàn tất (${res.status}).`); }
    return res;
  }
  async function docJson(res) { try { return await res.json(); } catch (_) { throw new LoiRv(0, "KET_QUA_CHUA_RO", "Phản hồi đọc không trọn — chưa rõ kết quả; bấm Gửi lại y nguyên."); } }
  const chuaRo = e => !!e && (e.status === 0 || e.status >= 500) && e.code !== "M4_CHUA_SAN_SANG_GHI_NGUON";
  function trangThai(msg, loi = false) { const s = box && box.querySelector(".m4-rv-status"); if (s) { s.textContent = msg || ""; s.className = "m4-rv-status m4-status" + (loi ? " m4-loi-chu" : ""); } }

  // lệnh có khóa (cùng mẫu C2 của m4.js): bản ghi theo (route, body gốc); lần gửi đang bay → bấm lặp không gửi; chưa rõ → giữ khóa, gửi lại y nguyên
  function nhanBanGhi(k) { let rec = khoaMap.get(k); if (rec && rec.chu) return null; if (!rec) { rec = {khoa: taoKhoa(), chu: null}; khoaMap.set(k, rec); } const ve = {}; rec.chu = ve; return {rec, ve}; }
  function traBanGhi(k, rec, ve, xong) { if (rec.chu === ve) rec.chu = null; if (xong && khoaMap.get(k) === rec) khoaMap.delete(k); }
  let guiLai = null;
  // FIX02 F6: `gf` = thế hệ form/lựa chọn chụp tại Ý ĐỊNH GỐC (lúc bấm). Mọi toast/trạng thái/lỗi/làm mới/nút gửi lại/giá trị trả về cho
  // continuation chỉ chạy khi CẢ ngữ cảnh (f) LẪN thế hệ form còn đúng — POST A về muộn sau khi người dùng nhập nháp B không chạm UI của B.
  // Request A có thể đã commit hợp lệ: bản ghi khóa (khoaMap) GIỮ NGUYÊN khi chưa rõ kết quả, bấm lại đúng lệnh cũ (cùng body) dùng lại khóa cũ.
  async function lenh(path, body, ok, f, gf = genForm) {
    const ui = () => f() && gf === genForm;
    if (!f()) { trangThai("Thao tác thuộc vai/HĐ/lựa chọn cũ — không gửi.", true); return null; }
    if (gf !== genForm) return null;  // nháp đã đổi giữa lúc bấm và lúc gửi → không gửi theo ý định cũ
    const k = JSON.stringify([path, body]), so = nhanBanGhi(k);
    if (!so) { trangThai("Đang gửi yêu cầu này — chờ kết quả."); return null; }
    const {rec, ve} = so;
    guiLai = null; trangThai(path === "review/ghep" ? "Đang ghi ghép tay…" : "Đang kiểm tra hồ sơ — Lớp 1 toàn vẹn file, Lớp 2 đối chiếu HĐ/PL/BOQ (có thể mất vài phút)…");
    let xong = false;
    try {
      const r = await docJson(await goi("/api/m4/" + path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({...body, khoa: rec.khoa})}));
      xong = true;
      if (!ui()) return null;
      K.toast(ok + (r.lap_lai ? " (kết quả cũ của cùng yêu cầu — không tính lại)" : ""));
      trangThai(ok + (r.lap_lai ? " — biên nhận cũ." : ""));
      return r;
    } catch (e) {
      if (!chuaRo(e)) xong = true;
      if (!ui()) return null;
      K.toast(e.message, true); trangThai(e.message, true);
      if (e.code === "M4_REVIEW_CO_SO_DOI") napDs();
      if (chuaRo(e)) { guiLai = {path, body, ok, f}; ve_(); }  // ĐÚNG body gốc + khóa (khoaMap) + fence ngữ cảnh gốc; không dựng lại từ nháp
      return null;
    } finally { traBanGhi(k, rec, ve, xong); }
  }

  // ------------------------------------------------------------------ nạp (barrier đổi vai + thế hệ + lựa chọn)
  async function napDs() {
    if (!ctx || !vungSong() || K.vaiDangChan("m4_review")) return;
    // FIX03 F2: thế hệ form/lựa chọn chụp lúc VÀO và kiểm cùng epoch/vai/HĐ/đợt/tệp/thế hệ GET/vùng đang hoạt động TRƯỚC mọi hiệu ứng
    // (gán ds/dsLoi/sel.tep/kq/runChon, trạng thái, lỗi, vẽ). GET làm mới A về muộn sau khi người dùng mở/nhập nháp B → bỏ toàn bộ, không
    // ghi trạng thái A vào B, không đổi basis/lựa chọn mà lệnh B sẽ dùng.
    const e = ep, g = ++genDs, key = selKey(), fs = formCon();
    const dung = () => e === ep && vungSong() && g === genDs && key === selKey() && fs();
    const q = new URLSearchParams({hop_dong_id: ctx.hdId});
    if (sel.dot) q.set("dot_id", sel.dot);
    if (sel.tep) { q.set("tep_id", sel.tep); q.set("che_do", sel.che_do); }
    if (sel.tep && sel.o_dich) q.set("o_dich", sel.o_dich);
    try {
      const res = await goi("/api/m4/review?" + q.toString());
      if (!dung()) return;
      const r = await res.json();
      if (!dung()) return;
      ds = r; dsLoi = null;
      if (sel.tep && !(r.tep || []).some(t => t.tep_id === sel.tep) && sel.dot) { sel.tep = null; }
      ve_();
    } catch (err) {
      if (!dung()) return;
      if (err.status === 403 || err.status === 404) { ds = null; kq = null; runChon = null; }  // từ chối quyền HIỆN HÀNH đúng ngữ cảnh vẫn hiệu lực
      dsLoi = err.message; trangThai(err.message, true);
      ve_();
    }
  }
  async function moRun(id) {
    if (!ctx || !vungSong() || K.vaiDangChan("m4_review")) return;
    runChon = id; ui.ev = null; boCc();
    // FIX01 R7/FIX02 F6: thế hệ form + lựa chọn chụp lúc VÀO; GET lịch sử A về muộn sau khi người dùng đã nhập/chọn nháp B → bỏ kết quả A:
    // không đóng form, không đổi lựa chọn, không xóa mã/lý do, không vẽ đè, không báo trạng thái A vào B
    const e = ep, g = ++genCt, gf = genForm, key = selKey(), dung = () => e === ep && hoatDong && g === genCt && runChon === id;
    const conNhap = () => gf === genForm && key === selKey();
    ve_();
    try {
      const r = await (await goi("/api/m4/review/" + encodeURIComponent(id))).json();
      if (!dung()) return;
      if (!conNhap()) { runChon = null; return; }
      kq = r; ui.layer = "all"; ui.severity = "all";
      ui.formMo = false;
      const run = r.run;  // đồng bộ lựa chọn với lần chạy để lấy token basis HIỆN HÀNH cho Ghép/Chạy lại
      if (selKey() !== JSON.stringify([ctx.hdId, run.dot_id, run.tep_id, run.che_do, run.o_dich || null])) {
        sel.dot = run.dot_id; sel.tep = run.tep_id; sel.che_do = run.che_do; sel.o_dich = run.o_dich || ""; genForm += 1;
        napDs();
      }
      ve_();
    } catch (err) {
      if (!dung()) return;
      if (!conNhap()) { runChon = null; return; }
      if (err.status === 403 || err.status === 404) { kq = null; runChon = null; }
      trangThai(err.message, true);
      ve_();
    }
  }
  // sau lệnh chạy/chạy lại xong: chỉ mở kết quả khi ngữ cảnh + thế hệ form của Ý ĐỊNH GỐC còn đúng (không đóng form/đổi lựa chọn/báo vào nháp B)
  function moSauLenh(r, f, gf) {
    if (r && r.run_id && f() && gf === genForm) moRun(r.run_id);
  }
  async function tai(a) {  // tải báo cáo: fence trước request, sau mọi await, trước click/trạng thái
    const id = runChon, gf = genForm, f = fence(() => runChon === id && gf === genForm);
    if (!f()) return;
    try {
      const res = await goi(`/api/m4/review/${encodeURIComponent(id)}/tep/${encodeURIComponent(a.id)}`);
      if (!f()) return;
      const blob = await res.blob();
      if (!f()) return;
      if (!blob.size) { trangThai("Tệp tải về rỗng — không lưu.", true); return; }
      const url = URL.createObjectURL(blob), link = el("a", {href: url, download: a.ten});
      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 60000);
      trangThai(`Đã tải ${a.ten} (${blob.size} byte · SHA ${a.raw_sha256.slice(0, 12)}…).`);
    } catch (err) { if (f()) trangThai(err.message, true); }
  }

  // ------------------------------------------------------------------ căn cứ lần chạy (checks.js evidence: "Mở BOQ hiệu lực"/"Xem phụ lục" → bản chụp BASIS)
  // CHỈ ĐỌC artifact BASIS bất biến của ĐÚNG lần chạy đang xem qua route tải hiện có GET /api/m4/review/{run}/tep/{artifact} (quyền hiện hành do máy chủ
  // kiểm). Không gọi API HĐ/PL/BOQ hiện hành, không POST, không tính lại hiệu lực PL/NT/TT/tiền. Trước khi hiển thị: đúng MỘT đăng ký BASIS, mã UUID,
  // SHA-256 đăng ký = basis_sha256 của lần chạy, độ dài ≤ giới hạn, Content-Type JSON, Content-Length (nếu có) = độ dài đăng ký, đọc từng khúc dừng
  // ngay khi vượt độ dài đăng ký, độ dài thật = đăng ký, SHA-256 thật (crypto.subtle) = đăng ký, UTF-8 chặt, JSON, phiên bản + kiểu + danh tính lần chạy.
  // Fence epoch/vai/HĐ/vùng + lần chạy/kết quả/bằng chứng/thế hệ panel sau MỌI await (headers, từng khúc bytes, hash) và trước mọi công bố.
  const CC_PHIEN_BAN = "m4.review.basis/1";
  const CC_TOI_DA_BYTE = 16 * 1024 * 1024;  // > 16 MiB (đăng ký/Content-Length/bytes thật) → chưa hiển thị; tải ⭳ Căn cứ JSON vẫn dùng được
  const CC_TOI_DA_DONG = 2000;  // dòng BOQ vẽ tối đa mỗi lần xem (cộng mọi bảng); vượt → báo rõ "chưa hiển thị đủ", không cắt im lặng
  const CC_TOI_DA_PL = 500;  // dòng phụ lục vẽ tối đa; vượt → báo rõ
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, HEX64 = /^[0-9a-f]{64}$/;
  const CU = Symbol("ngu-canh-cu");
  class LoiCc extends Error { constructor(code, message) { super(message); this.code = code; } }
  const laO = x => x !== null && typeof x === "object" && !Array.isArray(x);
  const laVo = x => x === null || x === undefined || typeof x === "string" || typeof x === "boolean" || (typeof x === "number" && Number.isFinite(x));
  const coTruong = (o, k) => laO(o) && Object.prototype.hasOwnProperty.call(o, k);
  // giá trị ĐÚNG như đã lưu: thiếu trường ≠ NULL ≠ "0"; số lưu dạng chuỗi Decimal giữ nguyên, không làm tròn/định dạng lại
  const gtLuu = (o, k) => !coTruong(o, k) ? "(không có trường)" : o[k] === null ? "NULL" : typeof o[k] === "boolean" ? (o[k] ? "có" : "không")
    : typeof o[k] === "object" ? JSON.stringify(o[k]) : String(o[k]);
  const CC_TEP = ["id", "du_an_id", "phap_nhan_id", "vai_tro_tai_lieu", "raw_sha256", "byte_length", "ten_goc", "media_type"];
  const CC_DOT = ["id", "hop_dong_id", "du_an_id", "so_dot", "ngay_nghiem_thu", "trang_thai", "revision", "nop_id", "nop_digest", "nop_revision_ho_so"];
  const CC_HD = ["id", "so_hop_dong", "ten", "revision", "rev_tham_so", "trang_thai_pl", "tep_hop_dong_id", "tep_hop_dong_sha256"];
  const CC_PL = ["id", "so_pl", "ngay_ky", "ngay_hieu_luc", "trang_thai", "doi_boq", "tep_id"];
  const CC_BOQ = ["id", "lan", "phu_luc_id", "tep_id", "raw_sha256", "sheet", "hang_tieu_de", "so_dong", "trang_thai"];
  const CC_DONG = ["dong", "ma_hm", "thao_tac", "stt", "nhom", "ten", "dvt", "kl", "don_gia", "thanh_tien", "ma_rieng"];
  const CC_DONG_NHAN = ["Dòng (vật lý)", "Mã HM", "Thao tác", "STT", "Nhóm", "Tên công việc", "ĐVT", "KL", "Đơn giá", "Thành tiền", "Mã riêng"];
  function chonBasis(k, id) {  // đúng MỘT đăng ký BASIS của đúng lần chạy đang chọn; không URL máy chủ trả về, không artifact của lần chạy khác
    const run = k && k.run;
    if (!run || run.id !== id || !UUID_RE.test(String(id))) throw new LoiCc("LAN_CHAY", "Lần chạy đang xem không khớp — không đọc căn cứ.");
    if (!HEX64.test(String(run.basis_sha256))) throw new LoiCc("DANG_KY", "Lần chạy không có SHA-256 căn cứ hợp lệ.");
    const bs = (Array.isArray(k.artifact) ? k.artifact : []).filter(a => a && a.loai === "BASIS");
    if (!bs.length) throw new LoiCc("KHONG_CO", "Lần chạy không có tệp căn cứ (BASIS) đã đăng ký.");
    if (bs.length > 1) throw new LoiCc("NHIEU", `Lần chạy có ${bs.length} tệp căn cứ đã đăng ký — không chọn được một nguồn duy nhất.`);
    const a = bs[0];
    if (!UUID_RE.test(String(a.id)) || !HEX64.test(String(a.raw_sha256)) || !Number.isSafeInteger(a.byte_length) || a.byte_length <= 0)
      throw new LoiCc("DANG_KY", "Đăng ký tệp căn cứ sai (mã / SHA-256 / độ dài).");
    if (a.raw_sha256 !== run.basis_sha256) throw new LoiCc("DANG_KY", "SHA-256 tệp căn cứ đã đăng ký khác căn cứ của lần chạy.");
    if (a.byte_length > CC_TOI_DA_BYTE) throw new LoiCc("QUA_LON", `Tệp căn cứ ${a.byte_length} byte vượt giới hạn hiển thị ${CC_TOI_DA_BYTE} byte.`);
    return a;
  }
  function kiemDau(res, a) {  // headers: kiểu JSON + Content-Length (nếu có) đúng độ dài đăng ký — trước khi đọc bytes
    const h = res.headers && typeof res.headers.get === "function" ? res.headers : null;
    const ct = h ? String(h.get("Content-Type") || "") : "";
    if (!/^application\/json\s*(;|$)/i.test(ct)) throw new LoiCc("KIEU", `Máy chủ trả kiểu "${ct || "không rõ"}" — không phải JSON căn cứ.`);
    const cl = h ? h.get("Content-Length") : null;
    if (cl !== null && cl !== undefined && cl !== "" && Number(cl) !== a.byte_length) throw new LoiCc("DO_DAI", `Độ dài máy chủ báo (${cl}) khác độ dài đăng ký (${a.byte_length}).`);
  }
  async function docBytes(res, can, f) {  // đọc có chặn: dừng + hủy luồng ngay khi vượt `can` byte; fence sau MỖI khúc
    const r = res.body && typeof res.body.getReader === "function" ? res.body.getReader() : null;
    const huy = () => { try { const p = r.cancel(); if (p && p.catch) p.catch(() => {}); } catch (_) { /* luồng đã đóng */ } };
    if (!r) {
      let ab;
      try { ab = await res.arrayBuffer(); } catch (_) { if (!f()) return CU; throw new LoiCc("DOC", "Đọc tệp căn cứ không trọn."); }
      return f() ? new Uint8Array(ab) : CU;
    }
    const phan = [];
    let n = 0;
    for (;;) {
      let k;
      try { k = await r.read(); } catch (_) { if (!f()) return CU; throw new LoiCc("DOC", "Đọc tệp căn cứ không trọn."); }
      if (!f()) { huy(); return CU; }
      if (k.done) break;
      const v = k.value;
      if (!v || typeof v.byteLength !== "number") { huy(); throw new LoiCc("DOC", "Luồng tệp căn cứ trả dữ liệu không phải bytes."); }
      n += v.byteLength;
      if (n > can) { huy(); throw new LoiCc("DO_DAI", `Tệp căn cứ dài hơn độ dài đăng ký (${can} byte) — dừng đọc.`); }
      phan.push(v);
    }
    const out = new Uint8Array(n);
    let o = 0;
    for (const p of phan) { out.set(p, o); o += p.byteLength; }
    return out;
  }
  async function bamSha(bytes) {
    const sub = window.crypto && window.crypto.subtle;
    if (!sub || typeof sub.digest !== "function") throw new LoiCc("CRYPTO", "Trình duyệt không có SHA-256 (crypto.subtle) — chưa kiểm được tệp căn cứ nên chưa hiển thị.");
    let h;
    try { h = await sub.digest("SHA-256", bytes); } catch (_) { throw new LoiCc("CRYPTO", "Trình duyệt không tính được SHA-256 — chưa kiểm được tệp căn cứ nên chưa hiển thị."); }
    return Array.from(new Uint8Array(h), b => b.toString(16).padStart(2, "0")).join("");
  }
  function voHet(o, keys, ten) { for (const k of keys) if (!laVo(o[k])) throw new LoiCc("HINH_DANG", `Căn cứ sai kiểu ở ${ten}.${k}.`); }
  function dsO(x, ten) { if (!Array.isArray(x) || !x.every(laO)) throw new LoiCc("HINH_DANG", `Căn cứ sai kiểu ở ${ten} (phải là danh sách bản ghi).`); return x; }
  function docCo(bytes) {  // UTF-8 chặt → JSON → kiểu đúng định dạng m4.review.basis/1 (không coi JSON chung là căn cứ)
    const TD = window.TextDecoder;
    if (typeof TD !== "function") throw new LoiCc("MA_HOA", "Trình duyệt không giải mã được UTF-8 — chưa hiển thị.");
    let s, co;
    try { s = new TD("utf-8", {fatal: true}).decode(bytes); } catch (_) { throw new LoiCc("MA_HOA", "Tệp căn cứ không phải UTF-8 hợp lệ."); }
    try { co = JSON.parse(s); } catch (_) { throw new LoiCc("JSON", "Tệp căn cứ không phải JSON hợp lệ."); }
    if (!laO(co)) throw new LoiCc("HINH_DANG", "Tệp căn cứ không phải object.");
    if (co.phien_ban !== CC_PHIEN_BAN) throw new LoiCc("PHIEN_BAN", `Phiên bản căn cứ "${laVo(co.phien_ban) ? String(co.phien_ban) : "?"}" chưa hỗ trợ (chỉ ${CC_PHIEN_BAN}).`);
    voHet(co, ["che_do", "o_dich", "du_an_id", "phap_nhan_id", "engine_sha256"], "căn cứ");
    if (!laO(co.tep)) throw new LoiCc("HINH_DANG", "Căn cứ thiếu/sai mục tep.");
    voHet(co.tep, CC_TEP, "tep");
    if (co.dot != null) { if (!laO(co.dot)) throw new LoiCc("HINH_DANG", "Căn cứ sai kiểu ở dot."); voHet(co.dot, CC_DOT, "dot"); }
    if (co.dot_tep != null) dsO(co.dot_tep, "dot_tep").forEach(x => voHet(x, ["tep_id", "muc"], "dot_tep"));
    if (co.hop_dong != null) { if (!laO(co.hop_dong)) throw new LoiCc("HINH_DANG", "Căn cứ sai kiểu ở hop_dong."); voHet(co.hop_dong, CC_HD, "hop_dong"); }
    if (co.phu_luc != null) dsO(co.phu_luc, "phu_luc").forEach(p => voHet(p, CC_PL, "phu_luc"));
    if (co.boq != null) dsO(co.boq, "boq").forEach(b => { voHet(b, CC_BOQ, "boq"); if (b.dong != null) dsO(b.dong, "boq.dong").forEach(d => voHet(d, CC_DONG, "boq.dong")); });
    if (co.truoc_da_duyet != null) { if (!laO(co.truoc_da_duyet)) throw new LoiCc("HINH_DANG", "Căn cứ sai kiểu ở truoc_da_duyet."); voHet(co.truoc_da_duyet, ["trang_thai", "ly_do"], "truoc_da_duyet"); }
    return co;
  }
  function kiemDanhTinh(co, run) {  // chỉ so trường mà lần chạy/bản chụp CÓ cung cấp; không tự thêm run_id vào định dạng lưu
    const lech = [], so = (ten, a, b) => { if (b !== null && b !== undefined && a !== b) lech.push(ten); };
    if (co.che_do !== run.che_do) lech.push("chế độ");
    if ((co.o_dich || null) !== (run.o_dich || null)) lech.push("ô đích");
    so("dự án", co.du_an_id, run.du_an_id); so("pháp nhân", co.phap_nhan_id, run.phap_nhan_id);
    so("tệp", co.tep.id, run.tep_id); so("raw tệp", co.tep.raw_sha256, run.raw_sha256); so("dự án của tệp", co.tep.du_an_id, run.du_an_id);
    if (run.dot_id) { if (!co.dot) lech.push("đợt"); else { so("đợt", co.dot.id, run.dot_id); so("HĐ của đợt", co.dot.hop_dong_id, run.hop_dong_id); } }
    else if (co.dot) lech.push("đợt");
    if (co.hop_dong) { so("HĐ", co.hop_dong.id, co.dot && co.dot.hop_dong_id); so("HĐ", co.hop_dong.id, run.hop_dong_id); }
    if (run.hop_dong_id && ctx && run.hop_dong_id !== ctx.hdId) lech.push("HĐ đang mở");
    if (lech.length) throw new LoiCc("LECH", `Căn cứ không khớp lần chạy đang xem (${[...new Set(lech)].join(", ")}).`);
  }
  function xemCanCu(loai, r) {  // nút "Xem BOQ căn cứ"/"Xem phụ lục căn cứ": đổi góc xem trên CÙNG bản đã kiểm, hoặc đọc mới
    if (!ctx || !vungSong() || K.vaiDangChan("m4_review")) return;
    if (!kq || !kq.run || ui.ev !== r) return;
    const c = ui.cc;
    if (c && c.ev === r && c.run === runChon && c.g === genCc && (c.trang === "DANG" || c.trang === "OK")) { c.loai = loai; ve_(); return; }
    docCanCu(loai, r);
  }
  async function docCanCu(loai, r) {
    genCc += 1;
    const g = genCc, kqLuc = kq, run = kq.run, id = runChon;
    const rec = {g, ev: r, run: id, loai, trang: "DANG", co: null, ly_do: null, a: null};
    ui.cc = rec;
    const f = fence(() => g === genCc && ui.cc === rec && kq === kqLuc && runChon === id && ui.ev === r);
    ve_();
    try {
      const a = chonBasis(kqLuc, id);
      rec.a = a;
      const res = await goi(`/api/m4/review/${encodeURIComponent(id)}/tep/${encodeURIComponent(a.id)}`);
      if (!f()) return;
      kiemDau(res, a);
      const bytes = await docBytes(res, a.byte_length, f);
      if (bytes === CU || !f()) return;
      if (bytes.byteLength !== a.byte_length) throw new LoiCc("DO_DAI", `Độ dài thật ${bytes.byteLength} byte khác độ dài đăng ký ${a.byte_length} byte.`);
      const hex = await bamSha(bytes);
      if (!f()) return;
      if (hex !== a.raw_sha256 || hex !== run.basis_sha256) throw new LoiCc("HASH", "SHA-256 thật của tệp căn cứ khác SHA-256 đã đăng ký — không hiển thị.");
      const co = docCo(bytes);
      kiemDanhTinh(co, run);
      if (!f()) return;
      rec.trang = "OK"; rec.co = co;
      ve_();
    } catch (err) {
      if (!f()) return;  // lỗi/403 của ngữ cảnh cũ không xóa bằng chứng/panel/trạng thái của ngữ cảnh mới
      if (err instanceof LoiRv && (err.status === 401 || err.status === 403 || (err.status === 404 && err.code === "M4_REVIEW_KHONG_THAY"))) {
        kq = null; runChon = null; ui.ev = null; boCc();  // từ chối quyền HIỆN HÀNH đúng ngữ cảnh: gỡ kết quả/bằng chứng/căn cứ đang hiện (như moRun)
        ve_(); trangThai(err.message, true);  // vẽ trước rồi mới ghi trạng thái (ve_ dựng dòng trạng thái mới)
        return;
      }
      rec.trang = "LOI";
      rec.ly_do = err instanceof LoiRv && err.status === 0 ? "Mất kết nối khi đọc tệp căn cứ — bấm lại để thử." : err.message;
      ve_();
    }
  }

  // ------------------------------------------------------------------ hành động (handleCheckAction nguồn, nối route hiện hành)
  async function chay() {
    const cs = ds && ds.co_so;
    if (!sel.tep) { trangThai("Chọn tệp hồ sơ Excel đã tiếp nhận trước khi chạy.", true); return; }
    if (sel.che_do === "L1_L2" && !sel.dot) { trangThai("L1+L2 cần chọn đợt (ngày nghiệm thu) của hợp đồng.", true); return; }
    if (!cs || !cs.san_sang || !cs.basis_sha256) { trangThai((cs && cs.ly_do) || "Chưa có căn cứ hiện hành — bấm ↻ rồi chạy.", true); return; }
    const key = selKey(), gf = genForm, f = fence(() => key === selKey());
    const r = await lenh("review/chay", {du_an_id: cs.du_an_id, tep_id: sel.tep, che_do: sel.che_do, dot_id: sel.dot, o_dich: sel.o_dich || null, expected_basis: cs.basis_sha256},
      "Đã kiểm tra hồ sơ", f, gf);
    if (r && f() && gf === genForm) { await napDs(); moSauLenh(r, f, gf); }
  }
  async function chayLai() {
    const run = kq && kq.run, cs = ds && ds.co_so;
    if (!run || !cs || !cs.basis_sha256) return;
    const gf = genForm, f = fence(() => runChon === run.id);
    const r = await lenh("review/chay-lai", {run_id: run.id, expected_basis: cs.basis_sha256}, "Đã chạy lại trên cùng tệp gốc", f, gf);
    if (r && f() && gf === genForm) { await napDs(); moSauLenh(r, f, gf); }
  }
  async function ghep(h) {
    const run = kq && kq.run, cs = ds && ds.co_so, k = h.khoa;
    const ma = String(ui.ghep[k] || "").trim(), ly = String(ui.lyDo[k] || "").trim();
    if (!run || !cs) return;
    if (!ma) { trangThai("Chọn mã HM BOQ để ghép.", true); return; }
    if (!ly) { trangThai("Nhập lý do ghép tay (ghi lịch sử).", true); return; }
    const u = (h.ung_vien || []).find(x => x.ma_hm === ma);
    const ng = (u && u.nguon_boq) || [];
    if (ng.length !== 1) { trangThai(ng.length ? "Mã HM có nhiều dòng nguồn hiệu lực — chưa chọn được đích duy nhất." : "Mã HM không có dòng BOQ hiệu lực tại ngày NT (chưa có/đã bỏ/chỉ ở PL chưa hiệu lực).", true); return; }
    // FIX01 R7/FIX02 F6: POST ghép A có thể commit hợp lệ dù về muộn; continuation (toast/trạng thái/dọn mã-lý do/làm mới) chỉ chạy khi ngữ cảnh
    // VÀ thế hệ form của ý định gốc còn đúng — lenh đã chặn trước mọi callback khi nháp B xuất hiện
    const gf = genForm, kqLuc = kq, f = fence(() => runChon === run.id);
    const r = await lenh("review/ghep", {run_id: run.id, khoa_dong: k, boq_id: ng[0].boq_id, ma_hm: ma, expected_basis: cs.basis_sha256, ly_do: ly}, `Đã ghép dòng ${h.dong} → ${ma}`, f, gf);
    if (!r || !f() || gf !== genForm) return;
    if (kq === kqLuc) h.ghep_tay = ma;  // sự thật đã commit của dòng A (chỉ trên đúng bản kết quả đã hiển thị), không chạm nháp
    if (ui.ghep[k] === ma) delete ui.ghep[k];
    if (String(ui.lyDo[k] || "").trim() === ly) delete ui.lyDo[k];
    await napDs();
    if (f() && gf === genForm) ve_();
  }

  // ------------------------------------------------------------------ khối giao diện (port DOM của checks.js)
  const bang = (cot, rows, cls) => el("div", {class: "m4-bang m4-rv-bang" + (cls ? " " + cls : "")}, el("table", {}, el("thead", {}, el("tr", {}, cot.map(c => el("th", {text: c})))), el("tbody", {}, rows)));
  const td = (...c) => el("td", {}, ...c);
  const nho = (t, cls) => el("div", {class: "m4-nho" + (cls ? " " + cls : ""), text: t});
  function cheDo() {  // checks.js cheDo — hai chế độ trên CÙNG một màn
    const o = (id, t, d) => el("button", {type: "button", class: "m4-rv-chedo" + (sel.che_do === id ? " m4-chon" : ""), "aria-pressed": String(sel.che_do === id),
      onclick: () => { if (sel.che_do !== id) { sel.che_do = id; genForm += 1; ds = ds && {...ds, co_so: null}; ve_(); napDs(); } }}, el("strong", {text: (sel.che_do === id ? "✓ " : "") + t}), nho(d));
    return el("div", {class: "m4-rv-hang", role: "group", "aria-label": "Chế độ kiểm tra"},
      o("L1_L2", "Đủ hai lớp — L1 + L2 theo HĐ/PL/BOQ", "Lớp 1 toàn vẹn file + Lớp 2 đối chiếu giá trị HĐ, đơn giá, khối lượng BOQ, tỷ lệ thanh toán, phụ lục tại ngày nghiệm thu của đợt."),
      o("L1", "Chỉ toàn vẹn file — Lớp 1", "Công thức, liên kết, số gõ tay, sheet ẩn, truy vết số đề nghị. Không đối chiếu hợp đồng."));
  }
  function form() {  // checks.js paymentForm — HĐ đến từ shell (không chọn HĐ đầu danh sách), đợt + tệp đã tiếp nhận, ô đích tùy chọn
    const dots = ctx.dots || [];
    const sDot = el("select", {"aria-label": "Đợt thanh toán", onchange: ev => { sel.dot = ev.target.value || null; sel.tep = null; genForm += 1; ve_(); napDs(); }},
      el("option", {value: "", text: "— chọn đợt —"}), dots.map(d => el("option", {value: d.id, selected: d.id === sel.dot, text: `Đợt ${d.so_dot} · NT ${fmtDate(d.ngay_nghiem_thu)} · ${d.trang_thai === "DA_NOP" ? "đã nộp" : "nháp"}`})));
    const teps = (ds && ds.tep) || [];
    const sTep = el("select", {"aria-label": "Tệp hồ sơ Excel", onchange: ev => { sel.tep = ev.target.value || null; genForm += 1; ve_(); napDs(); }},
      el("option", {value: "", text: sel.dot ? (teps.length ? "— chọn tệp Excel đã gắn vào đợt —" : "Đợt chưa có tệp Excel (.xlsx) nào") : "Chọn đợt trước"}),
      teps.map(t => el("option", {value: t.tep_id, selected: t.tep_id === sel.tep, text: `${t.muc} · ${t.ten_goc} · ${num(t.byte_length)} byte`})));
    const oDich = el("input", {type: "text", value: sel.o_dich, placeholder: "Ví dụ: 0.Giấy ĐNTT!F16 — để trống: tự tìm", "aria-label": "Ô số đề nghị",
      oninput: ev => { sel.o_dich = ev.target.value; genForm += 1; }, onchange: () => napDs()});
    const cs = ds && ds.co_so;
    const can = [];
    if (cs && cs.phu_thuoc) for (const [k, v] of Object.entries(cs.phu_thuoc)) can.push(el("li", {class: v.ok ? "m4-du-chu" : "m4-loi-chu"}, `${v.ok ? "✓" : "✗"} ${k}: ${v.ly_do}`));
    const nut = el("button", {type: "button", class: "m4-chinh", disabled: !(sel.tep && cs && cs.san_sang && cs.basis_sha256), onclick: () => chay()}, "▶ Kiểm tra hồ sơ");
    return el("section", {class: "m4-card"}, el("h3", {text: "Hồ sơ kiểm tra"}), nho("Áp dụng phụ lục theo ngày nghiệm thu của đợt (lấy từ đợt M4; đổi ngày qua tab Đợt)."),
      el("div", {class: "m4-form"}, el("label", {}, "Đợt", sDot), el("label", {}, "Tệp hồ sơ Excel đã tiếp nhận", sTep), el("label", {}, "Ô số đề nghị (không bắt buộc)", oDich)),
      cs ? nho(cs.san_sang ? `Căn cứ hiện hành ${String(cs.basis_sha256).slice(0, 12)}… · quyền ${cs.quyen} · ${cs.so_ghep_tay} ghép tay · ${cs.engine}` : cs.ly_do) : (sel.tep ? nho("Đang chụp căn cứ…") : null),
      can.length ? el("ul", {class: "m4-thieu-ds"}, can) : null,
      el("div", {class: "m4-rv-hang"}, nut, el("span", {class: "m4-nho", text: "Tệp giữ nguyên trên máy này; không gửi ra ngoài. Báo cáo Excel không phải phiếu duyệt/thanh toán."})));
  }
  function scope(k2, run) {  // checks.js scope
    const chua = k2.phu_luc_chua_ap_dung || [], ap = k2.phu_luc_ap_dung || [];
    return el("section", {class: "m4-card m4-rv-hang"},
      el("div", {class: "m4-rv-o"}, el("strong", {text: ctx.soHd || ""}), nho(`${k2.loai_gia || ""} · đợt ${k2.dot ?? "?"} · đợt trước đã duyệt: ${k2.dot_truoc ?? "chưa có nguồn"}`)),
      el("div", {class: "m4-rv-o"}, nho("Ngày nghiệm thu áp dụng"), el("strong", {text: fmtDate(k2.ngay_nghiem_thu)}),
        nho(chua.length ? chua.map(p => `${p.so_pl} (${fmtDate(p.ngay_hieu_luc)}) chưa áp dụng`).join("; ") : "Không có phụ lục chờ hiệu lực")),
      el("div", {class: "m4-rv-o"}, nho("Giá trị HĐ hiệu lực"), el("strong", {class: "m4-o", text: money(k2.gt_hieu_luc) + " ₫"})),
      el("div", {class: "m4-rv-o"}, nho("Phụ lục áp dụng"), el("strong", {text: ap.length ? ap.map(p => p.so_pl).join(", ") : "Không có"})),
      el("div", {class: "m4-rv-o"}, nho("Lần chạy"), ttRun(run.trang_thai)));
  }
  function summary(r, integrity) {  // checks.js summary
    const dem = r.dem || {}, dinhLuong = (r.phat_hien || []).filter(f => f.layer === 2 && typeof f.amount === "number" && f.code !== "GT").length;
    const deNghi = (r.lop2 && r.lop2.de_nghi) ?? r.lop1.de_nghi;
    return el("section", {class: "m4-rv-stat"},
      el("div", {class: "m4-card"}, nho("Số đề nghị thanh toán"), el("div", {class: "m4-rv-so m4-o", text: deNghi == null ? "—" : money(deNghi) + " ₫"}),
        nho(((r.lop2 && r.lop2.o_de_nghi) || r.lop1.dich || "Không tìm được ô số đề nghị") + (r.lop1.nguon_dich === "NGUOI_CHON" ? " · ô do người chọn" : r.lop1.nguon_dich === "TU_DONG" ? " · máy tự tìm" : ""))),
      el("div", {class: "m4-card"}, nho(integrity ? "Số sheet" : "Ảnh hưởng ước tính"), el("div", {class: "m4-rv-so m4-o", text: integrity ? String(r.lop1.so_sheet ?? "—") : money(r.anh_huong_uoc_tinh || 0) + " ₫"}),
        nho(integrity ? "Chỉ Lớp 1 · Chưa đối chiếu BOQ" : `${dinhLuong} phát hiện định lượng · Chưa gồm VAT · ước tính của thuật toán nguồn, không phải số được chấp nhận`)),
      el("div", {class: "m4-card"}, nho("Phát hiện cần xem"), el("div", {class: "m4-rv-so", text: String(r.so_phat_hien || 0)}),
        el("div", {class: "m4-rv-hang"}, dem.Cao ? badge(`${dem.Cao} cao`, "danger") : null, dem["Trung bình"] ? badge(`${dem["Trung bình"]} trung bình`, "warning") : null,
          dem["Thấp"] ? badge(`${dem["Thấp"]} thấp`, "neutral") : null, !r.so_phat_hien ? badge("Không có", "success") : null)));
  }
  function coveragePanel(r) {  // companion bắt buộc §10: cùng ngữ nghĩa với kết quả lưu + báo cáo tải về
    const cov = r.coverage || {}, ma = Object.keys(cov);
    const xau = ma.filter(m => !["CHECKED", "NOT_ELIGIBLE", "KHONG_AP_DUNG"].includes(cov[m].trang_thai));
    return el("section", {class: "m4-card"}, el("h3", {text: `Phạm vi đã kiểm · ${ma.length - xau.length}/${ma.length} mã đủ phạm vi`}),
      xau.length ? el("div", {class: "m4-notice", text: "Mã chưa đủ căn cứ/lỗi KHÔNG được coi là Đạt. Thiếu căn cứ (PL chưa có kiểu GT/tham số/BO, lịch sử đợt trước đã duyệt chưa nối, tham số CHUA_CO, ô đích/bảng không nhận) phải bổ sung hoặc review tay."}) : null,
      bang(["Mã", "Trạng thái kiểm", "Lý do / phạm vi"], ma.map(m => el("tr", {}, td(el("strong", {text: m})), td(ttKiem(cov[m].trang_thai)), td(nho(cov[m].ly_do || ""))))));
  }
  function findingsTable(rows) {  // checks.js findingsTable
    const filtered = rows.filter(r => ui.severity === "all" || r.level === ui.severity);
    const tong = rows.reduce((a, r) => a + (typeof r.amount === "number" && r.code !== "GT" ? r.amount : 0), 0), chua = rows.filter(r => typeof r.amount !== "number").length;
    const loc = el("select", {"aria-label": "Lọc mức độ phát hiện", onchange: ev => { ui.severity = ev.target.value; ve_(); }},
      el("option", {value: "all", text: "Tất cả", selected: ui.severity === "all"}), ["Cao", "Trung bình", "Thấp"].map(l => el("option", {value: l, text: l, selected: ui.severity === l})));
    return el("section", {class: "m4-card"}, el("div", {class: "m4-rv-hang m4-rv-dau"}, el("div", {}, el("h3", {text: `Phát hiện cần xem ${filtered.length}/${rows.length}`}), nho("Bấm vị trí ô để mở bằng chứng và căn cứ đối chiếu")),
      el("label", {class: "m4-nho"}, "Mức độ ", loc)),
      bang(["Mã", "Lớp", "Mức", "Mô tả", "Ảnh hưởng (đồng)", "Vị trí trong file"], filtered.length ? filtered.map(r => el("tr", {},
        td(el("strong", {text: r.id})), td(`Lớp ${r.layer}`), td(pill(r.level)),
        td(el("strong", {text: r.title}), r.item ? nho(r.item) : null, r.detail ? nho(String(r.detail).slice(0, 260)) : null),
        td(el("span", {class: "m4-o", text: typeof r.amount === "number" ? money(r.amount) : "Chưa xác định"})),
        td(el("button", {type: "button", class: "m4-lien-ket", onclick: () => moEv(r)}, r.sheet ? `${r.sheet}!${r.cell}` : (r.cell || "Xem"), " ↗")))) :
        [el("tr", {}, el("td", {colspan: "6"}, el("div", {class: "m4-trong", text: rows.length ? "Không có phát hiện ở mức đã chọn." : "Không có phát hiện ở lớp này."})))]),
      nho(ui.layer === "1" || !kq.ket_qua.ket_qua.lop2 ? "Lớp 1 kiểm tra tính toàn vẹn của tệp." : `Tổng ảnh hưởng ${money(tong)} đồng là tổng các khoản chênh lệch Lớp 2 đã định lượng (chưa VAT, ước tính); ${chua} phát hiện chưa định lượng.`));
  }
  function checksGrid(r) {  // checks.js checksGrid + cột trạng thái kiểm (coverage)
    const rows = r.lop1.bang_k || [], can = rows.filter(x => x.ket_qua_hien_thi !== "Đạt").length;
    return el("section", {class: "m4-card"}, el("h3", {text: `Kiểm tra toàn vẹn K1–K8 · ${can} cần xem/chưa đủ · ${rows.length - can} đạt`}),
      bang(["Mã", "Nội dung kiểm tra", "Kết quả", "Trạng thái kiểm", "Chi tiết", ""], rows.map(x => el("tr", {},
        td(el("strong", {text: x.code})), td(x.ten), td(pill(x.ket_qua_hien_thi)), td(ttKiem(x.trang_thai_kiem), nho(x.ly_do_kiem || "")),
        td(nho(x.chi_tiet + (x.so > 1 ? ` (+${x.so - 1} phát hiện)` : "") + (x.ket_qua_nguon !== x.ket_qua_hien_thi ? ` · nguồn ghi: ${x.ket_qua_nguon}` : ""))),
        td(x.finding ? el("button", {type: "button", class: "m4-lien-ket", onclick: () => moEv((r.phat_hien || []).find(f => f.id === x.finding) || null)}, "Xem") : null)))));
  }
  function lop2Grid(r) {  // checks.js lop2Grid + cột trạng thái kiểm
    const l2 = r.lop2;
    if (!l2) return null;
    if (!l2.chay) return el("section", {class: "m4-card"}, el("h3", {text: "Lớp 2 · Các bước đối chiếu với hợp đồng"}), el("div", {class: "m4-notice m4-notice-loi", text: l2.ly_do || "Lớp 2 chưa chạy được"}));
    const rows = l2.bang_lop2 || [], lech = rows.filter(x => x.ket_qua === "Lệch").length, xem = rows.filter(x => x.ket_qua === "Cần xem").length;
    const v = (x, dv) => (x === null || x === undefined || x === "" ? "—" : typeof x === "number" ? (dv === "đồng" ? money(x) : num(x)) : String(x));
    let nhom = "";
    const body = [];
    for (const x of rows) {
      if (x.nhom !== nhom) { body.push(el("tr", {class: "m4-rv-nhom"}, el("td", {colspan: "7"}, el("strong", {text: x.nhom})))); nhom = x.nhom; }
      body.push(el("tr", {}, td(x.ten, x.ghi ? nho(x.ghi) : null), td(el("span", {class: "m4-o", text: v(x.ho_so, x.don_vi)})), td(el("span", {class: "m4-o", text: v(x.hd, x.don_vi)})),
        td(x.chenh === null || x.chenh === undefined ? "" : el("span", {class: Math.abs(x.chenh) > 1000 ? "m4-loi-chu m4-o" : "m4-o", text: money(x.chenh)})),
        td(pill(x.ket_qua_hien_thi || x.ket_qua)), td(ttKiem(x.trang_thai_kiem), x.ly_do_kiem ? nho(x.ly_do_kiem) : null),
        td(x.finding ? el("button", {type: "button", class: "m4-lien-ket", onclick: () => moEv((r.phat_hien || []).find(f => f.id === x.finding) || null)}, (x.o || x.finding) + " ↗") : nho(x.o || ""))));
    }
    return [el("section", {class: "m4-card"}, el("div", {class: "m4-rv-hang m4-rv-dau"}, el("div", {}, el("h3", {text: "Lớp 2 · Các bước đối chiếu với hợp đồng"}),
      nho(`Theo HĐ + phụ lục hiệu lực tại ngày nghiệm thu ${fmtDate(l2.ngay_nghiem_thu)} · số tiền tính bằng đồng`)),
      el("div", {class: "m4-rv-hang"}, badge(`${rows.length - lech - xem} đạt (theo nguồn)`, "success"), lech ? badge(`${lech} lệch`, "danger") : null, xem ? badge(`${xem} cần xem`, "warning") : null)),
      bang(["Bước kiểm tra", "Theo hồ sơ", "Theo HĐ / CSDL", "Chênh lệch", "Kết quả", "Trạng thái kiểm", "Ô trong hồ sơ"], body)), hangMuc(r)];
  }
  const KHOP_XEM = /^(tên trùng|tên gần đúng)/;
  function hangMuc(r) {  // checks.js hangMuc — ghép tay nối review/ghep (đích BOQ typed hiện hành + lý do), Chạy lại nối review/chay-lai
    const dsHm = (r.lop2 && r.lop2.doi_chieu_hm) || [];
    if (!dsHm.length) return null;
    const loi = dsHm.filter(h => h.loi && h.loi.length), ghepCan = dsHm.filter(h => !h.ma_hm && h.ung_vien && h.ung_vien.length), xemLai = dsHm.filter(h => h.ma_hm && KHOP_XEM.test(h.khop || ""));
    const het = (ui.hmLoc === "ghep" && !ghepCan.length) || (ui.hmLoc === "xem" && !xemLai.length);
    const loc = (!het && ui.hmLoc) || (ghepCan.length ? "ghep" : loi.length ? "loi" : "all");
    const rows = loc === "loi" ? loi : loc === "ghep" ? ghepCan : loc === "xem" ? xemLai : loc === "kn" ? dsHm.filter(h => h.kl_kn) : dsHm;
    const lech = (a, b, eps) => a !== null && a !== undefined && b !== null && b !== undefined && Math.abs(a - b) > eps;
    const cell = (a, b, eps, f = num) => [el("span", {class: "m4-o", text: f(a)}), b !== undefined && lech(a, b, eps) ? nho("HĐ: " + f(b), "m4-loi-chu") : null];
    const cuoi = n => String(n || "").split(" / ").pop();
    const sua = kq.run && kq.run.che_do === "L1_L2" && ["SUCCEEDED", "PARTIAL"].includes(kq.run.trang_thai);
    const chon = h => {
      const uv = h.ung_vien || [];
      const s = el("select", {"aria-label": `Mã HM ghép cho dòng ${h.dong}`, onchange: ev => { ui.ghep[h.khoa] = ev.target.value; genForm += 1; }},
        el("option", {value: "", text: "— mã HM —"}), uv.map(u => el("option", {value: u.ma_hm, selected: ui.ghep[h.khoa] === u.ma_hm,
          text: `${u.ma_hm} · ${cuoi(u.nhom) || "—"} · ĐG ${money(u.don_gia)} · KL ${num(u.kl)} · tên giống ${Math.round(u.ty_le * 100)}%`})));
      const ly = el("input", {type: "text", value: ui.lyDo[h.khoa] || "", placeholder: "Lý do ghép (bắt buộc)", "aria-label": `Lý do ghép dòng ${h.dong}`,
        oninput: ev => { ui.lyDo[h.khoa] = ev.target.value; genForm += 1; }});
      return el("div", {class: "m4-rv-hang"}, s, ly, el("button", {type: "button", disabled: !sua, onclick: () => ghep(h)}, "Ghép"),
        uv.slice(0, 5).map(u => nho(`${u.ma_hm} · ${cuoi(u.nhom) || "—"} · ĐG ${money(u.don_gia)} · KL ${num(u.kl)}${h.dg_hs != null && Math.abs((u.don_gia || 0) - h.dg_hs) <= 0.5 ? " · cùng ĐG" : ""}`)));
    };
    const body = rows.map(h => {
      const pct = h.kl_hd ? (h.kl_lk || 0) / h.kl_hd : null, xem = h.ma_hm && KHOP_XEM.test(h.khop || ""), moGhep = (!h.ma_hm && h.ung_vien && h.ung_vien.length) || ui.doi[h.khoa];
      const khop = h.ghep_tay ? nho(`Đã ghép tay → ${h.ghep_tay} · Chạy lại để cập nhật`, "m4-du-chu")
        : h.khop ? el("div", {class: "m4-nho" + (xem ? " m4-loi-chu" : "")}, h.khop, xem && !ui.doi[h.khoa] ? el("button", {type: "button", class: "m4-lien-ket", onclick: () => { ui.doi[h.khoa] = true; ve_(); }}, " Đổi") : null) : null;
      const kqh = h.loi && h.loi.length ? [pill(h.can_ghep ? "Cần xem" : "Lệch"), nho(h.loi.join("; "))] : [pill("Đạt")];
      return el("tr", {}, td(nho(String(h.dong))), td(el("strong", {class: "m4-ma", text: h.ma_hm || "—"}), h.ma_rieng ? nho("mã " + h.ma_rieng) : null, khop),
        td(h.ten, h.nhom ? nho(h.nhom) : null, moGhep ? chon(h) : null), td(h.dvt || ""), td(cell(h.kl_hd_hs, h.kl_hd, 1e-6)), td(cell(h.dg_hs, h.dg_hd, 0.5, money)),
        td(cell(h.kl_kt, h.kl_kt_db ?? undefined, 1e-6)), td(el("span", {class: "m4-o", text: num(h.kl_kn)})),
        td(el("span", {class: "m4-o" + (pct !== null && pct > 1 + 1e-9 ? " m4-loi-chu" : ""), text: num(h.kl_lk)}), pct !== null ? nho(num(Math.round(pct * 1000) / 10) + "%") : null), td(kqh));
    });
    const maps = (kq.manual_map || []).filter(m => dsHm.some(h => h.khoa === m.khoa_hstt));
    const nhac = maps.length ? el("div", {class: "m4-notice m4-rv-hang"}, `Đã ghép tay ${maps.length} khóa dòng của HĐ này (áp dụng cho các lần chạy sau của CÙNG hợp đồng, dòng cùng khóa — không áp HĐ khác). Chạy lại để cập nhật phát hiện và bảng kiểm.`,
      el("button", {type: "button", class: "m4-chinh", onclick: () => chayLai()}, "▶ Chạy lại kiểm tra"))
      : ghepCan.length ? el("div", {class: "m4-notice"}, el("strong", {text: `${ghepCan.length} dòng cần ghép tay: `}), "tên trùng nhiều hạng mục BOQ mà máy chưa chọn được, hoặc tên chỉ gần giống. Chọn mã HM đúng (xem nhóm/bể, đơn giá, KL) rồi bấm Ghép.") : null;
    const o = (v, t, n) => el("option", {value: v, text: `${t} (${n})`, selected: loc === v});
    const d = el("details", {open: ui.hmMo || ghepCan.length ? true : undefined, ontoggle: ev => { ui.hmMo = ev.target.open; }},
      el("summary", {class: "m4-rv-tom"}, el("h3", {text: "Đối chiếu từng hạng mục: BOQ hiệu lực so với hồ sơ"}),
        nho(`${dsHm.length} hạng mục · ${loi.length} lệch${ghepCan.length ? ` · ${ghepCan.length} cần ghép tay` : ""}${xemLai.length ? ` · ${xemLai.length} máy ghép theo tên trùng/gần đúng` : ""} · ô đỏ ghi số theo HĐ`)),
      el("label", {class: "m4-nho"}, "Hiện ", el("select", {onchange: ev => { ui.hmLoc = ev.target.value; ve_(); }}, ghepCan.length ? o("ghep", "Cần ghép tay", ghepCan.length) : null,
        o("loi", "Hạng mục lệch", loi.length), xemLai.length ? o("xem", "Máy ghép theo tên trùng / gần đúng", xemLai.length) : null, o("kn", "Có KL kỳ này", dsHm.filter(h => h.kl_kn).length), o("all", "Tất cả", dsHm.length))),
      nhac, bang(["Dòng", "Mã HM · khớp bằng", "Tên công việc", "ĐVT", "KL HĐ", "Đơn giá", "KL kỳ trước", "KL kỳ này", "KL lũy kế · % KL HĐ", "Kết quả"],
        body.length ? body : [el("tr", {}, el("td", {colspan: "10"}, el("div", {class: "m4-trong", text: "Không có hạng mục ở bộ lọc này."})))], "m4-bang-rong"));
    return el("section", {class: "m4-card"}, d);
  }
  function traceTree(cay, compact) {  // checks.js traceTree — cây theo thứ tự duyệt sâu, có cấp
    if (!cay || !cay.length) return nho("Không truy vết được số đề nghị (không tìm thấy ô đích). Chạy lại với ô số đề nghị cụ thể — K7 chưa kiểm được.");
    const line = n => el("span", {class: "m4-rv-dong"}, el("span", {}, el("strong", {text: n.o || ""}), " ", el("span", {class: "m4-nho", text: String(n.ten || "").slice(0, 90)}),
      n.loai && n.loai !== "Công thức" ? [" ", badge(n.loai, /tay|ngoài|lỗi/i.test(n.loai) ? "warning" : "neutral")] : null),
      el("strong", {class: "m4-o", text: typeof n.gia_tri === "number" ? money(n.gia_tri) + " ₫" : String(n.gia_tri ?? "")}));
    const extra = n => [n.cong_thuc ? nho(n.cong_thuc, "m4-rv-ct") : null, n.tai_lieu || n.ghi ? nho([n.tai_lieu, n.ghi].filter(Boolean).join(" · "), "m4-loi-chu") : null];
    let i = 0;
    const build = cap => {
      const out = [];
      while (i < cay.length && cay[i].cap === cap) {
        const n = cay[i++];
        if (i < cay.length && cay[i].cap > cap) {
          const open = !compact ? cap < 2 : cap < 1;
          out.push(el("details", {open: open || undefined}, el("summary", {}, line(n)), extra(n), el("div", {class: "m4-rv-nhanh"}, build(cay[i].cap))));
        } else out.push(el("div", {}, line(n), extra(n)));
      }
      return out;
    };
    const all = [];
    while (i < cay.length) { const truoc = i; all.push(...build(cay[i].cap)); if (i === truoc) i++; }
    return el("div", {class: "m4-rv-cay"}, all, nho(`Bấm từng nhánh để mở/đóng. ${cay.length} ô trong cây hình thành số đề nghị.`));
  }
  function evidence(r) {  // checks.js evidence drawer → panel trong vùng Review
    if (!r) return null;
    const res = kq.ket_qua.ket_qua;
    return el("aside", {class: "m4-card m4-rv-ev", "aria-label": "Bằng chứng phát hiện"},
      el("div", {class: "m4-rv-hang m4-rv-dau"}, el("h3", {text: `${r.id} · ${String(r.title).slice(0, 80)}`}), el("button", {type: "button", onclick: () => moEv(null)}, "Đóng")),
      el("div", {class: "m4-rv-hang"}, pill(r.level), nho(`Lớp ${r.layer}${r.so_o > 1 ? ` · ${r.so_o} ô cùng lỗi` : ""}`)),
      el("h4", {text: "Vị trí phát hiện"}), el("strong", {text: r.sheet ? `${r.sheet}!${r.cell}` : (r.cell || "—")}), nho(res.tep || ""),
      r.item ? nho("Hạng mục: " + r.item) : null, r.formula || r.value ? el("div", {class: "m4-rv-ct2", text: (r.formula || "") + (r.formula && r.value ? `  = ${r.value}` : (r.value || ""))}) : null,
      r.detail ? nho(r.detail) : null,
      el("h4", {text: r.layer === 2 ? "Đối chiếu BOQ / phụ lục" : "Đối chiếu nguồn trong Excel"}),
      el("div", {class: "m4-rv-hang"}, el("div", {}, nho("Trong hồ sơ"), el("strong", {text: r.actual == null ? "—" : String(r.actual)})),
        el("div", {}, nho(r.layer === 2 ? "Căn cứ cần đối chiếu" : "Phép kiểm tra"), el("strong", {text: r.expected == null ? "—" : String(r.expected)}))),
      nho("Nguồn: " + (r.source || "")), r.reference ? nho(r.reference) : null, res.lop2 && res.lop2.ngay_nghiem_thu ? nho("Ngày áp dụng: " + fmtDate(res.lop2.ngay_nghiem_thu)) : null,
      r.layer === 2 ? el("div", {class: "m4-rv-hang"}, nutCanCu("BOQ", "Xem BOQ căn cứ", r), nutCanCu("PL", "Xem phụ lục căn cứ", r)) : null,
      r.layer === 2 ? canCuPanel(r, res) : null,
      el("div", {class: "m4-notice"}, el("strong", {text: typeof r.amount === "number" ? `Ảnh hưởng ước tính: ${money(r.amount)} đồng` : "Cần bổ sung căn cứ"}), " ", r.conclusion || ""),
      el("h4", {text: "Cây hình thành số đề nghị"}), traceTree(res.lop1.cay, true));
  }
  function nutCanCu(loai, t, r) {
    const chon = !!(ui.cc && ui.cc.ev === r && ui.cc.loai === loai);
    return el("button", {type: "button", class: chon ? "m4-chon" : undefined, "aria-pressed": String(chon), onclick: () => xemCanCu(loai, r)}, t);
  }
  function canCuPanel(r, res) {  // "Căn cứ lần chạy": bản chụp BASIS bất biến đã kiểm — chỉ đọc, trong cùng panel bằng chứng
    const c = ui.cc;
    if (!c || c.ev !== r || c.run !== runChon || !kq || !kq.run) return null;
    const vo = (...con) => el("section", {class: "m4-card", "aria-label": "Căn cứ lần chạy", "aria-busy": c.trang === "DANG" ? "true" : undefined},
      el("h4", {text: `Căn cứ lần chạy · ${c.loai === "PL" ? "Phụ lục" : "BOQ"}`}), ...con);
    if (c.trang === "DANG") return vo(nho("Đang đọc tệp căn cứ của lần chạy (kiểm độ dài + SHA-256)…"));
    if (c.trang !== "OK" || !c.co) return vo(el("div", {class: "m4-notice m4-notice-loi", role: "alert"}, el("strong", {text: "Chưa hiển thị được căn cứ lần chạy."}), " ", c.ly_do || ""),
      c.a ? nho("Tệp gốc vẫn tải được bằng nút ⭳ Căn cứ JSON (máy chủ kiểm quyền hiện hành).") : null);
    const co = c.co, run = kq.run, hd = co.hop_dong, dot = co.dot, tep = co.tep, l2 = co.che_do === "L1_L2";
    const o = (nhan, gt) => el("div", {class: "m4-rv-o"}, nho(nhan), el("strong", {class: "m4-o", text: gt}));
    const ngayNt = dot && typeof dot.ngay_nghiem_thu === "string" && dot.ngay_nghiem_thu ? fmtDate(dot.ngay_nghiem_thu) : gtLuu(dot, "ngay_nghiem_thu");
    const thieu = [];
    if (l2) {
      if (!hd) thieu.push("hồ sơ HĐ");
      if (co.phu_luc == null) thieu.push("phụ lục");
      if (co.boq == null) thieu.push("BOQ");
      if (co.truoc_da_duyet == null) thieu.push("trạng thái lịch sử đợt trước");
    }
    const td_ = co.truoc_da_duyet;
    return vo(nho("Bản chụp bất biến đã dùng cho lần chạy này (đúng như đã lưu) — không phải dữ liệu HĐ đang mở. Review không xét lại phụ lục áp dụng, NT/TT hay số tiền ở đây."),
      el("div", {class: "m4-rv-hang"},
        o("Lần chạy", String(run.id)), o("SHA-256 căn cứ", String(run.basis_sha256)), o("Độ dài", `${c.a.byte_length} byte · đã kiểm độ dài + SHA-256`),
        o("Hợp đồng (lúc chạy)", hd ? `${gtLuu(hd, "so_hop_dong")} · revision ${gtLuu(hd, "revision")} · rev tham số ${gtLuu(hd, "rev_tham_so")} · trạng thái PL ${gtLuu(hd, "trang_thai_pl")}`
          : l2 ? "Căn cứ không có hồ sơ HĐ" : "Không áp dụng (chỉ Lớp 1)"),
        o("Đợt · ngày nghiệm thu", dot ? `Đợt ${gtLuu(dot, "so_dot")} · NT ${ngayNt} · ${gtLuu(dot, "trang_thai")} · revision ${gtLuu(dot, "revision")}` : "Không có đợt"),
        o("Phạm vi", `${co.che_do === "L1_L2" ? "L1 + L2" : "Chỉ L1"} · ô đích ${co.o_dich || "tự tìm"} · dự án ${gtLuu(co, "du_an_id")} · pháp nhân ${gtLuu(co, "phap_nhan_id")}`),
        o("Tệp hồ sơ", `${gtLuu(tep, "ten_goc")} · raw ${String(tep.raw_sha256 || "").slice(0, 12)}…`), o("Phiên bản căn cứ", co.phien_ban)),
      thieu.length ? el("div", {class: "m4-notice"}, ttKiem("INCOMPLETE"), ` Căn cứ lưu của lần chạy này không có mục: ${thieu.join(", ")} — hiển thị là chưa đủ; không coi là 0/trống, không lấy từ dữ liệu hiện tại.`) : null,
      laO(td_) ? nho(`Lịch sử đợt trước đã duyệt (như đã lưu): ${gtLuu(td_, "trang_thai")}${td_.ly_do ? " — " + td_.ly_do : ""}`) : null,
      !l2 ? nho("Lần chạy chỉ Lớp 1 — căn cứ không chứa HĐ/phụ lục/BOQ.") : c.loai === "PL" ? canCuPl(co, res) : canCuBoq(co));
  }
  function canCuBoq(co) {
    if (co.boq == null) return el("div", {class: "m4-notice"}, ttKiem("INCOMPLETE"), " Căn cứ lần chạy này không có mục BOQ — chưa hiển thị; không coi là 0 dòng.");
    if (!co.boq.length) return nho("Căn cứ ghi nhận 0 bảng BOQ lúc chạy.");
    const pls = Array.isArray(co.phu_luc) ? co.phu_luc : [];
    const nguon = b => b.phu_luc_id === null ? "BOQ gốc HĐ (phu_luc_id NULL)" : !coTruong(b, "phu_luc_id") ? "nguồn: (không có trường phu_luc_id)"
      : (p => p ? `PL ${gtLuu(p, "so_pl")} (trạng thái lưu ${gtLuu(p, "trang_thai")})` : `phụ lục ${String(b.phu_luc_id)} — không có trong mục phụ lục của căn cứ`)(pls.find(p => p.id === b.phu_luc_id));
    let con = CC_TOI_DA_DONG, an = 0;
    const out = [];
    for (const b of co.boq) {
      out.push(el("div", {class: "m4-rv-hang m4-rv-dau"}, el("strong", {text: `BOQ lần ${gtLuu(b, "lan")} · ${nguon(b)}`}),
        nho(`sheet ${gtLuu(b, "sheet")} · hàng tiêu đề ${gtLuu(b, "hang_tieu_de")} · so_dong ${gtLuu(b, "so_dong")} · trạng thái lưu ${gtLuu(b, "trang_thai")} · tệp raw ${String(b.raw_sha256 || "").slice(0, 12)}… · cột ${gtLuu(b, "cot")}`)));
      if (b.dong == null) { out.push(el("div", {class: "m4-notice"}, ttKiem("INCOMPLETE"), " Bảng này không có dòng trong căn cứ đã lưu — chưa hiển thị; không coi là 0 dòng.")); continue; }
      if (!b.dong.length) { out.push(nho("0 dòng lưu trong căn cứ.")); continue; }
      const hien = b.dong.slice(0, Math.max(con, 0));
      con -= hien.length; an += b.dong.length - hien.length;
      if (hien.length) out.push(bang(CC_DONG_NHAN, hien.map(d => el("tr", {}, CC_DONG.map(k => td(el("span", {class: ["dong", "kl", "don_gia", "thanh_tien"].includes(k) ? "m4-o" : undefined, text: gtLuu(d, k)}))))), "m4-bang-rong"));
      if (hien.length < b.dong.length) out.push(el("div", {class: "m4-notice", role: "status"}, ttKiem("LIMITED"),
        ` Bảng này đang hiển thị ${hien.length}/${b.dong.length} dòng (giới hạn ${CC_TOI_DA_DONG} dòng mỗi lần xem) — CHƯA hiển thị đủ; tải ⭳ Căn cứ JSON để xem toàn bộ.`));
    }
    return el("div", {}, an ? el("div", {class: "m4-notice", role: "status"}, ttKiem("LIMITED"), ` Chưa hiển thị đủ: ẩn ${an} dòng BOQ do giới hạn hiển thị.`) : null, out);
  }
  function canCuPl(co, res) {
    const l2 = res && res.lop2, ap = l2 && Array.isArray(l2.phu_luc_ap_dung) ? l2.phu_luc_ap_dung : null, chua = l2 && Array.isArray(l2.phu_luc_chua_ap_dung) ? l2.phu_luc_chua_ap_dung : null;
    const ten = ds_ => ds_.length ? ds_.map(p => String((p && p.so_pl) ?? "?")).join(", ") : "không có";
    const kq_ = ap || chua ? nho(`Theo kết quả đã lưu của lần chạy: áp dụng ${ap ? ten(ap) : "(không ghi)"} · chưa áp dụng ${chua ? ten(chua) : "(không ghi)"}.`)
      : nho("Kết quả đã lưu của lần chạy không ghi danh sách phụ lục áp dụng — không suy lại ở đây.");
    if (co.phu_luc == null) return el("div", {}, kq_, el("div", {class: "m4-notice"}, ttKiem("INCOMPLETE"), " Căn cứ lần chạy này không có mục phụ lục — chưa hiển thị; không coi là không có phụ lục."));
    if (!co.phu_luc.length) return el("div", {}, kq_, nho("Căn cứ ghi nhận 0 phụ lục lúc chạy."));
    const hien = co.phu_luc.slice(0, CC_TOI_DA_PL);
    return el("div", {}, kq_,
      bang(["Số PL", "Ngày ký", "Ngày hiệu lực (đã lưu)", "Trạng thái (đã lưu)", "Đổi BOQ", "Tệp PL", "Mã PL"], hien.map(p => el("tr", {},
        td(el("strong", {text: gtLuu(p, "so_pl")})), td(gtLuu(p, "ngay_ky")), td(gtLuu(p, "ngay_hieu_luc")), td(gtLuu(p, "trang_thai")), td(gtLuu(p, "doi_boq")),
        td(nho(gtLuu(p, "tep_id"))), td(nho(gtLuu(p, "id")))))),
      hien.length < co.phu_luc.length ? el("div", {class: "m4-notice", role: "status"}, ttKiem("LIMITED"),
        ` Đang hiển thị ${hien.length}/${co.phu_luc.length} phụ lục (giới hạn ${CC_TOI_DA_PL}) — CHƯA hiển thị đủ; tải ⭳ Căn cứ JSON để xem toàn bộ.`) : null);
  }
  function exportButtons() {  // checks.js exportButtons → tệp đã đăng ký (H/độ dài) của đúng lần chạy, tải qua quyền hiện hành
    const art = (kq && kq.artifact) || [];
    const nhan = {REPORT_L2: "Báo cáo Lớp 2", REPORT_L1: "Báo cáo Lớp 1", REPORT_L2_NGUON: "Lớp 2 (bản nguồn)", REPORT_L1_NGUON: "Lớp 1 (bản nguồn)", RESULT: "Kết quả JSON", BASIS: "Căn cứ JSON", LOG: "Nhật ký tính"};
    // FIX03 F3: flatMap — MỘT mảng phẳng các nút thật (mỗi artifact đã đăng ký ↔ một nút gọi tai(a)); el() chỉ làm phẳng một mức nên mảng lồng
    // hai mức trước đây bị chuyển thành chuỗi "[object HTMLButtonElement]" thay vì nút. Giữ thứ tự loại/nhãn/kiểu của nguồn.
    return el("div", {class: "m4-rv-hang"}, ["REPORT_L2", "REPORT_L1", "REPORT_L2_NGUON", "REPORT_L1_NGUON", "RESULT", "BASIS", "LOG"].flatMap(l => art.filter(a => a.loai === l).map(a =>
      el("button", {type: "button", class: l.startsWith("REPORT_L") && !l.endsWith("NGUON") ? "m4-chinh" : "", onclick: () => tai(a)}, "⭳ " + (nhan[l] || l)))));
  }
  function historyPanel() {  // checks.js historyPanel → lịch sử lần chạy bất biến (cha/con)
    const runs = (ds && ds.runs) || [];
    if (!runs.length) return null;
    return el("section", {class: "m4-card"}, el("div", {class: "m4-rv-hang m4-rv-dau"}, el("h3", {text: "Kết quả đã lưu"}), nho(`${runs.length} lượt gần nhất · bất biến · quyền đọc theo vai hiện hành`)),
      bang(["Thời gian", "Hồ sơ", "Chế độ / đợt", "Trạng thái", "Phạm vi", ""], runs.map(d => {
        const cov = d.coverage || {}, ma = Object.keys(cov), du = ma.filter(m => ["CHECKED", "NOT_ELIGIBLE", "KHONG_AP_DUNG"].includes(cov[m].trang_thai)).length;
        const dot = (ctx.dots || []).find(x => x.id === d.dot_id);
        return el("tr", {}, td(nho(String(d.tao_luc || "").replace("T", " ").slice(0, 19))), td(d.ten_goc || "", nho(`raw ${String(d.raw_sha256).slice(0, 10)}… · ${d.tao_boi} (${d.quyen})`)),
          td(d.che_do === "L1_L2" ? "L1 + L2" : "Chỉ L1", nho(dot ? `Đợt ${dot.so_dot}` : "")), td(ttRun(d.trang_thai), d.parent_run_id ? nho("chạy lại") : null),
          td(ma.length ? `${du}/${ma.length}` : "—"), td(el("button", {type: "button", disabled: runChon === d.id, onclick: () => moRun(d.id)}, runChon === d.id ? "Đang xem" : "Mở")));
      })));
  }

  // ------------------------------------------------------------------ màn hình (renderPayments/renderIntegrity nguồn)
  function ve_() {
    if (!box || !box.isConnected) return;
    const st = el("p", {class: "m4-rv-status m4-status", role: "status", "aria-live": "polite"});
    const out = [el("div", {class: "m4-rv-dau m4-rv-hang"}, el("div", {}, el("h3", {text: "Kiểm tra đợt thanh toán · Review L1/L2"}),
      nho("Review số đề nghị theo hai lớp: toàn vẹn Excel và đối chiếu HĐ, phụ lục, BOQ. Kết quả là phát hiện kỹ thuật — không phải duyệt/PDF/nghiệm thu/thanh toán.")),
      el("div", {class: "m4-rv-hang"}, el("button", {type: "button", onclick: () => { kq = null; runChon = null; ui.formMo = true; ui.ev = null; boCc(); genForm += 1; ve_(); }}, "＋ Kiểm tra đợt mới"),
        kq && kq.ket_qua ? exportButtons() : null, el("button", {type: "button", onclick: () => { napDs(); if (runChon) moRun(runChon); }}, "↻"))), st];
    if (guiLai) out.push(el("div", {class: "m4-hang"}, "Chưa rõ kết quả lần gửi trước. ", el("button", {type: "button", class: "m4-chinh", onclick: async () => {
      const g = guiLai; if (!g || !g.f()) { guiLai = null; ve_(); trangThai("Lệnh chưa rõ kết quả thuộc ngữ cảnh cũ — không gửi lại.", true); return; }
      const gf = genForm, r = await lenh(g.path, g.body, g.ok, g.f, gf); if (r && g.f() && gf === genForm) { await napDs(); moSauLenh(r, g.f, gf); }
    }}, "Gửi lại y nguyên (cùng khóa)")));
    if (dsLoi && !ds) out.push(el("div", {class: "m4-notice m4-notice-loi", text: dsLoi}));
    if (!kq || ui.formMo) out.push(cheDo(), form());
    if (runChon && !kq) out.push(el("p", {class: "m4-trong", text: "Đang tải kết quả…"}));
    if (kq && kq.ket_qua) {
      const res = kq.ket_qua.ket_qua, run = kq.run, integrity = !res.lop2;
      if (res.trang_thai === "FAILED") out.push(el("div", {class: "m4-notice m4-notice-loi", role: "alert"}, el("strong", {text: "Không kiểm tra được hồ sơ"}), " ", res.loi || run.ly_do || ""));
      else {
        if (run.trang_thai === "STALE") out.push(el("div", {class: "m4-notice", text: run.ly_do || "Căn cứ đã đổi trong lúc tính — kết quả chỉ là bằng chứng, không hiện hành. Bấm Chạy lại."}));
        out.push(el("section", {class: "m4-card m4-rv-hang m4-rv-dau"}, el("div", {}, el("strong", {text: res.tep}),
          nho(`${run.che_do === "L1_L2" ? "L1 + L2" : "Chỉ L1"} · raw ${String(run.raw_sha256).slice(0, 12)}… · căn cứ ${String(run.basis_sha256).slice(0, 12)}… · ${res.engine} · lúc ${String(run.xong_luc || run.tao_luc || "").replace("T", " ").slice(0, 19)} · ${run.tao_boi}`)),
          el("div", {class: "m4-rv-hang"}, ttRun(run.trang_thai), el("button", {type: "button", onclick: () => { ui.formMo = !ui.formMo; ve_(); }}, "✎ Kiểm tra hồ sơ khác"),
            ["SUCCEEDED", "PARTIAL", "STALE", "FAILED"].includes(run.trang_thai) ? el("button", {type: "button", onclick: () => chayLai()}, "▶ Chạy lại (cùng tệp gốc)") : null)));
        if (res.lop2 && res.lop2.chay) out.push(scope(res.lop2, run));
        out.push(summary(res, integrity), coveragePanel(res));
        if (ui.layer !== "1") { const g = lop2Grid(res); if (g) out.push(...[].concat(g)); }
        const ph = res.phat_hien || [], dem1 = ph.filter(f => f.layer === 1).length, dem2 = ph.filter(f => f.layer === 2).length;
        const rows = ph.filter(r => ui.layer === "all" || String(r.layer) === ui.layer);
        out.push(el("div", {class: "m4-tabs", role: "tablist", "aria-label": "Lớp kiểm tra"}, [["all", "Tất cả phát hiện", ph.length], ["1", "Lớp 1 · Toàn vẹn file", dem1], ...(integrity ? [] : [["2", "Lớp 2 · HĐ/PL/BOQ", dem2]])].map(([k, l, n]) =>
          el("button", {type: "button", role: "tab", "aria-selected": String(ui.layer === k), class: ui.layer === k ? "m4-chon" : "", onclick: () => { ui.layer = k; ui.severity = "all"; boCc(); ve_(); }}, `${l} ${n}`))));
        out.push(findingsTable(rows));
        if (ui.layer === "1" || integrity) out.push(checksGrid(res));
        out.push(el("section", {class: "m4-card"}, el("h3", {text: `Truy vết số đề nghị thanh toán · ${(res.lop1.cay || []).length} ô nguồn`}), traceTree(res.lop1.cay)));
        if (ui.ev) out.push(evidence(ui.ev));
      }
    }
    const h = historyPanel();
    if (h) out.push(h);
    out.push(nho("Chưa nối ở gói M4-02A: Lớp 3 (C01–C09), OCR/AI, duyệt reviewer + PDF ký, nghiệm thu–công nợ, Request thanh toán; phụ lục có kiểu GT/tham số/BO; lịch sử đợt trước đã được duyệt."));
    box.replaceChildren(...out.filter(Boolean));
  }

  // ------------------------------------------------------------------ đổi vai (người tham gia seam chung) + cầu nối shell M4
  function xoa() {  // đồng bộ, trước await đầu tiên của lần đổi vai ở BẤT KỲ selector nào
    ep += 1; ds = null; kq = null; runChon = null; dsLoi = null; guiLai = null; khoaMap.clear(); genForm += 1;
    sel.dot = null; sel.tep = null; sel.o_dich = ""; ui.ev = null; ui.ghep = {}; ui.lyDo = {}; ui.doi = {}; boCc();
    if (box) box.replaceChildren(el("p", {class: "m4-trong", text: "Đang tải…"}));
  }
  K.dangKyVai("m4_review", xoa, () => { if (vungSong()) { napDs(); if (runChon) moRun(runChon); } });
  function tat() {  // FIX01 R7: shell gọi ĐỒNG BỘ ngay lúc ý định đổi tab/HĐ/đợt/unmount — mọi GET/POST/tải/blob về muộn bị fence chặn
    ep += 1; genDs += 1; genCt += 1; genForm += 1; hoatDong = false; guiLai = null; box = null; boCc();
    // khoaMap giữ nguyên: bấm lại ĐÚNG lệnh cũ (cùng route + body gốc) ở cùng HĐ/vai dùng lại khóa cũ → máy chủ trả FINAL, không tạo khóa mới
  }
  window.kttM4Review = Object.freeze({
    // shell M4 gọi khi vẽ tab Review: ngữ cảnh do máy chủ trả (HĐ đang mở, đợt trong phạm vi, vai hiện hành) — không lấy từ trình duyệt khác
    ve(vung, c) {
      const doi = !ctx || ctx.hdId !== c.hdId || ctx.nguoi !== c.nguoi || (ctx.dotId || null) !== (c.dotId || null), moLai = !hoatDong;
      box = vung; hoatDong = true;
      if (doi) { xoa(); ctx = c; if (c.dotId && (c.dots || []).some(d => d.id === c.dotId)) sel.dot = c.dotId; }
      else ctx = {...ctx, ...c};
      ve_();
      if (doi || moLai || !ds) napDs();
      if (!doi && moLai && runChon) moRun(runChon);
    },
    tat,
  });
  if (typeof window.kttM4ReviewSanSang === "function") window.kttM4ReviewSanSang();
})();
