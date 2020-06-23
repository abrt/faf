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

from pyfaf.storage.opsys import BuildOpSysReleaseArch, Package
from pyfaf.actions import Action
from pyfaf.queries import (get_arch_by_name,
                           get_opsys_by_name,
                           get_osrelease,
                           get_builds_by_opsysrelease_id,
                           get_builds_by_arch_id)


class CleanupPackages(Action):
    name = "cleanup-packages"

    def run(self, cmdline, db):
        if not cmdline.OPSYS and not cmdline.RELEASE and not cmdline.arch:
            self.log_error("None of the arguments were specified.")
            return 1

        if (cmdline.OPSYS or cmdline.RELEASE) and cmdline.arch:
            self.log_error("Argument --arch not allowed with OPSYS and RELEASE.")
            return 1

        if cmdline.OPSYS and not cmdline.RELEASE:
            self.log_error("Missing RELEASE argument.")
            return 1

        # in case we're using the web UI:
        if not hasattr(cmdline, "dry_run"):
            cmdline.dry_run = False

        if cmdline.OPSYS:
            # nobody will write the full name
            if cmdline.OPSYS == "rhel":
                cmdline.OPSYS = "Red Hat Enterprise Linux"

            # check if operating system is known
            if not get_opsys_by_name(db, cmdline.OPSYS):
                self.log_error("Selected operating system '%s' is not supported.", cmdline.OPSYS)
                return 1

            self.log_info("Selected operating system: '%s'", cmdline.OPSYS)

            # check if release is known
            opsysrelease = get_osrelease(db, cmdline.OPSYS, cmdline.RELEASE)
            if not opsysrelease:
                self.log_error("Selected release '%s' is not supported.", cmdline.RELEASE)
                return 1

            self.log_info("Selected release: '%s'", cmdline.RELEASE)

            # find all builds, that are assigned to this opsysrelease but none other
            # architecture is missed out intentionally
            all_builds = get_builds_by_opsysrelease_id(db, opsysrelease.id)

            #delete all records, where the opsysrelease.id is present
            query = (db.session.query(BuildOpSysReleaseArch)
                     .filter(BuildOpSysReleaseArch.opsysrelease_id == opsysrelease.id))


        elif cmdline.arch:
            # check if operating system is known
            architecture = get_arch_by_name(db, cmdline.arch)
            if not architecture:
                self.log_error("Selected architecture '%s' is not supported.", cmdline.arch)
                return 1

            self.log_info("Selected architecture: '%s'", cmdline.arch)

            # find all builds, that are assigned to this arch_id but none other
            all_builds = get_builds_by_arch_id(db, architecture.id)

            #delete all records, where the arch.id is present
            query = (db.session.query(BuildOpSysReleaseArch)
                     .filter(BuildOpSysReleaseArch.arch_id == architecture.id))

        else:
            self.log_error("Architecture or operating system was not selected.")
            return 1

        self.log_info("%d links will be removed", query.count())
        if cmdline.dry_run:
            self.log_info("Dry run active, removal will be skipped")
        else:
            for build in all_builds:
                for pkg in (db.session.query(Package)
                            .filter(Package.build_id == build.build_id)
                            .all()):
                    self.delete_package(pkg, cmdline.dry_run)

            query.delete()

        return 0

    def tweak_cmdline_parser(self, parser):
        #TODO: use two argument groups: OS and release, and architecture # pylint: disable=fixme
        parser.add_opsys(positional=True, helpstr="operating system")
        parser.add_opsys_release(positional=True, helpstr="release")
        parser.add_arch(helpstr="architecture")
