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
import logging
import os.path
import xml.dom.minidom
import re
import StringIO
import urllib
import urllib2

import constants
import db
import util

ALBUMART_ROOT = 'http://www.albumart.org/index.php'

LASTFM_KEY = '7a2babf6de98a321d3da7a8e46265f76'
LASTFM_ROOT = 'http://ws.audioscrobbler.com/2.0'

IMAGE_SIZES = ('extralarge', 'large', 'medium', 'small')

HEADERS = {
    'User-Agent': constants.DAAP_SERVER,
}

not_found = set()

class ArtNotFoundError(Exception):
    pass

def get_albumart_url(artist, album):
    url = '%s?%s' % (ALBUMART_ROOT, urllib.urlencode({
        'itempage': 1,
        'newsearch': 1,
        'searchindex': 'Music',
        'srchkey': '%s %s' % (artist, album),
    }))
    logging.info('Fetching from albumart.org: %s' % url)
    req = urllib2.Request(url, headers=HEADERS)
    try:
        data = urllib2.urlopen(req).read()
        images = re.findall(r'title="(.+?)".*src=.*href="(.+?)".*zoom-icon\.jpg', data)
        for (title, url) in images:
            if util.clean_name(title) == util.clean_name(album):
                return url
        # If there's no exact match
        try:
            return images[0][1]
        except IndexError:
            pass
    except urllib2.URLError:
        pass

    return None

def get_lastfm_url(artist, album):
    url = '%s/?%s' % (
        LASTFM_ROOT, urllib.urlencode({
            'method': 'album.getinfo',
            'api_key': LASTFM_KEY,
            'artist': artist,
            'album': album,
        }))
    logging.info('Fetching from last.fm: %s' % url)
    req = urllib2.Request(url, headers=HEADERS)

    try:
        doc = xml.dom.minidom.parse(urllib2.urlopen(req))
        nodes = doc.getElementsByTagName('image')
        images = dict([(n.getAttribute('size'), n.childNodes[0].nodeValue) for n in nodes])
        for size in IMAGE_SIZES:
            try:
                return images[size]
            except KeyError:
                pass
    except Exception:
        pass

    return None

def serialize_image(img, width, height):
    buf = StringIO.StringIO()
    img.resize((width, height), Image.ANTIALIAS).save(buf, 'PNG')
    return buf.getvalue()

class AlbumArt(object):
    def __init__(self, artist, album):
        self.artist = artist
        self.album = album

    def get_png(self, width=300, height=300):
        try:
            buf = StringIO.StringIO(self._get_cached_artwork())
            img = Image.open(buf).convert('RGB')
        except ArtNotFoundError:
            key = '%s %s' % (self.artist, self.album)
            try:
                if key not in not_found:
                    img = self._download_image(min(width, height)).convert('RGB')
                else:
                    raise
            except ArtNotFoundError:
                not_found.add(key)
                raise
        return serialize_image(img, width, height)

    def _get_cached_artwork(self):
        record = db.AlbumArtRecord.find(artist=util.clean_name(self.artist),
                                        album=util.clean_name(self.album))
        if record is not None:
            return base64.b64decode(record.data)
        else:
            raise ArtNotFoundError(self.album, self.artist)

    def _cache_artwork(self, image_data):
        logging.info('Caching artwork for \'%s\' by \'%s\'' % (self.album, self.artist))
        db.AlbumArtRecord.add(artist=util.clean_name(self.artist),
                              album=util.clean_name(self.album),
                              data=base64.b64encode(image_data))


    def _download_image(self, min_size):
        best = None
        for func in (get_lastfm_url, get_albumart_url):
            url = func(self.artist, self.album)
            logging.debug('Trying image: \'%s\'' % url)
            if url is not None:
                try:
                    img_data = urllib2.urlopen(url).read()
                    img = Image.open(StringIO.StringIO(img_data))

                    if max(img.size) >= min_size:
                        self._cache_artwork(img_data)
                        return img
                    else:
                        logging.debug('Too small %d - looking for %d' %
                                (max(img.size), min_size))

                    if (best is None) or (img.size > best[0].size):
                        best = (img, img_data)

                except urllib2.URLError:
                    pass

        if best is not None:
            self._cache_artwork(best[1])
            return best[0]
        else:
            raise ArtNotFoundError(self.artist, self.album)


