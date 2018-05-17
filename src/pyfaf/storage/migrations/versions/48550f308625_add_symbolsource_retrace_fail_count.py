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


"""Add SymbolSource retrace_fail_count

Revision ID: 48550f308625
Revises: 1c7edfbf8941
Create Date: 2015-04-27 10:26:28.975738

"""

# revision identifiers, used by Alembic.
revision = '48550f308625'
down_revision = '1c7edfbf8941'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('symbolsources', sa.Column('retrace_fail_count', sa.Integer(),
                                             nullable=False, server_default="0"))


def downgrade():
    op.drop_column('symbolsources', 'retrace_fail_count')
