Name: faf
Version: 2.5.0
Release: 1%{?dist}
Summary: Software Problem Analysis Tool
License: GPLv3+
URL: https://github.com/abrt/faf/
Source0: https://github.com/abrt/%{name}/archive/%{version}/%{name}-%{version}.tar.gz

BuildArch: noarch

%global satyr_dep python3-satyr >= 0.26

Requires(pre): shadow-utils

Requires: cpio

Requires: postgresql

Requires: python3
Requires: python3-setuptools
Requires: python3-psycopg2
Requires: python3-sqlalchemy
Requires: python3-rpm
Requires: python3-argcomplete
Requires: python3-cachelib

BuildRequires: autoconf
BuildRequires: intltool
BuildRequires: libtool

# requirements for tests
BuildRequires: pg-semver
BuildRequires: postgresql
BuildRequires: postgresql-server
BuildRequires: %{satyr_dep}
BuildRequires: createrepo_c
BuildRequires: python3
BuildRequires: python3-devel
BuildRequires: python3-alembic
BuildRequires: python3-setuptools
BuildRequires: python3-bugzilla >= 2.0
BuildRequires: python3-psycopg2
BuildRequires: python3-testing.postgresql >= 1.3.0
BuildRequires: python3-rpm
BuildRequires: python3-sqlalchemy
BuildRequires: python3-koji
BuildRequires: python3-zeep
BuildRequires: python3-fedora-messaging
BuildRequires: python3-celery >= 3.1
BuildRequires: python3-dnf
BuildRequires: python3-zeep
BuildRequires: python3-argcomplete

# webui
BuildRequires: python3-cachelib
BuildRequires: python3-dateutil
BuildRequires: python3-flask
BuildRequires: python3-flask-openid
BuildRequires: python3-flask-sqlalchemy
BuildRequires: python3-flask-wtf
BuildRequires: python3-jinja2
BuildRequires: python3-markdown2
BuildRequires: python3-munch
BuildRequires: python3-openid-teams
BuildRequires: python3-ratelimitingfilter
BuildRequires: python3-werkzeug

BuildRequires: xstatic-patternfly-common
BuildRequires: js-jquery

%description
faf is a programmable tool for analysis of packages, packaging
issues, bug reports and other artifacts produced during software
development.

%package webui
Summary: %{name}'s WebUI rewrite
Requires: %{name} = %{version}
Requires: httpd
Requires: python3-mod_wsgi
Requires: python3-flask
Requires: python3-flask-wtf
Requires: python3-flask-sqlalchemy
Requires: python3-flask-openid
Requires: python3-openid-teams
Requires: python3-jinja2
Requires: python3-markdown2
Requires: python3-munch
Requires: python3-dateutil
Requires: python3-ratelimitingfilter

Requires: xstatic-patternfly-common
Requires: js-jquery

%description webui
A WebUI rewrite

%package problem-coredump
Summary: %{name}'s coredump plugin
Requires: %{name} = %{version}
Requires: %{satyr_dep}

%description problem-coredump
A plugin for %{name} handling user-space binary crashes.

%package problem-java
Summary: %{name}'s java plugin
Requires: %{name} = %{version}
Requires: %{satyr_dep}

%description problem-java
A plugin for %{name} handling java problems.

%package problem-kerneloops
Summary: %{name}'s kerneloops plugin
Requires: %{name} = %{version}
Requires: %{satyr_dep}

%description problem-kerneloops
A plugin for %{name} handling kernel oopses.

%package problem-python
Summary: %{name}'s python plugin
Requires: %{name} = %{version}
Requires: %{satyr_dep}

%description problem-python
A plugin for %{name} handling python scripts problems.

%package problem-ruby
Summary: %{name}'s ruby plugin
Requires: %{name} = %{version}
Requires: %{satyr_dep}

%description problem-ruby
A plugin for %{name} handling ruby scripts problems.

%package dnf
Summary: %{name}'s dnf plugin
Requires: %{name} = %{version}
Requires: python3-dnf
Obsoletes: %{name}-yum < 1.3.5

%description dnf
A plugin for %{name} implementing unified access to dnf repositories.

%package opsys-centos
Summary: %{name}'s CentOS operating system plugin
Requires: %{name} = %{version}
Requires: %{name}-dnf = %{version}

%description opsys-centos
A plugin for %{name} implementing support for CentOS operating system.

%package opsys-fedora
Summary: %{name}'s Fedora operating system plugin
Requires: %{name} = %{version}
Requires: koji
Requires: python3-koji

%description opsys-fedora
A plugin for %{name} implementing support for Fedora operating system.

%package schema
Summary: A plugin implementing fedora-messaging Message schema of %{name}.
Requires: python3-fedora-messaging

%description schema
A plugin implementing fedora-messaging Message schema of %{name}.

%package action-sar
Summary: %{name}'s sar plugin
Requires: %{name} = %{version}

%description action-sar
A plugin for %{name} implementing Subject Access Request (SAR) action

%package action-save-reports
Summary: %{name}'s save-reports plugin
Requires: %{name} = %{version}

%description action-save-reports
A plugin for %{name} implementing save-reports action

%package action-archive-reports
Summary: %{name}'s archive-reports plugin
Requires: %{name} = %{version}
Requires: tar
Requires: xz

%description action-archive-reports
A plugin for %{name} implementing archive-reports action

%package action-create-problems
Summary: %{name}'s create-problems plugin
Requires: %{name} = %{version}
Requires: %{satyr_dep}

%description action-create-problems
A plugin for %{name} implementing create-problems action

%package action-shell
Summary: %{name}'s shell plugin
Requires: %{name} = %{version}
Requires: python3-ipython-console

%description action-shell
A plugin for %{name} allowing to run IPython shell

%package action-pull-releases
Summary: %{name}'s pull-releases plugin
Requires: %{name} = %{version}

%description action-pull-releases
A plugin for %{name} implementing pull-releases action

%package action-pull-reports
Summary: %{name}'s pull-reports plugin
Requires: %{name} = %{version}

%description action-pull-reports
A plugin for %{name} implementing pull-reports action

%package action-pull-components
Summary: %{name}'s pull-components plugin
Requires: %{name} = %{version}

