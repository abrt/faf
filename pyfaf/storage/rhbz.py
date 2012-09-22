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

class RhbzUser(GenericTable):
    __tablename__ = "rhbzusers"

    id = Column(Integer, primary_key=True)
    email = Column(String(64), nullable=False)
    name = Column(String(64), nullable=False)
    real_name = Column(String(64), nullable=False)
    can_login = Column(Boolean, nullable=False)

class RhbzBug(GenericTable):
    __tablename__ = "rhbzbugs"
    __lobs__ = { "optimized-backtrace": 1 << 16 }

    id = Column(Integer, primary_key=True)
    summary = Column(String(256), nullable=False)
    status = Column(Enum("CLOSED", "ASSIGNED", "NEW", "MODIFIED", "VERIFIED", "ON_QA", "ON_DEV", "RELEASE_PENDING", "POST", name="rhbzbug_status"), nullable=False)
    resolution = Column(Enum("NOTABUG", "WONTFIX", "WORKSFORME", "DEFERRED", "CURRENTRELEASE", "RAWHIDE", "ERRATA", "DUPLICATE", "UPSTREAM", "NEXTRELEASE", "CANTFIX", "INSUFFICIENT_DATA", name="rhbzbug_resolution"), nullable=True)
    duplicate = Column(Integer, ForeignKey("{0}.id".format(__tablename__)), nullable=True, index=True)
    creation_time = Column(DateTime, nullable=False)
    last_change_time = Column(DateTime, nullable=False)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("{0}.id".format(OpSysComponent.__tablename__)), nullable=False, index=True)
    whiteboard = Column(String(256), nullable=False)
    creator_id = Column(Integer, ForeignKey("{0}.id".format(RhbzUser.__tablename__)), nullable=False, index=True)

    opsysrelease = relationship(OpSysRelease)
    component = relationship(OpSysComponent)

    def __str__(self):
        return 'RHBZ#{0}'.format(self.id)

    def url(self):
        return RHBZ_URL.format(self.id)

class RhbzBugCc(GenericTable):
    __tablename__ = "rhbzbugccs"

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey("{0}.id".format(RhbzBug.__tablename__)), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("{0}.id".format(RhbzUser.__tablename__)), nullable=False, index=True)

    bug = relationship(RhbzBug)
    user = relationship(RhbzUser)

class RhbzBugHistory(GenericTable):
    __tablename__ = "rhbzbughistory"

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey("{0}.id".format(RhbzBug.__tablename__)), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("{0}.id".format(RhbzUser.__tablename__)), nullable=False, index=True)
    time = Column(DateTime, nullable=False)
    field = Column(String(16), nullable=False)
    added = Column(String(256), nullable=False)
    removed = Column(String(256), nullable=False)

    bug = relationship(RhbzBug)
    user = relationship(RhbzUser)

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

    bug = relationship(RhbzBug)
    user = relationship(RhbzUser)

class RhbzComment(GenericTable):
    __tablename__ = "rhbzcomments"
    __lobs__ = { "content": 1 << 20 }

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey("{0}.id".format(RhbzBug.__tablename__)), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("{0}.id".format(RhbzUser.__tablename__)), nullable=False, index=True)
    number = Column(Integer, nullable=False)
    is_private = Column(Boolean, nullable=False)
    creation_time = Column(DateTime, nullable=False)
    comment_type = Column(Enum("NORMAL", "DUPLICATE_OF", "HAS_DUPLICATE", "POPULAR_VOTES", "MOVED_TO", "NEW_ATTACHMENT", "COMMENT_ON_ATTACHMENT", name="rhbzcomment_type"), nullable=False)
    duplicate_id = Column(Integer, ForeignKey("{0}.id".format(RhbzBug.__tablename__)), nullable=True, index=True)
    attachment_id = Column(Integer, ForeignKey("{0}.id".format(RhbzAttachment.__tablename__)), nullable=True, index=True)

    bug = relationship(RhbzBug, primaryjoin="RhbzComment.bug_id == RhbzBug.id")
    user = relationship(RhbzUser)
    duplicate = relationship(RhbzBug, primaryjoin="RhbzComment.duplicate_id == RhbzBug.id")
    attachment = relationship(RhbzAttachment)
