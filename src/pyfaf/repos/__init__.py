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

from typing import Any, Dict

from pyfaf.common import FafError, Plugin, import_dir, load_plugin_types

__all__ = ["Repo", "repo_types"]

# Invalid name "repos" for type constant
# pylint: disable-msg=C0103
repo_types: Dict[str, Any] = {}
# pylint: enable-msg=C0103


class Repo(Plugin):
    """
    A common superclass for repository plugins.
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        The superclass constructor does not really need to be called, but it
        enables a few useful features (like unified logging). If not called
        by the child, it just makes sure that Repo class is not instantiated
        directly.
        """

        if self.__class__.__name__ == "Repo":
            raise FafError("You need to subclass the Repo class "
                           "in order to implement a repository plugin.")

        super().__init__()

    def list_packages(self, architectures) -> None:
        """
        Return list of packages available in this repository.
        """

        raise NotImplementedError

    @property
    def cache_lifetime(self):
        """
        Return the lifetime of the repository metadata cache in seconds.
        """

        raise NotImplementedError

    @cache_lifetime.setter
    def cache_lifetime(self, lifetime):
        """
        Set the lifetime of the repository metadata cache in seconds.
        Negative values are interpreted as “never expire” and 0 circumvents the
        cache altogether.
        """

        raise NotImplementedError

import_dir(__name__, os.path.dirname(__file__))
load_plugin_types(Repo, repo_types)
