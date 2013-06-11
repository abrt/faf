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

from hashlib import sha1
from . import ProblemType
from ..checker import (Checker,
                       DictChecker,
                       IntChecker,
                       ListChecker,
                       StringChecker)
from ..common import get_libname
from ..queries import (get_backtrace_by_hash,
                       get_reportexe,
                       get_symbol_by_name_path,
                       get_symbolsource)
from ..storage import (OpSysComponent,
                       ReportBacktrace,
                       ReportBtFrame,
                       ReportBtHash,
                       ReportBtThread,
                       ReportExecutable,
                       OpSysComponent,
                       Symbol,
                       SymbolSource,
                       column_len)

__all__ = [ "PythonProblem" ]

class PythonProblem(ProblemType):
    name = "python"
    nice_name = "Unhandled Python exception"

    checker = DictChecker({
      # no need to check type twice, the toplevel checker already did it
      # "type": StringChecker(allowed=[PythonProblem.name]),
      "exception_name": StringChecker(pattern=r"^[a-zA-Z0-9_]+$", maxlen=64),
      "component":      StringChecker(pattern=r"^[a-zA-Z0-9\-\._]+$",
                                      maxlen=column_len(OpSysComponent,
                                                        "name")),
      "stacktrace":     ListChecker(
                          DictChecker({
          "file_name":      StringChecker(maxlen=column_len(SymbolSource,
                                                            "path")),
          "file_line":      IntChecker(minval=1),
          "is_module":      Checker(bool),
          "line_contents":  StringChecker(maxlen=column_len(SymbolSource,
                                                            "srcline")),
        }), minlen=1
      )
    })

    def __init__(self, *args, **kwargs):
        hashkeys = ["processing.pythonhashframes", "processing.hashframes"]
        self.load_config_to_self("hashframes", hashkeys, 16, callback=int)

        cmpkeys = ["processing.pythoncmpframes", "processing.cmpframes",
                   "processing.clusterframes"]
        self.load_config_to_self("cmpframes", cmpkeys, 16, callback=int)

        ProblemType.__init__(self)

    def _hash_traceback(self, traceback):
        hashbase = []
        for frame in traceback:
            if frame["is_module"]:
                funcname = "<module>"
            else:
                funcname = frame["function_name"]

            hashbase.append("{0} @ {1} + {2}".format(funcname,
                                                     frame["file_name"],
                                                     frame["file_line"]))

        return sha1("\n".join(hashbase)).hexdigest()

    def validate_ureport(self, ureport):
        PythonProblem.checker.check(ureport)
        return True

    def hash_ureport(self, ureport):
        hashbase = [ureport["component"]]

        for i, frame in enumerate(ureport["stacktrace"]):
            # Instance of 'PythonProblem' has no 'hashframes' member
            # pylint: disable-msg=E1101
            if i >= self.hashframes:
                break

            if frame["is_module"]:
                funcname = "<module>"
            else:
                funcname = frame["function_name"]

            hashbase.append("{0} @ {1} + {2}".format(funcname,
                                                     frame["file_name"],
                                                     frame["file_line"]))

        return sha1("\n".join(hashbase)).hexdigest()

    def get_component_name(self, ureport):
        return ureport["component"]

    def save_ureport(self, db, db_report, ureport, flush=False):
        crashframe = ureport["stacktrace"][-1]
        if crashframe["is_module"]:
            crashfn = "<module>"
        else:
            crashfn = crashframe["function_name"]

        db_reportexe = get_reportexe(db, db_report, crashframe["file_name"])
        if db_reportexe is None:
            db_reportexe = ReportExecutable()
            db_reportexe.report = db_report
            db_reportexe.path = crashframe["file_name"]
            db_reportexe.count = 0
            db.session.add(db_reportexe)

        db_reportexe.count += 1

        bthash = self._hash_traceback(ureport["stacktrace"])
        db_backtrace = get_backtrace_by_hash(db, bthash)
        if db_backtrace is None:
            db_backtrace = ReportBacktrace()
            db_backtrace.report = db_report
            db_backtrace.crashfn = crashfn
            db.session.add(db_backtrace)

            db_bthash = ReportBtHash()
            db_bthash.type = "NAMES"
            db_bthash.hash = bthash
            db_bthash.backtrace = db_backtrace

            db_thread = ReportBtThread()
            db_thread.backtrace = db_backtrace
            db_thread.crashthread = True
            db.session.add(db_thread)

            new_symbols = {}
            new_symbolsources = {}

            i = 0
            for frame in ureport["stacktrace"]:
                i += 1

                if frame["is_module"]:
                    function_name = "<module>"
                else:
                    function_name = frame["function_name"]

                norm_path = get_libname(frame["file_name"])

                db_symbol = get_symbol_by_name_path(db, function_name,
                                                    norm_path)
                if db_symbol is None:
                    key = (function_name, norm_path)
                    if key in new_symbols:
                        db_symbol = new_symbols[key]
                    else:
                        db_symbol = Symbol()
                        db_symbol.name = function_name
                        db_symbol.normalized_path = norm_path
                        db.session.add(db_symbol)
                        new_symbols[key] = db_symbol

                db_symbolsource = get_symbolsource(db, db_symbol,
                                                   frame["file_name"],
                                                   frame["file_line"])
                if db_symbolsource is None:
                    key = (function_name, frame["file_name"],
                           frame["file_line"])
                    if key in new_symbolsources:
                        db_symbolsource = new_symbolsources[key]
                    else:
                        db_symbolsource = SymbolSource()
                        db_symbolsource.path = frame["file_name"]
                        db_symbolsource.offset = frame["file_line"]
                        db_symbolsource.srcline = frame["line_contents"]
                        db_symbolsource.symbol = db_symbol
                        db.session.add(db_symbolsource)
                        new_symbolsources[key] = db_symbolsource

                db_frame = ReportBtFrame()
                db_frame.order = i
                db_frame.inlined = False
                db_frame.symbolsource = db_symbolsource
                db_frame.thread = db_thread
                db.session.add(db_frame)

        if flush:
            db.session.flush()

    def save_ureport_post_flush(self):
        self.log_debug("save_ureport_post_flush is not required for python")

    def retrace_symbols(self):
        self.log_info("Retracing is not required for Python exceptions")

#    def compare(self, problem1, problem2):
#        pass

#    def mass_compare(self, problems):
#        pass
