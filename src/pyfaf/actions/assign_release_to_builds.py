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
from pyfaf.storage.opsys import (Build, BuildOpSysReleaseArch, OpSys,
                                 OpSysRelease, Arch)
from pyfaf.opsys import systems
from pyfaf.queries import get_opsys_by_name, get_osrelease, get_arch_by_name


class AssignReleaseToBuilds(Action):
    name = "assign-release-to-builds"

    def __init__(self):
        super(AssignReleaseToBuilds, self).__init__()
        self.uncommited = 0

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

        # check if architecture is known
        arch = get_arch_by_name(db, cmdline.ARCH)
        if not arch:
            self.log_error("Selected architecture '{0}' is not supported."
                            .format(cmdline.ARCH))
            return 1
        else:
            self.log_info("Selected architecture: '{0}'".format(cmdline.ARCH))

        # when release-builds argument specified
        if cmdline.released_builds:
            self.log_info("Assigning released builds for '{0} {1}'"
                    .format(cmdline.OPSYS, cmdline.RELEASE))
            opsys = self._edit_opsys(cmdline.OPSYS)
            if not opsys in systems.keys():
                self.log_error("There are no known released builds for '{0}'"
                                    .format(cmdline.OPSYS))
                return 1

            for build in systems[opsys].get_released_builds(cmdline.RELEASE):
                found_build = (db.session.query(Build)
                         .filter(Build.base_package_name ==
                                 build["name"])
                         .filter(Build.version == build["version"])
                         .filter(Build.release == build["release"])
                         .filter(Build.epoch == build["epoch"])
                         .first())

                if found_build:
                    self._add_into_build_opsysrelease_arch(db, found_build,
                                                           opsysrelease, arch)

        # when expression argument was passed
        if cmdline.expression:
            self.log_info("Selecting builds by expression: '{0}'"
                    .format(cmdline.expression))
            found_builds = (db.session.query(Build)
                            .filter(Build.release.like("%{0}"
                            .format(cmdline.expression)))
                            .all())
            for build in found_builds:
                self._add_into_build_opsysrelease_arch(db, build,
                                                       opsysrelease, arch)

        db.session.flush()

    def _edit_opsys(self, original_name):
        """ Solve name problem

        There is one complication with operating system names. In the database
        names are in a full form, with capital latters e.g. Fedora, CentOS,
        Red Hat Enterpise Linux. On the other hand, plugins are associated with
        names in shorter form a without capitals e.g fedora, centos, rhel.
        """
        if original_name == "Red Hat Enterprise Linux":
            return "rhel"
        else:
            return original_name.lower()


    def _add_into_build_opsysrelease_arch(self, db, build, opsysrelease, arch):
        build_opsysrelease_arch = (
               db.session.query(BuildOpSysReleaseArch)
               .join(Build)
               .join(OpSysRelease)
               .join(Arch)
               .filter(Build.id == build.id)
               .filter(OpSys.name == opsysrelease.opsys.name)
               .filter(OpSysRelease.version == opsysrelease.version)
               .filter(Arch.name == arch.name)
               .first())

        if not build_opsysrelease_arch:
            self.log_info("Adding link between build {0}-{1} "
                    "operating system '{2}', release '{3} and "
                    "architecture {4}".format(build.base_package_name,
                    build.version, opsysrelease.opsys.name,
                    opsysrelease.version, arch.name))
            bosra = BuildOpSysReleaseArch()
            bosra.build = build
            bosra.opsysrelease = opsysrelease
            bosra.arch = arch

            db.session.add(bosra)
            self.uncommited += 1
            if self.uncommited > 1000:
                self.uncommited = 0
                db.session.flush()


    def tweak_cmdline_parser(self, parser):
        parser.add_argument("OPSYS", help="operating system to be assigned")
        parser.add_argument("RELEASE", help="release to be assigned")
        parser.add_argument("ARCH", help="architecture to be assigned")
        parser.add_argument("--expression", dest='expression',
                            help="sql 'like' statement will be used with given"
                                 " expession")
        parser.add_argument("--released-builds", action="store_true", 
                            help = "released builds will be assigned")
