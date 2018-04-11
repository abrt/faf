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
from pyfaf.queries import get_sf_prefilter_sol, get_sf_prefilter_sols


class SfPrefilterSolShow(Action):
    name = "sf-prefilter-solshow"

    def __init__(self):
        super(SfPrefilterSolShow, self).__init__()

    def run(self, cmdline, db):
        if len(cmdline.ID) < 1:
            db_solutions = get_sf_prefilter_sols(db)
        else:
            db_solutions = []
            for solution_id in cmdline.ID:
                db_solution = get_sf_prefilter_sol(db, solution_id)

                if db_solution is None:
                    self.log_warn("Solution '{0}' not found"
                                  .format(solution_id))
                    continue

                db_solutions.append(db_solution)

        first = True
        for db_solution in db_solutions:
            if first:
                first = False
            else:
                print("----------")

            print("Solution #{0}".format(db_solution.id))

            print("Cause: {0}".format(db_solution.cause))

            if db_solution.url is not None:
                print("URL: {0}".format(db_solution.url))

            if "\n" in db_solution.note_text:
                print("Note:\n{0}".format(db_solution.note_text))
            else:
                print("Note: {0}".format(db_solution.note_text))

            if db_solution.note_html is not None:
                if "\n" in db_solution.note_text:
                    print("HTML Note:\n{0}".format(db_solution.note_html))
                else:
                    print("HTML Note: {0}".format(db_solution.note_html))

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("ID", nargs="*",
                            help="The ID of the solution or cause.")
