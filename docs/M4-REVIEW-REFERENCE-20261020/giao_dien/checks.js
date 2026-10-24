// checks.js — Kiểm tra đợt thanh toán: chế độ đủ hai lớp (Lớp 1 toàn vẹn + Lớp 2 đối chiếu HĐ/PL/BOQ) và chế độ chỉ
// toàn vẹn file (Lớp 1) cho hồ sơ của hợp đồng chưa có trong CSDL — cùng một mục trên menu.
// Dữ liệu thật: POST /api/hop_dong/<ma>/kiem_dot, POST /api/toan_ven, GET /api/kiem_tra/... (xem API.md).
import { icon, badge, escapeHTML, upload, header } from "./ui.js";
import { get, post, upload as uploadFile, choViec, money, num, fmtDate, today, clock, LoiApi } from "./api.js";
import { chonHopDong } from "./chon_hd.js";

const esc = (v) => escapeHTML(String(v ?? ""));
const BUOC = {
  payments: [
    [0.05, "Lớp 1 — đọc cấu trúc file và công thức"],
    [0.45, "Lớp 2 — đối chiếu BOQ, đơn giá, phụ lục tại ngày nghiệm thu"],
    [0.8, "Ghi báo cáo Excel"],
    [1, "Tổng hợp kết quả"],
  ],
  integrity: [
    [0.05, "Đọc cấu trúc file"],
    [0.15, "Kiểm tra công thức, liên kết và truy vết số đề nghị"],
    [0.85, "Tổng hợp báo cáo"],
    [1, "Xong"],
  ],
};
const LOAI = { payments: "kiem_tra_dot", integrity: "toan_ven" };
const LOAI_VIEC = { payments: "kiem_dot", integrity: "toan_ven" };

function st(ctx) {
  if (!ctx.state.ck) {
    const moi = () => ({ view: "form", file: null, job: null, kq: null, loi: "", layer: "all", severity: "all", history: null, stopped: false, formOpen: false, nap: false });
    ctx.state.ck = { contracts: null, payments: { ...moi(), hd: null, ngay: today(), dot: "" }, integrity: { ...moi(), o: "" } };
  }
  return ctx.state.ck;
}
function pill(label) {
  const kind = ["Cao", "Lỗi", "CHẶN", "Lệch"].includes(label)
    ? "danger"
    : ["Trung bình", "Cần xem", "Có cảnh báo"].includes(label)
      ? "warning"
      : ["Thấp", "Không áp dụng", "Không có số liệu"].includes(label)
        ? "neutral"
        : "success";
  return badge(label, kind);
}
function val(v) {
  if (v === null || v === undefined || v === "") return "—";
  return typeof v === "number" ? money(v) : esc(v);
}
function fileUpload(id, accept, subtitle) {
  return upload(id, accept, false, subtitle);
}

// ================================================================== tải dữ liệu
async function loadContractsList(ctx) {
  const s = st(ctx);
  try {
    s.contracts = (await get("/api/hop_dong")).ds;
  } catch (e) {
    s.contracts = [];
    ctx.toast(e.message, "danger");
  }
  const p = s.payments; // null = chưa chọn → hợp đồng đầu; "" = bộ lọc không còn hợp đồng nào
  if (p.hd == null || (p.hd && !s.contracts.some((h) => h.ma_hd === p.hd))) p.hd = s.contracts[0]?.ma_hd || "";
}
async function loadHistory(ctx, page) {
  const s = st(ctx)[page];
  try {
    s.history = (await get(`/api/kiem_tra/${LOAI[page]}`)).ds;
  } catch (e) {
    s.history = [];
  }
}
async function openSaved(ctx, page, ma) {
  const s = st(ctx)[page];
  try {
    s.kq = await get(`/api/kiem_tra/${LOAI[page]}/${encodeURIComponent(ma)}`);
    s.view = "result";
    s.layer = "all";
    s.severity = "all";
    s.formOpen = false;
  } catch (e) {
    ctx.toast(e.message, "danger");
  }
}
export async function loadChecks(ctx) {
  const ck = st(ctx);
  const page = ctx.state.view;
  const s = ck[page];
  const opts = ctx.state.navOpts || {};
  ctx.state.navOpts = null;
  const jobs = [];
  if (page === "payments") jobs.push(loadContractsList(ctx));
  jobs.push(loadHistory(ctx, page));
  await Promise.all(jobs);
  if (opts.hd && page === "payments") {
    s.hd = opts.hd;
    s.view = "form";
  }
  if (opts.ma) await openSaved(ctx, page, opts.ma);
  // việc đang chạy từ trước (vd mở lại trang) → theo dõi tiếp
  if (!s.job && s.view !== "result") {
    try {
      const ds = (await get("/api/viec")).ds;
      const v = ds.find((x) => x.loai === LOAI_VIEC[page] && ["cho", "dang_chay"].includes(x.tt));
      if (v) follow(ctx, page, v);
    } catch (e) {
      /* bỏ qua */
    }
  }
  if (ctx.state.view === page) ctx.render();
}

// ================================================================== theo dõi việc nền
async function follow(ctx, page, v) {
  const s = st(ctx)[page];
  s.job = v;
  s.view = "running";
  s.loi = "";
  const ve = () => {
    if (ctx.state.view === page && !document.querySelector(".modal,.drawer")) ctx.render();
  };
  ve();
  try {
    const kq = await choViec(v.id, (x) => {
      if (s.job?.id !== v.id) return;
      s.job = x;
      ve();
    });
    if (s.job?.id !== v.id) return;
    s.job = null;
    if (kq.tt === "xong" && kq.ket_qua) {
      s.kq = kq.ket_qua;
      s.view = "result";
      s.layer = "all";
      s.severity = "all";
      s.formOpen = false;
      s.file = null;
      loadHistory(ctx, page).then(ve);
    } else if (kq.tt === "da_dung") {
      s.view = "form";
      s.stopped = true;
    } else {
      s.view = "error";
      s.loi = kq.loi || "Không rõ lỗi";
    }
  } catch (e) {
    s.job = null;
    s.view = "error";
    s.loi = e.message;
  }
  ve();
}
async function run(ctx, page) {
  const s = st(ctx)[page];
  if (!s.file) return ctx.toast("Chọn file Excel hồ sơ trước khi chạy.", "warning");
  let url;
  if (page === "payments") {
    if (!s.hd) return ctx.toast("Chọn hợp đồng.", "warning");
    if (!s.ngay) return ctx.toast("Nhập ngày nghiệm thu — mốc áp dụng phụ lục.", "warning");
    if (s.dot && !/^\d+$/.test(String(s.dot).trim())) return ctx.toast("Số đợt phải là số (ví dụ 4).", "warning");
    url = `/api/hop_dong/${encodeURIComponent(s.hd)}/kiem_dot?ten=${encodeURIComponent(s.file.name)}&ngay_nghiem_thu=${s.ngay}${s.dot ? `&dot=${Number(s.dot)}` : ""}`;
  } else url = `/api/toan_ven?ten=${encodeURIComponent(s.file.name)}${s.o.trim() ? `&o=${encodeURIComponent(s.o.trim())}` : ""}`;
  s.stopped = false;
  try {
    const v = await uploadFile(url, s.file);
    ctx.refreshJobs?.();
    follow(ctx, page, v);
  } catch (e) {
    ctx.toast(e.message, "danger");
  }
}

