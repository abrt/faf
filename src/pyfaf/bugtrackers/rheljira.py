# Copyright (C) 2023  ABRT Team
# Copyright (C) 2023  Red Hat, Inc.
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

import re
from typing import Generator, Optional, List, Union

from jira import JIRA, Issue

from pyfaf import queries
from pyfaf.common import FafError
from pyfaf.storage import Database
from pyfaf.storage.bugzilla import BzBug
from pyfaf.utils.decorators import retry

from pyfaf.bugtrackers import BugTracker
from pyfaf.utils.parse import str2bool

__all__ = ["RhelJira"]


STATUS_MAPPING = {
    "New": "NEW",
    "Planning": "ON_DEV",
    "In Progress": "ASSIGNED",
    "Integration": "ON_QA",
    "Release Pending": "RELEASE_PENDING",
    "Closed": "CLOSED"
}


class RhelJira(BugTracker):
    """
    Proxy over Jira library handling bug downloading,
    creation and updates.
    """

    name = "rhel-jira"

    # This is "RHEL JIRA", so the product is always RHEL
    product_name = 'Red Hat Enterprise Linux'

    report_backref_name = "bz_bugs"

    api_url: str = ''
    web_url: Optional[str] = None
    new_bug_url: Optional[str] = None
    api_key: Optional[str] = None
    save_comments: bool = False
    save_attachments: bool = False

    user: Optional[str] = None
    password: Optional[str] = None

    project_name: str = ''
    project_id: str = ''

    connected: bool = False

    def __init__(self) -> None:
        """
        Load required configuration based on instance name.
        """

        super().__init__()

        self.load_config_to_self("api_url", f"{self.name}.api_url")
        self.load_config_to_self("web_url", f"{self.name}.web_url")
        self.load_config_to_self("new_bug_url", f"{self.name}.new_bug_url")
        self.load_config_to_self("api_key", f"{self.name}.api_key")
        self.load_config_to_self("save_comments", f"{self.name}.save_comments",
                                 False, callback=str2bool)
        self.load_config_to_self("save_attachments", f"{self.name}.save_attachments",
                                 False, callback=str2bool)

        self.load_config_to_self("user", f"{self.name}.user")
        self.load_config_to_self("password", f"{self.name}.password")

        self.load_config_to_self("project_name", f"{self.name}.project_name")
        self.load_config_to_self("project_id", f"{self.name}.project_id")

        self.jira_api = JIRA(
            options={
                "server": self.api_url,
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.password}",
                }
            }
        )
 
    def get_component_id(self, component_name: str) -> Optional[str]:
        """
        Return component id.
        """
        components = self.jira_api.project_components(self.project_name)
        for component in components:
            if component.name == component_name:
                return component.id
        return None


    def list_bugs(self, *args, **kwargs) -> Union[Generator[int, None, None], List[int]]:
        """
        List bugs by their IDs. `args` and `kwargs` may be used
        for instance-specific filtering.
        """

        raise NotImplementedError("list_bugs is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def download_bug_to_storage_no_retry(self, db: Database, bug_id: int) -> BzBug:
        """
        Download and save single bug identified by `bug_id`.
        """

        self.log_debug(u"Downloading bug #%d", bug_id)
        try:
            bug = self.jira_api.issue('RHEL-' + str(bug_id))

        except Exception as ex:
            raise FafError(str(ex)) from ex
        return self._save_bug(db, bug, bug_id)

    @retry(3, delay=10, backoff=3, verbose=True)
    def download_bug_to_storage(self, db: Database, bug_id: int) -> BzBug:
        """
        Downloads the bug with given ID into storage or updates
        it if it already exists in storage.
        """
        return self.download_bug_to_storage_no_retry(db, bug_id)

    def create_bug(self, **data) -> None:
        """
        Creates a new bug with given data.
        """

        raise NotImplementedError("create_bug is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def clone_bug(self, orig_bug_id, new_product, new_version) -> None:
        """
        Clones the bug - Creates the same bug reported against a different
        product and version.
        """

        raise NotImplementedError("clone_bug is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def _save_bug(self, db: Database, bug: Issue, bug_id: int) -> BzBug:
        """
        Save bug represented by `bug_dict` to the database.
        """
        self.log_debug("Saving bug #%d: %s", bug_id, bug.fields.summary)

        tracker = queries.get_bugtracker_by_name(db, self.name)
        if not tracker:
            self.log_error("Tracker with name '{0}' is not installed"
                           .format(self.name))
            raise FafError("Tracker with name '{0}' is not installed"
                           .format(self.name))

        product_versions = bug.fields.versions
        product_version = '9.4'  # default version, if there is no version set in the JIRA issue
        if product_versions:
            product_version_long = bug.fields.versions[0].name
            product_version_match = re.search(r"(\d+\.\d+)", product_version_long)
            if product_version_match:
                product_version = product_version_match[0]

        opsysrelease = queries.get_osrelease(db, self.product_name,
                                             product_version)

        if not opsysrelease:
            self.log_error("Unable to save this bug due to unknown "
                           "release '{0} {1}'".format(self.product_name,
                                                      product_version))
            raise FafError("Unable to save this bug due to unknown "
                           "release '{0} {1}'".format(self.product_name,
                                                      product_version))

        relcomponent = queries.get_component_by_name_release(
            db, opsysrelease, bug.fields.components[0].name)

        if not relcomponent:
            self.log_error("Unable to save this bug due to unknown "
                           "component '{0}'".format(bug.fields.components[0].name))
            raise FafError("Unable to save this bug due to unknown "
                           "component '{0}'".format(bug.fields.components[0].name))

        component = relcomponent.component

        new_bug = BzBug()
        new_bug.id = bug_id
        new_bug.summary = bug.fields.summary
        new_bug.status = STATUS_MAPPING.get(bug.fields.status.name, "NEW")
        new_bug.creation_time = bug.fields.created
        new_bug.last_change_time = bug.fields.updated
        new_bug.private = bool(int(bug.fields.security.id) == 11694)  # 11694 means that only users in the bz_redhat LDAP group can access the bug (RH-private)

        new_bug.tracker_id = tracker.id
        new_bug.component_id = component.id
        new_bug.opsysrelease_id = opsysrelease.id

        # we don't really care, or do we?
        new_bug.resolution = None
        new_bug.creator_id = 323435  # abrt user
        new_bug.whiteboard = ''

        db.session.add(new_bug)
        db.session.flush()

        return new_bug
