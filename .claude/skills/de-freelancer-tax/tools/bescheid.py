#!/usr/bin/env python3
"""Tax-notice (Steuerbescheid) checker and objection (Einspruch) draft.
  bescheid.py check notice.json [--return pack.json]   compare notice with the return, recompute the tax, list deviations
  bescheid.py deadline YYYY-MM-DD                        objection deadline from the notice date (§ 122 Abs. 2, § 355, § 108 Abs. 3 AO)
  bescheid.py draft notice.json out.md [--points "text; text"] [--suspend]   German objection letter draft
Statute checks: § 122 Abs. 2 Nr. 1 AO (deemed served on the 4th day after posting - the statute has no weekend shift for this day), § 355 Abs. 1 AO (one month),
§ 108 Abs. 3 AO (weekend/holiday -> next working day; national holidays are NOT modelled: check them)."""
import argparse, calendar, datetime as dt, json, sys
import taxcalc as T

def _add_month(d):
    y, m = (d.year + (d.month == 12), d.month % 12 + 1); return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
def _next_workday(d):
    while d.weekday() >= 5: d += dt.timedelta(days=1)
    return d

def deadline(notice_date, posted=True):
    """notice_date: date on the notice (assumed posting date). Returns dict."""
    d = dt.date.fromisoformat(notice_date) if isinstance(notice_date, str) else notice_date
    served = d + dt.timedelta(days=4) if posted else d                           # § 122 Abs. 2 Nr. 1 AO: 4th day, no weekend shift
    end = _next_workday(_add_month(served))                                     # § 355 Abs. 1, § 108 Abs. 3 AO
    return {"posted": d.isoformat(), "deemed_served": served.isoformat(), "objection_deadline": end.isoformat(),
            "note": "Check public holidays; Paper notice assumed. Notices sent electronically (§ 122 Abs. 2a AO) or provided for download (§ 122a Abs. 4 AO) are also deemed served on the 4th day - count from the dispatch / provision date, not the notice date. Public holidays are not modelled."}

FIELDS = [("einkuenfte_selbstaendig", "Einkünfte aus selbständiger Arbeit"), ("einkuenfte_gewerbe", "Einkünfte aus Gewerbebetrieb"),
          ("einkuenfte_nichtselbst", "Einkünfte nichtselbständige Arbeit"), ("einkuenfte_kapital", "Einkünfte Kapitalvermögen"),
          ("einkuenfte_vermietung", "Einkünfte Vermietung"), ("sonderausgaben", "Sonderausgaben"), ("zve", "zu versteuerndes Einkommen"),
          ("est", "Einkommensteuer"), ("soli", "Solidaritätszuschlag"), ("kirchensteuer", "Kirchensteuer"), ("vorauszahlungen", "Vorauszahlungen angerechnet"),
          ("saldo", "Nachzahlung (+) / Erstattung (-)")]

def check(notice, filed=None, tol=1.0):
    rows, flags = [], []
    year = notice.get("steuerjahr", 2025); y = year if year in T.TARIFF else 2026
    for key, label in FIELDS:
        n, f = notice.get(key), (filed or {}).get(key)
        if n is None: continue
        diff = None if f is None else round(n - f, 2)
        st = "OK" if diff is not None and abs(diff) <= tol else ("DIFFERS" if diff is not None else "no comparison")
        rows.append({"item": label, "notice": n, "filed": f, "difference": diff, "status": st})
        if st == "DIFFERS": flags.append(f"{label}: notice {n:,.2f} vs filed {f:,.2f} (difference {diff:+,.2f}) - find the reason in the 'Erläuterungen' of the notice")
    if "zve" in notice and "est" in notice:
        calc = T.tariff(notice["zve"], bool(notice.get("splitting")), y)
        if abs(calc - notice["est"]) > tol and not notice.get("kinder_oder_besondere_steuer"):
            flags.append(f"ESt recomputed from zvE with the {y} tariff = {calc:,}, notice says {notice['est']:,}: check child allowances, Steuer on capital income, § 34 or other special rules, or an arithmetic error")
    if all(k in notice for k in ("est", "soli", "kirchensteuer", "vorauszahlungen", "saldo")):
        calc = notice["est"] + notice["soli"] + notice["kirchensteuer"] - notice["vorauszahlungen"]
        if abs(calc - notice["saldo"]) > tol: flags.append(f"balance does not add up: {calc:,.2f} vs {notice['saldo']:,.2f}")
    if notice.get("vorbehalt_nachpruefung"): flags.append("Vorbehalt der Nachprüfung (§ 164 AO): the notice can still be changed by either side until the reservation is lifted")
    if notice.get("vorlaeufig"): flags.append("Vorläufigkeitsvermerk (§ 165 AO) on: " + ", ".join(notice["vorlaeufig"]))
    if notice.get("schaetzung"): flags.append("estimated assessment (§ 162 AO): file the missing return and object within the deadline")
    dl = deadline(notice["datum"]) if notice.get("datum") else None
    return {"rows": rows, "flags": flags, "deadline": dl}

def draft(notice, points, suspend=False):
    n = notice; art = n.get("art", "Einkommensteuerbescheid")
    pts = "\n".join(f"{i}. {p.strip()}" for i, p in enumerate(points, 1)) or "1. [Begründung hier einfügen]"
    aus = ("\n**Antrag auf Aussetzung der Vollziehung (§ 361 AO):** Ich beantrage, die Vollziehung des angefochtenen Bescheids in Höhe von "
           f"{n.get('streitig', '[Betrag]')} EUR auszusetzen.\n") if suspend else ""
    return f"""> ENTWURF - vor dem Versand von der Steuerberaterin / dem Steuerberater prüfen lassen. Frist beachten (Einspruchsfrist: ein Monat nach Bekanntgabe, § 355 Abs. 1 AO).

{n.get('absender', '[Name, Anschrift]')}
Steuernummer / IdNr.: {n.get('steuernummer', '[Steuernummer]')}

An das Finanzamt {n.get('finanzamt', '[Finanzamt, Anschrift]')}

[Ort], [Datum]

**Einspruch gegen den {art} {n.get('steuerjahr', '[Jahr]')} vom {n.get('datum', '[Datum des Bescheids]')}**

Sehr geehrte Damen und Herren,

gegen den oben genannten Bescheid lege ich hiermit **Einspruch** ein (§ 347 AO).

**Begründung:**
{pts}

Weitere Unterlagen und eine ausführliche Begründung reiche ich bei Bedarf nach. Ich bitte darum, die Einspruchsentscheidung bis dahin zurückzustellen.
{aus}
Bitte bestätigen Sie mir den Eingang dieses Schreibens.

Mit freundlichen Grüßen

[Unterschrift]
"""

def main():
    ap = argparse.ArgumentParser(description=__doc__); sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("notice"); c.add_argument("--return", dest="ret")
    d = sub.add_parser("deadline"); d.add_argument("date")
    w = sub.add_parser("draft"); w.add_argument("notice"); w.add_argument("out"); w.add_argument("--points", default=""); w.add_argument("--suspend", action="store_true")
    a = ap.parse_args()
    if a.cmd == "check": print(json.dumps(check(json.load(open(a.notice)), json.load(open(a.ret)) if a.ret else None), indent=1, ensure_ascii=False))
    elif a.cmd == "deadline": print(json.dumps(deadline(a.date), indent=1))
    else:
        open(a.out, "w", encoding="utf-8").write(draft(json.load(open(a.notice)), [p for p in a.points.split(";") if p.strip()], a.suspend)); print("draft written to", a.out)
if __name__ == "__main__": main()
