import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.components.core.trigger import ManualTrigger, Trigger


class TestTrigger(unittest.TestCase):
    def test_base_class_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            Trigger(Mock())

    def test_requires_a_callable(self) -> None:
        with self.assertRaisesRegex(TypeError, "callback must be callable"):
            ManualTrigger(None)


class TestManualTrigger(unittest.TestCase):
    def setUp(self) -> None:
        self.callback = Mock()
        self.trigger = ManualTrigger(self.callback)

    def test_inactive_trigger_does_not_invoke_callback(self) -> None:
        self.assertFalse(self.trigger.is_active)
        self.assertFalse(self.trigger.invoke())
        self.callback.assert_not_called()

    def test_start_enables_trigger_without_invoking_callback(self) -> None:
        self.trigger.start()
        self.assertTrue(self.trigger.is_active)
        self.callback.assert_not_called()

    def test_each_invocation_calls_callback_once_without_arguments(self) -> None:
        self.trigger.start()
        self.assertTrue(self.trigger.invoke())
        self.callback.assert_called_once_with()
        self.assertTrue(self.trigger.invoke())
        self.assertEqual(self.callback.call_count, 2)
        self.assertTrue(self.trigger.is_active)

    def test_repeated_start_is_harmless(self) -> None:
        self.trigger.start()
        self.trigger.start()
        self.trigger.invoke()
        self.callback.assert_called_once_with()

    def test_stop_disables_future_invocations(self) -> None:
        self.trigger.start()
        self.trigger.invoke()
        self.trigger.stop()
        self.assertFalse(self.trigger.is_active)
        self.assertFalse(self.trigger.invoke())
        self.callback.assert_called_once_with()

    def test_stopping_an_inactive_trigger_is_harmless(self) -> None:
        self.trigger.stop()
        self.trigger.start()
        self.trigger.stop()
        self.trigger.stop()
        self.assertFalse(self.trigger.is_active)
        self.callback.assert_not_called()

    def test_stopped_trigger_can_be_restarted(self) -> None:
        self.trigger.start()
        self.trigger.stop()
        self.trigger.start()
        self.assertTrue(self.trigger.is_active)
        self.assertTrue(self.trigger.invoke())
        self.callback.assert_called_once_with()

    def test_callback_can_stop_its_trigger(self) -> None:
        self.callback.side_effect = self.trigger.stop
        self.trigger.start()
        self.assertTrue(self.trigger.invoke())
        self.assertFalse(self.trigger.is_active)
        self.assertFalse(self.trigger.invoke())
        self.callback.assert_called_once_with()

    def test_callback_errors_propagate_and_allow_later_invocations(self) -> None:
        self.callback.side_effect = ValueError("callback failed")
        self.trigger.start()
        with self.assertRaisesRegex(ValueError, "callback failed"):
            self.trigger.invoke()
        self.assertTrue(self.trigger.is_active)
        self.callback.side_effect = None
        self.assertTrue(self.trigger.invoke())
        self.assertEqual(self.callback.call_count, 2)

    def test_accepts_an_owners_bound_method_as_callback(self) -> None:
        class Owner:
            def __init__(self) -> None:
                self.update_count = 0
                self.trigger = ManualTrigger(self.update)

            def update(self) -> None:
                self.update_count += 1

        owner = Owner()
        owner.trigger.start()
        owner.trigger.invoke()
        self.assertEqual(owner.update_count, 1)


if __name__ == "__main__":
    unittest.main()
