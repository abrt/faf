#!/usr/bin/python3
# -*- encoding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import logging
import faftests
import json

from datetime import datetime, timedelta

from pyfaf.storage.problem import Problem
from pyfaf.storage.report import (Report,
                                  ReportHash,
                                  ReportUnknownPackage,
                                  ReportPackage,
                                  ReportOpSysRelease)
from pyfaf.storage.opsys import Build, Package
from pyfaf.opsys import systems
from pyfaf.problemtypes import problemtypes
from pyfaf.solutionfinders import find_solution, Solution


def get_released_builds_mock(release):
    return [
        {"name": "systemd",
         "epoch": None,
         "version": "3",
         "release": "1",
         "nvr": "systemd-3-1",
         "completion_time": datetime.now()-timedelta(days=2)
         },
        {"name": "faf",
         "epoch": None,
         "version": "3.11",
         "release": "11",
         "nvr": "faf-3.11-11",
         "completion_time": datetime.now()-timedelta(days=30)
         },
        {"name": "systemd",
         "epoch": None,
         "version": "3",
         "release": "0",
         "nvr": "systemd-3-0",
         "completion_time": datetime.now()-timedelta(days=90)
         },
        {"name": "systemd",
         "epoch": None,
         "version": "2",
         "release": "0",
         "nvr": "systemd-2-0",
         "completion_time": datetime.now()-timedelta(days=100)
         }
    ]


