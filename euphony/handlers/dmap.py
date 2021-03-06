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
import operator
import re

from tornado import web

import albumart
import constants
import dacpy.pairing
import dacpy.tags
import dacpy.types
import euphony
import logging
import query
import util

from config import current as config
from db import PairingRecord
from mpdplayer import MPD

mpd = MPD(str(config.mpd.host), int(config.mpd.port))

def query_to_dict(query):
    """ Turns a **simple** query (ignores subgroups) into a dict """
    return dict(re.findall(r"([^\(\),+']+?)[:!]+([^\(\),+']+)", query))

def fetch_properties(properties, source):
    """ Returns a list of tag-value tuples from the source object """
    result = []
    for p in properties:
        try:
            propinfo = dacpy.tags.PROPERTIES[p]
            value = source.get_property(p)
            if value is not None:
                result.append((propinfo[0], value))
        except KeyError:
            raise web.HTTPError(404)
    return result

class DMAPRequestHandler(web.RequestHandler):
    def prepare(self):
        self.set_header('Content-Type', 'application/x-dmap-tagged')
        self.set_header('DAAP-Server', constants.DAAP_SERVER)

class ServerInfoHandler(DMAPRequestHandler):
    def get(self):
        node = dacpy.types.build_node(('msrv', [
            ('mstt', 200),
            ('mpro', constants.DMAP_PROTOCOL_VERSION),
            ('apro', constants.DAAP_PROTOCOL_VERSION),
            ('aeSV', constants.ITUNES_SHARING_VERSION),
            ('aeFP', True),
            ('ated', 3),
            ('msed', 1),
            ('msml', [
                ('msma', 0x0000298F668C2400L),
                ('msma', 0x00000100C0565000L),
                ('msma', 0x00000800C0565000L),
            ]),
            ('ceWM', ''),
            ('ceVO', False),
            ('minm', config.server.name),
            ('mslr', True),
            ('mstm', constants.DACP_TIMEOUT),
            ('msal', True),
            ('msas', 3),
            ('msup', True),
            ('mspi', True),
            ('msex', True),
            ('msbr', True),
            ('msqy', True),
            ('msix', True),
            ('msrs', True),
            ('msdc', True),
            ('mstc', datetime.datetime.utcnow),
            ('msto', util.get_tz_offset)
        ]))
        self.write(node.serialize())

class LoginHandler(DMAPRequestHandler):
    def get(self):
        guid = int(self.get_argument('pairing-guid'), 16)
        if PairingRecord.find(guid) is not None:
            sid = util.generate_sessionid(guid)
            node = dacpy.types.build_node(('mlog', [
                ('mstt', 200),
                ('mlid', sid),
            ]))
            self.write(node.serialize())
        else:
            raise web.HTTPError(503)

class UpdateHandler(DMAPRequestHandler):
    @web.asynchronous
    def get(self):
        mpd.register_update_callback(self.send_response, int(self.get_argument('revision-number', 1)))

    def send_response(self):
        node = dacpy.types.build_node(('mupd', [
            ('mstt', 200),
            ('musr', mpd.revision_number + 1),
        ]))
        self.write(node.serialize())
        self.finish()

class DatabaseHandler(DMAPRequestHandler):
    def get(self):
        node = dacpy.types.build_node(('avdb', [
            ('mstt', 200),
            ('muty', False),
            ('mtco', 1),
            ('mrco', 1),
            ('mlcl', [
                ('mlit', [
                    ('miid', 1),
                    ('mper', 1L),
                    ('minm', config.server.name),
                    ('mimc', 1),
                    ('mctc', len(mpd.containers)),
                    ('meds', 3),
                ]),
            ]),
        ]))
        self.write(node.serialize())

