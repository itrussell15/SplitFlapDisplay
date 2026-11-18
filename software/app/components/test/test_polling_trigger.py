import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.components.core.playlist import PlaylistItem
from app.components.core.trigger import PollingTrigger
from app.components.core.updater import TimeStatus, UpdateFrequency
from app.components.test.test_interval_trigger import ControlledTimer


class TestPollingTrigger(unittest.TestCase):
    def setUp(self) -> None:
        self.timers = []

        def create_timer(*args, **kwargs):
            timer = ControlledTimer(*args, **kwargs)
            self.timers.append(timer)
            return timer

        timer_patch = patch(
            "app.components.core.trigger.threading.Timer", side_effect=create_timer
        )
        timer_patch.start()
        self.addCleanup(timer_patch.stop)
        self.callback = Mock()
        self.evaluation = Mock(return_value=False)
        self.frequency = UpdateFrequency(seconds=5)
        self.trigger = PollingTrigger(self.callback, self.frequency, self.evaluation)
        self.addCleanup(self.trigger.stop)

    def test_requires_a_callable_evaluation(self) -> None:
        with self.assertRaisesRegex(TypeError, "evaluation must be callable"):
            PollingTrigger(self.callback, self.frequency, None)

    def test_start_schedules_poll_without_evaluating_immediately(self) -> None:
        self.assertFalse(self.trigger.invoke())
        self.trigger.start()
        self.trigger.start()
        self.assertTrue(self.trigger.is_active)
        self.evaluation.assert_not_called()
        self.callback.assert_not_called()
        self.assertEqual(len(self.timers), 1)
        self.assertEqual(self.timers[0].interval, 5)

    def test_polls_repeatedly_and_calls_callback_for_each_true_result(self) -> None:
        self.evaluation.side_effect = [False, True, True, False]
        self.trigger.start()
        for poll_number, callbacks in enumerate((0, 1, 2, 2), start=1):
            self.timers[-1].fire()
            self.assertEqual(self.evaluation.call_count, poll_number)
            self.assertEqual(self.callback.call_count, callbacks)
            self.assertEqual(len(self.timers), poll_number + 1)
            self.assertTrue(self.trigger.is_active)
        self.evaluation.assert_called_with()
        self.callback.assert_called_with()

    def test_explicit_invocation_returns_whether_callback_ran(self) -> None:
        self.trigger.start()
        self.assertFalse(self.trigger.invoke())
        self.callback.assert_not_called()
        self.evaluation.return_value = True
        self.assertTrue(self.trigger.invoke())
        self.callback.assert_called_once_with()
        self.assertEqual(self.evaluation.call_count, 2)

    def test_frequency_changes_apply_to_next_poll(self) -> None:
        self.assertIs(self.trigger.frequency, self.frequency)
        self.trigger.start()
        self.frequency.seconds = 10
        self.assertEqual(self.timers[-1].interval, 5)
        self.timers[-1].fire()
        self.assertEqual(self.timers[-1].interval, 10)

    def test_stale_timer_does_not_evaluate_after_stop_or_restart(self) -> None:
        self.trigger.start()
        old_timer = self.timers[-1]
        self.trigger.stop()
        old_timer.fire()
        self.trigger.start()
        old_timer.fire()
        self.evaluation.assert_not_called()
        self.callback.assert_not_called()
        self.assertEqual(len(self.timers), 2)
        self.timers[-1].fire()
        self.evaluation.assert_called_once_with()

    def test_evaluation_can_stop_and_its_true_result_is_discarded(self) -> None:
        def evaluation():
            self.trigger.stop()
            return True

        self.evaluation.side_effect = evaluation
        self.trigger.start()
        self.assertFalse(self.trigger.invoke())
        self.callback.assert_not_called()
        self.assertFalse(self.trigger.is_active)
        self.assertEqual(len(self.timers), 1)

    def test_evaluation_can_restart_and_old_result_is_discarded(self) -> None:
        def evaluation():
            self.trigger.stop()
            self.trigger.start()
            return True

        self.evaluation.side_effect = evaluation
        self.trigger.start()
        self.timers[-1].fire()
        self.callback.assert_not_called()
        self.assertEqual(len(self.timers), 2)
        self.evaluation.side_effect = None
        self.evaluation.return_value = True
        self.timers[-1].fire()
        self.callback.assert_called_once_with()

    def test_overlapping_evaluation_is_skipped(self) -> None:
        def evaluation():
            self.assertFalse(self.trigger.invoke())
            return True

        self.evaluation.side_effect = evaluation
        self.trigger.start()
        self.assertTrue(self.trigger.invoke())
        self.evaluation.assert_called_once_with()
        self.callback.assert_called_once_with()

    def test_background_errors_are_logged_and_polling_continues(self) -> None:
        self.trigger.start()
        for failing_function in (self.evaluation, self.callback):
            with self.subTest(failing_function=failing_function):
                self.evaluation.return_value = True
                failing_function.side_effect = ValueError("poll failed")
                with self.assertLogs("PollingTrigger", level="ERROR") as logs:
                    self.timers[-1].fire()
                self.assertIn("poll failed", logs.output[0])
                self.assertTrue(self.trigger.is_active)
                failing_function.side_effect = None
                count = self.callback.call_count
                self.timers[-1].fire()
                self.assertEqual(self.callback.call_count, count + 1)

    def test_explicit_errors_propagate_and_allow_later_polls(self) -> None:
        self.trigger.start()
        for failing_function in (self.evaluation, self.callback):
            with self.subTest(failing_function=failing_function):
                self.evaluation.return_value = True
                failing_function.side_effect = ValueError("poll failed")
                with self.assertRaisesRegex(ValueError, "poll failed"):
                    self.trigger.invoke()
                failing_function.side_effect = None
                self.assertTrue(self.trigger.invoke())

    def test_item_can_use_polling_trigger_factory(self) -> None:
        class Item(PlaylistItem):
            def update(self):
                self.calls += 1

        item = Item(
            "polling item",
            trigger_factory=lambda callback: PollingTrigger(
                callback, self.frequency, self.evaluation
            ),
        )
        item.calls = 0
        self.addCleanup(item.deactivate)
        item.activate(update_on_start=False)
        self.timers[-1].fire()
        self.assertEqual(item.calls, 0)
        self.evaluation.return_value = True
        self.timers[-1].fire()
        self.assertEqual(item.calls, 1)


