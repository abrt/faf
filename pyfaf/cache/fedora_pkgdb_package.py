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

class FedoraPkgDbPackage:
    AWAITING_REVIEW = "AWAITING_REVIEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    STATUS_ARRAY = [AWAITING_REVIEW,UNDER_REVIEW,APPROVED,DENIED]
    def __init__(self):
        self.id = None
        self.name = None
        self.review_url = None
        self.should_open = None
        self.summary = None
        self.upstream_url = None
        self.status = None
        self.description = None
        self.collections = []

class Collection:
    AWAITING_REVIEW = "AWAITING_REVIEW"
    AWAITING_BRANCH = "AWAITING_BRANCH"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    OBSOLETE = "OBSOLETE"
    ORPHANED = "ORPHANED"
    DEPRECATED = "DEPRECATED"
    REMOVED = "REMOVED" # Log
    STATUS_ARRAY = [AWAITING_REVIEW,AWAITING_BRANCH,APPROVED,DENIED,OBSOLETE,ORPHANED,DEPRECATED,REMOVED]
    def __init__(self):
        self.id = None
        self.owner = None
        self.status = None
        self.critical_path = None
        self.comaintainers = []

class Comaintainer:
    def __init__(self):
        # User name
        self.id = None
        self.acl = []

parser = toplevel("fedora_pkgdb_package",
                  FedoraPkgDbPackage,
                  [int_positive("id"),
                   string("name"),
                   string("review_url", null=True),
                   boolean("should_open"),
                   string("summary", null=True),
                   string("upstream_url", null=True),
                   string("status", constraint=lambda value,parent:value in FedoraPkgDbPackage.STATUS_ARRAY),
                   string_multiline("description", null=True),
                   array_dict("collections",
                              Collection,
                              [int_positive("id"),
                               string("owner"),
                               string("status", constraint=lambda value,parent:value in Collection.STATUS_ARRAY),
                               boolean("critical_path"),
                               array_dict("comaintainers",
                                          Comaintainer,
                                          [string("id"),
                                           array_inline_string("acl")])])])
