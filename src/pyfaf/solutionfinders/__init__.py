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

import os
import cgi
import datetime
#from collections import namedtuple
from pyfaf.common import FafError, Plugin, import_dir, load_plugins
from pyfaf.storage import Report, getDatabase
from pyfaf.ureport import ureport2
from pyfaf.problemtypes import problemtypes
from pyfaf.queries import get_report_by_hash

solution_finders = {}

#Solution = namedtuple("Solution", ["cause", "url", "note_text", "note_html"])

class Solution(object):
    def __init__(self, cause, url, note_text, note_html=None, since=None):
        self.cause = cause
        self.url = url
        self.note_text = note_text
        if note_html is None:
            try:
                self.note_html = cgi.escape(note_text).replace("\n", "<br/>")
            except:
                note_html = ""
        if since is None:
            since = datetime.datetime.now()


class SolutionFinder(Plugin):
    name = "abstract_solution_finder"

    def __init__(self, *args, **kwargs):
        """
        The superclass constructor does not really need to be called, but it
        enables a few useful features (like unified logging). If not called
        by the child, it just makes sure that SolutionFinder class is not
        instantiated directly.
        """

        if self.__class__.__name__ == "SolutionFinder":
            raise FafError("You need to subclass the SolutionFinder class "
                           "in order to implement a solution finder plugin.")

        super(SolutionFinder, self).__init__()

        # Lower number means higher priority
        self.load_config_to_self("solution_priority", "{0}.solution_priority"
                                 .format(self.name), 100, callback=int)

    def _get_db_report(self, db, ureport):
        ureport = ureport2(ureport)

        problemplugin = problemtypes[ureport["problem"]["type"]]
        report_hash = problemplugin.hash_ureport(ureport["problem"])

        report = get_report_by_hash(db, report_hash)
        if report is None:
            return None
        return report

    def find_solution_ureport(self, db, ureport, osr=None):
        return self.find_solution_db_report(db, self._get_db_report(db, ureport), osr)

    def find_solution_db_report(self, db, db_report, osr=None):
        return None

    def find_solutions_problem(self, db, problem, osr=None):
        solutions = []
        for report in problem.reports:
            solution = self.find_solution_db_report(db, report, osr)
            if solution is not None and solution not in solutions:
                solutions.append(solution)
        return solutions

import_dir(__name__, os.path.dirname(__file__))
load_plugins(SolutionFinder, solution_finders)


def find_solution(report, db=None, finders=None, osr=None):
    """
    Check whether a Solution exists for a report (pyfaf.storage.Report or
    uReport dict). Return pyfaf.storage.SfPrefilterSolution object for the
    solution with the highest priority (i.e. lowest number) or None.
    """

    if db is None:
        db = getDatabase()

    if finders is None:
        finders = solution_finders.keys()

    solutions = []
    if isinstance(report, Report):
        for finder_name in finders:
            solution_finder = solution_finders[finder_name]
            solution = solution_finder.find_solution_db_report(db, report, osr)
            if solution is not None:
                solutions.append((solution_finder.solution_priority, solution))

    elif isinstance(report, dict):
        for finder_name in finders:
            solution_finder = solution_finders[finder_name]
            solution = solution_finder.find_solution_ureport(db, report, osr)
            if solution is not None:
                solutions.append((solution_finder.solution_priority, solution))

    else:
        raise ValueError("`report` must be an instance of either "
                         "pyfaf.storage.Report or dict")

    if len(solutions) > 0:
        return sorted(solutions, key=lambda solution: solution[0])[0][1]
    else:
        return None


def find_solutions_problem(problem, db=None, finders=None, osr=None):
    """
    Return a list of Solution objects for a given `problem` sorted from highest
    to lowest priority.
    Use `finders` to optionally list `SolutionFinder` objects to be used.
    Otherwise all solution finders are used.
    Use `osr` to optionally list `OpSysRelease` objects to find the solutions for.
    """

    if db is None:
        db = getDatabase()

    if finders is None:
        finders = solution_finders.keys()

    solutions = []
    for finder_name in finders:
        solution_finder = solution_finders[finder_name]
        sf_solutions = solution_finder.find_solutions_problem(db, problem, osr)
        if sf_solutions:
            solutions += [(solution_finder.solution_priority, solution)
                          for solution in sf_solutions]

    return [solution[1] for solution in
            sorted(solutions, key=lambda solution: solution[0])]
