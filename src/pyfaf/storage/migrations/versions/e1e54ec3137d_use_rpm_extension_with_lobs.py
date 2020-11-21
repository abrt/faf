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
use rpm extension with lobs

Revision ID: e1e54ec3137d
Revises: bb2289ffb392
Create Date: 2020-11-19 14:40:36.484635
"""

import os

import sqlalchemy as sa
from alembic.op import get_bind

from pyfaf.storage.opsys import Package


# revision identifiers, used by Alembic.
revision = 'e1e54ec3137d'
down_revision = 'bb2289ffb392'

metadata = sa.MetaData()
package = sa.Table("packages", metadata,
                   sa.Column("id", sa.Integer),
                   sa.Column("build_id", sa.Integer),
                   sa.Column("pkgtype", sa.Enum("rpm", "deb", "tgz")))

def upgrade() -> None:
    for (pkgid, build, pkgtype) in get_bind().execute(
            sa.select(
                [package.c.id,
                 package.c.build_id,
                 package.c.pkgtype]
            )):
        db_package = Package()
        db_package.id = pkgid
        db_package.build_id = build
        db_package.pkgtype = pkgtype
        ext_len = len(pkgtype) + 1
        lobpath = db_package.get_lob_path("package")
        if lobpath.endswith(".{}".format(pkgtype)) and os.path.isfile(lobpath[:-ext_len]):
            os.rename(lobpath[:-ext_len], lobpath)


def downgrade() -> None:
    for (pkgid, build, pkgtype) in get_bind().execute(
            sa.select(
                [package.c.id,
                 package.c.build_id,
                 package.c.pkgtype]
            )):
        db_package = Package()
        db_package.id = pkgid
        db_package.build_id = build
        db_package.pkgtype = pkgtype
        ext_len = len(pkgtype) + 1
        lobpath = db_package.get_lob_path("package")
        if lobpath.endswith(".{}".format(pkgtype)) and os.path.isfile(lobpath):
            os.rename(lobpath, lobpath[:-ext_len])
