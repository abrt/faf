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

INSTALL_RPM_DEPENDENCIES_FAILED = "INSTALL-RPM-DEPENDENCIES-FAILED"
PREPARE_BUILD_ENVIRONMENT_FAILED = "PREPARE-BUILD-ENVIRONMENT-FAILED"
BUILD_SRPM_FAILED = "BUILD-SRPM-FAILED"
DEBUGSOURCES_NOT_FOUND = "DEBUGSOURCES-NOT-FOUND"
CLEAN_FAILED = "CLEAN-FAILED"
SUCCESS = "SUCCESS"

STATUSES = [ INSTALL_RPM_DEPENDENCIES_FAILED,
             PREPARE_BUILD_ENVIRONMENT_FAILED,
             BUILD_SRPM_FAILED,
             DEBUGSOURCES_NOT_FOUND,
             CLEAN_FAILED,
             SUCCESS ]

class DebuginfoSources:
    def __init__(self):
        # Id of the build
        self.id = None
        self.build_status = None
        self.sources = []

parser = toplevel("debuginfo_sources",
                  DebuginfoSources,
                  [int_positive("id"),
                   string("build_status", constraint=lambda value,parent:value in STATUSES),
                   array_string("sources")])
