// app.js — khung "Bàn kiểm soát": điều hướng, thanh trên, việc đang chạy, Tổng quan, Cài đặt.
// Dữ liệu thật từ máy chủ cục bộ (API.md). Thiết kế gốc: Claude Design (prototype "Bàn kiểm soát").
import { icon, badge, escapeHTML, header } from "./ui.js";
import { api, get, post, money, fmtDate, timeOf, duration, choViec } from "./api.js";
import { renderExtraction, handleExtractionAction, handleExtractionChange, loadExtraction } from "./extraction.js";
import {
  renderContracts,
  renderAppendices,
  renderBOQ,
  handleContractAction,
  handleContractChange,
  loadContracts,
} from "./contracts.js";
import { renderPayments, renderIntegrity, handleCheckAction, handleCheckChange, loadChecks } from "./checks.js";
import { renderChungTu, loadChungTu, handleChungTuAction, handleChungTuChange, ganTrangThai } from "./chung_tu.js";

const E = escapeHTML;
const state = {
  view: "overview",
  ai: null,
  viec: [],
  overview: null,
  overviewErr: "",
  recentFilter: "all",
  recentSort: false,
  settings: null,
  settingsDraft: null,
  settingsDirty: false,
  phienBan: "",
};
const titles = {
  overview: "Tổng quan",
  extraction: "Trích tham số",
  contracts: "Danh mục hợp đồng",
  appendices: "Phụ lục",
  boq: "BOQ",
  payments: "Kiểm tra đợt",
  integrity: "Kiểm tra đợt · chỉ toàn vẹn file",
  documents: "Chứng từ",
  settings: "Cài đặt",
};
const sections = {
  overview: "Bàn làm việc",
  extraction: "Hợp đồng",
  contracts: "Hợp đồng",
  appendices: "Hợp đồng",
  boq: "Hợp đồng",
  payments: "Đợt thanh toán",
  integrity: "Đợt thanh toán",
  documents: "Đợt thanh toán",
  settings: "Bàn làm việc",
};
let modalConfig = null,
  drawerConfig = null,
  focusReturn = null;

function toast(message, kind = "success") {
  const div = document.createElement("div");
  div.className = `toast ${kind}`;
  div.innerHTML = `${icon(kind === "danger" ? "alert" : kind === "warning" ? "alert" : "check")}<span>${E(message)}</span><button type="button" aria-label="Đóng thông báo">${icon("x", 16)}</button>`;
  document.getElementById("toasts").replaceChildren(div);
  div.querySelector("button").onclick = () => div.remove();
  setTimeout(() => div.remove(), kind === "danger" ? 9000 : 5500);
}
function navigate(route, opts = {}) {
  if (!titles[route]) return;
  closeOverlay();
  if (location.hash.slice(1) !== route) location.hash = route;
  state.view = route;
  Object.assign(state, { navOpts: opts });
  render();
  loadView();
  window.scrollTo(0, 0);
}
function openModal(config) {
  focusReturn = document.activeElement;
  modalConfig = config;
  drawerConfig = null;
  document.getElementById("overlays").innerHTML =
    `<div class="overlay-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><div class="modal-head"><h2 id="dialog-title">${E(config.title)}</h2><button class="icon-btn" data-action="overlay-close" aria-label="Đóng hộp thoại">${icon("x")}</button></div><div class="modal-body">${config.body || ""}${config.requireReason ? `<div class="field" style="margin-top:20px"><label for="dialog-reason">${E(config.reasonLabel || "Lý do")} <span class="danger-text">*</span></label><textarea id="dialog-reason" placeholder="Nhập lý do để lưu vào nhật ký" required></textarea><span id="reason-error" class="danger-text small" hidden>Cần nhập lý do trước khi tiếp tục.</span></div>` : ""}</div><div class="modal-actions"><button class="btn" data-action="overlay-close">Quay lại</button><button class="btn ${config.danger ? "btn-danger" : "btn-primary"}" data-action="modal-confirm">${E(config.confirmLabel || "Xác nhận")}</button></div></section></div>`;
  document.getElementById("dialog-reason")?.focus();
  if (!config.requireReason) document.querySelector('[data-action="modal-confirm"]').focus();
}
function openDrawer(config) {
  focusReturn = document.activeElement;
  drawerConfig = config;
  modalConfig = null;
  document.getElementById("overlays").innerHTML =
    `<div class="drawer-backdrop" data-action="overlay-close"></div><section class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title"><div class="drawer-head"><h2 id="drawer-title">${E(config.title)}</h2><button class="icon-btn" data-action="overlay-close" aria-label="Đóng ngăn chi tiết">${icon("x")}</button></div><div class="drawer-body">${config.body}</div></section>`;
  document.querySelector('.drawer [data-action="overlay-close"]').focus();
}
function closeOverlay() {
  document.getElementById("overlays").innerHTML = "";
  modalConfig = null;
  drawerConfig = null;
  focusReturn?.focus?.();
}
const ctx = { state, render, navigate, toast, openModal, openDrawer, closeOverlay, refreshJobs };
ganTrangThai(ctx);

