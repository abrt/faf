#!/usr/bin/python3
# -*- encoding: utf-8 -*-
import unittest
import glob
import logging

import faftests

from pyfaf.common import FafError
from pyfaf.storage.opsys import Arch, Build, Package, PackageDependency
from pyfaf.faf_rpm import parse_evr, store_rpm_provides


class RpmTestCase(faftests.DatabaseCase):
    """
    Test case for pyfaf.rpm
    """

    def test_store_rpm_provides(self):
        """
        """

        # add required stuff to db
        arch = Arch()
        arch.name = "noarch"
        self.db.session.add(arch)

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
        self.db.session.flush()

        # save sample rpm
        with open("sample_rpms/sample-1.0-1.fc18.noarch.rpm", mode='rb') as sample:
            pkg.save_lob("package", sample, truncate=True)

        # get dependencies
        store_rpm_provides(self.db, pkg, nogpgcheck=True)

        expected_deps = [
            ("PROVIDES", "sample", 8),
            ("PROVIDES", "/sample", 0),
            ("PROVIDES", "nothing-new", 0),
        ]

        found_deps = []

        for dep in self.db.session.query(PackageDependency).all():
            found_deps.append((dep.type, dep.name, dep.flags))

        self.assertCountEqual(found_deps, expected_deps)

        build = Build()
        build.base_package_name = "sample-broken"
        build.version = "1"
        build.release = "1"
        build.epoch = 0

        self.db.session.add(build)

        pkg = Package()
        pkg.name = "sample-broken"
        pkg.pkgtype = "rpm"
        pkg.arch = arch
        pkg.build = build

        self.db.session.add(pkg)
        self.db.session.flush()

        with open("sample_rpms/sample-broken-1-1.fc22.noarch.rpm", mode='rb') as rpm_file:
            pkg.save_lob("package", rpm_file, truncate=True)

        with self.assertLogs(level=logging.WARNING) as captured_logs:
            store_rpm_provides(self.db, pkg, nogpgcheck=True)

        self.assertEqual(captured_logs.output,
                         ["WARNING:faf.pyfaf.faf_rpm:Unparsable EVR ‘%{epoch}:1’ of "
                          "zabbix in Provides of sample-broken: EVR string "
                          "contains a non-numeric epoch: %{epoch}. Skipping"])

        # Safety flush
        self.db.session.flush()

        query = self.db.session.query(PackageDependency)
        # Filter out rich RPM dependencies
        dependencies = filter(lambda x: "rpmlib" not in x.name, query.all())

        # Only provides that were correctly formatted were added
        expected_deps.extend([
            ("PROVIDES", "sample-broken", 8),
            ("PROVIDES", "happiness", 0),
            ("PROVIDES", "joy", 0),
            ("PROVIDES", "love", 0),
        ])

        self.assertCountEqual(((x.type, x.name, x.flags) for x in dependencies),
                              expected_deps)

        build = Build()
        build.base_package_name = "sample-provides-too-long"
        build.version = "1"
        build.release = "1"
        build.epoch = 0

        self.db.session.add(build)

        pkg = Package()
        pkg.name = "sample-provides-too-long"
        pkg.pkgtype = "rpm"
        pkg.arch = arch
        pkg.build = build

        self.db.session.add(pkg)
        self.db.session.flush()

        with open("sample_rpms/sample-provides-too-long-1-1.fc33.noarch.rpm", mode='rb') as rpm_file:
            pkg.save_lob("package", rpm_file, truncate=True)

        with self.assertLogs(level=logging.WARNING) as captured_logs:
            store_rpm_provides(self.db, pkg, nogpgcheck=True)

        self.assertEqual(captured_logs.output,
                         ["WARNING:faf.pyfaf.faf_rpm:Provides item in RPM header of "
                          "sample-provides-too-long longer than 1024 characters. "
                          "Skipping"])

        # Safety flush
        self.db.session.flush()

        query = self.db.session.query(PackageDependency)
        # Filter out rich RPM dependencies
        dependencies = filter(lambda x: "rpmlib" not in x.name, query.all())

        # Only provides that were correctly formatted were added
        expected_deps.extend([
            ("PROVIDES", "sample-provides-too-long", 8),
            ("PROVIDES", "one-thing", 0),
            ("PROVIDES", "another-thing", 0),
            ("PROVIDES", "penultimate-item", 0),
            ("PROVIDES", "the-last-one", 0),
        ])

        self.assertCountEqual(((x.type, x.name, x.flags) for x in dependencies),
                              expected_deps)


class UtilTestCase(faftests.TestCase):
    def test_parse_evr(self):
        self.assertEqual(parse_evr(""), (None, None, None))
        self.assertEqual(parse_evr(None), (None, None, None))
        self.assertEqual(parse_evr("1:"), ("1", None, None))
        self.assertEqual(parse_evr("-1"), (0, None, "1"))
        self.assertEqual(parse_evr("1:-1"), ("1", None, "1"))
        self.assertEqual(parse_evr("1-1"), (0, "1", "1"))
        self.assertEqual(parse_evr("1:1-1"), ("1", "1", "1"))
        with self.assertRaises(ValueError):
            parse_evr("%{epoch}:1-1")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
