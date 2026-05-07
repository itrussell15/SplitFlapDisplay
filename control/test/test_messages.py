import unittest
import sys
from queue import Queue
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from source.dataclasses_ import OutgoingMessage, ModuleCommand

class TestOutgoingMessage(unittest.TestCase):

    def setUp(self):
        self.data_message = OutgoingMessage(
            module_id=0,
            command=ModuleCommand.MOVE_TO_POSITION,
            data_value=256
        )

        self.basic_message = OutgoingMessage(
            module_id=0,
            command=ModuleCommand.HOME,
        )

    def test_start_and_end_data(self):
        self.assertEqual(self.data_message.start_value, 2)
        self.assertEqual(self.data_message.end_value, 3)

    def test_start_and_end_basic(self):
        self.assertEqual(self.basic_message.start_value, 2)
        self.assertEqual(self.basic_message.end_value, 3)
        self.assertEqual(self.basic_message.data_value, 255)

    def test_generation(self):
        packet = self.data_message.generate_packet()

        data_value = packet[3] + (packet[4] * 256)
        self.assertEqual(packet[0], self.data_message.start_value)
        self.assertEqual(packet[1], self.data_message.module_id)
        self.assertEqual(packet[2], self.data_message.command.value)
        self.assertEqual(data_value , self.data_message.data_value)
        self.assertEqual(packet[5], self.data_message.end_value)


if __name__ == "__main__":
    unittest.main()