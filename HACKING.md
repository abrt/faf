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

    or installed by:

        $ ./autogen.sh sysdeps --install

    The dependency installer gets the data from [the rpm spec file](faf.spec.in)

2. Build from source

    When you have all dependencies installed you can now build a rpm package by these commands:

        $ ./autogen.sh
        $ ./configure
        $ make rpm

    Now in the `noarch` folder you can find a rpm package. You can install it by:

        $ rpm -Uvh noarch/faf-*.rpm

### Building in container
Prerequisite:

- Docker - see for example [this
guide](https://developer.fedoraproject.org/tools/docker/docker-installation.html)

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
It is advised to use persistent storage, which needs to be prepared the following way

    # mkdir /var/tmp/data
    # chown 26:26 /var/tmp/data
    # chcon -t svirt_sandbox_file_t /var/tmp/data

In most cases it is enough to use official FAF database image

    $ make run_db

If some changes were made in database, which cannot be solved with migration, a new database image
must be built.

    $ make build_db

Such build image can be run the same way

    $ make run_db

#### FAF itself
If local image was built with `make build` then the image should be run with

    $ make run_local

otherwise an official image can be run with

    $ make run

FAF should be available at ```http://localhost:8080/faf/```

### Reporting into FAF
1. Set a `URL` to your server in `/etc/libreport/plugins/ureport.conf`

```
URL = http://localhost:8080/faf
```

2. Create crash

- Make sure you have ABRT running and that you have auto-reporting enabled (`abrt-auto-reporting enabled`)
- Install package `will-crash` and then execute `will_abort`

This should be enough, so in a few minutes (reports are processed every few minutes) you should see
a spike in graph on your FAF. However there are few places where it can go wrong, therefore the following
troubleshooting might be required:



1. Was the problem caught by ABRT on your local machine?

    Check output of `abrt-cli ls`. If you dont see any problems there, ABRT is probably not running on your machine. Check https://abrt.readthedocs.io/en/latest/ for more information.

2. Was the problem sent to FAF?

    Check content of `/var/spool/faf/reports`. In there you should be able to find a file whose name consists of numbers and letters.

    _(If you are running FAF in container, you will need to check this from the inside of the container. You can switch to the container's bash by running $ make sh from docker directory.)_

    For example, you can execute `find /var/spool/faf/reports/` and output should look something like this

        /var/spool/faf/reports/
        /var/spool/faf/reports/saved
        /var/spool/faf/reports/saved/6ab72295-cc09-4e15-af52-e818f6920314
        /var/spool/faf/reports/archive
        /var/spool/faf/reports/incoming
        /var/spool/faf/reports/deferred

    If there is no such file, it means that the report was not sent automatically or it was sent to a wrong server.
    Go to the `/var/spool/abrt/cccp-...` directory on your local machine and execute `reporter-ureport -vvv`. From the output you should be able to see if it was successfully sent and to which server. After that you should be able to see a new file in `/var/spool/faf/reports/incoming`.

3. Was the problem automatically processed on the server?

    If you see the file in `/var/spool/faf/reports/incoming` it means the report was not processed. Just run `sudo -E -u faf faf save-reports`.

_Note: Instead of the first two steps you can just copy [this
file](https://mmarusak.fedorapeople.org/43335030-7423-43b2-b49b-992913f773ba) into
`var/spool/faf/reports/incoming`_

### Testing

Easiest way how to test everything (build, run tests, check lints) is to make rpm build (see,
        *2. Build from source in Building locally chapter*) or to make local image build.

For running only tests change to *tests* directory and execute

    unit2

If you want to run only specific test, you can do so by simply executing it, for example

    ./test_actions

For running only pylint, change to *src* directory and execute

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
