'use strict';
/* Kho tri thức kế toán — màn hình Định khoản (V10).
   Dựng lại từ bản bàn giao Claude Design (dinh-khoan-prototype.html), nối với phần lõi qua API cục bộ.
   Quy tắc giữ nguyên: phần mềm không tự nhập Junsky; chỉ giao dịch "Đã đồng ý" mới được xuất. */

/* =====================================================================
   1. TIỆN ÍCH
   ===================================================================== */
const TOKEN = (document.querySelector('meta[name="ktt-token"]') || {}).content || '';
const p2 = (n) => (n < 10 ? '0' : '') + n;
const fmt = (n) => String(Math.round(Math.abs(n || 0))).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const norm = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd');
const clone = (lines) => lines.map((l) => Object.assign({}, l));
const vnDate = (iso) => { const v = String(iso || '').slice(0, 10); return v.length === 10 ? v.slice(8, 10) + '/' + v.slice(5, 7) + '/' + v.slice(0, 4) : (iso || ''); };
const vnTime = (iso) => { if (!iso) return ''; const d = new Date(iso); return isNaN(d) ? String(iso) : p2(d.getDate()) + '/' + p2(d.getMonth() + 1) + '/' + d.getFullYear() + ' ' + p2(d.getHours()) + ':' + p2(d.getMinutes()); };
const isoFromVn = (v) => { const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(String(v || '').trim()); return m ? m[3] + '-' + m[2] + '-' + m[1] : null; };
const mask = (acct) => { const v = String(acct || ''); return v.length > 4 ? '•••• ' + v.slice(-4) : v; };
const ACTOR = 'CFO_NTD';

async function api(path, options) {
  const opts = options || {};
  const headers = Object.assign({ 'X-KTT-Token': TOKEN }, opts.headers || {});
  let body = opts.body;
  if (opts.json !== undefined) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(opts.json); }
  const res = await fetch(path, { method: opts.method || (body !== undefined ? 'POST' : 'GET'), headers, body });
  let data = null;
  try { data = await res.json(); } catch (e) { data = null; }
  if (!res.ok) { const err = new Error((data && data.message) || ('Lỗi ' + res.status)); err.code = data && data.error; throw err; }
  return data;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitJob(jobId, onProgress) {
  for (;;) {
    const job = await api('/api/that/job?id=' + encodeURIComponent(jobId));
    if (onProgress && job.progress) onProgress(job.progress);
    if (job.state === 'COMPLETED') return job.result;
    if (job.state === 'FAILED') { const err = new Error(job.message || 'Thao tác chưa hoàn tất.'); err.code = job.error; throw err; }
    await sleep(500);
  }
}
const store = {
  get(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* bỏ qua */ } }
};

const ICONS = {
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  checks: '<path d="M4 12.5l4 4L18 6.5"/><path d="M12 16.5l1 1L21 9"/>',
  checkCircle: '<circle cx="12" cy="12" r="9.5"/><path d="M8 12.5l2.7 2.7L16.2 9.6"/>',
  xCircle: '<circle cx="12" cy="12" r="9.5"/><path d="M9 9l6 6M15 9l-6 6"/>',
  warn: '<path d="M12 3.5L21.5 20h-19z"/><path d="M12 10v4.5"/><path d="M12 17.6v.01"/>',
  book: '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>',
  shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/>',
  upload: '<path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>',
  download: '<path d="M12 4v12"/><path d="M7 11l5 5 5-5"/><path d="M4 18v1a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-1"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  chevRight: '<path d="M9 6l6 6-6 6"/>',
  chevDown: '<path d="M6 9l6 6 6-6"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>'
};
const icon = (n, size, sw) => `<svg class="ic" width="${size || 16}" height="${size || 16}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${sw || 2}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${ICONS[n]}</svg>`;
const LV = {
  xanh: { label: 'Đủ căn cứ', tile: 'Xanh · Đủ căn cứ', icon: 'checkCircle' },
  vang: { label: 'Cần xem', tile: 'Vàng · Cần xem', icon: 'warn' },
  do: { label: 'Thiếu căn cứ', tile: 'Đỏ · Thiếu căn cứ', icon: 'xCircle' },
  junsky: { label: 'Có trong Junsky', tile: 'Đã có trong Junsky', icon: 'book' }
};
const badge = (k) => `<span class="badge badge--${k}">${icon(LV[k].icon, 14, 2.6)}${LV[k].label}</span>`;

/* =====================================================================
   2. DANH MỤC — nạp từ Junsky (qua lõi)
   ===================================================================== */
const CAT = { tk: [], dt: [], da: [], km: [], cp: [] };
const CAT_NAME = { tk: new Map(), dt: new Map(), da: new Map(), km: new Map(), cp: new Map() };
const CAT_KIND = { tk: 'ACCOUNT', dt: 'COUNTERPARTY', da: 'PROJECT', km: 'EXPENSE', cp: 'COST_CENTER' };
const FIELD_LABEL = { tk: 'Tài khoản', dt: 'Đối tượng', da: 'Dự án', km: 'Khoản mục', cp: 'Trung tâm chi phí' };
const nameOf = (k, code) => CAT_NAME[k].get(code) || '';
const lbl = (k, code) => (code ? code + (nameOf(k, code) ? ' – ' + nameOf(k, code) : '') : '');
const COMBO_LIMIT = 60;
function filterCat(k, q) {
  const nq = norm(q).trim(); const out = [];
  for (const r of CAT[k]) { if (!nq || r[2].indexOf(nq) >= 0) { out.push(r); if (out.length >= COMBO_LIMIT) break; } }
  return out;
}
function loadCatalog(data) {
  const c = (data && data.catalog) || {};
  Object.keys(CAT_KIND).forEach((k) => {
    const rows = c[CAT_KIND[k]] || [];
    CAT[k] = rows.map((r) => [r.code, r.name || '', norm(r.code + ' ' + (r.name || ''))]);
    CAT_NAME[k] = new Map(rows.map((r) => [r.code, r.name || '']));
  });
}

/* =====================================================================
   3. CHUYỂN DỮ LIỆU LÕI → GIAO DỊCH TRÊN MÀN HÌNH
   ===================================================================== */
let DEBT = ['131', '331', '141', '344', '1388', '3388'];
const isDebt = (tk) => /^\d+$/.test(tk || '') && DEBT.some((p) => String(tk).indexOf(p) === 0);
const LEVEL_MAP = { 'Xanh': 'xanh', 'Vàng': 'vang', 'Đỏ': 'do' };
const STATUS_MAP = { WAIT: 'cho', APPROVE: 'dongy', EXPORTED: 'dongy', SKIP: 'boqua', EXISTING: 'junsky' };
const toLine = (l) => ({ side: l.side, tk: l.account || '', amt: l.amount || 0, dt: l.counterparty || '', da: l.project || '', km: l.expense || '', cp: l.cost_center || '' });
const toServerLine = (l) => ({ side: l.side, account: l.tk || '', amount: Math.round(l.amt || 0), counterparty: l.dt || '', project: l.da || '', expense: l.km || '', cost_center: l.cp || '' });
const linesKey = (lines) => JSON.stringify(lines.map((l) => [l.side, l.tk, l.amt, l.dt, l.da, l.km, l.cp]));
function toTxn(r) {
  const status = STATUS_MAP[r.state] || 'cho';
  const level = r.state === 'EXISTING' ? 'junsky' : (LEVEL_MAP[r.proposal_level] || 'do');
  const lines = (r.entry_lines || []).map(toLine);
  /* V12: hóa đơn — chiều là Mua vào / Bán ra */
  const inv = r.invoice_direction || '';
  const dir = inv ? (inv === 'MUA_VAO' ? 'mua' : 'ban') : (r.amount_minor > 0 ? 'thu' : 'chi');
  const options = (r.options || []).map((o) => ({ label: o.label, note: o.note, lines: (o.lines || []).map(toLine) }));
  const chosen = options.findIndex((o) => linesKey(o.lines) === linesKey(lines));
  const missingAccount = lines.some((l) => !l.tk);
  /* V11: công nợ đang mở của đối tượng đứng trước "TK hay gặp" */
  const accOpts = (r.account_options || []).map((o) => ({ kind: 'tk', value: o.account, note: 'công nợ đang mở' + (o.count ? ' · ' + o.count + ' chứng từ' : '') }));
  const sugg = accOpts.concat((r.suggest_accounts || []).filter((v) => !accOpts.some((o) => o.value === v)).map((v) => ({ kind: 'tk', value: v })));
  const nameOpts = (r.name_options || []).filter((o) => o && o.code);
  const party = r.fields && r.fields.counterparty ? r.fields.counterparty : '';
  return {
    id: r.id, date: vnDate(r.business_date), iso: r.business_date, dir, amt: Math.abs(r.amount_minor), desc: r.source_description || '',
    party: r.source_counterparty_name || '', level, status, exported: r.state === 'EXPORTED', lines, orig: linesKey(lines), dirty: false,
    why: r.why || '', basis: r.basis || [], options: options.length >= 2 ? options : null, chosen,
    suggest: missingAccount && sugg.length ? sugg : null,
    sgTitle: accOpts.length ? 'TK đối ứng gợi ý:' : 'TK hay gặp cho ' + ({ thu: 'thu tiền:', chi: 'chi tiền:', mua: 'hóa đơn mua vào:', ban: 'hóa đơn bán ra:' })[dir],
    inv: !!inv,
    junskyNo: r.junsky_voucher || '', skipReason: r.reason || '', cashMissing: (r.constraints || []).some((c) => c.indexOf('CASH_ACCOUNT_MAPPING') === 0),
    reference: r.source_reference || '',
    nameOpts: !party && nameOpts.length ? nameOpts : (nameOpts.length > 1 ? nameOpts : null), conflict: r.identifier_conflict || null,
    group: r.group || null, stats: r.stats || null, aiNote: r.ai_note || '', aiDraft: r.ai_note || '', aiOpen: !!r.ai_note
  };
}

/* =====================================================================
   4. TRẠNG THÁI
   ===================================================================== */
let S = {
  screen: 'dk', phase: 'boot', progress: { done: 0, total: 0 }, procLabel: '', txns: [], runId: null, run: null,
  open: null, cursor: null, basisOpen: null, fLevel: 'all', fStatus: 'all', fDir: 'all', q: '',
  drawer: null, modal: null, skipId: null, skipReason: '', exportDone: false, exportResult: null, exporting: false, toast: null,
  kbQ: '', kb: null, overview: null, recent: [], history: [], historyFolder: '', error: null, dragOver: false,
  mocDraft: '', objDraft: '', debtDraft: '', srcLoading: false, mapForm: null, saving: false,
  score: null, scoring: false, aiResult: null, cfo: null, cfoBusy: null, invMonths: null
};
const timers = {};
const pending = new Map(); /* id → trạng thái đang chờ máy chủ xác nhận */
let lastScreen = S.screen;
let lastFile = null;
function set(patch) { S = Object.assign({}, S, typeof patch === 'function' ? patch(S) : patch); render(); }
function focusLater(id) { setTimeout(() => { const el = document.getElementById(id); if (el) el.focus(); }, 0); }
function toast(text, undo, extra) {
  const k = Date.now() + Math.random();
  set(Object.assign({}, extra || {}, { toast: { k, text, undo: undo || null } }));
  clearTimeout(timers.toast);
  timers.toast = setTimeout(() => { if (S.toast && S.toast.k === k) set({ toast: null }); }, undo ? 6000 : 4500);
}
function applyRows(data, extra) {
  if (data && data.debt_accounts) DEBT = data.debt_accounts;
  const local = new Map(S.txns.map((t) => [t.id, t]));
  const txns = (data.rows || []).map((r) => {
    const t = toTxn(r); const old = local.get(t.id);
    if (pending.has(t.id)) t.status = pending.get(t.id).status;
    else if (old && old.dirty && old.status === 'cho' && t.status === 'cho') { t.lines = old.lines; t.dirty = true; t.chosen = old.chosen; }
    if (old && old.aiNote === t.aiNote) { t.aiDraft = old.aiDraft; t.aiOpen = old.aiOpen; }
    if (old && old.dirty && old.nameOpts === null && t.status === 'cho') t.nameOpts = null;
    return t;
  });
  txns.sort((a, b) => (a.iso < b.iso ? -1 : a.iso > b.iso ? 1 : (a.reference < b.reference ? -1 : a.reference > b.reference ? 1 : 0)));
  const run = data.run || S.run;
  if (data.run_id) store.set('ktt-last-run', data.run_id);
  set(Object.assign({ txns, runId: data.run_id || S.runId, run, phase: 'loaded', error: null }, extra || {}));
}

/* =====================================================================
   5. QUY TẮC NGHIỆP VỤ TRÊN GIAO DIỆN
   ===================================================================== */
function check(lines, t) {
  let n = 0, c = 0; const miss = [];
  lines.forEach((l) => { if (l.side === 'N') n += l.amt || 0; else c += l.amt || 0; });
  if (t && t.cashMissing && lines.some((l) => !l.tk)) miss.push('TK tiền (chưa khai TK kế toán cho tài khoản ngân hàng)');
  else if (lines.some((l) => !l.tk)) miss.push('tài khoản đối ứng');
  lines.forEach((l) => { if (l.tk && isDebt(l.tk) && !l.dt) { const m = 'đối tượng cho TK ' + l.tk; if (miss.indexOf(m) < 0) miss.push(m); } });
  const bal = n === c && n > 0;
  if (t && !t.inv && bal && n !== t.amt && !lines.some((l) => l.tk && l.tk.indexOf('112') === 0 && l.amt === t.amt)) miss.push('dòng TK tiền đúng số tiền sao kê');
  if (t && t.inv && bal && n !== t.amt) miss.push('tổng Nợ = tổng tiền hóa đơn');
  return { miss, bal, n, c, ok: miss.length === 0 && bal };
}
function reasonText(ck) {
  const parts = [];
  if (ck.miss.length) parts.push('Thiếu: ' + ck.miss.join(' · '));
  if (!ck.bal) parts.push(ck.n === 0 && ck.c === 0 ? 'Chưa có số tiền' : 'Nợ ≠ Có (lệch ' + fmt(ck.n - ck.c) + ' VND)');
  return parts.join(' — ');
}
function entrySum(lines) {
  const uniq = (a) => a.filter((v, i) => a.indexOf(v) === i);
  const d = uniq(lines.filter((l) => l.side === 'N').map((l) => l.tk || '?'));
  const c = uniq(lines.filter((l) => l.side === 'C').map((l) => l.tk || '?'));
  return 'Nợ ' + d.join(' + ') + ' / Có ' + c.join(' + ');
}
const DIR_WORD = { thu: 'Thu', chi: 'Chi', mua: 'Mua vào', ban: 'Bán ra' };
const DIR_SIGN = { thu: '+', chi: '−', mua: '', ban: '' };
function objText(t) { const l = t.lines.find((x) => x.dt && x.tk && x.tk.indexOf('112') !== 0) || t.lines.find((x) => x.dt); return l ? lbl('dt', l.dt) : ''; }
function visible(s) {
  const q = norm(s.q).trim(); const qd = s.q.replace(/\D/g, '');
  return s.txns.filter((t) => (s.fLevel === 'all' || t.level === s.fLevel)
    && (s.fStatus === 'all' || t.status === s.fStatus)
    && (s.fDir === 'all' || t.dir === s.fDir)
    && (!q || norm(t.desc + ' ' + objText(t) + ' ' + t.party).indexOf(q) >= 0 || (qd.length >= 3 && String(t.amt).indexOf(qd) >= 0)));
}
function nextPending(s, fromId) {
  const vis = visible(s).map((t) => t.id); const order = s.txns.map((t) => t.id); const start = order.indexOf(fromId);
  for (let k = 1; k <= order.length; k++) {
    const id = order[(start + k) % order.length]; const t = s.txns.find((x) => x.id === id);
    if (t.status === 'cho' && vis.indexOf(id) >= 0) return id;
  }
  return null;
}
const bulkList = (s) => visible(s).filter((t) => t.level === 'xanh' && t.status === 'cho' && !t.dirty && check(t.lines, t).ok);
const findTxn = (id) => S.txns.find((x) => x.id === id);
const exportable = (s) => s.txns.filter((t) => t.status === 'dongy' && !t.exported);

