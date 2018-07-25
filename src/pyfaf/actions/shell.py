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

# Unused variable
# pylint: disable-msg=W0612

# Unused import
# pylint: disable-msg=W0611
# pylint: disable-msg=W0614

# Wildcard import
# pylint: disable-msg=W0401

from collections import Iterable
from sqlalchemy.sql.expression import func

import pyfaf
from pyfaf.storage import * # pylint: disable=redefined-builtin
from pyfaf.actions import Action


class Shell(Action):
    name = "shell"
    cmdline_only = True


    def run(self, cmdline, db):
        session = db.session

        def first(obj):
            return session.query(obj).first()

        # Redefining built-in 'any'
        # pylint: disable-msg=W0622
        def any(obj):
            if isinstance(obj, Iterable):
                return __builtins__["any"](obj)

            return session.query(obj).order_by(func.random()).first()

        try:
            import IPython
        except ImportError:
            print('IPython required')
            return 1

        # Module 'IPython' has no 'Shell' member
        # pylint: disable-msg=E1101
        if hasattr(IPython, "embed"):
            IPython.embed()
        else:
            IPython.Shell.IPShellEmbed()()
