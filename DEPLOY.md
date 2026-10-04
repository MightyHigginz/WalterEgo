# Running the tax suite on your own server

The server wraps the skill in an HTTP API: your clients talk to it, it talks to the Claude API, and the model can only call the 24 functions in `server/tools.py` (no shell, no access outside the client's own folder).

```
client / your suite --HTTPS--> reverse proxy (TLS) --> uvicorn app:app --> Claude API (api.anthropic.com)
                                                        |-> server/tools.py -> .claude/skills/de-freelancer-tax/tools/*.py
                                                        '-> DATA_ROOT/<client_id>/{inbox,work,packs,state,conversations}
```

## What was tested here, and what was not
| Tested (26 tests + manual run) | NOT tested - do these once on your machine |
| :--- | :--- |
| tool dispatcher, sandbox against `..`, absolute paths and symlinks | a real call to the Claude API (`python3 smoke.py`, a few cents) |
| agent loop with a fake model and with the real SDK on a mocked transport (request shape, beta header, thinking-block round-trip) | `docker build` / compose (no Docker daemon in my environment) |
| citation guard, refusal, turn cap, token budget | TLS/reverse proxy, backups, your firewall |
| API auth, client isolation, advisor-only sign-off, upload and download rules, uvicorn boot | load and concurrency |

## 1. Prepare
1. Server with Docker (or Python 3.11+ for the no-Docker route below). Encrypted disk.
2. Create a **dedicated API key** in the Anthropic Console for this service and set a **spend limit**. Never commit it.
3. `cp .env.example .env`, put the key in `.env`, `chmod 600 .env`.
4. Clone this repo (or unzip `dist/de-tax-suite.zip` plus the `server/` folder, `Dockerfile`, `docker-compose.yml`).

## 2. Start (Docker)
```sh
mkdir -p runtime/data runtime/config && sudo chown -R 10001 runtime
docker compose up -d --build
curl -s localhost:8080/healthz          # {"ok":true,"sources_refreshed":"...","model":"claude-opus-5-5"}
```
No Docker: `python3 -m venv .venv && . .venv/bin/activate && pip install -r server/requirements.txt` then
`cd server && TAX_DATA_ROOT=/srv/tax/data TAX_TOKENS_FILE=/srv/tax/tokens.json uvicorn app:app --host 127.0.0.1 --port 8080 --no-access-log` (run it under systemd as an unprivileged user).

## 3. Users and tokens
```sh
docker compose exec tax python3 make_token.py client alice client-alice     # a client: may only use client-alice
docker compose exec tax python3 make_token.py advisor stb-meier client-alice  # the Steuerberater: review + sign-off for that client
docker compose exec tax python3 make_token.py admin ops                       # all clients
```
The token is printed once; only its hash is stored (`tokens.json`, mode 600). Client ids: 3-40 chars `a-z0-9_-`. Replace this with SSO/OIDC before you serve many people.

## 4. API
| Call | Who | What |
| :--- | :--- | :--- |
| `PUT /v1/clients/{id}/files/{name}` (raw body, .csv/.json/.txt/.md/.xlsx, max 5 MB) | client, admin | upload a bank export or receipt data to `inbox/` |
| `POST /v1/clients/{id}/messages` `{"message": "...", "conversation_id": "..."}` | client, admin | chat; returns answer, status, tools used, token usage |
| `GET /v1/clients/{id}/packs/{pack}/{file}` | client, advisor, admin | download pack files (whitelist: review-pack.md, eur-lines.csv, advisor-workbook.xlsx, datev-entwurf.csv, ...) |
| `GET /v1/clients/{id}/packs/{pack}/review` | same | review checklist |
| `POST .../review/{item}` `{"status","comment"}` and `POST .../signoff` | advisor, admin | advisor workspace; the model cannot do either |

Example:
```sh
curl -X PUT https://tax.example.com/v1/clients/client-alice/files/bank.csv -H "Authorization: Bearer $TOKEN" --data-binary @bank.csv
curl -X POST https://tax.example.com/v1/clients/client-alice/messages -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
     -d '{"message":"Import inbox/bank.csv into work/ledger.csv and show me the lines you could not categorise."}'
```

## 5. TLS and exposure
Bind to localhost and put a reverse proxy in front, e.g. Caddy: `tax.example.com { reverse_proxy 127.0.0.1:8080 }` (automatic HTTPS). Allow only 443 from outside. Add IP allow-lists or a VPN if the users are few. Request bodies are not logged by the app; keep proxy logs free of bodies too.

## 6. Keep the law current
- `cd .claude/skills/de-freelancer-tax/tools && python3 refresh.py` (dry run) weekly; `--apply` after you reviewed the diff; then `python3 check_rules.py && python3 -m unittest` and restart the service. The GitHub workflow does the same and opens a pull request if the repo runs on GitHub.
- `/healthz` shows when the sources were last refreshed; every pack carries the date and warns after 45 days.

## 7. Cost and safety controls (all in `.env`)
`TAX_EFFORT` (high default; `medium` is cheaper), `TAX_MAX_TURNS` (tool steps per request), a token cap per request (600k, in `agent.py`), 30 requests/minute per token. The static prompt and tool list are cached, so repeated requests are cheaper. A citation guard re-prompts the model when it cites a paragraph that does not exist and warns the user if it still does.

## 8. Data protection and professional rules (your responsibility)
- Client data = tax IDs, income, bank data. Sign the data processing agreement with Anthropic, document the legal basis, tell clients that a US AI provider processes their data, set a retention and deletion routine (`runtime/data/<client>/`), and encrypt backups.
- Only you or your advisor's firm may use it for your own affairs; offering tax advice to others for a fee is restricted to authorised persons (StBerG §§ 2, 3, 5).
- Nothing is filed. The advisor signs off a pack in the API; any later change to the pack voids the sign-off.

## 9. Known limits
No token streaming to the client (the answer arrives when the loop ends); one node with file storage (no database); tokens instead of SSO; DATEV output is a draft; only Anlage EÜR and the USt 1 A advance return are mapped; the 2025 income-tax constants are unconfirmed. See `AUDIT.md` for the full list.
