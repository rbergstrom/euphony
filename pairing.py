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

import logging
import os.path
import socket
import struct
import urllib2

import dacp
import db

__all__  = ['generate_code', 'TouchRemote', 'TouchRemoteListener']

class TouchRemote(object):
    def __init__(self, name, address, port, pairid):
        self.name = name
        self.address = address
        self.port = port
        self.pairid = pairid

    def pair(self, passcode, servicename):
        hashcode = generate_code(passcode, self.pairid)
        logging.info('Attempting to pair with %s:%d with code %s' % (
            self.address, self.port, hashcode
        ))

        try:
            resp = urllib2.urlopen('http://%s:%d/pair?pairingcode=%s&servicename=%s' % (
                self.address, self.port, hashcode, servicename
            ))
            node = dacp.NodeValue.deserialize(resp.read())

            logging.info('Pairing successful with GUID %016X' % node.cmpg[0])
            db.PairingRecord.add(guid=node.cmpg[0])
        except Exception, e:
            logging.warning('Pairing failed: %s' % e)

        return node

    def __unicode__(self):
        return '%(name)s @ %(address)s:%(port)d' % self.__dict__


class TouchRemoteListener(object):
    def __init__(self):
        self.remotes = {}

    def removeService(self, mdns, type, name):
        try:
            del self.remotes[name]
        except KeyError:
            pass

    def addService(self, mdns, type, name):
        info = mdns.getServiceInfo(type, name)
        props = info.getProperties()
        self.remotes[name] = TouchRemote(
            props['DvNm'],
            str(socket.inet_ntoa(info.getAddress())),
            info.getPort(),
            props['Pair'],
        )
        logging.info('New remote found: %s' % self.remotes[name])

class uint32(object):
    def __init__(self, value, base=10):
        try:
            self.real = 0xffffffff & value
        except TypeError:
            self.real = 0xffffffff & int(value, base)

    def __add__(self, other):
        return uint32(self.real + other.real)

    def __sub__(self, other):
        return uint32(self.real - other.real)

    def __lshift__(self, other):
        return uint32(self.real << other.real)

    def __rshift__(self, other):
        return uint32(self.real >> other.real)

    def __and__(self, other):
        return uint32(self.real & other.real)

    def __or__(self, other):
        return uint32(self.real | other.real)

    def __xor__(self, other):
        return uint32(self.real ^ other.real)

    def __invert__(self):
        return uint32(0xffffffff - self.real)

# Based on the iTunes pairing code hash from:
# http://jinxidoru.blogspot.com/2009/06/itunes-remote-pairing-code.html
#
# Which was, in turn, based on the XINE project, released under the GPL.

