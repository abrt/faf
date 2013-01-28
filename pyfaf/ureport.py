#!/usr/bin/python
import re
import math
import hashlib
import datetime

import os
import pyfaf

from sqlalchemy.orm import joinedload_all

from pyfaf.common import get_libname, cpp_demangle

from pyfaf.storage.opsys import (OpSys,
                                 OpSysRelease,
                                 OpSysComponent,
                                 Arch,
                                 Build,
                                 Package,
                                 PackageDependency)

from pyfaf.storage.report import (Report,
                                  ReportArch,
                                  ReportOpSysRelease,
                                  ReportExecutable,
                                  ReportUptime,
                                  ReportBtHash,
                                  ReportBtFrame,
                                  ReportPackage,
                                  ReportUnknownPackage,
                                  ReportReason,
                                  ReportRhbz,
                                  ReportBacktrace,
                                  ReportSelinuxMode,
                                  ReportSelinuxContext,
                                  ReportHistoryDaily,
                                  ReportHistoryWeekly,
                                  ReportHistoryMonthly,
                                  ReportKernelTaintState)

from pyfaf.storage.symbol import (Symbol,
                                  SymbolSource)

# 2.0.12 | 2.0.13.35.g1033 | 2.0.12.26.gc7ab.dirty
ABRT_VERSION_PARSER = re.compile("^([0-9]+)\.([0-9]+)\.([0-9]+)(\..*)?$")

RE_ARCH = re.compile("^[0-9a-zA-Z_]+$")
RE_EXEC = re.compile("^[0-9a-zA-Z/_\.\-\+]+$")
RE_FUNCHASH = re.compile("^[a-zA-Z0-9\;\_\:\,\?]+$")
RE_HEX = re.compile("^(0[xX])?[0-9a-fA-F]+$")
RE_NONEMPTY = re.compile("^.+$")
RE_PACKAGE = re.compile("^[0-9a-zA-Z_\.\+\-~]+$")
RE_PHRASE = re.compile("^[0-9a-zA-Z_<>:\*\+=~@\?\!\ &(),\/\|\`\'\^\-\.\[\]\$\#]+$")
RE_PROJNAME = re.compile("^[0-9a-zA-Z \+\-\)\(\._~]+$")
RE_SEPOL = re.compile("^[a-zA-Z0-9_\.\-]+(:[a-zA-Z0-9_\.\-]+){3,4}$")
RE_TAINT = re.compile("^[A-Z ]+$")

def get_column_length(cls, name):
    return cls.__table__.c[name].type.length

MAX_UREPORT_LENGTH = 1 << 22 # 4MB
MAX_ATTACHMENT_LENGTH = 1 << 20 # 1MB (just metadata)

PACKAGE_CHECKER = {
  "name":         { "mand": True, "type": basestring, "re": RE_PACKAGE, "maxlen": get_column_length(Package, "name") },
  "version":      { "mand": True, "type": basestring, "re": RE_PACKAGE, "maxlen": get_column_length(Build, "version") },
  "release":      { "mand": True, "type": basestring, "re": RE_PACKAGE, "maxlen": get_column_length(Build, "release") },
  "architecture": { "mand": True, "type": basestring, "re": RE_ARCH, "maxlen": get_column_length(Arch, "name") },
  "epoch":        { "mand": True, "type": int }
}

RELATED_PACKAGES_ELEM_CHECKER = {
  "installed_package": { "mand": True,  "type": dict, "checker": PACKAGE_CHECKER },
  "running_package":   { "mand": False, "type": dict, "checker": PACKAGE_CHECKER }
}

RELATED_PACKAGES_CHECKER = { "type": dict, "checker": RELATED_PACKAGES_ELEM_CHECKER }

NV_CHECKER = {
  "name":    { "mand": True, "type": basestring, "re": RE_PROJNAME, "maxlen": get_column_length(OpSys, "name") },
  "version": { "mand": True, "type": basestring, "re": RE_PACKAGE, "maxlen": get_column_length(OpSysRelease, "version") }
}

