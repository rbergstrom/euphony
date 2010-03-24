# coding: utf8

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
