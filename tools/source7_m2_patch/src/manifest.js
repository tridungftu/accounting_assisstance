'use strict';

/*
 * M2-00A — hop dong manifest / observation / intent / receipt va IO bat bien cho producer #7.
 * Chi dung Node stdlib. KHONG parse nghiep vu XML, KHONG master/quyen/ledger/tien te:
 * validator chi kiem hinh dang, dinh danh tho, hash, tong so va tinh nhat quan trang thai.
 * Kiem context o day KHONG phai quyet dinh quyen (quyen thuoc M2 coordinator ve sau).
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const SCHEMA = Object.freeze({
  CONTEXT: 'm2_00a.source7.run_context.v1',
  MANIFEST: 'm2_00a.source7.manifest.v1',
  OBSERVATIONS: 'm2_00a.source7.observations.v1',
  INTENT: 'm2_00a.source7.intent.v1',
  NONCE: 'm2_00a.source7.nonce.v1',
  RECEIPT: 'm2_00a.source7.receipt.v1',
  RUN_STARTED: 'm2_00a.source7.run_started.v1',
});

// Gioi han huu han tuong thich bo doc nguon/hoa_don_xml.py hien co.
const LIMITS = Object.freeze({
  XML_BYTES: 16 * 1024 * 1024,
  ZIP_BYTES: 64 * 1024 * 1024,
  ZIP_ENTRIES: 1000,
  JSON_BYTES: 64 * 1024 * 1024,
  PROFILE_BYTES: 64 * 1024,
});

const TYPE_DIR = Object.freeze({ purchase: 'mua_vao', sold: 'ban_ra' });
const INTENT_DIR = '_m2_intents';
const RUN_FILES = Object.freeze({
  STARTED: 'run.started.json',
  MANIFEST: 'manifest.json',
  OBSERVATIONS: 'observations.json',
});
const KEY_PARTS = Object.freeze(['nbmst', 'khmshdon', 'khhdon', 'shdon']);
const XML_STATUS = Object.freeze(['OK', 'KHONG_XML_GOC', 'LOI', 'KHONG_YEU_CAU']);
const RUN_STATUS = Object.freeze(['COMPLETE', 'PARTIAL', 'FAILED']);
const RECEIPT_STATUS = Object.freeze(['COMPLETE', 'PARTIAL', 'FAILED', 'CONFLICT']);
const RECEIPT_RUN_STATUS = Object.freeze(['COMPLETE', 'PARTIAL', 'FAILED', 'MANIFEST_INVALID', 'MANIFEST_WRITE_FAILED']);
const STAGES = Object.freeze(['RESERVE', 'LOGIN', 'LIST', 'EXPORT_XML', 'XML', 'ZIP', 'PDF', 'EXCEL', 'MANIFEST', 'INTERNAL']);
const ZIP_READ_STATES = Object.freeze(['READ_OK', 'READ_ERROR', 'IGNORED_NON_XML', 'DIRECTORY']);
const SCOPES = Object.freeze(['query', 'sco-query']);
const FACT_KIND = Object.freeze({
  captcha_da_go: 'boolean',
  token_tai_su_dung: 'boolean',
  thoi_gian_cho_dang_nhap_giay: 'number',
});

const RE = Object.freeze({
  uuid: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
  maPn: /^[A-Z0-9][A-Z0-9_-]{0,31}$/,
  ref: /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/,
  revision: /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/,
  actor: /^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}$/,
  instance: /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/,
  runId: /^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/,
  nonce: /^[A-Za-z0-9_-]{22,128}$/,
  requestKey: /^[A-Za-z0-9_-]{8,128}$/,
  hex64: /^[0-9a-f]{64}$/,
  ky: /^\d{4}-(0[1-9]|1[0-2])$/,
  iso: /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/,
  code: /^[A-Z0-9][A-Z0-9_+]{1,79}$/,
  apiPath: /^\/api\/[a-z0-9/-]+$/,
});
const SEGMENT_RE = /^[A-Za-z0-9_][A-Za-z0-9_.~-]{0,159}$/;
const WINDOWS_RESERVED = /^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])$/i;
const FORBIDDEN_KEY_RE = /^(password|passwd|pwd|pass|secret|cookie|cookies|set-cookie|authorization|bearer|token|access_token|refresh_token|id_token|jwt|captcha|captcha_text|captcha_value|username|user_name|tax_username|tax_password)$/i;
const JWT_RE = /[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/;
const BEARER_RE = /bearer\s+\S/i;

class ProducerError extends Error {
  constructor(code, detail) {
    super(code);
    this.name = 'ProducerError';
    this.code = code;
    this.detail = detail === undefined ? null : detail;
  }
}

/* ---------------- JSON chuan va hash ---------------- */