%description action-pull-components
A plugin for %{name} implementing pull-components action

%package action-pull-associates
Summary: %{name}'s pull-associates plugin
Requires: %{name} = %{version}

%description action-pull-associates
A plugin for %{name} implementing pull-associates action

%package action-find-components
Summary: %{name}'s find-components plugin
Requires: %{name} = %{version}

%description action-find-components
A plugin for %{name} implementing find-components action

%package action-assign-release-to-builds
Summary: %{name}'s assign-release-to-builds plugin
Requires: %{name} = %{version}

%description action-assign-release-to-builds
A plugin for %{name} implementing assign-release-to-builds action

%package action-find-crash-function
Summary: %{name}'s find-crash-function plugin
Requires: %{name} = %{version}

%description action-find-crash-function
A plugin for %{name} implementing find-crash-function action

%package action-find-report-solution
Summary: %{name}'s find-report-solution action
Requires: %{name} = %{version}

%description action-find-report-solution
A plugin for %{name} implementing find-report-solution action

%package action-repo
Summary: %{name}'s repo plugin
Requires: %{name} = %{version}

%description action-repo
A plugin for %{name} implementing repoadd, repolist and reposync actions

%package action-retrace
Summary: %{name}'s retrace plugin
Requires: %{name} = %{version}
Requires: binutils
Requires: elfutils >= 0.155

%description action-retrace
A plugin for %{name} implementing retrace action

%package action-arch
Summary: %{name}'s arch plugin
Requires: %{name} = %{version}

%description action-arch
A plugin for %{name} implementing archadd action

%package action-sf-prefilter
Summary: %{name}'s action-sf-prefilter plugin
Requires: %{name} = %{version}
Requires: %{name}-solutionfinder-prefilter
Obsoletes: %{name}-action-kb < 0.12
Provides: %{name}-action-kb = 0.12

%description action-sf-prefilter
A plugin for %{name} implementing Solution finder Prefilter actions

%package action-c2p
Summary: %{name}'s coredump to packages plugin
Requires: %{name} = %{version}

%description action-c2p
A plugin for %{name} implementing c2p (coredump to packages) action

%package action-bugtracker
Summary: %{name}'s plugins for bugtracker administration
Requires: %{name} = %{version}
Requires: %{name}-bugtracker-bugzilla = %{version}

%description action-bugtracker
A plugin for bugtracker management

%package action-external-faf
Summary: %{name}'s external-faf plugin
Requires: %{name} = %{version}

%description action-external-faf
A plugin for %{name} implementing extfaf* actions

%package action-external-faf-clone-bz
Summary: %{name}'s external-faf-clone-bz plugin
Requires: %{name} = %{version}
Requires: %{name}-action-external-faf = %{version}

%description action-external-faf-clone-bz
A plugin for %{name} implementing extfafclonebz action

%package action-add-compat-hashes
Summary: %{name}'s add-compat-hashes plugin
Requires: %{name} = %{version}

%description action-add-compat-hashes
A plugin for %{name} implementing addcompathashes action

%package action-mark-probably-fixed
Summary: %{name}'s mark-probably-fixed plugin
Requires: %{name} = %{version}

%description action-mark-probably-fixed
A plugin for %{name} implementing mark-probably-fixed action

%package action-stats
Summary: %{name}'s stats plugin
Requires: %{name} = %{version}

%description action-stats
A plugin for %{name} implementing statistics generation

%package action-retrace-remote
Summary: %{name}'s retrace-remote plugin
Requires: %{name} = %{version}
Requires: python3-requests

%description action-retrace-remote
A plugin for %{name} implementing remote retracing

%package action-attach-centos-bugs
Summary: %{name}'s attach-centos-bugs plugin
Requires: %{name} = %{version}
Requires: %{name}-bugtracker-centos-mantis = %{version}

%description action-attach-centos-bugs
A plugin for %{name} implementing attaching of bugs from CentOS Mantis bugtracker

%package action-fedmsg-notify
Summary: %{name}'s fedmsg-notify plugin
Requires: %{name} = %{version}
Requires: %{name}-fedmsg = %{version}

%description action-fedmsg-notify
A plugin for %{name} implementing notification into Fedora Messaging

%package action-cleanup-packages
Summary: %{name}'s cleanup-packages plugin
Requires: %{name} = %{version}

%description action-cleanup-packages
A plugin for %{name} implementing cleanup of old packages.

%package action-delete-invalid-ureports
Summary: %{name}'s delete-invalid-ureports plugin
Requires: %{name} = %{version}

%description action-delete-invalid-ureports
A plugin for %{name} implementing delete of old invalid ureports.

%package action-cleanup-task-results
Summary: %{name}'s cleanup-task-results plugin
Requires: %{name} = %{version}

%description action-cleanup-task-results
A plugin for %{name} implementing cleanup of old task results.

%package action-cleanup-unassigned
Summary: %{name}'s cleanup-unassigned plugin
Requires: %{name} = %{version}

%description action-cleanup-unassigned
A plugin for %{name} implementing cleanup of unassigned packages

%package action-check-repo
Summary: %{name}'s check repo plugin
Requires: %{name} = %{version}

%description action-check-repo
A plugin for %{name} implementing checking of repositories

%package bugtracker-bugzilla
Summary: %{name}'s bugzilla support
Requires: %{name} = %{version}
Requires: python3-bugzilla >= 2.0

%description bugtracker-bugzilla
A plugin adding bugzilla support to %{name}

%package bugtracker-fedora-bugzilla
Summary: %{name}'s bugzilla support for Fedora
Requires: %{name} = %{version}
Requires: %{name}-bugtracker-bugzilla = %{version}

%description bugtracker-fedora-bugzilla
A plugin adding support for bugzilla used by Fedora

%package bugtracker-rhel-bugzilla
Summary: %{name}'s bugzilla support for RHEL
Requires: %{name} = %{version}
Requires: %{name}-bugtracker-bugzilla = %{version}

%description bugtracker-rhel-bugzilla
A plugin adding support for bugzilla used by Red Hat Enterprise Linux

%package solutionfinder-prefilter
Summary: %{name}'s solution-finder-prefilter plugin
Requires: %{name} = %{version}

