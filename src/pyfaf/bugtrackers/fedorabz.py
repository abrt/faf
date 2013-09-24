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

from pyfaf.bugtrackers import bugzilla

__all__ = ["FedoraBugzilla"]


class FedoraBugzilla(bugzilla.Bugzilla):
    name = "fedora-bugzilla"

    def list_bugs(self, *args, **kwargs):

        abrt_specific = dict(
            status_whiteboard="abrt_hash",
            status_whiteboard_type="allwordssubstr",
            product="Fedora",
        )

        if 'custom_fields' in kwargs:
            kwargs['custom_fields'].update(abrt_specific)
        else:
            kwargs['custom_fields'] = abrt_specific

        return super(FedoraBugzilla, self).list_bugs(*args, **kwargs)
