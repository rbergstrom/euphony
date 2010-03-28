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

import os.path

from ConfigParser import SafeConfigParser

__all__ = ['current', 'ConfigSet']

class Section:
    def __init__(self, cfg, section):
        self._items = dict(cfg.items(section))

    def __getitem__(self, key):
        return self._items[key]

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError('Invalid key: %r' % name)

class ConfigSet:
    def __init__(self, inifile):
        cfg = SafeConfigParser()
        cfg.read(inifile)

        self._sections = dict([(s, Section(cfg, s)) for s in cfg.sections()])

    def __getitem__(self, key):
        return self._sections[key]

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError('Invalid section: %r' % name)

basepath = os.path.dirname(os.path.abspath(__file__))
current = ConfigSet(os.path.join(basepath, 'config.ini'))
