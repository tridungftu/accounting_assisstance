"use strict";
// M4-02B — màn Chứng từ L3 trong tab "Chứng từ L3" của Cổng hồ sơ M4. Bố cục/thao tác lấy từ màn nguồn `review_goc/giao_dien/chung_tu.js`
// (load 18, tao 49, dsBo 68, chiTiet 80 — phát hiện C01–C09 / ma trận hạng mục × chứng từ / chứng từ đã đọc + dòng hàng, taiVaChay 130, capNhat 165,
// change 175, action 196). Thích nghi DUY NHẤT phần nối: chuỗi HTML nguồn → dựng DOM (textContent, không innerHTML); API nguồn (/api/chung_tu, việc RAM,
// JSON toàn cục, xóa bộ) → route hiện hành /api/m4/chung-tu (token X-KTT-Token + cookie phiên). Bộ tệp = tệp đã gắn đợt trong M4 (tải/bổ sung qua đúng
// portal hiện có ở tab Đợt — không upload song song); KHÔNG có nút xóa bộ (DELETE nguồn), không danh sách JSON toàn cục. Sửa loại/số/ngày/bỏ → revision
// metadata mới (không ghi đè); ghép tay dòng → đích BOQ hiệu lực; Chạy lại → lần chạy con. Thêm cột "Trạng thái kiểm" (coverage) và vị trí vật lý.
// Đổi vai qua cổng chung window.kttChung (người tham gia "m4_chung_tu"); fence epoch/vai/PN/dự án/HĐ/đợt/lần chạy/thế hệ ngữ cảnh/GET sau MỌI await.
// FIX01: nháp sửa/ghép là trạng thái theo trường (không bump thế hệ ngữ cảnh mỗi phím, không vẽ lại cả form khi gõ — nút Lưu bật/tắt tại chỗ); lệnh mang
// hàm hoàn tất gắn với ĐÚNG body đã gửi (ACK/gửi lại cùng khóa chỉ dọn đúng giá trị đã gửi, giữ nháp mới); chi tiết/tải gắn đúng run đang hiển thị;
// GET về muộn sau khi người dùng đã sửa không vẽ đè/không báo lỗi (trừ thu hồi quyền 403/404 — xử lý có chủ ý); ma trận dùng so sánh typed theo hạng mục.
// FIX02A: continuation chạy/chạy lại/sửa/ghép mang fence GỐC qua mọi await (GET làm mới, GET chi tiết, vẽ, toast, dọn nháp); đích đang bay có phạm vi
// (vai|PN|dự án|HĐ|đợt|run + nhãn) và token riêng từng lần gửi — chỉ chủ token nhả; lệnh chưa rõ giữ theo ý định (route/body/khóa/đích/phạm vi) qua đổi
// đợt/vai/tab, chỉ hiện + gửi lại ở đúng phạm vi; dấu ✓/✗ lượng theo dung sai nguồn max(1e-3, |đối chiếu|·1e-6) trên toán hạng của so sánh typed.
// FIX02A-R5/R6: đích đang bay và bản ghi khóa KHÔNG bị xóa khi đổi đợt/vai/tab (đã có phạm vi đầy đủ → không rò sang ngữ cảnh khác; quay lại ĐÚNG
// ngữ cảnh A–B–A vẫn bị chặn, không sinh khóa thứ hai cho cùng đích). Ý định chưa rõ ở lại `treo` suốt lần Gửi lại (đánh dấu `bay` = token lần gửi
// lại) — chỉ kết quả RÕ của đúng chủ token mới gỡ; chưa rõ lần nữa thì giữ nguyên bản ghi/khóa/body gốc. Mỗi khóa đã phát có bản ghi `treo` riêng.
(() => {
  const K = window.kttChung;
  if (!K) return;
  const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || "";
  const nf3 = new Intl.NumberFormat("vi-VN", {maximumFractionDigits: 3}), nf0 = new Intl.NumberFormat("vi-VN", {maximumFractionDigits: 0});
  const num = v => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? "—" : nf3.format(Number(v)));
  const money = v => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? "—" : nf0.format(Math.round(Number(v))));
  const fmtDate = iso => { if (!iso) return "—"; const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? `${m[3]}/${m[2]}/${m[1]}` : String(iso); };
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
  const KIND = {success: "m4-du", warning: "m4-thieu", danger: "m4-loi", neutral: "m4-xam", info: "m4-xam"};
  const badge = (label, kind = "neutral") => el("span", {class: "m4-pill " + (KIND[kind] || "m4-xam"), text: label});
  const MUC = {Cao: "danger", "Trung bình": "warning", Thấp: "info"};
  const TT_KIEM = {CHECKED: ["Đã kiểm", "success"], LIMITED: ["Kiểm có giới hạn", "warning"], NOT_AVAILABLE: ["Không có số liệu", "neutral"],
    INCOMPLETE: ["Chưa đủ căn cứ", "warning"], ERROR: ["Lỗi kiểm tra", "danger"], KHONG_AP_DUNG: ["Không áp dụng (có căn cứ)", "neutral"]};
  const ttKiem = t => badge(...(TT_KIEM[t] || [t || "—", "neutral"]));
  const TT_DOC = {CHECKED: ["Đã đọc", "success"], LIMITED: ["Đọc có giới hạn", "warning"], NOT_CONFIGURED: ["Cần OCR/AI — chưa cấu hình", "warning"],
    KHONG_HO_TRO: ["Không đọc được (chưa hỗ trợ)", "danger"], ERROR: ["Lỗi đọc", "danger"]};
  const ttDoc = t => badge(...(TT_DOC[t] || [t || "—", "neutral"]));
  const TT_DONG = {CHECKED: ["Dòng hàng: đã đọc", "success"], LIMITED: ["Dòng hàng: có giới hạn", "warning"], NOT_CONFIGURED: ["Dòng hàng: chưa đọc (cần Local AI)", "warning"],
    KHONG_AP_DUNG: ["Dòng hàng: không áp dụng", "neutral"], KHONG_HO_TRO: ["Dòng hàng: không đọc được", "danger"], ERROR: ["Dòng hàng: lỗi", "danger"]};
  const ttDong = t => (t ? badge(...(TT_DONG[t] || [t, "neutral"])) : null);
  const TT_RUN = {RUNNING: ["Đang chạy", "info"], SUCCEEDED: ["Xong · đủ phạm vi", "success"], PARTIAL: ["Xong · phạm vi chưa đủ", "warning"],
    FAILED: ["Lỗi — không có kết quả", "danger"], STALE: ["Căn cứ đã đổi — không hiện hành", "warning"], CANCELLED: ["Đã hủy", "neutral"], PENDING: ["Chờ", "neutral"]};
  const ttRun = t => badge(...(TT_RUN[t] || [t, "neutral"]));
  const SS = {SO_DUOC: ["so được", "success"], CHUA_SO_DUOC: ["chưa so được", "warning"], NGUON_KHONG_SO: ["nguồn không so", "warning"], KHONG_AP_DUNG: ["không áp dụng", "neutral"]};
  const ttSs = s => (s ? badge(...(SS[s.trang_thai] || [s.trang_thai, "neutral"])) : null);

  // ------------------------------------------------------------------ trạng thái
  // genForm = thế hệ NGỮ CẢNH (đổi đợt/vai/HĐ/tab/hủy); genSua = thế hệ NHÁP (mỗi lần người dùng sửa một trường) — tách để gõ không làm mất ACK
  let ep = 0, genDs = 0, genCt = 0, genForm = 0, genSua = 0;
  let box = null, ctx = null, ds = null, kq = null, runChon = null, dsLoi = null, hoatDong = false, nutLuu = null;
  const sel = {dot: null};
  const ui = {sua: {}, lySua: "", ghep: {}, lyGhep: {}, moRong: {}, doi: {}};
  // đích có phạm vi → token của ĐÚNG lần gửi đang bay (incarnation); chỉ chủ token nhả. KHÔNG xóa khi đổi đợt/vai/tab: khóa đích chứa đủ
  // vai|PN|dự án|HĐ|đợt|run nên không chặn ngữ cảnh khác, còn quay lại đúng ngữ cảnh (A→B→A) vẫn thấy lệnh đang bay → không phát khóa thứ hai
  const dangGui = new Map();
  // ý định CHƯA RÕ kết quả: đích + (route, body) + khóa → {route, body, khóa, đích, phạm vi, hoàn tất gốc, bay}; giữ qua đổi đợt/vai/tab và suốt
  // lần Gửi lại (bay = token lần gửi lại đang bay); chỉ kết quả RÕ của đúng chủ token gỡ
  const treo = new Map();
  const khoaMap = new Map();  // (đích có phạm vi, route, body) → {khóa, chủ} — có phạm vi nên không cần xóa khi đổi vai (không tái dùng khóa giữa vai)
  const taoKhoa = () => "m4ct-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));
  const actor = () => (ctx && ctx.nguoi) || null;
  const vungSong = () => hoatDong && !!box && box.isConnected;
  const khoaNgCanh = () => (ctx ? [ctx.nguoi, ctx.phapNhan || null, ctx.duAnId || null, ctx.hdId].join("|") : "");
  function fence(them) {
    const e = ep, k = khoaNgCanh(), d = sel.dot, gf = genForm;
    return () => e === ep && vungSong() && k === khoaNgCanh() && d === sel.dot && gf === genForm && (!them || them());
  }
  // phạm vi đích = ngữ cảnh + đợt + run (null với lệnh cấp đợt); đích = phạm vi + nhãn — tính MỘT lần lúc ý định, không suy lại khi kết quả về
  const phamVi = run => JSON.stringify([khoaNgCanh(), sel.dot || null, run || null]);
  const idDich = (nhan, run) => phamVi(run) + "#" + nhan;
  const dichCua = (nhan, run, moTa) => ({id: idDich(nhan, run), pv: phamVi(run), dot: phamVi(null), run: run || null, moTa});
  const treoTai = id => [...treo.values()].some(t => t.id === id);
  const coTreo = (nhan, run) => treoTai(idDich(nhan, run));
  const banDich = (nhan, run) => dangGui.has(idDich(nhan, run)) || coTreo(nhan, run);
  const khopPv = t => t.pv === phamVi(t.run ? runChon : null);  // đúng vai/PN/dự án/HĐ/đợt và (nếu gắn run) đúng run đang mở
  class LoiCt extends Error { constructor(status, code, message) { super(message); this.status = status; this.code = code; } }
  async function goi(path, opts = {}) {
    let res;
    try { res = await fetch(path, {...opts, headers: {"X-KTT-Token": TOKEN, ...(opts.headers || {})}, cache: "no-store", credentials: "same-origin"}); }
    catch (_) { throw new LoiCt(0, "MAT_KET_NOI", "Mất kết nối — chưa rõ máy chủ đã ghi hay chưa. Khóa được giữ; bấm Gửi lại y nguyên."); }
    if (!res.ok) { const r = await res.json().catch(() => ({})); throw new LoiCt(res.status, r.error || "HTTP_" + res.status, r.message || `Không hoàn tất (${res.status}).`); }
    return res;
  }
  async function docJson(res) { try { return await res.json(); } catch (_) { throw new LoiCt(0, "KET_QUA_CHUA_RO", "Phản hồi đọc không trọn — chưa rõ kết quả; bấm Gửi lại y nguyên."); } }
  const chuaRo = e => !!e && (e.status === 0 || e.status >= 500) && e.code !== "M4_CHUA_SAN_SANG_GHI_NGUON";
  const thuHoi = e => !!e && (e.status === 403 || e.status === 404);
  function trangThai(msg, loi = false) { const s = box && box.querySelector(".m4-ct-status"); if (s) { s.textContent = msg || ""; s.className = "m4-ct-status m4-status" + (loi ? " m4-loi-chu" : ""); } }
  function xoaNhap() { ui.sua = {}; ui.lySua = ""; ui.ghep = {}; ui.lyGhep = {}; ui.doi = {}; genSua += 1; }

  // lệnh có khóa (mẫu review.js/m4.js C2): bản ghi theo (đích có phạm vi, route, body gốc); lần gửi đang bay → bấm lặp không gửi; chưa rõ → giữ khóa, gửi lại y nguyên.
  // `f` = fence ngữ cảnh tại Ý ĐỊNH GỐC. `xong(r)` = hoàn tất gắn với ĐÚNG body đã gửi — chạy khi kết quả rõ (lần đầu hoặc Gửi lại cùng khóa) và ngữ
  // cảnh còn đúng; nó chỉ dọn phần nháp TRÙNG giá trị đã gửi (sửa mới sau lúc gửi được giữ). `dich` = đích có phạm vi (dichCua) — chính lenh chặn lệnh
  // mới khi đích đang bay hoặc còn ý định chưa rõ (không dựa vào nút bị tắt). `lay` = ý định chưa rõ đang được Gửi lại (cùng route/body/khóa).
  function nhanBanGhi(k, khoa) {
    let rec = khoaMap.get(k);
    if (rec && rec.chu) return null;
    if (!rec || (khoa && rec.khoa !== khoa)) { rec = {khoa: khoa || taoKhoa(), chu: null}; khoaMap.set(k, rec); }
    const ve = {}; rec.chu = ve; return {rec, ve};
  }
  function traBanGhi(k, rec, ve, xong) { if (rec.chu === ve) rec.chu = null; if (xong && khoaMap.get(k) === rec) khoaMap.delete(k); }
  async function lenh(path, body, ok, f, xong, dich, lay) {
    if (!f()) return null;
    if (lay && (lay.bay || treo.get(lay.kt) !== lay)) { trangThai(lay.bay ? "Đang gửi lại lệnh chưa rõ này — chờ kết quả." : "Lệnh chưa rõ này đã có kết quả.", true); return null; }
    if (dangGui.has(dich.id)) { trangThai("Đang gửi lệnh cho cùng đích — chờ kết quả.", true); return null; }
    if (!lay && treoTai(dich.id)) { trangThai("Lệnh trước cho cùng đích chưa rõ kết quả — bấm Gửi lại y nguyên trước khi gửi lệnh mới.", true); return null; }
    const k = dich.id + "\n" + JSON.stringify([path, body]), so = nhanBanGhi(k, lay && lay.khoa);  // bản ghi khóa theo ĐÍCH CÓ PHẠM VI + route + body
    if (!so) { trangThai("Đang gửi yêu cầu này — chờ kết quả."); return null; }
    const {rec, ve} = so, tk = {};
    dangGui.set(dich.id, tk);  // giữ đích ĐỒNG BỘ trước await đầu tiên; token riêng lần gửi này
    if (lay) lay.bay = tk;  // Gửi lại: ý định chưa rõ Ở LẠI treo (không gỡ trước khi rõ) — đổi đợt/vai/tab rồi quay lại vẫn chặn khóa/body mới
    const chuTreo = () => !!lay && lay.bay === tk && treo.get(lay.kt) === lay;
    const nha = () => {  // chỉ chủ token nhả — lần gửi cũ về muộn không mở khóa lần gửi mới / không gỡ ý định mới hơn
      if (dangGui.get(dich.id) === tk) dangGui.delete(dich.id);
      if (lay && lay.bay === tk) lay.bay = null;
    };
    // kết quả về khi ngữ cảnh gốc đã đổi: chỉ vẽ lại nếu đang mở ĐÚNG vai/PN/dự án/HĐ/đợt của ý định (để hiện/gỡ dòng Gửi lại); khác phạm vi → không đụng
    const veLai = t => { if (t && ctx && vungSong() && t.dot === phamVi(null)) ve_(); else capNhatNut(); };
    trangThai(path === "chung-tu/chay" || path === "chung-tu/chay-lai" ? "Đang đọc bộ chứng từ và đối chiếu C01–C09 (có thể mất vài phút)…" : "Đang ghi…");
    let ro = false;
    try {
      const r = await docJson(await goi("/api/m4/" + path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({...body, khoa: rec.khoa})}));
      ro = true;
      const goTreo = chuTreo();
      nha();
      if (goTreo) treo.delete(lay.kt);  // ACK RÕ của đúng lần gửi lại hiện hành: gỡ đúng ý định này
      if (!f()) { veLai(lay); return null; }
      K.toast(ok + (r.lap_lai ? " (kết quả cũ của cùng yêu cầu — không làm lại)" : ""));
      trangThai(ok + (r.lap_lai ? " — biên nhận cũ." : ""));
      if (xong) await xong(r, f);  // hoàn tất nhận fence GỐC — tự kiểm lại sau mỗi await
      return r;
    } catch (e) {
      if (chuaRo(e)) {  // chưa rõ (mất kết nối/5xx/200 JSON cụt): giữ ĐÚNG ý định theo phạm vi gốc kể cả khi đã rời ngữ cảnh — không tạo khóa mới
        let t = lay && treo.get(lay.kt) === lay ? lay : null;  // Gửi lại vẫn chưa rõ: giữ NGUYÊN bản ghi gốc (route/body/khóa/đích/hoàn tất)
        nha();
        if (!t) {  // khóa thao tác nằm trong khóa của treo → mỗi khóa đã phát một bản ghi riêng, không ghi đè/gộp ý định khác khóa dù cùng body
          t = {kt: k + "\n" + rec.khoa, id: dich.id, pv: dich.pv, dot: dich.dot, run: dich.run, moTa: dich.moTa, path, body, ok, xong, khoa: rec.khoa, bay: null};
          treo.set(t.kt, t);
        }
        if (!f()) { veLai(t); return null; }  // ngữ cảnh khác: không vẽ/toast; đang mở lại đúng phạm vi → hiện nút Gửi lại
        K.toast(e.message, true); ve_(); trangThai(e.message, true); return null;
      }
      ro = true;
      const goTreo = chuTreo();
      nha();
      if (goTreo) treo.delete(lay.kt);  // lỗi RÕ của đúng lần gửi lại hiện hành: ý định đã có kết quả
      if (!f()) { veLai(lay); return null; }
      K.toast(e.message, true);
      if (thuHoi(e)) { ds = null; kq = null; runChon = null; xoaNhap(); ve_(); trangThai(e.message, true); napDs(); return null; }  // thu hồi: có chủ ý
      if (lay) ve_();  // Gửi lại đã có kết quả rõ (lỗi): gỡ dòng chưa rõ của ý định này
      trangThai(e.message, true);
      if (e.code === "M4_CHUNG_TU_CO_SO_DOI" || e.code === "M4_REVISION_CU") napDs();
      return null;
    } finally { traBanGhi(k, rec, ve, ro); }
  }

  // ------------------------------------------------------------------ nạp
  // `ngoai` = fence của continuation gốc (chạy/sửa/ghép): GET chỉ phát và kết quả chỉ áp khi ngữ cảnh gốc còn đúng
  async function napDs(ngoai) {
    if (!ctx || !vungSong() || !sel.dot || K.vaiDangChan("m4_chung_tu") || (ngoai && !ngoai())) return;
    const g = ++genDs, gs = genSua, dot = sel.dot, f = fence(() => g === genDs && (!ngoai || ngoai()));
    try {
      const res = await goi("/api/m4/chung-tu?" + new URLSearchParams({dot_id: dot}).toString());
      if (!f()) return;
      const r = await res.json();
      if (!f()) return;
      ds = r; dsLoi = null;
      if (gs === genSua) ve_(); else capNhatNut();  // đang sửa: giữ DOM (focus/nháp), dữ liệu mới dùng ở lần bấm kế tiếp
    } catch (err) {
      if (!f()) return;
      if (thuHoi(err)) { ds = null; kq = null; runChon = null; dsLoi = err.message; xoaNhap(); ve_(); trangThai(err.message, true); return; }
      if (gs !== genSua) return;  // lỗi GET về muộn sau khi người dùng đã sửa: không vẽ đè/không báo
      dsLoi = err.message; ve_(); trangThai(err.message, true);
    }
  }
  async function moRun(id, ngoai) {
    if (!ctx || !vungSong() || K.vaiDangChan("m4_chung_tu") || (ngoai && !ngoai())) return;
    if (!kq || !kq.run || kq.run.id !== id) { kq = null; xoaNhap(); }  // đổi sang run khác: gỡ ngay chi tiết + artifact + nháp của run cũ
    runChon = id;
    const g = ++genCt, gs = genSua, f = fence(() => g === genCt && runChon === id && (!ngoai || ngoai()));
    ve_();
    try {
      const r = await docJson(await goi("/api/m4/chung-tu/" + encodeURIComponent(id)));
      if (!f()) return;
      if (!r || !r.run || r.run.id !== id) { trangThai("Phản hồi chi tiết không đúng lần chạy đã chọn — không hiển thị.", true); return; }
      kq = r;
      if (gs === genSua) ve_(); else capNhatNut();
    } catch (err) {
      if (!f()) return;
      if (thuHoi(err)) { kq = null; runChon = null; xoaNhap(); ve_(); trangThai(err.message, true); return; }
      if (gs !== genSua) return;
      ve_(); trangThai(err.message, true);
    }
  }
  async function tai(a, runId) {  // tải gắn ĐÚNG run + artifact đang hiển thị: fence trước request, sau headers, sau blob, trước click
    const f = fence(() => runChon === runId && !!kq && !!kq.run && kq.run.id === runId);
    if (!f()) return;
    try {
      const res = await goi(`/api/m4/chung-tu/${encodeURIComponent(runId)}/tep/${encodeURIComponent(a.id)}`);
      if (!f()) return;
      const blob = await res.blob();
      if (!f()) return;
      if (!blob.size) { trangThai("Tệp tải về rỗng — không lưu.", true); return; }
      if (a.byte_length && blob.size !== a.byte_length) { trangThai("Tệp tải về khác độ dài đã đăng ký — không lưu.", true); return; }
      const url = URL.createObjectURL(blob), link = el("a", {href: url, download: a.ten});
      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 60000);
      trangThai(`Đã tải ${a.ten} (${blob.size} byte · SHA ${String(a.raw_sha256).slice(0, 12)}…).`);
    } catch (err) {
      if (!f()) return;
      if (thuHoi(err)) { kq = null; runChon = null; xoaNhap(); ve_(); trangThai(err.message, true); return; }
      trangThai(err.message, true);
    }
  }

  // ------------------------------------------------------------------ hành động (taiVaChay / capNhat / action nguồn → route hiện hành)
  // continuation sau ACK: fence GỐC `f` kiểm trước GET làm mới, sau GET (napDs nhận f) và trước khi mở run mới; GET chi tiết mang fence ngữ cảnh gốc
  // (không cần run cũ còn chọn — chạy lại mở run con) → đổi đợt/HĐ/vai/PN/dự án/tab giữa chừng thì không phát request/không hiện chi tiết của ngữ cảnh cũ
  const moSau = async (r, f) => {
    if (!f()) return;
    const fc = fence();
    await napDs(f);
    if (!f() || !ds) return;
    if (r && r.run_id) moRun(r.run_id, fc);
  };
  async function chay() {
    const cs = ds && ds.co_so;
    if (!cs || !cs.san_sang || !cs.basis_sha256) { trangThai((cs && cs.ly_do) || "Chưa có căn cứ hiện hành — bấm ↻ rồi chạy.", true); return; }
    await lenh("chung-tu/chay", {dot_id: sel.dot, revision: cs.revision, expected_basis: cs.basis_sha256}, "Đã đọc và đối chiếu bộ chứng từ", fence(), moSau,
      dichCua("chay", null, "đọc & đối chiếu"));
  }
  async function chayLai() {
    const run = kq && kq.run, cs = ds && ds.co_so;
    if (!run || !cs || !cs.basis_sha256) return;
    await lenh("chung-tu/chay-lai", {run_id: run.id, revision: cs.revision, expected_basis: cs.basis_sha256}, "Đã chạy lại (lần chạy con, giữ lần cũ)",
      fence(() => runChon === run.id), moSau, dichCua("chay-lai", run.id, "chạy lại"));
  }
  const mucSua = () => Object.entries(ui.sua).map(([tep_id, v]) => ({tep_id, ...v})).filter(x => Object.keys(x).length > 1);
  function capNhatNut() { if (nutLuu && nutLuu.isConnected) nutLuu.disabled = !mucSua().length || banDich("sua", runChon); }
  async function luuSua() {  // capNhat nguồn → revision metadata mới (append), rồi người dùng bấm Chạy lại
    const run = kq && kq.run, cs = ds && ds.co_so;
    if (!run || !cs || !cs.basis_sha256) return;
    if (banDich("sua", run.id)) {
      trangThai(dangGui.has(idDich("sua", run.id)) ? "Đang gửi lệnh sửa (hoặc Gửi lại) cho cùng đích — chờ kết quả; chưa gửi lệnh mới."
        : "Lệnh sửa trước chưa rõ kết quả — bấm Gửi lại y nguyên trước khi lưu thêm.", true);
      return;
    }
    const muc = mucSua();
    if (!muc.length) { trangThai("Chưa có sửa nào.", true); return; }
    const ly = String(ui.lySua || "").trim();
    if (!ly) { trangThai("Nhập lý do sửa (ghi lịch sử).", true); return; }
    const gui = muc.map(x => ({...x}));
    const p = lenh("chung-tu/sua", {run_id: run.id, revision: cs.revision, tai_lieu: gui, expected_basis: cs.basis_sha256, ly_do: ly},
      "Đã ghi revision metadata mới — bấm Chạy lại để đối chiếu", fence(() => runChon === run.id), async (r, f) => {
        if (!f()) return;
        for (const m of gui) {  // chỉ dọn đúng giá trị đã gửi; trường sửa tiếp sau lúc gửi (giá trị khác) giữ nguyên
          const s = ui.sua[m.tep_id];
          if (!s) continue;
          for (const [k, v] of Object.entries(m)) if (k !== "tep_id" && k in s && s[k] === v) delete s[k];
          if (!Object.keys(s).length) delete ui.sua[m.tep_id];
        }
        if (String(ui.lySua || "").trim() === ly) ui.lySua = "";
        genSua += 1;
        await napDs(f);
      }, dichCua("sua", run.id, "sửa metadata"));
    capNhatNut();  // lenh đã giữ đích sửa (có phạm vi) đồng bộ trước await đầu tiên → nút Lưu tắt trong lúc chờ
    await p;
    capNhatNut();
  }
  async function ghep(d, ln) {
    const run = kq && kq.run, cs = ds && ds.co_so, res = kq && kq.ket_qua && kq.ket_qua.ket_qua;
    if (!run || !cs || !res) return;
    const nhan = "ghep:" + ln.row_id;
    if (banDich(nhan, run.id)) { trangThai("Lệnh ghép dòng này đang gửi/chưa rõ kết quả — chờ hoặc Gửi lại y nguyên.", true); return; }
    const khoa = String(ui.ghep[ln.row_id] || ""), ly = String(ui.lyGhep[ln.row_id] || "").trim();
    const h = (res.hang_muc || []).find(x => x.khoa === khoa);
    if (!h) { trangThai("Chọn hạng mục đích.", true); return; }
    if (!ly) { trangThai("Nhập lý do ghép tay (ghi lịch sử).", true); return; }
    const ng = h.nguon_boq || [];
    if (ng.length !== 1) { trangThai(ng.length ? "Hạng mục có nhiều dòng BOQ nguồn hiệu lực — chưa chọn được đích duy nhất." : "Hạng mục không có dòng BOQ hiệu lực tại ngày NT — không ghép được.", true); return; }
    await lenh("chung-tu/ghep", {run_id: run.id, row_id: ln.row_id, boq_id: ng[0].boq_id, boq_dong: ng[0].dong, ma_hm: h.ma_hm, revision: cs.revision,
      expected_basis: cs.basis_sha256, ly_do: ly}, `Đã ghép tay → ${h.ma_hm} (áp ở lần Chạy lại)`, fence(() => runChon === run.id), async (r, f) => {
      if (!f()) return;
      if (ui.ghep[ln.row_id] === khoa) delete ui.ghep[ln.row_id];
      if (String(ui.lyGhep[ln.row_id] || "").trim() === ly) { delete ui.lyGhep[ln.row_id]; delete ui.doi[ln.row_id]; }
      genSua += 1;
      await napDs(f);
    }, dichCua(nhan, run.id, `ghép ${ln.ten} → ${h.ma_hm}`));
  }

  // ------------------------------------------------------------------ khối giao diện (port DOM của chung_tu.js nguồn)
  const bang = (cot, rows, cls) => el("div", {class: "m4-bang" + (cls ? " " + cls : "")}, el("table", {}, el("thead", {}, el("tr", {}, cot.map(c => el("th", {text: c})))), el("tbody", {}, rows)));
  const td = (...c) => el("td", {}, ...c);
  const nho = (t, cls) => el("div", {class: "m4-nho" + (cls ? " " + cls : ""), text: t});
  const dau = (ok, title) => el("span", {class: ok === null ? "m4-nho" : ok ? "m4-du-chu" : "m4-loi-chu", title: title || "", text: ok === null ? "—" : ok ? "✓" : "✗"});
  function boChungTu() {  // tao() nguồn → bộ tệp đã gắn đợt (không upload song song) + căn cứ + nút chạy
    const dots = ctx.dots || [];
    const sDot = el("select", {"aria-label": "Đợt thanh toán", onchange: ev => { sel.dot = ev.target.value || null; ds = null; kq = null; runChon = null; genForm += 1; xoaNhap(); ve_(); napDs(); }},
      el("option", {value: "", text: "— chọn đợt —"}), dots.map(d => el("option", {value: d.id, selected: d.id === sel.dot, text: `Đợt ${d.so_dot} · NT ${fmtDate(d.ngay_nghiem_thu)} · ${d.trang_thai === "DA_NOP" ? "đã nộp" : "nháp"}`})));
    const cs = ds && ds.co_so, teps = (ds && ds.tai_lieu) || [];
    const pt = [];
    if (cs && cs.phu_thuoc) for (const [k, v] of Object.entries(cs.phu_thuoc)) pt.push(el("li", {class: v.ok ? "m4-du-chu" : "m4-loi-chu"}, `${v.ok ? "✓" : "✗"} ${k}: ${v.ly_do || ""}`));
    const nut = el("button", {type: "button", class: "m4-chinh", disabled: !(cs && cs.san_sang && cs.basis_sha256), onclick: () => chay()}, "▶ Đọc & đối chiếu bộ chứng từ");
    return el("section", {class: "m4-card"}, el("h3", {text: "Bộ chứng từ của đợt"}),
      nho("BB nghiệm thu KL, BB giao nhận, packing list, CO, CQ, BB lắp đặt / chạy thử đã gắn vào đợt. Bổ sung tệp: tab Đợt & checklist (tải lên + gắn vào đợt) — tệp cũ giữ nguyên."),
      el("div", {class: "m4-form"}, el("label", {}, "Đợt", sDot)),
      sel.dot ? (teps.length ? bang(["Mục", "Tệp", "Loại tệp", "Byte", "Đọc"], teps.map(t => el("tr", {}, td(t.muc || ""), td(t.ten_goc, nho(`raw ${String(t.raw_sha256).slice(0, 12)}…`)),
        td(String(t.media_type).split("/").pop()), td(num(t.byte_length)), td(t.doc === "NATIVE" ? badge("Word/Excel — đọc trực tiếp", "success") : badge("PDF/ảnh — cần OCR/AI (chưa cấu hình)", "warning")))))
        : nho("Đợt chưa có tệp nào được gắn.")) : nho("Chọn đợt."),
      cs ? nho(cs.san_sang ? `Căn cứ hiện hành ${String(cs.basis_sha256).slice(0, 12)}… · quyền ${cs.quyen} · revision metadata ${cs.revision} · ${cs.so_ghep_tay} ghép tay · ${cs.engine}` : cs.ly_do) : null,
      pt.length ? el("ul", {class: "m4-thieu-ds"}, pt) : null,
      el("div", {class: "m4-rv-hang"}, nut, el("span", {class: "m4-nho", text: "Kết quả là phát hiện kỹ thuật L3 — không phải duyệt/PDF đợt/nghiệm thu/công nợ. Không dùng OCR/AI khi chưa cấu hình."})));
  }
  function lichSu() {  // dsBo nguồn → lịch sử lần chạy bất biến (cha/con) + revision metadata + ghép tay
    const runs = (ds && ds.runs) || [], revs = (ds && ds.revisions) || [], maps = (ds && ds.manual_map) || [];
    const out = [];
    if (runs.length) out.push(el("section", {class: "m4-card"}, el("h3", {text: `Các lần chạy (${runs.length})`}),
      bang(["Thời gian", "Revision", "Trạng thái", "Phát hiện", "Phạm vi", ""], runs.map(r => {
        const cov = r.coverage || {}, ma = Object.keys(cov), du = ma.filter(m => ["CHECKED", "KHONG_AP_DUNG"].includes(cov[m].trang_thai)).length;
        return el("tr", {}, td(nho(String(r.tao_luc || "").replace("T", " ").slice(0, 19)), nho(`${r.tao_boi} (${r.quyen})`)), td(String(r.revision)),
          td(ttRun(r.trang_thai), r.parent_run_id ? nho("chạy lại") : null), td(["Cao", "Trung bình", "Thấp"].map(m => (r.dem || {})[m] ? badge(`${r.dem[m]} ${m}`, MUC[m]) : null)),
          td(ma.length ? `${du}/${ma.length}` : "—"), td(el("button", {type: "button", disabled: runChon === r.id, onclick: () => moRun(r.id)}, runChon === r.id ? "Đang xem" : "Mở")));
      }))));
    if (revs.length) out.push(el("section", {class: "m4-card"}, el("h3", {text: "Lịch sử sửa metadata (revision)"}),
      bang(["Revision", "Thay đổi", "Lý do", "Bởi", "Lúc"], revs.map(v => el("tr", {}, td(String(v.revision)), td(nho(JSON.stringify(v.thay_doi).slice(0, 300))), td(v.ly_do || ""), td(v.tao_boi || ""),
        td(nho(String(v.tao_luc || "").replace("T", " ").slice(0, 19))))))));
    if (maps.length) out.push(el("section", {class: "m4-card"}, el("h3", {text: "Ghép tay dòng chứng từ (mọi revision)"}),
      bang(["Dòng", "Revision", "Mã HM", "BOQ dòng", "Lý do", "Bởi"], maps.map(m => el("tr", {}, td(m.ten_dong || "", nho(`${String(m.row_id).slice(0, 12)}…`)), td(String(m.revision)),
        td(m.ma_hm), td(String(m.boq_dong)), td(m.ly_do || ""), td(m.tao_boi || ""))))));
    return out;
  }
  function coveragePanel(res) {
    const cov = res.coverage || {}, ma = Object.keys(cov), xau = ma.filter(m => !["CHECKED", "KHONG_AP_DUNG"].includes(cov[m].trang_thai));
    return el("section", {class: "m4-card"}, el("h3", {text: `Phạm vi đã kiểm · ${ma.length - xau.length}/${ma.length} mục đủ phạm vi`}),
      xau.length ? el("div", {class: "m4-notice", text: "Mục chưa đủ căn cứ/lỗi KHÔNG được coi là Đạt — ít phát hiện không có nghĩa là đủ hồ sơ (thiếu BB nghiệm thu/giao nhận, lượng, ngày, ĐVT, tệp/dòng chưa đọc được, chưa có L2 hiện hành)."}) : null,
      bang(["Mã", "Trạng thái kiểm", "Lý do / phạm vi"], ma.map(m => el("tr", {}, td(el("strong", {text: m})), td(ttKiem(cov[m].trang_thai)), td(nho(cov[m].ly_do || "")))))) ;
  }
  function phatHien(res) {  // chiTiet nguồn mục 1 + ghi chú L3 riêng (finding nguồn không sửa)
    const ph = res.phat_hien || [], ghi = {};
    for (const x of res.chu_thich_phat_hien || []) (ghi[x.id] = ghi[x.id] || []).push(x.ghi_chu);
    return el("section", {class: "m4-card"}, el("div", {class: "m4-rv-hang m4-rv-dau"}, el("h3", {text: "1. Phát hiện (C01–C09)"}),
      el("div", {class: "m4-rv-hang"}, ["Cao", "Trung bình", "Thấp"].map(m => badge(`${(res.dem || {})[m] || 0} ${m}`, (res.dem || {})[m] ? MUC[m] : "neutral")))),
      ph.length ? bang(["Mã", "Mức", "Phát hiện", "Hạng mục / chứng từ", "Ảnh hưởng ước tính (đồng)"], ph.map(f => el("tr", {}, td(el("strong", {text: f.id})), td(badge(f.level, MUC[f.level] || "neutral")),
        td(el("strong", {text: f.title}), f.detail ? nho(f.detail) : null, (ghi[f.id] || []).map(g => nho("Ghi chú L3: " + g, "m4-loi-chu"))),
        td(nho(f.item || f.tai_lieu || "")), td(typeof f.amount === "number" ? money(f.amount) : "—"))))
        : el("div", {class: "m4-notice", text: "Không có phát hiện — xem Phạm vi đã kiểm: chưa đủ căn cứ thì không phải Đạt."}),
      nho("Ảnh hưởng là ước tính của thuật toán nguồn (VAT chỉ khi có thuế suất typed) — không phải số NT/thuế/công nợ được chấp nhận."));
  }
  // ô so lượng theo so sánh TYPED của chính hạng mục: ✓/✗ CHỈ khi so được; NULL/khác ĐVT/không rõ/nguồn không so → "chưa so được" kèm lý do; 0 tường minh giữ "0"
  function oLuong(s, giaTri, dat, docs, khongCo) {
    if (!s) return [giaTri != null ? num(giaTri) + " " : "", dau(null, "Chưa có so sánh typed")];
    if (s.trang_thai === "SO_DUOC") return [giaTri != null ? num(giaTri) + " " : "", dau(dat, docs || khongCo)];
    if (s.trang_thai === "KHONG_AP_DUNG") return [giaTri != null ? num(giaTri) + " " : "", el("span", {class: "m4-nho", title: s.ly_do || "", text: "—"})];
    return [giaTri != null ? num(giaTri) + " " : "", ttSs(s), nho(s.ly_do || "")];
  }
  // ngưỡng thiếu của nguồn review_goc/may_chu/chung_tu.py (C01 dòng 460: kn − nt; C03 dòng 479: kl_lk − gn) — chỉ ✗ khi chênh VƯỢT ngưỡng
  const tol = x => Math.max(1e-3, Math.abs(x) * 1e-6);
  const toan = (s, k, du) => (s && k in s ? s[k] : du);  // toán hạng của so sánh typed (adapter _ss); thiếu khóa → trường dòng ma trận
  function maTran(res) {  // chiTiet nguồn mục 2 — dấu theo so sánh typed từng hạng mục (không dùng một cờ coverage tổng để làm xanh dòng)
    const mt = res.ma_tran || [], docs = (res.tai_lieu || []).filter(d => !d.bo), coLoai = t => docs.some(d => d.loai === t);
    if (!mt.length) return el("section", {class: "m4-card"}, el("h3", {text: "2. Ma trận hạng mục × chứng từ"}), nho("Chưa có hạng mục nào có KL kỳ này hoặc có chứng từ."));
    return el("section", {class: "m4-card"}, el("h3", {text: "2. Ma trận hạng mục × chứng từ"}),
      bang(["Hạng mục", "ĐVT", "KL kỳ này", "KL lũy kế", "BB nghiệm thu", "Đã giao", "CO", "CQ", "Packing list", "BB lắp đặt"], mt.map(r => {
        const s = r.so_sanh || {}, c1 = s.C01, c3 = s.C03;
        const kn = toan(c1, "kl_kn", r.kl_kn), nt = toan(c1, "nt", r.nt), lk = toan(c3, "kl_lk", r.kl_lk), gn = toan(c3, "gn", r.gn);
        // dấu chỉ dùng khi oLuong thấy SO_DUOC; nt NULL với kn > 0 = nguồn báo "không có trong BB nghiệm thu" (thiếu), không suy ra đủ
        const ntDat = kn == null ? null : kn <= 1e-9 ? true : nt == null ? false : !(kn - nt > tol(nt));
        const gnDat = lk == null ? null : gn == null ? false : !(lk - gn > tol(gn)), can = r.gn_docs.length > 0;
        return el("tr", {}, td(el("strong", {text: r.ma_hm || ""}), " ", String(r.ten).slice(0, 70)), td(r.dvt || ""), td(num(r.kl_kn)), td(num(r.kl_lk)),
          td(...oLuong(c1, nt, ntDat, r.nt_docs.join(", "), "Không có trong BB nghiệm thu")),
          td(...oLuong(c3, r.gn_docs.length ? gn : null, gnDat, r.gn_docs.join(", "), "Chưa có BB giao nhận")),
          td(dau(can ? r.co.length > 0 : r.co.length ? true : null, r.co.join(", "))), td(dau(can ? r.cq.length > 0 : r.cq.length ? true : null, r.cq.join(", "))),
          td(dau(r.pl.length ? true : can && coLoai("PL") ? false : null, r.pl.join(", "))), td(dau(r.ld.length ? true : can && coLoai("BB_LD") ? false : null, r.ld.join(", "))));
      }), "m4-bang-rong"),
      nho("BB nghiệm thu / Đã giao: ✓ không thiếu · ✗ thiếu khi chênh vượt max(0,001; |lượng đối chiếu|×10⁻⁶) như nguồn — CHỈ khi so được (cùng ĐVT, có số lượng, có KL đã công bố, toán hạng của so sánh typed); “chưa so được” kèm lý do. CO/CQ/PL/BB lắp đặt: ✓ có chứng từ (không phải đủ lượng — xem mục 2b) · ✗ chưa có · — không áp dụng."));
  }
  function capC06(res) {
    const caps = res.c06_cap || [];
    if (!caps.length) return null;
    return el("section", {class: "m4-card"}, el("h3", {text: "2b. Đối chiếu chéo giao nhận ↔ CO / CQ / packing list (theo cặp)"}),
      bang(["Dòng giao nhận", "Chứng từ", "Dòng đối chiếu", "ĐVT", "Số lượng", "Số lô", "Ngày"], caps.map(c => el("tr", {},
        td(c.gn_ten || "", nho(`${num(c.gn_so_luong)} ${c.gn_dvt || ""}`)), td(c.loai), td(c.doi_ten || "", nho(`${num(c.doi_so_luong)} ${c.doi_dvt || ""}`)),
        td(badge(c.dvt === "CUNG" ? "cùng ĐVT" : c.dvt === "KHAC" ? "khác ĐVT" : "không rõ ĐVT", c.dvt === "CUNG" ? "success" : "warning")),
        td(ttSs(c.so_luong), c.so_luong && c.so_luong.ly_do ? nho(c.so_luong.ly_do) : null), td(ttSs(c.lo)), td(ttSs(c.ngay))))),
      nho("Số lượng giữa các chứng từ chỉ so khi cùng ĐVT (chuẩn hóa nguồn, không quy đổi); số lô/serial và ngày kiểm riêng."));
  }
  function chungTuDaDoc(res) {  // chiTiet nguồn mục 3 — sửa loại/số/ngày, bỏ/dùng lại (gom thành MỘT revision), dòng hàng + ghép tay
    const loaiDs = Object.entries((ds && ds.loai) || {}), docs = res.tai_lieu || [], sua = kq.run && ["SUCCEEDED", "PARTIAL", "STALE"].includes(kq.run.trang_thai) && ds && ds.co_so && ds.co_so.san_sang;
    const hm = res.hang_muc || [], gt = {};
    for (const x of ((res.provenance || {}).ghep_tay || [])) gt[x.row_id] = x;
    const goc = (d, k) => (k === "bo" ? !!d.bo : k === "ngay" ? (d.ngay || null) : k === "so" ? (d.so || "") : d.loai);
    const doi = (d, k, v) => {  // nháp theo trường: trùng giá trị đang hiệu lực → bỏ trường; không vẽ lại form, chỉ bật/tắt nút Lưu
      const s = {...(ui.sua[d.tep_id] || {})};
      if (v === goc(d, k)) delete s[k]; else s[k] = v;
      if (Object.keys(s).length) ui.sua[d.tep_id] = s; else delete ui.sua[d.tep_id];
      genSua += 1; capNhatNut();
    };
    const rows = [];
    for (const d of docs) {
      const s = ui.sua[d.tep_id] || {}, doc = ["CHECKED", "LIMITED"].includes(d.trang_thai_doc);
      const bo = "bo" in s ? s.bo : !!d.bo;
      const sLoai = el("select", {"aria-label": `Loại chứng từ ${d.ten}`, disabled: !doc || !sua, onchange: ev => doi(d, "loai", ev.target.value)},
        loaiDs.map(([k, t]) => el("option", {value: k, text: t, selected: k === ("loai" in s ? s.loai : d.loai)})));
      const iSo = el("input", {type: "text", value: "so" in s ? s.so : (d.so || ""), disabled: !doc || !sua, "aria-label": `Số chứng từ ${d.ten}`, oninput: ev => doi(d, "so", ev.target.value)});
      const iNgay = el("input", {type: "date", value: "ngay" in s ? (s.ngay || "") : (d.ngay || ""), disabled: !doc || !sua, "aria-label": `Ngày chứng từ ${d.ten}`,
        oninput: ev => doi(d, "ngay", ev.target.value || null)});
      rows.push(el("tr", {class: bo ? "m4-ct-bo" : ""}, td(el("strong", {text: d.ten}), ttDoc(d.trang_thai_doc), ttDong(d.trang_thai_dong), d.ly_do_doc ? nho(d.ly_do_doc) : null,
        d.ly_do_dong && d.trang_thai_dong !== "CHECKED" ? nho(d.ly_do_dong) : null, (d.thich_nghi_cot || []).map(x => nho(`Cột "${x.tieu_de}" đọc là tên (alias "${x.alias}")`)),
        (d.canh_bao || []).map(w => nho(w, "m4-loi-chu"))),
        td(sLoai, nho(d.ly_do_loai || "")), td(iSo, d.trich && d.trich.so !== (d.so || "") ? nho(`trích: ${d.trich.so || "—"}`) : null),
        td(iNgay, d.trich && d.trich.ngay !== d.ngay ? nho(`trích: ${fmtDate(d.trich.ngay)}`) : null),
        td(nho((d.hd_ref || []).map(x => x.join("/")).join(", ") || "—")), td(String((d.dong || []).length)),
        td(el("button", {type: "button", disabled: !sua, onclick: () => { doi(d, "bo", !bo); ve_(); }}, bo ? "Dùng lại" : "Bỏ khỏi bộ"))));
      if ((d.dong || []).length) {
        const lines = d.dong.map(ln => {
          const vt = ln.vi_tri_vat_ly || {}, g = gt[ln.row_id], canXn = g && g.trang_thai !== "DA_AP";
          const moGhep = sua && (!ln.khoa || canXn || ui.doi[ln.row_id]);
          const cho = moGhep ? el("div", {class: "m4-rv-hang"},
            el("select", {"aria-label": `Hạng mục ghép cho ${ln.ten}`, onchange: ev => { ui.ghep[ln.row_id] = ev.target.value; genSua += 1; }},
              el("option", {value: "", text: "— hạng mục —"}), hm.map(h => el("option", {value: h.khoa, selected: ui.ghep[ln.row_id] === h.khoa,
                text: `${h.ma_hm || h.khoa} · ${String(h.ten).slice(0, 50)} · ${h.dvt || ""}${(h.nguon_boq || []).length === 1 ? "" : " (không có đích BOQ duy nhất)"}`}))),
            el("input", {type: "text", value: ui.lyGhep[ln.row_id] || "", placeholder: "Lý do ghép (bắt buộc)", "aria-label": `Lý do ghép ${ln.ten}`,
              oninput: ev => { ui.lyGhep[ln.row_id] = ev.target.value; genSua += 1; }}),
            el("button", {type: "button", onclick: () => ghep(d, ln)}, "Ghép")) : null;
          const ghepTxt = ln.khoa ? [el("span", {text: `${ln.khoa} `}), nho(`${Math.round((ln.khop || 0) * 100)}%${ln.ghep_tay ? " · ghép tay" : ""}`),
            sua && !ui.doi[ln.row_id] && !canXn ? el("button", {type: "button", class: "m4-lien-ket", onclick: () => { ui.doi[ln.row_id] = true; ve_(); }}, "Đổi") : null] : [el("span", {class: "m4-loi-chu", text: "chưa ghép"})];
          return el("tr", {}, td(nho(ln.vi_tri || ""), nho(vt.trang_thai === "CHECKED" ? (vt.loai === "XLSX" ? `${vt.sheet}!dòng ${vt.dong}` : `bảng ${vt.bang} · dòng ${vt.dong}`) : "vị trí vật lý: không xác định")),
            td(ln.ten, ln.nhom ? nho(ln.nhom) : null), td(ln.model || ""), td(ln.quy_cach || ""), td(ln.dvt || ""), td(ln.so_luong == null ? el("span", {class: "m4-loi-chu", text: "không đọc được"}) : num(ln.so_luong)),
            td(ln.lo || ""), td([ln.xuat_xu, ln.nsx].filter(Boolean).join(" · ")),
            td(...ghepTxt, canXn ? nho(`Ghép tay cũ ${g.khoa}: ${g.trang_thai === "CAN_XAC_NHAN_LAI" ? "cần xác nhận lại" : "không áp"} — ${g.ly_do || ""}`, "m4-loi-chu") : null, cho),
            td(nho(ln.nguon || ""), ln.kiem_tra ? nho(ln.kiem_tra, "m4-loi-chu") : null));
        });
        rows.push(el("tr", {}, el("td", {colspan: "7"}, el("details", {open: ui.moRong[d.tep_id] ? true : undefined, ontoggle: ev => { ui.moRong[d.tep_id] = ev.target.open; }},
          el("summary", {text: `Dòng hàng (${d.dong.length})`}),
          bang(["Vị trí", "Tên", "Model", "Quy cách", "ĐVT", "Số lượng", "Số lô / serial", "Xuất xứ · NSX", "Ghép hạng mục", "Nguồn"], lines, "m4-bang-rong")))));
      }
    }
    nutLuu = sua ? el("button", {type: "button", class: "m4-chinh", disabled: !mucSua().length || banDich("sua", runChon), onclick: () => luuSua()}, "Lưu sửa (revision mới)") : null;
    return el("section", {class: "m4-card"}, el("div", {class: "m4-rv-hang m4-rv-dau"}, el("h3", {text: "3. Chứng từ đã đọc"}), nho("Sửa loại / số / ngày hoặc bỏ khỏi bộ → Lưu thành revision mới → Chạy lại; bản trích và raw giữ nguyên.")),
      bang(["Tệp", "Loại", "Số", "Ngày", "HĐ ghi trên chứng từ", "Dòng", ""], rows),
      sua ? el("div", {class: "m4-rv-hang"}, el("input", {type: "text", value: ui.lySua, placeholder: "Lý do sửa (bắt buộc)", "aria-label": "Lý do sửa metadata", oninput: ev => { ui.lySua = ev.target.value; genSua += 1; }}),
        nutLuu, el("button", {type: "button", onclick: () => chayLai()}, "▶ Chạy lại (lần chạy con)")) : null);
  }
  function xuatBaoCao() {  // nút gắn ĐÚNG run + artifact của chi tiết đang hiển thị
    const art = (kq && kq.artifact) || [], runId = kq && kq.run && kq.run.id;
    if (!runId || runId !== runChon) return null;
    const nhan = {REPORT_L3: "Báo cáo L3 (Excel)", RESULT: "Kết quả JSON", BASIS: "Căn cứ JSON", INPUT: "Đầu vào JSON", LOG: "Nhật ký tính"};
    return el("div", {class: "m4-rv-hang"}, ["REPORT_L3", "RESULT", "BASIS", "INPUT", "LOG"].flatMap(l => art.filter(a => a.loai === l).map(a =>
      el("button", {type: "button", class: l === "REPORT_L3" ? "m4-chinh" : "", onclick: () => tai(a, runId)}, "⭳ " + (nhan[l] || l)))));
  }
  // Gửi lại ý định chưa rõ: ĐÚNG route/body/khóa/đích/hoàn tất gốc; fence = phạm vi gốc còn đang mở (không gửi từ ngữ cảnh khác)
  async function guiLaiTreo(kt) {
    const t = treo.get(kt);
    if (!t || !khopPv(t)) { ve_(); trangThai("Lệnh chưa rõ kết quả không thuộc ngữ cảnh đang mở — không gửi lại từ đây.", true); return; }
    if (t.bay || dangGui.has(t.id)) { trangThai("Đang gửi lại lệnh chưa rõ này — chờ kết quả.", true); return; }
    await lenh(t.path, t.body, t.ok, fence(() => khopPv(t)), t.xong, t, t);
    capNhatNut();
  }
  function ve_() {
    if (!box || !box.isConnected) return;
    nutLuu = null;
    const out = [el("div", {class: "m4-rv-dau m4-rv-hang"}, el("div", {}, el("h3", {text: "Chứng từ của đợt · Lớp 3 (C01–C09)"}),
      nho("Khối lượng kỳ này có biên bản nghiệm thu; vật tư, thiết bị có BB giao nhận, CO / CQ, packing list, BB lắp đặt. Phân tích kỹ thuật — không phải duyệt.")),
      el("div", {class: "m4-rv-hang"}, kq && kq.ket_qua ? xuatBaoCao() : null, el("button", {type: "button", onclick: () => { napDs(); if (runChon) moRun(runChon); }}, "↻"))),
      el("p", {class: "m4-ct-status m4-status", role: "status", "aria-live": "polite"})];
    for (const t of treo.values()) {  // MỖI ý định chưa rõ một dòng, chỉ trong đúng phạm vi gốc (vai/PN/dự án/HĐ/đợt[/run]) — vai khác không thấy
      if (khopPv(t)) out.push(t.bay ? el("div", {class: "m4-notice", text: `Đang gửi lại y nguyên lệnh chưa rõ kết quả (${t.moTa}) — chờ kết quả; lệnh mới cho đích này bị chặn tới khi rõ.`})
        : el("div", {class: "m4-hang"}, `Chưa rõ kết quả lần gửi trước (${t.moTa}). `,
          el("button", {type: "button", class: "m4-chinh", onclick: () => guiLaiTreo(t.kt)}, "Gửi lại y nguyên (cùng khóa)")));
      else if (t.run && t.dot === phamVi(null)) out.push(el("div", {class: "m4-notice", text: `Chưa rõ kết quả lần gửi trước (${t.moTa}) ở một lần chạy khác của đợt này — mở lại lần chạy đó để Gửi lại y nguyên; lệnh mới cho đích này bị chặn tới khi rõ.`}));
    }
    if (dsLoi && !ds) out.push(el("div", {class: "m4-notice m4-notice-loi", text: dsLoi}));
    if (ds && ds.provider) out.push(el("div", {class: "m4-notice", text: "PDF/ảnh scan và chứng từ dạng form cần OCR (ABBYY) / Local AI — chưa cấu hình trong phần mềm này: tệp/dòng đó được giữ nguyên và ghi 'chưa đọc', các mục liên quan hiện Chưa đủ căn cứ (không giả kết quả)."}));
    out.push(boChungTu());
    if (runChon && !kq) out.push(el("p", {class: "m4-trong", text: "Đang tải kết quả…"}));
    if (kq && kq.ket_qua && kq.run && kq.run.id === runChon) {
      const res = kq.ket_qua.ket_qua, run = kq.run;
      if (res.trang_thai === "FAILED") out.push(el("div", {class: "m4-notice m4-notice-loi", role: "alert"}, el("strong", {text: "Không đọc/đối chiếu được bộ chứng từ"}), " ", res.loi || run.ly_do || ""));
      else {
        if (run.trang_thai === "STALE") out.push(el("div", {class: "m4-notice", text: run.ly_do || "Căn cứ đã đổi trong lúc tính — kết quả chỉ là bằng chứng. Bấm Chạy lại."}));
        const pv = res.provenance || {};
        out.push(el("section", {class: "m4-card m4-rv-hang m4-rv-dau"}, el("div", {}, el("strong", {text: `Chứng từ · ${res.so_hd || ""} · NT ${fmtDate(res.ngay_nt)}`}),
          nho(`${(res.tai_lieu || []).length} tệp · revision ${run.revision} · căn cứ ${pv.nguon_hang_muc || "chưa có"} · basis ${String(run.basis_sha256).slice(0, 12)}… · ${res.engine} · ${run.tao_boi}`),
          pv.l2_cu ? nho("L2 đã công bố không còn khớp căn cứ hiện hành — không dùng lượng L2: " + (pv.ly_do_can_cu || ""), "m4-loi-chu") : null),
          ttRun(run.trang_thai)));
        out.push(coveragePanel(res), phatHien(res), maTran(res), capC06(res), chungTuDaDoc(res));
      }
    }
    out.push(...lichSu());
    out.push(nho("Chưa nối ở gói M4-02B: duyệt reviewer + PDF ký (02C), kế toán/công nợ, Request; OCR/Local AI cho PDF/ảnh/chứng từ dạng form; .doc/.xls/.xlsm/.tif. Kết quả L3 không phải duyệt hay số được chấp nhận."));
    box.replaceChildren(...out.filter(Boolean));
  }

  // ------------------------------------------------------------------ đổi vai + cầu nối shell M4
  function xoa() {
    // treo/dangGui/khoaMap GIỮ (đều theo phạm vi gốc): không rò sang vai/ngữ cảnh mới, quay lại đúng ngữ cảnh vẫn chặn trùng và giữ khóa đã phát
    ep += 1; ds = null; kq = null; runChon = null; dsLoi = null; genForm += 1; nutLuu = null;
    xoaNhap();
    if (box) box.replaceChildren(el("p", {class: "m4-trong", text: "Đang tải…"}));
  }
  K.dangKyVai("m4_chung_tu", xoa, () => { if (vungSong()) { napDs(); if (runChon) moRun(runChon); } });
  function huy() {  // shell gọi ĐỒNG BỘ lúc ý định đổi tab/HĐ/đợt/vai — mọi GET/POST/blob về muộn bị fence chặn
    ep += 1; genDs += 1; genCt += 1; genForm += 1; hoatDong = false; box = null; nutLuu = null;  // dangGui giữ: tab away/back không mất khóa đích đang bay
  }
  window.kttM4ChungTu = Object.freeze({
    ve(vung, c) {
      const doi = !ctx || ctx.hdId !== c.hdId || ctx.nguoi !== c.nguoi || (ctx.dotId || null) !== (c.dotId || null) || (ctx.duAnId || null) !== (c.duAnId || null)
        || (ctx.phapNhan || null) !== (c.phapNhan || null), moLai = !hoatDong;
      box = vung; hoatDong = true;
      if (doi) { xoa(); ctx = c; sel.dot = c.dotId && (c.dots || []).some(d => d.id === c.dotId) ? c.dotId : null; }
      else ctx = {...ctx, ...c};
      ve_();
      if (doi || moLai || !ds) napDs();
      if (!doi && moLai && runChon) moRun(runChon);
    },
    huy,
    tat: huy,
  });
  if (typeof window.kttM4ChungTuSanSang === "function") window.kttM4ChungTuSanSang();
})();
