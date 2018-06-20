# Copyright (C) 2016  ABRT Team
# Copyright (C) 2016  Red Hat, Inc.
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
Create index on reportpackages table

Revision ID: 729a154b1609
Revises: f43edd5b636d
Create Date: 2018-06-12 14:53:06.150898
"""

from alembic.op import create_index, drop_index, f

# revision identifiers, used by Alembic.
revision = '729a154b1609'
down_revision = 'f43edd5b636d'

index_name = 'ix_reportpackages_report_id_installed_package_id'

def upgrade():
    create_index(f(index_name), 'reportpackages', ['report_id', 'installed_package_id'])


def downgrade():
    drop_index(f(index_name), table_name='reportpackages')
