import time
from .bus_controller import BusController
from .flaps import Flaps

# TODO Need to associated a module ID to a position on the overall display
# Display -> Bus -> Module
# Bus 0 - [Module 1, Module 2, Module 3]
# Bus 1 - [Module 5, Module 9, Module 10]
# Bus 2 - [Module 8, Module 4, Module 11]

COMMAND_SLEEP_TIME_S = 0.05

class DisplayController(BusController):
    def __init__(self, port: str, num_modules: int, baudrate: int = 9600, timeout: int = 2) -> None:
        super().__init__(bus_port=port, baudrate=baudrate, timeout=timeout)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.discover()

        if len(self.modules) != num_modules:
            raise RuntimeError(f"Expected {num_modules} modules, but found {len(self.modules)}")
        
    def home_all(self) -> None:
        for module in self.modules.values():
            module.home()
            time.sleep(COMMAND_SLEEP_TIME_S)  # Stagger commands to avoid overwhelming the bus
        
    def move_to_positions(self, positions: Dict[int, int]) -> None:
        for module_id, position in positions.items():
            self.modules[module_id].move_to_position(position)
            time.sleep(COMMAND_SLEEP_TIME_S)  # Stagger commands to avoid overwhelming the bus

    def move_to_flap(self, flaps: Dict[int, Flap]) -> None:
        for module_id, flap in flaps.items():
            self.modules[module_id].move_to_position(flap.value)
            time.sleep(COMMAND_SLEEP_TIME_S)  # Stagger commands to avoid overwhelming the bus

    def move_to_steps(self, steps: Dict[int, int]) -> None:
        for module_id, step in steps.items():
            self.modules[module_id].move_by_steps(step)
            time.sleep(COMMAND_SLEEP_TIME_S)  # Stagger commands to avoid overwhelming the bus
        