// ------------------------------------------------------------------ việc đang chạy + máy AI
const ROUTE_VIEC = { trich_xuat: "extraction", kiem_dot: "payments", toan_ven: "integrity", tim_may_ai: "settings", ocr_thu: "settings", phu_luc: "appendices", chung_tu: "documents" };
const TEN_VIEC = {
  ocr_thu: "Chạy thử OCR ABBYY",
  phu_luc: "Trích điều chỉnh phụ lục",
  chung_tu: "Đọc và đối chiếu chứng từ",
  trich_xuat: "Trích tham số hợp đồng",
  kiem_dot: "Kiểm tra đợt thanh toán",
  toan_ven: "Kiểm tra toàn vẹn file (HĐ chưa có trong CSDL)",
  tim_may_ai: "Tìm máy AI",
};
let dangChayTruoc = new Set();
async function refreshJobs() {
  try {
    const d = await get("/api/viec");
    state.viec = d.ds;
    const now = new Set(d.ds.filter((v) => ["cho", "dang_chay"].includes(v.tt)).map((v) => v.id));
    for (const id of dangChayTruoc)
      if (!now.has(id)) {
        const v = d.ds.find((x) => x.id === id);
        if (v) {
          toast(
            v.tt === "xong" ? `Xong: ${v.ten}` : v.tt === "da_dung" ? `Đã dừng: ${v.ten}` : `Lỗi: ${v.ten} — ${v.loi}`,
            v.tt === "xong" ? "success" : v.tt === "da_dung" ? "warning" : "danger",
          );
          if (v.loai === "trich_xuat" || state.view === "overview") loadView();
          if (v.loai === "ocr_thu" && state.view === "settings") loadOcr(true);
          if (v.loai === "phu_luc" && state.view === "appendices") loadView();
          if (v.loai === "chung_tu" && state.view === "documents" && !state.ct?.job) loadView();
        }
      }
    dangChayTruoc = now;
    const pill = document.querySelector(".count-pill");
    if (pill) pill.textContent = now.size;
  } catch (e) {
    /* máy chủ tạm không trả lời — lần sau thử lại */
  }
}
async function refreshAI(lamMoi = false) {
  try {
    state.ai = await get("/api/ai" + (lamMoi ? "?lam_moi=1" : ""));
  } catch (e) {
    state.ai = { ket_noi: false, loi: e.message, ip: "?", cong: "", model: "" };
  }
  const el = document.querySelector(".connection");
  if (el) el.outerHTML = connectionButton();
}
function aiOk() {
  return state.ai && state.ai.ket_noi && state.ai.co_model;
}
function connectionButton() {
  const a = state.ai || {};
  const ok = aiOk();
  if (a.nguon === "claude")
    return `<button class="connection ${ok ? "" : "conn-off"}" data-route="settings" aria-label="Nguồn AI Claude, mở cài đặt"><span class="conn-dot"></span><span>Claude (che định danh)<span class="conn-model"> · ${E(a.model || "")}</span><br><span class="conn-status">${E(ok ? "Đang dùng thay máy AI" : "Chưa có API key")}</span></span></button>`;
  const txt = !state.ai ? "Đang kiểm tra" : ok ? "Kết nối được" : a.ket_noi ? "Thiếu model" : "Mất kết nối";
  return `<button class="connection ${ok ? "" : "conn-off"}" data-route="settings" aria-label="Máy AI ${E(txt)}, mở cài đặt"><span class="conn-dot"></span><span>Máy AI ${E(a.ip || "")}${a.cong ? ":" + a.cong : ""}<span class="conn-model"> · ${E(a.model || "")}</span><br><span class="conn-status">${E(txt)}</span></span></button>`;
}
function activeJobs() {
  return (state.viec || []).filter((v) => ["cho", "dang_chay"].includes(v.tt));
}
function jobsDrawer() {
  const jobs = activeJobs();
  const xong = (state.viec || []).filter((v) => !["cho", "dang_chay"].includes(v.tt)).slice(0, 6);
  openDrawer({
    title: `Việc đang chạy (${jobs.length})`,
    body: `<p class="muted small" style="margin-bottom:20px">Công việc tiếp tục chạy khi chuyển màn hình. Việc dùng máy AI chạy lần lượt.</p>${
      jobs.length
        ? jobs
            .map(
              (j) =>
                `<div class="panel"><div class="panel-head"><h2>${E(TEN_VIEC[j.loai] || j.ten)}</h2>${badge(j.tt === "cho" ? "Chờ máy AI" : "Đang chạy", "info")}</div><div class="panel-body"><strong>${E(j.ten)}</strong><p class="muted small" style="margin:8px 0 18px">${E(j.thong_bao || "")}</p><div class="progress-label"><span>${j.bat_dau ? duration(Date.now() / 1000 - j.bat_dau) : "Đang chờ"}</span><strong>${Math.round((j.pct || 0) * 100)}%</strong></div><div class="progress"><div style="width:${Math.round((j.pct || 0) * 100)}%"></div></div><div class="toolbar" style="margin-top:18px"><button class="btn btn-primary" data-route="${ROUTE_VIEC[j.loai] || "overview"}">Mở tiến độ</button><button class="btn btn-danger" data-action="job-stop" data-id="${E(j.id)}">${icon("stop", 15)} Dừng</button></div></div></div>`,
            )
            .join("")
        : `<div class="empty-state">${icon("check")}<h2>Không có việc đang chạy</h2><p>Mọi công việc đã hoàn tất hoặc đã dừng.</p><button class="btn btn-primary" data-route="extraction">Trích hợp đồng mới</button></div>`
    }${xong.length ? `<h3>Kết quả gần đây trong phiên</h3>${xong.map((v) => `<button class="link-btn" data-route="${ROUTE_VIEC[v.loai] || "overview"}">${E(v.ten)} · ${E(v.tt === "xong" ? "Xong" : v.tt === "loi" ? "Lỗi" : "Đã dừng")} ${icon("chevron", 14)}</button><br>`).join("")}` : ""}`,
  });
}

