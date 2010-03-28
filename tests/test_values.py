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

import numpy as np

from datetime import datetime
from nose import tools
from euphony.dacp.values import *

class TestNumericValues:
    @tools.raises(ValueError)
    def test_unsigned_big_value(self):
        v = UByteValue(256)

    @tools.raises(ValueError)
    def test_signed_big_value(self):
        v = ByteValue(128)

    @tools.raises(ValueError)
    def test_unsigned_small_value(self):
        v = UByteValue(-1)

    @tools.raises(ValueError)
    def test_signed_small_value(self):
        v = ByteValue(-129)

    @tools.raises(TypeError)
    def test_bad_Value(self):
        v = UByteValue('s')

    def test_serialize(self):
        tools.assert_equals(UByteValue(255).serialize(), '\xff')

    def test_deserialize(self):
        tools.assert_equals(UByteValue.deserialize('\xff').value, 255)

class TestMultiIntValues:
    def test_signed(self):
        n = MultiIntValue((-1, 1))
        tools.assert_equals(n.length, 8)
        tools.assert_equals(n.serialize(), '\xff\xff\xff\xff\x00\x00\x00\x01')
        tools.assert_equals(MultiIntValue.deserialize('\xff\xff\xff\xff\x00\x00\x00\x01').value, (-1, 1))

    def test_unsigned(self):
        n = MultiUIntValue((4294967295, 1))
        tools.assert_equals(n.length, 8)
        tools.assert_equals(n.serialize(), '\xff\xff\xff\xff\x00\x00\x00\x01')
        tools.assert_equals(MultiUIntValue.deserialize('\xff\xff\xff\xff\x00\x00\x00\x01').value, (4294967295, 1))


class TestStringValues:
    def test_ascii_serialize(self):
        tools.assert_equals(StringValue('hello').serialize(), 'hello')

    def test_unicode_serialize(self):
        tools.assert_equals(StringValue(u'привет').serialize(), '\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82')

    def test_ascii_deserialize(self):
        tools.assert_equals(StringValue.deserialize('hello').value, 'hello')

    def test_unicode_deserialize(self):
        tools.assert_equals(StringValue.deserialize('\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82').value, u'привет')

    def test_special_length(self):
        val = StringValue(u'Joe\xe2\x80\x99s Library')
        tools.assert_equals(val.length, 18)

class TestBinaryValues:
    def test_serialize(self):
        tools.assert_equals(BinaryValue('\x00\x01').serialize(), '\x00\x01')

    def test_deserialize(self):
        tools.assert_equals(BinaryValue.deserialize('\x00\x01').value, '\x00\x01')

class TestDatetimeValues:
    def test_serialize(self):
        d = DatetimeValue(datetime(2010, 3, 11, 11, 31, 58))
        tools.assert_equals(d.serialize(), '\x4b\x99\x45\x2e')

    def test_deserialize(self):
        d = DatetimeValue.deserialize('\x4b\x99\x45\x2e')
        tools.assert_equals(d.value, datetime(2010, 3, 11, 11, 31, 58))

    def test_negative(self):
        zero = datetime(1969, 12, 31, 9, 0)
        tools.assert_equals(DatetimeValue.deserialize('\xff\xff\x9d\x90').value, zero)
        tools.assert_equals(DatetimeValue(None).serialize(), '\xff\xff\x9d\x90')

class TestVersionValues:
    def test_version_serialize(self):
        tools.assert_equals(VersionValue((3,0,1,0)).serialize(), '\x00\x03\x00\x01')

    def test_version_deserialize(self):
        tools.assert_equals(VersionValue.deserialize('\x00\x03\x00\x01'), VersionValue((3,0,1,0)))

