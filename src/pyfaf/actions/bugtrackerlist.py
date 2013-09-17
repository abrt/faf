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
from pyfaf.queries import get_bugtracker_by_name
from pyfaf.bugtrackers import bugtrackers
from pyfaf.storage.bugtracker import Bugtracker
from pyfaf.utils.format import as_table


class BugtrackerList(Action):
    name = "bugtrackerlist"

    def run(self, cmdline, db):
        if cmdline.detailed:
            data = []
            header = ["Name", "Installed", "API URL", "Web URL"]
            for tracker in bugtrackers:
                db_tracker = get_bugtracker_by_name(db, tracker)

                installed = "No"
                if db_tracker:
                    installed = "Yes"
                    tracker = db_tracker

                data.append((tracker, installed, tracker.api_url,
                             tracker.web_url))

            print(as_table(header, data, margin=2))
        else:
            for tracker in db.session.query(Bugtracker):
                print(tracker)

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--detailed", action="store_true",
                            help="detailed view")
