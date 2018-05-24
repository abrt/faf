AC_DEFUN([FAF_PARSE_WITH],
    [m4_pushdef([FAF_UC_PACKAGE], m4_toupper([$1]))dnl
    if test "$withval" = "no"; then
        NO_[]FAF_UC_PACKAGE=YesPlease
    elif test "$withval" = "yes"; then
        NO_[]FAF_UC_PACKAGE=
    else
        NO_[]FAF_UC_PACKAGE=
    fi
    m4_popdef([FAF_UC_PACKAGE])])

AC_INIT([faf],
    m4_esyscmd([cat ./faf-version]),
    [crash-catcher@fedorahosted.org])

AM_INIT_AUTOMAKE([foreign -Wall tar-ustar])
AM_MAINTAINER_MODE

AC_CONFIG_MACRO_DIR([m4])

AC_DISABLE_STATIC
AC_PROG_CC
AC_GNU_SOURCE
AC_PROG_LIBTOOL

AM_PATH_PYTHON([2.6])

AC_PATH_PROGS(BASH, sh bash)

AC_ARG_WITH(systemd,
AS_HELP_STRING([--with-systemd],[use Systemd (default is YES)]),
FAF_PARSE_WITH([systemd]))
if test -z "$NO_SYSTEMD" # if not defined
then
AC_MSG_NOTICE([building with systemd])
AM_CONDITIONAL(HAVE_SYSTEMD, true)
else
AC_MSG_NOTICE([building without systemd])
AM_CONDITIONAL(HAVE_SYSTEMD, false)
fi

AC_CONFIG_FILES([
    faf.spec
    Makefile
    config/Makefile
    config/plugins/Makefile
    config/templates/Makefile
    src/Makefile
    src/bin/Makefile
    src/pyfaf/Makefile
    src/pyfaf/actions/Makefile
    src/pyfaf/bugtrackers/Makefile
    src/pyfaf/celery_tasks/Makefile
    src/pyfaf/opsys/Makefile
    src/pyfaf/problemtypes/Makefile
    src/pyfaf/repos/Makefile
    src/pyfaf/solutionfinders/Makefile
    src/pyfaf/storage/Makefile
    src/pyfaf/storage/migrations/Makefile
    src/pyfaf/storage/migrations/versions/Makefile
    src/pyfaf/storage/fixtures/Makefile
    src/pyfaf/storage/fixtures/sql/Makefile
    src/pyfaf/utils/Makefile
    src/webfaf/Makefile
    src/webfaf/blueprints/Makefile
    src/webfaf/static/Makefile
    src/webfaf/static/js/Makefile
    src/webfaf/static/fonts/Makefile
    src/webfaf/static/icons/Makefile
    src/webfaf/static/css/Makefile
    src/webfaf/templates/Makefile
    src/webfaf/templates/celery_tasks/Makefile
    src/webfaf/templates/dumpdirs/Makefile
    src/webfaf/templates/problems/Makefile
    src/webfaf/templates/reports/Makefile
    src/webfaf/templates/stats/Makefile
    src/webfaf/templates/summary/Makefile
    tests/Makefile
    tests/faftests/Makefile
    tests/sample_plugin_dir/Makefile
    tests/sample_reports/Makefile
    tests/sample_rpms/Makefile
    tests/webfaf/Makefile
    tests/webfaf/webfaftests/Makefile
    tests/retrace_outputs/Makefile
    tests/bin/Makefile
    tests/sample_repo/Makefile
])

AC_OUTPUT
