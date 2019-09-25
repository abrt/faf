DB_IP=`docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' db`
DB_PASS="NotSoSecretPassword"

build:
	docker build -t faf-image -f Dockerfile ../
	docker tag faf-image abrt/faf-image

build_local:
	docker build -t faf-image-local -f Dockerfile_local ../

build_db:
	docker build -t postgres-semver -f Dockerfile_db ../
	docker tag postgres-semver abrt/postgres-semver

run:
	docker run --name faf -dit -e PGHOST=$(DB_IP) -e PGUSER=faf -e PGPASSWORD=scrt -e PGPORT=5432 -e PGDATABASE=faf -e RDSBROKER=redis://faf-redis:6379/0 -e RDSBACKEND=redis://faf-redis:6379/0 -p 8080:8080 abrt/faf-image

run_local:
	docker run --name faf -dit -e PGHOST=$(DB_IP) -e PGUSER=faf -e PGPASSWORD=scrt -e PGPORT=5432 -e PGDATABASE=faf -e RDSBROKER=redis://faf-redis:6379/0 -e RDSBACKEND=redis://faf-redis:6379/0 -p 8080:8080 faf-image-local

# When running as docker containers and need persistent storage, do this for the first time
# mkdir /var/tmp/data
# chown 26:26 /var/tmp/data
# chcon -t svirt_sandbox_file_t /var/tmp/data

run_db:
	docker run -p 5432:5432 -v /var/tmp/data:/var/lib/pgsql/data -e POSTGRESQL_ADMIN_PASSWORD=$(DB_PASS) --name db -dit abrt/postgres-semver
	sleep 5
	docker exec db sh -c "psql -c \"SELECT 1 FROM pg_roles WHERE rolname='faf'\" | grep -q 1 || yes scrt | createuser -Ps faf"

sh:
	docker exec -it faf bash

del:
	docker rm -f faf
