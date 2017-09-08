# Copyright (C) 2017  ABRT Team
# Copyright (C) 2017  Red Hat, Inc.
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


"""Support unpackaged executables

Revision ID: c2c9ea82f7f5
Revises: acd3d9bf85d1
Create Date: 2017-09-09 08:48:17.397236

"""

# revision identifiers, used by Alembic.
revision = 'c2c9ea82f7f5'
down_revision = 'acd3d9bf85d1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("reports", sa.Column("unpackaged", sa.Boolean(), nullable=False))
    op.execute('UPDATE reports SET "unpackaged" = False WHERE "unpackaged" IS NULL')

def downgrade():
    op.drop_column("reports", "unpackaged")