SELINUX_CHECKER = {
  "mode":           { "mand": True,  "type": basestring , "re": re.compile("^(enforcing|permissive|disabled)$", re.IGNORECASE) },
  "context":        { "mand": False, "type": basestring,  "re": RE_SEPOL, "maxlen": get_column_length(ReportSelinuxContext, "context") },
  "policy_package": { "mand": False, "type": dict, "checker": PACKAGE_CHECKER }
}

COREBT_ELEM_CHECKER = {
  "thread":   { "mand": True, "type": int },
  "frame":    { "mand": True, "type": int },
  "buildid":  { "mand": False, "type": basestring, "re": RE_PACKAGE, "maxlen": get_column_length(SymbolSource, "build_id") },
  "path":     { "mand": False, "type": basestring, "re": RE_EXEC, "maxlen": get_column_length(SymbolSource, "path") },
  "offset":   { "mand": True, "type": int },
  "funcname": { "mand": False, "type": basestring, "re": RE_PHRASE, "trunc": get_column_length(Symbol, "name") },
  "funchash": { "mand": False, "type": basestring, "re": RE_FUNCHASH, "maxlen": get_column_length(SymbolSource, "hash") }
}

COREBT_CHECKER = { "type": dict, "checker": COREBT_ELEM_CHECKER }

PROC_STATUS_CHECKER = {

}

PROC_LIMITS_CHECKER = {

}

OS_STATE_CHECKER = {
    "suspend":  { "mand": True, "type": basestring, "re": re.compile("^(yes|no)$", re.IGNORECASE) },
    "boot":     { "mand": True, "type": basestring, "re": re.compile("^(yes|no)$", re.IGNORECASE) },
    "login":    { "mand": True, "type": basestring, "re": re.compile("^(yes|no)$", re.IGNORECASE) },
    "logout":   { "mand": True, "type": basestring, "re": re.compile("^(yes|no)$", re.IGNORECASE) },
    "shutdown": { "mand": True, "type": basestring, "re": re.compile("^(yes|no)$", re.IGNORECASE) }
}

UREPORT_CHECKER = {
  "ureport_version":   { "mand": False, "type": int },
  "type":              { "mand": True,  "type": basestring,  "re": re.compile("^(python|userspace|kerneloops)$", re.IGNORECASE) },
  "reason":            { "mand": True,  "type": basestring,  "re": RE_NONEMPTY, "trunc": get_column_length(ReportReason, "reason") },
  "uptime":            { "mand": False, "type": int },
  "component":         { "mand": False, "type": basestring,  "re": RE_PACKAGE, "maxlen": get_column_length(OpSysComponent, "name") },
  "executable":        { "mand": False, "type": basestring,  "re": RE_EXEC, "maxlen": get_column_length(ReportExecutable, "path") },
  "installed_package": { "mand": True,  "type": dict, "checker": PACKAGE_CHECKER },
  "running_package":   { "mand": False, "type": dict, "checker": PACKAGE_CHECKER },
  "related_packages":  { "mand": True,  "type": list, "checker": RELATED_PACKAGES_CHECKER },
  "os":                { "mand": True,  "type": dict, "checker": NV_CHECKER },
  "architecture":      { "mand": True,  "type": basestring,  "re": RE_ARCH, "maxlen": get_column_length(Arch, "name") },
  "reporter":          { "mand": True,  "type": dict, "checker": NV_CHECKER },
  "crash_thread":      { "mand": True,  "type": int },
  "core_backtrace":    { "mand": True,  "type": list, "checker": COREBT_CHECKER },
  "user_type":         { "mand": False, "type": basestring,  "re": re.compile("^(root|nologin|local|remote)$", re.IGNORECASE) },
  "os_state":          { "mand": False, "type": dict,  "checker": OS_STATE_CHECKER },
  "selinux":           { "mand": False, "type": dict, "checker": SELINUX_CHECKER },
  "kernel_taint_state":{ "mand": False, "type": basestring,  "re": RE_TAINT, "maxlen": get_column_length(ReportKernelTaintState, "state")},
  "proc_status":       { "mand": False, "type": dict, "checker": PROC_STATUS_CHECKER },
  "proc_limits":       { "mand": False, "type": dict, "checker": PROC_LIMITS_CHECKER },
  "oops":              { "mand": False, "type": basestring, "maxlen": 1 << 16 },
}

