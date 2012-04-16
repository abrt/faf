#!/usr/bin/python
import datetime
import hashlib
import re

RE_ALNUM = re.compile("^[0-9a-zA-Z]+$")
RE_ALNUMSPACE = re.compile("^[0-9a-zA-Z ]+$")
RE_EXEC = re.compile("^/[0-9a-zA-Z/_\.\-]+$")
RE_FUNCNAME = re.compile("^[0-9a-zA-Z_<>]+$")
RE_HEX = re.compile("^(0[xX])?[0-9a-fA-F]+$")
RE_PACKAGE = re.compile("^[0-9a-zA-Z_\.\+\-~]+$")
RE_PHRASE = re.compile("^[0-9a-zA-Z :_/\-\+\*\.\(\)\?\!]+$")
RE_SEPOL = re.compile("^[a-zA-Z0-9_\.\-]+(:[a-zA-Z0-9_\.\-]+){3,4}$")

PACKAGE_CHECKER = {
  "name":         { "mand": True, "type": str, "re": RE_PACKAGE },
  "version":      { "mand": True, "type": str, "re": RE_PACKAGE },
  "release":      { "mand": True, "type": str, "re": RE_PACKAGE },
  "architecture": { "mand": True, "type": str, "re": RE_PHRASE },
  "epoch":        { "mand": True, "type": int }
}

RELATED_PACKAGES_ELEM_CHECKER = {
    "installed_package": { "mand": True,  "type": dict, "checker": PACKAGE_CHECKER },
    "running_package":   { "mand": False, "type": dict, "checker": PACKAGE_CHECKER }
}

RELATED_PACKAGES_CHECKER = { "type": dict, "checker": RELATED_PACKAGES_ELEM_CHECKER }

NV_CHECKER = {
  "name":    { "mand": True, "type": str, "re": RE_PHRASE },
  "version": { "mand": True, "type": str, "re": RE_PACKAGE }
}

SELINUX_CHECKER = {
  "mode":           { "mand": True,  "type": str , "re": re.compile("^(enforcing|permissive|disabled)$") },
  "context":        { "mand": False, "type": str,  "re": RE_SEPOL },
  "policy_package": { "mand": False, "type": dict, "checker": PACKAGE_CHECKER }
}

COREBT_ELEM_CHECKER = {
  "thread":   { "mand": True, "type": int },
  "frame":    { "mand": True, "type": int },
  "buildid":  { "mand": True, "type": str, "re": RE_HEX },
  "path":     { "mand": True, "type": str, "re": RE_EXEC },
  "offset":   { "mand": True, "type": int },
  "funcname": { "mand": False, "type": str, "re": RE_FUNCNAME },
  "funchash": { "mand": False, "type": str, "re": RE_HEX }
}

COREBT_CHECKER = { "type": dict, "checker": COREBT_ELEM_CHECKER }

PROC_STATUS_CHECKER = {

}

PROC_LIMITS_CHECKER = {

}

OS_STATE_CHECKER = {
    "suspend":  { "mand": True, "type": str, "re": re.compile("^(yes|no)$") },
    "boot":     { "mand": True, "type": str, "re": re.compile("^(yes|no)$") },
    "login":    { "mand": True, "type": str, "re": re.compile("^(yes|no)$") },
    "logout":   { "mand": True, "type": str, "re": re.compile("^(yes|no)$") },
    "shutdown": { "mand": True, "type": str, "re": re.compile("^(yes|no)$") }
}

UREPORT_CHECKER = {
  "type":              { "mand": True,  "type": str,  "re": re.compile("^(PYTHON|USERSPACE|KERNELOOPS)$") },
  "reason":            { "mand": True,  "type": str,  "re": RE_PHRASE },
  "uptime":            { "mand": True,  "type": int },
  "executable":        { "mand": True,  "type": str,  "re": RE_EXEC },
  "installed_package": { "mand": True,  "type": dict, "checker": PACKAGE_CHECKER },
  "running_package":   { "mand": False, "type": dict, "checker": PACKAGE_CHECKER },
  "related_packages":  { "mand": True,  "type": list, "checker": RELATED_PACKAGES_CHECKER },
  "os":                { "mand": True,  "type": dict, "checker": NV_CHECKER },
  "architecture":      { "mand": True,  "type": str,  "re": RE_PHRASE },
  "reporter":          { "mand": True,  "type": dict, "checker": NV_CHECKER },
  "crash_thread":      { "mand": True,  "type": int },
  "core_backtrace":    { "mand": True,  "type": list, "checker": COREBT_CHECKER },
  "user_type":         { "mand": False, "type": str,  "re": re.compile("^(root|nologin|local|remote)$") },
  "os_state":          { "mand": False, "type": dict,  "checker": OS_STATE_CHECKER },
  "selinux":           { "mand": False, "type": dict, "checker": SELINUX_CHECKER },
  "proc_status":       { "mand": False, "type": dict, "checker": PROC_STATUS_CHECKER },
  "proc_limits":       { "mand": False, "type": dict, "checker": PROC_LIMITS_CHECKER }
}

