// phu_luc_ai.js — Phụ lục: trích nội dung thay đổi từ file Word / PDF (PDF scan → OCR ABBYY trên máy),
// quy tắc + Local AI, anh duyệt (xác nhận / sửa / bỏ) rồi nạp CSDL. API: /api/phu_luc_ai (xem API.md).
import { icon, badge, escapeHTML as E, upload } from "./ui.js";
import { api, get, post, upload as uploadFile, money, num, choViec } from "./api.js";

const MUC = { CHẶN: "danger", ĐỎ: "danger", VÀNG: "warning", ĐẠT: "success", "THÔNG TIN": "info" };
const THAO_TAC = { THAY: "info", THEM: "success", BO: "danger", "Không đổi": "neutral" };
const TS = { "Chưa xác nhận": "warning", "Đã xác nhận": "success", "Đã sửa tay": "info" };

function s(ctx) {
  if (!ctx.state.plai) ctx.state.plai = { ds: null, che_do_boq: {}, chon: null, kq: null, loi: "", job: null, tai: null, busy: false };
  return ctx.state.plai;
}
const btn = (action, label, kind = "", attrs = "") => `<button class="btn ${kind}" data-action="${action}" ${attrs}>${label}</button>`;
const gon = (t) =>
  String(t || "")
    .replace(/^Công ty (Cổ phần|CP|TNHH( MTV)?)\s+/i, "")
    .trim();

export async function loadPLAI(ctx) {
  const st = s(ctx);
  try {
    const d = await get("/api/phu_luc_ai");
    st.ds = d.ds;
    st.che_do_boq = d.che_do_boq || {};
    st.loi = "";
    if (st.chon) st.kq = await get(`/api/phu_luc_ai/${st.chon}`);
  } catch (e) {
    st.loi = e.message;
    st.ds = st.ds || [];
  }
}

function style() {
  return `<style>
    .plai .pl-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px 18px}
    .plai .pl-grid .span-3{grid-column:1/-1}
    .plai .quote{display:block;font-size:11px;color:#5f6f84;margin-top:4px;line-height:1.5;font-style:italic}
    .plai .src{font-size:10.5px;color:#7a889b}
    .plai .bo td{opacity:.45;text-decoration:line-through}
    .plai .bo td:last-child{opacity:1;text-decoration:none}
    .plai .data-table td{vertical-align:top}
    .plai .ts-input{min-width:150px}
    .plai .sec-title{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:26px 0 12px}
    .plai .sec-title h3{font-size:14px;margin:0}
    .plai .arrow{color:#8a97a8;text-align:center}
    @media(max-width:1000px){.plai .pl-grid{grid-template-columns:1fr 1fr}}
  </style>`;
}

function dem(kt, m) {
  return (kt || []).filter((x) => x[1] === m).length;
}
function bangDs(st, dsHd) {
  if (!st.ds) return `<div class="panel-body muted small">Đang tải…</div>`;
  if (!st.ds.length) return "";
  const soHd = (ma) => (dsHd || []).find((h) => h.ma_hd === ma)?.so_hd || ma || "";
  return `<div class="table-wrap"><table class="data-table"><thead><tr><th>File phụ lục</th><th>Hợp đồng</th><th>Phụ lục</th><th>Thay đổi</th><th>Kiểm tra</th><th>Trạng thái</th><th></th></tr></thead><tbody>${st.ds
    .map(
      (r) =>
        `<tr><td><strong class="small" style="overflow-wrap:anywhere">${E(r.ten)}</strong>${r.ocr ? `<span class="subline">OCR ABBYY</span>` : ""}</td><td>${r.ma_hd ? E(soHd(r.ma_hd) || r.so_hd) : badge("Chưa xác định", "warning")}</td><td>${E(r.so_pl || "—")}<span class="subline">${E(r.ngay_ky || "")}</span></td><td class="small">${r.so_tham_so} tham số · ${r.so_boq} dòng BOQ${r.so_khac ? ` · ${r.so_khac} khác` : ""}</td><td>${r.chan ? badge(`${r.chan} CHẶN`, "danger") : ""}${r.do ? badge(`${r.do} ĐỎ`, "danger") : ""}${r.vang ? badge(`${r.vang} VÀNG`, "warning") : ""}${!r.chan && !r.do && !r.vang ? badge("Không cờ", "success") : ""}</td><td>${r.nap ? badge(`Đã nạp ${r.nap.so_pl}`, "success") : r.chua_xac_nhan ? badge(`${r.chua_xac_nhan} chờ xác nhận`, "warning") : badge("Chờ duyệt", "info")}</td><td>${btn("plai-mo", "Mở", "btn-ghost", `data-id="${E(r.id)}"`)}</td></tr>`,
    )
    .join("")}</tbody></table></div>`;
}

