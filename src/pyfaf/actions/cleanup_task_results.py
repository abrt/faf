# Copyright (C) 2015  ABRT Team
# Copyright (C) 2015  Red Hat, Inc.
#
# This file is part of faf.
#
# faf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# faf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with faf.  If not, see <http://www.gnu.org/licenses/>.

from pyfaf.actions import Action
from pyfaf.storage.task import TaskResult
from datetime import datetime, timedelta


class CleanupTaskResults(Action):
    name = "cleanup-task-results"

    def run(self, cmdline, db):
        if cmdline.keep_days >= 0:
            q = (db.session.query(TaskResult)
                 .filter(TaskResult.finished_time <
                         datetime.now()-timedelta(days=cmdline.keep_days)))
            self.log_info("About to delete {0} task results older than {1} days."
                          .format(q.count(), cmdline.keep_days))
            q.delete()
            db.session.flush()
            self.log_info("Task results deleted".format(q.count()))
        else:
            self.log_warn("--keep-days must be greater or equal to 0.")

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--keep-days", help="keep results for the last D days",
                            default=14, type=int)
