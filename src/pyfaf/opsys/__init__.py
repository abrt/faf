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
from ..common import FafError, Plugin, import_dir, load_plugins, log
log = log.getChild(__name__)

__all__ = [ "System", "systems" ]

systems = {}

class System(Plugin):
    """
    A common superclass for operating system plugins.
    """

    def __init__(self, *args, **kwargs):
        """
        The superclass constructor does not really need to be called, but it
        enables a few useful features (like unified logging). If not called
        by the child, it just makes sure that System class is not instantiated
        directly.
        """

        if self.__class__.__name__ == "System":
            raise FafError("You need to subclass the System class "
                           "in order to implement an operating system plugin.")

        Plugin.__init__(self)

import_dir(__name__, os.path.dirname(__file__))
load_plugins(System, systems)
