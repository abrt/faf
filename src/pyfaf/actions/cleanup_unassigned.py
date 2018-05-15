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
from pyfaf.storage.opsys import (BuildOpSysReleaseArch, Build, Package,
                                 PackageDependency, BuildArch, BuildComponent)
from pyfaf.storage.report import ReportPackage
from pyfaf.storage.problem import ProblemOpSysRelease
from pyfaf.storage.llvm import LlvmBuild, LlvmBcFile, LlvmResultFile

class CleanupUnassigned(Action):
    name = "cleanup-unassigned"

    def run(self, cmdline, db):
        # find all build, that are not assigned to any opsysrelease
        all_opsysrelases = db.session.query(BuildOpSysReleaseArch.build_id).distinct()
        all_builds = (db.session.query(Build)
                      .filter(~Build.id.in_(all_opsysrelases))
                      .yield_per(1000))

        count = 0
        #delete all builds and packages from them
        for build in all_builds:
            count += 1
            q = db.session.query(Package).filter(Package.build_id == build.id)
            for pkg in q.all():
                self.log_info("Processing package {0}".format(pkg.nevr()))
                self.delete_package(pkg, db, cmdline.force)
                if cmdline.force:
                    db.session.query(PackageDependency).filter(PackageDependency.package_id == pkg.id).delete()
                    db.session.query(ReportPackage).filter(ReportPackage.installed_package_id == pkg.id).delete()
            if cmdline.force:
                q.delete()
                db.session.query(BuildArch).filter(build.id == BuildArch.build_id).delete()
                db.session.query(BuildComponent).filter(build.id == BuildComponent.build_id).delete()
                db.session.query(ProblemOpSysRelease).filter(build.id
                                                             == ProblemOpSysRelease.probable_fix_build_id).delete()
                q_llvm = db.session.query(LlvmBuild.build_id == build.id)
                for llvm in q_llvm.all():
                    db.session.query(LlvmBcFile).filter(LlvmBcFile.llvmbuild_id == llvm.id).delete()
                    db.session.query(LlvmResultFile).filter(LlvmResultFile.llvmbuild_id == llvm.id).delete()
                db.session.query(Build).filter(Build.id == build.id).delete()
            if count > 1000:
                db.session.flush()
                count = 0

    def delete_package(self, pkg, db, force):
        #delete package from disk
        if pkg.has_lob("package"):
            self.log_info("Deleting lob for: {0}".format(pkg.nevr()))
            if not force:
                self.log_info("Use --force to delete. Skipping removal")
            else:
                pkg.del_lob("package")


    def tweak_cmdline_parser(self, parser):
        parser.add_argument("-f", "--force", action="store_true",
                            help="delete all unassigned packages."
                                 " Without -f acts like --dry-run.")