class DatabaseItemsHandler(DMAPRequestHandler):
    def get(self, db):
        properties = self.get_argument('meta').split(',')
        sort_type = self.get_argument('sort', None)
        query_type = self.get_argument('type', None)
        query_string = self.get_argument('query', '')

        container = mpd.root_playlist

        if query_string:
            items = list(container.items.query(query_string))
        else:
            items = list(container.items)

        if 'daap.songalbumid' in query_string:
            items.sort(key=operator.attrgetter('track'))

        item_nodes = [('mlit', fetch_properties(properties, i)) for i in items]

        node = dacpy.types.build_node(('apso', [
            ('mstt', 200),
            ('muty', 0),
            ('mtco', len(item_nodes)),
            ('mrco', len(item_nodes)),
            ('mlcl', item_nodes),
        ]))

        self.write(node.serialize())

class ContainersHandler(DMAPRequestHandler):
    def get(self, db):
        properties = self.get_argument('meta').split(',')

        container_nodes = [('mlit', fetch_properties(properties, c)) for c in mpd.containers]

        node = dacpy.types.build_node(('aply', [
            ('mstt', 200),
            ('muty', 1),
            ('mtco', len(mpd.containers)),
            ('mrco', len(mpd.containers)),
            ('mlcl', container_nodes),
        ]))
        self.write(node.serialize())

class ContainerItemsHandler(DMAPRequestHandler):
    def get(self, db, container_id):
        properties = self.get_argument('meta').split(',')
        sort_type = self.get_argument('sort', None)
        query_type = self.get_argument('type', None)
        query_string = self.get_argument('query', '')

        container = mpd.containers.get_by_id(int(container_id))

        if container is None:
            raise web.HTTPError(400)

        if query_string:
            items = list(container.items.query(query_string))
        else:
            items = list(container.items)

        if 'daap.songalbumid' in query_string:
            items.sort(key=operator.attrgetter('track'))

        item_nodes = [('mlit', fetch_properties(properties, i)) for i in items]

        node = dacpy.types.build_node(('apso', [
            ('mstt', 200),
            ('muty', 0),
            ('mtco', len(item_nodes)),
            ('mrco', len(item_nodes)),
            ('mlcl', item_nodes),
        ]))

        self.write(node.serialize())

class ContainerEditHandler(DMAPRequestHandler):
    def get(self, db, container_id):
        action = self.get_argument('action')
        params = query_to_dict(self.get_argument('edit-params'))

        container = mpd.containers.get_by_id(int(container_id))

        try:
            if action == 'add':
                self.add_to_container(container, int(params['dmap.itemid']))
            else:
                raise web.HTTPError(501)
        except KeyError:
            raise web.HTTPError(404)

    def add_to_container(self, container, item_id):
        item = mpd.items.get_by_id(int(item_id))
        if item:
            container.add_item(item)
            self.write(dacpy.types.build_node(('medc', [
                ('mstt', 200),
                ('mlit', []),
            ])).serialize())
        else:
            raise web.HTTPError(204)


class DatabaseEditHandler(DMAPRequestHandler):
    def get(self, db):
        action = self.get_argument('action')
        params = query_to_dict(self.get_argument('edit-params'))

        try:
            if action == 'add':
                self.add_playlist(params['dmap.itemname'])
            else:
                raise web.HTTPError(501)
        except KeyError:
            raise web.HTTPError(404)

    def add_playlist(self, name):
        pl = mpd.create_playlist(name)

        self.write(dacpy.types.build_node(('medc', [
            ('mstt', 200),
            ('miid', pl.id),
        ])).serialize())

