# -*- coding: utf-8 -*-
import os
import pyfaf
import sys
from kobo.worker import TaskBase
from kobo.worker import FailTaskException
from stat import ST_CTIME
from subprocess import Popen, PIPE, STDOUT

class GenerateReportsBugzilla(TaskBase):
    enabled = True

    arches = ["noarch"]    # list of supported architectures
    channels = ["default"] # list of channels
    exclusive = False      # leave False here unless you really know what you're doing
    foreground = True      # if True the task is not forked and runs in the worker process (no matter you run worker without -f)
    priority = 19
    weight = 1.0

    def run(self):
        if len(self.args) > 0:
            self.result = "No arguments expected"
            raise FailTaskException

        incoming_dir = os.path.join(pyfaf.config.CONFIG["report.spooldirectory"], "incoming")
        saved_dir = os.path.join(pyfaf.config.CONFIG["report.spooldirectory"], "saved")
        files = [os.path.join(saved_dir, filename) for filename in os.listdir(saved_dir)]
        newest = sorted([(os.stat(filename)[ST_CTIME], filename) for filename in files])[-1][1]

        child = Popen(["faf-generate-reports-bugzilla", incoming_dir, "--newer-than",
                       newest, "-v"], stdout=PIPE, stderr=STDOUT)
        line = child.stdout.readline()
        while line:
            sys.stdout.write(line)
            sys.stdout.flush()
            line = child.stdout.readline()

        retcode = child.wait()
        child.stdout.close()
        if retcode:
            self.result = "faf-generate-reports-bugzilla exitted with {0}".format(retcode)
            raise FailTaskException

        self.result = "Reports generated successfully"

    @classmethod
    def cleanup(cls, hub, conf, task_info):
        pass

    @classmethod
    def notification(cls, hub, conf, task_info):
        pass
        # hub.worker.email_<foo>_notification(task_info["id"])
