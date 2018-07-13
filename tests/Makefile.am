SUBDIRS = faftests sample_plugin_dir sample_reports sample_rpms webfaf \
		  retrace_outputs bin sample_repo

TESTS = test_actions.py \
	test_alembic.py \
	test_bugzilla.py \
	test_common.py \
	test_create_problems.py \
	test_checker.py \
	test_find_report_solution.py \
	test_mark_probably_fixed.py \
	test_queries.py \
	test_rpm.py \
	test_save_reports.py \
	test_storage.py \
	test_stats.py \
	test_report.py \
	test_ureport.py \
	test_utils.py \
	test_yum.py \
	test_rpm_metadata.py \
	test_retrace.py

check_SCRIPTS = $(TESTS)

check-local: check-TESTS

EXTRA_DIST = $(check_SCRIPTS)
