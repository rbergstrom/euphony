#!/usr/bin/env python

if __name__ == '__main__':
    import sys

    from euphony import start_app, stop_app
    from config import current as config

    try:
        print('Listening on %s:%d...' % (str(config.server.host), int(config.server.port)))
        start_app(sys.argv)
    except KeyboardInterrupt:
        print('Shutting down...')
        stop_app()