class TestPollingTriggerCooldown(unittest.TestCase):
    def setUp(self) -> None:
        self.timers = []

        def create_timer(*args, **kwargs):
            timer = ControlledTimer(*args, **kwargs)
            self.timers.append(timer)
            return timer

        timer_patch = patch(
            "app.components.core.trigger.threading.Timer", side_effect=create_timer
        )
        timer_patch.start()
        self.addCleanup(timer_patch.stop)
        clock_patch = patch("app.components.core.trigger.time.time", return_value=100.0)
        self.clock = clock_patch.start()
        self.addCleanup(clock_patch.stop)
        self.callback = Mock()
        self.evaluation = Mock(return_value=True)
        self.cooldown = UpdateFrequency(seconds=10)
        self.trigger = PollingTrigger(
            self.callback,
            frequency=UpdateFrequency(seconds=0.1),
            evaluation=self.evaluation,
            cooldown=self.cooldown,
        )
        self.addCleanup(self.trigger.stop)

    def test_cooldown_requires_an_update_frequency_or_none(self) -> None:
        for cooldown in (5, 0.5, "5"):
            with self.subTest(cooldown=cooldown):
                with self.assertRaisesRegex(TypeError, "must be an UpdateFrequency"):
                    PollingTrigger(self.callback, self.trigger.frequency, self.evaluation, cooldown)

    def test_cooldown_requires_a_positive_finite_interval(self) -> None:
        for seconds in (0, -1, float("nan"), float("inf")):
            with self.subTest(seconds=seconds):
                with self.assertRaises(ValueError):
                    PollingTrigger(
                        self.callback,
                        self.trigger.frequency,
                        self.evaluation,
                        cooldown=UpdateFrequency(seconds=seconds),
                    )

    def test_frequent_true_polls_do_not_extend_cooldown(self) -> None:
        self.trigger.start()
        for poll, (timestamp, callbacks) in enumerate(
            ((100, 1), (100.1, 1), (105, 1), (109.999, 1), (110, 2)), start=1
        ):
            self.clock.return_value = timestamp
            self.timers[-1].fire()
            self.assertEqual(self.callback.call_count, callbacks)
            self.assertEqual(self.evaluation.call_count, poll)
            self.assertEqual(len(self.timers), poll + 1)
        self.assertEqual(self.trigger.cooldown_status.end, 120)

    def test_time_status_exposes_cooldown_elapsed_and_remaining_time(self) -> None:
        self.assertIs(self.trigger.cooldown, self.cooldown)
        self.assertIsNone(self.trigger.cooldown_status)
        self.assertEqual(self.trigger.cooldown_remaining, 0)
        self.assertFalse(self.trigger.is_cooling_down)
        self.trigger.start()
        self.assertTrue(self.trigger.invoke())
        status = self.trigger.cooldown_status
        self.assertIsInstance(status, TimeStatus)
        self.assertEqual(status.start, 100)
        self.assertEqual(status.end, 110)
        self.clock.return_value = 103
        self.assertEqual(status.elapsed, 3)
        self.assertEqual(status.remaining, 7)
        self.assertEqual(self.trigger.cooldown_remaining, 7)
        self.assertTrue(self.trigger.is_cooling_down)
        self.assertFalse(self.trigger.invoke())
        self.assertIs(self.trigger.cooldown_status, status)
        self.clock.return_value = 110
        self.assertEqual(self.trigger.cooldown_remaining, 0)
        self.assertFalse(self.trigger.is_cooling_down)
        self.assertTrue(self.trigger.invoke())
        self.assertIsNot(self.trigger.cooldown_status, status)

    def test_false_results_do_not_start_or_extend_cooldown(self) -> None:
        self.evaluation.return_value = False
        self.trigger.start()
        self.assertFalse(self.trigger.invoke())
        self.assertIsNone(self.trigger.cooldown_status)
        self.evaluation.return_value = True
        self.trigger.invoke()
        self.clock.return_value = 105
        self.evaluation.return_value = False
        self.assertFalse(self.trigger.invoke())
        self.assertEqual(self.trigger.cooldown_status.end, 110)
        self.clock.return_value = 110
        self.evaluation.return_value = True
        self.assertTrue(self.trigger.invoke())
        self.assertEqual(self.callback.call_count, 2)

    def test_failed_callback_still_starts_cooldown(self) -> None:
        self.callback.side_effect = ValueError("update failed")
        self.trigger.start()
        with self.assertRaisesRegex(ValueError, "update failed"):
            self.trigger.invoke()
        self.assertTrue(self.trigger.is_cooling_down)
        self.callback.side_effect = None
        self.assertFalse(self.trigger.invoke())
        self.callback.assert_called_once_with()
        self.clock.return_value = 110
        self.assertTrue(self.trigger.invoke())

    def test_failed_evaluation_does_not_start_cooldown(self) -> None:
        self.evaluation.side_effect = ValueError("evaluation failed")
        self.trigger.start()
        with self.assertRaisesRegex(ValueError, "evaluation failed"):
            self.trigger.invoke()
        self.assertIsNone(self.trigger.cooldown_status)
        self.evaluation.side_effect = None
        self.assertTrue(self.trigger.invoke())
        self.callback.assert_called_once_with()

    def test_cooldown_persists_across_stop_and_restart(self) -> None:
        self.trigger.start()
        self.trigger.invoke()
        status = self.trigger.cooldown_status
        self.clock.return_value = 105
        self.trigger.stop()
        self.assertFalse(self.trigger.invoke())
        self.trigger.start()
        self.trigger.start()
        self.assertFalse(self.trigger.invoke())
        self.assertIs(self.trigger.cooldown_status, status)
        self.callback.assert_called_once_with()
        self.clock.return_value = 110
        self.assertTrue(self.trigger.invoke())

    def test_cooldown_configuration_changes_apply_to_next_accepted_result(self) -> None:
        self.trigger.start()
        self.trigger.invoke()
        self.cooldown.seconds = 20
        self.assertEqual(self.trigger.cooldown_status.end, 110)
        self.clock.return_value = 110
        self.assertTrue(self.trigger.invoke())
        self.assertEqual(self.trigger.cooldown_status.end, 130)

    def test_discarded_evaluation_does_not_start_cooldown(self) -> None:
        def evaluation():
            self.trigger.stop()
            return True

        self.evaluation.side_effect = evaluation
        self.trigger.start()
        self.assertFalse(self.trigger.invoke())
        self.assertIsNone(self.trigger.cooldown_status)
        self.callback.assert_not_called()


