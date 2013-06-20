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
import itertools

from pyfaf.rpm import store_rpm_deps
from pyfaf.repos import repo_types
from pyfaf.actions import Action
from pyfaf.storage.opsys import Arch, Repo, Build, BuildArch, Package
from pyfaf.queries import get_arch_by_name
from pyfaf.decorators import retry


class RepoSync(Action):
    name = "reposync"

    def __init__(self):
        super(RepoSync, self).__init__()

    def run(self, cmdline, db):
        repo_instances = []

        for repo in db.session.query(Repo):
            if cmdline.NAME and repo.name not in cmdline.NAME:
                continue

            if not repo.type in repo_types:
                self.log_error("No plugin installed to handle repository type "
                               "{0}, skipping.".format(repo.type))
                continue

            if "$" in repo.url:  # parametrized
                self.log_info("Processing parametrized repo '{0}'"
                              .format(repo.name))

                if not repo.opsys_list:
                    self.log_error("Parametrized repository is not assigned"
                                   " with an operating system")
                    return 1

                if not repo.arch_list:
                    self.log_error("Parametrized repository is not assigned"
                                   " with an architecture")
                    return 1

                repo_instances += list(self._get_parametrized_variants(repo))
            else:
                repo_instance = repo_types[repo.type](repo.name, repo.url)
                repo_instances.append(repo_instance)

        architectures = map(lambda x: x.name, db.session.query(Arch))

        for repo_instance in repo_instances:
            self.log_info("Processing repository '{0}' URL: '{1}'"
                          .format(repo_instance.name, repo_instance.url))

            pkglist = repo_instance.list_packages(architectures)
            total = len(pkglist)

            self.log_info("Repository has '{0}' packages".format(total))

            for num, pkg in enumerate(pkglist):
                self.log_debug("Processing package {0} {1}/{2}"
                               .format(pkg["name"], num + 1, total))

                arch = get_arch_by_name(db, pkg["arch"])
                if not arch:
                    self.log_error("Architecture '{0}' not found, skipping"
                                   .format(pkg["arch"]))

                    continue

                build = (db.session.query(Build)
                         .filter(Build.base_package_name ==
                                 pkg["base_package_name"])
                         .filter(Build.version == pkg["version"])
                         .filter(Build.release == pkg["release"])
                         .filter(Build.epoch == pkg["epoch"])
                         .first())

                if not build:
                    self.log_debug("Adding build {0}-{1}".format(
                        pkg["base_package_name"], pkg["version"]))

                    build = Build()
                    build.base_package_name = pkg["base_package_name"]
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

                    # Catching too general exception Exception
                    # pylint: disable-msg=W0703
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
                    # pylint: enable-msg=W0703

                    res = True
                    if pkg["type"] == "rpm":
                        res = store_rpm_deps(db, package, repo.nogpgcheck)

                    if not res:
                        self.log_error("Post-processing failed, skipping")
                        db.session.delete(package)
                        db.session.flush()
                        continue

                else:
                    self.log_debug("Known package {0}".format(pkg["filename"]))

    @retry(3, delay=5, backoff=3, verbose=True)
    def _download(self, obj, lob, url):
        pipe = urllib2.urlopen(url)
        obj.save_lob(lob, pipe.fp, truncate=True, binary=True)
        pipe.close()

    def _get_parametrized_variants(self, repo):
        """
        Generate a repo instance for each (OpSysRelease x Arch) combination
        that `repo` is associated with.
        """

        urls = set()

        for opsys in repo.opsys_list:
            active = opsys.active_releases
            if not active:
                self.log_warn("Operating system '{0}' assigned with"
                              " this repository has no active releases,"
                              " skipping".format(opsys))

            assigned = itertools.product(active,
                                         repo.arch_list)

            for releasever, arch in assigned:
                url = (repo.url.replace('$releasever', releasever.version)
                               .replace('$basearch', arch.name))

                if url in urls:
                    continue

                self.log_info("Adding variant '{0}'".format(url))
                urls.add(url)

                name = "{0}-{1}-{2}".format(repo.name, releasever.version,
                                            arch.name)

                yield repo_types[repo.type](name, url)

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("NAME", nargs="*", help="repository to sync")
