# Workflow: prepare a full tax file for a Steuerberater

Goal: give the human advisor a complete, checked, reviewable file. Not to file it. Filing (ELSTER) is done by the advisor or the taxpayer after review.

## Step 0 - Scope and year
Ask which tax year (default: the latest completed one; returns for the year are due 31 Jul of the following year, or the end of February of the second following year via an advisor, § 149 AO). Use that year's tariff (`taxcalc.py est --year`). Only 2025 and 2026 constants exist; 2025 values are reconstructed and must be confirmed.

## Step 1 - Intake
Fill `templates/intake.json` with the user (ask in small batches, most impactful first). Place the taxpayer via `playbooks/00-router.md`.

## Step 2 - Documents
Request per activity: ledger/bank statements and invoices (-> `templates/ledger.csv`), asset purchases, prior assessment (Steuerbescheid), advance-payment notices, insurance certificates (KV/PV, Basisrente via Anlage AV), employer wage statement, rental statement, broker tax certificate, donation receipts.

## Step 3 - Compute (reproducible)
1. Categorise every ledger line with the category names in `tools/taxcalc.py` `EUR_LINES`. Unknown categories are flagged, never guessed.
2. `python3 tools/taxcalc.py eur ledger.csv [--regular-vat]` -> EÜR lines with Zeile and Kennzahl; `ustva` for VAT; `asset` for each purchase; `gewst` for trade tax.
3. Build the other income types (Anlage N, V, KAP, ...) from the documents; not automated.
4. Compute: Summe der Einkünfte -> minus Sonderausgaben (Basisrente, KV/PV basis, others) -> minus außergewöhnliche Belastungen -> zu versteuerndes Einkommen -> `taxcalc.py est` (+ Soli, Kirchensteuer) -> minus prepayments.

## Step 4 - Cross-check (must pass before handing over)
- Re-run `python3 -m unittest` in `tools/`.
- Each rule used has a statute reference in `references/statutes/` or a BMF letter, quoted from the file.
- Plausibility: profit vs. prior year (> ±30% needs explanation); VAT vs. turnover; private use of phone/car; round-number receipts; missing months.
- Thresholds applied for the right year (Kleinunternehmer limits, GWG, Basisrente cap).
- Cash vs. accrual (§ 11 EStG) for year-end items.
- Mismatch between ledger VAT and UStVA filings.

## Step 5 - Review pack
Fill `templates/review-pack.md` (profile, assumptions, results, EÜR line map, advisor decisions, open issues, planning). Export as a document for the advisor. Include the ledger CSV and the JSON output of each tool run.

## Step 6 - After review
Apply the advisor's corrections, rerun computations, update the pack. Filing and tax-office correspondence stay with the advisor or the taxpayer.

## Limits to state up front
- No ELSTER submission; no authorised tax advice (§§ 2, 3 StBerG). The human advisor decides.
- Forms other than Anlage EÜR (Mantelbogen, S, G, N, V, KAP, Vorsorgeaufwand, AV) are not loaded; line numbers for them must come from the advisor or the current ELSTER form.
- The calculator estimates tax; the Finanzamt's calculation governs. Child allowances, loss carry, progression clause, Günstigerprüfung, Kirchensteuer details are simplified or not modelled.
