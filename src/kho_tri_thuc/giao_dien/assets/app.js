"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const token = document.querySelector('meta[name="ktt-token"]').content;
  const pages = {nhap: "Nhập dữ liệu", hoso: "Hồ sơ đã nhận", khanang: "Khả năng xử lý", huongdan: "Hướng dẫn sử dụng", mau: "Thử dữ liệu mẫu"};
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
    document.title = "Kho tri thức · " + pages[key];
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
  window.addEventListener("beforeunload", event => { if (busy || queue.length) { event.preventDefault(); event.returnValue = ""; } });
  route(); refresh().catch(() => {});
})();
