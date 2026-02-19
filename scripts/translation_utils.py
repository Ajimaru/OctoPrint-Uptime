#!/usr/bin/env python3
"""
Shared utilities for translation file management.

This module provides common functions used by translation management scripts.
"""

from pathlib import Path
from typing import Iterator


def iter_po_files(root: Path) -> Iterator[Path]:
    """
    Iterate over all messages.po files in the translations directory.

    Yields paths to messages.po files found under root/*/LC_MESSAGES/.
    If root does not exist, returns immediately without yielding.

    Args:
        root (Path): The root directory to search for PO files.

    Yields:
        Path: Paths to existing messages.po files.
    """
    if not root.is_dir():
        return
    for lang_dir in root.iterdir():
        po = lang_dir / "LC_MESSAGES" / "messages.po"
        if po.exists():
            yield po
