'use strict';
// Chạy: node --test tests/g2_31a.cjs (hoặc node tests/g2_31a.cjs).
// Không mạng, không server, không CSDL; tất cả là dữ liệu DEMO.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const SDK = require('../src/kho_tri_thuc/sdk_core/trinh_duyet.js');
const sdkPath = path.join(__dirname, '../src/kho_tri_thuc/sdk_core/trinh_duyet.js');
const html = fs.readFileSync(path.join(__dirname, '../src/kho_tri_thuc/core/ui/index.html'), 'utf8');
const ctx = { nguoi_dung_id: 'DEMO-NGUOI-A', phap_nhan_id: 'DEMO-PN-A', module: 'crm', man: 'bao_gia' };
const response = (status, body, headers = {}) => ({
  status, ok: status >= 200 && status < 300, headers: new Headers(headers),
  json: async () => structuredClone(body)
});
function tao(fetch, options = {}) {
  const sdk = SDK.tao({ fetch, tao_ma: () => 'DEMO-TRACE', ...options });
  sdk.api.doi_ngu_canh(ctx); sdk.api.gan_csrf('DEMO-CSRF'); return sdk;
}
const lenh = (more = {}) => ({ phuong_thuc: 'PATCH', duong_dan: '/api/v1/module/crm/bao-gia/DEMO-1',
  du_lieu: { row_version: '9007199254740993', expected_revision: 3, ghi_chu: 'Nháp DEMO' },
  khoa: 'DEMO-KHOA-1', ...more });
function doi() { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; }

test('202: polling theo Retry-After, HTTP 200 running chưa kết thúc; giữ CSRF/context', async () => {
  const calls = [], waits = [], states = [];
  const queue = [response(202, { viec_id: 'DEMO-VIEC', trang_thai: 'queued' }, {
    Location: '/api/v1/viec/DEMO-VIEC', 'Retry-After': '3' }),
  response(200, { trang_thai: 'running' }, { 'Retry-After': '5' }),
  response(200, { trang_thai: 'waiting_input' }),
  response(200, { trang_thai: 'succeeded', ket_qua_ids: ['DEMO-KQ'] })];
  const sdk = tao(async (url, init) => { calls.push([url, init]); return queue.shift(); },
    { cho: async ms => waits.push(ms) });
  const result = await sdk.api.goi(lenh({ theo_doi: true, khi_doi: s => states.push(s.trang_thai) }));
  assert.equal(result.trang_thai, 'succeeded');
  assert.deepEqual(waits, [3000, 5000, 2000]);
  assert.deepEqual(states, ['running', 'waiting_input', 'succeeded']);
  assert.equal(calls[0][1].headers['X-CSRF-Token'], 'DEMO-CSRF');
  assert.equal(calls[0][1].headers['Idempotency-Key'], 'DEMO-KHOA-1');
  for (const [url, init] of calls) {
    assert.ok(url.startsWith('/api/v1/'));
    assert.equal(init.headers['X-Phap-Nhan-Id'], 'DEMO-PN-A');
    assert.equal(init.headers['X-Module-Ma'], 'crm');
    assert.equal(init.headers['X-Request-Id'], 'DEMO-TRACE');
    assert.equal(init.redirect, 'error'); assert.equal(init.credentials, 'same-origin');
  }
  assert.equal(calls[1][1].method, 'GET');
  assert.equal(calls[1][1].headers['Idempotency-Key'], undefined);
});

test('biên nhận 202 dùng riêng viec.theo_doi; Retry-After dạng ngày và giá trị lỗi', async () => {
  const waits = [], now = Date.parse('2026-10-31T00:00:00Z');
  const queue = [response(202, { viec_id: 'DEMO-VIEC' }, { 'Retry-After': 'Sat, 31 Oct 2026 00:00:07 GMT' }),
    response(200, { trang_thai: 'running' }, { 'Retry-After': 'khong-hop-le' }),
    response(200, { trang_thai: 'interrupted' })];
  const sdk = tao(async () => queue.shift(), { dong_ho: () => now, cho: async ms => waits.push(ms) });
  const receipt = await sdk.api.goi(lenh());
  assert.equal(receipt.viec_id, 'DEMO-VIEC'); assert.equal(queue.length, 2);
  assert.equal((await sdk.viec.theo_doi(receipt.viec_id)).trang_thai, 'interrupted');
  assert.deepEqual(waits, [7000, 2000]);
});