# just metadata, large objects are uploaded separately
ATTACHMENT_CHECKER = {
  "type":   { "mand": True, "type": basestring, "re": RE_PHRASE, "maxlen": 64 },
  "bthash": { "mand": True, "type": basestring, "re": RE_HEX,    "maxlen": 64 },
  "data":   { "mand": True, "type": basestring, "re": RE_PHRASE, "maxlen": 1024 },
}

def validate(obj, checker=UREPORT_CHECKER):
    expected = dict
    if "type" in checker and isinstance(checker["type"], type):
        expected = checker["type"]

    # check for expected type
    if not isinstance(obj, expected):
        raise Exception, "typecheck failed: expected {0}, had {1}; {2}".format(expected.__name__, type(obj).__name__, obj)

    # str checks
    if isinstance(obj, basestring):
        if "re" in checker and checker["re"].match(obj) is None:
            raise Exception, 'string "{0}" contains illegal characters'.format(obj)
        if "trunc" in checker and len(obj) > checker["trunc"]:
            obj = obj[:checker["trunc"]]
        if "maxlen" in checker and len(obj) > checker["maxlen"]:
            raise Exception, 'string "{0}" is too long (maximum {1})'.format(obj, checker["maxlen"])
    # list - apply checker["checker"] to every element
    elif isinstance(obj, list):
        obj = [validate(elem, checker["checker"]) for elem in obj]

    # dict
    elif isinstance(obj, dict):
        # load the actual checker if we are not toplevel
        if "checker" in checker:
            checker = checker["checker"]

        # need to clone, we are going to modify
        clone = dict(obj)
        obj = dict()
        # validate each element separately
        for key in checker:
            subchkr = checker[key]
            try:
                value = clone.pop(key)
            except KeyError:
                # fail for mandatory elements
                if subchkr["mand"]:
                    raise Exception, "missing mandatory element '{0}'".format(key)
                # just skip optional
                continue

            try:
                obj[key] = validate(value, subchkr)
            except Exception, msg:
                # queue error messages
                raise Exception, "error validating '{0}': {1}".format(key, msg)

        # excessive elements - error
        keys = clone.keys()
        if keys:
            raise Exception, "unknown elements present: {0}".format(keys)

    return obj

def get_crash_thread(ureport):
    result = []
    for frame in ureport["core_backtrace"]:
        if frame["thread"] == ureport["crash_thread"]:
            result.append(frame)

    return sorted(result, key=lambda x: x["frame"])

def hash_thread(thread, hashbase=[], include_offset=False):
    hasnames = all(["funcname" in x and not x["funcname"] is None for x in thread])
    hashashes = all(["funchash" in x and not x["funchash"] is None for x in thread])
    # use function names if available
    if hasnames:
        # also hash offset for reports that use it as line numbers
        # these reports always have function names
        if include_offset:
            hashbase.extend(["{0} @ {1} + {2}".format(x["funcname"], x["path"], x["offset"]) for x in thread])
        else:
            hashbase.extend(["{0} @ {1}".format(x["funcname"], x["path"]) for x in thread])
        hashtype = "NAMES"
    # fallback to hashes
    elif hashashes:
        hashbase.extend(["{0} @ {1}".format(x["funchash"], x["path"]) for x in thread])
        hashtype = "HASHES"
    else:
        raise Exception, "either function names or function hashes are required"

    #pylint: disable=E1101
    # Module 'hashlib' has no 'sha1' member  (false positive)
    return (hashtype, hashlib.sha1("\n".join(hashbase)).hexdigest())

