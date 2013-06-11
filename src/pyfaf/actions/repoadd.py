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

import pyfaf.repos
from pyfaf.actions import Action
from pyfaf.storage.opsys import Repo


class RepoAdd(Action):
    name = "repoadd"

    def __init__(self):
        super(RepoAdd, self).__init__()
        self.repo_types = pyfaf.repos.repo_types

    def run(self, cmdline, db):
        repo = (db.session.query(Repo)
                          .filter(Repo.name == cmdline.NAME)
                          .first())

        if repo:
            self.log_error("Repository '{0}' already defined"
                           .format(cmdline.NAME))
            return 1

        self.log_info("Adding repository '{0}' ({1})"
                      .format(cmdline.NAME, cmdline.URL))

        new = Repo()
        new.name = cmdline.NAME
        new.type = cmdline.TYPE
        new.url = cmdline.URL
        if cmdline.nice_name:
            new.nice_name = cmdline.nice_name

        new.nogpgcheck = cmdline.nogpgcheck

        db.session.add(new)
        db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_argument('NAME', help='name of this repository')
        parser.add_argument('TYPE', choices=self.repo_types,
                            help='type of the repository')
        parser.add_argument('URL', help='repository/buildsystem API URL')
        parser.add_argument('--nice-name', help='human readable name')
        parser.add_argument('--nogpgcheck', action='store_true',
                            help='disable gpg check for this repository')
