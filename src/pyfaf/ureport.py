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

import re
from checker import (Checker,
                     DictChecker,
                     IntChecker,
                     ListChecker,
                     StringChecker)
from common import FafError, column_len
from numbers import Integral
from opsys import systems
from problemtypes import problemtypes
from storage import Arch, OpSysRelease, ReportReason

__all__ = [ "validate" ]

UREPORT_CHECKER = DictChecker({
  "os":              DictChecker({
    "name":            StringChecker(allowed=systems.keys()),
    "version":         StringChecker(pattern="^[a-zA-Z0-9_\.\-\+~]+$",
                                     maxlen=column_len(OpSysRelease,
                                                       "version")),
    "architecture":    StringChecker(pattern="^[a-zA-Z0-9_]+$",
                                     maxlen=column_len(Arch, "name")),
    # Anything else will be checked by the plugin
  }),

  # The checker for packages depends on operating system
  "packages":        ListChecker(Checker(object)),

  "problem":         DictChecker({
    "type":            StringChecker(allowed=problemtypes.keys()),
    # Anything else will be checked by the plugin
  }),

  "reason":          StringChecker(maxlen=column_len(ReportReason, "reason")),

  "reporter":        DictChecker({
    "name":            StringChecker(pattern="^[a-zA-Z0-9 ]+$", maxlen=64),
    "version":         StringChecker(pattern="^[a-zA-Z0-9_\. ]+$", maxlen=64),
  }),

  "ureport_version": IntChecker(minval=0),
})

def validate_ureport1(ureport):
    """
    Validates uReport1
    """

    # ToDo: backport uReport1
    pass

def validate_ureport2(ureport):
    """
    Validates uReport2
    """

    UREPORT_CHECKER.check(ureport)

    osplugin = systems[ureport["os"]["name"]]
    osplugin.validate_ureport(ureport["os"])
    osplugin.validate_packages(ureport["packages"])

    problemplugin = problemtypes[ureport["problem"]["type"]]
    problemplugin.validate_ureport(ureport["problem"])

    return True

def validate(ureport):
    """
    Validates ureport based on ureport_version element
    """

    if not "ureport_version" in ureport:
        raise FafError("`ureport_version` key is missing in the uReport")

    try:
        ver = int(ureport["ureport_version"])
    except ValueError:
        raise FafError("`ureport_version` must be an integer")

    if ver == 1:
        return validate_ureport1(ureport)

    if ver == 2:
        return validate_ureport2(ureport)

    raise FafError("uReport version %d is not supported" % ver)
