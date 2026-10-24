'use strict';

/*
 * M2-00B — dich vu RIENG (owned/private) cua bo tai #7 cho M2 coordinator Python.
 * Candidate tu reference server da loc: giu ten /api/config, /api/profiles, /api/start, /api/events, /api/open-folder;
 * them /api/status, /api/reconcile (dung CHINH job.reconcile cua producer A, khong planner moi).
 *
 * - `require('./server')` KHONG bind cong, KHONG doc .env/profile, KHONG mo dashboard/trinh duyet.
 * - Chi chay owned mode khi goi tuong minh: `node src/server.js --owned`. Doc MOT dong cau hinh JSON tu stdin
 *   (capability chi RAM; khong argv/env/file/log/health) TRUOC khi tao producer/listener; chi listen 127.0.0.1;
 *   bat tay mot dong JSON tren stdout {protocol, version, port, pid} — khong co token.
 * - MOI route (ke ca config/profiles/SSE/replay) doi capability trong header rieng, so sanh constant-time.
 *   Khong CORS, khong static dashboard, khong nhan query/duong dan tuy y; body JSON dong, gioi han.
 * - /api/start nhan context A nguyen ven tu Python tin cay -> manifest.validateContext -> producer.startJob.
 *   Credential do A doc theo profile sau validation, chi RAM; khong bao gio tra ve Python/trinh duyet.
 * - Su kien gan dung job (request key hash + context digest); doi job thi dong stream cu truoc.
 * - stdin EOF -> dong server/stream, cho job hien tai huu han roi thoat (intent/receipt/file giu nguyen).
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawn } = require('child_process');

const job = require('./job');
const mf = require('./manifest');

const PROTOCOL = 'source7-m2-owned/v1';
const KIEU = Object.freeze({
  CONFIG: 'source7-m2-owned-config/v1',
  READY: 'source7-m2-owned-ready/v1',
  ERROR: 'source7-m2-owned-error/v1',
});
const CAP_HEADER = 'x-source7-m2-cap';
const CAP_RE = /^[A-Za-z0-9_-]{43,128}$/;
const INSTANCE_RE = /^[0-9a-f]{16,64}$/;
const STARTUP_LINE_BYTES = 64 * 1024;
const DEPENDENCIES = Object.freeze(['adm-zip', 'exceljs', 'fast-xml-parser', 'playwright']);

const DEFAULT_LIMITS = Object.freeze({
  body_bytes: 64 * 1024,
  event_payload_bytes: 4096,
  events_per_job: 5000,
  sse_heartbeat_ms: 10000,
  sse_max_ms: 30 * 60 * 1000,
  stop_grace_ms: 15000,
  profiles_max: 64,
});
const LIMIT_BOUNDS = Object.freeze({
  body_bytes: [1024, 1024 * 1024],
  event_payload_bytes: [256, 64 * 1024],
  events_per_job: [10, 20000],
  sse_heartbeat_ms: [100, 60000],
  sse_max_ms: [1000, 6 * 60 * 60 * 1000],
  stop_grace_ms: [100, 120000],
  profiles_max: [1, 500],
});

const ROUTES = Object.freeze({
  '/api/config': 'GET',
  '/api/profiles': 'POST',
  '/api/start': 'POST',
  '/api/status': 'POST',
  '/api/reconcile': 'POST',
  '/api/events': 'POST',
  '/api/open-folder': 'POST',
});
const BODY_KEYS = Object.freeze({
  '/api/profiles': ['profiles'],
  '/api/start': ['context'],
  '/api/status': ['context'],
  '/api/reconcile': ['context'],
  '/api/events': ['context', 'cursor'],
  '/api/open-folder': ['context', 'run_rel'],
});
const EVENT_TYPES = Object.freeze(['log', 'phase', 'month', 'progress', 'manifest', 'error', 'done']);
const PROFILE_KEYS = ['ref', 'revision', 'phap_nhan'];
const JWT_RE = /[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/;
const BEARER_RE = /bearer\s+\S/i;

// Ma loi producer -> HTTP. Khong phat nguyen exception/message (co the chua bi mat).
const CONFLICT_CODES = new Set([
  'JOB_BUSY', 'REQUEST_KEY_CONFLICT', 'INTENT_BINDING_MISMATCH', 'RECEIPT_BINDING_MISMATCH', 'NONCE_REUSED',
  'REQUEST_IN_FLIGHT', 'INTENT_UNREADABLE', 'RECEIPT_UNREADABLE', 'INTENT_TIME_INVALID', 'FILE_EXISTS_DIFFERENT',
]);
const UNPROCESSABLE_CODES = new Set([
  'PROFILE_NOT_FOUND', 'PROFILE_BINDING_MISMATCH', 'PROFILE_REVISION_MISMATCH', 'PROFILE_CREDENTIAL_MISSING',
  'ROOT_INVALID', 'ROOTS_INVALID', 'PLAN_EMPTY', 'PATH_REPARSE', 'PATH_ESCAPE', 'PATH_SEGMENT_INVALID', 'FILE_TOO_LARGE',
]);

class OwnedError extends Error {
  constructor(code, status) {
    super(code);
    this.code = code;
    this.status = status || 400;
  }
}

function isObj(v) {
  if (v === null || typeof v !== 'object' || Array.isArray(v)) return false;
  const p = Object.getPrototypeOf(v);
  return p === Object.prototype || p === null;
}

function exactKeys(v, keys) {
  return isObj(v) && Object.keys(v).length === keys.length && keys.every((k) => Object.prototype.hasOwnProperty.call(v, k));
}

function safeCode(e, fallback) {
  return e && typeof e.code === 'string' && mf.RE.code.test(e.code) ? e.code : fallback;
}

function producerStatus(code) {
  if (code === 'CONTEXT_INVALID') return 400;
  if (CONFLICT_CODES.has(code)) return 409;
  if (UNPROCESSABLE_CODES.has(code)) return 422;
  return 500;
}

/* ---------------- cau hinh khoi dong (stdin, mot dong) ---------------- */

