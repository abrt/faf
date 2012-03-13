# Copyright (C) 2012 Red Hat, Inc.
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

ACTION_ARRAY = [ "CLOSE_DUPLICATE", "CHANGE_COMPONENT", "SUGGEST_DUPLICATE" ]
class RhbzAction:
    def __init__(self):
        self.id = None
        self.cluster_id = None
        self.bug_id = None
        self.bug_last_change_time = None
        self.action = None
        self.value = None

parser = toplevel("rhbz_action",
                  RhbzAction,
                  [int_positive("id", database_indexed=True),
                   int_positive("cluster_id"),
                   int_positive("bug_id"),
                   date_time("bug_last_change_time"),
                   string("action",
                       constraint=lambda value,parent:value in ACTION_ARRAY),
                   string("value")])
