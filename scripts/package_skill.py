#!/usr/bin/env python3
"""Synchronise the canonical Unified Build Standard into every packaged skill
location, then build the distributable ZIPs.

The repository root holds the single canonical copy of each shared file. Every
other copy in the tree is derived and must never be edited directly.

Usage:
    python3 scripts/package_skill.py            # sync derived copies, then build ZIPs
    python3 scripts/package_skill.py --check    # verify only; exit 1 on any drift
    python3 scripts/package_skill.py --no-zip   # sync derived copies only

Standard library only. Compatible with Python 3.9+.
"""

import argparse
import filecmp
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The canonical reference document and the portable skill are the sources of
# truth; everything on the right-hand side is a derived copy.
CANONICAL_DOC = ROOT / "BUILD_STANDARD.md"
PORTABLE_SKILL = ROOT / "skill" / "unified-build-standard"
OPENAI_SKILL = ROOT / "openai" / "plugin" / "skills" / "unified-build-standard"
PLUGIN_DIR = ROOT / "openai" / "plugin"

# (canonical source, derived destination)
SYNC_PAIRS = [
    (CANONICAL_DOC, PORTABLE_SKILL / "references" / "BUILD_STANDARD.md"),
    (CANONICAL_DOC, OPENAI_SKILL / "references" / "BUILD_STANDARD.md"),
    (PORTABLE_SKILL / "SKILL.md", OPENAI_SKILL / "SKILL.md"),
    # Codex reads .codex-plugin/plugin.json; the root copy is the portable
    # manifest described in the current OpenAI packaging docs. Same content.
    (PLUGIN_DIR / ".codex-plugin" / "plugin.json", PLUGIN_DIR / "plugin.json"),
]

ANTHROPIC_ZIP = ROOT / "dist" / "anthropic" / "unified-build-standard.zip"
OPENAI_ZIP = ROOT / "dist" / "openai" / "unified-build-standard-plugin.zip"

# Fixed timestamp so repeated builds produce byte-identical archives.
ZIP_DATE_TIME = (2026, 9, 1, 0, 0, 0)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sync(check_only: bool) -> int:
    """Copy canonical files over their derived copies, or report drift."""
    drift = 0
    for source, dest in SYNC_PAIRS:
        if not source.exists():
            print("MISSING CANONICAL: {}".format(rel(source)), file=sys.stderr)
            drift += 1
            continue
        same = dest.exists() and filecmp.cmp(source, dest, shallow=False)
        if same:
            print("ok      {}".format(rel(dest)))
            continue
        drift += 1
        if check_only:
            reason = "differs from" if dest.exists() else "missing, expected copy of"
            print("DRIFT   {} {} {}".format(rel(dest), reason, rel(source)), file=sys.stderr)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            print("synced  {}  <- {}".format(rel(dest), rel(source)))
    return drift


def validate_frontmatter(skill_md: Path) -> int:
    """Confirm SKILL.md opens with a YAML frontmatter block carrying name and
    description. Deliberately minimal: no third-party YAML dependency."""
    errors = 0
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        print("FRONTMATTER: {} does not open with ---".format(rel(skill_md)), file=sys.stderr)
        return 1
    try:
        end = lines.index("---", 1)
    except ValueError:
        print("FRONTMATTER: {} has no closing ---".format(rel(skill_md)), file=sys.stderr)
        return 1

    fields = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            print("FRONTMATTER: {}: unparsable line {!r}".format(rel(skill_md), line), file=sys.stderr)
            errors += 1
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()

    for required in ("name", "description"):
        if not fields.get(required):
            print("FRONTMATTER: {} missing {}".format(rel(skill_md), required), file=sys.stderr)
            errors += 1
    if fields.get("name") and fields["name"] != skill_md.parent.name:
        print(
            "FRONTMATTER: {} name {!r} != directory {!r}".format(
                rel(skill_md), fields["name"], skill_md.parent.name
            ),
            file=sys.stderr,
        )
        errors += 1
    if not errors:
        print("ok      frontmatter {} (name={})".format(rel(skill_md), fields.get("name")))
    return errors


