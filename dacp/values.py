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

import struct
import time

from datetime import datetime

import tags

__all__ = [
    'UByteValue', 'ByteValue','UShortValue', 'ShortValue',
    'UIntValue', 'IntValue', 'ULongValue', 'LongValue',
    'BinaryValue', 'ContainerValue', 'DatetimeValue',
    'MultiIntValue', 'MultiUIntValue', 'NodeValue',
    'StringValue', 'VersionValue',

    'UnknownTagError', 'InvalidValueError',

    'build_node'
]

class UnknownTagError(ValueError):
    pass

class InvalidValueError(ValueError):
    pass

class Value(object):
    """
    Generic value type.
    """

    value = None
    length = 0

    def __eq__(self, other):
        try:
            return self.value == other.value
        except AttributeError:
            return self.value == other

    def __ne__(self, other):
        try:
            return self.value != other.value
        except AttributeError:
            return self.value != other

    def __len__(self):
        return self.length

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return unicode(self.value)

    def serialize(self):
        raise NotImplementedError()

    @classmethod
    def deserialize(cls, bytes):
        raise NotImplementedError()

    def pprint(self):
        return unicode(self.value)

class NumericType(type):
    """
    Metaclass for numeric types.
    """
    _format_codes = {
        1: { False: '>B', True: '>b'},
        2: { False: '>H', True: '>h'},
        4: { False: '>L', True: '>l'},
        8: { False: '>Q', True: '>q'},
    }

    def __new__(cls, name, bases, attrs):
        signed = attrs.pop('signed', False)
        length = attrs.get('length', 4)

        if signed == True:
            attrs['min_value'] = - 1 * (1 << (length * 8 - 1))
            attrs['max_value'] = (1 << (length * 8 - 1)) - 1
        else:
            attrs['min_value'] = 0
            attrs['max_value'] = (1 << length * 8) - 1

        attrs['format_code'] = cls._format_codes[length][signed]

        return super(NumericType, cls).__new__(cls, name, bases, attrs)

class NumericValue(Value):
    """
    Generic numeric value type, providing serialization.
    """
    __metaclass__ = NumericType

    def __init__(self, value):
        try:
            self.value = int(value)
        except Exception:
            raise TypeError('%s requires a numeric value' % self.__class__.__name__)
        if self.value < self.min_value or self.value > self.max_value:
            raise ValueError('%s requires %d <= value <= %d' % (
                self.__class__.__name__, self.min_value, self.max_value
            ))

    def __int__(self):
        return self.value

    def serialize(self):
        return struct.pack(self.format_code, self.value)

    @classmethod
    def deserialize(cls, bytes):
        return cls(struct.unpack_from(cls.format_code, bytes)[0])

    def pprint(self):
        hexval = struct.unpack(self.format_code.upper(), self.serialize())[0]
        return ('0x%%0%dX == %%d' % (2*self.length)) % (hexval, self.value)

class UByteValue(NumericValue):
    """
    8-bit unsigned integer value
    """
    length = 1
    signed = False

class ByteValue(NumericValue):
    """
    8-bit signed integer value
    """
    length = 1
    signed = True

class UShortValue(NumericValue):
    """
    16-bit unsigned integer value
    """
    length = 2
    signed = False

class ShortValue(NumericValue):
    """
    16-bit signed integer value
    """
    length = 2
    signed = True

class UIntValue(NumericValue):
    """
    32-bit unsigned integer value
    """
    length = 4
    signed = False

class IntValue(NumericValue):
    """
    32-bit signed integer value
    """
    length = 4
    signed = True

class ULongValue(NumericValue):
    """
    64-bit unsigned integer value
    """
    length = 8
    signed = False

class LongValue(NumericValue):
    """
    64-bit signed integer value
    """
    length = 8
    signed = True

# TODO: refactor into a MultiNumericValue

class MultiIntValue(Value):
    """
    Multiple concatenated 32-bit integers
    """
    def __init__(self, value):
        self.value = value
        self.length = len(value) * 4

    def serialize(self):
        return struct.pack('>%dl' % (self.length / 4), *self.value)

    @classmethod
    def deserialize(cls, bytes):
        values = struct.unpack_from('>%dl' % (len(bytes) / 4), bytes)
        return cls(values)

    def pprint(self):
        return u'(%s) == %s' % (', '.join(['%X' % x for x in self.value]), self.value)

class MultiUIntValue(Value):
    """
    Multiple concatenated unsigned 32-bit integers
    """
    def __init__(self, value):
        self.value = value
        self.length = len(value) * 4

    def serialize(self):
        return struct.pack('>%dL' % (self.length / 4), *self.value)

    @classmethod
    def deserialize(cls, bytes):
        values = struct.unpack_from('>%dL' % (len(bytes) / 4), bytes)
        return cls(values)

    def pprint(self):
        return u'(%s) == %s' % (', '.join(['0x%X' % x for x in self.value]), self.value)

class DatetimeValue(Value):
    """
    Datetime value (standard UNIX format)
    """
    def __init__(self, value):
        self.value = value
        self.length = 4

    def serialize(self):
        if self.value is None:
            return '\xff\xff\x9d\x90'
        else:
            return struct.pack('>l', int(time.mktime(self.value.timetuple())))

    @classmethod
    def deserialize(cls, bytes):
        val = struct.unpack_from('>l', bytes)[0]
        return cls(datetime.fromtimestamp(val))

