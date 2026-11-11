import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.api.models.flaps import FlapData
from app.components.core.database_handler import DatabaseError
from app.components.database.split_flap_database import SplitFlapDatabase


class TestSplitFlapDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "split_flap.db"
        self.database = SplitFlapDatabase(str(self.database_path), num_flaps=4)
        self.database.init()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _add_flaps(self):
        with self.database.connect() as connection:
            connection.add_flap(0, "A", "A", "#FF0000")
            connection.add_flap(3, "Z", "Z", "#00FF00")

    def test_get_flaps(self):
        self._add_flaps()
        with self.database.connect() as db:
            flaps = db.get_flaps()
        self.assertEqual(flaps.num_flaps, 2)
        self.assertEqual(flaps.flaps[0].key, "A")
        self.assertEqual(flaps.flaps[3].glyph, "Z")


    def test_flap_positions_initialized_starts_false(self):
        self.assertFalse(self.database.flap_positions_initialized())

    def test_init_creates_expected_tables(self):
        with self.database.connect() as connection:
            self.assertIn(connection.FLAP_POSITION_TABLE, connection.tables)
            self.assertIn(connection.FLAP_ALIAS_TABLE, connection.tables)
            self.assertIn(connection.STATIC_ITEM_TABLE, connection.tables)
            self.assertIn(connection.STATIC_CELL_TABLE, connection.tables)

    def test_flap_crud_round_trip(self):
        with self.database.connect() as connection:
            connection.add_flap(0, "A", "A", "#FF0000")
            connection.add_flap(3, "Z", "Z", "#00FF00")

            first = connection.get_flap_data_by_position(0)
            self.assertEqual(first.glyph, "A")
            self.assertEqual(first.color_hex, "#FF0000")

            connection.update_flap(
                3,
                FlapData(position=3, key="X", glyph="X", color_hex="#0000FF"),
            )

            updated = connection.get_flap_data_by_position(3)
            self.assertEqual(updated.key, "X")
            self.assertEqual(updated.glyph, "X")
            self.assertEqual(updated.color_hex, "#0000FF")
            self.assertEqual(connection.get_all_flap_position_by_character()["flaps"]["X"], 3)

    def test_static_items_round_trip_and_delete(self):
        with self.database.connect() as connection:
            cells = [
                {"location": {"row": 1, "column": 1}, "position": 0},
                {"location": {"row": 1, "column": 2}, "position": 2},
            ]

            item_id = connection.add_static_item("Example Item", "uuid-123", 123.45, cells)
            self.assertIsInstance(item_id, int)

            item = connection.get_item_from_uuid("uuid-123")
            self.assertEqual(item.name, "Example Item")
            self.assertEqual(len(item.data), 2)
            self.assertEqual(item.data[0].location.row, 1)
            self.assertEqual(item.data[0].location.column, 1)
            self.assertEqual(item.data[0].position, 0)
            self.assertEqual(item.data[1].location.column, 2)
            self.assertEqual(item.data[1].position, 2)

            self.assertTrue(connection.delete_uuid("uuid-123"))
            with self.assertRaises(DatabaseError):
                connection.get_item_from_uuid("uuid-123")

    def test_flap_positions_initialized_after_loading_all_flaps(self):
        with self.database.connect() as connection:
            for position in range(self.database._num_flaps):
                connection.add_flap(position, f"key-{position}", f"glyph-{position}", "#FFFFFF")

        self.assertTrue(self.database.flap_positions_initialized())


if __name__ == "__main__":
    unittest.main()
