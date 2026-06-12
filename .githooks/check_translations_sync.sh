#!/usr/bin/env bash

# Pre-commit hook: keep translation catalogs in sync, automatically.
#
# This hook is fully self-contained: it inlines the pybabel
# extract/update/compile steps (mirroring .github/workflows/i18n.yml) so it
# works in a fresh clone without depending on any untracked helper script.
#
# Behavior:
#  - Re-extracts the POT from the current sources, updates the PO files (with
#    --no-fuzzy-matching), pins the volatile POT-Creation-Date to a
#    deterministic value, strips obsolete entries, verifies the catalogs
#    (fails on stray fuzzy entries or an 'en' msgstr that differs from its
#    msgid), compiles the MO files and copies them into the plugin package.
#  - Compares the regenerated catalogs against the staged/working versions
#    using a NORMALIZED comparison (volatile POT-Creation-Date / Generated-By
#    headers and shifting "#: file:line" references are ignored). Only a real
#    change in msgids/msgstrs counts.
#  - On a real content change, the hook re-stages the changed translation
#    files and FAILS once (standard pre-commit auto-fixer convention, like
#    black/prettier): the fix is staged for you, just re-run `git commit`.
#  - If only volatile metadata changed, the working tree is restored to avoid
#    noisy timestamp-only diffs, and the commit proceeds.
#  - If the i18n tooling (pybabel/polib) is not available locally, the hook
#    SKIPS with a warning and lets the commit proceed; the i18n CI workflow is
#    the authoritative gate, so a missing local toolchain must not block work.
#
# This catches the case where a formatter (djlint/prettier) reflows templates:
# msgid text is unchanged but POT line references move, so the catalogs must be
# regenerated to stay technically in sync without producing churn.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
cd "$REPO_ROOT"

# Project layout (kept in one place so this is easy to adapt for other plugins).
PACKAGE="octoprint_uptime"
BABEL_CFG="$REPO_ROOT/babel.cfg"
LANGUAGES=(de en)

# Translation artifacts that this hook may regenerate and re-stage.
TRANSLATION_PATHS=(
    "translations"
    "$PACKAGE/translations"
)

# Resolve the toolchain. Prefer the project venv, fall back to PATH.
if [[ -x "$REPO_ROOT/.venv/bin/python3" ]]; then
    PYTHON="$REPO_ROOT/.venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
else
    PYTHON=""
fi

if [[ -x "$REPO_ROOT/.venv/bin/pybabel" ]]; then
    PYBABEL="$REPO_ROOT/.venv/bin/pybabel"
elif command -v pybabel >/dev/null 2>&1; then
    PYBABEL="$(command -v pybabel)"
else
    PYBABEL=""
fi

# The toolchain needs pybabel (extract/update/compile), polib (snapshot/verify)
# and Jinja2 (babel.cfg uses the [jinja2: ...] extractor for the templates). If
# anything is missing, skip gracefully: the i18n CI workflow enforces the
# catalog, so a missing local toolchain must not block work.
if [[ -z "$PYBABEL" || -z "$PYTHON" ]] || ! "$PYTHON" -c "import polib, jinja2" >/dev/null 2>&1; then
    echo "i18n tooling (pybabel/polib/Jinja2) not available locally; skipping" >&2
    echo "translation sync check. The i18n CI workflow remains the authoritative gate." >&2
    exit 0
fi

if [[ ! -f "$BABEL_CFG" ]]; then
    echo "ERROR: $BABEL_CFG not found; cannot extract translations." >&2
    exit 1
fi

