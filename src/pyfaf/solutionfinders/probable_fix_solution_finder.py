# Copyright (C) 2014  ABRT Team
# Copyright (C) 2014  Red Hat, Inc.
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

import re
from pyfaf.solutionfinders import SolutionFinder, Solution
from pyfaf.common import log
from pyfaf.opsys import systems
from pyfaf.problemtypes import problemtypes
from pyfaf.queries import (get_sf_prefilter_btpaths, get_sf_prefilter_pkgnames,
                           get_opsys_by_name)
from pyfaf.ureport_compat import ureport1to2


class ProbableFixSolutionFinder(SolutionFinder):
    name = "sf-probable-fix"
    nice_name = "Probable Fix Solution"

    def find_solution_db_report(self, db, db_report, osr):
        if db_report is None:
            return None

        if db_report.problem is None:
            return None

        for posr in db_report.problem.opsysreleases:
            if osr is None or posr.opsysrelease_id == osr.id:
                if posr.probable_fix:
                    text = ("A new package version is available in which the "
                            "problem has not yet occured. Please update to "
                            "the following version and delete the ABRT problem:\n{}"
                            .format(posr.probable_fix))
                    html = ("A new package version is available in which the "
                            "problem has not yet occured. Please consider "
                            "updating to at least the following version:"
                            "<br/><pre>{}</pre>"
                            .format(posr.probable_fix))
                    since = None
                    if posr.probably_fixed_since:
                        since = posr.probably_fixed_since
                    return Solution(cause="Outdated package",
                                    url="",
                                    note_text=text,
                                    note_html=html,
                                    since=since)

        return None
