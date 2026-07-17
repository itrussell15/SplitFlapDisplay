import logging
import threading
import datetime

from typing import Any, Callable, Optional

class RateLimitNotSetError(Exception):
    pass


class RateLimiter:
    def __init__(self, minutes: int, seconds: int) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._minutes = int(minutes)
        self._seconds = int(seconds)
        
        self.set_rate(minutes, seconds)
        self._current_time: Optional[datetime.datetime] = None
        self._target: Optional[datetime.datetime] = datetime.datetime.now()
        self._callback = None
        self._callback_thread = None

    def set_rate(self, minutes: int, seconds: int) -> None:
        self._minutes = minutes
        self._seconds = seconds
        self._rate = datetime.timedelta(minutes=self._minutes, seconds=self._seconds)

    def add_callback(self, callback: Callable[[Any], None]) -> None:
        if self._callback is not None:
            self.logger.warning("Overwritting previous callback")
        self._callback = callback

    def update(self) -> None:
        # TODO Add check to see if we are already waiting for another update
        self._current_time = datetime.datetime.now()
        self._target = self._current_time + self._rate
        if self._callback is not None:
            self._callback_thread = threading.Thread(target=self._worker, args=(self._callback,), daemon=True)
            self._callback_thread.start()

    def check(self) -> bool:
        if self._target is None:
            raise RateLimitNotSetError("Unable to check a rate limter that has been set yet")
        return datetime.datetime.now() >= self._target

    def _worker(self, callback: Callable[None, None]) -> None:
        while datetime.datetime.now() <= self._target:
            time.sleep(0.05)
        self.logger.info("Invoking callback")
        callback()

    @property
    def is_active(self) -> bool:
        return self.check()

    @property
    def rate(self) -> datetime.timedelta:
        return self._rate
    
    @property
    def target_time(self) -> datetime.datetime:
        return self._target

    @property
    def last_update(self) -> datetime.datetime:
        return self._current_time