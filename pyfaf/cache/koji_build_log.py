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

class KojiBuildLog:
    def __init__(self):
        self.id = None
        self.architecture_log_sets = []

class ArchitectureLogSet:
    def __init__(self):
        # Matches build's RPMs architectures.
        self.architecture = None
        # Build.log file
        self.build = None
        # Root.log file
        self.root = None
        # State.log file
        self.state = None

parser = toplevel("koji_build_log",
                  KojiBuildLog,
                  [int_positive("id"),
                   array_dict("architecture_log_sets",
                              ArchitectureLogSet,
                              [string("architecture"),
                               bytearray_quoted_printable("build"),
                               bytearray_quoted_printable("root"),
                               bytearray_quoted_printable("state", null=True)])])
