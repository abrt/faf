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
from . import String
from . import relationship

class Project(GenericTable):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True, index=True)

class ProjRelease(GenericTable):
    __tablename__ = "projectreleases"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("{0}.id".format(Project.__tablename__)), nullable=False, index=True)
    # may be git hash
    version = Column(String(64), nullable=False)
    pubdate = Column(DateTime, nullable=False)
    project = relationship(Project, backref="releases")
