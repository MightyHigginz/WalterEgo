# Adding the DE-Tax-Suite to another project

## 1. What to copy
| From this repo | To the other project | Needed for |
| :--- | :--- | :--- |
| `.claude/skills/de-freelancer-tax/` (whole folder, ~8.7 MB) | `.claude/skills/de-freelancer-tax/` | skill, playbooks, tools, statutes, BMF texts, rules |
| `.claude/agents/de-freelancer-tax.md` | `.claude/agents/de-freelancer-tax.md` | the consultant agent (loads the skill) |
| `.github/workflows/refresh-tax-sources.yml` (optional) | same path | weekly law refresh PR |

Home-wide instead of per project: copy the first two to `~/.claude/skills/` and `~/.claude/agents/`.
Or run `./package.sh` here to get `dist/de-tax-suite.zip` and unzip it at the root of the other project.

## 2. Requirements
- Python 3.9+ (standard library only). Optional: `pip install openpyxl` for the Excel export (CSV files are written without it). `poppler-utils` (`pdftotext`) only for `refresh.py --apply`.
- Verify after copying: `cd .claude/skills/de-freelancer-tax/tools && python3 -m unittest && python3 check_rules.py` (expect all tests OK and all rules matching).

## 3. Merge points with an existing invoices project
| Item | Format | Where |
| :--- | :--- | :--- |
| Invoice check | JSON keys: supplier_name, supplier_address, tax_number_or_vat_id, invoice_date, invoice_number, service_description, service_date, net_amount, vat_rate, vat_amount, gross_amount, customer_name, customer_address | `tools/invoice_check.py` (§ 14 Abs. 4 UStG, § 33 UStDV for <= 250 EUR) |
| Ledger | CSV `date,description,category,net,vat` (amounts positive; Kleinunternehmer: gross in `net`, vat 0) | `tools/taxcalc.py` `EUR_LINES` lists the allowed categories |
| Bank import | semicolon CSV with Buchungstag / Verwendungszweck / Betrag | `tools/bank_import.py` |
| Review pack | intake JSON + ledger CSV -> markdown + CSVs | `tools/build_pack.py`, `templates/` |
| State / assets / IAB | JSON per client | `tools/state.py` |
| VAT form | ledger columns `vat_treatment, partner_country, partner_vat_id` -> Kz of USt 1 A 2026 | `tools/ustva.py` |
| Notices | notice JSON | `tools/bescheid.py` |
| Advisor review | `review.json` in the pack folder | `tools/review.py` |
| Citations | any text -> every § must exist in `references/statutes` | `tools/cite_check.py` (exit 1 on invented citation) |

If your invoices project already extracts invoice fields, map them to the JSON keys above and call `invoice_check.check(dict, kleinunternehmer=False)`. Map your expense categories to `EUR_LINES` (Anlage EÜR 2025 line + Kennzahl).

## 4. Name clashes
The skill and agent are both named `de-freelancer-tax`. Rename the folder, the `name:` in `SKILL.md`, and the agent file's `skills:` entry together if you need another name.

## 5. Running from your own server (API)
A working server is in `server/` (FastAPI + manual tool loop, Dockerfile, tests) - see `DEPLOY.md`. The notes below describe the design.

Use the Messages API with a tool runner: `SKILL.md` + playbooks as the system prompt (cache it), and expose these functions as tools: `taxcalc` (est/eur/ustva/gewst/asset), `build_pack`, `bank_import`, `invoice_check`, `cite_check`, `check_rules`, `search_statute` (grep over `references/`). Give the model no shell. One working directory per client. Default model `claude-opus-5-5`, adaptive thinking, effort set explicitly, streaming.

## 6. Keep it current
`tools/refresh.py` (dry run) / `--apply`, then `check_rules.py` and the tests. The workflow in `.github/workflows/` does this weekly on a repo's default branch and opens a PR. Yearly manual list: `references/sources.json` -> `manual_each_year`.

## 7. Privacy
Never commit real intake files, ledgers, bank exports or review packs. This repo is public. Put real data in a `private/` folder that is git-ignored (see `.gitignore`) or outside the repo.

## 8. Limits to carry over
Nothing is filed (no ELSTER). Only Anlage EÜR is mapped (2025 form). The 2025 income-tax constants are reconstructed and must be confirmed. A human Steuerberater must review every pack.
