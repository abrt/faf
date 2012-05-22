import sys
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
    'Fedora':   [('15',    date(2011, 5, 24)),
                 ('16',    date(2011, 11, 8)),
                 ('17',    date(2012, 5, 22)),
                 ('devel', None)],

    'RHEL':     [('6',   date(2010, 11, 10)),
                 ('6.1', date(2011, 5, 9)),
                 ('6.2', date(2011, 12, 6)),
                 ('6.3', None),
                 ('7',   None)],

    'openSUSE': [('11.4', date(2011, 3, 10)),
                 ('12.1', date(2011, 11, 16))]
    }

COMPS = set(map(lambda x: x.replace('_', '').split('.')[0], sys.modules))

_LIBS = ['gtk', 'gdk', 'dbus', 'xul', 'GL', 'jvm', 'freetype']
LIBS = map(lambda x: 'lib%s' % x, _LIBS)

FUNS = dir(__builtins__)
