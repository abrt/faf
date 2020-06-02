# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
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
from pyfaf.bugtrackers import bugtrackers


class PullAbrtBugs(Action):
    name = "pull-abrt-bugs"

    def run(self, cmdline, db) -> int:
        if cmdline.bugtracker:
            tracker = bugtrackers[cmdline.bugtracker]
            if not tracker.installed(db):
                self.log_error("Bugtracker is not installed")
                return 1

            self.log_info("Processing bugtracker: {0}"
                          .format(cmdline.bugtracker))
            for bug_id in tracker.list_bugs():
                tracker.download_bug_to_storage(db, bug_id)

            return 0

        self.log_info("Processing all bugtrackers")
        for name, tracker in bugtrackers.items():
            self.log_info("Processing bugtracker: {0}".format(name))
            if not tracker.installed(db):
                self.log_info("Bugtracker {0} not installed, skipping"
                              .format(name))
                continue

            for bug_id in tracker.list_bugs():
                tracker.download_bug_to_storage(db, bug_id)

        return 0

    def tweak_cmdline_parser(self, parser) -> None:
        parser.add_bugtracker()
