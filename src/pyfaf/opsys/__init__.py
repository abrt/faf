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
from pyfaf.common import FafError, Plugin, import_dir, load_plugins

__all__ = ["System", "systems"]

# Invalid name "systems" for type constant
# pylint: disable-msg=C0103
systems = {}
# pylint: enable-msg=C0103


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

        super(System, self).__init__()

    def validate_ureport(self, ureport):
        """
        Validate the custom part of uReport. Raise FafError if the uReport is
        invalid. It must be safe to call save_ureport on a valid uReport.
        """

        raise NotImplementedError("validate_ureport is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def validate_packages(self, packages):
        """
        Validate the list of packages from uReport. Raise FafError if any of
        the packages is invalid. It must be safe to call save_ureport on
        a valid package list.
        """

        raise NotImplementedError("validate_packages is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def save_ureport(self, db, db_report, ureport, packages, flush=False, count=1):
        """
        Save the custom part of uReport and the list of packages into database.
        Assumes that the given uReport and list of packages are valid.
        """

        raise NotImplementedError("save_ureport is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def get_releases(self):
        """
        Get a list of releases of the operating system. Return a dictionary
        { "release1": properties1, "release2": properties2 }, where propertiesX
        is a dictionary { "property1": value1, "property2": value2 }.
        """

        raise NotImplementedError("get_releases is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def get_components(self, release):
        """
        Get a list of components for the given release.
        """

        raise NotImplementedError("get_components is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def get_component_acls(self, component):
        """
        Get ACLs for the given component. Return the dictionary
        { "username1": acls1, "username2": acls2 }, where aclsX is a dictionary
        { "commit": Bool, "watchbugzilla": Bool }.

        """

        raise NotImplementedError("get_component_acls is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def get_build_candidates(self, db):
        """
        Query the builds that may be mapped into components.
        """

        raise NotImplementedError("get_build_candidates is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def check_pkgname_match(self, packages, parser):
        """
        Check whether a relevant package matches to a knowledgebase rule.
        """

        raise NotImplementedError("check_pkgname_match is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def get_released_builds(self, release):
        """
        Get a list of builds for the given release.
        """

        raise NotImplementedError("get_released_builds is not implemented for "
                                  "{0}".format(self.__class__.__name__))

import_dir(__name__, os.path.dirname(__file__))
load_plugins(System, systems)
