import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.components.core.trigger import OneShotTrigger
from app.components.core.updater import TimeStatus, UpdateFrequency
from app.components.test.test_interval_trigger import ControlledTimer


class TestOneShotTrigger(unittest.TestCase):
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
        self.duration = UpdateFrequency(minutes=1, seconds=5)
        self.trigger = OneShotTrigger(self.callback, duration=self.duration)
        self.addCleanup(self.trigger.stop)

    def test_requires_a_positive_finite_update_frequency_duration(self) -> None:
        with self.assertRaises(TypeError):
            OneShotTrigger(self.callback, duration=5)
        for seconds in (0, -1, float("nan"), float("inf")):
            with self.subTest(seconds=seconds):
                with self.assertRaises(ValueError):
                    OneShotTrigger(self.callback, UpdateFrequency(seconds=seconds))

    def test_start_schedules_once_without_firing_or_resetting_countdown(self) -> None:
        self.assertFalse(self.trigger.is_active)
        self.assertIsNone(self.trigger.time_status)
        self.assertFalse(self.trigger.invoke())
        self.trigger.start()
        status = self.trigger.time_status
        self.clock.return_value = 105
        self.trigger.start()
        self.assertTrue(self.trigger.is_active)
        self.callback.assert_not_called()
        self.assertEqual(len(self.timers), 1)
        self.assertEqual(self.timers[0].interval, 65)
        self.assertTrue(self.timers[0].daemon)
        self.assertIs(self.trigger.time_status, status)

    def test_time_status_tracks_countdown_and_completion(self) -> None:
        self.assertIs(self.trigger.duration, self.duration)
        self.trigger.start()
        status = self.trigger.time_status
        self.assertIsInstance(status, TimeStatus)
        self.assertEqual(status.start, 100)
        self.assertEqual(status.end, 165)
        self.clock.return_value = 110
        self.assertEqual(status.elapsed, 10)
        self.assertEqual(status.remaining, 55)
        self.clock.return_value = 165
        self.timers[-1].fire()
        self.assertIs(self.trigger.time_status, status)
        self.assertEqual(status.remaining, 0)
        self.assertFalse(self.trigger.is_active)

    def test_timer_fires_callback_once_without_rescheduling(self) -> None:
        self.trigger.start()
        timer = self.timers[-1]
        timer.fire()
        timer.fire()
        self.assertFalse(self.trigger.invoke())
        self.callback.assert_called_once_with()
        self.assertEqual(len(self.timers), 1)
        self.assertFalse(self.trigger.is_active)

    def test_becomes_inactive_before_callback_runs(self) -> None:
        def callback():
            self.assertFalse(self.trigger.is_active)
            self.assertFalse(self.trigger.invoke())
            self.assertEqual(self.trigger.time_status.remaining, 0)

        self.callback.side_effect = callback
        self.trigger.start()
        self.assertTrue(self.trigger.invoke())
        self.callback.assert_called_once_with()

    def test_explicit_invocation_fires_early_and_cancels_timer(self) -> None:
        self.trigger.start()
        timer = self.timers[-1]
        self.clock.return_value = 105
        self.assertTrue(self.trigger.invoke())
        self.assertTrue(timer.cancelled)
        self.assertEqual(self.trigger.time_status.end, 105)
        timer.fire()
        self.callback.assert_called_once_with()
        self.assertEqual(len(self.timers), 1)

    def test_stop_cancels_countdown_and_ignores_late_delivery(self) -> None:
        self.trigger.stop()
        self.trigger.start()
        timer = self.timers[-1]
        self.trigger.stop()
        self.trigger.stop()
        timer.fire()
        self.assertTrue(timer.cancelled)
        self.assertIsNone(self.trigger.time_status)
        self.assertFalse(self.trigger.is_active)
        self.callback.assert_not_called()

    def test_restart_ignores_old_timer_and_creates_fresh_countdown(self) -> None:
        self.trigger.start()
        old_timer = self.timers[-1]
        old_status = self.trigger.time_status
        self.trigger.stop()
        self.clock.return_value = 110
        self.trigger.start()
        old_timer.fire()
        self.callback.assert_not_called()
        self.assertIsNot(self.trigger.time_status, old_status)
        self.assertEqual(self.trigger.time_status.start, 110)
        self.assertEqual(self.trigger.time_status.end, 175)
        self.timers[-1].fire()
        self.callback.assert_called_once_with()
        self.assertEqual(len(self.timers), 2)

    def test_callback_can_restart_without_duplicate_or_overlapping_timers(self) -> None:
        def restart():
            self.trigger.start()
            self.trigger.start()
            self.assertTrue(self.trigger.is_active)
            self.assertFalse(self.trigger.invoke())
            self.assertIsNone(self.trigger.time_status)
            self.assertEqual(len(self.timers), 1)

        self.callback.side_effect = restart
        self.trigger.start()
        self.timers[-1].fire()
        self.assertEqual(len(self.timers), 2)
        self.assertIsNotNone(self.trigger.time_status)
        self.callback.side_effect = None
        self.timers[-1].fire()
        self.assertEqual(self.callback.call_count, 2)
        self.assertFalse(self.trigger.is_active)
        self.assertEqual(len(self.timers), 2)

    def test_duration_changes_apply_to_next_run(self) -> None:
        self.trigger.start()
        self.duration.seconds = 10
        self.assertEqual(self.timers[-1].interval, 65)
        self.assertEqual(self.trigger.time_status.end, 165)
        self.timers[-1].fire()
        self.trigger.start()
        self.assertEqual(self.timers[-1].interval, 70)
        self.assertEqual(self.trigger.time_status.end, 170)

    def test_background_callback_error_is_logged_without_rescheduling(self) -> None:
        self.callback.side_effect = ValueError("callback failed")
        self.trigger.start()
        with self.assertLogs("OneShotTrigger", level="ERROR") as logs:
            self.timers[-1].fire()
        self.assertIn("callback failed", logs.output[0])
        self.assertFalse(self.trigger.is_active)
        self.assertEqual(len(self.timers), 1)

    def test_explicit_callback_error_propagates_and_run_remains_consumed(self) -> None:
        self.callback.side_effect = ValueError("callback failed")
        self.trigger.start()
        with self.assertRaisesRegex(ValueError, "callback failed"):
            self.trigger.invoke()
        self.assertFalse(self.trigger.is_active)
        self.assertFalse(self.trigger.invoke())
        self.callback.side_effect = None
        self.trigger.start()
        self.assertTrue(self.trigger.invoke())
        self.assertEqual(self.callback.call_count, 2)

    def test_timer_start_failure_cleans_up_countdown(self) -> None:
        with patch.object(ControlledTimer, "start", side_effect=RuntimeError("no thread")):
            with self.assertRaisesRegex(RuntimeError, "no thread"):
                self.trigger.start()
        self.assertFalse(self.trigger.is_active)
        self.assertIsNone(self.trigger.time_status)
        self.trigger.start()
        self.assertTrue(self.trigger.is_active)


