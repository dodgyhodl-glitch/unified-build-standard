#!/usr/bin/env bash
#
# Keep the local Unified Build Standard clone in sync with GitHub.
#
# Three rules, in order of precedence:
#   1. Never destroy local work. If tracked files have uncommitted changes,
#      abort before touching the repository.
#   2. Fast-forward only. If the branch has diverged from origin, or is ahead
#      of it, log the situation and stop. Never merge, never rebase, never reset.
#   3. Never ask for credentials. The remote is public HTTPS and every
#      credential helper and terminal prompt is disabled, so an auth problem
#      fails fast instead of hanging a timer job forever.
#
# Untracked files do not abort the run: a fast-forward cannot delete them, and
# git refuses to clobber an untracked file on checkout. They are logged only.
#
# Exit codes: 0 success or already current; 1 aborted by a rule; 2 setup error.

set -uo pipefail

REPO="${UBS_REPO:-$HOME/unified-build-standard}"
BRANCH="${UBS_BRANCH:-main}"
LOG_DIR="${UBS_LOG_DIR:-$HOME/.local/state/unified-build-standard}"
LOG="$LOG_DIR/sync.log"
MAX_LOG_BYTES="${UBS_MAX_LOG_BYTES:-262144}"   # 256 KiB, then rotate; 2 files max

mkdir -p "$LOG_DIR" || { echo "cannot create $LOG_DIR" >&2; exit 2; }

# Cap the log before appending, so it can never grow without bound.
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG" 2>/dev/null || echo 0)" -gt "$MAX_LOG_BYTES" ]; then
  mv -f "$LOG" "$LOG.1"
fi

log() { printf '%s  %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >>"$LOG"; }

# Rule 3: no credential prompts, ever.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=/bin/true
export GIT_CONFIG_PARAMETERS="'credential.helper='"

# One run at a time.
exec 9>"$LOG_DIR/sync.lock"
if ! flock -n 9; then
  log "SKIP     another sync is already running"
  exit 0
fi

cd "$REPO" 2>/dev/null || { log "ERROR    repo not found at $REPO"; exit 2; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { log "ERROR    $REPO is not a git work tree"; exit 2; }

remote_url=$(git remote get-url origin 2>/dev/null || echo "")
case "$remote_url" in
  https://*) ;;
  *) log "ABORT    origin is not public HTTPS: ${remote_url:-<none>}"; exit 1 ;;
esac

current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ "$current_branch" != "$BRANCH" ]; then
  log "ABORT    on branch '$current_branch', expected '$BRANCH'; leaving it alone"
  exit 1
fi

# Rule 1: abort on uncommitted changes to tracked files.
dirty=$(git status --porcelain --untracked-files=no)
if [ -n "$dirty" ]; then
  count=$(printf '%s\n' "$dirty" | wc -l | tr -d ' ')
  log "ABORT    $count uncommitted change(s) to tracked files; refusing to sync"
  printf '%s\n' "$dirty" | sed 's/^/                            /' >>"$LOG"
  exit 1
fi

untracked=$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')
[ "$untracked" -gt 0 ] && log "NOTE     $untracked untracked file(s) present; they are left untouched"

if ! fetch_err=$(git fetch --quiet --prune origin "$BRANCH" 2>&1); then
  log "ERROR    fetch failed: ${fetch_err:-unknown error}"
  exit 2
fi

local_sha=$(git rev-parse HEAD)
remote_sha=$(git rev-parse "origin/$BRANCH")
base_sha=$(git merge-base HEAD "origin/$BRANCH")

if [ "$local_sha" = "$remote_sha" ]; then
  log "CURRENT  already at ${local_sha:0:7}"
  exit 0
fi

# Rule 2: fast-forward only.
if [ "$local_sha" != "$base_sha" ]; then
  if [ "$remote_sha" = "$base_sha" ]; then
    ahead=$(git rev-list --count "origin/$BRANCH..HEAD")
    log "STOP     local is $ahead commit(s) ahead of origin/$BRANCH; nothing to fast-forward"
  else
    ahead=$(git rev-list --count "origin/$BRANCH..HEAD")
    behind=$(git rev-list --count "HEAD..origin/$BRANCH")
    log "STOP     branch has DIVERGED from origin/$BRANCH (ahead $ahead, behind $behind); manual resolution required"
  fi
  exit 1
fi

behind=$(git rev-list --count "HEAD..origin/$BRANCH")
if merge_err=$(git merge --ff-only "origin/$BRANCH" 2>&1); then
  log "UPDATED  fast-forwarded $behind commit(s): ${local_sha:0:7} -> ${remote_sha:0:7}"
  exit 0
else
  log "ERROR    fast-forward failed: ${merge_err:-unknown error}"
  exit 2
fi
