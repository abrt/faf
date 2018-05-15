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
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import OpSys
from . import String
from . import UniqueConstraint
from . import relationship


class SfPrefilterSolution(GenericTable):
    __tablename__ = "sfprefiltersolutions"

    id = Column(Integer, primary_key=True)
    cause = Column(String(256), nullable=False, index=True)
    url = Column(String(4096))
    note_text = Column(String(8192), nullable=False)
    note_html = Column(String(16384))


class SfPrefilterBacktracePath(GenericTable):
    __tablename__ = "sfprefilterbacktracepaths"
    __table_args__ = (UniqueConstraint("pattern"),)

    id = Column(Integer, primary_key=True)
    pattern = Column(String(256), nullable=False, index=True)
    opsys_id = Column(Integer, ForeignKey("{0}.id".format(OpSys.__tablename__)), nullable=True, index=True)
    solution_id = Column(Integer, ForeignKey("{0}.id".format(SfPrefilterSolution.__tablename__)),
                         nullable=False, index=True)

    opsys = relationship(OpSys)
    solution = relationship(SfPrefilterSolution)


class SfPrefilterPackageName(GenericTable):
    __tablename__ = "sfprefilterpackagenames"
    __table_args__ = (UniqueConstraint("pattern"),)

    id = Column(Integer, primary_key=True)
    pattern = Column(String(256), nullable=False, index=True)
    opsys_id = Column(Integer, ForeignKey("{0}.id".format(OpSys.__tablename__)), nullable=True, index=True)
    solution_id = Column(Integer, ForeignKey("{0}.id".format(SfPrefilterSolution.__tablename__)),
                         nullable=False, index=True)

    opsys = relationship(OpSys)
    solution = relationship(SfPrefilterSolution)
