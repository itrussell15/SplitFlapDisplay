from typing import List

from dataclasses import dataclass

from ..core.database_handler import DatabaseHandler, DatabaseConnection
from app.api.models.static_items import (
    StaticModuleData, StaticItem, StaticItems, Location
)

@dataclass(frozen=True)
class RowEntry:
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

    STATIC_ITEM_TABLE: str = "static_item"
    STATIC_CELL_TABLE: str = "static_item_cell"

    def init(self) -> None:
        if self.STATIC_ITEM_TABLE not in self.tables:
            self.logger.debug("Creating item table")
            self._cursor.execute("""
                CREATE TABLE IF NOT EXISTS static_item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            self._connection.commit()
        
        if self.STATIC_CELL_TABLE not in self.tables:
            self.logger.debug("Creating item cell table")
            self._cursor.execute("""
                CREATE TABLE IF NOT EXISTS static_item_cell (
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

        self.get_static_item_names()
        return True
        
    def add_static_item(self, name: str, uuid: str, timestamp: float, cells: list[dict]) -> int:
        if self._connection is None:
            raise RuntimeError("Database connection is not open")

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

    def get_item_from_uuid(self, uuid: str) -> StaticItem:
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

        item = RowEntry(*rows[0]).create_static_item()
        for row in rows[1:]:
            row = RowEntry(*row)
            item.data.append(row.as_static_module_data())
        return item

    def get_all_static_items(self):
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
            row_data = RowEntry(*row)
            if row_data.uuid not in items:
                items[row_data.uuid] = row_data.create_static_item()
                num_items += 1
            else:
                items[row_data.uuid].data.append(row_data.as_static_module_data())
        
        return {"num_items": num_items, "items": items}
                
class SplitFlapDatabase(DatabaseHandler):

    def init(self) -> None:
        with self.connect() as conn:
            conn.init()
    
    def connect(self) -> DatabaseConnection:
        return Connection(self._file)

    