def generate_code(passcode, pair):
    rawparam = struct.pack('16s8sB31xB7x', pair, passcode.encode('utf-16')[2:], 0x80, 0xc0)
    param = [uint32(x) for x in struct.unpack('16L', rawparam)]

    a = uint32(0x67452301)
    b = uint32(0xefcdab89)
    c = uint32(0x98badcfe)
    d = uint32(0x10325476)

    a = ((b & c) | (~b & d)) + param[0] + a - 0x28955B88
    a = ((a << 0x07) | (a >> 0x19)) + b
    d = ((a & b) | (~a & c)) + param[1] + d - 0x173848AA
    d = ((d << 0x0c) | (d >> 0x14)) + a
    c = ((d & a) | (~d & b)) + param[2] + c + 0x242070DB
    c = ((c << 0x11) | (c >> 0x0f)) + d
    b = ((c & d) | (~c & a)) + param[3] + b - 0x3E423112
    b = ((b << 0x16) | (b >> 0x0a)) + c
    a = ((b & c) | (~b & d)) + param[4] + a - 0x0A83F051
    a = ((a << 0x07) | (a >> 0x19)) + b
    d = ((a & b) | (~a & c)) + param[5] + d + 0x4787C62A
    d = ((d << 0x0c) | (d >> 0x14)) + a
    c = ((d & a) | (~d & b)) + param[6] + c - 0x57CFB9ED
    c = ((c << 0x11) | (c >> 0x0f)) + d
    b = ((c & d) | (~c & a)) + param[7] + b - 0x02B96AFF
    b = ((b << 0x16) | (b >> 0x0a)) + c
    a = ((b & c) | (~b & d)) + param[8] + a + 0x698098D8
    a = ((a << 0x07) | (a >> 0x19)) + b
    d = ((a & b) | (~a & c)) + param[9] + d - 0x74BB0851
    d = ((d << 0x0c) | (d >> 0x14)) + a
    c = ((d & a) | (~d & b)) + param[10] + c - 0x0000A44F
    c = ((c << 0x11) | (c >> 0x0f)) + d
    b = ((c & d) | (~c & a)) + param[11] + b - 0x76A32842
    b = ((b << 0x16) | (b >> 0x0a)) + c
    a = ((b & c) | (~b & d)) + param[12] + a + 0x6B901122
    a = ((a << 0x07) | (a >> 0x19)) + b
    d = ((a & b) | (~a & c)) + param[13] + d - 0x02678E6D
    d = ((d << 0x0c) | (d >> 0x14)) + a
    c = ((d & a) | (~d & b)) + param[14] + c - 0x5986BC72
    c = ((c << 0x11) | (c >> 0x0f)) + d
    b = ((c & d) | (~c & a)) + param[15] + b + 0x49B40821
    b = ((b << 0x16) | (b >> 0x0a)) + c

    a = ((b & d) | (~d & c)) + param[1] + a - 0x09E1DA9E
    a = ((a << 0x05) | (a >> 0x1b)) + b
    d = ((a & c) | (~c & b)) + param[6] + d - 0x3FBF4CC0
    d = ((d << 0x09) | (d >> 0x17)) + a
    c = ((d & b) | (~b & a)) + param[11] + c + 0x265E5A51
    c = ((c << 0x0e) | (c >> 0x12)) + d
    b = ((c & a) | (~a & d)) + param[0] + b - 0x16493856
    b = ((b << 0x14) | (b >> 0x0c)) + c
    a = ((b & d) | (~d & c)) + param[5] + a - 0x29D0EFA3
    a = ((a << 0x05) | (a >> 0x1b)) + b
    d = ((a & c) | (~c & b)) + param[10] + d + 0x02441453
    d = ((d << 0x09) | (d >> 0x17)) + a
    c = ((d & b) | (~b & a)) + param[15] + c - 0x275E197F
    c = ((c << 0x0e) | (c >> 0x12)) + d
    b = ((c & a) | (~a & d)) + param[4] + b - 0x182C0438
    b = ((b << 0x14) | (b >> 0x0c)) + c
    a = ((b & d) | (~d & c)) + param[9] + a + 0x21E1CDE6
    a = ((a << 0x05) | (a >> 0x1b)) + b
    d = ((a & c) | (~c & b)) + param[14] + d - 0x3CC8F82A
    d = ((d << 0x09) | (d >> 0x17)) + a
    c = ((d & b) | (~b & a)) + param[3] + c - 0x0B2AF279
    c = ((c << 0x0e) | (c >> 0x12)) + d
    b = ((c & a) | (~a & d)) + param[8] + b + 0x455A14ED
    b = ((b << 0x14) | (b >> 0x0c)) + c
    a = ((b & d) | (~d & c)) + param[13] + a - 0x561C16FB
    a = ((a << 0x05) | (a >> 0x1b)) + b
    d = ((a & c) | (~c & b)) + param[2] + d - 0x03105C08
    d = ((d << 0x09) | (d >> 0x17)) + a
    c = ((d & b) | (~b & a)) + param[7] + c + 0x676F02D9
    c = ((c << 0x0e) | (c >> 0x12)) + d
    b = ((c & a) | (~a & d)) + param[12] + b - 0x72D5B376
    b = ((b << 0x14) | (b >> 0x0c)) + c

    a = (b ^ c ^ d) + param[5] + a - 0x0005C6BE
    a = ((a << 0x04) | (a >> 0x1c)) + b
    d = (a ^ b ^ c) + param[8] + d - 0x788E097F
    d = ((d << 0x0b) | (d >> 0x15)) + a
    c = (d ^ a ^ b) + param[11] + c + 0x6D9D6122
    c = ((c << 0x10) | (c >> 0x10)) + d
    b = (c ^ d ^ a) + param[14] + b - 0x021AC7F4
    b = ((b << 0x17) | (b >> 0x09)) + c
    a = (b ^ c ^ d) + param[1] + a - 0x5B4115BC
    a = ((a << 0x04) | (a >> 0x1c)) + b
    d = (a ^ b ^ c) + param[4] + d + 0x4BDECFA9
    d = ((d << 0x0b) | (d >> 0x15)) + a
    c = (d ^ a ^ b) + param[7] + c - 0x0944B4A0
    c = ((c << 0x10) | (c >> 0x10)) + d
    b = (c ^ d ^ a) + param[10] + b - 0x41404390
    b = ((b << 0x17) | (b >> 0x09)) + c
    a = (b ^ c ^ d) + param[13] + a + 0x289B7EC6
    a = ((a << 0x04) | (a >> 0x1c)) + b
    d = (a ^ b ^ c) + param[0] + d - 0x155ED806
    d = ((d << 0x0b) | (d >> 0x15)) + a
    c = (d ^ a ^ b) + param[3] + c - 0x2B10CF7B
    c = ((c << 0x10) | (c >> 0x10)) + d
    b = (c ^ d ^ a) + param[6] + b + 0x04881D05
    b = ((b << 0x17) | (b >> 0x09)) + c
    a = (b ^ c ^ d) + param[9] + a - 0x262B2FC7
    a = ((a << 0x04) | (a >> 0x1c)) + b
    d = (a ^ b ^ c) + param[12] + d - 0x1924661B
    d = ((d << 0x0b) | (d >> 0x15)) + a
    c = (d ^ a ^ b) + param[15] + c + 0x1fa27cf8
    c = ((c << 0x10) | (c >> 0x10)) + d
    b = (c ^ d ^ a) + param[2] + b - 0x3B53A99B
    b = ((b << 0x17) | (b >> 0x09)) + c

    a = ((~d | b) ^ c) + param[0] + a - 0x0BD6DDBC
    a = ((a << 0x06) | (a >> 0x1a)) + b
    d = ((~c | a) ^ b) + param[7] + d + 0x432AFF97
    d = ((d << 0x0a) | (d >> 0x16)) + a
    c = ((~b | d) ^ a) + param[14] + c - 0x546BDC59
    c = ((c << 0x0f) | (c >> 0x11)) + d
    b = ((~a | c) ^ d) + param[5] + b - 0x036C5FC7
    b = ((b << 0x15) | (b >> 0x0b)) + c
    a = ((~d | b) ^ c) + param[9] + a + 0x655B59C3
    a = ((a << 0x06) | (a >> 0x1a)) + b
    d = ((~c | a) ^ b) + param[3] + d - 0x70F3336E
    d = ((d << 0x0a) | (d >> 0x16)) + a
    c = ((~b | d) ^ a) + param[10] + c - 0x00100B83
    c = ((c << 0x0f) | (c >> 0x11)) + d
    b = ((~a | c) ^ d) + param[1] + b - 0x7A7BA22F
    b = ((b << 0x15) | (b >> 0x0b)) + c
    a = ((~d | b) ^ c) + param[8] + a + 0x6FA87E4F
    a = ((a << 0x06) | (a >> 0x1a)) + b
    d = ((~c | a) ^ b) + param[15] + d - 0x01D31920
    d = ((d << 0x0a) | (d >> 0x16)) + a
    c = ((~b | d) ^ a) + param[6] + c - 0x5CFEBCEC
    c = ((c << 0x0f) | (c >> 0x11)) + d
    b = ((~a | c) ^ d) + param[13] + b + 0x4E0811A1
    b = ((b << 0x15) | (b >> 0x0b)) + c
    a = ((~d | b) ^ c) + param[4] + a - 0x08AC817E
    a = ((a << 0x06) | (a >> 0x1a)) + b
    d = ((~c | a) ^ b) + param[11] + d - 0x42C50DCB
    d = ((d << 0x0a) | (d >> 0x16)) + a
    c = ((~b | d) ^ a) + param[2] + c + 0x2AD7D2BB
    c = ((c << 0x0f) | (c >> 0x11)) + d
    b = ((~a | c) ^ d) + param[9] + b - 0x14792C6F
    b = ((b << 0x15) | (b >> 0x0b)) + c

    a += 0x67452301
    b += 0xefcdab89
    c += 0x98badcfe
    d += 0x10325476

    hashcode = struct.pack('<4L', a.real, b.real, c.real, d.real)
    return ''.join(['%02X' % ord(x) for x in hashcode])
