import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.components.core.trigger import IntervalTrigger
from app.components.core.updater import UpdateFrequency


class ControlledTimer:
    """Drive timer delivery explicitly, including a cancelled timer's race."""

    def __init__(self, interval, function, args=()) -> None:
        self.interval = interval
        self.function = function
        self.args = args
        self.daemon = False
        self.started = False
        self.cancelled = False

    def start(self) -> None:
        self.started = True

    def cancel(self) -> None:
        self.cancelled = True

    def fire(self) -> None:
        self.function(*self.args)


class TestIntervalTrigger(unittest.TestCase):
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
        self.frequency = UpdateFrequency(minutes=1, seconds=5)
        self.trigger = IntervalTrigger(self.callback, frequency=self.frequency)
        self.addCleanup(self.trigger.stop)

    def test_requires_an_update_frequency_object(self) -> None:
        for frequency in (2.5, None, "5"):
            with self.subTest(frequency=frequency):
                with self.assertRaisesRegex(TypeError, "must be an UpdateFrequency"):
                    IntervalTrigger(self.callback, frequency)

    def test_frequency_interval_must_be_positive_and_finite(self) -> None:
        for interval in (0, -1, float("nan"), float("inf"), -float("inf")):
            with self.subTest(interval=interval):
                with self.assertRaises(ValueError):
                    IntervalTrigger(self.callback, UpdateFrequency(seconds=interval))

    def test_frequency_changes_apply_to_next_timer(self) -> None:
        self.assertIs(self.trigger.frequency, self.frequency)
        self.trigger.start()
        self.frequency.seconds = 10
        self.assertEqual(self.timers[-1].interval, 65)
        self.timers[-1].fire()
        self.assertEqual(self.timers[-1].interval, 70)

    def test_start_schedules_one_delayed_callback(self) -> None:
        self.assertFalse(self.trigger.is_active)
        self.assertFalse(self.trigger.invoke())
        self.trigger.start()
        self.trigger.start()
        self.assertTrue(self.trigger.is_active)
        self.callback.assert_not_called()
        self.assertEqual(len(self.timers), 1)
        self.assertEqual(self.timers[0].interval, 65)
        self.assertTrue(self.timers[0].started)
        self.assertTrue(self.timers[0].daemon)

    def test_repeats_only_after_callback_finishes(self) -> None:
        self.trigger.start()
        for count in range(1, 4):
            def check_no_next_timer():
                self.assertEqual(len(self.timers), count)
                self.assertTrue(self.trigger.is_active)

            self.callback.side_effect = check_no_next_timer
            self.timers[-1].fire()
            self.assertEqual(self.callback.call_count, count)
            self.assertEqual(len(self.timers), count + 1)
            self.assertEqual(self.timers[-1].interval, self.trigger.frequency.interval)

    def test_stop_cancels_timer_and_ignores_late_delivery(self) -> None:
        self.trigger.start()
        timer = self.timers[-1]
        self.trigger.stop()
        self.trigger.stop()
        self.assertTrue(timer.cancelled)
        timer.fire()
        self.assertFalse(self.trigger.is_active)
        self.assertFalse(self.trigger.invoke())
        self.callback.assert_not_called()
        self.assertEqual(len(self.timers), 1)

    def test_restart_does_not_accept_old_timer_delivery(self) -> None:
        self.trigger.start()
        old_timer = self.timers[-1]
        self.trigger.stop()
        self.trigger.start()
        new_timer = self.timers[-1]
        old_timer.fire()
        self.callback.assert_not_called()
        self.assertEqual(len(self.timers), 2)
        new_timer.fire()
        self.callback.assert_called_once_with()
        self.assertEqual(len(self.timers), 3)

    def test_callback_can_stop_without_rescheduling(self) -> None:
        self.callback.side_effect = self.trigger.stop
        self.trigger.start()
        self.timers[-1].fire()
        self.callback.assert_called_once_with()
        self.assertFalse(self.trigger.is_active)
        self.assertEqual(len(self.timers), 1)

    def test_callback_can_restart_without_duplicating_schedule(self) -> None:
        def restart():
            self.trigger.stop()
            self.trigger.start()
            # The new run waits for this callback to finish.
            self.assertEqual(len(self.timers), 1)

        self.callback.side_effect = restart
        self.trigger.start()
        self.timers[-1].fire()
        self.assertTrue(self.trigger.is_active)
        self.assertEqual(len(self.timers), 2)
        self.callback.side_effect = None
        self.timers[-1].fire()
        self.assertEqual(self.callback.call_count, 2)
        self.assertEqual(len(self.timers), 3)

    def test_background_callback_error_is_logged_and_schedule_continues(self) -> None:
        self.callback.side_effect = ValueError("callback failed")
        self.trigger.start()
        with self.assertLogs("IntervalTrigger", level="ERROR") as logs:
            self.timers[-1].fire()
        self.assertIn("callback failed", logs.output[0])
        self.assertTrue(self.trigger.is_active)
        self.assertEqual(len(self.timers), 2)
        self.callback.side_effect = None
        self.timers[-1].fire()
        self.assertEqual(self.callback.call_count, 2)

    def test_explicit_callback_error_propagates_without_losing_schedule(self) -> None:
        self.callback.side_effect = ValueError("callback failed")
        self.trigger.start()
        with self.assertRaisesRegex(ValueError, "callback failed"):
            self.trigger.invoke()
        self.assertTrue(self.trigger.is_active)
        self.assertEqual(len(self.timers), 1)
        self.callback.side_effect = None
        self.timers[-1].fire()
        self.assertEqual(self.callback.call_count, 2)

    def test_overlapping_invocation_is_skipped(self) -> None:
        self.callback.side_effect = lambda: self.assertFalse(self.trigger.invoke())
        self.trigger.start()
        self.assertTrue(self.trigger.invoke())
        self.callback.assert_called_once_with()
        self.assertEqual(len(self.timers), 1)

    def test_timer_expiring_during_explicit_callback_is_replaced_afterwards(self) -> None:
        self.trigger.start()
        self.callback.side_effect = self.timers[-1].fire
        self.assertTrue(self.trigger.invoke())
        self.callback.assert_called_once_with()
        self.assertEqual(len(self.timers), 2)

    def test_timer_start_failure_leaves_trigger_inactive(self) -> None:
        with patch.object(ControlledTimer, "start", side_effect=RuntimeError("no thread")):
            with self.assertRaisesRegex(RuntimeError, "no thread"):
                self.trigger.start()
        self.assertFalse(self.trigger.is_active)
        self.trigger.start()
        self.assertTrue(self.trigger.is_active)


