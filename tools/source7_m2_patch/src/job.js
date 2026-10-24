'use strict';

const fs = require('fs');
const path = require('path');
const EventEmitter = require('events');

const cfg = require('../config');
const mf = require('./manifest');

const TYPE_DIR = mf.TYPE_DIR;
const TYPE_LABEL = { purchase: 'Mua vao', sold: 'Ban ra' };
const PAUSE_BETWEEN_MONTHS_MS = 4000; // nghi giua cac ky de tranh bi chan (429)
const PRODUCER_VERSION = 'source7-m2-00a-candidate-1';
const MAX_NAME_SUFFIX = 50;

const defaultClock = {
  now: () => Date.now(),
  sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
};

/* M2-00A: goc tai / ho so trinh duyet / profiles lay tu config.js (khong tu .env profile, khong tu HTTP). */
function defaultRoots() {
  const toolRoot = path.resolve(__dirname, '..');
  return {
    downloadRoot: path.resolve(toolRoot, cfg.DOWNLOAD_ROOT_DIR),
    browserProfileRoot: path.resolve(toolRoot, cfg.BROWSER_PROFILE_ROOT_DIR),
    profilesDir: path.resolve(toolRoot, cfg.PROFILES_DIR),
  };
}

function normalizeRoots(r) {
  const out = {};
  for (const k of ['downloadRoot', 'browserProfileRoot', 'profilesDir']) {
    if (!r || typeof r[k] !== 'string' || !path.isAbsolute(r[k])) throw new mf.ProducerError('ROOTS_INVALID');
    out[k] = path.resolve(r[k]);
  }
  return Object.freeze(out);
}

/**
 * Tao producer. Seam toi thieu cho kiem thu: portal / build / clock / loadCredential.
 * Mac dinh nap ./portal va ./build khi can (Playwright/ExcelJS chi nap luc that su dung).
 */
