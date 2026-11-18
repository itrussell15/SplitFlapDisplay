import datetime
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.components.core.app_loader import AppLoader
from app.components.core.trigger import IntervalTrigger, ManualTrigger, PollingTrigger
from app.components.core.updater import UpdateFrequency
from app.components.display.base_apps.clock import DateTimeApp
from app.components.display.base_apps.static import StaticDisplayItem
from app.components.display.base_apps.weather import TemperatureApp
from app.components.display.display_item import DisplayItem
from app.components.test.test_interval_trigger import ControlledTimer
from control.source.display_controller import DisplayInfo


DISPLAY_PATH = Path(__file__).resolve().parents[1] / "display"


class TestExampleApps(unittest.TestCase):
    def setUp(self):
        self.info = DisplayInfo(rows=3, columns=15, modules=[])
        self.timers = []

        def create_timer(*args, **kwargs):
            timer = ControlledTimer(*args, **kwargs)
            self.timers.append(timer)
            return timer

        timer_patch = patch("app.components.core.trigger.threading.Timer", side_effect=create_timer)
        timer_patch.start()
        self.addCleanup(timer_patch.stop)

    def make_weather(self, **kwargs):
        return TemperatureApp(api_key="test-key", lat="0", lon="0", **kwargs)

    def configure(self, item):
        outputs = []
        item.add_display_info(self.info)
        item.add_resolve_function(lambda flaps: flaps)
        item.add_display_function(outputs.append)
        self.addCleanup(item.deactivate)
        return outputs

    def load_apps(self):
        with patch("builtins.print"):
            return AppLoader(DisplayItem, sources=[str(DISPLAY_PATH / "base_apps")])

    def test_default_schedules_and_static_initial_update(self):
        for item, seconds in ((DateTimeApp(), 10), (self.make_weather(), 60)):
            with self.subTest(app=type(item).__name__):
                self.assertIsInstance(item.trigger, IntervalTrigger)
                self.assertEqual(item.trigger.frequency.interval, seconds)
                self.assertFalse(item.trigger.is_active)
        item = StaticDisplayItem("Example", {(1, 1): 3}, needs_resolving=False)
        outputs = self.configure(item)
        item.activate()
        item.activate()
        self.assertIsNone(item.trigger)
        self.assertEqual(outputs, [{(1, 1): 3}])
        self.assertTrue(item.is_active)
        self.assertEqual(self.timers, [])

    def test_default_factories_create_independent_schedules(self):
        for factory in (DateTimeApp, self.make_weather):
            with self.subTest(app=factory.__name__):
                first, second = factory(), factory()
                self.assertIsNot(first.trigger, second.trigger)
                self.assertIsNot(first.trigger.frequency, second.trigger.frequency)
                original_interval = second.trigger.frequency.interval
                first.trigger.frequency.seconds = 99
                self.assertEqual(second.trigger.frequency.interval, original_interval)

    def test_explicit_none_disables_recurring_updates(self):
        for factory in (DateTimeApp, self.make_weather):
            item = factory(trigger_factory=None)
            outputs = self.configure(item)
            if isinstance(item, TemperatureApp):
                item.get_data = Mock(return_value=SimpleNamespace(temp=21, unit="imperial"))
            item.activate()
            self.assertIsNone(item.trigger)
            self.assertEqual(len(outputs), 1)
            self.assertTrue(item.is_active)
        self.assertEqual(self.timers, [])

    def test_custom_factories_bind_each_apps_display_callback(self):
        factories = (
            DateTimeApp,
            self.make_weather,
            lambda **kwargs: StaticDisplayItem("Example", {(1, 1): "A"}, **kwargs),
        )
        for factory in factories:
            with self.subTest(app=factory.__name__):
                item = factory(trigger_factory=ManualTrigger)
                outputs = self.configure(item)
                if isinstance(item, TemperatureApp):
                    item.get_data = Mock(return_value=SimpleNamespace(temp=21, unit="imperial"))
                self.assertFalse(item.trigger.invoke())
                item.activate(update_on_start=False)
                self.assertEqual(outputs, [])
                self.assertTrue(item.trigger.invoke())
                self.assertEqual(len(outputs), 1)
                item.deactivate()
                self.assertFalse(item.trigger.invoke())
                self.assertEqual(len(outputs), 1)

    def test_default_intervals_repeat_and_stop_rendering(self):
        for factory, seconds in ((DateTimeApp, 10), (self.make_weather, 60)):
            with self.subTest(app=factory.__name__):
                item = factory()
                outputs = self.configure(item)
                if isinstance(item, TemperatureApp):
                    item.get_data = Mock(return_value=SimpleNamespace(temp=21, unit="imperial"))
                item.activate()
                self.assertEqual(len(outputs), 1)
                for expected_count in (2, 3):
                    self.assertEqual(self.timers[-1].interval, seconds)
                    self.assertTrue(self.timers[-1].started)
                    self.timers[-1].fire()
                    self.assertEqual(len(outputs), expected_count)
                pending_timer = self.timers[-1]
                item.deactivate()
                pending_timer.fire()
                self.assertTrue(pending_timer.cancelled)
                self.assertEqual(len(outputs), 3)

    def test_clock_generates_content_through_the_trigger(self):
        item = DateTimeApp(trigger_factory=ManualTrigger)
        outputs = self.configure(item)
        with patch("app.components.display.base_apps.clock.datetime") as clock:
            clock.datetime.now.return_value = datetime.datetime(2026, 11, 18, 9, 30)
            item.activate(update_on_start=False)
            item.trigger.invoke()
        self.assertEqual(len(outputs[0]), 45)
        for row, expected in ((1, "NOV 18 2026"), (2, "WEDNESDAY"), (3, "9:30AM")):
            content = "".join(value for (r, _), value in sorted(outputs[0].items()) if r == row and value != "BLANK")
            self.assertEqual(content.strip(), expected)

    def test_weather_refreshes_data_on_each_trigger_invocation(self):
        item = self.make_weather(trigger_factory=ManualTrigger)
        outputs = self.configure(item)
        item.get_data = Mock(side_effect=[
            SimpleNamespace(temp=21, unit="imperial"),
            SimpleNamespace(temp=22, unit="metric"),
        ])
        item.activate()
        item.trigger.invoke()
        self.assertEqual(item.get_data.call_count, 2)
        self.assertEqual(outputs, [
            {(1, 1): "2", (1, 2): "1", (1, 3): "DEGREE", (1, 4): "F"},
            {(1, 1): "2", (1, 2): "2", (1, 3): "DEGREE", (1, 4): "C"},
        ])

    def test_polling_factory_cooldown_throttles_example_output(self):
        item = StaticDisplayItem("Polling", {(1, 1): "A"}, trigger_factory=lambda callback: PollingTrigger(
            callback,
            frequency=UpdateFrequency(seconds=0.1),
            evaluation=lambda: True,
            cooldown=UpdateFrequency(seconds=5),
        ))
        outputs = self.configure(item)
        with patch("app.components.core.trigger.time.time", return_value=100) as clock:
            item.activate(update_on_start=False)
            self.timers[-1].fire()
            clock.return_value = 100.1
            self.timers[-1].fire()
            self.assertEqual(len(outputs), 1)
            clock.return_value = 105
            self.timers[-1].fire()
        self.assertEqual(len(outputs), 2)

    def test_factories_are_excluded_from_serialized_parameters(self):
        items = (DateTimeApp(), self.make_weather(), StaticDisplayItem("Example", {(1, 1): "A"}))
        for item in items:
            self.assertNotIn("trigger_factory", item.params)
            self.assertNotIn("frequency", item.params)
        loader = self.load_apps()
        self.assertEqual(set(loader.list()), {"DateTimeApp", "TemperatureApp", "StaticDisplayItem"})
        parameters = {name: loader.get(name).parameters for name in loader.list()}
        for params in parameters.values():
            self.assertNotIn("trigger_factory", params)
        json.dumps(parameters)

    def test_playlist_example_app_arguments_use_current_constructors(self):
        loader = self.load_apps()
        data = json.loads((DISPLAY_PATH / "examples" / "playlist.json").read_text())
        for entry in data["items"]:
            if entry["item_type"].lower() == "app":
                item = loader.instantiate_app(entry["app_name"], **entry.get("args", {}))
                self.assertIsInstance(item.trigger, IntervalTrigger)
            else:
                flaps = {(module["location"]["row"], module["location"]["column"]): module["flap"] for module in entry["modules"]}
                item = StaticDisplayItem(name=entry["name"], flaps=flaps)
                self.assertIsNone(item.trigger)
            self.assertIsInstance(item, DisplayItem)

    def test_standalone_static_json_examples_use_constructor(self):
        for path in sorted((DISPLAY_PATH / "examples").glob("static_example*.json")):
            with self.subTest(example=path.name):
                data = json.loads(path.read_text())
                flaps = {(module["location"]["row"], module["location"]["column"]): module["flap"] for module in data["data"]}
                item = StaticDisplayItem(name=data["name"], flaps=flaps)
                outputs = self.configure(item)
                item.activate()
                self.assertEqual(outputs, [flaps])
                self.assertEqual(len(flaps), 5)


if __name__ == "__main__":
    unittest.main()
