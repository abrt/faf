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

import pyfaf
from pyfaf.storage import *
from pyfaf.actions import Action
from sqlalchemy.sql.expression import func


class Shell(Action):
    name = "shell"

    def __init__(self):
        Action.__init__(self)

    def run(self, cmdline, db):
        session = db.session

        def first(obj):
            return session.query(obj).first()

        def any(obj):
            return session.query(obj).order_by(func.random()).first()

        try:
            import IPython
        except ImportError:
            print('IPython required')
            return 1

        if hasattr(IPython, "embed"):
            IPython.embed()
        else:
            IPython.Shell.IPShellEmbed()()
