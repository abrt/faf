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
from .. import run
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

def db_connect(db_type=run.config_get("cache.db_type"),
               sqlite3_cache_dir=run.config_get("cache.directory"),
               mysql_host=run.config_get("cache.mysql_host"),
               mysql_user=run.config_get("cache.mysql_user"),
               mysql_passwd=run.config_get("cache.mysql_passwd"),
               mysql_db=run.config_get("cache.mysql_db")):
    if db_type == "sqlite3":
        import sqlite3
        import os
        db_path = os.path.join(sqlite3_cache_dir, "sqlite.db")
        return sqlite3.connect(db_path, timeout=500,
                               detect_types=sqlite3.PARSE_DECLTYPES)
    elif db_type == "mysql":
        import MySQLdb
        return MySQLdb.connect(host = mysql_host,
                               user = mysql_user,
                               passwd = mysql_passwd,
                               db = mysql_db)
    else:
        import sys
        sys.stderr.write("Invalid database type: {0}".format(db_type))
        sys.exit(1)
