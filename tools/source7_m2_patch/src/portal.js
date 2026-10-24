'use strict';

const path = require('path');
const crypto = require('crypto');
const cfg = require('../config');

// M2-00A: nap Playwright khi that su mo trinh duyet (de phan lay danh sach/tai XML kiem duoc bang transport gia).
let chromiumImpl = null;
function getChromium() {
  if (!chromiumImpl) chromiumImpl = require('playwright').chromium;
  return chromiumImpl;
}

// Header rieng ma trang web (SPA) gui kem moi request - WAF cong thue YEU CAU co,
// thieu se bi 403 "hanh vi khong hop le". Xem api_debug.log de doi chieu neu doi.
const END_POINT = '/tra-cuu/tra-cuu-hoa-don';
function newRequestId() {
  try { return crypto.randomUUID(); } catch (_) { return String(Date.now()) + Math.random().toString(16).slice(2); }
}
function labelAction(kind, type) {
  const t = type === 'sold' ? 'bán ra' : 'mua vào';
  const verb = kind === 'export' ? 'Xuất xml' : 'Tìm kiếm';
  return encodeURIComponent(`${verb} (hóa đơn ${t})`);
}

// Thong bao "khong ton tai ..." cua cong: CHI dung de dung retry som (hanh vi cu), khong dung de phan loai.
const NO_ORIGIN_RE = /kh[oôố]ng\s*t[oồ]n\s*t[aạ]i|kh[oôố]ng.*h[oồ]\s*s[oơ]|no[_\s-]*origin/i;

// M2-00A FIX01: bang chung nghiep vu "khong co ho so goc" phai neu ro cum "ho so goc" trong truong thong bao
// cua body JSON. "Khong ton tai" chung chung (duong dan/endpoint/quyen/tai khoan), HTML, text -> khong du.
const EXPLICIT_NO_ORIGINAL_RE = /kh[oôố]ng\s+(?:t[oồ]n\s+t[aạ]i|c[oó]|t[iì]m\s+th[aấ]y)\s+h[oồ]\s+s[oơ]\s+g[oố]c/iu;
const MESSAGE_KEYS = ['message', 'msg', 'error', 'errorMessage', 'detail', 'title', 'description'];
const MAX_PAGES = 2000;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Loi co ma an toan (khong mang body/token/tai khoan) de job ghi vao manifest.
function codedError(code, message, httpStatus) {
  const e = new Error(message || code);
  e.code = code;
  if (Number.isInteger(httpStatus)) e.http_status = httpStatus;
  return e;
}
function errorCode(e, fallback) {
  return e && typeof e.code === 'string' && /^[A-Z][A-Z0-9_]{1,63}$/.test(e.code) ? e.code : fallback;
}

/**
 * Mo trinh duyet (giu phien dang nhap), dieu huong toi cong thue, tu dien tai khoan,
 * cho nguoi dung nhap captcha + Dang nhap, roi lay token JWT (bat tu request cua trang).
 * M2-00A: userDataDir BAT BUOC do job truyen (ho so rieng theo phap nhan, da kiem containment);
 * tra them loginFacts chi gom su kien quan sat duoc, phan khong do duoc de UNKNOWN + ly do.
 * @returns {Promise<{context, page, token, loginFacts}>}
 */
