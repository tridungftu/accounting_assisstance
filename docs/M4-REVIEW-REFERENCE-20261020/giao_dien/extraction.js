// extraction.js — Trích tham số hợp đồng: hàng đợi, tiến độ 9 bước, nhật ký, bảng 37 tham số, sửa / xác nhận / nạp CSDL.
import { icon, badge, escapeHTML, upload, header } from "./ui.js";
import { api, get, post, money, clock, size, isOk } from "./api.js";

const E = escapeHTML;
const MUC = ["Thông tin", "Thấp", "Vừa", "Cao"];
const TT_HD = {
  "Chờ": ["Chờ", "neutral"],
  "Đang chạy": ["Đang chạy", "info"],
  "Xong": ["Xong", "success"],
  "Xong có ô vàng": ["Xong có ô vàng", "warning"],
  "Lỗi": ["Lỗi", "danger"],
  "Bỏ qua (dùng kết quả cũ)": ["Dùng kết quả cũ", "success"],
  "Đã dừng": ["Đã dừng", "neutral"],
};

function S(ctx) {
  if (!ctx.state.ex)
    ctx.state.ex = {
      tab: "queue",
      luot: null, // lượt đang xem (đang chạy / vừa chạy)
      run: null, // chi tiết lượt từ máy chủ
      draft: null, // lượt mới đang chọn file, chưa chạy
      draftFiles: [],
      opts: null,
      result: null, // {luot, ten, kq}
      resultTen: null,
      group: "all",
      yellowOnly: false,
      query: "",
      sort: "code",
      selected: [],
      uploading: 0,
      loaded: false,
      timer: null,
    };
  return ctx.state.ex;
}

export async function loadExtraction(ctx) {
  const s = S(ctx);
  const opts = ctx.state.navOpts || {};
  ctx.state.navOpts = {};
  try {
    if (!s.opts) {
      const c = await get("/api/cai_dat");
      s.opts = {
        model: c.may_ai.model,
        ra_lai: c.trich_xuat.ra_lai,
        cloud: c.cloud.bat,
        ncc: c.cloud.nha_cung_cap,
        tyLe: c.cloud.ty_le,
        chay_lai: false,
        coKhoa: c.cloud.khoa,
      };
    }
    if (opts.loai === "trich_xuat" && opts.ma) {
      s.luot = opts.ma;
      s.tab = "queue";
    }
    const ds = (await get("/api/trich_xuat?gioi_han=30")).ds.filter((l) => l.tt !== "chua_chay");
    s.runs = ds;
    if (!s.luot) {
      const dang = ds.find((l) => ["dang_chay", "cho"].includes(l.tt));
      s.luot = (dang || ds[0] || {}).luot || null;
    }
    if (s.luot) await refreshRun(ctx, false);
  } catch (e) {
    ctx.toast(e.message, "danger");
  }
  s.loaded = true;
  if (ctx.state.view === "extraction") ctx.render();
}

async function refreshRun(ctx, partial = true) {
  const s = S(ctx);
  if (!s.luot) return;
  const prev = s.run?.tt;
  s.run = await get(`/api/trich_xuat/${s.luot}`);
  const running = ["dang_chay", "cho"].includes(s.run.tt);
  if (running) schedule(ctx);
  if (prev && prev !== s.run.tt && !running) {
    // vừa xong → mở kết quả hợp đồng đầu tiên
    const first = (s.run.hd || []).find((h) => h.ten && h.so_ok != null);
    if (first && s.run.tt === "xong") {
      s.resultTen = first.ten;
      await loadResult(ctx, s.luot, first.ten);
    }
    if (ctx.state.view === "extraction") ctx.render();
    return;
  }
  if (ctx.state.view !== "extraction") return;
  if (partial && s.tab === "queue") {
    const q = document.getElementById("ex-queue"),
      p = document.getElementById("ex-progress");
    if (q && p) {
      q.outerHTML = queueTable(s);
      p.outerHTML = progressPanel(s);
      const log = document.querySelector(".ex-log");
      if (log) log.scrollTop = log.scrollHeight;
      return;
    }
  }
  if (!partial) return;
  // màn kết quả: chỉ vẽ lại khi lượt thực sự thay đổi (thêm hợp đồng xong, đổi bước) — tránh làm bảng đang xem
  // nhảy về đầu và mất chữ đang gõ (trước đây vẽ lại mỗi 2 giây)
  const ky = JSON.stringify([s.run.tt, (s.run.hd || []).map((h) => [h.ten, h.tt, h.so_ok, h.so_vang])]);
  if (ky === s.kyVe) return;
  s.kyVe = ky;
  ctx.render();
}
function schedule(ctx) {
  const s = S(ctx);
  clearTimeout(s.timer);
  s.timer = setTimeout(() => refreshRun(ctx).catch(() => schedule(ctx)), 2000);
}

async function loadResult(ctx, luot, ten) {
  const s = S(ctx);
  s.result = { luot, ten, kq: await get(`/api/trich_xuat/${luot}/hd/${encodeURIComponent(ten)}`) };
  s.selected = [];
}

const button = (action, label, kind = "", attrs = "") => `<button class="btn ${kind}" data-action="${action}" ${attrs}>${label}</button>`;

