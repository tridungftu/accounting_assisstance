"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const token = document.querySelector('meta[name="ktt-token"]').content;
  const pages = {nhap: "Nhập dữ liệu", hoso: "Hồ sơ đã nhận", hopdong: "Hợp đồng & lịch thu", khoanvay: "Khoản vay", nghiemthu: "Hồ sơ nghiệm thu", khanang: "Khả năng xử lý", huongdan: "Hướng dẫn sử dụng", mau: "Thử dữ liệu mẫu"};
  const extensions = new Set(["pdf", "xlsx", "xls", "xml", "csv", "tsv", "json", "txt", "zip"]);
  const limit = 50 * 1024 * 1024;
  let state = null, queue = [], busy = false, stopped = false, selected = null, page = 1, toastTimer;
  const node = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  };
  const size = n => n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toLocaleString("vi-VN", {maximumFractionDigits: 1})} KB` : `${(n / 1048576).toLocaleString("vi-VN", {maximumFractionDigits: 1})} MB`;
  const date = value => new Date(value).toLocaleString("vi-VN", {timeZone: "Asia/Ho_Chi_Minh", dateStyle: "short", timeStyle: "short"});
  const ext = name => name.split(".").pop().toLowerCase();
  function toast(message, error = false) {
    $("toast").textContent = message;
    $("toast").className = "toast" + (error ? " error" : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $("toast").classList.add("hidden"), error ? 9000 : 4500);
  }
  async function request(path, options = {}) {
    if (stopped) throw new Error("Ứng dụng đã dừng. Mở lại bằng file MỞ BẢN DEMO.cmd.");
    let response;
    try { response = await fetch(path, {...options, headers: {"X-KTT-Token": token, ...options.headers}, cache: "no-store"}); }
    catch (_) { throw new Error("Mất kết nối với ứng dụng trên máy. Mở lại file MỞ BẢN DEMO.cmd rồi tải lại trang; các tệp đã lưu vẫn được giữ."); }
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.message || `Không hoàn tất yêu cầu (${response.status}).`);
    }
    return response;
  }
  function route() {
    const key = location.hash.slice(1) in pages ? location.hash.slice(1) : "nhap";
    for (const name of Object.keys(pages)) $("page-" + name).classList.toggle("hidden", name !== key);
    document.querySelectorAll("[data-page]").forEach(el => {
      el.classList.toggle("active", el.dataset.page === key);
      if (el.dataset.page === key) el.setAttribute("aria-current", "page"); else el.removeAttribute("aria-current");
    });
    $("breadcrumb").textContent = pages[key];
    document.title = "Hỗ trợ kế toán · " + pages[key];
  }
  function empty(message, hint) {
    const box = node("div", undefined, "empty-state"), info = node("div");
    info.append(node("strong", message), node("p", hint));
    box.append(node("span", "▤", "empty-symbol"), info);
    return box;
  }
  function fileName(file) {
    const box = node("div", undefined, "name-cell"), info = node("div", undefined, "file-info");
    info.append(node("strong", file.name), node("small", `${size(file.bytes)} · ${file.entity}`));
    box.append(node("span", ext(file.name).toUpperCase().slice(0, 5), "file-icon"), info);
    return box;
  }
  function fileTable(files) {
    if (!files.length) return empty("Chưa có hồ sơ phù hợp", "Chọn tệp để lưu hồ sơ, hoặc điều chỉnh bộ lọc tìm kiếm.");
    const wrap = node("div", undefined, "table-wrap"), table = node("table"), head = node("thead"), row = node("tr");
    for (const label of ["Tệp gốc", "Loại dữ liệu", "Kỳ dữ liệu", "Trạng thái", ""]) row.append(node("th", label));
    head.append(row); table.append(head);
    const body = node("tbody");
    for (const file of files) {
      const tr = node("tr"), nameCell = node("td"), statusCell = node("td"), actionCell = node("td");
      nameCell.append(fileName(file)); statusCell.append(node("span", "Chờ bộ đọc", "pill amber"));
      const action = node("button", "Chi tiết ↗", "link-button");
      action.setAttribute("aria-label", "Chi tiết " + file.name);
      action.addEventListener("click", () => detail(file)); actionCell.append(action);
      tr.append(nameCell, node("td", file.source_label), node("td", file.period), statusCell, actionCell); body.append(tr);
    }
    table.append(body); wrap.append(table); return wrap;
  }
  function renderFiles() {
    if (!state) return;
    const search = $("search-files").value.trim().toLocaleLowerCase("vi-VN"), source = $("filter-source").value;
    const files = state.files.filter(f => (!source || f.source === source) && `${f.name} ${f.entity} ${f.period} ${f.note}`.toLocaleLowerCase("vi-VN").includes(search));
    const count = Math.max(1, Math.ceil(files.length / 25)); page = Math.min(page, count);
    $("all-files").replaceChildren(fileTable(files.slice((page - 1) * 25, page * 25)));
    $("page-info").textContent = `${files.length} hồ sơ · Trang ${page}/${count}`;
    $("previous-page").disabled = page <= 1; $("next-page").disabled = page >= count;
    $("recent-files").replaceChildren(state.files.length ? fileTable(state.files.slice(0, 5)) : empty("Kho hồ sơ đang trống", "Tệp đầu tiên Anh lưu sẽ xuất hiện ở đây."));
  }
  function renderDemoHistory() {
    const count = Object.values(state.demo.documents_by_kind).reduce((a, b) => a + b, 0);
    $("demo-count").textContent = `${count} chứng từ mô phỏng`;
    const box = $("demo-history");
    if (!state.demo_attempts.length) { box.replaceChildren(empty("Chưa nạp dữ liệu mẫu", "Bấm Nạp mẫu sao kê để kiểm tra luồng nạp.")); return; }
    const wrap = node("div", undefined, "table-wrap"), table = node("table"), head = node("tr");
    for (const label of ["Nguồn mẫu", "Kết quả", "Chứng từ mới", "Trùng đã bỏ qua"]) head.append(node("th", label));
    const thead = node("thead"); thead.append(head); table.append(thead);
    const body = node("tbody");
    for (const r of state.demo_attempts) {
      const row = node("tr");
      row.append(node("td", state.sources[r.source] || "Tệp mẫu"), node("td", r.state === "COMMITTED" ? "Đã nạp mô phỏng" : "Từ chối nạp"), node("td", r.inserted_documents || 0), node("td", r.duplicate_documents || 0));
      body.append(row);
    }
    table.append(body); wrap.append(table); box.replaceChildren(wrap);
  }
  async function refresh() {
    try {
      state = await (await request("/api/state")).json();
      $("connection-label").textContent = "Đang chạy trên máy này";
      $("version").textContent = "v" + state.version;
      $("storage-path").textContent = state.storage_path;
      for (const id of ["metric-files", "metric-waiting", "nav-count"]) $(id).textContent = state.total.toLocaleString("vi-VN");
      $("metric-size").textContent = size(state.total_bytes);
      $("fatal-error").classList.toggle("hidden", !state.damaged_receipts);
      $("fatal-error").textContent = state.damaged_receipts ? `${state.damaged_receipts} phiếu tiếp nhận không đọc được. Giữ nguyên thư mục kho để kiểm tra và phục hồi; chưa thể coi danh sách này là đầy đủ.` : "";
      renderFiles(); renderDemoHistory();
    } catch (error) {
      $("connection-label").textContent = "Chưa kết nối";
      $("fatal-error").textContent = error.message; $("fatal-error").classList.remove("hidden"); throw error;
    }
  }
  function detail(file) {
    selected = file;
    const fields = [["Loại dữ liệu", file.source_label], ["Pháp nhân / kỳ", `${file.entity} / ${file.period}`], ["Dung lượng", size(file.bytes)], ["Nhận lúc (VN)", date(file.received_at)], ["Trạng thái", "Đã nhận · chờ bộ đọc; chưa chuẩn hóa, chưa ghi sổ"], ["Ghi chú", file.note || "Chưa có"], ["Đường dẫn gốc", file.original_relative_path || "Chọn tệp riêng lẻ"], ["Thời điểm biết", "Chưa xác nhận — không suy từ ngày nhận tệp"], ["SHA-256", file.sha256]];
    const list = node("dl", undefined, "detail-grid");
    for (const [key, value] of fields) list.append(node("dt", key), node("dd", value, key === "SHA-256" ? "checksum" : ""));
    $("file-detail").replaceChildren(node("p", file.name, "detail-name"), list);
    $("file-dialog").showModal();
  }
  async function download(path, name) {
    const blob = await (await request(path)).blob(), url = URL.createObjectURL(blob), link = node("a");
    link.href = url; link.download = name; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }
  function controls() {
    for (const id of ["choose-folder", "clear-queue", "file-input", "folder-input", "source", "entity", "period", "note", "seed-bank", "seed-junsky", "demo-input", "stop-app"]) $(id).disabled = busy || stopped;
    $("save-files").disabled = busy || stopped || !queue.length;
    $("validate-demo").disabled = $("ingest-demo").disabled = busy || stopped || !$("demo-input").files.length;
    $("dropzone").setAttribute("aria-disabled", String(busy || stopped));
  }
  function renderQueue() {
    $("queue-area").classList.toggle("hidden", !queue.length);
    $("queue-title").textContent = `${queue.length} tệp đã chọn`;
    $("file-queue").replaceChildren();
    for (const item of queue) {
      const li = node("li"), info = node("div", undefined, "file-info"), remove = node("button", "×", "icon-button");
      info.append(node("strong", item.file.webkitRelativePath || item.file.name), node("small", item.error || size(item.file.size)));
      if (item.error) info.lastChild.classList.add("queue-error");
      remove.setAttribute("aria-label", "Bỏ chọn " + item.file.name); remove.disabled = busy || stopped;
      remove.addEventListener("click", () => { queue = queue.filter(q => q !== item); renderQueue(); });
      li.append(node("span", ext(item.file.name).toUpperCase(), "file-icon"), info, remove); $("file-queue").append(li);
    }
    controls();
  }
  function addFiles(files) {
    if (busy || stopped) return;
    let rejected = 0, firstReason = "";
    for (const file of files) {
      const error = !extensions.has(ext(file.name)) ? "định dạng chưa hỗ trợ" : !file.size ? "tệp rỗng" : file.size > limit ? "vượt 50 MB" : queue.length >= 300 ? "mỗi lượt tối đa 300 tệp" : "";
      if (error) { rejected++; if (!firstReason) firstReason = `${file.name}: ${error}`; continue; }
      // Queue identity is only a convenience. The server deduplicates actual bytes.
      const key = JSON.stringify([file.name, file.webkitRelativePath, file.size, file.lastModified]);
      if (!queue.some(q => q.key === key)) queue.push({key, file, error: ""});
    }
    renderQueue();
    $("upload-status").textContent = rejected ? `Bỏ qua ${rejected} tệp (${firstReason}). Còn ${queue.length} tệp để lưu.` : `Đã chọn ${queue.length} tệp. Kiểm tra loại dữ liệu, pháp nhân và kỳ trước khi lưu.`;
    if (rejected) toast(`${rejected} tệp chưa được chọn. ${firstReason}.`, true);
  }
  async function saveFiles(event) {
    event.preventDefault(); if (busy || stopped || !queue.length) return;
    const metadata = {source: $("source").value, entity: $("entity").value.trim(), period: $("period").value, note: $("note").value};
    busy = true; renderQueue(); $("upload-progress").classList.remove("hidden"); $("upload-progress").value = 0;
    let saved = 0, duplicates = 0, failed = 0;
    const pending = [...queue];
    for (let index = 0; index < pending.length; index++) {
      const item = pending[index], file = item.file;
      $("upload-status").textContent = `Đang lưu ${index + 1}/${pending.length}: ${file.name}`;
      try {
        const info = {...metadata, name: file.name, relative_path: file.webkitRelativePath || "", modified_at: file.lastModified};
        const result = await (await request("/api/upload", {method: "POST", headers: {"X-File-Info": encodeURIComponent(JSON.stringify(info))}, body: file})).json();
        if (result.duplicate) duplicates++; else saved++;
        queue = queue.filter(q => q !== item);
      } catch (error) { item.error = error.message; failed++; }
      $("upload-progress").value = Math.round((index + 1) * 100 / pending.length); renderQueue();
    }
    busy = false; renderQueue();
    const message = `Đã lưu ${saved} hồ sơ mới; ${duplicates} tệp trùng đã có; ${failed} tệp chưa lưu.`;
    $("upload-status").textContent = message + (failed ? " Xem lỗi dưới tên tệp, sửa rồi thử lại." : " Hồ sơ đang chờ bộ đọc.");
    toast(message, failed > 0);
    await refresh().catch(() => {});
  }
  function demoReport(report, committed) {
    const box = $("demo-result"), ok = report.state === "COMMITTED" || report.state === "VALIDATED";
    box.replaceChildren(node("h2", ok ? (committed ? "Đã nạp vào kho mô phỏng" : "Tệp mẫu hợp lệ — chưa nạp") : "Chưa nạp: tệp mẫu chưa hợp lệ"));
    const metrics = node("div", undefined, "demo-results-metrics");
    const values = committed ? [["Chứng từ mới", report.inserted_documents || 0], ["Trùng đã bỏ qua", report.duplicate_documents || 0]] : [["Dòng đầu vào", report.input_records || 0]];
    for (const [label, value] of values) { const item = node("div"); item.append(node("strong", value), node("span", label)); metrics.append(item); }
    box.append(metrics, node("p", "Kết quả chỉ thuộc kho PLHN_FIXTURE, không chứng minh dữ liệu thật đã được đọc hoặc ghi sổ."));
    if (report.issues?.length) {
      const list = node("ul"); for (const issue of report.issues) list.append(node("li", `${issue.code}: ${issue.message || issue.detail || "Kiểm tra cấu trúc tệp mẫu."}`)); box.append(list);
    }
    box.classList.remove("hidden");
  }
  async function demoRun(source, committed = true) {
    if (busy || stopped) return;
    busy = true; controls();
    try {
      const file = source ? await (await request("/api/sample?source=" + source)).blob() : $("demo-input").files[0];
      if (!file || file.size > limit) throw new Error("Chọn tệp JSON mô phỏng tối đa 50 MB.");
      const report = await (await request(committed ? "/api/demo/ingest" : "/api/demo/validate", {method: "POST", body: file, headers: {"X-File-Name": encodeURIComponent(source ? source + "_MO_PHONG.json" : file.name)}})).json();
      demoReport(report, committed); await refresh();
      toast(report.state === "REJECTED" ? "Mẫu chưa hợp lệ. Xem kết quả kiểm tra." : committed ? "Đã hoàn tất nạp mẫu." : "Đã kiểm tra, chưa nạp vào kho.", report.state === "REJECTED");
    } catch (error) {
      $("demo-result").replaceChildren(node("h2", "Chưa hoàn tất thao tác"), node("p", error.message));
      $("demo-result").classList.remove("hidden"); toast(error.message, true);
    } finally { busy = false; controls(); }
  }
  const now = new Date(); $("period").value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  $("open-demo").addEventListener("click", () => { location.hash = "mau"; });
  window.addEventListener("hashchange", route);
  $("dropzone").addEventListener("click", () => { if (!busy && !stopped) $("file-input").click(); });
  $("dropzone").addEventListener("keydown", event => { if (["Enter", " "].includes(event.key)) { event.preventDefault(); if (!busy && !stopped) $("file-input").click(); } });
  $("choose-folder").addEventListener("click", () => $("folder-input").click());
  for (const id of ["file-input", "folder-input"]) $(id).addEventListener("change", event => { addFiles(event.target.files); event.target.value = ""; });
  for (const kind of ["dragover", "drop"]) window.addEventListener(kind, event => event.preventDefault());
  $("dropzone").addEventListener("dragover", () => { if (!busy && !stopped) $("dropzone").classList.add("drag-over"); });
  $("dropzone").addEventListener("dragleave", () => $("dropzone").classList.remove("drag-over"));
  $("dropzone").addEventListener("drop", event => { $("dropzone").classList.remove("drag-over"); addFiles(event.dataTransfer.files); });
  $("clear-queue").addEventListener("click", () => { queue = []; renderQueue(); $("upload-status").textContent = "Chọn tệp để bắt đầu."; });
  $("intake-form").addEventListener("submit", saveFiles);
  for (const id of ["search-files", "filter-source"]) $(id).addEventListener("input", () => { page = 1; renderFiles(); });
  $("previous-page").addEventListener("click", () => { page--; renderFiles(); });
  $("next-page").addEventListener("click", () => { page++; renderFiles(); });
  $("refresh-files").addEventListener("click", () => refresh().then(() => toast("Đã cập nhật danh sách hồ sơ.")).catch(error => toast(error.message, true)));
  $("close-detail").addEventListener("click", () => $("file-dialog").close());
  $("download-file").addEventListener("click", async () => {
    if (!selected) return; $("download-file").disabled = true;
    try { await download(`/api/files/${selected.id}/download`, selected.name); toast("Đã chuẩn bị tệp gốc. Xem mục Tải xuống của trình duyệt."); }
    catch (error) { toast(error.message, true); } finally { $("download-file").disabled = false; }
  });
  $("seed-bank").addEventListener("click", () => demoRun("sao_ke"));
  $("seed-junsky").addEventListener("click", () => demoRun("junsky_xuat"));
  $("download-bank").addEventListener("click", () => download("/api/sample?source=sao_ke", "sao_ke_MO_PHONG.json").catch(error => toast(error.message, true)));
  $("demo-input").addEventListener("change", controls);
  $("validate-demo").addEventListener("click", () => demoRun(null, false));
  $("ingest-demo").addEventListener("click", () => demoRun(null, true));
  $("stop-app").addEventListener("click", () => $("stop-dialog").showModal());
  $("cancel-stop").addEventListener("click", () => $("stop-dialog").close());
  $("confirm-stop").addEventListener("click", async () => {
    $("confirm-stop").disabled = true;
    try {
      await request("/api/shutdown", {method: "POST", body: "{}"}); stopped = true;
      $("stop-dialog").close(); document.body.classList.add("stopped"); controls(); renderQueue();
      $("connection-label").textContent = "Ứng dụng đã dừng";
      $("fatal-error").textContent = "Ứng dụng đã dừng, hồ sơ đã lưu được giữ nguyên. Mở lại bằng file MỞ BẢN DEMO.cmd rồi tải lại trang.";
      $("fatal-error").classList.remove("hidden");
    } catch (error) { toast(error.message, true); } finally { $("confirm-stop").disabled = false; }
  });
  // ---- Hồ sơ nghiệm thu (M4 bridge DEMO). Mọi chuỗi nguồn hiển thị bằng textContent. ----
  let nt = null, ntSelected = null;
  // Tiền từ máy chủ là chuỗi số nguyên: định dạng bằng chuỗi, không qua Number (giữ đủ chữ số kể cả > 2^53).
  const vnd = v => {
    if (v === null || v === undefined || v === "") return "Chưa xác nhận / không đọc được";
    const text = String(v);
    if (!/^-?\d+$/.test(text)) return text;
    const sign = text.startsWith("-") ? "-" : "", digits = sign ? text.slice(1) : text;
    return sign + digits.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " VND";
  };
  const nguonLabel = {DA_NAP_CSDL_REVIEW: "Đã nạp vào phần mềm review", CHUA_NAP_CSDL_REVIEW: "Chưa nạp vào phần mềm review", BANG_CHUNG_NAP_KHONG_HOP_LE: "Bằng chứng nạp không hợp lệ — chờ"};
  const ntState = {WAIT: "Chờ xác nhận", APPROVE: "Đã đồng ý", SKIP: "Bỏ qua", EXPORTED: "Đã xuất file soát"};
  async function ntPost(path, body) {
    return (await request(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})).json();
  }
  function ntField(label, input) { const box = node("div"), l = node("label", label); l.htmlFor = input.id; box.append(l, input); return box; }
  function ntSelect(id, values, current) {
    const sel = node("select"); sel.id = id; sel.append(node("option", "— chọn —"));
    sel.firstChild.value = "";
    for (const v of values) { const opt = node("option", v); opt.value = v; if (v === current) opt.selected = true; sel.append(opt); }
    return sel;
  }
  function ntInput(id, value, type = "text") { const el = node("input"); el.id = id; el.type = type; el.value = value ?? ""; el.autocomplete = "off"; return el; }
  function ntTable(headers, rows) {
    const wrap = node("div", undefined, "table-wrap"), table = node("table"), head = node("thead"), tr = node("tr");
    for (const h of headers) tr.append(node("th", h)); head.append(tr); table.append(head);
    const body = node("tbody");
    for (const r of rows) { const row = node("tr"); for (const c of r) { const td = node("td"); if (c instanceof Node) td.append(c); else td.textContent = c ?? ""; row.append(td); } body.append(row); }
    table.append(body); wrap.append(table); return wrap;
  }
  function ntRenderList() {
    $("nt-count").textContent = nt.ho_so.length;
    if (!nt.ho_so.length) { $("nt-list").replaceChildren(empty("Chưa có hồ sơ nghiệm thu", "Nạp danh mục DEMO rồi bấm Nhận review mẫu.")); return; }
    $("nt-list").replaceChildren(ntTable(["Mã review", "HĐ nguồn", "Đợt", "Ngày NT", "Nguồn", "Kế toán", ""], nt.ho_so.map(h => {
      const open = node("button", "Mở ↗", "link-button"); open.addEventListener("click", () => { ntSelected = h.id; ntRenderDetail(); });
      return [h.ma_review, `${h.hop_dong.ma_hd} · ${h.hop_dong.so_hd || ""}`, h.dot, h.ngay_nghiem_thu,
              nguonLabel[h.trang_thai_nguon] || h.trang_thai_nguon,
              ntState[h.trang_thai] + (h.chan.length ? ` · ${h.chan.length} điều kiện chưa đủ` : ""), open];
    })));
    $("nt-exports").replaceChildren(nt.file_soat.length ? ntTable(["Tệp", "Lúc", "Số hồ sơ", ""], nt.file_soat.map(e => {
      const dl = node("button", "Tải ↓", "link-button"); dl.addEventListener("click", () => download(`/api/nghiem-thu/file-soat/${encodeURIComponent(e.id)}`, e.tep[0].ten).catch(err => toast(err.message, true)));
      return [e.tep[0].ten, date(e.luc), e.so_dong, dl];
    })) : empty("Chưa xuất file soát", "Đồng ý ít nhất một hồ sơ rồi bấm Xuất file soát."));
  }
  function ntRenderDetail() {
    const h = nt && nt.ho_so.find(x => x.id === ntSelected), box = $("nt-detail");
    if (!h) { box.classList.add("hidden"); return; }
    box.replaceChildren(node("h2", `Hồ sơ ${h.ma_review} · ${ntState[h.trang_thai]}`));
    if (h.ly_do) box.append(node("p", "Lý do: " + h.ly_do));
    const facts = node("dl", undefined, "detail-grid");
    const add = (k, v) => facts.append(node("dt", k), node("dd", v ?? ""));
    add("Nguồn", `#5 · ${h.instance} · review ${h.ma_review} · lúc ${date(h.luc_review)} (${h.luc_basis})`);
    add("Hợp đồng nguồn", `${h.hop_dong.ma_hd} · số ${h.hop_dong.so_hd || "—"} · ${h.hop_dong.phan_loai || "—"}`);
    add("Đợt / ngày nghiệm thu", `${h.dot} (đợt trước ${h.dot_truoc || "—"}) · ${h.ngay_nghiem_thu}`);
    add("Số đề nghị (không phải số hạch toán)", vnd(h.de_nghi.minor));
    for (const t of h.tong_hop) add(t.nhan + (t.o ? ` [${t.o}]` : ""), t.minor === null ? `Không đọc được (gốc: ${String(t.goc)})` : vnd(t.minor));
    add("Ảnh hưởng review", `${String(h.anh_huong.goc)} — ${h.anh_huong.y_nghia}`);
    add("Trạng thái nguồn", (nguonLabel[h.trang_thai_nguon] || h.trang_thai_nguon) + " (không phải duyệt kế toán)" + (h.da_nap_loi.length ? " — " + h.da_nap_loi.join("; ") : ""));
    add("Căn cứ hiệu lực", JSON.stringify(h.can_cu));
    add("Thiếu trong nguồn", h.thieu.length ? h.thieu.join(", ") : "Không");
    add("Tệp / hash raw", `${h.tep_nguon} · ${h.hash_raw}`);
    if (h.thay_cho) add("Bản thay", "Thay cho hồ sơ " + h.thay_cho);
    box.append(facts);
    if (h.chan.length) { const list = node("ul"); for (const c of h.chan) list.append(node("li", c.thong_diep)); box.append(node("h3", "Chưa đủ điều kiện Đồng ý"), list); }
    if (h.trang_thai === "WAIT") {
      const x = h.xac_nhan || {mapping: h.goi_y_mapping || {}, so: {}}, m = x.mapping || {}, s = x.so || {};
      const form = node("form"); form.id = "nt-form";
      const row1 = node("div", undefined, "form-row"), row2 = node("div", undefined, "form-row"), row3 = node("div", undefined, "form-row");
      row1.append(ntField("Pháp nhân", ntInput("nt-pn", m.phap_nhan || nt.phap_nhan)), ntField("Mã hợp đồng chung", ntInput("nt-hd", m.ma_hd_chung || "")));
      row2.append(ntField("Dự án (ProjectID)", ntSelect("nt-da", nt.danh_muc.PROJECT, m.du_an)), ntField("Nhà thầu (ObjectID)", ntSelect("nt-dt", nt.danh_muc.COUNTERPARTY, m.doi_tuong)));
      row3.append(ntField("Số chấp nhận hạch toán (trước VAT, VND)", ntInput("nt-cn", s.chap_nhan_truoc_vat ?? "")), ntField("Giữ lại đợt (VND)", ntInput("nt-gl", s.giu_lai_dot ?? "")));
      const row4 = node("div", undefined, "form-row");
      row4.append(ntField("Thuế suất VAT xác nhận", ntSelect("nt-vat", nt.vat_hop_le, s.thue_suat_vat)), ntField("Thu hồi tạm ứng (ghi nhận, VND)", ntInput("nt-tu", s.thu_hoi_tam_ung ?? "")));
      form.prepend(node("p", "Giữ lại đợt và thu hồi tạm ứng phải nhập rõ, kể cả 0; ô trống là chưa xác nhận."));
      const basis = node("label"), check = node("input"); check.type = "checkbox"; check.id = "nt-coso"; check.checked = s.co_so === "TRUOC_VAT";
      basis.append(check, document.createTextNode(" Số chấp nhận ở trên là số trước VAT"));
      const save = node("button", "Lưu xác nhận", "button secondary"); save.type = "submit";
      form.append(row1, row2, row3, row4, basis, save);
      if (h.goi_y_mapping && !h.xac_nhan) form.prepend(node("p", "Mapping gợi ý từ lần xác nhận trước của cùng hợp đồng — kiểm lại trước khi lưu."));
      form.addEventListener("submit", event => { event.preventDefault(); ntAct("/api/nghiem-thu/xac-nhan", {id: h.id,
        mapping: {phap_nhan: $("nt-pn").value.trim(), ma_hd_chung: $("nt-hd").value.trim(), du_an: $("nt-da").value || null, doi_tuong: $("nt-dt").value || null},
        so: {chap_nhan_truoc_vat: $("nt-cn").value.trim() || null, giu_lai_dot: $("nt-gl").value.trim() || null, thu_hoi_tam_ung: $("nt-tu").value.trim() || null,
             thue_suat_vat: $("nt-vat").value || null, co_so: $("nt-coso").checked ? "TRUOC_VAT" : null}}, "Đã lưu xác nhận."); });
      box.append(node("h3", "Xác nhận kế toán (người thao tác: MO_PHONG_KE_TOAN)"), form);
    }
    if (h.but_toan) box.append(node("h3", "Đề xuất bút toán nghiệm thu (không phát sinh thu/chi tiền)"), ntTable(["Dòng", "Nợ/Có", "Tài khoản", "Số tiền", "Đối tượng", "Dự án", "Diễn giải"],
      h.but_toan.map(l => [l.stt, l.no_co === "N" ? "Nợ" : "Có", l.tai_khoan, vnd(l.so_tien), l.doi_tuong, l.du_an, l.dien_giai])), node("p", nt.mau.ghi_chu));
    const actions = node("div", undefined, "demo-actions");
    const btn = (label, cls, action, ok) => { const b = node("button", label, cls); b.addEventListener("click", () => ntAct("/api/nghiem-thu/quyet-dinh", {id: h.id, hanh_dong: action}, ok)); return b; };
    if (h.trang_thai === "WAIT") { const agree = btn("Đồng ý", "button primary", "dong_y", "Đã đồng ý."); agree.disabled = !h.dong_y_duoc; actions.append(agree, btn("Bỏ qua", "button secondary", "bo_qua", "Đã bỏ qua.")); }
    if (h.trang_thai === "APPROVE") actions.append(btn("Hoàn tác", "button secondary", "hoan_tac", "Đã hoàn tác về chờ xác nhận."));
    box.append(actions); box.classList.remove("hidden");
  }
  async function ntLoad() {
    try { nt = await (await request("/api/nghiem-thu")).json(); ntRenderList(); ntRenderDetail(); }
    catch (error) { $("nt-status").textContent = error.message; }
  }
  async function ntAct(path, body, ok) {
    if (busy || stopped) return; busy = true; controls();
    try { await ntPost(path, body); toast(ok); await ntLoad(); }
    catch (error) { toast(error.message, true); $("nt-status").textContent = error.message; }
    finally { busy = false; controls(); }
  }
  async function ntSeed(kind, ok) {
    if (busy || stopped) return; busy = true; controls();
    try {
      const report = await ntPost("/api/nghiem-thu/mau", {mau: kind});
      $("nt-status").textContent = `${ok}: ${report.state === "COMMITTED" ? "đã nhận" : "từ chối"} · mới ${report.inserted_documents || 0}, trùng ${report.duplicate_documents || 0}.`;
      await ntLoad();
    } catch (error) { toast(error.message, true); $("nt-status").textContent = error.message; }
    finally { busy = false; controls(); }
  }
  $("nt-refresh").addEventListener("click", () => ntLoad());
  $("nt-seed-catalog").addEventListener("click", () => ntSeed("danh_muc", "Danh mục DEMO"));
  $("nt-seed-review").addEventListener("click", () => ntSeed("review", "Review mẫu"));
  $("nt-seed-pending").addEventListener("click", () => ntSeed("review_chua_nap", "Review chưa nạp"));
  $("nt-seed-revision").addEventListener("click", () => ntSeed("review_ban_thay", "Bản thay"));
  $("nt-input").addEventListener("change", () => { $("nt-receive").disabled = !$("nt-input").files.length; });
  $("nt-receive").addEventListener("click", async () => {
    const file = $("nt-input").files[0]; if (!file || busy) return; busy = true; controls();
    try {
      const report = await (await request("/api/nghiem-thu/nhan", {method: "POST", body: file, headers: {"X-File-Name": encodeURIComponent(file.name)}})).json();
      $("nt-status").textContent = `${report.state === "COMMITTED" ? "Đã nhận" : "Từ chối"} · mới ${report.inserted_documents || 0}, trùng ${report.duplicate_documents || 0}` + (report.issues?.length ? " · " + report.issues.map(i => i.code).join(", ") : "");
      await ntLoad();
    } catch (error) { toast(error.message, true); } finally { busy = false; controls(); }
  });
  $("nt-export").addEventListener("click", async () => {
    if (busy || stopped) return; busy = true; controls();
    try { const r = await ntPost("/api/nghiem-thu/xuat", {}); toast(`Đã xuất file soát ${r.ten}.`); await ntLoad(); }
    catch (error) { toast(error.message, true); } finally { busy = false; controls(); }
  });
  window.addEventListener("hashchange", () => { if (location.hash === "#nghiemthu") ntLoad(); });

  // ---- Hợp đồng & lịch thu (CRM-01 DEMO trên K2). Danh tính do máy chủ giữ; chuỗi nguồn chỉ hiển thị bằng textContent. ----
  let crm = null, crmChon = null;
  // M4-01C: CRM tham gia seam đổi vai chung — epoch gắn vai/lựa chọn; đổi vai ở bất kỳ module nào xóa cache/DOM CRM đồng bộ, phản hồi/tải của epoch cũ
  // bị bỏ; GET /api/crm không gửi khi barrier đổi vai còn chờ. Lịch sử/biên nhận/file trên máy chủ không bị xóa.
  let crmEpoch = 0, crmGen = 0, crmTrichGen = 0;  // crmTrichGen: thế hệ form trích Word (CRM-41-01) — khai báo trước crmXoaTrangThai
  function crmXoaTrangThai() {
    crmEpoch += 1; crm = null; crmChon = null;
    crmTrichGen += 1;  // CRM-41-01 FIX01 F5: đổi vai bỏ nháp trích có chủ đích (vùng form gắn epoch cũ sẽ được dựng lại cho vai mới)
    for (const id of ["crm-mau", "crm-tien-mau", "crm-ho-so", "crm-hop-dong", "crm-tien", "crm-file-soat", "crm-danh-tinh"]) $(id).replaceChildren();
    $("crm-chi-tiet").replaceChildren(); $("crm-chi-tiet").classList.add("hidden");
    $("crm-nguoi").textContent = "Đang tải…"; $("crm-status").textContent = "";
  }
  async function crmTai(path, name) {  // tải file soát CHỈ khi vẫn đúng epoch vai/lựa chọn (bytes về trễ của vai cũ: không click)
    const ep = crmEpoch;
    try {
      const blob = await (await request(path)).blob();
      if (ep !== crmEpoch) return;
      const url = URL.createObjectURL(blob), a = node("a"); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (error) { if (ep === crmEpoch) toast(error.message, true); }
  }
  const canCuLabel = {CO_CAN_CU: "Có căn cứ", KHONG_QUY_DINH: "Không quy định/chưa có căn cứ", CAN_CU_KHONG_KHOP: "Trích dẫn không khớp văn bản",
    CHUA_DOI_CHIEU_NGUON: "Chưa có văn bản để đối chiếu", CHUA_DOI_CHIEU_VI_TRI: "Có câu trích, chưa đối chiếu được Điều/Khoản", VI_TRI_KHONG_KHOP: "Trích dẫn không nằm ở Điều/Khoản nguồn ghi",
    GIA_TRI_KHONG_KHOP_TRICH_DAN: "Giá trị không có trong câu trích dẫn", SUY_RA: "Giá trị suy ra (không trích trực tiếp)"};
  const canXacNhan = new Set(["SUY_RA", "GIA_TRI_KHONG_KHOP_TRICH_DAN"]);
  async function crmPost(path, body) { return (await request("/api/crm/" + path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})).json(); }
  async function crmAct(path, body, ok) {
    if (busy || stopped) return null; busy = true; controls();
    const ep = crmEpoch;  // M4-01C: phản hồi đến sau khi đổi vai/lựa chọn → không toast/không nạp/không trả kết quả cũ
    try {
      const r = await crmPost(path, body);
      if (ep !== crmEpoch) return null;
      toast(ok + (r && r.ket_qua ? ` (${r.ket_qua})` : "")); await crmLoad();
      return ep === crmEpoch ? r : null;
    }
    catch (error) { if (ep === crmEpoch) { toast(error.message, true); $("crm-status").textContent = error.message; } return null; }
    finally { busy = false; controls(); }
  }
  function crmInput(id, label, value) { const i = node("input"), l = node("label", label); i.id = id; i.value = value || ""; l.htmlFor = id; return [l, i]; }
  // ---- CRM-41-01: hồ sơ Word thô → engine trích DÙNG CHUNG #6 (common/v1, RULE_ONLY) → đường nhận/kiểm/duyệt hiện có. Loại TRÍCH (danh mục tham số)
  // tách khỏi loại hình tài chính; chỉ XD có danh mục thật. Ý định gốc (bytes tệp + PN + loại + mã + request_id) giữ nguyên khi chưa rõ kết quả;
  // phản hồi muộn của vai/lựa chọn/form cũ không chạm form mới.
  const CRM_LOAI_TRICH = [["XD", "Hợp đồng xây dựng — danh mục XD (37 mã)"]];
  const crmTrichYDinh = new Map();  // khóa = [SHA-256 bytes thật, PN, loại trích, mã] → {info, bytes, sha} — ý định gốc giữ nguyên khi chưa rõ kết quả
  // FIX01 F5: MỘT vùng form trích CỐ ĐỊNH theo vai (epoch): làm mới GET nền (crmLoad → crmRender) gắn lại đúng DOM này, KHÔNG dựng lại → nháp đang nhập
  // (tệp/PN/loại/mã) không bị xóa/ghi đè; đổi vai (crmXoaTrangThai) mới bỏ nháp có chủ đích.
  let crmTrichVung = null;
  function crmTrichForm() {
    const dsPn = (crm && crm.nguoi && crm.nguoi.phap_nhan) || [];
    if (crmTrichVung && crmTrichVung.ep === crmEpoch) {
      const pn = crmTrichVung.pn, cu = pn.value;
      if (JSON.stringify([...pn.options].map(o => o.value)) !== JSON.stringify(dsPn)) {  // chỉ đổi khi danh sách PN thực sự đổi; giữ lựa chọn nếu còn
        pn.replaceChildren(...dsPn.map(p => { const o = node("option", p); o.value = p; return o; }));
        if (dsPn.includes(cu)) pn.value = cu; else crmTrichGen += 1;
      }
      return crmTrichVung.box;
    }
    const box = node("div", undefined, "demo-actions"), tep = node("input"), pn = node("select"), loai = node("select"), ma = node("input"), nut = node("button", "Trích hồ sơ Word (engine dùng chung)", "button secondary");
    tep.type = "file"; tep.accept = ".docx"; tep.id = "crm-trich-tep";
    pn.id = "crm-trich-pn"; pn.replaceChildren(...dsPn.map(p => { const o = node("option", p); o.value = p; return o; }));
    loai.id = "crm-trich-loai"; loai.replaceChildren(...CRM_LOAI_TRICH.map(([v, t]) => { const o = node("option", t); o.value = v; return o; }));
    ma.id = "crm-trich-ma"; ma.placeholder = "ALL hoặc mã cách nhau dấu phẩy (vd TC-01,TC-02)"; ma.value = "ALL";
    for (const el of [tep, pn, loai, ma]) for (const ev of ["input", "change"]) el.addEventListener(ev, () => { crmTrichGen += 1; });
    const lab = (t, el) => { const l = node("label", t); l.htmlFor = el.id; return l; };
    nut.addEventListener("click", () => crmTrich(tep, pn, loai, ma));
    box.append(lab("Hồ sơ Word (.docx)", tep), tep, lab("Pháp nhân", pn), pn, lab("Loại trích (danh mục)", loai), loai, lab("Mã tham số", ma), ma, nut);
    crmTrichVung = {ep: crmEpoch, box, pn};
    return box;
  }
  async function crmSha256Hex(buf) {
    if (!(window.crypto && crypto.subtle)) throw new Error("Trình duyệt không tính được SHA-256 của tệp — không gửi để tránh nhầm tệp.");
    return [...new Uint8Array(await crypto.subtle.digest("SHA-256", buf))].map(b => b.toString(16).padStart(2, "0")).join("");
  }
  async function crmTrich(tep, pn, loai, ma) {
    const f = tep.files && tep.files[0];
    if (!f) { toast("Chọn tệp Word .docx.", true); return; }
    if (!/\.docx$/i.test(f.name)) { toast("Chỉ nhận tệp .docx.", true); return; }
    // giá trị form chụp TẠI ý định gốc (lúc bấm) — không đọc lại form sau await
    const txt = ma.value.trim(), pnGoc = pn.value, loaiGoc = loai.value;
    const tham_so = txt === "ALL" ? "ALL" : txt.split(",").map(s => s.trim()).filter(Boolean);
    if (Array.isArray(tham_so) && !tham_so.length) { toast("Nhập ALL hoặc ít nhất một mã tham số.", true); return; }
    if (busy || stopped) return; busy = true; controls();
    const ep = crmEpoch, gen = crmTrichGen, conDung = () => ep === crmEpoch && gen === crmTrichGen && !vaiDangChan("crm");
    let khoa = null;
    try {
      const buf = await f.arrayBuffer();
      if (!conDung()) return;          // vai/form/ngữ cảnh đổi trong lúc đọc tệp → KHÔNG phát lệnh dưới phiên/form mới
      const sha = await crmSha256Hex(buf);
      if (!conDung()) return;
      khoa = JSON.stringify([sha, pnGoc, loaiGoc, tham_so]);  // định danh theo BYTES thật, không theo tên/cỡ/thời gian sửa (File B cùng metadata ≠ File A)
      let yd = crmTrichYDinh.get(khoa);  // cùng bytes + lựa chọn → cùng request_id (máy chủ/engine đối soát, không chạy lại)
      if (!yd) {
        const rid = "crm:" + ((window.crypto && crypto.randomUUID && crypto.randomUUID()) || (Date.now().toString(36) + Math.random().toString(36).slice(2)));
        yd = {info: {phap_nhan: pnGoc, trich: {loai_hop_dong: loaiGoc, tham_so, request_id: rid}}, bytes: buf, sha};
        crmTrichYDinh.set(khoa, yd);
      }
      const r = await (await request("/api/crm/trich6", {method: "POST", headers: {"Content-Type": "application/octet-stream", "X-CRM-Info": encodeURIComponent(JSON.stringify(yd.info))}, body: yd.bytes})).json();
      crmTrichYDinh.delete(khoa);  // đã có kết quả: ý định khép lại
      if (!conDung()) return;      // vai/lựa chọn/form đã đổi: không toast/không nạp vào form mới (kết quả đã ghi vẫn hiện ở danh sách sau khi tải lại)
      toast(`Đã trích ${r.tham_so_da_dung ? r.tham_so_da_dung.length : ""} mã qua engine dùng chung` + (r.ket_qua ? ` (${r.ket_qua})` : ""));
      await crmLoad();             // làm mới có chủ đích: form trích là DOM cố định nên nháp mới (nếu có) không bị xóa
    } catch (error) {
      // ý định GIỮ NGUYÊN (cùng bytes/PN/loại/mã/request_id): bấm lại với cùng tệp và lựa chọn → máy chủ/engine đối soát, không chạy lại
      if (conDung()) { toast(error.message + (khoa ? " — có thể bấm Trích lại với cùng tệp/lựa chọn (cùng mã ý định, không chạy lại)." : ""), true); $("crm-status").textContent = error.message; }
    } finally { busy = false; controls(); }
  }
  function crmHoSo(h) {
    const box = node("div"), v = h.viec.find(x => x.trang_thai === "CHO_DUYET");
    if (!v) return box;
    if (v.ly_do_cho.includes("TRICH_LAI_CUNG_WORD")) {
      const out = node("div"), cmp = node("button", "Đối chiếu bản trích lại", "button secondary");
      const [ll, ly] = crmInput("crm-trich-ly-do-" + h.id, "Lý do");
      cmp.addEventListener("click", async () => {
        const ep = crmEpoch;
        try { const r = await crmPost("trich-lai/doi-chieu", {id: h.id});
          if (ep !== crmEpoch) return;  // M4-01C: kết quả đối chiếu của vai/lựa chọn cũ không vẽ vào màn hình mới
          out.replaceChildren(node("p", `${r.so_khac} mã khác so với phiên bản ${r.trang_thai_ban === "CHO_DUYET" ? "đang chờ duyệt" : "đã chốt"}`),
            ntTable(["Mã", "Bản cũ", "Bản trích lại", "Khác"], r.dong.map(d => [d.ma, d.cu ? `${d.cu.gia_tri_tho ?? "—"} · ${canCuLabel[d.cu.can_cu] || d.cu.can_cu}` : "—",
              d.moi ? `${d.moi.gia_tri_tho ?? "—"} · ${canCuLabel[d.moi.can_cu] || d.moi.can_cu}` : "—", d.khac ? "KHÁC" : ""])));
        } catch (error) { if (ep === crmEpoch) toast(error.message, true); }
      });
      const giu = node("button", "Giữ bản cũ", "button secondary"), ap = node("button", "Áp dụng bản trích lại", "button secondary");
      giu.addEventListener("click", () => crmAct("trich-lai/xu-ly", {id: h.id, hanh_dong: "GIU_BAN_CU", ly_do: ly.value}, "Đã giữ bản cũ"));
      ap.addEventListener("click", () => crmAct("trich-lai/xu-ly", {id: h.id, hanh_dong: "AP_DUNG", ly_do: ly.value}, "Đã áp dụng bản trích lại"));
      const acts = node("div", undefined, "demo-actions"); acts.append(cmp, ll, ly, giu, ap); box.append(acts, out);
      return box;
    }
    const e = h.envelope, acts = node("div", undefined, "demo-actions"), fields = [["loai_hinh", "Loại hình"], ["loai_ban", "Loại bản (GOC/PHU_LUC)"],
      ["ma_hop_dong_chung", "Mã HĐ chung"], ["hop_dong_goc", "HĐ gốc (phụ lục)"], ["doi_tac_object_id", "ObjectID đối tác"], ["du_an", "Mã dự án"]];
    const inputs = fields.map(([k, label]) => { const [l, i] = crmInput(`crm-bs-${k}-${h.id}`, label, e[k]); acts.append(l, i); return [k, i]; });
    const save = node("button", "Bổ sung & lập tiếp", "button secondary");
    save.addEventListener("click", () => crmAct("bo-sung", {id: h.id, bo_sung: Object.fromEntries(inputs.filter(([k, i]) => (i.value.trim() || null) !== (e[k] || null)).map(([k, i]) => [k, i.value.trim()]))}, "Đã bổ sung hồ sơ"));
    acts.append(save); box.append(acts);
    return box;
  }
  function crmRender() {
    if (!crm.cau_hinh) { $("crm-nguoi").textContent = crm.ly_do; $("crm-hop-dong").replaceChildren(empty("Chưa kết nối kho DEMO PostgreSQL", crm.ly_do)); return; }
    const sel = $("crm-danh-tinh"); sel.replaceChildren(...crm.danh_tinh_demo.map(d => { const o = node("option", `${d.dang_nhap} (${d.vai_tro})`); o.value = d.dang_nhap; o.selected = d.dang_nhap === crm.nguoi.dang_nhap; return o; }));
    if (crm.khong_quyen) {
      $("crm-nguoi").textContent = `${crm.nguoi.dang_nhap} · ${crm.khong_quyen}`;
      for (const id of ["crm-mau", "crm-tien-mau", "crm-ho-so", "crm-hop-dong", "crm-tien", "crm-file-soat"]) $(id).replaceChildren();
      $("crm-chi-tiet").classList.add("hidden"); return;
    }
    $("crm-nguoi").textContent = `${crm.nguoi.dang_nhap} · ${crm.nguoi.vai_tro} · pháp nhân: ${crm.nguoi.phap_nhan.join(", ")} · ngày nghiệp vụ ${crm.ngay_nghiep_vu} · phiên của trình duyệt này`;
    $("crm-mau").replaceChildren(...crm.mau.map(m => { const b = node("button", "Nhận mẫu " + m, "button secondary"); b.addEventListener("click", () => crmAct("mau", {mau: m}, "Đã nhận mẫu")); return b; }),
      crmTrichForm());
    $("crm-tien-mau").replaceChildren(...(crm.m1_cau_hinh ? crm.tien_mau.map(p => { const b = node("button", "Sao kê M1 DEMO " + p, "button secondary");
      b.addEventListener("click", () => crmAct("m1-sao-ke", {mau: p}, "Đã nạp sao kê qua M1 và chiếu sang K2")); return b; }) : [node("p", "Chưa cấu hình bộ chiếu M1 → K2 (tài khoản chủ CSDL DEMO).")]));
    const viec = crm.ho_so.filter(h => h.viec.some(v => v.trang_thai === "CHO_DUYET"));
    $("crm-ho-so").replaceChildren(viec.length ? ntTable(["Pháp nhân", "Tệp nguồn", "Việc", "Lý do chờ", "Xử lý"], viec.map(h => [h.phap_nhan, String(h.tham_chieu_file ?? ""),
      h.viec.map(v => `${v.loai} ${v.trang_thai}`).join("; "), h.viec.filter(v => v.trang_thai === "CHO_DUYET").flatMap(v => v.ly_do_cho).join(", "), crmHoSo(h)])) : empty("Không có hồ sơ chờ mapping/khóa", "Hồ sơ đủ khóa hiện ở mục Hợp đồng."));
    $("crm-hop-dong").replaceChildren(crm.hop_dong.length ? ntTable(["Pháp nhân", "Mã HĐ chung", "Số HĐ", "Giá trị", "Trạng thái", "Phiên bản", ""], crm.hop_dong.map(h => {
      const b = node("button", "Mở ↗", "link-button"); b.addEventListener("click", () => { crmChon = h.id; crmDetail(); });
      return [h.phap_nhan, h.ma_noi_bo, h.so_hop_dong, h.gia_tri ? vnd(h.gia_tri) : "Chưa có căn cứ", h.trang_thai,
        h.phien_ban.map(v => `v${v.phien_ban} ${v.loai} ${v.trang_thai}${v.hieu_luc_hom_nay ? " (hiệu lực hôm nay)" : v.sap_hieu_luc ? " (sắp hiệu lực " + v.ngay_hieu_luc + ")" : ""}`).join(" · "), b];
    })) : empty("Chưa có hợp đồng", "Nhận mẫu kcn_goc hoặc nha_goc."));
    $("crm-tien").replaceChildren(!crm.nguoi.xem_tien ? empty("Không có quyền xem khoản thu", "Khoản thu thuộc module M1.") : crm.tien.length
      ? ntTable(["Pháp nhân", "Mã GD (khóa M1)", "Ngày", "Số tiền", "Đã nối", "Đề xuất M1", "Nguồn"], crm.tien.map(t => [t.phap_nhan, t.khoa, t.ngay, vnd(t.so_tien) + (t.tien_te !== "VND" ? " " + t.tien_te : ""), vnd(t.da_noi), t.so_de_xuat, t.nguon_m1 ? "M1 (bộ chiếu)" : "khác"]))
      : empty("Chưa có khoản thu", "Bấm Sao kê M1 DEMO để tiền về qua M1."));
    $("crm-file-soat").replaceChildren(crm.file_soat.length ? ntTable(["Pháp nhân", "Tệp", "Lúc", ""], crm.file_soat.map(f => {
      const dl = node("button", "Tải ↓", "link-button"); dl.addEventListener("click", () => crmTai(`/api/crm/file-soat/${encodeURIComponent(f.id)}`, f.ten));
      return [f.phap_nhan, f.ten, date(f.luc), dl];
    })) : empty("Chưa xuất file soát", "Mở hợp đồng rồi bấm Xuất file soát lịch nghĩa vụ."));
    crmDetail();
  }
  function crmDetail() {
    const h = crm && crm.hop_dong && crm.hop_dong.find(x => x.id === crmChon), box = $("crm-chi-tiet");
    if (!h) { box.classList.add("hidden"); return; }
    const top = node("div", undefined, "demo-actions"), xuat = node("button", "Xuất file soát lịch nghĩa vụ", "button secondary");
    xuat.addEventListener("click", () => crmAct("file-soat", {id: h.id}, "Đã xuất file soát CRM"));
    top.append(xuat);
    if (h.v4 === "CHO_DUYET") { const v4 = node("button", "CFO duyệt V4 (hợp đồng/danh mục mới)", "button secondary"); v4.addEventListener("click", () => crmAct("duyet-v4", {id: h.id}, "Đã duyệt V4")); top.append(v4); }
    box.replaceChildren(node("h2", `${h.ma_noi_bo} · ${h.so_hop_dong} · ${h.phap_nhan}`),
      node("p", `Đối tác (ObjectID): ${h.doi_tac_object_id || "chưa mapping"} · Dự án: ${h.du_an || "chưa mapping"} · việc V4: ${h.v4 || "—"}`), top);
    for (const v of h.phien_ban) {
      box.append(node("h3", `Phiên bản ${v.phien_ban} · ${v.loai}${v.so_phu_luc ? " " + v.so_phu_luc : ""} · ${v.trang_thai}${v.ngay_hieu_luc ? " · hiệu lực từ " + v.ngay_hieu_luc : ""}${v.hieu_luc_hom_nay ? " · ĐANG HIỆU LỰC" : v.sap_hieu_luc ? " · SẮP HIỆU LỰC" : ""}`));
      box.append(node("p", `Kế toán kiểm: ${v.kiem_boi || "chưa (hoặc đã hết hiệu lực do nội dung/mapping đổi)"} · CFO duyệt: ${v.nguoi_duyet || "chưa"} · nguồn: ${v.nguon}${v.profile ? ` · profile ${v.profile.ma} v${v.profile.phien_ban}` : ""}`));
      box.append(ntTable(["Mã", "Field", "Giá trị nguồn", "Giá trị hiệu lực", "Căn cứ", "Trích dẫn", "Điều khoản", ""], v.tham_so.map(p => {
        let act = p.xac_nhan_thu_cong ? `Đã xác nhận: ${p.xac_nhan_thu_cong.boi}` : "";
        if (v.trang_thai === "CHO_DUYET" && canXacNhan.has(p.can_cu) && !p.xac_nhan_thu_cong && !p.ke_thua) {
          act = node("div"); const [l, i] = crmInput(`crm-xn-${v.id}-${p.ten}`, "Lý do"); const b = node("button", "Xác nhận thủ công", "link-button");
          b.addEventListener("click", () => crmAct("xac-nhan-tham-so", {id: v.id, ma: p.ma, ly_do: i.value}, "Đã xác nhận tham số")); act.append(l, i, b);
        }
        return [p.ten, p.truong || "", p.gia_tri_tho || "", p.gia_tri_hieu_luc ?? "Không quy định", (canCuLabel[p.can_cu] || p.can_cu) + (p.ke_thua ? " (kế thừa)" : "") + (p.loi.length ? " · " + p.loi.join(",") : ""), p.trich_dan || "", p.dieu_khoan || "", act];
      })));
      if (v.chan.length) { const ul = node("ul"); v.chan.forEach(c => ul.append(node("li", c.thong_diep))); box.append(node("h4", "Chưa đủ điều kiện"), ul); }
      if (v.trang_thai === "CHO_DUYET") {
        if (v.lich_du_kien.length) box.append(node("h4", "Lịch dự kiến (chưa hiệu lực)"), ntTable(["Đợt", "Số tiền", "Hạn", "Mốc"], v.lich_du_kien.map(r => [r.khoa, vnd(r.so_tien_minor), r.han || "—", r.moc || "—"])));
        const acts = node("div", undefined, "demo-actions"), lbl = node("label"), chk = node("input"); chk.type = "checkbox"; chk.id = "crm-thu-cong-" + v.id;
        lbl.htmlFor = chk.id; lbl.append(chk, document.createTextNode(" Tôi đã đối chiếu căn cứ thủ công (khi chưa có văn bản gốc)"));
        const kiem = node("button", "Kế toán kiểm trước", "button secondary"); kiem.addEventListener("click", () => crmAct("kiem", {id: v.id, xac_nhan_can_cu_thu_cong: chk.checked}, "Đã kiểm trước"));
        const duyet = node("button", "CFO duyệt", "button primary"); duyet.addEventListener("click", () => crmAct("duyet", {id: v.id}, "Đã duyệt"));
        const lyDo = node("input"); lyDo.id = "crm-ly-do-" + v.id; const lyLbl = node("label", "Lý do từ chối"); lyLbl.htmlFor = lyDo.id;
        const tuChoi = node("button", "Từ chối", "button secondary"); tuChoi.addEventListener("click", () => crmAct("tu-choi", {id: v.id, ly_do: lyDo.value}, "Đã từ chối"));
        acts.append(lbl, kiem, duyet, lyLbl, lyDo, tuChoi); box.append(acts);
        if (v.loai === "GOC") {
          const map = node("div", undefined, "demo-actions");
          const dt = node("select"); dt.id = "crm-dt-" + v.id; dt.append(node("option", "— đối tác —")); dt.firstChild.value = "";
          crm.danh_muc.doi_tac.filter(d => d.phap_nhan === h.phap_nhan).forEach(d => { const o = node("option", d.object_id); o.value = d.object_id; dt.append(o); });
          const da = node("select"); da.id = "crm-da-" + v.id; da.append(node("option", "— dự án —")); da.firstChild.value = "";
          crm.danh_muc.du_an.filter(d => d.phap_nhan === h.phap_nhan).forEach(d => { const o = node("option", d.ma); o.value = d.ma; da.append(o); });
          const l1 = node("label", "ObjectID đối tác"), l2 = node("label", "Mã dự án"); l1.htmlFor = dt.id; l2.htmlFor = da.id;
          const save = node("button", "Lưu mapping", "button secondary");
          save.addEventListener("click", () => crmAct("mapping", {id: v.id, mapping: Object.fromEntries([["doi_tac_object_id", dt.value], ["du_an", da.value]].filter(([, x]) => x))}, "Đã lưu mapping"));
          map.append(l1, dt, l2, da, save); box.append(map);
        }
      }
      if (v.lich.length) {
        box.append(node("h4", "Lịch thu"), ntTable(["Đợt", "Số tiền", "Hạn", "Mốc", "Trạng thái", "Đã thu (đợt này)", "Liên kết tiền"], v.lich.map(l => {
          const cell = node("div");
          l.lien_ket.forEach(k => { const line = node("div", `${vnd(k.so_tien)} · ${k.trang_thai}${k.ly_do_huy ? " · " + k.ly_do_huy : ""} `);
            if (k.trang_thai !== "HUY") { const go = node("button", "Gỡ", "link-button"); go.addEventListener("click", () => crmAct("go-lien-ket", {id: k.id, ly_do: "Gỡ trên giao diện DEMO"}, "Đã gỡ liên kết")); line.append(go); }
            cell.append(line); });
          if (h.hieu_luc_hom_nay === v.id && crm.nguoi.xem_tien) {
            const tien = node("select"); tien.id = "crm-tien-" + l.id; crm.tien.filter(t => t.phap_nhan === h.phap_nhan).forEach(t => { const o = node("option", `${t.khoa} · ${vnd(t.so_tien)}`); o.value = t.id; tien.append(o); });
            const so = node("input"); so.id = "crm-so-" + l.id; so.inputMode = "numeric";
            const lt = node("label", "Khoản thu"), ls = node("label", "Số tiền nối (VND)"); lt.htmlFor = tien.id; ls.htmlFor = so.id;
            const noi = node("button", "Nối", "button secondary"); const khoa = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now() + Math.random());
            noi.addEventListener("click", () => crmAct("lien-ket", {tien: tien.value, lich: l.id, so_tien: so.value.trim(), khoa}, "Đã nối tiền"));
            cell.append(lt, tien, ls, so, noi);
          }
          return [l.khoa, vnd(l.so_tien), l.han || "—", l.moc || "—", l.trang_thai, vnd(l.da_thu), cell];
        })));
      }
    }
    box.classList.remove("hidden");
  }
  async function crmLoad() {
    if (vaiDangChan("crm")) return;  // M4-01C: đổi vai đang chờ — không GET vai cũ; nạp lại khi ý định mới nhất giải quyết
    const ep = crmEpoch, gen = ++crmGen, moiNhat = () => ep === crmEpoch && gen === crmGen;  // GET cũ hơn không đè GET mới
    try { const s = await (await request("/api/crm")).json(); if (!moiNhat()) return; crm = s; crmRender(); }
    catch (error) { if (moiNhat()) $("crm-status").textContent = error.message; }
  }
  $("crm-refresh").addEventListener("click", () => crmLoad());
  $("crm-doi-vai").addEventListener("click", () => {
    const login = $("crm-danh-tinh").value;  // M4-01C: chụp login đồng bộ, rồi cổng đổi vai chung (xóa mọi module + barrier + hàng POST)
    return doiVaiTuanTu(() => crmPost("danh-tinh", {dang_nhap: login}), "crm-status", "crm");
  });
  window.addEventListener("hashchange", () => { if (location.hash === "#hopdong") crmLoad(); });

  // ---- Khoản vay (M9 DEMO trên K2). Cùng phiên/cookie với CRM; tiền là chuỗi minor, định dạng bằng chuỗi; chuỗi nguồn chỉ qua textContent. ----
  let m9 = null, m9Chon = null, m9Ngay = "";
  const SCALE = {VND: 0, USD: 2};
  const tien9 = (v, cur) => {
    if (v === null || v === undefined || v === "") return "— (chưa có số)";
    const s = SCALE[cur || "VND"], text = String(v);
    if (!s || !/^-?\d+$/.test(text)) return cur && cur !== "VND" ? `${text} ${cur} (minor)` : vnd(text);
    const sign = text.startsWith("-") ? "-" : "", d = (sign ? text.slice(1) : text).padStart(s + 1, "0");
    return `${sign}${d.slice(0, -s).replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${d.slice(-s)} ${cur}`;
  };
  const khoa9 = () => (crypto.randomUUID && crypto.randomUUID()) || String(Date.now() + Math.random());
  async function m9Post(path, body) { return (await request("/api/m9/" + path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})).json(); }
  async function m9Act(path, body, ok) {
    if (busy || stopped) return null; busy = true; controls();
    try { const r = await m9Post(path, body); toast(ok); await m9Load(); return r; }
    catch (error) { toast(error.message, true); $("m9-status").textContent = error.message; return null; }
    finally { busy = false; controls(); }
  }
  function m9Btn(text, cls, fn) { const b = node("button", text, cls); b.addEventListener("click", fn); return b; }
  function m9Field(id, label, el) { el.id = id; const l = node("label", label); l.htmlFor = id; return [l, el]; }
  function m9Sel(values, first) { const s = node("select"); if (first) { s.append(node("option", first)); s.firstChild.value = ""; } values.forEach(([v, t]) => { const o = node("option", t); o.value = v; s.append(o); }); return s; }
  function m9Render() {
    if (!m9.cau_hinh) { $("m9-nguoi").textContent = m9.ly_do; $("m9-khoan-vay").replaceChildren(empty("Chưa kết nối kho DEMO PostgreSQL", m9.ly_do)); return; }
    $("m9-danh-tinh").replaceChildren(...m9.danh_tinh_demo.map(d => { const o = node("option", `${d.dang_nhap} (${d.vai_tro})`); o.value = d.dang_nhap; o.selected = d.dang_nhap === m9.nguoi.dang_nhap; return o; }));
    const ids = ["m9-mau", "m9-snapshot", "m9-anh-xa", "m9-khoan-vay", "m9-tien-mau", "m9-tien", "m9-noi", "m9-viec", "m9-file-soat", "m9-khoang-trong"];
    if (m9.khong_quyen) { $("m9-nguoi").textContent = `${m9.nguoi.dang_nhap} · ${m9.khong_quyen}`; ids.forEach(id => $(id).replaceChildren()); $("m9-chi-tiet").classList.add("hidden"); return; }
    const n = m9.nguoi;
    $("m9-nguoi").textContent = `${n.dang_nhap} · ${n.vai_tro} · pháp nhân: ${n.phap_nhan.join(", ")} · xem ngày ${m9.ngay_xem} · được làm: ${n.hanh_dong.join(", ") || "chỉ xem"}`;
    $("m9-mau").replaceChildren(...m9.mau.map(m => m9Btn("Nhận mẫu " + m, "button secondary", async () => {
      const r = await m9Act("mau", {mau: m}, "Đã nhận nguồn"); if (r) $("m9-status").textContent = `Ảnh chụp ${r.trang_thai} · ${r.pham_vi}${r.loi.length ? " · " + r.loi.join(", ") : ""}${r.cong_ty_cho_map.length ? " · công ty chờ map: " + r.cong_ty_cho_map.join(", ") : ""}`; })));
    const pns = n.phap_nhan.map(p => [p, p]);
    $("m9-snapshot").replaceChildren(m9.snapshot.length ? ntTable(["Nhận lúc", "Profile", "Trạng thái", "Phạm vi", "Lỗi", "Raw SHA-256", "Dòng có PN", "Lập hồ sơ"], m9.snapshot.map(s => {
      const cell = node("div", undefined, "demo-actions");
      if (s.profile.startsWith("VAY_DEPLOY") && s.trang_thai !== "REJECTED" && n.hanh_dong.includes("M9_STAGE")) {
        const [l, sel] = m9Field("m9-lap-" + s.id, "Pháp nhân", m9Sel(pns)); cell.append(l, sel, m9Btn("Lập/cập nhật hồ sơ", "button secondary", async () => {
          const r = await m9Act("lap", {snapshot: s.id, phap_nhan: sel.value}, "Đã lập hồ sơ vay");
          if (r) $("m9-status").textContent = r.khoan_vay.map(k => `${k.khoa}: ${k.ket_qua}${k.chan && k.chan.length ? " · chờ " + k.chan.join(", ") : ""}`).join(" | "); }));
      }
      return [date(s.biet_luc), s.profile, s.trang_thai, s.pham_vi, (s.loi || []).join(", "), s.raw_sha256.slice(0, 16) + "…", s.so_dong_pn, cell];
    })) : empty("Chưa nhận nguồn khoản vay", "Bấm Nhận mẫu native_v6."));
    const ax = node("div");
    if (m9.cong_ty_cho_map.length) ax.append(node("h4", "Công ty nguồn chờ map"), ntTable(["Nguồn", "Công ty nguồn", "Số dòng chờ", "Map vào"], m9.cong_ty_cho_map.map(c => {
      const cell = node("div", undefined, "demo-actions"), [l, sel] = m9Field("m9-ct-" + c.cong_ty, "Pháp nhân", m9Sel(pns));
      cell.append(l, sel, m9Btn("CFO duyệt mapping", "button secondary", () => m9Act("anh-xa", {kind: "COMPANY", cong_ty: c.cong_ty, dich: sel.value, ly_do: "Duyệt trên giao diện DEMO"}, "Đã duyệt mapping công ty")));
      return [c.instance, c.cong_ty, c.so_dong, cell]; })));
    if (m9.ung_vien_anh_xa.length) ax.append(node("h4", "Ngân hàng / dự án nguồn chờ map"), ntTable(["Loại", "Công ty nguồn", "Giá trị nguồn", "Pháp nhân", "Map vào"], m9.ung_vien_anh_xa.map(u => {
      const cell = node("div", undefined, "demo-actions"), [l, inp] = m9Field(`m9-uv-${u.kind}-${u.cong_ty}-${u.nguon}`, u.kind === "BANK" ? "ObjectID ngân hàng (danh mục PN)" : "Mã dự án (danh mục PN)", node("input"));
      cell.append(l, inp, m9Btn("CFO duyệt mapping", "button secondary", () => m9Act("anh-xa", {kind: u.kind, cong_ty: u.cong_ty, nguon: u.nguon, dich: inp.value.trim(), ly_do: "Duyệt trên giao diện DEMO"}, "Đã duyệt mapping")));
      return [u.kind, u.cong_ty, u.nguon, u.phap_nhan, cell]; })));
    if (m9.anh_xa.length) ax.append(node("h4", "Mapping đã duyệt"), ntTable(["Loại", "Công ty nguồn", "Nguồn", "Pháp nhân", "Đích", "Rev", "Trạng thái", "Người duyệt", ""], m9.anh_xa.map(m => {
      const cell = node("div", undefined, "demo-actions");
      if (m.trang_thai === "DA_DUYET") {
        const [l, ly] = m9Field("m9-dong-" + m.id, "Lý do đóng", node("input"));
        cell.append(m9Btn("Ảnh hưởng", "link-button", async () => { try { const r = await m9Post("anh-xa/anh-huong", {id: m.id});
          toast(`Ảnh hưởng: ${r.so_dong_nguon} dòng · ${r.so_hop_dong} HĐ · ${r.so_phien_ban_da_duyet} bản đã duyệt · ${r.so_lien_ket_tien_hieu_luc} liên kết tiền. ${r.quy_tac}`); } catch (e) { toast(e.message, true); } }),
          l, ly, m9Btn("Đóng mapping", "link-button", () => m9Act("anh-xa/dong", {id: m.id, ly_do: ly.value}, "Đã đóng mapping")));
      }
      return [m.kind, m.cong_ty, m.nguon, m.phap_nhan, m.doi_tac || m.du_an || m.phap_nhan, m.revision, m.trang_thai, m.duyet_boi, cell]; })));
    $("m9-anh-xa").replaceChildren(ax.childNodes.length ? ax : empty("Chưa có mapping", "Nhận nguồn trước; CFO duyệt mapping công ty."));
    $("m9-khoan-vay").replaceChildren(m9.khoan_vay.length ? ntTable(["Pháp nhân", "Khóa nguồn", "Số HĐ", "Ngân hàng", "Loại", "Trạng thái", "Phiên bản", ""], m9.khoan_vay.map(h => {
      const last = h.phien_ban[h.phien_ban.length - 1];
      return [h.phap_nhan, h.khoa_nguon, h.so_hop_dong, h.ngan_hang || "chưa map", last ? last.vay.financing_kind : "", h.trang_thai,
        h.phien_ban.map(v => `v${v.phien_ban} ${v.trang_thai}${v.hieu_luc_hom_nay ? " (hiệu lực)" : ""}${v.chan.length ? " · chờ " + v.chan.length : ""}`).join(" · "),
        m9Btn("Mở ↗", "link-button", () => { m9Chon = h.id; m9Detail(); })];
    })) : empty("Chưa có khoản vay", "Lập hồ sơ từ ảnh chụp nguồn sau khi CFO duyệt mapping công ty."));
    $("m9-tien-mau").replaceChildren(...(m9.m1_cau_hinh ? m9.tien_mau.map(p => m9Btn("Sao kê M1 DEMO " + p, "button secondary", () => m9Act("m1-sao-ke", {mau: p}, "Đã nạp sao kê qua M1, chiếu sang K2, ghi proof số tiền")))
      : [node("p", "Chưa cấu hình bộ chiếu M1 → K2 (tài khoản chủ CSDL DEMO).")]));
    $("m9-tien").replaceChildren(!n.xem_tien ? empty("Không có quyền xem tiền", "Tiền thuộc module M1.") : m9.tien.length ? ntTable(["Pháp nhân", "Ngày", "Chiều", "Tham chiếu", "Số tiền", "Đã phân bổ (mọi module)", "Còn lại", "Chặn", ""], m9.tien.map(t =>
      [t.phap_nhan, t.ngay, t.chieu, t.tham_chieu || "", tien9(t.so_tien, t.tien_te), tien9(t.da_phan_bo, t.tien_te), t.con_lai === null ? "—" : tien9(t.con_lai, t.tien_te), t.chan || "",
        m9Btn("Gợi ý & nối", "link-button", () => m9GoiY(t))])) : empty("Chưa có tiền", "Bấm Sao kê M1 DEMO."));
    $("m9-viec").replaceChildren(node("h4", "Việc đang mở"), m9.viec.length ? ntTable(["Loại", "Tóm tắt", "Lý do chờ", "Kế toán kiểm"], m9.viec.map(v => [v.loai, v.tom_tat || "", v.ly_do_cho.join(", "), v.kiem_boi || ""])) : empty("Không có việc mở", ""));
    $("m9-file-soat").replaceChildren(node("h4", "File soát"), m9.file_soat.length ? ntTable(["Pháp nhân", "Tệp", "Lúc", ""], m9.file_soat.map(f =>
      [f.phap_nhan, f.ten, date(f.luc), m9Btn("Tải ↓", "link-button", () => download(`/api/m9/file-soat/${encodeURIComponent(f.id)}`, f.ten).catch(err => toast(err.message, true)))])) : empty("Chưa xuất file soát", "Mở khoản vay rồi bấm Xuất file soát."));
    $("m9-khoang-trong").replaceChildren(node("h4", "Khoảng trống M9 (giữ việc, chưa làm)"), ntTable(["Nhánh", "Trạng thái", "Còn thiếu", "Không làm"], m9.khoang_trong.map(g => [g.nhanh, g.trang_thai, g.thieu.join("; "), g.khong_lam])));
    m9Detail();
  }
  function m9Detail() {
    const h = m9 && m9.khoan_vay && m9.khoan_vay.find(x => x.id === m9Chon), box = $("m9-chi-tiet");
    if (!h) { box.classList.add("hidden"); return; }
    const top = node("div", undefined, "demo-actions");
    top.append(m9Btn("Xuất file soát hồ sơ vay", "button secondary", () => m9Act("file-soat", {id: h.id}, "Đã xuất file soát M9")));
    if (h.v4 === "CHO_DUYET") top.append(m9Btn("CFO duyệt V4 (khoản vay mới)", "button secondary", () => m9Act("duyet-v4", {id: h.id}, "Đã duyệt V4")));
    box.replaceChildren(node("h2", `${h.so_hop_dong} · ${h.phap_nhan}`), node("p", `Khóa nguồn ${h.khoa_nguon} · ngân hàng ${h.ngan_hang || "chưa map"} · dự án ${h.du_an || "—"} · V4: ${h.v4 || "—"}`), top);
    for (const v of h.phien_ban) {
      const f = v.vay, cur = f.currency_code;
      box.append(node("h3", `Phiên bản ${v.phien_ban} · ${v.trang_thai}${v.hieu_luc_hom_nay ? " · ĐANG HIỆU LỰC" : ""} · ${f.financing_kind}`));
      box.append(node("p", `Nguồn: ảnh chụp ${v.nguon.snapshot_id} · profile ${v.nguon.profile} · raw ${String(v.nguon.raw_sha256).slice(0, 16)}… · precision ${f.precision_status} · kiểm: ${v.kiem_boi || "chưa"} · duyệt: ${v.nguoi_duyet || "chưa"}${v.ly_do ? " · " + v.ly_do : ""}`));
      box.append(ntTable(["Tiền tệ", "Hạn mức", "Dư nợ nguồn", "Ngày dư nợ", "Số vay VND", "Nguyên tệ", "Tỷ giá nguồn", "Số HĐ/nhận nợ/LC", "Ngày nhận nợ / mở LC / đến hạn"],
        [[cur || "chưa có", tien9(f.han_muc, cur), tien9(f.du_no_nguon, cur), f.ngay_du_no_nguon || "—", tien9(f.so_vay_vnd, "VND"), f.so_nguyen_te ? tien9(f.so_nguyen_te, f.nguyen_te_code) : "—",
          f.source_fx_rate || "—", [f.so_hop_dong_nguon, f.so_nhan_no, f.so_lc].filter(Boolean).join(" / "), [f.ngay_nhan_no, f.ngay_mo_lc, f.ngay_den_han].map(x => x || "—").join(" / ")]]));
      if (v.chan.length) { const ul = node("ul"); v.chan.forEach(c => ul.append(node("li", c))); box.append(node("h4", "Chưa đủ điều kiện (giữ chờ)"), ul); }
      if (v.trang_thai === "CHO_DUYET") {
        const acts = node("div", undefined, "demo-actions"), [ll, ly] = m9Field("m9-tc-" + v.id, "Lý do từ chối", node("input"));
        acts.append(m9Btn("Kế toán kiểm", "button secondary", () => m9Act("kiem", {id: v.id}, "Đã kiểm")), m9Btn("CFO duyệt", "button primary", () => m9Act("duyet", {id: v.id}, "Đã duyệt")),
          ll, ly, m9Btn("Từ chối", "button secondary", () => m9Act("tu-choi", {id: v.id, ly_do: ly.value}, "Đã từ chối")));
        box.append(acts);
        if (v.chan.includes("CHO_XAC_NHAN_PHAM_VI_LICH")) {
          const pv = node("div", undefined, "demo-actions"), [l1, sel] = m9Field("m9-pv-" + v.id, "Tầng nghĩa vụ gốc", m9Sel(Object.entries(m9.lua_chon_pham_vi).map(([k, t]) => [k, `${k} — ${t}`])));
          const [l2, lyp] = m9Field("m9-pvl-" + v.id, "Lý do", node("input"));
          pv.append(l1, sel, l2, lyp, m9Btn("Xác nhận phạm vi lịch & lập lại", "button secondary", () => m9Act("pham-vi", {hop_dong: h.id, lua_chon: sel.value, ly_do: lyp.value}, "Đã xác nhận phạm vi lịch")));
          box.append(pv);
        }
      }
      if (v.khe_uoc.length) box.append(node("h4", "Khế ước (giải ngân)"), ntTable(["Mã", "Ngày giải ngân", "Số tiền", "Precision", "Đã nối", "Còn lại", "Chặn nối"],
        v.khe_uoc.map(d => [d.ma, d.ngay || "—", tien9(d.so_tien, d.currency), d.precision, d.da_phan_bo ? tien9(d.da_phan_bo, d.currency) : "—", d.con_lai ? tien9(d.con_lai, d.currency) : "—", d.chan_noi || ""])));
      if (v.lai_suat.length) box.append(node("h4", "Lãi suất theo mốc (nguồn)"), ntTable(["Khế ước", "Áp dụng từ", "%/năm", "Precision"], v.lai_suat.map(r => [r.ma, r.ap_dung_tu, r.pct_nam, r.precision])));
      if (v.lich.length) box.append(node("h4", "Lịch trả nợ"), ntTable(["Nghĩa vụ", "Phạm vi", "Cấu phần", "Kỳ", "Từ–đến", "Đến hạn", "Số tiền", "Loại số", "Đã nối", "Còn lại"],
        v.lich.map(x => [x.nghia_vu_key, x.pham_vi, x.cau_phan, x.ky, x.tu ? `${x.tu} → ${x.den}` : "—", x.han || "—", tien9(x.so_tien, x.currency), x.amount_kind, x.da_phan_bo ? tien9(x.da_phan_bo, x.currency) : "—", x.con_lai ? tien9(x.con_lai, x.currency) : (x.chan_noi || "—")])));
      if (v.phat_sinh.length) box.append(node("h4", "Phát sinh nguồn (bằng chứng, chưa là tiền)"), ntTable(["Khóa", "Rev", "Ngày", "Số CT", "Gốc", "Lãi", "Phí", "Trạng thái"],
        v.phat_sinh.map(e => [e.key, e.revision, e.ngay || "—", e.so_chung_tu || "", tien9(e.parts.GOC, cur), tien9(e.parts.LAI, cur), tien9(e.parts.PHI, cur), e.trang_thai])));
    }
    if (h.lien_ket.length) box.append(node("h3", "Liên kết tiền"), ntTable(["Tiền", "Tổng", "Trạng thái", "Phân bổ", ""], h.lien_ket.map(k => [`${k.bank_ngay} ${k.bank_ref || ""}`, vnd(k.tong), k.trang_thai + (k.ly_do_huy ? " · " + k.ly_do_huy : ""),
      k.child.map(c => `${c.logical_key}: ${vnd(c.so_tien)} ${c.trang_thai}`).join("; "),
      k.trang_thai !== "HUY" ? m9Btn("Gỡ cả liên kết", "link-button", () => m9Act("go", {id: k.id, ly_do: "Gỡ trên giao diện DEMO", khoa: khoa9()}, "Đã gỡ liên kết")) : ""])));
    box.classList.remove("hidden");
  }
  async function m9GoiY(t) {
    const out = $("m9-noi");
    try {
      const r = await m9Post("goi-y", {tien: t.id});
      const hl = m9.khoan_vay.flatMap(h => h.phien_ban.filter(v => v.hieu_luc_hom_nay).flatMap(v => [...v.lich.map(x => [x.dich, `${h.so_hop_dong} · ${x.nghia_vu_key} · còn ${x.con_lai ?? x.chan_noi}`]),
        ...v.khe_uoc.map(d => [d.dich, `${h.so_hop_dong} · GIẢI NGÂN ${d.ma} · còn ${d.con_lai ?? d.chan_noi}`])]));
      const rows = node("div"), them = (dich = "", so = "") => {
        const line = node("div", undefined, "demo-actions"), sel = m9Sel(hl, "— đích —"), inp = node("input"); sel.value = dich; inp.value = so; inp.inputMode = "numeric";
        sel.setAttribute("aria-label", "Đích phân bổ"); inp.setAttribute("aria-label", "Số tiền (minor)"); line.append(sel, inp, m9Btn("Bỏ", "link-button", () => line.remove())); rows.append(line);
      };
      const phanBo = () => [...rows.children].map(l => ({dich: l.children[0].value, so_tien: l.children[1].value.trim()})).filter(p => p.dich);
      const preview = node("div"), key = khoa9();
      out.replaceChildren(node("h4", `Nối tiền ${t.ngay} ${t.tham_chieu || ""} · ${tien9(t.so_tien, t.tien_te)} · ${t.chieu}`), node("p", r.ghi_chu),
        ...r.goi_y.map(g => m9Btn(`Dùng gợi ý: ${g.can_cu} · ${g.tong}${g.du_dich ? "" : " (thiếu đích)"}`, "button secondary", () => { rows.replaceChildren(); g.phan_bo.forEach(p => them(p.dich || "", p.so_tien)); })),
        rows, m9Btn("+ dòng", "link-button", () => them()), m9Btn("Xem trước", "button secondary", async () => {
          try { const p = await m9Post("xem-truoc", {tien: t.id, phan_bo: phanBo()});
            preview.replaceChildren(ntTable(["Đích", "Cấu phần", "Số nối", "Sức chứa", "Đã phân bổ", "Còn lại"], p.phan_bo.map(x => [x.logical_key, x.cau_phan, vnd(x.so_tien), vnd(x.suc_chua), vnd(x.da_phan_bo), vnd(x.con_lai)])),
              node("p", `Tổng ${vnd(p.tong)} · BANK còn ${vnd(p.bank.con_lai)}${p.chan.length ? " · CHẶN: " + p.chan.join(", ") : " · đủ điều kiện"}`),
              ...(p.chan.length ? [] : [m9Btn("Xác nhận nối", "button primary", () => m9Act("xac-nhan", {tien: t.id, phan_bo: phanBo(), khoa: key, xem_truoc_token: p.xem_truoc_token}, "Đã nối tiền"))]));
          } catch (e) { toast(e.message, true); } }), preview);
      if (r.goi_y.length) r.goi_y[0].phan_bo.forEach(p => them(p.dich || "", p.so_tien)); else them();
    } catch (error) { toast(error.message, true); }
  }
  async function m9Load() {
    try { m9 = await (await request("/api/m9" + (m9Ngay ? "?ngay=" + encodeURIComponent(m9Ngay) : ""))).json(); m9Render(); }
    catch (error) { $("m9-status").textContent = error.message; }
  }
  $("m9-refresh").addEventListener("click", () => m9Load());
  $("m9-doi-vai").addEventListener("click", () => m9Act("danh-tinh", {dang_nhap: $("m9-danh-tinh").value}, "Đã đổi vai mô phỏng"));
  $("m9-xem-ngay").addEventListener("click", () => { m9Ngay = $("m9-ngay").value; m9Load(); });
  window.addEventListener("hashchange", () => { if (location.hash === "#khoanvay") m9Load(); });
  // repair06: trạng thái đổi vai CHUNG của M2/M5/L11 (khai báo TRƯỚC khối M5 vì loader có thể chạy ngay khi khởi tạo trang).
  //   vaiGen   — ý định đổi vai mới nhất (tăng đồng bộ khi click);
  //   vaiCho   — chuỗi POST đổi vai tuần tự;
  //   vaiChan  — BARRIER: ≠ 0 từ lúc nhận ý định mới nhất đến khi CHÍNH ý định đó giải quyết (thành công/lỗi). Trong khoảng này m2Load/m5Load/l11Load
  //              KHÔNG gửi GET (máy chủ chưa xử lý xong POST vẫn trả vai cũ) — chỉ ghi tên module cần nạp vào `vaiChoTai`, trả ngay (không await ⇒
  //              không tự deadlock). Completion/lỗi/finally của ý định cũ không mở barrier; chỉ ý định mới nhất mở rồi nạp lại.
  let vaiGen = 0, vaiCho = Promise.resolve(), vaiChan = 0;
  const vaiChoTai = new Set();
  // M4-01C: seam CHUNG đăng ký người tham gia đổi vai (một phiên cookie máy chủ cho CRM/M2/M5/L11/M4). Mỗi người tham gia khai `xoa` (đồng bộ: tăng
  // epoch/form, xóa cache/lựa chọn/raw/DOM/nút) và `nap` (GET lại vai thật từ máy chủ). Đổi vai ở BẤT KỲ selector nào → xóa TẤT CẢ trước await đầu
  // tiên, một hàng POST tuần tự, barrier GET, chỉ ý định mới nhất mở barrier. M9 giữ nguyên trạng (không tham gia seam ở gói này).
  const vaiThanhVien = new Map();
  function dangKyVai(ten, xoa, nap) {
    if (typeof ten !== "string" || typeof xoa !== "function" || typeof nap !== "function") throw new Error("Đăng ký vai sai cấu trúc");
    vaiThanhVien.set(ten, {xoa, nap});
  }
  dangKyVai("crm", crmXoaTrangThai, () => crmLoad());
  dangKyVai("m5", m5XoaTrangThai, () => m5Load());
  dangKyVai("m2", m2XoaTrangThai, () => m2Load());
  dangKyVai("l11", l11XoaTrangThai, () => l11Load());
  // ---------------------------------------------------------------- M5 phiếu kho DEMO (cùng shell/token/cookie phiên với CRM)
  pages.phieukho = "Phiếu kho (số lượng)";
  let m5 = null, m5Chon = null, m5ChiTiet = null;
  // I1: epoch gắn actor/nguồn/PN/lựa chọn — đổi vai/bộ lọc/phiếu đang mở thì tăng epoch, xóa cache/panel/nút ngay; phản hồi của epoch cũ bị bỏ qua.
  let m5Epoch = 0, m5Gen = 0;
  // R2: epoch riêng của form nhận tệp — đổi nguồn/phạm vi/coverage/tệp/lỗi/khóa (hoặc đổi vai) thì claim đang đọc tệp bị vô hiệu
  let m5FormEpoch = 0;
  // R3: khóa FILE theo (actor, PN, phiếu, ba con trỏ, token basis) — sống qua refresh tự động; chỉ "Lần xuất mới" hoặc basis đổi mới có khóa mới
  const m5KhoaFile = new Map();
  const m5Khoa = () => "m5-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
  const m5TT = {NHAP: "Nháp", DA_DUYET: "Đã duyệt", DA_DAO: "Đã đảo", CHUA_MAP: "Chưa map"};
  function m5XoaForm() {  // xóa lựa chọn tệp/lỗi/khóa của form nhận (không gắn tệp của nguồn A sang B)
    m5FormEpoch += 1;
    $("m5-tl-native").value = ""; $("m5-tl-master").value = ""; $("m5-tl-loi").value = ""; $("m5-tl-khoa").value = "";
  }
  function m5XoaTrangThai() {
    m5Epoch += 1; m5 = null; m5Chon = null; m5ChiTiet = null;
    for (const id of ["m5-nang-luc", "m5-mau", "m5-nguon", "m5-phieu", "m5-viec", "m5-file-soat", "m5-mapping", "m5-gioi-han"]) $(id).replaceChildren();
    $("m5-chi-tiet").replaceChildren(); $("m5-chi-tiet").classList.add("hidden"); $("m5-tai-len").classList.add("hidden");
    $("m5-tl-nguon").replaceChildren(); $("m5-tl-coverage").replaceChildren(); m5XoaForm();
    $("m5-nguoi").textContent = "Đang tải…"; $("m5-status").textContent = "";
    return m5Epoch;
  }
  async function m5Post(path, body) { return (await request("/api/m5/" + path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})).json(); }
  // F1 (repair04): `conHieuLuc` = predicate ngữ cảnh của caller (vd form nhận tệp chưa đổi) kiểm cùng actor epoch ở MỌI điểm hoàn tất:
  // sau POST, trước toast, sau refresh và trong nhánh lỗi. Ngữ cảnh đã đổi → không toast/không status/không trả kết quả cho caller render
  // (capture đã commit vẫn giữ nguyên; danh sách nguồn sau refresh là nơi xem lần nhận đó).
  // UI05: cùng predicate đi tiếp vào refresh của thao tác (m5Load → m5Render → m5Detail) và được kiểm NGAY TRƯỚC mỗi assignment/cache/render/lỗi,
  // không chỉ sau await. Predicate sai trước refresh → bỏ refresh đó (người dùng bấm Làm mới để xem). Ghi chú trung tính tách hai trường hợp:
  // đã nhận phản hồi thành công (không gắn vào form mới) / lỗi hoặc mất kết nối (KHÔNG khẳng định máy chủ đã hay chưa ghi).
  const M5_FORM_DA_DOI = "Một lần gửi trước đã nhận phản hồi sau khi form/nguồn đổi — kết quả không gắn vào lựa chọn hiện tại; bấm Làm mới để xem bảng lần nhận nguồn.";
  const M5_FORM_DA_DOI_LOI = "Một lần gửi trước kết thúc bằng lỗi hoặc mất kết nối sau khi form/nguồn đổi — chưa xác định máy chủ đã ghi hay chưa; "
    + "không gắn vào lựa chọn hiện tại; bấm Làm mới để kiểm tra bảng lần nhận nguồn.";
  async function m5Act(path, body, ok, conHieuLuc = () => true) {
    const ep = m5Epoch;
    $("m5-status").textContent = "";
    try {
      const r = await m5Post(path, body);
      if (ep !== m5Epoch) return null;  // vai/lựa chọn đã đổi trong lúc chờ: không render kết quả cũ
      if (!conHieuLuc()) { $("m5-status").textContent = M5_FORM_DA_DOI; return null; }  // không toast, không refresh vào form mới
      toast(ok);
      await m5Load(conHieuLuc);  // refresh mang predicate: không assign/render/lỗi nếu form đổi trong lúc GET hoặc detail pending
      if (ep !== m5Epoch) return null;  // R1: đổi vai/lựa chọn trong lúc refresh sau POST — không trả kết quả cũ cho caller render
      if (!conHieuLuc()) { $("m5-status").textContent = M5_FORM_DA_DOI; return null; }
      return r;
    } catch (error) {
      if (ep !== m5Epoch) return null;
      if (!conHieuLuc()) { $("m5-status").textContent = M5_FORM_DA_DOI_LOI; return null; }
      toast(error.message, true); $("m5-status").textContent = error.message; return null;
    }
  }
  function m5Base64(buffer) {  // bytes nguyên văn → base64 (không TextDecoder/JSON.parse/Number)
    const bytes = new Uint8Array(buffer); let s = "";
    for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(s);
  }
  function m5DocTep(f) {  // nhận đúng File đã chụp lúc submit (không đọc lại input sau await)
    if (!f) return Promise.resolve(null);
    return new Promise((ok, loi) => { const r = new FileReader(); r.onload = () => ok(m5Base64(r.result)); r.onerror = () => loi(new Error("Không đọc được tệp " + f.name)); r.readAsArrayBuffer(f); });
  }
  let m5PhamViNhan = [];
  function m5Coverage(pv, covCu) {  // coverage theo đúng phạm vi đang chọn (không mặc định phạm vi đầu)
    m5PhamViNhan = pv;
    const chon = $("m5-tl-nguon").value, s = pv.find(x => JSON.stringify([x.source_instance_id, x.scope_ref]) === chon);
    const covs = s ? s.coverage_values : [];
    $("m5-tl-coverage").replaceChildren(...covs.map(c => { const o = node("option", c); o.value = c; return o; }));
    if (covCu && covs.includes(covCu)) $("m5-tl-coverage").value = covCu;
  }
  function m5KhoaFileLay(ctx, moi) {  // R3: cùng ngữ cảnh (actor/PN/phiếu/con trỏ/basis) → cùng khóa; "Lần xuất mới" → khóa mới
    const k = JSON.stringify(ctx);
    if (moi || !m5KhoaFile.has(k)) m5KhoaFile.set(k, m5Khoa());
    return m5KhoaFile.get(k);
  }
  function m5Btn(text, cls, fn) { const b = node("button", text, cls); b.addEventListener("click", fn); return b; }
  function m5Field(id, label, el) { el.id = id; const l = node("label", label); l.htmlFor = id; return [l, el]; }
  function m5Hold(codes) {
    const box = node("div");
    (codes || []).forEach(c => box.append(node("span", c, "m5-hold")));
    if (!(codes || []).length) box.append(node("span", "không có lý do giữ", "m5-ok"));
    return box;
  }
  const m5Hash = h => node("span", h ? h.slice(0, 12) + "…" : "— (NULL)", "m5-hash");
  const m5Raw = v => node("span", v === null || v === undefined ? "NULL" : typeof v === "string" ? JSON.stringify(v) : JSON.stringify(v), "m5-raw");
  function m5TomTat(r) {
    const p = r.promote ? ` · ${r.promote.trang_thai}${r.promote.phan_loai && r.promote.phan_loai.length ? " · " + r.promote.phan_loai.join(", ") : ""}` : "";
    return `${r.lap_lai ? "Biên nhận cũ (nhận lại cùng khóa, không ghi thêm)" : "Lần nhận mới"} · semantic ${r.semantic_digest ? r.semantic_digest.slice(0, 12) : "NULL"}`
      + ` · request ${r.request_digest ? r.request_digest.slice(0, 12) : "NULL"}${r.giu_cho && r.giu_cho.length ? " · giữ chờ: " + r.giu_cho.join(", ") : ""}${p}`;
  }
  async function m5Tai(path, name) {  // tải raw/file: bỏ nếu vai/lựa chọn đã đổi trong lúc chờ (không lưu bytes của vai cũ)
    const ep = m5Epoch;
    try {
      const blob = await (await request(path)).blob();
      if (ep !== m5Epoch) return;
      const url = URL.createObjectURL(blob), a = node("a"); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { if (ep === m5Epoch) toast(error.message, true); }
  }
  function m5RawLinks(c) {
    const box = node("div", undefined, "demo-actions");
    for (const role of ["NATIVE_DETAIL", "MASTER_RAW"]) box.append(m5Btn(role + " ↓", "link-button", () => m5Tai(`/api/m5/nguon/${encodeURIComponent(c.id)}/raw/${role}`, `${role}.json`)));
    return box;
  }
  function m5Render(conHieuLuc = () => true) {  // đồng bộ; predicate của refresh chỉ cần chuyển tiếp cho detail async
    if (!m5.cau_hinh) { $("m5-nguoi").textContent = m5.ly_do; $("m5-phieu").replaceChildren(empty("Chưa kết nối kho DEMO PostgreSQL", m5.ly_do)); return; }
    $("m5-danh-tinh").replaceChildren(...m5.danh_tinh_demo.map(d => { const o = node("option", `${d.dang_nhap} (${d.vai_tro})`); o.value = d.dang_nhap; o.selected = d.dang_nhap === m5.nguoi.dang_nhap; return o; }));
    const n = m5.nguoi;
    $("m5-nguoi").textContent = m5.khong_quyen ? `${n.dang_nhap} · ${m5.khong_quyen}` : `${n.dang_nhap} · ${n.vai_tro} · pháp nhân M5: ${(n.phap_nhan || []).join(", ") || "—"} · được làm: ${(n.hanh_dong || []).join(", ") || "chỉ xem"}`;
    $("m5-nang-luc").replaceChildren(m5.nang_luc_nguon.length ? ntTable(["Nguồn", "Năng lực nguồn", "PN đích (SOURCE_MAP)"], m5.nang_luc_nguon.map(c => [c.source_instance_id, c.hanh_dong, c.phap_nhan_dich || ""]))
      : node("p", "Vai này không có năng lực nguồn (nhận/đọc raw/mapping).", "upload-status"));
    const coIntake = m5.nang_luc_nguon.some(c => c.hanh_dong === "INTAKE");
    $("m5-mau").replaceChildren(...(coIntake ? m5.mau.map(m => m5Btn("Nhận mẫu " + m, "button secondary", async () => {
      const ep = m5Epoch, r = await m5Act("nhan", {mau: m, khoa: m5Khoa()}, "Đã nhận nguồn"); if (r && ep === m5Epoch) $("m5-status").textContent = m5TomTat(r); }))
      : [node("span", "Vai này không có năng lực INTAKE — không nhận nguồn.", "upload-status")]));
    // I5: form nhận tệp thật — chỉ nguồn/phạm vi có năng lực INTAKE do máy chủ trả; coverage theo profile; khóa giữ được để nhận lại
    const nguonIntake = new Set(m5.nang_luc_nguon.filter(c => c.hanh_dong === "INTAKE").map(c => c.source_instance_id));
    const pv = (m5.pham_vi_nguon || []).filter(s => nguonIntake.has(s.source_instance_id));
    $("m5-tai-len").classList.toggle("hidden", !(coIntake && pv.length && m5.may_chu_nhan));
    // R2: refresh giữ đúng nguồn/phạm vi/coverage đang chọn nếu còn hợp lệ; nếu lựa chọn biến mất thì xóa tệp/lỗi/khóa đã chọn (không gắn sang nguồn khác)
    const chonCu = $("m5-tl-nguon").value, covCu = $("m5-tl-coverage").value;
    $("m5-tl-nguon").replaceChildren(...pv.map(s => { const o = node("option", `${s.source_instance_id} · ${s.scope_ref} · kho ${s.ma_kho}`); o.value = JSON.stringify([s.source_instance_id, s.scope_ref]); return o; }));
    if (chonCu && pv.some(s => JSON.stringify([s.source_instance_id, s.scope_ref]) === chonCu)) $("m5-tl-nguon").value = chonCu;
    else if (chonCu) m5XoaForm();
    m5Coverage(pv, covCu);
    if (!$("m5-tl-khoa").value) $("m5-tl-khoa").value = m5Khoa();
    $("m5-nguon").replaceChildren(m5.nguon.length ? ntTable(["Nhận lúc", "Nguồn", "Khóa", "Coverage", "Lỗi nguồn báo", "Semantic", "Lý do giữ chờ", "Raw"], m5.nguon.map(c => [
      date(c.nhan_luc), c.source_instance_id, c.client_key, c.coverage, (c.reported_errors || []).join(", "), m5Hash(c.ket_qua.semantic_digest),
      m5Hold([...(c.ket_qua.giu_cho || []), ...(c.ket_qua.reader_issues || [])]), c.doc_raw ? m5RawLinks(c) : "không có READ_SOURCE"]))
      : empty("Chưa có lần nhận nguồn trong phạm vi của vai này", "Vai có INTAKE bấm Nhận mẫu."));
    const ids = ["m5-phieu", "m5-viec", "m5-file-soat"];
    if (m5.khong_quyen) { ids.forEach(id => $(id).replaceChildren(empty("Không có quyền M5 nghiệp vụ", m5.khong_quyen))); $("m5-chi-tiet").classList.add("hidden"); }
    else {
      $("m5-phieu").replaceChildren(m5.phieu.length ? ntTable(["Pháp nhân", "Nguồn", "Số phiếu", "Kho", "Ngày", "Trạng thái nguồn (mới nhất)", "Lý do giữ/phân loại", "Lịch sử", "Đã chấp nhận", ""], m5.phieu.map(p => [
        p.phap_nhan, p.nguon, p.so_phieu, p.ma_kho, p.ngay || "chưa có ngày", m5TT[p.trang_thai_nguon] || p.trang_thai_nguon || "", m5Hold(p.phan_loai),
        `${p.so_noi_dung} nội dung · ${p.so_quan_sat} quan sát · ${p.history_state || ""}`, p.accepted_source_observation_id ? (p.eligible_content_id ? "Có · đủ điều kiện" : "Có · chưa đủ điều kiện") : "Chưa",
        m5Btn("Mở ↗", "link-button", () => { m5Epoch += 1; m5Chon = p.id; m5ChiTiet = null; $("m5-chi-tiet").replaceChildren(); m5Detail(); })]))
        : empty("Chưa có phiếu trong pháp nhân được xem", "Phiếu chỉ vào pháp nhân khi kho nguồn đã có mapping đã duyệt và nội dung đọc được đủ ngày/graph."));
      $("m5-viec").replaceChildren(node("h4", "Việc đang mở"), m5.viec.length ? ntTable(["Pháp nhân", "Loại", "Tóm tắt", "Lý do chờ"], m5.viec.map(v => [v.phap_nhan, v.loai, v.tom_tat || "", v.ly_do_cho.join(", ")])) : empty("Không có việc mở", ""));
      $("m5-file-soat").replaceChildren(node("h4", "File soát"), m5.file_soat.length ? ntTable(["Pháp nhân", "Tệp", "SHA-256", "Lúc", ""], m5.file_soat.map(f => [f.phap_nhan, f.ten, m5Hash(f.hash), f.luc ? date(f.luc) : "",
        m5Btn("Tải ↓", "link-button", () => m5Tai(`/api/m5/file-soat/${encodeURIComponent(f.id)}`, f.ten))])) : empty("Chưa xuất file soát", "Mở phiếu rồi bấm Xuất file soát."));
    }
    m5Mapping();
    $("m5-gioi-han").replaceChildren(node("p", m5.l11 || "Liên kết số lượng với hóa đơn (L11) là gói kế tiếp — chưa có số đã khớp/còn lại.", "upload-status"),
      m5Btn("Xem tồn nguồn", "button secondary", () => m5GioiHan("ton-nguon")), m5Btn("Xem kiểm kê", "button secondary", () => m5GioiHan("kiem-ke")));
    if (m5Chon) m5Detail(conHieuLuc);
  }
  async function m5GioiHan(path) {
    const ep = m5Epoch;
    try { const r = await (await request("/api/m5/" + path)).json(); if (ep === m5Epoch) $("m5-status").textContent = `${r.trang_thai} · ${r.gioi_han}`; }
    catch (error) { if (ep === m5Epoch) { toast(error.message, true); $("m5-status").textContent = error.message; } }
  }
  function m5Mapping() {
    const caps = m5.nang_luc_nguon.filter(c => c.hanh_dong === "SOURCE_MAP"), box = node("div");
    if (!caps.length) { $("m5-mapping").replaceChildren(empty("Vai này không có năng lực SOURCE_MAP", "Mapping cần CFO có SOURCE_MAP đúng pháp nhân đích và quyền V4.")); return; }
    const [l1, inst] = m5Field("m5-map-nguon", "Nguồn", ntSelect("m5-map-nguon", [...new Set(caps.map(c => c.source_instance_id))]));
    const [l2, kho] = m5Field("m5-map-kho", "Kho nguồn (MaKho)", ntInput("m5-map-kho", "KHO_DEMO"));
    const [l3, pn] = m5Field("m5-map-pn", "Pháp nhân đích", ntSelect("m5-map-pn", [...new Set(caps.map(c => c.phap_nhan_dich))]));
    const [l4, rev] = m5Field("m5-map-rev", "Revision cuối đã biết", ntInput("m5-map-rev", "0", "number"));
    const [l5, ly] = m5Field("m5-map-ly-do", "Lý do", ntInput("m5-map-ly-do", ""));
    const line = node("div", undefined, "demo-actions");
    line.append(l1, inst, l2, kho, l3, pn, l4, rev, l5, ly, m5Btn("CFO tạo revision mapping", "button secondary", async () => {
      const ep = m5Epoch, r = await m5Act("mapping", {source_instance: inst.value, ma_kho: kho.value.trim(), phap_nhan: pn.value, revision_hien_tai: Number(rev.value), ly_do: ly.value, khoa: m5Khoa()}, "Đã ghi revision mapping");
      if (r && ep === m5Epoch) $("m5-status").textContent = `Mapping ${r.reference_id} r${r.revision} → ${r.phap_nhan}${r.anh_huong_phieu.length ? " · mở việc ảnh hưởng " + r.anh_huong_phieu.length + " phiếu" : ""}`; }));
    box.append(line);
    $("m5-mapping").replaceChildren(box);
  }
  async function m5Detail(conHieuLuc = () => true) {  // UI05: detail do refresh của thao tác kéo theo mang cùng predicate
    const box = $("m5-chi-tiet"), ep = m5Epoch, chon = m5Chon;
    if (!m5Chon) { box.classList.add("hidden"); return; }
    if (!conHieuLuc()) return;  // ngữ cảnh thao tác đã đổi trước khi tải detail: bỏ, không đụng panel
    let d;
    try { d = await (await request("/api/m5/phieu/" + encodeURIComponent(chon))).json(); }
    catch (error) { if (ep === m5Epoch && chon === m5Chon && conHieuLuc()) { box.classList.add("hidden"); toast(error.message, true); } return; }
    if (ep !== m5Epoch || chon !== m5Chon || !conHieuLuc()) return;  // I1/UI05: vai/phiếu cũ hoặc form của thao tác đã đổi — trước cache/render
    m5ChiTiet = d;
    const top = node("div", undefined, "demo-actions");
    box.classList.remove("hidden");
    top.append(m5Btn("Đóng", "link-button", () => { m5Epoch += 1; m5Chon = null; m5ChiTiet = null; box.replaceChildren(); box.classList.add("hidden"); }));
    const coSo = d.co_so_file && d.co_so_file.co_so_sha256;
    if (d.duoc.M5_FILE_SOAT && coSo) {  // I4/R3/R4: expected = ba con trỏ + token basis toàn graph do máy chủ trả; khóa giữ qua refresh cùng ngữ cảnh
      const ctx = [(m5 && m5.nguoi && m5.nguoi.dang_nhap) || "", d.phap_nhan, d.id, d.con_tro.latest_observation_id, d.con_tro.accepted_source_observation_id,
        d.con_tro.eligible_content_id, coSo];
      const than = () => ({phieu_id: d.id, khoa: m5KhoaFileLay(ctx, false), latest_truoc: d.con_tro.latest_observation_id,
        accepted_truoc: d.con_tro.accepted_source_observation_id, eligible_truoc: d.con_tro.eligible_content_id, co_so_truoc: coSo});
      top.append(m5Btn("Xuất file soát phiếu", "button secondary", () => m5Act("xuat-file-soat", than(), "Đã xuất file soát M5")),
        m5Btn("Lần xuất mới (khóa mới)", "link-button", () => { m5KhoaFileLay(ctx, true); toast("Đã tạo khóa xuất mới cho phiếu này"); }),
        node("span", `basis ${coSo.slice(0, 12)}… · kỳ ${d.co_so_file.ky || "?"}${d.co_so_file.ky_da_khoa ? " (đã khóa — không xuất)" : ""}`, "m5-hash"));
    }
    const ct = node("div", undefined, "m5-con-tro"), ptr = (label, v) => { const c = node("div"); c.append(node("strong", label), node("br"), m5Hash(v)); return c; };
    ct.append(ptr("Quan sát mới nhất (thứ tự nhận)", d.con_tro.latest_observation_id), ptr("Nguồn đã chấp nhận (review V8)", d.con_tro.accepted_source_observation_id),
      ptr("Nội dung đủ điều kiện soát", d.con_tro.eligible_content_id));
    const parts = [node("h2", `Phiếu ${d.so_phieu} · ${d.phap_nhan} · ${d.nguon} · kho ${d.ma_kho}`), top, ct, node("p", d.l11, "upload-status")];
    for (const v of d.noi_dung) {
      parts.push(node("h4", `Nội dung v${v.version} · ${m5TT[v.trang_thai_nguon] || v.trang_thai_nguon} (nguồn ghi "${v.trang_thai_raw}") · ngày ${v.ngay} · semantic ${v.semantic_sha256.slice(0, 12)}…`),
        ntTable(["STT", "ID_Dong", "MaHang", "Loại số lượng", "Số lượng nguồn (nguyên văn)", "Chuẩn hóa", "Độ chính xác", "ĐVT nguồn", "Đơn vị định nghĩa"], v.dong.map(l => [
          String(l.stt), l.id_dong, l.ma_hang || "", l.loai_so_luong, m5Raw(l.so_luong_nguon), l.so_luong_chuan_hoa === null ? "NULL (chưa đủ căn cứ)" : l.so_luong_chuan_hoa,
          l.do_chinh_xac, l.dvt_nguon === null ? "NULL" : l.dvt_nguon === "" ? "(rỗng)" : l.dvt_nguon, l.don_vi || "NULL"])));
    }
    const coReview = d.duoc.M5_SOURCE_REVIEW_V8;
    parts.push(node("h4", "Lịch sử quan sát nguồn"), ntTable(["#", "Nhận lúc", "Trạng thái nguồn", "Nội dung", "Phân loại / lý do giữ", "Lịch sử", "Review"], d.lich_su.map(o => {
      const ver = d.noi_dung.find(v => v.id === o.content_id), cell = node("div", undefined, "demo-actions");
      if (coReview) {
        const [l, ly] = m5Field("m5-ly-do-" + o.id, "Lý do", node("input"));
        const gui = qd => m5Act("nguon/kiem-lai", {phieu_id: d.id, observation_id: o.id, quyet_dinh: qd, accepted_truoc: d.con_tro.accepted_source_observation_id,
          eligible_truoc: d.con_tro.eligible_content_id, latest_truoc: d.con_tro.latest_observation_id, ly_do: ly.value, khoa: m5Khoa()}, qd === "CHAP_NHAN_NGUON" ? "Đã chấp nhận nguồn" : "Đã ghi giữ chờ");
        cell.append(l, ly, m5Btn("CFO chấp nhận nguồn", "button secondary", () => gui("CHAP_NHAN_NGUON")), m5Btn("Giữ chờ", "link-button", () => gui("GIU_CHO")));
      }
      return [String(o.thu_tu), date(o.known_at), m5TT[o.trang_thai_nguon] || o.trang_thai_nguon, ver ? "v" + ver.version : "", m5Hold(o.phan_loai), o.history_state, coReview ? cell : ""];
    })));
    if (d.anh_xa.length) parts.push(node("h4", "Mapping kho nguồn"), ntTable(["Mapping", "Rev", "Kho", "Trạng thái", "Hiệu lực từ", "Đến", "Quyết định"], d.anh_xa.map(m => [m.reference_id, String(m.revision), m.subject_key, m.state, date(m.valid_from), m.valid_to ? date(m.valid_to) : "", m.nguon_quyet_dinh])));
    if (d.viec.length) parts.push(node("h4", "Việc của phiếu"), ntTable(["Loại", "Tóm tắt", "Lý do chờ", "Trạng thái"], d.viec.map(v => [v.loai, v.tom_tat || "", v.ly_do_cho.join(", "), v.trang_thai])));
    box.replaceChildren(...parts);
  }
  // UI05: `conHieuLuc` mặc định đúng (Làm mới/đổi vai/lọc/hash); refresh của upload truyền predicate form — kiểm trước GET, trước assignment
  // `m5 = s`/render và trước ghi lỗi; chuyển tiếp cho detail async.
  async function m5Load(conHieuLuc = () => true) {
    if (vaiDangChan("m5")) return;  // repair06: đổi vai đang chờ — không GET vai cũ; nạp lại khi ý định mới nhất giải quyết
    const ep = m5Epoch, q = new URLSearchParams();
    if (!conHieuLuc()) return;  // ngữ cảnh thao tác đã đổi trước refresh: bỏ refresh này
    const gen = ++m5Gen, moiNhat = () => gen === m5Gen && ep === m5Epoch && conHieuLuc();  // M4-01C2: GET cũ hơn không đè GET mới cùng epoch
    for (const [k, id] of [["phap_nhan", "m5-loc-pn"], ["ma_kho", "m5-loc-kho"], ["ky", "m5-loc-ky"], ["trang_thai", "m5-loc-tt"]]) if ($(id).value.trim()) q.set(k, $(id).value.trim());
    try {
      const s = await (await request("/api/m5" + (q.toString() ? "?" + q : ""))).json();
      if (!moiNhat()) return;  // epoch/thế hệ cũ hoặc form của thao tác đã đổi — bỏ, không assign/render
      m5 = s; m5Render(conHieuLuc);
    } catch (error) { if (moiNhat()) $("m5-status").textContent = error.message; }
  }
  $("m5-refresh").addEventListener("click", () => m5Load());
  $("m5-loc").addEventListener("click", () => { m5XoaTrangThai(); m5Load(); });
  $("m5-doi-vai").addEventListener("click", () => {
    const login = $("m5-danh-tinh").value;  // repair05: xóa ngay cache/chi tiết/raw/file/nút của vai cũ ở CẢ M2/M5/L11, trước khi đổi
    return doiVaiTuanTu(() => m5Post("danh-tinh", {dang_nhap: login}), "m5-status", "m5");
  });
  $("m5-tl-khoa-moi").addEventListener("click", () => { m5FormEpoch += 1; $("m5-tl-khoa").value = m5Khoa(); });
  // R2: đổi nguồn/phạm vi → coverage theo phạm vi mới, xóa tệp/lỗi/khóa của nguồn cũ; đổi bất kỳ claim nào → claim đang đọc tệp bị vô hiệu
  $("m5-tl-nguon").addEventListener("change", () => { m5XoaForm(); m5Coverage(m5PhamViNhan, null); $("m5-tl-khoa").value = m5Khoa(); });
  for (const id of ["m5-tl-coverage", "m5-tl-native", "m5-tl-master", "m5-tl-loi", "m5-tl-khoa"]) {
    $(id).addEventListener("change", () => { m5FormEpoch += 1; });
    $(id).addEventListener("input", () => { m5FormEpoch += 1; });
  }
  $("m5-tai-len").addEventListener("submit", async event => {
    event.preventDefault();
    const ep = m5Epoch, fe = m5FormEpoch;
    try {
      // chụp TOÀN BỘ claim + đối tượng File đồng bộ TRƯỚC khi đọc tệp; sau await chỉ dùng bản chụp, không đọc lại form
      const [inst, scope] = JSON.parse($("m5-tl-nguon").value || "[]");
      const claim = {source_instance: inst, scope_ref: scope, coverage: $("m5-tl-coverage").value,
        reported_errors: $("m5-tl-loi").value.split(/\r?\n/).map(x => x.trim()).filter(Boolean), khoa: $("m5-tl-khoa").value.trim()};
      const fNative = ($("m5-tl-native").files || [])[0] || null, fMaster = ($("m5-tl-master").files || [])[0] || null;
      const [native, master] = await Promise.all([m5DocTep(fNative), m5DocTep(fMaster)]);
      if (ep !== m5Epoch) return;
      if (fe !== m5FormEpoch) { $("m5-status").textContent = "Form nhận tệp đã đổi trong lúc đọc tệp — kiểm tra rồi gửi lại."; return; }
      const body = {...claim};
      if (native !== null) body.native_b64 = native;
      if (master !== null) body.master_b64 = master;
      const formCon = () => fe === m5FormEpoch;  // F1: predicate form-current đi xuyên POST/refresh/success/error
      const r = await m5Act("nhan", body, "Đã nhận tệp nguồn", formCon);
      if (r && ep === m5Epoch && formCon()) $("m5-status").textContent = m5TomTat(r);
    } catch (error) {
      if (ep !== m5Epoch) return;
      if (fe !== m5FormEpoch) { $("m5-status").textContent = M5_FORM_DA_DOI_LOI; return; }
      toast(error.message, true); $("m5-status").textContent = error.message;
    }
  });
  window.addEventListener("hashchange", () => { if (location.hash === "#phieukho") m5Load(); });
  if (location.hash === "#phieukho") m5Load();
  // ---------------------------------------------------------------- M2 hóa đơn mua XML DEMO (R15) — cùng shell/token/cookie, cùng mẫu epoch/form/khóa như M5
  pages.hoadonmua = "Hóa đơn mua XML";
  let m2 = null, m2Chon = null, m2Epoch = 0, m2FormEpoch = 0, m2PhamVi = [];
  let m2DocGen = 0, m2CtGen = 0;  // F2: thế hệ GET danh sách/chi tiết — chỉ phản hồi của lần GET bắt đầu SAU CÙNG được vẽ (A trễ không đè B)
  const m2KhoaThaoTac = new Map();  // khóa thao tác theo (actor, hóa đơn, thao tác, đối tượng, token đồ thị) — sống qua refresh; đồ thị đổi → khóa mới
  const m2Khoa = () => "m2-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
  function m2KhoaLay(ctx) { const k = JSON.stringify(ctx); if (!m2KhoaThaoTac.has(k)) m2KhoaThaoTac.set(k, m2Khoa()); return m2KhoaThaoTac.get(k); }
  const M2_FORM_DA_DOI = "Một lần gửi trước đã nhận phản hồi sau khi form/nguồn đổi — kết quả không gắn vào lựa chọn hiện tại; bấm Làm mới để xem.";
  const M2_FORM_DA_DOI_LOI = "Một lần gửi trước kết thúc bằng lỗi hoặc mất kết nối sau khi form/nguồn đổi — chưa xác định máy chủ đã ghi hay chưa; bấm Làm mới để kiểm tra.";
  function m2XoaForm() { m2FormEpoch += 1; for (const id of ["m2-tl-native", "m2-tl-crosswalk", "m2-tl-loi", "m2-tl-khoa"]) $(id).value = ""; }
  function m2XoaTrangThai() {
    m2Epoch += 1; m2 = null; m2Chon = null;
    for (const id of ["m2-nang-luc", "m2-nguon", "m2-hoa-don", "m2-mapping"]) $(id).replaceChildren();
    $("m2-chi-tiet").replaceChildren(); $("m2-chi-tiet").classList.add("hidden"); $("m2-tai-len").classList.add("hidden");
    $("m2-tl-nguon").replaceChildren(); $("m2-tl-coverage").replaceChildren(); m2XoaForm();
    $("m2-nguoi").textContent = "Đang tải…"; $("m2-status").textContent = "";
  }
  async function m2Post(path, body) { return (await request("/api/m2/" + path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})).json(); }
  async function m2Tai(receipt, role) {  // F1: tải raw M2 chỉ khi vẫn đúng epoch M2 + vai + lần nhận còn READ_SOURCE trong state hiện hành
    const ep = m2Epoch, actor = m2 && m2.nguoi ? m2.nguoi.dang_nhap : null;
    const conHieuLuc = () => ep === m2Epoch && !!m2 && !!m2.nguoi && m2.nguoi.dang_nhap === actor
      && (m2.nguon || []).some(c => c.id === receipt && c.doc_raw);
    if (!conHieuLuc()) return;
    try {
      const blob = await (await request(`/api/m2/nguon/${encodeURIComponent(receipt)}/raw/${role}`)).blob();
      if (!conHieuLuc()) return;
      const url = URL.createObjectURL(blob), a = node("a"); a.href = url; a.download = `${role}-${String(receipt).slice(0, 8)}`; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { if (conHieuLuc()) { toast(error.message, true); $("m2-status").textContent = error.message; } }
  }
  async function m2Act(path, body, ok, conHieuLuc = () => true) {
    const ep = m2Epoch;
    $("m2-status").textContent = "";
    try {
      const r = await m2Post(path, body);
      if (ep !== m2Epoch) return null;
      if (!conHieuLuc()) { $("m2-status").textContent = M2_FORM_DA_DOI; return null; }
      toast(ok);
      await m2Load(conHieuLuc);
      if (ep !== m2Epoch) return null;
      if (!conHieuLuc()) { $("m2-status").textContent = M2_FORM_DA_DOI; return null; }
      return r;
    } catch (error) {
      if (ep !== m2Epoch) return null;
      if (!conHieuLuc()) { $("m2-status").textContent = M2_FORM_DA_DOI_LOI; return null; }
      toast(error.message, true); $("m2-status").textContent = error.message; return null;
    }
  }
  function m2TomTat(r) {
    const p = r.promote && r.promote.items ? ` · đưa vào M2: ${r.promote.items.length} quan sát` : "";
    const u = r.promote && r.promote.candidates && r.promote.candidates.length ? ` · ứng viên/HOLD: ${r.promote.candidates.map(c => c.reason || c.state).join(", ")}` : "";
    return `${r.lap_lai ? "Biên nhận cũ (nhận lại cùng khóa, không ghi thêm)" : "Lần nhận mới"} · ${r.artifact_kind || ""} · ${r.so_dong_nguon ?? 0} dòng nguồn dẫn xuất${p}${u}`;
  }
  function m2Coverage(covCu) {
    const chon = $("m2-tl-nguon").value, s = m2PhamVi.find(x => JSON.stringify([x.source_instance_id, x.scope_ref]) === chon);
    const covs = s ? s.coverage_values : [];
    $("m2-tl-coverage").replaceChildren(...covs.map(c => { const o = node("option", c); o.value = c; return o; }));
    if (covCu && covs.includes(covCu)) $("m2-tl-coverage").value = covCu;
  }
  function m2Render(conHieuLuc = () => true) {
    if (!m2.cau_hinh) { $("m2-nguoi").textContent = m2.ly_do; $("m2-hoa-don").replaceChildren(empty("Chưa kết nối kho DEMO PostgreSQL", m2.ly_do)); return; }
    $("m2-danh-tinh").replaceChildren(...m2.danh_tinh_demo.map(d => { const o = node("option", `${d.dang_nhap} (${d.vai_tro})`); o.value = d.dang_nhap; o.selected = d.dang_nhap === m2.nguoi.dang_nhap; return o; }));
    const n = m2.nguoi;
    $("m2-nguoi").textContent = m2.khong_quyen ? `${n.dang_nhap} · ${m2.khong_quyen}` : `${n.dang_nhap} · ${n.vai_tro} · pháp nhân M2: ${(n.phap_nhan || []).join(", ") || "—"} · được làm: ${(n.hanh_dong || []).join(", ") || "chỉ xem"}`;
    $("m2-nang-luc").replaceChildren(m2.nang_luc_nguon.length ? ntTable(["Nguồn", "Năng lực nguồn", "PN đích (SOURCE_MAP)"], m2.nang_luc_nguon.map(c => [c.source_instance_id, c.hanh_dong, c.phap_nhan_dich || ""]))
      : node("p", "Vai này không có năng lực nguồn hóa đơn.", "upload-status"));
    const nguonIntake = new Set(m2.nang_luc_nguon.filter(c => c.hanh_dong === "INTAKE").map(c => c.source_instance_id));
    m2PhamVi = (m2.pham_vi_nguon || []).filter(s => nguonIntake.has(s.source_instance_id));
    $("m2-tai-len").classList.toggle("hidden", !(m2PhamVi.length && m2.may_chu_nhan));
    const chonCu = $("m2-tl-nguon").value, covCu = $("m2-tl-coverage").value;
    $("m2-tl-nguon").replaceChildren(...m2PhamVi.map(s => { const o = node("option", `${s.source_instance_id} · ${s.scope_ref} · ${s.company_keys.join("/")}`); o.value = JSON.stringify([s.source_instance_id, s.scope_ref]); return o; }));
    if (chonCu && m2PhamVi.some(s => JSON.stringify([s.source_instance_id, s.scope_ref]) === chonCu)) $("m2-tl-nguon").value = chonCu;
    else if (chonCu) m2XoaForm();
    m2Coverage(covCu);
    const mauCu = $("m2-tl-mau").value;
    $("m2-tl-mau").replaceChildren(...(m2.mau || []).map(m => { const o = node("option", m); o.value = m; return o; }));
    if (mauCu) $("m2-tl-mau").value = mauCu;
    if (!$("m2-tl-khoa").value) $("m2-tl-khoa").value = m2Khoa();
    if (m2.gioi_han_tai_len_byte) $("m2-tl-gioi-han").textContent = `Giới hạn mỗi lần nhận: tổng tệp hóa đơn + crosswalk tối đa ${m2.gioi_han_tai_len_byte} byte (bản DEMO chưa hỗ trợ tệp lớn hơn; tệp vượt giới hạn bị từ chối trước khi gửi).`;
    $("m2-nguon").replaceChildren(m2.nguon.length ? ntTable(["Nhận lúc", "Nguồn", "Khóa", "Coverage (báo / hiệu lực)", "Lỗi nguồn báo", "Raw"], m2.nguon.map(c => [
      date(c.nhan_luc), c.source_instance_id, c.client_key, `${c.coverage} / ${c.coverage_hieu_luc}`, (c.reported_errors || []).join(", "),
      c.doc_raw ? m5Btn("NATIVE ↓", "link-button", () => m2Tai(c.id, "NATIVE")) : "không có READ_SOURCE"]))
      : empty("Chưa có lần nhận hóa đơn trong phạm vi của vai này", "Vai có INTAKE chọn tệp hoặc mẫu rồi nhận."));
    if (m2.khong_quyen) { $("m2-hoa-don").replaceChildren(empty("Không có quyền M2 nghiệp vụ", m2.khong_quyen)); $("m2-chi-tiet").classList.add("hidden"); }
    else {
      $("m2-hoa-don").replaceChildren(m2.hoa_don.length ? ntTable(["Pháp nhân", "Chiều", "MST bán", "Mẫu/Ký hiệu/Số", "Ngày lập", "Phân loại quan sát mới nhất", "Nguồn đã chọn", ""], m2.hoa_don.map(h => [
        h.phap_nhan, h.chieu, h.mst_ban, `${h.mau_so} · ${h.ky_hieu} · ${h.so_chuan}`, h.ngay_lap || "", m5Hold(h.phan_loai),
        h.accepted_source_observation_id ? (h.eligible_content_id ? "Có · nội dung đủ căn cứ" : "Có · đang HOLD") : "Chưa",
        m5Btn("Mở ↗", "link-button", () => { m2Epoch += 1; m2Chon = h.id; $("m2-chi-tiet").replaceChildren(); m2Detail(); })]))
        : empty("Chưa có hóa đơn mua trong pháp nhân được xem", "Hóa đơn chỉ vào pháp nhân khi công ty mua đã có mapping và đủ định danh/ngày/tiền tệ."));
    }
    m2MappingCongTy();
    if (m2Chon) m2Detail(conHieuLuc);
  }
  function m2MappingCongTy() {
    const caps = m2.nang_luc_nguon.filter(c => c.hanh_dong === "SOURCE_MAP");
    if (!caps.length) { $("m2-mapping").replaceChildren(empty("Vai này không có năng lực SOURCE_MAP", "Mapping cần CFO có SOURCE_MAP đúng pháp nhân đích và quyền V4.")); return; }
    const keys = [...new Set((m2.pham_vi_nguon || []).flatMap(s => s.company_keys))];
    const [l1, inst] = m5Field("m2-map-nguon", "Nguồn", ntSelect("m2-map-nguon", [...new Set(caps.map(c => c.source_instance_id))]));
    const [l2, key] = m5Field("m2-map-key", "Company key", ntSelect("m2-map-key", keys));
    const [l3, pn] = m5Field("m2-map-pn", "Pháp nhân đích", ntSelect("m2-map-pn", [...new Set(caps.map(c => c.phap_nhan_dich))]));
    const [l4, rev] = m5Field("m2-map-rev", "Revision cuối đã biết", ntInput("m2-map-rev", "1", "number"));
    const [l5, ly] = m5Field("m2-map-ly-do", "Lý do", ntInput("m2-map-ly-do", ""));
    const line = node("div", undefined, "demo-actions");
    line.append(l1, inst, l2, key, l3, pn, l4, rev, l5, ly, m5Btn("CFO tạo revision mapping công ty", "button secondary", async () => {
      const ep = m2Epoch, r = await m2Act("mapping", {source_instance: inst.value, company_key: key.value, phap_nhan: pn.value, revision_hien_tai: Number(rev.value), ly_do: ly.value, khoa: m2Khoa()}, "Đã ghi mapping công ty");
      if (r && ep === m2Epoch) $("m2-status").textContent = `Mapping ${r.reference_id} r${r.revision} → ${r.phap_nhan}`; }));
    $("m2-mapping").replaceChildren(line);
  }
  async function m2Detail(conHieuLuc = () => true) {
    const box = $("m2-chi-tiet"), ep = m2Epoch, chon = m2Chon;
    if (!m2Chon) { box.classList.add("hidden"); return; }
    if (!conHieuLuc()) return;
    const gen = ++m2CtGen, moiNhat = () => gen === m2CtGen && ep === m2Epoch && chon === m2Chon && conHieuLuc();
    let d;
    try { d = await (await request("/api/m2/hoa-don/" + encodeURIComponent(chon))).json(); }
    catch (error) { if (moiNhat()) { box.classList.add("hidden"); toast(error.message, true); } return; }
    if (!moiNhat()) return;
    const actor = (m2 && m2.nguoi && m2.nguoi.dang_nhap) || "";
    box.classList.remove("hidden");
    const top = node("div", undefined, "demo-actions");
    top.append(m5Btn("Đóng", "link-button", () => { m2Epoch += 1; m2Chon = null; box.replaceChildren(); box.classList.add("hidden"); }),
      node("span", `đồ thị ${d.expected_graph ? d.expected_graph.slice(0, 12) + "…" : "—"}`, "m5-hash"));
    const ct = node("div", undefined, "m5-con-tro"), ptr = (label, v) => { const c = node("div"); c.append(node("strong", label), node("br"), m5Hash(v)); return c; };
    ct.append(ptr("Quan sát mới nhất", d.con_tro.latest_observation_id), ptr("Nguồn đã chọn", d.con_tro.accepted_source_observation_id), ptr("Nội dung đủ căn cứ", d.con_tro.eligible_content_id));
    const parts = [node("h2", `Hóa đơn ${d.dinh_danh.slice(2).join(" · ")} · ${d.phap_nhan} · ${d.chieu}`), top, ct, node("p", d.l11, "upload-status")];
    parts.push(node("h4", "Phiên bản nội dung"), ntTable(["Bản", "Semantic", "Ngày lập", "Tiền tệ nguồn", "Tiền (minor)", "Chứng từ core"], d.phien_ban.map(v => [
      "v" + v.phien_ban, m5Hash(v.semantic_sha256), v.ngay_lap, v.tien_te, v.money_basis_state + " (NULL, chưa căn cứ)", m5Hash(v.chung_tu_id)])));
    const coReview = d.duoc.M2_SOURCE_REVIEW;
    parts.push(node("h4", "Quan sát nguồn"), ntTable(["#", "Nhận lúc", "Phân loại", "Native SHA", "ZIP entry", "Fiscal", "Chọn nguồn"], d.quan_sat.map(o => {
      const cell = node("div", undefined, "demo-actions");
      if (coReview && o.id === d.con_tro.latest_observation_id) {
        const [l, ly] = m5Field("m2-rv-" + o.id, "Lý do", node("input"));
        cell.append(l, ly, m5Btn("CFO chọn nguồn mới nhất", "button secondary", () => m2Act("nguon/kiem-lai", {hoa_don_id: d.id, observation_id: o.id, expected_graph: d.expected_graph,
          ly_do: ly.value, khoa: m2KhoaLay([actor, d.id, "REVIEW", o.id, d.expected_graph])}, "Đã chọn nguồn")));
      }
      return [String(o.thu_tu), o.known_at_server ? date(o.known_at_server) : "", m5Hold(o.phan_loai), m5Hash(o.native_xml_sha256),
        o.entry_ordinal ? `#${o.entry_ordinal} ${o.entry_name}` : "", o.native_fiscal_status, coReview ? cell : ""];
    })));
    const coMap = d.duoc.M2_MAP, daCau = new Set(d.cau_noi.map(b => b.source_dong_id));
    parts.push(node("h4", "Dòng nguồn của quan sát mới nhất (map dòng logic do CFO quyết; không ghép theo STT/mã hàng)"), d.dong_nguon_hien_hanh.length ? ntTable(
      ["Thứ tự", "Locator", "Mã hàng", "Số lượng nguồn", "Chuẩn hóa", "ĐVT/định nghĩa", "Map dòng"], d.dong_nguon_hien_hanh.map(r => {
        const f = r.fields || {}, lx = k => (f[k] && f[k].length === 1 ? f[k][0].lexeme : null);
        const cell = node("div", undefined, "demo-actions");
        if (coMap) {  // R2: chỉ chọn trong ứng viên literal đã admitted khớp đúng dòng hiện hành (máy chủ lọc); chọn ≠ duyệt — CSDL đối chiếu lại khi CFO gửi
          const uv = (d.ung_vien_dong || []).filter(u => u.source_row_id === r.source_row_id), keys = new Set(uv.map(u => u.logical_line_key));
          if (!uv.length) cell.append(node("span", "HOLD · chưa có ứng viên literal khớp dòng này — không map", "m5-hold"));
          else if (keys.size > 1) cell.append(node("span", "HOLD · ứng viên mơ hồ (nhiều dòng logic) — không tự chọn", "m5-hold"));
          else {
            const [l1, sel] = m5Field("m2-ml-uv-" + r.source_row_id, "Bằng chứng literal", ntSelect("m2-ml-uv-" + r.source_row_id, uv.map(u => `${u.evidence_ref} r${u.evidence_revision}`)));
            const [l2, ly] = m5Field("m2-ml-ly-" + r.source_row_id, "Lý do", node("input"));
            cell.append(node("span", `dòng logic: ${uv[0].logical_line_key}`, "m5-raw"), l1, sel, l2, ly, m5Btn("CFO map dòng", "button secondary", () => {
              const u = sel.selectedIndex >= 1 ? uv[sel.selectedIndex - 1] : null;  // option 0 là "— chọn —": không tự lấy ứng viên đầu
              if (!u) { $("m2-status").textContent = "Chọn bằng chứng literal."; return null; }
              return m2Act("mapping-line", {hoa_don_id: d.id, expected_graph: d.expected_graph, source_row_id: r.source_row_id, logical_line_key: u.logical_line_key,
                evidence_ref: u.evidence_ref, evidence_revision: u.evidence_revision, ly_do: ly.value,
                khoa: m2KhoaLay([actor, d.id, "MAP_LINE", r.source_row_id, u.evidence_ref, u.evidence_revision, d.expected_graph])}, "Đã map dòng");
            }));
          }
        }
        return [String(r.source_ordinal), r.locator, lx("MHHDVu") || "", m5Raw(lx("SLuong")), r.normalized_quantity_text === null ? "NULL (chưa đủ căn cứ)" : r.normalized_quantity_text,
          `${lx("DVTinh") === null ? "NULL" : lx("DVTinh")} / ${r.unit_definition_ref || "NULL"}`, coMap ? cell : ""];
      })) : empty("Không có dòng nguồn hiện hành", ""));
    const coRoute = d.duoc.M2_ROUTE, tuyenHH = new Map(d.tuyen.filter(t => t.hien_hanh).map(t => [t.source_dong_id, t]));
    parts.push(node("h4", "Cầu nối dòng đã duyệt và tuyến dòng (tuyến KHO chỉ là bằng chứng định tuyến)"), d.cau_noi.length ? ntTable(
      ["Thứ tự", "Dòng logic", "Số lượng (exact)", "Độ chính xác", "Tính chất", "Tuyến hiện hành", "Chọn tuyến"], d.cau_noi.map(b => {
        const logic = d.dong_logic.find(x => x.id === b.dong_danh_tinh_id), cur = tuyenHH.get(b.source_dong_id), cell = node("div", undefined, "demo-actions");
        if (coRoute) {
          const [l1, dich] = m5Field("m2-rt-dich-" + b.id, "Đích", ntSelect("m2-rt-dich-" + b.id, ["KHO", "CHI_PHI", "XDCB_241", "TAI_SAN"]));
          const [l2, ly] = m5Field("m2-rt-ly-" + b.id, "Lý do", node("input"));
          cell.append(l1, dich, l2, ly, m5Btn("CFO tạo + duyệt tuyến", "button secondary", () => m2Act("route", {hoa_don_id: d.id, cau_noi_id: b.id, dich: dich.value,
            expected_route_id: cur ? cur.id : null, expected_graph: d.expected_graph, ly_do: ly.value,
            khoa: m2KhoaLay([actor, d.id, "ROUTE", b.id, dich.value, d.expected_graph])}, "Đã ghi tuyến dòng")));
        }
        return [String(b.source_ordinal), logic ? logic.logical_line_key : "", b.quantity_exact === null ? "NULL" : b.quantity_exact, b.precision_state, b.nature,
          cur ? `${cur.dich} · v${cur.phien_ban} · ${cur.trang_thai}` : "chưa có", coRoute ? cell : ""];
      })) : empty("Chưa có cầu nối dòng", daCau.size ? "" : "CFO map dòng nguồn với khóa dòng logic trước; tuyến chỉ mở khi có cầu nối đã duyệt."));
    if (d.tuyen.length) parts.push(node("h4", "Lịch sử tuyến"), ntTable(["Phiên bản", "Đích", "Trạng thái", "Hiện hành", "Lý do"], d.tuyen.map(t => ["v" + t.phien_ban, t.dich, t.trang_thai, t.hien_hanh ? "Có" : "", t.reason])));
    box.replaceChildren(...parts);
  }
  async function m2Load(conHieuLuc = () => true) {
    if (vaiDangChan("m2")) return;  // repair06: đổi vai đang chờ — không GET vai cũ; nạp lại khi ý định mới nhất giải quyết
    const ep = m2Epoch, q = new URLSearchParams();
    if (!conHieuLuc()) return;
    const gen = ++m2DocGen, moiNhat = () => gen === m2DocGen && ep === m2Epoch && conHieuLuc();
    for (const [k, id] of [["phap_nhan", "m2-loc-pn"], ["ky", "m2-loc-ky"]]) if ($(id).value.trim()) q.set(k, $(id).value.trim());
    try {
      const s = await (await request("/api/m2" + (q.toString() ? "?" + q : ""))).json();
      if (!moiNhat()) return;
      m2 = s; m2Render(conHieuLuc);
    } catch (error) { if (moiNhat()) $("m2-status").textContent = error.message; }
  }
  $("m2-refresh").addEventListener("click", () => m2Load());
  $("m2-loc").addEventListener("click", () => { m2XoaTrangThai(); m2Load(); });
  $("m2-doi-vai").addEventListener("click", () => {
    const login = $("m2-danh-tinh").value;  // repair05: xóa đồng bộ ngữ cảnh vai của CẢ M2/M5/L11 trước POST (helper chung ở khối L11)
    return doiVaiTuanTu(() => m2Post("danh-tinh", {dang_nhap: login}), "m2-status", "m2");
  });
  $("m2-tl-khoa-moi").addEventListener("click", () => { m2FormEpoch += 1; $("m2-tl-khoa").value = m2Khoa(); });
  $("m2-tl-nguon").addEventListener("change", () => { m2XoaForm(); m2Coverage(null); $("m2-tl-khoa").value = m2Khoa(); });
  for (const id of ["m2-tl-coverage", "m2-tl-native", "m2-tl-crosswalk", "m2-tl-loi", "m2-tl-khoa", "m2-tl-mau"]) {
    $(id).addEventListener("change", () => { m2FormEpoch += 1; });
    $(id).addEventListener("input", () => { m2FormEpoch += 1; });
  }
  $("m2-tl-gui-mau").addEventListener("click", async () => {
    const ep = m2Epoch, fe = m2FormEpoch, [inst, scope] = JSON.parse($("m2-tl-nguon").value || "[]");
    const body = {mau: $("m2-tl-mau").value, source_instance: inst, scope_ref: scope, coverage: $("m2-tl-coverage").value, khoa: $("m2-tl-khoa").value.trim()};
    const formCon = () => fe === m2FormEpoch;
    const r = await m2Act("nhan", body, "Đã nhận mẫu hóa đơn", formCon);
    if (r && ep === m2Epoch && formCon()) $("m2-status").textContent = m2TomTat(r);
  });
  $("m2-tai-len").addEventListener("submit", async event => {
    event.preventDefault();
    const ep = m2Epoch, fe = m2FormEpoch;
    try {
      const [inst, scope] = JSON.parse($("m2-tl-nguon").value || "[]");
      const claim = {source_instance: inst, scope_ref: scope, coverage: $("m2-tl-coverage").value,
        reported_errors: $("m2-tl-loi").value.split(/\r?\n/).map(x => x.trim()).filter(Boolean), khoa: $("m2-tl-khoa").value.trim()};
      const fNative = ($("m2-tl-native").files || [])[0] || null, fCw = ($("m2-tl-crosswalk").files || [])[0] || null;
      if (!fNative) { $("m2-status").textContent = "Chọn tệp hóa đơn XML hoặc ZIP."; return; }
      const gioiHan = m2 && m2.gioi_han_tai_len_byte, tong = fNative.size + (fCw ? fCw.size : 0);
      if (gioiHan && tong > gioiHan) { $("m2-status").textContent = `Tổng tệp ${tong} byte vượt giới hạn ${gioiHan} byte mỗi lần nhận — không gửi.`; return; }
      const [native, crosswalk] = await Promise.all([m5DocTep(fNative), m5DocTep(fCw)]);
      if (ep !== m2Epoch) return;
      if (fe !== m2FormEpoch) { $("m2-status").textContent = "Form nhận tệp đã đổi trong lúc đọc tệp — kiểm tra rồi gửi lại."; return; }
      const body = {...claim, native_b64: native, artifact_name: fNative.name};
      if (crosswalk !== null) body.crosswalk_b64 = crosswalk;
      const formCon = () => fe === m2FormEpoch;
      const r = await m2Act("nhan", body, "Đã nhận tệp hóa đơn", formCon);
      if (r && ep === m2Epoch && formCon()) $("m2-status").textContent = m2TomTat(r);
    } catch (error) {
      if (ep !== m2Epoch) return;
      if (fe !== m2FormEpoch) { $("m2-status").textContent = M2_FORM_DA_DOI_LOI; return; }
      toast(error.message, true); $("m2-status").textContent = error.message;
    }
  });
  window.addEventListener("hashchange", () => { if (location.hash === "#hoadonmua") m2Load(); });
  if (location.hash === "#hoadonmua") m2Load();
  // ---------------------------------------------------------------- L11 liên kết số lượng DEMO (R16) — cùng shell/token/cookie; fence epoch vai/lựa chọn,
  // epoch form, thế hệ GET (A trễ không đè B), tải file chỉ khi vẫn đúng vai/epoch. Picker theo DTO máy chủ — không nhập UUID/hệ số.
  pages.lienketsoluong = "Liên kết số lượng";
  let l11 = null, l11Epoch = 0, l11FormEpoch = 0, l11Gen = 0, l11XemTruoc = null;
  const l11KhoaThaoTac = new Map();
  const l11Khoa = () => "l11-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
  function l11KhoaLay(ctx) { const k = JSON.stringify(ctx); if (!l11KhoaThaoTac.has(k)) l11KhoaThaoTac.set(k, l11Khoa()); return l11KhoaThaoTac.get(k); }
  const l11Actor = () => (l11 && l11.nguoi && l11.nguoi.dang_nhap) || null;
  function l11XoaTrangThai() {
    l11Epoch += 1; l11FormEpoch += 1; l11 = null; l11XemTruoc = null;
    for (const id of ["l11-ung-vien", "l11-bang-chung", "l11-dong-hoa-don", "l11-dong-phieu", "l11-cap", "l11-xem-truoc", "l11-lien-ket"]) $(id).replaceChildren();
    $("l11-tai-len").classList.add("hidden"); $("l11-nguoi").textContent = "Đang tải…"; $("l11-status").textContent = "";
  }
  // repair05: M2/M5/L11 dùng CHUNG một phiên cookie trên máy chủ → đổi vai ở BẤT KỲ selector nào cũng làm mất hiệu lực ngữ cảnh vai của CẢ BA module,
  // ĐỒNG BỘ, trước POST và trước await đầu tiên: tăng epoch/form epoch, xóa cache/lựa chọn/raw/chi tiết/bằng chứng/xem trước/liên kết/nút FILE và mọi
  // continuation đang chờ (POST→GET riêng→headers→Blob→click đều kiểm epoch/vai gốc nên tự hủy). Không xóa lịch sử/biên nhận/file, không reset nghiệp vụ.
  // Cổng thao tác đổi vai: `vaiGen` (lần đổi vai mới nhất thắng) + chuỗi `vaiCho` (POST đổi vai tuần tự, không chạy chéo) — phản hồi/lỗi của lần cũ
  // không toast/status/load, không hồi sinh cache. UI chỉ hiển thị vai do máy chủ trả ở lần GET sau; không tự cấp actor/PN/quyền.
  // (biến vaiGen/vaiCho/vaiChan/vaiChoTai khai báo trước khối M5 — repair06)
  function doiVaiChung() {
    vaiGen += 1;
    vaiChan = vaiGen;  // repair06: barrier thuộc ý định MỚI NHẤT, đặt đồng bộ cùng lúc xóa — GET mới sau click không thể lấy vai cũ của máy chủ
    for (const p of vaiThanhVien.values()) p.xoa();  // M4-01C: mọi người tham gia đã đăng ký (CRM/M5/M2/L11/M4), đồng bộ
    return vaiGen;
  }
  // repair06: loader gọi khi barrier đang chặn → ghi module cần nạp, trả `true` (người gọi KHÔNG gửi GET, không await gì)
  function vaiDangChan(ten) {
    if (!vaiChan) return false;
    vaiChoTai.add(ten);
    return true;
  }
  // repair06: CHỈ ý định mới nhất mở barrier (sau POST thành công hoặc lỗi), rồi nạp lại module khởi tạo + mọi module đã xin nạp trong lúc chặn.
  // Mở barrier TRƯỚC khi gọi loader ⇒ loader không tự chờ chính lần đổi vai này (không deadlock).
  function moChanVaNap(ve, khoiTao) {
    if (ve !== vaiGen || vaiChan !== ve) return [];
    vaiChan = 0;
    const can = new Set([...vaiChoTai, khoiTao]);
    vaiChoTai.clear();
    return [...can].filter(t => vaiThanhVien.has(t)).map(t => vaiThanhVien.get(t).nap());
  }
  async function doiVaiTuanTu(gui, statusId, khoiTao) {
    const ve = doiVaiChung();  // đồng bộ — trước mọi await (xóa mọi người tham gia + dựng barrier)
    const truoc = vaiCho;
    let xong, ok = false, loi = null;
    vaiCho = new Promise(r => { xong = r; });
    // M4-01C2: hàng chờ CHỈ tuần tự hóa POST đổi vai — nhả ngay khi POST của ý định này kết thúc (thành công/lỗi), KHÔNG chờ các GET nạp lại.
    // GET nạp lại treo không chặn ý định đổi vai mới; mọi GET/lỗi/hoàn tất của từng module vẫn rào theo epoch/thế hệ riêng của module đó.
    try {
      await truoc;  // POST đổi vai trước đó (ở bất kỳ module) đã kết thúc
      if (ve !== vaiGen) return;  // đã có lần đổi vai mới hơn: bỏ POST cũ, không gửi; barrier vẫn thuộc ý định mới hơn
      try { await gui(); ok = true; } catch (error) { loi = error; }
    } finally { xong(); }
    if (ve !== vaiGen) return;  // phản hồi/lỗi của ý định cũ: không mở barrier, không toast/status/load
    if (ok) toast("Đã đổi vai mô phỏng");
    else {
      // lỗi/mất kết nối: KHÔNG khẳng định máy chủ đã hay chưa đổi vai — mở barrier của ý định mới nhất và đọc lại vai THẬT từ máy chủ;
      // cache cũ đã xóa, không hồi sinh; giao diện dùng tiếp được
      toast(loi.message, true); $(statusId).textContent = loi.message;
    }
    await Promise.all(moChanVaNap(ve, khoiTao));
  }
  async function l11Post(path, body) { return (await request("/api/m5/" + path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})).json(); }
  // R4 repair02: fence GỐC của thao tác (epoch + vai + form/cặp) giữ qua MỌI await — POST, GET làm mới, và tải tự động; không lấy epoch hiện tại
  // để "kích lại" kết quả cũ. GET mới hơn thắng (thế hệ) cũng làm kết quả cũ mất hiệu lực.
  // repair03 (B): ngữ cảnh GỐC bất biến = epoch + vai + điều kiện form/cặp do người gọi chụp (conHieuLuc) + VÉ thế hệ của GET làm mới do CHÍNH
  // thao tác mở. Kiểm sau MỌI await trước toast/status/DOM/tải; GET cạnh tranh mới hơn (l11Gen tăng) hủy continuation cũ suốt đời của nó.
  async function l11Act(path, body, ok, conHieuLuc = () => true) {
    const ep = l11Epoch, actor = l11Actor();
    const ctx = () => ep === l11Epoch && actor === l11Actor() && conHieuLuc();
    $("l11-status").textContent = "";
    try {
      const r = await l11Post(path, body);
      if (ep !== l11Epoch || actor !== l11Actor()) return null;  // vai/lựa chọn đã đổi: không gắn kết quả cũ vào vai mới
      if (!conHieuLuc()) { $("l11-status").textContent = "Phản hồi đến sau khi form/lựa chọn đã đổi — bấm Làm mới để xem trạng thái thật."; return null; }
      toast(ok);
      const ve = await l11Load(ctx);  // vé bất biến của GET do chính thao tác này mở; ctx kiểm TRƯỚC khi phản hồi được vẽ (repair04)
      const fence = () => ctx() && ve === l11Gen;
      if (!fence()) return null;  // vai/cặp/form đổi hoặc GET mới hơn thắng trong khoảng POST→GET: bỏ kết quả cũ
      return {r, fence};
    } catch (error) {
      if (!ctx()) return null;  // không đẩy lỗi cũ sang vai/lựa chọn mới
      toast(error.message, true); $("l11-status").textContent = error.message; return null;
    }
  }
  async function l11Tai(loId, fence) {  // tải file CHỈ dưới fence gốc của thao tác xuất (không tự tạo fence từ epoch/form/thế hệ hiện tại)
    const con = () => typeof fence === "function" && fence() && l11Actor() !== null;
    if (!con()) return;
    try {
      const res = await request(`/api/m5/file-soat/${encodeURIComponent(loId)}`);
      if (!con()) return;  // sau headers
      const blob = await res.blob();
      if (!con()) return;  // sau body — ngay trước click thật
      const url = URL.createObjectURL(blob), a = node("a"); a.href = url; a.download = `FILE-SOAT-L11-${String(loId).slice(0, 8)}.xlsx`; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { if (con()) { toast(error.message, true); $("l11-status").textContent = error.message; } }
  }
  const l11MaHoaMoiNhat = (side, lineId) => (l11.ma_hoa || []).filter(e => e.owner_module === side && (side === "M2" ? e.cau_noi_id : e.phieu_dong_phien_ban_id) === lineId)
    .sort((a, b) => b.basis_revision - a.basis_revision)[0] || null;
  function l11NganSach(n) {
    if (!n) return "chưa có pool";
    return n.con_lai === null ? `BỊ CHẶN (${(n.ly_do_chan || []).join(", ")}) · đã dùng ${n.da_dung} ${n.don_vi_ma || ""}`
      : `sức chứa ${n.suc_chua} · đã xác nhận ${n.da_xac_nhan} · đang giữ ${n.dang_giu} · còn lại ${n.con_lai} ${n.don_vi_ma || ""}`;
  }
  function l11Facts(kind, f) {  // facts trích từ raw đã capture (chỉ hiển thị, không gửi lại) — miền/binding/đơn vị/tỷ lệ theo loại
    if (!f || typeof f !== "object") return "— (JSON không đọc được: giữ HOLD)";
    const s = v => (v === null || v === undefined ? "—" : typeof v === "object" ? JSON.stringify(v) : String(v));
    const dong = [];
    const bindings = f.supporting_native_bindings || f.supported_warehouse_bindings || [];
    if (kind === "GOODS_EQUIVALENCE") {
      const d = f.domain || {}, i = d.invoice || {}, w = d.warehouse || {};
      dong.push(`Hóa đơn: ${s(i.source_instance)} · ${s(i.profile_ref)} · ${s(i.company_key)}/${s(i.company_mapping_ref)} · mã ${s(i.item_code)}`);
      dong.push(`Kho: ${s(w.source_instance)} · ${s(w.profile_ref)} · ${s(w.MaKho)}/${s(w.warehouse_mapping_ref)} · mã ${s(w.item_code)}`);
    } else if (kind === "CROSS_NATIVE_RATIO") {
      dong.push(`native ${s(f.from_definition_ref)} × ${s(f.numerator_text)} = native ${s(f.to_definition_ref)} × ${s(f.denominator_text)} (chuỗi nguyên văn)`);
      dong.push(`Bằng chứng hàng: ${s(f.goods_equivalence_ref)}`);
    } else if (kind === "NATIVE_ENCODING") {
      const r = f.native_to_pool_ratio || {};
      dong.push(`Artifact ${s(f.native_xml_sha256)} · ${s(f.native_byte_length)} byte · ${s(f.quantity_field_locator)}=${s(f.quantity_decoded_lexeme)} · ${s(f.unit_field_locator)}=${s(f.unit_decoded_lexeme)}`);
      dong.push(`Đơn vị native ${s((f.unit_definition || {}).reference_id)} → pool ${s(f.pool_unit_definition_ref)} × ${s(r.numerator_text)}/${s(r.denominator_text)}`);
    }
    for (const b of bindings) dong.push(`${s(b.side)} ${s(b.native_sha256)} · ${s(b.SoPhieu || b.locator)} ${s(b.ID_Dong || "")} #${s(b.source_ordinal)} · mã ${s(b.item_code)}`
      + (b.measurement_payload_sha256 ? ` · đo lường ${b.measurement_payload_sha256}` : ""));
    const box = node("details"); box.append(node("summary", `${dong.length} dòng facts`));
    for (const t of dong) box.append(node("div", t));
    return box;
  }
  function l11Render() {
    if (!l11.cau_hinh) { $("l11-nguoi").textContent = l11.ly_do; return; }
    const n = l11.nguoi || {}, duoc = n.duoc || {};
    $("l11-danh-tinh").replaceChildren(...(l11.danh_tinh_demo || []).map(d => { const o = node("option", `${d.dang_nhap} (${d.vai_tro})`); o.value = d.dang_nhap; o.selected = d.dang_nhap === n.dang_nhap; return o; }));
    $("l11-nguoi").textContent = l11.khong_quyen ? `${n.dang_nhap || ""} · ${l11.khong_quyen}` : `${n.dang_nhap} · ${n.vai_tro} · được: ${Object.keys(duoc).filter(k => duoc[k]).join(", ") || "chỉ xem"}`;
    // 1 · nhận bằng chứng (form chỉ hiện khi có phạm vi bằng chứng + máy chủ nhận)
    const pv = l11.pham_vi_bang_chung || [];
    $("l11-tai-len").classList.toggle("hidden", !(pv.length && l11.may_chu_nhan));
    const chon = $("l11-tl-nguon").value;
    $("l11-tl-nguon").replaceChildren(...pv.map(s => { const o = node("option", `${s.source_instance_id} · ${s.scope_ref}`); o.value = JSON.stringify([s.source_instance_id, s.scope_ref]); return o; }));
    if (chon) $("l11-tl-nguon").value = chon;
    const s0 = pv.find(s => JSON.stringify([s.source_instance_id, s.scope_ref]) === $("l11-tl-nguon").value) || pv[0];
    const covCu = $("l11-tl-coverage").value;
    $("l11-tl-coverage").replaceChildren(...((s0 && s0.coverage_values) || []).map(c => { const o = node("option", c); o.value = c; return o; }));
    if (covCu) $("l11-tl-coverage").value = covCu;
    const mauCu = $("l11-tl-mau").value;
    $("l11-tl-mau").replaceChildren(...(l11.mau_bang_chung || []).map(m => { const o = node("option", m); o.value = m; return o; }));
    if (mauCu) $("l11-tl-mau").value = mauCu;
    if (!$("l11-tl-khoa").value) $("l11-tl-khoa").value = l11Khoa();
    const actor = n.dang_nhap || "";
    // R4 repair02: CFO thấy H/độ dài raw, claim coverage/lỗi báo và FACTS trích từ raw (miền/binding/đơn vị native/pool/tỷ lệ) TRƯỚC nút xác nhận.
    // Chỉ dùng DTO ứng viên đã lọc theo READ_SOURCE ở CSDL (LINK không nhận raw candidate); không ô nhập UUID/hệ số.
    $("l11-ung-vien").replaceChildren((l11.ung_vien || []).length ? ntTable(["Tham chiếu", "Rev", "Loại (cấu hình)", "Raw (SHA-256 · byte)", "Coverage / lỗi báo",
      "Facts trước khi duyệt", "Trạng thái", "Lý do giữ", "Xác nhận"], l11.ung_vien.map(u => {
      const cell = node("div", undefined, "demo-actions");
      if (duoc.CFO && u.trang_thai === "UNG_VIEN" && !u.bang_chung_id) {
        const [l, ly] = m5Field("l11-uv-ly-" + u.id, "Lý do", node("input"));
        cell.append(l, ly, m5Btn("CFO xác nhận bằng chứng", "button secondary", () => l11Act("l11/proof/xac-nhan", {candidate_id: u.id, expected_graph: u.expected_graph,
          ly_do: ly.value, khoa: l11KhoaLay([actor, "PROOF_CONFIRM", u.id, u.expected_graph])}, "Đã xác nhận bằng chứng")));
      }
      return [u.reference_id || "—", u.evidence_revision ?? "—", u.kind || "—", `${u.raw_sha256 || "—"} · ${u.byte_length ?? "—"}`,
        `${u.coverage || "—"} (hiệu lực ${u.coverage_hieu_luc || "—"})${(u.reported_errors || []).length ? " · lỗi: " + u.reported_errors.join(", ") : ""}`,
        l11Facts(u.kind, u.facts), u.bang_chung_id ? "ĐÃ CÓ BẰNG CHỨNG" : u.trang_thai, m5Hold(u.issues), cell];
    })) : empty("Chưa thấy bằng chứng thô", "Cần năng lực đọc nguồn bằng chứng; hoặc chưa nhận tệp nào."));
    // 2 · bằng chứng đã xác nhận
    $("l11-bang-chung").replaceChildren((l11.bang_chung || []).length ? ntTable(["Loại", "Tham chiếu", "Nội dung", "Trạng thái", "Thu hồi"], l11.bang_chung.map(q => {
      const nd = q.kind === "GOODS_EQUIVALENCE" ? `${q.hang_hoa_hoa_don} ↔ ${q.hang_hoa_kho}` : q.kind === "CROSS_NATIVE_RATIO"
        ? `native ${q.tu_don_vi} × ${q.tu_so} = native ${q.den_don_vi} × ${q.mau_so}`
        : `${q.unit_lexeme}: native ${q.tu_don_vi} → pool ${q.den_don_vi} (×${q.tu_so}/${q.mau_so})`;
      const cell = node("div", undefined, "demo-actions");
      if (duoc.CFO && q.trang_thai === "DA_XAC_NHAN") {
        const [l, ly] = m5Field("l11-bc-ly-" + q.id, "Lý do", node("input"));
        cell.append(l, ly, m5Btn("CFO thu hồi", "button secondary", () => l11Act("l11/proof/huy", {proof_id: q.id, expected_graph: q.expected_graph, ly_do: ly.value,
          khoa: l11KhoaLay([actor, "PROOF_REVOKE", q.id, q.expected_graph])}, "Đã thu hồi bằng chứng")));
      }
      return [q.kind, `${q.reference_id} r${q.evidence_revision}`, nd, q.trang_thai, cell];
    })) : empty("Chưa có bằng chứng đã xác nhận", "CFO xác nhận từ bằng chứng thô ở mục 1."));
    // 3 · mã hóa nguồn
    const maHoaBC = (l11.bang_chung || []).filter(q => q.kind === "NATIVE_ENCODING" && q.trang_thai === "DA_XAC_NHAN");
    const oMaHoa = (side, lineId, token, pool) => {
      const cell = node("div", undefined, "demo-actions");
      if (duoc.CFO && token) {
        let sel = null;
        if (side === "M2" && maHoaBC.length) { const [l0, s] = m5Field(`l11-mh-bc-${lineId}`, "Bằng chứng mã hóa (nếu cần)", ntSelect(`l11-mh-bc-${lineId}`, maHoaBC.map(q => q.reference_id))); sel = s; cell.append(l0, s); }
        const [l, ly] = m5Field(`l11-mh-ly-${lineId}`, "Lý do", node("input"));
        cell.append(l, ly, m5Btn("Mã hóa nguồn", "button secondary", () => {
          const bc = sel && sel.selectedIndex >= 1 ? maHoaBC[sel.selectedIndex - 1] : null;
          return l11Act("l11/ma-hoa", {side, line_id: lineId, proof_id: bc ? bc.id : null, expected_graph: token, ly_do: ly.value,
            khoa: l11KhoaLay([actor, "ENCODE", side, lineId, bc ? bc.id : null, token])}, "Đã mã hóa nguồn");
        }));
      }
      return [pool ? l11NganSach(pool) : "chưa mã hóa", cell];
    };
    $("l11-dong-hoa-don").replaceChildren((l11.dong_hoa_don || []).length ? ntTable(["Pháp nhân", "Hóa đơn", "STT", "Mã hàng", "SL gốc", "ĐVT gốc", "Tuyến", "Hiện hành", "Pool", "Mã hóa"],
      l11.dong_hoa_don.map(d => { const e = l11MaHoaMoiNhat("M2", d.cau_noi_id); return [d.phap_nhan, `${d.ky_hieu} · ${d.so_chuan}`, String(d.source_ordinal), d.ma_hang || "",
        d.quantity_raw ?? "NULL", d.unit_raw ?? "NULL", d.dich || "chưa có", d.hien_hanh ? "Có" : "Không", ...oMaHoa("M2", d.cau_noi_id, d.ma_hoa && d.ma_hoa.expected_graph, e && e.ngan_sach)]; }))
      : empty("Chưa có dòng hóa đơn đã map", "Map dòng + tuyến KHO ở trang Hóa đơn mua XML trước."));
    $("l11-dong-phieu").replaceChildren((l11.dong_phieu || []).length ? ntTable(["Pháp nhân", "Phiếu", "STT", "ID dòng", "Mã hàng", "SL gốc", "ĐVT", "Hiện hành", "Pool", "Mã hóa"],
      l11.dong_phieu.map(d => { const e = l11MaHoaMoiNhat("M5", d.dong_phien_ban_id); return [d.phap_nhan, d.so_phieu, String(d.stt), d.id_dong_nguon, d.ma_hang || "",
        d.so_luong_raw ?? "NULL", d.dvt_raw ?? "NULL", d.hien_hanh ? "Có" : "Không", ...oMaHoa("M5", d.dong_phien_ban_id, d.ma_hoa && d.ma_hoa.expected_graph, e && e.ngan_sach)]; }))
      : empty("Chưa có dòng phiếu", "Nhận + chấp nhận nguồn phiếu ở trang Phiếu kho trước."));
    l11RenderCap();
    // 5 · liên kết đã ghi
    $("l11-lien-ket").replaceChildren(...((l11.lien_ket || []).length ? l11.lien_ket.map(k => {
      const box = node("div", undefined, "card"), cs = k.co_so || {}, tok = cs.token_dong || {};
      box.append(node("h4", `Liên kết ${String(k.id).slice(0, 8)} · ${k.phap_nhan} · ${k.trang_thai}`));
      box.append(ntTable(["Trạng thái", "Hiệu lực", "Lý do soát", "SL hóa đơn (gốc → pool)", "SL phiếu (gốc → pool)", "Hủy"], (cs.dong || []).map(c => {
        const cell = node("div", undefined, "demo-actions"), sl = c.so_luong || {}, dv = c.don_vi || {};
        if (duoc.LINK && c.trang_thai === "DA_KHOP" && tok[c.child_id]) {
          const [l, ly] = m5Field("l11-huy-ly-" + c.child_id, "Lý do", node("input"));
          cell.append(l, ly, m5Btn("Hủy liên kết (giải phóng đúng lượng đã ghi)", "button secondary", () => l11Act("lien-ket/huy", {child_id: c.child_id,
            expected_graph: tok[c.child_id], ly_do: ly.value, khoa: l11KhoaLay([actor, "UNDO", c.child_id, tok[c.child_id]])}, "Đã hủy liên kết")));
        }
        return [c.trang_thai, c.hieu_luc, (c.can_soat_ly_do || []).join(", "), `${sl.hoa_don_nguon} ${dv.hoa_don_nguon || ""} → ${sl.pool_hoa_don} ${dv.pool_hoa_don || ""}`,
          `${sl.phieu_nguon} ${dv.phieu_nguon || ""} → ${sl.pool_phieu} ${dv.pool_phieu || ""}`, cell];
      })));
      if (duoc.FILE && cs.duoc_file) {
        const [l, ly] = m5Field("l11-file-ly-" + k.id, "Lý do", node("input")), line = node("div", undefined, "demo-actions");
        line.append(l, ly, m5Btn("Xuất file soát số lượng", "button secondary", async () => {
          // repair03 (B): chụp form epoch + cặp/liên kết + token đồ thị lúc bấm; truyền predicate THẬT vào l11Act (giữ qua POST/refresh) và tải
          const fe = l11FormEpoch, coSo = cs.co_so_sha256;
          const conCap = () => fe === l11FormEpoch && (l11 && l11.lien_ket || []).some(x => x.id === k.id && x.co_so && x.co_so.co_so_sha256 === coSo);
          const kq = await l11Act("l11/file-soat", {lien_ket_id: k.id, co_so_truoc: coSo, ly_do: ly.value,
            khoa: l11KhoaLay([actor, "FILE", k.id, coSo])}, "Đã xuất file soát số lượng", conCap);
          if (kq && kq.r && kq.r.id && kq.fence()) await l11Tai(kq.r.id, kq.fence);
        }));
        box.append(line);
      }
      return box;
    }) : [empty("Chưa có liên kết số lượng", "Xem trước rồi xác nhận ở mục 4.")]));
  }
  function l11RenderCap() {
    const duoc = (l11.nguoi && l11.nguoi.duoc) || {};
    const hd = (l11.dong_hoa_don || []).filter(d => d.hien_hanh && l11MaHoaMoiNhat("M2", d.cau_noi_id));
    const pk = (l11.dong_phieu || []).filter(d => d.hien_hanh && l11MaHoaMoiNhat("M5", d.dong_phien_ban_id));
    const hang = (l11.bang_chung || []).filter(q => q.kind === "GOODS_EQUIVALENCE" && q.trang_thai === "DA_XAC_NHAN");
    const tyLe = (l11.bang_chung || []).filter(q => q.kind === "CROSS_NATIVE_RATIO" && q.trang_thai === "DA_XAC_NHAN");
    if (!hd.length || !pk.length || !hang.length || !tyLe.length) {
      $("l11-cap").replaceChildren(empty("Chưa đủ để chọn cặp", "Cần dòng hóa đơn + dòng phiếu đã mã hóa và bằng chứng hàng hóa + tỷ lệ đã xác nhận.")); $("l11-xem-truoc").replaceChildren(); return;
    }
    const doiForm = () => { l11FormEpoch += 1; l11XemTruoc = null; $("l11-xem-truoc").replaceChildren(); };
    const [l1, sHd] = m5Field("l11-cap-hd", "Dòng hóa đơn", ntSelect("l11-cap-hd", hd.map(d => `${d.ky_hieu}·${d.so_chuan} #${d.source_ordinal} ${d.ma_hang} ${d.quantity_raw} ${d.unit_raw}`)));
    const [l2, sPk] = m5Field("l11-cap-pk", "Dòng phiếu", ntSelect("l11-cap-pk", pk.map(d => `${d.so_phieu} #${d.stt} ${d.ma_hang} ${d.so_luong_raw} ${d.dvt_raw}`)));
    const [l3, sHang] = m5Field("l11-cap-hang", "Bằng chứng hàng", ntSelect("l11-cap-hang", hang.map(q => q.reference_id)));
    const [l4, sTl] = m5Field("l11-cap-tl", "Tỷ lệ", ntSelect("l11-cap-tl", tyLe.map(q => `${q.reference_id} (${q.tu_so}:${q.mau_so})`)));
    const [l5, a] = m5Field("l11-cap-a", "SL hóa đơn (gốc)", ntInput("l11-cap-a", ""));
    const [l6, b] = m5Field("l11-cap-b", "SL phiếu (gốc)", ntInput("l11-cap-b", ""));
    for (const el of [sHd, sPk, sHang, sTl, a, b]) { el.addEventListener("change", doiForm); el.addEventListener("input", doiForm); }
    const than = () => {
      const h = sHd.selectedIndex >= 1 ? hd[sHd.selectedIndex - 1] : null, p = sPk.selectedIndex >= 1 ? pk[sPk.selectedIndex - 1] : null;
      const g = sHang.selectedIndex >= 1 ? hang[sHang.selectedIndex - 1] : null, t = sTl.selectedIndex >= 1 ? tyLe[sTl.selectedIndex - 1] : null;
      if (!h || !p || !g || !t) return null;
      const body = {cau_noi_id: h.cau_noi_id, dong_phien_ban_id: p.dong_phien_ban_id, ma_hoa_hoa_don_id: l11MaHoaMoiNhat("M2", h.cau_noi_id).id,
                    ma_hoa_phieu_id: l11MaHoaMoiNhat("M5", p.dong_phien_ban_id).id, bang_chung_hang_id: g.id, bang_chung_ty_le_id: t.id};
      if (a.value.trim() || b.value.trim()) { body.so_luong_hoa_don = a.value.trim(); body.so_luong_phieu = b.value.trim(); }  // chuỗi nguyên văn, không Number
      return body;
    };
    const line = node("div", undefined, "demo-actions");
    line.append(l1, sHd, l2, sPk, l3, sHang, l4, sTl, l5, a, l6, b, m5Btn("Xem trước bốn lượng", "button secondary", async () => {
      const body = than(); if (!body) { $("l11-status").textContent = "Chọn đủ cặp dòng, bằng chứng và nhập hai số lượng gốc."; return; }
      const ep = l11Epoch, fe = l11FormEpoch, actor = l11Actor(), gen = ++l11Gen;
      try {
        const v = await l11Post("lien-ket/preview", body);
        if (ep !== l11Epoch || fe !== l11FormEpoch || gen !== l11Gen || actor !== l11Actor()) return;  // preview cũ không gắn vào lựa chọn mới
        l11XemTruoc = {body, v, fe}; l11RenderXemTruoc(duoc);
      } catch (error) { if (ep === l11Epoch && fe === l11FormEpoch && actor === l11Actor()) { toast(error.message, true); $("l11-status").textContent = error.message; } }
    }));
    $("l11-cap").replaceChildren(line); $("l11-xem-truoc").replaceChildren();
  }
  function l11RenderXemTruoc(duoc) {
    const x = l11XemTruoc; if (!x) return;
    const v = x.v, sl = v.so_luong || {}, dv = v.don_vi || {}, ns = v.ngan_sach || {};
    const box = node("div");
    box.append(ntTable(["Phía", "Lượng gốc", "Đơn vị gốc", "Lượng pool", "Đơn vị pool", "Ngân sách pool"], [
      ["Hóa đơn", sl.hoa_don_nguon ?? "—", dv.hoa_don_nguon ?? "—", sl.pool_hoa_don ?? "—", dv.pool_hoa_don ?? "—", l11NganSach(ns.hoa_don)],
      ["Phiếu kho", sl.phieu_nguon ?? "—", dv.phieu_nguon ?? "—", sl.pool_phieu ?? "—", dv.pool_phieu ?? "—", l11NganSach(ns.phieu)]]));
    const tl = v.ty_le || {}, mh = v.ma_hoa_ty_le || {};
    box.append(node("p", `Tỷ lệ cross-native áp trên đơn vị NATIVE (${dv.dinh_nghia_nguon_hoa_don ?? "—"} × ${tl.tu_so ?? "—"} = ${dv.dinh_nghia_nguon_phieu ?? "—"} × ${tl.mau_so ?? "—"}); `
      + `lượng pool mỗi phía dẫn xuất riêng qua mã hóa own-pool (hóa đơn ×${(mh.hoa_don || {}).tu_so ?? "—"}/${(mh.hoa_don || {}).mau_so ?? "—"}, `
      + `phiếu ×${(mh.phieu || {}).tu_so ?? "—"}/${(mh.phieu || {}).mau_so ?? "—"}).`));
    box.append(m5Hold(v.blockers));
    if (duoc.LINK && v.duoc_xac_nhan && !(v.blockers || []).length && x.body.so_luong_hoa_don && x.body.so_luong_phieu) {
      const [l, ly] = m5Field("l11-xn-ly", "Lý do", node("input")), line = node("div", undefined, "demo-actions");
      line.append(l, ly, m5Btn("Xác nhận liên kết số lượng", "button primary", () => {
        const fe = x.fe;
        return l11Act("lien-ket/xac-nhan", {...x.body, expected_graph: v.expected_graph, ly_do: ly.value,
          khoa: l11KhoaLay([l11Actor(), "CONFIRM", x.body, v.expected_graph])}, "Đã xác nhận liên kết", () => fe === l11FormEpoch);
      }));
      box.append(line);
    }
    $("l11-xem-truoc").replaceChildren(box);
  }
  // repair04 (UI03-1): `conGoc` = ngữ cảnh GỐC của thao tác sở hữu lần làm mới này (epoch + vai + form/cặp/basis chụp lúc bấm). Kiểm TRƯỚC mọi hiệu ứng
  // DOM/state/status của phản hồi: thao tác đã mất hiệu lực (người dùng đổi cặp/lượng/form trong lúc GET chờ) → KHÔNG gán `l11`, KHÔNG render/reset
  // picker/xem trước, KHÔNG status — giữ nguyên lựa chọn hiện tại; làm mới thường (không conGoc) và GET mới hơn thắng giữ như cũ.
  async function l11Load(conGoc = null) {
    // repair06: đổi vai đang chờ — không GET vai cũ. Vẫn cấp vé thế hệ mới (vô hiệu GET/continuation cũ hơn); thao tác sở hữu nhận vé này nhưng
    // fence gốc của nó đã sai do epoch/vai đổi ⇒ không render/tải. Module được nạp lại khi ý định mới nhất giải quyết.
    if (vaiDangChan("l11")) return ++l11Gen;
    const ep = l11Epoch, gen = ++l11Gen, actor = l11Actor();
    const conHop = () => ep === l11Epoch && gen === l11Gen && (conGoc === null || conGoc());
    try {
      const s = await (await request("/api/m5/l11")).json();
      if (!conHop()) return gen;  // GET cũ hơn (A trễ không đè B) hoặc thao tác sở hữu đã mất hiệu lực: 0 hiệu ứng
      if (actor !== null && s.nguoi && s.nguoi.dang_nhap !== actor) { l11Epoch += 1; }
      l11 = s; l11XemTruoc = null; l11Render();
    } catch (error) { if (conHop()) $("l11-status").textContent = error.message; }
    return gen;  // người gọi so với l11Gen hiện tại: GET mới hơn đã thắng → kết quả thao tác cũ hết hiệu lực
  }
  $("l11-refresh").addEventListener("click", () => l11Load());
  $("l11-doi-vai").addEventListener("click", () => {
    const login = $("l11-danh-tinh").value;  // chụp login đồng bộ trước khi xóa trạng thái
    return doiVaiTuanTu(() => l11Post("l11/danh-tinh", {dang_nhap: login}), "l11-status", "l11");
  });
  $("l11-tl-khoa-moi").addEventListener("click", () => { l11FormEpoch += 1; $("l11-tl-khoa").value = l11Khoa(); });
  for (const id of ["l11-tl-nguon", "l11-tl-coverage", "l11-tl-tep", "l11-tl-khoa", "l11-tl-mau"]) {
    $(id).addEventListener("change", () => { l11FormEpoch += 1; });
    $(id).addEventListener("input", () => { l11FormEpoch += 1; });
  }
  const l11Claim = () => { const [inst, scope] = JSON.parse($("l11-tl-nguon").value || "[]"); return {source_instance: inst, scope_ref: scope, coverage: $("l11-tl-coverage").value, khoa: $("l11-tl-khoa").value.trim()}; };
  $("l11-tl-gui-mau").addEventListener("click", async () => {
    const fe = l11FormEpoch;
    await l11Act("l11/proof/nhan", {...l11Claim(), fixture_ref: $("l11-tl-mau").value}, "Đã nhận bằng chứng (thô)", () => fe === l11FormEpoch);
  });
  $("l11-tai-len").addEventListener("submit", async event => {
    event.preventDefault();
    const ep = l11Epoch, fe = l11FormEpoch, claim = l11Claim(), f = ($("l11-tl-tep").files || [])[0] || null;
    if (!f) { $("l11-status").textContent = "Chọn tệp bằng chứng JSON."; return; }
    try {
      const native = await m5DocTep(f);
      if (ep !== l11Epoch) return;
      if (fe !== l11FormEpoch) { $("l11-status").textContent = "Form đã đổi trong lúc đọc tệp — kiểm tra rồi gửi lại."; return; }
      await l11Act("l11/proof/nhan", {...claim, native_b64: native}, "Đã nhận bằng chứng (thô)", () => fe === l11FormEpoch);
    } catch (error) { if (ep === l11Epoch) { toast(error.message, true); $("l11-status").textContent = error.message; } }
  });
  window.addEventListener("hashchange", () => { if (location.hash === "#lienketsoluong") l11Load(); });
  if (location.hash === "#lienketsoluong") l11Load();
  window.addEventListener("beforeunload", event => { if (busy || queue.length) { event.preventDefault(); event.returnValue = ""; } });
  // M4-01C: trang Cổng hồ sơ M4 (#m4, nội dung do /m4.js dựng trong #page-m4) + API seam tối thiểu cho m4.js. Không lộ token/actor/quyền;
  // m4.js chỉ dùng tiện ích hiển thị và cổng đổi vai chung (đăng ký người tham gia, barrier, hàng POST).
  pages.m4 = "Hồ sơ xây dựng (M4)";
  window.kttChung = Object.freeze({node, empty, toast, size, date, dangKyVai, vaiDangChan, doiVaiTuanTu});
  route(); refresh().catch(() => {}); ntLoad(); if (location.hash === "#hopdong") crmLoad(); if (location.hash === "#khoanvay") m9Load();
})();
