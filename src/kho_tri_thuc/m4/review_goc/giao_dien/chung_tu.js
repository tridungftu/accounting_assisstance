// chung_tu.js — Lớp 3: chứng từ của đợt (BB nghiệm thu KL, BB giao nhận, packing list, CO, CQ, BB lắp đặt / chạy thử).
// PDF / ảnh scan → OCR ABBYY trên máy; Python đọc bảng dòng hàng, Local AI đọc chứng từ không có bảng.
// API: /api/chung_tu (xem API.md).
import { icon, badge, escapeHTML as E, upload, header } from "./ui.js";
import { api, get, post, upload as uploadFile, money, num, fmtDate, choViec } from "./api.js";

const MUC = { Cao: "danger", "Trung bình": "warning", Thấp: "info" };
const LOAI_MAU = { BB_NT: "info", BB_GN: "success", PL: "neutral", CO: "warning", CQ: "warning", BB_LD: "info", KHAC: "neutral" };
const ACCEPT = ".pdf,.docx,.doc,.xlsx,.xlsm,.xls,.jpg,.jpeg,.png,.tif,.tiff";

function s(ctx) {
  if (!ctx.state.ct)
    ctx.state.ct = { ds: null, loai: {}, dot: null, hd: null, chon: null, kq: null, coSo: "dot", maKq: "", maHd: "", ngay: "", job: null, tai: null, loi: "", moRong: {} };
  return ctx.state.ct;
}
const btn = (a, l, k = "", at = "") => `<button class="btn ${k}" data-action="${a}" ${at}>${l}</button>`;

export async function loadChungTu(ctx) {
  const st = s(ctx);
  try {
    const [d, dot, hd] = await Promise.all([get("/api/chung_tu"), get("/api/kiem_tra/kiem_tra_dot"), get("/api/hop_dong")]);
    st.ds = d.ds;
    st.loai = d.loai || {};
    st.dot = dot.ds || [];
    st.hd = hd.ds || [];
    if (!st.maKq && st.dot.length) st.maKq = st.dot[0].ma;
    if (!st.maHd && st.hd.length) st.maHd = st.hd[0].ma_hd;
    if (st.chon) st.kq = await get(`/api/chung_tu/${st.chon}`);
    st.loi = "";
  } catch (e) {
    st.loi = e.message;
  }
  if (ctx.state.view === "documents") ctx.render();
}

function style() {
  return `<style>
    .ct .mt td,.ct .mt th{text-align:center}.ct .mt td:first-child,.ct .mt th:first-child{text-align:left}
    .ct .ok{color:var(--green);font-weight:700}.ct .no{color:var(--red);font-weight:700}.ct .na{color:#a4afbd}
    .ct details{border-top:1px solid #e9edf3}.ct details summary{cursor:pointer;padding:10px 0;font-size:12px}
    .ct .doc-row td{vertical-align:top}.ct .table-control{max-width:200px}
    .ct .sec-title{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:24px 0 12px}
    .ct .sec-title h3{font-size:14px;margin:0}
    .ct .subline{display:block;color:#718095;font-size:11px;margin-top:4px;line-height:1.45}
    .ct .doc-row td:first-child{min-width:170px}.ct .doc-row.bo td{opacity:.5}.ct .doc-row.bo td:last-child{opacity:1}
  </style>`;
}

