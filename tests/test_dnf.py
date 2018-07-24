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

import faftests

from pyfaf.repos.dnf import Dnf
from pyfaf.utils.proc import popen


class DnfTestCase(faftests.TestCase):
    """
    Test case for dnf repository plugin.
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
        self.assertIn("Workers Finished", proc.stdout)

        dnf = Dnf("test_repo_name", tmpdir)
        pkgs = dnf.list_packages(["noarch"])
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
