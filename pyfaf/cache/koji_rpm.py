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

class Dependency:
    # Flags from RPM, not exported to Python
    RPMSENSE_ANY = 0
    RPMSENSE_LESS = (1 << 1)
    RPMSENSE_GREATER = (1 << 2)
    RPMSENSE_EQUAL = (1 << 3)
    RPMSENSE_PROVIDES = (1 << 4)
    RPMSENSE_CONFLICTS = (1 << 5)
    RPMSENSE_OBSOLETES = (1 << 7)
    RPMSENSE_INTERP = (1 << 8)
    RPMSENSE_SCRIPT_PRE = ((1 << 9)| RPMSENSE_ANY)
    RPMSENSE_SCRIPT_POST = ((1 << 10)| RPMSENSE_ANY)
    RPMSENSE_SCRIPT_PREUN = ((1 << 11)| RPMSENSE_ANY)
    RPMSENSE_SCRIPT_POSTUN = ((1 << 12)| RPMSENSE_ANY)
    RPMSENSE_SCRIPT_VERIFY = (1 << 13)
    RPMSENSE_FIND_REQUIRES = (1 << 14)
    RPMSENSE_FIND_PROVIDES = (1 << 15)
    RPMSENSE_TRIGGERIN = (1 << 16)
    RPMSENSE_TRIGGERUN = (1 << 17)
    RPMSENSE_TRIGGERPOSTUN = (1 << 18)
    RPMSENSE_MISSINGOK = (1 << 19)
    RPMSENSE_SCRIPT_PREP = (1 << 20)
    RPMSENSE_SCRIPT_BUILD = (1 << 21)
    RPMSENSE_SCRIPT_INSTALL = (1 << 22)
    RPMSENSE_SCRIPT_CLEAN = (1 << 23)
    RPMSENSE_RPMLIB = ((1 << 24) | RPMSENSE_ANY)
    RPMSENSE_TRIGGERPREIN = (1 << 25)
    RPMSENSE_KEYRING = (1 << 26)
    RPMSENSE_PATCHES = (1 << 27)
    RPMSENSE_CONFIG = (1 << 28)

    def __init__(self):
        self.name = None
        # RPMSENSE_*
        self.flags = None
        self.epoch = None
        self.version = None
        self.release = None

class KojiRPM:
    def __init__(self):
        self.id = None
        self.build_id = None
        self.name = None
        self.version = None
        self.release = None
        self.epoch = None
        self.architecture = None
        self.size = None
        self.files = []
        self.provides = []
        self.requires = []
        self.obsoletes = []
        self.conflicts = []

    def nvra(self):
        return "{0}-{1}-{2}.{3}".format(self.name, self.version, self.release, self.architecture)

    def envra(self):
        return "{0}:{1}-{2}-{3}.{4}".format(self.epoch, self.name, self.version, self.release, self.architecture)

    def evr(self):
        return "{0}:{1}-{2}".format(self.epoch, self.version, self.release)

    def filename(self):
        return "{0}.rpm".format(self.nvra())

    def is_debuginfo(self):
        return "-debuginfo" in self.name

    def provides(self, dependency):
        for provide in self._provides:
            if provide.name == dependency.name:
                return True
        for file in self.files:
            if file == dependency.name:
                return True
        return False

dependency_parser = [string("name", database_indexed=True),
                     int_unsigned("flags"),
                     int_unsigned("epoch", null=True),
                     string("version", null=True),
                     string("release", null=True)]

parser = toplevel("koji_rpm",
                  KojiRPM,
                  [int_positive("id", database_indexed=True),
                   int_positive("build_id", database_indexed=True),
                   string("name"),
                   string("version"),
                   string("release"),
                   int_unsigned("epoch"),
                   string("architecture"),
                   int_positive("size"),
                   array_string("files", database_indexed=True),
                   array_dict("provides", Dependency, dependency_parser, database_indexed=True, text_name="provides"),
                   array_dict("requires", Dependency, dependency_parser, database_indexed=True),
                   array_dict("obsoletes", Dependency, dependency_parser, database_indexed=True),
                   array_dict("conflicts", Dependency, dependency_parser, database_indexed=True)])
