#!/usr/bin/python
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

class Function:
    def __init__(self):
        self.symbol = None
        # fp = Fingerprint
        self.fp_library_function_calls = None
        self.fp_transitive_lib_calls = None
        self.fp_equality_jump_presence = None
        self.fp_unsigned_comparison_jump_presence = None
        self.fp_signed_comparison_jump_presence = None
        self.fp_andor_presence = None
        self.fp_shift_presence = None
        self.fp_simple_recursion_presence = None
        self.fp_unconditional_local_jump_presence = None
        self.fp_internal_calls = None

class Binary:
    def __init__(self):
        # Binary is identified by path, a string
        self.id = None
        self.functions = []

class Rpm:
    def __init__(self):
        # Rpm id
        self.id = None
        self.binaries = []

class KojiBuildFunfinReport:
    def __init__(self):
        # Build id
        self.id = None
        self.rpms = []

    def binaries(self):
        return reduce(lambda accum, rpm: accum + rpm.binaries, self.rpms, [])

binary_parser_array = [string("id"),
                       array_dict("functions",
                                  Function,
                                  [string("symbol"),
                                   string("fp_library_function_calls"),
                                   string("fp_transitive_lib_calls"),
                                   string("fp_equality_jump_presence"),
                                   string("fp_unsigned_comparison_jump_presence"),
                                   string("fp_signed_comparison_jump_presence"),
                                   string("fp_andor_presence"),
                                   string("fp_shift_presence"),
                                   string("fp_simple_recursion_presence"),
                                   string("fp_unconditional_local_jump_presence"),
                                   string("fp_internal_calls")])]

binary_parser = toplevel("binary",
                         Binary,
                         binary_parser_array)

parser = toplevel("koji_build_funfin_report",
                  KojiBuildFunfinReport,
                  [int_positive("id"),
                   array_dict("rpms",
                              Rpm,
                              [int_positive("id"),
                               array_dict("binaries",
                                          Binary,
                                          binary_parser_array)])])
