# Copyright (C) 2017  ABRT Team
# Copyright (C) 2017  Red Hat, Inc.
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

import os
import urllib2
import urlparse
from pyfaf.actions import Action
from pyfaf.storage.opsys import Repo


class CheckRepo(Action):
    name = "check-repo"

    def __init__(self):
        super(CheckRepo, self).__init__()

    def check_repo(self, repo):
        # Test available mirror
        for mirror in repo.url_list:
            if mirror.url.startswith("http:") or \
               mirror.url.startswith("https:") or \
               mirror.url.startswith("ftp:"):

                repodata = urlparse.urljoin(mirror.url, 'repodata')
                try:
                    urllib2.urlopen(repodata)
                    break
                except urllib2.URLError:
                    pass
            else:
                if mirror.url.startswith("file://"):
                    mirror.url = mirror.url[7:]
                self.log_error(mirror.url)
                if os.path.exists(os.path.join(mirror.url, 'repodata')):
                    break
        else:
            print("'{0}' does not have a valid url.".format(repo.name))
            return 1

        # Test if assigned
        if not repo.opsysrelease_list:
            print("'{0}' is not assigned with OpSys release.".format(repo.name))
            return 1
        if not repo.arch_list:
            print("'{0}' is not assigned with architecture.".format(repo.name))
            return 1

        return 0


    def run(self, cmdline, db):
        repos = []
        for reponame in cmdline.REPONAME:
            repo = (db.session.query(Repo)
                    .filter(Repo.name == reponame)
                    .first())
            if repo:
                repos.append(repo)
            else:
                print("Repository '{0}' does not exists".format(reponame))

        if not cmdline.REPONAME:
            for repo in db.session.query(Repo):
                repos.append(repo)

        problems = 0
        for repo in repos:
            problems += self.check_repo(repo)

        if problems:
            print("There are some problems, please resolve them")
        else:
            print("Everything is OK!")

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("REPONAME",
                            help="Repo name to be checked", nargs='*')
