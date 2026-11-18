import sys
import threading
import unittest
import uuid
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.components.core.playlist import Playlist, PlaylistEmptyError, PlaylistEntry, PlaylistItem
from app.components.core.trigger import IntervalTrigger, ManualTrigger, OneShotTrigger
from app.components.core.updater import UpdateFrequency
from app.components.test.test_interval_trigger import ControlledTimer


class BasicPlaylistItem(PlaylistItem):
    def __init__(self, name, trigger_factory=None):
        super().__init__(name, trigger_factory=trigger_factory)
        self.update_count = 0
        self.action = None

    def update(self):
        self.update_count += 1
        if self.action is not None:
            self.action()


class TestPlaylistEntry(unittest.TestCase):
    def test_unique_ids_and_independent_durations_for_the_same_item(self):
        item = BasicPlaylistItem("A")
        first = PlaylistEntry(item, UpdateFrequency(minutes=1))
        second = PlaylistEntry(item, UpdateFrequency(seconds=10))
        self.assertNotEqual(first.uuid, second.uuid)
        self.assertEqual(str(uuid.UUID(first.uuid)), first.uuid)
        self.assertEqual(first.duration.interval, 60)
        self.assertEqual(second.duration.interval, 10)
        with self.assertRaises(FrozenInstanceError):
            first.item = BasicPlaylistItem("B")

    def test_requires_valid_item_and_finite_positive_duration(self):
        item = BasicPlaylistItem("A")
        with self.assertRaises(TypeError):
            PlaylistEntry(object(), UpdateFrequency(seconds=10))
        for duration in (None, 10, "10"):
            with self.subTest(duration=duration):
                with self.assertRaises(TypeError):
                    PlaylistEntry(item, duration)
        for seconds in (float("inf"), float("nan")):
            with self.subTest(seconds=seconds):
                with self.assertRaises(ValueError):
                    PlaylistEntry(item, UpdateFrequency(seconds=seconds))


