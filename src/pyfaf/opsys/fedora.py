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

from . import System
from ..checker import DictChecker, IntChecker, ListChecker, StringChecker
from ..common import column_len
from ..storage import Arch, Build, Package

__all__ = [ "Fedora" ]

class Fedora(System):
    name = "fedora"
    nice_name = "Fedora"

    supported_repos = [ "fedora-koji" ]

    packages_checker = ListChecker(
                         DictChecker({
        "name":            StringChecker(pattern="^[a-zA-Z0-9_\-\.\+~]+$",
                                         maxlen=column_len(Package, "name")),
        "epoch":           IntChecker(minval=0),
        "version":         StringChecker(pattern="^[a-zA-Z0-9_\.\+]+$",
                                         maxlen=column_len(Build, "version")),
        "release":         StringChecker(pattern="^[a-zA-Z0-9_\.\+]+$",
                                         maxlen=column_len(Build, "release")),
        "architecture":    StringChecker(pattern="^[a-zA-Z0-9_]+$",
                                         maxlen=column_len(Arch, "name")),
      })
    )

    ureport_checker = DictChecker({
      # no need to check name, version and architecture twice
      # the toplevel checker already did it
      # "name": StringChecker(allowed=[Fedora.name])
      # "version":        StringChecker()
      # "architecture":   StringChecker()
    })

    def __init__(self):
        System.__init__(self)

    def validate_ureport(self, ureport):
        Fedora.ureport_checker.check(ureport)
        return True

    def validate_packages(self, packages):
        Fedora.packages_checker.check(packages)
        return True
