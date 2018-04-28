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

from rpm import labelCompare

BOOL_TRUE_STRINGS = ["1", "y", "t", "yes", "true"]

__all__ = ["parse_nvra", "str2bool"]


def parse_nvra(pkg):
    """
    Split name-version-release.arch.rpm into
    dictionary.
    """

    result = {}

    if pkg.endswith(".rpm"):
        pkg = pkg[:-4]

    dot = pkg.rfind(".")
    result["arch"] = pkg[dot + 1:]
    pkg = pkg[:dot]

    rel_dash = pkg.rfind("-", 0, dot)
    result["release"] = pkg[rel_dash + 1:dot]

    ver_dash = pkg.rfind("-", 0, rel_dash)
    result["version"] = pkg[ver_dash + 1:rel_dash]
    result["name"] = pkg[:ver_dash]

    return result


def str2bool(string):
    return string.lower() in BOOL_TRUE_STRINGS


def cmp_evr(a, b):
    return labelCompare((str(a[0] or 0), a[1], a[2]),
                        (str(b[0] or 0), b[1], b[2]))


SIGNAL_TO_NAME_DICT = {
    0: 'SIG_DFL',
    1: 'SIGHUP',
    # 1: 'SIG_IGN',
    2: 'SIGINT',
    3: 'SIGQUIT',
    4: 'SIGILL',
    5: 'SIGTRAP',
    6: 'SIGABRT',
    # 6: 'SIGIOT',
    7: 'SIGBUS',
    8: 'SIGFPE',
    9: 'SIGKILL',
    10: 'SIGUSR1',
    11: 'SIGSEGV',
    12: 'SIGUSR2',
    13: 'SIGPIPE',
    14: 'SIGALRM',
    15: 'SIGTERM',
    17: 'SIGCHLD',
    # 17: 'SIGCLD',
    18: 'SIGCONT',
    19: 'SIGSTOP',
    20: 'SIGTSTP',
    21: 'SIGTTIN',
    22: 'SIGTTOU',
    23: 'SIGURG',
    24: 'SIGXCPU',
    25: 'SIGX',
    26: 'SIGVTALRM',
    27: 'SIGPROF',
    28: 'SIGWINCH',
    29: 'SIGIO',
    # 29: 'SIGPOLL',
    30: 'SIGPWR',
    31: 'SIGSYS',
    34: 'SIGRTMIN',
    64: 'SIGRTMAX'
}


def signal2name(signal, with_number=False):
    number = ""
    if with_number:
        number = " {0}".format(signal)
    try:
        return SIGNAL_TO_NAME_DICT[int(signal)]+number
    except (ValueError, KeyError):
        return "UNKNOWN_SIGNAL"+number
