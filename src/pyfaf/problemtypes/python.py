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

from __future__ import unicode_literals
from string import ascii_uppercase #pylint: disable=deprecated-module

from typing import Tuple

import satyr

from pyfaf.problemtypes import ProblemType
from pyfaf.checker import (CheckError,
                           DictChecker,
                           IntChecker,
                           ListChecker,
                           StringChecker)
from pyfaf.common import get_libname
from pyfaf.queries import (get_reportexe,
                           get_symbol_by_name_path,
                           get_symbolsource)
from pyfaf.storage import (ReportBacktrace,
                           ReportBtFrame,
                           ReportBtHash,
                           ReportBtThread,
                           ReportExecutable,
                           OpSysComponent,
                           Symbol,
                           SymbolSource,
                           column_len)
from pyfaf.utils.parse import str2bool
from pyfaf.utils.hash import hash_list


__all__ = ["PythonProblem"]


class PythonProblem(ProblemType):
    name = "python"
    nice_name = "Unhandled Python exception"

    checker = DictChecker({
        # no need to check type twice, the toplevel checker already did it
        # "type": StringChecker(allowed=[PythonProblem.name]),
        "exception_name": StringChecker(pattern=r"^[a-zA-Z0-9_\.]+$", maxlen=256),
        "component":      StringChecker(pattern=r"^[a-zA-Z0-9\-\._]+$",
                                        maxlen=column_len(OpSysComponent,
                                                          "name")),
        "stacktrace":     ListChecker(DictChecker({
            "file_name":      StringChecker(maxlen=column_len(SymbolSource,
                                                              "path")),
            "file_line":      IntChecker(minval=1, mandatory=False),
            "line_contents":  StringChecker(maxlen=column_len(SymbolSource,
                                                              "srcline"),
                                            mandatory=False),
            "function_name": StringChecker(pattern=r"^([a-zA-Z0-9_]+|[a-z ']+)",
                                           maxlen=column_len(Symbol, "name"),
                                           mandatory=False),
            "special_function": StringChecker(pattern=r"^[a-zA-Z0-9_]+",
                                              maxlen=column_len(Symbol, "name"),
                                              mandatory=False),
        }), minlen=1)
    })

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()

        hashkeys = ["processing.pythonhashframes", "processing.hashframes"]
        self.hashframes = None
        self.load_config_to_self("hashframes", hashkeys, 16, callback=int)

        cmpkeys = ["processing.pythoncmpframes", "processing.cmpframes",
                   "processing.clusterframes"]
        self.cmpframes = None
        self.load_config_to_self("cmpframes", cmpkeys, 16, callback=int)

        cutkeys = ["processing.pythoncutthreshold", "processing.cutthreshold"]
        self.cutthreshold = None
        self.load_config_to_self("cutthreshold", cutkeys, 0.3, callback=float)

        normkeys = ["processing.pythonnormalize", "processing.normalize"]
        self.normalize = None
        self.load_config_to_self("normalize", normkeys, True, callback=str2bool)

        skipkeys = ["retrace.pythonskipsource", "retrace.skipsource"]
        self.skipsrc = None
        self.load_config_to_self("skipsrc", skipkeys, True, callback=str2bool)

    def _hash_traceback(self, traceback):
        hashbase = []
        for frame in traceback:
            if "special_function" in frame:
                funcname = "<{0}>".format(frame["special_function"])
            else:
                funcname = frame["function_name"]

            hashbase.append("{0} @ {1} + {2}".format(funcname,
                                                     frame["file_name"],
                                                     frame["file_line"]))

        return hash_list(hashbase)

    def db_report_to_satyr(self, db_report) -> satyr.PythonStacktrace:
        if not db_report.backtraces:
            self.log_warn("Report #{0} has no usable backtraces"
                          .format(db_report.id))
            return None

        db_backtrace = db_report.backtraces[0]

        if not db_backtrace.threads:
            self.log_warn("Backtrace #{0} has no usable threads"
                          .format(db_backtrace.id))
            return None

        db_thread = db_backtrace.threads[0]

        if not db_thread.frames:
            self.log_warn("Thread #{0} has no usable frames"
                          .format(db_thread.id))
            return None

        stacktrace = satyr.PythonStacktrace()
        if db_report.errname is not None:
            stacktrace.exception_name = db_report.errname

        for db_frame in db_thread.frames:
            frame = satyr.PythonFrame()
            funcname = db_frame.symbolsource.symbol.name
            if funcname.startswith("<") and funcname.endswith(">"):
                frame.special_function = funcname[1:-1]
            else:
                frame.function_name = funcname
            frame.file_line = db_frame.symbolsource.offset
            frame.file_name = db_frame.symbolsource.path

            if db_frame.symbolsource.srcline is not None:
                frame.line_contents = db_frame.symbolsource.srcline

            stacktrace.frames.append(frame)

        return stacktrace

    def validate_ureport(self, ureport) -> bool:
        PythonProblem.checker.check(ureport)

        for frame in ureport["stacktrace"]:
            if "function_name" not in frame and "special_function" not in frame:
                raise CheckError("Either `function_name` or `special_function`"
                                 " is required")
        return True

    def hash_ureport(self, ureport):
        hashbase = [ureport["component"]]

        for i, frame in enumerate(ureport["stacktrace"]):
            # Instance of 'PythonProblem' has no 'hashframes' member
            # pylint: disable-msg=E1101
            if i >= self.hashframes:
                break

            if "special_function" in frame:
                funcname = "<{0}>".format(frame["special_function"])
            else:
                funcname = frame["function_name"]

            hashbase.append("{0} @ {1} + {2}".format(funcname,
                                                     frame["file_name"],
                                                     frame["file_line"]))
        return hash_list(hashbase)

    def get_component_name(self, ureport) -> str:
        return ureport["component"]

    def save_ureport(self, db, db_report, ureport, flush=False, count=1) -> None:
        crashframe = ureport["stacktrace"][0]
        if "special_function" in crashframe:
            crashfn = "<{0}>".format(crashframe["special_function"])
        else:
            crashfn = crashframe["function_name"]

        if not db_report.errname or (ureport["exception_name"]
                                     and (ureport["exception_name"][0] in ascii_uppercase
                                          or "." in ureport["exception_name"])):
            # Only overwrite errname if the new one begins with an uppercase
            # letter or contains a ".", i.e. is probably a valid exception type
            db_report.errname = ureport["exception_name"]

        db_reportexe = get_reportexe(db, db_report, crashframe["file_name"])
        if db_reportexe is None:
            db_reportexe = ReportExecutable()
            db_reportexe.report = db_report
            db_reportexe.path = crashframe["file_name"]
            db_reportexe.count = 0
            db.session.add(db_reportexe)

        db_reportexe.count += count

        bthash = self._hash_traceback(ureport["stacktrace"])

        if not db_report.backtraces:
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

                if "special_function" in frame:
                    function_name = "<{0}>".format(frame["special_function"])
                else:
                    function_name = frame["function_name"]

                if "special_file" in frame:
                    file_name = "<{0}>".format(frame["special_file"])
                else:
                    file_name = frame["file_name"]

                norm_path = get_libname(file_name)

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
                                                   file_name,
                                                   frame["file_line"])
                if db_symbolsource is None:
                    key = (function_name, file_name,
                           frame["file_line"])
                    if key in new_symbolsources:
                        db_symbolsource = new_symbolsources[key]
                    else:
                        db_symbolsource = SymbolSource()
                        db_symbolsource.path = file_name
                        db_symbolsource.offset = frame["file_line"]
                        db_symbolsource.source_path = file_name
                        db_symbolsource.symbol = db_symbol
                        if "line_contents" in frame:
                            db_symbolsource.srcline = frame["line_contents"]
                        if "file_line" in frame:
                            db_symbolsource.line_number = frame["file_line"]
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

    def save_ureport_post_flush(self) -> None:
        self.log_debug("save_ureport_post_flush is not required for python")

    def _get_ssources_for_retrace_query(self, db) -> None:
        return None

    def find_packages_for_ssource(self, db, db_ssource) -> Tuple[None, Tuple[None, None, None]]:
        self.log_info("Retracing is not required for Python exceptions")
        return None, (None, None, None)

    def retrace(self, db, task) -> None:
        self.log_info("Retracing is not required for Python exceptions")

    def compare(self, db_report1, db_report2):
        satyr_report1 = self.db_report_to_satyr(db_report1)
        satyr_report2 = self.db_report_to_satyr(db_report2)
        return satyr_report1.distance(satyr_report2)

    def check_btpath_match(self, ureport, parser) -> bool:
        for frame in ureport["stacktrace"]:
            if "special_file" in frame:
                file_name = "<{0}>".format(frame["special_file"])
            else:
                file_name = frame["file_name"]

            match = parser.match(file_name)

            if match is not None:
                return True

        return False

    def find_crash_function(self, db_backtrace):
        crashthreads = [t for t in db_backtrace.threads if t.crashthread]
        if not crashthreads:
            self.log_debug("crashthread not found")
            return None

        if len(crashthreads) > 1:
            self.log_debug("multiple crash threads found")
            return None

        db_symbol = crashthreads[0].frames[0].symbolsource.symbol

        return db_symbol.nice_name or db_symbol.name
