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

UNDER_DEVELOPMENT = "UNDER_DEVELOPMENT"
ACTIVE = "ACTIVE"
MAINTENANCE = "MAINTENANCE"
EOL = "EOL"
REJECTED = "REJECTED"

STATUS_ARRAY = [UNDER_DEVELOPMENT, ACTIVE, MAINTENANCE, EOL, REJECTED]

class FedoraPkgDbCollection:
    def __init__(self):
        self.id = None
        self.koji_name = None
        self.branch_name = None
        self.git_branch_name = None
        self.dist_tag = None
        self.owner = None
        self.name = None
        self.version = None
        self.status = None
        self.kind = None

parser = toplevel("fedora_pkgdb_collection",
                  FedoraPkgDbCollection,
                  [int_positive("id"),
                   string("koji_name", null=True),
                   string("branch_name"),
                   string("git_branch_name", null=True),
                   string("dist_tag"),
                   string("owner"),
                   string("name"),
                   string("version"),
                   string("status", constraint=lambda value,parent:value in STATUS_ARRAY),
                   string("kind")])
