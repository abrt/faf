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
    rpm.py \
    queries.py \
    ureport.py \
    ureport_compat.py

pyfafdir = $(pythondir)/pyfaf

__init__.py: __init__.py.in
	sed -e 's|@fafversion@|'$$(cat $(top_builddir)/faf-version)'|' $< > $@

EXTRA_DIST = $(pyfaf_PYTHON) __init__.py.in
