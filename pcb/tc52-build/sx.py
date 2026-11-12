"""Minimal S-expression reader/writer for KiCad files (keeps quoted strings distinct)."""
import re


class Q(str):
    """A quoted string token."""


_tok = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')


def parse(text):
    stack = [[]]
    for m in _tok.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append([])
        elif t == ')':
            x = stack.pop()
            stack[-1].append(x)
        elif t[0] == '"':
            stack[-1].append(Q(t[1:-1]))
        else:
            stack[-1].append(t)
    return stack[0][0]


def dump(x, depth=0):
    if isinstance(x, Q):
        return '"' + x + '"'
    if isinstance(x, str):
        return x
    flat = '(' + ' '.join(dump(c, depth + 1) for c in x) + ')'
    if depth >= 2 or len(flat) < 100:
        return flat
    ind = '\n' + '\t' * (depth + 1)
    out = '(' + dump(x[0])
    for c in x[1:]:
        if isinstance(c, list):
            out += ind + dump(c, depth + 1)
        else:
            out += ' ' + dump(c)
    return out + '\n' + '\t' * depth + ')'


def find(x, name):
    return [c for c in x if isinstance(c, list) and c and c[0] == name]


def first(x, name):
    r = find(x, name)
    return r[0] if r else None


def prop(sym, key):
    for p in find(sym, 'property'):
        if p[1] == key:
            return p[2]
    return None
