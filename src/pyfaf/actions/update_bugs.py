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
from pyfaf.storage.bugtracker import Bugtracker
from pyfaf.queries import get_bugtracker_by_name


class UpdateBugs(Action):
    name = "update-bugs"

    def run(self, cmdline, db):
        if cmdline.bugtracker:
            tracker = bugtrackers[cmdline.bugtracker]
            if not tracker.installed(db):
                self.log_error("Bugtracker is not installed")
                return 1

            dbtracker = get_bugtracker_by_name(db, cmdline.bugtracker)
            buglist = dbtracker.bugs
            self.update_bugs(db, tracker, buglist)

        else:
            for dbtracker in db.session.query(Bugtracker):
                tracker = bugtrackers[dbtracker.name]
                buglist = dbtracker.bugs
                self.update_bugs(db, tracker, buglist)

    def update_bugs(self, db, tracker, buglist):
        if not buglist:
            self.log_info("Found no bugs associated with this bugtracker")

        total = len(buglist)
        for num, bug in enumerate(buglist):
            self.log_debug("[{0} / {1}] Updating bug {2}"
                           .format(num + 1, total, bug.id))

            tracker.download_bug_to_storage(db, bug.id)

    def tweak_cmdline_parser(self, parser):
        parser.add_bugtracker(help="update bugs only from this bug tracker")
