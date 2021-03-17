# Copyright (C) 2014  ABRT Team
# Copyright (C) 2014  Red Hat, Inc.
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

from typing import Dict, List, Optional, Union

from zeep import Client

from pyfaf import queries
from pyfaf.common import FafConfigError
from pyfaf.utils.decorators import retry

from pyfaf.storage.mantisbt import MantisBug

from pyfaf.bugtrackers import BugTracker


__all__ = ["Mantis"]


BUG_STATE_MAP = {
    "new": "NEW",
    "feedback": "NEW",
    "acknowledged": "NEW",
    "confirmed": "NEW",
    "assigned": "ASSIGNED",
    "resolved": "CLOSED",
    "closed": "CLOSED"
}

BUG_RESOLUTION_MAP = {
    # OPEN
    10: None,
    # FIXED
    20: "UPSTREAM",
    # REOPENED
    30: None,
    # UNABLE_TO_REPRODUCE
    40: "WORKSFORME",
    # NOT_FIXABLE
    50: "CANTFIX",
    # DUPLICATE
    60: "DUPLICATE",
    # NOT_A_BUG
    70: "NOTABUG",
    # SUSPENDED
    80: "INSUFFICIENT_DATA",
    # WONT_FIX
    90: "WONTFIX"
}

# see https://github.com/abrt/faf/issues/695
# pylint: disable=abstract-method

