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

from typing import Dict, List

from pyfaf.actions import Action
from pyfaf.opsys import systems
from pyfaf.queries import (get_associate_by_name,
                           get_opsys_by_name,
                           get_components_by_opsys)
from pyfaf.storage import (AssociatePeople,
                           OpSysComponentAssociate)


class PullAssociates(Action):
    name = "pull-associates"


    def run(self, cmdline, db) -> None:
        if not cmdline.opsys:
            cmdline.opsys = list(systems.keys())

        opsyss = []
        for shortname in cmdline.opsys:
            if shortname not in systems:
                self.log_warn("Operating system '{0}' is not installed"
                              .format(shortname))
                continue

            opsys = systems[shortname]
            db_opsys = get_opsys_by_name(db, opsys.nice_name)
            if db_opsys is None:
                self.log_warn("Operating system '{0}' is not initialized"
                              .format(shortname))
                continue

            opsyss.append((opsys, db_opsys))

        new_associates: Dict[str, AssociatePeople] = {}
        opsyss_len = len(opsyss)
        for i, (opsys, db_opsys) in enumerate(opsyss, start=1):
            self.log_info("[{0} / {1}] Processing {2}"
                          .format(i, opsyss_len, opsys.nice_name))

            components = get_components_by_opsys(db, db_opsys).all()
            components_len = len(components)
            for j, db_component in enumerate(components, start=1):
                name = db_component.name
                self.log_debug("\t[%d / %d] Processing component '%s'", j, components_len, name)
                try:
                    acls = opsys.get_component_acls(name)
                except TypeError:
                    self.log_warn("Error getting ACLs.")
                    continue

                acl_lists: Dict[str, List[str]] = {
                    "watchbugzilla": [],
                    "commit": []
                }

                for associate_name, associate_perms in acls.items():
                    for permission, permission_members in acl_lists.items():
                        if associate_perms.get(permission, False):
                            permission_members.append(associate_name)

                for permission, permission_members in acl_lists.items():
                    acl_list_perm_len = len(permission_members)
                    for k, associate in enumerate(permission_members, start=1):
                        self.log_debug("\t[%d / %d] Processing associate '%s' permission %s",
                                       k, acl_list_perm_len, associate, permission)

                        db_associate = get_associate_by_name(db, associate)
                        if db_associate is None:
                            if associate in new_associates:
                                db_associate = new_associates[associate]
                            else:
                                db_associate = AssociatePeople()
                                db_associate.name = associate
                                db.session.add(db_associate)
                                new_associates[associate] = db_associate

                                self.log_info("Adding a new associate '{0}'"
                                              .format(associate))

                        associates = [a.associates for a in db_component.associates
                                      if a.permission == permission]
                        if db_associate not in associates:
                            db_associate_comp = OpSysComponentAssociate()
                            db_associate_comp.component = db_component
                            db_associate_comp.associates = db_associate
                            db_associate_comp.permission = permission
                            db.session.add(db_associate_comp)

                            self.log_info("Assigning associate '{0}' to component "
                                          "'{1}' with permission {2}"
                                          .format(associate, name, permission))

                    for db_associate_comp in db_component.associates:
                        if (db_associate_comp.permission == permission
                                and db_associate_comp.associates.name not in permission_members):
                            db.session.delete(db_associate_comp)
                            self.log_info("Removing associate '{0}' permission "
                                          "{1} from component '{2}'"
                                          .format(db_associate_comp.associates.name,
                                                  permission, name))

                db.session.flush()

    def tweak_cmdline_parser(self, parser) -> None:
        parser.add_opsys(multiple=True, helpstr="operating system")
