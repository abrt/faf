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
from pyfaf.queries import get_arch_by_name
from pyfaf.storage import Arch


class Init(Action):
    name = "init"

    archs = ["src", "noarch", "x86_64", "i386", "i486", "i586", "i686",
             "armv5tel", "armv7l", "armv7hl", "armv7hnl", "ppc", "ppc64",
             "s390", "s390x", "sparc", "sparc64", "ia64"]

    def __init__(self):
        super(Init, self).__init__()

    def run(self, cmdline, db):
        for arch in Init.archs:
            db_arch = get_arch_by_name(db, arch)
            if db_arch is not None:
                continue

            self.log_info("Adding architecture '{0}'".format(arch))
            new = Arch()
            new.name = arch
            db.session.add(new)

        db.session.flush()

    def tweak_cmdline_parser(self, parser):
        pass
