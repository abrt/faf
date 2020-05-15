# Building images

This directory (`container`) is assumed to be the build context directory.

Production images are built from the `build` target:

    make build

Slightly faster builds for development can be achieved with the `build_local` target:

    make build_local

Database images are built from the `build_db` target:

    make build_db

# Running containers

Production containers can be started with the `run` target:

    make run

Development containers can be started with the `run_local` target:

    make run_local

Database containers can be started with the `run_db` target:

    make run_db

Redis containers can be started with the `run_redis` target:

    make run_redis

All of the above can be done at once with:

 * the `run_all` target:

        make run_all

 * the `run_all_local` target:

        make run_all_local


Shell access for the main and database containers can be achieved with the `sh`
and `sh_db` targets, respectively:

    make sh
    make sh_db

# Removing containers

Containers can be removed with:
 * the `del` target for the main container:

        make del

 * the `del_db` target for the database container:

        make del_db

 * the `del_redis` target for the Redis container:

        make del_redis

 * the `del_all` target for everything at once:

        make del_all
