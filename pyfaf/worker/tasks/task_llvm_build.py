# -*- coding: utf-8 -*-
import os
import pyfaf
import sys
import subprocess
from kobo.worker import TaskBase
from kobo.worker import FailTaskException
from pyfaf.storage import getDatabase, Package

class LlvmBuild(TaskBase):
    enabled = True

    arches = ["x86_64"]    # list of supported architectures
    channels = ["default"] # list of channels
    exclusive = False      # leave False here unless you really know what you're doing
    foreground = True      # if True the task is not forked and runs in the worker process (no matter you run worker without -f)
    priority = 19
    weight = 1.0

    def run(self):
        db = getDatabase()
        srpm = db.session.query(Package).filter(Package.id == self.args["srpm_id"]).one()
        child = subprocess.Popen(["faf-llvm-build", self.args["srpm_id"], self.args["os"],
                                  self.args["tag"], "-vv", "--use-llvm-ld", "--use-wrappers",
                                  "--save-results"],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        line = child.stdout.readline()
        while line:
            sys.stdout.write(line)
            sys.stdout.flush()
            line = child.stdout.readline()

        if child.wait():
            self.result = "LLVM build failed with exitcode {0}".format(child.returncode)
            raise FailTaskException

        subprocess.call(["faf-chroot", "-r", os.path.join(pyfaf.config.CONFIG["llvmbuild.buildroot"], srpm.nvr()), "clean"])

        self.result = "RPM rebuilt successfully"

    @classmethod
    def cleanup(cls, hub, conf, task_info):
        pass

    @classmethod
    def notification(cls, hub, conf, task_info):
        pass
