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

from typing import List, Optional

import configparser
import os

import pyfaf.repos
from pyfaf.actions import Action
from pyfaf.storage.opsys import Repo, Url


class RepoImport(Action):
    name = "repoimport"

    def __init__(self) -> None:
        super().__init__()
        self.repo_types = pyfaf.repos.repo_types

    def import_repo(self, fp, repo_type) -> Optional[List[Repo]]:
        """
        Parse open .repo file `fp` and return
        list of Repo instances.

        Section name is used as repository name,
        baseurl (required) and gpgcheck are stored.
        """

        parser = configparser.SafeConfigParser()
        try:
            parser.readfp(fp) #pylint: disable=deprecated-method
        except configparser.Error as exc:
            self.log_error("Exception while parsing repository file: "
                           "'{0}'".format(exc))
            return None

        result = []
        for section in parser.sections():
            new = Repo()
            new.name = section
            new.type = repo_type
            if not parser.has_option(section, "baseurl"):
                self.log_error("Repo '{0}' is missing required"
                               " option 'baseurl'".format(section))
                return None

            new_url = Url()
            new_url.url = parser.get(section, "baseurl")
            new.url_list = [new_url]

            if parser.has_option(section, "gpgcheck"):
                new.nogpgcheck = parser.getint(section, "gpgcheck") == 0

            result.append(new)

        return result

    def run(self, cmdline, db) -> int:
        if not os.path.isfile(cmdline.FILE):
            self.log_error("File '{0}' not found".format(cmdline.FILE))
            return 1

        if not os.access(cmdline.FILE, os.R_OK):
            self.log_error("File '{0}' not readable".format(cmdline.FILE))
            return 1

        if cmdline.TYPE not in ["dnf"]:
            self.log_error("Import of repository type '{0}' is not"
                           " supported".format(cmdline.TYPE))
            return 1

        with open(cmdline.FILE) as fp:
            repos = self.import_repo(fp, cmdline.TYPE)

        if not repos:
            return 1

        for repo in repos:
            dbrepo = (db.session.query(Repo)
                      .filter(Repo.name == repo.name)
                      .first())

            if dbrepo:
                self.log_error("Repository '{0}' already defined"
                               .format(repo.name))
                return 1

            self.log_info("Adding repository '{0}' {1}"
                          .format(repo.name, [url.url for url in repo.url_list]))

            db.session.add(repo)

        db.session.flush()
        return 0

    def tweak_cmdline_parser(self, parser) -> None:
        parser.add_repo_type(choices=self.repo_types, required=True, positional=True,
                             helpstr="type of the repository")
        parser.add_file(helpstr="repository file")