def get_package(ureport_package, ureport_os, db):
    return db.session.query(Package).join(Package.arch).join(Package.build).\
            join(Build.component).join(OpSysComponent.opsysreleases).\
            join(OpSysRelease.opsys).\
            filter((Package.name == ureport_package["name"]) & \
                   (Build.epoch == ureport_package["epoch"]) & \
                   (Build.version == ureport_package["version"]) & \
                   (Build.release == ureport_package["release"]) & \
                   (Arch.name == ureport_package["architecture"]) & \
                   (OpSys.name == ureport_os["name"]) & \
                   (OpSysRelease.version == ureport_os["version"])).first()

def get_component(component_name, ureport_os, db):
    return db.session.query(OpSysComponent).join(OpSys).\
            join(OpSysRelease).\
            filter((OpSysComponent.name == component_name) & \
                   (OpSys.name == ureport_os["name"]) & \
                   (OpSysRelease.version == ureport_os["version"])).first()

def guess_component(ureport_package, ureport_os, db):
    # Find a package only by name.
    pkg = db.session.query(Package).join(Package.build).\
            join(Build.component).join(OpSysComponent.opsysreleases).\
            join(OpSysRelease.opsys).\
            filter((Package.name == ureport_package["name"]) & \
                   (OpSys.name == ureport_os["name"]) & \
                   (OpSysRelease.version == ureport_os["version"])).first()
    if pkg:
        return pkg.build.component
    return None

def guess_component_paths(path):
    # Return list of paths which could belong to the same component as path
    result = [path]

    # Strip version after .so to hit a devel package
    idx = path.rfind(".so")
    if idx > 0 and idx + len(".so") < len(path):
        result.append(path[:idx + len(".so")])
        # Try also moving to /usr
        if path.startswith("/lib"):
            result.append("/usr" + result[-1])

    return result

def get_report_hash(ureport, component):
    cthread = get_crash_thread(ureport)
    # Hash only up to first 16 frames or use HashFrames
    # configuration option if present
    frames_to_use = 16

    if "processing.hashframes" in pyfaf.config.CONFIG:
        frames_to_use = int(pyfaf.config.CONFIG["processing.hashframes"])

    cthread = cthread[:frames_to_use]
    include_offset = ureport["type"].lower() == "python"
    return hash_thread(cthread, hashbase=[component],
                       include_offset=include_offset)

def get_unknownpackage_spec(type, ureport_packages, db):
    ureport_installed_package = ureport_packages["installed_package"]
    result = [("type", type),
              ("name", ureport_installed_package["name"]),
              ("installed_epoch", ureport_installed_package["epoch"]),
              ("installed_version", ureport_installed_package["version"]),
              ("installed_release", ureport_installed_package["release"]),
              ("installed_arch", db.session.query(Arch).\
                      filter(Arch.name == ureport_installed_package["architecture"]).one())]

    if "running_package" in ureport_packages:
        ureport_running_package = ureport_packages["running_package"]
        if ureport_running_package["name"] != ureport_installed_package["name"]:
            raise Exception, "Names of installed and running packages don't match."
        result.extend([("running_epoch", ureport_running_package["epoch"]),
                       ("running_version", ureport_running_package["version"]),
                       ("running_release", ureport_running_package["release"]),
                       ("running_arch", db.session.query(Arch).\
                               filter(Arch.name == ureport_running_package["architecture"]).one())])
    else:
        result.extend([("running_epoch", None),
                       ("running_version", None),
                       ("running_release", None),
                       ("running_arch", None)])

    return result

def get_package_stat(package_type, ureport_packages, ureport_os, db):
    installed_package = get_package(ureport_packages["installed_package"], ureport_os, db)
    if "running_package" in ureport_packages:
        running_package = get_package(ureport_packages["running_package"], ureport_os, db)
    else:
        running_package = None

    # If both installed and running packages were found in the Package
    # table, add them directly to the report stat, otherwise add them to
    # ReportUnknownPackage as strings where they will be resolved to
    # packages later.
    if installed_package and \
            ("running_package" not in ureport_packages or running_package):
        return (ReportPackage, [("type", package_type),
                                ("installed_package", installed_package),
                                ("running_package", running_package)])
    else:
        return (ReportUnknownPackage,
                get_unknownpackage_spec(package_type, ureport_packages, db))