class Mantis(BugTracker):

    name = "abstract_mantisbt"

    report_backref_name = "mantis_bugs"

    def __init__(self) -> None:
        """
        Load required configuration based on instance name.
        """

        super().__init__()

        # load config for corresponding bugzilla (e.g. fedorabz.api_url,
        # rhelbz.user, xyzbz.password)
        self.api_url = None
        self.user = None
        self.password = None
        self.load_config_to_self("api_url", "{0}.api_url".format(self.name))
        self.load_config_to_self("user", "{0}.user".format(self.name))
        self.load_config_to_self("password", "{0}.password".format(self.name))

        self.connected = False

    def connect(self) -> None:
        if self.connected:
            return

        if not self.api_url:
            raise FafConfigError(
                "No api_url specified for '{0}' mantisbt instance"
                .format(self.name))

        if not self.user or not self.password:
            raise FafConfigError(
                "No username or password specified for '{0}'"
                " mantisbt instance".format(self.name))

        self.log_debug("Opening mantisbt connection for '%s'", self.name)

        client = Client(self.api_url)
        self.mantis_client = client
        self.mc = client.service

        self.connected = True

    @retry(3, delay=10, backoff=3, verbose=True)
    def download_bug_to_storage(self, db, bug_id) -> Optional[MantisBug]:
        """
        Download and save single bug identified by `bug_id`.
        """

        self.log_debug("Downloading bug #%d", bug_id)
        self.connect()
        bug = self.mc.mc_issue_get(self.user, self.password, bug_id)
        return self._save_bug(db, bug)

    def preprocess_bug(self, bug) -> Optional[Dict[str, Union[int, str]]]:
        """
        Process the bug instance and return
        dictionary with fields required by lower logic.

        Returns `None` if there are missing fields.
        """

        try:
            url = ""
            if bug.custom_fields:
                url = next((f.value for f in bug.custom_fields if f.field.name == "URL"))
            bug_dict = {
                "bug_id": int(str(bug.id)),
                "creation_time": bug.date_submitted,
                "last_change_time": bug.last_updated,
                "product": bug.project.name.split("-")[0],
                "version": str(bug.os_build),
                "component": str(bug.category),
                "summary": str(bug.summary),
                "status": BUG_STATE_MAP[bug.status.name],
                "resolution": BUG_RESOLUTION_MAP.get(bug.resolution.id, "WONTFIX"),
                # URL in custom field list or ""
                "url": url,
            }
        except (AttributeError, KeyError) as e:
            self.log_error(str(e))
            return None

        if bug_dict["resolution"] == "DUPLICATE":
            for relationship in bug.relationships or []:
                if relationship.type.name == "duplicate of":
                    bug_dict["dupe_id"] = relationship.target_id
                    break

        return bug_dict

    def _save_bug(self, db, bug) -> Optional[MantisBug]:
        """
        Save bug represented by `bug_dict` to the database.

        If bug is marked as duplicate, the duplicate bug is downloaded
        as well.
        """

        bug_dict = self.preprocess_bug(bug)
        if not bug_dict:
            self.log_error("Bug pre-processing failed")
            return None

        self.log_debug("Saving bug #%d: %s", bug_dict["bug_id"], bug_dict["summary"])

        bug_id = bug_dict["bug_id"]

        tracker = queries.get_bugtracker_by_name(db, self.name)
        if not tracker:
            self.log_error("Tracker with name '{0}' is not installed"
                           .format(self.name))
            return None

        # check if we already have this bug up-to-date
        old_bug = (
            db.session.query(MantisBug)
            .filter(MantisBug.external_id == bug_id)
            .filter(MantisBug.tracker_id == tracker.id)
            .filter(MantisBug.last_change_time == bug_dict["last_change_time"])
            .first())

        if old_bug:
            self.log_info("Bug already up-to-date")
            return old_bug

        opsysrelease = queries.get_osrelease(db, bug_dict["product"],
                                             bug_dict["version"])

        if not opsysrelease:
            self.log_error("Unable to save this bug due to unknown "
                           "release '{0} {1}'".format(bug_dict["product"],
                                                      bug_dict["version"]))
            return None

        relcomponent = queries.get_component_by_name_release(
            db, opsysrelease, bug_dict["component"])

        if not relcomponent:
            self.log_error("Unable to save this bug due to unknown "
                           "component '{0}'".format(bug_dict["component"]))
            return None

        component = relcomponent.component

        new_bug = MantisBug()
        new_bug.external_id = bug_dict["bug_id"]
        new_bug.summary = bug_dict["summary"]
        new_bug.status = bug_dict["status"]
        new_bug.creation_time = bug_dict["creation_time"]
        new_bug.last_change_time = bug_dict["last_change_time"]

        if bug_dict["status"] == "CLOSED":
            new_bug.resolution = bug_dict["resolution"]
            if bug_dict["resolution"] == "DUPLICATE":
                if not queries.get_mantis_bug(db, bug_dict["dupe_id"], tracker.id):
                    self.log_debug("Duplicate #%d not found", bug_dict["dupe_id"])

                    dup = self.download_bug_to_storage(db, bug_dict["dupe_id"])
                    if dup:
                        new_bug.duplicate_id = dup.id

        new_bug.tracker_id = tracker.id
        new_bug.component_id = component.id
        new_bug.opsysrelease_id = opsysrelease.id

        # the bug itself might be downloaded during duplicate processing
        # exit in this case - it would cause duplicate database entry
        if queries.get_mantis_bug(db, bug_dict["bug_id"], tracker.id):
            self.log_debug("Bug #%d already exists in storage, updating", bug_dict["bug_id"])

            bugdict = {}
            for col in new_bug.__table__._columns: #pylint: disable=protected-access
                bugdict[col.name] = getattr(new_bug, col.name)
            # Otherwise id would be None, which would cause the following
            # update query to fail
            if "id" in bugdict:
                del bugdict["id"]

            (db.session.query(MantisBug)
             .filter(MantisBug.external_id == bug_id)
             .filter(MantisBug.tracker_id == tracker.id)
             .update(bugdict))

            new_bug = queries.get_mantis_bug(db, bug_dict["bug_id"], tracker.id)
        else:
            db.session.add(new_bug)

        db.session.flush()

        return new_bug

    def list_bugs(self, *args, **kwargs) -> List[int]:
        self.connect()
        f_type = self.mantis_client.get_type('ns0:FilterSearchData')
        f = f_type()
        f.search = "[abrt]"
        return self.mc.mc_filter_search_issue_ids(self.user, self.password, f,
                                                  1, -1)
