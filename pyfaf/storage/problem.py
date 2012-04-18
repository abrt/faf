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

    __columns__ = [ Column("problem_id", Integer, ForeignKey("problems.id"), primary_key=True),
                    Column("component_id", Integer, ForeignKey("{0}.id".format(OpSysComponent.__tablename__)), primary_key=True),
                    Column("order", Integer, nullable=False) ]

    __relationships__ = { "problem": "relationship(Problem)",
                          "component": relationship(OpSysComponent) }

class Problem(GenericTable):
    __tablename__ = "problems"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("first_occurence", DateTime),
                    Column("last_occurence", DateTime) ]

    __relationships__ = { "components": "relationship(OpSysComponent, secondary=ProblemComponent.table, \
                                         order_by=ProblemComponent.order)" }