class TestOneShotTriggerThreads(unittest.TestCase):
    def test_real_timer_delivers_one_background_callback(self) -> None:
        done = threading.Event()
        calls = []

        def callback():
            calls.append(threading.current_thread())
            done.set()

        trigger = OneShotTrigger(callback, duration=UpdateFrequency(seconds=0.01))
        self.addCleanup(trigger.stop)
        trigger.start()
        self.assertTrue(done.wait(2), "One-shot callback did not run")
        self.assertEqual(len(calls), 1)
        self.assertIsNot(calls[0], threading.current_thread())
        self.assertFalse(trigger.is_active)
        self.assertFalse(trigger.invoke())

    def test_restart_during_running_callback_waits_without_overlap(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        done = threading.Event()
        calls = []
        errors = []

        def callback():
            calls.append(len(calls) + 1)
            if len(calls) == 1:
                entered.set()
                if not release.wait(2):
                    errors.append("Callback was not released")
            else:
                if not release.is_set():
                    errors.append("Callbacks overlapped")
                done.set()

        trigger = OneShotTrigger(callback, duration=UpdateFrequency(seconds=0.01))
        self.addCleanup(trigger.stop)
        self.addCleanup(release.set)
        trigger.start()
        self.assertTrue(entered.wait(2), "First callback did not run")
        trigger.start()
        self.assertTrue(trigger.is_active)
        self.assertIsNone(trigger.time_status)
        self.assertFalse(trigger.invoke())
        release.set()
        self.assertTrue(done.wait(2), "Restarted countdown did not fire")
        self.assertEqual(calls, [1, 2])
        self.assertEqual(errors, [])
        self.assertFalse(trigger.is_active)


if __name__ == "__main__":
    unittest.main()
