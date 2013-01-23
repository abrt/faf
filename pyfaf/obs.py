#!/usr/bin/python
import base64
import libxml2
import pycurl
import pyfaf
import tempfile
import urllib
from cStringIO import StringIO
from pyfaf.config import CONFIG

class OBS(object):
    def __init__(self, baseurl, username, password, debug=False):
        self.baseurl = baseurl.rstrip("/")
        self.debug = debug

        auth = base64.b64encode("{0}:{1}".format(username, password))
        self.auth = "Authorization: Basic {0}".format(auth)

        self.result = None

        self.xml = None
        self.xpath = None

    def _curl(self):
        curl = pycurl.Curl()
        self.result = StringIO()
        curl.setopt(curl.HTTPHEADER, [self.auth])
        curl.setopt(curl.VERBOSE, self.debug)
        curl.setopt(curl.WRITEFUNCTION, self.result.write)
        return curl

    def _parse_xml_result(self):
        if not self.result:
            raise Exception, "No result yet"

        self._free_xml_xpath()

        self.xml = libxml2.parseDoc(self.result.getvalue())
        self.xpath = self.xml.xpathNewContext()

    def _download_and_parse(self, url):
        curl = self._curl()

        curl.setopt(curl.URL, url)
        curl.perform()
        curl.close()

        self._parse_xml_result()

    def _free_xml_xpath(self):
        if self.xpath:
            self.xpath.xpathFreeContext()
            self.xpath = None

        if self.xml:
            self.xml.freeDoc()
            self.xml = None

    def _download_to_file(self, fileobj, url):
        curl = self._curl()
        curl.setopt(curl.WRITEFUNCTION, fileobj.write)
        curl.setopt(curl.URL, url)
        curl.perform()
        curl.close()

    def get_architectures(self):
        self._download_and_parse("{0}/architectures".format(self.baseurl))

        result = set(e.prop("name") for e in self.xpath.xpathEval("/directory/entry"))

        self._free_xml_xpath()

        return result

    def get_distributions(self, vendor=None):
        """Returns: set of tuples (name, version, project, repo)"""
        self._download_and_parse("{0}/distributions".format(self.baseurl))

        query = "/distributions/distribution"
        if vendor:
            query = "{0}[@vendor='{1}']".format(query, urllib.quote_plus(vendor))

        result = set()
        for entry in self.xpath.xpathEval(query):
            vendor = entry.prop("vendor")
            version = entry.prop("version")
            project = entry.xpathEval("project")[0].content
            repo = entry.xpathEval("repository")[0].content
            result.add((vendor, version, project, repo))

        self._free_xml_xpath()

        return result

    def get_project(self, project):
        self._download_and_parse("{0}/source/{1}/_meta".format(self.baseurl, urllib.quote_plus(project)))

        project = self.xpath.xpathEval("/project")[0]
        name = project.xpathEval("title")[0].content
        repos = {}
        for repo in project.xpathEval("repository"):
            reponame = repo.prop("name")
            repos[reponame] = set(a.content for a in repo.xpathEval("arch"))

        self._free_xml_xpath()

        return name, repos

    def get_repository(self, project, repository, arch):
        url = "{0}/build/{1}/{2}/{3}".format(self.baseurl, urllib.quote_plus(project), urllib.quote_plus(repository), urllib.quote(arch))
        self._download_and_parse(url)

        result = set(p.prop("name") for p in self.xpath.xpathEval("/directory/entry"))

        self._free_xml_xpath()

        return result

    def get_package_binaries(self, project, repository, arch, pkgname):
        url = "{0}/build/{1}/{2}/{3}/{4}".format(self.baseurl, urllib.quote_plus(project), urllib.quote_plus(repository), urllib.quote_plus(arch), urllib.quote_plus(pkgname))

        self._download_and_parse(url)

        result = set()
        for binary in self.xpath.xpathEval("/binarylist/binary"):
            result.add((binary.prop("filename"), binary.prop("size"), binary.prop("mtime")))

        self._free_xml_xpath()

        return result

    def download_package_to_dir(self, project, repository, arch, pkgname, binary, basedir):
        url = "{0}/build/{1}/{2}/{3}/{4}/{5}".format(self.baseurl, urllib.quote_plus(project), urllib.quote_plus(repository), urllib.quote_plus(arch), urllib.quote_plus(pkgname), urllib.quote_plus(binary))
        with open(os.path.join(basedir, binary), "w") as f:
            self._download_to_file(f, url)

    def download_package_to_tmp(self, project, repository, arch, pkgname, binary, basedir=None):
        url = "{0}/build/{1}/{2}/{3}/{4}/{5}".format(self.baseurl, urllib.quote_plus(project), urllib.quote_plus(repository), urllib.quote_plus(arch), urllib.quote_plus(pkgname), urllib.quote_plus(binary))
        with tempfile.NamedTemporaryFile(mode="wb", prefix=binary, dir=basedir, delete=False) as f:
            self._download_to_file(f, url)

        return f.name

if __name__ == "__main__":
    obs = OBS(CONFIG["obs.url"], CONFIG["obs.username"], CONFIG["obs.password"])
    for name, version, project, repo in obs.get_distributions(vendor="openSUSE"):
        projname, repos = obs.get_project(project)
        for arch in repos[repo]:
            for pkg in obs.get_repository(project, repo, arch):
                for filename, size, mtime in obs.get_package_binaries(project, repo, arch, pkg):
                    print obs.download_package_to_tmp(project, repo, arch, pkg, filename)