/* =====================================================================
   6. HÀNH ĐỘNG (gọi lõi)
   ===================================================================== */
/* Quyết định gửi lần lượt theo đúng thứ tự bấm (Đồng ý rồi Hoàn tác không bao giờ đảo thứ tự). */
let decideChain = Promise.resolve();
function decide(items) {
  const runId = S.runId;
  const run = () => api('/api/that/quick/decide', { json: { run_id: runId, items, actor: ACTOR } }).then((res) => {
    /* Kết quả về muộn của một lần làm khác (Anh đã mở file khác) thì bỏ qua. */
    if (runId !== S.runId) { const err = new Error('Đã chuyển sang lần làm khác.'); err.code = 'STALE'; err.stale = true; throw err; }
    return S.phase === 'loaded' ? res : null; /* đang đề xuất lại: danh sách mới sẽ tự nạp */
  });
  const p = decideChain.then(run, run);
  decideChain = p.catch(() => null);
  return p;
}
let pendingSeq = 0;
function markPending(ids, status) { const token = ++pendingSeq; ids.forEach((id) => pending.set(id, { status, token })); return token; }
function clearPending(ids, token) { ids.forEach((id) => { const v = pending.get(id); if (v && (token === undefined || v.token === token)) pending.delete(id); }); }
const applyIf = (res, extra) => { if (res) applyRows(res, extra); };

async function startUpload(file) {
  if (!file) return;
  if (!/\.(xlsx|xls)$/i.test(file.name)) { toast('Vùng thả file nhận sao kê Excel (.xlsx, .xls). Hóa đơn XML: chọn tháng ở khung “Hóa đơn theo tháng”.'); set({ dragOver: false }); return; }
  lastFile = file;
  clearInterval(timers.load);
  set({ phase: 'processing', progress: { done: 0, total: 0 }, procLabel: file.name, screen: 'dk', dragOver: false, open: null, modal: null, error: null });
  try {
    const job = await api('/api/that/quick/upload', { method: 'POST', body: file, headers: { 'X-Quick-Info': encodeURIComponent(JSON.stringify({ name: file.name, relative_path: file.name })) } });
    const result = await waitJob(job.job_id, (p) => set({ progress: p }));
    if (result.state !== 'READY') throw Object.assign(new Error(result.message || 'Chưa đọc được tệp này.'), { code: 'REJECTED' });
    pending.clear();
    applyRows(result, { open: null, cursor: null, fLevel: 'all', fStatus: 'all', fDir: 'all', q: '' });
    if (result.reused) toast('Tệp này đã làm trước đó — mở lại kết quả cũ, giữ nguyên các quyết định đã có.');
    loadRecent();
  } catch (e) { showError(e); }
}
function showError(e) {
  const code = e.code || '';
  let title = 'Chưa đề xuất được bút toán', cause = e.message || 'Có lỗi khi xử lý tệp.', todo = 'Kiểm tra lại tệp rồi bấm Thử lại.';
  if (code === 'NO_CATALOG') { title = 'Chưa có danh mục đối tượng'; todo = 'Nạp danh mục ở màn hình Nguồn dữ liệu, rồi quay lại bấm Thử lại. File vẫn được giữ, không cần thả lại.'; }
  else if (code === 'NO_NEW_RECORDS') { title = 'Tệp này đã làm trước đó'; todo = 'Mở lại lần làm cũ ở mục “Đã làm gần đây” bên dưới vùng thả file.'; }
  else if (code === 'INVOICE_MONTH_EMPTY') { title = 'Không thấy hóa đơn của tháng này'; todo = 'Kiểm tra thư mục tải hóa đơn (Nguồn dữ liệu → Hóa đơn) có thư mục tháng với mua_vao / ban_ra chứa file XML.'; }
  else if (code === 'REJECTED') { title = 'Chưa đọc được tệp'; todo = 'Kiểm tra đúng file sao kê Excel (.xlsx/.xls) xuất từ ngân hàng rồi thả lại.'; }
  else if (code === 'SESSION_TOKEN') { title = 'Phiên giao diện đã đổi'; todo = 'Tải lại trang (phím F5) rồi thử lại.'; }
  set({ phase: 'error', error: { title, cause, todo, code } });
}
async function openRun(runId) {
  if (!runId) return;
  set({ phase: 'processing', progress: { done: 0, total: 0 }, procLabel: 'Đang mở lần làm trước…', screen: 'dk' });
  try { pending.clear(); const data = await api('/api/that/quick?run_id=' + encodeURIComponent(runId)); applyRows(data, { open: null, cursor: null }); }
  catch (e) { showError(e); }
}
async function repropose() {
  if (!S.runId) return;
  set({ phase: 'processing', progress: { done: 0, total: 0 }, procLabel: 'Đề xuất lại các giao dịch đang chờ' });
  try {
    const job = await api('/api/that/quick/repropose', { json: { run_id: S.runId } });
    const result = await waitJob(job.job_id, (p) => set({ progress: p }));
    applyRows(result); toast('Đã đề xuất lại các giao dịch đang chờ duyệt. Giao dịch đã quyết định giữ nguyên.');
  } catch (e) { showError(e); }
}
async function approve(id) {
  const t = findTxn(id); if (!t || t.status !== 'cho') return;
  const ck = check(t.lines, t);
  if (!ck.ok) { toast('Chưa đồng ý được: ' + reasonText(ck), null, { open: id, cursor: id }); return; }
  const txns = S.txns.map((x) => x.id === id ? Object.assign({}, x, { status: 'dongy' }) : x);
  const next = nextPending(Object.assign({}, S, { txns }), id);
  const token = markPending([id], 'dongy');
  toast('Đã đồng ý · ' + t.date + ' · ' + fmt(t.amt) + ' VND', { ids: [id] }, { txns, open: next, cursor: next });
  /* Gửi đúng bút toán đang hiện trên màn hình: máy chủ duyệt đúng cái Anh đã thấy. */
  const item = { id, action: 'APPROVE', remember: true, lines: t.lines.map(toServerLine) };
  try {
    const res = await decide([item]); clearPending([id], token); applyIf(res);
    if (res && res.refreshed) toast('Đã đồng ý · đã áp dụng cho ' + res.refreshed + ' giao dịch đang chờ cùng STK/tên đối ứng', { ids: [id] });
  } catch (e) {
    clearPending([id], token);
    if (e.stale) return;
    set((s) => ({ txns: s.txns.map((x) => x.id === id ? Object.assign({}, x, { status: 'cho' }) : x), open: id, cursor: id }));
    toast('Chưa đồng ý được: ' + e.message);
  }
}
function edit(id) {
  const t = findTxn(id); if (!t || t.status === 'junsky' || t.exported) return;
  set({ drawer: { id, lines: clone(t.lines), remember: true, combo: null, q: '' }, cursor: id });
  focusLater('drawer-close');
}
function skip(id) {
  const t = findTxn(id); if (!t || t.status !== 'cho') return;
  set({ modal: 'skip', skipId: id, skipReason: '', cursor: id });
  focusLater('ly-do');
}
async function confirmSkip() {
  const id = S.skipId; const t = findTxn(id); if (!t) return;
  const reason = S.skipReason.trim();
  const txns = S.txns.map((x) => x.id === id ? Object.assign({}, x, { status: 'boqua', skipReason: reason }) : x);
  const next = nextPending(Object.assign({}, S, { txns }), id);
  if (t.status !== 'cho') { set({ modal: null }); return; }
  const token = markPending([id], 'boqua');
  toast('Đã bỏ qua · ' + t.date + ' · ' + fmt(t.amt) + ' VND', { ids: [id] }, { txns, modal: null, open: next, cursor: next });
  try { const res = await decide([{ id, action: 'SKIP', reason }]); clearPending([id], token); applyIf(res); }
  catch (e) { clearPending([id], token); if (e.stale) return; set((s) => ({ txns: s.txns.map((x) => x.id === id ? Object.assign({}, x, { status: 'cho' }) : x) })); toast('Chưa bỏ qua được: ' + e.message); }
}
async function reopen(ids, quiet) {
  const list = [].concat(ids);
  const token = markPending(list, 'cho');
  set((s) => ({ txns: s.txns.map((x) => list.indexOf(x.id) >= 0 ? Object.assign({}, x, { status: 'cho', skipReason: '' }) : x), open: list[0], cursor: list[0], toast: null }));
  try { const res = await decide(list.map((id) => ({ id, action: 'REOPEN' }))); clearPending(list, token); applyIf(res); if (!quiet) toast('Đã mở lại để duyệt lại.'); }
  catch (e) { clearPending(list, token); if (e.stale) return; toast('Chưa mở lại được: ' + e.message); openRun(S.runId); }
}
async function clearExisting(id) {
  try { const res = await decide([{ id, action: 'CLEAR_EXISTING' }]); applyIf(res, { open: id, cursor: id }); toast('Đã bỏ đánh dấu “có trong Junsky”. Giao dịch chuyển về Chờ duyệt.'); }
  catch (e) { if (!e.stale) toast('Chưa đổi được: ' + e.message); }
}
function useOption(id, i) { set((s) => ({ txns: s.txns.map((x) => x.id === id ? Object.assign({}, x, { chosen: i, lines: clone(x.options[i].lines), dirty: linesKey(x.options[i].lines) !== x.orig }) : x) })); }
function pickSuggest(id, i) {
  set((s) => ({ txns: s.txns.map((x) => {
    if (x.id !== id || !x.suggest) return x;
    const g = x.suggest[i]; const lines = clone(x.lines); let done = false;
    lines.forEach((l) => {
      if (done) return;
      if (g.kind === 'tk' && !l.tk && !(x.cashMissing && l.side === (x.dir === 'thu' ? 'N' : 'C'))) { l.tk = g.value; done = true; }
      if (g.kind === 'dt' && l.tk && isDebt(l.tk) && !l.dt) { l.dt = g.value; done = true; }
    });
    return Object.assign({}, x, { lines, dirty: linesKey(lines) !== x.orig });
  }) }));
}
function pickName(id, code) {
  set((s) => ({ txns: s.txns.map((x) => {
    if (x.id !== id) return x;
    const lines = clone(x.lines);
    lines.forEach((l) => { if (!l.tk || l.tk.indexOf('112') !== 0) l.dt = code; });
    return Object.assign({}, x, { lines, dirty: linesKey(lines) !== x.orig, nameOpts: null });
  }) }));
}
async function saveAiNote(id) {
  const t = findTxn(id); if (!t) return;
  try {
    const res = await api('/api/that/quick/ai-note', { json: { run_id: S.runId, id, note: t.aiDraft || '', actor: ACTOR } });
    set((s) => ({ txns: s.txns.map((x) => x.id === id ? Object.assign({}, x, { aiNote: res.ai_note || '', aiDraft: res.ai_note || '' }) : x) }));
    toast(res.ai_note ? 'Đã lưu ghi chú cho AI' : 'Đã xóa ghi chú');
  } catch (e) { toast('Không lưu được ghi chú: ' + e.message); }
}
async function sendAiContext(id) {
  const t = findTxn(id);
  if (t && (t.aiDraft || '') !== (t.aiNote || '')) await saveAiNote(id);
  try {
    const res = await api('/api/that/quick/ai-context', { json: { run_id: S.runId, ids: id ? [id] : null } });
    set({ modal: 'ai', aiResult: res }); focusLater('modal-cancel');
  } catch (e) { toast('Chưa tạo được gói ngữ cảnh: ' + e.message); }
}
async function runScore() {
  if (!S.runId) return;
  set({ scoring: true });
  try { const res = await api('/api/that/quick/score', { json: { run_id: S.runId } }); set({ modal: 'score', score: res, scoring: false }); focusLater('modal-cancel'); }
  catch (e) { set({ scoring: false }); toast('Chưa chấm được: ' + e.message); }
}
async function toggleScoring(on) {
  try { await api('/api/that/learning-settings', { json: { scoring_mode: !!on } }); await loadOverview(); toast(on ? 'Đã bật chế độ chấm điểm. Bấm “Đề xuất lại” ở màn Định khoản để tính lại.' : 'Đã tắt chế độ chấm điểm. Bấm “Đề xuất lại” để đánh dấu lại các dòng đã có trong Junsky.'); }
  catch (e) { toast('Không đổi được chế độ: ' + e.message); }
}
async function confirmBulk() {
  const ids = bulkList(S).map((t) => t.id);
  if (!ids.length) { set({ modal: null }); return; }
  const txns = S.txns.map((x) => ids.indexOf(x.id) >= 0 ? Object.assign({}, x, { status: 'dongy' }) : x);
  const lineMap = new Map(S.txns.map((x) => [x.id, x.lines]));
  const token = markPending(ids, 'dongy');
  toast('Đã đồng ý ' + ids.length + ' giao dịch Xanh', { ids }, { txns, modal: null, open: null });
  try { const res = await decide(ids.map((id) => ({ id, action: 'APPROVE', remember: true, lines: lineMap.get(id).map(toServerLine) }))); clearPending(ids, token); applyIf(res); }
  catch (e) { clearPending(ids, token); if (e.stale) return; toast('Chưa đồng ý hàng loạt được: ' + e.message); openRun(S.runId); }
}
async function doExport() {
  const n = exportable(S).length; if (!n || S.exporting) return;
  set({ exporting: true });
  try {
    const res = await api('/api/that/quick/export', { json: { run_id: S.runId, junsky_files: false, actor: ACTOR } });
    set({ exporting: false, exportDone: true, exportResult: res });
    const data = await api('/api/that/quick?run_id=' + encodeURIComponent(S.runId)); applyRows(data);
    loadHistory(); loadRecent();
  } catch (e) { set({ exporting: false }); toast('Chưa xuất được: ' + e.message); }
}
async function openExport(runId, file) {
  try {
    const res = await api('/api/that/open', { json: { run_id: runId, file: file || '' } });
    toast(res.opened ? ('Đã mở ' + (file ? 'file ' + file : 'thư mục xuất file')) : ('Mở bằng tay tại: ' + res.path));
  } catch (e) { toast('Chưa mở được: ' + e.message); }
}
async function downloadExport(runId, file) {
  try {
    const res = await fetch('/api/that/quick/' + encodeURIComponent(runId) + '/download?file=' + encodeURIComponent(file), { headers: { 'X-KTT-Token': TOKEN } });
    if (!res.ok) throw new Error('Không tải được file.');
    const blob = await res.blob(); const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = file; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  } catch (e) { toast(e.message); }
}
async function reloadSrc() {
  if (S.srcLoading) return;
  set({ srcLoading: true });
  try {
    const job = await api('/api/that/reload', { json: {} });
    await waitJob(job.job_id);
    await Promise.all([loadOverview(), loadCatalogData()]);
    set({ srcLoading: false }); toast('Đã nạp lại dữ liệu nền từ Junsky');
  } catch (e) { set({ srcLoading: false }); await loadOverview(); toast('Chưa nạp lại được: ' + e.message); }
}
async function applyMoc() {
  const raw = S.mocDraft.trim(); const objRaw = S.objDraft.trim();
  const iso = raw ? isoFromVn(raw) : '';
  const objIso = objRaw ? isoFromVn(objRaw) : null;
  if (iso === null || (objRaw && !objIso)) { toast('Ngày chưa đúng dạng dd/mm/yyyy'); return; }
  const payload = { learning_cutoff: iso };
  if (objIso) payload.object_learning_from = objIso;
  try {
    await api('/api/that/learning-settings', { json: payload }); await loadOverview();
    toast(iso ? 'Đã đổi mốc học: máy học từ sổ đến ' + raw + '. Bấm “Đề xuất lại” ở màn Định khoản để áp dụng cho giao dịch đang chờ.' : 'Máy học từ toàn bộ sổ (đến ngày của từng giao dịch).');
  } catch (e) { toast('Chưa đổi được: ' + e.message); }
}
async function applyDebt() {
  const list = S.debtDraft.split(/[\s,;]+/).map((v) => v.trim()).filter(Boolean);
  if (!list.length || list.some((v) => !/^\d{3,10}$/.test(v))) { toast('Nhập các số tài khoản, cách nhau bằng dấu phẩy (ví dụ 131, 331, 141)'); return; }
  try { await api('/api/that/learning-settings', { json: { debt_accounts: list } }); await loadOverview(); if (S.runId) openRun(S.runId); toast('Đã cập nhật danh sách TK công nợ cần đối tượng'); }
  catch (e) { toast('Chưa lưu được: ' + e.message); }
}
async function saveMapping() {
  const f = S.mapForm || {}; const acct = String(f.acct || '').replace(/[\s.\-]/g, '');
  if (!/^\d{6,}$/.test(acct)) { toast('Số tài khoản ngân hàng cần ít nhất 6 chữ số'); return; }
  if (!f.gl) { toast('Chọn TK kế toán (TK 112 chi tiết)'); return; }
  try { await api('/api/that/cash-mapping', { json: { bank_account: acct, cash_account: f.gl } }); set({ mapForm: null }); await loadOverview(); toast('Đã lưu: tài khoản ngân hàng ' + mask(acct) + ' → TK ' + f.gl + '. Bấm “Đề xuất lại” để áp dụng.'); }
  catch (e) { toast('Chưa lưu được: ' + e.message); }
}
async function deleteMapping(acct) {
  try { await api('/api/that/cash-mapping', { json: { bank_account: acct, cash_account: '' } }); await loadOverview(); toast('Đã xóa ánh xạ ' + mask(acct)); }
  catch (e) { toast('Chưa xóa được: ' + e.message); }
}
/* ngăn Sửa */
function dUpd(fn) {
  if (!S.drawer) return;
  const d = Object.assign({}, S.drawer, { lines: clone(S.drawer.lines) });
  fn(d); set({ drawer: d });
}
function dSet(li, key, val, close) { dUpd((d) => { if (d.lines[li]) d.lines[li][key] = val; if (close) d.combo = null; }); }
function comboActive(li, key) { const d = S.drawer; return !!(d && d.combo && d.combo.li === li && d.combo.key === key); }
function openCombo(li, key) { if (!comboActive(li, key)) dUpd((d) => { d.combo = { li, key }; d.q = ''; }); }
async function saveDrawer() {
  const d = S.drawer; if (!d || S.saving) return;
  const t = findTxn(d.id);
  const ck = check(d.lines, t);
  if (!ck.ok) { toast('Chưa lưu được: ' + reasonText(ck)); return; }
  set({ saving: true });
  try {
    const res = await decide([{ id: d.id, action: 'APPROVE', lines: d.lines.map(toServerLine), remember: !!d.remember }]);
    const txns = S.txns.map((x) => x.id === d.id ? Object.assign({}, x, { status: 'dongy' }) : x);
    const next = nextPending(Object.assign({}, S, { txns }), d.id);
    set({ saving: false, drawer: null });
    applyIf(res, { open: next, cursor: next });
    toast('Đã lưu và đồng ý · ' + t.date + ' · ' + fmt(t.amt) + ' VND' + (d.remember ? ' · đã ghi nhớ cho lần sau' : '') + (res && res.refreshed ? ' · áp dụng cho ' + res.refreshed + ' giao dịch đang chờ' : ''), { ids: [d.id] });
  } catch (e) { set({ saving: false }); if (!e.stale) toast('Chưa lưu được: ' + e.message); }
}