function createProducer(options = {}) {
  const roots = normalizeRoots(options.roots || defaultRoots());
  const clock = options.clock || defaultClock;
  const loadCredential = options.loadCredential || loadProfileCredential;
  let portalImpl = options.portal || null;
  let buildImpl = options.build || null;
  let AdmZipImpl = null;
  const portal = () => portalImpl || (portalImpl = require('./portal'));
  const build = () => buildImpl || (buildImpl = require('./build'));
  const AdmZip = () => AdmZipImpl || (AdmZipImpl = require('adm-zip'));

  // Trang thai 1 job (chi chay 1 job tai 1 thoi diem)
  const state = {
    running: false,
    id: null,
    requestKeyHash: null,
    done: null,
    events: [],
    emitter: new EventEmitter(),
    summary: null,
  };
  state.emitter.setMaxListeners(50);

  const iso = () => new Date(clock.now()).toISOString();

  function redact(job, s) {
    let out = String(s);
    if (job && job.secrets) for (const sec of job.secrets) if (sec) out = out.split(sec).join('[AN]');
    return out;
  }

  function emit(job, type, payload) {
    const ev = { type, payload, ts: clock.now() };
    state.events.push(ev);
    if (state.events.length > 5000) state.events.shift();
    state.emitter.emit('event', ev);
    if (!job || !job.logPath) return;
    let line = null;
    if (type === 'log') line = payload.msg;
    else if (type === 'error') line = 'ERROR: ' + (payload.code || '');
    else if (type === 'phase') line = '--- ' + (payload.label || '') + ' ' + (payload.monthTag || '') + ' ---';
    else if (type === 'month') line = '##### KY ' + (payload.monthTag || '') + ' #####';
    else if (type === 'done') line = '=== KET THUC (' + (payload.trang_thai || '') + ') ===';
    if (line !== null) {
      try { fs.appendFileSync(job.logPath, line + '\n'); } catch (_) {}
    }
  }
  const log = (job, msg) => emit(job, 'log', { msg: redact(job, msg) });

  function getState() {
    return state;
  }

  function identities(ctx) {
    return {
      digest: mf.contextDigest(ctx),
      keyHash: mf.sha256Hex(Buffer.from(ctx.run.request_key, 'utf8')),
      nonceHash: mf.sha256Hex(Buffer.from(ctx.run.nonce, 'utf8')),
    };
  }

  function validated(rawContext) {
    const v = mf.validateContext(rawContext);
    if (!v.ok) throw new mf.ProducerError('CONTEXT_INVALID', v.errors);
    return v.value;
  }

  /** Doc intent/receipt/nonce da co (chi doc). */
  function readPrior(ctx, ids) {
    mf.assertRootDir(roots.downloadRoot);
    const intentDir = mf.resolveContained(roots.downloadRoot, [ctx.phap_nhan.ma, mf.INTENT_DIR]);
    const out = { intentDir, intent: null, receipt: null, receiptSha: null, nonceRecord: null };
    if (!fs.existsSync(intentDir)) return out;
    const it = mf.readJsonBounded(path.join(intentDir, `${ids.keyHash}.intent.json`));
    if (it) {
      if (mf.validateIntent(it.value).length || it.value.request_key_sha256 !== ids.keyHash) {
        throw new mf.ProducerError('INTENT_UNREADABLE');
      }
      out.intent = it.value;
      const rc = mf.readJsonBounded(path.join(intentDir, `${ids.keyHash}.receipt.json`));
      if (rc) {
        if (mf.validateReceipt(rc.value).length) throw new mf.ProducerError('RECEIPT_UNREADABLE');
        out.receipt = rc.value;
        out.receiptSha = mf.sha256Hex(rc.bytes);
      }
    }
    const nr = mf.readJsonBounded(path.join(intentDir, `${ids.nonceHash}.nonce.json`));
    if (nr) out.nonceRecord = nr.value;
    return out;
  }

  /** Doi soat intent khong co receipt: chi doc, KHONG chay lai. */
  function reconcileIntent(intent) {
    const runs = intent.ky_chieu.map((k) => {
      const row = { ky: k.ky, chieu: k.chieu, run_rel: k.run_rel, ton_tai: false, manifest: 'MISSING', manifest_sha256: null, trang_thai_run: null, loi: [] };
      let dir;
      try {
        dir = mf.resolveContained(roots.downloadRoot, k.segments);
      } catch (e) {
        row.loi = [e.code || 'PATH_INVALID'];
        return row;
      }
      if (!fs.existsSync(dir)) return row;
      row.ton_tai = true;
      const v = mf.verifyRunDir(dir, { context_digest: intent.context_digest });
      if (v.manifest_present) {
        row.manifest = v.ok ? 'VALID' : 'INVALID';
        row.manifest_sha256 = v.manifest_sha256;
        row.trang_thai_run = v.ok ? v.manifest.trang_thai : null;
      }
      row.loi = v.errors.map((e) => e.code).slice(0, 20);
      return row;
    });
    return {
      trang_thai: 'UNKNOWN',
      request_key_sha256: intent.request_key_sha256,
      context_digest: intent.context_digest,
      runs,
      co_the_doi_soat: runs.every((r) => r.manifest === 'VALID'),
      hanh_dong: 'KHONG_TU_CHAY_LAI',
    };
  }

  /**
   * FIX01: mot routine duy nhat cho ca startJob va reconcile. Intent phai khop context/identities da kiem;
   * receipt phai khop ca intent + context + plan + manifest/observation tren dia. Sai -> tu choi, khong start/sua.
   */
  function bindPrior(ctx, ids, prior) {
    if (prior.intent.context_digest !== ids.digest) throw new mf.ProducerError('REQUEST_KEY_CONFLICT');
    // FIX02: ke hoach day du duoc dung lai bang CHINH planRuns voi thoi diem lap ke hoach goc (intent.tao_luc),
    // khong dung dong ho hien tai -> intent+receipt bi cat cung nhau khong qua duoc.
    const expected = planRuns(ctx, intentPlanTime(prior.intent))
      .map((p) => ({ ky: p.ky, chieu: p.type, segments: p.segments.slice(), run_rel: p.run_rel }));
    const ie = mf.verifyIntentBinding(prior.intent, ctx, ids, expected);
    if (ie.length) throw new mf.ProducerError('INTENT_BINDING_MISMATCH', ie.slice(0, 20));
    if (prior.receipt) {
      const re = mf.verifyReceiptBinding({ receipt: prior.receipt, intent: prior.intent, ctx, ids, downloadRoot: roots.downloadRoot });
      if (re.length) throw new mf.ProducerError('RECEIPT_BINDING_MISMATCH', re.slice(0, 20));
    }
  }

  /** Tra cuu ket qua cu theo request key ma khong khoi chay. */
  function reconcile(rawContext) {
    const ctx = validated(rawContext);
    const ids = identities(ctx);
    const prior = readPrior(ctx, ids);
    if (!prior.intent) return { status: 'NOT_FOUND' };
    bindPrior(ctx, ids, prior);
    if (prior.receipt) return { status: 'REPLAY', receipt: prior.receipt, receipt_sha256: prior.receiptSha };
    return { status: 'UNKNOWN', reconciliation: reconcileIntent(prior.intent) };
  }

  /**
   * @param {object} rawContext  context v1 do M2 coordinator cap (xem manifest.validateContext).
   *   Khong nhan duong dan, credential, DOWNLOAD_DIR, PN/actor override.
   * @returns {{status:'STARTED'|'REPLAY'|'RUNNING'|'UNKNOWN', job_id, done:Promise, receipt?, reconciliation?}}
   */
  function startJob(rawContext) {
    const ctx = validated(rawContext); // sai context: tu choi truoc moi IO
    const ids = identities(ctx);
    // FIX02: MOT thoi diem lap ke hoach cho ca plan va tao_luc/bat_dau cua intent (cung moc lich).
    const plannedAt = clock.now();
    const plan = planRuns(ctx, plannedAt);
    if (!plan.length) throw new mf.ProducerError('PLAN_EMPTY');

    const prior = readPrior(ctx, ids);
    if (prior.intent) {
      bindPrior(ctx, ids, prior);
      if (prior.receipt) {
        return { status: 'REPLAY', job_id: null, receipt: prior.receipt, receipt_sha256: prior.receiptSha, done: Promise.resolve(prior.receipt) };
      }
      if (state.running && state.requestKeyHash === ids.keyHash) {
        return { status: 'RUNNING', job_id: state.id, done: state.done };
      }
      // Ket qua cu chua ro (mat ket noi/restart): khong blind start.
      return { status: 'UNKNOWN', job_id: null, reconciliation: reconcileIntent(prior.intent), done: Promise.resolve(null) };
    }
    if (prior.nonceRecord) throw new mf.ProducerError('NONCE_REUSED');
    if (state.running) throw new mf.ProducerError('JOB_BUSY');

    mf.assertRootDir(roots.browserProfileRoot);
    mf.assertRootDir(roots.profilesDir);
    const cred = checkCredential(loadCredential({ profilesDir: roots.profilesDir, context: ctx }));

    // ---- tu day moi co side effect: intent bat bien truoc trinh duyet/portal ----
    const intentDir = mf.ensureDirChain(roots.downloadRoot, [ctx.phap_nhan.ma, mf.INTENT_DIR]);
    const startedAt = new Date(plannedAt).toISOString();
    try {
      mf.writeExclusive(intentDir, `${ids.keyHash}.intent.json`, mf.stableBytes(mf.buildIntent({ ctx, ids, plan, createdAt: startedAt })));
    } catch (e) {
      throw new mf.ProducerError(e.code === 'FILE_EXISTS' ? 'REQUEST_IN_FLIGHT' : (e.code || 'INTENT_WRITE_FAILED'));
    }
    mf.writeExclusive(intentDir, `${ids.nonceHash}.nonce.json`, mf.stableBytes(mf.buildNonceRecord(ids)));
    const logName = `${ids.keyHash}.log`;
    mf.writeExclusive(intentDir, logName, Buffer.from(`=== RUN ${ctx.run.run_id} ===\n`, 'utf8'));

    const job = {
      ctx,
      ids,
      plan,
      intentDir,
      cred,
      secrets: new Set([cred.username, cred.password]),
      ignoredProfileKeys: cred.ignoredKeys,
      logPath: path.join(intentDir, logName),
      startedAt,
    };

    state.running = true;
    state.id = ctx.run.run_id;
    state.requestKeyHash = ids.keyHash;
    state.events = [];
    state.summary = null;
    state.done = runJob(job)
      .then((receipt) => {
        state.summary = receipt;
        emit(job, 'done', { trang_thai: receipt.trang_thai, so_run: receipt.runs.length });
        return receipt;
      })
      .catch((err) => {
        // Receipt khong ghi duoc -> lan sau doi soat UNKNOWN, khong tu chay lai.
        emit(job, 'error', { code: safeCode(err, 'INTERNAL') });
        emit(job, 'done', { trang_thai: 'UNKNOWN', so_run: 0 });
        return null;
      })
      .finally(() => {
        job.cred = null;
        job.secrets.clear();
        state.running = false;
        state.requestKeyHash = null;
      });
    return { status: 'STARTED', job_id: state.id, done: state.done };
  }

  async function runJob(job) {
    const { ctx } = job;
    const formats = ctx.request.formats;
    const opt = { wantXml: formats.includes('xml'), wantPdf: formats.includes('pdf'), wantExcel: formats.includes('excel') };
    const runs = [];

    log(job, `So ky/chieu can tai: ${job.plan.length} (${job.plan.map((p) => `${p.ky}/${TYPE_DIR[p.type]}`).join(', ')})`);

    // 1. Dat cho thu muc run doc quyen TRUOC khi mo trinh duyet; trung (cung giay) -> CONFLICT huu han.
    for (const p of job.plan) {
      try {
        const dir = mf.createDirExclusive(roots.downloadRoot, p.segments);
        mf.writeExclusive(dir, mf.RUN_FILES.STARTED, mf.stableBytes(mf.buildRunStarted({ ctx, ids: job.ids, plan: p, createdAt: iso() })));
        runs.push({ plan: p, dir, used: reservedNames(), result: null });
      } catch (e) {
        const code = e.code === 'RUN_DIR_CONFLICT' ? 'RUN_DIR_CONFLICT' : safeCode(e, 'RESERVE_FAILED');
        log(job, `!! Khong dat cho duoc thu muc run ${p.run_rel} (${code}). Dung, khong mo trinh duyet.`);
        for (const r of runs) {
          r.result = writeRunManifest(job, r, failedManifest(job, r, opt, [mf.errorObject('RUN_DIR_CONFLICT_SIBLING', 'RESERVE')], mf.unknownLoginFacts('LOGIN_NOT_STARTED')));
        }
        return finishReceipt(job, runs, 'CONFLICT', [mf.errorObject(code, 'RESERVE')], [p.run_rel]);
      }
    }

    // 2. Ho so trinh duyet rieng theo phap nhan (dan xuat tu goc cau hinh + ma PN da kiem).
    let session = null;
    try {
      const userDataDir = mf.ensureDirChain(roots.browserProfileRoot, [ctx.phap_nhan.ma]);
      // 3. Dang nhap: captcha go tay trong cua so trinh duyet; credential chi trong RAM cua job.
      session = await portal().launchAndLogin({
        username: job.cred.username,
        password: job.cred.password,
        userDataDir,
        onStatus: (m) => log(job, m),
        now: clock.now,
      });
    } catch (e) {
      const code = safeCode(e, 'LOGIN_FAILED');
      log(job, `!! Dang nhap khong thanh cong (${code}).`);
      for (const r of runs) {
        r.result = writeRunManifest(job, r, failedManifest(job, r, opt, [mf.errorObject(code, 'LOGIN')], mf.unknownLoginFacts('LOGIN_NOT_COMPLETED')));
      }
      return finishReceipt(job, runs, 'FAILED', [mf.errorObject(code, 'LOGIN')], []);
    } finally {
      job.cred = null;
    }
    if (session && typeof session.token === 'string' && session.token) job.secrets.add(session.token);
    const facts = mf.normalizeLoginFacts(session && session.loginFacts);

    let pdfRenderer = null;
    try {
      if (opt.wantPdf) {
        log(job, 'Khoi tao bo tao PDF...');
        try {
          pdfRenderer = await build().createPdfRenderer();
        } catch (e) {
          log(job, `!! Khong khoi tao duoc bo tao PDF (${safeCode(e, 'PDF_INIT_FAILED')}).`);
        }
      }
      let lastKy = null;
      let kyIndex = 0;
      const kyTotal = new Set(job.plan.map((p) => p.ky)).size;
      for (const r of runs) {
        if (r.plan.ky !== lastKy) {
          if (lastKy !== null) await clock.sleep(PAUSE_BETWEEN_MONTHS_MS);
          lastKy = r.plan.ky;
          kyIndex += 1;
          emit(job, 'month', { monthTag: r.plan.ky, index: kyIndex, total: kyTotal });
          log(job, `========== KY ${r.plan.ky} (${kyIndex}/${kyTotal}): ${r.plan.startDate} -> ${r.plan.endDate} ==========`);
        }
        try {
          r.result = await processRun(job, r, session, facts, opt, pdfRenderer);
        } catch (e) {
          log(job, `!! Loi khi xu ly ${TYPE_LABEL[r.plan.type]} ${r.plan.ky} (${safeCode(e, 'RUN_FAILED')}).`);
          r.result = writeRunManifest(job, r, failedManifest(job, r, opt, [mf.errorObject(safeCode(e, 'RUN_FAILED'), 'INTERNAL')], facts));
        }
      }
    } finally {
      if (pdfRenderer) await pdfRenderer.close().catch(() => {});
      // Chi dong context do chinh job nay mo.
      if (session && session.context) await session.context.close().catch(() => {});
    }

    const st = runs.map((r) => r.result.trang_thai);
    const overall = st.every((s) => s === 'COMPLETE') ? 'COMPLETE' : st.every((s) => s === 'FAILED') ? 'FAILED' : 'PARTIAL';
    log(job, 'HOAN TAT. Ban co the mo thu muc de kiem tra hoa don.');
    return finishReceipt(job, runs, overall, [], []);
  }

  async function processRun(job, r, session, facts, opt, pdfRenderer) {
    const p = r.plan;
    const type = p.type;
    const label = TYPE_LABEL[type];
    const startedAt = iso();
    emit(job, 'phase', { type, label, monthTag: p.ky });
    log(job, `===== ${label} (${p.ky}): dang lay danh sach hoa don =====`);

    let records = [];
    let nhom = [];
    const loiChung = [];
    let listFailed = false;
    try {
      const res = await portal().fetchAllInvoicesWithGroups(session.context, session.token, type, p.startDate, p.endDate, (m) => log(job, m));
      records = Array.isArray(res && res.records) ? res.records : [];
      nhom = (Array.isArray(res && res.nhom) ? res.nhom : []).map(normalizeGroup);
    } catch (e) {
      listFailed = true;
      loiChung.push(mf.errorObject(safeCode(e, 'LIST_FAILED'), 'LIST', e && e.http_status));
    }
    // FIX01: khong nhom nao xac minh duoc nguon -> FAILED (khong de 0 hoa don thanh COMPLETE/PARTIAL).
    if (!listFailed && !nhom.some((g) => g.trang_thai === 'OK')) {
      listFailed = true;
      loiChung.push(mf.errorObject('NO_SOURCE_GROUP_VERIFIED', 'LIST'));
    }
    log(job, `${label}: tong cong ${records.length} hoa don.`);

    const items = [];
    for (let i = 0; i < records.length; i++) {
      const rec = records[i];
      const item = baseItem(rec, i + 1); // anh chup gia tri tho TRUOC moi bo sung cho Excel
      emit(job, 'progress', { type, monthTag: p.ky, index: i + 1, total: records.length });
      if (opt.wantXml || opt.wantPdf) {
        await fetchXmlInto(job, r, session, rec, item, invoiceFileBase(rec, i + 1), opt, pdfRenderer);
      } else {
        item.xml_status = 'KHONG_YEU_CAU';
      }
      items.push(item);
      if ((i + 1) % 10 === 0) log(job, `  ...da xu ly ${i + 1}/${records.length} hoa don ${label}`);
    }

    let bangKe = null;
    let bangKeTrangThai = 'KHONG_YEU_CAU';
    if (opt.wantExcel) {
      if (listFailed) {
        bangKeTrangThai = 'LOI';
      } else {
        try {
          bangKe = await writeExcel(r, records, items, `${label} ${p.mm}-${p.year}`, `bang_ke_${type}_${p.ky}`);
          bangKeTrangThai = 'OK';
          log(job, `Da xuat bang ke Excel -> ${bangKe.file}`);
        } catch (e) {
          bangKeTrangThai = 'LOI';
          loiChung.push(mf.errorObject('EXCEL_WRITE_FAILED', 'EXCEL'));
          log(job, `Khong the ghi bang ke Excel (${safeCode(e, 'EXCEL_WRITE_FAILED')}).`);
        }
      }
    }

    const manifest = baseManifest(job, r, facts, startedAt);
    manifest.nhom = nhom;
    manifest.hoa_don = items;
    manifest.loi_chung = loiChung;
    manifest.tong = Object.assign(mf.computeTotals(items), { bang_ke: bangKe, bang_ke_trang_thai: bangKeTrangThai });
    manifest.ly_do_partial = mf.computePartialReasons(manifest);
    manifest.trang_thai = listFailed ? 'FAILED' : manifest.ly_do_partial.length ? 'PARTIAL' : 'COMPLETE';
    manifest.ket_thuc = iso();

    const t = manifest.tong;
    log(job,
      `===== ${label} ${p.ky} XONG: ${t.tong_hd} HD | XML ok ${t.xml_ok}` +
        ` | khong ma ${t.khong_xml_goc} | loi ${t.xml_loi} | PDF ok ${t.pdf_ok}/loi ${t.pdf_loi} | ${manifest.trang_thai} =====`);
    return writeRunManifest(job, r, manifest);
  }

  async function fetchXmlInto(job, r, session, rec, item, fileBase, opt, pdfRenderer) {
    let res;
    try {
      res = await portal().exportInvoiceXml(session.context, session.token, rec);
    } catch (_) {
      res = { ok: false, status: 0, kind: 'EXCEPTION' };
    }
    if (!res || !res.ok) {
      const cls = classifyExportFailure(rec, res || {});
      if (cls.xml_status === 'KHONG_XML_GOC') {
        item.xml_status = 'KHONG_XML_GOC';
        item.bang_chung = 'BANG_KE';
        item.can_cu = cls.can_cu;
        log(job, `  [${item.item_ordinal}] khong co XML goc tren cong (${cls.can_cu}) - da ghi vao bang ke`);
      } else {
        item.xml_status = 'LOI';
        item.loi = cls.loi;
        log(job, `  [${item.item_ordinal}] LOI tai XML (${cls.loi.code}${cls.loi.http_status ? ' HTTP ' + cls.loi.http_status : ''})`);
      }
      return;
    }

    const buf = Buffer.isBuffer(res.buffer) ? res.buffer : Buffer.from(res.buffer || []);
    const kind = sniffPayload(buf);
    let primaryXml = null;
    if (kind === 'ZIP') primaryXml = storeZip(r, item, fileBase, buf);
    else if (kind === 'XML') primaryXml = storeXml(r, item, fileBase, buf);
    else storeUnknown(r, item, fileBase, buf);
    if (item.xml_status === 'LOI') {
      log(job, `  [${item.item_ordinal}] LOI noi dung tai ve (${item.loi.code})`);
    }

    // Bo sung ten nguoi mua cho BANG KE nhu ban cu (chi Excel; manifest giu gia tri tho da chup).
    if (primaryXml && opt.wantExcel) {
      try {
        const info = build().parseInvoiceXml(primaryXml.toString('utf8'));
        if (info && info.buyer) {
          if (info.buyer.ten && !String(rec.nmten || '').trim()) rec.nmten = info.buyer.ten;
          if (info.buyer.cccd && !String(rec.nmmst || '').trim()) rec.nmcccd = info.buyer.cccd;
        }
      } catch (_) {}
    }

    // PDF chi de xem lai, khong phai bang chung nguon.
    if (opt.wantPdf) {
      if (primaryXml && pdfRenderer) {
        try {
          const pdf = await pdfRenderer.render(primaryXml.toString('utf8'));
          const f = writeNewFile(r, item.xml_tep[0].file.replace(/\.xml$/i, ''), '.pdf', Buffer.from(pdf));
          item.file_pdf = f.file;
          item.hash_pdf = f.sha256;
          item.vai_tro_pdf = 'XEM_LAI';
        } catch (e) {
          item.pdf_loi = true;
          log(job, `  [${item.item_ordinal}] LOI tao PDF (${safeCode(e, 'PDF_FAILED')})`);
        }
      } else {
        item.pdf_loi = true;
      }
    }
  }

  function storeXml(r, item, fileBase, buf) {
    if (buf.length > mf.LIMITS.XML_BYTES) {
      item.xml_status = 'LOI';
      item.loi = mf.errorObject('XML_TOO_LARGE', 'XML');
      item.payload = { file: null, sha256: mf.sha256Hex(buf), bytes: buf.length, loai: 'XML' };
      return null;
    }
    const f = writeNewFile(r, fileBase, '.xml', buf);
    setXmlOk(item, [{ file: f.file, sha256: f.sha256, bytes: f.bytes, ordinal_zip: null, ten_entry_zip: null }]);
    return buf;
  }

  function storeZip(r, item, fileBase, buf) {
    // Giu raw archive bytes (trong gioi han) truoc khi doc entry; ZIP hong khong thanh empty-success.
    let zipFile = null;
    if (buf.length <= mf.LIMITS.ZIP_BYTES) zipFile = writeNewFile(r, fileBase, '.zip', buf).file;
    const inv = inspectZip(AdmZip(), buf);
    const okEntries = inv.entries.filter((e) => e.read_state === 'READ_OK');
    const multi = okEntries.length > 1;
    const tep = [];
    for (const e of okEntries) {
      // Ten XML giu ordinal vat ly cua entry trong ZIP (khong danh lai so).
      const f = writeNewFile(r, multi ? `${fileBase}_${e.ordinal}` : fileBase, '.xml', e.data);
      e.file = f.file;
      tep.push({ file: f.file, sha256: e.sha256, bytes: e.bytes, ordinal_zip: e.ordinal, ten_entry_zip: e.name });
    }
    item.zip = {
      file: zipFile,
      sha256: mf.sha256Hex(buf),
      bytes: buf.length,
      coverage: inv.coverage,
      entries: inv.entries.map((e) => ({
        ordinal: e.ordinal,
        name: e.name,
        declared_bytes: e.declared_bytes,
        read_state: e.read_state,
        bytes: e.bytes,
        sha256: e.sha256,
        loi: e.loi,
        trung_ten: e.trung_ten,
        file: e.file,
      })),
      loi: inv.loi,
    };
    if (tep.length) {
      setXmlOk(item, tep);
      return okEntries[0].data;
    }
    item.xml_status = 'LOI';
    item.loi = inv.loi ? Object.assign({}, inv.loi) : mf.errorObject('ZIP_NO_READABLE_XML', 'ZIP');
    return null;
  }

  function storeUnknown(r, item, fileBase, buf) {
    const f = writeNewFile(r, fileBase, '.bin', buf);
    item.xml_status = 'LOI';
    item.loi = mf.errorObject('PAYLOAD_UNRECOGNIZED', 'EXPORT_XML');
    item.payload = { file: f.file, sha256: f.sha256, bytes: f.bytes, loai: 'UNKNOWN' };
  }

  async function writeExcel(r, records, items, sheetTitle, baseName) {
    const rows = records.map((rec, i) => Object.assign({}, rec, {
      scope: items[i].scope,
      ttxly: items[i].ttxly,
      xml_status: items[i].xml_status,
      file_xml: items[i].xml_tep.map((t) => t.file).join('; '),
      hash_xml: items[i].xml_tep.map((t) => t.sha256).join('; '),
    }));
    const name = freeName(r, baseName, '.xlsx');
    const outPath = path.join(r.dir, name);
    await build().buildExcel(rows, sheetTitle, outPath);
    const bytes = mf.readBounded(outPath, mf.LIMITS.ZIP_BYTES);
    if (!bytes || !bytes.length) throw new mf.ProducerError('EXCEL_NOT_WRITTEN');
    return { file: name, sha256: mf.sha256Hex(bytes), bytes: bytes.length, so_cot: cfg.EXCEL_COLUMNS.length };
  }

  function baseManifest(job, r, facts, startedAt) {
    const { ctx } = job;
    return {
      schema: mf.SCHEMA.MANIFEST,
      nguon: 'TAI_MOI',
      run_id: ctx.run.run_id,
      phap_nhan: { uuid: ctx.phap_nhan.uuid, ma: ctx.phap_nhan.ma },
      ky: r.plan.ky,
      chieu: r.plan.type,
      thu_muc_chieu: TYPE_DIR[r.plan.type],
      bat_dau: startedAt,
      ket_thuc: startedAt,
      phien_ban_bo_tai: PRODUCER_VERSION,
      nguoi_bam: ctx.actor.id,
      context: mf.buildContextBlock(ctx, job.ids, job.ignoredProfileKeys),
      dang_nhap: facts,
      nhom: [],
      tong: null,
      hoa_don: [],
      loi_chung: [],
      trang_thai: null,
      ly_do_partial: [],
      gioi_han: { xml_bytes: mf.LIMITS.XML_BYTES, zip_bytes: mf.LIMITS.ZIP_BYTES, zip_entries: mf.LIMITS.ZIP_ENTRIES },
    };
  }

  function failedManifest(job, r, opt, errors, facts) {
    const now = iso();
    const m = baseManifest(job, r, facts, now);
    m.loi_chung = errors;
    m.tong = Object.assign(mf.computeTotals([]), { bang_ke: null, bang_ke_trang_thai: opt.wantExcel ? 'LOI' : 'KHONG_YEU_CAU' });
    m.ly_do_partial = mf.computePartialReasons(m);
    m.trang_thai = 'FAILED';
    m.ket_thuc = iso();
    return m;
  }

  function writeRunManifest(job, r, manifest) {
    const errs = mf.validateManifest(manifest);
    if (errs.length) {
      log(job, `!! Manifest tu kiem khong dat (${errs.slice(0, 5).map((e) => e.code).join(',')}); khong ghi.`);
      return { trang_thai: 'MANIFEST_INVALID', manifest_sha256: null, observations_sha256: null, loi: errs.slice(0, 20).map((e) => e.code) };
    }
    try {
      emit(job, 'phase', { type: r.plan.type, label: 'Dang ghi manifest', monthTag: r.plan.ky });
      const w = mf.writeExclusive(r.dir, mf.RUN_FILES.MANIFEST, mf.stableBytes(manifest));
      const ow = mf.writeExclusive(r.dir, mf.RUN_FILES.OBSERVATIONS, mf.stableBytes(mf.buildObservations(manifest, w.sha256)));
      emit(job, 'manifest', { run_rel: r.plan.run_rel, trang_thai: manifest.trang_thai, manifest_sha256: w.sha256 });
      return { trang_thai: manifest.trang_thai, manifest_sha256: w.sha256, observations_sha256: ow.sha256, loi: [] };
    } catch (e) {
      log(job, `!! Khong ghi duoc manifest (${safeCode(e, 'MANIFEST_WRITE_FAILED')}).`);
      return { trang_thai: 'MANIFEST_WRITE_FAILED', manifest_sha256: null, observations_sha256: null, loi: [safeCode(e, 'MANIFEST_WRITE_FAILED')] };
    }
  }

  function finishReceipt(job, runs, trangThai, loiChung, xungDot) {
    const receipt = mf.buildReceipt({
      ctx: job.ctx,
      ids: job.ids,
      runs: runs.map((r) => ({
        ky: r.plan.ky,
        chieu: r.plan.type,
        run_rel: r.plan.run_rel,
        trang_thai: r.result.trang_thai,
        manifest_sha256: r.result.manifest_sha256,
        observations_sha256: r.result.observations_sha256,
        loi: r.result.loi,
      })),
      trangThai,
      loiChung,
      xungDot,
      batDau: job.startedAt,
      ketThuc: iso(),
      version: PRODUCER_VERSION,
    });
    mf.writeExclusive(job.intentDir, `${job.ids.keyHash}.receipt.json`, mf.stableBytes(receipt));
    return receipt;
  }

  function writeNewFile(r, base, ext, bytes) {
    for (let n = 1; n <= MAX_NAME_SUFFIX; n++) {
      const name = n === 1 ? `${base}${ext}` : `${base}~${n}${ext}`;
      const lk = name.toLowerCase();
      if (r.used.has(lk)) continue;
      try {
        const w = mf.writeExclusive(r.dir, name, bytes);
        r.used.add(lk);
        return w;
      } catch (e) {
        if (e.code === 'FILE_EXISTS') {
          r.used.add(lk);
          continue;
        }
        throw e;
      }
    }
    throw new mf.ProducerError('FILENAME_COLLISION_EXHAUSTED');
  }

  function freeName(r, base, ext) {
    for (let n = 1; n <= MAX_NAME_SUFFIX; n++) {
      const name = n === 1 ? `${base}${ext}` : `${base}~${n}${ext}`;
      const lk = name.toLowerCase();
      if (r.used.has(lk) || fs.existsSync(path.join(r.dir, name))) continue;
      mf.assertSegment(name);
      r.used.add(lk);
      return name;
    }
    throw new mf.ProducerError('FILENAME_COLLISION_EXHAUSTED');
  }

  return { startJob, getState, reconcile, roots };
}

