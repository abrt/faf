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


from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
import logging
import logging.config

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

try:
    logging.config.dictConfig({
        "version": 1,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "level": "NOTSET",
                "formatter": "generic",
            }
        },
        "formatters": {
            "generic": {
                "format": "%(levelname)-5.5s [%(name)s] %(message)s",
                "datefmt": "%H:%M:%S"
            }
        },
        "loggers": {
            "root": {
                "level": "WARN",
                "handlers": ["console", ],
                "qualname": ""
            },
            "sqlalchemy": {
                "level": "WARN",
                "handlers": [],
                "qualname": "sqlalchemy.engine"
            },
            "alembic": {
                "level": "INFO",
                "handlers": [],
                "qualname": "alembic"
            }

        }
    })
except Exception:
    # dictConfig is only available since Python 2.7
    pass

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
import pyfaf
target_metadata = pyfaf.storage.GenericTable.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata
        )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
