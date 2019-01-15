#!/usr/bin/python3
# -*- encoding: utf-8 -*-
import os
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import sys
from io import BytesIO as StringIO

from webfaftests import WebfafTestCase
from pyfaf.config import paths, config


class DumpdirsTestCase(WebfafTestCase):
    """
    Tests for webfaf.dumpdirs
    """

    def setUp(self):
        super(DumpdirsTestCase, self).setUp()
        self.basic_fixtures()
        self.db.session.commit()
        os.makedirs(paths["dumpdir"])

    def post_dumpdir(self, filename):

        r = self.app.post("/dumpdirs/new/", buffered=True,
                          headers={"Accept": "application/json"},
                          content_type="multipart/form-data",
                          data={"file": (StringIO("nothing".encode("utf-8")), filename)})

        return r

    def test_new_dumpdir(self):
        """
        Test saving of dumpdir
        """

        # Wrong file name
        r = self.post_dumpdir("test.txt")
        self.assertEqual(r.status_code, 400)

        # Wrong file name
        r = self.post_dumpdir("ccpp-2018-09-20-21:15:55.518467-11870.tar.gzz")
        self.assertEqual(r.status_code, 400)

        # Correct file name
        r = self.post_dumpdir("ccpp-2014-09-19-18:42:29-12810.tar.gz")
        self.assertEqual(r.status_code, 201)

        # Correct file name
        r = self.post_dumpdir("Python3-2017-05-02-09:38:47-5285.tar.gz")
        self.assertEqual(r.status_code, 201)

        # Correct file name
        r = self.post_dumpdir("oops-2017-08-16-16:51:10-882-0.tar.gz")
        self.assertEqual(r.status_code, 201)

        # Correct file name
        r = self.post_dumpdir("ccpp-2018-09-20-21:15:55.518467-11870.tar.gz")
        self.assertEqual(r.status_code, 201)

        # Too big dumpdir
        config["dumpdir.maxdumpdirsize"] = 1
        r = self.post_dumpdir("ccpp-2014-09-19-18:42:29-12811.tar.gz")
        self.assertEqual(r.status_code, 413)
        config["dumpdir.maxdumpdirsize"] = 1000

        # Breaking size quota
        config["dumpdir.cachedirectorysizequota"] = 1
        r = self.post_dumpdir("ccpp-2014-09-19-18:42:29-12812.tar.gz")
        self.assertEqual(r.status_code, 500)
        config["dumpdir.cachedirectorysizequota"] = 10000

        # Breaking count quota
        config["dumpdir.cachedirectorycountquota"] = 1
        r = self.post_dumpdir("ccpp-2014-09-19-18:42:29-12813.tar.gz")
        self.assertEqual(r.status_code, 500)
        config["dumpdir.cachedirectorycountquota"] = 10000

if __name__ == "__main__":
    unittest.main()
