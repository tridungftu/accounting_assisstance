'use strict';

/*
 * Cau hinh tap trung cac endpoint / ten truong cua cong thue.
 * Neu cong Tong cuc Thue thay doi API, chi can sua o DAY (khong can dong vao code chinh).
 * Cac gia tri duoi day dua tren cau truc API cong khai da on dinh nhieu nam cua
 * https://hoadondientu.gdt.gov.vn (dung boi nhieu cong cu cong dong).
 */

module.exports = {
  BASE_URL: 'https://hoadondientu.gdt.gov.vn',

  // Trang dang nhap (SPA). Sau khi dang nhap, token JWT duoc luu trong localStorage.
  LOGIN_URL: 'https://hoadondientu.gdt.gov.vn/',

  // He thong hoadondientu (ban Next.js moi) dung tien to /api.
  // Moi loai hoa don co NHIEU nhom theo o "Ket qua kiem tra" (= ma ttxly),
  // va co the nam o 2 he:
  //   - query     : hoa don dien tu thong thuong (co ma / khong ma)
  //   - sco-query : hoa don khoi tao tu MAY TINH TIEN
  // App lay TAT CA cac nhom roi gop lai (loai trung) de khong sot hoa don.
  // (Muon bot nhom nao thi xoa dong tuong ung.)
  QUERY_GROUPS: {
    purchase: [
      { path: '/api/query/invoices/purchase', ttxly: 5 },     // Co ma (Cuc Thue da cap ma)
      { path: '/api/query/invoices/purchase', ttxly: 6 },     // Khong ma (Cuc Thue da nhan)
      { path: '/api/sco-query/invoices/purchase', ttxly: 8 }, // MAY TINH TIEN (he sco-query)
    ],
    sold: [
      { path: '/api/query/invoices/sold', ttxly: 5 },     // Co ma
      { path: '/api/query/invoices/sold', ttxly: 6 },     // Khong ma
      { path: '/api/sco-query/invoices/sold', ttxly: 8 }, // MAY TINH TIEN (he sco-query)
    ],
  },

  // Duong dan tai XML goc theo he (scope) cua hoa don
  EXPORT_XML: {
    query: '/api/query/invoices/export-xml',
    'sco-query': '/api/sco-query/invoices/export-xml',
  },

  // Tham so sap xep, so ban ghi moi trang, va dinh dang thoi gian
  SORT: 'tdlap:desc',
  PAGE_SIZE: 50,
  SEARCH_TIME_SUFFIX: true,

  // Chong bi cong thue chan (HTTP 429/403 - goi qua nhanh):
  THROTTLE_MS: 1000, // nghi 1 giay giua cac lan tai XML
  RETRY_429: 5, // so lan thu lai khi bi 429
  RETRY_DELAY_MS: 3000, // thoi gian cho co ban khi thu lai, tang dan theo lan

  // Thoi gian toi da cho ban dang nhap + nhap captcha (ms)
  LOGIN_TIMEOUT_MS: 8 * 60 * 1000,

  // Cac key co the chua token JWT trong localStorage (thu lan luot)
  TOKEN_STORAGE_KEYS: ['token', 'authToken', 'access_token', 'jwt'],

  // Cac tham so can lay tu moi ban ghi hoa don de goi export-xml.
  // (ten truong theo JSON tra ve cua cong thue)
  EXPORT_XML_PARAMS: ['nbmst', 'khhdon', 'khmshdon', 'shdon', 'tdlap'],

  // M2-00A: profile theo phap nhan va cac goc tai/ho so trinh duyet (tuong doi thu muc bo tai).
  // Goc tai KHONG con lay tu DOWNLOAD_DIR trong .env profile; run dir dan xuat tu goc + ma phap nhan da kiem.
  PROFILES_DIR: 'profiles',
  DOWNLOAD_ROOT_DIR: 'Download hoa don',
  BROWSER_PROFILE_ROOT_DIR: '.browser-profile',

  // Anh xa cot cho BANG KE EXCEL: [tenTruongJSON, tieuDeCot]
  // 15 cot dau giu nguyen thu tu (M8 doc); 5 cot cuoi them cho M2-00A.
  EXCEL_COLUMNS: [
    ['_stt', 'STT'],
    ['khmshdon', 'Ky hieu mau so'],
    ['khhdon', 'Ky hieu HD'],
    ['shdon', 'So HD'],
    ['tdlap', 'Ngay lap'],
    ['nbmst', 'MST nguoi ban'],
    ['nbten', 'Ten nguoi ban'],
    ['nmmst', 'MST nguoi mua'],
    ['nmten', 'Ten nguoi mua'],
    ['nmcccd', 'So giay to (CCCD)'],
    ['tgtcthue', 'Tien chua thue'],
    ['tgtthue', 'Tien thue'],
    ['tgtttbso', 'Tong thanh toan'],
    ['dvtte', 'Don vi tien te'],
    ['tthai', 'Trang thai'],
    ['scope', 'scope'],
    ['ttxly', 'ttxly'],
    ['xml_status', 'xml_status'],
    ['file_xml', 'file_xml'],
    ['hash_xml', 'hash_xml'],
  ],

  // Cac truong so tien (de dinh dang so trong Excel)
  MONEY_FIELDS: ['tgtcthue', 'tgtthue', 'tgtttbso'],
};