def validate(obj, checker=UREPORT_CHECKER):
    objtype = type(obj)
    expected = dict
    if "type" in checker and isinstance(checker["type"], type):
        expected = checker["type"]

    # check for expected type
    if not objtype is expected:
        raise Exception, "typecheck failed: expected {0}, had {1}; {2}".format(expected, objtype, obj)

    # str must match regexp
    if objtype is str and checker["re"].match(obj) is None:
        raise Exception, "contains illegal characters"
    # list - apply checker["checker"] to every element
    elif objtype is list:
        for elem in obj:
            validate(elem, checker["checker"])
    # dict
    elif objtype is dict:
        # load the actual checker if we are not toplevel
        if "checker" in checker:
            checker = checker["checker"]

        # need to clone, we are going to modify
        clone = dict(obj)
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
                validate(value, subchkr)
            except Exception, msg:
                # queue error messages
                raise Exception, "error validating '{0}': {1}".format(key, msg)

        # excessive elements - error
        keys = clone.keys()
        if keys:
            raise Exception, "unknown elements present: {0}".format(keys)

def get_crash_thread(ureport):
    result = []
    for frame in ureport["core_backtrace"]:
        if frame["thread"] == ureport["crash_thread"]:
            result.append(frame)

    return sorted(result, key=lambda x: x["frame"])

def hash_thread(thread, hashbase=[]):
    hasnames = all(["funcname" in x and not x["funcname"] is None for x in thread])
    hashashes = all(["funchash" in x and not x["funchash"] is None for x in thread])
    # use function names if available
    if hasnames:
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
    return db.session.query(db.Package).join(db.Package.arch).join(db.Package.build).\
            join(db.Build.component).join(db.OpSysComponent.opsysreleases).\
            join(db.OpSysRelease.opsys).\
            filter(db.Package.name == ureport_package["name"],
                   db.Build.epoch == ureport_package["epoch"],
                   db.Build.version == ureport_package["version"],
                   db.Build.release == ureport_package["release"],
                   db.Arch.name == ureport_package["architecture"],
                   db.OpSys.name == ureport_os["name"],
                   db.OpSysRelease.version == ureport_os["version"]).first()

def get_report_hash(ureport, package):
    cthread = get_crash_thread(ureport)
    # Hash only up to first 16 frames.
    cthread = cthread[:16]
    return hash_thread(cthread, hashbase=[package.build.component.name])

