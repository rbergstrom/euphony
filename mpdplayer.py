import socket
import threading
import collections

from euphony import util, mpdclient
from euphony.config import current as config
from euphony.dacp.constants import *

__all__ = ['MPD', 'Container', 'Album', 'Artist', 'mpd']

SERVER_NAME = u'MPD@%s'

itemcache = {}

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
            func.prop_name = self.prop_name
        return func

class PropertyMeta(type):
    def __init__(cls, name, bases, attrs):
        props = collections.defaultdict(dict)
        for (k, v) in attrs.iteritems():
            if hasattr(v, 'prop_name') and hasattr(v, 'prop_type'):
                for n in v.prop_name:
                    props[v.prop_type][n] = v
        cls._properties = props

class PropertyMixin(object):
    __metaclass__ = PropertyMeta

    def get_property(self, name):
        try:
            return self._properties['get'][name](self)
        except KeyError:
            return None

    def set_property(self, name, value):
        try:
            return self._properties['set'][name](value)
        except KeyError:
            return None

class MPDMixin(object):
    def __init__(self, host, port, password=None):
        self.client = mpdclient.MPDClient()

        self.host = host
        self.port = port
        self.password = password

    def connect(self):
        self.client.connect(self.host, self.port)
        if self.password is not None:
            self.client.password(self.password)

class CachedIDMixin(object):
    @classmethod
    def get(cls, obj_id):
        try:
            record = itemcache[cls.__name__.lower()][obj_id]
            return cls(id=obj_id, **record)
        except KeyError:
            return None

    @classmethod
    def find(cls, **kwargs):
        itemtype = cls.__name__.lower()
        try:
            for (k, v) in itemcache[itemtype].iteritems():
                if v == kwargs:
                    return cls(id=k, **kwargs)
        except KeyError:
            pass

        if itemtype not in itemcache:
            itemcache[itemtype] = {}

        obj_id = 1 + len(itemcache[itemtype])
        itemcache[itemtype][obj_id] = kwargs

        return cls(id=obj_id, **kwargs)

class Container(PropertyMixin, CachedIDMixin):
    def __init__(self, id, name, is_base=False, **kwargs):
        self.id = id
        self.name = name
        self.is_base = is_base

        # this MUST be zero for the remote to "see" the playlist
        self.parent_container_id = 0

    def __str__(self):
        return 'Container: %s' % self.name

    def __unicode__(self):
        return u'Container: %s' % self.name

    def add_item(self, item):
        mpd.client.playlistadd(self.name, item.uri)

    def fetch_items(self):
        if self.is_base:
            items = [i for i in mpd.client.listallinfo('/')  if 'title' in i]
        else:
            items = [i for i in mpd.client.listplaylistinfo(self.name) if 'title' in i]
        return [Item.find(name=i['title'], artist=i['artist'], album=i['album'], uri=i['file']) for i in items]

    @property_getter('dmap.itemname')
    def get_name(self):
        return self.name

    @property_getter('dmap.itemid')
    @property_getter('dmap.persistentid')
    def get_id(self):
        return self.id

    @property_getter('dmap.itemcount')
    def get_item_count(self):
        if self.is_base:
            return len([item for item in mpd.client.listall('/') if 'file' in item])
        else:
            return len(mpd.client.listplaylist(self.name))

    @property_getter('dmap.parentcontainerid')
    def get_parent_container_id(self):
        return self.parent_container_id

    @property_getter('dmap.editcommandssupported')
    def get_editable(self):
        return not self.is_base

    @property_getter('daap.baseplaylist')
    def get_is_base_playlist(self):
        return self.is_base


class Artist(PropertyMixin, CachedIDMixin):
    def __init__(self, id, name, **kwargs):
        self.id = id
        self.name = name

    def __str__(self):
        return 'Artist: %s' % self.name

    def __unicode__(self):
        return u'Artist: %s' % self.name

    @property_getter('dmap.itemname')
    def get_name(self):
        return self.name

    @property_getter('dmap.itemid')
    @property_getter('dmap.persistentid')
    def get_id(self):
        return self.id

class Album(PropertyMixin, CachedIDMixin):
    def __init__(self, id, name, artist, **kwargs):
        self.id = id
        self.name = name
        self.artist = Artist.find(name=artist)

    def __str__(self):
        return 'Album: %s' % self.name

    def __unicode__(self):
        return u'Album: %s' % self.name

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
        return self.artist.name,

    @property_getter('dmap.itemcount')
    def get_item_count(self):
            return len(mpd.client.list('title', 'album', self.name))

