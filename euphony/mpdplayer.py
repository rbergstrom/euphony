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

import collections
import logging
import socket
import threading

import constants
import mpdclient
import util
import query

from config import current as config

__all__ = ['MPD', 'Container', 'Album', 'Artist', 'mpd']

SERVER_NAME = u'MPD@%s'

class InvalidItemError(ValueError):
    pass

class property_getter(object):
    def __init__(self, prop_name):
        self.prop_name = prop_name

    def __call__(self, func):
        func.prop_type = 'get'
        if hasattr(func, 'prop_name'):
            func.prop_name.append(self.prop_name)
        else:
            func.prop_name = [self.prop_name]
        return func

class property_setter(object):
    def __init__(self, prop_name):
        self.prop_name = prop_name

    def __call__(self, func):
        func.prop_type = 'set'
        if hasattr(func, 'prop_name'):
            func.prop_name.append(self.prop_name)
        else:
            func.prop_name = [self.prop_name]
        return func

class PropertyMeta(type):
    def __init__(cls, name, bases, attrs):
        cls._properties = collections.defaultdict(dict)
        for (k, v) in attrs.iteritems():
            if hasattr(v, 'prop_name') and hasattr(v, 'prop_type'):
                for n in v.prop_name:
                    cls._properties[v.prop_type][n] = v

class PropertyMixin(object):
    __metaclass__ = PropertyMeta

    def enumerate_properties(self):
        for (prop, func) in self._properties['get'].iteritems():
            yield (prop, func(self))

    def get_property(self, name):
        try:
            return self._properties['get'][name](self)
        except KeyError:
            return None

    def set_property(self, name, value):
        try:
            return self._properties['set'][name](self, value)
        except KeyError:
            return None

class MPDObjectMixin(object):
    def __init__(self, id):
        self.id = id
        self.mpd = MPD.instance()

class MPDMixin(object):
    def __init__(self, host, port, password=None):
        self.host = host
        self.port = port
        self.password = password

    def get_connection(self):
        client = mpdclient.MPDClient()
        client.connect(self.host, self.port)
        if self.password is not None:
            client.password(self.password)
        return client

    def execute(self, command, *args):
        client = self.get_connection()
        retval = getattr(client, command)(*args)
        client.disconnect()
        return retval

class Container(PropertyMixin, MPDObjectMixin):
    def __init__(self, id, name, is_base=False):
        MPDObjectMixin.__init__(self, id)
        self.name = name
        self.is_base = is_base
        # this MUST be zero for the remote to "see" the playlist
        self.parent_container_id = 0

        if self.is_base:
            self.items = self.mpd.items
        else:
            plfiles = set(self.mpd.execute('listplaylist', self.name))
            self.items = IndexedCollection(Item)
            for i in [x for x in self.mpd.items if x.uri in plfiles]:
                self.items.add_item(i)

    def __str__(self):
        return 'Container: %s' % self.name

    def __unicode__(self):
        return u'Container: %s' % self.name

    def serialize_to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'items': [i.serialize_to_json() for i in self.items],
        }

    def add_item(self, item):
        self.items.add_item(item)
        self.mpd.execute('playlistadd', self.name, item.uri)

    def get_item_index(self, itemid):
        for (index, item) in enumerate(self.items):
            if item.id == itemid:
                return index
        return -1

    @property_getter('dmap.itemname')
    def get_name(self):
        return self.name

    @property_getter('dmap.itemid')
    @property_getter('dmap.persistentid')
    def get_id(self):
        return self.id

    @property_getter('dmap.itemcount')
    def get_item_count(self):
        return len(self.items)

    @property_getter('dmap.parentcontainerid')
    def get_parent_container_id(self):
        return self.parent_container_id

    @property_getter('dmap.editcommandssupported')
    def get_editable(self):
        return not self.is_base

    @property_getter('daap.baseplaylist')
    def get_is_base_playlist(self):
        return self.is_base

class Artist(PropertyMixin, MPDObjectMixin):
    def __init__(self, id, name):
        MPDObjectMixin.__init__(self, id)
        self.name = name

    def __str__(self):
        return 'Artist: %s' % self.name

    def __unicode__(self):
        return u'Artist: %s' % self.name

    def serialize_to_json(self):
        return {
            'id': self.id,
            'name': self.name,
        }

    @property_getter('dmap.itemname')
    def get_name(self):
        return self.name

    @property_getter('dmap.itemid')
    @property_getter('dmap.persistentid')
    def get_id(self):
        return self.id