function css() {
  return `<style>
  .extraction .ex-topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px;flex-wrap:wrap}
  .extraction .ex-state-switch{display:flex;align-items:center;gap:8px;color:#64748b;font-size:12px}
  .extraction .ex-state-switch select{min-height:40px;padding:6px 30px 6px 10px;border:1px solid #d8e0e9;border-radius:5px;background:white;color:#334155;max-width:420px}
  .extraction .panel-head h3{font-size:14px;font-weight:600;margin:0}.extraction .ex-topbar .tabs{margin-bottom:0}.extraction .ex-topbar .tab{display:flex;align-items:center;gap:8px}
  .extraction .notice,.ex-detail .notice{display:block}.extraction .notice p,.ex-detail .notice p{margin:7px 0 0}
  .extraction .ex-queue-layout{display:grid;grid-template-columns:minmax(300px,0.88fr) minmax(430px,1.12fr);gap:18px;align-items:start}
  .extraction .ex-upload .upload-zone{min-height:154px}
  .extraction .ex-file-tools{display:flex;justify-content:space-between;align-items:center;margin:12px 0 0;gap:12px}
  .extraction .ex-file-name{display:flex;align-items:center;gap:9px;max-width:300px;font-weight:600}
  .extraction .ex-file-name svg{flex:0 0 17px;color:#64748b}.extraction .ex-file-name span{overflow-wrap:anywhere}
  .extraction .ex-section-gap{margin-top:18px}.extraction .ex-options{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .extraction .ex-checkbox{display:flex;gap:9px;align-items:flex-start;min-height:40px;font-size:13px;line-height:1.6;cursor:pointer}.extraction .ex-checkbox input{margin-top:4px;width:16px;height:16px;accent-color:#173d63}
  .extraction .ex-cloud-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px}
  .extraction .ex-cloud-box{margin-top:18px;padding:16px;background:#f8fafc;border:1px solid #e1e7ee;border-radius:6px}
  .extraction .ex-cloud-settings{display:grid;grid-template-columns:1.15fr 0.85fr;gap:14px;margin-top:16px}.extraction .ex-cloud-help{font-size:12px;line-height:1.65;color:#64748b;margin:10px 0 0}
  .extraction .ex-job-title{display:flex;align-items:flex-start;gap:12px;margin-bottom:20px}.extraction .ex-job-icon{width:42px;height:46px;display:grid;place-items:center;border:1px solid #d6e0ea;background:#f4f7fa;border-radius:5px;color:#173d63;flex:0 0 42px}
  .extraction .ex-job-title h3{font-size:15px;margin:0 0 5px;overflow-wrap:anywhere}.extraction .ex-job-title p{margin:0}
  .extraction .ex-progress-top{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:10px}.extraction .ex-progress-percent{font-size:30px;line-height:1.1;letter-spacing:-1px;color:#173d63;font-weight:650;font-variant-numeric:tabular-nums}
  .extraction .ex-progress-track{height:7px;background:#e7edf3;overflow:hidden;border-radius:3px}.extraction .ex-progress-track span{display:block;height:100%;background:#244d73;transition:width .4s}
  .extraction .ex-job-times{display:flex;justify-content:space-between;gap:8px;font-size:12px;color:#64748b;margin:11px 0 21px}.extraction .ex-job-times strong{font-weight:600;color:#334155;font-variant-numeric:tabular-nums}
  .extraction .ex-timeline{list-style:none;padding:0;margin:0 0 20px;display:grid;grid-template-columns:1fr 1fr;gap:0 20px}
  .extraction .ex-step{display:flex;gap:9px;align-items:flex-start;position:relative;min-height:52px;padding-bottom:12px;line-height:1.35;font-size:12px;color:#64748b}
  .extraction .ex-step-dot{width:22px;height:22px;display:grid;place-items:center;flex:0 0 22px;background:#f1f4f7;border:1px solid #d7dfe8;border-radius:50%;font-size:11px;font-weight:600;font-variant-numeric:tabular-nums}.extraction .ex-step-dot svg{width:13px;height:13px}
  .extraction .ex-step-title{font-weight:500;margin-top:3px}.extraction .ex-step small{display:block;margin-top:5px;color:#8290a0;font-size:10px}.extraction .ex-step.complete .ex-step-dot{background:#edf5f0;color:#247149;border-color:#cfe2d6}.extraction .ex-step.complete .ex-step-title{color:#426254}.extraction .ex-step.current .ex-step-dot{background:#244d73;color:white;border-color:#244d73}.extraction .ex-step.current .ex-step-title{color:#173d63;font-weight:650}.extraction .ex-step.skipped{opacity:.72}
  .extraction .ex-log{height:185px;overflow:auto;border:1px solid #e1e7ee;border-radius:5px;background:#f8fafc;padding:12px 13px;font-size:11px;line-height:1.75}.extraction .ex-log-row{display:flex;gap:9px;margin-bottom:4px}.extraction .ex-log-row time{flex:0 0 54px;color:#8391a1;font-variant-numeric:tabular-nums}.extraction .ex-log-row.warn span{color:#976919}.extraction .ex-log-row.err span{color:#ad3536}
  .extraction .ex-log-label{display:flex;justify-content:space-between;align-items:center;margin:20px 0 8px;font-size:12px;font-weight:600}.extraction .ex-log-label span{font-weight:400;color:#94a3b8;font-size:11px}.extraction .ex-job-footer{margin-top:16px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
  .extraction .ex-results-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.extraction .ex-results-actions{display:flex;gap:8px;flex-wrap:wrap}
  .extraction .ex-results-summary{display:grid;grid-template-columns:1.4fr repeat(3,1fr);border-bottom:1px solid #e1e7ee;margin:0 -20px;padding:0 20px}.extraction .ex-results-summary>div{padding:18px 14px 18px 0}.extraction .ex-results-summary strong{font-size:21px;color:#173d63;font-variant-numeric:tabular-nums;display:block;margin-bottom:5px}.extraction .ex-results-summary span{font-size:12px;color:#64748b}
  .extraction .ex-results-toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:16px 0}.extraction .ex-results-toolbar .field{margin:0;min-width:190px}.extraction .ex-results-toolbar input[type=search]{min-width:240px}.extraction .ex-results-toolbar .ex-checkbox{align-items:center;white-space:nowrap}.extraction .ex-results-toolbar .ex-checkbox input{margin-top:0}
  .extraction .ex-table{width:100%;min-width:2310px;table-layout:fixed}.extraction .ex-table th{white-space:nowrap}.extraction .ex-table td{vertical-align:top;line-height:1.6;font-size:12px}.extraction .ex-table td input[type=checkbox]{width:16px;height:16px;accent-color:#173d63;cursor:pointer}.extraction .ex-row-yellow{background:#fffbf1!important}.extraction .ex-row-yellow td:nth-child(2){box-shadow:inset 3px 0 #cb922e}.extraction .ex-row-yellow .ex-value-input{border-color:#e1cb91;background:#fffef9}
  .extraction .ex-table td:first-child,.extraction .ex-table th:first-child{padding:8px 2px}.extraction .ex-table .checkbox-target{min-width:40px;min-height:40px}
  .extraction .ex-value-input{width:100%;min-height:40px;border:1px solid transparent;border-radius:4px;background:transparent;padding:7px 8px;color:#243449;font:inherit}.extraction .ex-value-input:hover{border-color:#c8d4e1}.extraction .ex-value-input:focus{border-color:#244d73;background:white;outline:2px solid #dbe8f4;outline-offset:1px}
  .extraction .ex-code-btn{background:transparent;border:0;padding:0;min-height:40px;font:inherit;font-weight:650;color:#1e4c75;cursor:pointer;text-align:left;text-decoration:underline;text-decoration-color:#b9c7d6;text-underline-offset:4px}.extraction .ex-quote{max-height:62px;overflow:hidden;color:#64748b;font-size:11px;line-height:1.7}.extraction .ex-warning{display:block;color:#976919;font-size:11px;line-height:1.55;margin-top:5px}.extraction .ex-confirm-one{min-height:40px;font-size:11px;margin-top:6px;padding:5px 9px}.extraction .ex-table-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:15px 20px;border-top:1px solid #e1e7ee;background:#fbfcfd}.extraction .ex-table-footer p{margin:0;font-size:12px;color:#64748b}.extraction .ex-batch-selection{display:flex;gap:12px;align-items:center;font-size:12px;font-weight:600}
  .ex-detail .ex-detail-meta{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 18px}.ex-detail .ex-citation{border-left:3px solid #244d73;background:#f4f7fa;padding:16px 18px;margin:8px 0 20px;line-height:1.9;color:#334155;font-size:14px}.ex-detail .ex-original{padding:13px 14px;background:#f8fafc;border:1px solid #e1e7ee;border-radius:5px;margin:10px 0 20px;font-size:13px}.ex-detail .ex-detail-footer{display:flex;gap:9px;margin-top:20px;flex-wrap:wrap}.ex-detail textarea{width:100%;min-height:90px;resize:vertical}.ex-detail .history-item{padding:10px 0;border-bottom:1px solid #e2e7ee;font-size:12px}
  @media(max-width:1140px){.extraction .ex-queue-layout{grid-template-columns:1fr}.extraction .ex-results-summary{grid-template-columns:repeat(4,1fr)}}
  @media(max-width:650px){.extraction .ex-options,.extraction .ex-cloud-settings{grid-template-columns:1fr}.extraction .ex-results-summary{grid-template-columns:1fr 1fr}.extraction .ex-timeline{grid-template-columns:1fr}.extraction .ex-results-toolbar .field{width:100%}}
  @media(prefers-reduced-motion:reduce){.extraction .ex-progress-track span{transition:none}}
</style>`;
}