%description solutionfinder-prefilter
A plugin for %{name} implementing the Prefilter solution finder

%package solutionfinder-probable-fix
Summary: %{name}'s solution-finder-probable-fix plugin
Requires: %{name} = %{version}

%description solutionfinder-probable-fix
A plugin for %{name} implementing the Probale Fix solution finder

%package blueprint-symbol-transfer
Summary: %{name}'s symbol transfer blueprint
Requires: faf = %{version}
Requires: %{name} = %{version}
Requires: %{name}-webui = %{version}

%description blueprint-symbol-transfer
A plugin for %{name} implementing symbol transfer plugin.

%package blueprint-celery-tasks
Summary: %{name}'s Celery tasks blueprint
Requires: faf = %{version}
Requires: %{name} = %{version}
Requires: %{name}-webui = %{version}
Requires: %{name}-celery-tasks = %{version}
Requires: python3-munch
Requires: python3-redis

%description blueprint-celery-tasks
A plugin for %{name} implementing Celery tasks blueprint plugin.

%package migrations
Summary: %{name}'s database migrations
Requires: %{name} = %{version}
Requires: python3-alembic

%description migrations
Database migrations using alembic

%package bugtracker-mantis
Summary: %{name}'s mantis support
Requires: %{name} = %{version}
Requires: python3-zeep

%description bugtracker-mantis
A plugin adding mantis support to %{name}

%package bugtracker-centos-mantis
Summary: %{name}'s Mantis support for CentOS
Requires: %{name} = %{version}
Requires: %{name}-bugtracker-mantis = %{version}

%description bugtracker-centos-mantis
A plugin adding support for Mantis used by CentOS

%package fedmsg
Summary: %{name}'s Fedora Messaging support
Requires: %{name} = %{version}
Requires: %{name}-schema = %{version}
Requires: python3-fedora-messaging

%description fedmsg
Base for Fedora Messaging support.

%package fedmsg-realtime
Summary: %{name}'s support for realtime Fedora Messaging notification sending
Requires: %{name} = %{version}
Requires: %{name}-fedmsg = %{version}

%description fedmsg-realtime
Support for sending Fedora Messaging notifications as reports are saved.

%package celery-tasks
Summary: %{name}'s task queue based on Celery
Requires: %{name} = %{version}
Requires: python3-celery >= 3.1

%description celery-tasks
Task queue using Celery.

%package celery-tasks-systemd-services
Summary: %{name}'s Celery task queue systemd services
Requires: %{name} = %{version}
%if 0%{?fedora} > 27 || 0%{?rhel} > 7
%{?systemd_requires}
%else
Requires: systemd-units
%endif

%description celery-tasks-systemd-services
systemd services for the Celery task queue.

%post celery-tasks-systemd-services
%systemd_post faf-celery-beat.service
%systemd_post faf-celery-worker.service

%preun celery-tasks-systemd-services
%systemd_preun faf-celery-beat.service
%systemd_preun faf-celery-worker.service

%postun celery-tasks-systemd-services
%systemd_postun_with_restart faf-celery-beat.service
%systemd_postun_with_restart faf-celery-worker.service

%prep
%setup -q
NOCONFIGURE=1 ./autogen.sh

%build
%configure
make %{?_smp_mflags}

%install
make install DESTDIR=%{buildroot}

# embedded action names
ln -s %{_bindir}/faf %{buildroot}%{_bindir}/faf-c2p

# /etc
mkdir -p %{buildroot}%{_sysconfdir}/faf
mkdir -p %{buildroot}%{_sysconfdir}/faf/plugins
mkdir -p %{buildroot}%{_sysconfdir}/faf/templates

# /usr/share
mkdir -p %{buildroot}%{_datadir}/faf/web/media
mkdir -p %{buildroot}%{_datadir}/faf/web/static

# /var/spool
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/lob
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/reports
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/reports/incoming
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/reports/deferred
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/reports/saved
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/reports/archive
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/attachments/
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/attachments/incoming
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/attachments/deferred
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/attachments/saved
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/attachments/archive
mkdir -p %{buildroot}%{_localstatedir}/spool/faf/openid_store

# /var/log
mkdir -p %{buildroot}%{_localstatedir}/log/faf/

mkdir -p %{buildroot}%{_tmpfilesdir}
mkdir -p %{buildroot}/run/faf-celery

%posttrans
%systemd_post httpd.service

%check
make check || ( cat tests/test_webfaf/test-suite.log; cat tests/test-suite.log; exit 1; )

%pre
# http://fedoraproject.org/wiki/Packaging:UsersAndGroups
getent group faf >/dev/null || groupadd --system faf
getent passwd faf >/dev/null || useradd --system -g faf -d /etc/faf -s /sbin/nologin faf
exit 0

%post webui
if [ "$1" = 1 ]
then
    # alphanumeric string of 50 characters
    RANDOM_STR="$( tr -dc [:alnum:] < /dev/urandom | head -c 50 )"
    sed -i "s#@SECRET_KEY@#$RANDOM_STR#g" %{_sysconfdir}/faf/plugins/web.conf
fi

%files
# /etc
%dir %{_sysconfdir}/faf
%dir %{_sysconfdir}/faf/plugins
%dir %{_sysconfdir}/faf/templates
%config(noreplace) %{_sysconfdir}/faf/faf.conf
%config(noreplace) %{_sysconfdir}/faf/faf-logging.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/faf
%config(noreplace) %{_sysconfdir}/bash_completion.d/faf.bash_completion

# /var/spool
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/lob
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/reports
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/reports/incoming
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/reports/saved
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/reports/deferred
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/reports/archive
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/attachments
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/attachments/incoming
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/attachments/deferred
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/attachments/saved
%dir %attr(0775, faf, faf) %{_localstatedir}/spool/faf/attachments/archive

# /var/log
%dir %attr(0775, faf, faf) %{_localstatedir}/log/faf

# /usr/bin
%{_bindir}/faf

# /usr/lib/python*/pyfaf

