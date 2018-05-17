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


"""add contact email tables

Revision ID: 2e5f6d8b68f5
Revises: 272e6a3deea4
Create Date: 2015-01-07 09:13:07.655796

"""

# revision identifiers, used by Alembic.
revision = '2e5f6d8b68f5'
down_revision = '272e6a3deea4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('contactemails',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('email_address', sa.String(length=128), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    mysql_charset='utf8',
                    mysql_engine='InnoDB'
                   )
    op.create_table('reportcontactemails',
                    sa.Column('report_id', sa.Integer(), nullable=False),
                    sa.Column('contact_email_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['contact_email_id'], ['contactemails.id'], ),
                    sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
                    sa.PrimaryKeyConstraint('report_id', 'contact_email_id'),
                    mysql_charset='utf8',
                    mysql_engine='InnoDB'
                   )


def downgrade():
    op.drop_table('reportcontactemails')
    op.drop_table('contactemails')
