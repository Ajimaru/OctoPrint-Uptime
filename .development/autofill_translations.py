#!/usr/bin/env python3
"""
Autofill missing translations using Argos Translate.

This script scans `translations/*/LC_MESSAGES/*.po` and fills entries with
empty `msgstr` using Argos Translate if a suitable model is installed.

Behavior:
- Skips if `argostranslate` is not installed or no model for the language is
  available.
- Marks auto-filled entries with the `fuzzy` flag and a comment.

Usage: python3 .development/autofill_translations.py
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRANSLATIONS_DIR = REPO_ROOT / "translations"

try:
    import polib
except Exception:
    print("polib not installed. Install with: pip install polib", file=sys.stderr)
    sys.exit(0)

try:
    import argostranslate.package
    import argostranslate.translate
except Exception:
    print("argostranslate not available; skipping autofill (pip install argostranslate)")
    sys.exit(0)


def get_target_languages():
    if not TRANSLATIONS_DIR.exists():
        return []
    langs = []
    for child in TRANSLATIONS_DIR.iterdir():
        if (child / "LC_MESSAGES" / "messages.po").exists():
            langs.append(child.name)
    return langs


def has_model(from_code: str, to_code: str) -> bool:
    try:
        installed = argostranslate.translate.get_installed_languages()
        has_from = next((inst for inst in installed if inst.code == from_code), None)
        has_to = next((inst for inst in installed if inst.code == to_code), None)
        return has_from is not None and has_to is not None
    except Exception:
        return False


def translate_text(text: str, from_code: str, to_code: str) -> str:
    try:
        return argostranslate.translate.translate(text, from_code, to_code)
    except Exception:
        return ""


def autofill_language(lang: str, source_lang: str = "en"):
    po_path = TRANSLATIONS_DIR / lang / "LC_MESSAGES" / "messages.po"
    if not po_path.exists():
        return 0
    if not has_model(source_lang, lang):
        print(f"No Argos model for {source_lang}->{lang}; skipping {po_path}")
        return 0

    po = polib.pofile(str(po_path))
    changed = 0
    for entry in po:
        if not entry.msgstr or entry.msgstr.strip() == "":
            src = entry.msgid
            tr = translate_text(src, source_lang, lang)
            if tr:
                entry.msgstr = tr
                # mark for review
                if "fuzzy" not in entry.flags:
                    entry.flags.append("fuzzy")
                # add a short comment
                entry.comment = (
                    entry.comment + "\n" if entry.comment else ""
                ) + "Auto-translated by argostranslate"
                changed += 1
    if changed > 0:
        po.save()
        print(f"Autofilled {changed} entries in {po_path}")
    else:
        print(f"No entries to autofill in {po_path}")
    return changed


def main():
    # Source language is assumed English; you can make this configurable later.
    source_lang = os.environ.get("AUTOFILL_SOURCE_LANG", "en")
    langs = get_target_languages()
    total = 0
    for lang in langs:
        if lang == source_lang:
            continue
        total += autofill_language(lang, source_lang)
    if total == 0:
        print("No autofill operations performed.")


if __name__ == "__main__":
    main()
