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
import urllib2
import yum

from pyfaf.common import get_temp_dir
from pyfaf.repos import Repo
import six


class Yum(Repo):
    """
    A common interface to yum repositories. All yum repos
    should use this class and just differ in URL.
    """

    name = "yum"

    def __init__(self, name, *urls):
        """
        Following `url` schemes are supported:
        http://, ftp://, file:// (used if full
        path is passed).
        """

        super(Yum, self).__init__()

        self.load_config_to_self("yum_root", ["yum.root"], "/")
        self.name = name
        self.urls = urls
        self.yum_base = yum.YumBase()
        self.yum_base.doConfigSetup(init_plugins=False, debuglevel=0,
                                    root=self.yum_root)
        self.yum_base.conf.cachedir = get_temp_dir("yum")
        self.yum_base.disablePlugins()
        self.yum_base.repos.disableRepo("*")

        for i, url in enumerate(urls):
            if isinstance(url, six.string_types):
                if url.startswith("/"):
                    url = "file://{0}".format(url)
                # call str() on url, because if url is unicode,
                # list_packages will crash on el6
                self.yum_base.add_enable_repo("faf_{0}-{1}".format(self.name, i),
                                              baseurls=[str(url)])
            else:
                for url_single in url:
                    if url_single.startswith("/"):
                        url_single = "file://{0}".format(url_single)
                    try:
                        urllib2.urlopen(os.path.join(url_single, "repodata/repomd.xml"))
                        self.yum_base.add_enable_repo("faf-{0}-{1}".format(self.name, i),
                                                      baseurls=[url_single])
                        break
                    except:
                        pass
                else:
                    self.log_error("No mirrors available")
                    raise NameError('NoMirrorsAvailable')


    def list_packages(self, architectures):
        """
        Return list of packages present in this repository.

        Returns dictionaries containing name, epoch, version,
        release, arch, srpm_name, type, filename, url items.
        """

        self.yum_base.arch.archlist = architectures

        result = []
        try:
            packagelist = self.yum_base.doPackageLists('all', showdups=True)
        except yum.Errors.RepoError as err:
            self.log_error("Repository listing failed: '{0}'".format(err))
            return result

        pkgs = (packagelist.available +
                packagelist.old_available +
                packagelist.reinstall_available)

        for package in pkgs:
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

        self.yum_base.closeRpmDB()
        self.yum_base.close()

        return result