/* nạp dữ liệu */
async function loadOverview() { try { const o = await api('/api/that/overview'); set({ overview: o, mocDraft: S.mocDraft || (o.learning_cutoff ? vnDate(o.learning_cutoff) : ''), objDraft: S.objDraft || vnDate(o.object_learning_from || ''), debtDraft: S.debtDraft || (o.debt_accounts || []).join(', ') }); if (o.debt_accounts) DEBT = o.debt_accounts; return o; } catch (e) { return null; } }
async function loadCatalogData() { try { const d = new Date(); const iso = d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate()); loadCatalog(await api('/api/that/catalog?date=' + iso + '&cutoff=' + encodeURIComponent(new Date().toISOString()))); } catch (e) { /* danh mục trống: ô chọn sẽ báo không tìm thấy */ } }
async function loadInvoiceMonths() { try { set({ invMonths: await api('/api/that/invoice-months') }); } catch (e) { set({ invMonths: null }); } }
async function startInvoiceMonth(month) {
  if (!month) return;
  lastFile = null;
  clearInterval(timers.load);
  set({ phase: 'processing', progress: { done: 0, total: 0 }, procLabel: 'Hóa đơn tháng ' + month.slice(5) + '/' + month.slice(0, 4), screen: 'dk', dragOver: false, open: null, modal: null, error: null });
  try {
    const job = await api('/api/that/quick/invoice-month', { json: { month } });
    const result = await waitJob(job.job_id, (p) => set({ progress: p }));
    if (result.state !== 'READY') throw Object.assign(new Error(result.message || 'Chưa đọc được hóa đơn tháng này.'), { code: 'REJECTED' });
    pending.clear();
    applyRows(result, { open: null, cursor: null, fLevel: 'all', fStatus: 'all', fDir: 'all', q: '' });
    if (result.reused) toast('Tháng này đã làm trước đó — mở lại kết quả cũ, giữ nguyên các quyết định đã có.');
    loadRecent();
  } catch (e) { showError(e); }
}
async function loadRecent() { try { const r = await api('/api/that/runs'); set({ recent: r.rows || [] }); return r.rows || []; } catch (e) { return []; } }
async function loadHistory() { try { const h = await api('/api/that/history'); set({ history: h.rows || [], historyFolder: h.folder_display || '' }); } catch (e) { /* bỏ qua */ } }
async function loadCfo() { try { set({ cfo: await api('/api/that/cfo-rules') }); } catch (e) { set({ cfo: { rules: [], error: e.message } }); } }
async function toggleCfo(code, on) {
  if (S.cfoBusy) return;
  set({ cfoBusy: code });
  try { const r = await api('/api/that/cfo-rules/toggle', { json: { ma: code, bat: !!on } }); set({ cfo: r, cfoBusy: null }); toast((on ? 'Đã bật lại ' : 'Đã tắt ') + code + '. Bấm “Đề xuất lại” ở màn Định khoản để áp dụng cho giao dịch đang chờ.'); }
  catch (e) { set({ cfoBusy: null }); toast('Chưa đổi được: ' + e.message); }
}
async function loadKb() { const q = S.kbQ; try { const r = await api('/api/that/knowledge-cards?q=' + encodeURIComponent(q)); if (q === S.kbQ) set({ kb: r }); } catch (e) { set({ kb: { cards: [], total: 0, error: e.message } }); } }
async function boot() {
  await Promise.all([loadOverview(), loadCatalogData(), loadHistory(), loadInvoiceMonths()]);
  const runs = await loadRecent();
  const last = store.get('ktt-last-run');
  /* Chỉ tự mở lại lần làm dở của chính trình duyệt này; lần đầu luôn bắt đầu ở vùng thả file. */
  const target = runs.find((r) => r.id === last && (r.waiting || r.approved));
  if (target) openRun(target.id); else set({ phase: 'empty' });
  pollBootstrap();
}
async function pollBootstrap() {
  const o = S.overview;
  if (o && o.bootstrap_job && o.bootstrap_job.state === 'RUNNING') {
    await sleep(1500); const before = o.catalog_counts && o.catalog_counts.COUNTERPARTY; await loadOverview();
    const after = S.overview && S.overview.catalog_counts && S.overview.catalog_counts.COUNTERPARTY;
    if (after !== before || (S.overview.bootstrap_job && S.overview.bootstrap_job.state !== 'RUNNING')) loadCatalogData();
    pollBootstrap();
  }
}

const ACT = {
  nav: (d) => { set({ screen: d.screen }); if (d.screen === 'tracuu' && !S.kb) loadKb(); if (d.screen === 'lichsu') loadHistory(); if (d.screen === 'nguon') loadOverview(); if (d.screen === 'cfo') loadCfo(); },
  'cfo-toggle': (d) => toggleCfo(d.code, d.on === '1'),
  'start-load': () => { const input = document.getElementById('file-input'); if (input) { input.value = ''; input.click(); } },
  'retry': () => { if (S.error && S.error.code === 'NO_NEW_RECORDS') { set({ phase: 'empty', error: null }); return; } if (lastFile) startUpload(lastFile); else { set({ phase: 'empty', error: null }); loadInvoiceMonths(); } },
  'open-run': (d) => openRun(d.run),
  'invoice-month': (d) => startInvoiceMonth(d.month),
  'reset-file': () => { set({ phase: 'empty', open: null, cursor: null }); loadRecent(); loadInvoiceMonths(); },
  'repropose': repropose,
  'go-nguon': () => { set({ screen: 'nguon' }); loadOverview(); },
  tile: (d) => set((s) => ({ fLevel: s.fLevel === d.level ? 'all' : d.level })),
  pill: (d) => set({ [d.key]: d.val }),
  'clear-filters': () => set({ fLevel: 'all', fStatus: 'all', fDir: 'all', q: '' }),
  'open-bulk': () => { if (bulkList(S).length) { set({ modal: 'bulk' }); focusLater('modal-cancel'); } else toast('Không có giao dịch Xanh nào đủ điều kiện trong danh sách đang lọc'); },
  'confirm-bulk': confirmBulk,
  'open-export': () => { set({ modal: 'export', exportDone: false, exportResult: null }); focusLater('modal-cancel'); },
  'do-export': doExport,
  'open-folder': () => openExport(S.runId),
  'download-file': (d) => downloadExport(d.run || S.runId, d.file),
  'close-modal': () => set({ modal: null }),
  toggle: (d) => { const id = d.id; set((s) => ({ cursor: id, open: s.open === id ? null : id })); },
  approve: (d) => approve(d.id),
  edit: (d) => edit(d.id),
  skip: (d) => skip(d.id),
  reopen: (d) => reopen(d.id),
  'clear-existing': (d) => clearExisting(d.id),
  basis: (d) => { const id = d.id; set((s) => ({ basisOpen: s.basisOpen === id ? null : id })); },
  'use-option': (d) => useOption(d.id, +d.i),
  suggest: (d) => pickSuggest(d.id, +d.i),
  'confirm-skip': confirmSkip,
  'close-drawer': () => set({ drawer: null }),
  'add-line': () => dUpd((d) => { d.lines.push({ side: 'N', tk: '', amt: 0, dt: '', da: '', km: '', cp: '' }); d.combo = null; }),
  'remove-line': (x) => dUpd((d) => { d.lines.splice(+x.li, 1); d.combo = null; }),
  side: (x) => dSet(+x.li, 'side', x.side),
  'clear-field': (x) => dSet(+x.li, x.key, ''),
  'save-drawer': saveDrawer,
  undo: () => { const t = S.toast; if (t && t.undo && t.undo.ids) reopen(t.undo.ids, true); },
  'close-toast': () => set({ toast: null }),
  'reload-src': reloadSrc,
  'apply-moc': applyMoc,
  'apply-debt': applyDebt,
  'add-bank': () => set({ mapForm: { acct: '', gl: (CAT.tk.find((r) => /^112\d+/.test(r[0])) || [''])[0] } }),
  'cancel-bank': () => set({ mapForm: null }),
  'save-bank': saveMapping,
  'delete-bank': (x) => deleteMapping(x.acct),
  'open-file': (x) => openExport(x.run, x.file),
  'hist-folder': (x) => openExport(x.run),
  'pick-name': (x) => pickName(x.id, x.code),
  'ai-toggle': (x) => { const id = x.id; set((s) => ({ txns: s.txns.map((t) => t.id === id ? Object.assign({}, t, { aiOpen: !t.aiOpen }) : t) })); focusLater('ai-' + id); },
  'ai-save': (x) => saveAiNote(x.id),
  'ai-send': (x) => sendAiContext(x.id),
  'ai-send-all': () => sendAiContext(null),
  'score': runScore,
  'open-score-file': () => { const r = S.score || {}; if (r.file) openExport(S.runId, r.file); },
  'download-score-file': () => { const r = S.score || {}; if (r.file) downloadExport(S.runId, r.file); },
  'open-ai-folder': () => { api('/api/that/open', { json: { ai_folder: true } }).then((r) => { if (!r.opened) toast('Thư mục: ' + r.path); }).catch((e) => toast('Không mở được thư mục: ' + e.message)); }
};

/* =====================================================================
   7. GIAO DIỆN (HTML dựng từ trạng thái)
   ===================================================================== */
