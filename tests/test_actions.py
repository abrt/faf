#!/usr/bin/python3
# -*- encoding: utf-8 -*-
import functools
import http.server
import unittest
import logging
import json
from datetime import datetime, timedelta
import threading

import glob
import tempfile
import shutil
import os
import time

import faftests

from pyfaf.utils.proc import popen
from pyfaf.config import config
from pyfaf.opsys import systems
from pyfaf.storage.bugtracker import Bugtracker
from pyfaf.storage.bugzilla import BzBug, BzUser
from pyfaf.storage.report import Report
from pyfaf.storage.problem import Problem
from pyfaf.storage.opsys import (Arch,
                                 OpSysReleaseRepo,
                                 BuildOpSysReleaseArch,
                                 Build,
                                 BuildArch,
                                 Package,
                                 )
from pyfaf.storage.debug import InvalidUReport
from pyfaf.storage.user import User
from pyfaf.solutionfinders import find_solution
from pyfaf.repos import repo_types


class ActionsTestCase(faftests.DatabaseCase):

    """
    Test case for pyfaf.actions
    """

    preferred_repo_types = ["dnf"]

    def setUp(self):
        super(ActionsTestCase, self).setUp()
        self.basic_fixtures()

    def assert_correct_sar_output(self, json_data, mail, num):
        user = (self.db.session.query(User)
                .filter(User.mail == mail)
                .first())

        self.assertEqual(json_data["Username"], user.username)
        self.assertEqual(json_data["Mail"], user.mail)

        bg = json_data["Bugzilla"]
        self.assertEqual(bg["Name"], user.mail)
        self.assertEqual(bg["Mail"], user.mail)
        self.assertEqual(bg["Created Bugzillas"][0]["Bug ID"], num)
        self.assertEqual(bg["Created Bugzillas"][0]["Status"], "CLOSED")
        self.assertEqual(bg["History"][0]["Bug ID"], num)
        self.assertEqual(bg["History"][0]["Added"], "POST")
        self.assertEqual(bg["History"][0]["Removed"], "NEW")
        self.assertEqual(bg["Comments"][0]["Bug ID"], num)
        self.assertEqual(bg["Comments"][0]["Comment #"], 1)
        self.assertEqual(bg["Attachments"][0]["Bug ID"], num)
        self.assertEqual(bg["Attachments"][0]["Filename"], "fake_filename.json")
        self.assertIn(num, bg["CCs"])

        self.assertEqual(json_data["Contact Mail Reports"]["Contact Mail"], user.mail)
        self.assertEqual(json_data["Contact Mail Reports"]["Reports"][0], "{}".format(num))

    def test_releaseadd(self):
        self.assertEqual(self.call_action("releaseadd", {
            "opsys": "fedora",
            "opsys-release": "20",
            "status": "ACTIVE",
        }), 0)
        self.assertEqual(self.call_action("releaseadd", {
            "opsys": "fedora",
            "opsys-release": "20",
            "status": "ACTIVE",
        }), 0)
        self.assertEqual(self.call_action("releaseadd", {
            "opsys": "fedora",
            "opsys-release": "10",
            "status": "EOL",
        }), 0)


    def test_archadd(self):
        init_archs = self.db.session.query(Arch).all()

        self.assertEqual(self.call_action("archadd", {
            "NAME": "FooArch"
        }), 0)

        archs = self.db.session.query(Arch).all()
        self.assertEqual(len(archs), len(init_archs) + 1)

        # Adding an existing Arch should return 1 and not add it
        self.assertEqual(self.call_action("archadd", {
            "NAME": "FooArch"
        }), 1)
        archs = self.db.session.query(Arch).all()
        self.assertEqual(len(archs), len(init_archs) + 1)

    def test_repoadd(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.repoadd_testing(repo_type)
                self.tearDown()
                self.setUp()

    def repoadd_testing(self, repo_type):
        self.assertEqual(self.call_action_ordered_args("repoadd", [
            "sample_repo", # NAME
            repo_type, # TYPE
            "file:///sample_rpms", # URL
        ]), 0)

        self.assertEqual(self.call_action_ordered_args("repoadd", [
            "sample_repo", # NAME
            repo_type, # TYPE
            "file:///sample_rpms", # URL
        ]), 1)

        self.assertEqual(self.call_action_ordered_args("repoadd", [
            "another_repo", # NAME
            repo_type, # TYPE
            "file:///sample_rpms", # URL1
            "file:///sample_rpms1", # URL2
            "file:///sample_rpms2", # URL3
        ]), 0)

        self.assertEqual(self.call_action_ordered_args("repoadd", [
            "yet_another_repo", # NAME
            repo_type, # TYPE
            "file:///sample_rpms", # URL
        ]), 0)

        self.assertEqual(self.call_action_ordered_args("repoadd", [
            "samplerepo1", # NAME
            repo_type, # TYPE
            "file:///sample_rpms", # URL
        ]), 0)

        self.assertEqual(self.call_action_ordered_args("repoadd", [
            "samplerepo2", # NAME
            repo_type, # TYPE
            "file:///sample_rpms", # URL
        ]), 0)

        self.assertEqual(self.call_action_ordered_args("repoadd", [
            "samplerepo30", # NAME
            repo_type, # TYPE
            "file:///sample_rpms", # URL
        ]), 0)

    def test_repoinfo(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.repoinfo_testing(repo_type)
                self.tearDown()
                self.setUp()

    def repoinfo_testing(self, repo_type):
        self.repoadd_testing(repo_type)

        self.assertEqual(self.call_action_ordered_args("repoinfo", [
            "sample_repo"]), 0)

        self.assertIn("file:///sample_rpms", self.action_stdout)

        self.assertEqual(self.call_action_ordered_args("repoinfo", [
            "another_repo"]), 0)

        self.assertIn("file:///sample_rpms", self.action_stdout)
        self.assertIn("file:///sample_rpms1", self.action_stdout)
        self.assertIn("file:///sample_rpms2", self.action_stdout)

        self.assertEqual(self.call_action_ordered_args("repoinfo", [
            "sample_repo_unknown"]), 1)

    def test_repolist(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.repolist_testing(repo_type)
                self.tearDown()
                self.setUp()

    def repolist_testing(self, repo_type):
        self.repoadd_testing(repo_type)

        self.assertEqual(self.call_action_ordered_args("repolist", [
            ]), 0)

        self.assertIn("another_repo", self.action_stdout)
        self.assertIn("sample_repo", self.action_stdout)

        self.assertEqual(self.call_action_ordered_args("repolist", [
            "--detailed"]), 0)

        self.assertIn("another_repo", self.action_stdout)
        self.assertIn("sample_repo", self.action_stdout)
        self.assertIn("file:///sample_rpms", self.action_stdout)
        self.assertIn("file:///sample_rpms1", self.action_stdout)
        self.assertIn("file:///sample_rpms2", self.action_stdout)

    def test_repomod(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.repomod_testing(repo_type)
                self.tearDown()
                self.setUp()

    def repomod_testing(self, repo_type):
        self.repoadd_testing(repo_type)

        self.assertEqual(self.call_action_ordered_args("repomod", [
            "sample_repo", "--add-url=file:///some/new/url"]), 0)

        self.assertEqual(self.call_action_ordered_args("repoinfo", [
            "sample_repo"]), 0)

        self.assertIn("file:///sample_rpms", self.action_stdout)
        self.assertIn("file:///some/new/url", self.action_stdout)

        self.assertEqual(self.call_action_ordered_args("repomod", [
            "sample_repo", "--remove-url=file:///sample_rpms"]), 0)

        self.assertEqual(self.call_action_ordered_args("repoinfo", [
            "sample_repo"]), 0)

        self.assertNotIn("file:///sample_rpms", self.action_stdout)
        self.assertIn("file:///some/new/url", self.action_stdout)

        self.assertEqual(self.call_action_ordered_args("repomod", [
            "sample_repo", "another_repo", "--gpgcheck", "disable"]), 0)

        self.assertEqual(self.call_action_ordered_args("repolist", ["--detailed"]), 0)

        self.assertRegex(self.action_stdout, r'sample_repo.*False')
        self.assertRegex(self.action_stdout, r'another_repo.*False')

        self.assertEqual(self.call_action_ordered_args("repomod", [
            "*_repo", "--name=impossible_repo"]), 1)

    def test_repodel(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.repodel_testing(repo_type)
                self.tearDown()
                self.setUp()

    def repodel_testing(self, repo_type):
        self.repoadd_testing(repo_type)

        self.assertEqual(self.call_action_ordered_args("repodel", [
            "sample_repo"]), 0)

        self.assertEqual(self.call_action_ordered_args("repolist", [
            "--detailed"]), 0)

        self.assertIn("another_repo", self.action_stdout)
        self.assertNotIn("sample_repo", self.action_stdout)
        self.assertIn("file:///sample_rpms", self.action_stdout)
        self.assertIn("file:///sample_rpms1", self.action_stdout)
        self.assertIn("file:///sample_rpms2", self.action_stdout)

        self.assertEqual(self.call_action_ordered_args("repodel", [
            "*_*"]), 0)

        self.assertEqual(self.call_action_ordered_args("repolist", [
            "--detailed"]), 0)

        self.assertNotIn("another_repo", self.action_stdout)
        self.assertNotIn("sample_repo", self.action_stdout)
        self.assertNotIn("yet_another_repo", self.action_stdout)

        self.assertEqual(self.call_action_ordered_args("repodel", [
            "samplerepo?"]), 0)

        self.assertEqual(self.call_action_ordered_args("repolist", [
            "--detailed"]), 0)

        self.assertNotIn("samplerepo1", self.action_stdout)
        self.assertNotIn("samplerepo2", self.action_stdout)
        self.assertIn("samplerepo30", self.action_stdout)

        self.assertEqual(self.call_action_ordered_args("repodel", [
            "--all"]), 0)

        self.assertEqual(self.call_action_ordered_args("repolist", [
            "--detailed"]), 0)

        self.assertNotIn("samplerepo30", self.action_stdout)

    def test_repoimport(self):

        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.repoimport_testing(repo_type)
                self.tearDown()
                self.setUp()

    def repoimport_testing(self, repo_type):
        self.assertEqual(self.call_action_ordered_args("repoimport", [
            repo_type, "sample_repo/dummy_repo.repo"]), 0)

        self.assertEqual(self.call_action_ordered_args("repolist", [
            "--detailed"]), 0)

        self.assertIn("repo1", self.action_stdout)
        self.assertIn("repo2", self.action_stdout)
        self.assertIn("file:///some/where", self.action_stdout)
        self.assertIn("file:///some/other/place", self.action_stdout)

    def test_repoassign_opsysrelease(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.repoassign_opsysrelease_testing(repo_type)
                self.tearDown()
                self.setUp()

    def repoassign_opsysrelease_testing(self, repo_type):
        # add repo
        self.assertEqual(self.call_action_ordered_args("repoadd", [
            "sample_repo", # NAME
            repo_type, # TYPE
            "file:///sample_rpms", # URL
        ]), 0)

        # add release
        self.assertEqual(self.call_action("releaseadd", {
            "opsys": "fedora",
            "opsys-release": "24",
            "status": "ACTIVE",
        }), 0)

        init_opsysreleaserepo = self.db.session.query(OpSysReleaseRepo).count()
        self.assertEqual(self.call_action_ordered_args("repoassign", [
            "sample_repo", # NAME
            "Fedora 24", # OPSYS
            "x86_64",# ARCH
        ]), 0)

        opsysreleaserepo = self.db.session.query(OpSysReleaseRepo).count()
        self.assertEqual(opsysreleaserepo, init_opsysreleaserepo + 1)

        self.assertEqual(self.call_action_ordered_args("repoassign", [
            "sample_repo", # NAME
            "Fedora", # OPSYS
            "x86_64",# ARCH
        ]), 1)

    def test_reposync(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.reposync_testing(repo_type)
                self.tearDown()
                self.setUp()

    def reposync_testing(self, repo_type):
        self.call_action("releaseadd", {
            "opsys": "fedora",
            "opsys-release": "24",
            "status": "ACTIVE",
        })

        init_bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        init_package_count = self.db.session.query(Package).count()

        def reposync(repo, repodir, packages, reuse=False, force_resync=False):
            for package in packages:
                shutil.copyfile(package,
                                os.path.join(repodir, os.path.basename(package)))

            proc = popen("createrepo_c", "--verbose", repodir)
            self.assertTrue(b"Workers Finished" in proc.stdout or b"Pool finished" in proc.stdout)

            if not reuse:
                self.call_action_ordered_args("repoadd", [
                    repo, # NAME
                    repo_type, # TYPE
                    "file://{0}".format(repodir), # URL
                ])

                self.call_action_ordered_args("repoassign", [
                    repo, # NAME
                    "Fedora 24", # OPSYS
                    "x86_64",# ARCH
                ])

            reposync_args = {
                "NAME": repo,
                "no-download-rpm": "",
            }

            if force_resync:
                reposync_args["no-cache"] = ""

            self.assertEqual(self.call_action("reposync", reposync_args), 0)

        with tempfile.TemporaryDirectory() as tmpdir:
            packages = [
                "sample_rpms/sample-1.0-1.fc18.noarch.rpm",
            ]
            reposync("sample_repo", tmpdir, packages)

            bosra = self.db.session.query(BuildOpSysReleaseArch).count()
            self.assertEqual(bosra, init_bosra + 1)
            package_count = self.db.session.query(Package).count()
            self.assertEqual(init_package_count + 1, package_count)

            packages = [
                "sample_rpms/sample2-2.0-1.fc32.noarch.rpm",
            ]
            reposync("sample_repo", tmpdir, packages, reuse=True)

            bosra = self.db.session.query(BuildOpSysReleaseArch).count()
            self.assertEqual(bosra, init_bosra + 1)
            package_count = self.db.session.query(Package).count()
            self.assertEqual(init_package_count + 1, package_count)

            # The repo metadata needs to be sufficiently aged and POSIX defines
            # stat.st_mtime as stat.st_mtim.tv_sec for compatibility raisins,
            # so we need to do some lollygagging here.
            time.sleep(1)

            reposync("sample_repo", tmpdir, [], reuse=True, force_resync=True)

            bosra = self.db.session.query(BuildOpSysReleaseArch).count()
            self.assertEqual(bosra, init_bosra + 2)
            package_count = self.db.session.query(Package).count()
            self.assertEqual(init_package_count + 2, package_count)

        self.call_action_ordered_args("repoadd", [
            "fail_repo", # NAME
            repo_type, # TYPE
            "file:///non/existing", # URL
        ])

        self.call_action_ordered_args("repoassign", [
            "fail_repo", # NAME
            "Fedora 24", # OPSYS
            "x86_64",# ARCH
        ])

        self.assertEqual(self.call_action("reposync", {
            "NAME": "fail_repo",
        }), 0)

        self.assertEqual(package_count, self.db.session.query(Package).count())

    def test_reposync_mirror(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.reposync_mirror_testing(repo_type)
                self.tearDown()
                self.setUp()

    def reposync_mirror_testing(self, repo_type):
        self.rpm = "sample_rpms/sample-1.0-1.fc18.noarch.rpm"

        self.tmpdir = tempfile.mkdtemp()
        shutil.copyfile(self.rpm,
                        os.path.join(self.tmpdir, os.path.basename(self.rpm)))

        proc = popen("createrepo_c", "--verbose", self.tmpdir)
        self.assertTrue(b"Workers Finished" in proc.stdout or b"Pool finished" in proc.stdout)

        self.call_action_ordered_args("repoadd", [
            "one_correct_repo", # NAME
            repo_type, # TYPE
            "file:///non/existing", # URL
            "file://{0}".format(self.tmpdir), # URL
        ])

        self.call_action("releaseadd", {
            "opsys": "fedora",
            "opsys-release": "24",
            "status": "ACTIVE",
        })

        self.call_action_ordered_args("repoassign", [
            "one_correct_repo", # NAME
            "Fedora 24", # OPSYS
            "x86_64",# ARCH
        ])

        packages = self.db.session.query(Package).count()
        self.assertEqual(self.call_action("reposync", {
            "NAME": "one_correct_repo",
        }), 0)

        self.assertEqual(packages + 1, self.db.session.query(Package).count())
        shutil.rmtree(self.tmpdir)

    def test_assign_release_to_builds(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.assign_release_to_builds_testing(repo_type)
                self.tearDown()
                self.setUp()

    def assign_release_to_builds_testing(self, repo_type):
        # add repo
        self.assertEqual(self.call_action_ordered_args("repoadd", [
            "sample_repo", # NAME
            repo_type, # TYPE
            "file:///sample_rpms", # URL
        ]), 0)

        # add release
        self.assertEqual(self.call_action("releaseadd", {
            "opsys": "fedora",
            "opsys-release": "24",
            "status": "ACTIVE",
        }), 0)

        # add two builds
        build = Build()
        build.base_package_name = "build"
        build.epoch = 0
        build.version = "1.2.3"
        build.release = "20.fc24"
        self.db.session.add(build)
        self.db.session.flush()

        build_arch = BuildArch(arch_id=self.arch_x86_64.id,
                               build_id=build.id)
        self.db.session.add(build_arch)
        self.db.session.flush()

        build = Build()
        build.base_package_name = "build1"
        build.epoch = 0
        build.version = "1.2.3"
        build.release = "20.fc23"
        self.db.session.add(build)
        self.db.session.flush()

        build_arch = BuildArch(arch_id=self.arch_x86_64.id,
                               build_id=build.id)

        self.db.session.add(build_arch)
        self.db.session.flush()

        systems['fedora'].get_released_builds = get_released_builds_mock

        init_bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        self.assertEqual(self.call_action_ordered_args(
            "assign-release-to-builds", [
            "Fedora", # OPSYS
            "24", # RELEASE
            "x86_64", # ARCH
            "--expression=fc24", # variant
        ]), 0)
        bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        self.assertEqual(bosra, init_bosra + 1)

        self.assertEqual(self.call_action_ordered_args(
            "assign-release-to-builds", [
            "Fedora", # OPSYS
            "24", # RELEASE
            "x86_64", # ARCH
            "--released-builds", # variant
        ]), 0)
        bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        self.assertEqual(bosra, init_bosra + 2)

    def test_clenup_unassigned(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.cleanup_unassigned_testing(repo_type)
                self.tearDown()
                self.setUp()

                self.cleanup_packages_testing_arch(repo_type)
                self.tearDown()
                self.setUp()

    def cleanup_unassigned_testing(self, repo_type):
        self.assign_release_to_builds_testing(repo_type)

        # add package and lob that will not be deleted
        pkg_stay = Package()
        pkg_stay.build = self.db.session.query(Build).first()
        pkg_stay.arch = self.db.session.query(Arch).first()
        pkg_stay.name = "pkg-test-stay"
        self.db.session.add(pkg_stay)
        self.db.session.flush()

        config["storage.lobdir"] = tempfile.mkdtemp(prefix="faf")

        sample_rpm = glob.glob("sample_rpms/sample*.rpm")[0]
        with open(sample_rpm, mode='rb') as sample:
            pkg_stay.save_lob("package", sample, truncate=True)
        self.assertTrue(pkg_stay.has_lob("package"))

        # add build and package and lob that will be deleted
        build = Build()
        build.base_package_name = "build_unassigned"
        build.epoch = 0
        build.version = "1.2.3"
        build.release = "20.fc23"
        self.db.session.add(build)

        pkg_del = Package()
        pkg_del.build = build
        pkg_del.arch = self.db.session.query(Arch).first()
        pkg_del.name = "pkg-test-del"
        self.db.session.add(pkg_del)

        self.db.session.flush()

        sample_rpm = glob.glob("sample_rpms/sample*.rpm")[0]
        with open(sample_rpm, mode='rb') as sample:
            pkg_del.save_lob("package", sample, truncate=True)
        self.assertTrue(pkg_del.has_lob("package"))

        init_bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        self.assertEqual(self.call_action_ordered_args("cleanup-unassigned", [
            "--force"
        ]), 0)

        bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        self.assertEqual(bosra, init_bosra)

        self.assertFalse(pkg_del.has_lob("package"))
        self.assertTrue(pkg_stay.has_lob("package"))

    def test_cleanup_packages(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.cleanup_packages_testing(repo_type)
                self.tearDown()
                self.setUp()

    def cleanup_packages_testing(self, repo_type):
        self.assign_release_to_builds_testing(repo_type)

        # add package and lob
        pkg = Package()
        pkg.build = self.db.session.query(Build).first()
        pkg.arch = self.db.session.query(Arch).first()
        pkg.name = "pkg-test"
        self.db.session.add(pkg)
        self.db.session.flush()

        config["storage.lobdir"] = "/tmp/faf_test_data/lob"
        sample_rpm = glob.glob("sample_rpms/sample*.rpm")[0]
        with open(sample_rpm, mode='rb') as sample:
            pkg.save_lob("package", sample, truncate=True)
        self.assertTrue(pkg.has_lob("package"))

        init_bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        self.assertEqual(self.call_action_ordered_args("cleanup-packages", [
            "Fedora", # OPSYS
            "24", # RELEASE
        ]), 0)

        bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        self.assertEqual(bosra, init_bosra - 2)

        self.assertFalse(pkg.has_lob("package"))

    def cleanup_packages_testing_arch(self, repo_type):
        self.assign_release_to_builds_testing(repo_type)

        # add package and lob
        pkg = Package()
        pkg.build = self.db.session.query(Build).first()
        pkg.arch = self.db.session.query(Arch).first()
        pkg.name = "pkg-test"
        self.db.session.add(pkg)
        self.db.session.flush()

        config["storage.lobdir"] = tempfile.mkdtemp(prefix="faf")
        sample_rpm = glob.glob("sample_rpms/sample*.rpm")[0]
        with open(sample_rpm, mode='rb') as sample:
            pkg.save_lob("package", sample, truncate=True)
        self.assertTrue(pkg.has_lob("package"))

        init_bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        self.assertEqual(self.call_action("cleanup-packages", {
            "arch": "noarch",
        }), 0)

        bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        self.assertEqual(bosra, init_bosra)

        self.assertEqual(self.call_action("cleanup-packages", {
            "arch": "x86_64",
        }), 0)

        bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        self.assertEqual(bosra, init_bosra - 2)

        self.assertFalse(pkg.has_lob("package"))


    def test_delete_invalid_ureports(self):
        # try to delete from empty table
        self.assertEqual(self.call_action("delete-invalid-ureports", {
            "age": "6",
        }), 0)

        # add invalid ureport and lob
        inv_ureport = InvalidUReport()
        inv_ureport.errormsg = "fedora"
        # 3 days old
        current_time = datetime.utcnow()
        inv_ureport.date = current_time - timedelta(days=3)
        self.db.session.add(inv_ureport)
        self.db.session.flush()

        config["storage.lobdir"] = "/tmp/faf_test_data/lob"
        sample_ureport = "sample_reports/ureport_core_invalid"
        with open(sample_ureport, mode='rb') as sample:
            inv_ureport.save_lob("ureport", sample, truncate=True)
        self.assertTrue(inv_ureport.has_lob("ureport"))

        # try to remove older than we have in the table, nothing should happen
        tbl_size_before = self.db.session.query(InvalidUReport).count()
        self.assertEqual(self.call_action("delete-invalid-ureports", {
            "age": "4",
        }), 0)

        tbl_size_after = self.db.session.query(InvalidUReport).count()
        self.assertEqual(tbl_size_after, tbl_size_before)
        self.assertTrue(inv_ureport.has_lob("ureport"))

        # remove correctly, at the time of call, our table entry is
        # slightly older than 3 days
        tbl_size_before = self.db.session.query(InvalidUReport).count()
        self.assertEqual(self.call_action("delete-invalid-ureports", {
            "age": "3",
        }), 0)

        tbl_size_after = self.db.session.query(InvalidUReport).count()
        self.assertEqual(tbl_size_after, tbl_size_before - 1)
        self.assertFalse(inv_ureport.has_lob("ureport"))

        # negative age argument, should fail
        self.assertEqual(self.call_action("delete-invalid-ureports", {
            "age": "-4",
        }), 1)

    def test_releasemod(self):

        # add F20 release
        self.assertEqual(self.call_action("releaseadd", {
            "opsys": "fedora",
            "opsys-release": "20",
            "status": "EOL",
        }), 0)

        self.assertEqual(self.call_action("releasemod", {
            "opsys": "fedora",
            "opsys-release": 20,
            "status": "ACTIVE",
        }), 0)

        self.assertEqual(self.call_action("releasemod", {
            "opsys": "fedora",
            "opsys-release": 20,
            "status": "ACTIVE",
        }), 0)

        self.assertEqual(self.call_action("releasemod", {
            "opsys": "fedora",
            "opsys-release": 20,
            "status": "EOL",
        }), 0)

    def test_kb(self):
        self.assertEqual(self.call_action("sf-prefilter-soladd", {
            "CAUSE": "VLC Media Player",
            "NOTE": "VLC unsupported.",
            "note-html": "<html><b>VLC unsupported.</b><html>",
            "url": "http://www.fedoraproject.org",
        }), 0)

        self.assertEqual(self.call_action("sf-prefilter-soladd", {
            "CAUSE": "VLC Media Player",
            "NOTE": "VLC unsupported.",
            "note-html": "<html><b>VLC unsupported.</b><html>",
            "url": "http://www.fedoraproject.org",
        }), 0)

        self.assertEqual(self.call_action("sf-prefilter-soladd", {
            "CAUSE": "Unsupported",
            "NOTE": "Unsupported",
            "note-html": "<html><b>Unsupported</b><html>",
            "url": "http://www.fedoraproject.org",
        }), 0)

        self.assertEqual(self.call_action("sf-prefilter-patadd", {
            "SOLUTION": "FooSolution",
            "btpath": "^.*/systemd-logind$",
        }), 1)

        self.assertEqual(self.call_action("sf-prefilter-patadd", {
            "SOLUTION": "FooSolution",
            "opsys": "fedora",
            "btpath": "^.*/systemd-logind$",
        }), 1)

        self.assertEqual(self.call_action("sf-prefilter-patadd", {
            "SOLUTION": "Unsupported",
            "opsys": "fedora",
            "btpath": "^.*/systemd-logind$",
        }), 0)

        self.assertEqual(self.call_action("sf-prefilter-patadd", {
            "SOLUTION": "Unsupported",
            "opsys": "fedora",
            "pkgname": "^ibus-table",
        }), 0)

        sample_report_names = ("ureport1", "ureport2", "ureport_core",
                               "ureport_python", "ureport_kerneloops",
                               "ureport_java", "ureport_ruby")
        sample_reports = {}
        for report_name in sample_report_names:
            with open("sample_reports/{0}".format(report_name), "r") as file:
                sample_reports[report_name] = json.load(file)

        solution = find_solution(sample_reports['ureport_core'])
        self.assertIsNotNone(solution)
        self.assertEqual(solution.cause, "Unsupported")

        solution = find_solution(sample_reports['ureport_python'])
        self.assertIsNotNone(solution)
        self.assertEqual(solution.cause, "Unsupported")

        solution = find_solution(sample_reports['ureport_java'])
        self.assertIsNone(solution)

    def test_check_repo(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.check_repo_testing(repo_type)
                self.tearDown()
                self.setUp()

    def check_repo_testing(self, repo_type):
        self.rpm = glob.glob("sample_rpms/sample*.rpm")[0]

        self.tmpdir = tempfile.mkdtemp()
        shutil.copyfile(self.rpm,
                        os.path.join(self.tmpdir, os.path.basename(self.rpm)))

        proc = popen("createrepo_c", "--verbose", self.tmpdir)
        self.assertTrue(b"Workers Finished" in proc.stdout or b"Pool finished" in proc.stdout)

        self.call_action_ordered_args("repoadd", [
            "repo_file", # NAME
            repo_type, # TYPE
            "file:///non/existing", # URL
            "file://{0}".format(self.tmpdir), # URL
        ])
        self.assertEqual(self.call_action("check-repo"), 0)
        self.assertIn("'repo_file' is not assigned with OpSys release",
                      self.action_stdout)

        self.call_action("releaseadd", {
            "opsys": "fedora",
            "opsys-release": "24",
            "status": "ACTIVE",
        })

        self.call_action_ordered_args("repoassign", [
            "repo_file", # NAME
            "Fedora 24", # OPSYS
        ])

        self.assertEqual(self.call_action("check-repo"), 0)
        self.assertIn("'repo_file' is not assigned with architecture",
                      self.action_stdout)

        self.call_action_ordered_args("repoassign", [
            "repo_file", # NAME
            "x86_64",# ARCH
        ])

        self.assertEqual(self.call_action("check-repo"), 0)
        self.assertIn("Everything is OK!", self.action_stdout)

        self.call_action_ordered_args("repoadd", [
            "fail_repo", # NAME
            repo_type, # TYPE
            "file:///non/existing", # URL
        ])
        self.assertEqual(self.call_action("check-repo"), 0)
        self.assertIn("'fail_repo' does not have a valid url",
                      self.action_stdout)

        tmpdir = tempfile.mkdtemp()
        proc = popen("createrepo_c", "--verbose", tmpdir)

        self.assertTrue(b"Workers Finished" in proc.stdout or b"Pool finished" in proc.stdout)

        handler_class = functools.partial(http.server.SimpleHTTPRequestHandler,
                                          directory=tmpdir)

        with http.server.HTTPServer(('localhost', 8080), handler_class) as server:
            server_thread = threading.Thread(target=server.serve_forever)

            server_thread.daemon = True
            server_thread.start()

            self.call_action_ordered_args("repoadd", [
                "remote_repo",
                repo_type,
                ("http://%s:%d/" % (server.server_address[0], server.server_address[1])),
            ])

            self.call_action_ordered_args("repoassign", [
                "remote_repo",
                "Fedora 24",
                "x86_64",
            ])

            self.assertEqual(self.call_action("check-repo",
                                              {"REPONAME" :"remote_repo"}),
                             0)
            self.assertIn("Everything is OK!", self.action_stdout)

            server.shutdown()

        shutil.rmtree(tmpdir)

        self.assertEqual(self.call_action("check-repo",
                                          {"REPONAME" :"unknown_name"}),
                         0)

        self.assertIn("Repository 'unknown_name' does not exists",
                      self.action_stdout)

        self.call_action_ordered_args("repoadd", [
            "remote_repo_unknown", # NAME
            repo_type, # TYPE
            "http://unknow_repo.com/", # URL
        ])

        self.assertEqual(self.call_action("check-repo",
                                          {"REPONAME" :"remote_repo_unknown"}),
                         0)
        self.assertIn("'remote_repo_unknown' does not have a valid url",
                      self.action_stdout)

        shutil.rmtree(self.tmpdir)

    def test_sar(self):
        # faker1
        self.create_user(usrnum=1)
        self.create_bugzilla_user(bzuid=1)
        self.create_bugzilla(bugid=1, bzuid=1)
        self.create_report(rid=1)
        self.create_contact_email_report(emailid=1, usruid=1)
        # faker2
        self.create_user(usrnum=2)
        self.create_bugzilla_user(bzuid=2)
        self.create_bugzilla(bugid=2, bzuid=2)
        self.create_report(rid=2)
        self.create_contact_email_report(emailid=2, usruid=2)
        self.db.session.flush()

        self.assertEqual(self.call_action('sar'), 1)
        self.assertIn('SAR_USERNAME, SAR_EMAIL were not set',
                      self.action_stdout)

        os.environ['SAR_USERNAME'] = 'faker1'
        self.assertEqual(self.call_action('sar'), 0)
        json_data = json.loads(self.action_stdout)
        self.assert_correct_sar_output(json_data, 'faker1@localhost', 1)

        os.environ['SAR_EMAIL'] = 'faker2@localhost'
        self.assertEqual(self.call_action('sar'), 0)
        json_data = json.loads(self.action_stdout)
        self.assert_correct_sar_output(json_data, 'faker2@localhost', 2)

    def test_releasedel(self):
        for repo_type in repo_types:
            if repo_type in self.preferred_repo_types:
                self.releasedel_testing(repo_type)
                self.tearDown()
                self.setUp()

    def releasedel_testing(self, repo_type):
        self.assertEqual(self.call_action("releasedel", {
            "opsys": "fedora",
            "opsys-release": "1337",
        }), 1)

        # add release f24 and assign two builds
        self.assign_release_to_builds_testing(repo_type)

        # assign sample_repo to f24 release (sample_repo comes from ^^^)
        self.assertEqual(self.call_action_ordered_args("repoassign", [
            "sample_repo",  # NAME
            "Fedora 24",  # OPSYS
            "x86_64",  # ARCH
        ]), 0)

        tracker = Bugtracker(name="fedora-bugzilla")
        self.db.session.add(tracker)

        self.save_report('ureport_f20')
        self.save_report('ureport_core')
        self.call_action("create-problems")

        bzuser = BzUser(name="Fake user",
                        email="fake@example.org",
                        real_name="Fake name",
                        can_login=False)

        self.db.session.add(bzuser)

        bug = BzBug()
        bug.id = 123456
        bug.summary = "Fake bug"
        bug.status = "NEW"
        bug.creation_time = datetime.now()
        bug.last_change_time = datetime.now()
        bug.whiteboard = "empty"
        bug.tracker = tracker
        bug.creator = bzuser
        bug.component = self.comp_faf
        bug.opsysrelease = self.release_20
        bug.private = False

        self.db.session.add(bug)

        # add package and lob that will be deleted
        pkg_del = Package()
        pkg_del.build = self.db.session.query(Build).first()
        pkg_del.arch = self.db.session.query(Arch).first()
        pkg_del.name = "pkg-test-del"
        self.db.session.add(pkg_del)
        self.db.session.flush()

        config["storage.lobdir"] = tempfile.mkdtemp(prefix="faf")

        sample_rpm = glob.glob("sample_rpms/sample*.rpm")[0]
        with open(sample_rpm, mode='rb') as sample:
            pkg_del.save_lob("package", sample, truncate=True)
        self.assertTrue(pkg_del.has_lob("package"))

        # add build and package and lob that will not be deleted
        build = Build()
        build.base_package_name = "build_unassigned"
        build.epoch = 0
        build.version = "1.2.3"
        build.release = "20.fc23"
        self.db.session.add(build)

        pkg_stay = Package()
        pkg_stay.build = build
        pkg_stay.arch = self.db.session.query(Arch).first()
        pkg_stay.name = "pkg-test-stay"
        self.db.session.add(pkg_stay)
        self.db.session.flush()

        sample_rpm = glob.glob("sample_rpms/sample*.rpm")[0]
        with open(sample_rpm, mode='rb') as sample:
            pkg_stay.save_lob("package", sample, truncate=True)
        self.assertTrue(pkg_stay.has_lob("package"))

        init_bosra = self.db.session.query(BuildOpSysReleaseArch).count()
        bosra = self.db.session.query(BuildOpSysReleaseArch).count()

        # delete release f24 with assigned repos and builds with lobs
        self.assertEqual(self.call_action("releasedel", {
            "opsys": "fedora",
            "opsys-release": "24",
        }), 0)

        self.assertEqual(bosra, init_bosra)
        self.assertTrue(pkg_stay.has_lob("package"))
        self.assertFalse(pkg_del.has_lob("package"))

        self.assertEqual(self.db.session.query(Report).count(), 2)
        self.assertEqual(self.db.session.query(Problem).count(), 2)

        # delete release f20 with assigned bugs, reports and problems
        self.assertEqual(self.call_action("releasedel", {
            "opsys": "fedora",
            "opsys-release": "20",
        }), 0)

        self.assertEqual(self.db.session.query(Report).count(), 0)
        self.assertEqual(self.db.session.query(Problem).count(), 0)

        # attempt to delete deleted release f20
        self.assertEqual(self.call_action("releasedel", {
            "opsys": "fedora",
            "opsys-release": "20",
        }), 1)

def get_released_builds_mock(release):
    return [
        {"name": "build1",
         "epoch": "0",
         "version": "1.2.3",
         "release": "20.fc23",
         "nvr": "build1-1.2.3-20.fc23",
         "completion_time": datetime.now()-timedelta(days=2)
         }]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
