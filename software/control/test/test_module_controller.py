import unittest
import sys
from queue import Queue
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from source.module_controller import (
    ModuleController, MAX_SPEED, MOTOR_RESOLUTION
)
from source.dataclasses_ import OutgoingMessage, ModuleCommand

class TestModuleController(unittest.TestCase):

    def setUp(self):
        self.module_id = 1
        self.controller = ModuleController(self.module_id)
        queue = Queue()
        self.controller.register_command_queue(queue)
    
    def test_bad_id(self):
        with self.assertRaises(ValueError):
            controller = ModuleController(0)
        with self.assertRaises(ValueError):
            controller = ModuleController(300)

    def test_index(self):
        self.assertEqual(self.controller.module_id, self.module_id)

    def test_move(self):
        move_value = 100
        message = self.controller.move(move_value)
        self._validate_message(message, ModuleCommand.MOVE_TO_POSITION, move_value)

        move_value = 2 * MOTOR_RESOLUTION
        with self.assertRaises(ValueError):
            message = self.controller.move(move_value)
        
        move_value = -1
        with self.assertRaises(ValueError):
            message = self.controller.move(move_value)
    
    def test_get_position(self):
        message = self.controller.get_position()
        self._validate_message(message, ModuleCommand.GET_POSITION, 255)
    
    def test_home(self):
        message = self.controller.home()
        self._validate_message(message, ModuleCommand.HOME, 255)
        
    def test_stop(self):
        move_value = 100
        message = self.controller.stop()
        self._validate_message(message, ModuleCommand.STOP, 255)

    def test_set_speed(self):
        speed_value = 10
        message = self.controller.set_speed(speed_value)
        self._validate_message(message, ModuleCommand.SET_SPEED, speed_value)

        speed_value = 2 * MAX_SPEED
        with self.assertRaises(ValueError):
            message = self.controller.set_speed(speed_value)
        
        speed_value = -1
        with self.assertRaises(ValueError):
            message = self.controller.set_speed(speed_value)

    def test_get_speed(self):
        message = self.controller.get_speed()
        self._validate_message(message, ModuleCommand.GET_SPEED, 255)

    def test_queue(self):
        with self.assertRaises(TypeError):
            self.controller.register_command_queue([])
        self.controller.unregister_command_queue()
        self.assertFalse(self.controller.is_command_queue_registered)

        queue = Queue()
        self.controller.register_command_queue(queue)
        self.assertTrue(self.controller.is_command_queue_registered)
        self.assertTrue(queue.empty())

        value = 100
        self.controller.move(value)
        self.assertEqual(queue.qsize(), 1)
        self.controller.move(value)
        self.assertEqual(queue.qsize(), 2)

        message = queue.get()
        self.assertEqual(queue.qsize(), 1)
        self._validate_message(message, ModuleCommand.MOVE_TO_POSITION, value)

    def _validate_message(self, message: OutgoingMessage, command: ModuleCommand, data_value: int):
        self.assertIsInstance(message, OutgoingMessage)
        self.assertIsInstance(message.command, ModuleCommand)

        self.assertEqual(message.module_id, self.module_id)
        self.assertEqual(message.command, command)
        self.assertEqual(message.data_value, data_value)


if __name__ == "__main__":
    unittest.main()