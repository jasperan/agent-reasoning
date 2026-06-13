"""Shared parsers for extracting structured signals from free-text critiques."""

import re


def parse_score(critique: str, default: float = 0.5) -> float:
    """Extract a numeric 0-1 score from a critique response.

    Looks first for an explicit ``SCORE: X.X`` marker, then falls back to any
    bare decimal in the text, and finally returns ``default`` if nothing parses.
    """
    match = re.search(r"SCORE:\s*(0?\.\d+|1\.0|1|0)", critique, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    match = re.search(r"\b(0\.\d+|1\.0)\b", critique)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    return default


def parse_feedback(critique: str) -> str:
    """Extract feedback text from a critique response.

    Returns the text following a ``FEEDBACK:`` marker if present, otherwise the
    entire critique unchanged.
    """
    match = re.search(r"FEEDBACK:\s*(.+)", critique, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return critique