for (const state of ['failed', 'cancelled', 'interrupted']) test(`trạng thái ${state} giữ đúng, không tự thử lại`, async () => {
  let calls = 0;
  const sdk = tao(async () => { calls++; return response(200, { trang_thai: state }); });
  assert.equal((await sdk.viec.theo_doi('DEMO-VIEC')).trang_thai, state); assert.equal(calls, 1);
});

test('đề nghị hủy tiếp tục polling đến xác nhận cuối', async () => {
  const calls = [], queue = [response(202, { viec_id: 'DEMO-VIEC', trang_thai: 'cancel_requested' }),
    response(200, { trang_thai: 'cancel_requested' }), response(200, { trang_thai: 'cancelled' })];
  const sdk = tao(async (url, init) => { calls.push([url, init]); return queue.shift(); }, { cho: async () => {} });
  await sdk.viec.huy('DEMO-VIEC', 'DEMO-HUY');
  assert.equal((await sdk.viec.theo_doi('DEMO-VIEC')).trang_thai, 'cancelled');
  assert.equal(calls[0][0], '/api/v1/viec/DEMO-VIEC/huy'); assert.equal(calls[0][1].method, 'POST');
  assert.equal(calls.length, 3);
});

test('409 giữ nháp, giữ nguyên row_version và expected_revision; không ghi đè hoặc tự gửi lại', async () => {
  let calls = 0, sent;
  const sdk = tao(async (_, init) => { calls++; sent = JSON.parse(init.body); return response(409,
    { ma: 'XUNG_DOT_PHIEN_BAN', request_id: 'DEMO-REQUEST', chi_tiet: [{ truong: 'ghi_chu', ma: 'SAI' }] }); });
  const request = lenh();
  await assert.rejects(sdk.api.goi(request), e => {
    assert.equal(e.status, 409); assert.equal(e.request_id, 'DEMO-REQUEST');
    assert.deepEqual(e.nhap, request.du_lieu); assert.match(e.message, /Bản nháp/); return true;
  });
  request.du_lieu.ghi_chu = 'Đã sửa trên form';
  assert.equal(sdk.api.doc_nhap('DEMO-KHOA-1').ghi_chu, 'Nháp DEMO');
  assert.equal(sent.row_version, '9007199254740993'); assert.equal(sent.expected_revision, 3); assert.equal(calls, 1);
  const copy = sdk.api.doc_nhap('DEMO-KHOA-1'); copy.ghi_chu = 'Không đổi bản giữ';
  assert.equal(sdk.api.doc_nhap('DEMO-KHOA-1').ghi_chu, 'Nháp DEMO');
});

test('mất mạng gửi lại đúng khóa/body; khác nội dung hoặc context bị chặn', async () => {
  const calls = [];
  const sdk = tao(async (_, init) => { calls.push(init); if (calls.length === 1) throw new TypeError('DEMO mat mang');
    return response(200, { da_luu: true }); });
  await assert.rejects(sdk.api.goi(lenh()), TypeError);
  assert.deepEqual(await sdk.api.goi(lenh()), { da_luu: true });
  assert.equal(calls[0].body, calls[1].body);
  assert.equal(calls[0].headers['Idempotency-Key'], calls[1].headers['Idempotency-Key']);
  await assert.rejects(sdk.api.goi(lenh({ du_lieu: { row_version: '8' } })), { ma: 'KHOA_KHAC_NOI_DUNG' });
  sdk.api.doi_ngu_canh({ ...ctx, phap_nhan_id: 'DEMO-PN-B' });
  await assert.rejects(sdk.api.goi(lenh()), { ma: 'KHOA_KHAC_NOI_DUNG' }); assert.equal(calls.length, 2);
});

for (const next of [
  { ...ctx, nguoi_dung_id: 'DEMO-NGUOI-B' },
  { ...ctx, phap_nhan_id: 'DEMO-PN-B' },
  { ...ctx, nguoi_dung_id: 'DEMO-NGUOI-B', phap_nhan_id: 'DEMO-PN-B' },
  {}
]) test(`nháp 409 không lộ hoặc sống lại sau đổi chủ ${JSON.stringify(next)}`, async () => {
  const sdk = tao(async () => response(409, { ma: 'XUNG_DOT_PHIEN_BAN' }));
  await assert.rejects(sdk.api.goi(lenh()), { ma: 'XUNG_DOT_PHIEN_BAN' });
  assert.deepEqual(sdk.api.doc_nhap('DEMO-KHOA-1'), lenh().du_lieu);
  sdk.api.doi_ngu_canh(next);
  assert.equal(sdk.api.doc_nhap('DEMO-KHOA-1'), undefined);
  sdk.api.doi_ngu_canh(ctx);
  assert.equal(sdk.api.doc_nhap('DEMO-KHOA-1'), undefined);
});