function kindTag(o) {
  if (!o) return '<span class="tag-kho">KHO THẬT</span>';
  const label = String(o.data_label || '');
  /* V13: engine lưu trữ — SQLite (mặc định) hoặc PostgreSQL (kho thử) */
  const engine = o.storage_engine === 'postgres' ? ' · PostgreSQL' : '';
  return label === 'plhn-that' ? `<span class="tag-kho">KHO THẬT${engine}</span>` : `<span class="tag-kho tag-thu" title="${esc(label)}${o.storage_schema ? ' · schema ' + esc(o.storage_schema) : ''}">KHO THỬ${engine}</span>`;
}
function viewTopbar(s) {
  const o = s.overview;
  const running = o && o.bootstrap_job && o.bootstrap_job.state === 'RUNNING';
  const ledger = o && o.ledger_to ? vnDate(o.ledger_to) : '—';
  const moc = o ? (o.learning_cutoff ? vnDate(o.learning_cutoff) : 'hết sổ') : '—';
  return `<header class="topbar">
    <div class="brand"><span class="logo">${icon('book', 18)}</span><span class="brand-name">Kho tri thức kế toán</span>${kindTag(o)}</div>
    <span class="topbar-note">${icon('shield', 15)}Không tự nhập Junsky — chỉ tạo file</span>
    <div class="topbar-status">${running ? '<span class="busy">Đang nạp dữ liệu nền từ Junsky…</span><span aria-hidden="true">·</span>' : ''}<span>Sổ Junsky đến <strong>${esc(ledger)}</strong></span><span aria-hidden="true">·</span><span>Máy học đến <strong>${esc(moc)}</strong></span></div>
  </header>`;
}
function viewNav(s) {
  const items = [['dk', 'Định khoản'], ['nguon', 'Nguồn dữ liệu'], ['tracuu', 'Tra cứu tri thức'], ['cfo', 'Tri thức CFO'], ['lichsu', 'Lịch sử xuất file']];
  return `<nav class="nav" aria-label="Menu chính">
    ${items.map((n, i) => `<button type="button" class="nav-item" data-act="nav" data-screen="${n[0]}" aria-current="${s.screen === n[0] ? 'page' : 'false'}"><span class="nav-num">${i + 1}</span><span>${n[1]}</span></button>`).join('')}
    <div class="nav-foot"><span>Chạy trên máy này · không gửi dữ liệu ra ngoài</span><span>Phiên bản V12</span></div>
  </nav>`;
}
function viewFileRow(s) {
  const info = (s.run && s.run.source_info) || {};
  const rawName = (s.run && s.run.source_name) || s.procLabel || '';
  const name = /^Hoa don (\d{4})-(\d{2})\.zip$/.test(rawName) ? rawName.replace(/^Hoa don (\d{4})-(\d{2})\.zip$/, 'Hóa đơn tháng $2/$1 (máy tự lấy XML mua vào + bán ra)') : rawName;
  const cash = (s.txns.find((t) => t.lines.some((l) => l.tk && l.tk.indexOf('112') === 0)) || { lines: [] }).lines.find((l) => l.tk && l.tk.indexOf('112') === 0);
  const dates = s.txns.map((t) => t.iso).filter(Boolean).sort();
  const period = dates.length ? vnDate(dates[0]) + '–' + vnDate(dates[dates.length - 1]) : '';
  const bal = info.balance_ok === true ? `<span class="ok-text">${icon('checkCircle', 15, 2.4)}Số dư đầu–cuối khớp</span>` : info.balance_ok === false ? `<span class="bal-bad">${icon('xCircle', 15, 2.4)}Số dư đầu–cuối lệch — kiểm tra lại file</span>` : '';
  const invRun = isInvoiceRun(s);
  const kind = invRun ? 'Hóa đơn điện tử' : (s.run && s.run.source_kind) === 'sao_ke' || !s.run ? 'Sao kê ngân hàng' : 'Chứng từ';
  const invCounts = invRun ? s.txns.filter((t) => t.dir === 'mua').length + ' mua vào · ' + s.txns.filter((t) => t.dir === 'ban').length + ' bán ra' : '';
  return `<div class="file-row">
    <div class="card file-card">
      <span class="file-icon">${icon('file', 20)}</span>
      <div style="min-width:0;display:flex;flex-direction:column;gap:2px">
        <div class="file-meta"><span>${kind}</span>${cash ? `<span class="dot" aria-hidden="true">·</span><span>TK ${esc(cash.tk)}</span>` : ''}${period ? `<span class="dot" aria-hidden="true">·</span><span>${esc(period)}</span>` : ''}<span class="dot" aria-hidden="true">·</span><span>${invRun ? s.txns.length + ' hóa đơn (' + invCounts + ')' : s.txns.length + ' giao dịch'}</span>${bal ? `<span class="dot" aria-hidden="true">·</span>${bal}` : ''}</div>
        <span class="file-name">${esc(name)}${s.run && s.run.created_at ? ' · đề xuất lúc ' + esc(vnTime(s.run.created_at)) : ''}</span>
      </div>
    </div>
    ${s.phase === 'loaded' ? `<button type="button" class="btn btn-newfile" data-act="repropose" title="Tính lại đề xuất cho các giao dịch đang chờ (sau khi đổi mốc học, ánh xạ TK hoặc đã duyệt thêm)">${icon('refresh', 16)}Đề xuất lại</button><button type="button" class="btn btn-newfile" data-act="reset-file">${icon('upload', 16)}${invRun ? 'Chọn tháng / file khác' : 'Thả file khác'}</button>` : ''}
  </div>`;
}
function viewRecentList(s) {
  if (!s.recent.length) return '<div class="recent-empty">Chưa có lần làm nào.</div>';
  return s.recent.map((r) => {
    const period = r.first_day ? vnDate(r.first_day) + '–' + vnDate(r.last_day) : '';
    const parts = [r.count + ' giao dịch', r.approved ? r.approved + ' đã đồng ý chờ xuất' : '', r.exported ? r.exported + ' đã xuất' : '', r.waiting ? r.waiting + ' chờ duyệt' : ''].filter(Boolean).join(' · ');
    const name = r.source_kind === 'hoa_don' && /^Hoa don (\d{4})-(\d{2})\.zip$/.test(r.source_name || '') ? (r.source_name || '').replace(/^Hoa don (\d{4})-(\d{2})\.zip$/, 'Hóa đơn tháng $2/$1') : (r.source_name || 'Sao kê');
    return `<div class="recent-item">${icon('file', 20)}<div class="recent-text"><b>${esc(name)}${period ? ' · ' + esc(period) : ''}</b><span>${esc(parts)} · làm lúc ${esc(vnTime(r.created_at))}</span></div><button type="button" class="btn btn-secondary btn-sm" data-act="open-run" data-run="${esc(r.id)}">Mở lại</button></div>`;
  }).join('');
}
function viewEmpty(s) {
  return `<button type="button" class="dropzone${s.dragOver ? ' is-over' : ''}" id="dropzone" data-act="start-load">
      <span class="drop-icon">${icon('upload', 26)}</span>
      <span class="drop-title">Thả file vào đây hoặc bấm để chọn</span>
      <span class="sub" style="font-size:14px">Sao kê ngân hàng (.xlsx, .xls) — mỗi lần một file</span>
      <span style="color:var(--chu-nhat);font-size:13px">Phần mềm tự nhận loại file, không cần chọn trước. Hóa đơn: chọn tháng ở khung bên dưới.</span>
      ${s.overview && s.overview.bootstrap_job && s.overview.bootstrap_job.state === 'RUNNING' ? '<span style="color:var(--chinh);font-size:13px;font-weight:600">Đang nạp dữ liệu nền từ Junsky — vẫn có thể thả file, phần mềm sẽ chờ nạp xong rồi đề xuất.</span>' : ''}
    </button>
    ${viewInvoiceMonths(s)}
    <section class="card recent" aria-labelledby="h-recent">
      <h2 id="h-recent">Đã làm gần đây</h2>
      ${viewRecentList(s)}
    </section>`;
}
/* V12: hóa đơn theo tháng — máy tự lấy XML mua vào + bán ra trong thư mục tải hóa đơn */
function isInvoiceRun(s) { return !!(s.run && s.run.source_kind === 'hoa_don') || s.txns.some((t) => t.inv); }
function viewInvoiceMonths(s) {
  const d = s.invMonths;
  if (!d) return '';
  let body;
  if (!d.root) body = '<div class="recent-empty">Chưa khai thư mục hóa đơn. Vào Nguồn dữ liệu → mục Hóa đơn, chọn thư mục tải hóa đơn (có các thư mục tháng yyyy-mm).</div>';
  else if (!d.exists) body = '<div class="recent-empty">Không thấy thư mục hóa đơn đã khai: ' + esc(d.root) + '</div>';
  else {
    const test = d.months.filter((m) => !m.learning);
    const learn = d.months.filter((m) => m.learning);
    body = (test.length ? test.map((m) => `<div class="recent-item">${icon('file', 20)}<div class="recent-text"><b>Hóa đơn tháng ${esc(m.month.slice(5))}/${esc(m.month.slice(0, 4))}</b><span>${m.mua_vao} mua vào · ${m.ban_ra} bán ra</span></div><button type="button" class="btn btn-secondary btn-sm" data-act="invoice-month" data-month="${esc(m.month)}">Đề xuất bút toán</button></div>`).join('')
      : '<div class="recent-empty">Chưa có tháng nào sau mốc học.</div>')
      + (learn.length ? `<div class="recent-empty">${learn.length} tháng đến ${esc(learn[0].month.slice(5))}/${esc(learn[0].month.slice(0, 4))} là tháng <strong>dùng để học</strong> (mốc học ${d.learning_cutoff ? esc(vnDate(d.learning_cutoff)) : '—'}): máy đọc các hóa đơn này để biết đã hạch toán thế nào, không chạy thử.</div>` : '');
  }
  return `<section class="card recent" aria-labelledby="h-inv"><h2 id="h-inv">Hóa đơn theo tháng (mua vào + bán ra)</h2>${body}</section>`;
}
function viewProc(s) {
  const p = s.progress || {}; const total = p.total || 0; const done = p.done || 0;
  const pct = total ? Math.round(done * 100 / total) : 0;
  const ws = ['80%', '62%', '74%', '55%', '68%'];
  const title = total ? `Đang đề xuất ${done}/${total}…` : 'Đang đọc file và chuẩn bị…';
  return `<div class="card proc">
      <div class="proc-top"><span class="proc-title">${title}</span><span class="sub" style="font-size:14px">${total ? pct + '%' : ''}</span></div>
      <div class="bar" role="progressbar" aria-label="Tiến độ đề xuất" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${done}"><span style="width:${total ? pct : 4}%"></span></div>
      <span style="font-size:13px;color:var(--chu-nhat)">${esc(s.procLabel || '')} — đang so từng giao dịch với sổ Junsky, danh bạ đối tác và chứng từ cũ. Có thể chuyển sang màn hình khác trong lúc chờ.</span>
    </div>
    <div class="card skel" aria-hidden="true">${ws.map((w, i) => `<div class="skel-row" style="opacity:${1 - i * 0.18}"><span></span><span style="width:70%"></span><span style="width:${w}"></span><span></span><span style="height:18px;border-radius:999px;width:90px;background:#EEF0F3"></span><span style="background:#EEF0F3"></span></div>`).join('')}</div>`;
}
function viewError(s) {
  const e = s.error || {};
  return `<div class="block-error" role="alert">
    <span class="err-icon">${icon('xCircle', 24, 2.2)}</span>
    <div class="err-body">
      <h2>${esc(e.title || 'Có lỗi')}</h2>
      <p>${esc(e.cause || '')}</p>
      <p><strong>Việc cần làm:</strong> ${esc(e.todo || '')}</p>
      <div class="btn-row" style="margin-top:6px"><button type="button" class="btn btn-primary" data-act="go-nguon">Sang Nguồn dữ liệu</button><button type="button" class="btn btn-secondary" data-act="retry">${e.code === 'NO_NEW_RECORDS' ? 'Về vùng thả file' : 'Thử lại'}</button></div>
    </div>
  </div>
  <section class="card recent" aria-labelledby="h-recent"><h2 id="h-recent">Đã làm gần đây</h2>${viewRecentList(s)}</section>`;
}
function viewSummary(s) {
  const all = s.txns;
  const tiles = ['xanh', 'vang', 'do', 'junsky'].map((k) => {
    const ts = all.filter((t) => t.level === k);
    return `<button type="button" class="tile tile--${k}" data-act="tile" data-level="${k}" aria-pressed="${s.fLevel === k}" title="Bấm để lọc theo mức này">
      <span class="tile-label">${icon(LV[k].icon, 16, 2.4)}${LV[k].tile}</span>
      <span class="tile-count">${ts.length} <small>giao dịch</small></span>
      <span class="tile-total">${fmt(ts.reduce((a, t) => a + t.amt, 0))} VND</span>
    </button>`;
  }).join('');
  const review = all.filter((t) => t.status !== 'junsky').length;
  const done = all.filter((t) => t.status === 'dongy' || t.status === 'boqua').length;
  const waiting = all.filter((t) => t.status === 'cho').length;
  const pct = review ? Math.round(done * 100 / review) : 0;
  const ex = exportable(s).length;
  return `<div class="summary">
    <div class="tiles">${tiles}</div>
    <div class="card review">
      <div style="display:flex;flex-direction:column;gap:6px">
        <div class="review-top"><b>Đã duyệt ${done}/${review}</b><span>${waiting} chờ duyệt · ${ex} chờ xuất</span></div>
        <div class="bar bar--ok" role="progressbar" aria-label="Tiến độ duyệt" aria-valuemin="0" aria-valuemax="${review}" aria-valuenow="${done}"><span style="width:${pct}%"></span></div>
      </div>
      ${s.overview && s.overview.scoring_mode ? `<button type="button" class="btn btn-secondary btn-lg" data-act="score" aria-disabled="${s.scoring}" title="So đề xuất của máy với chứng từ Junsky (chế độ chấm điểm)">${icon('checks', 16, 2.4)}${s.scoring ? 'Đang chấm…' : 'So với Junsky'}</button>` : ''}
      <button type="button" class="btn btn-primary btn-lg" data-act="open-export">${icon('download', 16)}Xuất file</button>
    </div>
    ${s.overview && s.overview.scoring_mode ? `<div class="note-warn">${icon('warn', 17, 2.4)}<span>${s.overview.answer_ledger_name ? `<strong>Đang chấm điểm:</strong> sổ Junsky trong kho này chỉ có đến ${s.overview.ledger_to ? vnDate(s.overview.ledger_to) : '?'} (chứng từ sau ngày đó đã xóa khỏi kho). Nút “So với Junsky” đối chiếu với file đầy đủ <strong>${esc(s.overview.answer_ledger_name)}</strong>, chỉ để chấm. Không xuất File soát cho đến khi tắt chế độ chấm điểm.` : `<strong>Chế độ chấm điểm đang bật:</strong> máy chỉ học đến ${s.overview.learning_cutoff ? vnDate(s.overview.learning_cutoff) : '(chưa đặt mốc)'}; chứng từ Junsky sau mốc là đáp án, không đánh dấu “Đã có trong Junsky”. Tắt ở màn Nguồn dữ liệu trước khi dùng thật.`}</span></div>` : ''}
  </div>`;
}
function viewFilters(s) {
  const pills = (key, arr) => arr.map((a) => `<button type="button" class="pill" data-act="pill" data-key="${key}" data-val="${a[0]}" aria-pressed="${s[key] === a[0]}">${a[1]}</button>`).join('');
  const bl = bulkList(s);
  return `<div class="card filters">
    <div class="fgroup"><span class="fgroup-label">Mức</span>${pills('fLevel', [['all', 'Tất cả'], ['xanh', 'Xanh'], ['vang', 'Vàng'], ['do', 'Đỏ'], ['junsky', 'Đã có trong Junsky']])}</div>
    <div class="fgroup"><span class="fgroup-label">Trạng thái</span>${pills('fStatus', [['all', 'Tất cả'], ['cho', 'Chờ duyệt'], ['dongy', 'Đã đồng ý'], ['boqua', 'Đã bỏ qua'], ['junsky', 'Đã có trong Junsky']])}</div>
    <div class="fgroup"><span class="fgroup-label">Chiều</span>${pills('fDir', isInvoiceRun(s) ? [['all', 'Tất cả'], ['mua', 'Mua vào'], ['ban', 'Bán ra']] : [['all', 'Tất cả'], ['thu', 'Thu'], ['chi', 'Chi']])}</div>
    <label class="search">${icon('search', 16)}<span class="sr-only">Tìm giao dịch</span><input id="tim-giao-dich" type="search" data-input="q" value="${esc(s.q)}" placeholder="Tìm diễn giải, đối tượng, số tiền…"></label>
    <button type="button" class="btn btn-sm btn-soft-ok bulk" data-act="open-bulk" aria-disabled="${bl.length === 0}" title="${bl.length ? 'Đồng ý các giao dịch Xanh đủ điều kiện trong danh sách đang lọc' : 'Không có giao dịch Xanh nào đủ điều kiện trong danh sách đang lọc'}">${icon('checks', 16, 2.4)}Đồng ý tất cả dòng Xanh đang lọc (${bl.length})</button>
  </div>`;
}
function missBox(text) { return `<span class="miss-box">${icon('xCircle', 13, 2.6)}${text}</span>`; }
function optCell(k, v) { return v ? esc(lbl(k, v)) : '<span class="dash">—</span>'; }
function viewDetail(t, s, ck) {
  const isJ = t.status === 'junsky', pend = t.status === 'cho';
  const lines = t.lines.map((l) => {
    const dm = l.tk && isDebt(l.tk) && !l.dt;
    const cashLine = !l.tk && t.cashMissing && l.side === (t.dir === 'thu' ? 'N' : 'C');
    return `<div class="et-grid et-row">
      <span class="et-side">${l.side === 'N' ? 'Nợ' : 'Có'}</span>
      <span>${l.tk ? `<strong>${esc(l.tk)}</strong> <span class="c2">– ${esc(nameOf('tk', l.tk))}</span>` : missBox(cashLine ? 'Thiếu TK tiền' : 'Thiếu tài khoản')}</span>
      <span class="et-num">${fmt(l.amt)}</span>
      <span>${dm ? missBox('Thiếu đối tượng') : optCell('dt', l.dt)}</span>
      <span>${optCell('da', l.da)}</span><span>${optCell('km', l.km)}</span><span>${optCell('cp', l.cp)}</span>
    </div>`;
  }).join('');
  let h = `<div class="detail">`;
  if (isJ) h += `<div class="note-js">${icon('book', 18)}<span>${esc(t.why)} Không cần duyệt và không được xuất lại. <button type="button" class="btn btn-sm btn-link" data-act="clear-existing" data-id="${esc(t.id)}">Không trùng — chuyển về Chờ duyệt</button></span></div>`;
  if (t.cashMissing && pend) h += `<div class="note-warn">${icon('warn', 17, 2.4)}<span>Chưa khai TK kế toán cho tài khoản ngân hàng của sao kê này nên thiếu vế TK tiền. <button type="button" class="btn btn-sm btn-link" data-act="go-nguon">Khai ở Nguồn dữ liệu</button> rồi bấm “Đề xuất lại”.</span></div>`;
  if (t.dirty && pend) h += `<div class="note-warn">${icon('warn', 17, 2.4)}<span>Bút toán đã được đổi so với đề xuất của máy (chọn phương án/điền gợi ý). Bấm Đồng ý để lưu phương án này.</span></div>`;
  if (t.conflict && pend) h += `<div class="note-warn">${icon('warn', 17, 2.4)}<span>Danh bạ STK đang gắn số tài khoản này với <strong>${esc(t.conflict.code)}</strong>${t.conflict.name ? ' – ' + esc(t.conflict.name) : ''}, nhưng tên trên sao kê không khớp. Máy đã bỏ qua ánh xạ đó; Anh chọn đối tượng đúng bên dưới (hoặc bấm Sửa) — khi Đồng ý, danh bạ sẽ được sửa theo.</span></div>`;
  h += `<div class="et"><div class="et-inner">
      <div class="et-grid et-head"><span>Nợ/Có</span><span>Tài khoản</span><span class="right">Số tiền (VND)</span><span>Đối tượng</span><span>Dự án</span><span>Khoản mục</span><span>Trung tâm chi phí</span></div>
      ${lines}
      <div class="et-foot"><span>Tổng Nợ <strong>${fmt(ck.n)}</strong> · Tổng Có <strong>${fmt(ck.c)}</strong>${t.party ? (t.inv ? (t.dir === 'mua' ? ' · Người bán trên hóa đơn: <strong>' : ' · Người mua trên hóa đơn: <strong>') : ' · Tên đối ứng trên sao kê: <strong>') + esc(t.party) + '</strong>' : ''}${t.inv && t.reference ? ' · ' + esc(t.reference) : ''}</span>${ck.bal ? `<span class="bal-ok">${icon('checkCircle', 15, 2.4)}Nợ = Có</span>` : `<span class="bal-bad">${icon('xCircle', 15, 2.4)}Lệch ${fmt(ck.n - ck.c)} VND (Nợ ≠ Có)</span>`}</div>
    </div></div>`;
  if (!isJ) {
    const sgShow = !!(pend && t.suggest && t.suggest.some((g) => g.kind === 'tk' ? t.lines.some((l) => !l.tk) : t.lines.some((l) => l.tk && isDebt(l.tk) && !l.dt)));
    const miss = pend && !ck.ok;
    const hasOpt = pend && t.options;
    const basisOpen = s.basisOpen === t.id;
    h += `<div class="why-row">
      <div class="why">
        <span class="eyebrow eyebrow--blue">VÌ SAO</span>
        <span>${esc(t.why)}</span>
        ${t.basis.length ? `<button type="button" class="btn-basis" data-act="basis" data-id="${esc(t.id)}" aria-expanded="${basisOpen}">${basisOpen ? 'Ẩn căn cứ' : 'Xem căn cứ (' + t.basis.length + ')'}</button>` : `<span style="font-size:13px;color:var(--chu-phu)">Không có chứng từ cũ đủ giống để làm căn cứ.</span>`}
      </div>`;
    if (miss || sgShow || hasOpt || (pend && t.nameOpts)) {
      h += `<div class="side">`;
      if (miss) h += `<div class="miss">${icon('xCircle', 17, 2.4)}<span>${esc(reasonText(ck))}</span></div>`;
      if (sgShow) h += `<div class="suggest"><span class="suggest-title">${esc(t.sgTitle)}</span>${t.suggest.map((g, i) => `<button type="button" class="chip" data-act="suggest" data-id="${esc(t.id)}" data-i="${i}" title="${esc(g.note ? g.note : 'Bấm để điền vào bút toán')}">${icon('plus', 13, 2.6)}${esc(g.kind === 'tk' ? g.value + (nameOf('tk', g.value) ? ' – ' + nameOf('tk', g.value) : '') : lbl('dt', g.value))}${g.note ? `<small class="chip-note">${esc(g.note)}</small>` : ''}</button>`).join('')}</div>`;
      if (pend && t.nameOpts) h += `<div class="suggest"><span class="suggest-title">Đối tượng gợi ý theo tên:</span>${t.nameOpts.map((o) => `<button type="button" class="chip" data-act="pick-name" data-id="${esc(t.id)}" data-code="${esc(o.code)}" title="Bấm để gắn đối tượng này cho bút toán">${icon('plus', 13, 2.6)}${esc(o.code)}${o.name ? ' – ' + esc(o.name) : ''}</button>`).join('')}</div>`;
      if (hasOpt) {
        h += `<span class="eyebrow eyebrow--amber">CÁC PHƯƠNG ÁN</span><div class="options">${t.options.map((o, i) => `<div class="option${t.chosen === i ? ' is-active' : ''}">
          <span class="option-title">Phương án ${i + 1} · ${esc(o.label)}</span>
          <span class="option-sum">${esc(entrySum(o.lines))}</span>
          <span class="option-note">${esc(o.note)}</span>
          ${t.chosen === i ? `<span class="in-use">${icon('checkCircle', 14, 2.6)}Đang dùng</span>` : `<button type="button" class="btn btn-secondary" data-act="use-option" data-id="${esc(t.id)}" data-i="${i}">Dùng phương án này</button>`}
        </div>`).join('')}</div>`;
      }
      h += `</div>`;
    }
    h += `</div>`;
    if (basisOpen) {
      h += `<div class="basis"><div class="basis-inner"><div class="basis-grid basis-head"><span>Ngày</span><span>Số chứng từ</span><span>Diễn giải</span><span>Hạch toán</span></div>${t.basis.map((b) => `<div class="basis-grid"><span>${esc(b.d)}</span><span>${esc(b.no)}${b.note ? `<span class="basis-note">${esc(b.note)}</span>` : ''}</span><span>${esc(b.desc)}</span><b>${esc(b.hk || '—')}</b></div>`).join('')}</div></div>`;
    }
    if (t.status === 'boqua') h += `<p class="skip-note">Lý do bỏ qua: ${esc(t.skipReason || 'không ghi')}</p>`;
  }
  h += viewAiBox(t);
  return h + `</div>`;
}
function viewAiBox(t) {
  const id = esc(t.id);
  if (!t.aiOpen) return `<div class="ai-row"><button type="button" class="btn btn-sm btn-link" data-act="ai-toggle" data-id="${id}">${icon('book', 14)}${t.aiNote ? 'Xem ghi chú cho AI' : 'Ghi chú cho AI / gửi Claude'}</button></div>`;
  const changed = (t.aiDraft || '') !== (t.aiNote || '');
  return `<div class="ai-box">
    <span class="eyebrow eyebrow--blue">GHI CHÚ CHO AI</span>
    <textarea id="ai-${id}" class="input ai-text" rows="3" data-input="aiNote" data-id="${id}" placeholder="Anh muốn giao dịch này xử lý thế nào, vì sao máy sai… Ghi chú được gói cùng ngữ cảnh (đề xuất, căn cứ, chứng từ Junsky) để Claude phân tích hoặc sửa phần mềm.">${esc(t.aiDraft || '')}</textarea>
    <div class="btn-row">
      <button type="button" class="btn btn-sm btn-primary" data-act="ai-save" data-id="${id}" aria-disabled="${!changed}">Lưu ghi chú</button>
      <button type="button" class="btn btn-sm btn-secondary" data-act="ai-send" data-id="${id}">Gửi Claude (tạo gói ngữ cảnh)</button>
      <button type="button" class="btn btn-sm btn-link" data-act="ai-toggle" data-id="${id}">Thu gọn</button>
      ${t.aiNote ? '<span class="small">Đã lưu.</span>' : ''}
    </div>
  </div>`;
}
function viewRow(t, s) {
  const ck = check(t.lines, t);
  const open = s.open === t.id, cur = s.cursor === t.id;
  const obj = objText(t);
  const id = esc(t.id);
  let actions = '';
  if (t.status === 'cho') {
    const dis = !ck.ok;
    actions = `<button type="button" class="btn btn-sm btn-primary" data-act="approve" data-id="${id}" aria-disabled="${dis}" title="${esc(dis ? 'Chưa đồng ý được — ' + reasonText(ck) : 'Đồng ý bút toán này (phím A)')}">${icon('check', 14, 2.8)}Đồng ý</button>
      <button type="button" class="btn btn-sm btn-secondary" data-act="edit" data-id="${id}" title="Sửa bút toán (phím E)">Sửa</button>
      <button type="button" class="btn btn-sm btn-ghost" data-act="skip" data-id="${id}" title="Bỏ qua, để kế toán hạch toán tay (phím S)">Bỏ qua</button>`;
  } else if (t.status === 'dongy' && t.exported) {
    actions = `<span class="state state--exported">${icon('download', 16, 2.4)}Đã xuất file</span>`;
  } else if (t.status === 'dongy') {
    actions = `<span class="state state--ok">${icon('checkCircle', 16, 2.4)}Đã đồng ý</span><button type="button" class="btn btn-sm btn-link" data-act="reopen" data-id="${id}">Mở lại</button>`;
  } else if (t.status === 'boqua') {
    actions = `<span class="state" title="${esc(t.skipReason ? 'Lý do: ' + t.skipReason : 'Không ghi lý do')}">Đã bỏ qua</span><button type="button" class="btn btn-sm btn-link" data-act="reopen" data-id="${id}">Duyệt lại</button>`;
  } else {
    actions = `<span class="js-no">Số CT <strong class="tnum">${esc(t.junskyNo || '—')}</strong></span>`;
  }
  return `<div class="txn txn--${t.status}${cur ? ' is-cursor' : ''}">
    <div class="txn-row">
      <button type="button" class="txn-main txn-cols" id="row-${id}" data-act="toggle" data-id="${id}" aria-expanded="${open}">
        <span class="chev">${icon(open ? 'chevDown' : 'chevRight', 16, 2.2)}</span>
        <span class="date">${esc(t.date)}</span>
        <span class="money"><span class="dir dir--${t.dir}">${DIR_WORD[t.dir]}</span><span class="amt amt--${t.dir}">${DIR_SIGN[t.dir]}${fmt(t.amt)}</span></span>
        <span class="desc-cell"><span class="desc" title="${esc(t.desc)}">${esc(t.desc)}</span><span class="obj${obj ? '' : ' obj--missing'}">${esc(obj || 'Chưa có đối tượng')}</span></span>
        <span class="entry">${esc(entrySum(t.lines))}</span>
        <span style="display:flex">${badge(t.level)}</span>
      </button>
      <div class="txn-actions">${actions}</div>
    </div>
    ${open ? viewDetail(t, s, ck) : ''}
  </div>`;
}
function viewList(s) {
  const vis = visible(s);
  return `<div class="hint"><span class="tnum">Đang hiện ${vis.length}/${s.txns.length} giao dịch</span><span class="hint-keys">Phím tắt (bấm vào danh sách trước): <kbd>↑</kbd><kbd>↓</kbd> chuyển · <kbd>Enter</kbd> mở/đóng · <kbd>A</kbd> đồng ý · <kbd>E</kbd> sửa · <kbd>S</kbd> bỏ qua</span></div>
  <section class="card txn-list" id="ds-giao-dich" tabindex="0" aria-label="Danh sách giao dịch, dùng phím mũi tên để chuyển">
    <div class="txn-head"><div class="txn-cols"><span></span><span>Ngày</span><span>${isInvoiceRun(s) ? 'Mua/Bán · Tiền HĐ' : 'Thu/Chi · Số tiền'}</span><span>${isInvoiceRun(s) ? 'Tên hàng · Đối tượng' : 'Diễn giải gốc · Đối tượng'}</span><span>Bút toán đề xuất</span><span>Mức</span></div><div class="act-h">Thao tác</div></div>
    ${vis.map((t) => viewRow(t, s)).join('')}
    ${vis.length ? '' : `<div class="empty-filter"><span>Không có giao dịch khớp bộ lọc.</span><button type="button" class="btn btn-secondary" data-act="clear-filters">Xóa bộ lọc</button></div>`}
  </section>`;
}
function pageDK(s) {
  let h = `<div class="page"><div class="page-head"><h1>Định khoản</h1><span class="sub">Thả sao kê → máy đề xuất bút toán → duyệt từng giao dịch → xuất file</span></div>`;
  if (s.phase === 'boot') h += '<div class="card loading-block">Đang nạp dữ liệu…</div>';
  else if (s.phase === 'empty') h += viewEmpty(s);
  else if (s.phase === 'error') h += viewError(s);
  else {
    if (s.phase === 'processing') h += viewProc(s);
    else h += viewFileRow(s) + viewSummary(s) + viewFilters(s) + viewList(s);
  }
  return h + `</div>`;
}

