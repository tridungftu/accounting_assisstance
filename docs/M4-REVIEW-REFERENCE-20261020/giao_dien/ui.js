export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const money = value => new Intl.NumberFormat('vi-VN', {maximumFractionDigits:0}).format(Number(value) || 0);
const paths = {
 calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18M7 15h.01M12 15h.01M17 15h.01"/>',
 'arrow-left':'<path d="M20 12H4m6-6-6 6 6 6"/>',
 grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
 file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
 scan:'<path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4M3 12h18M8 8h8M8 16h8"/>',
 layers:'<path d="m12 3 10 5-10 5L2 8zM2 12l10 5 10-5M2 16l10 5 10-5"/>',
 table:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18M9 4v16M15 4v16"/>',
 check:'<path d="m5 12 4 4L19 6"/>',
 shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
 folder:'<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
 settings:'<path d="m9 3-.5 3-2 1-2.8-1-2 3 2.2 2v2L2 15l2 3 2.5-1 2 1L9 21h6l.5-3 2-1 2.5 1 2-3-2-2v-2l2-2-2-3-2.5 1-2-1L15 3z"/><circle cx="12" cy="12" r="3"/>',
 search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
 chevron:'<path d="m9 5 7 7-7 7"/>',
 down:'<path d="m6 9 6 6 6-6"/>',
 arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
 upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 16v4h16v-4"/>',
 download:'<path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 activity:'<path d="M3 12h4l3-8 4 16 3-8h4"/>',
 alert:'<path d="m12 3 10 18H2zM12 9v5M12 17h.01"/>',
 x:'<path d="m6 6 12 12M6 18 18 6"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 stop:'<rect x="6" y="6" width="12" height="12" rx="1"/>',
 play:'<path d="m7 4 14 8-14 8z"/>',
 external:'<path d="M14 3h7v7M21 3l-9 9M10 3H3v18h18v-7"/>',
 eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
 edit:'<path d="m16 3 5 5-13 13H3v-5zM13 6l5 5"/>',
 database:'<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 4 18 4 18 0V5M3 12c0 4 18 4 18 0"/>',
 refresh:'<path d="M20 8a8 8 0 1 0 1 7M20 3v5h-5"/>',
 server:'<rect x="3" y="3" width="18" height="7" rx="2"/><rect x="3" y="14" width="18" height="7" rx="2"/><path d="M7 6.5h.01M7 17.5h.01M11 6.5h6M11 17.5h6"/>',
 lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
 link:'<path d="m10 14 4-4M8 16l-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0M16 8l2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0"/>',
 filter:'<path d="M3 4h18l-7 8v7l-4 2v-9z"/>',
 bell:'<path d="M6 9a6 6 0 0 1 12 0v7l2 2H4l2-2zM10 21h4"/>',
 building:'<path d="M4 21V3h12v18M16 9h4v12M2 21h20M8 7h4M8 11h4M8 15h4M8 21v-2h4v2"/>',
 cloud:'<path d="M6 19a5 5 0 0 1-1-10 7 7 0 0 1 13-1 5.5 5.5 0 0 1 0 11z"/>',
 copy:'<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
 help:'<circle cx="12" cy="12" r="9"/><path d="M9 8a3 3 0 0 1 6 1c0 2-3 2-3 4M12 17h.01"/>',
 briefcase:'<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V3h8v4M3 12h18M10 12v3h4v-3"/>',
 menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
 trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
 sort:'<path d="M8 4v16m-4-4 4 4 4-4M16 20V4m-4 4 4-4 4 4"/>'
};
const aliases = {'layout-dashboard':'grid','file-text':'file','scan-text':'scan','circle-check':'check','check-circle':'check','chevron-right':'chevron','chevron-down':'down','arrow-right':'arrow','triangle-alert':'alert','alert-triangle':'alert','circle-alert':'alert','circle-x':'x','x-circle':'x','upload-cloud':'upload','cloud-upload':'upload','file-check':'shield','settings-2':'settings','list':'table','list-checks':'table','hard-drive':'database','history':'clock','loader':'refresh','loader-circle':'refresh','refresh-cw':'refresh','square':'stop','square-pen':'edit','pencil':'edit','circle-play':'play','file-spreadsheet':'table','file-search':'scan','file-up':'upload','network':'server','circle-help':'help','ban':'x','check-check':'check','arrow-down-to-line':'download','arrow-up-from-line':'upload','database-backup':'database','building-2':'building','chevrons-up-down':'sort','arrow-left':'arrow','log-out':'external'};
export function icon(name, size=18) {return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths[aliases[name]]||paths.file}</svg>`;}
export function badge(label, kind='neutral') {const map={'ok':'success','green':'success','yellow':'warning','red':'danger','blue':'info','gray':'neutral','blocked':'danger','pass':'success','high':'danger','medium':'warning','low':'info'}; kind=map[kind]||kind; return `<span class="badge badge-${escapeHTML(kind)}"><span class="status-mark" aria-hidden="true">${kind==='success'?'✓':kind==='warning'?'!':kind==='danger'?'!':kind==='info'?'•':'–'}</span>${escapeHTML(label)}</span>`;}
export function header(title, subtitle, actions='') {return `<div class="page-head"><div><h1 class="page-title">${title}</h1><p class="page-subtitle">${subtitle}</p></div><div class="page-actions">${actions}</div></div>`;}
export function upload(id, accept, multiple=false, subtitle='') {return `<div class="upload-zone" data-drop="${escapeHTML(id)}"><div class="upload-symbol">${icon('upload',24)}</div><strong>Kéo thả ${multiple?'các file':'file'} vào đây</strong><span class="muted small">${subtitle || accept.split(',').join(' · ')}</span><div class="upload-actions"><label class="btn" for="${id}">${icon('folder')} Chọn file</label>${multiple?`<label class="btn btn-ghost" for="${id}-folder">Chọn thư mục</label><input id="${id}-folder" class="file-input" type="file" webkitdirectory multiple accept="${accept}" data-folder-for="${id}">`:''}</div><input id="${id}" class="file-input" type="file" accept="${accept}" ${multiple?'multiple':''}><span class="upload-selection" data-selection="${id}" aria-live="polite"></span></div>`;}
