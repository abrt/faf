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
from .. import support
import sys
import logging
import glob
import os

# Creating a MySQL database:
# CREATE DATABASE faf CHARACTER SET = utf8 COLLATE = utf8_general_ci;

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
                convertType = lambda t: "TEXT CHARACTER SET utf8 COLLATE utf8_general_ci" if t == "TEXT" else t
                # Backticks `` are necessary to avoid collision with MySQL reserved keywords.
                params = ["`{0}` {1}".format(field[0], convertType(field[1])) for field in fields]
                params.extend(["INDEX({0})".format(index[0]) for index in indices if index[1] != "TEXT"])
                params.extend(["INDEX({0}(6))".format(index[0]) for index in indices if index[1] == "TEXT"])
                query = u"CREATE TABLE {0} ({1})".format(table_name, u", ".join(params))
                logging.debug("Creating table: " + query)
                self.cursor.execute(query)
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
                                            use_unicode = True,
                                            charset = "utf8")
            else:
                self.conn = MySQLdb.connect(host = mysql_host,
                                            user = mysql_user,
                                            passwd = mysql_passwd,
                                            unix_socket = mysql_socket,
                                            db = mysql_db,
                                            use_unicode = True,
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

class Target:
    def __init__(self, db, cache_dir, target_dir_name):
        self.db = db
        self.cache_dir = cache_dir
        self.target_dir_name = target_dir_name
        self.full_dir = os.path.join(self.cache_dir, self.target_dir_name)

    def remove_all(self):
        paths = glob.glob("{0}/*".format(self.full_dir))
        [self.remove(os.path.basename(path)) for path in paths]
        logging.info("Removed from '{0}': {1}".format(
                self.full_dir, len(paths)))

    def verify_all(self, remove, check_database):
        paths = glob.glob("{0}/*".format(self.full_dir))
        logging.info("Verifying {0} {1}...".format(
                len(paths), self.target_dir_name))
        index = 0
        for path in sorted(paths):
            index += 1
            logging.debug("[{0}/{1}] Verifying {2}.".format(
                    index, len(paths), path))
            self.verify(os.path.basename(path), remove, check_database)

        # TODO: verify that database doesn't contain superfluous
        # entries

    def _entry_path(self, entry_id):
        return os.path.join(self.full_dir, str(entry_id))

    def get_path(self, entry_id):
        path = self._entry_path(entry_id)
        if not os.path.exists(path):
            raise Exception("Path not found for entry {0}".format(entry_id))
        return path

    def list(self):
        result = []
        paths = glob.glob("{0}/*".format(self.full_dir))
        for path in paths:
            base = str(os.path.basename(path))
            mtime = str(os.path.getmtime(path))
            result.append((base, mtime))
        return result

    def stats(self, oneline):
        paths = glob.glob("{0}/*".format(self.full_dir))
        total_size = 0
        max_size = 0
        min_size = 1e20
        for path in paths:
            size = os.path.getsize(path)
            total_size += size
            max_size = max(max_size, size)
            min_size = min(min_size, size)
        if oneline:
            if len(paths) > 0:
                sys.stdout.write(
                    "{0}: {1} entries, {2} total (max {3}, min {4})\n".format(
                        self.target_dir_name,
                        len(paths),
                        support.human_byte_count(total_size),
                        support.human_byte_count(max_size),
                        support.human_byte_count(min_size)))
            else:
                sys.stdout.write("{0}: {1} entries\n".format(
                        self.target_dir_name, len(paths)))
        else:
            sys.stdout.write("{0} count         : {1}\n".format(
                    self.target_dir_name, len(paths)))
            sys.stdout.write("{0} total size    : {1}\n".format(
                    self.target_dir_name, support.human_byte_count(total_size)))
            sys.stdout.write("{0} max entry size: {1}\n".format(
                    self.target_dir_name, support.human_byte_count(max_size)))
            sys.stdout.write("{0} min entry size: {1}\n".format(
                    self.target_dir_name, support.human_byte_count(min_size)))

class TextualTarget(Target):
    def __init__(self, db, cache_dir, namespace, prefix=""):
        self.namespace = namespace
        self.prefix = prefix
        target_dir_name = namespace.__name__
        target_dir_name = target_dir_name[target_dir_name.rindex(".") + 1:]
        target_dir_name = target_dir_name.replace("_", "-")
        if len(prefix) > 0:
            target_dir_name = "{0}-{1}".format(prefix, target_dir_name)
        Target.__init__(self, db, cache_dir, target_dir_name)

    def _load_by_id(self, entry_id):
        path = self._entry_path(entry_id)
        entry = self._load_from_file(path, failure_allowed=False)
        if not entry:
            raise Exception("Failed to load entry '{0}'.\n".format(entry_id))
        return entry

    def _load_from_file(self, path, failure_allowed):
        if not os.path.isfile(path):
            if failure_allowed:
                return None
            raise Exception("Entry file '{0}' not found.\n".format(path))
        f = open(path, 'r')
        text = f.read().decode('utf-8')
        f.close()
        if len(text) == 0:
            if failure_allowed:
                return None
            raise Exception("File '{0}' is empty.\n".format(path))
        return self.namespace.parser.from_text(text, failure_allowed)

    def get(self, entry_id):
        # Convert from text to entry and then to text to filter
        # deprecated or broken parts of the database.
        entry = self._load_by_id(entry_id)
        return self.namespace.parser.to_text(entry)

    def _save_to_file(self, entry, overwrite):
        if not os.path.isdir(self.full_dir):
            os.makedirs(self.full_dir)

        path = self._entry_path(entry.id)
        if not overwrite and os.path.exists(path):
            raise Exception("Entry '{0}' already exists.\n".format(entry.id))
        # The to_text method might fail, as it checks validity. Call it
        # before opening the file to avoid creating empty file.
        text = self.namespace.parser.to_text(entry)
        f = open(path, 'w')
        f.write(text.encode('utf-8'))
        f.close()

    def add(self, entry_id, entry_value, overwrite):
        entry = self.namespace.parser.from_text(unicode(entry_value, "utf-8"), failure_allowed=False)
        self._save_to_file(entry, overwrite)

        # Update database
        self.namespace.parser.database_create_table(self.db, self.prefix)
        self.namespace.parser.database_add(entry, self.db, self.prefix)
        self.db.commit()

    def remove(self, entry_id):
        path = self._entry_path(entry_id)
        if not os.path.isfile(path):
            raise Exception("Entry '{0}' not found.\n".format(entry_id))
        os.remove(path)

        # Update database
        self.namespace.parser.database_remove(entry_id, self.db, self.prefix)
        self.db.commit()

    def verify(self, entry_id, remove, check_database):
        logging.debug("Loading entry '{0}' from {1} cache...".format(
                entry_id, self.target_dir_name))
        path = self._entry_path(entry_id)
        logging.debug("Verifiing {0} '{1}'...".format(self.target_dir_name, entry_id))
        entry = self._load_from_file(path,failure_allowed=True)
        if entry is None:
            if remove:
                logging.info("Failed to parse {0}.\n".format(path, validity))
                logging.info("Removing {0}.".format(path))
                self.remove(entry_id)
            else:
                raise Exception("Failed to parse {0}.\n".format(path, validity))

        validity = self.namespace.parser.is_valid(entry)
        if validity != True:
            if remove:
                logging.info("Invalid file {0}: {1}\n".format(path, validity))
                logging.info("Removing {0}.".format(path))
                self.remove(entry_id)
            else:
                raise Exception("Invalid file {0}: {1}\n".format(path, validity))

        # Check database
        if check_database:
            database_validity = self.namespace.parser.database_is_valid(entry, self.db, self.prefix)
            if database_validity != True:
                if remove:
                    logging.info("Invalid database entry {0}: {1}\n".format(path, database_validity))
                    logging.info("Removing {0}.".format(path))
                    self.remove(entry_id)
                else:
                    raise Exception("Invalid database entry {0}: {1}\n".format(path, database_validity))

    def rebuild_db(self):
        self.namespace.parser.database_drop_table(self.db, self.prefix)
        self.namespace.parser.database_create_table(self.db, self.prefix)
        self.db.commit()
        paths = glob.glob("{0}/*".format(self.full_dir))
        index = 0
        entry_ids = [os.path.basename(path) for path in paths]
        for entry_id in entry_ids:
            index +=1
            logging.debug("[{0}/{1}] {2} #{3}.".format(
                    index, len(entry_ids), self.target_dir_name, entry_id))
            entry = self._load_by_id(entry_id)
            self.namespace.parser.database_add(entry, self.db, self.prefix)
            if index % 1000 == 0:
                self.db.commit()
        self.db.commit()

class BinaryTarget(Target):
    def __init__(self, db, cache_dir, name):
        Target.__init__(self, db, cache_dir, name)
        self.name = name

    def get(self, entry_id):
        path = self._entry_path(entry_id)
        if not os.path.isfile(path):
            raise Exception("Entry file '{0}' not found.".format(path))
        with open(path, 'r') as f:
            return f.read()

    def add(self, entry_id, entry_value, overwrite):
        directory = self.full_dir
        if not os.path.isdir(directory):
            os.makedirs(directory)
        path = self._entry_path(entry_id)
        if not overwrite and os.path.exists(path):
            raise Exception("Entry '{0}' already exists.".format(entry_id))
        with open(path, 'w') as f:
            f.write(entry_value)

    def remove(self, entry_id):
        if not os.path.isfile(self._entry_path(entry_id)):
            raise Exception("Entry '{0}' not found.".format(entry_id))
        os.remove(self._entry_path(self, entry_id))

    def verify(self, entry_id, remove, check_database):
        logging.debug("Skipping '{0}' from {1} cache, because it's a binary record...".format(
                entry_id, self.target_dir_name))

    def rebuild_db(self):
        pass

class TargetList:
    def __init__(self, db, cache_dir):
        self.list = [
            # Red Hat Bugzilla
            TextualTarget(db, cache_dir, rhbz_bug),
            TextualTarget(db, cache_dir, rhbz_attachment),
            TextualTarget(db, cache_dir, rhbz_comment),
            TextualTarget(db, cache_dir, rhbz_user),
            TextualTarget(db, cache_dir, abrt_report_check, "rhbz"),
            BinaryTarget(db, cache_dir, "rhbz-optimized-backtrace"),
            # Fedora
            TextualTarget(db, cache_dir, fedora_pkgdb_collection),
            TextualTarget(db, cache_dir, fedora_pkgdb_package),
            TextualTarget(db, cache_dir, koji_tag, "fedora"),
            TextualTarget(db, cache_dir, koji_build, "fedora"),
            TextualTarget(db, cache_dir, koji_build_funfin_report, "fedora"),
            BinaryTarget(db, cache_dir, "fedora-koji-build-log-data"),
            TextualTarget(db, cache_dir, koji_rpm, "fedora"),
            BinaryTarget(db, cache_dir, "fedora-koji-rpm-data"),
            TextualTarget(db, cache_dir, debuginfo_report, "fedora"),
            TextualTarget(db, cache_dir, debuginfo_sources, "fedora"),
            # RHEL
            TextualTarget(db, cache_dir, koji_tag, "rhel"),
            TextualTarget(db, cache_dir, koji_build, "rhel"),
            BinaryTarget(db, cache_dir, "rhel-koji-build-log-data"),
            TextualTarget(db, cache_dir, koji_rpm, "rhel"),
            BinaryTarget(db, cache_dir, "rhel-koji-rpm-data"),
            TextualTarget(db, cache_dir, debuginfo_report, "rhel"),
            TextualTarget(db, cache_dir, debuginfo_sources, "rhel")
        ]

    def from_directory_name(self, dir_name):
        for target in self.list:
            if target.target_dir_name == dir_name:
                return target
        raise Exception("Unknown target '{0}'.\n".format(dir_name))

    def verify_all(self, remove_broken, check_database):
        [target.verify_all(remove_broken, check_database) for target in self.list]

    def remove_all(self):
        [target.remove_all() for target in self.list]

    def stats(self):
        [target.stats(oneline=True) for target in self.list]

    def rebuild_db(self):
        [target.rebuild_db() for target in self.list]
