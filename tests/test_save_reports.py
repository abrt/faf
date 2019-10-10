#!/usr/bin/python3
# -*- encoding: utf-8 -*-
import unittest
import logging
import json

import faftests
import os
import shutil
from pyfaf.common import ensure_dirs
from pyfaf.config import paths
from pyfaf.storage import Report, OpSysComponent, ReportBacktrace
from pyfaf.ureport import ureport2


class ActionsTestCase(faftests.DatabaseCase):

    """
    Test case for pyfaf.actions.save_reports
    """

    def setUp(self):
        super(ActionsTestCase, self).setUp()
        self.basic_fixtures()
        ensure_dirs([paths["reports_incoming"]])
        ensure_dirs([paths["reports_saved"]])
        ensure_dirs([paths["reports_deferred"]])
        ensure_dirs([paths["attachments_incoming"]])
        sample_report_names = ("ureport1", "ureport_core", "ureport_python",
                               "ureport_kerneloops", "ureport_java",
                               "ureport_ruby", "ureport_kerneloops_nouveau")
        sample_reports = {}
        i = 0
        for report_name in sample_report_names:
            i += 1
            report_filename = os.path.join(faftests.cpath, "..",
                                           "sample_reports", report_name)
            for j in range(i):
                shutil.copy(
                    report_filename,
                    os.path.join(paths["reports_incoming"], "{0}_{1}".format(report_name, j)))
            with open(report_filename, "r") as file:
                sample_reports[report_name] = ureport2(json.load(file))
                sample_reports[report_name]["test_count"] = i
        self.sample_reports = sample_reports

    def after_save_reports(self):
        self.assertEqual(self.db.session.query(Report).count(), len(self.sample_reports))
        self.assertEqual(self.db.session.query(ReportBacktrace).count(), len(self.sample_reports))
        for report in self.sample_reports.values():
            report_count = (self.db.session.query(Report.count)
                            .join(OpSysComponent)
                            .filter(OpSysComponent.name == report["problem"]["component"]).scalar())
            self.assertEqual(report["test_count"], report_count)

    def test_save_reports(self):
        self.assertEqual(self.call_action("save-reports"), 0)
        self.after_save_reports()

    def test_save_by_pattern(self):
        self.assertEqual(self.call_action("save-reports", {"pattern": "ureport1*"}), 0)
        self.assertEqual(self.db.session.query(Report).count(), 1)
        self.assertEqual(self.call_action("save-reports", {"pattern": "foobar"}), 0)
        self.assertEqual(self.db.session.query(Report).count(), 1)
        self.assertEqual(self.call_action("save-reports", {"pattern": "ureport_k*"}), 0)
        self.assertEqual(self.db.session.query(Report).count(), 3)
        self.assertEqual(self.call_action("save-reports", {"pattern": "*"}), 0)
        self.after_save_reports()


    def test_save_reports_speedup(self):
        self.assertEqual(self.call_action("save-reports", {"speedup": ""}), 0)
        self.after_save_reports()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