async function launchAndLogin({ username, password, userDataDir, onStatus = () => {}, now = Date.now }) {
  if (typeof userDataDir !== 'string' || !path.isAbsolute(userDataDir)) {
    throw codedError('USER_DATA_DIR_REQUIRED');
  }
  const t0 = now();
  const context = await getChromium().launchPersistentContext(userDataDir, {
    headless: false,
    viewport: null,
    args: ['--start-maximized'],
  });

  let capturedToken = null;
  context.on('request', (req) => {
    try {
      const h = req.headers();
      const auth = h['authorization'] || h['Authorization'];
      if (auth) {
        const m = /Bearer\s+([A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+)/.exec(auth);
        if (m) capturedToken = m[1];
      }
    } catch (_) {}
  });

  const page = context.pages()[0] || (await context.newPage());
  onStatus('Dang mo cong thue hoadondientu.gdt.gov.vn ...');
  await page.goto(cfg.LOGIN_URL, { waitUntil: 'domcontentloaded' }).catch(() => {});

  // M2-00A: quan sat token co san TRUOC khi dien form (chi giu trong RAM de so sanh, khong xuat ra dau).
  const tokenAtStart = capturedToken || (await readTokenFromPage(page));

  try {
    await prefillLogin(page, username, password);
    onStatus('Da dien san tai khoan (neu tim thay o). Vui long NHAP CAPTCHA va bam Dang nhap trong cua so trinh duyet.');
  } catch (e) {
    onStatus('Vui long dang nhap thu cong trong cua so trinh duyet (nhap captcha).');
  }

  onStatus('Dang cho dang nhap thanh cong... (sau khi vao duoc he thong, app se tu tiep tuc)');
  const token = await waitForToken(context, () => capturedToken, onStatus);
  if (!token) {
    await context.close().catch(() => {});
    throw codedError('LOGIN_TIMEOUT', 'Chua lay duoc token dang nhap. Hay chac chan da dang nhap vao he thong roi thu lai.');
  }
  onStatus('Da nhan dien dang nhap thanh cong!');

  const waitedSec = Math.round(Math.max(0, now() - t0)) / 1000;
  const loginFacts = {
    // Producer khong doc/khong thay o captcha: khong suy tu token_tai_su_dung.
    captcha_da_go: { trang_thai: 'UNKNOWN', gia_tri: null, ly_do: 'CAPTCHA_INPUT_NOT_OBSERVED_BY_PRODUCER' },
    token_tai_su_dung: tokenAtStart
      ? {
          trang_thai: 'OBSERVED',
          gia_tri: tokenAtStart === token,
          can_cu: tokenAtStart === token ? 'PRECHECK_TOKEN_EQUALS_FINAL' : 'PRECHECK_TOKEN_REPLACED',
        }
      : { trang_thai: 'OBSERVED', gia_tri: false, can_cu: 'NO_TOKEN_AT_PRECHECK' },
    thoi_gian_cho_dang_nhap_giay: { trang_thai: 'OBSERVED', gia_tri: waitedSec, can_cu: 'CLOCK_LAUNCH_TO_TOKEN' },
  };
  return { context, page, token, loginFacts };
}

async function prefillLogin(page, username, password) {
  // Thu dien ngay; neu chua thay form (co the o sau 1 nut) thi bam mo roi thu lai.
  let ok = await tryFill(page, username, password, 8000);
  if (!ok) {
    await clickLoginTrigger(page).catch(() => {});
    ok = await tryFill(page, username, password, 6000);
  }
  if (!ok) throw new Error('Khong tim thay o dang nhap (co the da dang nhap san)');
}

/**
 * Dien tai khoan theo cach tuong thich form React:
 * dat gia tri bang native setter + phat su kien input/change de React nhan.
 */
async function tryFill(page, username, password, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const r = await page
      .evaluate(
        ({ u, p }) => {
          function setVal(el, val) {
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, val);
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
          }
          const vis = (e) => e.offsetParent !== null && !e.disabled && !e.readOnly;
          const inputs = Array.from(document.querySelectorAll('input')).filter(vis);
          const pass = inputs.find((e) => (e.type || '').toLowerCase() === 'password');
          if (!pass) return { ok: false };
          setVal(pass, p);
          const idx = inputs.indexOf(pass);
          let user = null;
          for (let i = idx - 1; i >= 0; i--) {
            const t = (inputs[i].type || 'text').toLowerCase();
            if (['text', 'tel', 'email', 'search', ''].includes(t)) { user = inputs[i]; break; }
          }
          if (!user) user = inputs.find((e) => ['text', 'tel', 'email', ''].includes((e.type || 'text').toLowerCase()));
          if (user) setVal(user, u);
          return { ok: !!user };
        },
        { u: String(username || ''), p: String(password || '') }
      )
      .catch(() => ({ ok: false }));
    if (r && r.ok) return true;
    await sleep(500);
  }
  return false;
}

