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

import os
from hashlib import sha1
from . import ProblemType
from ..checker import (Checker,
                       DictChecker,
                       IntChecker,
                       ListChecker,
                       StringChecker)
from ..common import FafError, column_len, get_libname
from ..queries import (get_backtrace_by_hash,
                       get_reportexe,
                       get_ssource_by_bpo,
                       get_symbol_by_name_path)
from ..storage import (OpSysComponent,
                       ReportBacktrace,
                       ReportBtFrame,
                       ReportBtHash,
                       ReportBtThread,
                       ReportExecutable,
                       Symbol,
                       SymbolSource)

__all__ = [ "CoredumpProblem" ]

class CoredumpProblem(ProblemType):
    name = "core"
    nice_name = "Crash of user-space binary"

    checker = DictChecker({
      # no need to check type twice, the toplevel checker already did it
      # "type": StringChecker(allowed=[CoredumpProblem.name]),
      "signal":     IntChecker(minval=0),
      "component":  StringChecker(pattern=r"^[a-zA-Z0-9\-\._]+$",
                                  maxlen=column_len(OpSysComponent, "name")),
      "executable": StringChecker(maxlen=column_len(ReportExecutable, "path")),
      "user":       DictChecker({
        "root":       Checker(bool),
        "local":      Checker(bool),
      }),
      "stacktrace": ListChecker(
                      DictChecker({
          "crash_thread": Checker(bool),
          "frames":       ListChecker(
                            DictChecker({
              "address":         IntChecker(minval=0),
              "build_id":        StringChecker(pattern=r"^[a-fA-F0-9]+$",
                                               maxlen=column_len(SymbolSource,
                                                                 "build_id")),
              "build_id_offset": IntChecker(minval=0),
              "file_name":       StringChecker(maxlen=column_len(SymbolSource,
                                                                 "path")),
              "fingerprint":     StringChecker(pattern=r"^[a-fA-F0-9]+$",
                                               maxlen=column_len(ReportBtHash,
                                                                 "hash"))
            }), minlen=1
          )
        }), minlen=1
      )
    })

    fname_checker = StringChecker(maxlen=column_len(Symbol, "nice_name"))

    def __init__(self, *args, **kwargs):
        hashkeys = ["processing.corehashframes", "processing.hashframes"]
        self.load_config_to_self("hashframes", hashkeys, 16, callback=int)

        cmpkeys = ["processing.corecmpframes", "processing.cmpframes",
                   "processing.clusterframes"]
        self.load_config_to_self("cmpframes", cmpkeys, 16, callback=int)

        ProblemType.__init__(self)

    def _get_crash_thread(self, stacktrace):
        """
        Searches for a single crash thread and return it. Raises FafError if
        there is no crash thread or if there are multiple crash threads.
        """

        crashthreads = filter(lambda t: t["crash_thread"], stacktrace)
        if len(crashthreads) < 1:
            raise FafError("No crash thread found")

        if len(crashthreads) > 1:
            raise FafError("Multiple crash threads found")

        return crashthreads[0]["frames"]

    def _hash_backtrace(self, backtrace):
        result = []

        for key in ["function_name", "fingerprint"]:
            hashbase = []

            threads_sane = []
            for thread in backtrace:
                threads_sane.append(all(key in f for f in thread["frames"]))

            if not all(threads_sane):
                continue

            for thread in backtrace:
                if thread["crash_thread"]:
                    hashbase.append("Crash Thread")
                else:
                    hashbase.append("Thread")

                for frame in thread["frames"]:
                    hashbase.append("  {0} @ {1} ({2})"
                                    .format(frame[key], frame["file_name"],
                                            frame["build_id"]))

            result.append(sha1("\n".join(hashbase)).hexdigest())

        return result

    def validate_ureport(self, ureport):
        CoredumpProblem.checker.check(ureport)

        for thread in ureport["stacktrace"]:
            for frame in thread["frames"]:
                if "function_name" in frame:
                    CoredumpProblem.fname_checker.check(frame["function_name"])

        # just to be sure there is exactly one crash thread
        self._get_crash_thread(ureport["stacktrace"])
        return True

    def hash_ureport(self, ureport):
        crashthread = self._get_crash_thread(ureport["stacktrace"])
        hashbase = [ureport["component"]]

        if all("function_name" in f for f in crashthread):
            key = "function_name"
        else:
            key = "fingerprint"

        for i, frame in enumerate(crashthread):
            # Instance of 'CoredumpProblem' has no 'hashframes' member
            # pylint: disable-msg=E1101
            if i >= self.hashframes:
                break

            hashbase.append("{0} @ {1}".format(frame[key], frame["file_name"]))

        return sha1("\n".join(hashbase)).hexdigest()

    def save_ureport(self, db, db_report, ureport, flush=False):
        db_reportexe = get_reportexe(db, db_report, ureport["executable"])
        if db_reportexe is None:
            db_reportexe = ReportExecutable()
            db_reportexe.path = ureport["executable"]
            db_reportexe.report = db_report
            db_reportexe.count = 0
            db.session.add(db_reportexe)

        db_reportexe.count += 1

        bthashes = self._hash_backtrace(ureport["stacktrace"])
        if len(bthashes) < 1:
            raise FafError("Unable to get backtrace hash")

        bts = filter(None, set(get_backtrace_by_hash(db, b) for b in bthashes))
        if len(bts) > 1:
            raise FafError("Unable to reliably identify backtrace by hash")

        if len(bts) == 1:
            db_backtrace = bts.pop()
        else:
            new_symbolsources = {}

            db_backtrace = ReportBacktrace()
            db_backtrace.report = db_report
            db.session.add(db_backtrace)

            for bthash in bthashes:
                db_bthash = ReportBtHash()
                db_bthash.backtrace = db_backtrace
                db_bthash.type = "NAMES"
                db_bthash.hash = bthash
                db.session.add(db_bthash)

            tid = 0
            for thread in ureport["stacktrace"]:
                tid += 1

                db_thread = ReportBtThread()
                db_thread.backtrace = db_backtrace
                db_thread.number = tid
                db_thread.crashthread = thread["crash_thread"]
                db.session.add(db_thread)

                fid = 0
                for frame in thread["frames"]:
                    fid += 1

                    path = os.path.abspath(frame["file_name"])
                    offset = frame["build_id_offset"]

                    db_symbol = None
                    if "function_name" in frame:
                        norm_path = get_libname(path)

                        db_symbol = \
                            get_symbol_by_name_path(db,
                                                    frame["function_name"],
                                                    norm_path)
                        if db_symbol is None:
                            db_symbol = Symbol()
                            db_symbol.name = frame["function_name"]
                            db_symbol.normalized_path = norm_path
                            db.session.add(db_symbol)

                    db_symbolsource = get_ssource_by_bpo(db, frame["build_id"],
                                                         path, offset)


                    if db_symbolsource is None:
                        ssource_tuple = (frame["build_id"], path, offset)

                        if ssource_tuple in new_symbolsources:
                            db_symbolsource = new_symbolsources[ssource_tuple]
                        else:
                            db_symbolsource = SymbolSource()
                            db_symbolsource.symbol = db_symbol
                            db_symbolsource.build_id = frame["build_id"]
                            db_symbolsource.path = path
                            db_symbolsource.offset = offset
                            db_symbolsource.hash = frame["fingerprint"]
                            db.session.add(db_symbolsource)
                            new_symbolsources[ssource_tuple] = db_symbolsource

                    db_frame = ReportBtFrame()
                    db_frame.thread = db_thread
                    db_frame.order = fid
                    db_frame.symbolsource = db_symbolsource
                    db_frame.inlined = False
                    db.session.add(db_frame)

        if flush:
            db.session.flush()

    def get_component_name(self, ureport):
        return ureport["component"]

    def retrace_symbols(self):
        self.log_info("Retracing is not yet implemented for coredumps")

#    def compare(self, problem1, problem2):
#        pass

#    def mass_compare(self, problems):
#        pass
