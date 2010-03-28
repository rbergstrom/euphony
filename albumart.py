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

import base64
import Image
import lxml.etree
import StringIO
import urllib
import urllib2

from euphony import util
from euphony.db import db
from euphony.dacp.constants import *

LASTFM_KEY = '7a2babf6de98a321d3da7a8e46265f76'
LASTFM_ROOT = 'http://ws.audioscrobbler.com/2.0'

IMAGE_SIZES = ('extralarge', 'large', 'medium', 'small')

class ArtNotFoundError(Exception):
    pass

class AlbumArt(object):
    def __init__(self, album, artist):
        self.album = album
        self.artist = artist

        self._headers = {
            'User-Agent': DAAP_SERVER,
        }

    def get_png(self, width=320, height=320):
        output = StringIO.StringIO()
        img = self._fetch_image().resize((width, height), Image.ANTIALIAS)
        img.save(output, 'PNG')
        return output.getvalue()

    def _get_cached_artwork(self):
        try:
            record = db.albumart.find_one({
                'artist': util.clean_name(self.artist),
                'album': util.clean_name(self.album),
            })
            return base64.b64decode(record['data'])
        except TypeError:
            raise ArtNotFoundError(self.album, self.artist)

    def _cache_artwork(self, image_data):
        record = {
            'artist': util.clean_name(self.artist),
            'album': util.clean_name(self.album),
            'data': base64.b64encode(image_data),
        }
        db.albumart.insert(record)

    def _get_artwork_url(self):
        url = '%s/?method=album.getinfo&api_key=%s&artist=%s&album=%s' % (
            LASTFM_ROOT, LASTFM_KEY, urllib.quote_plus(self.artist), urllib.quote_plus(self.album))
        req = urllib2.Request(url, headers=self._headers)

        try:
            xml = lxml.etree.parse(urllib2.urlopen(req))
            for size in IMAGE_SIZES:
                try:
                    return xml.xpath('//image[@size="%s"]/text()' % size)[0]
                except IndexError:
                    pass
        except IOError:
            pass

        raise ArtNotFoundError(self.album, self.artist)

    def _fetch_image(self):
        try:
            buf = StringIO.StringIO(self._get_cached_artwork())
            return Image.open(buf).convert('RGB')
        except ArtNotFoundError:
            req = urllib2.Request(self._get_artwork_url(), headers=self._headers)
            try:
                image_data = urllib2.urlopen(req).read()
                self._cache_artwork(image_data)
                buf = StringIO.StringIO(image_data)
                return Image.open(buf).convert('RGB')
            except urllib2.URLError:
                raise ArtNotFoundError(self.album, self.artist)



