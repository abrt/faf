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
from pyfaf.opsys import systems
from pyfaf.queries import get_opsys_by_name
from pyfaf.common import FafError, Plugin, import_dir, load_plugins

__all__ = ["Action", "actions"]

# Invalid name "actions" for type constant
# pylint: disable-msg=C0103
actions = {}
# pylint: enable-msg=C0103


class Action(Plugin):
    """
    A common superclass for action plugins.
    """
    # cmdline_only actions are not available in the Web UI
    cmdline_only = False

    def __init__(self, *args, **kwargs) -> None:
        """
        The superclass constructor does not really need to be called, but it
        enables a few useful features (like unified logging). If not called
        by the child, it just makes sure that Action class is not instantiated
        directly.
        """

        if self.__class__.__name__ == "Action":
            raise FafError("You need to subclass the Action class "
                           "in order to implement an action.")

        super(Action, self).__init__()

    def run(self, cmdline, db) -> None:
        """
        The actual code to execute. Needs to be overridden in subclasses.
        """

        raise NotImplementedError("The `run` method is not implemented in {0} "
                                  "class.".format(self.__class__.__name__))

    def tweak_cmdline_parser(self, parser) -> None:
        """
        Action may add its specific options to command line parser.
        """

    def get_opsys_name(self, cmdline_opsys) -> str:
        """
        Get correct opsys name from user passed opsys
        or raise FafError if not available
        """

        cmdline_opsys = cmdline_opsys.lower()
        if not cmdline_opsys in systems:
            raise FafError("Operating system '{0}' does not exist"
                           .format(cmdline_opsys))

        return systems[cmdline_opsys].nice_name

    def get_db_opsys(self, db, cmdline_opsys) -> str:
        """
        Get opsys object from database or raise
        FafError if not available
        """

        opsys_name = self.get_opsys_name(cmdline_opsys)
        db_opsys = get_opsys_by_name(db, opsys_name)
        if db_opsys is None:
            raise FafError("Operating system '{0}' is not installed"
                           .format(opsys_name))

        return db_opsys

    def delete_package(self, pkg, dry_run=False) -> None:
        #delete package from disk
        if pkg.has_lob("package"):
            self.log_info("Deleting lob for: {0}".format(pkg.nevr()))
            if dry_run:
                self.log_info("Dry run active, removal will be skipped.")
            else:
                pkg.del_lob("package")
        else:
            self.log_info("Package does not have a LOB. Skipping.")


import_dir(__name__, os.path.dirname(__file__))
load_plugins(Action, actions)
