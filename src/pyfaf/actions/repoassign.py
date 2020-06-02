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

from typing import Tuple, Union

from pyfaf.actions import Action
from pyfaf.storage.opsys import Repo
from pyfaf.queries import get_opsys_by_name, get_arch_by_name, get_osrelease


class RepoAssign(Action):
    name = "repoassign"


    def run(self, cmdline, db) -> int:
        repo = (db.session.query(Repo)
                .filter(Repo.name == cmdline.REPO)
                .first())

        if not repo:
            self.log_error("Repository '{0}' not found"
                           .format(cmdline.REPO))
            return 1

        arch_list = []
        opsys_list = []
        opsysrelease_list = []

        for item_name in cmdline.OPSYS + cmdline.ARCH:
            pos_name, pos_release = self._parser_osrelease(item_name)
            opsysrelease = get_osrelease(db, pos_name, pos_release)
            opsys = get_opsys_by_name(db, item_name)
            arch = get_arch_by_name(db, item_name)

            if not (opsys or arch or opsysrelease):
                #If name is rhel we will search Red Hat Enterprise Linux
                if item_name == "rhel":
                    item_name = "Red Hat Enterprise Linux"
                    opsys = get_opsys_by_name(db, item_name)

                    if not opsys:
                        self.log_error("Item '{0}' not found"
                                       .format(item_name))
                        return 1

                elif pos_name == "rhel":
                    pos_name = "Red Hat Enterprise Linux"
                    opsysrelease = get_osrelease(db, pos_name, pos_release)

                    if not opsysrelease:
                        self.log_error("Item '{0}' not found"
                                       .format(item_name))
                        return 1

                else:
                    self.log_error("Item '{0}' not found"
                                   .format(item_name))
                    return 1

            if opsys:
                opsys_list.append(opsys)
            elif opsysrelease:
                opsysrelease_list.append(opsysrelease)
            else:
                arch_list.append(arch)

        # test if url type correspond with type of repo
        if any('$' in url.url for url in repo.url_list) and opsysrelease_list:
            self.log_error("Assigning operating system with release to "
                           "parametrized repo. Assign only operating system.")
            return 1

        if any('$' not in url.url for url in repo.url_list) and opsys_list:
            self.log_error("Assigning operating system without release to "
                           "non - parametrized repo. Assign operating system"
                           " with release.")
            return 1

        repo.opsys_list += opsys_list
        repo.opsysrelease_list += opsysrelease_list
        repo.arch_list += arch_list

        db.session.flush()

        self.log_info("Assigned '{0}' to {1} operating system(s)"
                      ", {2} operating systems with release(s) and {3} architecture(s)"
                      .format(repo.name, len(opsys_list), len(opsysrelease_list),
                              (len(arch_list))))

        return 0


    def _parser_osrelease(self, osrelease) -> Union[Tuple[str, str], Tuple[None, None]]:
        if " " not in osrelease: #must consist from at least two words
            return (None, None)

        splitpos = osrelease.rfind(" ")
        name = osrelease[:splitpos]
        release = osrelease[splitpos+1:]
        return (name, release)


    def tweak_cmdline_parser(self, parser) -> None:
        parser.add_repo(helpstr="name of the repository")
        parser.add_opsys(multiple=True, positional=True, with_rel=True,
                         helpstr="operating system with release")
        parser.add_arch(multiple=True, positional=True, helpstr="architecture")