// ------------------------------------------------------------------ Tổng quan
async function loadOverview() {
  try {
    state.overview = await get("/api/tong_quan");
    state.overviewErr = "";
  } catch (e) {
    state.overviewErr = e.message;
  }
  if (state.view === "overview") render();
}
function renderOverview() {
  const o = state.overview;
  const now = new Date();
  const sub = `${now.toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })} · Phòng Tài chính`;
  const head = header(
    "Tổng quan",
    E(sub.charAt(0).toUpperCase() + sub.slice(1)),
    `<button class="btn" data-route="extraction">${icon("plus", 16)} Trích hợp đồng</button><button class="btn btn-primary" data-route="payments">${icon("shield", 16)} Kiểm tra đợt</button>`,
  );
  if (!o)
    return (
      head +
      (state.overviewErr
        ? `<div class="notice notice-danger">${icon("alert")}<div><strong>Không tải được dữ liệu</strong>${E(state.overviewErr)}</div></div>`
        : `<div class="panel"><div class="panel-body muted">Đang tải…</div></div>`)
    );
  const c = o.csdl || {};
  const jobs = activeJobs();
  const empty = !c.so_hop_dong && !(o.viec_gan_day || []).length;
  const oCanXem = (o.so_o_can_xem || 0) + (c.tham_so_chua_xac_nhan || 0);
  const stat = (ic, label, value, desc, warn = false) =>
    `<div class="stat"><div class="stat-label">${icon(ic, 15)} ${label}</div><div class="stat-value ${warn && value ? "warn" : ""}">${value}</div><div class="stat-description">${desc}</div></div>`;
  let html =
    head +
    `<div class="stat-strip">${stat("file", "Hợp đồng trong CSDL", c.so_hop_dong || 0, c.so_hop_dong ? `${c.moi_trong_thang || 0} hợp đồng mới trong tháng` : "Chưa có dữ liệu")}${stat("layers", "Phụ lục", c.so_phu_luc || 0, c.phu_luc_co_do ? `${c.phu_luc_co_do} phụ lục có cờ đỏ` : "Không có cờ đỏ")}${stat("shield", "Đợt chờ duyệt", (o.dot_cho_duyet || []).length, "Đã kiểm tra, chưa nạp CSDL")}${stat("activity", "Việc đang chạy", jobs.length, "Có thể chuyển màn hình")}${stat("alert", "Ô cần xác nhận", oCanXem, `${o.so_o_can_xem || 0} ở kết quả trích · ${c.tham_so_chua_xac_nhan || 0} trong CSDL`, true)}</div>`;
  if (state.ai && !aiOk())
    html += `<div class="notice notice-danger">${icon("alert")}<div><strong>Máy AI chưa sẵn sàng</strong>${E(state.ai.loi || "")}. Kiểm tra địa chỉ máy AI và kết nối mạng LAN trước khi trích hợp đồng.</div><button class="btn" data-route="settings">Mở cài đặt</button></div>`;
  if (empty)
    return (
      html +
      `<div class="panel"><div class="empty-state">${icon("folder", 36)}<h2>Bắt đầu với hợp đồng đầu tiên</h2><p>Trích tham số, kiểm tra các ô cần xác nhận, sau đó nạp hợp đồng vào CSDL để đối chiếu hồ sơ thanh toán.</p><button class="btn btn-primary" data-route="extraction">${icon("upload")} Trích hợp đồng</button></div></div>`
    );
  const dot = (o.dot_cho_duyet || [])[0];
  if (dot) {
    const cao = (dot.dem || {}).Cao || 0;
    html += `<div class="payment-review-banner"><div><div class="review-title">${icon("shield", 20)} Hồ sơ cần review</div><p>${E((dot.hop_dong || {}).ma_hd || "")} · ${E(dot.tep || "")}${dot.dot ? ` · Đợt ${E(dot.dot)}` : ""}</p></div><div><span class="small muted">Số đề nghị thanh toán</span><div class="review-value">${money(dot.de_nghi)} <span style="font-size:13px;color:var(--muted)">₫</span></div></div><div class="inline-row">${cao ? badge(`${cao} phát hiện mức cao`, "danger") : badge(`${dot.so_phat_hien || 0} phát hiện`, "warning")}<button class="btn btn-primary" data-action="open-payment" data-ma="${E(dot.ma)}">Mở kết quả ${icon("arrow", 16)}</button></div></div>`;
  }
  let rows = (o.viec_gan_day || []).filter((r) => state.recentFilter === "all" || r.kind === state.recentFilter);
  if (state.recentSort) rows = [...rows].reverse();
  const iconLoai = { trich_xuat: "scan", kiem_tra_dot: "shield", toan_ven: "table", csdl: "database" };
  const alerts = o.can_xem_xet || [];
  html += `<div class="overview-columns"><div class="panel"><div class="panel-head"><div><h2>Việc gần đây</h2><span class="small muted">Kết quả và dấu vết xử lý hồ sơ</span></div><div class="toolbar"><select id="recent-filter" aria-label="Lọc kết quả"><option value="all" ${state.recentFilter === "all" ? "selected" : ""}>Tất cả kết quả</option><option value="success" ${state.recentFilter === "success" ? "selected" : ""}>Xong</option><option value="warning" ${state.recentFilter === "warning" ? "selected" : ""}>Có cảnh báo</option><option value="danger" ${state.recentFilter === "danger" ? "selected" : ""}>Lỗi</option></select></div></div><div class="table-wrap"><table class="data-table"><thead><tr><th><button class="sort-btn" data-action="recent-sort">Thời gian ${icon("sort", 13)}</button></th><th>Công việc</th><th>Kết quả</th><th></th></tr></thead><tbody>${
    rows
      .map((r, i) => {
        const [t, d] = timeOf(r.t);
        return `<tr><td style="width:95px"><span class="primary-cell">${t}</span><span class="secondary-cell">${d}</span></td><td><div class="inline-row"><span style="color:#7c8da0">${icon(iconLoai[r.loai] || "file", 18)}</span><div><span class="primary-cell">${E(r.ten)}</span><span class="secondary-cell">${E(r.phu)}</span></div></div></td><td>${badge(r.ket_qua, r.kind)}<span class="secondary-cell">${E(r.ghi_chu)}</span></td><td><button class="icon-btn" data-action="recent-open" data-i="${(o.viec_gan_day || []).indexOf(r)}" aria-label="Mở ${E(r.ten)}">${icon("chevron", 16)}</button></td></tr>`;
      })
      .join("") || `<tr><td colspan="4" class="muted small">Chưa có việc nào.</td></tr>`
  }</tbody></table></div><div class="panel-foot"><span>Hiển thị ${rows.length} công việc gần nhất</span><span>Giờ trên máy này</span></div></div><div class="stack"><div class="panel"><div class="panel-head"><h2>Cần Anh xem xét</h2>${badge(String(alerts.length), alerts.length ? "warning" : "neutral")}</div>${
    alerts
      .map(
        (a, i) =>
          `<div class="alert-item"><div class="alert-icon ${a.loai === "tham_so" ? "yellow" : ""}">${icon(a.loai === "dot" ? "alert" : a.loai === "canh_bao" ? "layers" : "file", 16)}</div><div><strong>${E(a.tieu_de)}</strong><p>${E(a.noi_dung)}${a.anh_huong ? `<br>Ảnh hưởng ước tính ${money(a.anh_huong)} ₫` : ""}</p><button class="link-btn" data-action="alert-open" data-i="${i}">${E(a.nut || "Xem")} ${icon("chevron", 13)}</button></div></div>`,
      )
      .join("") || '<div class="panel-body small muted">Không có mục cần xem xét.</div>'
  }</div><div class="panel"><div class="panel-head"><h2>Việc đang chạy</h2>${badge(String(jobs.length), "info")}</div>${
    jobs.length
      ? jobs
          .map(
            (j) =>
              `<div class="job-item"><div class="job-title">${icon("scan", 16)} ${E(TEN_VIEC[j.loai] || j.ten)}</div><span class="small muted">${E(j.ten)}</span><div class="job-meta"><span>${E(j.thong_bao || (j.tt === "cho" ? "Chờ máy AI" : ""))}</span><strong>${Math.round((j.pct || 0) * 100)}%</strong></div><div class="progress"><div style="width:${Math.round((j.pct || 0) * 100)}%"></div></div><div class="job-meta"><span>${icon("clock", 12)} ${j.bat_dau ? duration(Date.now() / 1000 - j.bat_dau) : "Đang chờ"}</span><button class="link-btn" data-route="${ROUTE_VIEC[j.loai] || "overview"}" style="font-size:10px;min-height:25px">Mở tiến độ</button></div></div>`,
          )
          .join("")
      : '<div class="panel-body small muted">Không có việc đang chạy.</div>'
  }</div></div></div>`;
  return html + `<div class="footer-note"><span>Đối chiếu từ số đề nghị về chứng từ gốc · Dữ liệu trên máy này</span><span>${E(state.phienBan)}</span></div>`;
}

