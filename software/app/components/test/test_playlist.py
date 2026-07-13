import logging
import sys
import threading
import time
import unittest
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.components.core.updater import UpdateFrequency
from app.components.core.playlist import Playlist, PlaylistItem
from utils import create_logger

logger = logging.getLogger("PlaylistTester")

class BasicPlaylistItem(PlaylistItem):

    def __init__(self, name: str, frequency: Optional[UpdateFrequency] = None) -> None:
        super().__init__(
            name=name,
            frequency=frequency
        )
        self.update_count = 0
        self.previous_update_count = 0

    def _update(self) -> None:
        self.update_count += 1
        self.logger.info(f"Updated {self.name}")

    def stop(self) -> None:
        super().stop()
        self.previous_update_count = self.update_count
        self.update_count = 0

class TestPlaylist(ABC):

    @classmethod
    def setUpClass(cls):
        create_logger(level=logging.DEBUG, spacing=23)

    def setUp(self) -> None:
        self.frequency = self.create_frequency_updater()
        self.playlist = Playlist(self.frequency)

        self.items = []
        for i in range(10):
            item = self.create_item()
            self.playlist.add_item(item)
            self.items.append(item)

    def tearDown(self) -> None:
        if self.playlist.is_alive:
            self.playlist.stop()

    @abstractmethod
    def create_frequency_updater(self) -> PlaylistItem:
        pass

    @abstractmethod
    def create_item(self) -> PlaylistItem:
        pass

    @abstractmethod
    def _loop_item(self, i: int) -> None:
        pass

    def test_next(self) -> None:
        self.assertEqual(self.playlist.current_index, 0)
        item = self.playlist.next()
        self.assertEqual(item, self.items[self.playlist.current_index])
        self.assertEqual(self.playlist.current_index, 1)

    def test_peek_next(self) -> None:
        self.assertEqual(self.playlist.current_index, 0)
        item = self.playlist.peek_next()
        self.assertEqual(item, self.items[self.playlist.current_index + 1])
        self.assertEqual(self.playlist.current_index, 0)

    def test_add_item(self) -> None:
        init_size = self.playlist.size
        new_item = BasicPlaylistItem("new_item")
        self.playlist.add_item(new_item)
        self.assertEqual(self.playlist.size, init_size + 1)
    
    def test_empty(self) -> None:
        playlist = Playlist(self.frequency)
        self.assertTrue(playlist.is_empty)
        item = BasicPlaylistItem('new_item')
        playlist.add_item(item)
        self.assertFalse(playlist.is_empty)

    def test_start(self) -> None:
        self.assertEqual(self.playlist.current_index, 0)
        self.playlist.start()
        for i in range(5):
            logger.info(f"Looping Item {i}")
            self._loop_item(i)
        self.evaluate_start()
        
class TestStaticPlaylistItems(TestPlaylist, unittest.TestCase):

    def create_item(self) -> BasicPlaylistItem:
        return BasicPlaylistItem(f"Item{len(self.items)}")

    def create_frequency_updater(self) -> UpdateFrequency:
        return UpdateFrequency(seconds=1)

    def evaluate_start(self) -> None:
        pass

    def _loop_item(self, i: int) -> None:
        time.sleep(self.playlist.frequency.interval * 1.1)
        self.assertEqual(self.playlist.current_index, (i + 1) % len(self.items))
        self.assertEqual(self.playlist.current_item, self.items[self.playlist.current_index])
        self.assertEqual(self.playlist.current_item.update_count, 1)

class TestDynamicPlaylistItems(TestPlaylist, unittest.TestCase):

    def create_item(self) -> BasicPlaylistItem:
        frequency = UpdateFrequency(seconds=1)
        return BasicPlaylistItem(f"Item{len(self.items)}", frequency)

    def create_frequency_updater(self) -> UpdateFrequency:
        return UpdateFrequency(seconds=2)

    def evaluate_start(self) -> None:
        updates = {item: item.previous_update_count for item in self.items}
        print(updates)

    def _loop_item(self, i: int) -> None:
        this_item = self.playlist.current_item
        while this_item.is_updating or this_item.is_alive:
            time.sleep(0.001)
        expected_updates = int(self.playlist.frequency.interval / this_item.frequency.interval)
        self.assertEqual(expected_updates, this_item.previous_update_count)
