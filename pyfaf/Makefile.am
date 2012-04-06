SUBDIRS = client hub worker

pyfaf_PYTHON = \
	__init__.py \
	argparse.py \
	btserver.py \
	bugzilla.py \
	koji.py \
	libsolv.py \
	run.py \
	support.py \
	ureport.py \
	terminal.py
pyfafdir = $(pythondir)/pyfaf

nodist_config_SCRIPTS = config.py
configdir = $(pyfafdir)

pyfaf_cache_PYTHON =	\
	cache/__init__.py \
	cache/helpers.py \
	cache/abrt_report_check.py \
	cache/debuginfo_report.py \
	cache/debuginfo_sources.py \
	cache/fedora_pkgdb_collection.py \
	cache/fedora_pkgdb_package.py \
	cache/koji_build.py \
	cache/koji_build_funfin_report.py \
	cache/koji_rpm.py \
	cache/koji_tag.py \
	cache/rhbz_action.py \
	cache/rhbz_attachment.py \
	cache/rhbz_bug.py \
	cache/rhbz_bug_btserver_report.py \
	cache/rhbz_comment.py \
	cache/rhbz_cluster.py \
	cache/rhbz_user.py
pyfaf_cachedir = $(pythondir)/pyfaf/cache

pyfaf_storage_PYTHON = \
	storage/__init__.py \
	storage/common.py \
	storage/llvm.py \
	storage/opsys.py \
	storage/problem.py \
	storage/project.py \
	storage/symbol.py
pyfaf_storagedir = $(pythondir)/pyfaf/storage

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
