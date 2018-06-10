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
            header = ["Name", "Type", "URL", "Nice name"]
            for repo in db.session.query(Repo):
                data.append((repo.name, repo.type, repo.url_list[0].url,
                             repo.nice_name or ""))
                for url in repo.url_list[1:]:
                    data.append(("", "", url.url, ""))

            print(as_table(header, data, margin=2))
        else:
            for repo in db.session.query(Repo):
                print(repo.name)

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--detailed", action="store_true",
                            help="detailed view")
