"""Lead: so file kết quả MỚI (argv[1]) với NỀN (argv[2]) theo ids_loi. Không dùng chung tên với script của worker."""
import json
import sys


def load(f):
    d = json.load(open(f, encoding="utf-8"))
    return d.get("modules", d)


moi, nen = load(sys.argv[1]), load(sys.argv[2])


def tong(m):
    t = {k: 0 for k in ("ok", "error", "fail", "skip", "treo")}
    for v in m.values():
        if isinstance(v, dict):
            for k in t:
                t[k] += int(v.get(k, 0) or 0)
    return t, len(m)


print("MOI :", *tong(moi))
print("NEN :", *tong(nen))
loi_moi = 0
for k, v in sorted(moi.items()):
    if not isinstance(v, dict):
        continue
    o = nen.get(k)
    a = set(v.get("ids_loi") or [])
    if o is None:
        if a or v.get("treo"):
            print("  MODULE MOI co loi:", k, f"{v.get('ok')}/{v.get('error')}/{v.get('fail')}/{v.get('skip')}", (v.get("loi_dau") or "")[:100])
        continue
    m = a - set(o.get("ids_loi") or [])
    if m:
        loi_moi += len(m)
        print("  LOI MOI:", k, len(m), sorted(m)[:3], (v.get("loi_dau") or "")[:100])
    if v.get("treo") and not o.get("treo"):
        print("  TREO MOI:", k)
het = [k for k, o in nen.items() if isinstance(o, dict) and o.get("treo") and not (moi.get(k) or {}).get("treo")]
print("het treo:", het, "| tong ma loi moi:", loi_moi)