// ------------------------------------------------------------------ hàng đợi + tiến độ
function queueTable(s) {
  const rows = [];
  for (const h of s.run?.hd || []) rows.push({ ...h, nguon: "run" });
  for (const f of s.draftFiles) rows.push({ file: f.ten, tt: "Chờ", kich_thuoc: f.kich_thuoc, nguon: "draft" });
  if (!rows.length) return `<div id="ex-queue" class="panel-body muted small" style="border-top:1px solid #e1e7ee">Chưa có file trong hàng đợi.</div>`;
  const now = Date.now() / 1000;
  return `<div id="ex-queue" class="table-wrap"><table class="data-table"><thead><tr><th>File hợp đồng</th><th>Trạng thái</th><th class="numeric">Thời gian</th><th></th></tr></thead><tbody>${rows
    .map((q) => {
      const st = TT_HD[q.tt] || [q.tt, "neutral"];
      const t = q.tt === "Đang chạy" && q.bat_dau ? clock(now - q.bat_dau) : q.thoi_gian != null ? clock(q.thoi_gian) : "—";
      const sub = q.nguon === "draft" ? `${size(q.kich_thuoc || 0)} · lượt mới, chưa chạy` : q.loi ? E(q.loi) : q.so_ok != null ? `OK ${q.so_ok} · cần xem ${q.so_vang}${q.dung_dap_an ? ` · đáp án ${E(q.dung_dap_an)}` : ""}` : "";
      const act =
        q.nguon === "draft"
          ? button("extraction-remove", icon("x"), "btn-ghost", `data-ten="${E(q.file)}" title="Xóa khỏi hàng đợi" aria-label="Xóa ${E(q.file)} khỏi hàng đợi"`)
          : q.ten && q.so_ok != null
            ? button("extraction-results", icon("chevron-right"), "btn-ghost", `data-ten="${E(q.ten)}" title="Mở kết quả" aria-label="Mở kết quả ${E(q.file)}"`)
            : "";
      return `<tr><td><div class="ex-file-name">${icon("file")}<span>${E(q.file)}</span></div><div class="muted small" style="padding-left:26px">${sub}</div></td><td>${badge(...st)}</td><td class="numeric small">${t}</td><td>${act}</td></tr>`;
    })
    .join("")}</tbody></table></div>`;
}

function options(s) {
  const o = s.opts || {};
  const models = (s.aiModels || []).length ? s.aiModels : [o.model];
  const coKhoa = (o.coKhoa || {})[o.ncc]?.co_khoa;
  const running = s.run && ["dang_chay", "cho"].includes(s.run.tt);
  return `<div class="panel ex-section-gap"><div class="panel-head"><h3>Thiết lập trích tham số</h3>${badge("Máy AI nội bộ", "neutral")}</div><div class="panel-body"><div class="ex-options"><label class="field">Model<select id="extraction-model">${[...new Set([...models, o.model])].map((m) => `<option ${o.model === m ? "selected" : ""}>${E(m)}</option>`).join("")}</select></label><label class="ex-checkbox" style="padding-top:26px"><input id="extraction-reread" type="checkbox" ${o.ra_lai ? "checked" : ""}><span>Rà lại toàn hợp đồng<br><span class="muted small">Đối với tham số cần xem lại</span></span></label></div><label class="ex-checkbox"><input id="extraction-rerun" type="checkbox" ${o.chay_lai ? "checked" : ""}><span>Trích lại kể cả hợp đồng đã trích <span class="muted small">(mặc định dùng lại kết quả nếu file không đổi)</span></span></label><div class="ex-cloud-box"><div class="ex-cloud-heading"><strong class="small">Kiểm tra chéo trên cloud</strong><label class="ex-checkbox"><input id="extraction-cloud" type="checkbox" ${o.cloud ? "checked" : ""}>${o.cloud ? "Đã bật" : "Đang tắt"}</label></div><p class="ex-cloud-help">${o.cloud ? "Gửi ô vàng mức 2–3, tham số khó (Luôn hỏi Claude) và mẫu ngẫu nhiên — chỉ các Khoản liên quan, đã che định danh. Có nhật ký gửi." : "Trích tham số tại máy AI nội bộ. Bật khi cần thêm một nguồn kiểm tra."}</p>${o.cloud ? `<div class="ex-cloud-settings"><label class="field">Nhà cung cấp<select id="extraction-provider"><option value="anthropic" ${o.ncc === "anthropic" ? "selected" : ""}>Anthropic (Claude)</option><option value="openai" ${o.ncc === "openai" ? "selected" : ""}>OpenAI</option></select></label><label class="field">Kiểm tra ngẫu nhiên (%)<input id="extraction-sample" type="number" min="0" max="100" value="${E(o.tyLe)}"></label></div>${coKhoa ? "" : `<div class="notice notice-warning small" style="margin-top:10px">Chưa có API key cho nhà cung cấp này. <button class="link-btn" data-route="settings">Nhập key trong Cài đặt</button></div>`}` : ""}</div><div style="margin-top:16px;display:flex;justify-content:space-between;align-items:center;gap:12px"><span class="muted small">${running ? "Lượt mới sẽ chờ lượt đang chạy xong" : "Cấu hình áp dụng cho lượt chạy tiếp theo"}</span>${button("extraction-start", icon("play") + " Bắt đầu trích", "btn-primary", s.draftFiles.length && !s.uploading ? "" : "disabled")}</div></div></div>`;
}