test('đọc nháp kiểm pháp nhân/module sở hữu; đổi màn cùng chủ giữ nháp để đối chiếu', async () => {
  const sdk = tao(async () => response(409, { ma: 'XUNG_DOT_PHIEN_BAN' }));
  await assert.rejects(sdk.api.goi(lenh()), { ma: 'XUNG_DOT_PHIEN_BAN' });
  sdk.api.doi_ngu_canh({ ...ctx, man: 'hop_dong' });
  assert.deepEqual(sdk.api.doc_nhap('DEMO-KHOA-1'), lenh().du_lieu);
  sdk.api.doi_ngu_canh({ ...ctx, module: 'module_khac' });
  assert.equal(sdk.api.doc_nhap('DEMO-KHOA-1'), undefined);
  sdk.api.doi_ngu_canh(ctx);
  assert.deepEqual(sdk.api.doc_nhap('DEMO-KHOA-1'), lenh().du_lieu);

  // Request chỉ rõ pháp nhân không được cho context chưa chọn pháp nhân đọc nháp.
  const unselected = SDK.tao({ fetch: async () => response(409, { ma: 'XUNG_DOT_PHIEN_BAN' }),
    tao_ma: () => 'DEMO-TRACE' });
  unselected.api.doi_ngu_canh({ nguoi_dung_id: ctx.nguoi_dung_id, module: ctx.module });
  unselected.api.gan_csrf('DEMO-CSRF');
  await assert.rejects(unselected.api.goi(lenh({ phap_nhan_id: ctx.phap_nhan_id })),
    { ma: 'XUNG_DOT_PHIEN_BAN' });
  assert.equal(unselected.api.doc_nhap('DEMO-KHOA-1'), undefined);
});

test('409 đang xử lý chờ Retry-After, gửi đúng ý định ban đầu dù form đổi', async () => {
  const calls = [], waits = [], request = lenh();
  const sdk = tao(async (url, init) => {
    calls.push([url, init]);
    if (calls.length === 1) return response(409, { ma: 'YEU_CAU_DANG_XU_LY' }, { 'Retry-After': '4' });
    return response(200, { da_luu: true });
  }, { cho: async ms => {
    waits.push(ms); request.du_lieu.ghi_chu = 'Sửa form khi đang chờ'; request.module = 'module_khac';
    request.duong_dan = '/api/v1/module/khac/luu';
  } });
  await sdk.api.goi(request);
  assert.deepEqual(waits, [4000]); assert.equal(calls.length, 2);
  assert.equal(calls[0][0], calls[1][0]); assert.equal(calls[0][1].body, calls[1][1].body);
  assert.equal(calls[1][1].headers['Idempotency-Key'], 'DEMO-KHOA-1');
  assert.equal(calls[1][1].headers['X-Module-Ma'], 'crm');
});

