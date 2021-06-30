# ABRT Analytics

[![Build status](https://copr.fedorainfracloud.org/coprs/g/abrt/faf-el8-devel/package/faf/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/g/abrt/faf-el8-devel/package/faf/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/abrt/faf.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/abrt/faf/context:python)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/abrt/faf.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/abrt/faf/alerts/)

---

**ABRT Analytics collects reports from ABRT and aggregate them. Developer or DevOps admin can sort them using number of occurences and see all similar reports.**

ABRT Analytics collects thousands of reports a day serving needs of three different projects:

 * [CentOS](http://centos.org)
 * [Fedora](http://fedoraproject.org)
 * [Red Hat Enterprise Linux](http://www.redhat.com/en/technologies/linux-platforms/enterprise-linux)

Live ABRT Analytics instances:

[https://retrace.fedoraproject.org/faf](https://retrace.fedoraproject.org/faf)

ABRT Analytics is part of the [ABRT project](http://github.com/abrt)

ABRT Analytics was originally named FAF (Fedora Analysis Framework).

### How it works

Currently, the typical crash reporting workflow consists of generating so-called
[µReport](http://abrt.readthedocs.org/en/latest/ureport.html#ureport)
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
[http://abrt.readthedocs.org](http://abrt.readthedocs.org).

### Deploy in a container
The easiest way to deploy ABRT Analytics is in a container using podman images.
Learn how to use and build them in the [container specific README](https://github.com/abrt/faf/tree/master/container).


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

 * Sources: git clone https://github.com/abrt/faf.git
 * IRC: #abrt @ [irc.libera.chat](https://libera.chat/)
 * [Mailing list](https://lists.fedorahosted.org/mailman/listinfo/crash-catcher)
 * [Contribution guidelines](https://github.com/abrt/faf/blob/master/CONTRIBUTING.rst)
 * [Wiki](https://github.com/abrt/faf/wiki)
 * [Installation Guide](https://github.com/abrt/faf/wiki/Installation-Guide)
 * [Github repository](http://github.com/abrt/faf/)
 * [Issue tracker](http://github.com/abrt/faf/issues)
 * [ABRT Documentation](http://abrt.readthedocs.org)


### Technologies behind ABRT Analytics


 * ABRT stack - ([abrt](http://github.com/abrt/abrt/)
  [libreport](http://github.com/abrt/libreport/), [satyr](http://github.com/abrt/satyr/))
 * [Python](http://python.org)
 * [PostgreSQL](http://postgresql.org)
 * [SQLAlchemy](http://sqlalchemy.org)
 * [Alembic](http://alembic.readthedocs.org)
 * [Flask](http://flask.pocoo.org)
 * [Celery](http://www.celeryproject.org)


### RPM Repositories

Nightly builds of ABRT Analytics can be obtained from these repositories:

 * Fedora, EPEL: https://copr.fedorainfracloud.org/coprs/g/abrt/faf-el8-devel/
