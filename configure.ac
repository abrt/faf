AC_INIT([faf],
    m4_esyscmd([cat ./faf-version]),
    [crash-catcher@fedorahosted.org])

AM_INIT_AUTOMAKE([-Wall tar-ustar])
AM_MAINTAINER_MODE

AC_CONFIG_MACRO_DIR([m4])

AC_DISABLE_STATIC
AC_PROG_CC
AC_GNU_SOURCE
AC_PROG_LIBTOOL

AM_PATH_PYTHON([2.6])

AC_PATH_PROGS(BASH, sh bash)

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
    src/webfaf2/Makefile
    src/webfaf2/blueprints/Makefile
    src/webfaf2/static/Makefile
    src/webfaf2/static/js/Makefile
    src/webfaf2/static/fonts/Makefile
    src/webfaf2/static/css/Makefile
    src/webfaf2/templates/Makefile
    src/webfaf2/templates/dumpdirs/Makefile
    src/webfaf2/templates/problems/Makefile
    src/webfaf2/templates/reports/Makefile
    src/webfaf2/templates/stats/Makefile
    src/webfaf2/templates/summary/Makefile
    tests/Makefile
    tests/faftests/Makefile
    tests/sample_plugin_dir/Makefile
    tests/sample_reports/Makefile
    tests/sample_rpms/Makefile
    tests/webfaf/Makefile
    tests/webfaf/webfaftests/Makefile
])

AC_OUTPUT
