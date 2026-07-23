import logging
import threading
import datetime
from abc import abstractmethod
from .updater import Updater, UpdateFrequency

from typing import Any, Callable, Optional, List

class RateLimitError(Exception):
    def __init__(self, frequency: UpdateFrequency, allowed_calls: int):
        super().__init__(f"Rate limited - {allowed_calls} allowed in {frequency.interval} seconds")


class RateLimiter(Updater):

    def __init__(self, frequency: UpdateFrequency, num_calls_allowed: int, callbacks: Optional[List[Callable[[], None]]] = None) -> None:
        super().__init__(frequency)
        self._allowed_calls = num_calls_allowed
        self._num_ticks = 0
        self._latest_reset_time = datetime.datetime.now()
        self.callbacks: List[Callable[[], None]] = []
        if callbacks:
            for callback in callbacks:
                self.callbacks.append(callback)

    def add_callback(self, callback: Callable[[], None]) -> None:
        self.callbacks.append(callback)

    def tick(self) -> None:
        """
        This will be called explicitly to try and make updates
        """
        self._update_rate()
        self._perform_tick_update()

    def update(self) -> None:
        """
        This will be called by the timer and be invoked in the background automatically
        """
        self._num_ticks = 0
        self._latest_reset_time = datetime.datetime.now()

    @abstractmethod
    def _perform_tick_update(self) -> None:
        pass

    def _invoke_update(self) -> None:
        self._is_updating = True
        for callback in self.callbacks:
            callback()
        self.update()
        self._is_updating = False

    def _update_rate(self) -> None:
        if self._num_ticks + 1 > self._allowed_calls:
            raise RateLimitError(self.frequency, self._allowed_calls)
        self._num_ticks += 1

    @property
    def next_reset(self) -> datetime.datetime:
        return self._latest_reset_time + datetime.timedelta(seconds=self.frequency.interval)
    
    @property
    def seconds_to_next_update(self) -> float:
        return (self.next_reset - datetime.datetime.now()).total_seconds()
    

if __name__ == "__main__":

    rl = RateLimiter(UpdateFrequency(seconds=1), 1)
