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


class RepoDel(Action):
    name = "repodel"


    def run(self, cmdline, db):
        repo = (db.session.query(Repo)
                .filter(Repo.name == cmdline.NAME)
                .first())

        if not repo:
            self.log_error("Repository '{0}' not found"
                           .format(cmdline.NAME))
            return 1

        for url in repo.url_list:
            db.session.delete(url)

        self.log_info("Removing repository '{0}'".format(cmdline.NAME))

        db.session.delete(repo)
        db.session.flush()

        return 0

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("NAME", help="name of the repository to delete")
