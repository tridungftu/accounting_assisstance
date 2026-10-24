'use strict';

/*
 * M2-00B — kiem thu literal DEMO cho dich vu owned RPC/SSE (server.js createOwnedService) tren producer A THAT (job.createProducer).
 * Trang thai: AUTHORED_NOT_RUN. Chay (Root, sau independent review): node --test tests/m2_00b_source7_rpc.cjs voi
 *   M2_00B_VIEW_ROOT = view rieng da materialize: src/{server,job,manifest,portal}.js + config.js (khong cai dat trong luot chay)
 *   M2_00B_DEMO_OUT  = thu muc tuyet doi da ton tai de giu file DEMO (khong xoa/cleanup)
 * Khong bind cong, khong mang/portal/Playwright: req/res gia goi thang service.handle; portal.launchAndLogin + build la gia
 * (dang nhap luon that bai co ma -> receipt FAILED cua A). Profile <MA>.env DEMO co canary credential; moi ca co positive + denial.
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { Readable } = require('node:stream');
const { EventEmitter } = require('node:events');

const VIEW = process.env.M2_00B_VIEW_ROOT;
const OUT = process.env.M2_00B_DEMO_OUT;
if (!VIEW || !path.isAbsolute(VIEW) || !fs.existsSync(path.join(VIEW, 'src', 'server.js'))) {
  throw new Error('M2_00B_VIEW_ROOT phai la duong dan tuyet doi toi view da materialize (khong fallback).');
}
if (!OUT || !path.isAbsolute(OUT) || !fs.existsSync(OUT) || !fs.lstatSync(OUT).isDirectory()) {
  throw new Error('M2_00B_DEMO_OUT phai la thu muc tuyet doi da ton tai.');
}

const server = require(path.join(VIEW, 'src', 'server.js'));
const job = require(path.join(VIEW, 'src', 'job.js'));
const mf = require(path.join(VIEW, 'src', 'manifest.js'));

const RUN_ROOT = path.join(OUT, `m2_00b_rpc-${process.pid}-${Date.now()}`);
fs.mkdirSync(RUN_ROOT); // doc quyen; giu lai sau khi chay
let seq = 0;
const sha = (b) => crypto.createHash('sha256').update(b).digest('hex');
const tick = () => new Promise((r) => setImmediate(r));

/* ---------------- literal DEMO ---------------- */

const PORT = 47011;
const CAP = 'DEMOcapRPC_DEMOcapRPC_DEMOcapRPC_DEMOcapRPC_01';
const REV = sha('demo-source-profile-revision');
const PN = {
  A: { ma: 'DEMO_A', uuid: '00000000-0000-4000-8000-0000000000a1' },
  B: { ma: 'DEMO_B', uuid: '00000000-0000-4000-8000-0000000000b1' },
};
const USER_A = 'DEMO_CANARY_USER_A_51e0';
const PASS_A = 'DEMO_CANARY_PASS_A_77b2';
const USER_B = 'DEMO_CANARY_USER_B_0c9d';
const PASS_B = 'DEMO_CANARY_PASS_B_e4a8';
const TOKEN = 'DEMOCANARYhdrRPCA.DEMOCANARYpayloadRPCB.DEMOCANARYsigRPCC';
const CANARIES = [USER_A, PASS_A, USER_B, PASS_B, TOKEN, CAP];

function ctxFor(o = {}) {
  const pn = PN[o.pn || 'A'];
  return {
    schema: 'm2_00a.source7.run_context.v1',
    issued_by: 'M2_COORDINATOR',
    phap_nhan: { uuid: pn.uuid, ma: pn.ma },
    profile: { ref: pn.ma, revision: o.revision || REV },
    actor: { id: '11111111-1111-4111-8111-111111111111', nguon: 'crm_phien' },
    binding: { selection_digest: sha(`sel-${o.tag || 'base'}`) },
    source_instance: 'demo.hddt.m2',
    scope_ref: 'INV_SET_DEMO',
    run: {
      run_id: o.runId || '20261023-101500',
      nonce: o.nonce || `DEMOnonce_${o.tag || 'base'}`.padEnd(26, '0'),
      request_key: o.key || `m2b_${sha(`key-${o.tag || 'base'}`)}`,
    },
    request: { mode: 'month', year: 2026, month: o.month || 9, types: o.types || ['purchase'], formats: ['xml'] },
  };
}

