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
"""Unit tests for the message schema."""
import unittest

from jsonschema import ValidationError
from .. import schema


class FafReportMessageTests(unittest.TestCase):
    """A set of unit tests to ensure the schema works as expected."""

    msg_class = schema.FafReportMessage

    def setUp(self):
        self.minimal_message = {
            'components': ['evolution'],
            'count': 7,
            'first_occurrence': '2015-04-10',
            'function': 'main',
            'level': 1,
            'report_id': 4321,
            'type': 'core'
        }
        self.full_message = {
            'components': ['evolution-full'],
            'count': 7,
            'first_occurrence': '2015-04-10',
            'function': 'main',
            'level': 1,
            'problem_id': 54321,
            'report_id': 54321,
            'type': 'core',
            'url': 'http://example.org/faf/reports/1234/'
        }

    def test_minimal_message(self):
        """
        Assert the message schema validates a message with the minimal number
        of required fields.
        """
        message = self.msg_class(body=self.minimal_message)

        message.validate()

    def test_full_message(self):
        """Assert a message with all fields passes validation."""
        message = self.msg_class(body=self.full_message)

        message.validate()

    def test_missing_fields(self):
        """Assert an exception is actually raised on validation failure."""
        del self.minimal_message["type"]
        message = self.msg_class(body=self.minimal_message)

        self.assertRaises(ValidationError, message.validate)


class FafProblemMessageTests(FafReportMessageTests):
    """A set of unit tests to ensure the schema works as expected."""

    msg_class = schema.FafProblemMessage

    def setUp(self):
        self.minimal_message = {
            'components': ['evolution'],
            'count': 7,
            'first_occurrence': '2015-04-10',
            'function': 'main',
            'level': 1,
            'problem_id': 4321,
            'type': 'core'
        }
        self.full_message = {
            'components': ['evolution-full'],
            'count': 7,
            'first_occurrence': '2015-04-10',
            'function': 'main',
            'level': 1,
            'problem_id': 54321,
            'type': 'core',
            'url': 'http://example.org/faf/reports/1234/'
        }

    def test_missing_fields(self):
        """Assert an exception is actually raised on validation failure."""
        del self.minimal_message["problem_id"]
        message = self.msg_class(body=self.minimal_message)

        self.assertRaises(ValidationError, message.validate)
