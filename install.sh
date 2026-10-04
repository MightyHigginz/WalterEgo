#!/bin/sh
# Install the tax suite into another project:  ./install.sh /path/to/your/project [--with-server] [--force]
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"; DEST="$1"; shift || true
[ -d "$DEST" ] || { echo "usage: $0 /path/to/project [--with-server] [--force]"; exit 1; }
SERVER=0; FORCE=0; for a in "$@"; do [ "$a" = "--with-server" ] && SERVER=1; [ "$a" = "--force" ] && FORCE=1; done
if [ -e "$DEST/.claude/skills/de-freelancer-tax" ] && [ $FORCE = 0 ]; then echo "already installed (use --force to update)"; exit 1; fi
mkdir -p "$DEST/.claude/skills" "$DEST/.claude/agents"
rm -rf "$DEST/.claude/skills/de-freelancer-tax"
cp -R "$SRC/.claude/skills/de-freelancer-tax" "$DEST/.claude/skills/"
cp "$SRC/.claude/agents/de-freelancer-tax.md" "$DEST/.claude/agents/"
find "$DEST/.claude/skills/de-freelancer-tax" -name __pycache__ -prune -exec rm -rf {} +
if [ $SERVER = 1 ]; then cp -R "$SRC/server" "$DEST/tax-server"; cp "$SRC/DEPLOY.md" "$DEST/TAX-DEPLOY.md"; fi
touch "$DEST/.gitignore"; for l in "private/" ".claude/skills/de-freelancer-tax/private/" "tax-server/data/" "tax-server/tokens.json"; do grep -qxF "$l" "$DEST/.gitignore" || echo "$l" >> "$DEST/.gitignore"; done
( cd "$DEST/.claude/skills/de-freelancer-tax/tools" && python3 -W ignore -m unittest 2>&1 | tail -1 && python3 check_rules.py | tail -1 )
echo "Installed. Open the project in Claude Code: skill and agent 'de-freelancer-tax' are available."