function writeProfile(dir, ref, lines) {
  fs.writeFileSync(path.join(dir, `${ref}.env`), lines.join('\r\n') + '\r\n', { flag: 'wx' });
}

function makePortal() {
  const p = {
    logins: [],
    gate: null,
    statusLines: 1,
    async launchAndLogin({ username, password, onStatus }) {
      p.logins.push({ userHash: sha(username), passHash: sha(password) });
      for (let i = 0; i < p.statusLines; i++) onStatus(`DEMO prefill ${username} / ${password} cap=${CAP} #${i}`); // phai bi lam sach
      onStatus(`DEMO token ${TOKEN}`);
      if (p.gate) await p.gate;
      throw Object.assign(new Error(`DEMO ${password}`), { code: 'LOGIN_DEMO_DENIED' });
    },
  };
  return p;
}

function setup(tag, limits = {}) {
  seq += 1;
  const base = path.join(RUN_ROOT, `${String(seq).padStart(2, '0')}-${tag}`);
  fs.mkdirSync(base);
  const roots = {};
  for (const [k, d] of [['downloadRoot', 'download'], ['browserProfileRoot', 'browser'], ['profilesDir', 'profiles']]) {
    roots[k] = path.join(base, d);
    fs.mkdirSync(roots[k]);
  }
  writeProfile(roots.profilesDir, PN.A.ma, [`MA_PHAP_NHAN=${PN.A.ma}`, `PHAP_NHAN_UUID=${PN.A.uuid}`, `PROFILE_REVISION=${REV}`,
    `TAX_USERNAME=${USER_A}`, `TAX_PASSWORD="${PASS_A}"`]);
  writeProfile(roots.profilesDir, PN.B.ma, [`MA_PHAP_NHAN=${PN.B.ma}`, `PHAP_NHAN_UUID=${PN.B.uuid}`, `PROFILE_REVISION=${REV}`,
    `TAX_USERNAME=${USER_B}`, `TAX_PASSWORD=${PASS_B}`]);
  let t = Date.UTC(2026, 9, 23, 3, 15, 0);
  const clock = { now: () => t++, sleep: async () => {} };
  const portal = makePortal();
  const producer = job.createProducer({ roots, clock, portal, build: { createPdfRenderer: async () => null } });
  const opened = [];
  const svc = server.createOwnedService({
    capability: CAP, port: PORT, producer, openFolder: (abs) => opened.push(abs),
    limits: Object.assign({ sse_heartbeat_ms: 60000, sse_max_ms: 600000 }, limits),
  });
  const seen = [];
  return { base, roots, portal, producer, svc, opened, seen };
}

/* ---------------- req/res gia (dung interface handle dung) ---------------- */

function fakeReq(method, url, headers, body) {
  const r = Readable.from(body ? [body] : []);
  r.method = method;
  r.url = url;
  r.headers = headers;
  return r;
}

function fakeRes() {
  const res = new EventEmitter();
  res.status = null;
  res.headers = null;
  res.chunks = [];
  res.ended = false;
  res.writeHead = (s, h) => {
    res.status = s;
    res.headers = h;
  };
  res.write = (c) => {
    assert.equal(res.ended, false, 'write sau end');
    res.chunks.push(Buffer.isBuffer(c) ? c.toString('utf8') : String(c));
    return true;
  };
  res.end = (c) => {
    if (c !== undefined) res.chunks.push(Buffer.isBuffer(c) ? c.toString('utf8') : String(c));
    res.ended = true;
  };
  res.text = () => res.chunks.join('');
  res.json = () => JSON.parse(res.text());
  return res;
}

