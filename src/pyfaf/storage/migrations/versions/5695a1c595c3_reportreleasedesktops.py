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


"""Added reportreleasedesktops table

Revision ID: 5695a1c595c3
Revises: 23bab42e7be7
Create Date: 2014-08-22 12:21:50.973673

"""

# revision identifiers, used by Alembic.
revision = '5695a1c595c3'
down_revision = '23bab42e7be7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('reportreleasedesktops',
                    sa.Column('report_id', sa.Integer(), nullable=False),
                    sa.Column('release_id', sa.Integer(), nullable=False),
                    sa.Column('desktop', sa.String(length=256), nullable=False),
                    sa.Column('count', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['release_id'], ['opsysreleases.id'], ),
                    sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
                    sa.PrimaryKeyConstraint('report_id', 'release_id', 'desktop'),
                   )


def downgrade():
    op.drop_table('reportreleasedesktops')
