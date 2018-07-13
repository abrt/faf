#!/usr/bin/python
# -*- encoding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import glob
import logging

import faftests

from pyfaf.storage.opsys import Arch, Build, Package, PackageDependency
from pyfaf.rpm import store_rpm_deps


class RpmTestCase(faftests.DatabaseCase):
    """
    Test case for pyfaf.rpm
    """

    def test_store_rpm_deps(self):
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
        sample_rpm = glob.glob("sample_rpms/sample*.rpm")[0]
        with open(sample_rpm) as sample:
            pkg.save_lob("package", sample, truncate=True)

        # get dependencies
        res = store_rpm_deps(self.db, pkg, nogpgcheck=True)
        self.assertIs(res, True)

        expected_deps = [
            ("PROVIDES", "sample", 8),
            ("PROVIDES", "/sample", 0),
            ("PROVIDES", "nothing-new", 0),
            ("REQUIRES", "nothing", 0,),
            ("CONFLICTS", "surprisingly-nothing", 0,),
        ]

        found_deps = []

        for dep in self.db.session.query(PackageDependency).all():
            found_deps.append((dep.type, dep.name, dep.flags))

        for dep in expected_deps:
            self.assertIn(dep, found_deps)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
