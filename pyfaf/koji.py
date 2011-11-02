#!/usr/bin/python
# Copyright (C) 2011 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from . import run
from . import cache
import logging
import os
import sys
import subprocess
import shutil

def get_rpm_entries(os_prefix, build_id):
    KOJI_BUILD = "{0}-koji-build".format(os_prefix)
    KOJI_RPM = "{0}-koji-rpm".format(os_prefix)
    logging.info("Loading build #{0} from {1}.".format(build_id, KOJI_BUILD))
    build = run.cache_get(KOJI_BUILD, build_id,
                          parser_module=cache.koji_build)
    logging.info("  - build name {0}".format(build.name))

    logging.info("Loading {0} rpms from {1}.".format(len(build.rpms), KOJI_RPM))
    rpms = []
    for rpm_id in build.rpms:
        logging.info("  - loading rpm #{0}".format(rpm_id))
        rpm_entry = run.cache_get(KOJI_RPM, rpm_id,
                                  parser_module=cache.koji_rpm)
        rpms.append(rpm_entry)
    return rpms

def unpack_rpm_entry(os_prefix, rpm_entry):
    KOJI_RPM_DATA = "{0}-koji-rpm-data".format(os_prefix)

    logging.info("Unpacking RPM #{0}: {1}".format(rpm_entry.id, rpm_entry.nvra()))
    # Prepare destination directory
    if os.path.exists(rpm_entry.nvra()):
        shutil.rmtree(rpm_entry.nvra())
    os.makedirs(rpm_entry.nvra())

    rpm_file = open(rpm_entry.filename(), "wb")
    cache_get_proc = subprocess.Popen(["faf-cache", "show", KOJI_RPM_DATA,
                                       str(rpm_entry.id)], stdout=rpm_file)
    cache_get_proc.wait()
    if cache_get_proc.returncode != 0:
        sys.stderr.write("Failed to get RPM from cache.\n")
        exit(1)
    rpm_file.close()

    cpio_file = open(rpm_entry.filename() + ".cpio", "wb+")
    rpm2cpio_proc = subprocess.Popen(["rpm2cpio", rpm_entry.filename()],
                                     stdout=cpio_file)
    rpm2cpio_proc.wait()
    if rpm2cpio_proc.returncode != 0:
        sys.stderr.write("Failed to convert RPM to cpio using rpm2cpio.\n")
        exit(1)
    cpio_file.seek(0)

    cpio_proc = subprocess.Popen(["cpio", "--extract", "-d", "--quiet"],
                                 stdin=cpio_file, cwd=rpm_entry.nvra())
    cpio_proc.wait()
    if cpio_proc.returncode != 0:
        sys.stderr.write("Failed to unpack RPM using cpio.\n")
        exit(1)
    cpio_file.close()
    os.remove(rpm_entry.filename() + ".cpio")

    return rpm_entry.nvra()