/* ---------------- helper ---------------- */

/** Xay dung danh sach cac ky can tai. mode='year' -> ca 12 thang (nam hien tai chi den thang hien tai). */
function buildMonths(mode, year, month, nowMs) {
  if (mode === 'year') {
    const now = new Date(nowMs);
    const maxM = year === now.getFullYear() ? now.getMonth() + 1 : 12;
    const arr = [];
    for (let m = 1; m <= maxM; m++) arr.push({ year, month: m });
    return arr;
  }
  return [{ year, month }];
}

function planRuns(ctx, nowMs) {
  const out = [];
  for (const { year: y, month: m } of buildMonths(ctx.request.mode, ctx.request.year, ctx.request.month, nowMs)) {
    const mm = String(m).padStart(2, '0');
    const lastDay = new Date(y, m, 0).getDate();
    const ky = `${y}-${mm}`;
    for (const type of ctx.request.types) {
      const segments = [ctx.phap_nhan.ma, ky, TYPE_DIR[type], ctx.run.run_id];
      out.push({
        year: y,
        month: m,
        mm,
        ky,
        type,
        startDate: `01/${mm}/${y}`,
        endDate: `${String(lastDay).padStart(2, '0')}/${mm}/${y}`,
        segments,
        run_rel: segments.join('/'),
      });
    }
  }
  return out;
}

