# OpenAI / Codex + ChatGPT installation

Two independent options:

| Option | What it covers | Use when |
| --- | --- | --- |
| **Standalone skill** | Codex CLI on one machine | You only want it in the terminal |
| **Personal plugin** | ChatGPT web, desktop, mobile and Codex | You want it everywhere on your account |

Both contain the identical skill, generated from the same canonical document.

---

## Option A — standalone skill (Codex CLI)

Skills placed in `~/.agents/skills/` are picked up by Codex on this machine.

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/unified-build-standard/skill/unified-build-standard ~/.agents/skills/unified-build-standard
```

A symlink keeps the installation current with `git pull`. If your filesystem cannot use symlinks, copy instead and refresh with:

```bash
rm -rf ~/.agents/skills/unified-build-standard
cp -R /path/to/unified-build-standard/skill/unified-build-standard ~/.agents/skills/
```

Start a **new** Codex session, then confirm:

```
/skills
```

Invoke it explicitly:

```
$unified-build-standard
```

Or just describe the task — the `description` field lets Codex select it implicitly.

---

## Option B — personal plugin (ChatGPT web, desktop, mobile)

Package: [`dist/openai/unified-build-standard-plugin.zip`](../dist/openai/unified-build-standard-plugin.zip)

```
unified-build-standard/
├── .codex-plugin/
│   └── plugin.json      # manifest Codex reads
├── plugin.json          # identical portable manifest
└── skills/
    └── unified-build-standard/
        ├── SKILL.md
        └── references/
            └── BUILD_STANDARD.md
```

The plugin declares **no MCP servers, no connectors and no external tools**. It bundles a skill and its reference document, nothing else — so it needs no permissions beyond being enabled.

### Install

1. Open the **Plugins** tab in the ChatGPT plugin directory.
2. Add this plugin under your personal plugins, using the ZIP above or this repository as the source.
3. Enable it, then **start a new chat or CLI session** — bundled skills only load on session start.

In Codex CLI you can browse and install plugins from configured marketplaces with:

```
/plugins
```

### Invoke

- ChatGPT: type `@` and pick **Unified Build Standard**, or describe the task and let ChatGPT choose it.
- Codex CLI: `$unified-build-standard`, or describe the task.

Both explicit and implicit invocation are supported; nothing in the manifest restricts selection.

---

## Install for one repository only

```bash
mkdir -p .agents/skills
cp -R /path/to/unified-build-standard/skill/unified-build-standard .agents/skills/
```

Commit it, and everyone working in that repository gets the standard automatically.

---

## Updating

Edit the canonical `BUILD_STANDARD.md` at the repository root, then:

```bash
python3 scripts/package_skill.py
```

This re-synchronises every packaged copy and rebuilds both ZIPs. Bump `version` in `openai/plugin/.codex-plugin/plugin.json` (strict semver) before redistributing the plugin; the root `plugin.json` is regenerated from it automatically.

Verify before publishing:

```bash
python3 scripts/package_skill.py --check
```
