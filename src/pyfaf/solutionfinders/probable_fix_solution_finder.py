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

from pyfaf.solutionfinders import SolutionFinder, Solution
from pyfaf.ureport import ureport2, validate
from pyfaf.utils.parse import cmp_evr


class ProbableFixSolutionFinder(SolutionFinder):
    name = "sf-probable-fix"
    nice_name = "Probable Fix Solution"

    def _posr_to_solution(self, posr):
        text = ("A new package version is available in which the "
                "problem has not yet occurred. Please update to "
                "the following version and delete the ABRT problem:\n{0}"
                .format(posr.probable_fix))
        html = ("A new package version is available in which the "
                "problem has not yet occurred. Please consider "
                "updating to at least the following version:"
                "<br/><pre>{0}</pre>"
                .format(posr.probable_fix))
        since = None
        if posr.probably_fixed_since:
            since = posr.probably_fixed_since
        return Solution(cause="Outdated package",
                        url="",
                        note_text=text,
                        note_html=html,
                        since=since,
                        stype=self.name,
                        certainty=Solution.ALMOST_THE_SAME
                       )

    def find_solution_ureport(self, db, ureport, osr=None):
        ureport = ureport2(ureport)
        validate(ureport)
        db_report = self._get_db_report(db, ureport)
        if db_report is None:
            return None

        if db_report.problem is None:
            return None

        for posr in db_report.problem.opsysreleases:
            if osr is None or posr.opsysrelease_id == osr.id:
                if posr.probable_fix_build is not None:
                    db_build = posr.probable_fix_build
                    for pkg in ureport["packages"]:
                        if pkg.get("package_role", "") == "affected":
                            break
                    if pkg.get("package_role", "") != "affected":
                        return None
                    # Fixing version must be greater than affected version
                    if cmp_evr((pkg["epoch"], pkg["version"], pkg["release"]),
                               (db_build.epoch, db_build.version, db_build.release)) < 0:
                        return self._posr_to_solution(posr)

                    return None
        return None

    def find_solution_db_report(self, db, db_report, osr):
        if db_report is None:
            return None

        if db_report.problem is None:
            return None

        for posr in db_report.problem.opsysreleases:
            if osr is None or posr.opsysrelease_id == osr.id:
                if posr.probable_fix:
                    return self._posr_to_solution(posr)

        return None