/**
 * FIX02: thoi diem lap ke hoach goc tu intent.tao_luc. Chi nhan ISO UTC chuan (dang toISOString) va huu han;
 * thieu/sai/khong chuan -> tu choi, KHONG doan bang dong ho hien tai.
 */
function intentPlanTime(intent) {
  const s = intent && intent.tao_luc;
  if (typeof s !== 'string' || !mf.RE.iso.test(s)) throw new mf.ProducerError('INTENT_TIME_INVALID');
  const t = Date.parse(s);
  if (!Number.isFinite(t) || new Date(t).toISOString() !== s) throw new mf.ProducerError('INTENT_TIME_INVALID');
  return t;
}

function reservedNames() {
  return new Set(Object.values(mf.RUN_FILES).map((n) => n.toLowerCase()));
}

function safeCode(e, fallback) {
  return e && typeof e.code === 'string' && mf.RE.code.test(e.code) ? e.code : fallback;
}

function rawValue(v) {
  if (v === undefined || v === null) return null;
  if (typeof v === 'string' || typeof v === 'boolean') return v;
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  return null;
}

/** Observation tho: giu nguyen kieu/gia tri cong tra, thieu = null; khong so hoa, khong suy VND/tthai. */
function baseItem(rec, ordinal) {
  const keyRaw = {};
  for (const k of mf.KEY_PARTS) keyRaw[k] = rawValue(rec[k]);
  return {
    item_ordinal: ordinal,
    key_raw: keyRaw,
    key_canonical: mf.canonicalKeyOf(keyRaw), // = [nbmst,khmshdon,khhdon,shdon].join('|') cua portal voi gia tri tho
    key_thieu: mf.missingKeyParts(keyRaw),
    scope: rec._scope === 'sco-query' ? 'sco-query' : 'query',
    ttxly: rawValue(rec._ttxly),
    nhom_thu_tu: Number.isInteger(rec._group_ordinal) ? rec._group_ordinal : null,
    tthai_cong: rawValue(rec.tthai),
    tdlap: rawValue(rec.tdlap),
    dvtte_cong: rawValue(rec.dvtte),
    xml_status: null,
    bang_chung: null,
    can_cu: null,
    file_xml: null,
    hash_xml: null,
    xml_bytes: null,
    ordinal_zip: null,
    ten_entry_zip: null,
    xml_tep: [],
    zip: null,
    payload: null,
    file_pdf: null,
    hash_pdf: null,
    vai_tro_pdf: null,
    pdf_loi: false,
    loi: null,
  };
}