async function clickLoginTrigger(page) {
  const cands = ['text=/\\bĐăng nh/i', 'button:has-text("Đăng nh")', 'a:has-text("Đăng nh")', '[class*="login" i]'];
  for (const sel of cands) {
    try {
      const loc = page.locator(sel).first();
      if (await loc.isVisible({ timeout: 1000 })) { await loc.click({ timeout: 1500 }); return true; }
    } catch (_) {}
  }
  return false;
}

async function waitForToken(context, getCaptured, onStatus = () => {}) {
  const deadline = Date.now() + cfg.LOGIN_TIMEOUT_MS;
  let i = 0;
  while (Date.now() < deadline) {
    const cap = getCaptured();
    if (cap && cap.split('.').length === 3) return cap;
    for (const p of context.pages()) {
      const t = await readTokenFromPage(p);
      if (t) return t;
    }
    i += 1;
    if (i % 12 === 0) {
      onStatus('Van dang cho... Neu da vao duoc he thong, hay bam menu "Tra cuu" mot lan de trang tai du lieu.');
    }
    await sleep(2000);
  }
  return null;
}

async function readTokenFromPage(p) {
  try {
    if (p.isClosed()) return null;
    return await p.evaluate((keys) => {
      function scan(store) {
        if (!store) return null;
        for (const k of keys) {
          const v = store.getItem(k);
          if (v && String(v).split('.').length === 3) return v;
        }
        for (let i = 0; i < store.length; i++) {
          const key = store.key(i);
          const val = store.getItem(key);
          if (val && typeof val === 'string' && val.split('.').length === 3 && val.length > 40) return val;
        }
        return null;
      }
      try { return scan(window.localStorage) || scan(window.sessionStorage); } catch (_) { return null; }
    }, cfg.TOKEN_STORAGE_KEYS);
  } catch (_) {
    return null;
  }
}

function scopeOf(p) {
  return p.indexOf('/sco-query/') !== -1 ? 'sco-query' : 'query';
}

/** Lay 1 nhom truy van (1 endpoint + 1 ttxly), tu dong phan trang qua con tro "state". */
async function fetchOneGroup(context, token, group, startDate, endDate, action) {
  const scope = scopeOf(group.path);
  const results = [];
  let state = null;
  let pageNo = 0;
  const seenStates = new Set();

  const startP = cfg.SEARCH_TIME_SUFFIX ? `${startDate}T00:00:00` : startDate;
  const endP = cfg.SEARCH_TIME_SUFFIX ? `${endDate}T23:59:59` : endDate;
  let search = `tdlap=ge=${startP};tdlap=le=${endP}`;
  if (group.ttxly !== undefined && group.ttxly !== null && group.ttxly !== '') {
    search += `;ttxly==${group.ttxly}`;
  }

  while (true) {
    pageNo += 1;
    const params = new URLSearchParams();
    params.set('sort', cfg.SORT);
    params.set('size', String(cfg.PAGE_SIZE));
    params.set('search', search);
    if (state) params.set('state', state);

    const url = `${cfg.BASE_URL}${group.path}?${params.toString()}`;
    const resp = await apiGet(context, url, authHeaders(token), { action });
    if (!resp.ok()) {
      // M2-00A: chi giu ma HTTP; khong dua body cong vao thong bao/log.
      throw codedError('HTTP_STATUS', `HTTP ${resp.status()}`, resp.status());
    }
    let data;
    try {
      data = await resp.json();
    } catch (_) {
      throw codedError('RESPONSE_PARSE', 'RESPONSE_PARSE', resp.status());
    }
    // M2-00A FIX01: HTTP 200 sai hinh dang (khong phai object / thieu hoac sai kieu `datas`) KHONG phai bang
    // chung "khong co hoa don" -> nhom LOI, khong tra empty-success.
    if (!data || typeof data !== 'object' || Array.isArray(data) || !Array.isArray(data.datas)) {
      throw codedError('RESPONSE_SHAPE', 'RESPONSE_SHAPE', resp.status());
    }
    const rows = data.datas;
    if (!rows.every((r) => r && typeof r === 'object' && !Array.isArray(r))) {
      throw codedError('RESPONSE_SHAPE', 'RESPONSE_SHAPE', resp.status());
    }
    if (data.state !== undefined && data.state !== null && typeof data.state !== 'string') {
      throw codedError('PAGINATION_STATE_INVALID', 'PAGINATION_STATE_INVALID', resp.status());
    }
    for (const r of rows) {
      r._scope = scope;
      r._ttxly = group.ttxly;
    }
    results.push(...rows);

    const nextState = data.state || null;
    if (!nextState) break; // trang cuoi hop le: khong con con tro (ke ca datas rong)
    // M2-00A FIX02: trang rong nhung van con con tro -> chua chung minh het nguon; khong coi la trang cuoi.
    if (!rows.length) {
      throw codedError('PAGINATION_EMPTY_PAGE_WITH_CURSOR', 'PAGINATION_EMPTY_PAGE_WITH_CURSOR', resp.status());
    }
    // Con tro lap/vong hoac cham tran so trang ma van con trang sau: chua chung minh het nguon -> LOI, khong cat im lang.
    if (nextState === state || seenStates.has(nextState)) {
      throw codedError('PAGINATION_CURSOR_REPEATED', 'PAGINATION_CURSOR_REPEATED', resp.status());
    }
    if (pageNo >= MAX_PAGES) {
      throw codedError('PAGINATION_CAP_REACHED', 'PAGINATION_CAP_REACHED', resp.status());
    }
    seenStates.add(nextState);
    state = nextState;
  }
  return results;
}