async function call(s, method, url, body, extra = {}) {
  const buf = body === undefined ? null : Buffer.from(typeof body === 'string' ? body : JSON.stringify(body), 'utf8');
  const headers = Object.assign({ host: `127.0.0.1:${PORT}`, [server.CAP_HEADER]: CAP },
    buf ? { 'content-type': 'application/json', 'content-length': String(buf.length) } : {}, extra);
  for (const k of Object.keys(headers)) if (headers[k] === null) delete headers[k];
  const res = fakeRes();
  await s.svc.handle(fakeReq(method, url, headers, buf), res);
  s.seen.push(res);
  return res;
}

function frames(text) {
  const out = [];
  for (const block of text.split('\n\n')) {
    if (!block || block.startsWith(':')) continue;
    const f = {};
    for (const line of block.split('\n')) {
      const i = line.indexOf(': ');
      if (i > 0) f[line.slice(0, i)] = line.slice(i + 2);
    }
    out.push(f.event === 'end' ? { end: JSON.parse(f.data).reason } : JSON.parse(f.data));
  }
  return out;
}

function noCanary(s) {
  const all = s.seen.map((r) => r.text()).join('\n');
  for (const c of CANARIES) assert.ok(!all.includes(c), 'canary lo qua RPC/SSE');
}

/* ---------------- tests ---------------- */

test('B02 createOwnedService tu choi cau hinh sai, khong IO khi tao',() => {
  const s = setup('cfg');
  assert.throws(() => server.createOwnedService({ capability: 'ngan', producer: s.producer }), (e) => e.code === 'CAPABILITY_CONFIG');
  assert.throws(() => server.createOwnedService({ capability: CAP, producer: {} }), (e) => e.code === 'PRODUCER_CONFIG');
  assert.deepEqual(fs.readdirSync(s.roots.downloadRoot), []);
  assert.equal(s.portal.logins.length, 0);
  s.svc.close();
});

test('B03/B11 tu choi truoc moi IO: host/CORS/capability/query/route/method/body/context',async () => {
  const s = setup('deny');
  const ctx = ctxFor();
  const ca = [
    [['POST', '/api/start', { context: ctx }, { host: 'localhost:47011' }], 403, 'HOST_FORBIDDEN'],
    [['POST', '/api/start', { context: ctx }, { host: '127.0.0.1:1' }], 403, 'HOST_FORBIDDEN'],
    [['POST', '/api/start', { context: ctx }, { origin: 'http://127.0.0.1:47011' }], 403, 'CORS_FORBIDDEN'],
    [['POST', '/api/start', { context: ctx }, { 'sec-fetch-site': 'same-origin' }], 403, 'CORS_FORBIDDEN'],
    [['OPTIONS', '/api/start', undefined, {}], 403, 'CORS_FORBIDDEN'],
    [['POST', '/api/start', { context: ctx }, { [server.CAP_HEADER]: null }], 401, 'CAPABILITY_MISSING'],
    [['POST', '/api/start', { context: ctx }, { [server.CAP_HEADER]: CAP.slice(0, -1) + 'X' }], 401, 'CAPABILITY_INVALID'],
    [['GET', '/api/config?cap=' + CAP, undefined, {}], 400, 'QUERY_FORBIDDEN'],
    [['POST', '/api/start#x', { context: ctx }, {}], 400, 'QUERY_FORBIDDEN'],
    [['GET', '/', undefined, {}], 404, 'ROUTE_UNKNOWN'],
    [['GET', '/api/start', undefined, {}], 405, 'METHOD_NOT_ALLOWED'],
    [['GET', '/api/config', undefined, { 'content-length': '5' }], 400, 'BODY_FORBIDDEN'],
    [['POST', '/api/start', { context: ctx }, { 'content-type': 'text/plain' }], 415, 'CONTENT_TYPE_INVALID'],
    [['POST', '/api/start', 'x'.repeat(2048), { 'content-length': '2048' }], 413, 'BODY_TOO_LARGE'],
    [['POST', '/api/start', '{hong', {}], 400, 'BODY_INVALID_JSON'],
    [['POST', '/api/start', { context: ctx, roots: { downloadRoot: 'C:\\' } }, {}], 400, 'BODY_FIELDS_INVALID'],
    [['POST', '/api/start', { context: Object.assign({}, ctx, { credential: USER_A }) }, {}], 400, 'CONTEXT_INVALID'],
    [['POST', '/api/start', { context: Object.assign({}, ctx, { profile: { ref: '..\\x', revision: REV } }) }, {}], 400, 'CONTEXT_INVALID'],
  ];
  const s2 = setup('deny-small', { body_bytes: 1024 });
  for (const [[m, u, b, h], st, code] of ca) {
    const r = await call(code === 'BODY_TOO_LARGE' ? s2 : s, m, u, b, h);
    assert.equal(r.status, st, code);
    assert.equal(r.json().code, code);
    assert.equal(r.json().ok, false);
  }
  const inv = s.seen[s.seen.length - 1].json();
  assert.ok(Array.isArray(inv.errors) && inv.errors.every((e) => Object.keys(e).sort().join() === 'code,path'));
  assert.equal(s.portal.logins.length + s2.portal.logins.length, 0);
  assert.deepEqual(fs.readdirSync(s.roots.downloadRoot), []);
  noCanary(s);
  s.svc.close();
  s2.svc.close();
});

