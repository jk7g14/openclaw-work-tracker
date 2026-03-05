#!/bin/bash
set -e

SKILL_DIR="$HOME/.openclaw/workspace/skills/work-tracker"

echo "📦 Installing work-tracker skill..."

mkdir -p "$SKILL_DIR/scripts"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cp "$SCRIPT_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
cp "$SCRIPT_DIR/scripts/calc_hours.py" "$SKILL_DIR/scripts/calc_hours.py"
chmod +x "$SKILL_DIR/scripts/calc_hours.py"

echo "✅ Installed to $SKILL_DIR"
echo ""
echo "Restart the gateway:"
echo "  openclaw gateway restart"
