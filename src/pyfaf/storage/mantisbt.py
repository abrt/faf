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

from . import Boolean
from . import Column
from . import DateTime
from . import Enum
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import Bugtracker
from . import OpSysComponent
from . import OpSysRelease
from . import String
from . import relationship
from . import UniqueConstraint

__all__ = ["MantisBug"]

# Severity ordered list of bug states
BUG_STATES = [
    "NEW", "ASSIGNED", "MODIFIED", "ON_QA",
    "VERIFIED", "RELEASE_PENDING", "ON_DEV", "POST",
    "CLOSED",
]

BUG_RESOLUTIONS = [
    "NOTABUG", "WONTFIX", "WORKSFORME",
    "DEFERRED", "CURRENTRELEASE", "RAWHIDE",
    "ERRATA", "DUPLICATE", "UPSTREAM", "NEXTRELEASE",
    "CANTFIX", "INSUFFICIENT_DATA",
]


class MantisBug(GenericTable):
    __tablename__ = "mantisbugs"
    __table_args__ = (UniqueConstraint("external_id", "tracker_id"),)

    # Object ID
    id = Column(Integer, primary_key=True)
    summary = Column(String(256), nullable=False)
    status = Column(Enum(*BUG_STATES, name="mantisbug_status"), nullable=False)
    resolution = Column(Enum(*BUG_RESOLUTIONS, name="mantisbug_resolution"), nullable=True)
    duplicate_id = Column(Integer, ForeignKey("{0}.id".format(__tablename__)), nullable=True, index=True)
    creation_time = Column(DateTime, nullable=False)
    last_change_time = Column(DateTime, nullable=False)
    # ID in the external bug tracker
    external_id = Column(Integer, nullable=False, index=True)
    # ID of the bug tracker
    tracker_id = Column(Integer, ForeignKey("{0}.id".format(Bugtracker.__tablename__)), nullable=False)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("{0}.id".format(OpSysComponent.__tablename__)), nullable=False, index=True)

    tracker = relationship(Bugtracker, backref="mantis_bugs")
    opsysrelease = relationship(OpSysRelease)
    component = relationship(OpSysComponent)

    def __str__(self):
        return '{0}#{1}'.format(self.tracker.abbr, self.external_id)

    def order(self):
        return BUG_STATES.index(self.status)

    @property
    def url(self):
        return "{0}{1}".format(self.tracker.web_url, self.external_id)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'summary': self.summary,
            'status': self.status,
            'resolution': self.resolution,
            'duplicate_id': self.duplicate_id,
            'creation_time': self.creation_time,
            'last_change_time': self.last_change_time,
            'external_id': self.external_id,
            'tracker_id': self.tracker_id,
            'opsysrelease_id': self.opsysrelease_id,
            'component_id': self.component_id,
            'type': 'MANTIS'
        }
