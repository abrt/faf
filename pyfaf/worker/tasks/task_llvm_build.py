# -*- coding: utf-8 -*-

import os
import pyfaf
import re
import sys
from kobo.worker import TaskBase
from kobo.worker import FailTaskException
from subprocess import *

BUILDROOT = "/var/lib/faf"

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
        child = Popen(["faf-llvm-build", str(srpm.id), "-vv", "--use-llvm-ld",
                       "--use-wrappers", "--save-results"], stdout=PIPE, stderr=STDOUT)

        line = child.stdout.readline()
        while line:
            sys.stdout.write(line)
            sys.stdout.flush()
            line = child.stdout.readline()

        if child.wait():
            self.result = "LLVM build failed with exitcode {0}".format(child.returncode)
            raise FailTaskException

        call(["faf-chroot", "-r", os.path.join(BUILDROOT, srpm.nvr()), "clean"])

        self.result = "RPM rebuilt successfully"

    @classmethod
    def cleanup(cls, hub, conf, task_info):
        pass

    @classmethod
    def notification(cls, hub, conf, task_info):
        pass
        # hub.worker.email_<foo>_notification(task_info["id"])
