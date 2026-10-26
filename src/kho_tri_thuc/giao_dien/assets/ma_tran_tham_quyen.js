"use strict";
// MTQ-3a: asset độc lập, không tự gắn vào shell, không tự áp mẫu.
// dungMaTranThamQuyen(element, {laAdmin: false, tenPhapNhan(id), tenNguoi(id)})
// laAdmin chỉ chọn màn/route; thẩm quyền luôn do máy chủ kiểm. Mặc định chỉ cua-toi.
// Hai hàm tên là seam NHÃN của shell MTQ-3b, không được gửi làm căn cứ quyền.
// DTO MTQ-2 chưa có tên pháp nhân/người, thời điểm sửa;
// lấy thời điểm từ nhat-ky, thiếu tên thì báo rõ, không hiện UUID/login kỹ thuật.
(function (scope) {
  const VAI = [
    ["THUC_HIEN_1", "Người thực hiện 1"], ["THUC_HIEN_2", "Người thực hiện 2"],
    ["TRUONG_PHONG", "Trưởng phòng"], ["CFO", "CFO"], ["NGUOI_XEM", "Người xem"]
  ];
  const HD = [["XEM", "Xem"], ["LAP", "Lập"], ["SUA", "Sửa"], ["KIEM", "Kiểm"], ["DUYET", "Duyệt"], ["HUY", "Hủy"]];
  const MODULE = {CRM: "CRM · Khách hàng & hợp đồng", M1: "M1 · Tiền về / tiền đi", M2: "M2 · Mua hàng / Hóa đơn mua vào", M4: "M4 · Nghiệm thu & chi phí dự án", M5: "M5 · Kho & số lượng"};
  const MAN = {
    TIEP_NHAN: "Tiếp nhận hợp đồng ký", G1_MAU: "Mẫu hợp đồng", G7_CHUAN: "Bộ chuẩn dự án",
    G2_BAO_GIA: "Báo giá", G3_G4_SOAN_KY: "Soạn / Ký kết", G5_G6_KIEM_KY: "Kiểm hợp đồng ký",
    DU_AN_BAN: "Dự án đang bán / mốc / phí", TY_GIA: "Tỷ giá mặc định", FILE_SOAT: "Báo cáo & file soát",
    BAN_KY: "Bản ký", TIEN: "Tiền về / tiền đi", XEM_TIEN: "Xem tiền", HOA_DON: "Hóa đơn mua vào",
    NGUON_THO: "Nguồn thô", KHO: "Kho & số lượng", L11: "Liên kết số lượng", HO_SO: "Hồ sơ dự án",
    "02A_REVIEW": "Review đợt", "02B_CHUNG_TU": "Chứng từ", "02C_DUYET": "Duyệt hồ sơ đợt",
    PDF_DA_DUYET: "PDF hồ sơ đã duyệt", "03A_KE_TOAN": "Kế toán nghiệm thu",
    "03B_DOI_CHIEU": "Ghi nhận đối chiếu", "04_REQUEST_NHAP": "Request nháp"
  };
  const cellKey = c => JSON.stringify([c.module, c.man, c.hanh_dong]);
  function money(value) {
    if (value === null || value === undefined || value === "") return null;
    if (typeof value !== "string" && !(typeof value === "number" && Number.isSafeInteger(value))) throw Error("Hạn mức phải là số nguyên không âm, tối đa 20 chữ số.");
    const s = String(value).trim();
    if (!s) return null;
    if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+)$/.test(s)) throw Error("Hạn mức phải là số nguyên không âm, tối đa 20 chữ số.");
    const raw = s.replace(/\./g, "").replace(/^0+(?=\d)/, "");
    if (raw.length > 20) throw Error("Hạn mức tối đa 20 chữ số.");
    return raw;
  }
  const moneyText = v => v === null ? "Không giới hạn" : v.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " VND";
  function timeText(value) {
    if (!value) return "Chưa có thông tin";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "Chưa có thông tin";
    const p = new Intl.DateTimeFormat("en-GB", {timeZone: "Asia/Ho_Chi_Minh", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23"}).formatToParts(d);
    const get = t => p.find(x => x.type === t).value;
    return `${get("day")}/${get("month")}/${get("year")} ${get("hour")}:${get("minute")}`;
  }
  function dungMaTranThamQuyen(root, options = {}) {
    const doc = root.ownerDocument || scope.document;
    const node = (tag, text, cls) => {
      const e = doc.createElement(tag);
      if (text !== undefined) e.textContent = String(text); // DOM text node escape mọi nguồn.
      if (cls) e.className = cls;
      return e;
    };
    const token = (doc.querySelector('meta[name="ktt-token"]') || {}).content || "";
    let data = null, logs = null, logError = "", pn = "", room = "", versionId = "";
    let rows = [], original = [], catalog = [], reason = "", busy = false, blocked = false, dead = false, generation = 0;
    let retry = null, logOpen = false, pending = null;
    const folded = new Set();
    const view = node("section", undefined, "mtq-man"); root.replaceChildren(view);
    let message, diffBox, saveButton, publishButton, activateButton, reasonInput;
    const isAdmin = () => options.laAdmin === true && data && data.admin === true;
    const version = () => (data.phien_ban || []).find(v => v.id === versionId);
    const activation = () => (data.kich_hoat || []).find(k => k.phap_nhan_id === pn);
    const canActivate = () => isAdmin() && data.chua_noi_mtq4 === false && version()?.trang_thai === "DA_CONG_BO" && !(activation()?.bat && activation().phien_ban_id === versionId);
    const roomName = id => (data.phong || []).find(p => p.id === id)?.ten || (data.dong || []).find(d => d.phong_id === id)?.ten_phong || "Chưa có tên phòng";
    const personName = id => (options.tenNguoi && options.tenNguoi(id)) || "Chưa có tên hiển thị";
    const legalIds = () => [...new Set([...(data.phong || []), ...(data.phien_ban || []), ...(data.dong || [])].map(x => x.phap_nhan_id))];
    const legalName = id => (options.tenPhapNhan && options.tenPhapNhan(id)) || `Pháp nhân ${legalIds().indexOf(id) + 1} (chưa có tên)`;
    async function api(path, body) {
      const res = await scope.fetch("/api/tham-quyen/" + path, {
        method: body ? "POST" : "GET", credentials: "same-origin", cache: "no-store",
        headers: {"X-KTT-Token": token, ...(body ? {"Content-Type": "application/json"} : {})},
        ...(body ? {body: JSON.stringify(body)} : {})
      });
      const payload = await res.json();
      if (!res.ok) {
        const reason = ({
          MTQ_CHUA_NOI_MTQ4: "Chưa thể bật: các chức năng chưa hoàn tất kiểm tra thẩm quyền.",
          MTQ_THIEU_DONG: "Chưa đủ năm vai tại mọi phòng hoạt động.",
          MTQ_CON_TRO_SAI: "Chưa thể bật: cần chọn bản đã công bố của đúng pháp nhân."
        })[payload.error] || "";
        const e = Error(res.status === 403 ? "Anh không có quyền thực hiện thao tác này." : res.status === 409 ? "Đã có người khác sửa, tải lại" + (reason ? ". " + reason : "") : reason || "Máy chủ từ chối yêu cầu. Vui lòng kiểm tra lại hoặc tải lại.");
        e.status = res.status; throw e;
      }
      return payload;
    }
    const show = text => { if (message) message.textContent = text; };
    function button(text, action, cls) {
      const b = node("button", text, cls); b.type = "button"; b.disabled = busy;
      b.addEventListener("click", () => { if (!b.disabled && !dead) action(); }); return b;
    }
    function prepare() {
      const v = version();
      catalog = (data.danh_muc || []).filter(c => c.catalog_version === (v ? v.catalog_version : 1) && MODULE[c.module] && MAN[c.man] && HD.some(a => a[0] === c.hanh_dong));
      rows = VAI.filter(([vai]) => isAdmin() || data.dong.some(d => d.phien_ban_id === versionId && d.phong_id === room && d.vai === vai)).map(([vai]) => {
        const d = data.dong.find(x => x.phien_ban_id === versionId && x.phong_id === room && x.vai === vai);
        return {phong_id: room, vai, gioi_han_vnd: money(d ? d.gioi_han_vnd : null), o: catalog.map(c => ({module: c.module, man: c.man, hanh_dong: c.hanh_dong, cho_phep: !!d?.o.some(o => cellKey(o) === cellKey(c) && o.cho_phep === true)})), missing: !d, error: ""};
      });
      original = JSON.parse(JSON.stringify(rows)); reason = "";
    }
    function differences() {
      const list = [];
      rows.forEach((r, i) => {
        const before = original[i], name = VAI.find(v => v[0] === r.vai)[1];
        if (r.missing) list.push(name + ": Chưa có dòng → Tạo dòng quyền");
        if (r.gioi_han_vnd !== before.gioi_han_vnd) list.push(`${name} · Giới hạn số tiền: ${moneyText(before.gioi_han_vnd)} → ${moneyText(r.gioi_han_vnd)}`);
        r.o.forEach((c, j) => { if (c.cho_phep !== before.o[j].cho_phep) list.push(`${name} · ${MODULE[c.module]} · ${MAN[c.man]} · ${HD.find(a => a[0] === c.hanh_dong)[1]}: ${before.o[j].cho_phep ? "Có" : "Không"} → ${c.cho_phep ? "Có" : "Không"}`); });
      });
      return list;
    }
    const hasEdits = () => rows.some((r, i) => r.error || r.gioi_han_vnd !== original[i].gioi_han_vnd || r.o.some((c, j) => c.cho_phep !== original[i].o[j].cho_phep));
    function updateDiff() {
      if (!diffBox) return;
      diffBox.replaceChildren(node("h3", "Thay đổi trước khi lưu"));
      const changes = differences(), ul = node("ul"); changes.forEach(t => ul.append(node("li", t)));
      diffBox.append(changes.length ? ul : node("p", "Chưa có thay đổi."));
      const invalid = rows.some(r => r.error);
      saveButton.disabled = busy || blocked || invalid || !room || !catalog.length || !changes.length || !reason.trim() || reason.length > 2000;
      publishButton.disabled = busy || blocked || invalid || changes.length > 0 || !reason.trim() || reason.length > 2000 || version()?.trang_thai !== "NHAP";
      if (activateButton) activateButton.disabled = busy || blocked || invalid || changes.length > 0 || !reason.trim() || reason.length > 2000 || !canActivate();
    }
    function selectField(label, items, current, changed) {
      const wrap = node("label", label, "mtq-field"), sel = node("select");
      items.forEach(([id, title]) => { const o = node("option", title); o.value = id; sel.append(o); });
      sel.value = current; sel.disabled = busy;
      sel.addEventListener("change", () => {
        if (busy || pending || (isAdmin() && hasEdits())) { sel.value = current; show("Lưu nháp hoặc tải lại trước khi đổi lựa chọn."); return; }
        changed(sel.value); prepare(); render();
      }); wrap.append(sel); return wrap;
    }
    function table() {
      const wrap = node("div", undefined, "mtq-scroll"), t = node("table", undefined, "mtq-table");
      t.append(node("caption", "Quyền theo vai và giới hạn số tiền"));
      const head = node("thead"), top = node("tr"), mid = node("tr"), low = node("tr");
      ["Vai", "Giới hạn số tiền (VND)"].forEach((name, i) => { const th = node("th", name, i ? "mtq-limit" : "mtq-role"); th.rowSpan = 3; th.scope = "col"; top.append(th); });
      const groups = [...new Set(catalog.map(c => c.module))];
      const columns = [];
      for (const mod of groups) {
        const screens = [...new Set(catalog.filter(c => c.module === mod).map(c => c.man))];
        const collapsed = folded.has(mod), th = node("th");
        th.colSpan = collapsed ? 1 : screens.reduce((n, s) => n + (folded.has(mod + ":" + s) ? 1 : 6), 0);
        const b = button((collapsed ? "+ " : "− ") + MODULE[mod], () => { folded.has(mod) ? folded.delete(mod) : folded.add(mod); render(); });
        b.setAttribute("aria-expanded", String(!collapsed)); th.append(b); top.append(th);
        if (collapsed) {
          const h = node("th", "Đã gấp"); h.rowSpan = 2; mid.append(h); columns.push(null); continue;
        }
        for (const screen of screens) {
          const key = mod + ":" + screen, closed = folded.has(key), h = node("th"); h.colSpan = closed ? 1 : 6;
          const b = button((closed ? "+ " : "− ") + MAN[screen], () => { folded.has(key) ? folded.delete(key) : folded.add(key); render(); });
          b.setAttribute("aria-expanded", String(!closed)); h.append(b); mid.append(h);
          if (closed) { low.append(node("th", "Đã gấp")); columns.push(null); }
          else HD.forEach(([action, label]) => { low.append(node("th", label)); columns.push({module: mod, man: screen, hanh_dong: action}); });
        }
      }
      const paused = node("th", "M9 · Vốn vay & đầu tư tài chính — Tạm dừng", "mtq-paused"); paused.rowSpan = 3; top.append(paused);
      head.append(top, mid, low); t.append(head);
      const body = node("tbody");
      rows.forEach((r, i) => {
        const roleName = VAI.find(v => v[0] === r.vai)[1];
        const tr = node("tr", undefined, "mtq-row"), role = node("th", roleName, "mtq-role"); role.scope = "row";
        const limit = node("td", undefined, "mtq-limit"); tr.append(role, limit);
        if (isAdmin()) {
          const input = node("input", undefined, "mtq-money"), display = node("span", moneyText(r.gioi_han_vnd)), error = node("span", r.error, "mtq-error");
          input.type = "text"; input.inputMode = "numeric"; input.value = r.error ? r.raw : (r.gioi_han_vnd === null ? "" : moneyText(r.gioi_han_vnd).replace(" VND", ""));
          input.placeholder = "Không giới hạn"; input.disabled = busy || blocked;
          input.setAttribute("aria-label", roleName + " · Giới hạn số tiền (VND)");
          input.setAttribute("aria-invalid", String(!!r.error));
          input.addEventListener("input", () => {
            if (busy || blocked) return;
            r.raw = input.value;
            try { r.gioi_han_vnd = money(input.value); r.error = ""; display.textContent = moneyText(r.gioi_han_vnd); }
            catch (e) { r.error = e.message; display.textContent = ""; }
            error.textContent = r.error; input.setAttribute("aria-invalid", String(!!r.error)); updateDiff();
          });
          input.addEventListener("blur", () => { if (!r.error) input.value = r.gioi_han_vnd === null ? "" : moneyText(r.gioi_han_vnd).replace(" VND", ""); });
          limit.append(input, display, error);
        } else limit.append(node("span", moneyText(r.gioi_han_vnd)));
        columns.forEach(c => {
          const td = node("td");
          const value = c && r.o.find(o => cellKey(o) === cellKey(c));
          if (!value) td.append(node("span", c ? "—" : "…"));
          else if (!isAdmin()) td.append(node("span", value.cho_phep ? "Có" : "Không"));
          else {
            const input = node("input"); input.type = "checkbox"; input.checked = value.cho_phep; input.disabled = busy || blocked;
            input.setAttribute("aria-label", `${roleName} · ${MODULE[c.module]} · ${MAN[c.man]} · ${HD.find(a => a[0] === c.hanh_dong)[1]}`);
            input.addEventListener("change", () => { if (busy || blocked) return; value.cho_phep = input.checked; updateDiff(); }); td.append(input);
          }
          tr.append(td);
        }); tr.append(node("td", "Tạm dừng", "mtq-paused")); body.append(tr);
      });
      t.append(body); wrap.append(t); return wrap;
    }
    function auditDetail(event) {
      const before = event.truoc || {}, after = event.sau || {}, target = after.module ? after : event.doi_tuong || {};
      if (target.module && target.man && target.hanh_dong) return `${MODULE[target.module] || "Nhóm chức năng"} · ${MAN[target.man] || "Màn chức năng"} · ${HD.find(a => a[0] === target.hanh_dong)?.[1] || "Thao tác"}: ${before.cho_phep === true ? "Có" : "Không"} → ${after.cho_phep === true ? "Có" : "Không"}`;
      if (Object.prototype.hasOwnProperty.call(after, "gioi_han_vnd")) return `${VAI.find(v => v[0] === after.vai)?.[1] || "Vai"} · Giới hạn số tiền: ${moneyText(money(before.gioi_han_vnd))} → ${moneyText(money(after.gioi_han_vnd))}`;
      return ({NHAP: "Tạo bản nháp", DONG: "Cập nhật dòng quyền", O: "Cập nhật ô quyền", CONG_BO: "Công bố phiên bản", KICH_HOAT: "Bật ma trận", HTTP_LUU_NHAP: "Lưu bản nháp", HTTP_CONG_BO: "Công bố phiên bản", HTTP_KICH_HOAT: "Bật ma trận"})[event.loai_su_kien] || "Thay đổi cấu hình thẩm quyền";
    }
    function render() {
      if (dead) return;
      view.replaceChildren(node("h2", isAdmin() ? "Ma trận thẩm quyền" : "Quyền của tôi"));
      message = node("p", "", "mtq-message"); message.setAttribute("role", "status"); view.append(message);
      if (!data) return;
      if (!legalIds().length) { view.append(node("p", "Chưa có quyền đang áp dụng.")); return; }
      const controls = node("div", undefined, "mtq-controls");
      controls.append(selectField("Pháp nhân", legalIds().map(id => [id, legalName(id)]), pn, id => { pn = id; choose(); }));
      const rooms = isAdmin() ? data.phong.filter(p => p.phap_nhan_id === pn && p.hoat_dong).map(p => p.id) : [...new Set(data.dong.filter(d => d.phap_nhan_id === pn).map(d => d.phong_id))];
      controls.append(selectField("Phòng", rooms.map(id => [id, roomName(id)]), room, id => { room = id; }));
      controls.append(selectField("Phiên bản", data.phien_ban.filter(v => v.phap_nhan_id === pn).map(v => [v.id, `${v.so_phien_ban} · ${v.trang_thai === "NHAP" ? "Bản nháp" : "Đã công bố"}`]), versionId, id => { versionId = id; }));
      controls.append(button("Tải lại", () => { load(); })); view.append(controls);
      const v = version(), last = (logs?.thay_doi || []).filter(e => e.phien_ban_id === versionId).sort((a, b) => new Date(b.luc) - new Date(a.luc))[0];
      view.append(node("p", `${activation()?.bat ? "Đang dùng" : "Chưa bật"} · Phiên bản ${v ? v.so_phien_ban : "chưa có"}${activation()?.bat && activation().phien_ban_id !== versionId ? " · Bản đang xem chưa áp dụng" : ""}`, "mtq-state"));
      if (isAdmin()) view.append(node("p", `Lần sửa cuối: ${timeText(last?.luc)} · Người sửa: ${last ? personName(last.actor_id) : "Chưa có thông tin"}`));
      if (logError) view.append(node("p", logError, "mtq-error"));
      if (!room) { view.append(node("p", "Chưa có phòng hoạt động để cấu hình.")); return; }
      view.append(table());
      if (!isAdmin()) { view.append(node("p", "Chỉ đọc quyền đang áp dụng. Ô Không chưa được cấp; ô — chưa có chức năng. Quyền thao tác còn phụ thuộc phạm vi và điều kiện nghiệp vụ.")); return; }
      diffBox = node("div", undefined, "mtq-diff"); view.append(diffBox);
      const label = node("label", "Lý do (bắt buộc, tối đa 2.000 ký tự)", "mtq-field");
      reasonInput = node("textarea"); reasonInput.value = reason; reasonInput.maxLength = 2000; reasonInput.disabled = busy || blocked;
      reasonInput.addEventListener("input", () => { reason = reasonInput.value; updateDiff(); }); label.append(reasonInput); view.append(label);
      const actions = node("div", undefined, "mtq-controls");
      saveButton = button("Lưu nháp", () => { write("luu-nhap"); });
      publishButton = button("Công bố", () => { confirmPublish(); });
      actions.append(saveButton, publishButton, button(logOpen ? "Ẩn nhật ký" : "Xem nhật ký", () => { logOpen = !logOpen; render(); }));
      // MTQ-2 luôn true: cấm bật. Thiếu cờ cũng cấm, không suy từ vai Admin.
      activateButton = null;
      if (canActivate()) { activateButton = button("Bật", () => { confirmPublish("kich-hoat"); }); actions.append(activateButton); }
      view.append(actions);
      if (data.chua_noi_mtq4 !== false) view.append(node("p", "Chưa thể bật: các chức năng chưa hoàn tất kiểm tra thẩm quyền.", "mtq-note"));
      if (logOpen) {
        const log = node("section", undefined, "mtq-log"); log.append(node("h3", "Nhật ký thay đổi"));
        (logs?.thay_doi || []).filter(e => e.phap_nhan_id === pn).forEach(e => {
          const item = node("article"); item.append(node("p", `${timeText(e.luc)} · ${personName(e.actor_id)}`), node("p", "Lý do: " + e.ly_do), node("p", auditDetail(e))); log.append(item);
        });
        if (!logs?.thay_doi?.some(e => e.phap_nhan_id === pn)) log.append(node("p", "Chưa có nhật ký thay đổi."));
        view.append(log);
      }
      updateDiff();
    }
    function confirmPublish(command = "cong-bo") {
      if (busy || blocked || pending || (command === "kich-hoat" ? !canActivate() || activateButton.disabled : publishButton.disabled)) return;
      const dialog = node("dialog", undefined, "mtq-confirm");
      const empty = !data.dong.some(d => d.phien_ban_id === versionId && d.o.some(o => o.cho_phep));
      const verb = command === "kich-hoat" ? "Bật" : "Công bố", confirmText = command === "kich-hoat" ? "Xác nhận bật" : "Xác nhận công bố";
      dialog.append(node("h3", confirmText), node("p", `${verb} phiên bản ${version().so_phien_ban} của ${legalName(pn)}?${empty ? " Toàn bộ ô quyền đang tắt; khi bật sẽ không cấp hành động nào." : ""}`));
      const close = () => { dialog.close(); dialog.hidden = true; pending = null; };
      dialog.append(button("Quay lại", close), button(confirmText, () => { close(); write(command); }));
      dialog.addEventListener("cancel", () => { pending = null; });
      pending = dialog; view.append(dialog); dialog.showModal();
    }
    async function write(command) {
      if (busy || blocked || !isAdmin() || !reason.trim() || reason.length > 2000 || rows.some(r => r.error)) { show("Cần nhập lý do hợp lệ và kiểm tra hạn mức trước khi gửi."); return; }
      if (command === "luu-nhap" && saveButton.disabled) return;
      if (command === "cong-bo" && publishButton.disabled) return;
      if (command === "kich-hoat" && (!canActivate() || activateButton.disabled)) return;
      const v = version(), body = {expected_revision: v?.trang_thai === "NHAP" ? v.revision : 0, ly_do: reason.trim()};
      if (v) body[command !== "luu-nhap" || v.trang_thai === "NHAP" ? "phien_ban_id" : "nguon_id"] = v.id;
      if (command === "kich-hoat") body.expected_revision = activation()?.revision || 0;
      if (command === "luu-nhap") body.dong = rows.map(r => ({phong_id: r.phong_id, vai: r.vai, gioi_han_vnd: r.gioi_han_vnd, o: r.o.map(c => ({...c}))}));
      const signature = JSON.stringify([command, body]);
      if (!retry || retry.signature !== signature) retry = {signature, khoa: scope.crypto.randomUUID()};
      body.khoa = retry.khoa;
      busy = true; render(); const current = generation;
      try {
        const result = await api(command, body);
        if (dead || current !== generation) return;
        retry = null; versionId = command === "kich-hoat" ? result.ket_qua.phien_ban_id : result.ket_qua.id;
        await load(); if (!dead) show(command === "luu-nhap" ? "Đã lưu nháp." : command === "kich-hoat" ? "Đã bật ma trận." : "Đã công bố phiên bản.");
      } catch (e) {
        if (dead || current !== generation) return;
        if (e.status === 403 || e.status === 409) blocked = true;
        busy = false; render(); show(e.status ? e.message : "Mất kết nối, chưa rõ kết quả. Thử lại cùng nội dung để kiểm tra yêu cầu cũ.");
      }
    }
    function choose() {
      const versions = data.phien_ban.filter(v => v.phap_nhan_id === pn);
      if (!versions.some(v => v.id === versionId)) versionId = versions.slice().sort((a, b) => b.so_phien_ban - a.so_phien_ban)[0]?.id || "";
      const rooms = isAdmin() ? data.phong.filter(p => p.phap_nhan_id === pn && p.hoat_dong).map(p => p.id) : [...new Set(data.dong.filter(d => d.phap_nhan_id === pn).map(d => d.phong_id))];
      if (!rooms.includes(room)) room = rooms[0] || "";
    }
    async function load() {
      if (dead || (busy && !data)) return;
      const current = ++generation; busy = true; blocked = false;
      if (data) render(); else { view.replaceChildren(node("p", "Đang tải quyền…")); }
      try {
        const next = await api(options.laAdmin === true ? "ma-tran" : "cua-toi");
        if (dead || current !== generation) return;
        data = next; logs = null; logError = "";
        if (isAdmin()) {
          try { logs = await api("nhat-ky"); }
          catch (e) { logError = e.status ? e.message : "Chưa tải được nhật ký. Vui lòng tải lại."; }
          if (dead || current !== generation) return;
        }
        if (!legalIds().includes(pn)) pn = legalIds()[0] || "";
        choose(); prepare(); busy = false; render();
      } catch (e) {
        if (dead || current !== generation) return;
        busy = false; blocked = true;
        // Không để ma trận phiên trước tồn tại sau khi bị từ chối tải lại.
        data = null; rows = []; view.replaceChildren(node("p", e.status ? e.message : "Không tải được quyền. Vui lòng thử lại.", "mtq-error"), button("Tải lại", () => { load(); }));
      }
    }
    return {sanSang: load(), taiLai: load, huy() { dead = true; ++generation; data = logs = null; rows = original = []; root.replaceChildren(); }};
  }
  if (typeof module === "object" && module.exports) module.exports = dungMaTranThamQuyen;
  else scope.dungMaTranThamQuyen = dungMaTranThamQuyen;
})(typeof window !== "undefined" ? window : globalThis);
