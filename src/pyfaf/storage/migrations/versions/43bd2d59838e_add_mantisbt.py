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


"""add mantisbt

Revision ID: 43bd2d59838e
Revises: 2dfd5aef57ca
Create Date: 2015-04-01 10:06:03.059696

"""

# revision identifiers, used by Alembic.
revision = '43bd2d59838e'
down_revision = '2dfd5aef57ca'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('mantisbugs',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('summary', sa.String(length=256), nullable=False),
                    sa.Column('status', sa.Enum('NEW', 'ASSIGNED', 'MODIFIED', 'ON_QA', 'VERIFIED', 'RELEASE_PENDING',
                                                'ON_DEV', 'POST', 'CLOSED', name='mantisbug_status'), nullable=False),
                    sa.Column('resolution', sa.Enum('NOTABUG', 'WONTFIX', 'WORKSFORME', 'DEFERRED', 'CURRENTRELEASE',
                                                    'RAWHIDE', 'ERRATA', 'DUPLICATE', 'UPSTREAM', 'NEXTRELEASE',
                                                    'CANTFIX', 'INSUFFICIENT_DATA', name='mantisbug_resolution'),
                              nullable=True),
                    sa.Column('duplicate_id', sa.Integer(), nullable=True),
                    sa.Column('creation_time', sa.DateTime(), nullable=False),
                    sa.Column('last_change_time', sa.DateTime(), nullable=False),
                    sa.Column('external_id', sa.Integer(), nullable=False),
                    sa.Column('tracker_id', sa.Integer(), nullable=False),
                    sa.Column('opsysrelease_id', sa.Integer(), nullable=False),
                    sa.Column('component_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['component_id'], ['opsyscomponents.id'], ),
                    sa.ForeignKeyConstraint(['duplicate_id'], ['mantisbugs.id'], ),
                    sa.ForeignKeyConstraint(['opsysrelease_id'], ['opsysreleases.id'], ),
                    sa.ForeignKeyConstraint(['tracker_id'], ['bugtrackers.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('external_id', 'tracker_id')
                   )
    op.create_index(op.f('ix_mantisbugs_component_id'), 'mantisbugs', ['component_id'], unique=False)
    op.create_index(op.f('ix_mantisbugs_duplicate_id'), 'mantisbugs', ['duplicate_id'], unique=False)
    op.create_index(op.f('ix_mantisbugs_opsysrelease_id'), 'mantisbugs', ['opsysrelease_id'], unique=False)
    op.create_table('reportmantis',
                    sa.Column('report_id', sa.Integer(), nullable=False),
                    sa.Column('mantisbug_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['mantisbug_id'], ['mantisbugs.id'], ),
                    sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
                    sa.PrimaryKeyConstraint('report_id', 'mantisbug_id'),
                   )


def downgrade():
    op.drop_table('reportmantis')
    op.drop_index(op.f('ix_mantisbugs_opsysrelease_id'), table_name='mantisbugs')
    op.drop_index(op.f('ix_mantisbugs_duplicate_id'), table_name='mantisbugs')
    op.drop_index(op.f('ix_mantisbugs_component_id'), table_name='mantisbugs')
    op.drop_table('mantisbugs')
