# -*- coding: utf-8 -*-

import sys
from kobo.worker import TaskBase
from kobo.worker import FailTaskException
from subprocess import Popen, PIPE, STDOUT

class GenerateOptimizedBacktraces(TaskBase):
    enabled = True

    arches = ["noarch"]    # list of supported architectures
    channels = ["default"] # list of channels
    exclusive = False      # leave False here unless you really know what you're doing
    foreground = True      # if True the task is not forked and runs in the worker process (no matter you run worker without -f)
    priority = 19
    weight = 1.0

    def run(self):
        if len(self.args) > 0:
            self.result = "No argumets are expected"
            raise FailTaskException

        child = Popen(["faf-btserver-create-optimized-backtraces", "-v"], stdout=PIPE, stderr=STDOUT)
        line = child.stdout.readline()
        while line:
            sys.stdout.write(line)
            sys.stdout.flush()
            line = child.stdout.readline()

        retcode = child.wait()
        child.stdout.close()
        if retcode:
            self.result = "faf-btserver-create-optimized-backtraces exitted with {0}".format(retcode)
            raise FailTaskException

        self.result = "Optimized backtraces generated successfully"

    @classmethod
    def cleanup(cls, hub, conf, task_info):
        pass

    @classmethod
    def notification(cls, hub, conf, task_info):
        pass
        # hub.worker.email_<foo>_notification(task_info["id"])
