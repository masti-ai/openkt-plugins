#!/usr/bin/env bash
# Sync the vendored copy of masti-ai/openfield — the Deepwork Labs / OpenKT
# design system (tokens, art, loading, app shell). One source of truth for every
# surface in this repo; consumers never copy upstream files by hand.
#
# What it does:
#   1. Clone masti-ai/openfield at the pinned commit (from openfield.lock).
#   2. Mirror every tracked upstream file into shared/vendor/openfield/.
#   3. Propagate the foundation assets into the consuming plugins (currently the
#      openkt-demos interactive-demo skill), renamed to that skill's asset names.
#
# Usage:
#   ./sync-openfield.sh            # reproduce the vendored tree at the pinned commit
#   ./sync-openfield.sh --update   # re-pin to the current tip of the tracked ref
#
# The pin lives in openfield.lock (repo + ref + commit). Editing it by hand is
# discouraged — run with --update to move the pin and refresh the lock.
set -euo pipefail

VENDOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$VENDOR_DIR/../.." && pwd)"
LOCK="$VENDOR_DIR/openfield.lock"
DEST="$VENDOR_DIR/openfield"

# --- read the pin (single source of truth) ---------------------------------
read_lock() { grep -E "^$1=" "$LOCK" | head -1 | cut -d= -f2-; }
REPO="$(read_lock repo)"
REF="$(read_lock ref)"
COMMIT="$(read_lock commit)"
[ -n "$REPO" ] || { echo "openfield.lock: missing repo" >&2; exit 1; }

UPDATE=0
[ "${1:-}" = "--update" ] && UPDATE=1

# --- where each vendored foundation file lands in a consuming plugin --------
# Format: "<path under shared/vendor/openfield>=<path under repo root>"
# The interactive-demo skill keeps its own asset names; map upstream -> skill.
CONSUMERS=(
  "tokens/mix.css=claude-code/openkt-demos/skills/interactive-demo/assets/openkt-pages.css"
  "art/_art.js=claude-code/openkt-demos/skills/interactive-demo/assets/openkt-art.js"
  "loading/loading.js=claude-code/openkt-demos/skills/interactive-demo/assets/openkt-loading.js"
)

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "→ cloning $REPO (ref: $REF)"
git clone --quiet "$REPO" "$TMP/openfield"
cd "$TMP/openfield"

if [ "$UPDATE" -eq 1 ]; then
  git checkout --quiet "$REF"
  COMMIT="$(git rev-parse HEAD)"
  echo "→ updating pin to $COMMIT"
else
  git checkout --quiet "$COMMIT"
fi

# --- mirror all tracked files into the vendor dir --------------------------
rm -rf "$DEST"
mkdir -p "$DEST"
for f in $(git ls-files); do
  mkdir -p "$DEST/$(dirname "$f")"
  cp -f "$f" "$DEST/$f"
done
echo "→ vendored $(git ls-files | wc -l | tr -d ' ') files into shared/vendor/openfield/"

# --- propagate foundation assets into consumers ----------------------------
for pair in "${CONSUMERS[@]}"; do
  src="${pair%%=*}"; dst="${pair#*=}"
  if [ -f "$DEST/$src" ] && [ -d "$(dirname "$REPO_ROOT/$dst")" ]; then
    cp -f "$DEST/$src" "$REPO_ROOT/$dst"
    echo "  ↳ $src → $dst"
  fi
done

# --- write the lock --------------------------------------------------------
cat > "$LOCK" <<EOF
# openfield vendor lock — managed by shared/vendor/sync-openfield.sh
# Do not edit by hand; run the sync script to update the pin.
repo=$REPO
ref=$REF
commit=$COMMIT
EOF

echo "✓ openfield synced at $COMMIT"
