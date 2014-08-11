SUBDIRS = faftests sample_plugin_dir sample_reports sample_rpms

TESTS = actions \
	bugzilla \
	common \
	checker \
	queries \
	rpm \
	storage \
	stats \
	report \
	ureport \
	utils \
	yum

#check_SCRIPTS = bugzilla common rpm storage report ureport utils yum queries checker \
#    actions

check_SCRIPTS = $(TESTS)

check-local: check-TESTS

EXTRA_DIST = $(check_SCRIPTS)
