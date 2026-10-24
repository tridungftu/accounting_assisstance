'use strict';

/*
 * M2-00A FIX02 — regression literal DEMO cho 2 causal fix:
 *   (A) trang datas rong nhung con con tro KHONG chung minh het nguon -> nhom LOI (PARTIAL/FAILED, khong COMPLETE);
 *   (B) replay/doi soat phai khop DU ke hoach goc = planRuns(ctx, intent.tao_luc); intent+receipt bi cat cung nhau
 *       bi chan o ca reconcile va startJob. Job moi dung MOT thoi diem cho plan va intent.tao_luc/bat_dau.
 * Chay (Root, sau FULL review): node --test tests/m2_00a_source7_fix02.cjs voi
 *   M2_00A_VIEW_ROOT = view rieng da materialize: src/{job,portal,manifest,build}.js, config.js,
 *                      node_modules/adm-zip tu lock da pin (KHONG cai dat trong luot chay)
 *   M2_00A_DEMO_OUT  = thu muc tuyet doi da ton tai de giu file DEMO (khong xoa/cleanup)
 * Khong mang/portal/Playwright/ExcelJS that; khong credential/du lieu that. Fixture negative la ban sao CreateNew;
 * ban goc chi doc va duoc kiem lai bat bien. Thoi diem dung Date constructor local (cung ngu nghia planner).
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const VIEW = process.env.M2_00A_VIEW_ROOT;
const OUT = process.env.M2_00A_DEMO_OUT;
if (!VIEW || !path.isAbsolute(VIEW) || !fs.existsSync(path.join(VIEW, 'src', 'job.js'))) {
  throw new Error('M2_00A_VIEW_ROOT phai la duong dan tuyet doi toi view da materialize (khong fallback).');
}
if (!OUT || !path.isAbsolute(OUT) || !fs.existsSync(OUT) || !fs.lstatSync(OUT).isDirectory()) {
  throw new Error('M2_00A_DEMO_OUT phai la thu muc tuyet doi da ton tai.');
}

const cfg = require(path.join(VIEW, 'config.js'));
const mf = require(path.join(VIEW, 'src', 'manifest.js'));
const job = require(path.join(VIEW, 'src', 'job.js'));
const realPortal = require(path.join(VIEW, 'src', 'portal.js'));

// Chi trong bo nho tien trinh test: bo nghi giua cac lan goi de chay nhanh (so lan thu lai giu nguyen).
cfg.THROTTLE_MS = 0;
cfg.RETRY_DELAY_MS = 1;

const RUN_ROOT = path.join(OUT, `m2_00a_fix02-${process.pid}-${Date.now()}`);
fs.mkdirSync(RUN_ROOT); // doc quyen; giu lai sau khi chay
let seq = 0;
function freshDir(tag) {
  seq += 1;
  const d = path.join(RUN_ROOT, `${String(seq).padStart(2, '0')}-${tag}`);
  fs.mkdirSync(d);
  return d;
}
function mk(base, name) {
  const d = path.join(base, name);
  fs.mkdirSync(d);
  return d;
}
const sha = (b) => crypto.createHash('sha256').update(b).digest('hex');
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
function throwsCode(fn, code) {
  assert.throws(fn, (e) => {
    assert.equal(e.code, code);
    return true;
  });
}

/* ---------------- literal DEMO ---------------- */

const PN = {
  A: { ma: 'DEMO_PN_A', uuid: '00000000-0000-4000-8000-0000000000a1', profile: 'DEMO_A' },
};
const TOKEN = 'DEMOFIX02hdrAAAA.DEMOFIX02payloadBBBB.DEMOFIX02sigCCCC';
const FACTS = {
  captcha_da_go: { trang_thai: 'UNKNOWN', gia_tri: null, ly_do: 'CAPTCHA_INPUT_NOT_OBSERVED_BY_PRODUCER' },
  token_tai_su_dung: { trang_thai: 'OBSERVED', gia_tri: false, can_cu: 'NO_TOKEN_AT_PRECHECK' },
  thoi_gian_cho_dang_nhap_giay: { trang_thai: 'OBSERVED', gia_tri: 42, can_cu: 'CLOCK_LAUNCH_TO_TOKEN' },
};
const EMPTY_CURSOR = '{"datas":[],"state":"next-page"}';
const E_EMPTY = 'PAGINATION_EMPTY_PAGE_WITH_CURSOR';

function xmlFor(nbmst, shdon) {
  return Buffer.from(
    `<?xml version="1.0" encoding="UTF-8"?><HDon><DLHDon><TTChung><SHDon>${shdon}</SHDon></TTChung>` +
      `<NDHDon><NBan><MST>${nbmst}</MST></NBan></NDHDon></DLHDon></HDon>`,
    'utf8'
  );
}

