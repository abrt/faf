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
from __future__ import absolute_import

import fedora.client
from . import System
from ..checker import DictChecker, IntChecker, ListChecker, StringChecker
from ..common import column_len
from ..queries import get_package_by_nevra, get_reportpackage
from ..storage import Arch, Build, Package, ReportPackage

__all__ = [ "Fedora" ]

class Fedora(System):
    name = "fedora"
    nice_name = "Fedora"

    supported_repos = [ "fedora-koji" ]

    packages_checker = ListChecker(
                         DictChecker({
        "name":            StringChecker(pattern="^[a-zA-Z0-9_\-\.\+~]+$",
                                         maxlen=column_len(Package, "name")),
        "epoch":           IntChecker(minval=0),
        "version":         StringChecker(pattern="^[a-zA-Z0-9_\.\+]+$",
                                         maxlen=column_len(Build, "version")),
        "release":         StringChecker(pattern="^[a-zA-Z0-9_\.\+]+$",
                                         maxlen=column_len(Build, "release")),
        "architecture":    StringChecker(pattern="^[a-zA-Z0-9_]+$",
                                         maxlen=column_len(Arch, "name")),
      }), minlen=1
    )

    ureport_checker = DictChecker({
      # no need to check name, version and architecture twice
      # the toplevel checker already did it
      # "name": StringChecker(allowed=[Fedora.name])
      # "version":        StringChecker()
      # "architecture":   StringChecker()
    })

    def __init__(self):
        System.__init__(self)
        self._pkgdb = fedora.client.PackageDB()

    def _save_packages(self, db, db_report, packages):
        i = 0
        for package in packages:
            i += 1

            db_package = get_package_by_nevra(db,
                                              name=package["name"],
                                              epoch=package["epoch"],
                                              version=package["version"],
                                              release=package["release"],
                                              arch=package["architecture"])
            if db_package is None:
                self.log_warn("Package {0}-{1}:{2}-{3}.{4} not found in "
                              "storage".format(package["name"],
                                               package["epoch"],
                                               package["version"],
                                               package["release"],
                                               package["architecture"]))
                continue

            db_reportpackage = get_reportpackage(db, db_report, db_package)
            if db_reportpackage is None:
                db_reportpackage = ReportPackage()
                db_reportpackage.report = db_report
                db_reportpackage.installed_package = db_package
                db_reportpackage.count = 0
                if i == 1:
                    db_reportpackage.type = "CRASHED"
                elif package["name"] == "selinux-policy":
                    db_reportpackage.type = "SELINUX_POLICY"
                else:
                    db_reportpackage.type = "RELATED"
                db.session.add(db_reportpackage)

            db_reportpackage.count += 1

    def validate_ureport(self, ureport):
        Fedora.ureport_checker.check(ureport)
        return True

    def validate_packages(self, packages):
        Fedora.packages_checker.check(packages)
        return True

    def save_ureport(self, db, db_report, ureport, packages, flush=False):
        self._save_packages(db, db_report, packages)

        if flush:
            db.session.flush()

    def get_releases(self):
        result = {}
        collections = [c[0] for c in self._pkgdb.get_collection_list()]
        for collection in collections:
            # there is EPEL in collections, we are only interested in Fedora
            if collection.name.lower() != Fedora.name:
                continue

            # "devel" is called "rawhide" on all other places
            if collection.version.lower() == "devel":
                collection.version = "rawhide"

            result[collection.version] = { "status": collection.statuscode,
                                           "kojitag": collection.koji_name,
                                           "shortname": collection.branchname, }

        return result

    def get_components(self, release):
        # "rawhide" is called "devel" in pkgdb
        if release is not None and release.lower() == "rawhide":
            release = "devel"

        return self._pkgdb.get_package_list(collectn=release)

    def get_component_acls(self, component, release=None):
        # "rawhide" is called "devel" in pkgdb
        if release is not None and release.lower() == "rawhide":
            release = "devel"

        result = {}

        owner_info = self._pkgdb.get_owners(component, collctn_name="Fedora",
                                            collctn_ver=release)

        for rel in owner_info.packageListings:
            # "devel" is called "rawhide" on all other places
            if rel.collection.version.lower() == "devel":
                relname = "rawhide"
            else:
                relname = rel.collection.version

            acls = { rel.owner: { "owner": True, }, }

            for person in rel.people:
                if any(person.aclOrder.values()):
                    acls[person.username] = {}
                    for acl, value in person.aclOrder.items():
                        acls[person.username][acl] = value is not None

            if release is not None:
                return acls

            result[relname] = acls

        return result
