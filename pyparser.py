"""
    Parser
    ~~~~~~~

    Extension to ast that allow ast -> ipython nodebook code generation.

    :copyright: Copyright 2016 by Ralph Goestenmeier
                Based on the work of Armin Ronacher 
                https://github.com/andreif/codegen
    :license: BSD.
"""

import os
import inspect

import ast
from ast import *

BINOP_SYMBOLS = {}
BINOP_SYMBOLS[Add] = '+'
BINOP_SYMBOLS[Sub] = '-'
BINOP_SYMBOLS[Mult] = '*'
BINOP_SYMBOLS[Div] = '/'
BINOP_SYMBOLS[Mod] = '%'
BINOP_SYMBOLS[Pow] = '**'
BINOP_SYMBOLS[LShift] = '<<'
BINOP_SYMBOLS[RShift] = '>>'
BINOP_SYMBOLS[BitOr] = '|'
BINOP_SYMBOLS[BitXor] = '^'
BINOP_SYMBOLS[BitAnd] = '&'
BINOP_SYMBOLS[FloorDiv] = '//'

BOOLOP_SYMBOLS = {}
BOOLOP_SYMBOLS[And] = 'and'
BOOLOP_SYMBOLS[Or] = 'or'

CMPOP_SYMBOLS = {}
CMPOP_SYMBOLS[Eq] = '=='
CMPOP_SYMBOLS[NotEq] = '!='
CMPOP_SYMBOLS[Lt] = '<'
CMPOP_SYMBOLS[LtE] = '<='
CMPOP_SYMBOLS[Gt] = '>'
CMPOP_SYMBOLS[GtE] = '>='
CMPOP_SYMBOLS[Is] = 'is'
CMPOP_SYMBOLS[IsNot] = 'is not'
CMPOP_SYMBOLS[In] = 'in'
CMPOP_SYMBOLS[NotIn] = 'not in'

UNARYOP_SYMBOLS = {}
UNARYOP_SYMBOLS[Invert] = '~'
UNARYOP_SYMBOLS[Not] = 'not'
UNARYOP_SYMBOLS[UAdd] = '+'
UNARYOP_SYMBOLS[USub] = '-'

KEY_CLASS_COUNT = "#class"
KEY_FUNC_COUNT = "#func"

PYTHON_ELEMENTS = {
          "class_enter": 1
        , "class_exit": 1
        , "classdef": 1

        , "func_enter": 1
        , "func_exit": 1
        , "functiondef": 1

        , KEY_CLASS_COUNT: 0
        , KEY_FUNC_COUNT: 0

        , "assert" : 0
        , "alias": 0
        , "arguments": 0
        , "assign" : 1
        , "attribute": 0
        , "augassign": 0
        , "binop": 0
        , "body": 1
        , "body_or_else": 1
        , "boolop": 0
        , "break": 0
        , "bytes": 0
        , "call": 0
        , "compare": 0
        , "comprehension": 0
        , "continue": 0
        , "decorators": 0
        , "delete": 0
        , "dict": 0
        , "dictcomp": 0
        , "ellipsis": 0
        , "excepthandler": 0
        , "expr": 1
        , "extslice": 0
        , "for": 1
        , "global": 0
        , "if": 1
        , "ifexp": 0
        , "import": 1
        , "importfrom": 1
        , "lambda": 0
        , "name": 0
        , "newline": 0
        , "nonlocal": 0
        , "num": 0
        , "pass": 1
        , "print": 1
        , "raise": 0
        , "repr": 0
        , "return": 1
        , "signature": 0
        , "slice": 0
        , "starred": 0
        , "str": 0
        , "subscript": 0
        , "tryexcept": 0
        , "tryfinally": 0
        , "tuple": 0
        , "unaryop": 0
        , "visit": 0
        , "while": 1
        , "with": 1
        , "write": 0
        , "yield": 0
}

