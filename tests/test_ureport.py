#!/usr/bin/python
# -*- encoding: utf-8 -*-
import json
import datetime

try:
    import unittest2 as unittest
except ImportError:
    import unittest
import logging

import faftests

from pyfaf.config import config
from pyfaf.bugtrackers import bugtrackers
from pyfaf.ureport import (attachment_type_allowed,
                           save,
                           save_attachment,
                           validate,
                           validate_attachment)

from pyfaf.storage.report import Report, ContactEmail
from pyfaf.storage.bugtracker import Bugtracker
from pyfaf.storage.bugzilla import BzBug, BzUser


class UreportTestCase(faftests.DatabaseCase):
    """
    Tests ureport processing functionality.
    """

    def setUp(self):
        """
        Add required stuff to the database
        """

        super(UreportTestCase, self).setUp()
        self.basic_fixtures()

        tracker = Bugtracker(name="fedora-bugzilla")
        self.db.session.add(tracker)

        bzuser = BzUser(name="Fake user",
                        email="fake@example.org",
                        real_name="Fake name",
                        can_login=False)

        self.db.session.add(bzuser)

        bug = BzBug()
        bug.id = 123456
        bug.summary = "Fake bug"
        bug.status = "NEW"
        bug.creation_time = datetime.datetime.now()
        bug.last_change_time = datetime.datetime.now()
        bug.whiteboard = "empty"
        bug.tracker = tracker
        bug.creator = bzuser
        bug.component = self.comp_faf
        bug.opsysrelease = self.release_20
        bug.private = False

        self.bug = bug
        self.db.session.add(bug)
        self.db.session.flush()

        self.sample_report_names = (
            "ureport1", "ureport2", "ureport_core", "ureport_python",
            "ureport_kerneloops", "ureport_java", "ureport_ruby",
            "ureport_kerneloops_nouveau")
        self.sample_reports = {}

        for report_name in self.sample_report_names:
            with open("sample_reports/{0}".format(report_name), "r") as file:
                self.sample_reports[report_name] = json.load(file)

        with open("sample_reports/bugzilla_attachment", "r") as file:
            self.bugzilla_attachment = json.load(file)

        with open("sample_reports/comment_attachment", "r") as file:
            self.comment_attachment = json.load(file)

        with open("sample_reports/contact_email_attachment", "r") as file:
            self.contact_email_attachment = json.load(file)

        with open("sample_reports/url_attachment", "r") as file:
            self.url_attachment = json.load(file)

    def test_ureport_validation(self):
        """
        Check if ureport validation works correctly
        for both versions.
        """

        # validate raises FafError on failure
        for report_name in self.sample_report_names:
            validate(self.sample_reports[report_name])

    def test_ureport_saving(self):
        """
        Check if ureport saving works correctly.
        """

        # save raises FafError on failure
        for report_name in self.sample_report_names:
            save(self.db, self.sample_reports[report_name])

    def test_attachment_validation(self):
        """
        Check if attachment validation works correctly.
        """

        validate_attachment(self.bugzilla_attachment)

    def test_attachment_saving(self):
        """
        Check if bugzilla attachment is added to report.
        """

        save(self.db, self.sample_reports['ureport2'])
        report = self.db.session.query(Report).first()

        # update hash locally
        reporthash = report.hashes[0].hash
        bz_attachment = self.bugzilla_attachment
        bz_attachment["bthash"] = reporthash

        class MockBugtracker(object):
            def download_bug_to_storage(db, bug_id):
                return self.bug

        bugtrackers["fedora-bugzilla"] = MockBugtracker()

        save_attachment(self.db, bz_attachment)
        self.assertEqual(len(report.bz_bugs), 1)

    def test_attachment_type_allowed(self):
        config["ureport.acceptattachments"] = "only_this"

        self.assertTrue(attachment_type_allowed("only_this"))
        self.assertFalse(attachment_type_allowed("not_this"))

        config["ureport.acceptattachments"] = "*"
        self.assertTrue(attachment_type_allowed("anything"))


    def test_comment_saving(self):
        """
        Check if comment attachment is added to report.
        """

        save(self.db, self.sample_reports['ureport2'])
        report = self.db.session.query(Report).first()

        # update hash locally
        reporthash = report.hashes[0].hash
        com_attachment = self.comment_attachment
        com_attachment["bthash"] = reporthash

        save_attachment(self.db, com_attachment)
        self.assertEqual(len(report.comments), 1)

    def test_contact_email_saving(self):
        """
        Check if comment attachment is added to report.
        """

        save(self.db, self.sample_reports['ureport2'])
        report = self.db.session.query(Report).first()

        # update hash locally
        reporthash = report.hashes[0].hash
        contact_email_attachment = self.contact_email_attachment
        contact_email_attachment["bthash"] = reporthash

        save_attachment(self.db, contact_email_attachment)
        self.assertEqual(len(report.report_contact_emails), 1)
        self.assertEqual(len(self.db.session.query(ContactEmail).all()), 1)
        self.assertEqual(report.report_contact_emails[0].contact_email.email_address,
                         contact_email_attachment["data"])

        # saving it twice should have no effect
        save_attachment(self.db, contact_email_attachment)
        self.assertEqual(len(report.report_contact_emails), 1)
        self.assertEqual(len(self.db.session.query(ContactEmail).all()), 1)

    def test_url_saving(self):
        """
        Check if URL attachment is added to report.
        """

        save(self.db, self.sample_reports['ureport2'])
        report = self.db.session.query(Report).first()

        # update hash locally
        reporthash = report.hashes[0].hash
        url_attachment = self.url_attachment
        url_attachment["bthash"] = reporthash

        save_attachment(self.db, url_attachment)
        self.assertEqual(len(report.urls), 1)
        self.assertEqual(report.urls[0].url, 'http://example.org')
        self.assertIsNotNone(report.urls[0].saved)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
