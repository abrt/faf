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


"""Link probable fix to Build

Revision ID: 272e6a3deea4
Revises: 82081a3c76b
Create Date: 2014-12-08 14:44:00.362834

"""

# revision identifiers, used by Alembic.
revision = '272e6a3deea4'
down_revision = '82081a3c76b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('problemopsysreleases', sa.Column('probable_fix_build_id', sa.Integer(), nullable=True))
    op.drop_column('problemopsysreleases', u'probable_fix')


def downgrade():
    op.add_column('problemopsysreleases',
                  sa.Column(u'probable_fix', sa.VARCHAR(length=256), autoincrement=False, nullable=True))
    op.drop_column('problemopsysreleases', 'probable_fix_build_id')
