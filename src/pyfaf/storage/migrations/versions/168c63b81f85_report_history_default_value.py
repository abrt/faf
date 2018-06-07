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

from alembic.op import alter_column, execute

"""report_history_default_value

Revision ID: 168c63b81f85
Revises: 183a15e52a4f
Create Date: 2016-12-13 15:49:32.883743

"""

# revision identifiers, used by Alembic.
revision = '168c63b81f85'
down_revision = '1c4d6317721a'


def upgrade():
    alter_column('reporthistorydaily', 'unique', server_default="0")
    alter_column('reporthistoryweekly', 'unique', server_default="0")
    alter_column('reporthistorymonthly', 'unique', server_default="0")

    execute('UPDATE reporthistorydaily SET "unique" = 0 WHERE "unique" IS NULL')
    execute('UPDATE reporthistoryweekly SET "unique" = 0 WHERE "unique" IS NULL')
    execute('UPDATE reporthistorymonthly SET "unique" = 0 WHERE "unique" IS NULL')


def downgrade():
    alter_column('reporthistorydaily', 'unique', server_default=None)
    alter_column('reporthistoryweekly', 'unique', server_default=None)
    alter_column('reporthistorymonthly', 'unique', server_default=None)

    execute('UPDATE reporthistorydaily SET "unique" = NULL WHERE "unique" = 0')
    execute('UPDATE reporthistoryweekly SET "unique" = NULL WHERE "unique" = 0')
    execute('UPDATE reporthistorymonthly SET "unique" = NULL WHERE "unique" = 0')
