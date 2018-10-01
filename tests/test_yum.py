#!/usr/bin/python
# -*- encoding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os
import glob
import shutil
import logging
import tempfile
import sys

import faftests

if sys.version_info.major == 2:
    from pyfaf.repos.yum import Yum

from pyfaf.utils.proc import popen


@unittest.skipUnless(sys.version_info.major == 2, "requires Python 2")
class YumTestCase(faftests.TestCase):
    """
    Test case for yum repository plugin.
    """

    def test_list_packages(self):
        """
        Test whether list_packages lists our ad-hoc
        repository correctly.
        """

        rpm = glob.glob("sample_rpms/sample*.rpm")[0]

        tmpdir = tempfile.mkdtemp()
        shutil.copyfile(rpm, os.path.join(tmpdir, os.path.basename(rpm)))

        proc = popen("createrepo", tmpdir)
        self.assertIn(b"Workers Finished", proc.stdout)

        yum = Yum("test_repo_name", tmpdir)
        pkgs = yum.list_packages(["noarch"])
        self.assertEqual(len(pkgs), 1)
        pkg = pkgs.pop()
        self.assertEqual(pkg["name"], "sample")
        self.assertEqual(pkg["base_package_name"], "sample")
        self.assertEqual(pkg["version"], "1.0")
        self.assertEqual(pkg["release"], "1.fc18")
        self.assertEqual(pkg["arch"], "noarch")

        self.assertEqual(pkg["filename"], os.path.basename(rpm))
        self.assertEqual(pkg["url"], "file://{0}".format(
            os.path.join(tmpdir, os.path.basename(rpm))))

        self.assertEqual(pkg["type"], "rpm")

        shutil.rmtree(tmpdir)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
