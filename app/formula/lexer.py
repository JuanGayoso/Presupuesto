"""Tokenizer for the formula language.

Only arithmetic, comparisons and whitelisted function calls are recognised —
there is no way to reach arbitrary Python from a formula string.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


class FormulaSyntaxError(Exception):
    pass


TOKEN_SPEC = [
    ("NUMBER", r"\d+(\.\d+)?"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("LE", r"<="),
    ("GE", r">="),
    ("EQ", r"=="),
    ("NE", r"!="),
    ("LT", r"<"),
    ("GT", r">"),
    ("PLUS", r"\+"),
    ("MINUS", r"-"),
    ("STAR", r"\*"),
    ("SLASH", r"/"),
    ("PERCENT", r"%"),
    ("CARET", r"\^"),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("COMMA", r","),
    ("SKIP", r"[ \t]+"),
]
MASTER_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))


@dataclass
class Token:
    type: str
    value: str
    pos: int


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    length = len(text)
    while pos < length:
        m = MASTER_RE.match(text, pos)
        if not m:
            raise FormulaSyntaxError(f"Carácter inesperado en la posición {pos}: '{text[pos]}'")
        kind = m.lastgroup
        value = m.group()
        if kind != "SKIP":
            tokens.append(Token(kind, value, pos))
        pos = m.end()
    tokens.append(Token("EOF", "", length))
    return tokens