// ================================================================== khối giao diện
// Một màn Kiểm tra đợt, hai chế độ: đủ hai lớp (HĐ đã có trong CSDL) / chỉ toàn vẹn file (HĐ CHƯA có trong CSDL)
function cheDo(page) {
  const o = (id, route, t, d) =>
    `<button class="panel" data-route="${route}" aria-pressed="${page === id}" style="flex:1;min-width:260px;text-align:left;padding:14px 16px;cursor:pointer;border:${page === id ? "2px solid var(--blue,#2c5aa0)" : "1px solid var(--border,#dce2e7)"};background:${page === id ? "var(--surface-soft,#f4f6f8)" : "var(--surface,#fff)"}"><strong style="display:flex;gap:8px;align-items:center">${icon(page === id ? "check" : "file", 16)} ${t}</strong><span class="small muted" style="display:block;margin-top:6px">${d}</span></button>`;
  return `<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px" role="group" aria-label="Chế độ kiểm tra">${o("payments", "payments", "Đủ hai lớp — hợp đồng đã có trong CSDL", "Lớp 1 toàn vẹn file + Lớp 2 đối chiếu giá trị HĐ, đơn giá, khối lượng BOQ, tỷ lệ thanh toán, phụ lục. Nạp được đợt đã duyệt.")}${o("integrity", "integrity", "Chỉ toàn vẹn file — hợp đồng CHƯA có trong CSDL", "Chỉ Lớp 1: công thức, liên kết, số gõ tay, sheet ẩn, truy vết số đề nghị. Không đối chiếu với hợp đồng, không nạp đợt.")}</div>`;
}
function paymentForm(ctx, s, expanded = true) {
  const ck = st(ctx);
  if (!expanded) {
    const k = s.kq;
    return `<section class="panel" style="margin-bottom:18px"><div class="panel-body" style="display:flex;align-items:center;justify-content:space-between;gap:16px"><div><strong>${esc(k.tep)}</strong><div class="small muted" style="margin-top:4px">${k.dot ? `Đợt ${esc(k.dot)} · ` : ""}${k.so_hang_muc ?? "?"} hạng mục ở sheet ${esc(k.bang_chi_tiet || "")} · Kiểm tra lúc ${esc(String(k.luc || "").replace("T", " "))}</div></div><button class="btn btn-ghost" data-action="pay-form">${icon("edit")} Kiểm tra hồ sơ khác</button></div></section>`;
  }
  const ds = ck.contracts || [];
  const hd = ds.find((h) => h.ma_hd === s.hd);
  return `<section class="panel" style="margin-bottom:18px"><div class="panel-head"><h2>Hồ sơ kiểm tra</h2><span class="small muted">Áp dụng phụ lục theo ngày nghiệm thu</span></div><div class="panel-body">${
    !ck.contracts
      ? '<p class="muted">Đang tải danh sách hợp đồng…</p>'
      : !ds.length
        ? `<div class="notice notice-warning">${icon("alert")} <div><strong>CSDL chưa có hợp đồng.</strong> Kiểm tra đủ hai lớp cần hợp đồng, phụ lục và BOQ trong CSDL. Hợp đồng chưa nạp thì chọn chế độ <button class="link-btn" data-route="integrity" style="display:inline;min-height:0;padding:0">Chỉ toàn vẹn file — hợp đồng CHƯA có trong CSDL</button>.</div></div>`
        : ""
  }<div class="toolbar" style="align-items:flex-end;margin-bottom:12px">${chonHopDong(ctx.state, ds, s.hd, 'data-check-field="hd"')}</div><div class="grid-2" style="margin-bottom:16px"><label class="field">Ngày nghiệm thu<input type="date" data-check-field="ngay" value="${esc(s.ngay)}" required></label><label class="field">Số đợt<input type="text" inputmode="numeric" data-check-field="dot" value="${esc(s.dot)}" placeholder="Để trống: tự đọc từ hồ sơ"></label></div>${fileUpload("payments-file", ".xlsx,.xlsm,.xls", "Excel .xlsx, .xlsm, .xls · Một file cho mỗi đợt")}<div class="small muted" style="margin-top:8px">${s.file ? `Đã chọn: <strong>${esc(s.file.name)}</strong>. ` : ""}File được lưu trên máy này để truy vết; không gửi ra ngoài.</div><div class="toolbar" style="justify-content:space-between;margin-top:16px"><span class="small muted">${hd ? `${esc(hd.ma_hd)}: ${hd.so_phu_luc} phụ lục · ${hd.so_boq} dòng BOQ gốc · ${hd.so_dot} đợt đã nạp${hd.so_boq ? "" : " — chưa có BOQ, Lớp 2 sẽ thiếu căn cứ"}` : ""}</span><button class="btn btn-primary" data-action="pay-run" ${s.file && s.hd ? "" : "disabled"}>${icon("play")} Kiểm tra hồ sơ</button></div></div></section>`;
}
function scope(k) {
  const chua = k.phu_luc_chua_ap_dung || [];
  const ap = k.phu_luc_ap_dung || [];
  return `<section class="panel" style="margin-bottom:18px"><div class="panel-body" style="display:flex;gap:22px;flex-wrap:wrap;align-items:center"><div style="flex:1;min-width:230px"><strong>${esc(k.hop_dong?.ma_hd)} · ${esc(k.hop_dong?.so_hd)}</strong><div class="small muted" style="margin-top:5px">${esc(k.ben_b || "")}${k.loai_gia ? ` · ${esc(k.loai_gia)}` : ""}</div></div><div><div class="small muted">Ngày nghiệm thu áp dụng</div><strong style="display:block;margin-top:4px">${fmtDate(k.ngay_nghiem_thu)}</strong><div class="small muted" style="margin-top:3px">${chua.length ? esc(chua.map((p) => `${p.so_pl} (${fmtDate(p.ngay_hieu_luc)}) chưa áp dụng`).join("; ")) : "Không có phụ lục chờ hiệu lực"}</div></div><div><div class="small muted">Giá trị HĐ hiệu lực</div><strong class="numeric" style="display:block;margin-top:4px">${money(k.gt_hieu_luc)} ₫</strong></div><div><div class="small muted">Phụ lục áp dụng</div><button class="btn btn-ghost" data-action="pay-open-appendices" style="padding-left:0;padding-right:0">${ap.length ? esc(ap.map((p) => p.so_pl).join(", ")) : "Không có"} ${icon("external")}</button></div></div></section>`;
}
function summary(k, integrity = false) {
  const dem = k.dem || {};
  const dinhLuong = (k.phat_hien || []).filter((f) => f.layer === 2 && typeof f.amount === "number" && f.code !== "GT").length;
  return `<section class="stat-strip" style="margin-bottom:18px;grid-template-columns:repeat(3,minmax(0,1fr))"><div class="stat"><div class="stat-label">Số đề nghị thanh toán</div><div class="stat-value numeric" style="font-size:24px">${k.de_nghi == null ? "—" : money(k.de_nghi)}<span class="small muted"> ₫</span></div><div class="small muted">${esc(k.o_de_nghi || k.dich || "Không tìm được ô số đề nghị")}${k.dot ? ` · Đợt ${esc(k.dot)}` : ""}</div></div><div class="stat"><div class="stat-label">${integrity ? "Số sheet" : "Ảnh hưởng ước tính"}</div><div class="stat-value numeric" style="font-size:24px;${integrity ? "" : "color:var(--red,#ad3536)"}">${integrity ? esc(k.so_sheet ?? "—") : `${money(k.anh_huong || 0)}<span class="small muted"> ₫</span>`}</div><div class="small muted">${integrity ? "Chỉ Lớp 1 · Chưa đối chiếu BOQ" : `${dinhLuong} phát hiện định lượng · Chưa gồm VAT`}</div></div><div class="stat"><div class="stat-label">Phát hiện cần xem</div><div class="stat-value">${k.so_phat_hien || 0}</div><div class="small" style="display:flex;gap:7px;flex-wrap:wrap">${dem.Cao ? badge(`${dem.Cao} cao`, "danger") : ""}${dem["Trung bình"] ? badge(`${dem["Trung bình"]} trung bình`, "warning") : ""}${dem["Thấp"] ? badge(`${dem["Thấp"]} thấp`, "neutral") : ""}${!k.so_phat_hien ? badge("Không có", "success") : ""}</div></div></section>`;
}
function findingsTable(rows, s, page) {
  const filtered = rows.filter((r) => s.severity === "all" || r.level === s.severity);
  const p = page === "payments" ? "pay" : "int";
  const tong = rows.reduce((a, r) => a + (typeof r.amount === "number" && r.code !== "GT" ? r.amount : 0), 0);
  const chua = rows.filter((r) => typeof r.amount !== "number").length;
  return `<section class="panel" style="margin-bottom:18px"><div class="panel-head" style="gap:12px;flex-wrap:wrap"><div><h2 style="margin:0">Phát hiện cần xem <span class="muted small">${filtered.length}/${rows.length}</span></h2><div class="small muted" style="margin-top:5px">Bấm vị trí ô để mở bằng chứng và căn cứ đối chiếu</div></div><label class="field" style="display:flex;flex-direction:row;align-items:center;gap:8px">Mức độ<select aria-label="Lọc mức độ phát hiện" data-check-field="severity" style="width:auto"><option value="all">Tất cả</option>${["Cao", "Trung bình", "Thấp"].map((l) => `<option ${s.severity === l ? "selected" : ""}>${l}</option>`).join("")}</select></label></div><div class="table-wrap"><table class="data-table"><thead><tr><th style="width:82px">Mã</th><th style="width:72px">Lớp</th><th style="width:100px">Mức</th><th>Mô tả</th><th class="numeric" style="width:150px">Ảnh hưởng (đồng)</th><th style="width:170px">Vị trí trong file</th></tr></thead><tbody>${
    filtered.length
      ? filtered
          .map(
            (r) =>
              `<tr><td><strong>${esc(r.id)}</strong></td><td>Lớp ${r.layer}</td><td>${pill(r.level)}</td><td><strong>${esc(r.title)}</strong>${r.item ? `<div class="small" style="margin-top:4px">${esc(r.item)}</div>` : ""}${r.detail ? `<div class="small muted" style="margin-top:4px;max-width:460px">${esc(String(r.detail).slice(0, 260))}</div>` : ""}</td><td class="numeric">${typeof r.amount === "number" ? money(r.amount) : '<span class="muted" title="Chưa xác định được ảnh hưởng">Chưa xác định</span>'}</td><td><button class="btn btn-ghost" data-action="${p}-evidence" data-id="${esc(r.id)}" style="padding-left:0;padding-right:0;text-align:left;white-space:normal">${r.sheet ? `${esc(r.sheet)}!${esc(r.cell)}` : esc(r.cell || "Xem")} ${icon("external")}</button></td></tr>`,
          )
          .join("")
      : `<tr><td colspan="6"><div class="empty-state" style="padding:28px">${rows.length ? "Không có phát hiện ở mức đã chọn." : "Không có phát hiện ở lớp này."}</div></td></tr>`
  }</tbody></table></div><div class="panel-body small muted" style="padding-top:10px;padding-bottom:10px">${page === "integrity" ? "Lớp 1 kiểm tra tính toàn vẹn của tệp. Đối chiếu HĐ, phụ lục và BOQ tại màn Kiểm tra đợt." : `Tổng ảnh hưởng ${money(tong)} đồng là tổng các khoản chênh lệch Lớp 2 đã định lượng (chưa VAT); ${chua} phát hiện chưa định lượng.`}</div></section>`;
}
function checksGrid(k, page) {
  const rows = k.bang_k || [];
  const can = rows.filter((r) => r.ket_qua !== "Đạt").length;
  const p = page === "payments" ? "pay" : "int";
  return `<section class="panel" style="margin-bottom:18px"><div class="panel-head"><h2>Kiểm tra toàn vẹn K1–K8</h2><span class="small muted">${can} cần xem · ${rows.length - can} đạt</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th style="width:72px">Mã</th><th>Nội dung kiểm tra</th><th style="width:120px">Kết quả</th><th>Chi tiết</th><th style="width:80px"></th></tr></thead><tbody>${rows
    .map(
      (r) =>
        `<tr><td><strong>${esc(r.code)}</strong></td><td>${esc(r.ten)}</td><td>${pill(r.ket_qua)}</td><td class="muted">${esc(r.chi_tiet)}${r.so > 1 ? ` <span class="small">(+${r.so - 1} phát hiện)</span>` : ""}</td><td>${r.finding ? `<button class="btn btn-ghost" aria-label="Xem bằng chứng ${esc(r.code)}" data-action="${p}-evidence" data-id="${esc(r.finding)}">Xem</button>` : `<button class="btn btn-ghost" aria-label="Xem chi tiết ${esc(r.code)}" data-action="check-detail" data-id="${esc(r.code)}">Xem</button>`}</td></tr>`,
    )
    .join("")}</tbody></table></div></section>`;
}
// Lớp 2: các bước đã so với HĐ (kể cả bước đạt) — giá trị HĐ ↔ thanh toán, tỷ lệ thanh toán, BOQ ↔ hồ sơ
function lop2Grid(k) {
  const rows = k.bang_lop2;
  if (!rows)
    return `<div class="notice notice-info" style="display:block;margin-bottom:18px">Kết quả này chạy bằng bản cũ nên chưa có bảng các bước đối chiếu Lớp 2 (giá trị HĐ so với thanh toán, tỷ lệ thanh toán, đơn giá và khối lượng BOQ so với hồ sơ). Bấm <strong>Kiểm tra đợt mới</strong> và nạp lại file để xem. Báo cáo Excel Lớp 2 vẫn có phần Tổng hợp và Hạng mục.</div>`;
  const lech = rows.filter((r) => r.ket_qua === "Lệch").length;
  const xem = rows.filter((r) => r.ket_qua === "Cần xem").length;
  const v = (x, dv) => (x === null || x === undefined || x === "" ? "—" : typeof x === "number" ? (dv === "đồng" ? money(x) : num(x)) : `<span style="white-space:normal;display:inline-block;max-width:260px;text-align:left">${esc(x)}</span>`);
  let nhom = "";
  const body = rows
    .map((r) => {
      const h = r.nhom !== nhom ? `<tr class="l2-group"><td colspan="6"><strong>${esc(r.nhom)}</strong></td></tr>` : "";
      nhom = r.nhom;
      const o = r.finding
        ? `<button class="btn btn-ghost" data-action="pay-evidence" data-id="${esc(r.finding)}" style="padding:0;min-height:0;text-align:left;white-space:normal">${esc(r.o || r.finding)} ${icon("external", 13)}</button>`
        : `<span class="small muted">${esc(r.o || "")}</span>`;
      return `${h}<tr><td>${esc(r.ten)}${r.ghi ? `<div class="small muted" style="margin-top:4px">${esc(r.ghi)}</div>` : ""}</td><td class="numeric">${v(r.ho_so, r.don_vi)}</td><td class="numeric">${v(r.hd, r.don_vi)}</td><td class="numeric">${r.chenh === null || r.chenh === undefined ? "" : `<span class="${Math.abs(r.chenh) > 1000 ? "danger-text" : "muted"}">${money(r.chenh)}</span>`}</td><td>${pill(r.ket_qua)}</td><td>${o}</td></tr>`;
    })
    .join("");
  return `<section class="panel" style="margin-bottom:18px"><div class="panel-head" style="flex-wrap:wrap;gap:10px"><div><h2 style="margin:0">Lớp 2 · Các bước đối chiếu với hợp đồng</h2><div class="small muted" style="margin-top:5px">Theo HĐ + phụ lục hiệu lực tại ngày nghiệm thu ${fmtDate(k.ngay_nghiem_thu)} · số tiền tính bằng đồng</div></div><div style="display:flex;gap:6px;flex-wrap:wrap">${badge(`${rows.length - lech - xem} đạt`, "success")}${lech ? badge(`${lech} lệch`, "danger") : ""}${xem ? badge(`${xem} cần xem`, "warning") : ""}</div></div><div class="table-wrap"><table class="data-table l2-table"><thead><tr><th style="min-width:300px">Bước kiểm tra</th><th class="numeric" style="width:150px">Theo hồ sơ</th><th class="numeric" style="width:150px">Theo HĐ / CSDL</th><th class="numeric" style="width:120px">Chênh lệch</th><th style="width:120px">Kết quả</th><th style="width:150px">Ô trong hồ sơ</th></tr></thead><tbody>${body}</tbody></table></div></section>${hangMuc(k)}`;
}
// cách ghép máy tự chọn nhưng nên liếc lại (tên trùng nhiều hạng mục BOQ / tên gần đúng)
const KHOP_XEM = /^(tên trùng|tên gần đúng)/;
function hangMuc(k) {
  const ds = k.doi_chieu_hm || [];
  if (!ds.length) return "";
  const s = hangMuc.s || (hangMuc.s = { loc: null });
  s.doi = s.doi || {};
  const loi = ds.filter((h) => h.loi?.length);
  const ghep = ds.filter((h) => !h.ma_hm && h.ung_vien?.length);
  const xemLai = ds.filter((h) => h.ma_hm && KHOP_XEM.test(h.khop || ""));
  const het = (s.loc === "ghep" && !ghep.length) || (s.loc === "xem" && !xemLai.length);
  const loc = (!het && s.loc) || (ghep.length ? "ghep" : loi.length ? "loi" : "all");
  const rows = loc === "loi" ? loi : loc === "ghep" ? ghep : loc === "xem" ? xemLai : loc === "kn" ? ds.filter((h) => h.kl_kn) : ds;
  const lech = (a, b, eps) => a !== null && a !== undefined && b !== null && b !== undefined && Math.abs(a - b) > eps;
  const cell = (a, b, eps, f = num) => `${f(a)}${b !== undefined && lech(a, b, eps) ? `<div class="small danger-text">HĐ: ${f(b)}</div>` : ""}`;
  const cuoi = (n) => String(n || "").split(" / ").pop();
  const chon = (h) => {
    const uv = h.ung_vien || [];
    const dl = `<datalist id="hm-uv-${esc(h.dong)}">${uv.map((u) => `<option value="${esc(u.ma_hm)}" label="${esc(`${cuoi(u.nhom) || "—"} · ĐG ${money(u.don_gia)} · KL ${num(u.kl)} · tên giống ${Math.round(u.ty_le * 100)}%`)}"></option>`).join("")}</datalist>`;
    const bang = uv.length
      ? `<div class="small muted" style="margin-top:6px">${uv
          .slice(0, 5)
          .map((u) => `<div><strong>${esc(u.ma_hm)}</strong> · ${esc(cuoi(u.nhom) || "—")} · ĐG ${money(u.don_gia)} · KL ${num(u.kl)}${h.dg_hs != null && Math.abs((u.don_gia || 0) - h.dg_hs) <= 0.5 ? " · <span style=\"color:var(--success,#2f7d4f)\">cùng ĐG</span>" : ""}</div>`)
          .join("")}</div>`
      : "";
    return `<div style="margin-top:6px;display:flex;gap:6px;align-items:center;flex-wrap:wrap"><input data-hm-ma="${esc(h.dong)}" list="hm-uv-${esc(h.dong)}" value="${esc(h.ghep_tay || "")}" placeholder="${esc(uv[0]?.ma_hm || "Mã HM")}" style="width:120px;min-height:30px;padding:4px 8px" aria-label="Mã HM ghép cho dòng ${esc(h.dong)}">${dl}<button class="btn btn-ghost" data-action="pay-hm-ghep" data-dong="${esc(h.dong)}" style="min-height:30px;padding:4px 10px">Ghép</button></div>${bang}`;
  };
  const body = rows
    .map((h) => {
      const pct = h.kl_hd ? (h.kl_lk || 0) / h.kl_hd : null;
      const xem = h.ma_hm && KHOP_XEM.test(h.khop || "");
      const moGhep = (!h.ma_hm && h.ung_vien?.length) || s.doi[h.dong];
      const khop = h.ghep_tay
        ? `<div class="small" style="color:var(--success,#2f7d4f)">Đã ghép tay → ${esc(h.ghep_tay)} · chạy lại để cập nhật</div>`
        : h.khop
          ? `<div class="small ${xem ? "" : "muted"}" style="${xem ? "color:var(--warning,#92661d)" : ""}">${esc(h.khop)}${xem && !s.doi[h.dong] ? ` · <button class="link-btn" data-action="pay-hm-doi" data-dong="${esc(h.dong)}" style="display:inline;min-height:0;padding:0">Đổi</button>` : ""}</div>`
          : "";
      const kq = h.loi?.length
        ? `${pill(h.can_ghep ? "Cần xem" : "Lệch")}<div class="small" style="margin-top:4px">${esc(h.loi.join("; "))}</div>`
        : pill("Đạt");
      return `<tr><td class="small muted">${esc(h.dong)}</td><td><strong class="small">${esc(h.ma_hm || "—")}</strong>${h.ma_rieng ? `<div class="small muted">mã ${esc(h.ma_rieng)}</div>` : ""}${khop}</td><td class="small">${esc(h.ten)}${h.nhom ? `<div class="muted" style="font-size:11px">${esc(h.nhom)}</div>` : ""}${moGhep ? chon(h) : ""}</td><td>${esc(h.dvt)}</td><td class="numeric">${cell(h.kl_hd_hs, h.kl_hd, 1e-6)}</td><td class="numeric">${cell(h.dg_hs, h.dg_hd, 0.5, money)}</td><td class="numeric">${cell(h.kl_kt, h.kl_kt_db ?? undefined, 1e-6)}</td><td class="numeric">${num(h.kl_kn)}</td><td class="numeric ${pct !== null && pct > 1 + 1e-9 ? "danger-text" : ""}">${num(h.kl_lk)}${pct !== null ? `<div class="small muted">${num(Math.round(pct * 1000) / 10)}%</div>` : ""}</td><td>${kq}</td></tr>`;
    })
    .join("");
  const moi = (k.ghep_moi || []).length;
  const nhac = moi
    ? `<div class="notice notice-info" style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0 18px 12px;flex-wrap:wrap"><span>Đã ghép tay ${moi} dòng. Máy nhớ các ghép này cho các lần kiểm tra và các đợt sau của hợp đồng. Chạy lại để cập nhật phát hiện và bảng kiểm.</span><button class="btn btn-primary" data-action="pay-rerun">${icon("play")} Chạy lại kiểm tra</button></div>`
    : ghep.length
      ? `<div class="notice notice-warning" style="display:block;margin:0 18px 12px"><strong style="display:inline">${ghep.length} dòng cần ghép tay:</strong> tên trùng nhiều hạng mục BOQ (thiết bị lặp ở nhiều bể) mà máy chưa chọn được, hoặc tên chỉ gần giống. Chọn mã HM đúng (xem nhóm/bể, đơn giá, KL bên dưới) rồi bấm Ghép.</div>`
      : "";
  const o = (v, t, n) => `<option value="${v}" ${loc === v ? "selected" : ""}>${t} (${n})</option>`;
  return `<section class="panel" style="margin-bottom:18px"><details ${s.mo || ghep.length ? "open" : ""} data-hm-mo><summary class="panel-head" style="cursor:pointer;list-style:none;flex-wrap:wrap;gap:10px"><div><h2 style="margin:0">Đối chiếu từng hạng mục: BOQ hiệu lực so với hồ sơ</h2><div class="small muted" style="margin-top:5px">${ds.length} hạng mục · ${loi.length} lệch${ghep.length ? ` · ${ghep.length} cần ghép tay` : ""}${xemLai.length ? ` · ${xemLai.length} máy ghép theo tên trùng/gần đúng` : ""} · KL HĐ, đơn giá, KL kỳ trước so với BOQ và đợt trước đã duyệt; ô đỏ ghi số theo HĐ</div></div><span class="btn btn-ghost">${s.mo || ghep.length ? "Thu gọn" : "Mở bảng"}</span></summary><div class="toolbar" style="padding:0 18px 12px"><label class="field" style="display:flex;flex-direction:row;align-items:center;gap:8px">Hiện<select data-hm-loc style="width:auto">${ghep.length ? o("ghep", "Cần ghép tay", ghep.length) : ""}${o("loi", "Hạng mục lệch", loi.length)}${xemLai.length ? o("xem", "Máy ghép theo tên trùng / gần đúng", xemLai.length) : ""}${o("kn", "Có KL kỳ này", ds.filter((h) => h.kl_kn).length)}${o("all", "Tất cả", ds.length)}</select></label></div>${nhac}<div class="table-wrap" style="max-height:560px;overflow:auto"><table class="data-table"><thead><tr><th>Dòng</th><th>Mã HM · khớp bằng</th><th>Tên công việc</th><th>ĐVT</th><th class="numeric">KL HĐ</th><th class="numeric">Đơn giá</th><th class="numeric">KL kỳ trước</th><th class="numeric">KL kỳ này</th><th class="numeric">KL lũy kế · % KL HĐ</th><th>Kết quả</th></tr></thead><tbody>${body || `<tr><td colspan="10"><div class="empty-state" style="padding:22px">Không có hạng mục ở bộ lọc này.</div></td></tr>`}</tbody></table></div></details></section>`;
}
document.addEventListener("toggle", (e) => {
  if (e.target?.matches?.("[data-hm-mo]")) {
    (hangMuc.s || (hangMuc.s = {})).mo = e.target.open;
    const b = e.target.querySelector("summary .btn");
    if (b) b.textContent = e.target.open ? "Thu gọn" : "Mở bảng";
  }
}, true);
function traceTree(cay, compact = false) {
  if (!cay?.length) return '<p class="small muted">Không truy vết được số đề nghị (không tìm thấy ô đích). Chạy Toàn vẹn với ô số đề nghị cụ thể.</p>';
  const line = (n) =>
    `<span style="display:flex;justify-content:space-between;gap:18px;align-items:center;min-height:38px"><span><strong>${esc(n.o)}</strong> <span class="muted">${esc(String(n.ten || "").slice(0, 90))}</span>${n.loai && n.loai !== "Công thức" ? ` ${badge(n.loai, /tay|ngoài|lỗi/i.test(n.loai) ? "warning" : "neutral")}` : ""}</span><strong class="numeric" style="white-space:nowrap">${typeof n.gia_tri === "number" ? `${money(n.gia_tri)} ₫` : esc(n.gia_tri ?? "")}</strong></span>`;
  const extra = (n) =>
    `${n.cong_thuc ? `<div class="small muted" style="margin:2px 0 8px 20px;overflow-wrap:anywhere">${esc(n.cong_thuc)}</div>` : ""}${n.tai_lieu || n.ghi ? `<div class="small" style="margin:0 0 8px 20px;color:var(--warning,#92661d)">${esc([n.tai_lieu, n.ghi].filter(Boolean).join(" · "))}</div>` : ""}`;
  // cây: hàng theo thứ tự duyệt sâu, có cấp
  let i = 0;
  const build = (cap) => {
    let html = "";
    while (i < cay.length && cay[i].cap === cap) {
      const n = cay[i++];
      if (i < cay.length && cay[i].cap > cap) {
        const open = !compact ? cap < 2 : cap < 1;
        html += `<details ${open ? "open" : ""}><summary style="min-height:40px;cursor:pointer">${line(n)}</summary>${extra(n)}<div style="margin-left:20px;border-left:2px solid var(--border,#dce2e7);padding-left:14px">${build(cay[i].cap)}</div></details>`;
      } else html += `<div>${line(n)}${extra(n)}</div>`;
    }
    return html;
  };
  let html = "";
  while (i < cay.length) {
    const before = i;
    html += build(cay[i].cap);
    if (i === before) i++;
  }
  return `<div class="trace-tree" style="font-size:13px">${html}<div class="small muted" style="margin-top:12px">Bấm từng nhánh để mở/đóng. ${cay.length} ô trong cây hình thành số đề nghị.</div></div>`;
}
function tracePanel(k) {
  return `<section class="panel"><div class="panel-head"><h2>Truy vết số đề nghị thanh toán</h2>${badge(`${(k.cay || []).length} ô nguồn`, "neutral")}</div><div class="panel-body">${traceTree(k.cay)}</div></section>`;
}
function runningPanel(page, s) {
  const j = s.job || {};
  const pct = Math.round((j.pct || 0) * 100);
  const steps = BUOC[page];
  let index = 0;
  steps.forEach(([m], i) => {
    if ((j.pct || 0) >= m) index = i;
  });
  const elapsed = j.bat_dau ? Date.now() / 1000 - j.bat_dau : 0;
  const log = (j.nhat_ky || []).slice(-30);
  return `<section class="panel"><div class="panel-head"><h2>${j.tt === "cho" ? "Đang chờ" : "Đang kiểm tra"} · ${esc(j.ten || "")}</h2><button class="btn btn-danger" data-action="${page === "payments" ? "pay" : "int"}-stop">${icon("stop")} Dừng</button></div><div class="panel-body"><div style="display:flex;justify-content:space-between;gap:12px;margin-bottom:12px"><strong>${esc(j.thong_bao || steps[index][1])}</strong><span class="numeric">${pct}%</span></div><progress value="${pct}" max="100" aria-label="Tiến độ kiểm tra hồ sơ" style="width:100%;height:9px;accent-color:var(--accent,#237c70)"></progress><div class="small muted" style="margin:10px 0 20px">Đã chạy ${clock(elapsed)} · Có thể chuyển màn hình, việc vẫn chạy tiếp</div><ol style="list-style:none;padding:0;margin:0;display:grid;gap:10px">${steps.map(([, step], i) => `<li style="display:flex;align-items:center;gap:10px">${i < index ? badge("Xong", "success") : i === index ? badge("Đang chạy", "info") : badge("Chờ", "neutral")}<span ${i > index ? 'class="muted"' : ""}>${step}</span></li>`).join("")}</ol>${log.length ? `<div class="panel" style="margin-top:22px"><div class="panel-head"><h3 style="margin:0;font-size:14px">Nhật ký kiểm tra</h3></div><div class="panel-body small" role="log" aria-live="polite" style="max-height:165px;overflow:auto;line-height:1.9;white-space:pre-wrap">${log.map(([t, m]) => `<div><span class="muted numeric">${new Date(t * 1000).toLocaleTimeString("vi-VN", { hour12: false })}</span> &nbsp; ${esc(m)}</div>`).join("")}</div></div>` : ""}</div></section>`;
}
function errorPanel(page, s) {
  const p = page === "payments" ? "pay" : "int";
  const scan = /scan|ảnh/i.test(s.loi);
  return `<section class="panel"><div class="panel-body"><div class="notice notice-danger" style="display:block" role="alert"><strong>Không kiểm tra được hồ sơ</strong><p style="overflow-wrap:anywhere">${esc(s.loi)}</p><div class="small">${scan ? "" : "Nếu file lỗi cấu trúc: mở trong Excel, lưu lại thành .xlsx rồi chọn lại. Nếu báo thiếu hợp đồng / BOQ: nạp vào CSDL trước."}</div></div><div class="toolbar" style="margin-top:16px">${s.file ? `<button class="btn btn-primary" data-action="${p}-run">${icon("refresh")} Chạy lại với ${esc(s.file.name)}</button>` : ""}<button class="btn btn-ghost" data-action="${p}-new">Chọn lại file</button></div></div></section>`;
}
function emptyPanel(page, stopped = false) {
  return `<div class="empty-state" style="padding:38px 24px"><div style="margin-bottom:12px;color:var(--muted,#768493)">${icon("file")}</div><h2>${stopped ? "Đã dừng lượt kiểm tra" : "Sẵn sàng kiểm tra hồ sơ"}</h2><p class="muted">${stopped ? "Chưa có kết quả cho lượt vừa dừng. Anh có thể chọn lại tệp và chạy một lượt mới." : page === "payments" ? "Chọn hợp đồng, ngày nghiệm thu và hồ sơ Excel để đi từ số đề nghị về căn cứ gốc." : "Chọn file Excel để rà soát công thức, liên kết ngoài và nguồn hình thành số đề nghị."}</p></div>`;
}
function historyPanel(page, s) {
  const ds = s.history || [];
  if (!ds.length) return "";
  const p = page === "payments" ? "pay" : "int";
  return `<section class="panel" style="margin-top:18px"><div class="panel-head"><h2>Kết quả đã lưu</h2><span class="small muted">${ds.length} lượt gần nhất · lưu trên máy này</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Thời gian</th><th>Hồ sơ</th>${page === "payments" ? "<th>Hợp đồng / đợt</th><th class=\"numeric\">Số đề nghị</th>" : ""}<th>Phát hiện</th>${page === "payments" ? "<th>CSDL</th>" : ""}<th></th></tr></thead><tbody>${ds
    .map((d) => {
      const dem = d.dem || {};
      return `<tr><td class="small">${esc(String(d.luc || "").replace("T", " "))}</td><td>${esc(d.tep)}</td>${page === "payments" ? `<td>${esc(d.hop_dong?.ma_hd || "")}${d.dot ? ` · Đợt ${esc(d.dot)}` : ""}<span class="secondary-cell">NT ${fmtDate(d.ngay_nghiem_thu)}</span></td><td class="numeric">${money(d.de_nghi)}</td>` : ""}<td>${dem.Cao ? badge(`${dem.Cao} cao`, "danger") : ""} ${badge(`${d.so_phat_hien || 0}`, d.so_phat_hien ? "warning" : "success")}</td>${page === "payments" ? `<td>${d.da_nap ? badge("Đã nạp", "success") : badge("Chưa nạp", "neutral")}</td>` : ""}<td><button class="btn btn-ghost" data-action="${p}-open" data-ma="${esc(d.ma)}" ${s.kq?.ma === d.ma ? "disabled" : ""}>${s.kq?.ma === d.ma ? "Đang xem" : "Mở"}</button></td></tr>`;
    })
    .join("")}</tbody></table></div></section>`;
}
function exportButtons(k) {
  const t = k?.tai;
  if (!t) return "";
  if (typeof t === "string") return `<a class="btn" href="${esc(t)}">${icon("download")} Tải báo cáo Excel</a>`;
  return `${t.lop2 ? `<a class="btn" href="${esc(t.lop2)}">${icon("download")} Báo cáo Lớp 2</a>` : ""}${t.lop1 ? `<a class="btn" href="${esc(t.lop1)}">${icon("download")} Báo cáo Lớp 1</a>` : ""}`;
}

