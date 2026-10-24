// chon_hd.js — ô chọn hợp đồng có lọc theo Bên A, Dự án và từ khoá (dùng chung: Phụ lục, BOQ, Kiểm tra đợt).
// Bộ lọc dùng chung cho mọi màn hình (state.hdLoc). Khi lọc làm hợp đồng đang chọn rơi khỏi danh sách,
// app.js tự chọn hợp đồng đầu tiên còn lại (phát sự kiện change trên ô [data-hd-pick]).
import { escapeHTML as E } from "./ui.js";

export function boLoc(state) {
  if (!state.hdLoc) state.hdLoc = { ben_a: "", du_an: "", q: "" };
  return state.hdLoc;
}
const gon = (t) =>
  String(t || "")
    .replace(/^Công ty (Cổ phần|CP|TNHH( MTV)?)\s+/i, "")
    .trim();
const khop = (h, loc) => {
  const q = (loc.q || "").trim().toLocaleLowerCase("vi");
  return (
    (!loc.ben_a || (h.ben_a || "") === loc.ben_a) &&
    (!loc.du_an || (h.du_an || h.goi_thau || "") === loc.du_an) &&
    (!q || `${h.ma_hd} ${h.so_hd} ${h.ben_a || ""} ${h.ben_b || ""} ${h.du_an || ""} ${h.goi_thau || ""}`.toLocaleLowerCase("vi").includes(q))
  );
};
const ngan = (t, n = 60) => (t.length > n ? t.slice(0, n - 1) + "…" : t);

/** HTML các ô lọc + ô chọn hợp đồng.
 *  ds: danh sách /api/hop_dong; selected: mã đang chọn; attr: thuộc tính của ô chọn (vd 'data-contract-field="boqContract"');
 *  nhan: nhãn ô chọn. */
export function chonHopDong(state, ds, selected, attr, nhan = "Hợp đồng") {
  const loc = boLoc(state);
  ds = ds || [];
  // danh sách Bên A / Dự án: Dự án chỉ lấy trong Bên A đang lọc
  const benA = [...new Set(ds.map((h) => h.ben_a).filter(Boolean))].sort((a, b) => gon(a).localeCompare(gon(b), "vi"));
  const duAn = [...new Set(ds.filter((h) => !loc.ben_a || h.ben_a === loc.ben_a).map((h) => h.du_an || h.goi_thau).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "vi"),
  );
  const loc_ = ds.filter((h) => khop(h, loc));
  const dangLoc = loc.ben_a || loc.du_an || (loc.q || "").trim();
  const opts = loc_.length
    ? loc_
        .map(
          (h) =>
            `<option value="${E(h.ma_hd)}" ${h.ma_hd === selected ? "selected" : ""}>${E(h.so_hd)}${h.ben_b ? " · " + E(ngan(gon(h.ben_b), 40)) : ""}${h.du_an ? " · " + E(ngan(h.du_an, 50)) : ""}</option>`,
        )
        .join("")
    : `<option value="">${ds.length ? "Không có hợp đồng phù hợp bộ lọc" : "Chưa có hợp đồng trong CSDL"}</option>`;
  return `<label class="field" style="min-width:170px;max-width:240px"><span>Bên A</span><select data-hd-loc="ben_a"><option value="">Tất cả bên A</option>${benA
    .map((b) => `<option value="${E(b)}" ${loc.ben_a === b ? "selected" : ""} title="${E(b)}">${E(ngan(gon(b), 45))}</option>`)
    .join("")}</select></label><label class="field" style="min-width:170px;max-width:260px"><span>Dự án</span><select data-hd-loc="du_an"><option value="">Tất cả dự án</option>${duAn
    .map((d) => `<option value="${E(d)}" ${loc.du_an === d ? "selected" : ""} title="${E(d)}">${E(ngan(d, 55))}</option>`)
    .join("")}</select></label><label class="field" style="min-width:150px;max-width:200px"><span>Tìm</span><input type="search" id="hd-loc-q" data-hd-loc="q" value="${E(loc.q || "")}" placeholder="Số HĐ, bên B…"></label><label class="field" style="flex:1;min-width:260px"><span>${E(nhan)}${dangLoc ? ` <span class="muted small">(${loc_.length}/${ds.length})</span>` : ""}</span><select data-hd-pick data-cur="${E(selected || "")}" ${attr}>${opts}</select></label>`;
}
