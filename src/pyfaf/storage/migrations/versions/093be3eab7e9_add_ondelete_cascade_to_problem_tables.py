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
Add ondelete cascade to problem tables

Revision ID: 093be3eab7e9
Revises: a2b6d12819f9
Create Date: 2019-03-21 11:49:05.615768
"""

from alembic.op import drop_constraint, create_foreign_key


# revision identifiers, used by Alembic.
revision = '093be3eab7e9'
down_revision = 'a2b6d12819f9'


def upgrade() -> None:
    drop_constraint('problemopsysreleases_problem_id_fkey', 'problemopsysreleases', type_='foreignkey')
    create_foreign_key('problemopsysreleases_problem_id_fkey', 'problemopsysreleases', 'problems',
                       ['problem_id'], ['id'], ondelete='CASCADE')

    drop_constraint('problemreassign_problem_id_fkey', 'problemreassign', type_='foreignkey')
    create_foreign_key('problemreassign_problem_id_fkey', 'problemreassign', 'problems',
                       ['problem_id'], ['id'], ondelete='CASCADE')

    drop_constraint('problemscomponents_problem_id_fkey', 'problemscomponents', type_='foreignkey')
    create_foreign_key('problemscomponents_problem_id_fkey', 'problemscomponents', 'problems',
                       ['problem_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    drop_constraint('problemscomponents_problem_id_fkey', 'problemscomponents', type_='foreignkey')
    create_foreign_key('problemscomponents_problem_id_fkey', 'problemscomponents', 'problems',
                       ['problem_id'], ['id'])

    drop_constraint('problemreassign_problem_id_fkey', 'problemreassign', type_='foreignkey')
    create_foreign_key('problemreassign_problem_id_fkey', 'problemreassign', 'problems',
                       ['problem_id'], ['id'])

    drop_constraint('problemopsysreleases_problem_id_fkey', 'problemopsysreleases', type_='foreignkey')
    create_foreign_key('problemopsysreleases_problem_id_fkey', 'problemopsysreleases', 'problems',
                       ['problem_id'], ['id'])
