# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
#
# This file is part of faf.
#
# faf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# faf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with faf.  If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=E1101
import sys
import os
import pkg_resources
from pyfaf.common import FafError, log, get_connect_string, import_dir

# sqlalchemy dependency is preferred to be explicit
# also required for EL6
import __main__
__main__.__requires__ = __requires__ = []
__requires__.append("SQLAlchemy >= 0.8.2")
pkg_resources.require(__requires__)

# now we can import sqlalchemy
# pylint: disable=wrong-import-position, wildcard-import, wrong-import-order
from sqlalchemy import *
# be explicit
from sqlalchemy.exc import * # pylint: disable=redefined-builtin
from sqlalchemy.orm import *
from sqlalchemy.orm.properties import *

from typing import Iterator, Optional

# all derived tables
# must be ordered - the latter may require the former
from .project import *
from .opsys import *
from .symbol import *
from .problem import *
from .bugtracker import *
from .bugzilla import *
from .mantisbt import *
from .externalfaf import *
from .report import *
from .llvm import *
from .sf_prefilter import *
from .debug import *
from .user import *
from .task import *


def column_len(cls, name) -> int:
    """
    Get the maximal length of a storage object attribute.
    """

    return cls.__table__.c[name].type.length


class Database(object):
    __version__ = 0
    __instance__ = None

    def __init__(self, debug=False, dry=False, create_schema=False) -> None:
        if Database.__instance__ and Database.__instancecheck__(Database.__instance__):
            raise FafError("Database is a singleton and has already been instantiated. "
                           "If you have lost the reference, you can access the object "
                           "from Database.__instance__ .")

        self._db = create_engine(get_connect_string())
        self._db.echo = self._debug = debug
        self._dry = dry
        GenericTable.metadata.bind = self._db
        self.session = Session(self._db)
        self.session._flush_orig = self.session.flush #pylint: disable=protected-access
        self.session.flush = self._flush_session

        if create_schema:
            GenericTable.metadata.create_all()

        Database.__instance__ = self

    def _flush_session(self, *args, **kwargs) -> None:
        if self._dry:
            log.warning("Dry run enabled, not flushing the database")
        else:
            self.session._flush_orig(*args, **kwargs) #pylint: disable=protected-access

    def close(self) -> None:
        self.session.close()

    def _del(self) -> None:
        """ Remove singleton instance - Only for testing purposes. """
        del Database.__instance__
        Database.__instance__ = None


def getDatabase(debug=False, dry=False) -> Database:
    db = Database.__instance__
    if db is None:
        db = Database(debug=debug, dry=dry)

    return db


class TemporaryDatabase(object):
    def __init__(self, session) -> None:
        self.session = session


class DatabaseFactory(object):
    def __init__(self) -> None:
        self.engine = create_engine(get_connect_string(), echo=False)
        self.sessionmaker = sessionmaker(bind=self.engine)

    def get_database(self) -> TemporaryDatabase:
        return TemporaryDatabase(self.sessionmaker())


class YieldQueryAdaptor:
    """
    This class wraps a Query into an object with interface that can be
    used at places where we need to iterate over items and want to know
    count of those items.
    """

    def __init__(self, query, yield_per) -> None:
        self._query = query
        self._yield_per = yield_per
        self._len: Optional[int] = None

    def __len__(self) -> Optional[int]:
        if self._len is None:
            self._len = int(self._query.count())

        return self._len

    def __iter__(self) -> Iterator[int]:
        return iter(self._query.yield_per(self._yield_per))


# Import all events
import_dir(__name__, os.path.dirname(__file__), "events")