class TestContainerValues:
    def test_container_serialize(self):
        n1 = NodeValue('msup', UByteValue(1))
        n2 = NodeValue('msup', UByteValue(2))
        n3 = NodeValue('msup', UByteValue(3))
        lst = ContainerValue([n1, n2, n3])
        tools.assert_equals(lst.length, 27)
        tools.assert_equals(lst.value, [n1, n2, n3])

        bytes = 'msup\x00\x00\x00\x01\x01msup\x00\x00\x00\x01\x02msup\x00\x00\x00\x01\x03'
        tools.assert_equals(lst.serialize(), bytes)

    def test_container_deserialize(self):
        n1 = NodeValue('msup', UByteValue(1))
        n2 = NodeValue('msup', UByteValue(2))
        n3 = NodeValue('msup', UByteValue(3))

        bytes = 'msup\x00\x00\x00\x01\x01msup\x00\x00\x00\x01\x02msup\x00\x00\x00\x01\x03'
        lst = ContainerValue.deserialize(bytes)
        tools.assert_equals(lst.serialize(), bytes)
        tools.assert_equals(lst.length, 27)
        tools.assert_equals(lst.value[0], n1)
        tools.assert_equals(lst.value[1], n2)
        tools.assert_equals(lst.value[2], n3)

    def test_non_node_container(self):
        bytes = 'mlit\x00\x00\x00\x05Hellomlit\x00\x00\x00\x05World'
        lst = ContainerValue.deserialize(bytes)
        tools.assert_equals(lst.value[0], NodeValue('mlit', StringValue('Hello')))
        tools.assert_equals(lst.value[1], NodeValue('mlit', StringValue('World')))
        tools.assert_equals(lst.serialize(), bytes)

class TestNodeValues:
    def test_simple_serialize(self):
        node = NodeValue('msup', UByteValue(255))
        tools.assert_equals(node.tag, 'msup')
        tools.assert_equals(node.length, 9)
        tools.assert_equals(node.value, 255)
        tools.assert_equals(node.serialize(), 'msup\x00\x00\x00\x01\xff')

    def test_simple_deserialize(self):
        node = NodeValue.deserialize('msup\x00\x00\x00\x01\xff')
        tools.assert_equals(node.serialize(), 'msup\x00\x00\x00\x01\xff')
        tools.assert_equals(node.tag, 'msup')
        tools.assert_equals(node.length, 9)
        tools.assert_equals(node.value, 255)

    def test_interface(self):
        node = NodeValue('msrv', ContainerValue([
            NodeValue('mstt', UIntValue(200)),
            NodeValue('mlcl', ContainerValue([
                NodeValue('minm', StringValue('Bob\'s Library')),
            ])),
        ]))
        tools.assert_equals(node.mstt[0], 200)
        tools.assert_equals(node.mlcl[0].minm[0], 'Bob\'s Library')

class TestShorthand:
    def test_build_node(self):
        n1 = build_node(('msrv', [
            ('mstt', lambda: 200),
            ('mpro', '\x00\x02\x00\x06'),
            ('musr', UShortValue(64)),
            ('msed', True),
            ('msml', [
                ('msma', 71359108752128L),
                ('msma', 1102738509824L),
                ('msma', 8799319904256L),
            ]),
            ('ceWM', ''),
            ('minm', u'Joe\xe2\x80\x99s Library'),
            ('mstm', 1800),
            ('mstc', datetime(2010, 3, 12, 12, 46, 10)),
        ]))

        n2 = NodeValue('msrv', ContainerValue([
            NodeValue('mstt', UIntValue(200)),
            NodeValue('mpro', BinaryValue('\x00\x02\x00\x06')),
            NodeValue('musr', UShortValue(64)),
            NodeValue('msed', UByteValue(1)),
            NodeValue('msml', ContainerValue([
                NodeValue('msma', ULongValue(71359108752128L)),
                NodeValue('msma', ULongValue(1102738509824L)),
                NodeValue('msma', ULongValue(8799319904256L)),
            ])),
            NodeValue('ceWM', BinaryValue('')),
            NodeValue('minm', StringValue(u'Joe\xe2\x80\x99s Library')),
            NodeValue('mstm', UIntValue(1800)),
            NodeValue('mstc', DatetimeValue(datetime(2010, 3, 12, 12, 46, 10))),
        ]))

        tools.assert_equals(n1.mstt[0], 200)
        tools.assert_equals(n1.mpro[0], '\x00\x02\x00\x06')
        tools.assert_equals(n1.musr[0], 64)
        tools.assert_equals(n1.msed[0], 1)
        tools.assert_equals(n1.msml[0].msma[0], 71359108752128L)
        tools.assert_equals(n1.msml[0].msma[1], 1102738509824L)
        tools.assert_equals(n1.msml[0].msma[2], 8799319904256L)
        tools.assert_equals(n1.ceWM[0], '')
        tools.assert_equals(n1.minm[0], u'Joe\xe2\x80\x99s Library')
        tools.assert_equals(n1.mstm[0], 1800)
        tools.assert_equals(n1.mstc[0], datetime(2010, 3, 12, 12, 46, 10))

        tools.assert_equals(n1, n2)