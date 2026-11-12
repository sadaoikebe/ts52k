import re
def parse(text):
    tok=re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')
    stack=[[]]
    for m in tok.finditer(text):
        t=m.group(0)
        if t=='(': stack.append([])
        elif t==')':
            x=stack.pop(); stack[-1].append(x)
        elif t[0]=='"': stack[-1].append(t[1:-1])
        else: stack[-1].append(t)
    return stack[0][0]
def find(n,k): return [c for c in n if isinstance(c,list) and c and c[0]==k]
def first(n,k):
    r=find(n,k); return r[0] if r else None
