# Copyright (C) 2019  ABRT Team
# Copyright (C) 2019  Red Hat, Inc.
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

"""
Drop not used opsysreleasescomponentsassociates table

Revision ID: cee07a513404
Revises: e17dc14292b9
Create Date: 2019-04-25 13:51:14.321913
"""

from alembic.op import drop_table, get_bind
from sqlalchemy.engine import reflection


# revision identifiers, used by Alembic.
revision = 'cee07a513404'
down_revision = 'e17dc14292b9'


def upgrade() -> None:
    """
     'opsysreleasescomponentsassociates' is an old table that was replaced by
     'opsyscomponentsassociates' and is no longer used anywhere.

     Older deployments may still have this table in DB, but in newly created DBs
     this table shouldn't exist.

     It holds data about associates and their relation to components from PkgDb
     that was replaced by Pagure.

     See revision: 9301a426f19d

     Relevant github commit:
     https://github.com/abrt/faf/commit/4e56c268e3bc51d8b880393e400e8968de1ae76c#diff-96c12153abda7ddb6637b5a2fd394887
    """

    conn = get_bind()
    inspector = reflection.Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    if 'opsysreleasescomponentsassociates' in tables:
        drop_table('opsysreleasescomponentsassociates')

def downgrade() -> None:
    """
     The dropped table is not used anymore so do nothing when downgrading.
    """