function progressPanel(s) {
  const r = s.run;
  if (!r)
    return `<div id="ex-progress" class="panel"><div class="panel-head"><h3>Tiến độ trích tham số</h3></div><div class="panel-body empty-state" style="min-height:450px">${icon("file")}<h3>Thêm hợp đồng để bắt đầu</h3><p>Chọn file Word hoặc PDF có chữ. Hệ thống hiển thị từng bước, thời gian và nhật ký tại đây.</p></div></div>`;
  const hd = (r.hd || []).find((h) => h.tt === "Đang chạy") || [...(r.hd || [])].reverse().find((h) => h.tt !== "Chờ") || (r.hd || [])[0] || {};
  const steps = r.buoc_ten || [];
  const tc = r.tuy_chon || {};
  const running = ["dang_chay", "cho"].includes(r.tt);
  const done = r.tt === "xong";
  const now = Date.now() / 1000;
  const logs = (r.log || [])
    .map(([t, m]) => {
      const k = /LỖI|lỗi|KHÔNG|Không kết nối/.test(m) ? "err" : /cần|vàng|thử lại|không xác nhận/i.test(m) ? "warn" : "";
      return `<div class="ex-log-row ${k}"><time>${E(t)}</time><span>${E(m)}</span></div>`;
    })
    .join("");
  if (r.tt === "loi")
    return `<div id="ex-progress" class="panel"><div class="panel-head"><h3>Tiến độ trích tham số</h3>${badge("Lỗi", "danger")}</div><div class="panel-body"><div class="ex-job-title"><div class="ex-job-icon">${icon("file")}</div><div><h3>${E(hd.file || "")}</h3><p class="muted small">Lượt ${E(s.luot)} · ${E(r.model || "")}</p></div></div><div class="notice notice-danger"><strong>Lượt trích dừng do lỗi</strong><p>${E(r.thong_bao || "")}</p></div><div style="display:flex;gap:8px;margin-top:18px">${button("extraction-retry", icon("play") + " Chạy lại", "btn-primary")}<button class="btn" data-route="settings">Mở cài đặt máy AI</button></div><div class="ex-log-label">Nhật ký gần nhất</div><div class="ex-log">${logs}</div></div></div>`;
  const pct = running ? Math.round((hd.pct || 0) * 100) : done ? 100 : Math.round((r.pct || 0) * 100);
  const el = hd.bat_dau ? (hd.tt === "Đang chạy" ? now - hd.bat_dau : hd.thoi_gian || 0) : 0;
  const eta = running && hd.pct > 0.08 ? Math.round((el * (1 - hd.pct)) / hd.pct) : null;
  const phase = done ? steps.length : hd.buoc ?? -1;
  const nHd = (r.hd || []).length,
    nXong = (r.hd || []).filter((h) => !["Chờ", "Đang chạy"].includes(h.tt)).length;
  const vang = (r.hd || []).reduce((a, h) => a + (h.so_vang || 0), 0);
  const title = done ? "Đã hoàn tất trích tham số" : r.tt === "da_dung" ? "Lượt trích đã dừng" : r.tt === "cho" ? "Đang chờ máy AI" : "Hợp đồng đang trích";
  const st = done ? (vang ? ["Xong có ô vàng", "warning"] : ["Xong", "success"]) : r.tt === "da_dung" ? ["Đã dừng", "neutral"] : ["Đang chạy", "info"];
  const words = hd.canh_bao?.length ? ` · ${hd.canh_bao.length} cảnh báo đầu vào` : "";
  return `<div id="ex-progress" class="panel"><div class="panel-head"><h3>${title}</h3>${badge(...st)}</div><div class="panel-body"><div class="ex-job-title"><div class="ex-job-icon">${icon("file")}</div><div><h3>${E(hd.file || "")}</h3><p class="muted small">${E(r.model || "")} · Hợp đồng ${Math.min(nXong + (running ? 1 : 0), nHd)}/${nHd} · Lượt ${E(s.luot)}${words}</p></div></div><div class="ex-progress-top"><span class="small">${done ? `${nHd} hợp đồng · ${vang} ô cần xem` : r.tt === "da_dung" ? "Lượt trích đã dừng — kết quả đã xong được giữ lại" : E(hd.mo_ta || steps[hd.buoc] || "Đang chuẩn bị…")}</span><strong class="ex-progress-percent">${pct}<span style="font-size:16px;margin-left:2px">%</span></strong></div><div class="ex-progress-track" role="progressbar" aria-label="Tiến độ trích tham số" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><span style="width:${pct}%"></span></div><div class="ex-job-times"><span>Đã chạy <strong>${clock(el)}</strong></span><span>${done ? "Hoàn tất" : eta != null ? "Ước tính còn lại" : ""} <strong>${eta != null ? "~ " + clock(eta) : ""}</strong></span></div><ol class="ex-timeline">${steps
    .map((label, i) => {
      const skipped = (i === 5 && tc.ra_lai === false) || (i === 7 && !tc.cloud);
      const status = skipped ? "skipped" : i < phase ? "complete" : i === phase ? "current" : "";
      return `<li class="ex-step ${status}"><span class="ex-step-dot">${skipped ? "—" : i < phase ? icon("check") : i + 1}</span><div><div class="ex-step-title">${E(label)}</div><small>${skipped ? "Không áp dụng" : i < phase ? "Đã hoàn tất" : i === phase ? (running ? "Đang thực hiện" : "Dừng ở bước này") : "Chờ thực hiện"}</small></div></li>`;
    })
    .join("")}</ol>${hd.canh_bao?.length ? `<div class="notice notice-warning small">${hd.canh_bao.map(E).join("<br>")}</div>` : ""}<div class="ex-log-label">Nhật ký xử lý <span>Giờ máy tính · không ghi nội dung hợp đồng</span></div><div class="ex-log" aria-label="Nhật ký xử lý">${logs}</div><div class="ex-job-footer"><span class="muted small">${done ? Object.entries(r.tai || {}).map(([k, u]) => `<a href="${u}">${{ tong_hop_xlsx: "Tổng hợp Excel", tong_hop_json: "Tổng hợp JSON", nhat_ky: "Nhật ký", danh_muc_hd: "Danh mục HĐ" }[k] || k}</a>`).join(" · ") : running ? "Có thể mở màn hình khác khi việc đang chạy" : ""}</span>${done ? button("extraction-results", "Mở kết quả " + icon("chevron-right"), "btn-primary", `data-ten="${E((r.hd.find((h) => h.ten && h.so_ok != null) || {}).ten || "")}"`) : r.tt === "da_dung" ? button("extraction-retry", icon("play") + " Chạy lại", "btn-primary") : button("extraction-stop", icon("stop") + " Dừng", "btn-danger")}</div></div></div>`;
}

function cloudTomTat(k) {
  const c = k.tom_tat?.cloud;
  if (!c || !c.bat) return "";
  const ten = c.nha_cung_cap === "openai" ? "OpenAI" : "Claude";
  if (c.loi && !c.so_o_gui)
    return `<div class="notice notice-danger small" style="margin-bottom:12px">${icon("alert")} <strong>Kiểm tra chéo ${ten} không chạy được:</strong> ${E(c.loi)} — vào Cài đặt bấm "Thử kết nối ${ten}".</div>`;
  const ds = [`gửi ${c.so_o_gui} ô`, `xác nhận ${c.xac_nhan}`, `sửa ${c.sua}`];
  if (c.cung_khong_quy_dinh) ds.push(`cùng "không quy định" ${c.cung_khong_quy_dinh}`);
  ds.push(`không xác nhận được ${c.khong_xac_nhan}`);
  if ((c.khong_gui || []).length) ds.push(`không gửi ${c.khong_gui.length}`);
  return `<div class="notice notice-${c.loi ? "warning" : "info"} small" style="margin-bottom:12px">${icon("cloud")} <strong>Kiểm tra chéo ${ten}${c.model ? ` (${E(c.model)})` : ""}:</strong> ${E(ds.join(" · "))}${c.token_vao ? ` · ${Number(c.token_vao).toLocaleString("vi-VN")} / ${Number(c.token_ra).toLocaleString("vi-VN")} token` : ""}.${c.loi ? ` Lỗi giữa chừng: ${E(c.loi)}` : ""} Xem cột Nguồn; bấm một tham số để xem câu trả lời của ${ten}.</div>`;
}

function queueView(s) {
  return `<div class="ex-queue-layout"><div><div class="panel"><div class="panel-head"><h3>Hàng đợi hợp đồng</h3>${badge(`${(s.run?.hd || []).length + s.draftFiles.length} file`, "neutral")}</div><div class="panel-body ex-upload">${upload("extraction-files", ".doc,.docx,.pdf", true, "Word hoặc PDF (PDF scan tự OCR bằng ABBYY trên máy) · chọn nhiều file trong cùng một lượt")}<div class="ex-file-tools"><span class="muted small">${s.uploading ? `Đang tải lên ${s.uploading} file…` : "Thứ tự xử lý từ trên xuống"}</span><span class="muted small">File gốc được giữ nguyên</span></div></div>${queueTable(s)}</div>${options(s)}</div>${progressPanel(s)}</div>`;
}

