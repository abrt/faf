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

import os
import re
import shutil
import string #pylint: disable=deprecated-module
import tempfile
from pyfaf.queries import get_packages_by_file, get_packages_by_file_builds_arch
from pyfaf.actions import Action
from pyfaf.retrace import usrmove
from pyfaf.utils.proc import safe_popen


class Coredump2Packages(Action):
    name = "c2p"
    cmdline_only = True

    UNSTRIP_LINE_PARSER = re.compile(r"""
                                     ^0x[0-9a-f]+
                                     \+
                                     0x[0-9a-f]+
                                     \s+
                                     ( ([0-9a-f]+) @ 0x[0-9a-f]+ | \- )
                                     \s+
                                     (\S+)
                                     \s+
                                     (\S+)
                                     \s+
                                     ( (\S+) | ( \[vdso: \s+ (\d+)\] ) )
                                     ( \s+ \(deleted\) )?
                                     $
                                     """, re.VERBOSE)

    SKIP_PACKAGES = ["kernel", "kernel-debuginfo",
                     "kernel-PAE", "kernel-PAE-debuginfo",
                     "kernel-debug", "kernel-debug-debuginfo", "kernel-lpae"]


    def _build_id_to_debug_files(self, build_id):
        return ["/usr/lib/debug/.build-id/{0}/{1}.debug".format(build_id[:2],
                                                                build_id[2:]),
                "/usr/lib/.build-id/{0}/{1}".format(build_id[:2], build_id[2:])]


    def _unstrip(self, cmdline):
        build_ids = []
        missing = []

        self.log_info("Executing eu-unstrip")
        child = safe_popen("eu-unstrip", "-n", "--core", cmdline.COREDUMP, encoding="utf-8")
        if child is None:
            self.log_error("Failed to execute eu-unstrip")
            return 1

        for line in child.stdout.splitlines():
            if not all(c in string.printable for c in line):
                self.log_warn("Skipping line with non-printable characters")
                self.log_debug(line)
                continue
            match = Coredump2Packages.UNSTRIP_LINE_PARSER.match(line)
            if not match:
                self.log_warn("Unable to parse line: {0}".format(line))
                continue

            # Build ID
            if match.group(2):
                # File
                if match.group(3).startswith("/"):
                    build_ids.append((match.group(2), match.group(3)))
                # Name
                elif match.group(5) != "-":
                    # vDSO
                    if match.group(7):
                        self.log_debug("Skipping vDSO %s", match.group(8))
                        continue
                    # Deleted
                    if match.group(9):
                        self.log_warn("{} was reported as deleted, "
                                      "which means that the file comes from "
                                      "a different package version than "
                                      "the one installed".format(match.group(5)))
                        continue

                    build_ids.append((match.group(2), match.group(5)))
                else:
                    build_ids.append((match.group(2), None))
            else:
                missing.append(match.group(3))

        return build_ids, missing

    def run(self, cmdline, db):
        build_ids, _ = self._unstrip(cmdline)

        self.log_info("Mapping build-ids into debuginfo packages")
        build_id_maps = {}
        debuginfos = {}
        for build_id, soname in build_ids:
            files = self._build_id_to_debug_files(build_id)
            db_packages = get_packages_by_file(db, files)
            db_packages = [p for p in db_packages if p.has_lob("package")]
            if not db_packages:
                self.log_warn("No debuginfo found for '{0}' ({1})"
                              .format(build_id, soname))
                continue
            self.log_debug("Found %d debuginfo packages for '%s' (%s): %s",
                           len(db_packages), build_id, soname, [p.nvra() for p in db_packages])

            if build_id not in build_id_maps:
                build_id_maps[build_id] = set()

            for db_package in db_packages:
                pkgname = db_package.name
                pkgnvra = db_package.nvra()

                build_id_maps[build_id].add(pkgname)

                if pkgname not in debuginfos:
                    debuginfos[pkgname] = {}

                if pkgnvra not in debuginfos[pkgname]:
                    debuginfos[pkgname][pkgnvra] = {"count": 0,
                                                    "package": db_package}

                debuginfos[pkgname][pkgnvra]["count"] += 1

        for build_id, debug_pkgs in build_id_maps.items():
            if len(debug_pkgs) > 1:
                self.log_warn("Debuginfo conflict: '{0}' is provided by {1}"
                              .format(build_id, debug_pkgs))

            build_id_maps[build_id] = debug_pkgs.pop()

        result = set()
        debuginfo_maps = {}
        debuginfo_packages = []
        for pkgname in sorted(debuginfos):
            best = {"count": -1, "package": None}
            for pkgnvra in debuginfos[pkgname]:
                if debuginfos[pkgname][pkgnvra]["count"] > best["count"]:
                    best = debuginfos[pkgname][pkgnvra]

            if best["package"]:
                basename = best["package"].build.base_package_name
                if basename in Coredump2Packages.SKIP_PACKAGES:
                    self.log_debug("Skipping '%s'", basename)
                    continue

                self.log_debug("Picking '%s' for '%s' with %d build_id matches",
                               best["package"].nvra(), best["package"].name, best["count"])

                debuginfo_packages.append(best["package"])
                debuginfo_maps[best["package"].name] = best["package"]
                result.add(best["package"])
            else:
                #paranoia - never happens
                self.log_warn("Unable to determine best version of '{0}'"
                              .format(pkgname))

        self.log_info("Getting binary packages from debuginfos")
        archs = {}
        db_build_ids = [dp.build.id for dp in debuginfo_packages]
        postprocess = set()
        for build_id, soname in build_ids:
            if build_id not in build_id_maps:
                continue

            if soname is None:
                if (build_id in build_id_maps and
                        isinstance(build_id_maps[build_id], str) and
                        build_id_maps[build_id] in debuginfo_maps):
                    nvra = debuginfo_maps[build_id_maps[build_id]].nvra()
                    self.log_info("No shared object name for '{0}' ({1})"
                                  .format(build_id, nvra))
                    db_build = debuginfo_maps[build_id_maps[build_id]].build
                    postprocess.add(db_build)
            else:
                debuginfo_name = build_id_maps[build_id]
                if debuginfo_name in Coredump2Packages.SKIP_PACKAGES:
                    self.log_debug("Skipping %s", debuginfo_name)
                    continue

                db_arch = debuginfo_maps[debuginfo_name].arch
                abspath = soname.startswith("/")
                db_packages = get_packages_by_file_builds_arch(db,
                                                               soname,
                                                               db_build_ids,
                                                               db_arch,
                                                               abspath=abspath)

                if abspath and not db_packages:
                    new_soname = usrmove(soname)
                    db_packages = get_packages_by_file_builds_arch(db,
                                                                   new_soname,
                                                                   db_build_ids,
                                                                   db_arch)

                if not db_packages:
                    self.log_warn("Unable to find binary package for '{0}' "
                                  "({1})".format(build_id, soname))
                    continue

                for db_package in db_packages:
                    result.add(db_package)
                    arch = db_arch.name
                    if arch not in archs:
                        archs[arch] = 0

                    archs[arch] += 1

        if postprocess and archs:
            self.log_info("Post-processing records without shared object name")
            arch = None
            archmax = 0
            for archname, archcount in archs.items():
                if archcount > archmax:
                    archmax = archcount
                    arch = archname

            self.log_info("Determined architecture: {0}".format(arch))

            for db_build in postprocess:
                basename = db_build.base_package_name
                if basename in Coredump2Packages.SKIP_PACKAGES:
                    self.log_info("Skipping {0}".format(basename))
                    continue

                for db_package in db_build.packages:
                    if db_package.arch.name == arch:
                        self.log_debug("Picking %s for %s", db_package.nvra(), basename)
                        result.add(db_package)

        link = None
        tmpdir = None
        if cmdline.symlink_dir:
            tmpdir = tempfile.mkdtemp(dir=cmdline.symlink_dir)
            link = os.symlink
        elif cmdline.hardlink_dir:
            tmpdir = tempfile.mkdtemp(dir=cmdline.hardlink_dir)
            link = os.link

        for db_package in result:
            if link is None:
                print(db_package.nvra())
                continue

            path_from = db_package.get_lob_path("package")
            path_to = os.path.join(tmpdir, "{0}.rpm".format(db_package.nvra()))
            try:
                link(path_from, path_to)
            except OSError:
                if cmdline.no_copy:
                    continue

                shutil.copy2(path_from, path_to)

        if tmpdir is not None:
            print(tmpdir)
        return 0

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("COREDUMP", help="coredump file to analyze")
        parser.add_argument("--hardlink-dir",
                            help="Hardlink resulting packages into a directory")
        parser.add_argument("--symlink-dir",
                            help="Symlink resulting packages into a directory")
        parser.add_argument("--no-copy", action="store_true", default=False,
                            help="Do not fallback to copying when link fails")
