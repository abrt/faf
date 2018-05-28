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


"""Add privileged user field

Revision ID: 21345f007bdf
Revises: cef2fcd69ef
Create Date: 2015-08-18 14:56:02.571419

"""

# revision identifiers, used by Alembic.
revision = '21345f007bdf'
down_revision = 'cef2fcd69ef'

from alembic.op import add_column, drop_column
import sqlalchemy as sa


def upgrade():
    add_column('users', sa.Column('privileged', sa.Boolean(), nullable=True))


def downgrade():
    drop_column('users', 'privileged')
