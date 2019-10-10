#!/usr/bin/python3
# -*- encoding: utf-8 -*-
import unittest
from webfaftests import WebfafTestCase

from pyfaf.storage.opsys import Build, Package


class ProblemsTestCase(WebfafTestCase):
    """
    Tests for webfaf.problems
    """

    def setUp(self):
        super(ProblemsTestCase, self).setUp()
        self.basic_fixtures()

        build = Build()
        build.base_package_name = "kernel"
        build.epoch = 0
        build.version = "3.12.10"
        build.release = "300.fc20"
        self.db.session.add(build)

        pkg = Package()
        pkg.build = build
        pkg.arch = self.arch_x86_64
        pkg.name = "kernel"
        self.db.session.add(pkg)

        self.db.session.commit()

        self.save_report("ureport_kerneloops")
        self.call_action("create-problems")

        self.db.session.commit()

    def test_problem_shown(self):
        """
        Test if new problem is displayed on problems page
        """

        r = self.app.get("/problems/")
        self.assertIn(b"/problems/1/", r.data)
        self.assertIn(b"NEW", r.data)

    def test_problem_detail(self):
        """
        Test if problem details are presented correctly
        """

        r = self.app.get("/problems/1/")
        self.assertIn(b"kernel", r.data)
        self.assertIn(b"NEW", r.data)
        self.assertIn(b"wl_event_handler", r.data)
        self.assertIn(b"Fedora 20", r.data)
        self.assertIn(b"0:3.12.10-300.fc20", r.data)

    def test_problem_version_filter(self):
        """
        Test if version filtering yields problem
        when valid query string is used
        """
        present = [
            "since_version=3",
            "since_version=3.12",
            "since_version=3.12.10",
            "since_release=100",
            "since_release=100.fc20",
            "since_release=300.fc20",
            "to_version=4",
            "to_version=3.13",
            "to_version=3.12.11",
            "to_release=400",
            "to_release=400.fc20",
            "to_release=300.fc20",
            "since_version=3.12.9&since_release=400.fc20",
            "since_version=3.12.10&since_release=300.fc20",
            "to_version=3.12.11&to_release=200.fc20",
            "to_version=3.12.11&to_release=300.fc20",
            ("since_version=3.12.10&since_release=300.fc20"
             "&to_version=3.12.11&to_release=300.fc20"),
        ]

        filtered = [
            "since_version=4",
            "since_version=3.13",
            "since_version=3.12.11",
            "since_release=400",
            "since_release=400.fc20",
            "to_version=3",
            "to_version=3.12",
            "to_version=3.12.9",
            "to_release=200",
            "to_release=200.fc20",
            ("since_version=3.12.10&since_release=300.fc20"
             "&to_version=3.11.11&to_release=300.fc20"),
        ]

        for qs in present:
            r = self.app.get("/problems/?{0}".format(qs))
            if b"NEW" not in r.data:
                self.fail("query string {0}, missing expected 'NEW' in result"
                          .format(qs))

        for qs in filtered:
            r = self.app.get("/problems/?{0}".format(qs))
            if b"NEW" in r.data:
                self.fail("query string {0}, unexpected 'NEW' in result"
                          .format(qs))

    def test_problem_version_complex_filter(self):
        """
        Test if filtering yields two problems
        when only one of them matches release
        """

        build = Build()
        build.base_package_name = "kernel"
        build.epoch = 0
        build.version = "3.13.10"
        build.release = "100.fc20"
        self.db.session.add(build)

        pkg = Package()
        pkg.build = build
        pkg.arch = self.arch_x86_64
        pkg.name = "kernel"
        self.db.session.add(pkg)

        self.db.session.commit()

        self.save_report("ureport_kerneloops2")
        self.call_action("create-problems")

        self.db.session.commit()

        qs = "since_version=3.12&since_release=300.fc20"
        r = self.app.get("/problems/?{0}".format(qs))
        self.assertIn(b"problems/1", r.data)
        self.assertIn(b"problems/2", r.data)


if __name__ == "__main__":
    unittest.main()
