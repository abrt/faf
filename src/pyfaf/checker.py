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

import re
from numbers import Integral
from pyfaf.common import FafError

__all__ = ["CheckError", "CheckerError", "Checker", "DictChecker",
           "IntChecker", "ListChecker", "StringChecker"]


class CheckerError(FafError):
    """
    Exception raised for errors in checker configuration.
    """


class CheckError(FafError):
    """
    Exception raised when given object does not pass the check.
    """


class Checker(object):
    """
    Generic checker. Checks that the object is of the required type
    and gives the possibility to specify allowed values whitelist.
    """

    def __init__(self, checktype, allowed=None, mandatory=True):
        if not isinstance(checktype, type):
            raise CheckerError("`checktype` must be a valid type")

        if allowed is None:
            allowed = []

        if not isinstance(allowed, list):
            raise CheckerError("`allowed` must be a list")

        if any([not isinstance(e, checktype) for e in allowed]):
            raise CheckerError("All elements of `allowed` must be of type '{0}'"
                               .format(checktype.__name__))

        self.checktype = checktype
        self.allowed = allowed
        self.mandatory = mandatory

    def check(self, obj):
        if not isinstance(obj, self.checktype):
            raise CheckError("Expected '{0}', got '{1}'"
                             .format(self.checktype.__name__,
                                     type(obj).__name__))

        if self.allowed and obj not in self.allowed:
            raise CheckError("Only the following values are allowed: {0}"
                             .format(", ".join(self.allowed)))


class IntChecker(Checker):
    """
    Integer checker. Requires numbers.Integral type (int or long)
    and gives the possibility to specify minimal/maximal value.
    """

    def __init__(self, minval=None, maxval=None, **kwargs):
        # Use numbers.Integral to handle both `int` and `long`
        super(IntChecker, self).__init__(Integral, **kwargs)

        self.minval = minval
        self.maxval = maxval

    def check(self, obj):
        super(IntChecker, self).check(obj)

        if self.minval is not None and obj < self.minval:
            raise CheckError("Expected number greater or equal to {0}, "
                             "got {1}".format(self.minval, obj))

        if self.maxval is not None and obj > self.maxval:
            raise CheckError("Expected number lesser or equal to {0}, "
                             "got {1}".format(self.maxval, obj))


class StringChecker(Checker):
    """
    String checker. Requires basestring type (str or unicode)
    and gives the possibility to specify maximal length and regexp pattern.
    """

    def __init__(self, pattern=None, maxlen=0, **kwargs):
        super(StringChecker, self).__init__(str, **kwargs)

        if pattern is not None:
            self.re = re.compile(pattern)
        else:
            self.re = None

        self.maxlen = maxlen

    def check(self, obj):
        super(StringChecker, self).check(obj)

        if self.maxlen > 0 and len(obj) > self.maxlen:
            raise CheckError("String '{0}' is too long, the limit is {1} "
                             "characters".format(obj.encode("utf-8"),
                                                 self.maxlen))

        if self.re is not None:
            match = self.re.match(obj)
            if not match:
                raise CheckError("String '{0}' does not match the pattern "
                                 " '{1}'".format(obj, self.re.pattern))


class ListChecker(Checker):
    """
    List checker. Requires list type and a checker for checking every element.
    Also gives possibility to specify minimal/maximal length.
    """

    def __init__(self, elemchecker, minlen=0, maxlen=0, **kwargs):
        super(ListChecker, self).__init__(list, **kwargs)

        if not isinstance(elemchecker, Checker):
            raise CheckerError("`elemchecker` must be an instance of Checker")

        self.elemchecker = elemchecker
        self.minlen = minlen
        self.maxlen = maxlen

    def check(self, obj):
        super(ListChecker, self).check(obj)

        if self.minlen > 0 and len(obj) < self.minlen:
            raise CheckError("The list must contain at least {0} elements"
                             .format(self.minlen))

        if self.maxlen > 0 and len(obj) > self.maxlen:
            raise CheckError("The list must contain at most {0} elements"
                             .format(self.maxlen))

        for elem in obj:
            try:
                self.elemchecker.check(elem)
            except CheckError as ex: # pylint: disable=try-except-raise
                raise CheckError("List element is invalid: {0}"
                                 .format(str(ex)))


class DictChecker(Checker):
    """
    Dictionary checker. Requires dict type and a dictionary in the form
    { "element_name1": checker1, "element_name2": checker2, ... }.
    """

    def __init__(self, elements, **kwargs):
        super(DictChecker, self).__init__(dict, **kwargs)

        if not isinstance(elements, dict):
            raise CheckerError("`elements` must be a dictionary in the form "
                               "{ 'element1': checker1, 'element2': checker2 }")

        self.elements = elements

    def check(self, obj):
        super(DictChecker, self).check(obj)

        for name, checker in self.elements.items():
            if name in obj:
                try:
                    checker.check(obj[name])
                except CheckError as ex: # pylint: disable=try-except-raise
                    raise CheckError("Element '{0}' is invalid: {1}"
                                     .format(name, str(ex)))

            elif checker.mandatory:
                raise CheckError("Element '{0}' is missing".format(name))