function readStartupConfig(line) {
  let v;
  try {
    v = JSON.parse(String(line));
  } catch (_) {
    throw new OwnedError('CONFIG_INVALID');
  }
  if (!exactKeys(v, ['kieu', 'protocol', 'capability', 'port', 'instance_id', 'roots', 'limits'])) throw new OwnedError('CONFIG_INVALID');
  if (v.kieu !== KIEU.CONFIG || v.protocol !== PROTOCOL) throw new OwnedError('CONFIG_PROTOCOL');
  if (typeof v.capability !== 'string' || !CAP_RE.test(v.capability)) throw new OwnedError('CONFIG_CAPABILITY');
  if (!Number.isInteger(v.port) || v.port < 0 || v.port > 65535 || (v.port > 0 && v.port < 1024)) throw new OwnedError('CONFIG_PORT');
  if (typeof v.instance_id !== 'string' || !INSTANCE_RE.test(v.instance_id)) throw new OwnedError('CONFIG_INVALID');
  if (!exactKeys(v.roots, ['downloadRoot', 'browserProfileRoot', 'profilesDir'])) throw new OwnedError('CONFIG_ROOTS');
  const roots = {};
  for (const k of ['downloadRoot', 'browserProfileRoot', 'profilesDir']) {
    const r = v.roots[k];
    if (typeof r !== 'string' || !path.isAbsolute(r) || r.startsWith('\\\\') || r.startsWith('//')) throw new OwnedError('CONFIG_ROOTS');
    roots[k] = path.resolve(r);
  }
  if (new Set(Object.values(roots).map((r) => r.toLowerCase())).size !== 3) throw new OwnedError('CONFIG_ROOTS');
  if (!isObj(v.limits)) throw new OwnedError('CONFIG_LIMITS');
  const limits = Object.assign({}, DEFAULT_LIMITS);
  for (const [k, val] of Object.entries(v.limits)) {
    const b = LIMIT_BOUNDS[k];
    if (!b || !Number.isInteger(val) || val < b[0] || val > b[1]) throw new OwnedError('CONFIG_LIMITS');
    limits[k] = val;
  }
  return Object.freeze({
    capability: v.capability,
    port: v.port,
    instance_id: v.instance_id,
    roots: Object.freeze(roots),
    limits: Object.freeze(limits),
  });
}

