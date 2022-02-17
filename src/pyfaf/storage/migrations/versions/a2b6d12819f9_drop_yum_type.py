# Copyright (C) 2019  ABRT Team
# Copyright (C) 2019  Red Hat, Inc.
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
drop_yum_type

Revision ID: a2b6d12819f9
Revises: e5d5cefb8ca4
Create Date: 2019-02-08 11:41:56.967881
"""

from alembic.op import execute, get_bind
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a2b6d12819f9"
down_revision = "e5d5cefb8ca4"

new_values = ["dnf", "koji", "rpmmetadata"]
old_values = new_values + ["yum"]

old_type = sa.Enum(*old_values, name="repo_type")
new_type = sa.Enum(*new_values, name="repo_type")
tmp_type = sa.Enum(*new_values, name="_repo_type")


def upgrade() -> None:
    bind = get_bind()

    execute("UPDATE repo SET type='dnf' WHERE type='yum'")

    tmp_type.create(bind, checkfirst=False)
    execute("ALTER TABLE repo ALTER COLUMN type TYPE _repo_type USING "
            "type::text::_repo_type")
    old_type.drop(bind, checkfirst=False)
    new_type.create(bind, checkfirst=False)
    execute("ALTER TABLE repo ALTER COLUMN type TYPE repo_type USING "
            "type::text::repo_type")
    tmp_type.drop(bind, checkfirst=False)


def downgrade() -> None:
    bind = get_bind()

    tmp_type.create(bind, checkfirst=False)
    execute("ALTER TABLE repo ALTER COLUMN type TYPE _repo_type USING "
            "type::text::_repo_type")
    new_type.drop(bind, checkfirst=False)
    old_type.create(bind, checkfirst=False)
    execute("ALTER TABLE repo ALTER COLUMN type TYPE repo_type USING "
            "type::text::repo_type")
    tmp_type.drop(bind, checkfirst=False)