// ------------------------------------------------------------------ Cài đặt
const CLOUD_MODELS = {
  anthropic: ["claude-sonnet-5", "claude-opus-5-5", "claude-haiku-4-5-20251001"],
  openai: ["gpt-4o-mini", "gpt-4o"],
};
async function loadSettings() {
  try {
    state.settings = await get("/api/cai_dat");
    if (!state.settingsDirty) state.settingsDraft = draftFrom(state.settings);
  } catch (e) {
    toast(e.message, "danger");
  }
  if (state.view === "settings") render();
}
function draftFrom(c) {
  return {
    ip: c.may_ai.ip,
    cong: c.may_ai.cong,
    model: c.may_ai.model,
    an_danh: c.may_ai.an_danh,
    ra_lai: c.trich_xuat.ra_lai,
    nguon: c.nguon_ai || "local",
    cloud: c.cloud.bat,
    ncc: c.cloud.nha_cung_cap,
    cloudModel: c.cloud.model || "",
    tyLe: c.cloud.ty_le,
    ocrCheDo: c.ocr?.che_do || "tu_dong",
    ocrThuMuc: c.ocr?.mac_dinh ? "" : c.ocr?.thu_muc || "",
    ocrCho: c.ocr?.cho_toi_da || 1800,
    models: null,
  };
}
async function loadOcr(lamMoi = false) {
  try {
    state.ocr = await get(`/api/ocr/trang_thai${lamMoi ? "?lam_moi=1" : ""}`);
  } catch (e) {
    state.ocr = { loi: e.message, checks: [], canh_bao: [] };
  }
  if (state.view === "settings") render();
}
function ocrPanel(c, s) {
  const o = c.ocr || {};
  const st = state.ocr;
  const u = st?.usage || null;
  const b = !st
    ? badge("Đang kiểm tra", "neutral")
    : s.ocrCheDo === "tat"
      ? badge("Đang tắt", "neutral")
      : st.loi
        ? badge("Chưa dùng được", "danger")
        : st.ok
          ? badge("Sẵn sàng", "success")
          : badge("Cần kiểm tra", "warning");
  const checks = (st?.checks || [])
    .map((k) => `<li class="${k.ok === false ? "danger-text" : ""}">${k.ok === true ? "✓" : k.ok === false ? "✗" : "•"} ${E(k.check)}${k.detail && k.ok !== true ? ` — <span class="small">${E(k.detail)}</span>` : ""}</li>`)
    .join("");
  const vao = st?.input_dir || o.input_dir || "";
  const ra = st?.output_dir || o.output_dir || "";
  const dong = (nhan, p) => `<div class="ocr-path"><span>${nhan}</span><code>${E(p)}</code><button class="icon-btn" data-action="settings-copy" data-text="${E(p)}" aria-label="Chép đường dẫn" title="Chép đường dẫn">${icon("copy", 15)}</button></div>`;
  return `<section class="panel setting-section"><div class="panel-head"><h2 class="setting-icon">${icon("scan", 19)} OCR PDF scan · ABBYY Hot Folder</h2>${b}</div><div class="panel-body"><p class="muted small" style="margin-bottom:14px">PDF scan của hợp đồng, phụ lục, BOQ được phần mềm đưa vào thư mục <strong>in</strong> của một task ABBYY Hot Folder riêng trên máy này (không gửi ra ngoài); ABBYY trả bản Word vào thư mục <strong>out</strong>, phần mềm đọc rồi xoá file tạm. Kết quả OCR lưu đệm theo nội dung file: nạp lại cùng file không tốn thêm trang.</p><div class="ocr-setup"><strong class="small">Tạo task trong ABBYY Hot Folder (một lần)</strong><ol class="small"><li>New task → <em>File from folder</em>:${dong("", vao)}</li><li><em>Save results</em> → Microsoft Word (.docx), Folder:${dong("", ra)}</li><li>Schedule <em>Recurring – every minute</em>; Original files <em>Delete</em>; mỗi file một tài liệu.</li><li>Bấm <em>Chạy thử 1 trang</em> bên dưới để kiểm tra.</li></ol></div><div class="setting-form"><div class="field"><label for="ocr-mode">Chế độ</label><select id="ocr-mode" data-setting="ocrCheDo">${(o.che_do_ds || [])
    .map((m) => `<option value="${E(m.ma)}" ${s.ocrCheDo === m.ma ? "selected" : ""}>${E(m.ten)}</option>`)
    .join("")}</select><small>BOQ dạng PDF luôn cần OCR để đọc bảng.</small></div><div class="field"><label for="ocr-wait">Chờ tối đa mỗi file (giây)</label><input id="ocr-wait" type="number" min="60" max="7200" data-setting="ocrCho" value="${E(s.ocrCho)}"></div><div class="field span-2"><label for="ocr-dir">Thư mục OCR của phần mềm</label><input id="ocr-dir" data-setting="ocrThuMuc" value="${E(s.ocrThuMuc)}" placeholder="Mặc định: ${E(o.mac_dinh_thu_muc || "")}"><small>Để trống = mặc định (trong thư mục phần mềm, không lên Git). Đổi thư mục thì sửa lại task Hot Folder.</small></div><div class="toolbar span-2"><button class="btn" data-action="settings-ocr-check">${icon("refresh", 16)} Kiểm tra</button><button class="btn btn-ghost" data-action="settings-ocr-test">${icon("scan", 16)} Chạy thử 1 trang</button>${
    u ? `<span class="small muted">Phần mềm đã OCR <strong>${E(u.used_pages)}</strong> trang / ${E(u.window_days)} ngày (hạn mức ABBYY ${E(u.limit)} trang, tính chung cả máy)</span>` : ""
  }</div>${
    st
      ? `<div class="span-2">${st.loi ? `<div class="notice notice-danger">${icon("alert")} ${E(st.loi)}</div>` : ""}${(st.canh_bao || [])
          .map((w) => `<div class="notice notice-warning" style="margin-top:8px">${icon("alert")} ${E(w)}</div>`)
          .join("")}<ul class="small" style="margin:10px 0 0;padding-left:18px;line-height:1.8;list-style:none">${checks}</ul></div>`
      : ""
  }</div></div></section>`;
}
function nguonPanel(c, s) {
  const khoa = (c.cloud.khoa || {})[s.ncc] || {};
  const mdl = s.cloudModel || (c.cloud.model_mac_dinh || {})[s.ncc] || "";
  const opt = (v, t, d) => `<label class="check-label" style="align-items:flex-start;gap:10px;margin-bottom:10px"><input type="radio" name="nguon-ai" data-setting="nguon" value="${v}" ${s.nguon === v ? "checked" : ""}><span><strong>${t}</strong><br><span class="small muted">${d}</span></span></label>`;
  return `<section class="panel setting-section"><div class="panel-head"><h2 class="setting-icon">${icon("activity", 19)} Nguồn AI</h2>${badge(s.nguon === "claude" ? "Claude (che định danh)" : "Local AI", s.nguon === "claude" ? "warning" : "success")}</div><div class="panel-body">${opt("local", "Local AI — máy AI trong mạng (mặc định)", "Hợp đồng chỉ đi tới máy AI của anh (LAN / Tailscale).")}${opt("claude", `Claude qua API — khi máy AI không bật được`, `Dùng nhà cung cấp, model${mdl ? ` (${E(mdl)})` : ""} và API key ở mục Kiểm tra chéo cloud${khoa.co_khoa ? "" : ' — <span class="danger-text">chưa có API key</span>'}. Che tên các bên, công ty, dự án, số HĐ, MST, tài khoản, điện thoại trước khi gửi; câu nào còn sót định danh thì không gửi. Thông tin chung đọc bằng quy tắc, không gửi Phần mở đầu, không rà lại toàn HĐ. Số liệu (giá trị, đơn giá, tỷ lệ, ngày) không bị che. Mỗi lần gửi ghi nhật ký GUI_RA_NGOAI.`)}${s.nguon === "claude" ? `<div class="notice notice-warning" style="display:block;margin-top:6px">Đang chọn Claude: trích hợp đồng, phụ lục và chứng từ sẽ gửi các Khoản liên quan (đã che định danh) ra ngoài. Chọn lại Local AI khi máy AI bật lại.</div>` : ""}</div></section>`;
}
function renderSettings() {
  const c = state.settings;
  if (!c || !state.settingsDraft) return header("Cài đặt", "Đang tải…") + "";
  const s = state.settingsDraft;
  const ok = aiOk();
  const models = s.models || (state.ai && state.ai.models && state.ai.models.length ? state.ai.models : [s.model]);
  const khoa = c.cloud.khoa[s.ncc] || {};
  const env = Object.keys(c.bien_moi_truong || {});
  return (
    header(
      "Cài đặt",
      "Cấu hình máy AI trong mạng LAN, kiểm tra chéo và nơi lưu dữ liệu.",
      `<button class="btn btn-primary" data-action="settings-save">${icon("check", 16)} Lưu cài đặt</button>`,
    ) +
    (env.length
      ? `<div class="notice notice-warning">${icon("alert")}<div><strong>Đang có biến môi trường ghi đè cài đặt</strong>${E(env.join(", "))} — giá trị trong biến môi trường được ưu tiên.</div></div>`
      : "") +
    `<div class="settings-layout"><div>${nguonPanel(c, s)}<section class="panel setting-section"><div class="panel-head"><h2 class="setting-icon">${icon("server", 19)} Máy AI</h2>${s.nguon === "claude" ? badge("Không dùng — nguồn AI đang là Claude", "neutral") : badge(ok ? "Kết nối được" : state.ai?.ket_noi ? "Thiếu model" : "Mất kết nối", ok ? "success" : "danger")}</div><div class="panel-body"><div class="setting-form"><div class="field"><label for="ai-ip">Địa chỉ IP</label><input id="ai-ip" data-setting="ip" value="${E(s.ip)}"><small>Máy chạy Ollama trong mạng LAN · máy này: ${E((c.ip_may_nay || []).join(", ") || "?")}</small></div><div class="field"><label for="ai-port">Cổng</label><input id="ai-port" type="number" min="1" max="65535" data-setting="cong" value="${E(s.cong)}"></div><div class="toolbar span-2"><button class="btn" data-action="settings-connect">${icon("refresh", 16)} Kiểm tra kết nối</button><button class="btn btn-ghost" data-action="settings-discover">${icon("search", 16)} Tự tìm máy AI trong mạng</button><span class="small muted" id="connect-result"></span></div><div class="field span-2"><label for="ai-model">Model mặc định</label><select id="ai-model" data-setting="model">${[...new Set([...models, s.model])].map((m) => `<option ${s.model === m ? "selected" : ""}>${E(m)}</option>`).join("")}</select><small>Danh sách lấy từ máy AI. Bấm Kiểm tra kết nối để cập nhật.</small></div><label class="check-label span-2"><input type="checkbox" data-setting="ra_lai" ${s.ra_lai ? "checked" : ""}>Mặc định rà lại toàn hợp đồng cho ô vàng</label></div></div></section><section class="panel setting-section cloud-panel ${s.cloud ? "" : "disabled"}"><div class="panel-head"><h2 class="setting-icon">${icon("cloud", 19)} Kiểm tra chéo cloud</h2><label class="toggle"><input type="checkbox" id="settings-cloud" ${s.cloud ? "checked" : ""}><span>${s.cloud ? "Đang bật" : "Đang tắt"}</span></label></div><div class="panel-body"><p class="muted small" style="margin-bottom:18px">Chỉ gửi ô vàng mức 2–3, tham số đánh dấu "Luôn hỏi Claude" và mẫu ngẫu nhiên ô OK. Không gửi Thông tin chung, không gửi Phần mở đầu; đã che tên các bên, số HĐ, MST, tài khoản, điện thoại. Mặc định tắt.</p><div class="setting-form cloud-options"><div class="field"><label for="cloud-provider">Nhà cung cấp</label><select id="cloud-provider" data-setting="ncc"><option value="anthropic" ${s.ncc === "anthropic" ? "selected" : ""}>Anthropic (Claude)</option><option value="openai" ${s.ncc === "openai" ? "selected" : ""}>OpenAI</option></select></div><div class="field"><label for="cloud-model">Model</label><input id="cloud-model" list="cloud-model-list" data-setting="cloudModel" value="${E(s.cloudModel)}" placeholder="Mặc định: ${E((c.cloud.model_mac_dinh || {})[s.ncc] || "")}"><datalist id="cloud-model-list">${(CLOUD_MODELS[s.ncc] || []).map((m) => `<option value="${m}">`).join("")}</datalist></div><div class="field span-2"><label for="cloud-key">API key ${s.ncc === "anthropic" ? "Anthropic" : "OpenAI"}</label><div class="key-input"><input id="cloud-key" type="password" autocomplete="off" placeholder="${khoa.co_khoa ? "Đã lưu · •••• " + E(khoa.bon_ky_tu_cuoi) : "Dán API key rồi bấm Lưu key"}"><button class="icon-btn" data-action="settings-eye" aria-label="Hiện hoặc ẩn API key">${icon("eye", 16)}</button></div><div class="toolbar"><button class="btn" data-action="settings-save-key">${icon("lock", 15)} Lưu key</button><small>${khoa.co_khoa ? `Đã có key (${E(khoa.nguon)}) · chỉ hiển thị 4 ký tự cuối` : "Chưa có key được lưu"}</small>${khoa.co_khoa && khoa.nguon === "file" ? '<button class="link-btn danger-text" data-action="settings-delete-key">Xóa key</button>' : ""}</div></div><div class="field"><label for="cloud-rate">Tỷ lệ kiểm ngẫu nhiên (%)</label><input id="cloud-rate" type="number" min="0" max="100" data-setting="tyLe" value="${E(s.tyLe)}"><small>Ô OK mức 3 lấy x%, mức 2 lấy x/2%.</small></div><div class="field" style="justify-content:center"><button class="btn btn-ghost" data-action="settings-log">${icon("external", 16)} Nhật ký gửi ra ngoài</button></div><div class="toolbar span-2"><button class="btn" data-action="settings-cloud-test">${icon("refresh", 16)} Thử kết nối ${s.ncc === "openai" ? "OpenAI" : "Claude"}</button><span class="small ${state.cloudTest?.ok === false ? "danger-text" : "muted"}" id="cloud-test-result">${state.cloudTest ? E(state.cloudTest.ok ? `Kết nối được · ${state.cloudTest.model} · ${state.cloudTest.giay} giây` : state.cloudTest.loi || "Lỗi") : "Gửi một câu kiểm tra ngắn, không có dữ liệu hợp đồng."}</span></div></div></div></section>${ocrPanel(c, s)}<section class="panel setting-section"><div class="panel-head"><h2 class="setting-icon">${icon("database", 19)} Dữ liệu</h2>${badge("Lưu trên máy này", "neutral")}</div><div class="panel-body"><div class="setting-form"><div class="field span-2"><label>Đường dẫn CSDL</label><input value="${E(c.du_lieu.csdl)}" readonly></div><div class="field span-2"><label>Thư mục kết quả trích</label><input value="${E(c.du_lieu.ket_qua)}" readonly></div><div class="field span-2"><label>Danh mục hợp đồng (Excel)</label><input value="${E(c.du_lieu.danh_muc_hd)}" readonly></div><div class="field span-2"><label>Nơi lưu API key</label><input value="${E(c.du_lieu.khoa_api)}" readonly><small>Ngoài thư mục dự án — không bao giờ lên Git.</small></div><div class="toolbar span-2"><button class="btn" data-action="settings-backup">${icon("download", 16)} Sao lưu CSDL</button><button class="btn btn-ghost" data-action="settings-export">${icon("table", 16)} Xuất CSDL ra Excel</button></div></div></div></section><div class="settings-footer"><span class="small muted">${state.settingsDirty ? "Có thay đổi chưa lưu" : "Cài đặt đã được lưu."}</span><button class="btn btn-primary" data-action="settings-save">Lưu cài đặt</button></div></div><aside class="settings-help"><h3>Kiểm soát dữ liệu gửi đi</h3><div class="inline-row" style="color:var(--green)">${icon("lock", 17)}<strong class="small">Local AI được ưu tiên</strong></div><p>Hợp đồng được xử lý trên máy AI trong mạng nội bộ; chỉ gửi các Khoản liên quan.</p><hr class="divider"><h3>Khi bật kiểm tra chéo</h3><p>Chỉ trích đoạn đã che định danh được gửi đến nhà cung cấp đã chọn. Mỗi lần gửi ghi nhật ký GUI_RA_NGOAI (không ghi API key).</p><button class="link-btn" data-action="settings-log">Xem nhật ký gửi ${icon("chevron", 14)}</button><hr class="divider"><h3>OCR bằng ABBYY</h3><p>PDF scan được nhận dạng bằng ABBYY trên máy này; file tạm trong thư mục Hot Folder bị xoá ngay sau khi đọc. Hạn mức giấy phép 5.000 trang / 30 ngày.</p><hr class="divider"><h3>Danh mục tham số</h3><p>37 tham số, mức quan trọng, từ khoá và cột "Luôn hỏi Claude" sửa trong file trich_xuat\\DANH_MUC_THAM_SO.xlsx (bản cũ tự sao lưu).</p></aside></div>`
  );
}
async function saveSettings() {
  const s = state.settingsDraft;
  if (!String(s.ip).trim() || !s.cong || Number(s.cong) < 1 || Number(s.cong) > 65535) {
    toast("Nhập địa chỉ IP và cổng hợp lệ.", "danger");
    return;
  }
  try {
    state.settings = await post("/api/cai_dat", {
      may_ai: { ip: s.ip, cong: Number(s.cong), model: s.model },
      trich_xuat: { ra_lai: !!s.ra_lai },
      nguon_ai: s.nguon || "local",
      cloud: { bat: !!s.cloud, nha_cung_cap: s.ncc, model: s.cloudModel, ty_le: Number(s.tyLe) || 0 },
      ocr: { che_do: s.ocrCheDo, thu_muc: s.ocrThuMuc || "", cho_toi_da: Number(s.ocrCho) || 1800 },
    });
    loadOcr(true);
    state.settingsDirty = false;
    state.settingsDraft = draftFrom(state.settings);
    await refreshAI(true);
    render();
    toast("Đã lưu cài đặt.");
  } catch (e) {
    toast(e.message, "danger");
  }
}
async function handleSettings(action, el) {
  const s = state.settingsDraft;
  if (action === "settings-save") return saveSettings();
  if (action === "settings-copy") {
    const txt = el?.dataset?.text || "";
    try {
      await navigator.clipboard.writeText(txt);
      toast("Đã chép đường dẫn.");
    } catch (e) {
      toast(txt, "info");
    }
    return;
  }
  if (action === "settings-cloud-test") {
    state.cloudTest = null;
    const r = document.getElementById("cloud-test-result");
    if (r) r.textContent = "Đang gọi thử…";
    try {
      state.cloudTest = await post("/api/cai_dat/thu_cloud", { nha_cung_cap: s.ncc, model: s.cloudModel });
    } catch (e) {
      state.cloudTest = { ok: false, loi: e.message };
    }
    toast(state.cloudTest.ok ? `Kết nối ${state.cloudTest.model} được (${state.cloudTest.giay} giây).` : state.cloudTest.loi, state.cloudTest.ok ? "success" : "danger");
    render();
    return;
  }
  if (action === "settings-ocr-test") {
    try {
      await post("/api/ocr/chay_thu", {});
      toast("Đã đưa PDF thử vào thư mục in — chờ ABBYY (≤ 1–2 phút). Kết quả hiện ở Việc đang chạy.", "info");
      refreshJobs();
    } catch (e) {
      toast(e.message, "danger");
    }
    return;
  }
  if (action === "settings-ocr-check") {
    state.ocr = null;
    render();
    return loadOcr(true);
  }
  if (action === "settings-eye") {
    const input = document.getElementById("cloud-key");
    input.type = input.type === "password" ? "text" : "password";
    return;
  }
  if (action === "settings-save-key") {
    const k = document.getElementById("cloud-key")?.value.trim();
    if (!k) return toast("Dán API key vào ô trước khi lưu.", "warning");
    try {
      await post("/api/cai_dat/khoa", { nha_cung_cap: s.ncc, khoa: k });
      toast("Đã lưu API key (chỉ trên máy này).");
      loadSettings();
    } catch (e) {
      toast(e.message, "danger");
    }
    return;
  }
  if (action === "settings-delete-key")
    return openModal({
      title: "Xóa API key đã lưu?",
      body: "<p>Kiểm tra chéo cloud sẽ cần key mới trước khi chạy.</p>",
      confirmLabel: "Xóa key",
      danger: true,
      onConfirm: async () => {
        await api("DELETE", `/api/cai_dat/khoa/${s.ncc}`);
        toast("Đã xóa key.");
        loadSettings();
      },
    });
  if (action === "settings-connect") {
    const out = document.getElementById("connect-result");
    if (out) out.textContent = "Đang kiểm tra…";
    try {
      const k = await post("/api/cai_dat/kiem_tra_ai", { ip: s.ip, cong: Number(s.cong), model: s.model });
      if (k.models?.length) s.models = k.models;
      render();
      toast(k.ok ? `Máy AI kết nối được${k.giay != null ? ` · trả lời thử ${k.giay}s` : ""}.` : k.loi, k.ok ? "success" : "danger");
      if (k.ok && !state.settingsDirty) refreshAI(true);
    } catch (e) {
      if (out) out.textContent = "";
      toast(e.message, "danger");
    }
    return;
  }
  if (action === "settings-discover") {
    try {
      const v = await post("/api/cai_dat/tim_may_ai", {});
      openDrawer({ title: "Máy AI trong mạng LAN", body: `<p class="muted small" id="discover-status">Đang dò các máy trong mạng…</p>` });
      const kq = await choViec(v.id, (x) => {
        const el = document.getElementById("discover-status");
        if (el) el.textContent = x.thong_bao || "Đang dò…";
      });
      const ds = kq.ket_qua?.may || [];
      openDrawer({
        title: "Máy AI trong mạng LAN",
        body: ds.length
          ? `<p class="muted small" style="margin-bottom:20px">Tìm thấy ${ds.length} máy đang chạy Ollama.</p>${ds.map((m) => `<div class="panel"><div class="panel-head"><strong>${E(m.ip)} : ${E(s.cong || 11434)}</strong>${badge("Có Ollama", "success")}</div><div class="panel-body"><p>${E(m.models.join(" · ") || "Chưa có model")}</p><button class="btn btn-primary" data-action="settings-select-server" data-ip="${E(m.ip)}" style="margin-top:20px">Dùng máy này</button></div></div>`).join("")}`
          : `<div class="empty-state">${icon("search", 32)}<h2>Không tìm thấy máy AI</h2><p>Kiểm tra máy AI đang bật, Ollama đang chạy với OLLAMA_HOST=0.0.0.0 và tường lửa mở cổng 11434.</p></div>`,
      });
    } catch (e) {
      toast(e.message, "danger");
    }
    return;
  }
  if (action === "settings-log") {
    try {
      const d = await get("/api/cai_dat/nhat_ky_gui_ngoai");
      openDrawer({
        title: "Nhật ký gửi ra ngoài",
        body: `${badge(state.settings?.cloud?.bat ? "Cloud đang bật mặc định" : "Cloud tắt mặc định", "neutral")}<p class="muted small" style="margin:16px 0">Mỗi lần gửi lưu nhà cung cấp, model, ô được chọn, nội dung đã che và nội dung nhận về. Không lưu API key.</p>${d.ds.length ? `<table class="data-table"><thead><tr><th>Thời gian</th><th>Hợp đồng</th><th></th></tr></thead><tbody>${d.ds.map((x) => `<tr><td>${E(x.luc.replace("T", " "))}</td><td>${E(x.hop_dong)}<span class="secondary-cell">Lượt ${E(x.luot)}</span></td><td><a class="btn btn-ghost" href="${x.tai}?xem=1" target="_blank">Mở</a></td></tr>`).join("")}</tbody></table>` : `<div class="empty-state">${icon("lock", 32)}<h2>Chưa có lần gửi nào</h2><p>Khi bật kiểm tra chéo, nhật ký gửi sẽ xuất hiện tại đây.</p></div>`}`,
      });
    } catch (e) {
      toast(e.message, "danger");
    }
    return;
  }
  if (action === "settings-backup")
    return openModal({
      title: "Sao lưu CSDL",
      body: "<p>Chép toàn bộ cơ sở dữ liệu hợp đồng sang thư mục <strong>co_so_du_lieu\\sao_luu\\</strong> kèm ngày giờ.</p>",
      confirmLabel: "Sao lưu",
      onConfirm: async () => {
        try {
          const r = await post("/api/csdl/sao_luu");
          toast("Đã sao lưu: " + r.file);
        } catch (e) {
          toast(e.message, "danger");
        }
      },
    });
  if (action === "settings-export") {
    try {
      const r = await post("/api/csdl/xuat_excel", {});
      location.href = r.tai;
    } catch (e) {
      toast(e.message, "danger");
    }
  }
}