class TestPollingTriggerThreads(unittest.TestCase):
    def test_real_timer_polls_false_and_true_results(self) -> None:
        done = threading.Event()
        evaluation = Mock(side_effect=[False, True, False, True])
        calls = []

        def callback():
            calls.append(threading.current_thread())
            if len(calls) == 2:
                trigger.stop()
                done.set()

        trigger = PollingTrigger(callback, UpdateFrequency(seconds=0.01), evaluation)
        self.addCleanup(trigger.stop)
        trigger.start()
        self.assertTrue(done.wait(2), "Polling did not deliver two callbacks")
        self.assertEqual(evaluation.call_count, 4)
        self.assertEqual(len(calls), 2)
        self.assertFalse(trigger.is_active)

    def test_stop_and_restart_during_evaluation_discards_old_result(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        done = threading.Event()
        evaluation = Mock()
        callback = Mock()
        errors = []

        def evaluate():
            entered.set()
            if not release.wait(2):
                errors.append("Evaluation was not released")
            return True

        evaluation.side_effect = evaluate
        trigger = PollingTrigger(callback, UpdateFrequency(seconds=5), evaluation)
        self.addCleanup(trigger.stop)
        self.addCleanup(release.set)
        trigger.start()

        def invoke():
            try:
                if trigger.invoke():
                    errors.append("Old evaluation invoked callback")
            finally:
                done.set()

        worker = threading.Thread(target=invoke, daemon=True)
        worker.start()
        self.assertTrue(entered.wait(2), "Evaluation did not start")
        trigger.stop()
        trigger.start()
        self.assertFalse(trigger.invoke())
        release.set()
        self.assertTrue(done.wait(2), "Evaluation did not finish")
        worker.join(2)
        callback.assert_not_called()
        self.assertEqual(errors, [])
        evaluation.side_effect = None
        evaluation.return_value = True
        self.assertTrue(trigger.invoke())
        callback.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
