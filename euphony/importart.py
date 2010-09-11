#!/usr/bin/env python

import base64
import os
import os.path

import db
import util

def get_mp3_info(filename):
    from mutagen.mp3 import MP3
    try:
        tags = MP3(filename).tags
        return (
            tags.getall('TPE1')[0].text[0],
            tags.getall('TALB')[0].text[0],
            tags.getall('APIC')[0].data,
        )
    except IndexError:
        return None

def get_mp4_info(filename):
    from mutagen.mp4 import MP4
    try:
        tags = MP4(filename).tags
        return (
            tags['\xa9ART'][0],
            tags['\xa9alb'][0],
            tags['covr'][0],
        )
    except IndexError:
        return None

filetypes = {
    '.mp3': get_mp3_info,
    '.mp4': get_mp4_info,
    '.m4a': get_mp4_info,
    }

def cache_path(path):
    print 'Caching %s...' % path
    done = set()
    for root, dirs, files in os.walk(path):
        for f in [os.path.join(root, x) for x in files]:
            ext = os.path.splitext(f)[1].lower()
            if ext in filetypes:
                try:
                    (artist, album, data) = filetypes[ext](f)
                    if (artist, album) not in done:
                        print u'Adding \'%s\' by \'%s\'...' % (album, artist)
                        db.AlbumArtRecord.add(artist=util.clean_name(artist),
                                              album=util.clean_name(album),
                                              data=base64.b64encode(data))
                        done.add((artist, album))
                except TypeError:
                    print u'No art for \'%s\'!' % f

def main():
    import sys

    if len(sys.argv) <= 1:
        print 'Usage: %s PATH1, PATH2...' % sys.argv[0]
        print '  - Requires at least one path to search'
        return

    for path in sys.argv[1:]:
        cache_path(path)

if __name__ == '__main__':
    main()

