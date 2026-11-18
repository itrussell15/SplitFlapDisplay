import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.components.core.playlist import PlaylistEmptyError, PlaylistEntry
from app.components.core.updater import UpdateFrequency
from app.components.display.base_apps.static import StaticDisplayItem
from app.components.display.display_item import DisplayItem
from app.components.display.playlist import DisplayPlaylist
from app.components.test.test_display_item import ExampleDisplayItem
from app.components.test.test_interval_trigger import ControlledTimer
from app.components.test.test_playlist import BasicPlaylistItem
from control.source.display_controller import DisplayInfo


class TestDisplayPlaylist(unittest.TestCase):
    def setUp(self):
        self.info = DisplayInfo(rows=3, columns=15, modules=[])
        self.resolve = Mock(return_value={(1, 1): 2})
        self.resolve.__name__ = "resolve"
        self.display = Mock()
        self.display.__name__ = "display"
        self.timers = []

        def create_timer(*args, **kwargs):
            timer = ControlledTimer(*args, **kwargs)
            self.timers.append(timer)
            return timer

        timer_patch = patch("app.components.core.trigger.threading.Timer", side_effect=create_timer)
        timer_patch.start()
        self.addCleanup(timer_patch.stop)

    def make_playlist(self, **kwargs):
        with patch("builtins.print"):
            playlist = DisplayPlaylist(**kwargs)
        self.addCleanup(playlist.stop)
        return playlist

    def configure(self, playlist):
        playlist.add_display_info(self.info)
        playlist.add_resolve_function(self.resolve)
        playlist.add_display_function(self.display)

    def test_constructor_entries_can_be_configured_after_construction(self):
        item = ExampleDisplayItem()
        entry = PlaylistEntry(item, UpdateFrequency(minutes=1))
        playlist = self.make_playlist(entries=[entry])
        self.assertIs(playlist.current_entry, entry)
        self.assertFalse(item.is_active)
        self.assertEqual(self.timers, [])
        self.configure(playlist)
        playlist.start()
        self.assertIs(item.display_info_received, self.info)
        self.resolve.assert_called_once_with({(1, 1): "A"})
        self.display.assert_called_once_with({(1, 1): 2})
        self.assertTrue(playlist.is_active)
        self.assertIsNone(playlist.trigger)

    def test_added_items_receive_existing_display_configuration(self):
        playlist = self.make_playlist(app_folders=[])
        self.configure(playlist)
        item = ExampleDisplayItem()
        entry = playlist.add_entry(item, UpdateFrequency(seconds=10))
        self.assertIs(entry.item, item)
        self.assertEqual(entry.duration.interval, 10)
        playlist.start()
        self.assertIs(item.display_info_received, self.info)
        self.display.assert_called_once_with({(1, 1): 2})

    def test_constructor_and_add_entry_reject_non_display_items(self):
        playlist = self.make_playlist(app_folders=[])
        duration = UpdateFrequency(seconds=10)
        basic = BasicPlaylistItem("not a display item")
        for value in (basic, PlaylistEntry(basic, duration)):
            with self.subTest(value=type(value).__name__):
                with self.assertRaisesRegex(TypeError, "DisplayItem"):
                    playlist.add_entry(value, duration if value is basic else None)
        with self.assertRaises(TypeError):
            playlist.add_entry(ExampleDisplayItem())
        with self.assertRaises(TypeError):
            playlist.add_entry(PlaylistEntry(ExampleDisplayItem(), duration), duration)
        with patch("builtins.print"):
            with self.assertRaisesRegex(TypeError, "PlaylistEntry"):
                DisplayPlaylist(entries=[ExampleDisplayItem()], app_folders=[])
            with self.assertRaisesRegex(TypeError, "DisplayItem"):
                DisplayPlaylist(entries=[PlaylistEntry(basic, duration)], app_folders=[])
        self.assertTrue(playlist.is_empty)

    def test_legacy_frequency_constructor_is_rejected(self):
        with self.assertRaises(TypeError):
            DisplayPlaylist(frequency=UpdateFrequency(seconds=30))

    def test_default_and_empty_app_sources(self):
        playlist = self.make_playlist()
        self.assertEqual(set(playlist.available_apps), {"DateTimeApp", "TemperatureApp", "StaticDisplayItem"})
        self.assertTrue(issubclass(playlist.apps.get_app_class("DateTimeApp"), DisplayItem))
        empty = self.make_playlist(app_folders=[])
        self.assertEqual(empty.available_apps, [])

    def test_display_setup_is_required_before_activation(self):
        playlist = self.make_playlist(app_folders=[])
        item = ExampleDisplayItem()
        playlist.add_entry(item, UpdateFrequency(seconds=10))
        for message, configure in (
            ("No display info", lambda: playlist.add_display_info(self.info)),
            ("add_display_function", lambda: playlist.add_display_function(self.display)),
            ("add_resolve_function", lambda: playlist.add_resolve_function(self.resolve)),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(RuntimeError, message):
                    playlist.start()
                self.assertFalse(playlist.is_active)
                self.assertFalse(item.is_active)
                self.assertIsNone(playlist.trigger)
                configure()
        playlist.start()
        self.display.assert_called_once()

    def test_empty_playlist_uses_core_start_validation(self):
        playlist = self.make_playlist(app_folders=[])
        self.configure(playlist)
        with self.assertRaises(PlaylistEmptyError):
            playlist.start()
        self.assertFalse(playlist.is_active)

    def test_variable_durations_render_switch_and_wrap(self):
        a = ExampleDisplayItem()
        b = StaticDisplayItem("B", {(1, 2): 3}, needs_resolving=False)
        first = PlaylistEntry(a, UpdateFrequency(minutes=1))
        second = PlaylistEntry(b, UpdateFrequency(seconds=10))
        playlist = self.make_playlist(entries=[first, second], app_folders=[])
        self.configure(playlist)
        playlist.start()
        self.display.assert_called_with({(1, 1): 2})
        self.assertEqual(self.timers[-1].interval, 60)
        self.timers[-1].fire()
        self.assertIs(playlist.current_entry, second)
        self.assertFalse(a.is_active)
        self.assertTrue(b.is_active)
        self.display.assert_called_with({(1, 2): 3})
        self.assertEqual(self.timers[-1].interval, 10)
        self.timers[-1].fire()
        self.assertIs(playlist.current_entry, first)
        self.assertEqual(a.calls, 2)
        self.assertEqual(self.display.call_count, 3)
        self.assertEqual(self.timers[-1].interval, 60)
        pending = self.timers[-1]
        playlist.stop()
        pending.fire()
        self.assertFalse(a.is_active)
        self.assertEqual(self.display.call_count, 3)

    def test_clock_refresh_schedule_is_independent_of_display_duration(self):
        playlist = self.make_playlist()
        self.configure(playlist)
        clock = playlist.apps.instantiate_app("DateTimeApp")
        playlist.add_entry(clock, UpdateFrequency(minutes=1))
        static = StaticDisplayItem("Static", {(1, 1): 3}, needs_resolving=False)
        playlist.add_entry(static, UpdateFrequency(seconds=10))
        playlist.start()
        refresh, countdown = self.timers
        self.assertEqual(refresh.interval, 10)
        self.assertEqual(countdown.interval, 60)
        refresh.fire()
        self.assertEqual(self.display.call_count, 2)
        pending_refresh = self.timers[-1]
        countdown.fire()
        pending_refresh.fire()
        self.assertIs(playlist.current_item, static)
        self.assertFalse(clock.trigger.is_active)
        self.assertEqual(self.display.call_count, 3)
        self.assertEqual(self.timers[-1].interval, 10)

    def test_display_configuration_can_be_replaced_while_stopped(self):
        playlist = self.make_playlist(app_folders=[])
        item = ExampleDisplayItem()
        playlist.add_entry(item, UpdateFrequency(seconds=10))
        self.configure(playlist)
        info = DisplayInfo(rows=1, columns=5, modules=[])
        resolve = Mock(return_value={(1, 1): 4})
        resolve.__name__ = "new_resolve"
        display = Mock()
        display.__name__ = "new_display"
        playlist.add_display_info(info)
        playlist.add_resolve_function(resolve)
        playlist.add_display_function(display)
        playlist.start()
        self.assertIs(item.display_info_received, info)
        resolve.assert_called_once()
        display.assert_called_once_with({(1, 1): 4})
        self.resolve.assert_not_called()
        self.display.assert_not_called()

    def test_entry_and_configuration_changes_require_stopped_playback(self):
        item = ExampleDisplayItem()
        playlist = self.make_playlist(entries=[PlaylistEntry(item, UpdateFrequency(seconds=10))], app_folders=[])
        self.configure(playlist)
        playlist.start()
        new_display = Mock()
        new_display.__name__ = "replacement"
        for change in (
            lambda: playlist.add_display_info(DisplayInfo(1, 1, [])),
            lambda: playlist.add_resolve_function(self.resolve),
            lambda: playlist.add_display_function(new_display),
            lambda: playlist.add_entry(ExampleDisplayItem(), UpdateFrequency(seconds=10)),
            lambda: playlist.remove_entry(0),
        ):
            with self.assertRaisesRegex(RuntimeError, "Stop the playlist"):
                change()
        self.assertEqual(playlist.size, 1)
        new_display.assert_not_called()
        playlist.stop()
        playlist.add_display_function(new_display)
        playlist.start()
        new_display.assert_called_once()


if __name__ == "__main__":
    unittest.main()
