import socket
import threading

from euphony import util, mpdclient
from euphony.config import current as config
from euphony.db import db
from euphony.dacp.constants import *

__all__ = ['MPD', 'Container', 'Album', 'Artist', 'mpd']

SERVER_NAME = u'MPD@%s'

class InvalidItemError(ValueError):
    pass

class PropertyMixin(object):
    gettable_properties = {}
    settable_properties = {}

    def get_property(self, name):
        try:
            prop = self.gettable_properties[name]
            if callable(prop):
                return prop()
            else:
                return prop
        except KeyError:
            return None

    def set_property(self, name, value):
        try:
            return self.settable_properties[name](value)
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
        record = db.itemcache.find_one({
            'item_type': cls.__name__.lower(),
            'id': obj_id,
        })
        if record is not None:
            return cls(**dict([(str(k), v) for (k, v) in record.iteritems()]))
        else:
            return None

    @classmethod
    def find(cls, **kwargs):
        kwargs['item_type'] = cls.__name__.lower()
        try:
            kwargs['id'] = db.itemcache.find_one(kwargs)['id']
        except TypeError:
            kwargs['id'] = 1 + db.itemcache.find({'item_type': kwargs['item_type']}).count()
            db.itemcache.insert(kwargs)
        return cls(**kwargs)


class Container(PropertyMixin, CachedIDMixin):
    def __init__(self, id, name, is_base=False, **kwargs):
        self.id = id
        self.name = name
        self.is_base = is_base

        self.gettable_properties = {
            'dmap.itemname': self.name,
            'dmap.itemcount': self.get_item_count,
            'dmap.itemid': self.id,
            'dmap.persistentid': self.id,
            'dmap.parentcontainerid': 1,
            'dmap.editcommandssupported': 3,
            'daap.baseplaylist': self.is_base,
        }

    def __str__(self):
        return 'Container: %s' % self.name

    def __unicode__(self):
        return u'Container: %s' % self.name

    def fetch_items(self):
        if self.is_base:
            items = [i for i in mpd.client.listallinfo('/')  if 'title' in i]
        else:
            items = mpd.client.listplaylistinfo(self.name)
        return [Item.find(name=i['title'], artist=i['artist'], album=i['album']) for i in items]

    def get_item_count(self):
        if self.is_base:
            return len([item for item in mpd.client.listall('/') if 'title' in item])
        else:
            return len(mpd.client.listplaylist(self.name))

class Artist(PropertyMixin, CachedIDMixin):
    def __init__(self, id, name, **kwargs):
        self.id = id
        self.name = name

        self.gettable_properties = {
            'dmap.itemname': self.name,
            'dmap.itemid': self.id,
            'dmap.persistentid': self.id,
        }

    def __str__(self):
        return 'Artist: %s' % self.name

    def __unicode__(self):
        return u'Artist: %s' % self.name

class Album(PropertyMixin, CachedIDMixin):
    def __init__(self, id, name, artist, **kwargs):
        self.id = id
        self.name = name
        self.artist = Artist.find(name=artist)

        self.gettable_properties = {
            'dmap.itemname': self.name,
            'dmap.itemid': self.id,
            'dmap.persistentid': self.id,
            'daap.songalbumartist': self.artist.name,
            'daap.songartist': self.artist.name,
            'dmap.itemcount': self.get_item_count,
        }

    def __str__(self):
        return 'Album: %s' % self.name

    def __unicode__(self):
        return u'Album: %s' % self.name

    def get_item_count(self):
            return len(mpd.client.list('title', 'album', self.name))

class Item(PropertyMixin, CachedIDMixin):
    def __init__(self, id, name, artist, album, **kwargs):
        self.id = id
        self.name = name
        self.artist = Artist.find(name=artist)
        self.album = Album.find(name=album, artist=artist)

        self.gettable_properties = {
            'dmap.itemname': self.name,
            'dmap.itemid': self.id,
            'dmap.persistentid': self.id,
            'dmap.itemkind': 2,
            'daap.songalbum': self.album.name,
            'daap.songalbumid': self.album.id,
            'daap.songartist': self.artist.name,
            'dmap.containeritemid': 1,
            'daap.songcontentdescription': '',
            'com.apple.itunes.has-video': 0,
        }

    def __str__(self):
        return 'Item: %s' % self.name

    def __unicode__(self):
        return u'Item: %s' % self.name

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

        self.gettable_properties = {
            'dmcp.volume': self.get_volume,
            'dacp.playerstate': self.get_player_state,
            'dacp.shufflestate': self.get_shuffle_state,
            'dacp.repeatstate': self.get_repeat_state,
            'dacp.availableshufflestates': 2,
            'dacp.availablerepeatstates': 2,#6,
            'dacp.volumecontrollable': 1,
            'dacp.nowplaying': self.get_nowplaying_info,
            'daap.songalbumid': self.get_current_album_id,
        }

        self.settable_properties = {
            'dmcp.volume': self.set_volume,
        }

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

    def toggle_play(self):
        if self.get_player_state() == PLAYER_STATE_PLAYING:
            self.pause()
        else:
            self.play()

    def pause(self):
        self.client.pause()

    def play(self):
        self.client.play()

    def get_nowplaying_info(self):
        rootpl_id = 25
        album_id = 50
        song_id = 75
        return (1, rootpl_id, album_id, song_id)

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

    def get_repeat_state(self):
        status = self.client.status()
        if status['single'] == '1':
            return REPEAT_STATE_SINGLE
        elif status['repeat'] == '1':
            return REPEAT_STATE_ON
        else:
            return REPEAT_STATE_OFF

    def get_shuffle_state(self):
        status = self.client.status()
        if status['random'] == '1':
            return SHUFFLE_STATE_ON
        else:
            return SHUFFLE_STATE_OFF

    def get_volume(self):
        return int(self.client.status()['volume'])

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

    def get_current_album_id(self):
        songinfo = self.client.currentsong()
        return Album.find(name=songinfo['title'], artist=songinfo['artist']).id

    def get_containers(self):
        playlists = [p['playlist'] for p in self.client.listplaylists()]
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

    def get_album_by_id(self, album_id):
        record = db.itemcache.find_one({'item_type': 'album', 'id': album_id})
        if record is None:
            raise InvalidItemError()
        else:
            return Album.find(name=record['name'], artist=record['artist'])

mpd = MPD(str(config.mpd.host), int(config.mpd.port))
