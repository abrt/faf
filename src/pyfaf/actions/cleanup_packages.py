# Copyright (C) 2016  ABRT Team
# Copyright (C) 2016  Red Hat, Inc.
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
from sqlalchemy.orm import aliased
from pyfaf.storage.opsys import BuildOpSysReleaseArch, Package
from pyfaf.queries import get_opsys_by_name, get_osrelease

class CleanupPackages(Action):
    name = "cleanup-packages"

    def run(self, cmdline, db):
        # nobody will write the full name
        if cmdline.OPSYS == "rhel":
            cmdline.OPSYS = "Red Hat Enterprise Linux"

        # check if operating system is known
        if not get_opsys_by_name(db, cmdline.OPSYS):
            self.log_error("Selected operating system '{0}' is not supported."
                           .format(cmdline.OPSYS))
            return 1
        else:
            self.log_info("Selected operating system: '{0}'"
                          .format(cmdline.OPSYS))

        # check if release is known
        opsysrelease = get_osrelease(db, cmdline.OPSYS, cmdline.RELEASE)
        if not opsysrelease:
            self.log_error("Selected release '{0}' is not supported."
                           .format(cmdline.RELEASE))
            return 1
        else:
            self.log_info("Selected release: '{0}'".format(cmdline.RELEASE))

        # find all builds, that are assigned to this opsysrelease but none other
        # architecture is missed out intentionally
        bosra1 = aliased(BuildOpSysReleaseArch)
        bosra2 = aliased(BuildOpSysReleaseArch)
        all_builds = (db.session.query(bosra1)
                      .filter(bosra1.opsysrelease_id == opsysrelease.id)
                      .filter(~bosra1.build_id.in_(
                          db.session.query(bosra2.build_id)
                          .filter(bosra1.build_id == bosra2.build_id)
                          .filter(bosra2.opsysrelease_id != opsysrelease.id)
                      ))
                      .all())

        #delete all records, where the opsysrelease.id is present
        query = (db.session.query(BuildOpSysReleaseArch)
                 .filter(BuildOpSysReleaseArch.opsysrelease_id == opsysrelease.id))

        self.log_info("{0} links will be removed".format(query.count()))
        if cmdline.dry_run:
            self.log_info("Dry run active, removal will be skipped")
        else:
            query.delete()

        #delete all builds and packages from them
        for build in all_builds:
            for pkg in (db.session.query(Package)
                        .filter(Package.build_id == build.build_id)
                        .all()):
                self.delete_package(pkg, db, cmdline.dry_run)


    def delete_package(self, pkg, db, dry_run):
        #delete package from disk
        if pkg.has_lob("package"):
            self.log_info("Deleting lob for: {0}".format(pkg.nevr()))
            if dry_run:
                self.log_info("Dry run active, removal will be skipped")
            else:
                pkg.del_lob("package")


    def tweak_cmdline_parser(self, parser):

        parser.add_argument("OPSYS", help="operating system")
        parser.add_argument("RELEASE", help="release")
