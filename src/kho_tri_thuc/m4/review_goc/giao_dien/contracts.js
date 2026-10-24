// contracts.js — Danh mục hợp đồng, Phụ lục, BOQ: dữ liệu thật từ CSDL SQLite (xem API.md).
// Bố cục, lớp CSS theo thiết kế "Bàn kiểm soát" (Claude Design).
import { icon, badge, escapeHTML, upload, header } from "./ui.js";
import { get, post, upload as uploadFile, money, num, fmtDate, today } from "./api.js";
import { chonHopDong } from "./chon_hd.js";
import { renderPLAI, handlePLAIAction, handlePLAIChange, loadPLAI } from "./phu_luc_ai.js";

const E = escapeHTML;
const COLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
const TRUONG = [
  ["stt", "STT", false],
  ["ma_rieng", "Mã hạng mục (phòng Dự án đặt)", false],
  ["ten", "Tên công việc", true],
  ["dvt", "Đơn vị tính", true],
  ["kl", "Khối lượng", true],
  ["don_gia", "Đơn giá", true],
  ["thanh_tien", "Thành tiền", false],
];
const dg = (v) => (v === null || v === undefined || Number.isInteger(Number(v)) ? money(v) : num(v));
const MUC_KT = { CHẶN: "danger", ĐỎ: "danger", VÀNG: "warning", ĐẠT: "success", "THÔNG TIN": "info" };

function s(ctx) {
  if (!ctx.state.hd)
    ctx.state.hd = {
      list: null,
      listErr: "",
      query: "",
      type: "all",
      risk: "all",
      selected: null,
      detail: null,
      detailErr: "",
      detailTab: "parameters",
      detailDate: today(),
      detailBoq: null,
      paramGroup: "all",
      amendedOnly: false,
      chuaXacNhan: false,
      appendixContract: null,
      appendixDetail: null,
      appendixStatus: "all",
      phieu: null, // {file, ket_qua, ghi}
      boqContract: null,
      boqDate: today(),
      boqQuery: "",
      boqView: "effective",
      boq: null,
      boqErr: "",
      imp: null, // {file, tep, ten, sheets, sheet, xem, hang, cot, kt, ghi, chapNhan, doan, tuLoat}
      loat: null, // nạp cả loạt: {dong: [{id, ten, tep, sheets, sheet, xem, hang, cot, doan, ma, kt, loi, chon, ghi, ghiLoi, dang}], dang, dangGhi}
      busy: false,
    };
  return ctx.state.hd;
}
function button(action, label, kind = "", attrs = "") {
  return `<button class="btn ${kind}" data-action="${action}" ${attrs}>${label}</button>`;
}
function gon(ten) {
  return String(ten || "")
    .replace(/^Công ty (Cổ phần|CP|TNHH( MTV)?)\s+/i, "")
    .trim();
}
function risk(h) {
  if (h.co_do) return ["red", `${h.co_do} cờ đỏ`];
  if (h.chua_xac_nhan) return ["warning", `${h.chua_xac_nhan} ô cần xác nhận`];
  if (h.co_vang) return ["warning", `${h.co_vang} cảnh báo vàng`];
  if (!h.so_tham_so) return ["neutral", "Chưa có tham số"];
  return ["success", "Đủ tham số"];
}
function isNum(v) {
  return v !== null && v !== "" && v !== undefined && !isNaN(Number(v)) && /^-?[\d.,]+$/.test(String(v).trim());
}
function giaTri(v, donVi) {
  if (v === null || v === undefined || v === "") return '<span class="muted">—</span>';
  if (typeof v === "number") return /đồng|vnd/i.test(donVi || "") || Math.abs(v) >= 100000 ? money(v) : num(v);
  return E(v);
}
function csv(name, headers, rows) {
  const q = (x) => {
    const t = x === null || x === undefined ? "" : String(x);
    return /[",;\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t;
  };
  const text = "﻿" + [headers, ...rows].map((r) => r.map(q).join(",")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  a.download = name + ".csv";
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(a.href);
    a.remove();
  }, 500);
}
function style() {
  return `<style>
    .contracts-screen .contract-code{font-weight:700;color:#173e66}
    .contracts-screen .subline{display:block;color:#718095;font-size:11px;margin-top:4px;line-height:1.45}
    .contracts-screen .table-link{padding:0;border:0;background:none;color:#173e66;font:inherit;font-weight:650;cursor:pointer;min-height:40px;text-align:left}
    .contracts-screen .contract-banner{display:flex;justify-content:space-between;gap:24px;padding:18px 22px;background:#edf3f9;border-left:3px solid #284d78;border-radius:4px;margin-bottom:20px}
    .contracts-screen .contract-banner strong{display:block;font-size:16px;margin-bottom:5px}
    .contracts-screen .contract-banner .numeric{white-space:nowrap;align-self:center}
    .contracts-screen .contract-banner .amount{display:block;font-size:24px;font-weight:750;letter-spacing:-.5px}
    .contracts-screen .contract-summary{display:flex;gap:0;border:1px solid var(--border,#dbe2eb);background:white;border-radius:5px;margin-bottom:20px}
    .contracts-screen .contract-summary>div{flex:1;padding:16px 20px;border-right:1px solid var(--border,#dbe2eb)}
    .contracts-screen .contract-summary>div:last-child{border:0}
    .contracts-screen .contract-summary strong{display:block;font-size:17px;margin-top:7px}
    .contracts-screen .check-code{font-weight:650;white-space:nowrap}
    .contracts-screen .check-summary{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:14px 18px;background:#f5f7fa;border-bottom:1px solid #dbe2eb}
    .contracts-screen .check-summary .counts{display:flex;gap:8px;flex-wrap:wrap}
    .contracts-screen .import-step{display:flex;gap:8px;margin:0 0 20px;flex-wrap:wrap}
    .contracts-screen .import-step span{padding:9px 12px;background:#f1f4f8;border-radius:4px;color:#6d7c90;font-size:12px}
    .contracts-screen .import-step .active{background:#e7eef8;color:#244b7d;font-weight:700}
    .contracts-screen .mapping-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
    .contracts-screen .equation{display:grid;grid-template-columns:1fr 24px 1fr 24px 1fr;gap:10px;align-items:center;background:#f4f7fb;border:1px solid #dbe2eb;border-radius:4px;padding:20px;margin:18px 0}
    .contracts-screen .equation strong{display:block;margin-top:6px;font-size:17px;font-variant-numeric:tabular-nums}
    .contracts-screen .source-change{display:block;font-size:11px;color:#527395;margin-top:5px;line-height:1.5}
    .contracts-screen .table-foot{padding:12px 18px;color:#718095;font-size:12px;border-top:1px solid #e2e7ee;display:flex;justify-content:space-between;gap:16px}
    .contracts-screen .citation{max-width:340px;font-size:12px;line-height:1.55;color:#526176}
    .contracts-screen .amended-row{background:#f3f7fc}
    .contracts-screen .unconfirmed-row{background:#fffaf0}
    .contracts-screen .panel>.toolbar{padding:16px 20px;align-items:flex-end;border-bottom:1px solid #e2e7ee}
    .contracts-screen .panel>.toolbar .check-field{min-height:44px}
    .contracts-screen .contract-list{table-layout:fixed;min-width:1000px}
    .contracts-screen .contract-list td{vertical-align:top;overflow-wrap:anywhere}
    .contracts-screen .contract-list td:first-child .table-link{white-space:nowrap;min-height:0}
    .contracts-screen .contract-list .badge{white-space:normal}
    .contracts-screen .contract-list .clamp{-webkit-line-clamp:2}
    .contracts-screen .clamp{display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
    .contracts-screen .param-table{table-layout:fixed;min-width:1100px}
    .contracts-screen .param-table td{vertical-align:top}
    .contracts-screen input[type="checkbox"]{width:16px;height:16px;accent-color:#244b7d}
    .contracts-screen .check-field{display:inline-flex;gap:9px;align-items:center;min-height:40px;font-size:12px}
    .contracts-screen .positive-delta{color:#244b7d;font-weight:650}
    .contracts-screen .negative-delta{color:#ad3943;font-weight:650}
    .contracts-screen .boq-tabs{margin-bottom:20px}
    .contracts-screen .boq-up .up-title{display:block;font-size:12px;color:#526176;margin-bottom:8px}
    .contracts-screen .boq-loat{min-width:1060px}
    .contracts-screen .boq-loat td{vertical-align:top}
    .contracts-screen .boq-loat td:nth-child(2){min-width:190px;max-width:260px}
    .contracts-screen .boq-loat td:nth-child(3){min-width:200px}
    .contracts-screen .boq-loat td.numeric,.contracts-screen .boq-loat th{white-space:nowrap}
    .contracts-screen .boq-loat td:nth-child(9){min-width:150px}
    .contracts-screen .boq-loat .badge{white-space:nowrap}
    .contracts-screen .inline-help{font-size:12px;color:#718095;line-height:1.6;margin:9px 0 0}
    .contracts-screen .notice{display:block;line-height:1.65}
    .contracts-screen .notice strong{display:inline}
    .contracts-screen .notice svg{display:inline-block;vertical-align:middle;margin:-2px 6px 0 0}
    .contracts-screen .panel+.panel{margin-top:20px}
    .contracts-screen .sheet-preview{max-height:300px;overflow:auto;border:1px solid #dbe2eb;border-radius:4px;margin:16px 0}
    .contracts-screen .sheet-preview table{border-collapse:collapse;font-size:11px;min-width:100%}
    .contracts-screen .sheet-preview td,.contracts-screen .sheet-preview th{border:1px solid #e2e7ee;padding:4px 7px;white-space:nowrap;max-width:240px;overflow:hidden;text-overflow:ellipsis}
    .contracts-screen .sheet-preview th{background:#f1f4f8;position:sticky;top:0;color:#526176}
    .contracts-screen .sheet-preview tr.header-row td{background:#e7eef8;font-weight:700}
    .contracts-screen .sheet-preview td.rn{color:#8a97a8;background:#f7f9fb;text-align:right}
    @media(max-width:1100px){.contracts-screen .mapping-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.contracts-screen .contract-summary{flex-wrap:wrap}.contracts-screen .contract-summary>div{flex-basis:50%;border-bottom:1px solid #dbe2eb}.contracts-screen .equation{grid-template-columns:1fr}.contracts-screen .equation .operator{display:none}}
    @media(max-width:700px){.contracts-screen .contract-banner{flex-direction:column}.contracts-screen .contract-banner .numeric{align-self:flex-start;text-align:left}.contracts-screen .mapping-grid{grid-template-columns:1fr}.contracts-screen .check-summary{align-items:flex-start;flex-direction:column}}
  </style>`;
}
function loading(text = "Đang tải…") {
  return `<div class="panel-body muted">${E(text)}</div>`;
}
function errBox(msg) {
  return `<div class="notice notice-danger">${icon("alert")} <strong>Không tải được dữ liệu.</strong> ${E(msg)}</div>`;
}

// ================================================================== tải dữ liệu
async function loadList(ctx) {
  const ui = s(ctx);
  try {
    ui.list = (await get("/api/hop_dong")).ds;
    ui.listErr = "";
  } catch (e) {
    ui.listErr = e.message;
    ui.list = ui.list || [];
  }
  const dau = ui.list[0]?.ma_hd || "";
  // null = chưa chọn lần nào → hợp đồng đầu; "" = bộ lọc không còn hợp đồng nào → giữ trống
  if (ui.appendixContract == null || (ui.appendixContract && !ui.list.some((h) => h.ma_hd === ui.appendixContract))) ui.appendixContract = dau;
  if (ui.boqContract == null || (ui.boqContract && !ui.list.some((h) => h.ma_hd === ui.boqContract))) ui.boqContract = dau;
}
async function loadDetail(ctx) {
  const ui = s(ctx);
  if (!ui.selected) return;
  try {
    ui.detail = await get(`/api/hop_dong/${encodeURIComponent(ui.selected)}?ngay=${ui.detailDate}`);
    ui.detailErr = "";
  } catch (e) {
    ui.detail = null;
    ui.detailErr = e.message;
  }
  if (ui.detailTab === "boq") await loadDetailBoq(ctx);
}
async function loadDetailBoq(ctx) {
  const ui = s(ctx);
  try {
    ui.detailBoq = await get(`/api/hop_dong/${encodeURIComponent(ui.selected)}/boq?ngay=${ui.detailDate}`);
  } catch (e) {
    ui.detailBoq = { loi: e.message };
  }
}
async function loadAppendix(ctx) {
  const ui = s(ctx);
  if (!ui.appendixContract) return (ui.appendixDetail = null);
  try {
    ui.appendixDetail = await get(`/api/hop_dong/${encodeURIComponent(ui.appendixContract)}`);
  } catch (e) {
    ui.appendixDetail = { loi: e.message };
  }
}
async function loadBoq(ctx) {
  const ui = s(ctx);
  if (!ui.boqContract) return (ui.boq = null);
  try {
    ui.boq = await get(`/api/hop_dong/${encodeURIComponent(ui.boqContract)}/boq?ngay=${ui.boqDate}`);
    ui.boqErr = "";
  } catch (e) {
    ui.boq = null;
    ui.boqErr = e.message;
  }
}
export async function loadContracts(ctx) {
  const ui = s(ctx);
  const view = ctx.state.view;
  const opts = ctx.state.navOpts || {};
  ctx.state.navOpts = null;
  await loadList(ctx);
  if (opts.ma && ui.list.some((h) => h.ma_hd === opts.ma)) {
    if (view === "contracts") {
      ui.selected = opts.ma;
      ui.detailTab = "parameters";
      ui.chuaXacNhan = opts.loai === "tham_so";
      ui.detail = null;
    } else if (view === "appendices") ui.appendixContract = opts.ma;
    else if (view === "boq") {
      ui.boqContract = opts.ma;
      if (opts.ngay) ui.boqDate = opts.ngay;
      ui.boqView = "effective";
    }
  }
  if (view === "contracts") await loadDetail(ctx);
  else if (view === "appendices") await Promise.all([loadAppendix(ctx), loadPLAI(ctx)]);
  else if (view === "boq") await loadBoq(ctx);
  if (["contracts", "appendices", "boq"].includes(ctx.state.view)) ctx.render();
}
async function reload(ctx, fn) {
  await fn(ctx);
  ctx.render();
}

