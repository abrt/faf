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

from functools import reduce

__all__ = ["as_table"]


def as_table(headers, data, margin=1, separator=' '):
    '''
    Return `headers` and `data` lists formatted as table.
    '''

    headers = map(str, headers)
    data = map(lambda x: map(str, x), data)

    widths = reduce(
        lambda x, y: map(
            lambda a_b: max(a_b[0], a_b[1]), zip(x, y)
        ),
        map(lambda x: map(len, x), data) + [map(len, headers)],
        map(lambda _: 0, headers))

    fmt = ''
    for num, width in enumerate(widths):
        fmt += '{{{0}:<{1}}}{2}'.format(num, width, separator * margin)
    fmt += '\n'

    # Used * or ** magic
    # pylint: disable-msg=W0142
    return ''.join(map(lambda row: fmt.format(*row), [headers] + data))
