# Copyright (C) 2015  ABRT Team
# Copyright (C) 2015  Red Hat, Inc.
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


"""add EOL bz resolution

Revision ID: 2dfd5aef57ca
Revises: 58f44afc3a3a
Create Date: 2015-03-05 08:45:52.544974

"""

# revision identifiers, used by Alembic.
revision = '2dfd5aef57ca'
down_revision = '58f44afc3a3a'

from alembic import op


def upgrade():
    # PostgreSQL 9.1+ has the simpler
    # ALTER TYPE bzbug_resolution ADD VALUE 'EOL' AFTER 'INSUFFICIENT_DATA';
    # but we need to support 8.4
    op.execute("ALTER TYPE bzbug_resolution RENAME TO bzbug_resolution_old")
    op.execute("CREATE TYPE bzbug_resolution as enum ('NOTABUG', 'WONTFIX', "
               "'WORKSFORME', 'DEFERRED', 'CURRENTRELEASE', 'RAWHIDE', "
               "'ERRATA', 'DUPLICATE', 'UPSTREAM', 'NEXTRELEASE', 'CANTFIX', "
               "'INSUFFICIENT_DATA', 'EOL')")
    op.execute("ALTER TABLE bzbugs ALTER COLUMN resolution TYPE "
               "bzbug_resolution USING resolution::text::bzbug_resolution")
    op.execute("DROP TYPE bzbug_resolution_old")


def downgrade():
    op.execute("ALTER TYPE bzbug_resolution RENAME TO bzbug_resolution_old")
    op.execute("CREATE TYPE bzbug_resolution as enum ('NOTABUG', 'WONTFIX', "
               "'WORKSFORME', 'DEFERRED', 'CURRENTRELEASE', 'RAWHIDE', "
               "'ERRATA', 'DUPLICATE', 'UPSTREAM', 'NEXTRELEASE', 'CANTFIX', "
               "'INSUFFICIENT_DATA')")
    op.execute("ALTER TABLE bzbugs ALTER COLUMN resolution TYPE "
               "bzbug_resolution USING resolution::text::bzbug_resolution")
    op.execute("DROP TYPE bzbug_resolution_old")
