from __future__ import annotations

import logging
import threading
import uuid
from abc import ABC, abstractmethod
from typing import Callable, Optional

from .trigger import Trigger
from .updater import UpdateFrequency, Updater


class PlaylistEmptyError(Exception):
    def __init__(self) -> None:
        super().__init__("Playlist is empty")


class PlaylistItem(ABC):
    """Own content updates and an optional trigger that decides when to run them.

    A trigger factory receives this item's update callback and must return a
    new, inactive Trigger. Subclasses can supply their own default factory.
    Without a factory the item updates once on start, then stays active until
    stopped. Lifecycle methods are idempotent; running updates may finish
    after stop().
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
        self.uuid = str(uuid.uuid4())
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


class Playlist(Updater):

    def __init__(self, frequency: UpdateFrequency) -> None:
        super().__init__(frequency)
        self._queue = []
        self._current_position = 0

    def start(self) -> None:
        super().start(update_on_start=False)
        self.current_item.activate()

    def stop(self) -> None:
        super().stop()
        if self.current_item.is_alive:
            self.logger.debug(f"Shutting down current item - {self.current_item}")
            self.current_item.deactivate()
        else:
            raise RuntimeError("Playlist not running, nothing to stop")

    def add_item(self, item: PlaylistItem) -> None:
        if not isinstance(item, PlaylistItem):
            raise TypeError(f"Item is {type(item)} and not a PlaylistItem")
        self._queue.append(item)

    def remove_item(self, index: int) -> None:
        if self.is_empty:
            raise ValueError("Unable to remove items from an empty queue")
        if index < 0 or index > len(self._queue):
            raise ValueError(f"Index {index} is not valid with {self.size} items")

        if self.is_alive and index == current_index:
            raise RuntimeError("Unable to remove currently active item")

        removed_item = self._queue.pop(index)
        self.logger.info(f"Item {removed_item.uuid} has been removed")
        if index < current_index:
            current_index -= 1

    def get_item(self, index: int) -> PlaylistItem:
        if index > self.size or index <= 0:
            raise IndexError(
                f"Index {index} out of bounds for playlist of size {self.size}"
            )
        return self._queue[index]

    def peek_next(self) -> Playlist:
        if self.is_empty:
            raise PlaylistEmptyError()
        return self._queue[(self._current_position + 1) % self.size]

    def next(self) -> PlaylistItem:
        if self.is_empty:
            raise PlaylistEmptyError()
        if self.size == 1:
            self.logger.debug(f"Playlist of size 1, no need to update again")
            return self.current_item
        self._current_position = (self._current_position + 1) % self.size
        self.logger.info(
            f"Current Position: {self._current_position} - {self.current_item}"
        )
        self.logger.info(f"Playlist updated to {self.current_item.name}")
        return self.current_item

    def update(self) -> None:
        if self.current_item.is_alive:
            self.current_item.deactivate()
        next_item = self.next()
        if next_item is not None:
            next_item.activate()

    @property
    def items(self) -> List[PlaylistItem]:
        return list(self._queue)

    @property
    def current_index(self) -> int:
        return self._current_position

    @property
    def current_item(self) -> PlaylistItem:
        if self.is_empty:
            raise PlaylistEmptyError()
        return self._queue[self._current_position]

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def is_empty(self) -> int:
        return len(self._queue) == 0