class Parser(NodeVisitor):
    """
    This visitor is able to transform a well formed syntax tree into python
    sourcecode.  For more details have a look at the docstring of the
    `node_to_source` function.
    """

    (STATE_IGNORE, STATE_ENTER, STATE_EXIT) = [ "ignore", "enter", "exit" ] # range(3)

    debuglevel = 0
    lineno = -1

    state = {}
    stack = []
    lines = {}
    result = []

    in_classdef = 0
    in_funcdef = 0

    def __init__(self, indent_with=' ' * 4, add_line_information=False, debuglevel=4):
        self.result = []
        self.state = {}
        self.stack=[]
        self.indent_with = indent_with
        self.add_line_information = add_line_information
        self.debuglevel = debuglevel
        self.indentation = 0
        self.new_lines = 0

    def debug(self, level, line=""):
        call = inspect.stack()[1][3]
        this = inspect.stack()[0][3] 

        if level <= self.debuglevel:
            print("DBG: %s" % line)

    def setstate(self, state, level=9, node=None, lineno=None, line=""):
        call = inspect.stack()[1][3]
        # this = inspect.stack()[0][3]
        key = call.replace('visit_', '').lower()
        val = PYTHON_ELEMENTS[key]

        # handle STATE_ENTER
        if state == self.STATE_ENTER:
            self.state[key] = 1

            if key == "functiondef":
                self.state["func_enter"] = 1

            if key == "classdef":
                self.state["class_enter"] = 1

        if state == self.STATE_EXIT and key == "functiondef":
            self.state["func_exit"] = 1

        if state == self.STATE_EXIT and key == "classdef":
            self.state["class_exit"] = 1

            if self.has_func_exit:
                self.state["func_exit"] = 1

        if not lineno is None:
            self.lineno = lineno
        else:
            lineno = -1
            if node is None:
                pass
            elif hasattr(node, 'lineno'):
                self.lineno = node.lineno -1

        nodetype=""
        if not node is None:
            nodetype=type(node)

        #
        self.state[KEY_CLASS_COUNT] = self.in_classdef
        self.state[KEY_FUNC_COUNT] = self.in_funcdef

        #
        flags = [key for key in self.state.keys() if PYTHON_ELEMENTS[key] == 1 or key in [ KEY_CLASS_COUNT, KEY_FUNC_COUNT ]]

        if level <= self.debuglevel:
            if  level > 8:
                _stack=','.join(self.stack)
                _flags=flags
            else:
                _stack=""
                _flags=""
            print("LOG: node=%-30s line=%-4d / %-4d s=%-6s v=%s k=%-20s f=%r stack=%s" % (
                nodetype,
                self.lineno, lineno, 
                state, val, key, 
                _flags,
                _stack
            ))

        if val == 1:
            self.lines[self.lineno] = flags

        self.debug(8, "f=%r s=%r" % (flags, state))

        # handle STATE_ENTER
        if "func_enter" in self.state and key == "body":
            del self.state["func_enter"]

        if "class_enter" in self.state and key == "body":
            del self.state["class_enter"]

        # handle STATE_EXIT
        if state == self.STATE_EXIT:
            if "func_exit" in self.state:
                del self.state["func_exit"]

                self.has_func_exit = True

            if "class_exit" in self.state:
                del self.state["class_exit"]

            if key in self.state:
                del self.state[key]

        self.debug(8, "f=%r s=%r" % (flags, state))

    def push(self):
        '''
        -
        '''
        call = inspect.stack()[1][3]
        this = inspect.stack()[0][3]
        key = call.replace('visit_', '').lower()

        self.stack.append(key)

    def pop(self):
        self.stack.pop()
        
    def write(self, line, append_newline=False):
        if self.new_lines:
            if self.result:
                self.result.append('\n' * self.new_lines)

            self.result.append(self.indent_with * self.indentation)
            self.new_lines = 0

        self.result.append(line)

        if append_newline:
            self.newline()

    def newline(self, node=None, extra=0):
        self.new_lines = max(self.new_lines, 1 + extra)
        if node is not None and self.add_line_information:
            self.write('# line: %s' % node.lineno)
            self.new_lines = 1

    def signature(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        want_comma = []

        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        padding = [None] * (len(node.args) - len(node.defaults))
        for arg, default in zip(node.args, padding + node.defaults):
            write_comma()
            self.visit(arg)
            if default is not None:
                self.write('=')
                self.visit(default)
        if node.vararg is not None:
            write_comma()
            self.write('*' + node.vararg.arg)
        if node.kwarg is not None:
            write_comma()
            self.write('**' + node.kwarg.arg)

    def decorators(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        for decorator in node.decorator_list:
            self.newline(decorator)
            self.write('@')
            self.visit(decorator)

    def visit_Assert(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('assert ')
        self.visit(node.test)
        if node.msg is not None:
            self.write(', ')
            self.visit(node.msg)

    def visit_Assign(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        for idx, target in enumerate(node.targets):
            if idx:
                self.write(', ')
            self.visit(target)
        self.write(' = ')
        self.visit(node.value)

    def visit_AugAssign(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.visit(node.target)
        self.write(' ' + BINOP_SYMBOLS[type(node.op)] + '= ')
        self.visit(node.value)

    def visit_ImportFrom(self, node):
        self.push()
        self.setstate(self.STATE_ENTER, 2, node=node)

        self.newline(node)
        self.write('from %s%s import ' % ('.' * node.level, node.module))
        for idx, item in enumerate(node.names):
            if idx:
                self.write(', ')
            self.write(item)

        self.setstate(self.STATE_EXIT, 2, node=node)
        self.pop()

    def visit_Import(self, node):
        self.push()
        self.setstate(self.STATE_ENTER, 2, node=node, line="IMPORT: ")

        self.newline(node)
        for item in node.names:
            self.write('import ')
            self.visit(item)

        self.setstate(self.STATE_EXIT, 2, node=node, line="IMPORT: DONE")
        self.pop()

    def visit_Expr(self, node):
        self.push()
        self.setstate(self.STATE_ENTER, node=node, line="EXPR: ")

        self.generic_visit(node)

        self.setstate(self.STATE_ENTER, node=node, line="EXPR: DONE")
        self.pop()

    def visit_FunctionDef(self, node):
        self.push()
        self.in_funcdef += 1
        self.setstate(self.STATE_ENTER, level=2, node=node)

        self.newline(extra=1)
        self.decorators(node)
        self.newline(node)

        self.write('def %s(' % node.name)
        self.visit(node.args)
        self.write('):')
        self.body(node.body)

        self.newline()

        self.setstate(self.STATE_EXIT, level=2, lineno=self.lineno)
        self.in_funcdef -= 1
        self.pop()
        
    def visit_ClassDef(self, node):
        self.push()
        self.in_classdef += 1
        self.setstate(self.STATE_ENTER, level=2, node=node)

        have_args = []

        def paren_or_comma():
            if have_args:
                self.write(', ')
            else:
                have_args.append(True)
                self.write('(')

        self.newline(extra=2)
        self.decorators(node)
        self.newline(node)

        self.write('class %s' % node.name)

        for base in node.bases:
            paren_or_comma()
            self.visit(base)
        
        if hasattr(node, 'keywords'):
            for keyword in node.keywords:
                paren_or_comma()
                self.write(keyword.arg + '=')
                self.visit(keyword.value)

            if not hasattr(node, 'starargs'):
                pass
            elif node.starargs is not None:
                paren_or_comma()
                self.write('*')
                self.visit(node.starargs)

            if not hasattr(node, 'kwargs'):
                pass
            elif node.kwargs is not None:
                paren_or_comma()
                self.write('**')
                self.visit(node.kwargs)

        self.write(have_args and '):' or ':')
        self.body(node.body)

        self.setstate(self.STATE_EXIT, 2, node=node, lineno=self.lineno)
        self.in_classdef -= 1
        self.pop()

    def body_or_else(self, node):
        self.push()
        self.setstate(self.STATE_ENTER, node=node)

        self.body(node.body)
        if node.orelse:
            self.newline()
            self.write('else:')
            self.body(node.orelse)

        self.setstate(self.STATE_EXIT)
        self.pop()

    def body(self, statements):
        self.push()
        self.setstate(self.STATE_ENTER)

        self.new_line = True
        self.indentation += 1

        for stmt in statements:
            self.visit(stmt)

        self.indentation -= 1

        self.setstate(self.STATE_EXIT)
        self.pop()

    def visit_If(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('if ')
        self.visit(node.test)
        self.write(':')
        self.body(node.body)
        while True:
            else_ = node.orelse
            if len(else_) == 0:
                break
            elif len(else_) == 1 and isinstance(else_[0], If):
                node = else_[0]
                self.newline()
                self.write('elif ')
                self.visit(node.test)
                self.write(':')
                self.body(node.body)
            else:
                self.newline()
                self.write('else:')
                self.body(else_)
                break

    def visit_For(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('for ')
        self.visit(node.target)
        self.write(' in ')
        self.visit(node.iter)
        self.write(':')
        self.body_or_else(node)

    def visit_While(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('while ')
        self.visit(node.test)
        self.write(':')
        self.body_or_else(node)

    def visit_With(self, node):
        self.setstate(self.STATE_ENTER, node=node)

        self.newline(node)
        self.write('with ')
        if hasattr(node, 'context_expr'):
            self.visit(node.context_expr)

        if hasattr(node, 'optional_vars'):
            if node.optional_vars is not None:
                self.write(' as ')
                self.visit(node.optional_vars)

        self.write(':')
        self.body(node.body)

        self.setstate(self.STATE_EXIT, node=node)

    def visit_Pass(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('pass')

    def visit_Print(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        # XXX: python 2.6 only
        self.newline(node)
        self.write('print ')
        want_comma = False
        if node.dest is not None:
            self.write(' >> ')
            self.visit(node.dest)
            want_comma = True
        for value in node.values:
            if want_comma:
                self.write(', ')
            self.visit(value)
            want_comma = True
        if not node.nl:
            self.write(',')

    def visit_Delete(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.debug(2, "node%r" % node)

        self.newline(node)
        self.write('del ')

        r''' IGNORE
        for idx, target in enumerate(node):
            if idx:
                self.write(', ')
            self.visit(target)
        '''
    def visit_TryExcept(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('try:')
        self.body(node.body)
        for handler in node.handlers:
            self.visit(handler)

    def visit_TryFinally(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('try:')
        self.body(node.body)
        self.newline(node)
        self.write('finally:')
        self.body(node.finalbody)

    def visit_Global(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('global ' + ', '.join(node.names))

    def visit_Nonlocal(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('nonlocal ' + ', '.join(node.names))

    def visit_Return(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        if node.value is None:
            self.write('return')
        else:
            self.write('return ')
            self.visit(node.value)

    def visit_Break(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('break')

    def visit_Continue(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('continue')

    def visit_Raise(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        # XXX: Python 2.6 / 3.0 compatibility
        self.newline(node)
        self.write('raise')
        if hasattr(node, 'exc') and node.exc is not None:
            self.write(' ')
            self.visit(node.exc)
            if node.cause is not None:
                self.write(' from ')
                self.visit(node.cause)
        elif hasattr(node, 'type') and node.type is not None:
            self.visit(node.type)
            if node.inst is not None:
                self.write(', ')
                self.visit(node.inst)
            if node.tback is not None:
                self.write(', ')
                self.visit(node.tback)

    def visit_Attribute(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.visit(node.value)
        self.write('.' + node.attr)

    def visit_Call(self, node):
        self.push()
        self.setstate(self.STATE_ENTER, 4, node=node)

        want_comma = []

        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        self.visit(node.func)
        self.write('(')
        for arg in node.args:
            write_comma()
            self.visit(arg)
        for keyword in node.keywords:
            write_comma()
            self.write(keyword.arg + '=')
            self.visit(keyword.value)

        if not hasattr(node, 'starargs'):
            pass
        elif node.starargs is not None:
            write_comma()
            self.write('*')
            self.visit(node.starargs)

        if not hasattr(node, 'kwargs'):
            pass
        elif node.kwargs is not None:
            write_comma()
            self.write('**')
            self.visit(node.kwargs)
        self.write(')')

        self.setstate(self.STATE_EXIT, node=node)
        self.pop()

    def visit_Name(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write(node.id)

    def visit_Str(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write(repr(node.s))

    def visit_Bytes(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write(repr(node.s))

    def visit_Num(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write(repr(node.n))

    def visit_Tuple(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write('(')
        idx = -1
        for idx, item in enumerate(node.elts):
            if idx:
                self.write(', ')
            self.visit(item)
        self.write(idx and ')' or ',)')

    def sequence_visit(left, right):
        def visit(self, node):
            self.setstate(self.STATE_ENTER, 4, node=node)

            self.write(left)
            for idx, item in enumerate(node.elts):
                if idx:
                    self.write(', ')
                self.visit(item)
            self.write(right)
        return visit

    visit_List = sequence_visit('[', ']')
    visit_Set = sequence_visit('{', '}')
    del sequence_visit

    def visit_Dict(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write('{')
        for idx, (key, value) in enumerate(zip(node.keys, node.values)):
            if idx:
                self.write(', ')
            self.visit(key)
            self.write(': ')
            self.visit(value)
        self.write('}')

    def visit_BinOp(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.visit(node.left)
        self.write(' %s ' % BINOP_SYMBOLS[type(node.op)])
        self.visit(node.right)

    def visit_BoolOp(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write('(')
        for idx, value in enumerate(node.values):
            if idx:
                self.write(' %s ' % BOOLOP_SYMBOLS[type(node.op)])
            self.visit(value)
        self.write(')')

    def visit_Compare(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write('(')
        self.visit(node.left)
        for op, right in zip(node.ops, node.comparators):
            self.write(' %s ' % CMPOP_SYMBOLS[type(op)])
            self.visit(right)
        self.write(')')

    def visit_UnaryOp(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write('(')
        op = UNARYOP_SYMBOLS[type(node.op)]
        self.write(op)
        if op == 'not':
            self.write(' ')
        self.visit(node.operand)
        self.write(')')

    def visit_Subscript(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.visit(node.value)
        self.write('[')
        self.visit(node.slice)
        self.write(']')

    def visit_Slice(self, node):
        self.push()
        self.setstate(self.STATE_ENTER, 4, node=node)

        if node.lower is not None:
            self.visit(node.lower)
        self.write(':')
        if node.upper is not None:
            self.visit(node.upper)
        if node.step is not None:
            self.write(':')
            if not (isinstance(node.step, Name) and node.step.id == 'None'):
                self.visit(node.step)
        
        self.pop()

    def visit_ExtSlice(self, node):
        self.setstate(self.STATE_ENTER, node=node)

        for idx, item in enumerate(node.dims):
            if idx:
                self.write(', ')
            self.visit(item)

        self.setstate(self.STATE_EXIT, node=node)

    def visit_Yield(self, node):
        self.setstate(self.STATE_ENTER, node=node)

        self.write('yield ')

        if node.value:
            self.visit(node.value)

    def visit_Lambda(self, node):
        self.setstate(self.STATE_ENTER, node=node)

        self.write('lambda ')
        self.visit(node.args)
        self.write(': ')
        self.visit(node.body)

    def visit_Ellipsis(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write('Ellipsis')

    def generator_visit(left, right):
        def visit(self, node):
            self.setstate(self.STATE_ENTER, 4, node=node)

            self.write(left)
            self.visit(node.elt)
            for comprehension in node.generators:
                self.visit(comprehension)
            self.write(right)
        return visit

    visit_ListComp = generator_visit('[', ']')
    visit_GeneratorExp = generator_visit('(', ')')
    visit_SetComp = generator_visit('{', '}')
    del generator_visit

    def visit_DictComp(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write('{')
        self.visit(node.key)
        self.write(': ')
        self.visit(node.value)
        for comprehension in node.generators:
            self.visit(comprehension)
        self.write('}')

    def visit_IfExp(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.visit(node.body)
        self.write(' if ')
        self.visit(node.test)
        self.write(' else ')
        self.visit(node.orelse)

    def visit_Starred(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write('*')
        self.visit(node.value)

    def visit_Repr(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        # XXX: python 2.6 only
        self.write('`')
        self.visit(node.value)
        self.write('`')

    
    def visit_alias(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write(node.name)
        if node.asname is not None:
            self.write(' as ' + node.asname)

    def visit_comprehension(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.write(' for ')
        self.visit(node.target)
        self.write(' in ')
        self.visit(node.iter)
        if node.ifs:
            for if_ in node.ifs:
                self.write(' if ')
                self.visit(if_)

    def visit_excepthandler(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.newline(node)
        self.write('except')
        if node.type is not None:
            self.write(' ')
            self.visit(node.type)
            if node.name is not None:
                self.write(' as ')
                self.visit(node.name)
        self.write(':')
        self.body(node.body)

    def visit_arguments(self, node):
        self.setstate(self.STATE_ENTER, 4, node=node)

        self.signature(node)

    def parse(self, code):
        self.debug(1)
        self.code = [line.rstrip() for line in code]

        tree = ast.parse(os.linesep.join(self.code))
        self.visit(tree)

    def notebook(self):
        self.debug(1)

        currCx=0
        currFx=0

        lastCx=0
        lastFx=0

        lastType="M"

        for lineno,line in enumerate(self.code):
            tags=""
            inClass="__"
            inFunc="__"
            currType="M"

            if lineno in self.lines:
                tags = self.lines[lineno]

                if line.strip() in ["'''", '"""']:
                    currType="M"
                else:
                    currType="C"

            if "class_enter" in tags:
                inClass="C+"
            elif "class_exit" in tags:
                inClass="C-"

            if "func_enter" in tags:
                inFunc="F+"
            elif "func_exit" in tags:
                inFunc="F-"

            if "class_enter" in tags:
                currCx += 1

            if "func_enter" in tags:
                currFx += 1

            if currCx > 0 or currFx > 0:
                currType="C"

            if lineno == 0:
                change = 1
            elif currCx > 0 and lastCx != 0:
                change = 0 
            elif currFx == lastFx and currType == lastType:
                change = 0
            else:
                change = 1

            yield (lineno, line, change, currType)

            if "class_exit" in tags:
                currCx -= 1

            if "func_exit" in tags:
                currFx -= 1

            lastCx = currCx
            lastFx = currFx
            lastType = currType

        yield None
