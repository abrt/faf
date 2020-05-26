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
Add ondelete cascade to report bt tables

Revision ID: cb084388e232
Revises: 093be3eab7e9
Create Date: 2019-03-21 11:59:09.637677
"""

from alembic.op import drop_constraint, create_foreign_key


# revision identifiers, used by Alembic.
revision = 'cb084388e232'
down_revision = '093be3eab7e9'


def upgrade() -> None:
    drop_constraint('reportbacktraces_report_id_fkey', 'reportbacktraces', type_='foreignkey')
    create_foreign_key('reportbacktraces_report_id_fkey', 'reportbacktraces', 'reports',
                       ['report_id'], ['id'], ondelete='CASCADE')

    drop_constraint('reportbtkernelmodules_backtrace_id_fkey', 'reportbtkernelmodules', type_='foreignkey')
    create_foreign_key('reportbtkernelmodules_backtrace_id_fkey', 'reportbtkernelmodules', 'reportbacktraces',
                       ['backtrace_id'], ['id'], ondelete='CASCADE')

    drop_constraint('reportbttaintflags_backtrace_id_fkey', 'reportbttaintflags', type_='foreignkey')
    create_foreign_key('reportbttaintflags_backtrace_id_fkey', 'reportbttaintflags', 'reportbacktraces',
                       ['backtrace_id'], ['id'], ondelete='CASCADE')

    drop_constraint('reportbtframes_thread_id_fkey', 'reportbtframes', type_='foreignkey')
    create_foreign_key('reportbtframes_thread_id_fkey', 'reportbtframes', 'reportbtthreads',
                       ['thread_id'], ['id'], ondelete='CASCADE')

    drop_constraint('reportbthashes_backtrace_id_fkey', 'reportbthashes', type_='foreignkey')
    create_foreign_key('reportbthashes_backtrace_id_fkey', 'reportbthashes', 'reportbacktraces',
                       ['backtrace_id'], ['id'], ondelete='CASCADE')

    drop_constraint('reportbtthreads_backtrace_id_fkey', 'reportbtthreads', type_='foreignkey')
    create_foreign_key('reportbtthreads_backtrace_id_fkey', 'reportbtthreads', 'reportbacktraces',
                       ['backtrace_id'], ['id'], ondelete='CASCADE')

def downgrade() -> None:
    drop_constraint('reportbtthreads_backtrace_id_fkey', 'reportbtthreads', type_='foreignkey')
    create_foreign_key('reportbtthreads_backtrace_id_fkey', 'reportbtthreads', 'reportbacktraces',
                       ['backtrace_id'], ['id'])

    drop_constraint('reportbthashes_backtrace_id_fkey', 'reportbthashes', type_='foreignkey')
    create_foreign_key('reportbthashes_backtrace_id_fkey', 'reportbthashes', 'reportbacktraces',
                       ['backtrace_id'], ['id'])

    drop_constraint('reportbtframes_thread_id_fkey', 'reportbtframes', type_='foreignkey')
    create_foreign_key('reportbtframes_thread_id_fkey', 'reportbtframes', 'reportbtthreads',
                       ['thread_id'], ['id'])

    drop_constraint('reportbttaintflags_backtrace_id_fkey', 'reportbttaintflags', type_='foreignkey')
    create_foreign_key('reportbttaintflags_backtrace_id_fkey', 'reportbttaintflags', 'reportbacktraces',
                       ['backtrace_id'], ['id'])

    drop_constraint('reportbtkernelmodules_backtrace_id_fkey', 'reportbtkernelmodules', type_='foreignkey')
    create_foreign_key('reportbtkernelmodules_backtrace_id_fkey', 'reportbtkernelmodules', 'reportbacktraces',
                       ['backtrace_id'], ['id'])

    drop_constraint('reportbacktraces_report_id_fkey', 'reportbacktraces', type_='foreignkey')
    create_foreign_key('reportbacktraces_report_id_fkey', 'reportbacktraces', 'reports',
                       ['report_id'], ['id'])
