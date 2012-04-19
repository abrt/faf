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
    component_id = Column(Integer, ForeignKey("{0}.id".format(OpSysComponent.__tablename__)), primary_key=True)
    order = Column(Integer, nullable=False)
    problem = relationship("Problem")
    component = relationship(OpSysComponent)

class Problem(GenericTable):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True)
    first_occurence = Column(DateTime)
    last_occurence = Column(DateTime)
    components = relationship(OpSysComponent, secondary=ProblemComponent.__table__, order_by=ProblemComponent.order)
