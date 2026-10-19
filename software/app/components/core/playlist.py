from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from .updater import Updater, UpdateFrequency

from typing import Optional

class PlaylistEmptyError(Exception):
    def __init__(self) -> None:
        super().__init__("Playlist is empty")


class PlaylistItem(Updater):
    # Should be able to do static and app based updates
    def __init__(self, name: str, frequency: Optional[UpdateFrequency] = None) -> None:
        super().__init__(frequency)
        self._name = name
        self._is_updating = False
        self.uuid = str(uuid.uuid4())

    def __repr__(self) -> str:
        return f"PlaylistItem({self.name})"

    @property
    def name(self) -> str:
        return self._name


class Playlist(Updater):

    def __init__(self, frequency: UpdateFrequency) -> None:
        super().__init__(frequency)
        self._queue = []
        self._current_position = 0

    def start(self) -> None:
        super().start(update_on_start=False)
        self.current_item.start()

    def stop(self) -> None:
        super().stop()
        if self.current_item.is_alive:
            self.logger.debug(f"Shutting down current item - {self.current_item}")
            self.current_item.stop()
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
            raise IndexError(f"Index {index} out of bounds for playlist of size {self.size}")
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
        self.logger.info(f"Current Position: {self._current_position} - {self.current_item}")
        self.logger.info(f"Playlist updated to {self.current_item.name}")
        return self.current_item

    def update(self) -> None:
        if self.current_item.is_alive:
            self.current_item.stop()
        next_item = self.next()
        if next_item is not None:
            next_item.start()

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