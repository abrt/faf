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

from . import Column
from . import GenericTable
from . import Integer
from . import String
from . import ForeignKey
from . import relationship


class Erratum(GenericTable):
    __tablename__ = "errata"

    id = Column(Integer, primary_key=True)
    advisory_name = Column(String(256), nullable=False)
    synopsis = Column(String(1024), nullable=False)


class ErratumBug(GenericTable):
    __tablename__ = "erratumbugs"

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, primary_key=True)
    erratum_id = Column(Integer, ForeignKey("{0}.id".format(Erratum.__tablename__)), nullable=False, index=True)

    erratum = relationship(Erratum, primaryjoin="ErratumBug.erratum_id == Erratum.id",
                       backref="bugs")
