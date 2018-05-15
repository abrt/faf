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
from pyfaf.queries import (get_sf_prefilter_btpaths_by_solution,
                           get_sf_prefilter_pkgnames_by_solution,
                           get_sf_prefilter_sol,
                           get_sf_prefilter_sols)


class SfPrefilterPatShow(Action):
    name = "sf-prefilter-patshow"

    def __init__(self):
        super(SfPrefilterPatShow, self).__init__()

    def run(self, cmdline, db):
        if len(cmdline.SOLUTION_ID) < 1:
            db_solutions = get_sf_prefilter_sols(db)
        else:
            db_solutions = []
            for solution_id in cmdline.SOLUTION_ID:
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

            print("Solution #{0}: {1}".format(db_solution.id, db_solution.cause))

            db_btpaths = get_sf_prefilter_btpaths_by_solution(db, db_solution)
            for db_btpath in db_btpaths:
                if db_btpath.opsys is not None:
                    opsys_str = (" (only valid for '{0}' operating system)"
                                 .format(db_btpath.opsys.name))
                else:
                    opsys_str = ""

                print("Stacktrace path pattern: {0}{1}"
                      .format(db_btpath.pattern, opsys_str))

            db_pkgnames = get_sf_prefilter_pkgnames_by_solution(db, db_solution)
            for db_pkgname in db_pkgnames:
                if db_pkgname.opsys is not None:
                    opsys_str = (" (only valid for '{0}' operating system)"
                                 .format(db_pkgname.opsys.name))
                else:
                    opsys_str = ""

                print("Package name pattern: {0}{1}"
                      .format(db_pkgname.pattern, opsys_str))

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("SOLUTION_ID", nargs="*",
                            help="The ID of the solution or cause.")
