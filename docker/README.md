# FAF in Docker container

**Easiest way how to run FAF**
---

## How to deploy

It is as simple as:

`docker run --name faf -dit abrt/faf-image`

However you also probably want to mount volumes to `/var/lib/postgres` and
to `/var/spool/faf` not to lose database and FAF's data.

`docker run --name faf -v /var/lib/faf-docker/faf:/var/spool/faf -v
/var/lib/faf-docker/postgres:/var/lib/postgres/ -dit abrt/faf-image`

If you run FAF for the first time, then there is no database. You have to
initialize it.

`docker exec faf init_db`

Then FAF is ready for use.

## What's next
You can see incoming reports in webUI. It is accessible on `http://<container_IP>/faf`.

Finding out container IP address:

`docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' faf`

Also to send reports into your own FAF, you have to set up libreport on all
machines, from with you wish to report into your own FAF. To do so, set up
`URL = http://<container_IP>/faf` in `/etc/libreport/plugins/ureport.conf`.

## Configuring FAF
New containers come with fully working and configured FAF (on top of basic configuration
Fedora releases are added, caching is disabled, and FAF accepts unknown components).

To run any FAF action, please run them as faf user.

`docker exec -u faf faf faf <action> <arguments>`

## How to build the image
`cd faf/docker`

`make build` to build from copr

`make build_local` to build from currently checked out github branch

For easier using and debugging you can use also:

`make run` to run copr version of FAF

`make run_local` to run git version of FAF

`make sh` to jump into bash in the container

`make del` to remove faf container