test('B01/B11 config + profiles: san sang theo binding/revision, khong tra credential',async () => {
  const s = setup('profiles');
  const c = await call(s, 'GET', '/api/config');
  assert.equal(c.status, 200);
  assert.deepEqual([c.json().protocol, c.json().version, c.json().running], [server.PROTOCOL, job.PRODUCER_VERSION, false]);
  const p = await call(s, 'POST', '/api/profiles', { profiles: [
    { ref: PN.A.ma, revision: REV, phap_nhan: PN.A },
    { ref: PN.B.ma, revision: sha('khac'), phap_nhan: PN.B },
    { ref: 'DEMO_X', revision: REV, phap_nhan: { uuid: PN.A.uuid, ma: 'DEMO_X' } },
  ] });
  assert.equal(p.status, 200);
  assert.deepEqual(p.json().profiles.map((x) => [x.ref, x.san_sang, x.ly_do]),
    [[PN.A.ma, true, null], [PN.B.ma, false, 'PROFILE_REVISION_MISMATCH'], ['DEMO_X', false, 'PROFILE_NOT_FOUND']]);
  const dup = await call(s, 'POST', '/api/profiles', { profiles: [{ ref: PN.A.ma, revision: REV, phap_nhan: PN.A }, { ref: PN.A.ma, revision: REV, phap_nhan: PN.A }] });
  assert.equal(dup.json().code, 'PROFILES_DUPLICATE');
  const lech = await call(s, 'POST', '/api/profiles', { profiles: [{ ref: PN.B.ma, revision: REV, phap_nhan: PN.A }] });
  assert.equal(lech.json().code, 'PROFILES_INVALID');
  assert.equal(s.portal.logins.length, 0);
  noCanary(s);
  s.svc.close();
});