%dir %{python3_sitelib}/pyfaf
%dir %{python3_sitelib}/pyfaf/__pycache__
%{python3_sitelib}/pyfaf/__init__.py
%{python3_sitelib}/pyfaf/checker.py
%{python3_sitelib}/pyfaf/cmdline.py
%{python3_sitelib}/pyfaf/common.py
%{python3_sitelib}/pyfaf/config.py
%{python3_sitelib}/pyfaf/local.py
%{python3_sitelib}/pyfaf/retrace.py
%{python3_sitelib}/pyfaf/faf_rpm.py
%{python3_sitelib}/pyfaf/queries.py
%{python3_sitelib}/pyfaf/ureport.py
%{python3_sitelib}/pyfaf/ureport_compat.py
%{python3_sitelib}/pyfaf/__pycache__/__init__.*.pyc
%{python3_sitelib}/pyfaf/__pycache__/checker.*.pyc
%{python3_sitelib}/pyfaf/__pycache__/cmdline.*.pyc
%{python3_sitelib}/pyfaf/__pycache__/common.*.pyc
%{python3_sitelib}/pyfaf/__pycache__/config.*.pyc
%{python3_sitelib}/pyfaf/__pycache__/local.*.pyc
%{python3_sitelib}/pyfaf/__pycache__/retrace.*.pyc
%{python3_sitelib}/pyfaf/__pycache__/faf_rpm.*.pyc
%{python3_sitelib}/pyfaf/__pycache__/queries.*.pyc
%{python3_sitelib}/pyfaf/__pycache__/ureport.*.pyc
%{python3_sitelib}/pyfaf/__pycache__/ureport_compat.*.pyc

%dir %{python3_sitelib}/pyfaf/actions
%dir %{python3_sitelib}/pyfaf/actions/__pycache__
%{python3_sitelib}/pyfaf/actions/__init__.py
%{python3_sitelib}/pyfaf/actions/init.py
%{python3_sitelib}/pyfaf/actions/componentadd.py
%{python3_sitelib}/pyfaf/actions/hash_paths.py
%{python3_sitelib}/pyfaf/actions/opsysadd.py
%{python3_sitelib}/pyfaf/actions/opsysdel.py
%{python3_sitelib}/pyfaf/actions/opsyslist.py
%{python3_sitelib}/pyfaf/actions/releaseadd.py
%{python3_sitelib}/pyfaf/actions/releasedel.py
%{python3_sitelib}/pyfaf/actions/releaselist.py
%{python3_sitelib}/pyfaf/actions/releasemod.py
%{python3_sitelib}/pyfaf/actions/match_unknown_packages.py
%{python3_sitelib}/pyfaf/actions/__pycache__/__init__.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/init.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/componentadd.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/hash_paths.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/opsysadd.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/opsysdel.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/opsyslist.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/releaseadd.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/releasedel.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/releaselist.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/releasemod.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/match_unknown_packages.*.pyc

%dir %{python3_sitelib}/pyfaf/bugtrackers
%dir %{python3_sitelib}/pyfaf/bugtrackers/__pycache__
%{python3_sitelib}/pyfaf/bugtrackers/__init__.py
%{python3_sitelib}/pyfaf/bugtrackers/__pycache__/__init__.*.pyc

%dir %{python3_sitelib}/pyfaf/opsys
%dir %{python3_sitelib}/pyfaf/opsys/__pycache__
%{python3_sitelib}/pyfaf/opsys/__init__.py
%{python3_sitelib}/pyfaf/opsys/__pycache__/__init__.*.pyc

%dir %{python3_sitelib}/pyfaf/problemtypes
%dir %{python3_sitelib}/pyfaf/problemtypes/__pycache__
%{python3_sitelib}/pyfaf/problemtypes/__init__.py
%{python3_sitelib}/pyfaf/problemtypes/__pycache__/__init__.*.pyc

%dir %{python3_sitelib}/pyfaf/repos
%dir %{python3_sitelib}/pyfaf/repos/__pycache__
%{python3_sitelib}/pyfaf/repos/__init__.py
%{python3_sitelib}/pyfaf/repos/rpm_metadata.py
%{python3_sitelib}/pyfaf/repos/__pycache__/__init__.*.pyc
%{python3_sitelib}/pyfaf/repos/__pycache__/rpm_metadata.*.pyc

%dir %{python3_sitelib}/pyfaf/solutionfinders
%dir %{python3_sitelib}/pyfaf/solutionfinders/__pycache__
%{python3_sitelib}/pyfaf/solutionfinders/__init__.py
%{python3_sitelib}/pyfaf/solutionfinders/__pycache__/__init__.*.pyc

%dir %{python3_sitelib}/pyfaf/storage
%dir %{python3_sitelib}/pyfaf/storage/__pycache__
%{python3_sitelib}/pyfaf/storage/__init__.py
%{python3_sitelib}/pyfaf/storage/bugzilla.py
%{python3_sitelib}/pyfaf/storage/bugtracker.py
%{python3_sitelib}/pyfaf/storage/custom_types.py
%{python3_sitelib}/pyfaf/storage/debug.py
%{python3_sitelib}/pyfaf/storage/externalfaf.py
%{python3_sitelib}/pyfaf/storage/events.py
%{python3_sitelib}/pyfaf/storage/generic_table.py
%{python3_sitelib}/pyfaf/storage/sf_prefilter.py
%{python3_sitelib}/pyfaf/storage/llvm.py
%{python3_sitelib}/pyfaf/storage/opsys.py
%{python3_sitelib}/pyfaf/storage/mantisbt.py
%{python3_sitelib}/pyfaf/storage/problem.py
%{python3_sitelib}/pyfaf/storage/project.py
%{python3_sitelib}/pyfaf/storage/report.py
%{python3_sitelib}/pyfaf/storage/symbol.py
%{python3_sitelib}/pyfaf/storage/user.py
%{python3_sitelib}/pyfaf/storage/jsontype.py
%{python3_sitelib}/pyfaf/storage/task.py
%{python3_sitelib}/pyfaf/storage/__pycache__/__init__.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/bugzilla.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/bugtracker.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/custom_types.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/debug.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/externalfaf.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/events.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/generic_table.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/sf_prefilter.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/llvm.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/opsys.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/mantisbt.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/problem.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/project.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/report.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/symbol.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/user.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/jsontype.*.pyc
%{python3_sitelib}/pyfaf/storage/__pycache__/task.*.pyc

