AC_INIT([faf], [0.5])

AM_INIT_AUTOMAKE([-Wall])
AM_MAINTAINER_MODE

AC_CONFIG_MACRO_DIR([m4])

AC_DISABLE_STATIC
AC_PROG_CC
AC_GNU_SOURCE
AC_PROG_LIBTOOL

AM_PATH_PYTHON([2.6])
AX_PYTHON_MODULE([rpm], [1])
AX_PYTHON_MODULE([rpmUtils.miscutils], [1])

AC_PATH_PROGS(BASH, sh bash)

# Manual pages.
AC_PATH_PROG([ASCIIDOC], [asciidoc], [no])
[if test "$ASCIIDOC" = "no"]
[then]
    [echo "The asciidoc program was not found in the search path. Please ensure"]
    [echo "that it is installed and its directory is included in the search path."]
    [echo "Then run configure again before attempting to build faf."]
    [exit 1]
[fi]

# Manual pages.
AC_PATH_PROG([XMLTO], [xmlto], [no])
[if test "$XMLTO" = "no"]
[then]
    [echo "The xmlto program was not found in the search path. Please ensure"]
    [echo "that it is installed and its directory is included in the search path."]
    [echo "Then run configure again before attempting to build faf."]
    [exit 1]
[fi]

# faf-dwarf-files.c
AC_CHECK_HEADERS([dwarf.h],,AC_MSG_ERROR([Required header file dwarf.h was not found. Please ensure that the development headers for elfutils are installed. Then run configure again before attempting to build faf.]))

AC_CONFIG_FILES([
    faf.spec
    Makefile
    bin/Makefile
    config/Makefile
    pyfaf/Makefile
    tests/Makefile
    tests/sample_reports/Makefile
    pyfaf/client/Makefile
    pyfaf/client/commands/Makefile
    pyfaf/hub/Makefile
    pyfaf/hub/common/Makefile
    pyfaf/hub/problems/Makefile
    pyfaf/hub/reports/Makefile
    pyfaf/hub/summary/Makefile
    pyfaf/hub/status/Makefile
    pyfaf/hub/templates/Makefile
    pyfaf/hub/templates/openid/Makefile
    pyfaf/hub/templates/problems/Makefile
    pyfaf/hub/templates/reports/Makefile
    pyfaf/hub/templates/summary/Makefile
    pyfaf/hub/templates/status/Makefile
    pyfaf/hub/templatetags/Makefile
    pyfaf/hub/xmlrpc/Makefile
    pyfaf/hub/media/Makefile
    pyfaf/hub/services/Makefile
    pyfaf/hub/query/Makefile
    pyfaf/storage/Makefile
    pyfaf/storage/fixtures/Makefile
    pyfaf/storage/fixtures/sql/Makefile
    pyfaf/worker/Makefile
    pyfaf/worker/tasks/Makefile
    wrappers/Makefile
])

AC_OUTPUT
