build:
	docker build -t faf-image -f Dockerfile ../

build_local:
	docker build -t faf-image-local -f Dockerfile_local ../

run:
	docker run --name faf -dit faf-image

run_local:
	docker run --name faf -dit faf-image-local

init_db:
	docker exec faf init_db

sh:
	docker exec -it faf bash

del:
	docker rm -f faf
