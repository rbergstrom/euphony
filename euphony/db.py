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

from pymongo import Connection

from config import current as config

__all__ = ['db']

conn = Connection(config.db.host, int(config.db.port))
db = conn[config.db.name]

def record_to_kwargs(record):
    return dict([(str(k), v) for k, v in record.iteritems() if not k.startswith('_')])

class BasicRecord(object):
    collection = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def insert(self):
        global db
        db[self.collection].insert(self.__dict__)

    @classmethod
    def find(cls, **kwargs):
        global db
        record = db[cls.collection].find_one(kwargs)
        if record is not None:
            return cls(**record_to_kwargs(record))
        else:
            return None

    @classmethod
    def add(cls, **kwargs):
        record = cls.find(**kwargs)
        if record is None:
            record = cls(**kwargs)
            record.insert()
        return record


class PairingRecord(BasicRecord):
    collection = 'pairing'

class AlbumArtRecord(BasicRecord):
    collection = 'albumart'
