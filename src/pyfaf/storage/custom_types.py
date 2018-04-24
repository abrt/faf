# Copyright (C) 2015  ABRT Team
# Copyright (C) 2015  Red Hat, Inc.
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

import re
from sqlalchemy import func
import sqlalchemy.types as types


class Semver(types.UserDefinedType):
    """
    Semnatic version type

    http://semver.org/
    https://github.com/theory/pg-semver/
    """

    def get_col_spec(self):
        """
        Map to SEMVER type
        """

        return "SEMVER"

    def bind_processor(self, dialect):
        """
        Convert data to be sent do DB
        """

        def process(value):
            return to_semver(value)

        return process

    def bind_expression(self, bindvalue):
        """
        Make sure we use to_semver database function
        during conversion
        """

        return func.to_semver(bindvalue, type_=self)


# Semver 1.0.0
semver_valid = re.compile("^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
                          "(-([a-zA-Z]+[0-9a-zA-Z-]*))?$")

semver_safe = re.compile("[^0-9.]")

def parts_fit(version_string):
    first = version_string.split('-')[0]
    parts = first.split('.')
    for part in parts[:3]:
        if int(part) >= 2 ** 31:
            return False
    return True

def is_semver(version_string):
    """
    Check if `version_string` matches semantic versioning format
    """

    return semver_valid.match(version_string) is not None and parts_fit(version_string)

def to_semver(version_string):
    """
    Returns Semver acceptable version string

    - returns original string if it's already valid

    or

    - erases non-semver_safe characters (2.23_05b -> 2.2305)
    - merges everything after the second dot character (0.2.4.25 -> 0.2.425)
    - make sure that there are exactly two dots (1.2 -> 1.2.0)
    - fits parts of the result into 31 bit range (20130222622 -> 2013022262)

    """

    if is_semver(version_string):
        return version_string

    if len(version_string) == 0:
        return "0.0.0"

    version_string = version_string.replace(',', '.')

    if version_string.count('.') > 2:
        sp = version_string.split('.')
        version_string = '.'.join(sp[:3]) + ''.join(sp[3:])

    if version_string.count('.') < 2:
        for i in range(2 - version_string.count('.')):
            version_string = version_string + ".0"

    version_string = semver_safe.sub('', version_string)

    def fit(part):
        """
        Strip last digit until we fit into 2^31
        """

        if part:
            while int(part) >= 2 ** 31:
                part = part[:-1]

        return part

    if len(version_string) >= 10:
        parts = version_string.split('.')
        version_string = '.'.join(map(fit, parts))

    return version_string
