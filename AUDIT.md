# Audit of the DE-Tax-Suite (2026-10-03) - professional view

Verdict in one line: a solid, honest **preparation and review-pack tool for a sole proprietor's EÜR + VAT**, with verified statute text and automatic law-change alarms. It is **not yet a full tax-return system** and must not be used as one.

## A. What is sound (checked, with evidence)
| Area | Evidence |
| :--- | :--- |
| Statute text | 13 laws from gesetze-im-internet.de; `refresh.py` reproduces it byte-for-section (all unchanged on re-fetch) |
| Rules in use | 46 canary rules match the statute text (`check_rules.py`); a test proves a changed number is caught |
| Citations | 88 citations in skill/playbooks/workflow, 0 invalid (`cite_check.py`) |
| Calculations | 33 unit tests: tariff zones continuous, Soli Milderungszone, GWG/AfA, EÜR mapping, § 15 Abs. 1a UStG |
| EÜR mapping | Zeile + Kennzahl taken from the BMF-published Anlage EÜR 2025 |
| Tone and limits | disclaimer, no filing, "advisor decides" in every pack |

## B. Defects and weaknesses found in this audit
| # | Finding | Severity | Fix |
| :--- | :--- | :--- | :--- |
| 1 | **Statutes are today's consolidated text**, but a 2025 return needs the **2025 version** of each rule (e.g. Grundfreibetrag, Basisrente cap, GWG treatment, tariff). Older versions are not loaded. | High | Load version history per tax year (BGBl. / commercial database); tag every rule with valid-from/to |
| 2 | **2025 income-tax constants are reconstructed**, only checked for continuity. | High | Advisor confirms against the official Programmablaufplan; add golden test cases |
| 3 | **VAT return not mapped to ELSTER Kennzahlen** (Kz 81, 86, 66, 21 ...); `/quarterly` gives a checklist, not filing numbers. | High | Load the UStVA form + instructions; add Kz mapping and tests |
| 4 | **Only Anlage EÜR is mapped.** Missing: Mantelbogen (ESt 1 A), Anlagen S, G, N, V, KAP, SO, AV, Vorsorgeaufwand, Kind, Sonderausgaben/agB, AUS, SZ/AVEÜR, USt-Jahreserklärung, Gewerbesteuererklärung, Zusammenfassende Meldung, OSS | High | Load each year's BMF form text; map fields; one module per form |
| 5 | **Income-tax calculation is simplified**: no Pauschbeträge, Vorsorgeaufwendungen/Günstigerprüfung, Kinderfreibetrag/Kindergeld, Entlastungsbetrag, außergewöhnliche Belastungen, § 35a, Progressionsvorbehalt, Verlustvortrag application, Fünftelregelung, Kirchensteuer limits | High | Implement against statute with test vectors from the advisor's software |
| 6 | **Gewerbesteuer** lacks add-backs/deductions (§§ 8, 9 GewStG, e.g. financing add-backs) and loss carry-forward (§ 10a). | Medium | Implement from `gewstg.md` |
| 7 | **No administrative guidance beyond a few BMF letters**: EStR/EStH, AfA-Tabellen, travel, vehicle logbook, cash records (GoBD/KassenSichV), crypto, § 7g, home office, computer useful life (hosts were not on the allowlist). | Medium | Add the hosts; fetch the letters; add to `sources.json` |
| 8 | **No case-law corpus.** Classification (Freiberufler/Gewerbe, IT work), Ist-Versteuerung (BFH 2026 note), Scheinselbständigkeit rest on secondary sources. | Medium | Index BFH/FG decisions from the public sources; cite Aktenzeichen only from the file |
| 9 | **Playbooks only partly verified against statute**: rental, GmbH, capital/crypto contain claims not individually checked (listed in `research-2026-10.md`). | Medium | Verify line by line; add rules to `rules.json` |
| 10 | **Not covered:** inheritance/gift, property transfer tax, foreign income and treaties (DBA), exit/wegzug, reorganisations, payroll, trade of employees, holding structures, crypto mining/staking detail, insolvency | Medium | Route to advisor (already stated); add only if needed |
| 11 | **Agent behaviour never evaluated.** Tests cover code, not the model's judgement (classification, advice quality, refusal to evade). | Medium | Build an eval set with the advisor; run before each release |
| 12 | `__pycache__` files were committed by accident (8 files). | Low | Removed from git in this audit; ignored via `.gitignore` |
| 13 | Weekly refresh workflow is **untested** (runs only on GitHub default branch). | Low | Trigger once manually after merging |
| 14 | Basisrente 2026 cap (EUR 30,826) and KV ceilings are secondary-sourced. | Low | Verify; they change yearly |

## C. Legal and professional position (read this before using it on real clients)
- **Who may use it:** for your own affairs it is fine. Offering tax advice to third parties for a fee, even via software, is restricted to authorised persons (StBerG §§ 2, 3, 5). Running it inside a Steuerberater's practice is possible; the advisor stays responsible.
- **"He only has to check it" understates the advisor's duty.** A Steuerberater must form his own view and carries professional liability (§ 57 StBerG: independent, conscientious, responsible). He will want the sources, the assumptions and the open questions - the review pack provides them - but he cannot rely on the tool.
- **Data protection (GDPR):** tax IDs and bank data sent to a model provider need a lawful basis, a processing agreement and a retention decision; keep real data out of this public repo.
- **Record keeping:** keep the pack, inputs and tool versions per year (traceability); retention periods follow § 147 AO.
- **Transparency:** tell the advisor which parts were machine-generated.

## D. What you have to add (in order)
1. **Your real inputs:** tax year, activities (freelancer/trade/rental/employee), prior Steuerbescheid, bank export or ledger, invoices, insurance and pension certificates, prepayment notices, marital/child/church data.
2. **Advisor sign-off items:** 2025 tariff constants; classification and VAT regime; Basisrente cap; opinion on the open flags in the pack.
3. **Per-year legal versions** (Defect 1) and **golden test cases** from the advisor's tax software (Defects 2, 5): 10-20 anonymised profiles with the correct result.
4. **Forms and Kennzahlen** (Defects 3, 4) for the forms your profile needs, starting with UStVA and ESt Mantelbogen + Anlage S/N/Vorsorge.
5. **Allow more hosts** (Defect 7) and refresh once; **merge the branch** and trigger the workflow (Defect 13).
6. **Decide the deployment** (your server): language, interface, per-client isolation, backups, logging.
7. **Engagement paperwork with the advisor:** mandate, ELSTER authorisation (Vollmacht), who files, who is liable for what.
8. **Eval set** (Defect 11) built with the advisor, re-run after every legal refresh.

## E. Honest readiness
| Use | Ready? |
| :--- | :--- |
| Learning, orientation, spotting deductions, drafting questions for the advisor | Yes |
| Preparing EÜR + VAT figures for a sole trader for advisor review | Yes, with the caveats above |
| Producing a complete income-tax return for review | No (Defects 1-5) |
| Filing anything | No - by design |
| Serving other people's returns commercially | No - regulatory limits |
