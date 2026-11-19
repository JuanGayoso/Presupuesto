"""Recursive-descent parser for the formula language.

Grammar (top to bottom precedence):
    comparison := additive (( '<' | '<=' | '>' | '>=' | '==' | '!=' ) additive)?
    additive   := multiplicative (('+' | '-') multiplicative)*
    multiplicative := unary (('*' | '/' | '%') unary)*
    unary      := ('+' | '-') unary | power
    power      := primary ('^' unary)?
    primary    := NUMBER | IDENT | IDENT '(' args ')' | '(' comparison ')'
    args       := comparison (',' comparison)*
"""
from __future__ import annotations

from .ast_nodes import BinOp, Call, Name, Node, Num, UnaryOp
from .lexer import FormulaSyntaxError, Token, tokenize

COMPARISON_OPS = {"LT", "LE", "GT", "GE", "EQ", "NE"}
OP_SYMBOL = {
    "LT": "<", "LE": "<=", "GT": ">", "GE": ">=", "EQ": "==", "NE": "!=",
    "PLUS": "+", "MINUS": "-", "STAR": "*", "SLASH": "/", "PERCENT": "%", "CARET": "^",
}


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0

    @property
    def cur(self) -> Token:
        return self.tokens[self.i]

    def advance(self) -> Token:
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def expect(self, type_: str) -> Token:
        if self.cur.type != type_:
            raise FormulaSyntaxError(f"Se esperaba '{type_}' pero se encontró '{self.cur.value or 'fin de la fórmula'}' en la posición {self.cur.pos}")
        return self.advance()

    def parse(self) -> Node:
        node = self.comparison()
        if self.cur.type != "EOF":
            raise FormulaSyntaxError(f"Token inesperado '{self.cur.value}' en la posición {self.cur.pos}")
        return node

    def comparison(self) -> Node:
        node = self.additive()
        if self.cur.type in COMPARISON_OPS:
            op = self.advance()
            right = self.additive()
            node = BinOp(OP_SYMBOL[op.type], node, right)
        return node

    def additive(self) -> Node:
        node = self.multiplicative()
        while self.cur.type in ("PLUS", "MINUS"):
            op = self.advance()
            right = self.multiplicative()
            node = BinOp(OP_SYMBOL[op.type], node, right)
        return node

    def multiplicative(self) -> Node:
        node = self.unary()
        while self.cur.type in ("STAR", "SLASH", "PERCENT"):
            op = self.advance()
            right = self.unary()
            node = BinOp(OP_SYMBOL[op.type], node, right)
        return node

    def unary(self) -> Node:
        if self.cur.type in ("PLUS", "MINUS"):
            op = self.advance()
            operand = self.unary()
            return UnaryOp(OP_SYMBOL[op.type], operand)
        return self.power()

    def power(self) -> Node:
        node = self.primary()
        if self.cur.type == "CARET":
            self.advance()
            right = self.unary()
            node = BinOp("^", node, right)
        return node

    def primary(self) -> Node:
        tok = self.cur
        if tok.type == "NUMBER":
            self.advance()
            return Num(float(tok.value))
        if tok.type == "IDENT":
            self.advance()
            if self.cur.type == "LPAREN":
                self.advance()
                args = []
                if self.cur.type != "RPAREN":
                    args.append(self.comparison())
                    while self.cur.type == "COMMA":
                        self.advance()
                        args.append(self.comparison())
                self.expect("RPAREN")
                return Call(tok.value, args)
            return Name(tok.value)
        if tok.type == "LPAREN":
            self.advance()
            node = self.comparison()
            self.expect("RPAREN")
            return node
        raise FormulaSyntaxError(f"Token inesperado '{tok.value or 'fin de la fórmula'}' en la posición {tok.pos}")


def parse_formula(text: str) -> Node:
    tokens = tokenize(text)
    return Parser(tokens).parse()
