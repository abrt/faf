# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
#
# This file is part of faf.
#
# faf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# faf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with faf.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import unicode_literals

import time
import datetime
import xmlrpc.client # type: ignore

from typing import Any, Dict, Generator, List, Optional, Union


import bugzilla
from bugzilla.bug import Bug, User

from pyfaf import queries
from pyfaf.common import FafError, FafConfigError
from pyfaf.utils.decorators import retry
from pyfaf.utils.date import daterange

from pyfaf.storage import column_len, Database
from pyfaf.storage.bugzilla import (BzBug,
                                    BzUser,
                                    BzBugCc,
                                    BzComment,
                                    BzAttachment,
                                    BzBugHistory)

from pyfaf.bugtrackers import BugTracker
from pyfaf.utils.parse import str2bool

__all__ = ["Bugzilla"]


class Bugzilla(BugTracker):
    """
    Proxy over python-bugzilla library handling bug downloading,
    creation and updates.
    """

    name = "abstract_bugzilla"

    report_backref_name = "bz_bugs"

    api_url: Optional[str] = None
    web_url: Optional[str] = None
    new_bug_url: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    save_comments: bool = False
    save_attachments: bool = False

    connected: bool = False

    def __init__(self) -> None:
        """
        Load required configuration based on instance name.
        """

        super().__init__()

        # load config for corresponding bugzilla (e.g. fedorabz.api_url,
        # rhelbz.user, xyzbz.password)
        self.load_config_to_self("api_url", f"{self.name}.api_url")
        self.load_config_to_self("web_url", f"{self.name}.web_url")
        self.load_config_to_self("new_bug_url", f"{self.name}.new_bug_url")
        self.load_config_to_self("user", f"{self.name}.user")
        self.load_config_to_self("password", f"{self.name}.password")
        self.load_config_to_self("save_comments", f"{self.name}.save_comments",
                                 False, callback=str2bool)
        self.load_config_to_self("save_attachments", f"{self.name}.save_attachments",
                                 False, callback=str2bool)

    def connect(self) -> None:
        if self.connected:
            return

        if not self.api_url:
            raise FafConfigError(
                "No api_url specified for '{0}' bugzilla instance"
                .format(self.name))

        self.log_debug("Opening bugzilla connection for '%s'", self.name)

        self.bz = bugzilla.Bugzilla(url=str(self.api_url), cookiefile=None,
                                    tokenfile=None)

        if self.user and self.password:
            self.log_debug("Logging into bugzilla '%s' as '%s'", self.name, self.user)

            self.bz.login(self.user, self.password)
        else:
            self.log_warn("No user and password specified for '{0}' bugzilla"
                          "instance, using anonymously")

        self.connected = True

    def download_bug_to_storage_no_retry(self, db: Database, bug_id: int) -> BzBug:
        """
        Download and save single bug identified by `bug_id`.
        """

        self.log_debug(u"Downloading bug #%d", bug_id)
        self.connect()
        try:
            if self.save_attachments:
                bug = self.bz.getbug(bug_id, extra_fields='attachments')
            else:
                bug = self.bz.getbug(bug_id)
        except xmlrpc.client.Fault as ex:
            if int(ex.faultCode) == 102:
                # Access denied to a private bug
                raise FafError(ex.faultString) from ex
            raise
        return self._save_bug(db, bug)

    @retry(3, delay=10, backoff=3, verbose=True)
    def download_bug_to_storage(self, db: Database, bug_id: int) -> BzBug:
        return self.download_bug_to_storage_no_retry(db, bug_id)

    def list_bugs(self, *args, **kwargs) -> Generator[int, None, None]:
        """
        Fetch all bugs by creation or modification date
        starting `from_date` until we are not able to find more
        of them or `to_date` is hit.

        Bugs are pulled in date ranges defined by `step`
        not to hit bugzilla timeouts.

        Number of empty queries required before we stop querying is
        controlled by `stop_after_empty_steps`.

        If `updated_first` is True, recently modified bugs
        are queried first.

        `custom_fields` dictionary can be used to create more specific
        bugzilla queries.

        """
        from_date = kwargs.get('from_date', datetime.date.today())
        to_date = kwargs.get('to_date', datetime.date(2000, 1, 1))
        step = kwargs.get('step', 7)
        stop_after_empty_steps = kwargs.get('stop_after_empty_steps', 10)
        updated_first = kwargs.get('updated_first', False)
        custom_fields = kwargs.get('custom_fields', dict())

        if not updated_first:
            custom_fields.update(dict(chfield="[Bug creation]"))

        empty = 0

        over_days = list(daterange(from_date, to_date, step, desc=True))
        prev = over_days[0]

        for current in over_days[1:]:
            limit = 100
            offset = 0
            fetched_per_date_range = 0
            while True:
                try:
                    result = self._query_bugs(
                        prev, current, limit, offset, custom_fields)

                except Exception as e: # pylint: disable=broad-except
                    self.log_error("Exception after multiple attempts: {0}."
                                   " Ignoring".format(e))
                    continue

                count = len(result)
                fetched_per_date_range += count
                self.log_debug("Got %d bugs", count)
                for bug in result:
                    yield bug.bug_id

                if not count:
                    self.log_debug("No more bugs in this date range")
                    break

                offset += limit

            if not fetched_per_date_range:
                empty += 1
                if empty >= stop_after_empty_steps:
                    break
            else:
                empty = 0

            prev = current - datetime.timedelta(1)

    @retry(3, delay=10, backoff=3, verbose=True)
    def _query_bugs(self, to_date, from_date,
                    limit: int = 100, offset: int = 0,
                    custom_fields: Optional[Dict[str, Union[str, int]]] = None) \
                    -> List[Bug]:
        """
        Perform bugzilla query for bugs since `from_date` to `to_date`.

        Use `custom_fields` to perform additional filtering.
        """

        if not custom_fields:
            custom_fields = dict()
        target = "bugs modified"
        if "chfield" in custom_fields:
            target = "bugs created"

        self.log_debug("Fetching %s between %s and %s, offset is: %s",
                       target, from_date, to_date, offset)

        queue = dict(
            chfieldto=to_date.strftime("%Y-%m-%d"),
            chfieldfrom=from_date.strftime("%Y-%m-%d"),
            query_format="advanced",
            limit=limit,
            offset=offset,
        )

        queue.update(custom_fields)

        self.connect()
        return self.bz.query(queue)

    def _convert_datetime(self, bz_datetime: xmlrpc.client.DateTime) \
            -> datetime.datetime:
        """
        Convert `bz_datetime` returned by python-bugzilla
        to standard datetime.
        """

        return datetime.datetime.fromtimestamp(
            time.mktime(bz_datetime.timetuple()))

    def preprocess_bug(self, bug: Bug) -> Optional[Dict[str, Any]]:
        """
        Process the bug instance and return
        dictionary with fields required by lower logic.

        Returns `None` if there are missing fields.
        """

        required_fields = [
            "bug_id",
            "creation_time",
            "last_change_time",
            "product",
            "version",
            "component",
            "summary",
            "status",
            "resolution",
            "cc",
            "status_whiteboard",
            "reporter",
            "groups",
        ]

        if self.save_comments:
            required_fields.append("comments")
        if self.save_attachments:
            required_fields.append("attachments")

        bug_dict = dict()
        for field in required_fields:
            if not hasattr(bug, field):
                self.log_error("Missing bug field {0}".format(field))
                return None

            bug_dict[field] = getattr(bug, field)

        for field in ["creation_time", "last_change_time"]:
            bug_dict[field] = self._convert_datetime(bug_dict[field])

        history = bug.get_history_raw()
        bug_dict["history"] = history["bugs"][0]["history"]
        if bug.resolution == "DUPLICATE":
            bug_dict["dupe_id"] = bug.dupe_id

        return bug_dict

    def _save_bug(self, db: Database, bug: Bug) -> BzBug:
        """
        Save bug represented by `bug_dict` to the database.

        If bug is marked as duplicate, the duplicate bug is downloaded
        as well.
        """

        bug_dict = self.preprocess_bug(bug)
        if not bug_dict:
            self.log_error("Bug pre-processing failed")
            raise FafError("Bug pre-processing failed")

        self.log_debug("Saving bug #%d: %s", bug_dict["bug_id"], bug_dict["summary"])

        bug_id = bug_dict["bug_id"]

        # check if we already have this bug up-to-date
        old_bug = (
            db.session.query(BzBug)
            .filter(BzBug.id == bug_id)
            .filter(BzBug.last_change_time == bug_dict["last_change_time"])
            .first())

        if old_bug:
            self.log_info("Bug already up-to-date")
            return old_bug

        tracker = queries.get_bugtracker_by_name(db, self.name)
        if not tracker:
            self.log_error("Tracker with name '{0}' is not installed"
                           .format(self.name))
            raise FafError("Tracker with name '{0}' is not installed"
                           .format(self.name))

        opsysrelease = queries.get_osrelease(db, bug_dict["product"],
                                             bug_dict["version"])

        if not opsysrelease:
            self.log_error("Unable to save this bug due to unknown "
                           "release '{0} {1}'".format(bug_dict["product"],
                                                      bug_dict["version"]))
            raise FafError("Unable to save this bug due to unknown "
                           "release '{0} {1}'".format(bug_dict["product"],
                                                      bug_dict["version"]))

        relcomponent = queries.get_component_by_name_release(
            db, opsysrelease, bug_dict["component"])

        if not relcomponent:
            self.log_error("Unable to save this bug due to unknown "
                           "component '{0}'".format(bug_dict["component"]))
            raise FafError("Unable to save this bug due to unknown "
                           "component '{0}'".format(bug_dict["component"]))

        component = relcomponent.component

        reporter = queries.get_bz_user(db, bug_dict["reporter"])
        if not reporter:
            self.log_debug("Creator %s not found", bug_dict["reporter"])

            downloaded = self._download_user(bug_dict["reporter"])
            if not downloaded:
                self.log_error("Unable to download user, skipping.")
                raise FafError("Unable to download user, skipping.")

            reporter = self._save_user(db, downloaded)

        new_bug = BzBug()
        new_bug.id = bug_dict["bug_id"]
        new_bug.summary = bug_dict["summary"]
        new_bug.status = bug_dict["status"]
        new_bug.creation_time = bug_dict["creation_time"]
        new_bug.last_change_time = bug_dict["last_change_time"]
        new_bug.private = bool(bug_dict["groups"])

        if bug_dict["status"] == "CLOSED":
            new_bug.resolution = bug_dict["resolution"]
            if bug_dict["resolution"] == "DUPLICATE":
                if not queries.get_bz_bug(db, bug_dict["dupe_id"]):
                    self.log_debug("Duplicate #%d not found", bug_dict["dupe_id"])

                    dup = self.download_bug_to_storage(db, bug_dict["dupe_id"])
                    if dup:
                        new_bug.duplicate = dup.id

        new_bug.tracker_id = tracker.id
        new_bug.component_id = component.id
        new_bug.opsysrelease_id = opsysrelease.id
        new_bug.creator_id = reporter.id
        new_bug.whiteboard = bug_dict["status_whiteboard"]

        # the bug itself might be downloaded during duplicate processing
        # exit in this case - it would cause duplicate database entry
        if queries.get_bz_bug(db, bug_dict["bug_id"]):
            self.log_debug("Bug #%d already exists in storage, updating", bug_dict["bug_id"])

            bugdict = {}
            for col in new_bug.__table__._columns:  # pylint: disable=no-member,protected-access
                bugdict[col.name] = getattr(new_bug, col.name)

            (db.session.query(BzBug)
             .filter(BzBug.id == bug_id).update(bugdict))

            new_bug = queries.get_bz_bug(db, bug_dict["bug_id"])
        else:
            db.session.add(new_bug)

        db.session.flush()

        self._save_ccs(db, bug_dict["cc"], new_bug.id)
        self._save_history(db, bug_dict["history"], new_bug.id)
        if self.save_attachments:
            self._save_attachments(db, bug_dict["attachments"], new_bug.id)
        if self.save_comments:
            self._save_comments(db, bug_dict["comments"], new_bug.id)

        return new_bug

    def _save_ccs(self, db: Database, ccs: List[str], new_bug_id: int) -> None:
        """
        Save CC"ed users to the database.

        Expects list of emails (`ccs`) and ID of the bug as `new_bug_id`.
        """

        total = len(ccs)
        for num, user_email in enumerate(ccs, start=1):
            self.log_debug("Processing CC: %d/%d", num, total)
            cc = (
                db.session.query(BzBugCc)
                .join(BzUser)
                .filter((BzUser.email == user_email) &
                        (BzBugCc.bug_id == new_bug_id)).first())

            if cc:
                self.log_debug("CC'ed user %s already exists", user_email)
                continue

            cced = queries.get_bz_user(db, user_email)
            if not cced:
                self.log_debug("CC'ed user %s not found, adding.", user_email)

                downloaded = self._download_user(user_email)
                if not downloaded:
                    self.log_error("Unable to download user, skipping.")
                    continue

                cced = self._save_user(db, downloaded)

            new = BzBugCc()
            new.bug_id = new_bug_id
            new.user = cced
            db.session.add(new)

        db.session.flush()

    def _save_history(self, db: Database, events: List[Dict[str, Any]],
                      new_bug_id: int) -> None:
        """
        Save bug history to the database.

        Expects list of `events` and ID of the bug as `new_bug_id`.
        """

        total = len(events)
        for num, event in enumerate(events, start=1):
            self.log_debug("Processing history event %d/%d", num, total)

            user_email = event["who"]
            user = queries.get_bz_user(db, user_email)

            if not user:
                self.log_debug("History changed by unknown user # %s", user_email)

                downloaded = self._download_user(user_email)
                if not downloaded:
                    self.log_error("Unable to download user, skipping.")
                    continue

                user = self._save_user(db, downloaded)

            for change in event["changes"]:
                chtime = self._convert_datetime(event["when"])
                ch = (
                    db.session.query(BzBugHistory)
                    .filter((BzBugHistory.user == user) &
                            (BzBugHistory.time == chtime) &
                            (BzBugHistory.field == change["field_name"]) &
                            (BzBugHistory.added == change["added"]) &
                            (BzBugHistory.removed == change["removed"]))
                    .first())

                if ch:
                    self.log_debug("Skipping existing history event #%d", ch.id)
                    continue

                new = BzBugHistory()
                new.bug_id = new_bug_id
                new.user = user
                new.time = chtime
                new.field = change["field_name"]
                new.added = change["added"][:column_len(BzBugHistory, "added")]
                new.removed = change["removed"][:column_len(BzBugHistory, "removed")]

                db.session.add(new)

        db.session.flush()

    def _save_attachments(self, db: Database, attachments: List[Dict[str, Any]],
                          new_bug_id: int) -> None:
        """
        Save bug attachments to the database.

        Expects list of `attachments` and ID of the bug as `new_bug_id`.
        """

        total = len(attachments)
        for num, attachment in enumerate(attachments, start=1):
            self.log_debug("Processing attachment %d/%d", num, total)

            if queries.get_bz_attachment(db, attachment["id"]):
                self.log_debug("Skipping existing attachment #%d", attachment["id"])
                continue

            user_email = attachment["attacher"]
            user = queries.get_bz_user(db, user_email)

            if not user:
                self.log_debug("Attachment from unknown user %s", user_email)

                downloaded = self._download_user(user_email)
                if not downloaded:
                    self.log_error("Unable to download user, skipping.")
                    continue

                user = self._save_user(db, downloaded)

            new = BzAttachment()
            new.id = attachment["id"]
            new.bug_id = new_bug_id
            new.mimetype = attachment["content_type"]
            new.description = attachment["description"]
            new.filename = attachment["file_name"]
            new.is_private = bool(attachment["is_private"])
            new.is_patch = bool(attachment["is_patch"])
            new.is_obsolete = bool(attachment["is_obsolete"])
            new.creation_time = self._convert_datetime(
                attachment["creation_time"])
            new.last_change_time = self._convert_datetime(
                attachment["last_change_time"])
            new.user = user
            db.session.add(new)

            self.connect()
            data = self.bz.openattachment(attachment["id"])
            # save_lob is inherited method which cannot be seen by pylint
            # because of sqlalchemy magic
            # pylint: disable=E1101
            new.save_lob("content", data, truncate=True, overwrite=True)
            data.close()

        db.session.flush()

    def _save_comments(self, db: Database, comments: List[Dict[str, Any]],
                       new_bug_id: int) -> None:
        """
        Save bug comments to the database.

        Expects list of `comments` and ID of the bug as `new_bug_id`.
        """

        total = len(comments)
        for num, comment in enumerate(comments, start=1):
            self.log_debug("Processing comment %d/%d", num, total)

            if queries.get_bz_comment(db, comment["id"]):
                self.log_debug("Skipping existing comment #%d", comment["id"])
                continue

            self.log_debug("Downloading comment #%d", comment["id"])

            user_email = comment["creator"]
            user = queries.get_bz_user(db, user_email)

            if not user:
                self.log_debug("History changed by unknown user # %s", user_email)

                downloaded = self._download_user(user_email)
                if not downloaded:
                    self.log_error("Unable to download user, skipping.")
                    continue

                user = self._save_user(db, downloaded)

            new = BzComment()
            new.id = comment["id"]
            new.bug_id = new_bug_id
            new.creation_time = self._convert_datetime(comment["time"])
            new.is_private = comment["is_private"]

            if "attachment_id" in comment:
                attachment = queries.get_bz_attachment(
                    db, comment["attachment_id"])

                if attachment:
                    new.attachment = attachment
                else:
                    self.log_warn("Comment is referencing an attachment"
                                  " which is not accessible.")

            new.number = num
            new.user = user
            db.session.add(new)

            if not isinstance(comment["text"], str):
                comment["text"] = str(comment["text"])

            # save_lob is inherited method which cannot
            # be seen by pylint because of sqlalchemy magic
            # pylint: disable=E1101
            new.save_lob("content", comment["text"].encode("utf-8"),
                         overwrite=True)

        db.session.flush()

    @retry(3, delay=10, backoff=3, verbose=True)
    def _download_user(self, user_email: str) -> Optional[User]:
        """
        Return user with `user_email` downloaded from bugzilla.
        """

        if '@' not in user_email:
            self.log_warn("User email not available, bugzilla"
                          " requires logged in user to retrieve emails")

            return None

        self.log_debug("Downloading user %s", user_email)
        self.connect()
        user = self.bz.getuser(user_email)
        return user

    def _save_user(self, db: Database, user: User) -> BzUser:
        """
        Save bugzilla `user` to the database. Return persisted
        BzUser object.
        """

        # We need to account for case when user has changed
        # the email address.

        dbuser = (db.session.query(BzUser)
                  .filter(BzUser.id == user.userid).first())

        if not dbuser:
            dbuser = BzUser(id=user.userid)

        for field in ["name", "email", "can_login", "real_name"]:
            setattr(dbuser, field, getattr(user, field))

        db.session.add(dbuser)
        db.session.flush()
        return dbuser

    @retry(3, delay=10, backoff=3, verbose=True)
    def create_bug(self, **data) -> Bug:
        """
        Create new bugzilla ticket using `data` dictionary.
        """

        self.connect()
        return self.bz.createbug(**data)

    @retry(2, delay=60, backoff=1, verbose=True)
    def clone_bug(self, orig_bug_id: int, new_product: str, new_version: str) -> Bug:
        self.connect()

        origbug = self.bz.getbug(orig_bug_id)
        desc = ["+++ This bug was initially created as a clone "
                "of Bug #{0} +++".format(orig_bug_id)]

        private = False
        first = True
        for comment in origbug.longdescs:
            if comment["is_private"]:
                private = True

            if not first:
                desc.append("--- Additional comment from {0} on {1} ---"
                            .format(comment["author"], comment["time"]))

            if "extra_data" in comment:
                desc.append("*** This bug has been marked as a duplicate "
                            "of bug {0} ***".format(comment["extra_data"]))
            else:
                desc.append(comment["text"])

            first = False

        data = {
            'product': new_product,
            'component': origbug.component,
            'version': new_version,
            'op_sys': origbug.op_sys,
            'platform': origbug.platform,
            'summary': origbug.summary,
            'description': "\n\n".join(desc),
            'comment_is_private': private,
            'priority': origbug.priority,
            'bug_severity': origbug.bug_severity,
            'blocked': origbug.blocked,
            'whiteboard': origbug.whiteboard,
            'keywords': origbug.keywords,
            'cf_clone_of': str(orig_bug_id),
            'cf_verified': ['Any'],
            'cf_environment': origbug.cf_environment,
            'groups': origbug.groups
        }

        # filter empty elements
        for key in data:
            if data[key] is None:
                data.pop(key)

        newbug = self.bz.createbug(**data)

        return newbug
