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
from pyfaf.common import FafError, Plugin, import_dir, load_plugins

__all__ = ["ProblemType", "problemtypes"]

# Invalid name "problemtypes" for type constant
# pylint: disable-msg=C0103
problemtypes = {}
# pylint: enable-msg=C0103


class ProblemType(Plugin):
    """
    A common superclass for problem type plugins.
    """

    def __init__(self, *args, **kwargs):
        """
        The superclass constructor does not really need to be called, but it
        enables a few useful features (like unified logging). If not called
        by the child, it just makes sure that ProblemType class is not
        instantiated directly.
        """

        if self.__class__.__name__ == "ProblemType":
            raise FafError("You need to subclass the ProblemType class "
                           "in order to implement a problem type plugin.")

        super(ProblemType, self).__init__()

    def hash_ureport(self, ureport):
        """
        Used for fast(!) deduplication. If ureport1 and ureport2 are equal
        then hash_ureport(ureport1) == hash_ureport(ureport2). If ureport1
        and ureport2 are not equal, then the hashes are not equal as well.
        Assumes that the give uReport is valid.
        """

        raise NotImplementedError("hash_ureport is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def validate_ureport(self, ureport):
        """
        Validate the custom part of uReport. Raise UReportError if the report
        is not valid. If a report passes validate_ureport, it must be safe
        to call hash_ureport and save_ureport on it.
        """

        raise NotImplementedError("validate_ureport is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def save_ureport(self, db, db_report, ureport, flush=False):
        """
        Save the custom part of uReport into database. Assumes that
        the given uReport is valid. `db_report` may be a new object not
        yet flushed into database and thus may have no `id` attribute.
        """

        raise NotImplementedError("save_ureport is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def save_ureport_post_flush(self):
        """
        Save the parts that need the objects to be flushed into database.
        For example adding lobs requires the primary key to be available.
        """

        raise NotImplementedError("save_ureport_post_flush is not implemented "
                                  "for {0}".format(self.__class__.__name__))

    def get_component_name(self, ureport):
        """
        Get the component name against which the report should be filed.
        """

        raise NotImplementedError("get_component_name is not implemented for "
                                  "{0}".format(self.__class__.__name__))

    def retrace_symbols(self):
        """
        Retrace the symbols for the given problem type.
        """

        raise NotImplementedError("retrace_symbols is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def compare(self, db_report1, db_report2):
        """
        Compare 2 pyfaf.storage.Report objects returning an integer
        in range [-100; 100]
        -100: reports are totally different, report1 > report2
        0: reports are equal
        100: reports are totally different, report2 > report1
        """

        raise NotImplementedError("compare is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def compare_many(self, db_reports):
        """
        Some libraries (btparser, satyr) provide a way to compare
        many reports at the same time returning a report list
        and distances object. This may be a significant speedup.
        """

        raise NotImplementedError("compare_many is not implemented for {0}"
                                  .format(self.__class__.__name__))

    def check_btpath_match(self, ureport, parser):
        """
        Check whether a path in stacktrace matches to a knowledgebase rule.
        """

        raise NotImplementedError("check_btpath_match is not implemented for "
                                  "{0}".format(self.__class__.__name__))

import_dir(__name__, os.path.dirname(__file__))
load_plugins(ProblemType, problemtypes)
