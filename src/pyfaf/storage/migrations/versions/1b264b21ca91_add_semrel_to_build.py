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


"""add semrel to build

Revision ID: 1b264b21ca91
Revises: 4ff13674a015
Create Date: 2015-03-02 14:59:34.502070

"""

# revision identifiers, used by Alembic.
revision = '1b264b21ca91'
down_revision = '4ff13674a015'

from alembic import op
import sqlalchemy as sa

from pyfaf.storage import custom_types

metadata = sa.MetaData()


def upgrade():
    op.add_column('builds', sa.Column('semrel', custom_types.Semver(),
                                      nullable=True))

    build = sa.Table("builds", metadata,
                     sa.Column("id", sa.Integer),
                     sa.Column("base_package_name", sa.String(length=64)),
                     sa.Column("projrelease_id", sa.Integer),
                     sa.Column("epoch", sa.Integer),
                     sa.Column("version", sa.String(length=64)),
                     sa.Column("release", sa.String(length=64)),
                     sa.Column("semver", custom_types.Semver()),
                     sa.Column("semrel", custom_types.Semver()),
                    )

    for b in op.get_bind().execute(sa.select([build.c.id, build.c.release])):
        bid, brel = b
        brel = custom_types.to_semver(brel)
        op.get_bind().execute((build.update()
                               .where(build.c.id == bid)
                               .values(semrel=sa.func.to_semver(brel))))

    op.alter_column('builds', sa.Column('semrel', custom_types.Semver(),
                                        nullable=False))

    op.create_index('ix_builds_semrel', 'builds', ['semrel'])


def downgrade():
    op.drop_column('builds', 'semrel')