// ================================================================== màn hình
export function renderPayments(ctx) {
  const s = st(ctx).payments;
  const k = s.kq;
  const actions = `<button class="btn btn-ghost" data-action="pay-new">${icon("plus")} Kiểm tra đợt mới</button>${s.view === "result" ? exportButtons(k) : ""}`;
  let content = "";
  if (s.view === "running") content = runningPanel("payments", s);
  else if (s.view === "error") content = errorPanel("payments", s);
  else if (s.view === "form" || !k) content = cheDo("payments") + paymentForm(ctx, s) + emptyPanel("payments", s.stopped);
  else {
    const ph = k.phat_hien || [];
    const rows = ph.filter((r) => s.layer === "all" || String(r.layer) === s.layer);
    const dl = k.dem_lop || {};
    const chua = k.phu_luc_chua_ap_dung || [];
    content =
      (s.formOpen ? cheDo("payments") : "") +
      scope(k) +
      paymentForm(ctx, s, s.formOpen) +
      summary(k) +
      (s.layer !== "1" ? lop2Grid(k) : "") +
      `<div class="toolbar" style="justify-content:space-between;flex-wrap:wrap;margin-bottom:16px"><div class="tabs" role="tablist" aria-label="Lớp kiểm tra">${[
        ["all", "Tất cả phát hiện", ph.length],
        ["1", "Lớp 1 · Toàn vẹn file", dl["1"] ?? ph.filter((f) => f.layer === 1).length],
        ["2", "Lớp 2 · HĐ/PL/BOQ", dl["2"] ?? ph.filter((f) => f.layer === 2).length],
      ]
        .map(
          ([key, label, count]) =>
            `<button role="tab" aria-selected="${s.layer === key}" class="tab ${s.layer === key ? "active" : ""}" data-action="pay-layer" data-layer="${key}">${label} <span class="small">${count}</span></button>`,
        )
        .join("")}</div>${k.da_nap ? badge(`Đã nạp đợt ${k.da_nap.dot} · ${String(k.da_nap.luc || "").replace("T", " ")}`, "success") : `<button class="btn btn-primary" data-action="pay-approve" ${s.nap ? "disabled" : ""}>${icon("database")} Nạp đợt đã duyệt</button>`}</div>${
        s.layer === "2"
          ? `<div class="notice notice-info" style="display:block;margin-bottom:16px">Đối chiếu theo ngày nghiệm thu <strong>${fmtDate(k.ngay_nghiem_thu)}</strong> với BOQ hiệu lực${(k.phu_luc_ap_dung || []).length ? ` (gốc + ${esc(k.phu_luc_ap_dung.map((p) => `${p.so_pl} từ ${fmtDate(p.ngay_hieu_luc)}`).join(", "))})` : " (BOQ gốc, chưa có phụ lục áp dụng)"}.${chua.length ? ` <strong>${esc(chua.map((p) => `${p.so_pl} hiệu lực ${fmtDate(p.ngay_hieu_luc)}`).join(", "))} chưa áp dụng</strong> cho kỳ này.` : ""}${k.dot_truoc ? ` Lũy kế kỳ trước lấy từ đợt ${esc(k.dot_truoc)} đã nạp.` : ""}</div>`
          : ""
      }${findingsTable(rows, s, "payments")}${s.layer === "1" ? checksGrid(k, "payments") : ""}${tracePanel(k)}`;
  }
  return (
    header("Kiểm tra đợt thanh toán", "Review số đề nghị theo hai lớp: toàn vẹn Excel và đối chiếu HĐ, phụ lục, BOQ.", actions) +
    `<div class="small muted" style="margin:0 0 16px">${s.view === "result" && k ? `Kết quả ${k.dot ? `đợt ${esc(k.dot)}` : ""} · ${esc(k.hop_dong?.ma_hd || "")} · Kiểm tra lúc ${esc(String(k.luc || "").replace("T", " "))}` : "Kiểm tra hồ sơ thanh toán · Dữ liệu trên máy này"}</div>` +
    content +
    (s.view !== "running" ? historyPanel("payments", s) : "")
  );
}

