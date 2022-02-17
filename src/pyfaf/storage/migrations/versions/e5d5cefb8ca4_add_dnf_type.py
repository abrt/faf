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
Migration: add dnf repo type

Revision ID: e5d5cefb8ca4
Revises: 729a154b1609
Create Date: 2018-08-14 14:32:32.398243
"""

from alembic.op import execute, get_bind
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e5d5cefb8ca4"
down_revision = "729a154b1609"

old_values = ["yum", "koji", "rpmmetadata"]
new_values = old_values + ["dnf"]

old_type = sa.Enum(*old_values, name="repo_type")
new_type = sa.Enum(*new_values, name="repo_type")
tmp_type = sa.Enum(*new_values, name="_repo_type")


def upgrade() -> None:
    tmp_type.create(get_bind(), checkfirst=False)
    execute("ALTER TABLE repo ALTER COLUMN type TYPE _repo_type USING "
            "type::text::_repo_type")
    old_type.drop(get_bind(), checkfirst=False)
    new_type.create(get_bind(), checkfirst=False)
    execute("ALTER TABLE repo ALTER COLUMN type TYPE repo_type USING "
            "type::text::repo_type")
    tmp_type.drop(get_bind(), checkfirst=False)

def downgrade() -> None:
    execute("UPDATE repo SET type='yum' WHERE type='dnf'")
    tmp_type.create(get_bind(), checkfirst=False)
    execute("ALTER TABLE repo ALTER COLUMN type TYPE _repo_type USING "
            "type::text::_repo_type")
    new_type.drop(get_bind(), checkfirst=False)
    old_type.create(get_bind(), checkfirst=False)
    execute("ALTER TABLE repo ALTER COLUMN type TYPE repo_type USING "
            "type::text::repo_type")
    tmp_type.drop(get_bind(), checkfirst=False)