%dir %{python3_sitelib}/pyfaf/storage/fixtures
%dir %{python3_sitelib}/pyfaf/storage/fixtures/__pycache__
%{python3_sitelib}/pyfaf/storage/fixtures/__init__.py
%{python3_sitelib}/pyfaf/storage/fixtures/data.py
%{python3_sitelib}/pyfaf/storage/fixtures/randutils.py
%{python3_sitelib}/pyfaf/storage/fixtures/__pycache__/__init__.*.pyc
%{python3_sitelib}/pyfaf/storage/fixtures/__pycache__/data.*.pyc
%{python3_sitelib}/pyfaf/storage/fixtures/__pycache__/randutils.*.pyc

%dir %{python3_sitelib}/pyfaf/utils
%dir %{python3_sitelib}/pyfaf/utils/__pycache__
%{python3_sitelib}/pyfaf/utils/__init__.py
%{python3_sitelib}/pyfaf/utils/contextmanager.py
%{python3_sitelib}/pyfaf/utils/date.py
%{python3_sitelib}/pyfaf/utils/decorators.py
%{python3_sitelib}/pyfaf/utils/format.py
%{python3_sitelib}/pyfaf/utils/hash.py
%{python3_sitelib}/pyfaf/utils/parse.py
%{python3_sitelib}/pyfaf/utils/proc.py
%{python3_sitelib}/pyfaf/utils/storage.py
%{python3_sitelib}/pyfaf/utils/user.py
%{python3_sitelib}/pyfaf/utils/web.py
%{python3_sitelib}/pyfaf/utils/__pycache__/__init__.*.pyc
%{python3_sitelib}/pyfaf/utils/__pycache__/contextmanager.*.pyc
%{python3_sitelib}/pyfaf/utils/__pycache__/date.*.pyc
%{python3_sitelib}/pyfaf/utils/__pycache__/decorators.*.pyc
%{python3_sitelib}/pyfaf/utils/__pycache__/format.*.pyc
%{python3_sitelib}/pyfaf/utils/__pycache__/hash.*.pyc
%{python3_sitelib}/pyfaf/utils/__pycache__/parse.*.pyc
%{python3_sitelib}/pyfaf/utils/__pycache__/proc.*.pyc
%{python3_sitelib}/pyfaf/utils/__pycache__/storage.*.pyc
%{python3_sitelib}/pyfaf/utils/__pycache__/user.*.pyc
%{python3_sitelib}/pyfaf/utils/__pycache__/web.*.pyc

# /usr/share/faf
%dir %{_datadir}/faf
%{_datadir}/faf/fixtures/lob_download_location

%dir %{_datadir}/faf/fixtures/sql
%{_datadir}/faf/fixtures/sql/archs.sql
%{_datadir}/faf/fixtures/sql/archstags.sql
%{_datadir}/faf/fixtures/sql/buildarchs.sql
%{_datadir}/faf/fixtures/sql/builds.sql
%{_datadir}/faf/fixtures/sql/buildstags.sql
%{_datadir}/faf/fixtures/sql/buildsys.sql
%{_datadir}/faf/fixtures/sql/opsys.sql
%{_datadir}/faf/fixtures/sql/opsyscomponents.sql
%{_datadir}/faf/fixtures/sql/opsysreleases.sql
%{_datadir}/faf/fixtures/sql/opsysreleasescomponents.sql
%{_datadir}/faf/fixtures/sql/packages.sql
%{_datadir}/faf/fixtures/sql/taginheritances.sql
%{_datadir}/faf/fixtures/sql/tags.sql

# Configuration file for systemd-tmpfiles(8).
%{_tmpfilesdir}/faf.conf

%files webui
# /etc
%config(noreplace) %{_sysconfdir}/httpd/conf.d/faf-web.conf
%config(noreplace) %{_sysconfdir}/faf/plugins/web.conf

# /usr/lib/python*/webfaf

%dir %{python3_sitelib}/webfaf
%dir %{python3_sitelib}/webfaf/__pycache__
%{python3_sitelib}/webfaf/__init__.py
%{python3_sitelib}/webfaf/config.py
%{python3_sitelib}/webfaf/filters.py
%{python3_sitelib}/webfaf/forms.py
%{python3_sitelib}/webfaf/hub.wsgi
%{python3_sitelib}/webfaf/login.py
%{python3_sitelib}/webfaf/problems.py
%{python3_sitelib}/webfaf/reports.py
%{python3_sitelib}/webfaf/stats.py
%{python3_sitelib}/webfaf/summary.py
%{python3_sitelib}/webfaf/user.py
%{python3_sitelib}/webfaf/utils.py
%{python3_sitelib}/webfaf/webfaf_main.py
%{python3_sitelib}/webfaf/__pycache__/__init__.*.pyc
%{python3_sitelib}/webfaf/__pycache__/config.*.pyc
%{python3_sitelib}/webfaf/__pycache__/filters.*.pyc
%{python3_sitelib}/webfaf/__pycache__/forms.*.pyc
%{python3_sitelib}/webfaf/__pycache__/login.*.pyc
%{python3_sitelib}/webfaf/__pycache__/problems.*.pyc
%{python3_sitelib}/webfaf/__pycache__/reports.*.pyc
%{python3_sitelib}/webfaf/__pycache__/stats.*.pyc
%{python3_sitelib}/webfaf/__pycache__/summary.*.pyc
%{python3_sitelib}/webfaf/__pycache__/user.*.pyc
%{python3_sitelib}/webfaf/__pycache__/utils.*.pyc
%{python3_sitelib}/webfaf/__pycache__/webfaf_main.*.pyc

%dir %{python3_sitelib}/webfaf/blueprints
%dir %{python3_sitelib}/webfaf/blueprints/__pycache__
%{python3_sitelib}/webfaf/blueprints/__init__.py
%{python3_sitelib}/webfaf/blueprints/__pycache__/__init__.*.pyc

