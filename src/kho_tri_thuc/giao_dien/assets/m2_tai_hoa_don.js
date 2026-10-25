"use strict";
// M2-00E — khối "Tải từ cổng thuế" trong màn Hóa đơn mua XML (#page-hoadonmua → #m2-tct), theo TL 43 §3.
// Chỉ gọi route thật của giao_dien/m2_tai_hoa_don.py (/api/m2/tai-hoa-don*). Trình duyệt chỉ gửi nguồn/phạm vi/công ty (lấy từ danh sách máy chủ trả,
// chỉ gồm pháp nhân vai hiện tại ĐƯỢC PHÉP), kỳ, chiều, định dạng và một khóa thao tác; danh tính, pháp nhân, hồ sơ đăng nhập cổng thuế, đường dẫn,
// mật khẩu và captcha không bao giờ đi qua đây (captcha gõ tay trong cửa sổ Chrome của bộ tải). Mọi chuỗi từ máy chủ hiển thị bằng textContent.
// Trạng thái hiện theo sự kiện của bộ tải (SSE đã lọc): mở cổng → chờ đăng nhập (đồng hồ 8 phút) → lấy danh sách → tải n/N → ghi manifest → nhận vào M2.
// Đổi vai: đăng ký vào cổng chung window.kttChung (xóa đồng bộ, barrier GET). Fence = epoch (đổi vai) + lần chạy (run) sau MỌI await.
(() => {
  const K = window.kttChung;
  if (!K) return;  // shell chưa có seam
  const $ = id => document.getElementById(id);
  const node = K.node;
  const goc = $("m2-tct");
  if (!goc) return;
  const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || "";
  const API = "/api/m2/tai-hoa-don";
  const HAN_DANG_NHAP_GIAY = 8 * 60;  // LOGIN_TIMEOUT_MS của bộ tải
  const CHIEU = {purchase: "Mua vào", sold: "Bán ra"};
  const TAI_XONG = new Set(["COMPLETE", "PARTIAL", "HOAN_TAT"]);  // biên nhận có thư mục run đọc được → nhận vào M2

  // ------------------------------------------------------------------ trạng thái
  let ep = 0, gen = 0;            // epoch (đổi vai) + thế hệ GET danh sách
  let tt = null, loiTai = null, loiBoTai = null, dangMo = false, daThuMo = false;
  let run = null, abort = null, dongHo = null, logMo = false;
  let hangDoi = null, dangGuiTatCa = false, dangHuy = false, doiGen = 0;
  const khoaMap = new Map();      // lựa chọn (JSON) → khóa thao tác: giữ tới khi lần tải kết thúc (bấm lại sau mất kết nối = cùng run, không chạy mù)
  const taoKhoa = () => "m2tct-" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));

  class LoiTct extends Error {
    constructor(status, code, message, goiY) { super(message); this.status = status; this.code = code; this.goiY = goiY || null; }
  }
  async function goi(path, opts = {}) {
    let res;
    try { res = await fetch(path, {...opts, headers: {"X-KTT-Token": TOKEN, ...(opts.headers || {})}, cache: "no-store", credentials: "same-origin"}); }
    catch (e) {
      if (e && e.name === "AbortError") throw e;
      throw new LoiTct(0, "MAT_KET_NOI", "Mất kết nối với ứng dụng trên máy — chưa rõ lệnh vừa gửi đã được xử lý hay chưa. Bấm lại đúng thao tác đó (cùng lựa chọn là cùng một lần tải, không chạy hai lần) hoặc “Kiểm tra lại”.");
    }
    if (!res.ok) {
      const r = await res.json().catch(() => ({}));
      throw new LoiTct(res.status, r.error || "HTTP_" + res.status, r.message || `Không hoàn tất yêu cầu (${res.status}).`, r.goi_y);
    }
    return res;
  }
  const getJson = async path => (await goi(path)).json();
  const postJson = async (path, body) => (await goi(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})).json();
  const conHop = (r, e) => e === ep && run === r;

  // ------------------------------------------------------------------ suy bước từ sự kiện (hàm thuần — kiểm thử được)
  function suyBuoc(ev, nowMs) {
    let dn = null, tCho = null, hien = null;
    for (const e of ev) {
      const p = e.payload || {};
      if (e.type === "log") {
        const m = String(p.msg || "");
        if (/captcha|dang nhap thu cong/i.test(m)) { dn = "CHO"; tCho = typeof e.ts === "number" ? e.ts : (Date.parse(e.ts) || e.nhanLuc || nowMs); }
        else if (/nhan dien dang nhap thanh cong/i.test(m)) dn = "XONG";
        else if (/nhom/i.test(m) && hien && hien.k === "DS") hien = {...hien, nhom: m};
      } else if (e.type === "phase") {
        hien = /ghi manifest/i.test(p.label || "") ? {k: "MANIFEST", chieu: p.type, ky: p.monthTag} : {k: "DS", chieu: p.type, ky: p.monthTag, nhom: null};
      } else if (e.type === "progress") {
        hien = {k: "TAI", chieu: p.type, ky: p.monthTag, index: p.index, total: p.total};
      } else if (e.type === "done") {
        hien = {k: "XONG", trang_thai: p.trang_thai, so_run: p.so_run};
      } else if (e.type === "error") {
        hien = {k: "LOI", code: p.code, goiY: p.goi_y};
      }
    }
    const ten = (c, k) => [c ? CHIEU[c] : null, k].filter(Boolean).join(" ");
    if (hien && hien.k === "XONG") return {k: "XONG", nhan: "Bộ tải đã tải xong — đang đọc biên nhận"};
    if (hien && hien.k === "LOI") return {k: "LOI", nhan: "Bộ tải báo lỗi " + hien.code, goiY: hien.goiY};
    if (hien && hien.k === "MANIFEST") return {k: "MANIFEST", nhan: "Đang ghi manifest" + (ten(hien.chieu, hien.ky) ? " (" + ten(hien.chieu, hien.ky) + ")" : "")};
    if (hien && hien.k === "TAI") return {k: "TAI", nhan: `Đang tải ${hien.index}/${hien.total} (${ten(hien.chieu, hien.ky)})`, index: hien.index, total: hien.total};
    if (hien && hien.k === "DS") return {k: "DS", nhan: `Đang lấy danh sách ${ten(hien.chieu, hien.ky)} (nhóm có mã / không mã / máy tính tiền)`, chiTiet: hien.nhom};
    if (dn === "CHO") {
      const conLai = HAN_DANG_NHAP_GIAY - Math.floor(((nowMs === undefined ? Date.now() : nowMs) - tCho) / 1000);
      return {k: "CHO_DANG_NHAP", nhan: "Chờ đăng nhập — gõ captcha trong cửa sổ Chrome", conLai};
    }
    if (dn === "XONG") return {k: "DA_DANG_NHAP", nhan: "Đã đăng nhập — chuẩn bị lấy danh sách"};
    return {k: "MO_CONG", nhan: "Đang mở cổng thuế"};
  }
  const mmss = s => { const a = Math.max(0, s); return String(Math.floor(a / 60)).padStart(2, "0") + ":" + String(a % 60).padStart(2, "0"); };
  const nhanDongHo = b => b.conLai > 0 ? `còn ${mmss(b.conLai)} / hạn ${HAN_DANG_NHAP_GIAY / 60} phút` : "đã quá hạn chờ đăng nhập — bộ tải sẽ báo lỗi LOGIN_TIMEOUT";
  function dungDongHo() { if (dongHo !== null) { clearInterval(dongHo); dongHo = null; } }
  function capDongHo() {
    const o = $("m2-tct-dong-ho");
    if (!o || !run || run.xong) { dungDongHo(); return; }
    const b = suyBuoc(run.ev);
    if (b.k !== "CHO_DANG_NHAP") { o.textContent = ""; return; }
    o.textContent = nhanDongHo(b);
  }

  // ------------------------------------------------------------------ hiển thị
  const pill = (text, cls) => node("span", text, "pill " + (cls || "neutral"));
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
    const b = node("button", text, cls || "button secondary small"); b.type = "button"; b.disabled = !!tat;
    b.addEventListener("click", () => { if (!b.disabled) fn(b); }); return b;
  }
  function trangThai(msg, loi = false) { const o = $("m2-tct-status"); if (o) { o.textContent = msg || ""; o.className = "upload-status" + (loi ? " error" : ""); } }
  const chuaSan = m => !m || m.san_sang !== true;
  const lieuChon = () => { try { return JSON.parse($("m2-tct-phap-nhan").value || "null"); } catch (_) { return null; } };
  const mucChon = () => { const l = lieuChon(); return l && tt && tt.muc ? tt.muc.find(m => m.source_instance === l[0] && m.scope_ref === l[1] && m.company_key === l[2]) : null; };
  const dangChay = () => !!run && !run.xong && !run.chuaRo;

  function boxLoi(loi, tieuDe) {
    const box = node("div", undefined, "alert error");
    box.append(node("strong", tieuDe || "Lỗi"));
    const dong = node("p", `${loi.message} (mã ${loi.code}${loi.status ? ", HTTP " + loi.status : ""})`);
    box.append(dong);
    if (loi.goiY) box.append(node("p", "Gợi ý: " + loi.goiY));
    return box;
  }
  function dongLoiCong(chieu, ky, l) {
    const t = `${CHIEU[chieu] || ""} ${ky || ""}: mã lỗi ${l.code}${l.stage ? " · giai đoạn " + l.stage : ""}${l.http_status !== null && l.http_status !== undefined ? " · HTTP " + l.http_status : ""}`;
    const d = node("div"); d.append(node("p", t.trim())); if (l.goi_y) d.append(node("p", "Gợi ý: " + l.goi_y)); return d;
  }

  function veBoTai() {
    const o = $("m2-tct-bo-tai"); if (!o) return;
    if (loiTai) { o.replaceChildren(boxLoi(loiTai, "Không đọc được trạng thái bộ tải"), nut("Thử lại", () => napTrangThai())); return; }
    if (!tt) { o.replaceChildren(node("p", "Đang tải…", "upload-status")); return; }
    if (!tt.cau_hinh) {
      o.replaceChildren(K.empty("Bộ tải chưa cấu hình", (tt.ly_do || "") + (tt.goi_y ? " Gợi ý: " + tt.goi_y : ""))); return;
    }
    const kids = [];
    const b = tt.bo_tai || {};
    if (b.san_sang) kids.push(pill("Bộ tải đã mở", "green"));
    else {
      kids.push(pill(dangMo ? "Đang mở bộ tải…" : "Bộ tải chưa mở", "amber"));
      kids.push(nut(b.loi_khoi_dong ? "Thử mở lại bộ tải" : "Mở bộ tải", () => moBoTai(), "button secondary small", dangMo || !(tt.muc || []).length));
    }
    if (b.loi_khoi_dong) kids.push(boxLoi(new LoiTct(0, b.loi_khoi_dong, "Bộ tải không khởi động được.", b.goi_y), "Lỗi khởi động bộ tải"));
    if (loiBoTai) kids.push(boxLoi(loiBoTai, "Không mở được bộ tải"));
    o.replaceChildren(...kids);
  }

  function veForm() {
    const f = $("m2-tct-form"); if (!f) return;
    const cauHinh = !!tt && tt.cau_hinh === true, co = cauHinh && (tt.muc || []).length > 0;
    f.classList.toggle("hidden", !co);
    $("m2-tct-form-trong").classList.toggle("hidden", !(cauHinh && !co));
    if (!co) return;
    const cu = $("m2-tct-phap-nhan").value, ds = tt.muc || [];
    $("m2-tct-phap-nhan").replaceChildren(...ds.map(m => {
      const op = node("option", `${m.phap_nhan_ma} · ${m.company_key}${m.san_sang ? "" : " — " + (m.ly_do_vi || "chưa sẵn sàng")}`);
      op.value = JSON.stringify([m.source_instance, m.scope_ref, m.company_key]); op.disabled = !m.san_sang; return op;
    }));
    const giu = ds.find(m => JSON.stringify([m.source_instance, m.scope_ref, m.company_key]) === cu && m.san_sang);
    const dau = ds.find(m => m.san_sang);
    $("m2-tct-phap-nhan").value = giu ? cu : (dau ? JSON.stringify([dau.source_instance, dau.scope_ref, dau.company_key]) : "");
    $("m2-tct-nam").classList.toggle("hidden", $("m2-tct-che-do").value !== "year");
    $("m2-tct-thang").classList.toggle("hidden", $("m2-tct-che-do").value === "year");
    $("m2-tct-bat-dau").disabled = dangChay() || dangGuiTatCa || chuaSan(mucChon());
    $("m2-tct-tat-ca").disabled = dangChay() || dangGuiTatCa || !!(hangDoi && hangDoi.dang_co_hang_doi) || !ds.some(m => m.san_sang);
    if (hangDoi && hangDoi.dang_co_hang_doi) $("m2-tct-bat-dau").disabled = true;
  }

  function veTienTrinh() {
    const o = $("m2-tct-tien-trinh"); if (!o) return;
    dungDongHo();
    if (!run) { o.replaceChildren(); return; }
    const kids = [], b = suyBuoc(run.ev);
    const dau = node("div", undefined, "demo-actions");
    const nhanBuoc = run.giaiDoan === "NHAN" ? "Đang nhận vào M2…" : run.xong ? (run.loi ? "Dừng do lỗi" : "Xong") : run.giaiDoan === "BAT_DAU" ? "Đang gửi lệnh tải…" : b.nhan;
    dau.append(pill(nhanBuoc, run.loi ? "amber" : run.xong ? "green" : "neutral"));
    if (!run.xong && !run.giaiDoan.startsWith("NHAN") && b.k === "CHO_DANG_NHAP") {
      const c = node("span", nhanDongHo(b), "upload-status"); c.id = "m2-tct-dong-ho"; dau.append(c);
      dongHo = setInterval(capDongHo, 1000);
    }
    kids.push(dau);
    if (b.k === "TAI" && !run.xong) { const p = node("progress"); p.max = b.total; p.value = b.index; kids.push(p); }
    if (b.chiTiet && !run.xong) kids.push(node("p", b.chiTiet, "upload-status"));
    if (run.chuaRo) {
      const box = node("div", undefined, "alert error");
      box.append(node("strong", "Chưa rõ bộ tải đã nhận lệnh hay chưa"), node("p", run.chuaRo.goi_y || "Bấm “Đối soát” để kiểm tra; đừng tải lại ngay."));
      box.append(nut("Đối soát", () => doiSoat(run)));
      kids.push(box);
    }
    for (const e of run.ev) {  // lỗi do bộ tải báo trong luồng sự kiện: hiện mã nguyên văn, không chờ biên nhận
      if (e.type !== "error") continue;
      const p = e.payload || {}, box = node("div", undefined, "alert error");
      box.append(node("strong", "Bộ tải báo lỗi"), node("p", `Mã lỗi ${p.code}`));
      if (p.goi_y) box.append(node("p", "Gợi ý: " + p.goi_y));
      kids.push(box);
    }
    if (run.loi) {
      kids.push(boxLoi(run.loi, "Lỗi"));
      if (run.handle && !run.xong0) kids.push(nut("Kiểm tra lại", () => { const r = run; r.loi = null; r.xong = false; r.dangNhan = false; ve(); vong(r, ep); }));
    }
    if (run.ev.length) {
      const logs = run.ev.filter(e => e.type === "log").slice(-30).map(e => (e.payload || {}).msg).join("\n");
      const d = node("details"); d.open = logMo; d.addEventListener("toggle", () => { logMo = d.open === true; });  // vẽ lại theo từng sự kiện không làm gập nhật ký người dùng đang mở
      d.append(node("summary", `Nhật ký bộ tải (${run.ev.length} sự kiện)`));
      const pre = node("pre", logs); pre.style.whiteSpace = "pre-wrap"; d.append(pre); kids.push(d);
    }
    o.replaceChildren(...kids);
  }

  function veKetQua() {
    const o = $("m2-tct-ket-qua"); if (!o) return;
    if (!run || !run.st) { o.replaceChildren(); return; }
    const kids = [], st = run.st, runs = (st.ket_qua && st.ket_qua.runs) || [];
    if (st.trang_thai === "UNKNOWN" || st.trang_thai === "NOT_FOUND") {
      kids.push(node("p", st.trang_thai === "NOT_FOUND" ? "Bộ tải chưa có lần tải này (chưa nhận lệnh)." : "Chưa rõ kết quả của bộ tải — bấm “Đối soát”.", "upload-status"), nut("Đối soát", () => doiSoat(run)));
    }
    const loiRun = [];
    for (const r of runs) for (const l of r.loi || []) loiRun.push(dongLoiCong(r.chieu, r.ky, l));
    const tr = st.ket_qua && st.ket_qua.trang_thai;
    if (st.trang_thai === "REPLAY" && tr && !TAI_XONG.has(tr)) {
      const box = node("div", undefined, "alert error");
      box.append(node("strong", `Lần tải không hoàn tất (${tr})`), ...loiRun);
      if (!loiRun.length) box.append(node("p", "Bộ tải không ghi mã lỗi cụ thể; xem “Nhật ký bộ tải”."));
      kids.push(box);
    } else if (loiRun.length) {
      const box = node("div", undefined, "alert error");
      box.append(node("strong", "Bộ tải ghi nhận lỗi ở một số phần của lần tải"), ...loiRun);
      kids.push(box);
    }
    if (run.dangNhan) kids.push(node("p", "Đang nhận kết quả vào M2…", "upload-status"));
    if (run.loiNhan) kids.push(boxLoi(run.loiNhan, "Chưa nhận được kết quả vào M2"), nut("Nhận lại", () => nhan(run)));
    if (run.nhan) {
      const t = run.nhan.tom_tat;
      let s = `Đã nhận vào M2: mới ${t.moi} · đổi trạng thái ${t.doi_trang_thai} · không mã ${t.khong_ma} · lỗi ${t.loi}`;
      if (t.khong_doi) s += ` · không đổi ${t.khong_doi}`;
      if (t.giu_cho_tien_te) s += ` · giữ chờ tiền tệ ${t.giu_cho_tien_te}`;
      const box = node("div", undefined, "notice demo-notice"), ct = node("div");
      ct.append(node("strong", s), node("p", "“Không mã” là hóa đơn chỉ có trong bảng kê (cổng thuế không cấp XML gốc); “giữ chờ tiền tệ” chờ người duyệt. Máy chỉ nhận làm bằng chứng nguồn, chưa hạch toán."));
      box.append(ct); kids.push(box);
      const ng = [];
      for (const r of run.nhan.runs) {
        for (const e of r.ngoai_le || []) ng.push([`${CHIEU[r.chieu] || ""} ${r.ky || ""}`.trim(), e.ma, e.item_ordinal === null || e.item_ordinal === undefined ? "" : e.item_ordinal,
          e.loi ? `${e.loi.code}${e.loi.http_status !== null && e.loi.http_status !== undefined ? " · HTTP " + e.loi.http_status : ""}${e.loi.goi_y ? " — " + e.loi.goi_y : ""}` : ""]);
        if (r.loi) ng.push([`${CHIEU[r.chieu] || ""} ${r.ky || ""}`.trim(), r.loi.ma, "", r.loi.thong_bao || ""]);
      }
      if (ng.length) { kids.push(node("h3", "Ngoại lệ cần xử lý (không bị bỏ qua im lặng)")); kids.push(bang(["Phần", "Mã", "Dòng", "Chi tiết"], ng)); }
    }
    const acts = node("div", undefined, "demo-actions");
    for (const r of runs) {
      if (!r.run_rel) continue;
      const ten = `${CHIEU[r.chieu] || ""} ${r.ky || ""}`.trim();
      acts.append(nut("Mở thư mục " + ten, () => moThuMuc(run, r.run_rel)), nut("Xem manifest " + ten, () => xemManifest(run, r.run_rel)));
    }
    if (run.nhan) acts.append(nut("Xem hóa đơn mới", () => xemHoaDon(run)));
    if (acts.children.length) kids.push(acts);
    if (run.manifest) kids.push(veManifest(run.manifest));
    o.replaceChildren(...kids);
  }
  function veManifest(m) {
    const box = node("div"), t = m.tong || {};
    const trangThai = {COMPLETE: "Hoàn tất", HOAN_TAT: "Hoàn tất", PARTIAL: "Hoàn tất một phần", FAILED: "Thất bại", CONFLICT: "Xung đột"};
    const bangKe = {OK: "Đã tải", LOI: "Lỗi", KHONG_YEU_CAU: "Không yêu cầu"};
    box.append(node("h3", `Manifest ${CHIEU[m.chieu === "purchase" ? "purchase" : "sold"]} ${m.ky} — ${trangThai[m.trang_thai] || "Chưa rõ"} (${m.nguon === "HOI_CUU" ? "hồi cứu, xấp xỉ" : "tải mới"})`));
    box.append(bang(["Tổng HĐ", "Có XML", "Không mã (bảng kê)", "XML lỗi", "PDF lỗi", "Bảng kê"], [[t.tong_hd, t.xml_ok, t.khong_xml_goc, t.xml_loi, t.pdf_loi, bangKe[t.bang_ke_trang_thai] || "Chưa rõ"]]));
    const ngay = m.khoang_ngay || {};
    box.append(node("p", `Số tệp dữ liệu: ${m.so_tep ?? "chưa đo"} · Khoảng ngày tải: ${ngay.tu || "chưa rõ"} – ${ngay.den || "chưa rõ"}`));
    const dn = m.dang_nhap || {}, gt = k => dn[k] && dn[k].gia_tri !== null && dn[k].gia_tri !== undefined ? String(dn[k].gia_tri) : "chưa đo";
    box.append(node("p", `Đăng nhập: gõ captcha = ${gt("captcha_da_go")} · dùng lại token = ${gt("token_tai_su_dung")} · chờ đăng nhập (giây) = ${gt("thoi_gian_cho_dang_nhap_giay")}`, "upload-status"));
    const nl = (m.nhom || []).filter(g => g.loi).map(g => [g.thu_tu, g.scope, g.ttxly, g.loi.code, g.loi.http_status === null ? "" : g.loi.http_status]);
    const lc = (m.loi_chung || []).map(l => ["chung", "", "", l.code, l.http_status === null ? "" : l.http_status]);
    if (nl.length || lc.length) box.append(bang(["Nhóm", "Phạm vi", "ttxly", "Mã lỗi", "HTTP"], [...nl, ...lc]));
    return box;
  }
  function veHangDoi() {
    const o = $("m2-tct-hang-doi");
    o.replaceChildren();
    if (!hangDoi) return;
    if (hangDoi.dang_co_hang_doi) o.append(node("p", "Đang có hàng đợi tải tất cả công ty. Các công ty được tải lần lượt.", "upload-status"));
    if (hangDoi.dang_chay) {
      const huy = nut(dangHuy ? "Đang hủy…" : "Hủy", huyHangDoi, undefined, dangHuy);
      huy.id = "m2-tct-huy-hang-doi"; o.append(huy);
    }
    if ((hangDoi.muc || []).length) o.append(bang(["Pháp nhân", "Trạng thái", "Lý do"], hangDoi.muc.map(m => [m.phap_nhan_ten, m.trang_thai, m.ly_do || ""])));
  }
  function ve() { veBoTai(); veForm(); veTienTrinh(); veKetQua(); veHangDoi(); }

  async function theoDoiHangDoi(e = ep) {
    const g = ++doiGen;
    let loiLienTiep = 0;
    while (e === ep && g === doiGen) {
      try {
        const q = await getJson(API + "/hang-doi");
        if (e !== ep || g !== doiGen) return;
        loiLienTiep = 0;
        hangDoi = q; ve();
        if (!q.dang_co_hang_doi) return;
      } catch (err) {
        if (e !== ep || g !== doiGen) return;
        trangThai(err.message, true);
        if ([400, 403, 404, 409, 503].includes(err.status)) return;
        if (++loiLienTiep >= 20) {
          trangThai("Mất kết nối — bấm Làm mới", true);
          return;
        }
      }
      await cho(1500);
    }
  }
  async function taiTatCa() {
    if (dangChay() || dangGuiTatCa || (hangDoi && hangDoi.dang_co_hang_doi)) return;
    const sel = layLuaChon(); if (!sel) return;
    const {mode, year, month, types, formats} = sel, e = ep;
    const n = new Set((tt.muc || []).filter(m => m.san_sang).map(m => m.phap_nhan_ma)).size;
    const ky = mode === "month" ? `${String(month).padStart(2, "0")}/${year}` : String(year);
    if (!window.confirm(`Tải ${n} công ty · ${ky} · ${types.map(t => CHIEU[t]).join(" và ")}?`)) return;
    dangGuiTatCa = true; trangThai(""); ve();
    try {
      const q = await postJson(API + "/tai-tat-ca", {mode, year, month, types, formats});
      if (e !== ep) return;
      hangDoi = q; theoDoiHangDoi(e);
    } catch (err) {
      if (e !== ep) return;
      trangThai(err.message, true);
      // Mất phản hồi POST có thể đã tạo hàng đợi: đọc trạng thái máy chủ, không gửi lại mù.
      theoDoiHangDoi(e);
    } finally { if (e === ep) { dangGuiTatCa = false; ve(); } }
  }

  async function huyHangDoi() {
    if (dangHuy || !hangDoi || !hangDoi.dang_chay) return;
    const e = ep;
    dangHuy = true; doiGen += 1; veHangDoi();
    try {
      await postJson(API + "/huy-hang-doi", {});
      if (e !== ep) return;
      theoDoiHangDoi(e);
    } catch (err) {
      if (e !== ep) return;
      trangThai(err.message, true);
      theoDoiHangDoi(e);
    } finally { if (e === ep) { dangHuy = false; veHangDoi(); } }
  }

  // ------------------------------------------------------------------ nạp / mở bộ tải
  async function napTrangThai() {
    if (K.vaiDangChan("m2_tai_hoa_don")) return;  // đổi vai đang chờ: không GET vai cũ; nạp lại khi ý định mới nhất giải quyết
    const e = ep, g = ++gen;
    try {
      const s = await getJson(API);
      if (e !== ep || g !== gen) return;
      tt = s; hangDoi = s.hang_doi || null; loiTai = null; ve();
      if (hangDoi && hangDoi.dang_co_hang_doi) theoDoiHangDoi(e);
      if (s.cau_hinh && (s.muc || []).length && !(s.bo_tai || {}).san_sang && !daThuMo) { daThuMo = true; moBoTai(); }  // TL 43 §3 bước 1: mở M2 → bộ tải chạy ngầm
    } catch (err) { if (e === ep && g === gen) { loiTai = err; ve(); } }
  }
  async function moBoTai() {
    const e = ep;
    if (dangMo) return;
    dangMo = true; loiBoTai = null; ve();
    try { await postJson(API + "/khoi-dong", {}); } catch (err) { if (e === ep) loiBoTai = err; }
    if (e !== ep) return;
    dangMo = false;
    await napTrangThai();
    if (e === ep) ve();
  }

  // ------------------------------------------------------------------ bắt đầu → theo dõi → nhận
  function layLuaChon() {
    const l = lieuChon(), m = mucChon();
    if (!l || !m || chuaSan(m)) { trangThai("Chọn một pháp nhân đã sẵn sàng.", true); return null; }
    const mode = $("m2-tct-che-do").value === "year" ? "year" : "month";
    let year, month = null;
    if (mode === "year") { year = parseInt($("m2-tct-nam").value, 10); }
    else { const mm = /^(\d{4})-(\d{2})$/.exec($("m2-tct-thang").value || ""); if (!mm) { trangThai("Chọn tháng cần tải.", true); return null; } year = +mm[1]; month = +mm[2]; }
    if (!(year >= 2020 && year <= 2100)) { trangThai("Năm phải từ 2020 đến 2100.", true); return null; }
    const chieu = $("m2-tct-chieu").value, types = chieu === "ca-hai" ? ["purchase", "sold"] : [chieu === "ban" ? "sold" : "purchase"];
    const formats = [["xml", "m2-tct-dd-xml"], ["pdf", "m2-tct-dd-pdf"], ["excel", "m2-tct-dd-excel"]].filter(([, id]) => $(id).checked).map(([f]) => f);
    if (!formats.length) { trangThai("Chọn ít nhất một định dạng (XML là mặc định).", true); return null; }
    return {source_instance: l[0], scope_ref: l[1], company_key: l[2], mode, year, month, types, formats};
  }
  async function batDau() {
    if (dangChay() || dangGuiTatCa || (hangDoi && hangDoi.dang_co_hang_doi)) return;
    trangThai("");
    const sel = layLuaChon();
    if (!sel) return;
    const key = JSON.stringify(sel), e = ep;
    if (!khoaMap.has(key)) khoaMap.set(key, taoKhoa());
    const r = run = {sel, key, handle: null, ev: [], cursor: 0, giaiDoan: "BAT_DAU", st: null, nhan: null, manifest: null, loi: null, loiNhan: null, chuaRo: null, dangNhan: false, xong: false};
    ve();
    try {
      const kq = await postJson(API + "/bat-dau", {...sel, khoa: khoaMap.get(key)});
      if (!conHop(r, e)) return;
      r.handle = kq.run_handle; r.giaiDoan = "THEO_DOI";
      if (kq.trang_thai === "UNKNOWN") { r.chuaRo = kq; ve(); return; }
      ve();
      vong(r, e);
    } catch (err) {
      if (!conHop(r, e)) return;
      r.loi = err; r.xong = true; r.xong0 = true;
      if (err.status >= 400 && err.status < 500 && err.status !== 409) khoaMap.delete(key);  // lỗi xác định: lần bấm sau lấy khóa mới
      ve();
    }
  }
  const cho = ms => new Promise(res => setTimeout(res, ms));
  function xuLyKhung(r, khung) {
    let ten = null, du = [];
    for (const dong of khung.split("\n")) {
      if (dong.startsWith("event: ")) ten = dong.slice(7);
      else if (dong.startsWith("data: ")) du.push(dong.slice(6));
    }
    if (!ten || !du.length) return null;
    let v; try { v = JSON.parse(du.join("\n")); } catch (_) { return null; }
    if (ten === "su-kien" && v && typeof v.seq === "number" && v.seq > r.cursor) {
      r.cursor = v.seq; r.ev.push({...v, nhanLuc: Date.now()});
      veTienTrinh();
    }
    return ten;
  }
  async function docLuong(r, e) {
    const ac = new AbortController(); abort = ac;
    const res = await goi(`${API}/su-kien?run=${encodeURIComponent(r.handle)}&cursor=${r.cursor}`, {signal: ac.signal});
    const rd = res.body.getReader(), dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const {done, value} = await rd.read();
      if (!conHop(r, e)) { ac.abort(); return; }
      if (done) return;
      buf += dec.decode(value, {stream: true});
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const khung = buf.slice(0, i); buf = buf.slice(i + 2);
        if (xuLyKhung(r, khung) === "ket-thuc") return;
      }
    }
  }
  async function vong(r, e) {
    r.xong = false;
    while (conHop(r, e)) {
      try { await docLuong(r, e); } catch (err) { if (!conHop(r, e)) return; if (err instanceof LoiTct && err.status >= 400 && err.status !== 0) { r.loi = err; r.xong = true; ve(); return; } }
      if (!conHop(r, e)) return;
      let st;
      try { st = await getJson(`${API}/trang-thai?run=${encodeURIComponent(r.handle)}`); }
      catch (err) { if (conHop(r, e)) { r.loi = err; r.xong = true; ve(); } return; }
      if (!conHop(r, e)) return;
      if (st.trang_thai === "RUNNING") { await cho(1500); continue; }
      return ketThuc(r, e, st);
    }
  }
  async function ketThuc(r, e, st) {
    r.st = st; r.giaiDoan = "XONG_TAI";
    const tr = st.ket_qua && st.ket_qua.trang_thai;
    if (st.trang_thai === "REPLAY") khoaMap.delete(r.key);  // lần tải đã kết thúc: lần bấm sau là lần tải mới (khóa mới)
    if (st.trang_thai === "REPLAY" && TAI_XONG.has(tr)) { ve(); return nhan(r, e); }
    r.xong = true; ve();
  }
  async function doiSoat(r) {
    const e = ep;
    try {
      const st = await postJson(API + "/doi-soat", {run: r.handle});
      if (!conHop(r, e)) return;
      r.chuaRo = null; r.loi = null;
      if (st.trang_thai === "RUNNING") { ve(); vong(r, e); return; }
      await ketThuc(r, e, st);
    } catch (err) { if (conHop(r, e)) { r.loi = err; ve(); } }
  }
  async function nhan(r, e = ep) {
    r.giaiDoan = "NHAN"; r.dangNhan = true; r.loiNhan = null; ve();
    try {
      const kq = await postJson(API + "/nhan", {run: r.handle});
      if (!conHop(r, e)) return;
      r.nhan = kq; r.dangNhan = false; r.xong = true; r.giaiDoan = "XONG"; ve();
      const loc = $("m2-loc"); if (loc) loc.dataset.run = r.handle;
      const lm = $("m2-refresh"); if (lm) lm.click();  // danh sách hóa đơn M2 bên dưới tự làm mới
    } catch (err) {
      if (!conHop(r, e)) return;
      r.dangNhan = false; r.loiNhan = err; r.xong = true; ve();
    }
  }
  async function moThuMuc(r, runRel) {
    const e = ep;
    try { await postJson(API + "/mo-thu-muc", {run: r.handle, run_rel: runRel}); if (conHop(r, e)) trangThai("Đã mở thư mục tải trên máy."); }
    catch (err) { if (conHop(r, e)) trangThai(`${err.message} (mã ${err.code})`, true); }
  }
  async function xemManifest(r, runRel) {
    const e = ep;
    try { const m = await getJson(`${API}/manifest?run=${encodeURIComponent(r.handle)}&run_rel=${encodeURIComponent(runRel)}`); if (conHop(r, e)) { r.manifest = m; ve(); } }
    catch (err) { if (conHop(r, e)) trangThai(`${err.message} (mã ${err.code})${err.goiY ? " — " + err.goiY : ""}`, true); }
  }
  function xemHoaDon(r) {  // chuyển sang danh sách hóa đơn của pháp nhân + kỳ vừa tải (lọc theo pháp nhân và kỳ có sẵn của M2)
    const ma = (tt && mucChon0(r)) || null, ky = r.sel.mode === "month" ? `${r.sel.year}-${String(r.sel.month).padStart(2, "0")}` : "";
    if ($("m2-loc-pn")) $("m2-loc-pn").value = ma || "";
    if ($("m2-loc-ky")) $("m2-loc-ky").value = ky;
    const b = $("m2-loc"); if (b) {
      b.dataset.run = r.handle;
      b.dataset.chonLanTai = "1";  // bấm lại sau khi bỏ lọc vẫn mở đúng lần tải này
      b.click();
    }
    const l = $("m2-hoa-don"); if (l && l.scrollIntoView) l.scrollIntoView();
  }
  function mucChon0(r) { const m = ((tt && tt.muc) || []).find(x => x.source_instance === r.sel.source_instance && x.scope_ref === r.sel.scope_ref && x.company_key === r.sel.company_key); return m ? m.phap_nhan_ma : null; }

  // ------------------------------------------------------------------ đổi vai + khởi tạo
  function xoa() {
    ep += 1;
    doiGen += 1; hangDoi = null; dangGuiTatCa = false; dangHuy = false;
    if (abort) { try { abort.abort(); } catch (_) {} abort = null; }
    run = null; tt = null; loiTai = null; loiBoTai = null; dangMo = false; daThuMo = false; dungDongHo();
    for (const id of ["m2-tct-bo-tai", "m2-tct-tien-trinh", "m2-tct-ket-qua", "m2-tct-hang-doi"]) { const o = $(id); if (o) o.replaceChildren(); }
    const f = $("m2-tct-form"); if (f) f.classList.add("hidden");
    trangThai("");
    // Cổng đổi vai chỉ nạp lại module đã "xin nạp" trong lúc barrier (hoặc module khởi tạo): đang xem màn này thì xin ngay để được nạp theo vai mới.
    if (location.hash === "#hoadonmua") napTrangThai();
  }
  K.dangKyVai("m2_tai_hoa_don", xoa, () => napTrangThai());

  const homNayVN = () => new Date(Date.now() + 7 * 3600 * 1000);
  function macDinhKy() {
    const d = homNayVN(); let y = d.getUTCFullYear(), m = d.getUTCMonth();  // getUTCMonth() 0..11 của tháng hiện tại == số tháng TRƯỚC (1..12); tháng 1 → tháng 12 năm trước
    if (m === 0) { y -= 1; m = 12; }
    if (!$("m2-tct-thang").value) $("m2-tct-thang").value = `${y}-${String(m).padStart(2, "0")}`;
    if (!$("m2-tct-nam").value) $("m2-tct-nam").value = String(d.getUTCFullYear());
  }
  const tatCa = nut("Tải tất cả công ty", taiTatCa); tatCa.id = "m2-tct-tat-ca";
  $("m2-tct-form").append(tatCa);
  const bangDoi = node("div"); bangDoi.id = "m2-tct-hang-doi"; goc.append(bangDoi);
  macDinhKy();
  $("m2-tct-form").addEventListener("submit", ev => { ev.preventDefault(); batDau(); });
  for (const id of ["m2-tct-phap-nhan", "m2-tct-che-do"]) $(id).addEventListener("change", () => veForm());
  if ($("m2-tct-lam-moi")) $("m2-tct-lam-moi").addEventListener("click", () => { daThuMo = false; napTrangThai(); });
  if ($("m2-refresh")) $("m2-refresh").addEventListener("click", () => { if (!run || !run.nhan) napTrangThai(); });
  window.addEventListener("hashchange", () => { if (location.hash === "#hoadonmua") napTrangThai(); });
  if (location.hash === "#hoadonmua") napTrangThai();
})();