export function renderIntegrity(ctx) {
  const s = st(ctx).integrity;
  const k = s.kq;
  const actions = `<button class="btn btn-ghost" data-action="int-new">${icon("plus")} Kiểm tra file mới</button>${s.view === "result" ? exportButtons(k) : ""}`;
  let content = "";
  if (s.view === "running") content = runningPanel("integrity", s);
  else if (s.view === "error") content = errorPanel("integrity", s);
  else if (s.view === "form" || !k)
    content = `${cheDo("integrity")}<div class="notice notice-warning" style="display:block;margin-bottom:16px"><div><strong>Chỉ dùng khi hợp đồng CHƯA có trong CSDL.</strong> Chế độ này chỉ kiểm tra tính toàn vẹn của file Excel (Lớp 1); không so với giá trị HĐ, đơn giá / khối lượng BOQ, tỷ lệ thanh toán, phụ lục và không nạp được đợt vào CSDL. Hợp đồng đã có trong CSDL thì chọn <button class="link-btn" data-route="payments" style="display:inline;min-height:0;padding:0">Đủ hai lớp</button> — đã gồm cả Lớp 1.</div></div><section class="panel"><div class="panel-body">${fileUpload("integrity-file", ".xlsx,.xlsm,.xls", "Excel .xlsx, .xlsm, .xls · Hợp đồng chưa có trong CSDL · chỉ Lớp 1 (toàn vẹn file)")}<div class="small muted" style="margin-top:8px">${s.file ? `Đã chọn: <strong>${esc(s.file.name)}</strong>. ` : ""}File được lưu trên máy này để truy vết; không gửi ra ngoài.</div><div class="toolbar" style="justify-content:space-between;margin-top:16px;align-items:flex-end"><label class="field" style="min-width:280px">Ô số đề nghị (không bắt buộc)<input type="text" data-check-field="o" value="${esc(s.o)}" placeholder="Ví dụ: 0.Giấy ĐNTT!F16 — để trống: tự tìm"></label><button class="btn btn-primary" data-action="int-run" ${s.file ? "" : "disabled"}>${icon("play")} Kiểm tra file</button></div></div></section>${emptyPanel("integrity", s.stopped)}`;
  else
    content = `<section class="panel" style="margin-bottom:18px"><div class="panel-body" style="display:flex;align-items:center;justify-content:space-between;gap:16px"><div><strong>${esc(k.tep)}</strong><div class="small muted" style="margin-top:5px">${esc(k.so_sheet ?? "?")} sheet · ${(k.cay || []).length} ô nguồn của số đề nghị · Kiểm tra lúc ${esc(String(k.luc || "").replace("T", " "))}</div></div><button class="btn btn-ghost" data-action="int-new">${icon("upload")} Kiểm tra file khác</button></div></section><div class="notice notice-warning" style="display:block;margin-bottom:18px"><div><strong style="display:inline">Kết quả chỉ toàn vẹn file (Lớp 1)</strong> — hợp đồng chưa có trong CSDL nên chưa đối chiếu giá trị HĐ, đơn giá, khối lượng BOQ, tỷ lệ thanh toán. Khi đã nạp hợp đồng, chạy lại ở chế độ <button class="link-btn" data-route="payments" style="display:inline;min-height:0;padding:0">Đủ hai lớp</button> để đối chiếu và nạp đợt.</div></div>${summary(k, true)}${findingsTable(k.phat_hien || [], s, "integrity")}${checksGrid(k, "integrity")}${tracePanel(k)}`;
  return (
    header("Kiểm tra đợt thanh toán", "Chế độ chỉ toàn vẹn file (Lớp 1) — dành cho hồ sơ của hợp đồng CHƯA có trong CSDL.", actions) +
    content +
    (s.view !== "running" ? historyPanel("integrity", s) : "")
  );
}

