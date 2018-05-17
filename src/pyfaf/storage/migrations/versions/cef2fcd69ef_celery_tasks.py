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


"""Celery tasks

Revision ID: cef2fcd69ef
Revises: 48550f308625
Create Date: 2015-06-01 12:22:13.499460

"""

# revision identifiers, used by Alembic.
revision = 'cef2fcd69ef'
down_revision = '48550f308625'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('periodictasks',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=100), nullable=False),
                    sa.Column('task', sa.String(length=100), nullable=False),
                    sa.Column('enabled', sa.Boolean(), nullable=False),
                    sa.Column('crontab_minute', sa.String(length=20), nullable=False),
                    sa.Column('crontab_hour', sa.String(length=20), nullable=False),
                    sa.Column('crontab_day_of_week', sa.String(length=20), nullable=False),
                    sa.Column('crontab_day_of_month', sa.String(length=20), nullable=False),
                    sa.Column('crontab_month_of_year', sa.String(length=20), nullable=False),
                    sa.Column('last_run_at', sa.DateTime(), nullable=True),
                    sa.Column('args', sa.Text(), nullable=False),
                    sa.Column('kwargs', sa.Text(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                   )
    op.create_table('taskresult',
                    sa.Column('id', sa.String(length=50), nullable=False),
                    sa.Column('task', sa.String(length=100), nullable=False),
                    sa.Column('finished_time', sa.DateTime(), nullable=True),
                    sa.Column('state', sa.String(length=20), nullable=False),
                    sa.Column('retval', sa.Text(), nullable=False),
                    sa.Column('args', sa.Text(), nullable=False),
                    sa.Column('kwargs', sa.Text(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                   )


def downgrade():
    op.drop_table('taskresult')
    op.drop_table('periodictasks')