def validate_manifest(manifest: Path) -> int:
    """Check the plugin manifest against the documented Codex requirements."""
    errors = 0
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print("MANIFEST: {} is not valid JSON: {}".format(rel(manifest), exc), file=sys.stderr)
        return 1

    for field in ("name", "version", "description", "author", "interface"):
        if field not in data:
            print("MANIFEST: {} missing required field {!r}".format(rel(manifest), field), file=sys.stderr)
            errors += 1

    version = data.get("version", "")
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        print("MANIFEST: version {!r} is not strict semver".format(version), file=sys.stderr)
        errors += 1

    author = data.get("author", {})
    if isinstance(author, dict):
        for field in ("name", "email", "url"):
            if not author.get(field):
                print("MANIFEST: author.{} is required".format(field), file=sys.stderr)
                errors += 1
    else:
        print("MANIFEST: author must be an object", file=sys.stderr)
        errors += 1

    interface = data.get("interface", {})
    if isinstance(interface, dict):
        for field in ("displayName", "shortDescription"):
            if not interface.get(field):
                print("MANIFEST: interface.{} is required".format(field), file=sys.stderr)
                errors += 1
        for field in ("websiteURL", "privacyPolicyURL", "termsOfServiceURL"):
            value = interface.get(field)
            if value and not value.startswith("https://"):
                print("MANIFEST: interface.{} must be an absolute https URL".format(field), file=sys.stderr)
                errors += 1
        prompts = interface.get("defaultPrompt", [])
        if len(prompts) > 3:
            print("MANIFEST: interface.defaultPrompt allows at most 3 entries", file=sys.stderr)
            errors += 1
        for prompt in prompts:
            if len(prompt) > 128:
                print("MANIFEST: defaultPrompt entry exceeds 128 chars: {!r}".format(prompt), file=sys.stderr)
                errors += 1
    else:
        print("MANIFEST: interface must be an object", file=sys.stderr)
        errors += 1

    skills_path = data.get("skills")
    if skills_path:
        resolved = (manifest.parent.parent / skills_path).resolve()
        if not resolved.is_dir():
            print("MANIFEST: skills path {!r} does not resolve to a directory".format(skills_path), file=sys.stderr)
            errors += 1

    if not errors:
        print("ok      manifest {} (name={}, version={})".format(rel(manifest), data.get("name"), version))
    return errors


def validate() -> int:
    """Run every structural check that does not require network access."""
    errors = 0
    for skill_dir in (PORTABLE_SKILL, OPENAI_SKILL):
        skill_md = skill_dir / "SKILL.md"
        reference = skill_dir / "references" / "BUILD_STANDARD.md"
        if not skill_md.exists():
            print("MISSING: {}".format(rel(skill_md)), file=sys.stderr)
            errors += 1
            continue
        errors += validate_frontmatter(skill_md)
        if not reference.exists():
            print("MISSING: {} referenced by {}".format(rel(reference), rel(skill_md)), file=sys.stderr)
            errors += 1
        else:
            print("ok      reference present {}".format(rel(reference)))

    errors += validate_manifest(PLUGIN_DIR / ".codex-plugin" / "plugin.json")
    return errors


def write_zip(target: Path, entries) -> None:
    """Write a deterministic ZIP from (archive name, source path) pairs."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for arcname, source in sorted(entries):
            info = zipfile.ZipInfo(arcname, date_time=ZIP_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())
    print("built   {}".format(rel(target)))


def collect(base: Path, prefix: str):
    """Yield (archive name, path) for every file under base, excluding noise."""
    for path in sorted(base.rglob("*")):
        if path.is_dir() or path.name == ".DS_Store":
            continue
        yield "{}/{}".format(prefix, path.relative_to(base).as_posix()), path


def build_zips() -> None:
    write_zip(ANTHROPIC_ZIP, collect(PORTABLE_SKILL, "unified-build-standard"))
    write_zip(OPENAI_ZIP, collect(PLUGIN_DIR, "unified-build-standard"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify only; exit 1 if any derived copy has drifted")
    parser.add_argument("--no-zip", action="store_true", help="synchronise and validate without building ZIPs")
    args = parser.parse_args()

    drift = sync(check_only=args.check)
    errors = validate()

    if args.check:
        if drift or errors:
            print("\nFAILED: {} drifted file(s), {} validation error(s)".format(drift, errors), file=sys.stderr)
            return 1
        print("\nOK: all derived copies match the canonical sources and validation passed")
        return 0

    if errors:
        print("\nFAILED: {} validation error(s); ZIPs not built".format(errors), file=sys.stderr)
        return 1

    if not args.no_zip:
        build_zips()
    print("\nOK: packaging complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
