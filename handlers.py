import datetime
import re

from tornado import web

from euphony import util, albumart, mpdplayer, query
from euphony.config import current as config
from euphony.dacp import tags
from euphony.dacp.values import build_node
from euphony.dacp.constants import *
from euphony.db import db

__all__ = [
    'ServerInfoHandler', 'LoginHandler', 'UpdateHandler', 'DatabaseHandler', 'ContainersHandler',
    'ContainerItemsHandler', 'GroupsHandler', 'GroupArtHandler', 'BrowseArtistHandler',
    'ControlInterfaceHandler', 'GetSpeakerHandler', 'GetPropertyHandler', 'SetPropertyHandler',
    'PlayStatusUpdateHandler', 'NowPlayingArtHandler', 'PlayPauseHandler', 'PauseHandler'
    'DatabaseEditHandler', 'ContainerEditHandler',
]

mpd = mpdplayer.mpd

def parse_properties(properties, source):
    result = []
    for p in properties:
        try:
            propinfo = tags.PROPERTIES[p]
            value = source.get_property(p)
            if value is not None:
                result.append((propinfo[0], value))
        except KeyError:
            raise web.HTTPError(404)
    return result

class DMAPRequestHandler(web.RequestHandler):
    def prepare(self):
        self.set_header('Content-Type', 'application/x-dmap-tagged')
        self.set_header('DAAP-Server', DAAP_SERVER)

