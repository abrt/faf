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

import satyr
from pyfaf.actions import Action
from pyfaf.problemtypes import problemtypes
from pyfaf.queries import get_problems, get_reports_by_type
from pyfaf.storage import Problem, ProblemComponent, Report


class CreateProblems(Action):
    name = "create-problems"

    def __init__(self):
        super(CreateProblems, self).__init__()

    def _remove_empty_problems(self, db):
        self.log_info("Removing empty problems")
        db_problems = get_problems(db)

        for db_problem in db_problems:
            if len(db_problem.reports) < 1:
                self.log_debug("Removing empty problem #{0}"
                               .format(db_problem.id))
                db.session.delete(db_problem)

        db.session.flush()

    def _create_problems(self, db, problemplugin):
        db_reports = get_reports_by_type(db, problemplugin.name)
        db_reports, distances = problemplugin.compare_many(db_reports)
        dendrogram = satyr.Dendrogram(distances)
        cut = dendrogram.cut(problemplugin.cutthreshold, 1)

        problems = []
        for problem in cut:
            problems.append(db_reports[p] for p in problem)

        self.log_info("Creating problems")
        for problem in problems:
            comps = {}

            db_problem = Problem()
            db.session.add(db_problem)

            for db_report in problem:
                db_report.problem = db_problem

                if (db_problem.last_occurrence is None or
                    db_problem.last_occurrence < db_report.last_occurrence):
                    db_problem.last_occurrence = db_report.last_occurrence

                if (db_problem.first_occurrence is None or
                    db_problem.first_occurrence < db_report.first_occurrence):
                    db_problem.first_occurrence = db_report.first_occurrence

                if db_report.component not in comps:
                    comps[db_report.component] = 0

                comps[db_report.component] += 1

            db_comps = sorted(comps, key=lambda x: comps[x], reverse=True)

            order = 0
            for db_component in db_comps:
                order += 1

                db_pcomp = ProblemComponent()
                db_pcomp.problem = db_problem
                db_pcomp.component = db_component
                db_pcomp.order = order
                db.session.add(db_pcomp)

        db.session.flush()

    def run(self, cmdline, db):
        if len(cmdline.problemtype) < 1:
            ptypes = problemtypes.keys()
        else:
            ptypes = cmdline.problemtype

        i = 0
        for ptype in ptypes:
            i += 1
            problemplugin = problemtypes[ptype]
            self.log_info("[{0} / {1}] Processing problem type: {2}"
                          .format(i, len(ptypes), problemplugin.nice_name))

            self._create_problems(db, problemplugin)

        self._remove_empty_problems(db)

    def tweak_cmdline_parser(self, parser):
        parser.add_problemtype(multiple=True)
