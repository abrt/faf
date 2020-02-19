POD_NAME = faf-pod
VOLUME_NAME = faf-db-volume
DB_PASS="NotSoSecretPassword"

build:
	podman build -t faf-image -f Dockerfile ../
	podman tag faf-image abrt/faf-image

build_local:
	podman build -t faf-image-local -f Dockerfile_local ../

build_db:
	podman build -t postgres-semver -f Dockerfile_db ../
	podman tag postgres-semver abrt/postgres-semver

run:
	podman run --pod $(POD_NAME) --name faf -dit -e PGHOST=localhost -e PGUSER=faf -e PGPASSWORD=scrt -e PGPORT=5432 -e PGDATABASE=faf -e RDSBROKER=redis://faf-redis:6379/0 -e RDSBACKEND=redis://faf-redis:6379/0 abrt/faf-image

run_local:
	podman run --pod $(POD_NAME) --name faf -dit -e PGHOST=localhost -e PGUSER=faf -e PGPASSWORD=scrt -e PGPORT=5432 -e PGDATABASE=faf -e RDSBROKER=redis://faf-redis:6379/0 -e RDSBACKEND=redis://faf-redis:6379/0 faf-image-local

run_db:
	podman volume create $(VOLUME_NAME) 2>/dev/null ||:
	podman pod create -p 5432:5432 -p 6379:6379 -p 8080:8080 --name $(POD_NAME)
	podman run --pod $(POD_NAME) -v $(VOLUME_NAME):/var/lib/pgsql/data -e POSTGRESQL_ADMIN_PASSWORD=$(DB_PASS) --name db -dit abrt/postgres-semver
	sleep 5
	podman exec db sh -c "psql -c \"SELECT 1 FROM pg_roles WHERE rolname='faf'\" | grep -q 1 || yes scrt | createuser -Ps faf"

run_redis:
	podman run --pod $(POD_NAME) --name faf-redis --hostname faf-redis -dit redis
	
sh:
	podman exec -it faf bash

sh_db:
	podman exec -it db bash

del:
	-podman rm -f faf

del_db:
	-podman rm -f db
	-podman pod rm $(POD_NAME)
	@echo Notice: You might also want to remove the DB volume by running \"podman volume rm $(VOLUME_NAME)\" >&2

del_redis:
	-podman rm -f faf-redis

run_all_local: run_db run_local run_redis

run_all: run_db run run_redis

del_all: del_redis del del_db
