# Copyright (C) 2018  ABRT Team
# Copyright (C) 2018  Red Hat, Inc.
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


"""Do not connect associates to release but only to opsys (may take a while)

Revision ID: 9301a426f19d
Revises: acd3d9bf85d1
Create Date: 2018-03-16 14:04:57.590176

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '9301a426f19d'
down_revision = 'acd3d9bf85d1'


def upgrade():
    enum = postgresql.ENUM("watchbugzilla", "commit", name="_permission_type", create_type=False)
    enum.create(op.get_bind(), checkfirst=False)
    op.create_table('opsyscomponentsassociates',
                    sa.Column('opsyscomponent_id', sa.Integer(), nullable=False),
                    sa.Column('associatepeople_id', sa.Integer(), nullable=False),
                    sa.Column('permission', enum, nullable=False, server_default="commit"),
                    sa.PrimaryKeyConstraint('opsyscomponent_id',
                                            'associatepeople_id',
                                            'permission'),
                    sa.ForeignKeyConstraint(['opsyscomponent_id'], ['opsyscomponents.id'], ),
                    sa.ForeignKeyConstraint(['associatepeople_id'], ['associatepeople.id'], ),
                   )

    """
    The following code would convert current permissions.
    However it is biblically slow (the first query) and it seems like better idea
    to pull those data once again (since this may set up some old and obscure
    permission that are now not true.

    q = "select distinct components_id, associatepeople_id, permission from \
         opsysreleasescomponentsassociates, opsysreleasescomponents;"
    for orca in op.get_bind().execute(q).fetchall():
        q = "insert into opsyscomponentsassociates (opsyscomponent_id, \
             associatepeople_id, permission) values({0}, {1}, '{2}')".format(
            orca.components_id, orca.associatepeople_id, orca.permission)
        op.execute(q)
    """

    # deliberately do not remove OpSysReleaseComponentAssociate as there is
    # no way how to get those data back.


def downgrade():
    op.drop_table('opsyscomponentsassociates')
    postgresql.ENUM(name="_permission_type").drop(op.get_bind(), checkfirst=False)
