#!/usr/bin/python
# -*- encoding: utf-8 -*-
# vim: set makeprg=python3-flake8\ %

try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os
import glob
import time

import sys
if sys.version_info.major == 2:
#Python 2
    import Queue as queue
else:
#Python 3+
    import queue

import shutil
import logging
import tempfile
import urlparse
import threading
import six.moves.BaseHTTPServer

import faftests

from pyfaf.repos.rpm_metadata import RpmMetadata
from pyfaf.utils.proc import popen


class DummyHTTPServerThread(threading.Thread):

    class Handler(six.moves.BaseHTTPServer.BaseHTTPRequestHandler):

        def do_GET(self):
            DummyHTTPServerThread.Handler.requests += 1

            parsed_path = urlparse.urlparse(self.path)

            self.send_response(200)
            if parsed_path.path.endswith(".xml"):
                self.send_header("Content-type", "text/xml")
            elif parsed_path.path.endswith(".gz"):
                self.send_header("Content-type", "application/x-gzip")
            self.end_headers()

            filepath = os.path.join(DummyHTTPServerThread.Handler.directory,
                                    parsed_path.path[1:])

            with open(filepath, "rb") as fp:
                while True:
                    data = fp.read(1024)
                    if not data:
                        break
                    self.wfile.write(data)

    def __init__(self, port, directory):
        threading.Thread.__init__(self)

        self.port = port
        self._stop = threading.Event()
        self.rqueue = queue.Queue()
        DummyHTTPServerThread.Handler.directory = directory
        DummyHTTPServerThread.Handler.requests = 0

    def stop(self):
        self._stop.set()

    def keep_running(self):
        return not self._stop.isSet()

    def run(self):
        httpd = six.moves.BaseHTTPServer.HTTPServer(("", self.port),
                                          DummyHTTPServerThread.Handler)
        httpd.timeout = 1

        while self.keep_running():
            httpd.handle_request()

        self.rqueue.put(DummyHTTPServerThread.Handler.requests)


class RpmMetadataTestCase(faftests.TestCase):
    """
    Test case for mock-yum repository plugin.
    """

    def setUp(self):
        self.rpm = glob.glob("sample_rpms/sample*.rpm")[0]

        self.tmpdir = tempfile.mkdtemp()
        self.cachedir = tempfile.mkdtemp()
        shutil.copyfile(self.rpm,
                        os.path.join(self.tmpdir, os.path.basename(self.rpm)))

        proc = popen("createrepo", self.tmpdir)
        self.assertIn("Workers Finished", proc.stdout)

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

        rpm_metadata = RpmMetadata("test_repo_absolute", self.tmpdir)
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

        rpm_metadata = RpmMetadata("test_repo_file", "file://" + self.tmpdir)
        rpm_metadata.cachedir = self.cachedir

        pkgs = rpm_metadata.list_packages(["noarch"])
        self.verify_result(pkgs,
                           "file://{0}".format(os.path.join(self.tmpdir,
                                               os.path.basename(self.rpm))))

    def test_list_packages_remote_repo_cached(self):
        t = DummyHTTPServerThread(53135, self.tmpdir)
        try:
            t.start()
            time.sleep(1)

            rpm_metadata = RpmMetadata("test_repo_http",
                                       "http://localhost:53135/")
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
        finally:
            t.stop()

        t.join(2)
        if t.isAlive():
            os.abort()

        handled_requests = t.rqueue.get()
        self.assertEqual(handled_requests, 2)

    def test_list_packages_remote_repo_NO_cache(self):
        t = DummyHTTPServerThread(53535, self.tmpdir)
        try:
            t.start()
            time.sleep(1)

            rpm_metadata = RpmMetadata("test_repo_http",
                                       "http://localhost:53535/")
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
        finally:
            t.stop()

        t.join(2)
        if t.isAlive():
            os.abort()

        handled_requests = t.rqueue.get()
        self.assertEqual(handled_requests, 6)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
