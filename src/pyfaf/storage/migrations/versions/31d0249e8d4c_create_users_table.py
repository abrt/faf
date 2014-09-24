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


"""create users table

Revision ID: 31d0249e8d4c
Revises: 7fa8b3134f0
Create Date: 2014-09-24 14:49:20.793855

"""

# revision identifiers, used by Alembic.
revision = '31d0249e8d4c'
down_revision = '7fa8b3134f0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'users',
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('mail', sa.String(length=150), nullable=False),
        sa.Column('admin', sa.Boolean(), default=False),
        sa.PrimaryKeyConstraint('username'),
    )


def downgrade():
    op.drop_table('users')
