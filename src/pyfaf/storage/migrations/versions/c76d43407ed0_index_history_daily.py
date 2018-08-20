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

"""
Add index into reporthistorydaily

Revision ID: c76d43407ed0
Revises: e5d5cefb8ca4
Create Date: 2018-08-20 11:26:36.991067
"""

from alembic.op import create_index, drop_index, f


# revision identifiers, used by Alembic.
revision = 'c76d43407ed0'
down_revision = 'e5d5cefb8ca4'


def upgrade():
    create_index(f('ix_reporthistorydaily_day'), 'reporthistorydaily', ['day'], unique=False)

def downgrade():
    drop_index(f('ix_reporthistorydaily_day'), table_name='reporthistorydaily')
