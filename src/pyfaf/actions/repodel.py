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
from pyfaf.queries import get_repos_by_wildcards
from pyfaf.storage.opsys import Repo


class RepoDel(Action):
    name = "repodel"


    def run(self, cmdline, db):
        if not cmdline.REPO and not cmdline.all:
            self.log_error("No repositories specified")
            return 1

        repos = []

        if cmdline.all or '*' in cmdline.REPO:
            repos.extend(db.session.query(Repo).all())
        else:
            repos.extend(get_repos_by_wildcards(db, cmdline.REPO))

        if repos:
            repos = sorted(list(set(repos)), key=lambda x: x.name)
            for repo in repos:
                for url in repo.url_list:
                    db.session.delete(url)

                self.log_info("Removing repository '{0}'".format(repo))

                db.session.delete(repo)

            db.session.flush()
        else:
            self.log_warn("No matching repositories found")
            return 1

        return 0


    def tweak_cmdline_parser(self, parser):
        parser.add_repo(multiple=True, helpstr="name of the repository to delete")
        parser.add_argument("-a", "--all", action="store_true", default=False, help="delete all repositories")
