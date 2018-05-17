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


"""assign build to operating system, release and architecture

Revision ID: 133991a89da4
Revises: 17d4911132f8
Create Date: 2016-09-08 09:08:26.035450

"""

# revision identifiers, used by Alembic.
revision = '133991a89da4'
down_revision = '17d4911132f8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('buildopsysreleasearch',
                    sa.Column('build_id', sa.Integer(), nullable=False),
                    sa.Column('opsysrelease_id', sa.Integer(), nullable=False),
                    sa.Column('arch_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['build_id'], ['builds.id'], ),
                    sa.ForeignKeyConstraint(['opsysrelease_id'], ['opsysreleases.id'], ),
                    sa.ForeignKeyConstraint(['arch_id'], ['archs.id'], ),
                    sa.PrimaryKeyConstraint('build_id', 'opsysrelease_id', 'arch_id'),
                   )


def downgrade():
    op.drop_table('buildopsysreleasearch')