function rec(nbmst, khhdon, shdon) {
  return {
    nbmst, khmshdon: 1, khhdon, shdon,
    tdlap: '2026-09-05T00:00:00', tthai: 1, nbten: 'DEMO SELLER',
    tgtcthue: 1000000, tgtthue: 100000, tgtttbso: 1100000, dvtte: 'VND',
  };
}

function ctxFor(o = {}) {
  const pn = PN.A;
  const tag = o.tag || 'base';
  return {
    schema: 'm2_00a.source7.run_context.v1',
    issued_by: 'M2_COORDINATOR',
    phap_nhan: { uuid: pn.uuid, ma: pn.ma },
    profile: { ref: pn.profile, revision: 'rev-1' },
    actor: { id: 'demo.actor.1', nguon: 'crm_phien' },
    binding: { selection_digest: 'a'.repeat(64) },
    source_instance: 'demo-source7',
    scope_ref: 'demo-scope-1',
    run: {
      run_id: o.runId || '20261023-101500',
      nonce: o.nonce || `DEMOnonce_${tag}`.padEnd(26, '0'),
      request_key: o.key || `DEMOreq_${tag}`,
    },
    request: {
      mode: o.mode || 'month',
      year: o.year || 2026,
      month: o.mode === 'year' ? null : (o.month || 9),
      types: o.types || ['purchase'],
      formats: o.formats || ['xml'],
    },
  };
}

function setup(tag) {
  const base = freshDir(tag);
  return { base, roots: { downloadRoot: mk(base, 'download'), browserProfileRoot: mk(base, 'browser'), profilesDir: mk(base, 'profiles') } };
}

/* Clock seam: moi lan now() tien 1 ms tu moc cho truoc (mac dinh 2026-10-23T03:00:00Z nhu suite cu). */
function makeClock(startMs = Date.UTC(2026, 9, 23, 3, 0, 0)) {
  let t = startMs;
  const c = { sleeps: [], now: () => t++, sleep: async (ms) => { c.sleeps.push(ms); } };
  return c;
}

function credSpy() {
  const s = {
    calls: 0,
    fn: () => {
      s.calls += 1;
      return { username: 'DEMO_FIX02_USER', password: 'DEMO_FIX02_PASS', ignoredKeys: [] };
    },
  };
  return s;
}

function makeWorld(spec) {
  const calls = { list: {}, export: {} };
  const route = (arg) => {
    const u = new URL(arg.url);
    if (u.pathname.endsWith('/export-xml')) {
      const q = u.searchParams;
      const key = `${q.get('nbmst')}|${q.get('khhdon')}|${q.get('shdon')}`;
      calls.export[key] = (calls.export[key] || 0) + 1;
      return (world.spec.exports && world.spec.exports[key]) || { status: 404, body: '' };
    }
    const type = u.pathname.endsWith('/sold') ? 'sold' : 'purchase';
    const scope = u.pathname.includes('/sco-query/') ? 'sco-query' : 'query';
    const ttxly = (/ttxly==(\d+)/.exec(u.searchParams.get('search') || '') || [])[1];
    const gk = `${type}|${scope}|${ttxly}`;
    calls.list[gk] = (calls.list[gk] || 0) + 1;
    const v = world.spec.list && world.spec.list[gk];
    if (v && !Array.isArray(v)) return { status: v.status, body: v.body };
    return { status: 200, body: JSON.stringify({ datas: JSON.parse(JSON.stringify(v || [])), state: null }) };
  };
  const page = { isClosed: () => false, evaluate: async (_fn, arg) => route(arg) };
  const context = { pages: () => [page], close: async () => {} };
  const world = { spec, calls, page, context };
  return world;
}
const xmlOut = (buf) => ({ status: 200, b64: Buffer.from(buf).toString('base64') });

function makePortal(world) {
  const p = {
    logins: 0,
    async launchAndLogin() {
      p.logins += 1;
      return { context: world.context, page: world.page, token: TOKEN, loginFacts: FACTS };
    },
    fetchAllInvoicesWithGroups: realPortal.fetchAllInvoicesWithGroups,
    exportInvoiceXml: realPortal.exportInvoiceXml,
  };
  return p;
}

function makeBuild() {
  const b = {
    excelCalls: 0,
    async buildExcel(rows, sheetTitle, outPath) {
      b.excelCalls += 1;
      fs.writeFileSync(outPath, JSON.stringify({ sheet: sheetTitle, n: rows.length }), { flag: 'wx' });
    },
    parseInvoiceXml: () => ({ buyer: null }),
    async createPdfRenderer() {
      return { render: async () => Buffer.from('%PDF-DEMO'), close: async () => {} };
    },
  };
  return b;
}

