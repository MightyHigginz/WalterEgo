# Research digest - 2026-10-03

## CORRECTIONS after reading the statute text (2026-10-03)
Primary access opened mid-session. Checked against statute text:
- CONFIRMED: § 19 UStG 25,000 / 100,000; § 6 Abs. 2 EStG 800 EUR; § 4 Abs. 5 Nr. 1 gifts 50 EUR, Nr. 2 Bewirtung 70%; § 7 Abs. 2 EStG 30% for assets after 30 Jun 2025 and before 1 Jan 2028; § 7g EStG 50%, EUR 200,000, 3 years, special depreciation 40% in year plus 4 years; § 10 Abs. 4 EStG 2,800 / 1,900; § 20 UStG 800,000 and freelancers; § 35 EStG 4x trade tax base; § 37 EStG dates and 400/100; § 10d EStG 1m/70%; § 147 AO 8 years for booking vouchers, 10 for books; § 9 Abs. 4a EStG 14/28.
- WRONG in secondary sources: tariff coefficients (statute: 914.51 / 173.10 / 1,034.87 / 11,135.63 / 19,470.38); room lump sum for non-centre rooms (statute: only if centre of activity; otherwise daily rate); late-filing minimum EUR 25 (statute § 152 Abs. 5: 0.25% of tax, min EUR 10; EUR 25 applies to Feststellungserklärungen); "22 months" (statute § 152 Abs. 2: 14 months); founders quarterly VAT (statute § 18 Abs. 2: monthly in start year and next, with 2021-2026 estimation rule).
- Still unverified from statute: electric-car 0.25% rule limit, Basisrente 2026 amount (derived annually), BFH 2026 Ist-Versteuerung ruling, BMF letters.

