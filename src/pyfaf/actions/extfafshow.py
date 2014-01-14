# Copyright (C) 2014  ABRT Team
# Copyright (C) 2014  Red Hat, Inc.
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

from pyfaf.actions import Action
from pyfaf.queries import get_external_faf_instances
from pyfaf.utils.format import as_table


class ExternalFafShow(Action):
    name = "extfafshow"

    def __init__(self):
        super(ExternalFafShow, self).__init__()

    def run(self, cmdline, db):
        header = ["ID", "Name", "Base URL"]

        db_instances = get_external_faf_instances(db)
        data = []
        for db_instance in sorted(db_instances, key=lambda x: x.id):
            data.append((db_instance.id, db_instance.name, db_instance.baseurl))

        print(as_table(header, data, margin=2))
