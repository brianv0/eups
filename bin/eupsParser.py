"""A simple recursive descent parser for logical expressions"""

import re

class Parser(object):
    """Evaluate a logical expression, returning a Bool.  The grammar is:

        expr : term
               expr || term          (or  is also accepted)
               expr && term          (and is also accepted)

        term : prim == prim
               prim != prim
               prim < prim
               prim <= prim
               prim > prim
               prim >= prim

	prim : int
               string
               name
               ( expr )

names are declared using Parser.declare()
        """
    def __init__(self, exprStr):
        self._tokens = re.split(r"([\w.+]+|\s+|==|!=|<=|>=|[()<>])", exprStr)
        self._tokens = filter(lambda p: p and not re.search(r"^\s*$", p), self._tokens)
        
        self._symbols = {}
        self._caseSensitive = False

    def define(self, key, value):
        """Define a symbol, which may be substituted using _lookup"""
        
        self._symbols[key] = value

    def _lookup(self, key):
        """Attempt to lookup a key in the symbol table"""
        key0 = key
        
        if not self._caseSensitive:
            key = key.lower()

        try:
            return self._symbols[key]
        except KeyError:
            return key0        

    def _peek(self):
        """Return the next terminal symbol, but don't pop it off the lookahead stack"""
        
        if not self._tokens:
            return "EOF"
        else:
            tok = self._lookup(self._tokens[0])
            try:
                tok = int(tok)
            except ValueError:
                pass

            return tok

    def _push(self, tok):
        """Push a token back onto the lookahead stack"""

        if tok != "EOF":
            self._tokens = [tok] + self._tokens
    
    def _next(self):
        """Return the next terminal symbol, popping it off the lookahead stack"""
        
        tok = self._peek()
        if tok != "EOF":
            self._tokens.pop(0)

        return tok
    
    def eval(self):
        """Evaluate the logical expression, returning a Bool"""
        val = self._expr()              # n.b. may not have consumed all tokens as || and && short circuit

        if val == "EOF":
            return False
        else:
            return val

    def _expr(self):
        lhs = self._term()

        while True:
            op = self._next()

            if op == "||" or op == "or":
                lhs = lhs or self._term()
            elif op == "&&" or op == "and":
                lhs = lhs and self._term()
            else:
                self._push(op)
                return lhs

    def _term(self):
        lhs = self._prim()
        op = self._next()

        if op == "EOF":
            return lhs

        if op == "==":
            return lhs == self._prim()
        elif op == "!=":
            return lhs != self._prim()
        elif op == "<":
            return lhs < self._prim()
        elif op == "<=":
            return lhs <= self._prim()
        elif op == ">":
            return lhs > self._prim()
        elif op == ">=":
            return lhs >= self._prim()
        else:
            self._push(op)
            return lhs

    def _prim(self):
        next = self._peek()

        if next == "(":
            self._next()

            term = self._expr()
            
            next = self._next()
            if next != ")":
                raise RuntimeError, ("Saw next = \"%s\" in prim" % next)

            return term

        return self._next()