function checkDependencies(resolve = require.resolve) {
  for (const d of DEPENDENCIES) {
    try {
      resolve(d);
    } catch (_) {
      return d;
    }
  }
  return null;
}

/* ---------------- su kien: lam sach + gan job ---------------- */

function scrubString(s, capability, max) {
  let out = String(s);
  if (capability) out = out.split(capability).join('[AN]');
  if (JWT_RE.test(out) || BEARER_RE.test(out)) return '[AN]';
  return out.length > max ? out.slice(0, max) : out;
}

/** Payload su kien: chi object phang cac scalar; chuoi da quet token/capability, gioi han kich thuoc. */
function sanitizePayload(payload, capability, maxBytes) {
  const out = {};
  if (!isObj(payload)) return out;
  for (const k of Object.keys(payload).slice(0, 32)) {
    if (!/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(k)) continue;
    const v = payload[k];
    if (v === null || typeof v === 'boolean') out[k] = v;
    else if (typeof v === 'number' && Number.isFinite(v)) out[k] = v;
    else if (typeof v === 'string') out[k] = scrubString(v, capability, 1000);
  }
  while (Buffer.byteLength(JSON.stringify(out), 'utf8') > maxBytes) {
    const keys = Object.keys(out);
    if (!keys.length) break;
    delete out[keys[keys.length - 1]];
  }
  return out;
}

function sseFrame(ev) {
  return `id: ${ev.seq}\ndata: ${JSON.stringify(ev)}\n\n`;
}

function sseEnd(reason) {
  return `event: end\ndata: ${JSON.stringify({ reason })}\n\n`;
}

/* ---------------- dich vu (khong IO khi tao) ---------------- */

/**
 * @param {object} o
 *   capability  chuoi capability do Python cap (chi RAM)
 *   port        so cong da bind hoac ham tra so cong (kiem Host)
 *   producer    ket qua job.createProducer(...) cua A (khong viet lai)
 *   limits      gioi han da kiem (readStartupConfig)
 *   openFolder  seam mo thu muc (mac dinh explorer, shell=false)
 *   now         dong ho (ms)
 */