function pageNguon(s) {
  const o = s.overview;
  if (!o) return `<div class="page page--mid"><div class="page-head page-head--stack"><h1>Nguồn dữ liệu</h1></div><div class="card loading-block">Đang đọc trạng thái…</div></div>`;
  const running = s.srcLoading || (o.bootstrap_job && o.bootstrap_job.state === 'RUNNING');
  const cc = o.catalog_counts || {};
  const updated = o.junsky_loaded_at ? 'Nạp lúc ' + vnTime(o.junsky_loaded_at) : 'Chưa nạp';
  const pe = o.paths_exist || {}; const paths = o.paths || {}; const fm = o.files_modified || {};
  const fileAt = (k) => fm[k] ? 'File cập nhật ' + vnTime(fm[k]) : 'Chưa thấy file';
  const defs = [
    { k: 'so', title: 'Sổ Junsky', desc: 'Sổ NKC có đối ứng, xuất từ Junsky', dataTo: o.ledger_to ? 'Dữ liệu đến ' + vnDate(o.ledger_to) + ' · ' + fmt(o.journal_count) + ' chứng từ' : 'Chưa có dữ liệu sổ', updated: fileAt('junsky_ledger') + ' · ' + updated,
      err: !pe.junsky_ledger ? 'Không thấy file sổ tại: ' + (paths.junsky_ledger || '') + '. Việc cần làm: xuất lại “Sổ NKC có đối ứng” từ Junsky vào đúng chỗ này rồi bấm Nạp lại.' : (!o.journal_count ? 'Chưa đọc được chứng từ nào trong sổ. Việc cần làm: kiểm tra file sổ rồi bấm Nạp lại.' : '') },
    { k: 'cn', title: 'Danh sách chứng từ công nợ', desc: 'dgbList — chứng từ còn số dư công nợ', dataTo: o.open_item_count ? fmt(o.open_item_count) + ' dòng công nợ đang mở' : 'Chưa có dữ liệu công nợ', updated: fileAt('junsky_dgblist') + ' · ' + updated,
      warn: !pe.junsky_dgblist ? 'Không thấy file dgbList tại: ' + (paths.junsky_dgblist || '') + '. Việc cần làm: xuất lại từ Junsky rồi bấm Nạp lại.' : '' },
    { k: 'dm', title: 'Danh mục', desc: 'Dùng để chọn mã khi sửa bút toán và kiểm tra mã hợp lệ', dataTo: [cc.COUNTERPARTY, cc.ACCOUNT, cc.EXPENSE, cc.PROJECT, cc.COST_CENTER].filter((v) => v > 0).length + '/5 danh mục', updated: fileAt('junsky_catalog') + ' · ' + updated,
      chips: [['Đối tượng', cc.COUNTERPARTY], ['Tài khoản', cc.ACCOUNT], ['Khoản mục', cc.EXPENSE], ['Dự án', cc.PROJECT], ['Trung tâm chi phí', cc.COST_CENTER]],
      err: !cc.COUNTERPARTY ? 'Chưa có danh mục đối tượng nên chưa gắn được đối tượng cho tài khoản công nợ. Việc cần làm: xuất danh mục từ Junsky vào thư mục ' + (paths.junsky_catalog || 'DANH MỤC') + ' rồi bấm Nạp lại.' : '' },
    { k: 'db', title: 'Danh bạ đối tác', desc: 'Số tài khoản ngân hàng đã biết của khách hàng, nhà cung cấp', dataTo: fmt(o.partner_accounts) + ' số tài khoản đã biết · ' + fmt(o.anh_decisions) + ' quyết định Anh đã duyệt', updated: o.partner_file ? 'File: ' + o.partner_file : '',
      warn: !o.partner_file ? 'Chưa thấy file danh bạ đối tác cạnh phần mềm. Giao dịch của đối tác chưa có STK sẽ thiếu đối tượng.' : '' }
  ];
  const cards = defs.map((c) => {
    const err = !running && !!c.err; const warn = !running && !err && !!c.warn;
    const st = running ? ['load', 'refresh', 'Đang nạp…'] : err ? ['err', 'xCircle', 'Lỗi'] : warn ? ['warn', 'warn', 'Cần bổ sung'] : ['ok', 'checkCircle', 'Sẵn sàng'];
    return `<div class="card src${err ? ' is-err' : ''}">
      <div class="src-top"><div class="src-title"><b>${c.title}</b><span>${c.desc}</span></div><span class="st st--${st[0]}">${icon(st[1], 14, 2.6)}${st[2]}</span></div>
      ${c.chips ? `<div class="chips">${c.chips.map((ch) => { const bad = !ch[1]; return `<span class="chip-sm${bad ? ' is-bad' : ''}">${icon(bad ? 'x' : 'check', 12, 3)}${ch[0]} <b>${fmt(ch[1] || 0)}</b></span>`; }).join('')}</div>` : ''}
      <div class="src-meta"><span>${esc(c.dataTo)}</span><span>${esc(c.updated)}</span></div>
      ${err ? `<div class="msg msg--err">${esc(c.err)}</div>` : warn ? `<div class="msg msg--warn">${esc(c.warn)}</div>` : ''}
      <div><button type="button" class="btn btn-secondary" data-act="reload-src"${running ? ' aria-disabled="true"' : ''}>${icon('refresh', 15)}${running ? 'Đang nạp…' : 'Nạp lại'}</button></div>
    </div>`;
  }).join('');
  const maps = (o.cash_accounts || []);
  const glOptions = CAT.tk.filter((r) => /^112/.test(r[0]));
  const mf = s.mapForm;
  return `<div class="page page--mid">
    <div class="page-head page-head--stack"><h1>Nguồn dữ liệu</h1><span class="sub">Dữ liệu nền máy dùng để đề xuất bút toán. Nạp lại mỗi khi có số liệu mới từ Junsky (cả 4 nguồn được đọc lại cùng lúc).</span></div>
    <div class="grid-2">${cards}</div>
    <div class="grid-2">
      <div class="card panel">
        <span class="panel-title">Mốc học</span>
        <span class="sub">Máy chỉ học từ chứng từ trong sổ Junsky đến ngày này. Để trống = học toàn bộ sổ (đến ngày của từng giao dịch). Chứng từ sau mốc học không dùng để học.</span>
        <div class="btn-row" style="align-items:flex-end">
          <div class="stack"><label class="lbl" for="moc-hoc">Máy học từ sổ đến</label><input id="moc-hoc" class="input input-date" type="text" inputmode="numeric" data-input="mocDraft" value="${esc(s.mocDraft)}" placeholder="dd/mm/yyyy"></div>
          <div class="stack"><label class="lbl" for="moc-dt">Chỉ học đối tượng từ ngày</label><input id="moc-dt" class="input input-date" type="text" inputmode="numeric" data-input="objDraft" value="${esc(s.objDraft)}" placeholder="dd/mm/yyyy"></div>
          <button type="button" class="btn btn-primary" data-act="apply-moc">Áp dụng</button>
        </div>
        <span style="font-size:12.5px;color:var(--chu-nhat)">Đổi mốc học xong, bấm “Đề xuất lại” ở màn Định khoản để tính lại các giao dịch đang chờ; giao dịch đã quyết định giữ nguyên.</span>
      </div>
      <div class="card panel">
        <span class="panel-title">Tài khoản ngân hàng ↔ tài khoản kế toán</span>
        <div class="mini-table">
          <div class="r r4 h"><span>Số tài khoản ngân hàng</span><span>Tài khoản kế toán</span><span>Nguồn</span><span></span></div>
          ${maps.length ? maps.map((m) => `<div class="r r4"><span class="tnum">${esc(mask(m.bank_account))}</span><span><strong>${esc(m.cash_account)}</strong> <span class="c2">${esc(nameOf('tk', m.cash_account))}</span></span><span>${m.source === 'MANUAL' ? 'Anh khai' : 'Máy suy ra từ sổ'}</span><span>${m.source === 'MANUAL' ? `<button type="button" class="btn btn-sm btn-link btn-danger" data-act="delete-bank" data-acct="${esc(m.bank_account)}">Xóa</button>` : ''}</span></div>`).join('') : '<div class="r"><span>Chưa khai tài khoản nào — giao dịch sẽ thiếu vế TK tiền.</span></div>'}
        </div>
        ${mf ? `<div class="map-form">
          <div class="stack"><label class="lbl" for="map-acct">Số tài khoản ngân hàng</label><input id="map-acct" class="input" type="text" inputmode="numeric" data-input="mapAcct" value="${esc(mf.acct)}" placeholder="Số tài khoản trên sao kê"></div>
          <div class="stack"><label class="lbl" for="map-gl">TK kế toán (112 chi tiết)</label><select id="map-gl" class="input" data-select="mapGl">${glOptions.map((r) => `<option value="${esc(r[0])}"${r[0] === mf.gl ? ' selected' : ''}>${esc(r[0] + ' – ' + r[1])}</option>`).join('')}</select></div>
          <button type="button" class="btn btn-primary" data-act="save-bank">Lưu</button><button type="button" class="btn btn-secondary" data-act="cancel-bank">Hủy</button>
        </div>` : `<div><button type="button" class="btn btn-dashed" data-act="add-bank">${icon('plus', 14, 2.4)}Thêm tài khoản</button></div>`}
      </div>
      <div class="card panel">
        <span class="panel-title">Chế độ chấm điểm (so với Junsky)</span>
        <span class="sub">Bật khi muốn kiểm tra độ chính xác: đặt <strong>Mốc học</strong> (ví dụ 30/06/2026), bật chế độ này, rồi thả sao kê của tháng sau mốc (T7, T8). Máy không dùng chứng từ sau mốc để học và không đánh dấu “Đã có trong Junsky”; nút <strong>So với Junsky</strong> ở màn Định khoản chấm từng dòng. <strong>Tắt trước khi dùng thật.</strong></span>
        <label class="export-opt"><input type="checkbox" data-check="scoring"${o.scoring_mode ? ' checked' : ''}><span><strong>${o.scoring_mode ? 'Đang bật' : 'Đang tắt'}</strong><small>${o.scoring_mode ? 'Chứng từ Junsky sau mốc học là đáp án, không phải tri thức.' : 'Vận hành bình thường: học toàn bộ sổ đến mốc, đánh dấu dòng đã có trong Junsky.'}</small></span></label>
        <span style="font-size:12.5px;color:var(--chu-nhat)">AI cục bộ: ${o.local_ai && o.local_ai.enabled ? 'đang bật (' + esc(o.local_ai.url || '') + ')' : 'tắt — chỉ bật trong source-settings.json khi máy đã cài LM Studio/Ollama; chỉ dùng để chọn giữa các tên gần giống.'}</span>
      </div>
      <div class="card panel">
        <span class="panel-title">Tài khoản công nợ bắt buộc có đối tượng</span>
        <span class="sub">Nút Đồng ý chỉ bấm được khi các dòng có tài khoản này (kể cả tài khoản chi tiết, ví dụ 1388 gồm 13881) đã có đối tượng. <strong>Danh sách chờ CFO xác nhận.</strong></span>
        <div class="btn-row" style="align-items:flex-end"><div class="stack"><label class="lbl" for="debt">Các tài khoản (cách nhau dấu phẩy)</label><input id="debt" class="input debt-input" type="text" data-input="debtDraft" value="${esc(s.debtDraft)}"></div><button type="button" class="btn btn-primary" data-act="apply-debt">Lưu</button></div>
      </div>
    </div>
  </div>`;
}
function pageTC(s) {
  const kb = s.kb;
  const cards = kb ? kb.cards : [];
  return `<div class="page page--narrow">
    <div class="page-head page-head--stack"><h1>Tra cứu tri thức</h1><span class="sub">Các quy tắc máy đang dùng. Chỉ đọc — muốn đổi thì sửa bút toán và bật “Ghi nhớ cho lần sau”.</span></div>
    <label class="search search--lg">${icon('search', 18)}<span class="sr-only">Tìm quy tắc</span><input id="tim-tri-thuc" type="search" data-input="kbQ" value="${esc(s.kbQ)}" placeholder="Tìm theo số tài khoản, mã/tên đối tượng hoặc từ khóa (ví dụ: 331, phí SMS, tiền điện)"></label>
    <span class="sub">${kb ? (kb.total > cards.length ? 'Hiện ' + cards.length + '/' + fmt(kb.total) + ' quy tắc — gõ thêm để lọc' : fmt(kb.total) + ' quy tắc') : 'Đang tải…'} · ${s.overview && s.overview.learning_cutoff ? 'học từ sổ đến ' + vnDate(s.overview.learning_cutoff) : 'học từ toàn bộ sổ'}</span>
    ${cards.map((r) => `<article class="card kb">
      <span class="eyebrow eyebrow--gray">KHI</span><span class="kb-when">${r.kind === 'ANH' ? '<span class="kb-kind kb-kind--anh">ANH ĐÃ DUYỆT</span> ' : r.code ? '<span class="kb-kind">' + esc(r.code) + '</span> ' : ''}${esc(r.when)}</span>
      <span class="eyebrow eyebrow--blue">THÌ</span><span>${esc(r.then)}</span>
      <span class="eyebrow eyebrow--gray">VÌ SAO</span><span class="kb-why">${esc(r.why)}</span>
      <span></span><span class="tags">${(r.tags || []).map((t) => `<span class="tag">${esc(t)}</span>`).join('')}</span>
    </article>`).join('')}
    ${kb && !cards.length ? '<div class="card empty-card">Không tìm thấy quy tắc phù hợp. Thử số tài khoản (ví dụ 131) hoặc mã đối tượng.</div>' : ''}
  </div>`;
}
function pageCFO(s) {
  const c = s.cfo;
  const rules = c ? c.rules || [] : [];
  const monthLabel = (m) => (m && m.length >= 7 ? m.slice(5, 7) + '/' + m.slice(0, 4) : m || '');
  const stat = (r) => {
    if (!r.thang || !r.thang.length) return '<span class="sub">Chưa áp dụng lần nào.</span>';
    return `<div class="mini-table"><div class="r r6 h"><span>Tháng</span><span>Áp dụng</span><span>Anh đồng ý giữ nguyên</span><span>Anh sửa</span><span>Bỏ qua</span><span>Chưa xử lý</span></div>
      ${r.thang.map((m) => `<div class="r r6"><span>${esc(monthLabel(m.thang))}</span><span><strong>${m.ap_dung || 0}</strong></span><span>${m.giu_nguyen || 0}</span><span>${m.sua || 0}</span><span>${m.bo_qua || 0}</span><span>${m.cho || 0}</span></div>`).join('')}</div>`;
  };
  return `<div class="page page--narrow">
    <div class="page-head page-head--stack"><h1>Tri thức CFO</h1><span class="sub">Quy tắc Anh quyết định khi trao đổi với Claude (tệp ${esc((c && c.file) || 'TRI-THUC-CFO.json')}). Claude ghi quy tắc theo xác nhận của Anh; phần mềm duyệt dưới tên Anh. Tắt ở đây thì máy ngừng dùng — bấm “Đề xuất lại” ở màn Định khoản để áp dụng.</span></div>
    ${c && c.error ? `<div class="note-warn">${icon('warn', 17, 2.4)}<span>${esc(c.error)}</span></div>` : ''}
    ${!c ? '<div class="card empty-card">Đang tải…</div>' : !rules.length ? '<div class="card empty-card">Chưa có quy tắc nào. Khi Anh chốt một cách hạch toán trong Cowork, Claude sẽ ghi vào đây.</div>' : ''}
    ${rules.map((r) => `<article class="card kb">
      <span class="eyebrow eyebrow--gray">MÃ</span><span class="kb-when"><span class="kb-kind${r.loai === 'LUU_Y' ? '' : ' kb-kind--anh'}">${r.loai === 'LUU_Y' ? 'LƯU Ý' : 'QUY TẮC'}</span> <strong>${esc(r.ma)}</strong> · Anh duyệt ${esc(r.ngay_duyet ? vnDate(r.ngay_duyet) : '?')} · ${r.dang_dung ? '<span class="tag">Đang dùng</span>' : '<span class="tag">Đã tắt</span>'}</span>
      <span class="eyebrow eyebrow--gray">KHI</span><span>${esc(r.dieu_kien)}</span>
      <span class="eyebrow eyebrow--blue">THÌ</span><span>${esc(r.ket_qua)}</span>
      <span class="eyebrow eyebrow--gray">NGUỒN</span><span class="kb-why">${esc(r.nguon)}</span>
      <span class="eyebrow eyebrow--gray">ĐÃ DÙNG</span><span>${stat(r)}</span>
      <span></span><span class="btn-row"><button type="button" class="btn btn-sm ${r.dang_dung ? 'btn-secondary' : 'btn-primary'}" data-act="cfo-toggle" data-code="${esc(r.ma)}" data-on="${r.dang_dung ? '0' : '1'}" aria-disabled="${s.cfoBusy === r.ma}">${r.dang_dung ? 'Tắt quy tắc' : 'Bật lại'}</button></span>
    </article>`).join('')}
  </div>`;
}
function pageLS(s) {
  return `<div class="page page--mid">
    <div class="page-head page-head--stack"><h1>Lịch sử xuất file</h1><span class="sub">File được lưu trong thư mục ${esc(s.historyFolder || 'xuat-junsky')}. Phần mềm không tự nhập Junsky.</span></div>
    <div class="card hist"><div class="hist-inner">
      <div class="hist-grid h5 hist-head"><span>Ngày giờ</span><span class="right">Số giao dịch</span><span class="right">Tổng tiền (VND)</span><span>Người duyệt</span><span>Tên file</span><span class="right">Thao tác</span></div>
      ${s.history.length ? s.history.map((h) => { const f = (h.files || [])[0] || ''; return `<div class="hist-grid h5"><span>${esc(vnTime(h.at))}</span><span class="right"><strong>${h.count}</strong></span><span class="right tnum">${fmt(h.total_minor)}</span><span>${esc(h.actor)}</span><span class="ell" title="${esc(f)}">${esc(f)}</span><span class="acts"><button type="button" class="btn btn-sm btn-secondary" data-act="open-file" data-run="${esc(h.run_id)}" data-file="${esc(f)}">Mở file</button><button type="button" class="btn btn-sm btn-link" data-act="download-file" data-run="${esc(h.run_id)}" data-file="${esc(f)}">${icon('download', 15)}Tải về</button><button type="button" class="btn btn-sm btn-link" data-act="hist-folder" data-run="${esc(h.run_id)}">${icon('folder', 15)}Thư mục</button></span></div>`; }).join('') : '<div class="hist-grid"><span>Chưa xuất file nào.</span></div>'}
    </div></div>
  </div>`;
}

