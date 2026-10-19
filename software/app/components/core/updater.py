import time
import logging
import threading
import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod

from typing import Optional

class UpdateFrequency:
    def __init__(self, minutes: int = 0, seconds: int = 0) -> None:
        self._minutes = minutes
        self._seconds = seconds

        self.minutes = minutes
        self.seconds = seconds

    def __repr__(self) -> str:
        return f"UpdateFrequency(mins={self.minutes}, seconds={self.seconds})"

    def _check_valid_update(self, minutes: int, seconds: int) -> None:
        if seconds == 0 and minutes == 0:
            raise ValueError("Invalid update frequency of 0 seconds and 0 minutes")

        if seconds < 0 or minutes < 0:
            raise ValueError(f"Invalid update frequency - values must be greater than 0, not minutes: {minutes} seconds: {seconds}")

    def to_dict(self) -> Dict[str, int]:
        return {
            "minutes": self.minutes,
            "seconds": self.seconds
        }

    @property
    def minutes(self) -> int:
        return self._minutes

    @minutes.setter
    def minutes(self, value: int) -> None:
        self._check_valid_update(minutes=value, seconds=self._seconds)
        self._minutes = max(0, value)

    @property
    def seconds(self) -> int:
        return self._seconds

    @seconds.setter
    def seconds(self, value: int) -> None:
        self._check_valid_update(minutes=self._minutes, seconds=value)
        self._seconds = max(0, value)

    @property
    def interval(self) -> int:
        return (self.minutes * 60)  + self.seconds


@dataclass
class TimeStatus:
    start: Optional[float]
    end: Optional[float]
    

    def __post_init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def remaining(self) -> Optional[float]:
        if self.end is None:
            self.logger.warning("No end time set. Unable to calculate time left")
            return None
            
        this_time = time.time()
        if this_time - self.end > 0.25:
            self.logger.warning("Unable to calculate time left because current time is already greater than end time")
            self.logger.warning(f"Start: {self.start} End: {self.end} - Current Time: {this_time}")
            return None

        return self.end - this_time

    @property
    def elapsed(self) -> float:
        this_time = time.time()
        if self.start is None:
            self.logger.warning("No start time set. Unable to calculate time elapsed")
            return None
            
        this_time = time.time()
        if this_time < self.start:
            self.logger.warning("Unable to calculate time elapsed because current time is less than start time")
            self.logger.warning(f"Start: {self.start} End: {self.end} - Current Time: {this_time}")
            return None

        return this_time - self.start

    def to_dict(self) -> Dict[str, float]:
        return {
            "start": self.start,
            "end": self.end,
            "remaining": self.remaining,
            "elapsed": self.elapsed
        }

class TimeBasedUpdater(ABC):

    def __init__(self, update_frequency: Optional[UpdateFrequency] = None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._frequency = update_frequency
        self._timer = None
        self._time_status: Optional[TimeStatus] = None

    @abstractmethod
    def update(self) -> None:
        pass

    def start(self, update_on_start: bool = True) -> None:
        if self._timer is not None:
            raise RuntimeError("Can not start another updater with one running. Please stop it and try again")
        
        if not self.is_dynamic:
            self._invoke_update()
            return 

        self.logger.debug("Updater started")
        # First update on startup
        if update_on_start:
            self._invoke_update()

        # Kick off remaining updates on a schedule
        self._schedule_timer()

    @abstractmethod
    def _invoke_update(self) -> None:
        pass

    def _schedule_timer(self) -> None:
        # Don't update if we don't have a dynamic updater
        if not self.is_dynamic:
            return
        self._timer = threading.Timer(interval=self.frequency.interval, function=self._worker_invoked_update)
        self._timer.start()

    def _worker_invoked_update(self) -> None:
        # If we are here, then the timer has completed and we want to start another one.
        self._top_level_update()
        if self._timer is not None:
            self._schedule_timer()
        
    def stop(self) -> None:
        if self._timer is None:
            self.logger.warning("No updater started - unable to stop one")
            return
        self.logger.info("Updater stopped")
        self._timer.cancel()
        self._timer = None
        self._time_status = None

    @property
    def frequency(self) -> Optional[UpdateFrequency]:
        return self._frequency

    @frequency.setter
    def frequency(self, value: Optional[UpdateFrequency]) -> None:
        self._frequency = value

    @property
    def is_dynamic(self) -> bool:
        return self.frequency is not None
    
    @property
    def is_alive(self) -> None:
        return self._timer is not None
    
    @property
    def time_status(self) -> Optional[TimeStatus]:
        return self._time_status

class Updater(TimeBasedUpdater):

    @abstractmethod
    def update(self) -> None:
        """
        This is the callback that gets called at the end of the timer
        """
        pass

    def _update_time_status(self) -> TimeStatus:
        return TimeStatus(start=time.time(), end=time.time() + self.frequency.interval)

    def _invoke_update(self) -> None:
        self._is_updating = True
        self.update()
        self._is_updating = False

    def _worker_invoked_update(self) -> None:
        # If we are here, then the timer has completed and we want to start another one.
        self._invoke_update()
        if self._timer is not None:
            self._schedule_timer()