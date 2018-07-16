#!/usr/bin/python
# -*- encoding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest
from webfaftests import WebfafTestCase


class SummaryTestCase(WebfafTestCase):
    """
    Tests for webfaf.summary
    """

    def setUp(self):
        super(SummaryTestCase, self).setUp()
        self.basic_fixtures()

        self.save_report("ureport_f20")

        self.db.session.commit()

    def test_index_redirect(self):
        """
        Index should redirect to /summary/
        """

        r = self.app.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/summary/", r.data)

    def test_summary(self):
        """
        Test presence of data on the summary page
        """

        r = self.app.get("/summary/")

        self.assertIn("Fedora 20", r.data)
        self.assertIn("faf", r.data)
        self.assertIn(" 1],", r.data)  # graph point

if __name__ == "__main__":
    unittest.main()
