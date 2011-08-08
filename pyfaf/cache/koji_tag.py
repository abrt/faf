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

class KojiTag:
    def __init__(self):
        self.id = None
        self.name = None
        self.architectures = None
        self.perm_id = None
        self.locked = None
        self.inheritance = []

class Inheritance:
    def __init__(self):
        self.parent_id = None
        self.intranisitive = None
        self.priority = None
        self.config = None

parser = toplevel("koji_tag",
                  KojiTag,
                  [int_positive("id"),
                   string("name"),
                   string("architectures", null=True),
                   int_positive("perm_id", null=True),
                   boolean("locked"),
                   array_dict("inheritance",
                              Inheritance,
                              [int_positive("parent_id"),
                               boolean("intransitive"),
                               int_unsigned("priority"),
                               boolean("config")])])
