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

class KojiBuild:
    def __init__(self):
        self.id = None
        self.name = None
        self.version = None
        self.release = None
        self.epoch = None
        self.task_id = None
        self.creation_time = None
        self.completion_time = None
        self.tags = []
        self.rpms = []
        self.logs = []

    def nv(self):
        """Returns build name and version in a single string."""
        return "{0}-{1}".format(self.name, self.version)

    def nvr(self):
        """Returns build name, version and release in a single
        string."""
        return "{0}-{1}-{2}".format(self.name,
                                    self.version,
                                    self.release)

    def nevr(self):
        """Returns build name, epoch, version and release in a single
        string."""
        return "{0}-{1}:{2}-{3}".format(self.name,
                                        self.epoch,
                                        self.version,
                                        self.release)

class LogSet:
    """Koji logs (buil log, root log, state log) for a build on single
    architecture."""
    def __init__(self):
        self.architecture = None
        self.build_id = None
        self.root_id = None
        self.state_id = None

parser = toplevel("koji_build",
                  KojiBuild,
                  [int_positive("id", database_primary_key=True),
                   string("name", database_indexed=True),
                   string("version"),
                   string("release"),
                   int_unsigned("epoch"),
                   int_positive("task_id"),
                   date_time("creation_time"),
                   date_time("completion_time"),
                   array_inline_string("tags"),
                   array_inline_int("rpms", text_name="RPMs"),
                   array_dict("logs",
                              LogSet,
                              [string("architecture"),
                               string("build_id"),
                               string("root_id"),
                               string("state_id", null=True)])])
