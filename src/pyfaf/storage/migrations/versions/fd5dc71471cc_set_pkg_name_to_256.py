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
set-pkg-name-to-256

Revision ID: fd5dc71471cc
Revises: 8ac9b3343649
Create Date: 2019-08-06 14:26:17.254047
"""

import sqlalchemy as sa
from alembic.op import alter_column


# revision identifiers, used by Alembic.
revision = "fd5dc71471cc"
down_revision = "8ac9b3343649"


def upgrade() -> None:
    alter_column("packages", "name", type_=sa.String(length=256), nullable=False)
    alter_column("opsyscomponents", "name", type_=sa.String(length=256), nullable=False)
    alter_column("builds", "base_package_name", type_=sa.String(length=256), nullable=False)
    alter_column("reportunknownpackages", "name", type_=sa.String(length=256), nullable=False)


def downgrade() -> None:
    alter_column("packages", "name", type_=sa.String(length=64), nullable=False)
    alter_column("opsyscomponents", "name", type_=sa.String(length=64), nullable=False)
    alter_column("builds", "base_package_name", type_=sa.String(length=64), nullable=False)
    alter_column("reportunknownpackages", "name", type_=sa.String(length=64), nullable=False)
