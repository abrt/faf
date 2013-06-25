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
import yum

from pyfaf.repos import Repo
from pyfaf.local import var


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

        super(Yum, self).__init__()

        self.name = name

        self.url = url
        if self.url.startswith("/"):
            self.url = "file://{0}".format(self.url)

        self.yum_base = yum.YumBase()
        self.yum_base.doConfigSetup(init_plugins=False, debuglevel=0)
        self.yum_base.conf.cachedir = os.path.join(var, 'tmp/faf/yum')
        self.yum_base.disablePlugins()
        self.yum_base.repos.disableRepo("*")
        # call str() on self.url, because if self.url is unicode,
        # list_packages will crash on el6
        self.yum_base.add_enable_repo("faf_{0}".format(self.name),
                                      baseurls=[str(self.url)])

    def list_packages(self, architectures):
        """
        Return list of packages present in this repository.

        Returns dictionaries containing name, epoch, version,
        release, arch, srpm_name, type, filename, url items.
        """

        self.yum_base.arch.archlist = architectures

        result = []
        try:
            packagelist = self.yum_base.doPackageLists('all')
        except yum.Errors.RepoError as err:
            self.log_error("Repository listing failed: '{0}'".format(err))
            return result

        for package in packagelist.available + packagelist.old_available:
            pkg = dict(name=package.name,
                       base_package_name=package.base_package_name,
                       epoch=package.epoch,
                       version=package.version,
                       release=package.release,
                       arch=package.arch,
                       url=package.remote_url,
                       filename=os.path.basename(package.remote_url))

            pkg["type"] = "rpm"

            result.append(pkg)

        return result
