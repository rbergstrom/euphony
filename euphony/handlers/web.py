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

import datetime
import Image
import operator
import os.path
import re

from tornado import web, escape
from jinja2 import Environment, FileSystemLoader

import albumart
import constants
import dacpy.pairing
import euphony
import logging
import query

from config import current as config
from db import db, PairingRecord
from mpdplayer import MPD

PLACEHOLDER_IMG = os.path.join(os.path.dirname(__file__), 'albumart_placeholder.png')

mpd = MPD(str(config.mpd.host), int(config.mpd.port))

env = Environment(loader=FileSystemLoader('views'))

class JinjaRequestHandler(web.RequestHandler):
    def render(self, template_name, **kwargs):
        args = {
            'handler': self,
            'request': self.request,
            'current_user': self.current_user,
            'locale': self.locale,
            '_': self.locale.translate,
            'static_url': self.static_url,
            'xsrf_form_html': self.xsrf_form_html,
            'reverse_url': self.application.reverse_url,
        }
        args.update(self.ui)
        args.update(kwargs)
        self.finish(env.get_template(template_name).render(args))

class StatusDashboardHandler(JinjaRequestHandler):
    @web.addslash
    def get(self):
        args = {
            'server_name': config.server.name,
        }
        self.render('status.html', **args)

class CurrentStatusJsonHandler(JinjaRequestHandler):
    def get(self):
        track = mpd.get_current_item()
        status = mpd.get_current_status()

        timeinfo = status.get('time', '0:0').split(':')

        self.write({
            'track': track.serialize_to_json(),
            'playlist': [x.serialize_to_json() for x in mpd.get_current_playlist()],
            'status': {
                'playlist_index': int(status.get('song', 0)),
                'next_index': int(status.get('nextsong', 0)),
                'time': int(timeinfo[0]),
                'volume': int(status.get('volume', 0)),
            },
        })

class PlaylistJsonHandler(JinjaRequestHandler):
    def get(self, playlist_id):
        pl = mpd.containers.get_by_id(int(playlist_id))

        if pl is None:
            raise web.HTTPError(404)

        self.write(pl.serialize_to_json())

class AlbumArtHandler(JinjaRequestHandler):
    def get(self, album_id, width, height):
        width = int(width)
        height = int(height)
        self.set_header('Content-Type', 'image/png')
        try:
            album = mpd.albums.get_by_id(int(album_id))
            artwork = albumart.AlbumArt(album.artist.name, album.name)
            self.write(artwork.get_png(width, height))
        except (TypeError, albumart.ArtNotFoundError):
            self.write(albumart.serialize_image(Image.open(PLACEHOLDER_IMG).convert('RGB'), width, height))

# Pairing

class PairingHandler(JinjaRequestHandler):
    @web.addslash
    def get(self):
        self.render('pairing.html')

    def post(self):
        app = euphony.EuphonyServer.instance()
        code = self.get_argument('code')
        remote_id = self.get_argument('remotes')
        try:
            remote = app.remote_listener.remotes[remote_id]
            PairingRecord.add(guid=remote.pair(code, config.server.id))
        except KeyError:
            raise web.HTTPError(500)
        except Exception as e:
            raise web.HTTPError(403)
        self.write('Pairing succeeded!')


class ListRemotesHandler(JinjaRequestHandler):
    def get(self):
        app = euphony.EuphonyServer.instance()
        self.set_header('Content-Type', 'application/json')
        self.write({
            'remotes': dict(
                [(k, unicode(v)) for k, v in app.remote_listener.remotes.iteritems()]),
        })