function createOwnedService(o) {
  if (!o || typeof o.capability !== 'string' || !CAP_RE.test(o.capability)) throw new OwnedError('CAPABILITY_CONFIG');
  if (!o.producer || typeof o.producer.startJob !== 'function' || typeof o.producer.reconcile !== 'function') {
    throw new OwnedError('PRODUCER_CONFIG');
  }
  const capability = o.capability;
  const capDigest = crypto.createHash('sha256').update(capability, 'utf8').digest();
  const producer = o.producer;
  const limits = Object.assign({}, DEFAULT_LIMITS, o.limits || {});
  const portOf = typeof o.port === 'function' ? o.port : () => o.port;
  const openFolder = o.openFolder || defaultOpenFolder;
  const now = o.now || (() => Date.now());
  const roots = producer.roots;
  const jobs = new Map(); // request_key_sha256 -> entry
  const counters = { dropped_events: 0, denied: 0 };
  let closed = false;

  const state = () => producer.getState();
  const onEvent = (ev) => {
    const key = state().requestKeyHash;
    const entry = key ? jobs.get(key) : null;
    if (!entry || !ev || !EVENT_TYPES.includes(ev.type)) {
      counters.dropped_events += 1;
      return;
    }
    entry.seq += 1;
    const out = {
      seq: entry.seq,
      type: ev.type,
      payload: sanitizePayload(ev.payload, capability, limits.event_payload_bytes),
      ts: Number.isFinite(ev.ts) ? ev.ts : now(),
      run_id: entry.runId,
      context_digest: entry.digest,
    };
    entry.events.push(out);
    while (entry.events.length > limits.events_per_job) entry.events.shift();
    for (const s of entry.streams) s.send(out);
    if (ev.type === 'done') {
      entry.done = true;
      for (const s of Array.from(entry.streams)) s.end('DONE');
    }
  };
  state().emitter.on('event', onEvent);

  function capabilityOk(v) {
    if (typeof v !== 'string' || !v.length || v.length > 256) return false;
    const d = crypto.createHash('sha256').update(v, 'utf8').digest();
    return crypto.timingSafeEqual(d, capDigest);
  }

  function sendJson(res, status, body) {
    const buf = Buffer.from(JSON.stringify(body), 'utf8');
    res.writeHead(status, {
      'Content-Type': 'application/json; charset=utf-8',
      'Content-Length': String(buf.length),
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
    });
    res.end(buf);
  }

  function deny(res, status, code, extra) {
    counters.denied += 1;
    sendJson(res, status, Object.assign({ ok: false, code }, extra || {}));
  }

  function readBody(req) {
    return new Promise((resolve, reject) => {
      const declared = req.headers['content-length'];
      if (declared !== undefined && (!/^\d+$/.test(String(declared)) || Number(declared) > limits.body_bytes)) {
        reject(new OwnedError('BODY_TOO_LARGE', 413));
        return;
      }
      const chunks = [];
      let size = 0;
      let done = false;
      const fail = (e) => {
        if (!done) {
          done = true;
          reject(e);
        }
      };
      req.on('data', (c) => {
        if (done) return;
        size += c.length;
        if (size > limits.body_bytes) {
          fail(new OwnedError('BODY_TOO_LARGE', 413));
          return;
        }
        chunks.push(c);
      });
      req.on('error', () => fail(new OwnedError('BODY_READ_FAILED', 400)));
      req.on('end', () => {
        if (done) return;
        done = true;
        resolve(Buffer.concat(chunks));
      });
    });
  }

  function validated(ctx) {
    const v = mf.validateContext(ctx);
    if (!v.ok) {
      throw Object.assign(new OwnedError('CONTEXT_INVALID', 400), { errors: v.errors.slice(0, 20) });
    }
    return {
      ctx: v.value,
      digest: mf.contextDigest(v.value),
      keyHash: mf.sha256Hex(Buffer.from(v.value.run.request_key, 'utf8')),
    };
  }

  function closeOtherStreams(keyHash) {
    for (const [k, entry] of jobs) {
      if (k === keyHash) continue;
      for (const s of Array.from(entry.streams)) s.end('NEXT_JOB');
    }
  }

  function receiptView(receipt, sha) {
    return receipt ? { receipt, receipt_sha256: sha || null } : {};
  }

  /* ---- route handlers ---- */

  function routeConfig() {
    return {
      ok: true,
      protocol: PROTOCOL,
      version: job.PRODUCER_VERSION,
      running: !!state().running,
      capabilities: Object.keys(ROUTES),
      limits: { body_bytes: limits.body_bytes, events_per_job: limits.events_per_job },
    };
  }

  function profileReadiness(p) {
    const base = { ref: p.ref, revision: p.revision, phap_nhan: { uuid: p.phap_nhan.uuid, ma: p.phap_nhan.ma } };
    let kv = null;
    try {
      mf.assertRootDir(roots.profilesDir);
      const file = mf.resolveContained(roots.profilesDir, [`${p.ref}.env`]);
      const bytes = mf.readBounded(file, mf.LIMITS.PROFILE_BYTES);
      if (!bytes) return Object.assign(base, { san_sang: false, ly_do: 'PROFILE_NOT_FOUND' });
      kv = job._internal.parseEnvText(bytes.toString('utf8'));
      if (kv.MA_PHAP_NHAN !== p.phap_nhan.ma || kv.PHAP_NHAN_UUID !== p.phap_nhan.uuid) {
        return Object.assign(base, { san_sang: false, ly_do: 'PROFILE_BINDING_MISMATCH' });
      }
      if (kv.PROFILE_REVISION !== p.revision) return Object.assign(base, { san_sang: false, ly_do: 'PROFILE_REVISION_MISMATCH' });
      if (!kv.TAX_USERNAME || !kv.TAX_PASSWORD) return Object.assign(base, { san_sang: false, ly_do: 'PROFILE_CREDENTIAL_MISSING' });
      return Object.assign(base, { san_sang: true, ly_do: null });
    } catch (e) {
      return Object.assign(base, { san_sang: false, ly_do: safeCode(e, 'PROFILE_UNREADABLE') });
    } finally {
      kv = null; // credential chi trong pham vi ham nay, khong tra ve
    }
  }

  function routeProfiles(body) {
    const list = body.profiles;
    if (!Array.isArray(list) || list.length > limits.profiles_max) throw new OwnedError('PROFILES_INVALID');
    const seen = new Set();
    for (const p of list) {
      if (!exactKeys(p, PROFILE_KEYS) || !exactKeys(p.phap_nhan, ['uuid', 'ma'])) throw new OwnedError('PROFILES_INVALID');
      if (typeof p.ref !== 'string' || !mf.RE.ref.test(p.ref) || typeof p.revision !== 'string' || !mf.RE.revision.test(p.revision) ||
          typeof p.phap_nhan.uuid !== 'string' || !mf.RE.uuid.test(p.phap_nhan.uuid) ||
          typeof p.phap_nhan.ma !== 'string' || !mf.RE.maPn.test(p.phap_nhan.ma) || p.ref !== p.phap_nhan.ma) {
        throw new OwnedError('PROFILES_INVALID');
      }
      if (seen.has(p.ref)) throw new OwnedError('PROFILES_DUPLICATE');
      seen.add(p.ref);
    }
    return { ok: true, profiles: list.map(profileReadiness) };
  }

  function routeStart(body) {
    const { ctx, digest, keyHash } = validated(body.context);
    // Job ke tiep chi co the bat dau khi producer ranh: dong stream cua job cu TRUOC; job khac dang chay thi giu (startJob tu choi JOB_BUSY).
    if (!state().running) closeOtherStreams(keyHash);
    let entry = jobs.get(keyHash);
    const fresh = !entry;
    if (!fresh && entry.digest !== digest) throw new OwnedError('CONTEXT_MISMATCH', 409);
    if (fresh) {
      entry = { digest, runId: ctx.run.run_id, events: [], seq: 0, done: false, streams: new Set() };
      jobs.set(keyHash, entry);
    }
    let r;
    try {
      r = producer.startJob(ctx);
    } catch (e) {
      if (fresh) jobs.delete(keyHash);
      const code = safeCode(e, 'INTERNAL');
      throw new OwnedError(code, producerStatus(code));
    }
    if (r.status !== 'STARTED' && r.status !== 'RUNNING') entry.done = true;
    const out = { ok: true, status: r.status, run_id: ctx.run.run_id, context_digest: digest, request_key_sha256: keyHash };
    if (r.status === 'REPLAY') Object.assign(out, receiptView(r.receipt, r.receipt_sha256));
    if (r.status === 'UNKNOWN') out.reconciliation = r.reconciliation;
    return out;
  }

  function routeStatus(body) {
    const { ctx, digest, keyHash } = validated(body.context);
    const st = state();
    const entry = jobs.get(keyHash);
    if (st.running && st.requestKeyHash === keyHash) {
      if (!entry || entry.digest !== digest) throw new OwnedError('CONTEXT_MISMATCH', 409);
      return { ok: true, status: 'RUNNING', run_id: ctx.run.run_id, context_digest: digest, request_key_sha256: keyHash, events_seq: entry.seq };
    }
    let r;
    try {
      r = producer.reconcile(ctx);
    } catch (e) {
      const code = safeCode(e, 'INTERNAL');
      throw new OwnedError(code, producerStatus(code));
    }
    const out = { ok: true, status: r.status, run_id: ctx.run.run_id, context_digest: digest, request_key_sha256: keyHash };
    if (r.status === 'REPLAY') Object.assign(out, receiptView(r.receipt, r.receipt_sha256));
    if (r.status === 'UNKNOWN') out.reconciliation = r.reconciliation;
    if (entry && entry.digest === digest) out.events_seq = entry.seq;
    return out;
  }

  function routeEvents(body, req, res) {
    const { digest, keyHash } = validated(body.context);
    const cursor = body.cursor;
    const entry = jobs.get(keyHash);
    if (!entry) throw new OwnedError('EVENTS_NOT_FOUND', 404);
    if (entry.digest !== digest) throw new OwnedError('CONTEXT_MISMATCH', 409);
    if (!Number.isInteger(cursor) || cursor < 0 || cursor > entry.seq) throw new OwnedError('CURSOR_INVALID', 400);
    const first = entry.events.length ? entry.events[0].seq : entry.seq + 1;
    if (cursor < first - 1) throw new OwnedError('CURSOR_EXPIRED', 410);
    res.writeHead(200, {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
    });
    res.write(': open\n\n');
    for (const ev of entry.events) if (ev.seq > cursor) res.write(sseFrame(ev));
    if (entry.done || closed) {
      res.end(sseEnd(entry.done ? 'DONE' : 'SHUTDOWN'));
      return;
    }
    let ended = false;
    const stream = {
      send: (ev) => {
        if (!ended) res.write(sseFrame(ev));
      },
      end: (reason) => {
        if (ended) return;
        ended = true;
        clearInterval(hb);
        clearTimeout(maxT);
        entry.streams.delete(stream);
        try {
          res.end(sseEnd(reason));
        } catch (_) {}
      },
    };
    const hb = setInterval(() => {
      if (!ended) res.write(': hb\n\n');
    }, limits.sse_heartbeat_ms);
    const maxT = setTimeout(() => stream.end('MAX_DURATION'), limits.sse_max_ms);
    if (hb.unref) hb.unref();
    if (maxT.unref) maxT.unref();
    entry.streams.add(stream);
    const gone = () => {
      if (ended) return;
      ended = true;
      clearInterval(hb);
      clearTimeout(maxT);
      entry.streams.delete(stream);
    };
    if (typeof req.on === 'function') req.on('close', gone);
    if (typeof res.on === 'function') res.on('close', gone);
  }

  function allowedRunRels(r) {
    if (r.status === 'REPLAY' && r.receipt && Array.isArray(r.receipt.runs)) return r.receipt.runs.map((x) => x.run_rel);
    if (r.status === 'UNKNOWN' && r.reconciliation && Array.isArray(r.reconciliation.runs)) {
      return r.reconciliation.runs.filter((x) => x.ton_tai).map((x) => x.run_rel);
    }
    return [];
  }

  function routeOpenFolder(body) {
    const { ctx } = validated(body.context);
    const rel = body.run_rel;
    if (typeof rel !== 'string' || rel.length > 300 || /[\\:?#%*"<>|]/.test(rel) || rel.startsWith('/')) {
      throw new OwnedError('RUN_REL_INVALID', 400);
    }
    const seg = rel.split('/');
    if (seg.length !== 4 || seg[0] !== ctx.phap_nhan.ma || seg[3] !== ctx.run.run_id) throw new OwnedError('RUN_REL_INVALID', 400);
    let r;
    try {
      r = producer.reconcile(ctx);
    } catch (e) {
      const code = safeCode(e, 'INTERNAL');
      throw new OwnedError(code, producerStatus(code));
    }
    if (!allowedRunRels(r).includes(rel)) throw new OwnedError('RUN_NOT_FOUND', 404);
    let abs;
    try {
      abs = mf.resolveContained(roots.downloadRoot, seg);
      const st = fs.lstatSync(abs);
      if (!st.isDirectory() || st.isSymbolicLink()) throw new OwnedError('RUN_DIR_INVALID', 404);
      mf.assertNoReparse(abs);
    } catch (e) {
      throw new OwnedError(e instanceof OwnedError ? e.code : safeCode(e, 'RUN_DIR_INVALID'), 404);
    }
    if (abs.startsWith('\\\\') || abs.startsWith('//')) throw new OwnedError('RUN_DIR_INVALID', 404);
    try {
      openFolder(abs);
    } catch (_) {
      throw new OwnedError('OPEN_FAILED', 500);
    }
    return { ok: true, run_rel: rel };
  }

  /* ---- cong chung: moi kiem tra truoc moi IO ---- */

  async function handle(req, res) {
    try {
      if (closed) return deny(res, 503, 'SHUTTING_DOWN');
      const h = req.headers || {};
      if (h.host !== `127.0.0.1:${portOf()}`) return deny(res, 403, 'HOST_FORBIDDEN');
      if (req.method === 'OPTIONS' || h.origin !== undefined || h['sec-fetch-site'] !== undefined) return deny(res, 403, 'CORS_FORBIDDEN');
      if (h[CAP_HEADER] === undefined) return deny(res, 401, 'CAPABILITY_MISSING');
      if (!capabilityOk(h[CAP_HEADER])) return deny(res, 401, 'CAPABILITY_INVALID');
      const url = typeof req.url === 'string' ? req.url : '';
      if (url.includes('?') || url.includes('#')) return deny(res, 400, 'QUERY_FORBIDDEN');
      const method = ROUTES[url];
      if (!method) return deny(res, 404, 'ROUTE_UNKNOWN');
      if (req.method !== method) return deny(res, 405, 'METHOD_NOT_ALLOWED');
      if (method === 'GET') {
        const cl = h['content-length'];
        if ((cl !== undefined && cl !== '0') || h['transfer-encoding'] !== undefined) return deny(res, 400, 'BODY_FORBIDDEN');
        return sendJson(res, 200, routeConfig());
      }
      const ct = String(h['content-type'] || '').toLowerCase();
      if (ct !== 'application/json' && ct !== 'application/json; charset=utf-8') return deny(res, 415, 'CONTENT_TYPE_INVALID');
      const raw = await readBody(req);
      let body;
      try {
        body = JSON.parse(raw.toString('utf8'));
      } catch (_) {
        return deny(res, 400, 'BODY_INVALID_JSON');
      }
      if (!exactKeys(body, BODY_KEYS[url])) return deny(res, 400, 'BODY_FIELDS_INVALID');
      if (url === '/api/profiles') return sendJson(res, 200, routeProfiles(body));
      if (url === '/api/start') return sendJson(res, 200, routeStart(body));
      if (url === '/api/status' || url === '/api/reconcile') return sendJson(res, 200, routeStatus(body));
      if (url === '/api/open-folder') return sendJson(res, 200, routeOpenFolder(body));
      return routeEvents(body, req, res);
    } catch (e) {
      if (e instanceof OwnedError) {
        const extra = e.errors ? { errors: e.errors.map((x) => ({ path: String(x.path), code: String(x.code) })) } : null;
        return deny(res, e.status, e.code, extra);
      }
      return deny(res, 500, 'INTERNAL');
    }
  }

  function close() {
    closed = true;
    for (const entry of jobs.values()) for (const s of Array.from(entry.streams)) s.end('SHUTDOWN');
    state().emitter.removeListener('event', onEvent);
  }

  return { handle, close, counters, jobs };
}

function defaultOpenFolder(abs) {
  // shell=false, khong qua cmd; chi duong dan thu muc run da kiem.
  const p = spawn('explorer.exe', [abs], { shell: false, windowsHide: false, stdio: 'ignore' });
  p.on('error', () => {});
}

/* ---------------- owned CLI ---------------- */

function readOneLine(stream, max) {
  return new Promise((resolve) => {
    let buf = Buffer.alloc(0);
    let done = false;
    const finish = (v) => {
      if (done) return;
      done = true;
      stream.removeListener('data', onData);
      stream.removeListener('end', onEnd);
      resolve(v);
    };
    const onData = (c) => {
      buf = Buffer.concat([buf, c]);
      const i = buf.indexOf(0x0a);
      if (i >= 0) finish(buf.slice(0, i).toString('utf8'));
      else if (buf.length > max) finish(null);
    };
    const onEnd = () => finish(null);
    stream.on('data', onData);
    stream.on('end', onEnd);
  });
}

function runOwned(io = {}) {
  const stdin = io.stdin || process.stdin;
  const stdout = io.stdout || process.stdout;
  const exit = io.exit || ((c) => process.exit(c));
  const writeLine = (o) => stdout.write(JSON.stringify(o) + '\n');
  const fail = (ma, extra) => {
    writeLine(Object.assign({ kieu: KIEU.ERROR, protocol: PROTOCOL, ma, pid: process.pid }, extra || {}));
    exit(3);
  };
  return readOneLine(stdin, STARTUP_LINE_BYTES).then((line) => {
    if (line === null) return fail('CONFIG_MISSING');
    let cfg;
    try {
      cfg = readStartupConfig(line);
    } catch (e) {
      return fail(safeCode(e, 'CONFIG_INVALID'));
    }
    const dep = checkDependencies();
    if (dep) return fail('DEPENDENCY_MISSING', { phu_thuoc: dep });
    try {
      for (const k of ['downloadRoot', 'browserProfileRoot', 'profilesDir']) mf.assertRootDir(cfg.roots[k]);
    } catch (_) {
      return fail('ROOT_INVALID');
    }
    const producer = job.createProducer({ roots: cfg.roots });
    let bound = null;
    const service = createOwnedService({ capability: cfg.capability, port: () => bound, producer, limits: cfg.limits });
    const server = http.createServer({ maxHeaderSize: 16 * 1024 }, (req, res) => {
      service.handle(req, res);
    });
    server.headersTimeout = 10000;
    server.requestTimeout = 0; // SSE song lau; body POST da gioi han kich thuoc
    server.keepAliveTimeout = 2000;
    server.on('error', (e) => {
      if (bound === null) fail(e && e.code === 'EADDRINUSE' ? 'ADDRESS_IN_USE' : 'LISTEN_FAILED');
    });
    let stopping = false;
    const shutdown = () => {
      if (stopping) return;
      stopping = true;
      service.close();
      server.close();
      const st = producer.getState();
      const done = st.running && st.done ? st.done.then(() => 0, () => 0) : Promise.resolve(0);
      const grace = new Promise((r) => {
        const t = setTimeout(() => r(4), cfg.limits.stop_grace_ms);
        if (t.unref) t.unref();
      });
      Promise.race([done, grace]).then((code) => exit(code));
    };
    server.listen({ host: '127.0.0.1', port: cfg.port, exclusive: true }, () => {
      bound = server.address().port;
      writeLine({ kieu: KIEU.READY, protocol: PROTOCOL, version: job.PRODUCER_VERSION, port: bound, pid: process.pid, instance_id: cfg.instance_id });
    });
    stdin.on('end', shutdown);
    stdin.on('close', shutdown);
    stdin.resume();
    return { server, service, producer };
  });
}

if (require.main === module) {
  if (process.argv.length === 3 && process.argv[2] === '--owned') {
    runOwned();
  } else {
    // Khong co che do dashboard/legacy trong M2: thieu co tuong minh -> thoat, khong bind, khong doc profile.
    process.stderr.write('source7-m2: chi chay owned mode tuong minh (--owned).\n');
    process.exitCode = 2;
  }
}

module.exports = {
  PROTOCOL,
  KIEU,
  CAP_HEADER,
  ROUTES,
  DEFAULT_LIMITS,
  OwnedError,
  readStartupConfig,
  checkDependencies,
  sanitizePayload,
  createOwnedService,
  runOwned,
};
