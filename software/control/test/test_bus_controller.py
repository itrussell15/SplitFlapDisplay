import os
import logging
import struct
import sys
import threading
import time
import unittest
from concurrent.futures import Future
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from source.bus_controller import BusController
from source.dataclasses_ import IncomingMessage, ModuleCommand, OutgoingMessage
from source.module_controller import (
    FirmwareException,
    MAX_SPEED,
    ModuleController,
    MOTOR_RESOLUTION,
    NUM_POSITIONS,
)
from test.mock_components.mock_module_firmware import MockFirmware
from utils import create_logger

MODULE_IDS = [1, 2, 3, 4, 5]
SLEEP_TIME_S = 1.0


class TestBusController(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        create_logger(level=logging.DEBUG, spacing=23)

        cls.ROW = 1
        cls.COLUMN = 5
        cls.module = ModuleController(row=cls.ROW, column=cls.COLUMN)
        cls.test_location = (cls.ROW, cls.COLUMN)
        cls.modules = {cls.test_location: cls.module}
        port = os.getenv("DISP_USB_PORT")
        cls.bus = BusController(port=port, modules=cls.modules, timeout=0.75)
        cls.latencies = []

    @classmethod
    def tearDownClass(cls):
        # Runs once after ALL tests in this class
        cls.bus.close()
        if len(cls.latencies) > 0:
            print(
                f"Average Latency: {sum([i.total for i in cls.latencies]) / len(cls.latencies):.2f}ms"
            )

    def setUp(self):
        self.timeout = 0.5
        self.bus.reset_processed_commands()

    def tearDown(self):
        time.sleep(1.0)
        self.timeout = 0.5

    def test_ping(self) -> None:
        ping_message = OutgoingMessage(
            row=self.ROW, column=self.COLUMN, command=ModuleCommand.PING
        )
        future = Future()
        self.bus.queue.put((future, ping_message))
        response = future.result()
        self.assertEqual(response.command, ModuleCommand.PING)
        self.assertTrue(response.status)

    def test_get_steps(self) -> None:
        message = self.modules[self.test_location].get_steps()
        self.assertEqual(message.command, ModuleCommand.GET_STEPS)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)

    def test_get_speed(self) -> None:
        message = self.modules[self.test_location].get_speed()
        self.assertEqual(message.command, ModuleCommand.GET_SPEED)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)

    def test_home(self) -> None:
        message = self.modules[self.test_location].home()
        self.assertEqual(message.command, ModuleCommand.HOME)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)

    def test_move_steps(self) -> None:
        message = self.modules[self.test_location].move_to_step(1200)
        self.assertEqual(message.command, ModuleCommand.MOVE_TO_STEP)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)
        time.sleep(1)
        message = self.modules[self.test_location].get_steps()

    def test_move_steps(self) -> None:
        start_steps = self.modules[self.test_location].get_steps().data_value
        message = self.modules[self.test_location].move_steps(2000)
        time.sleep(6)
        end_steps = self.modules[self.test_location].get_steps().data_value
        print(f"Diff: {end_steps-start_steps}")

    def test_get_position(self) -> None:
        message = self.modules[self.test_location].get_position(0)
        self.assertEqual(message.command, ModuleCommand.GET_POSITION)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)
    
    def test_set_position(self) -> None:
        message = self.modules[self.test_location].set_position(59)
        self.assertEqual(message.command, ModuleCommand.SET_POSITION)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)

    def test_move_to_position(self) -> None:
        message = self.modules[self.test_location].move_to_position(6)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)
        # time.sleep(10)
        # message = self.modules[self.test_location].get_steps()
        # step_value = message.data_value
        # message = self.modules[self.test_location].get_position(10)
        # postion_value = message.data_value
        # print(f"Position: {postion_value} Step: {step_value}")

    def test_get_all_positions(self) -> None:
        values = {}
        for position in range(NUM_POSITIONS):
            values[position] = self.modules[self.test_location].get_position(position).data_value
            time.sleep(0.5)
        print(values)
        # self.assertEqual(message.command, ModuleCommand.GET_SPEED)
        # self.assertTrue(message.status)

    def test_bad_command(self) -> None:
        with self.assertRaises(FirmwareException):
            message = self.modules[self.test_location]._send_packet(
                ModuleCommand.BAD_COMMAND
            )

    def test_discover(self) -> None:
        # Test all bad values
        with self.assertRaises(ValueError):
            self.bus.discover([0, 5], [0, -1])
        with self.assertRaises(ValueError):
            self.bus.discover([0, -1], [0, 5])
        with self.assertRaises(ValueError):
            self.bus.discover([0, 500], [0, 10])
        with self.assertRaises(ValueError):
            self.bus.discover([0, 4], [0, 500])

        # Actually search for 1 module
        self.bus.discover([1, 2], [1, 10], 0.1)
        self.assertEqual(len(self.bus.modules), 1)

    def test_broadcast(self) -> None:
        self.bus.broadcast(ModuleCommand.MOVE_TO_STEP, 1000)
        self.assertEqual(self.bus.queue.qsize(), 1)

    def test_hall_effect_status(self) -> None:
        message = self.modules[self.test_location].get_hall_effect_status()
        self.assertEqual(message.command, ModuleCommand.GET_HALL_EFFECT_STATUS)
        self.assertTrue(message.status)
        self.latencies.append(message.latency_ms)

    def test_is_moving(self) -> None:
        message = self.modules[self.test_location].is_moving()
        self.assertEqual(message.command, ModuleCommand.IS_MOVING)
        self.assertTrue(message.status)
        self.assertFalse(bool(message.data_value))
        self.latencies.append(message.latency_ms)

        message = self.modules[self.test_location].move_to_step(3000)
        message = self.modules[self.test_location].is_moving()
        self.assertTrue(bool(message.data_value))
        self.latencies.append(message.latency_ms)

    def test_set_auto_home(self) -> None:
        message = self.modules[self.test_location].set_auto_home(True)
    
    def test_set_calibration_mode(self) -> None:
        message = self.modules[self.test_location].set_calibration_mode(False)

    def test_set_home_offset(self) -> None:
        message = self.modules[self.test_location].set_home_offset(2800)

    def test_get_home_offset(self) -> None:
        message = self.modules[self.test_location].get_home_offset()

    def test_get_auto_home(self) -> None:
        message = self.modules[self.test_location].get_home_offset()

    def test_set_max_steps(self) -> None:
        message = self.modules[self.test_location].set_max_steps(4094)

    def test_get_eeprom(self) -> None:
        row = self.modules[self.test_location].get_eeprom_value(0)
        col = self.modules[self.test_location].get_eeprom_value(1)
        auto_home = self.modules[self.test_location].get_eeprom_value(2)
        message1 = self.modules[self.test_location].get_eeprom_value(3)
        message2 = self.modules[self.test_location].get_eeprom_value(4)
        steps1 = self.modules[self.test_location].get_eeprom_value(5)
        steps2 = self.modules[self.test_location].get_eeprom_value(6)

        print(f"ROW: {row.data_value} COLUMN: {col.data_value}")
        print(f"AUTO HOME: {auto_home.data_value} -> {bool(auto_home.data_value)}")
        print(f"HOME OFFSET ---- ")
        print(f"1: {message1.data_value} - 2: {message2.data_value} = {(message2.data_value * 256) + message1.data_value}")
        print(f"MAX STEPS ---- ")
        print(f"1: {steps1.data_value} - 2: {steps2.data_value} = {(steps2.data_value * 256) + steps1.data_value}")

    def test_get_total_steps(self) -> None:
        self.bus.timeout = 30
        message = self.modules[self.test_location].get_drum_steps()
        print(f"TOTAL MOTOR STEPS: {message.data_value}")