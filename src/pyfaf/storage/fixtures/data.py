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

from datetime import date

ARCH = [
    'noarch',
    'src',
    'x86_64',
    'i686',
    'i586',
    'i486',
    'i386',
    'ppc',
    'ppc64',
    ]

OPSYS = {
    'Fedora':   [('17', date(2012, 5, 22)),
                 ('18', date(2013, 1, 15)),
                 ('devel', None)],

    'RHEL':     [('6', date(2010, 11, 10)),
                 ('6.1', date(2011, 5, 9)),
                 ('6.2', date(2011, 12, 6)),
                 ('6.3', date(2012, 6, 20)),
                 ('7', None)],

    'openSUSE': [('11.4', date(2011, 3, 10)),
                 ('12.1', date(2011, 11, 16))]
    }

COMPS = {
    'abrt':
        {'packages': ['abrt',
                      'abrt-gui',
                      'abrt-tui',
                      'abrt-addon-vmcore',
                      'abrt-addon-xorg',
                      'abrt-addon-ccpp',
                      'abrt-addon-python',
                      'abrt-addon-kerneloops',
                      'abrt-dbus',
                      'abrt-libs',
                      'abrt-python']},
    'libreport':
        {'packages': ['libreport',
                      'libreport-cli',
                      'libreport-devel',
                      'libreport-web',
                      'libreport-plugin-ureport']},
    'btparser':
        {'packages': ['btparser',
                      'btparser-devel',
                      'btparser-python']},
    'will-crash':
        {'packages': ['will-crash']},
    }

_LIBS = ['gtk', 'gdk', 'dbus', 'xul', 'GL', 'jvm', 'freetype']
LIBS = ['lib%s' % x for x in _LIBS]

FUNS = dir(__builtins__)