// ------------------------------------------------------------------ khung
// Giữ vị trí cuộn của các bảng / khung cuộn và ô đang gõ khi vẽ lại cùng một màn hình
const KHUNG_CUON = ".table-wrap, .sheet-preview, .ex-log, .drawer-body, .modal-body, [data-giu-cuon]";
let manTruoc = null;
function khoaO(el) {
  if (el.id) return `#${CSS.escape(el.id)}`;
  const attrs = Array.from(el.attributes).filter((a) => a.name.startsWith("data-") && a.name !== "data-cur");
  if (!attrs.length) return null;
  return el.tagName.toLowerCase() + attrs.map((a) => `[${a.name}="${CSS.escape(a.value)}"]`).join("");
}
function giuTrangThai() {
  const app = document.getElementById("app");
  const g = { view: manTruoc, cuon: [], focus: null };
  if (!app || manTruoc !== state.view) return g;
  g.cuon = Array.from(app.querySelectorAll(KHUNG_CUON)).map((el) => [el.scrollTop, el.scrollLeft]);
  const a = document.activeElement;
  if (a && app.contains(a) && a.matches("input:not([type=checkbox]):not([type=radio]):not([type=file]), textarea")) {
    const k = khoaO(a);
    if (k) g.focus = { k, v: a.value, s: a.selectionStart, e: a.selectionEnd };
  }
  return g;
}
function traTrangThai(g) {
  const app = document.getElementById("app");
  manTruoc = state.view;
  if (!app || g.view !== state.view) return;
  const ds = app.querySelectorAll(KHUNG_CUON);
  if (ds.length === g.cuon.length)
    ds.forEach((el, i) => {
      el.scrollTop = g.cuon[i][0];
      el.scrollLeft = g.cuon[i][1];
    });
  if (g.focus) {
    let el = null;
    try {
      el = app.querySelector(g.focus.k);
    } catch (e) {
      el = null;
    }
    if (el) {
      if (el.value !== g.focus.v) el.value = g.focus.v;          // chữ đang gõ dở không bị mất
      el.focus({ preventScroll: true });
      try {
        el.setSelectionRange(g.focus.s, g.focus.e);
      } catch (e) {
        /* ô không hỗ trợ chọn */
      }
    } else g.focus = null;
  }
}
function render() {
  const route = location.hash.slice(1).split("/")[0];
  if (titles[route]) state.view = route;
  const jobs = activeJobs();
  const dangO = (id) => state.view === id || (id === "payments" && state.view === "integrity");  // một mục, hai chế độ
  const nav = (id, name, i, sub = false) =>
    `<button class="nav-item ${sub ? "sub" : ""} ${dangO(id) ? "active" : ""}" data-route="${id}" ${dangO(id) ? 'aria-current="page"' : ""}>${icon(i)}<span>${name}</span></button>`;
  const soon = (name, i) => `<button class="nav-item" disabled>${icon(i)}<span>${name}</span><span class="soon">Sắp có</span></button>`;
  let screen = "";
  switch (state.view) {
    case "extraction":
      screen = renderExtraction(ctx);
      break;
    case "contracts":
      screen = renderContracts(ctx);
      break;
    case "appendices":
      screen = renderAppendices(ctx);
      break;
    case "boq":
      screen = renderBOQ(ctx);
      break;
    case "payments":
      screen = renderPayments(ctx);
      break;
    case "integrity":
      screen = renderIntegrity(ctx);
      break;
    case "documents":
      screen = renderChungTu(ctx);
      break;
    case "settings":
      screen = renderSettings();
      break;
    default:
      screen = renderOverview();
  }
  const keep = document.activeElement?.id;
  const giu = giuTrangThai();
  document.getElementById("app").innerHTML =
    `<div class="app-shell"><aside class="sidebar" aria-label="Điều hướng chính"><div class="brand"><div class="brand-mark">${icon("building", 23)}</div><div><div class="brand-name">Bàn kiểm soát</div><div class="brand-subtitle">Hồ sơ thanh toán xây dựng</div></div></div><div class="workspace">${icon("briefcase", 17)}<div><strong>Phòng Tài chính</strong><span>Dữ liệu trên máy này</span></div></div><nav class="nav-scroll">${nav("overview", "Tổng quan", "grid")}<div class="nav-group">Hợp đồng</div>${nav("extraction", "Trích tham số", "scan", true)}${nav("contracts", "Danh mục hợp đồng", "file", true)}${nav("appendices", "Phụ lục", "layers", true)}${nav("boq", "BOQ", "table", true)}<div class="nav-group">Đợt thanh toán</div>${nav("payments", "Kiểm tra đợt", "shield", true)}${nav("documents", "Chứng từ", "folder", true)}${soon("Bản vẽ", "layers")}<div class="nav-group">Phòng dự án</div>${soon("Cổng hồ sơ", "building")}</nav><div class="nav-footer">${nav("settings", "Cài đặt", "settings")}<div class="user-profile"><div class="avatar">TC</div><div><strong>Giám đốc Tài chính</strong><span>Quyền review và xác nhận</span></div></div></div></aside><div class="main-shell"><header class="topbar"><div class="breadcrumbs"><button class="icon-btn mobile-menu" style="display:none" data-action="mobile-menu" aria-label="Mở menu">${icon("menu")}</button><span>${sections[state.view]}</span>${icon("chevron")}<strong>${titles[state.view]}</strong></div><div class="top-actions">${connectionButton()}<button class="jobs-button" data-action="jobs-open">${icon("activity", 18)} Việc đang chạy <span class="count-pill">${jobs.length}</span></button></div></header><main class="content" id="main-content">${screen}</main></div></div>`;
  // ô chọn hợp đồng có lọc: bộ lọc dùng chung nên khi vào màn khác, hợp đồng đang chọn có thể không còn trong danh sách lọc
  const pick = document.querySelector("[data-hd-pick]");
  if (pick && pick.value !== pick.dataset.cur && (pick.value || pick.dataset.cur))
    setTimeout(() => {
      const p2 = document.querySelector("[data-hd-pick]");
      if (p2 && p2.value !== p2.dataset.cur) p2.dispatchEvent(new Event("change", { bubbles: true }));
    }, 0);
  traTrangThai(giu);
  if (keep && !giu.focus) {
    const el = document.getElementById(keep);
    if (el && el.matches("input[type=search],input[type=text]:not([data-keep-focus=no])")) {
      el.focus({ preventScroll: true });
      try {
        el.setSelectionRange(el.value.length, el.value.length);
      } catch (e) {
        /* ô không hỗ trợ chọn */
      }
    }
  }
}
function loadView() {
  if (state.view === "overview") loadOverview();
  else if (state.view === "settings") {
    loadSettings();
    loadOcr();
  }
  else if (state.view === "extraction") loadExtraction(ctx);
  else if (["contracts", "appendices", "boq"].includes(state.view)) loadContracts(ctx);
  else if (["payments", "integrity"].includes(state.view)) loadChecks(ctx);
  else if (state.view === "documents") loadChungTu(ctx);
}