class GroupsHandler(DMAPRequestHandler):
    def get(self, db):
        query_string = self.get_argument('query')
        query_type = self.get_argument('type')
        group_type = self.get_argument('group-type')
        sort_type = self.get_argument('sort')
        include_headers = bool(int(self.get_argument('include-sort-headers', 0)))
        properties = self.get_argument('meta').split(',')

        albums = util.sort_by_initial(mpd.albums.query(query_string), key=operator.attrgetter('name'))

        properties.append('dmap.itemcount')
        name_nodes = [('mlit', fetch_properties(properties, a)) for a in albums]

        node_list = [
            ('mstt', 200),
            ('muty', 0),
            ('mtco', len(albums)),
            ('mrco', len(albums)),
            ('mlcl', name_nodes),
        ]

        if include_headers:
            header_data = util.build_sort_headers([a.name for a in albums])
            header_nodes = []
            for (char, index, num) in header_data:
                header_nodes.append(('mlit', [
                    ('mshc', char),
                    ('mshi', index),
                    ('mshn', num),
                ]))
            node_list.append(('mshl', header_nodes))

        node = dacpy.types.build_node(('agal', node_list))
        self.write(node.serialize())

class GroupArtHandler(DMAPRequestHandler):
    def get(self, db, group):
        width = int(self.get_argument('mw', 55))
        height = int(self.get_argument('mh', 55))
        try:
            album = mpd.albums.get_by_id(int(group))
            artwork = albumart.AlbumArt(album.artist.name, album.name)
            self.set_header('Content-Type', 'image/png')
            self.write(artwork.get_png(width, height))
        except Exception:
            raise web.HTTPError(404)

class BrowseArtistHandler(DMAPRequestHandler):
    def get(self, db):
        filter_string = self.get_argument('filter')
        include_headers = bool(int(self.get_argument('include-sort-headers', 0)))

        artists = util.sort_by_initial(mpd.artists.query(filter_string), key=operator.attrgetter('name'))

        name_nodes = [('mlit', a.name) for a in artists]

        node_list = [
            ('mstt', 200),
            ('muty', 0),
            ('mtco', len(artists)),
            ('mrco', len(artists)),
            ('abar', name_nodes),
        ]

        if include_headers:
            header_data = util.build_sort_headers([a.name for a in artists])
            header_nodes = []
            for (char, index, num) in header_data:
                header_nodes.append(('mlit', [
                    ('mshc', char),
                    ('mshi', index),
                    ('mshn', num),
                ]))
            node_list.append(('mshl', header_nodes))

        node = dacpy.types.build_node(('abro', node_list))
        self.write(node.serialize())

class ControlInterfaceHandler(DMAPRequestHandler):
    def get(self):
        node = dacpy.types.build_node(('caci', [
            ('mstt', 200),
            ('muty', 0),
            ('mtco', 1),
            ('mrco', 1),
            ('mlcl', [
                ('mlit', [
                    ('miid', 1),
                    ('cmik', True),
                    ('cmsp', True),
                    ('cmsv', True),
                    ('cass', True),
                    ('casu', True),
                    ('ceSG', True),
                ]),
            ]),
        ]))
        self.write(node.serialize())

class CueHandler(DMAPRequestHandler):
    def get(self):
        command = self.get_argument('command')

        if command == 'clear':
            self.command_clear()
        elif command == 'play':
            query_string = self.get_argument('query')
            index = int(self.get_argument('index'))
            sort_type = self.get_argument('sort')
            self.command_play(query_string, index)
        else:
            raise web.HTTPError(501)

    def command_clear(self):
        mpd.clear_current()

        self.write(dacpy.types.build_node(('cacr', [
            ('mstt', 200),
            ('miid', 0),
        ])).serialize())

    def command_play(self, query_string, index):
        items = list(mpd.items.query(query_string))
        items.sort(key=operator.attrgetter('album.name', 'track'))

        for i in items:
            mpd.add_to_current(i.uri)
        mpd.play(index)

        self.write(dacpy.types.build_node(('cacr', [
            ('mstt', 200),
            ('miid', 0),
        ])).serialize())


class GetSpeakerHandler(DMAPRequestHandler):
    def get(self):
        node = dacpy.types.build_node(('casp', [
            ('mstt', 200),
            ('mdcl', [
                ('caia', 1),
                ('minm', 'MPD Output Device'),
                ('msma', 0),
            ]),
        ]))
        self.write(node.serialize())