function producerFor(roots, portal, extra = {}) {
  return job.createProducer({
    roots,
    clock: extra.clock || makeClock(),
    portal,
    build: extra.build || makeBuild(),
    loadCredential: extra.loadCredential || credSpy().fn,
  });
}

const runDir = (roots, chieuDir, runId, ky) => path.join(roots.downloadRoot, PN.A.ma, ky, chieuDir, runId);
const manifestOf = (dir) => readJson(path.join(dir, 'manifest.json'));
function assertRunVerified(dir, ctx) {
  const v = mf.verifyRunDir(dir, { context_digest: mf.contextDigest(ctx) });
  assert.deepEqual(v.errors, []);
  assert.equal(v.ok, true);
  return v;
}
function walkFiles(dir, out = []) {
  for (const n of fs.readdirSync(dir)) {
    const p = path.join(dir, n);
    if (fs.lstatSync(p).isDirectory()) walkFiles(p, out);
    else out.push(p);
  }
  return out;
}
function snap(root) {
  return walkFiles(root).map((f) => [path.relative(root, f).split(path.sep).join('/'), sha(fs.readFileSync(f))])
    .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
}
const intentRel = (ctx) => `DEMO_PN_A/_m2_intents/${sha(ctx.run.request_key)}.intent.json`;
const receiptRel = (ctx) => `DEMO_PN_A/_m2_intents/${sha(ctx.run.request_key)}.receipt.json`;
const fileAt = (root, rel) => path.join(root, ...rel.split('/'));

/* Ban sao CreateNew; override = {rel: bytes} ghi 'wx'; skip = [rel]. Ban goc chi doc. */
function copyTree(from, to, rel, override, skip) {
  fs.mkdirSync(to);
  for (const n of fs.readdirSync(from)) {
    const r = rel ? `${rel}/${n}` : n;
    const a = path.join(from, n);
    const b = path.join(to, n);
    const st = fs.lstatSync(a);
    if (st.isSymbolicLink()) throw new Error('fixture nguon co reparse');
    if (st.isDirectory()) copyTree(a, b, r, override, skip);
    else if (skip.includes(r)) continue;
    else if (Object.prototype.hasOwnProperty.call(override, r)) fs.writeFileSync(b, override[r], { flag: 'wx' });
    else fs.copyFileSync(a, b, fs.constants.COPYFILE_EXCL);
  }
}
function fixture(srcRoots, tag, { override = {}, skip = [] } = {}) {
  const base = freshDir(`fx-${tag}`);
  const roots = { downloadRoot: path.join(base, 'download'), browserProfileRoot: mk(base, 'browser'), profilesDir: mk(base, 'profiles') };
  copyTree(srcRoots.downloadRoot, roots.downloadRoot, '', override, skip);
  return roots;
}
const clone = (v) => JSON.parse(JSON.stringify(v));

/* Tu choi an toan o CA HAI entrypoint (clock replay tuy chon): khong credential/login/goi cong/thay doi file. */
function assertDeniedBoth(roots, ctx, code, label, clock) {
  const before = snap(roots.downloadRoot);
  const spy = credSpy();
  const world = makeWorld({});
  const portal = makePortal(world);
  const p = producerFor(roots, portal, { loadCredential: spy.fn, clock });
  throwsCode(() => p.reconcile(ctx), code);
  throwsCode(() => p.startJob(ctx), code);
  assert.equal(spy.calls, 0, label);
  assert.equal(portal.logins, 0, label);
  assert.deepEqual(world.calls, { list: {}, export: {} }, label);
  assert.deepEqual(snap(roots.downloadRoot), before, label);
  assert.deepEqual(fs.readdirSync(roots.browserProfileRoot), [], label);
}
/* REPLAY o CA HAI entrypoint, khong credential/login/goi cong/thay doi file. */
function assertReplayBoth(roots, ctx, receipt, label, clock) {
  const before = snap(roots.downloadRoot);
  const spy = credSpy();
  const world = makeWorld({});
  const portal = makePortal(world);
  const p = producerFor(roots, portal, { loadCredential: spy.fn, clock });
  const rc = p.reconcile(ctx);
  assert.equal(rc.status, 'REPLAY', label);
  assert.deepEqual(rc.receipt, receipt, label);
  const st = p.startJob(ctx);
  assert.equal(st.status, 'REPLAY', label);
  assert.deepEqual(st.receipt, receipt, label);
  assert.equal(spy.calls, 0, label);
  assert.equal(portal.logins, 0, label);
  assert.deepEqual(world.calls, { list: {}, export: {} }, label);
  assert.deepEqual(snap(roots.downloadRoot), before, label);
}

