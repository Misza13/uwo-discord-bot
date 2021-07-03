from datetime import datetime
from typing import Optional

from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from dataclasses import dataclass


@dataclass
class Channel:
    id: int


@dataclass
class Server:
    id: int
    channels: list[Channel]


@dataclass
class Database:
    servers: list[Server]

    time_offset: int
    maintenance_time: Optional[datetime]

    def fixup(self):
        if not hasattr(self, 'time_offset') or self.time_offset is None:
            self.time_offset = 0

        if not hasattr(self, 'maintenance_time'):
            self.maintenance_time = None


def load_database() -> Database:
    data = load(open('data.yaml', 'r'), Loader=Loader)
    data.fixup()
    return data


def save_database(database: Database) -> None:
    dump(database, open('data.yaml', 'w'), Dumper=Dumper)
