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


"""add new value to repo_types enum

Revision ID: 89d35a57f82b
Revises: 50d3e87e4b2a
Create Date: 2016-05-30 10:55:33.988264

"""

# revision identifiers, used by Alembic.
revision = '89d35a57f82b'
down_revision = '50d3e87e4b2a'

from alembic import op
import sqlalchemy as sa


old_values = ['yum', 'koji']
new_values = old_values + ['rpmmetadata']

old_type = sa.Enum(*old_values, name='repo_type')
new_type = sa.Enum(*new_values, name='repo_type')
tmp_type = sa.Enum(*new_values, name='_repo_type')


def upgrade():
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE repo ALTER COLUMN type TYPE _repo_type USING '
               'type::text::_repo_type')
    old_type.drop(op.get_bind(), checkfirst=False)
    new_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE repo ALTER COLUMN type TYPE repo_type USING '
               'type::text::repo_type')
    tmp_type.drop(op.get_bind(), checkfirst=False)

def downgrade():
    op.execute('UPDATE repo SET type=\'yum\' WHERE type=\'rpmmetadata\'')
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE repo ALTER COLUMN type TYPE _repo_type USING '
               'type::text::_repo_type')
    new_type.drop(op.get_bind(), checkfirst=False)
    old_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE repo ALTER COLUMN type TYPE repo_type USING '
               'type::text::repo_type')
    tmp_type.drop(op.get_bind(), checkfirst=False)
