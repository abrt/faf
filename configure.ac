AC_INIT([faf], [0.9])

AM_INIT_AUTOMAKE([-Wall])
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
    src/external/Makefile
    src/external/bootstrap/Makefile
    src/external/flot/Makefile
    src/external/select2/Makefile
    src/pyfaf/Makefile
    src/pyfaf/actions/Makefile
    src/pyfaf/bugtrackers/Makefile
    src/pyfaf/opsys/Makefile
    src/pyfaf/problemtypes/Makefile
    src/pyfaf/repos/Makefile
    src/pyfaf/storage/Makefile
    src/pyfaf/storage/fixtures/Makefile
    src/pyfaf/storage/fixtures/sql/Makefile
    src/pyfaf/utils/Makefile
    src/webfaf/Makefile
    src/webfaf/common/Makefile
    src/webfaf/dumpdirs/Makefile
    src/webfaf/static/Makefile
    src/webfaf/problems/Makefile
    src/webfaf/query/Makefile
    src/webfaf/reports/Makefile
    src/webfaf/services/Makefile
    src/webfaf/stats/Makefile
    src/webfaf/status/Makefile
    src/webfaf/summary/Makefile
    src/webfaf/templates/Makefile
    src/webfaf/templates/dumpdirs/Makefile
    src/webfaf/templates/openid/Makefile
    src/webfaf/templates/problems/Makefile
    src/webfaf/templates/reports/Makefile
    src/webfaf/templates/stats/Makefile
    src/webfaf/templates/status/Makefile
    src/webfaf/templates/summary/Makefile
    src/webfaf/templatetags/Makefile
    src/webfaf/xmlrpc/Makefile
])

AC_OUTPUT
