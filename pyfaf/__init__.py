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
import cache
import run
import config
import terminal
import sys
import argparse

verbosity = 0

class VerboseAction(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        if values is None:
            values='1'
        try:
            values=int(values)
        except ValueError:
            values=values.count('v')+1
        setattr(args, self.dest, values)

# TODO: remove
def handle_verbosity_args(argv):
    global verbosity
    for arg in argv[:]:
        if arg == "--verbose" or arg == "-v":
            verbosity += 1
            argv.remove(arg)
        elif arg == "-vv":
            verbosity += 2
            argv.remove(arg)
        elif arg == "-vvv":
            verbosity += 3
            argv.remove(arg)

def log0(message):
    sys.stdout.write(message)
def log1(message):
    if verbosity > 0:
        sys.stdout.write(message)
def log2(message):
    if verbosity > 1:
        sys.stdout.write(message)
def log3(message):
    if verbosity > 2:
        sys.stdout.write(message)


def human_byte_count(num):
    num = int(num)
    if num == 0:
        return "0"
    if num < 1024:
        return "{0} bytes".format(num)
    for x in ['kB','MB','GB','TB']:
        num /= 1024.0
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
    sys.stderr.write("Invalid size {0}.\n".format(num))
    exit(1)
