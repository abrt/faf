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
from . import helpers

"""
Comment types
They correspond to Bugzilla internal constants CMT_* from Constants.pm
"""
NORMAL = "NORMAL"
DUPE_OF = "DUPLICATE_OF"
HAS_DUPE = "HAS_DUPLICATE"
POPULAR_VOTES = "POPULAR_VOTES"
MOVED_TO = "MOVED_TO"
ATTACHMENT_CREATED = "NEW_ATTACHMENT"
ATTACHMENT_UPDATED = "COMMENT_ON_ATTACHMENT"

"""
Index to this field correspond to the number returned by Bugzilla
XML-RPC getBug call ["longdescs"][comment_offset]["type"] (rhbz specific).
"""
TYPE_ARRAY = [NORMAL,
              DUPE_OF,
              HAS_DUPE,
              POPULAR_VOTES,
              MOVED_TO,
              ATTACHMENT_CREATED,
              ATTACHMENT_UPDATED]

class RhbzComment:
    """A bug comment."""
    def __init__(self):
        # Comment id, which is unique for single Bugzilla instance.
        self.id = None
        # The bug number this comment is associated to.
        self.bug_id = None
        # Bugzilla user id of the comment author.
        self.author_id = None
        # The comment number in the particular bug, starting from
        # zero.
        self.number = None
        # Indicates if the comment is private.
        self.is_private = None
        # The text of the comment. Optional (see rhbz#528272).
        self.body = None
        # The time this comment was added to the bug.
        self.time = None
        # The type of the comment, one of TYPE_ARRAY.
        self.type = None
        # When the comment type is `DUPE_OF` or `HAS_DUPE`,
        # this field contains the associated bug id.
        self.duplicate_id = None
        # When the comment type is `ATTACHMENT_CREATED` or
        # `ATTACHMENT_UPDATED`, this field contains the attachment
        # id.
        self.attachment_id = None

parser = helpers.toplevel("rhbz_comment",
                          RhbzComment,
                          [helpers.int_positive("id", database_indexed=True, database_primary_key=True),
                           helpers.int_positive("bug_id"),
                           helpers.int_positive("author_id"),
                           helpers.int_unsigned("number"),
                           helpers.boolean("is_private"),
                           helpers.string_multiline("body", null=True),
                           helpers.date_time("time"),
                           helpers.string("type", constraint=lambda value,parent:value in TYPE_ARRAY),
                           helpers.int_positive("duplicate_id", null=lambda parent: not parent.type in [DUPE_OF, HAS_DUPE]),
                           helpers.int_positive("attachment_id", null=lambda parent: not parent.type in [ATTACHMENT_CREATED, ATTACHMENT_UPDATED])])