/* Transport phan trang thuan cho fetchAllInvoicesWithGroups that. */
const EMPTY_PAGE = { status: 200, body: '{"datas":[],"state":null}' };
function makePager(handler) {
  const calls = { byGroup: {} };
  const pg = {
    isClosed: () => false,
    evaluate: async (_fn, arg) => {
      const u = new URL(arg.url);
      const scope = u.pathname.includes('/sco-query/') ? 'sco-query' : 'query';
      const ttxly = (/ttxly==(\d+)/.exec(u.searchParams.get('search') || '') || [])[1];
      const gk = `${scope}|${ttxly}`;
      const n = (calls.byGroup[gk] = (calls.byGroup[gk] || 0) + 1);
      return handler(gk, u.searchParams.get('state'), n) || EMPTY_PAGE;
    },
  };
  return { context: { pages: () => [pg] }, calls };
}
const pageOf = (rows, state) => ({ status: 200, body: JSON.stringify({ datas: rows, state }) });
const fetchPurchase = (c) => realPortal.fetchAllInvoicesWithGroups(c, TOKEN, 'purchase', '01/09/2026', '30/09/2026');
const nhomView = (nhom) => nhom.map((g) => [g.scope, g.ttxly, g.trang_thai, g.so_ban_ghi, g.loi]);
const OK0 = [['query', 6, 'OK', 0, null], ['sco-query', 8, 'OK', 0, null]];
const LOI_EMPTY = ['query', 5, 'LOI', null, { code: E_EMPTY, http_status: 200 }];

/* ================= A. Het nguon phai co bang chung ================= */

test('A positive: {datas:[],state:null} -> OK 0; trang co dong + state null -> OK; 2 trang ket thuc dung', async () => {
  const e = makePager(() => EMPTY_PAGE);
  const r0 = await fetchPurchase(e.context);
  assert.deepEqual(nhomView(r0.nhom), [['query', 5, 'OK', 0, null], ...OK0]);
  assert.deepEqual(r0.records, []);

  const one = makePager((gk) => (gk === 'query|5' ? pageOf([rec('9990000001', 'C26TAA', 1)], null) : null));
  const r1 = await fetchPurchase(one.context);
  assert.deepEqual(nhomView(r1.nhom), [['query', 5, 'OK', 1, null], ...OK0]);
  assert.equal(one.calls.byGroup['query|5'], 1);

  const two = makePager((gk, st) => {
    if (gk !== 'query|5') return null;
    if (st === null) return pageOf([rec('9990000001', 'C26TAA', 1)], 'p2');
    if (st === 'p2') return pageOf([rec('9990000001', 'C26TAA', 2)], null);
    return { status: 500, body: '' };
  });
  const r2 = await fetchPurchase(two.context);
  assert.deepEqual(nhomView(r2.nhom), [['query', 5, 'OK', 2, null], ...OK0]);
  assert.deepEqual(r2.records.map((r) => r.shdon), [1, 2]);
  assert.equal(two.calls.byGroup['query|5'], 2);
});

test('A negative: datas rong + con tro chua ket thuc (trang 1, sau trang co dong, lap con tro, trang cap) -> nhom LOI', async () => {
  const first = makePager((gk) => (gk === 'query|5' ? { status: 200, body: EMPTY_CURSOR } : null));
  const r1 = await fetchPurchase(first.context);
  assert.deepEqual(nhomView(r1.nhom), [LOI_EMPTY, ...OK0]);
  assert.deepEqual(r1.records, []);
  assert.equal(first.calls.byGroup['query|5'], 1);

  const after = makePager((gk, st, n) => {
    if (gk !== 'query|5') return null;
    return n === 1 ? pageOf([rec('9990000001', 'C26TAA', 1)], 'p2') : pageOf([], 'p3');
  });
  const r2 = await fetchPurchase(after.context);
  assert.deepEqual(nhomView(r2.nhom), [LOI_EMPTY, ...OK0]);
  assert.deepEqual(r2.records, []); // ban ghi trang 1 cua nhom loi khong vao records
  assert.equal(after.calls.byGroup['query|5'], 2);

  // Trang cuoi rong lap lai con tro cu: van khong OK.
  const rep = makePager((gk, st, n) => {
    if (gk !== 'query|5') return null;
    return n === 1 ? pageOf([rec('9990000001', 'C26TAA', 1)], 's1') : pageOf([], 's1');
  });
  const r3 = await fetchPurchase(rep.context);
  assert.equal(r3.nhom[0].trang_thai, 'LOI');
  assert.deepEqual(r3.nhom[0].loi, { code: E_EMPTY, http_status: 200 });
  assert.equal(rep.calls.byGroup['query|5'], 2);

  // Trang thu CAP rong nhung con con tro: khong OK, so lan goi <= cap+1.
  const CAP = realPortal._internal.MAX_PAGES;
  const cap = makePager((gk, st, n) => {
    if (gk !== 'query|5') return null;
    if (n > CAP + 1) throw new Error('fake transport vuot cap+1');
    return n < CAP ? pageOf([rec('9990000001', 'C26TAA', n)], `c${n}`) : pageOf([], `c${n}`);
  });
  const r4 = await fetchPurchase(cap.context);
  assert.equal(r4.nhom[0].trang_thai, 'LOI');
  assert.equal(['PAGINATION_EMPTY_PAGE_WITH_CURSOR', 'PAGINATION_CAP_REACHED'].includes(r4.nhom[0].loi.code), true);
  assert.equal(r4.nhom[0].loi.http_status, 200);
  assert.ok(cap.calls.byGroup['query|5'] <= CAP + 1);
  assert.deepEqual(r4.records, []);
});

