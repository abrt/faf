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

from . import ProblemType
from ..config import config
from ..ureport import UReportError
from hashlib import sha1

class PythonProblem(ProblemType):
    name = "python"
    nice_name = "Unhandled Python exception"

    def __init__(self, *args, **kwargs):
        hashkeys = ["processing.pythonhashframes", "processing.hashframes"]
        self.load_config_to_self("hashframes", hashkeys, 16, callback=int)

        cmpkeys = ["processing.pythoncmpframes", "processing.cmpframes",
                   "processing.clusterframes"]
        self.load_config_to_self("cmpframes", cmpkeys, 16, callback=int)

        ProblemType.__init__(self)

    def validate_ureport(self, ureport):
        # ToDo: Very simple, needs to be rewritten with something more generic

        if "type" not in ureport:
            raise UReportError("ureport must have 'type' element")

        if ureport["type"].lower() != "python":
            raise UReportError("calling python validate on non-python ureport")

        if "exception_name" not in ureport:
            raise UReportError("python report must have"
                               "'exception_name' element")

        # ToDo: also check the actual value of exception_name

        if "component" not in ureport:
            raise UReportError("python report must have 'component' element")

        if not isinstance(ureport["component"], basestring):
            raise UReportError("component must be a string")

        if "traceback" not in ureport:
            raise UReportError("python report must have 'traceback' element")

        if not isinstance(ureport["traceback"], list):
            raise UReportError("python traceback must be a list of frames")

        for frame in ureport["traceback"]:
            if not isinstance(frame, dict):
                raise UReportError("python frame must be a dictionary")

            if ("file_name" not in frame or "file_line" not in frame or
                "is_module" not in frame or "line_contents" not in frame):
                raise UReportError("python frame must contain "
                                   "'file_name', 'file_line', 'is_module' and "
                                   "'line_contents' elements")

            if not isinstance(frame["file_name"], basestring):
                raise UReportError("'file_name' must be a string")

            if not isinstance(frame["file_line"], int):
                raise UReportError("'file_line' must be an integer")

            if not isinstance(frame["is_module"], bool):
                raise UReportError("'is_module' must be a boolean")

            if not isinstance(frame["line_contents"], basestring):
                raise UReportError("'line_contents' must be a string")

            if ("function_name" in frame and
                not isinstance(frame["function_name"], basestring)):
                raise UReportError("'function_name' must be a string")

            # ToDo: also check the actual values

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
