# -*- coding: utf-8 -*-
import os
import pyfaf
import signal
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

    def terminate(self, signo, frame):
        self.child.terminate()
        self.child.stdout.close()
        self.result = "Reached timeout {0} seconds.".format(self.timeout)
        raise FailTaskException

    def run(self):
        db = getDatabase()
        srpm = db.session.query(Package).filter(Package.id == self.args["srpm_id"]).one()

        try:
            self.timeout = int(pyfaf.config.CONFIG["llvmbuild.maxbuildtimesec"])
        except Exception as ex:
            self.result = "Error converting config 'llvmbuild.maxbuildtimesec' to integer: {0}".format(str(ex))
            raise FailTaskException

        self.killed = False
        signal.signal(signal.SIGALRM, self.terminate)
        signal.alarm(self.timeout)

        self.child = subprocess.Popen(["faf-llvm-build", self.args["srpm_id"], self.args["os"],
                                       self.args["tag"], "-vv", "--use-llvm-ld", "--use-wrappers",
                                       "--save-results"],
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        line = self.child.stdout.readline()
        while line:
            sys.stdout.write(line)
            sys.stdout.flush()
            line = None if self.child.stdout.closed else self.child.stdout.readline()

        if self.child.wait():
            self.result = "LLVM build failed with exitcode {0}".format(self.child.returncode)
            raise FailTaskException

        signal.alarm(0)

        self.result = "RPM rebuilt successfully"

    @classmethod
    def cleanup(cls, hub, conf, task_info):
        # aggressively clean up everything
        buildroot = pyfaf.config.CONFIG["llvmbuild.buildroot"]
        for dirname in os.listdir(buildroot):
            subprocess.call(["faf-chroot", "-r", os.path.join(buildroot, dirname), "clean"])

    @classmethod
    def notification(cls, hub, conf, task_info):
        pass