/**
 * Lay TAT CA hoa don cua 1 loai (purchase|sold) = gop tat ca cac nhom trong QUERY_GROUPS,
 * loai trung theo (nbmst|khmshdon|khhdon|shdon). Nhom nao loi thi bo qua, khong dung ca phien.
 * M2-00A: tra them nhom[] (ca nhom thanh cong va nhom loi co ma) de manifest ghi coverage trung thuc.
 * @returns {Promise<{records: object[], nhom: object[]}>}
 */
async function fetchAllInvoicesWithGroups(context, token, type, startDate, endDate, onStatus = () => {}) {
  const groups = cfg.QUERY_GROUPS[type] || [];
  const label = type === 'purchase' ? 'Mua vao' : 'Ban ra';
  const action = labelAction('search', type);
  const map = new Map();
  const nhom = [];

  for (let gi = 0; gi < groups.length; gi++) {
    const group = groups[gi];
    const tag = `${scopeOf(group.path) === 'sco-query' ? 'MTT' : 'thuong'}/ttxly=${group.ttxly}`;
    const row = {
      thu_tu: gi + 1,
      path: group.path,
      scope: scopeOf(group.path),
      ttxly: group.ttxly === undefined ? null : group.ttxly,
      trang_thai: 'OK',
      so_ban_ghi: null,
      so_moi: null,
      loi: null,
    };
    try {
      const rows = await fetchOneGroup(context, token, group, startDate, endDate, action);
      let added = 0;
      for (const r of rows) {
        const key = [r.nbmst, r.khmshdon, r.khhdon, r.shdon].join('|');
        if (!map.has(key)) {
          r._type = type;
          r._group_ordinal = gi + 1;
          map.set(key, r);
          added += 1;
        }
      }
      row.so_ban_ghi = rows.length;
      row.so_moi = added;
      onStatus(`[${label}] nhom ${tag}: ${rows.length} HD (+${added} moi, tong ${map.size})`);
    } catch (e) {
      row.trang_thai = 'LOI';
      row.loi = { code: errorCode(e, 'LIST_FAILED'), http_status: Number.isInteger(e && e.http_status) ? e.http_status : null };
      onStatus(`[${label}] nhom ${tag}: bo qua (${row.loi.code}${row.loi.http_status ? ' HTTP ' + row.loi.http_status : ''})`);
    }
    nhom.push(row);
  }
  return { records: Array.from(map.values()), nhom };
}

