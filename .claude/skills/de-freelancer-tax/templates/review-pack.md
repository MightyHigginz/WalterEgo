# Steuerberater review pack - {{name}}, tax year {{year}}

Prepared by the DE-Tax-Suite (AI-assisted). Everything below is a draft for professional review; nothing has been filed.

## 1. Taxpayer profile and assumptions
{{profile table: marital status, church tax, state, health insurance, activities, VAT status, profit method}}
Assumptions made (each needs confirmation): {{list}}

## 2. Documents received / missing
| Document | Status | Needed for |
| :--- | :--- | :--- |

## 3. Results at a glance
| Item | Amount | Calculation / source |
| :--- | ---: | :--- |
| Betriebseinnahmen (EÜR Z23) | | `taxcalc.py eur` |
| Betriebsausgaben (EÜR Z75) | | |
| Gewinn | | |
| Zu versteuerndes Einkommen (estimate) | | profit - Sonderausgaben - ... |
| Einkommensteuer (tariff {{year}}) | | `taxcalc.py est` |
| Soli / Kirchensteuer | | |
| Prepayments made | | |
| Expected balance (payment / refund) | | |
| VAT: Zahllast per period (if Regelbesteuerung) | | `taxcalc.py ustva` |

## 4. Anlage EÜR line map (2025 form)
| Zeile | Kz | Item | EUR |
| :--- | :--- | :--- | ---: |

## 5. Decisions that need the advisor
1. Classification (Freiberufler vs. Gewerbe) - basis and risk.
2. VAT regime and any option/waiver (§ 19 Abs. 3 UStG, 5-year lock).
3. Treatment of each asset > EUR 800 / IAB / degressive AfA / e-vehicle write-off.
4. Home office method and proof.
5. Anything flagged under "Open issues".

## 6. Open issues and flags
| # | Issue | Source (statute/BMF) | Suggested handling | Risk |
| :--- | :--- | :--- | :--- | :--- |

## 7. Planning opportunities (legal)
{{from /optimize, each with statute, effect in EUR, deadline, downside}}

## 8. Evidence and sources
Statute text: `references/statutes/`; BMF: `references/bmf/`; digest: `references/research-2026-10.md`. Items marked "unverified" must be checked before filing.