def flip_corebt_if_necessary(ureport):
    # only python needs flipping
    if ureport["type"].lower() != "python":
        return

    # ureport_version 1 already assumes flipped core-backtrace
    if "ureport_version" in ureport and ureport["ureport_version"] >= 1:
        return

    # libreport > 2.0.13 does not need flipping
    # (actually ABRT sends libreport's version)
    if ureport["reporter"]["name"].lower() == "abrt":
        match = ABRT_VERSION_PARSER.match(ureport["reporter"]["version"])
        if match and (int(match.group(1)) > 2 or
                      int(match.group(2)) > 0 or
                      int(match.group(3)) > 13):
            return

    # get thread length
    threads = {}
    for frame in ureport["core_backtrace"]:
        if not frame["thread"] in threads:
            threads[frame["thread"]] = 0
        else:
            threads[frame["thread"]] += 1

    # flip
    for frame in ureport["core_backtrace"]:
        frame["frame"] = threads[frame["thread"]] - frame["frame"]

def add_report(ureport, db, utctime=None, count=1, only_check_if_known=False, return_report=False):
    if not utctime:
        utctime = datetime.datetime.utcnow()

    flip_corebt_if_necessary(ureport)

    if "component" in ureport:
        component = get_component(ureport["component"], ureport["os"], db)
    else:
        component = guess_component(ureport["installed_package"], ureport["os"], db)
    if component is None:
        raise Exception, "Unknown component."

    for frame in ureport["core_backtrace"]:
        if not "path" in frame and "executable" in ureport:
            frame["path"] = ureport["executable"]

        frame["path"] = os.path.abspath(frame["path"])

    hash_type, hash_hash = get_report_hash(ureport, component.name)

    # Find a report with matching hash and component.
    report = db.session.query(Report).join(ReportBacktrace).join(ReportBtHash).\
            filter((ReportBtHash.hash == hash_hash) & \
                   (ReportBtHash.type == hash_type) & \
                   (Report.component == component)).first()

    if only_check_if_known:
        # check whether the report has a BZ associated
        # if it does not, proclaim it unknown
        if report:
            reportbz = db.session.query(ReportRhbz) \
                                 .filter(ReportRhbz.report_id == report.id) \
                                 .first()

            if not reportbz:
                report = None

        if return_report:
            return report

        return bool(report)

    # Create a new report if not found.
    if not report:
        # do not process reports with empty
        # core-backtrace, except for selinux
        if ureport["type"].lower() != "selinux" and \
           len(ureport["core_backtrace"]) < 1:
            raise Exception, "empty core_backtrace"

        report = Report()
        report.type = ureport["type"].upper()
        report.first_occurence = report.last_occurence = utctime
        report.count = count
        report.component = component
        db.session.add(report)

        report_backtrace = ReportBacktrace()
        report_backtrace.report = report
        db.session.add(report_backtrace)

        report_bthash = ReportBtHash()
        report_bthash.type = hash_type
        report_bthash.hash = hash_hash
        report_bthash.backtrace = report_backtrace
        db.session.add(report_bthash)

        # Add frames, symbols, hashes and sources.
        for frame in get_crash_thread(ureport):
            report_btframe = ReportBtFrame()
            report_btframe.backtrace = report_backtrace
            report_btframe.order = frame["frame"]
            if not "buildid" in frame:
                frame["buildid"] = None

            # Check if there was already such symbol added, but first check
            # the current session before doing a query.
            for symbolsource in (x for x in db.session.new if type(x) is SymbolSource):
                if symbolsource.build_id == frame["buildid"] and \
                        symbolsource.path == frame["path"] and \
                        symbolsource.offset == frame["offset"]:
                    break
            else:
                symbolsource = db.session.query(SymbolSource).\
                        filter((SymbolSource.build_id == frame["buildid"]) & \
                               (SymbolSource.path == frame["path"]) & \
                               (SymbolSource.offset == frame["offset"])).first()

            # Create a new symbolsource if not found.
            if not symbolsource:
                symbolsource = SymbolSource()
                symbolsource.build_id = frame["buildid"]
                symbolsource.path = frame["path"]
                symbolsource.offset = frame["offset"]
                if ureport["type"].lower() == "python":
                    symbolsource.source_path = frame["path"]
                    symbolsource.line_number = frame["offset"]

                if "funchash" in frame:
                    symbolsource.hash = frame["funchash"]

                if "funcname" in frame:
                    normalized_path = get_libname(frame["path"])
                    for symbol in (x for x in db.session.new if type(x) is Symbol):
                        if symbol.name == frame["funcname"] and \
                            symbol.normalized_path == normalized_path:
                            break
                    else:
                        symbol = db.session.query(Symbol).\
                                filter((Symbol.name == frame["funcname"]) & \
                                       (Symbol.normalized_path == normalized_path)).first()

                    # Create a new symbol if not found.
                    if not symbol:
                        symbol = Symbol()
                        symbol.name = frame["funcname"]

                        demangled = cpp_demangle(symbol.name)
                        if demangled != symbol.name:
                            symbol.nice_name = demangled

                        symbol.normalized_path = normalized_path
                        db.session.add(symbol)

                    symbolsource.symbol = symbol

                db.session.add(symbolsource)

            report_btframe.symbolsource = symbolsource
            db.session.add(report_btframe)
    else:
        report.count += count
        if report.last_occurence < utctime:
            report.last_occurence = utctime
        elif report.first_occurence > utctime:
            report.first_occurence = utctime

        if report.problem:
            if report.problem.last_occurence < report.last_occurence:
                report.problem.last_occurence = report.last_occurence
            if report.problem.first_occurence > report.first_occurence:
                report.problem.first_occurence = report.first_occurence

    db.session.flush()
    if report.type == "KERNELOOPS":
        if not report.get_lob_fd("oops") and "oops" in ureport:
            report.save_lob("oops", ureport["oops"])

    # Update various stats.

    opsysrelease = db.session.query(OpSysRelease).join(OpSys).filter(\
            (OpSysRelease.version == ureport["os"]["version"]) & \
            (OpSys.name == ureport["os"]["name"])).one()

    arch = db.session.query(Arch).filter_by(name=ureport['architecture']).one()

    day = utctime.date()
    week = day - datetime.timedelta(days=day.weekday())
    month = day.replace(day=1)

    stat_map = [(ReportArch, [("arch", arch)]),
                (ReportOpSysRelease, [("opsysrelease", opsysrelease)]),
                (ReportReason, [("reason", ureport["reason"])]),
                (ReportHistoryMonthly, [("opsysrelease", opsysrelease), ("month", month)]),
                (ReportHistoryWeekly, [("opsysrelease", opsysrelease), ("week", week)]),
                (ReportHistoryDaily, [("opsysrelease", opsysrelease), ("day", day)])]

    if "executable" in ureport:
        stat_map.append((ReportExecutable, [("path", ureport["executable"])]))

    if "uptime" in ureport:
        if ureport["uptime"] < 0.1:
            uptime_exp = -1
        else:
            uptime_exp = int(math.log(ureport["uptime"], 10))
        stat_map.append((ReportUptime, [("uptime_exp", uptime_exp)]))

    # Add the reported package (installed and running).
    stat_map.append(get_package_stat("CRASHED", ureport, ureport["os"], db))

    # Similarly add related packages.
    if "related_packages" in ureport:
        for related_package in ureport["related_packages"]:
            stat_map.append(get_package_stat("RELATED", related_package, ureport["os"], db))

    # Add selinux fields to stat_map
    if "selinux" in ureport:
        stat_map.append((ReportSelinuxMode, [("mode", ureport["selinux"]["mode"].upper())]))

        if "context" in ureport["selinux"]:
            stat_map.append((ReportSelinuxContext, [("context", ureport["selinux"]["context"])]))

        if "policy_package" in ureport["selinux"]:
            stat_map.append(get_package_stat("SELINUX_POLICY",
                {"installed_package": ureport["selinux"]["policy_package"]}, ureport["os"], db))

    # Add kernel taint state fields to stat_map.
    if "kernel_taint_state" in ureport:
        stat_map.append((ReportKernelTaintState, [("state", ureport["kernel_taint_state"])]))

    # Create missing stats and increase counters.
    for table, cols in stat_map:
        report_stat_query = db.session.query(table).join(Report).filter(Report.id == report.id)
        for name, value in cols:
            report_stat_query = report_stat_query.filter(getattr(table, name) == value)

        report_stat = report_stat_query.first()
        if not report_stat:
            report_stat = table()
            report_stat.report = report
            for name, value in cols:
                setattr(report_stat, name, value)
            report_stat.count = 0
            db.session.add(report_stat)
        report_stat.count += count

