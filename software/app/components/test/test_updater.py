import os
import logging
import struct
import sys
import threading
import time
import unittest
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.components.updater import Updater, UpdateFrequency
from utils import create_logger

MODULE_IDS = [1, 2, 3, 4, 5]
SLEEP_TIME_S = 1.0


class TestUpdateFrequency(unittest.TestCase):

    def setUp(self) -> None:
        self.frequency = UpdateFrequency(1, 1)

    def test_happy_path(self) -> None:
        self.assertIsInstance(self.frequency, UpdateFrequency)
        self.assertEqual(self.frequency.minutes, 1)
        self.assertEqual(self.frequency.seconds, 1)
    
    def test_no_init_values(self) -> None:
        with self.assertRaises(ValueError):
            frequency = UpdateFrequency()
    
    def test_set_minutes(self) -> None:
        self.frequency.minutes = 10
        self.assertEqual(self.frequency.minutes, 10)

    def test_set_seconds(self) -> None:
        self.frequency.seconds = 10
        self.assertEqual(self.frequency.seconds, 10)

    def test_set_invalid_minutes(self) -> None:
        with self.assertRaises(ValueError):
            self.frequency.minutes = -10

    def test_set_invalid_seconds(self) -> None:
        with self.assertRaises(ValueError):
            self.frequency.seconds = -10

    def test_just_minutes(self) -> None:
        frequency = UpdateFrequency(minutes=1)
    
    def test_just_seconds(self) -> None:
        frequency = UpdateFrequency(seconds=1)

    def test_interval(self) -> None:
        self.assertEqual(self.frequency.interval, self.frequency.minutes * 60 + self.frequency.seconds)


class TestUpdater(unittest.TestCase):

    class BasicUpdater(Updater):
        def __init__(self, frequency: UpdateFrequency) -> None:
            super().__init__(frequency)
            self.logger = logging.getLogger(self.__class__.__name__)
            self.update_count = 0

        def update(self) -> None:
            self.update_count += 1
            self.logger.info(f"Update count set to {self.update_count}")
    
    @classmethod
    def setUpClass(cls):
        create_logger(level=logging.DEBUG, spacing=23)
    
    def setUp(self) -> None:
        self.frequency = UpdateFrequency(seconds=1)
        self.updater =  self.BasicUpdater(self.frequency)

    def tearDown(self) -> None:
        if self.updater.is_alive:
            self.updater.stop()

    def test_frequency(self) -> None:
        self.assertEqual(self.updater.frequency, self.frequency)
    
    def test_static_update(self) -> None:
        self.updater.frequency = None
        self.updater.start()
        self.assertEqual(self.updater.update_count, 1)
        time.sleep(5)
        self.assertEqual(self.updater.update_count, 1)

    def test_dynamic_update(self) -> None:
        self.assertEqual(self.updater.update_count, 0)
        self.updater.start()
        for i in range(10):
            self.assertEqual(self.updater.update_count, i + 1)
            time.sleep(self.updater.frequency.interval * 1.01)

    def test_is_alive(self) -> None:
        self.assertEqual(self.updater.update_count, 0)
        self.updater.start()
        self.assertTrue(self.updater.is_alive)
        self.updater.stop()
        self.assertFalse(self.updater.is_alive)

    
    def test_is_dynamic(self) -> None:
        self.assertTrue(self.updater.is_dynamic)
        self.updater.frequency = None
        self.assertFalse(self.updater.is_dynamic)