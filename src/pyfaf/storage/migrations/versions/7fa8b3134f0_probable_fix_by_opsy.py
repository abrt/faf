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

"""
Probable fix by OpSysRelease

Revision ID: 7fa8b3134f0
Revises: 5695a1c595c3
Create Date: 2014-08-26 10:50:55.926760
"""

from alembic.op import create_table, drop_column, add_column, drop_table
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7fa8b3134f0'
down_revision = '5695a1c595c3'


def upgrade() -> None:
    create_table('problemopsysreleases',
                 sa.Column('problem_id', sa.Integer(), nullable=False),
                 sa.Column('opsysrelease_id', sa.Integer(), nullable=False),
                 sa.Column('probable_fix', sa.String(length=256), nullable=True),
                 sa.Column('probably_fixed_since', sa.DateTime(), nullable=True),
                 sa.ForeignKeyConstraint(['opsysrelease_id'], ['opsysreleases.id'], ),
                 sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ),
                 sa.PrimaryKeyConstraint('problem_id', 'opsysrelease_id'),
                )
    drop_column('problems', u'probably_fixed_since')
    drop_column('reports', u'probable_fix')


def downgrade() -> None:
    add_column('reports', sa.Column(u'probable_fix', sa.VARCHAR(length=256), nullable=True))
    add_column('problems', sa.Column(u'probably_fixed_since', postgresql.TIMESTAMP(), nullable=True))
    drop_table('problemopsysreleases')