function tao(st) {
  const optDot = (st.dot || [])
    .map((d) => `<option value="${E(d.ma)}" ${d.ma === st.maKq ? "selected" : ""}>${E(d.hop_dong?.so_hd || "")} · đợt ${E(d.dot ?? "?")} · NT ${fmtDate(d.ngay_nghiem_thu)} · ${E(d.tep || "")}</option>`)
    .join("");
  const optHd = (st.hd || []).map((h) => `<option value="${E(h.ma_hd)}" ${h.ma_hd === st.maHd ? "selected" : ""}>${E(h.so_hd)}${h.ben_b ? " · " + E(String(h.ben_b).slice(0, 40)) : ""}</option>`).join("");
  const j = st.job;
  return `<section class="panel"><div class="panel-head"><div><strong>Bộ chứng từ mới</strong><span class="subline">Đối chiếu với hồ sơ thanh toán đã kiểm tra (KL kỳ này, lũy kế) — hoặc chỉ với BOQ hiệu lực của hợp đồng.</span></div></div><div class="panel-body">
    <div class="toolbar" style="align-items:flex-end;margin-bottom:14px"><label class="field"><span>Đối chiếu với</span><select data-ct="coSo"><option value="dot" ${st.coSo === "dot" ? "selected" : ""}>Một lần Kiểm tra đợt</option><option value="hd" ${st.coSo === "hd" ? "selected" : ""}>Hợp đồng + ngày nghiệm thu (chỉ BOQ)</option></select></label>${
      st.coSo === "dot"
        ? `<label class="field" style="flex:1;min-width:320px"><span>Kiểm tra đợt</span><select data-ct="maKq">${optDot || '<option value="">Chưa có lần Kiểm tra đợt nào</option>'}</select></label>`
        : `<label class="field" style="flex:1;min-width:280px"><span>Hợp đồng</span><select data-ct="maHd">${optHd}</select></label><label class="field"><span>Ngày nghiệm thu</span><input type="date" data-ct="ngay" value="${E(st.ngay)}"></label>`
    }</div>
    ${
      j || st.tai
        ? `<div class="notice notice-info">${icon("activity")} <div style="flex:1"><strong>${E(st.tai ? `Đang tải lên ${st.tai}` : j.thong_bao || "Đang chờ máy AI…")}</strong><div class="progress" style="margin-top:8px"><div style="width:${Math.round((j?.pct || 0) * 100)}%"></div></div></div>${j ? btn("ct-dung", `${icon("stop", 14)} Dừng`, "btn-danger", `data-id="${E(j.id)}"`) : ""}</div>`
        : upload("ct-files", ACCEPT, true, "BB nghiệm thu KL, BB giao nhận, packing list, CO, CQ, BB lắp đặt / chạy thử · PDF scan / ảnh tự OCR bằng ABBYY")
    }<p class="inline-help">Phần mềm tự nhận loại chứng từ theo tiêu đề, đọc số, ngày và bảng dòng hàng (tên, model, ĐVT, số lượng, số lô / serial, xuất xứ); chứng từ không có bảng (vd CO dạng form) do Local AI đọc kèm trích dẫn nguyên văn. Sau đó đối chiếu với KL kỳ này / lũy kế, đối chiếu chéo giữa các chứng từ và ngày tháng.</p></div></section>`;
}

function dsBo(st) {
  if (!st.ds?.length) return "";
  return `<section class="panel"><div class="panel-head"><strong>Các bộ chứng từ</strong>${badge(`${st.ds.length}`, "neutral")}</div><div class="table-wrap"><table class="data-table"><thead><tr><th>Hợp đồng</th><th>Đợt · ngày nghiệm thu</th><th>Hồ sơ thanh toán</th><th class="numeric">Chứng từ</th><th>Phát hiện</th><th></th></tr></thead><tbody>${st.ds
    .map(
      (b) =>
        `<tr><td><strong>${E(b.so_hd || b.ma_hd)}</strong></td><td>${b.dot ? `Đợt ${E(b.dot)} · ` : ""}${fmtDate(b.ngay_nt)}</td><td class="small">${E(b.tep_hstt || "— (chỉ BOQ)")}</td><td class="numeric">${b.so_tai_lieu}</td><td>${["Cao", "Trung bình", "Thấp"].map((m) => (b.dem?.[m] ? badge(`${b.dem[m]} ${m}`, MUC[m]) : "")).join("") || badge("Không cờ", "success")}</td><td>${btn("ct-mo", "Mở", "btn-ghost", `data-id="${E(b.id)}"`)}</td></tr>`,
    )
    .join("")}</tbody></table></div></section>`;
}

const dau = (ok, title) => (ok === null ? `<span class="na" title="${E(title)}">—</span>` : ok ? `<span class="ok" title="${E(title)}">✓</span>` : `<span class="no" title="${E(title)}">✗</span>`);

