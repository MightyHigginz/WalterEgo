#!/usr/bin/env python3
"""Multi-year memory: asset register (AfA), § 7g investment deductions, loss carry-forward, year summaries.
State lives in one JSON file per client (default: ./private/<client>/state.json, git-ignored).
Rules implemented (statute text checked): § 7 Abs. 1 (linear, monthly pro rata), § 7 Abs. 2 (declining
balance max 30% / 3x linear, acquisitions 1 Jul 2025 - 31 Dec 2027), § 7 Abs. 2a (e-vehicle 75/10/5/5/3/2),
§ 7 Abs. 3 (switch to linear), § 6 Abs. 2/2a (GWG, Sammelposten), § 7g Abs. 1-3 (IAB), § 10d Abs. 2 (carry-forward).
Usage: state.py CLIENT_DIR init|asset-add|register|iab-add|iab-status|close-year|years ...  (see --help)"""
import argparse, datetime as dt, json, os, sys

SCHEMA = 1
ECAR = [0.75, 0.10, 0.05, 0.05, 0.03, 0.02]

def load(d):
    p = os.path.join(d, "state.json")
    if not os.path.exists(p):
        return {"schema": SCHEMA, "assets": [], "iab": [], "years": {}, "loss_carryforward": {"amount": 0.0, "as_of_year": None}}
    return json.load(open(p, encoding="utf-8"))