// ------------------------------------------------------------------ bảng kết quả
function rowsOf(s) {
  return s.result?.kq?.bang || [];
}
function filteredRows(s) {
  const q = s.query.toLocaleLowerCase("vi");
  let rows = rowsOf(s).filter(
    (r) =>
      (s.group === "all" || r.nhom === s.group) &&
      (!s.yellowOnly || r.vang) &&
      (!q || `${r.ma} ${r.tham_so} ${r.gia_tri}`.toLocaleLowerCase("vi").includes(q)),
  );
  if (s.sort === "importance") rows = rows.slice().sort((a, b) => b.muc - a.muc);
  if (s.sort === "warning") rows = rows.slice().sort((a, b) => Number(b.can_xem) - Number(a.can_xem) || Number(b.vang) - Number(a.vang));
  return rows;
}
function reason(r) {
  return String(r.kiem_tra || "").replace(/^KIỂM TRA: /, "");
}
function statusBadge(r) {
  if (r.da_sua) return badge(r.da_xac_nhan ? "Đã sửa tay · đã xác nhận" : "Đã sửa tay", r.da_xac_nhan ? "success" : "info");
  return badge(r.da_xac_nhan ? "Đã xác nhận" : "Chưa xác nhận", r.da_xac_nhan ? "success" : "neutral");
}
function resultSelect(s) {
  const hds = (s.run?.hd || []).filter((h) => h.ten && h.so_ok != null);
  if (hds.length < 2) return "";
  return `<label class="ex-state-switch" for="extraction-result-hd">Hợp đồng <select id="extraction-result-hd">${hds.map((h) => `<option value="${E(h.ten)}" ${s.resultTen === h.ten ? "selected" : ""}>${E(h.file)}</option>`).join("")}</select></label>`;
}
function resultsView(s) {
  if (!s.result)
    return `<div class="panel"><div class="empty-state">${icon("table")}<h3>Chưa có kết quả</h3><p>Chạy trích tham số hoặc mở một hợp đồng đã xong trong hàng đợi.</p>${button("extraction-tab", "Về hàng đợi", "btn-primary", 'data-tab="queue"')}</div></div>`;
  const k = s.result.kq,
    t = k.tom_tat;
  const rows = filteredRows(s);
  const all = rowsOf(s);
  const confirmed = all.filter((r) => r.da_xac_nhan).length,
    yellow = all.filter((r) => r.can_xem).length,
    selected = s.selected.length,
    n = all.length;
  const groups = [...new Set(all.map((r) => r.nhom))];
  const so = all.find((r) => r.ma === "TC-01")?.gia_tri || "";
  const benB = all.find((r) => r.ma === "TC-07")?.gia_tri || "";
  const gt = all.find((r) => r.ma === "TT-02")?.gia_tri || "";
  const gtNum = Number(String(gt).replace(/[^\d,]/g, "").replace(/,.*$/, "")) || null;
  const daNap = k.csdl?.ma_hd;
  return `<div class="panel"><div class="panel-head ex-results-head"><div><h3 style="margin-bottom:5px">${E(so || k.hop_dong)}${benB ? " · " + E(benB) : ""}</h3><span class="muted small">${E(k.hop_dong)} · ${E(k.model || "chưa chạy AI")} · ${daNap ? `Đã nạp vào CSDL (${E(daNap)})` : "Chưa nạp vào CSDL"}</span></div><div class="ex-results-actions">${k.tai?.excel ? `<a class="btn" href="${k.tai.excel}">${icon("download")} Tải Excel</a>` : ""}${k.tai?.json ? `<a class="btn" href="${k.tai.json}">Tải JSON</a>` : ""}${k.tai?.gui_ra_ngoai ? `<a class="btn btn-ghost" href="${k.tai.gui_ra_ngoai}?xem=1" target="_blank">Nhật ký gửi cloud</a>` : ""}${button("extraction-import", icon("check") + " " + (daNap ? "Đã nạp vào CSDL" : "Nạp vào CSDL"), "btn-primary", daNap || k.che_do !== "AI" ? "disabled" : "")}</div></div><div class="panel-body" style="padding-bottom:0"><div class="ex-results-summary"><div><strong>${gtNum ? money(gtNum) : E(gt || "—")}</strong><span>Giá trị hợp đồng · đồng</span></div><div><strong>${n}</strong><span>Tham số đã trích · ${t.so_ok} tự kiểm OK</span></div><div><strong style="color:#976919">${yellow}</strong><span>Ô vàng chưa xác nhận</span></div><div><strong>${confirmed}<span style="display:inline;font-size:14px;margin-left:3px">/${n}</span></strong><span>Đã xác nhận</span></div></div><div class="ex-results-toolbar"><label class="field"><input id="extraction-search" type="search" value="${E(s.query)}" placeholder="Tìm mã hoặc tham số…" aria-label="Tìm tham số"></label><label class="field"><select id="extraction-group" aria-label="Lọc theo nhóm"><option value="all">Tất cả nhóm</option>${groups.map((g) => `<option ${s.group === g ? "selected" : ""}>${E(g)}</option>`).join("")}</select></label><label class="ex-checkbox"><input id="extraction-yellow" type="checkbox" ${s.yellowOnly ? "checked" : ""}>Chỉ ô vàng (${all.filter((r) => r.vang).length})</label>${resultSelect(s)}<label class="field" style="margin-left:auto;min-width:160px"><select id="extraction-sort" aria-label="Sắp xếp tham số"><option value="code" ${s.sort === "code" ? "selected" : ""}>Theo mã tham số</option><option value="importance" ${s.sort === "importance" ? "selected" : ""}>Quan trọng cao trước</option><option value="warning" ${s.sort === "warning" ? "selected" : ""}>Ô vàng trước</option></select></label></div>${cloudTomTat(k)}${(k.phieu_kiem_tra?.warnings || []).length ? `<div class="notice notice-info small" style="margin-bottom:12px">${k.phieu_kiem_tra.warnings.map(E).join("<br>")}</div>` : ""}${confirmed !== n ? `<div class="notice notice-warning small" style="margin-bottom:16px">Còn ${n - confirmed} tham số chưa xác nhận (${yellow} ô vàng). Đọc trích dẫn và xác nhận trước khi nạp; sửa tay giữ nguyên giá trị máy trích ban đầu.</div>` : `<div class="notice notice-success small" style="margin-bottom:16px">${daNap ? `Đã nạp ${E(daNap)} vào cơ sở dữ liệu.` : `Đã xác nhận đủ ${n} tham số. Có thể nạp hợp đồng vào cơ sở dữ liệu.`}</div>`}</div><div class="table-wrap" aria-label="Bảng tham số; cuộn ngang để xem nguồn và trạng thái" tabindex="0"><table class="data-table ex-table"><colgroup><col style="width:60px"><col style="width:85px"><col style="width:150px"><col style="width:210px"><col style="width:290px"><col style="width:75px"><col style="width:160px"><col style="width:320px"><col style="width:270px"><col style="width:100px"><col style="width:150px"><col style="width:165px"><col style="width:120px"></colgroup><thead><tr><th><label class="checkbox-target"><input id="extraction-select-all" type="checkbox" aria-label="Chọn tất cả tham số đang hiển thị" ${rows.length && rows.every((r) => s.selected.includes(r.ma)) ? "checked" : ""}></label></th><th>Mã</th><th>Nhóm</th><th>Tham số</th><th>Giá trị · sửa trong ô</th><th>Đơn vị</th><th>Điều khoản</th><th>Trích dẫn nguyên văn</th><th>Kiểm tra</th><th>Quan trọng</th><th>Nguồn</th><th>Trạng thái</th><th>Xác nhận</th></tr></thead><tbody>${
    rows
      .map(
        (r) =>
          `<tr class="${r.can_xem ? "ex-row-yellow" : ""}"><td><label class="checkbox-target"><input type="checkbox" data-extraction-select="${r.ma}" aria-label="Chọn ${r.ma}" ${s.selected.includes(r.ma) ? "checked" : ""}></label></td><td><button class="ex-code-btn" data-action="extraction-detail" data-code="${r.ma}" title="Đọc trích dẫn và lịch sử">${r.ma}</button></td><td>${E(r.nhom)}</td><td><strong>${E(r.tham_so)}</strong></td><td><input class="ex-value-input" data-extraction-value="${r.ma}" value="${E(r.gia_tri)}" aria-label="Giá trị ${r.ma} ${E(r.tham_so)}">${r.da_sua ? `<span class="small muted">Đã sửa · máy trích: ${E(r.gia_tri_ai)}</span>` : ""}</td><td>${E(r.don_vi) || "—"}</td><td>${E(r.dieu_khoan) || "—"}</td><td><div class="ex-quote">${r.trich_dan ? `“${E(r.trich_dan)}”` : '<span class="muted">Không có trích dẫn</span>'}</div><button class="ex-code-btn small" data-action="extraction-detail" data-code="${r.ma}" style="min-height:40px;font-size:11px;font-weight:500">Đọc đầy đủ</button></td><td>${badge(r.vang ? "Vàng · Cần xem" : "OK", r.vang ? "warning" : "success")}${r.vang ? `<span class="ex-warning">${E(reason(r))}</span>` : isOk(r.kiem_tra) && r.kiem_tra !== "OK" ? `<span class="small muted" style="display:block;margin-top:5px">${E(r.kiem_tra)}</span>` : ""}</td><td>${badge(`${r.muc} · ${MUC[r.muc] || ""}`, r.muc === 3 ? "info" : "neutral")}</td><td>${E(r.nguon)}</td><td>${statusBadge(r)}</td><td>${r.da_xac_nhan ? '<span class="small" style="color:#247149">Đã xác nhận</span>' : button("extraction-confirm", "Xác nhận", "ex-confirm-one", `data-code="${r.ma}"`)}</td></tr>`,
      )
      .join("") || '<tr><td colspan="13"><div class="empty-state">Không có tham số phù hợp bộ lọc.</div></td></tr>'
  }</tbody></table></div><div class="ex-table-footer"><div class="ex-batch-selection">${selected ? `Đã chọn ${selected} tham số` : `${rows.length} / ${n} tham số`}${button("extraction-confirm-batch", "Xác nhận đã chọn", "btn-primary", selected ? "" : "disabled")}${selected ? button("extraction-clear-selection", "Bỏ chọn", "btn-ghost") : ""}</div><p>Cuộn ngang để xem trích dẫn, mức quan trọng, nguồn và trạng thái.</p></div></div>`;
}

