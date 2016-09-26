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
from pyfaf.queries import get_report_opsysrelease
from pyfaf.solutionfinders import find_solution
from pyfaf.storage import (Report)


class FindReportSolution(Action):
    name = "find-report-solution"

    def __init__(self):
        super(FindReportSolution, self).__init__()

    def run(self, cmdline, db):
        db.session.autocommit = False
        for report in db.session.query(Report).filter(Report.max_certainty.is_(None)):
            osr = get_report_opsysrelease(db=db, report_id=report.id)
            solutions = [find_solution(report, db=db, osr=osr)]

            if solutions[0] is not None:
                report.max_certainty = max((s.certainty for s in solutions))
                self.log_info("Max_certainty of report '{0}' is changed to {1}".format(report.id, report.max_certainty))

        db.session.commit()
