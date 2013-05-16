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
from ..storage import OpSysComponent, Symbol

__all__ = [ "KerneloopsProblem" ]

class KerneloopsProblem(ProblemType):
    name = "kerneloops"
    nice_name = "Kernel oops"

    tainted_flags = ["module_proprietary", "forced_module", "forced_removal",
                     "smp_unsafe", "mce", "page_release", "userspace",
                     "died_recently", "acpi_overridden", "module_out_of_tree",
                     "staging_driver", "firmware_workaround", "warning"]

    modname_checker = StringChecker(pattern="^[a-zA-Z0-9_]+(\([A-Z\+]+\))?$")

    checker = DictChecker({
      # no need to check type twice, the toplevel checker already did it
      # "type": StringChecker(allowed=[KerneloopsProblem.name]),
      "component":   StringChecker(pattern="^kernel(-[a-zA-Z0-9\-\._]+)?$",
                                   maxlen=column_len(OpSysComponent, "name")),

      "taint_flags": ListChecker(StringChecker(allowed=tainted_flags)),

      "modules":     ListChecker(modname_checker),

      "frames":      ListChecker(
                       DictChecker({
          "address":         IntChecker(minval=0),
          "reliable":        Checker(bool),
          "function_name":   StringChecker(pattern="^[a-zA-Z0-9_]+$",
                                           maxlen=column_len(Symbol, "name")),
          "function_offset": IntChecker(minval=0),
          "function_length": IntChecker(minval=0),
        })
      )
    })

    def __init__(self, *args, **kwargs):
        hashkeys = ["processing.oopshashframes", "processing.hashframes"]
        self.load_config_to_self("hashframes", hashkeys, 16, callback=int)

        cmpkeys = ["processing.oopscmpframes", "processing.cmpframes",
                   "processing.clusterframes"]
        self.load_config_to_self("cmpframes", cmpkeys, 16, callback=int)

        ProblemType.__init__(self)

    def validate_ureport(self, ureport):
        KerneloopsProblem.checker.check(ureport)
        for frame in ureport["frames"]:
            if "module_name" in frame:
                KerneloopsProblem.modname_checker.check(frame["module_name"])

        return True

    def hash_ureport(self, ureport):
        hashbase = [ureport["component"]]

        for i, frame in enumerate(ureport["frames"]):
            if i >= self.hashframes:
                break

            if not "module_name" in frame:
                module = "vmlinux"
            else:
                module = frame["module_name"]

            hashbase.append("{0} @ {1}".format(frame["function_name"], module))

        return sha1("\n".join(hashbase)).hexdigest()

#    def save_ureport(self, ureport, db):
#        pass

    def retrace_symbols(self):
        self.log_info("Retracing is not yet implemented for kerneloops")

#    def compare(self, problem1, problem2):
#        pass

#    def mass_compare(self, problems):
#        pass
