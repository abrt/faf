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

class Relation:
    def __init__(self):
        # Id of the other bug.
        self.bug_id = None
        # Levenshtein distace between the two backtraces.
        self.levenshtein_distance = None
        # Jaccard distance of the two backtraces.
        self.jaccard_distance = None
        # Jaro-Winkler distance between the two backtraces.
        self.jaro_winkler_distance = None

class RhbzBugBtserverReport:
    def __init__(self):
        # Bug id, which is unique for single Bugzilla instance.
        self.id = None
        self.relations = []
        self.expected_backtrace_rating = None
        self.reported_backtrace_rating = None
        self.expected_crash_function = None
        self.reported_crash_function = None

parser = toplevel("rhbz_bug_btserver_report",
                  RhbzBugBtserverReport,
                  [int_positive("id", database_indexed=True),
                   array_dict("relations",
                              Relation,
                              [int_positive("bug_id", database_indexed=True),
                               int_unsigned("levenshtein_distance"),
                               double("jaccard_distance"),
                               double("jaro_winkler_distance")]),
                   int_unsigned("expected_backtrace_rating", null=True),
                   int_unsigned("reported_backtrace_rating", null=True),
                   string("expected_crash_function", null=True),
                   string("reported_crash_function", null=True)])
