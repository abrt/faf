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

from typing import Any, Dict, Generator, List, Optional, Union

from pyfaf.common import FafError, Plugin, import_dir, load_plugins, log
from pyfaf.queries import get_bugtracker_by_name

from pyfaf.storage.bugtracker import Bugtracker

__all__ = ["BugTracker", "bugtrackers"]

# Invalid name "bugtrackers" for type constant
# pylint: disable-msg=C0103
bugtrackers: Dict[str, Any] = {}
# pylint: enable-msg=C0103


class BugTracker(Plugin):
    """
    A common superclass for bug tracker plugins.
    """

    # backref name for accessing bugs associated with a Report
    report_backref_name = None
    name = None

    @classmethod
    def install(cls, db, logger=None) -> None:
        if logger is None:
            logger = log.getChild(cls.__name__)

        logger.info("Adding bugtracker '{0}'".format(cls.name))
        new = Bugtracker()
        new.name = cls.name
        db.session.add(new)
        db.session.flush()

    @classmethod
    def installed(cls, db) -> bool:
        return bool(get_bugtracker_by_name(db, cls.name))

    def __init__(self, *args, **kwargs) -> None:
        """
        The superclass constructor does not really need to be called, but it
        enables a few useful features (like unified logging). If not called
        by the child, it just makes sure that BugTracker class is not
        instantiated directly.
        """

        if self.__class__.__name__ == "BugTracker":
            raise FafError("You need to subclass the BugTracker class "
                           "in order to implement a bugtracker plugin.")

        super().__init__()

    def list_bugs(self, *args, **kwargs) -> Union[Generator[int, None, None], List[int]]:
        """
        List bugs by their IDs. `args` and `kwargs` may be used
        for instance-specific filtering.
        """

        raise NotImplementedError("list_bugs is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def download_bug_to_storage(self, db, bug_id) -> None:
        """
        Downloads the bug with given ID into storage or updates
        it if it already exists in storage.
        """

        raise NotImplementedError("download_bug_to_storage is not implemented "
                                  "for {0}".format(self.__class__.__name__))

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


import_dir(__name__, os.path.dirname(__file__))
load_plugins(BugTracker, bugtrackers)

report_backref_names = set() #pylint: disable=invalid-name
for bt in bugtrackers.values():
    if bt.report_backref_name is not None:
        report_backref_names.add(bt.report_backref_name)
