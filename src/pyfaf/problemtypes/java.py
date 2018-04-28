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

import satyr
from pyfaf.problemtypes import ProblemType
from pyfaf.checker import (Checker,
                           DictChecker,
                           IntChecker,
                           ListChecker,
                           StringChecker)
from pyfaf.queries import (get_symbol_by_name_path,
                           get_symbolsource)
from pyfaf.storage import (ReportBacktrace,
                           ReportBtFrame,
                           ReportBtHash,
                           ReportBtThread,
                           OpSysComponent,
                           Symbol,
                           SymbolSource,
                           column_len)
from pyfaf.utils.parse import str2bool
from pyfaf.utils.hash import hash_list

__all__ = ["JavaProblem"]


class JavaProblem(ProblemType):
    name = "java"
    nice_name = "Unhandled Java exception"

    checker = DictChecker({
        # no need to check type twice, the toplevel checker already did it
        # "type": StringChecker(allowed=[JavaProblem.name]),
        "component":      StringChecker(pattern=r"^[a-zA-Z0-9\-\._]+$",
                                        maxlen=column_len(OpSysComponent,
                                                          "name")),
        "threads":        ListChecker(DictChecker({
            "name":           StringChecker(),
            "frames":         ListChecker(DictChecker({
                "name":           StringChecker(maxlen=column_len(Symbol,
                                                                  "name")),
                "is_native":      Checker(bool),
                "is_exception":   Checker(bool),
            }), minlen=1),
        }), minlen=1)
    })

    default_frame_checker = DictChecker({
        "file_name":  StringChecker(maxlen=column_len(SymbolSource,
                                                      "source_path")),
        "file_line":  IntChecker(minval=1),
        "class_path": StringChecker(maxlen=column_len(SymbolSource, "path")),
    })

    exception = "Exception thrown"
    native = "Native function call"
    unknown = "Unknown"

    def __init__(self, *args, **kwargs):
        super(JavaProblem, self).__init__()

        hashkeys = ["processing.javahashframes", "processing.hashframes"]
        self.load_config_to_self("hashframes", hashkeys, 16, callback=int)

        cmpkeys = ["processing.javacmpframes", "processing.cmpframes",
                   "processing.clusterframes"]
        self.load_config_to_self("cmpframes", cmpkeys, 16, callback=int)

        cutkeys = ["processing.javacutthreshold", "processing.cutthreshold"]
        self.load_config_to_self("cutthreshold", cutkeys, 0.3, callback=float)

        normkeys = ["processing.javanormalize", "processing.normalize"]
        self.load_config_to_self("normalize", normkeys, True, callback=str2bool)

        skipkeys = ["retrace.javaskipsource", "retrace.skipsource"]
        self.load_config_to_self("skipsrc", skipkeys, True, callback=str2bool)

    def _hash_backtrace(self, threads):
        hashbase = []

        for thread in threads:
            hashbase.append("Thread")

            for frame in thread["frames"]:
                # Instance of 'JavaProblem' has no 'hashframes' member
                # pylint: disable-msg=E1101

                if "class_path" in frame:
                    hashbase.append("{0} @ {1}".format(frame["name"],
                                                       frame["class_path"]))
                    continue

                hashbase.append(frame["name"])

        return hash_list(hashbase)

    def _db_backtrace_find_crash_thread(self, db_backtrace):
        if len(db_backtrace.threads) == 1:
            return db_backtrace.threads[0]

        db_threads = [t for t in db_backtrace.threads if t.crashthread]
        if len(db_threads) < 1:
            raise FafError("No crash thread could be found for backtrace #{0}"
                           .format(db_backtrace.id))

        if len(db_threads) > 1:
            raise FafError("Multiple crash threads found for backtrace #{0}"
                           .format(db_backtrace.id))

        return db_threads[0]

    def _db_frame_to_satyr(self, db_frame):
        class_path = db_frame.symbolsource.path

        result = satyr.JavaFrame()
        result.name = db_frame.symbolsource.symbol.name
        result.is_native = class_path == JavaProblem.native
        result.is_exception = class_path == JavaProblem.exception
        if class_path not in [JavaProblem.exception,
                              JavaProblem.native,
                              JavaProblem.unknown]:
            result.class_path = class_path
        if db_frame.symbolsource.source_path is not None:
            result.file_name = db_frame.symbolsource.source_path
        result.file_line = db_frame.symbolsource.line_number

        return result

    def _db_thread_to_satyr(self, db_thread):
        if len(db_thread.frames) < 1:
            self.log_warn("Thread #{0} has no usable frames"
                          .format(db_thread.id))
            return None

        result = satyr.JavaThread()
        result.name = "Thread #{0}".format(db_thread.number)
        for db_frame in db_thread.frames:
            frame = self._db_frame_to_satyr(db_frame)
            if frame is None:
                continue

            result.frames.append(frame)

        return result

    def _db_backtrace_to_satyr(self, db_backtrace):
        if len(db_backtrace.threads) < 1:
            self.log_warn("Backtrace #{0} has no usable threads"
                          .format(db_backtrace.id))
            return None

        if len(db_backtrace.threads) > 1:
            self.log_warn("Backtrace #{0} has several threads"
                          .format(db_backtrace.id))

        return self._db_thread_to_satyr(db_backtrace.threads[0])

    def _db_report_to_satyr(self, db_report):
        if len(db_report.backtraces) < 1:
            self.log_warn("Report #{0} has no usable backtraces"
                          .format(db_report.id))
            return None

        return self._db_backtrace_to_satyr(db_report.backtraces[0])

    def validate_ureport(self, ureport):
        JavaProblem.checker.check(ureport)
        for thread in ureport["threads"]:
            for frame in thread["frames"]:
                if not frame["is_native"] and not frame["is_exception"]:
                    JavaProblem.default_frame_checker.check(frame)

        return True

    def hash_ureport(self, ureport):
        hashbase = [ureport["component"]]

        # at the moment we only send crash thread
        # we may need to identify the crash thread in the future
        for i, frame in enumerate(ureport["threads"][0]["frames"]):
            # Instance of 'JavaProblem' has no 'hashframes' member
            # pylint: disable-msg=E1101
            if i >= self.hashframes:
                break

            if "class_path" in frame:
                hashbase.append("{0} @ {1}".format(frame["name"],
                                                   frame["class_path"]))
                continue

            hashbase.append(frame["name"])

        return hash_list(hashbase)

    def get_component_name(self, ureport):
        return ureport["component"]

    def save_ureport(self, db, db_report, ureport, flush=False, count=1):
        # at the moment we only send crash thread
        # we may need to identify the crash thread in the future
        crashthread = ureport["threads"][0]

        crashfn = None
        for frame in crashthread["frames"]:
            if not frame["is_exception"]:
                crashfn = frame["name"]
                break

        if crashfn is not None and "." in crashfn:
            crashfn = crashfn.rsplit(".", 1)[1]

        errname = None
        for frame in crashthread["frames"]:
            if frame["is_exception"]:
                errname = frame["name"]
                break

        if "." in errname:
            errname = errname.rsplit(".", 1)[1]

        db_report.errname = errname

        bthash = self._hash_backtrace(ureport["threads"])

        if len(db_report.backtraces) < 1:
            db_backtrace = ReportBacktrace()
            db_backtrace.report = db_report
            db_backtrace.crashfn = crashfn
            db.session.add(db_backtrace)

            db_bthash = ReportBtHash()
            db_bthash.type = "NAMES"
            db_bthash.hash = bthash
            db_bthash.backtrace = db_backtrace

            new_symbols = {}
            new_symbolsources = {}

            j = 0
            for thread in ureport["threads"]:
                j += 1

                db_thread = ReportBtThread()
                db_thread.backtrace = db_backtrace
                db_thread.crashthread = thread == crashthread
                db_thread.number = j
                db.session.add(db_thread)

                i = 0
                for frame in thread["frames"]:
                    i += 1

                    function_name = frame["name"]

                    if "class_path" in frame:
                        file_name = frame["class_path"]
                    elif frame["is_exception"]:
                        file_name = JavaProblem.exception
                    elif frame["is_native"]:
                        file_name = JavaProblem.native
                    else:
                        file_name = JavaProblem.unknown

                    if "file_line" in frame:
                        file_line = frame["file_line"]
                    else:
                        file_line = 0

                    db_symbol = get_symbol_by_name_path(db, function_name,
                                                        file_name)
                    if db_symbol is None:
                        key = (function_name, file_name)
                        if key in new_symbols:
                            db_symbol = new_symbols[key]
                        else:
                            db_symbol = Symbol()
                            db_symbol.name = function_name
                            db_symbol.normalized_path = file_name
                            db.session.add(db_symbol)
                            new_symbols[key] = db_symbol

                    db_symbolsource = get_symbolsource(db, db_symbol,
                                                       file_name,
                                                       file_line)
                    if db_symbolsource is None:
                        key = (function_name, file_name, file_line)
                        if key in new_symbolsources:
                            db_symbolsource = new_symbolsources[key]
                        else:
                            db_symbolsource = SymbolSource()
                            db_symbolsource.path = file_name
                            db_symbolsource.offset = file_line
                            if "file_name" in frame:
                                db_symbolsource.source_path = frame["file_name"]
                            db_symbolsource.line_number = file_line
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
        self.log_debug("save_ureport_post_flush is not required for java")

    def _get_ssources_for_retrace_query(self, db):
        return None

    def find_packages_for_ssource(self, db, db_ssource):
        self.log_info("Retracing is not required for Java exceptions")
        return None, (None, None, None)

    def retrace(self, db, task):
        self.log_info("Retracing is not required for Java exceptions")

    def compare(self, db_report1, db_report2):
        satyr_report1 = self._db_report_to_satyr(db_report1)
        satyr_report2 = self._db_report_to_satyr(db_report2)
        return satyr_report1.distance(satyr_report2)

    def compare_many(self, db_reports):
        self.log_info("Loading reports")
        reports = []
        ret_db_reports = []

        i = 0
        for db_report in db_reports:
            i += 1

            self.log_debug("[{0} / {1}] Loading report #{2}"
                           .format(i, len(db_reports), db_report.id))

            report = self._db_report_to_satyr(db_report)
            if report is None:
                self.log_debug("Unable to build satyr.JavaStacktrace")
                continue

            reports.append(report)
            ret_db_reports.append(db_report)

        self.log_info("Calculating distances")
        distances = satyr.Distances(reports, len(reports))

        return ret_db_reports, distances

    def check_btpath_match(self, ureport, parser):
        for thread in ureport["threads"]:
            for frame in thread["frames"]:
                for key in ["class_path", "file_name"]:
                    if key in frame:
                        match = parser.match(frame[key])

                        if match is not None:
                            return True

        return False

    def find_crash_function(self, db_backtrace):
        crash_thread = self._db_backtrace_find_crash_thread(db_backtrace)
        return crash_thread.frames[0].symbolsource.symbol.name
