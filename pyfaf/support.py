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

import sys

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
