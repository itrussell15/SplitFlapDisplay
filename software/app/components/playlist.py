

class PlaylistEmptyError(Exception):
    def __init__(self) -> None:
        super().__init__("Playlist is empty")

class PlaylistItem:
    # Should be able to do static and app based updates
    def __init__(self) -> None:
        pass

class Playlist:

    def __init__(self) -> None:
        self._queue = []
        self._current_position = 0

    def add_item(self, item: PlaylistItem) -> None:
        if not isinstance(item, PlaylistItem):
            raise TypeError(f"Item is {type(item)} and not a PlaylistItem") 
        self._queue.append(item)

    def next(self) -> PlaylistItem:
        if self.size < 1:
            raise ValueError('The playlist is empty')
        self._current_position = (self._current_position + 1) % self.size
        
    @property
    def size(self) -> int:
        return len(self._queue)