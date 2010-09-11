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


import sqlite3

from config import current as config

__all__ = ['PairingRecord', 'AlbumArtRecord']

db = sqlite3.connect(config.db.path)
db.row_factory = sqlite3.Row

class RecordMeta(type):
    def __new__(cls, name, bases, attrs):
        obj = super(RecordMeta, cls).__new__(cls, name, bases, attrs)
        obj.build_table()
        return obj

class PairingRecord(object):
    __metaclass__ = RecordMeta

    def __init__(self, guid):
        self.guid = guid

    def insert(self):
        db.execute('INSERT INTO pairing (guid) VALUES (?)', (self.guid,))
        db.commit()

    @classmethod
    def find(cls, guid):
        for row in db.execute('SELECT * FROM pairing WHERE guid=?', (guid,)):
            return cls(row['guid'])
        return None

    @classmethod
    def add(cls, guid):
        record = cls.find(guid)
        if record is None:
            record = cls(guid)
            record.insert()
        return record

    @classmethod
    def build_table(cls):
        db.execute('''
            CREATE TABLE IF NOT EXISTS pairing (
               guid INTEGER UNIQUE
            )''')
        db.commit()

class AlbumArtRecord(object):
    __metaclass__ = RecordMeta

    def __init__(self, artist, album, data):
        self.artist = artist
        self.album = album
        self.data = data

    def insert(self):
        db.execute('''
            INSERT INTO albumart (artist, album, data)
            VALUES (?, ?, ?)
        ''', (self.artist, self.album, self.data))
        db.commit()

    @classmethod
    def find(cls, artist, album):
        for row in db.execute('SELECT * FROM albumart WHERE artist=? AND album=?', (artist, album)):
            return cls(row['artist'], row['album'], row['data'])
        return None

    @classmethod
    def add(cls, artist, album, data):
        record = cls.find(artist, album)
        if record is None:
            record = cls(artist, album, data)
            record.insert()
        return record

    @classmethod
    def build_table(cls):
        db.execute('''
            CREATE TABLE IF NOT EXISTS albumart (
                artist TEXT,
                album TEXT,
                data BLOB,
                PRIMARY KEY (artist, album) ON CONFLICT REPLACE
            )''')
        db.commit()