class TestIntervalTriggerThreads(unittest.TestCase):
    def test_real_timers_repeat_and_callback_can_stop(self) -> None:
        done = threading.Event()
        calls = []

        def callback():
            calls.append(threading.current_thread())
            if len(calls) == 3:
                trigger.stop()
                done.set()

        trigger = IntervalTrigger(callback, frequency=UpdateFrequency(seconds=0.01))
        self.addCleanup(trigger.stop)
        trigger.start()
        self.assertTrue(done.wait(2), "Timers did not deliver three callbacks")
        self.assertEqual(len(calls), 3)
        self.assertFalse(trigger.is_active)
        self.assertTrue(all(thread is not threading.current_thread() for thread in calls))

    def test_stop_and_restart_during_callback_does_not_overlap(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        stopped = threading.Event()
        restarted = threading.Event()
        done = threading.Event()
        calls = []
        errors = []

        def callback():
            calls.append(len(calls) + 1)
            if len(calls) == 1:
                entered.set()
                if not release.wait(2):
                    errors.append("First callback was not released")
            else:
                if not release.is_set():
                    errors.append("Callbacks overlapped")
                trigger.stop()
                done.set()

        def stop_and_restart():
            trigger.stop()
            stopped.set()
            trigger.start()
            restarted.set()

        trigger = IntervalTrigger(callback, frequency=UpdateFrequency(seconds=0.01))
        self.addCleanup(trigger.stop)
        self.addCleanup(release.set)
        trigger.start()
        self.assertTrue(entered.wait(2), "First callback did not start")
        controller = threading.Thread(target=stop_and_restart, daemon=True)
        controller.start()
        try:
            self.assertTrue(stopped.wait(1), "stop() waited for the callback")
            self.assertTrue(restarted.wait(1), "start() waited for the callback")
            self.assertTrue(trigger.is_active)
            self.assertFalse(trigger.invoke())
            self.assertEqual(calls, [1])
        finally:
            release.set()
            controller.join(2)
        self.assertTrue(done.wait(2), "Restarted trigger did not fire")
        self.assertEqual(calls, [1, 2])
        self.assertEqual(errors, [])
        self.assertFalse(trigger.is_active)


if __name__ == "__main__":
    unittest.main()
