# Copyright (C) 2014  ABRT Team
# Copyright (C) 2014  Red Hat, Inc.
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

from pyfaf.actions import Action
from pyfaf.queries import get_external_faf_by_name, get_external_faf_by_baseurl
from pyfaf.storage import ExternalFafInstance


class ExternalFafAdd(Action):
    name = "extfafadd"

    def __init__(self):
        super(ExternalFafAdd, self).__init__()

    def run(self, cmdline, db):
        db_instance = get_external_faf_by_name(db, cmdline.NAME)
        if db_instance is not None:
            self.log_error("An instance named '{0}' is already present "
                           "in storage saved with ID {1}"
                           .format(cmdline.NAME, db_instance.id))
            return 1

        baseurl = cmdline.BASEURL.rstrip("/")
        db_instance = get_external_faf_by_baseurl(db, baseurl)
        if db_instance is not None:
            self.log_error("An instance with base URL '{0}' is already "
                           "present in storage saved with ID {1}"
                           .format(cmdline.BASEURL, db_instance.id))
            return 1

        db_instance = ExternalFafInstance()
        db_instance.name = cmdline.NAME
        db_instance.baseurl = baseurl
        db.session.add(db_instance)
        db.session.flush()

        self.log_info("The external FAF instance was added with ID {0}"
                      .format(db_instance.id))

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("NAME", help="Nice name of the instance")
        parser.add_argument("BASEURL", help="API root")