function truong(kq, k, nhan, opts = {}) {
  const v = kq.info?.[k];
  const tr = kq.trich?.[k];
  const ng = kq.nguon?.[k];
  const khoa = !!kq.nap;
  const val = opts.tien ? (v === null || v === undefined || v === "" ? "" : money(v)) : v ?? "";
  const ctrl = opts.chon
    ? `<select data-plai-info="${k}" ${khoa ? "disabled" : ""}>${opts.chon.map((o) => `<option ${o === v ? "selected" : ""}>${E(o)}</option>`).join("")}</select>`
    : opts.dai
      ? `<textarea data-plai-info="${k}" rows="2" ${khoa ? "disabled" : ""}>${E(val)}</textarea>`
      : `<input data-plai-info="${k}" value="${E(val)}" placeholder="${E(opts.goi_y || "")}" ${khoa ? "disabled" : ""}>`;
  return `<label class="field ${opts.rong ? "span-3" : ""}"><span>${E(nhan)}</span>${ctrl}<small class="src">${ng ? `Nguồn: ${E(ng)}` : v === undefined || v === null || v === "" ? "Không thấy trong phụ lục" : ""}</small>${tr && tr !== v ? `<span class="quote">“${E(String(tr).slice(0, 220))}”</span>` : ""}</label>`;
}

