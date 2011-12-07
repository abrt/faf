# Copyright (C) 2011 Red Hat, Inc.
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
from . import abrt_report_check
from . import debuginfo_report
from . import debuginfo_sources
from . import fedora_pkgdb_collection
from . import fedora_pkgdb_package
from . import koji_build
from . import koji_build_funfin_report
from . import koji_rpm
from . import koji_tag
from . import rhbz_attachment
from . import rhbz_bug
from . import rhbz_bug_btserver_report
from . import rhbz_comment
from . import rhbz_user
from .. import run

class Cursor:
    def __init__(self, database):
        self.database = database
        self.cursor = database.conn.cursor()

    def execute(self, sql, parameters=[]):
        if self.database.type == "mysql":
            sql = sql.replace("?", "%s")
        self.cursor.execute(sql, parameters)

    def execute_create_table_if_not_exists(self, table_name, fields, indices):
        """
        fields - a list of pairs (name, type)
        indices - a list of pairs (name, type)
        """
        if self.database.type == "mysql":
            # We need to avoid a warning issued by existing table even for
            # "IF NOT EXISTS" queries.
            self.cursor.execute(u"""SELECT table_name FROM information_schema.tables
                                     WHERE table_schema = '{0}'
                                       AND table_name = '{1}';""".format(self.database.mysql_db, table_name))
            if len(self.cursor.fetchall()) == 0:
                params = [" ".join(field) for field in fields]
                params.extend(["INDEX({0})".format(index[0]) for index in indices if index[1] != "TEXT"])
                params.extend(["INDEX({0}(6))".format(index[0]) for index in indices if index[1] == "TEXT"])
                self.cursor.execute(u"CREATE TABLE {0} ({1})".format(table_name, u", ".join(params)))
        else:
            params = [" ".join(field) for field in fields]
            self.cursor.execute(u"CREATE TABLE IF NOT EXISTS {0} ({1})".format(table_name, u", ".join(params)))
            [self.cursor.execute(u"CREATE INDEX IF NOT EXISTS {0}_{1} ON {0} ({1})".format(table_name, index[0]))
                                 for index in indices]

    def fetch_table_list(self):
        if self.database.type == "mysql":
            self.cursor.execute(u"""SELECT * FROM information_schema.tables
                                     WHERE table_schema = '{0}'""".format(self.database.mysql_db))
            rows = self.cursor.fetchall()
            return [row[2] for row in rows]
        elif self.database.type == "sqlite3":
            self.cursor.execute("SELECT * FROM sqlite_master")
            rows = self.cursor.fetchall()
            return [row[1] for row in rows]
        else:
            exit("Invalid database type {0}.".format(self.database_type))

    def fetch_table_info(self, table):
        if self.database.type == "mysql":
            self.cursor.execute("DESCRIBE {0}".format(table))
            rows = [list(row)[:2] for row in self.cursor.fetchall()]
            for row in rows:
                row[1] = "INTEGER" if row[1].startswith("int") else row[1].upper()
            return rows
        elif self.database.type == "sqlite3":
            self.cursor.execute("PRAGMA table_info({0})".format(table))
            return [list(row[1:3]) for row in self.cursor.fetchall()]
        else:
            exit("Invalid database type {0}.".format(self.database_type))

    def fetchall(self):
        return self.cursor.fetchall()

    def close(self):
        self.cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.cursor is not None:
            self.cursor.close()

class Database:
    def __init__(self, db_type=None, sqlite3_cache_dir=None, mysql_host=None,
                 mysql_socket=None,
                 mysql_user=None, mysql_passwd=None, mysql_db=None):
        if db_type is None:
            db_type = run.config_get("cache.dbtype")
        if sqlite3_cache_dir is None:
            sqlite3_cache_dir = run.config_get("cache.directory")
        if mysql_host is None:
            mysql_host = run.config_get("cache.mysqlhost")
        if mysql_user is None:
            mysql_user = run.config_get("cache.mysqluser")
        if mysql_passwd is None:
            mysql_passwd = run.config_get("cache.mysqlpasswd")
        if mysql_db is None:
            mysql_db = run.config_get("cache.mysqldb")

        self.type = db_type
        self.sqlite3_cache_dir = sqlite3_cache_dir
        self.mysql_host = mysql_host
        self.mysql_user = mysql_user
        self.mysql_passwd = mysql_passwd
        self.mysql_db = mysql_db

        if db_type == "sqlite3":
            import sqlite3
            import os
            db_path = os.path.join(sqlite3_cache_dir, "sqlite.db")
            self.conn = sqlite3.connect(db_path, timeout=500,
                                   detect_types=sqlite3.PARSE_DECLTYPES)
        elif db_type == "mysql":
            import MySQLdb
            if mysql_socket is None:
                self.conn = MySQLdb.connect(host = mysql_host,
                                            user = mysql_user,
                                            passwd = mysql_passwd,
                                            db = mysql_db,
                                            charset = "utf8")
            else:
                self.conn = MySQLdb.connect(host = mysql_host,
                                            user = mysql_user,
                                            passwd = mysql_passwd,
                                            unix_socket = mysql_socket,
                                            db = mysql_db,
                                            charset = "utf8")
        else:
            import sys
            sys.stderr.write("Invalid database type: {0}".format(db_type))
            sys.exit(1)

        self._cursor = self.cursor()


    def execute(self, sql, parameters=[]):
        self._cursor.execute(sql, parameters)

    def execute_create_table_if_not_exists(self, table_name, fields, indices):
        self._cursor.execute_create_table_if_not_exists(table_name, fields, indices)

    def fetch_table_list(self):
        return self._cursor.fetch_table_list()

    def fetch_table_info(self, table):
        return self._cursor.fetch_table_info(table)

    def fetchall(self):
        return self._cursor.fetchall()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def cursor(self):
        return Cursor(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._cursor is not None:
            self._cursor.close()
        if self.conn is not None:
            self.conn.close()