function viewField(d, l, li, key) {
  const active = !!(d.combo && d.combo.li === li && d.combo.key === key);
  const code = l[key];
  const req = key === 'tk' || (key === 'dt' && isDebt(l.tk));
  const err = req && !code && !active;
  const id = 'f-' + li + '-' + key;
  const opts = active ? filterCat(key, d.q) : [];
  return `<div class="field${key === 'cp' ? ' field--wide' : ''}">
    <label class="lbl" for="${id}">${FIELD_LABEL[key]}${req ? ' <span class="req">*</span>' : ''}</label>
    <input id="${id}" class="input${active ? ' is-active' : err ? ' is-error' : ''}" type="text" autocomplete="off" role="combobox" aria-expanded="${active}" aria-controls="${id}-list" data-combo data-li="${li}" data-key="${key}" value="${esc(active ? d.q : (code ? lbl(key, code) : ''))}" placeholder="${esc(active && code ? lbl(key, code) : 'Tìm theo mã hoặc tên…')}">
    ${code && !active ? `<button type="button" class="field-clear" aria-label="Xóa ${FIELD_LABEL[key]}" data-act="clear-field" data-li="${li}" data-key="${key}">${icon('x', 14, 2.4)}</button>` : ''}
    ${active ? `<div class="combo-list" id="${id}-list" role="listbox">${opts.length ? opts.map((r, i) => `<button type="button" role="option" class="combo-opt${i === 0 && d.q ? ' is-first' : ''}${r[0] === code ? ' is-current' : ''}" data-pick data-li="${li}" data-key="${key}" data-code="${esc(r[0])}"><strong>${esc(r[0])}</strong><span>${esc(r[1])}</span></button>`).join('') + (opts.length >= COMBO_LIMIT ? '<div class="combo-empty">Gõ thêm để thu hẹp kết quả…</div>' : '') : '<div class="combo-empty">Không tìm thấy trong danh mục.</div>'}</div>` : ''}
    ${err ? `<span class="field-err">${key === 'tk' ? 'Chưa chọn tài khoản' : 'Tài khoản công nợ cần có đối tượng'}</span>` : ''}
  </div>`;
}
function viewDrawer(s) {
  const d = s.drawer; const t = s.txns.find((x) => x.id === d.id); const ck = check(d.lines, t);
  if (!t) return '';
  return `<button type="button" class="backdrop" aria-label="Đóng ngăn Sửa" data-act="close-drawer"></button>
  <aside class="drawer" aria-label="Sửa bút toán">
    <div class="drawer-head">
      <div class="drawer-title"><h2>Sửa bút toán</h2><span class="meta">${esc(t.date)} · ${DIR_WORD[t.dir]} <strong>${fmt(t.amt)} VND</strong> · ${esc(t.desc)}</span></div>
      <button type="button" class="icon-btn" id="drawer-close" aria-label="Đóng" data-act="close-drawer">${icon('x', 18, 2.2)}</button>
    </div>
    <div class="drawer-body" id="drawer-body">
      ${d.lines.map((l, li) => `<div class="line-card">
        <div class="line-top">
          <span class="line-no">Dòng ${li + 1}</span>
          <div class="stack"><span class="lbl">Nợ/Có</span><div class="seg"><button type="button" data-act="side" data-li="${li}" data-side="N" aria-pressed="${l.side === 'N'}">Nợ</button><button type="button" data-act="side" data-li="${li}" data-side="C" aria-pressed="${l.side === 'C'}">Có</button></div></div>
          <div class="stack"><label class="lbl" for="amt-${li}">Số tiền (VND)</label><input id="amt-${li}" class="input input-amt" type="text" inputmode="numeric" data-input="amt" data-li="${li}" value="${l.amt ? fmt(l.amt) : ''}"></div>
          ${d.lines.length > 2 ? `<button type="button" class="btn btn-sm btn-ghost btn-danger remove-line" aria-label="Xóa dòng ${li + 1}" data-act="remove-line" data-li="${li}">${icon('x', 15, 2.2)}Xóa dòng</button>` : ''}
        </div>
        <div class="fields">${['tk', 'dt', 'da', 'km', 'cp'].map((k) => viewField(d, l, li, k)).join('')}</div>
      </div>`).join('')}
      <button type="button" class="btn btn-dashed" style="align-self:flex-start" data-act="add-line">${icon('plus', 14, 2.4)}Thêm dòng bút toán</button>
      <div class="bal ${ck.bal ? 'bal--ok' : 'bal--bad'}">
        <span>Tổng Nợ <strong>${fmt(ck.n)}</strong> · Tổng Có <strong>${fmt(ck.c)}</strong> · Số tiền sao kê <strong>${fmt(t.amt)}</strong></span>
        ${ck.bal ? `<span class="bal-ok">${icon('checkCircle', 15, 2.4)}Nợ = Có</span>` : `<span class="bal-bad">${icon('xCircle', 15, 2.4)}Lệch ${fmt(ck.n - ck.c)} VND</span>`}
      </div>
    </div>
    <div class="drawer-foot">
      <label class="check-row"><input type="checkbox" data-remember${d.remember ? ' checked' : ''}><span><strong>Ghi nhớ cho lần sau:</strong> áp dụng cho các giao dịch cùng số tài khoản đối ứng (cả các giao dịch đang chờ trong file này)</span></label>
      <div class="btn-row btn-row--end">
        ${ck.ok ? '' : `<span class="foot-reason">Chưa lưu được — ${esc(reasonText(ck))}</span>`}
        <button type="button" class="btn btn-secondary" data-act="close-drawer">Hủy</button>
        <button type="button" class="btn btn-primary" data-act="save-drawer" aria-disabled="${!ck.ok}"${s.saving ? ' aria-busy="true"' : ''}>${icon('check', 15, 2.8)}${s.saving ? 'Đang lưu…' : 'Lưu và đồng ý'}</button>
      </div>
    </div>
  </aside>`;
}
function viewModal(s) {
  let body = '', label = '';
  if (s.modal === 'bulk') {
    const bl = bulkList(s); label = 'Đồng ý hàng loạt';
    body = `<h2>Đồng ý hàng loạt</h2>
      <p class="lead">Anh sắp đồng ý <strong>${bl.length} giao dịch</strong>, tổng <strong class="tnum">${fmt(bl.reduce((a, t) => a + t.amt, 0))} VND</strong>.</p>
      <div class="mini-list">${bl.map((t) => `<div class="mini-row"><span>${esc(t.date)}</span><b>${fmt(t.amt)}</b><span class="ell">${esc(t.desc)}</span></div>`).join('')}</div>
      <p class="small">Chỉ gồm giao dịch mức Xanh, đang chờ duyệt, khớp bộ lọc hiện tại và đủ điều kiện (Nợ = Có, tài khoản công nợ có đối tượng). Có thể hoàn tác ngay sau khi đồng ý.</p>
      <div class="btn-row btn-row--end"><button type="button" class="btn btn-secondary" id="modal-cancel" data-act="close-modal">Hủy</button><button type="button" class="btn btn-primary" data-act="confirm-bulk">Đồng ý ${bl.length} giao dịch</button></div>`;
  } else if (s.modal === 'score') {
    const r = s.score || { summary: [], rows: [] }; label = 'So với Junsky';
    const sum = (k) => r.summary.reduce((a, x) => a + (x[k] || 0), 0);
    const bad = r.rows.filter((x) => x.account_ok === false || x.counterparty_ok === false).slice(0, 40);
    const invScore = r.kind === 'INVOICE';
    body = `<h2>So đề xuất của máy với chứng từ Junsky</h2>
      <p class="small">${invScore ? 'Mỗi hóa đơn được ghép với chứng từ Junsky theo số tiền chưa thuế + tiền thuế (20 ngày trước đến 75 ngày sau ngày hóa đơn), rồi so TK chi phí/doanh thu (cột “TK đúng”), TK công nợ, đối tượng, dự án. Chấm riêng Mua vào và Bán ra.' + (r.summary.length ? ' TK công nợ đúng: ' + r.summary.map((x) => esc(x.level) + ' ' + (x.partner_ok || 0) + '/' + x.matched).join(' · ') + '.' : '') : 'Mỗi dòng sao kê được ghép với chứng từ Junsky theo ngày + số tiền (gộp dòng 112; nhiều lần chuyển cùng ngày = 1 chứng từ), rồi so tài khoản đối ứng, đối tượng, dự án.'}${r.answer_source ? ' Đáp án: <strong>' + esc(r.answer_source) + '</strong>.' : ''}</p>
      <div class="score-table">
        <div class="r r9 h"><span>Mức</span><span>Dòng</span><span>Ghép được</span><span>Không ghép</span><span>TK đúng</span><span>Có đối tượng</span><span>Đối tượng đúng</span><span>Có dự án</span><span>Dự án đúng</span></div>
        ${r.summary.map((x) => `<div class="r r9"><span><b>${esc(x.level)}</b></span><span>${x.rows}</span><span>${x.matched}</span><span>${x.unmatched}</span><span>${x.account_ok}/${x.matched}</span><span>${x.counterparty_given}</span><span>${x.counterparty_ok}/${x.counterparty_given}</span><span>${x.project_given}</span><span>${x.project_ok}/${x.project_given}</span></div>`).join('')}
        <div class="r r9 h"><span>Tổng</span><span>${sum('rows')}</span><span>${sum('matched')}</span><span>${sum('unmatched')}</span><span>${sum('account_ok')}/${sum('matched')}</span><span>${sum('counterparty_given')}</span><span>${sum('counterparty_ok')}/${sum('counterparty_given')}</span><span>${sum('project_given')}</span><span>${sum('project_ok')}/${sum('project_given')}</span></div>
      </div>
      ${bad.length ? `<p class="small" style="margin-top:10px"><strong>${bad.length} dòng máy sai TK hoặc sai đối tượng</strong> (chi tiết đầy đủ trong file):</p><div class="mini-list">${bad.map((x) => `<div class="mini-row"><span>${esc(vnDate(x.business_date))}</span><b>${fmt(x.amount_minor)}</b><span class="ell">${esc(x.level)} · máy ${esc(x.proposed || '?')}${x.counterparty ? ' [' + esc(x.counterparty) + ']' : ''} · Junsky ${esc(x.actual || '?')}${x.actual_counterparty ? ' [' + esc(x.actual_counterparty) + ']' : ''} · CT ${esc(x.voucher)}</span></div>`).join('')}</div>` : ''}
      <div class="path">${esc((r.folder_display ? r.folder_display + '\\' : '') + (r.file || ''))}</div>
      <div class="btn-row btn-row--end"><button type="button" class="btn btn-secondary" id="modal-cancel" data-act="close-modal">Đóng</button><button type="button" class="btn btn-secondary" data-act="download-score-file">${icon('download', 16)}Tải về</button><button type="button" class="btn btn-primary" data-act="open-score-file">${icon('folder', 16)}Mở file</button></div>`;
  } else if (s.modal === 'ai') {
    const r = s.aiResult || {}; label = 'Gói ngữ cảnh cho Claude';
    body = `<div class="done-head"><span class="done-icon">${icon('check', 22, 2.6)}</span><h2>Đã tạo gói ngữ cảnh (${r.count || 0} giao dịch)</h2></div>
      <p class="small">File nằm trong thư mục dưới đây (bản mới nhất luôn là <strong>MOI-NHAT.md</strong>). Trong phiên Cowork, Anh chỉ cần nói: <em>“đọc ghi chú AI mới nhất”</em> — Claude đọc file này từ máy Anh rồi phân tích hoặc sửa phần mềm.</p>
      <div class="path">${esc((r.folder_display ? r.folder_display + '\\' : '') + (r.file || ''))}</div>
      <details class="ai-preview"><summary>Xem nội dung gói</summary><pre>${esc(r.markdown || '')}</pre></details>
      <div class="btn-row btn-row--end"><button type="button" class="btn btn-secondary" id="modal-cancel" data-act="close-modal">Đóng</button><button type="button" class="btn btn-primary" data-act="open-ai-folder">${icon('folder', 16)}Mở thư mục</button></div>`;
  } else if (s.modal === 'skip') {
    const t = s.txns.find((x) => x.id === s.skipId); label = 'Bỏ qua giao dịch';
    body = `<h2>Bỏ qua giao dịch</h2>
      <p class="tnum">${t ? esc(t.date + ' · ' + DIR_WORD[t.dir] + ' ' + fmt(t.amt) + ' VND · ' + t.desc) : ''}</p>
      <p class="small">Giao dịch sẽ không có trong file xuất; kế toán hạch toán tay trong Junsky.</p>
      <div class="stack"><label class="lbl" for="ly-do">Lý do (không bắt buộc)</label><input id="ly-do" class="input" type="text" data-input="skipReason" value="${esc(s.skipReason)}" placeholder="Ví dụ: chờ hợp đồng, cần hỏi lại phòng kinh doanh"></div>
      <div class="btn-row btn-row--end"><button type="button" class="btn btn-secondary" id="modal-cancel" data-act="close-modal">Hủy</button><button type="button" class="btn btn-dark" data-act="confirm-skip">Bỏ qua giao dịch</button></div>`;
  } else {
    const ap = exportable(s); const apTotal = fmt(ap.reduce((a, t) => a + t.amt, 0));
    const pd = s.txns.filter((t) => t.status === 'cho').length; label = 'Xuất file';
    if (!s.exportDone) {
      body = `<h2>Xuất file</h2>
        <div class="stat-grid">
          <div class="stat stat--ok"><span style="font-weight:600">Đã đồng ý, chưa xuất</span><b>${ap.length}</b><span class="tnum">${apTotal} VND</span></div>
          <div class="stat stat--gray"><span style="font-weight:600">Còn chờ duyệt</span><b>${pd}</b><span>sẽ không có trong file</span></div>
        </div>
        ${pd ? `<div class="warn-box">${icon('warn', 17, 2.4)}<span>Còn ${pd} giao dịch chờ duyệt. Có thể xuất ngay rồi xuất bổ sung sau khi duyệt xong (lần sau chỉ gồm giao dịch mới đồng ý).</span></div>` : ''}
        <label class="export-opt"><input type="checkbox" checked disabled><span><strong>File soát (Excel)</strong><small>Luôn bật — từng dòng bút toán đã đồng ý kèm “Vì sao”, để kế toán soát và nhập tay vào Junsky.</small></span></label>
        <label class="export-opt export-opt--locked"><input type="checkbox" disabled><span><strong>${icon('lock', 14, 2.2)}File nhập Junsky (Phiếu thu / Phiếu chi ngân hàng)</strong><small>Tạm khóa — mở sau khi nhập thử thành công.</small></span></label>
        <div class="btn-row btn-row--end"><button type="button" class="btn btn-secondary" id="modal-cancel" data-act="close-modal">Hủy</button><button type="button" class="btn btn-primary" data-act="do-export" aria-disabled="${ap.length === 0 || s.exporting}"${s.exporting ? ' aria-busy="true"' : ''}>${icon('download', 16)}${s.exporting ? 'Đang xuất…' : 'Xuất'}</button></div>`;
    } else {
      const r = s.exportResult || {};
      body = `<div class="done-head"><span class="done-icon">${icon('check', 22, 2.6)}</span><h2>Đã xuất file soát</h2></div>
        <p>${r.reviewed || 0} giao dịch đã đồng ý, tổng ${fmt(r.total_minor || 0)} VND.</p>
        <div class="path">${esc((r.folder_display ? r.folder_display + '\\' : '') + (r.review || ''))}</div>
        <div class="btn-row btn-row--end"><button type="button" class="btn btn-secondary" id="modal-cancel" data-act="close-modal">Đóng</button><button type="button" class="btn btn-secondary" data-act="download-file" data-file="${esc(r.review || '')}">${icon('download', 16)}Tải về</button><button type="button" class="btn btn-primary" data-act="open-folder">${icon('folder', 16)}Mở thư mục</button></div>`;
    }
  }
  return `<div class="modal-wrap"><div class="modal" role="dialog" aria-modal="true" aria-label="${label}">${body}</div></div>`;
}
function viewToast(s) {
  return `<div class="toast" role="status"><span>${esc(s.toast.text)}</span>${s.toast.undo ? '<button type="button" class="toast-undo" data-act="undo">Hoàn tác</button>' : ''}<button type="button" class="toast-close" aria-label="Đóng thông báo" data-act="close-toast">${icon('x', 15, 2.4)}</button></div>`;
}
function view(s) {
  const page = s.screen === 'dk' ? pageDK(s) : s.screen === 'nguon' ? pageNguon(s) : s.screen === 'tracuu' ? pageTC(s) : s.screen === 'cfo' ? pageCFO(s) : pageLS(s);
  return `<div class="app">${viewTopbar(s)}${viewNav(s)}<main class="main" id="main">${page}</main>${s.drawer ? viewDrawer(s) : ''}${s.modal ? viewModal(s) : ''}${s.toast ? viewToast(s) : ''}</div>`;
}