/** Giu API cu: chi tra danh sach ban ghi (canonical dedupe khong doi). */
async function fetchAllInvoices(context, token, type, startDate, endDate, onStatus = () => {}) {
  const res = await fetchAllInvoicesWithGroups(context, token, type, startDate, endDate, onStatus);
  return res.records;
}

function isJsonText(s) {
  if (typeof s !== 'string' || !s.trim()) return false;
  try { JSON.parse(s); return true; } catch (_) { return false; }
}

/** true chi khi body la JSON object co truong thong bao neu ro "khong ton tai/khong co/khong tim thay ho so goc". */
function explicitNoOriginal(body) {
  if (typeof body !== 'string' || !body.trim() || body.length > 64 * 1024) return false;
  let v;
  try { v = JSON.parse(body); } catch (_) { return false; }
  if (!v || typeof v !== 'object' || Array.isArray(v)) return false;
  return MESSAGE_KEYS.some((k) => typeof v[k] === 'string' && EXPLICIT_NO_ORIGINAL_RE.test(v[k].normalize('NFC')));
}

/**
 * Tai file XML goc cua 1 hoa don, dung dung he (query / sco-query) theo _scope cua ban ghi.
 * M2-00A: ket qua that bai mang kind/status/noOriginalBody/bodyIsJson de job phan loai co can cu;
 * job khong ghi `error` (body cong) ra bat ky output nao.
 */
async function exportInvoiceXml(context, token, record) {
  await sleep(cfg.THROTTLE_MS || 0); // gian nhip de tranh bi chan
  const scope = record._scope === 'sco-query' ? 'sco-query' : 'query';
  const exportPath = cfg.EXPORT_XML[scope] || cfg.EXPORT_XML.query;
  const params = new URLSearchParams();
  for (const key of cfg.EXPORT_XML_PARAMS) {
    if (record[key] !== undefined && record[key] !== null) params.set(key, String(record[key]));
  }
  const url = `${cfg.BASE_URL}${exportPath}?${params.toString()}`;
  try {
    // Hoa don CO MA (ky hieu bat dau bang 'C', gom ca may tinh tien / ttxly 5,8) -> co XML goc -> RETRY khi loi tam thoi.
    // Hoa don KHONG MA (ky hieu bat dau bang 'K', hoac ttxly 6) -> thuong khong co XML goc -> KHONG retry, chi ghi Excel.
    const kyHieu = String(record.khhdon || '').trim().toUpperCase();
    const khongMa = kyHieu.startsWith('K') || record._ttxly === 6;
    const resp = await apiGet(context, url, authHeaders(token), {
      binary: true,
      action: labelAction('export', record._type),
      maxRetry: khongMa ? 0 : (cfg.RETRY_XML != null ? cfg.RETRY_XML : 3),
      // an toan: du la loai nao, neu cong thue bao "khong ton tai ho so goc" thi dung ngay
      noRetryIfBody: NO_ORIGIN_RE,
    });
    if (!resp.ok()) {
      const body = await safeText(resp);
      return { ok: false, url, status: resp.status(), kind: 'HTTP', noOriginalBody: explicitNoOriginal(body), bodyIsJson: isJsonText(body), error: body };
    }
    const buffer = await resp.body();
    if (!buffer || buffer.length === 0) {
      const body = await safeText(resp);
      return {
        ok: false, url, status: resp.status(), kind: 'EMPTY_BODY',
        noOriginalBody: explicitNoOriginal(body), bodyIsJson: isJsonText(body),
        error: body || 'Khong co du lieu XML goc',
      };
    }
    return { ok: true, buffer, url, status: resp.status(), kind: 'PAYLOAD' };
  } catch (e) {
    return { ok: false, url, status: 0, kind: 'EXCEPTION', noOriginalBody: false, bodyIsJson: false, error: e.message };
  }
}