class VersionValue(Value):
    """
    Dotted version number (i.e. 3.0.2.0)
    """
    def __init__(self, value):
        self.value = value
        self.length = 4

    def serialize(self):
        val = (self.value[1], self.value[0], self.value[3], self.value[2])
        return struct.pack('4B', *val)

    @classmethod
    def deserialize(cls, bytes):
        val = struct.unpack_from('4B', bytes)
        return cls((val[1], val[0], val[3], val[2]))

    def pprint(self):
        return '%d.%d.%d.%d' % self.value

class StringValue(Value):
    """
    Unicode string value
    """
    def __init__(self, value, codec='utf-8'):
        self.codec = codec
        self.value = unicode(value)
        self.length = len(self.serialize())

    def serialize(self):
        return self.value.encode(self.codec)

    @classmethod
    def deserialize(cls, bytes, codec='utf-8'):
        return cls(bytes.decode(codec))

    def __str__(self):
        return "'%s'" % self.serialize()

    def __unicode__(self):
        return u"'%s'" % self.value

class BinaryValue(Value):
    """
    Raw binary value (for unknown types)
    """
    def __init__(self, value):
        self.value = value
        self.length = len(self.value)

    def serialize(self):
        return self.value

    @classmethod
    def deserialize(cls, bytes):
        return cls(bytes)

    def pprint(self):
        return repr(self.value)

class ContainerValue(Value):
    """
    Container type, holding either a list of nodes, or a single string
    """
    def __init__(self, value):
        self.value = value
        if isinstance(self.value, StringValue):
            self.length = self.value.length
        else:
            self.length = sum([x.length for x in self.value])

    def serialize(self):
        if isinstance(self.value, StringValue):
            return self.value.serialize()
        else:
            return ''.join([x.serialize() for x in self.value])

    @classmethod
    def deserialize(cls, bytes):
        pos = 0
        values = []
        while pos < len(bytes):
            try:
                val = NodeValue.deserialize(bytes[pos:])
            except InvalidValueError:
                return cls(StringValue.deserialize(bytes[pos:]))
            pos += val.length
            values.append(val)
        return cls(values)

    def pprint(self, depth=0):
        sep = (' ' * depth * 4)
        if isinstance(self.value, StringValue):
            return sep + unicode(self.value) + '\n'
        else:
            return unicode(sep + sep.join([x.pprint(depth) for x in self.value]))

    def __iter__(self):
        return self.value.__iter__()

    def __contains__(self, key):
        for i in self.value:
            if i.tag == key:
                return True
        return False

    def __str__(self):
        return '[' + ', '.join([str(x) for x in self.value]) + ']'

    def __unicode__(self):
        return u'[' + ', '.join([unicode(x) for x in self.value]) + ']'


class NodeValue(Value):
    """
    DACP Node value
    """
    def __init__(self, tag, value):
        self.tag = tag
        self.value = value
        self.length = self.value.length + 8

    def __getattr__(self, name):
        if isinstance(self.value, ContainerValue):
            try:
                vals = []
                for x in [item for item in self.value if item.tag == name]:
                    if isinstance(x.value, (ContainerValue, NodeValue)):
                        vals.append(x)
                    else:
                        vals.append(x.value.value)
                return vals
            except AttributeError:
                pass

        raise AttributeError(name)

    def __eq__(self, other):
        try:
            return (self.tag == other.tag) and (self.value == other.value)
        except AttributeError:
            return False

    def __ne__(self, other):
        try:
            return (self.tag != other.tag) or (self.value != other.value)
        except AttributeError:
            return True

    def __str__(self):
        return '<%s value="%s">' % (self.tag, str(self.value))

    def __unicode__(self):
        return u'<%s value="%s">' % (self.tag, unicode(self.value))

    def serialize(self):
        data = self.value.serialize()
        return struct.pack('>4sl', self.tag, len(data)) + data

    @classmethod
    def deserialize(cls, bytes):
        if (len(bytes)) < 8:
            raise InvalidValueError('Not enough data to read tag header')
        (tag, size) = struct.unpack_from('>4sl', bytes)
        data = bytes[8 : 8 + size]
        if len(data) != size:
            raise InvalidValueError('Not enough data to deserialize \'%s\' (%d/%d bytes)' % (tag, len(data), size))
        try:
            tagtype = globals()[tags.TAGS[tag][1]]
        except KeyError:
            tagtype = BinaryValue

        data = tagtype.deserialize(data)
        return cls(tag, data)

    def pprint(self, depth=0):
        from StringIO import StringIO
        try:
            tagdesc = tags.TAGS[self.tag][0]
            if tagdesc:
                tagname = u'%s (%s)' % (self.tag, tagdesc)
            else:
                tagname = self.tag
        except KeyError:
            tagname = self.tag
        out = StringIO()

        if isinstance(self.value, ContainerValue):
            depth += 1
            out.write(u'%s --+\n%s' % (tagname, self.value.pprint(depth)))
        else:
            out.write(u'%s = %s\n' % (tagname, self.value.pprint()))
        return unicode(out.getvalue())

def build_node(pair):
    """
    Builds a NodeValue from a set of (tag, value) pair tuples.
    """

    (tag, value) = pair

    if callable(value):
        value = value()

    try:
        tagtype = globals()[tags.TAGS[tag][1]]

        if tagtype == ContainerValue:
            if isinstance(value, list):
                value = [build_node(x) for x in value]
            else:
                value = StringValue(value)
        elif tagtype == NodeValue:
            value = build_node(value)
        try:
            return NodeValue(tag, tagtype(value))
        except TypeError:
            print tag, tagtype, value
            raise
    except KeyError:
        raise UnknownTagError(tag)



