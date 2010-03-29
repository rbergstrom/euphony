#!/usr/bin/env python

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
import tornado.web

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

import dacp
import handlers
import pairing
import zeroconf

from config import current as config

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
            (r'/databases/([0-9]+)/containers/([0-9]+)/edit', handlers.ContainerEditHandler),
            (r'/databases/([0-9]+)/edit', handlers.DatabaseEditHandler),
            (r'/databases/([0-9]+)/groups', handlers.GroupsHandler),
            (r'/databases/([0-9]+)/groups/([0-9]+)/extra_data/artwork', handlers.GroupArtHandler),
            (r'/databases/([0-9]+)/browse/artists', handlers.BrowseArtistHandler),
            (r'/ctrl-int', handlers.ControlInterfaceHandler),
            (r'/ctrl-int/1/cue', handlers.CueHandler),
            (r'/ctrl-int/1/getspeakers', handlers.GetSpeakerHandler),
            (r'/ctrl-int/1/getproperty', handlers.GetPropertyHandler),
            (r'/ctrl-int/1/setproperty', handlers.SetPropertyHandler),
            (r'/ctrl-int/1/playstatusupdate', handlers.PlayStatusUpdateHandler),
            (r'/ctrl-int/1/nowplayingartwork', handlers.NowPlayingArtHandler),
            (r'/ctrl-int/1/playspec', handlers.PlaySpecHandler),
            (r'/ctrl-int/1/playpause', handlers.PlayPauseHandler),
            (r'/ctrl-int/1/pause', handlers.PauseHandler),
            (r'/ctrl-int/1/nextitem', handlers.NextItemHandler),
            (r'/ctrl-int/1/previtem', handlers.PrevItemHandler),
        ])

    def start_zeroconf(self):
        self.mdns = zeroconf.Zeroconf()

        localip = socket.gethostbyname(socket.gethostname())
        self.player_service = zeroconf.ServiceInfo(
            type=dacp.MDNS_TYPE_SERVER,
            name='%s.%s' % (config.server.id, dacp.MDNS_TYPE_SERVER),
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

        self.mdns.addServiceListener(dacp.MDNS_TYPE_REMOTE, self.remote_listener)
        self.mdns.registerService(self.player_service)

    def stop_zeroconf(self):
        self.mdns.close()


app = None

def start_app():
    global app
    app = EuphonyServer()
    http_server = HTTPServer(app.wsgi_app)
    http_server.listen(int(config.server.port), str(config.server.host))

    app.start_zeroconf()
    IOLoop.instance().start()

def stop_app():
    global app
    app.stop_zeroconf()
    IOLoop.instance().stop()

if __name__ == '__main__':
    import sys

    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-v', '--verbose',
                      action='store_true',
                      dest='verbose',
                      help='Spam the log with lots of information',
                      default=False)

    (options, args) = parser.parse_args(sys.argv)

    if options.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    try:
        print('Listening on %s:%d...' % (str(config.server.host), int(config.server.port)))
        start_app()
    except KeyboardInterrupt:
        print('Shutting down...')
        stop_app()