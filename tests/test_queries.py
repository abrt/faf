#!/usr/bin/python
# -*- encoding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import logging

import faftests

from pyfaf.storage.opsys import Arch, Build, Package, OpSys, OpSysComponent
from pyfaf.storage.report import ReportUnknownPackage, Report
from pyfaf.storage.problem import Problem
from pyfaf.queries import get_packages_and_their_reports_unknown_packages


class QueriesTestCase(faftests.DatabaseCase):
    """
    Test case for pyfaf.queries
    """

    def test_get_packages_and_their_reports_unknown_packages(self):
        """
        """

        # add required stuff to db
        arch = Arch()
        arch.name = "noarch"
        self.db.session.add(arch)

        arch1 = Arch()
        arch1.name = "x86_64"
        self.db.session.add(arch1)

        build = Build()
        build.base_package_name = "sample"
        build.version = "1"
        build.release = "1"
        build.epoch = "0"
        self.db.session.add(build)

        pkg = Package()
        pkg.name = "sample"
        pkg.pkgtype = "rpm"
        pkg.arch = arch
        pkg.build = build
        self.db.session.add(pkg)
        #print(pkg.nevra())

        #different arch
        pkg2 = Package()
        pkg2.name = "sample"
        pkg2.pkgtype = "rpm"
        pkg2.arch = arch1
        pkg2.build = build
        self.db.session.add(pkg2)
        #print(pkg2.nevra())

        build2 = Build()
        build2.base_package_name = "sample"
        build2.version = "1"
        build2.release = "2"
        build2.epoch = "0"
        self.db.session.add(build2)

        pkg3 = Package()
        pkg3.name = "sample"
        pkg3.pkgtype = "rpm"
        pkg3.arch = arch
        pkg3.build = build2
        self.db.session.add(pkg3)
        #print(pkg3.nevra())

        problem = Problem()
        self.db.session.add(problem)

        opsys = OpSys()
        opsys.name = "Fedora"
        self.db.session.add(opsys)

        opsys_component = OpSysComponent()
        opsys_component.name = "core"
        opsys_component.opsys = opsys
        self.db.session.add(opsys_component)

        report = Report()
        report.type = "type"
        report.count = 2
        report.problem = problem
        report.component = opsys_component
        self.db.session.add(report)

        report_unknown = ReportUnknownPackage()
        report_unknown.report = report
        report_unknown.name = pkg.name
        report_unknown.epoch = pkg.build.epoch
        report_unknown.version = pkg.build.version
        report_unknown.release = pkg.build.release
        report_unknown.arch = pkg.arch
        report_unknown.count = 1
        self.db.session.add(report_unknown)

        report_unknown2 = ReportUnknownPackage()
        report_unknown2.report = report
        report_unknown2.name = pkg2.name
        report_unknown2.epoch = pkg2.build.epoch
        report_unknown2.version = pkg2.build.version
        report_unknown2.release = pkg2.build.release
        report_unknown2.arch = pkg2.arch
        report_unknown2.count = 1
        self.db.session.add(report_unknown2)

        report_unknown3 = ReportUnknownPackage()
        report_unknown3.report = report
        report_unknown3.name = "nonsense"
        report_unknown3.epoch = pkg.build.epoch
        report_unknown3.version = pkg.build.version
        report_unknown3.release = pkg.build.release
        report_unknown3.arch = pkg.arch
        report_unknown3.count = 1
        self.db.session.add(report_unknown3)

        self.db.session.flush()

        packages_and_their_reports_unknown_packages = \
            get_packages_and_their_reports_unknown_packages(self.db).all()
        self.assertEqual(len(packages_and_their_reports_unknown_packages), 2)
        self.assertIn(
            (pkg, report_unknown), packages_and_their_reports_unknown_packages)
        self.assertIn(
            (pkg2, report_unknown2), packages_and_their_reports_unknown_packages)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
