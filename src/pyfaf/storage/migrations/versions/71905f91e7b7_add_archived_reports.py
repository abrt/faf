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


"""add_archived_reports

Revision ID: 71905f91e7b7
Revises: 9301a426f19d
Create Date: 2017-03-08 16:56:11.355916

"""

# revision identifiers, used by Alembic.
revision = '71905f91e7b7'
down_revision = '9301a426f19d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'reportarchive',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('active', sa.Boolean, nullable=False),
        sa.Column('report_id', sa.Integer, nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
        sa.ForeignKeyConstraint(['username'], ['users.username'], ),
    )


def downgrade():
    op.drop_table('reportarchive')
