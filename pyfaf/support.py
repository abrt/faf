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

def string_to_bool(text):
    return text in [u"True", u"true", u"yes", u"1"]

class GetOutOfLoop(Exception):
    pass

def as_table(headers, data, margin=1, separator=' '):
    '''
    Return `headers` and `data` lists formatted as table.
    '''

    headers = map(str, headers)
    data = map(lambda x: map(str, x), data)

    widths = reduce(
            lambda x, y: map(
            lambda (a,b): max(a,b), zip(x, y)
        ),
        map(lambda x: map(len, x), data) + [map(len, headers)],
        map(lambda _: 0, headers))

    fmt = ''
    for num, width in enumerate(widths):
        fmt += '{{{0}:<{1}}}{2}'.format(num, width, separator*margin)
    fmt += '\n'

    return ''.join(map(lambda row: fmt.format(*row), [headers] + data))