class MPFTestCase(faftests.DatabaseCase):

    """
    Test case for pyfaf.actions.mark_probably_fixed
    """

    def setUp(self):
        super(MPFTestCase, self).setUp()
        self.basic_fixtures()

        # Fixed problem 1
        problem = Problem()
        self.db.session.add(problem)

        report = Report()
        report.type = "type"
        report.count = 2
        report.problem = problem
        report.component = self.comp_systemd
        self.db.session.add(report)

        with open("sample_reports/ureport_systemd2", "r") as file:
            self.ureport_systemd2 = json.load(file)
        with open("sample_reports/ureport_systemd77", "r") as file:
            self.ureport_systemd77 = json.load(file)
        problemplugin = problemtypes[self.ureport_systemd2["problem"]["type"]]
        report_hash = problemplugin.hash_ureport(self.ureport_systemd2["problem"])
        db_hash = ReportHash()
        db_hash.hash = report_hash
        db_hash.report = report
        self.db.session.add(db_hash)

        report_unknown = ReportUnknownPackage()
        report_unknown.report = report
        report_unknown.name = "systemd-test"
        report_unknown.epoch = 0
        report_unknown.version = 2
        report_unknown.release = 1
        report_unknown.semver = "2.0.0"
        report_unknown.semrel = "1.0.0"
        report_unknown.arch = self.arch_i686
        report_unknown.count = 1
        report_unknown.type = "CRASHED"
        self.db.session.add(report_unknown)

        report_unknown = ReportUnknownPackage()
        report_unknown.report = report
        report_unknown.name = "faf"
        report_unknown.epoch = 0
        report_unknown.version = 1
        report_unknown.release = 1
        report_unknown.semver = "1.0.0"
        report_unknown.semrel = "1.0.0"
        report_unknown.arch = self.arch_i686
        report_unknown.count = 1
        report_unknown.type = "RELATED"
        self.db.session.add(report_unknown)

        report_osr = ReportOpSysRelease()
        report_osr.count = 77
        report_osr.opsysrelease = self.release_20
        report_osr.report = report
        self.db.session.add(report_osr)

        report_osr = ReportOpSysRelease()
        report_osr.count = 77
        report_osr.opsysrelease = self.release_19
        report_osr.report = report
        self.db.session.add(report_osr)

        self.problem_fixed1 = problem

        # Fixed problem 2
        problem = Problem()
        self.db.session.add(problem)

        report = Report()
        report.type = "type"
        report.count = 2
        report.problem = problem
        report.component = self.comp_faf
        self.db.session.add(report)

        build = Build()
        build.base_package_name = "faf"
        build.epoch = 0
        build.version = "3.4"
        build.release = "5"
        self.db.session.add(build)

        pkg = Package()
        pkg.build = build
        pkg.arch = self.arch_i686
        pkg.name = "faf-test"
        self.db.session.add(pkg)

        rpkg = ReportPackage()
        rpkg.report = report
        rpkg.type = "CRASHED"
        rpkg.installed_package = pkg
        rpkg.count = 66
        self.db.session.add(rpkg)

        report_osr = ReportOpSysRelease()
        report_osr.count = 77
        report_osr.opsysrelease = self.release_20
        report_osr.report = report
        self.db.session.add(report_osr)

        self.problem_fixed2 = problem

        # Unfixed problem 1
        problem = Problem()
        self.db.session.add(problem)

        report = Report()
        report.type = "type"
        report.count = 2
        report.problem = problem
        report.component = self.comp_systemd
        self.db.session.add(report)

        report_unknown = ReportUnknownPackage()
        report_unknown.report = report
        report_unknown.name = "systemd"
        report_unknown.epoch = 0
        report_unknown.version = 3
        report_unknown.release = 1
        report_unknown.semver = "3.0.0"
        report_unknown.semrel = "1.0.0"
        report_unknown.arch = self.arch_i686
        report_unknown.count = 1
        report_unknown.type = "CRASHED"
        self.db.session.add(report_unknown)

        report_osr = ReportOpSysRelease()
        report_osr.count = 77
        report_osr.opsysrelease = self.release_20
        report_osr.report = report
        self.db.session.add(report_osr)

        self.problem_unfixed1 = problem

        # Unfixed problem 2
        problem = Problem()
        self.db.session.add(problem)

        report = Report()
        report.type = "type"
        report.count = 2
        report.problem = problem
        report.component = self.comp_systemd
        self.db.session.add(report)

        report_unknown = ReportUnknownPackage()
        report_unknown.report = report
        report_unknown.name = "systemd"
        report_unknown.epoch = 0
        report_unknown.version = 3
        report_unknown.release = 0
        report_unknown.semver = "3.0.0"
        report_unknown.semrel = "0.0.0"
        report_unknown.arch = self.arch_i686
        report_unknown.count = 1
        report_unknown.type = "CRASHED"
        self.db.session.add(report_unknown)

        report_osr = ReportOpSysRelease()
        report_osr.count = 77
        report_osr.opsysrelease = self.release_20
        report_osr.report = report
        self.db.session.add(report_osr)

        self.problem_unfixed2 = problem

        # Unfixed problem 3
        problem = Problem()
        self.db.session.add(problem)

        report = Report()
        report.type = "type"
        report.count = 2
        report.problem = problem
        report.component = self.comp_faf
        self.db.session.add(report)

        build = Build()
        build.base_package_name = "faf"
        build.epoch = 0
        build.version = "3.110"
        build.release = "5"
        self.db.session.add(build)

        pkg = Package()
        pkg.build = build
        pkg.arch = self.arch_i686
        pkg.name = "faf-test"
        self.db.session.add(pkg)

        rpkg = ReportPackage()
        rpkg.report = report
        rpkg.type = "CRASHED"
        rpkg.installed_package = pkg
        rpkg.count = 66
        self.db.session.add(rpkg)

        report_osr = ReportOpSysRelease()
        report_osr.count = 77
        report_osr.opsysrelease = self.release_20
        report_osr.report = report
        self.db.session.add(report_osr)

        self.problem_unfixed3 = problem

        self.db.session.flush()

        systems['fedora'].get_released_builds = get_released_builds_mock
        systems['fedora'].build_aging_days = 7

    def test_mark_probably_fixed_20(self):
        self.call_action("mark-probably-fixed", {
            "opsys": "fedora",
            "opsys-release": "20"
        })

        self.assertEqual(len(self.problem_fixed1.probable_fixes), 1)
        self.assertEqual(self.problem_fixed1
                         .probable_fix_for_opsysrelease_ids([self.release_20.id]),
                         "systemd-3-0")
        self.assertEqual(self.problem_fixed1
                         .probable_fix_for_opsysrelease_ids([self.release_19.id]),
                         "")
        self.assertEqual(self.problem_fixed1.probable_fix_for_opsysrelease_ids(
                         [self.release_20.id, self.release_19.id]),
                         "Fedora 20: systemd-3-0")

        self.assertEqual(len(self.problem_fixed2.probable_fixes), 1)
        self.assertEqual(self.problem_fixed2
                         .probable_fix_for_opsysrelease_ids([self.release_20.id]),
                         "faf-3.11-11")

        self.assertEqual(len(self.problem_unfixed1.probable_fixes), 0)

        self.assertEqual(len(self.problem_unfixed2.probable_fixes), 0)

        self.assertEqual(len(self.problem_unfixed3.probable_fixes), 0)

    def test_mark_probably_fixed_19(self):
        self.call_action("mark-probably-fixed", {
            "opsys": "fedora",
            "opsys-release": "19"
        })

        self.assertEqual(len(self.problem_fixed1.probable_fixes), 1)
        self.assertEqual(self.problem_fixed1
                         .probable_fix_for_opsysrelease_ids([self.release_19.id]),
                         "systemd-3-0")
        self.assertEqual(self.problem_fixed1
                         .probable_fix_for_opsysrelease_ids([self.release_20.id]),
                         "")
        self.assertEqual(self.problem_fixed1.probable_fix_for_opsysrelease_ids(
                         [self.release_20.id, self.release_19.id]),
                         "Fedora 19: systemd-3-0")

        self.assertEqual(len(self.problem_fixed2.probable_fixes), 0)

        self.assertEqual(len(self.problem_unfixed1.probable_fixes), 0)

        self.assertEqual(len(self.problem_unfixed2.probable_fixes), 0)

        self.assertEqual(len(self.problem_unfixed3.probable_fixes), 0)

    def test_mark_probably_fixed_19_20(self):
        self.call_action("mark-probably-fixed", {
            "opsys": "fedora",
            "opsys-release": "19"
        })
        self.call_action("mark-probably-fixed", {
            "opsys": "fedora",
            "opsys-release": "20"
        })

        self.assertEqual(len(self.problem_fixed1.probable_fixes), 2)
        self.assertEqual(self.problem_fixed1
                         .probable_fix_for_opsysrelease_ids([self.release_19.id]),
                         "systemd-3-0")
        self.assertEqual(self.problem_fixed1
                         .probable_fix_for_opsysrelease_ids([self.release_20.id]),
                         "systemd-3-0")

        self.assertEqual(len(self.problem_fixed2.probable_fixes), 1)

        self.assertEqual(len(self.problem_unfixed1.probable_fixes), 0)

        self.assertEqual(len(self.problem_unfixed2.probable_fixes), 0)

        self.assertEqual(len(self.problem_unfixed3.probable_fixes), 0)

    def test_solution_finder(self):
        """
        Test if no solution is given when the version of an affected package
        in a report is greater that the probable fix.
        """
        self.call_action("mark-probably-fixed", {
            "opsys": "fedora",
            "opsys-release": "20"
        })

        self.assertIsInstance(find_solution(self.ureport_systemd2), Solution)
        self.assertIsNone(find_solution(self.ureport_systemd77))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