def is_known(ureport, db, return_report=False):
    return add_report(ureport, db, only_check_if_known=True, return_report=return_report)

def convert_to_str(obj):
    if type(obj) in (int, float, str, bool):
        return obj
    elif type(obj) == unicode:
        return str(obj.encode("utf-8"))
    elif type(obj) in (list, tuple):
        obj = [convert_to_str(v) for v in obj]
    elif type(obj) == dict:
        for n, v in obj.iteritems():
            obj[n] = convert_to_str(v)
    else:
        assert False
    return obj

def get_btp_thread(backtrace, max_frames=16):
    norm = backtrace.normalized()
    norm.frames = norm.frames[:max_frames]
    return norm

def get_report_btp_threads(report_ids, db, log_debug=None):
    # Create btparser threads for specified report ids. Return a list
    # of (report_id, thread) pairs.

    result = []

    frames_to_use = 16

    if "processing.clusterframes" in pyfaf.config.CONFIG:
        frames_to_use = int(pyfaf.config.CONFIG["processing.clusterframes"])

    # Split the ids into small groups to keep memory consumption low.
    group_size = 100
    report_id_groups = []
    for i in xrange(0, len(report_ids), group_size):
        report_id_groups.append(report_ids[i:i + group_size])

    # Load all reports from each group and create threads.
    for i, report_id_group in enumerate(report_id_groups):
        if log_debug:
            log_debug("Loading reports {0}-{1}/{2}.".format(i * group_size + 1,
                i * group_size + len(report_id_group), len(report_ids)))

        # Set joined load to fetch all needed data at once.
        reports = db.session.query(Report).filter(Report.id.in_(report_id_group)).\
                options(joinedload_all('backtraces.frames.symbolsource.symbol')).\
                order_by(Report.id).all()

        for report in reports:
            for backtrace in report.backtraces:
                thread = get_btp_thread(backtrace, max_frames=frames_to_use)
                result.append((report.id, thread))

                # For now, return only the first thread per report.
                break

    return result

