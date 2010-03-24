from pymongo import Connection

from euphony.config import current as config

__all__ = ['db']

conn = Connection(config.db.host, int(config.db.port))
db = conn[config.db.name]