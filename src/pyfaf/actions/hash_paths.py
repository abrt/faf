# Copyright (C) 2015  ABRT Team
# Copyright (C) 2015  Red Hat, Inc.
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

from sqlalchemy import or_

from pyfaf.actions import Action
from pyfaf.storage.symbol import Symbol
from pyfaf.utils.hash import hash_path


class HashPaths(Action):
    name = "hash-paths"

    def __init__(self):
        super(HashPaths, self).__init__()

        self.load_config_to_self("prefixes", ["ureport.private_prefixes"],
                                 "/home /opt /usr/local /tmp /var/tmp")

        self.prefixes = self.prefixes.split()

    def run(self, cmdline, db):
        q = db.session.query(Symbol)

        filters = []

        for p in self.prefixes:
            filters.append(Symbol.normalized_path.like("{}/%".format(p)))

        q = q.filter(or_(*filters))

        total = q.count()
        print("Going to process {} symbols".format(total))

        for c, symbol in enumerate(q.yield_per(100)):
            symbol.normalized_path = hash_path(symbol.normalized_path,
                                               self.prefixes)

            if not c % 1000:
                db.session.flush()

        db.session.flush()
        self.log_info("Done")
