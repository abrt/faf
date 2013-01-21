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
from . import UniqueConstraint
from . import relationship

class Symbol(GenericTable):
    __tablename__ = "symbols"
    __table_args__ = ( UniqueConstraint('name', 'normalized_path'), )

    id = Column(Integer, primary_key=True)
    name = Column(String(1024), nullable=False)
    nice_name = Column(String(2048))
    normalized_path = Column(String(512), nullable=False)

class SymbolSource(GenericTable):
    __tablename__ = "symbolsources"
    __table_args__ = ( UniqueConstraint('build_id', 'path', 'offset'), )

    id = Column(Integer, primary_key=True)
    symbol_id = Column(Integer, ForeignKey("{0}.id".format(
        Symbol.__tablename__)), nullable=True, index=True)
    build_id = Column(String(64), nullable=True)
    path = Column(String(512), nullable=False)
    offset = Column(Integer, nullable=False)
    hash = Column(String(1024), nullable=True)
    source_path = Column(String(512), nullable=True)
    line_number = Column(Integer, nullable=True)
    presrcline = Column(String(1024), nullable=True)
    srcline = Column(String(1024), nullable=True)
    postsrcline = Column(String(1024), nullable=True)
    symbol = relationship(Symbol, backref="sources")
