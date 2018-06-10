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
from pyfaf.storage.opsys import OpSys


class OpSysAdd(Action):
    name = "opsysadd"


    def run(self, cmdline, db):
        opsys = get_opsys_by_name(db, cmdline.NAME)

        if opsys:
            self.log_error("Operating system '{0}' already defined"
                           .format(cmdline.NAME))
            return 1

        self.log_info("Adding operating system '{0}'".format(cmdline.NAME))

        new = OpSys()
        new.name = cmdline.NAME
        db.session.add(new)
        db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_argument('NAME', help='name of new operating system')