function evidence(ctx, page, row) {
  const k = st(ctx)[page].kq;
  ctx.openDrawer({
    title: `${row.id} · ${String(row.title).slice(0, 80)}`,
    body: `<div class="toolbar" style="justify-content:space-between;margin-bottom:16px">${pill(row.level)}<span class="small muted">Lớp ${row.layer}${row.so_o > 1 ? ` · ${row.so_o} ô cùng lỗi` : ""}</span></div><section class="panel" style="margin-bottom:16px"><div class="panel-head"><h3 style="margin:0;font-size:15px">Vị trí phát hiện</h3></div><div class="panel-body"><strong>${row.sheet ? `${esc(row.sheet)}!${esc(row.cell)}` : esc(row.cell || "—")}</strong><div class="small muted" style="margin-top:5px">${esc(k.tep)}</div>${row.item ? `<div style="margin-top:14px"><span class="small muted">Hạng mục</span><p style="margin:5px 0">${esc(row.item)}</p></div>` : ""}${row.formula || row.value ? `<div style="margin-top:14px"><span class="small muted">Công thức / giá trị tại ô</span><div style="padding:12px;margin-top:6px;background:var(--surface-soft,#f4f6f8);border:1px solid var(--border,#dce2e7);border-radius:6px;overflow-wrap:anywhere;font-variant-numeric:tabular-nums">${esc(row.formula || "")}${row.formula && row.value ? `<br><span class="muted">= ${esc(row.value)}</span>` : esc(row.value || "")}</div></div>` : ""}${row.detail ? `<p class="small" style="margin-top:14px;overflow-wrap:anywhere">${esc(row.detail)}</p>` : ""}</div></section><section class="panel" style="margin-bottom:16px"><div class="panel-head"><h3 style="margin:0;font-size:15px">${row.layer === 2 ? "Đối chiếu BOQ / phụ lục" : "Đối chiếu nguồn trong Excel"}</h3></div><div class="panel-body"><div class="grid-2"><div><div class="small muted">Trong hồ sơ</div><strong style="display:block;margin-top:6px;overflow-wrap:anywhere">${val(row.actual)}</strong></div><div><div class="small muted">${row.layer === 2 ? "Căn cứ cần đối chiếu" : "Phép kiểm tra"}</div><strong style="display:block;margin-top:6px">${val(row.expected)}</strong></div></div><hr style="border:0;border-top:1px solid var(--border,#dce2e7);margin:16px 0"><div class="small muted">Nguồn: ${esc(row.source)}</div>${row.reference ? `<div class="small muted" style="margin-top:7px">${esc(row.reference)}</div>` : ""}${k.ngay_nghiem_thu ? `<div class="small muted" style="margin-top:7px">Ngày áp dụng: ${fmtDate(k.ngay_nghiem_thu)}</div>` : ""}${row.layer === 2 ? '<div class="toolbar" style="margin-top:12px"><button class="btn" data-action="pay-open-boq">Mở BOQ hiệu lực</button><button class="btn btn-ghost" data-action="pay-open-appendices">Xem phụ lục</button></div>' : ""}</div></section><div class="notice notice-warning" style="display:block;margin-bottom:18px"><strong>${typeof row.amount === "number" ? `Ảnh hưởng ước tính: ${money(row.amount)} đồng` : "Cần bổ sung căn cứ"}</strong><p style="margin-bottom:0">${esc(row.conclusion)}</p></div><section class="panel"><div class="panel-head"><h3 style="margin:0;font-size:15px">Cây hình thành số đề nghị</h3></div><div class="panel-body">${traceTree(k.cay, true)}</div></section>`,
  });
}

