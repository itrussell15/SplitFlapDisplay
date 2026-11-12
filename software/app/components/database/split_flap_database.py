from typing import Any, Dict, List, Optional

from dataclasses import dataclass

from ..core.database_handler import DatabaseHandler, DatabaseConnection, DatabaseError
from app.api.models.static_items import (
    StaticModuleData, StaticItem, StaticItems, Location
)
from app.api.models.flaps import FlapsByKey, FlapsByPosition, FlapData
from app.api.common import exception_response
from utils import get_env_var


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
            position=int(self.value)
        )

@dataclass(frozen=True)
class FlapRowEntry:
    position: int
    key: str
    glyph: str
    color_hex: str
    alias: Optional[str]

    def to_flap_data(self) -> FlapData:
        values = vars(self)
        values["aliases"] = [self.alias] if self.alias else []
        return FlapData(**values)    


class Connection(DatabaseConnection):

    FLAP_POSITION_TABLE: str = "flap_positions"
    FLAP_ALIAS_TABLE: str = "flap_aliases"
    STATIC_ITEM_TABLE: str = "static_item"
    STATIC_CELL_TABLE: str = "static_item_cell"

    def __init__(self, file: str, num_flaps: int) -> None:
        super().__init__(file)
        self._num_flaps = num_flaps

    def init(self) -> None:
        self._create_static_item_tables()
        self.get_static_item_names()
        self._create_flap_tables()

    def get_num_rows_in_table(self, table: str) -> int:
        self._ensure_connection()
        count = self._cursor.execute(
            f"""
            SELECT COUNT(*) FROM {table};
            """
        ).fetchone()
        return int(count[0]) if count is not None else 0

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
            value = cell.get("position", cell.get("value"))

            self._cursor.execute(
                f"""
                INSERT INTO {self.STATIC_CELL_TABLE} (static_item_id, row_index, column_index, value)
                VALUES (?, ?, ?, ?)
                """,
                (item_id, row, column, int(value)),
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

    def add_flap(self, position: int, key: str, glyph: str, color_hex: str) -> FlapData:
        key = key.upper()
        self._cursor.execute(
            f"""
            INSERT INTO {self.FLAP_POSITION_TABLE} (position, key, glyph, color_hex)
            VALUES (?, ?, ?, ?)
            """,
            (position, key, glyph, color_hex),
        )
        self.logger.info(f"Assigning {(key, glyph)} to flap {position}")
        self._connection.commit()
        return FlapData(
            position=position,
            key=key,
            glyph=glyph,
            color_hex=color_hex,
            aliases=[]
        )

    def get_flaps(self) -> FlapsByPosition:
        rows = self._cursor.execute(
            f"""
            SELECT 
                fp.position,
                fp.key,
                fp.glyph,
                fp.color_hex,
                fa.alias
            FROM {self.FLAP_POSITION_TABLE} fp
            LEFT JOIN {self.FLAP_ALIAS_TABLE} fa
                ON fa.position = fp.position
            ORDER BY fp.position, fa.alias
            """
        ).fetchall()

        flaps = self._flap_query_to_flap_data(rows)
        return FlapsByPosition(
            num_flaps=len(flaps),
            flaps=flaps
        )

    def get_flap_data_by_position(self, position: int) -> FlapData:
        if not 0 <= position < self._num_flaps:
            raise DatabaseError(f"Position {position} out of bounds. Must be 0-{self._num_flaps - 1}")

        rows = self._cursor.execute(
            f"""
            SELECT 
                fp.position,
                fp.key,
                fp.glyph,
                fp.color_hex,
                fa.alias
            FROM {self.FLAP_POSITION_TABLE} fp
            LEFT JOIN {self.FLAP_ALIAS_TABLE} fa
                ON fa.position = fp.position
            WHERE fp.position = ?
            ORDER BY fp.position, fa.alias
            """,
            (position,)
        ).fetchall()
        flaps = self._flap_query_to_flap_data(rows)
        if position not in flaps:
            raise DatabaseError(f"No flap configured at position {position}")
        return flaps[position]

    def get_all_flap_position_by_key(self) -> Dict[str, Any]:
        rows = self._cursor.execute(
            f"""
            SELECT 
                fp.position,
                fp.key,
                fp.glyph,
                fp.color_hex,
                fa.alias
            FROM {self.FLAP_POSITION_TABLE} fp
            LEFT JOIN {self.FLAP_ALIAS_TABLE} fa
                ON fa.position = fp.position
            ORDER BY fp.position, fa.alias
            """
        ).fetchall()
        flaps = self._flap_query_to_flap_data(rows)
        return {
            "num_flaps": len(flaps),
            "flaps": {flap.key: flap for flap in flaps.values()}
        }

    def get_flap_data_by_key(self, key: str) -> FlapData:
        row = self._cursor.execute(
            f"""
            SELECT 
                fp.position,
                fp.key,
                fp.glyph,
                fp.color_hex,
                fa.alias
            FROM {self.FLAP_POSITION_TABLE} fp
            LEFT JOIN {self.FLAP_ALIAS_TABLE} fa
                ON fa.position = fp.position
            WHERE fp.key = ?
            ORDER BY fp.position, fa.alias
            """,
            (key.upper(),)
        ).fetchall()
        if not row:
            return exception_response(f"{key} was not associated with a flap")

        flaps = self._flap_query_to_flap_data(row)
        if len(flaps) > 1:
            raise DatabaseError(f"Multiple flaps found for {key}")
        return list(flaps.values())[0]

    def update_flap(self, position: int, flap_data: FlapData) -> None:
        self._ensure_connection()
        self._cursor.execute(f"""
            UPDATE {self.FLAP_POSITION_TABLE}
            SET key = ?,
                glyph = ?,
                color_hex = ?
            WHERE position = ?;
            """,
            (flap_data.key.upper(), flap_data.glyph, flap_data.color_hex, flap_data.position,)
        )
        self._connection.commit()

    def add_flap_alias(self, position: int, alias: str) -> None:
        self._ensure_connection()
        self.logger.info(f"Adding {alias} as an alias to position {position}")
        self._cursor.execute(
            f"""
            INSERT INTO {self.FLAP_ALIAS_TABLE} (alias, position)
            VALUES (?, ?);
            """,
            (alias.upper(), position)
        )
        self._connection.commit()

    def get_flap_aliases(self, position: int) -> None:
        self._ensure_connection()
        aliases = self._cursor.execute(
            f"""
            SELECT alias  
            FROM {self.FLAP_ALIAS_TABLE}
            WHERE position = ?
            """,
            (position, )
        ).fetchall()
        return aliases

    def _flap_query_to_flap_data(self, query_response: List[Any]) -> Dict[int, FlapData]:
        flaps = {}
        for row in query_response:
            row = FlapRowEntry(*row)
            flap_data = flaps.get(row.position, None)
            if flap_data is None:
                flaps[row.position] = row.to_flap_data()
            else:
                if row.alias:
                    flap_data.aliases.append(row.alias)
        return flaps
        
    def _create_flap_tables(self) -> None:
        self._ensure_connection()

        if self.FLAP_POSITION_TABLE not in self.tables:
            self.logger.debug("Creating flap position table")
            self._cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.FLAP_POSITION_TABLE} (
                    position INTEGER PRIMARY KEY
                        CHECK (position >= 0 AND position < {self._num_flaps}),
                    key TEXT NOT NULL
                        COLLATE NOCASE
                        UNIQUE
                        CHECK (length(trim(key)) > 0),
                    glyph TEXT NOT NULL
                        UNIQUE
                        CHECK (length(glyph) > 0), 
                    color_hex TEXT NOT NULL DEFAULT '#FFFFFF'
                        CHECK (
                        length(color_hex) = 7
                        AND color_hex GLOB
                            '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'
                            || '[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'
                    ),
                    created_at INTEGER NOT NULL
                        DEFAULT (unixepoch())
                )
            """)
            self._create_flap_alias_table()
            self._connection.commit()

    def _create_flap_alias_table(self) -> None:
        self._ensure_connection()
        self.logger.debug("Creating flap position table")
        if self.FLAP_ALIAS_TABLE not in self.tables:
            self._cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.FLAP_ALIAS_TABLE} (
                    alias TEXT PRIMARY KEY COLLATE NOCASE,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (position)
                        REFERENCES {self.FLAP_POSITION_TABLE}(position)
                        ON UPDATE CASCADE
                        ON DELETE CASCADE,
                    CHECK (length(trim(alias)) > 0)
                )
            """)

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
                    value INTEGER NOT NULL,
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
