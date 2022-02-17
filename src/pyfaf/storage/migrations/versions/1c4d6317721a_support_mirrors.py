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
Support mirror urls in repositories

Revision ID: 1c4d6317721a
Revises: 183a15e52a4f
Create Date: 2016-11-22 10:41:15.866893
"""

from alembic.op import create_table, get_bind, drop_column, drop_table, execute, add_column
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1c4d6317721a"
down_revision = "183a15e52a4f"


def upgrade() -> None:
    create_table("urls",
                 sa.Column("id", sa.Integer(), nullable=False),
                 sa.Column("url", sa.String(length=256), nullable=False),
                 sa.PrimaryKeyConstraint("id"),
                )

    create_table("urlrepo",
                 sa.Column("url_id", sa.Integer(), nullable=False),
                 sa.Column("repo_id", sa.Integer(), nullable=False),
                 sa.ForeignKeyConstraint(["url_id"], ["urls.id"], ),
                 sa.ForeignKeyConstraint(["repo_id"], ["repo.id"], ),
                 sa.PrimaryKeyConstraint("url_id", "repo_id"),
                )

    url_id = 1
    for repo in get_bind().execute("select * from repo").fetchall():
        execute("insert into urls (url) values('{0}')".format(repo.url))
        execute("insert into urlrepo values({0}, {1})".format(url_id, repo.id))
        url_id += 1
    drop_column("repo", "url")


def downgrade() -> None:
    add_column("repo", sa.Column("url", sa.String(length=256)))

    for repo in get_bind().execute("select * from repo").fetchall():
        urls = get_bind().execute("select * from urlrepo r, urls u where r.repo_id = {0} and\
                r.url_id = u.id".format(repo.id)).fetchall()
        if not urls:
            print("Repository {0} does not have any url assigned.".format(repo.name))
            continue
        execute("update repo set url = '{0}' where id = {1}".format(urls[0].url, repo.id))
        for url in urls[1:]:
            print("Skipping url {0} for repository {1}".format(url.url, repo.name))

    drop_table("urlrepo")
    drop_table("urls")