document.addEventListener("click", (e) => {
  const route = e.target.closest("[data-route]");
  if (route && !route.disabled) {
    e.preventDefault();
    if (route.classList.contains("nav-item") && route.dataset.route === "contracts" && state.hd) state.hd.selected = null;
    navigate(route.dataset.route);
    return;
  }
  const el = e.target.closest("[data-action]");
  if (!el || el.disabled) return;
  const action = el.dataset.action;
  if (action === "overlay-close") return closeOverlay();
  if (action === "modal-confirm") {
    const config = modalConfig;
    const reason = document.getElementById("dialog-reason")?.value.trim();
    if (config?.requireReason && !reason) {
      document.getElementById("reason-error").hidden = false;
      document.getElementById("dialog-reason").focus();
      return;
    }
    const vals = Object.fromEntries(Array.from(document.querySelectorAll(".modal [data-modal-field]")).map((x) => [x.dataset.modalField, x.value]));
    closeOverlay();
    config?.onConfirm?.(reason, vals);
    return;
  }
  if (action === "jobs-open") return jobsDrawer();
  if (action === "job-stop")
    return openModal({
      title: "Dừng công việc?",
      body: "<p>Việc đang chạy sẽ dừng. Các kết quả đã hoàn tất được giữ lại.</p>",
      confirmLabel: "Dừng công việc",
      danger: true,
      onConfirm: async () => {
        try {
          await post(`/api/viec/${encodeURIComponent(el.dataset.id)}/dung`);
          toast("Đã gửi lệnh dừng.", "warning");
          refreshJobs();
        } catch (err) {
          toast(err.message, "danger");
        }
      },
    });
  if (action === "mobile-menu") return document.querySelector(".sidebar").classList.toggle("mobile-open");
  if (action === "recent-sort") {
    state.recentSort = !state.recentSort;
    return render();
  }
  if (action === "recent-open") {
    const r = state.overview?.viec_gan_day?.[Number(el.dataset.i)];
    if (!r) return;
    return navigate(r.route, { ma: r.ma, loai: r.loai });
  }
  if (action === "alert-open") {
    const a = state.overview?.can_xem_xet?.[Number(el.dataset.i)];
    if (!a) return;
    return navigate(a.route, { ma: a.ma, loai: a.loai === "dot" ? "kiem_tra_dot" : a.loai });
  }
  if (action === "open-payment") return navigate("payments", { ma: el.dataset.ma, loai: "kiem_tra_dot" });
  if (action === "settings-select-server") {
    state.settingsDraft.ip = el.dataset.ip;
    state.settingsDirty = true;
    closeOverlay();
    render();
    toast("Đã chọn máy AI — bấm Lưu cài đặt để áp dụng.");
    return;
  }
  if (action.startsWith("settings-")) return handleSettings(action, el);
  if (handleExtractionAction(action, el, ctx)) return;
  if (handleContractAction(action, el, ctx)) return;
  if (handleCheckAction(action, el, ctx)) return;
  if (handleChungTuAction(action, el, ctx)) return;
});
// bộ lọc chọn hợp đồng (chon_hd.js): Bên A / Dự án / từ khoá — dùng chung mọi màn hình
let henChon = null;
function locHopDong(el) {
  const loc = (state.hdLoc = state.hdLoc || { ben_a: "", du_an: "", q: "" });
  loc[el.dataset.hdLoc] = el.value;
  if (el.dataset.hdLoc === "ben_a") loc.du_an = "";
  render();
  clearTimeout(henChon);
  henChon = setTimeout(
    () => {
      const sel = document.querySelector("[data-hd-pick]");
      if (sel && sel.value !== sel.dataset.cur) sel.dispatchEvent(new Event("change", { bubbles: true })); // "" = không còn hợp đồng phù hợp
    },
    el.type === "search" ? 400 : 0,
  );
}
document.addEventListener("change", (e) => {
  const el = e.target;
  if (el.type === "search") return;
  if (el.dataset.hdLoc !== undefined) return locHopDong(el);
  if (el.id === "recent-filter") {
    state.recentFilter = el.value;
    return render();
  }
  if (el.id === "settings-cloud") {
    state.settingsDraft.cloud = el.checked;
    state.settingsDirty = true;
    return render();
  }
  if (el.dataset.setting && state.settingsDraft) {
    const key = el.dataset.setting;
    state.settingsDraft[key] = el.type === "checkbox" ? el.checked : el.type === "number" ? Number(el.value) : el.value;
    state.settingsDirty = true;
    if (key === "ncc") {
      state.settingsDraft.cloudModel = "";
      render();
    }
    if (key === "nguon") render();
    return;
  }
  if (el.type === "file") {
    const id = el.dataset.folderFor || el.id;
    const selection = document.querySelector(`[data-selection="${id}"]`);
    if (selection)
      selection.textContent = el.files.length
        ? `${el.files.length} file đã chọn · ${Array.from(el.files)
            .slice(0, 3)
            .map((f) => f.name)
            .join(", ")}`
        : "";
  }
  if (handleExtractionChange(el, ctx)) return;
  if (handleContractChange(el, ctx)) return;
  if (state.view === "documents" && handleChungTuChange(el, ctx)) return;
  handleCheckChange(el, ctx);
});
document.addEventListener("input", (e) => {
  const el = e.target;
  if (el.dataset.setting && el.id !== "cloud-key" && state.settingsDraft) {
    state.settingsDraft[el.dataset.setting] = el.type === "number" ? Number(el.value) : el.value;
    state.settingsDirty = true;
  }
  if (el.dataset.hdLoc !== undefined) return locHopDong(el);
  if (el.matches("input[type=search]")) {
    if (handleExtractionChange(el, ctx)) return;
    if (handleContractChange(el, ctx)) return;
    handleCheckChange(el, ctx);
  }
});
document.addEventListener("dragover", (e) => {
  const zone = e.target.closest("[data-drop]");
  if (zone) {
    e.preventDefault();
    zone.classList.add("drag-over");
  }
});
document.addEventListener("dragleave", (e) => e.target.closest("[data-drop]")?.classList.remove("drag-over"));
document.addEventListener("drop", (e) => {
  const zone = e.target.closest("[data-drop]");
  if (!zone) return;
  e.preventDefault();
  zone.classList.remove("drag-over");
  const input = document.getElementById(zone.dataset.drop);
  const accepted = input.accept.split(",").map((x) => x.trim().toLowerCase());
  const files = Array.from(e.dataTransfer.files).filter((f) => accepted.some((a) => f.name.toLowerCase().endsWith(a)));
  if (!files.length) return toast("Định dạng file không phù hợp với vùng nạp này.", "danger");
  const data = new DataTransfer();
  (input.multiple ? files : files.slice(0, 1)).forEach((f) => data.items.add(f));
  input.files = data.files;
  input.dispatchEvent(new Event("change", { bubbles: true }));
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeOverlay();
    document.querySelector(".sidebar")?.classList.remove("mobile-open");
  }
  if (e.key === "Tab" && (modalConfig || drawerConfig)) {
    const box = document.querySelector(".modal,.drawer"),
      items = Array.from(
        box?.querySelectorAll("button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),summary") || [],
      ).filter((x) => x.offsetParent !== null);
    const first = items[0],
      last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
});
window.addEventListener("hashchange", () => {
  const r = location.hash.slice(1).split("/")[0];
  if (titles[r] && r !== state.view) {
    state.view = r;
    closeOverlay();
    render();
    loadView();
  }
});

// nhịp: việc đang chạy 2 giây/lần khi có việc, 8 giây/lần khi rảnh; máy AI 30 giây/lần
let nhip = 0;
setInterval(() => {
  nhip++;
  if (activeJobs().length || nhip % 4 === 0) refreshJobs();
}, 2000);
setInterval(() => refreshAI(), 30000);
(async () => {
  try {
    const h = await get("/api/he_thong");
    state.phienBan = `Phiên bản ${h.phien_ban}`;
    state.ai = h.ai;
  } catch (e) {
    toast(e.message, "danger");
  }
  render();
  refreshJobs();
  loadView();
})();
render();
