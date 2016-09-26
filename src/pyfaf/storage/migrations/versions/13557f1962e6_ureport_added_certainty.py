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


"""ureport_added_certainty

Revision ID: 13557f1962e6
Revises: 2573150e1470
Create Date: 2016-08-09 10:01:00.818966

"""

# revision identifiers, used by Alembic.
revision = '13557f1962e6'
down_revision = '89d35a57f82b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('reports', sa.Column('max_certainty', sa.Integer, nullable=True))


def downgrade():
    op.drop_column("reports", "max_certainty")