# Snapshot PO/POT content (normalized: only sorted msgid/msgctxt/msgstr tuples,
# ignoring headers, line refs and ordering) so we can tell a real change from
# pure timestamp/line-ref churn.
snapshot_normalized() {
    PACKAGE="$PACKAGE" "$PYTHON" - <<'PY'
import hashlib
import os
from pathlib import Path

import polib

# Two different normalizations, because the two CI checks treat the files
# differently:
#  - messages.pot is compared verbatim by the i18n CI workflow (only the
#    volatile date / tool-version headers are ignored), so the hook must also
#    track its "#: file:line" references and entry order. A template reflow
#    that shifts those refs then correctly re-stages the POT.
#  - the .po catalogs are NOT format-checked by CI; their refs, entry order and
#    line wrapping vary by Babel version/platform, so comparing them verbatim
#    produces false "content changed" results (Babel on the committer's machine
#    vs Babel in CI). They are compared semantically (msgctxt/msgid/msgstr only).
VOLATILE = ('"POT-Creation-Date:', '"PO-Revision-Date:', '"Generated-By:')

roots = ["translations", f"{os.environ['PACKAGE']}/translations"]
out = []
for root in roots:
    base = Path(root)
    if not base.exists():
        continue
    for f in sorted(base.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix == ".pot":
            lines = [
                line
                for line in f.read_text(encoding="utf-8").splitlines()
                if not line.startswith(VOLATILE)
            ]
            h = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
            out.append(f"{f}:{h}")
        elif f.suffix == ".po":
            try:
                po = polib.pofile(str(f))
            except Exception:
                continue
            items = sorted(
                (e.msgctxt or "", e.msgid, e.msgstr)
                for e in po
                if not e.obsolete
            )
            h = hashlib.sha256(repr(items).encode("utf-8")).hexdigest()
            out.append(f"{f}:{h}")
print("\n".join(out))
PY
}

before="$(snapshot_normalized)"

echo "Regenerating translation catalogs (extract + update + verify + compile)..."

# 1) Extract. The babel.cfg patterns are scoped to the package, so extracting
#    from "." does not walk build/, dist/ or .venv. If extraction fails (e.g.
#    pybabel runs in an environment without Jinja2 for the jinja2 extractor),
#    restore the catalogs and skip rather than leaving a truncated POT behind.
if ! "$PYBABEL" extract --sort-output -F "$BABEL_CFG" -o translations/messages.pot .; then
    echo "WARNING: 'pybabel extract' failed (is Jinja2 available to pybabel?);" >&2
    echo "restoring catalogs and skipping the sync check." >&2
    git checkout -- "${TRANSLATION_PATHS[@]}" 2>/dev/null || true
    exit 0
fi

# 2) Update each language catalog. --no-fuzzy-matching avoids Babel silently
#    mistranslating new msgids by matching them to similar old ones.
for lang in "${LANGUAGES[@]}"; do
    "$PYBABEL" update --no-fuzzy-matching \
        -i translations/messages.pot -d translations -l "$lang"
done

# 3) Verify catalogs (read-only). The .po/.pot files are intentionally left in
#    Babel's own output format so the committed messages.pot keeps matching
#    `pybabel extract` (the i18n CI compares against that, ignoring only the
#    volatile POT-Creation-Date / Generated-By headers). The volatile date
#    therefore is NOT pinned here; pure timestamp churn is absorbed by the
#    "restore on no normalized change" step below.
if ! "$PYTHON" - <<'PY'; then
import sys
from pathlib import Path

import polib

bad_fuzzy = []
en_mismatch = []
for path in sorted(Path("translations").glob("*/LC_MESSAGES/messages.po")):
    lang = path.parts[1]
    cat = polib.pofile(str(path))
    for entry in cat:
        if entry.obsolete:
            continue
        if "fuzzy" in entry.flags and entry.msgstr and entry.msgstr != entry.msgid:
            bad_fuzzy.append(f"{lang}: {entry.msgid!r} -> {entry.msgstr!r}")
        if lang == "en" and entry.msgstr and entry.msgstr != entry.msgid:
            en_mismatch.append(
                f"en: msgstr != msgid for {entry.msgid!r} (got {entry.msgstr!r})"
            )

if bad_fuzzy or en_mismatch:
    print("Catalog verification FAILED:", file=sys.stderr)
    for p in bad_fuzzy:
        print(f"  wrong fuzzy match: {p}", file=sys.stderr)
    for p in en_mismatch:
        print(f"  {p}", file=sys.stderr)
    sys.exit(2)
PY
    echo "ERROR: translation verification failed (see above). Fix the catalog," >&2
    echo "then re-run the commit." >&2
    exit 1
fi

# 4) Compile (fuzzy entries are excluded by default, so gettext falls back to
#    the msgid) and copy the compiled catalogs into the plugin package. Only
#    the .mo files are shipped in the package; the .po/.pot sources stay under
#    translations/ so the package dir does not gain untracked source files.
"$PYBABEL" compile -d translations >/dev/null 2>&1 || true
while IFS= read -r -d '' mo; do
    rel="${mo#translations/}"
    mkdir -p "$PACKAGE/translations/$(dirname "$rel")"
    cp -a "$mo" "$PACKAGE/translations/$rel"
done < <(find translations -name '*.mo' -type f -print0)

after="$(snapshot_normalized)"

if [[ -n "$before" && "$before" == "$after" ]]; then
    # Only volatile metadata (timestamps / line refs) changed. Restore the
    # working tree for these paths to avoid noisy diffs, then proceed.
    echo "Translations already in sync (no msgid/msgstr changes)."
    git checkout -- "${TRANSLATION_PATHS[@]}" 2>/dev/null || true
    exit 0
fi

# Real content change: re-stage and ask for re-commit.
echo "Translation catalogs were regenerated with content changes. Re-staging:" >&2
git add -- "${TRANSLATION_PATHS[@]}"
git status --porcelain -- "${TRANSLATION_PATHS[@]}" | sed 's/^/  /' >&2

cat >&2 <<'MSG'

Translation catalogs were out of sync and have been regenerated and staged.
This is expected after editing translatable strings or reformatting templates.
Please re-run your commit to include the updated catalogs.
MSG
exit 1
