"""Callback-based triggers, independent of playlists and display items."""

from abc import ABC, abstractmethod
import logging
import math
import threading
import time
from typing import Callable, Optional

from .updater import TimeStatus, UpdateFrequency


class Trigger(ABC):
    """Define when a callback may run without knowing what that callback does.

    Subclasses own the lifecycle and decide when to call ``invoke()``. A
    trigger starts inactive. Starting enables it; stopping disables it.
    Repeated starts and stops must be harmless, and a stopped trigger can
    be started again. Starting does not invoke the callback by itself.
    """

    def __init__(self, callback: Callable[[], None]) -> None:
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._callback = callback

    @abstractmethod
    def start(self) -> None:
        """Enable triggering without creating duplicate event sources."""

    @abstractmethod
    def stop(self) -> None:
        """Disable triggering and release any event source resources.

        A callback already running is allowed to finish.
        """

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Whether the trigger is enabled, even between invocations."""

    def invoke(self) -> bool:
        """Run the callback once if active; return whether it was called.

        The callback takes no arguments and runs synchronously on the
        invoking thread. Exceptions propagate to the caller. Subclasses
        that introduce background work must handle errors and coordinate
        invocations with lifecycle changes, and may skip overlapping calls.
        """
        if not self.is_active:
            return False
        self._callback()
        return True


class ManualTrigger(Trigger):
    """An explicitly invoked trigger with no timer or background worker.

    Use from one thread, including lifecycle calls. This is a simple way
    to exercise the trigger contract before adding scheduling strategies.
    """

    def __init__(self, callback: Callable[[], None]) -> None:
        super().__init__(callback)
        self._is_active = False

    def start(self) -> None:
        self._is_active = True

    def stop(self) -> None:
        self._is_active = False

    @property
    def is_active(self) -> bool:
        return self._is_active


class IntervalTrigger(Trigger):
    """Repeatedly invoke a callback using chained timers, like TimeBasedUpdater.

    ``frequency`` is an UpdateFrequency with a positive, finite interval.
    The first callback runs after one interval; the next timer starts after
    that callback ends. Frequency changes apply to the next scheduled timer.
    Callbacks never overlap, including across stop/restart. An explicit
    ``invoke()`` while a callback is running returns False.

    Stopping cancels the pending timer without waiting for a callback already
    running. Restarting during that callback waits for it to finish before
    scheduling the first interval of the new run. Background callback errors
    are logged and scheduling continues; explicit invoke() errors propagate.
    """

    def __init__(self, callback: Callable[[], None], frequency: UpdateFrequency) -> None:
        super().__init__(callback)
        if not isinstance(frequency, UpdateFrequency):
            raise TypeError("frequency must be an UpdateFrequency")
        if not math.isfinite(frequency.interval) or frequency.interval <= 0:
            raise ValueError("frequency interval must be positive and finite")
        self._frequency = frequency
        self._logger = logging.getLogger(self.__class__.__name__)
        self._lock = threading.Lock()
        self._is_active = False
        self._is_invoking = False
        self._timer: Optional[threading.Timer] = None
        # Each run has an identifier, so cancelled timers cannot affect a restart.
        self._generation = 0

    @property
    def frequency(self) -> UpdateFrequency:
        return self._frequency

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._is_active

    def start(self) -> None:
        with self._lock:
            if self._is_active:
                return
            self._is_active = True
            self._generation += 1
            if not self._is_invoking:
                self._schedule_timer()

    def stop(self) -> None:
        with self._lock:
            self._is_active = False
            self._generation += 1
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def invoke(self) -> bool:
        with self._lock:
            generation = self._generation
        return self._invoke(generation)

    def _schedule_timer(self) -> None:
        """Schedule one timer. The caller must hold the lifecycle lock."""
        self._timer = threading.Timer(
            self.frequency.interval, self._timer_elapsed, args=(self._generation,)
        )
        self._timer.daemon = True
        try:
            self._timer.start()
        except BaseException:
            self._timer = None
            self._is_active = False
            raise

    def _timer_elapsed(self, generation: int) -> None:
        with self._lock:
            if not self._is_active or generation != self._generation:
                return
            self._timer = None
        try:
            self._invoke(generation)
        except Exception:
            self._logger.exception("Trigger invocation failed")

    def _invoke(self, generation: int) -> bool:
        with self._lock:
            if (
                not self._is_active
                or generation != self._generation
                or self._is_invoking
            ):
                return False
            # Reserve this invocation before releasing the lock. stop() can
            # disable future invocations while this callback finishes.
            self._is_invoking = True
        try:
            return self._invoke_callback(generation)
        finally:
            with self._lock:
                self._is_invoking = False
                if self._is_active and self._timer is None:
                    self._schedule_timer()

    def _invoke_callback(self, generation: int) -> bool:
        """Run the callback inside the serialized invocation.

        Conditional strategies can use the run identifier to discard an
        evaluation result if the trigger stopped or restarted while checking.
        """
        self._callback()
        return True


class OneShotTrigger(IntervalTrigger):
    """Invoke a callback once after an UpdateFrequency duration.

    Starting schedules one timer. The trigger becomes inactive before its
    callback runs and remains inactive unless explicitly restarted. invoke()
    fires early and cancels the pending timer. Repeated starts while active
    do not reset the countdown; stop() cancels it and clears time_status.

    time_status is a TimeStatus for the current countdown, retained with zero
    remaining time after firing. Duration changes apply to the next run.
    Restarting during a callback waits for it to finish before beginning the
    new countdown, so callbacks never overlap. Callback exceptions propagate
    from explicit invocations and are logged for background invocations.
    """

    def __init__(self, callback: Callable[[], None], duration: UpdateFrequency) -> None:
        super().__init__(callback, frequency=duration)
        # Lifecycle overrides hold this lock while calling the parent methods.
        self._lock = threading.RLock()
        self._time_status: Optional[TimeStatus] = None

    @property
    def duration(self) -> UpdateFrequency:
        return self.frequency

    @property
    def time_status(self) -> Optional[TimeStatus]:
        with self._lock:
            return self._time_status

    def start(self) -> None:
        with self._lock:
            if self._is_active:
                return
            self._time_status = None
            super().start()

    def stop(self) -> None:
        with self._lock:
            super().stop()
            self._time_status = None

    def _schedule_timer(self) -> None:
        now = time.time()
        self._time_status = TimeStatus(start=now, end=now + self.duration.interval)
        try:
            super()._schedule_timer()
        except BaseException:
            self._time_status = None
            raise

    def _invoke_callback(self, generation: int) -> bool:
        with self._lock:
            if not self._is_active or generation != self._generation:
                return False
            # Consume this run before calling user code; a restart is a new run.
            self._is_active = False
            self._generation += 1
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            if self._time_status is not None:
                self._time_status.end = time.time()
        return super()._invoke_callback(generation)


class PollingTrigger(IntervalTrigger):
    """Evaluate a condition on a schedule, optionally limiting update frequency.

    ``frequency`` controls how often to poll. ``evaluation`` is a synchronous,
    zero-argument function returning a bool. A true evaluation calls the
    callback once unless a cooldown is active. False evaluations keep polling
    without calling it. Without a cooldown, every true poll triggers an update.

    ``cooldown`` is an optional UpdateFrequency. It starts when a true result
    is accepted, before running the callback, even if that callback raises.
    Polling continues during cooldown, but true results are discarded without
    extending it. The next true result after expiry starts a new cooldown.
    TimeStatus tracks the cooldown's start, end, elapsed and remaining time,
    using the same wall-clock timestamps as the existing updater.
    Cooldown persists across stop/restart; configuration changes apply to the
    next accepted result. None disables cooldown.

    The first evaluation runs after one interval, and the next interval
    starts after evaluation and any callback finish. Evaluations and callbacks
    never overlap. Stopping during an evaluation discards its result, including
    if a new run starts before that evaluation finishes.

    Explicit invoke() performs one evaluation and returns whether the callback
    ran. Evaluation or callback errors propagate from explicit invocations;
    background errors are logged and polling continues.
    """

    def __init__(
        self,
        callback: Callable[[], None],
        frequency: UpdateFrequency,
        evaluation: Callable[[], bool],
        cooldown: Optional[UpdateFrequency] = None,
    ) -> None:
        super().__init__(callback, frequency)
        if not callable(evaluation):
            raise TypeError("evaluation must be callable")
        if cooldown is not None:
            if not isinstance(cooldown, UpdateFrequency):
                raise TypeError("cooldown must be an UpdateFrequency or None")
            if not math.isfinite(cooldown.interval) or cooldown.interval <= 0:
                raise ValueError("cooldown interval must be positive and finite")
        self._evaluation = evaluation
        self._cooldown = cooldown
        self._cooldown_status: Optional[TimeStatus] = None

    @property
    def cooldown(self) -> Optional[UpdateFrequency]:
        return self._cooldown

    @property
    def cooldown_status(self) -> Optional[TimeStatus]:
        with self._lock:
            return self._cooldown_status

    @property
    def cooldown_remaining(self) -> float:
        """Seconds left before another true result can trigger an update."""
        with self._lock:
            if self._cooldown_status is None:
                return 0.0
            return self._cooldown_status.remaining or 0.0

    @property
    def is_cooling_down(self) -> bool:
        return self.cooldown_remaining > 0

    def _invoke_callback(self, generation: int) -> bool:
        if not self._evaluation():
            return False
        with self._lock:
            if not self._is_active or generation != self._generation:
                return False
            if self._cooldown_status is not None and self._cooldown_status.remaining:
                return False
            if self._cooldown is not None:
                now = time.time()
                self._cooldown_status = TimeStatus(
                    start=now, end=now + self._cooldown.interval
                )
        return super()._invoke_callback(generation)