def save(d, s):
    os.makedirs(d, exist_ok=True)
    json.dump(s, open(os.path.join(d, "state.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

def _date(x): return dt.date.fromisoformat(x)

# ---------------- AfA ----------------
def _months_first_year(acq): return 13 - acq.month

def schedule(a, last_year):
    """Return {year: {'afa': x, 'book_end': y, 'abgang': z, 'erloes': p}} up to last_year for asset dict a."""
    acq = _date(a["acquired"]); cost = float(a["cost"]) * float(a.get("business_use_pct", 100)) / 100
    m = a["method"]; out = {}; book = cost
    disp = _date(a["disposed"]["date"]) if a.get("disposed") else None
    life = a.get("life_years")
    if m == "ecar75" and not (dt.date(2025, 7, 1) <= acq < dt.date(2028, 1, 1)):
        raise ValueError("ecar75 only for e-vehicles acquired 1 Jul 2025 - 31 Dec 2027 (§ 7 Abs. 2a EStG)")
    if m == "degressive" and not (dt.date(2025, 7, 1) <= acq < dt.date(2028, 1, 1)):
        raise ValueError("degressive 30% only for acquisitions 1 Jul 2025 - 31 Dec 2027 (§ 7 Abs. 2 EStG)")
    months_done = 0
    for y in range(acq.year, last_year + 1):
        first = (y == acq.year)
        months = _months_first_year(acq) if first else 12
        if disp and y == disp.year:
            months = (disp.month - (acq.month - 1)) if first else disp.month   # months up to and incl. disposal month
            months = max(months, 0)
        if book <= 0.005:
            afa = 0.0
        elif m in ("sofort", "gwg", "computer"):
            afa = book if first else 0.0
        elif m == "sammelposten":
            afa = min(cost * 0.20, book)
        elif m == "ecar75":
            idx = y - acq.year; afa = cost * ECAR[idx] if idx < len(ECAR) else 0.0
            afa = min(afa, book)
        elif m == "linear":
            afa = min(cost / life * months / 12, book)
        elif m == "degressive":
            rate = min(0.30, 3.0 / life)
            degr = book * rate * (months / 12 if first else 1)
            rem_months = max(life * 12 - months_done, 1)
            lin = book / rem_months * min(months, 12)
            afa = min(max(degr, lin) if a.get("auto_switch", True) and not first else degr, book)
        else:
            raise ValueError(f"unknown method {m}")
        months_done += months if m in ("linear", "degressive") else 0
        book -= afa
        rec = {"afa": round(afa, 2), "book_end": round(book, 2), "abgang": 0.0, "erloes": 0.0}
        if disp and y == disp.year:
            rec["abgang"] = round(book, 2); rec["erloes"] = float(a["disposed"].get("proceeds", 0)); rec["book_end"] = 0.0; book = 0.0
        out[y] = rec
        if disp and y == disp.year: break
    return out

def register(s, year):
    rows, tot = [], {"afa_beweglich": 0.0, "gwg": 0.0, "sammelposten": 0.0, "restbuchwert_abgang": 0.0, "erloes_abgang": 0.0}
    for a in s["assets"]:
        acq = _date(a["acquired"])
        if acq.year > year: continue
        sch = schedule(a, year)
        if year not in sch:
            continue
        r = sch[year]; prev = sch.get(year - 1, {}).get("book_end", 0.0) if year > acq.year else 0.0
        zugang = round(float(a["cost"]) * float(a.get("business_use_pct", 100)) / 100, 2) if acq.year == year else 0.0
        rows.append({"id": a["id"], "description": a["description"], "method": a["method"], "buchwert_beginn": round(prev, 2),
                     "zugang": zugang, "afa": r["afa"], "abgang": r["abgang"], "buchwert_ende": r["book_end"]})
        key = {"gwg": "gwg", "sammelposten": "sammelposten"}.get(a["method"], "afa_beweglich")
        tot[key] += r["afa"]; tot["restbuchwert_abgang"] += r["abgang"]; tot["erloes_abgang"] += r["erloes"]
    tot = {k: round(v, 2) for k, v in tot.items()}
    eur = {"Z33 AfA bewegliche WG": tot["afa_beweglich"], "Z36 GWG (§ 6 Abs. 2)": tot["gwg"], "Z37 Auflösung Sammelposten": tot["sammelposten"],
           "Z38 Restbuchwert Abgänge": tot["restbuchwert_abgang"], "Z19 Veräußerungserlöse": tot["erloes_abgang"]}
    return {"year": year, "rows": rows, "eur_lines": eur}

def classify_new(cost_net, kind="other", electric=False, acquired=None):
    """Suggest methods for a purchase (advisor decides)."""
    opts = []
    if kind == "computer": opts.append(("computer", "Nutzungsdauer 1 Jahr, volle Abschreibung (BMF 26.02.2021)"))
    if cost_net <= 800: opts.append(("gwg", "GWG-Sofortabzug § 6 Abs. 2 EStG"))
    if 250 < cost_net <= 1000: opts.append(("sammelposten", "Sammelposten 5 Jahre § 6 Abs. 2a EStG (Wahlrecht einheitlich je Jahr)"))
    opts.append(("linear", "lineare AfA § 7 Abs. 1 EStG"))
    if acquired and dt.date(2025, 7, 1) <= _date(acquired) < dt.date(2028, 1, 1):
        opts.append(("degressive", "degressive AfA bis 30% § 7 Abs. 2 EStG"))
        if electric: opts.append(("ecar75", "E-Fahrzeug 75/10/5/5/3/2 § 7 Abs. 2a EStG"))
    return opts

# ---------------- IAB § 7g ----------------
def iab_check(s, year_now, profit_prior_to_iab=None):
    out = []
    for i in s["iab"]:
        if i["status"] != "open": continue
        deadline = i["year"] + 3
        out.append({"id": i["id"], "year": i["year"], "amount": i["amount"], "deadline_end_of": deadline,
                    "action": "REVERSE in year %d (§ 7g Abs. 3 EStG) - investment missing" % i["year"] if year_now > deadline else f"invest by 31.12.{deadline}"})
    window = sum(i["amount"] for i in s["iab"] if i["status"] == "open" and year_now - 3 <= i["year"] <= year_now)
    warn = []
    if window > 200000: warn.append("sum of open IAB in the last 4 years exceeds EUR 200,000 (§ 7g Abs. 1 S. 4)")
    if profit_prior_to_iab is not None and profit_prior_to_iab > 200000: warn.append("profit above EUR 200,000: no IAB allowed (§ 7g Abs. 1 S. 2 Nr. 1b)")
    return {"open": out, "warnings": warn}

def iab_use(i, cost):
    """Hinzurechnung: up to 50% of acquisition cost, max the IAB amount (§ 7g Abs. 2)."""
    return round(min(i["amount"], 0.5 * cost), 2)

# ---------------- losses § 10d ----------------
def apply_loss(gesamtbetrag, carry):
    """Return (used, new_carry, new_loss_added). Gesamtbetrag der Einkünfte after Verlustausgleich."""
    if gesamtbetrag < 0:
        return 0.0, carry + (-gesamtbetrag), -gesamtbetrag
    cap = min(gesamtbetrag, 1_000_000) + 0.7 * max(gesamtbetrag - 1_000_000, 0)
    used = min(carry, cap)
    return round(used, 2), round(carry - used, 2), 0.0

def close_year(s, year, gesamtbetrag, profit=None, ust_zahllast=None, est_paid=None):
    carry = s["loss_carryforward"]["amount"]
    used, new, added = apply_loss(gesamtbetrag, carry)
    s["loss_carryforward"] = {"amount": new, "as_of_year": year}
    s["years"][str(year)] = {"gesamtbetrag": gesamtbetrag, "profit": profit, "ust_zahllast": ust_zahllast, "est_prepaid": est_paid,
                             "loss_used": used, "loss_added": added, "closed": True}
    return s["years"][str(year)]

def compare_years(s, year):
    a, b = s["years"].get(str(year)), s["years"].get(str(year - 1))
    if not a or not b or not a.get("profit") or not b.get("profit"): return {"note": "no comparable prior year"}
    ch = (a["profit"] - b["profit"]) / abs(b["profit"]) * 100
    return {"profit": a["profit"], "prior": b["profit"], "change_pct": round(ch, 1), "flag": abs(ch) > 30}

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("dir"); sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    a = sub.add_parser("asset-add"); [a.add_argument(x) for x in ("id", "description", "acquired", "cost")]
    a.add_argument("--method", default="linear"); a.add_argument("--life", type=float); a.add_argument("--use", type=float, default=100)
    r = sub.add_parser("register"); r.add_argument("year", type=int)
    i = sub.add_parser("iab-add"); i.add_argument("id"); i.add_argument("year", type=int); i.add_argument("amount", type=float); i.add_argument("--plan", default="")
    c = sub.add_parser("iab-status"); c.add_argument("year", type=int)
    y = sub.add_parser("close-year"); y.add_argument("year", type=int); y.add_argument("gesamtbetrag", type=float); y.add_argument("--profit", type=float)
    a2 = sub.add_parser("suggest"); a2.add_argument("cost", type=float); a2.add_argument("--kind", default="other"); a2.add_argument("--acquired"); a2.add_argument("--electric", action="store_true")
    sub.add_parser("years")
    g = ap.parse_args(); s = load(g.dir)
    if g.cmd == "init": save(g.dir, s); print("initialised", g.dir)
    elif g.cmd == "asset-add":
        s["assets"].append({"id": g.id, "description": g.description, "acquired": g.acquired, "cost": float(g.cost), "method": g.method, "life_years": g.life, "business_use_pct": g.use}); save(g.dir, s); print("asset added")
    elif g.cmd == "register": print(json.dumps(register(s, g.year), indent=1, ensure_ascii=False))
    elif g.cmd == "iab-add": s["iab"].append({"id": g.id, "year": g.year, "amount": g.amount, "plan": g.plan, "status": "open"}); save(g.dir, s); print("iab added")
    elif g.cmd == "iab-status": print(json.dumps(iab_check(s, g.year), indent=1))
    elif g.cmd == "close-year": print(json.dumps(close_year(s, g.year, g.gesamtbetrag, g.profit), indent=1)); save(g.dir, s)
    elif g.cmd == "suggest": print(json.dumps(classify_new(g.cost, g.kind, g.electric, g.acquired), indent=1, ensure_ascii=False))
    elif g.cmd == "years": print(json.dumps(s["years"], indent=1))
if __name__ == "__main__": main()
