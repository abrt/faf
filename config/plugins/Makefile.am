pluginconf_DATA = \
    centos.conf \
    clonebz.conf \
    centosmantisbt.conf \
    celery_tasks.conf \
    coredump.conf \
    create-problems.conf \
    fedora.conf \
    fedorabz.conf \
    fedmsg.conf \
    java.conf \
    kerneloops.conf \
    pull-reports.conf \
    python.conf \
    retrace.conf \
    retrace-remote.conf \
    ruby.conf \
    rhelbz.conf \
    save-reports.conf \
    sf-prefilter.conf \
    symbol-transfer.conf \
    web.conf

if USE_DNF
    pluginconf_DATA += dnf.conf
endif

if USE_YUM
    pluginconf_DATA += yum.conf
endif

pluginconfdir = $(sysconfdir)/faf/plugins

EXTRA_DIST = $(pluginconf_DATA)
