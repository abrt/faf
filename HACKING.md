# Hacking on FAF

Here's where to get the code:

    $ git clone https://github.com/abrt/faf.git
    $ cd faf/

The remainder of the commands assume you're in the top level of the
FAF git repository checkout.

## Building
It is possible to either build and run FAF [locally](HACKING.md#building-locally) or in
[container](HACKING.md#building-in-container).

### Building locally
1. Install dependencies

    First you should install all dependent packages.

    Dependencies can be listed by:

        $ ./autogen.sh sysdeps

    or installed by (two versions based on your package manager):

        $ ./autogen.sh sysdeps --install-yum
        $ ./autogen.sh sysdeps --install-dnf

    The dependency installer gets the data from [the rpm spec file](faf.spec.in)

2. Build from source

    When you have all dependencies installed you can now build a rpm package by these commands:

        $ ./autogen.sh
        $ ./configure
        $ make rpm

    Now in the `noarch` folder you can find a rpm package. You can install it by:

        $ rpm -Uvh noarch/faf-*.rpm

### Building in container
1. Change to docker directory

        $ cd docker

2. Build the image

        $ make build_local

## Running
### Running locally built server
1. Set up database

    FAF requires a working relational database such as PostgreSQL. If not already done, [set up a database for FAF](https://github.com/abrt/faf/wiki/Set-Up-a-Database-for-FAF) and install the appropriate python connector package (e.g. python-psycopg2).

2. Initialize FAF

        $ sudo -u faf faf-migrate-db --create-all
        $ sudo -u faf faf-migrate-db --stamp-only
        $ sudo -u faf faf init

3. Restart apache service

        $ sudo service httpd restart

FAF should be available at ```http://localhost/faf/```

### Running container images
Prerequisites:

1. Docker, see for example [this
guide](https://developer.fedoraproject.org/tools/docker/docker-installation.html)

2. All following commands assume you are in docker directory

#### Database
It is adviced to use persistant storage, which needs to be prepared the following way

    # mkdir /var/tmp/data
    # chown 26:26 /var/tmp/data
    # chcon -t svirt_sandbox_file_t /var/tmp/data

In most cases it is enough to use offical FAF database image

    $ make run_db

If some changes were made in database, which cannot be solved with migration a new database image
must be build

    $ make build_db

Such build image can be run the same way

    $ make run_db

#### FAF itself
If local image was build with `make build` then the image should be run with

    $ make run_local

otherwise an offical image can be run with

    $ make run

FAF should be available at ```http://localhost:8080/faf/```

### Testing

Easiest way how to test everything (build, run tests, check lints) is to make rpm build (see,
        *2. Build from source in Building locally chapter*) or to make local image build.

For running only tests change to *tests* directory and execute

    unit2

If you want to run only specific test, you can do so by simply executing it, for example

    ./test_actions

For runing only pylint, change to *src* directory and execute

    pylint-3 --rcfile=../pylintrc $(find ./ -name *.py) webfaf/hub.wsgi bin/faf-migrate-db bin/faf


## Contributing a change

### Basic git workflow:

1. Fork the FAF repository (hit fork button on https://github.com/abrt/faf)

2. Clone your fork

3. Checkout to a new branch in your clone (`git checkout -b <name_of_branch>`)

4. ... make changes...

5. Test your changes

6. Create tests for the given changes

7. Add edited files (`git add <file_name>`)

8. Create commit (`git commit`) [How to write a proper git commit
   message](https://chris.beams.io/posts/git-commit/)

9. Push your branch (`git push -u origin <name_of_branch>`)

10. Go to https://github.com/abrt/faf and click `Create pull request`

11. Create the PR

12. Wait for review
