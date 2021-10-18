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
#
# vim: set makeprg=python3-flake8\ %

import errno
import gzip
import os
import time
import xml.sax
import zlib
from typing import Dict, List, Optional, Union
from urllib.error import HTTPError
from urllib.request import urlopen
from xml.sax import SAXException

from pyfaf.common import FafError
from pyfaf.utils import parse
from pyfaf.repos import Repo


class RepomdPrimaryLocationHandler(xml.sax.ContentHandler):
    def __init__(self) -> None:
        super().__init__()
        self._location = None
        self._searching = "data"

    def startElement(self, name, attrs) -> None:
        if self._searching is None or self._searching != name:
            return

        if name == "data" and attrs.get("type", "") == "primary":
            self._searching = "location"
        elif name == "location":
            self._location = attrs["href"]
            self._searching = None

    @property
    def primary_location(self) -> str:
        if self._location is None:
            raise FafError(
                "repomd.xml is missing data[@type='primary']/location@href")
        return self._location


class PrimaryHandler(xml.sax.ContentHandler):

    def __init__(self, baseurl) -> None:
        super().__init__()
        self._baseurl = baseurl
        self._current = None
        self._package = None
        self._result = []
        self._local_repo = baseurl[0] == '/'

    def startElement(self, name, attrs) -> None:
        if name == "package":
            if self._package is not None:
                raise FafError("Malformed primary.xml")

            self._package = {"type": "rpm"}
        elif name == "version":
            self._package["epoch"] = attrs["epoch"]
            self._package["version"] = attrs["ver"]
            self._package["release"] = attrs["rel"]
        elif name == "location":
            relativepath = attrs["href"]
            self._package["filename"] = os.path.basename(relativepath)
            url = os.path.join(self._baseurl, relativepath)
            if self._local_repo:
                self._package["url"] = "file://" + url
            else:
                self._package["url"] = url

        self._current = name

    def endElement(self, name) -> None:
        self._current = None

        if name == "rpm:sourcerpm":
            nvra = parse.parse_nvra(self._package["srpm"])
            self._package["base_package_name"] = nvra["name"]

        if name == "package":
            pkg = self._package
            self._package = None
            self._result.append(pkg)

    def characters(self, content) -> None:
        if self._current in ["name", "arch"]:
            self._package[self._current] = \
                    self._package.get(self._current, "") + content
        elif self._current == "rpm:sourcerpm":
            self._package["srpm"] = self._package.get("srpm", "") + content

    def packages(self) -> List[Dict[str, Union[str, int]]]:
        return self._result


class RpmMetadata(Repo):
    """
    An interface to createrepo/rpm metadata repositories. Whenever you are not
    able to use dnf (if dnf does not work on your system) you can use
    RpmMetadata repo which behaves like a dnf repository but it does not
    need dnf libraries because this repository parses repodata files
    on its own.
    """

    name = "rpmmetadata"

    cachedir: str
    cacheperiod: int

    def __init__(self, name, urls, *args) -> None:
        """
        Following `url` schemes are supported:
        http://, ftp://, file:// (used if full
        path is passed).
        """

        super().__init__()

        self.load_config_to_self("cachedir",
                                 ["rpmmetadata.cachedir"],
                                 "/var/tmp/faf-rpmmetadata")
        # Cache files for 1 hour by default
        self.load_config_to_self("cacheperiod",
                                 ["rpmmetadata.cacheperiod"],
                                 3600,
                                 int)

        self.name = name
        self.urls = urls

    def _setup_dirs(self, reponame) -> str:
        dirname = os.path.join(self.cachedir, self.name, reponame)
        try:
            os.makedirs(dirname)
        except OSError as ex:
            if ex.errno != 17:
                raise FafError("Cache directories error '{0}': {1}"
                               .format(self.cachedir, str(ex))) from ex
        return dirname

    def _get_repo_file_path(self, reponame: str, repourl: str, remote: str,
                            local: Optional[str] = None) -> str:
        url = os.path.join(repourl, remote)
        if url.startswith("file://"):
            return url[len("file://"):]
        if url.startswith("/"):
            return url

        if local is None:
            local = os.path.basename(remote)

        cachename = os.path.join(self.cachedir,
                                 self.name,
                                 reponame,
                                 local)

        last_modified: float = 0
        try:
            last_modified = os.path.getmtime(cachename)
        except OSError as ex:
            if errno.ENOENT != ex.errno:
                raise FafError("Cannot access cache: {0}".format(str(ex))) from ex

        # Check for cache expiration.
        if (last_modified + self.cacheperiod) <= time.time():
            try:
                cache_file = open(cachename, "wb")
            except Exception as ex:
                raise FafError("Creating cache file {0} filed with: {1}"
                               .format(cachename, str(ex))) from ex

            with cache_file:
                try:
                    with urlopen(url) as response:
                        cache_file.write(response.read())
                except HTTPError as ex:
                    raise FafError("Downloading failed: {0}"
                                    .format(str(ex))) from ex

        return cachename

    def _get_primary_file_path(self, reponame, repourl) -> str:
        self._setup_dirs(reponame)

        repomdfilename = self._get_repo_file_path(reponame,
                                                  repourl,
                                                  "repodata/repomd.xml")
        rplh = RepomdPrimaryLocationHandler()
        repomdparser = xml.sax.make_parser()
        repomdparser.setContentHandler(rplh)

        try:
            mdfp = open(repomdfilename, "r")
        except Exception as ex:
            raise FafError("Reading: {0}".format(str(ex))) from ex
        else:
            with mdfp:
                try:
                    repomdparser.parse(mdfp)
                except SAXException as ex:
                    # pylint: disable=raise-missing-from
                    raise FafError("Failed to parse repomd.xml: {0}"
                                   .format(str(ex)))

        return self._get_repo_file_path(reponame,
                                        repourl,
                                        rplh.primary_location)

    def _parse_primary_file(self, filename, repourl) -> List[Dict[str, Union[str, int]]]:
        primaryhandler = PrimaryHandler(repourl)
        primaryparser = xml.sax.make_parser()
        primaryparser.setContentHandler(primaryhandler)

        pfp = None
        try:
            # Cannot use 'with' statement because GzipFile does not support the
            # context manager protocol in some version of Python.
            if filename.endswith(".gz"):
                pfp = gzip.open(filename, "rb")
            else:
                # The handle is closed below in the 'finally' clause.
                pfp = open(filename, "r") # pylint: disable=consider-using-with
            primaryparser.parse(pfp)
        except (Exception, SAXException, zlib.error) as ex:
            raise FafError("Failed to parse primary.xml[.gz]: {0}"
                           .format(str(ex))) from ex
        finally:
            if pfp is not None:
                pfp.close()

        return primaryhandler.packages()

    def list_packages(self, architectures) -> List[Dict[str, Union[str, int]]]:
        """
        Return list of packages present in this repository.

        Returns dictionaries containing name, epoch, version,
        release, arch, srpm_name, type, filename, url items.
        """

        result = []
        for c, u in enumerate(self.urls):
            try:
                primaryfilename = self._get_primary_file_path(str(c), u)
                result += self._parse_primary_file(primaryfilename, u)
            except FafError as ex:
                self.log_error(
                    "Repository listing failed for '{0}'['{1}']: {2}"
                    .format(self.name, u, str(ex)))

        return result

    @property
    def cache_lifetime(self):
        return self.cacheperiod

    @cache_lifetime.setter
    def cache_lifetime(self, lifetime):
        self.cacheperiod = lifetime
