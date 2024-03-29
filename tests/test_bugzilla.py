#!/usr/bin/python3
# -*- encoding: utf-8 -*-
import unittest
import logging
import datetime

import faftests
from faftests import mockzilla

from pyfaf.common import FafError
from pyfaf.bugtrackers import bugzilla

from pyfaf.storage.bugtracker import Bugtracker
from pyfaf.storage.opsys import (OpSysComponent,
                                 OpSysRelease,
                                 OpSysReleaseComponent)


class BugzillaTestCase(faftests.DatabaseCase):
    """
    Tests bugzilla functionality.
    """
    def setUp(self):
        """
        Set up bugzilla instance with mockzilla.
        """

        super(BugzillaTestCase, self).setUp()

        self.basic_fixtures()

        tracker = Bugtracker(name="fakebugzilla")
        self.db.session.add(tracker)
        self.db.session.flush()

        cls = bugzilla.Bugzilla
        cls.name = "fakebugzilla"
        self.bz = cls()
        self.mz = mockzilla.Mockzilla()
        self.bz.bz = self.mz
        self.bz.connected = True

    def create_dummy_bug(self):
        """
        Create dummy bug with pre-defined values.
        """
        bug = dict(
            component="will-crash",
            product="Fedora",
            version="17",
            summary="Crashed...",
            description="Desc",
            status_whiteboard="abrt_hash:123 reports:15",
            groups="")
        self.bz.create_bug(**bug)

    def test_config_loading(self):
        """
        Make sure that configuration is loaded properly on init
        """

        self.assertEqual(self.bz.api_url, "http://fake_test_api_url")
        self.assertEqual(self.bz.web_url, "http://fake_test_web_url")
        self.assertEqual(self.bz.api_key, "FAKE_API_KEY_QR43290T4V743BN")

    def test_query_bugs(self):
        """
        Check if bugzilla query uses correct parameters.
        """
        from_date = datetime.date(2013, 1, 1)
        to_date = from_date + datetime.timedelta(days=1)
        self.bz._query_bugs(to_date, from_date,
                            limit=1, offset=1,
                            custom_fields=dict(test=True))

        params = self.mz.last_query_params
        self.assertEqual(params["chfieldfrom"], "2013-01-01")
        self.assertEqual(params["chfieldto"], "2013-01-02")
        self.assertEqual(params["test"], True)

    def test_list_bugs(self):
        """
        Check if list_bugs works correctly.
        """
        self.create_dummy_bug()

        from_date = datetime.date(2013, 1, 1)
        to_date = from_date + datetime.timedelta(days=7)
        ret = list(self.bz.list_bugs(
            to_date=to_date,
            from_date=from_date,
            step=2,
            stop_after_empty_steps=1))

        self.assertEqual(len(ret), 1)

        params = self.mz.last_query_params
        self.assertEqual(params["chfieldfrom"], "2013-01-04")
        self.assertEqual(params["chfieldto"], "2013-01-05")

    def test_preprocess_bug(self):
        """
        Check if preprocess_bug returns correct data.
        """
        self.create_dummy_bug()
        bug = self.mz.bugs[1]
        bug.resolution = 'DUPLICATE'
        bug.dupe_id = '15'
        processed = self.bz.preprocess_bug(bug)

        self.assertIs(type(processed), dict)
        self.assertIn('history', processed)
        self.assertEqual(processed['dupe_id'], '15')

    def test_preprocess_bug_returns_none_on_missing_data(self):
        """
        Check if process_bug returns None in case of missing fields.
        """
        self.assertIsNone(self.bz.preprocess_bug(None))

    def test_user_handling(self):
        """
        Check if user downloading and saving works correctly.
        """
        user = self.bz._download_user("user@example.org")
        dbuser = self.bz._save_user(self.db, user)
        self.assertEqual(dbuser.id, user.userid)
        self.assertEqual(dbuser.name, user.name)
        self.assertEqual(dbuser.email, user.email)
        self.assertEqual(dbuser.can_login, user.can_login)
        self.assertEqual(dbuser.real_name, user.real_name)

    def test_save_user_handles_email_changes(self):
        """
        Check if _save_user can match users based on userid.
        """
        user = self.bz._download_user("user@example.org")
        dbuser1 = self.bz._save_user(self.db, user)
        user.email = "changed@example.org"
        dbuser2 = self.bz._save_user(self.db, user)
        self.assertEqual(dbuser1, dbuser2)
        self.assertEqual(dbuser1.id, dbuser2.id)
        self.assertEqual(dbuser1.email, "changed@example.org")

    def test_user_handling_no_email(self):
        """
        Check if download user returns None if no user email
        is supplied

        Can happen if bugzilla is used without credentials
        """
        user = self.bz._download_user("Johny Has No Email")
        self.assertIsNone(user)

    def test_bug_handling(self):
        """
        Check if bug downloading and saving works correctly.
        """
        self.bz.save_comments = True
        self.bz.save_attachments = True
        self.create_dummy_bug()
        dbbug = self.bz.download_bug_to_storage(self.db, 1)
        self.assertIsNotNone(dbbug)
        self.assertEqual(len(dbbug.ccs), 1)
        self.assertEqual(len(dbbug.history), 1)
        self.assertEqual(len(dbbug.attachments), 1)
        self.assertEqual(len(dbbug.comments), 1)

        com = dbbug.comments.pop()
        att = dbbug.attachments.pop()

        self.assertEqual(com.attachment, att)

    def test_save_bug_updates_bugs(self):
        """
        Check if _save_bug updates bug when last change time
        differs.
        """
        self.create_dummy_bug()
        downloaded = self.bz.bz.getbug(1)
        dbbug = self.bz._save_bug(self.db, downloaded)
        downloaded['last_change_time'] += datetime.timedelta(days=1)
        downloaded['status'] = 'ON_QA'

        dbbug2 = self.bz._save_bug(self.db, downloaded)
        self.assertEqual(dbbug, dbbug2)
        self.assertEqual(dbbug2.status, 'ON_QA')
        self.assertEqual(dbbug2.last_change_time.day, downloaded['last_change_time'].day)

    def test_save_bug_missing_component(self):
        """
        Check if download_bug_to_storage raises error
        if there's missing component.
        """
        self.db.session.query(OpSysReleaseComponent).delete()
        self.db.session.query(OpSysComponent).delete()
        self.create_dummy_bug()
        with self.assertRaises(FafError):
            self.bz.download_bug_to_storage(self.db, 1)


    def test_save_bug_missing_release(self):
        """
        Check if download_bug_to_storage raises error
        if there's missing OpSysRelease.
        """
        self.db.session.query(OpSysReleaseComponent).delete()
        self.db.session.query(OpSysRelease).delete()
        self.create_dummy_bug()
        with self.assertRaises(FafError):
            self.bz.download_bug_to_storage_no_retry(self.db, 1)

    def test_save_bug_missing_tracker(self):
        """
        Check if download_bug_to_storage raises error
        if tracker is not installed.
        """
        self.db.session.query(Bugtracker).delete()
        self.create_dummy_bug()
        with self.assertRaises(FafError):
            self.bz.download_bug_to_storage_no_retry(self.db, 1)

    def test_comment_handling(self):
        """
        Check if comments are saved correctly.
        """
        self.bz.save_comments = True
        self.create_dummy_bug()
        dbbug = self.bz.download_bug_to_storage_no_retry(self.db, 1)

        comment = dbbug.comments.pop()
        self.assertEqual(comment.id, self.mz.comment.id)
        self.assertEqual(comment.user.email, self.mz.comment.creator)
        self.assertEqual(comment.is_private, self.mz.comment.is_private)
        self.assertEqual(comment.creation_time, self.mz.comment.time)

    def test_cc_handling(self):
        """
        Check if CCs are saved correctly.
        """
        self.create_dummy_bug()
        dbbug = self.bz.download_bug_to_storage_no_retry(self.db, 1)

        cc = dbbug.ccs.pop()
        self.assertEqual(cc.user.email, self.mz.user.email)

    def test_history_handling(self):
        """
        Check if history events are saved correctly.
        """
        self.create_dummy_bug()
        dbbug = self.bz.download_bug_to_storage_no_retry(self.db, 1)

        event = dbbug.history.pop()
        orig = self.mz.history_event
        self.assertEqual(event.user.email, orig.who)
        self.assertEqual(event.time, orig.when)
        self.assertEqual(event.field, orig.changes[0].field_name)
        self.assertEqual(event.added, orig.changes[0].added)
        self.assertEqual(event.removed, orig.changes[0].removed)

    def test_attachment_handling(self):
        """
        Check if attachments are saved correctly.
        """
        self.bz.save_attachments = True
        self.create_dummy_bug()
        dbbug = self.bz.download_bug_to_storage_no_retry(self.db, 1)

        new = dbbug.attachments.pop()
        orig = self.mz.attachment
        self.assertEqual(new.user.email, orig.attacher)
        self.assertEqual(new.mimetype, orig.content_type)
        self.assertEqual(new.description, orig.description)
        self.assertEqual(new.filename, orig.file_name)
        self.assertEqual(new.is_private, orig.is_private)
        self.assertEqual(new.is_patch, orig.is_patch)
        self.assertEqual(new.is_obsolete, orig.is_obsolete)
        self.assertEqual(new.creation_time, orig.creation_time)
        self.assertEqual(new.last_change_time, orig.last_change_time)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
