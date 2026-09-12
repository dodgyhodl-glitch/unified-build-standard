# Anthropic / Claude installation

Package: [`dist/anthropic/unified-build-standard.zip`](../dist/anthropic/unified-build-standard.zip)

The ZIP contains exactly:

```
unified-build-standard/
├── SKILL.md
└── references/
    └── BUILD_STANDARD.md
```

## 1. Upload to your Claude account

1. Open Claude → **Settings → Customize → Skills**.
2. Choose **Add** (or **Upload skill**) and select `dist/anthropic/unified-build-standard.zip`.
3. Enable **Unified Build Standard** once it appears in the list.

The skill is now attached to your account, so it is available on web, desktop and mobile without any further per-device setup.

## 2. Invoke it

Explicitly:

```
/unified-build-standard
```

Implicitly — the `description` in `SKILL.md` lets Claude select it on its own when you ask for planning, execution, review, resumption or completion of technical work.

## 3. Use it in Claude Code

Account-level skills are not synced into the CLI by default. Sync them once:

```bash
CLAUDE_CODE_SYNC_SKILLS=1 claude -p "List the skills you have available"
```

Then confirm inside an interactive session:

```
/skills
```

`unified-build-standard` should be listed.

## 4. Install it for one repository only

Commit the skill into the repository instead of installing it account-wide:

```bash
mkdir -p .claude/skills
cp -R /path/to/unified-build-standard/skill/unified-build-standard .claude/skills/
```

Anyone who clones the repository then gets the skill automatically. Use this when the standard should apply to one project rather than to everything you do.

## 5. Install it for this machine only

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/unified-build-standard/skill/unified-build-standard ~/.claude/skills/unified-build-standard
```

A symlink means `git pull` in the repository updates the installed skill immediately.

## Updating

Edit the canonical `BUILD_STANDARD.md` at the repository root, then:

```bash
python3 scripts/package_skill.py
```

Re-upload the regenerated ZIP to replace the account-level version. Symlinked CLI and repository installations pick the change up with no further action.
