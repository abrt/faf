# Copyright (C) 2018  Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from fedora_messaging import message


class FafMessage(message.Message):
    """
    A base class of a Fedora message that defines a message schema for
    messages published by FAF.
    """

    def __str__(self):
        """ Return human readable message """
        return "ABRT report for package {pkg} has reached {count} occurrences".format(pkg=self.components,
                                                                                      count=self.occurance)

    @property
    def summary(self):
        """ Summary of the crash report. """
        return "Property 'summary' not implemented in the FafMessage."

    @property
    def components(self):
        """ Components of the crash report. """
        return []

    @property
    def occurance(self):
        """ Occurance count of the crash report. """
        return "Property 'occurance' not implemented in the FafMessage."


class FafProblemMessage(FafMessage):
    """
    A sub-class of a Fedora message that defines a message schema for
    messages published by FAF to notify about a problem.
    """
    body_schema = {
        "id": "http://fedoraproject.org/message-schema/faf#",
        "$schema": "http://json-schema.org/draft-04/schema#",
        "desctription": "Schema for FAF server for problems",
        "type": "object",
        "properties": {
            "components": {
                "type": "array",
                "items": {"type": "string"}
            },
            "count": {"type": "number"},
            "first_occurrence": {"type": "string"},
            "function": {"type": "string"},
            "level": {"type": "number"},
            "problem_id": {"type": "number"},
            "type": {"type": "string"},
            "url": {"type": "string"}
        },
        "required": ["components", "count", "first_occurrence", "function", "level",
                     "problem_id", "type"]
    }

    @property
    def summary(self):
        """ Summary of the crash report. """
        return "ABRT report for package {pkg} has reached {count} occurrences".format(pkg=self.components,
                                                                                      count=self.occurance)

    @property
    def components(self):
        """ Components of the crash report. """
        return self._body["components"]

    @property
    def occurance(self):
        """ Occurance count of the crash report. """
        return self._body["count"]


class FafReportMessage(FafMessage):
    """
    A sub-class of a Fedora message that defines a message schema for
    messages published by FAF to notify about a crash report.
    """
    body_schema = {
        "id": "http://fedoraproject.org/message-schema/faf#",
        "$schema": "http://json-schema.org/draft-04/schema#",
        "desctription": "Schema for FAF server for crash reports",
        "type": "object",
        "properties": {
            "components": {
                "type": "array",
                "items": {"type": "string"}
            },
            "count": {"type": "number"},
            "first_occurrence": {"type": "string"},
            "function": {"type": "string"},
            "level": {"type": "number"},
            "problem_id": {"type": "number"},
            "report_id": {"type": "number"},
            "type": {"type": "string"},
            "url": {"type": "string"}
        },
        "required": ["components", "count", "first_occurrence", "function", "level",
                     "report_id", "type"]
    }

    @property
    def summary(self):
        """ Summary of the crash report. """
        return "ABRT report for package {pkg} has reached {count} occurrences".format(pkg=self.components,
                                                                                      count=self.occurance)
    @property
    def components(self):
        """ Components of the crash report. """
        return self._body["components"]

    @property
    def occurance(self):
        """ Occurance count of the crash report. """
        return self._body["count"]
