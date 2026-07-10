import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple

from .bus_controller import BusController
from .flaps import Flap
from .module_controller import ModuleController




class DisplayController:

    def __init__(self, timeout: float = 0.3) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.buses = {}
        self.modules = {}

    def add_bus_controller(self, bus: BusController, discover: bool = False) -> None:
        if bus.port in self.buses:
            raise ConnectionError(f"Already connected to bus at {bus.port}")
        self.buses[bus.port] = bus
        self._update_modules(bus)
        self.logger.info(f"Adding bus at {bus.port}")

    def get_module(self, row: int, column: int) -> ModuleController:
        location = (row, column)
        if location not in self.modules:
            raise ValueError(f"No module found at ({row}, {column})")
        return self.modules[location]

    def reset_processed_commands(self) -> None:
        for bus in self.buses.values():
            bus.reset_processed_commands()

    def discover(self, row_value: int, column_value: int) -> List[Tuple[int, int]]:
        modules = []
        for bus in self.buses.values():
            module_locations = bus.discover(row_value, column_value)
            modules.extend(module_locations)
            self._update_modules(bus)
            bus.get_module_info()
        self.check_display_for_gaps()
        return modules

    def home_all(self) -> None:
        values = []
        self.logger.info("Homing all modules")
        for _, module in self.modules.items():
            values.append(module.home())
        return values

    def move_all_to_position(self, position: int) -> List[int]:
        values = []
        self.logger.info(f"Moving {self.num_modules} modules to position {position}")
        for location, module in self.modules.items():
            values.append(module.move_to_position(position))
        return values

    def get_all_steps(self) -> List[int]:
        values = []
        for location, module in self.modules.items():
            values.append(module.get_steps())
        return values

    def get_current_positions(self):
        return {
            location: module.current_position
            for location, module in self.modules.items()
        }
    
    def move_all_to_step(self, position: int):
        return {
            location: module.move_to_step(position)
            for location, module in self.modules.items()
        }

    def move_to_steps(self, steps: Dict[Tuple[int, int], int]) -> List[int]:
        values = []
        for module_location, step in steps.items():
            self._is_valid_module(module_location, throw_error=True)
            response = self.modules[module_location].move_to_step(step)
            values.append(response)
        return values

    def get_position_steps(self, position: int) -> List[int]:
        values = []
        for location, module in self.modules.items():
            values.append(module.get_position(position))
        return values

    def set_all_position_steps(self, position: int) -> List[int]:
        values = []
        for location, module in self.modules.items():
            values.append(module.set_position(position))
        return values

    def move_to_position(self, positions: Dict[Tuple[int, int], int]) -> List[int]:
        values = []
        for module_location, position in positions.items():
            self._is_valid_module(module_location, throw_error=True)
            response = self.modules[module_location].move_to_position(position)
            values.append(response)
        return values

    def move_to_flaps(self, flaps: Dict[Tuple[int, int], Flap]) -> List:
        values = []
        for module_location, flap in flaps.items():
            self._is_valid_module(module_location, throw_error=True)
            response = self.modules[module_location].move_to_position(flap.value)
            values.append(response)
        return values

    def get_rows_and_columns(self) -> Tuple[int, int]:
        max_row = -1
        max_col = -1
        for location in self.modules:
            row, col = location
            max_row = max([row, max_row])
            max_col = max([col, max_col])
        return max_row, max_col

    def close(self) -> None:
        self.logger.info("Closing display connection")
        for bus in self.buses.values():
            bus.close()

    def _update_modules(self, bus: BusController) -> None:
        self.modules = {}
        for bus in self.buses.values():
            for location, controller in bus.modules.items():
                if location in self.modules:
                    raise ValueError(
                        f"Location value: {location} already found in display"
                    )
                self.modules[location] = controller

    def _is_valid_module(
        self, module_location: Tuple[int, int], throw_error: bool = False
    ) -> bool:
        result = module_location in self.modules
        if not result and throw_error:
            raise ValueError(f"No module at {module_location} found on this display")
        return result

    def check_for_gaps(self) -> None:
        # Gather modules
        rows = {}
        for module in self.modules:
            row, column = module
            if row not in rows:
                rows[row] = []
            rows[row].append(column)

        # Check for gaps
        for row, columns in rows.items():
            column = sorted(columns)
            current_column = columns[0]
            for column in columns[1:]:
                if abs(column - current_column) > 1:
                    raise ValueError(f"Gap in modules at {(row, column)}")
                current_column = column
        
 
    @property
    def processed_commands(self) -> int:
        return sum(bus.processed_commands for bus in self.buses.values())

    @property
    def num_buses(self) -> int:
        return len(self.buses)

    @property
    def num_modules(self) -> int:
        return len(self.modules)
