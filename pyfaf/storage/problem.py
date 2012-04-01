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
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import String
from . import Symbol
from . import relationship

class ProblemType(GenericTable):
    __tablename__ = "problemtypes"

    __columns__ = [ Column("id", String(16), primary_key=True),
                    Column("description", String(64), nullable=False) ]

class Problem(GenericTable):
    __tablename__ = "problems"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("type_id", String(16), ForeignKey("{0}.id".format(ProblemType.__tablename__)), nullable=False, index=True) ]

    __relationships__ = { "type": relationship(ProblemType) }

    __lobs__ = { "raw": 1 << 22 }

class Fingerprint(GenericTable):
    __tablename__ = "fingerprints"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("problem_id", Integer, ForeignKey("{0}.id".format(Problem.__tablename__)), nullable=False, index=True) ]

    __relationships__ = { "problem": relationship(Problem) }

class FpRecord(GenericTable):
    __tablename__ = "fprecords"

    __columns__ = [ Column("fingerprint_id", Integer, ForeignKey("{0}.id".format(Fingerprint.__tablename__)), primary_key=True),
                    Column("ord", Integer, nullable=False, primary_key=True),
                    Column("symbol_id", Integer, ForeignKey("{0}.id".format(Symbol.__tablename__)), nullable=False, index=True) ]

    __relationships__ = { "fingerprint": relationship(Fingerprint),
                          "symbol": relationship(Symbol) }
