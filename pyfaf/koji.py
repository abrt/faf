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
from . import support
from . import package
import logging
import os
import rpm
import rpmUtils.miscutils
import sys
import subprocess
import shutil
import tempfile
import time

def get_rpm_entries(os_prefix, build_id):
    KOJI_BUILD = "{0}-koji-build".format(os_prefix)
    KOJI_RPM = "{0}-koji-rpm".format(os_prefix)
    logging.info("Loading build #{0} from {1}.".format(build_id, KOJI_BUILD))
    build = run.cache_get(KOJI_BUILD, build_id)
    logging.info("  - build name {0}".format(build.name))

    logging.info("Loading {0} rpms from {1}.".format(len(build.rpms), KOJI_RPM))
    rpms = []
    for rpm_id in build.rpms:
        logging.info("  - loading rpm #{0}".format(rpm_id))
        rpm_entry = run.cache_get(KOJI_RPM, rpm_id)
        rpms.append(rpm_entry)
    return rpms

def unpack_rpm_entry(os_prefix, rpm_entry):
    KOJI_RPM_DATA = "{0}-koji-rpm-data".format(os_prefix)

    logging.info("Unpacking RPM #{0}: {1}".format(rpm_entry.id, rpm_entry.nvra()))
    rpm_file = open(rpm_entry.filename(), "wb")
    cache_get_proc = subprocess.Popen(["faf-cache", "show", KOJI_RPM_DATA,
                                       str(rpm_entry.id)], stdout=rpm_file)
    cache_get_proc.wait()
    if cache_get_proc.returncode != 0:
        sys.stderr.write("Failed to get RPM from cache.\n")
        exit(1)
    rpm_file.close()

    return package.unpack_rpm_to_tmp(rpm_entry.filename(), prefix="faf-koji")

def download_rpm(rpm_info, os_prefix, attempts=4):
    """
    Koji randomly fails to provide data with
    urllib2.HTTPError: HTTP Error 502: Proxy Error
    So we need to try downloading several times.
    """
    koji_url_args = ["--fedora"] if os_prefix == "fedora" else ["--brew"]
    rpm_file = tempfile.TemporaryFile()
    koji_args = ["faf-koji"] + koji_url_args + ["rpm-data", str(rpm_info[0])]
    koji_proc = subprocess.Popen(koji_args, stdout=rpm_file)
    koji_proc.wait()
    if koji_proc.returncode != 0:
        sys.stderr.write("Failed to download RPM from koji.\n")

    rpm_file.seek(0)
    cache_args = ["faf-cache", "add", "{0}-koji-rpm-data".format(os_prefix), str(rpm_info[0]), "--overwrite"]
    cache_proc = subprocess.Popen(cache_args, stdin=rpm_file)
    cache_proc.wait()
    if cache_proc.returncode != 0:
        sys.stderr.write("Failed to store RPM data to cache.\n")
    if koji_proc.returncode != 0 or cache_proc.returncode != 0:
        if attempts > 0:
            time.sleep(10) # wait 10 seconds before another attempt
            download_rpm(rpm_info, os_prefix, attempts - 1)
            return
        else:
            run.cache_remove("{0}-koji-rpm".format(os_prefix), rpm_info[0], failure_allowed=True)
            logging.warn("  - failed with all attempts to download an RPM from Koji -> skipping")
            return

    koji_args = ["faf-koji"] + koji_url_args + ["rpm", str(rpm_info[0])]
    rpm_text = run.process(koji_args, stdout=subprocess.PIPE, timeout=5*60*60, timeout_attempts=1, returncode_attempts=2)[0]

    transaction_set = rpm.ts()
    rpm_file.seek(0)
    header = transaction_set.hdrFromFdno(rpm_file.fileno())
    filelist = []
    rpm_file_info = header.fiFromHeader()
    for f in rpm_file_info:
        # f is a tuple (FN, FSize, FMode, FMtime, FFlags, FRdev,
        # FInode, FNlink, FState, VFlags, FUser, FGroup, FMD5).
        # File name (FN) is encoded in UTF-8.
        filelist.append(u"- {0}".format(unicode(f[0], "utf-8")))
    if len(filelist) > 0:
        rpm_text += u"Files:\n{0}\n".format(u"\n".join(filelist))
    def build_dependency(dependency_set):
        lines = []
        for p in dependency_set:
            # Package name is encoded in UTF-8.
            lines.append(u"- Name: {0}".format(unicode(p.N(), "utf-8")))
            lines.append(u"  Flags: {0}".format(p.Flags()))
            evr = p.EVR()
            if len(evr) > 0:
                (epoch, version, release) = rpmUtils.miscutils.stringToVersion(evr)
                lines.append(u"  Epoch: {0}".format(epoch))
                lines.append(u"  Version: {0}".format(version))
                lines.append(u"  Release: {0}".format(release))
        return lines
    provides = build_dependency(header.dsFromHeader('providename'))
    if len(provides) > 0:
        rpm_text += u"Provides:\n{0}\n".format(u"\n".join(provides))
    requires = build_dependency(header.dsFromHeader('requirename'))
    if len(requires) > 0:
        rpm_text += u"Requires:\n{0}\n".format(u"\n".join(requires))
    obsoletes = build_dependency(header.dsFromHeader('obsoletename'))
    if len(obsoletes) > 0:
        rpm_text += u"Obsoletes:\n{0}\n".format(u"\n".join(obsoletes))
    conflicts = build_dependency(header.dsFromHeader('conflictname'))
    if len(conflicts) > 0:
        rpm_text += u"Conflicts:\n{0}\n".format(u"\n".join(conflicts))

    rpm_file.close()
    run.cache_add_text(
        rpm_text, rpm_info[0],
        "{0}-koji-rpm".format(os_prefix),
        overwrite=True)
    rpm_entry = cache.koji_rpm.parser.from_text(rpm_text, failure_allowed=False)
    logging.debug("  - {0}: {1}.".format(
            rpm_entry.nvra(),
            support.human_byte_count(rpm_entry.size)))