Method: web search (secondary sources only; statute and BMF sites were blocked by the session's network policy). Every row is `(S)` = secondary source, not yet checked against the statute. Re-verify the exact wording at gesetze-im-internet.de / bundesfinanzministerium.de when access exists. "Doubt" marks items where sources were thin or looked inconsistent.

## 1. Income tax
| Topic | Finding | Basis | Confidence |
| :--- | :--- | :--- | :--- |
| Tariff 2026 (single) | 0-12,348 zero; 12,349-17,799 (14% -> 23.97%); 17,800-69,878 (23.97% -> 42%); 69,879-277,825 at 42%; from 277,826 at 45% | § 32a EStG | (S) medium; formulas quoted by sources: zone 2 (954.80 y + 1,400) y; zone 3 (181.19 z + 2,397) z + 991.21; top 0.42 x - 11,136.95; 0.45 x - 19,471.95 |
| Splitting | all thresholds doubled for joint assessment | § 32a Abs. 5 EStG | (S) |
| Soli | 5.5% of income tax; exemption limit EUR 20,350 single / EUR 40,700 joint | SolzG | (S) |
| Church tax | 8% (Bavaria, Baden-Württemberg), 9% elsewhere, on assessed income tax; no exemption limit | state church tax laws | (S) |
| Advance payments | 10 Mar, 10 Jun, 10 Sep, 10 Dec; set only if at least EUR 400/year and EUR 100 per date | § 37 EStG | (S) |
| Return deadline tax year 2025 | 31 Jul 2026 self-prepared; 1 Mar 2027 with Steuerberater; late-filing surcharge mandatory if not filed within 14 months after year-end when a tax advisor is used; minimum EUR 25 per started month | § 149 AO, § 152 AO | (S) doubt: 14-month vs 22-month wording differs between sources; verify |
| Loss carry (§ 10d EStG) | carry-back 2 years (optional), carry-forward mandatory; up to EUR 1m (EUR 2m joint) fully offset, above that 70% of the excess in 2024-2027 | § 10d EStG | (S) doubt on the 70% figure |
| Hobby risk | persistent losses without intent to make profit (**Liebhaberei**) mean no loss offset | § 2 EStG, BMF | (S) |

## 2. VAT
| Topic | Finding | Basis | Confidence |
| :--- | :--- | :--- | :--- |
| Kleinunternehmer | see SKILL.md Module B; waiver binds 5 calendar years | § 19 UStG | (S) high |
| Ist-Versteuerung | taxed on payment received; allowed up to EUR 800,000 prior-year turnover; freelancers may apply regardless of turnover | § 20 UStG | (S) medium |
| BFH 2026 on Ist-Versteuerung | a freelancer who voluntarily computes profit by balance-sheet comparison (Betriebsvermögensvergleich) can't use § 20 | BFH (single secondary source) | doubt; verify case number |
| Cross-border B2B services in EU | place of supply at the customer; invoice without VAT, note "Steuerschuldnerschaft des Leistungsempfängers (§ 13b UStG)", both VAT IDs; report in the **Zusammenfassende Meldung** and UStVA (Kennzahl 21) | § 3a Abs. 2, § 13b, § 18a UStG | (S) medium |
| Voranmeldung filing interval | monthly if prior-year VAT > EUR 9,000; quarterly EUR 2,000-9,000; may be exempt below EUR 2,000; founders: special rule through 2026 | § 18 Abs. 2 UStG | (S) medium |
| Dauerfristverlängerung | +1 month; monthly filers pay a special advance of 1/11 of prior-year VAT | § 46-48 UStDV | (S) |
| E-invoice | see SKILL.md Module F | § 14 UStG, § 34a UStDV, BMF 2024/2025 | (S) |

## 3. Business expenses (Betriebsausgaben) - quick reference for `/deduct`
| Item | Rule | Basis |
| :--- | :--- | :--- |
| Entertainment of business partners (**Bewirtung**) | 70% deductible, separate account, receipt with names and reason | § 4 Abs. 5 Nr. 2 EStG |
| Gifts | deductible only up to EUR 50 per recipient per year (net) | § 4 Abs. 5 Nr. 1 EStG (the limit rose from EUR 35 in 2024) |
| Training / education | fully deductible with link to the activity | § 4 Abs. 4 EStG |
| Computer, software | 1-year useful life (BMF 26 Feb 2021), full write-off | § 7 EStG |
| Travel meal allowance (**Verpflegungspauschale**) | EUR 14 (more than 8 h away), EUR 28 (24 h); unchanged since 2021; reduced for meals provided | § 4 Abs. 5 Nr. 5 i.V.m. § 9 Abs. 4a EStG |
| Mileage | business trips with the private car: EUR 0.30/km flat (practice) or actual costs; the commuting allowance (**Entfernungspauschale**) is a separate rule, not for business trips | BMF practice; verify |
| Company car | 1% rule or logbook; electric vehicles 0.25% of list price when list price is up to EUR 100,000 (limit raised from EUR 70,000); self-employed also apply the private-use rule (**Entnahme**) | § 6 Abs. 1 Nr. 4, § 4 Abs. 5 EStG | doubt: start date of the EUR 100,000 limit differs among sources |
| Health and care insurance | basic cover deductible without cap; other provisions up to EUR 2,800 for self-employed, EUR 1,900 for employees | § 10 Abs. 4 EStG | (S) |
| Contributions to health insurance (GKV) | 2026: contribution assessment ceiling EUR 5,812.50/month; general rate 14.6% + average additional 2.9% | SGB V | (S) |
| Non-deductible | private items, fines, gifts above limit, 30% of Bewirtung | § 4 Abs. 5 EStG |

## 4. Social-law traps for freelancers
- **Scheinselbständigkeit**: one client > about 5/6 of revenue, no own employees, instructions bound, integrated in the client's organisation -> risk of social-insurance liability. A voluntary status procedure (**Statusfeststellungsverfahren**, § 7a SGB IV) at the Deutsche Rentenversicherung Bund gives certainty. (S)
- **Rentenversicherungspflicht** for some self-employed (§ 2 SGB VI), e.g. one main client and no employees. (S)
- **Künstlersozialkasse (KSK)**: artists and publicists get statutory social insurance if income reaches EUR 3,900/year. Commissioning firms owe the **Künstlersozialabgabe**, 4.9% in 2026; de-minimis limit of EUR 1,000 for some cases from 2026. (S) BMAS press release confirmed the 4.9%.

## 5. Process
- Registration: **Fragebogen zur steuerlichen Erfassung** via ELSTER, with profit estimate (drives advance payments), profit method, VAT choice (Kleinunternehmer waiver binds 5 years). (S)
- Retention (**Aufbewahrung**, § 147 AO): booking vouchers 8 years since 1 Jan 2025 (BEG IV); books, annual accounts 10 years; cash book 10 years. (S) medium.
- GoBD applies to digital records.

## 6. Open items needing primary sources
1. Exact § 7g EStG wording: profit limit EUR 200,000, 50%, 3-year investment period.
2. § 7 Abs. 2 EStG declining-balance rule dates (after 30 Jun 2025, before 1 Jan 2028).
3. BFH 2026 Ist-Versteuerung ruling: case number and holding.
4. Late-filing surcharge periods (§ 152 AO).
5. EUR 0.25% EV rule effective date.
6. Founders' quarterly VAT special rule (end 2026?).
7. Kleinunternehmer in practice: BMF letter 18 Mar 2025, sections on invoices and cross-border sales.