def add_report(ureport, db, only_check_if_known=False):
    utcnow = datetime.datetime.utcnow()

    package = get_package(ureport["installed_package"], ureport["os"], db)
    if package is None:
        raise Exception, "Unknown installed package."

    hash_type, hash_hash = get_report_hash(ureport, package)

    # Find a report with matching hash and component.
    report = db.session.query(db.Report).join(db.ReportBacktrace).join(db.ReportBtHash).\
            filter(db.ReportBtHash.hash == hash_hash,
                   db.ReportBtHash.type == hash_type,
                   db.Report.component == package.build.component).first()

    if only_check_if_known:
        return bool(report)

    # Create a new report if not found.
    if not report:
        report = db.Report()
        report.type = ureport["type"]
        report.first_occurence = report.last_occurence = utcnow
        report.component = package.build.component
        db.session.add(report)

        report_backtrace = db.ReportBacktrace()
        report_backtrace.report = report
        db.session.add(report_backtrace)

        report_bthash = db.ReportBtHash()
        report_bthash.type = hash_type
        report_bthash.hash = hash_hash
        report_bthash.backtrace = report_backtrace
        db.session.add(report_bthash)

        # Add frames, symbols, hashes and sources.
        for frame in get_crash_thread(ureport):
            report_btframe = db.ReportBtFrame()
            report_btframe.backtrace = report_backtrace
            report_btframe.order = frame["frame"]

            # TODO: use proper normalization
            normalized_path = frame["path"]

            if "funcname" in frame:
                symbol = db.session.query(db.Symbol).\
                        filter(db.Symbol.name == frame["funcname"],
                               db.Symbol.normalized_path == normalized_path).first()
            else:
                symbol = None

            symbolhash = None
            symbolsource = None

            # Create a new symbol if not found or unknown name.
            if not symbol:
                symbol = db.Symbol()
                symbol.normalized_path = normalized_path
                if "funcname" in frame:
                    symbol.name = frame["funcname"]
                db.session.add(symbol)
            else:
                if "funchash" in frame:
                    symbolhash = db.session.query(db.SymbolHash).\
                            filter(db.SymbolHash.symbol == symbol,
                                   db.SymbolHash.hash == frame["funchash"]).first()

                symbolsource = db.session.query(db.SymbolSource).\
                        filter(db.SymbolSource.symbol == symbol,
                               db.SymbolSource.build_id == frame["buildid"],
                               db.SymbolSource.path == frame["path"],
                               db.SymbolSource.offset == frame["offset"]).first()

            # Create a new symbolhash if not found or with new symbol.
            if not symbolhash and "funchash" in frame:
                symbolhash = db.SymbolHash()
                symbolhash.symbol = symbol
                symbolhash.hash = frame["funchash"]
                db.session.add(symbolhash)

            # Create a new symbolsource if not found or with new symbol.
            if not symbolsource:
                symbolsource = db.SymbolSource()
                symbolsource.symbol = symbol
                symbolsource.build_id = frame["buildid"]
                symbolsource.path = frame["path"]
                symbolsource.offset = frame["offset"]
                db.session.add(symbolsource)

            report_btframe.symbol = symbol

            db.session.add(report_btframe)

    else:
        report.last_occurence = utcnow

    # Update various stats.

    opsysrelease = db.session.query(db.OpSysRelease).join(db.OpSys).filter(\
            db.OpSysRelease.version == ureport["os"]["version"],
            db.OpSys.name == ureport["os"]["name"]).one()

    arch = db.session.query(db.Arch).filter_by(name=ureport['architecture']).one()

    day = datetime.date.today()
    week = day - datetime.timedelta(days=day.weekday())
    month = day.replace(day=1)

    if "running_package" in ureport:
        running_package = get_package(ureport["running_package"], ureport["os"], db)
        if not running_package:
            raise Exception, "Unknown running package."
    else:
        running_package = None

    stat_map = [(db.ReportPackage, [("installed_package", package),
                                    ("running_package", running_package)]),
                (db.ReportArch, [("arch", arch)]),
                (db.ReportOpSysRelease, [("opsysrelease", opsysrelease)]),
                (db.ReportExecutable, [("path", ureport["executable"])]),
                (db.ReportHistoryMonthly, [("month", month)]),
                (db.ReportHistoryWeekly, [("week", week)]),
                (db.ReportHistoryDaily, [("day", day)])]

    # Add related packages to stat_map.
    if "related_packages" in ureport:
        for related_package in ureport["related_packages"]:
            if "installed_package" not in related_package:
                continue
            related_installed_package = get_package(related_package["installed_package"], ureport["os"], db)
            if not related_installed_package:
                raise Exception, "Unknown related installed package."

            if "running_package" in related_package:
                related_running_package = get_package(related_package["running_package"], ureport["os"], db)
                if not related_running_package:
                    raise Exception, "Unknown related running package."
            else:
                related_running_package = None

            stat_map.append((db.ReportRelatedPackage, [("installed_package", related_installed_package),
                                                       ("running_package", related_running_package)]))

    # Create missing stats and increase counters.
    for table, cols in stat_map:
        report_stat_query = db.session.query(table).join(db.Report).filter(db.Report.id == report.id)
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
        report_stat.count += 1

def is_known(ureport, db):
    return add_report(ureport, db, only_check_if_known=True)

def convert_to_str(obj):
    if type(obj) in (int, float, str, bool):
        return obj
    elif type(obj) == unicode:
        return str(obj)
    elif type(obj) in (list, tuple):
        obj = [convert_to_str(v) for v in obj]
    elif type(obj) == dict:
        for n, v in obj.iteritems():
            obj[n] = convert_to_str(v)
    else:
        assert False
    return obj

# only for debugging purposes
if __name__ == "__main__":
    import pyfaf

    ureport = {
      "type": "PYTHON",
      "reason": "TypeError",
      "uptime": 1,
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
                                       "release": "80.fc16",
                                       "epoch": 0,
                                       "architecture": "noarch" } },
    }

    try:
        # import json
        # input = some json
        # ureport = convert_to_str(json.loads(input))
        validate(ureport)
        known = is_known(ureport, pyfaf.storage.Database())
        if known:
            print "THANKYOU"
        else:
            print "NEEDMORE"
        # todo save ureport somewhere for further processing
    except Exception as ex:
        print "ERROR {0}".format(str(ex))
