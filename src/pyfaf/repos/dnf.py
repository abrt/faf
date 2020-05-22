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

from __future__ import absolute_import

import os
from urllib import request
import dnf

from pyfaf.common import get_temp_dir
from pyfaf.repos import Repo


class Dnf(Repo):
    """
    A common interface to dnf repositories. All dnf repos
    should use this class and just differ in URL.
    """

    name = "dnf"

    def __init__(self, name, *urls):
        """
        Following `url` schemes are supported:
        http://, ftp://, file:// (used if full
        path is passed).
        """

        super(Dnf, self).__init__()

        self.dnf_root = None
        self.load_config_to_self("dnf_root", ["dnf.root"], "/")
        self.name = name
        self.urls = urls
        self.dnf_base = dnf.Base()
        self.dnf_base.conf.debuglevel = 0
        self.dnf_base.conf.installroot = self.dnf_root
        self.dnf_base.conf.cachedir = get_temp_dir("dnf")
        self.dnf_base.read_all_repos()
        self.dnf_base.repos.all().disable()

        # Add repositories
        for i, url in enumerate(urls):
            if isinstance(url, str):
                if url.startswith("/"):
                    url = "file://{0}".format(url)
                # call str() on url, because if url is unicode,
                # list_packages will crash on el6
                self.dnf_base.repos.add_new_repo("faf_{0}-{1}".format(self.name, i), self.dnf_base.conf,
                                                 baseurl=[str(url)], skip_if_unavailable=True)
            else:
                for url_single in url:
                    if url_single.startswith("/"):
                        url_single = "file://{0}".format(url_single)
                    try:
                        request.urlopen(os.path.join(url_single, "repodata/repomd.xml"))
                        self.dnf_base.repos.add_new_repo("faf_{0}-{1}".format(self.name, i), self.dnf_base.conf,
                                                         baseurl=[url_single], skip_if_unavailable=True)
                        break
                    except: # pylint: disable=bare-except
                        pass
                else:
                    self.log_error("No mirrors available")
                    raise NameError('NoMirrorsAvailable')

            # A sack is required by marking methods and dependency resolving
            try:
                self.dnf_base.fill_sack()
            except dnf.exceptions.RepoError:
                self.log_error("Repo error")

    def list_packages(self, architectures):
        """
        Return list of packages present in this repository.

        Returns dictionaries containing name, epoch, version,
        release, arch, srpm_name, type, filename, url items.
        """

        result = []
        try:
            packagelist = self.dnf_base.sack.query().filterm(arch=architectures)
        except dnf.exceptions.RepoError as err:
            self.log_error("Repository listing failed: '{0}'".format(err))
            return result

        pkgs = packagelist.available()

        for package in pkgs:
            base_name = package.name
            for suffix in (package.DEBUGINFO_SUFFIX, package.DEBUGSOURCE_SUFFIX):
                if package.name.endswith(suffix):
                    base_name = package.name[:-len(suffix)]
                    break
            pkg = dict(name=package.name,
                       base_package_name=base_name,
                       epoch=package.epoch,
                       version=package.version,
                       release=package.release,
                       arch=package.arch,
                       filename=os.path.basename(package.location))
            pkg["url"] = os.path.join(package.repo.baseurl[0], package.location)

            pkg["type"] = "rpm"

            result.append(pkg)

        self.dnf_base.close()

        return result