function setXmlOk(item, tep) {
  item.xml_status = 'OK';
  item.bang_chung = 'XML';
  item.xml_tep = tep;
  item.file_xml = tep[0].file;
  item.hash_xml = tep[0].sha256;
  item.xml_bytes = tep[0].bytes;
  item.ordinal_zip = tep[0].ordinal_zip;
  item.ten_entry_zip = tep[0].ten_entry_zip;
}

function normalizeGroup(g, i) {
  const ok = g && g.trang_thai === 'OK';
  return {
    thu_tu: i + 1,
    path: g && typeof g.path === 'string' ? g.path : '/api/unknown',
    scope: g && g.scope === 'sco-query' ? 'sco-query' : 'query',
    ttxly: rawValue(g && g.ttxly),
    trang_thai: ok ? 'OK' : 'LOI',
    so_ban_ghi: ok ? g.so_ban_ghi : null,
    so_moi: ok ? g.so_moi : null,
    loi: ok ? null : mf.errorObject(g && g.loi && g.loi.code, 'LIST', g && g.loi && g.loi.http_status),
  };
}

/**
 * Phan loai tai XML that bai. KHONG_XML_GOC (bang chung BANG_KE) chi khi co can cu tuong minh:
 * nhom nguon ttxly=6 voi phan hoi khong tam thoi, hoac phan hoi JSON noi ro "khong ton tai ho so goc"
 * voi ma 4xx/rong. 0/429/5xx/401/403 luon la LOI. Khong dung mot regex text don le de gan nhan.
 */
