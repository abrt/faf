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
Rename Kb to SF-prefilter

Revision ID: 82081a3c76b
Revises: 31d0249e8d4c
Create Date: 2014-10-21 12:34:28.849585
"""

from alembic.op import rename_table

# revision identifiers, used by Alembic.
revision = "82081a3c76b"
down_revision = "31d0249e8d4c"


def upgrade() -> None:
    rename_table("kbsolutions", "sfprefiltersolutions")
    rename_table("kbbacktracepath", "sfprefilterbacktracepaths")
    rename_table("kbpackagename", "sfprefilterpackagenames")


def downgrade() -> None:
    rename_table("sfprefiltersolutions", "kbsolutions")
    rename_table("sfprefilterbacktracepaths", "kbbacktracepath")
    rename_table("sfprefilterpackagenames", "kbpackagename")