/* =====================================================================
   8. VẼ LẠI (giữ tiêu điểm, vị trí con trỏ chữ, vị trí cuộn)
   ===================================================================== */
const $app = document.getElementById('app');
let restoring = false;
function render() {
  const ae = document.activeElement; const fid = ae && ae.id ? ae.id : null;
  let selS = null, selE = null;
  try { if (fid && typeof ae.selectionStart === 'number') { selS = ae.selectionStart; selE = ae.selectionEnd; } } catch (e) { /* bỏ qua */ }
  const m = document.getElementById('main'); let mainTop = m ? m.scrollTop : 0;
  const db = document.getElementById('drawer-body'); const dTop = db ? db.scrollTop : 0;
  if (S.screen !== lastScreen) { mainTop = 0; lastScreen = S.screen; }
  $app.innerHTML = view(S);
  const m2 = document.getElementById('main'); if (m2) m2.scrollTop = mainTop;
  const d2 = document.getElementById('drawer-body'); if (d2) d2.scrollTop = dTop;
  if (fid) {
    const el = document.getElementById(fid);
    if (el) {
      restoring = true; el.focus({ preventScroll: true }); restoring = false;
      if (selS !== null && el.setSelectionRange) {
        try { if (fid.indexOf('amt-') === 0) { const n = el.value.length; el.setSelectionRange(n, n); } else el.setSelectionRange(selS, selE); } catch (e) { /* bỏ qua */ }
      }
    }
  }
}