test('B04/B07/B09 start -> RUNNING/JOB_BUSY -> su kien gan dung job -> DONE -> REPLAY; hai PN tach biet', async () => {
  const s = setup('flow');
  let releaseA;
  s.portal.gate = new Promise((r) => { releaseA = r; });
  const a = ctxFor({ tag: 'A' });
  const r1 = await call(s, 'POST', '/api/start', { context: a });
  assert.equal(r1.status, 200);
  const st = r1.json();
  assert.equal(st.status, 'STARTED');
  assert.equal(st.context_digest, mf.contextDigest(a));
  assert.equal(st.request_key_sha256, sha(a.run.request_key));
  assert.equal((await call(s, 'POST', '/api/start', { context: a })).json().status, 'RUNNING');
  const sa = await call(s, 'POST', '/api/status', { context: a });
  assert.equal(sa.json().status, 'RUNNING');
  const busy = await call(s, 'POST', '/api/start', { context: ctxFor({ pn: 'B', tag: 'B' }) });
  assert.deepEqual([busy.status, busy.json().code], [409, 'JOB_BUSY']);
  const mismatch = await call(s, 'POST', '/api/start', { context: ctxFor({ tag: 'A', nonce: 'DEMOnonce_other_000000000' }) });
  assert.deepEqual([mismatch.status, mismatch.json().code], [409, 'CONTEXT_MISMATCH']);

  const stream = await call(s, 'POST', '/api/events', { context: a, cursor: 0 });
  assert.equal(stream.status, 200);
  assert.match(stream.headers['Content-Type'], /^text\/event-stream/);
  assert.equal(stream.ended, false);
  releaseA();
  await s.producer.getState().done;
  await tick();
  assert.equal(stream.ended, true);
  const evA = frames(stream.text());
  assert.deepEqual(evA[evA.length - 1], { end: 'DONE' });
  const data = evA.slice(0, -1);
  assert.ok(data.length >= 3);
  data.forEach((e, i) => {
    assert.equal(e.seq, i + 1);
    assert.equal(e.run_id, a.run.run_id);
    assert.equal(e.context_digest, st.context_digest);
    for (const v of Object.values(e.payload)) assert.ok(v === null || ['string', 'number', 'boolean'].includes(typeof v));
  });
  assert.equal(data[data.length - 1].type, 'done');

  const rep = (await call(s, 'POST', '/api/status', { context: a })).json();
  assert.equal(rep.status, 'REPLAY');
  assert.equal(rep.receipt.trang_thai, 'FAILED');
  assert.deepEqual(rep.receipt.runs.map((x) => x.run_rel), [`${PN.A.ma}/2026-09/mua_vao/${a.run.run_id}`]);
  assert.equal((await call(s, 'POST', '/api/start', { context: a })).json().status, 'REPLAY');
  assert.equal((await call(s, 'POST', '/api/reconcile', { context: a })).json().status, 'REPLAY');

  // PN B sau khi A xong: su kien B khong lan vao A
  let releaseB;
  s.portal.gate = new Promise((r) => { releaseB = r; });
  const b = ctxFor({ pn: 'B', tag: 'B' });
  assert.equal((await call(s, 'POST', '/api/start', { context: b })).json().status, 'STARTED');
  const nA = s.svc.jobs.get(sha(a.run.request_key)).events.length;
  releaseB();
  await s.producer.getState().done;
  await tick();
  assert.equal(s.svc.jobs.get(sha(a.run.request_key)).events.length, nA);
  const evB = frames((await call(s, 'POST', '/api/events', { context: b, cursor: 0 })).text());
  assert.ok(evB.slice(0, -1).every((e) => e.run_id === b.run.run_id && e.context_digest === mf.contextDigest(b)));
  const evA2 = frames((await call(s, 'POST', '/api/events', { context: a, cursor: 0 })).text());
  assert.ok(evA2.slice(0, -1).every((e) => e.context_digest === st.context_digest));
  assert.equal(s.portal.logins.length, 2);
  noCanary(s);
  s.svc.close();
});

test('B09 cursor sai/het han, events khong co job, context lech', async () => {
  const s = setup('cursor', { events_per_job: 10 });
  s.portal.statusLines = 15;
  const a = ctxFor({ tag: 'C' });
  assert.equal((await call(s, 'POST', '/api/events', { context: a, cursor: 0 })).json().code, 'EVENTS_NOT_FOUND');
  await call(s, 'POST', '/api/start', { context: a });
  await s.producer.getState().done;
  const seqNow = s.svc.jobs.get(sha(a.run.request_key)).seq;
  assert.ok(seqNow > 10);
  for (const [cur, st, code] of [[-1, 400, 'CURSOR_INVALID'], ['0', 400, 'CURSOR_INVALID'], [seqNow + 1, 400, 'CURSOR_INVALID'], [0, 410, 'CURSOR_EXPIRED']]) {
    const r = await call(s, 'POST', '/api/events', { context: a, cursor: cur });
    assert.deepEqual([r.status, r.json().code], [st, code]);
  }
  const ok = frames((await call(s, 'POST', '/api/events', { context: a, cursor: seqNow - 2 })).text());
  assert.deepEqual(ok.map((e) => e.seq || e.end), [seqNow - 1, seqNow, 'DONE']);
  const lech = await call(s, 'POST', '/api/events', { context: ctxFor({ tag: 'C', nonce: 'DEMOnonce_lech_00000000000' }), cursor: 0 });
  assert.deepEqual([lech.status, lech.json().code], [409, 'CONTEXT_MISMATCH']);
  noCanary(s);
  s.svc.close();
});

