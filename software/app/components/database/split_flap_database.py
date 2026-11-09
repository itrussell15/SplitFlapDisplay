from typing import List

from dataclasses import dataclass

from ..core.database_handler import DatabaseHandler, DatabaseConnection, DatabaseError
from app.api.models.static_items import (
    StaticModuleData, StaticItem, StaticItems, Location
)
from app.api.models.flaps import AllFlaps, FlapData
from app.api.common import exception_response


@dataclass(frozen=True)
class StaticItemRowEntry:
    item_id: int
    uuid: str
    item_name: str
    timestamp: float
    item_index: int
    row: int
    column: int
    value: str

    def create_static_item(self) -> StaticItem:
        return StaticItem(
            name=self.item_name,
            uuid=self.uuid,
            request_time=str(self.timestamp),
            data=[self.as_static_module_data()]
        )

    def as_static_module_data(self) -> StaticModuleData:
        return StaticModuleData(
            location=Location(row=self.row, column=self.column),
            value=self.value
        )

class Connection(DatabaseConnection):

    FLAP_POSITION_TABLE: str = "flap_positions"
    STATIC_ITEM_TABLE: str = "static_item"
    STATIC_CELL_TABLE: str = "static_item_cell"

    def __init__(self, file: str, num_flaps: int) -> None:
        super().__init__(file)
        self._num_flaps = num_flaps

    def init(self) -> None:
        self._create_static_item_tables()
        self._create_flap_position_table()
        self.get_static_item_names()

        return True

    def add_static_item(self, name: str, uuid: str, timestamp: float, cells: list[dict]) -> int:
        self._ensure_connection()

        self.logger.info(f"Adding static item to database with name {name}")
        if name in self.get_static_item_names():
            raise ValueError(f"Name already exists in database with name {name}")

        # Create new static item entry
        self._cursor.execute(
            f"""
            INSERT INTO {self.STATIC_ITEM_TABLE} (uuid, name, created_at)
            VALUES (?, ?, ?)
            """,
            (uuid, name, timestamp),
        )
        item_id = self._cursor.lastrowid

        # Create new cell entries tied back to static entry by the id
        for cell in cells:
            location = cell["location"]
            row = location["row"]
            column = location["column"]
            value = cell["value"]

            self._cursor.execute(
                f"""
                INSERT INTO {self.STATIC_CELL_TABLE} (static_item_id, row_index, column_index, value)
                VALUES (?, ?, ?, ?)
                """,
                (item_id, row, column, value),
            )

        self._connection.commit()
        return item_id

    def get_static_item_names(self) -> List[str]:
        names = self._cursor.execute(
            f"""
            SELECT name, uuid
            FROM {self.STATIC_ITEM_TABLE}
            """
        ).fetchall()
        return {name[0]: name[1] for name in names}

    def add_flap(self, position: int, character: str, color_hex: str) -> FlapData:
        self._cursor.execute(
            f"""
            INSERT INTO {self.FLAP_POSITION_TABLE} (flap_index, character, color_hex)
            VALUES (?, ?, ?)
            """,
            (position, character, color_hex),
        )
        self.logger.info(f"Assigning {character} to flap {position}")
        self._connection.commit()
        return FlapData(
            position=position,
            character=character,
            color_hex=color_hex
        )

    def get_flaps(self) -> AllFlaps:
        rows = self._cursor.execute(
            f"""
            SELECT *
            FROM {self.FLAP_POSITION_TABLE}
            """
        ).fetchall()

        flaps = {}
        for row in rows:
            flap = FlapData(position=row[1], character=row[2], color_hex=row[3])
            flaps[flap.position] = flap
        return AllFlaps(
            num_flaps=len(flaps),
            flaps=flaps
        )

    def get_all_flap_characters_by_position(self) -> Dict[str, Any]:
        rows = self._cursor.execute(
            f"""
            SELECT flap_index, character
            FROM {self.FLAP_POSITION_TABLE}
            """
        ).fetchall()
        map_ = {row[0]: row[1] for row in rows}
        return {
            "num_flaps": len(rows),
            "flaps": map_
        }

    def get_flap_data_by_position(self, position: int) -> FlapData:
        if position < 0 or position > self._num_flaps:
            raise DatabaseError(f"Position {position} out of bounds. Must be 0-{self._num_flaps}")

        row = self._cursor.execute(
            f"""
            SELECT flap_index, character, color_hex
            FROM {self.FLAP_POSITION_TABLE}
            WHERE flap_index = ?
            """,
            (position,)
        ).fetchone()
        return FlapData(
            position=row[0],
            character=row[1],
            color_hex=row[2]
        )

    def get_all_flap_position_by_character(self) -> Dict[str, Any]:
        rows = self._cursor.execute(
            f"""
            SELECT flap_index, character
            FROM {self.FLAP_POSITION_TABLE}
            """
        ).fetchall()
        map_ = {row[1]: row[0] for row in rows}
        return {
            "num_flaps": len(rows),
            "flaps": map_
        }

    def get_flap_data_by_character(self, character: str) -> FlapData:
        row = self._cursor.execute(
            f"""
            SELECT flap_index, character, color_hex
            FROM {self.FLAP_POSITION_TABLE}
            WHERE character = ?
            """,
            (character,)
        ).fetchone()
        if row is None:
            return exception_response(f"{character} was not associated with a flap")

        return FlapData(
            position=row[0],
            character=row[1],
            color_hex=row[2]
        )

    def get_item_from_uuid(self, uuid: str) -> StaticItem:
        self._ensure_connection()

        rows = self._cursor.execute(
            f""" 
            SELECT s.id AS item_id, s.uuid, s.name, s.created_at,
                c.id AS cell_id, c.row_index, c.column_index, c.value
            FROM {self.STATIC_ITEM_TABLE} s
            LEFT JOIN {self.STATIC_CELL_TABLE} c
                ON c.static_item_id = s.id
            WHERE s.uuid = ?
            ORDER BY s.id, c.row_index, c.column_index
            """,
            (uuid,)
        ).fetchall()

        if len(rows) == 0:
            raise DatabaseError(f"No entries found for uuid '{uuid}'")

        item = StaticItemRowEntry(*rows[0]).create_static_item()
        for row in rows[1:]:
            row = StaticItemRowEntry(*row)
            item.data.append(row.as_static_module_data())
        return item

    def get_all_static_items(self):
        self._ensure_connection()

        rows = self._cursor.execute(
            f"""
            SELECT s.id AS item_id, s.uuid, s.name, s.created_at,
                c.id AS cell_id, c.row_index, c.column_index, c.value
            FROM {self.STATIC_ITEM_TABLE} s
            LEFT JOIN {self.STATIC_CELL_TABLE} c
                ON c.static_item_id = s.id
            ORDER BY s.id, c.row_index, c.column_index
            """
        ).fetchall()

        items = {}
        num_items = 0
        for row in rows:
            row_data = StaticItemRowEntry(*row)
            if row_data.uuid not in items:
                items[row_data.uuid] = row_data.create_static_item()
                num_items += 1
            else:
                items[row_data.uuid].data.append(row_data.as_static_module_data())
        
        return {"num_items": num_items, "items": items}
                
    def delete_uuid(self, uuid: str) -> bool:
        self._ensure_connection()

        row = self._cursor.execute(
            f"""
            SELECT id
            FROM {self.STATIC_ITEM_TABLE}
            WHERE uuid = ?
            """,
            (uuid,)
        ).fetchone()
       
        if row is None:
            raise DatabaseError(f"Error getting data about {uuid} from database")

        item_id = row[0]
        self._cursor.execute(
            f"""
            DELETE
            FROM {self.STATIC_CELL_TABLE}
            WHERE static_item_id = ?
            """,
            (item_id,)
        )
        self._cursor.execute(
            """
            DELETE
            FROM static_item
            WHERE uuid = ?
            """,
            (uuid,),
        )
        self._connection.commit()
        return True

    def get_num_rows_in_table(self, table: str) -> int:
        self._ensure_connection()
        count = self._cursor.execute(
            f"""
            SELECT COUNT(*) FROM {table};
            """
        ).fetchone()
        return int(count[0]) if count is not None else 0

    def update_flap(self, position: int, flap_data: FlapData) -> None:
        self._ensure_connection()
        self._cursor.execute(f"""
            UPDATE flap_positions
            SET character = ?,
                color_hex = ?
            WHERE flap_index = ?;
            """,
            (flap_data.character, flap_data.color_hex, flap_data.position,)
        )
        self._connection.commit()

    def _create_flap_position_table(self) -> None:
        self._ensure_connection()

        if self.FLAP_POSITION_TABLE not in self.tables:
            self.logger.debug("Creating flap position table")
            self._cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.FLAP_POSITION_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    flap_index INTEGER NOT NULL CHECK (flap_index >= 0 AND flap_index < 64),
                    character TEXT NOT NULL,
                    color_hex TEXT NOT NULL CHECK (length(color_hex) = 7 AND color_hex LIKE '#%'),
                    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now')),
                    UNIQUE (flap_index)
                )
            """)
            self._connection.commit()

    def _create_static_item_tables(self) -> None:
        self._ensure_connection()
        if self.STATIC_ITEM_TABLE not in self.tables:
            self.logger.debug("Creating item table")
            self._cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.STATIC_ITEM_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            self._connection.commit()
        
        if self.STATIC_CELL_TABLE not in self.tables:
            self.logger.debug("Creating item cell table")
            self._cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.STATIC_CELL_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    static_item_id INTEGER NOT NULL,
                    row_index INTEGER NOT NULL,
                    column_index INTEGER NOT NULL,
                    value TEXT NOT NULL,
                    FOREIGN KEY (static_item_id) REFERENCES static_item(id),
                    UNIQUE (static_item_id, row_index, column_index)
                )
            """)
            self._connection.commit()

    def _ensure_connection(self) -> None:
        if self._connection is None:
            raise RuntimeError("Database connection is not open")



class SplitFlapDatabase(DatabaseHandler):

    def __init__(self, database_file: str, num_flaps: int) -> None:
        super().__init__(database_file)
        self._num_flaps = num_flaps

    def init(self) -> None:
        with self.connect() as conn:
            conn.init()
    
    def connect(self) -> DatabaseConnection:
        self._num_connections += 1
        return Connection(self._file, self._num_flaps)

    def flap_positions_initialized(self) -> bool:
        with self.connect() as connection:
            connection.connect()
            db_flap_count = connection.get_num_rows_in_table(connection.FLAP_POSITION_TABLE)
            self.logger.info(f"Desired Flaps: {self._num_flaps} - Found Flaps: {db_flap_count}")
        return db_flap_count == self._num_flaps

    