function classifyExportFailure(rec, res) {
  const s = Number.isInteger(res.status) ? res.status : 0;
  const transient = s === 0 || s === 429 || s >= 500 || s === 401 || s === 403;
  const emptyBody = res.kind === 'EMPTY_BODY';
  const groupKhongMa = rec._ttxly === 6 || rec._ttxly === '6';
  // FIX01: 400/404 chung chung la loi API (TL43). 4xx chi la KHONG_XML_GOC khi portal da xac nhan body JSON
  // neu ro "khong co ho so goc"; rieng nhom ttxly=6 + 200 rong giu can cu nhom nguon da duoc Root chot.
  const explicitNoOrigin = res.noOriginalBody === true && res.bodyIsJson === true;
  if (!transient && groupKhongMa && emptyBody && s >= 200 && s < 300) {
    return { xml_status: 'KHONG_XML_GOC', can_cu: 'NHOM_TTXLY_6+EMPTY_BODY' };
  }
  if (!transient && explicitNoOrigin && (emptyBody || (s >= 400 && s < 500))) {
    const tail = emptyBody ? 'EMPTY_BODY' : 'HTTP_' + s;
    return { xml_status: 'KHONG_XML_GOC', can_cu: `${groupKhongMa ? 'NHOM_TTXLY_6' : 'RESPONSE_NO_ORIGIN'}+${tail}` };
  }
  const code = emptyBody ? 'EMPTY_BODY' : res.kind === 'EXCEPTION' || s === 0 ? 'TRANSPORT' : 'HTTP_STATUS';
  return { xml_status: 'LOI', loi: mf.errorObject(code, 'EXPORT_XML', s || null) };
}

