"""Locks retained only while a cache key has active users (process-local)."""

from contextlib import contextmanager
from functools import wraps
from threading import RLock


class KeyLocks:
    def __init__(self):
        self.guard = RLock()
        self.entries = {}

    @contextmanager
    def hold(self, key):
        with self.guard:
            lock, users = self.entries.get(key, (RLock(), 0))
            self.entries[key] = (lock, users + 1)
        try:
            with lock:
                yield
        finally:
            with self.guard:
                _, users = self.entries[key]
                if users == 1:
                    del self.entries[key]
                else:
                    self.entries[key] = (lock, users - 1)


def synchronized(lock):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            with lock:
                return fn(*args, **kwargs)

        return wrapped

    return decorate