test('khóa khác nội dung ở backend không bị gọi lại hoặc coi là CAS', async () => {
  let calls = 0;
  const sdk = tao(async () => { calls++; return response(409, { ma: 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG' }); });
  await assert.rejects(sdk.api.goi(lenh()), e => {
    assert.equal(e.ma, 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG'); assert.ok(!e.message.includes('Dữ liệu đã thay đổi')); return true;
  });
  assert.equal(calls, 1);
});

test('theo dõi biên nhận giữ pháp nhân/module được chỉ rõ trên request', async () => {
  const calls = [], queue = [response(202, { viec_id: 'DEMO-VIEC' }), response(200, { trang_thai: 'succeeded' })];
  const sdk = SDK.tao({ fetch: async (_, init) => { calls.push(init); return queue.shift(); },
    tao_ma: () => 'DEMO', cho: async () => {} });
  sdk.api.gan_csrf('DEMO-CSRF');
  await sdk.api.goi(lenh({ phap_nhan_id: 'DEMO-PN-A', module: 'crm' }));
  await sdk.viec.theo_doi('DEMO-VIEC');
  assert.equal(calls[1].headers['X-Phap-Nhan-Id'], 'DEMO-PN-A');
  assert.equal(calls[1].headers['X-Module-Ma'], 'crm');
});

test('việc không rõ trạng thái hoặc Location khác mã phải dừng', async () => {
  const sdk = tao(async () => response(200, { trang_thai: 'khong_ro' }));
  await assert.rejects(sdk.viec.theo_doi('DEMO-VIEC'), { ma: 'PHAN_HOI_KHONG_HOP_LE' });
  const other = tao(async () => response(202, { viec_id: 'DEMO-VIEC' }, { Location: '/api/v1/viec/DEMO-KHAC' }));
  await assert.rejects(other.api.goi(lenh()), { ma: 'PHAN_HOI_KHONG_HOP_LE' });
});

for (const field of ['phap_nhan_id', 'nguoi_dung_id', 'man']) test(`đổi ${field} bỏ response cũ dù transport không nhận abort`, async () => {
  const gate = doi(); let signal;
  const sdk = tao(async (_, init) => { signal = init.signal; return gate.promise; });
  const request = sdk.api.goi({ duong_dan: '/api/v1/tai-lieu' });
  const rejected = assert.rejects(request, { ma: 'NGU_CANH_DA_DOI' });
  sdk.api.doi_ngu_canh({ ...ctx, [field]: 'DEMO-MOI' }); assert.equal(signal.aborted, true);
  gate.resolve(response(200, { bi_mat_cu: 'DEMO' })); await rejected;
});

test('đổi context trong lúc đọc JSON không phát phản hồi hoặc cập nhật CSRF cũ', async () => {
  const gate = doi(), entered = doi();
  const sdk = tao(async () => ({ ...response(200, null), json: () => { entered.resolve(); return gate.promise; } }));
  const promise = sdk.api.goi({ duong_dan: '/api/v1/phien' });
  const rejected = assert.rejects(promise, { ma: 'NGU_CANH_DA_DOI' });
  await entered.promise; sdk.api.doi_ngu_canh({ ...ctx, nguoi_dung_id: 'DEMO-NGUOI-B' });
  gate.resolve({ csrf_token: 'DEMO-TOKEN-CU' }); await rejected;
  await assert.rejects(sdk.api.goi(lenh()), { ma: 'THIEU_CSRF' });
});

test('đổi context trong Retry-After không poll/callback cũ', async () => {
  const gate = doi(), entered = doi(); let calls = 0, callbacks = 0;
  const sdk = tao(async () => { calls++; return response(202, { viec_id: 'DEMO-VIEC' }); },
    { cho: () => { entered.resolve(); return gate.promise; } });
  const promise = sdk.api.goi(lenh({ theo_doi: true, khi_doi: () => callbacks++ }));
  const rejected = assert.rejects(promise, { ma: 'NGU_CANH_DA_DOI' });
  await entered.promise; sdk.api.doi_ngu_canh({ ...ctx, man: 'DEMO-MAN-MOI' }); gate.resolve();
  await rejected; assert.equal(calls, 1); assert.equal(callbacks, 0);
});

test('caller abort dừng theo dõi', async () => {
  const external = new AbortController(), gate = doi(); let calls = 0;
  const sdk = tao(async () => { calls++; return gate.promise; });
  const promise = sdk.viec.theo_doi('DEMO-VIEC', { signal: external.signal });
  const rejected = assert.rejects(promise, { name: 'AbortError' });
  external.abort(); gate.resolve(response(200, { trang_thai: 'succeeded' })); await rejected;
  assert.equal(calls, 1);
});

test('chặn URL ngoài Core, traversal, encoded path và Location độc hại trước khi gọi', async () => {
  const calls = [];
  const sdk = tao(async url => { calls.push(url); return response(202, { viec_id: 'DEMO-VIEC' },
    { Location: 'https://evil.invalid/api/v1/viec/DEMO-VIEC' }); });
  for (const url of ['https://evil.invalid/api/v1/x', '//evil.invalid/api/v1/x', '/api/crm/x',
    '/api/v1/../../x', '/api/v1/%2e%2e/x', '/api/v1/%252e%252e/x', '/api/v1/x\\y',
    '/api/v1/x#abc', '/api/v1//x', '/api/v1/x\n']) {
    await assert.rejects(sdk.api.goi({ duong_dan: url }), { ma: 'DUONG_DAN_KHONG_HOP_LE' });
  }
  assert.equal(calls.length, 0);
  await assert.rejects(sdk.api.goi(lenh()), { ma: 'DUONG_DAN_KHONG_HOP_LE' }); assert.equal(calls.length, 1);
});

test('response redirect bị từ chối, không phát data', async () => {
  const sdk = tao(async () => ({ ...response(200, { secret: 'DEMO' }), redirected: true }));
  await assert.rejects(sdk.api.goi({ duong_dan: '/api/v1/tai-lieu' }), { ma: 'CHUYEN_HUONG_BI_CHAN' });
});

test('phiên cấp CSRF trong bộ nhớ; thiếu khóa, CAS số và context khác bị từ chối', async () => {
  const calls = [];
  const sdk = SDK.tao({ tao_ma: () => 'DEMO', fetch: async (_, init) => {
    calls.push(init); return response(200, { csrf_token: 'DEMO-CSRF-MOI' }); } });
  sdk.api.doi_ngu_canh(ctx);
  await assert.rejects(sdk.api.goi(lenh()), { ma: 'THIEU_CSRF' });
  await sdk.api.goi({ duong_dan: '/api/v1/phien' });
  await sdk.api.goi(lenh()); assert.equal(calls[1].headers['X-CSRF-Token'], 'DEMO-CSRF-MOI');
  await assert.rejects(sdk.api.goi(lenh({ khoa: undefined })), { ma: 'THIEU_KHOA' });
  await assert.rejects(sdk.api.goi(lenh({ du_lieu: { row_version: 7 } })), { ma: 'PHIEN_BAN_KHONG_HOP_LE' });
  await assert.rejects(sdk.api.goi(lenh({ phap_nhan_id: 'DEMO-PN-B' })), { ma: 'SAI_NGU_CANH' });
  assert.equal(calls.length, 2);
});

for (const duong_dan of ['/api/v1/phien', '/api/v1/phien?kiem_tra=1']) {
  test(`đăng xuất ${duong_dan} miễn khóa chống trùng, vẫn gửi CSRF và cookie cùng nguồn`, async () => {
    const calls = [];
    const sdk = tao(async (url, init) => { calls.push([url, init]); return response(204); });
    assert.equal(await sdk.api.goi({ phuong_thuc: 'DELETE', duong_dan }), null);
    assert.equal(calls.length, 1);
    assert.equal(calls[0][0], duong_dan);
    assert.equal(calls[0][1].method, 'DELETE');
    assert.equal(calls[0][1].headers['X-CSRF-Token'], 'DEMO-CSRF');
    assert.equal(calls[0][1].headers['Idempotency-Key'], undefined);
    assert.equal(calls[0][1].credentials, 'same-origin');
    sdk.api.gan_csrf('');
    await assert.rejects(sdk.api.goi({ phuong_thuc: 'DELETE', duong_dan }), { ma: 'THIEU_CSRF' });
    assert.equal(calls.length, 1);
  });
}

test('ngoại lệ khóa chỉ cho đăng nhập/đăng xuất, không áp cho ghi khác hoặc đường dẫn gần giống', async () => {
  let calls = 0;
  const sdk = tao(async () => { calls++; return response(200, {}); });
  await sdk.api.goi({ phuong_thuc: 'POST', duong_dan: '/api/v1/phien' });
  for (const [phuong_thuc, duong_dan] of [
    ['PATCH', '/api/v1/phien'], ['PUT', '/api/v1/phien'],
    ['DELETE', '/api/v1/phien/khac'], ['DELETE', '/api/v1/module/crm/bao-gia/DEMO-1']
  ]) await assert.rejects(sdk.api.goi({ phuong_thuc, duong_dan }), { ma: 'THIEU_KHOA' });
  assert.equal(calls, 1);
});

test('phân trang chuyển nguyên con trỏ opaque và giữ context', async () => {
  let called;
  const sdk = tao(async (url, init) => { called = [url, init]; return response(200,
    { danh_sach: [], con_tiep: true, con_tro_tiep: 'DEMO+/=' }); });
  const result = await sdk.api.goi({ duong_dan: '/api/v1/tai-lieu?kich_thuoc_trang=25&con_tro=DEMO%2B%2F%3D' });
  assert.equal(result.con_tro_tiep, 'DEMO+/='); assert.match(called[0], /con_tro=DEMO%2B%2F%3D$/);
});

// DOM tối thiểu: kiểm hành vi DOM thật mà SDK dùng, không giả kết quả renderer.
class Element {
  constructor(tag, doc) { this.tagName = tag; this.ownerDocument = doc; this.children = []; this.attrs = {};
    this.events = {}; this.hidden = false; this._text = ''; }
  set textContent(text) { this._text = String(text); this.children = []; }
  get textContent() { return this._text + this.children.map(c => c.textContent).join(' '); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this._text = ''; this.children = nodes; }
  setAttribute(key, value) { this.attrs[key] = value; }
  addEventListener(event, fn) { this.events[event] = fn; }
  click() { this.events.click?.(); }
}
function documentGia() {
  const doc = { createElement: tag => new Element(tag, doc) };
  const ids = {};
  doc.getElementById = id => ids[id] ||= new Element('div', doc);
  return doc;
}
function find(root, predicate) { return [root, ...root.children.flatMap(c => find(c, () => true))].filter(predicate); }
function button(root, title) { return find(root, e => e.tagName === 'button' && e.attrs.title === title).at(-1); }
const khaiBao = { module: [{ ma: 'crm', ten: 'Hợp đồng bán hàng', so: 0,
  phan: [{ ma: 'bao_gia', ten: 'Báo giá', so: 2, canh_bao: true },
    { ma: 'hop_dong', ten: 'Hợp đồng', so: 8, day_du: false }],
  the: [{ ma: 'den_han', nhan: 'Đến hạn', so: 3, loc: { phan: 'bao_gia', tham_so: { den_han: true } } }]
}] };

test('khung hai cấp chỉ dựng khai báo được cấp, badge 0 ẩn, thiếu tổng hiện rõ, mở đúng lọc', async () => {
  const doc = documentGia(), root = doc.createElement('div'), opened = [], contexts = [];
  const view = SDK.khung.dung(root, khaiBao, { khi_mo: e => opened.push(e), khi_doi_man: c => contexts.push(c) });
  assert.equal(find(root, e => e.className === 'core-badge').length, 0);
  assert.ok(!root.textContent.includes('Quản trị'));
  button(root, 'Hợp đồng bán hàng').click();
  assert.match(root.textContent, /2 quá hạn/); assert.match(root.textContent, /Chưa đủ số liệu/);
  assert.ok(!root.textContent.includes('8'));
  button(root, 'Đến hạn').click(); await Promise.resolve();
  assert.equal(opened.length, 1); assert.equal(opened[0].module, 'crm');
  assert.deepEqual(opened[0].phan.loc, khaiBao.module[0].the[0].loc);
  assert.ok(view.noi_dung.textContent.includes('Đến hạn'));
  assert.deepEqual(contexts.at(-1), { module: 'crm', man: 'den_han' });
  button(root, 'Báo giá').click(); await Promise.resolve();
  assert.equal(opened[0].signal.aborted, true);
  view.dung(); assert.equal(opened[1].signal.aborted, true);
});

test('tìm nhanh không thêm quyền; nội dung tên được dựng bằng text', () => {
  const doc = documentGia(), root = doc.createElement('div');
  SDK.khung.dung(root, { module: [{ ma: 'demo', ten: '<img src=x onerror=alert(1)>', phan: [] }] });
  assert.ok(root.textContent.includes('<img src=x onerror=alert(1)>'));
  assert.equal(find(root, e => e.tagName === 'img').length, 0);
  const input = find(root, e => e.tagName === 'input')[0]; input.value = 'Không có'; input.events.input();
  assert.match(root.textContent, /Chưa có nghiệp vụ phù hợp/);
});

test('nhận khai báo UI-2 module/phan/the; khong_quyen không dựng nghiệp vụ', () => {
  const doc = documentGia(), root = doc.createElement('div');
  const m = khaiBao.module[0];
  const data = { module: { ma: m.ma, ten: m.ten }, phan: m.phan, the: m.the };
  SDK.khung.dung(root, data); button(root, m.ten).click();
  assert.ok(button(root, 'Báo giá')); assert.ok(button(root, 'Đến hạn'));
  SDK.khung.dung(root, { ...data, khong_quyen: true });
  assert.ok(!root.textContent.includes(m.ten));
});

test('thông báo giữ nháp, request_id trong details; không phản chiếu giá trị lỗi máy chủ', () => {
  const doc = documentGia(), root = doc.createElement('div');
  SDK.thong_bao.loi(root, { status: 409, ma: 'XUNG_DOT_PHIEN_BAN', request_id: 'DEMO-REQUEST', message: 'CANARY-BI-MAT' });
  assert.match(root.textContent, /Bản nháp được giữ/); assert.ok(!root.textContent.includes('CANARY-BI-MAT'));
  assert.equal(find(root, e => e.tagName === 'details').length, 1);
  assert.match(root.textContent, /DEMO-REQUEST/);
});

test('Shell tích hợp SDK: DEMO chỉ khi la_demo true, đổi pháp nhân/đăng xuất xóa nội dung cũ', () => {
  const doc = documentGia(), events = {};
  const window = { addEventListener: (type, fn) => { events[type] = fn; } };
  const context = vm.createContext({ window, document: doc, KttCore: SDK });
  const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m => m[1]).filter(s => s.trim());
  assert.equal(scripts.length, 1); vm.runInContext(scripts[0], context); events.DOMContentLoaded();
  const params = { khai_bao_da_loc_quyen: khaiBao, nguoi_dung_id: 'DEMO-NGUOI', csrf_token: 'DEMO-CSRF' };
  window.KttShell.dung({ ...params, phap_nhan: { id: 'DEMO-A', ten: 'Công ty DEMO', la_demo: true } });
  assert.equal(doc.getElementById('demo').textContent, 'DEMO'); assert.equal(doc.getElementById('demo').hidden, false);
  window.KttShell.dung({ ...params, khai_bao_da_loc_quyen: { module: [] },
    phap_nhan: { id: 'DEMO-B', ten: 'Công ty B', la_demo: false } });
  assert.equal(doc.getElementById('demo').hidden, true); assert.equal(doc.getElementById('demo').textContent, '');
  assert.ok(!doc.getElementById('khung').textContent.includes('Hợp đồng bán hàng'));
  window.KttShell.dung({ ...params, phap_nhan: null });
  assert.match(doc.getElementById('phap-nhan').textContent, /Chưa chọn/);
  assert.ok(!doc.getElementById('khung').textContent.includes('Hợp đồng bán hàng'));
  SDK.khung.nhan_demo(doc.getElementById('demo'), { la_demo: 'false' });
  assert.equal(doc.getElementById('demo').hidden, true);
});

test('SDK browser không đọc/ghi storage hoặc cookie; asset SDK của Shell tồn tại', async () => {
  const source = fs.readFileSync(sdkPath, 'utf8');
  const forbidden = () => { throw new Error('Không được truy cập kho trình duyệt'); };
  const context = { fetch: async () => response(200, {}), AbortController, DOMException, setTimeout, clearTimeout,
    crypto: require('node:crypto').webcrypto };
  for (const name of ['localStorage', 'sessionStorage', 'indexedDB']) Object.defineProperty(context, name, { get: forbidden });
  vm.runInNewContext(source, context);
  assert.equal(typeof context.KttCore.tao, 'function');
  const instance = context.KttCore.tao();
  await instance.api.goi({ duong_dan: '/api/v1/phien' });
  instance.api.gan_csrf('DEMO-CSRF');
  await instance.api.goi(lenh());
  const src = html.match(/<script src="([^"]+)"/)[1];
  assert.equal(path.resolve(__dirname, '../src/kho_tri_thuc/core/ui', src), sdkPath);
});

test('Shell tham chiếu CSS dùng chung trực tiếp, lưới sử dụng class có trong asset nền', () => {
  const href = html.match(/<link rel="stylesheet" href="([^"]+)"/)[1];
  const assetPath = path.resolve(__dirname, '../src/kho_tri_thuc/core/ui', href);
  assert.equal(assetPath, path.resolve(__dirname, '../src/kho_tri_thuc/giao_dien/assets/style.css'));
  const css = fs.readFileSync(assetPath, 'utf8');
  assert.match(css, /\.gk-luoi\s*\{[^}]*display:grid/);
  assert.ok(!html.includes('.core-luoi { display: grid'));
  // Không nạp app.js cũ: tệp đó tự gọi API cũ và gắn DOM cố định.
  assert.ok(!html.includes('<script src="../../giao_dien/assets/app.js"'));
  const doc = documentGia(), root = doc.createElement('div');
  SDK.khung.dung(root, khaiBao);
  assert.equal(find(root, e => e.className?.split(' ').includes('gk-luoi')).length, 1);
});
