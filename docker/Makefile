DB_IP=`docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' db`
DB_PASS="NotSoSecretPassword"

build:
	docker build -t faf-image -f Dockerfile ../

build_local:
	docker build -t faf-image-local -f Dockerfile_local ../

build_db:
	docker build -t postgres_w_semver -f Dockerfile_db ../

run:
	docker run --name faf -dit -e PGHOST=$(DB_IP) -e PGUSER=faf -e PGPASSWORD=scrt -e PGPORT=5432 -e PGDATABASE=faf faf-image

run_local:
	docker run --name faf -dit -e PGHOST=$(DB_IP) -e PGUSER=faf -e PGPASSWORD=scrt -e PGPORT=5432 -e PGDATABASE=faf faf-image-local

# When running as docker containers and need persistent storage, do this for the first time
# mkdir /var/tmp/data
# chown 26:26 /var/tmp/data
# chcon -t svirt_sandbox_file_t /var/tmp/data

run_db:
	docker run -p 5432:5432 -v /var/tmp/data:/var/lib/pgsql/data -e POSTGRESQL_ADMIN_PASSWORD=$(DB_PASS) --name db -dit postgres_w_semver

sh:
	docker exec -it faf bash

del:
	docker rm -f faf
