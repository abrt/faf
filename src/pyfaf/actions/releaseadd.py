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
from pyfaf.storage import OpSysRelease, OpSysReleaseStatus

class ReleaseAdd(Action):
    name = "releaseadd"


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
        if db_release is not None:
            self.log_info("Release '{0} {1}' is already defined"
                          .format(opsys.nice_name, cmdline.opsys_release))
            return 0

        if not cmdline.status in OpSysReleaseStatus.enums:
            self.log_error("Status '{0}' is invalid".format(cmdline.status))
            return 1

        self.log_info("Adding release '{0} {1}'"
                      .format(opsys.nice_name, cmdline.opsys_release))
        db_release = OpSysRelease()
        db_release.opsys = db_opsys
        db_release.version = cmdline.opsys_release
        db_release.status = cmdline.status
        db.session.add(db_release)

        db.session.flush()

        return 0

    def tweak_cmdline_parser(self, parser):
        parser.add_opsys(required=True, helpstr="operating system")
        parser.add_argument("--opsys-release", required=True,
                            validators=["validators.InputRequired()"],
                            help="operating system release")
        parser.add_opsys_rel_status(required=True)
