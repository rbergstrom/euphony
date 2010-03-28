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

def apply_parameter(parameter, collection):
    try:
        result = PARAMETER_REGEX.match(parameter).groupdict()

        if tuple(collection)[0].get_property(result['property']) is None:
            return collection

        value = urllib.unquote_plus(result['value'])
        try:
            value = int(value)
        except ValueError:
            try:
                value = int(value, 16)
            except ValueError:
                pass

        cmpfunc = lambda x, y: x == y

        try:
            if value[0] == value[-1] == '*':
                cmpfunc = lambda x, y: x in y
            elif value[0] == '*':
                cmpfunc = lambda x, y: y.endswith(x)
            elif value[-1] == '*':
                cmpfunc = lambda x, y: y.startswith(x)

            value = value.strip('*')
        except TypeError:
            pass

        if result['operator'] == TOKEN_EQUAL:
            return frozenset([x for x in collection if cmpfunc(value, x.get_property(result['property']))])
        elif result['operator'] == TOKEN_NOTEQUAL:
            return frozenset([x for x in collection if not cmpfunc(value, x.get_property(result['property']))])
        else:
            raise QuerySyntaxError('Invalid operator: %r' % result['operator'])
    except AttributeError, e:
        raise QuerySyntaxError('Unable to apply parameter: %r - %s' % (parameter, e))

def apply_operator(op, left, right):
    if op == TOKEN_AND:
        return left & right
    elif op == TOKEN_OR:
        return left | right
    else:
        raise QuerySyntaxError('Invalid operator: %r' % op)

def handle_group(lexer, collection):
    result = frozenset()

    while True:
        token = lexer.get_token()
        if token == TOKEN_GROUP_END:
            return result
        elif token == TOKEN_GROUP_START:
            result = handle_group(lexer, collection)
        elif token.startswith(TOKEN_QUOTE):
            result = apply_parameter(token, collection)
        elif token in (TOKEN_AND, TOKEN_OR):
            next_token = lexer.get_token()
            if next_token == TOKEN_GROUP_START:
                result = apply_operator(token, result, handle_group(lexer, collection))
            elif next_token.startswith(TOKEN_QUOTE):
                result = apply_operator(token, result, apply_parameter(next_token, collection))
            else:
                raise QuerySyntaxError('Operators must preceed either a group or parameter token')
        else:
            raise QuerySyntaxError('Unknown or invalid token in group: %r' % token)



def apply_query(query, collection):
    collection = frozenset(collection)
    lexer = shlex.shlex(StringIO.StringIO(query.replace(' ', '+')))

    token = lexer.get_token()
    if token == TOKEN_GROUP_START:
        return handle_group(lexer, collection)
    elif token.startswith(TOKEN_QUOTE):
        return apply_parameter(token, collection)
    else:
        raise QuerySyntaxError('Invalid query syntax')
