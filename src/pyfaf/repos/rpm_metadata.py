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

import os
import time
import gzip
import zlib
import errno
import xml.sax
from xml.sax import SAXException
import pycurl

from pyfaf.utils import parse
from pyfaf.repos import Repo
from pyfaf.common import FafError


class RepomdPrimaryLocationHandler(xml.sax.ContentHandler):

    def __init__(self):
        self._location = None
        self._searching = "data"

    def startElement(self, name, attrs):
        if self._searching is None or self._searching != name:
            return

        if name == "data" and "primary" == attrs.get("type", ""):
            self._searching = "location"
        elif name == "location":
            self._location = attrs["href"]
            self._searching = None

    @property
    def primary_location(self):
        if self._location is None:
            raise FafError(
                "repomd.xml is missing data[@type='primary']/location@href")
        return self._location


class PrimaryHandler(xml.sax.ContentHandler):

    def __init__(self, baseurl):
        self._baseurl = baseurl
        self._current = None
        self._package = None
        self._result = []
        self._local_repo = baseurl[0] == '/'

    def startElement(self, name, attrs):
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

    def endElement(self, name):
        self._current = None

        if name == "rpm:sourcerpm":
            nvra = parse.parse_nvra(self._package["srpm"])
            self._package["base_package_name"] = nvra["name"]

        if name == "package":
            pkg = self._package
            self._package = None
            self._result.append(pkg)

    def characters(self, content):
        if self._current in ["name", "arch"]:
            self._package[self._current] = \
                    self._package.get(self._current, "") + content
        elif self._current == "rpm:sourcerpm":
            self._package["srpm"] = self._package.get("srpm", "") + content

    def packages(self):
        return self._result


class RpmMetadata(Repo):
    """
    An interface to createrepo/rpm metadata repositories. Whenever you are not
    able to use yum (if yum does not work on your system) you can use
    RpmMetadata repo which behaves like a yum repository but it does not need
    yum libraries because this repository parses repodata files on its own.
    """

    name = "rpmmetadata"

    def __init__(self, name, *urls):
        """
        Following `url` schemes are supported:
        http://, ftp://, file:// (used if full
        path is passed).
        """

        super(RpmMetadata, self).__init__()

        self.load_config_to_self("cachedir",
                                 ["rpmmetadata.cachedir"],
                                 "/var/tmp/faf-rpmmetadata")
        # Cache files for 1 hour by default
        self.load_config_to_self("cacheperiod",
                                 ["rpmmetadata.cacheperiod"],
                                 3600)
        self.cacheperiod = int(self.cacheperiod)

        self.name = name
        self.urls = urls

    def _setup_dirs(self, reponame):
        dirname = os.path.join(self.cachedir, self.name, reponame)
        try:
            os.makedirs(dirname)
        except OSError as ex:
            if ex.errno != 17:
                raise FafError("Cache directories error '{0}': {1}"
                               .format(self.cachedir, str(ex)))
        return dirname

    def _get_repo_file_path(self, reponame, repourl, remote, local=None):
        url = os.path.join(repourl, remote)
        if url.startswith("file://"):
            return url[len("file://"):]
        elif url.startswith("/"):
            return url

        if local is None:
            local = os.path.basename(remote)

        cachename = os.path.join(self.cachedir,
                                 self.name,
                                 reponame,
                                 local)

        mtime = 0
        try:
            mtime = os.path.getmtime(cachename)
        except OSError as ex:
            if errno.ENOENT != ex.errno:
                raise FafError("Cannot access cache: {0}".format(str(ex)))

        if (mtime + self.cacheperiod) <= time.time():
            curl = pycurl.Curl()
            curl.setopt(pycurl.URL, url.encode("ascii", "ignore"))

            try:
                fp = open(cachename, "wb")
            except Exception as ex:
                raise FafError("Creating cache file: {1}"
                               .format(cachename, str(ex)))
            else:
                with fp:
                    curl.setopt(pycurl.WRITEDATA, fp)
                    try:
                        curl.perform()
                    except pycurl.error as ex:
                        raise FafError("Downloading failed: {0}"
                                       .format(str(ex)))
                    finally:
                        curl.close()

        return cachename

    def _get_primary_file_path(self, reponame, repourl):
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
            raise FafError("Reading: {0}".format(str(ex)))
        else:
            with mdfp:
                try:
                    repomdparser.parse(mdfp)
                except SAXException as ex:
                    raise FafError("Failed to parse repomd.xml: {0}"
                                   .format(str(ex)))

        return self._get_repo_file_path(reponame,
                                        repourl,
                                        rplh.primary_location)

    def _parse_primary_file(self, filename, repourl):
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
                pfp = open(filename, "r")
            primaryparser.parse(pfp)
        except (Exception, SAXException, zlib.error) as ex:
            raise FafError("Failed to parse primary.xml[.gz]: {0}".format(
                str(ex)))
        finally:
            if pfp is not None:
                pfp.close()

        return primaryhandler.packages()

    def list_packages(self, architectures):
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
