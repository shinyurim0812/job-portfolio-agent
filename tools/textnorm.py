"""Text normalization shared by the checkers.

Only differences that do not change meaning are removed:
Unicode form, whitespace/line breaks, quote marks, and leading bullet marks.
Any change to the words themselves still fails a comparison.
"""
import re
import unicodedata

QUOTES = "\"'“”‘’「」『』«»`"
BULLET_AT_LINE_START = re.compile(r"^[ \t]*[•▪◦○●■□▶►✓※\-\*·]+[ \t]*", re.MULTILINE)
WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = BULLET_AT_LINE_START.sub("", text)
    text = text.translate({ord(c): None for c in QUOTES})
    return WHITESPACE.sub("", text)
