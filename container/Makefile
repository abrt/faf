DB_IMAGE=quay.io/abrt/faf-db
LOCAL_IMAGE=abrt/faf-local
IMAGE=quay.io/abrt/faf

CONTAINER=faf
DB_CONTAINER=$(CONTAINER)-db
REDIS_CONTAINER=$(CONTAINER)-redis

POD = faf-pod

VOLUME = faf-db

DB_PASS="NotSoSecretPassword"
ENVIRONMENT = \
	"-e PGHOST=$(POD)" \
	"-e PGUSER=faf" \
	"-e PGPASSWORD=scrt" \
	"-e PGPORT=5432" \
	"-e PGDATABASE=faf" \
	"-e RDSBROKER=redis://$(POD):6379/0" \
	"-e RDSBACKEND=redis://$(POD):6379/0"

build: Dockerfile
	podman build --file=$< --tag=$(IMAGE) ../

build_local: Dockerfile_local
	podman build --file=$< --tag=$(LOCAL_IMAGE) ../

build_db: Dockerfile_db
	podman build --file=$< --tag=$(DB_IMAGE) ../

.PHONY: pod db_volume
pod:
	podman pod create --publish=5432:5432/tcp --publish=6379:6379/tcp --publish=8080:8080/tcp --name=$(POD) || :

db_volume:
	podman volume create $(VOLUME) 2>/dev/null ||:

run: pod
	podman run --detach --interactive --pod=$(POD) --name=$(CONTAINER) --tty $(ENVIRONMENT) $(IMAGE)

run_local: pod
	podman run --detach --interactive --pod=$(POD) --name=$(CONTAINER) --tty $(ENVIRONMENT) $(LOCAL_IMAGE)

run_db: db_volume pod
	podman run --pod=$(POD) -v $(VOLUME):/var/lib/pgsql/data -e POSTGRESQL_ADMIN_PASSWORD=$(DB_PASS) --name=$(DB_CONTAINER) -dit $(DB_IMAGE)
	sleep 5
	podman exec $(DB_CONTAINER) sh -c "psql -c \"SELECT 1 FROM pg_roles WHERE rolname='faf'\" | grep -q 1 || yes scrt | createuser -Ps faf"

run_redis: pod
	podman run --pod=$(POD) --name=$(REDIS_CONTAINER) -dit redis
	
sh:
	podman exec -it $(CONTAINER) /bin/bash

sh_db:
	podman exec -it $(DB_CONTAINER) /bin/bash

del:
	-podman rm -f $(CONTAINER)

del_db:
	-podman rm -f $(DB_CONTAINER)
	-podman pod rm $(POD)
	@echo Notice: You might also want to remove the DB volume by running \"podman volume rm $(VOLUME)\" >&2

del_redis:
	-podman rm -f $(REDIS_CONTAINER)

run_all_local: run_db run_local run_redis

run_all: run_db run run_redis

del_all: del_redis del del_db
