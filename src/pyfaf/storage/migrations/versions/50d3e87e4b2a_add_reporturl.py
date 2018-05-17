# Copyright (C) 2015  ABRT Team
# Copyright (C) 2015  Red Hat, Inc.
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


"""add_reporturl

Revision ID: 50d3e87e4b2a
Revises: 21345f007bdf
Create Date: 2015-10-15 14:27:16.769105

"""

# revision identifiers, used by Alembic.
revision = '50d3e87e4b2a'
down_revision = '21345f007bdf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('reporturls',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('report_id', sa.Integer(), nullable=False),
                    sa.Column('url', sa.String(length=1024), nullable=False),
                    sa.Column('saved', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                   )

def downgrade():
    op.drop_table('reporturls')
