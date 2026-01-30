#!/usr/bin/env python3
"""
Remove obsolete (`#~`) entries from PO files under `translations/*/LC_MESSAGES/`.

Usage:
  FORCE_CLEAN=true python3 .development/clean_obsolete.py
or
  python3 .development/clean_obsolete.py

If `FORCE_CLEAN` is set to a truthy value, obsolete entries are removed
without prompting. Otherwise the script asks per-file.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRANSLATIONS = REPO_ROOT / "translations"

try:
    import polib
except ImportError:
    print("polib is required for clean_obsolete. Install with: pip install polib", file=sys.stderr)
    sys.exit(0)


def find_po_files():
    if not TRANSLATIONS.exists():
        return []
    for lang_dir in TRANSLATIONS.iterdir():
        po = lang_dir / "LC_MESSAGES" / "messages.po"
        if po.exists():
            yield po


def remove_obsolete(po_path: Path, force: bool) -> int:
    pofile = polib.pofile(str(po_path))
    obsolete = [e for e in pofile if e.obsolete]
    if not obsolete:
        return 0
    if not force:
        ans = input(f"  Remove {len(obsolete)} obsolete entries from {po_path}? [y/N] ")
        if not ans.lower().startswith("y"):
            print(f"  -> skipped {po_path}")
            return 0
    for entry in obsolete:
        try:
            pofile.remove(entry)
        except Exception:
            # if removal by object fails, try removing by msgid/context
            try:
                pofile.remove(entry.msgid)
            except Exception:
                pass
    pofile.save()
    print(f"  -> cleaned {po_path}")
    return len(obsolete)


def main():
    force = os.environ.get("FORCE_CLEAN", "false").lower() in ("1", "true", "yes")
    total = 0
    for po in find_po_files():
        try:
            total += remove_obsolete(po, force)
        except Exception as exc:
            print(f"Error cleaning {po}: {exc}", file=sys.stderr)
    if total == 0:
        print("No obsolete entries removed.")
    else:
        print(f"Removed {total} obsolete entries total.")


if __name__ == "__main__":
    main()
