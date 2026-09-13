# Automatic syncing

GitHub is the source of truth; a local clone is a disposable cache of it. These
files keep that clone current without supervision.

| File | Purpose |
| --- | --- |
| `unified-build-standard-sync.sh` | the sync itself — portable, no scheduler assumptions |
| `systemd/unified-build-standard-sync.service` | runs the script once |
| `systemd/unified-build-standard-sync.timer` | every 12 hours, and 5 minutes after boot |

If the skill is installed by symlink, a successful sync updates every local
installation at once — nothing else to run.

## The three rules

The script is deliberately conservative. It would rather do nothing than do
something surprising.

1. **Never destroy local work.** If tracked files have uncommitted changes, it
   aborts before touching the repository.
2. **Fast-forward only.** If the branch has diverged from origin, or is ahead of
   it, it logs the situation and stops. It never merges, rebases or resets.
3. **Never ask for credentials.** The remote is public HTTPS, and every
   credential helper and terminal prompt is disabled — so an authentication
   problem fails fast instead of hanging a scheduled job indefinitely.

Untracked files do not abort a run: a fast-forward cannot delete them, and git
refuses to clobber an untracked file on checkout. They are logged only, so a
stray editor file never wedges the timer.

**Exit codes:** `0` synced or already current · `1` stopped by a rule ·
`2` setup or network error. The systemd unit sets `SuccessExitStatus=1`, because
a refusal is a correct outcome, not a failure.

## Install (Linux, systemd)

```bash
install -Dm755 -t ~/.local/bin/           install/unified-build-standard-sync.sh
install -Dm644 -t ~/.config/systemd/user/ install/systemd/unified-build-standard-sync.service
install -Dm644 -t ~/.config/systemd/user/ install/systemd/unified-build-standard-sync.timer
systemctl --user daemon-reload
systemctl --user enable --now unified-build-standard-sync.timer
```

Confirm it is scheduled:

```bash
systemctl --user list-timers unified-build-standard-sync.timer
```

The units reference `%h`, so they need no editing for a different username.

## Logs

`~/.local/state/unified-build-standard/sync.log`, rotated at 256 KiB and capped
at two files, so it cannot grow without bound.

```bash
tail -f ~/.local/state/unified-build-standard/sync.log
```

If the clone ever looks stale, read this file first. The most common cause is
rule 1 or rule 2 doing its job — `ABORT` means uncommitted changes, `STOP` means
the branch is ahead of or diverged from origin. Both are logged with detail.

## Configuration

Every path is overridable, so the script suits a non-default layout without
editing:

| Variable | Default |
| --- | --- |
| `UBS_REPO` | `$HOME/unified-build-standard` |
| `UBS_BRANCH` | `main` |
| `UBS_LOG_DIR` | `$HOME/.local/state/unified-build-standard` |
| `UBS_MAX_LOG_BYTES` | `262144` |

## Other platforms

The script itself is portable — it assumes only bash, git and coreutils. Only
the scheduler is Linux-specific. On macOS, drive it with a `launchd` agent; on
Windows, Task Scheduler under WSL or Git Bash. Whatever the scheduler, the three
rules above are what matter.

## Verifying a change

Both failure paths are worth testing directly rather than trusting:

```bash
# Rule 1 — must abort, and leave the edit untouched
echo "" >> README.md
~/.local/bin/unified-build-standard-sync.sh; echo "exit=$?"   # expect 1
git checkout -- README.md

# Rule 2 — must fast-forward cleanly back to origin
git reset --hard HEAD~1
~/.local/bin/unified-build-standard-sync.sh; echo "exit=$?"   # expect 0
git rev-parse --short HEAD                                     # back at origin/main
```
