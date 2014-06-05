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
from pyfaf.queries import (get_external_faf_by_baseurl,
                           get_external_faf_by_id,
                           get_external_faf_by_name)


class ExternalFafModify(Action):
    name = "extfafmod"

    def __init__(self):
        super(ExternalFafModify, self).__init__()

    def run(self, cmdline, db):
        db_instance = get_external_faf_by_id(db, cmdline.instance_id)
        if db_instance is None:
            self.log_error("Instance with ID {0} is not defined in storage"
                           .format(cmdline.instance_id))
            return 1

        if cmdline.name is not None:
            db_instance2 = get_external_faf_by_name(db, cmdline.name)
            if db_instance2 is not None:
                self.log_warn("Instance with name '{0}' is already defined with"
                              " ID {1}".format(cmdline.name, db_instance2.id))
            else:
                self.log_info("Updated name")
                db_instance.name = cmdline.name

        if cmdline.baseurl is not None:
            baseurl = cmdline.baseurl.rstrip("/")
            db_instance2 = get_external_faf_by_baseurl(db, baseurl)
            if db_instance2 is not None:
                self.log_warn("Instance with base URL '{0}' is already defined"
                              " with ID {1}".format(baseurl, db_instance2.id))
            else:
                self.log_info("Updated base URL")
                db_instance.baseurl = baseurl

        db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("instance_id", type=int, help="Instance to modify")
        parser.add_argument("--name", help="Update the nice name")
        parser.add_argument("--baseurl", help="Update the base URL - API root")