class Album(PropertyMixin, MPDObjectMixin):
    def __init__(self, id, name, artist):
        MPDObjectMixin.__init__(self, id)
        self.name = name
        self.artist = self.mpd.artists.first({'dmap.itemname': artist})
        self.item_count = len(self.mpd.execute('list', 'title', 'album', self.name))

    def __str__(self):
        return 'Album: %s' % self.name

    def __unicode__(self):
        return u'Album: %s' % self.name

    def serialize_to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'artist': self.artist.serialize_to_json(),
        }

    @property_getter('dmap.itemname')
    def get_name(self):
        return self.name

    @property_getter('dmap.itemid')
    @property_getter('dmap.persistentid')
    def get_id(self):
        return self.id

    @property_getter('daap.songalbumartist')
    @property_getter('daap.songartist')
    def get_artist_name(self):
        return self.artist.name

    @property_getter('dmap.itemcount')
    def get_item_count(self):
        return self.item_count

class Item(PropertyMixin, MPDObjectMixin):
    def __init__(self, id, name, uri, artist, album, track=1, year=None, composer=None, genre=None, time=0):
        MPDObjectMixin.__init__(self, id)
        self.uri = uri
        self.name = name
        self.artist = self.mpd.artists.first({'dmap.itemname': artist})
        self.album = self.mpd.albums.first({'dmap.itemname': album, 'dmap.songartist': artist})
        self.track = track
        self.item_kind = 2
        self.content_description = ''
        self.has_video = 0
        self.year = year or ''
        self.composer = util.de_listify(composer or '')
        self.genre = util.de_listify(genre or '')
        self.time = time

    def __str__(self):
        return 'Item: %s' % self.name

    def __unicode__(self):
        return u'Item: %s' % self.name

    def serialize_to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'artist': self.artist.serialize_to_json(),
            'album': self.album.serialize_to_json(),
            'track': self.track,
            'year': self.year,
            'composer': self.composer,
            'genre': self.genre,
            'time': self.time,
        }

    @property_getter('dmap.itemname')
    def get_name(self):
        return self.name

    @property_getter('dmap.containeritemid')
    @property_getter('dmap.itemid')
    @property_getter('dmap.persistentid')
    def get_id(self):
        return self.id

    @property_getter('dmap.itemkind')
    def get_item_kind(self):
        return self.item_kind

    @property_getter('daap.songalbum')
    def get_album_name(self):
        return self.album.name

    @property_getter('daap.songalbumid')
    def get_album_id(self):
        return self.album.id

    @property_getter('daap.songartist')
    def get_artist(self):
        return self.artist.name

    @property_getter('daap.songartistid')
    def get_artist_id(self):
        return self.artist.id

    @property_getter('daap.songcontentdescription')
    def get_content_description(self):
        return self.content_description

    @property_getter('com.apple.itunes.has-video')
    def get_has_video(self):
        return self.has_video

    @property_getter('daap.songcomposer')
    def get_composer(self):
        return self.composer

    @property_getter('daap.songyear')
    def get_year(self):
        return self.year

    @property_getter('daap.songgenre')
    def get_genre(self):
        return self.genre

    @property_getter('daap.songtime')
    def get_time(self):
        return self.time

class IndexedCollection(object):
    def __init__(self, cls):
        if not issubclass(cls, PropertyMixin):
            raise TypeError('Can only index classes implementing PropertyMixin')

        self._cls = cls
        self._items = []
        self.indexes = {}
        self.ids = set()

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        for item in self._items:
            yield item

    def add_new(self, **kwargs):
        if 'id' not in kwargs:
            kwargs['id'] = len(self)
        return self.add_item(self._cls(**kwargs))

    def add_item(self, item):
        list_index = len(self)
        self.ids.add(list_index)
        self._items.append(item)
        for (prop, value) in item.enumerate_properties():
            if (prop not in self.indexes):
                self.indexes[prop] = {}
            if (value not in self.indexes[prop]):
                self.indexes[prop][value] = []
            self.indexes[prop][value].append(list_index)
        return item

    def query(self, querystring):
        return (self._items[x] for x in query.parse_query_string(querystring)(self))

    def get_by_id(self, id):
        return self.first({'dmap.itemid': id})

    def get(self, props):
        ids = []
        for (prop, value) in props.iteritems():
            if prop in self.indexes and value in self.indexes[prop]:
                ids.extend(self.indexes[prop][value])
        return (self._items[x] for x in ids)

    def first(self, props):
        l = list(self.get(props))
        if len(l) > 0:
            return l[0]
        return None

