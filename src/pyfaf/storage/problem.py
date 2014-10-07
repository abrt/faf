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

from . import Column
from . import DateTime
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import String
from . import OpSysComponent, OpSysRelease
from . import relationship, backref


class ProblemComponent(GenericTable):
    __tablename__ = "problemscomponents"

    problem_id = Column(Integer, ForeignKey("problems.id"), primary_key=True)
    component_id = Column(Integer, ForeignKey("{0}.id".format(
        OpSysComponent.__tablename__)), primary_key=True)
    order = Column(Integer, nullable=False)
    problem = relationship("Problem")
    component = relationship(OpSysComponent)


class Problem(GenericTable):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True)
    first_occurrence = Column(DateTime)
    last_occurrence = Column(DateTime)
    #pylint:disable=E1101
    # Class has no '__table__' member
    components = relationship(OpSysComponent,
                              secondary=ProblemComponent.__table__,
                              order_by=ProblemComponent.order)

    @property
    def unique_component_names(self):
        return set(c.name for c in self.components)

    @property
    def bugs(self):
        my_bugs = set()

        for report in self.reports:
            for bug in report.bugs:
                my_bugs.add(bug)

        return my_bugs

    @property
    def status(self):
        bugs = self.bugs

        if not bugs:
            return 'NEW'

        return sorted(bugs, key=lambda x: x.order())[0].status

    @property
    def crash_function(self):
        report = self.reports[0]
        return report.backtraces[0].crash_function

    @property
    def type(self):
        report = self.reports[0]
        return report.type

    @property
    def reports_count(self):
        return sum(map(lambda x: x.count, self.reports))

    @property
    def quality(self):
        '''
        Return quality metric for this problem
        which equals to the quality of its best report.
        '''
        reps = self.sorted_reports
        if not reps:
            return -10000

        return self.sorted_reports[0].quality

    @property
    def sorted_reports(self):
        '''
        List of all reports assigned to this problem
        sorted by quality.
        '''
        return sorted(self.reports, key=lambda r: r.quality, reverse=True)

    @property
    def backtraces(self):
        '''
        List of all backtraces assigned to this problem.
        '''
        return sum(map(lambda x: x.backtraces, self.reports), [])

    @property
    def sorted_backtraces(self):
        '''
        List of all backtraces assigned to this problem
        sorted by quality.
        '''
        return sorted(self.backtraces, key=lambda bt: bt.quality, reverse=True)

    @property
    def comments(self):
        """
        List of all comments assigned to this problem.

        As the webui only shows first N comments, sort the result
        so that comments from all reports are included.

        With 3 reports having 3, 1 and 2 comments, the result would be
        [reports[0].comment[0],
         reports[1].comment[0],
         reports[2].comment[0],
         reports[0].comment[1],
         reports[2].comment[1],
         reports[0].comment[2]]
        """

        result = []
        longest = max(len(r.comments) for r in self.reports)
        i = 0
        while i < longest:
            i += 1
            for report in self.reports:
                if len(report.comments) >= i:
                    result.append(report.comments[i - 1])

        return result

    @property
    def probable_fixes(self):
        return ["{0}: {1}".format(osr.opsysrelease, osr.probable_fix)
                for osr in self.opsysreleases if osr.probable_fix]

    @property
    def probable_fixes_with_dates(self):
        return ["{0}: {1}, {2}".format(
            osr.opsysrelease, osr.probable_fix,
            osr.probably_fixed_since.strftime("%Y-%m-%d"))
            for osr in self.opsysreleases if osr.probable_fix]

    def probable_fix_for_opsysrelease_ids(self, osr_ids):
        if len(osr_ids) == 1:
            for osr in self.opsysreleases:
                if osr.opsysrelease_id in osr_ids:
                    return osr.probable_fix or ""
        else:
            return ", ".join(
                ["{0}: {1}".format(osr.opsysrelease, osr.probable_fix)
                 for osr in self.opsysreleases
                 if osr.probable_fix and osr.opsysrelease_id in osr_ids])
        return ""

    def probable_fix_for_opsysrelease_ids(self, osr_ids):
        if len(osr_ids) == 1:
            for posr in self.opsysreleases:
                if posr.opsysrelease_id in osr_ids:
                    return posr.probable_fix or ""
        else:
            return ", ".join(["{0}: {1}".format(osr.opsysrelease, osr.probable_fix)
                              for osr in self.opsysreleases
                              if osr.probable_fix and osr.opsysrelease_id in osr_ids])
        return ""


class ProblemOpSysRelease(GenericTable):
    __tablename__ = "problemopsysreleases"

    problem_id = Column(Integer, ForeignKey("{0}.id".format(Problem.__tablename__)), primary_key=True)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), primary_key=True)
    problem = relationship(Problem, backref=backref("opsysreleases", cascade="all, delete-orphan"))
    opsysrelease = relationship(OpSysRelease)
    probable_fix = Column(String(256), nullable=True)
    probably_fixed_since = Column(DateTime, nullable=True)

    def __str__(self):
        return "Problem #{0} of {1}".format(self.problem_id,
                                            str(self.opsysrelease))
