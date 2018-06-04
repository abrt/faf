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

from alembic.op import add_column, drop_column
import sqlalchemy as sa

"""Ignore private bugzilla bugz

Revision ID: acd3d9bf85d1
Revises: 168c63b81f85
Create Date: 2017-07-25 09:03:53.335397

"""

# revision identifiers, used by Alembic.
revision = 'acd3d9bf85d1'
down_revision = '168c63b81f85'


def upgrade():
    add_column('bzbugs', sa.Column('private', sa.Boolean(), nullable=False, server_default='f'))


def downgrade():
    drop_column("bzbugs", "private")