export function renderExtraction(ctx) {
  const s = S(ctx);
  s.aiModels = ctx.state.ai?.models || [];
  if (!s.loaded) return `${css()}<section class="extraction">${header("Trích tham số hợp đồng", "Từ văn bản hợp đồng đến tham số có trích dẫn để review.")}<div class="panel"><div class="panel-body muted">Đang tải…</div></div></section>`;
  const yellow = rowsOf(s).filter((r) => r.can_xem).length;
  const runs = s.runs || [];
  return `${css()}<section class="extraction">${header("Trích tham số hợp đồng", "Từ văn bản hợp đồng đến tham số có trích dẫn để review.")}
    <div class="ex-topbar"><div class="tabs"><button class="tab ${s.tab === "queue" ? "active" : ""}" data-action="extraction-tab" data-tab="queue">Hàng đợi & tiến độ ${badge((s.run?.hd || []).length + s.draftFiles.length, "neutral")}</button><button class="tab ${s.tab === "results" ? "active" : ""}" data-action="extraction-tab" data-tab="results">Kết quả tham số ${s.result ? badge(`${yellow} cần xem`, yellow ? "warning" : "success") : ""}</button></div><label class="ex-state-switch" for="extraction-history">Lượt đã chạy <select id="extraction-history" data-loaded="${runs.length ? 1 : 0}"><option value="">${s.luot ? `Lượt ${E(s.luot)}` : "Chọn lượt…"}</option>${runs.map((l) => `<option value="${E(l.luot)}">${E(l.luot)} · ${l.so_hd} HĐ · ${E(l.model || "")} · ${{ xong: "Xong", loi: "Lỗi", da_dung: "Đã dừng", dang_chay: "Đang chạy", cho: "Chờ" }[l.tt] || E(l.tt || "")}</option>`).join("")}</select></label></div>${s.tab === "queue" ? queueView(s) : resultsView(s)}</section>`;
}

// ------------------------------------------------------------------ chi tiết 1 tham số
function showDetail(row, s, ctx) {
  s.detailCode = row.ma;
  s.detailDraft = row.gia_tri;
  s.detailNote = row.ghi_chu_soat || "";
  const k = s.result.kq;
  ctx.openDrawer({
    title: `${row.ma} · ${row.tham_so}`,
    body: `<div class="ex-detail"><div class="ex-detail-meta">${badge(row.nhom, "neutral")}${badge(`${row.muc} · ${MUC[row.muc] || ""}`, "info")}${badge(row.nguon, "neutral")}${statusBadge(row)}</div>${row.vang ? `<div class="notice notice-warning" style="margin-bottom:20px"><strong>Cần xem lại</strong><p>${E(reason(row))}</p></div>` : `<div class="notice notice-success" style="margin-bottom:20px"><strong>${E(row.kiem_tra)}</strong><p>Trích dẫn có nguyên văn trong hợp đồng; số liệu nằm trong trích dẫn.</p></div>`}<p class="muted small">Mô tả cho AI: ${E(row.mo_ta)}</p><p class="muted small">Nguồn: ${E(k.hop_dong)}${row.vi_tri_do_duoc ? ` · vị trí dò được: ${E(row.vi_tri_do_duoc)}` : ""}</p><h4>${E(row.dieu_khoan || "Chưa xác định điều khoản")}</h4><blockquote class="ex-citation">${row.trich_dan ? `“${E(row.trich_dan)}”` : "Không có trích dẫn."}</blockquote>${row.ghi_chu ? `<p class="small muted">Ghi chú máy: ${E(row.ghi_chu)}</p>` : ""}${row.cloud ? `<div class="notice notice-info small">Cloud trả lời: ${E(row.cloud.gia_tri)} — “${E(row.cloud.trich_dan)}” (${E(row.cloud.kiem_tra)})</div>` : ""}<label class="field">Giá trị review ${row.don_vi ? `(${E(row.don_vi)})` : ""}<input id="extraction-detail-value" value="${E(row.gia_tri)}"></label><div class="ex-original"><span class="muted small">Giá trị máy trích ban đầu · luôn được giữ lại</span><p style="margin:5px 0 0;font-weight:600">${E(row.gia_tri_ai)} ${E(row.don_vi)}</p>${row.dap_an ? `<p class="small muted" style="margin:6px 0 0">Đáp án: ${E(row.dap_an)} · ${E(row.so_voi_dap_an)}</p>` : ""}</div><label class="field">Ghi chú người review<textarea id="extraction-detail-note" placeholder="Căn cứ sửa hoặc kết luận sau khi đối chiếu…">${E(row.ghi_chu_soat || "")}</textarea></label><div class="ex-detail-footer">${button("extraction-save-detail", "Lưu giá trị review", "btn-primary", `data-code="${row.ma}"`)}${button("extraction-confirm", "Xác nhận tham số", "", `data-code="${row.ma}" ${row.da_xac_nhan ? "disabled" : ""}`)}</div><p class="muted small" style="margin-top:18px">Sửa giá trị sẽ bỏ trạng thái xác nhận để Anh kiểm tra lại.</p>${(row.lich_su || []).length ? `<h4 style="margin-top:22px">Lịch sử review</h4>${row.lich_su.map((h) => `<div class="history-item"><strong>${E(h.thao_tac)}</strong> · ${E((h.luc || "").replace("T", " "))}${h.nguoi ? ` · ${E(h.nguoi)}` : ""}<br>${h.cu ? `${E(h.cu)} → ` : ""}${E(h.moi || "")}</div>`).join("")}` : ""}</div>`,
  });
}

