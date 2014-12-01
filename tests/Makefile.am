SUBDIRS = faftests sample_plugin_dir sample_reports sample_rpms webfaf

TESTS = actions \
	bugzilla \
	common \
	checker \
	mark_probably_fixed \
	queries \
	rpm \
	save_reports \
	storage \
	stats \
	report \
	ureport \
	utils \
	yum

check_SCRIPTS = $(TESTS)

check-local: check-TESTS

EXTRA_DIST = $(check_SCRIPTS)