class GetPropertyHandler(DMAPRequestHandler):
    def get(self):
        properties = self.get_argument('properties').split(',')
        node_list = [
            ('mstt', 200)
        ]

        # Handle special properties that return multiple tags
        if 'dacp.nowplaying' in properties:
            properties.remove('dacp.nowplaying')
        if 'dacp.playingtime' in properties:
            properties.remove('dacp.playingtime')

        node_list += fetch_properties(properties, mpd)
        node = dacpy.types.build_node(('cmgt', node_list))
        self.write(node.serialize())

class SetPropertyHandler(DMAPRequestHandler):
    def get(self):
        for (prop, values) in self.request.arguments.iteritems():
            # Take the last instance of each property, to allow for duplicates
            ret = mpd.set_property(prop, values[-1])
            if ret is None:
                logging.info("Unknown Property: %s (Value = %s)" % (prop, values))
        raise web.HTTPError(204)


class PlayStatusUpdateHandler(DMAPRequestHandler):
    @web.asynchronous
    def get(self):
        mpd.register_update_callback(self.send_response, int(self.get_argument('revision-number', 1)))

    def send_response(self):
        player_state = mpd.get_property('dacp.playerstate')
        node_list = [
            ('mstt', 200),
            ('cmsr', mpd.revision_number + 1),
            ('caps', player_state),
            ('cash', mpd.get_property('dacp.shufflestate')),
            ('carp', mpd.get_property('dacp.repeatstate')),
            ('cavc', mpd.get_property('dacp.volumecontrollable')),
            ('caas', mpd.get_property('dacp.availableshufflestates')),
            ('caar', mpd.get_property('dacp.availablerepeatstates')),
        ]

        if player_state != constants.PLAYER_STATE_STOPPED:
            songinfo = mpd.get_current_track()
            timeinfo = mpd.get_current_time()
            node_list += [
                ('canp', mpd.get_property('dacp.nowplaying')),
                ('cann', songinfo.get('title', '')),
                ('cana', songinfo.get('artist', '')),
                ('canl', songinfo.get('album', '')),
                ('cang', songinfo.get('genre', '')),
                ('asai', mpd.get_current_album_id),
                ('cmmk', 1),
                ('ceGS', 1),
                ('cant', timeinfo[1] - timeinfo[0]),
                ('cast', timeinfo[1]),
            ]

        node = dacpy.types.build_node(('cmst', node_list))
        self.write(node.serialize())
        self.finish()

class NowPlayingArtHandler(DMAPRequestHandler):
    def get(self):
        width = int(self.get_argument('mw', 300))
        height = int(self.get_argument('mh', 300))
        try:
            songinfo = mpd.get_current_track()
            artwork = albumart.AlbumArt(songinfo['artist'], songinfo['album'])
            self.set_header('Content-Type', 'image/png')
            self.write(artwork.get_png(width, height))
        except (KeyError, albumart.ArtNotFoundError):
            raise web.HTTPError(404)

class PlaySpecHandler(DMAPRequestHandler):
    def get(self):
        database_spec = query_to_dict(self.get_argument('database-spec'))
        container_spec = query_to_dict(self.get_argument('container-spec'))
        item_spec = query_to_dict(self.get_argument('container-item-spec'))
        try:
            container = mpd.containers.get_by_id(int(container_spec['dmap.persistentid'], 16))
            index = container.get_item_index(int(item_spec['dmap.containeritemid'], 16))
            mpd.clear_current()
            mpd.load_playlist(container.name)
            if index < 0:
                raise web.HTTPError(404)
            mpd.play(index)
        except KeyError:
            raise web.HTTPError(404)

class PlayPauseHandler(DMAPRequestHandler):
    def get(self):
        mpd.toggle_play()

class PauseHandler(DMAPRequestHandler):
    def get(self):
        mpd.pause()

class NextItemHandler(DMAPRequestHandler):
    def get(self):
        mpd.next()

class PrevItemHandler(DMAPRequestHandler):
    def get(self):
        mpd.prev()
