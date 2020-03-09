SUBDIRS = \
    actions \
    bugtrackers \
    celery_tasks \
    opsys \
    problemtypes \
    repos \
    solutionfinders \
    storage \
    utils

pyfaf_PYTHON = \
    __init__.py \
    checker.py \
    cmdline.py \
    common.py \
    config.py \
    local.py \
    retrace.py \
    faf_rpm.py \
    queries.py \
    ureport.py \
    ureport_compat.py

pyfafdir = $(pythondir)/pyfaf

__init__.py: __init__.py.in
	sed -e 's|@fafversion@|'$$(cat $(top_builddir)/faf-version)'|' $< > $@

all-local: __init__.py

EXTRA_DIST = $(pyfaf_PYTHON) __init__.py.in
