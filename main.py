import os.path
import random
import sys
import socket
import tornado.web

sys.path = [os.path.abspath('..')] + sys.path

from euphony import zeroconf, pairing, handlers
from euphony.dacp import values, tags, constants
from euphony.db import db
from euphony.config import current as config

class EuphonyServer(object):

    def __init__(self):
        self.mdns = None
        self.remote_listener = pairing.TouchRemoteListener()
        self.player_service = None

        self.wsgi_app = tornado.web.Application([
            (r'/server-info', handlers.ServerInfoHandler),
            (r'/login', handlers.LoginHandler),
            (r'/update', handlers.UpdateHandler),
            (r'/databases', handlers.DatabaseHandler),
            (r'/databases/([0-9]+)/containers', handlers.ContainersHandler),
            (r'/databases/([0-9]+)/containers/([0-9]+)/items', handlers.ContainerItemsHandler),
            (r'/databases/([0-9]+)/groups', handlers.GroupsHandler),
            (r'/databases/([0-9]+)/groups/([0-9]+)/extra_data/artwork', handlers.GroupArtHandler),
            (r'/databases/([0-9]+)/browse/artists', handlers.BrowseArtistHandler),
            (r'/ctrl-int', handlers.ControlInterfaceHandler),
            (r'/ctrl-int/1/getspeakers', handlers.GetSpeakerHandler),
            (r'/ctrl-int/1/getproperty', handlers.GetPropertyHandler),
            (r'/ctrl-int/1/setproperty', handlers.SetPropertyHandler),
            (r'/ctrl-int/1/playstatusupdate', handlers.PlayStatusUpdateHandler),
            (r'/ctrl-int/1/nowplayingartwork', handlers.NowPlayingArtHandler),
            (r'/ctrl-int/1/playpause', handlers.PlayPauseHandler),
            (r'/ctrl-int/1/pause', handlers.PauseHandler),
        ])

    def start_zeroconf(self):
        self.mdns = zeroconf.Zeroconf()

        localip = socket.gethostbyname(socket.gethostname())
        self.player_service = zeroconf.ServiceInfo(
            type=constants.MDNS_TYPE_SERVER,
            name='%s.%s' % (config.server.id, constants.MDNS_TYPE_SERVER),
            server=socket.getfqdn(localip),
            address=socket.inet_aton(localip),
            port=3689,
            properties = {
                    'txtvers': '1',
                    'OSsi': '0x122D9F',
                    'CtlN' : str(config.server.name),
                    'Ver': '131073',
                    'DvSv': '2306',
                    'DvTy': 'iTunes',
                    'DbId': config.server.id,
            }
        )

        self.mdns.addServiceListener(constants.MDNS_TYPE_REMOTE, self.remote_listener)
        self.mdns.registerService(self.player_service)

    def stop_zeroconf(self):
        self.mdns.close()


if __name__ == '__main__':
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop
    import logging

    app = EuphonyServer()
    try:
        http_server = HTTPServer(app.wsgi_app)
        http_server.listen(int(config.server.port), str(config.server.host))

        app.start_zeroconf()
        print 'Advertising Zeroconf Service...'

        print 'Listening on %s:%d...' % (str(config.server.host), int(config.server.port))
        IOLoop.instance().start()
    except KeyboardInterrupt:
        print 'Shutting down...'
        app.stop_zeroconf()