class ServerInfoHandler(DMAPRequestHandler):
    def get(self):
        node = build_node(('msrv', [
            ('mstt', 200),
            ('mpro', DMAP_PROTOCOL_VERSION),
            ('apro', DAAP_PROTOCOL_VERSION),
            ('aeSV', ITUNES_SHARING_VERSION),
            ('aeFP', True),
            ('ated', 3),
            ('msed', 1),
            ('msml', [
                ('msma', 71359108752128L),
                ('msma', 1102738509824L),
                ('msma', 8799319904256L),
            ]),
            ('ceWM', ''),
            ('ceVO', False),
            ('minm', config.server.name),
            ('mslr', True),
            ('mstm', DACP_TIMEOUT),
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
        if db.pairing.find_one({'guid': guid}) is not None:
            sid = util.generate_sessionid(guid)
            node =build_node(('mlog', [
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
        node = build_node(('mupd', [
            ('mstt', 200),
            ('musr', mpd.revision_number + 1),
        ]))
        self.write(node.serialize())
        self.finish()

class DatabaseHandler(DMAPRequestHandler):
    def get(self):
        node = build_node(('avdb', [
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
                    ('mctc', len(mpd.get_containers())),
                    ('meds', 3),
                ]),
            ]),
        ]))

        self.write(node.serialize())

class ContainersHandler(DMAPRequestHandler):
    def get(self, db):
        containers = mpd.get_containers()
        properties = self.get_argument('meta').split(',')

        container_nodes = [('mlit', parse_properties(properties, c)) for c in containers]

        node = build_node(('aply', [
            ('mstt', 200),
            ('muty', 0),
            ('mtco', len(containers)),
            ('mrco', len(containers)),
            ('mlcl', container_nodes),
        ]))

        self.write(node.serialize())

class ContainerItemsHandler(DMAPRequestHandler):
    def get(self, db, container_id):
        properties = self.get_argument('meta').split(',')
        sort_type = self.get_argument('sort', None)
        query_type = self.get_argument('type', None)
        query_string = self.get_argument('query', None)

        container = mpdplayer.Container.get(int(container_id))

        if container is None:
            raise web.HTTPError(400)

        if query_string:
            items = query.apply_query(query_string, container.fetch_items())
        else:
            items = container.fetch_items()

        item_nodes = [('mlit', parse_properties(properties, i)) for i in items]

        node = build_node(('apso', [
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
        params = dict(re.findall(PARAMETER_REGEX, self.get_argument('edit-params')))

        container = mpdplayer.Container.get(int(container_id))

        try:
            if action == 'add':
                self.add_to_container(container, int(params['dmap.itemid']))
            else:
                raise web.HTTPError(501)
        except KeyError:
            raise web.HTTPError(404)

    def add_to_container(self, container, item_id):
        item = mpdplayer.Item.get(item_id)
        if item:
            container.add_item(item)
            self.write(build_node(('medc', [
                ('mstt', 200),
                ('mlit', []),
            ])).serialize())
        else:
            raise web.HTTPError(204)


class DatabaseEditHandler(DMAPRequestHandler):
    def get(self, db):
        action = self.get_argument('action')
        params = dict(re.findall(PARAMETER_REGEX, self.get_argument('edit-params')))

        try:
            if action == 'add':
                self.add_playlist(params['dmap.itemname'])
            else:
                raise web.HTTPError(501)
        except KeyError:
            raise web.HTTPError(404)

    def add_playlist(self, name):
        pl = mpd.create_playlist(name)

        self.write(build_node(('medc', [
            ('mstt', 200),
            ('miid', pl.id),
        ])).serialize())

class GroupsHandler(DMAPRequestHandler):
    def get(self, db):
        query_string = self.get_argument('query')
        query_type = self.get_argument('type')
        group_type = self.get_argument('group-type')
        sort_by = self.get_argument('sort')
        include_headers = bool(int(self.get_argument('include-sort-headers', 0)))
        properties = self.get_argument('meta').split(',')

        albums = query.apply_query(query_string, mpd.get_albums())

        properties.append('dmap.itemcount')
        name_nodes = [('mlit', parse_properties(properties, a)) for a in albums]

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

        node = build_node(('agal', node_list))
        self.write(node.serialize())

class GroupArtHandler(DMAPRequestHandler):
    def get(self, db, group):
        width = int(self.get_argument('mw', 55))
        height = int(self.get_argument('mh', 55))
        try:
            album = mpdplayer.Album.get(int(group))
            artwork = albumart.AlbumArt(album.name, album.artist)
            self.set_header('Content-Type', 'image/png')
            self.write(artwork.get_png(width, height))
        except Exception:
            raise web.HTTPError(404)

class BrowseArtistHandler(DMAPRequestHandler):
    def get(self, db):
        filter_string = self.get_argument('filter')
        include_headers = bool(int(self.get_argument('include-sort-headers', 0)))

        artists = mpd.get_artists()

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

        node = build_node(('abro', node_list))
        self.write(node.serialize())

class ControlInterfaceHandler(DMAPRequestHandler):
    def get(self):
        node = build_node(('caci', [
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

class GetSpeakerHandler(DMAPRequestHandler):
    def get(self):
        node = build_node(('casp', [
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

        node_list += parse_properties(properties, mpd)
        node = build_node(('cmgt', node_list))

        self.write(node.serialize())

class SetPropertyHandler(DMAPRequestHandler):
    def get(self):
        for key in mpd.settable_properties:
            value = self.get_argument(key, None)
            if value is not None:
                mpd.set_property(key, value)

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

        if player_state != PLAYER_STATE_STOPPED:
            songinfo = mpd.get_current_track()
            timeinfo = mpd.get_current_time()
            node_list += [
                ('canp', mpd.get_property('dacp.nowplaying')),
                ('cann', songinfo['title']),
                ('cana', songinfo['artist']),
                ('canl', songinfo['album']),
                ('cang', songinfo['genre']),
                ('asai', mpd.get_current_album_id),
                ('cmmk', 1),
                ('ceGS', 1),
                ('cant', timeinfo[0]),
                ('cast', timeinfo[1]),
            ]

        node = build_node(('cmst', node_list))

        self.write(node.serialize())
        self.finish()

class NowPlayingArtHandler(DMAPRequestHandler):
    def get(self):
        width = int(self.get_argument('mw', 320))
        height = int(self.get_argument('mh', 320))
        try:
            songinfo = mpd.get_current_track()
            artwork = albumart.AlbumArt(songinfo['album'], songinfo['artist'])
            self.set_header('Content-Type', 'image/png')
            self.write(artwork.get_png(width, height))
        except albumart.ArtNotFoundError:
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