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

import os

from pyfaf.repos import Repo
from pyfaf.proc import safe_popen
from pyfaf.parse import parse_nvra


class Yum(Repo):
    """
    A common interface to yum repositories. All yum repos
    should use this class and just differ in URL.
    """

    def __init__(self, name, url):
        """
        Following `url` schemes are supported:
        http://, ftp://, file:// (used if full
        path is passed).
        """

        self.name = name

        self.url = url

    def list_packages(self):
        """
        Return list of packages present in this repository.

        Returns dictionaries containing name, epoch, version,
        release, arch, srpm_name, type, filename, url items.
        """

        query = "%{name}|%{epoch}|%{version}|%{release}|%{arch}|%{sourcerpm}"

        proc = safe_popen("repoquery",
                          "-q", "-a",
                          "--queryformat={0}".format(query),
                          "--repofrompath={0},{1}".format(self.name, self.url),
                          "--repoid={0}".format(self.name))
        result = []

        if proc:
            for line in proc.stdout.splitlines():
                pkg_data = line.split("|")
                pkg = dict(name=pkg_data[0],
                           epoch=int(pkg_data[1]),
                           version=pkg_data[2],
                           release=pkg_data[3],
                           arch=pkg_data[4])

                pkg["filename"] = "{0}-{1}-{2}.{3}.rpm".format(
                    pkg["name"], pkg["version"], pkg["release"], pkg["arch"])
                pkg["type"] = "rpm"

                pkg["srpm_name"] = parse_nvra(pkg_data[5])["name"]
                pkg["url"] = os.path.join(self.url, pkg["filename"])

                result.append(pkg)

        return result