function sha256Hex(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function sortValue(v) {
  if (v === null) return null;
  if (Array.isArray(v)) return v.map(sortValue);
  switch (typeof v) {
    case 'string':
    case 'boolean':
      return v;
    case 'number':
      if (!Number.isFinite(v)) throw new ProducerError('NON_FINITE_NUMBER');
      return v;
    case 'object': {
      const out = {};
      for (const k of Object.keys(v).sort()) {
        if (v[k] === undefined) throw new ProducerError('UNDEFINED_VALUE', k);
        out[k] = sortValue(v[k]);
      }
      return out;
    }
    default:
      throw new ProducerError('UNSUPPORTED_JSON_VALUE');
  }
}

function canonicalJson(v) {
  return JSON.stringify(sortValue(v));
}

/** Bytes ghi ra dia: khoa sap xep, thut 2, ket thuc '\n' — tat dinh de hash/replay. */
function stableBytes(v) {
  return Buffer.from(JSON.stringify(sortValue(v), null, 2) + '\n', 'utf8');
}

function deepFreeze(v) {
  if (v && typeof v === 'object') {
    for (const k of Object.keys(v)) deepFreeze(v[k]);
    Object.freeze(v);
  }
  return v;
}

/* ---------------- helper kiem hinh dang ---------------- */

function isObj(v) {
  if (v === null || typeof v !== 'object' || Array.isArray(v)) return false;
  const p = Object.getPrototypeOf(v);
  return p === Object.prototype || p === null;
}

function exactKeys(v, keys, at, errs) {
  if (!isObj(v)) {
    errs.push({ path: at, code: 'NOT_OBJECT' });
    return false;
  }
  for (const k of Object.keys(v)) if (!keys.includes(k)) errs.push({ path: `${at}.${k}`, code: 'UNKNOWN_KEY' });
  let ok = true;
  for (const k of keys) {
    if (!Object.prototype.hasOwnProperty.call(v, k)) {
      errs.push({ path: `${at}.${k}`, code: 'MISSING_KEY' });
      ok = false;
    }
  }
  return ok;
}

function checkStr(v, re, at, errs, code = 'INVALID_VALUE') {
  if (typeof v !== 'string' || !re.test(v)) {
    errs.push({ path: at, code });
    return false;
  }
  return true;
}

function isInt(v, min, max) {
  return Number.isInteger(v) && v >= min && v <= max;
}

/** Gia tri tho tu cong: chuoi/so/boolean giu nguyen kieu, thieu = null. Khong so hoa, khong mac dinh. */
function isRawScalar(v) {
  return v === null || typeof v === 'string' || typeof v === 'boolean' || (typeof v === 'number' && Number.isFinite(v));
}

function arrayEq(a, b) {
  return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((x, i) => x === b[i]);
}

function validRunId(s) {
  const m = typeof s === 'string' ? RE.runId.exec(s) : null;
  if (!m) return false;
  const [y, mo, d, h, mi, se] = m.slice(1).map(Number);
  if (mo < 1 || mo > 12 || d < 1) return false;
  if (d > new Date(Date.UTC(y, mo, 0)).getUTCDate()) return false;
  return h < 24 && mi < 60 && se < 60;
}

function uniqueSubset(v, allowed) {
  return Array.isArray(v) && v.length > 0 && v.every((x) => allowed.includes(x)) && new Set(v).size === v.length;
}

/* ---------------- context tin cay ---------------- */

const CONTEXT_KEYS = ['schema', 'issued_by', 'phap_nhan', 'profile', 'actor', 'binding', 'source_instance', 'scope_ref', 'run', 'request'];

/**
 * Kiem context do M2 coordinator cap. Strict: khoa la (duong dan, credential, override) bi tu choi.
 * Tra { ok, errors[{path,code}], value(deep frozen clone) }. Ham thuan, khong IO.
 */
function validateContext(ctx) {
  const errs = [];
  if (exactKeys(ctx, CONTEXT_KEYS, 'ctx', errs)) {
    if (ctx.schema !== SCHEMA.CONTEXT) errs.push({ path: 'ctx.schema', code: 'SCHEMA_INVALID' });
    if (ctx.issued_by !== 'M2_COORDINATOR') errs.push({ path: 'ctx.issued_by', code: 'ISSUER_INVALID' });
    if (exactKeys(ctx.phap_nhan, ['uuid', 'ma'], 'ctx.phap_nhan', errs)) {
      checkStr(ctx.phap_nhan.uuid, RE.uuid, 'ctx.phap_nhan.uuid', errs);
      if (checkStr(ctx.phap_nhan.ma, RE.maPn, 'ctx.phap_nhan.ma', errs) && WINDOWS_RESERVED.test(ctx.phap_nhan.ma)) {
        errs.push({ path: 'ctx.phap_nhan.ma', code: 'RESERVED_NAME' });
      }
    }
    if (exactKeys(ctx.profile, ['ref', 'revision'], 'ctx.profile', errs)) {
      if (checkStr(ctx.profile.ref, RE.ref, 'ctx.profile.ref', errs) && WINDOWS_RESERVED.test(ctx.profile.ref)) {
        errs.push({ path: 'ctx.profile.ref', code: 'RESERVED_NAME' });
      }
      checkStr(ctx.profile.revision, RE.revision, 'ctx.profile.revision', errs);
    }
    if (exactKeys(ctx.actor, ['id', 'nguon'], 'ctx.actor', errs)) {
      checkStr(ctx.actor.id, RE.actor, 'ctx.actor.id', errs);
      if (ctx.actor.nguon !== 'crm_phien') errs.push({ path: 'ctx.actor.nguon', code: 'ACTOR_SOURCE_INVALID' });
    }
    if (exactKeys(ctx.binding, ['selection_digest'], 'ctx.binding', errs)) {
      checkStr(ctx.binding.selection_digest, RE.hex64, 'ctx.binding.selection_digest', errs);
    }
    checkStr(ctx.source_instance, RE.instance, 'ctx.source_instance', errs);
    checkStr(ctx.scope_ref, RE.instance, 'ctx.scope_ref', errs);
    if (exactKeys(ctx.run, ['run_id', 'nonce', 'request_key'], 'ctx.run', errs)) {
      if (!validRunId(ctx.run.run_id)) errs.push({ path: 'ctx.run.run_id', code: 'INVALID_VALUE' });
      checkStr(ctx.run.nonce, RE.nonce, 'ctx.run.nonce', errs);
      checkStr(ctx.run.request_key, RE.requestKey, 'ctx.run.request_key', errs);
    }
    if (exactKeys(ctx.request, ['mode', 'year', 'month', 'types', 'formats'], 'ctx.request', errs)) {
      const r = ctx.request;
      if (r.mode !== 'month' && r.mode !== 'year') errs.push({ path: 'ctx.request.mode', code: 'INVALID_VALUE' });
      if (!isInt(r.year, 2020, 2100)) errs.push({ path: 'ctx.request.year', code: 'INVALID_VALUE' });
      if (r.mode === 'month' && !isInt(r.month, 1, 12)) errs.push({ path: 'ctx.request.month', code: 'INVALID_VALUE' });
      if (r.mode === 'year' && r.month !== null) errs.push({ path: 'ctx.request.month', code: 'MONTH_MUST_BE_NULL' });
      if (!uniqueSubset(r.types, Object.keys(TYPE_DIR))) errs.push({ path: 'ctx.request.types', code: 'INVALID_VALUE' });
      if (!uniqueSubset(r.formats, ['xml', 'pdf', 'excel'])) errs.push({ path: 'ctx.request.formats', code: 'INVALID_VALUE' });
    }
  }
  if (errs.length) return { ok: false, errors: errs, value: null };
  return { ok: true, errors: [], value: deepFreeze(JSON.parse(JSON.stringify(ctx))) };
}

function contextDigest(ctx) {
  return sha256Hex(Buffer.from(canonicalJson(ctx), 'utf8'));
}

/* ---------------- duong dan: containment + reparse toan chuoi ---------------- */

function assertSegment(s) {
  if (
    typeof s !== 'string' ||
    !SEGMENT_RE.test(s) ||
    /[. ]$/.test(s) ||
    s.includes('..') ||
    WINDOWS_RESERVED.test(s.split('.')[0])
  ) {
    throw new ProducerError('PATH_SEGMENT_INVALID');
  }
}

function samePath(a, b) {
  return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b;
}

/** Tu choi neu bat ky thanh phan da ton tai nao cua duong dan la symlink/junction, hoac realpath khac. */
function assertNoReparse(absPath) {
  if (typeof absPath !== 'string' || !path.isAbsolute(absPath)) throw new ProducerError('PATH_NOT_ABSOLUTE');
  const abs = path.resolve(absPath);
  const parsed = path.parse(abs);
  const parts = abs.slice(parsed.root.length).split(path.sep).filter(Boolean);
  let cur = parsed.root;
  let deepestExisting = parsed.root;
  for (const part of parts) {
    cur = path.join(cur, part);
    let st;
    try {
      st = fs.lstatSync(cur);
    } catch (e) {
      if (e.code === 'ENOENT') break;
      throw new ProducerError('PATH_STAT_FAILED');
    }
    if (st.isSymbolicLink()) throw new ProducerError('PATH_REPARSE');
    deepestExisting = cur;
  }
  let real;
  try {
    real = fs.realpathSync.native(deepestExisting);
  } catch (_) {
    throw new ProducerError('PATH_STAT_FAILED');
  }
  if (!samePath(path.resolve(real), path.resolve(deepestExisting))) throw new ProducerError('PATH_REPARSE');
}

function assertRoot(root) {
  if (typeof root !== 'string' || !path.isAbsolute(root)) throw new ProducerError('ROOT_INVALID');
  return path.resolve(root);
}

/** Goc cau hinh phai la thu muc that, ton tai, khong reparse. */
function assertRootDir(root) {
  const base = assertRoot(root);
  let st;
  try {
    st = fs.lstatSync(base);
  } catch (_) {
    throw new ProducerError('ROOT_INVALID');
  }
  if (!st.isDirectory() || st.isSymbolicLink()) throw new ProducerError('ROOT_INVALID');
  assertNoReparse(base);
  return base;
}

/** Ghep root + segments da kiem; khong tao gi. */
function resolveContained(root, segments) {
  const base = assertRoot(root);
  if (!Array.isArray(segments)) throw new ProducerError('PATH_SEGMENT_INVALID');
  segments.forEach(assertSegment);
  const abs = path.join(base, ...segments);
  const rel = path.relative(base, abs);
  if (rel.startsWith('..') || path.isAbsolute(rel)) throw new ProducerError('PATH_ESCAPE');
  assertNoReparse(abs);
  return abs;
}

/** Tao chuoi thu muc (khong recursive mu): moi cap kiem la thu muc that, khong reparse. */
function ensureDirChain(root, segments) {
  const base = assertRootDir(root);
  resolveContained(base, segments);
  let cur = base;
  for (const seg of segments) {
    cur = path.join(cur, seg);
    try {
      fs.mkdirSync(cur);
    } catch (e) {
      if (e.code !== 'EEXIST') throw new ProducerError('DIR_CREATE_FAILED');
    }
    const st = fs.lstatSync(cur);
    if (!st.isDirectory() || st.isSymbolicLink()) throw new ProducerError('PATH_REPARSE');
  }
  assertNoReparse(cur);
  return cur;
}

/** Tao thu muc cuoi doc quyen; da ton tai (cung giay/collision) -> RUN_DIR_CONFLICT, khong dung lai. */
function createDirExclusive(root, segments) {
  if (!Array.isArray(segments) || !segments.length) throw new ProducerError('PATH_SEGMENT_INVALID');
  const parent = ensureDirChain(root, segments.slice(0, -1));
  const last = segments[segments.length - 1];
  assertSegment(last);
  const p = path.join(parent, last);
  try {
    fs.mkdirSync(p);
  } catch (e) {
    if (e.code === 'EEXIST') throw new ProducerError('RUN_DIR_CONFLICT');
    throw new ProducerError('DIR_CREATE_FAILED');
  }
  assertNoReparse(p);
  return p;
}

/**
 * Ghi file CreateNew ('wx'). Da ton tai: chi chap nhan replay khi allowIdenticalReplay va bytes trung khop;
 * khac bytes -> FILE_EXISTS_DIFFERENT. Khong bao gio ghi de/xoa/doi ten.
 */
function writeExclusive(dir, name, bytes, opts = {}) {
  assertSegment(name);
  assertNoReparse(dir);
  const p = path.join(dir, name);
  const buf = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes);
  let fd;
  try {
    fd = fs.openSync(p, 'wx');
  } catch (e) {
    if (e.code !== 'EEXIST') throw new ProducerError('FILE_CREATE_FAILED');
    if (!opts.allowIdenticalReplay) throw new ProducerError('FILE_EXISTS');
    const st = fs.lstatSync(p);
    if (!st.isFile() || st.isSymbolicLink()) throw new ProducerError('FILE_EXISTS_DIFFERENT');
    const old = fs.readFileSync(p);
    if (!old.equals(buf)) throw new ProducerError('FILE_EXISTS_DIFFERENT');
    return { created: false, replay: true, file: name, sha256: sha256Hex(buf), bytes: buf.length };
  }
  try {
    let off = 0;
    while (off < buf.length) off += fs.writeSync(fd, buf, off, buf.length - off);
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  return { created: true, replay: false, file: name, sha256: sha256Hex(buf), bytes: buf.length };
}

/** Doc file thuong co gioi han; khong ton tai -> null. */
function readBounded(p, max) {
  let st;
  try {
    st = fs.lstatSync(p);
  } catch (e) {
    if (e.code === 'ENOENT') return null;
    throw new ProducerError('FILE_STAT_FAILED');
  }
  if (!st.isFile() || st.isSymbolicLink()) throw new ProducerError('FILE_NOT_REGULAR');
  if (st.size > max) throw new ProducerError('FILE_TOO_LARGE');
  return fs.readFileSync(p);
}

function readJsonBounded(p, max = LIMITS.JSON_BYTES) {
  const bytes = readBounded(p, max);
  if (!bytes) return null;
  try {
    return { bytes, value: JSON.parse(bytes.toString('utf8')) };
  } catch (_) {
    throw new ProducerError('JSON_UNREADABLE');
  }
}

/* ---------------- su kien dang nhap (facts) ---------------- */

function factObserved(value, basis) {
  return { trang_thai: 'OBSERVED', gia_tri: value, can_cu: basis };
}

function factUnknown(reason) {
  return { trang_thai: 'UNKNOWN', gia_tri: null, ly_do: reason };
}

function validateFact(f, kind, at, errs) {
  if (!isObj(f)) {
    errs.push({ path: at, code: 'FACT_INVALID' });
    return;
  }
  if (f.trang_thai === 'OBSERVED') {
    exactKeys(f, ['trang_thai', 'gia_tri', 'can_cu'], at, errs);
    const okVal = kind === 'boolean'
      ? typeof f.gia_tri === 'boolean'
      : typeof f.gia_tri === 'number' && Number.isFinite(f.gia_tri) && f.gia_tri >= 0;
    if (!okVal) errs.push({ path: `${at}.gia_tri`, code: 'FACT_VALUE_INVALID' });
    if (typeof f.can_cu !== 'string' || !RE.code.test(f.can_cu)) errs.push({ path: `${at}.can_cu`, code: 'FACT_BASIS_MISSING' });
  } else if (f.trang_thai === 'UNKNOWN') {
    exactKeys(f, ['trang_thai', 'gia_tri', 'ly_do'], at, errs);
    if (f.gia_tri !== null) errs.push({ path: `${at}.gia_tri`, code: 'FACT_UNKNOWN_HAS_VALUE' });
    if (typeof f.ly_do !== 'string' || !RE.code.test(f.ly_do)) errs.push({ path: `${at}.ly_do`, code: 'FACT_REASON_MISSING' });
  } else {
    errs.push({ path: `${at}.trang_thai`, code: 'FACT_STATE_INVALID' });
  }
}

/** Chuan hoa facts tu portal: thieu/sai -> UNKNOWN + ly do, khong bao gio doan true/false. */
function normalizeLoginFacts(raw) {
  const out = {};
  for (const [k, kind] of Object.entries(FACT_KIND)) {
    if (!isObj(raw) || raw[k] === undefined) {
      out[k] = factUnknown('PORTAL_FACT_MISSING');
      continue;
    }
    const e = [];
    validateFact(raw[k], kind, k, e);
    if (e.length) out[k] = factUnknown('PORTAL_FACT_INVALID');
    else out[k] = raw[k].trang_thai === 'OBSERVED'
      ? factObserved(raw[k].gia_tri, raw[k].can_cu)
      : factUnknown(raw[k].ly_do);
  }
  out.do_luong = Object.keys(FACT_KIND).every((k) => out[k].trang_thai === 'OBSERVED') ? 'COMPLETE' : 'PARTIAL';
  return out;
}

function unknownLoginFacts(reason) {
  const out = {};
  for (const k of Object.keys(FACT_KIND)) out[k] = factUnknown(reason);
  out.do_luong = 'PARTIAL';
  return out;
}

/* ---------------- manifest v1 ---------------- */

const MANIFEST_KEYS = [
  'schema', 'nguon', 'run_id', 'phap_nhan', 'ky', 'chieu', 'thu_muc_chieu', 'bat_dau', 'ket_thuc',
  'phien_ban_bo_tai', 'nguoi_bam', 'context', 'dang_nhap', 'nhom', 'tong', 'hoa_don', 'loi_chung',
  'trang_thai', 'ly_do_partial', 'gioi_han',
];
const CONTEXT_BLOCK_KEYS = [
  'digest', 'nonce', 'request_key_sha256', 'profile_ref', 'profile_revision', 'source_instance', 'scope_ref',
  'selection_digest', 'actor_nguon', 'quyet_dinh_quyen', 'profile_khoa_bo_qua',
];
const NHOM_KEYS = ['thu_tu', 'path', 'scope', 'ttxly', 'trang_thai', 'so_ban_ghi', 'so_moi', 'loi'];
const TONG_KEYS = ['tong_hd', 'xml_ok', 'khong_xml_goc', 'xml_loi', 'xml_khong_yeu_cau', 'pdf_ok', 'pdf_loi', 'bang_ke', 'bang_ke_trang_thai'];
const ITEM_KEYS = [
  'item_ordinal', 'key_raw', 'key_canonical', 'key_thieu', 'scope', 'ttxly', 'nhom_thu_tu', 'tthai_cong', 'tdlap',
  'dvtte_cong', 'xml_status', 'bang_chung', 'can_cu', 'file_xml', 'hash_xml', 'xml_bytes', 'ordinal_zip',
  'ten_entry_zip', 'xml_tep', 'zip', 'payload', 'file_pdf', 'hash_pdf', 'vai_tro_pdf', 'pdf_loi', 'loi',
];
const TEP_KEYS = ['file', 'sha256', 'bytes', 'ordinal_zip', 'ten_entry_zip'];
const ZIP_KEYS = ['file', 'sha256', 'bytes', 'coverage', 'entries', 'loi'];
const ZIP_ENTRY_KEYS = ['ordinal', 'name', 'declared_bytes', 'read_state', 'bytes', 'sha256', 'loi', 'trung_ten', 'file'];
const PAYLOAD_KEYS = ['file', 'sha256', 'bytes', 'loai'];
const BANG_KE_KEYS = ['file', 'sha256', 'bytes', 'so_cot'];

function errorObject(code, stage, httpStatus) {
  return {
    code: typeof code === 'string' && RE.code.test(code) ? code : 'UNSPECIFIED',
    stage: STAGES.includes(stage) ? stage : 'INTERNAL',
    http_status: Number.isInteger(httpStatus) && httpStatus >= 0 && httpStatus <= 999 ? httpStatus : null,
  };
}

function validateErr(e, at, errs) {
  if (!exactKeys(e, ['code', 'stage', 'http_status'], at, errs)) return;
  checkStr(e.code, RE.code, `${at}.code`, errs);
  if (!STAGES.includes(e.stage)) errs.push({ path: `${at}.stage`, code: 'INVALID_VALUE' });
  if (e.http_status !== null && !isInt(e.http_status, 0, 999)) errs.push({ path: `${at}.http_status`, code: 'INVALID_VALUE' });
}

function isFileName(v) {
  try {
    assertSegment(v);
    return true;
  } catch (_) {
    return false;
  }
}

function canonicalKeyOf(keyRaw) {
  return KEY_PARTS.map((k) => (keyRaw[k] === null || keyRaw[k] === undefined ? '' : String(keyRaw[k]))).join('|');
}

function missingKeyParts(keyRaw) {
  return KEY_PARTS.filter((k) => keyRaw[k] === null || keyRaw[k] === undefined || keyRaw[k] === '');
}

function computeTotals(items) {
  const list = Array.isArray(items) ? items : [];
  const count = (s) => list.filter((h) => h && h.xml_status === s).length;
  return {
    tong_hd: list.length,
    xml_ok: count('OK'),
    khong_xml_goc: count('KHONG_XML_GOC'),
    xml_loi: count('LOI'),
    xml_khong_yeu_cau: count('KHONG_YEU_CAU'),
    pdf_ok: list.filter((h) => h && h.file_pdf !== null && h.file_pdf !== undefined).length,
    pdf_loi: list.filter((h) => h && h.pdf_loi === true).length,
  };
}

/** Ly do PARTIAL tinh tu noi dung; PDF chi de xem lai nen khong lam giam coverage nguon. */
function computePartialReasons(m) {
  const nhom = Array.isArray(m && m.nhom) ? m.nhom : [];
  const items = Array.isArray(m && m.hoa_don) ? m.hoa_don : [];
  const loi = Array.isArray(m && m.loi_chung) ? m.loi_chung : [];
  const r = [];
  if (!nhom.length) r.push('KHONG_CO_NHOM');
  if (nhom.some((g) => !g || g.trang_thai !== 'OK')) r.push('NHOM_LOI');
  if (items.some((h) => h && h.xml_status === 'LOI')) r.push('XML_LOI');
  if (items.some((h) => h && h.zip && h.zip.coverage !== 'COMPLETE')) r.push('ZIP_PARTIAL');
  if (m && m.tong && m.tong.bang_ke_trang_thai === 'LOI') r.push('BANG_KE_LOI');
  if (loi.length) r.push('LOI_CHUNG');
  return r;
}

function scanForbidden(v, at, errs, depth = 0) {
  if (depth > 32) {
    errs.push({ path: at, code: 'TOO_DEEP' });
    return;
  }
  if (typeof v === 'string') {
    if (JWT_RE.test(v) || BEARER_RE.test(v)) errs.push({ path: at, code: 'FORBIDDEN_VALUE' });
    return;
  }
  if (Array.isArray(v)) {
    v.forEach((x, i) => scanForbidden(x, `${at}[${i}]`, errs, depth + 1));
    return;
  }
  if (v && typeof v === 'object') {
    for (const k of Object.keys(v)) {
      if (FORBIDDEN_KEY_RE.test(k)) errs.push({ path: `${at}.${k}`, code: 'FORBIDDEN_KEY' });
      scanForbidden(v[k], `${at}.${k}`, errs, depth + 1);
    }
  }
}

function validateZip(z, at, errs) {
  if (!exactKeys(z, ZIP_KEYS, at, errs)) return;
  if (z.file !== null && !isFileName(z.file)) errs.push({ path: `${at}.file`, code: 'INVALID_VALUE' });
  checkStr(z.sha256, RE.hex64, `${at}.sha256`, errs);
  if (!isInt(z.bytes, 0, Number.MAX_SAFE_INTEGER)) errs.push({ path: `${at}.bytes`, code: 'INVALID_VALUE' });
  if (z.file !== null && z.bytes > LIMITS.ZIP_BYTES) errs.push({ path: `${at}.file`, code: 'ZIP_STORED_OVER_LIMIT' });
  if (!['COMPLETE', 'PARTIAL'].includes(z.coverage)) errs.push({ path: `${at}.coverage`, code: 'INVALID_VALUE' });
  if (z.loi !== null) validateErr(z.loi, `${at}.loi`, errs);
  if (!Array.isArray(z.entries) || z.entries.length > LIMITS.ZIP_ENTRIES) {
    errs.push({ path: `${at}.entries`, code: 'INVALID_VALUE' });
    return;
  }
  const names = new Map();
  for (const e of z.entries) if (e && typeof e.name === 'string') names.set(e.name, (names.get(e.name) || 0) + 1);
  let anyError = false;
  z.entries.forEach((e, i) => {
    const ea = `${at}.entries[${i}]`;
    if (!exactKeys(e, ZIP_ENTRY_KEYS, ea, errs)) return;
    if (e.ordinal !== i + 1) errs.push({ path: `${ea}.ordinal`, code: 'ORDINAL_NOT_PHYSICAL_SEQUENCE' });
    if (typeof e.name !== 'string') errs.push({ path: `${ea}.name`, code: 'INVALID_VALUE' });
    if (e.declared_bytes !== null && !isInt(e.declared_bytes, 0, Number.MAX_SAFE_INTEGER)) errs.push({ path: `${ea}.declared_bytes`, code: 'INVALID_VALUE' });
    if (!ZIP_READ_STATES.includes(e.read_state)) errs.push({ path: `${ea}.read_state`, code: 'INVALID_VALUE' });
    if (e.trung_ten !== ((names.get(e.name) || 0) > 1)) errs.push({ path: `${ea}.trung_ten`, code: 'DUPLICATE_FLAG_MISMATCH' });
    if (e.read_state === 'READ_OK') {
      if (!isInt(e.bytes, 1, LIMITS.XML_BYTES)) errs.push({ path: `${ea}.bytes`, code: 'INVALID_VALUE' });
      checkStr(e.sha256, RE.hex64, `${ea}.sha256`, errs);
      if (!isFileName(e.file)) errs.push({ path: `${ea}.file`, code: 'INVALID_VALUE' });
      if (e.loi !== null) errs.push({ path: `${ea}.loi`, code: 'READ_OK_HAS_ERROR' });
    } else {
      if (e.bytes !== null || e.sha256 !== null || e.file !== null) errs.push({ path: ea, code: 'UNREAD_ENTRY_HAS_OUTPUT' });
      if (e.read_state === 'READ_ERROR') {
        anyError = true;
        if (e.loi === null) errs.push({ path: `${ea}.loi`, code: 'READ_ERROR_WITHOUT_CODE' });
        else validateErr(e.loi, `${ea}.loi`, errs);
      } else if (e.loi !== null) {
        validateErr(e.loi, `${ea}.loi`, errs);
      }
    }
  });
  if (z.coverage === 'COMPLETE' && (anyError || z.loi !== null)) errs.push({ path: `${at}.coverage`, code: 'ZIP_COVERAGE_OVERSTATED' });
}

function validateItem(h, i, errs) {
  const at = `m.hoa_don[${i}]`;
  if (!exactKeys(h, ITEM_KEYS, at, errs)) return;
  if (h.item_ordinal !== i + 1) errs.push({ path: `${at}.item_ordinal`, code: 'ORDINAL_INVALID' });
  if (exactKeys(h.key_raw, KEY_PARTS.slice(), `${at}.key_raw`, errs)) {
    for (const k of KEY_PARTS) if (!isRawScalar(h.key_raw[k])) errs.push({ path: `${at}.key_raw.${k}`, code: 'RAW_VALUE_INVALID' });
    if (h.key_canonical !== canonicalKeyOf(h.key_raw)) errs.push({ path: `${at}.key_canonical`, code: 'KEY_CANONICAL_MISMATCH' });
    if (!arrayEq(h.key_thieu, missingKeyParts(h.key_raw))) errs.push({ path: `${at}.key_thieu`, code: 'KEY_MISSING_LIST_MISMATCH' });
  }
  if (!SCOPES.includes(h.scope)) errs.push({ path: `${at}.scope`, code: 'INVALID_VALUE' });
  for (const k of ['ttxly', 'tthai_cong', 'tdlap', 'dvtte_cong']) {
    if (!isRawScalar(h[k])) errs.push({ path: `${at}.${k}`, code: 'RAW_VALUE_INVALID' });
  }
  if (h.nhom_thu_tu !== null && !isInt(h.nhom_thu_tu, 1, 1000)) errs.push({ path: `${at}.nhom_thu_tu`, code: 'INVALID_VALUE' });
  if (!XML_STATUS.includes(h.xml_status)) {
    errs.push({ path: `${at}.xml_status`, code: 'INVALID_VALUE' });
    return;
  }
  const noXmlFields = () => {
    for (const k of ['file_xml', 'hash_xml', 'xml_bytes', 'ordinal_zip', 'ten_entry_zip']) {
      if (h[k] !== null) errs.push({ path: `${at}.${k}`, code: 'XML_FIELD_WITHOUT_XML' });
    }
    if (!Array.isArray(h.xml_tep) || h.xml_tep.length) errs.push({ path: `${at}.xml_tep`, code: 'XML_FIELD_WITHOUT_XML' });
  };
  if (h.xml_status === 'OK') {
    if (!Array.isArray(h.xml_tep) || !h.xml_tep.length) {
      errs.push({ path: `${at}.xml_tep`, code: 'XML_OK_WITHOUT_BYTES' });
    } else {
      h.xml_tep.forEach((t, k) => {
        const ta = `${at}.xml_tep[${k}]`;
        if (!exactKeys(t, TEP_KEYS, ta, errs)) return;
        if (!isFileName(t.file)) errs.push({ path: `${ta}.file`, code: 'INVALID_VALUE' });
        checkStr(t.sha256, RE.hex64, `${ta}.sha256`, errs);
        if (!isInt(t.bytes, 1, LIMITS.XML_BYTES)) errs.push({ path: `${ta}.bytes`, code: 'INVALID_VALUE' });
        if (t.ordinal_zip !== null) {
          const e = h.zip && Array.isArray(h.zip.entries) ? h.zip.entries[t.ordinal_zip - 1] : null;
          if (!e || e.read_state !== 'READ_OK' || e.name !== t.ten_entry_zip || e.sha256 !== t.sha256 || e.bytes !== t.bytes || e.file !== t.file) {
            errs.push({ path: ta, code: 'ZIP_ENTRY_LINK_MISMATCH' });
          }
        } else if (t.ten_entry_zip !== null) {
          errs.push({ path: `${ta}.ten_entry_zip`, code: 'INVALID_VALUE' });
        }
      });
      const t0 = h.xml_tep[0] || {};
      if (h.file_xml !== t0.file || h.hash_xml !== t0.sha256 || h.xml_bytes !== t0.bytes ||
          h.ordinal_zip !== t0.ordinal_zip || h.ten_entry_zip !== t0.ten_entry_zip) {
        errs.push({ path: `${at}.file_xml`, code: 'PRIMARY_XML_MISMATCH' });
      }
    }
    if (h.bang_chung !== 'XML') errs.push({ path: `${at}.bang_chung`, code: 'INVALID_VALUE' });
    if (h.can_cu !== null) errs.push({ path: `${at}.can_cu`, code: 'INVALID_VALUE' });
    if (h.loi !== null) errs.push({ path: `${at}.loi`, code: 'XML_OK_HAS_ERROR' });
  } else if (h.xml_status === 'KHONG_XML_GOC') {
    noXmlFields();
    if (h.bang_chung !== 'BANG_KE') errs.push({ path: `${at}.bang_chung`, code: 'BANG_KE_EVIDENCE_REQUIRED' });
    if (typeof h.can_cu !== 'string' || !RE.code.test(h.can_cu)) errs.push({ path: `${at}.can_cu`, code: 'NO_ORIGINAL_BASIS_REQUIRED' });
    if (h.loi !== null) errs.push({ path: `${at}.loi`, code: 'INVALID_VALUE' });
    if (h.zip !== null || h.payload !== null) errs.push({ path: at, code: 'NO_ORIGINAL_HAS_PAYLOAD' });
  } else if (h.xml_status === 'LOI') {
    noXmlFields();
    if (h.bang_chung !== null || h.can_cu !== null) errs.push({ path: `${at}.bang_chung`, code: 'INVALID_VALUE' });
    if (h.loi === null) errs.push({ path: `${at}.loi`, code: 'ERROR_CODE_REQUIRED' });
    else validateErr(h.loi, `${at}.loi`, errs);
  } else {
    noXmlFields();
    if (h.bang_chung !== null || h.can_cu !== null || h.loi !== null || h.zip !== null || h.payload !== null) {
      errs.push({ path: at, code: 'NOT_REQUESTED_HAS_DATA' });
    }
  }
  if (h.zip !== null) validateZip(h.zip, `${at}.zip`, errs);
  if (h.payload !== null && exactKeys(h.payload, PAYLOAD_KEYS, `${at}.payload`, errs)) {
    if (h.payload.file !== null && !isFileName(h.payload.file)) errs.push({ path: `${at}.payload.file`, code: 'INVALID_VALUE' });
    checkStr(h.payload.sha256, RE.hex64, `${at}.payload.sha256`, errs);
    if (!isInt(h.payload.bytes, 0, Number.MAX_SAFE_INTEGER)) errs.push({ path: `${at}.payload.bytes`, code: 'INVALID_VALUE' });
    if (!['XML', 'UNKNOWN'].includes(h.payload.loai)) errs.push({ path: `${at}.payload.loai`, code: 'INVALID_VALUE' });
    if (h.xml_status !== 'LOI') errs.push({ path: `${at}.payload`, code: 'PAYLOAD_ONLY_FOR_ERROR' });
  }
  if (h.file_pdf === null) {
    if (h.hash_pdf !== null || h.vai_tro_pdf !== null) errs.push({ path: `${at}.file_pdf`, code: 'PDF_FIELDS_INCONSISTENT' });
  } else {
    if (!isFileName(h.file_pdf)) errs.push({ path: `${at}.file_pdf`, code: 'INVALID_VALUE' });
    checkStr(h.hash_pdf, RE.hex64, `${at}.hash_pdf`, errs);
    if (h.vai_tro_pdf !== 'XEM_LAI') errs.push({ path: `${at}.vai_tro_pdf`, code: 'PDF_IS_REVIEW_ONLY' });
    if (h.xml_status !== 'OK') errs.push({ path: `${at}.file_pdf`, code: 'PDF_WITHOUT_XML' });
  }
  if (typeof h.pdf_loi !== 'boolean') errs.push({ path: `${at}.pdf_loi`, code: 'INVALID_VALUE' });
}

/** Tra danh sach loi [{path, code}] (rong = hop le). Khong nem. */
function validateManifest(m) {
  const errs = [];
  try {
    if (!exactKeys(m, MANIFEST_KEYS, 'm', errs)) return errs;
    scanForbidden(m, 'm', errs);
    if (m.schema !== SCHEMA.MANIFEST) errs.push({ path: 'm.schema', code: 'SCHEMA_INVALID' });
    if (m.nguon !== 'TAI_MOI') errs.push({ path: 'm.nguon', code: 'NGUON_UNSUPPORTED' });
    if (!validRunId(m.run_id)) errs.push({ path: 'm.run_id', code: 'INVALID_VALUE' });
    if (exactKeys(m.phap_nhan, ['uuid', 'ma'], 'm.phap_nhan', errs)) {
      checkStr(m.phap_nhan.uuid, RE.uuid, 'm.phap_nhan.uuid', errs);
      checkStr(m.phap_nhan.ma, RE.maPn, 'm.phap_nhan.ma', errs);
    }
    checkStr(m.ky, RE.ky, 'm.ky', errs);
    if (!Object.prototype.hasOwnProperty.call(TYPE_DIR, m.chieu)) errs.push({ path: 'm.chieu', code: 'INVALID_VALUE' });
    else if (m.thu_muc_chieu !== TYPE_DIR[m.chieu]) errs.push({ path: 'm.thu_muc_chieu', code: 'INVALID_VALUE' });
    if (checkStr(m.bat_dau, RE.iso, 'm.bat_dau', errs) && checkStr(m.ket_thuc, RE.iso, 'm.ket_thuc', errs) && m.ket_thuc < m.bat_dau) {
      errs.push({ path: 'm.ket_thuc', code: 'END_BEFORE_START' });
    }
    if (typeof m.phien_ban_bo_tai !== 'string' || !m.phien_ban_bo_tai) errs.push({ path: 'm.phien_ban_bo_tai', code: 'INVALID_VALUE' });
    checkStr(m.nguoi_bam, RE.actor, 'm.nguoi_bam', errs);
    if (exactKeys(m.context, CONTEXT_BLOCK_KEYS, 'm.context', errs)) {
      const c = m.context;
      checkStr(c.digest, RE.hex64, 'm.context.digest', errs);
      checkStr(c.nonce, RE.nonce, 'm.context.nonce', errs);
      checkStr(c.request_key_sha256, RE.hex64, 'm.context.request_key_sha256', errs);
      checkStr(c.profile_ref, RE.ref, 'm.context.profile_ref', errs);
      checkStr(c.profile_revision, RE.revision, 'm.context.profile_revision', errs);
      checkStr(c.source_instance, RE.instance, 'm.context.source_instance', errs);
      checkStr(c.scope_ref, RE.instance, 'm.context.scope_ref', errs);
      checkStr(c.selection_digest, RE.hex64, 'm.context.selection_digest', errs);
      if (c.actor_nguon !== 'crm_phien') errs.push({ path: 'm.context.actor_nguon', code: 'INVALID_VALUE' });
      if (c.quyet_dinh_quyen !== 'NGOAI_PRODUCER_CHUA_KIEM') errs.push({ path: 'm.context.quyet_dinh_quyen', code: 'INVALID_VALUE' });
      if (!Array.isArray(c.profile_khoa_bo_qua) || !c.profile_khoa_bo_qua.every((k) => k === 'DOWNLOAD_DIR')) {
        errs.push({ path: 'm.context.profile_khoa_bo_qua', code: 'INVALID_VALUE' });
      }
    }
    if (exactKeys(m.gioi_han, ['xml_bytes', 'zip_bytes', 'zip_entries'], 'm.gioi_han', errs)) {
      if (m.gioi_han.xml_bytes !== LIMITS.XML_BYTES || m.gioi_han.zip_bytes !== LIMITS.ZIP_BYTES || m.gioi_han.zip_entries !== LIMITS.ZIP_ENTRIES) {
        errs.push({ path: 'm.gioi_han', code: 'LIMITS_MISMATCH' });
      }
    }
    if (exactKeys(m.dang_nhap, Object.keys(FACT_KIND).concat(['do_luong']), 'm.dang_nhap', errs)) {
      for (const [k, kind] of Object.entries(FACT_KIND)) validateFact(m.dang_nhap[k], kind, `m.dang_nhap.${k}`, errs);
      const all = Object.keys(FACT_KIND).every((k) => m.dang_nhap[k] && m.dang_nhap[k].trang_thai === 'OBSERVED');
      if (m.dang_nhap.do_luong !== (all ? 'COMPLETE' : 'PARTIAL')) errs.push({ path: 'm.dang_nhap.do_luong', code: 'LOGIN_MEASURE_OVERSTATED' });
    }
    if (!Array.isArray(m.nhom)) errs.push({ path: 'm.nhom', code: 'INVALID_VALUE' });
    else m.nhom.forEach((g, i) => {
      const at = `m.nhom[${i}]`;
      if (!exactKeys(g, NHOM_KEYS, at, errs)) return;
      if (g.thu_tu !== i + 1) errs.push({ path: `${at}.thu_tu`, code: 'ORDINAL_INVALID' });
      checkStr(g.path, RE.apiPath, `${at}.path`, errs);
      if (!SCOPES.includes(g.scope)) errs.push({ path: `${at}.scope`, code: 'INVALID_VALUE' });
      if (!isRawScalar(g.ttxly)) errs.push({ path: `${at}.ttxly`, code: 'RAW_VALUE_INVALID' });
      if (g.trang_thai === 'OK') {
        if (!isInt(g.so_ban_ghi, 0, Number.MAX_SAFE_INTEGER) || !isInt(g.so_moi, 0, Number.MAX_SAFE_INTEGER) || g.so_moi > g.so_ban_ghi) {
          errs.push({ path: `${at}.so_ban_ghi`, code: 'INVALID_VALUE' });
        }
        if (g.loi !== null) errs.push({ path: `${at}.loi`, code: 'INVALID_VALUE' });
      } else if (g.trang_thai === 'LOI') {
        if (g.so_ban_ghi !== null || g.so_moi !== null) errs.push({ path: `${at}.so_ban_ghi`, code: 'FAILED_GROUP_HAS_COUNT' });
        if (g.loi === null) errs.push({ path: `${at}.loi`, code: 'GROUP_ERROR_REQUIRED' });
        else validateErr(g.loi, `${at}.loi`, errs);
      } else {
        errs.push({ path: `${at}.trang_thai`, code: 'INVALID_VALUE' });
      }
    });
    if (!Array.isArray(m.hoa_don)) errs.push({ path: 'm.hoa_don', code: 'INVALID_VALUE' });
    else m.hoa_don.forEach((h, i) => validateItem(h, i, errs));
    if (!Array.isArray(m.loi_chung)) errs.push({ path: 'm.loi_chung', code: 'INVALID_VALUE' });
    else m.loi_chung.forEach((e, i) => validateErr(e, `m.loi_chung[${i}]`, errs));
    if (exactKeys(m.tong, TONG_KEYS, 'm.tong', errs)) {
      const exp = computeTotals(m.hoa_don);
      for (const k of Object.keys(exp)) if (m.tong[k] !== exp[k]) errs.push({ path: `m.tong.${k}`, code: 'TOTALS_MISMATCH' });
      if (!['OK', 'LOI', 'KHONG_YEU_CAU'].includes(m.tong.bang_ke_trang_thai)) {
        errs.push({ path: 'm.tong.bang_ke_trang_thai', code: 'INVALID_VALUE' });
      } else if (m.tong.bang_ke_trang_thai === 'OK') {
        if (exactKeys(m.tong.bang_ke, BANG_KE_KEYS, 'm.tong.bang_ke', errs)) {
          if (!isFileName(m.tong.bang_ke.file)) errs.push({ path: 'm.tong.bang_ke.file', code: 'INVALID_VALUE' });
          checkStr(m.tong.bang_ke.sha256, RE.hex64, 'm.tong.bang_ke.sha256', errs);
          if (!isInt(m.tong.bang_ke.bytes, 1, Number.MAX_SAFE_INTEGER)) errs.push({ path: 'm.tong.bang_ke.bytes', code: 'INVALID_VALUE' });
          if (!isInt(m.tong.bang_ke.so_cot, 20, 20)) errs.push({ path: 'm.tong.bang_ke.so_cot', code: 'EXCEL_COLUMNS_MISMATCH' });
        }
      } else if (m.tong.bang_ke !== null) {
        errs.push({ path: 'm.tong.bang_ke', code: 'INVALID_VALUE' });
      }
    }
    const reasons = computePartialReasons(m);
    if (!arrayEq(m.ly_do_partial, reasons)) errs.push({ path: 'm.ly_do_partial', code: 'PARTIAL_REASONS_MISMATCH' });
    if (!RUN_STATUS.includes(m.trang_thai)) errs.push({ path: 'm.trang_thai', code: 'INVALID_VALUE' });
    else if (m.trang_thai === 'FAILED') {
      if (!Array.isArray(m.loi_chung) || !m.loi_chung.length) errs.push({ path: 'm.trang_thai', code: 'FAILED_WITHOUT_ERROR' });
    } else if (m.trang_thai !== (reasons.length ? 'PARTIAL' : 'COMPLETE')) {
      errs.push({ path: 'm.trang_thai', code: 'STATUS_INCONSISTENT' });
    }
  } catch (_) {
    errs.push({ path: 'm', code: 'VALIDATOR_EXCEPTION' });
  }
  return errs;
}

function buildContextBlock(ctx, ids, ignoredProfileKeys) {
  return {
    digest: ids.digest,
    nonce: ctx.run.nonce,
    request_key_sha256: ids.keyHash,
    profile_ref: ctx.profile.ref,
    profile_revision: ctx.profile.revision,
    source_instance: ctx.source_instance,
    scope_ref: ctx.scope_ref,
    selection_digest: ctx.binding.selection_digest,
    actor_nguon: ctx.actor.nguon,
    quyet_dinh_quyen: 'NGOAI_PRODUCER_CHUA_KIEM',
    profile_khoa_bo_qua: (ignoredProfileKeys || []).slice(),
  };
}

/* ---------------- observation (K1, khong phai quyen/nghia vu) ---------------- */

function buildObservations(manifest, manifestSha) {
  const nonce = manifest.context.nonce;
  return {
    schema: SCHEMA.OBSERVATIONS,
    y_nghia: 'K1_SOURCE_OBSERVATION_ONLY',
    nguon: manifest.nguon,
    run_id: manifest.run_id,
    nonce,
    context_digest: manifest.context.digest,
    manifest_sha256: manifestSha,
    phap_nhan_uuid: manifest.phap_nhan.uuid,
    ky: manifest.ky,
    chieu: manifest.chieu,
    items: manifest.hoa_don.map((h) => ({
      observation_id: sha256Hex(Buffer.from(`${nonce}|${manifestSha}|${h.item_ordinal}`, 'utf8')),
      item_ordinal: h.item_ordinal,
      key_canonical: h.key_canonical,
      key_raw: Object.assign({}, h.key_raw),
      scope: h.scope,
      ttxly: h.ttxly,
      tthai_cong: h.tthai_cong,
      tdlap: h.tdlap,
      dvtte_cong: h.dvtte_cong,
      xml_status: h.xml_status,
      bang_chung: h.bang_chung,
      hash_xml: h.hash_xml,
      xml_hashes: h.xml_tep.map((t) => t.sha256),
    })),
  };
}

function verifyObservations(obs, manifest, manifestSha) {
  const errs = [];
  try {
    if (canonicalJson(obs) !== canonicalJson(buildObservations(manifest, manifestSha))) {
      errs.push({ path: 'observations', code: 'OBSERVATIONS_MISMATCH' });
    }
  } catch (_) {
    errs.push({ path: 'observations', code: 'OBSERVATIONS_UNREADABLE' });
  }
  return errs;
}

/* ---------------- intent / nonce / run started / receipt ---------------- */

function buildIntent({ ctx, ids, plan, createdAt }) {
  return {
    schema: SCHEMA.INTENT,
    request_key_sha256: ids.keyHash,
    context_digest: ids.digest,
    nonce: ctx.run.nonce,
    run_id: ctx.run.run_id,
    phap_nhan: { uuid: ctx.phap_nhan.uuid, ma: ctx.phap_nhan.ma },
    nguoi_bam: ctx.actor.id,
    ky_chieu: plan.map((p) => ({ ky: p.ky, chieu: p.type, segments: p.segments.slice(), run_rel: p.run_rel })),
    tao_luc: createdAt,
  };
}

function validateIntent(x) {
  const errs = [];
  if (!exactKeys(x, ['schema', 'request_key_sha256', 'context_digest', 'nonce', 'run_id', 'phap_nhan', 'nguoi_bam', 'ky_chieu', 'tao_luc'], 'intent', errs)) return errs;
  if (x.schema !== SCHEMA.INTENT) errs.push({ path: 'intent.schema', code: 'SCHEMA_INVALID' });
  checkStr(x.request_key_sha256, RE.hex64, 'intent.request_key_sha256', errs);
  checkStr(x.context_digest, RE.hex64, 'intent.context_digest', errs);
  if (!Array.isArray(x.ky_chieu) || !x.ky_chieu.length) errs.push({ path: 'intent.ky_chieu', code: 'INVALID_VALUE' });
  else x.ky_chieu.forEach((k, i) => {
    if (!exactKeys(k, ['ky', 'chieu', 'segments', 'run_rel'], `intent.ky_chieu[${i}]`, errs)) return;
    if (!Array.isArray(k.segments) || k.segments.length !== 4 || !k.segments.every(isFileName)) {
      errs.push({ path: `intent.ky_chieu[${i}].segments`, code: 'INVALID_VALUE' });
    }
  });
  return errs;
}

function buildNonceRecord(ids) {
  return { schema: SCHEMA.NONCE, request_key_sha256: ids.keyHash, context_digest: ids.digest };
}

function buildRunStarted({ ctx, ids, plan, createdAt }) {
  return {
    schema: SCHEMA.RUN_STARTED,
    context_digest: ids.digest,
    request_key_sha256: ids.keyHash,
    nonce: ctx.run.nonce,
    run_id: ctx.run.run_id,
    ky: plan.ky,
    chieu: plan.type,
    phap_nhan_uuid: ctx.phap_nhan.uuid,
    tao_luc: createdAt,
  };
}

function buildReceipt({ ctx, ids, runs, trangThai, loiChung, xungDot, batDau, ketThuc, version }) {
  return {
    schema: SCHEMA.RECEIPT,
    request_key_sha256: ids.keyHash,
    context_digest: ids.digest,
    nonce: ctx.run.nonce,
    run_id: ctx.run.run_id,
    phap_nhan: { uuid: ctx.phap_nhan.uuid, ma: ctx.phap_nhan.ma },
    nguoi_bam: ctx.actor.id,
    phien_ban_bo_tai: version,
    trang_thai: trangThai,
    runs,
    loi_chung: loiChung,
    xung_dot: xungDot,
    bat_dau: batDau,
    ket_thuc: ketThuc,
  };
}

const RECEIPT_KEYS = ['schema', 'request_key_sha256', 'context_digest', 'nonce', 'run_id', 'phap_nhan', 'nguoi_bam',
  'phien_ban_bo_tai', 'trang_thai', 'runs', 'loi_chung', 'xung_dot', 'bat_dau', 'ket_thuc'];
const RECEIPT_RUN_KEYS = ['ky', 'chieu', 'run_rel', 'trang_thai', 'manifest_sha256', 'observations_sha256', 'loi'];

/**
 * Kiem hinh dang + nhat quan noi bo cua receipt (khong can context). FIX01: du truong dinh danh, hash bat buoc
 * khi run co manifest, va trang thai tong khop trang thai run (COMPLETE chi khi moi run COMPLETE).
 */
function validateReceipt(x) {
  const errs = [];
  if (!exactKeys(x, RECEIPT_KEYS, 'receipt', errs)) return errs;
  scanForbidden(x, 'receipt', errs);
  if (x.schema !== SCHEMA.RECEIPT) errs.push({ path: 'receipt.schema', code: 'SCHEMA_INVALID' });
  checkStr(x.request_key_sha256, RE.hex64, 'receipt.request_key_sha256', errs);
  checkStr(x.context_digest, RE.hex64, 'receipt.context_digest', errs);
  checkStr(x.nonce, RE.nonce, 'receipt.nonce', errs);
  if (!validRunId(x.run_id)) errs.push({ path: 'receipt.run_id', code: 'INVALID_VALUE' });
  if (exactKeys(x.phap_nhan, ['uuid', 'ma'], 'receipt.phap_nhan', errs)) {
    checkStr(x.phap_nhan.uuid, RE.uuid, 'receipt.phap_nhan.uuid', errs);
    checkStr(x.phap_nhan.ma, RE.maPn, 'receipt.phap_nhan.ma', errs);
  }
  checkStr(x.nguoi_bam, RE.actor, 'receipt.nguoi_bam', errs);
  if (typeof x.phien_ban_bo_tai !== 'string' || !x.phien_ban_bo_tai) errs.push({ path: 'receipt.phien_ban_bo_tai', code: 'INVALID_VALUE' });
  checkStr(x.bat_dau, RE.iso, 'receipt.bat_dau', errs);
  checkStr(x.ket_thuc, RE.iso, 'receipt.ket_thuc', errs);
  if (!RECEIPT_STATUS.includes(x.trang_thai)) errs.push({ path: 'receipt.trang_thai', code: 'INVALID_VALUE' });
  const loiChung = Array.isArray(x.loi_chung) ? x.loi_chung : null;
  if (!loiChung) errs.push({ path: 'receipt.loi_chung', code: 'INVALID_VALUE' });
  else loiChung.forEach((e, i) => validateErr(e, `receipt.loi_chung[${i}]`, errs));
  const xungDot = Array.isArray(x.xung_dot) && x.xung_dot.every((s) => typeof s === 'string' && s) ? x.xung_dot : null;
  if (!xungDot) errs.push({ path: 'receipt.xung_dot', code: 'INVALID_VALUE' });
  if (!Array.isArray(x.runs)) {
    errs.push({ path: 'receipt.runs', code: 'INVALID_VALUE' });
    return errs;
  }
  x.runs.forEach((r, i) => {
    const at = `receipt.runs[${i}]`;
    if (!exactKeys(r, RECEIPT_RUN_KEYS, at, errs)) return;
    checkStr(r.ky, RE.ky, `${at}.ky`, errs);
    if (!Object.prototype.hasOwnProperty.call(TYPE_DIR, r.chieu)) errs.push({ path: `${at}.chieu`, code: 'INVALID_VALUE' });
    if (typeof r.run_rel !== 'string' || !r.run_rel) errs.push({ path: `${at}.run_rel`, code: 'INVALID_VALUE' });
    if (!RECEIPT_RUN_STATUS.includes(r.trang_thai)) errs.push({ path: `${at}.trang_thai`, code: 'INVALID_VALUE' });
    const hasManifest = RUN_STATUS.includes(r.trang_thai);
    for (const k of ['manifest_sha256', 'observations_sha256']) {
      if (hasManifest) checkStr(r[k], RE.hex64, `${at}.${k}`, errs, 'RUN_HASH_REQUIRED');
      else if (r[k] !== null) errs.push({ path: `${at}.${k}`, code: 'RUN_HASH_WITHOUT_MANIFEST' });
    }
    if (!Array.isArray(r.loi) || !r.loi.every((c) => typeof c === 'string' && RE.code.test(c))) {
      errs.push({ path: `${at}.loi`, code: 'INVALID_VALUE' });
    }
  });
  const st = x.runs.map((r) => (r ? r.trang_thai : null));
  const allComplete = st.length > 0 && st.every((s) => s === 'COMPLETE');
  const anyVerified = st.some((s) => s === 'COMPLETE' || s === 'PARTIAL');
  const nLoi = loiChung ? loiChung.length : 0;
  const nXung = xungDot ? xungDot.length : 0;
  let consistent = true;
  if (x.trang_thai === 'COMPLETE') consistent = allComplete && nLoi === 0 && nXung === 0;
  else if (x.trang_thai === 'PARTIAL') consistent = st.length > 0 && !allComplete && nXung === 0;
  else if (x.trang_thai === 'FAILED') consistent = !anyVerified && nXung === 0;
  else if (x.trang_thai === 'CONFLICT') consistent = !anyVerified && nXung > 0;
  if (!consistent) errs.push({ path: 'receipt.trang_thai', code: 'RECEIPT_STATUS_INCONSISTENT' });
  return errs;
}

/**
 * FIX01: intent da luu phai khop context + identities da kiem: key/digest/nonce/run/actor/PN va moi ky/chieu
 * dan xuat dung tu request (khong phu thuoc dong ho hien tai). Tra danh sach loi (rong = khop).
 * FIX02: `expectedPlan` = phep chieu {ky,chieu,segments,run_rel} cua planRuns(ctx, intent.tao_luc) do job tinh;
 * intent.ky_chieu phai bang CHINH XAC (du so muc, dung thu tu, khong thieu/thua/lap). Thieu expectedPlan -> mismatch.
 */
function verifyIntentBinding(intent, ctx, ids, expectedPlan) {
  const errs = validateIntent(intent);
  if (errs.length) return errs;
  const need = (ok, p) => { if (!ok) errs.push({ path: p, code: 'INTENT_BINDING_MISMATCH' }); };
  need(intent.request_key_sha256 === ids.keyHash, 'intent.request_key_sha256');
  need(intent.context_digest === ids.digest, 'intent.context_digest');
  need(intent.nonce === ctx.run.nonce, 'intent.nonce');
  need(intent.run_id === ctx.run.run_id, 'intent.run_id');
  need(isObj(intent.phap_nhan) && intent.phap_nhan.uuid === ctx.phap_nhan.uuid && intent.phap_nhan.ma === ctx.phap_nhan.ma, 'intent.phap_nhan');
  need(intent.nguoi_bam === ctx.actor.id, 'intent.nguoi_bam');
  const seen = new Set();
  intent.ky_chieu.forEach((k, i) => {
    const m = typeof k.ky === 'string' && RE.ky.test(k.ky) ? k.ky.split('-').map(Number) : null;
    const kyOk = !!m && m[0] === ctx.request.year && (ctx.request.mode === 'year' || m[1] === ctx.request.month);
    const exp = [ctx.phap_nhan.ma, k.ky, TYPE_DIR[k.chieu], ctx.run.run_id];
    need(
      ctx.request.types.includes(k.chieu) && kyOk && arrayEq(k.segments, exp) &&
        k.run_rel === exp.join('/') && !seen.has(k.run_rel),
      `intent.ky_chieu[${i}]`
    );
    seen.add(k.run_rel);
  });
  if (ctx.request.mode === 'month') need(intent.ky_chieu.length === ctx.request.types.length, 'intent.ky_chieu');
  let fullPlan = false;
  try {
    fullPlan = Array.isArray(expectedPlan) && expectedPlan.length > 0 &&
      canonicalJson(intent.ky_chieu) === canonicalJson(expectedPlan);
  } catch (_) {
    fullPlan = false;
  }
  need(fullPlan, 'intent.ky_chieu.full_plan');
  return errs;
}

/**
 * FIX01: receipt chi duoc REPLAY khi khop intent + context + identities, pham vi ke hoach day du (tru CONFLICT
 * giu lich su dat cho), va moi run co manifest duoc kiem lai tren dia (hash manifest/observation, trang thai,
 * dinh danh). Chi doc; khong sua/ghi lai receipt.
 */
function verifyReceiptBinding({ receipt, intent, ctx, ids, downloadRoot }) {
  const errs = validateReceipt(receipt);
  if (errs.length) return errs;
  const bad = (p) => errs.push({ path: p, code: 'RECEIPT_BINDING_MISMATCH' });
  if (receipt.request_key_sha256 !== ids.keyHash || receipt.request_key_sha256 !== intent.request_key_sha256) bad('receipt.request_key_sha256');
  if (receipt.context_digest !== ids.digest || receipt.context_digest !== intent.context_digest) bad('receipt.context_digest');
  if (receipt.nonce !== ctx.run.nonce) bad('receipt.nonce');
  if (receipt.run_id !== ctx.run.run_id) bad('receipt.run_id');
  if (receipt.phap_nhan.uuid !== ctx.phap_nhan.uuid || receipt.phap_nhan.ma !== ctx.phap_nhan.ma) bad('receipt.phap_nhan');
  if (receipt.nguoi_bam !== ctx.actor.id) bad('receipt.nguoi_bam');
  const plan = new Map(intent.ky_chieu.map((k) => [k.run_rel, k]));
  const rels = receipt.runs.map((r) => r.run_rel);
  const scopeOk = receipt.trang_thai === 'CONFLICT'
    ? rels.every((r) => plan.has(r)) && new Set(rels).size === rels.length && receipt.xung_dot.every((s) => plan.has(s))
    : rels.length === intent.ky_chieu.length && rels.every((r, i) => r === intent.ky_chieu[i].run_rel);
  if (!scopeOk) bad('receipt.runs');
  receipt.runs.forEach((r, i) => {
    const at = `receipt.runs[${i}]`;
    const k = plan.get(r.run_rel);
    if (!k || k.ky !== r.ky || k.chieu !== r.chieu) {
      bad(at);
      return;
    }
    if (r.manifest_sha256 === null) return;
    let v;
    try {
      v = verifyRunDir(resolveContained(downloadRoot, k.segments), { context_digest: ids.digest });
    } catch (_) {
      bad(at);
      return;
    }
    const m = v.manifest;
    if (!v.ok || v.manifest_sha256 !== r.manifest_sha256 || v.observations_sha256 !== r.observations_sha256 ||
        !m || m.trang_thai !== r.trang_thai || m.run_id !== ctx.run.run_id || m.ky !== r.ky || m.chieu !== r.chieu ||
        m.nguoi_bam !== ctx.actor.id || m.phap_nhan.uuid !== ctx.phap_nhan.uuid || m.phap_nhan.ma !== ctx.phap_nhan.ma ||
        m.context.nonce !== ctx.run.nonce) {
      bad(at);
    }
  });
  return errs;
}

/* ---------------- kiem lai mot thu muc run (hash/tong/observation) ---------------- */

function fileMatches(runDir, name, sha, bytes, at, errs) {
  if (!isFileName(name)) {
    errs.push({ path: at, code: 'FILE_NAME_INVALID' });
    return;
  }
  let buf;
  try {
    buf = readBounded(path.join(runDir, name), LIMITS.ZIP_BYTES);
  } catch (e) {
    errs.push({ path: at, code: e.code || 'FILE_UNREADABLE' });
    return;
  }
  if (!buf) {
    errs.push({ path: at, code: 'FILE_MISSING' });
    return;
  }
  if (bytes !== null && buf.length !== bytes) errs.push({ path: at, code: 'SIZE_MISMATCH' });
  if (sha256Hex(buf) !== sha) errs.push({ path: at, code: 'HASH_MISMATCH' });
}

/**
 * Kiem lai run dir chi doc: manifest hop le, bytes chuan, moi file tham chieu ton tai dung hash/kich thuoc,
 * observations khop manifest digest, run.started khop context. File khong co trong manifest -> khong_ro_nguon.
 */
function verifyRunDir(runDir, expect = {}) {
  const out = { ok: false, errors: [], manifest_present: false, manifest: null, manifest_sha256: null, observations_sha256: null, khong_ro_nguon: [] };
  const errs = out.errors;
  try {
    assertNoReparse(runDir);
  } catch (e) {
    errs.push({ path: 'run_dir', code: e.code });
    return out;
  }
  let mj;
  try {
    mj = readJsonBounded(path.join(runDir, RUN_FILES.MANIFEST));
  } catch (e) {
    errs.push({ path: 'manifest', code: e.code || 'MANIFEST_UNREADABLE' });
    return out;
  }
  if (!mj) {
    errs.push({ path: 'manifest', code: 'MANIFEST_MISSING' });
    return out;
  }
  out.manifest_present = true;
  const m = mj.value;
  out.manifest = m;
  out.manifest_sha256 = sha256Hex(mj.bytes);
  errs.push(...validateManifest(m));
  try {
    if (!stableBytes(m).equals(mj.bytes)) errs.push({ path: 'manifest', code: 'MANIFEST_NOT_CANONICAL' });
  } catch (_) {
    errs.push({ path: 'manifest', code: 'MANIFEST_NOT_CANONICAL' });
  }
  if (expect.context_digest && (!m || !m.context || m.context.digest !== expect.context_digest)) {
    errs.push({ path: 'manifest.context.digest', code: 'CONTEXT_DIGEST_MISMATCH' });
  }
  const known = new Set(Object.values(RUN_FILES).map((n) => n.toLowerCase()));
  const items = m && Array.isArray(m.hoa_don) ? m.hoa_don : [];
  items.forEach((h, i) => {
    if (!h) return;
    const at = `m.hoa_don[${i}]`;
    (Array.isArray(h.xml_tep) ? h.xml_tep : []).forEach((t, k) => {
      if (!t) return;
      known.add(String(t.file).toLowerCase());
      fileMatches(runDir, t.file, t.sha256, t.bytes, `${at}.xml_tep[${k}]`, errs);
    });
    if (h.zip && h.zip.file !== null) {
      known.add(String(h.zip.file).toLowerCase());
      fileMatches(runDir, h.zip.file, h.zip.sha256, h.zip.bytes, `${at}.zip`, errs);
    }
    if (h.payload && h.payload.file !== null) {
      known.add(String(h.payload.file).toLowerCase());
      fileMatches(runDir, h.payload.file, h.payload.sha256, h.payload.bytes, `${at}.payload`, errs);
    }
    if (h.file_pdf) {
      known.add(String(h.file_pdf).toLowerCase());
      fileMatches(runDir, h.file_pdf, h.hash_pdf, null, `${at}.file_pdf`, errs);
    }
  });
  if (m && m.tong && m.tong.bang_ke) {
    known.add(String(m.tong.bang_ke.file).toLowerCase());
    fileMatches(runDir, m.tong.bang_ke.file, m.tong.bang_ke.sha256, m.tong.bang_ke.bytes, 'm.tong.bang_ke', errs);
  }
  try {
    const rs = readJsonBounded(path.join(runDir, RUN_FILES.STARTED));
    if (!rs) errs.push({ path: 'run_started', code: 'RUN_STARTED_MISSING' });
    else if (!m || !m.context || rs.value.context_digest !== m.context.digest || rs.value.run_id !== m.run_id ||
             rs.value.ky !== m.ky || rs.value.chieu !== m.chieu || rs.value.schema !== SCHEMA.RUN_STARTED) {
      errs.push({ path: 'run_started', code: 'RUN_STARTED_MISMATCH' });
    }
  } catch (e) {
    errs.push({ path: 'run_started', code: e.code || 'RUN_STARTED_UNREADABLE' });
  }
  try {
    const ob = readJsonBounded(path.join(runDir, RUN_FILES.OBSERVATIONS));
    if (!ob) errs.push({ path: 'observations', code: 'OBSERVATIONS_MISSING' });
    else {
      out.observations_sha256 = sha256Hex(ob.bytes);
      errs.push(...verifyObservations(ob.value, m, out.manifest_sha256));
    }
  } catch (e) {
    errs.push({ path: 'observations', code: e.code || 'OBSERVATIONS_UNREADABLE' });
  }
  try {
    for (const name of fs.readdirSync(runDir)) if (!known.has(name.toLowerCase())) out.khong_ro_nguon.push(name);
    out.khong_ro_nguon.sort();
  } catch (_) {
    errs.push({ path: 'run_dir', code: 'RUN_DIR_UNREADABLE' });
  }
  out.ok = errs.length === 0;
  return out;
}

module.exports = {
  SCHEMA,
  LIMITS,
  TYPE_DIR,
  INTENT_DIR,
  RUN_FILES,
  KEY_PARTS,
  XML_STATUS,
  STAGES,
  RE,
  ProducerError,
  sha256Hex,
  canonicalJson,
  stableBytes,
  validateContext,
  contextDigest,
  assertSegment,
  assertNoReparse,
  assertRootDir,
  resolveContained,
  ensureDirChain,
  createDirExclusive,
  writeExclusive,
  readBounded,
  readJsonBounded,
  factObserved,
  factUnknown,
  normalizeLoginFacts,
  unknownLoginFacts,
  errorObject,
  canonicalKeyOf,
  missingKeyParts,
  computeTotals,
  computePartialReasons,
  validateManifest,
  buildContextBlock,
  buildObservations,
  verifyObservations,
  buildIntent,
  validateIntent,
  buildNonceRecord,
  buildRunStarted,
  buildReceipt,
  validateReceipt,
  verifyIntentBinding,
  verifyReceiptBinding,
  verifyRunDir,
};