// ------------------------------------------------------------------ thao tác
async function patchRow(ctx, ma, body) {
  const s = S(ctx);
  const { luot, ten } = s.result;
  const d = await api("PATCH", `/api/trich_xuat/${luot}/hd/${encodeURIComponent(ten)}/o/${ma}`, body);
  const rows = s.result.kq.bang;
  const i = rows.findIndex((r) => r.ma === ma);
  if (i >= 0) rows[i] = { ...rows[i], ...d };
  return rows[i];
}
async function startRun(ctx, retry = false) {
  const s = S(ctx);
  const o = s.opts;
  const body = {
    model: o.model,
    ra_lai: !!o.ra_lai,
    chay_lai: !!o.chay_lai,
    cloud: { bat: !!o.cloud, nha_cung_cap: o.ncc, ty_le: Number(o.tyLe) || 0 },
  };
  const d = retry ? await post(`/api/trich_xuat/${s.luot}/chay_lai`, body) : await post(`/api/trich_xuat/${s.draft}/chay`, body);
  s.luot = d.luot;
  s.draft = null;
  s.draftFiles = [];
  s.result = null;
  s.run = null;
  s.tab = "queue";
  ctx.toast(`Đã bắt đầu: ${d.so_hop_dong} hợp đồng, ${d.so_tham_so} tham số${d.cloud ? ", có kiểm tra chéo cloud" : ""}.`);
  await refreshRun(ctx, false);
  ctx.render();
  ctx.refreshJobs();
}
async function uploadFiles(ctx, files) {
  const s = S(ctx);
  const ok = files.filter((f) => /\.(docx?|pdf|tsv)$/i.test(f.name));
  if (files.length !== ok.length) ctx.toast("Chỉ nhận file .doc, .docx, .pdf (và đáp án .tsv).", "warning");
  if (!ok.length) return;
  try {
    if (!s.draft) s.draft = (await post("/api/trich_xuat")).luot;
    s.uploading = ok.length;
    ctx.render();
    for (const f of ok) {
      const r = await api("POST", `/api/trich_xuat/${s.draft}/tep?ten=${encodeURIComponent(f.name)}`, undefined, f);
      if (!/\.tsv$/i.test(r.ten)) s.draftFiles.push({ ten: r.ten, kich_thuoc: r.kich_thuoc });
      s.uploading--;
    }
    ctx.toast(`Đã thêm ${ok.length} file vào hàng đợi.`);
  } catch (e) {
    ctx.toast(e.message, "danger");
  }
  s.uploading = 0;
  ctx.render();
}

