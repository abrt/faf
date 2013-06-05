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

import datetime
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
from queries import (get_arch_by_name,
                     get_component_by_name,
                     get_osrelease,
                     get_report_by_hash,
                     get_reportarch,
                     get_reportreason,
                     get_reportosrelease)
from storage import (Arch,
                     OpSysRelease,
                     Report,
                     ReportArch,
                     ReportHash,
                     ReportOpSysRelease,
                     ReportReason)
from ureport_compat import ureport1to2

__all__ = [ "get_version", "save", "validate" ]

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

def get_version(ureport):
    """
    Get uReport version
    """

    ver = 0
    if "ureport_version" in ureport:
        try:
            ver = int(ureport["ureport_version"])
        except ValueError:
            raise FafError("`ureport_version` must be an integer")

    return ver

def validate_ureport1(ureport):
    """
    Validates uReport1
    """

    ureport2 = ureport1to2(ureport)
    validate_ureport2(ureport2)

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

    ver = get_version(ureport)

    if ver == 1:
        return validate_ureport1(ureport)

    if ver == 2:
        return validate_ureport2(ureport)

    raise FafError("uReport version {0} is not supported".format(ver))

def save_ureport1(db, ureport, timestamp=None, flush=True):
    """
    Saves uReport1
    """

    ureport2 = ureport1to2(ureport)
    save_ureport2(db, ureport2, timestamp=timestamp, flush=flush)

def save_ureport2(db, ureport, timestamp=None, flush=True):
    """
    Save uReport2
    """

    osplugin = systems[ureport["os"]["name"]]
    problemplugin = problemtypes[ureport["problem"]["type"]]

    report_hash = problemplugin.hash_ureport(ureport["problem"])
    db_report = get_report_by_hash(db, report_hash)
    if db_report is None:
        component_name = problemplugin.get_component_name(ureport["problem"])
        db_component = get_component_by_name(db, component_name,
                                             osplugin.nice_name)
        if db_component is None:
            raise FafError("Can't find component '{0}' in operating system "
                           "'{1}'".format(component_name, osplugin.nice_name))

        db_report = Report()
        db_report.type = problemplugin.name
        db_report.first_occurrence = timestamp
        db_report.last_occurrence = timestamp
        db_report.count = 0
        db_report.component = db_component
        db.session.add(db_report)

        db_report_hash = ReportHash()
        db_report_hash.report = db_report
        db_report_hash.hash = report_hash
        db.session.add(db_report_hash)

    if db_report.first_occurrence > timestamp:
        db_report.first_occurrence = timestamp

    if db_report.last_occurrence < timestamp:
        db_report.last_occurrence = timestamp

    db_report.count += 1

    db_osrelease = get_osrelease(db, osplugin.nice_name,
                                 ureport["os"]["version"])
    if db_osrelease is None:
        raise FafError("Operating system '{0} {1}' not found in storage"
                       .format(osplugin.nice_name, ureport["os"]["version"]))

    db_reportosrelease = get_reportosrelease(db, db_report, db_osrelease)
    if db_reportosrelease is None:
        db_reportosrelease = ReportOpSysRelease()
        db_reportosrelease.report = db_report
        db_reportosrelease.opsysrelease = db_osrelease
        db_reportosrelease.count = 0
        db.session.add(db_reportosrelease)

    db_reportosrelease.count += 1

    db_arch = get_arch_by_name(db, ureport["os"]["architecture"])
    if db_arch is None:
        raise FafError("Architecture '{0}' is not supported"
                       .format(ureport["os"]["architecture"]))

    db_reportarch = get_reportarch(db, db_report, db_arch)
    if db_reportarch is None:
        db_reportarch = ReportArch()
        db_reportarch.report = db_report
        db_reportarch.arch = db_arch
        db_reportarch.count = 0
        db.session.add(db_reportarch)

    db_reportarch.count += 1

    db_reportreason = get_reportreason(db, db_report, ureport["reason"])
    if db_reportreason is None:
        db_reportreason = ReportReason()
        db_reportreason.report = db_report
        db_reportreason.reason = ureport["reason"]
        db_reportreason.count = 0
        db.session.add(db_reportreason)

    db_reportreason.count += 1

    # do not forward flush, flush the whole thing at the end
    osplugin.save_ureport(db, db_report, ureport["os"], ureport["packages"])
    problemplugin.save_ureport(db, db_report, ureport["problem"])

    if flush:
        db.session.flush()

def save(db, ureport, timestamp=None, flush=True):
    """
    Save uReport based on ureport_version element
    assuming the given uReport is valid.
    """

    if timestamp is None:
        timestamp = datetime.datetime.utcnow()

    ver = get_version(ureport)

    if ver == 1:
        save_ureport1(db, ureport, timestamp=timestamp, flush=flush)
    elif ver == 2:
        save_ureport2(db, ureport, timestamp=timestamp, flush=flush)
    else:
        raise FafError("uReport version {0} is not supported".format(ver))