class Item(PropertyMixin, CachedIDMixin):
    def __init__(self, id, name, artist, album, uri, **kwargs):
        self.id = id
        self.name = name
        self.uri = uri
        self.artist = Artist.find(name=artist)
        self.album = Album.find(name=album, artist=artist)
        self.item_kind = 2
        self.container_id = 1
        self.content_description = ''
        self.has_video = 0

    def __str__(self):
        return 'Item: %s' % self.name

    def __unicode__(self):
        return u'Item: %s' % self.name

    @property_getter('dmap.itemname')
    def get_name(self):
        return self.name

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

    @property_getter('dmap.containeritemid')
    def get_container_id(self):
        return self.container_id

    @property_getter('daap.songcontentdescription')
    def get_content_description(self):
        return self.content_description

    @property_getter('com.apple.itunes.has-video')
    def get_has_video(self):
        return self.has_video

class MPDIdler(threading.Thread, MPDMixin):
    def __init__(self, host, port, password=None):
        threading.Thread.__init__(self)
        MPDMixin.__init__(self, host, port, password)
        self.daemon = True

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
        self.disconnect()

    def run(self):
        self.connect()
        while not self._done:
            self.client.idle('playlist, player, options, mixer')
            with self._callback_lock:
                for callback in self._callbacks:
                    callback()


class MPD(PropertyMixin, MPDMixin):
    client = None

    def __init__(self, host, port, password=None):
        MPDMixin.__init__(self, host, port, password)

        self.server_name = self._get_server_name()

        self.revision_number = 1
        self._update_callbacks = {}
        self._update_callbacks_lock = threading.Lock()

        self.idler = MPDIdler(host, port, password)
        self.idler.register_callback(self._update_event)
        self.idler.start()

        self.connect()

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

    def create_playlist(self, name):
        self.client.save(name)
        self.client.playlistclear(name)
        return Container.find(name=name, is_base=False)

    def delete_playlist(self, name):
        self.client.rm(name)

    def toggle_play(self):
        if self.get_player_state() == PLAYER_STATE_PLAYING:
            self.pause()
        else:
            self.play()

    def pause(self):
        self.client.pause()

    def play(self):
        self.client.play()

    def prev(self):
        self.client.previous()

    def next(self):
        self.client.next()

    @property_getter('dacp.nowplaying')
    def get_nowplaying_info(self):
        rootpl_id = 25
        album_id = 50
        song_id = 75
        return (1, rootpl_id, album_id, song_id)

    @property_getter('dacp.playerstate')
    def get_player_state(self):
        status = self.client.status()
        try:
            return {
                'stop': PLAYER_STATE_STOPPED,
                'pause': PLAYER_STATE_PAUSED,
                'play': PLAYER_STATE_PLAYING,
            }[status['state']]
        except KeyError:
            return PLAYER_STATE_STOPPED

    @property_getter('dacp.repeatstate')
    def get_repeat_state(self):
        status = self.client.status()
        if status['single'] == '1':
            return REPEAT_STATE_SINGLE
        elif status['repeat'] == '1':
            return REPEAT_STATE_ON
        else:
            return REPEAT_STATE_OFF

    @property_getter('dacp.availablerepeatstates')
    def get_available_repeat_states(self):
        return AVAILABLE_REPEAT_STATES

    @property_getter('dacp.shufflestate')
    def get_shuffle_state(self):
        status = self.client.status()
        if status['random'] == '1':
            return SHUFFLE_STATE_ON
        else:
            return SHUFFLE_STATE_OFF

    @property_getter('dacp.availableshufflestates')
    def get_available_shuffle_states(self):
        return AVAILABLE_SHUFFLE_STATES

    @property_getter('dacp.volumecontrollable')
    def get_volume_controllable(self):
        return VOLUME_CONTROLLABLE

    @property_getter('dmcp.volume')
    def get_volume(self):
        return int(self.client.status()['volume'])

    @property_setter('dmcp.volume')
    def set_volume(self, value):
        self.client.setvol(str(value))

    def get_current_track(self):
        return self.client.currentsong()

    def get_current_time(self):
        status = self.client.status()
        try:
            return [1000 * int(x) for x in status['time'].split(':')]
        except TypeError:
            return (0, 0)

    @property_getter('daap.songalbumid')
    def get_current_album_id(self):
        songinfo = self.client.currentsong()
        return Album.find(name=songinfo['title'], artist=songinfo['artist']).id

    def get_containers(self):
        playlists = [p['playlist'] for p in self.client.listplaylists() if 'playlist' in p]
        playlists.sort()
        root = Container.find(name=BASE_PLAYLIST, is_base=True)
        return [root] + [Container.find(name=p, is_base=False) for p in playlists if p]

    def get_artists(self):
        artists = util.sort_by_initial(self.client.list('artist'))
        return [Artist.find(name=a) for a in artists if a]

    def get_albums(self):
        artists = self.get_artists()
        albums = []
        for a in artists:
            albums.extend([
                Album.find(name=n, artist=a.name) for n in self.client.list('album', 'artist', a.name) if n
            ])

        return util.sort_by_initial(albums, key=lambda x: x.name)

mpd = MPD(str(config.mpd.host), int(config.mpd.port))
