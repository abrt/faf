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

import urllib2

from pyfaf.rpm import store_rpm_deps
from pyfaf.repos import repo_types
from pyfaf.actions import Action
from pyfaf.storage.opsys import Repo, Build, BuildArch, Package
from pyfaf.queries import get_arch_by_name
from pyfaf.decorators import retry


class RepoSync(Action):
    name = "reposync"

    def __init__(self):
        Action.__init__(self)

    def run(self, cmdline, db):
        for repo in db.session.query(Repo):
            if not repo.type in repo_types:
                self.log_error("No plugin installed to handle repository type {0}"
                               ", skipping.".format(repo.type))
                continue

            repo_instance = repo_types[repo.type](repo.name, repo.url)

            for pkg in repo_instance.list_packages():

                arch = get_arch_by_name(db, pkg["arch"])
                if not arch:
                    self.log_error("Architecture '{0}' not found, skipping"
                                   .format(pkg["arch"]))

                    continue

                build = (db.session.query(Build)
                         .filter(Build.srpm_name == pkg["srpm_name"])
                         .filter(Build.version == pkg["version"])
                         .filter(Build.release == pkg["release"])
                         .filter(Build.epoch == pkg["epoch"])
                         .first())

                if not build:
                    self.log_debug("Adding build {0}-{1}".format(
                        pkg["srpm_name"], pkg["version"]))

                    build = Build()
                    build.srpm_name = pkg["srpm_name"]
                    build.version = pkg["version"]
                    build.release = pkg["release"]
                    build.epoch = pkg["epoch"]

                    db.session.add(build)

                    build_arch = BuildArch()
                    build_arch.build = build
                    build_arch.arch = arch

                    db.session.add(build_arch)
                    db.session.flush()

                package = (db.session.query(Package)
                           .filter(Package.name == pkg["name"])
                           .filter(Package.pkgtype == pkg["type"])
                           .filter(Package.build == build)
                           .filter(Package.arch == arch)
                           .first())

                if not package:
                    self.log_info("Adding package {0}".format(pkg["filename"]))

                    package = Package()
                    package.name = pkg["name"]
                    package.pkgtype = pkg["type"]
                    package.arch = arch
                    package.build = build

                    db.session.add(package)
                    db.session.flush()

                    try:
                        self.log_info("Downloading {0}".format(pkg["url"]))
                        self._download(package, "package", pkg["url"])
                    except Exception as exc:
                        self.log_error("Exception ({0}) after multiple attemps"
                                       " while trying to download {1},"
                                       " skipping.".format(exc, pkg["url"]))

                        db.session.delete(package)
                        db.session.flush()
                        continue

                    if pkg["type"] == "rpm":
                        store_rpm_deps(db, package)

                else:
                    self.log_debug("Known package {0}".format(pkg["filename"]))

    @retry(3, delay=5, backoff=3, verbose=True)
    def _download(self, obj, lob, url):
        pipe = urllib2.urlopen(url)
        obj.save_lob(lob, pipe.fp, truncate=True, binary=True)
        pipe.close()
