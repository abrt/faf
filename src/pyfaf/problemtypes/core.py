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
from ..common import column_len
from ..config import config
from ..storage import (OpSysComponent,
                       ReportBtHash,
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
      "component":  StringChecker(pattern="^[a-zA-Z0-9\-\._]+$",
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
              "build_id":        StringChecker(pattern="^[a-fA-F0-9]+$",
                                               maxlen=column_len(SymbolSource,
                                                                 "build_id")),
              "build_id_offset": IntChecker(minval=0),
              "file_name":       StringChecker(maxlen=column_len(SymbolSource,
                                                                 "path")),
              "fingerprint":     StringChecker(pattern="^[a-fA-F0-9]+$",
                                               maxlen=column_len(ReportBtHash,
                                                                 "hash"))
            })
          )
        })
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
            if i >= self.hashframes:
                break

            hashbase.append("{0} @ {1}".format(frame[key], frame["file_name"]))

        return sha1("\n".join(hashbase)).hexdigest()

#    def save_ureport(self, ureport, db):
#        pass

    def retrace_symbols(self):
        self.log_info("Retracing is not yet implemented for coredumps")

#    def compare(self, problem1, problem2):
#        pass

#    def mass_compare(self, problems):
#        pass
