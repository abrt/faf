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
        self.fingerprint_library_function_calls = None
        self.fingerprint_transitive_lib_calls = None
        self.fingerprint_equality_jump_presence = None
        self.fingerprint_unsigned_comparison_jump_presence = None
        self.fingerprint_signed_comparison_jump_presence = None
        self.fingerprint_andor_presence = None
        self.fingerprint_shift_presence = None
        self.fingerprint_simple_recursion_presence = None
        self.fingerprint_unconditional_local_jump_presence = None

class Binary:
    def __init__(self):
        self.path = None
        self.functions = []

class Rpm:
    def __init__(self):
        self.name = None
        self.evr = None
        self.architecture = None
        self.binaries = []

class KojiBuildFunfinReport:
    def __init__(self):
        # Build id
        self.id = None
        self.rpms = []


binary_parser_array = [string("path"),
                       array_dict("functions",
                                  Function,
                                  [string("fingerprint_library_function_calls"),
                                   string("fingerprint_transitive_lib_calls"),
                                   string("fingerprint_equality_jump_presence"),
                                   string("fingerprint_unsigned_comparison_jump_presence"),
                                   string("fingerprint_signed_comparison_jump_presence"),
                                   string("fingerprint_andor_presence"),
                                   string("fingerprint_shift_presence"),
                                   string("fingerprint_simple_recursion_presence"),
                                   string("fingerprint_unconditional_local_jump_presence")])]

binary_parser = toplevel("binary",
                         Binary,
                         binary_parser_array)

parser = toplevel("koji_build_funfin_report",
                  KojiBuildFunfinReport,
                  [int_positive("id"),
                   array_dict("rpms",
                              Rpm,
                              [string("name"),
                               string("evr"),
                               string("arch"),
                               array_dict("binaries",
                                          Binary,
                                          binary_parser_array)])])
