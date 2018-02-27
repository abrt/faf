# FAF in Docker container

**Easiest way how to run FAF**
---

## How to deploy

Prerequisites:
A postgres database with semver extension is needed. Using abrt/postgres-semver
image is recommended.
`docker run -p 5432:5432 -v /var/tmp/data:/var/lib/pgsql/data -e POSTGRESQL_ADMIN_PASSWORD=scrt --name db -dit postgres-semver`

Running FAF is as simple as:

`docker run --name faf -dit -e PGHOST=$(DB_IP) -e PGUSER=faf -e PGPASSWORD=scrt -e PGPORT=5432 -e PGDATABASE=faf -p 8080:8080 faf-image`

However you also probably want to mount volumes to `/var/spool/faf` not to lose 
FAF's data.

`docker run --name faf -dit -v /var/lib/faf-docker/faf:/var/spool/faf -e PGHOST=$(DB_IP) -e PGUSER=faf -e PGPASSWORD=scrt -e PGPORT=5432 -e PGDATABASE=faf -p 8080:8080 faf-image`

Then FAF is ready for use.

## What's next
You can see incoming reports in webUI. It is accessible on `http://<container_IP>:8080/faf`.

Finding out container IP address:

`docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' faf`

Also to send reports into your own FAF, you have to set up libreport on all
machines, from with you wish to report into your own FAF. To do so, set up
`URL = http://<container_IP>:8080/faf` in `/etc/libreport/plugins/ureport.conf`.

## Configuring FAF
New containers come with fully working and configured FAF (on top of basic configuration
Fedora releases are added, caching is disabled, and FAF accepts unknown components).

To run any FAF action, please run them as faf user.

`docker exec faf faf <action> <arguments>`

## How to build the image
`cd faf/docker`

`make build` to build from copr

`make build_local` to build from currently checked out github branch

`make build_db` to build database

For easier using and debugging you can use also:

`make run` to run copr version of FAF

`make run_local` to run git version of FAF

`make sh` to jump into bash in the container

`make del` to remove faf container

'make run_db' to run database