function chiTiet(st) {
  const kq = st.kq;
  if (!kq) return `<section class="panel"><div class="panel-body muted small">Đang tải…</div></section>`;
  const ph = kq.phat_hien || [];
  const docs = kq.tai_lieu || [];
  const coLoai = (t) => docs.some((d) => !d.bo && d.loai === t);
  const loaiOpt = (v) => Object.entries(st.loai || {}).map(([k, t]) => `<option value="${k}" ${k === v ? "selected" : ""}>${E(t)}</option>`).join("");
  const phHtml = ph.length
    ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Mã</th><th>Mức</th><th>Phát hiện</th><th>Hạng mục / chứng từ</th><th class="numeric">Ảnh hưởng (sau VAT)</th></tr></thead><tbody>${ph
        .map((f) => `<tr><td class="check-code">${E(f.id)}</td><td>${badge(f.level, MUC[f.level] || "neutral")}</td><td><strong class="small">${E(f.title)}</strong><span class="subline">${E(f.detail || "")}</span></td><td class="small">${E(f.item || f.tai_lieu || "")}</td><td class="numeric">${f.amount ? money(f.amount) : "—"}</td></tr>`)
        .join("")}</tbody></table></div>`
    : `<div class="notice notice-success">${icon("check")} Không có phát hiện.</div>`;
  const mt = kq.ma_tran || [];
  const mtHtml = mt.length
    ? `<div class="table-wrap"><table class="data-table mt"><thead><tr><th>Hạng mục</th><th>ĐVT</th><th class="numeric">KL kỳ này</th><th class="numeric">KL lũy kế</th><th>BB nghiệm thu</th><th>Đã giao</th><th>CO</th><th>CQ</th><th>Packing list</th><th>BB lắp đặt</th></tr></thead><tbody>${mt
        .map((r) => {
          const kn = r.kl_kn || 0;
          const nt = !coLoai("BB_NT") || !kn ? null : r.nt != null && r.nt + 1e-9 >= kn;
          const gn = r.gn_docs.length ? (r.kl_lk == null ? true : r.gn + 1e-9 >= r.kl_lk) : null;
          const can = r.gn_docs.length > 0;
          return `<tr><td style="text-align:left"><strong class="small">${E(r.ma_hm || "")}</strong> <span class="small">${E(String(r.ten).slice(0, 70))}</span></td><td>${E(r.dvt || "")}</td><td class="numeric">${num(r.kl_kn)}</td><td class="numeric">${num(r.kl_lk)}</td><td>${r.nt != null ? `${num(r.nt)} ` : ""}${dau(nt, r.nt_docs.join(", ") || "Không có trong BB nghiệm thu")}</td><td>${r.gn_docs.length ? `${num(r.gn)} ` : ""}${dau(gn, r.gn_docs.join(", ") || "Chưa có BB giao nhận")}</td><td>${dau(can ? r.co.length > 0 : r.co.length ? true : null, r.co.join(", "))}</td><td>${dau(can ? r.cq.length > 0 : r.cq.length ? true : null, r.cq.join(", "))}</td><td>${dau(r.pl.length ? true : can && coLoai("PL") ? false : null, r.pl.join(", "))}</td><td>${dau(r.ld.length ? true : can && coLoai("BB_LD") ? false : null, r.ld.join(", "))}</td></tr>`;
        })
        .join("")}</tbody></table></div><p class="inline-help">✓ có chứng từ và đủ số lượng · ✗ thiếu / chưa đủ · — không áp dụng. Rê chuột lên dấu để xem tên chứng từ.</p>`
    : `<p class="small muted">Chưa có hạng mục nào có KL kỳ này hoặc có chứng từ.</p>`;
  const docHtml = docs
    .map((d) => {
      const lines = (d.dong || [])
        .map((l) => `<tr><td class="small">${E(l.vi_tri)}</td><td class="small">${E(l.ten)}${l.nhom ? `<span class="subline">${E(l.nhom)}</span>` : ""}</td><td class="small">${E(l.model || "")}</td><td class="small">${E(l.quy_cach || "")}</td><td>${E(l.dvt || "")}</td><td class="numeric">${num(l.so_luong)}</td><td class="small">${E(l.lo || "")}</td><td class="small">${E([l.xuat_xu, l.nsx].filter(Boolean).join(" · "))}</td><td class="small">${l.khoa ? `${E(l.khoa)} <span class="muted">(${Math.round((l.khop || 0) * 100)}%)</span>` : '<span class="danger-text">chưa ghép</span>'}</td><td class="small">${E(l.nguon)}${l.kiem_tra ? `<span class="subline danger-text">${E(l.kiem_tra)}</span>` : ""}</td></tr>`)
        .join("");
      return `<tr class="doc-row ${d.bo ? "bo" : ""}"><td><strong class="small" style="overflow-wrap:anywhere">${E(d.ten)}</strong>${d.ocr ? `<span class="subline">OCR ABBYY ${E(d.ocr)} trang</span>` : ""}${(d.canh_bao || []).map((w) => `<span class="subline danger-text">${E(w)}</span>`).join("")}</td><td><select class="table-control" data-ct-loai="${E(d.id)}">${loaiOpt(d.loai)}</select><span class="subline">${E(d.ly_do_loai || "")}</span></td><td><input class="table-control" style="max-width:130px" data-ct-so="${E(d.id)}" value="${E(d.so || "")}"></td><td><input class="table-control" style="max-width:140px" type="date" data-ct-ngay="${E(d.id)}" value="${E(d.ngay || "")}"><span class="subline">${E((d.ngay_trich || "").slice(0, 70))}</span></td><td class="small">${E((d.hd_ref || []).map((x) => x.join("/")).join(", ") || "—")}</td><td class="numeric">${(d.dong || []).length}</td><td>${btn("ct-bo", d.bo ? "Dùng lại" : "Bỏ", "btn-ghost", `data-id="${E(d.id)}" data-bo="${d.bo ? 0 : 1}"`)}</td></tr>${
        lines ? `<tr><td colspan="7" style="padding-top:0"><details ${st.moRong[d.id] ? "open" : ""} data-ct-mo="${E(d.id)}"><summary>Dòng hàng (${d.dong.length})</summary><div class="table-wrap"><table class="data-table"><thead><tr><th>Vị trí</th><th>Tên</th><th>Model</th><th>Quy cách</th><th>ĐVT</th><th class="numeric">Số lượng</th><th>Số lô / serial</th><th>Xuất xứ · NSX</th><th>Ghép hạng mục</th><th>Nguồn</th></tr></thead><tbody>${lines}</tbody></table></div></details></td></tr>` : ""
      }`;
    })
    .join("");
  return `<section class="panel ct-detail"><div class="panel-head"><div><strong>Chứng từ · ${E(kq.so_hd || "")}${kq.dot ? ` · đợt ${E(kq.dot)}` : ""}</strong><span class="subline">Ngày nghiệm thu ${fmtDate(kq.ngay_nt)} · ${kq.tep_hstt ? `hồ sơ ${E(kq.tep_hstt)}` : "đối chiếu với BOQ hiệu lực (không có KL kỳ này)"} · ${docs.length} chứng từ</span></div><div class="toolbar">${btn("ct-dong", `${icon("arrow-left", 15)} Danh sách`, "btn-ghost")}<label class="btn" for="ct-them">${icon("upload", 15)} Thêm chứng từ</label><input id="ct-them" class="file-input" type="file" multiple accept="${ACCEPT}">${btn("ct-xoa", "Xoá bộ", "btn-ghost")}</div></div><div class="panel-body">
    ${(kq.loi || []).map((l) => `<div class="notice notice-danger">${icon("alert")} ${E(l.ten)}: ${E(l.loi)}</div>`).join("")}
    <div class="sec-title" style="margin-top:0"><h3>1. Phát hiện (C01–C09)</h3><div>${["Cao", "Trung bình", "Thấp"].map((m) => badge(`${kq.dem?.[m] || 0} ${m}`, kq.dem?.[m] ? MUC[m] : "neutral")).join("")}</div></div>${phHtml}
    <div class="sec-title"><h3>2. Ma trận hạng mục × chứng từ</h3></div>${mtHtml}
    <div class="sec-title"><h3>3. Chứng từ đã đọc</h3><span class="small muted">Sửa loại / số / ngày thì phần mềm đối chiếu lại</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>File</th><th>Loại</th><th>Số</th><th>Ngày</th><th>HĐ ghi trên chứng từ</th><th class="numeric">Dòng</th><th></th></tr></thead><tbody>${docHtml}</tbody></table></div>
  </div></section>`;
}

export function renderChungTu(ctx) {
  const st = s(ctx);
  const head = header("Chứng từ của đợt", "Lớp 3 — khối lượng kỳ này có biên bản nghiệm thu; vật tư, thiết bị có BB giao nhận, CO / CQ, packing list, BB lắp đặt.");
  if (!st.ds) return `<div class="ct">${style()}${head}<section class="panel"><div class="panel-body muted">Đang tải…</div></section></div>`;
  return `<div class="ct">${style()}${head}${st.loi ? `<div class="notice notice-danger">${icon("alert")} ${E(st.loi)}</div>` : ""}${st.chon ? chiTiet(st) : tao(st) + dsBo(st)}</div>`;
}

// ------------------------------------------------------------------ sự kiện
async function taiVaChay(ctx, files, themVao) {
  const st = s(ctx);
  const teps = [];
  try {
    for (const [i, f] of files.entries()) {
      st.tai = `${f.name} (${i + 1}/${files.length})`;
      ctx.render();
      teps.push((await uploadFile(`/api/chung_tu/tai_len?ten=${encodeURIComponent(f.name)}`, f)).tep);
    }
    st.tai = null;
    const body = themVao ? { tep: teps, them_vao: themVao } : st.coSo === "dot" ? { tep: teps, ma_kq: st.maKq } : { tep: teps, ma_hd: st.maHd, ngay_nt: st.ngay };
    const v = await post("/api/chung_tu/chay", body);
    st.job = v;
    if (themVao) ctx.toast("Đang đọc thêm chứng từ…", "info");
    ctx.render();
    const x = await choViec(v.id, (t) => {
      st.job = t;
      if (ctx.state.view === "documents" && !st.chon) ctx.render();
    });
    st.job = null;
    if (x.tt === "loi") ctx.toast(x.loi, "danger");
    else {
      (x.ket_qua?.loi || []).forEach((l) => ctx.toast(`${l.ten}: ${l.loi}`, "danger"));
      st.chon = x.ket_qua?.id || themVao || null;
      ctx.toast(`Đã đọc ${x.ket_qua?.so_tai_lieu ?? ""} chứng từ.`, "success");
    }
    await loadChungTu(ctx);
  } catch (e) {
    st.tai = null;
    st.job = null;
    ctx.toast(e.message, "danger");
  }
  ctx.render();
}

async function capNhat(ctx, body) {
  const st = s(ctx);
  try {
    st.kq = await post(`/api/chung_tu/${st.chon}/cap_nhat`, body);
  } catch (e) {
    ctx.toast(e.message, "danger");
  }
  ctx.render();
}

export function handleChungTuChange(el, ctx) {
  const st = s(ctx);
  if ((el.id === "ct-files" || el.dataset?.folderFor === "ct-files" || el.id === "ct-them") && el.files?.length) {
    const fs = Array.from(el.files).filter((f) => /\.(pdf|docx?|xls[xm]|jpe?g|png|tiff?)$/i.test(f.name) && !f.name.startsWith("~$"));
    if (!fs.length) ctx.toast("Không có file chứng từ phù hợp (PDF, Word, Excel, ảnh).", "danger");
    else if (el.id !== "ct-them" && st.coSo === "dot" && !st.maKq) ctx.toast("Chưa có lần Kiểm tra đợt — chọn 'Hợp đồng + ngày nghiệm thu'.", "danger");
    else if (el.id !== "ct-them" && st.coSo === "hd" && !st.ngay) ctx.toast("Nhập ngày nghiệm thu của đợt.", "danger");
    else taiVaChay(ctx, fs, el.id === "ct-them" ? st.chon : null);
    return true;
  }
  if (el.dataset?.ct) {
    st[el.dataset.ct] = el.value;
    ctx.render();
    return true;
  }
  if (el.dataset?.ctLoai) return capNhat(ctx, { tai_lieu: [{ id: el.dataset.ctLoai, loai: el.value }] }), true;
  if (el.dataset?.ctSo) return capNhat(ctx, { tai_lieu: [{ id: el.dataset.ctSo, so: el.value }] }), true;
  if (el.dataset?.ctNgay) return capNhat(ctx, { tai_lieu: [{ id: el.dataset.ctNgay, ngay: el.value }] }), true;
  return false;
}

export function handleChungTuAction(action, el, ctx) {
  const st = s(ctx);
  switch (action) {
    case "ct-mo":
      st.chon = el.dataset.id;
      st.kq = null;
      ctx.render();
      get(`/api/chung_tu/${st.chon}`)
        .then((d) => (st.kq = d))
        .catch((e) => {
          ctx.toast(e.message, "danger");
          st.chon = null;
        })
        .finally(() => ctx.render());
      return true;
    case "ct-dong":
      st.chon = null;
      st.kq = null;
      loadChungTu(ctx);
      return true;
    case "ct-bo":
      capNhat(ctx, { tai_lieu: [{ id: el.dataset.id, bo: el.dataset.bo === "1" }] });
      return true;
    case "ct-xoa":
      ctx.openModal({
        title: "Xoá bộ chứng từ",
        body: "<p>Xoá kết quả đọc và đối chiếu của bộ chứng từ này? File gốc và CSDL không bị đụng tới.</p>",
        confirmLabel: "Xoá",
        danger: true,
        onConfirm: async () => {
          try {
            await api("DELETE", `/api/chung_tu/${st.chon}`);
          } catch (e) {
            ctx.toast(e.message, "danger");
          }
          st.chon = null;
          st.kq = null;
          await loadChungTu(ctx);
        },
      });
      return true;
    case "ct-dung":
      post(`/api/viec/${encodeURIComponent(el.dataset.id)}/dung`).catch(() => {});
      return true;
  }
  return false;
}

// nhớ chi tiết dòng hàng nào đang mở để vẽ lại không bị đóng
document.addEventListener("toggle", (e) => {
  const d = e.target;
  if (d?.dataset?.ctMo && window.__ctState) window.__ctState.moRong[d.dataset.ctMo] = d.open;
}, true);
export function ganTrangThai(ctx) {
  window.__ctState = s(ctx);
}
