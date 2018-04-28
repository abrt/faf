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

from pyfaf.actions import Action
from pyfaf.opsys import systems
from pyfaf.queries import get_components_by_opsys, get_opsys_by_name
from pyfaf.storage import BuildComponent


class FindComponents(Action):
    name = "find-components"

    def __init__(self):
        super(FindComponents, self).__init__()

    def run(self, cmdline, db):
        result = set()

        if len(cmdline.opsys) < 1:
            for osname, osplugin in systems.items():
                db_opsys = get_opsys_by_name(db, osplugin.nice_name)
                if db_opsys is None:
                    self.log_warn("Operating system '{0}' is not installed"
                                  .format(osplugin.nice_name))
                    continue

                result.add((osplugin, db_opsys))
        else:
            for osname in cmdline.opsys:
                if osname not in systems:
                    self.log_warn("Operating system '{0}' is not supported"
                                  .format(osname))
                    continue

                osplugin = systems[osname]
                db_opsys = get_opsys_by_name(db, osplugin.nice_name)
                if db_opsys is None:
                    self.log_warn("Operating system '{0}' is not installed"
                                  .format(osplugin.nice_name))
                    continue

                result.add((osplugin, db_opsys))

        for osplugin, db_opsys in result:
            db_components = get_components_by_opsys(db, db_opsys)
            components = {}
            for db_component in db_components:
                components[db_component.name] = db_component

            i = 0
            db_builds = osplugin.get_build_candidates(db)
            for db_build in db_builds:
                i += 1

                self.log_info("[{0} / {1}] Processing '{2}'"
                              .format(i, len(db_builds), db_build.nevr()))

                comp_name = db_build.base_package_name
                if comp_name not in components:
                    self.log_debug("Component '{0}' not found in operating "
                                   "system '{1}'".format(comp_name,
                                                         osplugin.nice_name))
                    continue

                db_component = components[comp_name]

                if any(db_component == bcomp.component
                       for bcomp in db_build.components):
                    self.log_debug("Already assigned")
                    continue

                self.log_info("Assigning to component '{0}'".format(comp_name))
                db_buildcomponent = BuildComponent()
                db_buildcomponent.build = db_build
                db_buildcomponent.component = db_component
                db.session.add(db_buildcomponent)

            db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_opsys(multiple=True)
