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

"""
Drop running_package from reportpackages

Revision ID: 58f44afc3a3a
Revises: 1b264b21ca91
Create Date: 2015-03-03 17:56:36.903726
"""

from alembic.op import drop_constraint, drop_column, add_column
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '58f44afc3a3a'
down_revision = '1b264b21ca91'


def upgrade():
    drop_constraint("reportpackages_running_package_id_fkey",
                    "reportpackages")

    drop_column("reportpackages", "running_package_id")


def downgrade():
    add_column("reportpackages",
               sa.Column("running_package_id", sa.Integer(),
                         sa.ForeignKey('packages.id'),
                         nullable=True))
