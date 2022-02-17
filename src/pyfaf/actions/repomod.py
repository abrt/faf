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
from pyfaf.queries import get_repos_by_wildcards
from pyfaf.storage.opsys import Repo, Url, UrlRepo


class RepoMod(Action):
    name = "repomod"

    def __init__(self) -> None:
        super().__init__()
        self.repo_types = pyfaf.repos.repo_types

    def run(self, cmdline, db) -> int:
        if not cmdline.REPO and not cmdline.all:
            self.log_error("No repositories specified")
            return 1

        repos = []

        for pattern in cmdline.REPO:
            wildcard_used = any(c in pattern for c in ["?", "*"])
            if wildcard_used:
                break

        if (len(cmdline.REPO) > 1 or cmdline.all or wildcard_used) and (cmdline.name or cmdline.nice_name):
            self.log_error("Can't assign the same name to multiple repositories")
            return 1


        if cmdline.all or "*" in cmdline.REPO:
            repos.extend(db.session.query(Repo).all())

        else:
            repos.extend(get_repos_by_wildcards(db, cmdline.REPO))

        if repos:
            repos = sorted(list(set(repos)), key=lambda x: x.name)

        else:
            self.log_warn("No matching repositories found")
            return 1

        if cmdline.name:
            dbrepo = (db.session.query(Repo)
                      .filter(Repo.name == cmdline.name)
                      .first())
            if dbrepo:
                self.log_error("Unable to rename repository '{0}' to '{1}',"
                               " the latter is already defined"
                               .format(cmdline.REPO[0], dbrepo.name))
                return 1

        options = ["name", "type", "nice_name"]
        for repo in repos:
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
                    self.log_warn("Url is not assigned to {0} repository."
                                  " Use repoinfo to find out more about repository.".format(repo.name))
                    continue

                repo.url_list.remove(url)
                db.session.delete(url)

            if cmdline.gpgcheck == "enable":
                repo.nogpgcheck = False

            if cmdline.gpgcheck == "disable":
                repo.nogpgcheck = True

            db.session.add(repo)
            self.log_info("Repository {0} modified".format(repo.name))

        db.session.flush()

        return 0

    def tweak_cmdline_parser(self, parser) -> None:
        parser.add_repo(multiple=True, helpstr="current name of the repository")
        parser.add_argument("--name", help="new name of the repository")
        parser.add_repo_type(choices=self.repo_types, helpstr="new type of the repository")
        parser.add_argument("--add-url", metavar="URL", help="new repository URL")
        parser.add_argument("--remove-url", metavar="URL", help="repository URL to delete")
        parser.add_argument("--nice-name", help="new human readable name")
        parser.add_gpgcheck_toggle(helpstr="toggle GPG check requirement for this repository")
        parser.add_argument("-a", "--all", action="store_true", default=False, help="apply to all repositories; "
                            "do not use with --name or --nice-name")