test('B06 profile revision lech -> 422 truoc intent/portal', async () => {
  const s = setup('rev');
  const r = await call(s, 'POST', '/api/start', { context: ctxFor({ tag: 'R', revision: sha('revision-cu') }) });
  assert.deepEqual([r.status, r.json().code], [422, 'PROFILE_REVISION_MISMATCH']);
  assert.equal(s.portal.logins.length, 0);
  assert.deepEqual(fs.readdirSync(s.roots.downloadRoot), []);
  assert.equal(s.svc.jobs.size, 0);
  s.svc.close();
});

test('B10 open-folder chi thu muc run trong receipt cua dung context', async () => {
  const s = setup('open');
  const a = ctxFor({ tag: 'O' });
  await call(s, 'POST', '/api/start', { context: a });
  await s.producer.getState().done;
  const rel = `${PN.A.ma}/2026-09/mua_vao/${a.run.run_id}`;
  const ok = await call(s, 'POST', '/api/open-folder', { context: a, run_rel: rel });
  assert.deepEqual([ok.status, ok.json()], [200, { ok: true, run_rel: rel }]);
  assert.deepEqual(s.opened, [path.join(s.roots.downloadRoot, PN.A.ma, '2026-09', 'mua_vao', a.run.run_id)]);
  for (const [bad, st, code] of [
    [`${PN.B.ma}/2026-09/mua_vao/${a.run.run_id}`, 400, 'RUN_REL_INVALID'],
    [`${PN.A.ma}\\2026-09\\mua_vao\\${a.run.run_id}`, 400, 'RUN_REL_INVALID'],
    [`${PN.A.ma}/../mua_vao/${a.run.run_id}`, 404, 'RUN_NOT_FOUND'],
    [`${PN.A.ma}/../../mua_vao/${a.run.run_id}`, 400, 'RUN_REL_INVALID'],
    [`${PN.A.ma}/2026-08/mua_vao/${a.run.run_id}`, 404, 'RUN_NOT_FOUND'],
    [`/${rel}`, 400, 'RUN_REL_INVALID'],
  ]) {
    const r = await call(s, 'POST', '/api/open-folder', { context: a, run_rel: bad });
    assert.deepEqual([r.status, r.json().code], [st, code], bad);
  }
  const khac = await call(s, 'POST', '/api/open-folder', { context: ctxFor({ tag: 'O2' }), run_rel: rel });
  assert.equal(khac.status, 404);
  assert.equal(s.opened.length, 1);
  noCanary(s);
  s.svc.close();
});

test('B08/B09 close(): stream dang mo ket thuc SHUTDOWN, route sau do 503', async () => {
  const s = setup('close');
  let release;
  s.portal.gate = new Promise((r) => { release = r; });
  const a = ctxFor({ tag: 'S' });
  await call(s, 'POST', '/api/start', { context: a });
  const stream = await call(s, 'POST', '/api/events', { context: a, cursor: 0 });
  s.svc.close();
  assert.equal(stream.ended, true);
  const ev = frames(stream.text());
  assert.deepEqual(ev[ev.length - 1], { end: 'SHUTDOWN' });
  assert.equal((await call(s, 'GET', '/api/config')).status, 503);
  release();
  await s.producer.getState().done; // producer A tu ket thuc job, receipt giu nguyen
  assert.equal(s.producer.reconcile(a).status, 'REPLAY');
  noCanary(s);
});
