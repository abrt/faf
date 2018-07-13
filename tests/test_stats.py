#!/usr/bin/python
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import logging
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import faftests

from pyfaf.utils.date import prev_days

from pyfaf.storage.report import (Report,
                                  Problem,
                                  ReportHistoryDaily,
                                  ReportHistoryWeekly,
                                  ReportHistoryMonthly)


class StatsTestCase(faftests.DatabaseCase):
    """
    Tests stats action
    """

    def setUp(self):
        """
        Add required stuff to the database
        """

        super(StatsTestCase, self).setUp()
        self.basic_fixtures()

    def make_up_history(self, report, over_days):
        """
        Make up history counts for report for `over_days` days.
        """

        total = 0

        daily = []
        weekly = []
        monthly = []

        self.db.session.delete(report.history_daily[0])
        self.db.session.delete(report.history_weekly[0])
        self.db.session.delete(report.history_monthly[0])

        opsysrelease = report.opsysreleases[0].opsysrelease

        for i, day in enumerate(prev_days(over_days)):
            d = ReportHistoryDaily(report=report,
                                   opsysrelease=opsysrelease,
                                   count=i,
                                   day=day)

            w = ReportHistoryWeekly(report=report,
                                    opsysrelease=opsysrelease,
                                    count=i,
                                    week=day)

            m = ReportHistoryMonthly(report=report,
                                     opsysrelease=opsysrelease,
                                     count=i,
                                     month=day)

            total += i
            daily.append(d)
            weekly.append(w)
            monthly.append(m)

        report.history_daily = daily
        report.history_weekly = weekly
        report.history_monthly = monthly
        report.first_occurrence = daily[0].day
        report.last_occurrence = daily[-1].day

        return total

    def test_stats_components_good_report(self):
        """
        Check if stats --components works with single good report
        """

        self.save_report("ureport1")
        self.call_action("create-problems")
        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "components": ""})

        self.assertIn("faf seen 1 times", self.action_stdout)
        self.assertIn("100%", self.action_stdout)

    def test_stats_components_filtering(self):
        """
        Check if stats --components filters opsys/release correctly
        """

        self.save_report("ureport1")
        self.call_action("create-problems")
        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "20",
            "components": ""})

        self.assertNotIn("faf seen 1 times", self.action_stdout)

    def test_stats_components_skips_bad_reports(self):
        """
        Check if stats --components respects --include-low-quality switch
        """

        self.save_report("tainted_kernel")
        self.call_action("create-problems")
        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "components": ""})

        self.assertNotIn("kernel", self.action_stdout)

        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "include-low-quality": "",
            "components": ""})

        self.assertIn("kernel", self.action_stdout)

    def test_stats_components_multiple_reports(self):
        """
        Check if stats --components produces correct results
        for multiple reports.
        """

        self.save_report("ureport1")
        self.save_report("tainted_kernel")
        self.call_action("create-problems")
        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "include-low-quality": "",
            "components": ""})

        self.assertIn("faf", self.action_stdout)
        self.assertIn("kernel", self.action_stdout)

    def test_stats_components_doesnt_include_reports_from_another_release(self):
        """
        Check if stats --components doesn't include reports
        for different release.
        """

        self.save_report("ureport1")  # faf f18
        self.save_report("ureport_f20")  # faf f20
        self.call_action("create-problems")
        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "include-low-quality": "",
            "components": ""})

        self.assertIn("faf seen 1 times", self.action_stdout)
        self.assertIn("100%", self.action_stdout)

    def test_stats_trends_produces_correct_output(self):
        """
        Check that stats --trends produces correct output for simple usecase
        """

        self.save_report("ureport1")  # faf f18
        r = self.db.session.query(Report).first()
        self.make_up_history(r, 7)

        self.db.session.flush()
        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "include-low-quality": "",
            "trends": ""})

        self.assertIn("faf", self.action_stdout)
        self.assertIn("stabilized", self.action_stdout)
        self.assertIn("destabilized", self.action_stdout)
        self.assertIn("6", self.action_stdout)  # Jump

    def test_stats_trends_generates_graphs(self):
        """
        Check that stats --trends --graph outputs UTF graphs
        """

        self.save_report("ureport1")  # faf f18
        r = self.db.session.query(Report).first()

        self.make_up_history(r, 7)

        self.db.session.flush()
        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "include-low-quality": "",
            "graph": "",
            "trends": ""})

        self.assertIn("faf", self.action_stdout)
        self.assertIn("▁▂▃▄▅▆█", self.action_stdout)

    def test_stats_trends_handles_not_enough_data(self):
        """
        Check that stats --trends copes with not enough data points
        """

        self.save_report("ureport1")  # faf f18
        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "include-low-quality": "",
            "trends": ""})

        self.assertNotIn("faf", self.action_stdout)

    def test_stats_hot_problems(self):
        """
        Verify functionality of hot problems parts of stats --problems

        Create a fake history spanning over 10 days and verify that
        the report is present in output and that the report count is correct.
        """

        self.save_report("ureport1")  # faf f18
        r = self.db.session.query(Report).first()

        total = self.make_up_history(r, 10)

        self.db.session.flush()

        self.call_action("create-problems")
        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "include-low-quality": "",
            "last": "10",
            "problems": ""})

        self.assertIn("faf", self.action_stdout)
        self.assertIn("Hot problems", self.action_stdout)
        self.assertIn(str(total), self.action_stdout)

    def test_stats_longterm_problems(self):
        """
        Verify functionality of longterm problems parts of stats --problems

        Create a fake history spanning over two months and verify that
        the report is present in output.
        """

        self.save_report("ureport1")  # faf f18
        r = self.db.session.query(Report).first()

        self.make_up_history(r, 160)

        self.db.session.flush()

        self.call_action("create-problems")

        r = self.db.session.query(Problem).first()

        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "include-low-quality": "",
            "problems": ""})

        self.assertIn("faf", self.action_stdout)
        self.assertIn("Long-term", self.action_stdout)

    def test_stats_problems_skips_bad_reports(self):
        """
        Check if stats --problems respects --include-low-quality switch
        """

        self.save_report("tainted_kernel")
        r = self.db.session.query(Report).first()
        self.make_up_history(r, 10)

        self.db.session.flush()
        self.call_action("create-problems")
        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "problems": ""})

        self.assertNotIn("kernel", self.action_stdout)

        self.call_action("stats", {
            "opsys": "fedora",
            "opsys-release": "18",
            "include-low-quality": "",
            "problems": ""})

        self.assertIn("kernel", self.action_stdout)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
