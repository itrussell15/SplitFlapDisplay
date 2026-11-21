import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from control.source.display_controller import DisplayInfo
from app.components.display.display_helper import DisplayHelper


class TestDisplayHelper(unittest.TestCase):

    def test_center_text_single_line(self):
        helper = DisplayHelper(DisplayInfo(rows=3, columns=5, modules=[]))

        result = helper.center_text("HI")

        self.assertEqual(result[(2, 2)], "H")
        self.assertEqual(result[(2, 3)], "I")

    def test_center_text_multi_line(self):
        helper = DisplayHelper(DisplayInfo(rows=3, columns=5, modules=[]))

        result = helper.center_text("A\nBC")

        self.assertEqual(result[(1, 3)], "A")
        self.assertEqual(result[(2, 2)], "B")
        self.assertEqual(result[(2, 3)], "C")

    def test_center_row_uses_one_based_columns(self):
        helper = DisplayHelper(DisplayInfo(rows=3, columns=5, modules=[]))

        result = helper.center_row("HI", row_value=2)

        self.assertEqual(result[(2, 2)], "H")
        self.assertEqual(result[(2, 3)], "I")
        self.assertEqual(result[(2, 1)], "BLANK")
        self.assertEqual(result[(2, 4)], "BLANK")
        self.assertEqual(result[(2, 5)], "BLANK")

    def test_center_rows(self):
        helper = DisplayHelper(DisplayInfo(rows=3, columns=5, modules=[]))

        result = helper.center_rows(["A", "BC", ""])

        self.assertEqual(result[(1, 3)], "A")
        self.assertEqual(result[(2, 2)], "B")
        self.assertEqual(result[(2, 3)], "C")
        self.assertTrue(all(result[(3, col)] == "BLANK" for col in range(1, 6)))

    def test_weather_unit_configuration(self):
        from app.components.display.base_apps.weather import TemperatureApp

        imperial = TemperatureApp(
            trigger_factory=None,
            lat="0",
            lon="0",
            metric_units="false",
            api_key="test",
        )
        imperial_by_units = TemperatureApp(
            trigger_factory=None,
            lat="0",
            lon="0",
            units="imperial",
            api_key="test",
        )
        metric = TemperatureApp(
            trigger_factory=None,
            lat="0",
            lon="0",
            metric_units="true",
            api_key="test",
        )

        self.assertEqual(imperial._unit_system, "imperial")
        self.assertEqual(imperial_by_units._unit_system, "imperial")
        self.assertEqual(metric._unit_system, "metric")

    def test_weather_temperature_uses_resolver_degree_alias(self):
        from app.components.display.base_apps.weather import TemperatureApp

        app = TemperatureApp(
            trigger_factory=None,
            lat="0",
            lon="0",
            units="imperial",
            api_key="test",
        )
        helper = DisplayHelper(DisplayInfo(rows=3, columns=15, modules=[]))

        result = app.get_temperature_data(helper, 72.4, False, 2)
        text = "".join(
            value
            for (row, _), value in sorted(result.items())
            if row == 2 and value != "BLANK"
        )

        self.assertEqual(text, "72DEGREEF")


if __name__ == "__main__":
    unittest.main()
