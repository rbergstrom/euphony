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

DAAP_SERVER = 'Euphony/0.1'

MDNS_TYPE_SERVER = '_touch-able._tcp.local.'
MDNS_TYPE_REMOTE = '_touch-remote._tcp.local.'

DACP_TIMEOUT = 1800

DMAP_PROTOCOL_VERSION = (2, 0, 6, 0)
DAAP_PROTOCOL_VERSION = (3, 0, 8, 0)
ITUNES_SHARING_VERSION = (3, 0, 1, 0)

PLAYER_STATE_STOPPED = 2
PLAYER_STATE_PAUSED = 3
PLAYER_STATE_PLAYING = 4
SHUFFLE_STATE_OFF = 0
SHUFFLE_STATE_ON = 1
REPEAT_STATE_OFF = 0
REPEAT_STATE_SINGLE = 1
REPEAT_STATE_ON = 2

AVAILABLE_REPEAT_STATES = 6
AVAILABLE_SHUFFLE_STATES = 2

VOLUME_CONTROLLABLE = 1

BASE_PLAYLIST = 'Library'
