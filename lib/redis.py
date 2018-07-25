
import time

from redis.sentinel import Sentinel
from settings import redis_conf

class Redis():

    __instance = None

    def __init__(self):

        self.sentinel = self.connect()

    def connect(self):
        sentinel = Sentinel(redis_conf["redis_servers"], password=redis_conf["password"], socket_timeout=0.1)
        return sentinel

    @classmethod
    def getInstance(cls, ):
        if cls.__instance is None:
            cls.__instance = Redis()
        return cls.__instance

    def get(self, key):
        """
        :param key:
        :return:  {"referName": "BTT", "referId": "23", "loginType": "2", "loginName": "344949311@qq.com" }
        """
        try:
            slave = self.sentinel.slave_for('mymaster')
            val = slave.get(key)
            return val
        except Exception as e:
            self.sentinel = self.connect()
            return {}

    def set(self, key, value):
        """
        :param key:
        :value:  {"referName": "BTT", "referId": "23", "loginType": "2", "loginName": "344949311@qq.com" }
        """
        try:
            slave = self.sentinel.master_for('mymaster')
            slave.set(key, value)
            return True
        except Exception as e:
            self.sentinel = self.connect()
            return False

    def set_expire(self, key, time):
        """
        :param key:
        :param time:
        :return:
        """
        try:
            slave = self.sentinel.master_for('mymaster')
            slave.expire(key, time)
            return True
        except Exception as e:
            self.sentinel = self.connect()
            return False

    def getHash(self, name, key):

        try:
            slave = self.sentinel.slave_for('mymaster')
            val = slave.hget(name, key)
            return val
        except Exception as e:
            self.sentinel = self.connect()
            return {}

    def setHash(self, name, key, value):

        try:
            slave = self.sentinel.master_for('mymaster')
            val = slave.hset(name, key, value)
            return val
        except Exception as e:
            self.sentinel = self.connect()
            return {}

    def setHashExpire(self, name, time):

        try:
            slave = self.sentinel.master_for('mymaster')
            val = slave.expire(name, time)
            return val
        except Exception as e:
            self.sentinel = self.connect()
            return {}

    def producer(self, prodcons_queue, elem):
        try:
            slave = self.sentinel.master_for('mymaster')
            val = slave.lpush(prodcons_queue, elem)
            return val
        except Exception as e:
            self.sentinel = self.connect()
            return {}

    def customer(self, prodcons_queue):
        try:
            slave = self.sentinel.master_for('mymaster')
            val = slave.blpop(prodcons_queue, 0)[1]
            return val
        except Exception as e:
            self.sentinel = self.connect()
            return {}

        
    def getListLen(self, prodcons_queue):
        try:
            slave = self.sentinel.master_for('mymaster')
            val = slave.llen(prodcons_queue)
            return val
        except Exception as e:
            self.sentinel = self.connect()
            return 0

    def clear_list(self, prodcons_queue):
        try:
            slave = self.sentinel.master_for('mymaster')
            val = slave.delete(prodcons_queue)
            return val
        except Exception as e:
            self.sentinel = self.connect()
            return {}

    def cache_without_dogpiling(self, key, value="", cache_expiry=60*2, *args, **kwargs):

        slave = self.sentinel.master_for('mymaster')
        val = slave.get(key)
        if val is not None:
            return val

        # Cache miss; gain the lock to prevent multiple clients calling cb()
        with Lock(key, client=slave, *args, **kwargs):
            # Check cache again - another client may have set the cache
            val = slave.get(key)
            if val is None:
                slave.set(key, value, cache_expiry)
                return value
            return val


class Lock(object):

    def __init__(self, key, client=None, expires=60, timeout=5):
        """
        Distributed locking using Redis SETNX and GETSET.

        Usage::

            with Lock('my_lock'):
                print "Critical section"

        :param  expires     We consider any existing lock older than
                            ``expires`` seconds to be invalid in order to
                            detect crashed clients. This value must be higher
                            than it takes the critical section to execute.
        :param  timeout     If another client has already obtained the lock,
                            sleep for a maximum of ``timeout`` seconds before
                            giving up. A value of 0 means we never wait.
        """

        self.key = "%s_lock"%key
        self.timeout = timeout
        self.expires = expires
        self.client = client

    def __enter__(self):
        timeout = self.timeout
        while timeout >= 0:
            expires = time.time() + self.expires + 1

            if self.client.setnx(self.key, expires):
                # We gained the lock; enter critical section
                return

            current_value = self.client.get(self.key)

            # We found an expired lock and nobody raced us to replacing it
            if current_value and float(current_value) < time.time() and \
                self.client.getset(self.key, expires) == current_value:
                return

            timeout -= 1
            time.sleep(1)

        raise LockTimeout("Timeout whilst waiting for lock")

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.delete(self.key)

class LockTimeout(BaseException):
    pass