/* =====================================================================
   9. SỰ KIỆN (ủy quyền trên #app)
   ===================================================================== */
$app.addEventListener('click', (e) => {
  const combo = e.target.closest('[data-combo]');
  if (combo) { openCombo(+combo.dataset.li, combo.dataset.key); return; }
  const el = e.target.closest('[data-act]');
  if (!el) return;
  if (el.getAttribute('aria-disabled') === 'true' && ['approve', 'save-drawer'].indexOf(el.dataset.act) < 0) { if (el.dataset.act === 'open-bulk') ACT['open-bulk'](el.dataset, e); return; }
  const fn = ACT[el.dataset.act];
  if (fn) fn(el.dataset, e);
});
$app.addEventListener('mousedown', (e) => {
  const o = e.target.closest('[data-pick]');
  if (o) { e.preventDefault(); dSet(+o.dataset.li, o.dataset.key, o.dataset.code, true); }
});
$app.addEventListener('input', (e) => {
  const t = e.target;
  if (t.matches('[data-combo]')) { const li = +t.dataset.li, key = t.dataset.key, v = t.value; dUpd((d) => { d.q = v; d.combo = { li, key }; }); return; }
  const f = t.dataset.input; if (!f) return;
  if (f === 'amt') { const v = t.value.replace(/\D/g, ''); dSet(+t.dataset.li, 'amt', v ? Number(v) : 0); return; }
  if (f === 'mapAcct') { set({ mapForm: Object.assign({}, S.mapForm, { acct: t.value }) }); return; }
  if (f === 'aiNote') { const id = t.dataset.id, v = t.value; set((s) => ({ txns: s.txns.map((x) => x.id === id ? Object.assign({}, x, { aiDraft: v }) : x) })); return; }
  set({ [f]: t.value });
  if (f === 'kbQ') { clearTimeout(timers.kb); timers.kb = setTimeout(loadKb, 300); }
});
$app.addEventListener('change', (e) => {
  const t = e.target;
  if (t.matches('[data-remember]')) dUpd((d) => { d.remember = t.checked; });
  else if (t.matches('[data-check="scoring"]')) toggleScoring(t.checked);
  else if (t.matches('[data-select="mapGl"]')) set({ mapForm: Object.assign({}, S.mapForm, { gl: t.value }) });
});
$app.addEventListener('focusin', (e) => {
  const t = e.target;
  if (!restoring && t.matches && t.matches('[data-combo]')) openCombo(+t.dataset.li, t.dataset.key);
});
$app.addEventListener('focusout', (e) => {
  const t = e.target;
  if (!(t.matches && t.matches('[data-combo]'))) return;
  const id = t.id, li = +t.dataset.li, key = t.dataset.key;
  setTimeout(() => {
    const a = document.activeElement; if (a && a.id === id) return;
    if (comboActive(li, key)) dUpd((d) => { d.combo = null; });
  }, 160);
});
$app.addEventListener('dragover', (e) => {
  if (!e.target.closest('#dropzone')) return;
  e.preventDefault(); if (!S.dragOver) set({ dragOver: true });
});
$app.addEventListener('dragleave', (e) => {
  if (e.target.closest('#dropzone') && !(e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('#dropzone'))) set({ dragOver: false });
});
$app.addEventListener('drop', (e) => {
  if (!e.target.closest('#dropzone')) return;
  e.preventDefault();
  const files = e.dataTransfer && e.dataTransfer.files ? Array.from(e.dataTransfer.files) : [];
  if (files.length > 1) toast('Mỗi lần thả một file sao kê — đang xử lý file đầu tiên: ' + files[0].name);
  if (files.length) startUpload(files[0]); else set({ dragOver: false });
});
document.addEventListener('dragover', (e) => { e.preventDefault(); });
document.addEventListener('drop', (e) => { if (!e.target.closest || !e.target.closest('#dropzone')) e.preventDefault(); });
document.getElementById('file-input').addEventListener('change', (e) => {
  const files = Array.from(e.target.files || []);
  if (files.length) startUpload(files[0]);
});
document.addEventListener('keydown', (e) => {
  const t = e.target;
  if (t.matches && t.matches('[data-combo]')) {
    const li = +t.dataset.li, key = t.dataset.key;
    if (e.key === 'Escape' && comboActive(li, key)) { e.preventDefault(); dUpd((d) => { d.combo = null; }); }
    else if (e.key === 'Enter' && comboActive(li, key)) { e.preventDefault(); const f = filterCat(key, S.drawer.q)[0]; if (f) dSet(li, key, f[0], true); }
    return;
  }
  if (e.key === 'Escape') { if (S.modal) { set({ modal: null }); return; } if (S.drawer) { set({ drawer: null }); return; } }
  if (t.closest && t.closest('#ds-giao-dich')) listKey(e);
});
function listKey(e) {
  const t = e.target;
  if (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || S.drawer || S.modal) return;
  const ids = visible(S).map((x) => x.id); if (!ids.length) return;
  const i = ids.indexOf(S.cursor); const k = e.key;
  if (k === 'ArrowDown' || k === 'ArrowUp') {
    e.preventDefault();
    const j = k === 'ArrowDown' ? Math.min(ids.length - 1, i + 1) : Math.max(0, i - 1);
    set((s) => ({ cursor: ids[j], open: s.open !== null ? ids[j] : null }));
    const b = document.getElementById('row-' + ids[j]); if (b) b.focus();
  } else if (k === 'Enter') {
    const onRow = t.id === 'ds-giao-dich' || t.classList.contains('txn-main');
    if (!onRow) return;
    e.preventDefault(); const id = t.classList.contains('txn-main') ? t.dataset.id : (i >= 0 ? ids[i] : ids[0]);
    set((s) => ({ cursor: id, open: s.open === id ? null : id }));
  } else if ((k === 'a' || k === 'A') && i >= 0) { e.preventDefault(); approve(ids[i]); }
  else if ((k === 'e' || k === 'E') && i >= 0) { e.preventDefault(); edit(ids[i]); }
  else if ((k === 's' || k === 'S') && i >= 0) { e.preventDefault(); skip(ids[i]); }
}

render();
boot();
