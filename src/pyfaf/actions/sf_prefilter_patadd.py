# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
#
# This file is part of faf.
#
# faf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# faf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with faf.  If not, see <http://www.gnu.org/licenses/>.

import re
from pyfaf.actions import Action
from pyfaf.opsys import systems
from pyfaf.queries import (get_sf_prefilter_btpath_by_pattern,
                           get_sf_prefilter_pkgname_by_pattern,
                           get_sf_prefilter_sol,
                           get_opsys_by_name)
from pyfaf.storage import SfPrefilterBacktracePath, SfPrefilterPackageName


class SfPrefilterPatAdd(Action):
    name = "sf-prefilter-patadd"


    def run(self, cmdline, db):
        db_solution = get_sf_prefilter_sol(db, cmdline.SOLUTION)

        if db_solution is None:
            self.log_error("Unable to find solution '{0}'"
                           .format(cmdline.SOLUTION))
            return 1

        if cmdline.opsys is not None:
            if cmdline.opsys not in systems:
                self.log_error("Operating system '{0}' is not supported"
                               .format(cmdline.opsys))
                return 1

            osplugin = systems[cmdline.opsys]
            db_opsys = get_opsys_by_name(db, osplugin.nice_name)

            if db_opsys is None:
                self.log_error("Operating system '{0}' is not installed "
                               "in storage".format(osplugin.nice_name))
                return 1
        else:
            db_opsys = None

        self.log_info("Adding patterns for '{0}'".format(db_solution.cause))
        if db_opsys is not None:
            self.log_info("Limitting patterns to operating system '{0}'"
                          .format(db_opsys.name))

        for btpath in cmdline.btpath:
            self.log_debug("Processing stacktrace path pattern: {0}"
                           .format(btpath))
            db_btpath = get_sf_prefilter_btpath_by_pattern(db, btpath)
            if db_btpath is not None:
                self.log_debug("Stacktrace path pattern {0} already exists"
                               .format(btpath))
                continue

            try:
                re.compile(btpath)
            except re.error as ex:
                self.log_warn("Stacktrace path pattern {0} can not be "
                              "compiled: {1}".format(btpath, str(ex)))
                continue

            self.log_info("Adding new stacktrace path pattern: {0}"
                          .format(btpath))

            db_btpath = SfPrefilterBacktracePath()
            db_btpath.solution = db_solution
            db_btpath.opsys = db_opsys
            db_btpath.pattern = btpath
            db.session.add(db_btpath)

        for pkgname in cmdline.pkgname:
            self.log_debug("Processing package name pattern: {0}"
                           .format(pkgname))
            db_btpath = get_sf_prefilter_pkgname_by_pattern(db, pkgname)
            if db_btpath is not None:
                self.log_debug("Package name pattern {0} already exists"
                               .format(pkgname))
                continue

            try:
                re.compile(pkgname)
            except re.error as ex:
                self.log_warn("Package name pattern {0} can not be "
                              "compiled: {1}".format(pkgname, str(ex)))
                continue

            self.log_info("Adding new package name pattern: {0}"
                          .format(pkgname))

            db_pkgname = SfPrefilterPackageName()
            db_pkgname.solution = db_solution
            db_pkgname.opsys = db_opsys
            db_pkgname.pattern = pkgname
            db.session.add(db_pkgname)

        db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_opsys()
        parser.add_argument("SOLUTION", help="Solution ID or textual cause")
        parser.add_argument("--btpath", action="append", default=[],
                            help="Regexp to match the path in stacktrace")
        parser.add_argument("--pkgname", action="append", default=[],
                            help="Regexp to match the package name")
