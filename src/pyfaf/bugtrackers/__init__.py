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

import os
from pyfaf.common import FafError, Plugin, import_dir, load_plugins, log
from pyfaf.queries import get_bugtracker_by_name

from pyfaf.storage.bugtracker import Bugtracker

__all__ = ["BugTracker", "bugtrackers"]

# Invalid name "bugtrackers" for type constant
# pylint: disable-msg=C0103
bugtrackers = {}
# pylint: enable-msg=C0103


class BugTracker(Plugin):
    """
    A common superclass for bug tracker plugins.
    """

    @classmethod
    def install(cls, db, logger=None):
        if logger is None:
            logger = log.getChildLogger(cls.__name__)

        logger.info("Adding bugtracker '{0}'".format(cls.name))
        new = Bugtracker()
        new.name = cls.name
        db.session.add(new)
        db.session.flush()

    @classmethod
    def installed(cls, db):
        return bool(get_bugtracker_by_name(db, cls.name))

    def __init__(self, *args, **kwargs):
        """
        The superclass constructor does not really need to be called, but it
        enables a few useful features (like unified logging). If not called
        by the child, it just makes sure that BugTracker class is not
        instantiated directly.
        """

        if self.__class__.__name__ == "BugTracker":
            raise FafError("You need to subclass the BugTracker class "
                           "in order to implement a bugtracker plugin.")

        super(BugTracker, self).__init__()

    def list_bugs(self, *args, **kwargs):
        """
        List bugs by their IDs. `args` and `kwargs` may be used
        for instance-specific filtering.
        """

        raise NotImplementedError("list_bugs is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def download_bug_to_storage(self, db, bug_id):
        """
        Downloads the bug with given ID into storage or updates
        it if it already exists in storage.
        """

        raise NotImplementedError("download_bug_to_storage is not implemented "
                                  "for {0}".format(self.__class__.__name__))

    def create_bug(self, contents):
        """
        Creates a new bug with given contents.
        """

        raise NotImplementedError("create_bug is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def add_comment(self, bug_id, comment):
        """
        Adds `comment` to a bug with given bug ID.
        """

        raise NotImplementedError("add_comment is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def add_attachment(self, bug_id, attachment):
        """
        Adds `attachment` to a bug with given bug ID.
        `attachment` may be string or file-like object.
        """

        raise NotImplementedError("add_attachment is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def attach_bug_to_db_report(self, db, db_report, bug_id):
        """
        Attaches bug with given bug ID to a given `db_report`.
        """

        raise NotImplementedError("attach_bug_to_db_report is not implemented "
                                  "for {0}".format(self.__class__.__name__))

    def clone_bug(self, bug_id, new_product, new_version):
        """
        Clones the bug - Creates the same bug reported against a different
        product and version.
        """

        raise NotImplementedError("clone_bug is not implemented for {0}"
                                  .format(self.__class__.__name__))

import_dir(__name__, os.path.dirname(__file__))
load_plugins(BugTracker, bugtrackers)