test('A job: mot nhom rong+con tro -> PARTIAL; moi nhom -> FAILED NO_SOURCE_GROUP_VERIFIED; manifest/receipt nhat quan', async () => {
  const s = setup('a-partial');
  const world = makeWorld({
    list: {
      'purchase|query|5': [rec('9990000001', 'C26TAA', 7)],
      'purchase|query|6': { status: 200, body: EMPTY_CURSOR },
    },
    exports: { '9990000001|C26TAA|7': xmlOut(xmlFor('9990000001', 7)) },
  });
  const p = producerFor(s.roots, makePortal(world));
  const ctx = ctxFor({ tag: 'apart' });
  const receipt = await p.startJob(ctx).done;
  assert.equal(receipt.trang_thai, 'PARTIAL');
  assert.deepEqual(receipt.runs.map((r) => r.trang_thai), ['PARTIAL']);
  const dir = runDir(s.roots, 'mua_vao', '20261023-101500', '2026-09');
  const v = assertRunVerified(dir, ctx);
  assert.equal(v.manifest_sha256, receipt.runs[0].manifest_sha256);
  const m = manifestOf(dir);
  assert.deepEqual(m.nhom.map((g) => [g.trang_thai, g.loi]), [
    ['OK', null], ['LOI', { code: E_EMPTY, stage: 'LIST', http_status: 200 }], ['OK', null],
  ]);
  assert.deepEqual(m.ly_do_partial, ['NHOM_LOI']);
  assert.equal(m.trang_thai, 'PARTIAL');
  assertReplayBoth(s.roots, ctx, receipt, 'partial-replay');

  const f = setup('a-failed');
  const all = { status: 200, body: EMPTY_CURSOR };
  const worldF = makeWorld({ list: { 'purchase|query|5': all, 'purchase|query|6': all, 'purchase|sco-query|8': all } });
  const build = makeBuild();
  const pf = producerFor(f.roots, makePortal(worldF), { build });
  const ctxF = ctxFor({ tag: 'afail', formats: ['xml', 'excel'] });
  const rf = await pf.startJob(ctxF).done;
  assert.equal(rf.trang_thai, 'FAILED');
  const dirF = runDir(f.roots, 'mua_vao', '20261023-101500', '2026-09');
  assertRunVerified(dirF, ctxF);
  const mF = manifestOf(dirF);
  assert.equal(mF.trang_thai, 'FAILED');
  assert.deepEqual(mF.loi_chung, [{ code: 'NO_SOURCE_GROUP_VERIFIED', stage: 'LIST', http_status: null }]);
  assert.deepEqual(mF.nhom.map((g) => g.loi.code), [E_EMPTY, E_EMPTY, E_EMPTY]);
  assert.equal(build.excelCalls, 0);
  assert.deepEqual(worldF.calls.list, { 'purchase|query|5': 1, 'purchase|query|6': 1, 'purchase|sco-query|8': 1 });
  assertReplayBoth(f.roots, ctxF, rf, 'failed-replay');
});

/* ================= B. Replay phai giu du ke hoach goc ================= */

