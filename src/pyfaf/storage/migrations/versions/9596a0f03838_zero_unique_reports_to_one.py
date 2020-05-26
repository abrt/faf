# Copyright (C) 2020  ABRT Team
# Copyright (C) 2020  Red Hat, Inc.
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
Make all report summaries contain at least one unique report

Revision ID: 9596a0f03838
Revises: fd5dc71471cc
Create Date: 2020-01-09 09:23:53.053811
"""

from alembic.op import execute
from sqlalchemy import and_, update

import pyfaf.storage as st


# revision identifiers, used by Alembic.
revision = '9596a0f03838'
down_revision = 'fd5dc71471cc'


def upgrade() -> None:
    # Set the unique count to one for all report summaries which have no
    # unique reports but have _some_ reports.
    execute(update(st.ReportHistoryDaily)
            .where(and_(st.ReportHistoryDaily.unique == 0,
                        st.ReportHistoryDaily.count > 0))
            .values(unique=1))
    execute(update(st.ReportHistoryMonthly)
            .where(and_(st.ReportHistoryMonthly.unique == 0,
                        st.ReportHistoryMonthly.count > 0))
            .values(unique=1))
    execute(update(st.ReportHistoryWeekly)
            .where(and_(st.ReportHistoryWeekly.unique == 0,
                        st.ReportHistoryWeekly.count > 0))
            .values(unique=1))


def downgrade() -> None:
    # It does not make sense to reverse this migration.
    pass