class MPDIdler(threading.Thread, MPDMixin):
    def __init__(self, subsystems, host, port, password=None):
        threading.Thread.__init__(self)
        MPDMixin.__init__(self, host, port, password)
        self.daemon = True
        self.subsystems = subsystems

        self._callback_lock = threading.Lock()
        self._callbacks = []
        self._done = False

    def register_callback(self, callback):
        with self._callback_lock:
            self._callbacks.append(callback)

    def unregister_callback(self, callback):
        with self._callback_lock:
            self._callbacks.remove(callback)

    def stop(self):
        self._done = True

    def run(self):
        while not self._done:
            self.execute('idle', self.subsystems)
            with self._callback_lock:
                for callback in self._callbacks:
                    callback()

class MPD(PropertyMixin, MPDMixin):
    def __init__(self, host, port, password=None):
        if not hasattr(self.__class__, '_instance'):
            MPD._instance = self
        MPDMixin.__init__(self, host, port, password)

        self.server_name = self._get_server_name()

        self._status_idler = MPDIdler('playlist, player, options, mixer', host, port, password)
        self._status_idler.register_callback(self._update_event)
        self._status_idler.start()

        self._db_idler = MPDIdler('database', host, port, password)
        self._db_idler.register_callback(self.update_db)
        self._db_idler.start()

        self.revision_number = 1
        self._update_callbacks = {}
        self._update_callbacks_lock = threading.Lock()

        self.update_db()

    @classmethod
    def instance(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance

    def _get_server_name(self):
        hostname = socket.getfqdn(self.host)
        if hostname == 'localhost':
            hostname = socket.getfqdn()
        return SERVER_NAME % hostname

    def register_update_callback(self, callback, revno):
        if revno <= self.revision_number:
            return callback()
        if revno not in self._update_callbacks:
            self._update_callbacks[revno] = []
        self._update_callbacks[revno].append(callback)

    def _update_event(self):
        self.revision_number += 1
        try:
            with self._update_callbacks_lock:
                callbacks = self._update_callbacks[self.revision_number]
                for callback in callbacks:
                    callback()
                del self._update_callbacks[self.revision_number]
        except KeyError:
            pass

    def _update_playlists(self):
        self.containers = IndexedCollection(Container)
        playlists = [p['playlist'] for p in self.execute('listplaylists') if 'playlist' in p and p['playlist']]
        playlists.sort()

        self.root_playlist = self.containers.add_new(name=constants.BASE_PLAYLIST, is_base=True)

        for p in playlists:
            self.containers.add_new(name=p)

    def _update_artists(self):
        self.artists = IndexedCollection(Artist)
        for n in (x for x in util.sort_by_initial(self.execute('list', 'artist')) if x):
            self.artists.add_new(name=n)

    def _update_albums(self):
        self.albums = IndexedCollection(Album)
        for a in self.artists:
            for n in (x for x in self.execute('list', 'album', 'artist', a.name) if x):
                self.albums.add_new(name=n, artist=a.name)

    def _update_items(self):
        self.items = IndexedCollection(Item)
        for i in (x for x in self.execute('listallinfo', '') if 'title' in x):
            try:
                track = int(str(i['track']).split('/')[0])
            except KeyError:
                track = 1

            self.items.add_new(
                name = i.get('title', ''),
                uri = i.get('file', ''),
                artist = i.get('artist', ''),
                album = i.get('album', ''),
                time = int(i.get('time', 0)),
                composer = i.get('composer', ''),
                genre = i.get('genre', ''),
                year = i.get('date', ''),
                track = track)


    def update_db(self):
        self._update_artists()
        self._update_albums()
        self._update_items()
        self._update_playlists()

    def root_playlist(self):
        return self.root_playlist

    def create_playlist(self, name):
        self.execute('save', name)
        self.execute('playlistclear', name)
        return self.containers.add_new(name=name, is_base=False)

    def delete_playlist(self, name):
        self.execute('rm', name)

    def load_playlist(self, name):
        self.execute('load', name)

    def clear_current(self):
        self.execute('clear')

    def add_to_current(self, uri):
        self.execute('add', uri)

    def toggle_play(self):
        if self.get_player_state() == constants.PLAYER_STATE_PLAYING:
            self.pause()
        else:
            self.play()

    def pause(self):
        self.execute('pause')

    def play(self, pos=None):
        if pos is None:
            self.execute('play')
        else:
            self.execute('play', pos)

    def prev(self):
        self.execute('previous')

    def next(self):
        self.execute('next')

    @property_setter('dacp.playingtime')
    def seek(self, value):
        try:
            songnum = self.execute('status')['song']
            self.execute('seek', songnum, int(int(value) / 1000))
        except KeyError:
            pass

    @property_getter('dacp.nowplaying')
    def get_nowplaying_info(self):
        rootpl_id = 25
        album_id = 50
        song_id = 75
        return (1, rootpl_id, album_id, song_id)

    @property_getter('dacp.playerstate')
    def get_player_state(self):
        status = self.execute('status')
        try:
            return {
                'stop': constants.PLAYER_STATE_STOPPED,
                'pause': constants.PLAYER_STATE_PAUSED,
                'play': constants.PLAYER_STATE_PLAYING,
            }[status['state']]
        except KeyError:
            return PLAYER_STATE_STOPPED

    @property_getter('dacp.repeatstate')
    def get_repeat_state(self):
        status = self.execute('status')
        if status['single'] == '1':
            return constants.REPEAT_STATE_SINGLE
        elif status['repeat'] == '1':
            return constants.REPEAT_STATE_ON
        else:
            return constants.REPEAT_STATE_OFF

    @property_getter('dacp.availablerepeatstates')
    def get_available_repeat_states(self):
        return constants.AVAILABLE_REPEAT_STATES

    @property_getter('dacp.shufflestate')
    def get_shuffle_state(self):
        status = self.execute('status')
        if status['random'] == '1':
            return constants.SHUFFLE_STATE_ON
        else:
            return constants.SHUFFLE_STATE_OFF

    @property_getter('dacp.availableshufflestates')
    def get_available_shuffle_states(self):
        return constants.AVAILABLE_SHUFFLE_STATES

    @property_setter('dacp.repeatstate')
    def set_repeat_state(self, value):
        value = int(value)
        if value == constants.REPEAT_STATE_OFF:
            self.execute('repeat', 0)
        else:
            self.execute('repeat', 1)
        if value == constants.REPEAT_STATE_SINGLE:
            self.execute('single', 1)
        else:
            self.execute('single', 0)
        return value

    @property_setter('dacp.shufflestate')
    def set_shuffle_state(self, value):
        value = int(value)
        if value == constants.SHUFFLE_STATE_OFF:
            self.execute('random', 0)
        else:
            self.execute('random', 1)
        return value

    @property_getter('dacp.volumecontrollable')
    def get_volume_controllable(self):
        return constants.VOLUME_CONTROLLABLE

    @property_getter('dmcp.volume')
    def get_volume(self):
        return int(self.execute('status')['volume'])

    @property_setter('dmcp.volume')
    def set_volume(self, value):
        self.execute('setvol', str(value))

    def get_current_track(self):
        return self.execute('currentsong')

    def get_current_status(self):
        return self.execute('status')

    def get_current_time(self):
        status = self.execute('status')
        try:
            return [1000 * int(x) for x in status['time'].split(':')]
        except TypeError:
            pass
        except KeyError:
            pass
        return [0, 0]

    @property_getter('daap.songalbumid')
    def get_current_album_id(self):
        songinfo = self.execute('currentsong')
        album = self.albums.first({
            'dmap.itemname': songinfo['album'],
            'dmap.songalbumartist': songinfo['artist']
        })
        return album.id

    @property_getter('daap.songartistid')
    def get_current_artist_id(self):
        songinfo = self.execute('currentsong')
        artist = self.artists.first({
            'dmap.itemname': songinfo['artist'],
        })
        return artist.id

    def get_current_item(self):
        songinfo = self.execute('currentsong')
        return self.items.first({
            'dmap.itemname': songinfo['title'],
            'dmap.songartist': songinfo['artist'],
            'dmap.songalbum': songinfo['album'],
        })

    def get_current_playlist(self):
        return (
            self.items.first({
                'dmap.itemname': x['title'],
                'dmap.songartist': x['artist'],
                'dmap.songalbum': x['album'],
            }) for x in self.execute('playlistinfo'))

