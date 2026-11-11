from __future__ import annotations

import os
import json
from pathlib import Path
import logging
import sqlite3
from abc import ABC, abstractmethod
from typing import Any

class DatabaseError(Exception):
    pass


class DatabaseHandler(ABC):

    def __init__(self, database_file: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing database connection")
        self._file = Path(database_file)
        if not os.path.exists(self._file):
            # Create the file
            self.logger.warning(f"No database file found at {self._file}, creating one now.")
            conn = sqlite3.connect(self._file)
            conn.close()
        self._db_sanity_check()
        self._num_connections = 0

    def __repr__(self) -> str:
        return f"DatabaseHandler({self._file.stem})"

    @abstractmethod
    def connect(self) -> DatabaseConnection:
        pass

    def _db_sanity_check(self) -> None:
        if not os.path.exists(self._file):
            raise FileExistsError(f"No file found at {self._file}")

class DatabaseConnection(ABC):

    def __init__(self, file: str) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._file = file
        self._connection = None
        self._cursor = None

    def __enter__(self) -> DatabaseConnection:
        return self.connect()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        if self._connection is None:
            self._connection = sqlite3.connect(self._file)
            self._cursor = self._connection.cursor()
        else:
            self.logger.error("Connection already open")
        return self

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            self._cursor = None
        else:
            self.logger.warning("Unable to close a connection that isn't open")

    @property
    def tables(self) -> List[str]:
        result = self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        return [item[0] for item in result]