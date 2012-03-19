# -*- coding: utf-8 -*-

import os
import pyfaf
import re
from kobo.worker import TaskBase
from subprocess import *

STDOUT_PARSER = re.compile("INFO:root:stdout log: (.*\.log)")
STDERR_PARSER = re.compile("INFO:root:stderr log: (.*\.log)")

BUILDROOT = "/var/lib/faf"

def get_log(candidates, parser):
    for candidate in candidates:
        match = parser.search(candidate)
        if match:
            filename = match.group(1)
            break
    else:
        return None, None

    with open(filename, "r") as f:
        result = f.read()

    return filename.rsplit("/", 1)[1], result

def find_llvm_bc(rootdir):
    result = []
    for f in os.listdir(rootdir):
        fullpath = os.path.join(rootdir, f)
        if os.path.isdir(fullpath):
            result.extend(find_llvm_bc(fullpath))
        elif os.path.isfile(fullpath) and f.endswith(".bc") and f != "a.out.bc":
            result.append(fullpath)

    return result

class LlvmBuild(TaskBase):
    enabled = True

    arches = ["x86_64"]    # list of supported architectures
    channels = ["default"] # list of channels
    exclusive = False      # leave False here unless you really know what you're doing
    foreground = True      # if True the task is not forked and runs in the worker process (no matter you run worker without -f)
    priority = 19
    weight = 1.0

    def run(self):
        srpm = pyfaf.run.cache_get("fedora-koji-rpm", self.args["srpm_id"])

        child = Popen(["faf-llvm-build", str(srpm.id), "-vvv", "--use-llvm-ld", "--use-wrappers"], stdout=PIPE, stderr=PIPE)
        stdout, stderr = child.communicate()
        msg = "=== STDOUT ===\n{0}\n\n=== STDERR ===\n{1}".format(stdout, stderr)

        bcfiles = find_llvm_bc(os.path.join(BUILDROOT, srpm.nvr(), "usr", "src", "rpm", "BUILD"))
        if bcfiles:
            msg += "\n\n=== Bytecode files === \n{0}".format("\n".join(bcfiles))

        outname, buildout = get_log([stdout, stderr], STDOUT_PARSER)
        if outname and buildout:
            msg += "\n\n=== {0} ===\n{1}".format(outname, buildout)

        errname, builderr = get_log([stdout, stderr], STDERR_PARSER)
        if errname and builderr:
            msg += "\n\n=== {0} ===\n{1}".format(errname, builderr)

        if child.wait():
            raise Exception("LLVM build failed with exitcode {0}\n\n{1}".format(child.returncode, msg))

        self.result = "RPM rebuilt successfully\n\n{0}".format(msg)

    @classmethod
    def cleanup(cls, hub, conf, task_info):
        for d in os.listdir(BUILDROOT):
            call(["faf-chroot", "-r", os.path.join(BUILDROOT, d), "clean"])

    @classmethod
    def notification(cls, hub, conf, task_info):
        pass
        # hub.worker.email_<foo>_notification(task_info["id"])