%dir %{python3_sitelib}/webfaf/templates
%{python3_sitelib}/webfaf/templates/_helpers.html
%{python3_sitelib}/webfaf/templates/403.html
%{python3_sitelib}/webfaf/templates/404.html
%{python3_sitelib}/webfaf/templates/413.html
%{python3_sitelib}/webfaf/templates/500.html
%{python3_sitelib}/webfaf/templates/about.md
%{python3_sitelib}/webfaf/templates/base.html
%{python3_sitelib}/webfaf/templates/mdpage.html

%dir %{python3_sitelib}/webfaf/templates/problems
%{python3_sitelib}/webfaf/templates/problems/item.html
%{python3_sitelib}/webfaf/templates/problems/list.html
%{python3_sitelib}/webfaf/templates/problems/list_table_rows.html
%{python3_sitelib}/webfaf/templates/problems/multiple_bthashes.html
%{python3_sitelib}/webfaf/templates/problems/waitforit.html

%dir %{python3_sitelib}/webfaf/templates/reports
%{python3_sitelib}/webfaf/templates/reports/associate_bug.html
%{python3_sitelib}/webfaf/templates/reports/attach.html
%{python3_sitelib}/webfaf/templates/reports/diff.html
%{python3_sitelib}/webfaf/templates/reports/item.html
%{python3_sitelib}/webfaf/templates/reports/list.html
%{python3_sitelib}/webfaf/templates/reports/list_table_rows.html
%{python3_sitelib}/webfaf/templates/reports/new.html
%{python3_sitelib}/webfaf/templates/reports/waitforit.html

%dir %{python3_sitelib}/webfaf/templates/stats
%{python3_sitelib}/webfaf/templates/stats/by_date.html

%dir %{python3_sitelib}/webfaf/templates/summary
%{python3_sitelib}/webfaf/templates/summary/index.html
%{python3_sitelib}/webfaf/templates/summary/index_plot_data.html

