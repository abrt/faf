# Copyright (C) 2014  ABRT Team
# Copyright (C) 2014  Red Hat, Inc.
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
from pyfaf.queries import get_component_by_name, get_component_by_name_release, get_opsys_by_name, get_osrelease
from pyfaf.storage import OpSysComponent, OpSysReleaseComponent


class ComponentAdd(Action):
    name = "compadd"


    def run(self, cmdline, db):
        if cmdline.opsys is None:
            self.log_error("You must specify an operating system")
            return 1

        if not cmdline.opsys in systems:
            self.log_error("Operating system '{0}' does not exist"
                           .format(cmdline.opsys))
            return 1

        opsys = systems[cmdline.opsys]
        db_opsys = get_opsys_by_name(db, opsys.nice_name)
        if db_opsys is None:
            self.log_error("Operating system '{0}' is not installed"
                           .format(opsys.nice_name))
            return 1

        db_component = get_component_by_name(db, cmdline.COMPONENT,
                                             opsys.nice_name)
        if db_component is None:
            self.log_info("Adding component '{0}' to operating system '{1}'"
                          .format(cmdline.COMPONENT, opsys.nice_name))

            db_component = OpSysComponent()
            db_component.opsys = db_opsys
            db_component.name = cmdline.COMPONENT
            db.session.add(db_component)

        for release in cmdline.opsys_release:
            db_release = get_osrelease(db, opsys.nice_name, release)
            if db_release is None:
                self.log_warn("Release '{0} {1}' is not defined"
                              .format(opsys.nice_name, release))
                continue

            db_relcomponent = get_component_by_name_release(db, db_release,
                                                            cmdline.COMPONENT)
            if db_relcomponent is None:
                self.log_info("Adding component '{0}' to '{1} {2}'"
                              .format(cmdline.COMPONENT,
                                      opsys.nice_name, release))

                db_relcomponent = OpSysReleaseComponent()
                db_relcomponent.component = db_component
                db_relcomponent.release = db_release
                db.session.add(db_relcomponent)

        db.session.flush()
        return 0

    def tweak_cmdline_parser(self, parser):
        parser.add_opsys(required=True, helpstr="operating system")
        parser.add_opsys_release(multiple=True, helpstr="operating system release")
        parser.add_argument("COMPONENT", validators=[("InputRequired", {})], help="Component name")
