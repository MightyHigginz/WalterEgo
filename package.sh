#!/bin/sh
# Build dist/de-tax-suite.zip (skill + agent + workflow + INTEGRATION.md), no private data.
set -e
cd "$(dirname "$0")"; mkdir -p dist; rm -f dist/de-tax-suite.zip
zip -rq dist/de-tax-suite.zip INTEGRATION.md install.sh DEPLOY.md AUDIT.md Dockerfile docker-compose.yml .env.example server .claude/skills/de-freelancer-tax .claude/agents/de-freelancer-tax.md .github/workflows/refresh-tax-sources.yml \
  -x 'server/data/*' 'server/tokens.json' '*/__pycache__/*' '*/private/*' '*.pyc'
echo "dist/de-tax-suite.zip: $(du -h dist/de-tax-suite.zip | cut -f1)"