// ================================================================== Danh mục hợp đồng
export function renderContracts(ctx) {
  const ui = s(ctx);
  if (ui.selected) return renderContractDetail(ctx, ui);
  const head = header(
    "Danh mục hợp đồng",
    "Một nguồn dữ liệu cho hợp đồng, phụ lục và các đợt thanh toán.",
    `${button("contracts-export", `${icon("download")} Xuất Excel CSDL`, "btn-ghost")}${button("contracts-new", `${icon("plus")} Trích hợp đồng mới`, "btn-primary")}`,
  );
  if (!ui.list) return `<div class="contracts-screen">${style()}${head}<section class="panel">${loading()}</section></div>`;
  const ds = ui.list;
  const q = ui.query.trim().toLocaleLowerCase("vi");
  const filtered = ds.filter((h) => {
    const [r] = risk(h);
    return (
      (!q || `${h.ma_hd} ${h.so_hd} ${h.ben_a || ""} ${h.ben_b || ""} ${h.du_an || ""} ${h.goi_thau || ""}`.toLocaleLowerCase("vi").includes(q)) &&
      (ui.type === "all" || h.loai_gia === ui.type) &&
      (ui.risk === "all" || r === ui.risk)
    );
  });
  const tongHl = ds.reduce((a, h) => a + (Number(h.gt_hieu_luc_hom_nay) || 0), 0);
  const coDo = ds.filter((h) => h.co_do).length;
  const canXn = ds.reduce((a, h) => a + (h.chua_xac_nhan || 0), 0);
  return `<div class="contracts-screen">${style()}${head}
    ${ui.listErr ? errBox(ui.listErr) : ""}
    <div class="contract-summary">
      <div><span class="muted small">Hợp đồng trong CSDL</span><strong>${ds.length} hợp đồng</strong></div>
      <div><span class="muted small">Giá trị hiệu lực hôm nay (sau VAT)</span><strong>${money(tongHl)}</strong></div>
      <div><span class="muted small">Cần người ký xem xét</span><strong>${coDo ? `${coDo} hợp đồng có cờ đỏ` : "Không có cờ đỏ"}</strong></div>
      <div><span class="muted small">Tham số chưa xác nhận</span><strong>${canXn}</strong></div>
    </div>
    <section class="panel">
      <div class="panel-head"><div><strong>Sổ hợp đồng</strong><span class="subline">Bấm số hợp đồng để xem tham số, nguồn trích và lịch sử thay đổi.</span></div>${badge(`${filtered.length} / ${ds.length} hợp đồng`, "neutral")}</div>
      <div class="toolbar">
        <label class="field" style="flex:1;min-width:240px"><span>Tìm hợp đồng</span><input type="search" id="contract-search" data-contract-field="query" value="${E(ui.query)}" placeholder="Số HĐ, bên A, bên B hoặc dự án" aria-label="Tìm hợp đồng"></label>
        <label class="field"><span>Trạng thái dữ liệu</span><select data-contract-field="risk"><option value="all">Tất cả trạng thái</option><option value="red" ${ui.risk === "red" ? "selected" : ""}>Có cờ đỏ</option><option value="warning" ${ui.risk === "warning" ? "selected" : ""}>Cần xác nhận</option><option value="success" ${ui.risk === "success" ? "selected" : ""}>Đủ tham số</option></select></label>
        ${button("contracts-clear", "Xóa bộ lọc", "btn-ghost")}
      </div>
      ${
        !ds.length
          ? `<div class="empty-state">${icon("database", 32)}<h3>CSDL chưa có hợp đồng</h3><p>Trích tham số hợp đồng, xác nhận các ô vàng rồi bấm "Nạp CSDL" ở màn hình Trích tham số.</p><button class="btn btn-primary" data-route="extraction">${icon("scan")} Trích tham số</button></div>`
          : filtered.length
            ? `<div class="table-wrap"><table class="data-table contract-list"><colgroup><col style="width:18%"><col style="width:15%"><col style="width:15%"><col style="width:20%"><col style="width:12%"><col style="width:6%"><col style="width:14%"></colgroup><thead><tr><th>Số hợp đồng</th><th>Bên A</th><th>Bên B</th><th>Dự án</th><th class="numeric">Giá trị (sau VAT)</th><th class="numeric">Phụ lục</th><th>Kiểm tra</th></tr></thead><tbody>${filtered
                .map((h) => {
                  const [r, t] = risk(h);
                  const doi = Math.abs((Number(h.gt_hieu_luc_hom_nay) || 0) - (Number(h.gt_sau_vat_goc) || 0)) >= 1;
                  return `<tr><td><button class="table-link" data-action="contract-open" data-id="${E(h.ma_hd)}" title="${E(h.ma_hd)}">${E(h.so_hd)}</button></td><td title="${E(h.ben_a || "")}">${E(gon(h.ben_a) || "—")}</td><td title="${E(h.ben_b || "")}">${E(gon(h.ben_b) || "—")}</td><td><span class="clamp" title="${E(h.du_an || h.goi_thau || "")}">${E(h.du_an || h.goi_thau || "—")}</span></td><td class="numeric"><strong>${money(h.gt_hieu_luc_hom_nay)}</strong>${doi ? `<span class="subline">Gốc ${money(h.gt_sau_vat_goc)}</span>` : ""}</td><td class="numeric">${h.so_phu_luc || "—"}</td><td>${badge(t, r)}${h.so_boq ? "" : '<span class="subline">Chưa có BOQ</span>'}</td></tr>`;
                })
                .join("")}</tbody></table></div><div class="table-foot"><span>Giá trị = gốc + phụ lục đã ký có hiệu lực đến hôm nay</span><span>${filtered.length} hợp đồng</span></div>`
            : `<div class="empty-state">${icon("search")}<h3>Không tìm thấy hợp đồng</h3><p>Thử tên nhà thầu khác hoặc xóa bộ lọc để xem toàn bộ danh mục.</p>${button("contracts-clear", "Xóa bộ lọc", "btn-primary")}</div>`
      }
    </section>
  </div>`;
}

function paramRows(ui) {
  const d = ui.detail;
  return (d?.tham_so || []).filter(
    (p) =>
      (ui.paramGroup === "all" || p.nhom === ui.paramGroup) &&
      (!ui.amendedOnly || p.nguon_hieu_luc !== "HĐ gốc") &&
      (!ui.chuaXacNhan || (p.nguon_trich && !p.nguon_trich.da_xac_nhan && !String(p.nguon_trich.kiem_tra || "").startsWith("OK"))),
  );
}
function trangThaiTs(p) {
  const n = p.nguon_trich;
  if (!n) return `${badge("Từ master", "neutral")}${p.trang_thai ? `<span class="subline">${E(p.trang_thai)}</span>` : ""}`;
  if (n.da_xac_nhan) return badge(n.da_sua_tay ? "Đã sửa tay · đã xác nhận" : "Đã xác nhận", "success");
  if (String(n.kiem_tra || "").startsWith("OK")) return badge("Tự kiểm OK", "info");
  return badge("Chưa xác nhận", "warning");
}

