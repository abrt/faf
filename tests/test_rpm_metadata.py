#!/usr/bin/python3
# -*- encoding: utf-8 -*-
# vim: set makeprg=python3-flake8\ %

import unittest
import os
import glob
import time

import sys

from collections import Counter
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import shutil
import logging
import tempfile
import urllib

import faftests

from pyfaf.repos.rpm_metadata import RpmMetadata
from pyfaf.utils.proc import popen


class DummyHTTPServerHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, counter=None, directory=None, **kwargs):
        self._counter = counter
        self._directory = directory

        super().__init__(*args, **kwargs)

    def do_GET(self):
        self._counter["requests"] += 1

        parsed_path = urllib.parse.urlparse(self.path)

        self.send_response(200)
        if parsed_path.path.endswith(".xml"):
            self.send_header("Content-type", "text/xml")
        elif parsed_path.path.endswith(".gz"):
            self.send_header("Content-type", "application/x-gzip")
        self.end_headers()

        filepath = os.path.join(self._directory, parsed_path.path[1:])

        with open(filepath, "rb") as fp:
            while True:
                data = fp.read(1024)
                if not data:
                    break
                self.wfile.write(data)


class DummyHTTPServer(HTTPServer):
    def __init__(self, port, directory):
        self._counter = Counter({"requests": 0})
        self._thread = Thread(target=super().serve_forever)

        handler_class = partial(DummyHTTPServerHandler,
                                counter=self._counter,
                                directory=directory)

        super().__init__(("", port), handler_class)

        self.timeout = 1

    @property
    def requests(self):
        return self._counter["requests"]

    def serve_forever(self):
        self._thread.start()

    def server_close(self):
        super().server_close()

        self._thread.join()


class RpmMetadataTestCase(faftests.TestCase):
    """
    Test case for mock-dnf repository plugin.
    """

    def setUp(self):
        self.rpm = glob.glob("sample_rpms/sample*.rpm")[0]

        self.tmpdir = tempfile.mkdtemp()
        self.cachedir = tempfile.mkdtemp()
        shutil.copyfile(self.rpm,
                        os.path.join(self.tmpdir, os.path.basename(self.rpm)))

        proc = popen("createrepo_c", "--verbose", self.tmpdir)
        self.assertTrue(b"Workers Finished" in proc.stdout or b"Pool finished" in proc.stdout)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        shutil.rmtree(self.cachedir)

    def verify_result(self, pkgs, url):
        self.assertEqual(len(pkgs), 1)
        pkg = pkgs.pop()
        self.assertEqual(pkg["name"], "sample")
        self.assertEqual(pkg["base_package_name"], "sample")
        self.assertEqual(pkg["version"], "1.0")
        self.assertEqual(pkg["release"], "1.fc18")
        self.assertEqual(pkg["arch"], "noarch")

        self.assertEqual(pkg["filename"], os.path.basename(self.rpm))
        self.assertEqual(pkg["url"], url)

        self.assertEqual(pkg["type"], "rpm")

    def test_list_packages_absolute_repo(self):
        """
        Test whether list_packages lists our ad-hoc
        repository without any protocol in URL correctly.
        """

        rpm_metadata = RpmMetadata("test_repo_absolute", [self.tmpdir])
        rpm_metadata.cachedir = self.cachedir

        pkgs = rpm_metadata.list_packages(["noarch"])
        self.verify_result(pkgs,
                           "file://{0}".format(
                            os.path.join(self.tmpdir,
                                         os.path.basename(self.rpm))))

    def test_list_packages_file_repo(self):
        """
        Test whether list_packages lists our ad-hoc
        repository with file:// protocol in URL correctly.
        """

        rpm_metadata = RpmMetadata("test_repo_file", ["file://" + self.tmpdir])
        rpm_metadata.cachedir = self.cachedir

        pkgs = rpm_metadata.list_packages(["noarch"])
        self.verify_result(pkgs,
                           "file://{0}".format(os.path.join(self.tmpdir,
                                               os.path.basename(self.rpm))))

    def test_list_packages_remote_repo_cached(self):
        with DummyHTTPServer(53135, self.tmpdir) as httpd:
            httpd.serve_forever()

            rpm_metadata = RpmMetadata("test_repo_http",
                                       ["http://localhost:53135/"])
            rpm_metadata.cachedir = self.cachedir

            pkgs = rpm_metadata.list_packages(["noarch"])
            self.verify_result(pkgs,
                               "http://localhost:53135/{0}".format(
                                                   os.path.basename(self.rpm)))

            pkgs = rpm_metadata.list_packages(["noarch"])
            self.verify_result(pkgs,
                               "http://localhost:53135/{0}".format(
                                                   os.path.basename(self.rpm)))

            pkgs = rpm_metadata.list_packages(["noarch"])
            self.verify_result(pkgs,
                               "http://localhost:53135/{0}".format(
                                                   os.path.basename(self.rpm)))

            httpd.shutdown()

            self.assertEqual(httpd.requests, 2)

    def test_list_packages_remote_repo_NO_cache(self):
        with DummyHTTPServer(53535, self.tmpdir) as httpd:
            httpd.serve_forever()

            rpm_metadata = RpmMetadata("test_repo_http",
                                       ["http://localhost:53535/"])
            rpm_metadata.cachedir = self.cachedir
            rpm_metadata.cacheperiod = -1

            pkgs = rpm_metadata.list_packages(["noarch"])
            self.verify_result(pkgs,
                               "http://localhost:53535/{0}".format(
                                                   os.path.basename(self.rpm)))

            pkgs = rpm_metadata.list_packages(["noarch"])
            self.verify_result(pkgs,
                               "http://localhost:53535/{0}".format(
                                                   os.path.basename(self.rpm)))

            pkgs = rpm_metadata.list_packages(["noarch"])
            self.verify_result(pkgs,
                               "http://localhost:53535/{0}".format(
                                                   os.path.basename(self.rpm)))

            httpd.shutdown()

            self.assertEqual(httpd.requests, 6)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
