import os.path

from ConfigParser import SafeConfigParser

__all__ = ['current', 'ConfigSet']

class Section:
    def __init__(self, cfg, section):
        self._items = dict(cfg.items(section))

    def __getitem__(self, key):
        return self._items[key]

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError('Invalid key: %r' % name)

class ConfigSet:
    def __init__(self, inifile):
        cfg = SafeConfigParser()
        cfg.read(inifile)

        self._sections = dict([(s, Section(cfg, s)) for s in cfg.sections()])

    def __getitem__(self, key):
        return self._sections[key]

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError('Invalid section: %r' % name)

basepath = os.path.dirname(os.path.abspath(__file__))
current = ConfigSet(os.path.join(basepath, 'config.ini'))
