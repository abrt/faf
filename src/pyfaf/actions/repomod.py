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
from pyfaf.storage.opsys import Repo, Url, UrlRepo


class RepoMod(Action):
    name = "repomod"

    def __init__(self):
        super(RepoMod, self).__init__()
        self.repo_types = pyfaf.repos.repo_types

    def run(self, cmdline, db):
        repo = (db.session.query(Repo)
                .filter(Repo.name == cmdline.NAME)
                .first())

        if not repo:
            self.log_error("Repository '{0}' not found"
                           .format(cmdline.NAME))
            return 1

        if cmdline.name:
            dbrepo = (db.session.query(Repo)
                      .filter(Repo.name == cmdline.name)
                      .first())
            if dbrepo:
                self.log_error("Unable to rename repository '{0}' to '{1}',"
                               " the latter is already defined"
                               .format(repo.name, dbrepo.name))
                return 1

        options = ["name", "type", "nice_name"]
        for opt in options:
            if hasattr(cmdline, opt) and getattr(cmdline, opt):
                newval = getattr(cmdline, opt)
                self.log_info("Updating {0} on '{1}' to '{2}'"
                              .format(opt, repo.name, newval))
                setattr(repo, opt, newval)

        if cmdline.add_url:
            new_url = Url()
            new_url.url = getattr(cmdline, "add_url")
            repo.url_list.append(new_url)

        if cmdline.remove_url:
            url = (db.session.query(Url)
                   .join(UrlRepo)
                   .filter(Url.url == cmdline.remove_url)
                   .filter(UrlRepo.repo_id == repo.id)
                   .first())
            if not url:
                self.log_error("Url is not assigned to selected repository."
                               " Use repoinfo to find out more about repository.")
                return 1

            repo.url_list.remove(url)
            db.session.delete(url)

        if cmdline.gpgcheck:
            repo.nogpgcheck = False

        if cmdline.nogpgcheck:
            repo.nogpgcheck = True

        db.session.add(repo)
        db.session.flush()

        self.log_info("Repository modified")
        return 0

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("NAME", help="name of this repository")
        parser.add_argument("--name", help="new name of the repository")
        parser.add_argument("--type", choices=self.repo_types,
                            help="new type of the repository")
        parser.add_argument("--add-url", help="new repository URL")
        parser.add_argument("--remove-url", help="new repository URL")
        parser.add_argument("--nice-name", help="new human readable name")

        group = parser.add_mutually_exclusive_group()
        group.add_argument("--gpgcheck", action="store_true",
                           help="enable gpg check for this repository")
        group.add_argument("--nogpgcheck", action="store_true",
                           help="disable gpg check for this repository")
