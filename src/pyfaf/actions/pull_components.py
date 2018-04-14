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
from pyfaf.common import FafError
from pyfaf.opsys import systems
from pyfaf.queries import (get_component_by_name,
                           get_opsys_by_name,
                           get_osrelease)
from pyfaf.storage import (OpSysComponent,
                           OpSysReleaseComponent)


class PullComponents(Action):
    name = "pull-components"

    def __init__(self):
        super(PullComponents, self).__init__()

    def _get_tasks(self, cmdline, db):
        result = set()

        # no arguments - pull everything for non-EOL releases
        if len(cmdline.opsys) < 1:
            for osplugin in systems.values():
                db_opsys = get_opsys_by_name(db, osplugin.nice_name)
                if db_opsys is None:
                    raise FafError("Operating system '{0}' is not defined in "
                                   "storage".format(osplugin.nice_name))

                for db_release in db_opsys.releases:
                    if db_release.status != "EOL":
                        result.add((osplugin, db_release))

        # a single opsys - respect opsysrelease
        elif len(cmdline.opsys) == 1:
            if cmdline.opsys[0] not in systems:
                raise FafError("Operating system '{0}' is not supported"
                               .format(cmdline.opsys[0]))

            osplugin = systems[cmdline.opsys[0]]
            db_opsys = get_opsys_by_name(db, osplugin.nice_name)
            if db_opsys is None:
                raise FafError("Operating system '{0}' is not defined in "
                               "storage".format(osplugin.nice_name))

            if len(cmdline.opsys_release) < 1:
                for db_release in db_opsys.releases:
                    result.add((osplugin, db_release))
            else:
                for release in cmdline.opsys_release:
                    db_release = get_osrelease(db, osplugin.nice_name, release)
                    if db_release is None:
                        self.log_warn("Operating system '{0} {1}' is not "
                                      "supported".format(osplugin.nice_name,
                                                         release))
                        continue

                    result.add((osplugin, db_release))

        # multiple opsys - pull all of their releases
        else:
            for opsys_name in cmdline.opsys:
                if not opsys_name in systems:
                    self.log_warn("Operating system '{0}' is not supported"
                                  .format(opsys_name))
                    continue

                osplugin = systems[opsys_name]
                db_opsys = get_opsys_by_name(db, osplugin.nice_name)
                if db_opsys is None:
                    self.log_warn("Operating system '{0}' is not defined in "
                                  "storage".format(osplugin.nice_name))
                    continue

                for db_release in db_opsys.releases:
                    result.add((osplugin, db_release))

        return sorted(result, key=lambda p_r: (p_r[1].opsys.name, p_r[1].version))

    def run(self, cmdline, db):
        try:
            tasks = self._get_tasks(cmdline, db)
        except FafError as ex:
            self.log_error("Unable to process command line arguments: {0}"
                           .format(str(ex)))
            return 1

        new_components = {}

        i = 0
        for osplugin, db_release in tasks:
            i += 1

            self.log_info("[{0} / {1}] Processing '{2} {3}'"
                          .format(i, len(tasks), osplugin.nice_name,
                                  db_release.version))

            db_components = [c.component.name for c in db_release.components]
            remote_components = osplugin.get_components(db_release.version)

            for remote_component in remote_components:
                if remote_component in db_components:
                    continue

                db_component = get_component_by_name(db, remote_component,
                                                     db_release.opsys.name)

                if db_component is None:
                    key = (db_release.opsys, remote_component)
                    if key in new_components:
                        db_component = new_components[key]
                    else:
                        self.log_info("Creating new component '{0}' in "
                                      "operating system '{1}'"
                                      .format(remote_component,
                                              osplugin.nice_name))

                        db_component = OpSysComponent()
                        db_component.name = remote_component
                        db_component.opsys = db_release.opsys
                        db.session.add(db_component)

                        new_components[key] = db_component

                self.log_info("Creating new component '{0}' in {1} {2}"
                              .format(remote_component, osplugin.nice_name,
                                      db_release.version))
                db_release_component = OpSysReleaseComponent()
                db_release_component.release = db_release
                db_release_component.component = db_component
                db.session.add(db_release_component)

        db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_opsys(multiple=True)
        parser.add_opsys_release(multiple=True)
