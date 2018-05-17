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
from pyfaf.storage.opsys import (Repo, Build, BuildArch, Package, OpSys,
                                 BuildOpSysReleaseArch, OpSysRelease, Arch)
from pyfaf.queries import get_archs
from pyfaf.utils.decorators import retry

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

            if repo.opsys_list:  # parametrized
                self.log_info("Processing parametrized repo '{0}'"
                              .format(repo.name))

                if not repo.arch_list:
                    self.log_error("Parametrized repository is not assigned"
                                   " with an architecture, skipping")
                    continue
                try:
                    repo_instances += list(self._get_parametrized_variants(repo))
                except:
                    self.log_error("No valid mirror for repository '{0}', skipping"
                                   .format(repo.name))
                    continue


            elif repo.opsysrelease_list:
                self.log_info("Processing repo '{0}' assigned with OpSysRelease"
                              .format(repo.name))

                if not repo.arch_list:
                    self.log_error("OpSysRelease repository is not assigned"
                                   " with an architecture, skipping")
                    continue
                try:
                    repo_instances += list(self._get_opsysrelease_variants(repo))
                except:
                    self.log_error("No valid mirror for repository '{0}', skipping"
                                   .format(repo.name))
                    continue

            else:
                if any('$' in url.url for url in repo.url_list):
                    self.log_error("No operating system assigned to"
                                   "parametrized repo '{0}', skipping".format(repo.name))
                    continue
                for arch in repo.arch_list:
                    try:
                        repo_instance = {
                            'instance' : repo_types[repo.type](
                            	   repo.name,
                                [url.url for url in repo.url_list]),
                            'opsys' : None,
                            'release' : None,
                            'arch' : arch.name}
                        repo_instances.append(repo_instance)
                    except:
                        self.log_error("No valid mirror for repository '{0}', skipping"
                                       .format(repo.name))
                        continue

        cmdline.name_prefix = cmdline.name_prefix.lower()
        architectures = dict((x.name, x) for x in get_archs(db))
        for repo_instance in repo_instances:
            self.log_info("Processing repository '{0}' URL: '{1}'"
                          .format(repo_instance['instance'].name,
                                  repo_instance['instance'].urls))

            pkglist = \
                repo_instance['instance'].list_packages(list(architectures.keys()))
            total = len(pkglist)

            self.log_info("Repository has '{0}' packages".format(total))

            for num, pkg in enumerate(pkglist):
                self.log_debug("[{0} / {1}] Processing package {2}"
                               .format(num + 1, total, pkg["name"]))

                if not pkg["name"].lower().startswith(cmdline.name_prefix):
                    self.log_debug("Skipped package {0}"
                                   .format(pkg["name"]))
                    continue
                arch = architectures.get(pkg["arch"], None)
                if not arch:
                    self.log_error("Architecture '{0}' not found, skipping"
                                   .format(pkg["arch"]))

                    continue

                repo_arch = architectures.get(repo_instance["arch"], None)
                if not repo_arch:
                    self.log_error("Architecture '{0}' not found, skipping"
                                   .format(repo_instance["arch"]))

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
                    db.session.flush()

                build_arch = (db.session.query(BuildArch)
                              .filter(BuildArch.build_id == build.id)
                              .filter(BuildArch.arch_id == arch.id)
                              .first())

                if not build_arch:
                    build_arch = BuildArch()
                    build_arch.build = build
                    build_arch.arch = arch

                    db.session.add(build_arch)
                    db.session.flush()

                build_opsysrelease_arch = (
                    db.session.query(BuildOpSysReleaseArch)
                    .join(Build)
                    .join(OpSysRelease)
                    .join(Arch)
                    .filter(Build.id == build.id)
                    .filter(OpSys.name == repo_instance['opsys'])
                    .filter(OpSysRelease.version == repo_instance['release'])
                    .filter(Arch.name == repo_instance['arch'])
                    .first())

                if not build_opsysrelease_arch and repo_instance['release'] and repo_instance['opsys']:
                    self.log_info("Adding link between build {0}-{1} "
                                  "operating system '{2}', release '{3} and "
                                  "architecture {4}".format(pkg["base_package_name"],
                                                            pkg["version"], repo_instance['opsys'],
                                                            repo_instance['release'], repo_instance['arch']))

                    opsysrelease = (
                        db.session.query(OpSysRelease)
                        .filter(OpSys.name == repo_instance['opsys'])
                        .filter(OpSysRelease.version == repo_instance['release'])
                        .first())

                    bosra = BuildOpSysReleaseArch()
                    bosra.build = build
                    bosra.opsysrelease = opsysrelease
                    bosra.arch = repo_arch

                    db.session.add(bosra)
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

                    if cmdline.no_download_rpm:
                        continue

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

                    if cmdline.no_store_rpm:
                        try:
                            package.del_lob("package")
                            self.log_info("Package deleted.")
                        except Exception as exc:
                            self.log_error("Error deleting the RPM file.")

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
                url_mirrors = []
                for url in repo.url_list:
                    url = (url.url.replace('$releasever', releasever.version)
                           .replace('$basearch', arch.name))

                    if url not in urls:
                        url_mirror.append(url)

                    self.log_info("Adding variant '{0}'".format(url))
                    urls.add(url)

                name = "{0}-{1}-{2}".format(repo.name, releasever.version,
                                            arch.name)

                yield {'instance' : repo_types[repo.type](name, url_mirrors),
                       'opsys' : releasever.opsys.name,
                       'release' : releasever.version,
                       'arch' : arch.name}

    def _get_opsysrelease_variants(self, repo):
        """
        Generate a repo instance for each (OpSysRelease x Arch) combination
        that `repo` is associated with.
        """

        assigned = itertools.product(repo.opsysrelease_list, repo.arch_list)
        for opsysrelease, arch in assigned:
            name = "{0}-{1}-{2}".format(repo.name, opsysrelease.version,
                                        arch.name)
            yield {'instance' : repo_types[repo.type](repo.name,
                                                      [url.url for url in repo.url_list]),
                   'opsys' : opsysrelease.opsys.name,
                   'release' : opsysrelease.version,
                   'arch' : arch.name}



    def tweak_cmdline_parser(self, parser):
        parser.add_argument("NAME", nargs="*", help="repository to sync")
        parser.add_argument("--no-download-rpm", action="store_true",
                            help="Don't download the RPM. Cannot create "
                                 "dependencies.")
        parser.add_argument("--no-store-rpm", action="store_true",
                            help="Download the RPM but delete it after "
                                 "processing dependencies.")
        parser.add_argument("--name-prefix", default="",
                            help="Process only packages whose name "
                                 "starts with the prefix")
