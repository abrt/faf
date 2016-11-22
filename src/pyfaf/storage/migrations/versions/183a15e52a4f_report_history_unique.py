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


"""Unique column added into report history

Revision ID: 183a15e52a4f
Revises: 13557f1962e6
Create Date: 2016-09-26 14:35:00.567052

"""

# revision identifiers, used by Alembic.
revision = '183a15e52a4f'
down_revision = '133991a89da4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('reporthistorydaily', sa.Column('unique', sa.Integer, nullable=True))
    op.add_column('reporthistoryweekly', sa.Column('unique', sa.Integer, nullable=True))
    op.add_column('reporthistorymonthly', sa.Column('unique', sa.Integer, nullable=True))


def downgrade():
    op.drop_column("reporthistorydaily", "unique")
    op.drop_column("reporthistoryweekly", "unique")
    op.drop_column("reporthistorymonthly", "unique")
