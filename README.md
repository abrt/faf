# ABRT Analytics (formerly FAF)

[![Build status](https://copr.fedorainfracloud.org/coprs/g/abrt/faf-devel/package/faf/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/g/abrt/faf-devel/package/faf/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/abrt/faf.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/abrt/faf/context:python)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/abrt/faf.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/abrt/faf/alerts/)

---

**ABRT Analytics collects reports from ABRT and aggregates them. Developer or DevOps admin can sort them using number of occurences and see all similar reports.**

ABRT Analytics collects thousands of reports a day serving needs of three different projects:

 * [CentOS](https://centos.org/)
 * [Fedora](https://getfedora.org/)
 * [Red Hat Enterprise Linux](https://www.redhat.com/en/technologies/linux-platforms/enterprise-linux)

Live ABRT Analytics instances:

[https://retrace.fedoraproject.org/faf](https://retrace.fedoraproject.org/faf)

### How it works

Currently, the typical crash reporting workflow consists of generating a
so-called [µReport](https://abrt.readthedocs.org/en/latest/ureport.html#ureport)
(micro-report) designed to be completely anonymous so it can be sent
and processed automatically avoiding costly Bugzilla queries and manpower.

ABRT Analytics in this scenario works like the first line of defense — collecting
massive amounts of similar reports and responding with tracker URLs
in case of known problems.

If a user is lucky enough to hit a unique issue not known by ABRT Analytics,
reporting chain continues with reporting to Bugzilla, more complex process
which requires user having a Bugzilla account and going through numerous steps
including verification that the report doesn't contain sensitive data.

You can read more about the technical aspects of ABRT at our documentation site:
[https://abrt.readthedocs.io/en/latest/](https://abrt.readthedocs.io/en/latest/).


### Features

 * Support for various programming languages and software projects:
   * C/C++
   * Java
   * Python
   * Python 3
   * Linux (kernel oops)
 * De-duplication of incoming reports
 * Clustering of similar reports (Problems)
 * Collection of various statistics about a platform
 * [Retracing](https://github.com/abrt/faf/wiki/Retracing) of C/C++ backtraces and kernel oopses
 * Simple knowledge base to provide instant responses to certain reports
 * Bug tracker support

### Developer resources

 * IRC: #abrt @ freenode
 * [Mailing list](https://lists.fedorahosted.org/mailman/listinfo/crash-catcher)
 * [Contribution guidelines](https://github.com/abrt/faf/blob/master/CONTRIBUTING.rst)
 * [Installation Guide](https://github.com/abrt/faf/wiki/Installation-Guide)
 * [ABRT Documentation](http://abrt.readthedocs.org)

### RPM Repositories

Nightly builds of ABRT Analytics can be obtained from these repositories:

 * Fedora, EPEL: https://copr.fedorainfracloud.org/coprs/g/abrt/faf-devel/

### Deploying the container image
#### Prerequisites

 * A PostgreSQL database with the
[semver extension](https://pgxn.org/dist/semver/doc/semver.html)
   * The abrt/faf-db image provides both
 * A volume for persistent storage
 * A Redis container for scheduling actions from the web UI

#### Running

```bash
podman volume create <volume_name>
podman pod create --publish=5432:5432 --publish=6379:6379 --publish=8080:8080 --name=<pod_name>

podman run \
    --pod=<pod_name> \
    --name=faf-db \
    --detach --interactive --tty \
    --volume=<volume_name>:/var/lib/pgsql/data \
    --env=POSTGRESQL_ADMIN_PASSWORD=scrt \
    abrt/faf-db

podman run \
    --pod=<pod_name> \
    --name=faf \
    --detach --interactive --tty \
    --env=PGHOST=localhost --env=PGUSER=faf --env=PGPASSWORD=scrt --env=PGPORT=5432 --env=PGDATABASE=faf \
    abrt/faf
```

If you are also running a Redis container for scheduling actions, you need to
set some additional environment variables:

```bash
podman run \
    --pod=<pod_name> \
    --name=faf \
    --detach --interactive --tty \
    --env=PGHOST=localhost --env=PGUSER=faf --env=PGPASSWORD=scrt --env=PGPORT=5432 --env=PGDATABASE=faf \
    --env=RDSBROKER=redis://faf-redis:6379/0 --env=RDSBACKEND=redis://faf-redis:6379/0
    abrt/faf
```

The Redis container can then be downloaded and run as follows:

```bash
podman pull redis:latest
podman run \
    --pod=<pod_name> \
    --name=faf-redis \
    --detach --interactive --tty \
    --hostname=faf-redis \
    redis
```

The running instance is now reachable on http://localhost:8080/faf/.

#### Client configuration

Sending reports from clients requires making changes to the configuration. Open
`/etc/libreport/plugins/ureport.conf` and set `URL` to point to your Analytics
instance:
```
URL = http://<container_IP>:8080/faf
```
