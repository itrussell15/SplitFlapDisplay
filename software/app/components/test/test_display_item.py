import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.components.core.trigger import IntervalTrigger, ManualTrigger, OneShotTrigger, PollingTrigger
from app.components.core.updater import UpdateFrequency
from app.components.display.display_item import DisplayItem, DisplayItemType, DisplayItemUpdate
from app.components.test.test_interval_trigger import ControlledTimer
from control.source.display_controller import DisplayInfo


class ExampleDisplayItem(DisplayItem):
    def __init__(self, trigger_factory=None):
        super().__init__(
            name="example",
            item_type=DisplayItemType.APP,
            params={"trigger_factory": trigger_factory, "label": "example"},
            trigger_factory=trigger_factory,
        )
        self.calls = 0
        self.display_info_received = None
        self.response = DisplayItemUpdate({(1, 1): "A"})
        self.update_action = None

    def update(self, display_info):
        self.calls += 1
        self.display_info_received = display_info
        if self.update_action is not None:
            return self.update_action(display_info)
        return self.response


class TestDisplayItem(unittest.TestCase):
    def setUp(self):
        self.info = DisplayInfo(rows=3, columns=15, modules=[])
        self.resolve = Mock(return_value={(1, 1): 2})
        self.resolve.__name__ = "resolve"
        self.display = Mock()
        self.display.__name__ = "display"

    def make_item(self, trigger_factory=None):
        item = ExampleDisplayItem(trigger_factory)
        item.add_display_info(self.info)
        item.add_resolve_function(self.resolve)
        item.add_display_function(self.display)
        self.addCleanup(item.deactivate)
        return item

    def test_no_trigger_renders_once_and_item_stays_active(self):
        item = self.make_item()
        self.assertIsNone(item.trigger)
        item.activate()
        item.activate()
        self.assertTrue(item.is_active)
        self.assertFalse(item.is_updating)
        self.assertEqual(item.calls, 1)
        self.assertIs(item.display_info_received, self.info)
        self.display.assert_called_once_with({(1, 1): 2})
        item.deactivate()
        item.activate()
        self.assertEqual(item.calls, 2)

    def test_factory_binds_render_pipeline_to_trigger(self):
        item = self.make_item(ManualTrigger)
        item.activate()
        self.assertTrue(item.trigger.is_active)
        self.assertTrue(item.trigger.invoke())
        self.assertEqual(item.calls, 2)
        self.assertEqual(self.display.call_count, 2)
        self.assertIs(item.display_info_received, self.info)
        item.deactivate()
        self.assertFalse(item.trigger.is_active)
        self.assertFalse(item.trigger.invoke())

    def test_accepts_factory_and_excludes_it_from_parameters(self):
        item = self.make_item(ManualTrigger)
        self.assertEqual(item.params, {"label": "example"})
        with self.assertRaisesRegex(TypeError, "frequency"):
            DisplayItem.__init__(item, "old", DisplayItemType.APP, {}, frequency=UpdateFrequency(seconds=5))

    def test_activation_can_skip_initial_update(self):
        item = self.make_item(ManualTrigger)
        item.activate(update_on_start=False)
        self.display.assert_not_called()
        self.assertEqual(item.calls, 0)
        item.trigger.invoke()
        self.display.assert_called_once()

    def test_inactive_item_ignores_execution(self):
        item = self.make_item()
        item._execute_update()
        item.activate()
        item.deactivate()
        item._execute_update()
        self.assertEqual(item.calls, 1)
        self.display.assert_called_once()

    def test_no_output_skips_resolving_and_rendering(self):
        item = self.make_item(ManualTrigger)
        item.response = None
        item.activate()
        item.trigger.invoke()
        self.assertEqual(item.calls, 2)
        self.assertFalse(item.is_updating)
        self.assertTrue(item.is_active)
        self.resolve.assert_not_called()
        self.display.assert_not_called()

    def test_position_output_bypasses_resolver(self):
        item = self.make_item()
        item.response = DisplayItemUpdate({(1, 1): 7}, needs_resolving=False)
        item.activate()
        self.resolve.assert_not_called()
        self.display.assert_called_once_with({(1, 1): 7})

    def test_resolving_does_not_replace_the_generated_request(self):
        item = self.make_item(ManualTrigger)
        request = item.response
        item.activate()
        item.trigger.invoke()
        self.assertEqual(request.flaps, {(1, 1): "A"})
        self.assertTrue(request.needs_resolving)
        self.assertEqual(self.resolve.call_count, 2)
        self.resolve.assert_called_with({(1, 1): "A"})

    def test_display_prerequisites_are_checked_before_activation(self):
        item = ExampleDisplayItem(ManualTrigger)
        self.addCleanup(item.deactivate)
        for expected_error, configure in (
            ("No display info", lambda: item.add_display_info(self.info)),
            ("No display function", lambda: item.add_display_function(self.display)),
            ("No display function", lambda: item.add_resolve_function(self.resolve)),
        ):
            with self.subTest(expected_error=expected_error):
                with self.assertRaisesRegex(RuntimeError, expected_error):
                    item.activate()
                self.assertFalse(item.is_active)
                self.assertFalse(item.trigger.is_active)
                configure()
        item.activate()
        self.display.assert_called_once()

    def test_initial_update_errors_preserve_original_error_and_cleanup_state(self):
        for stage in ("generation", "resolving", "rendering"):
            with self.subTest(stage=stage):
                item = self.make_item(ManualTrigger)
                error = ValueError(f"{stage} failed")
                if stage == "generation":
                    def fail(display_info):
                        raise error
                    item.update_action = fail
                elif stage == "resolving":
                    self.resolve.side_effect = error
                else:
                    self.display.side_effect = error
                with self.assertRaisesRegex(ValueError, f"{stage} failed"):
                    item.activate()
                self.assertFalse(item.is_active)
                self.assertFalse(item.is_updating)
                self.assertFalse(item.trigger.is_active)
                item.update_action = None
                self.resolve.side_effect = None
                self.display.side_effect = None
                item.activate()
                self.assertTrue(item.is_active)
                item.deactivate()

    def test_later_callback_error_does_not_leave_item_updating(self):
        item = self.make_item(ManualTrigger)
        item.activate()
        self.display.side_effect = ValueError("render failed")
        with self.assertRaisesRegex(ValueError, "render failed"):
            item.trigger.invoke()
        self.assertFalse(item.is_updating)
        self.assertTrue(item.is_active)
        self.display.side_effect = None
        self.assertTrue(item.trigger.invoke())

    def test_one_shot_completion_does_not_deactivate_item(self):
        item = self.make_item(lambda callback: OneShotTrigger(callback, UpdateFrequency(seconds=10)))
        item.activate()
        item.trigger.invoke()
        self.assertFalse(item.trigger.is_active)
        self.assertTrue(item.is_active)
        self.assertEqual(item.calls, 2)

    def test_interval_trigger_repeatedly_runs_display_pipeline(self):
        timers = []
        def timer_factory(*args, **kwargs):
            timer = ControlledTimer(*args, **kwargs)
            timers.append(timer)
            return timer
        with patch("app.components.core.trigger.threading.Timer", side_effect=timer_factory):
            item = self.make_item(lambda callback: IntervalTrigger(callback, UpdateFrequency(seconds=5)))
            item.activate()
            timers[-1].fire()
            self.assertEqual(item.calls, 2)
            self.assertEqual(self.display.call_count, 2)
            pending_timer = timers[-1]
            item.deactivate()
            pending_timer.fire()
            self.assertTrue(pending_timer.cancelled)
            self.assertEqual(item.calls, 2)

    def test_polling_trigger_cooldown_limits_rendering(self):
        item = self.make_item(lambda callback: PollingTrigger(
            callback,
            frequency=UpdateFrequency(seconds=0.1),
            evaluation=lambda: True,
            cooldown=UpdateFrequency(seconds=5),
        ))
        with (
            patch("app.components.core.trigger.threading.Timer", side_effect=ControlledTimer),
            patch("app.components.core.trigger.time.time", return_value=100) as clock,
        ):
            item.activate(update_on_start=False)
            self.assertTrue(item.trigger.invoke())
            clock.return_value = 100.1
            self.assertFalse(item.trigger.invoke())
            clock.return_value = 105
            self.assertTrue(item.trigger.invoke())
        self.assertEqual(self.display.call_count, 2)

    def test_running_update_is_not_duplicated_or_rendered_after_reactivation(self):
        item = self.make_item(ManualTrigger)
        entered = threading.Event()
        release = threading.Event()
        done = threading.Event()
        errors = []
        self.addCleanup(release.set)

        def generate(display_info):
            entered.set()
            if not release.wait(2):
                errors.append("Generation was not released")
            return DisplayItemUpdate({(1, 1): "A"})

        def execute():
            try:
                item._execute_update()
            except Exception as error:
                errors.append(str(error))
            finally:
                done.set()

        item.update_action = generate
        item.activate(update_on_start=False)
        worker = threading.Thread(target=execute, daemon=True)
        worker.start()
        self.assertTrue(entered.wait(2), "Generation did not start")
        self.assertTrue(item.is_updating)
        item._execute_update()
        self.assertEqual(item.calls, 1)
        item.deactivate()
        item.activate(update_on_start=False)
        release.set()
        self.assertTrue(done.wait(2), "Generation did not finish")
        worker.join(2)
        self.display.assert_not_called()
        self.assertFalse(item.is_updating)
        self.assertTrue(item.is_active)
        self.assertEqual(errors, [])
        item.update_action = None
        item.trigger.invoke()
        self.display.assert_called_once()


if __name__ == "__main__":
    unittest.main()
