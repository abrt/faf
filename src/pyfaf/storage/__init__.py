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
import errno
import os
from pyfaf.common import FafError, log, get_connect_string, import_dir
from pyfaf.config import config

# sqlalchemy dependency is preferred to be explicit
# also required for EL6
import __main__
import pkg_resources
import six
from six.moves import range
__main__.__requires__ = __requires__ = []
__requires__.append("SQLAlchemy >= 0.8.2")
pkg_resources.require(__requires__)

# now we can import sqlalchemy
from sqlalchemy import *
# be explicit
from sqlalchemy.exc import *
from sqlalchemy.orm import *
from sqlalchemy.orm.properties import *
from sqlalchemy.ext.declarative import declarative_base


# Parent of all our tables
class GenericTableBase(object):
    __lobs__ = {}

    __table_args__ = ({"mysql_engine": "InnoDB",
                       "mysql_charset": "utf8"})

    def pkstr(self):
        parts = []
        for column in self.__table__._columns:
            if column.primary_key:
                parts.append(str(self.__getattribute__(column.name)))

        if not parts:
            raise FafError("No primary key found for object '{0}'".format(self.__class__.__name__))

        return "-".join(parts)

    def get_lob_path(self, name):
        classname = self.__class__.__name__
        if not name in self.__lobs__:
            raise FafError("'{0}' does not allow a lob named '{1}'".format(classname, name))

        pkstr = self.pkstr()
        pkstr_long = pkstr
        while len(pkstr_long) < 5:
            pkstr_long = "{0}{1}".format("".join(["0" for i in range(5 - len(pkstr_long))]), pkstr_long)

        lobdir = os.path.join(config["storage.lobdir"], classname, name,
                              pkstr_long[0:2], pkstr_long[2:4])
        try:
            os.makedirs(lobdir)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise

        return os.path.join(lobdir, pkstr)

    def has_lob(self, name):
        return os.path.isfile(self.get_lob_path(name))

    # lob for Large OBject
    # in DB: blob = Binary Large OBject, clob = Character Large OBject
    def get_lob(self, name, binary=True):
        lobpath = self.get_lob_path(name)

        if not os.path.isfile(lobpath):
            return None

        mode = "r"
        if binary:
            mode += "b"
        with open(lobpath, mode) as lob:
            result = lob.read()

        return result

    def get_lob_fd(self, name, binary=True):
        lobpath = self.get_lob_path(name)

        if not os.path.isfile(lobpath):
            return None

        mode = "r"
        if binary:
            mode += "b"

        try:
            result = open(lobpath, mode)
        except:
            result = None

        return result

    def _save_lob_string(self, dest, data, maxlen=0, truncate=False):
        if maxlen > 0 and len(data) > maxlen:
            if truncate:
                data = data[:maxlen]
            else:
                raise FafError("Data is too long, '{0}' only allows length of {1}".format(dest.name, maxlen))

        dest.write(data)

    def _save_lob_file(self, dest, src, maxlen=0, bufsize=4096):
        read = 0
        buf = src.read(bufsize)
        while buf and (maxlen <= 0 or read <= maxlen):
            read += len(buf)
            if maxlen > 0 and read > maxlen:
                buf = buf[:(read - maxlen)]
            dest.write(buf)
            buf = src.read(bufsize)

    def save_lob(self, name, data, binary=True, overwrite=False, truncate=False):
        lobpath = self.get_lob_path(name)

        if not overwrite and os.path.isfile(lobpath):
            raise FafError("Lob '{0}' already exists".format(name))

        maxlen = self.__lobs__[name]
        mode = "w"
        if binary:
            mode += "b"

        with open(lobpath, mode) as lob:
            if isinstance(data, six.string_types):
                self._save_lob_string(lob, data, maxlen, truncate)
            elif hasattr(data, "read"):
                if not truncate:
                    raise FafError("When saving from file, truncate must be enabled")

                self._save_lob_file(lob, data, maxlen)
            else:
                raise FafError("Data must be either str, unicode or file-like object")

    def del_lob(self, name):
        lobpath = self.get_lob_path(name)

        if not os.path.isfile(lobpath):
            raise FafError("Lob '{0}' does not exist".format(name))

        os.unlink(lobpath)

GenericTable = declarative_base(cls=GenericTableBase)

# all derived tables
# must be ordered - the latter may require the former
# ToDo: rewrite with import_dir
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


def column_len(cls, name):
    """
    Get the maximal length of a storage object attribute.
    """

    return cls.__table__.c[name].type.length


def getDatabase(debug=False, dry=False):
    db = Database.__instance__
    if db is None:
        db = Database(debug=debug, dry=dry)

    return db


class Database(object):
    __version__ = 0
    __instance__ = None

    def __init__(self, debug=False, dry=False, session_kwargs={"autoflush": False, "autocommit": True},
                 create_schema=False):
        if Database.__instance__ and Database.__instancecheck__(Database.__instance__):
            raise FafError("Database is a singleton and has already been instanciated. "
                           "If you have lost the reference, you can access the object "
                           "from Database.__instance__ .")

        self._db = create_engine(get_connect_string())
        self._db.echo = self._debug = debug
        self._dry = dry
        GenericTable.metadata.bind = self._db
        self.session = Session(self._db, **session_kwargs)
        self.session._flush_orig = self.session.flush
        self.session.flush = self._flush_session

        if create_schema:
            GenericTable.metadata.create_all()

        Database.__instance__ = self

    def _flush_session(self, *args, **kwargs):
        if self._dry:
            log.warn("Dry run enabled, not flushing the database")
        else:
            self.session._flush_orig(*args, **kwargs)

    def close(self):
        self.session.close()


class TemporaryDatabase(object):
    def __init__(self, session):
        self.session = session


class DatabaseFactory(object):
    def __init__(self, autocommit=False):
        self.engine = create_engine(get_connect_string(), echo=False)
        self.sessionmaker = sessionmaker(bind=self.engine, autocommit=autocommit)

    def get_database(self):
        return TemporaryDatabase(self.sessionmaker())


class YieldQueryAdaptor:
    """
    This class wraps a Query into an object with interface that can be
    used at places where we need to iterate over items and want to know
    count of those items.
    """

    def __init__(self, query, yield_per):
        self._query = query
        self._yield_per = yield_per
        self._len = None

    def __len__(self):
        if self._len is None:
            self._len = int(self._query.count())

        return self._len

    def __iter__(self):
        return iter(self._query.yield_per(self._yield_per))


# Import all events
import_dir(__name__, os.path.dirname(__file__), "events")
