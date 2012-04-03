#!/usr/bin/python
import hashlib
import re

RE_ALNUM = re.compile("^[0-9a-zA-Z]+$")
RE_ALNUMSPACE = re.compile("^[0-9a-zA-Z ]+$")
RE_EXEC = re.compile("^/[0-9a-zA-Z/_\.\-]+$")
RE_FUNCNAME = re.compile("^[0-9a-zA-Z_<>]+$")
RE_HEX = re.compile("^(0[xX])?[0-9a-fA-F]+$")
RE_PACKAGE = re.compile("^[0-9a-zA-Z_\.\+\-]+$")
RE_PHRASE = re.compile("^[0-9a-zA-Z :_/\-\+\*\.\(\)\?\!]+$")
RE_SEPOL = re.compile("^[a-zA-Z0-9_\.\-]+(:[a-zA-Z0-9_\.\-]+){3,4}$")
RE_STATE = re.compile("^(boot|login|logout|sleep|hibernate)$")

RELATED_CHECKER = { "type": str, "re": RE_PACKAGE }

NV_CHECKER = {
  "name": { "mand": True, "type": str, "re": RE_PHRASE },
  "version": { "mand": True, "type": str, "re": RE_PACKAGE }
}

SELINUX_CHECKER = {
  "mode": { "mand": True, "type": str, "re": RE_ALNUM },
  "context": { "mand": True, "type": str, "re": RE_SEPOL },
  "policy": { "mand": True, "type": str, "re": RE_PACKAGE }
}

COREBT_ELEM_CHECKER = {
  "thread": { "mand": True, "type": int },
  "frame": { "mand": True, "type": int },
  "buildid": { "mand": True, "type": str, "re": RE_HEX },
  "path": { "mand": True, "type": str, "re": RE_EXEC },
  "offset": { "mand": True, "type": int },
  "funcname": { "mand": False, "type": str, "re": RE_FUNCNAME },
  "funchash": { "mand": False, "type": str, "re": RE_HEX }
}

COREBT_CHECKER = { "type": dict, "checker": COREBT_ELEM_CHECKER }

PACKAGE_CHECKER = {
  "name": { "mand": True, "type": str, "re": RE_PACKAGE },
  "version": { "mand": True, "type": str, "re": RE_PACKAGE },
  "release": { "mand": True, "type": str, "re": RE_PACKAGE },
}

PROCSTATUS_CHECKER = {

}

PROCLIMITS_CHECKER = {

}

UREPORT_CHECKER = {
  "problemtype": { "mand": True, "type": str, "re": RE_ALNUM },
  "reason": { "mand": True, "type": str, "re": RE_PHRASE },
  "crashtime": { "mand": True, "type": int },
  "uptime": { "mand": True, "type": int },
  "executable": { "mand": True, "type": str, "re": RE_EXEC },
  "package": { "mand": True, "type": dict, "checker": PACKAGE_CHECKER },
  "related_packages": { "mand": True, "type": list, "checker": RELATED_CHECKER },
  "os": { "mand": True, "type": dict, "checker": NV_CHECKER },
  "architecture": { "mand": True, "type": str, "re": RE_FUNCNAME },
  "reporter": { "mand": True, "type": dict, "checker": NV_CHECKER },
  "crash_thread": { "mand": True, "type": int },
  "core_backtrace": { "mand": True, "type": list, "checker": COREBT_CHECKER },
  "user_type": { "mand": False, "type": str, "re": RE_ALNUM },
  "state": { "mand": False, "type": str, "re": RE_STATE },
  "selinux": { "mand": False, "type": dict, "checker": SELINUX_CHECKER },
  "procstatus": { "mand": False, "type": dict, "checker": PROCSTATUS_CHECKER },
  "proclimits": { "mand": False, "type": dict, "checker": PROCLIMITS_CHECKER }
}

def validate(obj, checker=UREPORT_CHECKER):
    objtype = type(obj)
    expected = dict
    if "type" in checker:
        expected = checker["type"]

    # check for expected type
    if not objtype is expected:
        raise Exception, "typecheck failed: expected {0}, had {1}".format(expected, objtype)

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

def get_crashthread(ureport):
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
    # fallback to hashes
    elif hashashes:
        hashbase.extend(["{0} @ {1}".format(x["funchash"], x["path"]) for x in thread])
    else:
        raise Exception, "either function names or function hashes are required"

    return hashlib.sha1("\n".join(hashbase)).hexdigest()

def is_known(ureport, db):
    # workaround - not using upstream yet
    # whole version-release is set under revision
    vr = "{0}-{1}".format(ureport["package"]["version"], ureport["package"]["release"])
    pkg = db.session.query(db.Package).filter((db.Package.name == ureport["package"]["name"]) & \
                                              (db.Build.revision == vr) & \
                                              (db.OpSys.id == ureport["os"]["name"]) & \
                                              (db.OpSysRelease.version == ureport["os"]["version"])).first()

    if pkg is None:
        raise Exception, "unknown package"

    cthread = get_crashthread(ureport)
    uhash = hash_thread(cthread, hashbase=[pkg.build.component.name])

    known = db.session.query(db.BtHash).filter(db.BtHash.bthash == uhash).first()
    return not known is None

# only for debugging purposes
if __name__ == "__main__":
    import pyfaf

    ureport = {
      "problemtype": "python",
      "reason": "TypeError",
      "crashtime": 1333091790,
      "uptime": 1,
      "executable": "/usr/bin/faf-btserver-cgi",
      "package": { "name": "faf", "version": "0.4", "release": "1.fc16" },
      "related_packages": [ "python-2.7.2-5.2.fc16" ],
      "os": { "name": "fedora", "version": "16" },
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
                   "policy": "selinux-policy-3.10.0-80.fc16" },
    }

    try:
        # import json
        # input = some json
        # ureport = json.loads(input)
        validate(ureport)
        known = is_known(ureport, pyfaf.storage.Database())
        if known:
            print "THANKYOU"
        else:
            print "NEEDMORE"
        # todo save ureport somewhere for further processing
    except Exception as ex:
        print "ERROR {0}".format(str(ex))
