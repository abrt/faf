# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
#
# This file is part of faf.
#
# faf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# faf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with faf.  If not, see <http://www.gnu.org/licenses/>.

from pyfaf.actions import Action
from pyfaf.problemtypes import problemtypes
from pyfaf.queries import get_backtraces_by_type
from pyfaf.retrace import demangle
from pyfaf.storage import ReportBacktrace, column_len


class FindCrashFunction(Action):
    name = "find-crashfn"

    def __init__(self):
        super(FindCrashFunction, self).__init__()

    def _find_crashfn(self, db, problemplugin, query_all=False):
        db_backtraces = get_backtraces_by_type(db, problemplugin.name,
                                               query_all=query_all)
        db_backtraces_count = db_backtraces.count()
        i = 0
        for db_backtrace in db_backtraces.yield_per(100):
            i += 1
            try:
                crashfn = (demangle(problemplugin.find_crash_function(
                    db_backtrace))[:column_len(ReportBacktrace, "crashfn")])
            except Exception as ex:
                self.log_warn("Unable to find crash function: {0}"
                              .format(str(ex)))
                continue

            if db_backtrace.crashfn != crashfn:
                self.log_info("[{0} / {1}] Updating backtrace #{2}: {3} ~> {4}"
                              .format(i, db_backtraces_count, db_backtrace.id,
                                      db_backtrace.crashfn, crashfn))
                db_backtrace.crashfn = crashfn
            else:
                self.log_info("[{0} / {1}] Backtrace #{2} up to date: {3}"
                              .format(i, db_backtraces_count, db_backtrace.id,
                                      db_backtrace.crashfn))

            if (i % 100) == 0:
                db.session.flush()

        db.session.flush()

    def run(self, cmdline, db):
        if len(cmdline.problemtype) < 1:
            ptypes = list(problemtypes.keys())
        else:
            ptypes = cmdline.problemtype

        i = 0
        for ptype in ptypes:
            i += 1
            problemplugin = problemtypes[ptype]
            self.log_info("[{0} / {1}] Processing problem type: {2}"
                          .format(i, len(ptypes), problemplugin.nice_name))

            self._find_crashfn(db, problemplugin, query_all=cmdline.all)

    def tweak_cmdline_parser(self, parser):
        parser.add_problemtype(multiple=True)
        parser.add_argument("-a", "--all", action="store_true", default=False,
                            help="Process all reports of the given type")
