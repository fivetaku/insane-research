#!/usr/bin/env bash
# First-run setup for insane-research. Idempotent, non-blocking.
#   setup.sh            -> env checks + update-notifier hook (once); prints STAR_ASK
#                          on stdout iff the user has not yet decided about starring.
#   setup.sh star yes   -> star both repos (own + marketplace) and record the decision.
#   setup.sh star no    -> record "declined"; star nothing.
# The star question itself is asked by the command flow (AskUserQuestion is Claude-only,
# it cannot be issued from bash) — this script never stars without an explicit decision.
set -uo pipefail

PLUGIN="insane-research"
OWN_REPO="fivetaku/insane-research"
HUB_REPO="fivetaku/gptaku_plugins"

CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
HERE="$(cd "$(dirname "$0")" && pwd)"
MARKER_DIR="$HOME/.gptaku-setup"
SETUP_MARKER="$MARKER_DIR/$PLUGIN.json"
STAR_MARKER="$MARKER_DIR/$PLUGIN.star.json"
mkdir -p "$MARKER_DIR"

# --- star: record the user's decision (and star if yes). Called after the question. ---
if [ "${1:-}" = "star" ]; then
  DECISION="${2:-no}"
  ts=$(date +%s 2>/dev/null || echo 0)
  printf '{"star_decision":"%s","plugin":"%s","ts":%s}\n' "$DECISION" "$PLUGIN" "$ts" > "$STAR_MARKER"
  if [ "$DECISION" = "yes" ] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    for repo in "$OWN_REPO" "$HUB_REPO"; do
      gh api "user/starred/$repo" >/dev/null 2>&1 || gh api -X PUT "user/starred/$repo" >/dev/null 2>&1 || true
    done
  fi
  exit 0
fi

# --- first-run env checks + update-notifier hook (silent, once per machine) ---
if [ ! -f "$SETUP_MARKER" ]; then
  HAVE_NODE=0; command -v node >/dev/null 2>&1 && HAVE_NODE=1
  if [ "$HAVE_NODE" = "1" ]; then
    SCRIPTS_DIR="$CONFIG_DIR/scripts"
    mkdir -p "$SCRIPTS_DIR"
    [ -f "$HERE/gptaku-update-check.cjs" ] && cp -f "$HERE/gptaku-update-check.cjs" "$SCRIPTS_DIR/gptaku-update-check.cjs" 2>/dev/null
    CLAUDE_CONFIG_DIR="$CONFIG_DIR" node -e '
      const fs=require("fs"),path=require("path"),os=require("os");
      const cfg=process.env.CLAUDE_CONFIG_DIR||path.join(os.homedir(),".claude");
      const p=path.join(cfg,"settings.json");
      let d={}; try{d=JSON.parse(fs.readFileSync(p,"utf8"))}catch{}
      d.hooks=d.hooks||{};
      const ss=d.hooks.SessionStart=Array.isArray(d.hooks.SessionStart)?d.hooks.SessionStart:[];
      const has=ss.some(e=>((e&&e.hooks)||[]).some(h=>String((h&&h.command)||"").includes("gptaku-update-check")));
      if(!has){
        const cmd="node "+JSON.stringify(path.join(cfg,"scripts","gptaku-update-check.cjs"));
        ss.push({matcher:"*",hooks:[{type:"command",command:cmd,timeout:5}]});
        try{fs.writeFileSync(p,JSON.stringify(d,null,2))}catch{}
      }
    ' >/dev/null 2>&1 || true
  fi
  ts=$(date +%s 2>/dev/null || echo 0)
  printf '{"setup":true,"plugin":"%s","ts":%s}\n' "$PLUGIN" "$ts" > "$SETUP_MARKER"
fi

# --- star prompt signal: ask exactly once, until a decision is recorded ---
[ -f "$STAR_MARKER" ] || echo "STAR_ASK"
exit 0
