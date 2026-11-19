from __future__ import annotations

from dataclasses import dataclass, field


class Node:
    pass


@dataclass
class Num(Node):
    value: float


@dataclass
class Name(Node):
    ident: str


@dataclass
class BinOp(Node):
    op: str
    left: Node
    right: Node


@dataclass
class UnaryOp(Node):
    op: str
    operand: Node


@dataclass
class Call(Node):
    name: str
    args: list = field(default_factory=list)