def get_components_by_files(paths, opsys_id, db):
    # Return list of paths and corresponding components according to package provides.
    #pylint:disable=E1101
    # Class 'OpSysComponent' has no 'builds' member
    return db.session.query(PackageDependency.name, OpSysComponent.name).\
            join(OpSysComponent.builds).\
            join(Build.packages).\
            join(Package.dependencies).\
            filter((OpSysComponent.opsys_id == opsys_id) & \
                   (PackageDependency.type == 'PROVIDES') & \
                   (PackageDependency.name.in_(paths))).distinct().all()

def get_symbolsource_paths(report_ids, db):
    # Return symbolsource paths for all frames in all backtraces for each report.
    #pylint:disable=E1101
    # Class 'Report' has no 'backtraces' member
    return db.session.query(Report.id, ReportBacktrace.id, ReportBtFrame.order, SymbolSource.path).\
            join(Report.backtraces).\
            join(ReportBacktrace.frames).\
            join(ReportBtFrame.symbolsource).\
            filter(Report.id.in_(report_ids)).\
            order_by(Report.id).order_by(ReportBtFrame.order).distinct().all()

def get_frame_components(report_ids, opsys_id, db):
    # Return list of lists of component names corresponding to frames in
    # backtraces of the specified reports.

    reports_paths = dict()
    backtrace_ids = set()
    guess_path_map = dict()
    for report_id, backtrace_id, frame_order, path in get_symbolsource_paths(report_ids, db):
        if report_id not in reports_paths:
            reports_paths[report_id] = []
            backtrace_ids.add(backtrace_id)

        if backtrace_id not in backtrace_ids:
            # Pick only one backtrace per report.
            continue

        reports_paths[report_id].append(path)

        if path not in guess_path_map:
            # Look also for other paths which are more likely to be
            # matched with missing packages.
            guess_path_map[path] = set(guess_component_paths(path))

    # Find components for all guess paths in one query.
    path_component_map = dict()
    for path, component in get_components_by_files(set.union(*guess_path_map.values()), opsys_id, db):
        path_component_map[path] = component

    # Prepare the final lists.
    result = []
    for report_id in report_ids:
        result.append([])
        for report_path in reports_paths[report_id]:
            for guess_path in guess_path_map[report_path]:
                if guess_path in path_component_map:
                    result[-1].append(path_component_map[guess_path])
                    break
            else:
                # No component was found.
                result[-1].append(None)

    return result

