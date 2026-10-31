/* SDK trình duyệt Core. Không giữ cookie, CSRF hoặc nháp trong kho trình duyệt. */
(function (root, factory) {
  'use strict';
  const sdk = factory();
  if (typeof module === 'object' && module.exports) module.exports = sdk;
  else root.KttCore = sdk;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const ketThuc = new Set(['succeeded', 'failed', 'cancelled', 'interrupted']);
  const dangChay = new Set(['queued', 'running', 'waiting_input', 'cancel_requested']);
  const sao = value => value === undefined ? undefined : JSON.parse(JSON.stringify(value));
  const loi = (ma, message) => Object.assign(new Error(message), { ma });

  function duongDan(value) {
    if (typeof value !== 'string' || !value.startsWith('/api/v1/') ||
        /[\\\s#]/.test(value) || /[\u0000-\u001f\u007f]/.test(value)) {
      throw loi('DUONG_DAN_KHONG_HOP_LE', 'Chỉ được gửi yêu cầu tới Core.');
    }
    // Không cho URL parser chuẩn hóa traversal hoặc encoded separator trước kiểm tra.
    const path = value.split('?')[0];
    if (path.includes('%') || path.includes('//') || path.split('/').some(s => s === '.' || s === '..')) {
      throw loi('DUONG_DAN_KHONG_HOP_LE', 'Đường dẫn yêu cầu không hợp lệ.');
    }
    return value;
  }

  function tre(ms, signal) {
    return new Promise((resolve, reject) => {
      if (signal.aborted) return reject(new DOMException('Đã dừng theo dõi.', 'AbortError'));
      const dung = () => { clearTimeout(timer); reject(new DOMException('Đã dừng theo dõi.', 'AbortError')); };
      const timer = setTimeout(() => { signal.removeEventListener('abort', dung); resolve(); }, ms);
      signal.addEventListener('abort', dung, { once: true });
    });
  }

  function doiSau(value, now = Date.now()) {
    if (value === null || value === undefined || value === '') return 2000;
    if (/^\d+(\.\d+)?$/.test(value)) return Number(value) * 1000;
    const date = Date.parse(value);
    return Number.isFinite(date) ? Math.max(0, date - now) : 2000;
  }

  function tao({ fetch: tai = globalThis.fetch?.bind(globalThis), cho = tre, dong_ho = Date.now,
                 tao_ma = () => globalThis.crypto.randomUUID() } = {}) {
    let context = Object.freeze({}), csrf = '', theHe = 0;
    const controllers = new Set(), yDinh = new Map(), viecNhan = new Map();

    function doi_ngu_canh(next = {}) {
      theHe += 1;
      for (const controller of controllers) controller.abort();
      controllers.clear();
      viecNhan.clear();
      // Bỏ nội dung nháp khi đổi chủ; giữ fingerprint để không tái dùng nhầm khóa.
      if ((next.nguoi_dung_id ?? null) !== (context.nguoi_dung_id ?? null) ||
          (next.phap_nhan_id ?? null) !== (context.phap_nhan_id ?? null)) {
        for (const intent of yDinh.values()) intent.nhap = undefined;
      }
      // CSRF do Core cấp; không kế thừa token của người trước.
      if (next.nguoi_dung_id !== context.nguoi_dung_id) csrf = '';
      context = Object.freeze({ nguoi_dung_id: next.nguoi_dung_id ?? null,
        phap_nhan_id: next.phap_nhan_id ?? null, module: next.module ?? null, man: next.man ?? null });
    }

    async function trongContext(signal, fn) {
      const epoch = theHe, ctx = context, controller = new AbortController();
      const stop = () => controller.abort();
      if (signal?.aborted) stop();
      else signal?.addEventListener('abort', stop, { once: true });
      controllers.add(controller);
      const kiem = () => {
        if (epoch !== theHe) throw loi('NGU_CANH_DA_DOI', 'Đã đổi màn hoặc pháp nhân. Phản hồi cũ được bỏ qua.');
        if (controller.signal.aborted) throw new DOMException('Đã dừng theo dõi.', 'AbortError');
      };
      try {
        kiem();
        const result = await fn(ctx, controller.signal, kiem);
        kiem();
        return result;
      } catch (error) {
        kiem();
        throw error;
      } finally {
        controllers.delete(controller);
        signal?.removeEventListener('abort', stop);
      }
    }

    async function gui(request, ctx, signal, kiem) {
      const path = duongDan(request.duong_dan), method = (request.phuong_thuc || 'GET').toUpperCase();
      if (!['GET', 'HEAD', 'POST', 'PATCH', 'PUT', 'DELETE'].includes(method)) {
        throw loi('PHUONG_THUC_KHONG_HOP_LE', 'Thao tác không được hỗ trợ.');
      }
      const ghi = !['GET', 'HEAD'].includes(method);
      const phapNhan = request.phap_nhan_id === undefined ? ctx.phap_nhan_id : request.phap_nhan_id;
      const maModule = request.module === undefined ? ctx.module : request.module;
      if ((ctx.phap_nhan_id && phapNhan !== ctx.phap_nhan_id) || (ctx.module && maModule !== ctx.module)) {
        throw loi('SAI_NGU_CANH', 'Anh chọn lại đúng pháp nhân và màn trước khi gửi.');
      }
      const body = request.du_lieu === undefined ? undefined : JSON.stringify(request.du_lieu);
      const nhap = body === undefined ? undefined : JSON.parse(body);
      if (nhap?.row_version !== undefined &&
          (typeof nhap.row_version !== 'string' || !/^\d+$/.test(nhap.row_version))) {
        throw loi('PHIEN_BAN_KHONG_HOP_LE', 'Anh tải lại phiên bản dữ liệu trước khi lưu.');
      }
      const headers = { Accept: 'application/json', 'X-Request-Id': tao_ma() };
      if (phapNhan) headers['X-Phap-Nhan-Id'] = phapNhan;
      if (maModule) headers['X-Module-Ma'] = maModule;
      if (body !== undefined) headers['Content-Type'] = 'application/json';
      if (ghi) {
        if (!csrf) throw loi('THIEU_CSRF', 'Anh tải lại phiên đăng nhập trước khi lưu.');
        headers['X-CSRF-Token'] = csrf;
        // API §3.6: đăng nhập và đăng xuất miễn khóa, vẫn cần CSRF.
        if (path.split('?')[0] !== '/api/v1/phien' || !['POST', 'DELETE'].includes(method)) {
          if (typeof request.khoa !== 'string' || !request.khoa.trim()) {
            throw loi('THIEU_KHOA', 'Cần giữ khóa thao tác để gửi lại an toàn.');
          }
        }
        if (request.khoa) {
          const fingerprint = JSON.stringify([ctx.nguoi_dung_id, phapNhan, maModule, method, path, body]);
          const old = yDinh.get(request.khoa);
          if (old && old.fingerprint !== fingerprint) {
            throw loi('KHOA_KHAC_NOI_DUNG', 'Nội dung hoặc pháp nhân đã đổi. Anh đối chiếu kết quả trước khi tạo thao tác mới.');
          }
          if (!old) yDinh.set(request.khoa, { fingerprint, nhap, da_xong: false,
            nguoi_dung_id: ctx.nguoi_dung_id ?? null, phap_nhan_id: phapNhan ?? null,
            module: maModule ?? null });
          headers['Idempotency-Key'] = request.khoa;
        }
      } else if (body !== undefined) {
        throw loi('DU_LIEU_KHONG_HOP_LE', 'Yêu cầu đọc không nhận nội dung ghi.');
      }
      kiem();
      // Trình duyệt tự gắn Origin. Redirect bị chặn trước khi chuyển cookie/header sang đích khác.
      const response = await tai(path, { method, headers, body, signal,
        credentials: 'same-origin', mode: 'same-origin', redirect: 'error', cache: 'no-store' });
      kiem();
      if (response.redirected || (response.status >= 300 && response.status < 400)) {
        throw loi('CHUYEN_HUONG_BI_CHAN', 'Core trả đường dẫn chuyển hướng không được hỗ trợ.');
      }
      const data = response.status === 204 || method === 'HEAD' ? null : await response.json();
      kiem();
      if (!response.ok) {
        const error = Object.assign(loi(data?.ma || 'YEU_CAU_THAT_BAI', 'Chưa hoàn tất yêu cầu. Anh thử tải lại hoặc kiểm tra phiên đăng nhập.'), {
          status: response.status, request_id: data?.request_id || response.headers.get('X-Request-Id'),
          chi_tiet: data?.chi_tiet, retry_after: response.headers.get('Retry-After'),
          nhap: ghi ? sao(nhap) : undefined, khoa: request.khoa
        });
        if (response.status === 409 && error.ma === 'XUNG_DOT_PHIEN_BAN') {
          error.message = 'Dữ liệu đã thay đổi. Bản nháp được giữ; Anh tải bản mới để đối chiếu trước khi lưu.';
        }
        throw error;
      }
      if (path === '/api/v1/phien' && data?.csrf_token) csrf = data.csrf_token;
      const retry = response.headers.get('Retry-After');
      if (response.status === 202) {
        if (!data?.viec_id) throw loi('PHAN_HOI_KHONG_HOP_LE', 'Chưa nhận được mã theo dõi công việc.');
        const location = duongDan(response.headers.get('Location') || `/api/v1/viec/${encodeURIComponent(data.viec_id)}`);
        if (location !== `/api/v1/viec/${encodeURIComponent(data.viec_id)}`) {
          throw loi('PHAN_HOI_KHONG_HOP_LE', 'Đường dẫn theo dõi công việc không khớp.');
        }
        viecNhan.set(data.viec_id, { path: location, retry, phap_nhan_id: phapNhan, module: maModule });
      } else if (ghi && request.khoa) yDinh.get(request.khoa).da_xong = true;
      return { data, retry, status: response.status };
    }

    async function theoDoi(id, options, ctx, signal, kiem) {
      if (typeof id !== 'string' || !/^[A-Za-z0-9_-]+$/.test(id)) {
        throw loi('VIEC_KHONG_HOP_LE', 'Mã theo dõi công việc không hợp lệ.');
      }
      const nhan = viecNhan.get(id);
      let retry = nhan?.retry, canCho = Boolean(nhan);
      for (;;) {
        kiem();
        if (canCho) { await cho(doiSau(retry, dong_ho()), signal); kiem(); }
        const result = await gui({ duong_dan: nhan?.path || `/api/v1/viec/${id}`,
          phap_nhan_id: nhan ? nhan.phap_nhan_id : ctx.phap_nhan_id,
          module: nhan ? nhan.module : ctx.module }, ctx, signal, kiem);
        kiem();
        const state = result.data?.trang_thai;
        if (!ketThuc.has(state) && !dangChay.has(state)) {
          throw loi('PHAN_HOI_KHONG_HOP_LE', 'Chưa xác định được trạng thái công việc. Anh tải lại để kiểm tra.');
        }
        options.khi_doi?.(sao(result.data));
        kiem();
        if (ketThuc.has(state)) { viecNhan.delete(id); return result.data; }
        retry = result.retry;
        canCho = true;
      }
    }

    const api = {
      doi_ngu_canh,
      gan_csrf: token => { csrf = typeof token === 'string' ? token : ''; },
      doc_nhap(khoa) {
        const intent = yDinh.get(khoa);
        if (!intent || intent.nguoi_dung_id !== (context.nguoi_dung_id ?? null) ||
            intent.phap_nhan_id !== (context.phap_nhan_id ?? null) ||
            intent.module !== (context.module ?? null)) return undefined;
        return sao(intent.nhap);
      },
      goi(request) {
        // Chụp ý định trước await: sửa form trong lúc chờ không đổi body/context retry.
        const frozen = { ...request, du_lieu: sao(request.du_lieu) };
        return trongContext(frozen.signal, async (ctx, signal, kiem) => {
          const pollContext = { ...ctx,
            phap_nhan_id: frozen.phap_nhan_id === undefined ? ctx.phap_nhan_id : frozen.phap_nhan_id,
            module: frozen.module === undefined ? ctx.module : frozen.module };
          for (;;) {
            let result;
            try { result = await gui(frozen, ctx, signal, kiem); }
            catch (error) {
              if (error.status !== 409 || error.ma !== 'YEU_CAU_DANG_XU_LY') throw error;
              await cho(doiSau(error.retry_after, dong_ho()), signal);
              kiem();
              continue;
            }
            return result.status === 202 && frozen.theo_doi === true
              ? theoDoi(result.data.viec_id, frozen, pollContext, signal, kiem) : result.data;
          }
        });
      }
    };
    const viec = {
      theo_doi: (id, options = {}) => trongContext(options.signal,
        (ctx, signal, kiem) => theoDoi(id, options, ctx, signal, kiem)),
      huy: (id, khoa) => api.goi({ phuong_thuc: 'POST', duong_dan: `/api/v1/viec/${encodeURIComponent(id)}/huy`, khoa })
    };
    return { api, viec };
  }

  function node(doc, tag, text, className) {
    const element = doc.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }

  function nhanDemo(root, phapNhan) {
    root.textContent = phapNhan?.la_demo === true ? 'DEMO' : '';
    root.hidden = phapNhan?.la_demo !== true;
    root.setAttribute('aria-label', 'Pháp nhân DEMO');
  }

  /* Nhận cấu trúc module/phan/the của UI-2. Caller chỉ truyền bản Core đã lọc.
     Cần lead: renderer UI-1 ở lat/ui-1 chưa có trong cây này; app.js của nhánh đó
     chỉ xuất dangKy/phanTich, gắn DOM/router/API cũ, chưa có renderer độc lập để gọi lại.
     Không tự suy quyền, đếm số hoặc nạp HTML/script từ đường dẫn module. */
  function dungKhung(root, khaiBao, { khi_mo = () => {}, khi_doi_man = () => {} } = {}) {
    const doc = root.ownerDocument;
    const modules = sao(khaiBao?.khong_quyen ? [] : Array.isArray(khaiBao?.module) ? khaiBao.module
      : khaiBao?.module ? [{ ...khaiBao.module, phan: khaiBao.phan || [], the: khaiBao.the || [] }] : []);
    const hayDung = new Set();
    let selected = null, tim = '', pageController;
    const shell = node(doc, 'div', undefined, 'core-khung');
    const rail = node(doc, 'nav', undefined, 'core-rail');
    rail.setAttribute('aria-label', 'Module nghiệp vụ');
    const main = node(doc, 'div', undefined, 'core-main');
    const breadcrumb = node(doc, 'nav', undefined, 'core-breadcrumb');
    breadcrumb.setAttribute('aria-label', 'Vị trí hiện tại');
    const search = node(doc, 'input'); search.type = 'search'; search.placeholder = 'Tìm nhanh nghiệp vụ…';
    search.setAttribute('aria-label', 'Tìm nhanh nghiệp vụ');
    const favorites = node(doc, 'div', undefined, 'core-hay-dung');
    const heading = node(doc, 'h1', 'Nghiệp vụ');
    const cards = node(doc, 'div', undefined, 'core-the');
    const grid = node(doc, 'div', undefined, 'core-luoi gk-luoi');
    const content = node(doc, 'section', undefined, 'core-noi-dung');
    content.setAttribute('aria-label', 'Nội dung trang module');
    main.append(breadcrumb, search, favorites, heading, cards, grid, content);
    shell.append(rail, main); root.replaceChildren(shell);

    function badge(parent, item) {
      if (item.day_du === false) parent.append(node(doc, 'span', 'Chưa đủ số liệu', 'core-chua-du'));
      else if (Number.isSafeInteger(item.so) && item.so > 0) {
        parent.append(node(doc, 'span', `${item.so}${item.canh_bao ? ' quá hạn' : ''}`, 'core-badge'));
      }
    }
    function tile(item, action, compact = false) {
      // Không phản chiếu mã kỹ thuật khi chưa có tên nghiệp vụ.
      const title = item.ten || item.nhan;
      if (!title) return null;
      const button = node(doc, 'button', undefined, compact ? 'core-icon' : 'core-o'); button.type = 'button';
      button.setAttribute('title', title);
      const icon = node(doc, 'span', title.slice(0, 1), 'core-icon-hinh'); icon.setAttribute('aria-hidden', 'true');
      button.append(icon, node(doc, 'span', title)); badge(button, item);
      button.addEventListener('click', action); return button;
    }
    function doiMan(ma) {
      pageController?.abort(); pageController = new AbortController();
      khi_doi_man({ module: selected?.ma || null, man: ma });
      content.replaceChildren();
    }
    function mo(item) {
      doiMan(item.ma);
      const signal = pageController.signal, maModule = selected.ma;
      hayDung.add(selected.ma);
      veHayDung();
      content.append(node(doc, 'h2', item.ten || item.nhan));
      if (item.loc) content.append(node(doc, 'p', item.giai_thich || 'Danh sách theo bộ lọc đã chọn.'));
      const page = node(doc, 'div'); content.append(page);
      Promise.resolve().then(() => {
        if (!signal.aborted) return khi_mo({ module: maModule, phan: sao(item), root: page, signal });
      }).catch(error => { if (!signal.aborted) thongBaoLoi(page, error); });
    }
    function veHayDung() {
      favorites.replaceChildren();
      if (!hayDung.size) return;
      favorites.append(node(doc, 'span', 'Hay dùng: '));
      for (const m of modules.filter(m => hayDung.has(m.ma))) {
        const button = tile(m, () => chon(m), true); if (button) favorites.append(button);
      }
    }
    function ve() {
      breadcrumb.replaceChildren();
      const home = node(doc, 'button', 'Nghiệp vụ'); home.type = 'button';
      home.addEventListener('click', () => chon(null)); breadcrumb.append(home);
      if (selected) breadcrumb.append(node(doc, 'span', ` / ${selected.ten}`));
      heading.textContent = selected?.ten || 'Nghiệp vụ';
      grid.replaceChildren(); cards.replaceChildren();
      const items = selected?.phan || modules;
      for (const item of items) {
        if (!(item.ten || '').toLocaleLowerCase('vi').includes(tim)) continue;
        const button = tile(item, () => selected ? mo(item) : chon(item)); if (button) grid.append(button);
      }
      if (!grid.children.length) grid.append(node(doc, 'p', 'Chưa có nghiệp vụ phù hợp trong phạm vi được cấp.'));
      for (const card of (selected?.the || []).slice(0, 4)) {
        const button = tile(card, () => mo(card)); if (button) cards.append(button);
      }
    }
    function chon(m) { selected = m; tim = ''; search.value = ''; doiMan(null); ve(); }
    search.addEventListener('input', () => { tim = search.value.trim().toLocaleLowerCase('vi'); ve(); });
    for (const m of modules) { const button = tile(m, () => chon(m), true); if (button) rail.append(button); }
    ve();
    return { noi_dung: content, dung: () => pageController?.abort() };
  }

  function thongBaoLoi(root, error) {
    if (error?.ma === 'NGU_CANH_DA_DOI' || error?.name === 'AbortError') return;
    const doc = root.ownerDocument;
    const box = node(doc, 'div', undefined, 'core-loi'); box.setAttribute('role', 'alert');
    box.append(node(doc, 'p', error?.status === 409 && error?.ma === 'XUNG_DOT_PHIEN_BAN'
      ? 'Dữ liệu đã thay đổi. Bản nháp được giữ. Anh tải bản mới để đối chiếu trước khi lưu.'
      : 'Chưa hoàn tất yêu cầu. Anh tải lại dữ liệu hoặc kiểm tra phiên đăng nhập.'));
    if (error?.request_id) {
      const details = node(doc, 'details'); details.append(node(doc, 'summary', 'Chi tiết hỗ trợ'),
        node(doc, 'p', `Mã tra cứu: ${error.request_id}`)); box.append(details);
    }
    root.replaceChildren(box);
  }

  return { tao, khung: { dung: dungKhung, nhan_demo: nhanDemo }, thong_bao: { loi: thongBaoLoi } };
});
