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

from . import Boolean
from . import Column
from . import DateTime
from . import Enum
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import OpSysComponent
from . import OpSysRelease
from . import String
from . import relationship

RHBZ_URL = "https://bugzilla.redhat.com/show_bug.cgi?id={0}"

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

class RhbzUser(GenericTable):
    __tablename__ = "rhbzusers"

    id = Column(Integer, primary_key=True)
    email = Column(String(64), nullable=False)
    name = Column(String(64), nullable=False)
    real_name = Column(String(64), nullable=False)
    can_login = Column(Boolean, nullable=False)

    def __str__(self):
        return self.email

class RhbzBug(GenericTable):
    __tablename__ = "rhbzbugs"
    __lobs__ = { "optimized-backtrace": 1 << 16 }

    id = Column(Integer, primary_key=True)
    summary = Column(String(256), nullable=False)
    status = Column(Enum(*BUG_STATES, name="rhbzbug_status"), nullable=False)
    resolution = Column(Enum(*BUG_RESOLUTIONS, name="rhbzbug_resolution"), nullable=True)
    duplicate = Column(Integer, ForeignKey("{0}.id".format(__tablename__)), nullable=True, index=True)
    creation_time = Column(DateTime, nullable=False)
    last_change_time = Column(DateTime, nullable=False)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("{0}.id".format(OpSysComponent.__tablename__)), nullable=False, index=True)
    whiteboard = Column(String(256), nullable=False)
    creator_id = Column(Integer, ForeignKey("{0}.id".format(RhbzUser.__tablename__)), nullable=False, index=True)

    opsysrelease = relationship(OpSysRelease)
    component = relationship(OpSysComponent)
    creator = relationship(RhbzUser)

    def __str__(self):
        return 'RHBZ#{0}'.format(self.id)

    def url(self):
        return RHBZ_URL.format(self.id)

    def order(self):
        return BUG_STATES.index(self.status)

class RhbzBugCc(GenericTable):
    __tablename__ = "rhbzbugccs"

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey("{0}.id".format(RhbzBug.__tablename__)), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("{0}.id".format(RhbzUser.__tablename__)), nullable=False, index=True)

    bug = relationship(RhbzBug, backref="ccs")
    user = relationship(RhbzUser)

    def __str__(self):
        return str(self.user)

class RhbzBugHistory(GenericTable):
    __tablename__ = "rhbzbughistory"

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey("{0}.id".format(RhbzBug.__tablename__)), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("{0}.id".format(RhbzUser.__tablename__)), nullable=False, index=True)
    time = Column(DateTime, nullable=False)
    field = Column(String(64), nullable=False)
    added = Column(String(256), nullable=False)
    removed = Column(String(256), nullable=False)

    bug = relationship(RhbzBug, backref="history")
    user = relationship(RhbzUser)

    def __str__(self):
        action = ''
        if self.removed:
            action += 'removed: {0} '.format(self.removed)

        if self.added:
            action += 'added: {0} '.format(self.added)

        return '{0} changed {1}, {2}'.format(self.user, self.field, action)

class RhbzAttachment(GenericTable):
    __tablename__ = "rhbzattachments"
    __lobs__ = { "content": 1 << 24 }

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey("{0}.id".format(RhbzBug.__tablename__)), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("{0}.id".format(RhbzUser.__tablename__)), nullable=False, index=True)
    mimetype = Column(String(256), nullable=False)
    description = Column(String(256), nullable=False)
    creation_time = Column(DateTime, nullable=False)
    last_change_time = Column(DateTime, nullable=False)
    is_private = Column(Boolean, nullable=False)
    is_patch = Column(Boolean, nullable=False)
    is_obsolete = Column(Boolean, nullable=False)
    filename = Column(String(256), nullable=False)

    bug = relationship(RhbzBug, backref="attachments")
    user = relationship(RhbzUser)

class RhbzComment(GenericTable):
    __tablename__ = "rhbzcomments"
    __lobs__ = { "content": 1 << 22 }

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey("{0}.id".format(RhbzBug.__tablename__)), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("{0}.id".format(RhbzUser.__tablename__)), nullable=False, index=True)
    number = Column(Integer, nullable=False)
    is_private = Column(Boolean, nullable=False)
    creation_time = Column(DateTime, nullable=False)
    duplicate_id = Column(Integer, ForeignKey("{0}.id".format(RhbzBug.__tablename__)), nullable=True, index=True)
    attachment_id = Column(Integer, ForeignKey("{0}.id".format(RhbzAttachment.__tablename__)), nullable=True, index=True)

    bug = relationship(RhbzBug, primaryjoin="RhbzComment.bug_id == RhbzBug.id",
                       backref="comments")
    user = relationship(RhbzUser)
    duplicate = relationship(RhbzBug, primaryjoin="RhbzComment.duplicate_id == RhbzBug.id")
    attachment = relationship(RhbzAttachment)

    def __str__(self):
        return '#{0} from {1}, added {2}'.format(
            self.number, self.user, self.creation_time)