# only for debugging purposes
if __name__ == "__main__":
    import pyfaf

    ureport = {
      "type": "python",
      "reason": "TypeError",
      "uptime": 1,
      "component": "faf",
      "executable": "/usr/bin/faf-btserver-cgi",
      "installed_package": { "name": "faf",
                             "version": "0.4",
                             "release": "1.fc16",
                             "epoch": 0,
                             "architecture": "noarch" },
      "related_packages": [ { "installed_package": { "name": "python",
                                                     "version": "2.7.2",
                                                     "release": "4.fc16",
                                                     "epoch": 0,
                                                     "architecture": "x86_64" } } ],
      "os": { "name": "Fedora", "version": "16" },
      "architecture": "x86_64",
      "reporter": { "name": "abrt", "version": "2.0.7-2.fc16" },
      "crash_thread": 0,
      "core_backtrace": [
        { "thread": 0,
          "frame": 1,
          "buildid": "f76f656ab6e1b558fc78d0496f1960071565b0aa",
          "offset": 24,
          "path": "/usr/bin/faf-btserver-cgi",
          "funcname": "<module>" },
        { "thread": 0,
          "frame": 2,
          "buildid": "b07daccd370e885bf3d459984a4af09eb889360a",
          "offset": 190,
          "path": "/usr/lib64/python2.7/re.py",
          "funcname": "compile" },
        { "thread": 0,
          "frame": 3,
          "buildid": "b07daccd370e885bf3d459984a4af09eb889360a",
          "offset": 241,
          "path": "/usr/lib64/python2.7/re.py",
          "funcname": "_compile" }
      ],
      "user_type": "root",
      "selinux": { "mode": "permissive",
                   "context": "unconfined_u:unconfined_r:unconfined_t:s0",
                   "policy_package": { "name": "selinux-policy",
                                       "version": "3.10.0",
                                       "release": "2.fc16",
                                       "epoch": 0,
                                       "architecture": "noarch" } },
      "kernel_taint_state": "G    B      ",
    }

    try:
        # import json
        # input = some json
        # ureport = convert_to_str(json.loads(input))
        ureport = validate(ureport)
        known = is_known(ureport, pyfaf.storage.Database())
        if known:
            print "THANKYOU"
        else:
            print "NEEDMORE"
        # todo save ureport somewhere for further processing
    except Exception as ex:
        print "ERROR {0}".format(str(ex))