export function handleCheckAction(action, el, ctx) {
  const ck = st(ctx);
  const m = action.match(/^(pay|int)-(.+)$/);
  const page = m ? (m[1] === "pay" ? "payments" : "integrity") : ctx.state.view;
  const s = ck[page] || ck.payments;
  const sub = m ? m[2] : action;
  if (!m && action !== "check-detail") return false;
  switch (sub) {
    case "layer":
      s.layer = el.dataset.layer;
      s.severity = "all";
      ctx.render();
      return true;
    case "form":
      s.formOpen = !s.formOpen;
      ctx.render();
      return true;
    case "new":
      s.view = "form";
      s.stopped = false;
      s.kq = null;
      s.formOpen = true;
      ctx.render();
      return true;
    case "run":
      run(ctx, page);
      return true;
    case "stop":
      if (s.job)
        post(`/api/viec/${encodeURIComponent(s.job.id)}/dung`)
          .then(() => ctx.toast("Đã gửi lệnh dừng — việc dừng sau bước đang chạy.", "warning"))
          .catch((e) => ctx.toast(e.message, "danger"));
      return true;
    case "open":
      openSaved(ctx, page, el.dataset.ma).then(() => {
        ctx.render();
        window.scrollTo(0, 0);
      });
      return true;
    case "evidence": {
      const row = (s.kq?.phat_hien || []).find((r) => r.id === el.dataset.id);
      if (row) evidence(ctx, page, row);
      return true;
    }
    case "open-boq":
    case "open-appendices": {
      const hd = ck.payments.kq?.hop_dong?.ma_hd;
      const ui = ctx.state.hd;
      if (ui && hd) {
        if (sub === "open-boq") {
          ui.boqContract = hd;
          ui.boqDate = ck.payments.kq.ngay_nghiem_thu || ui.boqDate;
          ui.boqView = "effective";
          ui.boq = null;
        } else {
          ui.appendixContract = hd;
          ui.appendixDetail = null;
        }
      }
      ctx.navigate(sub === "open-boq" ? "boq" : "appendices", { ma: hd, ngay: ck.payments.kq?.ngay_nghiem_thu });
      return true;
    }
    case "check-detail": {
      const r = (s.kq?.bang_k || []).find((x) => x.code === el.dataset.id);
      if (r)
        ctx.openDrawer({
          title: `${r.code} · ${r.ten}`,
          body: `<div style="margin-bottom:16px">${pill(r.ket_qua)}</div><p>${esc(r.chi_tiet)}</p><div class="notice notice-info" style="display:block">Đạt một phép kiểm tra không thay thế việc review các phát hiện còn lại.</div>${r.code === "K5" || r.code === "K6" ? `<div style="margin-top:18px">${traceTree(s.kq.cay)}</div>` : ""}`,
        });
      return true;
    }
    case "hm-doi": {
      const hs = hangMuc.s || (hangMuc.s = {});
      (hs.doi || (hs.doi = {}))[el.dataset.dong] = true;
      ctx.render();
      return true;
    }
    case "hm-ghep": {
      const k = s.kq;
      const dong = el.dataset.dong;
      const inp = document.querySelector(`[data-hm-ma="${CSS.escape(dong)}"]`);
      const ma = (inp?.value || "").trim().toUpperCase();
      if (!k || !ma) return ctx.toast("Nhập hoặc chọn Mã HM để ghép.", "warning"), true;
      post(`/api/kiem_tra/kiem_tra_dot/${encodeURIComponent(k.ma)}/ghep`, { dong: Number(dong), ma_hm: ma })
        .then((r) => {
          const h = (k.doi_chieu_hm || []).find((x) => String(x.dong) === String(dong));
          if (h) h.ghep_tay = r.ma_hm;
          k.ghep_moi = [...new Set([...(k.ghep_moi || []), String(dong)])];
          ctx.toast(`Dòng ${dong} → ${r.ma_hm} (${String(r.ten_boq || "").slice(0, 50)}). Ghép xong các dòng thì bấm Chạy lại.`, "success");
          ctx.render();
        })
        .catch((e) => ctx.toast(e.message, "danger"));
      return true;
    }
    case "rerun": {
      const k = s.kq;
      if (!k) return true;
      post(`/api/kiem_tra/kiem_tra_dot/${encodeURIComponent(k.ma)}/chay_lai`, {})
        .then((v) => {
          ctx.refreshJobs?.();
          follow(ctx, page, v);
        })
        .catch((e) => ctx.toast(e.message, "danger"));
      return true;
    }
    case "approve": {
      const k = s.kq;
      if (!k || k.da_nap) return true;
      const dem = k.dem || {};
      const napVao = async (body) => {
        s.nap = true;
        ctx.render();
        ctx.toast("Đang nạp đợt vào CSDL…", "info");
        try {
          const r = await post(`/api/kiem_tra/kiem_tra_dot/${encodeURIComponent(k.ma)}/nap`, body);
          ctx.toast(`Đã nạp đợt ${body.dot}: ${r.so_hang_muc} hạng mục${r.khong_khop?.length ? `, ${r.khong_khop.length} dòng không khớp BOQ` : ""}.`, r.khong_khop?.length ? "warning" : "success");
          await openSaved(ctx, "payments", k.ma);
          await loadHistory(ctx, "payments");
        } catch (e) {
          if (e instanceof LoiApi && e.status === 409 && /đã có trong CSDL/i.test(e.message) && !body.ly_do_nap_lai) {
            s.nap = false;
            ctx.render();
            ctx.openModal({
              title: `Đợt ${body.dot} đã có trong CSDL`,
              body: `<div class="notice notice-danger" style="display:block">${esc(e.message.replace(/ Nạp lại thì thêm --ly-do\.?/, ""))}</div><p>Nạp lại sẽ <strong>thay</strong> số liệu đợt ${esc(body.dot)} đang có bằng hồ sơ này (${esc(k.tep)}). Thao tác ghi nhật ký kèm lý do. Nếu đây là đợt mới, bấm Quay lại và sửa số đợt.</p>`,
              confirmLabel: "Nạp lại, thay đợt cũ",
              danger: true,
              requireReason: true,
              reasonLabel: "Lý do nạp lại",
              onConfirm: (reason) => napVao({ ...body, ly_do_nap_lai: reason }),
            });
            return;
          }
          ctx.toast(e.message, "danger");
        }
        s.nap = false;
        ctx.render();
      };
      ctx.openModal({
        title: "Nạp đợt đã duyệt vào CSDL",
        confirmLabel: "Xác nhận nạp đợt",
        body: `<p>${esc(k.hop_dong?.ma_hd)} · ${esc(k.tep)} · Ngày nghiệm thu <strong>${fmtDate(k.ngay_nghiem_thu)}</strong></p><div class="grid-2" style="margin:16px 0"><label class="field">Số đợt<input data-modal-field="dot" type="number" min="1" value="${esc(k.dot || "")}" required></label><label class="field">Ngày nhận hồ sơ (không bắt buộc)<input data-modal-field="ngay_hs" type="date"></label></div><div class="stat-strip" style="margin:16px 0;grid-template-columns:1fr"><div class="stat"><div class="stat-label">Số đề nghị thanh toán</div><div class="stat-value numeric" style="font-size:22px">${money(k.de_nghi)} ₫</div></div></div>${k.so_phat_hien ? `<div class="notice notice-warning" style="display:block"><strong>Hồ sơ đang có ${k.so_phat_hien} phát hiện cần xem</strong><p>${dem.Cao || 0} cao, ${dem["Trung bình"] || 0} trung bình, ${dem["Thấp"] || 0} thấp. Xác nhận đã review các phát hiện và hồ sơ đã được duyệt trước khi nạp.</p></div>` : ""}<p class="small muted">Nạp khối lượng kỳ này / lũy kế theo hạng mục BOQ vào CSDL; đợt sau sẽ đối chiếu lũy kế kỳ trước với số này.</p>`,
        requireReason: !!dem.Cao,
        reasonLabel: "Ghi chú duyệt (bắt buộc khi còn phát hiện mức cao)",
        onConfirm: (reason, vals) => {
          const dot = Number(vals?.dot) || Number(k.dot);
          if (!dot) return ctx.toast("Nhập số đợt.", "warning");
          napVao({ dot, ngay_nhan_hs: vals?.ngay_hs || null, ghi_chu: reason || "" });
        },
      });
      return true;
    }
    default:
      return false;
  }
}

export function handleCheckChange(el, ctx) {
  const ck = st(ctx);
  const page = ctx.state.view;
  if (!["payments", "integrity"].includes(page)) return false;
  const s = ck[page];
  if (el.id === "payments-file" || el.id === "integrity-file") {
    s.file = el.files?.[0] || null;
    s.stopped = false;
    ctx.render();
    return true;
  }
  if (el.matches?.("[data-hm-loc]")) {
    (hangMuc.s || (hangMuc.s = {})).loc = el.value;
    ctx.render();
    return true;
  }
  const f = el.dataset?.checkField;
  if (!f) return false;
  s[f] = el.value;
  if (f === "severity" || f === "hd") ctx.render();
  return true;
}
