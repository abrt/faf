# Copyright (C) 2011 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from .helpers import *

class AbrtReportCheck:
    def __init__(self):
        # Id of the bug which was checked
        self.id = None
        self.reported_duphash = None
        self.expected_duphash = None
        self.backtrace_attachment_id = None
        self.backtrace_parseable = None
        self.expected_backtrace_rating = None
        self.reported_backtrace_rating = None
        self.expected_crash_function = None
        self.reported_crash_function = None

parser = toplevel("abrt_report_check",
                  AbrtReportCheck,
                  [int_positive("id"),
                   string("reported_duphash", null=True),
                   string("expected_duphash", null=True),
                   int_positive("backtrace_attachment_id", null=True),
                   boolean("backtrace_parseable", null=True),
                   int_unsigned("expected_backtrace_rating", null=True),
                   int_unsigned("reported_backtrace_rating", null=True),
                   string("expected_crash_function", null=True),
                   string("reported_crash_function", null=True)])
