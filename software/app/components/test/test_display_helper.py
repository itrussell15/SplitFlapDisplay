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


if __name__ == "__main__":
    unittest.main()
