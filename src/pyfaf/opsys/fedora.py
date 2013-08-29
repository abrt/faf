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
from pyfaf.opsys import System
from pyfaf.checker import DictChecker, IntChecker, ListChecker, StringChecker
from pyfaf.common import FafError, log
from pyfaf.queries import (get_opsys_by_name,
                           get_package_by_nevra,
                           get_reportpackage)
from pyfaf.storage import Arch, Build, OpSys, Package, ReportPackage, column_len

__all__ = ["Fedora"]


class Fedora(System):
    name = "fedora"
    nice_name = "Fedora"

    supported_repos = ["fedora-koji"]

    packages_checker = ListChecker(
        DictChecker({
            "name":            StringChecker(pattern=r"^[a-zA-Z0-9_\-\.\+~]+$",
                                             maxlen=column_len(Package,
                                                               "name")),
            "epoch":           IntChecker(minval=0),
            "version":         StringChecker(pattern=r"^[a-zA-Z0-9_\.\+]+$",
                                             maxlen=column_len(Build, "version")),
            "release":         StringChecker(pattern=r"^[a-zA-Z0-9_\.\+]+$",
                                             maxlen=column_len(Build, "release")),
            "architecture":    StringChecker(pattern=r"^[a-zA-Z0-9_]+$",
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

    pkg_roles = ["affected", "related", "selinux_policy"]

    @classmethod
    def install(cls, db, logger=None):
        if logger is None:
            logger = log

        logger.info("Adding Fedora operating system")
        new = OpSys()
        new.name = cls.nice_name
        db.session.add(new)
        db.session.flush()

    @classmethod
    def installed(cls, db):
        return bool(get_opsys_by_name(db, cls.nice_name))

    def __init__(self):
        super(Fedora, self).__init__()
        self._pkgdb = fedora.client.PackageDB()

    def _save_packages(self, db, db_report, packages):
        for package in packages:
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
                db_reportpackage.type = "RELATED"
                if "package_role" in package:
                    if package["package_role"] == "affected":
                        db_reportpackage.type = "CRASHED"
                    elif package["package_role"] == "selinux_policy":
                        db_reportpackage.type = "SELINUX_POLICY"
                db.session.add(db_reportpackage)

            db_reportpackage.count += 1

    def validate_ureport(self, ureport):
        Fedora.ureport_checker.check(ureport)
        return True

    def validate_packages(self, packages):
        Fedora.packages_checker.check(packages)
        for package in packages:
            if ("package_role" in package and
                package["package_role"] not in Fedora.pkg_roles):
                raise FafError("Only the following package roles are allowed: "
                               "{0}".format(", ".join(Fedora.pkg_roles)))

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

            result[collection.version] = {"status": collection.statuscode,
                                          "kojitag": collection.koji_name,
                                          "shortname": collection.branchname, }

        return result

    def get_components(self, release):
        if release is not None:
            if not isinstance(release, basestring):
                release = str(release)

            # "rawhide" is called "devel" in pkgdb
            if release.lower() == "rawhide":
                collection = "devel"
            else:
                try:
                    release_num = int(release)
                except ValueError:
                    raise FafError("{0} is not a valid Fedora version"
                                   .format(release))

                if release_num > 13:
                    collection = "f{0}".format(release_num)
                elif release_num > 6:
                    collection = "F-{0}".format(release_num)
                else:
                    collection = "FC-{0}".format(release_num)

        return self._pkgdb.get_package_list(collectn=collection)

    def get_component_acls(self, component, release=None):
        # "rawhide" is called "devel" in pkgdb
        if release is not None and release.lower() == "rawhide":
            release = "devel"

        result = {}

        owner_info = self._pkgdb.get_owners(component, collctn_name="Fedora",
                                            collctn_ver=release)

        # Instance of 'tuple' has no 'packageListings' member
        # pylint: disable-msg=E1103
        for rel in owner_info.packageListings:
            # "devel" is called "rawhide" on all other places
            if rel.collection.version.lower() == "devel":
                relname = "rawhide"
            else:
                relname = rel.collection.version

            acls = {rel.owner: {"owner": True, }, }

            for person in rel.people:
                if any(person.aclOrder.values()):
                    acls[person.username] = {}
                    for acl, value in person.aclOrder.items():
                        acls[person.username][acl] = value is not None

            if release is not None:
                return acls

            result[relname] = acls

        return result

    def get_build_candidates(self, db):
        return (db.session.query(Build)
                          .filter(Build.release.like("%%.fc%%"))
                          .all())

    def check_pkgname_match(self, packages, parser):
        for package in packages:
            if (not "package_role" in package or
                package["package_role"].lower() != "affected"):
                continue

            nvra = "{0}-{1}-{2}.{3}".format(package["name"],
                                            package["version"],
                                            package["release"],
                                            package["architecture"])

            match = parser.match(nvra)
            if match is not None:
                return True

        return False
