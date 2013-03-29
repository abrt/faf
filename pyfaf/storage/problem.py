# Copyright (C) 2012 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from . import Column
from . import DateTime
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import OpSysComponent
from . import relationship

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
    first_occurence = Column(DateTime)
    last_occurence = Column(DateTime)
    #pylint:disable=E1101
    # Class has no '__table__' member
    components = relationship(OpSysComponent,
        secondary=ProblemComponent.__table__, order_by=ProblemComponent.order)

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
    def sorted_reports(self):
        """
        Return list of all reports sorted by report count.
        """

        return sorted(self.reports, key=lambda report: report.count, reverse=True)
