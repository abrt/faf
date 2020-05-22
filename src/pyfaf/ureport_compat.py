import re

from typing import Any, Dict

from pyfaf.common import FafError

try:
    import satyr
except ImportError:
    # Invalid name "satyr" for type constant
    # pylint: disable-msg=C0103
    satyr = None

RE_SIGNAL = re.compile(r"^Process .* was killed by signal ([0-9]+) \([A-Z]+\)$")


def ureport1to2(ureport1) -> Dict[str, Any]:
    """
    Convert uReport1 to uReport2. This has hardcodes plugin names for python,
    coredump and kerneloops. It also adds a soft dependency on satyr library.
    The process is best-effort and strange results may be obtained. Be sure to
    validate the resulting uReport2 after conversion.
    """

    # Too many branches
    # pylint: disable-msg=R0912

    ureport2 = {"ureport_version": 2, "problem": {}, "os": {}, "packages": []}

    # make sure we are converting uReport1
    if "ureport_version" not in ureport1 or ureport1["ureport_version"] != 1:
        raise FafError("uReport1 is required")

    # problem type
    if "type" in ureport1:
        if ureport1["type"].lower() == "userspace":
            ureport2["problem"]["type"] = "core"
        else:
            ureport2["problem"]["type"] = ureport1["type"].lower()

    # operating system - quite straightforward
    if "os" in ureport1:
        if "name" in ureport1["os"]:
            ureport2["os"]["name"] = ureport1["os"]["name"].lower()

        if "version" in ureport1["os"]:
            ureport2["os"]["version"] = ureport1["os"]["version"]

    if "architecture" in ureport1:
        ureport2["os"]["architecture"] = ureport1["architecture"]

    # selinux
    if "selinux" in ureport1:
        ureport2["os"]["selinux"] = {}
        if "mode" in ureport1["selinux"]:
            ureport2["os"]["selinux"]["mode"] = ureport1["selinux"]["mode"]

        if "context" in ureport1["selinux"]:
            ureport2["os"]["selinux"]["context"] = \
                ureport1["selinux"]["context"]

        if "policy_package" in ureport1["selinux"]:
            newpkg = dict(ureport1["selinux"]["policy_package"])
            newpkg["package_role"] = "selinux_policy"
            ureport2["packages"].append(newpkg)

    # component
    if "component" in ureport1:
        ureport2["problem"]["component"] = ureport1["component"]

    # executable
    if "executable" in ureport1:
        ureport2["problem"]["executable"] = ureport1["executable"]

    # reason + exception name / signal number
    if "reason" in ureport1:
        ureport2["reason"] = ureport1["reason"]

        if ureport1["type"].lower() == "python":
            ureport2["problem"]["exception_name"] = "reason"

        if ureport1["type"].lower() == "userspace":
            match = RE_SIGNAL.match(ureport1["reason"])
            if match:
                ureport2["problem"]["signal"] = int(match.group(1))

    # just copy reporter - the format did not change
    if "reporter" in ureport1:
        ureport2["reporter"] = ureport1["reporter"]

    # packages - the NEVRA dict remains the same
    if "installed_package" in ureport1:
        newpkg = dict(ureport1["installed_package"])
        newpkg["package_role"] = "affected"
        ureport2["packages"].append(newpkg)

    if "running_package" in ureport1:
        ureport2["packages"].append(dict(ureport1["running_package"]))

    if "related_packages" in ureport1:
        for relpkg in ureport1["related_packages"]:
            if "running_package" in relpkg:
                ureport2["packages"].append(dict(relpkg["running_package"]))

            if "installed_package" in relpkg:
                ureport2["packages"].append(dict(relpkg["installed_package"]))

    # map core backtrace into uReport2 structures
    if "core_backtrace" in ureport1:
        # python
        if ureport1["type"].lower() == "python":
            ureport2["problem"]["stacktrace"] = []
            cb = sorted(ureport1["core_backtrace"], key=lambda f: f["frame"])
            for frame in cb:
                newframe = {"line_contents": "", }

                if "path" in frame:
                    newframe["file_name"] = frame["path"]

                if "offset" in frame:
                    newframe["file_line"] = frame["offset"]

                if "funcname" in frame:
                    if (frame["funcname"].startswith("<") and
                            frame["funcname"].endswith(">")):

                        funcname = frame["funcname"].strip("<>")
                        newframe["special_function"] = funcname
                    else:
                        newframe["function_name"] = frame["funcname"]

                if "buildid" in frame:
                    newframe["build_id"] = frame["buildid"]

                ureport2["problem"]["stacktrace"].append(newframe)

        # coredump
        if ureport1["type"].lower() == "userspace":
            ureport2["problem"]["stacktrace"] = []

            # group frame list into threads
            threads = {}
            cb = sorted(ureport1["core_backtrace"],
                        key=lambda f: (f["thread"], f["frame"]))

            for frame in cb:
                if frame["thread"] not in threads:
                    threads[frame["thread"]] = []

                threads[frame["thread"]].append(frame)

            for thread, frames in sorted(threads.items()):
                newthread = {
                    "crash_thread": thread == ureport1["crash_thread"],
                    "frames": []
                }

                for frame in frames:
                    newframe = {"address": 0, }

                    if "buildid" in frame:
                        newframe["build_id"] = frame["buildid"]

                    if "offset" in frame:
                        newframe["build_id_offset"] = frame["offset"]

                    if "path" in frame:
                        newframe["file_name"] = frame["path"]

                    if "funcname" in frame:
                        newframe["function_name"] = frame["funcname"]

                    if "funchash" in frame:
                        newframe["fingerprint"] = frame["funchash"]

                    newthread["frames"].append(newframe)

                ureport2["problem"]["stacktrace"].append(newthread)

        # kerneloops
        if ureport1["type"].lower() == "kerneloops":
            # in uReport1 there is not enough information to fill uReport2
            # let's try to use satyr library to parse the raw kerneloops
            # or skip this entirely even though the result will be an invalid
            # report
            if "oops" in ureport1 and satyr is not None:
                ureport2["problem"]["raw_oops"] = ureport1["oops"]

                if "core_backtrace" in ureport1:
                    for frame in ureport1["core_backtrace"]:
                        if "buildid" in frame:
                            ureport2["problem"]["version"] = frame["buildid"]
                            break

                koops = satyr.Kerneloops(ureport1["oops"])

                ureport2["problem"]["modules"] = koops.modules

                ureport2["problem"]["frames"] = []
                for frame in koops.frames:
                    newframe = {
                        "address": frame.address,
                        "reliable": frame.reliable,
                        "function_name": frame.function_name,
                        "function_offset": frame.function_offset,
                        "function_length": frame.function_length,
                    }

                    if frame.from_function_offset is not None:
                        newframe["from_function_offset"] = \
                            frame.from_function_offset

                    if frame.from_function_length is not None:
                        newframe["from_function_length"] = \
                            frame.from_function_length

                    if (frame.module_name is not None and
                            frame.module_name != "vmlinux"):
                        newframe["module_name"] = frame.module_name

                    ureport2["problem"]["frames"].append(newframe)

                # older versions of satyr do not export taint_flags
                if hasattr(koops, "taint_flags"):
                    ureport2["problem"]["taint_flags"] = []
                    for flag, value in koops.taint_flags.items():
                        if value:
                            ureport2["problem"]["taint_flags"].append(flag)

    # coredump requires user specs, use some defaults
    if ureport1["type"].lower() == "userspace":
        ureport2["problem"]["user"] = {"local": True, "root": False}
    else:
        ureport2["problem"]["user"] = {}

    # sometimes even uReport1 provides the user data but in a different format
    if "user_type" in ureport1:
        if ureport1["user_type"].lower() == "root":
            ureport2["problem"]["user"]["root"] = True

        if ureport1["user_type"].lower() == "nologin":
            ureport2["problem"]["user"]["nologin"] = True

        if ureport1["user_type"].lower() == "local":
            ureport2["problem"]["user"]["local"] = True

        if ureport1["user_type"].lower() == "remote":
            ureport2["problem"]["user"]["local"] = False

    # raw kernel oops text
    if ureport1["type"].lower() == "kerneloops" and "oops" in ureport1:
        ureport2["problem"]["raw_oops"] = ureport1["oops"]

    return ureport2
