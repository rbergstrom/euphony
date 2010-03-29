Euphony MPD-DACP Interface
==========================

Euphony is a simple interface to allow DACP clients (such as the Remote app
for the iPhone/iPod Touch) to control MPD servers. The objective of the
project was to provide a relatively transparent interface, with a minimal
amount of maintenance or set-up work involved.

Installation and Dependencies
-----------------------------

Simply run euphony.py to run the server in a terminal, or run_daemon.py to
start a daemon process.

Euphony currently has several dependencies:

* [Tornado][tornado] - Provides the web framework and HTTP server.
* [MongoDB][mongodb] and [PyMongo][pymongo] - Stores pairing codes and cover art.
* [Python Imaging Library][pil] - For resizing and converting album art.
* [Numpy][numpy] - Needed to generate the pairing code currently (on the list to remove).
* [lxml][lxml] - Parsing XML to fetch album art (on the list to fix - replace it with xml.etree).
* [python-daemon][pydaemon] - Used to daemonize the process. Only needed for run_daemon.py.

Everything else is either included (Zeroconf and MPDClient), or in the standard
Python library.

  [tornado]: http://www.tornadoweb.org/
  [mongodb]: http://www.mongodb.org/
  [pymongo]: http://pypi.python.org/pypi/pymongo/
  [pil]: http://www.pythonware.com/products/pil/
  [numpy]: http://numpy.scipy.org/
  [lxml]: http://codespeak.net/lxml/
  [pydaemon]: http://pypi.python.org/pypi/python-daemon/

Thanks and Credits
------------------

Thanks to Jeffrey Sharkey for [his work on decoding DACP][sharkey]. It proved
invaluable during work on Euphony.

Additional credit to the overview of the [DAAP protocol][tapjam] on tapjam.net,
which provided a lot of information on the tag-name mappings iTunes uses.

  [sharkey]: http://dacp.jsharkey.org/
  [tapjam]: http://www.tapjam.net/daap/

Licence (MIT)
-------------

    Copyright (c) 2010 Ryan Bergstrom

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE SOFTWARE.
