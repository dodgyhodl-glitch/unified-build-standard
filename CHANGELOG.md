# Changelog

This repository keeps its **own** version line. Numbers here are assigned
independently and are **not comparable** with any other repository's, including
the one this content was originally copied from. There is no upstream remote and
no merges arrive from elsewhere.

The tag `baseline-2.0` marks the last commit of shared history. Everything after
it belongs to this line alone.

Two version surfaces are tracked separately, because they change for different
reasons:

| Surface | Where | Changes when |
| --- | --- | --- |
| Standard version | `BUILD_STANDARD.md` heading | the standard's text changes |
| Plugin version | `openai/plugin/.codex-plugin/plugin.json` | anything shipped in the plugin changes |

Plugin versions follow strict semver and only ever move forward — a version that
goes backwards breaks update detection for anyone who installed the plugin.

---

## Unreleased

Standard version: 2.0 · Plugin version: 2.0.1 (unchanged — nothing shipped in the
plugin changed)

- Ship the sync tooling the README previously only described: `install/` now
  carries the sync script and a systemd user timer, with its own documentation.
- Document the self-updating symlink install, including the dangling-symlink
  failure mode it introduces and how to recover from it.

## Plugin 2.0.1 — 2026-09-13

Standard version: 2.0 (text unchanged)

- Established this repository as an independent line; tagged `baseline-2.0` at
  the final shared commit.
- Rebranded all ownership metadata — LICENSE, README and both plugin manifests.
- Recorded provenance in the canonical document so this line's 2.0 is never
  mistaken for another repository's 2.0.

## Plugin 2.0.0 — baseline

Standard version: 2.0

Initial content, inherited at the point of copying. Retained as the starting
point of this line rather than renumbered, so the shared history stays readable.
