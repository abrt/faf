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
from sqlalchemy.ext.declarative import *

# a generic table - parent of all our tables
# it is a custom replacement for DeclarativeReflectedBase
# which does not work at the moment
# may be dropped and replaced by DeclarativeReflectedBase
# in the future
class GenericTable(object):
    __columns__ = []
    __relationships__ = {}
    __lobs__ = {}
    __mapper_args__ = {}
    __table_args__ =  ( { "mysql_engine": "InnoDB",
                          "mysql_charset": "utf8" } )

    @classmethod
    def load(cls, metadata):
        cls.table = Table(cls.__tablename__, metadata, *cls.__columns__, **cls.__table_args__)

        relationships = {}
        for key in cls.__relationships__:
            value = cls.__relationships__[key]
            if type(value) is str:
                relationships[key] = eval(value)
            else:
                relationships[key] = value

        cls.mapper = mapper(cls, cls.table, properties=relationships, **cls.__mapper_args__)

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

    # ToDo: this will not handle huge files very well...
    def save_lob(self, name, data, binary=True, overwrite=False, truncate=False):
        lobpath = self._get_lobpath(name)

        if not overwrite and os.path.isfile(lobpath):
            raise Exception, "lob '{0}' already exists".format(name)

        maxlen = self.__lobs__[name]
        if maxlen > 0 and len(data) > maxlen:
            if truncate:
                data = data[maxlen:]
            else:
                raise Exception, "data is too long, '{0}' only allows length of {1}".format(name, maxlen)

        mode = "w"
        if binary:
            mode += "b"
        with open(lobpath, mode) as lob:
            lob.write(data)

# all derived tables
# must be ordered - the latter may require the former
from common import *
from project import *
from opsys import *
from symbol import *
from problem import *
from report import *
from llvm import *

class Database(object):
    __version__ = 0
    __instance__ = None

    @classmethod
    def reset_dbmd(cls, session):
        dbmd = DbMd()
        dbmd.version = cls.__version__

        session.query(DbMd).delete()
        session.add(dbmd)
        session.flush()

    def __init__(self, debug=False, session_kwargs={"autoflush": False, "autocommit": True}):
        if Database.__instance__ and Database.__instancecheck__(Database.__instance__):
            raise Exception("Database is a singleton and has already been instanciated. "
                            "If you have lost the reference, you can access the object "
                            "from Database.__instance__ .")

        # maybe too aggressive
        clear_mappers()

        self._db = create_engine(config.CONFIG["storage.connectstring"])
        self._db.echo = self._debug = debug
        self._md = MetaData(bind=self._db)

        for table in GenericTable.__subclasses__():
            table.load(self._md)
            self.__setattr__(table.__name__, table)

        # create all tables at once
        self._md.create_all()

        self.session = Session(bind=self._db, **session_kwargs)

        rows = self.session.query(DbMd).all()

        if len(rows) == 0:
            Database.reset_dbmd(self.session)
            rows = self.session.query(DbMd).all()

        if len(rows) != 1:
            raise Exception, "Your database is inconsistent. The '{0}' table " \
                             "should contain exactly one row, but it " \
                             "contains {1}.".format(DbMd.__tablename__, len(rows))

        dbmd = rows[0]

        if dbmd.version < Database.__version__:
            raise Exception, "The database you are trying to access has " \
                             "an older format. Use the migration tool to " \
                             "upgrade it."

        if dbmd.version > Database.__version__:
            raise Exception, "The database you are trying to access has " \
                             "a newer format. You need to update FAF to " \
                             "be able to work with it."

        Database.__instance__ = self

    def close(self):
        self.session.close()
