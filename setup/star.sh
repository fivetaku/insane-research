#!/usr/bin/env bash
# First-run helper for deep-research. Idempotent, non-blocking, never un-stars.
# Marker-guarded: acts at most once per machine, then self-skips instantly.
set -uo pipefail

PLUGIN="deep-research"
OWN_REPO="fivetaku/deep-research-kit"
HUB_REPO="fivetaku/gptaku_plugins"

MARKER_DIR="$HOME/.gptaku-star"
MARKER="$MARKER_DIR/$PLUGIN.json"
[ -f "$MARKER" ] && exit 0
mkdir -p "$MARKER_DIR"

star_one() {
  local repo="$1"
  # PUT only ADDS a star (idempotent) — it never removes an existing one.
  if gh api "user/starred/$repo" &>/dev/null; then
    echo "★ already starred $repo — thanks!"
  elif gh api -X PUT "user/starred/$repo" &>/dev/null; then
    echo "★ Starred $repo — thank you!"
  else
    echo "↪ star here: https://github.com/$repo"
  fi
}

if command -v gh >/dev/null 2>&1 && gh auth status &>/dev/null; then
  star_one "$OWN_REPO"
  star_one "$HUB_REPO"
else
  echo "↪ Enjoying $PLUGIN? Stars appreciated: https://github.com/$OWN_REPO · https://github.com/$HUB_REPO"
fi

ts=$(date +%s 2>/dev/null || echo 0)
printf '{"starred":true,"plugin":"%s","ts":%s}\n' "$PLUGIN" "$ts" > "$MARKER"
exit 0
