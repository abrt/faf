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
from pyfaf.utils.format import as_table


class RepoList(Action):
    name = "repolist"


    def run(self, cmdline, db):
        if cmdline.detailed:
            data = []
            header = ["Name", "Type", "URL", "Nice name", "GPG check", "OS", "OS release", "Architecture"]
            for repo in db.session.query(Repo):
                data.append((repo.name, repo.type, repo.url_list[0].url,
                             repo.nice_name or "", str(not repo.nogpgcheck),
                             repo.opsys_list[0] if repo.opsys_list else "",
                             repo.opsysrelease_list[0] if repo.opsysrelease_list else "",
                             repo.arch_list[0] if repo.arch_list else ""))
                for i in range(1, len(max([repo.url_list,
                                           repo.opsys_list,
                                           repo.opsysrelease_list,
                                           repo.arch_list],
                                          key=len))):
                    data.append(("",
                                 "",
                                 repo.url_list[i].url if len(repo.url_list) > i else "",
                                 "",
                                 "",
                                 repo.opsys_list[i] if len(repo.opsys_list) > i else "",
                                 repo.opsysrelease_list[i] if len(repo.opsysrelease_list) > i else "",
                                 repo.arch_list[i] if len(repo.arch_list) > i else ""))

            print(as_table(header, data, margin=2))
        else:
            for repo in db.session.query(Repo):
                print(repo.name)

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--detailed", action="store_true",
                            help="detailed view")