function chiTiet(ctx, st, dsHd) {
  const kq = st.kq;
  if (!kq) return `<div class="panel-body muted small">Đang tải…</div>`;
  const khoa = !!kq.nap;
  const kt = kq.kiem_tra || [];
  const chan = dem(kt, "CHẶN");
  const cho = (kq.tham_so || []).filter((r) => !r.bo && r.trang_thai === "Chưa xác nhận");
  const tinh = kq.info_tinh || {};
  const optHd = `<option value="">— Chọn hợp đồng —</option>${(dsHd || [])
    .map((h) => `<option value="${E(h.ma_hd)}" ${h.ma_hd === kq.ma_hd ? "selected" : ""}>${E(h.so_hd)}${h.ben_b ? " · " + E(gon(h.ben_b).slice(0, 40)) : ""}</option>`)
    .join("")}`;
  // 1. thông tin chung
  const info = `<div class="pl-grid"><label class="field span-3"><span>Hợp đồng của phụ lục</span><select data-plai-hd ${khoa ? "disabled" : ""}>${optHd}</select><small class="src">${kq.nhan_hd ? `Nhận theo ${E(kq.nhan_hd)}` : "Không tự nhận được — chọn hợp đồng"}</small></label>${truong(kq, "so_pl", "Số phụ lục", { goi_y: "PL01" })}${truong(kq, "ngay_ky", "Ngày ký", { goi_y: "dd/mm/yyyy" })}${truong(kq, "ngay_hieu_luc", "Ngày hiệu lực", { goi_y: "Trống = ngày ký" })}${truong(kq, "trang_thai", "Trạng thái", { chon: ["Đã ký", "Dự thảo"] })}${truong(kq, "gt_hd_sau_pl", "GT HĐ sau phụ lục (sau VAT)", { tien: true })}${truong(kq, "gt_sau_vat", "Giá trị tăng (+) / giảm (−) sau VAT", { tien: true, goi_y: tinh.gt_sau_vat != null ? `Tự tính: ${tinh.gt_sau_vat > 0 ? "+" : ""}${money(tinh.gt_sau_vat)}` : "" })}${truong(kq, "noi_dung", "Nội dung tóm tắt", { dai: true, rong: true })}${truong(kq, "can_cu", "Căn cứ (điều khoản HĐ / lý do)", { dai: true, rong: true })}</div>${kq.gt_truoc_pl != null ? `<p class="small muted" style="margin:10px 0 0">GT HĐ hiệu lực trước phụ lục (CSDL): <strong>${money(kq.gt_truoc_pl)}</strong> đồng</p>` : ""}`;
  // 2. tham số
  const rows = (kq.tham_so || [])
    .map((r) => {
      const ma = E(r.ma_ts);
      return `<tr class="${r.bo ? "bo" : ""}"><td class="check-code">${ma}</td><td>${E(r.ten)}<span class="subline">${E(r.nguon || "")}${r.dieu ? " · " + E(r.dieu) : ""}</span></td><td class="small">${E(r.cu ?? "—")}</td><td><input class="ts-input table-control" data-plai-moi="${ma}" value="${E(r.moi || "")}" ${khoa || r.bo ? "disabled" : ""}></td><td class="small" style="max-width:320px">${r.trich ? `“${E(r.trich)}”` : '<span class="muted">—</span>'}${r.kiem_tra_trich && r.trang_thai === "Chưa xác nhận" ? `<span class="subline danger-text">${E(r.kiem_tra_trich)}</span>` : ""}${r.ghi_chu ? `<span class="subline">${E(r.ghi_chu)}</span>` : ""}</td><td>${r.bo ? badge("Đã bỏ", "neutral") : badge(r.trang_thai, TS[r.trang_thai] || "neutral")}</td><td style="white-space:nowrap">${
        khoa
          ? ""
          : r.bo
            ? btn("plai-ts", "Khôi phục", "btn-ghost", `data-ma="${ma}" data-op="khoi_phuc"`)
            : `${r.trang_thai === "Chưa xác nhận" ? btn("plai-ts", `${icon("check", 14)} Xác nhận`, "", `data-ma="${ma}" data-op="xac_nhan"`) : ""}${btn("plai-ts", "Bỏ", "btn-ghost", `data-ma="${ma}" data-op="bo"`)}`
      }</td></tr>`;
    })
    .join("");
  const thamSo = `${kq.loi_ai ? `<div class="notice notice-warning">${icon("alert")} ${E(kq.loi_ai)}</div>` : ""}${
    rows
      ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Mã</th><th>Tham số</th><th>Trước phụ lục (CSDL)</th><th>Sau phụ lục</th><th>Trích dẫn nguyên văn</th><th>Trạng thái</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`
      : `<p class="small muted">${kq.loi_ai ? "" : "Local AI không thấy tham số nào bị sửa (ngoài giá trị hợp đồng và BOQ)."}</p>`
  }<p class="inline-help">Giá trị cũ lấy từ CSDL tại ngày ký phụ lục. Giá trị hợp đồng (TT-02) không ghi ở đây: máy tự tính từ giá trị tăng/giảm khi nạp.</p>`;
  // 3. khác
  const khac = (kq.khac || []).length
    ? `<ul class="small" style="margin:0;padding-left:18px;line-height:1.8">${kq.khac.map((k) => `<li>${E(k.noi_dung)}${k.dieu ? ` <span class="muted">(${E(k.dieu)})</span>` : ""}${k.trich ? `<span class="quote">“${E(k.trich)}”</span>` : ""}</li>`).join("")}</ul><p class="inline-help">Không thuộc tham số nào: được ghi vào nội dung phụ lục khi nạp.</p>`
    : `<p class="small muted">Không có.</p>`;
  // 4. BOQ
  const bq = kq.boq || {};
  const b = bq.bang;
  const ss = bq.so_sanh || [];
  const tong = b?.tong || {};
  const boq = !b
    ? `<p class="small muted">Phụ lục không có bảng khối lượng / đơn giá.</p>`
    : `<div class="toolbar" style="margin-bottom:12px"><label class="field" style="min-width:280px"><span>Cách áp vào BOQ</span><select data-plai-boq ${khoa ? "disabled" : ""}>${Object.entries(st.che_do_boq || {})
        .map(([k, t]) => `<option value="${k}" ${bq.che_do === k ? "selected" : ""}>${E(t)}</option>`)
        .join("")}</select></label><span class="small muted">Bảng ${E(b.bang)} · ${b.items.length} dòng · ${b.loai === "doi_chieu" ? "bảng cũ → mới" : "bảng sau phụ lục"}${tong.sau_vat != null ? ` · Tổng sau VAT ghi trên bảng ${money(tong.sau_vat)}` : ""}</span></div>${
        bq.thoi_han ? `<div class="notice notice-warning">${icon("calendar")} Đơn giá chỉ áp cho KL thực hiện từ <strong>${E(bq.thoi_han.tu)}</strong> đến <strong>${E(bq.thoi_han.den)}</strong>. Phần mềm chưa áp đơn giá theo khoảng thời gian — nên để "Không đổi BOQ (chỉ ghi nhận)".</div>` : ""
      }<div class="table-wrap"><table class="data-table"><thead><tr><th>Dòng PL</th><th>Tên trên phụ lục</th><th>ĐVT</th><th class="numeric">KL PL</th><th class="numeric">ĐG PL</th><th></th><th>Mã HM</th><th>Hạng mục CSDL</th><th class="numeric">KL CSDL</th><th class="numeric">ĐG CSDL</th><th>Thao tác</th></tr></thead><tbody>${(ss.length ? ss : b.items.map((it) => ({ ...it, thao_tac: "" })))
        .map(
          (r) =>
            `<tr><td class="muted small">${E(r.dong ?? "")}</td><td class="small">${E(r.ten || "")}${r.dg_cu != null ? `<span class="subline">ĐG cũ ghi trên PL ${money(r.dg_cu)}</span>` : ""}</td><td>${E(r.dvt || "")}</td><td class="numeric">${num(r.kl)}</td><td class="numeric">${money(r.don_gia)}</td><td class="arrow">→</td><td class="check-code">${E(r.ma_hm || "")}${r.do_khop != null && r.ma_hm ? `<span class="subline">khớp ${Math.round(r.do_khop * 100)}%</span>` : ""}</td><td class="small">${E(r.ten_csdl || "")}</td><td class="numeric">${num(r.kl_csdl)}</td><td class="numeric">${money(r.dg_csdl)}</td><td>${r.thao_tac ? badge(r.thao_tac, THAO_TAC[r.thao_tac] || "neutral") : '<span class="muted small">—</span>'}</td></tr>`,
        )
        .join("")}</tbody></table></div>${
        tong.truoc_vat != null || tong.vat != null
          ? `<p class="small muted" style="margin-top:8px">Trên bảng: Tổng trước VAT ${money(tong.truoc_vat)} · VAT${tong.ty_le_vat != null ? ` ${num(tong.ty_le_vat * 100)}%` : ""} ${money(tong.vat)} · Tổng sau VAT ${money(tong.sau_vat)}</p>`
          : ""
      }`;
  // 5. kiểm tra
  const kiem = `<div class="check-summary"><div class="counts">${["CHẶN", "ĐỎ", "VÀNG", "ĐẠT"].map((m) => badge(`${dem(kt, m)} ${m}`, dem(kt, m) ? MUC[m] : "neutral")).join("")}</div><span class="small muted">CHẶN khóa nút nạp · ĐỎ / VÀNG lưu kèm phụ lục</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Mã</th><th>Mức</th><th>Nội dung</th></tr></thead><tbody>${kt.map((x) => `<tr><td class="check-code">${E(x[0])}</td><td>${badge(x[1], MUC[x[1]] || "neutral")}</td><td class="small">${E(x[2])}</td></tr>`).join("")}</tbody></table></div>`;
  const lyDo = khoa ? "" : chan ? `Còn ${chan} lỗi CHẶN` : cho.length ? `Còn ${cho.length} tham số chưa xác nhận` : "";
  const nut = khoa
    ? `<div class="notice notice-success">${icon("check")} Đã nạp <strong>${E(kq.nap.so_pl)}</strong> vào CSDL lúc ${E(kq.nap.luc)}. Giá trị hiệu lực, tham số và BOQ được tính lại theo ngày hiệu lực.</div>`
    : `<div style="display:flex;justify-content:flex-end;align-items:center;gap:12px">${lyDo ? `<span class="small danger-text">${E(lyDo)}</span>` : ""}${btn("plai-nap", `${icon("database", 16)} Nạp phụ lục vào CSDL`, "btn-primary", lyDo || st.busy ? 'disabled aria-disabled="true"' : "")}</div>`;
  return `<div class="panel-head"><div><strong>${E(kq.ten)}</strong><span class="subline">${kq.ocr ? `OCR ABBYY ${E(kq.ocr.trang || "")} trang · ` : ""}${kq.model ? `Local AI ${E(kq.model)}` : "Chưa có Local AI"} · trích lúc ${new Date(kq.tao_luc * 1000).toLocaleString("vi-VN")}</span></div><div class="toolbar">${btn("plai-dong", `${icon("arrow-left", 15)} Danh sách`, "btn-ghost")}${khoa ? "" : btn("plai-hoi-lai", `${icon("refresh", 15)} Hỏi lại Local AI`, "", kq.ma_hd ? "" : "disabled")}${khoa ? "" : btn("plai-xoa", "Xoá bản trích", "btn-ghost")}</div></div><div class="panel-body">
    <div class="sec-title" style="margin-top:0"><h3>1. Thông tin chung</h3></div>${info}
    <div class="sec-title"><h3>2. Tham số hợp đồng bị sửa</h3>${khoa ? "" : btn("plai-them", `${icon("plus", 15)} Thêm tham số`, "btn-ghost")}</div>${thamSo}
    <div class="sec-title"><h3>3. Thay đổi khác (chỉ ghi nhận)</h3></div>${khac}
    <div class="sec-title"><h3>4. Khối lượng / đơn giá</h3></div>${boq}
    <div class="sec-title"><h3>5. Kiểm tra trước khi nạp (P01–P26)</h3></div>${kiem}
    <hr class="divider">${nut}</div>`;
}

export function renderPLAI(ctx, dsHd) {
  const st = s(ctx);
  let body;
  if (st.chon) body = chiTiet(ctx, st, dsHd);
  else {
    const j = st.job;
    const tai = st.tai;
    body = `<div class="panel-body">${st.loi ? `<div class="notice notice-danger">${icon("alert")} ${E(st.loi)}</div>` : ""}${
      j || tai
        ? `<div class="notice notice-info">${icon("activity")} <div style="flex:1"><strong>${E(tai ? `Đang tải lên ${tai}` : j.thong_bao || "Đang chờ máy AI…")}</strong><div class="progress" style="margin-top:8px"><div style="width:${Math.round((j?.pct || 0) * 100)}%"></div></div></div>${j ? btn("plai-dung", `${icon("stop", 14)} Dừng`, "btn-danger", `data-id="${E(j.id)}"`) : ""}</div>`
        : upload("plai-files", ".docx,.doc,.pdf", true, "Phụ lục Word hoặc PDF (PDF scan tự OCR bằng ABBYY trên máy) · chọn nhiều file một lượt")
    }<p class="inline-help">Phần mềm tự nhận hợp đồng, số phụ lục, ngày ký, ngày hiệu lực và bảng khối lượng / đơn giá; Local AI tìm tham số bị sửa và thay đổi khác (kèm trích dẫn nguyên văn). Anh duyệt từng mục rồi nạp. Nạp theo thứ tự PL01 → PL02 → …</p></div>${bangDs(st, dsHd)}`;
  }
  return `<section class="panel plai">${style()}<div class="panel-head"><div><strong>Trích từ file phụ lục (Word / PDF)</strong><span class="subline">Quy tắc + Local AI · kiểm tra P01–P18 như phiếu · anh duyệt trước khi nạp</span></div>${st.chon ? "" : badge(`${(st.ds || []).length} bản trích`, "neutral")}</div>${body}</section>`;
}

// ------------------------------------------------------------------ sự kiện
async function capNhat(ctx, body) {
  const st = s(ctx);
  try {
    st.kq = await post(`/api/phu_luc_ai/${st.chon}/cap_nhat`, body);
  } catch (e) {
    ctx.toast(e.message, "danger");
  }
  ctx.render();
}

async function taiVaChay(ctx, files) {
  const st = s(ctx);
  const teps = [];
  try {
    for (const [i, f] of files.entries()) {
      st.tai = `${f.name} (${i + 1}/${files.length})`;
      ctx.render();
      teps.push((await uploadFile(`/api/phu_luc_ai/tai_len?ten=${encodeURIComponent(f.name)}`, f)).tep);
    }
    st.tai = null;
    const v = await post("/api/phu_luc_ai/chay", { tep: teps });
    st.job = v;
    ctx.render();
    const x = await choViec(v.id, (t) => {
      st.job = t;
      if (ctx.state.view === "appendices") ctx.render();
    });
    st.job = null;
    await loadPLAI(ctx);
    const ds = x.ket_qua?.ds || [];
    (x.ket_qua?.loi || []).forEach((l) => ctx.toast(`${l.ten}: ${l.loi}`, "danger"));
    if (x.tt === "loi") ctx.toast(x.loi, "danger");
    else ctx.toast(`Đã trích ${ds.length} phụ lục — mở từng bản để duyệt.`, ds.length ? "success" : "warning");
    if (ds.length === 1) {
      st.chon = ds[0];
      st.kq = await get(`/api/phu_luc_ai/${ds[0]}`);
    }
  } catch (e) {
    st.tai = null;
    st.job = null;
    ctx.toast(e.message, "danger");
  }
  ctx.render();
}

export function handlePLAIChange(el, ctx) {
  const st = s(ctx);
  if ((el.id === "plai-files" || el.dataset?.folderFor === "plai-files") && el.files?.length) {
    const fs = Array.from(el.files).filter((f) => /\.(docx?|pdf)$/i.test(f.name) && !f.name.startsWith("~$"));
    if (!fs.length) ctx.toast("Chỉ nhận phụ lục .docx / .doc / .pdf.", "danger");
    else taiVaChay(ctx, fs);
    return true;
  }
  if (!st.chon || !st.kq) return false;
  if (el.dataset?.plaiInfo) {
    if (el.type === "search") return true;
    capNhat(ctx, { info: { [el.dataset.plaiInfo]: el.value } });
    return true;
  }
  if (el.dataset?.plaiMoi) {
    capNhat(ctx, { tham_so: [{ ma_ts: el.dataset.plaiMoi, moi: el.value }] });
    return true;
  }
  if (el.dataset?.plaiHd !== undefined) {
    capNhat(ctx, { ma_hd: el.value });
    return true;
  }
  if (el.dataset?.plaiBoq !== undefined) {
    capNhat(ctx, { boq_che_do: el.value });
    return true;
  }
  return false;
}

export function handlePLAIAction(action, el, ctx) {
  const st = s(ctx);
  switch (action) {
    case "plai-mo":
      st.chon = el.dataset.id;
      st.kq = null;
      ctx.render();
      get(`/api/phu_luc_ai/${st.chon}`)
        .then((d) => (st.kq = d))
        .catch((e) => {
          ctx.toast(e.message, "danger");
          st.chon = null;
        })
        .finally(() => ctx.render());
      return true;
    case "plai-dong":
      st.chon = null;
      st.kq = null;
      loadPLAI(ctx).then(() => ctx.render());
      ctx.render();
      return true;
    case "plai-ts": {
      const op = el.dataset.op;
      const ma = el.dataset.ma;
      capNhat(ctx, { tham_so: [op === "xac_nhan" ? { ma_ts: ma, trang_thai: "Đã xác nhận" } : { ma_ts: ma, bo: op === "bo" }] });
      return true;
    }
    case "plai-them": {
      ctx.openModal({
        title: "Thêm tham số bị phụ lục sửa",
        body: `<div class="field"><label>Mã tham số</label><input data-modal-field="ma_ts" placeholder="vd TT-50"></div><div class="field" style="margin-top:12px"><label>Giá trị sau phụ lục</label><input data-modal-field="moi"></div><div class="field" style="margin-top:12px"><label>Trích dẫn nguyên văn phụ lục</label><textarea data-modal-field="trich" rows="3"></textarea></div><p class="small muted" style="margin-top:10px">Mã tham số xem trong Danh mục hợp đồng → tab Tham số.</p>`,
        confirmLabel: "Thêm",
        onConfirm: (_r, vals) => capNhat(ctx, { them_ts: vals || {} }),
      });
      return true;
    }
    case "plai-hoi-lai":
      post(`/api/phu_luc_ai/${st.chon}/hoi_lai_ai`)
        .then(async (v) => {
          ctx.toast("Đang hỏi lại Local AI…", "info");
          const x = await choViec(v.id, () => {});
          if (x.tt === "loi") ctx.toast(x.loi, "danger");
          else ctx.toast("Local AI đã trả lời — xem mục 2 và 3.", "success");
          st.kq = await get(`/api/phu_luc_ai/${st.chon}`);
          ctx.render();
        })
        .catch((e) => ctx.toast(e.message, "danger"));
      return true;
    case "plai-xoa":
      ctx.openModal({
        title: "Xoá bản trích phụ lục",
        body: `<p>Xoá bản trích của <strong>${E(st.kq?.ten || "")}</strong>? Chỉ xoá kết quả trích (chưa nạp), không đụng CSDL.</p>`,
        confirmLabel: "Xoá",
        danger: true,
        onConfirm: async () => {
          try {
            await api("DELETE", `/api/phu_luc_ai/${st.chon}`);
            st.chon = null;
            st.kq = null;
            await loadPLAI(ctx);
          } catch (e) {
            ctx.toast(e.message, "danger");
          }
          ctx.render();
        },
      });
      return true;
    case "plai-nap": {
      const kq = st.kq;
      if (!kq) return true;
      const ts = (kq.tham_so || []).filter((r) => !r.bo);
      const dong = kq.boq?.dong || [];
      const g = kq.info?.gt_sau_vat ?? kq.info_tinh?.gt_sau_vat;
      ctx.openModal({
        title: `Nạp ${kq.info?.so_pl || "phụ lục"} vào CSDL`,
        body: `<p>Hợp đồng <strong>${E(kq.so_hd || kq.ma_hd)}</strong> · ký ${E(kq.info?.ngay_ky || "—")} · hiệu lực ${E(kq.info?.ngay_hieu_luc || kq.info?.ngay_ky || "—")} · ${E(kq.info?.trang_thai || "")}</p><ul class="small" style="line-height:1.9;padding-left:18px"><li>${ts.length} tham số: ${E(ts.map((r) => `${r.ma_ts} → ${r.moi}`).join("; ") || "—")}</li><li>${dong.length} dòng BOQ (${E(Object.entries(dong.reduce((a, d) => ((a[d.thao_tac] = (a[d.thao_tac] || 0) + 1), a), {})).map(([k, n]) => `${n} ${k}`).join(", ") || "không đổi BOQ")})</li><li>Giá trị tăng/giảm sau VAT: <strong>${g ? (g > 0 ? "+" : "") + money(g) : "0"}</strong> đồng</li>${(kq.khac || []).length ? `<li>${kq.khac.length} thay đổi khác ghi vào nội dung</li>` : ""}</ul><p class="small muted">Nạp rồi không sửa được; nhập sai thì hủy phụ lục (ghi lý do) rồi nạp lại.</p>`,
        confirmLabel: "Nạp vào CSDL",
        onConfirm: async () => {
          st.busy = true;
          ctx.render();
          try {
            st.kq = await post(`/api/phu_luc_ai/${st.chon}/nap`);
            ctx.toast(`Đã nạp ${st.kq.nap.so_pl} vào CSDL.`);
            if (ctx.state.hd) {
              ctx.state.hd.appendixContract = st.kq.nap.ma_hd;     // danh sách phụ lục phía trên tự tải lại
              ctx.state.hd.appendixDetail = null;
              if (ctx.state.hdLoc) ctx.state.hdLoc = { ben_a: "", du_an: "", q: "" };
            }
          } catch (e) {
            ctx.toast(e.message, "danger");
            try {
              st.kq = await get(`/api/phu_luc_ai/${st.chon}`);
            } catch (e2) {
              /* giữ bản cũ */
            }
          }
          st.busy = false;
          ctx.render();
        },
      });
      return true;
    }
    case "plai-dung":
      post(`/api/viec/${encodeURIComponent(el.dataset.id)}/dung`).catch(() => {});
      return true;
  }
  return false;
}
