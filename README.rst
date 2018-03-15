About FAF
=========

Originated as Fedora Analysis Framework –
The ultimate tool to fix problems of application crashes.

FAF now collects thousands of reports a day
serving needs of three different projects:

- `CentOS <http://centos.org>`_
- `Fedora <http://fedoraproject.org>`_
- `Red Hat Enterprise Linux <http://www.redhat.com/en/technologies/linux-platforms/enterprise-linux>`_

Live FAF instances:

- https://retrace.fedoraproject.org/faf/

FAF is part of the `ABRT project <http://github.com/abrt/>`_.

How it works
------------

Currently, typical crash reporting work-flow consists of generating so called
`ureport <http://abrt.readthedocs.org/en/latest/ureport.html#ureport>`_
(micro report) designed to be completely anonymous so it can be sent
and processed automatically avoiding costly bugzilla queries and manpower.

FAF in this scenario works like a first line of defense — collecting
massive amounts of similar reports and responding with tracker URLs
in case of known problems.

If user is lucky enough to hit a unique issue not known by FAF,
reporting chain continues with reporting to bugzilla, more complex process
which requires user having a bugzilla account and going through numerous steps
including verification that the report doesn't contain sensitive data.

You can read more about technical aspects of ABRT at our documentation site:
http://abrt.readthedocs.org.


Features
________

- Support for various programming languages and software projects:

  - C/C++
  - Java
  - Python
  - Python 3
  - Linux (kernel oops)
- De-duplication of incoming reports
- Clustering of similar reports (Problems)
- Collection of various statistics about platform
- `Retracing <https://github.com/abrt/faf/wiki/Retracing>`_ of C/C++ backtraces and kernel oopses
- Simple knowledge base to provide instant responses to certain reports
- Bug tracker support

Developer resources
-------------------

- Sources: git clone https://github.com/abrt/faf.git
- IRC: #abrt @ freenode
- `Mailing list <https://lists.fedorahosted.org/mailman/listinfo/crash-catcher>`_
- `Contribution guidelines <https://github.com/abrt/faf/blob/master/CONTRIBUTING.rst>`_
- `Wiki <https://github.com/abrt/faf/wiki>`_
- `Installation Guide <https://github.com/abrt/faf/wiki/Installation-Guide>`_
- `Github repository <http://github.com/abrt/faf/>`_
- `Issue tracker <http://github.com/abrt/faf/issues>`_
- `ABRT Documentation <http://abrt.readthedocs.org>`_


Technologies behind FAF
_______________________


- ABRT stack (`abrt <http://github.com/abrt/abrt/>`_,
  `libreport <http://github.com/abrt/libreport/>`_, `satyr <http://github.com/abrt/satyr/>`_)
- `Python <http://python.org>`_
- `PostgreSQL <http://postgresql.org>`_
- `SQLAlchemy <http://sqlalchemy.org>`_
- `Alembic <http://alembic.readthedocs.org>`_
- `Flask <http://flask.pocoo.org>`_
- `Celery <http://www.celeryproject.org/>`_


RPM Repositories
________________

Nightly builds of FAF can be obtained from these repositories:

- Fedora: https://repos.fedorapeople.org/repos/abrt/abrt/fedora-abrt.repo
- EPEL: https://repos.fedorapeople.org/repos/abrt/abrt/epel-abrt.repo