class TestPlaylist(unittest.TestCase):
    def setUp(self):
        self.timers = []

        def create_timer(*args, **kwargs):
            timer = ControlledTimer(*args, **kwargs)
            self.timers.append(timer)
            return timer

        timer_patch = patch("app.components.core.trigger.threading.Timer", side_effect=create_timer)
        timer_patch.start()
        self.addCleanup(timer_patch.stop)
        self.a = BasicPlaylistItem("A", ManualTrigger)
        self.b = BasicPlaylistItem("B", ManualTrigger)
        self.playlist = Playlist()
        self.first = self.playlist.add_entry(self.a, UpdateFrequency(minutes=1))
        self.second = self.playlist.add_entry(self.b, UpdateFrequency(seconds=10))
        self.addCleanup(self.playlist.stop)

    def test_existing_entries_and_validation(self):
        playlist = Playlist([self.first])
        self.assertIs(playlist.add_entry(self.second), self.second)
        self.assertEqual(playlist.entries, [self.first, self.second])
        self.assertEqual(playlist.items, [self.a, self.b])
        with self.assertRaises(TypeError):
            playlist.add_entry(self.first, UpdateFrequency(seconds=1))
        with self.assertRaises(TypeError):
            Playlist([self.a])
        with self.assertRaises(TypeError):
            playlist.add_entry(self.a)

    def test_selection_and_snapshot_accessors(self):
        self.assertIs(self.playlist.current_entry, self.first)
        self.assertIs(self.playlist.current_item, self.a)
        self.assertIs(self.playlist.get_entry(0), self.first)
        self.assertIs(self.playlist.get_entry(1), self.second)
        self.assertIs(self.playlist.peek_next(), self.second)
        self.assertEqual(self.playlist.current_index, 0)
        self.assertIs(self.playlist.next(), self.second)
        self.assertFalse(self.a.is_active)
        self.assertFalse(self.b.is_active)
        self.assertIs(self.playlist.next(), self.first)
        self.playlist.entries.clear()
        self.playlist.items.clear()
        self.assertEqual(self.playlist.size, 2)
        self.assertEqual(self.timers, [])

    def test_empty_playlist_and_zero_based_bounds(self):
        playlist = Playlist()
        playlist.stop()
        self.assertTrue(playlist.is_empty)
        self.assertFalse(playlist.is_active)
        for action in (playlist.start, playlist.next, playlist.peek_next,
                       lambda: playlist.current_entry, lambda: playlist.current_item):
            with self.assertRaises(PlaylistEmptyError):
                action()
        self.assertIsNone(playlist.time_status)
        for index in (-1, 2, 10):
            with self.subTest(index=index):
                with self.assertRaises(IndexError):
                    self.playlist.get_entry(index)
                with self.assertRaises(IndexError):
                    self.playlist.remove_entry(index)
        with self.assertRaises(TypeError):
            self.playlist.get_entry("0")

    def test_variable_durations_advance_and_wrap_around(self):
        self.playlist.start()
        self.assertEqual(self.a.update_count, 1)
        self.assertTrue(self.a.trigger.is_active)
        self.assertFalse(self.b.is_active)
        self.assertIsInstance(self.playlist.trigger, OneShotTrigger)
        self.assertEqual(self.timers[-1].interval, 60)
        self.timers[-1].fire()
        self.assertIs(self.playlist.current_entry, self.second)
        self.assertFalse(self.a.is_active)
        self.assertFalse(self.a.trigger.is_active)
        self.assertTrue(self.b.trigger.is_active)
        self.assertEqual(self.b.update_count, 1)
        self.assertEqual(self.timers[-1].interval, 10)
        self.timers[-1].fire()
        self.assertIs(self.playlist.current_entry, self.first)
        self.assertFalse(self.b.is_active)
        self.assertEqual(self.a.update_count, 2)
        self.assertEqual(self.timers[-1].interval, 60)

    def test_content_interval_is_independent_of_entry_duration(self):
        item = BasicPlaylistItem("Refreshing", lambda callback: IntervalTrigger(callback, UpdateFrequency(seconds=2)))
        playlist = Playlist([PlaylistEntry(item, UpdateFrequency(minutes=1)), self.second])
        self.addCleanup(playlist.stop)
        playlist.start()
        refresh_timer, advancement_timer = self.timers
        self.assertEqual(refresh_timer.interval, 2)
        self.assertEqual(advancement_timer.interval, 60)
        refresh_timer.fire()
        self.assertEqual(item.update_count, 2)
        self.assertIs(playlist.current_item, item)
        pending_refresh = self.timers[-1]
        advancement_timer.fire()
        pending_refresh.fire()
        self.assertTrue(pending_refresh.cancelled)
        self.assertFalse(item.trigger.is_active)
        self.assertEqual(item.update_count, 2)
        self.assertIs(playlist.current_item, self.b)

    def test_idempotent_start_stop_and_restart_reject_stale_callbacks(self):
        self.playlist.start()
        self.playlist.start()
        self.assertEqual(self.a.update_count, 1)
        self.assertEqual(len(self.timers), 1)
        timer = self.timers[-1]
        callback = self.playlist.trigger._callback
        self.playlist.stop()
        self.playlist.stop()
        self.assertTrue(timer.cancelled)
        self.assertFalse(self.playlist.is_active)
        self.assertFalse(self.a.is_active)
        self.assertIsNone(self.playlist.trigger)
        self.assertIsNone(self.playlist.time_status)
        timer.fire()
        callback()
        self.playlist.start()
        timer.fire()
        callback()
        self.assertIs(self.playlist.current_entry, self.first)
        self.assertEqual(len(self.timers), 2)
        self.timers[-1].fire()
        self.assertIs(self.playlist.current_entry, self.second)

    def test_manual_next_resets_countdown(self):
        self.playlist.start()
        timer = self.timers[-1]
        callback = self.playlist.trigger._callback
        self.assertIs(self.playlist.next(), self.second)
        self.assertTrue(timer.cancelled)
        self.assertEqual(self.timers[-1].interval, 10)
        timer.fire()
        callback()
        self.assertIs(self.playlist.current_entry, self.second)
        self.assertFalse(self.a.is_active)
        self.assertTrue(self.b.is_active)
        self.playlist.next()
        self.assertIs(self.playlist.current_entry, self.first)

    def test_single_entry_stays_active_without_advancement(self):
        playlist = Playlist([self.first])
        self.addCleanup(playlist.stop)
        playlist.start()
        self.assertIs(playlist.next(), self.first)
        self.assertTrue(self.a.is_active)
        self.assertTrue(self.a.trigger.is_active)
        self.assertEqual(self.a.update_count, 1)
        self.assertIsNone(playlist.trigger)
        self.assertIsNone(playlist.time_status)
        self.assertEqual(self.timers, [])

    def test_countdown_begins_after_initial_update_and_exposes_time_status(self):
        with patch("app.components.core.trigger.time.time", return_value=100) as clock:
            def generate_content():
                self.assertIsNone(self.playlist.time_status)
                self.assertEqual(self.timers, [])
                clock.return_value = 105
            self.a.action = generate_content
            self.playlist.start()
            status = self.playlist.time_status
            self.assertEqual(status.start, 105)
            self.assertEqual(status.end, 165)
            clock.return_value = 110
            self.assertEqual(status.remaining, 55)
            self.assertEqual(status.elapsed, 5)

    def test_duration_changes_apply_on_next_activation(self):
        self.playlist.start()
        self.first.duration.seconds = 5
        self.assertEqual(self.timers[-1].interval, 60)
        self.playlist.next()
        self.playlist.next()
        self.assertEqual(self.timers[-1].interval, 65)

    def test_removing_earlier_entry_preserves_stopped_selection(self):
        third = self.playlist.add_entry(BasicPlaylistItem("C"), UpdateFrequency(seconds=5))
        self.playlist.next()
        self.playlist.remove_entry(0)
        self.assertEqual(self.playlist.current_index, 0)
        self.assertIs(self.playlist.current_entry, self.second)
        self.playlist.start()
        self.assertEqual(self.timers[-1].interval, 10)
        self.timers[-1].fire()
        self.assertIs(self.playlist.current_entry, third)

    def test_entry_edits_require_stopping_and_do_not_start_timers(self):
        self.playlist.start()
        with self.assertRaisesRegex(RuntimeError, "Stop the playlist"):
            self.playlist.remove_entry(1)
        with self.assertRaisesRegex(RuntimeError, "Stop the playlist"):
            self.playlist.add_entry(BasicPlaylistItem("C"), UpdateFrequency(seconds=5))
        self.assertEqual(self.playlist.size, 2)
        self.playlist.stop()
        self.playlist.remove_entry(1)
        timer_count = len(self.timers)
        self.playlist.add_entry(self.second)
        self.assertEqual(len(self.timers), timer_count)
        self.assertIsNone(self.playlist.trigger)
        self.playlist.start()
        self.assertEqual(self.timers[-1].interval, 60)

    def test_removing_stopped_selection_keeps_index_valid(self):
        self.playlist.next()
        self.playlist.remove_entry(1)
        self.assertIs(self.playlist.current_entry, self.first)
        self.playlist.remove_entry(0)
        self.assertTrue(self.playlist.is_empty)
        self.assertEqual(self.playlist.current_index, 0)
        with self.assertRaises(IndexError):
            self.playlist.remove_entry(0)

    def test_initial_update_failure_stops_and_can_be_retried(self):
        def fail():
            raise ValueError("content failed")
        self.a.action = fail
        with self.assertRaisesRegex(ValueError, "content failed"):
            self.playlist.start()
        self.assertFalse(self.playlist.is_active)
        self.assertFalse(self.a.is_active)
        self.assertFalse(self.a.trigger.is_active)
        self.assertIsNone(self.playlist.trigger)
        self.a.action = None
        self.playlist.start()
        self.assertTrue(self.a.is_active)

    def test_background_activation_failure_is_logged_and_stops(self):
        def fail():
            raise ValueError("B failed")
        self.b.action = fail
        self.playlist.start()
        with self.assertLogs("OneShotTrigger", level="ERROR"):
            self.timers[-1].fire()
        self.assertFalse(self.playlist.is_active)
        self.assertFalse(self.a.is_active)
        self.assertFalse(self.b.is_active)
        self.assertIsNone(self.playlist.trigger)

    def test_timer_start_failure_cleans_up_activation(self):
        with patch.object(ControlledTimer, "start", side_effect=RuntimeError("timer failed")):
            with self.assertRaisesRegex(RuntimeError, "timer failed"):
                self.playlist.start()
        self.assertFalse(self.playlist.is_active)
        self.assertFalse(self.a.is_active)
        self.assertFalse(self.a.trigger.is_active)
        self.assertIsNone(self.playlist.trigger)

    def test_item_can_stop_playlist_or_deactivate_itself_during_initial_update(self):
        for action in (self.playlist.stop, self.a.deactivate):
            with self.subTest(action=action.__name__):
                self.a.action = action
                self.playlist.start()
                self.assertFalse(self.playlist.is_active)
                self.assertFalse(self.a.is_active)
                self.assertIsNone(self.playlist.trigger)
                self.assertEqual(self.timers, [])


    def test_stop_waits_for_initial_activation_then_cancels_its_timer(self):
        entered = threading.Event()
        release = threading.Event()
        stop_attempted = threading.Event()
        stopped = threading.Event()
        errors = []

        def block():
            entered.set()
            if not release.wait(2):
                raise RuntimeError("test activation timed out")
        self.a.action = block

        def start():
            try:
                self.playlist.start()
            except BaseException as exc:
                errors.append(exc)

        def stop():
            stop_attempted.set()
            try:
                self.playlist.stop()
            except BaseException as exc:
                errors.append(exc)
            finally:
                stopped.set()

        start_thread = threading.Thread(target=start, daemon=True)
        stop_thread = threading.Thread(target=stop, daemon=True)
        self.addCleanup(start_thread.join, 2)
        self.addCleanup(release.set)
        start_thread.start()
        self.assertTrue(entered.wait(1))
        stop_thread.start()
        self.addCleanup(stop_thread.join, 2)
        self.addCleanup(release.set)
        self.assertTrue(stop_attempted.wait(1))
        self.assertFalse(stopped.wait(0.02))
        release.set()
        start_thread.join(1)
        stop_thread.join(1)
        self.assertFalse(start_thread.is_alive())
        self.assertFalse(stop_thread.is_alive())
        self.assertEqual(errors, [])
        self.assertTrue(stopped.is_set())
        self.assertFalse(self.playlist.is_active)
        self.assertFalse(self.a.is_active)
        self.assertFalse(self.a.trigger.is_active)
        self.assertIsNone(self.playlist.trigger)
        self.assertTrue(self.timers[-1].cancelled)

    def test_old_timer_waiting_for_lock_does_not_advance_new_selection(self):
        self.playlist.start()
        callback = self.playlist.trigger._callback
        attempted = threading.Event()
        errors = []

        def run_callback():
            attempted.set()
            try:
                callback()
            except BaseException as exc:
                errors.append(exc)

        with self.playlist._lock:
            thread = threading.Thread(target=run_callback, daemon=True)
            thread.start()
            self.addCleanup(thread.join, 2)
            self.assertTrue(attempted.wait(1))
            self.playlist.next()
        thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertIs(self.playlist.current_entry, self.second)
        self.assertEqual(self.b.update_count, 1)
        self.assertEqual(len(self.timers), 2)


class TestPlaylistThreads(unittest.TestCase):
    def test_real_countdown_advances_and_item_can_stop_playlist(self):
        finished = threading.Event()

        class StoppingItem(BasicPlaylistItem):
            def deactivate(self):
                super().deactivate()
                finished.set()

        a = BasicPlaylistItem("A")
        b = StoppingItem("B")
        playlist = Playlist([
            PlaylistEntry(a, UpdateFrequency(seconds=0.01)),
            PlaylistEntry(b, UpdateFrequency(seconds=0.02)),
        ])
        self.addCleanup(playlist.stop)
        b.action = playlist.stop
        playlist.start()
        self.assertTrue(finished.wait(1))
        self.assertIs(playlist.current_item, b)
        self.assertEqual(a.update_count, 1)
        self.assertEqual(b.update_count, 1)
        self.assertFalse(a.is_active)
        self.assertFalse(b.is_active)
        self.assertFalse(playlist.is_active)
        self.assertIsNone(playlist.trigger)


if __name__ == "__main__":
    unittest.main()