let srcYearPromise = null;
/* Nguon 1: nam 2025, purchase, clock mac dinh (2026) -> 12 run COMPLETE. */
function srcYear() {
  if (!srcYearPromise) {
    srcYearPromise = (async () => {
      const s = setup('src-year2025');
      const ctx = ctxFor({ tag: 'y2025', mode: 'year', year: 2025 });
      const receipt = await producerFor(s.roots, makePortal(makeWorld({}))).startJob(ctx).done;
      assert.equal(receipt.trang_thai, 'COMPLETE');
      assert.equal(receipt.runs.length, 12);
      return { s, ctx, receipt, intent: readJson(fileAt(s.roots.downloadRoot, intentRel(ctx))), snapshot: snap(s.roots.downloadRoot) };
    })();
  }
  return srcYearPromise;
}
let srcCurPromise = null;
/* Nguon 2: nam hien tai cua clock (local 2026-03-15 12:00), purchase+sold -> 3 thang x 2 chieu = 6 run. */
const CUR_T0 = new Date(2026, 2, 15, 12, 0, 0, 0).getTime();
function srcCur() {
  if (!srcCurPromise) {
    srcCurPromise = (async () => {
      const s = setup('src-year2026-cur');
      const ctx = ctxFor({ tag: 'ycur', mode: 'year', year: 2026, types: ['purchase', 'sold'] });
      const receipt = await producerFor(s.roots, makePortal(makeWorld({})), { clock: makeClock(CUR_T0) }).startJob(ctx).done;
      assert.equal(receipt.trang_thai, 'COMPLETE');
      return { s, ctx, receipt, intent: readJson(fileAt(s.roots.downloadRoot, intentRel(ctx))), snapshot: snap(s.roots.downloadRoot) };
    })();
  }
  return srcCurPromise;
}

