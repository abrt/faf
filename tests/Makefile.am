SUBDIRS = faftests sample_plugin_dir sample_reports sample_rpms webfaf \
		  retrace_outputs bin

TESTS = actions \
	bugzilla \
	common \
	create_problems \
	checker \
	find_report_solution \
	mark_probably_fixed \
	queries \
	rpm \
	save_reports \
	storage \
	stats \
	report \
	ureport \
	utils \
	yum \
	rpm_metadata \
	retrace

check_SCRIPTS = $(TESTS)

check-local: check-TESTS

EXTRA_DIST = $(check_SCRIPTS)
