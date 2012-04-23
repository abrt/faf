# Copyright (C) 2012 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=E1101
import os
from .. import config

# sqlalchemy dependency is preferred to be explicit
import __main__
import pkg_resources
__main__.__requires__ = __requires__ = []
__requires__.append("SQLAlchemy >= 0.7.3")
pkg_resources.require(__requires__)

# now we can import sqlalchemy
from sqlalchemy import *
from sqlalchemy.exc import *
from sqlalchemy.orm import *
from sqlalchemy.orm.properties import *
from sqlalchemy.ext.declarative import declarative_base, declared_attr

# Parent of all our tables
class GenericTableBase(object):
    __lobs__ = {}

    __table_args__ =  ( { "mysql_engine": "InnoDB",
                          "mysql_charset": "utf8" } )

    def pkstr(self):
        parts = []
        for column in self.__columns__:
            if column.primary_key:
                parts.append(str(self.__getattribute__(column.name)))

        if not parts:
            raise Exception, "no primary key found for object '{0}'".format(self.__class__.__name__)

        return "-".join(parts)

    def _get_lobpath(self, name):
        classname = self.__class__.__name__
        if not name in self.__lobs__:
            raise Exception, "'{0}' does not allow a lob named '{1}'".format(classname, name)

        lobdir = os.path.join(config.CONFIG["storage.lobdir"], classname, name)
        if not os.path.isdir(lobdir):
            os.makedirs(lobdir)

        return os.path.join(lobdir, self.pkstr())

    # lob for Large OBject
    # in DB: blob = Binary Large OBject, clob = Character Large OBject
    def get_lob(self, name, binary=True):
        lobpath = self._get_lobpath(name)

        if not os.path.isfile(lobpath):
            return None

        mode = "r"
        if binary:
            mode += "b"
        with open(lobpath, mode) as lob:
            result = lob.read()

        return result

    def get_lob_fd(self, name, binary=True):
        lobpath = self._get_lobpath(name)

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
                raise Exception, "data is too long, '{0}' only allows length of {1}".format(dest.name, maxlen)

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
        lobpath = self._get_lobpath(name)

        if not overwrite and os.path.isfile(lobpath):
            raise Exception, "lob '{0}' already exists".format(name)

        maxlen = self.__lobs__[name]
        mode = "w"
        if binary:
            mode += "b"

        with open(lobpath, mode) as lob:
            if type(data) in [str, unicode]:
                self._save_lob_string(lob, data, maxlen, truncate)
            elif type(data) is file:
                if not truncate:
                    raise Exception, "when saving from file, truncate must be enabled"

                self._save_lob_file(lob, data, maxlen)
            else:
                raise Exception, "data must be either str, unicode or file"

    def del_lob(self, name):
        lobpath = self._get_lobpath(name)

        if not os.path.isfile(lobpath):
            raise Exception, "lob '{0}' does not exist".format(name)

        os.unlink(lobpath)

GenericTable = declarative_base(cls=GenericTableBase)

# all derived tables
# must be ordered - the latter may require the former
from common import *
from project import *
from opsys import *
from symbol import *
from problem import *
from report import *
from llvm import *

def getDatabase():
    db = Database.__instance__
    if db is None:
        db = Database()
    return db

class Database(object):
    __version__ = 0
    __instance__ = None

    def __init__(self, debug=False, session_kwargs={"autoflush": False, "autocommit": True}):
        if Database.__instance__ and Database.__instancecheck__(Database.__instance__):
            raise Exception("Database is a singleton and has already been instanciated. "
                            "If you have lost the reference, you can access the object "
                            "from Database.__instance__ .")

        self._db = create_engine(config.CONFIG["storage.connectstring"])
        self._db.echo = self._debug = debug
        GenericTable.metadata.bind = self._db
        self.session = Session(self._db)

        # Create all tables at once
        GenericTable.metadata.create_all()

        rows = self.session.query(DbMetadata).all()
        if len(rows) == 0:
            self.reset_metadata()
            rows = self.session.query(DbMetadata).all()
        if len(rows) != 1:
            raise Exception, "Your database is inconsistent. The '{0}' table " \
                             "should contain exactly one row, but it " \
                             "contains {1}.".format(DbMetadata.__tablename__, len(rows))

        metadata = rows[0]

        if metadata.version < Database.__version__:
            raise Exception, "The database you are trying to access has " \
                             "an older format. Use the migration tool to " \
                             "upgrade it."

        if metadata.version > Database.__version__:
            raise Exception, "The database you are trying to access has " \
                             "a newer format. You need to update FAF to " \
                             "be able to work with it."

        Database.__instance__ = self

    def close(self):
        self.session.close()

    def reset_metadata(self):
        metadata = DbMetadata()
        metadata.version = Database.__version__
        self.session.query(DbMetadata).delete()
        self.session.add(metadata)
        self.session.flush()
