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
from pyfaf.storage.opsys import Repo
from pyfaf.queries import get_opsys_by_name, get_arch_by_name


class RepoAssign(Action):
    name = "repoassign"

    def __init__(self):
        super(RepoAssign, self).__init__()

    def run(self, cmdline, db):
        repo = (db.session.query(Repo)
                          .filter(Repo.name == cmdline.NAME)
                          .first())

        if not repo:
            self.log_error("Repository '{0}' not found"
                           .format(cmdline.NAME))
            return 1

        arch_list = []
        opsys_list = []

        for item_name in cmdline.OPSYS + cmdline.ARCH:
            opsys = get_opsys_by_name(db, item_name)
            arch = get_arch_by_name(db, item_name)

            if not (opsys or arch):
                self.log_error("Item '{0}' not found"
                               .format(item_name))

                return 1

            if opsys:
                opsys_list.append(opsys)
            else:
                arch_list.append(arch)

        repo.opsys_list += opsys_list
        repo.arch_list += arch_list

        db.session.flush()

        self.log_info("Assigned {0} operating system(s) and {1} architecture(s)"
                      .format(len(opsys_list), len(arch_list)))

    def tweak_cmdline_parser(self, parser):
        parser.add_argument('NAME', help='name of the repository')
        parser.add_argument('OPSYS', nargs='*',
                            help='operating system')
        parser.add_argument('ARCH', nargs='*',
                            help='architecture')
