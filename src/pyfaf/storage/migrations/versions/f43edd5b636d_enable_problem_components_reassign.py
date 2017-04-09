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


"""enable problem components reassign

Revision ID: f43edd5b636d
Revises: 71905f91e7b7
Create Date: 2017-04-09 18:04:25.575450

"""

# revision identifiers, used by Alembic.
revision = 'f43edd5b636d'
down_revision = '71905f91e7b7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'problemreassign',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('problem_id', sa.Integer, nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ),
        sa.ForeignKeyConstraint(['username'], ['users.username'], ),
    )
    op.create_index('ix_problemreassign_problem_id', 'problemreassign', ['problem_id'])


def downgrade():
    op.drop_index(op.f('ix_problemreassign_problem_id'), table_name='problemreassign')
    op.drop_table('problemreassign')
