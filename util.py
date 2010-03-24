import random
import string
import datetime
import re

__all__ = ['generate_sessionid', 'build_sort_headers', 'sort_by_initial']

SORT_LAST = 'ZZZ'
SORT_DIGIT = '0'
PREFIXES = ('THE ', 'AN ', 'A ')

def generate_sessionid(guid, n=32):
    """ Generates a completely insecure but adequate session id """
    sid = 0
    for i in range(n):
        sid ^= random.randint(0, 0x7fffffff)
    return sid

def get_initial(name):
    name = name.upper()
    for p in PREFIXES:
        if name.startswith(p):
            name = name[len(p):]
    name = name.strip(string.punctuation)
    try:
        if name[0] in string.digits:
            return SORT_LAST
        elif name[0] in string.uppercase:
            return name[0]
        else:
            return ''
    except IndexError:
        return ''

def sort_by_initial(names, key=None):
    if key is not None and callable(key):
        names.sort(key=lambda x: ('%s %s' % (get_initial(key(x)), key(x))))
    else:
        names.sort(key=lambda x: ('%s %s' % (get_initial(x), x)))
    return names

def build_sort_headers(names):
    nlist = sort_by_initial(names)

    result = {}
    index = 0
    for name in nlist:
        initial = get_initial(name)
        if initial in result:
            result[initial][2] += 1
        else:
            if initial == SORT_LAST:
                result[initial] = [ord(SORT_DIGIT), index, 1]
            else:
                result[initial] = [ord(initial), index, 1]
        index += 1

    keys = result.keys()
    keys.sort()
    return [tuple(result[k]) for k in keys]

def get_tz_offset():
    now = datetime.datetime.now()
    utc = datetime.datetime.utcnow()
    return 3600 * (now.hour - utc.hour)

def clean_name(name):
    return re.sub(r'(?u)([\W_]+)', '', name.lower())