function renderContractDetail(ctx, ui) {
  const back = button("contracts-back", `${icon("arrow-left")} Danh mục`, "btn-ghost");
  if (!ui.detail)
    return `<div class="contracts-screen">${style()}${header(`${E(ui.selected)} · Chi tiết hợp đồng`, "", back)}${ui.detailErr ? errBox(ui.detailErr) : `<section class="panel">${loading()}</section>`}</div>`;
  const d = ui.detail;
  const h = d.hop_dong;
  const ts = d.tham_so || [];
  const groups = [...new Set(ts.map((p) => p.nhom).filter(Boolean))];
  const params = paramRows(ui);
  const changed = ts.filter((p) => p.nguon_hieu_luc !== "HĐ gốc").length;
  const chuaXn = ts.filter((p) => p.nguon_trich && !p.nguon_trich.da_xac_nhan && !String(p.nguon_trich.kiem_tra || "").startsWith("OK")).length;
  const coNguon = ts.filter((p) => p.nguon_trich).length;
  const tabs = [
    ["parameters", "Tham số", ts.length],
    ["appendices", "Phụ lục", d.phu_luc.filter((p) => p.trang_thai !== "Đã hủy").length],
    ["boq", "BOQ", null],
    ["payments", "Đợt thanh toán", d.dot.length],
    ["warnings", "Cảnh báo", d.canh_bao.length],
  ];
  const chuaApDung = d.phu_luc.filter((p) => p.trang_thai === "Đã ký" && p.ngay_hieu_luc > d.ngay);
  let body = "";
  if (ui.detailTab === "parameters")
    body = `<div class="toolbar"><label class="field" style="min-width:180px"><span>Giá trị hiệu lực tại ngày</span><input type="date" data-contract-field="detailDate" value="${E(ui.detailDate)}"></label><label class="field"><span>Nhóm tham số</span><select data-contract-field="paramGroup"><option value="all">Tất cả nhóm</option>${groups.map((g) => `<option ${ui.paramGroup === g ? "selected" : ""}>${E(g)}</option>`).join("")}</select></label><label class="check-field"><input type="checkbox" data-contract-field="amendedOnly" ${ui.amendedOnly ? "checked" : ""}> Chỉ tham số đã thay đổi</label><label class="check-field"><input type="checkbox" data-contract-field="chuaXacNhan" ${ui.chuaXacNhan ? "checked" : ""}> Chỉ tham số chưa xác nhận (${chuaXn})</label>${button("contract-date-today", "Dùng ngày hôm nay", "btn-ghost")}</div>
    <div class="notice notice-info">${icon("calendar")} Đang áp dụng phụ lục đã ký có hiệu lực đến <strong>${fmtDate(d.ngay)}</strong>${d.pl_ap_dung.length ? ` (${E(d.pl_ap_dung.join(", "))})` : " — chưa có phụ lục nào"}. Giá trị HĐ sau VAT: <strong>${money(d.gt_hieu_luc)}</strong>.${chuaApDung.length ? ` ${E(chuaApDung.map((p) => `${p.so_pl} hiệu lực ${fmtDate(p.ngay_hieu_luc)}`).join("; "))} chưa được áp dụng.` : ""}</div>
    ${chuaXn ? `<div class="notice notice-warning">${icon("alert")} <strong>${chuaXn} tham số nạp từ trích xuất AI chưa được xác nhận.</strong> Mở "Nguồn" để xem trích dẫn nguyên văn rồi xác nhận — thao tác được ghi nhật ký.</div>` : ""}
    ${
      params.length
        ? `<div class="table-wrap"><table class="data-table param-table"><colgroup><col style="width:92px"><col style="width:140px"><col style="width:20%"><col style="width:20%"><col style="width:130px"><col style="width:26%"><col style="width:150px"></colgroup><thead><tr><th>Mã / nhóm</th><th>Tham số</th><th>Giá trị gốc</th><th>Hiệu lực ${fmtDate(d.ngay)}</th><th>Phụ lục thay đổi</th><th>Điều khoản / trích dẫn</th><th>Nguồn trích</th></tr></thead><tbody>${params
            .map((p) => {
              const amended = p.nguon_hieu_luc !== "HĐ gốc";
              const last = p.lich_su[p.lich_su.length - 1];
              const n = p.nguon_trich;
              const chua = n && !n.da_xac_nhan && !String(n.kiem_tra || "").startsWith("OK");
              return `<tr class="${amended ? "amended-row" : chua ? "unconfirmed-row" : ""}"><td><strong>${E(p.ma_ts)}</strong><span class="subline">${E(p.nhom || "")}</span></td><td>${E(p.ten || "")}${p.don_vi ? `<span class="subline">${E(p.don_vi)}</span>` : ""}</td><td><div class="clamp" title="${E(p.gia_tri ?? "")}">${giaTri(p.gia_tri, p.don_vi)}</div></td><td>${amended ? `<div class="clamp" title="${E(p.gia_tri_hieu_luc ?? "")}"><strong>${giaTri(p.gia_tri_hieu_luc, p.don_vi)}</strong></div>` : '<span class="muted small">= giá trị gốc</span>'}</td><td>${amended ? `${badge(p.nguon_hieu_luc, "info")}<span class="source-change">${giaTri(last?.cu, p.don_vi)} → ${giaTri(last?.moi, p.don_vi)}</span>` : '<span class="muted">HĐ gốc</span>'}</td><td class="citation"><strong>${E(p.dieu_khoan || "")}</strong><span class="subline clamp" title="${E(amended && last?.trich_dan ? last.trich_dan : p.trich_dan || "")}">${E(amended && last?.trich_dan ? last.trich_dan : p.trich_dan || "")}</span></td><td>${trangThaiTs(p)}${n ? `<button class="link-btn" data-action="param-source" data-ma="${E(p.ma_ts)}">Nguồn ${icon("chevron", 13)}</button>` : ""}</td></tr>`;
            })
            .join("")}</tbody></table></div><div class="table-foot"><span>${params.length} / ${ts.length} tham số · ${changed} tham số thay đổi tại ngày chọn · ${coNguon} tham số có nguồn trích AI</span><span>Trích dẫn nguyên văn từ văn bản hợp đồng</span></div>`
        : ts.length
          ? `<div class="empty-state"><h3>Không có tham số phù hợp</h3><p>Chọn tất cả nhóm hoặc bỏ các ô lọc.</p>${button("contract-param-reset", "Xóa bộ lọc", "btn-primary")}</div>`
          : `<div class="empty-state">${icon("file")}<h3>Chưa có tham số</h3><p>Trích tham số hợp đồng rồi nạp CSDL để có bảng tham số.</p><button class="btn btn-primary" data-route="extraction">Trích tham số</button></div>`
    }`;
  if (ui.detailTab === "appendices")
    body = `${appendixTable(d.phu_luc, "all")}<div class="panel-body">${button("contract-open-appendices", "Quản lý và nạp phụ lục", "btn-primary")}</div>`;
  if (ui.detailTab === "boq")
    body = `<div class="toolbar"><label class="field"><span>BOQ hiệu lực tại ngày</span><input type="date" data-contract-field="detailDate" value="${E(ui.detailDate)}"></label>${button("contract-open-boq", "Mở bàn làm việc BOQ", "btn-ghost")}</div>${
      !ui.detailBoq
        ? loading()
        : ui.detailBoq.loi
          ? errBox(ui.detailBoq.loi)
          : ui.detailBoq.dong.length
            ? boqTable(ui.detailBoq, "")
            : `<div class="empty-state">${icon("table")}<h3>Chưa có BOQ</h3><p>Import BOQ để ánh xạ cột và kiểm tra tổng giá trị trước khi ghi.</p>${button("contract-import-boq", "Import BOQ", "btn-primary")}</div>`
    }`;
  if (ui.detailTab === "payments") {
    const luyKe = d.dot.length ? d.dot[d.dot.length - 1].gt_luy_ke : 0;
    body = d.dot.length
      ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Đợt</th><th>Ngày nghiệm thu</th><th class="numeric">Giá trị kỳ này</th><th class="numeric">Lũy kế</th><th class="numeric">Giữ lại</th><th class="numeric">Thu hồi tạm ứng</th><th class="numeric">Thanh toán kỳ này</th><th>Nguồn</th></tr></thead><tbody>${d.dot
          .map(
            (r) =>
              `<tr><td style="white-space:nowrap"><strong>Đợt ${E(r.dot)}</strong></td><td>${fmtDate(r.ngay_nghiem_thu)}</td><td class="numeric">${money(r.gt_ky)}</td><td class="numeric">${money(r.gt_luy_ke)}</td><td class="numeric">${money(r.giu_lai)}</td><td class="numeric">${money(r.thu_hoi_tu)}</td><td class="numeric"><strong>${money(r.gt_tt_ky)}</strong></td><td class="small">${E(r.file_nguon || "")}<span class="subline">Nạp ${E(r.ngay_nap || "")}</span></td></tr>`,
          )
          .join("")}</tbody><tfoot><tr><td colspan="3">Giá trị lũy kế đã nghiệm thu</td><td class="numeric"><strong>${money(luyKe)}</strong></td><td colspan="4"></td></tr></tfoot></table></div><div class="panel-body"><button class="btn btn-primary" data-action="contract-open-payments">Kiểm tra đợt mới</button></div>`
      : `<div class="empty-state"><h3>Chưa có đợt thanh toán</h3><p>Kiểm tra hồ sơ đợt để truy ngược các giá trị về nguồn, sau đó nạp đợt đã duyệt.</p><button class="btn btn-primary" data-action="contract-open-payments">Kiểm tra đợt</button></div>`;
  }
  if (ui.detailTab === "warnings")
    body = d.canh_bao.length
      ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Mã</th><th>Mức</th><th>Nội dung</th><th>Phụ lục / đợt</th><th>Thời điểm</th></tr></thead><tbody>${d.canh_bao
          .map((c) => {
            const pl = d.phu_luc.find((p) => p.id === c.pl_id);
            return `<tr><td class="check-code">${E(c.ma_kt || "")}</td><td>${badge(c.muc_do, MUC_KT[c.muc_do] || "neutral")}</td><td class="small">${E(c.noi_dung)}</td><td>${pl ? E(pl.so_pl) : c.dot ? `Đợt ${E(c.dot)}` : "—"}</td><td class="small">${E(c.thoi_diem || "")}</td></tr>`;
          })
          .join("")}</tbody></table></div>`
      : `<div class="empty-state">${icon("check")}<h3>Không có cảnh báo</h3><p>Chưa có cờ đỏ hoặc cảnh báo vàng từ phụ lục, BOQ hay đợt thanh toán.</p></div>`;
  const nhan = [h.loai_gia, h.ngay_ky ? `Ký ${fmtDate(h.ngay_ky)}` : "", coNguon ? `${coNguon - chuaXn} / ${coNguon} tham số trích AI đã xác nhận hoặc tự kiểm OK` : `${ts.length} tham số`]
    .filter(Boolean)
    .join(" · ");
  return `<div class="contracts-screen">${style()}${header(`${E(h.ma_hd)} · Chi tiết hợp đồng`, `${E(h.so_hd)}${h.du_an ? ` · ${E(h.du_an)}` : ""}`, `${back}${button("contract-detail-export", `${icon("download")} Xuất Excel CSDL`, "btn-primary")}`)}<div class="contract-banner"><div><strong>${E(h.ben_b || "Bên B chưa có")}</strong><span class="muted small">${E(nhan)}</span>${h.file_nguon ? `<span class="subline">Nguồn: ${E(h.file_nguon)}</span>` : ""}</div><div class="numeric"><span class="small muted">Giá trị hiệu lực tại ${fmtDate(d.ngay)}</span><span class="amount">${money(d.gt_hieu_luc)}</span><span class="subline">Gốc ${money(d.gt_goc)}${h.vat != null ? ` · VAT ${num(h.vat * 100)}%` : ""}</span></div></div><section class="panel"><div class="tabs">${tabs.map(([id, label, n]) => `<button class="tab ${ui.detailTab === id ? "active" : ""}" data-action="contract-tab" data-tab="${id}">${label}${n !== null ? ` <span class="muted">${n}</span>` : ""}</button>`).join("")}</div>${body}</section></div>`;
}

function paramSourceDrawer(ctx, ui, ma) {
  const p = (ui.detail?.tham_so || []).find((x) => x.ma_ts === ma);
  const n = p?.nguon_trich;
  if (!n) return;
  const okTu = String(n.kiem_tra || "").startsWith("OK");
  const ls = Array.isArray(n.lich_su) ? n.lich_su : [];
  const row = (k, v) => `<tr><th style="width:150px">${k}</th><td>${v}</td></tr>`;
  ctx.openDrawer({
    title: `${p.ma_ts} · ${p.ten || ""}`,
    body: `${style()}<div class="contracts-screen"><div class="contract-banner" style="display:block"><span class="small muted">Giá trị trong CSDL</span><strong style="font-size:18px;margin-top:6px">${giaTri(p.gia_tri, p.don_vi)}</strong>${n.gia_tri_ai !== n.gia_tri ? `<span class="subline">Máy trích ban đầu: ${E(n.gia_tri_ai ?? "—")}</span>` : ""}</div>
    <div style="margin:0 0 16px">${trangThaiTs(p)} ${badge(`Mức ${n.muc ?? "?"}`, "neutral")} ${n.nguon ? badge(n.nguon, /cloud/i.test(n.nguon) ? "info" : "neutral") : ""}</div>
    <h3>Trích dẫn nguyên văn</h3><p class="small" style="background:#f5f7fa;padding:12px;border-radius:4px;line-height:1.6"><strong>${E(p.dieu_khoan || "")}</strong><br>${E(p.trich_dan || "—")}</p>
    <h3>Tự kiểm</h3><p class="small ${okTu ? "" : "danger-text"}">${E(n.kiem_tra || "—")}</p>
    ${n.ghi_chu_soat ? `<h3>Ghi chú người soát</h3><p class="small">${E(n.ghi_chu_soat)}</p>` : ""}
    <h3>Dấu vết</h3><table class="data-table"><tbody>${row("Model / máy AI", `${E(n.model || "—")}<span class="subline">${E(n.may_ai || "")}</span>`)}${row("Lượt trích", E(n.luot || "—"))}${row("File hợp đồng", `${E(n.file_hop_dong || "—")}<span class="subline">SHA-1 ${E((n.sha1_file || "").slice(0, 12))}…</span>`)}${row("Lúc trích", E((n.luc_trich || "—").replace("T", " ")))}${row("Lúc nạp CSDL", E((n.luc_nap || "—").replace("T", " ")))}${n.da_xac_nhan ? row("Xác nhận", `${E(n.nguoi_xac_nhan || "")}<span class="subline">${E((n.luc_xac_nhan || "").replace("T", " "))}</span>`) : ""}</tbody></table>
    ${ls.length ? `<h3 style="margin-top:20px">Lịch sử</h3>${ls.map((x) => `<div class="history-item"><div class="history-date">${E(String(x.luc || "").replace("T", " "))}</div><div><div class="history-title">${E(x.thao_tac || "")}</div><p class="small">${x.cu !== undefined && x.cu !== "" ? `${E(x.cu)} → ` : ""}${E(x.moi ?? "")}</p>${x.ghi_chu ? `<span class="muted small">${E(x.ghi_chu)}</span>` : ""}<span class="muted small"> ${E(x.nguoi || "")}</span></div></div>`).join("")}` : ""}
    ${
      !n.da_xac_nhan
        ? `<div class="field" style="margin-top:20px"><label for="param-note">Ghi chú khi xác nhận (không bắt buộc)</label><textarea id="param-note" placeholder="Ví dụ: đã đối chiếu bản ký"></textarea></div><div class="toolbar" style="justify-content:flex-end;margin-top:12px"><button class="btn btn-primary" data-action="param-confirm" data-ma="${E(p.ma_ts)}">${icon("check", 16)} Xác nhận giá trị này</button></div><p class="small muted">Xác nhận không đổi giá trị. Muốn sửa giá trị: mở lại kết quả trích, sửa rồi nạp lại.</p>`
        : ""
    }</div>`,
  });
}

// ================================================================== Phụ lục
function appendixTable(rows, status = "all") {
  rows = (rows || []).filter((pl) => status === "all" || pl.trang_thai === status);
  return rows.length
    ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Phụ lục / nội dung</th><th>Ngày ký</th><th>Ngày hiệu lực</th><th>Trạng thái</th><th>Đổi BOQ</th><th class="numeric">Tăng / giảm sau VAT</th><th>Cờ</th><th></th></tr></thead><tbody>${rows
        .map((pl) => {
          const delta = Number(pl.gt_sau_vat) || 0;
          return `<tr><td><button class="table-link" data-action="appendix-detail" data-no="${E(pl.so_pl)}" data-hd="${E(pl.ma_hd)}">${E(pl.so_pl)}</button><span class="subline">${E(pl.noi_dung || pl.loai || "")}</span>${pl.ly_do_huy ? `<span class="subline">Lý do hủy: ${E(pl.ly_do_huy)}</span>` : ""}</td><td>${fmtDate(pl.ngay_ky)}</td><td>${fmtDate(pl.ngay_hieu_luc)}</td><td>${badge(pl.trang_thai, pl.trang_thai === "Đã ký" ? "success" : pl.trang_thai === "Đã hủy" ? "neutral" : "warning")}</td><td>${pl.doi_boq ? "Có" : "Không"}</td><td class="numeric ${delta < 0 ? "negative-delta" : "positive-delta"}">${delta ? `${delta > 0 ? "+" : ""}${money(delta)}` : "—"}</td><td>${pl.co_do ? badge(`${pl.co_do} đỏ`, "danger") : ""}${pl.co_vang ? badge(`${pl.co_vang} vàng`, "warning") : ""}${!pl.co_do && !pl.co_vang ? '<span class="muted small">—</span>' : ""}</td><td>${pl.trang_thai !== "Đã hủy" ? button("appendix-cancel", "Hủy", "btn-ghost", `data-no="${E(pl.so_pl)}" data-hd="${E(pl.ma_hd)}"`) : '<span class="muted small">Đã hủy</span>'}</td></tr>`;
        })
        .join("")}</tbody></table></div>`
    : `<div class="empty-state">${icon("file")}<h3>${status === "all" ? "Chưa có phụ lục" : "Không có phụ lục ở trạng thái này"}</h3><p>${status === "all" ? "Tạo phiếu phụ lục theo hợp đồng, điền nội dung thay đổi rồi nạp để kiểm tra P01–P18." : "Chọn tất cả trạng thái để xem các phụ lục của hợp đồng."}</p>${status === "all" ? button("appendix-template", "Tạo phiếu phụ lục", "btn-primary") : button("appendix-clear-filter", "Xóa bộ lọc", "btn-primary")}</div>`;
}

export function renderAppendices(ctx) {
  const ui = s(ctx);
  const head = header(
    "Phụ lục hợp đồng",
    "Kiểm tra thay đổi trước khi ghi. Mỗi giá trị đều có ngày hiệu lực và nguồn.",
    button("appendix-template", `${icon("download")} Tạo phiếu phụ lục`, "btn-primary", ui.appendixContract ? "" : "disabled"),
  );
  if (!ui.list) return `<div class="contracts-screen">${style()}${head}<section class="panel">${loading()}</section></div>`;
  if (ui.appendixContract && !ui.appendixDetail && !ui.dangTaiPL) {
    ui.dangTaiPL = true;                                    // vd vừa nạp phụ lục từ bản trích: tải lại danh sách
    loadAppendix(ctx).finally(() => {
      ui.dangTaiPL = false;
      ctx.render();
    });
  }
  const d = ui.appendixDetail;
  const ph = ui.phieu;
  let phieuHtml = "";
  if (!ph)
    phieuHtml = `<div class="panel-body">${upload("appendix-file", ".xlsx,.xlsm,.xls", false, "Phiếu phụ lục Excel (tạo bằng nút Tạo phiếu phụ lục) · Kiểm tra trước khi ghi vào CSDL")}<p class="inline-help">Phiếu đã điền: thông tin phụ lục, các tham số thay đổi (giá trị cũ → mới, trích dẫn) và các dòng BOQ thay / thêm / bỏ. Hợp đồng được xác định theo số HĐ ghi trên phiếu.</p></div>`;
  else if (ph.dang)
    phieuHtml = loading(`Đang kiểm tra ${ph.file.name}…`);
  else if (ph.loi) phieuHtml = `<div class="panel-body">${errBox(ph.loi)}</div>`;
  else {
    const kq = ph.ket_qua;
    phieuHtml = kq.phieu
      .map((p, i) => {
        const chk = p.kiem_tra;
        const count = (lv) => chk.filter((r) => r.muc === lv).length;
        const pl = p.phu_luc || {};
        const ghi = ph.ghi?.phieu?.[i];
        const delta = Number(pl.gt_sau_vat) || 0;
        return `<div class="toolbar"><div style="flex:1"><strong>${E(kq.tep)} · sheet ${E(p.sheet)}</strong><span class="subline">${E(pl.ma_hd || "")} · ${E(pl.so_pl || "")} · ${E(pl.trang_thai || "")} · Ký ${fmtDate(pl.ngay_ky)} · Hiệu lực ${fmtDate(pl.ngay_hieu_luc)}${delta ? ` · ${delta > 0 ? "+" : ""}${money(delta)} đồng sau VAT` : ""}</span>${pl.noi_dung ? `<span class="subline">${E(pl.noi_dung)}</span>` : ""}</div></div>
        ${ghi ? `<div class="notice notice-${ghi.ket_qua === "ĐÃ GHI" ? "success" : "danger"}">${icon(ghi.ket_qua === "ĐÃ GHI" ? "check" : "alert")} <strong>${E(ghi.ket_qua)}</strong> ${ghi.ket_qua === "ĐÃ GHI" ? `${E(pl.so_pl || "")} đã vào CSDL; giá trị hiệu lực và BOQ tính lại theo ngày hiệu lực.` : "Còn lỗi CHẶN — sửa phiếu rồi nạp lại."}</div>` : ""}
        <div class="check-summary"><div class="counts">${badge(`${count("CHẶN")} CHẶN`, count("CHẶN") ? "danger" : "neutral")}${badge(`${count("ĐỎ")} ĐỎ`, count("ĐỎ") ? "danger" : "neutral")}${badge(`${count("VÀNG")} VÀNG`, count("VÀNG") ? "warning" : "neutral")}${badge(`${count("ĐẠT")} ĐẠT`, "success")}</div><span class="small muted">${p.co_chan ? "Sửa CHẶN trên phiếu để mở nút ghi" : "Không có CHẶN · Có thể ghi sau khi xem cảnh báo"}</span></div>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>Mã</th><th>Mức</th><th>Giải thích / cách xử lý</th></tr></thead><tbody>${chk.map((r) => `<tr><td class="check-code">${E(r.ma)}</td><td>${badge(r.muc, MUC_KT[r.muc] || "neutral")}</td><td class="small">${E(r.noi_dung)}</td></tr>`).join("")}</tbody></table></div>`;
      })
      .join('<hr class="divider">');
    const soChan = kq.phieu.filter((p) => p.co_chan).length;
    const chan = soChan === kq.phieu.length;
    const daGhi = !!ph.ghi;
    phieuHtml += `<div class="panel-body"><div class="notice notice-${soChan ? "danger" : "warning"}">${icon("alert-triangle")} ${chan ? "Có lỗi CHẶN. Chỉnh nội dung được chỉ ra trên phiếu rồi nạp lại." : soChan ? `${soChan} / ${kq.phieu.length} phụ lục có lỗi CHẶN — khi ghi, các phụ lục này bị bỏ qua; sửa phiếu rồi nạp lại riêng. Cờ ĐỎ / VÀNG không khóa nút ghi.` : "Cờ ĐỎ và VÀNG cần người ký xem xét. Các mức này không khóa nút ghi; cờ được lưu kèm phụ lục."}</div><div style="display:flex;justify-content:flex-end;gap:12px;margin-top:16px">${button("appendix-check-export", `${icon("download")} Tải kết quả kiểm tra`, "btn-ghost")}${button("appendix-record", daGhi ? "Đã ghi vào CSDL" : "Ghi vào CSDL", "btn-primary", chan || daGhi || ui.busy ? 'disabled aria-disabled="true"' : "")}</div></div>`;
  }
  return `<div class="contracts-screen">${style()}${head}
    <section class="panel"><div class="toolbar">${chonHopDong(ctx.state, ui.list, ui.appendixContract, 'data-contract-field="appendixContract"')}<label class="field"><span>Trạng thái phụ lục</span><select data-contract-field="appendixStatus"><option value="all">Tất cả trạng thái</option>${["Đã ký", "Dự thảo", "Đã hủy"].map((st) => `<option ${ui.appendixStatus === st ? "selected" : ""}>${st}</option>`).join("")}</select></label></div><div class="panel-head"><strong>Phụ lục của ${E((ui.list || []).find((h) => h.ma_hd === ui.appendixContract)?.so_hd || "—")}</strong>${d && !d.loi ? badge(`${d.phu_luc.length} phụ lục · hiệu lực hôm nay ${money(d.gt_hieu_luc)}`, "neutral") : ""}</div>${!ui.appendixContract ? (ui.list.length ? `<div class="empty-state">${icon("filter")}<h3>Không có hợp đồng phù hợp bộ lọc</h3><p>Đổi Bên A, Dự án hoặc từ khoá để chọn hợp đồng.</p></div>` : `<div class="empty-state">${icon("database")}<h3>CSDL chưa có hợp đồng</h3><p>Nạp hợp đồng vào CSDL trước khi nạp phụ lục.</p><button class="btn btn-primary" data-route="extraction">Trích tham số</button></div>`) : !d ? loading() : d.loi ? errBox(d.loi) : appendixTable(d.phu_luc, ui.appendixStatus)}</section>
    ${renderPLAI(ctx, ui.list)}
    <section class="panel"><div class="panel-head"><div><strong>Nạp phiếu phụ lục Excel</strong><span class="subline">Cách nhập tay (dự phòng) · 18 kiểm tra P01–P18 trước khi ghi · CHẶN khóa nút ghi.</span></div>${ph && !ph.dang ? button("appendix-reset", "Nạp phiếu khác", "btn-ghost") : ""}</div>${phieuHtml}</section>
  </div>`;
}

// ================================================================== BOQ
function boqTable(b, query = "") {
  const ql = query.trim().toLocaleLowerCase("vi");
  const rows = b.dong.filter((r) => !ql || `${r.ma_hm} ${r.ten} ${r.nhom || ""}`.toLocaleLowerCase("vi").includes(ql));
  if (!rows.length)
    return `<div class="empty-state">${icon("search")}<h3>Không tìm thấy hạng mục</h3><p>Thử tên công việc khác hoặc xóa nội dung tìm kiếm.</p>${button("boq-clear-search", "Xóa tìm kiếm", "btn-primary")}</div>`;
  let nhomTruoc = null;
  const body = rows
    .map((r) => {
      const tt = Math.round((r.kl || 0) * (r.don_gia || 0));
      const changed = r.nguon !== "HĐ gốc";
      const g = r.nhom && r.nhom !== nhomTruoc ? `<tr><td colspan="8" class="small" style="background:#f5f7fa;font-weight:650">${E(r.nhom)}</td></tr>` : "";
      nhomTruoc = r.nhom;
      return `${g}<tr class="${changed ? "amended-row" : ""}"><td class="contract-code">${E(r.ma_hm)}<span class="subline">${E(r.stt || "")}</span></td><td>${E(r.ten)}</td><td>${E(r.dvt || "")}</td><td class="numeric">${num(r.kl)}</td><td class="numeric">${dg(r.don_gia)}</td><td class="numeric"><strong>${money(tt)}</strong></td><td>${badge(r.nguon, changed ? "info" : "neutral")}</td><td>${button("boq-history", icon("history"), "btn-ghost", `data-code="${E(r.ma_hm)}" aria-label="Lịch sử ${E(r.ma_hm)}" title="Lịch sử thay đổi"`)}</td></tr>`;
    })
    .join("");
  const lech = b.tong_sau_vat - b.gt_hieu_luc;
  return `<div class="table-wrap"><table class="data-table"><thead><tr><th>Mã HM</th><th>Tên công việc</th><th>ĐVT</th><th class="numeric">Khối lượng</th><th class="numeric">Đơn giá</th><th class="numeric">Thành tiền</th><th>Nguồn</th><th>Lịch sử</th></tr></thead><tbody>${body}</tbody><tfoot><tr><td colspan="5">Tổng trước VAT ${query ? "(toàn bộ BOQ)" : ""}</td><td class="numeric"><strong>${money(b.tong_truoc_vat)}</strong></td><td colspan="2"></td></tr><tr><td colspan="5">VAT ${num((b.vat || 0) * 100)}%</td><td class="numeric">${money(b.tong_truoc_vat * (b.vat || 0))}</td><td colspan="2"></td></tr><tr><td colspan="5"><strong>Tổng sau VAT</strong> <span class="muted small">· giá trị HĐ hiệu lực ${money(b.gt_hieu_luc)}</span></td><td class="numeric"><strong>${money(b.tong_sau_vat)}</strong></td><td colspan="2">${b.khop ? badge("ĐẠT", "success") : badge(`LỆCH ${money(lech)}`, "danger")}</td></tr></tfoot></table></div>${b.da_bo?.length ? `<div class="notice notice-info" style="margin:16px">${icon("info")} ${b.da_bo.length} hạng mục đã bị bỏ bởi phụ lục: ${E(b.da_bo.map((r) => `${r.ma_hm} (${r.bo_boi})`).join(", "))}</div>` : ""}<div class="table-foot"><span>${rows.length} / ${b.dong.length} hạng mục · Hiệu lực tại ${fmtDate(b.ngay)}${b.pl_ap_dung.length ? ` · áp dụng ${E(b.pl_ap_dung.join(", "))}` : ""}</span><span>Đơn giá chưa VAT · thành tiền = KL × ĐG làm tròn</span></div>`;
}

export function renderBOQ(ctx) {
  const ui = s(ctx);
  const head = header(
    "BOQ hợp đồng",
    "Đối chiếu khối lượng và đơn giá theo đúng ngày nghiệm thu.",
    ui.boqView === "effective" ? button("boq-export", `${icon("download")} Xuất BOQ hiệu lực`, "btn-ghost", ui.boqContract ? "" : "disabled") : "",
  );
  if (!ui.list) return `<div class="contracts-screen">${style()}${head}<section class="panel">${loading()}</section></div>`;
  const b = ui.boq;
  const hd = (ui.list || []).find((h) => h.ma_hd === ui.boqContract);
  const body =
    ui.boqView === "import"
      ? renderBOQImport(ctx, ui)
      : `<section class="panel"><div class="toolbar">${chonHopDong(ctx.state, ui.list, ui.boqContract, 'data-contract-field="boqContract"')}<label class="field"><span>Ngày áp dụng BOQ</span><input type="date" data-contract-field="boqDate" value="${E(ui.boqDate)}"></label>${button("boq-date-today", "Dùng ngày hôm nay", "btn-ghost")}</div><div class="panel-head"><div><strong>BOQ hiệu lực · ${E((ui.list || []).find((h) => h.ma_hd === ui.boqContract)?.so_hd || "—")}</strong><span class="subline">BOQ gốc và các thay đổi từ phụ lục đã ký có hiệu lực đến ngày chọn</span></div>${badge(fmtDate(ui.boqDate), "info")}</div>${
          !ui.boqContract
            ? (ui.list.length ? `<div class="empty-state">${icon("filter")}<h3>Không có hợp đồng phù hợp bộ lọc</h3><p>Đổi Bên A, Dự án hoặc từ khoá để chọn hợp đồng.</p></div>` : `<div class="empty-state">${icon("database")}<h3>CSDL chưa có hợp đồng</h3><p>Nạp hợp đồng vào CSDL trước khi import BOQ.</p></div>`)
            : ui.boqErr
              ? errBox(ui.boqErr)
              : !b
                ? loading()
                : b.dong.length
                  ? `<div class="toolbar"><label class="field" style="flex:1;max-width:440px"><span>Tìm hạng mục</span><input type="search" id="boq-search" data-contract-field="boqQuery" value="${E(ui.boqQuery)}" placeholder="Mã HM, tên công việc hoặc nhóm"></label><div class="small muted" style="margin-left:auto">Giá trị HĐ sau VAT<br><strong style="color:#1c314c">${money(b.gt_hieu_luc)}</strong></div></div>${
                      (ui.appendixDetail?.hop_dong?.ma_hd === ui.boqContract ? ui.appendixDetail.phu_luc : [])
                        .filter((p) => p.trang_thai === "Đã ký" && p.doi_boq && p.ngay_hieu_luc > ui.boqDate)
                        .map((p) => `<div class="notice notice-info">${icon("calendar")} Ngày ${fmtDate(ui.boqDate)} chưa áp dụng ${E(p.so_pl)} (hiệu lực ${fmtDate(p.ngay_hieu_luc)}). BOQ hôm nay có thể khác BOQ của đợt đang review.</div>`)
                        .join("")
                    }${boqTable(b, ui.boqQuery)}`
                  : `<div class="empty-state">${icon("table")}<h3>${E(ui.boqContract)} chưa có BOQ</h3><p>Nạp bảng khối lượng, ánh xạ cột và kiểm tra tổng giá trị trước khi ghi.${hd?.so_phu_luc ? " Lưu ý: hợp đồng đã có phụ lục nên không nhập BOQ gốc được." : ""}</p>${button("boq-import-open", "Import BOQ", "btn-primary")}</div>`
        }</section>`;
  return `<div class="contracts-screen">${style()}${head}
    <div class="tabs boq-tabs"><button class="tab ${ui.boqView === "effective" ? "active" : ""}" data-action="boq-view" data-view="effective">BOQ hiệu lực</button><button class="tab ${ui.boqView === "import" ? "active" : ""}" data-action="boq-view" data-view="import">Import BOQ</button></div>${body}</div>`;
}

function mapping(ui) {
  const cot = ui.imp?.cot || {};
  const dung = Object.values(cot).filter(Boolean);
  const thieu = TRUONG.filter(([k, , req]) => req && !cot[k]).map(([, t]) => t);
  return { cot, thieu, trung: dung.length !== new Set(dung).size };
}
function renderBOQImport(ctx, ui) {
  const im = ui.imp;
  if (!im?.tep && !im?.dang && ui.loat) return renderBOQLoat(ctx, ui);
  const step = !im || !im.tep ? 1 : im.kt ? 3 : 2;
  let inner = "";
  if (!im || !im.tep) {
    inner = im?.dang
      ? loading(`Đang đọc ${im.file?.name || "file"}…${/\.pdf$/i.test(im.file?.name || "") ? " PDF scan được OCR bằng ABBYY trên máy này (khoảng 1 phút / vài trang)." : ""}`)
      : `${im?.loi ? errBox(im.loi) : ""}<div class="grid-2 boq-up"><div><strong class="up-title">Một file</strong>${upload("boq-file", ".xlsx,.xlsm,.xls,.pdf,.docx", false, "Excel (.xlsx, .xls), Word hoặc PDF (PDF scan tự OCR bằng ABBYY) · chọn sheet và ánh xạ cột trước khi ghi")}</div><div><strong class="up-title">Cả loạt</strong>${upload("boq-files", ".xlsx,.xlsm,.xls,.pdf,.docx", true, "Nhiều file BOQ (Excel / Word / PDF) · tự nhận hợp đồng theo số HĐ ghi trong file")}</div></div><p class="inline-help">Phần mềm tự đoán sheet, dòng tiêu đề và các cột; Anh kiểm tra lại trước khi ghi. Dòng không có ĐVT được hiểu là tiêu đề nhóm; dừng ở dòng Cộng / Tổng. Nạp cả loạt: mỗi file được nhận hợp đồng theo số HĐ ghi ở đầu sheet (vd "Kèm theo hợp đồng số …") hoặc tên file, rồi hiện bảng số liệu để Anh xác nhận.</p>`;
  } else {
    const x = im.xem || {};
    const { cot, thieu, trung } = mapping(ui);
    const so = Math.max(1, Math.min(26, x.so_cot || 8));
    const tieuDe = (x.dong || [])[(im.hang || 1) - 1] || [];
    const opts = (k) =>
      `<option value="">Chưa chọn cột</option>${COLS.slice(0, so)
        .map((c, j) => `<option value="${c}" ${cot[k] === c ? "selected" : ""}>Cột ${c}${tieuDe[j] ? ` · ${E(String(tieuDe[j]).slice(0, 28))}` : ""}</option>`)
        .join("")}`;
    const hang = Number(im.hang) || 0;
    const preview = (x.dong || [])
      .map((r, i) => {
        const n = i + 1;
        return `<tr class="${n === hang ? "header-row" : ""}"><td class="rn">${n}</td>${COLS.slice(0, so)
          .map((_, j) => `<td title="${E(r[j] || "")}">${E(r[j] || "")}</td>`)
          .join("")}</tr>`;
      })
      .join("");
    const sheetInfo = (im.sheets || []).find((sh) => sh.ten === im.sheet);
    const dang = (ui.list || []).find((h) => h.ma_hd === ui.boqContract);
    const lechHd = im.doan && im.doan.ma !== ui.boqContract
      ? `<div class="notice notice-warning" style="margin-bottom:12px">${icon("alert")} File ghi <strong>hợp đồng ${E(im.doan.so)}</strong> (theo ${E(im.doan.nguon)}) nhưng đang chọn <strong>${E(dang?.so_hd || "—")}</strong>. Kiểm tra lại hợp đồng nhận BOQ.</div>`
      : im.doan ? `<div class="small muted" style="margin:-8px 0 12px">${icon("check", 14)} Số hợp đồng trong file khớp hợp đồng đang chọn.</div>` : "";
    inner = lechHd + `<div class="notice notice-info">${icon("file")} <strong>${E(im.ten)}</strong> · ${(im.sheets || []).length} ${im.nguon ? "bảng" : "sheet"}${sheetInfo ? ` · đang chọn ${sheetInfo.so_dong} dòng` : ""}</div>${nguonBoq(im.nguon)}${im.tuXls ? `<div class="small muted" style="margin-top:8px">${icon("file", 14)} File Excel 97-2003 (.xls) đã chuyển sang .xlsx bằng ${E(im.tuXls)}.</div>` : ""}
    <div class="grid-2" style="margin:20px 0"><label class="field"><span>Sheet dữ liệu</span><select data-boq-imp="sheet">${(im.sheets || []).map((sh) => `<option value="${E(sh.ten)}" ${sh.ten === im.sheet ? "selected" : ""}>${E(sh.ten)} (${sh.so_dong} dòng${sh.an ? ", ẩn" : ""})</option>`).join("")}</select></label><label class="field"><span>Dòng tiêu đề của bảng</span><input type="number" min="1" max="40" data-boq-imp="hang" value="${E(im.hang || "")}"><small>${x.hang_tieu_de ? `Phần mềm đoán dòng ${x.hang_tieu_de}` : "Không đoán được — xem bảng dưới rồi nhập số dòng"}</small></label></div>
    <div class="sheet-preview"><table><thead><tr><th></th>${COLS.slice(0, so).map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${preview}</tbody></table></div>
    <div class="mapping-grid">${TRUONG.map(([k, t, req]) => `<label class="field"><span>${t} ${req ? '<span style="color:#ad3943">*</span>' : `<span class="muted small">${k === "ma_rieng" ? "(nếu có — để ghép hồ sơ thanh toán theo mã)" : "(nên có)"}</span>`}</span><select data-boq-map="${k}">${opts(k)}</select></label>`).join("")}</div>
    ${thieu.length || trung ? `<div class="notice notice-danger" style="margin-top:16px">${icon("alert-triangle")} ${thieu.length ? `Chọn cột cho: ${E(thieu.join(", "))}.` : "Một cột đang được dùng cho nhiều trường. Mỗi trường cần một cột riêng."}</div>` : ""}
    ${!cot.thanh_tien && !thieu.length ? `<p class="inline-help">Không chọn cột Thành tiền thì không bắt được lỗi KL × ĐG ≠ thành tiền trên file.</p>` : ""}
    <div style="display:flex;justify-content:flex-end;margin-top:20px">${button("boq-preview", `${icon("check")} Xem trước và kiểm tra`, "btn-primary", thieu.length || trung || !hang || !ui.boqContract || ui.busy ? "disabled" : "")}</div>
    ${im.kt ? renderBOQCheck(ui) : ""}`;
  }
  return `<section class="panel"><div class="panel-head"><div><strong>Import BOQ gốc theo hợp đồng</strong><span class="subline">Chọn sheet, ánh xạ cột và kiểm tra tổng giá trị so với giá trị HĐ gốc.</span></div>${im?.tep ? button("boq-import-reset", im.tuLoat ? `${icon("arrow-left")} Về bảng cả loạt` : im.ghi ? "Import BOQ hợp đồng khác" : "Chọn file khác", "btn-ghost") : ""}</div><div class="panel-body">
    <div class="import-step"><span class="${step === 1 ? "active" : ""}">1. Chọn file</span><span class="${step === 2 ? "active" : ""}">2. Ánh xạ cột</span><span class="${step === 3 ? "active" : ""}">3. Xem trước và ghi</span></div>
    <div class="toolbar" style="align-items:flex-end;margin-bottom:8px">${chonHopDong(ctx.state, ui.list, ui.boqContract, 'data-contract-field="boqContract"', "Hợp đồng nhận BOQ")}</div><p class="small muted" style="margin:0 0 20px">BOQ gốc có hiệu lực từ ngày ký hợp đồng. Thay đổi sau đó phải qua phiếu phụ lục.</p>
    ${inner}
  </div></section>`;
}
function renderBOQCheck(ui) {
  const k = ui.imp.kt;
  const ghi = ui.imp.ghi;
  const lech = k.ket_luan !== "ĐẠT";
  const chan = k.chan || [];
  const cols = TRUONG.map(([, t]) => t);
  const dis = chan.length || ghi || (lech && !ui.imp.chapNhan) || ui.busy;
  return `<hr style="border:0;border-top:1px solid #dbe2eb;margin:24px 0"><div class="panel-head" style="padding:0 0 16px"><strong>Xem trước dữ liệu · ${k.so_dong} hạng mục</strong><span class="small muted">${E(k.ma_hd)} · ${E(k.so_hd)}</span></div>
    <div class="table-wrap"><table class="data-table"><thead><tr><th>Dòng</th><th>Nhóm</th>${cols.map((f) => `<th>${f}</th>`).join("")}</tr></thead><tbody>${k.xem_truoc
      .slice(0, 8)
      .map(
        (r) =>
          `<tr><td class="muted">${r.dong}</td><td class="small">${E(r.nhom || "")}</td><td>${E(r.stt || "")}</td><td>${E(r.ma_rieng || "")}</td><td>${E(r.ten)}</td><td>${E(r.dvt)}</td><td class="numeric">${num(r.kl)}</td><td class="numeric">${dg(r.don_gia)}</td><td class="numeric">${r.thanh_tien == null ? "—" : money(r.thanh_tien)}</td></tr>`,
      )
      .join("")}</tbody></table></div><p class="inline-help">Hiện ${Math.min(8, k.so_dong)} / ${k.so_dong} dòng để duyệt ánh xạ. Tổng giá trị tính trên toàn bộ ${k.so_dong} dòng.</p>
    ${k.loi.length ? `<div class="notice notice-danger" style="margin-top:16px">${icon("alert-triangle")} <strong>${k.loi.length} dòng lỗi:</strong> ${E(k.loi.slice(0, 5).map((l) => `dòng ${l.dong}: ${l.noi_dung}`).join(" · "))}${k.loi.length > 5 ? " …" : ""}</div>` : ""}
    <div class="equation"><div><span class="small muted">Σ round(KL × ĐG) trước VAT</span><strong>${money(k.tong_truoc_vat)}</strong></div><span class="operator">×</span><div><span class="small muted">Hệ số VAT</span><strong>${num(1 + (k.vat || 0))} (VAT ${num((k.vat || 0) * 100)}%)</strong></div><span class="operator">=</span><div><span class="small muted">Tổng sau VAT</span><strong>${money(k.tong_sau_vat)}</strong></div></div>
    <div class="notice notice-${lech ? "danger" : "success"}">${icon(lech ? "alert-triangle" : "check")} ${lech ? `<strong>LỆCH ${money(Math.abs(k.lech))} đồng</strong> so với giá trị HĐ gốc ${money(k.gt_hd)} đồng${k.gom_vat ? ` (${E(k.gom_vat)})` : ""}. Kiểm tra tổng thành tiền, VAT và ánh xạ cột trước khi ghi.` : `<strong>ĐẠT</strong> · Tổng BOQ sau VAT bằng giá trị hợp đồng gốc: ${money(k.gt_hd)} đồng.`}</div>
    ${chan.map((c) => `<div class="notice notice-danger" style="margin-top:12px">${icon("x")} <strong>Không ghi được:</strong> ${E(c)}</div>`).join("")}
    ${k.boq_hien_co && !chan.length ? `<div class="notice notice-warning" style="margin-top:12px">${icon("alert")} Hợp đồng đã có ${k.boq_hien_co} dòng BOQ gốc — ghi sẽ <strong>thay toàn bộ</strong> BOQ gốc và cần nhập lý do (ghi nhật ký).</div>` : ""}
    ${lech && !chan.length && !ghi ? `<label class="check-field" style="margin-top:12px"><input type="checkbox" data-boq-imp="chapNhan" ${ui.imp.chapNhan ? "checked" : ""}> Vẫn ghi dù lệch (đã kiểm tra, ghi lý do vào nhật ký)</label>` : ""}
    ${ghi ? `<div class="notice notice-success" style="margin-top:12px">${icon("check")} Đã ghi ${ghi.so_dong} hạng mục vào BOQ gốc của ${E(ghi.ma_hd)} (${E(ghi.ket_luan)}).${ghi.canh_bao?.length ? ` Cảnh báo: ${E(ghi.canh_bao.map((c) => (Array.isArray(c) ? c.join(" ") : c.noi_dung || String(c))).join("; "))}` : ""}</div>` : ""}
    <div style="display:flex;justify-content:flex-end;gap:12px;margin-top:20px">${button("boq-export-preview", `${icon("download")} Tải bản xem trước`, "btn-ghost")}${ghi ? button("boq-import-reset", ui.imp.tuLoat ? `${icon("arrow-left")} Về bảng cả loạt` : `${icon("upload")} Import BOQ hợp đồng khác`, "btn-primary") + button("boq-view-effective", "Xem BOQ hiệu lực", "") : button("boq-confirm", "Xác nhận ghi BOQ", "btn-primary", dis ? 'disabled aria-disabled="true"' : "")}</div>`;
}

function nguonBoq(n) {
  if (!n) return "";
  return n.loai === "pdf_ocr"
    ? `<div class="notice notice-warning" style="margin-top:8px">${icon("scan")} Bảng lấy từ <strong>PDF scan qua OCR ABBYY</strong>${n.trang ? ` (${E(n.trang)} trang${n.tu_luu_dem ? ", dùng lại kết quả đã OCR" : ""})` : ""} · ${E(n.so_bang)} bảng (bảng ngắt trang đã gộp). Số do máy nhận dạng — đối chiếu tổng với bản scan trước khi ghi.</div>`
    : `<div class="small muted" style="margin-top:8px">${icon("file", 14)} Bảng lấy từ file Word · ${E(n.so_bang)} bảng (bảng ngắt trang đã gộp).</div>`;
}
// ------------------------------------------------------------------ nạp BOQ cả loạt
function loatLech(k) {
  return k && k.ket_luan !== "ĐẠT";
}
function loatTrung(L) {
  const dem = {};
  for (const r of L.dong) if (r.ma) dem[r.ma] = (dem[r.ma] || 0) + 1;
  return dem;
}
function loatChonDuoc(r) {
  return r.kt && !r.dang && !r.ghi && !(r.kt.chan || []).length;
}
function renderBOQLoat(ctx, ui) {
  const L = ui.loat;
  const ds = ui.list || [];
  const dem = loatTrung(L);
  const chon = L.dong.filter((r) => r.chon && loatChonDuoc(r));
  const xong = L.dong.filter((r) => !r.dang).length;
  const n = { dat: 0, lech: 0, chua: 0, chan: 0, ghi: 0 };
  for (const r of L.dong) {
    if (r.ghi) n.ghi++;
    else if (!r.ma) n.chua++;
    else if (r.kt && (r.kt.chan || []).length) n.chan++;
    else if (r.kt && loatLech(r.kt)) n.lech++;
    else if (r.kt) n.dat++;
  }
  const opt = (r) =>
    `<option value="">— Chọn hợp đồng —</option>${ds
      .map((h) => `<option value="${E(h.ma_hd)}" ${h.ma_hd === r.ma ? "selected" : ""}>${E(h.so_hd)}${h.ben_b ? " · " + E(gon(h.ben_b).slice(0, 30)) : ""}</option>`)
      .join("")}`;
  const ketLuan = (r) => {
    if (r.dang) return `<span class="muted small">${E(r.dang)}</span>`;
    if (r.ghi) return badge(`Đã ghi ${r.ghi.so_dong} HM`, "success");
    if (r.loi) return `${badge("Lỗi", "danger")}<span class="subline danger-text">${E(r.loi)}</span>`;
    if (!r.ma) return `${badge("Chưa nhận HĐ", "warning")}<span class="subline">Chọn hợp đồng ở cột Hợp đồng</span>`;
    const k = r.kt;
    if (!k) return "—";
    const ghiChu = [
      ...(k.chan || []).map((c) => `<span class="subline danger-text">${E(c)}</span>`),
      k.boq_hien_co && !(k.chan || []).length ? `<span class="subline">Đã có ${k.boq_hien_co} dòng BOQ — ghi sẽ thay toàn bộ</span>` : "",
      (k.loi || []).length ? `<span class="subline danger-text">${k.loi.length} dòng lỗi (vd dòng ${E(k.loi[0].dong)}: ${E(k.loi[0].noi_dung)})</span>` : "",
      dem[r.ma] > 1 ? `<span class="subline danger-text">Trùng hợp đồng với file khác trong loạt</span>` : "",
      r.ghiLoi ? `<span class="subline danger-text">Ghi lỗi: ${E(r.ghiLoi)}</span>` : "",
    ].join("");
    return `${(k.chan || []).length ? badge("Không ghi được", "danger") : loatLech(k) ? badge("LỆCH", "danger") : badge("ĐẠT", "success")}${ghiChu}`;
  };
  const rows = L.dong
    .map((r) => {
      const k = r.kt;
      const ok = loatChonDuoc(r);
      return `<tr class="${r.ghi ? "amended-row" : ""}"><td><input type="checkbox" data-boq-loat-chon="${r.id}" ${r.chon && ok ? "checked" : ""} ${ok && !L.dangGhi ? "" : "disabled"} aria-label="Ghi BOQ ${E(r.ten)}"></td>
        <td><strong class="small" style="overflow-wrap:anywhere">${E(r.ten)}</strong><span class="subline">${r.sheet ? `${r.nguon ? "" : "Sheet "}${E(r.sheet)} · tiêu đề dòng ${E(r.hang || "?")}` : ""}${r.nguon?.loai === "pdf_ocr" ? ` · OCR ABBYY${r.nguon.trang ? ` ${E(r.nguon.trang)} trang` : ""}` : r.nguon ? " · bảng Word" : ""}</span>${r.tep && !r.ghi ? `<button class="table-link small" data-action="boq-loat-mo" data-id="${r.id}" ${L.dangGhi ? "disabled" : ""} title="Đổi sheet / dòng tiêu đề / ánh xạ cột, xem các dòng" style="min-height:28px">Chi tiết ›</button>` : ""}</td>
        <td><select data-boq-loat-hd="${r.id}" ${r.dang || r.ghi || L.dangGhi ? "disabled" : ""} style="width:100%;max-width:220px">${opt(r)}</select><span class="subline">${r.doan ? `Nhận theo ${E(r.doan.nguon)}${r.doan.ma !== r.ma ? ` (file ghi ${E(r.doan.so)})` : ""}` : r.tep ? "Không thấy số HĐ trong file" : ""}</span></td>
        <td class="numeric">${k ? num(k.so_dong) : "—"}</td>
        <td class="numeric">${k ? money(k.tong_truoc_vat) : "—"}</td>
        <td class="numeric"><strong>${k ? money(k.tong_sau_vat) : "—"}</strong>${k ? `<span class="subline">× ${num(1 + (k.vat || 0))} (VAT ${num((k.vat || 0) * 100)}%)</span>` : ""}</td>
        <td class="numeric">${k ? money(k.gt_hd) : "—"}</td>
        <td class="numeric ${k && loatLech(k) ? "negative-delta" : ""}">${k ? (k.lech ? money(k.lech) : "0") : "—"}</td>
        <td>${ketLuan(r)}</td></tr>`;
    })
    .join("");
  const tongChon = chon.reduce((a, r) => a + (r.kt?.tong_sau_vat || 0), 0);
  return `<section class="panel"><div class="panel-head"><div><strong>Nạp BOQ cả loạt · ${L.dong.length} file</strong><span class="subline">Phần mềm tự nhận hợp đồng và tính tổng; Anh xem số liệu, sửa hợp đồng nếu cần, tích chọn rồi ghi. Chỉ dòng ĐẠT được chọn sẵn.</span></div><div style="display:flex;gap:8px">${button("boq-loat-csv", `${icon("download")} Tải bảng đối chiếu`, "btn-ghost", L.dang ? "disabled" : "")}${button("boq-loat-reset", "Nạp loạt khác", "btn-ghost", L.dangGhi ? "disabled" : "")}</div></div>
    <div class="check-summary"><div class="counts">${badge(`${n.dat} ĐẠT`, "success")}${n.lech ? badge(`${n.lech} LỆCH`, "danger") : ""}${n.chan ? badge(`${n.chan} không ghi được`, "danger") : ""}${n.chua ? badge(`${n.chua} chưa nhận HĐ`, "warning") : ""}${n.ghi ? badge(`${n.ghi} đã ghi`, "info") : ""}${L.dang ? `<span class="small muted">Đang đọc ${xong}/${L.dong.length} file…</span>` : ""}</div><div class="small muted">Đã chọn <strong>${chon.length}</strong> file · Σ sau VAT <strong>${money(tongChon)}</strong></div></div>
    <div class="table-wrap"><table class="data-table boq-loat"><thead><tr><th style="width:36px"></th><th>File</th><th>Hợp đồng</th><th class="numeric">Số HM</th><th class="numeric">Σ trước VAT</th><th class="numeric">Tổng sau VAT</th><th class="numeric">GT HĐ gốc</th><th class="numeric">Lệch</th><th>Kết luận</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="panel-body" style="display:flex;justify-content:space-between;align-items:center;gap:16px"><p class="inline-help" style="margin:0">Lệch = tổng sau VAT − GT HĐ gốc. Dòng LỆCH hoặc đã có BOQ chỉ ghi khi Anh tự tích chọn và nhập lý do (ghi nhật ký). Bấm Chi tiết để đổi sheet, dòng tiêu đề, ánh xạ cột.</p>${button("boq-loat-ghi", `${icon("check")} Ghi ${chon.length} BOQ đã chọn`, "btn-primary", !chon.length || L.dang || L.dangGhi || ui.busy ? 'disabled aria-disabled="true"' : "")}</div></section>`;
}
async function loatKiemTra(ctx, r) {
  const ui = s(ctx);
  r.kt = null;
  r.loi = "";
  r.chon = false;
  if (!r.ma || !r.tep) return;
  r.dang = "Đang kiểm tra…";
  ctx.render();
  try {
    const cot = {};
    for (const [k] of TRUONG) if (r.cot?.[k]) cot[k] = r.cot[k];
    r.kt = await post("/api/boq/kiem_tra", { tep: r.tep, sheet: r.sheet, hang_tieu_de: r.hang, cot, ma_hd: r.ma });
  } catch (e) {
    r.loi = e.message;
  }
  r.dang = "";
  const k = r.kt;
  // chọn sẵn chỉ khi ĐẠT, không chặn, chưa có BOQ, không dòng lỗi, không trùng hợp đồng với file khác
  r.chon = !!(k && k.ket_luan === "ĐẠT" && !(k.chan || []).length && !k.boq_hien_co && !(k.loi || []).length && loatTrung(ui.loat)[r.ma] === 1);
  ctx.render();
}
async function taiLoat(ctx, files) {
  const ui = s(ctx);
  if (!ui.list) await loadList(ctx);
  ui.imp = null;
  ui.loat = { dong: Array.from(files).map((f, i) => ({ id: String(i + 1), ten: f.name, file: f, dang: "Đang chờ…" })), dang: true };
  ctx.render();
  const L = ui.loat;
  for (const r of L.dong) {
    if (ui.loat !== L) return; // Anh đã nạp loạt khác
    r.dang = /\.pdf$/i.test(r.ten) ? "Đang OCR bằng ABBYY…" : "Đang đọc file…";
    ctx.render();
    try {
      const d = await uploadFile(`/api/boq/tai_len?ten=${encodeURIComponent(r.file.name)}`, r.file);
      const g = d.goi_y || {};
      Object.assign(r, { tep: d.tep, ten: d.ten || r.ten, sheets: d.sheets, sheet: g.sheet, xem: g, hang: g.hang_tieu_de || "", cot: { ...(g.cot || {}) }, nguon: d.nguon });
      r.doan = doanHopDong(r, ui.list);
      r.ma = r.doan?.ma || "";
      if (!r.hang) {
        r.loi = "Không tự đoán được dòng tiêu đề — bấm Chi tiết để chọn sheet và dòng tiêu đề";
        r.dang = "";
        continue;
      }
      await loatKiemTra(ctx, r);
    } catch (e) {
      r.loi = e.message;
    }
    r.dang = "";
  }
  L.dang = false;
  const dem = loatTrung(L);
  for (const r of L.dong) if (dem[r.ma] > 1) r.chon = false; // trùng hợp đồng: Anh tự chọn file đúng
  const ok = L.dong.filter((r) => r.chon).length;
  ctx.toast(`Đã đọc ${L.dong.length} file BOQ · ${ok} file ĐẠT được chọn sẵn. Kiểm tra bảng rồi bấm Ghi.`, "info");
  ctx.render();
}
// Mở 1 file của loạt trong màn hình 1 file (đổi sheet / ánh xạ / xem các dòng); quay lại thì cập nhật dòng đó
function loatMo(ctx, id) {
  const ui = s(ctx);
  const r = ui.loat?.dong.find((x) => x.id === id);
  if (!r?.tep) return;
  ui.imp = { file: r.file, tep: r.tep, ten: r.ten, sheets: r.sheets, sheet: r.sheet, xem: r.xem, hang: r.hang, cot: { ...(r.cot || {}) }, doan: r.doan, tuLoat: id, nguon: r.nguon };
  if (r.ma && r.ma !== ui.boqContract) {
    ui.boqContract = r.ma;
    if (ctx.state.hdLoc) ctx.state.hdLoc = { ben_a: "", du_an: "", q: "" };
    ui.boq = null;
  }
  if (r.ma) {
    // xem trước luôn với ánh xạ hiện tại
    post("/api/boq/kiem_tra", boqBody(ui))
      .then((k) => {
        if (ui.imp?.tuLoat === id && !ui.imp.kt) ui.imp.kt = k;
      })
      .catch(() => {})
      .finally(() => ctx.render());
  }
  ctx.render();
}
function loatVe(ctx) {
  const ui = s(ctx);
  const im = ui.imp;
  const r = ui.loat?.dong.find((x) => x.id === im?.tuLoat);
  ui.imp = null;
  if (!r) return ctx.render();
  Object.assign(r, { sheet: im.sheet, xem: im.xem, hang: im.hang, cot: { ...(im.cot || {}) }, ma: ui.boqContract || r.ma });
  if (im.ghi) {
    r.ghi = im.ghi;
    r.chon = false;
    return ctx.render();
  }
  loatKiemTra(ctx, r);
}
function loatGhi(ctx) {
  const ui = s(ctx);
  const L = ui.loat;
  const chon = L.dong.filter((r) => r.chon && loatChonDuoc(r));
  if (!chon.length) return;
  const dem = {};
  for (const r of chon) dem[r.ma] = (dem[r.ma] || 0) + 1;
  const trung = Object.keys(dem).filter((m) => dem[m] > 1);
  if (trung.length) return ctx.toast(`Có ${trung.length} hợp đồng được chọn từ 2 file trở lên — bỏ chọn bớt trước khi ghi.`, "danger");
  const lech = chon.filter((r) => loatLech(r.kt));
  const thay = chon.filter((r) => r.kt.boq_hien_co);
  const can = lech.length || thay.length;
  const so = (r) => (ui.list || []).find((h) => h.ma_hd === r.ma)?.so_hd || r.ma;
  ctx.openModal({
    title: `Xác nhận ghi ${chon.length} BOQ`,
    body: `<div class="table-wrap"><table class="data-table"><thead><tr><th>Hợp đồng</th><th class="numeric">Số HM</th><th class="numeric">Tổng sau VAT</th><th class="numeric">Lệch</th></tr></thead><tbody>${chon
      .map((r) => `<tr><td><strong>${E(so(r))}</strong><span class="subline">${E(r.ten)}</span></td><td class="numeric">${num(r.kt.so_dong)}</td><td class="numeric">${money(r.kt.tong_sau_vat)}</td><td class="numeric ${loatLech(r.kt) ? "negative-delta" : ""}">${r.kt.lech ? money(r.kt.lech) : "0"}</td></tr>`)
      .join("")}</tbody></table></div>${lech.length ? `<div class="notice notice-danger" style="margin-top:12px">${icon("alert-triangle")} ${lech.length} file <strong>LỆCH</strong> giá trị HĐ gốc vẫn được ghi theo lựa chọn của Anh.</div>` : ""}${thay.length ? `<div class="notice notice-warning" style="margin-top:12px">${icon("alert")} ${thay.length} hợp đồng đã có BOQ gốc — sẽ <strong>thay toàn bộ</strong>.</div>` : ""}`,
    confirmLabel: `Ghi ${chon.length} BOQ`,
    requireReason: !!can,
    reasonLabel: "Lý do ghi (áp dụng cho các file lệch / thay BOQ)",
    onConfirm: async (reason) => {
      L.dangGhi = true;
      ctx.render();
      let ok = 0;
      for (const r of chon) {
        r.dang = "Đang ghi…";
        r.ghiLoi = "";
        ctx.render();
        try {
          const cot = {};
          for (const [k] of TRUONG) if (r.cot?.[k]) cot[k] = r.cot[k];
          r.ghi = await post("/api/boq/ghi", { tep: r.tep, sheet: r.sheet, hang_tieu_de: r.hang, cot, ma_hd: r.ma, ly_do: reason || "", chap_nhan_lech: loatLech(r.kt) });
          r.chon = false;
          ok++;
        } catch (e) {
          r.ghiLoi = e.message;
        }
        r.dang = "";
      }
      L.dangGhi = false;
      ui.boq = null;
      await loadList(ctx);
      // file khác trong loạt cùng hợp đồng vừa ghi: kiểm tra lại (giờ hợp đồng đã có BOQ)
      const daGhi = new Set(chon.filter((r) => r.ghi).map((r) => r.ma));
      for (const r of L.dong) if (!r.ghi && daGhi.has(r.ma)) await loatKiemTra(ctx, r);
      ctx.toast(`Đã ghi BOQ cho ${ok}/${chon.length} hợp đồng.`, ok === chon.length ? "success" : "warning");
      ctx.render();
    },
  });
}
function loatCsv(ctx) {
  const ui = s(ctx);
  const so = (r) => (ui.list || []).find((h) => h.ma_hd === r.ma)?.so_hd || "";
  csv(
    `doi_chieu_boq_ca_loat_${today()}`,
    ["File", "Sheet", "Dòng tiêu đề", "Số HĐ", "Nhận HĐ theo", "Số HM", "Σ trước VAT", "VAT", "Tổng sau VAT", "GT HĐ gốc", "Lệch", "Kết luận", "Ghi chú"],
    ui.loat.dong.map((r) => [
      r.ten,
      r.sheet || "",
      r.hang || "",
      so(r),
      r.doan?.nguon || "",
      r.kt?.so_dong ?? "",
      r.kt?.tong_truoc_vat ?? "",
      r.kt ? r.kt.vat : "",
      r.kt?.tong_sau_vat ?? "",
      r.kt?.gt_hd ?? "",
      r.kt?.lech ?? "",
      r.ghi ? "Đã ghi" : r.loi ? "Lỗi" : !r.ma ? "Chưa nhận HĐ" : r.kt ? ((r.kt.chan || []).length ? "Không ghi được" : r.kt.ket_luan) : "",
      [r.loi, ...(r.kt?.chan || []), r.kt?.boq_hien_co ? `Đã có ${r.kt.boq_hien_co} dòng BOQ` : "", r.ghiLoi].filter(Boolean).join("; "),
    ]),
  );
}

// ================================================================== sự kiện
export function handleContractChange(el, ctx) {
  const ui = s(ctx);
  if (ctx.state.view === "appendices" && handlePLAIChange(el, ctx)) return true;
  if (el.dataset?.contractField) {
    const key = el.dataset.contractField;
    const value = el.type === "checkbox" ? el.checked : el.value;
    if (["detailDate", "boqDate"].includes(key) && !value) return true;
    if (el.type === "search" && ui[key] === value) return true;
    const caret = el.type === "search" ? { start: el.selectionStart, end: el.selectionEnd } : null;
    ui[key] = value;
    if (key === "detailDate") {
      ui.detailBoq = null;
      reload(ctx, loadDetail);
    }
    if (key === "boqDate") reload(ctx, loadBoq);
    if (key === "boqContract") {
      ui.boq = null;
      if (ui.imp) {
        ui.imp.kt = null;
        ui.imp.ghi = null;
      }
      reload(ctx, async (c) => {
        await loadBoq(c);
        if (ui.appendixContract !== ui.boqContract) {
          ui.appendixContract = ui.boqContract;
          await loadAppendix(c);
        }
      });
    }
    if (key === "appendixContract") {
      ui.appendixDetail = null;
      reload(ctx, loadAppendix);
    }
    ctx.render();
    if (caret) {
      const r = document.querySelector(`[data-contract-field="${key}"]`);
      r?.focus({ preventScroll: true });
      r?.setSelectionRange(caret.start, caret.end);
    }
    return true;
  }
  if (el.dataset?.boqMap !== undefined && ui.imp) {
    ui.imp.cot = { ...ui.imp.cot, [el.dataset.boqMap]: el.value };
    ui.imp.kt = null;
    ctx.render();
    return true;
  }
  if (el.dataset?.boqImp && ui.imp) {
    const k = el.dataset.boqImp;
    if (k === "chapNhan") {
      ui.imp.chapNhan = el.checked;
      ctx.render();
    } else if (k === "hang") {
      ui.imp.hang = Number(el.value) || "";
      ui.imp.kt = null;
      ctx.render();
    } else if (k === "sheet") xemSheet(ctx, el.value);
    return true;
  }
  if (el.id === "appendix-file" && el.files?.length) {
    kiemTraPhieu(ctx, el.files[0]);
    return true;
  }
  if (el.id === "boq-file" && el.files?.length) {
    taiBoq(ctx, el.files[0]);
    return true;
  }
  if ((el.id === "boq-files" || el.dataset?.folderFor === "boq-files") && el.files?.length) {
    const fs = Array.from(el.files).filter((f) => /\.(xls[xm]?|pdf|docx)$/i.test(f.name) && !f.name.startsWith("~$"));
    if (!fs.length) ctx.toast("Không có file .xlsx / .xlsm / .xls / .pdf / .docx trong lựa chọn.", "danger");
    else taiLoat(ctx, fs);
    return true;
  }
  if (el.dataset?.boqLoatHd && ui.loat) {
    const r = ui.loat.dong.find((x) => x.id === el.dataset.boqLoatHd);
    if (r) {
      r.ma = el.value;
      loatKiemTra(ctx, r).then(() => ctx.render());
      ctx.render();
    }
    return true;
  }
  if (el.dataset?.boqLoatChon && ui.loat) {
    const r = ui.loat.dong.find((x) => x.id === el.dataset.boqLoatChon);
    if (r) r.chon = el.checked;
    ctx.render();
    return true;
  }
  return false;
}

async function kiemTraPhieu(ctx, file) {
  const ui = s(ctx);
  ui.phieu = { file, dang: true };
  ctx.render();
  try {
    const kq = await uploadFile(`/api/phu_luc/kiem_tra?ten=${encodeURIComponent(file.name)}`, file);
    ui.phieu = { file, ket_qua: kq };
    const ma = kq.phieu[0]?.phu_luc?.ma_hd;
    if (ma && ma !== ui.appendixContract) {
      ui.appendixContract = ma;
      await loadAppendix(ctx);
    }
  } catch (e) {
    ui.phieu = { file, loi: e.message };
  }
  ctx.render();
}
// Đoán hợp đồng của file BOQ: số HĐ ghi trong các dòng đầu sheet ("Kèm theo hợp đồng số 1304/2026/…") hoặc tên file ("HĐ 1304.2026")
function doanHopDong(im, ds) {
  im = im || {};
  ds = ds || [];
  const dau = ((im.xem?.dong || []).slice(0, 12).flat().join(" ") || "").toLowerCase();
  const ten = String(im.ten || im.file?.name || "").toLowerCase();
  const khop = (h, txt, chat) => {
    const so = String(h.so_hd || "").toLowerCase();
    if (chat) return so && txt.includes(so);
    const m = so.match(/^(\d+)\/(\d{4})/);
    return m && new RegExp(`(^|[^\\d])${m[1]}[./_ -]${m[2]}([^\\d]|$)`).test(txt);
  };
  for (const [txt, chat, nguon] of [[dau, true, "dòng đầu file"], [dau, false, "dòng đầu file"], [ten, false, "tên file"]]) {
    const ung = ds.filter((h) => khop(h, txt, chat));
    if (ung.length === 1) return { ma: ung[0].ma_hd, so: ung[0].so_hd, nguon };
  }
  return null;
}
async function taiBoq(ctx, file) {
  const ui = s(ctx);
  ui.imp = { file, dang: true };
  ctx.render();
  try {
    const d = await uploadFile(`/api/boq/tai_len?ten=${encodeURIComponent(file.name)}`, file);
    const g = d.goi_y || {};
    ui.imp = { file, tep: d.tep, ten: d.ten, sheets: d.sheets, sheet: g.sheet, xem: g, hang: g.hang_tieu_de || "", cot: { ...(g.cot || {}) }, nguon: d.nguon, tuXls: d.tu_xls };
    if (!g.hang_tieu_de) ctx.toast("Không tự đoán được dòng tiêu đề — chọn sheet và nhập dòng tiêu đề.", "warning");
    const doan = doanHopDong(ui.imp, ui.list);
    ui.imp.doan = doan;
    if (doan && doan.ma !== ui.boqContract) {
      ui.boqContract = doan.ma; // tự chọn hợp đồng theo số HĐ ghi trong file
      if (ctx.state.hdLoc) ctx.state.hdLoc = { ben_a: "", du_an: "", q: "" }; // bỏ lọc để hợp đồng được chọn hiện ra
      ctx.toast(`File ghi hợp đồng ${doan.so} → đã chọn hợp đồng này.`, "info");
    }
  } catch (e) {
    ui.imp = { loi: e.message };
  }
  ctx.render();
}
async function xemSheet(ctx, sheet) {
  const ui = s(ctx);
  try {
    const x = await post("/api/boq/sheet", { tep: ui.imp.tep, sheet });
    Object.assign(ui.imp, { sheet, xem: x, hang: x.hang_tieu_de || "", cot: { ...(x.cot || {}) }, kt: null, ghi: null });
  } catch (e) {
    ctx.toast(e.message, "danger");
  }
  ctx.render();
}
function boqBody(ui, extra = {}) {
  const cot = {};
  for (const [k] of TRUONG) if (ui.imp.cot[k]) cot[k] = ui.imp.cot[k];
  return { tep: ui.imp.tep, sheet: ui.imp.sheet, hang_tieu_de: ui.imp.hang, cot, ma_hd: ui.boqContract, ...extra };
}

export function handleContractAction(action, el, ctx) {
  const ui = s(ctx);
  if (action.startsWith("plai-")) return handlePLAIAction(action, el, ctx);
  switch (action) {
    case "contract-open":
      ui.selected = el.dataset.id;
      ui.detailTab = "parameters";
      ui.detail = null;
      ui.detailBoq = null;
      ctx.render();
      reload(ctx, loadDetail);
      return true;
    case "contracts-back":
      ui.selected = null;
      ui.chuaXacNhan = false;
      ctx.render();
      reload(ctx, loadList);
      return true;
    case "contracts-new":
      ctx.navigate("extraction");
      return true;
    case "contracts-clear":
      ui.query = "";
      ui.type = "all";
      ui.risk = "all";
      ctx.render();
      return true;
    case "contract-tab":
      ui.detailTab = el.dataset.tab;
      ctx.render();
      if (ui.detailTab === "boq" && !ui.detailBoq) reload(ctx, loadDetailBoq);
      return true;
    case "contract-date-today":
      ui.detailDate = today();
      ui.detailBoq = null;
      reload(ctx, loadDetail);
      return true;
    case "contract-param-reset":
      ui.paramGroup = "all";
      ui.amendedOnly = false;
      ui.chuaXacNhan = false;
      ctx.render();
      return true;
    case "param-source":
      paramSourceDrawer(ctx, ui, el.dataset.ma);
      return true;
    case "param-confirm": {
      const ma = el.dataset.ma;
      const ghiChu = document.getElementById("param-note")?.value.trim() || "";
      el.disabled = true;
      post(`/api/hop_dong/${encodeURIComponent(ui.selected)}/tham_so/${encodeURIComponent(ma)}/xac_nhan`, { ghi_chu: ghiChu })
        .then(async () => {
          ctx.closeOverlay();
          ctx.toast(`Đã xác nhận ${ma} trong CSDL.`);
          await loadDetail(ctx);
          ctx.render();
        })
        .catch((e) => {
          el.disabled = false;
          ctx.toast(e.message, "danger");
        });
      return true;
    }
    case "contract-open-appendices":
      ui.appendixContract = ui.selected;
      ui.appendixDetail = null;
      ctx.navigate("appendices");
      return true;
    case "contract-open-boq":
      ui.boqContract = ui.selected;
      ui.boqDate = ui.detailDate;
      ui.boqView = "effective";
      ui.boq = null;
      ctx.navigate("boq");
      return true;
    case "contract-import-boq":
      ui.boqContract = ui.selected;
      ui.boqView = "import";
      ctx.navigate("boq");
      return true;
    case "contract-open-payments":
      ctx.navigate("payments", { hd: ui.selected });
      return true;
    case "contracts-export":
    case "contract-detail-export":
    case "boq-export": {
      const body = action === "contracts-export" ? {} : action === "boq-export" ? { ref: ui.boqContract, ngay: ui.boqDate } : { ref: ui.selected, ngay: ui.detailDate };
      ctx.toast("Đang xuất Excel…", "info");
      post("/api/csdl/xuat_excel", body)
        .then((r) => (location.href = r.tai))
        .catch((e) => ctx.toast(e.message, "danger"));
      return true;
    }
    case "appendix-clear-filter":
      ui.appendixStatus = "all";
      ctx.render();
      return true;
    case "appendix-template": {
      const ma = ctx.state.view === "contracts" ? ui.selected : ui.appendixContract;
      if (!ma) return true;
      post(`/api/hop_dong/${encodeURIComponent(ma)}/phieu_phu_luc`)
        .then((r) => {
          ctx.toast(`Đã tạo phiếu ${r.so_pl} cho ${ma} — điền phiếu rồi nạp lại để kiểm tra.`);
          location.href = r.tai;
        })
        .catch((e) => ctx.toast(e.message, "danger"));
      return true;
    }
    case "appendix-reset":
      ui.phieu = null;
      ctx.render();
      return true;
    case "appendix-record": {
      const ph = ui.phieu;
      if (!ph?.ket_qua || ph.ghi) return true;
      const ds = ph.ket_qua.phieu;
      const tom = ds
        .map((p) => {
          const pl = p.phu_luc || {};
          const do_ = p.kiem_tra.filter((r) => r.muc === "ĐỎ").length;
          const vang = p.kiem_tra.filter((r) => r.muc === "VÀNG").length;
          if (p.co_chan) return `<li class="muted"><strong>${E(pl.so_pl || p.sheet)}</strong> · bỏ qua (có lỗi CHẶN)</li>`;
          return `<li><strong>${E(pl.so_pl || p.sheet)}</strong> · ${E(pl.ma_hd || "")} · hiệu lực ${fmtDate(pl.ngay_hieu_luc)}${pl.gt_sau_vat ? ` · ${pl.gt_sau_vat > 0 ? "+" : ""}${money(pl.gt_sau_vat)} đồng sau VAT` : ""}${do_ || vang ? ` · <span class="danger-text">${do_} cờ ĐỎ, ${vang} VÀNG</span>` : ""}</li>`;
        })
        .join("");
      ctx.openModal({
        title: "Ghi phụ lục vào CSDL",
        body: `<p>Ghi các phụ lục sau (theo thứ tự hiệu lực), kèm cờ cảnh báo:</p><ul style="margin:12px 0 12px 18px;line-height:1.8">${tom}</ul><div class="notice notice-warning">Giá trị hiệu lực, tham số và BOQ sẽ tính lại từ ngày hiệu lực của phụ lục. Muốn bỏ sau này phải Hủy kèm lý do (giữ lịch sử).</div>`,
        confirmLabel: "Ghi vào CSDL",
        onConfirm: async () => {
          ui.busy = true;
          ctx.render();
          try {
            const r = await uploadFile(`/api/phu_luc/nap?ten=${encodeURIComponent(ph.file.name)}`, ph.file);
            ph.ghi = r;
            const ok = r.phieu.filter((p) => p.ket_qua === "ĐÃ GHI").length;
            ctx.toast(ok ? `Đã ghi ${ok} phụ lục vào CSDL.` : "Không ghi được — còn lỗi CHẶN.", ok ? "success" : "danger");
            await loadList(ctx);
            await loadAppendix(ctx);
          } catch (e) {
            ctx.toast(e.message, "danger");
          }
          ui.busy = false;
          ctx.render();
        },
      });
      return true;
    }
    case "appendix-cancel": {
      const no = el.dataset.no;
      const ma = el.dataset.hd;
      ctx.openModal({
        title: `Hủy phụ lục ${no}`,
        body: `<p>Phụ lục sẽ chuyển sang trạng thái <strong>Đã hủy</strong>. Dữ liệu gốc và lịch sử vẫn được giữ để truy vết.</p><div class="notice notice-warning">Giá trị hiệu lực, tham số và BOQ sẽ tính lại khi bỏ phụ lục này. Nếu còn phụ lục sau nó, kiểm tra lại các phụ lục đó.</div>`,
        confirmLabel: "Hủy phụ lục",
        danger: true,
        requireReason: true,
        reasonLabel: "Lý do hủy",
        onConfirm: async (reason) => {
          try {
            await post(`/api/hop_dong/${encodeURIComponent(ma)}/phu_luc/${encodeURIComponent(no)}/huy`, { ly_do: reason });
            ctx.toast(`Đã hủy ${no} và lưu lý do.`);
            await loadList(ctx);
            if (ctx.state.view === "contracts") await loadDetail(ctx);
            else await loadAppendix(ctx);
            ctx.render();
          } catch (e) {
            ctx.toast(e.message, "danger");
          }
        },
      });
      return true;
    }
    case "appendix-detail": {
      const no = el.dataset.no;
      const ma = el.dataset.hd;
      get(`/api/hop_dong/${encodeURIComponent(ma)}/phu_luc/${encodeURIComponent(no)}`)
        .then((r) => {
          const pl = r.phu_luc;
          const delta = Number(pl.gt_sau_vat) || 0;
          ctx.openDrawer({
            title: `${pl.so_pl} · Chi tiết phụ lục`,
            body: `${style()}<div class="contracts-screen"><div class="contract-banner"><div><strong>${E(pl.noi_dung || pl.loai || pl.so_pl)}</strong><span class="small muted">Ký ${fmtDate(pl.ngay_ky)} · Hiệu lực ${fmtDate(pl.ngay_hieu_luc)}${pl.can_cu ? ` · Căn cứ: ${E(pl.can_cu)}` : ""}</span></div></div>
            <div class="grid-2"><div><span class="small muted">Trạng thái</span><p>${badge(pl.trang_thai, pl.trang_thai === "Đã ký" ? "success" : pl.trang_thai === "Đã hủy" ? "neutral" : "warning")}</p></div><div><span class="small muted">Thay đổi giá trị sau VAT</span><p><strong>${delta ? `${delta > 0 ? "+" : ""}${money(delta)}` : "Không thay đổi"}</strong>${pl.gt_hd_sau_pl ? `<span class="subline">GT HĐ sau PL ghi trên phụ lục: ${money(pl.gt_hd_sau_pl)}</span>` : ""}</p></div></div>
            ${pl.ly_do_huy ? `<div class="notice notice-warning"><strong>Đã hủy:</strong> ${E(pl.ly_do_huy)}</div>` : ""}
            ${r.thay_doi_tham_so.length ? `<h3>Tham số thay đổi</h3><table class="data-table"><thead><tr><th>Mã</th><th>Cũ → mới</th><th>Trích dẫn</th></tr></thead><tbody>${r.thay_doi_tham_so.map((t) => `<tr><td><strong>${E(t.ma_ts)}</strong></td><td>${E(t.gia_tri_cu ?? "—")} → <strong>${E(t.gia_tri_moi)}</strong></td><td class="small">${E(t.trich_dan || "")}</td></tr>`).join("")}</tbody></table>` : ""}
            ${r.boq.length ? `<h3 style="margin-top:20px">BOQ thay đổi (${r.boq.length} dòng)</h3><table class="data-table"><thead><tr><th>Thao tác</th><th>Mã HM / tên</th><th class="numeric">KL</th><th class="numeric">Đơn giá</th></tr></thead><tbody>${r.boq.map((b) => `<tr><td>${badge({ THEM: "Thêm", THAY: "Thay", BO: "Bỏ" }[b.thao_tac] || b.thao_tac, b.thao_tac === "BO" ? "danger" : b.thao_tac === "THEM" ? "success" : "info")}</td><td><strong>${E(b.ma_hm)}</strong><span class="subline">${E(b.ten || "")}</span></td><td class="numeric">${num(b.kl)}</td><td class="numeric">${dg(b.don_gia)}</td></tr>`).join("")}</tbody></table>` : ""}
            ${r.canh_bao.length ? `<h3 style="margin-top:20px">Cờ khi nạp</h3>${r.canh_bao.map((c) => `<p class="small">${badge(c.muc_do, MUC_KT[c.muc_do] || "neutral")} <strong>${E(c.ma_kt)}</strong> ${E(c.noi_dung)}</p>`).join("")}` : ""}
            <h3 style="margin-top:20px">Nhật ký</h3>${r.nhat_ky.map((n) => `<div class="history-item"><div class="history-date">${E(n.thoi_diem)}</div><div><div class="history-title">${E(n.thao_tac)}</div><p class="small">${E(n.chi_tiet)}</p><span class="muted small">${E(n.nguoi || "")}</span></div></div>`).join("") || '<p class="small muted">Chưa có.</p>'}
            <p class="small muted" style="margin-top:16px">Nguồn: ${E(pl.phieu || pl.file_nguon || "—")} · Người nạp: ${E(pl.nguoi_nhap || "—")} · ${E(pl.ngay_nap || "")}</p>
            ${r.lan_truoc.length ? `<div class="notice notice-info" style="margin-top:12px">Có ${r.lan_truoc.length} bản ${E(pl.so_pl)} trước đó đã hủy.</div>` : ""}</div>`,
          });
        })
        .catch((e) => ctx.toast(e.message, "danger"));
      return true;
    }
    case "appendix-check-export": {
      const kq = ui.phieu?.ket_qua;
      if (!kq) return true;
      const rows = [];
      for (const p of kq.phieu) for (const r of p.kiem_tra) rows.push([p.sheet, p.phu_luc?.so_pl || "", r.ma, r.muc, r.noi_dung]);
      csv(`Kiem_tra_${kq.tep.replace(/\.\w+$/, "")}`, ["Sheet", "Phụ lục", "Mã", "Mức", "Giải thích"], rows);
      return true;
    }
    case "boq-view":
      ui.boqView = el.dataset.view;
      ctx.render();
      if (ui.boqView === "effective") reload(ctx, loadBoq);
      return true;
    case "boq-view-effective":
      ui.boqView = "effective";
      ui.boq = null;
      ctx.render();
      reload(ctx, loadBoq);
      return true;
    case "boq-import-open":
      ui.boqView = "import";
      ctx.render();
      return true;
    case "boq-date-today":
      ui.boqDate = today();
      reload(ctx, loadBoq);
      return true;
    case "boq-clear-search":
      ui.boqQuery = "";
      ctx.render();
      return true;
    case "boq-import-reset":
      if (ui.imp?.tuLoat && ui.loat) {
        loatVe(ctx);
        return true;
      }
      ui.imp = null;
      ctx.render();
      return true;
    case "boq-loat-reset":
      ui.loat = null;
      ui.imp = null;
      ctx.render();
      return true;
    case "boq-loat-mo":
      loatMo(ctx, el.dataset.id);
      return true;
    case "boq-loat-ghi":
      loatGhi(ctx);
      return true;
    case "boq-loat-csv":
      if (ui.loat) loatCsv(ctx);
      return true;
    case "boq-preview": {
      if (!ui.imp?.tep) return true;
      ui.busy = true;
      ctx.render();
      post("/api/boq/kiem_tra", boqBody(ui))
        .then((k) => {
          ui.imp.kt = k;
          ui.imp.ghi = null;
          ui.imp.chapNhan = false;
          ctx.toast(`Đã đọc ${k.so_dong} hạng mục · ${k.ket_luan}.`, k.ket_luan === "ĐẠT" && !k.chan.length ? "success" : "warning");
        })
        .catch((e) => ctx.toast(e.message, "danger"))
        .finally(() => {
          ui.busy = false;
          ctx.render();
        });
      return true;
    }
    case "boq-confirm": {
      const k = ui.imp?.kt;
      if (!k || k.chan.length || ui.imp.ghi) return true;
      const lech = k.ket_luan !== "ĐẠT";
      if (lech && !ui.imp.chapNhan) return true;
      const canLyDo = k.can_ly_do || lech;
      ctx.openModal({
        title: "Xác nhận ghi BOQ",
        body: `<p>Ghi <strong>${k.so_dong} hạng mục</strong> vào BOQ gốc của <strong>${E(k.ma_hd)}</strong> (${E(k.so_hd)}).</p><div class="notice notice-${lech ? "danger" : "success"}">${lech ? `Tổng sau VAT <strong>lệch ${money(Math.abs(k.lech))} đồng</strong> so với giá trị HĐ gốc ${money(k.gt_hd)} đồng.` : `Tổng sau VAT khớp giá trị HĐ gốc: <strong>${money(k.gt_hd)} đồng</strong>.`}</div>${k.boq_hien_co ? `<p class="danger-text small">Thay ${k.boq_hien_co} dòng BOQ gốc đang có.</p>` : ""}`,
        confirmLabel: "Xác nhận ghi BOQ",
        requireReason: canLyDo,
        reasonLabel: k.boq_hien_co ? "Lý do thay BOQ gốc" : "Lý do ghi dù lệch",
        onConfirm: async (reason) => {
          ui.busy = true;
          ctx.render();
          try {
            ui.imp.ghi = await post("/api/boq/ghi", boqBody(ui, { ly_do: reason || "", chap_nhan_lech: lech }));
            ctx.toast(`Đã ghi BOQ ${ui.imp.ghi.so_dong} hạng mục cho ${k.ma_hd}.`);
            ui.boq = null;
            await loadList(ctx);
          } catch (e) {
            ctx.toast(e.message, "danger");
          }
          ui.busy = false;
          ctx.render();
        },
      });
      return true;
    }
    case "boq-export-preview": {
      const k = ui.imp?.kt;
      if (!k) return true;
      csv(
        `BOQ_xem_truoc_${k.ma_hd}`,
        ["Dòng", "Nhóm", "STT", "Mã hạng mục", "Tên công việc", "ĐVT", "Khối lượng", "Đơn giá", "Thành tiền"],
        k.xem_truoc.map((r) => [r.dong, r.nhom, r.stt, r.ma_rieng || "", r.ten, r.dvt, r.kl, r.don_gia, r.thanh_tien]),
      );
      return true;
    }
    case "boq-history": {
      const b = ctx.state.view === "contracts" ? ui.detailBoq : ui.boq;
      const r = b?.dong.find((x) => x.ma_hm === el.dataset.code);
      if (!r) return true;
      const tt = Math.round((r.kl || 0) * (r.don_gia || 0));
      ctx.openDrawer({
        title: `${r.ma_hm} · ${r.ten}`,
        body: `${style()}<div class="contracts-screen"><div class="notice notice-info">Đang xem BOQ hiệu lực tại <strong>${fmtDate(b.ngay)}</strong>: ${num(r.kl)} ${E(r.dvt || "")} × ${dg(r.don_gia)} = <strong>${money(tt)} đồng</strong>.</div>${r.nhom ? `<p class="small muted">Nhóm: ${E(r.nhom)}</p>` : ""}${(r.lich_su || []).map((t, i) => `<div class="history-item"><div class="history-date">${i === 0 ? "Gốc" : `Lần ${i}`}</div><div><div class="history-title">${E(t.split(":")[0])}</div><p class="small">${E(t.split(":").slice(1).join(":").trim())}</p></div></div>`).join("")}<p class="small muted" style="margin-top:12px">Vị trí nguồn: ${E(r.vi_tri_nguon || "—")}${r.thanh_tien_ghi != null ? ` · thành tiền ghi trên tài liệu ${money(r.thanh_tien_ghi)}` : ""}</p></div>`,
      });
      return true;
    }
    default:
      return false;
  }
}
