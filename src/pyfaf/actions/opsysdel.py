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

from pyfaf.actions import Action
from pyfaf.queries import get_opsys_by_name


class OpSysDel(Action):
    name = "opsysdel"


    def run(self, cmdline, db):
        for opsys in cmdline.OPSYS:
            db_opsys = get_opsys_by_name(db, opsys)

            if not db_opsys:
                self.log_warn("Operating system '{0}' not found"
                              .format(db_opsys))
                continue

            if db_opsys.releases:
                self.log_warn("Unable to delete operating system with associated"
                              " releases. Following is the list of associated "
                              " releases:")
                for release in db_opsys.releases:
                    self.log_warn(release)

                continue

            self.log_info("Removing operating system '{0}'".format(opsys))

            db.session.delete(db_opsys)
            db.session.flush()

        return 0

    def tweak_cmdline_parser(self, parser):
        parser.add_opsys_pos_arg(multiple=True, helpstr="operating system to delete")
