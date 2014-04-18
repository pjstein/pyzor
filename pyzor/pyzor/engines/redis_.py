"""Redis database engine."""

import time
import Queue
import logging
import datetime
import threading

try:
    import redis
except ImportError:
    redis = None

from pyzor.engines.common import *

encode_date = lambda d: "" if d is None else d.strftime("%Y-%m-%d %H:%M:%S.%f")
decode_date = lambda x: None if x == "" else datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f")

class RedisDBHandle(object):
    absolute_source = False

    log = logging.getLogger("pyzord")

    def __init__(self, fn, mode, max_age=None):
        self.max_age = max_age
        # The 'fn' is host,port,password,db.  We ignore mode.
        # We store the authentication details so that we can reconnect if
        # necessary.
        fn = fn.split(",")
        self.host = fn[0] or "localhost"
        self.port = fn[1] or "6379"
        self.passwd = fn[2] or None
        self.db_name = fn[3] or "0"
        self.db = self._get_new_connection()


    def _encode_record(self, r):
        return ("%s,%s,%s,%s,%s,%s" %
                (r.r_count,
                 encode_date(r.r_entered),
                 encode_date(r.r_updated),
                 r.wl_count,
                 encode_date(r.wl_entered),
                 encode_date(r.wl_updated)))

    def _decode_record(self, r):
        if r is None:
            return Record()
        fields = r.split(",")
        return Record(r_count=int(fields[0]),
                      r_entered=decode_date(fields[1]),
                      r_updated=decode_date(fields[2]),
                      wl_count=int(fields[3]),
                      wl_entered=decode_date(fields[4]),
                      wl_updated=decode_date(fields[5]))

    def _get_new_connection(self):
        return redis.StrictRedis(host=self.host, port=self.port,
                                 db=self.db_name, password=self.passwd)

    def __getitem__(self, key):
        return self._decode_record(self.db.get(key))

    def __setitem__(self, key, value):
        if self.max_age is None:
            self.db.set(key, self._encode_record(value))
        else:
            self.db.setex(key, self.max_age, self._encode_record(value))

    def __delitem__(self, key):
        self.db.delete(key)
        
class ThreadedRedisDBHandle(RedisDBHandle):
    
    def __init__(self, fn, mode, max_age=None, bound=None):
        RedisDBHandle.__init__(self, fn, mode, max_age=max_age)


if redis is None:
    handle = DBHandle(single_threaded=None,
                      multi_threaded=None,
                      multi_processing=None)
else:
    handle = DBHandle(single_threaded=RedisDBHandle,
                      multi_threaded=ThreadedRedisDBHandle,
                      multi_processing=None)