function sniffPayload(buf) {
  if (buf.length >= 4 && buf[0] === 0x50 && buf[1] === 0x4b && ((buf[2] === 3 && buf[3] === 4) || (buf[2] === 5 && buf[3] === 6))) {
    return 'ZIP';
  }
  return looksLikeXml(buf) ? 'XML' : 'UNKNOWN';
}

/**
 * Kiem ke ZIP bang adm-zip san co: du entry vat ly theo thu tu central directory (ordinal 1-based),
 * ke ca non-XML/trung ten/entry loi. Gioi han: ZIP 64MiB, 1000 entry, XML 16MiB (kiem kich thuoc khai
 * bao truoc khi inflate). Vuot gioi han / hong -> PARTIAL + loi, khong bao gio thanh empty-success.
 */
function inspectZip(AdmZip, buf) {
  const out = { coverage: 'COMPLETE', entries: [], loi: null };
  if (buf.length > mf.LIMITS.ZIP_BYTES) {
    out.coverage = 'PARTIAL';
    out.loi = mf.errorObject('ZIP_TOO_LARGE', 'ZIP');
    return out;
  }
  let list;
  try {
    list = new AdmZip(buf).getEntries();
  } catch (_) {
    out.coverage = 'PARTIAL';
    out.loi = mf.errorObject('ZIP_MALFORMED', 'ZIP');
    return out;
  }
  if (!Array.isArray(list)) {
    out.coverage = 'PARTIAL';
    out.loi = mf.errorObject('ZIP_MALFORMED', 'ZIP');
    return out;
  }
  if (list.length > mf.LIMITS.ZIP_ENTRIES) {
    out.coverage = 'PARTIAL';
    out.loi = mf.errorObject('ZIP_TOO_MANY_ENTRIES', 'ZIP');
    return out;
  }
  const count = new Map();
  for (const e of list) count.set(e.entryName, (count.get(e.entryName) || 0) + 1);
  list.forEach((e, idx) => {
    const declared = e.header && Number.isInteger(e.header.size) ? e.header.size : null;
    const row = {
      ordinal: idx + 1,
      name: String(e.entryName),
      declared_bytes: declared,
      read_state: null,
      bytes: null,
      sha256: null,
      loi: null,
      trung_ten: count.get(e.entryName) > 1,
      file: null,
      data: null,
    };
    const fail = (code) => {
      row.read_state = 'READ_ERROR';
      row.loi = mf.errorObject(code, 'ZIP');
    };
    if (e.isDirectory) row.read_state = 'DIRECTORY';
    else if (!/\.xml$/i.test(row.name)) row.read_state = 'IGNORED_NON_XML';
    else if (declared === null) fail('ZIP_MEMBER_SIZE_UNKNOWN');
    else if (declared > mf.LIMITS.XML_BYTES) fail('ZIP_MEMBER_TOO_LARGE');
    else {
      let data = null;
      try {
        data = e.getData();
      } catch (_) {
        data = null;
      }
      if (!Buffer.isBuffer(data)) fail('ZIP_MEMBER_READ_ERROR');
      else if (data.length > mf.LIMITS.XML_BYTES) fail('ZIP_MEMBER_TOO_LARGE');
      else if (data.length !== declared) fail('ZIP_MEMBER_SIZE_MISMATCH');
      else if (!data.length) fail('ZIP_MEMBER_EMPTY');
      else if (!looksLikeXml(data)) fail('ZIP_MEMBER_NOT_XML');
      else {
        row.read_state = 'READ_OK';
        row.bytes = data.length;
        row.sha256 = mf.sha256Hex(data);
        row.data = data;
      }
    }
    out.entries.push(row);
  });
  if (out.entries.some((e) => e.read_state === 'READ_ERROR')) out.coverage = 'PARTIAL';
  return out;
}