test('B positive: ke hoach nam literal theo planner goc; tao_luc = moc lap ke hoach; REPLAY ca hai entrypoint', async () => {
  const y = await srcYear();
  assert.deepEqual(y.intent.ky_chieu.map((k) => [k.ky, k.chieu]),
    ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'].map((m) => [`2025-${m}`, 'purchase']));
  assert.equal(y.intent.tao_luc, new Date(Date.UTC(2026, 9, 23, 3, 0, 0)).toISOString());
  assert.equal(y.receipt.bat_dau, y.intent.tao_luc);
  assertReplayBoth(y.s.roots, y.ctx, y.receipt, 'year2025');

  const c = await srcCur();
  assert.deepEqual(c.intent.ky_chieu.map((k) => [k.ky, k.chieu, k.run_rel]), [
    ['2026-01', 'purchase', 'DEMO_PN_A/2026-01/mua_vao/20261023-101500'],
    ['2026-01', 'sold', 'DEMO_PN_A/2026-01/ban_ra/20261023-101500'],
    ['2026-02', 'purchase', 'DEMO_PN_A/2026-02/mua_vao/20261023-101500'],
    ['2026-02', 'sold', 'DEMO_PN_A/2026-02/ban_ra/20261023-101500'],
    ['2026-03', 'purchase', 'DEMO_PN_A/2026-03/mua_vao/20261023-101500'],
    ['2026-03', 'sold', 'DEMO_PN_A/2026-03/ban_ra/20261023-101500'],
  ]);
  assert.equal(c.intent.tao_luc, new Date(CUR_T0).toISOString());
  // Replay khi dong ho da sang thang/nam khac: khong mo them thang theo current clock.
  assertReplayBoth(c.s.roots, c.ctx, c.receipt, 'cur-later-month', makeClock(new Date(2026, 7, 1, 9, 0, 0, 0).getTime()));
  assertReplayBoth(c.s.roots, c.ctx, c.receipt, 'cur-next-year', makeClock(new Date(2027, 1, 1, 9, 0, 0, 0).getTime()));
  assert.deepEqual(snap(c.s.roots.downloadRoot), c.snapshot);
});

test('B negative: cat CA intent + receipt cung nhau (prefix/bo thang giua/bo chieu/doi thu tu/lap) -> INTENT_BINDING_MISMATCH', async () => {
  const sets = [[await srcYear(), [
    ['y-prefix1', [0]],
    ['y-drop-middle', [0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11]],
    ['y-drop-last', [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]],
    ['y-reorder', [1, 0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]],
    ['y-duplicate', [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0]],
  ]], [await srcCur(), [
    ['c-prefix1', [0]],
    ['c-drop-middle-month', [0, 1, 4, 5]],
    ['c-drop-sold', [0, 2, 4]],
    ['c-drop-purchase', [1, 3, 5]],
    ['c-reorder-types', [1, 0, 3, 2, 5, 4]],
    ['c-duplicate', [0, 1, 2, 3, 4, 5, 5]],
  ]]];
  for (const [src, cuts] of sets) {
    for (const [tag, idx] of cuts) {
      const I = clone(src.intent);
      const R = clone(src.receipt);
      I.ky_chieu = idx.map((i) => clone(src.intent.ky_chieu[i]));
      R.runs = idx.map((i) => clone(src.receipt.runs[i]));
      // Tu nhat quan: receipt van COMPLETE hop le, digest/tao_luc/hash run giu nguyen.
      assert.deepEqual(mf.validateReceipt(R), [], tag);
      assert.deepEqual(mf.validateIntent(I), [], tag);
      const roots = fixture(src.s.roots, tag, {
        override: { [intentRel(src.ctx)]: mf.stableBytes(I), [receiptRel(src.ctx)]: mf.stableBytes(R) },
      });
      assertDeniedBoth(roots, src.ctx, 'INTENT_BINDING_MISMATCH', tag);
    }
    assert.deepEqual(snap(src.s.roots.downloadRoot), src.snapshot); // ban goc bat bien
  }

  // Intent bi cat ma KHONG co receipt: doi soat UNKNOWN cung phai bi chan.
  const y = await srcYear();
  const I = clone(y.intent);
  I.ky_chieu = I.ky_chieu.slice(0, 3);
  const noRc = fixture(y.s.roots, 'y-prefix3-no-receipt', { override: { [intentRel(y.ctx)]: mf.stableBytes(I) }, skip: [receiptRel(y.ctx)] });
  assertDeniedBoth(noRc, y.ctx, 'INTENT_BINDING_MISMATCH', 'unknown-trimmed');
});

test('B time negative: tao_luc thieu/sai/khong chuan -> tu choi; tao_luc hop le nhung khac moc -> ke hoach khac -> mismatch', async () => {
  const y = await srcYear();
  const bad = [
    ['t-month13', '2026-13-01T00:00:00.000Z'],
    ['t-feb30', '2026-02-30T00:00:00.000Z'],
    ['t-hour25', '2026-10-23T25:00:00.000Z'],
    ['t-no-ms', '2026-10-23T03:00:00Z'],
    ['t-offset', '2026-10-23T03:00:00.000+07:00'],
    ['t-empty', ''],
    ['t-number', 1792724400000],
    ['t-null', null],
  ];
  for (const [tag, v] of bad) {
    const I = clone(y.intent);
    I.tao_luc = v;
    const roots = fixture(y.s.roots, tag, { override: { [intentRel(y.ctx)]: mf.stableBytes(I) } });
    assertDeniedBoth(roots, y.ctx, 'INTENT_TIME_INVALID', tag);
  }
  // Thieu han truong tao_luc: intent sai hinh dang -> INTENT_UNREADABLE (fail closed, khong doan thoi diem).
  const Imiss = clone(y.intent);
  delete Imiss.tao_luc;
  assertDeniedBoth(fixture(y.s.roots, 't-missing', { override: { [intentRel(y.ctx)]: mf.stableBytes(Imiss) } }), y.ctx, 'INTENT_UNREADABLE', 't-missing');

  // Moc hop le nhung trong nam 2025 (thang 3): planner goc chi cho 3 thang != 12 trong intent/receipt.
  const Ishift = clone(y.intent);
  Ishift.tao_luc = new Date(new Date(2025, 2, 10, 8, 0, 0, 0).getTime()).toISOString();
  assertDeniedBoth(fixture(y.s.roots, 't-shift', { override: { [intentRel(y.ctx)]: mf.stableBytes(Ishift) } }), y.ctx, 'INTENT_BINDING_MISMATCH', 't-shift');
  assert.deepEqual(snap(y.s.roots.downloadRoot), y.snapshot);
});

test('B anchor: job moi qua ranh thang/nam dung MOT moc cho plan va tao_luc/bat_dau; replay sau do van REPLAY', async () => {
  // Ranh thang: 23:59:59.999 ngay cuoi thang 2 (local) -> ke hoach nam 2026 = thang 1..2, du clock sau do da sang thang 3.
  const T1 = new Date(2026, 1, 28, 23, 59, 59, 999).getTime();
  const s1 = setup('anchor-month');
  const c1 = ctxFor({ tag: 'anm', mode: 'year', year: 2026 });
  const r1 = await producerFor(s1.roots, makePortal(makeWorld({})), { clock: makeClock(T1) }).startJob(c1).done;
  assert.equal(r1.trang_thai, 'COMPLETE');
  const i1 = readJson(fileAt(s1.roots.downloadRoot, intentRel(c1)));
  assert.deepEqual(i1.ky_chieu.map((k) => k.ky), ['2026-01', '2026-02']);
  assert.deepEqual(r1.runs.map((r) => r.ky), ['2026-01', '2026-02']);
  assert.equal(i1.tao_luc, new Date(T1).toISOString());
  assert.equal(r1.bat_dau, i1.tao_luc);
  assert.deepEqual(fs.readdirSync(path.join(s1.roots.downloadRoot, 'DEMO_PN_A')).sort(), ['2026-01', '2026-02', '_m2_intents']);
  assertReplayBoth(s1.roots, c1, r1, 'anchor-month-replay', makeClock(new Date(2026, 5, 1, 9, 0, 0, 0).getTime()));

  // Ranh nam: 23:59:59.999 ngay 31/12/2026 (local), request nam 2027 -> planner goc cho 12 thang (nam khac nam moc);
  // neu lay moc sau ranh (2027-01-01) se chi con 1 thang.
  const T2 = new Date(2026, 11, 31, 23, 59, 59, 999).getTime();
  const s2 = setup('anchor-year');
  const c2 = ctxFor({ tag: 'any', mode: 'year', year: 2027 });
  const r2 = await producerFor(s2.roots, makePortal(makeWorld({})), { clock: makeClock(T2) }).startJob(c2).done;
  assert.equal(r2.trang_thai, 'COMPLETE');
  const i2 = readJson(fileAt(s2.roots.downloadRoot, intentRel(c2)));
  assert.deepEqual(i2.ky_chieu.map((k) => k.ky),
    ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'].map((m) => `2027-${m}`));
  assert.equal(i2.tao_luc, new Date(T2).toISOString());
  assert.equal(r2.bat_dau, i2.tao_luc);
  assertReplayBoth(s2.roots, c2, r2, 'anchor-year-replay', makeClock(new Date(2027, 2, 1, 9, 0, 0, 0).getTime()));
});

test('B retain: thang COMPLETE, CONFLICT that, UNKNOWN khong receipt (du ke hoach) va NONCE_REUSED giu nguyen', async () => {
  const s = setup('retain');
  const world = makeWorld({
    list: { 'purchase|query|5': [rec('9990000001', 'C26TAA', 7)], 'sold|query|5': [] },
    exports: { '9990000001|C26TAA|7': xmlOut(xmlFor('9990000001', 7)) },
  });
  const portal = makePortal(world);
  const p = producerFor(s.roots, portal);
  const c1 = ctxFor({ tag: 'rt1', runId: '20261023-140000' });
  const r1 = await p.startJob(c1).done;
  assert.equal(r1.trang_thai, 'COMPLETE');
  // Cung giay, sold dat cho duoc, mua_vao da ton tai -> CONFLICT that (lich su dat cho dang do).
  const c3 = ctxFor({ tag: 'rt3', runId: '20261023-140000', types: ['sold', 'purchase'] });
  const r3 = await p.startJob(c3).done;
  assert.equal(r3.trang_thai, 'CONFLICT');
  assert.deepEqual(r3.runs.map((r) => [r.chieu, r.trang_thai]), [['sold', 'FAILED']]);
  assert.equal(portal.logins, 1);
  assertReplayBoth(s.roots, c1, r1, 'month-complete');
  assertReplayBoth(s.roots, c3, r3, 'conflict');

  // Nam 2025 khong receipt -> UNKNOWN, 12 run VALID, khong blind start.
  const y = await srcYear();
  const noRc = fixture(y.s.roots, 'retain-unknown', { skip: [receiptRel(y.ctx)] });
  const before = snap(noRc.downloadRoot);
  const spy = credSpy();
  const portalU = makePortal(makeWorld({}));
  const pu = producerFor(noRc, portalU, { loadCredential: spy.fn, clock: makeClock(new Date(2027, 0, 5, 9, 0, 0, 0).getTime()) });
  const rc = pu.reconcile(y.ctx);
  assert.equal(rc.status, 'UNKNOWN');
  assert.equal(rc.reconciliation.runs.length, 12);
  assert.equal(rc.reconciliation.runs.every((r) => r.manifest === 'VALID' && r.trang_thai_run === 'COMPLETE'), true);
  assert.equal(rc.reconciliation.co_the_doi_soat, true);
  const st = pu.startJob(y.ctx);
  assert.equal(st.status, 'UNKNOWN');
  assert.equal(await st.done, null);
  throwsCode(() => pu.startJob(ctxFor({ tag: 'rt9', key: 'DEMOreq_rt9', nonce: y.ctx.run.nonce })), 'NONCE_REUSED');
  assert.equal(spy.calls, 0);
  assert.equal(portalU.logins, 0);
  assert.deepEqual(snap(noRc.downloadRoot), before);
});
