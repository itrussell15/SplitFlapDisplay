from abc import ABC, abstractmethod
from .updater import Updater, UpdateFrequency

from typing import Optional

class PlaylistEmptyError(Exception):
    def __init__(self) -> None:
        super().__init__("Playlist is empty")


class PlaylistItem(ABC, Updater):
    # Should be able to do static and app based updates
    def __init__(self, name: str, frequency: Optional[UpdateFrequency] = None) -> None:
        super().__init__(frequency)
        self._name = name

    def __repr__(self) -> str:
        return f"PlaylistItem({self.name})"

    @abstractmethod
    def update(self) -> None:
        pass

class Playlist(Updater):

    def __init__(self, frequency: UpdateFrequency) -> None:
        super().__init__(frequency)
        self._queue = []
        self._current_position = 0

    def add_item(self, item: PlaylistItem) -> None:
        if not isinstance(item, PlaylistItem):
            raise TypeError(f"Item is {type(item)} and not a PlaylistItem") 
        self._queue.append(item)

    def next(self) -> PlaylistItem:
        if self.is_empty:
            raise PlaylistEmptyError()
        self._current_position = (self._current_position + 1) % self.size

    def update(self) -> None:
        self.current_item.stop()
        self.next()
        self.current_item.start()
    
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
        return len(self._queue) > 0