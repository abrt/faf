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
from ..storage import OpSysComponent, SymbolSource

__all__ = [ "PythonProblem" ]

class PythonProblem(ProblemType):
    name = "python"
    nice_name = "Unhandled Python exception"

    checker = DictChecker({
      # no need to check type twice, the toplevel checker already did it
      # "type": StringChecker(allowed=[PythonProblem.name]),
      "exception_name": StringChecker(pattern="^[a-zA-Z0-9_]+$", maxlen=64),
      "component":      StringChecker(pattern="^[a-zA-Z0-9\-\._]+$",
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
        })
      )
    })

    def __init__(self, *args, **kwargs):
        hashkeys = ["processing.pythonhashframes", "processing.hashframes"]
        self.load_config_to_self("hashframes", hashkeys, 16, callback=int)

        cmpkeys = ["processing.pythoncmpframes", "processing.cmpframes",
                   "processing.clusterframes"]
        self.load_config_to_self("cmpframes", cmpkeys, 16, callback=int)

        ProblemType.__init__(self)

    def validate_ureport(self, ureport):
        PythonProblem.checker.check(ureport)
        return True

    def hash_ureport(self, ureport):
        hashbase = [ureport["component"]]

        for i, frame in enumerate(ureport["traceback"]):
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

#    def save_ureport(self, ureport, db):
#        pass

    def retrace_symbols(self):
        self.log_info("Retracing is not required for Python exceptions")

#    def compare(self, problem1, problem2):
#        pass

#    def mass_compare(self, problems):
#        pass
