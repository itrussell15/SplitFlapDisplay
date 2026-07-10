import logging
import threading
import datetime
from abc import ABC, abstractmethod

from typing import Optional

class UpdateFrequency:
    def __init__(self, minutes: int = 0, seconds: int = 0) -> None:
        self._minutes = minutes
        self._seconds = seconds

        self.minutes = minutes
        self.seconds = seconds

    def _check_valid_update(self, minutes: int, seconds: int) -> None:
        if seconds == 0 and minutes == 0:
            raise ValueError("Invalid update frequency of 0 seconds and 0 minutes")

        if seconds < 0 or minutes < 0:
            raise ValueError(f"Invalid update frequency - values must be greater than 0, not minutes: {minutes} seconds: {seconds}")

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


class Updater(ABC):

    def __init__(self, update_frequency: Optional[UpdateFrequency] = None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._frequency = update_frequency
        self._timer = None

    @abstractmethod
    def update(self) -> None:
        pass

    def start(self) -> None:
        if self._timer is not None:
            raise RuntimeError("Can not start another updater with one running. Please stop it and try again")

        # First update on startup
        self.update()

        if self.frequency is None:
            self.logger.info("No frequency is set - Invoking update once only")
            return 

        # Kick off remaining updates on a schedule
        self._schedule_timer()
        self.logger.info("Updater started")

    def _schedule_timer(self) -> None:
        # Don't update if we don't have a dynamic updater
        if not self.is_dynamic:
            return

        self._timer = threading.Timer(interval=self.frequency.interval, function=self._run_update)
        self._timer.start()

    def _run_update(self) -> None:
        # If we are here, then the timer has completed and we want to start another one.
        self.update()
        if self._timer is not None:
            self._schedule_timer()

    def stop(self) -> None:
        if self._timer is None:
            self.logger.warning("No updater started - unable to stop one")
            return
        self.logger.info("Updater stopped")
        self._timer.cancel()
        self._timer = None

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