# /usr/share/faf/
%dir %{_datadir}/faf/web
%dir %{_datadir}/faf/web/static
%dir %{_datadir}/faf/web/static/js
%dir %{_datadir}/faf/web/static/css
%dir %{_datadir}/faf/web/static/icons
%{_datadir}/faf/web/static/js/*.js
%{_datadir}/faf/web/static/css/*.css
%{_datadir}/faf/web/static/icons/*.png

# /var/spool/faf
%dir %attr(0770, faf, faf) %{_localstatedir}/spool/faf/openid_store

%files problem-coredump
%config(noreplace) %{_sysconfdir}/faf/plugins/coredump.conf
%{python3_sitelib}/pyfaf/problemtypes/core.py
%{python3_sitelib}/pyfaf/problemtypes/__pycache__/core.*.pyc

%files problem-java
%config(noreplace) %{_sysconfdir}/faf/plugins/java.conf
%{python3_sitelib}/pyfaf/problemtypes/java.py
%{python3_sitelib}/pyfaf/problemtypes/__pycache__/java.*.pyc

%files problem-kerneloops
%config(noreplace) %{_sysconfdir}/faf/plugins/kerneloops.conf
%{python3_sitelib}/pyfaf/problemtypes/kerneloops.py
%{python3_sitelib}/pyfaf/problemtypes/__pycache__/kerneloops.*.pyc

%files problem-python
%config(noreplace) %{_sysconfdir}/faf/plugins/python.conf
%{python3_sitelib}/pyfaf/problemtypes/python.py
%{python3_sitelib}/pyfaf/problemtypes/__pycache__/python.*.pyc

%files problem-ruby
%config(noreplace) %{_sysconfdir}/faf/plugins/ruby.conf
%{python3_sitelib}/pyfaf/problemtypes/ruby.py
%{python3_sitelib}/pyfaf/problemtypes/__pycache__/ruby.*.pyc

%files dnf
%config(noreplace) %{_sysconfdir}/faf/plugins/dnf.conf
%{python3_sitelib}/pyfaf/repos/dnf.py
%{python3_sitelib}/pyfaf/repos/__pycache__/dnf.*.pyc

%files opsys-centos
%config(noreplace) %{_sysconfdir}/faf/plugins/centos.conf
%{python3_sitelib}/pyfaf/opsys/centos.py
%{python3_sitelib}/pyfaf/opsys/__pycache__/centos.*.pyc

%files opsys-fedora
%config(noreplace) %{_sysconfdir}/faf/plugins/fedora.conf
%{python3_sitelib}/pyfaf/opsys/fedora.py
%{python3_sitelib}/pyfaf/opsys/__pycache__/fedora.*.pyc

%files schema
%{python3_sitelib}/faf_schema/
%{python3_sitelib}/faf_schema*.egg-info/

%files action-sar
%{python3_sitelib}/pyfaf/actions/sar.py
%{python3_sitelib}/pyfaf/actions/__pycache__/sar.*.pyc

%files action-save-reports
%config(noreplace) %{_sysconfdir}/faf/plugins/save-reports.conf
%{python3_sitelib}/pyfaf/actions/save_reports.py
%{python3_sitelib}/pyfaf/actions/__pycache__/save_reports.*.pyc

%files action-archive-reports
%{python3_sitelib}/pyfaf/actions/archive_reports.py
%{python3_sitelib}/pyfaf/actions/__pycache__/archive_reports.*.pyc

%files action-create-problems
%config(noreplace) %{_sysconfdir}/faf/plugins/create-problems.conf
%{python3_sitelib}/pyfaf/actions/create_problems.py
%{python3_sitelib}/pyfaf/actions/__pycache__/create_problems.*.pyc

%files action-shell
%{python3_sitelib}/pyfaf/actions/shell.py
%{python3_sitelib}/pyfaf/actions/__pycache__/shell.*.pyc

%files action-pull-releases
%{python3_sitelib}/pyfaf/actions/pull_releases.py
%{python3_sitelib}/pyfaf/actions/__pycache__/pull_releases.*.pyc

%files action-pull-reports
%config(noreplace) %{_sysconfdir}/faf/plugins/pull-reports.conf
%{python3_sitelib}/pyfaf/actions/pull_reports.py
%{python3_sitelib}/pyfaf/actions/__pycache__/pull_reports.*.pyc

%files action-pull-components
%{python3_sitelib}/pyfaf/actions/pull_components.py
%{python3_sitelib}/pyfaf/actions/__pycache__/pull_components.*.pyc

%files action-pull-associates
%{python3_sitelib}/pyfaf/actions/pull_associates.py
%{python3_sitelib}/pyfaf/actions/__pycache__/pull_associates.*.pyc

%files action-find-components
%{python3_sitelib}/pyfaf/actions/find_components.py
%{python3_sitelib}/pyfaf/actions/__pycache__/find_components.*.pyc

%files action-find-crash-function
%{python3_sitelib}/pyfaf/actions/find_crash_function.py
%{python3_sitelib}/pyfaf/actions/__pycache__/find_crash_function.*.pyc

%files action-find-report-solution
%{python3_sitelib}/pyfaf/actions/find_report_solution.py
%{python3_sitelib}/pyfaf/actions/__pycache__/find_report_solution.*.pyc

%files action-assign-release-to-builds
%{python3_sitelib}/pyfaf/actions/assign_release_to_builds.py
%{python3_sitelib}/pyfaf/actions/__pycache__/assign_release_to_builds.*.pyc

%files action-repo
%{python3_sitelib}/pyfaf/actions/repoadd.py
%{python3_sitelib}/pyfaf/actions/repoassign.py
%{python3_sitelib}/pyfaf/actions/repodel.py
%{python3_sitelib}/pyfaf/actions/repoinfo.py
%{python3_sitelib}/pyfaf/actions/repoimport.py
%{python3_sitelib}/pyfaf/actions/repolist.py
%{python3_sitelib}/pyfaf/actions/repomod.py
%{python3_sitelib}/pyfaf/actions/reposync.py
%{python3_sitelib}/pyfaf/actions/__pycache__/repoadd.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/repoassign.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/repodel.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/repoinfo.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/repoimport.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/repolist.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/repomod.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/reposync.*.pyc

%files action-retrace
%config(noreplace) %{_sysconfdir}/faf/plugins/retrace.conf
%{python3_sitelib}/pyfaf/actions/retrace.py
%{python3_sitelib}/pyfaf/actions/__pycache__/retrace.*.pyc

%files action-arch
%{python3_sitelib}/pyfaf/actions/archadd.py
%{python3_sitelib}/pyfaf/actions/archlist.py
%{python3_sitelib}/pyfaf/actions/__pycache__/archadd.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/archlist.*.pyc

%files action-sf-prefilter
%{python3_sitelib}/pyfaf/actions/sf_prefilter_patadd.py
%{python3_sitelib}/pyfaf/actions/sf_prefilter_patshow.py
%{python3_sitelib}/pyfaf/actions/sf_prefilter_soladd.py
%{python3_sitelib}/pyfaf/actions/sf_prefilter_solshow.py
%{python3_sitelib}/pyfaf/actions/__pycache__/sf_prefilter_patadd.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/sf_prefilter_patshow.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/sf_prefilter_soladd.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/sf_prefilter_solshow.*.pyc

%files action-c2p
%{_bindir}/faf-c2p
%{python3_sitelib}/pyfaf/actions/c2p.py
%{python3_sitelib}/pyfaf/actions/__pycache__/c2p.*.pyc

%files action-bugtracker
%{python3_sitelib}/pyfaf/actions/bugtrackerlist.py
%{python3_sitelib}/pyfaf/actions/pull_abrt_bugs.py
%{python3_sitelib}/pyfaf/actions/pull_bug.py
%{python3_sitelib}/pyfaf/actions/update_bugs.py
%{python3_sitelib}/pyfaf/actions/__pycache__/bugtrackerlist.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/pull_abrt_bugs.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/pull_bug.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/update_bugs.*.pyc

%files action-stats
%{python3_sitelib}/pyfaf/actions/stats.py
%{python3_sitelib}/pyfaf/actions/__pycache__/stats.*.pyc

%files action-external-faf
%{python3_sitelib}/pyfaf/actions/extfafadd.py
%{python3_sitelib}/pyfaf/actions/extfafshow.py
%{python3_sitelib}/pyfaf/actions/extfafmodify.py
%{python3_sitelib}/pyfaf/actions/extfafdelete.py
%{python3_sitelib}/pyfaf/actions/extfaflink.py
%{python3_sitelib}/pyfaf/actions/__pycache__/extfafadd.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/extfafshow.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/extfafmodify.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/extfafdelete.*.pyc
%{python3_sitelib}/pyfaf/actions/__pycache__/extfaflink.*.pyc

%files action-external-faf-clone-bz
%config(noreplace) %{_sysconfdir}/faf/plugins/clonebz.conf
%{python3_sitelib}/pyfaf/actions/extfafclonebz.py
%{python3_sitelib}/pyfaf/actions/__pycache__/extfafclonebz.*.pyc

%files action-add-compat-hashes
%{python3_sitelib}/pyfaf/actions/addcompathashes.py
%{python3_sitelib}/pyfaf/actions/__pycache__/addcompathashes.*.pyc

%files action-mark-probably-fixed
%{python3_sitelib}/pyfaf/actions/mark_probably_fixed.py
%{python3_sitelib}/pyfaf/actions/__pycache__/mark_probably_fixed.*.pyc

%files action-retrace-remote
%{python3_sitelib}/pyfaf/actions/retrace_remote.py
%{python3_sitelib}/pyfaf/actions/__pycache__/retrace_remote.*.pyc
%config(noreplace) %{_sysconfdir}/faf/plugins/retrace-remote.conf

%files action-attach-centos-bugs
%{python3_sitelib}/pyfaf/actions/attach_centos_bugs.py
%{python3_sitelib}/pyfaf/actions/__pycache__/attach_centos_bugs.*.pyc

%files action-fedmsg-notify
%{python3_sitelib}/pyfaf/actions/fedmsg_notify.py
%{python3_sitelib}/pyfaf/actions/__pycache__/fedmsg_notify.*.pyc

%files action-cleanup-packages
%{python3_sitelib}/pyfaf/actions/cleanup_packages.py
%{python3_sitelib}/pyfaf/actions/__pycache__/cleanup_packages.*.pyc

%files action-delete-invalid-ureports
%{python3_sitelib}/pyfaf/actions/delete_invalid_ureports.py
%{python3_sitelib}/pyfaf/actions/__pycache__/delete_invalid_ureports.*.pyc

%files action-cleanup-task-results
%{python3_sitelib}/pyfaf/actions/cleanup_task_results.py
%{python3_sitelib}/pyfaf/actions/__pycache__/cleanup_task_results.*.pyc

%files action-cleanup-unassigned
%{python3_sitelib}/pyfaf/actions/cleanup_unassigned.py
%{python3_sitelib}/pyfaf/actions/__pycache__/cleanup_unassigned.*.pyc

%files action-check-repo
%{python3_sitelib}/pyfaf/actions/check_repo.py
%{python3_sitelib}/pyfaf/actions/__pycache__/check_repo.*.pyc

%files bugtracker-bugzilla
%{python3_sitelib}/pyfaf/bugtrackers/bugzilla.py
%{python3_sitelib}/pyfaf/bugtrackers/__pycache__/bugzilla.*.pyc

%files bugtracker-fedora-bugzilla
%{python3_sitelib}/pyfaf/bugtrackers/fedorabz.py
%{python3_sitelib}/pyfaf/bugtrackers/__pycache__/fedorabz.*.pyc
%config(noreplace) %{_sysconfdir}/faf/plugins/fedorabz.conf

%files bugtracker-rhel-bugzilla
%{python3_sitelib}/pyfaf/bugtrackers/rhelbz.py
%{python3_sitelib}/pyfaf/bugtrackers/__pycache__/rhelbz.*.pyc
%config(noreplace) %{_sysconfdir}/faf/plugins/rhelbz.conf

%files solutionfinder-prefilter
%{python3_sitelib}/pyfaf/solutionfinders/prefilter_solution_finder.py
%{python3_sitelib}/pyfaf/solutionfinders/__pycache__/prefilter_solution_finder.*.pyc
%config(noreplace) %{_sysconfdir}/faf/plugins/sf-prefilter.conf

%files solutionfinder-probable-fix
%{python3_sitelib}/pyfaf/solutionfinders/probable_fix_solution_finder.py
%{python3_sitelib}/pyfaf/solutionfinders/__pycache__/probable_fix_solution_finder.*.pyc

%files blueprint-symbol-transfer
%config(noreplace) %{_sysconfdir}/faf/plugins/symbol-transfer.conf
%{python3_sitelib}/webfaf/blueprints/symbol_transfer.py
%{python3_sitelib}/webfaf/blueprints/__pycache__/symbol_transfer.*.pyc

%files blueprint-celery-tasks
%dir %{python3_sitelib}/webfaf/templates/celery_tasks
%{python3_sitelib}/webfaf/blueprints/celery_tasks.py
%{python3_sitelib}/webfaf/blueprints/__pycache__/celery_tasks.*.pyc
%{python3_sitelib}/webfaf/templates/celery_tasks/action_run.html
%{python3_sitelib}/webfaf/templates/celery_tasks/index.html
%{python3_sitelib}/webfaf/templates/celery_tasks/results_item.html
%{python3_sitelib}/webfaf/templates/celery_tasks/results_list.html
%{python3_sitelib}/webfaf/templates/celery_tasks/schedule_item.html

%files migrations
%config(noreplace) %{_sysconfdir}/bash_completion.d/faf-migrate-db.bash_completion
%dir %{python3_sitelib}/pyfaf/storage/migrations
%dir %{python3_sitelib}/pyfaf/storage/migrations/__pycache__
%dir %{python3_sitelib}/pyfaf/storage/migrations/versions
%dir %{python3_sitelib}/pyfaf/storage/migrations/versions/__pycache__
%{python3_sitelib}/pyfaf/storage/migrations/alembic.ini
%{python3_sitelib}/pyfaf/storage/migrations/__init__.py
%{python3_sitelib}/pyfaf/storage/migrations/env.py
%{python3_sitelib}/pyfaf/storage/migrations/versions/*.py
%{python3_sitelib}/pyfaf/storage/migrations/__pycache__/__init__.*.pyc
%{python3_sitelib}/pyfaf/storage/migrations/__pycache__/env.*.pyc
%{python3_sitelib}/pyfaf/storage/migrations/versions/__pycache__/*.pyc
%{_bindir}/faf-migrate-db

%files bugtracker-mantis
%{python3_sitelib}/pyfaf/bugtrackers/mantisbt.py
%{python3_sitelib}/pyfaf/bugtrackers/__pycache__/mantisbt.*.pyc

%files bugtracker-centos-mantis
%{python3_sitelib}/pyfaf/bugtrackers/centosmantisbt.py
%{python3_sitelib}/pyfaf/bugtrackers/__pycache__/centosmantisbt.*.pyc
%config(noreplace) %{_sysconfdir}/faf/plugins/centosmantisbt.conf

%files fedmsg
%config(noreplace) %{_sysconfdir}/faf/plugins/fedmsg.conf

%files fedmsg-realtime
%{python3_sitelib}/pyfaf/storage/events_fedmsg.py
%{python3_sitelib}/pyfaf/storage/__pycache__/events_fedmsg.*.pyc

%files celery-tasks
%config(noreplace) %{_sysconfdir}/faf/plugins/celery_tasks.conf
%dir %{python3_sitelib}/pyfaf/celery_tasks
%dir %{python3_sitelib}/pyfaf/celery_tasks/__pycache__
%{python3_sitelib}/pyfaf/celery_tasks/__init__.py
%{python3_sitelib}/pyfaf/celery_tasks/schedulers.py
%{python3_sitelib}/pyfaf/celery_tasks/__pycache__/__init__.*.pyc
%{python3_sitelib}/pyfaf/celery_tasks/__pycache__/schedulers.*.pyc

%files celery-tasks-systemd-services
%{_unitdir}/faf-celery-beat.service
%{_unitdir}/faf-celery-worker.service
%config(noreplace) %{_sysconfdir}/faf/celery-beat-env.conf
%config(noreplace) %{_sysconfdir}/faf/celery-worker-env.conf
%{_tmpfilesdir}/faf-celery-tmpfiles.conf
%dir %attr(0775, faf, faf) /run/faf-celery/

%changelog
