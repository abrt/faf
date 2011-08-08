# Copyright (C) 2011 Red Hat, Inc.
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
from helpers import *

# Bug status
BS_CLOSED = "CLOSED"
BS_ASSIGNED = "ASSIGNED"
BS_NEW = "NEW"
BS_MODIFIED = "MODIFIED"
BS_VERIFIED = "VERIFIED"
BS_ON_QA = "ON_QA"
BS_ON_DEV = "ON_DEV"
BS_RELEASE_PENDING = "RELEASE_PENDING"
BS_POST = "POST"

STATUS_ARRAY = [ BS_CLOSED,
                 BS_ASSIGNED,
                 BS_NEW,
                 BS_MODIFIED,
                 BS_VERIFIED,
                 BS_ON_QA,
                 BS_ON_DEV,
                 BS_RELEASE_PENDING,
                 BS_POST ]

"""Resolution of closed bug"""
BR_NOTABUG = "NOTABUG"
BR_WONTFIX = "WONTFIX"
BR_WORKSFORME = "WORKSFORME"
BR_DEFERRED = "DEFERRED"
BR_CURRENTRELEASE = "CURRENTRELEASE"
BR_RAWHIDE = "RAWHIDE"
BR_ERRATA = "ERRATA"
BR_DUPLICATE = "DUPLICATE"
BR_UPSTREAM = "UPSTREAM"
BR_NEXTRELEASE = "NEXTRELEASE"
BR_CANTFIX = "CANTFIX"
BR_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

RESOLUTION_ARRAY = [ BR_NOTABUG,
                     BR_WONTFIX,
                     BR_WORKSFORME,
                     BR_DEFERRED,
                     BR_CURRENTRELEASE,
                     BR_RAWHIDE,
                     BR_ERRATA,
                     BR_DUPLICATE,
                     BR_UPSTREAM,
                     BR_NEXTRELEASE,
                     BR_CANTFIX,
                     BR_INSUFFICIENT_DATA ]

class RhbzBug:
    """A bug stored in local cache."""
    def __init__(self):
        # Bug id, which is unique for single Bugzilla instance.
        self.id = None
        # One line bug summary.
        self.summary = None
        # The bug status.  It's value must be from STATUS_ARRAY.
        self.status = None
        # Resolution of the bug, needed if `self.status` is
        # `BS_CLOSED`.
        self.resolution = None
        # If the resolution of a closed bug is `BR_DUPLICATE`, it
        # contains the duplicate bug id.
        self.resolution_dup_id = None
        # The time this bug was created.
        self.creation_time = None
        # The time this bug was last changed.
        self.last_change_time = None
        # Name of the product this bug is associated to.
        self.product = None
        # Version of the product this bug is associated to.
        self.product_version = None
        # Name of the product component this bug is associated to.
        self.component = None
        # Contents of the bug's whiteboard.
        self.whiteboard = None
        # Id of user which created this bug.
        self.creator_id = None
        # Array of bug comment ids.
        self.comments = []
        # Array of attachment ids.
        self.attachments = []
        # Array of user ids.
        self.cc = []
        # History of the bug.
        self.history = []

class History:
    def __init__(self):
        # Who did the change
        self.user_id = None
        # When it happened
        self.time = None
        # Field (in our text format); supported fields: cc
        self.field = None
        # What has been added to the field; if the field is cc, this
        # field contains a user email
        self.added = None
        # What has been removed from the field; if the field is cc,
        # this field contains a user email
        self.removed = None

parser = toplevel("rhbz_bug",
                  RhbzBug,
                  [int_positive("id", database_indexed=True),
                   string("summary"),
                   string("status",
                          constraint=lambda value,parent:value in STATUS_ARRAY),
                   string("resolution",
                          null=lambda parent:parent.status != BS_CLOSED,
                          constraint=lambda value,parent:parent.status == BS_CLOSED),
                   int_positive("resolution_dup_id",
                                null=lambda parent:parent.status != BS_CLOSED or \
                                    parent.resolution != BR_DUPLICATE),
                   date_time("creation_time"),
                   date_time("last_change_time"),
                   string("product"),
                   string("product_version"),
                   string("component", database_indexed=True),
                   string("whiteboard", null=True),
                   int_positive("creator_id"),
                   array_inline_int("comments"),
                   array_inline_int("attachments"),
                   array_inline_int("cc"),
                   array_dict("history",
                              History,
                              [int_positive("user_id"),
                               date_time("time"),
                               string("field"),
                               string("added",
                                      null=lambda parent:isinstance(parent.removed, basestring) and \
                                          len(parent.removed) > 0),
                               string("removed",
                                      null=lambda parent:isinstance(parent.added, basestring) and \
                                          len(parent.added) > 0)])])
