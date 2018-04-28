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
from pyfaf.opsys import systems
from pyfaf.queries import get_opsys_by_name, get_osrelease
from pyfaf.storage import OpSysReleaseStatus


class ReleaseModify(Action):
    name = "releasemod"

    def __init__(self):
        super(ReleaseModify, self).__init__()

    def run(self, cmdline, db):
        if cmdline.opsys is None:
            self.log_error("You must specify an operating system")
            return 1

        if not cmdline.opsys in systems:
            self.log_error("Operating system '{0}' does not exist"
                           .format(cmdline.opsys))
            return 1

        opsys = systems[cmdline.opsys]
        db_opsys = get_opsys_by_name(db, opsys.nice_name)
        if db_opsys is None:
            self.log_error("Operating system '{0}' is not installed"
                           .format(opsys.nice_name))
            return 1

        db_release = get_osrelease(db, opsys.nice_name, cmdline.opsys_release)
        if db_release is None:
            self.log_info("Release '{0} {1}' is not defined"
                          .format(opsys.nice_name, cmdline.opsys_release))
            return 1

        if cmdline.status is not None and cmdline.status != db_release.status:
            if not cmdline.status in OpSysReleaseStatus.enums:
                self.log_error("Status '{0}' is invalid".format(cmdline.status))
                return 1

            self.log_info("Updating status of '{0} {1}': {2} ~> {3}"
                          .format(opsys.nice_name, db_release.version,
                                  db_release.status, cmdline.status))

            db_release.status = cmdline.status

        db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_opsys()
        parser.add_opsys_release()
        parser.add_argument("-s", "--status", default=None,
                            help="ACTIVE, UNDER_DEVELOPMENT or EOL")
