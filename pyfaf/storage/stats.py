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

from . import Architecture
from . import Column
from . import Component
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import OpSysRelease
from . import Problem
from . import String
from . import relationship

class ProblemByArch(GenericTable):
    __tablename__ = "problembyarch"

    __columns__ = [ Column("problem_id", Integer, ForeignKey("{0}.id".format(Problem.__tablename__)), primary_key=True),
                    Column("arch", String(8), ForeignKey("{0}.arch".format(Architecture.__tablename__)), nullable=False),
                    Column("count", Integer, nullable=False) ]

    __relationships__ = { "problem": relationship(Problem) }

class ProblemByOpSysRelease(GenericTable):
    __tablename__ = "problembyopsys"

    __columns__ = [ Column("problem_id", Integer, ForeignKey("{0}.id".format(Problem.__tablename__)), primary_key=True),
                    Column("opsysrelease_id", Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), nullable=False),
                    Column("count", Integer, nullable=False) ]

    __relationships__ = { "opsysrelease": relationship(OpSysRelease) }

class ProblemByComponent(GenericTable):
    __tablename__ = "problembycomponent"

    __columns__ = [ Column("problem_id", Integer, ForeignKey("{0}.id".format(Problem.__tablename__)), primary_key=True),
                    Column("component_id", Integer, ForeignKey("{0}.id".format(Component.__tablename__)), nullable=False),
                    Column("count", Integer, nullable=False) ]

    __relationships__ = { "component": relationship(Component) }
