# The MIT License
#
# Copyright (c) 2010 Ryan Bergstrom
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import shlex
import re
import StringIO
import urllib

__all__ = ['QuerySyntaxError', 'apply_query']

TOKEN_GROUP_START = '('
TOKEN_GROUP_END = ')'
TOKEN_QUOTE = '\''
TOKEN_AND = '+'
TOKEN_OR = ','
TOKEN_EQUAL = ':'
TOKEN_NOTEQUAL = '!:'

PARAMETER_REGEX = re.compile(r'(?u)\'(?P<property>.+?)(?P<operator>!?:)(?P<value>.*)\'')

class QuerySyntaxError(Exception):
    pass

class IndexQuery(object):
    def __init__(self, collection, index):
        self.collection = collection
        self.index = index

    def __eq__(self, other):
        try:
            return frozenset(self.collection.indexes[self.index][other])
        except KeyError:
            return self.collection.ids

    def __ne__(self, other):
        try:
            return frozenset(self.collection.ids - self.collection.indexes[self.index][other])
        except KeyError:
            return self.collection.ids

class Expression(object):
    def __call__(self, *args, **kwargs):
        raise NotImplementedError()

class UnaryExpression(Expression):
    def __init__(self, value):
        self.value = value

class PropertyExpression(UnaryExpression):
    def __call__(self, *args, **kwargs):
        return IndexQuery(args[0], self.value)

    def __str__(self):
        return str(self.value)

class ConstantExpression(UnaryExpression):
    def __call__(self, *args, **kwargs):
        return self.value

    def __str__(self):
        return str(self.value)

class BinaryExpression(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class AndExpression(BinaryExpression):
    def __call__(self, *args, **kwargs):
        return self.left(*args, **kwargs) & self.right(*args, **kwargs)

    def __str__(self):
        return "(%s+%s)" % (self.left, self.right)

class OrExpression(BinaryExpression):
    def __call__(self, *args, **kwargs):
        return self.left(*args, **kwargs) | self.right(*args, **kwargs)

    def __str__(self):
        return "(%s,%s)" % (self.left, self.right)

class EqualsExpression(BinaryExpression):
    def __call__(self, *args, **kwargs):
        return self.left(*args, **kwargs) == self.right(*args, **kwargs)

    def __str__(self):
        return "'%s:%s'" % (self.left, self.right)

class NotEqualsExpression(BinaryExpression):
    def __call__(self, *args, **kwargs):
        return self.left(*args, **kwargs) != self.right(*args, **kwargs)

    def __str__(self):
        return "'%s!:%s'" % (self.left, self.right)

def handle_expression(expression_token):
    result = PARAMETER_REGEX.match(expression_token).groupdict()

    value = urllib.unquote_plus(result['value'])
    try:
        value = int(value)
    except ValueError:
        try:
            value = int(value, 16)
        except ValueError:
            pass

    left = PropertyExpression(result['property'])
    right = ConstantExpression(value)

    if result['operator'] == TOKEN_EQUAL:
        return EqualsExpression(left, right)
    elif result['operator'] == TOKEN_NOTEQUAL:
        return NotEqualsExpression(left, right)
    else:
        raise QuerySyntaxError('Invalid operator in expression: %r' % expression_token)


def handle_group(lexer):
    stack = []

    while True:
        token = lexer.get_token()
        if token == TOKEN_GROUP_END or token == '':
            return stack.pop()
        elif token == TOKEN_GROUP_START:
            stack.append(handle_group(lexer))
        elif token.startswith(TOKEN_QUOTE):
            stack.append(handle_expression(token))
        elif token in (TOKEN_AND, TOKEN_OR):
            next_token = lexer.get_token()
            right = None
            if next_token == TOKEN_GROUP_START:
                right = handle_group(lexer)
            elif next_token.startswith(TOKEN_QUOTE):
                right = handle_expression(next_token)
            else:
                raise QuerySyntaxError('Operators must preceed either a group or expression token')
            if token == TOKEN_AND:
                stack.append(AndExpression(stack.pop(), right))
            elif token == TOKEN_OR:
                stack.append(OrExpression(stack.pop(), right))
        else:
            raise QuerySyntaxError('Unknown or invalid token: %r' % token)

def parse_query_string(querystring):
    return handle_group(shlex.shlex(StringIO.StringIO(querystring.replace(' ', '+'))))

