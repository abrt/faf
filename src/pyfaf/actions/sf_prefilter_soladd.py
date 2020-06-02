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

import sys

from pyfaf.actions import Action
from pyfaf.queries import get_sf_prefilter_sol_by_cause
from pyfaf.storage import SfPrefilterSolution

class SfPrefilterSolAdd(Action):
    name = "sf-prefilter-soladd"


    def run(self, cmdline, db) -> int:
        db_solution = get_sf_prefilter_sol_by_cause(db, cmdline.CAUSE)
        if db_solution is not None:
            self.log_info("There is already a solution associated with "
                          "'{0}'. Try $ {1} sf-prefilter-solshow {2}".format(
                              cmdline.CAUSE, sys.argv[0], db_solution.id))
            return 0

        db_solution = SfPrefilterSolution()
        db_solution.cause = cmdline.CAUSE
        db_solution.note_text = cmdline.NOTE

        if cmdline.url is not None:
            db_solution.url = cmdline.url

        if cmdline.note_html is not None:
            db_solution.note_html = cmdline.note_html

        db.session.add(db_solution)
        db.session.flush()
        return 0

    def tweak_cmdline_parser(self, parser) -> None:
        parser.add_argument("CAUSE", validators=[("InputRequired", {})],
                            help=("The cause of the problem. Will be shown to end-users."))
        parser.add_argument("NOTE", validators=[("InputRequired", {})],
                            help=("Non-formatted text with additional information."))
        parser.add_argument("--url", help=("URL where more information about "
                                           "the issue can be found."))
        parser.add_argument("--note-html", help=("HTML-formatted text with "
                                                 "additional information."))
