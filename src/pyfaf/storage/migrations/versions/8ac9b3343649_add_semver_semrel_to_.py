# Copyright (C) 2019  ABRT Team
# Copyright (C) 2019  Red Hat, Inc.
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
Add semver semrel to reportunknownpackages

Revision ID: 8ac9b3343649
Revises: cee07a513404
Create Date: 2019-06-20 15:16:12.340579
"""

import sqlalchemy as sa
from alembic.op import add_column, alter_column, drop_column, create_index, drop_index, get_bind

from pyfaf.storage import custom_types

# revision identifiers, used by Alembic.
revision = '8ac9b3343649'
down_revision = 'cee07a513404'

metadata = sa.MetaData()

def upgrade():
    add_column('reportunknownpackages', sa.Column('semver', custom_types.Semver(), nullable=True))
    add_column('reportunknownpackages', sa.Column('semrel', custom_types.Semver(), nullable=True))

    reportunknownpackage = sa.Table("reportunknownpackages", metadata,
                                    sa.Column("id", sa.Integer),
                                    sa.Column("report_id", sa.Integer),
                                    sa.Column("type", sa.Enum("CRASHED",
                                                              "RELATED",
                                                              "SELINUX_POLICY",
                                                              name="reportpackage_type")),
                                    sa.Column("name", sa.String(length=64)),
                                    sa.Column("epoch", sa.Integer),
                                    sa.Column("version", sa.String(length=64)),
                                    sa.Column("release", sa.String(length=64)),
                                    sa.Column("arch_id", sa.Integer),
                                    sa.Column("count", sa.Integer),
                                    sa.Column("semver", custom_types.Semver()),
                                    sa.Column("semrel", custom_types.Semver()))

    for (pkg_id, version, release) in get_bind().execute(
            sa.select(
                [reportunknownpackage.c.id,
                 reportunknownpackage.c.version,
                 reportunknownpackage.c.release]
            )):
        semver = custom_types.to_semver(version)
        semrel = custom_types.to_semver(release)
        get_bind().execute((reportunknownpackage.update() #pylint: disable=no-value-for-parameter
                            .where(reportunknownpackage.c.id == pkg_id)
                            .values(semver=sa.func.to_semver(semver),
                                    semrel=sa.func.to_semver(semrel))))

    alter_column('reportunknownpackages', sa.Column('semver',
                                                    custom_types.Semver(), nullable=False))
    alter_column('reportunknownpackages', sa.Column('semrel',
                                                    custom_types.Semver(), nullable=False))

    create_index('ix_reportunknownpackages_semver_semrel', 'reportunknownpackages',
                 ['semver', 'semrel'], unique=False)

    create_index('ix_builds_semver_semrel', 'builds',
                 ['semver', 'semrel'], unique=False)
    drop_index('ix_builds_semver', table_name='builds')
    drop_index('ix_builds_semrel', table_name='builds')


def downgrade():
    drop_index('ix_reportunknownpackages_semver_semrel', table_name='reportunknownpackages')
    drop_column('reportunknownpackages', 'semver')
    drop_column('reportunknownpackages', 'semrel')

    create_index('ix_builds_semver', 'builds', ['semver'])
    create_index('ix_builds_semrel', 'builds', ['semrel'])
    drop_index('ix_builds_semver_semrel', table_name='builds')
