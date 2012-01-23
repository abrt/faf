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
from .helpers import *

class RhbzAttachment:
    def __init__(self):
        # Attachment id number, which is unique for single Bugzilla
        # instance.
        self.id = None
        # Id number of the bug this attachment is associated to.
        self.bug_id = None
        # Id number of the author.
        self.user_id = None
        # Mime type of the attachment.
        self.mime_type = None
        # Textual description of the attachment provided by user.
        self.description = None
        # The time this attachment was created.
        self.creation_time = None
        # The time when the attachment was last changed.
        self.last_change_time = None
        # Indicates if the attachment is nonpublic.
        self.is_private = None
        # Indicates if the attachment is a patch.
        self.is_patch = None
        # Indicates if the attachment is obsolete.
        self.is_obsolete = None
        # Indicates if the attachment is an URL.
        self.is_url = None
        # Name of the file. Optional (see rhbz#688907).
        self.file_name = None
        # Of the bytearray type. Mandatory.
        self.contents = None

parser = toplevel("rhbz_attachment",
                  RhbzAttachment,
                  [int_positive("id", database_primary_key=True),
                   int_positive("bug_id"),
                   int_positive("user_id"),
                   string("mime_type"),
                   string_multiline("description"),
                   date_time("creation_time"),
                   date_time("last_change_time"),
                   boolean("is_private"),
                   boolean("is_patch"),
                   boolean("is_obsolete"),
                   boolean("is_url"),
                   string("file_name", null=True),
                   bytearray_quoted_printable("contents")])
