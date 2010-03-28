# coding: utf8

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

from euphony import util
from nose import tools

class TestUtil:
    def test_sort_headers(self):
        names = ['The Ford', 'Agrajag', 'Trillian', 'Arthur', 'Zaphod', 'Marvin', '2 Zaphods']
        headers = util.build_sort_headers(names)
        print headers
        tools.assert_equals(len(headers), 6)
        tools.assert_equals(headers[0], (ord('A'), 0, 2))
        tools.assert_equals(headers[1], (ord('F'), 2, 1))
        tools.assert_equals(headers[2], (ord('M'), 3, 1))
        tools.assert_equals(headers[3], (ord('T'), 4, 1))
        tools.assert_equals(headers[4], (ord('Z'), 5, 1))
        tools.assert_equals(headers[5], (ord('0'), 6, 1))

    def test_get_initial(self):
        tools.assert_equals(util.get_initial('The Heart of Gold'), 'H')
        tools.assert_equals(util.get_initial('"Magrathea"'), 'M')
        tools.assert_equals(util.get_initial('42 is the Answer'), util.SORT_LAST)
