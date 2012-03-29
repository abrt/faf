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
from . import relationship

class Symbol(GenericTable):
    __tablename__ = "symbols"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("name", String(64), nullable=True),
                    Column("executable", String(256), nullable=False),
                    Column("buildid", String(64), nullable=False) ]

class SymbolHash(GenericTable):
    __tablename__ = "symbolhashes"

    __columns__ = [ Column("hash", String(64), primary_key=True),
                    Column("symbol_id", Integer, ForeignKey("{0}.id".format(Symbol.__tablename__)), nullable=False, index=True),
                    Column("offset", Integer, nullable=False) ]
