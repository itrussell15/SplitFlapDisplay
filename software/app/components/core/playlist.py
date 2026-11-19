from __future__ import annotations

import logging
import math
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Union

from .trigger import OneShotTrigger, Trigger
from .updater import TimeStatus, UpdateFrequency


class PlaylistEmptyError(Exception):
    def __init__(self) -> None:
        super().__init__("Playlist is empty")


@dataclass(frozen=True)
class PlaylistEntry:
    """Pair content with its duration in this playlist, independently of refreshes."""

    item: PlaylistItem
    duration: Optional[UpdateFrequency]
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if not isinstance(self.item, PlaylistItem):
            raise TypeError("item must be a PlaylistItem")
        if not isinstance(self.duration, UpdateFrequency):
            raise TypeError(f"duration must be an UpdateFrequency, not {type(self.duration)}")
        if not math.isfinite(self.duration.interval) or self.duration.interval <= 0:
            raise ValueError("duration interval must be positive and finite")


class PlaylistItem(ABC):
    """Own content updates and an optional trigger that decides when to run them.

    A trigger factory receives this item's update callback and must return a
    new, inactive Trigger. Subclasses can supply their own default factory.
    Without a factory the item updates once on activation, then stays active
    until deactivated. Lifecycle methods are idempotent; running updates may
    finish after deactivation.
    """

    def __init__(
        self,
        name: str,
        trigger_factory: Optional[Callable[[Callable[[], None]], Trigger]] = None,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._name = name
        self._is_active = False
        self._is_updating = False
        self._lifecycle_lock = threading.RLock()
        self._generation = 0
        self._trigger: Optional[Trigger] = None
        if trigger_factory is not None:
            if not callable(trigger_factory):
                raise TypeError("trigger_factory must be callable")
            trigger = trigger_factory(self._execute_update)
            if not isinstance(trigger, Trigger):
                raise TypeError("trigger_factory must return a Trigger")
            if trigger.is_active:
                raise ValueError("trigger_factory must return an inactive Trigger")
            self._trigger = trigger

    def __repr__(self) -> str:
        return f"PlaylistItem({self.name})"

    @abstractmethod
    def update(self) -> None:
        """Generate or display the item's content, independently of scheduling."""

    def activate(self, update_on_start: bool = True) -> None:
        """Activate the item, optionally update once, then enable its trigger."""
        with self._lifecycle_lock:
            if self._is_active:
                self.logger.warning(
                    "Tried to activate an already active item, skipping."
                )
                return
            self._is_active = True
            self._generation += 1
            generation = self._generation
        try:
            if update_on_start:
                self._execute_update()
            with self._lifecycle_lock:
                # An initial update may stop or restart its own item.
                if self._is_active and generation == self._generation:
                    if self._trigger is not None:
                        self._trigger.start()
        except BaseException:
            with self._lifecycle_lock:
                # A failed earlier start must not stop a newer run.
                if generation == self._generation:
                    self.deactivate()
            raise

    def deactivate(self) -> None:
        """Deactivate the item and disable further trigger callbacks."""
        if not self._is_active:
            self.logger.warning("Deactivating a not active item")
            return

        with self._lifecycle_lock:
            self._is_active = False
            self._generation += 1
            if self._trigger is not None:
                self._trigger.stop()

    def _execute_update(self) -> None:
        """Run the content callback while active, preventing overlapping updates.

        Subclasses may override this hook to adapt their content method, such
        as resolving generated display data before sending it to hardware.
        """
        with self._lifecycle_lock:
            if not self._is_active or self._is_updating:
                return
            self._is_updating = True
        try:
            self.update()
        finally:
            with self._lifecycle_lock:
                self._is_updating = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def trigger(self) -> Optional[Trigger]:
        return self._trigger

    @property
    def is_active(self) -> bool:
        with self._lifecycle_lock:
            return self._is_active

    @property
    def is_updating(self) -> bool:
        with self._lifecycle_lock:
            return self._is_updating


class Playlist:
    """Play entries in order using a one-shot timer for each entry's duration.

    start() activates the selected item and schedules advancement. next()
    cancels that timer, switches items, and schedules the next duration.
    stop() cancels the timer and deactivates the current item.

    Controls run one at a time; stop() waits for ongoing activation to finish.
    Edit entries while stopped. A single entry stays active without a timer.
    """

    def __init__(self, entries: Optional[List[PlaylistEntry]] = None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._queue: List[PlaylistEntry] = []
        self._current_position = 0
        self._lock = threading.RLock()
        self._is_active = False
        self._trigger: Optional[OneShotTrigger] = None
        if entries is not None:
            for entry in entries:
                if not isinstance(entry, PlaylistEntry):
                    raise TypeError("entries must contain PlaylistEntry objects")
                self.add_entry(entry)

    def start(self) -> None:
        with self._lock:
            if self._is_active:
                return
            if self.is_empty:
                raise PlaylistEmptyError()
            self._is_active = True
            try:
                self.current_item.activate()
                if self._is_active and self.current_item.is_active:
                    self._schedule_timer()
                else:
                    self.stop()
            except Exception:
                self.stop()
                raise

    def stop(self) -> None:
        with self._lock:
            if not self._is_active:
                return
            self._is_active = False
            self._stop_timer()
            if self.current_item.is_active:
                self.current_item.deactivate()

    def next(self) -> PlaylistEntry:
        """Switch items while running, or change only the selection while stopped."""
        with self._lock:
            if self.is_empty:
                raise PlaylistEmptyError()
            if len(self._queue) == 1:
                return self.current_entry
            try:
                if self._is_active:
                    self._stop_timer()
                    self.current_item.deactivate()
                self._current_position = (self._current_position + 1) % len(self._queue)
                if self._is_active:
                    self.current_item.activate()
                    if self._is_active and self.current_item.is_active:
                        self._schedule_timer()
                    else:
                        self.stop()
            except Exception:
                self.stop()
                raise
            return self.current_entry

    def _schedule_timer(self) -> None:
        """Create one advancement timer after the item's initial update finishes."""
        if len(self._queue) == 1:
            return

        def on_elapsed() -> None:
            with self._lock:
                # A cancelled timer's callback may already be waiting to run.
                if self._is_active and self._trigger is trigger:
                    self.next()

        trigger = OneShotTrigger(on_elapsed, duration=self.current_entry.duration)
        self._trigger = trigger
        trigger.start()

    def _stop_timer(self) -> None:
        if self._trigger is not None:
            self._trigger.stop()
            self._trigger = None

    def add_entry(
        self,
        item: Union[PlaylistItem, PlaylistEntry],
        duration: Optional[UpdateFrequency] = None,
    ) -> PlaylistEntry:
        """Add an existing entry, or construct one from an item and duration."""
        with self._lock:
            if self._is_active:
                raise RuntimeError("Stop the playlist before adding entries")
            if isinstance(item, PlaylistEntry):
                if duration is not None:
                    raise TypeError("duration is already part of the PlaylistEntry")
                entry = item
            else:
                entry = PlaylistEntry(item=item, duration=duration)
            self._queue.append(entry)
            return entry

    def remove_entry(self, index: int) -> None:
        with self._lock:
            if self._is_active:
                raise RuntimeError("Stop the playlist before removing entries")
            self._check_index(index)
            removed = self._queue.pop(index)
            if index < self._current_position:
                self._current_position -= 1
            elif self._current_position >= len(self._queue):
                self._current_position = 0
        self.logger.info("Removed entry %s (%s)", removed.uuid, removed.item.name)

    def get_entry(self, index: int) -> PlaylistEntry:
        with self._lock:
            self._check_index(index)
            return self._queue[index]

    def peek_next(self) -> PlaylistEntry:
        with self._lock:
            if self.is_empty:
                raise PlaylistEmptyError()
            return self._queue[(self._current_position + 1) % len(self._queue)]

    def _check_index(self, index: int) -> None:
        if not isinstance(index, int):
            raise TypeError("index must be an integer")
        if index < 0 or index >= len(self._queue):
            raise IndexError(
                f"Index {index} out of bounds for playlist of size {len(self._queue)}"
            )

    @property
    def is_empty(self) -> bool:
        return len(self._queue) > 0

    @property
    def entries(self) -> List[PlaylistEntry]:
        with self._lock:
            return list(self._queue)

    @property
    def items(self) -> List[PlaylistItem]:
        with self._lock:
            return [entry.item for entry in self._queue]

    @property
    def current_entry(self) -> PlaylistEntry:
        with self._lock:
            if self.is_empty:
                raise PlaylistEmptyError()
            return self._queue[self._current_position]

    @property
    def current_index(self) -> int:
        with self._lock:
            return self._current_position

    @property
    def current_item(self) -> PlaylistItem:
        return self.current_entry.item

    @property
    def trigger(self) -> Optional[OneShotTrigger]:
        with self._lock:
            return self._trigger

    @property
    def time_status(self) -> Optional[TimeStatus]:
        with self._lock:
            return self._trigger.time_status if self._trigger is not None else None

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._is_active

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return not self._queue
