#!/usr/bin/python
# -*- encoding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from flask import json
from webfaftests import WebfafTestCase
import pyfaf.storage as storage
from pyfaf.utils.user import UserDataDumper


class UserTestCase(WebfafTestCase):
    """
    Tests for webfaf.user
    """

    def setUp(self):
        super(UserTestCase, self).setUp()
        self.basic_fixtures()
        self.create_user(usrnum=1)
        self.create_bugzilla_user(bzuid=1)
        self.create_bugzilla(bugid=1, bzuid=1)
        self.create_report(rid=1)
        self.create_contact_email_report(emailid=1, usruid=1)
        self.db.session.commit()

        with self.app.session_transaction() as session:
            session['openid'] = 'faker1'

    def test_delete_user_data(self):
        """
        Test deletion of user data stored in database.
        """
        self.assertEqual(self.db.session.query(storage.User).count(), 1)

        with self.app as tc:
            r = tc.get('/delete_data')
            self.assertEqual(r.status_code, 302)

            self.assertIsNone(self.db.session.query(storage.BzUser)
                              .filter(storage.BzUser.email == 'faker1@localhost')
                              .first())

            self.assertIsNotNone(self.db.session.query(storage.BzUser)
                                 .filter(storage.BzUser.email == 'anonymous')
                                 .first())
            self.assertEqual(self.db.session.query(storage.BzUser).count(), 1)

            bzbug = self.db.session.query(storage.BzBug).first()
            self.assertEqual(bzbug.creator_id, -1)

            self.assertIsNone(self.db.session.query(storage.ContactEmail).first())
            self.assertIsNone(self.db.session.query(storage.User)
                              .filter(storage.User.mail == 'faker1@locahost')
                              .first())

    def test_delete_no_data_from_different_user(self):
        """
        Test deletion of user data of one user without affecting other users.
        """
        self.create_user(usrnum=22)
        self.create_bugzilla_user(bzuid=22)
        self.create_bugzilla(bugid=22, bzuid=22)
        self.create_report(22)
        self.create_contact_email_report(emailid=22, usruid=22)
        self.db.session.commit()

        self.assertEqual(self.db.session.query(storage.User).count(), 2)

        with self.app as tc:
            r = tc.get('/delete_data')
            self.assertEqual(r.status_code, 302)

            self.assertIsNone(self.db.session.query(storage.User)
                              .filter(storage.User.mail == 'faker1@localhost')
                              .first())
            self.assertIsNotNone(self.db.session.query(storage.User)
                                 .filter(storage.User.mail == 'faker22@localhost')
                                 .first())

            self.assertIsNone(self.db.session.query(storage.BzUser)
                              .filter(storage.BzUser.email == 'faker1@localhost')
                              .first())
            self.assertIsNotNone(self.db.session.query(storage.BzUser)
                                 .filter(storage.BzUser.email == 'anonymous')
                                 .first())
            self.assertEqual(self.db.session.query(storage.BzUser).count(), 2)

            self.assertEqual(self.db.session.query(storage.BzBug).count(), 2)
            bzbug = (self.db.session.query(storage.BzBug)
                     .filter(storage.BzBug.id == 1)
                     .first())
            self.assertEqual(bzbug.creator_id, -1)

            bzbug = (self.db.session.query(storage.BzBug)
                     .filter(storage.BzBug.id == 22)
                     .first())
            self.assertEqual(bzbug.creator_id, 22)

            self.assertEqual(self.db.session.query(storage.ContactEmail).count(), 1)

    def test_download_user_data(self):
        """
        Test download of user data stored in database, the information is returned
        in json format.
        """
        user = (self.db.session.query(storage.User)
                .filter(storage.User.mail == 'faker1@localhost')
                .first())

        r = self.app.get('/download_data')
        self.assertEqual(r.status_code, 200)

        json_data = json.loads(r.data)
        self.assertEqual(json_data["Username"], user.username)
        self.assertEqual(json_data["Mail"], user.mail)

        bg = json_data["Bugzilla"]
        self.assertEqual(bg["Name"], user.mail)
        self.assertEqual(bg["Mail"], user.mail)
        self.assertEqual(bg["Created Bugzillas"][0]["Bug ID"], 1)
        self.assertEqual(bg["Created Bugzillas"][0]["Status"], "CLOSED")
        self.assertEqual(bg["History"][0]["Bug ID"], 1)
        self.assertEqual(bg["History"][0]["Added"], "POST")
        self.assertEqual(bg["History"][0]["Removed"], "NEW")
        self.assertEqual(bg["Comments"][0]["Bug ID"], 1)
        self.assertEqual(bg["Comments"][0]["Comment #"], 1)
        self.assertEqual(bg["Attachments"][0]["Bug ID"], 1)
        self.assertEqual(bg["Attachments"][0]["Filename"], "fake_filename.json")
        self.assertIn(1, bg["CCs"])

        self.assertEqual(json_data["Contact Mail Reports"]["Contact Mail"], user.mail)
        self.assertEqual(json_data["Contact Mail Reports"]["Reports"][0], "1")


if __name__ == "__main__":
    unittest.main()