/* =====================================================================
 * GOI API BEN TRONG TRINH DUYET (page.fetch) - de request mang dung "van tay"
 * cua trinh duyet that, tranh bi WAF cong thue chan (HTTP 403 "hanh vi khong hop le").
 * Vi API cung origin voi trang (hoadondientu.gdt.gov.vn) nen khong vuong CORS.
 * Tra ve doi tuong "shim" co cac ham giong Playwright APIResponse:
 *   status(), ok(), json(), text(), body()
 * ===================================================================== */
function livePage(context) {
  const pages = context.pages().filter((p) => !p.isClosed());
  return pages[0] || null;
}

async function apiGet(context, url, headers, opts = {}) {
  const binary = !!opts.binary;
  const maxRetry = (opts.maxRetry != null) ? opts.maxRetry : (cfg.RETRY_429 || 0);
  const noRetryIfBody = opts.noRetryIfBody || null;
  const base = cfg.RETRY_DELAY_MS || 3000;
  let attempt = 0;

  // Bo sung cac header rieng ma WAF cong thue yeu cau (giong het trang web that).
  const finalHeaders = Object.assign(
    {
      'accept-language': 'vi',
      'end-point': END_POINT,
      'request-id': newRequestId(),
    },
    headers || {}
  );
  if (opts.action) finalHeaders['action'] = opts.action;

  while (true) {
    const page = livePage(context);
    if (!page) throw codedError('BROWSER_CLOSED', 'Trinh duyet da dong, khong the goi API.');

    let out;
    try {
      out = await page.evaluate(
        async ({ url, headers, binary }) => {
          try {
            const r = await fetch(url, { method: 'GET', headers, credentials: 'include' });
            const ct = (r.headers.get('content-type') || '');
            // Chi lay du lieu nhi phan khi tai thanh cong VA khong phai JSON (tuc la file XML/zip that).
            // Neu loi hoac tra ve JSON (vd: "khong ton tai ho so goc") -> lay TEXT de doc thong bao.
            if (binary && r.ok && ct.indexOf('json') === -1) {
              const ab = await r.arrayBuffer();
              const bytes = new Uint8Array(ab);
              let s = '';
              const CH = 0x8000;
              for (let i = 0; i < bytes.length; i += CH) {
                s += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
              }
              return { status: r.status, b64: btoa(s) };
            }
            return { status: r.status, body: await r.text() };
          } catch (e) {
            return { status: 0, body: '', err: String(e && e.message || e) };
          }
        },
        { url, headers: finalHeaders, binary }
      );
    } catch (e) {
      out = { status: 0, body: '', err: e.message };
    }

    const s = out.status || 0;
    // Loi nghiep vu dut khoat (vd: khong ton tai ho so goc) -> tra ve ngay, KHONG thu lai.
    const bodyStr = out.body || out.err || '';
    if (noRetryIfBody && bodyStr && noRetryIfBody.test(bodyStr)) return shimResponse(out, binary);
    const retryable = s === 429 || s >= 500 || s === 0;
    if (!retryable || attempt >= maxRetry) return shimResponse(out, binary);
    attempt += 1;
    await sleep(base * attempt);
  }
}

function shimResponse(out, binary) {
  const status = out.status || 0;
  return {
    status: () => status,
    ok: () => status >= 200 && status < 300,
    json: async () => JSON.parse(out.body || 'null'),
    text: async () => (out.body != null ? out.body : (out.err || '')),
    body: async () => Buffer.from(out.b64 || '', 'base64'),
  };
}

function authHeaders(token) {
  return { Authorization: `Bearer ${token}`, Accept: 'application/json, text/plain, */*' };
}
async function safeText(resp) {
  try { return await resp.text(); } catch (_) { return ''; }
}

module.exports = {
  launchAndLogin,
  fetchAllInvoices,
  fetchAllInvoicesWithGroups,
  exportInvoiceXml,
  _internal: { explicitNoOriginal, MAX_PAGES },
};
