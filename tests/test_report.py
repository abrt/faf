#!/usr/bin/python3
# -*- encoding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import logging

import faftests

from pyfaf.storage.report import Report
from pyfaf.problemtypes.kerneloops import KerneloopsProblem


class ReportTestCase(faftests.DatabaseCase):
    """
    Tests ureport processing functionality.
    """
    def setUp(self):
        """
        Add required stuff to the database
        """

        super(ReportTestCase, self).setUp()

        self.basic_fixtures()

    def test_good_backtrace_quality_eq_0(self):
        """
        Check if backtrace quality metric gives 0 for complete backtrace.
        """

        self.save_report('ureport1')
        report = self.db.session.query(Report).first()
        self.assertEqual(report.quality, 0)

    def test_report_with_no_backtrace_quality(self):
        """
        Check if report has no backtrace quality metric gives -1000.
        """

        self.save_report('ureport1')
        report = self.db.session.query(Report).first()
        report.backtraces = []
        self.assertEqual(report.quality, -1000)

    def test_backtrace_with_no_frames_quality(self):
        """
        Check if backtrace has no frames quality metric gives -100.
        """

        self.save_report('ureport1')
        report = self.db.session.query(Report).first()
        bt = report.backtraces[0]
        bt.threads = []
        self.assertEqual(bt.compute_quality(), -100)

    def test_report_with_low_backtrace_quality(self):
        """
        Check if report with backtrace quality metric gives -1.
        """

        self.save_report('low_quality1')
        report = self.db.session.query(Report).first()
        self.assertEqual(report.quality, -76)

    def test_tainted_report_quality(self):
        """
        Check if report with backtrace quality metric gives -1.
        """

        KerneloopsProblem.install(self.db)
        self.save_report('tainted_kernel')
        report = self.db.session.query(Report).first()
        self.assertEqual(len(report.backtraces[0].taint_flags), 3)
        self.assertEqual(report.quality, -5)
        self.assertEqual(report.tainted, True)

    def test_unreliable_frames_quality(self):
        """
        Check if frames marked as not reliable
        lower backtrace quality
        """

        KerneloopsProblem.install(self.db)
        self.save_report('tainted_kernel')
        report = self.db.session.query(Report).first()
        bt = report.backtraces[0]
        bt.threads[0].frames[0].reliable = False
        self.assertEqual(bt.compute_quality(), -6)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
