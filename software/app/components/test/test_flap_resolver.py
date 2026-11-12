import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.api.models.flaps import FlapData
from app.components.core.flap_resolver import FlapResolver, ResolutionError


class TestFlapResolver(unittest.TestCase):

    def setUp(self):
        self.flaps = [
            FlapData(position=0, key='BLANK', glyph=" ", color_hex="#FFFFF", aliases=["EMPTY", "SPACE"]), 
            FlapData(position=1, key='QUESTION_MARK', glyph="?", color_hex="#FFFFF", aliases=["QUESTION"]), 
            FlapData(position=2, key='AMPRESAND', glyph="&", color_hex="#FFFFF", aliases=["AND"]), 
            FlapData(position=3, key='UP', glyph="↑", color_hex="#FFFFF", aliases=["UP_ARROW", "ARROW"]),
        ]

    def tearDown(self):
        pass

    def _create_resolver(self) -> FlapResolver:
        return FlapResolver(self.flaps)
    
    def test_empty_resolver(self):
        with self.assertRaises(ValueError):
            flaps = FlapResolver([])
    
    def test_bad_parameter(self):
        with self.assertRaises(AssertionError):
            flaps = FlapResolver(self.flaps[0])
        
    def test_resolution_from_alias(self):
        resolver = self._create_resolver()
        for alias in self.flaps[-1].aliases:
            flap_data = resolver.resolve(alias)
            self.assertEqual(flap_data, self.flaps[-1])

    def test_unknown_value(self):
        resolver = self._create_resolver()
        with self.assertRaises(ResolutionError):
            resolver.resolve("FOO", fail_if_not_found=True)
        
        flap_data = resolver.resolve("FOO")
        self.assertEqual(flap_data, self.flaps[0])

    def test_non_flap_data(self):
        self.flaps.append("FOO")
        with self.assertRaises(AssertionError):
            resolver = FlapResolver(self.flaps)



if __name__ == "__main__":
    unittest.main()