function looksLikeXml(buffer) {
  const head = buffer.slice(0, 64).toString('utf8').trimStart();
  return head.startsWith('<?xml') || head.startsWith('<');
}

/** Ten file XML: <mau><ky hieu>-<so>__<MST ban>; chi ASCII an toan; trung ten xu ly bang ~n khi ghi. */
function invoiceFileBase(rec, ordinal) {
  let base = `hoadon_${ordinal}`;
  if (rec.khhdon && rec.shdon) base = `${rec.khmshdon || ''}${rec.khhdon}-${rec.shdon}`;
  const mst = rec.nbmst !== undefined && rec.nbmst !== null ? sanitize(rec.nbmst) : '';
  return `${sanitize(base) || `hoadon_${ordinal}`}__${mst || 'KHONG_MST'}`;
}
function sanitize(s) {
  return String(s).replace(/[^A-Za-z0-9_-]+/g, '_').replace(/^-+/, '').slice(0, 60);
}

/* ---------------- credential theo profile (chi RAM) ---------------- */

/**
 * Doc profiles\<ref>.env. Profile phai TU KHAI BAO MA_PHAP_NHAN + PHAP_NHAN_UUID + PROFILE_REVISION
 * khop context (khong suy mapping tu TAX_USERNAME/ten thu muc). DOWNLOAD_DIR bi bo qua.
 * Loi chi mang ma, khong mang gia tri.
 */
function loadProfileCredential({ profilesDir, context }) {
  mf.assertRootDir(profilesDir);
  const file = mf.resolveContained(profilesDir, [`${context.profile.ref}.env`]);
  const bytes = mf.readBounded(file, mf.LIMITS.PROFILE_BYTES);
  if (!bytes) throw new mf.ProducerError('PROFILE_NOT_FOUND');
  const kv = parseEnvText(bytes.toString('utf8'));
  if (kv.MA_PHAP_NHAN !== context.phap_nhan.ma || kv.PHAP_NHAN_UUID !== context.phap_nhan.uuid) {
    throw new mf.ProducerError('PROFILE_BINDING_MISMATCH');
  }
  if (kv.PROFILE_REVISION !== context.profile.revision) throw new mf.ProducerError('PROFILE_REVISION_MISMATCH');
  return {
    username: kv.TAX_USERNAME || '',
    password: kv.TAX_PASSWORD || '',
    ignoredKeys: Object.prototype.hasOwnProperty.call(kv, 'DOWNLOAD_DIR') ? ['DOWNLOAD_DIR'] : [],
  };
}

function parseEnvText(text) {
  const out = Object.create(null);
  for (const raw of text.replace(/^﻿/, '').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq <= 0) continue;
    const k = line.slice(0, eq).trim();
    let v = line.slice(eq + 1).trim();
    if (v.length >= 2 && ((v[0] === '"' && v.endsWith('"')) || (v[0] === "'" && v.endsWith("'")))) v = v.slice(1, -1);
    out[k] = v;
  }
  return out;
}

function checkCredential(c) {
  if (!c || typeof c.username !== 'string' || !c.username || typeof c.password !== 'string' || !c.password) {
    throw new mf.ProducerError('PROFILE_CREDENTIAL_MISSING');
  }
  const ignored = Array.isArray(c.ignoredKeys) ? c.ignoredKeys.filter((k) => k === 'DOWNLOAD_DIR') : [];
  return { username: c.username, password: c.password, ignoredKeys: ignored };
}

/* ---------------- API mac dinh (giu ten cu) ---------------- */

let defaultProducer = null;
function producer() {
  return defaultProducer || (defaultProducer = createProducer());
}

module.exports = {
  createProducer,
  // startJob nay doi hop dong: chi nhan context v1 tu M2 coordinator; goi kieu cu {mode,...,env} bi tu choi.
  startJob: (ctx) => producer().startJob(ctx),
  getState: () => producer().getState(),
  reconcile: (ctx) => producer().reconcile(ctx),
  PRODUCER_VERSION,
  _internal: { inspectZip, classifyExportFailure, invoiceFileBase, sniffPayload, planRuns, parseEnvText },
};
