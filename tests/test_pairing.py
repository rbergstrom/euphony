# coding: utf8

from nose import tools
from euphony.pairing import generate_code

class TestPairingCode:
    def test_code_gen(self):
        code = generate_code('3861', 'D06F5B3577C7A001')
        tools.assert_equals(len(code), 32)
        tools.assert_equals(code, '0BD8D9D49E66BB17F8BD0367A4E42058')