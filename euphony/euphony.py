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

import logging
import os.path
import random
import socket

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application

import constants
import dacpy
import handlers
import zeroconf

from config import current as config

class EuphonyServer(object):
    def __init__(self):
        self.mdns = None
        self.remote_listener = dacpy.pairing.TouchRemoteListener()
        self.player_service = None

        settings = {
            'static_path': os.path.join(os.path.dirname(__file__), 'static'),
        }

        self.wsgi_app = Application([
            # WEB
            (r'/web/status/?', handlers.web.StatusDashboardHandler),
            (r'/web/status/json', handlers.web.CurrentStatusJsonHandler),
            (r'/web/albumart/([0-9]+)x([0-9]+)/nowplaying', handlers.web.NowPlayingArtHandler),
            (r'/web/pairing/?', handlers.web.PairingHandler),
            (r'/web/pairing/remotes', handlers.web.ListRemotesHandler),

            # DMAP
            (r'/server-info', handlers.dmap.ServerInfoHandler),
            (r'/login', handlers.dmap.LoginHandler),
            (r'/update', handlers.dmap.UpdateHandler),
            (r'/databases', handlers.dmap.DatabaseHandler),
            (r'/databases/([0-9]+)/containers', handlers.dmap.ContainersHandler),
            (r'/databases/([0-9]+)/containers/([0-9]+)/items', handlers.dmap.ContainerItemsHandler),
            (r'/databases/([0-9]+)/containers/([0-9]+)/edit', handlers.dmap.ContainerEditHandler),
            (r'/databases/([0-9]+)/edit', handlers.dmap.DatabaseEditHandler),
            (r'/databases/([0-9]+)/groups', handlers.dmap.GroupsHandler),
            (r'/databases/([0-9]+)/groups/([0-9]+)/extra_data/artwork', handlers.dmap.GroupArtHandler),
            (r'/databases/([0-9]+)/browse/artists', handlers.dmap.BrowseArtistHandler),
            (r'/ctrl-int', handlers.dmap.ControlInterfaceHandler),
            (r'/ctrl-int/1/cue', handlers.dmap.CueHandler),
            (r'/ctrl-int/1/getspeakers', handlers.dmap.GetSpeakerHandler),
            (r'/ctrl-int/1/getproperty', handlers.dmap.GetPropertyHandler),
            (r'/ctrl-int/1/setproperty', handlers.dmap.SetPropertyHandler),
            (r'/ctrl-int/1/playstatusupdate', handlers.dmap.PlayStatusUpdateHandler),
            (r'/ctrl-int/1/nowplayingartwork', handlers.dmap.NowPlayingArtHandler),
            (r'/ctrl-int/1/playspec', handlers.dmap.PlaySpecHandler),
            (r'/ctrl-int/1/playpause', handlers.dmap.PlayPauseHandler),
            (r'/ctrl-int/1/pause', handlers.dmap.PauseHandler),
            (r'/ctrl-int/1/nextitem', handlers.dmap.NextItemHandler),
            (r'/ctrl-int/1/previtem', handlers.dmap.PrevItemHandler),
        ], **settings)

    @classmethod
    def instance(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance

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

def start_app(argv):
    import sys
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-v', '--verbose',
                      action='store_true',
                      dest='verbose',
                      help='Spam the log with lots of information',
                      default=False)
    parser.add_option('-d', '--debug',
                      action='store_true',
                      dest='debug',
                      help='Log debug information',
                      default=False)
    parser.add_option('-s', '--stdout',
                      action='store_true',
                      dest='stdout',
                      help='Log to stdout instead of a file',
                      default=False)


    (options, args) = parser.parse_args(argv)

    logger = logging.getLogger()

    if options.debug:
        logger.setLevel(logging.DEBUG)
    elif options.verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    if not options.stdout:
        sys.stdout = sys.stderr = open(config.logging.filename, 'w')

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    app = EuphonyServer.instance()
    http_server = HTTPServer(app.wsgi_app)
    http_server.listen(int(config.server.port), str(config.server.host))
    app.start_zeroconf()
    logging.info('Server starting on %s:%d...' % (str(config.server.host), int(config.server.port)))
    IOLoop.instance().start()

def stop_app():
    EuphonyServer.instance().stop_zeroconf()
    IOLoop.instance().stop()
    logging.info('Server stopped.')
    logging.shutdown()
