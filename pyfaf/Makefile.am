SUBDIRS = client hub worker cache storage

pyfaf_PYTHON = \
	__init__.py \
	argparse.py \
	btserver.py \
	bugzilla.py \
	common.py \
	koji.py \
	libsolv.py \
	package.py \
	run.py \
	support.py \
	ureport.py \
	terminal.py
pyfafdir = $(pythondir)/pyfaf

nodist_config_SCRIPTS = config.py
configdir = $(pyfafdir)

edit = sed \
	-e 's|@version[@]|$(PACKAGE_VERSION)|g' \
	-e 's|@bindir[@]|$(bindir)|g' \
	-e 's|@sysconfdir[@]|$(sysconfdir)|g' \
	-e 's|@prefix[@]|$(prefix)|g' \
	-e 's|@datadir[@]|$(datadir)|g' \
	-e 's|@libdir[@]|$(libdir)|g'

EXTRA_DIST = config.py.in
config.py: config.py.in Makefile
	$(edit) $< > $@