export function handleExtractionAction(action, el, ctx) {
  if (!action.startsWith("extraction-")) return false;
  const s = S(ctx);
  (async () => {
    switch (action) {
      case "extraction-tab":
        s.tab = el.dataset.tab;
        if (s.tab === "results" && !s.result) {
          const first = (s.run?.hd || []).find((h) => h.ten && h.so_ok != null);
          if (first) {
            s.resultTen = first.ten;
            await loadResult(ctx, s.luot, first.ten);
          }
        }
        ctx.render();
        break;
      case "extraction-results": {
        const ten = el.dataset.ten || (s.run?.hd || []).find((h) => h.ten && h.so_ok != null)?.ten;
        if (!ten) break;
        s.resultTen = ten;
        await loadResult(ctx, s.luot, ten);
        s.tab = "results";
        ctx.render();
        break;
      }
      case "extraction-remove":
        await api("DELETE", `/api/trich_xuat/${s.draft}/tep/${encodeURIComponent(el.dataset.ten)}`);
        s.draftFiles = s.draftFiles.filter((f) => f.ten !== el.dataset.ten);
        ctx.render();
        break;
      case "extraction-start":
        if (!s.draftFiles.length) return ctx.toast("Chọn ít nhất một file hợp đồng để bắt đầu.", "warning");
        await startRun(ctx);
        break;
      case "extraction-retry":
        ctx.openModal({
          title: "Chạy lại lượt trích?",
          body: "<p>Tạo lượt mới với cùng các file hợp đồng của lượt này và chạy lại theo thiết lập hiện tại.</p>",
          confirmLabel: "Chạy lại",
          onConfirm: () => startRun(ctx, true).catch((e) => ctx.toast(e.message, "danger")),
        });
        break;
      case "extraction-stop":
        ctx.openModal({
          title: "Dừng trích hợp đồng?",
          body: "<p>Câu hỏi đang chờ máy AI sẽ bị bỏ. Hợp đồng đã xong trong lượt được giữ lại; có thể chạy lại sau.</p>",
          confirmLabel: "Dừng trích",
          danger: true,
          onConfirm: async () => {
            try {
              await post(`/api/trich_xuat/${s.luot}/dung`);
              ctx.toast("Đã gửi lệnh dừng.", "warning");
              refreshRun(ctx);
            } catch (e) {
              ctx.toast(e.message, "danger");
            }
          },
        });
        break;
      case "extraction-detail": {
        const row = rowsOf(s).find((r) => r.ma === el.dataset.code);
        if (row) showDetail(row, s, ctx);
        break;
      }
      case "extraction-save-detail": {
        const ma = el.dataset.code;
        const draft = s.detailDraft ?? "";
        if (!String(draft).trim()) return ctx.toast("Giá trị tham số không được để trống.", "warning");
        const row = await patchRow(ctx, ma, { gia_tri: draft, ghi_chu: s.detailNote || "" });
        ctx.render();
        showDetail(row, s, ctx);
        ctx.toast("Đã lưu giá trị review; giá trị máy trích được giữ lại.");
        break;
      }
      case "extraction-confirm": {
        const row = rowsOf(s).find((r) => r.ma === el.dataset.code);
        if (!row) break;
        if (document.getElementById("extraction-detail-value") && s.detailCode === row.ma && s.detailDraft !== undefined && s.detailDraft !== row.gia_tri)
          return ctx.toast("Lưu giá trị review trước khi xác nhận.", "warning");
        ctx.openModal({
          title: `Xác nhận ${row.ma}?`,
          body: `<p><strong>${E(row.tham_so)}</strong>: ${E(row.gia_tri)} ${E(row.don_vi)}</p>${row.vang ? `<div class="notice notice-warning">${E(reason(row))}</div>` : ""}<p>Anh xác nhận đã kiểm tra giá trị và trích dẫn của tham số này.</p>`,
          confirmLabel: "Xác nhận tham số",
          onConfirm: async () => {
            try {
              await patchRow(ctx, row.ma, { xac_nhan: true });
              ctx.render();
              ctx.toast(`Đã xác nhận ${row.ma}.`);
            } catch (e) {
              ctx.toast(e.message, "danger");
            }
          },
        });
        break;
      }
      case "extraction-confirm-batch": {
        const sel = rowsOf(s).filter((r) => s.selected.includes(r.ma) && !r.da_xac_nhan);
        const warned = sel.filter((r) => r.vang).length;
        ctx.openModal({
          title: `Xác nhận ${sel.length} tham số?`,
          body: `<p>Anh xác nhận đã kiểm tra giá trị và trích dẫn cho ${sel.length} tham số đã chọn.</p>${warned ? `<div class="notice notice-warning">Có ${warned} tham số đang có ô vàng. Xác nhận sau khi đã xem lý do và căn cứ từng tham số.</div>` : ""}<p class="muted small">Kết quả tự kiểm vẫn được giữ lại để truy vết.</p>`,
          confirmLabel: "Xác nhận đã chọn",
          onConfirm: async () => {
            try {
              const { luot, ten } = s.result;
              await post(`/api/trich_xuat/${luot}/hd/${encodeURIComponent(ten)}/xac_nhan`, { ma: sel.map((r) => r.ma) });
              await loadResult(ctx, luot, ten);
              ctx.render();
              ctx.toast(`Đã xác nhận ${sel.length} tham số.`);
            } catch (e) {
              ctx.toast(e.message, "danger");
            }
          },
        });
        break;
      }
      case "extraction-clear-selection":
        s.selected = [];
        ctx.render();
        break;
      case "extraction-import": {
        const { luot, ten } = s.result;
        const nap = async (vanNap) => {
          try {
            const r = await post(`/api/trich_xuat/${luot}/hd/${encodeURIComponent(ten)}/nap_csdl`, { van_nap: vanNap });
            await loadResult(ctx, luot, ten);
            ctx.render();
            ctx.toast(r.moi ? `Đã nạp ${r.ma_hd} vào CSDL.` : `${r.ma_hd}: ${r.trang_thai}${r.lech.length ? ` — lệch ${r.lech.length} tham số` : ""}`, r.lech?.length ? "warning" : "success");
            if (r.lech?.length)
              ctx.openDrawer({
                title: `${r.ma_hd} · khác CSDL`,
                body: `<p class="muted small">Hợp đồng đã có trong CSDL nên không ghi đè. Các tham số khác nhau:</p><table class="data-table"><thead><tr><th>Mã</th><th>Kết quả trích</th><th>CSDL</th></tr></thead><tbody>${r.lech.map((x) => `<tr><td>${E(x.ma)}</td><td>${E(x.ket_qua)}</td><td>${E(x.csdl)}</td></tr>`).join("")}</tbody></table>`,
              });
          } catch (e) {
            if (e.status === 409 && e.chiTiet?.chua_xac_nhan) {
              const c = e.chiTiet;
              ctx.openModal({
                title: "Nạp hợp đồng vào CSDL?",
                body: `<p>Còn <strong>${c.chua_xac_nhan.length}</strong> tham số chưa xác nhận, trong đó <strong>${c.o_vang.length}</strong> ô vàng${c.o_vang.length ? `: ${E(c.o_vang.join(", "))}` : ""}.</p><div class="notice notice-warning">Các ô này được ghi kèm trạng thái "cần xác nhận" và hiện cảnh báo ở Danh mục hợp đồng cho tới khi Anh xác nhận.</div><p class="muted small">Giá trị máy trích, kết quả tự kiểm, nguồn (local/cloud), model và lịch sử sửa được lưu cùng từng tham số để truy ngược khi ký.</p>`,
                confirmLabel: "Nạp hợp đồng",
                onConfirm: () => nap(true),
              });
            } else ctx.toast(e.message, "danger");
          }
        };
        nap(false);
        break;
      }
      default:
        return;
    }
  })().catch((e) => ctx.toast(e.message, "danger"));
  return true;
}

export function handleExtractionChange(el, ctx) {
  const s = S(ctx),
    id = el.id;
  const o = s.opts || {};
  if (id === "extraction-files" || id === "extraction-files-folder") {
    uploadFiles(ctx, [...(el.files || [])]);
    return true;
  }
  if (id === "extraction-history") {
    if (!el.dataset.loaded || el.dataset.loaded === "0") {
      get("/api/trich_xuat?gioi_han=30").then((d) => {
        s.runs = d.ds.filter((l) => l.tt !== "chua_chay");
        ctx.render();
      });
    }
    if (el.value) {
      s.luot = el.value;
      s.result = null;
      s.tab = "queue";
      refreshRun(ctx, false).then(() => ctx.render());
    }
    return true;
  }
  if (id === "extraction-result-hd") {
    s.resultTen = el.value;
    loadResult(ctx, s.luot, el.value).then(() => ctx.render());
    return true;
  }
  if (id === "extraction-cloud") {
    o.cloud = el.checked;
    ctx.render();
    return true;
  }
  if (id === "extraction-reread") return (o.ra_lai = el.checked), true;
  if (id === "extraction-rerun") return (o.chay_lai = el.checked), true;
  if (id === "extraction-model") return (o.model = el.value), true;
  if (id === "extraction-provider") {
    o.ncc = el.value;
    ctx.render();
    return true;
  }
  if (id === "extraction-sample") {
    o.tyLe = Math.max(0, Math.min(100, Number(el.value) || 0));
    el.value = o.tyLe;
    return true;
  }
  if (id === "extraction-search") {
    s.query = el.value;
    ctx.render();
    return true;
  }
  if (id === "extraction-group") return (s.group = el.value), ctx.render(), true;
  if (id === "extraction-yellow") return (s.yellowOnly = el.checked), ctx.render(), true;
  if (id === "extraction-sort") return (s.sort = el.value), ctx.render(), true;
  if (id === "extraction-select-all") {
    const codes = filteredRows(s).map((r) => r.ma);
    s.selected = el.checked ? [...new Set([...s.selected, ...codes])] : s.selected.filter((c) => !codes.includes(c));
    ctx.render();
    return true;
  }
  if (id === "extraction-detail-value") return (s.detailDraft = el.value), true;
  if (id === "extraction-detail-note") return (s.detailNote = el.value), true;
  if (el.dataset.extractionSelect) {
    const code = el.dataset.extractionSelect;
    s.selected = el.checked ? [...new Set([...s.selected, code])] : s.selected.filter((c) => c !== code);
    ctx.render();
    return true;
  }
  if (el.dataset.extractionValue) {
    const row = rowsOf(s).find((r) => r.ma === el.dataset.extractionValue);
    if (row) {
      if (!el.value.trim()) {
        el.value = row.gia_tri;
        ctx.toast("Giá trị tham số không được để trống.", "warning");
        return true;
      }
      patchRow(ctx, row.ma, { gia_tri: el.value })
        .then(() => {
          ctx.render();
          ctx.toast(`Đã lưu ${row.ma}; cần xác nhận lại.`);
        })
        .catch((e) => ctx.toast(e.message, "danger"));
    }
    return true;
  }
  return false;
}
